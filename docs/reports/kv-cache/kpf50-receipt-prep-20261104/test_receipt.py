import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import window_custody
import receipt

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.win = 'full-a'; self.run = 'run1'
        window_custody.begin(self.root, self.win, self.run)
        common = {'window':self.win, 'run_id':self.run}
        self.files = {}
        self.put('outcome', {**common,'schema':'kpf50.window-outcome.v1','complete':True})
        self.put('cleanup', {**common,'schema':'kpf50.cleanup.v1','verified_dead':True,'remaining_children':0})
        self.put('clock_before', {**common,'schema':'kpf50.clock-sample.v1','phase':'clock_before','hsa_tick':10,'hsa_hz':1000,'mono_before_ns':100,'mono_after_ns':101})
        self.put('clock_after', {**common,'schema':'kpf50.clock-sample.v1','phase':'clock_after','hsa_tick':20,'hsa_hz':1000,'mono_before_ns':200,'mono_after_ns':201})
        raw=b'profile rows\n'; (self.root/'trace.csv').write_bytes(raw)
        self.put('trace_manifest', {**common,'schema':'kpf50.trace-manifest.v1','complete':True,'files':[{'file':'trace.csv','sha256':hashlib.sha256(raw).hexdigest()}]})

    def put(self, key, value):
        name=key+'.json'; self.files[key]=name; (self.root/name).write_text(json.dumps(value))

    def change(self,key,**values):
        p=self.root/self.files[key]; d=json.loads(p.read_text()); d.update(values); p.write_text(json.dumps(d))

    def reject(self):
        with self.assertRaises((ValueError, OSError, TypeError)):
            receipt.publish(self.root,self.win,self.run,self.files)
        self.assertFalse((self.root/(self.win+'.complete.json')).exists())

    def test_producer_binds_existing_consumer(self):
        r=receipt.publish(self.root,self.win,self.run,self.files)
        self.assertEqual(r['schema'],'kpf50.window-complete.v1')
        window_custody.begin(self.root,'mask-a',self.run,window_custody.validate_prior)
        with self.assertRaises(FileExistsError):receipt.publish(self.root,self.win,self.run,self.files)

    def test_missing_or_bad_cleanup_refused(self):
        self.change('cleanup', verified_dead=False); self.reject()
        self.change('cleanup', verified_dead=True, remaining_children=True); self.reject()
        (self.root/self.files['cleanup']).unlink(); self.reject()

    def test_missing_or_inconsistent_clock_refused(self):
        self.change('clock_after', hsa_hz=2000); self.reject()
        self.change('clock_after', hsa_hz=1000, mono_before_ns=100); self.reject()
        (self.root/self.files['clock_after']).unlink(); self.reject()

    def test_missing_tampered_or_empty_trace_refused(self):
        (self.root/'trace.csv').write_text('tampered'); self.reject()
        (self.root/'trace.csv').write_bytes(b''); self.reject()
        (self.root/self.files['trace_manifest']).unlink(); self.reject()

    def test_outcome_and_identity_refused(self):
        self.change('outcome', complete=False); self.reject()
        self.change('outcome', complete=True, run_id='other'); self.reject()

    def test_symlink_and_bad_start_refused(self):
        p=self.root/self.files['cleanup'];p.unlink();p.symlink_to('/dev/null');self.reject()
        p.unlink();self.put('cleanup',{'schema':'kpf50.cleanup.v1','window':self.win,'run_id':self.run,'verified_dead':True,'remaining_children':0})
        (self.root/(self.win+'.start.json')).write_text('{}');self.reject()

    def test_evidence_tampering_detected_by_consumer(self):
        receipt.publish(self.root,self.win,self.run,self.files)
        self.change('cleanup', remaining_children=1)
        with self.assertRaises(ValueError):window_custody.begin(self.root,'mask-a',self.run,window_custody.validate_prior)

    def test_referenced_trace_tampering_detected_by_consumer(self):
        receipt.publish(self.root,self.win,self.run,self.files)
        (self.root/'trace.csv').write_bytes(b'tampered')
        with self.assertRaises(ValueError):window_custody.begin(self.root,'mask-a',self.run,window_custody.validate_prior)

if __name__ == '__main__': unittest.main()
