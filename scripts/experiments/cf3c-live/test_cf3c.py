"""Offline checks for source-pinned policy activation and result classification."""
import copy

import pytest

import runner


@pytest.fixture(scope="module")
def sealed():
    return runner.verify()


def test_matrix_is_paired(sealed):
    _, policies, _, cases, rows = sealed
    assert len(rows) == 18
    assert len(set(row["unit"] for row in rows)) == 18
    for case in cases.values():
        paired = [row for row in rows if row["case"] == case["id"]]
        assert {r["seed"] for r in paired} == {case["seed"]}
        assert {r["arm"] for r in paired} == set(policies.ARMS)


@pytest.mark.parametrize(("case_id", "activation"), [
    ("old-deep", [True, False, False]),
    ("old-head", [True, True, False]),
    ("recent", [True, True, True]),
])
def test_production_stubbing_sweep(sealed, case_id, activation):
    _, policies, _, cases, _ = sealed
    original = policies.make_messages(cases[case_id])
    saved = copy.deepcopy(original)
    control, metrics = policies.apply_policy(original, "A0")
    assert control == saved == original
    assert metrics["changed_observations"] == []
    for k, active in zip((4, 8, 12), activation, strict=True):
        selected, metrics = policies.apply_policy(original, f"A1-k{k}")
        assert (selected != control) is active
        assert bool(metrics["production_stubbed"]) is active
        assert metrics["changed_assistant_entries"] == []
        assert selected[:4] == control[:4] and selected[-6:] == control[-6:]
    assert original == saved


@pytest.mark.parametrize(("arm", "changed_key"), [
    ("A2", "changed_observations"),
    ("A3", "changed_assistant_entries"),
])
def test_deterministic_anchors(sealed, arm, changed_key):
    _, policies, _, cases, _ = sealed
    case = cases["recent"]
    original = policies.make_messages(case)
    selected, metrics = policies.apply_policy(original, arm)
    assert len(metrics[changed_key]) == 7
    assert metrics["pairs_fixed"] == metrics["compaction_model_calls"] == 0
    for index, (before, after) in enumerate(zip(original, selected, strict=True)):
        if index not in metrics[changed_key]:
            assert before == after
        elif arm == "A2":
            assert before["tool_call_id"] == after["tool_call_id"]
            assert before["content"][:180] in after["content"]
            assert "ObservationTail" not in after["content"]
        elif arm == "A3":
            assert before["tool_calls"] == after["tool_calls"]
            assert after["reasoning_content"] == "omitted"
    rendered = "\n".join(msg.get("reasoning_content", "") + msg["content"] for msg in selected)
    policies.verify_render(case, selected, rendered)
    with pytest.raises(ValueError, match="visibility mismatch"):
        policies.verify_render(case, selected, rendered + " ObservationTail01 ReasoningTrace01")


def test_length_remains_na_even_if_exact():
    reply = {"model": runner.live.MODEL.name,
             "choices": [{"finish_reason": "length", "message": {"content": "abc"}}],
             "usage": {"prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105}}
    result = runner.grade(reply, 100, "abc", 5)
    assert (result["status"], result["answer"], result["correct"], result["non_termination"]) == (
        "NA", "NA", None, 1)
    with pytest.raises(ValueError, match="does not reconcile"):
        runner.grade(reply, 101, "abc", 5)


def test_stopped_abstention_keeps_its_status():
    reply = {"model": runner.live.MODEL.name,
             "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "UNKNOWN"}}],
             "usage": {"prompt_tokens": 100, "completion_tokens": 2, "total_tokens": 102}}
    result = runner.grade(reply, 100, "abc", 5)
    assert result["status"] == "abstained"
    assert result["correct"] is None


def test_pinned_template_keeps_historical_reasoning_where_required(sealed):
    from jinja2 import Environment

    _, policies, _, cases, _ = sealed
    case = cases["recent"]
    original = policies.make_messages(case)
    template = Environment().from_string(runner.live.TEMPLATE.read_text())
    for arm in policies.ARMS:
        transformed, _ = policies.apply_policy(original, arm)
        rendered = template.render(messages=transformed, tools=policies.TOOLS,
                                   enable_thinking=False, preserve_reasoning=True,
                                   add_generation_prompt=True)
        policies.verify_render(case, transformed, rendered)


def test_attempted_denominator_includes_ungraded_cells(sealed):
    _, policies, _, _, rows = sealed
    control = [row for row in rows if row["arm"] == "A0"]
    results = [{**row, "status": status, "correct": correct, "non_termination": int(status == "NA"), "wall_s": 1}
               for row, status, correct in zip(control, ("graded", "NA", "abstained"), (True, None, None), strict=True)]
    result = runner.summarize(rows, results, policies.ARMS)
    assert result["arms"]["A0"]["accuracy_over_attempted"] == pytest.approx(1 / 3)
    assert result["arms"]["A0"]["accuracy_among_graded"] == 1
    assert result["arms"]["A0"]["non_termination"] == 1
    assert result["completed"] == 3
