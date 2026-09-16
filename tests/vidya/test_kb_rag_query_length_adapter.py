"""KB-RAG H2 query-length telemetry -> ClaimTuple projection.

Pinned:
* the ladder is not reimplemented: the grade is whatever ``claim_tuple.grade()`` returns,
  and for a protocol-less observation that is the observation rung;
* identity is unique per (snapshot, group, metric);
* an empty report projects nothing (absence of traffic is not a 0 % rate);
* rows the producer could not have written are refused, never repaired.
"""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import kb_rag_query_length as adapter  # noqa: E402

PREFIX = "ab" * 32
PRODUCER = Path("/workspace/repos/epyc-orchestrator/src/retrieval/kb_rag_query_telemetry.py")


def _row(metric="kb_rag.query_over_cap_rate", key="over_cap_rate", value=0.25):
    return {
        "measurement_id": f"kbrag-qlen-0123456789abcdef-{key}",
        "metric": metric,
        "value": value,
        "unit": "fraction",
        "date": "2026-09-16T10:00:09Z",
        "category": "BASELINE",
        "claim": "1 of 4 KB-RAG queries (0.2500) exceeded the 48-token query cap [/m/gte, qd-v1, a..b]",
        "metric_direction": "lower_better",
        "protocol_id": "",
        "reps": 4,
        "reps_basis": "scored: queries with a recorded untruncated token count",
        "attestation_path": "/x/query_lengths.jsonl",
        "attestation_locator": "/x/query_lengths.jsonl#bytes=0-1234",
        "source_kind": "measurement",
        "extra": {"belief_schema": adapter.BELIEF_SCHEMA, "log_prefix_sha256": PREFIX,
                  "log_prefix_bytes": 1234, "cap": 48},
    }


def _report(rows, observations=4):
    return {"schema": adapter.REPORT_SCHEMA, "observations": observations,
            "belief_measurements": rows}


def test_projection_is_an_observation_graded_by_the_shared_ladder():
    tup = ct.registered()[adapter.PROJECTION_NAME](_row())
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ct._measurement_ladder(tup)[:2]
    assert q == "Judged" and t == "Located"
    assert any("OBSERVATION" in r for r in reasons)
    frames = ct.to_frames(tup, as_of="2026-09-16T12:00:00Z", adapter_id=adapter.ADAPTER_ID)
    assert len(frames) == 3


def test_report_rows_round_trip_with_unique_identity(tmp_path):
    rows = [_row(), _row("kb_rag.query_tokens_p50", "p50", 12),
            _row("kb_rag.query_tokens_p95", "p95", 60), _row("kb_rag.query_tokens_max", "max", 61)]
    path = tmp_path / "report.json"
    path.write_text(json.dumps(_report(rows)))
    tuples = [adapter.project(r) for r in adapter.native_rows(path)]
    assert len({t.measurement_id for t in tuples}) == len(rows) == 4


def test_empty_report_projects_nothing():
    assert adapter.native_rows(_report([], observations=0)) == ()
    with pytest.raises(ct.ProjectionError, match="zero observations"):
        adapter.native_rows(_report([_row()], observations=0))


@pytest.mark.parametrize("mutate, match", [
    (lambda r: r.update(protocol_id="kbrag-v1"), "no codified protocol"),
    (lambda r: r.update(metric_direction="higher_better"), "lower_better"),
    (lambda r: r.update(metric="kb_rag.something_else"), "unknown"),
    (lambda r: r.update(attestation_sha256="cd" * 32), "whole-file"),
    (lambda r: r["extra"].update(belief_schema="other"), "not a"),
    (lambda r: r["extra"].pop("log_prefix_sha256"), "log_prefix_sha256"),
    (lambda r: r.update(reps=0), "grammar"),
    (lambda r: r.update(bogus=1), "non-ClaimTuple"),
])
def test_rows_the_producer_could_not_have_written_are_refused(mutate, match):
    row = copy.deepcopy(_row())
    mutate(row)
    with pytest.raises(ct.ProjectionError, match=match):
        adapter.project(row)


def test_foreign_document_is_refused():
    with pytest.raises(ct.ProjectionError):
        adapter.native_rows({"schema": "something.else", "belief_measurements": []})


@pytest.mark.skipif(not PRODUCER.exists(), reason="orchestrator producer not present on this checkout")
def test_live_producer_rows_project_cleanly(tmp_path):
    """Drift guard against the actual write side, when it is installed."""
    spec = importlib.util.spec_from_file_location("_kbrag_qlen_producer", PRODUCER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    log = tmp_path / "q.jsonl"
    log.write_text("".join(
        json.dumps(mod.build_record("q", query_tokens=n, cap=48, role="query",
                                    prefix_convention="qd-v1", encoder_model_dir="/m",
                                    encoder_slot="s", index_dir="/i",
                                    ts=f"2026-09-16T00:00:0{i}Z")) + "\n"
        for i, n in enumerate([10, 30, 49, 70])))
    rows = adapter.native_rows(mod.build_report(log))
    tuples = [adapter.project(r) for r in rows]
    assert len(tuples) == 4
    assert tuples[0].value == pytest.approx(0.5)
