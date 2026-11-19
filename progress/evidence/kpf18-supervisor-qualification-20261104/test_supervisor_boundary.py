import hashlib, importlib.util, json, os, pathlib, sys, tempfile, types, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'supervisor.py'
EXPECTED = 'a85612e5c878d299c83a2dcac69b6f5126136354c3243c4f38394d56a29b0a9f'
assert hashlib.sha256(SRC.read_bytes()).hexdigest() == EXPECTED

class TestSupervisor(unittest.TestCase):
    def test_loop_boundary_failure_stops_owned_child_and_records_partial(self):
        calls=[]
        def boundary():
            calls.append('boundary')
            if len(calls)==4: raise RuntimeError('output budget exhausted')
        guard=types.SimpleNamespace(boundary=boundary, ID='id', BIN='/fake/binary')
        drain=types.SimpleNamespace(children=lambda:[], enable=lambda:None, drain=lambda:calls.append('drain'))
        lock=types.SimpleNamespace(capture_gpu=lambda:('owner','identity'), verify_gpu=lambda *a:None)
        modules={'guard':guard,'owned_drain':drain,'lock_witness':lock,
                 'gpu_smoke_admission':types.SimpleNamespace(check=lambda **kw:None),
                 'ram_admission':types.SimpleNamespace(check=lambda *args:None)}
        spec=importlib.util.spec_from_file_location('supervisor_test', SRC)
        module=importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, modules): spec.loader.exec_module(module)
        child=types.SimpleNamespace(pid=123, poll=lambda:None)
        realpath=pathlib.Path
        class Vram:
            def read_text(self): return '0'
        def path(arg):
            return Vram() if str(arg)=='/sys/class/drm/card2/device/mem_info_vram_used' else realpath(arg)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(module, 'D', realpath(tmp)), mock.patch.object(module, 'Path', side_effect=path), \
             mock.patch.object(module.subprocess, 'Popen', return_value=child), \
             mock.patch.object(module, 'stop_process', side_effect=lambda p:calls.append(('stop',p))), \
             mock.patch.object(module.time, 'sleep', return_value=None), \
             mock.patch.object(sys, 'argv', ['supervisor.py','normal']):
            rc=module.main()
            receipts=list(realpath(tmp).glob('attempts/run-*/PARTIAL.json'))
            self.assertEqual(rc,75)
            self.assertEqual(len(receipts),1)
            result=json.loads(receipts[0].read_text())
            self.assertTrue(result['partial'])
            self.assertEqual(result['reason'],'output budget exhausted')
            self.assertEqual(calls.count('boundary'),4)
            self.assertIn(('stop',child),calls)
            self.assertEqual(calls[-1],'drain')
            self.assertEqual(result['sampling_overshoot'],'unknown')

if __name__=='__main__': unittest.main()
