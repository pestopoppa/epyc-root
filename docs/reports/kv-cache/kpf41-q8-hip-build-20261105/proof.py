import hashlib,json,pathlib,subprocess
D=pathlib.Path(__file__).resolve().parent
b=D/'build/bin'; files=[b/'test-kv-rows-vec-direct']+sorted(p for p in b.glob('libggml*.so*') if p.is_file())+sorted(p for p in b.glob('libllama*.so*') if p.is_file())
assert files[0].is_file() and any('libggml-hip.so' in p.name for p in files) and any('libggml-base.so' in p.name for p in files) and any('libggml-cpu.so' in p.name for p in files)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(4*1024*1024),b''): h.update(c)
 return h.hexdigest()
r={'status':'BUILD_PASS','source_commit':'15caecbbf4cb27452dbd87fa1a68a0e75098388e','files':{str(p):sha(p) for p in files},'compiler':subprocess.check_output(['/opt/rocm/bin/hipcc','--version'],text=True),'scope':'source-bound HIP build and linkage only; no GPU execution or parity'}
(D/'out/RESULT.json').write_text(json.dumps(r,indent=2)+'\n')
