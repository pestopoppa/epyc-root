"""S4 Omega's ROOT reader is exercised against the producer's controlled live path.

The producer is a separate repository. The focused launcher must set
``EPYC_ORCHESTRATOR_SOURCE_ROOT`` to its pinned clean checkout (or
``S4_OMEGA_RUNNER_PATH`` to the exact runner file). Missing producer code fails
the test instead of skipping it. The runner gets a fake OpenAPI client and local
fake call function; no API, model, or inference request is made.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import s4_omega_ab as reader  # noqa: E402
from ledger import Ledger  # noqa: E402

AS_OF = "2026-10-24T12:00:00Z"

def _producer():
    runner_pin = os.environ.get("S4_OMEGA_RUNNER_PATH")
    source_root = os.environ.get("EPYC_ORCHESTRATOR_SOURCE_ROOT")
    if runner_pin:
        path = Path(runner_pin)
    elif source_root:
        path = Path(source_root) / "scripts/benchmark/s4_omega_ab.py"
    else:
        raise RuntimeError("set EPYC_ORCHESTRATOR_SOURCE_ROOT to the pinned producer checkout")
    if not path.is_file():
        raise FileNotFoundError(f"pinned S4 Omega producer is missing: {path}")
    benchmark_dir = str(path.parent)
    if benchmark_dir not in sys.path:
        sys.path.insert(0, benchmark_dir)
    spec = importlib.util.spec_from_file_location("s4_omega_ab_producer_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"components": {"schemas": {"ChatResponse": {"properties": {
            "turns": {}, "tokens_generated": {}, "prompt_tokens": {},
        }}}}}


class _Client:
    def get(self, *_args, **_kwargs):
        return _Response()


def _write_live_fixture(tmp_path: Path, *, interrupt_after: int | None = None,
                        first_response: dict | None = None) -> tuple[Path, Any]:
    producer = _producer()
    suite, suite_digest = producer.load_suite()
    root_repo = tmp_path / "root"
    adapter_path = root_repo / "scripts/vidya/adapters/s4_omega_ab.py"
    adapter_path.parent.mkdir(parents=True)
    adapter_path.write_text("controlled test-only reader pin\n", encoding="utf-8")
    source_table = root_repo / "scripts/vidya/adapters/README.md"
    source_table.parent.mkdir(parents=True, exist_ok=True)
    source_table.write_text("S4 Omega REPL A/B runner records\n", encoding="utf-8")
    task = root_repo / "handoffs/active/vidya-belief-substrate-program.md"
    task.parent.mkdir(parents=True, exist_ok=True)
    task.write_text("- [x] **VB-S4-OMEGA-WIRE — controlled fixture**\n", encoding="utf-8")
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "root_lm_system.md").write_text("baseline controlled fixture prompt\n", encoding="utf-8")
    (prompts / "root_lm_system.s4_omega.md").write_text("Omega controlled fixture prompt\n", encoding="utf-8")

    calls = 0

    def call_fn(**kwargs):
        nonlocal calls
        calls += 1
        if interrupt_after is not None and calls > interrupt_after:
            raise RuntimeError("controlled stop after durable requests")
        batch_id = kwargs["batch_id"]
        request = {
            "prompt": kwargs["prompt"], "real_mode": True,
            "force_role": kwargs["force_role"], "force_mode": kwargs["force_mode"],
            "timeout_s": kwargs["timeout"], "request_priority": kwargs["request_priority"],
            "max_queue_wait_ms": 150000, "cache_prompt": kwargs["cache_prompt"],
            "allow_delegation": kwargs["allow_delegation"],
            "scoring_method": kwargs["scoring_method"],
            "workload_class": kwargs["workload_class"], "batch_id": batch_id,
            "x_orchestrator_prompt_root": kwargs["prompt_root"],
        }
        kwargs["client"].capture_payload(request)
        question = next(q for q in suite["questions"] if q["prompt"] == kwargs["prompt"])
        response = {
            "answer": question["expected"], "turns": 2,
            "tokens_generated": 8, "prompt_tokens": 17,
        }
        if calls == 1 and first_response is not None:
            response = dict(first_response)
        return response

    try:
        manifest_path, _records_path, _records = producer.run_live(
            suite=suite, suite_sha256=suite_digest,
            output_dir=tmp_path / "out", root_repo=root_repo,
            override_base=tmp_path / "prompt-overrides", prompt_dir=prompts,
            client=_Client(), call_fn=call_fn,
        )
    except producer.LiveRunInterrupted as exc:
        manifest_path = exc.manifest_path
    return manifest_path, producer


def write_fixture(tmp_path: Path) -> Path:
    """Builder consumed by ``test_ingest_sources``; artifacts come from the actual runner."""
    return _write_live_fixture(tmp_path)[0]


def test_actual_producer_roundtrips_native_rows_through_shared_grader(tmp_path):
    manifest_path, _producer_module = _write_live_fixture(tmp_path)
    native = reader.native_rows(manifest_path)
    assert len(native) == 6 * 5
    tuples = [reader.project(row) for row in native]
    assert {t.category for t in tuples} == {"BASELINE", "CANDIDATE"}
    assert {ct.grade(t)[:2] for t in tuples} == {("Judged", "Located")}
    assert all(t.protocol_id == "" and t.date == "" for t in tuples)
    assert all(t.extra["model_identity"] is None and t.extra["server_identity"] is None for t in tuples)
    assert all(Path(t.attestation_path).is_file() for t in tuples)
    assert all(hashlib.sha256(Path(t.attestation_path).read_bytes()).hexdigest() == t.attestation_sha256
               for t in tuples)
    assert all(t.attestation_locator.startswith(t.attestation_path + "#record=") for t in tuples)
    assert not any("pair" in t.claim.lower() and "delta" in t.claim.lower() for t in tuples)
    assert all("not an exact output-token or cost measure" in t.claim
               for t in tuples if t.extra["native_field"] == "tokens_generated")


def test_false_zero_and_unknown_prompt_tokens_are_preserved(tmp_path):
    manifest_path, _producer_module = _write_live_fixture(
        tmp_path,
        first_response={"answer": "wrong", "turns": 0, "tokens_generated": 0, "prompt_tokens": 0},
    )
    rows = reader.native_rows(manifest_path)
    first = [reader.project(row) for row in rows if row.record["question_id"] == "arith-multiply-17-23"
             and row.record["arm_id"] == "baseline"]
    by_field = {t.extra["native_field"]: t for t in first}
    assert by_field["turns"].value == 0
    assert by_field["tokens_generated"].value == 0
    assert by_field["prompt_tokens"].value == 0
    assert by_field["passed"].value == 0 and by_field["passed"].extra["native_value"] is False

    unknown_path, _ = _write_live_fixture(
        tmp_path / "unknown", first_response={"answer": "391", "turns": 1, "tokens_generated": 4},
    )
    assert json.loads(unknown_path.read_text(encoding="utf-8"))["run_status"] == "refused"
    unknown_rows = reader.native_rows(unknown_path)
    unknown_first = [reader.project(row) for row in unknown_rows
                     if row.record["question_id"] == "arith-multiply-17-23"
                     and row.record["arm_id"] == "baseline"]
    assert {t.extra["native_field"] for t in unknown_first} == {
        "turns", "tokens_generated", "passed", "elapsed_seconds"}
    assert all(t.extra["prompt_tokens"] is None
               and t.extra["prompt_tokens_unavailable_reason"] == "response_missing_prompt_tokens"
               for t in unknown_first)
    assert all("response_missing_prompt_tokens" in t.observation["outcome_reason"]
               for t in unknown_first)


def test_valid_stopped_partial_projects_only_durable_rows_and_labels_status(tmp_path):
    manifest_path, producer = _write_live_fixture(tmp_path, interrupt_after=2)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_status"] == "partial"
    assert manifest["record_count"] == 2
    rows = reader.native_rows(manifest_path)
    assert rows
    tuples = [reader.project(row) for row in rows]
    assert all(t.observation["outcome_native"] == "partial" for t in tuples)
    assert all("capture status=partial" in t.observation["outcome_reason"] for t in tuples)
    assert all("No pair or suite result is inferred" in t.claim for t in tuples)

    # Exercise the producer's separate recovered view and original-byte custody.
    # A producer-authored complete run is held at the same manifest state the
    # incremental writer publishes before its final seal, then passed through
    # the actual recovery function with explicit stopped-writer confirmation.
    complete_path, producer = _write_live_fixture(tmp_path / "recovery-source")
    original_manifest = json.loads(complete_path.read_text(encoding="utf-8"))
    original_manifest["run_status"] = "running"
    original_manifest = producer.with_content_hash(
        {k: v for k, v in original_manifest.items() if k != "content_sha256"})
    producer._atomic_write(complete_path, producer.canonical_json_bytes(original_manifest) + b"\n")
    original_records = complete_path.parent / original_manifest["records_file"]
    with original_records.open("ab") as stream:
        stream.write(b'{"truncated":')
    with pytest.raises(ValueError, match="explicit confirmation"):
        producer.recover_native_run(complete_path)
    recovery_manifest, _ = producer.recover_native_run(complete_path, source_stopped=True)
    recovered_path = complete_path.parent / f"{original_manifest['run_id']}.recovered.manifest.json"
    assert json.loads(recovered_path.read_text(encoding="utf-8")) == recovery_manifest
    recovered_rows = reader.native_rows(recovered_path)
    assert recovered_rows
    assert all(reader.project(row).observation["outcome_native"] == "partial"
               for row in recovered_rows)


def _reseal_manifest_and_records(producer, manifest_path: Path, mutate):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records_path = manifest_path.parent / manifest["records_file"]
    rows = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    mutate(manifest, rows)
    rows = [producer.with_content_hash({k: v for k, v in row.items() if k != "content_sha256"})
            for row in rows]
    raw_records = b"".join(producer.canonical_json_bytes(row) + b"\n" for row in rows)
    records_path.write_bytes(raw_records)
    manifest.update({
        "record_count": len(rows), "record_sha256s": [r["content_sha256"] for r in rows],
        "records_file_sha256": hashlib.sha256(raw_records).hexdigest(),
    })
    sealed = producer.with_content_hash({k: v for k, v in manifest.items() if k != "content_sha256"})
    manifest_path.write_bytes(producer.canonical_json_bytes(sealed) + b"\n")


def test_hash_identity_and_snapshot_mismatches_are_refused(tmp_path):
    hash_path, _ = _write_live_fixture(tmp_path / "hash")
    manifest = json.loads(hash_path.read_text(encoding="utf-8"))
    records_path = hash_path.parent / manifest["records_file"]
    records_path.write_bytes(records_path.read_bytes() + b" ")
    with pytest.raises(ct.ProjectionError, match="records_file_sha256"):
        reader.native_rows(hash_path)

    identity_path, producer = _write_live_fixture(tmp_path / "identity")
    _reseal_manifest_and_records(
        producer, identity_path,
        lambda _manifest, rows: rows[0].update(question_id="foreign-question"),
    )
    with pytest.raises(ct.ProjectionError, match="question/arm identity"):
        reader.native_rows(identity_path)

    snapshot_path, _ = _write_live_fixture(tmp_path / "snapshot")
    manifest = json.loads(snapshot_path.read_text(encoding="utf-8"))
    prompt_file = snapshot_path.parent / manifest["source_snapshot_dir"] / "baseline.root_lm_system.md"
    prompt_file.write_text("altered prompt snapshot\n", encoding="utf-8")
    with pytest.raises(ct.ProjectionError, match="prompt snapshot does not match"):
        reader.native_rows(snapshot_path)


def test_project_reopens_and_refuses_mutated_or_forged_reader_values(tmp_path):
    manifest_path, _ = _write_live_fixture(tmp_path / "mutated")
    metric = next(row for row in reader.native_rows(manifest_path) if row.metric_field == "turns")

    # Frozen dataclass does not freeze the nested producer row.
    metric.record["turns"] = metric.record["turns"] + 9
    with pytest.raises(ct.ProjectionError, match="selected record changed"):
        reader.project(metric)

    manifest_path, _ = _write_live_fixture(tmp_path / "forged")
    metric = next(row for row in reader.native_rows(manifest_path) if row.metric_field == "turns")
    with pytest.raises(ct.ProjectionError, match="value does not match"):
        reader.project(replace(metric, value=metric.value + 9))

    manifest_path, _ = _write_live_fixture(tmp_path / "changed-after-read")
    metric = next(row for row in reader.native_rows(manifest_path) if row.metric_field == "turns")
    records_path = Path(metric.records_path)
    records_path.write_bytes(records_path.read_bytes() + b" ")
    with pytest.raises(ct.ProjectionError, match="records_file_sha256"):
        reader.project(metric)


def test_synthetic_dry_run_is_declined(tmp_path):
    producer = _producer()
    suite, suite_digest = producer.load_suite()
    manifest_path, _records_path, _records = producer.run_dry_run(
        suite=suite, suite_sha256=suite_digest, output_dir=tmp_path,
    )
    assert reader.native_rows(manifest_path) == ()


def test_cli_only_new_is_idempotent_for_replayed_producer_run(tmp_path, capsys):
    manifest_path, _ = _write_live_fixture(tmp_path / "fixture")
    ledger = tmp_path / "ledger.jsonl"
    args = ["--ledger", str(ledger), "--json", "ingest", "s4-omega-ab", "--path",
            str(manifest_path), "--as-of", AS_OF]
    assert cli.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    initial_count = len(Ledger(ledger).read_all())
    assert first["rows_projected"] == 30 and initial_count == 90
    assert cli.main([*args, "--only-new"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["rows_projected"] == 0 and second["frames_emitted"] == 0
    assert len(Ledger(ledger).read_all()) == initial_count
