"""Owner-only, after build terminal success; pin inputs and verify before publication."""
import hashlib,json,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent; B=D.parent; root=Path('/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-root-code')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(D/'source-pins.json') == '26d72341d3a6d73458350a8559b340b357c6a469e60ab02deb3c3165c65b303f'
source_pins=json.loads((D/'source-pins.json').read_text())['files']
for name,want in source_pins.items(): assert sha(D/name)==want,name
t=json.loads((B/'build-terminal.json').read_text()); assert t['state']=='success',t
receipt=B/'build-receipt.json'; b=json.loads(receipt.read_text()); assert b['schema']=='kvu19a2.successor-build.v1' and b['source_commit']=='a0d0ae238e714aaab04e973ef4b5a4b7c9917744' and len(b['artifacts'])==9
for path,want in b['artifacts'].items(): assert sha(path)==want,path
exe=B/'build/harness/fa_harness'; assert str(exe) in b['artifacts']
harness=exe.parent/'harness-receipt.json'; h={'schema':'kvu19a2.harness-build.v1','scope':'owner finalization attestation from new successor build receipt; not a historical compiler receipt','executable_sha256':sha(exe),'pair_build_receipt_sha256':sha(receipt),'source_sha256':b['harness_source_sha256']}; harness.write_text(json.dumps(h,indent=2)+'\n')
old=json.loads(Path('/mnt/raid0/llm/tmp/vb-kvu19a2-wire-20261104/spec.ready.json').read_text())
files={}
for path,want in old['pins'].items():
 marker='/mnt/raid0/llm/tmp/vb-kvu19a2-wire-20261104/root-code/'
 if path.startswith(marker):
  p=root/path[len(marker):]; assert sha(p)==want,str(p); files[str(p)]=want
assert len(files)>250
for p in D.iterdir():
 if p.is_file() and p.name != 'pins.json': files[str(p)]=sha(p)
files.update(b['artifacts']); files[str(receipt)]=sha(receipt); files[str(harness)]=sha(harness)
archive=Path('/mnt/raid0/llm/tmp/kvu/kvu19a2-source-pair-20261102/source.tar'); assert sha(archive)==b['source_sha256']; files[str(archive)]=sha(archive)
env={'KVU19A2_BUILD_RECEIPT_SHA256':sha(receipt),'KVU19A2_EXE_SHA256':sha(exe),'KVU19A2_HARNESS_RECEIPT_SHA256':sha(harness)}
(D/'pins.json').write_text(json.dumps({'schema':'kvu19a2.successor-pins.v1','files':files,'env':env},indent=2)+'\n')
subprocess.run([sys.executable,str(D/'preflight.py')],check=True)
print('READY_FOR_PUBLISH', D/'spec.json')
