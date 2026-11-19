#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
packet=Path(sys.argv[1]);port=int(sys.argv[2]); root=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-api-budget600-20261104/long-scope-path.txt').read_text().strip(); mpath=packet/'manifest.json';m=json.loads(mpath.read_text())
def update(ref,change):
 p=packet/ref['path']; obj=json.loads(p.read_text()); change(obj); raw=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();p.write_bytes(raw);ref['sha256']=hashlib.sha256(raw).hexdigest()
update(m['tasks'][0]['request'],lambda x:x.update(scope_root=root))
update(m['api_request'],lambda x:x.update(task_root=root,server_urls={'frontdoor':f'http://127.0.0.1:{port}'},timeout_s=1800))
m['arm_timeout_s']=1800
m['provenance']['interpretation']='Prospective transformed HS-19a two-scout long-root diagnostic with explicit private 600s per-call and 1800s route policy; not a real historical fan-out or a gate.'
mpath.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
