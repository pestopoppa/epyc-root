#!/usr/bin/env python3
import errno,fcntl,hashlib,json,mmap,os,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
stop=False
def sig(*_):
 global stop
 stop=True
signal.signal(signal.SIGINT,sig);signal.signal(signal.SIGTERM,sig)
def boundary():
 if stop or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))):raise RuntimeError('deadline')
def denied(fn):
 try:fn()
 except OSError as e:
  if e.errno==errno.EPERM:return True
  raise
 return False
def run(smoke):
 base=b'private-fixture!';changed=b'changed-fixture!';assert len(base)==len(changed)
 cases=[]
 fd=os.memfd_create('private-control',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
 try:
  os.write(fd,base)
  with mmap.mmap(fd,len(base),access=mmap.ACCESS_READ) as m:
   assert os.pwrite(fd,changed,0)==len(changed);cases.append({'case':'unsealed_write_visible','matched':m[:]==changed})
 finally:os.close(fd)
 boundary();fd=os.memfd_create('private-sealed',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
 try:
  os.write(fd,base);seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL;fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
  assert fcntl.fcntl(fd,fcntl.F_GET_SEALS)&seals==seals
  with mmap.mmap(fd,len(base),access=mmap.ACCESS_READ) as m:
   alias=os.open(f'/proc/self/fd/{fd}',os.O_RDWR|os.O_CLOEXEC)
   try:
    rejected=denied(lambda:os.pwrite(alias,changed,0));cases.append({'case':'sealed_alias_overwrite_refused','matched':rejected and m[:]==base})
    if not smoke:
     boundary();cases.append({'case':'sealed_truncate_refused','matched':denied(lambda:os.ftruncate(alias,1)) and m[:]==base})
     boundary();cases.append({'case':'seal_change_refused','matched':denied(lambda:fcntl.fcntl(alias,fcntl.F_ADD_SEALS,fcntl.F_SEAL_WRITE)) and m[:]==base})
   finally:os.close(alias)
 finally:os.close(fd)
 if not all(c['matched'] for c in cases):raise RuntimeError('control mismatch')
 return {'schema':'kpf17.memfd-seal-control.v1','status':'PASS','smoke':smoke,'case_count':len(cases),'cases':cases,'fixture_sha256':hashlib.sha256(base).hexdigest(),'scope':'private non-ELF memfd and same-process descriptor; no native loader, build identity or whole custody-chain claim'}
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if sys.argv[1:]==['--complete']:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text());assert r['status']=='PASS' and r['smoke'] is smoke and r['case_count']==(2 if smoke else 4) and all(x['matched'] is True for x in r['cases']);boundary();return
 boundary()
 if smoke:assert len(os.sched_getaffinity(0))==4
 r=run(smoke);p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output exists')
 q=p.with_suffix('.tmp')
 with q.open('x') as f:json.dump(r,f,sort_keys=True);f.write('\n')
 boundary();os.replace(q,p)
if __name__=='__main__':main()
