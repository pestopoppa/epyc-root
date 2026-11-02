"""Prepare a self-contained diagnostic module bundle before any grant.

This does not create a runnable row or verify model weights. Caller must
independently bind the worker plan, launcher, runtime and model catalog.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat

MODULES = ('rowflow_worker.py', 'grant_bridge_draft.py', 'worker_draft.py',
           'supervisor.py', 'contained_supervisor_draft.py', 'pdeath_exec_draft.py',
           'completion_draft.py', 'receipts.py')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare_bundle(source, guard, root, source_pins):
    """Copy the explicit module set and sibling guard into a new private tree.

    root must not exist and must be under /mnt/raid0/llm/tmp/kvu. A manifest
    binds the resulting bytes to independently supplied SHA-256 source pins.
    The caller must establish the pins' provenance; this is not an attestation.
    """
    source, guard, root = Path(source), Path(guard), Path(root)
    allowed = Path('/mnt/raid0/llm/tmp/kvu').resolve()
    if not root.is_absolute() or not root.parent.resolve().is_relative_to(allowed):
        raise ValueError('bundle root must be beneath kvu scratch')
    inputs = [(source / name, Path('launcher') / name) for name in MODULES]
    inputs.append((guard, Path('kvu-vkq3-guard-review-20261102/guard.py')))
    names = {str(rel) for _, rel in inputs}
    if (not isinstance(source_pins, dict) or set(source_pins) != names or
            any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v)
                for v in source_pins.values())):
        raise ValueError('source pins must cover the exact bundle with SHA-256 digests')
    root.mkdir(mode=0o700)
    try:
        manifest = {}
        for src, rel in inputs:
            dst = root / rel
            dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            # O_NOFOLLOW closes the check/open symlink race. Hash the exact bytes copied.
            fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as inp:
                if not stat.S_ISREG(os.fstat(inp.fileno()).st_mode):
                    raise ValueError('source must be a regular non-symlink: ' + str(src))
                h = hashlib.sha256()
                with dst.open('xb') as out:
                    for chunk in iter(lambda: inp.read(1024 * 1024), b''):
                        h.update(chunk)
                        out.write(chunk)
            actual = h.hexdigest()
            if not hmac.compare_digest(actual, source_pins[str(rel)]):
                raise ValueError('source digest mismatch: ' + str(rel))
            os.chmod(dst, 0o400)
            manifest[str(rel)] = actual
        payload = (json.dumps({'schema': 'kvu-diagnostic-bundle-v1', 'files': manifest},
                              sort_keys=True, indent=2) + '\n').encode()
        # Write the complete record privately before making its public name visible.
        temporary_manifest = root / '.bundle-manifest.tmp'
        with temporary_manifest.open('xb') as out:
            out.write(payload)
            out.flush()
            os.fchmod(out.fileno(), 0o400)
            os.fsync(out.fileno())
        os.replace(temporary_manifest, root / 'bundle-manifest.json')
        return manifest
    except BaseException:
        # Preserve partial custody; no caller may re-use this root.
        raise
