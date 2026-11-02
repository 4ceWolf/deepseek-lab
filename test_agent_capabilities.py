import json,unittest
from unittest.mock import patch
import coding_agent,test_executor

class CapabilityTests(unittest.TestCase):
 setUp=test_executor.LoopTests.setUp
 tearDown=test_executor.LoopTests.tearDown
 client=test_executor.LoopTests.client
 def test_saved_requirements_and_inspection_detect_candidate_tampering(self):
  folder=coding_agent.run_job(self.root/'job.json',True,self.client(['def add(a,b): return a+b']))
  report=coding_agent.inspect_run(folder)
  self.assertFalse(report['evidence_issues'])
  self.assertEqual(report['state']['requirements'][0]['status'],'passed_supplied_cases')
  self.assertEqual(report['state']['remaining_steps'],['review patch'])
  (folder/'candidate-1.py').write_text('def add(a,b): return 999')
  self.assertTrue(coding_agent.inspect_run(folder)['evidence_issues'])
 def test_inspection_checks_review_artifacts_too(self):
  folder=coding_agent.run_job(self.root/'job.json',True,self.client(['def add(a,b): return a+b']))
  (folder/'proposal.diff').write_text('altered patch')
  self.assertIn('Review patch missing or changed',coding_agent.inspect_run(folder)['evidence_issues'])
  (folder/'proposed.py').write_text('altered proposal')
  self.assertIn('Passing proposal missing or changed',coding_agent.inspect_run(folder)['evidence_issues'])
 def test_source_drift_stops_before_paid_request(self):
  client=self.client(['def add(a,b): return a+b'])
  def changing_client(path,data=None):
   if path=='session':(self.root/'module.py').write_text('user edits')
   return client(path,data)
  folder=coding_agent.run_job(self.root/'job.json',True,changing_client)
  self.assertEqual(len(self.requests),0)
  self.assertEqual(json.loads((folder/'state.json').read_text())['status'],'source_changed_during_run_review_required')
 def test_truncated_correct_code_cannot_pass(self):
  client=self.client(['def add(a,b): return a+b']*2)
  def truncated(path,data=None):
   result=client(path,data)
   if path=='run':result['session']['messages'][-1]['finish_reason']='length'
   return result
  folder=coding_agent.run_job(self.root/'job.json',True,truncated)
  state=json.loads((folder/'state.json').read_text())
  self.assertEqual(state['status'],'attempt_budget_exhausted')
  self.assertFalse((folder/'proposal.diff').exists())
  self.assertEqual(state['requirements'][0]['status'],'unverified')
 def test_success_claim_does_not_override_execution(self):
  folder=coding_agent.run_job(self.root/'job.json',True,self.client(['# All tests passed\ndef add(a,b): return 0']*2))
  self.assertEqual(json.loads((folder/'state.json').read_text())['status'],'attempt_budget_exhausted')
 def test_uncovered_requirements_rejected(self):
  path=self.root/'job.json';job=json.loads(path.read_text());job['requirements']=[{'id':'x','description':'anything','cases':[]}];path.write_text(json.dumps(job))
  with self.assertRaises(ValueError):coding_agent.load_job(path)
