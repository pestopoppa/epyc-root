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
import shutil
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
               "3-5 concurrent subagents on the cheapest capable model/effort with TIGHT, FILE-POINTED prompts (paths + the exact "
               "change; never a transcript), only where it saves wall-clock without raising tokens per completed task - the metric "
               "(exceptions: agents/shared/OPERATING_CONSTRAINTS.md -> *When NOT to fan out*). This applies on every engine; do not "
               "rely on AGENTS.md/CLAUDE.md being loaded. Never re-read or re-verify what the scripts (wrapup.py, file_result.py, "
               "publish_row.py) already guarantee. Every subagent gets ONE bounded job (<=40 tool calls) and ends; never spawn a "
               "subagent to watch, poll, wait or monitor anything (2026-11-01: single luna subagents made ~1000 calls each).")
NO_POLL_LINE = ("NEVER wait in this turn: no sleep, no polling of grants/dry-run/queue files, no wait_agent/status loops - publish or "
                "delegate, wrap up, end the turn; the dispatcher resumes you on the event (grant end, dry-run result, or a file you "
                "registered under handoff-sessions/<slug>/awaiting/).")


def lane_line(slug):
    return (f"Work ONLY in your lane worktree {lane_dir(slug)} (branch {lane_branch(slug)}; origin/main was merged in before "
            f"this resume) and NEVER commit in {ROOT}; wrap up by pushing the lane to main with serialized_push.py --repo {lane_dir(slug)}. "
            + NO_POLL_LINE)


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
# DSH-2/3/4 (intake-2603, operator "All four" 2026-11-01)
MAX_REQUEUE = 3                       # run-end event redelivered at most 3 times without filing-done/<id>.FILED
TRANSIENT_RX = re.compile(r"\b(408|50[0-9]|502|503|504)\b|connection reset|ECONNRESET|ETIMEDOUT|timed? ?out|stream disconnected|"
                          r"server_error|overloaded|temporarily unavailable", re.I)
TRANSIENT_BACKOFF_S = (120, 240, 480)  # "go on" retries after 2/4/8 min
DRYRUN_EVENT_MAX_AGE_S = 30 * 60      # dry-run results older than this are not events (restart safety)
FILING_SLOTS = 1                       # DSH-4: one slot above max_live reserved for run-end filing resumes
GO_ON_PROMPT = ("[{v}] go on. Your previous turn ended with a transient error (rc={rc}: {err}) and no wrap-up; this is retry "
                "{n}/3. Continue exactly where you were and finish with `WRAPPED <sha>` (and report.json).")


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
    if is_generalist(e):
        try:
            goal = open(os.path.join(flags, f"GOAL-{GENERALIST}.md"), errors="replace").read()
        except OSError:
            goal = "(GOAL-codex-gen.md missing)"
        return (goal + f"\n\n## Managed-session contract (dispatcher)\n{FANOUT_LINE}\n{lane_line(slug)}\n"
                f"Your backlog: `{flags}/BACKLOG-{GENERALIST}.md`; rows/tasks labelled 'yours' are yours. Wrap up with ONE JSON -> "
                f"`python3 scripts/coordination/churn/wrapup.py --json <file> --lane {lane_dir(slug)}` (slug {GENERALIST}); its "
                f"`WRAPPED <sha>` is your LAST line. One turn = ALL ready items, via sub-agents; never a one-item turn.\n")
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
- Every resume prompt carries your STATE delta (rows, next tasks, own inference tasks; CAF-3) - act on it, do not start a
  turn by re-reading files. Full view when needed: `{flags}/BACKLOG-handoff-{slug}.md` (regenerated every 10 min by backlog_gen.py from the registry
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
   handoff_task, priority_rank, kind=compute) and publish it: `python3 scripts/coordination/rowflow/publish_row.py <spec.json>`.
   **Verify/prepare inputs ONCE before publishing, never inside the grant** (operator 23:55Z "DO BETTER"): publish_row
   refuses a launcher, or any script it runs, that hashes model weights (`sha256sum` over *.gguf / FULL-MODEL.sha256) or
   does single-core prep (tokenize, download, copy) - do that in your own turn, then publish; fetch-only rows
   (`kind: fetch|prepare`) are refused for the same reason.
2. The keeper dry-runs/qualifies the row and grants it (`grants/<id>`); you NEVER arm, grant, qualify or run compute.
3. `grants/<id>.ended|.complete` appears -> the dispatcher resumes you with rc, end line, result_path, decision_rule.
4. YOU file the verdict: read `result_path`, apply `decision_rule`, tick the handoff with evidence (rc, result path,
   numbers). No filing subagent exists; nobody files for you. Then `touch {flags}/filing-done/<id>.FILED`: that
   receipt lets the deterministic keeper reaper reclaim the row's scratch_root (reclaim is never your job).
   Row state: `python3 scripts/coordination/rowflow/rowflow.py status <id>` (needs-dryrun, dryrun-running, failed
   [fix task in {flags}/dryrun/<id>/FAIL-*.json], parked, grantable, armed, running, done).
5. Decide the next step (follow-up row, park, done) and publish the next row (step 1). Rule 1 starved lane first;
   rule 2: 3 failed qualifications of a lineage -> parked, stop retrying; rule 3: you fix cross-session code blocking
   your row (reviewed commit, name the owner); rule 4: non-inference work is its own later turn, never an in-turn wait.

## Wrap-up contract — at EVERY task boundary, before you end any turn (CAF-2: ONE command)
- Write ONE JSON: {{"slug": "{slug}", "state": "progress|ready|blocked|failed|idle|dropped", "task_text": "<what you did>",
  "ticks": ["<exact text of each handoff box you completed>"], "progress_md": "<the progress entry>", "paths": ["<files you
  changed, lane-relative>"], "belief": "cc|clm_<id>|no-belief: <reason>", "message": "<commit subject + body>",
  "question": null, "rows_published": ["<row ids>"], "trailers": ["Co-Authored-By: ...", "Claude-Session: ..."]}} and run
  `python3 scripts/coordination/churn/wrapup.py --json <file> --lane {lane_dir(slug)}`. It merges origin/main into your
  lane, appends the progress entry (`progress/YYYY-MM/YYYY-MM-DD-handoff-{slug}.md`), ticks the boxes BY TEXT with the
  belief tag, runs `index_state.py --check`, makes the pathspec commit with your trailers, pushes the lane to main through
  `serialized_push.py`, proves `git cherry origin/main` empty, writes `{flags}/handoff-sessions/{slug}/report.json` (the
  DSH-1 record, with `wrapped_sha`) and prints `WRAPPED <sha>` as its last line - make that the LAST line of your reply.
  You never run progress/tick/commit/push/cherry by hand. The dispatcher reads report.json first and will NOT resume you
  for new work until that sha is on origin/main. A run-end event counts as consumed ONLY when `filing-done/<id>.FILED`
  exists (DSH-2; `file_result.py` touches it).
- At a milestone, or when your context is large, wrap up and also say `FRESH-SESSION-REQUESTED`.
- **Rows queued or running are never a reason to stop** (operator 2026-11-01 23:30Z: compute must be the ONLY bottleneck;
  waiting for rows to become available is a pipeline FAILURE). While your rows run, continue with this handoff's other
  blockers and unpublished inference tasks; deficit lanes (inventory below target in your STATE delta) come first. Pause only
  when NOTHING is open except items waiting on your own running rows - then say `IDLE: waiting on rows <ids>` after `WRAPPED`.

## Hard rules
- Never arm, grant, qualify, kill or launch compute; never edit grants, the keeper, gates or another session's READY
  manifest. Never pkill/pgrep by name; kill only PIDs you captured.
- Git: work ONLY in your lane worktree; never commit in {ROOT}; never `git add -A`/`git add .`; pathspec-limited commits
  only; push only through serialized_push.py (lane -> main). Never `git worktree prune`, never `git gc`.
- **Scratch never goes in the lane** (disk incident 2026-11-02 00:55Z, 130 GiB leaked): you and your sub-agents write
  scratch to `/mnt/raid0/llm/tmp/{slug}/...` (or the row's scratch_root). The lane is sparse (no `artifacts/`); wrapup.py
  REFUSES to land while untracked files sit under `artifacts/` in the lane; the lane is reaped when you pause and
  recreated on resume, so anything not committed and pushed is gone.
- **NEVER wait in a turn** (CAF-1, operator 2026-11-01): no `sleep`, no polling of grants/dry-run/queue files, no
  `wait_agent`/`list_agents`/status loops, no watching a sub-agent. Publish or delegate, wrap up, END THE TURN. The
  dispatcher resumes you on the event: your row's `grants/<id>.ended|.complete`, its `dryrun/<id>/PASS.json|FAIL-n.json`,
  or any file you register in `{flags}/handoff-sessions/{slug}/awaiting/<name>.json` as {{"path": "<file that will
  appear>", "note": "<what it means>"}} (a sub-agent's output file, a build artifact). A turn that polls is a defect.
- A turn that commits nothing, publishes no row and files nothing is a no-op: the dispatcher will not resume you again
  until a new event arrives, so do real work or end with `IDLE: <reason>`.

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


FILE_RESULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "churn", "file_result.py")


def file_result(flags, rid, lane) -> tuple[int, str]:
    """CAF-5: let the script file a numeric decision_rule before any agent turn. (rc, stdout). Monkeypatched in tests."""
    try:
        r = subprocess.run([sys.executable, "-I", FILE_RESULT, rid, "--flags", flags, "--lane", lane or ROOT],
                           capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 2, str(ex)


def filing_step(flags, rid, filing):
    """Step 3 of the run-end prompt. CAF-5 deletes the agent filing turn for numeric rules: when file_result.py filed
    the row (rc 0) the agent only carries the TICK line into its wrap-up; rc 4 = the rule needs the agent's verdict JSON."""
    rc, out = filing if filing else (None, "")
    tick = next((ln for ln in out.splitlines() if ln.startswith("TICK ")), "")
    if rc == 0:
        return (f"3. FILED BY SCRIPT (file_result.py): {out.strip().splitlines()[0][:300] if out.strip() else 'filed'}. The receipt "
                f"filing-done/{rid}.FILED exists; do NOT re-file. Put this tick line in your wrap-up ticks: `{tick[5:300]}`.")
    if rc == 4:
        return (f"3. The decision_rule is not machine-checkable. Write {{\"verdict\": \"pass|fail|inconclusive\", \"rationale\": \"...\", "
                f"\"tick_text\": \"<exact open box text>\"}} to a file and run `python3 scripts/coordination/churn/file_result.py {rid} "
                f"--flags {flags} --verdict-json <file> --lane <your lane>`: it writes the verdict record, ticks the box and touches "
                f"filing-done/{rid}.FILED (the receipt that acks this event and lets the reaper reclaim scratch).")
    return (f"3. Filing script result rc={rc}: {out.strip()[:200]}. File the verdict yourself (read result_path, apply decision_rule, "
            f"tick the handoff with evidence) and `touch {flags}/filing-done/{rid}.FILED` — the receipt acks this event.")


def related_ids(flags, rid):
    """SA-3: the ids a resumed owner needs for a targeted delta instead of a cold re-read: row, manifest, handoff task,
    lineage, grant end file(s), prior dry-run FAIL/PASS records, verdict record."""
    mp, m = manifest_for(flags, rid)
    fails = sorted(glob.glob(os.path.join(flags, "dryrun", rid, "FAIL-*.json")))
    rel = {"row": rid, "manifest": mp, "handoff_task": m.get("handoff_task"), "lineage": (m.get("lineage") or bg.id_stem(rid)),
           "result_path": m.get("result_path"), "decision_rule": m.get("decision_rule"),
           "ends": [p for p in (os.path.join(flags, "grants", rid + ".ended"), os.path.join(flags, "grants", rid + ".complete")) if os.path.exists(p)],
           "prior_fail": fails[-1] if fails else None, "pass": os.path.join(flags, "dryrun", rid, "PASS.json") if os.path.exists(os.path.join(flags, "dryrun", rid, "PASS.json")) else None,
           "verdict": os.path.join(flags, "filing-done", rid + ".verdict.json") if os.path.exists(os.path.join(flags, "filing-done", rid + ".verdict.json")) else None}
    return rel


def related_line(rel):
    return ("Related: " + "; ".join(f"{k}={v}" for k, v in rel.items() if v and k not in ("decision_rule", "result_path")))[:900]


def end_prompt(slug, e, flags, rid, endfile, delta="", filing=None):
    mp, m = manifest_for(flags, rid)
    rel = related_ids(flags, rid)
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
    return f"""[{VERSION}] Run end in your handoff {e.get('handoff') or 'codex-gen backlog'}: row `{rid}`. {FANOUT_LINE} {lane_line(slug)}
{delta_block(delta).replace('{flags}', flags).replace('<slug>', slug)}1. The handoff is {e['handoff']} in your lane; the state above is current.
2. Facts: end file {endfile}: `{endline}` (rc={rc}); launcher end line: `{tail}`; manifest {mp or '(none)'} (schema {m.get('schema', 'epyc.row.v3')});
   result_path: {m.get('result_path')}; decision_rule: {json.dumps(m.get('decision_rule'))[:800]}.
   {related_line(rel)}
{filing_step(flags, rid, filing)}
   Row state any time: `python3 scripts/coordination/rowflow/rowflow.py status <id>` (needs-dryrun, dryrun-running,
   failed [owner fix task in {flags}/dryrun/<id>/FAIL-*.json], parked, grantable, armed, running, done).
4. Decide the next step and publish the next row: `python3 scripts/coordination/rowflow/publish_row.py <spec.json>`
   (spec: id, owner, launcher, lane cpu|gpu, result_path, result_format, decision_rule, estimate_s, handoff_task,
   priority_rank). Continue per {flags}/briefs/HANDOFF-{slug}.md.
5. Wrap up: ONE JSON -> `python3 scripts/coordination/churn/wrapup.py --json <file> --lane {lane_dir(slug)}` (CAF-2); its
   `WRAPPED <sha>` is your LAST line."""


def delta_block(delta):
    return (f"STATE (CAF-3; this replaces re-reading the BACKLOG — open {{flags}}/BACKLOG-handoff-<slug>.md only for rows not listed):\n{delta}\n"
            if delta else "")


def idle_prompt(slug, e, flags, delta=""):
    return f"""[{VERSION}] Continue your handoff {e.get('handoff') or 'codex-gen backlog'}. {FANOUT_LINE} {lane_line(slug)}
{delta_block(delta).replace('{flags}', flags).replace('<slug>', slug)}Take the top actionable item per {flags}/briefs/HANDOFF-{slug}.md (inference first). Wrap up with ONE JSON ->
`python3 scripts/coordination/churn/wrapup.py --json <file> --lane {lane_dir(slug)}` (CAF-2); its `WRAPPED <sha>` is your
LAST line (add `IDLE: <reason>` after it when nothing unblockable is left)."""


def continue_prompt(slug, e, flags, why="", delta=""):
    warn = ("" if int(e.get("noop_turns", 0)) < STUCK_AFTER - 1 else
            f"WARNING: your last {e.get('noop_turns')} turn(s) landed nothing. THIS turn must land a tick, publish a row or file a result "
            f"(wrapup.py / publish_row.py / file_result.py) or you will be parked as STUCK until a run-end arrives. ")
    return f"""[{VERSION}] {warn}continue: FINISH ALL READY ITEMS IN THIS ONE TURN (budget rule 22:45Z: one resume per session per
{MIN_RESUME_GAP_S // 60} min; a one-item turn wastes the whole context re-read). Your handoff {e.get('handoff') or 'codex-gen backlog'}
still has open work ({why}); fan every independent item out to sub-agents now and land them all before wrapping up.
Rows queued or running are no reason to stop: a session pauses ONLY when nothing is open except items waiting on its own running rows. {FANOUT_LINE}
{lane_line(slug)}
{delta_block(delta).replace('{flags}', flags).replace('<slug>', slug)}INFERENCE FIRST: publish this handoff's measurement
tasks as rows (`publish_row.py`, fastest-clearable blockers first) before any non-inference task; then the top non-inference
item per {flags}/briefs/HANDOFF-{slug}.md. Wrap up with ONE JSON -> `python3 scripts/coordination/churn/wrapup.py --json <file>
--lane {lane_dir(slug)}` (CAF-2); its `WRAPPED <sha>` is your LAST line (add `IDLE: <reason>` after it only if truly nothing
is publishable or doable)."""


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
===== LAST TURN REPORT (report.json, DSH-1) =====
{json.dumps(e.get("last_report")) if e.get("last_report") else "(none)"}
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
        # SPARSE lane (ws58 00:55Z, 71 lanes x 1-2 GiB leaked 130 GiB): no checkout first, then everything but artifacts/
        if _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{lane_branch(slug)}").returncode == 0:
            r = _git(repo, "worktree", "add", "--no-checkout", d, lane_branch(slug))
        else:
            r = _git(repo, "worktree", "add", "--no-checkout", "-b", lane_branch(slug), d, "origin/main")
        if r.returncode:
            raise RuntimeError(f"worktree add {d} failed: {(r.stderr or r.stdout).strip()[:300]}")
        sparse_lane(d)
        r = _git(d, "checkout", "-q")
        if r.returncode:
            raise RuntimeError(f"sparse checkout of {d} failed: {(r.stderr or r.stdout).strip()[:300]}")
        return d, "created"
    if not os.path.exists(os.path.join(repo, ".git", "worktrees", os.path.basename(d), "info", "sparse-checkout")) and \
            not _git(d, "config", "--get", "core.sparseCheckout").stdout.strip() == "true":
        sparse_lane(d)  # an old full lane: drop artifacts/ from its working tree (tracked files only; scratch stays visible)
    if _git(d, "merge", "--ff-only", "origin/main").returncode == 0:
        return d, "fast-forwarded"
    if _git(d, "merge", "--no-edit", "origin/main").returncode == 0:
        return d, "merged"
    _git(d, "merge", "--abort")
    return d, "merge-conflict"


LANE_EXCLUDE = ("artifacts/",)      # ~800 MB of every full checkout; sessions never need it in the lane
DISK_FLOOR_GIB = 160                # no new lane below this much free space


def sparse_lane(d):
    """Non-cone sparse checkout: everything except LANE_EXCLUDE."""
    _git(d, "sparse-checkout", "init", "--no-cone")
    _git(d, "sparse-checkout", "set", "--no-cone", "/*", *[f"!/{x}" for x in LANE_EXCLUDE])


def free_gib(path="/mnt/raid0/llm") -> float:
    try:
        return shutil.disk_usage(path).free / 2**30
    except OSError:
        return float("inf")


def lane_clean_and_landed(d) -> bool:
    if not os.path.isdir(d):
        return False
    if _git(d, "status", "--porcelain").stdout.strip():
        return False
    r = _git(d, "cherry", "origin/main")
    return r.returncode == 0 and not any(l.startswith("+") for l in r.stdout.splitlines())


def reap_lanes(flags, reg, repo=None):
    """Lanes of sessions that are not live (suspended/yielded/done/failed) are removed when clean and landed (never --force,
    never prune); they are recreated on the next resume. A dirty lane is left for one wrap-up resume (logged once)."""
    repo = repo or ROOT
    for slug, e in (reg.get("sessions") or {}).items():
        if alive(e.get("pid")) or e.get("status") in ("live", "retry", "unpushed"):
            continue
        d = lane_dir(slug)
        if not os.path.exists(d):
            continue
        if lane_clean_and_landed(d):
            r = _git(repo, "worktree", "remove", d)
            log(flags, f"LANE-REAPED {slug} {d}: rc={r.returncode} {(r.stderr or '').strip()[:120]} (clean, landed; recreated on resume)")
        elif not e.get("lane_dirty_logged"):
            e["lane_dirty_logged"] = now_iso()
            log(flags, f"LANE-DIRTY {slug} {d}: uncommitted or unlanded work; kept for one wrap-up resume")


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


def report_path(flags, slug):
    return os.path.join(flags, "handoff-sessions", slug, "report.json")


def turn_report(flags, slug, e):
    """DSH-1: the session's structured turn report, if written during this turn (mtime >= last_resume); else None.
    {state: progress|ready|blocked|failed|idle|dropped, wrapped_sha, question, rows_published}"""
    p = report_path(flags, slug)
    try:
        if os.path.getmtime(p) + 1 < _parse(e.get("last_resume") or ""):
            return None
        r = json.load(open(p))
        return r if isinstance(r, dict) else None
    except (OSError, ValueError):
        return None


def landed_ticks(sha, repo=None) -> int:
    """Boxes ticked by a LANDED wrap-up commit (the sha must resolve; `git show <sha> -- handoffs/`)."""
    if not sha or not re.fullmatch(r"[0-9a-f]{7,40}", str(sha)):
        return 0
    r = subprocess.run(["git", "-C", repo or ROOT, "show", "--format=", sha, "--", "handoffs/"], capture_output=True, text=True)
    return sum(1 for l in r.stdout.splitlines() if re.match(r"^\+\s*- \[x\]", l, re.I)) if r.returncode == 0 else 0


def turn_effect(flags, slug, e, rep=None) -> str:
    """What the turn COMPLETED (operator 2026-11-02): a landed tick, a published row or a filing. A commit alone is not an
    effect. '' = no effect."""
    since = _parse(e.get("last_resume") or "") - 1
    out = []
    n = landed_ticks(e.get("last_wrapup")) if e.get("last_wrapup") and landed(e.get("last_wrapup")) else 0
    if n:
        out.append(f"{n} landed tick(s) in {str(e.get('last_wrapup'))[:9]}")
    for pat, name in (("ready/*.json", "row(s) published"), ("filing-done/*.FILED", "filing(s)")):
        new = [p for p in glob.glob(os.path.join(flags, pat)) if os.path.getmtime(p) >= since]
        if new:
            out.append(f"{len(new)} {name}")
    if rep and rep.get("rows_published"):
        out.append(f"rows_published {len(rep['rows_published'])}")
    return "; ".join(out)


def filed(flags, rid) -> bool:
    return os.path.exists(os.path.join(flags, "filing-done", f"{rid}.FILED"))


def escalate_filing(flags, slug, ev):
    d = os.path.join(flags, "operator-escalations")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"filing-{ev['rid']}.md")
    bg.write_atomic(p, f"# Filing escalation: row {ev['rid']} (handoff session {slug})\n\n"
                       f"The run-end event ({ev.get('end')}) was delivered {MAX_REQUEUE + 1} times to session `{slug}` and no "
                       f"`filing-done/{ev['rid']}.FILED` receipt appeared (DSH-2 cap). The row stays `needs-filing` in the backlog "
                       f"until an operator or the owner files it and touches the receipt. Generated {now_iso()}.\n")
    return p


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


def candidates(flags, reg, repo=None, priority=None, keeper_log=None, data=None):
    """Handoffs needing a session, best first (backlog_gen's needs_session ranking), filtered to files that exist in the
    repo with open tasks and no live/suspended session. `data` = a build from this pass, to avoid a second one."""
    repo = repo or ROOT
    data = data or bg.build(flags, priority_for(repo, priority), keeper_log or os.path.join(flags, "ws58-calendar-keeper.log"),
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


def has_awaiting(flags, slug) -> bool:
    return bool(glob.glob(os.path.join(flags, "handoff-sessions", slug, "awaiting", "*.json")))


def sticky(flags, slug, e) -> bool:
    """Operator 2026-11-01 23:35Z (thrash, not idleness: ~40 handoffs cycled in 30 min, half-built rows abandoned): a
    session KEEPS its slot while it is mid-work - live, a commit/row/filing in its last turn, or delegated work awaited.
    It loses it only after 2 consecutive no-op turns, an IDLE report, or when nothing is open."""
    if int(e.get("noop_turns", 0)) >= 2 or e.get("idle_reported"):
        return False  # two no-op turns or an IDLE report: the slot is up for grabs even while the session is live
    return alive(e.get("pid")) or bool(e.get("last_effect")) or has_awaiting(flags, slug)


def mark_yields(flags, reg, data, cap):
    """Operator 2026-11-01: a session whose handoff is not in the top-`cap` handoffs by rows unblocked YIELDS its slot -
    it finishes its current task and wraps up, then is not resumed for NEW work (run-end events for its own rows still
    reach it). Never killed mid-task. The flag clears when the handoff is back in the top-`cap`."""
    S = reg.get("sessions") or {}
    top = {h["handoff"] for h in (data.get("handoff_rank") or [])[:cap]}
    ranked = {h["handoff"]: h for h in data.get("handoff_rank") or []}
    for slug, e in S.items():
        if e.get("status") == "done" or not e.get("handoff") or is_generalist(e):
            continue
        hf = "handoffs/" + str(e["handoff"]).split("handoffs/", 1)[-1]
        outranked = bool(ranked) and hf not in top and not sticky(flags, slug, e)
        if outranked and not e.get("yield"):
            h = ranked.get(hf) or {}
            e["yield"] = True
            log(flags, f"YIELD {slug}: handoff rank #{h.get('position', '?')} score={h.get('score', 0)} is below the live cap {cap}; "
                       f"finishes its current task, then not resumed for new work")
        elif not outranked and e.get("yield"):
            e["yield"] = False
            log(flags, f"UNYIELD {slug}: handoff back in the top {cap}")


st_disk_logged = {}


def auto_start(flags, reg, live, cap, runner=None, repo=None, priority=None, keeper_log=None, data=None):
    """Start sessions for the best handoffs that need one until live == cap. Returns the new live count."""
    if not reg.get("auto_start", True):
        return live
    S = reg.setdefault("sessions", {})
    try:
        cands, data = candidates(flags, reg, repo, priority, keeper_log, data)
    except Exception as ex:
        log(flags, f"AUTO-START-SKIPPED candidates failed: {ex!r}")
        return live
    mark_yields(flags, reg, data, cap)
    if live >= cap:
        return live
    started = []
    if free_gib() < DISK_FLOOR_GIB:
        if time.time() - st_disk_logged.get("t", 0) > 600:
            log(flags, f"AUTO-START-THROTTLED disk: {free_gib():.0f} GiB free < {DISK_FLOOR_GIB}; no new lanes")
            st_disk_logged["t"] = time.time()
        return live
    pinned = set(reg.get("pinned") or [])
    st = load(state_path(flags), {})
    starts = [t for t in (st.get("starts") or []) if time.time() - t < 3600]
    # SA-1 (intake ws58-jev-20261102, operator D9-ack 2026-11-02): admit ONLY handoffs with a real ready/stuck row, or pinned
    # ones; heuristic "own inference tasks" never start a session (that path produced ~40 starts/30 min and 0 ready rows).
    order = [h for h in cands if h.get("rows") or h["handoff"] in pinned or (h.get("slug") or "") in pinned]
    for h in order:
        if live >= cap:
            break
        slug0 = h.get("slug") or slug_for(h["handoff"], S)
        prev = S.get(slug0) or {}
        last = max(_parse(prev.get("done_at") or ""), _parse(prev.get("last_end") or ""), _parse((prev.get("auto_start") or {}).get("at") or ""))
        if last and time.time() - last < AUTO_START_COOLDOWN_S:
            if time.time() - _parse(prev.get("throttle_logged") or "") > AUTO_START_COOLDOWN_S:
                log(flags, f"AUTO-START-THROTTLED {slug0}: per-handoff cooldown ({int((time.time() - last) / 60)} min since its last end/start < {AUTO_START_COOLDOWN_S // 60})")
                prev["throttle_logged"] = now_iso()
                S[slug0] = prev
            continue
        if len(starts) >= MAX_STARTS_PER_HOUR:
            log(flags, f"AUTO-START-THROTTLED {slug0}: global cap {MAX_STARTS_PER_HOUR} starts/hour reached")
            break
        starts.append(time.time())
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
    st["starts"] = starts
    save(state_path(flags), st)
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
MIN_RESUME_GAP_S = 10 * 60        # budget emergency 22:45Z: at most one non-filing resume per session per 10 min
AWAIT_EXPIRY_S = 30 * 60            # a no-op turn parks a session for this long at most (03:29Z deadlock: 0 live, 45 parked)
STUCK_AFTER = 3                     # consecutive no-effect turns -> stuck: run-end / new external events only
RESUME_STALL_S = 30 * 60            # RESUME-STALL: queued events but no RESUME for this long
WATCHDOG_MIN_STARTS = 3             # SA-2: alarm when this many starts in an hour produced no ready row
AUTO_START_COOLDOWN_S = 30 * 60     # SA-1: a handoff is not restarted within this long of its last end/start
MAX_STARTS_PER_HOUR = 10            # SA-1: global auto-start cap
STARVED_TICKS = 2                  # keeper ticks (~2 min each) a lane may sit free with zero candidates before INVENTORY-STARVED
STARVED_ALARM_EVERY_S = 30 * 60
PUSH_LOCK_DIR = os.path.join(ROOT, "coordination", "push-locks")
PUSH_LOCK_REPORT_EVERY_S = 10 * 60
CONTEXT_ROTATE_TOKENS = 150_000   # per-call input context above this -> fresh session at the next landed wrap-up (rotation)
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")
GENERALIST = bg.GENERALIST        # codex-gen: an ordinary dispatcher-managed, always-on session (no handoff; never yields)


def context_size(session_id, engine="codex"):
    """Per-call input context of a session = input_tokens of the LAST token_count event in its Codex rollout; None if unknown."""
    if engine != "codex" or not session_id:
        return None
    files = glob.glob(os.path.join(CODEX_SESSIONS, "*", "*", "*", f"rollout-*{session_id}*.jsonl"))
    if not files:
        return None
    last = None
    try:
        with open(max(files, key=os.path.getmtime), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400_000))
            for ln in f.read().decode(errors="replace").splitlines():
                if '"token_count"' in ln:
                    try:
                        d = json.loads(ln)
                        last = int((((d.get("payload") or {}).get("info") or {}).get("last_token_usage") or {}).get("input_tokens") or 0)
                    except ValueError:
                        pass
    except OSError:
        return None
    return last


def start_watchdog(flags, st, now, sessions=None):
    """SA-2: zero-token counters over the last hour - AUTO-STARTs and DONEs (dispatcher state) vs ready rows produced
    (dryrun/*/PASS.json mtime). Starts without any effect -> AUTO-START-NO-EFFECT alarm (once per hour)."""
    starts = [t for t in (st.get("starts") or []) if now - t < 3600]
    dones = [t for t in (st.get("dones") or []) if now - t < 3600]
    st["dones"] = dones
    produced = [p for p in glob.glob(os.path.join(flags, "dryrun", "*", "PASS.json")) if now - os.path.getmtime(p) < 3600]
    st["watchdog"] = {"starts_h": len(starts), "dones_h": len(dones), "ready_rows_h": len(produced), "at": now_iso()}
    if len(starts) >= WATCHDOG_MIN_STARTS and not produced and now - st.get("watchdog_alarm", 0) >= 3600:
        log(flags, f"AUTO-START-NO-EFFECT {len(starts)} auto-start(s) and {len(dones)} done(s) in the last hour produced 0 ready rows (dry-run PASS); "
                   f"the starts are not converting - check the real-row gate and the briefs")
        st["watchdog_alarm"] = now
    sess = (sessions or {}).values()
    last = max([_parse(e.get("last_resume") or "") for e in sess] or [0])
    refused = any(now - _parse(e.get("unwrapped_logged") or "") < RESUME_STALL_S for e in sess)
    if (st.get("queue") or refused) and now - last >= RESUME_STALL_S and now - st.get("resume_stall_alarm", 0) >= RESUME_STALL_S:
        log(flags, f"RESUME-STALL 0 RESUME events in the last {RESUME_STALL_S // 60} min while {len(st.get('queue') or [])} event(s) are queued"
                   f"{' and UNWRAPPED is refusing resumes' if refused else ''} - check the dispatcher gates (cap, cooldown, unwrapped lanes)")
        st["resume_stall_alarm"] = now
    return st["watchdog"]


def inventory_alarm(flags, st, data, now):
    """Governing objective: compute must be the ONLY bottleneck. A lane that the keeper reports free (IDLE-ALARM in the last
    5 min) with zero ready rows AND zero candidate rows for more than STARVED_TICKS ticks -> INVENTORY-STARVED <lane>,
    naming the 3 nearest-to-ready rows and their blockers. Logged at most every 30 min per lane."""
    if not data:
        return
    inv = data.get("inventory") or {}
    idle = {}
    for ts, b in data.get("klog_idle") or []:
        t = _parse(ts)
        if now - t <= 300:
            idle["gpu" if "gpu" in b else "cpu"] = True
    rows = [r for w in data["workers"].values() for r in w["rows"]]
    starved = st.setdefault("starved_since", {})
    for lane, v in inv.items():
        cands = [r for r in rows if r["lane"] == lane and r["state"] in bg.ADVANCEABLE]
        if v["ready"] == 0 and idle.get(lane) and not [r for r in cands if r["state"] == "needs-qualification"]:
            since = starved.setdefault(lane, now)
            if now - since >= STARVED_TICKS * 120 and now - st.get("starved_alarm", {}).get(lane, 0) >= STARVED_ALARM_EVERY_S:
                near = sorted(cands, key=lambda r: (bg.STATE_ORDER[r["state"]], float(r["rank"]) if str(r["rank"]).replace(".", "", 1).isdigit() else 999))[:3]
                desc = "; ".join(f"{r['id']} [{r['state']}] " + ("; ".join(r.get('reasons') or r.get('tasks') or [])[:120]) for r in near) or "no candidate rows at all"
                log(flags, f"INVENTORY-STARVED {lane}: free region, 0 ready rows, 0 publishable candidates for {int((now - since) / 60)} min; nearest-to-ready: {desc}")
                st.setdefault("starved_alarm", {})[lane] = now
        else:
            starved.pop(lane, None)


def dead_push_lock(flags, st, now):
    """Report (never release) a push lock whose holder pid is dead; it blocked every push for ~10 min tonight."""
    for p in glob.glob(os.path.join(PUSH_LOCK_DIR, "push-*.json")):
        d = bg.load_json(p) or {}
        pid = d.get("pid")
        if pid and not alive(pid) and now - st.get("push_lock_report", {}).get(p, 0) >= PUSH_LOCK_REPORT_EVERY_S:
            log(flags, f"PUSH-LOCK-DEAD {p}: holder {d.get('agent')} pid {pid} is dead since <= {d.get('acquired') or d.get('at') or '?'}; every push is blocked. "
                       f"NOT released automatically: `serialized_push.py --force-release {d.get('agent')}` is the operator's/holder's call.")
            st.setdefault("push_lock_report", {})[p] = now


TYPED_SHADOW_PORT = 8102          # worker_fast; the shadow runs only while this server answers (zero cost otherwise)


def typed_shadow(flags, slug, e, state, st, now, repo=None):
    """JEV-3 (shadow only, approved intake ws58-jev-20261102): a typed label beside work_state's heuristic, logged as
    TYPED-SHADOW; never drives behaviour. Skipped (no model call, no subprocess) unless worker_fast is listening."""
    probe = st.setdefault("typed_probe", {"at": 0, "up": False})
    if now - probe["at"] > 300:
        import socket
        try:
            with socket.create_connection(("127.0.0.1", TYPED_SHADOW_PORT), timeout=0.3):
                probe.update(at=now, up=True)
        except OSError:
            probe.update(at=now, up=False)
    if not probe["up"]:
        return
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "churn"))
        import typed_shadow as ts
        b = open(os.path.join(flags, f"BACKLOG-handoff-{slug}.md")).read() if os.path.exists(os.path.join(flags, f"BACKLOG-handoff-{slug}.md")) else ""
        sh = ts.classify_work_state(b, open_tasks(e.get("handoff", ""), repo))
        label = sh["label"].value if sh.get("label") is not None else None
        reason = sh["stop_reason"].value if sh.get("stop_reason") is not None else None
        log(flags, f"TYPED-SHADOW {slug}: heuristic={state} typed={label} reason={reason} source={sh['source']}"
                   + ("" if label is None or label == state else " DISAGREE"))
    except Exception as ex:  # shadow never breaks the dispatcher
        log(flags, f"TYPED-SHADOW {slug}: unavailable ({ex!r})")


def is_generalist(e) -> bool:
    return bool(e.get("generalist")) or not e.get("handoff")


def ensure_generalist(reg):
    """codex-gen is a managed session like any other: same events, NOOP gate, lane h-codex-gen, window agent:h-codex-gen."""
    S = reg.setdefault("sessions", {})
    if GENERALIST not in S:
        S[GENERALIST] = {"handoff": None, "generalist": True, "engine": reg.get("default_engine", "codex"), "session_id": None,
                         "status": "suspended", "pid": None, "row_ids": [], "row_patterns": [], "handoff_rows": [], "waits_on": []}
    return S[GENERALIST]


def work_state(flags, slug, e, repo=None) -> tuple[str, str]:
    """('continue'|'pause'|'done', reason) from BACKLOG-handoff-<slug>.md + the handoff's open boxes."""
    try:
        b = open(os.path.join(flags, f"BACKLOG-handoff-{slug}.md")).read()
    except OSError:
        b = ""
    if is_generalist(e):  # codex-gen: its backlog is BACKLOG-codex-gen.md; never done, pauses only on an empty backlog
        try:
            b = open(os.path.join(flags, f"BACKLOG-{GENERALIST}.md")).read()
        except OSError:
            b = ""
        adv = ADV_RX.findall(b)
        nf = re.findall(r"^- \[needs-filing\] ", b, re.M)
        ni = (b.split("## Non-inference", 1)[1] if "## Non-inference" in b else "").split("\n## ", 1)[0]
        ntasks = len([l for l in ni.splitlines() if l.startswith("- [")])
        if adv or nf or ntasks:
            return "continue", f"codex-gen backlog: {len(adv)} row fix(es), {len(nf)} filing(s), {ntasks} small task(s)"
        return "pause", "codex-gen backlog empty (resumed when backlog_gen adds an eligible item or an event arrives)"
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
    """(rid, path, kind): grant ends and dry-run results (CAF-1: the dispatcher, not the session, watches these files)."""
    for p in glob.glob(os.path.join(flags, "grants", "*.ended")) + glob.glob(os.path.join(flags, "grants", "*.complete")):
        yield os.path.basename(p).rsplit(".", 1)[0], p, "run-end"
    cutoff = time.time() - DRYRUN_EVENT_MAX_AGE_S
    for p in glob.glob(os.path.join(flags, "dryrun", "*", "PASS.json")) + glob.glob(os.path.join(flags, "dryrun", "*", "FAIL-*.json")):
        try:
            if os.path.getmtime(p) < cutoff:
                continue  # historic result: the backlog already carries it as the row's fix task; no resume storm on (re)start
        except OSError:
            continue
        yield os.path.basename(os.path.dirname(p)), p, "dryrun"


def awaiting_events(flags, slug):
    """Files the session registered under handoff-sessions/<slug>/awaiting/<name>.json ({"path": ..., "note": ...}) that now
    exist. The registration is consumed (renamed .fired) when the event is queued."""
    for p in glob.glob(os.path.join(flags, "handoff-sessions", slug, "awaiting", "*.json")):
        d = bg.load_json(p) or {}
        if not d.get("path") or not os.path.exists(str(d["path"])):
            continue
        try:  # a file that already existed when it was registered is a poll in disguise (118 AWAITED resumes/h): not an event
            if os.path.getmtime(str(d["path"])) <= os.path.getmtime(p) and not d.get("allow_existing"):
                os.replace(p, p + ".preexisting")
                continue
        except OSError:
            continue
        yield d, p


def dryrun_prompt(slug, e, flags, rid, path):
    d = bg.load_json(path) or {}
    verdict = "PASS" if os.path.basename(path) == "PASS.json" else "FAIL"
    return f"""[{VERSION}] Dry-run {verdict} for your row `{rid}` ({path}). {FANOUT_LINE} {lane_line(slug)}
Record: {json.dumps(d)[:900]}
{"The row is grantable; publish your NEXT row now (inference first), then wrap up." if verdict == "PASS" else
 "Fix task: " + str(d.get("fix_task") or d.get("reason"))[:400] + " -> fix the launcher/spec in your lane, re-publish (publish_row.py), then wrap up."}
Print `WRAPPED <sha>` as your LAST line.""".replace("\n\n", "\n")


def awaiting_prompt(slug, e, flags, data):
    items = data if isinstance(data, list) else [data]
    lines = "\n".join(f"- {d.get('path')} ({d.get('note') or 'no note'})" for d in items)
    return f"""[{VERSION}] {len(items)} file(s) you were waiting for now exist:
{lines}
{FANOUT_LINE} {lane_line(slug)}
Consume ALL of them in this one turn, continue your task, wrap up; print `WRAPPED <sha>` as your LAST line."""


def dispatch_once(flags, runner=None, now=None, seed=False, repo=None, priority=None, keeper_log=None):
    now = now or time.time()
    repo = repo or ROOT
    reg = load(reg_path(flags), {"sessions": {}})
    st = load(state_path(flags), {"seen": [], "queue": []})
    seen = set(st.get("seen") or [])
    pilots = bg.load_pilots(reg_path(flags))
    ensure_generalist(reg)
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
            rep = turn_report(flags, slug, e)  # DSH-1: structured record first, transcript regex as the fallback
            m = WRAPPED_RX.findall(tailtxt)
            if rep and re.fullmatch(r"[0-9a-f]{7,40}", str(rep.get("wrapped_sha") or "")):
                e["last_wrapup"] = rep["wrapped_sha"]
            elif m:
                e["last_wrapup"] = m[-1]
            if e.get("last_wrapup"):
                e["dirty_wrap_resume"] = None
            e["last_report"] = {k: rep.get(k) for k in ("state", "wrapped_sha", "question", "rows_published")} if rep else None
            effect = turn_effect(flags, slug, e, rep)
            if not effect:  # unlanded progress in a clean lane is landed HERE at zero token cost, then counted
                landed_now = land_lane(e.get("cwd") or "")
                if landed_now:
                    n = sum(landed_ticks(x) for x in landed_now)
                    e["last_wrapup"] = e.get("last_wrapup") or landed_now[-1]
                    log(flags, f"LANDED-BY-DISPATCHER {slug}: {len(landed_now)} commit(s) from a clean lane, {n} tick(s)")
                    if n:
                        effect = f"{n} tick(s) landed by the dispatcher"
            if not effect:  # no landed tick, no row, no filing: pure spend
                e["noop_turns"], e["await_event"] = int(e.get("noop_turns", 0)) + 1, True
                log(flags, f"NOOP {slug}: turn completed nothing (no landed tick, no row published, no filing) [{e['noop_turns']}/{STUCK_AFTER}]")
                if e["noop_turns"] >= STUCK_AFTER and not e.get("stuck"):
                    why = (rep or {}).get("question") or (rep or {}).get("state") or e.get("idle_reported") or e.get("work_reason") or "no report.json reason"
                    e["stuck"] = f"{e['noop_turns']} consecutive turns without a landed tick, row or filing; last report: {str(why)[:200]}"
                    log(flags, f"STUCK {slug}: {e['stuck']}; resumed only on a run-end or a new external event")
            else:
                e["noop_turns"], e["await_event"], e["noop_reason"], e["stuck"] = 0, False, None, None
                e["last_effect"] = effect
            if "FRESH-SESSION-REQUESTED" in tailtxt:
                e["fresh_next"] = True
            e["context_tokens"] = context_size(e.get("session_id"), e.get("engine", "codex"))
            if (e["context_tokens"] or 0) > CONTEXT_ROTATE_TOKENS and not e.get("fresh_next"):  # context rotation
                e["fresh_next"] = True
                e["rotated_from"] = {"session_id": e.get("session_id"), "context_tokens": e["context_tokens"], "at": now_iso()}
                log(flags, f"ROTATE {slug}: per-call context {e['context_tokens']} > {CONTEXT_ROTATE_TOKENS}; next resume is a FRESH session from brief + state delta")
            mi = IDLE_RX.findall(tailtxt)
            e["idle_reported"] = (rep.get("question") or "idle") if rep and rep.get("state") == "idle" else (mi[-1][:200] if mi else None)
            ev, e["pid"], e["last_end"], e["last_rc"] = e.get("pending_event"), None, now_iso(), last_rc(e)
            e["pending_event"] = None
            wrapped_now = bool(e.get("last_wrapup")) and (bool(m) or bool(rep and rep.get("wrapped_sha")))
            if ev and not filed(flags, ev["rid"]):  # DSH-2: a run-end is acked by the FILED receipt, not by the turn ending
                n = int(ev.get("redelivered", 0)) + 1
                if n <= MAX_REQUEUE:
                    st.setdefault("queue", []).insert(0, dict(ev, redelivered=n))
                    log(flags, f"REQUEUE {ev['rid']} -> {slug}: turn ended without filing-done/{ev['rid']}.FILED (redelivery {n}/{MAX_REQUEUE})")
                else:
                    log(flags, f"ESCALATE {ev['rid']} -> {slug}: no FILED receipt after {MAX_REQUEUE} redeliveries; "
                               f"{escalate_filing(flags, slug, ev)}")
            transient = (e["last_rc"] not in (None, 0)) and not wrapped_now and not any(USAGE_RX.search(ln) for ln in errs) \
                and any(TRANSIENT_RX.search(ln) for ln in (errs or tailtxt.splitlines()[-20:]))
            if transient:  # DSH-3
                n = int(e.get("transient_retries", 0)) + 1
                if n <= len(TRANSIENT_BACKOFF_S):
                    e["transient_retries"], e["status"] = n, "retry"
                    e["retry_at"] = _dt.datetime.fromtimestamp(now + TRANSIENT_BACKOFF_S[n - 1], _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    e["retry_error"] = (errs or tailtxt.splitlines()[-1:] or [""])[-1][:200]
                    log(flags, f"TRANSIENT {slug}: rc={e['last_rc']} retry {n}/{len(TRANSIENT_BACKOFF_S)} at {e['retry_at']}: {e['retry_error']}")
                else:
                    e["status"], e["failed"] = "failed", f"{n - 1} transient retries exhausted (rc={e['last_rc']})"
                    log(flags, f"FAILED {slug}: {e['failed']}; shown in the backlog")
            elif e.get("last_wrapup") and not landed(e.get("last_wrapup")):
                e["status"] = "unpushed"  # a WRAPPED sha exists but is not on origin/main: PUSH_PROMPT
                log(flags, f"UNPUSHED {slug} wrapup={e.get('last_wrapup')}: resuming to push")
            else:
                e["status"], e["push_retries"], e["transient_retries"] = "suspended", 0, 0
            log(flags, f"TURN-END {slug} session={e.get('session_id')} rc={e.get('last_rc')} wrapup={e.get('last_wrapup')}")
    # 2. new run ends owned by a pilot
    for rid, p, kind in end_events(flags):
        key = os.path.basename(p) if kind == "run-end" else f"dryrun/{rid}/{os.path.basename(p)}"
        if key in seen:
            continue
        seen.add(key)
        if seed:
            continue
        slug = bg.pilot_of(pilots, rid, None, manifest_for(flags, rid)[1].get("handoff"))
        if (not slug or slug not in S) and GENERALIST in S:  # ownerless row: the dispatcher files it, else codex-gen does
            if kind == "run-end" and not filed(flags, rid):
                rc, out = file_result(flags, rid, lane_dir(GENERALIST))
                if rc == 0:
                    log(flags, f"FILED-BY-SCRIPT {rid} (no owner): {out.strip().splitlines()[0][:160] if out.strip() else ''}")
                    continue
                log(flags, f"ORPHAN {rid} -> {GENERALIST}: file_result rc={rc}")
            slug = GENERALIST
        if slug and slug in S:
            if kind == "run-end" and any(ev["slug"] == slug and ev["rid"] == rid for ev in st.get("queue") or []):
                log(flags, f"DEDUPE {rid} -> {slug}: a run-end for this row is already queued; dropped {key}")  # CAF-6
                continue
            st.setdefault("queue", []).append({"slug": slug, "rid": rid, "end": p, "kind": kind,
                                               "related": {k: v for k, v in related_ids(flags, rid).items() if k in ("handoff_task", "lineage", "prior_fail", "manifest")}})
            S[slug]["await_event"], S[slug]["noop_reason"], S[slug]["dirty_wrap_resume"] = False, None, None
            if kind == "run-end":
                S[slug]["stuck"] = None  # a run-end is the external event that unsticks a session
            log(flags, f"{'RUN-END' if kind == 'run-end' else 'DRYRUN-RESULT'} {rid} -> {slug}")
    for slug, e in S.items():  # CAF-1: files a session registered as awaited - ALL fired files of a slug ride in ONE event
        fired = []
        for d, reg_file in awaiting_events(flags, slug):
            os.replace(reg_file, reg_file + ".fired")
            fired.append(dict(d, registration=reg_file))
        if not fired:
            continue
        ev = next((x for x in st.get("queue") or [] if x["slug"] == slug and x.get("kind") == "awaiting"), None)
        if ev:
            prev = ev.get("data") or []
            ev["data"] = ([prev] if isinstance(prev, dict) else list(prev)) + fired  # coalesce: 15 awaited files, ONE turn
        else:
            st.setdefault("queue", []).append({"slug": slug, "rid": f"awaiting-{len(fired)}", "end": fired[0]["registration"] + ".fired",
                                               "kind": "awaiting", "data": fired})
        e["await_event"], e["noop_reason"], e["dirty_wrap_resume"] = False, None, None
        log(flags, f"AWAITED {len(fired)} file(s) -> {slug}: " + ", ".join(str(d.get("path")) for d in fired)[:300])
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
        if e.get("status") == "done" or alive(e.get("pid")) or (not e.get("handoff") and not is_generalist(e)):
            continue
        ws, why = work_state(flags, slug, e, repo)
        e["_work"] = (ws, why)
        if not is_generalist(e):
            typed_shadow(flags, slug, e, ws, st, now, repo)
        if ws == "done":
            e["status"], e["done_at"] = "done", now_iso()
            kill_window(slug)
            remove_lane(flags, slug, repo)
            st.setdefault("dones", []).append(now)
            log(flags, f"DONE {slug}: {why}; slot freed; tmux window {window_name(slug)} killed")
        else:
            idle_window = ws == "pause" or bool(e.get("yield"))  # operator: no window clutter while paused/yielded
            if idle_window and tmux_has_window(slug):
                kill_window(slug)
                log(flags, f"STATE {slug}: {'paused' if ws == 'pause' else 'yielded'} - {why}; tmux window {window_name(slug)} killed "
                           f"(last turn: {e.get('last_output')})")
            if e.get("work_state") != ws or e.get("work_reason") != why:
                log(flags, f"{'PAUSE' if ws == 'pause' else 'OPEN'} {slug}: {why}")
            if e.get("await_event") and not e.get("noop_reason"):
                e["noop_reason"] = why  # the backlog as it was when the no-op turn ended; a changed backlog is an event
        e["work_state"], e["work_reason"] = ws, why
    try:  # CAF-3: one backlog build per pass; its per-slug delta rides in every resume prompt instead of a re-read
        _, bdata = candidates(flags, reg, repo, priority, keeper_log)
    except Exception as ex:
        bdata = None
        log(flags, f"DELTA-SKIPPED {ex!r}")

    def delta(slug):
        try:
            return bg.resume_delta(bdata, slug) if bdata else ""
        except Exception:
            return ""
    inventory_alarm(flags, st, bdata, now)
    dead_push_lock(flags, st, now)
    start_watchdog(flags, st, now, S)
    reap_lanes(flags, reg, repo)
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
        for slug, e in S.items():  # DSH-3: "go on" after the backoff
            if e.get("status") == "retry" and not alive(e.get("pid")) and e.get("session_id") and live < cap \
                    and now >= _parse(e.get("retry_at") or ""):
                _go(flags, slug, e, GO_ON_PROMPT.format(v=VERSION, rc=e.get("last_rc"), err=e.get("retry_error"), n=e.get("transient_retries")), runner, e.get("pending_event"))
                launched.add(slug)
                live += 1
        for ev in q:
            e = S.get(ev["slug"])
            if not e or e.get("status") == "done":
                continue
            if alive(e.get("pid")) or live >= cap + FILING_SLOTS or not e.get("session_id"):  # DSH-4: filing never queues behind auto-start
                rest.append(ev)
                continue
            if e.get("stuck") and ev.get("kind") in ("awaiting", "dryrun"):
                continue  # stuck: its own awaited/dry-run events are dropped; only a run-end or a new external event resumes it
            if ev.get("kind") == "dryrun" and not e.get("last_effect") and now - _parse(e.get("last_resume") or "") < MIN_RESUME_GAP_S:
                rest.append(ev)  # not a filing event: wait for the gap (the next resume carries it with everything else)
                continue
            if not wrapped(e, lcache):  # 2026-11-01 ruling: no new work on an unwrapped session; keep the event
                e["pending_event"] = ev
                rest.append(ev)
                log_unwrapped(flags, ev["slug"], e)
                continue
            if ev.get("kind") == "dryrun":
                pr = dryrun_prompt(ev["slug"], e, flags, ev["rid"], ev["end"])
            elif ev.get("kind") == "awaiting":
                pr = awaiting_prompt(ev["slug"], e, flags, ev.get("data") or {})
            else:
                filing = None if filed(flags, ev["rid"]) else file_result(flags, ev["rid"], e.get("cwd") or lane_dir(ev["slug"]))
                if filing and filing[0] == 0:
                    log(flags, f"FILED-BY-SCRIPT {ev['rid']} -> {ev['slug']}: {filing[1].strip().splitlines()[0][:160] if filing[1].strip() else ''}")
                pr = end_prompt(ev["slug"], e, flags, ev["rid"], ev["end"], delta(ev["slug"]), filing)
            _go(flags, ev["slug"], e, pr, runner, ev if ev.get("kind") in (None, "run-end") else None)
            launched.add(ev["slug"])
            live += 1
        st["queue"] = rest
        for slug, e in S.items():  # continue: anything open that is not waiting on a queued/running row
            if (live >= cap and not is_generalist(e)) or e.get("status") in ("done", "retry", "failed") or alive(e.get("pid")) \
                    or (e.get("_work") or ("", ""))[0] != "continue":
                continue
            if not e.get("last_effect") and now - _parse(e.get("last_resume") or "") < MIN_RESUME_GAP_S:
                continue  # gap only after a turn that produced nothing (ws58 23:30Z: the gap throttled productive sessions to 0 alive)
            if slug in launched or any(ev["slug"] == slug for ev in st["queue"]):
                continue
            if e.get("yield"):
                continue  # outranked: no new work; its slot goes to a higher-ranked handoff
            if e.get("stuck"):
                continue  # 3 no-effect turns: only a run-end (or a new external event) resumes it
            if e.get("await_event") and e.get("work_reason") == e.get("noop_reason") \
                    and now - _parse(e.get("last_end") or "") < AWAIT_EXPIRY_S:
                continue  # last turn was a no-op and nothing changed since: wait for an event (or 30 min), not another re-check
            if e.get("idle_reported") and now - _parse(e.get("last_end") or "") < IDLE_REPORT_COOLDOWN_S:
                continue  # the session itself said IDLE: <reason>; re-asked after the cooldown
            if not wrapped(e, lcache):
                log_unwrapped(flags, slug, e)
                continue
            fresh = bool(e.get("fresh_next")) or not e.get("session_id")
            _go(flags, slug, e, (brief_text(slug, e, flags) + "\n" if fresh else "") + continue_prompt(slug, e, flags, e["_work"][1], delta(slug)),
                runner, None, fresh)
            live += 1
        # 5. AUTO-START: fill the remaining slots with the best handoffs that have no session yet
        live = auto_start(flags, reg, live, cap, runner, repo, priority, keeper_log, bdata)
        S = reg["sessions"]
    for e in S.values():
        e.pop("_advanceable", None)
        e.pop("_work", None)
    st["seen"] = sorted(seen)
    reg["dispatcher"] = {"version": VERSION, "last_pass": now_iso(), "live": live, "paused": paused}
    save(reg_path(flags), reg)
    save(state_path(flags), st)
    return reg, st


def land_lane(cwd):
    """Land a CLEAN lane's unlanded commits (fetch, rebase onto origin/main, serialized_push --agent dispatcher).
    Returns the list of shas that were unlanded before (now landed) or [] when nothing was landed."""
    if not cwd or not os.path.isdir(cwd):
        return []
    try:
        dirty = subprocess.run(["git", "-C", cwd, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, timeout=60).stdout.strip()
        ahead = [l[2:].strip() for l in subprocess.run(["git", "-C", cwd, "cherry", "origin/main"], capture_output=True, text=True, timeout=60).stdout.splitlines() if l.startswith("+")]
        if dirty or not ahead:
            return []
        subprocess.run(["git", "-C", cwd, "fetch", "-q", "origin"], timeout=120)
        if subprocess.run(["git", "-C", cwd, "rebase", "-q", "origin/main"], timeout=120).returncode != 0:
            subprocess.run(["git", "-C", cwd, "rebase", "--abort"], timeout=60)
            return []
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts/coordination/serialized_push.py"), "--agent", "dispatcher",
                        "--repo", cwd, "--fetch", "--push"], capture_output=True, timeout=600)
        still = subprocess.run(["git", "-C", cwd, "cherry", "origin/main"], capture_output=True, text=True, timeout=60).stdout
        if "+" in still:
            return []
        head = subprocess.run(["git", "-C", cwd, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=60).stdout.strip()
        return [head] if head else []
    except (OSError, subprocess.TimeoutExpired):
        return []


def log_unwrapped(flags, slug, e):
    """UNWRAPPED is logged at most once per 10 min per session (1293 lines in an hour were log spam, not information)."""
    if time.time() - _parse(e.get("unwrapped_logged") or "") > 600:
        e["unwrapped_logged"] = now_iso()
        log(flags, f"UNWRAPPED {slug}: refusing resume for new work; last_wrapup={e.get('last_wrapup')} lane={e.get('cwd')}")


def wrapped(e, cache=None) -> bool:
    """Gate for resuming a session with NEW work: its last `WRAPPED <sha>` must be on origin/main.
    A session that never ran a turn (no session_id, no last_end) has nothing to have wrapped and passes."""
    lw = e.get("last_wrapup")
    if not lw:
        if not e.get("session_id") and not e.get("last_end"):
            return True
        # ws58 2026-11-01: a session that never printed WRAPPED but left nothing unlanded (clean lane, empty cherry) has
        # nothing to wrap; refusing it deadlocked codex-gen and others (104 UNWRAPPED refusals, no rows published).
        cwd = e.get("cwd") or ""
        if not cwd.startswith(LANES_DIR + "/"):
            return False
        if not os.path.isdir(cwd):
            return True  # the lane was reaped: that only happens when it was clean and landed, so nothing is unwrapped
        try:
            dirty = subprocess.run(["git", "-C", cwd, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, timeout=60).stdout.strip()
            ahead = subprocess.run(["git", "-C", cwd, "cherry", "origin/main"], capture_output=True, text=True, timeout=60).stdout
        except (OSError, subprocess.TimeoutExpired):
            return False
        if dirty and not e.get("dirty_wrap_resume"):
            e["dirty_wrap_resume"] = now_iso()  # a dirty lane gets ONE wrap-up resume (its prompt ends with wrapup.py); then refused
            return True
        if not dirty and "+" in ahead:
            if land_lane(cwd):  # ws58 23:46Z: a clean lane's unlanded commit is landed here instead of refusing forever
                ahead = ""
        return not dirty and "+" not in ahead
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
    if fresh:  # a fresh session (auto-start, rotation, generalist) always has its brief file on disk
        bd = os.path.join(flags, "briefs")
        os.makedirs(bd, exist_ok=True)
        e["brief"] = os.path.join(bd, f"HANDOFF-{slug}.md")
        bg.write_atomic(e["brief"], brief_text(slug, e, flags))
    r = _git(lane, "rev-parse", "HEAD")
    e["head_at_resume"] = r.stdout.strip() if r.returncode == 0 else None
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
