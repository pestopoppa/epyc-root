import copy
import unittest
from analyze_pairs import ARMS, analyze

def rows():
    return [dict(window=w,prompt_id=f'p{w}',arm=a,status='complete',predicted_n=50,predicted_ms=1000,
                 prompt_sha256='p',rendered_sha256='r',sampler_sha256='s',seed=w,**{'class':'code'},output_tokens_sha256='o')
            for w in range(3) for a in ARMS]
class Tests(unittest.TestCase):
    def test_complete_is_only_descriptive(self):
        result=analyze(rows()); self.assertEqual(result['status'],'DESCRIPTIVE_ONLY'); self.assertIsNone(result['verdict'])
    def test_missing_arm_fails(self):
        self.assertEqual(analyze(rows()[:-1])['status'],'UNKNOWN')
    def test_two_windows_fail(self):
        self.assertEqual(analyze(rows()[:10])['status'],'UNKNOWN')
    def test_mismatched_seed_fails(self):
        r=rows(); r[0]['seed']=99; self.assertEqual(analyze(r)['status'],'UNKNOWN')
    def test_mismatched_tokens_fail(self):
        r=rows(); r[0]['output_tokens_sha256']='other'; self.assertEqual(analyze(r)['status'],'UNKNOWN')
    def test_duplicate_fails(self):
        r=rows(); r.append(copy.deepcopy(r[0])); self.assertEqual(analyze(r)['status'],'UNKNOWN')
    def test_zero_time_fails(self):
        r=rows(); r[0]['predicted_ms']=0; self.assertEqual(analyze(r)['status'],'UNKNOWN')
if __name__=='__main__': unittest.main()
