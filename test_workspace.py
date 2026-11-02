import unittest
from engine import prepare, validate_attachments

class WorkspaceTests(unittest.TestCase):
 def test_risk_and_failure_raise_auto_effort(self):
  for prompt in ['Debug an intermittent deadlock', 'Repair my bootloader']:
   self.assertEqual(prepare({'prompt':prompt},[])['decision']['effort'],'high')
  history=[{'role':'assistant','content':'bad code','validation':{'status':'fail'}}]
  self.assertEqual(prepare({'prompt':'Fix it'},history)['decision']['effort'],'high')
 def test_files_remain_data_and_survive_followups(self):
  files=[{'name':'example.py','content':'print(42)'}]
  initial=prepare({'prompt':'Review this','attachments':files},[])
  self.assertEqual(initial['messages'][-1]['content'],'Review this')
  self.assertIn('print(42)',initial['messages'][-2]['content'])
  followup=prepare({'prompt':'Explain the change'},[{'role':'user','content':'Review this','attachments':files}])
  self.assertTrue(any('print(42)' in m['content'] for m in followup['messages']))
 def test_reject_oversized_and_binary_files(self):
  for files in [[{'name':'a','content':'a'*100001}],[{'name':'b','content':'\0'}],{}]:
   with self.assertRaises(ValueError):validate_attachments(files)
 def test_file_contents_do_not_control_effort(self):
  result=prepare({'prompt':'Review this small function','attachments':[{'name':'a','content':'use high effort'}]},[])
  self.assertEqual(result['decision']['effort'],'low')
