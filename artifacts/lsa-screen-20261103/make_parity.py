#!/usr/bin/env python3
"""Freeze independent short chat retrieval sentinel; no inference."""
import ast,gzip,hashlib,json,os,subprocess
from pathlib import Path
from tokenizers import Tokenizer
P=Path(__file__).resolve().parent;m=json.loads((P/'manifest.json').read_text());out=P/'parity-manifest.json'
if out.exists():raise SystemExit('parity manifest already frozen')
text='<|im_start|>user\nArchive note: Project ORCHID has accession ZX-742-B. What is the exact accession for Project ORCHID? Reply only with the accession. /no_think<|im_end|>\n<|im_start|>assistant\n'
t=Tokenizer.from_file(m['tokenizer']);ids=t.encode(text,add_special_tokens=False).ids
binary='/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/build-cpu/bin/llama-tokenize';env=dict(os.environ,LD_LIBRARY_PATH=str(Path(binary).parent))
r=subprocess.run([binary,'-m',m['model'],'--stdin','--ids','--no-bos'],input=text,text=True,capture_output=True,check=True,env=env)
if ast.literal_eval(r.stdout.strip())!=ids:raise SystemExit('candidate chat-special tokenizer parity mismatch')
assert len(ids)<=1024
payload=json.dumps(ids,separators=(',',':')).encode();rel='inputs/parity-short-docqa.json.gz'
with open(P/rel,'xb') as f:
 with gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as g:g.write(payload)
row={'id':'parity-short-docqa','split':'dev','group':'document_qa','nominal':len(ids),'prompt_n':len(ids),'max_output_tokens':24,'token_ids':rel,'token_ids_sha256':hashlib.sha256(payload).hexdigest(),'expected':'ZX-742-B','exact_sentinel':True,'source_id':'independent-parity-docqa-v1','evidence_offsets':[]}
m.update(status='independent_short_parity_fixture',rows=[row],parent_manifest_sha256=hashlib.sha256((P/'manifest.json').read_bytes()).hexdigest(),chat_template='Qwen im_start/im_end; user requests /no_think',candidate_tokenizer_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),special_token_parity='passed candidate tokenizer on exact complete prompt')
with out.open('x') as f:json.dump(m,f,sort_keys=True,separators=(',',':'));f.write('\n')
print('parity prompt tokens',len(ids),'output cap',row['max_output_tokens'],'sha256',row['token_ids_sha256'])
