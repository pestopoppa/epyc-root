import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

P = Path(__file__).parent
spec = importlib.util.spec_from_file_location('capture', P / 'belief_capture.py')
capture = importlib.util.module_from_spec(spec); spec.loader.exec_module(capture)

class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.d = self.root / 'out/E1-A0-low'; self.d.mkdir(parents=True)
        (self.root/'inputs').mkdir(); (self.root/'inputs/manifest.json').write_text('{}')
        (self.root/'SOURCE.sha256').write_text('source')
        (self.root/'image-binding.json').write_text(json.dumps({'source_commit':'a'*40}))
        (self.root/'model-pin.json').write_text(json.dumps({'sha256':'b'*64}))
        (self.d/'launch.json').write_text(json.dumps({'pid':123,'at':1}))
        (self.d/'runtime-proof.json').write_text(json.dumps({'pid':123}))
        kfd = self.d/'kfd.jsonl'; kfd.write_text(json.dumps({'t': 2.5, 'pid_vram_gib': 2.0, 'kfd_pids': [123]}) + '\n')
        shim = self.d/'hipmalloc.jsonl'; shim.write_text('trace')
        calls = self.d/'calls.jsonl'; calls.write_text('calls')
        self.a={'kfd':str(kfd),'shim':str(shim),'native_calls':str(calls),'stages':{s:{'own_kfd_peak_gib':2.0,'start':2,'end':3,'requests':6} for s in ('128k','240k')}}
        (self.d/'phase-attribution.json').write_text(json.dumps(self.a))
        self.old = os.environ.get('FILLER_ID'); os.environ['FILLER_ID']='test-run'
    def tearDown(self):
        if self.old is None: os.environ.pop('FILLER_ID',None)
        else: os.environ['FILLER_ID']=self.old
        self.tmp.cleanup()
    def test_rows_have_shared_carrier_fields(self):
        path=capture.emit(self.d,self.a);rows=[json.loads(x) for x in path.read_text().splitlines()]
        self.assertEqual([r['phase'] for r in rows],['128k','240k'])
        self.assertEqual(rows[0]['protocol_id'],'');self.assertEqual(rows[0]['category'],'BASELINE')
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[3] / 'vidya'))
        from claim_tuple import ClaimTuple, grade
        r=rows[0]; tup=ClaimTuple(measurement_id=r['measurement_id'],metric=r['metric'],value=r['value'],date=r['date'],category=r['category'],claim=r['claim'],metric_direction=r['metric_direction'],unit=r['unit'],protocol_id=r['protocol_id'],reps=r['reps'],reps_basis=r['reps_basis'])
        self.assertIsNotNone(grade(tup))
    def test_missing_samples_refuses(self):
        self.a['stages']['240k']['own_kfd_peak_gib']=None
        (self.d/'phase-attribution.json').write_text(json.dumps(self.a))
        with self.assertRaises(ValueError): capture.emit(self.d,self.a)
        self.assertFalse((self.d/'belief_measurements.jsonl').exists())
    def test_out_of_window_and_wrong_pid_samples_refused(self):
        (self.d/'kfd.jsonl').write_text(json.dumps({'t': 8, 'pid_vram_gib': 2, 'kfd_pids': [123]}) + '\n')
        with self.assertRaises(ValueError): capture.emit(self.d, self.a)
        (self.d/'kfd.jsonl').write_text(json.dumps({'t': 2.5, 'pid_vram_gib': 2, 'kfd_pids': [124]}) + '\n')
        with self.assertRaises(ValueError): capture.emit(self.d, self.a)
    def test_wrong_pid_refuses(self):
        (self.d/'runtime-proof.json').write_text(json.dumps({'pid':124}))
        with self.assertRaises(ValueError): capture.emit(self.d,self.a)
    def test_changed_record_refuses(self):
        (self.d/'phase-attribution.json').write_text('{}')
        with self.assertRaises(ValueError): capture.emit(self.d,self.a)

if __name__=='__main__':unittest.main()
