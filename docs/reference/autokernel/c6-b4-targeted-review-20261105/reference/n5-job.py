#!/usr/bin/env python3
"""Candidate-only n5; smoke and actual grant are separate."""
import collections,ctypes,hashlib,json,os,re,signal,subprocess,time
from pathlib import Path
from compare_capture import compare
from strict_capture import read_complete
D=Path(__file__).resolve().parent;ID='cross-keep-c6-mmq-n5-20261104';dry=os.environ.get('FILLER_DRYRUN')=='1';done=False
stop=False
def term(*_):
 global stop
 stop=True
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,term)
if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0):raise RuntimeError('subreaper unavailable')
def children():return {int(x) for t in Path('/proc/self/task').iterdir() for x in (t/'children').read_text().split()}
if children():raise RuntimeError('unexpected preexisting child')
def drain():
 end=time.monotonic()+5;forced=False
 while time.monotonic()<end:
  ids=children()
  if not ids:return not forced
  for pid in ids:
   try:
    fd=os.pidfd_open(pid)
    try:
     try:os.waitpid(pid,os.WNOHANG)
     except ChildProcessError:pass
     if pid in children():signal.pidfd_send_signal(fd,signal.SIGTERM if time.monotonic()<end-2 else signal.SIGKILL);forced=True
    finally:os.close(fd)
   except ProcessLookupError:pass
  time.sleep(.02)
 raise RuntimeError('child cleanup timed out')
def check():
 if stop or Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']):raise TimeoutError('own stop/deadline')
def custody():
 r=json.loads((D/'IMAGE-CUSTODY.json').read_text());base=D/'bin'
 for rel,x in r['files'].items():
  p=D/rel
  if p.is_symlink():raise ValueError('image regular file symlink')
  s=p.stat()
  if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(x['device'],x['inode'],x['size'],x['mtime_ns'],x['ctime_ns']):raise ValueError('image metadata changed '+rel)
 for rel,target in r['symlinks'].items():
  p=base/rel
  if not p.is_symlink() or os.readlink(p)!=target or not p.resolve().is_relative_to(base.resolve()):raise ValueError('image alias changed')
 return r

def write(path,body):
 data=json.dumps(body,sort_keys=True,allow_nan=False)+'\n';tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
 with tmp.open('x') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.link(tmp,path);tmp.unlink()
def append(path,body):
 with path.open('a') as f:f.write(json.dumps(body,sort_keys=True,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def gpu_node():
 nodes=Path('/sys/class/kfd/kfd/topology/nodes');found=[]
 for n in nodes.iterdir():
  props=dict(s.split(maxsplit=1) for s in (n/'properties').read_text().splitlines());gid=int((n/'gpu_id').read_text());
  if gid and (n/'name').read_text().strip()=='aldebaran' and props.get('drm_render_minor')=='128' and props.get('device_id')=='29711':found.append(gid)
 if len(found)!=1:raise RuntimeError('unique MI210 KFD mapping unavailable')
 return found[0]
def native(args,env,out,tag,gid):
 check();p=None;fd=None;maps=set();samples=[];forced=False;errors=[];stdout=out/('stdout.log' if tag=='native' else tag+'.log');stderr=out/('stderr.log' if tag=='native' else tag+'.stderr.log');expected=(D/'bin/libggml-hip.so').resolve();expected_st=expected.stat()
 try:
  with stdout.open('xb') as so,stderr.open('xb') as se:
   p=subprocess.Popen(args,env=env,stdout=so,stderr=se);fd=os.pidfd_open(p.pid);birth=int(Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
   while p.poll() is None:
    check()
    try:
     if int(Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split()[19])!=birth:raise RuntimeError('child PID reused')
     lines=Path(f'/proc/{p.pid}/maps').read_text().splitlines()
     for line in lines:
      fields=line.split()
      if len(fields)>=6 and fields[-1]==str(expected):
       device=fields[3].split(':');
       if (int(device[0],16),int(device[1],16),int(fields[4]))==(os.major(expected_st.st_dev),os.minor(expected_st.st_dev),expected_st.st_ino):maps.add(str(expected))
     v=Path(f'/sys/class/kfd/kfd/proc/{p.pid}/vram_{gid}');value=int(v.read_text());samples.append({'pid':p.pid,'birth':birth,'time':time.time(),'gpu_id':gid,'vram_bytes':value,'hip_mapped':bool(maps)})
    except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    time.sleep(.02)
   rc=p.wait()
 finally:
  try:
   if p is not None and p.poll() is None:
    forced=True
    if fd is None:errors.append('missing child pidfd')
    else:
     try:signal.pidfd_send_signal(fd,signal.SIGTERM)
     except ProcessLookupError:pass
     try:p.wait(timeout=2)
     except subprocess.TimeoutExpired:
      try:signal.pidfd_send_signal(fd,signal.SIGKILL)
      except ProcessLookupError:pass
      try:p.wait(timeout=3)
      except subprocess.TimeoutExpired:errors.append('child unreaped')
  except BaseException as e:errors.append(repr(e))
  finally:
   if fd is not None:
    try:os.close(fd)
    except OSError as e:errors.append(repr(e))
   try:
    if not drain():forced=True
   except BaseException as e:errors.append(repr(e))
  if forced or errors:raise RuntimeError('forced/incomplete cleanup '+str(errors))
 custody()
 if len(samples)<2 or not maps or max(s['vram_bytes'] for s in samples)<=0:raise RuntimeError('own MI210 HIP/KFD/VRAM proof missing')
 write(out/(tag+'.residency.json'),{'samples':samples,'mapped_path':str(expected),'gpu_id':gid})
 return rc,stdout,stderr,samples

def main():
 if os.environ.get('FILLER_ID')!=ID:raise RuntimeError('wrong ID')
 if not dry and ((D/'PROGRESS.jsonl').exists() or (D/'RESULT.json').exists()):raise RuntimeError('existing production output refuses rerun')
 if dry:os.sched_setaffinity(0,set(range(184,188)))
 expected=set(range(184,188 if dry else 192))
 if os.sched_getaffinity(0)!=expected:raise RuntimeError('wrong GPU host affinity')
 custody();prep=json.loads((D/'PREPARED.json').read_text());prior=json.loads((D/'PRIOR-RESULT.json').read_text());assert prep['case']==prior['case'] and prep['tolerance']==prior['records']['candidate']['tolerance']
 out=D/'runs'/('run-'+str(time.time_ns()));out.mkdir(parents=True,exist_ok=False);n5=out/'n5';n5.mkdir();gid=gpu_node();binary=D/'bin/test-backend-ops'
 env=dict(os.environ,LD_LIBRARY_PATH=str(D/'bin')+':/opt/rocm/lib',GGML_BACKEND_PATH=str(D/'bin'),C6_PROPERTY_CAPTURE_DIR=str(n5),GGML_FA_VKQ_F32='1',HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0',HIP_VISIBLE_DEVICES='0',ROCR_VISIBLE_DEVICES='0',CUDA_VISIBLE_DEVICES='0',GGML_CUDA_LOG_MMVQ_ROUTE='2');args=[str(binary),'test','-b','ROCm0','-o','MUL_MAT','-p',prep['case'],'-j','1','--suite-seed','71','--autokernel-properties'];rc,stdout,stderr,samples=native(args,env,n5,'native',gid)
 logs=stderr.read_text();o=stdout.read_text();routes=[v for v in logs.splitlines() if 'GGML_CUDA_MUL_MAT_ROUTE' in v];index=re.findall(r'^C6_SEED_INDEX (\d+)$',logs,re.M);props=re.findall(r'AK_PROP_V2 metric=fp64_error_ratio/host-double-gguf-wire/v1 residual=([^ ]+) tolerance=([^ ]+) passed=1 suite_seed=71 transform=identity',o);matched=compare(D/'prior-candidate',n5)
 if rc!=0 or index!=['7047'] or len(props)!=1 or props[0][1]!=prep['tolerance'] or float(props[0][0])>float(props[0][1]) or not matched['input_bytes_equal'] or not any('route=MMQ ' in v for v in routes):raise RuntimeError('original matched n5 did not pass')
 unit={'schema':'c6.q4k_mmq.n5.v2','id':ID,'dryrun':dry,'ordinal':7047,'residual':float(props[0][0]),'tolerance':float(props[0][1]),'input_bytes_equal':True,'native_rc':rc,'route':'MMQ','run':str(out),'scope':'single synthetic case; not a full gate'}
 unit.update(source_build_sha256=prep['build_receipt_sha256'],candidate_hip_sha256=prep['hip_sha256'],binary_sha256=prep['binary_sha256'],cleanup=True,full_gak_pass=None)
 if dry:write(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),unit)
 else:write(D/'RESULT.json',unit)
if __name__=='__main__':main()
