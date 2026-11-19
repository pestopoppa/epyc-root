"""Seal a disabled terminal-refusal successor; retain all inputs by reference."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/kvu')
BASE = SCRATCH / 'driver-transport-successor-20261119'
BOUNDARY = HERE.parent / 'kpf18-g3-owned-drain-20261104'
PINS = {
    BASE / 'manifest.json': '5e325357a6508fd6e72ba8287e2d905b98a7349f312bfdbf375b848e9803ca33',
    BASE / 'driver.py': '6999b2b215c75dddd911c42f9dbeb8ddce2f9fff22f149c1f4966997ab74f47b',
    BOUNDARY / 'driver-entry-refusal.patch': '194b0bd2eb14b1a5a0752977d1f948158a29cf7692a090598220d164366964eb',
    BOUNDARY / 'driver_boundary.py': '6d5830c6dfc53e62a3694387edd23b337546d45c9aac8db2db4c4ed408633b79',
    BOUNDARY / 'adapter.py': '9ec4e80d7c0ffe7f6f2fc5e0cc3d9e1872b2a64cae8b29e77dc6744709470a1f',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(destination):
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists() or destination.is_symlink()
            or not destination.resolve().is_relative_to(SCRATCH)):
        raise ValueError('new private scratch destination required')
    sources = {str(p): sha for p, sha in PINS.items()}
    for name, expected in json.loads((BASE / 'manifest.json').read_text())['sources'].items():
        sources[name] = expected
    # Do not let inherited entries silently overwrite explicit pins.
    sources.update({str(p): sha for p, sha in PINS.items()})
    for name, expected in sources.items():
        if digest(Path(name)) != expected:
            raise ValueError('source identity mismatch: ' + name)
    destination.mkdir()
    marker = destination / 'INCOMPLETE'
    marker.touch()
    (destination / 'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexit 78\n')
    # Only the changed driver is materialized, never an inherited source tree.
    (destination / 'driver.py').write_bytes((BASE / 'driver.py').read_bytes())
    subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1'], cwd=destination,
                   input=(BOUNDARY / 'driver-entry-refusal.patch').read_bytes().replace(
                       b' OUT=guard.attempt_root()', b' OUT=output_root()'),
                   check=True, capture_output=True)
    (destination / 'composition.py').write_bytes((HERE / 'composition.py').read_bytes())
    for path in (HERE / 'compose.py', HERE / 'composition.py', BASE / 'composition.py',
                 destination / 'driver.py', destination / 'composition.py', destination / 'launch.sh'):
        sources[str(path)] = digest(path)
    seal = {'schema': 'kpf18.disabled-terminal-composition.v1', 'runtime_dispatch': False,
            'predecessor': str(BASE), 'boundary_path': str(BOUNDARY), 'sources': sources}
    (destination / 'manifest.json').write_text(json.dumps(seal, indent=2) + '\n')
    # patch may emit a backup when applying with line offsets.
    (destination / 'driver.py.orig').unlink(missing_ok=True)
    marker.unlink()
    return seal


if __name__ == '__main__':
    install(sys.argv[1])
