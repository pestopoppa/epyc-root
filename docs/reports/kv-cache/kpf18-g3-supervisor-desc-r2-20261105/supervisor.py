#!/usr/bin/python3
"""Own a native gate process and its descendants until all have drained."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import guard,owned_drain,lock_witness,gpu_smoke_admission,ram_admission,publisher_smoke

def stop_process(p, fd):
 # The direct child is captured at Popen. Never signal a process group.
 if p is None:return
 if p.poll() is not None:
  p.wait();return
 if fd is None:
  # pidfd acquisition failed before poll could reap the captured child.
  try:p.kill()
  except ProcessLookupError:pass
  p.wait();return
 try:signal.pidfd_send_signal(fd,signal.SIGTERM)
 except ProcessLookupError:pass
 try:p.wait(timeout=3)
 except subprocess.TimeoutExpired:
  try:signal.pidfd_send_signal(fd,signal.SIGKILL)
  except ProcessLookupError:pass
  p.wait()

def decide(mode, completed, result_ok, forced, boundary_ok):
 if not boundary_ok or forced:return 75
 if not completed:return 75
 return 0 if result_ok else 70

def main():
 if len(sys.argv)!=2 or sys.argv[1] not in ('official','normal','cutoff'):return 64
 mode=sys.argv[1]
 if owned_drain.children():raise RuntimeError('unexpected existing child')
 owned_drain.enable(); interrupted=[False]
 def interrupt(*_):interrupted[0]=True
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,interrupt)
 attempts=D/'attempts'
 if attempts.is_symlink():raise RuntimeError('attempt parent symlink')
 attempts.mkdir(exist_ok=True)
 out=attempts/('run-'+str(time.time_ns()));out.mkdir(exist_ok=False)
 (out/'tmp').mkdir();(out/'cache').mkdir()
 os.environ.update(KPF_OUTPUT_ROOT=str(out),TMPDIR=str(out/'tmp'),XDG_CACHE_HOME=str(out/'cache'),HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0')
 if mode!='official':
  publisher_smoke.context(D)
  os.environ['KPF_SMOKE']='1'
  if mode=='cutoff':os.environ['KPF_SMOKE_CUTOFF']='1'
 else:
  os.environ.pop('KPF_SMOKE',None);os.environ.pop('KPF_SMOKE_CUTOFF',None)
 p=None;pidfd=None;rc=75;reason='admission failed';completed=False;forced=False
 try:
  owner,identity=lock_witness.capture_gpu();lock_witness.verify_gpu(owner,identity)
  guard.boundary()
  if mode!='official':gpu_smoke_admission.check(admit_ram=True)
  else:ram_admission.check(guard.ID,int(os.environ['FILLER_END']))
  guard.boundary()
  cpus='184-191' if mode=='official' else os.environ['FILLER_CPUS']
  prefix=f'numactl --membind=3 -- taskset -c {cpus}'
  if mode!='official':prefix+=f' /usr/bin/python3 -B -I {D}/fence_exec.py'
  args=['/usr/bin/python3','-B','-I',str(D/'driver.py'),'item3','--fork-bin',str(guard.BIN),'--argv-file','/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt','--prompt-set','/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl','--out',str(out/'raw-gate'),'--fork-min','1024','--port','18486','--n-predict','256','--n-probs','20','--item3-groups','3','--item3-suffix','2','--launch-prefix',prefix,'--budget-min','145','--vram-ceiling-gib','60','--gpu-window-id',os.environ['FILLER_ID'],'--window-id',os.environ['FILLER_ID'],'--no-device-claim','exclusive GPU-quiet lock held by ancestor']
  with (out/'driver.log').open('xb') as log:
   p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
   pidfd=os.pidfd_open(p.pid)  # Acquire while direct child remains unreaped.
   while p.poll() is None:
    if interrupted[0]:reason='signal';break
    try:
     lock_witness.verify_gpu(owner,identity);guard.boundary()
     if int(Path('/sys/class/drm/card2/device/mem_info_vram_used').read_text())>60*1024**3:raise RuntimeError('VRAM ceiling')
    except (RuntimeError,OSError,ValueError,KeyError) as e:reason=str(e);break
    if mode=='cutoff' and (out/'SMOKE-REQUEST.json').is_file():forced=True;reason='forced cutoff after native request and residency';break
    time.sleep(.25)
   else:
    completed=True;rc=p.wait();reason='native driver exited'
    lock_witness.verify_gpu(owner,identity);guard.boundary()
    expected=[out/'conformance/VERDICT.json',out/'conformance/SHARED-PROJECTION.json'] if mode=='official' else [out/'SMOKE-REQUEST.json']
    if rc==0 and any(not x.is_file() or x.stat().st_size==0 for x in expected):rc=70;reason='native result missing'
    if mode=='cutoff':rc=70;reason='cutoff request was not observed while child was live'
 except (RuntimeError,OSError,ValueError,KeyError) as e:rc=75;reason=str(e)
 finally:
  try:stop_process(p,pidfd)
  finally:
   if pidfd is not None:os.close(pidfd)
   owned_drain.drain()
 if not completed or forced:rc=75
 result={'mode':mode,'rc':rc,'partial':rc==75,'reason':reason,'children_drained':True,'attempt':str(out),'sampled_output_cap_gib':64,'sampling_overshoot':'unknown'}
 with (out/('PARTIAL.json' if rc==75 else 'RESULT.json')).open('x') as f:json.dump(result,f);f.write('\n')
 return rc
if __name__=='__main__':raise SystemExit(main())
