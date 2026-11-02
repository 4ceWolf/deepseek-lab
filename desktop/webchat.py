"""Chat-only website provider, isolated from the API agent and command tools."""
import http.client,json,os,queue,secrets,shutil,subprocess,threading,time
from . import web_artifacts,artifacts,drawing,interactive
from pathlib import Path

BRIDGE=Path(__file__).resolve().parent/'web_bridge/server.mjs'
MODELS=('deepseek-v4-flash','deepseek-v4-pro')

class WebsiteBridge:
    def __init__(self,directory):
        self.directory=Path(directory);self.process=None;self.port=None;self.key='';self.lock=threading.RLock()
    def start(self,browser=''):
        with self.lock:
            if self.process and self.process.poll() is None:return
            node=shutil.which('node')
            if not node:raise ValueError('Website chat requires Node 22+ and Chrome/Chromium. Nothing has been installed.')
            self.directory.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(self.directory,0o700)
            self.key=secrets.token_urlsafe(32)
            self.process=subprocess.Popen([node,str(BRIDGE)],cwd=BRIDGE.parent,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1,close_fds=True)
            self.process.stdin.write(json.dumps(dict(directory=str(self.directory),key=self.key,browser=browser))+'\n');self.process.stdin.flush()
            result=queue.Queue();process=self.process
            threading.Thread(target=lambda:result.put(process.stdout.readline(1000)),daemon=True).start()
            try:
                greeting=json.loads(result.get(timeout=10));port=greeting['port']
                if type(port) is not int or not 0<port<65536:raise ValueError()
                self.port=port
            except Exception:
                self.close();raise ValueError('Website bridge could not start. Check Node 22+ and bundled runtime files.') from None
    def connection(self,method,path,body=None):
        if not self.process or self.process.poll() is not None:raise ValueError('Connect your website account first')
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=620)
        raw=json.dumps(body).encode() if body is not None else None
        try:
            conn.request(method,path,body=raw,headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
            response=conn.getresponse()
            if response.status!=200:
                if path.startswith('/history'):raise ValueError('Website history could not be loaded. Saved chats are unchanged; refresh history and try again.')
                if response.status==503:raise ValueError('A system Chrome or Chromium browser is required. Nothing has been installed.')
                raise ValueError('Website connection failed. Reconnect and start a new chat before retrying.')
            return conn,response
        except Exception:conn.close();raise
    def login(self,browser=''):
        conn,response=self.connection('POST','/login')
        try:return json.loads(response.read(16000))
        finally:conn.close()
    def history(self,ident=None):
        path='/history' if ident is None else '/history/'+__import__('urllib.parse',fromlist=['quote']).quote(ident,safe='')
        conn,response=self.connection('GET',path)
        try:
            raw=response.read(3_000_001)
            if len(raw)>3_000_000:raise ValueError('History exceeds the import limit')
            return json.loads(raw)
        finally:conn.close()
    def stream(self,payload):
        conn,response=self.connection('POST','/chat',payload)
        try:
            while True:
                line=response.readline(1_000_001)
                if len(line)>1_000_000:raise ValueError('Website response frame exceeded the display limit')
                if not line:raise ValueError('Website stream ended before completion')
                if not line.startswith(b'data: '):continue
                value=line[6:].strip()
                if value==b'[DONE]':return
                event=json.loads(value)
                if 'error' in event:raise ValueError('Website request failed or login expired; partial output is saved')
                yield event
        finally:conn.close()
    def close(self):
        with self.lock:
            if self.process:
                try:
                    self.process.stdin.close();self.process.wait(timeout=4)
                except (OSError,subprocess.TimeoutExpired):
                    self.process.kill();self.process.wait(timeout=3)
                for pipe in (self.process.stdout,self.process.stderr):
                    if pipe:pipe.close()
            self.process=None;self.port=None;self.key=''
    def forget(self):
        self.close()
        if self.directory.exists():shutil.rmtree(self.directory)

class WebChats:
    def __init__(self,core,bridge=None):
        self.core=core;self.store=core.store;self.lock=threading.RLock();self.bridge=bridge or WebsiteBridge(self.store.directory/'website-account')
        self.connection_status='disconnected';self.connection_error='';self.active=None;self.login_active=False;self.history_syncing=False;self.history_error=''
        self.browser_path=(self.store.list('web_config',limit=1) or [{}])[0].get('browser','')
        for s in self.store.list('web_session'):
            if s['status']=='running':
                s.update(status='interrupted',error='Service restarted during a website request. Start a new chat; no request was replayed.');self.store.put('web_session',s)
    def state(self):
        with self.lock:
            return dict(connection=self.connection_status,error=self.connection_error,active=self.active,login_active=self.login_active,browser=self.browser_path,
             sessions=[{k:s.get(k) for k in ('id','title','created','status','conversation')} for s in self.store.list('web_session',limit=100)],
             usage='unknown',tools=False,history_import=True,history_syncing=self.history_syncing,history_error=self.history_error,remote_sessions=(self.store.list('web_remote_index',limit=1) or [{}])[0].get('sessions',[]),history_limited=(self.store.list('web_remote_index',limit=1) or [{}])[0].get('limited',False))
    def connect(self,browser=''):
        if not isinstance(browser,str) or len(browser)>2000 or (browser and (not Path(browser).is_absolute() or not Path(browser).is_file())):raise ValueError('Choose an existing absolute browser executable path')
        with self.lock:
            if self.active or self.login_active or self.history_syncing:raise ValueError('Wait for the current website operation')
            self.browser_path=browser;self.store.put('web_config',{'browser':browser},'default')
            self.connection_status='connecting';self.connection_error='';self.login_active=True;self.store.delete('web_remote_index','current')
        def work():
            try:
                with self.lock:
                    if self.connection_status!='connecting':return
                    self.bridge.start(browser)
                self.bridge.login(browser)
                with self.lock:
                    if self.connection_status!='connecting':return
                    self.connection_status='connected'
                self.core.event('website_connection',{'status':'connected'});self._load_index()
            except Exception as exc:
                with self.lock:
                    self.connection_status='disconnected'
                    # Only our known local errors are suitable for presentation.
                    self.connection_error=str(exc) if isinstance(exc,ValueError) else 'Website login failed. Check the browser and try connecting again.'
                self.core.event('website_connection',{'status':'failed'})
            finally:
                with self.lock:
                    self.login_active=False
                    if self.connection_status=='stopping':self.connection_status='disconnected'
        threading.Thread(target=work,daemon=True).start();return self.state()
    def _load_index(self):
        try:
            result=self.bridge.history()
            with self.lock:
                if self.connection_status!='connected':return
                self.store.put('web_remote_index',dict(sessions=result['sessions'],limited=result.get('limited',False),updated=time.time()),'current');self.history_error=''
            self.core.event('website_history_index',dict(count=len(result['sessions'])))
        except Exception:
            self.history_error='Website history could not be loaded. Saved chats are unchanged. Use Refresh website history to try again.'
    def sync_history(self):
        with self.lock:
            if self.connection_status!='connected':raise ValueError('Connect your website account first')
            if self.active or self.login_active or self.history_syncing:raise ValueError('Wait for the current website operation')
            self.history_syncing=True
        def work():
            try:self._load_index()
            finally:
                with self.lock:self.history_syncing=False
        threading.Thread(target=work,daemon=True).start();return self.state()
    def read_history(self,ident):
        with self.lock:
            if self.connection_status!='connected':raise ValueError('Reconnect to read website history')
            if self.active or self.login_active or self.history_syncing:raise ValueError('Wait for the current website operation')
            rows=(self.store.list('web_remote_index',limit=1) or [{}])[0].get('sessions',[])
            row=next((r for r in rows if r['id']==ident),None)
            if not row:raise ValueError('Refresh history and choose a listed conversation')
            self.history_syncing=True
        try:
            result=self.bridge.history(ident)
            web_artifacts.capture(self.core,'remote:'+ident,result['messages'])
            return dict(id=ident,title=row['title'],messages=result['messages'],status='imported',read_only=True,notice=result['notice'],options=dict(model=MODELS[0],thinking='auto',search=False))
        finally:
            with self.lock:self.history_syncing=False
    def new(self):
        return self.store.put('web_session',dict(title='New website chat',created=time.time(),messages=[],status='idle',error='',conversation='',options=dict(model=MODELS[0],thinking='auto',search=False),draft=''))
    def session(self,sid):return self.store.get('web_session',sid)
    def submit(self,sid,text,model=MODELS[0],thinking='auto',search=False,instructions=''):
        if model not in MODELS or thinking not in ('auto','on','off') or type(search) is not bool:raise ValueError('Invalid website chat controls')
        if model==MODELS[1] and search:raise ValueError('Website search is available on Flash only')
        if not isinstance(text,str) or not text.strip() or len(text)>20000:raise ValueError('Enter a message of up to 20,000 characters')
        if not isinstance(instructions,str) or len(instructions)>8000:raise ValueError('Chat instructions must be at most 8,000 characters')
        with self.lock:
            if self.connection_status!='connected':raise ValueError('Connect your website account first')
            if self.active or self.login_active or self.history_syncing:raise ValueError('One website request can run at a time')
            session=self.session(sid)
            if session['status'] in ('interrupted','failed','cancelled'):raise ValueError('This chat has an incomplete turn. Start a new chat to avoid replaying it.')
            messages=[dict(role=m['role'],content=m['content']) for m in session['messages']]
            clean=self.core.redact(text.strip());messages.append(dict(role='user',content=clean))
            messages.insert(0,dict(role='system',content=self.core.redact(instructions.strip())+'\n'+web_artifacts.HINT+'\n'+drawing.HINT+'\n'+interactive.HINT))
            if len(messages)>300 or len(json.dumps(messages).encode())>750000:raise ValueError('Website chat context limit reached. Start a new chat; existing messages remain saved.')
            from .reasoning import choose
            route=choose(clean,len(messages)-1,4096)
            enabled=thinking=='on' or (thinking=='auto' and (route['effort'] in ('high','max') or (route['effort']!='none' and len(clean.split())>15)))
            session.update(status='running',error='',started=time.time(),finished=None,options=dict(model=model,thinking=thinking,search=search),effective_thinking=enabled,instructions=self.core.redact(instructions),draft='')
            session['title']=session['title'] if session['messages'] else clean[:70]
            session['messages'] += [dict(role='user',content=clean),dict(role='assistant',content='',reasoning='')]
            self.store.put('web_session',session);self.active=sid
            payload=dict(model=model,messages=messages,thinking_enabled=enabled,search_enabled=search)
            if session['conversation']:payload['conversation']=session['conversation']
            self.core.event('website_request',dict(session=sid,model=model,thinking=enabled,search=search,usage='unknown'))
        threading.Thread(target=self._run,args=(sid,payload),daemon=True).start();return session
    def _run(self,sid,payload):
        last=0;finished=False;conversation='';text='';thought=''
        try:
            for event in self.bridge.stream(payload):
                with self.lock:
                    session=self.session(sid)
                    if session['status']!='running':return
                    text+=self.core.redact(str(event.get('content','')));thought+=self.core.redact(str(event.get('reasoning','')))
                    if len(text)+len(thought)>500000:raise ValueError('Website output limit reached; partial output is saved')
                    if event.get('conversation'):conversation=str(event['conversation'])[:128]
                    finished=finished or event.get('finish') is True
                    if time.monotonic()-last>.2 or finished:
                        session['messages'][-1].update(content=text,reasoning=thought);self.store.put('web_session',session);last=time.monotonic()
            if not finished or not text.strip() or not conversation:raise ValueError('Website stream did not provide a complete answer and conversation receipt')
            with self.lock:
                session=self.session(sid)
                if session['status']=='running':
                    session['messages'][-1].update(content=text,reasoning=thought);session.update(status='completed',conversation=conversation,finished=time.time());self.store.put('web_session',session)
            web_artifacts.capture(self.core,sid,session['messages'])
            self.core.event('website_response',dict(session=sid,status='completed',usage='unknown',characters=len(text)))
        except Exception:
            with self.lock:
                session=self.session(sid)
                if session['status']=='running':
                    session['messages'][-1].update(content=text,reasoning=thought);session.update(status='failed',finished=time.time(),error='Website request failed or was incomplete. Partial output is saved. Reconnect and start a new chat; nothing was retried.');self.store.put('web_session',session)
                    self.connection_status='disconnected'
            self.core.event('website_response',dict(session=sid,status='incomplete',usage='unknown'))
        finally:
            with self.lock:
                if self.active==sid:self.active=None
    def stop(self):
        with self.lock:
            sid=self.active
            if sid:
                session=self.session(sid);session.update(status='cancelled',finished=time.time(),error='Stopped locally. The website may have processed the request. Start a new chat before sending again.');self.store.put('web_session',session)
            self.connection_status='stopping' if self.login_active else 'disconnected'
        self.bridge.close()
        # Keep active reserved until its worker exits; it must not share a new bridge.
        return self.state()
    def disconnect(self):
        with self.lock:
            if self.active or self.login_active or self.history_syncing:raise ValueError('Finish or stop the website operation first')
            self.bridge.forget();self.connection_status='disconnected';self.connection_error='';self.store.delete('web_remote_index','current')
            for s in self.store.list('web_session'):
                if s['conversation']:s.update(status='interrupted',error='Website credentials were forgotten. Start a new chat after reconnecting.');self.store.put('web_session',s)
        return self.state()
    def dispatch(self,method,data):
        if method=='web_artifacts':return self.store.list('web_artifact',limit=100,session=data['session'])
        if method=='web_artifact':return self.store.get('web_artifact',data['id'])
        if method=='web_edit_artifact':
            with self.lock:
                r=self.store.get('web_artifact',data['id'])
                if data['revision']!=r['revision']:raise ValueError('Artifact changed; reload before editing')
                spec=artifacts.validate(self.core.redact(data['spec']));self.store.put('web_artifact_revision',r,r['id']+'-'+str(r['revision']));r.update(spec=spec,svg=artifacts.svg(spec),revision=r['revision']+1,updated=time.time());return self.store.put('web_artifact',r)
        if method=='web_import_artifact':
            key=data['session']
            if key.startswith('remote:'):
                rows=(self.store.list('web_remote_index',limit=1) or [{}])[0].get('sessions',[])
                if key[7:] not in {r['id'] for r in rows}:raise ValueError('Choose a listed conversation')
            else:self.session(key)
            text=json.dumps(artifacts.validate(self.core.redact(data['spec'])))
            web_artifacts.capture(self.core,key,[dict(role='assistant',content='```deepseek-artifact\n'+text+'\n```')]);return {'saved':True}
        if method=='web_state':return self.state()
        if method=='web_connect':return self.connect(data.get('browser',''))
        if method=='web_history_sync':return self.sync_history()
        if method=='web_history_read':return self.read_history(data['id'])
        if method=='web_new':return self.new()
        if method=='web_session':
            session=self.session(data['id'])
            if session['status']=='completed':web_artifacts.capture(self.core,session['id'],session['messages'])
            return session
        if method=='web_send':return self.submit(data['id'],data['text'],data.get('model',MODELS[0]),data.get('thinking','auto'),data.get('search',False),data.get('instructions',''))
        if method=='web_stop':return self.stop()
        if method=='web_forget':return self.disconnect()
        if method=='web_draft':
            with self.lock:
                session=self.session(data['id']);session['draft']=self.core.redact(str(data['text'])[:20000])
                if 'options' in data:
                    options=data['options'];instructions=data.get('instructions','')
                    if options.get('model') not in MODELS or options.get('thinking') not in ('auto','on','off') or type(options.get('search')) is not bool or (options['model']==MODELS[1] and options['search']):raise ValueError('Invalid website controls')
                    if not isinstance(instructions,str) or len(instructions)>8000:raise ValueError('Chat instructions must be at most 8,000 characters')
                    session.update(options={k:options[k] for k in ('model','thinking','search')},instructions=self.core.redact(instructions))
                return self.store.put('web_session',session)
        raise ValueError('Unknown website method')
