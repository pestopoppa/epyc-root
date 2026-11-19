#!/usr/bin/env python3
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;TREE=D/'source';HEAD='326f502759986c9846027f8187972969139c0089';STOP=False
JSWS='\u0009\u000b\u000c\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000\ufeff\n\r\u2028\u2029'
def stop(*_):
 global STOP
 STOP=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def boundary():
 if STOP or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))):raise RuntimeError('deadline')
def git(*args):
 boundary();return subprocess.run(['git','-C',str(TREE),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=15).stdout
def check():
 if git('rev-parse','HEAD').decode().strip()!=HEAD:raise RuntimeError('head drift')
 if git('status','--porcelain','--untracked-files=all'):raise RuntimeError('source dirty')
def empty(s):return not s.strip(JSWS)
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if sys.argv[1:]==['--check']:check();return
 if sys.argv[1:]==['--complete']:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text());assert r['status']==('SMOKE_PASS' if smoke else 'SOURCE_CENSUS_COMPLETE') and r['source_count']>0;boundary();return
 boundary()
 if smoke:
  assert len(os.sched_getaffinity(0))==4 and empty(' \n\ufeff') and not empty('x')
  r={'status':'SMOKE_PASS','source_count':2,'fixture':True}
 else:
  check();files=git('ls-files','-z','--','*.py').split(b'\0');names=[];oversize=[];unknown=[];count=0
  for raw in files:
   if not raw:continue
   boundary();name=os.fsdecode(raw);p=TREE/name
   if p.is_symlink() or not p.is_file():unknown.append(name);continue
   with p.open('rb') as f:
    a=os.fstat(f.fileno())
    if a.st_size>512*1024:oversize.append(name);continue
    data=f.read(512*1024+1);b=os.fstat(f.fileno())
   if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns) or len(data)!=a.st_size:raise RuntimeError('source file changed')
   try:text=data.decode('utf-8')
   except UnicodeDecodeError:unknown.append(name);continue
   count+=1
   if empty(text):names.append(name)
  check();r={'status':'SOURCE_CENSUS_COMPLETE','source_count':count,'empty_candidates':names,'empty_count':len(names),'oversize_count':len(oversize),'unknown_count':len(unknown),'head':HEAD,'scope':'tracked Python source candidate census only; no actual index manifest binding and no inference that candidates equal the four skipped files','cli_scope':'copied current installed extractor code; historical tool identity not established'}
 p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output collision')
 q=p.with_suffix('.tmp')
 with q.open('x') as f:json.dump(r,f,sort_keys=True);f.write('\n')
 boundary();os.replace(q,p)
if __name__=='__main__':main()
