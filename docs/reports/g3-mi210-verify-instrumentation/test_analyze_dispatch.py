import unittest
from analyze_dispatch import classify


def call(ident='a', kernel='VEC'):
    return [{'kind':'begin','invocation':ident,'mode':'parallel','draft_length':1,
             'view_tokens':2,'spec_indices':[0,1]},
            {'kind':'dispatch','invocation':ident,'layer':0,'kernel':kernel,'q_len':2,'kv_type':'Q8_0'},
            {'kind':'dispatch','invocation':ident,'layer':1,'kernel':'TILE','q_len':2,'kv_type':'Q8_0'},
            {'kind':'end','invocation':ident,'rc':0}]


class ClassifyTest(unittest.TestCase):
    def test_vec_and_scoped_no_vec(self):
        result = classify(call() + call('b', 'TILE'), expected_attention_layers=2)
        self.assertEqual([x['vec_observed'] for x in result['verify_calls']], [True, False])
    def test_incomplete_and_nonverify_are_unknown(self):
        for records in (call()[:-1], call()[:2]+call()[-1:],
                        [dict(call()[0], mode='serial')]+call()[1:],
                        [dict(call()[0], spec_indices=[0,0])]+call()[1:]):
            with self.subTest(records=records):
                result = classify(records, expected_attention_layers=2)
                self.assertEqual(result['verify_calls'], [])
                self.assertEqual(result['unknown_invocations'], ['a'])
    def test_invalid_correlation_rejected(self):
        records = call() + [dict(call()[1])]
        with self.assertRaises(ValueError): classify(records, expected_attention_layers=2)
        records = call() + [dict(call()[0])]
        with self.assertRaises(ValueError): classify(records, expected_attention_layers=2)

    def test_wrong_layer_set_is_unknown(self):
        records = call()
        records[2] = dict(records[2], layer=7)
        result = classify(records, expected_attention_layers=2)
        self.assertEqual(result['verify_calls'], [])
        self.assertEqual(result['unknown_invocations'], ['a'])

if __name__ == '__main__':
    unittest.main()
