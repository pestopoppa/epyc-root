"""Exercise a source-pinned copied supervisor against inert owned children.

No model, server, GPU or native candidate is launched. Run only under rowflow.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import select
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
REAL_POPEN = subprocess.Popen
sys.path.insert(0, str(ROOT))
for name in ('guard', 'lock_witness', 'gpu_smoke_admission', 'ram_admission', 'publisher_smoke'):
 sys.modules[name] = types.ModuleType(name)
spec = importlib.util.spec_from_file_location('successor_supervisor', ROOT/'supervisor.py')
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


class RealSupervisor(unittest.TestCase):
 def run_case(self, scenario):
  with tempfile.TemporaryDirectory(prefix='g3-lifecycle-') as tmp:
   dest = Path(tmp); child_pids=[]; descendant_pids=[]; count=[0]
   def boundary():
    count[0] += 1
    if scenario in ('STOP','deadline') and count[0] >= 3:
     raise ValueError(scenario)
   def popen(args, **kwargs):
    (Path(kwargs['env']['KPF_OUTPUT_ROOT'])/'SMOKE-REQUEST.json').write_text('{}')
    reader, writer = os.pipe()
    parent_action = "time.sleep(30)" if scenario in ('STOP', 'deadline') else ("raise SystemExit(7)" if scenario == 'failure' else "pass")
    command = ("import os,time\nfd=int(os.environ['TEST_READY_FD'])\npid=os.fork()\n"
               "if pid == 0:\n time.sleep(30)\n os._exit(0)\n"
               "os.write(fd,(str(pid)+'\\n').encode())\nos.close(fd)\n" + parent_action)
    env = dict(kwargs['env'], TEST_READY_FD=str(writer))
    kwargs['env'] = env
    try:
     p=REAL_POPEN([sys.executable, '-c', command], pass_fds=(writer,), **kwargs)
     child_pids.append(p.pid)
    finally:
     os.close(writer)
    try:
     if not select.select([reader], [], [], 5)[0]: raise RuntimeError('owned child did not report descendant')
     data=os.read(reader, 80)
     descendant_pids.append(int(data.strip()))
    finally:
     os.close(reader)
    return p
   original_read=Path.read_text
   def read(path,*a,**k):
    return '0' if str(path)=='/sys/class/drm/card2/device/mem_info_vram_used' else original_read(path,*a,**k)
   env={'FILLER_CPUS':','.join(str(i) for i in sorted(os.sched_getaffinity(0))[:4]), 'FILLER_ID':'synthetic-row'}
   fake_lock=types.SimpleNamespace(capture_gpu=lambda:('owner','identity'),verify_gpu=lambda *a:None)
   fake_guard=types.SimpleNamespace(boundary=boundary, BIN='/unused',ID='synthetic-row')
   with mock.patch.object(supervisor,'D',dest), mock.patch.object(supervisor,'lock_witness',fake_lock), mock.patch.object(supervisor,'guard',fake_guard), mock.patch.object(supervisor,'gpu_smoke_admission',types.SimpleNamespace(check=lambda **k:None)), mock.patch.object(supervisor,'publisher_smoke',types.SimpleNamespace(context=lambda *_:None)), mock.patch.object(supervisor.subprocess,'Popen',side_effect=popen), mock.patch.object(Path,'read_text',read), mock.patch.dict(os.environ,env,clear=False), mock.patch.object(sys,'argv',['supervisor.py','normal']):
    rc=supervisor.main()
   attempts=list((dest/'attempts').glob('run-*')); self.assertEqual(len(attempts),1)
   result=json.loads(next(attempts[0].glob('*RESULT.json') if rc != 75 else attempts[0].glob('PARTIAL.json')).read_text())
   self.assertTrue(result['children_drained']); self.assertEqual(len(child_pids),1); self.assertEqual(len(descendant_pids),1)
   for pid in child_pids + descendant_pids: self.assertFalse(Path('/proc',str(pid)).exists(),f'captured PID {pid} survived')
   return rc,result
 def test_normal(self):
  rc,_=self.run_case('normal');self.assertEqual(rc,0)
 def test_stop(self):
  rc,r=self.run_case('STOP');self.assertEqual(rc,75);self.assertIn('STOP',r['reason'])
 def test_deadline(self):
  rc,r=self.run_case('deadline');self.assertEqual(rc,75);self.assertIn('deadline',r['reason'])
 def test_child_failure(self):
  rc,_=self.run_case('failure');self.assertEqual(rc,7)

if __name__=='__main__': unittest.main()
