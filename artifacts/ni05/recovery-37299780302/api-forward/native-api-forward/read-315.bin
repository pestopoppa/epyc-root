"""EV-14e: the baseline a trial was judged against is RECORDED, not re-parsed from prose.

Before this, the incumbent value reached the journal only inside `failure_analysis`
("Quality regression: 1.744 vs baseline 1.884 …") and was read back out with
`_BASELINE_QUALITY_RE`. A regex over a sentence cannot say which tier reference,
which EV-14c revision, or which eval_quality era was compared — and writes nothing
at all when the gate PASSES. These tests pin the structured field, the one-way
resolution order (structured wins, legacy regex only as a marked fallback), and
that legacy shards still load with no pin.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "autopilot"))

from experiment_journal import (  # noqa: E402
    BASELINE_PIN_SOURCE_ABSENT,
    BASELINE_PIN_SOURCE_LEGACY_REGEX,
    BASELINE_PIN_SOURCE_STRUCTURED,
    ExperimentJournal,
    JournalEntry,
    baseline_pin_for,
    build_baseline_pin,
)
import experiment_journal as ej  # noqa: E402


def entry(**over):
    base = dict(
        trial_id=1,
        timestamp="2026-09-14T10:00:00+00:00",
        species="s",
        action_type="numeric_trial",
        tier=2,
        quality=1.44,
        speed=1.0,
        cost=2.0,
        reliability=0.9,
        pareto_status="candidate",
    )
    base.update(over)
    return JournalEntry(**base)


# --- build --------------------------------------------------------------------


def test_pin_records_reference_identity_and_the_delta_it_measured():
    pin = build_baseline_pin(
        tier=2,
        baseline_quality=1.524,
        candidate_quality=1.444,
        baseline_revision=7,
        eval_quality_era="E8",
        autopilot_speed_era="v9",
        per_suite_quality={"math": 1.9},
        per_suite_counts={"math": 50},
        baseline_path="/x/autopilot_baseline.yaml",
    )
    assert pin["source"] == BASELINE_PIN_SOURCE_STRUCTURED
    assert pin["tier"] == 2
    assert pin["baseline_quality"] == 1.524
    assert pin["baseline_revision"] == 7
    assert pin["eval_quality_era"] == "E8"
    assert pin["autopilot_speed_era"] == "v9"
    assert pin["per_suite_baseline_quality"] == {"math": 1.9}
    assert pin["per_suite_baseline_counts"] == {"math": 50}
    assert pin["delta"] == pytest.approx(1.444 - 1.524)
    assert pin["relative_delta"] == pytest.approx((1.444 - 1.524) / 1.524)
    assert pin["captured_at"]


def test_an_absent_reference_is_recorded_as_absent_not_as_zero():
    pin = build_baseline_pin(
        tier=1,
        baseline_quality=None,
        candidate_quality=1.2,
        suppressed_by="quality_rebaseline_hold",
    )
    assert pin["baseline_quality"] is None
    assert pin["delta"] is None
    assert pin["relative_delta"] is None
    assert pin["suppressed_by"] == "quality_rebaseline_hold"


def test_non_finite_values_never_reach_the_pin():
    pin = build_baseline_pin(
        tier=0, baseline_quality=float("nan"), candidate_quality=float("inf")
    )
    assert pin["baseline_quality"] is None
    assert pin["candidate_quality"] is None


# --- read ---------------------------------------------------------------------


def test_reader_prefers_the_structured_pin_over_prose(caplog):
    e = entry(
        baseline_pin=build_baseline_pin(
            tier=2, baseline_quality=1.524, candidate_quality=1.444, baseline_revision=3
        ),
        # Prose deliberately DISAGREES: the structured field must win outright.
        failure_analysis="Quality regression: 1.444 vs baseline 9.900 (-85%)",
    )
    pin = baseline_pin_for(e)
    assert pin["source"] == BASELINE_PIN_SOURCE_STRUCTURED
    assert pin["baseline_quality"] == 1.524
    assert pin["baseline_revision"] == 3
    assert "legacy baseline read" not in caplog.text


def test_reader_falls_back_to_the_regex_for_a_legacy_row_and_marks_it(caplog):
    ej._LEGACY_BASELINE_PIN_WARNED.clear()
    e = entry(
        trial_id=4242,
        baseline_pin={},
        failure_analysis="Quality regression: 1.444 vs baseline 1.524 (-5.2%)",
    )
    with caplog.at_level("WARNING"):
        pin = baseline_pin_for(e)
    assert pin["source"] == BASELINE_PIN_SOURCE_LEGACY_REGEX
    assert pin["baseline_quality"] == 1.524
    # The identity a regex can NEVER recover is reported as unrecorded.
    assert pin["tier"] is None
    assert pin["baseline_revision"] is None
    assert "EV-14e legacy baseline read" in caplog.text
    assert "4242" in caplog.text


def test_legacy_fallback_refuses_to_hand_back_a_corrupt_scale_baseline():
    ej._LEGACY_BASELINE_PIN_WARNED.clear()
    e = entry(
        trial_id=77,
        baseline_pin={},
        failure_analysis="Quality regression: 1.444 vs baseline 9.900 (-85%)",
    )
    pin = baseline_pin_for(e)
    assert pin["source"] == BASELINE_PIN_SOURCE_LEGACY_REGEX
    assert pin["legacy_scale_suspect"] is True
    assert pin["baseline_quality"] is None


def test_no_pin_and_no_prose_reports_absent_never_zero():
    e = entry(baseline_pin={}, failure_analysis="Throughput floor violation")
    pin = baseline_pin_for(e)
    assert pin["source"] == BASELINE_PIN_SOURCE_ABSENT
    assert pin["baseline_quality"] is None


# --- persistence / backward compatibility ------------------------------------


def test_pin_round_trips_through_the_journal(tmp_path):
    journal = ExperimentJournal(journal_dir=tmp_path)
    pin = build_baseline_pin(
        tier=2, baseline_quality=1.5, candidate_quality=1.6, baseline_revision=9
    )
    journal.record(entry(trial_id=1, baseline_pin=pin))

    row = json.loads((tmp_path / "autopilot_journal.jsonl").read_text().splitlines()[0])
    assert row["baseline_pin"]["baseline_revision"] == 9

    reloaded = ExperimentJournal(journal_dir=tmp_path).all_entries()[0]
    assert baseline_pin_for(reloaded)["source"] == BASELINE_PIN_SOURCE_STRUCTURED
    assert baseline_pin_for(reloaded)["baseline_quality"] == 1.5


def test_a_legacy_shard_without_the_field_still_loads(tmp_path):
    ej._LEGACY_BASELINE_PIN_WARNED.clear()
    legacy = {
        "trial_id": 3,
        "timestamp": "2026-06-01T00:00:00+00:00",
        "species": "s",
        "action_type": "numeric_trial",
        "tier": 1,
        "quality": 1.744,
        "speed": 1.0,
        "cost": 2.0,
        "reliability": 0.9,
        "pareto_status": "dominated",
        "failure_analysis": "Quality regression: 1.744 vs baseline 1.884 (-7.4%)",
    }
    (tmp_path / "autopilot_journal.jsonl").write_text(json.dumps(legacy) + "\n")

    entries = ExperimentJournal(journal_dir=tmp_path).all_entries()
    assert len(entries) == 1
    assert entries[0].baseline_pin == {}  # never back-filled on load
    pin = baseline_pin_for(entries[0])
    assert pin["source"] == BASELINE_PIN_SOURCE_LEGACY_REGEX
    assert pin["baseline_quality"] == 1.884


class _Gate:
    def __init__(self, baseline, hold=False):
        self.baseline = baseline
        self.quality_rebaseline_required = hold


class _Result:
    def __init__(self, tier=2, quality=1.44):
        self.tier = tier
        self.quality = quality


def test_autopilot_pin_capture_reads_the_live_gate_reference():
    import autopilot  # noqa: E402
    from safety_gate import Baseline  # noqa: E402

    baseline = Baseline(baselines_by_tier={2: 1.524}, eval_quality_era="E8")
    pin = autopilot._baseline_pin_for_trial(_Gate(baseline), _Result())
    assert pin["baseline_quality"] == 1.524
    assert pin["eval_quality_era"] == "E8"
    assert pin["tier"] == 2
    assert pin["candidate_quality"] == 1.44
    assert pin["suppressed_by"] == ""
    # pin_tier(register=False): capturing provenance must not register a
    # measurement window that update_tier would then report against.
    assert baseline.pins_for_tier(2) == ()


def test_autopilot_pin_capture_mirrors_the_rebaseline_hold():
    """Under the hold the gate forces baseline_q=None — the pin must say so."""
    import autopilot  # noqa: E402
    from safety_gate import Baseline  # noqa: E402

    baseline = Baseline(baselines_by_tier={2: 1.524}, eval_quality_era="E8")
    pin = autopilot._baseline_pin_for_trial(_Gate(baseline, hold=True), _Result())
    assert pin["baseline_quality"] is None
    assert pin["delta"] is None
    assert pin["suppressed_by"] == "quality_rebaseline_hold"


def test_autopilot_pin_capture_names_a_missing_same_tier_reference():
    import autopilot  # noqa: E402
    from safety_gate import Baseline  # noqa: E402

    baseline = Baseline(baselines_by_tier={})
    pin = autopilot._baseline_pin_for_trial(_Gate(baseline), _Result(tier=3))
    assert pin["baseline_quality"] is None
    assert pin["suppressed_by"] == "no_same_tier_baseline"


def test_autopilot_pin_capture_records_the_ev14c_revision():
    import autopilot  # noqa: E402
    from safety_gate import Baseline  # noqa: E402

    baseline = Baseline(baselines_by_tier={2: 1.5}, tier_revisions={2: 11})
    pin = autopilot._baseline_pin_for_trial(_Gate(baseline), _Result())
    assert pin["baseline_revision"] == 11


def test_autopilot_pin_capture_never_fails_a_trial():
    import autopilot  # noqa: E402

    class _Broken:
        @property
        def baseline(self):
            raise RuntimeError("boom")

    pin = autopilot._baseline_pin_for_trial(_Broken(), _Result())
    assert pin["source"] == "capture_error"
