"""Normal-owner prelaunch; receipt binds sources and immutable served pins."""
import hashlib,json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
B=Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c')
model=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
template=Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
receipt=json.loads(Path(sys.argv[1]).read_text())
for key,path in [('source',D/'direct_diagnostic.py'),('profile',D/'DIAGNOSTIC-PROFILE.md'),('fixture',D/'fixtures.json'),('manifest',D/'source-manifest.sha256')]:
 if receipt.get(key+'_sha256') != sha(path):raise SystemExit('enrollment receipt mismatch: '+key)
if receipt.get('profile')!='ct21-direct-exploratory-v1' or receipt.get('approved') is not True:raise SystemExit('enrollment not approved')
pins={B/'bin/llama-server':'49b124aa59a6ebfd3dfa993ee284ac5727d38f033a187fa086748204dbd5fad5',B/'bin/libggml-hip.so.0.16.0':'6aabef001bf1090604e4c0fe048284953e98554f08b3d8460761c4f560b1e5cd',model:'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348',template:'1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551'}
for path,digest in pins.items():
 if sha(path)!=digest:raise SystemExit('pin mismatch: '+str(path))
version=subprocess.check_output([str(B/'bin/llama-server'),'--version'],text=True).strip()
if '10345' not in version or 'dd3d9721c' not in version:raise SystemExit('server version mismatch')
provenance=(B/'PROVENANCE.md').read_text(); commit='dd3d9721ca37321ad9159520bbd9616e3d0d6228'
if commit not in provenance:raise SystemExit('build provenance mismatch')
output={'source_commit':commit,'binary_version':version,'template_sha256':pins[template],'model_path':str(model),'served_sha256':{str(k):v for k,v in pins.items()}}
(D/'runtime-identity.json').write_text(json.dumps(output,indent=2)+'\n')
