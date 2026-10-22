#!/usr/bin/env python3
"""UFH14-LB9.1: re-tokenization gap on TOOL-CALL turns, rendered through each role's GGUF chat template.

Extends orchestrator ``scripts/analysis/ufh14_lb9_retokenize_gap.py`` (text-only turns) to assistant turns that
carry tool parts. Each logged tool-call turn is rebuilt as a structured assistant message
(content + tool_calls), rendered through the role's chat template (research repo
``scripts/benchmark/prefix_property/harness.py``: v10 jinja engine + ``llama-tokenize`` vocab_only), and the
segment the template appends for that message is tokenized. diff = reported ``tokens.output`` - rendered
segment length. NO model inference; GGUF header only; snapshots opened ``mode=ro`` (live stores refused).
Aggregates go to stdout; per-turn token counts (no text) go to --private-out (private dir only).

Run:  nice -n 19 /usr/bin/python3 -B scripts/analysis/ufh14_lb9_1_toolcall_retok.py --max-turns 120
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

RESEARCH = Path("/workspace/repos/epyc-inference-research/scripts/benchmark/prefix_property")
ORCH_ANALYSIS = Path("/workspace/repos/epyc-orchestrator/scripts/analysis")
REGISTRY = "/workspace/repos/epyc-orchestrator/orchestration/model_registry.yaml"
# opencode model id -> registry entry ids (prefix match on entry id)
MODEL_TO_ENTRY = {
    "qwen3.8-27b": ["Qwen3.8-27B-Q8_0+file:", "Qwen3.8-27B-Q8_0+embedded"],
    "qwen3.8-flash-next": ["Qwen3.8-Flash-Next"],
}
SNAPSHOTS = {"epyc": "/mnt/raid0/llm/opencode-db/epyc.db", "host": "/mnt/raid0/llm/opencode-db/host-daniele.db"}


def open_ro(path: str):
    sys.path.insert(0, str(ORCH_ANALYSIS))
    import opencode_ro
    opencode_ro.refuse_live_opencode_path(path)
    for attempt in (0, 1):
        try:
            return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        except sqlite3.Error:
            if attempt:
                raise
            time.sleep(2)


def build_message(parts: list[dict]) -> dict | None:
    """Structured assistant message from a turn's parts, or None if not a clean tool-call turn."""
    kinds = {p.get("type") for p in parts}
    if "tool" not in kinds or "reasoning" in kinds:
        return None
    calls = []
    for p in parts:
        if p.get("type") != "tool":
            continue
        args = (p.get("state") or {}).get("input")
        if not isinstance(args, dict) or not p.get("tool"):
            return None
        calls.append({"type": "function", "function": {"name": p["tool"], "arguments": args}})
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    return {"role": "assistant", "content": text, "tool_calls": calls}


def summarise(rows: list[tuple[int, int]]) -> dict:
    diffs = [r - t for r, t in rows]
    n = len(diffs)
    if not n:
        return {"n": 0}
    c = Counter(diffs)
    mode, mode_n = c.most_common(1)[0]
    above = sum(v for d, v in c.items() if d > mode)
    below = sum(v for d, v in c.items() if d < mode)
    return {"n": n, "modal_offset": mode, "modal_share": round(mode_n / n, 4),
            "rows_above_mode": above, "rows_below_mode": below,
            "share_above_mode": round(above / n, 4), "share_below_mode": round(below / n, 4),
            "median_diff": statistics.median(diffs), "diff_histogram": dict(sorted(c.items())[:30])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sessions", type=int, default=40)
    ap.add_argument("--per-session", type=int, default=60)
    ap.add_argument("--max-turns", type=int, default=120, help="cap per (source, model) cell")
    ap.add_argument("--private-out")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(RESEARCH))
    import harness as h
    entries = {e["id"]: e for e in h.role_templates(REGISTRY)}
    engines = {}
    for mid, prefixes in MODEL_TO_ENTRY.items():
        for eid, e in entries.items():
            if any(eid.startswith(p) for p in prefixes):
                engines[(mid, eid)] = h.engine_for(e)
    base_user = [{"role": "user", "content": "go"}]
    agg: dict[str, list] = {}
    excluded: Counter = Counter()
    private = []
    for src, path in SNAPSHOTS.items():
        con = open_ro(path)
        for mid in MODEL_TO_ENTRY:
            cell = 0
            sess = [r[0] for r in con.execute(
                "SELECT id FROM session WHERE model LIKE ? ORDER BY time_updated DESC LIMIT ?",
                (f'%"id":"{mid}"%', a.sessions))]
            excluded[f"{src}/{mid}/sessions"] += len(sess)
            for sid in sess:
                for m_id, out, finish in con.execute(
                        "SELECT id, json_extract(data,'$.tokens.output'), json_extract(data,'$.finish') FROM message "
                        "WHERE session_id=? AND json_extract(data,'$.role')='assistant' ORDER BY time_created LIMIT ?",
                        (sid, a.per_session)).fetchall():
                    if cell >= a.max_turns:
                        break
                    parts = [json.loads(p[0]) for p in con.execute(
                        "SELECT data FROM part WHERE message_id=? ORDER BY id", (m_id,))]
                    msg = build_message(parts)
                    if msg is None:
                        k = {p.get("type") for p in parts}
                        excluded["excl_reasoning_turn" if "reasoning" in k else "excl_no_tool_part" if "tool" not in k
                                 else "excl_unusable_tool_input"] += 1
                        continue
                    if not isinstance(out, int) or out <= 0:
                        excluded["no_output_tokens"] += 1
                        continue
                    cell += 1
                    for (m2, eid), (eng, tok, eog) in engines.items():
                        if m2 != mid:
                            continue
                        try:
                            base = eng.render(base_user, add_generation_prompt=True)
                            full = eng.render(base_user + [msg], add_generation_prompt=False)
                        except RuntimeError:
                            excluded[f"{eid}/render_failed"] += 1
                            continue
                        if not full.startswith(base):
                            excluded[f"{eid}/segment_not_prefix_extension"] += 1
                            continue
                        seg = full[len(base):]
                        if seg.endswith("\n"):
                            seg = seg[:-1]       # template's separator after eog is not generated
                        n = len(tok(seg))
                        agg.setdefault(f"{src}|{mid}|{eid}", []).append((out, n))
                        private.append({"src": src, "sid": sid, "mid": m_id, "entry": eid, "reported": out, "rendered": n,
                                        "n_calls": len(msg["tool_calls"])})
        con.close()
    res = {k: summarise(v) for k, v in sorted(agg.items())}
    allrows = [r for v in agg.values() for r in v]
    print(json.dumps({"by_cell": res, "pooled": summarise(allrows), "excluded": dict(excluded)}, indent=1, sort_keys=True))
    if a.private_out:
        Path(a.private_out).write_text("\n".join(json.dumps(r) for r in private))
    return 0


if __name__ == "__main__":
    sys.exit(main())
