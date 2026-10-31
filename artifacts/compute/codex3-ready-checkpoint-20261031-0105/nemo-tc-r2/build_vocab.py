import hashlib,json,pathlib,sys
sys.path.insert(0,'/mnt/raid0/llm/llama.cpp/gguf-py')
from gguf import GGUFReader
p=pathlib.Path('/mnt/raid0/llm/models/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf');h=hashlib.sha256()
with p.open('rb') as f:
 for b in iter(lambda:f.read(4194304),b''):h.update(b)
if h.hexdigest()!='b94545b313b3223fda7b2857a52681da813935c2127643d1e9ff0c23d988089c':raise ValueError('model drift')
r=GGUFReader(p,'r');pieces=r.fields['tokenizer.ggml.tokens'].contents();types=[int(x) for x in r.fields['tokenizer.ggml.token_type'].contents()];assert len(pieces)==len(types) and pieces[0]=='<unk>'
out={'model_sha256':h.hexdigest(),'pieces':pieces,'types':types,'unk_id':0};dest=pathlib.Path(__file__).resolve().parent/'vocab.json';dest.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n');print(hashlib.sha256(dest.read_bytes()).hexdigest(),len(pieces))
