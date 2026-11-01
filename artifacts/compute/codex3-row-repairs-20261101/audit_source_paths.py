from pathlib import Path
import json
M=Path('/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/source.sha256')
missing=[];total=0
for line in M.read_text().splitlines():
 digest,name=line.split('  ',1)
 if name.endswith('.gguf'):continue
 if name=='/home/node/.local/share/uv/python/cpython-3.11.17-linux-x86_64-gnu/bin/python3.11':name='/mnt/micron/codex3-evl34-deepdive-r9-20261030/bin/python3.11'
 total+=1
 if not Path(name).is_file():missing.append({'path':name,'sha256':digest})
print(json.dumps({'total':total,'missing':missing},indent=2))
