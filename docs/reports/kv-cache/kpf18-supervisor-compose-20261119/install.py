"""Install only the new supervisor; inherited sources remain referenced."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency')
BASE = Path('/mnt/raid0/llm/tmp/kvu/driver-terminal-successor-20261119')
HELPER = HERE.parent / 'kpf18-g3-owned-drain-20261104/owned_drain.py'
PINS = {BASE / 'manifest.json': 'b990727e5bc09cebc7784e15d6b5c8a55f0c45ae1da04e5d43e9d2bc983ab104',
        HELPER: '6cf1d4159ee768b762ba76f911cab16b675a4b115b1fff34cf6c3e35aa461ec4'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(destination):
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists() or destination.is_symlink()
            or not destination.resolve().is_relative_to(SCRATCH)):
        raise ValueError('new private scratch destination required')
    for path, expected in PINS.items():
        if digest(path) != expected:
            raise ValueError('pinned predecessor drift: ' + str(path))
    base_seal = json.loads((BASE / 'manifest.json').read_text())
    sources, relocations = {}, {}
    old_root = Path('/mnt/raid0/llm/worktrees/mains/h-kvu')
    lane = HERE.parents[3]
    for name, expected in base_seal['sources'].items():
        path = Path(name)
        if path.is_relative_to(old_root):
            path = lane / path.relative_to(old_root)
            relocations[name] = str(path)
        if digest(path) != expected:
            raise ValueError('inherited source drift: ' + name)
        sources[str(path)] = expected
    sources.update({str(path): expected for path, expected in PINS.items()})
    destination.mkdir()
    marker = destination / 'INCOMPLETE'
    marker.touch()
    # Two small binding modules need private manifests; the driver remains
    # an immutable symlink to its original bytes, never a copied source tree.
    binding = destination / 'transport-binding'
    binding.mkdir()
    transport_seal = json.loads((Path(base_seal['predecessor']) / 'manifest.json').read_text())
    transport_seal['sources'] = dict(sources)
    (binding / 'composition.py').write_bytes((Path(base_seal['predecessor']) / 'composition.py').read_bytes())
    (binding / 'manifest.json').write_text(json.dumps(transport_seal, indent=2) + '\n')
    (destination / 'composition.py').write_bytes((BASE / 'composition.py').read_bytes())
    (destination / 'driver.py').symlink_to(BASE / 'driver.py')
    (destination / 'supervisor.py').write_bytes((HERE / 'supervisor.py').read_bytes())
    (destination / 'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexit 78\n')
    for path in (HERE / 'install.py', HERE / 'supervisor.py', destination / 'supervisor.py', destination / 'launch.sh',
                 destination / 'composition.py', binding / 'composition.py', binding / 'manifest.json'):
        sources[str(path)] = digest(path)
    seal = {'schema': 'kpf18.disabled-supervisor.v1', 'runtime_dispatch': False,
            'driver': str(destination / 'driver.py'), 'helper': str(HELPER), 'sources': sources,
            'predecessor': str(binding), 'boundary_path': str(HELPER.parent),
            'relocations': relocations}
    (destination / 'manifest.json').write_text(json.dumps(seal, indent=2) + '\n')
    marker.unlink()
    return seal


if __name__ == '__main__':
    install(sys.argv[1])
