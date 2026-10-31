#!/usr/bin/env python3
"""Choose original unedited agent conversation by metadata only; do not print prompt."""
import hashlib,json,os,pathlib,subprocess,sys
D=pathlib.Path(__file__).resolve().parent;src=D.parent/'dsc25592';sys.path.insert(0,'/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/kpf64_replay');import adapter
K=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin');M='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf';index=json.loads((src/'TOKEN-INDEX.json').read_text());candidates=sorted((r for r in index['rows'] if r['following_turn_exists'] and 70000<=r['prompt_tokens']<=100000),key=lambda r:(r['prompt_tokens'],r['session'],r['turn']));attempts=[]
for r in candidates:
 data=json.loads((src/'private-sessions'/(r['session']+'.json')).read_text());prompt=next(s for k,s,prev in adapter.iter_prompts(data['turns'],None,slot_holds_output=False) if k==r['turn']);digest=hashlib.sha256(prompt.encode()).hexdigest()
 if digest!=r['prompt_sha256']:raise RuntimeError('source prompt identity drift')
 env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
 proc=subprocess.run([str(K/'llama-tokenize'),'-m',M,'--stdin','--ids','--no-escape'],input=prompt.encode(),capture_output=True,env=env,timeout=120)
 if proc.returncode:raise RuntimeError('native tokenizer failed: '+proc.stderr.decode(errors='replace')[-500:])
 tokens=json.loads(proc.stdout);attempts.append({'session':r['session'],'turn':r['turn'],'sha256':digest,'architect_token_count':len(tokens),'selection_tokenizer_count':r['prompt_tokens']})
 if len(tokens)>65536:
  out={'selection':'first original conversation ordered by existing metadata token count, then session/turn, with following turn and actual architect native tokenizer count >65536; no truncation or score used','selected':attempts[-1],'attempts':attempts,'tokens_include_added_specials':'native tokenizer default; exact setting pinned'};p=D/'CONTEXT-METADATA.json';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump(out,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  print('selected',out['selected']);break
else:raise RuntimeError('no eligible original conversation found')
