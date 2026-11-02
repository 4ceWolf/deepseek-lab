import unittest
from engine import prepare

class EvaluationProfileTests(unittest.TestCase):
 def test_raw_history_keeps_conversation_without_ecu_or_reasoning(self):
  history=[{'role':'user','content':'Earlier requirement'},{'role':'assistant','content':'Earlier code','reasoning_content':'not replayed'}]
  result=prepare({'prompt':'Continue','evaluation_profile':'raw_history'},history)
  self.assertEqual([m['role'] for m in result['messages']],['user','assistant','user'])
  self.assertTrue(all(set(m)=={'role','content'} for m in result['messages']))
  self.assertEqual(result['decision']['effort'],'high')
 def test_raw_is_user_only_and_separate(self):
  r=prepare({'prompt':'hello','evaluation_profile':'raw','instructions':'Do not inject this','max_tokens':4096},[])
  self.assertEqual(r['messages'],[{'role':'user','content':'hello'}])
  self.assertEqual(r['decision']['effort'],'high')
  self.assertEqual(r['decision']['max_tokens'],4096)
  with self.assertRaises(ValueError):prepare({'prompt':'hello','evaluation_profile':'raw'},[{'role':'user','content':'old'}])
 def test_candidate_respects_risk_and_manual_effort(self):
  base={'evaluation_profile':'candidate','task_mode':'coding','output_check':'python'}
  self.assertEqual(prepare(dict(base,prompt='Fix this small pure function'),[])['decision']['effort'],'none')
  self.assertEqual(prepare(dict(base,prompt='Fix a security vulnerability'),[])['decision']['effort'],'high')
  self.assertEqual(prepare(dict(base,prompt='Fix this small pure function',effort='high'),[])['decision']['effort'],'high')
 def test_default_is_not_experimental(self):
  self.assertEqual(prepare({'prompt':'Fix this small pure function','task_mode':'coding','output_check':'python'},[])['decision']['effort'],'low')
 def test_bounded_production_route_preserves_custom_and_hard_tasks(self):
  base={'prompt':'Fix this small module: def f(xs): return xs','task_mode':'coding','output_check':'python'}
  r=prepare(base,[])
  self.assertEqual(r['decision']['effort'],'none')
  self.assertEqual(r['decision']['reference_ids'],[])
  self.assertEqual(prepare(dict(base,instructions='My custom instructions'),[])['decision']['effort'],'low')
  self.assertEqual(prepare(dict(base,prompt=base['prompt']+' Prove optimal complexity.'),[])['decision']['effort'],'low')
  self.assertEqual(prepare(dict(base,prompt=base['prompt']+' Fix security vulnerability.'),[])['decision']['effort'],'high')
 def test_truncation_does_not_automatically_escalate_or_expand_budget(self):
  history=[{'role':'assistant','content':'partial','finish_reason':'length','effort':'high'}]
  result=prepare({'prompt':'Complete the answer','max_tokens':512},history)
  self.assertEqual((result['decision']['effort'],result['decision']['max_tokens']),('low',512))
  self.assertIn('cut off',result['messages'][0]['content'])
  self.assertEqual(prepare({'prompt':'Review the bootloader recovery'},history)['decision']['effort'],'high')
 def test_promoted_request_matches_tested_compact_candidate(self):
  data={'prompt':'Fix this module: def tally(events): return {}','task_mode':'coding','output_check':'python','max_tokens':4096}
  actual=prepare(data,[])
  tested=prepare(dict(data,evaluation_profile='compact'),[])
  self.assertEqual(actual['messages'],tested['messages'])
  self.assertEqual(actual['decision']['effort'],tested['decision']['effort'])
