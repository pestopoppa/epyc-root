#!/usr/bin/env python3
import ctypes, errno, fcntl, hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path
D=Path(__file__).resolve().parent
LIB=Path('/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104/build/bin/libggml-base.so.0.16.0')
PIN='734fb17b9916947695ec0787f4c123f1f63b0cfa90831385a7685415040c900b'
stopped=False
def stop(*_):
 global stopped; stopped=True
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
def guard():
 if stopped or (D/'STOP').exists() or (os.getenv('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()): raise RuntimeError('STOP')
 if time.time() >= float(os.getenv('FILLER_DEADLINE',os.getenv('FILLER_END','9999999999'))): raise RuntimeError('deadline')
def child(fd,action):
 guard(); p=subprocess.run([sys.executable,'-B',__file__,'--child',str(fd),action,str(os.getpid())],pass_fds=(fd,),capture_output=True,text=True,timeout=15,check=True); guard()
 x=json.loads(p.stdout); st=os.fstat(fd)
 if x['ppid']!=os.getpid() or x['uid']!=os.geteuid() or x['inode']!=st.st_ino or x['device']!=st.st_dev or x['action']!=action: raise RuntimeError('child identity')
 return x
def main():
 if sys.argv[1:2]==['--child']:
  fd=int(sys.argv[2]); action=sys.argv[3]; parent=int(sys.argv[4]); st=os.fstat(fd)
  if os.getppid()!=parent or os.stat('/proc/%d'%parent).st_uid!=os.geteuid(): raise RuntimeError('parent identity')
  try:
   if action=='write': os.pwrite(fd,b'X',0)
   elif action=='shrink': os.ftruncate(fd,1)
   else: raise RuntimeError('action')
   result='success'
  except OSError as e:
   if e.errno!=errno.EPERM: raise
   result='EPERM'
  print(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'uid':os.geteuid(),'inode':st.st_ino,'device':st.st_dev,'action':action,'result':result})); return
 smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
 out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if sys.argv[1:]==['--complete']:
  guard(); x=json.loads(out.read_text()); assert x['status']=='PASS' and x['smoke']==smoke and x['case_count']==5 and all(c['ok'] for c in x['cases']); return
 guard()
 if smoke and len(os.sched_getaffinity(0))!=4: raise RuntimeError('affinity')
 result={'schema':'kpf17.ggml-memfd.v1','status':'UNKNOWN','smoke':smoke,'source':str(LIB),'expected_sha256':PIN,'scope':'one pinned ggml-base DSO and owned child only; no model, dependency custody, unrelated process or whole-chain custody'}
 mutable=fd=None
 try:
  blob=LIB.read_bytes(); digest=hashlib.sha256(blob).hexdigest()
  if digest!=PIN: raise RuntimeError('pinned library mismatch')
  mutable=os.memfd_create('kpf17-mutable',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING); os.write(mutable,b'control'); m=child(mutable,'write')
  cases=[{'case':'mutable_child_write_visible','ok':m['result']=='success' and os.pread(mutable,7,0)==b'Xontrol'}]
  fd=os.memfd_create('kpf17-ggml-base',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
  pos=0
  while pos<len(blob): pos+=os.write(fd,blob[pos:])
  seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL; fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
  lib=ctypes.CDLL('/proc/self/fd/%d'%fd,mode=os.RTLD_LOCAL|os.RTLD_NOW); fn=lib.ggml_version; fn.restype=ctypes.c_char_p; version=fn(); st=os.fstat(fd)
  maps=[l for l in Path('/proc/self/maps').read_text().splitlines() if len(l.split())>=6 and tuple(int(i,16) for i in l.split()[3].split(':'))==(os.major(st.st_dev),os.minor(st.st_dev)) and l.split()[4]==str(st.st_ino) and 'memfd:kpf17-ggml-base' in l]
  first=[l for l in maps if l.split()[2]=='00000000' and 'r' in l.split()[1]]
  if not first: raise RuntimeError('no readable offset-zero map')
  address=int(first[0].split('-')[0],16); mapped_before=ctypes.string_at(address,64)
  cases.append({'case':'pinned_ggml_loaded_mapped_sealed','ok':bool(maps) and mapped_before==blob[:64] and fcntl.fcntl(fd,fcntl.F_GET_SEALS)&seals==seals})
  w=child(fd,'write'); cases.append({'case':'sealed_child_write_refused','ok':w['result']=='EPERM'})
  t=child(fd,'shrink'); cases.append({'case':'sealed_child_shrink_refused','ok':t['result']=='EPERM'})
  cases.append({'case':'bytes_mapping_and_call_unchanged','ok':hashlib.sha256(os.pread(fd,len(blob),0)).hexdigest()==PIN and ctypes.string_at(address,64)==mapped_before and fn()==version})
  if not all(c['ok'] for c in cases): raise RuntimeError('control failure')
  result.update(status='PASS',case_count=len(cases),cases=cases,child_controls=[m,w,t],sha256=digest,device=st.st_dev,inode=st.st_ino,seals=fcntl.fcntl(fd,fcntl.F_GET_SEALS),maps=maps,ggml_version=version.decode('utf-8'))
 except Exception as e: result['reason']=type(e).__name__+': '+str(e)
 finally:
  if mutable is not None: os.close(mutable)
  if fd is not None: os.close(fd)
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists(): raise RuntimeError('output exists')
 tmp=out.with_name(out.name+'.tmp')
 with tmp.open('x') as f: json.dump(result,f,sort_keys=True); f.write('\n')
 os.replace(tmp,out)
 if result['status']!='PASS': raise RuntimeError(result['reason'])
 guard()
if __name__=='__main__': main()
