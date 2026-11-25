#!/usr/bin/env python3
"""taskflow/harness/codex.py — the `codex` lane type of the deterministic dispatcher (PM-CODEX-DISPATCH-DETERMINISTIC).

    python3 scripts/coordination/taskflow/dispatch.py codex [--file F.md ...] [--max-boxes N] [--apply] [--dry-run]

Routes backlog boxes to UNASSISTED Codex lanes with no Claude driver (operator 2026-11-25: the unassisted bar is met).
Selection, prompt, lane drive, verdict, tick and kill switch are all deterministic; no LLM is called here except the
Codex lane itself (through codex_lane/drive.py, which resumes the one-shot `codex exec` thread until its own
artifact verdict says stop).

ELIGIBLE (codex_skip() returns None) only when ALL hold: box_index.skip_reason() admits it (open, not frozen /
needs-owner / proposal / roll-up, holds.yaml targets nothing on it, every gate resolved, lint ok, not NEEDS-BRIEF), no
unresolved gate ref, class `non-inference`, an ID, a `· done when:`, a brief file (handoffs/active/briefs/<ID>.md, state
not none/orphaned), no `operator-decision` anywhere on the box, still open at origin/main, and never attempted before
by this dispatcher (run ledger). One box per handoff file per run.

DONE is judged ONLY from artifacts (judge()): the report's first line `LANE-STATUS: DONE`, a `<ID> <repo> <branch>
<sha>` line for THIS box whose commit exists, is on its branch, is reachable from origin/main after a fetch, and is NEW
(not reachable from origin/main at dispatch start); a `PUSH VERIFIED` line; and the report's `TEST:` command (a pytest
invocation) re-run BY THE DISPATCHER, pinned to cores 84-87, in a detached worktree at origin/main, exiting 0. The
lane's own DONE text is never enough. Anything else -> a `· NEEDS-OWNER: <date> codex lane <lane>: <why>` continuation
line on the box (box_index then reads it as needs-owner, so select skips it) pushed via serialized_push, and the ledger
records the attempt, so a box is NEVER retried automatically.

With --apply a verified DONE is ticked via churn/wrapup.py (`[no-belief: software]`); a refused tick (machine
done-when) is recorded in the ledger and the box stays open. Without --apply nothing is ticked or tagged (the lane still
runs and pushes its own work). --dry-run prints the selection and runs nothing.

Concurrency: ONE Codex lane at a time (MAX_CODEX_LANES, a constant; lanes run sequentially in one process, and a run
lock refuses a second dispatcher). Every lane and every dispatcher test re-run is pinned: taskset -c 84-87, nice 19,
ionice -c3. Kill switch: `<out>/STOP` is checked before every lane and between resume rounds is honoured by not
starting the next lane. Ledger: `<out>/ledger.jsonl`, one JSON line per lane.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
from codex_lane import drive as D  # noqa: E402  (the artifact verdict + resume loop; one copy)

MAX_CODEX_LANES = 1                      # one Codex lane at a time (operator 2026-11-25)
CORES = "84-87"
PIN = ["taskset", "-c", CORES, "nice", "-n", "19", "ionice", "-c3"]
OUT_DEFAULT = Path(os.environ.get("CODEX_DISPATCH_OUT", "/mnt/raid0/llm/tmp/codex-dispatch"))
WT_ROOT = Path(os.environ.get("CODEX_DISPATCH_WT_ROOT", "/mnt/raid0/llm/worktrees"))
DEFAULT_FILES = ("handoffs/active/churn-pipeline.md", "handoffs/active/coordination-and-churn-pipeline.md")
MAX_ROUNDS = 10
TEST_TIMEOUT_S = 1800
AGENT = "pipeline-mgmt"
WRAPUP_SLUG = "codex-dispatch"
BRIEF_OK = ("unverified", "fresh", "drift", "stale")     # a brief file exists for this ID (none / orphaned do not count)
_OPDEC = re.compile(r"operator[- ]decision", re.I)
_TEST_LINE = re.compile(r"^\s*TEST:\s*(.+?)\s*$", re.M)
_WRAP = re.compile(r"^(?:nice\s+-n\s+-?\d+|taskset\s+-c\s+[\d,-]+|ionice\s+-c\s*\d+|env\s+\w+=\S+|\w+=\S+)\s+")

COMMON = """
How to work (UNASSISTED lane: you finish the job yourself; other measurement runs on this host, so stay off their cores):
- Work ONLY in your worktree {wt} (branch {lane}, upstream origin/main), which the dispatcher already created as a
  sparse checkout without artifacts/, benchmarks/ and data/. Do not create another one, do not change its sparse set,
  and never edit /workspace or any other worktree. The dispatcher removes it after it verifies your work.
- Run EVERY test command pinned and niced: `nice -n 19 taskset -c 84-87 python3 -m pytest -q -p no:cacheprovider <files>`.
  No other heavy commands. No builds, servers, models or benchmarks. Take NO rowflow claim.
- Never touch /mnt/raid0/llm/tmp/compute-flags (live keeper state). Never start, stop or kill any process. Never deploy.
- Commit with the trailers {trailers}and `Co-Authored-By: Codex <noreply@openai.com>`{envack}.
- Rebase onto a fresh origin/main, re-run your tests, then push with
  `python3 /workspace/scripts/coordination/serialized_push.py --agent {agent} --repo {wt} --push`. The output must say
  PUSH VERIFIED. If a push is refused, fix the cause; never force.
- Don't touch: holds.yaml, agents/shared, CLAUDE.md, artifacts/operator, filler_run15.sh, scripts/hooks/. No
  force-push, no git prune, gc, stash or reset in shared clones. Do not tick boxes and do not edit handoffs/ (the
  dispatcher ticks after it verifies your work).
- If the task text cites code that has moved, design for the CURRENT code. If the work turns out to be already done on
  origin/main, say so as a BLOCKED line (the dispatcher only counts a NEW commit).

Done means your tests pass AND your new commit is on origin/main (PUSH VERIFIED). Then write {report} with EXACTLY:
  line 1: `LANE-STATUS: DONE`
  line 2: `{box} {repo} {lane} <full sha>`
  line 3: `TEST: <the exact pytest command you ran>` (the dispatcher re-runs it from the repo root on origin/main)
  line 4: the pass count, then the PUSH VERIFIED line copied from serialized_push.
Only if a concrete external blocker stops you, make line 1 `LANE-STATUS: BLOCKED <file/command/error>`.
"""


# ------------------------------------------------------------------------------------------------ small helpers
def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(repo, *a, timeout=600) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, timeout=timeout)


def read_ledger(out: Path) -> list[dict]:
    p = out / "ledger.jsonl"
    rows = []
    if p.exists():
        for ln in p.read_text(errors="replace").splitlines():
            try:
                rows.append(json.loads(ln))
            except ValueError:
                continue
    return rows


def write_ledger(out: Path, row: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "ledger.jsonl").open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def attempted(out: Path) -> set[str]:
    """Box IDs this dispatcher already ran a lane for (any verdict): never retried automatically."""
    return {r["box"] for r in read_ledger(out) if r.get("box") and r.get("lane")}


def stopped(out: Path) -> bool:
    return (out / "STOP").exists()


# --------------------------------------------------------------------------------------------------- eligibility
def brief_path(root: Path, bid: str) -> Path:
    return root / "handoffs" / "active" / "briefs" / f"{bid}.md"


def codex_skip(rec: dict, root: Path, done_ids: set[str] = frozenset(), base_state=None) -> str | None:
    """Why this box is NOT eligible for a Codex lane, or None. `base_state(rec)` -> open|ticked|gone|None at origin/main."""
    sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
    try:
        import box_index
    finally:
        sys.path.pop(0)
    why = box_index.skip_reason(rec)
    if why:
        return why
    if rec.get("state") != "open" or rec.get("frozen_until"):
        return "frozen"
    if rec.get("needs_owner"):
        return "needs-owner"
    if rec.get("holds"):
        return "held"
    if rec.get("gate_open") or rec.get("gate_unknown"):
        return "gated"
    if rec.get("class") != "non-inference":
        return f"class-{rec.get('class')}"
    bid = rec.get("id")
    if not bid:
        return "no-id"
    if not str(rec.get("done_when") or "").strip():
        return "no-done-when"
    if rec.get("brief") not in BRIEF_OK or not brief_path(root, bid).is_file():
        return "no-brief"
    if _OPDEC.search(" ".join(str(rec.get(k) or "") for k in ("text", "done_when", "class"))):
        return "operator-decision"
    if bid in done_ids:
        return "attempted-before"
    if base_state is not None:
        st = base_state(rec)
        if st in ("ticked", "gone"):
            return f"box-{st}-at-origin"
        if st == "landed":
            return "acceptance-already-passes"
    return None


def select(doc: dict, root: Path, files=DEFAULT_FILES, done_ids: set[str] = frozenset(), n: int = 3,
           base_state=None) -> tuple[list[tuple[str, dict]], dict]:
    """(chosen [(key, rec)] in select.py order, skip histogram). One box per handoff file per run is NOT enforced:
    the lanes are sequential, so a second box of the same file starts after the first one landed."""
    from taskflow import select as S
    hist: dict[str, int] = {}
    out = []
    if doc.get("boxes") and not doc.get("holds_source"):
        return [], {"holds-source-missing": len(doc["boxes"])}           # C3: fail closed
    for key, rec in sorted((doc.get("boxes") or {}).items(), key=S.order_key):
        if files and rec.get("file") not in files:
            continue
        why = codex_skip(rec, root, done_ids, base_state if len(out) < n else None)
        if why is None and len(out) >= n:
            why = "over-limit"
        hist[why or "chosen"] = hist.get(why or "chosen", 0) + 1
        if why is None:
            out.append((key, rec))
    return out, hist


_DW_PYTEST = re.compile(r"^\s*`?(?:python3 -m )?pytest\s+((?:[\w./-]+\.py(?:::\w+)?\s*)+)")


def done_when_tests(rec: dict) -> list[str] | None:
    """A done-when that is a pytest acceptance (`pytest <files> passes ...`) -> pytest argv, else None."""
    m = _DW_PYTEST.match(str(rec.get("done_when") or ""))
    return [sys.executable, "-m", "pytest", "-q", *m.group(1).split()] if m else None


def already_done(rec: dict, repo: Path, rerun=None) -> bool:
    """Stale-packet check (taskflow r8c fix 3) before any Codex call: the box's pytest acceptance already passes on
    origin/main -> the work landed and only the tick is missing; a lane could only report no new commit."""
    argv = done_when_tests(rec)
    if not argv:
        return False
    return (rerun or rerun_test)(repo, argv, f"cxd-pre-{rec['id'].lower()}-{int(time.time())}")[0] == 0


def origin_box_state(rec: dict, repo: Path) -> str | None:
    r = git(repo, "show", f"origin/main:{rec['file']}", timeout=60)
    if r.returncode != 0:
        return None
    state = "gone"
    for ln in r.stdout.splitlines():
        m = re.match(r"\s*[-*] \[(.)\] \*\*" + re.escape(rec["id"]) + r"\*\*", ln)
        if m:
            return "open" if m.group(1) not in "xX" else "ticked"
    return state


# -------------------------------------------------------------------------------------------------------- prompt
def lane_name(bid: str, stamp: str) -> str:
    return "cxd-" + re.sub(r"[^a-z0-9]+", "-", bid.lower()).strip("-")[:40] + "-" + stamp


def build_prompt(rec: dict, root: Path, lane: str, report: Path, repo: str = "/workspace",
                 trailers: list[str] = (), env_ack: str = "") -> str:
    brief = brief_path(root, rec["id"]).read_text(errors="replace")
    tr = "".join(f"`{t}` " for t in trailers)
    tr = (tr + "and ") if tr else ""
    envack = f", with env `EPYC_D9_ACK=\"{env_ack}\"`" if env_ack else ""
    body = (f"Task {rec['id']} (handoff {rec['file']}:{rec['line']}).\n\n"
            f"Box text:\n{rec['text'].strip()}\n\n"
            f"Done when: {rec['done_when'].strip()}\n\n"
            f"Brief ({brief_path(root, rec['id']).relative_to(root)}):\n{brief.strip()}\n")
    return body + COMMON.format(repo=repo, wt=WT_ROOT / f"{lane}-wt", lane=lane, trailers=tr, envack=envack,
                                agent=AGENT, report=report, box=rec["id"])


# ------------------------------------------------------------------------------------------------------- verdict
def test_cmd(text: str) -> list[str] | None:
    """The report's `TEST:` command as argv, wrappers (nice/taskset/ionice/env VAR=) stripped, or None when it is not a
    pytest invocation (the dispatcher re-runs ONLY pytest; anything else is not a verifiable done)."""
    m = _TEST_LINE.search(text or "")
    if not m:
        return None
    cmd = m.group(1).strip().strip("`")
    cmd = re.split(r"\s+[—-]{1,2}\s+\d+\s+passed", cmd)[0].strip()
    while True:
        s = _WRAP.sub("", cmd, count=1)
        if s == cmd:
            break
        cmd = s
    if re.search(r"[;&|<>`$]", cmd):
        return None
    argv = shlex.split(cmd)
    if argv[:3] == ["python3", "-m", "pytest"]:
        argv = [sys.executable, "-m", "pytest"] + argv[3:]
    elif argv[:1] == ["pytest"]:
        argv = [sys.executable, "-m", "pytest"] + argv[1:]
    else:
        return None
    return argv


def rerun_test(repo: Path, argv: list[str], tag: str, runner=None) -> tuple[int, str]:
    """Re-run the lane's test, pinned 84-87, in a detached worktree of `repo` at origin/main. -> (rc, tail)."""
    wt = WT_ROOT / f"{tag}-verify"
    try:
        sparse_worktree(repo, wt, None)
    except RuntimeError as e:
        return 98, f"verify worktree: {e}"
    try:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HIP_VISIBLE_DEVICES="-1")
        try:
            p = (runner or subprocess.run)(PIN + argv + ["-p", "no:cacheprovider"], cwd=str(wt), capture_output=True,
                                           text=True, timeout=TEST_TIMEOUT_S, env=env)
            return p.returncode, (p.stdout + p.stderr).strip()[-300:]
        except subprocess.TimeoutExpired:
            return 124, f"timeout {TEST_TIMEOUT_S}s"
    finally:
        rm = git(repo, "worktree", "remove", str(wt))
        if rm.returncode != 0:
            print(f"[codex] verify worktree kept (remove refused): {wt}: {rm.stderr.strip()[-160:]}", file=sys.stderr)


def judge(report_text: str, box_id: str, repos: dict[str, str], base_heads: dict[str, str], rerun=None) -> dict:
    """{done: bool, why, sha, repo, test_rc}. DONE only from artifacts; the lane's LANE-STATUS line is a hint."""
    status, detail, boxes = D.parse_report(report_text)
    if status != "DONE":
        return {"done": False, "why": f"lane status {status or 'none'}: {detail}"[:300]}
    mine = [b for b in boxes if b[0] == box_id]
    if len(mine) != 1:
        return {"done": False, "why": f"report names {len(mine)} commit lines for {box_id}"}
    _, rname, branch, sha = mine[0]
    rpath = repos.get(rname, rname)
    git(rpath, "fetch", "-q", "origin")
    bad = D.commit_check(rpath, branch, sha, push=True)
    if bad:
        return {"done": False, "why": bad, "sha": sha}
    base = base_heads.get(rpath)
    if base and git(rpath, "merge-base", "--is-ancestor", sha, base).returncode == 0:
        return {"done": False, "why": f"commit {sha[:12]} was already on origin/main before dispatch (no new work)", "sha": sha}
    if "PUSH VERIFIED" not in report_text:
        return {"done": False, "why": "no PUSH VERIFIED line in the report", "sha": sha}
    argv = test_cmd(report_text)
    if not argv:
        return {"done": False, "why": "no re-runnable `TEST: <pytest ...>` line in the report", "sha": sha}
    rc, tail = (rerun or rerun_test)(Path(rpath), argv, f"cxd-{box_id.lower()}-{int(time.time())}")
    if rc != 0:
        return {"done": False, "why": f"dispatcher re-run of the lane's test rc={rc}: {tail[-160:]}", "sha": sha, "test_rc": rc}
    return {"done": True, "why": "artifacts verified", "sha": sha, "repo": rname, "test_rc": 0, "test": " ".join(argv[1:])}


# ------------------------------------------------------------------------------------------------ tick / tag
SPARSE_EXCLUDE = ("artifacts/", "benchmarks/", "data/")   # ~1.2 GB per full epyc-root tree (coordinator 2026-11-25)
SPARSE_KEEP = ("artifacts/operator/*.sh",)                  # the observer-census commit hook reads them (handoff_sessions)
WORKTREE_GATE = "scripts/system/worktree_gate.py"


def sparse_worktree(repo: Path, wt: Path, branch: str | None) -> Path:
    """`git worktree add --no-checkout`, non-cone sparse set = everything but SPARSE_EXCLUDE, then checkout."""
    add = ["worktree", "add", "-q", "--no-checkout"] + (["-b", branch] if branch else ["--detach"]) + [str(wt), "origin/main"]
    r = git(repo, *add)
    if r.returncode != 0:
        raise RuntimeError(f"worktree add {wt}: {r.stderr.strip()[-200:]}")
    git(wt, "sparse-checkout", "init", "--no-cone")
    git(wt, "sparse-checkout", "set", "--no-cone", "/*", *[f"!/{x}" for x in SPARSE_EXCLUDE], *[f"/{x}" for x in SPARSE_KEEP])
    c = git(wt, "checkout", "-q")
    if c.returncode != 0:
        raise RuntimeError(f"checkout {wt}: {c.stderr.strip()[-200:]}")
    if branch:
        git(wt, "branch", "--set-upstream-to=origin/main")
    return wt


def gate_remove(root_repo: Path, wt: Path, runner=None) -> dict:
    """Remove a lane worktree through worktree_gate.py remove (it removes only a clean, landed, unreferenced tree)."""
    if not wt.exists():
        return {"removed": True, "detail": "absent"}
    r = (runner or subprocess.run)([sys.executable, str(root_repo / WORKTREE_GATE), "remove", str(wt)],
                                   capture_output=True, text=True, timeout=600)
    tail = (r.stdout + r.stderr).strip().splitlines()
    return {"removed": r.returncode == 0 and not wt.exists(), "detail": tail[-1][:200] if tail else f"rc={r.returncode}"}


def lane_clean(wt: Path) -> bool:
    return wt.exists() and git(wt, "status", "--porcelain").returncode == 0 and not git(wt, "status", "--porcelain").stdout.strip()


def _side_lane(root_repo: Path, tag: str) -> Path:
    return sparse_worktree(root_repo, WT_ROOT / f"{tag}-wt", f"codex-dispatch/{tag}")


def _drop_side_lane(root_repo: Path, wt: Path) -> None:
    if git(root_repo, "worktree", "remove", str(wt)).returncode != 0:
        print(f"[codex] side lane kept (remove refused): {wt}", file=sys.stderr)


def tick(rec: dict, v: dict, lane: str, root_repo: Path, trailers: list[str], env_ack: str) -> dict:
    """Tick the box via wrapup.py, `[no-belief: software]`. -> {ticked, detail}. A refusal leaves the box open."""
    wt = _side_lane(root_repo, f"{lane}-tick")
    j = WT_ROOT / f"{lane}-tick.json"
    first = rec["text"].split("**", 2)
    tick_text = f"**{rec['id']}**" + (first[2][:60] if len(first) > 2 else "")
    verdict = f"codex lane {lane}: {v['sha'][:9]} on origin/main, dispatcher re-ran `{v.get('test', '')[:70]}` rc=0"
    body = {"slug": WRAPUP_SLUG, "box": rec["id"], "state": "ready", "task_text": f"{rec['id']} via Codex lane {lane}",
            "ticks": [tick_text], "belief": "no-belief: software", "verdict": verdict,
            "progress_md": f"Codex dispatcher: {rec['id']} DONE by lane {lane}, commit {v['sha']} (PUSH VERIFIED, "
                           f"on origin/main), dispatcher test re-run rc=0: `{v.get('test', '')}`.",
            "paths": [], "evidence": {"verdict": verdict, "paths": [], "artifact_class": "software",
                                      "commands": [{"cmd": "python3 " + v.get("test", ""), "rc": 0}]},
            "message": f"handoffs: tick {rec['id']} (Codex lane {lane}, {v['sha'][:9]}, dispatcher-verified)",
            "question": "", "rows_published": [], "trailers": list(trailers)}
    try:
        j.write_text(json.dumps(body))
        env = dict(os.environ, **({"EPYC_D9_ACK": env_ack} if env_ack else {}))
        r = subprocess.run([sys.executable, str(root_repo / "scripts/coordination/churn/wrapup.py"), "--json", str(j),
                            "--lane", str(wt)], capture_output=True, text=True, env=env, timeout=3600)
        last = (r.stdout.strip().splitlines() or ["?"])[-1]
        ok = r.returncode == 0 and last.startswith("WRAPPED")
        why = last if ok else next((l for l in (r.stdout + r.stderr).splitlines()[::-1] if "refused" in l or "fail" in l.lower()), last)
        return {"ticked": ok, "detail": why[:300]}
    finally:
        j.unlink(missing_ok=True)
        _drop_side_lane(root_repo, wt)


def tag_needs_owner(rec: dict, why: str, lane: str, root_repo: Path, trailers: list[str], env_ack: str) -> dict:
    """`· NEEDS-OWNER: <date> codex lane <lane>: <why>` continuation line on the box, committed and pushed."""
    wt = _side_lane(root_repo, f"{lane}-tag")
    try:
        sys.path.insert(0, str(wt / "scripts" / "handoffs"))
        try:
            import handoff_box as HB
        finally:
            sys.path.pop(0)
        f = wt / rec["file"]
        lines = f.read_text(encoding="utf-8").split("\n")
        i = HB.find_box(lines, rec["id"])
        note = " ".join(f"{dt.date.today().isoformat()} codex lane {lane}: {why}".replace("·", "-").split())[:240]
        f.write_text("\n".join(HB.set_field(lines, i, "NEEDS-OWNER", note)), encoding="utf-8")
        msg = f"handoffs: {rec['id']} NEEDS-OWNER (Codex lane {lane} not verified DONE; never auto-retried)\n\n" + \
              "\n".join(trailers) + "\n"
        env = dict(os.environ, **({"EPYC_D9_ACK": env_ack} if env_ack else {}))
        c = subprocess.run(["git", "-C", str(wt), "commit", "-q", "-F", "-", "--", rec["file"]], input=msg,
                           capture_output=True, text=True, env=env)
        if c.returncode != 0:
            return {"tagged": False, "detail": (c.stderr or c.stdout).strip()[-200:]}
        p = subprocess.run([sys.executable, str(root_repo / "scripts/coordination/serialized_push.py"), "--agent", AGENT,
                            "--repo", str(wt), "--fetch", "--push", "--wait", "900"], capture_output=True, text=True,
                           env=env, timeout=2400)
        return {"tagged": p.returncode == 0 and "PUSH VERIFIED" in p.stdout,
                "detail": (p.stdout + p.stderr).strip().splitlines()[-1][:200] if (p.stdout + p.stderr).strip() else ""}
    except Exception as e:  # noqa: BLE001 - the ledger still records the attempt, so no retry either way
        return {"tagged": False, "detail": f"{type(e).__name__}: {e}"[:200]}
    finally:
        _drop_side_lane(root_repo, wt)


# ---------------------------------------------------------------------------------------------------------- run
def run_lane(lane: str, d: Path, codex: str, max_rounds: int, runner=None) -> int:
    """codex_lane/drive.py --push for one lane, pinned 84-87 / nice 19 / ionice 3 (drive's own nice is disabled)."""
    cmd = PIN + [sys.executable, str(ROOT / "scripts/coordination/codex_lane/drive.py"), lane, "--dir", str(d),
                 "--max", str(max_rounds), "--push", "--codex", codex, "--watch", f"/workspace:{lane}"]
    env = dict(os.environ, CODEX_LANE_NO_NICE="1", HIP_VISIBLE_DEVICES="-1")
    with (d / f"{lane}-drive.out").open("a") as o:
        return (runner or subprocess.run)(cmd, stdout=o, stderr=subprocess.STDOUT, env=env).returncode


def dispatch(*, root: Path = ROOT, root_repo: Path | None = None, out: Path = OUT_DEFAULT, files=DEFAULT_FILES,
             n: int = 3, apply: bool = False, dry_run: bool = False, codex: str = "codex", max_rounds: int = MAX_ROUNDS,
             trailers: list[str] = (), env_ack: str = "", doc: dict | None = None, hooks: dict | None = None,
             repos: dict[str, str] | None = None) -> list[dict]:
    """Select up to `n` eligible boxes and run them ONE AT A TIME. `hooks` (tests): lane, judge_rerun, tick, tag."""
    hooks = hooks or {}
    root_repo = root_repo or Path(os.environ.get("TASKFLOW_ROOT_REPO", "/workspace"))
    out.mkdir(parents=True, exist_ok=True)
    lock = open(out / ".dispatch.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)            # MAX_CODEX_LANES = 1: no second dispatcher
    except BlockingIOError:
        print("[codex] another codex dispatcher holds the run lock; refusing", file=sys.stderr)
        return []
    if stopped(out):
        print(f"[codex] STOP file present ({out / 'STOP'}); nothing started")
        return []
    git(root_repo, "fetch", "-q", "origin")
    if doc is None:
        sys.path.insert(0, str(root / "scripts" / "handoffs"))
        import box_index
        sys.path.pop(0)
        doc = box_index.load(root)
    def base_state(r):
        st = origin_box_state(r, root_repo)
        if st == "open" and (hooks.get("already_done") or (lambda x: already_done(x, root_repo)))(r):
            return "landed"
        return st
    chosen, hist = select(doc, root, files, attempted(out), n, base_state=base_state)
    print(f"[codex] chosen: {[k for k, _ in chosen]}  skips: {hist}")
    if dry_run:
        return [{"box": k, "file": r["file"], "line": r["line"], "dry_run": True} for k, r in chosen]
    repos = dict(repos or D.DEFAULT_REPOS)
    rows = []
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M")
    for key, rec in chosen[:n]:
        if stopped(out):
            print(f"[codex] STOP file present; not starting {key}")
            break
        lane = lane_name(rec["id"], stamp)
        report = out / f"{lane}-REPORT.md"
        base_heads = {}
        for p in {str(v) for v in repos.values()} | {str(root_repo)}:
            if Path(p).exists():
                git(p, "fetch", "-q", "origin")
                base_heads[p] = git(p, "rev-parse", "origin/main").stdout.strip()
        (out / f"{lane}.prompt").write_text(build_prompt(rec, root, lane, report, trailers=trailers, env_ack=env_ack))
        row = {"at": now(), "box": rec["id"], "file": rec["file"], "line": rec["line"], "lane": lane, "apply": apply}
        t0 = time.time()
        wt = WT_ROOT / f"{lane}-wt"
        try:
            (hooks.get("mklane") or (lambda: sparse_worktree(root_repo, wt, lane)))()
            row["drive_rc"] = (hooks.get("lane") or run_lane)(lane, out, codex, max_rounds)
            text = report.read_text(errors="replace") if report.exists() else ""
            v = judge(text, rec["id"], repos, base_heads, rerun=hooks.get("rerun"))
        except Exception as e:  # noqa: BLE001 - one lane never stops the ledger line
            v = {"done": False, "why": f"dispatcher error {type(e).__name__}: {e}"[:300]}
        row.update(verdict="DONE" if v["done"] else "NOT-DONE", why=v["why"], sha=v.get("sha"), test_rc=v.get("test_rc"),
                   wall_s=round(time.time() - t0, 1))
        if apply and v["done"]:
            row["tick"] = (hooks.get("tick") or tick)(rec, v, lane, root_repo, list(trailers), env_ack)
            if not row["tick"].get("ticked"):
                row["tick_refused"] = True                                  # box stays open; recorded, not retried
        elif apply:
            row["needs_owner"] = (hooks.get("tag") or tag_needs_owner)(rec, v["why"], lane, root_repo, list(trailers), env_ack)
        status = D.parse_report(report.read_text(errors="replace") if report.exists() else "")[0]
        if v["done"] or (status == "BLOCKED" and lane_clean(wt)):      # coordinator 2026-11-25: no leftover lane trees
            row["worktree"] = (hooks.get("remove") or gate_remove)(root_repo, wt)
        else:
            row["worktree"] = {"removed": False, "detail": f"kept for the owner: {wt}"}
        write_ledger(out, row)
        rows.append(row)
        print(f"[codex] {rec['id']} lane={lane} {row['verdict']}: {row['why']}")
    return rows
