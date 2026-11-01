import math,unittest
from reducer import reduce_pair
Q={k:True for k in ('same_binary','same_model','same_source','same_argv','gpu_idle_both','quarter_bound_both','both_complete','no_errors','same_clients','cleanup_verified','warrant_captured')}
def waves(sums,streams):
    return [dict(wave=i,n_ok=8,n_err=0,errors=[],decode_tps_sum=s,decode_tps_per_stream=[v]*8) for i,(s,v) in enumerate(zip(sums,streams))]
class ReducerTest(unittest.TestCase):
    def setUp(self):
        self.u={'decode_tps_sum_med':10.49,'decode_tps_stream_med':1.41,'ttft_s_med':2361.3};self.s={'decode_tps_sum_med':20.63,'decode_tps_stream_med':2.54,'ttft_s_med':2310.75};self.uw=waves([10,10.49,11.49,10.36],[.3,1.345,1.615,1.23]);self.sw=waves([12,20.65,20.63,20.45],[.3,2.305,2.54,2.485])
    def r(self,q=Q):return reduce_pair(self.u,self.s,self.uw,self.sw,q)
    def test_explicit_wave_threshold(self):
        r=self.r();self.assertEqual(r['verdict'],'NO_DIFFERENCE');self.assertAlmostEqual(r['threshold_pct']['stream'],57.24907063197027)
    def test_missing_evidence(self):self.assertEqual(self.r({})['verdict'],'INVALID')
    def test_invalid_stream(self):self.uw[1]['decode_tps_per_stream'][0]=math.nan;self.assertEqual(self.r()['verdict'],'INVALID')
    def test_missing_wave(self):self.uw.pop();self.assertEqual(self.r()['verdict'],'INVALID')
    def test_bad_completion(self):self.sw[0]['n_err']=1;self.assertEqual(self.r()['verdict'],'INVALID')
if __name__=='__main__':unittest.main()
