"""Before exposure, bind frozen source row hashes to exact projected prompt bytes."""
import hashlib,json,os
from pathlib import Path
import pyarrow as pa
from prompt_projection import project
base=Path(__file__).parent
pre=base/'PREDECLARATION-FROZEN.json'
if hashlib.sha256(pre.read_bytes()).hexdigest()!='08739d34cae4cfa58b0ede50c44bf24c1241953ed6f66fef7ec79627b0cb7485':raise ValueError('predecl mismatch')
p=json.loads(pre.read_bytes());source=Path('/mnt/raid0/llm/hf-home/datasets/hotpotqa___hotpot_qa/distractor/0.0.0/1908d6afbbead072334abe2965f91bd2709910ab/hotpot_qa-validation.arrow')
before=source.stat();h=hashlib.sha256()
with source.open('rb') as f:
 for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
if h.hexdigest()!=p['source_sha256']:raise ValueError('source hash mismatch')
with pa.memory_map(str(source),'r') as f:rows=pa.ipc.open_stream(f).read_all().to_pylist()
after=source.stat()
if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('source changed')
result=[]
for entry in p['pilot']+[p['independent_smoke_control']]:
 row=rows[entry['source_index']];raw=json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if row['id']!=entry['id'] or hashlib.sha256(raw).hexdigest()!=entry['row_sha256']:raise ValueError('row mismatch')
 prompt=project(row).encode();result.append({'id':entry['id'],'source_index':entry['source_index'],'row_sha256':entry['row_sha256'],'prompt_sha256':hashlib.sha256(prompt).hexdigest(),'prompt_bytes':len(prompt)})
out=base/'FROZEN-PROMPT-MANIFEST.json';data=json.dumps({'declaration_sha256':hashlib.sha256(pre.read_bytes()).hexdigest(),'source_sha256':h.hexdigest(),'pilot':result[:10],'control':result[10]},sort_keys=True,indent=2).encode()+b'\n'
with out.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
print('eleven verified source rows and exact prompt hashes',hashlib.sha256(data).hexdigest())
