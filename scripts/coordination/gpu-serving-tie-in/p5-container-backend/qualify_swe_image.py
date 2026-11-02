#!/usr/bin/env python3
"""Qualify an already prepared SWE image with deterministic, non-model probes.

Requires independently pinned local inputs. This is an integration check, not
proof of complete isolation or a scoring qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import shlex
from pathlib import Path
import sys

from container_backend import IsolatedContainer


def load_pinned(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('input SHA-256 mismatch: ' + path)
    return raw


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def select_tracked_python(env):
    """Choose a deterministic tracked, readable regular text file in testbed."""
    code, listing, error = env._exec("git ls-files -- '*.py'", 15)
    require(code == 0, 'cannot list tracked Python files: ' + (error or listing).strip()[-1000:])
    for name in sorted(listing.splitlines()):
        if (not re.fullmatch(r'[A-Za-z0-9_./-]+\.py', name)
                or any(part in ('', '.', '..') for part in name.split('/'))):
            continue
        content = env.read_file(name)  # adapter refuses symlinks and traversal
        if content is not None and '\x00' not in content and '\ufffd' not in content and len(content) < 1000000:
            return name, content
    raise RuntimeError('no safe tracked Python text file in testbed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--runner', required=True)
    parser.add_argument('--runner-sha256', required=True)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--dataset-sha256', required=True)
    parser.add_argument('--instance-id', required=True)
    parser.add_argument('--sandbox-source-dir', required=True)
    parser.add_argument('--sandbox-sha256-json', required=True)
    parser.add_argument('--output', required=True)
    a = parser.parse_args()
    load_pinned(a.runner, a.runner_sha256)
    rows = json.loads(load_pinned(a.dataset, a.dataset_sha256))
    matching = [row for row in rows if row.get('instance_id') == a.instance_id]
    require(len(matching) == 1 and bool(matching[0].get('base_commit')), 'instance or base is not unique')
    spec = importlib.util.spec_from_file_location('p5_qualify_harness', a.runner)
    harness = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = harness
    spec.loader.exec_module(harness)
    hashes = json.loads(Path(a.sandbox_sha256_json).read_text())
    checks = []
    with IsolatedContainer(harness, a.image_id, a.sandbox_source_dir, hashes) as env:
        code, out = env.run("python3 -c 'import socket; socket.socket()'", 15)
        require(code != 0 and 'PermissionError' in out and 'Errno 13' in out, 'socket denial not established')
        checks.append('socket_eacces')
        code, _ = env.run('test ! -S /var/run/docker.sock && test ! -e /mnt/raid0/llm', 15)
        require(code == 0, 'host socket or model path exposed')
        checks.append('host_paths_absent')
        require(env.read_file('../etc/passwd') is None, 'parent path accepted')
        require(not env.write_file('../escape', 'bad'), 'parent write accepted')
        code, _ = env.run('ln -s /etc p5_qualification_symlink', 15)
        require(code == 0 and env.read_file('p5_qualification_symlink/passwd') is None,
                'symlink escape not refused')
        checks.append('file_traversal_refused')
        target, original = select_tracked_python(env)
        dirty_marker = 'P5_PRE_RESET_CONTAMINATION_8421'
        patch_marker = 'P5_QUALIFICATION_PATCH_8421'
        require(dirty_marker not in original and patch_marker not in original, 'marker collision')
        require(env.write_file(target, original + '\n# ' + dirty_marker + '\n'), 'cannot seed reset control')
        client = harness.ReplayClient(['ACTION: bash\nprintf "\\n# ' + patch_marker + '\\n" >> ' + shlex.quote(target), 'ACTION: done'])
        result = harness.run_instance(client, env, matching[0], harness.AgentConfig())
        require(result.get('evidence_complete') and result.get('turns_used') == 2,
                'replay evidence incomplete or reset failed')
        patch = result.get('model_patch', '')
        require(target in patch and patch_marker in patch and dirty_marker not in patch,
                'replay patch missing or pre-trial contamination survived reset')
        checks.append('real_instance_reset_replay_and_patch')
    # The context must have removed its own container before any PASS is written.
    result = {'schema': 'p5.swe-image-qualification.v1', 'verdict': 'PASS',
              'image_id': a.image_id, 'instance_id': a.instance_id,
              'base_commit': matching[0]['base_commit'], 'runner_sha256': a.runner_sha256,
              'dataset_sha256': a.dataset_sha256, 'sandbox_sha256': hashes, 'checks': checks,
              'scope': 'bounded integration checks; not complete isolation or scorer qualification'}
    Path(a.output).write_text(json.dumps(result, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
