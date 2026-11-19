#!/usr/bin/env python3
import hashlib,json,os,re,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
STOP=False
def stop(*_):
 global STOP
 STOP=True
signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
def boundary():
 if STOP or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',os.environ.get('FILLER_END','9999999999'))):raise RuntimeError('deadline')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def census(body,symbol):
 if f'<{symbol}>:' not in body:raise RuntimeError('missing exact body header')
 section=body.split(f'<{symbol}>:',1)[1];lines=section.splitlines();counts={};insns=0
 for line in lines:
  boundary()
  if re.match(r'^\s*[0-9a-f]+ <[^>]+>:',line):break
  m=re.match(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+\s*(.+)$',line)
  if not m:continue
  insns+=1
  for disp,reg in re.findall(r'(?<![\w$])(-?0x[0-9a-f]+)\(%(r(?:ax|bx|cx|dx|si|di|bp|sp|8|9|1[0-5]))(?:[,)]|$)',m.group(2)):
   key=reg+':'+str(int(disp,16));counts[key]=counts.get(key,0)+1
 if not insns:raise RuntimeError('empty instruction body')
 return {'instruction_lines':insns,'displacement_counts':counts}
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 if sys.argv[1:]==['--complete']:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';r=json.loads(p.read_text());assert r['status']==('SMOKE_PASS' if smoke else 'CENSUS_COMPLETE') and r['scope']=='syntactic displacement counts only; no ABI or historical binding';assert len(r['bodies'])==(1 if smoke else 3);boundary();return
 boundary(); pins=json.loads((D/'inputs.json').read_text());bodies={}
 if smoke:
  assert len(os.sched_getaffinity(0))==4
  b=census('0000 <fixture>:\n  00: 48 8b 46 70 mov 0x70(%rsi),%rax\n','fixture');assert b['displacement_counts']=={'rsi:112':1};bodies={'fixture':b}
 else:
  for n,x in pins.items():
   p=D/'inputs'/n
   if p.is_symlink() or p.stat().st_size>8*1024*1024 or digest(p)!=x['sha256']:raise RuntimeError('input drift')
   bodies[x['symbol']]=census(p.read_text(),x['symbol'])
   if digest(p)!=x['sha256']:raise RuntimeError('input drift after')
 r={'status':'SMOKE_PASS' if smoke else 'CENSUS_COMPLETE','body_count':len(bodies),'bodies':bodies,'input_pins':pins,'scope':'syntactic displacement counts only; no ABI or historical binding'}
 p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json';p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('output exists')
 q=p.with_suffix('.tmp')
 with q.open('x') as f:json.dump(r,f,sort_keys=True);f.write('\n')
 boundary();os.replace(q,p)
if __name__=='__main__':main()
