#!/usr/bin/env python3
import ast,hashlib,json,os,re,signal,sys,tempfile,time
from pathlib import Path
D=Path(__file__).resolve().parent
STOP=False
def sig(*_):
 global STOP
 STOP=True
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
def guard():
 if STOP or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))):raise RuntimeError('deadline')
def load(patch,root):
 src=(D/'original.py').read_text(); tree=ast.parse(src)
 fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='verified_coverage')
 text=ast.get_source_segment(src,fn)
 if patch:
  old="unknown=[line for i,line in enumerate(lines) if i not in covered and\n             re.search"
  new="unknown=[line for i,line in enumerate(lines) if i not in covered and not re.fullmatch(r'\\[gitnexus-heap\\] sr-extract-end used_mb=\\d+ rss_mb=\\d+ lang=[A-Za-z0-9_+]+ parsedFiles=\\d+ preExtractedHits=\\d+ skipped=0',line) and\n             re.search"
  if text.count(old)!=1:raise RuntimeError('source shape drift')
  text=text.replace(old,new)
 ns={'D':root,'TREE':root,'HEAD':'fixture','ENV':{'GITNEXUS_VERBOSE':'1'},'re':re,'hashlib':hashlib,'json':json}
 exec(compile(text,'retained-coverage-function','exec'),ns)
 return ns['verified_coverage']
def checks(smoke):
 cases=[('clean','',True,True),('zero','[gitnexus-heap] sr-extract-end used_mb=490 rss_mb=1166 lang=c parsedFiles=3 preExtractedHits=3 skipped=0',False,True),('nonzero','[gitnexus-heap] sr-extract-end used_mb=557 rss_mb=1005 lang=python parsedFiles=2554 preExtractedHits=2554 skipped=4',False,False),('unknown','unclassified files skipped by parser',False,False),('fake-zero','skipped=0 omitted code',False,False),('truncation','...and 5 more',False,False),('known-large','Skipped 1 large files (>512 KiB)\n  - large.fixture',True,True),('bad-large','Skipped 2 large files (>512 KiB)\n  - large.fixture',False,False)]
 if smoke:cases=cases[:2]
 out=[]
 with tempfile.TemporaryDirectory(dir=D,prefix='fixture-') as td:
  root=Path(td);(root/'out').mkdir();(root/'large.fixture').write_text('fixture');(root/'out/analyze.stdout').write_text('Repository indexed successfully (fixture)\n')
  for name,line,w1,w2 in cases:
   guard();(root/'out/analyze.stderr').write_text(line+'\n')
   for changed,want in ((False,w1),(True,w2)):
    fn=load(changed,root)
    try:fn('fixture status',[]);got=True
    except AssertionError:got=False
    out.append({'case':name,'variant':'corrected' if changed else 'original','expected_accept':want,'actual_accept':got,'matched':got==want})
    if got!=want:raise RuntimeError('control mismatch')
 return out
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if sys.argv[1:]==['--complete']:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text());assert r['status']=='PASS' and r['synthetic_only'] is True and len(r['controls'])==(4 if smoke else 16) and all(x['matched'] for x in r['controls']);guard();return
 guard()
 if smoke:assert len(os.sched_getaffinity(0))==4
 obs=checks(smoke);r={'status':'PASS','synthetic_only':True,'controls':obs,'native_impact':'UNKNOWN','nonzero_skips':'UNKNOWN','children_spawned':0}
 p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output collision')
 q=p.with_suffix('.tmp')
 with q.open('x') as f:json.dump(r,f,sort_keys=True);f.write('\n')
 guard();os.replace(q,p)
if __name__=='__main__':main()
