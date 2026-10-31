#!/usr/bin/env python3
"""Predeclared GPU-ZOS-2.3 §9 core gate; no result is regraded on missing controls."""
import datetime,json,math,os,pathlib,statistics
G=pathlib.Path(os.environ.get('GPU_GATE_PACKET','/mnt/raid0/llm/tmp/codex-ni-gpu-zos-build-prep-20261031/successor/gpu'));OUT=G/'out'
def rows(arm):
 p=OUT/arm/'waves.jsonl'; x=[json.loads(s) for s in p.read_text().splitlines()]; x=[r for r in x if r['wave']>0];
 return [r for w in x for r in w['responses']]
def gm(x):return math.exp(statistics.mean(math.log(v) for v in x))
def same(a,b):
 if not all(isinstance(x.get('tokens'),list) and x['tokens'] and isinstance(x.get('content'),str) and x['content'] and all(k in x.get('timings',{}) for k in ('draft_n','draft_n_accepted')) for x in (a,b)):return False
 return a.get('tokens')==b.get('tokens') and a.get('content')==b.get('content') and a.get('timings',{}).get('draft_n')==b.get('timings',{}).get('draft_n') and a.get('timings',{}).get('draft_n_accepted')==b.get('timings',{}).get('draft_n_accepted')
def valid_response(r,n):
 t=r.get('tokens');u=r.get('usage',{});tim=r.get('timings',{})
 return isinstance(t,list) and len(t)==n and all(type(x) is int and x>=0 for x in t) and type(r.get('tokens_predicted')) is int and r['tokens_predicted']==n and type(u.get('completion_tokens')) is int and u['completion_tokens']==n and type(r.get('id_slot')) is int and 0<=r['id_slot']<4 and isinstance(r.get('content'),str) and bool(r['content']) and type(tim.get('draft_n')) is int and tim['draft_n']>0 and type(tim.get('draft_n_accepted')) is int and 0<=tim['draft_n_accepted']<=tim['draft_n']
def first_div(a,b):
 x=a.get('tokens') or [];y=b.get('tokens') or []
 for i,(u,v) in enumerate(zip(x,y)):
  if u!=v:return i
 return min(len(x),len(y)) if len(x)!=len(y) else None
A1,B1,A2,B2,O=(rows(x) for x in ('A1','B1','A2','B2','O'));F={k:rows(k) for k in ('F1','F2','F3')};assert all(len(x)==24 for x in (A1,B1,A2,B2,O)) and all(len(x)==8 for x in F.values())
import hashlib
intent_sha=hashlib.sha256((OUT/'RUN-INTENT-full.json').read_bytes()).hexdigest()
base={'run_intent_sha256':intent_sha,'schema':'ni.gpu_zos2_gate.v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unit':'percent paired geometric mean predicted decode tok/s, np4 spec ON','higher_is_better':True,'a_a_mismatch_count':sum(x.get('tokens')!=y.get('tokens') for x,y in zip(A1,A2)),'a_a_first_divergence':[first_div(x,y) for x,y in zip(A1,A2)],'knob_off_mismatch':[i for i,(a,o) in enumerate(zip(A1,O)) if not same(a,o)],'knob_on_mismatch':[i for i,(a,b,c) in enumerate(zip(A1,B1,B2)) if not same(a,b) or not same(a,c)],'feature_mismatch':{k:[i for i,(a,f) in enumerate(zip(A1,v)) if not same(a,f)] for k,v in F.items()}}
if base['a_a_mismatch_count']:
 m=base['a_a_mismatch_count']
 counts={'O':len(base['knob_off_mismatch']),'B1':sum(not same(a,b) for a,b in zip(A1,B1)),'B2':sum(not same(a,b) for a,b in zip(A1,B2)),**{k:len(v) for k,v in base['feature_mismatch'].items()}}
 base['g_det_fallback']={'m_AA':m,'mismatch_counts_against_A1':counts,'within_tolerance':all(n<=m for n in counts.values()),'reference_A2_sha256':hashlib.sha256(json.dumps([r['tokens'] for r in A2],sort_keys=True).encode()).hexdigest(),'serial_followup':str(G/'SERIAL-FOLLOWUP.json')}
 base['verdict']='INCONCLUSIVE_SERIAL_REQUIRED';base['reason']='G-DET failed; m_AA fallback counted and serial A/A/B/O tier required before any ship decision'
 (G/'SERIAL-FOLLOWUP.json').write_text(json.dumps({'status':'PREPARED','trigger':'G-DET A1/A2 tokens mismatch','m_AA':m,'within_tolerance':base['g_det_fallback']['within_tolerance'],'launcher':str(G/'launch_gpu.sh'),'mode':'serial','required_arms':['SA1','SA2','SB','SO'],'prompts':8,'max_tokens':256,'one_request_at_a_time':True,'decision':'serial A/A identity then B and O exact tokens, content and equal draft counts; otherwise INCONCLUSIVE'},indent=2)+'\n')
elif base['knob_off_mismatch']:
 base['verdict']='INCONCLUSIVE';base['reason']='G-OFF failed; knob-off not champion-identical'
elif base['knob_on_mismatch'] or any(base['feature_mismatch'].values()):
 base['verdict']='INCONCLUSIVE_RERUN';base['reason']='G-ON failed; rerun B with only passing feature tokens in new window'
else:
 pairs=[];excluded=[]
 for i,(a,b,c,d) in enumerate(zip(A1,B1,A2,B2)):
  if not all(x.get('tokens')==a.get('tokens') for x in (b,c,d)):
   excluded.append(i);continue
  t=[x.get('timings',{}).get('predicted_per_second') for x in (a,b,c,d)]
  if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in t):excluded.append(i);continue
  pairs.append(t)
 base['excluded_prompts']=excluded;base['paired_n']=len(pairs)
 if len(excluded)>6 or not pairs:
  base['verdict']='INCONCLUSIVE';base['reason']='more than 25% excluded or no pair'
 else:
  a1,b1,a2,b2=zip(*pairs)
  S=gm([math.sqrt(y*z/(x*w)) for x,y,w,z in pairs])-1
  NF=max(abs(gm([y/x for x,y in zip(a1,a2)])-1),abs(gm([y/x for x,y in zip(b1,b2)])-1))
  signs=[gm([y/x for x,y in zip(a1,b1)])-1,gm([y/x for x,y in zip(a2,b1)])-1,gm([y/x for x,y in zip(a2,b2)])-1]
  same_sign=all((v>0)==(S>0) for v in signs)
  base.update({'S':S,'NF':NF,'alternation_effects':signs,'alternation_same_sign':same_sign,'min_ship_effect':max(.01,2*NF),'plausibility_upper':.0371+2*NF,'AA_ratios_p10_p90':[sorted([y/x for x,y in zip(a1,a2)])[max(0,round(.1*(len(pairs)-1)))],sorted([y/x for x,y in zip(a1,a2)])[min(len(pairs)-1,round(.9*(len(pairs)-1)))]]})
  if NF>.0185:base['verdict']='UNDERPOWERED';base['reason']='one A3/B3 extension allowed'
  elif S>.0371+2*NF:base['verdict']='SUSPECT';base['reason']='above host-share plausibility ceiling; DEBUG attribution required'
  elif abs(S)<max(.01,2*NF):base['verdict']='NULL';base['reason']='effect below E_min/2NF; close GPU-ZOS-2 with numbers'
  elif S<=-2*NF:base['verdict']='REGRESS';base['reason']='decode tok/s regressed beyond 2NF'
  elif S>=max(.01,2*NF) and same_sign:base['verdict']='SHIP';base['reason']='all original correctness and speed gates pass; pending champion fold only'
  else:base['verdict']='INCONCLUSIVE';base['reason']='effect or alternation did not meet predeclared decision bands'
# Each native response slot is joined to one positive timing block within its wave.
for arm in ('A1','B1','A2','B2','O','F1','F2','F3'):
 waves=[json.loads(s) for s in (OUT/arm/'waves.jsonl').read_text().splitlines()]
 base.setdefault('request_graph_proofs',{})[arm]=sum(len(w.get('graph_proofs',[])) for w in waves)
 if any(len(w.get('graph_proofs',[]))!=len(w['responses']) or any(g['graphs_reused']<=0 for g in w['graph_proofs']) or not all(valid_response(r,w.get('max_tokens')) and sum(g['slot']==r['id_slot'] for g in w.get('graph_proofs',[]))==1 for r in w['responses']) for w in waves):
  base['verdict']='INCONCLUSIVE';base['reason']=f'native response fields/count or per-request positive graph proof missing on {arm}'
p=OUT/'RESULT.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(base,indent=2)+'\n');tmp.replace(p)
print(base['verdict'],base['reason'])
