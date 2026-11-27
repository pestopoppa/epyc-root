"""Regress output-bound, candidate-custody and transport failures seen in the A3B pilot."""
from contextlib import closing
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/coordination"))

from taskflow.harness.opencode_derived.__main__ import load_job
from taskflow.harness.opencode_derived.case_snapshot import candidate_state, digest, file_map
from taskflow.harness.opencode_derived.transport import Limits, proxy


class FixtureModel(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(request)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if request.get("stream") else "application/json")
        self.end_headers()
        if not request.get("stream"):
            self.wfile.write(b'{"choices":[{"message":{"content":"fixture"},"finish_reason":"stop"}],'
                             b'"usage":{"prompt_tokens":11,"completion_tokens":2}}')
            return
        try:
            for _ in range(40):
                self.wfile.write(b'data: {"choices":[{"delta":{"reasoning_content":"fixture"}}]}\n\n')
                self.wfile.flush()
                time.sleep(0.025)
        except ConnectionError:
            pass


@pytest.fixture
def model():
    with ThreadingHTTPServer(("127.0.0.1", 0), FixtureModel) as server:
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        yield server
        server.shutdown()


def post(port, **fields):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=2)) as conn:
        conn.request("POST", "/v1/chat/completions", json.dumps({"model": "q35-a3b",
            "messages": [{"role": "user", "content": "Fixture"}], **fields}), {"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, response.read()


def test_tool_and_metadata_limits_serialize_one_recognized_alias_with_no_lost_reservations(model, tmp_path):
    limits = Limits(wall_s=5, output_cap=8192, cumulative_output=120000)
    tools = [{"type": "function", "function": {"name": "execute", "parameters": {"type": "object"}}}]
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=2, task="fixture", label="run",
               thinking=True, preserve_resume=True) as adapter:
        assert post(adapter.server_port, maxOutputTokens=123)[0] == 200
        assert post(adapter.server_port, n_predict=100000, max_completion_tokens=32768, tools=tools)[0] == 200
        assert post(adapter.server_port, n_cmpl=2)[0] == 400
        assert post(adapter.server_port, chat_template_kwargs=[["bad"]])[0] == 400
    side, primary = model.requests
    assert side["max_completion_tokens"] == 123 and "tools" not in side
    assert primary["max_completion_tokens"] == 8192 and primary["tools"] == tools
    for request in (side, primary):
        assert "maxOutputTokens" not in request and "n_predict" not in request
        assert request["chat_template_kwargs"] == {"enable_thinking": True, "preserve_reasoning": True,
                                                   "preserve_thinking": True}
        assert request["id_slot"] == 2
    assert limits.pending == 0 and limits.observed == 4 and limits.unknown == 0
    rejected = [json.loads(line) for line in (tmp_path / "adapter-rejections.jsonl").read_text().splitlines()]
    assert [r["http_status"] for r in rejected] == [400, 400] and all(not r["reserved"] for r in rejected)
    assert all(row["ttft_s"] is None and row["first_body_s"] is not None for row in adapter.rows)


def test_steady_stream_still_stops_at_absolute_deadline(model, tmp_path):
    limits = Limits(wall_s=0.4, output_cap=8192, cumulative_output=120000)
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=0, task="fixture", label="timeout",
               thinking=True) as adapter:
        begin = time.monotonic()
        assert post(adapter.server_port, stream=True)[0] == 200
        assert time.monotonic() - begin < 0.9
    row, = adapter.rows
    assert row["transport_error"] and row["ttft_s"] is not None and not row["generation_complete"]
    assert limits.pending == 0 and limits.unknown == 1 and limits.charged == 8192


def test_runtime_artifacts_are_recorded_and_only_exact_new_cache_paths_are_excluded():
    baseline = {"pkg/__pycache__/existing.pyc": {"sha256": "old"}}
    observed = {**baseline, ".pytest_cache/v/cache/nodeids": {}, "pkg/__pycache__/new.pyc": {},
                "pkg/__pycache__/wrong.py": {}, ".pytest_cache/side.py": {}}
    candidate, runtime = candidate_state(baseline, observed)
    assert set(runtime) == {".pytest_cache/v/cache/nodeids", "pkg/__pycache__/new.pyc"}
    assert set(candidate) == set(observed) - set(runtime)


def test_model_free_entrypoint_verifies_approval_and_all_case_bytes(tmp_path):
    case = tmp_path / "case"
    baseline = case / "baseline"
    baseline.mkdir(parents=True)
    (baseline / "input.txt").write_text("pinned source")
    (case / "oracle.py").write_text("pass")
    (case / "prompt.md").write_text("Task fixture")
    known, unsafe = file_map(baseline)
    assert not unsafe
    (case / "case.json").write_text(json.dumps({"id": "fixture", "baseline_files": known,
                                               "oracle_sha256": digest(case / "oracle.py")}))
    job = tmp_path / "job.json"
    job.write_text(json.dumps({"case": str(case), "case_sha256": digest(case / "case.json"),
                               "prompt_sha256": digest(case / "prompt.md")}))
    approved = digest(job)
    assert load_job(job, approved)[-1] == "Task fixture"
    with pytest.raises(ValueError, match="approved receipt"):
        load_job(job, "bad")
    (baseline / "input.txt").write_text("altered")
    with pytest.raises(RuntimeError, match="frozen case baseline changed"):
        load_job(job, approved)


def test_saved_session_resumes_only_with_same_case_profile_and_private_state(tmp_path):
    from types import SimpleNamespace
    from taskflow.harness.opencode_derived.__main__ import SESSION_PROFILE, restore_session, state_digest

    prior = tmp_path / "prior"
    workspace = prior / "sandbox/work"
    session = prior / "sandbox/session"
    workspace.mkdir(parents=True)
    session.mkdir()
    (workspace / "wip.txt").write_text("keep")
    (session / "db").write_text("prior reasoning")
    prior_export = prior / "session.json"
    prior_export.write_text("{}")
    case = {"id": "fixture", "repo_base_sha": "original", "task_packet_sha256": "task"}
    job = {"backend": "gpu", "slot": 0, "thinking": True, "context": 131072, "request_cap": 32768,
           "sampling": {"temperature": 0.6}, "public_web": False}
    config = tmp_path / "config.json"
    config.write_text("{}")
    state = state_digest(workspace, session)
    p = prior / "receipt.json"
    p.write_text(json.dumps({"case": case["id"], "repo_base_sha": case["repo_base_sha"],
                             "task_packet_sha256": case["task_packet_sha256"], "session": "ses_fixture",
                             "session_profile": {k: job[k] for k in SESSION_PROFILE},
                             "opencode_config_sha256": digest(config), "workspace_session_sha256": state}))
    job["resume"] = {"prior_run": str(prior), "receipt_sha256": digest(p), "session_sha256": digest(prior_export),
                     "workspace_session_sha256": state}
    dest = tmp_path / "new"
    box = SimpleNamespace(root=dest, workspace=dest / "work", session=dest / "session", config_path=config)
    assert restore_session(job, case, box) == "ses_fixture"
    assert (box.workspace / "wip.txt").read_text() == "keep"
    assert (box.session / "db").read_text() == "prior reasoning"
    with pytest.raises(ValueError, match="OpenCode/model profile"):
        restore_session({**job, "thinking": False}, case, box)
    (workspace / "wip.txt").write_text("changed after approval")
    with pytest.raises(ValueError, match="saved workspace or session bytes changed"):
        restore_session(job, case, box)


def test_explicit_title_route_does_not_change_tool_bearing_replay_mode(model, tmp_path):
    limits = Limits(wall_s=5, output_cap=32768, cumulative_output=120000)
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=2, task="fixture", label="title",
               thinking=True, preserve_resume=True) as adapter:
        assert post(adapter.server_port, model="q35-a3b-title", maxOutputTokens=32768)[0] == 200
        assert post(adapter.server_port, maxOutputTokens=32768, tools=[{"function": {"name": "execute"}}])[0] == 200
    title, primary = model.requests
    assert title["model"] == primary["model"] == "q35-a3b"
    assert title["max_completion_tokens"] == 64 and title["chat_template_kwargs"] == {"enable_thinking": False}
    assert primary["max_completion_tokens"] == 32768 and primary["chat_template_kwargs"]["preserve_thinking"]
    assert [row["digest"]["role"] for row in adapter.rows] == ["title", None]


def test_open_code_interrupt_returns_a_valid_unwrapped_response(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from taskflow.harness.opencode_derived.sandbox import Assets, Sandbox

    box = Sandbox(tmp_path / "sandbox", 1, "0", assets=Assets(tmp_path / "opencode", tmp_path, tmp_path),
                  ctx=131072, cap=32768, transport_wall_s=1800)
    options = json.loads(box.config_path.read_text())["provider"]["taskflow-local"]["options"]
    assert options["headerTimeout"] is False and options["chunkTimeout"] == 1800000
    monkeypatch.setattr(box, "command", lambda *_args, **_kwargs: SimpleNamespace(
        stdout='{"interrupted":true}', stderr="", returncode=0))
    assert box.api("/api/session/ses_fixture/interrupt", {}) == {"interrupted": True}


def test_slot_wait_uses_same_gate_across_adapters_and_expires_without_upstream_request(model, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    def adapter(name, wall):
        limits = Limits(wall_s=wall, output_cap=8192, cumulative_output=120000)
        return proxy(model.server_port, tmp_path / name, limits=limits, backend="gpu", slot=2,
                     task="fixture", label=name, thinking=True)

    with ThreadPoolExecutor(max_workers=2) as pool, adapter("owner", 3) as owner:
        active = pool.submit(post, owner.server_port, stream=True)
        until = time.monotonic() + 1
        while not model.requests and time.monotonic() < until:
            time.sleep(0.005)
        assert len(model.requests) == 1
        with adapter("waiter", 0.2) as waiter:
            assert owner.gate is waiter.gate
            assert post(waiter.server_port)[0] == 429
            assert not waiter.rows and waiter.limits.pending == waiter.limits.charged == 0
            assert len(model.requests) == 1
        assert active.result()[0] == 200


def test_c22_requires_explicit_zero_shared_ram_cache():
    from taskflow.harness.opencode_derived.transport import require_disabled_shared_cache

    require_disabled_shared_cache((b"llama-server", b"--cache-ram", b"0"))
    for args in ((b"llama-server",), (b"llama-server", b"--cache-ram"),
                 (b"llama-server", b"--cache-ram", b"8192"),
                 (b"llama-server", b"--cache-ram", b"0", b"-cram", b"1")):
        with pytest.raises(ValueError, match="explicit --cache-ram 0"):
            require_disabled_shared_cache(args)
