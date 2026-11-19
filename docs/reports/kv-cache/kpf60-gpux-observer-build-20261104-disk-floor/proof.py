import hashlib,json,os
from pathlib import Path
D=Path(__file__).resolve().parent; B=D/'build/bin'; O=D/'out'; x=json.loads((D/'identity.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
exe=(B/'test-server-chunk-store').resolve(strict=True); linkage_exe=(B/'test-chunk-kv').resolve(strict=True)
libs=sorted({p.resolve(strict=True) for p in B.glob('*.so*') if p.name.startswith(('libggml','libllama'))})
assert any(p.name.startswith('libggml-base.') for p in libs) and any(p.name.startswith('libggml-cpu.') for p in libs) and any(p.name.startswith('libllama.') for p in libs)
files=[exe,linkage_exe,*libs,D/'identity.json',D/'build/CMakeCache.txt',*[O/n for n in ('configure.log','object.log','build.log','linkage.log','test.log')]]
r={'schema':'kpf60.selection-build.v1','status':'BUILT','source_commit':x['source_commit'],'diff_sha256':x['diff_sha256'],'files':{str(p):sha(p) for p in files},'scope':'linked build and model-free store test only; no counter, range-selection correctness, inference or crossover claim'}
p=O/'RESULT.json'; t=p.with_suffix('.tmp');t.write_text(json.dumps(r,sort_keys=True)+'\n');os.replace(t,p)
