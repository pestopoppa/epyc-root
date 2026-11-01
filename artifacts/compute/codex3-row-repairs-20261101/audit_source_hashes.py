from pathlib import Path
import json,hashlib
M=Path('/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/source.sha256')
missing=[];mismatch=[];total=0
for line in M.read_text().splitlines():
 digest,name=line.split('  ',1)
 if name.endswith('.gguf'):continue
 if name=='/home/node/.local/share/uv/python/cpython-3.11.17-linux-x86_64-gnu/bin/python3.11':name='/mnt/micron/codex3-evl34-deepdive-r9-20261030/bin/python3.11'
 if name=='/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/requirements-freeze.txt':name='/mnt/raid0/llm/tmp/codex3-row-repairs-20261101/reconstructed-freeze.txt'
 total+=1;p=Path(name);h=hashlib.sha256()
 try:
  with p.open('rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 except OSError as e:missing.append({'path':name,'error':str(e)});continue
 if h.hexdigest()!=digest:mismatch.append({'path':name,'expected':digest,'actual':h.hexdigest()})
print(json.dumps({'total':total,'missing':missing,'mismatch':mismatch},indent=2))
