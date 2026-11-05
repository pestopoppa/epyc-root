import copy
import unittest
from classify import classify

def row(op, arm, cases):
    return {'op': op, 'arm': arm, 'cases': [{'op': op, 'params': p, 'status': s} for p,s in cases], 'case_count': len(cases), 'cleanup': True}

def sample():
    m = [('type_a=q4_K,type_b=f16,m=16,bs=[2,3]', 'not_supported')]
    f = [('hsk=64,hsv=64,type_K=q5_0,type_V=q5_0', 'not_supported')]
    return {'status':'COMPLETE', 'mode':'grant', 'rows':[row('MUL_MAT','baseline',m),row('MUL_MAT','corrected',m),row('FLASH_ATTN_EXT','baseline',f),row('FLASH_ATTN_EXT','corrected',f)]}

class TestClassification(unittest.TestCase):
    def test_known_guards(self):
        x=classify(sample()); self.assertEqual(x['MUL_MAT']['rhs_f16_non_f16_lhs'],1); self.assertEqual(x['FLASH_ATTN_EXT']['unsupported_kv_types_when_all_quants_off'],1)
    def test_mismatched_identity_fails_closed(self):
        x=sample(); x['rows'][1]['cases'][0]['params'] += ',n=9'
        with self.assertRaises(ValueError): classify(x)
    def test_incomplete_fails_closed(self):
        x=sample(); x['rows'][2]['cleanup']=False
        with self.assertRaises(ValueError): classify(x)
    def test_counts_include_duplicates(self):
        x=sample(); c=copy.deepcopy(x['rows'][0]['cases'][0]); x['rows'][0]['cases'].append(c); x['rows'][1]['cases'].append(copy.deepcopy(c)); x['rows'][0]['case_count']+=1; x['rows'][1]['case_count']+=1
        self.assertEqual(classify(x)['MUL_MAT']['corrected_statuses']['not_supported'],2)

if __name__ == '__main__': unittest.main()
