"""Short-lived UI connections to the independently running service."""
import hashlib,json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SERVICE_ROOT=Path(os.environ.get('DEEPSEEK_DESKTOP_SOURCE',ROOT)).resolve()

def directory():return Path(os.environ.get('DEEPSEEK_DESKTOP_DATA',ROOT/'data/desktop')).resolve()

def call(method,data=None):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(45 if method=='web_history_read' else 30);sock.connect(str(directory()/'agent.sock'))
        sock.sendall(json.dumps(dict(method=method,data=data or {})).encode()+b'\n')
        with sock.makefile('rb') as stream:line=stream.readline(32_000_001)
        if len(line)>32_000_000:raise RuntimeError('Response exceeds the desktop display limit')
        result=json.loads(line)
        if not result['ok']:raise RuntimeError(result['error'])
        return result['result']

def ensure_service(_retried=False):
    try:call('state');return
    except (OSError,ValueError):pass
    directory().mkdir(parents=True,exist_ok=True,mode=0o700)
    logfile=directory()/'service.log';logfile.touch(mode=0o600,exist_ok=True);os.chmod(logfile,0o600)
    managed=False;existing=False
    if sys.platform.startswith('linux') and shutil.which('systemd-run'):
        # A transient user unit survives launcher scopes. It is not enabled at boot.
        unit='deepseek-lab-'+hashlib.sha256(str(directory()).encode()).hexdigest()[:12]
        args=['systemd-run','--user','--collect','--quiet','--unit='+unit,'--property=WorkingDirectory='+str(SERVICE_ROOT),'--property=StandardOutput=append:'+str(logfile),'--property=StandardError=append:'+str(logfile),'--setenv=DEEPSEEK_DESKTOP_DATA='+str(directory()),'--setenv=DEEPSEEK_DESKTOP_SOURCE='+str(SERVICE_ROOT)]
        for name in ('DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','XAUTHORITY'):
            if os.environ.get(name):args.append('--setenv='+name+'='+os.environ[name])
        try:
            result=subprocess.run(args+[sys.executable,str(SERVICE_ROOT/'desktop/service.py')],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
            managed=result.returncode==0
            if not managed:
                managed=subprocess.run(['systemctl','--user','is-active','--quiet',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0;existing=managed
        except (OSError,subprocess.TimeoutExpired):pass
    if not managed:
        with open(logfile,'ab',buffering=0) as log:
            subprocess.Popen([sys.executable,str(SERVICE_ROOT/'desktop/service.py')],cwd=SERVICE_ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
    for attempt in range(300):
        if existing and not _retried and attempt and attempt%10==0:
            try:
                if subprocess.run(['systemctl','--user','is-active','--quiet',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode!=0:return ensure_service(_retried=True)
            except (OSError,subprocess.TimeoutExpired):pass
        try:call('state');return
        except (OSError,ValueError):time.sleep(0.1)
    raise RuntimeError('Agent service did not start. See data/desktop/service.log.')

def restart_service():
    old=call('restart_service')['service_pid']
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        try:
            state=call('state')
            if state['service_pid']!=old:return state
        except (OSError,ValueError):ensure_service()
        time.sleep(.1)
    raise RuntimeError('Service restart did not complete. Inspect its local log before trying again.')
