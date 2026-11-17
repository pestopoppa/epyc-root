"""Exact-body replay and failure gates using fake servers and HTTP responses."""

from threading import Event
from types import SimpleNamespace

import pytest

from test_kernel_promotion_resident_runner import FakeRuntime, plan, runner, write_json


class ReplayRuntime(FakeRuntime):
    def __init__(self, failure=None):
        super().__init__(failure=failure)
        self.mode = "resident"

    def verify_fresh_ready(self):
        assert not self.live
        self.events.append(("fresh_guard",))
        if self.failure == "stopped":
            raise InterruptedError("filler requested stop")
        self.mode = "fresh"

    def start(self, cohort, arm, directory):
        if self.mode == "resident" and self.failure == "unproved_spawn" and arm == "candidate":
            raise runner.SpawnCleanupUnproved("candidate launch cleanup is unproved")
        return super().start(cohort, arm, directory)

    def request(self, server, arm, body):
        assert server.arm == arm
        expected = {arm} if self.mode == "fresh" else set(runner.resident_plan.ARMS)
        assert self.live == expected
        self.events.append((self.mode, server.proc.pid, arm, body))
        limit = body[runner.token_limit_field(body)]
        if self.mode == "resident" and limit != runner.resident_plan.WARMUP_TOKENS:
            raise TimeoutError("resident measured request failed")
        return {"completion_tokens": limit}

    def stop(self, server):
        record = super().stop(server)
        if self.mode == "fresh" and self.failure == "fresh_port_leak":
            record["port_closed"] = False
        return record


def test_resident_failure_replays_full_schedule_exactly(tmp_path):
    cohorts = [
        {key: cohort[key] for key in runner.resident_plan.COHORT_FIELDS}
        for cohort in plan()["cohorts"]
    ]
    cohorts[1]["request_body"] = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Δ"}]}],
        "max_tokens": 128, "cache_prompt": False, "temperature": 0, "seed": 7,
    }
    schedule = runner.resident_plan.build_plan(cohorts)
    original = runner.resident_plan._canonical_json(schedule)
    runtime = ReplayRuntime()
    output = tmp_path / "capture"
    assert runner.execute_plan(schedule, output, runtime) == runner.FRESH_REQUIRED
    assert runner.resident_plan._canonical_json(schedule) == original
    assert runtime.events.count(("preflight",)) == 2
    assert runtime.events[:runtime.events.index(("fresh_guard",))][-3:] == [
        ("stop", "candidate"), ("stop", "production"), ("preflight",),
    ]
    fallback = runner.read_json(output / "fresh-fallback.json")
    assert fallback["plan"] == schedule
    assert fallback["fresh_attempted"] and fallback["fresh_complete"]
    assert not fallback["requires_fresh_execution"] and not fallback["resident_rows_valid"]
    assert not runner.read_json(output / "capture.json")["complete"]

    fresh = output / "fresh-replay"
    capture = runner.read_json(fresh / "capture.json")
    assert capture["status"] == "observation_only" and capture["lifecycle_mode"] == "fresh_server"
    assert capture["schedule_sha256"] == schedule["schedule_sha256"]
    assert capture["complete"] and capture["cleanup_proved"] and not runtime.live
    events = iter(event for event in runtime.events if event[0] == "fresh")
    pids = set()
    for index, (cohort, observed) in enumerate(zip(schedule["cohorts"], capture["cohorts"], strict=True)):
        body = cohort["request_body"]
        warmup_body = body | {runner.token_limit_field(body): runner.resident_plan.WARMUP_TOKENS}
        for row, observed_row in zip(cohort["requests"], observed["requests"], strict=True):
            warmup, measured = next(events), next(events)
            pid = observed_row["server"]["pid"]
            assert pid not in pids
            pids.add(pid)
            assert warmup[1:] == (pid, row["arm"], warmup_body)
            assert measured[1:] == (pid, row["arm"], body)
            directory = fresh / f"cohort-{index:03}" / f"request-{row['schedule_position']:03}"
            assert runner.read_json(directory / "request.json") == body
            assert runner.read_json(directory / "warmup/row.json")["excluded"] is True
            assert {key: observed_row[key] for key in row} == row
            assert observed_row["cleanup"]["dead"] and observed_row["cleanup"]["port_closed"]
            assert observed_row["complete"]
    assert next(events, None) is None


@pytest.mark.parametrize("failure", ["unproved_spawn", "terminate", "port_leak"])
def test_unproved_resident_cleanup_blocks_replay(tmp_path, failure):
    runtime = ReplayRuntime(failure=failure)
    output = tmp_path / "capture"
    assert runner.execute_plan(plan(), output, runtime) == runner.FRESH_REQUIRED
    assert ("fresh_guard",) not in runtime.events
    assert not (output / "fresh-replay").exists()
    fallback = runner.read_json(output / "fresh-fallback.json")
    assert not fallback["cleanup_proved"] and not fallback["fresh_attempted"]


def test_stop_at_fresh_guard_prevents_any_replay_launch(tmp_path):
    runtime = ReplayRuntime(failure="stopped")
    output = tmp_path / "capture"
    assert runner.execute_plan(plan(), output, runtime) == runner.FRESH_REQUIRED
    assert runtime.events[-1] == ("fresh_guard",)
    fallback = runner.read_json(output / "fresh-fallback.json")
    assert fallback["cleanup_proved"] and not fallback["fresh_attempted"]
    capture = runner.read_json(output / fallback["fresh_capture"])
    assert "filler requested stop" in capture["failure"] and not capture["cohorts"]


def test_standalone_fresh_stops_after_unproved_cleanup(tmp_path):
    runtime = ReplayRuntime(failure="fresh_port_leak")
    output = tmp_path / "fresh"
    capture = runner.execute_fresh_plan(plan(), output, runtime)
    assert capture == runner.read_json(output / "capture.json")
    assert capture["attempted"] and not capture["complete"] and not capture["cleanup_proved"]
    assert [event for event in runtime.events if event[0] == "start"] == [("start", "production")]
    assert capture["cohorts"][0]["requests"][0]["cleanup"]["port_closed"] is False


def test_inside_query_affinity_failure_preserves_raw_response_and_refuses_row(tmp_path, monkeypatch):
    checking = Event()
    querying = Event()
    raw_response = {"content": "unchanged", "completion_tokens": 128}

    def query_chat(port, body, *, timeout_s, endpoint):
        assert (port, endpoint) == (19100, "completion")
        querying.set()
        assert checking.wait(2)
        return raw_response

    def check_affinity(server):
        assert querying.is_set()
        checking.set()
        raise runner.affinity_guard.AffinityError("thread exceeds granted CPU set")

    k35 = SimpleNamespace(query_chat=query_chat, write_json=write_json)
    runtime = runner.Runtime(k35, SimpleNamespace(request_timeout=2, claim_open=None))
    monkeypatch.setattr(runner, "verify_claim", lambda path: {})
    monkeypatch.setattr(runtime, "timeout", lambda timeout, claim: timeout)
    monkeypatch.setattr(runtime, "verify_server", lambda server, arm: None)
    monkeypatch.setattr(runtime, "affinity", check_affinity)
    server = SimpleNamespace(port=19100)
    with pytest.raises(runner.RequestAffinityError, match="exceeds granted CPU set"):
        runner.request_with_capture(runtime, server, "production", plan()["cohorts"][0]["request_body"], tmp_path)
    assert runner.read_json(tmp_path / "response.json") == raw_response
    assert "exceeds granted CPU set" in runner.read_json(tmp_path / "request-affinity.json")["failure"]
    assert not (tmp_path / "row.json").exists()


@pytest.mark.parametrize("sampled", [True, False])
def test_query_requires_a_completed_in_flight_scan(tmp_path, monkeypatch, sampled):
    second_check = Event()
    scans = []
    raw_response = {"content": "unchanged"}

    def check_affinity(server):
        scans.append({100: [0]})
        if len(scans) == 2:
            second_check.set()
        return scans[-1]

    def query_chat(*args, **kwargs):
        if sampled:
            assert second_check.wait(2)
        return raw_response

    k35 = SimpleNamespace(query_chat=query_chat, write_json=write_json)
    runtime = runner.Runtime(k35, SimpleNamespace(request_timeout=2, claim_open=None))
    monkeypatch.setattr(runner, "verify_claim", lambda path: {})
    monkeypatch.setattr(runner, "AFFINITY_SAMPLE_INTERVAL", 0.01 if sampled else 10)
    monkeypatch.setattr(runtime, "timeout", lambda timeout, claim: timeout)
    monkeypatch.setattr(runtime, "verify_server", lambda server, arm: None)
    monkeypatch.setattr(runtime, "affinity", check_affinity)
    server = SimpleNamespace(port=19100)
    arguments = runtime, server, "production", plan()["cohorts"][0]["request_body"], tmp_path
    if sampled:
        response, _ = runner.request_with_capture(*arguments)
        assert response == raw_response
    else:
        with pytest.raises(runner.RequestAffinityError, match="no affinity scan completed"):
            runner.request_with_capture(*arguments)
        assert runner.read_json(tmp_path / "response.json") == raw_response
    witness = runner.read_json(tmp_path / "request-affinity.json")
    assert bool(witness["sample_offsets_s"]) is sampled
    assert all(0 < offset <= witness["query_elapsed_s"] for offset in witness["sample_offsets_s"])
    assert witness["first_sample_affinity"] == ({"100": [0]} if sampled else None)
