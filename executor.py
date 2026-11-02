"""Fail-closed bubblewrap executor; never falls back to unsandboxed execution."""
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def equal_json(actual,expected):
 if type(actual) is bool or type(expected) is bool:return type(actual) is type(expected) and actual==expected
 if isinstance(actual,(int,float)) and isinstance(expected,(int,float)):return actual==expected
 if type(actual) is not type(expected):return False
 if isinstance(expected,list):return len(actual)==len(expected) and all(equal_json(a,b) for a,b in zip(actual,expected))
 if isinstance(expected,dict):return actual.keys()==expected.keys() and all(equal_json(actual[k],v) for k,v in expected.items())
 return actual==expected

def sandbox_command(work):
 # In this Flatpak runtime bwrap is on the host, where project paths also exist.
 if Path('/.flatpak-info').exists():prefix=['flatpak-spawn','--host']
 elif shutil.which('bwrap'):prefix=[]
 else:raise RuntimeError('bubblewrap unavailable; refusing unsandboxed execution')
 return prefix+['timeout','--kill-after=1','6','bwrap','--unshare-all','--die-with-parent','--new-session',
  '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64',
  '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(work),'/work',
  '--ro-bind',str(ROOT/'execution_worker.py'),'/runner.py','--clearenv',
  '--setenv','PATH','/usr/bin','--setenv','HOME','/tmp','--chdir','/work',
  '/usr/bin/python3','-I','/runner.py']

def validate_cases(function,cases):
 if not isinstance(function,str) or not function.isidentifier() or function.startswith('_'):raise ValueError('Use a public function name')
 if not isinstance(cases,list) or not 1<=len(cases)<=2000:raise ValueError('Supply 1–2000 test cases')
 if len(json.dumps(cases,allow_nan=False).encode())>200000:raise ValueError('Test data exceeds 200 KB')
 for c in cases:
  if not isinstance(c,dict) or not isinstance(c.get('args'),list):raise ValueError('Each case needs an args array')
  if ('expected' in c)==('raises' in c):raise ValueError('Each case needs exactly one of expected or raises')
  if 'raises'in c and c['raises'] not in ('ValueError','TypeError','StopIteration'):raise ValueError('Unsupported expected exception')

def verify(code,function,cases):
 validate_cases(function,cases)
 if not isinstance(code,str) or len(code.encode())>50000:raise ValueError('Candidate exceeds 50 KB')
 # Shared project path is visible to host bwrap; generic /tmp inside Flatpak is not.
 base=ROOT/'data/executor-tmp';base.mkdir(mode=0o700,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=base) as folder:
  work=Path(folder);(work/'module.py').write_text(code)
  # Output files stay outside the read-only mounted work directory.
  with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
   try:
    launcher_env={k:os.environ[k] for k in ('PATH','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR') if k in os.environ}
    proc=subprocess.run(sandbox_command(work),input=json.dumps({'function':function,'inputs':[c['args'] for c in cases]},allow_nan=False).encode(),stdout=stdout,stderr=stderr,timeout=9,env=launcher_env)
   except subprocess.TimeoutExpired:return {'pass':False,'status':'timeout','cases':len(cases)}
   stdout.seek(0);body=stdout.read(1048577);stderr.seek(0);err=stderr.read(2000).decode(errors='replace')
   if proc.returncode!=0:return {'pass':False,'status':'execution_failed','exit_code':proc.returncode,'detail':err or body[:1000].decode(errors='replace'),'cases':len(cases)}
   try:
    response=json.loads(body)
    results=response['results']
    if len(results)!=len(cases):raise ValueError('Wrong result count')
   except (ValueError,KeyError,TypeError):return {'pass':False,'status':'invalid_worker_output','cases':len(cases)}
 failures=[]
 for i,(case,result) in enumerate(zip(cases,results)):
  ok=(result.get('exception')==case['raises']) if 'raises'in case else ('value'in result and equal_json(result['value'],case['expected']))
  if case.get('immutable') and result.get('mutated'):ok=False
  if not ok:failures.append({'case':i,'args':case['args'],'expected':case.get('expected'),'raises':case.get('raises'),'actual':result})
 return {'pass':not failures,'status':'passed_supplied_tests' if not failures else 'failed_tests','cases':len(cases),'failures':failures[:20],'failure_count':len(failures),'source_sha256':hashlib.sha256(code.encode()).hexdigest(),'scope':'JSON-compatible pure functions only; passing supplied cases is not proof of general correctness.'}
