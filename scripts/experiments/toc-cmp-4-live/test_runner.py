import json
import os
import subprocess

import pytest
import runner as cpu_runner
from runner import (
    ENDPOINT,
    HERE,
    PYTHON,
    SOURCE,
    graph_env,
    smoke_predicate,
    split_kv_observed,
    summarize_ledger,
    trajectory_metrics,
)


def row():
    return {
        "point_id": "item@2", "arm": "summary_only", "repeat": 0,
        "env": {"ORCHESTRATOR_CONTEXT_FORCE_TURNS": "2", "ORCHESTRATOR_CONTEXT_BUDGET_TOKENS": "16384",
                "ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION": "0.5"},
    }


def final():
    return {
        "event": "final", "arm": "summary_only", "trial_index": 0,
        "context_budget_tokens": 16384, "effective_context_budget_tokens": 16384,
        "trigger_fraction": 0.5, "history_valid": True, "terminal_state": "solved",
    }


def turn(turn_no, *, blocked=False, error=False, reads=0, mixed=False):
    return {"event": "turn", "turn": turn_no, "blocked": blocked, "outcome": "error" if error else "ok",
            "log_follows": [{}] * reads, "log_follow_attempts": [{}] * reads,
            "tool_calls": {"retrieval": reads, "execution": int(mixed)}}


def test_uses_numeric_turns_b_plus_one_through_b_plus_five():
    events = [turn(1, blocked=True), {"event": "boundary", "turn": 2},
              turn(2, blocked=True), turn(3, reads=1, blocked=True), turn(4, reads=1, error=True, mixed=True),
              turn(5), turn(6), turn(7, blocked=True), turn(8, blocked=True), final()]
    observed = trajectory_metrics(events, row())
    assert observed["actions"] == 5
    assert observed["baps"] == 2 / 5
    assert observed["log_follows"] == 2
    assert observed["deliberate_rereads"] == 1


def test_no_boundary_and_incorrect_boundary_are_distinct():
    missing = trajectory_metrics([turn(1), final()], row())
    assert missing["boundary_reached"] is False
    assert missing["baps"] is None
    with pytest.raises(ValueError, match="exactly the assigned boundary"):
        trajectory_metrics([turn(1), {"event": "boundary", "turn": 3}, turn(3), final()], row())
    with pytest.raises(ValueError, match="missing post-boundary"):
        trajectory_metrics([turn(1), {"event": "boundary", "turn": 2}, final()], row())
    smoke = trajectory_metrics([turn(1), {"event": "boundary", "turn": 2}, turn(2), final()], row(), smoke=True)
    assert smoke["boundary_reached"] is True
    assert smoke["baps"] is None


def test_final_artifact_must_report_assigned_trial_and_budget():
    with pytest.raises(ValueError, match="trial_index"):
        trajectory_metrics([turn(1), {**final(), "trial_index": 1}], row())
    with pytest.raises(ValueError, match="effective_context_budget_tokens"):
        trajectory_metrics([turn(1), {**final(), "effective_context_budget_tokens": 4096}], row())


@pytest.mark.parametrize(("message", "expected"), [
    ("srv load_model: initializing, n_slots = 4, n_ctx_slot = 65536, kv_unified = 'false'", True),
    ("llama_context: kv_unified    = false", True),
    ("srv load_model: kv_unified = 'true'", False),
    ("srv load_model: kv_unified = falsehood", False),
])
def test_v10_split_kv_startup_witness(message, expected):
    assert split_kv_observed(message) is expected


@pytest.mark.parametrize(("started", "expected"), [
    (None, 1), ("0", 1), ("-1", 1), ("nan", 1), ("inf", 1), ("invalid", 1),
    ("1001", 1), ("1000", 0), ("999", 0),
])
def test_smoke_receipt_requires_a_valid_current_launch_timestamp(tmp_path, monkeypatch, started, expected):
    receipt = tmp_path / "cmp4-native/SMOKE.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({"transport_and_graph": True, "server_exited": True}))
    os.utime(receipt, (1000, 1000))
    monkeypatch.setenv("FILLER_DRYRUN_DIR", str(tmp_path))
    if started is None:
        monkeypatch.delenv("FILLER_SMOKE_T0", raising=False)
    else:
        monkeypatch.setenv("FILLER_SMOKE_T0", started)
    assert smoke_predicate() == expected


def test_graph_child_initializes_from_isolated_trial_dir(tmp_path):
    if not PYTHON.is_file() or not SOURCE.is_dir():
        pytest.skip("pinned orchestrator trial worktree and venv required")
    trial = row()
    trial["env"].update({"ORCHESTRATOR_CONTEXT_ARM": trial["arm"],
                         "ORCHESTRATOR_CONTEXT_TRIAL_INDEX": "0"})
    trial["sampling_seed"] = 1372
    (tmp_path / "INPUT.json").write_text(json.dumps({
        "row": trial, "case": {"prompt": "Compute 12."}, "source": str(SOURCE), "endpoint": ENDPOINT,
        "temperature": 0.3, "smoke": True,
    }))
    # The exact child entry point exercises imports, constructors and coroutine
    # argument binding. Stop just before the actual graph is advanced.
    script = """
import asyncio
import runpy
import socket
import sys
from pathlib import Path

class GraphInitialized(Exception):
    pass

def reject_network(*_args, **_kwargs):
    raise AssertionError("offline initialization attempted network I/O")

def inspect_graph(coroutine):
    try:
        assert Path(coroutine.cr_code.co_filename).is_relative_to(Path(sys.argv[3]))
        state = coroutine.cr_frame.f_locals["state"]
        deps = coroutine.cr_frame.f_locals["deps"]
        assert state.task_id == "trial"
        assert deps.primitives.mock_mode is False
        assert set(deps.primitives.server_urls.values()) == {sys.argv[4]}
        assert deps.config.max_escalations == 0
        from scripts.benchmark.seeding_scoring import score_answer_or_error
        assert score_answer_or_error("12", "12") == (True, None)
    finally:
        coroutine.close()
    raise GraphInitialized

asyncio.run = inspect_graph
socket.socket.connect = reject_network
try:
    runpy.run_path(sys.argv.pop(1), run_name="__main__")
except GraphInitialized:
    pass
else:
    raise AssertionError("child did not initialize the real graph")
"""
    process = subprocess.run([str(PYTHON), "-B", "-c", script, str(HERE / "graph_trial.py"),
                              str(tmp_path), str(tmp_path), str(SOURCE), ENDPOINT],
                             cwd=tmp_path, env=graph_env(trial, tmp_path, "offline-test"), text=True,
                             capture_output=True, timeout=20, check=False)
    assert process.returncode == 0, process.stderr


def test_sync_wire_capture_preserves_exact_bodies_and_errors(tmp_path):
    if not PYTHON.is_file():
        pytest.skip("orchestrator venv with HTTPX required")
    script = r"""
import hashlib
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, sys.argv[1])
from graph_trial import wire_hooks

root = Path(sys.argv[2])
original = b'{ "seed": 42, "prompt": "caf\\u00e9", "cache_prompt": true }\n'
sent = b'{"seed":42,"prompt":"caf\xc3\xa9","cache_prompt":false}'
replies = [(200, b'{ "content": "ok" }\n'), (502, b'{ "error": "transport" }\n')]
errors, wire = [], []
request_hook, response_hook = wire_hooks(root, 42, errors, wire)

def transport(req):
    assert req.content == req.read() == b"".join(req.stream) == sent
    assert req.headers["content-length"] == str(len(sent))
    assert req.headers["authorization"] == "Bearer auth-test-secret"
    if not replies:
        raise httpx.ConnectError("test connection failed", request=req)
    status, payload = replies.pop(0)
    return httpx.Response(status, stream=httpx.ByteStream(payload))

with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(transport),
                  event_hooks={"request": [request_hook], "response": [response_hook]},
                  headers={"Authorization": "Bearer auth-test-secret"}) as client:
    good = client.post("/completion", content=original)
    rejected = client.post("/v1/chat/completions", content=original)
    assert good.json() == {"content": "ok"}
    assert rejected.json() == {"error": "transport"}
    try:
        client.post("/completion", content=original)
    except httpx.ConnectError:
        pass
    else:
        raise AssertionError("expected transport failure")

assert errors == ["/v1/chat/completions: HTTP 502"]
for index, record in enumerate(wire):
    observed = json.loads((root / "wire" / f"{index:04}" / "record.json").read_bytes())
    assert observed == record
    for prefix, payload in (("original_request", original), ("request", sent)):
        assert (root / record[prefix + "_file"]).read_bytes() == payload
        assert record[prefix + "_sha256"] == hashlib.sha256(payload).hexdigest()
    if index < 2:
        response = (good, rejected)[index]
        assert record["http_status"] == response.status_code
        assert (root / record["response_file"]).read_bytes() == response.content
        assert record["response_sha256"] == hashlib.sha256(response.content).hexdigest()
    else:
        assert record["http_status"] is None
        assert "response_file" not in record
assert len(wire) == 3
assert all(b"auth-test-secret" not in path.read_bytes() for path in root.rglob("*") if path.is_file())
"""
    subprocess.run([str(PYTHON), "-B", "-c", script, str(HERE), str(tmp_path)], cwd=tmp_path,
                   check=True, timeout=20)


def test_wire_capture_tees_native_sse_parser_and_preserves_partial_bodies(tmp_path):
    if not PYTHON.is_file() or not SOURCE.is_dir():
        pytest.skip("pinned orchestrator trial worktree and venv required")
    script = r"""
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

sys.path[:0] = sys.argv[1:3]
from graph_trial import wire_hooks
from src.backends.llama_server import LlamaServerBackend
from src.model_server import InferenceRequest
from src.registry.registry_loader import RegistryLoader

root = Path(sys.argv[3])
errors, wire = [], []
request_hook, response_hook = wire_hooks(root, 42, errors, wire)
first = b'data: {"choices":[{"delta":{"content":"A"}}]}\r\n\r\n'
last = b'data: {"choices":[{"delta":{"content":"B"},"finish_reason":"stop"}]}\n\n'
done_left, done_right = b'data: [DO', b'NE]\r\n\r\n'
received = []

class Chunks(httpx.SyncByteStream):
    def __init__(self, mode):
        self.mode = mode
        self.closed = False

    def __iter__(self):
        yield first
        if self.mode == "backend":
            assert received == ["A"], "first delta was buffered"
            yield last
            assert received == ["A", "B"], "second delta was buffered"
            yield done_left
            yield done_right
            raise AssertionError("capture must not drain after the backend sees DONE")
        if self.mode == "failure":
            raise httpx.ReadError("truncated test SSE stream")
        if self.mode == "early":
            raise AssertionError("capture must not drain an early close")

    def close(self):
        self.closed = True

def test_result(record, expected, *, complete, exhausted, done, error=None):
    assert record["http_status"] == 200
    assert record["response_complete"] is complete
    assert record["response_transport_exhausted"] is exhausted
    assert record["response_sse_done"] is done
    assert record.get("response_error") == error
    assert (root / record["response_file"]).read_bytes() == expected
    assert record["response_sha256"] == hashlib.sha256(expected).hexdigest()

streams = [Chunks(mode) for mode in ("backend", "eof", "early", "failure")]
remaining = iter(streams)

def transport(req):
    assert req.url.path == "/v1/chat/completions"
    payload = json.loads(req.read())
    assert payload["cache_prompt"] is False and payload["stream"] is True and payload["seed"] == 42
    assert req.headers["authorization"] == "Bearer auth-test-secret"
    return httpx.Response(200, stream=next(remaining), headers={"Content-Type": "text/event-stream"})

with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(transport),
                  event_hooks={"request": [request_hook], "response": [response_hook]},
                  headers={"Authorization": "Bearer auth-test-secret"}) as client:
    backend = LlamaServerBackend(base_url="http://localhost")
    backend.client.close()
    backend.client = client
    registry = RegistryLoader(Path(sys.argv[2]) / "orchestration/model_registry.yaml", validate_paths=False)
    result = backend._infer_stream_text_chat_completions(
        registry.get_role("frontdoor"), InferenceRequest(role="frontdoor", prompt="REPL", n_tokens=64, seed=42),
        received.append, time.time())
    assert result.success and result.output == "AB"
    test_result(wire[0], first + last + done_left + done_right, complete=True, exhausted=False, done=True)

    req = {"seed": 42, "stream": True}
    with client.stream("POST", "/v1/chat/completions", json=req) as response:
        assert wire[1]["http_status"] == 200
        assert (root / wire[1]["response_file"]).read_bytes() == b"", "read before the consumer"
        assert b"".join(response.iter_raw()) == first
    test_result(wire[1], first, complete=True, exhausted=True, done=False)

    with client.stream("POST", "/v1/chat/completions", json=req) as response:
        iterator = response.iter_raw()
        assert next(iterator) == first
    test_result(wire[2], first, complete=False, exhausted=False, done=False)
    iterator.close()

    try:
        with client.stream("POST", "/v1/chat/completions", json=req) as response:
            list(response.iter_raw())
    except httpx.ReadError:
        pass
    else:
        raise AssertionError("expected SSE read failure")
    test_result(wire[3], first, complete=False, exhausted=False, done=False, error="ReadError")

assert all(stream.closed for stream in streams)
assert errors == ["/v1/chat/completions response capture: ReadError"]
assert all(b"auth-test-secret" not in path.read_bytes() for path in root.rglob("*") if path.is_file())
for index, record in enumerate(wire):
    assert json.loads((root / "wire" / f"{index:04}" / "record.json").read_bytes()) == record
"""
    subprocess.run([str(PYTHON), "-B", "-c", script, str(HERE), str(SOURCE), str(tmp_path)],
                   cwd=tmp_path, check=True, timeout=20)


def test_prior_runs_of_voided_points_are_kept_and_made_ineligible(tmp_path):
    points = [{"point_id": "item@2", "stratum": "early"}]
    reserves = {"early": [{"point_id": "next@2", "stratum": "early"}]}
    records = [
        {"run_id": "item@2|summary_only|r0", "point_id": "item@2", "status": "ok",
         "result": {"correct": True, "wall_s": 1.5, "baps": 0.2}},
        {"run_id": "item@2|summary_only|r1", "point_id": "item@2", "status": "void_point"},
        {"status": "replacement", "void": "item@2", "replacement": "next@2", "stratum": "early"},
        {"run_id": "next@2|summary_only|r0", "point_id": "next@2", "status": "ok",
         "result": {"correct": None, "wall_s": 2.5, "baps": 0.4}},
    ]
    (tmp_path / "ledger.jsonl").write_text("".join(json.dumps(rec) + "\n" for rec in records))
    summary = summarize_ledger(tmp_path, [row()], {"points": points, "reserves": reserves})
    runs = [json.loads(line) for line in (tmp_path / "RUNS.jsonl").read_text().splitlines()]
    assert summary["completed"] == 1
    assert summary["active_points"] == ["next@2"]
    assert summary["points_voided"] == ["item@2"]
    assert runs[0]["valid"] is False
    assert runs[0]["void_point"] is True
    assert runs[0]["baps"] is None
    assert runs[-1]["correct"] is None
    assert runs[-1]["valid"] is True
    assert summary["coverage_complete"] is False


@pytest.mark.parametrize("allocated,threads,expected", [
    ({0, 1, 2, 3, 96, 97, 98, 99}, "4", [0, 1, 2, 3]),
    ({0, 1, 2, 3}, "4", [0, 1, 2, 3]),
    ({96, 97, 98, 99}, "4", [96, 97, 98, 99]),
    ({0, 1, 2, 96, 97, 98}, "4", None),
    ({0, 1, 2, 3}, "3", None),
])
def test_grant_affinity_binding(monkeypatch, allocated, threads, expected):
    current = set(allocated)
    def bind(_pid, cpus):
        nonlocal current
        assert set(cpus) <= current
        current = set(cpus)
    monkeypatch.setenv("FILLER_THREADS", threads)
    monkeypatch.setattr(cpu_runner.os, "sched_getaffinity", lambda _: current)
    monkeypatch.setattr(cpu_runner.os, "sched_setaffinity", bind)
    if expected is None:
        with pytest.raises(ValueError):
            cpu_runner.bind_four_cores()
    else:
        assert cpu_runner.bind_four_cores() == expected
        assert current == set(expected)
