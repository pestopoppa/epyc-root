import io
import json
import os
import sys

import pytest

from scripts.harness import hs4_file_transport as transport


def test_live_refusal_precedes_http_and_process_io(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("live transport invoked before isolation proof")
    monkeypatch.setattr(transport, "urlopen", forbidden)
    monkeypatch.setattr(transport, "_process", forbidden)
    with pytest.raises(RuntimeError, match="isolation"):
        transport.run_repl("http://localhost:8000", {}, timeout_s=5)
    with pytest.raises(RuntimeError, match="isolation"):
        transport.run_opencode(tmp_path / "binary", tmp_path, tmp_path / "config", "prompt",
                               timeout_s=5, env={})


def test_repl_transport_captures_exact_request_and_response_in_mock(monkeypatch):
    monkeypatch.setattr(transport, "_require_live_isolation", lambda: None)
    seen = []
    class Response(io.BytesIO):
        status = 200
    raw = b'{"answer":"done","prompt_tokens":3,"output_tokens_reported":2,"output_tokens_status":"reported"}'
    def open_fake(request, *, timeout):
        seen.append((request.full_url, request.data, timeout))
        return Response(raw)
    monkeypatch.setattr(transport, "urlopen", open_fake)
    out = transport.run_repl("http://localhost:8000", {"prompt": "fixture"}, timeout_s=3)
    assert seen == [("http://localhost:8000/chat", b'{"prompt":"fixture"}', 3)]
    assert out["response_body"] == raw.decode() and out["observation"]["answer"] == "done"


def test_opencode_transport_retains_run_and_export_without_shell(monkeypatch, tmp_path):
    monkeypatch.setattr(transport, "_require_live_isolation", lambda: None)
    config = tmp_path / "opencode.jsonc"
    config.write_text("{}")
    events = [{"sessionID": "ses-1", "type": "text"}]
    session = {"messages": [{"info": {"role": "assistant"}, "parts": [{"type": "text", "text": "done"}]}]}
    calls = []
    def process(argv, **kwargs):
        calls.append((argv, kwargs))
        return {"pid": 123, "start_ticks": 99, "returncode": 0, "timed_out": False,
                "stdout": json.dumps(events[0]) if len(calls) == 1 else json.dumps(session), "stderr": ""}
    monkeypatch.setattr(transport, "_process", process)
    out = transport.run_opencode(tmp_path / "opencode", tmp_path, config, "task", timeout_s=3, env={"PATH": "/bin"})
    assert calls[0][0][1:] == ["run", "--format", "json", "--title", "hs4-file-trial"]
    assert calls[1][0][1:] == ["export", "ses-1"]
    assert calls[0][1]["stdin"] == "task" and calls[0][1]["env"]["OPENCODE_CONFIG"] == str(config)
    assert out["run"]["pid"] == 123 and out["run"]["start_ticks"] == 99
    assert out["observation"]["session"] == session and out["observation"]["events"] == events


def test_timeout_drains_captured_direct_child_and_descendant(tmp_path):
    source = (
        "import subprocess,sys,time; "
        "c=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        "print(c.pid,flush=True); time.sleep(30)"
    )
    result = transport._process([sys.executable, "-c", source], cwd=tmp_path,
                                env=dict(os.environ), stdin="", timeout_s=0.3)
    assert result["timed_out"] is True
    assert result["drain"]["remaining"] == []
    child_pid = int(result["stdout"].strip())
    captured = {item["pid"] for item in result["drain"]["captured"]}
    assert {result["pid"], child_pid} <= captured
    for pid in captured:
        record = transport._identity(pid)
        assert record is None or record[0] == "Z"


def test_signal_refuses_pid_reuse_and_dead_process(monkeypatch):
    sent = []
    monkeypatch.setattr(transport.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    monkeypatch.setattr(transport, "_identity", lambda _pid: ("S", 1, 8))
    transport._signal_owned(123, 7, 15)
    assert sent == []
    monkeypatch.setattr(transport, "_identity", lambda _pid: ("Z", 1, 7))
    transport._signal_owned(123, 7, 15)
    assert sent == []
    monkeypatch.setattr(transport, "_identity", lambda _pid: ("S", 1, 7))
    transport._signal_owned(123, 7, 15)
    assert sent == [(123, 15)]
