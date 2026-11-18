"""Offline checks for the sealed active-evidence intervention."""
import json
from copy import deepcopy

import pytest
import runner
from jinja2 import Environment

EXPECTED = {
    "old-deep": (True, False, False, False, False, True),
    "old-head": (True, False, False, False, True, True),
    "old-reasoning": (True, True, True, True, True, False),
}


@pytest.fixture(scope="module")
def sealed():
    return runner.verify()


def test_paired_schedule(sealed):
    _, policies, _, cases, rows = sealed
    assert len(rows) == len({row["unit"] for row in rows}) == 18
    for index, case in enumerate(cases.values()):
        paired = [row for row in rows if row["case"] == case["id"]]
        assert (case["steps"], case["target"]) == (10, 2)
        assert {row["seed"] for row in paired} == {case["seed"]}
        assert tuple(row["arm"] for row in paired) == policies.ARMS[index:] + policies.ARMS[:index]


@pytest.mark.parametrize("case_id", EXPECTED)
def test_full_exposure_matrix_and_pinned_template(sealed, case_id):
    _, policies, _, cases, _ = sealed
    case = cases[case_id]
    original = policies.make_messages(case)
    untouched = deepcopy(original)
    answer = case["answer"]
    assert len(original) == 23
    assert json.dumps(original).count(answer) == 1
    assert answer not in json.dumps([*original[:2], original[-1]])
    if case_id == "old-reasoning":
        assert answer in original[4]["reasoning_content"]
        assert "receipt=" not in original[5]["content"]
    else:
        assert answer in original[5]["content"]

    template = Environment().from_string(runner.live.TEMPLATE.read_text())
    for arm, expected in zip(policies.ARMS, EXPECTED[case_id], strict=True):
        selected, receipt = policies.apply_policy(original, arm)
        assert json.dumps(selected).count(answer) == int(expected)
        assert receipt["pairs_fixed"] == receipt["compaction_model_calls"] == 0
        if arm.startswith("A1-"):
            assert selected[:4] == original[:4] and selected[-6:] == original[-6:]
            assert receipt["production_threshold"] == int(arm.split("-k")[1])
            assert receipt["production_stubbed"] == 6
            assert receipt["changed_observations"] == [5, 7, 9, 11, 13, 15]
            assert receipt["changed_assistant_entries"] == []
        elif arm == "A2":
            assert receipt["changed_observations"] == [3, 5, 7, 9, 11, 13, 15]
            assert receipt["changed_assistant_entries"] == []
            assert selected[5]["content"].startswith(original[5]["content"][:180])
        elif arm == "A3":
            assert receipt["changed_observations"] == []
            assert receipt["changed_assistant_entries"] == [2, 4, 6, 8, 10, 12, 14]
            assert selected[4]["reasoning_content"] == "omitted"
        else:
            assert selected == original

        rendered = template.render(messages=selected, tools=policies.TOOLS,
                                   enable_thinking=False, preserve_reasoning=True,
                                   add_generation_prompt=True)
        assert policies.verify_render(case, selected, rendered, arm) is expected
        corrupted_render = rendered.replace(answer, "removed") if expected else rendered + answer
        with pytest.raises(ValueError, match="rendered answer exposure"):
            policies.verify_render(case, selected, corrupted_render, arm)

        corrupted_messages = deepcopy(selected)
        corrupted_messages[-1]["content"] += answer
        with pytest.raises(ValueError, match="unexpected target evidence"):
            policies.verify_evidence(case, corrupted_messages, arm)
    assert original == untouched


def test_abstention_na_and_instrument_unknown(sealed, tmp_path, monkeypatch):
    _, policies, _, cases, rows = sealed
    row = rows[0]
    case = cases[row["case"]]
    reply = {"model": runner.live.MODEL.name,
             "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "UNKNOWN"}}],
             "usage": {"prompt_tokens": 100, "completion_tokens": 2, "total_tokens": 102}}
    abstention = runner.grade(reply, 100, case["answer"], 96)
    assert (abstention["status"], abstention["answer"], abstention["non_termination"]) == ("abstained", "UNKNOWN", 0)
    reply["choices"][0]["finish_reason"] = "length"
    assert runner.grade(reply, 100, case["answer"], 96)["status"] == "NA"

    def fail_transport(*args):
        raise OSError("transport unavailable")

    monkeypatch.setattr(runner, "post", fail_transport)
    unknown = runner.cell(tmp_path / "failed", row, case, policies, "unused", float("inf"), "test")
    assert unknown["status"] == "UNKNOWN"
    assert unknown["error"] == "OSError: transport unavailable"
    paired_control = next(candidate for candidate in rows if candidate["arm"] == row["arm"] and candidate != row)
    summary = runner.summarize(rows, [unknown, {**paired_control, **abstention, "wall_s": 1}], policies.ARMS)
    arm = summary["arms"][row["arm"]]
    assert (arm["attempted"], arm["abstained"], arm["UNKNOWN"], summary["completed"]) == (2, 1, 1, 1)
