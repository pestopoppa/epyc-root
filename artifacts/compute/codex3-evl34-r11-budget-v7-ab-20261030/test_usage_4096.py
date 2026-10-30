import unittest
from native_usage import UsageLedger
class UsageBound(unittest.TestCase):
 def test_4096_allowed_4097_refused(self):
  u=UsageLedger();u.add({'prompt_tokens':3,'completion_tokens':4096});self.assertEqual(u.totals()['completion_tokens'],4096)
  with self.assertRaises(ValueError):u.add({'prompt_tokens':3,'completion_tokens':4097})
