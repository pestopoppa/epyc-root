from pathlib import Path
import json,math,statistics,hashlib
p=Path('/mnt/raid0/llm/tmp/codex-ni-zos23-concurrent-successor-20261031/out'); arms=['A1','B1','A2','B2','O','F1','F2','F3']; rows={}; proofs={};errors=[];h=lambda q:hashlib.sha256(q.read_bytes()).hexdigest(); intent=h(p/'RUN-INTENT-full.json')
for arm in arms:
 f=p/arm; c=json.loads((f/'COMPLETE.json').read_text()); ws=[json.loads(s) for s in (f/'waves.jsonl').read_text().splitlines()];
 if c['run_intent_sha256']!=intent:errors.append((arm,'intent'))
 for w in ws:
  if w['guard_tripped'] or w['vram_inside_count']<=0 or w['vram_peak']<=0 or len(w['responses'])!=len(w['graph_proofs']):errors.append((arm,'wave-proof'))
  for z in w['responses']:
   t=z['timings'];g=[g for g in w['graph_proofs'] if g['slot']==z['id_slot'] and g['graphs_reused']>0];
   if not z['ok'] or z['code']!=200 or len(z['tokens'])!=w['max_tokens'] or z['tokens_predicted']!=w['max_tokens'] or z['usage']['completion_tokens']!=w['max_tokens'] or not z['content'] or t['draft_n']<=0 or not 0<=t['draft_n_accepted']<=t['draft_n'] or len(g)!=1:errors.append((arm,'response'))
 rows[arm]=[r for w in ws if w['wave']>0 for r in w['responses']]; proofs[arm]=sum(len(w['graph_proofs']) for w in ws)
 expected=8 if arm.startswith('F') else 24
 if len(rows[arm])!=expected:errors.append((arm,'count'))
def same(a,b):return all(a[k]==b[k] for k in ('tokens','content')) and all(a['timings'][k]==b['timings'][k] for k in ('draft_n','draft_n_accepted'))
A,B,C,D,O=(rows[k] for k in ('A1','B1','A2','B2','O')); mismatch={'AA_tokens':sum(a['tokens']!=c['tokens'] for a,c in zip(A,C)),'OFF':sum(not same(a,o) for a,o in zip(A,O)),'B1':sum(not same(a,b) for a,b in zip(A,B)),'B2':sum(not same(a,d) for a,d in zip(A,D))};mismatch.update({k:sum(not same(a,f) for a,f in zip(A,rows[k])) for k in ('F1','F2','F3')});gm=lambda xs:math.exp(statistics.mean(math.log(x) for x in xs)); pairs=[[r['timings']['predicted_per_second'] for r in v] for v in zip(A,B,C,D)];assert all(all(math.isfinite(x) and x>0 for x in v) for v in pairs)
S=gm([math.sqrt(b*d/(a*c)) for a,b,c,d in pairs])-1;NF=max(abs(gm([c/a for a,b,c,d in pairs])-1),abs(gm([d/b for a,b,c,d in pairs])-1)); signs=[gm([b/a for a,b,c,d in pairs])-1,gm([b/c for a,b,c,d in pairs])-1,gm([d/c for a,b,c,d in pairs])-1]
result={'schema':'independent-zos-r5-audit/v1','intent_sha256':intent,'arms':{a:len(rows[a]) for a in arms},'mismatches':mismatch,'S':S,'NF':NF,'alternation_effects':signs,'graph_proofs_including_warmup':proofs,'all_positive_vram':True,'errors':errors,'paired_denominator':len(pairs),'threshold_band':'UNDERPOWERED' if NF>.0185 else 'OTHER','source_result_sha256':h(p/'RESULT.json')}; print(json.dumps(result,indent=2));assert not errors and not any(mismatch.values())
