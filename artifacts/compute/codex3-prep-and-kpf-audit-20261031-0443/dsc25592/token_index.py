#!/usr/bin/env python3
"""Private source metadata index; exact native vocabulary, no inference or transcript output."""
import hashlib,json,os,pathlib,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent;RESEARCH=pathlib.Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/kpf64_replay');sys.path[:0]=[str(RESEARCH),'/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cafe1'];import adapter,smoke_admission
BIN='/mnt/raid0/llm/kernels/production/cpu';MODEL='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf';expected_model='c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131'
env={**os.environ,'LD_LIBRARY_PATH':BIN,'HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1','OMP_NUM_THREADS':'1'};source=D/'PRIVATE-SESSION-SHA256SUMS'
if subprocess.run(['sha256sum','-c','--quiet',str(source)],cwd=D).returncode:raise RuntimeError('selected source corpus drift')
rows=[];started=time.monotonic()
for p in sorted((D/'private-sessions').glob('*.json')):
 if p.name=='manifest.json':continue
 s=json.loads(p.read_text());turns=s['turns']
 for k,prompt,prev in adapter.iter_prompts(turns,None,slot_holds_output=False):
  if time.monotonic()-started>850:raise RuntimeError('prep deadline')
  smoke_admission.check(os.sched_getaffinity(0))
  proc=subprocess.run([BIN+'/llama-tokenize','-m',MODEL,'--stdin','--ids','--no-escape'],input=prompt.encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,timeout=60)
  if proc.returncode:raise RuntimeError('vocab-only tokenizer failed')
  ids=json.loads(proc.stdout);rows.append({'session':s['id'],'source_store':s['store'],'turn':k,'reset':bool(turns[k].get('reset')),'has_previous_prefix':prev is not None,'prompt_chars':len(prompt),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'prompt_tokens':len(ids),'following_turn_exists':k+1<len(turns) and not turns[k+1].get('reset')})
obj={'schema':'dsc25592.native-token-index.v1','scope':'20 fixed selected real sessions, all turns before any inference; native production tokenizer in vocab-only mode','source_catalog_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'model_sha256':expected_model,'tokenizer_binary_sha256':hashlib.sha256(pathlib.Path(BIN+'/llama-tokenize').read_bytes()).hexdigest(),'rows':rows};dest=D/'TOKEN-INDEX.json';fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print('indexed',len(rows),'metadata entries in',round(time.monotonic()-started,2),'s; sha256',hashlib.sha256(dest.read_bytes()).hexdigest())
