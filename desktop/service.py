"""Private Unix-socket service. Closing/reloading the desktop window does not stop it."""
import fcntl,json,os,socketserver,sys,threading
from pathlib import Path
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop.core import Core

def create_server(directory,core):
    address=Path(directory)/'agent.sock';address.unlink(missing_ok=True)
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                line=self.rfile.readline(2_000_001)
                if len(line)>2_000_000:raise ValueError('Request exceeds 2 MB')
                request=json.loads(line)
                if request['method']=='restart_service':
                    with core.lock:
                        pending=any(c['status'] in ('running','queued','awaiting_approval','stopping') for c in core.store.list('command'))
                        if core.active() or pending or core.web.active or core.web.login_active or core.web.history_syncing:raise ValueError('Finish or stop pending tasks, website requests and commands before restarting the service')
                        core.draining=True
                        result={'service_pid':os.getpid(),'restarting':True}
                        threading.Thread(target=self.server.shutdown,daemon=True).start()
                else:result=core.dispatch(request['method'],request.get('data',{}))
                response={'ok':True,'result':core.redact(result)}
            except Exception as exc:response={'ok':False,'error':core.redact(str(exc))}
            try:self.wfile.write(json.dumps(response).encode()+b'\n')
            except (BrokenPipeError,ConnectionResetError):pass
    class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
    server=Server(str(address),Handler);os.chmod(address,0o600);return server

def main():
    root=Path(__file__).resolve().parents[1]
    directory=Path(os.environ.get('DEEPSEEK_DESKTOP_DATA',root/'data/desktop')).resolve()
    directory.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(directory,0o700)
    lock=open(directory/'service.lock','w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return
    core=Core(directory)
    try:
        with create_server(directory,core) as server:server.serve_forever()
    finally:core.web.bridge.close()

if __name__=='__main__':main()
