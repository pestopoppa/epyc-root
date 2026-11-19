import hashlib,json,os,pathlib,subprocess
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf50-hip-build-20261104');B=D/'build/bin';O=D/'out'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(D/'check.py')],check=True)
exe=(B/'llama-server').resolve(strict=True)
libs=sorted({p.resolve(strict=True) for p in B.glob('*.so*') if p.name.startswith(('libggml','libllama'))})
for prefix in ('libggml-hip.','libggml-cpu.','libggml-base.','libllama-server-impl.','libllama.'):
 assert any(p.name.startswith(prefix) for p in libs),prefix
assert all(p.parent==B.resolve() for p in libs)
server=next(p for p in libs if p.name.startswith('libllama-server-impl.')).read_bytes(); llama=next(p for p in libs if p.name.startswith('libllama.')).read_bytes()
for marker in (b'KPF50_STEP_BEGIN',b'KPF50_ITER_BEGIN',b'KPF50_ITER_END',b'KPF50_DRAFT_BEGIN',b'KPF50_DRAFT_END',b'KPF50_INPUT'):assert marker in server,marker
for marker in (b'KPF50_TRUNK_MASK',b'LLAMA_KPF50_MASK_SHARED_TRUNK'):assert marker in llama,marker
files=[exe,*libs,D/'build/CMakeCache.txt',*[O/x for x in ('configure.log','object.log','build.log','linkage.log')],D/'verify_ggml_linkage.sh']
r={'schema':'kpf50.hip-build.v1','status':'BUILT','source_commit':'1e8a6d5da9836a27e8f1d2010a02e6cebd95abdc','files':{str(p):sha(p) for p in files},'scope':'new prospective HIP build only; no GPU inference or profiling'}
p=O/'RESULT.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(r,sort_keys=True)+'\n');os.replace(t,p)
