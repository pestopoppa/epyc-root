import unittest
import evaluate_replay as E

class TestEvaluate(unittest.TestCase):
    def setUp(self):
        self.expected = [(str(i), 'h'+str(i)) for i in range(48)]
        self.requests = [{'tag':t, 'body_sha256':h, 'http_status':200, 'completed':True, 'trigger_observed':i<5} for i,(t,h) in enumerate(self.expected)]
        self.samples = [{'t':1,'phase':'load','own_vram_b':10*E.GIB,'hip_resident':True}, {'t':2,'phase':'load','own_vram_b':11*E.GIB,'hip_resident':True}, {'t':2.8,'phase':'warm','own_vram_b':12*E.GIB,'hip_resident':True}, {'t':3,'phase':'t7a','own_vram_b':12*E.GIB,'hip_resident':True}, {'t':3.5,'phase':'t7a','own_vram_b':12*E.GIB,'hip_resident':True}, {'t':4,'phase':'t7a','own_vram_b':12*E.GIB,'hip_resident':True}]
        self.evidence = dict.fromkeys(('capture_complete','load_complete','t7a_complete','cleanup_verified','source_bound'), True)
        self.evidence.update(load_start_t=1, load_end_t=2, t7a_start_t=2.9, t7a_end_t=3.9)
    def run_eval(self): return E.evaluate(self.expected,self.requests,self.samples,self.evidence)
    def test_holds_and_term(self):
        v=self.run_eval(); self.assertEqual(v['verdict'],'HOLDS'); self.assertEqual(v['runtime_term_gib'],1)
    def test_fail_above_threshold(self):
        self.samples[-1]['own_vram_b'] += E.GIB; self.assertEqual(self.run_eval()['verdict'],'FAILS')
    def test_missing_or_false_evidence_unknown(self):
        self.evidence['cleanup_verified']=False; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
    def test_incomplete_request_unknown(self):
        self.requests[-1]['completed']=False; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
    def test_trigger_count_is_observed_not_inferred(self):
        self.requests[0]['trigger_observed']=False; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
    def test_nonfinite_clock_and_missing_hip_unknown(self):
        self.samples[-1]['t']=float('nan'); self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
        self.samples[-1]['t']=4; self.samples[-1]['hip_resident']=False; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
    def test_missing_phase_bracket_unknown(self):
        self.evidence['t7a_end_t']=8; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
    def test_phase_marker_missing_unknown(self):
        del self.evidence['load_start_t']; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')
    def test_hash_mismatch_unknown(self):
        self.requests[0]['body_sha256']='wrong'; self.assertEqual(self.run_eval()['verdict'],'UNKNOWN')

if __name__ == '__main__': unittest.main()
