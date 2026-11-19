#!/usr/bin/env python3
"""Model-free tests of the combined supervisor; no GPU or model access."""
import importlib.util, json, os, signal, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import output_reserve
for n in ('guard','owned_drain','lock_witness','gpu_smoke_admission','ram_admission','publisher_smoke'):
 sys.modules[n]=types.ModuleType(n)
spec=importlib.util.spec_from_file_location('candidate_supervisor',D/'supervisor.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class TestSupervisor(unittest.TestCase):
 def test_integrated_loop_and_terminal_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); calls=[]
   s.D=root
   s.owned_drain.children=lambda: []
   s.owned_drain.enable=lambda: calls.append('enable')
   s.owned_drain.drain=lambda: calls.append('drain')
   s.lock_witness.capture_gpu=lambda: ('owner','identity')
   s.lock_witness.verify_gpu=lambda *a: calls.append('lock')
   s.guard.boundary=lambda: calls.append('boundary')
   s.guard.BIN=root/'binary';s.guard.ID='test'
   s.publisher_smoke.context=lambda _:None
   s.gpu_smoke_admission.check=lambda **_:None
   class Child:
    pid=987654321
    def __init__(self,*a,**kw):
     self.n=0
     (Path(os.environ['KPF_OUTPUT_ROOT'])/'SMOKE-REQUEST.json').write_text('{}')
    def poll(self):
     self.n+=1
     return None if self.n==1 else 0
    def wait(self,timeout=None):return 0
   oldsignal={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
   original=Path.read_text
   def read(path,*a,**kw):
    if str(path).endswith('/mem_info_vram_used'): return '0'
    return original(path,*a,**kw)
   try:
    with patch.object(sys,'argv',['supervisor','normal']),patch.dict(os.environ,{'FILLER_CPUS':'0-3'},clear=False),patch.object(s.subprocess,'Popen',Child),patch.object(Path,'read_text',read),patch.object(s.time,'sleep',lambda _:None):
     rc=s.main()
   finally:
    for sig,handler in oldsignal.items():signal.signal(sig,handler)
   self.assertEqual(rc,0)
   self.assertGreaterEqual(calls.count('lock'),2);self.assertGreaterEqual(calls.count('boundary'),3);self.assertIn('drain',calls)
   attempt=next((root/'attempts').glob('run-*'))
   receipt=json.loads((attempt/'RESULT.json').read_text())
   self.assertEqual([x['stage'] for x in receipt['samples']],['before-admission','running','after-drain'])
   sidecar=json.loads((attempt/'terminal-accounting.json').read_text())
   self.assertEqual(int(sidecar['terminal_bytes']),output_reserve.owned_bytes(attempt))
   self.assertEqual(sidecar['unsampled_peak'],'unknown')
 def test_terminal_failure_removes_success(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);s.D=root
   s.owned_drain.children=lambda: [];s.owned_drain.enable=lambda:None;s.owned_drain.drain=lambda:None
   s.lock_witness.capture_gpu=lambda: ('owner','identity');s.lock_witness.verify_gpu=lambda *a:None
   s.guard.boundary=lambda:None;s.guard.BIN=root/'binary';s.guard.ID='test'
   s.publisher_smoke.context=lambda _:None;s.gpu_smoke_admission.check=lambda **_:None
   class Child:
    pid=987654321
    def __init__(self,*a,**kw):(Path(os.environ['KPF_OUTPUT_ROOT'])/'SMOKE-REQUEST.json').write_text('{}')
    def poll(self):return 0
    def wait(self,timeout=None):return 0
   oldsignal={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
   try:
    with patch.object(sys,'argv',['supervisor','normal']),patch.dict(os.environ,{'FILLER_CPUS':'0-3'},clear=False),patch.object(s.subprocess,'Popen',Child),patch.object(s,'sample_attempt',side_effect=[0,0,RuntimeError('budget')]):
     rc=s.main()
   finally:
    for sig,handler in oldsignal.items():signal.signal(sig,handler)
   self.assertEqual(rc,75)
   attempt=next((root/'attempts').glob('run-*'))
   self.assertFalse((attempt/'RESULT.json').exists())
 def test_terminal_self_accounting_detects_allocation_change(self):
  # A filesystem that changes allocation during the fixed-width rewrite must refuse.
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);s.D=root
   s.owned_drain.children=lambda: [];s.owned_drain.enable=lambda:None;s.owned_drain.drain=lambda:None
   s.lock_witness.capture_gpu=lambda: ('owner','identity');s.lock_witness.verify_gpu=lambda *a:None
   s.guard.boundary=lambda:None;s.guard.BIN=root/'binary';s.guard.ID='test'
   s.publisher_smoke.context=lambda _:None;s.gpu_smoke_admission.check=lambda **_:None
   class Child:
    pid=987654321
    def __init__(self,*a,**kw):(Path(os.environ['KPF_OUTPUT_ROOT'])/'SMOKE-REQUEST.json').write_text('{}')
    def poll(self):return 0
    def wait(self,timeout=None):return 0
   oldsignal={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
   try:
    with patch.object(sys,'argv',['supervisor','normal']),patch.dict(os.environ,{'FILLER_CPUS':'0-3'},clear=False),patch.object(s.subprocess,'Popen',Child),patch.object(s,'sample_attempt',side_effect=[0,0,4096,8192]):
     rc=s.main()
   finally:
    for sig,handler in oldsignal.items():signal.signal(sig,handler)
   self.assertEqual(rc,75)
   attempt=next((root/'attempts').glob('run-*'))
   self.assertFalse((attempt/'RESULT.json').exists())
 def test_scanner_rejects_symlink_and_cap(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'link').symlink_to('/dev/null')
   with self.assertRaises(RuntimeError):s.sample_attempt(root)
   (root/'link').unlink();(root/'data').write_bytes(b'hello')
   with patch.object(output_reserve,'CAP',1):
    with self.assertRaises(RuntimeError):s.sample_attempt(root)
if __name__=='__main__':unittest.main()
