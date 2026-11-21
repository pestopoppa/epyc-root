#!/usr/bin/env python3
"""TOC-CMP-NONPROSE-TALLY part 2: composition of the FINAL request context of agentic wire traces.

Source: ds41-c95 F12 wire bodies (Codex agent on the 27B role; full request bodies retained).
Categories (chars scaled to server input_tokens of that request, so shares are token shares):
  instructions / model_prose (assistant messages + reasoning) / user_task_prompt_unclassified (the user turn(s): the
  task prompt embeds profile tables and code excerpts, so it is NOT classified prose or non-prose here)
  nonprose   : function_call_output (shell / file / test output), counted per rule below
  call_args  : function_call arguments (commands / code the model wrote) - reported separately, not prose
Per-command class of function_call_output (by the paired call's cmd): file-read (cat/sed -n/head/tail/rg/grep/ls/find),
test-or-build (pytest/make/cmake/ctest/build), other-shell.
"""
import collections, glob, gzip, json, re

R = "/mnt/raid0/llm/tmp/ds41-c95/results"
tot = collections.Counter()
per_call = {}
for d in sorted(glob.glob(f"{R}/C[24]/cxf1*/r[12]")):
    rows = [json.loads(l) for l in gzip.open(d + "/wire/wire-bodies.jsonl.gz", "rt")]
    wire = {json.loads(l)["seq"]: json.loads(l) for l in open(d + "/wire/wire.jsonl")}
    last = rows[-1]; body = last["body"]
    cnt = collections.Counter(); calls = {}
    cnt["instructions"] += len(body.get("instructions") or "")
    cnt["tools_schema"] += len(json.dumps(body.get("tools") or []))
    for it in body["input"]:
        t = it.get("type")
        if t == "message":
            k = {"user": "user_task_prompt_unclassified", "developer": "instructions"}.get(it.get("role"), "model_prose")
            cnt[k] += sum(len(c.get("text", "")) for c in it.get("content", []))
        elif t == "reasoning":
            cnt["model_prose"] += sum(len(c.get("text", "")) for c in it.get("content", []) or [])
        elif t == "function_call":
            a = it.get("arguments") or ""
            cnt["call_args"] += len(a)
            try:
                calls[it.get("call_id")] = json.loads(a).get("cmd", "")
            except Exception:
                calls[it.get("call_id")] = ""
        elif t == "function_call_output":
            n = len(json.dumps(it.get("output")))
            cmd = calls.get(it.get("call_id"), "")
            if re.search(r"pytest|\bmake\b|cmake|ctest|test-", cmd):
                k = "nonprose_test_build"
            elif re.search(r"\b(cat|sed|head|tail|rg|grep|ls|find|nl|wc)\b", cmd):
                k = "nonprose_file_read"
            else:
                k = "nonprose_other_shell"
            cnt[k] += n
    chars = sum(cnt.values())
    in_tok = (wire.get(last["seq"]) or {}).get("usage", {}).get("input_tokens") or 0
    scale = in_tok / chars if chars and in_tok else 0
    per_call[d.split("results/")[1]] = {"input_tokens": in_tok, **{k: round(v * scale) for k, v in cnt.items()}}
    tot.update({k: v * scale for k, v in cnt.items()})
    tot["input_tokens"] += in_tok
np_ = sum(v for k, v in tot.items() if k.startswith("nonprose"))
out = {"calls": len(per_call), "tokens_total": round(tot["input_tokens"]),
       "share": {k: round(v / tot["input_tokens"], 3) for k, v in tot.items() if k != "input_tokens"},
       "nonprose_total_share": round(np_ / tot["input_tokens"], 3), "per_call": per_call}
print(json.dumps(out, indent=1))
