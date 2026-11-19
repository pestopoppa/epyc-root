"""Offline tests for frozen task custody and the independent grading cohort."""

import json
import sys
from collections import Counter
from itertools import groupby

import prepare


def test_source_inventory_preserves_all_frozen_cases():
    prepare.verify_source()
    cases, inventory = prepare.source_corpus()
    raw = {
        row["id"]: row
        for line in (prepare.SOURCE / prepare.POOL).read_text().splitlines()
        if "id" in (row := json.loads(line))
    }
    assert len(raw) == len(inventory) == 50
    assert {row["id"] for row in inventory} == set(raw)
    assert {case["id"]: case for case in cases} == {
        task_id: task for task_id, task in raw.items() if not task.get("image_path")
    }
    assert Counter(row["grade_reason"] for row in inventory) == {
        None: 29,
        "substring_proxy_outside_accuracy_cohort": 12,
        "bounded_code_grader_unavailable": 4,
        "external_judge_unavailable": 3,
        "image_input_outside_text_frontdoor": 2,
    }
    for row in inventory:
        assert row["grade_cohort"] == (row["grade_reason"] is None)
        assert row["scheduled"] == (not bool(raw[row["id"]].get("image_path")))
        if row["grade_cohort"]:
            assert row["scoring_method"] in prepare.LOCAL_GRADERS


def test_schedule_reproducible_contiguous_paired_and_exhaustive():
    cases, _ = prepare.source_corpus()
    schedule = prepare.paired_schedule(cases)
    assert schedule == prepare.paired_schedule(cases)
    assert len(schedule["coverage"]) == 24
    assert len(schedule["full"]) == 4 * 48 * 6
    assert schedule["coverage"] == schedule["full"][:24]
    assert [row["ordinal"] for row in schedule["full"]] == list(range(4 * 48 * 6))
    assert len({row["unit"] for row in schedule["full"]}) == len(schedule["full"])
    assert list(dict.fromkeys(row["case"] for row in schedule["coverage"])) == list(
        prepare.COVERAGE_CASES
    )
    assert len({row["suite"] for row in cases[:4]}) == 4
    seeds = set()
    orders = set()
    pairs = set()
    for pair, rows in groupby(schedule["full"], key=lambda row: row["pair"]):
        group = list(rows)
        first = group[0]
        assert all(
            row["seed"] == first["seed"]
            and row["case"] == first["case"]
            and row["repeat"] == first["repeat"]
            and row["unit"] == f"{pair}/{row['arm']}"
            for row in group
        )
        assert Counter(row["arm"] for row in group) == dict.fromkeys(prepare.ARMS, 1)
        assert first["seed"] not in seeds and first["seed"] > 0
        seeds.add(first["seed"])
        orders.add(tuple(row["arm"] for row in group))
        pairs.add((first["case"], first["repeat"]))
    assert len(orders) > 1
    assert pairs == {
        (case["id"], repeat) for case in cases for repeat in range(prepare.FULL_REPEATS)
    }


def test_pinned_local_grader_passes_gold_and_rejects_decoys(monkeypatch):
    monkeypatch.syspath_prepend(str(prepare.SOURCE))
    monkeypatch.syspath_prepend(str(prepare.SOURCE / "scripts/benchmark"))
    from scripts.benchmark.seeding_scoring import score_answer_or_error

    cases, inventory = prepare.source_corpus()
    gradeable = {row["id"] for row in inventory if row["grade_cohort"]}
    for case in cases:
        if case["id"] not in gradeable:
            continue
        method = case["scoring_method"]
        expected = case["expected"]
        config = case.get("scoring_config")
        gold, decoy = str(expected), "__off_task_decoy__"
        if method == "programmatic":
            gold = "- North\n- South\n- East\n- West"
            decoy = "- North"
        elif method == "structural_exact_match":
            gold = f"SOLUTION = {expected}"
            decoy = "SOLUTION = [999]"
        elif method == "multiple_choice":
            choices = (config or {}).get("choices", ["A", "B", "C", "D"])
            decoy = next(choice for choice in choices if choice != expected)
        assert score_answer_or_error(gold, expected, method, config) == (True, None), (
            case["id"]
        )
        assert score_answer_or_error(decoy, expected, method, config) == (
            False,
            None,
        ), case["id"]

    scorer = sys.modules["epyc_orch_debug_scorer"]
    assert scorer.__file__.startswith(str(prepare.SOURCE))
