#!/usr/bin/env python3
import hashlib, json, os, pathlib, shutil, signal, subprocess, sys, tempfile, time
D=pathlib.Path(__file__).resolve().parent
SRC=D/'src'
BASE='729599d69871181d67af715a4c2f9162d5153a2e'
def sha(p):
 with open(p,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def source_manifest():
 files=subprocess.check_output(['git','-C',str(SRC),'ls-files','-z']).split(b'\0')
 result={}
 for raw in files:
  if not raw: continue
  p=os.fsdecode(raw); f=SRC/p
  result[p]=('symlink:'+os.readlink(f)) if f.is_symlink() else sha(f)
 return result
def stopped():
 return pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time() >= float(os.environ['FILLER_DEADLINE'])-60

class InterruptedBuild(Exception):
 pass

def run_owned(argv, log):
 """Keep a handle to the owned subprocess group and reap it on STOP/deadline."""
 proc=subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
 try:
  while proc.poll() is None:
   if stopped(): raise InterruptedBuild()
   time.sleep(0.2)
  if proc.returncode: raise subprocess.CalledProcessError(proc.returncode, argv)
 finally:
  # The group was created by this process; terminate descendants even if its
  # original leader has just exited. Never target a group by name.
  try: os.killpg(proc.pid, signal.SIGTERM)
  except ProcessLookupError: pass
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:
   try: os.killpg(proc.pid, 0)
   except ProcessLookupError: break
   proc.poll()
   time.sleep(0.1)
  else:
   try: os.killpg(proc.pid, signal.SIGKILL)
   except ProcessLookupError: pass
  try: proc.wait(timeout=3)
  except subprocess.TimeoutExpired: raise RuntimeError('owned build process did not exit')
  try: os.killpg(proc.pid, 0)
  except ProcessLookupError: pass
  else: raise RuntimeError('owned build process group still exists after cleanup')

def main():
 if subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip()!=BASE: raise ValueError('wrong source base')
 if sha(D/'candidate.patch') != '14607eb73b89c3a54521781948034f233e2d369b036de5967026766c83f23a78': raise ValueError('patch changed')
 if source_manifest()!=json.loads((D/'source-manifest.json').read_text()): raise ValueError('source content changed')
 if sha(D/'BUILD-IDENTITY.json')!=json.loads((D/'pins.json').read_text())['build_identity_sha256']: raise ValueError('build identity changed')
 if stopped(): return 75
 out=D/('run-'+str(time.time_ns())); out.mkdir()
 temp=pathlib.Path(tempfile.mkdtemp(prefix='c6-n4-cublas-',dir='/dev/shm'))
 def onterm(signum,frame): raise SystemExit(75)
 signal.signal(signal.SIGTERM,onterm)
 try:
  identity=json.loads((D/'BUILD-IDENTITY.json').read_text())
  conf=[s.replace(identity['source'],str(SRC)).replace(identity['output'],str(temp)) for s in identity['configure_argv']]
  with (out/'configure.log').open('wb') as log: run_owned(conf,log)
  if stopped(): return 75
  with (out/'build.log').open('wb', buffering=0) as log: run_owned(['cmake','--build',str(temp),'--target','test-backend-ops','-j','4'],log)
  if stopped(): return 75
  if source_manifest()!=json.loads((D/'source-manifest.json').read_text()): raise ValueError('source changed during build')
  image=out/'bin'; shutil.copytree(temp/'bin',image,symlinks=True)
  hip=next(x for x in image.glob('libggml-hip.so.*') if x.is_file() and not x.is_symlink())
  binary=image/'test-backend-ops'
  if b'CUBLAS_Q4K_N4' not in hip.read_bytes(): raise ValueError('route marker missing in built HIP library')
  files={str(x.relative_to(image)):sha(x) for x in image.rglob('*') if x.is_file() and not x.is_symlink()}
  links={str(x.relative_to(image)):os.readlink(x) for x in image.rglob('*') if x.is_symlink()}
  result={'status':'COMPLETE_BUILD_ONLY','source_base':BASE,'source_manifest_sha256':sha(D/'source-manifest.json'),'patch_sha256':sha(D/'candidate.patch'),'build_identity_sha256':sha(D/'BUILD-IDENTITY.json'),'configuration':conf,'candidate_hip_sha256':sha(hip),'binary_sha256':sha(binary),'files':files,'symlinks':links,'run':str(out),'gpu_execution':False,'full_gak_pass':None}
  tmp=D/'RESULT.tmp'; tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); os.replace(tmp,D/'RESULT.json'); return 0
 except InterruptedBuild: return 75
 finally: shutil.rmtree(temp,ignore_errors=True)
if __name__=='__main__': sys.exit(main())
