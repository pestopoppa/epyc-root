#!/usr/bin/env python3
"""Conservative native trace witness: refuses multi-ubatch association ambiguity."""
import argparse, hashlib, json, re
from pathlib import Path

B=re.compile(r'KPF_LAYOUT_BEGIN id=(\d+) streams=(\d+) swa=(\d+) nseq=(\d+) tokens=(\d+)$')
S=re.compile(r'KPF_LAYOUT_STREAM id=(\d+) stream=(\d+) size=(\d+) used=(\d+) head=(\d+)$')
C=re.compile(r'KPF_LAYOUT_CELL id=(\d+) stream=(\d+) cell=(\d+) pos=(-?\d+) mask=(\d+) owners=(\d+)$')
E=re.compile(r'KPF_LAYOUT_END id=(\d+)$')
RB=re.compile(r'KPF_ITEM4_BEGIN id=(\d+) off=(\d+) rows=(\d+) decode_prefix=(\d+)$')
RR=re.compile(r'KPF_ITEM4_ROW id=(\d+) row=(\d+) owner=(-?\d+) task=(-?\d+) nseq=(\d+) pos=(-?\d+) output=(\d+) phase=(\w+)$')
RE=re.compile(r'KPF_ITEM4_END id=(\d+) ret=(-?\d+)$')
class Invalid(ValueError): pass

def parse(raw):
    try: lines=raw.decode('utf-8',errors='strict').splitlines()
    except UnicodeDecodeError as e: raise Invalid('non-UTF8') from e
    batches=[]; batch=None; layout=None; seen=set()
    for line in lines:
        if 'KPF_ITEM4_' not in line and 'KPF_LAYOUT_' not in line: continue
        line=line[min(x for x in (line.find('KPF_ITEM4_'),line.find('KPF_LAYOUT_')) if x>=0):]
        m=RB.fullmatch(line)
        if m:
            if batch is not None: raise Invalid('nested batch')
            a=list(map(int,m.groups())); batch={'id':a[0],'off':a[1],'n':a[2],'decode_prefix':a[3],'rows':[],'layouts':[]};continue
        m=RR.fullmatch(line)
        if m:
            if batch is None or layout is not None:raise Invalid('row outside batch')
            vals=list(map(int,m.groups()[:-1]));i,row,owner,task,nseq,pos,output=vals;phase=m.group(8)
            if i!=batch['id'] or row!=len(batch['rows']) or nseq!=1 or owner not in range(4) or task<0 or phase not in ('decode','prefill'):raise Invalid('invalid batch row')
            batch['rows'].append([owner,task,pos,output,phase]);continue
        m=B.fullmatch(line)
        if m:
            if batch is None or layout is not None or len(batch['rows'])!=batch['n']:raise Invalid('unbound layout')
            i,streams,swa,nseq,tokens=map(int,m.groups())
            if i in seen or streams!=1 or swa!=0 or nseq<1 or tokens<1:raise Invalid('non-target or duplicate layout')
            seen.add(i); layout={'id':i,'stream':None,'cells':[],'nseq':nseq,'tokens':tokens};continue
        m=S.fullmatch(line)
        if m:
            if layout is None or layout['stream'] is not None:raise Invalid('invalid stream')
            i,stream,size,used,head=map(int,m.groups())
            if i!=layout['id'] or stream!=0 or not 0<=used<=size or not 0<=head<=size:raise Invalid('invalid stream counters')
            layout['stream']={'size':size,'used':used,'head':head};continue
        m=C.fullmatch(line)
        if m:
            if layout is None or layout['stream'] is None:raise Invalid('unbound cell')
            i,stream,idx,pos,mask,owners=map(int,m.groups())
            if i!=layout['id'] or stream!=0 or idx>=layout['stream']['size'] or pos<0 or mask<=0 or mask>=16 or mask.bit_count()!=owners or (layout['cells'] and idx<=layout['cells'][-1][0]):raise Invalid('invalid cell')
            layout['cells'].append([idx,pos,mask]);continue
        m=E.fullmatch(line)
        if m:
            if layout is None or int(m.group(1))!=layout['id'] or layout['stream'] is None or len(layout['cells'])!=layout['stream']['used']:raise Invalid('incomplete layout')
            batch['layouts'].append(layout);layout=None;continue
        m=RE.fullmatch(line)
        if m:
            if batch is None or layout is not None or int(m.group(1))!=batch['id'] or int(m.group(2))!=0 or len(batch['rows'])!=batch['n'] or not batch['layouts']:raise Invalid('incomplete batch')
            batches.append(batch);batch=None;continue
        raise Invalid('malformed trace line')
    if batch is not None or layout is not None:raise Invalid('truncated trace')
    return batches

def witness(raw,task,slot,prefix):
    if type(task)!=int or task<0 or slot not in range(4) or type(prefix)!=int or prefix<=0:raise Invalid('bad binding')
    batches=parse(raw); hits=[]
    for b in batches:
        target_rows=[r for r in b['rows'] if r[0]==slot and r[1]==task and r[4]=='prefill']
        if not target_rows:continue
        # find_slot() is called once per llama_decode ubatch; item4 logs the
        # entire server batch but does not bind layout IDs to row subranges.
        if len(b['layouts'])>1:raise Invalid('ambiguous multi-layout target batch')
        if min(r[2] for r in target_rows)!=prefix:continue
        for layout in b['layouts']:
            pairs=sorted((pos,idx) for idx,pos,mask in layout['cells'] if mask & (1<<slot) and pos<prefix)
            if [x[0] for x in pairs]==list(range(prefix)):
                hits.append({'batch':b['id'],'layout':layout['id'],'mapping':pairs,'head':layout['stream']['head'],'capacity':layout['stream']['size'],'used':layout['stream']['used'],'nseq':layout['nseq'],'tokens':layout['tokens'],'cells':layout['cells'],'rows':b['rows']})
    if len(hits)!=1:raise Invalid('expected exactly one bound prefix snapshot')
    return {'raw_sha256':hashlib.sha256(raw).hexdigest(),'task':task,'slot':slot,'prefix':prefix,**hits[0]}

def compare(x,y):
    if x['prefix']!=y['prefix']:raise Invalid('prefix mismatch')
    def occupied(w):return [(i,p,bool(m&(1<<w['slot']))) for i,p,m in w['cells']]
    def rows(w):return [('target' if o==w['slot'] else 'other',p,z,phase) for o,t,p,z,phase in w['rows']]
    geometry=all(k in x and k in y and x[k]==y[k] for k in ('capacity','used','nseq','tokens'))
    return {'same_capacity_geometry':geometry,'same_physical_prefix':x['mapping']==y['mapping'],'same_occupied_shape':occupied(x)==occupied(y),'same_head':x['head']==y['head'],'same_batch_rows':rows(x)==rows(y),'verdict':'MATCHED' if geometry and x['mapping']==y['mapping'] and occupied(x)==occupied(y) and x['head']==y['head'] and rows(x)==rows(y) else 'INVALID'}

def main():
    p=argparse.ArgumentParser();p.add_argument('trace',type=Path);p.add_argument('--task',type=int,required=True);p.add_argument('--slot',type=int,required=True);p.add_argument('--prefix',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:r=witness(a.trace.read_bytes(),a.task,a.slot,a.prefix)
    except (Invalid,OSError) as e:raise SystemExit('INVALID: '+str(e))
    a.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
