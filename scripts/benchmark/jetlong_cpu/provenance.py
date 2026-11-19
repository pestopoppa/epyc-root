"""Offline candidate provenance checks; integration and qualification required."""
import hashlib
import os
from pathlib import Path
import re

class ProvenanceError(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check_artifacts(manifest):
    """Verify small executable/library files only; never hash model weights here."""
    artifacts = manifest.get('artifacts')
    if not isinstance(artifacts, dict) or not artifacts:
        raise ProvenanceError('empty artifact manifest')
    for path, expected in artifacts.items():
        if path.endswith('.gguf') or not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ProvenanceError('invalid artifact entry')
        if sha256(path) != expected:
            raise ProvenanceError('artifact digest mismatch: ' + path)


def check_runtime_maps(text, expected_dir, expected_paths):
    """Accept only exact pinned ggml mapped files and require base + CPU libraries."""
    root = Path(expected_dir).resolve(strict=True)
    expected = {str(Path(p).resolve(strict=True)) for p in expected_paths}
    paths = set()
    for line in text.splitlines():
        cols = line.split(None, 5)
        if len(cols) != 6 or not cols[5].startswith('/'):
            continue
        raw = cols[5]
        if ' (deleted)' in raw:
            raise ProvenanceError('deleted mapping')
        if not Path(raw).name.startswith(('libggml', 'libllama')):
            continue
        p = Path(raw).resolve(strict=True)
        if not p.is_relative_to(root) or str(p) not in expected:
            raise ProvenanceError('unapproved ggml/llama mapping: ' + str(p))
        paths.add(str(p))
    names = {Path(p).name for p in paths}
    if not any(n.startswith('libggml-base.so') for n in names) or not any(n.startswith('libggml-cpu.so') for n in names):
        raise ProvenanceError('missing runtime ggml base or CPU backend')
    if any(n.startswith(('libggml-hip', 'libggml-cuda')) for n in names):
        raise ProvenanceError('unexpected GPU backend in CPU run')
    return sorted(paths)


def check_live(pid, expected_dir, manifest):
    if not isinstance(pid, int) or pid <= 0:
        raise ProvenanceError('invalid captured pid')
    return check_runtime_maps(Path(f'/proc/{pid}/maps').read_text(), expected_dir, manifest['artifacts'])
