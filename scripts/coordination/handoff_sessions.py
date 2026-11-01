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

2026-11-01 portability rulings (operator): the owner files its own results (no filing subagent); the session
wraps up at EVERY task boundary and prints `WRAPPED <sha>`; the dispatcher parses the LAST `WRAPPED <sha>` into
`last_wrapup` and REFUSES to resume a session for new work while `last_wrapup` is missing or not landed on
origin/main (`UNWRAPPED <slug>: refusing resume`, event re-queued); `transfer <slug> --engine X` moves a handoff to
a FRESH session of another engine from FILES ONLY (brief + handoff + latest progress + BACKLOG), recording
`transferred_from`. The brief is self-sufficient for a cold agent of any engine.

Subcommands:
    brief <slug>            write compute-flags/briefs/HANDOFF-<slug>.md (the session's goal file)
    start <slug>            start a fresh headless session with its brief, record session_id (registry)
    dispatch [--loop]       one pass (or loop): resume owners on grants/<id>.ended|.complete, start idle
                            handoffs with unblockable work, respect max_live, pause on usage-limit errors.
    transfer <slug> --engine claude|opencode|codex [--force]
                            start a FRESH session of <engine> from files only; refused while the old one is live.
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

VERSION = "hs-dispatcher-v2"
FLAGS = bg.FLAGS_DEFAULT
ROOT = "/workspace"
USAGE_RX = re.compile(r"usage limit|rate[ _-]?limit|quota exceeded|too many requests|\b429\b|hit your limit", re.I)
ADV_RX = re.compile(r"^- \[(blocked|needs-launcher|needs-qualification)\] ", re.M)
IDLE_COOLDOWN_S = 45 * 60
PAUSE_S = 30 * 60
ENGINES = ("codex", "claude", "opencode")
# `WRAPPED <sha>` is the boundary line (2026-11-01 ruling); `WRAPUP: <sha>` is the v1 form, still accepted.
FANOUT_LINE = ("Working mode: FAN OUT - your own thread only reviews, integrates and handles task boundaries; execution goes to "
               "3-5 concurrent subagents on the cheapest capable model/effort (exceptions: agents/shared/OPERATING_CONSTRAINTS.md "
               "-> *When NOT to fan out*). This applies on every engine; do not rely on AGENTS.md/CLAUDE.md being loaded.")
WRAPPED_RX = re.compile(r"(?:WRAPPED|WRAPUP:)\s+([0-9a-f]{7,40})\b")


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
    """Self-sufficient brief: everything a COLD agent of any engine needs (2026-11-01 portability rulings)."""
    rows = ", ".join(f"`{x}`" for x in (e.get("row_ids") or [])) or "(none listed)"
    pats = ", ".join(f"`{x}`" for x in (e.get("row_patterns") or [])) or "(none)"
    hrows = ", ".join(f"`{x}`" for x in (e.get("handoff_rows") or [])) or "(none)"
    return f"""# HANDOFF-{slug} — session-per-handoff brief (ws58 pilot, operator-approved 2026-11-01)

You are the ONE session that owns `{e['handoff']}` (engine {e.get('engine', 'codex')}). The handoff file is the durable
record; you are a cache. Its READY rows and tasks moved to you from the generalist workers. Everything you need is in
this brief and on disk/origin/main — you may have no transcript of earlier turns; never assume one.

## Working mode: fan out (operator rule, binding on every engine)
{FANOUT_LINE}

## Where things are
- Repo root: `{ROOT}` (branch main; always `git -C {ROOT} fetch origin` first). Handoff: `{ROOT}/{e['handoff']}`.
- Your backlog: `{flags}/BACKLOG-handoff-{slug}.md` (regenerated every 10 min by backlog_gen.py from the registry
  `{reg_path(flags)}`). Owned row ids: {rows}; row patterns: {pats}; handoff task rows: {hrows}.
- Progress files: `progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md` (one per day, append per boundary).
- Row manifests: `{flags}/ready/<id>.json` or `{flags}/ready/armed/<id>.json` (schema `epyc.row.v3`: `result_path`,
  `decision_rule`, `handoff_task`; older v2 manifests carry the same keys plus more). Grants: `{flags}/grants/`.
- This brief: `{flags}/briefs/HANDOFF-{slug}.md`. Flow doc: `docs/guides/agent-workflows/backlog-churn-flow.md`
  (section *Session per handoff*).

## Row lifecycle (you drive every step yourself)
1. Write a spec JSON (id, owner, launcher, lane cpu|gpu, result_path, result_format, decision_rule, estimate_s,
   handoff_task, priority_rank) and publish it: `python3 scripts/coordination/rowflow/publish_row.py <spec.json>`.
2. The keeper dry-runs/qualifies the row and grants it (`grants/<id>`); you NEVER arm, grant, qualify or run compute.
3. `grants/<id>.ended|.complete` appears -> the dispatcher resumes you with rc, end line, result_path, decision_rule.
4. YOU file the verdict: read `result_path`, apply `decision_rule`, tick the handoff with evidence (rc, result path,
   numbers). No filing subagent exists; nobody files for you. Then `touch {flags}/filing-done/<id>.FILED`: that
   receipt lets the deterministic keeper reaper reclaim the row's scratch_root (reclaim is never your job).
   Row state: `python3 scripts/coordination/rowflow/rowflow.py status <id>` (needs-dryrun, dryrun-running, failed
   [fix task in {flags}/dryrun/<id>/FAIL-*.json], parked, grantable, armed, running, done).
5. Decide the next step (follow-up row, park, done) and publish the next row (step 1). Rule 1 starved lane first;
   rule 2: 3 failed qualifications of a lineage -> parked, stop retrying; rule 3: you fix cross-session code blocking
   your row (reviewed commit, name the owner); rule 4: non-blocking code while waiting.

## Wrap-up contract — at EVERY task boundary, before you end any turn
- Progress entry in `progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md`; handoff ticks with evidence; pathspec-limited
  commit (`git commit -- <paths>`); push via `python3 scripts/coordination/serialized_push.py --fetch --push`
  (held lock = wait and retry); prove `git cherry origin/main <sha>` is empty.
- Then print the line `WRAPPED <sha>` (sha = the landed commit) as the LAST line of your reply. The dispatcher parses
  it into the registry and will NOT resume you for new work until that sha is on origin/main.
- At a milestone, or when your context is large, wrap up and also say `FRESH-SESSION-REQUESTED`.
- No unblockable work left in this handoff: wrap up and reply `IDLE: <reason>` after the `WRAPPED` line.

## Hard rules
- Never arm, grant, qualify, kill or launch compute; never edit grants, the keeper, gates or another session's READY
  manifest. Never pkill/pgrep by name; kill only PIDs you captured.
- Git: never `git add -A`/`git add .`; pathspec-limited commits only; push only through serialized_push.py.
- Suspend once your row is accepted (armed) by the keeper; do not poll.

## Transfer rule
Ownership of this handoff may move to another engine (codex/claude/opencode) at ANY boundary via
`handoff_sessions.py transfer`. The new session starts from FILES ONLY (this brief, the handoff, your latest progress
file, the backlog) — so your state must be complete on disk AND on origin/main at every boundary.
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
    return f"""[{VERSION}] Run end in your handoff {e['handoff']}: row `{rid}`. {FANOUT_LINE}
1. `git -C {ROOT} fetch origin`; re-read {e['handoff']} and {flags}/BACKLOG-handoff-{slug}.md.
2. Facts: end file {endfile}: `{endline}` (rc={rc}); launcher end line: `{tail}`;
   manifest {mp or '(not found; look in ' + flags + '/ready/<id>.json or ready/armed/<id>.json)'} (schema {m.get('schema', 'epyc.row.v2|v3')});
   result_path: {m.get('result_path')}; handoff_task: {m.get('handoff_task')}; decision_rule: {json.dumps(m.get('decision_rule'))[:800]}.
3. YOU file the verdict yourself: read result_path, apply decision_rule, tick the handoff with evidence. No filing
   subagent does this for you. Then `touch {flags}/filing-done/{rid}.FILED` — that receipt is what lets the
   deterministic keeper reaper reclaim the scratch_root; without it nothing is reclaimed (reclaim is not your job).
   Row state any time: `python3 scripts/coordination/rowflow/rowflow.py status <id>` (needs-dryrun, dryrun-running,
   failed [owner fix task in {flags}/dryrun/<id>/FAIL-*.json], parked, grantable, armed, running, done).
4. Decide the next step and publish the next row: `python3 scripts/coordination/rowflow/publish_row.py <spec.json>`
   (spec: id, owner, launcher, lane cpu|gpu, result_path, result_format, decision_rule, estimate_s, handoff_task,
   priority_rank). Continue per {flags}/briefs/HANDOFF-{slug}.md.
5. Wrap up at this task boundary (progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md, handoff ticks, pathspec commit,
   serialized_push.py, `git cherry origin/main <sha>` empty) and print `WRAPPED <sha>` as your LAST line."""


def idle_prompt(slug, e, flags):
    return f"""[{VERSION}] Continue your handoff {e['handoff']}. {FANOUT_LINE} `git -C {ROOT} fetch origin`; re-read the handoff and
{flags}/BACKLOG-handoff-{slug}.md; take the top actionable item per {flags}/briefs/HANDOFF-{slug}.md.
Wrap up at EVERY task boundary (progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md, handoff ticks, pathspec commit,
serialized_push.py, `git cherry origin/main <sha>` empty) and print `WRAPPED <sha>` as your LAST line
(add `IDLE: <reason>` after it when nothing unblockable is left)."""


def transfer_prompt(slug, e, flags, repo=ROOT):
    """FILES-ONLY cold-start prompt for a fresh engine: brief + handoff + latest progress file + BACKLOG."""
    brief = brief_text(slug, e, flags)
    hp = os.path.join(repo, e["handoff"])
    prog = sorted(glob.glob(os.path.join(repo, "progress", "*", f"*handoff-{slug}*.md")),
                  key=lambda p: (os.path.getmtime(p), p))
    pp = prog[-1] if prog else None
    bp = os.path.join(flags, f"BACKLOG-handoff-{slug}.md")

    def rd(p):
        try:
            return open(p, errors="replace").read()
        except (OSError, TypeError):
            return "(file not found)"
    prev = e.get("transferred_from") or []
    prev_s = f"{prev[-1]['engine']} session {prev[-1]['session_id']}" if prev else "another engine"
    return f"""[{VERSION}] TRANSFER: you are the NEW owner session (engine {e.get('engine')}) of handoff {e['handoff']},
taken over from {prev_s}. The previous engine's transcript is UNAVAILABLE and must not be assumed: the files below
are your complete starting state. `git -C {repo} fetch origin` first; then act per the brief.

===== BRIEF ({flags}/briefs/HANDOFF-{slug}.md) =====
{brief}
===== HANDOFF ({hp}) =====
{rd(hp)}
===== LATEST PROGRESS ({pp or 'none found: progress/YYYY-MM/*handoff-' + slug + '*.md'}) =====
{rd(pp)}
===== BACKLOG ({bp}) =====
{rd(bp)}
===== END OF FILES =====
{idle_prompt(slug, e, flags)}"""


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


def project_cwd(e: dict, repo=None) -> str:
    """Operator rule 2026-11-01: every launched session starts INSIDE the project (the repo or one of its worktrees) so it
    loads AGENTS.md / CLAUDE.md like any project agent. Returns the validated cwd or raises ValueError (the dispatcher
    refuses to spawn)."""
    repo = repo or ROOT
    cwd = os.path.realpath(e.get("cwd") or repo)
    if not os.path.isdir(cwd):
        raise ValueError(f"cwd {cwd} does not exist")
    def common(d):
        r = subprocess.run(["git", "-C", d, "rev-parse", "--git-common-dir"], capture_output=True, text=True)
        if r.returncode:
            return None
        return os.path.realpath(os.path.join(d, r.stdout.strip()))
    want, have = common(repo), common(cwd)
    if want is None or have is None or want != have:
        raise ValueError(f"cwd {cwd} is not the project repo {repo} or one of its worktrees (git common dir {have} != {want})")
    return cwd


def launch(flags, slug, e, prompt, fresh=False, runner=None):
    """Start the engine detached; prompt on stdin; output captured to a file (never a pipe). cwd = project_cwd(e)."""
    cwd = project_cwd(e)  # ValueError -> the caller logs REFUSED-CWD and does not spawn
    d = os.path.join(flags, "handoff-sessions", slug)
    os.makedirs(d, exist_ok=True)
    stamp = now_iso().replace(":", "")
    out, pf = os.path.join(d, f"{stamp}.jsonl"), os.path.join(d, f"{stamp}.prompt.md")
    open(pf, "w").write(prompt)
    cmd = engine_cmd(e.get("engine", "codex"), e.get("session_id"), fresh)
    if runner:
        try:
            return runner(cmd, pf, out, cwd=cwd)
        except TypeError:  # older 3-argument test runners
            return runner(cmd, pf, out)
    p = subprocess.Popen(cmd, stdin=open(pf), stdout=open(out, "w"), stderr=subprocess.STDOUT, cwd=cwd,
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
            m = WRAPPED_RX.findall(tailtxt)
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
        q, rest, lcache, launched = st.get("queue") or [], [], {}, set()
        for ev in q:
            e = S.get(ev["slug"])
            if not e or e.get("status") == "done":
                continue
            if alive(e.get("pid")) or live >= cap or not e.get("session_id"):
                rest.append(ev)
                continue
            if not wrapped(e, lcache):  # 2026-11-01 ruling: no new work on an unwrapped session; keep the event
                e["pending_event"] = ev
                rest.append(ev)
                log(flags, f"UNWRAPPED {ev['slug']}: refusing resume; last_wrapup={e.get('last_wrapup')}")
                continue
            _go(flags, ev["slug"], e, end_prompt(ev["slug"], e, flags, ev["rid"], ev["end"]), runner, ev)
            launched.add(ev["slug"])
            live += 1
        st["queue"] = rest
        for slug, e in S.items():  # idle handoffs with unblockable work
            if live >= cap or e.get("status") == "done" or alive(e.get("pid")) or not e.get("_advanceable"):
                continue
            if slug in launched or any(ev["slug"] == slug for ev in st["queue"]):
                continue
            if now - _parse(e.get("last_end") or e.get("last_resume") or "") < IDLE_COOLDOWN_S:
                continue
            if not wrapped(e, lcache):
                log(flags, f"UNWRAPPED {slug}: refusing resume; last_wrapup={e.get('last_wrapup')}")
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


def wrapped(e, cache=None) -> bool:
    """Gate for resuming a session with NEW work: its last `WRAPPED <sha>` must be on origin/main.
    A session that never ran a turn (no session_id, no last_end) has nothing to have wrapped and passes."""
    lw = e.get("last_wrapup")
    if not lw:
        return not e.get("session_id") and not e.get("last_end")
    if cache is None:
        cache = {}
    if lw not in cache:
        cache[lw] = landed(lw)
    return cache[lw]


def transfer(flags, slug, engine, force=False, runner=None, repo=ROOT):
    """Move a handoff to a FRESH session of `engine`, started from files only (brief, handoff, latest progress,
    BACKLOG). Refused while the previous session is live unless force. Records `transferred_from` history."""
    if engine not in ENGINES:
        raise ValueError(f"engine must be one of {ENGINES}: {engine}")
    reg = load(reg_path(flags), {"sessions": {}})
    e = reg["sessions"][slug]
    if alive(e.get("pid")) and not force:
        raise RuntimeError(f"REFUSED transfer {slug}: previous {e.get('engine')} session pid={e['pid']} is live; "
                           f"let it wrap up first (or --force)")
    bd = os.path.join(flags, "briefs")
    os.makedirs(bd, exist_ok=True)
    e["brief"] = os.path.join(bd, f"HANDOFF-{slug}.md")
    bg.write_atomic(e["brief"], brief_text(slug, e, flags))
    e.setdefault("transferred_from", []).append(
        {"engine": e.get("engine", "codex"), "session_id": e.get("session_id"), "at": now_iso(),
         "last_wrapup": e.get("last_wrapup"), "forced": bool(force and alive(e.get("pid")))})
    e["engine"] = engine
    _go(flags, slug, e, transfer_prompt(slug, e, flags, repo), runner, None, fresh=True)
    e["session_id"] = session_id_from(e.get("last_output") or "", engine)  # may still be None; reaped by dispatch
    log(flags, f"TRANSFER {slug} -> {engine} from={e['transferred_from'][-1]['engine']}:"
               f"{e['transferred_from'][-1]['session_id']} pid={e.get('pid')} session={e.get('session_id')}")
    save(reg_path(flags), reg)
    return e


def _go(flags, slug, e, prompt, runner, ev, fresh=False):
    if fresh:
        e["session_id"], e["fresh_next"] = None, False
    try:
        pid, out = launch(flags, slug, e, prompt, fresh=fresh, runner=runner)
    except ValueError as exc:  # project_cwd refused: never spawn outside the project
        log(flags, f"REFUSED-CWD {slug}: {exc}")
        e.update({"status": "suspended", "pending_event": ev, "last_refusal": str(exc)})
        return
    e.update({"pid": pid, "last_output": out, "status": "live", "last_resume": now_iso(), "pending_event": ev})
    log(flags, f"{'START' if fresh else 'RESUME'} {slug} pid={pid} event={(ev or {}).get('rid', 'idle')} out={out}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["brief", "start", "dispatch", "status", "transfer"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--seed", action="store_true", help="mark existing end files seen without resuming")
    ap.add_argument("--engine", choices=list(ENGINES), help="transfer: the engine of the new fresh session")
    ap.add_argument("--force", action="store_true", help="transfer: even while the previous session is live")
    a = ap.parse_args(argv)
    reg = load(reg_path(a.flags), {"sessions": {}})
    if a.cmd == "status":
        print(json.dumps(reg, indent=2))
        return 0
    if a.cmd == "transfer":
        if not a.slug or not a.engine:
            ap.error("transfer needs <slug> and --engine")
        try:
            e = transfer(a.flags, a.slug, a.engine, force=a.force)
        except RuntimeError as ex:
            log(a.flags, str(ex))
            print(ex, file=sys.stderr)
            return 2
        print(json.dumps({k: e.get(k) for k in ("engine", "session_id", "pid", "last_output", "transferred_from")}, indent=2))
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
