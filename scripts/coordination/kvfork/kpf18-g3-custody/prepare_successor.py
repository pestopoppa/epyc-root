#!/usr/bin/env python3
"""Prepare a NEW custody-only successor; never invoke the retained runtime."""
import hashlib
import json
from pathlib import Path
import re
import sys

from rebind_manifest import LINE, read_regular, rebind
from verify_manifest import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(manifest, mapping_file, launcher, output, manifest_sha, launcher_sha):
    manifest = Path(manifest)
    launcher = Path(launcher)
    output = Path(output)
    raw = read_regular(manifest)
    original_launcher = read_regular(launcher)
    if sha(raw) != manifest_sha or sha(original_launcher) != launcher_sha:
        raise ValueError('predecessor pin mismatch')
    # Refuse an input which is not the known deliberately disabled draft.
    if b"exit 78\nunset PYTHONHOME PYTHONPATH" not in original_launcher:
        raise ValueError('disabled predecessor barrier missing')
    mapping_raw = read_regular(mapping_file)
    mapping = json.loads(mapping_raw)
    # Resolve no aliases in caller-supplied paths; the custody tools reject them.
    if not output.is_absolute():
        raise ValueError('output must be absolute')
    output.mkdir(exist_ok=False)
    (output / 'INCOMPLETE').write_text('Preparation incomplete; never execute retained launcher.\n')
    (output / 'predecessor-launch.sh.disabled').write_bytes(original_launcher)
    (output / 'predecessor-NATIVE-SOURCES.sha256').write_bytes(raw)
    (output / 'rebinding.json').write_bytes(mapping_raw)
    rebound = output / 'NATIVE-SOURCES.sha256'
    rebind(manifest, mapping, rebound, manifest_sha)
    paths = []
    for line in raw.decode().splitlines():
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError('malformed manifest')
        old = match.group(2)
        paths.append(mapping.get(old, old))
    count = verify(rebound, paths, sha(read_regular(rebound)))
    (output / 'expected-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
    for name in ('rebind_manifest.py', 'verify_manifest.py'):
        (output / name).write_bytes(read_regular(Path(__file__).absolute().with_name(name)))
    entry = '''import json, sys\nfrom pathlib import Path\nfrom verify_manifest import verify\np = Path(__file__).parent\ncount = verify(p / "NATIVE-SOURCES.sha256", json.loads((p / "expected-paths.json").read_text()), sys.argv[1])\nprint(f"PASS: {count} native custody entries; runtime remains disabled")\n'''
    (output / 'custody_entry.py').write_text(entry)
    receipt = dict(status='CUSTODY_ONLY_NOT_READY', native_entries=count,
                   predecessor_manifest_sha256=manifest_sha,
                   predecessor_launcher_sha256=launcher_sha,
                   runtime_dispatch=False,
                   outstanding=['current lock semantics', 'independent validation manifests',
                                'live cancellation', 'whole-attempt supervision',
                                '150+64 GiB disk admission', 'GPU qualification'])
    (output / 'PREPARATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
    names = sorted(p.name for p in output.iterdir() if p.name != 'INCOMPLETE')
    seals = ''.join(f'{sha(read_regular(output / name))}  {name}\n' for name in names)
    (output / 'SUCCESSOR-SOURCES.sha256').write_text(seals)
    script = '''#!/bin/bash\nset -euo pipefail\nD=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)\n[[ ! -e "$D/INCOMPLETE" ]] || exit 78\nprintf '%s  %s\\n' SEAL "$D/SUCCESSOR-SOURCES.sha256" | sha256sum --status -c -\n(cd "$D" && sha256sum --quiet -c SUCCESSOR-SOURCES.sha256)\n# Isolated mode imports only the sealed sibling tools.\npython3 -B -I -c 'import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=[sys.argv[1]+"/custody_entry.py",sys.argv[2]];runpy.run_path(sys.argv[0],run_name="__main__")' "$D" NATIVE\ncase "${1:-official}" in\n custody-check) [[ $# == 1 ]] || exit 64;;\n *) echo 'REFUSED: custody-only successor; runtime unqualified, retained launcher disabled' >&2; exit 78;;\nesac\n'''.replace('SEAL', sha(seals.encode())).replace('NATIVE', sha(read_regular(rebound)))
    (output / 'launch.sh').write_text(script)
    (output / 'INCOMPLETE').unlink()
    return receipt


if __name__ == '__main__':
    if len(sys.argv) != 7:
        raise SystemExit('usage: prepare_successor.py manifest mapping.json disabled-launcher NEW-output manifest-sha256 launcher-sha256')
    try:
        print(json.dumps(prepare(*sys.argv[1:]), indent=2))
    except (OSError, ValueError, TypeError) as exc:
        raise SystemExit(f'REFUSED: {exc}')
