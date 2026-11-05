#!/usr/bin/env python3
"""Compose reviewed preload patch into a disabled GPU-witness successor."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
SOURCES=ROOT/'docs/reports/kv-cache/kpf18-g3-model-identity-20261104'
BASE=Path('/mnt/raid0/llm/tmp/kvu/g3-gpu-integrated-20261105')
RECEIPT=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-native-control-r15/out/PRELOAD-MODEL-IDENTITY.json')
PINS={'launch.sh':'9d96378ed0cbc1764001545e8bfb2e3c6aabd072c364392fd567f786030496d4',
      'driver.py':'36f6c4af601d97e8606a8f93ae269adc159e19fedba7d22b8b4a09e1057af77b',
      'PRELOAD-MODEL-IDENTITY.json':'4a44cf4a80377a9ea03b19ae8a0e73b0777a61ed9392025678b6a4f39db41052',
      'driver-preload.patch':'75e4650be3ddcff1a9dd36cd6b4b1be0e47d0918fd84ba337aed350d19416d12',
      'verify_receipt.py':'2f820a5a215a36aa822dee4fb43cec4eb8fddb57b94b2434a85dfa63857eb506',
      'preload_integration.py':'a7958fc86664381b287c589e14f21972473336cd3df58b4f3087e375e4a4b88d'}
def digest(raw): return hashlib.sha256(raw).hexdigest()
def pinned(path):
    if path.is_symlink() or not path.is_file(): raise ValueError('regular source required: '+str(path))
    raw=path.read_bytes()
    if digest(raw)!=PINS[path.name]: raise ValueError('source pin drift: '+str(path))
    return raw

def prepare(output):
    output=Path(output)
    if not output.is_absolute() or not output.is_relative_to('/mnt/raid0/llm/tmp/kvu') or output.exists():
        raise ValueError('new absolute scratch destination required')
    pinned(BASE/'launch.sh'); pinned(BASE/'candidate/driver.py'); pinned(RECEIPT)
    payload={n:pinned(SOURCES/n) for n in ('driver-preload.patch','verify_receipt.py','preload_integration.py')}
    subprocess.run(['bash',str(BASE/'launch.sh'),'custody-check'],check=True)
    shutil.copytree(BASE,output,symlinks=True)
    marker=output/'INCOMPLETE'; marker.write_text('incomplete; never dispatch\n')
    runtime=output/'candidate'
    patch=payload['driver-preload.patch'].split(b'--- a/SOURCES.sha256\n',1)[0]
    subprocess.run(['patch','--batch','--fuzz=0','-p1'],input=patch,cwd=runtime,check=True,capture_output=True)
    for n in ('verify_receipt.py','preload_integration.py'): (runtime/n).write_bytes(payload[n])
    driver=(runtime/'driver.py').read_text()
    if driver.count('gpu_witness.install(gate)')!=1 or 'gguf_identity import metadata' in driver:
        raise ValueError('preload and GPU integration did not compose')
    source_manifest=runtime/'SOURCES.sha256'
    names=sorted(str(p.relative_to(runtime)) for p in runtime.rglob('*') if p.is_file() and p!=source_manifest)
    source_manifest.write_text(''.join(f'{digest((runtime/n).read_bytes())}  {n}\n' for n in names))
    receipt=output/'PREPARATION.json'; data=json.loads(receipt.read_text())
    data['preload_integration']='source-bound historical receipt and stat checks; no fresh model digest'
    receipt.write_text(json.dumps(data,indent=2)+'\n')
    paths={str(output/Path(p).relative_to(BASE)) if Path(p).is_relative_to(BASE) else p for p in json.loads((output/'expected-paths.json').read_text())}
    paths.update(str(runtime/n) for n in ('verify_receipt.py','preload_integration.py'))
    paths.add(str(RECEIPT)); paths=sorted(paths)
    seals=''.join(f'{digest(Path(p).read_bytes())}  {p}\n' for p in paths)
    (output/'ALL-SOURCES.sha256').write_text(seals)
    (output/'expected-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
    names=['ALL-SOURCES.sha256','expected-paths.json','verify_manifest.py','rebind_manifest.py']
    bootstrap=''.join(f'{digest((output/n).read_bytes())}  {n}\n' for n in names)
    (output/'BOOTSTRAP.sha256').write_text(bootstrap)
    launch=output/'launch.sh'; entry=launch.read_text()
    entry,n=re.subn(r"(printf '%s  %s\\n' )[0-9a-f]{64}( \"\$D/BOOTSTRAP.sha256\")",lambda m:m[1]+digest(bootstrap.encode())+m[2],entry)
    if n!=1: raise ValueError('bootstrap pin missing')
    entry,n=re.subn(r'(verify_manifest.py.*\"\$D\" )[0-9a-f]{64}',lambda m:m[1]+digest(seals.encode()),entry)
    if n!=1: raise ValueError('inventory pin missing')
    launch.write_text(entry)
    sys.path.insert(0,str(output));from verify_manifest import verify
    verify(output/'ALL-SOURCES.sha256',paths,digest(seals.encode()))
    marker.unlink()
    return len(paths)

if __name__=='__main__': print('sealed entries:',prepare(sys.argv[1]))
