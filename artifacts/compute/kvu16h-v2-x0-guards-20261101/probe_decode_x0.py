#!/usr/bin/env python3
"""[X0 COPY of /mnt/raid0/llm/tmp/ds41-c95/probe_decode.py, sha256 b0ea6c69...; changes: --url (
REQUIRED, no default) and --out-dir (default x0 results/probe); contexts still read from ds41-c95 (read-only); all
measurement logic unchanged.  Folded into INF-80 X0 shape (b), Q8_0 arm, one launch.]

DS41-C95 decode-vs-context probe (coordinator request 2026-10-01): SOLO requests to :8083 at
~2k / ~16k / ~50k / ~80k prompt tokens of real DS41 planner context (C2 + C4 inline prompts,
truncated), ~1500 generated tokens, thinking on (template default), 2 reps each; plus one
request per length with speculative drafting disabled per request (`speculative.n_max: 0`,
reusing rep 2's cached prompt so only decode is paid) and a thinking-budget check on both the
chat and the responses endpoints (F12's 8k cap relies on it).

Records per request: llama `timings` (prompt_per_second, predicted_per_second, draft_n,
draft_n_accepted), time-to-first-token, slots busy before the request.
Writes probe-decode-vs-context.<label>.json and appends a section to probe-decode-vs-context.md.

Usage: python3 probe_decode.py --label mtp|dflash2 [--wait-idle-s 1200]
Stdlib only; talks to :8083 directly (no proxy); starts no processes.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
import uuid
from pathlib import Path

BASE = Path("/mnt/raid0/llm/tmp/ds41-c95")  # read-only: contexts/C2, contexts/C4
URL = "http://127.0.0.1:8083"  # overridden by --url
OUT = Path("/mnt/raid0/llm/tmp/x0-27b-quants/results/probe")  # overridden by --out-dir
TARGETS = [2000, 16000, 50000, 80000]
GEN = 1500
GEN_NODRAFT = 500
TASK = ("\n\n---\nTask: using the material above, reason about which single change to the tinyBLAS "
        "gemm4xN<3> kernel would most improve CPU decode throughput, then state it in one paragraph.")


def get(path: str, timeout: float = 10):
    with urllib.request.urlopen(URL + path, timeout=timeout) as r:
        return json.loads(r.read())


def busy_slots() -> list:
    try:
        return [s["id"] for s in get("/slots") if s.get("is_processing")]
    except Exception:  # noqa: BLE001
        return ["unreachable"]


def tokenize_count(text: str) -> int:
    req = urllib.request.Request(URL + "/tokenize", data=json.dumps({"content": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return len(json.loads(r.read())["tokens"])


def stream_chat(body: dict, path: str = "/v1/chat/completions") -> dict:
    if body.get("speculative.n_max") == 0:
        raise RuntimeError("KVU-16h: no-draft requests require a separate server")
    """Streamed request; returns timings, TTFT and reasoning/content sizes."""
    body = {**body, "stream": True}
    if path.endswith("chat/completions"):
        body["stream_options"] = {"include_usage": True}
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    out = {"ttfb_s": None, "ttft_s": None, "reasoning_chars": 0, "content_chars": 0, "timings": None,
           "usage": None, "finish": None, "reasoning_tail": ""}
    rtxt = []
    with urllib.request.urlopen(req, timeout=3600) as r:
        for raw in r:
            if out["ttfb_s"] is None:
                out["ttfb_s"] = round(time.time() - t0, 3)
            line = raw.strip()
            if not line.startswith(b"data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == b"[DONE]":
                continue
            try:
                ev = json.loads(payload)
            except ValueError:
                continue
            resp = ev.get("response") if isinstance(ev.get("response"), dict) else {}
            for src in (ev, resp):
                if isinstance(src.get("timings"), dict):
                    out["timings"] = src["timings"]
                if isinstance(src.get("usage"), dict):
                    out["usage"] = src["usage"]
            got = False
            for ch in ev.get("choices") or []:
                d = ch.get("delta") or {}
                if d.get("reasoning_content"):
                    out["reasoning_chars"] += len(d["reasoning_content"])
                    rtxt.append(d["reasoning_content"])
                    got = True
                if d.get("content"):
                    out["content_chars"] += len(d["content"])
                    got = True
                if ch.get("finish_reason"):
                    out["finish"] = ch["finish_reason"]
            t = ev.get("type") or ""
            if t in ("response.reasoning_text.delta", "response.reasoning.delta"):
                out["reasoning_chars"] += len(ev.get("delta") or "")
                rtxt.append(ev.get("delta") or "")
                got = True
            elif t == "response.output_text.delta":
                out["content_chars"] += len(ev.get("delta") or "")
                got = True
            elif t == "response.completed":
                out["finish"] = resp.get("status")
            if got and out["ttft_s"] is None:
                out["ttft_s"] = round(time.time() - t0, 3)
    out["wall_s"] = round(time.time() - t0, 2)
    out["reasoning_tail"] = "".join(rtxt)[-300:]
    return out


def summarize(rec: dict) -> dict:
    t = rec.get("timings") or {}
    return {"prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
            "prefill_tps": round(t.get("prompt_per_second") or 0, 1),
            "decode_tps": round(t.get("predicted_per_second") or 0, 2), "predicted_n": t.get("predicted_n"),
            "draft_n": t.get("draft_n"), "draft_acc_n": t.get("draft_n_accepted"),
            "draft_acc": round(t["draft_n_accepted"] / t["draft_n"], 3) if t.get("draft_n") else None,
            "ttft_s": rec.get("ttft_s"), "wall_s": rec.get("wall_s")}


def main() -> int:
    global URL, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--wait-idle-s", type=float, default=1200)
    ap.add_argument("--url", required=True)  # X0: no default, never hit production :8083 by accident
    ap.add_argument("--out-dir", type=Path, default=Path("/mnt/raid0/llm/tmp/x0-27b-quants/results/probe"))
    a = ap.parse_args()
    ap.error("KVU-16h: probe requires separate drafted and no-draft servers")
    URL, OUT = a.url.rstrip("/"), a.out_dir
    OUT.mkdir(parents=True, exist_ok=True)
    t_idle = time.time() + a.wait_idle_s
    while busy_slots() and time.time() < t_idle:
        time.sleep(15)
    pre_busy = busy_slots()
    slots = get("/slots")
    drafter_types = sorted({str((s.get("params") or {}).get("speculative.types") or s.get("speculative")) for s in slots})
    props = get("/props")
    text = ((BASE / "contexts/C2/prompt.inline.txt").read_text() + "\n\n"
            + (BASE / "contexts/C4/prompt.inline.txt").read_text())
    full_tok = tokenize_count(text)
    cpt = len(text) / full_tok
    rows, recs = [], []
    for target in TARGETS:
        cut = text[: int(min(len(text), target * cpt))]
        nominal = tokenize_count(cut)
        prompts = []
        for rep in (1, 2):
            msg = f"[probe {a.label} {uuid.uuid4().hex}]\n" + cut + TASK  # nonce first: no prefix-cache reuse
            prompts.append(msg)
            busy = busy_slots()
            r = stream_chat({"messages": [{"role": "user", "content": msg}], "max_tokens": GEN})
            s = {"label": a.label, "target": target, "nominal_tokens": nominal, "variant": "drafted",
                 "rep": rep, "busy_before": busy, **summarize(r)}
            rows.append(s)
            recs.append({**s, "raw": r})
            print(json.dumps(s), flush=True)
        busy = busy_slots()
        r = stream_chat({"messages": [{"role": "user", "content": prompts[1]}], "max_tokens": GEN_NODRAFT,
                         "speculative.n_max": 0})
        s = {"label": a.label, "target": target, "nominal_tokens": nominal, "variant": "no-draft (n_max 0, cached prompt)",
             "rep": 1, "busy_before": busy, **summarize(r)}
        rows.append(s)
        recs.append({**s, "raw": r})
        print(json.dumps(s), flush=True)
    # thinking-budget checks (F12's 8k cap): budget 256, chat + responses paths
    short = text[: int(2000 * cpt)] + TASK
    budget_checks = []
    for path in ("/v1/chat/completions", "/v1/responses"):
        nonce = f"[probe-budget {uuid.uuid4().hex}]\n"
        body = ({"messages": [{"role": "user", "content": nonce + short}]} if path.endswith("completions")
                else {"input": nonce + short, "model": "Qwen3.8-27B-Q8_0"})
        body.update({"max_tokens" if path.endswith("completions") else "max_output_tokens": 1500,
                     "thinking_budget_tokens": 256,
                     "reasoning_budget_message": "\n[budget reached; answer now]\n"})
        try:
            r = stream_chat(body, path)
            t = r.get("timings") or {}
            chk = {"path": path, "reasoning_chars": r["reasoning_chars"], "content_chars": r["content_chars"],
                   "predicted_n": t.get("predicted_n"), "finish": r.get("finish"),
                   "reasoning_tail": r.get("reasoning_tail"),
                   # 256 tokens of reasoning ~ 700-1100 chars; honoured if well under the 1500-token cap
                   # reasoning_chars == 0 means the stream exposed no reasoning deltas: unverifiable, not honoured
                   "honoured": (0 < r["reasoning_chars"] < 2500 and r["content_chars"] > 0) if r["reasoning_chars"]
                               else None}
        except Exception as exc:  # noqa: BLE001
            chk = {"path": path, "error": f"{type(exc).__name__}: {exc}"[:300], "honoured": False}
        budget_checks.append(chk)
        print(json.dumps({k: v for k, v in chk.items() if k != "reasoning_tail"}), flush=True)
    post_busy = busy_slots()
    out = {"label": a.label, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "speculative_types": drafter_types, "build": props.get("build_info"),
           "n_ctx_slot": min(s["n_ctx"] for s in slots), "busy_at_start": pre_busy, "busy_at_end": post_busy,
           "rows": rows, "budget_checks": budget_checks, "records": recs}
    (OUT / f"probe-decode-vs-context.{a.label}.json").write_text(json.dumps(out, indent=1) + "\n")
    # markdown section
    L = [f"\n## {a.label}: speculative.types {drafter_types}, build {props.get('build_info')}, {out['at']}\n",
         f"Solo check: busy slots at start {pre_busy or 'none'}, at end {post_busy or 'none'}"
         " (any non-empty busy_before below means another client shared the server).\n",
         "| target | prompt tok | variant | rep | prefill tok/s | TTFT s | decode tok/s | gen tok | draft acc | busy before |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for s in rows:
        L.append(f"| ~{s['target'] // 1000}k | {s['prompt_n']} (cache {s['cache_n']}) | {s['variant']} | {s['rep']} | "
                 f"{s['prefill_tps']} | {s['ttft_s']} | {s['decode_tps']} | {s['predicted_n']} | "
                 f"{s['draft_acc'] if s['draft_acc'] is not None else '-'} | {s['busy_before'] or '-'} |")
    L.append("")
    L.append("Thinking-budget check (thinking_budget_tokens=256): " + "; ".join(
        f"{c['path']}: {'HONOURED' if c.get('honoured') else ('UNVERIFIABLE (no reasoning deltas)' if c.get('honoured') is None and 'error' not in c else 'NOT honoured')} (reasoning {c.get('reasoning_chars')} chars, "
        f"content {c.get('content_chars')} chars, gen {c.get('predicted_n')})" for c in budget_checks))
    d = {t: [s for s in rows if s["target"] == t] for t in TARGETS}
    dr = {t: [s["decode_tps"] for s in v if s["variant"] == "drafted"] for t, v in d.items()}
    nd = {t: [s["decode_tps"] for s in v if s["variant"] != "drafted"] for t, v in d.items()}
    acc = {t: [s["draft_acc"] for s in v if s["variant"] == "drafted" and s["draft_acc"] is not None] for t, v in d.items()}
    def m(x):
        return round(sum(x) / len(x), 1) if x else None
    L.append("")
    L.append("**Interpretation (auto-generated from the table):**")
    L.append(f"1. Drafted decode falls from {m(dr[TARGETS[0]])} tok/s at ~2k to {m(dr[TARGETS[-1]])} tok/s at ~80k "
             f"(no-draft: {m(nd[TARGETS[0]])} -> {m(nd[TARGETS[-1]])}); the no-draft ratio isolates long-context attention cost.")
    L.append(f"2. Drafter speed-up (drafted / no-draft): " + ", ".join(
        f"~{t // 1000}k x{round(m(dr[t]) / m(nd[t]), 2) if m(dr[t]) and m(nd[t]) else '-'}" for t in TARGETS)
             + "; acceptance " + ", ".join(f"~{t // 1000}k {m(acc[t]) if acc[t] else '-'}" for t in TARGETS) + ".")
    L.append(f"3. Prefill is {m([s['prefill_tps'] for s in d[TARGETS[-1]] if s['variant'] == 'drafted'])} tok/s at ~80k; "
             f"TTFT at ~80k = {m([s['ttft_s'] for s in d[TARGETS[-1]] if s['variant'] == 'drafted' and s['ttft_s']])} s "
             "(the codex idle-timeout scale).")
    md = OUT / "probe-decode-vs-context.md"
    head = "" if md.exists() else ("# Decode vs context on :8083 (Qwen3.8-27B Q8_0)\n\nSolo probe, real DS41 planner "
                                   "context (C2+C4 inline prompts, truncated), thinking on, 1500 generated tokens, 2 reps; "
                                   "no-draft rows reuse rep 2's cached prompt with `speculative.n_max: 0`.\n")
    with open(md, "a") as fh:
        fh.write(head + "\n".join(L) + "\n")
    print(f"PROBE DONE {a.label}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
