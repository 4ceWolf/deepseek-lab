import unittest
from engine import validate

class ValidationTests(unittest.TestCase):
 def test_ambiguous_and_nonstandard_json_is_not_passed(self):
  for content in ['{"passed":false,"passed":true}', '{"value":NaN}', '{"value":Infinity}', '{"outer":{"x":1,"x":2}}']:
   self.assertEqual(validate(content,'json')['status'],'fail')
 def test_valid_nested_json_remains_accepted(self):
  self.assertEqual(validate('{"results":[{"passed":false}],"value":null}','json')['status'],'pass')
