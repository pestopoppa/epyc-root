from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/autopilot_replay"))
import w66_recovery as recovery


@pytest.fixture(scope="module")
def detectors():
    repo = ROOT / "repos/epyc-orchestrator"
    if not repo.exists():
        repo = Path("/workspace/repos/epyc-orchestrator")
    if not repo.exists():
        pytest.skip("orchestrator checkout required for detector replay")
    return recovery.load_detectors(repo)[0]


def inspection(index: int, same_input: bool = False) -> recovery.Turn:
    args = {"pattern": "query" if same_input else str(index)}
    return recovery.Turn([recovery.Tool("grep", args, "same", "completed", True, None, False)],
                         (index + 1) * 1000, [])


def test_long_and_exact_triggers_are_distinct(detectors):
    long = recovery.inspect_recovery_trace([inspection(i) for i in range(120)], detectors, 0, 600)
    assert long["counterfactual_advisories"]["primary"]["after_call"] == 80
    assert long["counterfactual_advisories"]["longer_inspection_run"]["after_call"] == 120
    assert long["counterfactual_advisories"]["exact_repeat_only"] is None
    exact = recovery.inspect_recovery_trace([inspection(i, same_input=True) for i in range(21)], detectors, 0, 600)
    assert exact["counterfactual_advisories"]["exact_repeat_only"]["after_call"] == 20


def test_changed_outputs_and_late_phase_do_not_trigger_exact_repeat(detectors):
    turns = [inspection(i, same_input=True) for i in range(25)]
    for i, turn in enumerate(turns):
        turn.tools[0].result_sha256 = str(i)
    assert recovery.inspect_recovery_trace(turns, detectors, 0, 600)["counterfactual_advisories"]["primary"] is None
    late = recovery.inspect_recovery_trace([inspection(i) for i in range(120)], detectors, 0, 150)
    assert late["counterfactual_advisories"]["primary"] is None


def test_only_scoped_shell_writes_reset_inspection_streak(detectors):
    session = {"messages": [{"type": "assistant", "time": {"created": 40_000, "completed": 40_001},
                             "snapshot": {"files": ["artifact.py", "__pycache__/artifact.pyc"]},
                             "content": [{"type": "tool", "name": "shell", "state": {
                                 "status": "completed", "input": {"command": "cat > artifact.py"},
                                 "content": [{"type": "text", "text": ""}], "metadata": {"exit": 0},
                             }}]}]}
    turn = recovery.session_turns(session, 0, 600, {"artifact.py"})[0]
    assert turn.changes == ["artifact.py"]
    turns = [inspection(i) for i in range(39)] + [turn] + [inspection(i) for i in range(40, 100)]
    result = recovery.inspect_recovery_trace(turns, detectors, 0, 600)
    assert result["observed_artifact_changes"][0]["execution_tool_in_turn"]
    assert result["first_completed_edit_or_write"] is None
    assert result["counterfactual_advisories"]["primary"] is None
