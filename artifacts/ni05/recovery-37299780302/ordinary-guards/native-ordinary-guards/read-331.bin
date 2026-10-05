"""The eval draw honours a DECLARED tier mix (operator decision 2026-08-04: equal thirds).

Before this, the sampler stratified by SUITE only (`per_suite = n // len(suites)`), so the
difficulty mix was a byproduct: the real seed-42 n=50 draw came out T1:24 / T2:15 / T3:11 —
T1-heavy — and it moved with n or with any edit to the question pool. Under the
questions/hour Pareto objective that is load-bearing, because T2/T3 questions cost far more
wall-clock than T1: a pool edit could move the objective with no config change at all.
"""
from __future__ import annotations

import importlib.util
import os
import random
import sys
from pathlib import Path

import pytest

ORCH_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def et(tmp_path):
    os.environ["AUTOPILOT_EVAL_INSTRUMENT_LEDGER"] = str(tmp_path / "ledger.json")
    sys.modules.pop("eval_tower", None)
    sys.path.insert(0, str(ORCH_ROOT / "scripts" / "autopilot"))
    spec = importlib.util.spec_from_file_location(
        "eval_tower", ORCH_ROOT / "scripts" / "autopilot" / "eval_tower.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["eval_tower"] = mod
    spec.loader.exec_module(mod)
    return mod


def _pool(per_suite_per_tier=20, suites=("alpha", "beta", "gamma"), tiers=(1, 2, 3)):
    return {
        s: [
            {
                "suite": s,
                "id": f"{s}-{t}-{i}",
                "tier": t,
                "prompt": f"{s}-{t}-{i}",
                "expected": "x",
                "scoring_method": "substring",
                "scoring_config": {},
            }
            for t in tiers
            for i in range(per_suite_per_tier)
        ]
        for s in suites
    }


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 49, 50, 65, 100, 101])
def test_targets_always_sum_to_n(et, n):
    """An off-by-one silently changes the questions/hour denominator."""
    assert sum(et.declared_tier_targets(n).values()) == n


def test_targets_are_equal_thirds_within_one(et):
    """Derived from the declared policy, not a restated literal."""
    targets = et.declared_tier_targets(50)
    assert set(targets) == set(et.EVAL_TIER_MIX_TIERS)
    assert max(targets.values()) - min(targets.values()) <= 1


def test_realized_mix_matches_the_declared_targets(et):
    questions, prov = et._sample_tier_stratified_eval_questions(_pool(), 50, random.Random(42))
    mix = et.question_tier_mix(questions)
    assert mix == {str(k): v for k, v in et.declared_tier_targets(50).items()}
    assert prov["tier_mix_shortfalls"] == {}
    assert prov["drawn_n"] == 50


def test_draw_is_deterministic_for_a_given_seed(et):
    a, _ = et._sample_tier_stratified_eval_questions(_pool(), 50, random.Random(42))
    b, _ = et._sample_tier_stratified_eval_questions(_pool(), 50, random.Random(42))
    assert et.dataset_content_sha256(a) == et.dataset_content_sha256(b)


def test_suite_diversity_is_preserved_inside_each_tier(et):
    """Stratifying by tier must not collapse the draw onto one suite."""
    questions, _ = et._sample_tier_stratified_eval_questions(_pool(), 30, random.Random(7))
    by_tier: dict = {}
    for q in questions:
        by_tier.setdefault(q["tier"], set()).add(q["suite"])
    for tier, suites in by_tier.items():
        assert len(suites) > 1, f"tier {tier} drew from only {suites}"


def test_a_starved_tier_is_reported_and_never_backfilled_from_another(et):
    """Backfilling would report the declared mix while drawing a different one."""
    starved = _pool(per_suite_per_tier=2, suites=("alpha",), tiers=(1, 2))
    starved["alpha"] += [
        {
            "suite": "alpha",
            "id": "alpha-3-0",
            "tier": 3,
            "prompt": "alpha-3-0",
            "expected": "x",
            "scoring_method": "substring",
            "scoring_config": {},
        }
    ]
    questions, prov = et._sample_tier_stratified_eval_questions(starved, 30, random.Random(1))
    mix = et.question_tier_mix(questions)

    assert prov["tier_mix_shortfalls"], "a starved tier must be reported"
    assert "3" in prov["tier_mix_shortfalls"]
    # The one available T3 row was used, and NOT topped up from tier 1 or 2.
    assert mix.get("3", 0) == 1
    assert prov["drawn_n"] == len(questions) < 30
    for tier, target in et.declared_tier_targets(30).items():
        assert mix.get(str(tier), 0) <= target, "no tier may exceed its declared target"


def test_no_question_is_drawn_twice_across_tiers(et):
    questions, _ = et._sample_tier_stratified_eval_questions(_pool(), 45, random.Random(3))
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))


def test_new_sampler_is_a_different_instrument_than_the_suite_only_one(et):
    """Same seed and n, different question set — so the core_id must not be reused."""
    pool = _pool()
    old = et._sample_scoreable_eval_questions(pool, 50, random.Random(42))
    new, _ = et._sample_tier_stratified_eval_questions(pool, 50, random.Random(42))
    assert et.dataset_content_sha256(old) != et.dataset_content_sha256(new)


def test_rotation_is_fixed_within_a_block(et):
    """The ratchet needs a stable instrument to compare trials against."""
    period = et.EVAL_CORE_ROTATION_TRIALS
    assert et.core_rotation_index(0) == et.core_rotation_index(period - 1)
    seed_first = et.rotated_core_seed(42, et.core_rotation_index(0))
    seed_last = et.rotated_core_seed(42, et.core_rotation_index(period - 1))
    assert seed_first == seed_last


def test_rotation_changes_across_blocks(et):
    """A permanently fixed seed lets the optimizer overfit one question set."""
    period = et.EVAL_CORE_ROTATION_TRIALS
    assert et.core_rotation_index(period) == et.core_rotation_index(0) + 1
    assert et.rotated_core_seed(42, 0) != et.rotated_core_seed(42, 1)


def test_consecutive_rotations_are_not_adjacent_seeds(et):
    """`base_seed + rotation` would make block N+1 the seed-43 draw of block N."""
    seeds = [et.rotated_core_seed(42, r) for r in range(5)]
    assert len(set(seeds)) == len(seeds)
    for a, b in zip(seeds, seeds[1:]):
        assert abs(a - b) > 1


def test_rotation_preserves_the_declared_mix_so_difficulty_is_unchanged(et):
    """Rotation must change WHICH questions, never how hard the instrument is.

    n, tier mix and pool are all held constant across a rotation, so expected difficulty
    is unchanged and the quality baseline stays valid — unlike changing the mix itself.
    """
    pool = _pool(per_suite_per_tier=40)
    targets = {str(k): v for k, v in et.declared_tier_targets(30).items()}
    for rotation in range(4):
        seed = et.rotated_core_seed(42, rotation)
        questions, prov = et._sample_tier_stratified_eval_questions(
            pool, 30, random.Random(seed)
        )
        assert et.question_tier_mix(questions) == targets
        assert prov["tier_mix_shortfalls"] == {}


def test_rotation_actually_draws_different_questions(et):
    """Guards the failure where a 'rotation' returns the same set under a new label."""
    pool = _pool(per_suite_per_tier=60)
    sets = []
    for rotation in range(3):
        seed = et.rotated_core_seed(42, rotation)
        questions, _ = et._sample_tier_stratified_eval_questions(
            pool, 30, random.Random(seed)
        )
        sets.append({q["id"] for q in questions})
    for a, b in zip(sets, sets[1:]):
        assert a != b, "a rotation that redraws the same questions is not a rotation"


def test_unknown_trial_id_is_deterministic_not_random(et):
    """A missing trial_id must not silently randomize the instrument."""
    assert et.core_rotation_index(None) == 0
    assert et.core_rotation_index(-5) == 0


def test_untiered_rows_cannot_satisfy_a_tier_target(et):
    """A row with no tier is unknown, not a free substitute for a declared tier."""
    pool = {
        "alpha": [
            {
                "suite": "alpha",
                "id": f"u{i}",
                "prompt": f"u{i}",
                "expected": "x",
                "scoring_method": "substring",
                "scoring_config": {},
            }
            for i in range(50)
        ]
    }
    questions, prov = et._sample_tier_stratified_eval_questions(pool, 9, random.Random(5))
    assert questions == []
    assert set(prov["tier_mix_shortfalls"]) == {"1", "2", "3"}
