"""The eval instrument's identity must survive a daemon restart.

Origin (2026-08-04): `_DATASET_SHA_BY_CORE_ID` was a module-level dict, so drift was only
detectable WITHIN one process. The drift that matters happens while the daemon is DOWN —
that day the debugbench python rows were retargeted `code_execution` -> `substring` in the
question pool, the daemon restarted, and the changed instrument was accepted silently.
`core_id` cannot express the difference: it is `legacy_pool_seed_{seed}_n{n}`, identical
for two different pools.

This matters more now that the Pareto objective is questions/HOUR — the drawn set's tier
mix drives wall-clock directly, so a pool edit moves the objective with no config change.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ORCH_ROOT = Path(__file__).resolve().parents[2]


def _load_eval_tower(ledger_path: Path):
    """Import eval_tower with the ledger pointed at a temp file (fresh module each time)."""
    import os

    os.environ["AUTOPILOT_EVAL_INSTRUMENT_LEDGER"] = str(ledger_path)
    sys.modules.pop("eval_tower", None)
    sys.path.insert(0, str(ORCH_ROOT / "scripts" / "autopilot"))
    spec = importlib.util.spec_from_file_location(
        "eval_tower", ORCH_ROOT / "scripts" / "autopilot" / "eval_tower.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["eval_tower"] = mod
    spec.loader.exec_module(mod)
    return mod


def _q(suite, tier, prompt, expected="a", method="substring"):
    return {
        "suite": suite,
        "id": f"{suite}-{prompt}",
        "tier": tier,
        "prompt": prompt,
        "expected": expected,
        "scoring_method": method,
        "scoring_config": {},
    }


@pytest.fixture
def et(tmp_path):
    return _load_eval_tower(tmp_path / "ledger.json")


def test_tier_mix_is_recorded_not_assumed(et):
    """The sampler stratifies by suite, never by tier — so the mix must be measured."""
    questions = [_q("a", 1, "p1"), _q("b", 2, "p2"), _q("c", 2, "p3"), _q("d", 3, "p4")]
    assert et.question_tier_mix(questions) == {"1": 1, "2": 2, "3": 1}


def test_tier_mix_marks_untiered_rows_rather_than_dropping_them(et):
    """A row with no tier is not tier 0 and not absent — it is unknown."""
    questions = [_q("a", 1, "p1"), {"suite": "x", "prompt": "p", "expected": "y"}]
    mix = et.question_tier_mix(questions)
    assert mix == {"1": 1, "unknown": 1}
    assert sum(mix.values()) == len(questions)


def test_drift_is_detected_across_a_simulated_restart(tmp_path):
    """The whole point: a pool edit between daemon runs must NOT pass silently."""
    ledger = tmp_path / "ledger.json"
    core_id = "legacy_pool_seed_42_n2"

    et1 = _load_eval_tower(ledger)
    before = [_q("a", 1, "p1"), _q("b", 2, "p2")]
    assert et1._record_instrument_identity(
        core_id, et1.dataset_content_sha256(before), et1.question_tier_mix(before), len(before)
    ) is None, "first sighting is not drift"

    # Daemon restart: brand-new process, in-memory ledger is empty again.
    et2 = _load_eval_tower(ledger)
    assert et2._DATASET_SHA_BY_CORE_ID == {}, "in-memory ledger must not survive; that is the bug"

    # Same core_id, different scoring oracle — exactly the debugbench retarget.
    after = [_q("a", 1, "p1"), _q("b", 2, "p2", method="code_execution")]
    drift = et2._record_instrument_identity(
        core_id, et2.dataset_content_sha256(after), et2.question_tier_mix(after), len(after)
    )
    assert drift is not None, "a changed pool under an unchanged core_id must be flagged"
    assert drift["detected_across_restart"] is True
    assert drift["previous_dataset_content_sha256"] != drift["current_dataset_content_sha256"]


def test_a_tier_mix_change_is_carried_in_the_drift_report(tmp_path):
    """Under a questions/hour objective the mix change IS the material fact."""
    ledger = tmp_path / "ledger.json"
    core_id = "legacy_pool_seed_42_n3"

    et1 = _load_eval_tower(ledger)
    t1_heavy = [_q("a", 1, "p1"), _q("b", 1, "p2"), _q("c", 1, "p3")]
    et1._record_instrument_identity(
        core_id, et1.dataset_content_sha256(t1_heavy), et1.question_tier_mix(t1_heavy), 3
    )

    et2 = _load_eval_tower(ledger)
    t3_heavy = [_q("a", 3, "p1"), _q("b", 3, "p2"), _q("c", 3, "p3")]
    drift = et2._record_instrument_identity(
        core_id, et2.dataset_content_sha256(t3_heavy), et2.question_tier_mix(t3_heavy), 3
    )
    assert drift is not None
    assert drift["previous_tier_mix"] == {"1": 3}
    assert drift["current_tier_mix"] == {"3": 3}


def test_unchanged_pool_does_not_cry_drift(tmp_path):
    """A false positive here would train the operator to ignore the alarm."""
    ledger = tmp_path / "ledger.json"
    core_id = "legacy_pool_seed_42_n2"
    questions = [_q("a", 1, "p1"), _q("b", 2, "p2")]

    for _ in range(3):
        et = _load_eval_tower(ledger)  # restart each time
        drift = et._record_instrument_identity(
            core_id,
            et.dataset_content_sha256(questions),
            et.question_tier_mix(questions),
            len(questions),
        )
        if drift is not None:
            pytest.fail(f"unchanged instrument reported drift: {drift}")


def test_corrupt_ledger_degrades_loudly_and_does_not_break_the_eval(tmp_path, caplog):
    """A detector that quietly degrades to 'no drift' is worse than no detector."""
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{ this is not json")
    et = _load_eval_tower(ledger)

    with caplog.at_level("ERROR"):
        drift = et._record_instrument_identity("core", "sha", {"1": 1}, 1)

    assert drift is None  # cannot compare against an unreadable prior
    assert any("DEGRADED" in r.message or "unreadable" in r.message for r in caplog.records), \
        "silent degradation is the failure mode this guards against"
    # And it must have recovered the ledger rather than staying broken forever.
    assert "core" in et._read_instrument_ledger()


def test_ledger_write_is_atomic_leaving_no_partial_file(tmp_path):
    """Concurrent evals share this file; a torn write would poison drift detection."""
    ledger = tmp_path / "ledger.json"
    et = _load_eval_tower(ledger)
    for i in range(5):
        et._record_instrument_identity(f"core-{i}", f"sha-{i}", {"1": i}, i)
    assert not list(tmp_path.glob("*.tmp")), "temp file must be renamed, not left behind"
    assert len(et._read_instrument_ledger()) == 5
