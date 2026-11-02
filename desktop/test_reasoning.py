"""Effort policy and actual outgoing requests; no live provider calls."""
import tempfile,time,unittest
from pathlib import Path
from desktop import reasoning
from desktop.core import Core
from desktop.test_desktop import FakeCredentials,reply,tool

class ReasoningPolicyTests(unittest.TestCase):
    def test_proofs_and_detailed_technical_work_receive_high_effort(self):
        self.assertEqual(reasoning.choose('Prove the algorithm terminates for every finite input',0,4096)['effort'],'high')
        self.assertEqual(reasoning.choose('Implement the system\n- preserve interface\n- handle cancellation\n- save state\n- verify restart',0,4096)['effort'],'high')
        self.assertEqual(reasoning.choose('Use maximum reasoning for this scheduling problem',0,4096)['effort'],'max')
    def test_small_work_avoids_forced_max_and_failure_does_not_inflate_greetings(self):
        self.assertEqual(reasoning.choose('hello',0,4096,{'verification_failed':True})['effort'],'none')
        self.assertEqual(reasoning.choose('Rename this variable',0,4096)['effort'],'low')
        self.assertNotEqual(reasoning.choose('Do not use maximum reasoning for this small question',0,4096)['effort'],'max')
        self.assertEqual(reasoning.choose('Translate the word theorem into Urdu',0,4096)['effort'],'none')
        self.assertEqual(reasoning.choose('Fix the last failing edge case',3,4096,{'verification_failed':True})['effort'],'high')
    def test_permissions_and_timeouts_do_not_trigger_reasoning_escalation(self):
        for result in (dict(status='denied',exit_code=None),dict(status='finished',exit_code=-9,note='Command timed out')):
            run=dict(config={'effort':'auto'},route={'effort':'low'});reasoning.observe_check(run,result);self.assertEqual(run['route']['effort'],'low')
        run=dict(config={'effort':'low'},route={'effort':'low'});reasoning.observe_check(run,dict(status='finished',exit_code=1));self.assertEqual(run['route']['effort'],'low')
    def test_check_failure_escalates_next_payload_and_manual_max_uses_ceiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);project=root/'project';project.mkdir();(project/'code.py').write_text('answer=1\n');core=Core(root/'state',FakeCredentials(),lambda _:reply());core.workspace.update({'project':str(project),'permission':'full'});calls=[]
            def provider(payload):
                calls.append(payload)
                return reply('',[tool('run_check',dict(command='python3 -c "raise SystemExit(1)"',cwd='.',timeout=5,paths=['code.py']))]) if len(calls)==1 else reply('The check failed; investigate the boundary case.')
            def wait(run):
                until=time.monotonic()+5
                while time.monotonic()<until:
                    result=core.store.get('run',run['id'])
                    if result['status'] not in ('running','waiting_approval','stopping'):return result
                    time.sleep(.02)
                self.fail('Provider loop timed out')
            core.provider=provider;run=wait(core.submit(core.new_session()['id'],'Check this function'));self.assertEqual(calls[0]['reasoning_effort'],'low');self.assertEqual(calls[1]['reasoning_effort'],'high');self.assertEqual(run['reasoning_escalations'],1);self.assertEqual(calls[1]['max_tokens'],4096)
            core.workspace.update({'effort':'max','max_tokens':131072});calls.clear();core.provider=lambda p:calls.append(p) or reply();result=wait(core.submit(core.new_session()['id'],'A difficult proof'));self.assertEqual(result['status'],'completed');self.assertEqual(calls[0]['reasoning_effort'],'max');self.assertEqual(calls[0]['max_tokens'],131072)
if __name__=='__main__':unittest.main()
