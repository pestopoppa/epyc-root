"""Synthetic identity checks; these do not build or run the candidate."""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).with_name('reciprocal_source_preflight.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, stdout=subprocess.PIPE).stdout.decode().strip()


@pytest.fixture
def candidate(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    git(source, 'init', '-q')
    git(source, 'config', 'user.name', 'fixture')
    git(source, 'config', 'user.email', 'fixture@example.invalid')
    (source / 'file').write_text('base')
    git(source, 'add', 'file')
    git(source, 'commit', '-qm', 'fixture')
    head, tree = git(source, 'rev-parse', 'HEAD'), git(source, 'rev-parse', 'HEAD^{tree}')
    (source / 'file').write_text('candidate')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'schema': 'autokernel-candidate-source-v1', 'head_commit': head,
        'base_tree': tree, 'changed_paths': ['file'], 'files': [{'path': 'file', 'mode': '100644',
        'sha256': hashlib.sha256(b'candidate').hexdigest()}]}))
    return source, manifest, hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_accepts_matching_checkout(candidate):
    assert mod.verify_candidate_source(*candidate)['status'] == 'PASS'


def test_refuses_tampered_checkout(candidate):
    (candidate[0] / 'file').write_text('other')
    with pytest.raises(ValueError, match='file SHA-256'):
        mod.verify_candidate_source(*candidate)


def test_refuses_untracked_and_manifest_mismatch(candidate):
    (candidate[0] / 'unexpected').write_text('other')
    with pytest.raises(ValueError, match='untracked'):
        mod.verify_candidate_source(*candidate)
    with pytest.raises(ValueError, match='manifest SHA-256'):
        mod.verify_candidate_source(candidate[0], candidate[1], '0' * 64)
