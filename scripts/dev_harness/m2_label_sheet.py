#!/usr/bin/env python3
"""DHM-4 — operator labelling sheet: interrupts + the next operator message.

The OPERATOR labels the sheet; no agent label is ever produced or used (intake-2429). Items carry
only mechanical facts (harness, source, timestamps, elapsed seconds, the marker) plus two short
excerpts: what the agent was doing at the interrupt and what the operator said next.

The sheet is PRIVATE (conversation text): written only under the private mining dir via
dh_privacy, never committed.

Sampling is deterministic: candidates are stratified by (harness, source) with a proportional
allocation (every non-empty stratum gets >=1 item), and within a stratum ordered by a SHA-256 of
(seed, item key).
"""
from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from datetime import datetime

from m2_common import Unit, excerpt, text_of

REASON_CLUSTERS = ("correction", "slow_hanging", "next_step_myself", "requirement_change", "other")
REASON_LABELS = {"correction": "correction", "slow_hanging": "slow/hanging",
                 "next_step_myself": "next step myself", "requirement_change": "requirement change",
                 "other": "other"}
CSV_COLUMNS = ["item_id", "harness", "source", "session", "interrupt_ts", "marker", "role",
               "secs_since_operator_prompt", "secs_since_last_agent_action", "agent_was_doing",
               "next_operator_message", "secs_to_next_message", "label", "note"]

PROVENANCE_TEMPLATE = """\
## Lesson provenance (fill one per new incident / feedback lesson)

- harness: claude_code | codex | opencode
- source: epyc | host | twyne
- session: <unit_key, first 8 chars is enough on this sheet>
- event range: <first_ts> .. <last_ts>  (or segment ids)
- trigger-phrased applicability: "When <situation the agent can recognise>, <do / never do> <action>."
- forbidden surface form (if any): <the command / edit shape a detector can match>
- channel: memory | incident_log | claude_md | hook
"""


def _secs(a: str | None, b: str | None) -> int | None:
    try:
        return int((datetime.fromisoformat(b.replace("Z", "+00:00")) -
                    datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds())
    except (AttributeError, ValueError, TypeError):
        return None


def _agent_action(m: dict) -> str:
    calls = m.get("tool_calls") or []
    if calls:
        tc = calls[-1]
        a = tc.get("arguments") or {}
        detail = ""
        for k in ("command", "cmd", "file_path", "filePath", "description", "pattern", "input", "prompt"):
            if a.get(k):
                detail = a[k] if isinstance(a[k], str) else str(a[k])
                break
        return f"[{tc.get('function')}] {detail}"
    return text_of(m)


def unit_candidates(u: Unit) -> list[dict]:
    out = []
    msgs = u.messages
    last_prompt_ts = None
    for i, m in enumerate(msgs):
        md = m.get("metadata") or {}
        if m.get("role") == "user" and md.get("human"):
            last_prompt_ts = md.get("ts")
        if not md.get("interrupt"):
            continue
        doing, doing_ts = "", None
        for j in range(i - 1, -1, -1):
            mm = msgs[j]
            if mm.get("role") == "assistant" and (mm.get("tool_calls") or text_of(mm)):
                doing, doing_ts = _agent_action(mm), (mm.get("metadata") or {}).get("ts")
                break
            if mm.get("role") == "user" and (mm.get("metadata") or {}).get("human"):
                break
        nxt, nxt_ts = "", None
        for j in range(i + 1, len(msgs)):
            mm = msgs[j]
            mdj = mm.get("metadata") or {}
            if mm.get("role") == "user" and mdj.get("human"):
                nxt, nxt_ts = text_of(mm), mdj.get("ts")
                break
            if mdj.get("interrupt"):
                continue
        ts = md.get("ts")
        out.append({
            "key": f"{u.harness}:{u.source}:{u.unit_key}:{i}",
            "harness": u.harness, "source": u.source, "session": u.unit_key[:8], "unit_key": u.unit_key,
            "interrupt_ts": ts, "marker": md.get("interrupt"), "role": "main" if u.is_main else "subagent",
            "secs_since_operator_prompt": _secs(last_prompt_ts, ts),
            "secs_since_last_agent_action": _secs(doing_ts, ts),
            "agent_was_doing": excerpt(doing, 240) or "(no agent action in this task window)",
            "next_operator_message": excerpt(nxt, 500) or "(none: no later operator message in this session)",
            "secs_to_next_message": _secs(ts, nxt_ts),
        })
    return out


def sample(cands: list[dict], n: int = 100, seed: str = "dhm4-v1") -> list[dict]:
    strata: dict = defaultdict(list)
    for c in cands:
        strata[(c["harness"], c["source"])].append(c)
    for v in strata.values():
        v.sort(key=lambda c: hashlib.sha256(f"{seed}|{c['key']}".encode()).hexdigest())
    total = len(cands)
    if total <= n:
        picked = [c for v in strata.values() for c in v]
    else:
        alloc = {k: max(1, round(n * len(v) / total)) for k, v in strata.items()}
        while sum(alloc.values()) > n:       # trim the largest strata first
            k = max(alloc, key=lambda k: (alloc[k], k))
            alloc[k] -= 1
        while sum(alloc.values()) < n:
            k = max((k for k in alloc if alloc[k] < len(strata[k])), key=lambda k: (len(strata[k]) - alloc[k], k))
            alloc[k] += 1
        picked = [c for k, v in strata.items() for c in v[:alloc[k]]]
    picked.sort(key=lambda c: (c["harness"], c["source"], c["interrupt_ts"] or ""))
    for i, c in enumerate(picked, 1):
        c["item_id"] = f"DHM4-{i:03d}"
    return picked


def render_csv(items: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for it in items:
        w.writerow({**it, "label": "", "note": ""})
    return buf.getvalue()


def render_md(items: list[dict], n_candidates: int, run_id: str) -> str:
    opts = " ".join(f"[ ] {REASON_LABELS[k]}" for k in REASON_CLUSTERS)
    lines = [f"# DHM-4 interrupt labelling sheet — {run_id}", "",
             "PRIVATE: contains conversation excerpts. Do not commit, paste or share.", "",
             f"{len(items)} items sampled from {n_candidates} interrupts (stratified by harness x source, "
             "deterministic seed). For each item tick ONE reason for the interrupt, judged from what the agent "
             "was doing and what you said next, and add a note if useful. Fill the `label` column of the CSV "
             f"with one of: {', '.join(REASON_CLUSTERS)}.", "",
             "Reasons: **correction** (the agent was doing the wrong thing) - **slow/hanging** (stuck, too slow, "
             "waiting on nothing) - **next step myself** (you took over the next step) - **requirement change** "
             "(you changed what you wanted) - **other**.", ""]
    q = lambda v: "?" if v is None else v  # noqa: E731
    for it in items:
        lines += [f"## {it['item_id']} — {it['harness']} / {it['source']} / {it['role']} / {it['interrupt_ts']}",
                  f"marker `{it['marker']}`; {q(it['secs_since_operator_prompt'])}s after your prompt, "
                  f"{q(it['secs_since_last_agent_action'])}s after the agent's last action; next message after "
                  f"{q(it['secs_to_next_message'])}s; session `{it['session']}`", "",
                  f"> **Agent was doing:** {it['agent_was_doing']}", ">",
                  f"> **You said next:** {it['next_operator_message']}", "",
                  f"Label: {opts}", "", "Note: ", ""]
    lines += ["---", "", PROVENANCE_TEMPLATE]
    return "\n".join(lines) + "\n"


def read_labels(csv_text: str) -> dict:
    """Validate an operator-filled CSV; returns {item_id: label} plus the invalid rows."""
    labels, bad = {}, []
    for row in csv.DictReader(io.StringIO(csv_text)):
        lab = (row.get("label") or "").strip().lower().replace("/", "_").replace(" ", "_")
        if not lab:
            continue
        if lab not in REASON_CLUSTERS:
            bad.append(row.get("item_id"))
            continue
        labels[row["item_id"]] = lab
    return {"labels": labels, "invalid": bad}
