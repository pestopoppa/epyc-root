import pathlib, unittest, subprocess, sys
from unittest.mock import patch
import native_functional as diagnostic

class Repair(unittest.TestCase):
 def test_real_owner_module_imports(self):
  self.assertEqual(diagnostic.RequestCapture.__module__, 'owner_hook')
  self.assertEqual(diagnostic.CPUS,(0,1,2,3))
 def test_capture_worker_imports_in_isolated_interpreter(self):
  native = pathlib.Path(__file__).resolve().parent / 'native'
  code = "import sys; sys.path.insert(0, sys.argv[1]); import capture_worker"
  subprocess.run([sys.executable, '-I', '-c', code, str(native)], check=True, capture_output=True, text=True)
 def test_worker_entrypoint_runs_under_isolated_python(self):
  native = pathlib.Path(__file__).resolve().parent / 'native'
  result = subprocess.run([sys.executable, '-I', '-B', str(native / 'capture_worker.py'), '--help'], capture_output=True, text=True, timeout=10)
  self.assertEqual(result.returncode, 0, result.stderr)
  self.assertIn('--control-fd', result.stdout)
 def test_context_is_bound_to_controlled_child(self):
  p=pathlib.Path('/tmp/example-only.json')
  with patch.object(diagnostic,'RequestCapture') as factory:
   diagnostic.make_capture(p,2)
  args,kwargs=factory.call_args
  self.assertEqual(args,(p,{0,1,2,3}))
  self.assertEqual(kwargs['request_context'],{'launch_ordinal':2,'phase':'diagnostic','slot_index':0,'prompt_id':'controlled-child','request_sha256':'0'*64})
  self.assertEqual(kwargs['timeout_s'],20)
if __name__=='__main__':unittest.main()
