import json,tempfile,unittest,os,subprocess
from pathlib import Path
from unittest.mock import patch
import executor,coding_agent

class ExecutorTests(unittest.TestCase):
 def test_os_boundary_has_no_host_home_network_or_work_writes(self):
  base=executor.ROOT/'data/executor-tmp';base.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=base) as folder:
   work=Path(folder);(work/'module.py').write_text('original')
   probe='''import os,socket,json
r={'home_hidden':not os.path.exists('/home/user'),'clean_env':set(os.environ)<= {'PATH','HOME','LC_CTYPE','PWD'} and os.environ.get('PWD')=='/work' and os.environ.get('HOME')=='/tmp'}
try:
 open('/work/module.py','w').write('changed');r['readonly']=False
except OSError:r['readonly']=True
s=socket.socket();s.settimeout(0.3)
try:
 s.connect(('127.0.0.1',8765));r['network_isolated']=False
except OSError:r['network_isolated']=True
print(json.dumps(r))
'''
   cmd=executor.sandbox_command(work)[:-1]+['-c',probe]
   env={k:os.environ[k] for k in ('PATH','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR') if k in os.environ}
   result=subprocess.run(cmd,capture_output=True,text=True,timeout=9,env=env)
   self.assertEqual(result.returncode,0,result.stderr)
   checks=json.loads(result.stdout);self.assertTrue(all(checks.values()),checks)
   self.assertEqual((work/'module.py').read_text(),'original')
 def test_boolean_is_not_mistaken_for_integer(self):
  self.assertFalse(executor.verify('def f(): return True','f',[{'args':[],'expected':1}])['pass'])
 def test_correctness_and_mutation_checked_outside_worker(self):
  self.assertTrue(executor.verify('def f(x): return x+1','f',[{'args':[1],'expected':2}])['pass'])
  result=executor.verify('def f(x): x.append(2); return x','f',[{'args':[[1]],'expected':[1,2],'immutable':True}])
  self.assertFalse(result['pass']);self.assertEqual(result['failure_count'],1)
 def test_io_import_and_introspection_rejected(self):
  for code in ['import os\ndef f(): return 1','def f(): return open("/etc/passwd").read()','def f(): return ().__class__']:
   self.assertFalse(executor.verify(code,'f',[{'args':[],'expected':1}])['pass'])
 def test_nontermination_bounded(self):
  result=executor.verify('def f():\n while True: pass','f',[{'args':[],'expected':1}])
  self.assertFalse(result['pass']);self.assertIn(result['status'],('execution_failed','timeout'))
 def test_worker_never_receives_expected_results(self):
  real=executor.subprocess.run
  with patch.object(executor.subprocess,'run',wraps=real) as run:
   executor.verify('def f(x): return x','f',[{'args':[1],'expected':1}])
  body=json.loads(run.call_args.kwargs['input'])
  self.assertEqual(set(body),{'function','inputs'})
 def test_missing_isolation_fails_closed(self):
  with patch.object(executor,'sandbox_command',side_effect=RuntimeError('unavailable')):
   with self.assertRaises(RuntimeError):executor.verify('def f(): return 1','f',[{'args':[],'expected':1}])

class LoopTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'module.py').write_text('def add(a,b): return a-b\n')
  (self.root/'job.json').write_text(json.dumps({'module':'module.py','contract':'Add numbers.','function':'add','cases':[{'args':[2,3],'expected':5}]}))
  self.patch=patch.object(coding_agent,'ROOT',self.root);self.patch.start()
 def tearDown(self):self.patch.stop();self.temp.cleanup()
 def client(self,outputs):
  self.requests=[]
  def call(path,data=None):
   if path=='state':return {'connected':True}
   if path=='session':return {'id':'test'}
   if path=='note':return {'saved':True}
   self.requests.append(data)
   return {'session':{'messages':[{'content':outputs[len(self.requests)-1],'finish_reason':'stop','usage':{'total_tokens':1},'run_id':'test'}]}}
  return call
 def test_repair_loop_two_attempts_preserves_original(self):
  folder=coding_agent.run_job(self.root/'job.json',True,self.client(['def add(a,b): return a-b','def add(a,b): return a+b']))
  state=json.loads((folder/'state.json').read_text())
  self.assertEqual(state['status'],'proposal_passed_supplied_tests');self.assertEqual(len(self.requests),2)
  self.assertTrue(state['source_unchanged']);self.assertTrue((folder/'proposal.diff').exists())
  self.assertIn('Verifier results',self.requests[1]['prompt'])
 def test_attempt_cap_and_dry_run(self):
  client=self.client(['def add(a,b): return 0']*2)
  folder=coding_agent.run_job(self.root/'job.json',True,client)
  self.assertEqual(json.loads((folder/'state.json').read_text())['status'],'attempt_budget_exhausted')
  self.assertEqual(len(self.requests),2)
  with patch.object(coding_agent,'call',side_effect=AssertionError('No API allowed')):
   folder=coding_agent.run_job(self.root/'job.json',False)
  self.assertEqual(json.loads((folder/'state.json').read_text())['status'],'checked_only')
 def test_provider_failure_records_pending_and_does_not_retry(self):
  client=self.client([])
  with self.assertRaises(IndexError):coding_agent.run_job(self.root/'job.json',True,client)
  files=list((self.root/'data/coding-runs').glob('*/state.json'))
  state=json.loads(files[0].read_text());self.assertEqual(state['pending_attempt'],1)
  self.assertEqual(state['status'],'error_no_automatic_retry');self.assertEqual(len(self.requests),1)
 def test_path_escape_rejected(self):
  (self.root/'job.json').write_text(json.dumps({'module':'../escape.py'}))
  with self.assertRaises(ValueError):coding_agent.load_job(self.root/'job.json')
