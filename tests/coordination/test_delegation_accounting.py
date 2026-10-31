"""FM-7 delegation accounting: paired-mutation tests.

Every positive assertion has a mutated twin that must flip it, so a test that
passes vacuously (empty input, wrong key) is caught by its pair."""

import json
from pathlib import Path

from scripts.coordination import delegation_accounting as da
from scripts.coordination import fanout_timing as ft

PRE = "2026-10-10T00:00:{:02d}Z"
POST = "2026-10-20T00:00:{:02d}Z"


def _asst(mid, ts, *, usage=(10, 100, 1000, 5), tool_use=None, text=None, model="claude-opus-5-5",
          effort="high", sidechain=False):
    content = []
    if text:
        content.append({"type": "text", "text": text})
    if tool_use:
        content.append({"type": "tool_use", **tool_use})
    rec = {"parentUuid": None, "isSidechain": sidechain, "type": "assistant", "timestamp": ts,
           "effort": effort, "message": {"id": mid, "model": model, "content": content,
                                         "usage": {"input_tokens": usage[0],
                                                   "cache_creation_input_tokens": usage[1],
                                                   "cache_read_input_tokens": usage[2],
                                                   "output_tokens": usage[3]}}}
    return rec


def _read_use(tid, path="/x/big.py", offset=None, limit=None):
    inp = {"file_path": path}
    if offset is not None:
        inp["offset"] = offset
    if limit is not None:
        inp["limit"] = limit
    return {"id": tid, "name": "Read", "input": inp}


def _read_result(tid, ts, *, total=400, num=None, start=1, chars=4000):
    num = total if num is None else num
    return {"parentUuid": None, "isSidechain": False, "type": "user", "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid}]},
            "toolUseResult": {"type": "text", "file": {"filePath": "/x/big.py", "content": "a" * chars,
                                                       "numLines": num, "startLine": start,
                                                       "totalLines": total}}}


def _main_session(*, limit=None, total=400, after=3, compact=False, fmt=PRE):
    recs = [_asst("m0", fmt.format(0), tool_use=_read_use("t1", limit=limit)),
            _read_result("t1", fmt.format(1), total=total)]
    for i in range(after):
        if compact and i == 1:
            recs.append({"type": "system", "subtype": "compact_boundary", "timestamp": fmt.format(2)})
        recs.append(_asst(f"m{i + 1}", fmt.format(3 + i)))
    return recs


def _a(recs, window="pre"):
    row, _, _ = da.account_claude_session("s", recs, [])
    return row["a_windows"].get(window)


# ---------------------------------------------------------------- the A numerator


def test_full_large_read_carries_into_every_later_request():
    w = _a(_main_session(after=3))
    assert w["num"] == 3 * 4000 / 4          # chars/4 x 3 requests remaining
    assert w["den"] == 4 * 1110               # 4 requests x (input + cc + cr)
    assert w["qualifying_reads"] == 1


def test_bounded_read_with_limit_does_not_count():
    assert _a(_main_session(limit=200))["num"] == 0


def test_more_requests_remaining_scales_numerator():
    assert _a(_main_session(after=5))["num"] == 5 * 1000


def test_file_of_exactly_350_lines_does_not_qualify():
    assert _a(_main_session(total=350))["num"] == 0


def test_file_of_351_lines_qualifies():
    assert _a(_main_session(total=351))["num"] == 3 * 1000


def test_result_shape_fallback_when_tool_input_missing():
    recs = _main_session()
    recs[0]["message"]["content"] = []                 # tool_use input absent
    assert _a(recs)["num"] == 3 * 1000                 # startLine 1, numLines == total


def test_result_shape_fallback_rejects_partial_window():
    recs = _main_session()
    recs[0]["message"]["content"] = []
    recs[1]["toolUseResult"]["file"]["numLines"] = 100
    assert _a(recs)["num"] == 0


def test_compaction_bounds_only_the_sensitivity():
    w = _a(_main_session(after=3, compact=True))
    assert w["num"] == 3000 and w["num_compact"] == 1000


def test_without_compaction_sensitivity_equals_rule_value():
    w = _a(_main_session(after=3, compact=False))
    assert w["num_compact"] == w["num"]


def test_window_follows_request_timestamp():
    assert _a(_main_session(fmt=POST), "post")["num"] == 3000
    assert _a(_main_session(fmt=POST), "pre") is None


def test_sidechain_records_never_count_as_main_thread():
    recs = _main_session()
    for r in recs:
        r["isSidechain"] = True
    assert _a(recs) is None


# ---------------------------------------------------------------- request units


def test_duplicate_message_id_is_one_request():
    recs = [_asst("m0", PRE.format(0), text="a"), _asst("m0", PRE.format(1), text="b")]
    row, _, _ = da.account_claude_session("s", recs, [])
    assert row["requests"] == 1 and row["tokens"]["input"] == 10


def test_distinct_message_ids_are_two_requests():
    recs = [_asst("m0", PRE.format(0), text="a"), _asst("m1", PRE.format(1), text="b")]
    row, _, _ = da.account_claude_session("s", recs, [])
    assert row["requests"] == 2 and row["tokens"]["input"] == 20


# ---------------------------------------------------------------- subagents


def _sub(first_usage=(3, 20000, 5000, 7), model="claude-haiku-5-5", report="done: see x"):
    return [_asst("a0", PRE.format(5), usage=first_usage, model=model, effort="low"),
            _asst("a1", PRE.format(6), usage=(1, 10, 100, 42), model=model, effort="low", text=report)]


def _session_with_sub(**kw):
    meta = {"agentType": "general-purpose", "description": "scan", "toolUseId": "tu1", "model": "haiku"}
    _, subs, _ = da.account_claude_session("s", _main_session(), [("aX", meta, _sub(**kw))])
    return subs[0]


def test_fixed_overhead_is_first_request_input():
    sub = _session_with_sub()
    assert sub["first_request"]["total_input"] == 25003
    assert sub["final_report_output_tokens"] == 42 and sub["final_report_chars"] == len("done: see x")
    assert sub["tier"] == 1 and sub["effort"] == "low"


def test_fixed_overhead_moves_with_first_request():
    assert _session_with_sub(first_usage=(3, 30000, 5000, 7))["first_request"]["total_input"] == 35003


def test_no_report_means_zero_report_length():
    sub = _session_with_sub(report=None)
    assert sub["final_report_chars"] == 0 and sub["final_report_output_tokens"] is None


# ---------------------------------------------------------------- decision rule


def test_decision_rule_fires_only_when_both_windows_clear_ten_percent():
    assert da.decide(0.10, 0.12) == "M1 fires"
    assert da.decide(0.10, 0.0999) == "re-measure"


def test_decision_rule_declines_only_when_both_windows_under_three_percent():
    assert da.decide(0.029, 0.01) == "M1 declined"
    assert da.decide(0.03, 0.01) == "re-measure"


def test_decision_rule_missing_window_is_never_a_verdict():
    assert da.decide(None, 0.5) == "re-measure"


# ---------------------------------------------------------------- re-dispatch (M2)


def _grp(second_tier, second_key="scan files", effort2="low"):
    return [[{"epoch": 1, "key": "scan files", "prompt": "", "tier": 1, "effort": "low"},
             {"epoch": 2, "key": second_key, "prompt": "", "tier": second_tier, "effort": effort2}]]


def test_cheap_dispatch_redone_at_higher_tier_counts():
    ev = da.redispatch_events(_grp(3))
    assert ev[0]["higher_tier_redispatch"] and ev[0]["match_basis"] == "description"


def test_different_task_at_higher_tier_does_not_count():
    assert not da.redispatch_events(_grp(3, second_key="write report"))[0]["higher_tier_redispatch"]


def test_same_tier_higher_effort_is_effort_only():
    ev = da.redispatch_events(_grp(1, effort2="high"))[0]
    assert ev["effort_only_redispatch"] and not ev["higher_tier_redispatch"]


def test_same_tier_same_effort_is_neither():
    ev = da.redispatch_events(_grp(1))[0]
    assert not ev["effort_only_redispatch"] and not ev["higher_tier_redispatch"]


def test_tier_tokens_are_stripped_from_task_keys():
    assert da._norm_task("scan_files_luna", "codex") == da._norm_task("scan_files_sol", "codex")
    assert da._norm_task("scan_files_luna", "codex") != da._norm_task("write_luna", "codex")


# ---------------------------------------------------------------- Codex


def _cx(ts, rtype, payload):
    return {"timestamp": ts, "type": rtype, "payload": payload}


def _codex_main(*, records=True, out_lines=400):
    recs = [_cx(PRE.format(0), "session_meta", {"id": "R", "session_id": "R", "originator": "codex-tui",
                                                "source": "vscode"}),
            _cx(PRE.format(0), "turn_context", {"model": "gpt-6.1-sol", "effort": "high"})]
    usage = {"input_tokens": 1000, "cached_input_tokens": 900, "output_tokens": 10, "total_tokens": 1010}
    for i in range(3):
        if records:
            recs.append(_cx(PRE.format(1 + 2 * i), "token_usage_record", {"response_id": f"r{i}", "usage": usage}))
        recs.append(_cx(PRE.format(1 + 2 * i), "event_msg", {"type": "token_count", "info": {
            "last_token_usage": usage, "total_token_usage": {"input_tokens": 1000 * (i + 1)}}}))
        if i == 0:
            recs.append(_cx(PRE.format(2), "response_item", {"type": "function_call_output",
                                                             "output": "x\n" * (out_lines - 1) + "x"}))
    recs.append(_cx(PRE.format(9), "response_item", {"type": "function_call", "name": "spawn_agent",
                                                     "arguments": json.dumps({"task_name": "scan_luna",
                                                                              "model": "gpt-6-luna"})}))
    return recs


def test_codex_usage_records_and_token_count_agree():
    a, _ = da.account_codex_rollout("f", _codex_main(records=True))
    b, _ = da.account_codex_rollout("f", _codex_main(records=False))
    assert a["requests"] == b["requests"] == 3
    assert a["tokens"]["cache_read"] == b["tokens"]["cache_read"] == 2700
    assert a["request_source"] == "token_usage_record" and b["request_source"] == "token_count"


def test_codex_large_tool_output_carries_in_proxy():
    row, disp = da.account_codex_rollout("f", _codex_main(out_lines=400))
    assert row["kind"] == "main" and row["tier"] == 3
    assert row["a_proxy_windows"]["pre"]["num"] == 2 * (400 * 2 - 1) / 4
    assert disp[0]["task_name"] == "scan_luna"


def test_codex_small_tool_output_does_not_carry():
    row, _ = da.account_codex_rollout("f", _codex_main(out_lines=350))
    assert row["a_proxy_windows"]["pre"]["num"] == 0


def test_codex_subagent_is_classified_and_skips_proxy():
    recs = _codex_main()
    recs[0]["payload"]["source"] = {"subagent": {"thread_spawn": {"parent_thread_id": "P", "depth": 1,
                                                                  "agent_path": "/root/scan_luna"}}}
    row, _ = da.account_codex_rollout("f", recs)
    assert row["kind"] == "subagent" and row["parent"] == "P" and "a_proxy_windows" not in row


# ---------------------------------------------------------------- frozen manifest


def _corpus(root):
    root.mkdir()
    lines = [json.dumps(r) for r in _main_session()]
    (root / "s1.jsonl").write_text("\n".join(lines) + "\n")
    return root


def test_manifest_prefix_survives_appends(tmp_path):
    root = _corpus(tmp_path / "c")
    man = da.build_manifest(root, None)
    rows1, rep1 = da.account(man)
    with (root / "s1.jsonl").open("a") as fh:
        fh.write(json.dumps(_asst("late", PRE.format(30))) + "\n")
    rows2, rep2 = da.account(man)
    assert rep2["integrity"]["verified"] == 1 and rows1 == rows2
    assert rep1["claude"]["A"]["pre"]["numerator_tokens"] == 3000


def test_manifest_detects_rewritten_prefix(tmp_path):
    root = _corpus(tmp_path / "c")
    man = da.build_manifest(root, None)
    data = (root / "s1.jsonl").read_bytes()
    (root / "s1.jsonl").write_bytes(data.replace(b'"m1"', b'"mZ"'))
    _, rep = da.account(man)
    assert rep["integrity"]["mismatch"] == ["s1.jsonl"] and rep["integrity"]["verified"] == 0
    assert rep["claude"]["A"]["pre"]["denominator_tokens"] == 0


def test_unparsable_lines_are_counted_not_dropped_silently(tmp_path):
    root = _corpus(tmp_path / "c")
    with (root / "s1.jsonl").open("a") as fh:
        fh.write('{"parentUuid": torn\n')
    _, rep = da.account(da.build_manifest(root, None))
    assert rep["integrity"]["unparsable_lines"] == 1


def test_cli_end_to_end_is_deterministic(tmp_path):
    root = _corpus(tmp_path / "c")
    man = tmp_path / "m.json"
    assert ft.main(["delegation-manifest", "--claude-root", str(root), "--cutoff",
                    "2026-10-31T00:00:00Z", "--output", str(man)]) == 0
    outs = []
    for n in (1, 2):
        rows, rep = tmp_path / f"r{n}.jsonl", tmp_path / f"rep{n}.json"
        assert ft.main(["delegation-accounting", "--manifest", str(man), "--rows", str(rows),
                        "--output", str(rep)]) == 0
        outs.append((rows.read_bytes(), json.loads(rep.read_text())))
    assert outs[0][0] == outs[1][0] and outs[0][1] == outs[1][1]
    assert outs[0][1]["claude"]["verdict"] == "re-measure"      # no post window


# ---------------------------------------------------------------- Claude proxy (sensitivity)


def _bash_out(ts, lines):
    return {"parentUuid": None, "isSidechain": False, "type": "user", "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "b"}]},
            "toolUseResult": {"stdout": "y\n" * (lines - 1) + "y", "stderr": ""}}


def _proxy(lines):
    recs = [_asst("m0", PRE.format(0)), _bash_out(PRE.format(1), lines),
            _asst("m1", PRE.format(2)), _asst("m2", PRE.format(3))]
    row, _, _ = da.account_claude_session("s", recs, [])
    return row


def test_large_bash_output_enters_proxy_but_never_A():
    row = _proxy(400)
    assert row["a_proxy_windows"]["pre"]["num"] == 2 * 799 / 4
    assert row["a_windows"]["pre"]["num"] == 0


def test_small_bash_output_stays_out_of_proxy():
    assert _proxy(350)["a_proxy_windows"]["pre"]["num"] == 0
