"""VB-OOLONG-WIRE: per-question Oolong JSONL -> cell rows -> existing measurement ladder."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import oolong  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
SRC = "oolongbench/oolong-synth@" + oolong.SOURCE_REVISIONS["oolongbench/oolong-synth"]


def rec(i, ctx, score, arm="thinking_off", labels=False, clen=131072, **kw):
    r = {"suite": "oolong", "id": i, "context_window_id": ctx, "model": "q35-27b", "arm": arm,
         "family": "synth", "labels_given": labels, "source_revision": SRC,
         "upstream_sha": oolong.UPSTREAM_SHA_PREFIX, "vendored_sha256": oolong.VENDORED_SHA256,
         "context_len": clen, "attempted": True, "answered": True, "no_answer": False,
         "parse_confidence": "high", "score": score,
         "failure_class": None if score >= 1 else "wrong"}
    r.update(kw)
    return r


def results(tmp_path, recs, name="oolong-off.jsonl"):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def base(tmp_path):
    return [rec(i, f"c{i % 3}", 1.0 if i % 2 else 0.0) for i in range(12)]


def write(tmp_path, recs=None, **kw):
    p = results(tmp_path, recs or base(tmp_path))
    return oolong.write_belief_measurements(tmp_path, run_id="o1", producer="win", results_path=p,
                                            emitted_at=WHEN, **kw)


def test_round_trip_observation_and_contexts_basis(tmp_path):
    (nat,) = oolong.native_rows(write(tmp_path))
    tup = oolong.project(nat)
    assert (tup.reps, tup.reps_basis) == (3, "contexts (clustered; 12 items)")
    assert tup.value == 0.5 and tup.protocol_id == ""
    assert ct.grade(tup)[:2] == ("Judged", "Located")      # observation: never gating
    x = tup.extra
    assert (x["model_pin"], x["arm"], x["context_len"], x["source_revision"]) == ("q35-27b", "thinking_off", 131072, SRC)
    assert x["ci"]["method"] == "context-clustered percentile bootstrap" and x["ci"]["n_contexts"] == 3


def test_with_named_protocol_grades_witnessed(tmp_path):
    (nat,) = oolong.native_rows(write(tmp_path, protocol_id="PROTO-X"))
    assert ct.grade(oolong.project(nat))[:2] == ("Witnessed", "Attested")


def test_one_row_per_arm_and_length_cell(tmp_path):
    recs = base(tmp_path) + [rec(100 + i, "d1", 1.0, arm="thinking_on", clen=262144) for i in range(3)]
    p = oolong.write_belief_measurements(tmp_path, run_id="o1", producer="w", emitted_at=WHEN,
                                         results_path=results(tmp_path, recs))
    assert len(oolong.native_rows(p)) == 2


def test_labels_given_never_projects(tmp_path):
    recs = base(tmp_path) + [rec(200 + i, "z", 1.0, arm="labels_given_thinking_off", labels=True) for i in range(5)]
    (nat,) = oolong.native_rows(write(tmp_path, recs))
    assert nat["row"]["extra"]["labels_given_excluded"] == 5 and nat["row"]["extra"]["n_items"] == 12
    only = [rec(i, "z", 1.0, arm="labels_given_thinking_off", labels=True) for i in range(3)]
    with pytest.raises(oolong.CaptureError, match="no gate-eligible"):
        write(tmp_path, only)


@pytest.mark.parametrize("drop", ["parse_confidence", "labels_given", "source_revision",
                                  "context_window_id", "arm", "failure_class", "context_len"])
def test_absent_producer_field_is_refused_not_backfilled(tmp_path, drop):
    recs = base(tmp_path)
    del recs[3][drop]
    with pytest.raises(oolong.CaptureError, match=drop):
        write(tmp_path, recs)


def test_wrong_scorer_or_revision_refused(tmp_path):
    for k, v in (("vendored_sha256", "0" * 64), ("source_revision", "oolongbench/oolong-synth@" + "a" * 40)):
        recs = base(tmp_path)
        recs[0][k] = v
        with pytest.raises(oolong.CaptureError):
            write(tmp_path, recs)


def test_tamper_voids_file_and_mutated_results_grade_down(tmp_path):
    side = write(tmp_path, protocol_id="P")
    p = tmp_path / "oolong-off.jsonl"
    p.write_text(p.read_text() + "\n")
    (nat,) = oolong.native_rows(side)
    q, t, _ = ct.grade(oolong.project(nat))
    assert (q, t) != ("Witnessed", "Attested")
    row = json.loads(side.read_text())
    row["value"] = 0.99
    side.write_text(json.dumps(row) + "\n")
    assert oolong.native_rows(side) == ()


def test_no_sidecar_means_zero_rows(tmp_path):
    assert oolong.native_rows(tmp_path / oolong.SIDECAR_NAME) == ()


def test_projection_refuses_foreign_row():
    with pytest.raises(ct.ProjectionError):
        oolong.project({"row": {"schema": "x"}})
