import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import publish_row as pr


def test_declared_store_checks_manifest_and_bytes(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    binary = store / "kernel"
    binary.write_bytes(b"built")
    manifest = store / "SHA256SUMS"
    manifest.write_text(hashlib.sha256(b"built").hexdigest() + "  kernel\n")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    pr.check_kernel_store({"kernel_store": {"path": str(store), "sha256": digest}})
    binary.write_bytes(b"changed")
    with pytest.raises(pr.rf.Refused, match="STORE-MISMATCH"):
        pr.check_kernel_store({"kernel_store": {"path": str(store), "sha256": digest}})
    with pytest.raises(pr.rf.Refused, match="STORE-MISMATCH"):
        pr.check_kernel_store({"kernel_store": {"path": str(store), "sha256": "0" * 64}})


def test_missing_and_escaping_store_refused(tmp_path):
    with pytest.raises(pr.rf.Refused, match="STORE-MISSING"):
        pr.check_kernel_store({"kernel_store": str(tmp_path / "absent")})
    store = tmp_path / "store"
    store.mkdir()
    (store / "SHA256SUMS").write_text("0" * 64 + "  ../elsewhere\n")
    with pytest.raises(pr.rf.Refused, match="STORE-MISMATCH"):
        pr.check_kernel_store({"kernel_store": str(store)})


def test_direct_rowflow_publish_cannot_bypass_store_check(tmp_path):
    with pytest.raises(pr.rf.Refused, match="STORE-MISSING"):
        pr.rf.publish({"kernel_store": str(tmp_path / "absent")}, str(tmp_path))


def test_declared_source_identity_is_checked(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    (store / "kernel").write_bytes(b"ok")
    (store / "SHA256SUMS").write_text(hashlib.sha256(b"ok").hexdigest() + "  kernel\n")
    (store / "BUILD-IDENTITY.json").write_text('{"source_sha":"abc"}')
    pr.check_kernel_store({"kernel_store": {"path": str(store), "source_sha": "abc"}})
    with pytest.raises(pr.rf.Refused, match="STORE-MISMATCH"):
        pr.check_kernel_store({"kernel_store": {"path": str(store), "source_sha": "other"}})


def test_empty_declared_digest_is_rejected(tmp_path):
    (tmp_path / "SHA256SUMS").write_text(hashlib.sha256(b"ok").hexdigest() + "  kernel\n")
    (tmp_path / "kernel").write_bytes(b"ok")
    with pytest.raises(pr.rf.Refused, match="STORE-MISMATCH"):
        pr.check_kernel_store({"kernel_store": {"path": str(tmp_path), "sha256": ""}})
