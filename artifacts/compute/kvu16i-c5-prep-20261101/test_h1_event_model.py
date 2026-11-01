import unittest
from h1_event_model import classify

class H1EventTests(unittest.TestCase):
    def test_exact_historic_transition_and_carry(self):
        rows=[{'nodraft':True,'prompt_n':4,'predicted_n':3},
              {'nodraft':False,'prompt_n':128,'predicted_n':3},
              {'nodraft':False,'prompt_n':129,'predicted_n':1},
              {'nodraft':False,'prompt_n':500,'predicted_n':5}]
        self.assertEqual([r['h1_event_model'] for r in classify(rows)], [False,False,True,False])
    def test_insufficient_decode_does_not_arm(self):
        rows=[{'nodraft':True,'prompt_n':0,'predicted_n':2},
              {'nodraft':False,'prompt_n':129,'predicted_n':9}]
        self.assertFalse(classify(rows)[1]['h1_event_model'])
    def test_missing_native_counts_are_not_zero(self):
        for key in ('prompt_n','predicted_n','nodraft'):
            row={'nodraft':True,'prompt_n':1,'predicted_n':3};row.pop(key)
            with self.assertRaises(ValueError):classify([row])
    def test_bool_is_not_an_integer_counter(self):
        with self.assertRaises(ValueError): classify([{'nodraft':True,'prompt_n':True,'predicted_n':3}])

if __name__=='__main__':unittest.main()
