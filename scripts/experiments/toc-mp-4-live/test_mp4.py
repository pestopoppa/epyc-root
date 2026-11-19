"""Offline native graph and immutable-custody regressions."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKET = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/mp4/packet")
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(PACKET)]
import runner
from assessment import assess
from prepare import resume_files

FAKE_TRANSPORT = r'''
import json
import os
import re
import runpy
import socket
import sys

import httpx

calls = 0
needle = sys.argv.pop()
arm = sys.argv.pop()
mode = sys.argv.pop()

def reject_network(*args, **kwargs):
    raise AssertionError("offline trial attempted network I/O")


def endpoint(request):
    global calls
    body = json.loads(request.content)
    if request.url.path == "/tokenize":
        content = body["content"]
        n = (len(content) + 3) // 4 + content.count(" q7") + content.count(" z8")
        return httpx.Response(200, json={"tokens": list(range(n))})
    assert request.url.path == "/v1/chat/completions", str(request.url)
    text = "\n".join(x["content"] for x in body["messages"])
    if "<conversation>" in text:
        assert needle in text
        summary = (f"## Progress\nThe receipt is {needle}." if mode in {"summary", "code_free", "capped"}
                   else "## Progress\nCheckpoint ready.")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": summary}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3300, "completion_tokens": 18},
        })
    calls += 1
    code_free = calls == 3 and mode in {"code_free", "capped"}
    if code_free:
        content = "I should review the checkpoint before returning the receipt."
        finish = "length" if mode == "capped" else "stop"
    elif calls == 1:
        assert needle not in text
        code = "FINAL('UNKNOWN')" if mode == "early" else "print(take_record())"
    elif calls == 2:
        assert needle in text
        code = "print(checkpoint())"
    elif calls == 3 and arm != "summary_only":
        assert needle not in text and "[Turn 1 role=" not in text
        path = re.search(r'Full log: peek\([^\n]*file_path="([^"]+)"', text).group(1)
        code = f"print(peek(500, file_path={path!r}))"
    else:
        assert mode == "wrong" or needle in text
        answer = needle + " " if mode == "wrong" else needle
        code = f"FINAL({answer!r})"
    if not code_free:
        content, finish = f"```python\n{code}\n```", "stop"
    response = [{"choices": [{"delta": {"content": content}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": finish}],
                 "usage": {"prompt_tokens": 500, "completion_tokens": 20}}]
    sse = "".join(f"data: {json.dumps(item)}\n\n" for item in response) + "data: [DONE]\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          stream=httpx.ByteStream(sse.encode()))


socket.socket.connect = reject_network
httpx.Client._transport_for_url = lambda *args: httpx.MockTransport(endpoint)
sys.path.insert(0, os.path.dirname(sys.argv[1]))
sys.path.insert(1, os.environ["TOC_MP4_TEST_HARNESS"])
runpy.run_path(sys.argv.pop(1), run_name="__main__")
'''


@pytest.fixture(scope="session")
def frozen():
    return runner.live.read_json(PACKET / "cases.json"), runner.live.read_json(PACKET / "schedule.json")


@pytest.fixture(scope="session")
def pinned_source():
    source = Path(os.environ.get("TOC_MP4_TEST_SOURCE", runner.SOURCE))
    git = ["git", "-C", source]
    assert subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip() == runner.live.SOURCE_SHA
    assert not subprocess.check_output([*git, "status", "--porcelain"], text=True)
    return source


@pytest.mark.parametrize(("arm", "mode", "correct"), [
    ("summary_pointer", "retrieve", True),
    ("summary_only", "summary", True),
    ("summary_only", "code_free", True),
    ("summary_only", "capped", None),
    ("pointer_only", "wrong", False),
    ("summary_pointer", "early", None),
])
def test_real_pinned_graph_offline(tmp_path, frozen, pinned_source, arm, mode, correct):
    cases, rows = frozen
    case = cases[0]
    row = next(row for row in rows if row["arm"] == arm)
    runner.seal(tmp_path / "INPUT.json", {"row": row, "case": {"prompt": runner.task_prompt(case)},
                "source": str(pinned_source), "endpoint": runner.ENDPOINT, "temperature": 0.3, "smoke": True})
    child = subprocess.run([str(runner.live.PYTHON), "-B", "-c", FAKE_TRANSPORT,
                            str(HERE / "trial.py"), str(tmp_path), mode, arm, case["needle"]],
                           check=False, input=json.dumps(case), cwd=tmp_path, text=True, capture_output=True,
                           env={**runner.live.graph_env(row, tmp_path, "offline"),
                                "TOC_MP4_TEST_HARNESS": str(PACKET)}, timeout=30)
    assert child.returncode == 0, child.stdout + child.stderr
    outcome = assess(tmp_path, row, case)
    assert outcome["correct"] is correct, outcome
    if mode == "early":
        assert outcome["reason"] == "boundary_not_reached"
        assert outcome.get("instrument_error") is None
        return
    if mode == "capped":
        assert outcome["reason"] == "generation_token_limit_reached"
        assert outcome.get("instrument_error") is None
    else:
        assert outcome["summary_has_needle"] is (mode in {"summary", "code_free"})
        assert outcome["log_read_turns"] == ([] if arm == "summary_only" else [3])
    assert case["needle"] not in (tmp_path / "INPUT.json").read_text()

    audit_path = tmp_path / "FIXTURE-AUDIT.json"
    audit = runner.live.read_json(audit_path)
    tail, = [entry for entry in audit if entry["kind"] == "tail"]
    if mode in {"code_free", "capped"}:
        assert [entry["turn"] for entry in audit if entry["kind"] == "execute"] == [1, 2, 4]
        assert tail["turn"] == 3
        wire = runner.live.read_json(tmp_path / "GRAPH.json")["wire"]
        boundary_request, = [record for record in wire
                             if record["call_kind"] == "generation" and record["graph_turn"] == 3]
        assert boundary_request["response_sse_done"] is True
    without_tail = [entry for entry in audit if entry["kind"] != "tail"]
    for altered_audit, reason in (
        (without_tail, "boundary_generation_tail_observation_missing"),
        (without_tail + [{**tail, "turn": 4}], "boundary_generation_tail_observation_missing"),
        (without_tail + [{**tail, "scope": {}}], "private_source_confinement_unverified"),
        (without_tail + [{**tail, "has_needle": True}], "needle_eviction_from_native_tail_unverified"),
    ):
        runner.live.atomic_json(audit_path, altered_audit)
        rejected = assess(tmp_path, row, case)
        assert rejected["reason"] == reason
        assert rejected["correct"] is None and rejected["instrument_error"] is True

    wire = runner.live.read_json(tmp_path / "GRAPH.json")["wire"]
    (tmp_path / wire[0]["response_file"]).write_text("corrupt response")
    with pytest.raises(ValueError, match="wire response custody mismatch"):
        assess(tmp_path, row, case)


def test_matrix_decision_requires_all_eligible(frozen):
    cases, rows = frozen
    assert runner.schedule(cases) == rows
    assert len(rows) == 120
    results = [{"unit": row["run_id"], "correct": True, "completed": True} for row in rows]
    initial = runner.summarize(rows, results)
    assert initial["decision"] == "retain_pointer_only_candidate"
    pointer_only = next(row for row in rows if row["arm"] == "pointer_only")
    results[pointer_only["ordinal"]]["correct"] = False
    result = runner.summarize(rows, results)
    assert result["decision"] == "fire_M-MP2" and result["paired"]["summary_pointer_correct"] == 1
    results[0]["correct"] = None
    result = runner.summarize(rows, results)
    assert result["coverage_complete"] and result["eligible"] == 119 and result["decision"] == "UNKNOWN"


def test_interruption_is_immutable_and_never_replayed(tmp_path, frozen):
    _, rows = frozen
    attempt = tmp_path / "units/000"
    attempt.mkdir(parents=True)
    (attempt / "incomplete").write_text("partial")
    assert runner.units(tmp_path, rows, "packet")[0]["reason"] == "interrupted_before_immutable_trial_receipt"
    with pytest.raises(ValueError, match="immutable trial receipt mismatch"):
        runner.units(tmp_path, rows, "different-packet")
    (attempt / "incomplete").write_text("changed")
    with pytest.raises(ValueError, match="immutable trial receipt mismatch"):
        runner.units(tmp_path, rows, "packet")


def test_runtime_receipt_changed_on_resume(tmp_path, frozen):
    _, rows = frozen
    attempt = tmp_path / "units/000"
    attempt.mkdir(parents=True)
    window = tmp_path / "window-test"
    window.mkdir()
    for name in ("WINDOW.json", "SERVER.json", "SERVER-PROPS.json", "SERVER-MODELS.json",
                 "SERVER-SLOTS.json", "LINKAGE.txt"):
        (window / name).write_text("original")
    runner.seal(attempt / "METRICS.json", {"unit": rows[0]["run_id"], "packet_sha256": "packet",
                "files_sha256": {}, "window": str(window), "runtime_sha256": runner.runtime_digests(window)})
    assert len(runner.units(tmp_path, rows, "packet")) == 1
    (window / "SERVER.json").write_text("changed")
    with pytest.raises(ValueError, match="runtime custody changed"):
        runner.units(tmp_path, rows, "packet")


def test_successor_reuses_sealed_native_matrix_and_uses_fresh_stop_file():
    directory, previous, spec, launcher = resume_files(PACKET, 2)
    base = runner.live.read_json(PACKET / "spec.json")
    assert spec["id"] == f"{previous}-r2"
    assert spec["supersedes"] == [base["id"]]
    assert spec["launcher"] == str(directory / "launcher.sh")
    assert spec["result_path"] == base["result_path"]
    assert spec["scratch_root"] == base["scratch_root"]
    assert f"--id {spec['id']} " in launcher
    assert '--stop "$R/STOP-r2"' in launcher
    assert f"D={PACKET}" in launcher


def test_structural_failure_saves_receipt_and_stops_before_next_unit(tmp_path, frozen, monkeypatch):
    cases, rows = frozen
    out = tmp_path / "native"
    (out / "units").mkdir(parents=True)
    process = SimpleNamespace(pid=43210, returncode=None)
    process.poll = lambda: process.returncode
    process.terminate = lambda: setattr(process, "returncode", 0)
    process.wait = lambda **_: process.returncode
    owner = SimpleNamespace(listen_inodes=lambda _port: {1} if process.poll() is None else set(),
                            pid_socket_inodes=lambda _pid: {1})
    monkeypatch.setenv("FILLER_ID", runner.ROW)
    monkeypatch.setenv("FILLER_DEADLINE", str(int(time.time()) + 3600))
    monkeypatch.setenv("FILLER_PIDFILE", str(tmp_path / "pids.txt"))
    monkeypatch.setattr(runner.signal, "signal", lambda *_: None)
    monkeypatch.setattr(runner.live, "bind_four_cores", lambda: [0, 1, 2, 3])
    monkeypatch.setattr(runner.live, "file_port_available", lambda _port: True)
    monkeypatch.setattr(runner.live, "check_window", lambda _deadline: None)
    monkeypatch.setattr(runner.live, "server_ready", lambda *_, **__: {"pid": process.pid})
    monkeypatch.setattr(runner.subprocess, "run", lambda *_, **__: SimpleNamespace(stdout="linked"))

    def launch(*_args, **_kwargs):
        owner.listen_inodes = lambda _port: {1} if process.poll() is None else set()
        return process

    owner.listen_inodes = lambda _port: set()
    monkeypatch.setattr(runner.subprocess, "Popen", launch)
    monkeypatch.setitem(sys.modules, "scripts.benchmark", SimpleNamespace(own_port_proof=owner))

    def fail_structurally(attempt, config, *_args):
        result = {"unit": config["row"]["run_id"], "status": "unknown", "correct": None,
                  "instrument_error": True, "reason": "needle_eviction_from_native_tail_unverified"}
        runner.seal(attempt / "METRICS.json", result)
        return result

    monkeypatch.setattr(runner, "run_trial", fail_structurally)
    source_inputs = runner.live.read_json(PACKET / "inputs.json")
    exited, stopped, error = runner.run_window(
        out, rows[:2], {case["label"]: case for case in cases}, source_inputs, False, "packet")
    assert exited and not stopped and "trial instrument failure" in error
    assert runner.live.read_json(out / "units/000/METRICS.json")["instrument_error"] is True
    assert not (out / "units/001").exists()
