"""Model-free actual main/writer controls; allocation/service adapters are fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
import test_arm_order

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c6_actual_job', HERE / 'gpu_identity_job.py')
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class MainControls(unittest.TestCase):
    def exercise(self, mode):
        # Retain every fixture: no cleanup/delete/rename.
        root = Path(tempfile.mkdtemp(prefix='actual-main-', dir=HERE / 'retained-control-fixtures'))
        (root / 'PROTOCOL-PINS.json').write_bytes((HERE / 'PROTOCOL-PINS.json').read_bytes())
        for name in ['ORIGINAL-SHA256SUMS', 'PACKAGE-SHA256SUMS']:
            (root / name).write_text('MODEL_FREE_ADAPTER_FIXTURE\n')
        proto = json.loads((HERE / 'PROTOCOL-PINS.json').read_text())
        fixture_grant = root / 'PRIVATE-NON-GRANT.txt'
        fixture_grant.write_text('not an admission; model-free external-boundary adapter only\n')
        real_sha = job.sha

        def fixture_sha(path):
            if Path(path).parent == Path('/mnt/raid0/llm/tmp/compute-flags/grants'):
                return real_sha(fixture_grant)
            return real_sha(path)

        class ServiceAdapter:
            def __init__(self, *args):
                pass

            def run(self, argv, workdir, env, timeout):
                self_case.assertIn(str(root / 'original/gpu_champion_ab.sh'), argv)
                self_case.assertEqual(argv[argv.index('--pairs') + 1], '15')
                if mode == 'stop':
                    return {'reason': 'fixture_active_stop', 'rc': 75, 'children_drained': True}
                ab = workdir / 'ab'
                ab.mkdir()
                manifest = json.loads((HERE / 'RETAINED-READSET.json').read_text())
                for name in manifest:
                    shutil.copy2(test_arm_order.RETAINED / name, ab / name)
                if mode == 'bad_order':
                    log = (ab / 'ab_arms.log').read_text()
                    (ab / 'ab_arms.log').write_text(log.replace('arm 1P: launching', 'arm 2C: launching', 1))
                return {'reason': None, 'rc': 0, 'children_drained': True}

        self_case = self
        env = {'FILLER_ID': job.ID, 'WS58_REGIONS': 'mi210_0,72-79', 'FILLER_CPUS': '72-79',
               'FILLER_DEADLINE': str(time.time() + 7200), 'FILLER_STOPFILE': str(root / 'UNCREATED-STOP')}
        with patch.object(job, 'HERE', root), patch.object(job, 'pins', return_value=proto), patch.object(job, 'sha', fixture_sha), patch.object(job.os, 'sched_getaffinity', return_value=set(range(72, 80))), patch.object(job.produce, 'OwnedStep', ServiceAdapter), patch.dict(os.environ, env):
            if mode == 'bad_order':
                with self.assertRaisesRegex(ValueError, 'duplicate native launch|execution sequence'):
                    job.main()
                self.assertFalse((job.ATTEMPT_ROOT / 'RESULT.json').exists())
                return
            rc = job.main()
        result = json.loads((job.ATTEMPT_ROOT / 'RESULT.json').read_text())
        self.assertEqual(rc, 75 if mode == 'stop' else 0)
        if mode == 'stop':
            self.assertTrue(result['partial'])
            self.assertIsNone(result['full_gate_pass'])
        else:
            self.assertTrue(result['full_gate_pass'])
            self.assertEqual(len(result['execution_order_proof']['tags_in_execution_order']), 30)
            self.assertEqual(result['original_result_sha256'], real_sha(test_arm_order.RETAINED / 'result.json'))
        (root / 'CONTROL-SCOPE.json').write_text(json.dumps({'scope':'MODEL_FREE_ACTUAL_MAIN_EXTERNAL_BOUNDARY_ADAPTERS_ONLY','mode':mode,'no_native_or_real_grant':True,'not_scientific_ingest':True}) + '\n')

    def test_actual_main_retained_native_and_result_writer(self):
        self.exercise('normal')

    def test_actual_main_rejects_bad_execution(self):
        self.exercise('bad_order')

    def test_actual_main_preserves_partial75(self):
        self.exercise('stop')


if __name__ == '__main__':
    unittest.main(verbosity=2)
