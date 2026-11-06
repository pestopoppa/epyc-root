#!/usr/bin/env python3
"""Zero-token budget meter (operator decision 2026-11-06, token-efficiency audit rec 3). No LLM calls.

Sums per-call usage from ~/.codex/sessions rollouts (`token_count.last_token_usage`) and, with --claude, Claude
transcripts (assistant `usage`, deduplicated by message id) into <flags>/budget.json:

  weekly_fraction   provider meter (rate_limits.primary.used_percent / 100 of the newest token_count event)
  resets_at         epoch seconds of that window's reset; window_minutes alongside
  burn_frac_per_h   weekly-fraction rise per hour over the last 3 h of meter samples
  tokens_last_1h / tokens_last_24h / tokens_window   raw per-call tokens (input + output) from the rollouts
  paused_until      = resets_at once exhausted (fraction >= 1 or rate_limit_reached_type set); else null
  alarms            50 % and 80 % alarms through rowflow/notify.py (idempotent per reset window)

Incremental: per-file byte offsets live in <flags>/budget-meter.state.json, so a pass reads only new lines.
Run it from the dispatcher loop (handoff_sessions.py calls update() each pass) or standalone with --loop.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rowflow"))

CODEX_ROOT = os.path.expanduser("~/.codex/sessions")
CLAUDE_ROOT = os.path.expanduser("~/.claude/projects")
STATE_NAME = "budget-meter.state.json"
BUDGET_NAME = "budget.json"
ALARMS = (0.5, 0.8)
KEEP_S = 8 * 86400


def _load(p, default):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return default


def _save(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1, sort_keys=True)
    os.replace(tmp, p)


def _ts(s):
    try:
        import datetime as dt
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def _scan(files, st, now, parse):
    """Read the new tail of every file (offset in st['files']); parse(line) -> (ts, tokens, extra) | None."""
    offs = st.setdefault("files", {})
    for f in files:
        try:
            size = os.path.getsize(f)
            if now - os.path.getmtime(f) > KEEP_S:
                continue
        except OSError:
            continue
        off = offs.get(f, 0)
        if off > size:
            off = 0
        if off == size:
            continue
        with open(f, "rb") as fh:
            fh.seek(off)
            data = fh.read()
        cut = data.rfind(b"\n") + 1  # never consume a partial last line
        for ln in data[:cut].decode(errors="replace").splitlines():
            r = parse(ln)
            if r:
                yield r
        offs[f] = off + cut


def _codex_parse(ln):
    if '"token_count"' not in ln:
        return None
    try:
        d = json.loads(ln)
    except ValueError:
        return None
    p = d.get("payload") or {}
    u = (p.get("info") or {}).get("last_token_usage") or {}
    return _ts(d.get("timestamp")), int(u.get("input_tokens") or 0) + int(u.get("output_tokens") or 0), p.get("rate_limits")


def _claude_parse_factory(seen):
    def parse(ln):
        if '"usage"' not in ln or '"assistant"' not in ln:
            return None
        try:
            d = json.loads(ln)
        except ValueError:
            return None
        m = d.get("message") or {}
        mid = m.get("id")
        if not mid or mid in seen:
            return None
        seen.add(mid)
        u = m.get("usage") or {}
        tok = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        return _ts(d.get("timestamp")), tok, None
    return parse


def _bucket(st, key, ts, tok, now):
    b = st.setdefault(key, {})
    h = str(int(ts // 3600 * 3600))
    b[h] = b.get(h, 0) + tok
    for k in [k for k in b if now - int(k) > KEEP_S]:
        del b[k]


def _sum(b, since):
    return sum(v for k, v in (b or {}).items() if int(k) + 3600 > since)


def compute(flags, now=None, codex_root=CODEX_ROOT, claude_root=None, write=True, notify=None):
    """One meter pass. Returns the budget dict; writes budget.json + state unless write=False."""
    now = now or time.time()
    sp = os.path.join(flags, STATE_NAME)
    st = _load(sp, {})
    files = glob.glob(os.path.join(codex_root, "*", "*", "*", "rollout-*.jsonl"))
    newest = st.get("rate_limits")
    for ts, tok, rl in _scan(files, st.setdefault("codex", {}), now, _codex_parse):
        if ts:
            _bucket(st, "codex_hours", ts, tok, now)
            if rl and rl.get("primary") and ts >= float((newest or {}).get("_ts") or 0):
                newest = dict(rl, _ts=ts)
    st["rate_limits"] = newest
    if claude_root:
        seen = set(st.get("claude_seen") or [])
        for ts, tok, _ in _scan(glob.glob(os.path.join(claude_root, "*", "*.jsonl")), st.setdefault("claude", {}), now,
                                _claude_parse_factory(seen)):
            if ts:
                _bucket(st, "claude_hours", ts, tok, now)
        st["claude_seen"] = sorted(seen)[-50000:]
    prim = (newest or {}).get("primary") or {}
    frac = float(prim["used_percent"]) / 100.0 if prim.get("used_percent") is not None else None
    resets_at = float(prim.get("resets_at") or 0) or None
    if resets_at and resets_at <= now:  # the window already reset since the last event: the meter is stale, not full
        frac, resets_at = 0.0, None
    samples = [s for s in st.get("samples") or [] if now - s[0] < 6 * 3600]
    if frac is not None:
        samples.append([now, frac])
    st["samples"] = samples
    old = [s for s in samples if now - s[0] <= 3 * 3600]
    burn = None
    if len(old) >= 2 and old[-1][0] > old[0][0] and old[-1][1] >= old[0][1]:
        burn = (old[-1][1] - old[0][1]) / ((old[-1][0] - old[0][0]) / 3600.0)
    exhausted = frac is not None and (frac >= 1.0 or bool((newest or {}).get("rate_limit_reached_type")))
    win_start = (resets_at - float(prim.get("window_minutes") or 10080) * 60) if resets_at else now - 7 * 86400
    budget = {"schema": "epyc.codex-budget.v1", "generated_at": now, "engine": "codex",
              "weekly_fraction": frac, "resets_at": resets_at, "window_minutes": prim.get("window_minutes"),
              "burn_frac_per_h": burn,
              "hours_to_reset": round((resets_at - now) / 3600.0, 2) if resets_at else None,
              "tokens_last_1h": _sum(st.get("codex_hours"), now - 3600),
              "tokens_last_24h": _sum(st.get("codex_hours"), now - 86400),
              "tokens_window": _sum(st.get("codex_hours"), win_start),
              "paused_until": resets_at if exhausted else None,
              "alarms": []}
    if claude_root:
        budget["claude_tokens_last_1h"] = _sum(st.get("claude_hours"), now - 3600)
        budget["claude_tokens_last_24h"] = _sum(st.get("claude_hours"), now - 86400)
    if frac is not None:
        for thr in ALARMS + ((1.0,) if exhausted else ()):
            if frac >= thr:
                budget["alarms"].append(thr)
                if write:
                    _alarm(flags, thr, frac, resets_at, burn, notify)
    if write:
        _save(sp, st)
        _save(os.path.join(flags, BUDGET_NAME), budget)
    return budget


def _alarm(flags, thr, frac, resets_at, burn, notify=None):
    """One idempotent alert per threshold per reset window through the existing inference mailbox."""
    emit = notify
    if emit is None:
        try:
            import notify as rf_notify
            emit = rf_notify.emit
        except Exception:
            return
    when = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(resets_at)) if resets_at else "unknown"
    summary = (f"codex weekly budget {frac:.0%} used (threshold {thr:.0%}); resets {when}; burn "
               f"{(burn or 0) * 100:.2f} %/h" + ("; dispatcher paused until reset" if thr >= 1.0 else ""))
    try:
        emit(flags, "quota", "", f"codex-budget-{int(thr * 100)}-{int(resets_at or 0)}", summary,
             "critical" if thr >= 0.8 else "warning", owner="", detail={"fraction": frac, "resets_at": resets_at})
    except Exception:
        pass  # an alert failure never stops the meter


def update(flags, **kw):
    """Dispatcher hook: one pass, never raises."""
    try:
        return compute(flags, **kw)
    except Exception as ex:
        return {"error": repr(ex)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=os.environ.get("HS_FLAGS", "/mnt/raid0/llm/tmp/compute-flags"))
    ap.add_argument("--codex-root", default=CODEX_ROOT)
    ap.add_argument("--claude", action="store_true", help="also sum Claude transcripts under ~/.claude/projects")
    ap.add_argument("--dry-run", action="store_true", help="print the budget; write nothing, alert nothing")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=300)
    a = ap.parse_args(argv)
    while True:
        b = compute(a.flags, codex_root=a.codex_root, claude_root=CLAUDE_ROOT if a.claude else None, write=not a.dry_run)
        print(json.dumps(b, indent=1))
        if not a.loop:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
