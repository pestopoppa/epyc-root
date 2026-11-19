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
REVISION = 'retained-bindings-v2'
R9 = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-format-r9')
RETAINED = Path('/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate')
# A new source inventory, never a relocation claim for the unavailable bytes.
SUPERSEDED = {
    str(R9 / 'evidence_view.py'): '434f97561317bd0a5f75f2bcee2c7ea56b362278958ff77959c7008085422212',
    str(R9 / 'normalize_bridge.py'): 'd3fed4a89230f5b18e9ec38787175c4fee9112c3dfa9e364923e0fa4d8cf8f0c',
    str(R9 / 'test_real_grid.py'): 'bcbb114cf72f5cc86b0672def2e805213c0910257670b9fcaa5bfe68d44e256e',
}
REPLACEMENTS = {
    RETAINED / 'evidence_view.py': SUPERSEDED[str(R9 / 'evidence_view.py')],
    RETAINED / 'normalize_bridge.py': 'a68c3a1e0986bcf4c8a058965bbaa78bc6592ce1172aac6e4d1831eadd9e1ad4',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(destination, *, execution=None, binding_revision=None):
    destination = Path(destination)
    if (not destination.is_absolute() or destination.exists() or destination.is_symlink()
            or not destination.resolve().is_relative_to(SCRATCH)):
        raise ValueError('new private scratch destination required')
    for path, expected in PINS.items():
        if digest(path) != expected:
            raise ValueError('pinned predecessor drift: ' + str(path))
    base_seal = json.loads((BASE / 'manifest.json').read_text())
    if binding_revision not in (None, REVISION):
        raise ValueError('unknown binding revision')
    inherited = dict(base_seal['sources'])
    if binding_revision == REVISION:
        for name, expected in SUPERSEDED.items():
            if inherited.pop(name, None) != expected:
                raise ValueError('historical supersession identity mismatch: ' + name)
        for path, expected in REPLACEMENTS.items():
            if digest(path) != expected:
                raise ValueError('retained replacement drift: ' + str(path))
            if str(path) in inherited and inherited[str(path)] != expected:
                raise ValueError('retained replacement conflicts with inherited seal')
            inherited[str(path)] = expected
        # Independent controls qualify this successor, not the lost R9 suite.
        for path in (HERE / 'test_successor.py',):
            inherited[str(path)] = digest(path)
    sources, relocations = {}, {}
    old_root = Path('/mnt/raid0/llm/worktrees/mains/h-kvu')
    lane = HERE.parents[3]
    for name, expected in inherited.items():
        path = Path(name)
        if path.is_relative_to(old_root):
            path = lane / path.relative_to(old_root)
            relocations[name] = str(path)
        if digest(path) != expected:
            raise ValueError('inherited source drift: ' + name)
        sources[str(path)] = expected
    sources.update({str(path): expected for path, expected in PINS.items()})
    # Explicit reviewed identities only; never learn native identities at entry.
    if execution is not None:
        for name, expected in execution['sources'].items():
            if Path(name).suffix.lower() == '.gguf' or digest(Path(name)) != expected:
                raise ValueError('current execution identity mismatch: ' + name)
            if name in sources and sources[name] != expected:
                raise ValueError('execution identity conflicts with inherited seal: ' + name)
            sources[name] = expected
        execution = {key: value for key, value in execution.items() if key != 'sources'}
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
    (destination / 'execution_admission.py').write_bytes((HERE / 'execution_admission.py').read_bytes())
    (destination / 'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexit 78\n')
    for path in (HERE / 'install.py', HERE / 'supervisor.py', HERE / 'execution_admission.py',
                 destination / 'execution_admission.py', destination / 'supervisor.py', destination / 'launch.sh',
                 destination / 'composition.py', binding / 'composition.py', binding / 'manifest.json'):
        sources[str(path)] = digest(path)
    seal = {'schema': 'kpf18.disabled-supervisor.v1', 'runtime_dispatch': False,
            'driver': str(destination / 'driver.py'), 'helper': str(HELPER), 'sources': sources,
            'predecessor': str(binding), 'boundary_path': str(HELPER.parent),
            'admission': str(destination / 'execution_admission.py'), 'execution': execution,
            'relocations': relocations}
    if binding_revision == REVISION:
        seal.update(schema='kpf18.disabled-supervisor.v2', binding_revision=REVISION,
                    historical_sources=SUPERSEDED,
                    qualification_scope='independent model-free bindings; no historical R9 or native qualification')
    (destination / 'manifest.json').write_text(json.dumps(seal, indent=2) + '\n')
    marker.unlink()
    return seal


if __name__ == '__main__':
    install(sys.argv[1])
