"""Model-free tests for isolation and receipts; no compiler or GPU is run."""
import importlib.util,json,os,tempfile,time,unittest
from pathlib import Path
from unittest import mock
spec=importlib.util.spec_from_file_location('kvu_build_job',Path(__file__).with_name('job.py'))
job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)
class Tests(unittest.TestCase):
 def test_modes_configure_both_and_full_builds_distinct_arms(self):
  for dry in (True,False):
   with self.subTest(dry=dry),tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
    root=Path(tmp);src=root/'source';out=root/'output';src.mkdir();out.mkdir();(root/'source-pair.json').write_text('{}');(root/'toolchain.sha256').write_text('test');(root/'sealed-source-receipt.json').write_text(json.dumps({'files_sha256':'a'*64}))
    for arm in ('base','candidate'):(src/arm).mkdir()
    dryroot=root/'dry';result=dryroot/'native-attempts'/'attempt-1'/'native-result.json';result.parent.mkdir(parents=True)
    calls=[]
    def fake(cmd,**kwargs):
     calls.append(cmd)
     if '-B' in cmd:
      build=Path(cmd[cmd.index('-B')+1]);(build/'CMakeCache.txt').write_text('GGML_HIP:BOOL=ON\nCMAKE_HOME_DIRECTORY:INTERNAL='+cmd[cmd.index('-S')+1]+'\n')
     else:
      build=Path(cmd[cmd.index('--build')+1]);binary=build/'bin';binary.mkdir()
      (binary/'test-backend-ops').write_bytes(build.name.encode())
      (binary/'libggml-hip.so').write_bytes(build.name.encode()+b'-hip')
    env={'FILLER_ID':'handoff-kvu-kvu19a2-build-20261102','FILLER_DRYRUN':'1' if dry else '0','FILLER_DRYRUN_RESULT_PATH':str(result),'FILLER_DRYRUN_DIR':str(dryroot),'FILLER_DEADLINE':str(int(time.time())+600),'FILLER_STOPFILE':str(root/'stop'),'FILLER_THREADS':'4'}
    with mock.patch.object(job,'D',root),mock.patch.object(job.source_guard,'open_sealed_source',side_effect=lambda *a:os.open(src,os.O_RDONLY|os.O_DIRECTORY)),mock.patch.object(job.source_guard,'proc_path',return_value=src),mock.patch.object(job,'OUT',out),mock.patch.object(job,'check'),mock.patch.object(job.subprocess,'run',side_effect=fake),mock.patch.dict(os.environ,env,clear=True):
     self.assertEqual(job.main(),0)
    rec=json.loads((result if dry else out/'RESULT.json').read_text())
    self.assertEqual(rec['status'],'configured' if dry else 'built')
    self.assertEqual(len(calls),2 if dry else 4)
    self.assertEqual(set(rec['outputs']),{'base','candidate'})
    if not dry:self.assertNotEqual(rec['outputs']['base']['test_sha256'],rec['outputs']['candidate']['test_sha256'])
    self.assertFalse((out/'RESULT.json').exists() if dry else result.exists())
 def test_source_path_and_generated_metadata_fail_closed(self):
  with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
   root=Path(tmp);build=root/'build';build.mkdir();cache=build/'CMakeCache.txt';anchor=Path('/proc/123/fd/7/base')
   cache.write_text('CMAKE_HOME_DIRECTORY:INTERNAL=/mutable/base\n')
   with mock.patch.object(job,'D',root),self.assertRaisesRegex(ValueError,'anchored'):
    job.verify_cmake_source(build,anchor,'base')
   cache.write_text('CMAKE_HOME_DIRECTORY:INTERNAL='+str(anchor)+'\n')
   (build/'Makefile').write_text(str(root/'source-sealed-20261102/base'))
   with mock.patch.object(job,'D',root),self.assertRaisesRegex(ValueError,'mutable'):
    job.verify_cmake_source(build,anchor,'base')
 def test_expired_window_refuses_before_work(self):
  with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
   env={'FILLER_ID':'handoff-kvu-kvu19a2-build-20261102','FILLER_DRYRUN':'0','FILLER_DEADLINE':'1','FILLER_STOPFILE':str(Path(tmp)/'stop'),'FILLER_THREADS':'4'}
   with mock.patch.object(job,'OUT',Path(tmp)),mock.patch.dict(os.environ,env,clear=True),mock.patch.object(job,'check') as check,self.assertRaisesRegex(RuntimeError,'deadline'):
    job.main()
   check.assert_not_called()
if __name__=='__main__':unittest.main()
