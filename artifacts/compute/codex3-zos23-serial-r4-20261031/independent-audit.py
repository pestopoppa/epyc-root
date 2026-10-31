import json,hashlib
from pathlib import Path
r=Path('/mnt/raid0/llm/tmp/codex-ni-gpu-zos-build-prep-20261031/successor/gpu/serial-tier/out'); arms=['SA1','SA2','SB','SO'];ws={}; errs=[];details={}
for a in arms:
 d=r/a;c=json.loads((d/'COMPLETE.json').read_text());lines=[json.loads(x) for x in (d/'waves.jsonl').read_text().splitlines()];ws[a]=lines
 if [x['wave'] for x in lines]!=list(range(9)):errs.append([a,'waves'])
 for name,h in c['files'].items():
  if hashlib.sha256((d/name).read_bytes()).hexdigest()!=h:errs.append([a,name])
 for x in lines:
  if len(x['responses'])!=1 or len(x['prompts'])!=1 or len(x['graph_proofs'])!=1 or not x['responses'][0]['ok'] or x['responses'][0]['code']!=200:errs.append([a,'response'])
  if x['max_tokens']!=(64 if x['wave']==0 else 256):errs.append([a,'max_tokens'])
  if x['guard_tripped'] or x['vram_inside_count']<1 or x['vram_peak']<=0:errs.append([a,'residency'])
 argv=c['argv'];assert '-np' in argv and argv[argv.index('-np')+1]=='4' and '393216' in argv
 details[a]={'complete_sha256':hashlib.sha256((d/'COMPLETE.json').read_bytes()).hexdigest(),'waves_sha256':hashlib.sha256((d/'waves.jsonl').read_bytes()).hexdigest(),'vram_peak_max':max(x['vram_peak'] for x in lines),'vram_sample_count':sum(x['vram_inside_count'] for x in lines),'env':c['environ']}
assert (r.parent/'prompts.json').read_bytes()==(r.parent.parent/'prompts.json').read_bytes()
original=json.loads((r.parent/'prompts.json').read_text())
for n in range(1,9):
 assert ws['SA1'][n]['prompts']==[original[n-1]]
 p=ws['SA1'][n]['prompts']; ph=ws['SA1'][n]['prompt_sha256'];base=ws['SA1'][n]['responses'][0]
 for a in arms[1:]:
  w=ws[a][n];z=w['responses'][0]
  if w['prompts']!=p or w['prompt_sha256']!=ph:errs.append([a,n,'prompt'])
  if not (base['tokens'] and base['content'] and z['tokens']==base['tokens'] and z['content']==base['content'] and all(z['timings'].get(k)==base['timings'].get(k) and k in z['timings'] and k in base['timings'] for k in ['draft_n','draft_n_accepted'])):errs.append([a,n,'response'])
core=json.loads((r/'RESULT.json').read_text());final=json.loads((r/'SERIAL-RESULT.json').read_text());assert not errs,errs
assert core['verdict']=='INCONCLUSIVE_SERIAL_REQUIRED' and core['g_det_fallback']['within_tolerance'] and final['correctness']=='PASS' and not final['ship_authorized']
assert hashlib.sha256((r/'RESULT.json').read_bytes()).hexdigest()==final['core_sha256'] and hashlib.sha256((r/'RUN-INTENT-serial.json').read_bytes()).hexdigest()==final['run_intent_sha256']
print(json.dumps({'arms':details,'serial_prompts':8,'per_arm_responses':8,'all_serial_token_content_and_draft_match':True,'original_core_m_AA':core['g_det_fallback']['m_AA'],'core_within_tolerance':True,'correctness':'PASS','ship_authorized':False,'scope':'serial correctness only; no speed gate'},indent=2))
