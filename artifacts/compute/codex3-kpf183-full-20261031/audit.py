#!/usr/bin/env python3
import hashlib,json,math,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-kpf183-multiturn-20261030');O=Path('/mnt/raid0/llm/tmp/codex3-kpf183-full-filing-20261031'); B=Path('/mnt/raid0/llm/tmp/codex3-kpf183-e332-build-r2-20261030')
M=Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
 return h.hexdigest()
def endhash(p):
 with p.open('rb') as f:
  n=os.fstat(f.fileno()).st_size;first=hashlib.sha256(f.read(64*1024**2)).hexdigest();f.seek(n-64*1024**2);last=hashlib.sha256(f.read()).hexdigest()
 return {'size':n,'first64':first,'last64':last}
model=endhash(M);assert (model['size'],model['first64'],model['last64'])==(37801097504,'3711c69305b6d77a3a8bc69abff096cda9f90238887f29ce3e83ec5f3cd348eb','d90af8cf5c5047a758c11a6fd64f4902708f55cb96bee73201814f4755954bfa')
model.update(path=str(M),full_sha256_expected='c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131',full_sha256_prior_verified_log=str(D/'Q8-MODEL-SHA256.log'))
result=json.loads((D/'run/RESULT.json').read_text());records=result['records'];prompts=json.loads((D/'prompts.json').read_text())['full']
assert result['complete'] is True and result['smoke'] is False and len(records)==12
assert json.loads((D/'run/records.json').read_text())==records
assert {(r['arm'],r['case']['id']) for r in records}=={(a,c['id']) for a in ['champion','fork-off','fork-on'] for c in prompts}
assert all(r['trunk']['ok'] and len(r['children'])==2 and {c['slot'] for c in r['children']}=={1,2} and all(c['ok'] for c in r['children']) for r in records)
assert not (D/'run/pending.json').exists()
def parsed(response,lane):
 if lane=='raw':
  probs=response.get('completion_probabilities')
  return {'text':response.get('content'),'tokens':response.get('tokens'),'stop':response.get('stop_type'),'logprobs':probs,'timings_fork':{k:v for k,v in response.get('timings',{}).items() if 'fork' in k}}
 choice=response['choices'][0];return {'message':choice.get('message'),'tokens':[q['id'] for q in choice.get('logprobs',{}).get('content',[])], 'stop':choice.get('finish_reason'),'logprobs':choice.get('logprobs',{}).get('content'),'timings_fork':{k:v for k,v in response.get('timings',{}).items() if 'fork' in k}}
def snap(slots):
 return [{'slot':s.get('id'),'n_prompt_tokens':s.get('n_prompt_tokens'),'n_prompt_tokens_processed':s.get('n_prompt_tokens_processed'),'checkpoints':s.get('checkpoints'),'fork':s.get('fork'),'chat_format':s.get('params',{}).get('chat_format'),'generation_prompt':s.get('params',{}).get('generation_prompt'),'message_delimiters':s.get('message_delimiters')} for s in slots]
out=[];lookup={}
for rec in records:
 lane=rec['case']['lane'];t=parsed(rec['trunk']['response'],lane);ch=[]
 assert len(t['tokens'])==8 and t['stop']==('limit' if lane=='raw' else 'length')
 for c in rec['children']:
  z=parsed(c['response'],lane);assert len(z['tokens'])==8 and z['stop']==('limit' if lane=='raw' else 'length')
  z.update(slot=c['slot'],ok=c['ok'],n_fork_tokens=c['response'].get('timings',{}).get('n_fork_tokens'),fork_src_slot=c['response'].get('timings',{}).get('fork_src_slot'),fork_src_kind=c['response'].get('timings',{}).get('fork_src_kind'))
  if lane=='raw':
   z['expected_prompt_plus_reply']=rec['expected_prompt_reply_tokens'];z['gap']=None if z['n_fork_tokens'] is None else rec['expected_prompt_reply_tokens']-z['n_fork_tokens']
  ch.append(z)
 item={'arm':rec['arm'],'case':rec['case'],'route':'/completion' if lane=='raw' else '/v1/chat/completions','argv':rec['argv'],'binary_sha256':rec['binary_sha256'],'model':rec['model'],'trunk_prompt_tokens':len(rec['prompt_tokens']) if lane=='raw' else rec['trunk']['response'].get('usage',{}).get('prompt_tokens'),'trunk_reply_tokens':len(rec['reply_tokens']) if lane=='raw' else rec['trunk']['response'].get('usage',{}).get('completion_tokens'),'prompt_token_ids':rec.get('prompt_tokens'),'reply_token_ids':rec.get('reply_tokens'),'chat_reply_content_resent':rec.get('reply_text'),'trunk':t,'children':ch,'slots_after_trunk':snap(rec['slots_after_trunk']),'slots_after_children':snap(rec['slots_after_children'])}
 out.append(item);lookup[(rec['arm'],rec['case']['id'])]=item
assert all(x['model']==str(M) for x in out)
assert {x['binary_sha256'] for x in out if x['arm']=='champion'}=={'8f471d0cd130314811df1ad07b5946d8353ac237b28654c1cb4aef93b2ebc5d7'}
assert {x['binary_sha256'] for x in out if x['arm']!='champion'}=={'1442c95d7516efadda0639cf07319078df0bae326b6a9bb95d72532b1499ad67'}
for arm,path in [('champion',Path('/mnt/micron/codex3-lanes/kpf-e332-build/bin/llama-server')),('fork',Path('/mnt/raid0/llm/kernels/builds/cpu-20261021-80a09c6ad-p1r2-fork/bin/llama-server'))]:
 expected='8f471d0cd130314811df1ad07b5946d8353ac237b28654c1cb4aef93b2ebc5d7' if arm=='champion' else '1442c95d7516efadda0639cf07319078df0bae326b6a9bb95d72532b1499ad67'
 assert sha(path)==expected
comparisons=[]
for case in prompts:
 cid=case['id'];on=lookup['fork-on',cid]
 for base in ('fork-off','champion'):
  other=lookup[base,cid]
  for pos in range(3):
   a=on['trunk'] if pos==0 else on['children'][pos-1];b=other['trunk'] if pos==0 else other['children'][pos-1]
   ids_equal=a['tokens']==b['tokens'];pa=a['logprobs'] or [];pb=b['logprobs'] or []
   aligned=len(pa)==len(pb) and all(i.get('id')==j.get('id') for i,j in zip(pa,pb))
   delta=max((abs(i['logprob']-j['logprob']) for i,j in zip(pa,pb)),default=None) if aligned else None
   comparisons.append({'case':cid,'against':base,'request':'trunk' if pos==0 else 'child-'+str(pos),'token_ids_equal':ids_equal,'response_equal':(a.get('text')==b.get('text') if case['lane']=='raw' else a.get('message')==b.get('message')),'selected_logprobs_same_token_sequence':aligned,'max_abs_selected_logprob_delta':delta,'scope':'descriptive, not a conformance or performance gate'})
paths=[D/'run/RESULT.json',D/'run/records.json',D/'prompts.json',D/'PREDECLARED.md',D/'job.py',D/'launch.sh',D/'SOURCES.sha256',D/'80a09-end-checkpoint-source.txt',D/'Q8-MODEL-SHA256.log',D/'ws58-launcher.out',B/'BUILD-SUCCESS',B/'BUILD-DIGESTS.txt']
paths += [Path('/mnt/micron/codex3-lanes/kpf-e332-build/bin/llama-server'),Path('/mnt/raid0/llm/kernels/builds/cpu-20261021-80a09c6ad-p1r2-fork/bin/llama-server'),Path('/mnt/raid0/llm/kernels/builds/cpu-20261021-80a09c6ad-p1r2-fork/SHA256SUMS'),Path('/mnt/raid0/llm/kernels/builds/cpu-20261021-80a09c6ad-p1r2-fork/PROVENANCE.md'),Path('/mnt/raid0/llm/tmp/compute-flags/grants/codex3-kpf183-multiturn-r1-20261030.complete'),Path('/mnt/raid0/llm/tmp/compute-flags/grants/codex3-kpf183-multiturn-r1-20261030.ended'),Path('/mnt/raid0/llm/tmp/compute-flags/ready/armed/codex3-kpf183-multiturn-r1-20261030.json')]
paths+=list(sorted((D/'run').glob('*.log')))+list(sorted((D/'run').glob('*.log-digest.json')))
native={str(p):sha(p) for p in paths}
for arm in ('champion','fork-off','fork-on'):
 d=json.loads((D/'run'/f'{arm}.log-digest.json').read_text());assert d['sha256']==sha(Path(d['server_log']))
outcome={'schema':'kpf183-native-audit/v1','result':'COMPLETE diagnostic CPU items 2 and 3; GPU items 1 and 4 remain open','request_count':36,'http_ok':36,'http_status_codes':'not retained; urllib success and JSON decode recorded per request','cases':out,'comparisons':comparisons,'hashes':native,'model_identity':model,'limitations':['chat message_delimiters array is absent from slot snapshots, so its contents are unknown','chat child uses reply content text; generated reasoning_content is not resent; turn re-tokenization and delimiters change prefix, so counts cannot prove chat prompt-plus-generated-reply coverage','baseline n_fork_tokens and fork source kind are absent, not measured zero','slot snapshot omits checkpoint list for champion and fork-off','fixed eight-token length/limit completion is intended cap, not failure','descriptive response/logprob differences do not establish parity, quality, or performance']}
with (O/'AUDIT.json').open('w') as f:json.dump(outcome,f,indent=2);f.write('\n')
with (O/'FILES.sha256').open('w') as f:
 for p,h in native.items():f.write(h+'  '+p+'\n')
lines=['| Arm | Case | Route | Prompt | Reply | Child 1 fork/source | Child 2 fork/source | Trunk checkpoints (tokens:pos/pinned) |','|---|---|---|---:|---:|---|---|---|']
for x in out:
 def ck(z):
  if z is None:return 'unknown (field absent)'
  return ', '.join(str(k['n_tokens'])+':'+str(k['pos_max'])+('/pinned' if k['pinned'] else '/unpinned') for k in z) or 'none'
 def child(z):
  n=z['n_fork_tokens'];v='unknown' if n is None else str(n)+'/'+str(z['fork_src_kind'])+' src'+str(z['fork_src_slot'])
  if 'gap' in z:v+='; gap '+('unknown' if z['gap'] is None else str(z['gap']))
  return v
 lines.append('| '+x['arm']+' | '+x['case']['id']+' | '+x['route']+' | '+str(x['trunk_prompt_tokens'])+' | '+str(x['trunk_reply_tokens'])+' | '+child(x['children'][0])+' | '+child(x['children'][1])+' | '+ck(x['slots_after_trunk'][0]['checkpoints'])+' |')
(O/'TABLE.md').write_text('\n'.join(lines)+'\n')
print('AUDIT PASS 12 rows, 36 requests; raw fork-on full-coverage',sum(c['gap']==0 for x in out if x['arm']=='fork-on' and x['case']['lane']=='raw' for c in x['children']),'/4')
print('comparisons',len(comparisons),'token equal',sum(c['token_ids_equal'] for c in comparisons),'response equal',sum(c['response_equal'] for c in comparisons))
for ref in ('fork-off','champion'):
 cs=[c for c in comparisons if c['against']==ref]
 print(ref,'tokens',sum(x['token_ids_equal'] for x in cs),'/12','response',sum(x['response_equal'] for x in cs),'/12','max selected logprob delta',max(x['max_abs_selected_logprob_delta'] for x in cs if x['max_abs_selected_logprob_delta'] is not None),'aligned',sum(x['selected_logprobs_same_token_sequence'] for x in cs))
