"""Exercise the KVQ row's prepared model identity with temporary files."""

import hashlib
import os
import runpy
import time
from functools import partial
from pathlib import Path
from unittest.mock import patch

import pytest


JOB = Path(__file__).resolve().parents[2] / "data/vidya/kvq-linkage-fix-20261117/row/job.py"
check_prepared_model = runpy.run_path(str(JOB))["check_prepared_model"]
ORIGINAL = b"original"


def stat_identity(info):
    return {
        "dev": info.st_dev,
        "inode": info.st_ino,
        "bytes": info.st_size,
        "mtime_ns": info.st_mtime_ns,
    }


@pytest.fixture
def prepared_model(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_bytes(ORIGINAL)
    info = path.stat()
    identity = {
        "path": str(path),
        "resolved_path": str(path.resolve()),
        **stat_identity(info),
        "sha256": hashlib.sha256(ORIGINAL).hexdigest(),
        "stable": True,
    }
    prepared = {
        "model_ctime_ns": info.st_ctime_ns,
        "preflight_sha256": hashlib.sha256(b"fixture preflight").hexdigest(),
    }
    check = partial(
        check_prepared_model, path, hash_file=True, identity=identity,
        prepared=prepared, stat_identity=stat_identity,
    )
    return path, check


def test_unchanged_model_reuses_digest_without_opening_content(prepared_model):
    _, check = prepared_model
    with (
        patch.object(Path, "open", side_effect=AssertionError("opened model content")),
        patch("builtins.open", side_effect=AssertionError("opened model content")),
        patch("os.open", side_effect=AssertionError("opened model content")),
    ):
        before = check()
        after = check()

    assert before == after
    assert before["stable"] is True
    assert before["sha256"] == hashlib.sha256(ORIGINAL).hexdigest()


def test_same_size_edit_with_restored_mtime_is_refused(prepared_model):
    path, check = prepared_model
    original = path.stat()
    # Back-to-back filesystem operations can share a kernel timestamp tick.
    time.sleep(0.02)
    path.write_bytes(b"changed!")
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
    mutated = path.stat()
    assert stat_identity(mutated) == stat_identity(original)
    assert mutated.st_ctime_ns != original.st_ctime_ns

    refused = check()
    assert refused["stable"] is False
    assert "sha256" not in refused


def test_missing_model_is_refused(prepared_model):
    path, check = prepared_model
    path.unlink()

    assert check()["stable"] is False


def test_replacement_symlink_to_original_file_is_refused(prepared_model):
    path, check = prepared_model
    renamed = path.rename(path.with_name("renamed.gguf"))
    path.symlink_to(renamed)

    assert check()["stable"] is False
