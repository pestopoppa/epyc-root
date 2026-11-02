"""Offline verifier for a VKQ3 draft bundle; this does not launch it.

The caller supplies trusted pins independently of the bundle, invokes this
from trusted code, and must separately guarantee custody from verification to
execution. A successful check is a point-in-time observation only.
"""
import hashlib
import hmac
import json
import os
import re
import stat

_NAMES = frozenset('launcher/' + n for n in (
    'rowflow_worker.py', 'grant_bridge_draft.py', 'worker_draft.py',
    'supervisor.py', 'contained_supervisor_draft.py', 'pdeath_exec_draft.py',
    'completion_draft.py', 'receipts.py')) | frozenset((
        'kvu-vkq3-guard-review-20261102/guard.py',))
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_REGULAR = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate manifest key')
        out[key] = value
    return out


def _read_regular(dirfd, name, limit=None):
    fd = os.open(name, _REGULAR, dir_fd=dirfd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('bundle member is not a regular file')
        h = hashlib.sha256()
        content = bytearray()
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            h.update(chunk)
            if limit is not None:
                content.extend(chunk)
                if len(content) > limit:
                    raise ValueError('manifest too large')
        return h.hexdigest(), bytes(content)
    finally:
        os.close(fd)


def verify_bundle(root, trusted_pins):
    """Validate exact pins, manifest and content via no-follow descriptors.

    Does not verify pin origin, enclosing directory ancestry, imports, runtime,
    or protect the interval after return. Raises on any malformed input or
    mismatch. Descriptor traversal prevents symlinks inside the opened root.
    """
    if (not isinstance(trusted_pins, dict) or set(trusted_pins) != _NAMES or
            any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v)
                for v in trusted_pins.values())):
        raise ValueError('trusted pins must exactly cover the bundle')
    rootfd = os.open(root, _DIRECTORY)
    try:
        _, raw = _read_regular(rootfd, 'bundle-manifest.json', limit=65536)
        try:
            manifest = json.loads(raw, object_pairs_hook=_unique_pairs)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError('invalid manifest') from exc
        if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'files'} or
                manifest['schema'] != 'kvu-diagnostic-bundle-v1' or
                not isinstance(manifest['files'], dict) or
                manifest['files'] != trusted_pins):
            raise ValueError('manifest does not match trusted pins')
        for directory in ('launcher', 'kvu-vkq3-guard-review-20261102'):
            dfd = os.open(directory, _DIRECTORY, dir_fd=rootfd)
            try:
                for rel in sorted(n for n in _NAMES if n.startswith(directory + '/')):
                    actual, _ = _read_regular(dfd, rel.split('/')[1])
                    if not hmac.compare_digest(actual, trusted_pins[rel]):
                        raise ValueError('bundle digest mismatch: ' + rel)
            finally:
                os.close(dfd)
    finally:
        os.close(rootfd)
