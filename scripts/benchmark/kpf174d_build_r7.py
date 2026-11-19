#!/usr/bin/env python3
"""Prepare the KPF-17.4d build with immutable, compatible UI assets before grant."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tarfile

ROOT = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-build-r7-20261119')
ROW = 'kvu-kpf174-custody-r7-20261119'
UI_SHA = '9f692b00f9e52b939852a3045752395f2b8f0495063a26e4641a1a189478ae40'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    base = Path(__file__).resolve().parents[1] / 'coordination/kvfork/kpf174d-build-r6/prepare.py'
    assert digest(base) == '5f472c268ed84b8b7715c1179ce899ca1e45cfa2c41c78d2f112c08a69f8da6a'
    assert digest(ROOT/'input/ui-assets.tar.gz') == UI_SHA
    spec = importlib.util.spec_from_file_location('r6_prepare', base)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.NEW, mod.ROW = ROOT, ROW
    mod.main()  # verifies sealed R5 recipe and all source bytes, then relocates it

    # Prepare assets once; grant-time builds neither fetch nor stage UI inputs.
    dist = ROOT/'runs/prepared/build/tools/ui/dist'
    dist.mkdir(parents=True)
    with tarfile.open(ROOT/'input/ui-assets.tar.gz') as archive:
        members = archive.getmembers()
        for member in members:
            target = dist/member.name
            assert target.resolve().is_relative_to(dist.resolve())
            assert member.isfile() or member.isdir(), member.name
        archive.extractall(dist, members=members, filter='data')
    files = sorted(p for p in dist.rglob('*') if p.is_file())
    names = {p.name for p in files}
    assert {'index.html', 'manifest.webmanifest', 'sw.js', 'build.json', 'version.json'} <= names
    for prefix, suffix in [('bundle', '.js'), ('bundle', '.css'), ('workbox', '.js')]:
        assert any(n.startswith(prefix) and n.endswith(suffix) for n in names)
    # Pinned CMake npm_build_should_skip accepts these prepared outputs only
    # when index.html is newer than its unchanged source inputs (no HF stamp).
    for p in files:
        os.utime(p, None)
    # fingerprint belongs to the sealed integrity module, loaded below.
    integ_spec = importlib.util.spec_from_file_location('integrity_r7', ROOT/'v3/integrity.py')
    integ = importlib.util.module_from_spec(integ_spec)
    integ_spec.loader.exec_module(integ)
    ui_pin = {str(p.relative_to(dist)): {'sha256': digest(p), 'stat': integ.fingerprint(p)} for p in files}
    prepared_path = ROOT/'input/PREPARED.json'
    prepared = json.loads(prepared_path.read_text())
    prepared['ui_sha256'] = UI_SHA
    prepared['ui_stat'] = ui_pin
    prepared_path.write_text(json.dumps(prepared, sort_keys=True)+'\n')

    integrity_path = ROOT/'v3/integrity.py'
    text = integrity_path.read_text()
    before = "    reference = cache(inputs/'reference-cache.txt')"
    after = f'''    if pin['ui_sha256'] != '{UI_SHA}': raise ValueError('UI archive identity mismatch')
    dist = root/'runs/prepared/build/tools/ui/dist'
    entries = {{str(p.relative_to(dist)):p for p in dist.rglob('*') if p.is_file() and '_gzip' not in p.relative_to(dist).parts}}
    if set(entries) != set(pin['ui_stat']): raise ValueError('UI inventory changed')
    for name, p in entries.items():
        if p.is_symlink() or fingerprint(p) != pin['ui_stat'][name]['stat']:
            raise ValueError('UI asset metadata changed: '+name)
    reference = cache(inputs/'reference-cache.txt')'''
    assert text.count(before) == 1
    text = text.replace(before, after)
    text = text.replace("'input_sha256':dict(HASHES)", "'ui_assets':{'archive_sha256':pin['ui_sha256'], 'files':pin['ui_stat']}, 'input_sha256':dict(HASHES)")
    integrity_path.write_text(text)

    host = ROOT/'v3/host-job.sh'
    text = host.read_text().replace('R=$(mktemp -d "$S/runs/build-XXXXXXXX")', 'R=$S/runs/prepared')
    marker = 'python3 "$S/v3/integrity.py" "$R/build/CMakeCache.txt"\ncheck\n'
    assert text.count(marker) == 1
    text = text.replace(marker, marker + 'python3 "$S/v3/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --target llama-ui-assets --parallel "$FILLER_THREADS" >"$R/ui-embed.log" 2>&1\ncheck\n')
    host.write_text(text)
    proof = ROOT/'v3/proof.py'
    text = proof.read_text().replace("run/'first-unit.log']", "run/'first-unit.log', run/'ui-embed.log', build/'tools/ui/ui.cpp', build/'tools/ui/ui.h']")
    proof.write_text(text)
    complete = ROOT/'v3/complete.py'
    text = complete.read_text().replace("r/'first-unit.log']", "r/'first-unit.log', r/'ui-embed.log', r/'build/tools/ui/ui.cpp', r/'build/tools/ui/ui.h']")
    complete.write_text(text)
    paths = sorted(p for p in (ROOT/'v3').iterdir() if p.is_file() and p.name not in ('launch.sh', 'runtime.sha256')) + [prepared_path]
    runtime = ROOT/'v3/runtime.sha256'
    old_pin = digest(runtime)
    runtime.write_text(''.join(digest(p)+'  '+str(p)+'\n' for p in paths))
    launch = ROOT/'v3/launch.sh'
    launch.write_text(launch.read_text().replace(old_pin, digest(runtime)))
    spec_path = ROOT/'spec.json'
    row = json.loads(spec_path.read_text())
    row['supersedes'] = 'kvu-kpf174-custody-r6-20261119'
    row['decision_rule'] += ' UI assets must match the prepared b10303 archive SHA-256 and inventory; smoke must also embed them with the pinned source helper.'
    row['notes'] = 'Exact prospective source and reference options unchanged. UI assets b10303 checksum-pinned and staged before publication; smoke compiles KV object and embeds compatible UI. No grant-time input download or copy. No inference or historical verdict.'
    spec_path.write_text(json.dumps(row, indent=2)+'\n')
    integ_spec.loader.exec_module(integ)
    integ.verify()
    print(json.dumps({str(p):digest(p) for p in [spec_path, launch, runtime, prepared_path]}, indent=2))


if __name__ == '__main__':
    main()
