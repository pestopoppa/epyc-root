import unittest
from job import gauge
class GaugeTest(unittest.TestCase):
 def test_supported_with_labels(self):self.assertEqual(gauge('# HELP x foo\nllamacpp:kv_cache_used_cells{model="x"} 7\n'),7)
 def test_missing_is_not_zero(self):
  with self.assertRaises(ValueError):gauge('llamacpp:other 0\n')
 def test_ambiguous_is_rejected(self):
  with self.assertRaises(ValueError):gauge('llamacpp:kv_cache_used_cells 1\nllamacpp:kv_cache_used_cells 2\n')
 def test_negative_and_fraction_rejected(self):
  for value in ('-1','1.5'):
   with self.subTest(value=value),self.assertRaises(ValueError):gauge('llamacpp:kv_cache_used_cells '+value+'\n')

class CustodyTest(unittest.TestCase):
 def test_exact_overlap_accepted_and_outside_refused(self):
  from job import require_overlap
  require_overlap(10,20,{'start_monotonic_ns':11,'end_monotonic_ns':19})
  for sample in ({'start_monotonic_ns':9,'end_monotonic_ns':11},{'start_monotonic_ns':19,'end_monotonic_ns':21},{'start_monotonic_ns':14,'end_monotonic_ns':13}):
   with self.subTest(sample=sample),self.assertRaises(RuntimeError):require_overlap(10,20,sample)
 def test_device_inode_and_content_binding(self):
  import hashlib,os,tempfile
  from pathlib import Path
  from job import verify_sample
  with tempfile.TemporaryDirectory() as d:
   samples=[];files={}
   for name in ('libggml-cpu.so','libggml-base.so','libllama.so'):
    p=Path(d)/name;p.write_bytes(name.encode());st=p.stat();key=str(p.resolve());files[key]=hashlib.sha256(p.read_bytes()).hexdigest();samples.append({'path':key,'dev_major':os.major(st.st_dev),'dev_minor':os.minor(st.st_dev),'inode':st.st_ino})
   self.assertEqual(len(verify_sample({'libraries':samples},files)),3)
   samples[0]['inode']+=1
   with self.assertRaises(RuntimeError):verify_sample({'libraries':samples},files)
   samples[0]['inode']-=1;Path(samples[0]['path']).write_bytes(b'altered')
   with self.assertRaises(RuntimeError):verify_sample({'libraries':samples},files)

if __name__=='__main__':unittest.main()
