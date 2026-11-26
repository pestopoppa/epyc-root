"""r8h harness fixes from the r8g CPU canary (2026-11-24, FIX-HARNESS, audited 6/10;
docs/design/taskflow-stage1-canary-findings.md r8g)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import verify  # noqa: E402
from taskflow.harness import local_llm as L  # noqa: E402


# ------------------------------------------------------------------------- fix 1: #L<a>-<b> where-range suffix
WS4 = {"repo": "epyc-root", "where": ["epyc-root:scripts/coordination/tmux_adapter.py#L2301-2488",
                                      "epyc-root:scripts/coordination/handoff_sessions.py::build_x#L10"],
       "forbidden": ["scripts/coordination/*.py"]}


def test_brief_paths_strip_line_range():
    assert verify.brief_paths(WS4) == {"scripts/coordination/tmux_adapter.py", "scripts/coordination/handoff_sessions.py"}


def test_outside_pathspec_admits_line_ranged_file():          # r8g nothink WS4 regression
    p = "scripts/coordination/tmux_adapter.py"
    assert verify.outside_pathspec([p], WS4, modified={p}) == []
    assert verify.outside_pathspec(["scripts/other.py"], WS4, modified={"scripts/other.py"}) == ["scripts/other.py"]


def test_forbidden_hits_admits_line_ranged_file():
    assert verify.forbidden_hits(["scripts/coordination/tmux_adapter.py"], WS4) == []
    assert verify.forbidden_hits(["scripts/coordination/zz.py"], WS4) == ["scripts/coordination/zz.py"]


# ------------------------------------------------------------------------- fix 2: reviewer control test / sanctioned skips
T = "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"
TU_GR_1_ACCEPTANCE = {   # r8g think TU-GR-1 acceptance log (pytest -rA), audited harness: reviewer false reject
    "rc": 0, "tail": "1 passed, 1 skipped",
    "ra": [f"PASSED {T}::test_reachable_grader_is_flagged",
           f"SKIPPED [1] {T}:41: unshare not permitted: unshare: write failed /proc/self/uid_map: Operation not permitted"]}
TU_GR_1 = {"goal": "TU-GR-1: grader isolation check", "done_when": "a test exists and fails on a deliberately reachable grader",
           "acceptance": f"python3 -m pytest -q {T}", "acceptance_result": TU_GR_1_ACCEPTANCE,
           "control_tests": ["test_reachable_grader_is_flagged: passes by asserting GraderReachable is raised"],
           "sanctioned_skips": ["test_isolated_launch_denies: pytest.skip when unshare is not permitted, with the errno"]}


def test_review_prompt_names_control_and_sanctioned_skip():
    p = verify.review_prompt(TU_GR_1, "diff")
    assert "## CONTROL TESTS" in p and "test_reachable_grader_is_flagged: passes by asserting GraderReachable" in p
    assert "## SANCTIONED SKIPS" in p and "test_isolated_launch_denies: pytest.skip when unshare" in p
    assert verify.REVIEW_CONTROL_RULE in p and "Operation not permitted" in p       # the rule and the log both reach it


def test_review_prompt_requires_control_evidence_and_review_of_skipped_code():
    approach = "Mount an empty tmpfs over the scratch directory before exec."
    prompt = verify.review_prompt(dict(TU_GR_1, approach=approach), "candidate diff")

    assert f"## APPROACH\n{approach}" in prompt
    assert "accessed that artifact before pytest.raises" in prompt
    assert "cannot count as reachability or denial" in prompt
    assert "actual skip reason and the predicate in the code" in prompt
    assert "trace the unexecuted code from launcher argv to child and assertions" in prompt
    assert "exact sanctioned skip and a witnessed passing control can be done" in prompt


def test_ra_lines_retains_skip_os_diagnostic_after_long_launcher_prefix():
    line = (f"SKIPPED [1] {T}:69: unshare not permitted on this host: launcher exited with code 1 and no stdout: "
            "unshare: write failed /proc/self/uid_map: Operation not permitted")
    assert len(line) > 200
    assert verify.ra_lines(line) == [line]


def test_review_prompt_checks_drift_even_when_acceptance_passes():
    task = {"goal": "Add the new section and link to it", "approach": "Insert after the existing Rules section",
            "acceptance_result": {"rc": 0}}
    prompt = verify.review_prompt(task, "candidate diff")

    assert "## APPROACH\nInsert after the existing Rules section" in prompt
    assert "Read deletions, replacements, and added sections" in prompt
    assert "duplicating existing rules is drift even when the requested additions and acceptance both succeed" in prompt


def test_review_context_from_approach_and_brief():
    t = {"approach": "(1) test_a: launcher=[] and it must raise. This is the 'fails on a reachable grader' control. "
                     "(2) test_b: if unshare is not permitted, pytest.skip with the errno."}
    ctl, skp = verify.reviewer_context(t)
    assert any("control" in c for c in ctl) and any("pytest.skip" in s for s in skp)
    assert "## CONTROL TESTS" not in verify.review_prompt({"goal": "g"}, "d")    # no context -> prompt unchanged


def test_tu_gr_1_brief_carries_reviewer_context():
    from taskflow import brief as B
    doc = B.parse_text((Path(__file__).resolve().parents[2] / "handoffs/active/briefs/TU-GR-1.md").read_text())
    assert any("assert the plain child read the sentinel" in c and "GraderReachable" in c for c in doc["control_tests"])
    assert any("only for an explicit namespace setup permission refusal" in s and "Operation not permitted" in s
               for s in doc["sanctioned_skips"])


# ------------------------------------------------------------------------- fix 3: shell refusal hint reaches the model
R8G_DENIAL = json.dumps({"error": {"type": "permission.rejected", "message": "Permission denied: shell"}, "content": []})  # r8g bodies


def _allowed_forms(text):
    return all(form in text for form in ("orch-py.sh -m pytest", "orch-py.sh -c", "`taskflow-scratch rm <relative path>`",
                                        "`taskflow-scratch mv <relative src>"))


def test_opencode_json_denial_gets_the_allowed_forms():
    body = {"messages": [{"role": "tool", "tool_call_id": "1", "content": R8G_DENIAL},
                         {"role": "tool", "tool_call_id": "2", "content": [{"type": "text", "text": "Permission denied: shell"}]},
                         {"role": "tool", "tool_call_id": "3", "content": '{"output":"ok"}'}]}
    assert L.annotate_denials(body) == 2
    d = json.loads(body["messages"][0]["content"])                          # still valid JSON
    assert d["error"]["message"].startswith("Permission denied: shell") and _allowed_forms(d["error"]["message"])
    assert _allowed_forms(body["messages"][1]["content"][0]["text"])
    assert body["messages"][2]["content"] == '{"output":"ok"}'
    snap = json.dumps(body)
    assert L.annotate_denials(body) == 0 and json.dumps(body) == snap      # idempotent: stable prefix
