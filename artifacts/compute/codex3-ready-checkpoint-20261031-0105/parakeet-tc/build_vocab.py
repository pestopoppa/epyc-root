import hashlib,json,pathlib,sys
sys.path.insert(0,'/mnt/raid0/llm/llama.cpp/gguf-py')
from gguf import GGUFReader
files={'v3q8':(pathlib.Path('/mnt/raid0/llm/models/handy-parakeet-tdt-0.6b-v3-gguf/parakeet-tdt-0.6b-v3-Q8_0.gguf'),'5859f77944efcd8eafa23a6350731960b2b55b2203df51f319665c807d802cc7'),'v3f16':(pathlib.Path('/mnt/raid0/llm/models/parakeet-tdt-0.6b-v3-F16.gguf'),'d9ec7e2c39da7b4fec3e01e71e82c7f7bbe97741e08c0c054091bf3d520a41d3')};allv=[]
for key,(p,expected) in files.items():
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 if h.hexdigest()!=expected:raise ValueError('model drift '+key)
 r=GGUFReader(p,'r');pieces=r.fields['tokenizer.ggml.tokens'].contents();types=[int(x) for x in r.fields['tokenizer.ggml.token_type'].contents()];allv.append((pieces,types))
if allv[0]!=allv[1] or allv[0][0][0]!='<unk>':raise ValueError('vocabulary mismatch')
out={'model_sha256':{k:v[1] for k,v in files.items()},'pieces':allv[0][0],'types':allv[0][1],'unk_id':0};dest=pathlib.Path(__file__).resolve().parent/'vocab.json';dest.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n');print(hashlib.sha256(dest.read_bytes()).hexdigest(),len(out['pieces']))
