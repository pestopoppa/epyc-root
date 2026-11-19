#!/usr/bin/env python3
import ctypes,errno,hashlib,json,mmap,os,select,signal,subprocess,sys,tempfile,time
from pathlib import Path
D=Path(__file__).resolve().parent
STOP=False
def sig(*_):
 global STOP
 STOP=True
signal.signal(signal.SIGINT,sig);signal.signal(signal.SIGTERM,sig)
def boundary():
 if STOP or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))):raise RuntimeError('deadline')
def proc(pid):
 raw=Path(f'/proc/{pid}/stat').read_text(); fields=raw[raw.rfind(')')+2:].split();return int(fields[1]),int(fields[19])
def child(path,mutation):
 with open(path,'r+b') as f:
  m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_COPY)
  if mutation:m[0]=m[0]^1
  addr=ctypes.addressof(ctypes.c_char.from_buffer(m));pid=os.getpid();ppid,birth=proc(pid)
  print(json.dumps({'pid':pid,'parent':ppid,'birth':birth,'addr':addr,'size':len(m)}),flush=True)
  sys.stdin.buffer.read(1);m.close()
class IOV(ctypes.Structure):_fields_=[('base',ctypes.c_void_p),('length',ctypes.c_size_t)]
def readvm(pid,address,n):
 libc=ctypes.CDLL(None,use_errno=True);func=libc.process_vm_readv;func.argtypes=[ctypes.c_int,ctypes.POINTER(IOV),ctypes.c_ulong,ctypes.POINTER(IOV),ctypes.c_ulong,ctypes.c_ulong];func.restype=ctypes.c_ssize_t
 buf=ctypes.create_string_buffer(n);local=IOV(ctypes.addressof(buf),n);remote=IOV(address,n);ctypes.set_errno(0);count=func(pid,ctypes.byref(local),1,ctypes.byref(remote),1,0);err=ctypes.get_errno();return count,err,buf.raw
def one(case,root):
 boundary();data=b'kpf50-private-mapping-fixture-0123456789abcdef';p=root/(case+'.dat');p.write_bytes(data);original=hashlib.sha256(data).hexdigest();f=p.open('rb');st=os.fstat(f.fileno())
 childproc=None;pidfd=None;cleanup=False
 try:
  childproc=subprocess.Popen([sys.executable,str(D/'job.py'),'--child',str(p),'1' if case=='mutated' else '0'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
  pidfd=os.pidfd_open(childproc.pid);expiry=time.monotonic()+10
  while True:
   boundary()
   if time.monotonic()>=expiry:raise TimeoutError('child receipt timeout')
   ready,_,_=select.select([childproc.stdout],[],[],0.2)
   if ready:break
  rec=json.loads(childproc.stdout.readline());ppid,birth=proc(childproc.pid)
  if rec['pid']!=childproc.pid or rec['parent']!=os.getpid() or ppid!=os.getpid() or rec['birth']!=birth or rec['size']!=len(data):raise RuntimeError('child identity')
  found=False
  for line in Path(f'/proc/{childproc.pid}/maps').read_text().splitlines():
   fields=line.split(maxsplit=5)
   if len(fields)<6:continue
   start,end=(int(x,16) for x in fields[0].split('-'));major,minor=(int(x,16) for x in fields[3].split(':'))
   if start<=rec['addr'] and rec['addr']+len(data)<=end and int(fields[2],16)==0 and (major,minor,int(fields[4]))==(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino) and fields[5]==str(p):found=True
  if not found:raise RuntimeError('file-backed mapping missing')
  addr=0 if case=='bad-address' else rec['addr'];count,err,got=readvm(childproc.pid,addr,len(data))
  if proc(childproc.pid)!=(os.getpid(),birth):raise RuntimeError('identity changed')
  if hashlib.sha256(p.read_bytes()).hexdigest()!=original:raise RuntimeError('fixture drift')
  if case=='honest':matched=count==len(data) and got==data
  elif case=='mutated':matched=count==len(data) and got!=data
  else:matched=count==-1 and err==errno.EFAULT
  childproc.stdin.write(b'x');childproc.stdin.flush();rc=childproc.wait(timeout=3);cleanup=rc==0
  return {'case':case,'matched':matched and cleanup,'bytes_read':count,'errno':err,'child_exit':rc,'file_sha256':original,'mapping_confirmed':found,'identity_bracketed':True}
 finally:
  f.close()
  if childproc is not None:
   if childproc.poll() is None:
    if childproc.stdin:childproc.stdin.close()
    try:childproc.wait(timeout=1)
    except subprocess.TimeoutExpired:
     if pidfd is None:raise RuntimeError('cannot safely signal unbound child')
     signal.pidfd_send_signal(pidfd,signal.SIGTERM)
     try:childproc.wait(timeout=1)
     except subprocess.TimeoutExpired:signal.pidfd_send_signal(pidfd,signal.SIGKILL);childproc.wait(timeout=3)
   for stream in (childproc.stdin,childproc.stdout,childproc.stderr):
    if stream:stream.close()
  if pidfd is not None:os.close(pidfd)
def main():
 if sys.argv[1:2]==['--child']:child(sys.argv[2],sys.argv[3]=='1');return
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if sys.argv[1:]==['--complete']:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text());assert r['status']=='PASS' and r['case_count']==(1 if smoke else 3) and all(c['matched'] for c in r['cases']);boundary();return
 if smoke:assert len(os.sched_getaffinity(0))==4
 with tempfile.TemporaryDirectory(dir=D,prefix='own-child-') as tmp:
  cases=[one(c,Path(tmp)) for c in (['honest'] if smoke else ['honest','mutated','bad-address'])]
 if not all(c['matched'] for c in cases):raise RuntimeError('control mismatch')
 result={'status':'PASS','case_count':len(cases),'cases':cases,'smoke':smoke,'scope':'own-child CPU virtual memory; no physical, GPU, map_files, target or complete custody claim'}
 p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output collision')
 q=p.with_suffix('.tmp')
 with q.open('x') as f:json.dump(result,f,sort_keys=True);f.write('\n')
 boundary();os.replace(q,p)
if __name__=='__main__':main()
