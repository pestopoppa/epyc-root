import json
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import controls
import pytest
from semantic import canonical


@pytest.mark.parametrize("payload, reason", (
    ({"choices": [{"finish_reason": "stop", "message": {"content": "invalid JSON"}}]},
     "invalid_evaluator_response"),
    ({"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
     "invalid_evaluator_transport_response"),
))
def test_invalid_control_is_preserved_and_marked_unknown(tmp_path, monkeypatch, payload, reason):
    def fake_http(route, timeout, body):
        assert route == "/v1/chat/completions"
        assert timeout > 0
        user = json.loads(body["messages"][1]["content"])
        assert set(user) == {"reference", "observed_messages", "request_id"}
        return canonical(payload)

    monkeypatch.setitem(sys.modules, "cmp2_runner", SimpleNamespace(
        json_bytes=canonical,
        http=fake_http,
        remaining=lambda _deadline: 100,
        atomic_json=lambda path, data: path.write_bytes(canonical(data)),
    ))
    evaluate = runpy.run_path(str(Path(__file__).with_name("runner.py")))["evaluate"]
    result = evaluate(controls.cases()[1], "mock-evaluator", tmp_path, 1, 100)
    assert result["literal_delivered"] is True
    assert result["semantic_verdict"] == "unknown"
    assert result["reason"] == reason
    assert result["control_pass"] is False
    attempt = tmp_path / "attempt-01"
    assert json.loads((attempt / "VERDICT.json").read_bytes()) == result
    assert (attempt / "response.json").read_bytes() == canonical(payload)


def test_full_runner_records_seven_cases_and_reaps_only_its_server(tmp_path, monkeypatch):
    controls_schedule = controls.cases()
    replay = [{"case": {**controls_schedule[0]["case"], "unit": f"native-{i}"}, "expected": None}
              for i in range(4)]
    schedule = controls_schedule + replay
    alias = "toc-cmp-3-semantic-qwen3-4b"
    requests = []

    def fake_http(_route, _timeout, body):
        row = schedule[len(requests)]
        case = row["case"]
        user = json.loads(body["messages"][1]["content"])
        requests.append(user["request_id"])
        quotes = controls.PARAPHRASE
        if case["unit"] == "control/folded-conflict":
            quotes = {**controls.REFERENCE, "pinned_governance":
                      "Send the receipt to the external reviewer before reporting the ID."}
        expected = row["expected"] or dict.fromkeys(controls.REFERENCE, "entailed")
        judgments = {field: {"verdict": label, "rationale": "Fixture evaluator result.",
                             "evidence": [] if label == "unknown" else [{"message": 0, "quote": quotes[field]}]}
                     for field, label in expected.items()}
        content = canonical({"request_id": user["request_id"], "judgments": judgments}).decode("utf-8")
        return canonical({"choices": [{"finish_reason": "stop", "message": {"content": content}}]})

    class FakeServer:
        pid = 100_001
        exited = False

        def poll(self):
            return 0 if self.exited else None

        def terminate(self):
            self.exited = True

        def wait(self, timeout):
            assert timeout == 5
            assert self.exited

    def atomic_json(path, data):
        path.write_bytes(canonical(data))

    fake = FakeServer()
    monkeypatch.setitem(sys.modules, "cmp2_runner", SimpleNamespace(
        json_bytes=canonical,
        http=fake_http,
        remaining=lambda _deadline: 100,
        atomic_json=atomic_json,
        bind_four_cores=lambda: [0, 1, 2, 3],
        server_ready=lambda *_: {"data": [{"id": alias}]},
        server_identity=lambda *_: {"pid": fake.pid},
        owns_listener=lambda pid: pid == fake.pid,
    ))
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout="fixture linkage"))
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: fake)
    monkeypatch.setenv("FILLER_ID", "toc-cmp-3-semantic-20261118")
    monkeypatch.setenv("FILLER_DRYRUN", "0")
    monkeypatch.setenv("FILLER_DEADLINE", "4000000000")
    monkeypatch.setenv("FILLER_PIDFILE", str(tmp_path / "pids"))
    run = runpy.run_path(str(Path(__file__).with_name("runner.py")))["run"]
    monkeypatch.setattr(run.__globals__["signal"], "signal", lambda *_: None)
    monkeypatch.setitem(run.__globals__, "SCRATCH", tmp_path)
    monkeypatch.setitem(run.__globals__, "verify", lambda: (
        {"sha256": "manifest", "bin_dir": str(tmp_path), "model": {"path": "fixture.gguf"}}, schedule))
    assert run() == 0
    result = json.loads((tmp_path / "native/RESULT.json").read_bytes())
    assert result["completed"] == 7
    assert result["coverage_complete"] is True
    assert result["server_exited"] is True
    assert requests == [row["case"]["request_id"] for row in schedule]
    assert (tmp_path / "pids").read_text() == f"{fake.pid}\n"
