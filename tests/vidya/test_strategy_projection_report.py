"""Synthetic custody and shared-grade fixtures for StrategyStore report capture."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import stat
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(ROOT / "scripts" / "harness"))
import cli  # noqa: E402
from adapters import strategy_projection_report as adapter  # noqa: E402
from claim_tuple import grade  # noqa: E402
import strategy_projection_report_capture as producer  # noqa: E402

AS_OF = "2026-10-05T00:00:00Z"


def _app_root() -> Path:
    value = os.environ.get("NI53_APP_SOURCE_ROOT")
    if not value:
        pytest.skip("dedicated NI53 off-host CI binds NI53_APP_SOURCE_ROOT to the reviewed app source")
    root = Path(value).resolve(strict=True)
    producer._app_source_bytes(root)  # A declared bad binding is a fixture failure, never a skip.
    return root


def _put(run_dir: Path, name: str, raw: bytes) -> dict:
    return producer._write_exclusive(run_dir / name, raw)


def _capsule(tmp_path: Path, *, ok: bool | None = True,
             execution_started: bool = True, journal_drift: bool = False) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_root = _app_root()
    journal_dir = tmp_path / "fixture-journal"
    store_dir = tmp_path / "fixture-store"
    journal_dir.mkdir()
    store_dir.mkdir()
    # The fixture binds synthetic files only; no app code or live store is opened.
    (journal_dir / "autopilot_journal.jsonl").write_text('{"fixture":true}\n')
    (store_dir / "strategies.db").write_bytes(b"synthetic sqlite identity\n")
    capture_id = uuid.uuid4().hex
    private_root = tmp_path / "private-captures"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    run_dir = private_root / capture_id
    run_dir.mkdir(mode=0o700)
    run_dir.chmod(0o700)
    sources = producer._app_source_bytes(app_root)
    source_refs = {name: _put(run_dir, name, raw) for name, raw in sources.items()}
    producer_source = producer._regular_bytes(Path(producer.__file__).resolve(), producer.MAX_SOURCE_BYTES)
    producer_ref = _put(run_dir, "producer-source.bin", producer_source)
    started, ended = "2026-10-05T00:00:00Z", "2026-10-05T00:00:01Z"
    request = {"schema": producer.REQUEST_SCHEMA, "capture_id": capture_id,
               "started_utc": started, "producer_source": producer_ref,
               "applicability": "synthetic_fixture", "application_root": str(app_root),
               "application_sources": source_refs,
               "input_roots": [producer._directory_identity(journal_dir, "journal-directory"),
                               producer._directory_identity(store_dir, "strategy-store-directory")],
               "declared_inputs": producer.declared_inputs(journal_dir, store_dir),
               "mode": {"write_missing": False, "allow_hash_fallback": False, "strict": True},
               "integrity_proposition": producer.PROPOSITION,
               "input_claim": "hash_only_declared_identity_no_transitive_completeness",
               "exclusions": ["transitive dependency completeness", "environment contents",
                              "embedding quality", "historical pre-hook output",
                              "whole-host health", "immutable SQLite snapshot",
                              "auxiliary StrategyStore temporary-file cleanup"]}
    request_ref = _put(run_dir, "execution-request.json", producer.canonical(request) + b"\n")
    report_ok = ok
    exception_type = ("FileNotFoundError" if not execution_started else
                      "RuntimeError" if ok is None else None)
    exit_code = None if ok is None else (0 if ok else 1)
    stdout = b"" if ok is None else producer.canonical({"ok": ok, "fixture": "synthetic"}) + b"\n"
    stderr = b"synthetic diagnostic\n" if ok is None else b""
    stdout_ref, stderr_ref = _put(run_dir, "stdout.bin", stdout), _put(run_dir, "stderr.bin", stderr)
    markdown_ref = None if ok is None else _put(run_dir, "report-markdown.bin", b"# Synthetic fixture\n")
    if journal_drift:
        with (journal_dir / "autopilot_journal.jsonl").open("ab") as handle:
            handle.write(b'{"fixture_append":true}\n')
    custody_complete = not journal_drift
    terminal = {"schema": adapter.SCHEMA + ".terminal", "capture_id": capture_id,
                "started_utc": started, "ended_utc": ended, "execution_started": execution_started,
                "exit_code": exit_code, "exception_type": exception_type,
                "custody_complete": custody_complete,
                "capture_complete": ok is not None and execution_started and custody_complete,
                "post_identity_error": "DeclaredJournalDrift" if journal_drift else None}
    terminal_ref = _put(run_dir, "terminal.json", producer.canonical(terminal) + b"\n")
    post_identity = {"schema": adapter.SCHEMA + ".input-identity", "capture_id": capture_id,
        "captured_utc": ended,
        "roots": [producer._directory_identity(journal_dir, "journal-directory"),
                  producer._directory_identity(store_dir, "strategy-store-directory")],
        "files": producer.declared_inputs(journal_dir, store_dir),
        "application_source_sha256": {name: ref["sha256"] for name, ref in source_refs.items()}}
    post_ref = _put(run_dir, "post-input-identity.json", producer.canonical(post_identity) + b"\n")
    record = {"schema": adapter.SCHEMA, "capture_id": capture_id,
              "applicability": "synthetic_fixture", "started_utc": started,
              "ended_utc": ended, "execution_started": execution_started, "exit_code": exit_code,
              "exception_type": exception_type, "report_ok": report_ok,
              "custody_complete": custody_complete,
              "capture_complete": ok is not None and execution_started and custody_complete,
              "post_identity_error": "DeclaredJournalDrift" if journal_drift else None,
              "integrity_proposition": None if ok is None else producer.PROPOSITION,
              "request": request_ref, "stdout": stdout_ref, "stderr": stderr_ref,
              "report_markdown": markdown_ref, "terminal": terminal_ref,
              "post_input_identity": post_ref}
    record["receipt_sha256"] = producer.sha256(producer.canonical(record))
    receipt = run_dir / "receipt.json"
    _put(run_dir, "receipt.json", producer.canonical(record) + b"\n")
    return receipt


def test_synthetic_true_and_false_report_bools_share_verifier_grade_and_private_cli(tmp_path, capsys):
    for result in (True, False):
        receipt = _capsule(tmp_path / str(result), ok=result)
        record, digest = adapter.read_receipt(receipt)
        assert receipt.parent.stat().st_mode & 0o777 == 0o700
        assert stat.S_IMODE(receipt.stat().st_mode) == 0o400
        assert record["applicability"] == "synthetic_fixture"
        native = adapter.native_rows(receipt)
        assert len(native) == 1
        row = adapter.project_strategy_projection_report(native[0])
        assert row.value is result
        assert row.metric == "strategy_projection_report_ok"
        assert row.metric_direction == "higher_better" and row.protocol_id == ""
        assert row.extra["applicability"] == "synthetic_fixture"
        assert row.attestation_locator == adapter.public_locator(receipt)
        assert str(receipt.parent) not in row.attestation_locator
        assert row.extra["receipt_sha256"] == digest
        assert grade(row)[:2] == ("Judged", "Located")

        ledger = tmp_path / f"ledger-{result}.jsonl"
        rc = cli.main(["--ledger", str(ledger), "--json", "ingest",
                       "strategy-projection-report", "--path", str(receipt.parent),
                       "--as-of", AS_OF, "--dry-run"])
        rendered = capsys.readouterr().out
        assert rc == 0
        assert str(receipt.parent) not in rendered
        report = json.loads(rendered)
        assert report["units_projected"] == report["rows_projected"] == 1
        assert report["refused"] == report["declined"] == []
        assert not ledger.exists() or ledger.stat().st_size == 0


def test_explicit_wrapper_captures_one_offhost_dry_run_and_restores_import_state(tmp_path):
    app_root = _app_root()
    journal_dir = tmp_path / "owned-empty-journal"
    store_dir = tmp_path / "owned-empty-strategy-store"
    output_root = tmp_path / "owned-private-captures"
    journal_dir.mkdir()
    store_dir.mkdir()
    output_root.mkdir(mode=0o700)
    output_root.chmod(0o700)
    before_meta_path = tuple(sys.meta_path)
    receipt = producer.capture_report(app_root=app_root, journal_dir=journal_dir,
        strategy_path=store_dir, output_root=output_root, write_missing=False,
        allow_hash_fallback=False, capture=True, strict=True)
    assert tuple(sys.meta_path) == before_meta_path
    record, _ = adapter.read_receipt(receipt)
    assert record["applicability"] == "captured_cli"
    terminal_raw = adapter._artifact(receipt.parent, record["terminal"])
    terminal = json.loads(terminal_raw.rstrip(b"\n"))
    stderr_raw = adapter._artifact(receipt.parent, record["stderr"])
    stderr_sha256 = hashlib.sha256(stderr_raw).hexdigest()
    assert record["execution_started"] is True and record["capture_complete"] is True, (
        f"capture incomplete; terminal={terminal!r}; stderr_sha256={stderr_sha256}"
    )
    assert record["report_ok"] is True and record["exit_code"] == 0
    request = adapter._request_for_native(receipt)[0]
    assert request["started_utc"] == record["started_utc"]
    assert request["mode"] == {"write_missing": False, "allow_hash_fallback": False,
                               "strict": True}
    native = adapter.native_rows(receipt)
    assert len(native) == 1
    projected = adapter.project_strategy_projection_report(native[0])
    assert projected.value is True
    assert projected.extra["applicability"] == "captured_cli"
    assert grade(projected)[:2] == ("Judged", "Located")
    assert not ({"strategy_projection_report", "experiment_journal", "journal_shards"}
                & set(sys.modules))

    second_journal = tmp_path / "second-owned-empty-journal"
    second_store = tmp_path / "second-owned-empty-strategy-store"
    second_output = tmp_path / "second-owned-private-captures"
    second_journal.mkdir()
    second_store.mkdir()
    second_output.mkdir(mode=0o700)
    second_output.chmod(0o700)
    second_receipt = producer.capture_report(app_root=app_root, journal_dir=second_journal,
        strategy_path=second_store, output_root=second_output, write_missing=False,
        allow_hash_fallback=False, capture=True, strict=True)
    second_record, _ = adapter.read_receipt(second_receipt)
    assert second_record["capture_complete"] is True
    assert tuple(sys.meta_path) == before_meta_path


def test_exception_diagnostic_preserves_original_terminal_and_projects_zero_rows(tmp_path):
    receipt = _capsule(tmp_path / "diagnostic", ok=None)
    record, _ = adapter.read_receipt(receipt)
    assert record["exception_type"] == "RuntimeError"
    assert record["report_ok"] is None
    assert adapter.native_rows(receipt) == ()


def test_preexecution_refusal_is_null_and_does_not_claim_a_cli_status(tmp_path):
    receipt = _capsule(tmp_path / "preexecution", ok=None, execution_started=False)
    record, _ = adapter.read_receipt(receipt)
    assert record["execution_started"] is False
    assert record["exit_code"] is None and record["exception_type"] == "FileNotFoundError"
    assert record["report_ok"] is None and adapter.native_rows(receipt) == ()


def test_journal_input_drift_preserves_original_boolean_but_declines_projection(tmp_path):
    receipt = _capsule(tmp_path / "journal-drift", ok=True, journal_drift=True)
    record, _ = adapter.read_receipt(receipt)
    assert record["report_ok"] is True
    assert record["custody_complete"] is False
    assert adapter.native_rows(receipt) == ()


def test_resealed_receipt_boolean_must_match_original_stdout(tmp_path):
    receipt = _capsule(tmp_path / "contradiction", ok=True)
    record = json.loads(receipt.read_bytes())
    record["report_ok"] = False
    unsigned = dict(record)
    unsigned.pop("receipt_sha256")
    record["receipt_sha256"] = hashlib.sha256(producer.canonical(unsigned)).hexdigest()
    receipt.chmod(0o600)
    receipt.write_bytes(producer.canonical(record) + b"\n")
    receipt.chmod(0o400)
    with pytest.raises(ValueError, match="strict CLI return code|report.ok"):
        adapter.read_receipt(receipt)
    with pytest.raises(adapter.ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)


def test_duplicate_json_member_and_moved_uuid_are_refused(tmp_path):
    receipt = _capsule(tmp_path / "duplicate", ok=True)
    raw = receipt.read_bytes()
    receipt.chmod(0o600)
    receipt.write_bytes(raw[:-2] + b',"schema":"duplicate"}\n')
    receipt.chmod(0o400)
    with pytest.raises(ValueError, match="duplicate JSON member"):
        adapter.read_receipt(receipt)
    with pytest.raises(adapter.ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)

    moved = receipt.parent.parent / "renamed-capture"
    os.rename(receipt.parent, moved)
    try:
        with pytest.raises(adapter.ProjectionError, match="custody refused"):
            adapter.native_rows(moved / "receipt.json")
        assert adapter.public_locator(moved / "receipt.json") == "strategy-projection-report:unresolved"
    finally:
        os.rename(moved, receipt.parent)


def test_symlink_artifact_and_nonprivate_capture_directory_are_refused(tmp_path):
    receipt = _capsule(tmp_path / "symlink", ok=True)
    stdout = receipt.parent / "stdout.bin"
    preserved = receipt.parent / "stdout.original"
    stdout.rename(preserved)
    stdout.symlink_to(preserved.name)
    with pytest.raises((OSError, ValueError)):
        adapter.read_receipt(receipt)
    stdout.unlink()
    preserved.rename(stdout)

    original_mode = receipt.parent.stat().st_mode & 0o777
    receipt.parent.chmod(0o755)
    try:
        with pytest.raises(adapter.ProjectionError, match="custody refused"):
            adapter.native_rows(receipt)
    finally:
        receipt.parent.chmod(original_mode)


def test_shared_source_enrollment_names_adapter_and_public_locator():
    from ingest_sources import SOURCES

    source = SOURCES["strategy-projection-report"]
    assert source.module == "strategy_projection_report"
    assert source.report_path == "public_locator"
    assert source.task == "VB-AP-STRATEGY-PROJECTION-REPORT-WIRE"
    assert source.name in cli._FILE_SOURCES
