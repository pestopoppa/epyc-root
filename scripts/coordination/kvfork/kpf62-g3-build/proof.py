import hashlib,json,os,pathlib,subprocess
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104'); B=D/'build/bin'; O=D/'out'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(D/'check.py')],check=True)
exe=(B/'test-chunk-kv-g3').resolve(strict=True); budget=(B/'test-kpf62-outcome-budget').resolve(strict=True)
libs=sorted({p.resolve(strict=True) for p in B.glob('*.so*') if p.name.startswith(('libggml','libllama'))})
assert any(p.name.startswith('libggml-base.') for p in libs) and any(p.name.startswith('libggml-cpu.') for p in libs) and any(p.name.startswith('libllama.') for p in libs) and all(p.parent==B.resolve() for p in libs)
files=[exe,budget,*libs,D/'source.json',D/'build/CMakeCache.txt',*[O/p for p in ('configure.log','object.log','build.log','linkage.log','budget.log','pytest.log')]]
r={'schema':'kpf62.g3-build.v1','status':'BUILT','source_commit':'3ec14227a0e293bfc223c9026ed761ea3bdda9bb','files':{str(p):sha(p) for p in files},'scope':'model-free linked build and unit checks; no inference or G3 scoring'}
p=O/'RESULT.json'; t=p.with_suffix('.tmp'); t.write_text(json.dumps(r,sort_keys=True)+'\n'); os.replace(t,p)
