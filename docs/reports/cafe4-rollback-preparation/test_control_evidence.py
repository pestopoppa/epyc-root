import unittest
from control_evidence import compare


def pair():
    common = {'binary_sha256':'a'*64,'model_sha256':'b'*64,'patch_sha256':'c'*64,'config':{'width':4,'seed':0},'rc':1}
    return (dict(common, log='CAFE4_NEXT_COMPARISON mode=observe index=8 finite=1 max_abs=0 threshold=1e-5 selected=1 faulted=0\nSTRICT_PARTIAL width=4 accepted=2 keep=7 max_abs=0\nRESULT: UNKNOWN (token consistency observed; recurrent snapshot execution and fault control unproven)\n'),
            dict(common, log='CAFE4_NEXT_COMPARISON mode=fault index=8 finite=1 max_abs=0.1 threshold=1e-5 selected=1 faulted=1\nUNKNOWN next-token logits differ from serial oracle\n'))

class Tests(unittest.TestCase):
    def test_candidate_control(self):
        self.assertEqual(compare(*pair())['status'], 'SYNTHETIC_CONTROL_OBSERVED')
    def test_identity_mismatch(self):
        a,b=pair(); b['model_sha256']='d'*64
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')
    def test_nonfinite_is_not_detection(self):
        a,b=pair(); b['log']=b['log'].replace('max_abs=0.1','max_abs=nan')
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')
    def test_generic_failure_is_not_detection(self):
        a,b=pair(); b['log']='UNKNOWN decode failed\n'
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')
    def test_fault_counter_required(self):
        a,b=pair(); b['log']=b['log'].replace('faulted=1','faulted=0')
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')
    def test_partial_and_complete_observe_required(self):
        a,b=pair(); a['log']=a['log'].replace('accepted=2','accepted=0')
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')
    def test_unmatched_token_position(self):
        a,b=pair(); b['log']=b['log'].replace('index=8','index=9')
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')
    def test_config_mismatch(self):
        a,b=pair(); b['config']={'width':8}
        self.assertEqual(compare(a,b)['status'], 'UNKNOWN')

if __name__ == '__main__': unittest.main()
