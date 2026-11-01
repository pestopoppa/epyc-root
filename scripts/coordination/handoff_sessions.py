#!/usr/bin/env python3
"""handoff_sessions.py - session-per-handoff pilot (operator-approved 2026-11-01, ws58).

ONE resumable agent session per piloted handoff. The handoff file is the durable record; the session is a cache.
Zero-token: this script never calls a model itself, it only starts/resumes the engines' headless CLIs.

Registry: compute-flags/handoff-sessions.json (schema epyc.handoff-sessions.v1)
    {"schema": ..., "max_live": 5, "paused_until": null,
     "sessions": {"<slug>": {"handoff": "handoffs/active/<file>.md", "engine": "codex|claude|opencode",
                             "session_id": "...", "status": "live|suspended|done", "waits_on": [row ids],
                             "last_resume": "<iso>", "last_wrapup": "<path or commit>", "brief": "briefs/HANDOFF-<slug>.md",
                             "row_ids": [...], "row_patterns": [regex...], "handoff_rows": [INF-..], "pid": <int|null>}}}
    backlog_gen.py reads the same file: matched rows leave BACKLOG-<worker>.md and go to BACKLOG-handoff-<slug>.md.

Subcommands:
    brief <slug>            write compute-flags/briefs/HANDOFF-<slug>.md (the session's goal file)
    start <slug>            start a fresh headless session with its brief, record session_id (registry)
    dispatch [--loop]       one pass (or loop): resume owners on grants/<id>.ended|.complete, start idle
                            handoffs with unblockable work, respect max_live, pause on usage-limit errors.
    status                  print the registry.

Verified headless resume forms (2026-11-01 round-trips):
    codex   : codex exec resume --json <thread_id> -      (prompt on stdin; start: codex exec --json -)
    claude  : claude -p --resume <session_id> ...          (OAuth works headless on this host)
    opencode: opencode run -s <ses_id> --format json        (prompt on STDIN; needs its local backend up)
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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_gen as bg  # noqa: E402

VERSION = "hs-dispatcher-v1"
FLAGS = bg.FLAGS_DEFAULT
ROOT = "/workspace"
USAGE_RX = re.compile(r"usage limit|rate[ _-]?limit|quota exceeded|too many requests|\b429\b|hit your limit", re.I)
ADV_RX = re.compile(r"^- \[(blocked|needs-launcher|needs-qualification)\] ", re.M)
IDLE_COOLDOWN_S = 45 * 60
PAUSE_S = 30 * 60


def landed(sha, repo=ROOT) -> bool:
    """Proof a wrap-up landed: `git cherry origin/main <sha>` is empty (and the sha resolves)."""
    if not sha or not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        return False
    subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", "main"], capture_output=True, timeout=120)
    r = subprocess.run(["git", "-C", repo, "cherry", "origin/main", sha], capture_output=True, text=True)
    # "- <sha>" = an equivalent patch is already upstream (rebased on push): landed. Only "+" lines are unlanded.
    return r.returncode == 0 and not any(ln.startswith("+") for ln in r.stdout.splitlines())


PUSH_PROMPT = ("[{v}] Your wrap-up {sha} is NOT on origin/main (`git cherry origin/main {sha}` is non-empty or no WRAPUP "
               "commit was reported). Push your wrap-up now via `python3 scripts/coordination/serialized_push.py --fetch "
               "--push` from your worktree; a held push lock means wait and retry until PUSH VERIFIED. Last line `WRAPUP: <sha>`.")
MAX_PUSH_RETRIES = 6


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(ts):
    try:
        return _dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc).timestamp()
    except Exception:
        return 0.0


def reg_path(flags): return os.path.join(flags, bg.SESSIONS_NAME)
def state_path(flags): return os.path.join(flags, "handoff-sessions.state.json")


def load(p, default):
    d = bg.load_json(p)
    return d if isinstance(d, dict) else default


def save(p, d):
    bg.write_atomic(p, json.dumps(d, indent=2, sort_keys=True) + "\n")


def log(flags, msg):
    with open(os.path.join(flags, "handoff-sessions.log"), "a") as f:
        f.write(f"{now_iso()} {msg}\n")


def alive(pid) -> bool:
    if not pid:
        return False
    try:
        st = open(f"/proc/{int(pid)}/stat").read().rsplit(")", 1)[1].split()[0]
        return st != "Z"
    except OSError:
        return False


# ---------------------------------------------------------------- briefs and prompts
def brief_text(slug: str, e: dict, flags: str) -> str:
    return f"""# HANDOFF-{slug} — session-per-handoff brief (ws58 pilot, operator-approved 2026-11-01)

You are the ONE session that owns `{e['handoff']}` (engine {e.get('engine', 'codex')}). The handoff file is the durable
record; you are a cache. Its READY rows and tasks moved to you from the generalist workers.

Your backlog: `{flags}/BACKLOG-handoff-{slug}.md` (regenerated every 10 min by backlog_gen.py; rows matched by the
registry `{reg_path(flags)}`). Your flow: `docs/guides/agent-workflows/backlog-churn-flow.md` (section *Session per
handoff*) and the loop in `{flags}/GOAL-codex3.md`, scoped to THIS handoff only:

- START every turn: `git -C {ROOT} fetch origin`; re-read the handoff and BACKLOG-handoff-{slug}.md.
- A row of yours ended: file the verdict against its predeclared decision_rule (result path, rc, end line), tick the
  handoff with evidence, decide the follow-up, publish the next id (v2 manifest), go to qualification.
- Rule 1 starved lane first; rule 2: 3 failed qualifications of a lineage -> parked, stop retrying; rule 3: you fix
  cross-session code blocking your row (reviewed commit, name the owner); rule 4: non-blocking code while waiting.
- Never edit grants, the keeper, gates or another session's READY manifest. Never pkill by name. Commits: pathspec only,
  push via `python3 scripts/coordination/serialized_push.py --fetch --push`.
- ALWAYS run the project wrap-up (`/wrap-up` per-task routine: progress entry, handoff ticks with evidence, commit,
  push) before you end a turn, i.e. before you are suspended. Suspend once your row is accepted (armed) by the keeper.
  Record your wrap-up commit in the last line of your reply as `WRAPUP: <commit or path>`.
- At a milestone, or when your context is large, wrap up and say `FRESH-SESSION-REQUESTED`; ws58 starts a new
  session from the handoff and this brief.
- No unblockable work left in this handoff: wrap up and reply `IDLE: <reason>`.
"""


def manifest_for(flags, rid):
    for p in [os.path.join(flags, "ready", f"{rid}.json")] + glob.glob(os.path.join(flags, "ready", "*", f"{rid}.json")):
        d = bg.load_json(p)
        if isinstance(d, dict):
            return p, d
    return None, {}


def end_prompt(slug, e, flags, rid, endfile):
    mp, m = manifest_for(flags, rid)
    try:
        endline = open(endfile).read().strip()[:400]
    except OSError:
        endline = ""
    rc = (re.search(r"rc=(\d+)", endline) or [None, "0" if endfile.endswith(".complete") else "?"])[1]
    outp = os.path.join(flags, "ready", f"{rid}.launcher.out")
    tail = ""
    try:
        tail = open(outp, errors="replace").read().strip().splitlines()[-1][:400]
    except (OSError, IndexError):
        pass
    return f"""[{VERSION}] Run end in your handoff {e['handoff']}: row `{rid}`.
1. `git -C {ROOT} fetch origin`; re-read {e['handoff']} and {flags}/BACKLOG-handoff-{slug}.md.
2. Facts: end file {endfile}: `{endline}` (rc={rc}); launcher end line: `{tail}`;
   READY manifest {mp or '(not found)'}; result_path: {m.get('result_path')}; decision_rule: {json.dumps(m.get('decision_rule'))[:800]}.
3. File the verdict against that decision_rule (handoff tick with evidence), decide the follow-up, and continue the flow
   per {flags}/briefs/HANDOFF-{slug}.md. Run the wrap-up before you end this turn; last line `WRAPUP: <commit>`."""


def idle_prompt(slug, e, flags):
    return f"""[{VERSION}] Continue your handoff {e['handoff']}. `git -C {ROOT} fetch origin`; re-read the handoff and
{flags}/BACKLOG-handoff-{slug}.md; take the top actionable item per {flags}/briefs/HANDOFF-{slug}.md.
Run the wrap-up before you end this turn; last line `WRAPUP: <commit>` (or `IDLE: <reason>`)."""


# ---------------------------------------------------------------- engines
def engine_cmd(engine, session_id, fresh: bool):
    if engine == "codex":
        return ["codex", "exec", "--json", "-"] if fresh else ["codex", "exec", "resume", "--json", session_id, "-"]
    if engine == "claude":
        base = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "bypassPermissions"]
        return base if fresh else base + ["--resume", session_id]
    if engine == "opencode":
        return ["opencode", "run", "--format", "json"] + ([] if fresh else ["-s", session_id])
    raise ValueError(engine)


def launch(flags, slug, e, prompt, fresh=False, runner=None):
    """Start the engine detached; prompt on stdin; output captured to a file (never a pipe)."""
    d = os.path.join(flags, "handoff-sessions", slug)
    os.makedirs(d, exist_ok=True)
    stamp = now_iso().replace(":", "")
    out, pf = os.path.join(d, f"{stamp}.jsonl"), os.path.join(d, f"{stamp}.prompt.md")
    open(pf, "w").write(prompt)
    cmd = engine_cmd(e.get("engine", "codex"), e.get("session_id"), fresh)
    if runner:
        return runner(cmd, pf, out)
    p = subprocess.Popen(cmd, stdin=open(pf), stdout=open(out, "w"), stderr=subprocess.STDOUT, cwd=ROOT,
                         start_new_session=True)
    return p.pid, out


def session_id_from(out_path, engine):
    try:
        s = open(out_path, errors="replace").read()
    except OSError:
        return None
    rx = {"codex": r'"thread_id":"([^"]+)"', "claude": r'"session_id":"([^"]+)"', "opencode": r'"sessionID":"([^"]+)"'}[engine]
    m = re.search(rx, s)
    return m.group(1) if m else None


# ---------------------------------------------------------------- dispatcher
def end_events(flags):
    for p in glob.glob(os.path.join(flags, "grants", "*.ended")) + glob.glob(os.path.join(flags, "grants", "*.complete")):
        yield os.path.basename(p).rsplit(".", 1)[0], p


def dispatch_once(flags, runner=None, now=None, seed=False):
    now = now or time.time()
    reg = load(reg_path(flags), {"sessions": {}})
    st = load(state_path(flags), {"seen": [], "queue": []})
    seen = set(st.get("seen") or [])
    pilots = bg.load_pilots(reg_path(flags))
    S = reg.get("sessions") or {}
    # 1. reap finished turns (and our own zombie children)
    try:
        while os.waitpid(-1, os.WNOHANG)[0]:
            pass
    except ChildProcessError:
        pass
    for slug, e in S.items():
        if e.get("pid") and alive(e["pid"]) and not e.get("session_id"):
            e["session_id"] = session_id_from(e.get("last_output") or "", e.get("engine", "codex"))
        if e.get("pid") and not alive(e["pid"]):
            out = e.get("last_output") or ""
            try:
                tailtxt = open(out, errors="replace").read()[-6000:]
            except OSError:
                tailtxt = ""
            if not e.get("session_id"):
                e["session_id"] = session_id_from(out, e.get("engine", "codex"))
            errs = [ln for ln in tailtxt.splitlines() if re.search(r'"type":\s*"(error|turn\.failed)"|^Error|API Error', ln)]
            if any(USAGE_RX.search(ln) for ln in errs):
                reg["paused_until"] = _dt.datetime.fromtimestamp(now + PAUSE_S, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                log(flags, f"USAGE-LIMIT {slug}: dispatcher paused until {reg['paused_until']} (work not dropped; re-queued)")
                if e.get("pending_event"):
                    st.setdefault("queue", []).insert(0, e["pending_event"])
            m = re.findall(r"WRAPUP: ([^\s\"\\]+)", tailtxt)
            if m:
                e["last_wrapup"] = m[-1]
            if "FRESH-SESSION-REQUESTED" in tailtxt:
                e["fresh_next"] = True
            e["pid"], e["pending_event"], e["last_end"] = None, None, now_iso()
            if landed(e.get("last_wrapup")):
                e["status"], e["push_retries"] = "suspended", 0
            else:
                e["status"] = "unpushed"  # never suspended without proof the wrap-up landed
                log(flags, f"UNPUSHED {slug} wrapup={e.get('last_wrapup')}: resuming to push")
            log(flags, f"TURN-END {slug} session={e.get('session_id')} wrapup={e.get('last_wrapup')}")
    # 2. new run ends owned by a pilot
    for rid, p in end_events(flags):
        key = os.path.basename(p)
        if key in seen:
            continue
        seen.add(key)
        if seed:
            continue
        slug = bg.pilot_of(pilots, rid, None, manifest_for(flags, rid)[1].get("handoff"))
        if slug and slug in S:
            st.setdefault("queue", []).append({"slug": slug, "rid": rid, "end": p})
            log(flags, f"RUN-END {rid} -> {slug}")
    # 3. waits_on from the generated handoff backlog
    for slug, e in S.items():
        try:
            b = open(os.path.join(flags, f"BACKLOG-handoff-{slug}.md")).read()
        except OSError:
            b = ""
        e["waits_on"] = re.findall(r"^- \[(?:qualified-armed|running)\] \S+ rank=\S+ \*\*([^*]+)\*\*", b, re.M)
        e["_advanceable"] = bool(ADV_RX.search(b)) or "## Non-inference" in b and "\n- [" in b.split("## Non-inference", 1)[1]
    paused = _parse(reg.get("paused_until") or "") > now
    live = sum(1 for e in S.values() if alive(e.get("pid")))
    cap = int(reg.get("max_live", 5))
    if not paused:
        for slug, e in S.items():  # wrap-up not landed: resume at once, no cooldown
            if e.get("status") == "unpushed" and not alive(e.get("pid")) and e.get("session_id") and live < cap:
                if e.get("push_retries", 0) >= MAX_PUSH_RETRIES:
                    continue
                e["push_retries"] = e.get("push_retries", 0) + 1
                _go(flags, slug, e, PUSH_PROMPT.format(v=VERSION, sha=e.get("last_wrapup")), runner, None)
                live += 1
        q, rest = st.get("queue") or [], []
        for ev in q:
            e = S.get(ev["slug"])
            if not e or e.get("status") == "done":
                continue
            if alive(e.get("pid")) or live >= cap or not e.get("session_id"):
                rest.append(ev)
                continue
            _go(flags, ev["slug"], e, end_prompt(ev["slug"], e, flags, ev["rid"], ev["end"]), runner, ev)
            live += 1
        st["queue"] = rest
        for slug, e in S.items():  # idle handoffs with unblockable work
            if live >= cap or e.get("status") == "done" or alive(e.get("pid")) or not e.get("_advanceable"):
                continue
            if any(ev["slug"] == slug for ev in st["queue"]):
                continue
            if now - _parse(e.get("last_end") or e.get("last_resume") or "") < IDLE_COOLDOWN_S:
                continue
            fresh = bool(e.get("fresh_next")) or not e.get("session_id")
            _go(flags, slug, e, (brief_text(slug, e, flags) + "\n" if fresh else "") + idle_prompt(slug, e, flags),
                runner, None, fresh)
            live += 1
    for e in S.values():
        e.pop("_advanceable", None)
    st["seen"] = sorted(seen)
    reg["dispatcher"] = {"version": VERSION, "last_pass": now_iso(), "live": live, "paused": paused}
    save(reg_path(flags), reg)
    save(state_path(flags), st)
    return reg, st


def _go(flags, slug, e, prompt, runner, ev, fresh=False):
    if fresh:
        e["session_id"], e["fresh_next"] = None, False
    pid, out = launch(flags, slug, e, prompt, fresh=fresh, runner=runner)
    e.update({"pid": pid, "last_output": out, "status": "live", "last_resume": now_iso(), "pending_event": ev})
    log(flags, f"{'START' if fresh else 'RESUME'} {slug} pid={pid} event={(ev or {}).get('rid', 'idle')} out={out}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["brief", "start", "dispatch", "status"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--seed", action="store_true", help="mark existing end files seen without resuming")
    a = ap.parse_args(argv)
    reg = load(reg_path(a.flags), {"sessions": {}})
    if a.cmd == "status":
        print(json.dumps(reg, indent=2))
        return 0
    if a.cmd in ("brief", "start"):
        e = reg["sessions"][a.slug]
        bd = os.path.join(a.flags, "briefs")
        os.makedirs(bd, exist_ok=True)
        bp = os.path.join(bd, f"HANDOFF-{a.slug}.md")
        bg.write_atomic(bp, brief_text(a.slug, e, a.flags))
        e["brief"] = bp
        if a.cmd == "start":
            _go(a.flags, a.slug, e, brief_text(a.slug, e, a.flags) + "\n" + idle_prompt(a.slug, e, a.flags), None, None, True)
        save(reg_path(a.flags), reg)
        print(bp, e.get("pid") or "")
        return 0
    while True:
        try:
            dispatch_once(a.flags, seed=a.seed)
        except Exception as ex:  # never die in the loop
            log(a.flags, f"ERROR {ex!r}")
        if not a.loop:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
