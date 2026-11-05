#!/usr/bin/env python3
"""No GPU: exercise custody refusal, parser and capture comparator."""
import importlib.util,json,os,pathlib,shutil,subprocess,sys,tempfile,unittest
D=pathlib.Path(__file__).resolve().parent
class Offline(unittest.TestCase):
 def test_bind_rejects_absent_build(self):
  if pathlib.Path('/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/c6-b4-build-20261105/BUILD-RESULT.json').exists(): self.skipTest('build present; do not bind real artifact')
  p=subprocess.run([sys.executable,'-B',str(D/'bind.py')],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0); self.assertIn('BIND_REFUSED',p.stderr); self.assertFalse((D/'BOUND.json').exists())
 def test_comparator_and_tamper(self):
  sys.path.insert(0,str(D));from compare_capture import compare
  prior=pathlib.Path('/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/c6-n5/prior-candidate')
  self.assertTrue(compare(prior,prior)['input_bytes_equal'])
  with tempfile.TemporaryDirectory() as t:
   c=pathlib.Path(t)/'capture';shutil.copytree(prior,c)
   p=c/'candidate_weight.bin';b=bytearray(p.read_bytes());b[0]^=1;p.write_bytes(b)
   with self.assertRaises(ValueError):compare(prior,c)
 def test_routes_and_custody_refusal(self):
  with tempfile.TemporaryDirectory() as t:
   t=pathlib.Path(t)
   for f in ('job.py','bind.py','residency.py','compare_capture.py','grant_evidence.py','spec.json'):shutil.copy(D/f,t/f)
   (t/'BOUND.json').write_text(json.dumps({'baseline':{},'corrected':{},'build_receipt':str(t/'missing')}))
   # Import with valid minimal shape, then assert missing receipts refuse before any GPU work.
   binding=json.loads((t/'BOUND.json').read_text())
   for arm in ('baseline','corrected'):binding[arm]={'binary':'/missing','library_dir':'/missing'}
   (t/'BOUND.json').write_text(json.dumps(binding));sys.path.insert(0,str(t))
   spec=importlib.util.spec_from_file_location('candidate_job_for_test',t/'job.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   n4='GGML_CUDA_MUL_MAT_ROUTE route=MMVQ src0=a src1=b dst=out type=q4_K cc=1 src0_ne=[256,16,3,2] src1_ne=[256,4,6,4] dst_ne=[16,4,6,4] ne11=4'
   n5='GGML_CUDA_MUL_MAT_ROUTE route=MMQ src0=a src1=b dst=out type=q4_K cc=1 src0_ne=[256,16,1,1] src1_ne=[256,5,1,1] dst_ne=[16,5,1,1] ne11=5'
   self.assertEqual(m.ROUTE.search(n4).group(1),'MMVQ');self.assertEqual(m.ROUTE.search(n5).group(1),'MMQ')
   with self.assertRaises((FileNotFoundError,KeyError)):m.check_inputs()
if __name__=='__main__':unittest.main()
