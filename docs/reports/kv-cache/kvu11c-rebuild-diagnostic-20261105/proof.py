#!/usr/bin/env python3
import hashlib,json,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvfork/kvu11c-rebuild-diagnostic-20261105'); B=D/'build'; O=D/'out'
cache=(B/'CMakeCache.txt').read_text()
assert 'GGML_HIP:BOOL=ON' in cache and 'AMDGPU_TARGETS:UNINITIALIZED=gfx90a' in cache
paths=[B/'tts-server']+[B/n for n in ('libggml.so','libggml-base.so','libggml-cpu.so','libggml-hip.so')]
files={}
for p in paths:
 q=p.resolve(); assert q.is_file() and q.is_relative_to(B.resolve()) and q.stat().st_size>0
 files[str(q)]=hashlib.sha256(q.read_bytes()).hexdigest()
reference=json.loads((D/'reference.json').read_text())
actual={Path(p).name:d for p,d in files.items()}
r={'prior_build_match':actual==reference,'prior_build_reference':reference,'prior_build_actual':actual,'schema':'kvu11c.hip-build.v1','status':'BUILT','qwentts_commit':'aca703283192f892f1e85636fbc48832c4d5560a','ggml_commit':'b86f660238dcc1a83b7cbf5a72d355a965de9245','files':files,'scope':'HIP-enabled build and CLI only; no GPU execution'}
tmp=O/'RESULT.json.tmp'
with tmp.open('x') as f: json.dump(r,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
os.replace(tmp,O/'RESULT.json')
