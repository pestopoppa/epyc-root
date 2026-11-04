import unittest
from sysfs_residency import correlate

class CorrelationTest(unittest.TestCase):
 def setUp(self):
  self.call={'invocation':4,'native_begin':1.,'native_dispatch':2.,'native_end':3.}
  self.one={'pid':42,'birth':7,'gpu_id':22,'hip_mapped':True,'kfd_pid_present':True,'own_vram_bytes':100,'device_vram_bytes':200,'observation_start':1.9,'observation_end':2.1}
  self.two=dict(self.one,observation_start=1.1,observation_end=1.2)
 def test_two_persistent_samples_with_one_dispatch_overlap(self):
  self.assertEqual(correlate(calls=[self.call],samples=[self.one,self.two],pid=42,birth=7,gpu_id=22)[0]['status'],'BOUNDED_OBSERVATION')
 def test_one_sample_or_wrong_gpu_is_unknown(self):
  for samples in ([self.one],[self.one,dict(self.one)],[self.one,dict(self.two,gpu_id=23)]):
   self.assertEqual(correlate(calls=[self.call],samples=samples,pid=42,birth=7,gpu_id=22)[0]['status'],'UNKNOWN')
 def test_no_overlap_or_outside_invocation_is_unknown(self):
  self.one['observation_end']=1.95
  self.assertEqual(correlate(calls=[self.call],samples=[self.one,self.two],pid=42,birth=7,gpu_id=22)[0]['status'],'UNKNOWN')
 def test_nonfinite_and_wrong_identity_refused(self):
  for val in (float('nan'),float('inf'),float('-inf')):
   call=dict(self.call,native_dispatch=val)
   with self.assertRaises(ValueError): correlate(calls=[call],samples=[self.one,self.two],pid=42,birth=7,gpu_id=22)
  self.one['birth']=8
  self.assertEqual(correlate(calls=[self.call],samples=[self.one,self.two],pid=42,birth=7,gpu_id=22)[0]['status'],'UNKNOWN')

class FixtureTest(unittest.TestCase):
 def test_process_identity_backend_and_own_gpu_binding(self):
  import os,tempfile
  from pathlib import Path
  from sysfs_residency import read_sysfs_sample
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); proc=root/'proc/42'; proc.mkdir(parents=True)
   (proc/'stat').write_text('42 (test server) S '+' '.join(['0']*18+['12345']+['0']*4))
   backend=root/'backend.so'; backend.write_bytes(b'backend'); st=backend.stat()
   (proc/'maps').write_text(f'0000-0001 r-xp 0000 {os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x} {st.st_ino} {backend}\n')
   gpu=root/'kfd/42'; gpu.mkdir(parents=True); (gpu/'vram_22').write_text('4096')
   vram=root/'vram'; vram.write_text('8192')
   device={'gpu_id':22,'device_vram':str(vram)}
   r=read_sysfs_sample(pid=42,birth=12345,device=device,backend=backend,proc_root=root/'proc',kfd_root=root/'kfd')
   self.assertTrue(r['hip_mapped']); self.assertTrue(r['kfd_pid_present']); self.assertEqual(r['own_vram_bytes'],4096)
   with self.assertRaises(ValueError): read_sysfs_sample(pid=42,birth=1,device=device,backend=backend,proc_root=root/'proc',kfd_root=root/'kfd')
   self.assertIsNone(read_sysfs_sample(pid=42,birth=12345,device={'gpu_id':23,'device_vram':str(vram)},backend=backend,proc_root=root/'proc',kfd_root=root/'kfd')['own_vram_bytes'])

if __name__ == '__main__': unittest.main()
