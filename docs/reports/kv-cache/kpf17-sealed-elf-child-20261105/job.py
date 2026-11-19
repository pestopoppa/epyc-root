#!/usr/bin/env python3
"""Owned same-UID child write controls against private memfds."""
import ctypes,fcntl,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
stopped=False
def stop(*_):
 global stopped;stopped=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def guard():
 if stopped or (D/'STOP').exists() or (os.getenv('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.getenv('FILLER_DEADLINE',os.getenv('FILLER_END','9999999999'))):raise RuntimeError('deadline')
def child(fd,action):
 guard()
 p=subprocess.run([sys.executable,'-B',str(D/'child.py'),str(fd),action,str(os.getpid())],pass_fds=(fd,),capture_output=True,text=True,timeout=30,check=True)
 guard(); x=json.loads(p.stdout)
 if x['pid']==os.getpid() or x['ppid']!=os.getpid() or x['uid']!=os.geteuid() or x['inode']!=os.fstat(fd).st_ino or x['action']!=action:raise RuntimeError('child identity')
 return x

def main():
 smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
 out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if sys.argv[1:]==['--complete']:
  x=json.loads(out.read_text());guard()
  if x['smoke']!=smoke or x['status']!='PASS' or x['case_count']!=5 or not all(c['ok'] for c in x['cases']):raise RuntimeError('incomplete')
  return
 guard()
 if smoke and len(os.sched_getaffinity(0))!=4:raise RuntimeError('affinity')
 obj=D/('fixture-%d.so'%os.getpid())
 try:
  subprocess.run(['/usr/bin/cc','-shared','-fPIC','-o',str(obj),str(D/'fixture.c')],check=True,timeout=60)
  guard();blob=obj.read_bytes()
 finally:obj.unlink(missing_ok=True)
 mutable=os.memfd_create('kpf17-child-mutable',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
 fd=os.memfd_create('kpf17-child-sealed-elf',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
 try:
  os.write(mutable,b'control');m=child(mutable,'write')
  cases=[{'case':'child_mutable_write_visible','ok':m['result']=='success' and os.pread(mutable,7,0)==b'Xontrol'}]
  pos=0
  while pos<len(blob):pos+=os.write(fd,blob[pos:])
  seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
  fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
  lib=ctypes.CDLL('/proc/self/fd/%d'%fd);fn=lib.sealed_fixture_value;fn.restype=ctypes.c_int
  st=os.fstat(fd)
  maps=[l for l in Path('/proc/self/maps').read_text().splitlines() if len(l.split())>=6 and tuple(int(i,16) for i in l.split()[3].split(':'))==(os.major(st.st_dev),os.minor(st.st_dev)) and l.split()[4]==str(st.st_ino) and 'memfd:kpf17-child-sealed-elf' in l]
  cases.append({'case':'sealed_elf_loaded_and_mapped','ok':bool(maps) and fn()==1729 and fcntl.fcntl(fd,fcntl.F_GET_SEALS)&seals==seals})
  w=child(fd,'write');cases.append({'case':'child_sealed_write_eperm','ok':w['result']=='EPERM'})
  t=child(fd,'shrink');cases.append({'case':'child_sealed_shrink_eperm','ok':t['result']=='EPERM'})
  cases.append({'case':'elf_bytes_and_call_unchanged','ok':os.pread(fd,len(blob),0)==blob and fn()==1729})
  if not all(c['ok'] for c in cases):raise RuntimeError('control failed')
  result={'schema':'kpf17.sealed-elf-child.v1','status':'PASS','smoke':smoke,'case_count':len(cases),'cases':cases,'child_controls':[m,w,t],'elf_sha256':hashlib.sha256(blob).hexdigest(),'device':st.st_dev,'inode':st.st_ino,'maps':maps,'scope':'private ELF and owned same-UID children with inherited descriptors only; no ggml, unrelated process, privileged adversary, build identity or complete custody'}
 finally:os.close(mutable);os.close(fd)
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise RuntimeError('output exists')
 tmp=out.with_name(out.name+'.tmp')
 with tmp.open('x') as f:json.dump(result,f,sort_keys=True);f.write('\n')
 guard();os.replace(tmp,out)
if __name__=='__main__':main()
