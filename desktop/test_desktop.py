"""Offline backend integration tests; no API, keyring writes or app installation."""
import json,os,socket,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from desktop.core import Core
from desktop.store import Store
from desktop.commands import Commands
from desktop.credentials import Credentials
from desktop.workspace import Workspace,digest
from desktop.service import create_server
from desktop import client

class FakeCredentials:
    def __init__(self):self.value='test-api-secret'
    def load(self):return self.value
    def save(self,key):self.value=key
    def remove(self):self.value=''

def reply(content='Done',calls=None,reasoning='brief',finish='stop'):
    message=dict(role='assistant',content=content,reasoning_content=reasoning)
    if calls:message['tool_calls']=calls
    return dict(choices=[dict(message=message,finish_reason=finish)],usage=dict(prompt_tokens=20,completion_tokens=10,total_tokens=30,completion_tokens_details=dict(reasoning_tokens=3)))
def tool(name,args,ident='call-1'):return dict(id=ident,type='function',function=dict(name=name,arguments=json.dumps(args)))

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.project=self.root/'project';self.project.mkdir();self.docs=self.root/'docs';self.docs.mkdir()
        (self.docs/'guide.md').write_text('# Example\nUse small patches.');(self.project/'module.py').write_text('x = 1\n')
        self.core=Core(self.root/'state',FakeCredentials(),lambda _:reply());self.core.workspace.update(dict(project=str(self.project),docs=str(self.docs)))
    def tearDown(self):
        for cancel in list(self.core.cancels.values()):cancel.set()
        for ident in list(self.core.commands.processes):self.core.commands.stop(ident)
        self.temp.cleanup()
    def wait_run(self,ident,timeout=5):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            run=self.core.store.get('run',ident)
            if run['status'] not in ('running','waiting_approval','stopping'):return run
            time.sleep(.02)
        self.fail('Run did not finish')
    def test_disabled_commands_never_spawn(self):
        marker=self.project/'marker';command=self.core.commands.request('touch '+str(marker),self.project,'disabled')
        self.assertEqual(command['status'],'denied');self.assertFalse(marker.exists())
    def test_environment_is_delivered_to_provider_and_refreshed_between_rounds(self):
        payloads=[]
        def provider(payload):
            payloads.append(payload)
            if len(payloads)==1:
                self.core.workspace.update({'permission':'disabled','dev_mode':True})
                return reply('',[tool('get_environment',{})])
            return reply('Environment received.')
        self.core.provider=provider;session=self.core.new_session();run=self.core.submit(session['id'],'Check the environment');self.assertEqual(self.wait_run(run['id'])['status'],'completed');self.assertEqual(len(payloads),2)
        def context(payload):return json.loads(payload['messages'][0]['content'].split('Observed environment (refreshed for this request):\n')[1])
        first,second=map(context,payloads);self.assertEqual(first['paths']['project'],str(self.project));self.assertEqual(first['paths']['docs'],str(self.docs));self.assertEqual(first['commands']['permission'],'approve');self.assertEqual(second['commands']['permission'],'disabled');self.assertTrue(second['dev_mode']);self.assertEqual(second['reasoning'],run['route']['effort']);self.assertIn('system',second['os'])
        response=json.loads(next(m['content'] for m in payloads[1]['messages'] if m['role']=='tool'));self.assertEqual(response['commands']['permission'],'disabled');self.assertIn('local display only',response['capabilities']['images']);self.assertNotIn('test-api-secret',json.dumps(payloads));self.assertNotIn('api_key',response)
        inspected=self.core.dispatch('instructions',{})['text'];self.assertIn('Observed environment:',inspected);self.assertIn(str(self.project),inspected)
    def test_exact_approval_input_output_and_exit(self):
        command=self.core.commands.request("printf 'ready\\n'; read answer; printf 'got:%s\\n' \"$answer\"",self.project,'approve')
        self.assertEqual(command['status'],'awaiting_approval')
        with self.assertRaises(ValueError):self.core.commands.decide(command['id'],True,'wrong-hash')
        self.core.commands.decide(command['id'],True,command['fingerprint'])
        deadline=time.monotonic()+3
        while command['id'] not in self.core.commands.processes and time.monotonic()<deadline:time.sleep(.01)
        self.core.commands.input(command['id'],'yes\n');result=self.core.commands.wait(command['id'])
        self.assertIn('got:yes',result['output']);self.assertEqual(result['exit_code'],0)
        self.assertEqual(result['inputs'][0]['text'],'yes\n');self.assertIsNotNone(result['finished'])
    def test_ask_is_narrow_and_full_runs(self):
        self.assertEqual(self.core.commands.request('echo ask',self.project,'ask')['status'],'awaiting_approval')
        read=self.core.commands.request('pwd',self.project,'ask');self.assertEqual(self.core.commands.wait(read['id'])['exit_code'],0)
        command=self.core.commands.request('printf full',self.project,'full');self.assertIn('full',self.core.commands.wait(command['id'])['output'])
    def test_timeout_and_stop_are_real(self):
        command=self.core.commands.request('sleep 10',self.project,'full',timeout=1)
        result=self.core.commands.wait(command['id']);self.assertEqual(result['note'],'Command timed out');self.assertNotEqual(result['exit_code'],0)
    def test_docs_and_memory_scope_and_escape(self):
        self.assertIn('guide.md',self.core.workspace.files(docs=True));self.assertTrue(self.core.workspace.search_docs('small'))
        with self.assertRaises(ValueError):self.core.workspace.read('../docs/guide.md')
        (self.project/'escape').symlink_to(self.docs/'guide.md')
        with self.assertRaises(ValueError):self.core.workspace.read('escape')
        self.core.workspace.remember('Preference','Use concise answers','personal')
        self.core.workspace.remember('Project fact','Test with pytest','project')
        self.assertEqual(len(self.core.workspace.memories()),2)
        self.assertEqual(len(self.core.workspace.memories(project='/other')),1)
    def test_proposals_detect_drift_and_need_explicit_apply(self):
        proposal=self.core.workspace.proposal('module.py','x = 2\n')
        self.assertEqual((self.project/'module.py').read_text(),'x = 1\n')
        (self.project/'module.py').write_text('user edit')
        with self.assertRaises(ValueError):self.core.workspace.apply_proposal(proposal['id'])
        proposal=self.core.workspace.proposal('module.py','x = 3\n');self.core.workspace.apply_proposal(proposal['id'])
        self.assertEqual((self.project/'module.py').read_text(),'x = 3\n')
    def test_tool_round_retains_reasoning_and_true_results(self):
        payloads=[]
        def provider(payload):
            payloads.append(json.loads(json.dumps(payload)))
            return reply('',[tool('read_file',{'path':'module.py'})]) if len(payloads)==1 else reply('Read x = 1.')
        self.core.provider=provider;session=self.core.new_session();run=self.core.submit(session['id'],'Inspect the module')
        result=self.wait_run(run['id']);self.assertEqual(result['status'],'completed')
        self.assertTrue(any(m.get('reasoning_content')=='brief' for m in payloads[1]['messages']))
        self.assertTrue(any(m['role']=='tool' and 'x = 1' in m['content'] for m in payloads[1]['messages']))
        self.assertEqual(result['usage']['total_tokens'],60)
    def test_drafts_survive_reply_and_round_budget(self):
        entered=threading.Event();release=threading.Event()
        def provider(_):entered.set();release.wait(3);return reply()
        self.core.provider=provider;session=self.core.new_session();run=self.core.submit(session['id'],'Work')
        self.assertTrue(entered.wait(2));self.core.dispatch('draft',{'id':session['id'],'text':'Next question'})
        release.set();self.wait_run(run['id']);self.assertEqual(self.core.store.get('session',session['id'])['draft'],'Next question')
        self.core.workspace.update({'max_rounds':1});self.core.provider=lambda _:reply('',[tool('list_files',{})])
        next_run=self.core.submit(session['id'],'Continue');self.assertEqual(self.wait_run(next_run['id'])['status'],'round_limit')
    def test_redaction_and_restart_preserve_data_without_retry(self):
        self.core.event('sample',{'text':'test-api-secret','authorization':'hidden'})
        self.assertNotIn('test-api-secret',json.dumps(self.core.store.events()))
        session=self.core.new_session();session['messages']=[dict(role='assistant',content='',tool_calls=[tool('list_files',{})],reasoning_content='brief')];self.core.store.put('session',session)
        self.core.store.put('run',dict(session=session['id'],status='running'))
        other=Core(self.root/'state',FakeCredentials(),lambda _:self.fail('Should not retry'))
        self.assertEqual(other.store.list('run')[0]['status'],'interrupted')
        self.assertEqual(other.store.get('session',session['id'])['messages'][-1]['role'],'tool')
    def test_native_reconnect_does_not_own_the_run(self):
        entered=threading.Event();release=threading.Event()
        def provider(_):entered.set();release.wait(3);return reply('Survived reconnect')
        self.core.provider=provider;server=create_server(self.root/'state',self.core)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def rpc(method,data=None):
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                sock.connect(str(self.root/'state/agent.sock'));sock.sendall(json.dumps(dict(method=method,data=data or {})).encode()+b'\n')
                with sock.makefile('rb') as stream:return json.loads(stream.readline())['result']
        try:
            session=rpc('new_session');run=rpc('submit',dict(session=session['id'],prompt='Stay running'))
            self.assertTrue(entered.wait(2));self.assertTrue(rpc('state')['runs'])
            self.assertEqual(os.stat(self.root/'state/agent.sock').st_mode&0o777,0o600)
            release.set();self.assertEqual(self.wait_run(run['id'])['status'],'completed')
            self.assertIn('Survived reconnect',json.dumps(rpc('session',{'id':session['id']})))
        finally:release.set();server.shutdown();server.server_close();thread.join(2)
    def test_service_restart_rejects_pending_approval(self):
        command=self.core.commands.request('printf waiting',self.project,'approve')
        server=create_server(self.root/'state',self.core);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                sock.connect(str(self.root/'state/agent.sock'));sock.sendall(b'{"method":"restart_service"}\n')
                with sock.makefile('rb') as stream:result=json.loads(stream.readline())
            self.assertFalse(result['ok']);self.assertIn('pending',result['error'])
            self.core.commands.decide(command['id'],False,command['fingerprint'])
        finally:server.shutdown();server.server_close();thread.join(2)
    def test_idle_restart_drains_before_shutdown(self):
        server=create_server(self.root/'state',self.core);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                sock.connect(str(self.root/'state/agent.sock'));sock.sendall(b'{"method":"restart_service"}\n')
                with sock.makefile('rb') as stream:result=json.loads(stream.readline())
            self.assertTrue(result['ok']);self.assertTrue(self.core.draining)
            with self.assertRaises(ValueError):self.core.dispatch('command',dict(command='printf refused'))
            thread.join(2);self.assertFalse(thread.is_alive())
        finally:
            if thread.is_alive():server.shutdown()
            server.server_close()
    def test_restart_client_waits_for_old_service_to_disappear(self):
        events=[];states=iter([{'service_pid':11},OSError('old socket closed'),{'service_pid':22}])
        def rpc(method,data=None):
            if method=='restart_service':events.append('requested');return {'service_pid':11}
            value=next(states)
            if isinstance(value,Exception):events.append('old_closed');raise value
            events.append('polled');return value
        with patch.object(client,'call',side_effect=rpc),patch.object(client,'ensure_service',side_effect=lambda:events.append('ensure')),patch.object(client.time,'sleep'):
            self.assertEqual(client.restart_service()['service_pid'],22)
        self.assertLess(events.index('old_closed'),events.index('ensure'))
    def test_dev_stages_never_touch_live_until_user_activation(self):
        with patch('desktop.workspace.APP',self.project):
            (self.project/'desktop').mkdir();(self.project/'desktop/ui.py').write_text('value = 1\n');(self.project/'engine.py').write_text('')
            self.core.workspace.update({'dev_mode':True});stage=self.core.workspace.new_stage()
            self.core.workspace.stage_patch(stage['id'],'desktop/ui.py','value = 2\n')
            with self.assertRaises(ValueError):self.core.workspace.stage_patch(stage['id'],'desktop/../engine.py','changed = True')
            self.assertEqual((self.project/'desktop/ui.py').read_text(),'value = 1\n')
            self.assertIn('value = 2',self.core.workspace.stage_diff(stage['id'])['diff'])
            self.core.workspace.activate_stage(stage['id']);self.assertEqual((self.project/'desktop/ui.py').read_text(),'value = 2\n')
            self.core.workspace.rollback_stage(stage['id']);self.assertEqual((self.project/'desktop/ui.py').read_text(),'value = 1\n')
    def test_key_persistence_is_secret_service_only(self):
        with patch('desktop.credentials.subprocess.run') as run:
            run.return_value.returncode=0;run.return_value.stdout='loaded'
            keys=Credentials();keys.save('new-secret');self.assertEqual(keys.load(),'loaded');keys.remove()
            self.assertEqual(run.call_args_list[0].kwargs['input'],'new-secret')
            self.assertNotIn('new-secret',str(run.call_args_list[0].args))
    def test_key_cannot_leak_through_drafts_memory_or_commands(self):
        session=self.core.new_session();self.core.dispatch('draft',{'id':session['id'],'text':'test-api-secret'})
        self.core.dispatch('remember',dict(title='Note',body='test-api-secret'))
        run=self.core.submit(session['id'],'Please use test-api-secret');self.wait_run(run['id'])
        with self.assertRaises(ValueError):self.core.dispatch('command',dict(command='echo test-api-secret'))
        self.assertNotIn('test-api-secret',json.dumps(self.core.store.list('session')+self.core.store.list('memory')+self.core.store.events()))
    def test_model_cannot_change_permissions_or_activate_stages(self):
        run=dict(config=self.core.workspace.settings())
        for name in ('settings','activate_stage','decide_command'):
            with self.assertRaises(ValueError):self.core.tool(name,{},run,threading.Event())
        self.assertEqual(self.core.workspace.settings()['permission'],'approve')
    def test_command_does_not_follow_replaced_directory(self):
        command=self.core.commands.request('printf should-not-run',self.project,'approve')
        moved=self.root/'moved';self.project.rename(moved);self.project.symlink_to(self.docs,target_is_directory=True)
        self.core.commands.decide(command['id'],True,command['fingerprint'])
        result=self.core.commands.wait(command['id']);self.assertEqual(result['status'],'error');self.assertNotIn('should-not-run',result['output'])

if __name__=='__main__':unittest.main()
