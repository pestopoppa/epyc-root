"""Producer-shaped capture, strict whole-file refusal, ingest and planner readback."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import kv_quant_27b_v10 as reader  # noqa: E402
from ingest_sources import SOURCES, ingest  # noqa: E402
from kvq_planner_context import context, render  # noqa: E402
from ledger import Ledger  # noqa: E402

AS_OF = "2026-09-25T12:00:00Z"


def write_capture(tmp_path, monkeypatch):
    research_root = Path(os.environ.get(
        "KV_QUANT_TEST_RESEARCH_ROOT", str(reader.RESEARCH_ROOT)
    )).resolve()
    monkeypatch.setattr(
        reader,
        "PRODUCER_PATH",
        research_root / "scripts/benchmark/kv_quant_27b_v10_sweep.py",
    )
    producer = reader._producer()
    monkeypatch.setattr(reader, "RESEARCH_ROOT", tmp_path)
    summary_path = tmp_path / "summary.json"
    summary_path.write_text('{"status":"ok"}\n')
    digest = reader._sha256(summary_path)
    cell_summaries = {}
    for depth in producer.DEPTHS:
        for cell in producer.CELLS:
            replicates = [{
                "status": "ok", "prompt_tokens": depth.target_prefill_tokens,
                "kv_k_mib": 100.0, "kv_v_mib": 200.0, "kv_buffer_total_mib": 300.0,
                "decode_tps": 123.0, "prompt_tps": 400.0,
            } for _ in range(5)]
            cell_summaries[f"{cell.name}|{depth.name}"] = producer.summarize_cell(
                replicates, cell.name, depth.name, 5)
    summary = {"status": "ok", "production_named_kernel": True, "n": 5,
               "cell_summaries": cell_summaries,
               "candidate": {"binary": {"version_line_matches": True}}}
    rows = producer.belief_capture_rows(
        summary, run_id="run-20260925", scored_path="summary.json",
        scored_sha256=digest, emitted_at=AS_OF)
    assert len(rows) == 12
    sidecar = tmp_path / "belief_measurements.jsonl"
    sidecar.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return sidecar, rows, summary_path, producer


def test_writer_rows_project_and_grade_through_shared_ladder(tmp_path, monkeypatch):
    sidecar, rows, summary, _ = write_capture(tmp_path, monkeypatch)
    natives = reader.native_rows(sidecar)
    assert len(natives) == 12
    tup = reader.project(natives[0])
    assert tup.attestation_path == ""
    assert tup.attestation_verified is True
    assert "K buffer 100.0 MiB; V buffer 200.0 MiB" in tup.claim
    assert isinstance(rows[0]["extra"]["arm"]["prefill_tokens_measured"], dict)
    assert isinstance(rows[0]["extra"]["kv_buffer_k_mib"], dict)
    assert rows[0]["extra"]["kv_buffer_k_mib"]["median"] == 100.0
    assert "-fa on" in tup.claim
    assert "d2k" in tup.attestation_locator
    assert tup.extra["arm"]["cache_k"] == tup.extra["arm"]["cache_v"]
    assert tup.extra["instrument_class"] == "bench"
    assert ct.grade(tup)[0]  # one existing measurement ladder, no adapter grade
    summary.write_text("changed")
    assert reader.project(natives[0]).attestation_verified is None


def test_legacy_finite_scalar_stats_remain_accepted(tmp_path, monkeypatch):
    sidecar, rows, _, producer = write_capture(tmp_path, monkeypatch)
    row = rows[0]
    row["extra"]["arm"]["prefill_tokens_measured"] = 2048
    row["extra"]["kv_buffer_k_mib"] = 100.0
    row["extra"]["kv_buffer_v_mib"] = 200.0
    row["row_sha256"] = producer.row_digest(row)
    sidecar.write_text("".join(json.dumps(item) + "\n" for item in rows))
    assert len(reader.native_rows(sidecar)) == 12
    assert "K buffer 100.0 MiB; V buffer 200.0 MiB" in reader.project(
        {"row": row, "sidecar_path": str(sidecar)}).claim


@pytest.mark.parametrize("mutation", ["hash", "fa", "kv", "median-bool", "median-nan",
                                       "median-inf", "median-missing", "duplicate", "foreign"])
def test_any_bad_row_voids_whole_sidecar(tmp_path, monkeypatch, mutation):
    sidecar, rows, _, producer = write_capture(tmp_path, monkeypatch)
    if mutation == "hash":
        rows[5]["value"] += 1
    elif mutation == "fa":
        rows[5]["extra"]["arm"]["flash_attention"] = "off"
        rows[5]["row_sha256"] = producer.row_digest(rows[5])
    elif mutation == "kv":
        rows[5]["extra"]["kv_buffer_k_mib"] = None
        rows[5]["row_sha256"] = producer.row_digest(rows[5])
    elif mutation.startswith("median-"):
        stats = rows[5]["extra"]["kv_buffer_k_mib"]
        if mutation == "median-bool":
            stats["median"] = True
        elif mutation == "median-nan":
            stats["median"] = float("nan")
        elif mutation == "median-inf":
            stats["median"] = float("inf")
        else:
            stats.pop("median")
        # Deliberately serialize nonfinite JSON as an untrusted input. The
        # producer's canonical digest correctly refuses it before the reader
        # can be exercised, so retain the original digest for these two cases.
        if mutation not in {"median-nan", "median-inf"}:
            rows[5]["row_sha256"] = producer.row_digest(rows[5])
    elif mutation == "duplicate":
        rows[5] = rows[4]
    else:
        rows[5]["scored_path"] = "../foreign.json"
        rows[5]["row_sha256"] = producer.row_digest(rows[5])
    sidecar.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(sidecar)


def test_ingested_fold_is_only_planner_source(tmp_path, monkeypatch):
    sidecar, _, _, _ = write_capture(tmp_path, monkeypatch)
    ledger_path = tmp_path / "ledger.jsonl"
    assert "unavailable" in render(ledger_path, as_of=AS_OF)
    assert "kv-quant-27b-v10-measurement" in SOURCES
    ledger = Ledger(ledger_path)
    report = ingest(ledger, "kv-quant-27b-v10-measurement", [sidecar], as_of=AS_OF)
    assert report["rows_projected"] == 12
    output = render(ledger_path, as_of=AS_OF)
    assert "latest complete ingested run run-20260925" in output
    assert "Bench-only" in output
    assert "K buffer 100.0 MiB; V buffer 200.0 MiB" in output
    assert output.count("grade=") == 12
    manifest = context(ledger_path, as_of=AS_OF)
    assert manifest["status"] == "available"
    assert manifest["run"] == "run-20260925"
    assert len(manifest["claim_ids"]) == 12
    assert all(f"claim_id={cid}" in output for cid in manifest["claim_ids"])
    assert manifest["frontier"] > 0 and manifest["state_hash"]


def test_planner_keeps_separate_kv_figures_when_claim_is_long(tmp_path, monkeypatch):
    sidecar, rows, _, producer = write_capture(tmp_path, monkeypatch)
    rows[0]["claim"] = rows[0]["claim"] + (" long attestation detail" * 30)
    rows[0]["row_sha256"] = producer.row_digest(rows[0])
    sidecar.write_text("".join(json.dumps(row) + "\n" for row in rows))
    ledger_path = tmp_path / "ledger.jsonl"
    ingest(Ledger(ledger_path), "kv-quant-27b-v10-measurement", [sidecar], as_of=AS_OF)
    output = render(ledger_path, as_of=AS_OF)
    assert "K buffer 100.0 MiB; V buffer 200.0 MiB" in output


def test_applicability_projects_only_recorded_native_fields(tmp_path, monkeypatch):
    sidecar, rows, _, producer = write_capture(tmp_path, monkeypatch)
    row = rows[0]
    row["extra"]["model"] = {"path": "/models/native.gguf"}
    row["extra"]["recipe"] = {"device": "ROCm0"}
    row["run_expected_keys"] = ["native-declared-key"]
    row["row_sha256"] = producer.row_digest(row)
    projected = reader.project({"row": row})
    scope = projected.applicability
    assert scope == {"model_file": "/models/native.gguf", "device": "ROCm0",
                     "context_tokens": row["extra"]["arm"]["context"],
                     "kernel": row["extra"]["kernel"], "run_id": row["run_id"],
                     "run_expected_keys": ["native-declared-key"]}
    frames = ct.to_frames(projected, as_of=AS_OF, adapter_id=reader.ADAPTER_ID)
    assert frames[0]["assertion"]["applicability"] == scope
    assert "backend" not in scope and "quant" not in scope


def test_applicability_does_not_invent_missing_native_values(tmp_path, monkeypatch):
    _, rows, _, _ = write_capture(tmp_path, monkeypatch)
    scope = reader.project({"row": rows[0]}).applicability
    assert set(scope) == {"context_tokens", "kernel", "run_id"}


@pytest.mark.parametrize("field,value", [("model", "invented-model"),
                                           ("model", {"path": None}),
                                           ("recipe", {"device": 1})])
def test_applicability_refuses_malformed_native_declarations(tmp_path, monkeypatch, field, value):
    _, rows, _, producer = write_capture(tmp_path, monkeypatch)
    row = rows[0]
    row["extra"][field] = value
    row["row_sha256"] = producer.row_digest(row)
    with pytest.raises(ct.ProjectionError, match="declaration|applicability"):
        reader.project({"row": row})
