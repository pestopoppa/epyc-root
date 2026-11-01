#!/usr/bin/env python3
"""handoff_sessions.py - session-per-handoff pilot (operator-approved 2026-11-01, ws58).

ONE resumable agent session per piloted handoff. The handoff file is the durable record; the session is a cache.
Zero-token: this script never calls a model itself, it only starts/resumes the engines' headless CLIs.

Registry: compute-flags/handoff-sessions.json (schema epyc.handoff-sessions.v1)
    {"schema": ..., "max_live": 5, "paused_until": null, "default_engine": "codex", "auto_start": true,
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

AUTO-START (2026-11-01, ws58; the operator found all compute idle while BACKLOG-codex-gen listed dozens of handoffs
"needing a handoff session" that nobody started): every dispatch pass, while live sessions (alive pid) < max_live, the
dispatcher STARTS a fresh session for the highest-ranked handoff without one. The ranking is backlog_gen's
`needs_session` (lane-weighted, transitive inference rows the handoff's open tasks unblock, then backlog-priority rank
of the handoff's index row - never alphabetical). Engine = registry `default_engine` (codex). A session whose handoff
has no open `- [ ]` task left (or whose file left handoffs/active/) becomes `done` and frees its slot. A suspended
session waiting on a running row has no live pid and does not count as live. Every start is logged `AUTO-START`.
Registry knobs: `auto_start` (default true), `default_engine`, `max_live`.

PAUSE RULE (operator, 2026-11-01 21:15Z): a session may be paused ONLY when everything left in its handoff waits on an
inference row that is queued or running. After a landed wrap-up, any open task / publishable row / failed-dry-run fix ->
resumed at once ("continue: next task"); nothing open and no rows waiting -> done (slot to the next ranked handoff);
the reason is logged (`OPEN`/`PAUSE`/`DONE <slug>: <why>`) and shown in the tmux pane between turns.

Subcommands:
    brief <slug>            write compute-flags/briefs/HANDOFF-<slug>.md (the session's goal file)
    start <slug>            start a fresh headless session with its brief, record session_id (registry)
    dispatch [--loop]       one pass (or loop): resume owners on grants/<id>.ended|.complete, start idle
                            handoffs with unblockable work, respect max_live, pause on usage-limit errors.
    transfer <slug> --engine claude|opencode|codex [--force]
                            start a FRESH session of <engine> from files only; refused while the old one is live.
    status                  print the registry.
    pretty                  stdin JSONL -> readable lines (the tmux pane filter)
    pane-status <slug>      the pane's between-turns loop: RUNNING / PAUSED - waiting on row / RESUMING / DONE every 30 s
    rank                    print the handoff ranking (auto-start / yield order) with candidate rows per handoff.

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

VERSION = "hs-dispatcher-v3"
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
def lane_line(slug):
    return (f"Work ONLY in your lane worktree {lane_dir(slug)} (branch {lane_branch(slug)}; origin/main was merged in before "
            f"this resume) and NEVER commit in {ROOT}; wrap up by pushing the lane to main with serialized_push.py --repo {lane_dir(slug)}.")


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
- **Your lane worktree: `{lane_dir(slug)}` on branch `{lane_branch(slug)}`** — your cwd and the ONLY place you edit and
  commit. **Never commit in `{ROOT}`** (the shared clone: parallel commits sweep up each other's staged files). At the
  start of EVERY turn: `git -C {lane_dir(slug)} fetch origin && (git -C {lane_dir(slug)} merge --ff-only origin/main ||
  git -C {lane_dir(slug)} merge --no-edit origin/main)` (the dispatcher does the same before resuming you; a reported
  merge conflict is your first task). Handoff: `{lane_dir(slug)}/{e['handoff']}`.
- Your backlog: `{flags}/BACKLOG-handoff-{slug}.md` (regenerated every 10 min by backlog_gen.py from the registry
  `{reg_path(flags)}`). Owned row ids: {rows}; row patterns: {pats}; handoff task rows: {hrows}.
- Progress files: `progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md` (one per day, append per boundary).
- Row manifests: `{flags}/ready/<id>.json` or `{flags}/ready/armed/<id>.json` (schema `epyc.row.v3`: `result_path`,
  `decision_rule`, `handoff_task`; older v2 manifests carry the same keys plus more). Grants: `{flags}/grants/`.
- This brief: `{flags}/briefs/HANDOFF-{slug}.md`. Flow doc: `docs/guides/agent-workflows/backlog-churn-flow.md`
  (section *Session per handoff*).

## Row lifecycle (you drive every step yourself)
**Inference first.** Your first job is to turn this handoff's measurement/inference tasks into published rows
(`publish_row.py`), starting with the ones whose blockers you can clear fastest, so every lane always has runnable rows.
Non-inference tasks come only after that, or while your rows wait. Your BACKLOG file lists the open boxes that read like
runs under "Own inference tasks to publish as rows" and your handoff's rank among all handoffs.

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
  commit in your LANE (`git -C {lane_dir(slug)} commit -- <paths>`); push the lane to main via
  `python3 scripts/coordination/serialized_push.py --agent handoff-{slug} --repo {lane_dir(slug)} --fetch --push`
  (held lock = wait and retry; non-fast-forward = merge origin/main into the lane and retry); prove
  `git -C {lane_dir(slug)} cherry origin/main <sha>` is empty.
- Then print the line `WRAPPED <sha>` (sha = the landed commit) as the LAST line of your reply. The dispatcher parses
  it into the registry and will NOT resume you for new work until that sha is on origin/main.
- At a milestone, or when your context is large, wrap up and also say `FRESH-SESSION-REQUESTED`.
- No unblockable work left in this handoff: wrap up and reply `IDLE: <reason>` after the `WRAPPED` line.

## Hard rules
- Never arm, grant, qualify, kill or launch compute; never edit grants, the keeper, gates or another session's READY
  manifest. Never pkill/pgrep by name; kill only PIDs you captured.
- Git: work ONLY in your lane worktree; never commit in {ROOT}; never `git add -A`/`git add .`; pathspec-limited commits
  only; push only through serialized_push.py (lane -> main). Never `git worktree prune`, never `git gc`.
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
    return f"""[{VERSION}] Run end in your handoff {e['handoff']}: row `{rid}`. {FANOUT_LINE} {lane_line(slug)}
1. Re-read {e['handoff']} and {flags}/BACKLOG-handoff-{slug}.md (in your lane).
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
    return f"""[{VERSION}] Continue your handoff {e['handoff']}. {FANOUT_LINE} {lane_line(slug)} Re-read the handoff and
{flags}/BACKLOG-handoff-{slug}.md; take the top actionable item per {flags}/briefs/HANDOFF-{slug}.md.
Wrap up at EVERY task boundary (progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md, handoff ticks, pathspec commit,
serialized_push.py, `git cherry origin/main <sha>` empty) and print `WRAPPED <sha>` as your LAST line
(add `IDLE: <reason>` after it when nothing unblockable is left)."""


def continue_prompt(slug, e, flags, why=""):
    return f"""[{VERSION}] continue: next task. Your handoff {e['handoff']} still has open work ({why}); a session pauses ONLY when
everything left waits on an inference row that is queued or running (operator rule 2026-11-01). {FANOUT_LINE}
{lane_line(slug)} Re-read {flags}/BACKLOG-handoff-{slug}.md. INFERENCE FIRST: publish this handoff's measurement
tasks as rows (`publish_row.py`, fastest-clearable blockers first) before any non-inference task; then the top non-inference
item per {flags}/briefs/HANDOFF-{slug}.md. Wrap up at this task boundary (progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md,
handoff ticks, pathspec commit, serialized_push.py, `git cherry origin/main <sha>` empty) and print `WRAPPED <sha>` as
your LAST line (add `IDLE: <reason>` after it only if truly nothing is publishable or doable)."""


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
are your complete starting state. {lane_line(slug)} Then act per the brief.

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


# ---------------------------------------------------------------- lane worktrees (ws58, 2026-11-01 - INC 2026-08-21 class)
# Every session works and commits in its OWN worktree /mnt/raid0/llm/worktrees/mains/h-<slug> on branch lane/h-<slug>
# (created from origin/main; a worktree of /workspace, so the project-cwd rule holds). origin/main is fast-forwarded or
# merged into the lane before every resume. NEVER commit in /workspace: parallel commits in the shared clone sweep up each
# other's staged files. Wrap-up pushes the lane to main through serialized_push.py. Never prune or gc.
LANES_DIR = "/mnt/raid0/llm/worktrees/mains"
WORKTREE_GATE = "scripts/system/worktree_gate.py"


def lane_dir(slug: str) -> str:
    return os.path.join(LANES_DIR, window_name(slug))


def lane_branch(slug: str) -> str:
    return f"lane/{window_name(slug)}"


def _git(cwd, *args, timeout=300):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=timeout)


def ensure_lane(slug: str, repo=None) -> tuple[str, str]:
    """(lane path, sync state). Creates the worktree from origin/main when missing (reusing an existing lane/h-<slug>
    branch), then fast-forwards or merges origin/main into it. 'merge-conflict' leaves the lane untouched (merge aborted)
    and the session is told to resolve it first. Raises RuntimeError when the worktree cannot be created."""
    repo = repo or ROOT
    d = lane_dir(slug)
    _git(repo, "fetch", "-q", "origin", "main")
    if not os.path.exists(os.path.join(d, ".git")):
        os.makedirs(LANES_DIR, exist_ok=True)
        if _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{lane_branch(slug)}").returncode == 0:
            r = _git(repo, "worktree", "add", d, lane_branch(slug))
        else:
            r = _git(repo, "worktree", "add", "-b", lane_branch(slug), d, "origin/main")
        if r.returncode:
            raise RuntimeError(f"worktree add {d} failed: {(r.stderr or r.stdout).strip()[:300]}")
        return d, "created"
    if _git(d, "merge", "--ff-only", "origin/main").returncode == 0:
        return d, "fast-forwarded"
    if _git(d, "merge", "--no-edit", "origin/main").returncode == 0:
        return d, "merged"
    _git(d, "merge", "--abort")
    return d, "merge-conflict"


def remove_lane(flags, slug, repo=None):
    """On done: hand the lane to the removal gate (never a raw `worktree remove`, never prune/gc). Logs the verdict."""
    d = lane_dir(slug)
    if not os.path.exists(d):
        return
    gate = os.path.join(repo or ROOT, WORKTREE_GATE)
    r = subprocess.run([sys.executable, "-I", gate, "remove", d], capture_output=True, text=True, timeout=300)
    log(flags, f"LANE-REMOVE {slug} {d}: rc={r.returncode} {(r.stdout or r.stderr).strip().splitlines()[-1][:200] if (r.stdout or r.stderr).strip() else ''}")


# ---------------------------------------------------------------- tmux windows (operator, 2026-11-01)
# Every handoff session runs inside window `h-<slug>` of the existing tmux session `agent` so the operator can watch it
# live. Windows are addressed by NAME only (`agent:=h-<slug>`), never by index. The engine's JSONL still goes to
# handoff-sessions/<slug>/<ts>.jsonl (tee), the pane shows a readable form (`handoff_sessions.py pretty`), the engine pid
# and exit status land in <out>.pid / <out>.rc for the dispatcher. The pane stays open after the turn (remain-on-exit),
# is reused on the next resume (respawn-pane) while the session is live/continuing, and is KILLED when the session
# pauses (waiting on a row), yields or is done (operator: no clutter; the turn's JSONL stays readable on disk and
# handoff-sessions.log carries the state line). Recreated by name on the next resume. No send-keys, ever.
TMUX_SESSION = "agent"
PROTECTED_WINDOWS = ("codex-gen", "claude")


def tmux(*args, timeout=20):
    """Run one tmux command; (rc, stdout). Monkeypatched in tests."""
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 1, str(ex)


def window_name(slug: str) -> str:
    return f"h-{slug}"


def window_target(slug: str) -> str:
    return f"{TMUX_SESSION}:={window_name(slug)}"  # `=` : exact name match, never an index


def tmux_has_window(slug: str) -> bool | None:
    """True/False, or None when the tmux session itself is unavailable (then the engine runs detached as before)."""
    rc, out = tmux("list-windows", "-t", TMUX_SESSION, "-F", "#{window_name}")
    if rc != 0:
        return None
    return window_name(slug) in out.splitlines()


def shell_quote(x: str) -> str:
    return "'" + str(x).replace("'", "'\\''") + "'"


def pane_command(cmd, prompt_file, out, cwd, slug="", flags=FLAGS) -> str:
    """The shell line the pane runs: engine (stdin = prompt) -> tee JSONL -> readable filter; pid and rc files."""
    me = os.path.abspath(__file__)
    eng = " ".join(shell_quote(c) for c in cmd)
    return (f"cd {shell_quote(cwd)} && {eng} < {shell_quote(prompt_file)} > >(tee {shell_quote(out)} | "
            f"python3 -I {shell_quote(me)} pretty) 2>&1 & echo $! > {shell_quote(out + '.pid')}; wait $!; rc=$?; "
            f"echo $rc > {shell_quote(out + '.rc')}; echo \"[handoff_sessions] engine exit rc=$rc $(date -u +%FT%TZ)\"; "
            f"exec python3 -I {shell_quote(me)} pane-status {shell_quote(slug)} --flags {shell_quote(flags)}")


def launch_in_tmux(slug, cmd, prompt_file, out, cwd, flags=FLAGS):
    """Run the engine in agent:h-<slug>; returns the engine pid or None when tmux is unavailable/failed."""
    has = tmux_has_window(slug)
    if has is None:
        return None
    if window_name(slug) in PROTECTED_WINDOWS:
        return None
    line = ["bash", "-c", pane_command(cmd, prompt_file, out, cwd, slug, flags)]
    if has:
        rc, msg = tmux("respawn-pane", "-k", "-t", window_target(slug), *line)
    else:
        rc, msg = tmux("new-window", "-d", "-t", TMUX_SESSION + ":", "-n", window_name(slug), *line)
    if rc != 0:
        return None
    tmux("set-option", "-w", "-t", window_target(slug), "remain-on-exit", "on")
    pidf = out + ".pid"
    for _ in range(50):  # the pane writes the engine pid within a moment
        try:
            pid = int(open(pidf).read().strip() or 0)
            if pid:
                return pid
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    return None


def kill_window(slug):
    if window_name(slug) in PROTECTED_WINDOWS:
        return
    if tmux_has_window(slug):
        tmux("kill-window", "-t", window_target(slug))


def pane_status_line(e: dict) -> str:
    """The one clear state line the pane shows between turns (operator: never 'Pane is dead')."""
    st = e.get("status")
    if st == "done":
        return "DONE"
    if st == "live":
        return f"RUNNING turn since {e.get('last_resume')} (pid {e.get('pid')})"
    if e.get("work_state") == "pause":
        return f"PAUSED — {e.get('work_reason')} since {e.get('last_end')}"
    if e.get("yield"):
        return f"PAUSED — yielded: handoff below the live cap; not resumed for new work (open: {e.get('work_reason')})"
    if e.get("status") == "unpushed":
        return f"RESUMING … (wrap-up {e.get('last_wrapup')} not yet on origin/main)"
    return f"RESUMING … ({e.get('work_reason') or 'open work; waiting for a free slot'})"


def pane_status(flags, slug, every=30, once=False):
    """Loop in the pane after the engine exits: one state line every 30 s until the registry says done."""
    while True:
        reg = load(reg_path(flags), {"sessions": {}})
        e = (reg.get("sessions") or {}).get(slug) or {"status": "done"}
        print(f"{now_iso()} [{window_name(slug)}] {pane_status_line(e)}", flush=True)
        if e.get("status") == "done" or once:
            return 0
        time.sleep(every)


def last_rc(e) -> int | None:
    try:
        return int(open((e.get("last_output") or "") + ".rc").read().strip())
    except (OSError, ValueError):
        return None


def pretty(src=sys.stdin, dst=sys.stdout):
    """Readable form of an engine JSONL stream for the pane (the JSONL itself is kept by tee)."""
    for line in src:
        line = line.rstrip("\n")
        try:
            ev = json.loads(line)
        except ValueError:
            dst.write(line + "\n"); dst.flush(); continue
        if not isinstance(ev, dict):
            continue
        t = ev.get("type") or ""
        item = ev.get("item") if isinstance(ev.get("item"), dict) else ev
        txt = item.get("text") or item.get("command") or item.get("message") or item.get("result") or ""
        if isinstance(ev.get("message"), dict):  # claude stream-json
            parts = ev["message"].get("content") or []
            txt = " ".join(p.get("text") or p.get("name") or "" for p in parts if isinstance(p, dict))
        sid = ev.get("thread_id") or ev.get("session_id") or ev.get("sessionID")
        if sid:
            dst.write(f"[session {sid}]\n")
        if txt or t:
            dst.write(f"[{t or item.get('type', '?')}] {str(txt)[:600]}\n")
        dst.flush()


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
    pid = launch_in_tmux(slug, cmd, pf, out, cwd, flags)
    if pid:
        return pid, out
    log(flags, f"TMUX-FALLBACK {slug}: no window in session {TMUX_SESSION}; engine runs detached")
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


# ---------------------------------------------------------------- auto-start
def open_tasks(handoff: str, repo=None) -> int:
    """Open `- [ ]` boxes in the handoff file; 0 when the file is gone from handoffs/active/ (moved to completed/)."""
    hp = os.path.join(repo or ROOT, handoff)
    try:
        return len(re.findall(r"^\s*- \[ \]", open(hp, errors="replace").read(), re.M))
    except OSError:
        return 0


def slug_for(handoff: str, sessions: dict) -> str:
    """Stable short slug from the handoff file name; unique against the registry."""
    base = re.sub(r"\.md$", "", os.path.basename(handoff))
    base = re.sub(r"-(?:program|rollout|research|implementation|integration|refresh|20\d{6})$", "", base)
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:40].strip("-") or "handoff"
    if slug in sessions and sessions[slug].get("handoff") != handoff:
        n = 2
        while f"{slug}-{n}" in sessions:
            n += 1
        slug = f"{slug}-{n}"
    return slug


def handoff_slug(sessions: dict, handoff: str):
    for slug, e in sessions.items():
        if isinstance(e, dict) and str(e.get("handoff", "")).split("handoffs/", 1)[-1] == handoff.split("handoffs/", 1)[-1]:
            return slug
    return None


def candidates(flags, reg, repo=None, priority=None, keeper_log=None):
    """Handoffs needing a session, best first (backlog_gen's needs_session ranking), filtered to files that exist in the
    repo with open tasks and no live/suspended session."""
    repo = repo or ROOT
    data = bg.build(flags, priority_for(repo, priority), keeper_log or os.path.join(flags, "ws58-calendar-keeper.log"),
                    sessions_path=reg_path(flags))
    out = []
    S = reg.get("sessions") or {}
    for h in data.get("needs_session") or []:
        hf = h["handoff"]
        slug = handoff_slug(S, hf)
        if slug and S[slug].get("status") != "done":
            continue
        if open_tasks(hf, repo) <= 0:
            continue
        out.append(dict(h, slug=slug))
    return out, data


def priority_for(repo, priority=None):
    """backlog-priority.json (and its sibling .index-state.json) of the repo the dispatcher serves."""
    return priority or os.path.join(repo or ROOT, "handoffs", "active", "backlog-priority.json")


def new_entry(reg, handoff, row_id=None):
    return {"handoff": handoff, "engine": reg.get("default_engine", "codex"), "session_id": None, "status": "suspended",
            "waits_on": [], "last_resume": None, "last_wrapup": None, "brief": None, "row_ids": [], "row_patterns": [],
            "handoff_rows": [row_id] if row_id else [], "pid": None, "auto_started": now_iso()}


def write_backlog_for(flags, slug, data=None, priority=None, keeper_log=None, repo=None):
    """Write BACKLOG-handoff-<slug>.md at once so the brief's pointer resolves before backlog_gen's next 10-min pass."""
    try:
        data = data or bg.build(flags, priority_for(repo, priority),
                                keeper_log or os.path.join(flags, "ws58-calendar-keeper.log"), sessions_path=reg_path(flags))
        if f"handoff-{slug}" in data["workers"]:
            bg.write_atomic(os.path.join(flags, f"BACKLOG-handoff-{slug}.md"), bg.render(f"handoff-{slug}", data))
    except Exception as ex:  # the generator's own pass will write it; never block a start on this
        log(flags, f"BACKLOG-WRITE-FAILED {slug}: {ex!r}")


def mark_yields(flags, reg, data, cap):
    """Operator 2026-11-01: a session whose handoff is not in the top-`cap` handoffs by rows unblocked YIELDS its slot -
    it finishes its current task and wraps up, then is not resumed for NEW work (run-end events for its own rows still
    reach it). Never killed mid-task. The flag clears when the handoff is back in the top-`cap`."""
    S = reg.get("sessions") or {}
    top = {h["handoff"] for h in (data.get("handoff_rank") or [])[:cap]}
    ranked = {h["handoff"]: h for h in data.get("handoff_rank") or []}
    for slug, e in S.items():
        if e.get("status") == "done" or not e.get("handoff"):
            continue
        hf = "handoffs/" + str(e["handoff"]).split("handoffs/", 1)[-1]
        outranked = bool(ranked) and hf not in top
        if outranked and not e.get("yield"):
            h = ranked.get(hf) or {}
            e["yield"] = True
            log(flags, f"YIELD {slug}: handoff rank #{h.get('position', '?')} score={h.get('score', 0)} is below the live cap {cap}; "
                       f"finishes its current task, then not resumed for new work")
        elif not outranked and e.get("yield"):
            e["yield"] = False
            log(flags, f"UNYIELD {slug}: handoff back in the top {cap}")


def auto_start(flags, reg, live, cap, runner=None, repo=None, priority=None, keeper_log=None):
    """Start sessions for the best handoffs that need one until live == cap. Returns the new live count."""
    if not reg.get("auto_start", True):
        return live
    S = reg.setdefault("sessions", {})
    try:
        cands, data = candidates(flags, reg, repo, priority, keeper_log)
    except Exception as ex:
        log(flags, f"AUTO-START-SKIPPED candidates failed: {ex!r}")
        return live
    mark_yields(flags, reg, data, cap)
    if live >= cap:
        return live
    started = []
    for h in cands:
        if live >= cap:
            break
        if h.get("position", 0) > cap and any(e.get("status") != "done" and alive(e.get("pid")) for e in S.values()):
            break  # below the cap and the slot would only be a leftover: wait for a higher-ranked handoff to need it
        slug = h.get("slug") or slug_for(h["handoff"], S)
        e = S.get(slug) or new_entry(reg, h["handoff"], h.get("row_id"))
        if e.get("status") == "done":  # the handoff grew open tasks again: fresh session, same slug
            e.update(new_entry(reg, h["handoff"], h.get("row_id")), restarted_from_done=e.get("session_id"))
        S[slug] = e
        bd = os.path.join(flags, "briefs")
        os.makedirs(bd, exist_ok=True)
        e["brief"] = os.path.join(bd, f"HANDOFF-{slug}.md")
        bg.write_atomic(e["brief"], brief_text(slug, e, flags))
        e["auto_start"] = {"score": h["score"], "rows": h["rows"][:8], "priority": h.get("row_id"), "rank": h.get("priority_rank"), "at": now_iso()}
        _go(flags, slug, e, brief_text(slug, e, flags) + "\n" + idle_prompt(slug, e, flags), runner, None, fresh=True)
        if not alive(e.get("pid")) and e.get("status") != "live":
            continue  # REFUSED-CWD already logged
        live += 1
        started.append(slug)
        log(flags, f"AUTO-START {slug} handoff={h['handoff']} engine={e['engine']} pid={e.get('pid')} score={h['score']} "
                   f"rows={','.join(h['rows'][:6]) or '-'} priority={h.get('row_id') or '-'} rank={h.get('priority_rank')} live={live}/{cap}")
    if started:
        save(reg_path(flags), reg)  # the registry must name the new sessions before their backlogs are rendered
        for slug in started:
            write_backlog_for(flags, slug, None, priority, keeper_log, repo)
    return live


# ---------------------------------------------------------------- pause rule (operator, 2026-11-01 21:15Z)
# A session may be PAUSED only when everything left in its handoff waits on an inference row that is queued or running.
# Otherwise, after a landed wrap-up it is resumed at once ("continue: next task"). Nothing open and no rows -> done.
OWN_TASK_RX = re.compile(r"^- \S+ L\d+ \[(cpu|gpu)\] ", re.M)
IDLE_RX = re.compile(r"IDLE:\s*(.*)")
IDLE_REPORT_COOLDOWN_S = 30 * 60  # a session that itself said IDLE: <reason> is re-asked after this long


def work_state(flags, slug, e, repo=None) -> tuple[str, str]:
    """('continue'|'pause'|'done', reason) from BACKLOG-handoff-<slug>.md + the handoff's open boxes."""
    try:
        b = open(os.path.join(flags, f"BACKLOG-handoff-{slug}.md")).read()
    except OSError:
        b = ""
    adv = ADV_RX.findall(b)
    waiting = re.findall(r"^- \[(?:qualified-armed|running)\] \S+ rank=\S+ \*\*([^*]+)\*\*", b, re.M)
    ni = b.split("## Non-inference", 1)[1] if "## Non-inference" in b else ""
    ni = ni.split("\n## ", 1)[0]
    ntasks = len([l for l in ni.splitlines() if l.startswith("- [")])
    own = len(OWN_TASK_RX.findall(b))
    open_boxes = open_tasks(e.get("handoff", ""), repo)
    if adv:
        return "continue", f"{len(adv)} advanceable row(s) (blocked/needs-launcher/needs-qualification)"
    if own:
        return "continue", f"{own} own inference task(s) to publish as rows"
    if ntasks:
        return "continue", f"{ntasks} non-inference task(s) in the backlog"
    if waiting:
        return "pause", "waiting on row(s) " + ", ".join(waiting[:6]) + " (queued/running)"
    if open_boxes:
        return "continue", f"{open_boxes} open box(es) in the handoff, none waiting on a row"
    return "done", "nothing open and no rows waiting"


# ---------------------------------------------------------------- dispatcher
def end_events(flags):
    for p in glob.glob(os.path.join(flags, "grants", "*.ended")) + glob.glob(os.path.join(flags, "grants", "*.complete")):
        yield os.path.basename(p).rsplit(".", 1)[0], p


def dispatch_once(flags, runner=None, now=None, seed=False, repo=None, priority=None, keeper_log=None):
    now = now or time.time()
    repo = repo or ROOT
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
            mi = IDLE_RX.findall(tailtxt)
            e["idle_reported"] = mi[-1][:200] if mi else None
            e["pid"], e["pending_event"], e["last_end"], e["last_rc"] = None, None, now_iso(), last_rc(e)
            if landed(e.get("last_wrapup")):
                e["status"], e["push_retries"] = "suspended", 0
            else:
                e["status"] = "unpushed"  # never suspended without proof the wrap-up landed
                log(flags, f"UNPUSHED {slug} wrapup={e.get('last_wrapup')}: resuming to push")
            log(flags, f"TURN-END {slug} session={e.get('session_id')} rc={e.get('last_rc')} wrapup={e.get('last_wrapup')}")
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
    # 3b. pause rule: continue / pause / done per work_state (operator 2026-11-01 21:15Z); logged on change
    for slug, e in S.items():
        if e.get("status") == "done" or alive(e.get("pid")) or not e.get("handoff"):
            continue
        ws, why = work_state(flags, slug, e, repo)
        e["_work"] = (ws, why)
        if ws == "done":
            e["status"], e["done_at"] = "done", now_iso()
            kill_window(slug)
            remove_lane(flags, slug, repo)
            log(flags, f"DONE {slug}: {why}; slot freed; tmux window {window_name(slug)} killed")
        else:
            idle_window = ws == "pause" or bool(e.get("yield"))  # operator: no window clutter while paused/yielded
            if idle_window and tmux_has_window(slug):
                kill_window(slug)
                log(flags, f"STATE {slug}: {'paused' if ws == 'pause' else 'yielded'} - {why}; tmux window {window_name(slug)} killed "
                           f"(last turn: {e.get('last_output')})")
            if e.get("work_state") != ws or e.get("work_reason") != why:
                log(flags, f"{'PAUSE' if ws == 'pause' else 'OPEN'} {slug}: {why}")
        e["work_state"], e["work_reason"] = ws, why
    paused = _parse(reg.get("paused_until") or "") > now
    live = sum(1 for e in S.values() if alive(e.get("pid")))  # suspended sessions (waiting on a running row) have no pid
    cap = int(reg.get("max_live", 5))
    if not paused:
        for slug, e in S.items():  # wrap-up not landed: resume at once, no cooldown
            if e.get("status") == "unpushed" and not alive(e.get("pid")) and e.get("session_id") and live < cap:
                if e.get("push_retries", 0) >= MAX_PUSH_RETRIES:
                    continue
                e["push_retries"] = e.get("push_retries", 0) + 1
                _go(flags, slug, e, PUSH_PROMPT.format(v=VERSION, sha=e.get("last_wrapup"), slug=slug, lane=lane_dir(slug)), runner, None)
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
        for slug, e in S.items():  # continue at once: anything open that is not waiting on a queued/running row
            if live >= cap or e.get("status") == "done" or alive(e.get("pid")) or (e.get("_work") or ("", ""))[0] != "continue":
                continue
            if slug in launched or any(ev["slug"] == slug for ev in st["queue"]):
                continue
            if e.get("yield"):
                continue  # outranked: no new work; its slot goes to a higher-ranked handoff
            if e.get("idle_reported") and now - _parse(e.get("last_end") or "") < IDLE_REPORT_COOLDOWN_S:
                continue  # the session itself said IDLE: <reason>; re-asked after the cooldown
            if not wrapped(e, lcache):
                log(flags, f"UNWRAPPED {slug}: refusing resume; last_wrapup={e.get('last_wrapup')}")
                continue
            fresh = bool(e.get("fresh_next")) or not e.get("session_id")
            _go(flags, slug, e, (brief_text(slug, e, flags) + "\n" if fresh else "") + continue_prompt(slug, e, flags, e["_work"][1]),
                runner, None, fresh)
            live += 1
        # 5. AUTO-START: fill the remaining slots with the best handoffs that have no session yet
        live = auto_start(flags, reg, live, cap, runner, repo, priority, keeper_log)
        S = reg["sessions"]
    for e in S.values():
        e.pop("_advanceable", None)
        e.pop("_work", None)
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
        lane, sync = ensure_lane(slug)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        log(flags, f"LANE-FAILED {slug}: {exc}; not spawned")
        e.update({"status": "suspended", "pending_event": ev, "last_refusal": str(exc)})
        return
    if e.get("cwd") != lane:
        log(flags, f"LANE {slug}: cwd {e.get('cwd') or ROOT} -> {lane} ({sync})")
    e["cwd"], e["lane_sync"] = lane, sync
    if sync == "merge-conflict":
        prompt = (f"[{VERSION}] FIRST: `git -C {lane} merge origin/main` conflicts; resolve it in your lane, commit, then continue.\n") + prompt
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
    ap.add_argument("cmd", choices=["brief", "start", "dispatch", "status", "transfer", "rank", "pretty", "pane-status"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--seed", action="store_true", help="mark existing end files seen without resuming")
    ap.add_argument("--engine", choices=list(ENGINES), help="transfer: the engine of the new fresh session")
    ap.add_argument("--force", action="store_true", help="transfer: even while the previous session is live")
    ap.add_argument("--priority", default=None, help="backlog-priority.json for the auto-start ranking (default: backlog_gen's)")
    ap.add_argument("--keeper-log", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "pretty":
        pretty()
        return 0
    if a.cmd == "pane-status":
        return pane_status(a.flags, a.slug)
    reg = load(reg_path(a.flags), {"sessions": {}})
    if a.cmd == "status":
        print(json.dumps(reg, indent=2))
        return 0
    if a.cmd == "rank":  # the auto-start / yield ranking with the candidate rows each handoff carries
        _, data = candidates(a.flags, reg, None, a.priority, a.keeper_log)
        cap = int(reg.get("max_live", 5))
        for h in data.get("handoff_rank") or []:
            mark = "live-cap" if h["position"] <= cap else "below"
            print(f"#{h['position']:>3} {mark:8} score={h['score']:<7} rows={len(h['rows'])} own-inference-tasks={h['candidate_rows']} "
                  f"session={h['session'] or '-':<12} priority={h['row_id'] or '-'} rank={h['priority_rank']} {h['handoff']}")
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
            dispatch_once(a.flags, seed=a.seed, priority=a.priority, keeper_log=a.keeper_log)
        except Exception as ex:  # never die in the loop
            log(a.flags, f"ERROR {ex!r}")
        if not a.loop:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
