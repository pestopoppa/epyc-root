"""Prospective same-input natural delegation pair; no model access in this module."""
import hashlib,json,re
from pathlib import Path
SOURCE=Path('/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/hotpot-validation-first10.json')
SOURCE_SHA='01d18636ad86217cca40b34ed5cb8eccc75120a2457b7101e017c36439711fa7'
ARMS=('production_repl','redel_delegate_wait')
def population(path=SOURCE,expected_sha=SOURCE_SHA):
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected_sha:raise ValueError('dataset digest mismatch')
 rows=json.loads(data)['rows']
 if len(rows)!=10 or [x['row_idx'] for x in rows]!=list(range(10)):raise ValueError('original diagnostic population required')
 result=[];ids=set()
 for x in rows:
  r=x['row'];titles=r['context']['title'];sentences=r['context']['sentences']
  if len(titles)!=len(sentences) or r['id'] in ids:raise ValueError('invalid context or duplicate ID')
  ids.add(r['id']);context='\n\n'.join('['+t+']\n'+' '.join(s) for t,s in zip(titles,sentences));prompt='Answer the question using the documents. Give a concise answer.\n\n'+context+'\n\nQuestion: '+r['question']
  result.append({'id':r['id'],'prompt':prompt,'gold':r['answer'],'prior_exposure':'20261029 prior historical-emulation and ReDel diagnostic'})
 return result

def model_input(row):
 # The caller gets no reference answers or scoring metadata.
 if not isinstance(row['prompt'],str) or not row['prompt']:raise ValueError('empty prompt')
 return {'prompt':row['prompt']}
def exact(answer,gold):
 normalize=lambda x:' '.join(re.sub(r'[^a-z0-9 ]',' ',x.lower()).split())
 return normalize(answer)==normalize(gold)
def summary(expected_ids,records):
 ids=list(expected_ids)
 if len(ids)!=len(set(ids)):raise ValueError('duplicate expected IDs')
 observed={}
 for r in records:
  key=(r['id'],r['arm'])
  if r['id'] not in ids or r['arm'] not in ARMS or key in observed:raise ValueError('unexpected or duplicate observation')
  if r['status'] not in ('complete','failed','unknown'):raise ValueError('invalid status')
  if r['status']=='complete' and (not isinstance(r.get('delegations'),int) or r['delegations']<0 or not isinstance(r.get('correct'),bool)):raise ValueError('incomplete evidence')
  observed[key]=r
 complete=[i for i in ids if all(observed.get((i,a),{}).get('status')=='complete' for a in ARMS)]
 natural=[i for i in complete if any(observed[(i,a)]['delegations']>0 for a in ARMS)]
 return {'population':len(ids),'expected_cells':2*len(ids),'observed_cells':len(observed),'complete_pairs':len(complete),'naturally_delegating_complete_pairs':len(natural),'failed_cells':sum(r['status']=='failed' for r in records),'unknown_cells':sum(r['status']=='unknown' for r in records),'missing_cells':2*len(ids)-len(observed),'eligible_substrate_comparison':bool(natural)}
