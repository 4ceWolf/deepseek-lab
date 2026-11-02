import unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch
import server

class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        server.DB = Path(self.temp.name)/'test.sqlite3'
        server.KEY = 'secret-unit-test-key'
        server.init()
        self.sid = server.new_session('Test')
    def tearDown(self): self.temp.cleanup(); server.KEY = ''
    def params(self,**kw):
        return dict(session_id=self.sid,prompt='Hello',model='deepseek-flash',effort='low',max_tokens=2048,instructions='Be concise',demo=False,**kw)
    def test_live_roundtrip_logs_exact_request_and_response(self):
        response={'choices':[{'message':{'role':'assistant','content':'Hi','reasoning_content':'sample'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':5}}
        with patch.object(server,'api',return_value=response) as api:
            server.run(self.params())
            server.run(self.params())
            sent=api.call_args.args[1]
            self.assertEqual(len(sent['messages']),4)
            self.assertNotIn('reasoning_content',sent['messages'][2])
        events=server.export()['events']
        self.assertEqual([e['kind'] for e in events],['session_created','route','request','response','validation','route','request','response','validation'])
        self.assertEqual(events[3]['payload']['response'],response)
    def test_failure_preserved_and_no_partial_history(self):
        with patch.object(server,'api',side_effect=RuntimeError('failed secret-unit-test-key')):
            with self.assertRaises(RuntimeError): server.run(self.params())
        data=server.export()
        self.assertEqual(data['events'][-1]['kind'],'error')
        self.assertNotIn(server.KEY,json.dumps(data))
        self.assertEqual(server.get_session(self.sid)['messages'],[])
        self.assertNotIn(self.sid,server.BUSY)
    def test_demo_never_calls_provider(self):
        p=self.params();p['demo']=True
        with patch.object(server,'api') as api:
            server.run(p);api.assert_not_called()
        self.assertTrue(server.get_session(self.sid)['messages'][-1]['demo'])
    def test_unconnected_and_bad_budget_do_not_submit(self):
        server.KEY=''
        with self.assertRaises(ValueError):server.run(self.params())
        p=self.params();p['max_tokens']=100000
        with self.assertRaises(ValueError):server.run(p)
        self.assertEqual(len(server.export()['events']),1)
    def test_secret_redaction_in_all_persisted_content(self):
        p=self.params();p.update(demo=True,prompt=server.KEY,instructions=server.KEY)
        server.run(p)
        self.assertNotIn(server.KEY,server.DB.read_bytes().decode('latin1'))

if __name__=='__main__':unittest.main()
