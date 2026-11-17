"""Lifecycle failures and the observation-only fallback contract."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark/kernel_promotion_resident_runner.py"
SPEC = importlib.util.spec_from_file_location("kernel_promotion_resident_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def write_json(path, value):
    path.write_text(json.dumps(value))


def plan():
    return runner.resident_plan.build_plan([
        {
            "scenario": "frontdoor",
            "nominal_context": context,
            "request_body": {"prompt": "benchmark", "seed": 42, "cache_prompt": False,
                             "temperature": 0, "n_predict": 128},
        }
        for context in (2048, 4096)
    ])


class FakeRuntime:
    def __init__(self, failure=None):
        self.failure = failure
        self.events = []
        self.live = set()
        self.k35 = SimpleNamespace(
            write_json=write_json,
            scenario_by_name=lambda name: name,
            summarize_response=lambda scenario, context, limit, response, elapsed, floor: response,
        )

    def preflight(self, output):
        self.events.append(("preflight",))
        if self.failure == "claim":
            raise ValueError("invalid live claim")

    def start(self, cohort, arm, directory):
        self.events.append(("start", arm))
        if self.failure == "spawn" and arm == "candidate":
            raise OSError("candidate spawn failed")
        handle = SimpleNamespace(arm=arm, proc=SimpleNamespace(pid=len(self.events)))
        self.live.add(arm)
        return handle

    def ready(self, server, arm, directory):
        self.events.append(("ready", arm))
        assert server.arm == arm
        if self.failure == "health" and arm == "candidate":
            raise TimeoutError("candidate failed health")
        if self.failure == "register_and_terminate" and arm == "candidate":
            raise OSError("candidate PID registration failed")
        return {"pid": server.proc.pid}

    def sample(self, server):
        assert server.arm in self.live
        busy = self.failure == "idle_peer" and len(self.events) >= 8
        return {"cpu_s": float(len(self.events)) if busy else 0.0, "rss_bytes": 10}

    def affinity(self, server):
        assert server.arm in self.live
        return {server.proc.pid: [0]}

    def request(self, server, arm, body):
        assert self.live == {"production", "candidate"}
        assert server.arm == arm
        self.events.append(("request", arm, body))
        if self.failure == "request" and body["n_predict"] != 64:
            raise TimeoutError("measured request timed out")
        if self.failure == "short" and body["n_predict"] != 64:
            return {"completion_tokens": 1}
        return {"completion_tokens": body["n_predict"]}

    def stop(self, server):
        self.events.append(("stop", server.arm))
        if self.failure in {"terminate", "register_and_terminate"} and server.arm == "candidate":
            raise RuntimeError("cleanup witness failed")
        self.live.remove(server.arm)
        return {"pid": server.proc.pid, "dead": True,
                "port_closed": self.failure != "port_leak"}


def test_validated_plan_runs_sequential_loads_warmups_and_abba(tmp_path):
    schedule = plan()
    runtime = FakeRuntime()
    output = tmp_path / "capture"
    assert runner.execute_plan(schedule, output, runtime) == 0
    assert runtime.events[1:5] == [
        ("start", "production"), ("ready", "production"),
        ("start", "candidate"), ("ready", "candidate"),
    ]
    requests = [event for event in runtime.events if event[0] == "request"]
    for index, cohort in enumerate(schedule["cohorts"]):
        warmup_a, warmup_b, *requested = requests[index * 22:(index + 1) * 22]
        assert [warmup_a[1], warmup_b[1]] == ["production", "candidate"]
        assert warmup_a[2] == warmup_b[2] == cohort["request_body"] | {"n_predict": 64}
        assert [event[1] for event in requested] == [row["arm"] for row in cohort["requests"]]
        assert all(event[2] == cohort["request_body"] for event in requested)
        assert runner.read_json(output / f"cohort-{index:03}/warmup-production/row.json")["excluded"]
    report = runner.read_json(output / "capture.json")
    assert report["status"] == "observation_only"
    assert report["complete"] is True
    assert not runtime.live
    assert not (output / "fresh-fallback.json").exists()


@pytest.mark.parametrize(
    ("failure", "stopped", "cleanup_proved"),
    [
        ("claim", [], True), ("spawn", ["production"], True),
        ("health", ["candidate", "production"], True),
        ("request", ["candidate", "production"], True),
        ("short", ["candidate", "production"], True),
        ("idle_peer", ["candidate", "production"], True),
        ("terminate", ["candidate", "production"], False),
        ("register_and_terminate", ["candidate", "production"], False),
        ("port_leak", ["candidate", "production"], False),
    ],
)
def test_failure_cleans_captured_servers_and_reemits_plan(tmp_path, failure, stopped, cleanup_proved):
    schedule = plan()
    runtime = FakeRuntime(failure=failure)
    output = tmp_path / "capture"
    assert runner.execute_plan(schedule, output, runtime) == runner.FRESH_REQUIRED
    assert [event[1] for event in runtime.events if event[0] == "stop"] == stopped
    if cleanup_proved:
        assert not runtime.live
    fallback = runner.read_json(output / "fresh-fallback.json")
    assert fallback["lifecycle_mode"] == "fresh_server"
    assert fallback["status"] == "observation_only"
    assert fallback["plan"] == schedule
    assert fallback["cleanup_proved"] is cleanup_proved
    assert fallback["requires_fresh_execution"] is True
    assert fallback["resident_rows_valid"] is False
    report = runner.read_json(output / "capture.json")
    assert report["complete"] is False
    assert report["cleanup_proved"] is cleanup_proved
    assert len(report["cohorts"]) <= 1


def test_mutated_plan_does_not_enter_preflight_or_create_capture(tmp_path):
    mutated = plan()
    mutated["cohorts"][0]["requests"][0]["arm"] = "candidate"
    runtime = FakeRuntime()
    output = tmp_path / "capture"
    with pytest.raises(ValueError, match="canonical resident schedule"):
        runner.execute_plan(mutated, output, runtime)
    assert not runtime.events
    assert not output.exists()


def test_pidfd_cleanup_leaves_unrelated_process_running(monkeypatch):
    unrelated = subprocess.Popen(["/usr/bin/sleep", "60"])
    proc, fd, birth = runner.owned.spawn(["/usr/bin/sleep", "60"], env=os.environ.copy())
    monkeypatch.setattr(runner, "port_listeners", lambda port: set())
    runtime = runner.Runtime(None, None)
    try:
        cleanup = runtime.stop(runner.Server(proc, fd, birth, 19100, {0}))
        assert cleanup["pid"] == proc.pid
        assert cleanup["dead"] and cleanup["port_closed"]
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_port_ownership_matches_listener_inode():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert runner.owns_listener(os.getpid(), port)
    assert not runner.port_listeners(port)


@dataclass
class NarrowRecipe:
    cpu_affinity: str = "24-47"
    slot_save_path: str = "/production-slot-cache"


def test_command_preserves_explicit_narrow_k35_placement():
    scenario = NarrowRecipe()

    def argv(recipe, *, binary, **kwargs):
        assert recipe.slot_save_path is None
        return ["numactl", "--interleave=all", "--", "taskset", "-c", recipe.cpu_affinity, str(binary)]

    k35 = SimpleNamespace(scenario_by_name=lambda name: scenario, build_server_argv=argv)
    runtime = runner.Runtime(k35, SimpleNamespace(production_binary=Path("/sealed/llama-server"), kv_mode="split"))
    assert runtime.command(plan()["cohorts"][0], "production", 19100)[3:6] == ["taskset", "-c", "24-47"]
    scenario.cpu_affinity = "96-119"
    with pytest.raises(ValueError, match="exceeds"):
        runtime.command(plan()["cohorts"][0], "production", 19100)


def test_post_request_image_failure_preserves_response(tmp_path, monkeypatch):
    args = SimpleNamespace(request_timeout=1, claim_open=tmp_path / "claim")
    response = {"content": "raw response", "tokens": [1]}
    k35 = SimpleNamespace(write_json=write_json, query_chat=lambda *args, **kwargs: response)
    runtime = runner.Runtime(k35, args)
    runtime.evidence = object()

    def verify_server(*_):
        if checks:
            raise ValueError("changed mapped inode")
        checks.append(True)

    checks = []
    monkeypatch.setattr(runner, "verify_claim", lambda path: {})
    monkeypatch.setattr(runner, "AFFINITY_SAMPLE_INTERVAL", 0.001)
    monkeypatch.setattr(runtime, "timeout", lambda *args: 1)
    monkeypatch.setattr(runtime, "verify_server", verify_server)
    sampled = runner.threading.Event()

    def affinity(_):
        sampled.set()
        return {10: [0]}

    def query(*args, **kwargs):
        assert sampled.wait(1)
        runner.time.sleep(0.01)
        return response

    monkeypatch.setattr(runtime, "affinity", affinity)
    k35.query_chat = query
    with pytest.raises(runner.CapturedResponseError, match="post-request image witness failed"):
        runner.request_with_capture(runtime, SimpleNamespace(port=19100), "production", {"n_predict": 1}, tmp_path)
    assert runner.read_json(tmp_path / "response.json") == response
    assert not (tmp_path / "row.json").exists()
