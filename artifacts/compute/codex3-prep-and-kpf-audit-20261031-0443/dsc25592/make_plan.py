#!/usr/bin/env python3
"""Freeze outcome-independent 16K/64K real-trace cases using the complete native token index."""
import hashlib,json,os,pathlib
D=pathlib.Path(__file__).resolve().parent;h=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();spec=json.loads((D/'PREDECLARED.json').read_text());index=json.loads((D/'TOKEN-INDEX.json').read_text())
if index['source_catalog_sha256']!=h(D/'PRIVATE-SESSION-SHA256SUMS') or index['model_sha256']!=spec['model_sha256']:raise RuntimeError('token index source drift')
rows=index['rows'];manifest=json.loads((D/'private-sessions/manifest.json').read_text());expected=manifest['totals']['requests'];by={(r['session'],r['turn']):r for r in rows};groups=[]
if len(rows)!=expected or len(by)!=len(rows) or index['tokenizer_binary_sha256']!=h('/mnt/raid0/llm/kernels/production/cpu/llama-tokenize'):raise RuntimeError('incomplete token index or tokenizer drift')
for store in ('claude','codex','opencode'):
 for name,(lo,hi) in spec['context_strata_tokens'].items():
  eligible=[];seen=set()
  for r in sorted(rows,key=lambda x:(x['session'],x['turn'])):
   if r['source_store']!=store or r['session'] in seen or not lo<=r['prompt_tokens']<=hi or not r['has_previous_prefix'] or not r['following_turn_exists']:continue
   seq=[by.get((r['session'],r['turn']+d)) for d in (-1,0,1)]
   if any(x is None or x['prompt_tokens']>=65530 for x in seq) or seq[1]['reset'] or seq[2]['reset']:continue
   eligible.append({'session':r['session'],'target_turn':r['turn'],'turns':[{'turn':x['turn'],'prompt_sha256':x['prompt_sha256'],'prompt_tokens':x['prompt_tokens']} for x in seq]});seen.add(r['session'])
  groups.append({'store':store,'stratum':name,'token_band':[lo,hi],'eligible_session_count':len(eligible),'required':2,'chosen':eligible[:2],'unfilled':max(0,2-len(eligible))})
obj={'schema':'dsc25592.case-plan.v1','predeclared_sha256':h(D/'PREDECLARED.json'),'token_index_sha256':h(D/'TOKEN-INDEX.json'),'private_source_catalog_sha256':h(D/'PRIVATE-SESSION-SHA256SUMS'),'groups':groups,'native_sequences_planned':sum(len(x['chosen']) for x in groups),'unfilled_sequence_slots':sum(x['unfilled'] for x in groups),'raw_prompts_in_plan':False,'inference_started':False};p=D/'CASE-PLAN.json';fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print('planned',obj['native_sequences_planned'],'unfilled',obj['unfilled_sequence_slots'],'sha256',h(p))
for g in groups:print(g['store'],g['stratum'],'eligible',g['eligible_session_count'],'chosen',len(g['chosen']),'unfilled',g['unfilled'])
