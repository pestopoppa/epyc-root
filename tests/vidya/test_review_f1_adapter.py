"""VB-REVIEW-F1 -- EV-13b review-F1 write hook + strict reader (no inference)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import review_f1 as reader  # noqa: E402
from adapters import review_f1_capture as capture  # noqa: E402


def summary(**over):
    s = {
        "matcher": "semantic-judge.v1", "spec_sha256": "b" * 64,
        "golden_manifest_checksum": "c" * 64, "golden_checksum": "c" * 64,
        "judge_config": {"judge_model": "gemma-4-26B-A4B-it-ORIG", "judge_quant": "Q4_K_M",
                         "reader_model": "Qwen3.8-27B", "reader_quant": "Q8_0",
                         "cross_family_ok": True, "judge_distinct_from_reader": True},
        "per_run": [{"f1": f, "precision": f, "recall": f, "malfunction": False} for f in (0.3, 0.35, 0.4)]
                   + [{"f1": 0.9, "precision": 0.9, "recall": 0.9, "malfunction": True}],
        "judge_parse_fail_rate": 0.01, "location_validity_rate": 0.7,
        "judge_swap": {"judge_swap_delta_pp": 1.2, "gate_ok": True},
    }
    s.update(over)
    return s


def write(tmp_path, s):
    p = tmp_path / "_summary.semantic.gemma__Q4_K_M.json"
    p.write_text(json.dumps(s))
    return p


def test_pre_hook_summary_emits_zero_rows(tmp_path):
    assert reader.rows_for_summary(write(tmp_path, summary())) == ()


def test_rows_exclude_malfunction_and_project(tmp_path):
    p = write(tmp_path, summary())
    capture.write_belief_measurements(p, run_id="ev13b-test", producer="t", emitted_at="2026-09-16T10:00:00Z")
    natives = reader.rows_for_summary(p)
    assert len(natives) == 3
    f1 = next(n["row"] for n in natives if n["row"]["metric"] == "review_f1_mean")
    assert f1["reps"] == 3 and f1["value"] == pytest.approx(0.35)
    assert f1["extra"]["runs_excluded_malfunction"] == 1
    tup = reader.project(natives[0])
    assert tup.protocol_id == "" and tup.attestation_present is True and tup.attestation_verified is True
    # No review-F1 protocol is codified: an observation, located by reader x judge x run.
    assert ct.grade(tup)[:2] == ("Judged", "Located")
    p.write_text(p.read_text() + " ")
    after = reader.project(reader.rows_for_summary(p)[0])
    assert after.attestation_present is False and after.attestation_verified is None
    assert ct.grade(after)[:2] == ("Judged", "Located")


def test_legacy_schema_citation_admissible_and_forged_citation_void(tmp_path):
    p = write(tmp_path, summary())
    side = capture.write_belief_measurements(p, run_id="x", producer="t")
    rows = [json.loads(line) for line in side.read_text().splitlines()]
    assert {r["protocol_id"] for r in rows} == {""}

    def resign(row, pid):
        row = {**row, "protocol_id": pid}
        row["row_sha256"] = capture.row_digest(row)
        return json.dumps(row) + "\n"

    side.write_text("".join(resign(r, capture.CAPTURE_SCHEMA) for r in rows))
    natives = reader.native_rows(side)
    assert len(natives) == 3 and reader.project(natives[0]).protocol_id == ""
    side.write_text("".join(resign(r, "P-QUAL-T1") for r in rows))
    assert reader.native_rows(side) == ()


@pytest.mark.parametrize("over", [
    {"judge_config": {"judge_model": "Qwen3.8-27B", "judge_quant": "Q8_0", "reader_model": "Qwen3.8-27B",
                      "reader_quant": "Q8_0", "cross_family_ok": False}},
    {"golden_manifest_checksum": None},
    {"per_run": [{"f1": 0.3, "precision": 0.3, "recall": 0.3}] * 2},
    {"spec_sha256": None},
])
def test_writer_refusals(tmp_path, over):
    with pytest.raises(capture.CaptureError):
        capture.write_belief_measurements(write(tmp_path, summary(**over)), run_id="x", producer="t")


def test_tampered_sidecar_void(tmp_path):
    p = write(tmp_path, summary())
    side = capture.write_belief_measurements(p, run_id="x", producer="t")
    lines = side.read_text().splitlines()
    row = json.loads(lines[0])
    row["value"] = 0.99
    side.write_text(json.dumps(row) + "\n" + "\n".join(lines[1:]) + "\n")
    assert reader.native_rows(side) == ()
