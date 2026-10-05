from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts/benchmark/e8_terminal_seal.py"
spec = importlib.util.spec_from_file_location("e8_terminal_seal_test", MODULE_PATH)
assert spec is not None and spec.loader is not None
seal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = seal
spec.loader.exec_module(seal)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_abort_seal_binds_marker_and_complete_namespace(tmp_path: Path) -> None:
    namespace = tmp_path / "candidate"
    namespace.mkdir()
    (namespace / "evidence.json").write_text('{"partial":true}\n')

    path = seal.record_terminal_abort(
        namespace,
        writer="fault_injection",
        error=RuntimeError("boom"),
        runner_path=MODULE_PATH,
    )

    value = json.loads(path.read_text())
    marker = namespace / "writer_abort.json"
    assert value["schema"] == seal.RUN_SEAL_SCHEMA
    assert value["status"] == seal.TERMINAL_STATUS
    assert value["no_admission"] is True
    assert value["abort_marker_sha256"] == _sha(marker)
    assert value["runner_sha256"] == _sha(MODULE_PATH)
    assert value["bundle_sha256"] == {
        "evidence.json": _sha(namespace / "evidence.json"),
        "writer_abort.json": _sha(marker),
    }


def test_terminal_abort_supersedes_nonterminal_seal_without_losing_hash(
    tmp_path: Path,
) -> None:
    namespace = tmp_path / "candidate"
    namespace.mkdir()
    old = namespace / "run_seal.json"
    old.write_text('{"status":"failed"}\n')
    old_sha = _sha(old)

    seal.record_terminal_abort(
        namespace,
        writer="fault_injection",
        error=RuntimeError("boom"),
    )

    value = json.loads(old.read_text())
    assert value["status"] == seal.TERMINAL_STATUS
    assert value["superseded_run_seal_sha256"] == old_sha
    assert value["superseded_run_seal_status"] == "failed"


def test_terminal_abort_rejects_contradictory_existing_marker(
    tmp_path: Path,
) -> None:
    namespace = tmp_path / "candidate"
    namespace.mkdir()
    marker = namespace / "writer_abort.json"
    marker.write_text(
        json.dumps(
            {
                "schema": "epyc.e8_quality_writer_abort.v1",
                "status": seal.TERMINAL_STATUS,
                "writer": "different_writer",
                "error_type": "builtins.RuntimeError",
                "error_sha256": "stale",
                "no_auto_retry": True,
                "no_admission": True,
            }
        )
    )

    with pytest.raises(ValueError, match="contradicts requested terminal seal"):
        seal.record_terminal_abort(
            namespace,
            writer="fault_injection",
            error=RuntimeError("boom"),
        )
    assert not (namespace / "run_seal.json").exists()


def test_complete_seal_binds_manifest_and_nested_run_seal(
    tmp_path: Path,
) -> None:
    namespace = tmp_path / "candidate"
    nested = namespace / "nested"
    nested.mkdir(parents=True)
    manifest = namespace / "deterministic_completion_manifest.json"
    manifest.write_text('{"status":"validated"}\n')
    nested_seal = nested / "run_seal.json"
    nested_seal.write_text('{"status":"non_authoritative"}\n')

    path = seal.record_complete(
        namespace,
        writer="deterministic_successor",
        manifest_name=manifest.name,
        runner_path=MODULE_PATH,
    )

    value = json.loads(path.read_text())
    assert value["status"] == seal.COMPLETE_STATUS
    assert value["completion_manifest_sha256"] == _sha(manifest)
    assert value["bundle_sha256"]["nested/run_seal.json"] == _sha(nested_seal)


def test_complete_seal_rejects_staging_namespace(tmp_path: Path) -> None:
    namespace = tmp_path / ".candidate.staging-deadbeef"
    namespace.mkdir()
    (namespace / "manifest.json").write_text("{}\n")
    with pytest.raises(ValueError, match="staging namespace"):
        seal.record_complete(
            namespace,
            writer="test",
            manifest_name="manifest.json",
        )


def test_promote_staged_complete_is_atomic_and_exact(tmp_path: Path) -> None:
    namespace = tmp_path / "published"
    namespace.mkdir()
    root = namespace / "run_seal.json"
    root.write_text(
        json.dumps(
            {
                "schema": seal.RUN_SEAL_SCHEMA,
                "status": seal.STAGED_COMPLETE_STATUS,
            }
        )
        + "\n"
    )

    seal.promote_staged_complete(namespace)

    promoted = json.loads(root.read_text())
    assert promoted["status"] == seal.COMPLETE_STATUS
    assert isinstance(promoted["published_at"], str)
    with pytest.raises(ValueError, match="staged-complete"):
        seal.promote_staged_complete(namespace)


def test_writer_preserves_original_failure_and_success_path(tmp_path: Path) -> None:
    failed_output = tmp_path / "failed"

    @seal.durable_candidate_writer(
        "injected",
        marker_name="abort.json",
        marker_schema="test.abort.v1",
        marker_status="aborted",
    )
    def fail(args: SimpleNamespace) -> None:
        args.output_dir.mkdir()
        raise LookupError("original")

    with pytest.raises(LookupError, match="original"):
        fail(SimpleNamespace(output_dir=failed_output))
    assert json.loads((failed_output / "run_seal.json").read_text())["status"] == (
        seal.TERMINAL_STATUS
    )

    success_output = tmp_path / "success"

    @seal.durable_candidate_writer(
        "successful",
        marker_name="abort.json",
        marker_schema="test.abort.v1",
        marker_status="aborted",
    )
    def succeed(args: SimpleNamespace) -> str:
        args.output_dir.mkdir()
        return "ok"

    assert succeed(SimpleNamespace(output_dir=success_output)) == "ok"
    assert not (success_output / "run_seal.json").exists()
