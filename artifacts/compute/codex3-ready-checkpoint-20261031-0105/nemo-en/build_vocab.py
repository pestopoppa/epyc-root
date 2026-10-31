import hashlib,json,pathlib,sys
sys.path.insert(0,'/mnt/raid0/llm/llama.cpp/gguf-py')
from gguf import GGUFReader
D=pathlib.Path(__file__).resolve().parent
models={'nemo':pathlib.Path('/mnt/raid0/llm/models/cs8-handy-computer--nemotron-speech-streaming-en-0.6b-gguf/nemotron-speech-streaming-en-0.6b-Q8_0.gguf'),}
for k,p in models.items():
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 r=GGUFReader(p,'r');pieces=r.fields['tokenizer.ggml.tokens'].contents();types=[int(x) for x in r.fields['tokenizer.ggml.token_type'].contents()]; u=[i for i,x in enumerate(pieces) if x=='<unk>'];assert len(u)==1
 out={'model_sha256':h.hexdigest(),'pieces':pieces,'types':types,'unk_id':u[0]}; dest=D/'vocab.json';dest.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n');print(k,h.hexdigest(),len(pieces),u[0],hashlib.sha256(dest.read_bytes()).hexdigest(),flush=True)
