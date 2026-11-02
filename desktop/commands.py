"""Persistent command receipts with exact approvals and bounded PTY execution."""
import errno,hashlib,json,os,pty,select,shlex,signal,subprocess,threading,time,uuid
from pathlib import Path

MODES={'disabled','ask','approve','full'}
AUTO_READONLY={('pwd',),('ls',),('ls','-la')}

class Commands:
    def __init__(self,store,redact=lambda s:s):
        self.store=store;self.redact=redact;self.lock=threading.RLock();self.processes={};self.events={}
        for record in store.list('command'):
            if not record.get('project'):
                project=record['cwd']
                if record.get('task'):
                    try:project=store.get('run',record['task'])['config']['project']
                    except (ValueError,KeyError):pass
                record['project']=project;store.put('command',record)
            if record['status'] in ('running','stopping','queued','awaiting_approval'):
                record.update(status='interrupted',finished=time.time(),note='Service restarted. Process state is unknown; no command was repeated.');store.put('command',record)
    @staticmethod
    def fingerprint(command,cwd,timeout):return hashlib.sha256(json.dumps([command,cwd,timeout]).encode()).hexdigest()
    def request(self,command,cwd,mode,task=None,timeout=120,project=None,check=None):
        if mode not in MODES:raise ValueError('Unknown command permission mode')
        if not isinstance(command,str) or not command.strip() or len(command)>16000:raise ValueError('Enter a command up to 16000 characters')
        cwd=str(Path(cwd).resolve())
        if not Path(cwd).is_dir():raise ValueError('Working directory does not exist')
        if type(timeout) is not int:raise ValueError('Command timeout must be an integer')
        if not 1<=timeout<=3600:raise ValueError('Command timeout must be 1–3600 seconds')
        try:readonly=tuple(shlex.split(command)) in AUTO_READONLY
        except ValueError:readonly=False
        automatic=mode=='full' or (mode=='ask' and readonly)
        info=os.stat(cwd)
        record=self.store.put('command',dict(command=command,cwd=cwd,project=str(Path(project or cwd).resolve()),check=check,directory_identity=[info.st_dev,info.st_ino],timeout=timeout,task=task,mode=mode,fingerprint=self.fingerprint(command,cwd,timeout),status='denied' if mode=='disabled' else 'queued' if automatic else 'awaiting_approval',created=time.time(),output='',inputs=[],exit_code=None,started=None,finished=None,environment='Laptop · host',readonly=readonly))
        with self.lock:self.events[record['id']]=threading.Event()
        if automatic:self._launch(record)
        if mode=='disabled':self.events[record['id']].set()
        return self.store.get('command',record['id'])
    def decide(self,ident,approved,fingerprint):
        if type(approved) is not bool:raise ValueError('Approval must be an explicit boolean decision')
        with self.lock:
            record=self.store.get('command',ident)
            if record['status']!='awaiting_approval':raise ValueError('This command is no longer awaiting approval')
            if fingerprint!=record['fingerprint'] or fingerprint!=self.fingerprint(record['command'],record['cwd'],record['timeout']):raise ValueError('Command changed; review a new approval request')
            record['status']='queued' if approved else 'denied';record['decision_at']=time.time();self.store.put('command',record)
            if approved:self._launch(record)
            else:self.events.setdefault(ident,threading.Event()).set()
        return self.store.get('command',ident)
    def _launch(self,record):threading.Thread(target=self._run,args=(record,),daemon=True).start()
    def _run(self,record):
        ident=record['id'];master=None;slave=None;proc=None
        try:
            with self.lock:
                if self.store.get('command',ident)['status']!='queued':return
            info=os.stat(record['cwd'])
            if str(Path(record['cwd']).resolve())!=record['cwd'] or [info.st_dev,info.st_ino]!=record['directory_identity']:raise ValueError('Working directory changed since the command was requested')
            master,slave=pty.openpty()
            # Only three literal list/pwd forms are automatically allowed in Ask mode.
            argv=shlex.split(record['command']) if record['readonly'] else ['/bin/sh','-c',record['command']]
            if record['readonly']:argv[0]='/usr/bin/'+argv[0]
            with self.lock:
                record=self.store.get('command',ident)
                if record['status']!='queued':return
                record.update(status='running',started=time.time());self.store.put('command',record)
                proc=subprocess.Popen(argv,cwd=record['cwd'],stdin=slave,stdout=slave,stderr=slave,start_new_session=True,close_fds=True)
                self.processes[ident]=(proc,master);record['process_id']=proc.pid;self.store.put('command',record)
                os.close(slave);slave=None
            raw=b'';last_saved=0
            while True:
                if time.time()-record['started']>record['timeout']:
                    self._kill(proc);record['note']='Command timed out';break
                ready,_,_=select.select([master],[],[],0.08)
                if ready:
                    try:chunk=os.read(master,8192)
                    except OSError as exc:
                        if exc.errno==errno.EIO:break
                        raise
                    if not chunk:break
                    raw+=chunk
                    if len(raw)>1024*1024:
                        self._kill(proc);record['note']='Stopped at the 1 MiB output limit';break
                    record['output']=self.redact(raw.decode(errors='replace'))
                    if time.time()-last_saved>0.1:
                        current=self.store.get('command',ident);record['inputs']=current['inputs'];self.store.put('command',record);last_saved=time.time()
                elif proc.poll() is not None:break
            proc.wait(timeout=3)
            current=self.store.get('command',ident);record['inputs']=current['inputs'];record['output']=self.redact(raw.decode(errors='replace'))
            record.update(status='finished',exit_code=proc.returncode,finished=time.time())
        except Exception as exc:
            if proc and proc.poll() is None:self._kill(proc)
            record.update(status='error',error=self.redact(str(exc)),finished=time.time())
        finally:
            if slave is not None:os.close(slave)
            if master is not None:os.close(master)
            with self.lock:self.processes.pop(ident,None)
            if proc is not None or record['status'] not in ('queued','running'):self.store.put('command',record)
            self.events.setdefault(ident,threading.Event()).set()
    @staticmethod
    def _kill(proc):
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    def input(self,ident,text):
        if not isinstance(text,str) or len(text)>16000:raise ValueError('Input too long')
        with self.lock:
            if ident not in self.processes:raise ValueError('Command is not accepting input')
            record=self.store.get('command',ident);record['inputs'].append(dict(time=time.time(),text=self.redact(text)));self.store.put('command',record)
            os.write(self.processes[ident][1],text.encode())
    def stop(self,ident):
        with self.lock:
            record=self.store.get('command',ident)
            if record['status']=='awaiting_approval':return self.decide(ident,False,record['fingerprint'])
            if record['status']=='queued':
                record.update(status='cancelled',finished=time.time(),note='Stopped before process launch');self.store.put('command',record);self.events.setdefault(ident,threading.Event()).set();return
            if ident in self.processes:self._kill(self.processes[ident][0])
    def wait(self,ident,cancel=None):
        deadline=time.monotonic()+3600
        while time.monotonic()<deadline:
            record=self.store.get('command',ident)
            if record['status'] in ('finished','denied','error','interrupted','cancelled'):return record
            if cancel and cancel.is_set():self.stop(ident);return dict(record,status='cancelled')
            self.events.setdefault(ident,threading.Event()).wait(0.15)
        self.stop(ident);return self.store.get('command',ident)
