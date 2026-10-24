"""VB-CLBENCH-CACHE-WIRE: CL-Bench cache-hit report -> OBSERVATION tuples graded by the one shared ladder.

FIXTURE CAVEAT: ``FIX`` carries the 2026-10-22 smoke numbers (0.7948 / 0.868, split 11028 / 1743 / 14058). That
record is a PRE-FIX LAYOUT measurement (written before research 08ace05fd, no basis / missed_split on disk); this
fixture restates its counts in the post-08ace05fd report layout to exercise the carrier and is NOT evidence about
the fixed layout. The real pre-fix file itself must yield no rows (test below)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import clbench_cache_hit as cc  # noqa: E402

WHEN = "2026-10-24T12:00:00Z"
SHA = "7e201b50efd66899a55aac98149e7238c5eed5a8"
IDENT = {"served_model": "Qwen3.6-35B-A3B-Q4_K_M", "recipe": "cme7-poker-smoke", "np": 1, "ctx": 65536, "slots": 1,
         "kernel_build": "10303", "research_sha": SHA, "basis": "prompt_prefix"}
FIX = {"schema": "epyc.clbench_cache_hit.v1", "min_hit": 0.95, "hit_ratio_reusable": 0.7948,
       "raw_cached_over_input": 0.7346, "reusable_tokens": 130762, "cached_tokens": 103933, "basis": "prompt_prefix",
       "hit_ratio_prompt_prefix": 0.868, "prompt_prefix_tokens": 119734, "prompt_prefix_cached_tokens": 103933,
       "missed_split": {"generated_tokens_unreusable": 11028, "history_rewind": 1743, "prompt_prefix_lost": 14058},
       "per_run": [{"run": 0, "calls": 15, "hands": 5, "hit_ratio": 0.7786},
                   {"run": 1, "calls": 9, "hands": 5, "hit_ratio": 0.6077},
                   {"run": 2, "calls": 17, "hands": 5, "hit_ratio": 0.8563}],
       "problems": [], "verdict": "MISS", "trace_files": []}
REAL_POSTFIX = Path("/mnt/raid0/llm/tmp/cme7-poker-out-s2/run-20261023T003634Z/clbench/cache_hit_report.json")
REAL_PREFIX = Path("/mnt/raid0/llm/tmp/cme7-poker-out/run-20261022T131252Z/clbench/cache_hit_report.json")


def report(tmp_path, tweak=None):
    d = json.loads(json.dumps(FIX))
    if tweak:
        tweak(d)
    p = tmp_path / "cache_hit_report.json"
    p.write_text(json.dumps(d))
    return p


def write(tmp_path, tweak=None, ident=None):
    return cc.write_belief_measurements(tmp_path, run_id="cme7-t", producer="t", report_path=report(tmp_path, tweak),
                                        identity=ident or IDENT, emitted_at=WHEN)


def test_fixture_arithmetic_adds_up():
    assert 11028 + 1743 + 14058 == 26829 == 130762 - 103933
    assert 130762 - 119734 == 11028 and 119734 - 103933 == 1743 + 14058


def test_round_trip_and_grade(tmp_path):
    side = write(tmp_path)
    by = {t.metric: t for t in map(cc.project, cc.native_rows(side))}
    assert set(by) == cc.METRICS
    assert by[cc.M_RU].value == pytest.approx(0.7948) and by[cc.M_PP].value == pytest.approx(0.868)
    assert by[cc.M_RU].extra["metric_basis"] == "cme5" and by[cc.M_PP].extra["metric_basis"] == "prompt_prefix"
    assert by[cc.M_RU].metric_direction == by[cc.M_PP].metric_direction == "higher_better"
    assert [by[m].value for m in cc.M_SPLIT.values()] == [11028, 1743, 14058]
    assert all(by[m].metric_direction == "lower_better" for m in cc.M_SPLIT.values())
    for t in by.values():
        assert t.protocol_id == "" and t.attestation_present is True and t.reps == 3
        assert t.applicability["np"] == 1 and t.applicability["context_tokens"] == 65536
        g = ct.grade(t)
        assert g[:2] == ("Judged", "Located")
    assert len(cc.frames_for_sidecar(side, as_of=WHEN)) >= 5


@pytest.mark.skipif(not REAL_POSTFIX.is_file(), reason="real post-fix record absent")
def test_real_postfix_record_projects(tmp_path):
    side = cc.write_belief_measurements(tmp_path, run_id="s2", producer="t", report_path=REAL_POSTFIX,
                                        identity=IDENT, emitted_at=WHEN)
    by = {t.metric: t for t in map(cc.project, cc.native_rows(side))}
    assert by[cc.M_PP].value == pytest.approx(0.9977) and by[cc.M_RU].value == pytest.approx(0.951)
    assert by[cc.M_SPLIT["history_rewind"]].value == 0 and by[cc.M_SPLIT["prompt_prefix_lost"]].value == 633


@pytest.mark.skipif(not REAL_PREFIX.is_file(), reason="real pre-fix record absent")
def test_real_prefix_record_yields_no_rows_never_backfilled(tmp_path):
    with pytest.raises(cc.CaptureError, match="never back-filled"):
        cc.write_belief_measurements(tmp_path, run_id="p", producer="t", report_path=REAL_PREFIX, identity=IDENT)
    assert not (tmp_path / cc.SIDECAR_NAME).exists() and cc.native_rows(tmp_path / cc.SIDECAR_NAME) == ()


@pytest.mark.parametrize("tweak,match", [
    (lambda d: d["missed_split"].update(history_rewind=1744), "inconsistent"),
    (lambda d: d.update(hit_ratio_reusable=0.80), "inconsistent"),
    (lambda d: d.update(problems=["run 0: x"], verdict="INVALID"), "not a complete"),
    (lambda d: d.pop("missed_split"), "never back-filled"),
    (lambda d: d.update(schema="other"), "schema"),
])
def test_writer_refuses_bad_reports(tmp_path, tweak, match):
    with pytest.raises(cc.CaptureError, match=match):
        write(tmp_path, tweak)


@pytest.mark.parametrize("bad", [{"np": 0}, {"research_sha": "abc"}, {"served_model": ""}, {"basis": "cme5"}])
def test_writer_refuses_bad_identity(tmp_path, bad):
    with pytest.raises(cc.CaptureError):
        write(tmp_path, ident={**IDENT, **bad})
    with pytest.raises(cc.CaptureError):
        write(tmp_path, ident={k: v for k, v in IDENT.items() if k != "slots"})


def _mutate(side, fn, rehash=True):
    rows = [json.loads(l) for l in side.read_text().splitlines()]
    fn(rows)
    if rehash:
        for r in rows:
            cc.ns.seal(r)
    side.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def test_tampered_value_refused_even_when_rehashed(tmp_path):
    side = write(tmp_path)
    _mutate(side, lambda rows: rows[0].update(value=0.99))
    assert cc.native_rows(side) == ()


def test_tampered_counts_and_unsealed_edit_refused(tmp_path):
    side = write(tmp_path)
    _mutate(side, lambda rows: rows[2]["extra"]["counts"]["missed_split"].update(history_rewind=1))
    assert cc.native_rows(side) == ()
    side = write(tmp_path)
    _mutate(side, lambda rows: rows[0].update(claim="edited"), rehash=False)
    assert cc.native_rows(side) == ()


def test_foreign_row_and_nonempty_protocol_refused(tmp_path):
    side = write(tmp_path)
    _mutate(side, lambda rows: rows[0].update(schema="epyc.vidya.other.v1"))
    assert cc.native_rows(side) == ()
    side = write(tmp_path)
    _mutate(side, lambda rows: rows[0].update(protocol_id="P1"))
    assert cc.native_rows(side) == ()


def test_no_sidecar_zero_rows(tmp_path):
    assert cc.native_rows(tmp_path / cc.SIDECAR_NAME) == ()


def test_mutated_report_grades_down(tmp_path):
    side = write(tmp_path)
    before = [ct.grade(cc.project(n)) for n in cc.native_rows(side)]
    rp = tmp_path / "cache_hit_report.json"
    rp.write_text(rp.read_text() + "\n ")
    ts = [cc.project(n) for n in cc.native_rows(side)]
    assert all(t.attestation_present is False for t in ts)
    # the OBSERVATION cap (no protocol) already holds the grade at Judged/Located; a mutated attestation must at
    # least never rise above it and must read as absent (the sidecar's own hash check is the tamper gate)
    after = [ct.grade(t) for t in ts]
    assert all(a[:2] == ("Judged", "Located") for a in before + after)
