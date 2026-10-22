#!/usr/bin/env python3
"""Convert dev-harness transcripts to AgentRun-style JSON segments (DHM-7, converter half).

Pure python, stdlib only. Same read-only sources and selection flags as projector.py
(vault first; tarballs streamed; live only past the last sync; opencode immutable).

AgentRun shape (Docent's schema, intake-2443#record; written from scratch, no dependency):

  AgentRun   {id, name, description, transcripts: [Transcript], transcript_groups: [], metadata}
  Transcript {messages: [ChatMessage], metadata, created_at}
  ChatMessage role-discriminated: system | user | assistant | tool
     assistant: content (str | [{"type":"text","text"} | {"type":"reasoning","reasoning"}]),
                tool_calls [{id, type:"function", function, arguments: dict}]
     tool:      content, tool_call_id, function, error {type, message} | null
     every message carries metadata {ts, source_line, fidelity, ...}

Interrupt markers are kept as user text: Claude's two verbatim markers
("[Request interrupted by user]" and "[Request interrupted by user for tool use]"), and for
Codex/opencode the abort analogue as "[turn_aborted:interrupted]" / "[message_aborted]" /
"[tool_aborted]" with metadata.marker_synthesized=true.

Sessions are split into TASK-WINDOW segments: a new segment starts at every genuine operator
prompt (record.human), and a window is further capped at --max-messages / --max-chars (a cap
split is marked metadata.continuation=true). Each message text is truncated to --max-msg-chars.

Output is PRIVATE (F3-LB1): <private-root>/agentrun/<run-id>/<harness>/<unit_key>.seg-NNN.json
plus index.jsonl (segment metadata only, used to pick tool-error / denial segments for the
clustering baseline, DHM-7.2).

    nice -n 19 python3 scripts/dev_harness/agentrun.py --claude 8 --codex 8 --opencode 4
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dh_privacy  # noqa: E402
import dh_sources as src  # noqa: E402
import projector  # noqa: E402

AGENTRUN_SCHEMA = "dev-harness-agentrun.v1"
SEGMENT_INDEX_SCHEMA = "dev-harness-agentrun-index.v1"
_SKIP_KINDS = {"usage"}


def _trunc(text: str, cap: int) -> str:
    text = text or ""
    return text if len(text) <= cap else text[:cap] + f"\n…[truncated {len(text) - cap} chars]"


def _trunc_args(args: dict, cap: int) -> dict:
    out = {}
    for k, v in (args or {}).items():
        if isinstance(v, str):
            out[k] = _trunc(v, cap)
        elif isinstance(v, (dict, list)):
            s = json.dumps(v, default=str)
            out[k] = v if len(s) <= cap else _trunc(s, cap)
        else:
            out[k] = v
    return out


def unit_messages(unit: src.Unit, max_msg_chars: int) -> list[tuple[dict, dict]]:
    """[(message, record)] in transcript order. Tool calls fold into their assistant turn."""
    msgs: list[tuple[dict, dict]] = []
    call_names: dict[str, str] = {}
    cur_asst: dict | None = None
    cur_resp = object()

    def meta(r: dict, **kw) -> dict:
        m = {"ts": r.get("ts"), "source_line": r.get("source_line"), "fidelity": r.get("fidelity", "observed"),
             "kind": r["kind"]}
        m.update({k: v for k, v in kw.items() if v not in (None, False)})
        return m

    for r in unit.records:
        k = r["kind"]
        if k in _SKIP_KINDS or (k == "meta" and r.get("subtype") not in ("permission-mode", "mode")):
            continue
        text = _trunc(r.get("text") or "", max_msg_chars)
        if k == "meta":
            msgs.append(({"role": "system", "content": f"[{r.get('subtype')}: {r.get('value')}]",
                          "metadata": meta(r)}, r))
            cur_asst = None
            continue
        if k == "compaction":
            msgs.append(({"role": "system", "content": "[compaction boundary]", "metadata": meta(r)}, r))
            cur_asst = None
            continue
        if k == "interrupt":
            marker = r.get("interrupt")
            if unit.harness == "claude_code":
                content = text
                synth = False
            else:
                content = f"[{marker}]"
                synth = True
            msgs.append(({"role": "user", "content": content,
                          "metadata": meta(r, interrupt=marker, marker_synthesized=synth)}, r))
            cur_asst = None
            continue
        if k == "tool_result":
            tcid = r.get("tool_call_id")
            err = None
            if r.get("is_error"):
                err = {"type": f"denial:{r['denial']}" if r.get("denial") else "tool_error",
                       "message": _trunc(r.get("text") or "", 300)}
            msgs.append(({"role": "tool", "content": text, "tool_call_id": tcid,
                          "function": call_names.get(tcid or ""), "error": err,
                          "metadata": meta(r, denial=r.get("denial"), commit_shas=r.get("commit_shas") or None)}, r))
            cur_asst = None
            continue
        if r.get("role") == "user":
            msgs.append(({"role": "user", "content": text,
                          "metadata": meta(r, human=r.get("human"), is_meta=r.get("is_meta"))}, r))
            cur_asst = None
            continue
        # assistant-side: chat text, reasoning, tool_call — merged per response id
        resp = r.get("response_id")
        if cur_asst is None or resp is None or resp != cur_resp:
            cur_asst = {"role": "assistant", "content": [], "tool_calls": [],
                        "metadata": meta(r, model=r.get("model"), response_id=resp)}
            cur_resp = resp
            msgs.append((cur_asst, r))
        if k == "chat" and text:
            cur_asst["content"].append({"type": "text", "text": text})
        elif k == "reasoning" and text:
            cur_asst["content"].append({"type": "reasoning", "reasoning": text})
        elif k == "tool_call":
            tcid = r.get("tool_call_id")
            if tcid:
                call_names[tcid] = r.get("tool_name")
            cur_asst["tool_calls"].append({"id": tcid, "type": "function", "function": r.get("tool_name"),
                                           "arguments": _trunc_args(r.get("arguments") or {}, max_msg_chars)})
    return msgs


def _msg_chars(m: dict) -> int:
    return len(json.dumps(m, default=str))


def segment(unit: src.Unit, *, max_messages: int, max_chars: int, max_msg_chars: int) -> list[dict]:
    pairs = unit_messages(unit, max_msg_chars)
    windows: list[list[tuple[dict, dict]]] = []
    cur: list[tuple[dict, dict]] = []
    chars = 0
    for m, r in pairs:
        starts_task = bool(r.get("human")) and m["role"] == "user"
        # a prompt opens a new window unless the open one holds only system/meta lines so far
        opens = starts_task and any(cm["role"] != "system" for cm, _ in cur)
        if cur and (opens or len(cur) >= max_messages or chars + _msg_chars(m) > max_chars):
            windows.append(cur)
            cur, chars = [], 0
        cur.append((m, r))
        chars += _msg_chars(m)
    if cur:
        windows.append(cur)
    # continuation flags: window i is a continuation if it did not start with a human prompt
    runs = []
    n = len(windows)
    for i, w in enumerate(windows):
        first_m, first_r = w[0]
        is_cont = i > 0 and not (first_r.get("human") and first_m["role"] == "user")
        msgs = [m for m, _ in w]
        recs = [r for _, r in w]
        tss = sorted(r.get("ts") for r in recs if r.get("ts"))
        interrupts = Counter(r.get("interrupt") for r in recs if r.get("interrupt"))
        denials = Counter(r.get("denial") for r in recs if r.get("denial"))
        tool_errors = sum(1 for r in recs if r["kind"] == "tool_result" and r.get("is_error"))
        md = {
            "schema": AGENTRUN_SCHEMA, "harness": unit.harness, "conversation_id": unit.conversation_id,
            "unit_key": unit.unit_key, "agent_name": unit.agent_name, "agent_instance_id": unit.agent_instance_id,
            "parent_conversation_id": unit.parent_conversation_id, "edge_kind": unit.edge_kind,
            "collection_method": unit.collection_method, "source_path": unit.source_path,
            "source_schema_key": unit.source_schema_key(), "segment_index": i, "n_segments": n,
            "continuation": is_cont, "first_ts": tss[0] if tss else None, "last_ts": tss[-1] if tss else None,
            "day": (tss[0] or "")[:10] if tss else None, "n_messages": len(msgs),
            "tool_calls": sum(len(m.get("tool_calls") or []) for m in msgs), "tool_errors": tool_errors,
            "has_tool_error": tool_errors > 0, "has_denial": bool(denials), "denials": dict(denials),
            "interrupts": dict(interrupts),
        }
        runs.append({
            "id": f"{unit.harness}:{unit.unit_key}:seg{i:03d}",
            "name": f"{unit.harness} {unit.unit_key} segment {i}",
            "description": "",
            "transcripts": [{"messages": msgs, "metadata": {"harness": unit.harness, "segment_index": i},
                             "created_at": tss[0] if tss else None}],
            "transcript_groups": [],
            "metadata": md,
        })
    return runs


def run(a) -> dict:
    t0 = time.time()
    root = Path(a.private_root)
    run_id = a.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = dh_privacy.private_dir(root / "agentrun" / run_id)
    index_rows = []
    n_units = Counter()
    for unit in projector.gather_units(a):
        n_units[unit.harness] += 1
        hdir = dh_privacy.private_dir(out / unit.harness)
        for ar in segment(unit, max_messages=a.max_messages, max_chars=a.max_chars, max_msg_chars=a.max_msg_chars):
            seg_i = ar["metadata"]["segment_index"]
            path = hdir / f"{unit.unit_key}.seg-{seg_i:03d}.json"
            dh_privacy.private_write(path, json.dumps(ar, sort_keys=True, default=str) + "\n")
            index_rows.append({"schema": SEGMENT_INDEX_SCHEMA, "path": str(path), "id": ar["id"], **ar["metadata"]})
    dh_privacy.private_write(out / "index.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in index_rows))
    summary = {
        "schema": "dev-harness-agentrun-run.v1", "run_id": run_id, "code_commit": projector.code_commit(),
        "units": dict(n_units), "segments": len(index_rows),
        "segments_with_tool_error": sum(1 for r in index_rows if r["has_tool_error"]),
        "segments_with_denial": sum(1 for r in index_rows if r["has_denial"]),
        "segments_with_interrupt": sum(1 for r in index_rows if r["interrupts"]),
        "caps": {"max_messages": a.max_messages, "max_chars": a.max_chars, "max_msg_chars": a.max_msg_chars},
        "elapsed_s": round(time.time() - t0, 2),
    }
    dh_privacy.private_write(out / "run.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["out_dir"] = str(out)
    return summary


def build_parser():
    p = projector.build_parser()
    p.description = __doc__
    p.add_argument("--max-messages", type=int, default=120)
    p.add_argument("--max-chars", type=int, default=60000)
    p.add_argument("--max-msg-chars", type=int, default=4000)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if os.environ.get("DEV_HARNESS_ALLOW_NOT_NICE") != "1" and os.nice(0) < 10:
        os.nice(19 - os.nice(0))
    print(json.dumps(run(a), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
