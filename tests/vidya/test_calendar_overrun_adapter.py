"""Compute-calendar .ended estimate-vs-actual -> strict reader -> shared grade (VB-CAL-OVERRUN-WIRE)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import calendar_overrun as reader  # noqa: E402

D4 = ("rc=125 time=2026-10-22T09:00:00Z reason=timeout-cap\n"
      "job_id=d4-k5-s4\nowner=ws58\nstep=k5_s4\nestimated_wall_s=6000\nactual_wall_s=12600\n"
      "started=2026-10-22T05:30:00Z\nratio=2.1\nregions=q0,q1\nco_residents=gpu-quiet:d2b\nnp=8\nctx=131072\n")


def _w(tmp_path, text, name="d4-k5-s4.ended"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_d4_record_projects_censored_ratio_with_shape_and_grades(tmp_path):
    (n,) = reader.native_rows(_w(tmp_path, D4))
    t = reader.project(n)
    assert t.metric == "wall_actual_over_estimated" and t.unit == "ratio" and t.value == 2.1
    assert t.metric_direction == "lower_better" and t.protocol_id == "" and t.reps == 1
    assert t.applicability["np"] == 8 and t.applicability["context_tokens"] == 131072
    assert "ratio >= 2.100" in t.claim and "lower bound" in t.claim and t.extra["censored"] is True
    assert t.attestation_sha256 == n["sha256"] and len(t.attestation_sha256) == 64
    assert ct.grade(t)[:2] == ("Judged", "Located")


def test_legacy_ended_without_estimate_is_unchecked(tmp_path):
    assert reader.native_rows(_w(tmp_path, "rc=1 time=2026-10-23T17:01:17Z reason=exited\n")) == ()


@pytest.mark.parametrize("edit,match", [
    (lambda s: s.replace("estimated_wall_s=6000", "estimated_wall_s=0"), "must be > 0"),
    (lambda s: s.replace("estimated_wall_s=6000", "estimated_wall_s=abc"), "not a number"),
    (lambda s: s.replace("ratio=2.1", "ratio=1.0"), "does not re-derive"),
    (lambda s: s.replace("actual_wall_s=12600", "actual_wall_s=9000"), "disagrees"),
    (lambda s: s.replace("actual_wall_s=12600\n", "").replace("started=2026-10-22T05:30:00Z\n", ""), "no actual"),
    (lambda s: s + "bogus=1\n", "unknown"),
])
def test_bad_records_refuse(tmp_path, edit, match):
    with pytest.raises(ct.ProjectionError, match=match):
        reader.native_rows(_w(tmp_path, edit(D4)))


def test_clean_finish_not_censored_and_actual_derived_from_started(tmp_path):
    txt = ("rc=0 time=2026-10-23T10:00:00Z reason=complete\njob_id=j\nowner=o\nstep=s\n"
           "estimated_wall_s=3600\nstarted=2026-10-23T09:00:00Z\n")
    t = reader.project(reader.native_rows(_w(tmp_path, txt))[0])
    assert t.value == 1.0 and t.extra["censored"] is False and t.applicability == {}


def test_units_and_registration(tmp_path):
    _w(tmp_path, D4)
    (tmp_path / "x.complete").write_text("x")
    assert [p.name for p in reader.units(tmp_path)] == ["d4-k5-s4.ended"]
    assert ct.source_classes()[reader.SOURCE_KIND] == ct.MEASUREMENT_CLASS
    assert all("calendar_overrun" not in module for module, _ in ct.ladders().values())
