"""Install a sealed disabled transport overlay; never copy a source tree."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CLEANUP = HERE.parent / 'kpf18-seed-cleanup-20261119'
SLOTS = HERE.parent / 'kpf18-g3-slots-deadline-prep-20261105'
SCRATCH = Path('/mnt/raid0/llm/tmp/kvu')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(path, expected):
    if path.is_symlink() or not path.is_file() or digest(path) != expected:
        raise ValueError('source identity mismatch: ' + str(path))
    return path.read_bytes()


def apply(target, patch):
    subprocess.run(['patch', '--batch', '--forward', str(target), str(patch)],
                   check=True, capture_output=True)


def install(destination):
    destination = Path(destination)
    if not destination.is_absolute() or not destination.resolve().is_relative_to(SCRATCH) or destination.exists():
        raise ValueError('new destination under kvu scratch required')
    pins = json.loads((CLEANUP / 'source.json').read_text())
    slots = json.loads((HERE / 'inputs.json').read_text())
    base = Path(pins['base'])
    raw = checked(base, pins['base_sha256'])
    checked(CLEANUP / 'transport.patch', pins['patch_sha256'])
    for name, expected in pins['dependencies'].items():
        checked(Path(name), expected)
    slots_base = ROOT / slots['slots_base']
    slots_raw = checked(slots_base, slots['slots_base_sha256'])
    checked(SLOTS / 'transport.patch', slots['slots_binding_patch_sha256'])
    checked(HERE / 'slots-cleanup.patch', slots['slots_cleanup_patch_sha256'])
    destination.mkdir()
    # Failure leaves a disabled incomplete overlay, never a runnable candidate.
    marker = destination / 'INCOMPLETE'
    marker.touch()
    launch = destination / 'launch.sh'
    launch.write_text('#!/bin/bash\nset -euo pipefail\necho "REFUSED: transport overlay only; native lifecycle unqualified" >&2\nexit 78\n')
    target = destination / 'cancel_seed_transport.py'
    target.write_bytes(raw)
    apply(target, CLEANUP / 'transport.patch')
    checked(target, pins['patched_sha256'])
    apply(target, SLOTS / 'transport.patch')
    checked(target, slots['composed_transport_sha256'])
    helper = destination / 'slots_transport.py'
    helper.write_bytes(slots_raw)
    apply(helper, HERE / 'slots-cleanup.patch')
    checked(helper, slots['slots_patched_sha256'])
    # Pin inherited dependencies by reference. No tree, binary, or log copying.
    paths = [Path(name) for name in pins['dependencies']]
    paths += [base, CLEANUP / 'transport.patch', SLOTS / 'transport.patch',
              slots_base, HERE / 'slots-cleanup.patch', HERE / 'install.py',
              HERE / 'inputs.json', CLEANUP / 'source.json', target, helper, launch]
    seal = {'schema': 'kpf18.disabled-transport-overlay.v1', 'runtime_dispatch': False,
            'dependency_path': str(base.parent),
            'scope': 'SeedControl transport only; native lifecycle and full driver unqualified',
            'sources': {str(p): digest(p) for p in paths}}
    (destination / 'manifest.json').write_text(json.dumps(seal, indent=2)+'\n')
    marker.unlink()
    return seal


if __name__ == '__main__':
    import sys
    print(json.dumps(install(sys.argv[1]), indent=2))
