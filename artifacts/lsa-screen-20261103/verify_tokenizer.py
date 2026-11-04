#!/usr/bin/env python3
"""Compare model tokenizer examples with the candidate build's metadata-only tokenizer."""
import argparse,ast,hashlib,json,os,subprocess
from pathlib import Path
from tokenizers import Tokenizer
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--binary',required=True,type=Path);p.add_argument('--library-path',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
m=json.loads((P/'manifest.json').read_text());tok=Tokenizer.from_file(m['tokenizer'])
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
if sha(m['model'])!=m['model_sha256'] or sha(m['tokenizer'])!=m['tokenizer_sha256']:raise SystemExit('model or tokenizer hash drift')
texts=['hello world','File dev-code-00.py: def transform_abcdef(3): return 32\n','crate K0123 has 42 packs.\nCatalog: 13 units.',' Café Ω → 中\nQuestion: checkpoint?']
env=dict(os.environ,LD_LIBRARY_PATH=a.library_path);results=[]
for text in texts:
 r=subprocess.run([str(a.binary),'-m',m['model'],'--stdin','--ids','--no-bos','--no-parse-special'],input=text,text=True,capture_output=True,env=env,check=True);observed=ast.literal_eval(r.stdout.strip());expected=tok.encode(text,add_special_tokens=False).ids
 results.append({'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'expected':expected,'observed':observed,'equal':observed==expected})
proof={'schema':'lsa-candidate-tokenizer-parity-v1','candidate_tokenizer':str(a.binary.resolve()),'candidate_tokenizer_sha256':sha(a.binary),'library_path':a.library_path,'model_sha256':m['model_sha256'],'tokenizer_sha256':m['tokenizer_sha256'],'probe_count':len(results),'results':results,'passed':all(x['equal'] for x in results),'scope':'four sample texts; requests supply frozen token IDs directly'}
with a.output.open('x') as f:json.dump(proof,f,sort_keys=True);f.write('\n')
if not proof['passed']:raise SystemExit('candidate tokenizer parity failed')
print('candidate tokenizer probes passed')
