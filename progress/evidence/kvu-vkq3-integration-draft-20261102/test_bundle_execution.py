"""Model-free qualification executes the prepared module bundle in isolation."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import bundle_preflight as bp


class BundleExecutionTests(unittest.TestCase):
    def test_synthetic_qualification_uses_prepared_bundle(self):
        src = Path(bp.__file__).resolve().parent
        guard = src.parent / 'kvu-vkq3-guard-review-20261102' / 'guard.py'
        pins = {str(Path('launcher') / n): bp.digest(src / n) for n in bp.MODULES}
        pins['kvu-vkq3-guard-review-20261102/guard.py'] = bp.digest(guard)
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            bundle = Path(tmp) / 'prepared'
            bp.prepare_bundle(src, guard, bundle, pins)
            # -I removes cwd and PYTHONPATH from import resolution. Load the
            # existing model-free lifecycle test only after pinning the bundle.
            program = r'''
import importlib.util
from pathlib import Path
import sys
import unittest
bundle = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(bundle / 'launcher'))
import rowflow_worker, grant_bridge_draft, worker_draft, supervisor
import contained_supervisor_draft, completion_draft, receipts
for module in (rowflow_worker, grant_bridge_draft, worker_draft, supervisor,
               contained_supervisor_draft, completion_draft, receipts):
    assert Path(module.__file__).resolve().parent == bundle / 'launcher', module.__file__
assert grant_bridge_draft._GUARD_PATH.resolve() == bundle / 'kvu-vkq3-guard-review-20261102' / 'guard.py'
assert Path(rowflow_worker._WRAPPER).resolve() == bundle / 'launcher' / 'pdeath_exec_draft.py'
spec = importlib.util.spec_from_file_location('lifecycle_test', sys.argv[2])
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test))
sys.exit(not result.wasSuccessful())
'''
            run = subprocess.run([sys.executable, '-I', '-B', '-c', program,
                                  str(bundle), str(src / 'test_rowflow_end_to_end.py')],
                                 cwd=bundle / 'launcher', capture_output=True, text=True,
                                 timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('Ran 1 test', run.stderr)


if __name__ == '__main__':
    unittest.main()
