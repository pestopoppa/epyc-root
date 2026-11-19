#!/usr/bin/env python3
"""Prepare a disabled G3 successor with the reviewed GPU sampler installed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
PREP = ROOT / 'scripts/coordination/kvfork/kpf18-g3-successor/prepare.py'
GPU = ROOT / 'scripts/coordination/kvfork/kpf18-g3-gpu'
PINS = {'prepare.py': '0de0ea8eac6e4625a8d1d049012402be4deefe38075e6843dab3d2e80df218f7',
        'gpu_witness.py': '27665b3a961ffd793c2c46ded39f2e90711e8ec6f47594d27140d73e45c71ed3',
        'sysfs_residency.py': 'dd36ae78e28f4fd048ed6411a038386410cfd6853b5c7ffc9194308b412e68a9'}
def digest(raw): return hashlib.sha256(raw).hexdigest()
def pinned(path):
    if path.is_symlink() or not path.is_file(): raise ValueError('source is not regular')
    raw=path.read_bytes()
    if digest(raw)!=PINS[path.name]: raise ValueError('source pin mismatch: '+str(path))
    return raw

def prepare(output):
    output=Path(output)
    if not output.is_absolute() or not output.is_relative_to('/mnt/raid0/llm/tmp/kvu') or output.exists():
        raise ValueError('new absolute destination under /mnt/raid0/llm/tmp/kvu required')
    sources={name:pinned(GPU/name) for name in ('gpu_witness.py','sysfs_residency.py')}
    predecessor=Path('/mnt/raid0/llm/tmp/kvfork/g3-rowflow-prep-20261104')
    if digest((predecessor/'launch.sh').read_bytes()) != 'c5301784c9430555828902fc7939ae896a1417e9d8b7df6a3212270cd53bf5c8':
        raise ValueError('predecessor entry changed')
    subprocess.run(['bash',str(predecessor/'launch.sh'),'custody-check'],check=True)
    shutil.copytree(predecessor,output,symlinks=True)
    sys.path.insert(0,str(output))
    from verify_manifest import verify
    marker=output/'INCOMPLETE';marker.write_text('GPU integration incomplete; never dispatch.\n')
    runtime=output/'candidate'; driver=runtime/'driver.py'
    text=driver.read_text()
    needle="    return gate.main()\n"
    if text.count(needle)!=1: raise ValueError('unexpected driver entry')
    text=text.replace(needle,"    import gpu_witness\n    gpu_witness.install(gate)\n"+needle)
    driver.write_text(text)
    for name, content in sources.items(): (runtime/name).write_bytes(content)
    source_manifest=runtime/'SOURCES.sha256'
    names=sorted(str(p.relative_to(runtime)) for p in runtime.rglob('*') if p.is_file() and p!=source_manifest)
    source_manifest.write_text(''.join(f'{digest((runtime/n).read_bytes())}  {n}\n' for n in names))
    receipt_path=output/'PREPARATION.json'; receipt=json.loads(receipt_path.read_text())
    receipt['gpu_integration']='reviewed dynamic sampler installed before gate.main; no live qualification'
    receipt['gpu_source_pins']=sources.keys() and {name:digest(raw) for name,raw in sources.items()}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    paths={str(output/Path(p).relative_to(predecessor)) if Path(p).is_relative_to(predecessor) else p for p in json.loads((output/'expected-paths.json').read_text())}
    paths.update(str(runtime/name) for name in sources)
    paths=sorted(paths)
    seals=''.join(f'{digest(Path(p).read_bytes())}  {p}\n' for p in paths)
    (output/'ALL-SOURCES.sha256').write_text(seals)
    (output/'expected-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
    bootstrap_names=['ALL-SOURCES.sha256','expected-paths.json','verify_manifest.py','rebind_manifest.py']
    bootstrap=''.join(f'{digest((output/n).read_bytes())}  {n}\n' for n in bootstrap_names)
    (output/'BOOTSTRAP.sha256').write_text(bootstrap)
    launch=output/'launch.sh'; entry=launch.read_text()
    entry,n=re.subn(r"(printf '%s  %s\\n' )[0-9a-f]{64}( \"\$D/BOOTSTRAP.sha256\")",lambda m:m[1]+digest(bootstrap.encode())+m[2],entry)
    if n!=1: raise ValueError('unexpected bootstrap launch pin')
    entry,n=re.subn(r'(verify_manifest.py.*\"\$D\" )[0-9a-f]{64}',lambda m:m[1]+digest(seals.encode()),entry)
    if n!=1: raise ValueError('unexpected inventory launch pin')
    launch.write_text(entry)
    verify(output/'ALL-SOURCES.sha256',paths,digest(seals.encode()))
    marker.unlink()
    return len(paths)

if __name__=='__main__': print('sealed entries:',prepare(sys.argv[1]))
