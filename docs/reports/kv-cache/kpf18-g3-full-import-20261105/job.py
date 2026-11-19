#!/usr/bin/env python3
"""Import the retained full G3 driver without entering its native main."""
import hashlib, json, os, pathlib, shutil, subprocess, sys, time
D=pathlib.Path(__file__).resolve().parent
BASE=pathlib.Path('/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105')
C=BASE/'candidate'; MANIFEST='5fe60fc56a6ad7c387763e17715b4a467edf00078a533ab9b4151bd30e74e85a'
LAUNCH='18aa8309056740df2c322e41e77e6a4ae4dc2fd10708708705a4d7e4e23dae18'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def boundary():
 if (os.environ.get('FILLER_STOPFILE') and pathlib.Path(os.environ['FILLER_STOPFILE']).exists()) or (D/'STOP').exists() or time.time()>=float(os.environ.get('FILLER_DEADLINE','9999999999')):raise RuntimeError('STOP/deadline')
def main():
 smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1'
 out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if sys.argv[1:]==['--complete']:
  r=json.loads(out.read_text());boundary();assert r['status']=='IMPORTED' and r['module_count']>0;return
 boundary()
 if sha(BASE/'ALL-SOURCES.sha256')!=MANIFEST or sha(BASE/'launch.sh')!=LAUNCH:raise RuntimeError('inventory or launcher drift')
 # The retained custody-check entry refuses native execution and binds all sources.
 subprocess.run(['bash',str(BASE/'launch.sh'),'custody-check'],check=True,timeout=120,stdout=subprocess.DEVNULL)
 boundary(); parent=C/'attempts'; parent.mkdir(exist_ok=True)
 if parent.is_symlink() or not parent.is_dir():raise RuntimeError('unsafe attempts parent')
 root=parent/('run-'+str(os.getpid()));root.mkdir()
 try:
  env=dict(os.environ,KPF_OUTPUT_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
  proc=subprocess.run([sys.executable,'-I','-B',str(D/'worker.py'),str(C)],env=env,capture_output=True,text=True,timeout=120,check=True)
  x=json.loads(proc.stdout);boundary()
  subprocess.run(['bash',str(BASE/'launch.sh'),'custody-check'],check=True,timeout=120,stdout=subprocess.DEVNULL)
  if sha(BASE/'ALL-SOURCES.sha256')!=MANIFEST or sha(BASE/'launch.sh')!=LAUNCH:raise RuntimeError('post-import drift')
  if not x['main_callable'] or not x['setup_callable'] or not x['gate_run_callable']:raise RuntimeError('missing driver symbols')
  x.update(status='IMPORTED',scope='full driver import only; no main, native lifecycle, model, GPU or custody guarantee during import')
  out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('x') as f:json.dump(x,f,sort_keys=True);f.write('\n')
 finally:
  shutil.rmtree(root)
  try:parent.rmdir()
  except OSError:pass
if __name__=='__main__':main()
