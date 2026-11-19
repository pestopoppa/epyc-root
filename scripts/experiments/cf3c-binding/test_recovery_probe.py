"""Offline controls: qualification is independent of quality correctness."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).resolve().parent
probe = load("recovery_probe", HERE / "recovery_probe.py")
binding = load("binding", HERE.parent / "cf3c-task-suite/binding.py")


def fixture(tmp_path):
    cohort = binding.compile_cohort()
    before = copy.deepcopy(cohort)
    control = probe.compile_probe(cohort)
    assert cohort == before
    log = tmp_path / "session.verbatim.md"
    log.write_text("\n".join(e["output"] for e in control["initial_history"]))

    class Repl:
        def __init__(self):
            # Native REPL namespaces bind methods at construction time.
            self.peek = self._peek

        def _peek(self, n=500, file_path=None, offset=0):
            return Path(file_path).read_text()[offset:offset + n]

    original = Repl._peek
    with probe.capture_peeks(Repl, control["initial_history"]) as capture:
        repl = Repl()
        capture["log_path"] = str(log)
        returned = repl.peek(99999, file_path=str(log))
        assert returned == log.read_text()
    assert Repl._peek is original
    trial = {
        "case": control["id"], "arm": control["arm"], "seed": control["seed"],
        "correct": False, "status": "grade_unavailable", "child_exited": True,
        "usage_complete": {"total_tokens": True},
        "native_result": {
            "answer": "wrong", "wire_requests": 2,
            "policy_receipts": [{"active": True, "selected_history_sha256": "a" * 64}],
            "tool_calls": {"retrieval": 1},
            "initial_history_receipt": {
                "observations": 10,
                "archive_sha256": binding.digest(control["initial_history"]),
                "verbatim_sha256": probe.sha(log.read_text()),
            },
        },
    }
    return control, trial, capture


def verdict(control, trial, capture):
    return probe.qualify(control, trial, capture, server_exited=True, error=None)


@pytest.mark.parametrize("correct", [True, False, None])
def test_qualification_does_not_select_for_task_correctness(tmp_path, correct):
    control, trial, capture = fixture(tmp_path)
    trial["correct"] = correct
    assert verdict(control, trial, capture)["qualified"]
    del trial["correct"]
    del trial["native_result"]["answer"]
    assert verdict(control, trial, capture)["qualified"]


@pytest.mark.parametrize("failure", [
    "no_call", "wrong_file", "prefix_only", "inactive", "no_wire",
    "unknown", "incomplete_cost", "child_alive", "old_version", "quality_cell",
    "archive_changed", "missing_custody", "wrong_seed", "log_changed", "missing_status",
])
def test_refuse_missing_instrument_evidence_even_with_correct_answer(tmp_path, failure):
    control, trial, capture = fixture(tmp_path)
    trial["correct"] = True
    native = trial["native_result"]
    if failure == "no_call":
        native["tool_calls"]["retrieval"] = 0
    elif failure == "wrong_file":
        capture["events"][0]["source_log"] = False
    elif failure == "prefix_only":
        capture["events"][0]["recovered_observation"] = False
    elif failure == "inactive":
        native["policy_receipts"][0]["active"] = False
    elif failure == "no_wire":
        native["wire_requests"] = 0
    elif failure == "unknown":
        trial["status"] = "UNKNOWN"
    elif failure == "incomplete_cost":
        trial["usage_complete"]["total_tokens"] = False
    elif failure == "child_alive":
        trial["child_exited"] = False
    elif failure == "old_version":
        capture["schema"] = "v0"
    elif failure == "quality_cell":
        trial["case"] = "binding_deep_v1"
    elif failure == "archive_changed":
        native["initial_history_receipt"]["archive_sha256"] = "0" * 64
    elif failure == "missing_custody":
        native["policy_receipts"][0].pop("selected_history_sha256")
    elif failure == "log_changed":
        capture["events"][0]["source_log_sha256"] = "0" * 64
    elif failure == "missing_status":
        trial.pop("status")
    else:
        trial["seed"] += 1
    assert not verdict(control, trial, capture)["qualified"]


def test_server_and_transport_failure_refuse(tmp_path):
    control, trial, capture = fixture(tmp_path)
    for server_exited, error in [(False, None), (True, "transport")]:
        assert not probe.qualify(control, trial, capture,
                                 server_exited=server_exited, error=error)["qualified"]


def test_compiler_refuses_mutated_quality_cohort():
    cohort = binding.compile_cohort()
    cohort["cases"][1]["prompt"] += " altered"
    with pytest.raises(ValueError, match="cohort changed"):
        probe.compile_probe(cohort)


def test_capture_checks_actual_path_and_returned_observation(tmp_path):
    control = probe.compile_probe(binding.compile_cohort())
    log, other = tmp_path / "log", tmp_path / "other"
    content = control["initial_history"][3]["output"]
    log.write_text(content)
    other.write_text(content)

    class Repl:
        def _peek(self, n=500, file_path=None, offset=0):
            return Path(file_path).read_text()[offset:offset + n]

    with probe.capture_peeks(Repl, control["initial_history"]) as capture:
        capture["log_path"] = str(log)
        repl = Repl()
        repl._peek(99999, file_path=str(other))
        repl._peek(180, file_path=str(log))
        repl._peek(99999, file_path=str(log))
    assert [e["recovered_observation"] for e in capture["events"]] == [False, False, True]
    assert capture["events"][-1]["returned_sha256"] == probe.sha(content)
    assert "expected" not in json.dumps(control)
