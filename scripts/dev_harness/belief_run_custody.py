"""Producer-time custody for opt-in prospective M1/M2 aggregate capture.

A start is made by each actual miner before analysis. A finish binds its outputs;
publication verifies both. This records code bytes, not a verified git commit.
"""
import hashlib
import json
import os
import secrets
from pathlib import Path

import dh_privacy


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def exclusive_write(path, raw):
    """Publish complete bytes once; a crash cannot expose a partial final file."""
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + secrets.token_hex(12) + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        temporary.unlink(missing_ok=True)


def begin(directory, phase, run_id, declarations, source, targets):
    directory = dh_privacy.private_dir(directory)
    if any(Path(p).exists() for p in targets):
        raise ValueError('prospective miner refuses pre-existing output')
    declaration_bytes = Path(declarations).read_bytes()
    st = directory.stat()
    start = {'directory_device': st.st_dev, 'directory_inode': st.st_ino, 'schema': 'dev-harness-mining-start.v1', 'phase': phase, 'run_id': run_id,
             'declarations_sha256': digest(declaration_bytes), 'producer_sha256': digest(Path(source).read_bytes())}
    exclusive_write(directory / (phase + '.start.json'), encode(start))
    return start


def finish(directory, phase, start, source, files):
    directory = Path(directory)
    start_path = directory / (phase + '.start.json')
    if json.loads(start_path.read_bytes()) != start or digest(Path(source).read_bytes()) != start['producer_sha256']:
        raise ValueError('start or producer bytes changed during mining')
    files = [Path(f) for f in files]
    if not files or any(not f.is_file() or f.is_symlink() for f in files):
        raise ValueError('missing native aggregate output')
    output = {str(f.relative_to(directory)): digest(f.read_bytes()) for f in files}
    final = {'schema': 'dev-harness-mining-finish.v1', 'phase': phase,
             'start_sha256': digest(start_path.read_bytes()), 'outputs': output}
    exclusive_write(directory / (phase + '.finish.json'), encode(final))


def verify(run_dir, declarations):
    run_dir = Path(run_dir)
    declaration_sha = digest(Path(declarations).read_bytes())
    starts = []
    for phase in ('m1', 'm2'):
        start_path = run_dir / (phase + '.start.json')
        finish_path = run_dir / (phase + '.finish.json')
        try:
            start = json.loads(start_path.read_bytes())
            final = json.loads(finish_path.read_bytes())
            if set(start) != {'schema', 'phase', 'run_id', 'declarations_sha256', 'producer_sha256', 'directory_device', 'directory_inode'} or start['schema'] != 'dev-harness-mining-start.v1' or start['phase'] != phase or start['declarations_sha256'] != declaration_sha:
                raise ValueError('start identity mismatch')
            st = run_dir.stat()
            if (start['directory_device'], start['directory_inode']) != (st.st_dev, st.st_ino):
                raise ValueError('producer directory identity mismatch')
            if set(final) != {'schema', 'phase', 'start_sha256', 'outputs'} or final['schema'] != 'dev-harness-mining-finish.v1' or final['phase'] != phase or final['start_sha256'] != digest(start_path.read_bytes()):
                raise ValueError('finish identity mismatch')
            outputs = final['outputs']
            if not isinstance(outputs, dict) or not outputs:
                raise ValueError('no native outputs')
            for name, expected in outputs.items():
                rel = Path(name)
                if rel.is_absolute() or '..' in rel.parts:
                    raise ValueError('unsafe output namespace')
                path = run_dir / rel
                if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
                    raise ValueError('native output digest mismatch')
            starts.append((start, outputs))
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f'prospective {phase} receipt missing or invalid: {exc}') from exc
    if starts[0][0]['run_id'] != starts[1][0]['run_id']:
        raise ValueError('producer run identities differ')
    return starts
