import json
from pathlib import Path
import tempfile
import signal
import unittest
from unittest.mock import patch

import row_job as job


class RowJob(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = self.root / 'plan.json'
        self.plan.write_text('{}')
        self.out = self.root / 'out'

    def result(self):
        return json.loads((self.out / 'RESULT.json').read_text())

    def test_quality_futility_is_measured_not_quality_pass(self):
        def measured(plan, out):
            out.mkdir()
            r = dict(status='MEASURED', stopped_at='compact-quality')
            (out / 'RESULT.json').write_text(json.dumps(r))
            return r
        with patch.object(job.pipeline, 'run', side_effect=measured):
            self.assertEqual(job.run(self.plan, self.out, False), 0)
        r = self.result()
        self.assertEqual(r['status'], 'MEASURED')
        self.assertEqual(r['stopped_at'], 'compact-quality')
        self.assertFalse(r['smoke'])
        self.assertEqual(r['measured_result_sha256'],
                         job.pipeline.digest(Path(r['attempt']) / 'RESULT.json'))

    def test_native_failure_is_retained_without_success(self):
        with patch.object(job.pipeline, 'run', side_effect=ValueError('budget exceeded')):
            self.assertEqual(job.run(self.plan, self.out, False), 3)
        self.assertFalse(self.result()['ok'])
        self.assertEqual(self.result()['status'], 'REFUSED')
        self.assertIn('budget exceeded', self.result()['error'])

    def test_smoke_input_refusal_never_launches(self):
        with patch.object(job.pipeline, 'validate', side_effect=ValueError('changed build')), \
             patch.object(job.pipeline.controls, 'run') as native:
            self.assertEqual(job.run(self.plan, self.out, True), 3)
        native.assert_not_called()
        self.assertTrue(self.result()['smoke'])
        self.assertFalse(self.result()['ok'])

    def test_smoke_requires_gpu_executor_and_rechecks_plan(self):
        plan = dict(builds={'patched_hip':str(self.root / 'BUILD.json')},
                    model='prepared', model_identity='a'*64, source_commit='pin',
                    threads=4, n_gpu_layers=999, device_vram_path='counter')
        self.plan.write_text(json.dumps(plan))
        tokens = dict(prefix_tokens=list(range(100)), warmup_tokens=[1, 2], probe_tokens=[3, 4, 5])
        with patch.object(job.pipeline, 'validate', return_value=(tokens, {})) as validate, \
             patch.object(job.pipeline, 'Executor') as executor, \
             patch.object(job.pipeline.controls, 'run') as native:
            self.assertEqual(job.run(self.plan, self.out, True), 0)
        self.assertEqual(validate.call_count, 2)
        self.assertTrue(executor.call_args.kwargs['gpu'])
        self.assertEqual(native.call_args.kwargs['execute'], executor.return_value)
        config = json.loads(native.call_args.args[1].read_text())
        self.assertEqual((len(config['prefix_tokens']),len(config['probe_tokens'])), (20,2))
        self.assertEqual(self.result()['status'], 'SMOKE_PASS')
        self.assertNotIn('stopped_at', self.result())

    def test_keeper_termination_unwinds_owned_executor_and_retains_refusal(self):
        reaped = []
        def interrupted(plan, out):
            try:
                job.request_stop(signal.SIGTERM, None)
            finally:
                reaped.append(True)
        with patch.object(job.pipeline, 'run', side_effect=interrupted):
            self.assertEqual(job.run(self.plan, self.out, False), 3)
        self.assertEqual(reaped, [True])
        self.assertIn('keeper termination signal', self.result()['error'])
