"""SC6 write half: a trial records the measurement constitution's claim tuple about itself.

MEASUREMENT_POLICY.md: a decision-gating number is (metric, protocol-id, n/reps, date,
attestation ref); a number without a protocol citation is an OBSERVATION and may never gate a
keep/revert/deploy decision. These tests pin that the tuple is captured at write time and, more
importantly, that a missing element is reported as missing rather than invented.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "autopilot"))

from experiment_journal import (  # noqa: E402
    ExperimentJournal,
    JournalEntry,
    measurement_tuple,
)


def entry(**over):
    base = dict(trial_id=1, timestamp="2026-08-12T10:00:00+00:00", species="s",
                action_type="numeric_trial", tier=1, quality=0.5, speed=1.0, cost=2.0,
                reliability=0.9, pareto_status="candidate")
    base.update(over)
    return JournalEntry(**base)


# --- capture ------------------------------------------------------------------------------

def test_protocol_id_composes_from_the_schema_versions_the_trial_knows():
    e = entry(metric_schema_version=1, harness_metrics={"schema_version": 2})
    assert measurement_tuple(e)["protocol_id"] == "autopilot/metric-v1+harness-v2"


def test_objective_policy_joins_the_protocol_id():
    e = entry(harness_metrics={"schema_version": 1},
              eval_details={"objective_policy_live": {"policy": "legacy_4d_v1"}})
    assert measurement_tuple(e)["protocol_id"].endswith("+legacy_4d_v1")


def test_date_is_the_calendar_day_of_the_trial():
    assert measurement_tuple(entry())["date"] == "2026-08-12"


def test_scored_denominator_wins_over_the_attempted_one():
    """n=50 attempted but 47 scored is n=47; claiming 50 overstates the sample."""
    e = entry(eval_details={"details": {"n_questions": 50, "n_scored": 47,
                                        "quality_denominator": 47}})
    t = measurement_tuple(e)
    assert t["reps"] == 47
    assert t["reps_basis"] == "scored:quality_denominator"


def test_legacy_total_is_used_but_labelled_attempted():
    """Older rows carry only `details.total`. Usable, but it is not a scored denominator.

    Recovering this key took the corpus from 46% to 86% full-tuple coverage — the first version of
    the extractor looked only at the modern keys and silently understated 545 real trials.
    """
    t = measurement_tuple(entry(eval_details={"details": {"total": 55, "correct": 33}}))
    assert t["reps"] == 55
    assert t["reps_basis"] == "attempted:total"


def test_config_snapshot_is_the_last_resort_for_reps():
    t = measurement_tuple(entry(config_snapshot={"n_questions": 12}))
    assert (t["reps"], t["reps_basis"]) == (12, "attempted:n_questions")


def test_zero_and_negative_denominators_are_not_reps():
    for det in ({"quality_denominator": 0}, {"total": -3}):
        assert measurement_tuple(entry(eval_details={"details": det}))["reps"] is None


# --- refusing to invent -------------------------------------------------------------------

def test_absent_elements_are_named_not_filled():
    """The load-bearing property: a gap must be visible, or it will be read as warrant."""
    t = measurement_tuple(entry(metric_schema_version=0))
    assert t["protocol_id"] == ""
    assert t["reps"] is None
    assert set(t["missing"]) == {"protocol_id", "reps"}


def test_a_complete_trial_reports_nothing_missing():
    e = entry(harness_metrics={"schema_version": 1},
              eval_details={"details": {"quality_denominator": 30}})
    assert "missing" not in measurement_tuple(e)


# --- the attestation digest ---------------------------------------------------------------

def test_digest_excludes_the_block_it_lives_in():
    """A hash covering its own container could never be recomputed, so it would attest to nothing."""
    e = entry()
    first = measurement_tuple(e)["attestation"]["sha256"]
    e.measurement = {"protocol_id": "x", "attestation": {"sha256": first}}
    assert measurement_tuple(e)["attestation"]["sha256"] == first


def test_distinct_trials_get_distinct_digests():
    a = measurement_tuple(entry(trial_id=1))["attestation"]["sha256"]
    b = measurement_tuple(entry(trial_id=2))["attestation"]["sha256"]
    assert a != b


def test_identical_content_is_stable_across_calls():
    assert (measurement_tuple(entry())["attestation"]["sha256"]
            == measurement_tuple(entry())["attestation"]["sha256"])


def test_a_changed_metric_changes_the_digest():
    a = measurement_tuple(entry(quality=0.5))["attestation"]["sha256"]
    b = measurement_tuple(entry(quality=0.6))["attestation"]["sha256"]
    assert a != b


# --- the write path -----------------------------------------------------------------------

def test_record_populates_the_tuple_and_it_survives_a_reload(tmp_path):
    j = ExperimentJournal(journal_dir=tmp_path)
    j.record(entry(harness_metrics={"schema_version": 1},
                   eval_details={"details": {"quality_denominator": 30}}))

    line = json.loads(next(tmp_path.glob("autopilot_journal*.jsonl")).read_text().splitlines()[0])
    assert line["measurement"]["protocol_id"] == "autopilot/metric-v1+harness-v1"
    assert line["measurement"]["reps"] == 30
    assert len(line["measurement"]["attestation"]["sha256"]) == 64
    assert line["measurement"]["attestation"]["locator"].endswith("#trial-1")

    reloaded = ExperimentJournal(journal_dir=tmp_path).all_entries()[0]
    assert reloaded.measurement == line["measurement"]


def test_a_caller_supplied_tuple_is_not_overwritten(tmp_path):
    j = ExperimentJournal(journal_dir=tmp_path)
    j.record(entry(measurement={"protocol_id": "hand-authored"}))
    line = json.loads(next(tmp_path.glob("autopilot_journal*.jsonl")).read_text().splitlines()[0])
    assert line["measurement"] == {"protocol_id": "hand-authored"}


def test_rows_written_before_the_hook_load_with_an_empty_tuple(tmp_path):
    """Back-filling a tuple on load would claim provenance the original run never recorded."""
    legacy = asdict(entry())
    legacy.pop("measurement")
    (tmp_path / "autopilot_journal.jsonl").write_text(json.dumps(legacy) + "\n")
    assert ExperimentJournal(journal_dir=tmp_path).all_entries()[0].measurement == {}


def test_capture_failure_records_itself_and_never_loses_the_trial(tmp_path, monkeypatch):
    """A provenance annotation that can drop a result is worse than one occasionally absent."""
    import experiment_journal as ej

    monkeypatch.setattr(ej, "measurement_tuple",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    j = ExperimentJournal(journal_dir=tmp_path)
    j.record(entry())
    line = json.loads(next(tmp_path.glob("autopilot_journal*.jsonl")).read_text().splitlines()[0])
    assert line["trial_id"] == 1
    assert "boom" in line["measurement"]["capture_error"]


def test_the_written_line_stays_strict_json(tmp_path):
    """D2: no bare NaN/Infinity may reach the file, tuple or not."""
    j = ExperimentJournal(journal_dir=tmp_path)
    j.record(entry(quality=float("nan"), eval_details={"details": {"total": 3}}))
    text = next(tmp_path.glob("autopilot_journal*.jsonl")).read_text()
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text.splitlines()[0])


@pytest.mark.parametrize("bad", [{"details": None}, {"details": []}, {}])
def test_malformed_eval_details_do_not_raise(bad):
    assert measurement_tuple(entry(eval_details=bad))["reps"] is None


# --- alignment with AutoKernel's claim_grammar --------------------------------------------

def test_vocabulary_matches_autokernels_claim_grammar():
    """One grammar across both loops, not two dialects of it.

    AutoKernel enforces MEASUREMENT.md:13 as a REQUIRED `claim_grammar` block. Its vocabulary is
    the reference; this test fails if the two drift apart.
    """
    t = measurement_tuple(entry())
    assert t["category"] in {"OPTIMUM", "BASELINE", "CANDIDATE"}
    assert set(t["metric_directions"].values()) <= {"higher_better", "lower_better"}


def test_a_trial_is_always_a_candidate():
    """Never the standing baseline, never a ratified optimum."""
    assert measurement_tuple(entry())["category"] == "CANDIDATE"


def test_cost_is_lower_better_despite_the_optimizer_maximizing_all_four():
    """The trap this pins: the study declares directions=["maximize"]*4, but over
    (quality, speed, -COST, reliability). The raw `cost` on the row is lower_better, and reading
    the maximize-list alone inverts it."""
    d = measurement_tuple(entry())["metric_directions"]
    assert d["cost"] == "lower_better"
    assert d["quality"] == d["speed"] == d["reliability"] == "higher_better"
