import unittest
from one_item import OneItemBudget

class OneItemTest(unittest.TestCase):
    def test_selects_first_and_rejects_second(self):
        b = OneItemBudget()
        self.assertEqual(b.first_pending([{'item_id':'a'}, {'item_id':'b'}]), [{'item_id':'a'}])
        b.claim('a')
        with self.assertRaises(RuntimeError): b.claim('b')
        with self.assertRaises(RuntimeError): b.claim('a')
    def test_wrong_item_does_not_consume_budget(self):
        b = OneItemBudget(); b.first_pending([{'item_id':'a'}])
        with self.assertRaises(RuntimeError): b.claim('b')
        b.claim('a')
    def test_empty_missing_and_repeat_selection_fail_closed(self):
        b = OneItemBudget(); self.assertEqual(b.first_pending([]), [])
        with self.assertRaises(RuntimeError): b.claim('x')
        with self.assertRaises(ValueError): OneItemBudget().first_pending([{}])
        b = OneItemBudget(); b.first_pending([{'item_id':'x'}])
        with self.assertRaises(RuntimeError): b.first_pending([{'item_id':'x'}])

if __name__ == '__main__': unittest.main()
