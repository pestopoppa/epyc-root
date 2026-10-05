"""scripts/autokernel_actor_cli.py -- the AutoKernel `orchestrator` actor CLI (INF-78 OAB-2).

No inference: every HTTP call goes to an in-process mock `/chat` server on an
ephemeral 127.0.0.1 port. The module is loaded by FILE PATH, because `scripts` is a
namespace package that also resolves through the venv's editable `.pth` (the shared
clone), and the test must exercise THIS worktree's copy.
"""
from __future__ import annotations

import importlib.util
import io
import json
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

CLI_PATH = Path(__file__).resolve().parents[2] / "scripts" / "autokernel_actor_cli.py"
_spec = importlib.util.spec_from_file_location("autokernel_actor_cli_under_test", CLI_PATH)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

OK_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
             "required": ["ok"], "additionalProperties": False}
HYP_OR_ABSTAIN = {"anyOf": [
    {"type": "object",
     "properties": {k: {"type": "string"} for k in ("mechanism_id", "statement", "falsifier",
                                                   "target_surface", "target_symbol")},
     "required": ["mechanism_id", "statement", "falsifier", "target_surface", "target_symbol"],
     "additionalProperties": False},
    {"type": "object", "properties": {"abstain": {"type": "string"}},
     "required": ["abstain"], "additionalProperties": False}]}


def chat_response(answer: str, **extra) -> dict:
    body = {"answer": answer, "turns": 7, "tokens_used": 900, "elapsed_seconds": 12.5,
            "mock_mode": False, "real_mode": True, "routed_to": "architect_general",
            "role_history": ["frontdoor", "architect_general"], "routing_strategy": "rules",
            "mode": "repl", "tokens_generated": 4321, "tools_used": 5,
            "tools_called": ["read_file", "grep", "grep", "list_dir", "read_file"],
            "tool_output_tokens": 1200, "compaction_triggered": False,
            "error_code": None, "error_detail": None}
    body.update(extra)
    return body


class MockChat:
    """A `/chat` endpoint returning one scripted (status, body, delay) per request."""

    def __init__(self, status: int = 200, body: dict | str | None = None, delay_s: float = 0.0):
        self.status, self.body, self.delay_s = status, body, delay_s
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 -- http.server API
                length = int(self.headers.get("Content-Length") or 0)
                outer.requests.append({"path": self.path,
                                       "body": json.loads(self.rfile.read(length))})
                if outer.delay_s:
                    time.sleep(outer.delay_s)
                payload = outer.body if isinstance(outer.body, str) else json.dumps(outer.body)
                data = payload.encode("utf-8")
                try:
                    self.send_response(outer.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):  # silence
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def run_main(args: list[str], prompt: str = "PROMPT") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(args, stdin=io.StringIO(prompt), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def _schema_file(tmp_path: Path, schema: dict) -> Path:
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(schema))
    return path


# --------------------------------------------------------------------------- request shape


def test_request_fields_follow_the_contract_and_live_in_one_map():
    body = cli.build_request("P", root="/lane", read_only=True, schema=OK_SCHEMA, role="auto",
                             max_turns=50, timeout_s=600, request_id="r1")
    assert body[cli.FIELDS["task_root"]] == "/lane"
    assert body[cli.FIELDS["edit_mode"]] == "none"
    assert body[cli.FIELDS["quiescent_after"]] is True
    assert body[cli.FIELDS["output_schema"]] == OK_SCHEMA
    assert body["mock_mode"] is False and body["real_mode"] is True, "ChatRequest defaults mock_mode=True"
    assert body["force_mode"] == "repl"
    assert body["max_turns"] == 50 and body["timeout_s"] == 600
    assert "force_role" not in body, "auto routing sends no force_role"
    pinned = cli.build_request("P", root="/lane", read_only=False, schema=None,
                               role="architect_general", max_turns=50, timeout_s=600,
                               request_id="r2")
    assert pinned["force_role"] == "architect_general"
    assert pinned["edit_mode"] == "direct"
    assert "output_schema" not in pinned
    unforced = cli.build_request("P", root="/lane", read_only=True, schema=None, role="auto",
                                 max_turns=50, timeout_s=600, request_id="r3", mode="auto")
    assert "force_mode" not in unforced, "--mode auto lets the orchestrator choose"
    # Every key sent is named in FIELDS -- the one place to rename them.
    assert set(body) | set(pinned) <= set(cli.FIELDS.values())


# --------------------------------------------------------------------------- success


def test_success_prints_one_object_exits_zero_and_writes_provenance(tmp_path):
    sidecar = tmp_path / "prov.json"
    with MockChat(body=chat_response('{"ok": true}', task_root=str(tmp_path))) as mock:
        code, out, err = run_main(["--root", str(tmp_path), "--read-only",
                                   "--schema", str(_schema_file(tmp_path, OK_SCHEMA)),
                                   "--url", mock.url, "--role", "architect_general",
                                   "--max-turns", "40", "--timeout-s", "300",
                                   "--provenance-out", str(sidecar)], prompt="say ok")
    assert code == 0, err
    assert out.count("\n") == 1 and json.loads(out) == {"ok": True}
    sent = mock.requests[0]
    assert sent["path"] == "/chat"
    assert sent["body"]["prompt"] == "say ok"
    assert sent["body"]["force_role"] == "architect_general"
    assert sent["body"]["max_turns"] == 40
    prov = json.loads(sidecar.read_text())
    assert prov["schema"] == cli.PROVENANCE_SCHEMA
    assert prov["http_status"] == 200
    assert prov["response"]["routed_to"] == "architect_general"
    assert prov["response"]["role_history"] == ["frontdoor", "architect_general"]
    assert prov["response"]["routing_strategy"] == "rules"
    assert prov["response"]["turns"] == 7
    assert "answer" not in prov["response"], "the sidecar never carries the answer"
    assert "say ok" not in sidecar.read_text(), "nor the prompt"
    assert prov["request"]["prompt_chars"] == 6
    assert prov["request"]["edit_mode"] == "none"
    assert prov["task_root_acknowledged"] is True
    assert prov["reply"] == {"found": True, "schema_valid": True, "exit_code": 0}


def test_abstention_validates_against_the_anyof_wire_schema(tmp_path):
    with MockChat(body=chat_response('{"abstain": "nothing reachable"}')) as mock:
        code, out, err = run_main(["--root", "/lane", "--read-only",
                                   "--schema", str(_schema_file(tmp_path, HYP_OR_ABSTAIN)),
                                   "--url", mock.url])
    assert code == 0, err
    assert json.loads(out) == {"abstain": "nothing reachable"}
    assert "did not echo task_root" in err, "a pre-OAB-1 server is flagged, not assumed"


def test_the_last_object_is_fished_from_prose(tmp_path):
    answer = 'draft {"ok": false} ... final: {"ok": true}'
    with MockChat(body=chat_response(answer)) as mock:
        code, out, _ = run_main(["--root", "/lane", "--schema",
                                 str(_schema_file(tmp_path, OK_SCHEMA)), "--url", mock.url])
    assert code == 0 and json.loads(out) == {"ok": True}


# --------------------------------------------------------------------------- failures


def test_orchestrator_down_is_exit_1_with_empty_stdout_and_a_sidecar(tmp_path):
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing listens here now
    sidecar = tmp_path / "prov.json"
    code, out, err = run_main(["--root", "/lane", "--url", f"http://127.0.0.1:{port}",
                               "--provenance-out", str(sidecar)])
    assert code == 1 and out == ""
    assert "unreachable" in err
    prov = json.loads(sidecar.read_text())
    assert "unreachable" in prov["error"]
    assert prov["response"] is None and prov["reply"]["exit_code"] == 1


def test_non_json_answer_is_exit_1_with_nothing_on_stdout(tmp_path):
    with MockChat(body=chat_response("I looked around and have no proposal.")) as mock:
        code, out, err = run_main(["--root", "/lane", "--schema",
                                   str(_schema_file(tmp_path, OK_SCHEMA)), "--url", mock.url])
    assert code == 1 and out == ""
    assert "no JSON object" in err


def test_schema_invalid_object_is_printed_but_exit_1(tmp_path):
    with MockChat(body=chat_response('{"ok": "yes"}')) as mock:
        code, out, err = run_main(["--root", "/lane", "--schema",
                                   str(_schema_file(tmp_path, OK_SCHEMA)), "--url", mock.url])
    assert code == 1
    assert json.loads(out) == {"ok": "yes"}, "printed for diagnosis; the loop will not salvage it"
    assert "does not validate" in err


def test_server_flagged_422_keeps_a_complete_reply_on_stdout_for_salvage(tmp_path):
    """The /chat route returns the whole ChatResponse with status=error_code (TD-21.1
    terminal flag). A complete object in the answer is printed with exit 1."""
    body = chat_response('{"ok": true}', error_code=422,
                         error_detail="FINAL() value failed output_schema validation after retry")
    sidecar = tmp_path / "prov.json"
    with MockChat(status=422, body=body) as mock:
        code, out, err = run_main(["--root", "/lane", "--schema",
                                   str(_schema_file(tmp_path, OK_SCHEMA)), "--url", mock.url,
                                   "--provenance-out", str(sidecar)])
    assert code == 1
    assert json.loads(out) == {"ok": True}
    assert "error_code=422" in err
    prov = json.loads(sidecar.read_text())
    assert prov["http_status"] == 422 and prov["response"]["error_code"] == 422


def test_request_validation_422_without_a_chat_response(tmp_path):
    detail = {"detail": [{"loc": ["body", "max_turns"], "msg": "less than or equal to 50"}]}
    with MockChat(status=422, body=detail) as mock:
        code, out, err = run_main(["--root", "/lane", "--url", mock.url, "--max-turns", "60"])
    assert code == 1 and out == ""
    assert "HTTP 422" in err and "max_turns" in err


def test_empty_prompt_is_refused_before_any_request(tmp_path):
    with MockChat(body=chat_response("{}")) as mock:
        code, out, err = run_main(["--root", "/lane", "--url", mock.url], prompt="  \n")
    assert code == 1 and out == "" and not mock.requests
    assert "empty prompt" in err


def test_client_timeout_is_exit_1(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CLIENT_SLACK_S", 0)
    with MockChat(body=chat_response('{"ok": true}'), delay_s=2.0) as mock:
        code, out, err = run_main(["--root", "/lane", "--url", mock.url, "--timeout-s", "1"])
    assert code == 1 and out == ""
    assert "timed out" in err


# --------------------------------------------------------------------------- the process contract


def test_real_subprocess_stdin_in_one_object_out(tmp_path):
    """The exact shape the loop runs: `python -I <path>`, prompt on stdin, cwd a tree
    with its own decoy `scripts/` (a llama.cpp lane has one)."""
    decoy = tmp_path / "lane"
    (decoy / "scripts").mkdir(parents=True)
    (decoy / "scripts" / "autokernel_actor_cli.py").write_text("raise SystemExit(99)\n")
    with MockChat(body=chat_response('{"ok": true}')) as mock:
        done = subprocess.run(
            [sys.executable, "-I", str(CLI_PATH), "--root", str(decoy), "--read-only",
             "--schema", str(_schema_file(tmp_path, OK_SCHEMA)), "--url", mock.url],
            input='reply with {"ok":true}', capture_output=True, text=True, cwd=str(decoy),
            timeout=60)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"ok": True}
    assert mock.requests[0]["body"]["prompt"] == 'reply with {"ok":true}'


# --------------------------------------------------------------------------- helpers


@pytest.mark.parametrize("text,expected", [
    ('{"a": 1}', {"a": 1}),
    ('x {"a": {"b": "}"}} y {"c": 2} z', {"c": 2}),
    ("no json here", None),
    ('{"a": "unterminated', None),
])
def test_extract_last_object(text, expected):
    assert cli.extract_last_object(text) == expected


def test_mini_validator_covers_the_loop_schemas():
    assert cli._mini_valid({"abstain": "x"}, HYP_OR_ABSTAIN)
    assert not cli._mini_valid({"abstain": "x", "extra": 1}, HYP_OR_ABSTAIN)
    assert not cli._mini_valid({"ok": 1}, OK_SCHEMA)
    assert not cli._mini_valid({"ok": True, "more": 1}, OK_SCHEMA)
    assert cli._mini_valid({"paths": ["a.cpp"]}, {"type": "object", "properties": {
        "paths": {"type": "array", "items": {"type": "string"}}}, "required": ["paths"]})
    assert not cli._mini_valid(True, {"type": "integer"})


# --------------------------------------------------------------------------- OAB-8 scouts


def test_no_scouts_field_unless_targets_are_given(tmp_path):
    body = cli.build_request("P", root="/lane", read_only=True, schema=None, role="auto",
                             max_turns=50, timeout_s=600, request_id="r1")
    assert "scouts" not in body, "default off: the pre-OAB-8 request is unchanged"
    assert cli.build_scouts([]) is None
    with MockChat(body=chat_response('{"ok": true}')) as mock:
        run_main(["--root", str(tmp_path), "--read-only", "--url", mock.url])
    assert "scouts" not in mock.requests[0]["body"]


def test_scout_targets_file_becomes_the_scouts_field_and_is_echoed(tmp_path):
    targets = tmp_path / "targets.json"
    targets.write_text(json.dumps({"targets": [
        {"symbol": "ggml_vec_dot_q4_K_q8_K", "dso": "libggml-cpu.so", "share": 0.31,
         "extra": "dropped"},
        {"file": "ggml/src/ggml-cpu/ops.cpp"},
        {"share": 0.2},                                   # neither symbol nor file: dropped
    ] + [{"symbol": f"s{i}"} for i in range(20)]}))
    sidecar = tmp_path / "prov.json"
    scouts_echo = {"schema": "epyc.orchestrator.scouts.v1", "launched": 2, "completed": 2,
                   "max_concurrency": 2, "scouts": [{"status": "ok", "wall_s": 12.0}]}
    with MockChat(body=chat_response('{"ok": true}', scouts=scouts_echo)) as mock:
        code, _, err = run_main(["--root", str(tmp_path), "--read-only", "--url", mock.url,
                                 "--scout-targets", str(targets), "--scouts-max", "3",
                                 "--scout-role", "architect_general", "--scout-max-turns", "6",
                                 "--provenance-out", str(sidecar)])
    assert code == 0, err
    sent = mock.requests[0]["body"]["scouts"]
    assert sent["enabled"] is True and sent["max"] == 3 and sent["max_turns"] == 6
    assert sent["role"] == "architect_general" and "budget_s" not in sent
    assert sent["targets"][0] == {"symbol": "ggml_vec_dot_q4_K_q8_K", "dso": "libggml-cpu.so",
                                  "share": 0.31}
    assert sent["targets"][1] == {"file": "ggml/src/ggml-cpu/ops.cpp"}
    assert len(sent["targets"]) == cli.MAX_SCOUT_TARGETS
    prov = json.loads(sidecar.read_text())
    assert prov["request"]["scouts"]["targets"] == cli.MAX_SCOUT_TARGETS
    assert prov["request"]["scouts"]["max"] == 3
    assert prov["response"]["scouts"] == scouts_echo, "scout provenance reaches the sidecar"


def test_malformed_scout_targets_fail_before_any_request(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"targets": "nope"}')
    with MockChat(body=chat_response('{"ok": true}')) as mock:
        code, out, err = run_main(["--root", str(tmp_path), "--url", mock.url,
                                   "--scout-targets", str(bad)])
    assert code == 1 and out == "" and "scout-targets" in err and not mock.requests
