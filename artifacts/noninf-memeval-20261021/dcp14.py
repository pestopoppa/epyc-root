"""DCP-14 delegation propagation audit. Detector FIXED before the run (this file's sha256 is recorded in the result).
Pairing: group 'start' events by parent_request_id (non-null). Delegate roles = {worker_general, worker, worker_vision}.
Parent-role = any other role. Pair = (delegate call, latest parent-role call in the group with ts_epoch <= delegate ts;
if none earlier, the earliest parent-role call after it, tagged parent_after). Groups with no parent-role call: 'no_parent_prompt'.
Items extracted from PARENT prompt (regexes below); item propagated iff normalized (lowercase, collapsed whitespace) item text is a
substring of normalized CHILD prompt.  Categories: format, options, ids, schema.
Truncated stratum: either prompt_truncated true -> separate denominator, not in main rates.
Unparsable: missing/non-str prompt on either side.
"""
import json,re,sys,hashlib,collections as C
F='/mnt/raid0/llm/tmp/inference_tap_events.jsonl'
DEL={'worker_general','worker','worker_vision'}
norm=lambda s:re.sub(r'\s+',' ',s).strip().lower()
FMT=re.compile(r'[^.\n]*\b(?:answer\s*:|in the form|final answer|format|respond with|reply with|output only|return only|return a|respond only|exactly|on its own|one word|only the)\b[^.\n]*',re.I)
OPT=re.compile(r'^\s*\(?([A-Ja-j])[\)\.:]\s+(\S.*)$',re.M)
ID=re.compile(r'\b[0-9a-f]{8,}\b|\b[A-Z]{2,}-\d+\b|(?<![\w/])/(?:[\w.\-]+/)+[\w.\-]+|`[^`\n]{2,60}`')
SCH=re.compile(r'\b(?:schema|json|fields?|keys?)\b',re.I)
KEY=re.compile(r'"([A-Za-z_][\w\-]{1,40})"\s*:')
def items(p):
    o={}
    o['format']=[norm(m.group(0)) for m in FMT.finditer(p) if len(m.group(0))>=8]
    o['options']=[norm(m.group(0)) for m in OPT.finditer(p)] if len(OPT.findall(p))>=2 else []
    o['ids']=sorted(set(norm(m.group(0)) for m in ID.finditer(p)))
    o['schema']=sorted(set('"%s":'%k.lower() for k in KEY.findall(p))) if SCH.search(p) and len(set(KEY.findall(p)))>=2 else []
    return o
g=C.defaultdict(list); bad=0
for l in open(F):
    e=json.loads(l)
    if e['event']=='start' and e.get('parent_request_id'): g[e['parent_request_id']].append(e)
res=C.defaultdict(lambda:C.defaultdict(lambda:C.Counter()))
npar=C.defaultdict(set); unp=C.Counter(); nopar=C.Counter(); npairs=C.Counter(); exact=C.Counter(); trunc=C.Counter()
ts_min=1e18;ts_max=0
for pid,v in g.items():
    v.sort(key=lambda x:x['ts_epoch'])
    for d in v:
        if d['role'] not in DEL: continue
        ts_min=min(ts_min,d['ts_epoch']);ts_max=max(ts_max,d['ts_epoch'])
        par=[x for x in v if x['role'] not in DEL]
        if not par: nopar[d['role']]+=1; continue
        before=[x for x in par if x['ts_epoch']<=d['ts_epoch']]
        p=before[-1] if before else par[0]; tag='after' if not before else 'before'
        key=(p['role'],d['role'])
        npar[key].add(pid)
        if not isinstance(p.get('prompt'),str) or not isinstance(d.get('prompt'),str): unp[key]+=1; continue
        if p.get('prompt_truncated') or d.get('prompt_truncated'): trunc[key]+=1; continue
        npairs[key]+=1
        pn,dn=norm(p['prompt']),norm(d['prompt'])
        if pn==dn: exact[key]+=1; ident=1
        else: ident=0
        it=items(p['prompt'])
        for c,L in it.items():
            if not L: continue
            hit=sum(1 for x in L if x in dn)
            r=res[key][c]; r['pairs']+=1; r['items']+=len(L); r['hit']+=hit; r['allhit']+=(hit==len(L))
            if not ident:
                r['pairs_nonident']+=1; r['items_ni']+=len(L); r['hit_ni']+=hit; r['allhit_ni']+=(hit==len(L))
out={'detector_sha256':hashlib.sha256(open(__file__,'rb').read()).hexdigest(),'window':[ts_min,ts_max],'rows':{}}
keys=sorted(npar)
for key in keys:
    row={'parents_N':len(npar[key]),'pairs_analysed':npairs[key],'identical_prompt_pairs':exact[key],'truncated_pairs_separate':trunc[key],'unparsable_pairs':unp[key],'cats':{}}
    for c,r in res[key].items(): row['cats'][c]=dict(r)
    out['rows']['%s->%s'%key]=row
out['no_parent_prompt_delegate_calls']=dict(nopar)
json.dump(out,open('dcp14_result.json','w'),indent=1)
print(out['detector_sha256'],ts_min,ts_max)
for k,r in out['rows'].items():
    print(k,{a:r[a] for a in r if a!='cats'})
    for c,x in r['cats'].items():
        print('   ',c,'pairs',x['pairs'],'item_rate %.3f'%(x['hit']/x['items']),'allhit_pair %.3f'%(x['allhit']/x['pairs']),'| non-identical pairs',x.get('pairs_nonident',0),'item_rate_ni',('%.3f'%(x['hit_ni']/x['items_ni'])) if x.get('items_ni') else 'n/a')
print('no parent prompt',dict(nopar))
