import unittest
from ecu import route

class RoutingTests(unittest.TestCase):
 def test_simple_extraction_is_direct(self):
  d=route('Extract the invoice ID from this record.',ceiling=2048)
  self.assertEqual((d['effort'],d['max_tokens']),('none',1024))
 def test_arithmetic_inside_transformation_retains_reasoning(self):
  self.assertEqual(route('Extract the prices and calculate their total.')['effort'],'low')
 def test_unknown_request_and_followup_retain_reasoning(self):
  self.assertEqual(route('What should we do about this situation?')['effort'],'low')
  self.assertEqual(route('Rewrite that',history_count=2)['effort'],'low')
 def test_explicit_depth(self):
  self.assertEqual(route('Think deeply about this proof.')['effort'],'high')
 def test_social_message_does_not_need_reasoning(self):
  self.assertEqual(route('hey!')['effort'],'none')
  self.assertEqual(route('hello, debug this deadlock')['effort'],'high')
  self.assertEqual(route('thanks, calculate the total')['effort'],'low')
 def test_attached_files_are_not_treated_as_idle_chat(self):
  from engine import prepare
  result=prepare({'prompt':'hello','attachments':[{'name':'bug.py','content':'x = 1'}]},[])
  self.assertEqual(result['decision']['effort'],'low')
 def test_style_applies_with_saved_custom_instructions(self):
  from engine import prepare, STYLE
  result=prepare({'prompt':'hello','instructions':'Help with coding.'},[])
  self.assertIn(STYLE,result['messages'][0]['content'])
 def test_respects_small_user_budget(self):
  self.assertEqual(route('Translate hello.',ceiling=512)['max_tokens'],512)

if __name__=='__main__':unittest.main()
