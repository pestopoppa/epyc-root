#!/usr/bin/env python3
"""tokens_per_task.py - THE churn metric (operator, 2026-11-01 22:55Z): tokens per COMPLETED task, per session.

    tokens  = input + output tokens of every Codex rollout attributable to the session today: its own thread
              (registry session_id) plus its sub-agents (rollouts whose cwd is the session's lane worktree
              /mnt/raid0/llm/worktrees/mains/h-<slug>). Rollouts in the shared /workspace era are "unattributed".
    completed = handoff boxes ticked (`+- [x]` lines in the session's landed wrap-up commits, from TURN-END lines in
              handoff-sessions.log) + rows published today (ready/<id>.json, owner = the session) + filings today
              (filing-done/<id>.FILED whose manifest owner is the session).
    tokens per completed task = tokens / completed   (inf when nothing completed: that session only spent)

Also lists the most expensive turns (task_started -> task_complete windows) with the wrap-up commit subject.

    python3 tokens_per_task.py [--flags DIR] [--repo DIR] [--since ISO] [--top N] [--json]
Imported by flow_scoreboard.py for its headline column. Zero-token, read-only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import subprocess
import sys

FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
REPO = "/workspace"
LANES = "/mnt/raid0/llm/worktrees/mains"
SESSIONS = os.path.expanduser("~/.codex/sessions")


def _ts(x):
    try:
        return _dt.datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except ValueError:
        return None


def rollout_files(day: _dt.date):
    return glob.glob(os.path.join(SESSIONS, f"{day:%Y}", f"{day:%m}", f"{day:%d}", "rollout-*.jsonl"))


def scan_rollout(path, since):
    """(thread_id, cwd, input, output, turns[list of (start, end, input, output)], last_ctx) for events at/after `since`."""
    tid = cwd = None
    inp = out = 0
    last_ctx = 0
    turns, cur = [], None
    with open(path, errors="replace") as f:
        for ln in f:
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            p = d.get("payload") or {}
            if d.get("type") == "session_meta":
                tid, cwd = p.get("id"), p.get("cwd")
                continue
            t = _ts(d.get("timestamp"))
            if t is None or (since and t < since) or d.get("type") != "event_msg":
                continue
            k = p.get("type")
            if k == "task_started":
                cur = [t, None, 0, 0]
            elif k == "token_count":
                u = ((p.get("info") or {}).get("last_token_usage") or {})
                i, o = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
                inp += i
                out += o
                last_ctx = i or last_ctx
                if cur:
                    cur[2] += i
                    cur[3] += o
            elif k in ("task_complete", "turn_aborted") and cur:
                cur[1] = t
                turns.append(tuple(cur))
                cur = None
    if cur:
        turns.append((cur[0], None, cur[2], cur[3]))
    return tid, cwd, inp, out, turns, last_ctx


def attribute(tid, cwd, sid2slug):
    if tid in sid2slug:
        return sid2slug[tid], "session"
    m = re.match(re.escape(LANES) + r"/h-([A-Za-z0-9._-]+)", str(cwd or ""))
    if m:
        return m.group(1), "subagent"
    return "unattributed", "shared"


def turn_ends(flags, since):
    """slug -> [(time, wrapup sha)] from handoff-sessions.log TURN-END lines."""
    out = {}
    try:
        for ln in open(os.path.join(flags, "handoff-sessions.log"), errors="replace"):
            m = re.match(r"^(\S+) TURN-END (\S+) .*wrapup=([0-9a-f]{7,40})", ln)
            if not m:
                continue
            t = _ts(m.group(1))
            if t and (not since or t >= since):
                out.setdefault(m.group(2), []).append((t, m.group(3)))
    except OSError:
        pass
    return out


def ticks_in(repo, sha):
    """(ticked boxes, subject) of one landed wrap-up commit."""
    r = subprocess.run(["git", "-C", repo, "show", "--format=%s%n", sha, "--", "handoffs/"], capture_output=True, text=True)
    if r.returncode:
        return 0, "(commit not found)"
    lines = r.stdout.splitlines()
    return sum(1 for l in lines if re.match(r"^\+\s*- \[x\]", l, re.I)), (lines[0] if lines else "")


def owner_slug(owner):
    o = str(owner or "")
    return re.sub(r"^(handoff-|h-)", "", o) if o else ""


def completed(flags, repo, slug, ends, since):
    ticks, commits, subjects = 0, 0, {}
    for _, sha in ends.get(slug, []):
        n, subj = ticks_in(repo, sha)
        ticks += n
        commits += 1
        subjects[sha] = subj
    rows = fil = 0
    since_ts = since.timestamp() if since else 0
    for p in glob.glob(os.path.join(flags, "ready", "*.json")):
        try:
            if os.path.getmtime(p) < since_ts:
                continue
            if owner_slug(json.load(open(p)).get("owner")) == slug:
                rows += 1
        except (OSError, ValueError):
            continue
    for p in glob.glob(os.path.join(flags, "filing-done", "*.FILED")):
        try:
            if os.path.getmtime(p) < since_ts:
                continue
            rid = os.path.basename(p)[:-6]
            mp = next(iter(glob.glob(os.path.join(flags, "ready", f"{rid}.json")) + glob.glob(os.path.join(flags, "ready", "*", f"{rid}.json"))), None)
            if mp and owner_slug(json.load(open(mp)).get("owner")) == slug:
                fil += 1
        except (OSError, ValueError):
            continue
    return {"ticks": ticks, "commits": commits, "rows": rows, "filings": fil, "subjects": subjects}


def compute(flags=FLAGS, repo=REPO, since=None, day=None, top=3):
    now = _dt.datetime.now(_dt.timezone.utc)
    day = day or now.date()
    since = since or _dt.datetime.combine(day, _dt.time(0, tzinfo=_dt.timezone.utc))
    reg = (json.load(open(os.path.join(flags, "handoff-sessions.json"))) or {}).get("sessions", {})
    sid2slug = {e.get("session_id"): s for s, e in reg.items() if e.get("session_id")}
    for s, e in reg.items():
        for prev in (e.get("transferred_from") or []) + ([e.get("rotated_from")] if e.get("rotated_from") else []):
            if prev and prev.get("session_id"):
                sid2slug.setdefault(prev["session_id"], s)
    per, turns_all = {}, []
    for f in rollout_files(day):
        tid, cwd, inp, out, turns, ctx = scan_rollout(f, since)
        if not inp and not out:
            continue
        slug, kind = attribute(tid, cwd, sid2slug)
        r = per.setdefault(slug, {"input": 0, "output": 0, "session_input": 0, "subagent_input": 0, "subagent_rollouts": 0, "ctx": 0, "turns": 0})
        r["input"] += inp
        r["output"] += out
        r["turns"] += len(turns)
        if kind == "session":
            r["session_input"] += inp
            r["ctx"] = max(r["ctx"], ctx)
            for st, en, ti, to in turns:
                turns_all.append({"slug": slug, "start": st, "end": en, "tokens": ti + to})
        else:
            r["subagent_input"] += inp
            r["subagent_rollouts"] += 1
    ends = turn_ends(flags, since)
    for slug, r in per.items():
        c = completed(flags, repo, slug, ends, since) if slug != "unattributed" else {"ticks": 0, "commits": 0, "rows": 0, "filings": 0, "subjects": {}}
        r.update(c)
        r["completed"] = c["ticks"] + c["rows"] + c["filings"]
        r["tokens"] = r["input"] + r["output"]
        r["tokens_per_task"] = (r["tokens"] / r["completed"]) if r["completed"] else None
    # most expensive turns: attach the wrap-up subject of the TURN-END that followed the turn
    for t in turns_all:
        subj = ""
        for (te, sha) in ends.get(t["slug"], []):
            if t["end"] and 0 <= (te - t["end"]).total_seconds() <= 600:
                subj = per[t["slug"]]["subjects"].get(sha, "") + f" ({sha[:9]})"
                break
        t["subject"] = subj or "(no landed wrap-up within 10 min: partial/no-op turn)"
    turns_all.sort(key=lambda t: -t["tokens"])
    return {"since": since.isoformat(), "per": per, "top_turns": turns_all[:top]}


def fmt_m(n):
    return f"{n / 1e6:.1f}M"


def render(res, width=36):
    L = [f"tokens per completed task (since {res['since']}; tokens = session + its lane sub-agents; completed = ticks + rows published + filings)",
         f"{'session':{width}}{'tokens':>8}{'sub-agent%':>11}{'ctx k':>7}{'turns':>6}{'ticks':>6}{'rows':>5}{'filed':>6}{'tok/task':>10}"]
    for slug, r in sorted(res["per"].items(), key=lambda x: -(x[1]["tokens_per_task"] or 1e18) if x[1]["completed"] else -1e19):
        tpt = fmt_m(r["tokens_per_task"]) if r["tokens_per_task"] else "inf"
        sub = f"{100 * r['subagent_input'] / r['input']:.0f}%" if r["input"] else "-"
        L.append(f"{slug:{width}}{fmt_m(r['tokens']):>8}{sub:>11}{r['ctx'] // 1000:>7}{r['turns']:>6}{r.get('ticks', 0):>6}{r.get('rows', 0):>5}{r.get('filings', 0):>6}{tpt:>10}")
    if res["top_turns"]:
        L.append("most expensive session turns:")
        for t in res["top_turns"]:
            L.append(f"- {t['slug']} {t['start']:%H:%M}Z-{t['end']:%H:%M}Z {fmt_m(t['tokens'])}: {t['subject'][:120]}" if t["end"]
                     else f"- {t['slug']} {t['start']:%H:%M}Z-(open) {fmt_m(t['tokens'])}: {t['subject'][:120]}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--since", default=None, help="ISO time (default: today 00:00Z)")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = compute(a.flags, a.repo, _ts(a.since) if a.since else None, top=a.top)
    if a.json:
        print(json.dumps(res, default=str, indent=1))
    else:
        print(render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
