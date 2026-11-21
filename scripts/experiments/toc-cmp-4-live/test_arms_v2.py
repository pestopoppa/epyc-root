import pytest

import analysis
from arms_v2 import REGISTRY, prefix_reuse, prefix_reuse_by_arm, resolve_arms
from runner import summarize_ledger  # noqa: F401  (the runner imports the v2 tally)


def test_new_arm_names_are_accepted_and_blocked_one_refused():
    assert resolve_arms(("summary_only", "persistence_floor", "prose_only_frozen_append"))
    with pytest.raises(ValueError, match="kv-prefix-fork P1"):
        resolve_arms(("summary_only", "async_compaction_next_k_judge"))
    with pytest.raises(ValueError, match="unknown arm"):
        resolve_arms(("summary_only", "fifo"))
    with pytest.raises(ValueError):
        resolve_arms(("summary_only", "summary_only"))
    assert REGISTRY["async_compaction_next_k_judge"][0] == "blocked"


def runs_for(arms, points=("p1", "p2"), repeats=2):
    out = []
    for p in points:
        for a_i, arm in enumerate(arms):
            for r in range(repeats):
                out.append({"point_id": p, "stratum": "early", "arm": arm, "repeat": r, "valid": True,
                            "baps": 0.2 * a_i + 0.1 * r, "correct": None, "wall_s": 10.0})
    return out


def test_analysis_runs_on_a_v2_arm_set_and_default_is_unchanged():
    arms = resolve_arms(("summary_only", "persistence_floor", "prose_only_frozen_append"))
    runs = runs_for(arms)
    with pytest.raises(ValueError):  # default arm triple rejects the new names
        analysis.analyze(runs, "pilot")
    # pilot needs 8 points x 4 repeats; the confirmatory shape is exercised by the existing suite
    rows = runs_for(arms, points=tuple(f"p{i}" for i in range(8)), repeats=4)
    rep = analysis.analyze(rows, "pilot", arms=arms)
    assert set(rep["paired_difference_sd"]) == {"summary_only - persistence_floor",
                                                "summary_only - prose_only_frozen_append",
                                                "persistence_floor - prose_only_frozen_append"}


def test_four_arm_set_has_six_contrasts():
    arms = ("summary_only", "pointer_only", "prune_pointer", "persistence_floor")
    rows = runs_for(arms, points=tuple(f"p{i}" for i in range(8)), repeats=4)
    assert len(analysis.analyze(rows, "pilot", arms=arms)["paired_difference_sd"]) == 6


def turn(n, prompt, cached):
    return {"event": "turn", "turn": n, "prompt_tokens": prompt, "cached_prompt_tokens": cached}


def test_prefix_reuse_token_weighted_all_and_post_boundary_with_unobserved_turns():
    ev = [turn(1, 1000, 0), turn(2, 1100, 1000), {"event": "boundary", "turn": 3},
          turn(3, 400, 100), turn(4, 450, 300), {"event": "turn", "turn": 5, "prompt_tokens": None,
                                                 "cached_prompt_tokens": None}, {"event": "final"}]
    r = prefix_reuse(ev, boundary_turn=2)
    assert r["all_turns"]["prompt_tokens"] == 2950 and r["all_turns"]["cached_prompt_tokens"] == 1400
    assert r["all_turns"]["unobserved_turns"] == 1
    assert r["post_boundary"]["reuse"] == pytest.approx(400 / 850)
    assert prefix_reuse([], 1)["all_turns"]["reuse"] is None  # zero observed is None, never 0


def test_prefix_reuse_by_arm_excludes_voided_points():
    a = {"arm": "summary_only", "void_point": False, "prefix_reuse": prefix_reuse([turn(1, 100, 50)], 0)}
    b = {"arm": "summary_only", "void_point": False, "prefix_reuse": prefix_reuse([turn(1, 100, 100)], 0)}
    c = {"arm": "pointer_only", "void_point": True, "prefix_reuse": prefix_reuse([turn(1, 100, 0)], 0)}
    agg = prefix_reuse_by_arm([a, b, c])
    assert agg["summary_only"]["all_turns"]["reuse"] == 0.75 and "pointer_only" not in agg
