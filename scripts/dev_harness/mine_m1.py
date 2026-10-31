#!/usr/bin/env python3
"""Dev-harness mining wave M1: DHM-1, DHM-5, OAB-LB1, UFH14-LB8 over one projection.

One driver, one pass per input, stdlib only. It reads

  * a private projection (``projector.py`` output: sessions.jsonl + events/**.jsonl) for
    DHM-1 (interrupt series) and DHM-5 (always-on prefix tokens per turn);
  * the vault's raw Codex rollouts for OAB-LB1 (AK-lane thread census: the projection keeps no
    turn ids, no exec command and no wall time);
  * the read-only opencode snapshots (``dh_sources.open_ro``, never the live store, never the
    ``event`` table) for UFH14-LB8 (step-level prefix-cache / gap / append / tool-duration pass);
  * optionally a Claude Code prompt history (``--history``) for the DHM-1 correction keyword pass.

Outputs (F3-LB1): per-session rows ONLY under
``<private-root>/mining/<run-id>/m1/*.sessions.jsonl``; aggregates (dev-harness-aggregate.v1, counts,
rates, Wilson CIs, rule text) under ``<private-root>/mining/<run-id>/m1/aggregates/``, each checked by
``dh_privacy.validate_aggregate``. Nothing is written into a repository; committing an aggregate
is a separate, human-run ``dh_privacy.publish_aggregate`` step.

Full run (scheduled by the main thread, outside a quiet window):

    nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m1.py \\
        --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import os
import re
import shlex
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dh_privacy  # noqa: E402
import dh_sources as src  # noqa: E402

AGG = dh_privacy.AGGREGATE_SCHEMA
Z95 = 1.959963984540054
QUANTS = (0.1, 0.25, 0.5, 0.75, 0.9, 0.99)


# ─── statistics ──────────────────────────────────────────────────────────────

def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials (0,0 when n == 0)."""
    if n <= 0:
        return 0.0, 0.0
    k = min(max(k, 0), n)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def rate_block(k: int, n: int, per: int = 1000) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, f"per_{per}": round(per * k / n, 4) if n else 0.0,
            "ci95_lo": round(per * lo, 4), "ci95_hi": round(per * hi, 4)}


def quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def dist(vals: Iterable[float]) -> dict:
    """Quantile summary (a CDF at fixed points) as keyed numbers: aggregates carry no lists."""
    v = sorted(float(x) for x in vals)
    out: dict[str, float] = {"n": len(v)}
    if not v:
        return out
    for q in QUANTS:
        out[f"p{int(q * 100)}"] = round(quantile(v, q), 3)
    out["min"], out["max"] = round(v[0], 3), round(v[-1], 3)
    out["mean"] = round(sum(v) / len(v), 3)
    return out


def log2_hist(vals: Iterable[float]) -> dict:
    h: Counter = Counter()
    for x in vals:
        h["le0" if x <= 0 else f"2^{int(math.floor(math.log2(x)))}"] += 1
    return dict(sorted(h.items(), key=lambda kv: (-1 if kv[0] == "le0" else int(kv[0][2:]))))


def bimodality_coefficient(vals: list[float]) -> float:
    """Sarle's sample bimodality coefficient; > 5/9 ≈ 0.555 suggests bi/multimodality."""
    n = len(vals)
    if n < 4:
        return 0.0
    m = sum(vals) / n
    m2 = sum((x - m) ** 2 for x in vals) / n
    if m2 <= 0:
        return 0.0
    m3 = sum((x - m) ** 3 for x in vals) / n
    m4 = sum((x - m) ** 4 for x in vals) / n
    g = m3 / m2 ** 1.5
    k = m4 / m2 ** 2 - 3
    return round((g * g + 1) / (k + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))), 4)


def frame(days: Iterable[str | None]) -> dict:
    """Sample frame as numbers: units, first/last day (YYYYMMDD) and distinct days."""
    ds = [d for d in days]
    good = sorted({d for d in ds if d and len(d) == 10})
    return {"units": len(ds), "distinct_days": len(good),
            "first_day": int(good[0].replace("-", "")) if good else 0,
            "last_day": int(good[-1].replace("-", "")) if good else 0}


def nest() -> defaultdict:
    return defaultdict(nest)


def plain(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: plain(v) for k, v in d.items()}
    return d


# ─── projection reading ──────────────────────────────────────────────────────

_VAULT_TENANT_RE = re.compile(r"/cloud-llm-vault/(epyc|host|twyne)/")


def source_of(row: dict) -> str:
    """The projection's ``source`` tag; older projections lack it, so derive it from the path."""
    if row.get("source"):
        return row["source"]
    p = row.get("source_path") or ""
    m = _VAULT_TENANT_RE.search(p)
    if m:
        return m.group(1)
    if "/opencode-db/epyc.db" in p or "/home/node/.local/share/opencode" in p:
        return "epyc"      # this container's own store (sample projections predating the tag)
    if "host-daniele.db" in p:
        return "host"
    return "unknown"


def role_of(row: dict) -> str:
    if row.get("parent_conversation_id") or ".agent-" in (row.get("unit_key") or ""):
        return "subagent"
    return "main"


def iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(d, dict):
                    yield d


def load_sessions(proj: Path) -> dict[tuple[str, str, str], dict]:
    return {(s["harness"], source_of(s), s["unit_key"]): s for s in iter_jsonl(proj / "sessions.jsonl")}


def event_files(proj: Path) -> list[Path]:
    # main units before their subagents, so a marker copied into a child is attributed to the main
    return sorted((proj / "events").rglob("*.jsonl"), key=lambda p: (".agent-" in p.name, str(p)))


def _month(ts: str | None) -> str:
    return (ts or "")[:7] or "unknown"


# ─── DHM-1 + DHM-5: one pass over events ─────────────────────────────────────

REPLAY_WINDOW_S = 5.0   # codex fork/spawn children replay parent history (fresh timestamps) at birth
CPT_UNRELIABLE = {"claude_code"}   # stale streamed output_tokens in the transcript
CPT_MIN_TOKENS = 2000
DEFAULT_CPT = 3.6                   # assumed chars/token for English markdown when nothing calibrates


def _ts_s(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def scan_unit(events: list[dict], sess: dict) -> dict:
    """Per-unit facts for DHM-1 and DHM-5 from its event rows (content-free)."""
    events.sort(key=lambda e: (e.get("ts") or "", str(e.get("source_line"))))
    first = _ts_s(sess.get("first_ts"))
    replay_child = sess["harness"] == "codex" and bool(sess.get("parent_conversation_id"))
    out = {"interrupts": Counter(), "interrupts_raw": Counter(), "interrupt_keys": [],
           "turns": 0, "turns_raw": 0, "prompt_tok": [], "cache_read": [], "first_prompt": None,
           "resp_chars": Counter(), "resp_reasoning": set(), "resp_out": {}}
    for e in events:
        kind = e.get("event_kind")
        d = e.get("detail_json") or {}
        t = _ts_s(e.get("ts"))
        in_replay = replay_child and first is not None and t is not None and t - first <= REPLAY_WINDOW_S
        if kind == "interrupt":
            m = d.get("dh.interrupt") or "unknown"
            out["interrupts_raw"][m] += 1
            if not in_replay:
                out["interrupts"][m] += 1
                out["interrupt_keys"].append((m, e.get("ts")))
        elif kind == "usage":
            out["turns_raw"] += 1
            if in_replay:
                continue
            out["turns"] += 1
            inp = int(d.get("gen_ai.usage.input_tokens") or 0)
            out["prompt_tok"].append(inp)
            out["cache_read"].append(int(d.get("gen_ai.usage.cache_read.input_tokens") or 0))
            if out["first_prompt"] is None and inp > 0:
                out["first_prompt"] = inp
            rid = d.get("gen_ai.response.id")
            if rid:
                out["resp_out"][rid] = int(d.get("gen_ai.usage.output_tokens") or 0)
        elif d.get("dh.role") == "assistant" and kind in ("chat", "reasoning", "tool_call"):
            rid = d.get("gen_ai.response.id")
            if rid:
                out["resp_chars"][rid] += int((e.get("content") or {}).get("n_chars") or 0)
                if kind == "reasoning":
                    out["resp_reasoning"].add(rid)
    return out


def mine_projection(proj: Path, priv_out: Path, static_files: dict[str, Path]) -> dict[str, dict]:
    sessions = load_sessions(proj)
    rows1, rows5 = [], []
    seen_interrupt: set = set()       # cross-unit dedupe: (family, marker, ts) — Claude fork copies keep ts
    cal = defaultdict(lambda: [0, 0])     # harness -> [chars, output tokens] (responses without reasoning)
    for f in event_files(proj):
        evs = list(iter_jsonl(f))
        if not evs:
            continue
        key = (evs[0].get("harness"), source_of(evs[0]), evs[0].get("unit_key"))
        sess = sessions.get(key)
        if sess is None:
            continue
        u = scan_unit(evs, sess)
        fam = sess.get("parent_conversation_id") or sess.get("conversation_id") or sess["unit_key"]
        dedup = Counter()
        for m, ts in u["interrupt_keys"]:
            k = (sess["harness"], fam, m, ts)
            if ts and k in seen_interrupt:
                continue
            seen_interrupt.add(k)
            dedup[m] += 1
        for rid, out_tok in u["resp_out"].items():
            if rid in u["resp_reasoning"] or out_tok <= 0 or u["resp_chars"].get(rid, 0) <= 0:
                continue
            cal[sess["harness"]][0] += u["resp_chars"][rid]
            cal[sess["harness"]][1] += out_tok
        base = {"harness": sess["harness"], "source": source_of(sess), "role": role_of(sess),
                "agent_name": sess.get("agent_name"), "unit_key": sess["unit_key"],
                "month": _month(sess.get("first_ts")), "day": (sess.get("first_ts") or "")[:10] or None}
        rows1.append({**base, "turns": u["turns"], "turns_raw": u["turns_raw"],
                      "human_turns": int(sess.get("human_turns") or 0),
                      "interrupts": dict(dedup), "interrupts_raw": dict(u["interrupts_raw"])})
        pt = sorted(u["prompt_tok"])
        rows5.append({**base, "turns": u["turns"], "first_prompt_tok": u["first_prompt"],
                      "median_prompt_tok": quantile(pt, 0.5) if pt else None,
                      "sum_prompt_tok": sum(pt), "sum_cache_read_tok": sum(u["cache_read"])})
    dh_privacy.private_write(priv_out / "dhm1.sessions.jsonl", "".join(json.dumps(r) + "\n" for r in rows1))
    dh_privacy.private_write(priv_out / "dhm5.sessions.jsonl", "".join(json.dumps(r) + "\n" for r in rows5))
    return {"dhm1": aggregate_dhm1(rows1), "dhm5": aggregate_dhm5(rows5, cal, static_files)}


def aggregate_dhm1(rows: list[dict]) -> dict:
    counts = nest()
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["harness"], r["source"], r["role"])].append(r)
        groups[(r["harness"], "all", r["role"])].append(r)
        groups[(r["harness"], "all", "all")].append(r)
    for (h, s, role), rs in sorted(groups.items()):
        turns = sum(r["turns"] for r in rs)
        human = sum(r["human_turns"] for r in rs)
        markers = Counter()
        raw = Counter()
        for r in rs:
            markers.update(r["interrupts"])
            raw.update(r["interrupts_raw"])
        g = counts["by_harness"][h][s][role]
        g["units"] = len(rs)
        g["turns"] = turns
        g["human_turns"] = human
        g["units_with_interrupt"] = sum(1 for r in rs if r["interrupts"])
        for m, k in sorted(markers.items()):
            g["per_1000_turns"][m] = rate_block(k, turns)
        g["per_1000_turns"]["any"] = rate_block(sum(markers.values()), turns)
        if human:
            g["per_1000_human_turns"]["any"] = rate_block(sum(markers.values()), human)
        g["replay_excluded"]["interrupts"] = sum(raw.values()) - sum(markers.values())
        g["replay_excluded"]["turns"] = sum(r["turns_raw"] for r in rs) - turns
    months = defaultdict(list)
    for r in rows:
        months[(r["harness"], r["role"], r["month"])].append(r)
    for (h, role, mo), rs in sorted(months.items()):
        turns = sum(r["turns"] for r in rs)
        k = sum(sum(r["interrupts"].values()) for r in rs)
        counts["series_by_month"][h][role][mo] = rate_block(k, turns)
    counts["frame"] = frame(r["day"] for r in rows)
    return {"schema": AGG, "spec": "DHM-1 interrupt markers per 1000 turns (Wilson 95%)",
            "counts": plain(counts),
            "rules": [
                "turn = one deduplicated assistant model call (usage record) of the unit",
                "markers: claude plain/tool_use; codex turn_aborted:<reason>; opencode message_aborted/tool_aborted",
                f"codex child threads: events within {REPLAY_WINDOW_S:g}s of thread birth are replayed parent "
                "history and are excluded from both numerator and denominator (raw kept under replay_excluded)",
                "an interrupt seen twice in one family with the same timestamp and marker counts once",
                "role subagent = unit has a parent conversation (claude subagents/, codex spawn/fork, opencode parent)",
                "Wilson intervals treat turns as independent; turns cluster by session, so they are optimistic",
            ]}


def aggregate_dhm5(rows: list[dict], cal: dict, static_files: dict[str, Path]) -> dict:
    counts = nest()
    # Claude Code's JSONL repeats the FIRST streamed usage on every content-block line, so its
    # output_tokens under-count (sample: 14.5 chars/token); only harnesses with final per-message
    # output counts calibrate. Fallback when none has enough tokens: DEFAULT_CPT (assumed, flagged).
    usable = {h: v for h, v in cal.items() if h not in CPT_UNRELIABLE and v[1] >= CPT_MIN_TOKENS}
    pooled = [sum(v[0] for v in usable.values()), sum(v[1] for v in usable.values())]
    cpt_pooled = round(pooled[0] / pooled[1], 4) if pooled[1] else DEFAULT_CPT
    for h, (c, t) in sorted(cal.items()):
        counts["chars_per_token_calibration"][h] = {"chars": c, "output_tokens": t,
                                                    "chars_per_token": round(c / t, 4) if t else 0.0,
                                                    "used": int(h in usable)}
    counts["chars_per_token_calibration"]["applied"] = {"chars_per_token": cpt_pooled,
                                                        "assumed_default": int(not pooled[1])}
    cpt: dict[str, float] = {}
    file_chars = {}
    for name, p in static_files.items():
        try:
            file_chars[name] = len(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            file_chars[name] = 0
    always_on_files = {"claude_code": {"main": ("CLAUDE.md", "MEMORY.md"), "subagent": ("CLAUDE.md",)},
                       "codex": {"main": ("AGENTS.md",), "subagent": ("AGENTS.md",)},
                       "opencode": {"main": ("AGENTS.md",), "subagent": ("AGENTS.md",)}}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["turns"] <= 0:
            continue
        groups[(r["harness"], r["source"], r["role"])].append(r)
        groups[(r["harness"], "all", r["role"])].append(r)
    for (h, s, role), rs in sorted(groups.items()):
        g = counts["by_harness"][h][s][role]
        turns = sum(r["turns"] for r in rs)
        prompt = sum(r["sum_prompt_tok"] for r in rs)
        g["units"], g["turns"] = len(rs), turns
        g["first_turn_prompt_tok"] = dist(r["first_prompt_tok"] for r in rs if r["first_prompt_tok"])
        g["median_prompt_tok_per_turn"] = dist(r["median_prompt_tok"] for r in rs if r["median_prompt_tok"])
        g["mean_prompt_tok_per_turn"] = round(prompt / turns, 1) if turns else 0.0
        g["cache_read_share"] = round(sum(r["sum_cache_read_tok"] for r in rs) / prompt, 4) if prompt else 0.0
        c = cpt.get(h, cpt_pooled)
        names = always_on_files.get(h, {}).get(role, ())
        est = sum(file_chars.get(n, 0) for n in names) / c if c else 0.0
        floor = g["first_turn_prompt_tok"].get("p50", 0.0)
        g["always_on_files_est_tok_per_turn"] = round(est, 1)
        g["always_on_files_share_of_first_turn_p50"] = round(est / floor, 4) if floor else 0.0
        g["always_on_files_share_of_mean_turn"] = round(est * turns / prompt, 4) if prompt else 0.0
        g["always_on_files_est_tok_total"] = round(est * turns, 0)
    for n, ch in sorted(file_chars.items()):
        counts["static_file_chars"][n.replace(".", "_")] = ch
    counts["frame"] = frame(r["day"] for r in rows)
    return {"schema": AGG, "spec": "DHM-5 always-on prefix (CLAUDE.md + MEMORY.md index) tokens per turn",
            "counts": plain(counts),
            "rules": [
                "first_turn_prompt_tok = input tokens INCLUSIVE of cache on the unit's first non-replayed model call "
                "= system prompt + tool schemas + always-on files + first message: the observed per-turn floor",
                "always_on_files_est = current file chars / chars-per-token calibrated on assistant output of harnesses "
                "with final per-message output counts (responses with no reasoning: chars of text+tool_call vs usage "
                "output tokens), pooled; claude_code is excluded (its JSONL usage output_tokens are stale stream "
                f"values); {DEFAULT_CPT} assumed when nothing calibrates (flagged assumed_default=1)",
                "files counted: claude main CLAUDE.md+MEMORY.md, claude subagent CLAUDE.md; codex/opencode AGENTS.md",
                "the files are re-sent on every turn, so tokens per turn = the estimate; share_of_mean_turn is its "
                "fraction of all prompt tokens; file sizes are TODAY's, sessions span months (dated sizes not used)",
            ]}


# ─── DHM-1 correction keyword pass (prompt history) ──────────────────────────

CORRECTION_PATTERNS = {
    "no_comma": r"^\s*no[,.!]",
    "not_what_i": r"\bnot what i\b",
    "i_said": r"\bi (said|asked|told you)\b",
    "dont_do": r"\b(don't|do not|never|stop)\b",
    "wrong": r"\b(wrong|incorrect|mistake)\b",
    "why_did_you": r"\bwhy (did|are|would) you\b",
    "undo_revert": r"\b(undo|revert|roll ?back)\b",
    "instead": r"\binstead\b",
    "thats_not": r"\bthat'?s not\b",
}
_CORR = {k: re.compile(v, re.I) for k, v in CORRECTION_PATTERNS.items()}


def mine_history(path: Path, since: str = "2026-03-01") -> dict:
    by_month: dict[str, Counter] = defaultdict(Counter)
    for d in iter_jsonl(path):
        ms = d.get("timestamp")
        try:
            day = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            continue
        if day < since:
            continue
        text = d.get("display") or ""
        c = by_month[day[:7]]
        if text.lstrip().startswith("/"):
            c["slash_commands"] += 1
            continue
        c["prompts"] += 1
        hits = [k for k, rx in _CORR.items() if rx.search(text)]
        if hits:
            c["matched"] += 1
            for k in hits:
                c[f"pattern_{k}"] += 1
    counts = nest()
    total = Counter()
    for mo, c in sorted(by_month.items()):
        counts["by_month"][mo] = {**{k: v for k, v in c.items() if k.startswith(("pattern_", "slash"))},
                                  "correction_rate": rate_block(c["matched"], c["prompts"], per=100)}
        total.update(c)
    counts["total"] = {**{k: v for k, v in total.items() if k.startswith(("pattern_", "slash"))},
                       "correction_rate": rate_block(total["matched"], total["prompts"], per=100)}
    return {"schema": AGG, "spec": f"DHM-1 operator-correction keyword pass over prompt history since {since}",
            "counts": plain(counts),
            "rules": [f"{k}: /{v}/i" for k, v in CORRECTION_PATTERNS.items()]
            + ["slash commands excluded from the denominator; a prompt counts once however many patterns hit",
               "keyword hits are a mechanical upper-bound proxy, not labelled corrections (labels: DHM-4)"]}


# ─── OAB-LB1: Codex AK-lane thread census (raw vault rollouts) ───────────────

AK_LANE_CWD_RE = re.compile(r"^/mnt/raid0/llm/(tmp/(ak-|aku)|autokernel/)")
_WALL_RE = re.compile(r"Wall time:?\s*([0-9.]+)\s*(?:s|sec|seconds)\b")
_CMD_JS_RE = re.compile(r'"cmd"\s*:\s*("(?:[^"\\]|\\.)*")')
_EXE_OK = re.compile(r"^[A-Za-z0-9_.+-]{1,32}$")
_WRAPPERS = {"nice", "timeout", "env", "sudo", "time", "nohup", "stdbuf", "ionice", "taskset", "numactl", "exec",
             "command"}
_SHELL_KEYWORDS = {"for", "while", "until", "if", "case", "do", "then", "{", "(", "[[", "function", "select"}
ERROR_CLASSES = (
    ("rate_limit", re.compile(r"rate.?limit|\b429\b|usage limit|quota", re.I)),
    ("context_window", re.compile(r"context (window|length)|too (long|many tokens)|maximum context", re.I)),
    ("stream_disconnect", re.compile(r"stream (disconnected|error|closed)|connection|reconnect|timed? ?out", re.I)),
    ("server_error", re.compile(r"\b5\d\d\b|internal server|overloaded|unavailable|bad gateway", re.I)),
    ("auth", re.compile(r"\b401\b|\b403\b|unauthori[sz]ed|forbidden|auth", re.I)),
    ("sandbox", re.compile(r"sandbox|permission denied|not permitted", re.I)),
)


def classify_error(msg: str) -> str:
    for name, rx in ERROR_CLASSES:
        if rx.search(msg or ""):
            return name
    return "other"


def executable_of(cmd: Any) -> str:
    """First real program of a shell command (wrappers, env assignments and ``cd X &&`` skipped)."""
    if isinstance(cmd, list):
        if len(cmd) >= 3 and Path(str(cmd[0])).name in ("bash", "sh", "zsh") and cmd[1] in ("-lc", "-c"):
            cmd = cmd[2]
        else:
            cmd = " ".join(str(c) for c in cmd)
    if not isinstance(cmd, str) or not cmd.strip():
        return "unknown"
    for seg in re.split(r"&&|\|\||;|\||\n", cmd):
        try:
            toks = shlex.split(seg, comments=True)
        except ValueError:
            toks = seg.split()
        i = 0
        while i < len(toks):
            t = toks[i]
            name = Path(t).name
            if "=" in t and not t.startswith(("-", "/", ".")) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
                i += 1
            elif name in _WRAPPERS or t.startswith("-") or re.match(r"^[0-9.]+[smhd]?$", t):
                i += 1
            elif name == "cd":
                break
            elif name in _SHELL_KEYWORDS:
                return "shell_compound"
            else:
                return name if _EXE_OK.match(name) else "other"
    return "unknown"


def _tool_command(p: dict) -> Any:
    pt = p.get("type")
    if pt == "custom_tool_call":
        m = _CMD_JS_RE.search(str(p.get("input") or ""))
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
        return None
    if pt == "function_call":
        try:
            a = json.loads(p.get("arguments") or "{}")
        except json.JSONDecodeError:
            return None
        if isinstance(a, dict):
            return a.get("cmd") or a.get("command")
    if pt == "local_shell_call":
        act = p.get("action") or {}
        return act.get("command") if isinstance(act, dict) else None
    return None


def _wall_seconds(output: Any) -> float | None:
    text = src._text_of(output) if not isinstance(output, str) else output
    m = _WALL_RE.search(text or "")
    if m:
        return float(m.group(1))
    try:
        j = json.loads(text)
        md = j.get("metadata") if isinstance(j, dict) else None
        if isinstance(md, dict) and md.get("duration_seconds") is not None:
            return float(md["duration_seconds"])
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def census_rollout(path: Path, seen_turns: set) -> dict | None:
    """One AK-lane thread's facts, or None if the rollout is not an AK-lane thread."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        try:
            first = json.loads(fh.readline())
        except json.JSONDecodeError:
            return None
        meta = first.get("payload") if isinstance(first, dict) else None
        if not isinstance(meta, dict) or not AK_LANE_CWD_RE.match(meta.get("cwd") or ""):
            return None
        t = {"started": 0, "completed": 0, "aborted": Counter(), "errors": Counter(), "turn_ms": [],
             "exec": defaultdict(list), "exec_fail": Counter(), "tool_calls": 0, "replayed_turns": 0,
             "exec_outputs": 0, "exec_no_wall": 0,
             "child": bool(meta.get("parent_thread_id") or meta.get("forked_from_id")
                           or isinstance(meta.get("source"), dict)),
             "month": (meta.get("timestamp") or "")[:7], "day": (meta.get("timestamp") or "")[:10] or None,
             "originator": meta.get("originator") or "unknown"}
        pending: dict[str, str] = {}
        replaying = False                        # inside a replayed parent turn: its tool calls are not ours
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
            pt = p.get("type")
            tid = p.get("turn_id")
            if d.get("type") == "event_msg":
                if pt in ("task_started", "task_complete", "turn_aborted") and tid:
                    k = (pt, tid)
                    if k in seen_turns:          # replayed parent history in a forked child
                        if pt == "task_started":
                            t["replayed_turns"] += 1
                            replaying = True
                        continue
                    seen_turns.add(k)
                    if pt == "task_started":
                        replaying = False
                if pt == "task_started":
                    t["started"] += 1
                elif pt == "task_complete":
                    t["completed"] += 1
                    try:
                        t["turn_ms"].append(float(p.get("duration_ms")))
                    except (TypeError, ValueError):
                        pass
                elif pt == "turn_aborted":
                    t["aborted"][p.get("reason") or "unknown"] += 1
                elif pt in ("error", "stream_error"):
                    t["errors"][f"{pt}:{classify_error(p.get('message') or '')}"] += 1
            elif d.get("type") == "response_item" and not replaying:
                if pt in ("custom_tool_call", "function_call", "local_shell_call"):
                    t["tool_calls"] += 1
                    cmd = _tool_command(p)
                    if cmd is not None and p.get("call_id"):
                        pending[p["call_id"]] = executable_of(cmd)
                elif pt in ("custom_tool_call_output", "function_call_output", "local_shell_call_output"):
                    exe = pending.pop(p.get("call_id"), None)
                    if exe is None:
                        continue
                    w = _wall_seconds(p.get("output"))
                    t["exec_outputs"] += 1
                    if w is not None:
                        t["exec"][exe].append(w)
                    else:
                        t["exec_no_wall"] += 1
                    text = src._text_of(p.get("output")) if not isinstance(p.get("output"), str) else p["output"]
                    m = src._CODEX_EXIT_RE.search(text or "")
                    if (m and m.group(1) != "0") or (text or "").lstrip().startswith("Script failed"):
                        t["exec_fail"][exe] += 1
    return t


def mine_oab(vault: Path, priv_out: Path, limit: int = 0) -> dict:
    files = []
    for tenant in ("epyc", "host", "twyne"):
        files += [(tenant, f) for f in sorted((vault / tenant / "codex").glob("**/rollout-*.jsonl"))]
    seen_turns: set = set()
    rows = []
    scanned = 0
    ak_bytes = 0
    for tenant, f in files:
        if limit and len(rows) >= limit:
            break
        scanned += 1
        t = census_rollout(f, seen_turns)
        if t is None:
            continue
        t["source"] = tenant
        rows.append(t)
        ak_bytes += f.stat().st_size
    dh_privacy.private_write(priv_out / "oab_lb1.threads.jsonl", "".join(json.dumps({
        "source": r["source"], "month": r["month"], "child": r["child"], "originator": r["originator"],
        "started": r["started"], "completed": r["completed"], "aborted": dict(r["aborted"]),
        "errors": dict(r["errors"]), "tool_calls": r["tool_calls"], "replayed_turns": r["replayed_turns"],
        "exec_s_total": {k: round(sum(v), 3) for k, v in r["exec"].items()}}) + "\n" for r in rows))
    counts = nest()
    for scope, rs in [("all", rows)] + [(s, [r for r in rows if r["source"] == s])
                                         for s in sorted({r["source"] for r in rows})]:
        g = counts["by_source"][scope]
        started = sum(r["started"] for r in rs)
        g["threads"] = len(rs)
        g["child_threads"] = sum(1 for r in rs if r["child"])
        g["turns_started"] = started
        g["turns_completed"] = sum(r["completed"] for r in rs)
        aborted = Counter()
        errors = Counter()
        for r in rs:
            aborted.update(r["aborted"])
            errors.update(r["errors"])
        failed = started - g["turns_completed"]
        g["turn_failure"]["not_completed"] = rate_block(max(failed, 0), started, per=100)
        for reason, k in sorted(aborted.items()):
            g["turn_failure"][f"aborted_{reason}"] = rate_block(k, started, per=100)
        g["turn_failure"]["no_terminal_event"] = rate_block(max(failed - sum(aborted.values()), 0), started, per=100)
        for cls, k in sorted(errors.items()):
            g["error_events"][cls] = k
        g["turn_wall_s"] = dist(ms / 1000 for r in rs for ms in r["turn_ms"])
        g["turn_wall_s_total"] = round(sum(sum(r["turn_ms"]) for r in rs) / 1000, 1)
        g["replayed_turns_excluded"] = sum(r["replayed_turns"] for r in rs)
        exe_vals: dict[str, list[float]] = defaultdict(list)
        exe_fail = Counter()
        for r in rs:
            for k, v in r["exec"].items():
                exe_vals[k].extend(v)
            exe_fail.update(r["exec_fail"])
        total_exec = sum(sum(v) for v in exe_vals.values())
        g["exec_wall_s_total"] = round(total_exec, 1)
        g["tool_calls"] = sum(r["tool_calls"] for r in rs)
        g["exec_outputs_matched"] = sum(r["exec_outputs"] for r in rs)
        g["exec_outputs_without_wall_time"] = sum(r["exec_no_wall"] for r in rs)
        top = sorted(exe_vals.items(), key=lambda kv: -sum(kv[1]))
        other: list[float] = []
        for i, (exe, v) in enumerate(top):
            if i >= 25:
                other.extend(v)
                continue
            e = g["exec_by_executable"][exe]
            e["calls"] = len(v)
            e["wall_s_total"] = round(sum(v), 2)
            e["wall_share"] = round(sum(v) / total_exec, 4) if total_exec else 0.0
            e["wall_s"] = dist(v)
            e["nonzero_exit"] = rate_block(exe_fail.get(exe, 0), len(v), per=100)
        if other:
            g["exec_by_executable"]["_rest"] = {"calls": len(other), "wall_s_total": round(sum(other), 2)}
    counts["frame"] = frame(r["day"] for r in rows)
    counts["scan"]["rollouts_scanned"] = scanned
    counts["scan"]["ak_lane_mib"] = round(ak_bytes / (1 << 20), 1)
    return {"schema": AGG, "spec": "OAB-LB1 Codex AK-lane thread census (turn failures, wall time by executable)",
            "counts": plain(counts),
            "rules": [
                f"AK-lane thread = rollout whose session_meta cwd matches /{AK_LANE_CWD_RE.pattern}/",
                "source of truth = the vault's rollout copies of the threads (the live ~/.codex state DB is never "
                "opened); a turn = task_started; failure = no task_complete (aborted by reason, or no terminal event)",
                "forked children replay parent turns: a (event, turn_id) pair is counted once corpus-wide, and tool "
                "calls inside a replayed turn are skipped",
                "executable = first program of the shell command after env assignments, wrappers and cd; names "
                "outside [A-Za-z0-9_.+-]{1,32} fold to 'other'; top 25 by wall time, the rest in _rest",
                "wall time = the exec output's own 'Wall time' (or metadata.duration_seconds); nonzero_exit from "
                "the reported exit code / 'Script failed'",
            ]}


# ─── UFH14-LB8: opencode step-level pass (read-only snapshots) ───────────────

NON_LOCAL_PROVIDERS = {"deepseek", "openai", "anthropic", "google", "github-copilot", "opencode", "openrouter",
                       "azure", "amazon-bedrock", "xai", "groq", "mistral", None, ""}
_TOOL_OK = re.compile(r"^[A-Za-z0-9_.:-]{1,48}$")


def _provider(model_json: str | None) -> str | None:
    try:
        m = json.loads(model_json) if model_json else None
    except json.JSONDecodeError:
        return None
    return m.get("providerID") if isinstance(m, dict) else None


def steps_of_session(conn, sid: str, parts_limit: int) -> dict:
    msgs = {}
    for mid, tc, data in conn.execute(
            "SELECT id, time_created, data FROM message WHERE session_id=? ORDER BY time_created, id LIMIT ?",
            (sid, parts_limit)):
        try:
            m = json.loads(data)
        except json.JSONDecodeError:
            continue
        msgs[mid] = (m.get("role"), m.get("providerID"), int(tc))
    user_times = sorted(tc for role, _p, tc in msgs.values() if role == "user")
    rows = conn.execute("SELECT message_id, time_created, data FROM part WHERE session_id=? "
                        "ORDER BY time_created, id LIMIT ?", (sid, parts_limit)).fetchall()
    steps, tools = [], []
    cur_start = None
    for mid, tc, data in rows:
        if '"step-' not in data and '"tool"' not in data:
            continue
        try:
            p = json.loads(data)
        except json.JSONDecodeError:
            continue
        typ = p.get("type")
        if typ == "step-start":
            cur_start = int(tc)
        elif typ == "step-finish":
            tok = p.get("tokens") if isinstance(p.get("tokens"), dict) else {}
            cache = tok.get("cache") if isinstance(tok.get("cache"), dict) else {}
            prov = (msgs.get(mid) or (None, None, 0))[1]
            steps.append({"start": cur_start, "end": int(tc), "provider": prov,
                          "input": int(tok.get("input") or 0), "read": int(cache.get("read") or 0),
                          "write": int(cache.get("write") or 0), "output": int(tok.get("output") or 0),
                          "reason": p.get("reason")})
            cur_start = None
        elif typ == "tool":
            st = p.get("state") if isinstance(p.get("state"), dict) else {}
            tm = st.get("time") if isinstance(st.get("time"), dict) else {}
            prov = (msgs.get(mid) or (None, None, 0))[1]
            if tm.get("start") and tm.get("end") and st.get("status") in ("completed", "error"):
                name = p.get("tool") or "unknown"
                tools.append({"tool": name if _TOOL_OK.match(name) else "other", "provider": prov,
                              "ms": int(tm["end"]) - int(tm["start"]), "status": st["status"]})
    # gaps + appends between consecutive local steps
    out_steps = []
    prev = None
    for s in steps:
        if s["provider"] in NON_LOCAL_PROVIDERS:
            prev = None
            continue
        prompt = s["input"] + s["read"] + s["write"]
        row = {"provider": s["provider"], "prompt": prompt, "read": s["read"], "first": prev is None,
               "gap_kind": None, "gap_ms": None, "append": None}
        if prev is not None and s["start"] is not None:
            i = bisect.bisect_right(user_times, prev["end"])
            human = i < len(user_times) and user_times[i] <= s["start"]
            row["gap_kind"] = "human" if human else "tool"
            row["gap_ms"] = s["start"] - prev["end"]
            row["append"] = prompt - (prev["prompt"] + prev["output"])
        out_steps.append(row)
        prev = {**s, "prompt": prompt}
    return {"steps": out_steps, "tools": [t for t in tools if t["provider"] not in NON_LOCAL_PROVIDERS],
            "truncated": len(rows) >= parts_limit}


def mine_opencode(dbs: dict[str, Path], priv_out: Path, max_sessions: int = 0, parts_limit: int = 20000) -> dict:
    per_session = []
    agg_steps: dict[tuple, list[dict]] = defaultdict(list)
    agg_tools: dict[tuple, list[dict]] = defaultdict(list)
    for source, db in dbs.items():
        if not Path(db).exists():
            continue
        conn = src.open_ro(db)
        sess = [(sid, _provider(m), ver, tc) for sid, m, ver, tc in conn.execute(
            "SELECT id, model, version, time_created FROM session ORDER BY time_created DESC")]
        local = [(sid, p, ver, tc) for sid, p, ver, tc in sess if p not in NON_LOCAL_PROVIDERS]
        if max_sessions:
            local = local[:max_sessions]
        for sid, prov, ver, tc in local:
            r = steps_of_session(conn, sid, parts_limit)
            agg_steps[(source, "all")].extend(r["steps"])
            agg_tools[(source, "all")].extend(r["tools"])
            for st in r["steps"]:
                agg_steps[(source, st["provider"])].append(st)
            for t in r["tools"]:
                agg_tools[(source, t["provider"])].append(t)
            pr = sum(s["prompt"] for s in r["steps"])
            per_session.append({"source": source, "session_key": sid, "provider": prov, "version": ver,
                                "day": src._ms_iso(tc)[:10] if src._ms_iso(tc) else None,
                                "steps": len(r["steps"]), "tools": len(r["tools"]), "truncated": r["truncated"],
                                "token_weighted_hit": round(sum(s["read"] for s in r["steps"]) / pr, 4) if pr else None})
        conn.close()
    dh_privacy.private_write(priv_out / "ufh14_lb8.sessions.jsonl", "".join(json.dumps(r) + "\n" for r in per_session))
    counts = nest()
    for (source, prov), steps in sorted(agg_steps.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        g = counts["by_source"][source][prov or "unknown"]
        g["sessions"] = sum(1 for r in per_session if r["source"] == source and (prov == "all" or r["provider"] == prov))
        g["steps"] = len(steps)
        pr = sum(s["prompt"] for s in steps)
        later = [s for s in steps if not s["first"]]
        prl = sum(s["prompt"] for s in later)
        g["prefix_hit"]["token_weighted"] = round(sum(s["read"] for s in steps) / pr, 4) if pr else 0.0
        g["prefix_hit"]["token_weighted_excl_first_step"] = round(sum(s["read"] for s in later) / prl, 4) if prl else 0.0
        g["prefix_hit"]["per_step"] = dist(s["read"] / s["prompt"] for s in steps if s["prompt"] > 0)
        g["prefix_hit"]["per_step_excl_first"] = dist(s["read"] / s["prompt"] for s in later if s["prompt"] > 0)
        for kind in ("human", "tool"):
            ks = [s for s in later if s["gap_kind"] == kind]
            g["gap_s"][kind] = dist(s["gap_ms"] / 1000 for s in ks if s["gap_ms"] is not None)
            ap = [s["append"] for s in ks if s["append"] is not None]
            g["append_tok"][kind] = {**dist(ap), "log2_hist": log2_hist(ap), "negative": sum(1 for a in ap if a < 0)}
        ap_all = [float(s["append"]) for s in later if s["append"] is not None and s["append"] > 0]
        g["append_tok"]["bimodality_coefficient_log2"] = bimodality_coefficient([math.log2(a) for a in ap_all])
        tools = agg_tools.get((source, prov), [])
        byt: dict[str, list[float]] = defaultdict(list)
        for t in tools:
            byt[t["tool"]].append(t["ms"] / 1000)
        for name, v in sorted(byt.items(), key=lambda kv: -len(kv[1]))[:20]:
            g["tool_duration_s"][name] = dist(v)
        g["truncated_sessions"] = sum(1 for r in per_session if r["source"] == source and r["truncated"])
        mine = [r for r in per_session if r["source"] == source and (prov == "all" or r["provider"] == prov)]
        g["frame"] = frame(r["day"] for r in mine)
        for v, k in sorted(Counter(r["version"] or "unknown" for r in mine).items()):
            g["opencode_versions"][v] = k
    return {"schema": AGG, "spec": "UFH14-LB8 opencode step-level prefix-cache / gap / append / tool-duration baseline",
            "counts": plain(counts),
            "rules": [
                "local provider = session providerID not in the hosted set " + ",".join(sorted(p for p in NON_LOCAL_PROVIDERS if p)),
                "step = one step-finish part (tokens input/cache.read/cache.write/output); prompt = input+read+write",
                "prefix hit = cache.read / prompt; excl_first drops each session's first local step (cold cache)",
                "gap = step-start of step k+1 minus step-finish of step k; human when a user message was created "
                "inside the gap, else tool",
                "append = prompt(k+1) - (prompt(k) + output(k)); negative = context shrank (compaction/truncation)",
                "bimodality coefficient over log2(append>0); > 0.555 suggests a bimodal append length",
                "read-only snapshots via dh_sources.open_ro; message/part tables only (indexed by session), "
                "LIMIT parts per session",
            ]}


# ─── driver ──────────────────────────────────────────────────────────────────

def provenance(proj: Path, run_id: str) -> str:
    try:
        pr = json.loads((proj / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pr = {}
    sem = pr.get("semconv") or {}
    return (f"mine_m1 run={run_id} code={code_commit() or 'unknown'} projection={pr.get('run_id', proj.name)} "
            f"projector_code={pr.get('code_commit') or 'unknown'} semconv={sem.get('commit', 'unknown')} "
            f"hash_scheme={pr.get('hash_scheme', 'unknown')}")


def code_commit() -> str | None:
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def write_aggregate(doc: dict, path: Path, source: str = "") -> Path:
    doc["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if source:
        doc["source"] = source
    errs = dh_privacy.validate_aggregate(doc)
    if errs:
        raise dh_privacy.PrivacyError(f"{path.name}: " + "; ".join(errs[:5]))
    return dh_privacy.private_write(path, json.dumps(doc, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--projection", required=True, help="projection run dir (sessions.jsonl + events/)")
    p.add_argument("--private-root", default=str(dh_privacy.PRIVATE_ROOT))
    p.add_argument("--belief-declarations", help="prospective declarations captured before mining")
    p.add_argument("--run-id", help="mining run id (default: the projection dir name)")
    p.add_argument("--tasks", default="dhm1,dhm5,oab,ufh",
                   help="comma list of dhm1,dhm5,oab,ufh,history (dhm1/dhm5 share one events pass)")
    p.add_argument("--vault", default=str(src.VAULT_ROOT))
    p.add_argument("--oab-limit", type=int, default=0, help="stop after N AK-lane threads (0 = all)")
    p.add_argument("--opencode-db", action="append", help="tag=path read-only snapshot (default: both)")
    p.add_argument("--ufh-max-sessions", type=int, default=0, help="local sessions per snapshot (0 = all)")
    p.add_argument("--ufh-parts-limit", type=int, default=20000, help="LIMIT on parts/messages per session")
    p.add_argument("--history", help="Claude Code prompt history JSONL for the DHM-1 correction keyword pass")
    p.add_argument("--history-since", default="2026-03-01")
    p.add_argument("--claude-md", default=str(Path(__file__).resolve().parents[2] / "CLAUDE.md"))
    p.add_argument("--agents-md", default=str(Path(__file__).resolve().parents[2] / "AGENTS.md"))
    p.add_argument("--memory-md", default=os.path.expanduser("~/.claude/projects/-workspace/memory/MEMORY.md"))
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if os.environ.get("DEV_HARNESS_ALLOW_NOT_NICE") != "1" and os.nice(0) < 10:
        os.nice(19 - os.nice(0))
    t0 = time.time()
    proj = Path(a.projection)
    run_id = a.run_id or proj.name
    out = dh_privacy.private_dir(Path(a.private_root) / "mining" / run_id / "m1")   # m1/: other waves share <run_id>
    aggdir = dh_privacy.private_dir(out / "aggregates")
    tasks = {t.strip() for t in a.tasks.split(",") if t.strip()}
    prov = provenance(proj, run_id)
    timings = {}
    written = []
    custody = None
    if a.belief_declarations:
        import belief_run_custody as custody
        run_dir = out.parent
        targets = [aggdir / (name + ".aggregate.json") for name in ("dhm1", "dhm5", "dhm1_history", "oab_lb1", "ufh14_lb8")] + [out / "run.json"]
        start = custody.begin(run_dir, "m1", run_id, a.belief_declarations, __file__, targets)
    if tasks & {"dhm1", "dhm5"}:
        t = time.time()
        res = mine_projection(proj, out, {"CLAUDE.md": Path(a.claude_md), "AGENTS.md": Path(a.agents_md),
                                          "MEMORY.md": Path(a.memory_md)})
        for k in ("dhm1", "dhm5"):
            if k in tasks:
                written.append(write_aggregate(res[k], aggdir / f"{k}.aggregate.json", prov))
        timings["dhm1_dhm5_s"] = round(time.time() - t, 2)
    if "history" in tasks and a.history:
        t = time.time()
        written.append(write_aggregate(mine_history(Path(a.history), a.history_since),
                                       aggdir / "dhm1_history.aggregate.json", prov))
        timings["history_s"] = round(time.time() - t, 2)
    if "oab" in tasks:
        t = time.time()
        written.append(write_aggregate(mine_oab(Path(a.vault), out, a.oab_limit), aggdir / "oab_lb1.aggregate.json", prov))
        timings["oab_s"] = round(time.time() - t, 2)
    if "ufh" in tasks:
        t = time.time()
        dbs = dict(x.split("=", 1) for x in a.opencode_db) if a.opencode_db else dict(src.OPENCODE_RO_DBS)
        written.append(write_aggregate(mine_opencode({k: Path(v) for k, v in dbs.items()}, out,
                                                     a.ufh_max_sessions, a.ufh_parts_limit),
                                       aggdir / "ufh14_lb8.aggregate.json", prov))
        timings["ufh_s"] = round(time.time() - t, 2)
    manifest = {"schema": "dev-harness-mining-run.v1", "run_id": run_id, "projection": str(proj),
                "tasks": sorted(tasks), "args": {k: v for k, v in vars(a).items() if k != "history"},
                "history_used": bool(a.history), "timings": timings, "elapsed_s": round(time.time() - t0, 2),
                "aggregates": [str(p) for p in written]}
    try:
        import resource
        manifest["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except ImportError:
        pass
    dh_privacy.private_write(out / "run.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if custody:
        custody.finish(run_dir, "m1", start, __file__, [*written, out / "run.json"])
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
