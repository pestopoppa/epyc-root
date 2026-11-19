import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".claude/skills/kernel-promotion/scripts/resident_plan.py"
)
SPEC = importlib.util.spec_from_file_location("resident_plan", SCRIPT)
resident_plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resident_plan)


def _cohort(scenario="cpu-role", nominal_context=4096, **body_changes):
    return {
        "scenario": scenario,
        "nominal_context": nominal_context,
        "request_body": {
            "prompt": "Measure a paired request.",
            "n_predict": 256,
            "temperature": 0,
            "seed": 35,
            "cache_prompt": False,
            **body_changes,
        },
    }


def _digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _requests(plan):
    return [row for cohort in plan["cohorts"] for row in cohort["requests"]]


def test_schedule_counts_keys_and_alternating_order():
    cohorts = [_cohort(), _cohort(nominal_context=8192), _cohort("other-role")]
    plan = resident_plan.build_plan(cohorts)

    for cohort, first, second in zip(
        plan["cohorts"],
        ("production", "candidate", "production"),
        ("candidate", "production", "candidate"),
    ):
        rows = cohort["requests"]
        assert [row["arm"] for row in rows] == [first, second, second, first] * 5
        assert Counter(row["arm"] for row in rows) == {"production": 10, "candidate": 10}
        assert [row["pair_index"] for row in rows] == [pair for pair in range(10) for _ in range(2)]
        assert [row["schedule_position"] for row in rows] == list(range(20))
        assert len({row["request_sha256"] for row in rows}) == 1
        assert rows[0]["request_sha256"] == _digest(cohort["request_body"])
        assert cohort["warmups"] == [
            {"arm": arm, "excluded": True, "request_overrides": {"n_predict": 64}}
            for arm in ("production", "candidate")
        ]

    rows = _requests(plan)
    assert len({
        (row["scenario"], row["nominal_context"], row["pair_index"], row["schedule_position"])
        for row in rows
    }) == len(rows) == 60
    assert plan["schema"] == "epyc.kernel_promotion_resident_plan.v1"
    assert plan["status"] == "observation_only"
    assert plan["schedule_sha256"] == _digest(rows)
    resident_plan.validate_plan(plan)


def test_stable_hash_and_detached_chat_body():
    chat_body = {
        "messages": [{"role": "user", "content": "Same chat prompt"}],
        "max_tokens": 256,
        "temperature": 0,
        "seed": 35,
        "cache_prompt": False,
    }
    chat = {**_cohort(), "request_body": chat_body}
    reversed_keys = {**chat, "request_body": dict(reversed(tuple(chat_body.items())))}
    plan = resident_plan.build_plan([chat])
    assert plan == resident_plan.build_plan([reversed_keys])
    resident_plan.validate_plan(json.loads(json.dumps(plan)))

    chat_body["messages"][0]["content"] = "Changed input"
    cohort = plan["cohorts"][0]
    assert cohort["request_body"]["messages"][0]["content"] == "Same chat prompt"
    assert cohort["warmups"][0]["request_overrides"] == {"max_tokens": 64}
    assert plan["schedule_sha256"] != resident_plan.build_plan([chat])["schedule_sha256"]


@pytest.mark.parametrize(
    ("cohorts", "error"),
    [
        ([], "nonempty JSON array"),
        ({"cohorts": [_cohort()]}, "nonempty JSON array"),
        ([{"scenario": "cpu-role"}], "each cohort requires exactly"),
        ([_cohort(), _cohort(seed=9)], "duplicate cohort"),
        ([_cohort(scenario=" ")], "scenario"),
        ([_cohort(nominal_context=True)], "nominal_context"),
        ([_cohort(nominal_context=0)], "nominal_context"),
        ([_cohort(cache_prompt=True)], "cache_prompt"),
        ([_cohort(cache_prompt=0)], "cache_prompt"),
        ([_cohort(temperature=0.2)], "temperature"),
        ([_cohort(temperature=False)], "temperature"),
        ([_cohort(seed=-1)], "fixed seed"),
        ([_cohort(seed=2**32 - 1)], "fixed seed"),
        ([_cohort(seed=True)], "fixed seed"),
        ([_cohort(n_predict=0)], "n_predict"),
        ([_cohort(messages=[])], "either prompt/n_predict or messages/max_tokens"),
        ([_cohort(prompt="")], "completion prompt"),
        ([_cohort(extra={"nested": [float("nan")]})], "finite JSON"),
        ([_cohort(extra={"nested": [float("inf")]})], "finite JSON"),
    ],
)
def test_invalid_cohorts(cohorts, error):
    with pytest.raises(ValueError, match=error):
        resident_plan.build_plan(cohorts)


@pytest.mark.parametrize(
    ("field", "value"),
    [("arm", "candidate"), ("pair_index", 1), ("schedule_position", 1), ("request_sha256", "0" * 64)],
)
def test_rehashed_schedule_mutations_fail_validation(field, value):
    plan = resident_plan.build_plan([_cohort()])
    rows = _requests(plan)
    rows[0][field] = value
    plan["schedule_sha256"] = _digest(rows)
    with pytest.raises(ValueError, match="canonical resident schedule"):
        resident_plan.validate_plan(plan)


def test_hash_preserving_mutations_fail_validation():
    plan = resident_plan.build_plan([_cohort()])
    cohort = plan["cohorts"][0]
    for mutation in (
        {**plan, "schema": "epyc.kernel_promotion_resident_plan.v2"},
        {**plan, "status": "decision_eligible"},
        {**plan, "protocol": "P-BENCH-4"},
        {**plan, "cohorts": [{**cohort, "requests": cohort["requests"][1:]}]},
        {**plan, "cohorts": [{**cohort, "warmups": []}]},
        {**plan, "cohorts": [{**cohort, "request_body": {**cohort["request_body"], "seed": 9}}]},
    ):
        with pytest.raises(ValueError, match="canonical resident schedule"):
            resident_plan.validate_plan(mutation)


def test_cli_generates_identical_observation_only_files(tmp_path):
    cohorts = tmp_path / "cohorts.json"
    cohorts.write_text(json.dumps([_cohort()]), encoding="utf-8")
    outputs = [tmp_path / "first.json", tmp_path / "second.json"]
    for output in outputs:
        subprocess.run(
            [sys.executable, str(SCRIPT), "--cohorts", str(cohorts), "--out", str(output)],
            check=True,
        )
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    resident_plan.validate_plan(json.loads(outputs[0].read_bytes()))


def test_cli_rejects_duplicate_json_fields_without_creating_output(tmp_path):
    cohorts = tmp_path / "cohorts.json"
    cohorts.write_text('[{"scenario":"one","scenario":"two"}]', encoding="utf-8")
    output = tmp_path / "plan.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--cohorts", str(cohorts), "--out", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "duplicate JSON field: scenario" in completed.stderr
    assert not output.exists()
