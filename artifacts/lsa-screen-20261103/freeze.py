#!/usr/bin/env python3
"""Freeze token-ID inputs. Run under CPU region lock; never invokes inference."""
import ast,gzip,hashlib,json,os,subprocess,sys
from pathlib import Path
from tokenizers import Tokenizer
P=Path(__file__).resolve().parent
if (P/'manifest.json').exists():raise SystemExit('manifest already frozen; do not overwrite')
MODEL=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TOKENIZER=Path('/mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw/tokenizer.json')
CLI='/mnt/raid0/llm/llama.cpp/build/bin/llama-tokenize'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
tok=Tokenizer.from_file(str(TOKENIZER))
def enc(s):return tok.encode(s,add_special_tokens=False).ids
# Probe plain text, Unicode, punctuation and benchmark-specific boundaries against exact GGUF.
env=dict(os.environ,LD_LIBRARY_PATH='/mnt/raid0/llm/llama.cpp/build/bin')
probes=['hello world','File dev-code-00.py: def transform_abcdef(3): return 32\n','crate K0123 has 42 packs.\nCatalog: 13 units.',' Café Ω → 中\nQuestion: checkpoint?']
for text in probes:
 p=subprocess.run([CLI,'-m',str(MODEL),'--stdin','--ids','--no-bos','--no-parse-special'],input=text,text=True,capture_output=True,env=env,check=True)
 if ast.literal_eval(p.stdout.strip())!=enc(text):raise SystemExit('GGUF tokenizer parity mismatch: '+repr(text))
rows=[json.loads(x) for x in (P/'cohort.jsonl').read_text().splitlines()]
assert len(rows)==64 and len({r['id'] for r in rows})==64
out=P/'inputs';out.mkdir(exist_ok=True)
manifest=[]
for r in rows:
 evidence=r['evidence'] if isinstance(r['evidence'],list) else [r['evidence']]
 question=enc('\nQuestion: '+r['question']+'\nAnswer:')
 # All three links occupy separate thirds; single sentinel stratifies its placement.
 chunks=[enc('\n'+s+'\n') for s in evidence]
 filler=enc(f"\nArchive {r['id']}: unrelated record describing routine observations and revision notes.\n")
 for nominal in (8192,32768,131072,262144):
  target=min(nominal,262144-256); positions=([target//6,target//2,5*target//6] if len(chunks)==3 else [{'early':target//6,'middle':target//2,'late':5*target//6}[r['position']]])
  ids=[]
  for pos,chunk in zip(positions,chunks):
   n=max(0,pos-len(ids)); ids.extend((filler*((n+len(filler)-1)//len(filler)))[:n]);ids.extend(chunk)
  n=target-len(ids)-len(question)
  if n<0:raise ValueError('prompt exceeds target')
  ids.extend((filler*((n+len(filler)-1)//len(filler)))[:n]);ids.extend(question)
  payload=dump(ids); rel=f"inputs/{r['id']}-{nominal}.json.gz"
  with open(P/rel,'wb') as f:
   with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as g:g.write(payload)
  manifest.append(dict(id=r['id'],split=r['split'],group=r['group'],nominal=nominal,prompt_n=len(ids),max_output_tokens=256,token_ids=rel,token_ids_sha256=hashlib.sha256(payload).hexdigest(),expected=r['answer'],exact_sentinel=r['exact_sentinel'],source_id=r['source_id'],evidence_offsets=positions))
identity={'cohort_sha256':sha(P/'cohort.jsonl'),'generator_sha256':sha(P/'prepare.py'),'freezer_sha256':sha(P/'freeze.py'),'model':str(MODEL),'model_sha256':sha(MODEL),'tokenizer':str(TOKENIZER),'tokenizer_sha256':sha(TOKENIZER),'gguf_tokenizer_cli':CLI,'gguf_tokenizer_cli_sha256':sha(CLI),'gguf_tokenizer_probe_count':len(probes),'tokenizer_parity':'four probe texts passed; direct frozen IDs are supplied to server','global_layers':16,'native_ctx':262144,'map_hashes':'pending runtime maps','effective_config':'pending runtime booking','source_commit':'pending runtime build','arms':['dense','all_keys','pca','distilled','oracle_topk','window'],'status':'inputs_frozen_runtime_identity_pending','rows':manifest}
(P/'manifest.json').write_bytes(dump(identity)+b'\n')
print('frozen',len(manifest),'inputs')
