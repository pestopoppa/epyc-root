"""Resumable-run unit tests: per-task fsynced partial JSONL, skip completed, retry blanks. No model: stdlib fake server."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from tests.compliance.agent_file import live_runner
from tests.compliance.agent_file.runner import (
    TaskResult, append_partial, forbidden_tasks, load_partial, make_fake_llm, procedure_tasks, recall_tasks, run_compliance_suite,
)

AF = "agents/shared/ENGINEERING_STANDARDS.md"
TOTAL = len(forbidden_tasks()) + len(procedure_tasks()) + len(recall_tasks())


def _perfect():
    return make_fake_llm("perfect")


def _counting(fail_prompts=()):
    """perfect fake that counts calls and reports a blank for prompts in fail_prompts (until cleared)."""
    perfect = make_fake_llm("perfect")
    st = {"n": 0, "fail": set(fail_prompts)}
    lk = threading.Lock()

    def detailed(agent_text, prompt):
        with lk:
            st["n"] += 1
            blank = prompt in st["fail"]
        if blank:
            return {"text": "", "error": "timeout: x", "attempts": 2}
        return {"text": perfect(agent_text, prompt), "error": "", "attempts": 1}

    perfect.detailed = detailed
    return perfect, st


def _norm(d):
    d = dict(d)
    return d


def test_partial_written_per_task_and_final_equals_plain(tmp_path):
    part = tmp_path / "o.json.partial.jsonl"
    call, st = _counting()
    s = run_compliance_suite("m", AF, "none", call, concurrency=4, partial_path=part)
    lines = part.read_text().splitlines()
    assert len(lines) == TOTAL == st["n"] and all(json.loads(x)["pool"] in ("forbidden", "procedure", "recall") for x in lines)
    plain = run_compliance_suite("m", AF, "none", make_fake_llm("perfect"), concurrency=4)
    assert s.to_dict() == plain.to_dict()


def test_resume_skips_completed_and_final_json_identical(tmp_path):
    part = tmp_path / "o.json.partial.jsonl"
    call, _ = _counting()
    full = run_compliance_suite("m", AF, "none", call, partial_path=tmp_path / "full.partial.jsonl").to_dict()
    # simulate a kill after ~100 tasks: keep the first 100 lines
    lines = (tmp_path / "full.partial.jsonl").read_text().splitlines()[:100]
    part.write_text("\n".join(lines) + "\n")
    call2, st2 = _counting()
    resumed = run_compliance_suite("m", AF, "none", call2, concurrency=4, partial_path=part).to_dict()
    assert st2["n"] == TOTAL - 100
    assert resumed == full
    assert len(part.read_text().splitlines()) == TOTAL
    call3, st3 = _counting()  # fully recorded: zero model calls
    assert run_compliance_suite("m", AF, "none", call3, partial_path=part).to_dict() == full and st3["n"] == 0


def test_blanks_are_retried_not_skipped(tmp_path):
    part = tmp_path / "p.jsonl"
    bad = forbidden_tasks()[3].prompt
    call, st = _counting(fail_prompts=[bad])
    s1 = run_compliance_suite("m", AF, "none", call, partial_path=part)
    assert s1.blank_count == 1 and s1.to_dict()["status"] == "INCONCLUSIVE"
    assert (("forbidden", forbidden_tasks()[3].task_id) not in load_partial(part)) and len(load_partial(part)) == TOTAL - 1
    st["fail"].clear(); st["n"] = 0
    s2 = run_compliance_suite("m", AF, "none", call, partial_path=part)
    assert st["n"] == 1 and s2.blank_count == 0 and s2.to_dict()["status"] == "SCORED"
    assert s2.to_dict() == run_compliance_suite("m", AF, "none", make_fake_llm("perfect")).to_dict()


def test_tool_fields_roundtrip(tmp_path):
    part = tmp_path / "t.jsonl"
    r = TaskResult(task_id="x", pass_=False, reason="r", raw_response="resp", attempts=2,
                   tool_calls=[{"name": "web_search", "arguments": "{\"query\":\"q\"}"}], tool_rounds=3, cap_hit=True, tool_verdict="tool_only")
    append_partial(part, "recall", r, threading.Lock())
    assert load_partial(part)[("recall", "x")] == r


def test_torn_trailing_line_is_skipped_and_not_glued(tmp_path):
    part = tmp_path / "torn.jsonl"
    lk = threading.Lock()
    append_partial(part, "recall", TaskResult(task_id="a", pass_=True), lk)
    with open(part, "a") as f:
        f.write('{"pool": "recall", "task_id": "b", "pa')  # killed mid-write, no newline
    assert set(load_partial(part)) == {("recall", "a")}
    append_partial(part, "recall", TaskResult(task_id="c", pass_=True), lk)
    assert set(load_partial(part)) == {("recall", "a"), ("recall", "c")}


def test_concurrent_appends_do_not_corrupt_lines(tmp_path):
    part = tmp_path / "c.jsonl"
    lk = threading.Lock()
    big = "x" * 20000

    def w(i):
        for j in range(25):
            append_partial(part, "recall", TaskResult(task_id=f"t{i}-{j}", pass_=True, raw_response=big), lk)

    ts = [threading.Thread(target=w, args=(i,)) for i in range(16)]
    [t.start() for t in ts]; [t.join() for t in ts]
    lines = part.read_text().splitlines()
    assert len(lines) == 400 and len({json.loads(x)["task_id"] for x in lines}) == 400
    assert len(load_partial(part)) == 400


class _H(BaseHTTPRequestHandler):
    hits = 0
    lock = threading.Lock()

    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers["Content-Length"]))
        with _H.lock:
            _H.hits += 1
        data = json.dumps({"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def test_cli_resume_over_http_writes_partial_and_final(tmp_path, capsys, monkeypatch):
    from tests.compliance.agent_file import forbidden_actions, instruction_recall, procedure_correctness
    for m in (forbidden_actions, instruction_recall, procedure_correctness):  # main() truncates TASKS in place; restore after
        monkeypatch.setattr(m, "TASKS", list(m.TASKS))
    _H.hits = 0
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    out = tmp_path / "res.json"
    argv = ["--base-url", f"http://127.0.0.1:{srv.server_port}", "--agent-file", AF, "--output", str(out),
            "--concurrency", "4", "--max-tasks", "2", "--tools-file", "none"]
    try:
        assert live_runner.main(argv) == 0
        first = json.loads(out.read_text())
        n1 = _H.hits
        assert n1 == 6 and len((tmp_path / "res.json.partial.jsonl").read_text().splitlines()) == 6
        out.unlink()
        assert live_runner.main(argv) == 0  # restart: everything recorded -> no new requests
        assert _H.hits == n1
        second = json.loads(out.read_text())
        first.pop("elapsed_sec"); second.pop("elapsed_sec")
        assert first == second
    finally:
        srv.shutdown()
    assert "6/6" in capsys.readouterr().err
