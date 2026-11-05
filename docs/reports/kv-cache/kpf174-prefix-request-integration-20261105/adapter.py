#!/usr/bin/env python3
"""Execute AST-retained request boundary with synthetic transport; no server imports."""
import ast,hashlib,importlib.util,json,math,os,sys,time
from pathlib import Path
from types import SimpleNamespace
BASE=Path(__file__).resolve().parent

def custody():
 for line in (BASE/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1);p=BASE/name
  if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('source seal')

def main():
 out=Path(sys.argv[1]);mode=sys.argv[2]
 if mode not in ('smoke','full') or out.name!='worker' or out.parent.parent!=BASE/'out':raise RuntimeError('output boundary')
 out.mkdir(exist_ok=False);custody()
 spec=importlib.util.spec_from_file_location('sealed_witness',BASE/'layout_witness.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
 tree=ast.parse((BASE/'retained_control.py').read_text())
 funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
 runner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Runner')
 req=next(n for n in runner.body if isinstance(n,ast.FunctionDef) and n.name=='request')
 # Only actual pure boundary functions and actual request method execute. Imports,
 # class bases, main, server startup and trials are absent from executable AST.
 nodes=[funcs['selected_slice'],funcs['cell_verdict'],funcs['validated_top2'],req]
 entries=[]
 def judge(*a,**k):entries.append('judge');raise RuntimeError('native judge forbidden')
 def compare(*a,**k):entries.append('compare');return w.compare(*a,**k)
 ns={'os':os,'math':math,'parse':w.parse,'witness':w.witness,'Invalid':w.Invalid,'hashlib':hashlib,'json':json,'time':time,'OUT':out,'LIMIT':2**20,'k':SimpleNamespace(Abort=RuntimeError,body_for=lambda *a,**k:{}),'validated_top2':None,'compare':compare,'judge':judge}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'sealed-retained-control-boundary','exec'),ns)
 def trace(case):
  rows=[(1,10,2)]
  if case=='foreign_task':rows.append((1,11,2))
  if case=='foreign_slot':rows.append((0,10,2))
  def batch(bid,lid,pos,layouts=1):
   rr=rows if bid==1 else [(1,10,pos)]
   a=[f'KPF_ITEM4_BEGIN id={bid} off=0 rows={len(rr)} decode_prefix=0']
   a += [f'KPF_ITEM4_ROW id={bid} row={i} owner={s} task={t} nseq=1 pos={p} output=0 phase=prefill' for i,(s,t,p) in enumerate(rr)]
   for z in range(layouts):
    j=lid+z;a += [f'KPF_LAYOUT_BEGIN id={j} streams=1 swa=0 nseq=1 tokens=1',f'KPF_LAYOUT_STREAM id={j} stream=0 size=8 used=2 head=2',f'KPF_LAYOUT_CELL id={j} stream=0 cell=0 pos=0 mask=2 owners=1',f'KPF_LAYOUT_CELL id={j} stream=0 cell=1 pos=1 mask=2 owners=1',f'KPF_LAYOUT_END id={j}']
   return '\n'.join(a+[f'KPF_ITEM4_END id={bid} ret=0'])+'\n'
  raw=batch(1,10,2,2 if case=='multi_layout' else 1)
  if case in ('positive','duplicate'):raw+=batch(2,20,3 if case=='positive' else 2)
  if case=='truncated':raw=raw.rsplit('KPF_ITEM4_END',1)[0]
  return raw.encode()
 cases=[]
 for case in (['positive','multi_layout'] if mode=='smoke' else ['positive','duplicate','multi_layout','foreign_task','foreign_slot','truncated']):
  custody();entries.clear()
  if (BASE/'STOP').exists():raise RuntimeError('STOP')
  raw=trace(case);log=out/(case+'.log');log.write_bytes(b'')
  vram=out/(case+'.vram');vram.write_text('')
  class Client:
   def complete(self,body,timeout):
    start=time.time();log.write_bytes(raw);vram.write_text(f'{start} 1\n{time.time()} 1\n')
    return {'http':200,'tokens':[1]*64,'probs':[{'top_logprobs':[{'id':1,'logprob':-.1},{'id':2,'logprob':-1.}]} for _ in range(64)]}
  obj=SimpleNamespace(ctx=SimpleNamespace(check_boundary=lambda:None,client=Client(),deadline=SimpleNamespace(remaining=lambda:30)),srv=SimpleNamespace(log=log),vram_file=vram)
  # Retained request's only hardcoded prefix is 1984/2048. Bind witness via
  # explicit synthetic-prefix translation, retain task/slot and record it.
  def miniature(raw,task,slot,prefix):
   if prefix!=1984:raise RuntimeError('unexpected retained geometry')
   return w.witness(raw,task,slot,2)
  ns['witness']=miniature
  try:r=ns['request'](obj,'fork1',[1,2,3],1,True,64,'synthetic-B')
  except (w.Invalid,RuntimeError) as exc:
   if case=='positive' or entries:raise RuntimeError('unexpected refusal/order') from exc
   cases.append({'case':case,'refused':True,'judge_entries':list(entries),'reason':str(exc)})
  else:
   if case!='positive':raise RuntimeError('unsafe admission '+case)
   if (r['witness']['batch'],r['witness']['layout'])!=(1,10):raise RuntimeError('wrong boundary')
   control={**r,'role':'control1'}
   verdict=ns['cell_verdict']([r,control],True)
   if verdict['verdict']!='SMOKE_ONLY' or entries!=['compare']:raise RuntimeError('positive boundary order')
   cases.append({'case':case,'refused':False,'entries':list(entries),'boundary':[1,10]})
 custody()
 (out/'QUALIFICATION.json').write_text(json.dumps({'classification':'SMOKE_ONLY' if mode=='smoke' else 'MODEL_FREE_QUALIFICATION','native_equality':False,'launch_verdicts':{},'cases':cases,'progress':len(cases),'inference':False,'synthetic_prefix':2,'executable_ast':['selected_slice','cell_verdict','validated_top2','Runner.request']},indent=2)+'\n')
if __name__=='__main__':main()
