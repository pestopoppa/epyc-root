import json,hashlib,collections
from pathlib import Path
b=Path('/mnt/raid0/llm/tmp/codex-ni-gpu-zos-build-prep-20261031/successor/gpu/out');result=json.loads((b/'RESULT.json').read_text()); arms=['A1','B1','A2','B2','O','F1','F2','F3']; data={};
for arm in arms:
 d=b/arm;c=json.loads((d/'COMPLETE.json').read_text());assert c['run_intent_sha256']==result['run_intent_sha256'];
 for name,h in c['files'].items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==h,(arm,name)
 ws=[json.loads(x) for x in (d/'waves.jsonl').read_text().splitlines()];assert len(ws)==(7 if arm in arms[:5] else 3)
 assert all(len(w['responses'])==4 and len(w['graph_proofs'])==4 and w['vram_inside_count']>=2 and not w['guard_tripped'] for w in ws)
 for w in ws:
  for z in w['responses']:
   assert len(z['tokens'])==w['max_tokens'] and z['tokens_predicted']==w['max_tokens'] and z['usage']['completion_tokens']==w['max_tokens'] and z['content'] and z['timings']['draft_n']>0 and 0<=z['timings']['draft_n_accepted']<=z['timings']['draft_n']
   assert sum(g['slot']==z['id_slot'] and g['graphs_reused']>0 for g in w['graph_proofs'])==1
 data[arm]=[r for w in ws if w['wave']>0 for r in w['responses']]
def same(a,b):return all([a['tokens']==b['tokens'],a['content']==b['content'],a['timings']['draft_n']==b['timings']['draft_n'],a['timings']['draft_n_accepted']==b['timings']['draft_n_accepted']])
a=data['A1'];aa=sum(x['tokens']!=y['tokens'] for x,y in zip(a,data['A2']));print('A/A token mismatch',aa,'/',len(a));assert aa==result['a_a_mismatch_count']==24
for k in ['O','B1','B2','F1','F2','F3']:
 n=sum(not same(x,y) for x,y in zip(a,data[k]));print(k,'mismatch',n,'/',len(data[k]));assert n==result['g_det_fallback']['mismatch_counts_against_A1'][k]
print('all arm file hashes verified; 4 streams, 1024 tokens on measured waves, draft counts, graph reuse and >=2 in-wave residency samples validated; m_AA fallback alone cannot ship, serial tier required')
