import json,hashlib,collections,math
from pathlib import Path
r=Path('/mnt/raid0/llm/tmp/codex-ni-yarn-agg1g-prep-20261031'); out={};data={};rows={}
for arm in ('A0','A1'):
 b=(r/'run/results'/f'{arm}.jsonl').read_bytes();a=[json.loads(x) for x in b.splitlines()];data[arm]={x['item_id']:x for x in a}; assert len(data[arm])==len(a)
 assert all(x['n_source']=='server_timings' and x['real_n']==x['timings']['prompt_n']+x['timings'].get('cache_n',0) for x in a)
 out[arm]={'records':len(a),'sha256':hashlib.sha256(b).hexdigest(),'statuses':dict(collections.Counter(x['status'] for x in a))}
ids=set(data['A0'])&set(data['A1']); bad=[]; rr=[]
for i in sorted(ids):
 a=data['A0'][i];b=data['A1'][i]
 if a['prompt_sha256']!=b['prompt_sha256'] or a['plan_sha256']!=b['plan_sha256']:bad.append(i)
 if a['right']!=(a['score']==1.0) or b['right']!=(b['score']==1.0):bad.append(i)
 rr.append((i,a,b))
src=[json.loads(x) for x in (r/'source-120/items.jsonl').read_text().splitlines()]; sub={x['item_id']:x['prompt_sha256'] for x in src};assert len(sub)==120
jointplan=[json.loads(x) for x in (r/'run/plan/items.jsonl').read_text().splitlines()];jointmap={x['item_id']:x['prompt_sha256'] for x in jointplan};assert len(jointmap)==141 and all(jointmap.get(i)==h for i,h in sub.items())
for i,a,b in rr:
 if i in sub and sub[i]!=a['prompt_sha256']:bad.append(i)

def stats(rs):
 native=[(a,b) for i,a,b in rs if a['zone']=='native' and b['zone']=='native'];n=len(native);bc=sum(a['right'] and not b['right'] for a,b in native);cc=sum(not a['right'] and b['right'] for a,b in native);p=sum(math.comb(bc+cc,k) for k in range(bc,bc+cc+1))/2**(bc+cc);return {'matched_pairs':len(rs),'native_pairs':n,'b':bc,'c':cc,'p':p,'mean_a1_minus_a0':sum(b['score']-a['score'] for a,b in native)/n if n else None}
out.update({'joint':stats(rr),'original120_subset':stats([(i,a,b) for i,a,b in rr if i in sub]),'original120_size':len(sub),'original120_matched_in_joint_plan':sum(jointmap.get(i)==h for i,h in sub.items()),'pair_binding_errors':len(bad),'paired_ids_sha256':hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest(),'scope':'snapshot not complete gate','results':str(r/'run/results')});print(json.dumps(out,indent=2))
