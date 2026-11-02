"""Offline website-provider checks. No account, browser, network or paid API."""
import tempfile,threading,time,unittest
from pathlib import Path
from desktop.core import Core
from desktop.test_desktop import FakeCredentials
from desktop.webchat import WebChats

class FakeBridge:
    def __init__(self,events=None,block=False):self.events=events;self.block=block;self.released=threading.Event();self.calls=[];self.closed=False
    def start(self,browser=''):pass
    def login(self,browser=''):return {'ready':True}
    def history(self,ident=None):
        if ident:return dict(messages=[{'role':'user','content':'An older question'},{'role':'assistant','content':'An older answer'}],notice='Imported website history · read-only')
        return dict(sessions=[dict(id='remote-123',title='Older website conversation',updated=123)],limited=False)
    def stream(self,payload):
        self.calls.append(payload)
        if self.events is not None:
            yield from self.events;return
        yield {'content':'Checked answer','reasoning':'Private reasoning'}
        if self.block:self.released.wait(3)
        yield {'finish':True,'conversation':'website-thread'}
    def close(self):self.closed=True;self.released.set()
    def forget(self):self.close()

class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.core=Core(Path(self.tmp.name)/'state',FakeCredentials(),lambda _:self.fail('Website chat must never invoke the API provider'))
        self.bridge=FakeBridge();self.web=WebChats(self.core,self.bridge);self.core.web=self.web;self.web.connection_status='connected'
    def tearDown(self):self.bridge.close();self.wait(lambda:not self.web.active);self.tmp.cleanup()
    def wait(self,predicate):
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.01)
        self.fail('Worker did not finish')
    def send(self,**kw):
        s=self.web.new();self.web.submit(s['id'],'Explain this carefully with several concrete examples and relevant evidence to help me check this technical decision.',**kw);self.wait(lambda:not self.web.active);return self.web.session(s['id'])
    def test_chat_without_api_key_and_separate_history(self):
        self.core.key='';s=self.send(search=True)
        self.assertEqual(s['status'],'completed');self.assertEqual(s['messages'][-1]['content'],'Checked answer');self.assertEqual(s['conversation'],'website-thread')
        self.assertEqual(self.core.store.list('session'),[]);self.assertEqual(self.core.store.list('run'),[]);self.assertEqual(self.core.store.list('command'),[])
        self.assertTrue(self.bridge.calls[0]['search_enabled']);self.assertTrue(self.bridge.calls[0]['thinking_enabled']);self.assertNotIn('tools',self.bridge.calls[0]);self.assertEqual(self.web.state()['usage'],'unknown')
    def test_continuation_and_instructions_keep_real_conversation(self):
        s=self.send(instructions='Be concise')
        self.web.submit(s['id'],'Continue',thinking='off',instructions='Be concise');self.wait(lambda:not self.web.active)
        p=self.bridge.calls[-1];self.assertEqual(p['conversation'],'website-thread');self.assertFalse(p['thinking_enabled']);self.assertEqual(p['messages'][0]['role'],'system');self.assertTrue(p['messages'][0]['content'].startswith('Be concise\n'));self.assertIn('deepseek-artifact',p['messages'][0]['content'])
        self.assertNotIn('Private reasoning',str(p));self.assertEqual(len(p['messages']),4)
    def test_search_pro_rejected_before_any_request(self):
        s=self.web.new()
        with self.assertRaisesRegex(ValueError,'Flash'):self.web.submit(s['id'],'test',model='deepseek-v4-pro',search=True)
        self.assertEqual(self.bridge.calls,[]);self.assertEqual(self.web.session(s['id'])['messages'],[])
    def test_auto_short_message_is_off_manual_on_is_respected(self):
        s=self.web.new();self.web.submit(s['id'],'Hello');self.wait(lambda:not self.web.active);self.assertFalse(self.bridge.calls[-1]['thinking_enabled'])
        self.web.submit(s['id'],'Hello',thinking='on');self.wait(lambda:not self.web.active);self.assertTrue(self.bridge.calls[-1]['thinking_enabled'])
    def test_incomplete_stream_is_saved_and_not_retried(self):
        self.bridge.events=[{'content':'Partial answer'}];s=self.send()
        self.assertEqual(s['status'],'failed');self.assertEqual(s['messages'][-1]['content'],'Partial answer');self.assertEqual(len(self.bridge.calls),1)
        self.web.connection_status='connected'
        with self.assertRaisesRegex(ValueError,'incomplete'):self.web.submit(s['id'],'Retry')
    def test_stopping_blocks_replay_and_preserves_partial_text(self):
        self.bridge.block=True;s=self.web.new();self.web.submit(s['id'],'Work on this')
        self.wait(lambda:bool(self.bridge.calls));self.wait(lambda:self.web.session(s['id'])['messages'][-1]['content']=='Checked answer')
        self.web.stop();self.wait(lambda:not self.web.active);saved=self.web.session(s['id'])
        self.assertEqual(saved['status'],'cancelled');self.assertEqual(saved['messages'][-1]['content'],'Checked answer');self.assertTrue(self.bridge.closed)
    def test_restart_marks_running_turn_interrupted(self):
        s=self.web.new();s.update(status='running');self.core.store.put('web_session',s)
        web=WebChats(self.core,FakeBridge());self.assertEqual(web.session(s['id'])['status'],'interrupted');self.assertEqual(web.state()['connection'],'disconnected')
    def test_forget_removes_login_but_retains_saved_chat(self):
        s=self.send();self.web.disconnect();self.assertTrue(self.bridge.closed)
        self.assertEqual(self.web.session(s['id'])['status'],'interrupted');self.assertEqual(self.web.session(s['id'])['messages'][-1]['content'],'Checked answer')
    def test_login_and_invalid_controls(self):
        self.web.connection_status='disconnected';self.web.connect();self.wait(lambda:self.web.connection_status!='connecting');self.assertEqual(self.web.connection_status,'connected')
        with self.assertRaises(ValueError):self.web.connect('/not-a-real-browser')
        with self.assertRaises(ValueError):self.web.submit(self.web.new()['id'],'',thinking='max')
    def test_logs_do_not_fabricate_usage_or_store_reasoning_as_api_events(self):
        self.send();events=self.core.store.events();self.assertTrue(any(e['kind']=='website_request' for e in events))
        self.assertFalse(any(e['kind']=='provider_request' for e in events));self.assertNotIn('Private reasoning',str(events));self.assertNotIn('prompt_tokens',str(events))

    def test_auto_short_proof_preserves_thinking(self):
        s=self.web.new();self.web.submit(s['id'],'Prove this theorem');self.wait(lambda:not self.web.active);self.assertTrue(self.bridge.calls[-1]['thinking_enabled'])
    def test_login_can_be_stopped_without_late_reconnection(self):
        waiting=threading.Event()
        def login(browser=''):waiting.set();self.bridge.released.wait(3);return {'ready':True}
        self.bridge.login=login;self.web.connection_status='disconnected';self.web.connect();self.wait(waiting.is_set)
        self.web.stop();self.wait(lambda:not self.web.login_active);self.assertEqual(self.web.connection_status,'disconnected');self.assertTrue(self.bridge.closed)

    def test_login_loads_directory_and_selection_reads_without_model_request(self):
        self.web.connect();self.wait(lambda:not self.web.login_active)
        self.assertEqual(self.web.state()['remote_sessions'][0]['id'],'remote-123')
        old=self.web.read_history('remote-123');self.assertTrue(old['read_only']);self.assertEqual(len(old['messages']),2);self.assertEqual(self.bridge.calls,[])
        self.assertEqual(self.core.store.list('session'),[])
        with self.assertRaisesRegex(ValueError,'listed'):self.web.read_history('unknown')
    def test_history_failure_keeps_login_and_local_chats(self):
        local=self.web.new()
        def fail(*args):raise RuntimeError('private provider diagnostics')
        self.bridge.history=fail;self.web.connect();self.wait(lambda:not self.web.login_active)
        self.assertEqual(self.web.connection_status,'connected');self.assertIn('could not be loaded',self.web.history_error);self.assertNotIn('private',self.web.history_error);self.assertEqual(self.web.session(local['id'])['id'],local['id'])
    def test_history_busy_blocks_send_and_forget(self):
        self.web.history_syncing=True
        with self.assertRaises(ValueError):self.web.submit(self.web.new()['id'],'Hi')
        with self.assertRaises(ValueError):self.web.disconnect()
        self.web.history_syncing=False

    def test_website_artifact_capture_is_bounded_validated_and_versioned(self):
        import json
        from desktop.test_artifacts import chart
        spec=chart();self.bridge.events=[{'content':'Here is a chart.\n```deepseek-artifact\n'+json.dumps(spec)+'\n```'},{'finish':True,'conversation':'visual-thread'}]
        s=self.send();rows=self.web.dispatch('web_artifacts',{'session':s['id']});self.assertEqual(len(rows),1);r=rows[0]
        self.assertTrue(r['svg'].startswith('<svg'));self.assertEqual(r['revision'],1)
        spec['title']='Edited chart';n=self.web.dispatch('web_edit_artifact',{'id':r['id'],'revision':1,'spec':spec});self.assertEqual(n['revision'],2)
        with self.assertRaisesRegex(ValueError,'changed'):self.web.dispatch('web_edit_artifact',{'id':r['id'],'revision':1,'spec':spec})
        with self.assertRaises(ValueError):self.web.dispatch('web_import_artifact',{'session':s['id'],'spec':{'kind':'html','title':'Unsafe'}})
        self.assertEqual(self.core.store.list('command'),[])

class BridgeProcessTest(unittest.TestCase):
    def test_bundled_process_starts_privately_without_opening_browser(self):
        import shutil
        from desktop.webchat import WebsiteBridge
        if not shutil.which('node'):self.skipTest('Node runtime is on the host')
        with tempfile.TemporaryDirectory() as folder:
            bridge=WebsiteBridge(Path(folder)/'account')
            try:
                bridge.start();conn,response=bridge.connection('GET','/status')
                try:
                    import json
                    status=json.loads(response.read());self.assertFalse(status['ready']);self.assertFalse(status['busy']);self.assertIsInstance(status['browser_available'],bool)
                finally:conn.close()
                self.assertEqual((Path(folder)/'account').stat().st_mode & 0o777,0o700)
                self.assertFalse((Path(folder)/'account/auth.json').exists())
            finally:bridge.close()

if __name__=='__main__':unittest.main()
