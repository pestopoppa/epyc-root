import copy
import unittest
from source_census import EVENTS, validate


def fixture():
    p=[]; r=[]
    for i, (cpu, name) in enumerate((c,e) for c in (0,1) for e in sorted(EVENTS)):
        p.append({'cpu':cpu,'name':name,'event_id':i+1})
        r.append({'cpu':cpu,'name':name,'event_id':i+1,'enable_before_ns':1,'enable_after_ns':2,'disable_before_ns':5,'disable_after_ns':6,'enabled_ns':4,'running_ns':4,'lost_samples':0,'count':0,'errors':[],'ring':{'errors':[]}})
    return {'errors':[],'status':'unproven','coverage':'unknown','loss':'unknown','measurement_admission':'none','markers':[{'kind':'begin','seq':1,'timestamp_ns':3},{'kind':'end','seq':2,'timestamp_ns':4}],'source_provenance':p,'rings':r}

class TestCensus(unittest.TestCase):
    def test_valid_is_not_admission(self):
        r=validate(fixture(),{0,1}); self.assertEqual(r['sources'],10); self.assertEqual(r['coverage'],'unknown'); self.assertEqual(r['measurement_admission'],'none')
    def test_reject_mutations(self):
        for mutate in [lambda d:d['rings'].pop(),lambda d:d['source_provenance'].pop(),lambda d:d['rings'].append(copy.deepcopy(d['rings'][0])),lambda d:d['source_provenance'][1].update(event_id=1),lambda d:d['rings'][0].update(lost_samples=1),lambda d:d['rings'][0].update(running_ns=3),lambda d:d['rings'][0].update(enable_after_ns=4),lambda d:d['rings'][0]['ring'].update(errors=['overrun']),lambda d:d.update(coverage='complete'),lambda d:d['markers'][0].update(seq=2),lambda d:d['rings'][0].update(event_id=999)]:
            d=fixture(); mutate(d)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): validate(d,{0,1})
    def test_reject_bad_cpu_set(self):
        with self.assertRaises(ValueError): validate(fixture(),{True})

if __name__ == '__main__': unittest.main()
