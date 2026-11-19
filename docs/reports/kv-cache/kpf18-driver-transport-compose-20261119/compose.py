"""Compose a disabled full-driver overlay without copying its source tree."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/kvu')
BASE = SCRATCH / 'g3-preload-integrated-20261105'
TRANSPORT = SCRATCH / 'transport-successor-20261119'
PINS = {
    BASE / 'ALL-SOURCES.sha256': '5fe60fc56a6ad7c387763e17715b4a467edf00078a533ab9b4151bd30e74e85a',
    BASE / 'candidate/driver.py': 'de71697af8c2b529c4ca78fccf76a2b75e29d1f8a72206ca1a85da3a4e85df21',
    TRANSPORT / 'manifest.json': '496d691bc1f7eb7429146e8fee5b22b38948ed814292c4bcd55549d431185208',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check(path, expected):
    # Historical inventories include intentional library symlinks. Their bytes
    # are pinned; the new overlay's own generated modules must be regular.
    if not path.is_file() or digest(path) != expected:
        raise ValueError('source identity mismatch: ' + str(path))


def install(destination):
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists()
            or destination.is_symlink() or not destination.resolve().is_relative_to(SCRATCH)):
        raise ValueError('new scratch destination required')
    for path, expected in PINS.items():
        check(path, expected)
    sources = dict(PINS)
    for line in (BASE / 'ALL-SOURCES.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = Path(name)
        if not path.is_absolute():
            raise ValueError('absolute inventory path required')
        # This qualification executes Python imports only. The historical
        # inventory also pins OS utilities/native binaries; it is retained as
        # provenance, not represented as current native execution custody.
        if path.suffix == '.py':
            check(path, expected)
            sources[path] = expected
    for name, expected in json.loads((TRANSPORT / 'manifest.json').read_text())['sources'].items():
        path = Path(name)
        check(path, expected)
        sources[path] = expected
    destination.mkdir()
    marker = destination / 'INCOMPLETE'
    marker.touch()
    # Both direct entries refuse, even if installation is interrupted.
    (destination / 'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexit 78\n')
    driver = (BASE / 'candidate/driver.py').read_text()
    old = 'BASE=Path(__file__).resolve().parent'
    if driver.count(old) != 1 or driver.count('OUT=guard.attempt_root()') != 1:
        raise ValueError('driver shape changed')
    prefix = "if __name__ == '__main__': raise SystemExit(78)\nfrom composition import bind, output_root\nbind()\n"
    driver = prefix + driver.replace(old, 'BASE=Path(' + repr(str(BASE / 'candidate')) + ')')
    driver = driver.replace('OUT=guard.attempt_root()', 'OUT=output_root()')
    (destination / 'driver.py').write_text(driver)
    # Changed driver only; fixed modules and inherited files stay by reference.
    (destination / 'composition.py').write_bytes((HERE / 'composition.py').read_bytes())
    sources[HERE / 'compose.py'] = digest(HERE / 'compose.py')
    sources[HERE / 'composition.py'] = digest(HERE / 'composition.py')
    for name in ('driver.py', 'composition.py', 'launch.sh'):
        path = destination / name
        sources[path] = digest(path)
    manifest = {'schema': 'kpf18.disabled-driver-composition.v1', 'runtime_dispatch': False,
                'predecessor': str(BASE), 'transport': str(TRANSPORT),
                'sources': {str(p): sha for p, sha in sources.items()}}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    marker.unlink()
    return manifest


if __name__ == '__main__':
    print(json.dumps(install(sys.argv[1]), indent=2))
