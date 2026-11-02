import json
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import kvu16a_native as adapter
from adapters import _native_sidecar as ns
from claim_tuple import ProjectionError

class KVU16aBeliefTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.plan = {'belief_adapter_sha256': ns.file_sha256(Path(adapter.__file__)), 'producer_sha256':'a'*64,
                     'producer_files_sha256':{k:'a'*64 for k in ('producer.py','sampler.py','device_identity.py','server_lifecycle.py')},
                     'producer_path':'/synthetic/producer.py', 'argv':['server','--no-cache-idle-slots'],
                     'effective_env':{'GGML_IQK':'1'}, 'identities':{'/synthetic/model':'b'*64},
                     'max_gap_seconds':1.0, 'healthy_samples':2}
        self.records = [{'status':'observed','own_vram_b':2048+i,'pid':123,'birth_ticks':1,'phase':'healthy',
                         'hip_resident':True,'sample_start_monotonic_s':1.0+i*0.2,
                         'sample_end_monotonic_s':1.1+i*0.2} for i in range(2)]
        self.result = {'schema':'kvu16a.load.sampled.v1', 'state':{'error':None,'started_at':0.9,'ended_at':1.5},
                       'cleanup':{'verified_dead':True,'pid':123,'birth_ticks':1},
                       'runtime_identity':{'argv':self.plan['argv'],'effective_env':self.plan['effective_env'],
                                           'mapped_libraries_sha256':{'/synthetic/libggml-hip.so':{'sha256':'c'*64}}},
                       'grant':{'FILLER_NEEDGPU':'1','FILLER_DEADLINE':'999'},'device':{'bdf':'synthetic'},
                       'sampling_gaps_s':[0.09999999999999998, 0.09999999999999987, 0.19999999999999996],
                       'coverage_qualified':True, 'sample_count':2, 'target_kv_b_from_log':1024.0,
                       'healthy_sampled_max_non_kv_b':1025.0}
        starts = [x['sample_start_monotonic_s'] for x in self.records] + [1.5]
        ends = [0.9] + [x['sample_end_monotonic_s'] for x in self.records]
        self.result['sampling_gaps_s'] = [max(0,b-a) for a,b in zip(ends, starts)]
        self.write()
    def tearDown(self): self.tmp.cleanup()
    def write(self):
        (self.root/'plan.json').write_text(json.dumps(self.plan))
        (self.root/'result.json').write_text(json.dumps(self.result))
        (self.root/'samples.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.records))
        (self.root/'server.log').write_text('llama_kv_cache: size = 0.0009765625 MiB (393216 cells, 16 layers, 4/1 seqs), K (q8_0)\n')
    def test_original_observation_shared_reader_and_tamper_refusal(self):
        path = adapter.record_run(self.root)
        rows = adapter.native_rows(path)
        claim = adapter.project(rows[0])
        self.assertEqual(claim.value, 1025.0)
        self.assertIn('not a peak', claim.claim)
        self.assertTrue(adapter.frames_for_sidecar(path, as_of='2026-11-02T15:00:00Z'))
        (self.root/'server.log').write_text('changed')
        with self.assertRaises(ProjectionError): adapter.native_rows(path)
    def test_missing_sample_or_missing_grant_is_unknown(self):
        self.records[0]['own_vram_b'] = None; self.write()
        self.assertIsNone(adapter.record_run(self.root))
        self.assertFalse((self.root/adapter.SIDECAR_NAME).exists())
        self.records[0]['own_vram_b'] = 2048; self.result['grant'] = {}; self.write()
        self.assertIsNone(adapter.record_run(self.root))
    def test_pre_hook_refuses(self):
        self.plan.pop('belief_adapter_sha256'); self.write()
        self.assertIsNone(adapter.record_run(self.root))

if __name__ == '__main__': unittest.main()
