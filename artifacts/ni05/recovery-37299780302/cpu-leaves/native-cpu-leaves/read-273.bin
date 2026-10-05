from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "scripts/benchmark/terminalize_e8_quality_baseline_v5_composite_source.py"
)
SPEC = importlib.util.spec_from_file_location(
    "e8_composite_source_terminalizer_test",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
TERMINALIZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TERMINALIZER
SPEC.loader.exec_module(TERMINALIZER)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminalizer_publishes_exact_nonstaging_complete_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / ".historical.staging-deadbeef"
    artifact = source / "evidence.json"
    artifact.parent.mkdir()
    artifact.write_text('{"value":1}\n')
    hashes = {"evidence.json": _sha(artifact)}
    monkeypatch.setattr(
        TERMINALIZER.FINALIZER,
        "validate_legacy_composite_source",
        lambda _source: {
            "source": str(source),
            "source_sha256": hashes,
            "source_tree_sha256": TERMINALIZER.FINALIZER.RECOVERY.canonical_hash(
                hashes
            ),
        },
    )
    output = tmp_path / "published-source"

    result = TERMINALIZER.execute(
        SimpleNamespace(source_dir=source, output_dir=output)
    )

    assert result == output
    assert (output / "source_snapshot/evidence.json").read_bytes() == artifact.read_bytes()
    manifest = json.loads((output / TERMINALIZER.MANIFEST_NAME).read_text())
    assert manifest["status"] == "complete"
    assert manifest["historical_source"] == str(source)
    seal = json.loads((output / "run_seal.json").read_text())
    assert seal["status"] == TERMINALIZER.TERMINAL_SEAL.COMPLETE_STATUS
    assert seal["completion_manifest_sha256"] == _sha(
        output / TERMINALIZER.MANIFEST_NAME
    )
    assert list(tmp_path.glob(".published-source.staging-*")) == []


def test_complete_seal_validator_rejects_staging_and_bundle_tamper(
    tmp_path: Path,
) -> None:
    staging = tmp_path / ".candidate.staging-deadbeef"
    staging.mkdir()
    (staging / "manifest.json").write_text('{"schema":"test.v1"}\n')
    (staging / "run_seal.json").write_text(
        json.dumps(
            {
                "schema": TERMINALIZER.TERMINAL_SEAL.RUN_SEAL_SCHEMA,
                "status": TERMINALIZER.TERMINAL_SEAL.COMPLETE_STATUS,
                "writer": "test",
                "completion_manifest_path": "manifest.json",
                "completion_manifest_sha256": _sha(staging / "manifest.json"),
                "bundle_sha256": {
                    "manifest.json": _sha(staging / "manifest.json"),
                },
            }
        )
        + "\n"
    )
    with pytest.raises(ValueError, match="published non-staging"):
        TERMINALIZER.FINALIZER._validate_standard_complete_seal(staging)

    published = tmp_path / "published"
    staging.rename(published)
    (published / "manifest.json").write_text('{"schema":"tampered"}\n')
    with pytest.raises(ValueError, match="manifest binding|bundle"):
        TERMINALIZER.FINALIZER._validate_standard_complete_seal(published)


def test_source_recheck_failure_terminalizes_published_copy_without_source_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / ".historical.staging-deadbeef"
    artifact = source / "evidence.json"
    artifact.parent.mkdir()
    artifact.write_text('{"value":1}\n')
    original = artifact.read_bytes()
    hashes = {"evidence.json": _sha(artifact)}
    monkeypatch.setattr(
        TERMINALIZER.FINALIZER,
        "validate_legacy_composite_source",
        lambda _source: {
            "source": str(source),
            "source_sha256": hashes,
            "source_tree_sha256": TERMINALIZER.FINALIZER.RECOVERY.canonical_hash(
                hashes
            ),
        },
    )
    calls = 0

    def fail_second_recheck(_source: Path, _hashes: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("injected source drift")

    monkeypatch.setattr(
        TERMINALIZER,
        "_validate_source_unchanged",
        fail_second_recheck,
    )
    output = tmp_path / "published-source"

    with pytest.raises(ValueError, match="injected source drift"):
        TERMINALIZER.execute(
            SimpleNamespace(source_dir=source, output_dir=output)
        )

    assert artifact.read_bytes() == original
    assert json.loads((output / "run_seal.json").read_text())["status"] == (
        TERMINALIZER.TERMINAL_SEAL.TERMINAL_STATUS
    )
    assert json.loads((output / "writer_abort.json").read_text())["no_admission"] is True
