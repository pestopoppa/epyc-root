#!/usr/bin/env python3
"""Validate HIP P9 publication bindings before invoking the standard publisher.

Check-only by default. This never repairs or retries a queued/parked row.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def validate(spec, inventory_path):
    """Bind the predicate and all three engine commands to the same inventory."""
    inventory_path = Path(inventory_path).resolve(strict=True)
    digest = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
    inventory = json.loads(inventory_path.read_text())
    if spec['id'] != inventory['row']:
        raise ValueError('row identity mismatch')
    launcher = spec['launcher']
    if isinstance(launcher, dict):
        source = Path(launcher['path']).read_bytes()
        if hashlib.sha256(source).hexdigest() != launcher['sha256']:
            raise ValueError('launcher digest mismatch')
    else:
        source = Path(launcher).read_bytes()
    # This row uses a fixed D assignment and one engine invocation. Parse shell
    # words without executing or sourcing the launcher.
    lines = source.decode().splitlines()
    assignments = [line[2:] for line in lines if line.startswith('D=')]
    if assignments != [str(inventory_path.parent)]:
        raise ValueError('launcher directory mismatch')
    commands = [line for line in lines if line.startswith('exec bash ')]
    if len(commands) != 1:
        raise ValueError('expected one engine invocation')
    words = shlex.split(commands[0])
    runtime = str(inventory_path.parent / 'runtime.py')
    for flag, action in [('--precond-cmd', 'inputs'), ('--cmd', 'run'), ('--complete-cmd', 'check')]:
        if words.count(flag) != 1:
            raise ValueError('missing/duplicate engine command: ' + flag)
        command = words[words.index(flag) + 1].replace('$D', str(inventory_path.parent))
        if shlex.split(command) != ['python3', runtime, action, digest]:
            raise ValueError('launcher inventory binding mismatch: ' + action)
    if shlex.split(spec['smoke_predicate']) != ['python3', runtime, 'predicate', digest]:
        raise ValueError('predicate inventory binding mismatch')
    return digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, default=ROOT / 'spec.json')
    parser.add_argument('--inventory', type=Path, help='defaults to the launcher packet inputs.json')
    parser.add_argument('--publish', action='store_true', help='invoke publish_row.py after validation; obey retry limits')
    args = parser.parse_args(argv)
    spec = json.loads(args.spec.read_text())
    launcher = spec['launcher']
    launcher_path = launcher['path'] if isinstance(launcher, dict) else launcher
    inventory_path = args.inventory or Path(launcher_path).parent / 'inputs.json'
    digest = validate(spec, inventory_path)
    print('publication bindings PASS ' + digest, flush=True)
    if args.publish:
        publisher = ROOT.parents[1] / 'coordination/rowflow/publish_row.py'
        return subprocess.run([sys.executable, str(publisher), str(args.spec.resolve())], check=False).returncode
    return 0


if __name__ == '__main__':
    sys.exit(main())
