import unittest
from analysis import analyze_sr8, TASKS, ARMS

class TestSR8(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(rep=r,task=t,arm=a,status='ok',temperature=0,fresh_server=True,gpu_residency=True,
                        decode_tps=(16 if a=='prompt_lookup' else 10),edit_validity='PASS',draft_rounds=4,accepted=2,drafted=8)
                   for r in range(1,6) for t in [TASKS[(r-1)%len(TASKS)]] for a in ARMS]
    def test_valid(self):
        x=analyze_sr8(self.rows)
        self.assertEqual(x['n_pairs'],5); self.assertTrue(x['candidate_threshold_met'])
        self.assertEqual(x['arms']['prompt_lookup']['mean_accepted_draft_tokens'],.5)
    def test_missing_and_duplicate(self):
        with self.assertRaises(ValueError): analyze_sr8(self.rows[:-1])
        with self.assertRaises(ValueError): analyze_sr8(self.rows+[self.rows[0]])
    def test_no_residency(self):
        self.rows[0]['gpu_residency']=False
        with self.assertRaises(ValueError): analyze_sr8(self.rows)
    def test_failed_edit(self):
        self.rows[0]['edit_validity']='FAIL'
        with self.assertRaises(ValueError): analyze_sr8(self.rows)
    def test_bad_counts(self):
        self.rows[-1]['accepted']=9
        with self.assertRaises(ValueError): analyze_sr8(self.rows)

if __name__=='__main__': unittest.main()
