#!/usr/bin/env python3
"""DHM-5.1: the per-harness always-on prefix measured from turn-1 usage fields.

DHM-5 (``mine_m1.aggregate_dhm5``) priced the always-on files as TODAY's file size divided by a
pooled chars/token figure, so Claude subagents, Codex and opencode all got the same 8,326 tokens.
This driver measures instead. For every transcript unit it takes the FIRST model call's prompt
total from the usage fields (input INCLUSIVE of cache read and cache creation) and, from the same
transcript, the character count of everything the harness sent before that call, split by class:

  always_on  the instruction files the harness injects on its own
             * claude_code: the ``instructions`` attachment (CLAUDE.md files + the MEMORY.md index),
               as rendered into the first user message; logged by Claude Code >= the first
               version seen to log it (older units are excluded, not zero-filled)
             * codex: the ``# AGENTS.md instructions for <dir>`` user content item
             * opencode: not logged; AGENTS.md/CLAUDE.md/CONTEXT.md found upward from the session
               directory to its git root, sized AT THE SESSION DATE from git history when the file
               is tracked (current size otherwise; unresolvable directories are excluded)
  reminder   other harness-injected context (skill/agent/deferred-tool listings, environment,
             git status, developer messages, meta user lines)
  system     codex only: the logged ``base_instructions`` text
  user       the operator's / parent's own first message text
  history    anything older carried into turn 1 (resumed, forked or compacted history, tool output)

and fits, per harness x role, ``prompt_tokens = intercept[model] + sum_c beta_c * chars_c`` by OLS.
``beta_always_on`` is the measured marginal tokens per always-on character; the always-on prefix in
tokens is ``beta_always_on * chars``; the intercept is the system-prompt + tool-schema baseline
(for codex plus ``beta_system * system chars``). Units with the files absent (always_on = 0 under a
version that logs them) are the natural control that anchors the intercept; variation in file size
across directories and over time (CLAUDE.md edits, MEMORY.md growth) identifies the slope.
Bootstrap (rows resampled, fixed seed) gives 95% intervals. Claude also reports the turn-1
cache-read p50 (the warm, cross-session system + tools prefix) as a direct baseline cross-check.

Reads the cloud-llm-vault JSONL and the read-only opencode snapshots (never a live store); writes
per-unit rows ONLY under ``<private-root>/mining/<run>/dhm51/`` and an aggregate
(dev-harness-aggregate.v1, numbers and rule text only) validated by ``dh_privacy``. Zero inference.

    nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_dhm51.py --run dhm51-20261024
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
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
CLASSES = ("always_on", "reminder", "system", "user", "history")
MIN_MODEL_ROWS = 15            # a model gets its own intercept with at least this many rows
BOOT = 400
SEED = 20261024
OPENCODE_RULE_FILES = ("AGENTS.md", "CLAUDE.md", "CONTEXT.md")   # opencode's local rule names, in order


# ─── small helpers ───────────────────────────────────────────────────────────

def _len(x: Any) -> int:
    if isinstance(x, str):
        return len(x)
    if isinstance(x, (dict, list)):
        return len(json.dumps(x, ensure_ascii=False))
    return 0


def _records(lines: Iterable[str]) -> Iterator[dict]:
    for line in lines:
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict):
            yield d


def version_key(v: str | None) -> tuple:
    out = []
    for p in (v or "").split("."):
        num = "".join(ch for ch in p if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)


def version_num(vk: tuple | None) -> int:
    """(2, 1, 199) -> 2001199: a version as a number (aggregate leaves must be numbers)."""
    if not vk:
        return 0
    a, b, c = (tuple(vk) + (0, 0, 0))[:3]
    return a * 1_000_000 + b * 1_000 + c


def quantile(vals: list[float], q: float) -> float:
    v = sorted(vals)
    if not v:
        return 0.0
    pos = q * (len(v) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


# ─── Claude Code ─────────────────────────────────────────────────────────────

def _rendered_chars(rec: dict) -> int:
    r = rec.get("rendered")
    if isinstance(r, list):
        return sum(_len(x.get("content")) for x in r if isinstance(x, dict))
    return 0


def claude_turn1(records: Iterable[dict]) -> dict | None:
    """Turn-1 usage and the chars sent before it, by class, from one Claude Code JSONL."""
    chars = Counter()
    files = Counter()
    instr_logged = False
    version = None
    cwd = None
    sidechain = False
    for d in records:
        version = version or d.get("version")
        cwd = cwd or d.get("cwd")
        sidechain = sidechain or bool(d.get("isSidechain"))
        t = d.get("type")
        if t == "attachment":
            a = d.get("attachment") if isinstance(d.get("attachment"), dict) else {}
            n = _rendered_chars(d)
            if a.get("type") == "instructions":
                instr_logged = True
                fl = a.get("files") if isinstance(a.get("files"), list) else []
                for f in fl:
                    if isinstance(f, dict):
                        kind = "memory_index" if str(f.get("path") or "").endswith("MEMORY.md") else "claude_md"
                        files[kind] += _len(f.get("content"))
                chars["always_on"] += n or sum(files.values())
            else:
                chars["reminder"] += n
        elif t == "user":
            m = d.get("message") if isinstance(d.get("message"), dict) else {}
            c = m.get("content")
            cls = "history" if d.get("isCompactSummary") else ("reminder" if d.get("isMeta") else "user")
            if isinstance(c, str):
                chars[cls] += len(c)
            elif isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_result":
                        chars["history"] += _len(b.get("content"))
                    elif b.get("type") == "text":
                        chars[cls] += _len(b.get("text"))
        elif t == "assistant":
            m = d.get("message") if isinstance(d.get("message"), dict) else {}
            u = m.get("usage")
            if not isinstance(u, dict) or m.get("model") == "<synthetic>" or d.get("isApiErrorMessage"):
                for b in m.get("content") or []:
                    if isinstance(b, dict):
                        chars["history"] += _len(b.get("text") or b.get("input") or b.get("thinking"))
                continue
            inp = int(u.get("input_tokens") or 0)
            cc = int(u.get("cache_creation_input_tokens") or 0)
            cr = int(u.get("cache_read_input_tokens") or 0)
            return {"harness": "claude_code", "role": "subagent" if sidechain else "main",
                    "model": m.get("model") or "unknown", "version": version, "cwd": cwd,
                    "ts": d.get("timestamp"), "prompt_tok": inp + cc + cr, "cache_read_tok": cr,
                    "cache_creation_tok": cc, "uncached_tok": inp, "instr_logged": instr_logged,
                    "chars": {k: chars.get(k, 0) for k in CLASSES},
                    "file_chars": {k: files.get(k, 0) for k in ("claude_md", "memory_index")}}
    return None


# ─── Codex ───────────────────────────────────────────────────────────────────

def _codex_item_chars(p: dict) -> int:
    n = 0
    for k in ("arguments", "output", "input", "summary", "content", "text"):
        if k in p and k != "content":
            n += _len(p.get(k))
    c = p.get("content")
    if isinstance(c, list):
        n += sum(_len(b.get("text")) for b in c if isinstance(b, dict))
    elif isinstance(c, str):
        n += len(c)
    return n


def codex_turn1(records: Iterable[dict]) -> dict | None:
    chars = Counter()
    pending_output = 0
    role = "main"
    version = model = cwd = ts = None
    for d in records:
        t = d.get("type")
        p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        if t == "session_meta":
            version = p.get("cli_version")
            cwd = p.get("cwd")
            ts = p.get("timestamp") or d.get("timestamp")
            bi = p.get("base_instructions")
            chars["system"] += _len(bi.get("text")) if isinstance(bi, dict) else _len(bi)
            s = p.get("source")
            if p.get("parent_thread_id") or p.get("forked_from_id") or (isinstance(s, dict) and s.get("subagent")):
                role = "subagent"
        elif t == "turn_context":
            model = model or p.get("model")
        elif t == "compacted":
            chars["history"] += _len(p.get("message")) + _len(p.get("replacement_history"))
        elif t == "response_item":
            pt = p.get("type")
            if pt == "message" and p.get("role") in ("user", "developer"):
                # model output seen before a later input message was earlier history (fork replay, resume)
                chars["history"] += pending_output
                pending_output = 0
                for b in p.get("content") or []:
                    if not isinstance(b, dict):
                        continue
                    txt = b.get("text") if isinstance(b.get("text"), str) else ""
                    if p.get("role") == "developer":
                        chars["reminder"] += len(txt)
                    elif txt.startswith("# AGENTS.md instructions"):
                        chars["always_on"] += len(txt)
                    elif txt.startswith("<") and not txt.startswith("<turn_aborted>"):
                        chars["reminder"] += len(txt)
                    else:
                        chars["user"] += len(txt)
            else:
                # the first call's own output (reasoning, message, function_call) is logged before its
                # token_count: hold it until an input message proves it was replayed history
                pending_output += _codex_item_chars(p)
        elif t == "event_msg" and p.get("type") == "token_count":
            info = p.get("info") if isinstance(p.get("info"), dict) else None
            last = (info or {}).get("last_token_usage")
            if not isinstance(last, dict) or not last.get("input_tokens"):
                continue
            return {"harness": "codex", "role": role, "model": model or "unknown", "version": version,
                    "cwd": cwd, "ts": ts or d.get("timestamp"), "prompt_tok": int(last.get("input_tokens") or 0),
                    "cache_read_tok": int(last.get("cached_input_tokens") or 0), "cache_creation_tok": 0,
                    "uncached_tok": int(last.get("input_tokens") or 0) - int(last.get("cached_input_tokens") or 0),
                    "instr_logged": True, "chars": {k: chars.get(k, 0) for k in CLASSES}, "file_chars": {}}
    return None


# ─── opencode ────────────────────────────────────────────────────────────────

class RuleFileSizer:
    """Chars of opencode's local rule files for a directory at a date (git history when tracked)."""

    def __init__(self) -> None:
        self._cache: dict[tuple, int | None] = {}

    @staticmethod
    def _git_root(d: Path) -> Path | None:
        for p in (d, *d.parents):
            if (p / ".git").exists():
                return p
        return None

    def _git_chars(self, repo: Path, rel: str, ts: str | None) -> int | None:
        key = ("git", str(repo), rel, (ts or "")[:10])
        if key in self._cache:
            return self._cache[key]
        val = None
        try:
            if ts:
                rev = subprocess.run(["git", "-C", str(repo), "rev-list", "-1", f"--before={ts}", "HEAD", "--", rel],
                                     capture_output=True, text=True, timeout=30, check=False).stdout.strip()
                if rev:
                    out = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{rel}"], capture_output=True,
                                         timeout=30, check=False)
                    if out.returncode == 0:
                        val = len(out.stdout.decode("utf-8", errors="replace"))
        except (OSError, subprocess.SubprocessError):
            val = None
        self._cache[key] = val
        return val

    def chars(self, directory: str | None, ts: str | None) -> tuple[int | None, str]:
        """(chars, how) — how is git|current|absent|unresolved."""
        if not directory:
            return None, "unresolved"
        d = Path(directory)
        if not d.is_dir():
            return None, "unresolved"
        root = self._git_root(d) or Path(d.anchor)
        for name in OPENCODE_RULE_FILES:
            hits = []
            for p in (d, *d.parents):
                if (p / name).is_file():
                    hits.append(p / name)
                if p == root:
                    break
            if not hits:
                continue
            total, how = 0, "git"
            for h in hits:
                real = h.resolve()
                repo = self._git_root(real.parent)
                g = self._git_chars(repo, str(real.relative_to(repo)), ts) if repo else None
                if g is None:
                    how = "current"
                    try:
                        g = len(real.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        g = 0
                total += g
            return total, how
        return 0, "absent"


def opencode_turn1(conn, sid: str, directory: str | None, parent: str | None, sizer: RuleFileSizer) -> dict | None:
    msgs = conn.execute("SELECT id, time_created, data FROM message WHERE session_id=? ORDER BY time_created, id",
                        (sid,)).fetchall()
    chars = Counter()
    agent = None
    for mid, tc, data in msgs:
        try:
            m = json.loads(data)
        except json.JSONDecodeError:
            continue
        if m.get("role") == "user":
            agent = agent or m.get("agent")
            for (pdata,) in conn.execute("SELECT data FROM part WHERE message_id=? ORDER BY time_created, id", (mid,)):
                try:
                    p = json.loads(pdata)
                except json.JSONDecodeError:
                    continue
                if p.get("type") == "text":
                    chars["reminder" if p.get("synthetic") else "user"] += _len(p.get("text"))
            continue
        tok = m.get("tokens") if isinstance(m.get("tokens"), dict) else None
        if not tok:
            continue
        cache = tok.get("cache") if isinstance(tok.get("cache"), dict) else {}
        inp, cr, cw = int(tok.get("input") or 0), int(cache.get("read") or 0), int(cache.get("write") or 0)
        if inp + cr + cw <= 0:
            continue
        ts = src._ms_iso(tc)
        ao, how = sizer.chars(directory, ts)
        c = {k: chars.get(k, 0) for k in CLASSES}
        c["always_on"] = ao if ao is not None else 0
        return {"harness": "opencode", "role": "subagent" if parent else "main",
                "model": m.get("modelID") or "unknown", "version": None, "agent_type": agent or m.get("agent") or "unknown", "cwd": directory, "ts": ts,
                "prompt_tok": inp + cr + cw, "cache_read_tok": cr, "cache_creation_tok": cw, "uncached_tok": inp,
                "instr_logged": ao is not None, "rule_file_sizing": how, "chars": c, "file_chars": {}}
    return None


# ─── discovery ───────────────────────────────────────────────────────────────

def _claude_agent_type(meta: Path) -> str:
    """The subagent type from Claude Code's sidecar (its system prompt differs per type)."""
    try:
        d = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return str(d.get("agentType") or "unknown") if isinstance(d, dict) else "unknown"


def iter_claude(vault: Path) -> Iterator[dict]:
    for tenant in src.VAULT_TENANTS:
        for f in sorted((vault / tenant / "claude").rglob("*.jsonl")):
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fh:
                    r = claude_turn1(_records(fh))
            except OSError:
                continue
            if r:
                r["source"] = tenant
                if "/subagents/" in str(f):
                    r["role"] = "subagent"
                    r["agent_type"] = _claude_agent_type(f.with_suffix(".meta.json"))
                yield r


def iter_codex(vault: Path) -> Iterator[dict]:
    for tenant in src.VAULT_TENANTS:
        for f in sorted((vault / tenant / "codex").rglob("*.jsonl")):
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fh:
                    r = codex_turn1(_records(fh))
            except OSError:
                continue
            if r:
                r["source"] = tenant
                yield r


def iter_opencode(dbs: Iterable[Path]) -> Iterator[dict]:
    sizer = RuleFileSizer()
    for db in dbs:
        conn = src.open_ro(db)
        source = src.opencode_source_for(db)
        try:
            for sid, parent, directory in conn.execute("SELECT id, parent_id, directory FROM session").fetchall():
                r = opencode_turn1(conn, sid, directory, parent, sizer)
                if r:
                    r["source"] = source
                    yield r
        finally:
            conn.close()


# ─── fitting ─────────────────────────────────────────────────────────────────

FE_SPECS = ("model", "model_version", "model_cwd")
# intercept buckets: model_version also absorbs harness-version drift; model_cwd absorbs per-directory
# config (tool sets, MCP servers, agents), so its slope comes only from a directory's files changing over time


def fe_key(r: dict, spec: str) -> str:
    parts = [r.get("model") or "unknown"]
    if r.get("agent_type"):
        parts.append(r["agent_type"])
    if spec == "model_version":
        parts.append(r.get("version") or "unknown")
    if spec == "model_cwd":
        parts.append(r.get("cwd") or "unknown")
    return "|".join(parts)


def _ci(draws, est: float, nd: int = 1) -> dict:
    import numpy as np
    return {"est": round(float(est), nd), "ci95_lo": round(float(np.percentile(draws, 2.5)), nd),
            "ci95_hi": round(float(np.percentile(draws, 97.5)), nd)}


def fit_group(rows: list[dict], spec: str = "model", boot: int = BOOT, seed: int = SEED) -> dict:
    """OLS of turn-1 prompt tokens on per-class chars with one intercept per ``fe_key`` bucket.

    Buckets with fewer than MIN_MODEL_ROWS rows are dropped (never pooled: pooling mixes system
    prompts). Rows are resampled ``boot`` times for 95% percentile intervals.
    """
    import numpy as np
    bc = Counter(fe_key(r, spec) for r in rows)
    keep = sorted(k for k, n in bc.items() if n >= MIN_MODEL_ROWS)
    rows = [r for r in rows if fe_key(r, spec) in keep]
    out: dict[str, Any] = {"n": len(rows), "buckets": len(keep), "rows_dropped_small_bucket": sum(bc.values()) - len(rows)}
    covs = [c for c in CLASSES if len({r["chars"][c] for r in rows}) > 1]
    if "always_on" not in covs or len(rows) < len(keep) + len(covs) + 5:
        out["identified"] = 0
        return out
    X = np.zeros((len(rows), len(keep) + len(covs)))
    for i, r in enumerate(rows):
        X[i, keep.index(fe_key(r, spec))] = 1.0
        for j, c in enumerate(covs):
            X[i, len(keep) + j] = r["chars"][c]
    y = np.array([float(r["prompt_tok"]) for r in rows])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_tot = float(((y - y.mean()) ** 2).sum())
    out["r2"] = round(1 - float((resid ** 2).sum()) / ss_tot, 4) if ss_tot else 0.0
    out["resid_mad_tok"] = round(float(np.median(np.abs(resid - np.median(resid)))), 1)
    rng = random.Random(seed)
    n = len(rows)
    D = np.array([np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]
                  for idx in ([rng.randrange(n) for _ in range(n)] for _ in range(boot))])
    for j, c in enumerate(covs):
        out[f"beta_{c}_tok_per_char"] = _ci(D[:, len(keep) + j], beta[len(keep) + j], 5)
    ja = len(keep) + covs.index("always_on")
    ao = [r["chars"]["always_on"] for r in rows if r["chars"]["always_on"] > 0]
    ao_p50 = quantile(ao, 0.5)
    out["always_on_chars_p50"] = round(ao_p50, 1)
    out["always_on_present_rows"] = len(ao)
    out["always_on_absent_rows"] = n - len(ao)
    # absent rows that share a bucket with present rows: the in-bucket control that anchors the intercept
    present_b = {fe_key(r, spec) for r in rows if r["chars"]["always_on"] > 0}
    out["always_on_absent_rows_in_shared_bucket"] = sum(1 for r in rows if r["chars"]["always_on"] == 0
                                                        and fe_key(r, spec) in present_b)
    # buckets with within-bucket always-on variation: what identifies the slope once intercepts are in
    var_b = defaultdict(set)
    for r in rows:
        var_b[fe_key(r, spec)].add(r["chars"]["always_on"])
    out["buckets_with_always_on_variation"] = sum(1 for v in var_b.values() if len(v) > 1)
    out["always_on_tok_p50"] = _ci(D[:, ja] * ao_p50, beta[ja] * ao_p50)
    ao_p90 = quantile(ao, 0.9)
    out["always_on_chars_p90"] = round(ao_p90, 1)
    out["always_on_tok_p90"] = _ci(D[:, ja] * ao_p90, beta[ja] * ao_p90)
    lo, hi = out["always_on_tok_p50"]["ci95_lo"], out["always_on_tok_p50"]["ci95_hi"]
    out["identified"] = int(lo > 0 and out["buckets_with_always_on_variation"] > 0)
    dom = max(keep, key=lambda k: bc[k])
    jd = keep.index(dom)
    base, base_est = D[:, jd].copy(), float(beta[jd])
    if "system" in covs:
        js = len(keep) + covs.index("system")
        sp50 = quantile([r["chars"]["system"] for r in rows if fe_key(r, spec) == dom], 0.5)
        base, base_est = base + D[:, js] * sp50, base_est + float(beta[js]) * sp50
    out["baseline_system_tools_tok"] = {**_ci(base, base_est), "bucket_rows": bc[dom]}
    if "reminder" in covs:
        jr = len(keep) + covs.index("reminder")
        rp50 = quantile([r["chars"]["reminder"] for r in rows], 0.5)
        out["harness_reminders_tok_p50"] = _ci(D[:, jr] * rp50, beta[jr] * rp50)
    out["_dominant_bucket"] = dom          # stripped before publishing (it names a model/version)
    return out


def fit_cache_split(rows: list[dict], boot: int = BOOT, seed: int = SEED) -> dict:
    """Claude only: subtract the turn-1 cache read (the warm cross-session system + tools prefix).

    A fresh Claude Code unit whose first call reads the cache reads exactly the prefix up to the
    system-prompt breakpoint when that prefix was written by an earlier unit of the same model,
    version and subagent type; the instruction files sit after it, in the first user message. Rows
    whose cache read equals their bucket's modal value (>= 3 hits) are kept; ``prompt_tok -
    cache_read`` is regressed on the per-class chars with one common intercept. No per-bucket
    baseline is estimated, so this is independent of the intercept-based fits.
    """
    import numpy as np
    def bk(r: dict) -> tuple:
        return (r.get("model"), r.get("version"), r.get("agent_type"))
    cand = [r for r in rows if r["cache_read_tok"] > 0 and r["chars"]["history"] == 0 and r["chars"]["always_on"] > 0]
    modal: dict[tuple, tuple[int, int]] = {}
    for k in {bk(r) for r in cand}:
        modal[k] = Counter(r["cache_read_tok"] for r in cand if bk(r) == k).most_common(1)[0]
    sel = [r for r in cand if modal[bk(r)][1] >= 3 and r["cache_read_tok"] == modal[bk(r)][0]]
    out: dict[str, Any] = {"n": len(sel), "candidates": len(cand)}
    covs = [c for c in ("always_on", "reminder", "user") if len({r["chars"][c] for r in sel}) > 1]
    if "always_on" not in covs or len(sel) < len(covs) + 10:
        out["identified"] = 0
        return out
    X = np.array([[1.0] + [float(r["chars"][c]) for c in covs] for r in sel])
    y = np.array([float(r["prompt_tok"] - r["cache_read_tok"]) for r in sel])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    rng = random.Random(seed)
    n = len(sel)
    D = np.array([np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]
                  for idx in ([rng.randrange(n) for _ in range(n)] for _ in range(boot))])
    ja = 1 + covs.index("always_on")
    ao_p50 = quantile([r["chars"]["always_on"] for r in sel], 0.5)
    out["intercept_tok"] = _ci(D[:, 0], beta[0])
    out["beta_always_on_tok_per_char"] = _ci(D[:, ja], beta[ja], 5)
    out["always_on_chars_p50"] = round(ao_p50, 1)
    out["always_on_tok_p50"] = _ci(D[:, ja] * ao_p50, beta[ja] * ao_p50)
    out["warm_prefix_cache_read_tok_p50"] = round(quantile([r["cache_read_tok"] for r in sel], 0.5), 1)
    out["identified"] = int(out["always_on_tok_p50"]["ci95_lo"] > 0)
    return out


def choose_primary(g: dict) -> dict:
    """model_version when identified (removes harness-version drift), else model; flag cwd robustness."""
    for spec in ("model_version", "model"):
        f = g.get(f"fit_by_{spec}", {})
        if f.get("identified"):
            cwd = g.get("fit_by_model_cwd", {})
            p, c = f["always_on_tok_p50"], cwd.get("always_on_tok_p50")
            overlap = bool(c and cwd.get("identified") and c["ci95_lo"] <= p["ci95_hi"] and p["ci95_lo"] <= c["ci95_hi"])
            return {"spec_model_version": int(spec == "model_version"), "spec_model": int(spec == "model"),
                    "always_on_tok_p50": p, "always_on_chars_p50": f["always_on_chars_p50"],
                    "beta_always_on_tok_per_char": f["beta_always_on_tok_per_char"],
                    "baseline_system_tools_tok": f["baseline_system_tools_tok"], "n": f["n"],
                    "robust_to_cwd_buckets": int(overlap), "measured": int(overlap), "identified": 1}
    return {"identified": 0, "measured": 0}


def aggregate(rows: list[dict], dhm5_file_estimate: dict[str, float] | None = None) -> dict:
    counts: dict[str, Any] = {"by_harness": {}}
    notes: list[str] = []
    groups: dict[tuple, list[dict]] = defaultdict(list)
    excluded = Counter()
    for r in rows:
        if r["prompt_tok"] <= 0:
            excluded[(r["harness"], "zero_prompt")] += 1
            continue
        groups[(r["harness"], r["role"])].append(r)
    for (h, role), rs in sorted(groups.items()):
        g: dict[str, Any] = {"units_with_turn1_usage": len(rs)}
        g["turn1_prompt_tok"] = {f"p{int(q * 100)}": round(quantile([r["prompt_tok"] for r in rs], q), 1)
                                 for q in (0.1, 0.5, 0.9)}
        crs = [r["cache_read_tok"] for r in rs if r["cache_read_tok"] > 0]
        g["turn1_cache_read_tok_p50"] = round(quantile(crs, 0.5), 1)
        g["turn1_cache_read_share_of_units"] = round(len(crs) / len(rs), 4)
        usable = [r for r in rs if r["instr_logged"]]
        if h == "claude_code":
            logged = [version_key(r["version"]) for r in rs if r["chars"]["always_on"] > 0 and r["version"]]
            vmin = min(logged) if logged else None
            usable = [r for r in rs if r["chars"]["always_on"] > 0 or (vmin and version_key(r["version"]) >= vmin)]
            g["first_logging_version_num"] = version_num(vmin)
            fc = [r for r in usable if r["chars"]["always_on"] > 0]
            g["claude_md_chars_p50"] = round(quantile([r["file_chars"]["claude_md"] for r in fc], 0.5), 1)
            g["memory_index_chars_p50"] = round(quantile([r["file_chars"]["memory_index"] for r in fc], 0.5), 1)
            g["memory_index_present_share"] = (round(sum(1 for r in fc if r["file_chars"]["memory_index"] > 0)
                                                     / len(fc), 4) if fc else 0.0)
        if h == "opencode":
            g["rule_file_sizing"] = dict(Counter(r.get("rule_file_sizing", "unresolved") for r in rs))
        g["units_excluded_unlogged_or_unresolved"] = len(rs) - len(usable)
        fresh = [r for r in usable if r["chars"]["history"] == 0]
        g["units_excluded_history_before_turn1"] = len(usable) - len(fresh)
        g["units_used_in_fit"] = len(fresh)
        for spec in FE_SPECS:
            fit = fit_group(fresh, spec)
            dom = fit.pop("_dominant_bucket", None)
            if dom and spec != "model_cwd":       # cwd buckets name directories: never published
                notes.append(f"{h}/{role}/{spec}: baseline bucket = {dom}")
            g[f"fit_by_{spec}"] = fit
        if h == "claude_code":
            g["fit_cache_split"] = fit_cache_split(fresh)
        g["primary"] = choose_primary(g)
        key = f"{h}|{role}"
        if dhm5_file_estimate and key in dhm5_file_estimate:
            g["dhm5_file_size_estimate_tok"] = dhm5_file_estimate[key]
        counts["by_harness"].setdefault(h, {})[role] = g
    counts["excluded"] = {f"{h}__{why}": n for (h, why), n in sorted(excluded.items())}
    return {"schema": AGG, "spec": "DHM-5.1 always-on prefix per harness x role from turn-1 usage fields",
            "counts": counts, "notes": "; ".join(notes),
            "rules": [
                "prompt_tok = the unit's FIRST model call: input INCLUSIVE of cache read and cache creation "
                "(claude input+cache_creation+cache_read; codex last_token_usage.input_tokens; opencode input+cache.read+cache.write)",
                "chars before that call are split always_on / reminder / system / user / history from the transcript itself",
                "claude always_on = the logged instructions attachment (CLAUDE.md files + MEMORY.md index, as rendered); "
                "units older than the first version that logs it are excluded, never zero-filled",
                "codex always_on = the '# AGENTS.md instructions' user content item; system = logged base_instructions",
                "opencode always_on = AGENTS.md|CLAUDE.md|CONTEXT.md found upward to the git root (opencode's order), "
                "sized at the session date from git history when tracked, else current size; unresolvable dirs excluded",
                "units with any history before turn 1 (resumed, forked, compacted) are excluded from the fit",
                "fit per harness x role: prompt_tok = intercept[bucket] + sum beta_class * chars_class (OLS); bucket = "
                "model (+ claude subagent type) [fit_by_model], + harness version [fit_by_model_version], or + working directory "
                "[fit_by_model_cwd]; "
                f"buckets < {MIN_MODEL_ROWS} rows dropped; {BOOT} row-bootstrap draws, seed {SEED}, 95% percentile CI",
                "always_on_tok_p50 = beta_always_on * the p50 always-on chars among units carrying the files; "
                "identified = its CI excludes 0 and at least one bucket has within-bucket always-on variation",
                "baseline_system_tools_tok = intercept of the largest bucket (codex: + beta_system * its p50 system chars) "
                "= system prompt + tool schemas; turn1_cache_read_tok_p50 is the warm cross-session prefix, a direct check",
                "claude fit_cache_split: prompt_tok - turn-1 cache_read regressed on chars (common intercept), rows whose "
                "cache read equals their model+version+subagent-type modal value (>= 3 hits): no baseline is estimated",
                "primary = fit_by_model_version when identified, else fit_by_model; robust_to_cwd_buckets = the "
                "fit_by_model_cwd estimate is identified and its CI overlaps the primary's; measured = identified and "
                "robust_to_cwd_buckets (otherwise the slope may be per-directory configuration, not the files)",
                "weakest assumption: always-on size is uncorrelated with unlogged prompt parts (tool schemas, MCP servers, "
                "per-directory config) within a bucket; the model_version spec removes harness-version drift but not cwd config",
            ]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default="dhm51-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ"))
    ap.add_argument("--vault", type=Path, default=src.VAULT_ROOT)
    ap.add_argument("--opencode-db", type=Path, action="append", default=None)
    ap.add_argument("--harness", default="claude_code,codex,opencode")
    ap.add_argument("--rows", type=Path, default=None, help="reuse a previous private rows file (skip extraction)")
    ap.add_argument("--dhm5-aggregate", type=Path, default=None,
                    help="committed DHM-5 aggregate, to carry its file-size estimate alongside")
    a = ap.parse_args(argv)
    out = dh_privacy.private_dir(dh_privacy.PRIVATE_ROOT / "mining" / a.run / "dhm51")
    t0 = time.time()
    if a.rows:
        rows = [json.loads(l) for l in a.rows.read_text().splitlines() if l.strip()]
    else:
        hs = set(a.harness.split(","))
        rows = []
        if "claude_code" in hs:
            rows += list(iter_claude(a.vault))
        if "codex" in hs:
            rows += list(iter_codex(a.vault))
        if "opencode" in hs:
            rows += list(iter_opencode(a.opencode_db or list(src.OPENCODE_RO_DBS.values())))
        dh_privacy.private_write(out / "turn1.rows.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
    dhm5 = None
    if a.dhm5_aggregate and a.dhm5_aggregate.exists():
        doc = json.loads(a.dhm5_aggregate.read_text())
        d5 = doc.get("dhm5") or doc.get("counts", {}).get("dhm5") or {}
        bh = d5.get("by_harness", {})
        dhm5 = {f"{h}|{role}": v.get("always_on_files_est_tok_per_turn")
                for h, by_src in bh.items() for role, v in (by_src.get("all") or {}).items()
                if isinstance(v, dict) and "always_on_files_est_tok_per_turn" in v}
    agg = aggregate(rows, dhm5)
    agg["generated_at"] = datetime.now(timezone.utc).isoformat()
    agg["counts"]["elapsed_s"] = round(time.time() - t0, 1)
    errs = dh_privacy.validate_aggregate(agg)
    if errs:
        print("aggregate invalid:", errs, file=sys.stderr)
        return 2
    p = dh_privacy.private_write(out / "aggregates" / "dhm51.aggregate.json", json.dumps(agg, indent=1, sort_keys=True))
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
