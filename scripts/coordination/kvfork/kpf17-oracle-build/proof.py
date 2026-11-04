#!/usr/bin/env python3
"""Build completion receipt; no inference or historical equivalence claim."""
import hashlib,json,os,pathlib,subprocess
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104'); B=D/'build/bin'; O=D/'out'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
subprocess.run(['python3',str(D/'check.py')],check=True)
exe=(B/'test-save-load-state').resolve(strict=True)
libs=sorted({p.resolve(strict=True) for p in B.glob('*.so*') if p.name.startswith(('libggml','libllama'))})
assert any(p.name.startswith('libggml-base.') for p in libs) and any(p.name.startswith('libggml-cpu.') for p in libs) and any(p.name.startswith('libllama.') for p in libs)
assert all(p.parent==B.resolve() for p in libs)
files=[exe,*libs,D/'build/CMakeCache.txt',O/'configure.log',O/'object.log',O/'build.log',O/'linkage.log',D/'verify_ggml_linkage.sh']
r={'schema':'kpf17.oracle-build.v1','status':'BUILT','source_commit':'8952a0f693fb923918157eb25117641b74766230','patched_test_sha256':'b2f7085c3b772b58d6e9eb5ec33f217f22e9e1987bb8f51f040094eb586ef2ab','oracle_header_sha256':'90787c4a526d2dedd3d3d11bf944ea81eeb1c2efd77e5e6862e8e69a57b26249','patch_sha256':'b7eb4cabacadb7378bd1bcc8af4532f71ce39c751b5d0f11ce4abe96b010eac6','compiler_sha256':{str(p):sha(p) for p in (pathlib.Path('/usr/bin/cc'),pathlib.Path('/usr/bin/c++'))},'files':{str(p):sha(p) for p in files},'scope':'prospective test-only build; no inference, non-vacuity or kernel verdict'}
p=O/'RESULT.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(r,sort_keys=True)+'\n');os.replace(t,p)
