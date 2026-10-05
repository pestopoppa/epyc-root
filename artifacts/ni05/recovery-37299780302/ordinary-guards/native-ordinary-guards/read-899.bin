"""Unit tests for src/uncertainty_shadow.py (URE-1 routing uncertainty shadow logging)."""

from __future__ import annotations

import json
from pathlib import Path

from src.uncertainty_shadow import (
    compute_routing_uncertainty,
    emit_uncertainty_shadow,
    ingest_uncertainty_shadow,
)
from src.trace import ensure_schema
from src.features import get_features


# ─── compute ─────────────────────────────────────────────────────────────────────

def test_flat_q_is_high_uncertainty() -> None:
    # multiple alternatives, ~identical Q (the DAR-1 96%-uniform pathology) → uncertain
    meta = {"decision_source": "learned", "q_topk": [0.501, 0.500, 0.499],
            "q_robust_confidence": 0.5}
    u = compute_routing_uncertainty(meta)
    assert u["score"] > 0.6
    assert u["components"]["flat_q"] > 0.8
    assert u["n_alternatives"] == 3


def test_clear_winner_is_low_uncertainty() -> None:
    meta = {"decision_source": "learned", "q_topk": [0.95, 0.20, 0.10],
            "q_robust_confidence": 0.95, "selection_score_topk": [0.9, 0.2]}
    u = compute_routing_uncertainty(meta)
    assert u["score"] < 0.4
    assert u["components"]["flat_q"] < 0.2  # wide spread → low flat-q uncertainty


def test_missing_signals_tolerated() -> None:
    # only a source, no Q at all → falls back to source prior
    u = compute_routing_uncertainty({"decision_source": "rules"})
    assert 0.0 <= u["score"] <= 1.0
    assert u["components"]["source_prior"] == 0.6
    assert u["n_alternatives"] == 0


def test_classifier_confidence_label_mapped() -> None:
    low = compute_routing_uncertainty({"decision_source": "classifier", "classifier_confidence": "low"})
    high = compute_routing_uncertainty({"decision_source": "classifier", "classifier_confidence": "high"})
    assert low["components"]["low_classifier_confidence"] > high["components"]["low_classifier_confidence"]


def test_score_bounded() -> None:
    for meta in [{}, {"q_topk": []}, {"q_topk": [1.0]}, {"decision_source": "x", "q_topk": [0.5, 0.5]}]:
        u = compute_routing_uncertainty(meta)
        assert 0.0 <= u["score"] <= 1.0


# ─── emit (shadow JSONL) ─────────────────────────────────────────────────────────

def test_emit_writes_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "shadow.jsonl"
    meta = {"decision_source": "learned", "chosen_action": "coder:repl",
            "q_topk": [0.9, 0.2], "q_robust_confidence": 0.9}
    assert emit_uncertainty_shadow(meta, request_id="req-1", path=p) is True
    lines = p.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["request_id"] == "req-1"
    assert rec["chosen_action"] == "coder:repl"
    assert 0.0 <= rec["uncertainty_score"] <= 1.0
    assert "source_prior" in rec["uncertainty_components"]
    assert rec["ts"]


def test_emit_appends(tmp_path: Path) -> None:
    p = tmp_path / "shadow.jsonl"
    emit_uncertainty_shadow({"decision_source": "rules"}, path=p)
    emit_uncertainty_shadow({"decision_source": "learned", "q_topk": [0.9, 0.1]}, path=p)
    assert len(p.read_text().splitlines()) == 2


def test_emit_never_raises_on_bad_path() -> None:
    # unwritable path → returns False, does not raise (hot-path safety)
    assert emit_uncertainty_shadow({"decision_source": "x"}, path="/proc/cannot/write/here.jsonl") is False


# ─── ingest → approval_record ────────────────────────────────────────────────────

def test_ingest_to_approval_record(tmp_path: Path) -> None:
    shadow = tmp_path / "shadow.jsonl"
    emit_uncertainty_shadow({"decision_source": "learned", "chosen_action": "architect",
                             "q_topk": [0.5, 0.49], "q_robust_confidence": 0.5}, request_id="r1", path=shadow)
    emit_uncertainty_shadow({"decision_source": "rules", "chosen_action": "worker"}, request_id="r2", path=shadow)

    conn = ensure_schema(tmp_path / "e.sqlite")
    n = ingest_uncertainty_shadow(shadow, conn)
    assert n == 2
    rows = conn.execute(
        "SELECT request_id, selected_role, trigger_reason, uncertainty_score, uncertainty_components "
        "FROM approval_record ORDER BY request_id"
    ).fetchall()
    assert rows[0][0] == "r1" and rows[0][1] == "architect"
    assert rows[0][2] == "uncertainty_shadow"
    assert rows[0][3] is not None
    assert json.loads(rows[0][4])  # components round-tripped as JSON
    conn.close()


def test_ingest_missing_file_is_zero(tmp_path: Path) -> None:
    conn = ensure_schema(tmp_path / "e.sqlite")
    assert ingest_uncertainty_shadow(tmp_path / "nope.jsonl", conn) == 0
    conn.close()


# ─── feature flags ───────────────────────────────────────────────────────────────

def test_flags_exist_and_default_off() -> None:
    f = get_features()
    assert hasattr(f, "ure_uncertainty_shadow_log")
    assert hasattr(f, "batch_edit_mode")
    assert hasattr(f, "dcp_for_consult")
    assert hasattr(f, "review_before_commit_consult")
    # both default OFF in prod + test
    assert f.ure_uncertainty_shadow_log is False
    assert f.batch_edit_mode is False
    assert f.dcp_for_consult is False
    assert f.review_before_commit_consult is False
