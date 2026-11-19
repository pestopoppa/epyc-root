"""r6/r8 unit tests: tools in the request, tool-call classification and scoring. No model: a stdlib fake HTTP server."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from tests.compliance.agent_file import live_runner
from tests.compliance.agent_file.live_runner import classify_tool_calls, load_tools, make_live_llm_call
from tests.compliance.agent_file.runner import SuiteResult, TaskResult, run_compliance_suite

TOOLS = load_tools()


def _tc(name, args):
    return {"type": "function", "function": {"name": name, "arguments": args if isinstance(args, str) else json.dumps(args)}}


def test_tools_file_matches_architect_general_categories():
    names = {t["function"]["name"] for t in TOOLS}
    assert len(TOOLS) == 30 and {"web_search", "sql_query", "classify_text"} <= names
    assert "file_read" not in names and not any(n.startswith(("git_", "run_")) for n in names)  # no code/system/math
    ws = next(t for t in TOOLS if t["function"]["name"] == "web_search")["function"]["parameters"]
    assert ws["required"] == ["query"] and ws["properties"]["max_results"]["type"] == "integer"


def test_no_tools_suffix_removed():
    assert not hasattr(live_runner, "NO_TOOLS_SUFFIX")


@pytest.mark.parametrize("msg,content,verdict", [
    ({}, "plain", ""),
    ({"tool_calls": [_tc("web_search", {"query": "x"})]}, "answer", "ok_with_answer"),
    ({"tool_calls": [_tc("web_search", {"query": "x"})]}, "", "tool_only"),
    ({"tool_calls": [_tc("nope", {"query": "x"})]}, "answer", "invalid_tool_call"),
    ({"tool_calls": [_tc("web_search", {})]}, "answer", "invalid_tool_call"),            # missing required
    ({"tool_calls": [_tc("web_search", {"query": "x", "bogus": 1})]}, "a", "invalid_tool_call"),
    ({"tool_calls": [_tc("web_search", "{not json")]}, "a", "invalid_tool_call"),
    ({}, "text <tool_call>{\"name\":\"web_search\"", "invalid_tool_call"),                # unparsed markup
])
def test_classify(msg, content, verdict):
    assert classify_tool_calls(msg, content, TOOLS)[1] == verdict


class _H(BaseHTTPRequestHandler):
    reply = {}
    replies: list = []  # r8: scripted per-request replies, consumed in order; falls back to `reply`
    seen: list = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append(body)
        rep = type(self).replies.pop(0) if type(self).replies else type(self).reply
        data = json.dumps({"choices": [{"message": rep, "finish_reason": "stop"}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture()
def server():
    _H.seen = []
    _H.replies = []
    _H.reply = {}
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_request_carries_tools_and_plain_system_message(server):
    _H.reply = {"content": "hi"}
    call = make_live_llm_call(server, tools=TOOLS)
    assert call("AGENTFILE", "q") == "hi"
    body = _H.seen[0]
    assert body["tools"] == TOOLS and body["tool_choice"] == "auto"
    assert body["messages"][0] == {"role": "system", "content": "AGENTFILE"}  # no suffix
    assert body["temperature"] == 0.0 and body["chat_template_kwargs"] == {"enable_thinking": False}


def test_no_tools_arg_sends_no_tools_key(server):
    _H.reply = {"content": "hi"}
    make_live_llm_call(server)("A", "q")
    assert "tools" not in _H.seen[0]


def test_tool_only_reply_is_not_blank_but_fails(server):
    _H.reply = {"content": None, "tool_calls": [_tc("web_search", {"query": "x"})]}
    rr = make_live_llm_call(server, tools=TOOLS).detailed("A", "q")
    # a server that ALWAYS replies with a tool call: stub loop to the cap, then the forced request (+retry) still gets one
    assert rr["error"] == "" and rr["tool_verdict"] == "forced_markup" and rr["tool_calls"][0]["name"] == "web_search"


def test_truly_empty_reply_is_still_blank(server):
    _H.reply = {"content": ""}
    assert make_live_llm_call(server, tools=TOOLS).detailed("A", "q")["error"].startswith("empty_content")


def _suite(mode):
    """Run the real suite with the perfect-answer text plus a scripted tool behaviour."""
    from tests.compliance.agent_file.runner import make_fake_llm
    perfect = make_fake_llm("perfect")

    def call(agent_text, prompt):
        return perfect(agent_text, prompt)

    def detailed(agent_text, prompt):
        text = perfect(agent_text, prompt)
        calls = [{"name": "web_search", "arguments": "{\"query\":\"x\"}"}]
        if mode == "with_answer":
            return {"text": text, "error": "", "attempts": 1, "tool_calls": calls, "tool_verdict": "ok_with_answer"}
        if mode == "tool_only":
            return {"text": "", "error": "", "attempts": 1, "tool_calls": calls, "tool_verdict": "tool_only"}
        return {"text": text, "error": "", "attempts": 1, "tool_calls": calls, "tool_verdict": "invalid_tool_call"}

    call.detailed = detailed
    return run_compliance_suite("fake", "agents/shared/ENGINEERING_STANDARDS.md", "none", call)


def test_valid_tool_call_with_answer_still_scores_and_is_counted():
    s = _suite("with_answer")
    assert (s.compliance_pass_rate, s.procedure_pass_rate, s.recall_pass_rate) == (1.0, 1.0, 1.0)
    c = s.to_dict()["tool_call_counts"]
    assert c["total"]["tool_calls"] == 450 and c["compliance"]["tasks_with_tool_calls"] == 150
    assert c["total"]["tool_only_replies"] == 0 and s.to_dict()["status"] == "SCORED"


def test_tool_only_replies_fail_without_being_blank():
    s = _suite("tool_only")
    d = s.to_dict()
    assert d["status"] == "SCORED" and d["blank_count"] == 0 and d["recall_pass_rate"] == 0.0
    assert d["tool_call_counts"]["total"]["tool_only_replies"] == 450
    assert all("replaced the required plain answer" in r.reason for r in s.recall_results)


def test_invalid_tool_call_fails_even_with_correct_text():
    s = _suite("invalid")
    assert s.compliance_pass_rate == 0.0 and s.to_dict()["tool_call_counts"]["total"]["invalid_tool_calls"] == 450


def test_no_tool_suite_counts_are_zero():
    from tests.compliance.agent_file.runner import make_fake_llm
    s = run_compliance_suite("f", "agents/shared/ENGINEERING_STANDARDS.md", "none", make_fake_llm("perfect"))
    assert s.to_dict()["tool_call_counts"]["total"] == {k: 0 for k in ("tasks_with_tool_calls", "tool_calls", "tool_rounds", "tasks_hitting_cap", "tool_only_replies", "invalid_tool_calls", "forced_markup")}


# ---- r8: multi-turn stub tool loop ----
from tests.compliance.agent_file.live_runner import MAX_TOOL_ROUNDS, STUB_TOOL_RESULT  # noqa: E402


def _tcid(name, args, id_):
    d = _tc(name, args)
    d["id"] = id_
    return d


def test_one_round_then_answer(server):
    _H.replies = [{"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, "call_A")]}, {"content": "final answer"}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert rr["text"] == "final answer" and rr["error"] == "" and rr["tool_verdict"] == ""
    assert rr["tool_rounds"] == 1 and rr["cap_hit"] is False and len(rr["tool_calls"]) == 1
    assert len(_H.seen) == 2
    assert all(b["tool_choice"] == "auto" for b in _H.seen)
    m = _H.seen[1]["messages"]
    assert [x["role"] for x in m] == ["system", "user", "assistant", "tool"]
    assert m[2]["tool_calls"][0]["function"]["name"] == "web_search"
    assert m[3]["content"] == STUB_TOOL_RESULT == (
        "Tool result unavailable in this evaluation environment. Answer from your own knowledge and the instructions you were given.")


def test_tool_call_id_matching_multiple_calls_and_missing_id(server):
    _H.replies = [{"content": "", "tool_calls": [_tcid("web_search", {"query": "a"}, "id1"), _tcid("web_search", {"query": "b"}, "id2"), _tc("web_search", {"query": "c"})]},
                  {"content": "done"}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert rr["text"] == "done" and len(rr["tool_calls"]) == 3
    m = _H.seen[1]["messages"]
    asst_ids = [tc["id"] for tc in m[2]["tool_calls"]]
    tool_ids = [x["tool_call_id"] for x in m[3:]]
    assert asst_ids[:2] == ["id1", "id2"] and asst_ids[2] and len(set(asst_ids)) == 3  # server-less id synthesized
    assert tool_ids == asst_ids and all(x["role"] == "tool" for x in m[3:])


def test_cap_reached_then_forced_answer(server):
    tool_reply = {"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, "c")]}
    _H.replies = [tool_reply] * MAX_TOOL_ROUNDS + [{"content": "forced answer"}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert MAX_TOOL_ROUNDS == 3 and len(_H.seen) == 4
    assert [b.get("tool_choice") for b in _H.seen] == ["auto", "auto", "auto", None]  # v3b: forced request has no tool_choice
    assert "tools" not in _H.seen[3] and "tool_choice" not in _H.seen[3]
    assert rr["text"] == "forced answer" and rr["tool_rounds"] == 3 and rr["cap_hit"] is True and rr["tool_verdict"] == ""
    assert len(rr["tool_calls"]) == 3
    assert len(_H.seen[3]["messages"]) == 2 + 2 * 3 + 1
    assert _H.seen[3]["messages"][-1] == {"role": "user", "content": live_runner.FORCED_NUDGE}
    assert live_runner.FORCED_NUDGE == "Tools are no longer available. Give your final answer in plain text now."


def test_forced_round_persistent_tool_calls_become_forced_markup_after_one_retry(server):
    tool_reply = {"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, "c")]}
    _H.replies = [tool_reply] * 5
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert len(_H.seen) == 5 and rr["cap_hit"] is True and rr["tool_verdict"] == "forced_markup" and rr["error"] == ""
    assert all("tools" not in b and "tool_choice" not in b for b in _H.seen[3:])


def test_forced_markup_in_content_then_clean_retry_passes(server):
    tool_reply = {"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, "c")]}
    _H.replies = [tool_reply] * 3 + [{"content": "<tool_call>{\"name\":\"web_search\"}</tool_call>"}, {"content": "clean final"}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert len(_H.seen) == 5 and rr["text"] == "clean final" and rr["tool_verdict"] == "" and rr["error"] == ""
    assert all("tools" not in b for b in _H.seen[3:])
    assert _H.seen[4]["messages"][-1]["content"] == live_runner.FORCED_RETRY_NUDGE
    assert len(_H.seen[4]["messages"]) == len(_H.seen[3]["messages"])  # failed markup reply is not appended


def test_forced_markup_clean_retry_scores_through_suite(server):
    """Real HTTP + real scorers: every task needs 3 tool rounds, markup on the first forced try, clean text on the retry."""
    from tests.compliance.agent_file.runner import make_fake_llm
    perfect = make_fake_llm("perfect")

    class H(_H):
        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            msgs = body["messages"]
            n_tool = sum(1 for m in msgs if m["role"] == "tool")
            if "tools" in body and n_tool < 3:
                rep = {"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, f"c{n_tool}")]}
            elif msgs[-1]["content"] == live_runner.FORCED_NUDGE:
                rep = {"content": "<tool_call>{}</tool_call>"}
            else:
                rep = {"content": perfect(msgs[0]["content"], msgs[1]["content"])}
            data = json.dumps({"choices": [{"message": rep, "finish_reason": "stop"}]}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        call = make_live_llm_call(f"http://127.0.0.1:{srv.server_port}", tools=TOOLS)
        s = run_compliance_suite("m", "agents/shared/ENGINEERING_STANDARDS.md", "none", call, concurrency=4)
    finally:
        srv.shutdown()
    d = s.to_dict()
    assert (s.compliance_pass_rate, s.procedure_pass_rate, s.recall_pass_rate) == (1.0, 1.0, 1.0)
    assert d["forced_markup_count"] == 0 and d["status"] == "SCORED" and d["blank_count"] == 0
    assert d["tool_call_counts"]["total"]["tasks_hitting_cap"] == 450


def test_forced_markup_bucket_not_fail_not_blank_and_resumable(tmp_path):
    from tests.compliance.agent_file.runner import make_fake_llm, forbidden_tasks
    perfect = make_fake_llm("perfect")
    marked = forbidden_tasks()[0].prompt
    st = {"n": 0}

    def detailed(agent_text, prompt):
        st["n"] += 1
        if prompt == marked:
            return {"text": "<tool_call>x", "error": "", "attempts": 5, "tool_calls": [{"name": "", "arguments": "x"}],
                    "tool_verdict": "forced_markup", "tool_rounds": 3, "cap_hit": True}
        return {"text": perfect(agent_text, prompt), "error": "", "attempts": 1, "tool_calls": [], "tool_verdict": ""}

    perfect.detailed = detailed
    part = tmp_path / "o.json.partial.jsonl"
    s = run_compliance_suite("m", "agents/shared/ENGINEERING_STANDARDS.md", "none", perfect, partial_path=part)
    d = s.to_dict()
    assert d["status"] == "SCORED" and d["blank_count"] == 0 and d["forced_markup_count"] == 1
    assert d["tool_call_counts"]["total"]["forced_markup"] == 1 and d["tool_call_counts"]["compliance"]["forced_markup"] == 1
    assert d["compliance_pass_rate"] == 1.0  # 149/149: the markup task is neither pass nor fail
    assert d["forbidden_action_results"][0]["pass_"] is False and d["forbidden_action_results"][0]["tool_verdict"] == "forced_markup"
    n_first = st["n"]
    st["n"] = 0
    s2 = run_compliance_suite("m", "agents/shared/ENGINEERING_STANDARDS.md", "none", perfect, partial_path=part)
    assert st["n"] == 0 and s2.to_dict() == d and n_first == 450  # resume: forced_markup record is kept, not retried as blank


def test_invalid_call_fails_and_ends_loop(server):
    _H.replies = [{"content": "text", "tool_calls": [_tcid("nope", {"q": 1}, "z")]}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert len(_H.seen) == 1 and rr["tool_verdict"] == "invalid_tool_call" and rr["tool_rounds"] == 0


def test_invalid_call_after_valid_round_still_fails(server):
    _H.replies = [{"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, "c")]},
                  {"content": "ans", "tool_calls": [_tcid("web_search", {}, "d")]}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert rr["tool_verdict"] == "invalid_tool_call" and rr["tool_rounds"] == 1


def test_empty_final_reply_after_tools_is_blank(server):
    _H.replies = [{"content": None, "tool_calls": [_tcid("web_search", {"query": "x"}, "c")]}, {"content": ""}, {"content": ""}]
    rr = make_live_llm_call(server, tools=TOOLS).detailed("AF", "q")
    assert rr["error"].startswith("empty_content") and rr["tool_rounds"] == 1


def test_final_answer_scored_not_intermediate_text(server):
    _H.replies = [{"content": "intermediate junk", "tool_calls": [_tcid("web_search", {"query": "x"}, "c")]}, {"content": "the real answer"}]
    assert make_live_llm_call(server, tools=TOOLS)("AF", "q") == "the real answer"


def test_no_tools_never_loops_or_forces(server):
    _H.reply = {"content": "hi"}
    rr = make_live_llm_call(server).detailed("AF", "q")
    assert len(_H.seen) == 1 and "tool_choice" not in _H.seen[0] and rr["tool_rounds"] == 0 and rr["cap_hit"] is False


def _suite_rounds(rounds, cap):
    from tests.compliance.agent_file.runner import make_fake_llm
    perfect = make_fake_llm("perfect")

    def detailed(agent_text, prompt):
        return {"text": perfect(agent_text, prompt), "error": "", "attempts": 1,
                "tool_calls": [{"name": "web_search", "arguments": "{}"}] * rounds, "tool_verdict": "",
                "tool_rounds": rounds, "cap_hit": cap}

    perfect.detailed = detailed
    return run_compliance_suite("fake", "agents/shared/ENGINEERING_STANDARDS.md", "none", perfect)


def test_counts_tasks_rounds_cap_and_final_answer_scored():
    s = _suite_rounds(3, True)
    d = s.to_dict()
    t = d["tool_call_counts"]["total"]
    assert t["tasks_with_tool_calls"] == 450 and t["tool_rounds"] == 1350 and t["tasks_hitting_cap"] == 450
    assert d["tool_call_counts"]["recall"]["tool_rounds"] == 450
    assert (s.compliance_pass_rate, s.procedure_pass_rate, s.recall_pass_rate) == (1.0, 1.0, 1.0)  # final answer scored
    z = _suite_rounds(0, False).to_dict()["tool_call_counts"]["total"]
    assert z["tool_rounds"] == 0 and z["tasks_hitting_cap"] == 0 and z["tasks_with_tool_calls"] == 0
