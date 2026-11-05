#!/usr/bin/env python3
import hashlib,json,os,signal,sys,tempfile,time
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
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run_case(case,root,source):
 boundary();sub=root/case;sub.mkdir();(sub/'check_models.py').write_bytes(source)
 files=[sub/'model-a',sub/'model-b']
 for p in files:p.write_bytes(b'synthetic-small-data')
 records=[]
 for p in files:
  s=p.stat();records.append(dict(path=str(p),device=s.st_dev,inode=s.st_ino,size=s.st_size,mtime_ns=s.st_mtime_ns))
 receipt={'schema':'kpf50.model-stat-admission.v1','models':records}
 if case=='bad-schema':receipt['schema']='wrong'
 (sub/'models.stat.json').write_text(json.dumps(receipt)+'\n')
 (sub/'seals.json').write_text(json.dumps({n:sha(sub/n) for n in ('check_models.py','models.stat.json')}))
 if case=='metadata-drift':os.truncate(files[0],1)
 if case=='receipt-drift':(sub/'models.stat.json').write_text('{}')
 if case=='symlink':
  backing=sub/'replacement';files[0].rename(backing);files[0].symlink_to(backing)
 if case=='content-restore-mtime':
  before=files[0].stat();files[0].write_bytes(b'changed-small-data!!');assert files[0].stat().st_size==before.st_size
  os.utime(files[0],ns=(before.st_atime_ns,before.st_mtime_ns));assert files[0].stat().st_mtime_ns==before.st_mtime_ns
 ns={'__name__':'fixture_module','__file__':str(sub/'check_models.py')};exec(compile(source,str(sub/'check_models.py'),'exec'),ns);ns['D']=sub;ns['EXPECTED_PATHS']=tuple(str(x) for x in files)
 try:ns['main']();got='ACCEPT'
 except (ValueError,FileNotFoundError):got='REFUSE'
 expected='ACCEPT' if case in ('positive','content-restore-mtime') else 'REFUSE'
 return {'case':case,'expected':expected,'actual':got,'matched':got==expected}
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if sys.argv[1:]==['--complete']:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text());assert r['status']=='PASS' and r['case_count']==(2 if smoke else 6) and all(x['matched'] for x in r['cases']);boundary();return
 if smoke:assert len(os.sched_getaffinity(0))==4
 source=(D/'original.py').read_bytes();old=hashlib.sha256(source).hexdigest();names=['positive','metadata-drift','bad-schema','receipt-drift','symlink','content-restore-mtime'];names=names[:2] if smoke else names
 with tempfile.TemporaryDirectory(dir=D,prefix='fixture-') as t:cases=[run_case(n,Path(t),source) for n in names]
 if sha(D/'original.py')!=old or not all(x['matched'] for x in cases):raise RuntimeError('seal or case mismatch')
 r={'status':'PASS','case_count':len(cases),'cases':cases,'source_sha256':old,'scope':'actual stat checker with synthetic path overrides; no model content, native profile or immutability claim'}
 p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output collision')
 q=p.with_suffix('.tmp')
 with q.open('x') as f:json.dump(r,f,sort_keys=True);f.write('\n')
 boundary();os.replace(q,p)
if __name__=='__main__':main()
