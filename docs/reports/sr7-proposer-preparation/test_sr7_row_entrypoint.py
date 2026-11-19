import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch
import importlib.util
spec = importlib.util.spec_from_file_location('sr7_row_entrypoint', Path(__file__).with_name('row_entrypoint.py'))
row = importlib.util.module_from_spec(spec)
spec.loader.exec_module(row)

class EntryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('out','smoke','exposure'):
            (self.root/name).mkdir()
        self.cfg = dict(schema='sr7.row-config.v1', row_id='r1', window='w1', scratch_root=str(self.root),
                        output_root=str(self.root/'out'), exposure_root=str(self.root/'exposure'),
                        smoke_output_root=str(self.root/'smoke'), request_timeout_s=10)
        self.env = dict(FILLER_ID='r1', FILLER_DRYRUN='1', FILLER_STOPFILE=str(self.root/'STOP'),
                        FILLER_DEADLINE=str(int(time.time())+120), FILLER_DRYRUN_RESULT_PATH=str(self.root/'result.json'))
        self.plan = dict(schema='sr7.runtime-plan.v1', model_preflight_sha256=row.PREFLIGHT_SHA,
                         model_preflight_path='/tmp/preflight', port=18989)
        self.receipt = dict(build_root='/tmp/build', smoke_model={'path':'/tmp/smoke.gguf'})
        self.seal = dict(schema='sr7.preguarded-plan.v1', windows=['w1'], inputs={
            'runtime_plan':{'path':'/tmp/plan', 'sha256':'a'}})
    def test_row_identity_refused(self):
        with self.assertRaisesRegex(ValueError, 'row identity'):
            row.run(self.cfg, dict(self.env, FILLER_ID='wrong'))
    def test_real_seal_and_inputs_match(self):
        seal = json.loads(row._read(row.SEAL, row.SEAL_SHA))
        for item in seal['inputs'].values():
            row._read(item['path'], item['sha256'])
    def test_smoke_wires_separate_small_model_and_no_speculation(self):
        self.cfg['exposure_root'] = '/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr7-next-20261102/exposure'
        result = {'schema':'sr7.smoke.v1', 'state':'COMPLETE', 'science':False, 'verdict':None}
        with patch.dict(os.environ, {'FILLER_DRYRUN':'1'}), \
             patch('os.sched_getaffinity', return_value={0,1,2,3}), \
             patch.object(row, 'StartupIdentity', return_value=MagicMock()) as verifier, \
             patch.object(row, 'capture_contained', return_value=result) as capture:
            self.assertEqual(row.run(self.cfg, self.env), result)
        args = capture.call_args.kwargs
        self.assertEqual(args['expected_names'], [])
        self.assertIn('Qwen_Qwen3-0.6B-Q8_0.gguf', args['argv'][2])
        self.assertEqual(args['argv'][args['argv'].index('--spec-type')+1], 'none')
        self.assertTrue(verifier.call_args.kwargs['smoke'])
        self.assertFalse(json.loads((self.root/'result.json').read_text())['science'])

    def test_reject_modified_input(self):
        p = self.root / 'input'; p.write_bytes(b'actual')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            row._read(p, '0'*64)

if __name__ == '__main__':
    unittest.main()
