import unittest
from block_guard import ARMS, classify

class TestBlockGuard(unittest.TestCase):
    def test_fresh(self):
        self.assertEqual(classify(['a'], []), 'FRESH')
    def test_complete(self):
        records = [dict(prompt_id='a', arm=a, exposure=True, response='complete') for a in ARMS]
        self.assertEqual(classify(['a'], records), 'COMPLETE')
    def test_interruption_fails(self):
        self.assertEqual(classify(['a'], [dict(prompt_id='a', arm='mtp3', exposure=True, response='complete')]), 'ABANDON')
    def test_bad_record_fails(self):
        self.assertEqual(classify(['a'], [dict(prompt_id='a', arm='mtp3', exposure=True, response='error')]), 'ABANDON')
    def test_duplicate_fails(self):
        record = dict(prompt_id='a', arm='mtp3', exposure=True, response='complete')
        self.assertEqual(classify(['a'], [record, record]), 'ABANDON')
    def test_invalid_plan_fails(self):
        self.assertEqual(classify(['a', 'a'], []), 'ABANDON')

if __name__ == '__main__':
    unittest.main()
