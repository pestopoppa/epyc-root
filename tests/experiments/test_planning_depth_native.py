"""Local HTTP software controls; no model or inference server is exercised."""
import base64
from contextlib import contextmanager
import http.server
import importlib.util
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "planning_depth_native", ROOT / "scripts/experiments/planning_depth/native.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
episode_spec = importlib.util.spec_from_file_location(
    "planning_depth_episode_integration", ROOT / "scripts/experiments/planning_depth/episode.py")
episode = importlib.util.module_from_spec(episode_spec)
episode_spec.loader.exec_module(episode)


@contextmanager
def endpoint(body=b'{"choices":[]}', *, status=200, declared=None, stall=None):
    release = threading.Event()
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            if stall == "headers":
                self.wfile.write(b"HTTP/1.0 200 OK\r\n")
                self.wfile.flush()
                release.wait(2)
                return
            self.send_response(status)
            self.send_header("Content-Length", str(len(body) if declared is None else declared))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            if stall == "body":
                release.wait(2)

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        release.set()
        thread.join(2)
        server.server_close()
        assert not thread.is_alive()


def test_native_request_and_response_are_retained_unmodified():
    records = []
    body = b'{"choices":[], "vendor_extension":{"x":1}}'
    with endpoint(body) as (url, requests):
        reply = native.NativeCompletion(url, records.append)({"model": "pin", "tools": []}, 1)
    assert reply == json.loads(body)
    assert requests == [("/v1/chat/completions", {"model": "pin", "tools": []})]
    assert records[0]["complete"] and records[0]["status"] == 200
    assert base64.b64decode(records[0]["body_base64"]) == body


@pytest.mark.parametrize("kwargs,match", [
    ({"body": b"bad json"}, "invalid native JSON"),
    ({"status": 302}, "HTTP status 302"),
    ({"status": 500}, "HTTP status 500"),
    ({"body": b"short", "declared": 100}, "truncated"),
])
def test_transport_errors_retain_native_bytes(kwargs, match):
    records = []
    with endpoint(**kwargs) as (url, _):
        with pytest.raises(OSError, match=match):
            native.NativeCompletion(url, records.append)({}, 1)
    assert base64.b64decode(records[0]["body_base64"]) == kwargs.get("body", b'{"choices":[]}')


def test_response_byte_bound_retains_bounded_partial():
    records = []
    with endpoint(b"x" * 100) as (url, _):
        with pytest.raises(OSError, match="byte bound"):
            native.NativeCompletion(url, records.append, max_bytes=10)({}, 1)
    assert len(base64.b64decode(records[0]["body_base64"])) == 11
    assert not records[0]["complete"]


@pytest.mark.parametrize("stall", ["headers", "body"])
def test_wall_deadline_interrupts_incomplete_http(stall):
    records = []
    with endpoint(b"partial", declared=100, stall=stall) as (url, _):
        started = time.monotonic()
        with pytest.raises(OSError):
            native.NativeCompletion(url, records.append)({}, 0.1)
        assert time.monotonic() - started < 1
    assert not records[0]["complete"]


@pytest.mark.parametrize("url", [
    "http://localhost:8000/v1", "http://192.0.2.1:8000/v1", "https://127.0.0.1:8000/v1",
    "http://127.0.0.1/v1", "http://user:password@127.0.0.1:8000/v1",
    "http://127.0.0.1:8000/other", "http://127.0.0.1:8000/v1?redirect=1",
])
def test_endpoint_refusal_is_offline(url):
    with pytest.raises(ValueError):
        native.NativeCompletion(url, lambda _: None)


def test_journal_exclusive_with_immutable_custody_and_synced_receipts(tmp_path, monkeypatch):
    synced = []
    original = native.os.fsync

    def fsync(fd):
        synced.append(fd)
        original(fd)

    monkeypatch.setattr(native.os, "fsync", fsync)
    path = tmp_path / "episode.jsonl"
    envelope = {"protocol_sha256": "pin", "arm": "critic", "case": "case-1"}
    with native.DurableJournal(path, envelope) as journal:
        envelope["arm"] = "mutated"
        journal({"event": "request", "payload": {"model": "pin"}})
        records = [json.loads(line) for line in path.read_text().splitlines()]
        assert [r["sequence"] for r in records] == [0, 1]
        assert all(r["custody"]["arm"] == "critic" for r in records)
        assert len(synced) == 3  # start, directory entry, request
    with pytest.raises(FileExistsError):
        native.DurableJournal(path, envelope)


def test_capture_failure_is_fatal_instead_of_transport_unknown():
    def capture(_):
        raise OSError("disk full")

    with endpoint() as (url, _):
        with pytest.raises(native.CaptureError, match="receipt lost"):
            native.NativeCompletion(url, capture)({}, 1)


def test_journal_fsync_failure_is_fatal(tmp_path, monkeypatch):
    path = tmp_path / "episode.jsonl"
    with native.DurableJournal(path, {"arm": "pin"}) as journal:
        def fail(_):
            raise OSError("disk full")
        monkeypatch.setattr(native.os, "fsync", fail)
        with pytest.raises(native.CaptureError):
            journal({"event": "response"})
        assert journal.sequence == 1


@pytest.mark.parametrize("malformed", [False, True])
def test_episode_transport_journal_integration(tmp_path, malformed):
    body = b"invalid" if malformed else json.dumps({
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "done"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }).encode()
    scored = []
    environment = SimpleNamespace(tools=[], score=lambda text: scored.append(text) or {"correct": False})
    path = tmp_path / "episode.jsonl"
    with endpoint(body) as (url, _), native.DurableJournal(path, {"arm": "test"}) as journal:
        result = episode.run_episode(native.NativeCompletion(url, journal), environment,
                                     [], journal, model="pin", seed=1)
        journal({"event": "episode_end", "result": result})
    records = [json.loads(line)["record"] for line in path.read_text().splitlines()]
    assert [r["event"] for r in records[:3]] == ["episode_start", "request", "native_http"]
    assert result["status"] == ("UNKNOWN" if malformed else "GRADED")
    assert scored == ([] if malformed else ["done"])
    assert records[-1]["result"] == result
