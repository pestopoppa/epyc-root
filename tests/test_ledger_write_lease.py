"""Scratch subprocess fixtures only. No canonical paths; root must run serially."""
import os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts/vidya'))
from ledger_write_lease import OwnedWriteLease,LeaseBroken,LeasedLedger

class LeaseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'ledger';self.path.write_bytes(b'prefix\n')
 def test_owned_lease_and_release(self):
  with OwnedWriteLease(self.path) as lease:lease.check()
  with self.path.open('ab') as f:f.write(b'peer\n')
  self.assertEqual(self.path.read_bytes(),b'prefix\npeer\n')
 def test_actual_native_append_and_read_under_lease(self):
  from ledger import Ledger
  from adapters import research_intake as native
  self.path.unlink();frame=native._frames_for_entry({"id":"intake-2003","url":"https://example.org/lease-fixture","key_claims":["synthetic fixture"],"verification":"stage1-unverified"},"2026-10-06T00:00:00Z")[0]
  Ledger(self.path).append(frame)
  with OwnedWriteLease(self.path) as lease:
   ledger=LeasedLedger(lease);self.assertEqual(len(ledger.read_all()),1);lease.append(ledger,frame);self.assertEqual(len(ledger.read_all()),2);self.assertEqual(ledger.verify(),[]);self.assertTrue(lease.read_bytes().endswith(b"\n"))
 def test_existing_peer_descriptor_refuses(self):
  child=subprocess.Popen([sys.executable,'-c','import sys; f=open(sys.argv[1],"rb"); print("ready",flush=True); sys.stdin.read()',str(self.path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  try:
   self.assertEqual(child.stdout.readline().strip(),'ready')
   with self.assertRaises(OSError):
    with OwnedWriteLease(self.path):pass
   self.assertEqual(self.path.read_bytes(),b'prefix\n')
  finally:child.communicate('',timeout=5)
 def test_break_request_aborts_before_mutation(self):
  child=None
  try:
   with self.assertRaises(LeaseBroken):
    with OwnedWriteLease(self.path) as lease:
     child=subprocess.Popen([sys.executable,'-c','import os,sys;\ntry: fd=os.open(sys.argv[1],os.O_WRONLY|os.O_NONBLOCK); os.close(fd)\nexcept BlockingIOError: pass',str(self.path)])
     child.wait(timeout=5);lease.check()
  finally:
   if child is not None:child.wait(timeout=5)
  self.assertEqual(self.path.read_bytes(),b'prefix\n')
 def test_path_replacement_refuses(self):
  with OwnedWriteLease(self.path) as lease:
   other=self.path.with_suffix('.other');other.write_bytes(b'peer\n');os.replace(other,self.path)
   with self.assertRaises(LeaseBroken):lease.check()
  self.assertEqual(self.path.read_bytes(),b'peer\n')
if __name__=='__main__':unittest.main()
