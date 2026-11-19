#!/usr/bin/env python3
"""Relocate the reviewed R5 recipe; verify source bytes before publication."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

OLD = Path('/mnt/raid0/llm/tmp/kvu/kpf174-custody-r5-20261104')
NEW = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-build-r6-20261119')
OLD_SOURCE = '/mnt/raid0/llm/worktrees/kpf174-custody-r5-source-20261104'
ROW = 'kvu-kpf174-custody-r6-20261119'

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def main():
    assert not (NEW/'spec.json').exists(), 'refuse to overwrite an existing publication'
    # Validate retained recipe against its original sealed runtime list.
    assert digest(OLD/'v3/runtime.sha256') == '4162b7a1e3241ec90b7c884a2d515f8c593c8d2b4a42fa6de0f9bf47505f2e5c'
    subprocess.run(['sha256sum', '-c', str(OLD/'v3/runtime.sha256')], check=True)
    (NEW/'v3').mkdir(parents=True, exist_ok=True)
    (NEW/'input').mkdir(exist_ok=True)
    for p in (OLD/'v3').iterdir():
        if p.suffix not in ('.py', '.sh') and p.name != 'linkage.sha256': continue
        text = p.read_text().replace(str(OLD), str(NEW)).replace(OLD_SOURCE, str(NEW/'source')).replace('kvu-kpf174-custody-r5-20261104', ROW).replace('/usr/bin/chroot', '/usr/sbin/chroot')
        (NEW/'v3'/p.name).write_text(text)
    specmod = importlib.util.spec_from_file_location('integrity', NEW/'v3/integrity.py')
    mod = importlib.util.module_from_spec(specmod)
    specmod.loader.exec_module(mod)
    for name, expected in mod.HASHES.items():
        assert digest(OLD/'input'/name) == expected, name
        # Reuse immutable inputs by reference; never duplicate source archives.
        (NEW/'input'/name).symlink_to(OLD/'input'/name)
    source = NEW/'source'
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD','HEAD^'], text=True).splitlines() == ['6ec877068936588b6d63dbba5842bbd540b92031','84d0a31603d495377dee24e1159bbbf02f1e2f21']
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'], text=True).strip()
    subprocess.run(['sha256sum','--check','--quiet',str(NEW/'input/source-files.sha256')],cwd=source,check=True)
    files = sorted((p for p in source.rglob('*') if p.is_file() and p.name != '.git'), key=lambda p:str(p.relative_to(source)).encode())
    assert ''.join('./'+str(p.relative_to(source))+'\n' for p in files) == (NEW/'input/source-file-list.txt').read_text()
    assert not any(p.is_symlink() for p in source.rglob('*'))
    prepared = {'input_sha256':mod.HASHES,'source_stat':{str(p.relative_to(source)):mod.fingerprint(p) for p in files},'input_stat':{name:mod.fingerprint(NEW/'input'/name) for name in mod.HASHES}}
    (NEW/'input/PREPARED.json').write_text(json.dumps(prepared, sort_keys=True)+'\n')
    mod.verify()
    paths = sorted(p for p in (NEW/'v3').iterdir() if p.is_file() and p.name not in ('launch.sh','runtime.sha256')) + [NEW/'input/PREPARED.json']
    (NEW/'v3/runtime.sha256').write_text(''.join(digest(p)+'  '+str(p)+'\n' for p in paths))
    launch = NEW/'v3/launch.sh'
    launch.write_text(launch.read_text().replace('4162b7a1e3241ec90b7c884a2d515f8c593c8d2b4a42fa6de0f9bf47505f2e5c',digest(NEW/'v3/runtime.sha256')))
    spec = json.loads((OLD/'spec.json').read_text().replace(str(OLD),str(NEW)).replace('kvu-kpf174-custody-r5-20261104',ROW))
    spec.update(owner='handoff-heterogeneous-slot-fabric-residency',verdict_by='agent',supersedes='kvu-kpf174-custody-r5-20261104',notes='Fresh full HIP rebuild of exact source 6ec877068 and parent 84d0a316 after R5 binaries were reclaimed. Reviewed R5 recipe relocated; source and input bytes verified before publication, metadata inventoried anew. No smoke or full result inherited. Keep full build for subsequent receipt-pinned prospective GPU successor, excluding exposed g0-S2-B and g1-S2-B. Historical verdicts stand.')
    (NEW/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    pins = {str(p):digest(p) for p in [NEW/'spec.json',NEW/'v3/launch.sh',NEW/'v3/runtime.sha256',NEW/'v3/verify_ggml_linkage.sh',NEW/'input/PREPARED.json']}
    print(json.dumps(pins,indent=2))

if __name__ == '__main__': main()
