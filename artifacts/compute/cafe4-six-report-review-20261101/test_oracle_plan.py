"""Source and abstract protocol fixtures; these do not execute the C++ or a model."""
import unittest
from pathlib import Path

class OraclePlan(unittest.TestCase):
    def test_accept_zero_and_partial(self):
        for proposals, predictions, expected in [([1,2,3],[8,2,3],0),([1,2,3],[1,9,3],1),([1,2,3,4],[1,2,9,4],2)]:
            n=0
            for p,t in zip(proposals,predictions):
                if p!=t: break
                n+=1
            self.assertEqual(n,expected)
            self.assertTrue(n<len(proposals))
            start=20
            keep=start+n-1
            self.assertEqual(keep+1,start+n)
    def test_candidate_no_oracle_append_and_explicit_fault_marker(self):
        s=(Path(__file__).parent/'candidate/rs-rollback.cpp').read_text()
        for expected in ['draft_ctx', 'greedy_row(ctx, vocab, j - 1)', 'out.push_back(draft[j])',
                         'logit_error(llama_get_logits_ith(ctx, -1), out.size(), err)',
                         'FAULT_DETECTED replay-state logits mismatch', 'UNKNOWN fault did not change observed logits']:
            self.assertIn(expected,s)
        self.assertNotIn('out.push_back(ref[',s)
        self.assertNotIn('out.push_back(replay)',s)

if __name__=='__main__': unittest.main()
