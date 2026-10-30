"""Retain the single predeclared control source row before any exposure."""
import hashlib,json,os
from pathlib import Path
import pyarrow as pa
base=Path(__file__).parent;manifest=json.loads((base/'FROZEN-PROMPT-MANIFEST.json').read_text());source=Path('/mnt/raid0/llm/hf-home/datasets/hotpotqa___hotpot_qa/distractor/0.0.0/1908d6afbbead072334abe2965f91bd2709910ab/hotpot_qa-validation.arrow')
h=hashlib.sha256()
with source.open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
if h.hexdigest()!=manifest['source_sha256']:raise ValueError('source drift')
with pa.memory_map(str(source),'r') as f:table=pa.ipc.open_stream(f).read_all();row=table.slice(manifest['control']['source_index'],1).to_pylist()[0]
data=json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
if hashlib.sha256(data).hexdigest()!=manifest['control']['row_sha256']:raise ValueError('row drift')
fd=os.open(base/'CONTROL-PRIVATE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
print('verified control row retained; no exposure')
