#!/usr/bin/env python3
"""taskflow/dispatch.py — select -> build task -> worker in a disposable worktree -> verify -> (tick) (DESIGN.md §2.4-2.6).

    dispatch.py plan  --keys K1,K2 ... | --top N  [--out tasks.json]        # select + schema, no model, no writes
    dispatch.py run   --tasks tasks.json --endpoint http://127.0.0.1:P/v1 --out DIR [--apply] [--reviewer]
    dispatch.py codex [--file F.md ...] [--max-boxes 3] [--apply] [--dry-run]  # Codex lane type: harness/codex.py

`run` per task: `git worktree add` a detached disposable worktree of the task's repo at origin/main, branch
`taskflow/<run>/<n>` -> harness spawn -> the DISPATCHER commits the worker's changes on that lane (the worker never
commits) -> verify.verify -> ledger line. With --apply, a `verified` task is ticked via churn/wrapup.py under the owning
handoff's slug (box resolved by TEXT; evidence = the verifier's); index rows are never touched. Without --apply nothing
leaves the lane (the canary default). The lane worktree is removed after the diff and ledger are saved; the local
branch is kept for review.

Two-phase run (task-brief layer P4, docs/design/task-brief-layer.md §5): on the local family, a box whose brief is
none / orphaned / stale / drift first gets PHASE 1 -- the worker self-briefs (or refreshes) with its output constrained
to a TASKFLOW-BRIEF line; the dispatcher writes `handoffs/active/briefs/<ID>.md` (author: self, review: backfill),
compiles it, rejects an acceptance that already passes on the unchanged tree, and commits the brief ALONE on the lane
before PHASE 2 executes. Two failed attempts end the run `needs-brief`. D3: the brief is `accepted: auto` when its
acceptance is the box's literal done-when, else `accepted: pending` -- a pending brief HOLDS the result tick (verify
returns hold=accepted-pending) until the owner accepts at wrap-up (`handoff_box.py brief accept <ID>`).

Tier (operator directive 3): box `tier:` wins; else class -> tier (TIER_BY_KIND); escalation only after a verified
failure (`escalate()`). Ledger: one JSON line per task {key, tier, model, family, tokens (input/cached/uncached/output),
wall_s, verdict, reason, failure_class}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import shutil
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
from taskflow import brief as B, external_refs, schema, verify  # noqa: E402
from taskflow.harness import local_llm  # noqa: E402

ROOT = _HERE.parents[2]
TIERS = ("luna", "terra", "sol")
# cheapest capable tier per kind of work (operator 2026-11-20: clerical/filing/docs low, code mid, design/debug top)
TIER_BY_KIND = {"clerical": "luna", "docs": "luna", "file": "luna", "code": "terra", "design": "sol", "debug": "sol"}
_KIND_RX = [("file", r"\bfile (?:the )?(?:result|row|verdict)|run-end"),
            ("debug", r"\b(?:debug|root[- ]cause|bisect|diagnos|reproduce)"),
            ("design", r"\b(?:design|architecture|decide between|spec out)\b"),
            ("docs", r"\b(?:document|docs?/|README|write[- ]up|record (?:the|a)|note in)\b"),
            ("code", r"\b(?:fix|implement|add (?:a )?test|wire|refactor|\.py\b|test_)")]


def kind_of(task: dict) -> str:
    t = task["goal"]
    for k, rx in _KIND_RX:
        if re.search(rx, t, re.I):
            return k
    return "code"


def pick_tier(task: dict) -> str:
    t = str(task.get("tier") or "").lower()
    if t in TIERS:
        return t
    alias = {"haiku": "luna", "sonnet": "terra", "opus": "sol"}
    return alias.get(t) or TIER_BY_KIND[kind_of(task)]


def escalate(tier: str) -> str | None:
    i = TIERS.index(tier)
    return TIERS[i + 1] if i + 1 < len(TIERS) else None


# ----------------------------------------------------------------------------------------------------------- plan
def plan(keys: list[str] | None, top: int) -> list[dict]:
    sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
    import box_index
    from taskflow import select as S
    doc = box_index.load(ROOT)
    cands, _ = S.candidates(doc)
    byk = dict(cands)
    chosen = [(k, byk.get(k)) for k in keys] if keys else cands
    out = []
    for k, rec in chosen:
        if rec is None:
            print(f"skip {k}: not dispatchable now (select.py skips it)", file=sys.stderr)
            continue
        t = schema.build(dict(rec, key=k))
        why = schema.unsupported(t)
        if why:
            if keys:
                print(f"skip {k}: {why}", file=sys.stderr)
            continue
        t["kind"] = kind_of(t)
        t["tier"] = pick_tier(t)
        out.append(t)
        if not keys and len(out) >= top:
            break
    return out


# ------------------------------------------------------------------------------------------------------------ run
def _git(repo: Path, *a: str, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=check)


# ------------------------------------------------------------------------------------------- worktree lifecycle
# docs/design/taskflow-dispatcher.md -> "Worktree lifecycle". One worker per worktree; created fresh from origin/main
# at a short path; the worker never commits, pushes or switches branches (POLICY + shell deny list); the DISPATCHER
# commits the worker's tree on the lane branch and only `--apply` (wrapup.py) pushes. Disposal = `git worktree remove`
# (never --force, never prune); a dirty lane is committed as WIP on its own branch first so nothing is lost.
KEEP_FAILED_H = float(os.environ.get("TASKFLOW_KEEP_FAILED_H", "24"))   # failed / aborted lanes kept for forensics
MAX_LANES = int(os.environ.get("TASKFLOW_MAX_LANES", "16"))             # live lanes under the lane root
MIN_FREE_GIB = float(os.environ.get("TASKFLOW_MIN_FREE_GIB", "50"))     # free space required to create a lane


class LaneRefused(RuntimeError):
    pass


def lane_root() -> Path:
    return Path(os.environ.get("TASKFLOW_LANE_ROOT", "/mnt/raid0/llm/tf"))


def _meta(lane: Path) -> Path:
    return lane.parent / f"{lane.name}.lane.json"


def make_lane(task: dict, base_dir: Path, branch: str) -> tuple[Path, Path, str]:
    repo = schema.REPOS[task["repo"]]
    # r3: the 35B miscopied long digit-heavy lane paths (".../canary-r3-2026120/.../t00/lane" for t02) ->
    # short lane roots: /mnt/raid0/llm/tf/<4 hex>
    root = lane_root()
    try:
        external = external_refs.read_sources(task, root)
    except (OSError, ValueError) as exc:
        raise LaneRefused(f"external reference preflight failed: {exc}") from exc
    root.mkdir(parents=True, exist_ok=True)
    lane = root / hashlib.sha1(str(base_dir).encode()).hexdigest()[:4]
    if lane.exists():
        reclaim_resumed_lane(lane, base_dir, task, repo)     # r8c fix 1: raises LaneRefused unless it is ours
    if lane.exists():
        raise LaneRefused(f"{lane} exists: one worker per worktree")
    live = live_lanes(root)            # r8d: only live lanes whose dispatcher is alive count (kept / orphans do not)
    if len(live) >= MAX_LANES:
        raise LaneRefused(f"{len(live)} live lanes >= cap {MAX_LANES}; run `dispatch.py sweep`")
    free = shutil.disk_usage(root).free / 2**30
    if free < MIN_FREE_GIB:
        raise LaneRefused(f"{free:.0f} GiB free < {MIN_FREE_GIB} GiB")
    base = _git(repo, "rev-parse", "origin/main").stdout.strip()
    if external and _git(repo, "ls-tree", base, "--", REFS).stdout:
        raise LaneRefused(f"base tracks reserved reference directory: {REFS}")
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "lane.path").write_text(str(lane))
    _git(repo, "worktree", "add", "-q", "-b", branch, str(lane), base)
    _meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "branch": branch, "base": base,
                                       "created": time.time(), "state": "live", "task": task.get("key"),
                                       "row": task.get("row") or os.environ.get("FILLER_ID") or None,
                                       "base_dir": str(base_dir), "owner": _proc_id(os.getpid())}))
    for r in task.get("refs") or []:
        dst = lane / REFS / (r["repo"] + (f"@{r['rev']}" if r.get("rev") else "")) / r["path"]
        data = (schema.git_show(schema.REPOS[r["repo"]], r["rev"], r["path"]) if r.get("rev")
                else (schema.REPOS[r["repo"]] / r["path"]).read_bytes())
        if data is None:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        dst.chmod(0o444)
    if external:
        try:
            external_refs.stage(lane, external)
            if failure := external_refs.verify(lane, task):
                raise ValueError(failure)
        except (OSError, ValueError) as exc:
            drop_lane(repo, lane)
            raise LaneRefused(f"external reference staging failed: {exc}") from exc
    return repo, lane, base


REFS = ".taskflow-refs"


def guarded_rm_path() -> str:
    for c in (os.environ.get("GUARDED_RM"), str(ROOT / "scripts/safety/guarded_rm.sh"), "/workspace/scripts/safety/guarded_rm.sh"):
        if c and Path(c).is_file():
            return c
    raise LaneRefused("guarded_rm.sh not found")


def _proc_id(pid: int) -> str | None:
    """`<pid>:<starttime>` from /proc (a recycled pid has another start time). None when the process is gone."""
    try:
        return f"{pid}:{Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]}"
    except (OSError, IndexError):
        return None


def _owner_alive(meta: dict) -> bool:
    own = str(meta.get("owner") or "")
    if not own or ":" not in own:
        return False                    # pre-r8d lanes carry no owner; their dispatcher is gone
    return _proc_id(int(own.split(":")[0])) == own


def _read_meta(m: Path) -> dict:
    try:
        return json.loads(m.read_text())
    except (OSError, ValueError):
        return {}


def live_lanes(root: Path | None = None) -> list[Path]:
    """r8d (tf1-cpu-r8d: 14 kept + 2 orphaned live lanes filled the 16 cap, 10/10 units refused): the cap counts only
    lanes in state "live" whose owner pid:starttime is still running. Kept (forensics) lanes and orphans do not."""
    root = root or lane_root()
    return [m for m in root.glob("*.lane.json") if (d := _read_meta(m)).get("state") == "live" and _owner_alive(d)]


def is_orphan(meta: dict) -> bool:
    """A live lane whose dispatcher is dead (killed stint): it has no keep_until and nobody will drop it."""
    return meta.get("state", "live") == "live" and not _owner_alive(meta)


FILED_DIR = Path(os.environ.get("TASKFLOW_FILED_DIR", "/mnt/raid0/llm/tmp/compute-flags/filing-done"))
READY_DIR = Path(os.environ.get("TASKFLOW_READY_DIR", "/mnt/raid0/llm/tmp/compute-flags/ready"))


def filed_rows(filed_dir: Path | None = None) -> set[str]:
    d = filed_dir or FILED_DIR
    return {f.name[:-len(".FILED")] for f in d.glob("*.FILED")} if d.is_dir() else set()


def legacy_lane_rows(rows: set[str], ready_dir: Path | None = None) -> dict[str, str]:
    """Pre-r8d lane metadata carries no row id: map lane path -> row through the row workdir's <base_dir>/lane.path
    files (the row manifest in ready/ names the workdir). Later rows win a shared workdir (r8 then r8b)."""
    rd = ready_dir or READY_DIR
    out: dict[str, str] = {}
    mans = []
    for r in rows:
        man = _read_meta(rd / f"{r}.json")
        if man.get("workdir"):
            mans.append((man.get("published_at") or "", r, Path(man["workdir"])))
    for _, r, wd in sorted(mans):
        for lp in wd.glob("out/**/lane.path"):
            try:
                out[lp.read_text().strip()] = r
            except OSError:
                pass
    return out


def lane_row(meta: dict, legacy: dict[str, str]) -> str | None:
    return meta.get("row") or legacy.get(str(meta.get("lane")))


def _registered_worktree(repo: Path, lane: Path) -> bool:
    out = _git(repo, "worktree", "list", "--porcelain", check=False).stdout
    want = {str(lane), os.path.realpath(lane)}
    return any(ln[len("worktree "):] in want for ln in out.splitlines() if ln.startswith("worktree "))


def reclaim_resumed_lane(lane: Path, base_dir: Path, task: dict, repo: Path) -> str:
    """r8c fix 1 (TU-GR-1 think, MM-5 think): a unit killed by an rc=75 yield leaves its lane at the deterministic
    /mnt/raid0/llm/tf/<sha1(base_dir)[:4]>, and the resumed unit was refused "exists: one worker per worktree".
    The leftover is reclaimed only when it is provably the SAME unit's (base_dir/lane.path names it, or its metadata
    names the same task key) AND the dispatcher that made it is dead (owner pid:starttime); a registered worktree goes through drop_lane (WIP committed on its branch, plain
    `git worktree remove`), anything else through guarded_rm.sh (trash, recoverable). Never --force, never prune."""
    meta = {}
    try:
        meta = json.loads(_meta(lane).read_text()) if _meta(lane).exists() else {}
    except ValueError:
        meta = {}
    lp = base_dir / "lane.path"
    ours = (lp.exists() and lp.read_text().strip() == str(lane)) or (meta.get("task") and meta.get("task") == task.get("key"))
    if not ours:
        raise LaneRefused(f"{lane} exists and is not this unit's leftover: one worker per worktree")
    if _owner_alive(meta):
        raise LaneRefused(f"{lane} exists and its dispatcher {meta.get('owner')} is alive: one worker per worktree")
    mrepo = Path(meta["repo"]) if meta.get("repo") else repo
    for r in dict.fromkeys([mrepo, repo]):
        if _registered_worktree(r, lane):
            if not drop_lane(r, lane):
                raise LaneRefused(f"{lane}: leftover worktree could not be removed (git worktree remove failed)")
            _sweep_log(f"reclaimed resumed lane {lane} (worktree remove) task {task.get('key')}")
            return "worktree-remove"
    cp = subprocess.run(["bash", guarded_rm_path(), str(lane)], capture_output=True, text=True, timeout=600)
    if cp.returncode != 0:
        raise LaneRefused(f"{lane}: guarded_rm rc={cp.returncode}: {(cp.stderr or cp.stdout).strip()[-200:]}")
    _meta(lane).unlink(missing_ok=True)
    _sweep_log(f"reclaimed resumed lane {lane} (guarded_rm) task {task.get('key')}")
    return "guarded_rm"


# r8e fix 2: what commit_lane dropped / restored, by lane (read by run() into the ledger row)
COMMIT_REPORTS: dict[str, dict] = {}
KEEP_EMPTY = {"__init__.py", "py.typed", ".gitkeep", ".keep"}


def tidy_lane(lane: Path, task: dict) -> dict:
    """Before the commit: restore tracked files deleted outside the checked scratch command, and
    drop zero-byte NEW files (an emptied scratch file, r8e TU-GR-1 / LOOP-62 nothink) unless the packet names them or
    they are conventionally empty (__init__.py, py.typed, .gitkeep). Returns {"restored": [...], "dropped_empty": [...]}."""
    named = set(task.get("outputs") or []) | set(task.get("inputs") or []) | verify.approach_new_paths(task)
    rep: dict = {"restored": [], "dropped_empty": []}
    for ln in _git(lane, "status", "--porcelain", "-uall").stdout.splitlines():
        code, p = ln[:2], ln[3:].split(" -> ")[-1]
        if p.startswith(REFS + "/"):
            continue
        if "D" in code and p not in set(task.get("outputs") or []):
            _git(lane, "restore", "--source=HEAD", "--staged", "--worktree", "--", p, check=False)
            rep["restored"].append(p)
        elif code == "??":
            f = lane / p
            if f.is_file() and not f.is_symlink() and f.stat().st_size == 0 and f.name not in KEEP_EMPTY \
                    and p not in named:
                f.unlink()
                rep["dropped_empty"].append(p)
    return rep


def lane_destroyed(lane: Path) -> bool:
    """True when the lane directory is gone or is no longer a git worktree (the worker deleted it)."""
    if not lane.is_dir() or not (lane / ".git").exists():
        return True
    return _git(lane, "rev-parse", "--is-inside-work-tree", check=False).returncode != 0


def commit_lane(lane: Path, task: dict) -> bool:
    rep = tidy_lane(lane, task)
    if rep["restored"] or rep["dropped_empty"]:
        COMMIT_REPORTS[str(lane)] = rep
    st = _git(lane, "status", "--porcelain", "-uall").stdout
    paths = [p for p in (ln[3:].split(" -> ")[-1] for ln in st.splitlines() if ln.strip())
             if not p.startswith(REFS + "/") and not p.endswith(".compile-cache.json")]
    if not paths:
        return False
    _git(lane, "add", "--", *paths)
    _git(lane, "-c", "user.name=taskflow", "-c", "user.email=taskflow@localhost", "commit", "-q", "--no-verify",
         "-m", f"taskflow: {task.get('id') or task['text_sha']} (worker draft)")
    return True


def _clear_refs(lane: Path) -> None:
    refs = lane / REFS
    if refs.is_symlink():
        refs.unlink()
        return
    if refs.exists():                   # our own read-only copies; the worktree is otherwise clean after commit
        for f in sorted(refs.rglob("*"), reverse=True):
            if f.is_symlink() or not f.is_dir():
                f.unlink()
            else:
                f.rmdir()
        refs.rmdir()


def _sweep_log(msg: str) -> None:
    root = lane_root()
    root.mkdir(parents=True, exist_ok=True)
    with (root / "sweep.log").open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")


def delete_branch_if_safe(repo: Path, branch: str | None, base: str | None = None, pinned: bool = False) -> str:
    """Delete a taskflow lane branch when it is ours (taskflow/*), not pinned and not pushed anywhere. The tip sha is
    logged to <lane root>/sweep.log so `git branch <b> <sha>` recovers it while the reflog/objects live."""
    if not branch or not branch.startswith("taskflow/"):
        return "skip:not-taskflow"
    if pinned:
        return "skip:pinned"
    tip = _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}", check=False).stdout.strip()
    if not tip:
        return "skip:absent"
    if _git(repo, "branch", "-r", "--contains", tip, check=False).stdout.strip() and tip != base:
        return "skip:pushed"
    if _git(repo, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}", check=False).returncode == 0:
        return "skip:has-upstream"
    if _git(repo, "branch", "-D", branch, check=False).returncode != 0:
        return "fail"
    _sweep_log(f"deleted branch {branch} tip {tip} repo {repo}")
    return "deleted"


def drop_lane(repo: Path, lane: Path) -> bool:
    """Remove a lane: commit any leftover worker change as WIP on the lane branch, then plain `worktree remove`.
    A lane branch with no commit over its base is deleted at once (nothing to recover)."""
    meta = json.loads(_meta(lane).read_text()) if _meta(lane).exists() else {}
    if not lane.exists():
        _meta(lane).unlink(missing_ok=True)
        return True
    _clear_refs(lane)
    if _git(lane, "status", "--porcelain", "-uall", check=False).stdout.strip():
        st = _git(lane, "status", "--porcelain", "-uall", check=False).stdout
        left = [ln[3:].split(" -> ")[-1] for ln in st.splitlines() if ln.strip()]
        _git(lane, "add", "--", *left, check=False)
        _git(lane, "-c", "user.name=taskflow", "-c", "user.email=taskflow@localhost", "commit", "-q", "--no-verify",
             "-m", "taskflow: WIP left in lane at disposal", check=False)
    ok = _git(repo, "worktree", "remove", str(lane), check=False).returncode == 0
    if ok:
        _meta(lane).unlink(missing_ok=True)
        b, base = meta.get("branch"), meta.get("base")
        if b and base and _git(repo, "rev-parse", "-q", "--verify", f"refs/heads/{b}", check=False).stdout.strip() == base:
            delete_branch_if_safe(repo, b, base)
    return ok


def keep_lane(lane: Path, reason: str, hours: float | None = None) -> None:
    """Failed / aborted lane: keep for forensics, the sweep removes it after KEEP_FAILED_H."""
    m = _meta(lane)
    d = json.loads(m.read_text()) if m.exists() else {"lane": str(lane), "created": time.time()}
    d.update(state="kept", reason=reason, keep_until=time.time() + 3600 * (KEEP_FAILED_H if hours is None else hours))
    m.write_text(json.dumps(d))


def sweep_lanes(now: float | None = None, release_filed: bool = False, filed_dir: Path | None = None,
                ready_dir: Path | None = None) -> dict:
    """Orphan / expiry sweep over the lane root. Removed (drop_lane only, never --force/prune):
    - kept lanes past keep_until;
    - live lanes whose owner pid:starttime is dead (r8d orphans: a killed stint never drops its lane), at once;
    - with release_filed, kept lanes whose row has a <row>.FILED marker in filing-done/ (the forensics window has
      served its purpose once the round is filed and its transcripts audited);
    - lane dirs with no metadata older than KEEP_FAILED_H."""
    now = now or time.time()
    out = {"removed": [], "kept": [], "failed": [], "orphans": [], "released_filed": []}
    root = lane_root()
    if not root.exists():
        return out
    rows = filed_rows(filed_dir) if release_filed else set()
    legacy = legacy_lane_rows(rows, ready_dir) if rows else {}
    seen = set()
    for m in sorted(root.glob("*.lane.json")):
        d = _read_meta(m)
        if not d.get("lane"):
            continue
        lane = Path(d["lane"])
        seen.add(lane.name)
        state = d.get("state", "live")
        why = None
        if state == "kept":
            if now >= (d.get("keep_until") or 0):
                why = "expired"
            elif rows and lane_row(d, legacy) in rows:
                why = "filed"
        elif is_orphan(d):
            why = "orphan"
        if not why:
            out["kept"].append(str(lane))
            continue
        repo = Path(d.get("repo") or ".")
        if drop_lane(repo, lane):
            out["removed"].append(str(lane))
            if why == "orphan":
                out["orphans"].append(str(lane))
            elif why == "filed":
                out["released_filed"].append(f"{lane}:{lane_row(d, legacy)}")
            _sweep_log(f"swept {why} lane {lane} task {d.get('task')} row {lane_row(d, legacy)}")
            if state == "kept":      # forensics window over: the WIP branch goes too (tip sha logged)
                out.setdefault("branches", []).append(
                    f"{d.get('branch')}:{delete_branch_if_safe(repo, d.get('branch'), d.get('base'), bool(d.get('pin')))}")
        else:
            out["failed"].append(str(lane))
    for lane in root.iterdir():
        if lane.is_dir() and lane.name not in seen and now - lane.stat().st_mtime > 3600 * KEEP_FAILED_H:
            common = _git(lane, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False).stdout.strip()
            repo = Path(common).parent if common else None
            (out["removed"] if repo and drop_lane(repo, lane) else out["failed"]).append(str(lane))
    return out


# ------------------------------------------------------------------------------------ phase 1: self-brief (P4)
BRIEF_REFRESH_STATES = ("none", "orphaned", "stale", "drift")
SELF_BRIEF_SHARE = 0.25          # §5: phase 1 gets <= 25 % of the turn / wall budget
SELF_BRIEF_ATTEMPTS = 2          # §5: two failed compiles -> NEEDS-BRIEF
_RUNNABLE = verify._RUNNABLE


def needs_phase1(task: dict, family: str) -> bool:
    """Local boxes dispatch with any brief state and self-brief first (D4); cloud families get the brief if it exists."""
    return family == "local" and bool(task.get("id")) and task.get("brief_state", "none") in BRIEF_REFRESH_STATES


def self_brief(task: dict, lane: Path, tdir: Path, endpoint: str, family: str = "local", spawn=None,
               brief_root: Path | None = None) -> dict:
    """Phase 1. Returns {ok, attempts, brief_path?, accepted?, committed, missing?, workers}. Never edits the box.
    `brief_root` = a separate epyc-root worktree that receives the brief when the lane is another repo (the worker
    reads the code in `lane`; the dispatcher writes + commits `briefs/<ID>.md` in `brief_root`)."""
    root = brief_root or lane
    spawn = spawn or local_llm.spawn
    b = task["budget"]
    t1 = dict(task, phase="brief", budget=dict(b, turns=max(4, int(b["turns"] * SELF_BRIEF_SHARE)),
                                               wall_s=max(120, int(b["wall_s"] * SELF_BRIEF_SHARE))))
    out = {"ok": False, "attempts": 0, "committed": False, "workers": []}
    missing: list[str] = []
    for n in range(1, SELF_BRIEF_ATTEMPTS + 1):
        out["attempts"] = n
        w = spawn(dict(t1, stale=missing or t1.get("stale") or []), lane, tdir / f"brief{n}", endpoint, family=family)
        out["workers"].append({k: w.get(k) for k in ("model", "rc", "timed_out", "usage", "brief")})
        d = w.get("brief") if isinstance(w.get("brief"), dict) else {}
        where = [str(x) for x in (d.get("where") or []) if str(x).strip()]
        if isinstance(d.get("where"), str):
            where = [d["where"]]
        missing = [k for k in ("where", "approach", "acceptance") if not (where if k == "where" else d.get(k))]
        if missing:
            missing = [f"missing key `{k}`" for k in missing]
            continue
        acc = " ".join(str(d["acceptance"]).strip().strip("`").split())
        accepted = "auto" if B.acceptance_matches(acc, task.get("done_when")) else "pending"     # D3
        ng = d.get("non_goals") or []
        try:
            p = B.write_brief(task["id"], where, str(d["approach"]), acc, [str(x) for x in (ng if isinstance(ng, list) else [ng])],
                              author="self", accepted=accepted, root=root)
        except ValueError as e:
            missing = [f"schema: {e}"]
            continue
        r = B.compile_brief(task["id"], root, use_cache=False)
        stale = list(r.get("stale_list") or [])
        if r["state"] not in ("fresh", "drift"):
            missing = stale or [f"compile: {r['state']}"]
            p.unlink(missing_ok=True)
            continue
        if _RUNNABLE.match(acc):          # §5: an acceptance that already passes proves nothing
            pre = verify.run_tests(lane, [acc])[0]
            if pre["rc"] == 0:
                missing = [f"acceptance: `{acc}` already passes on the unchanged tree; it must fail until the box is done"]
                p.unlink(missing_ok=True)
                continue
        rel = str(p.relative_to(root))
        _git(root, "add", "--", rel)
        _git(root, "-c", "user.name=taskflow", "-c", "user.email=taskflow@localhost", "commit", "-q", "--no-verify",
             "-m", f"taskflow: brief {task['id']} (author: self, review: backfill, accepted: {accepted})")
        out.update(ok=True, brief_path=rel, accepted=accepted, committed=True)
        if brief_root is not None:
            out["brief_branch"] = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            out["brief_commit"] = _git(root, "rev-parse", "HEAD").stdout.strip()
        return out
    out["missing"] = missing
    return out


def _brief_lane(task: dict, tdir: Path) -> tuple[Path, Path]:
    """A separate epyc-root worktree (detached from the code lane) at origin/main for a cross-repo box's brief."""
    t = dict(task, repo="epyc-root", refs=[], key=str(task.get("key")) + "+brief")
    repo, blane, _ = make_lane(t, tdir / "brieflane", f"taskflow/brief/{task['id']}-{int(time.time())}-"
                               f"{hashlib.sha1(str(tdir).encode()).hexdigest()[:6]}")
    return repo, blane


def fresh_hand_brief(task: dict) -> bool:
    """The packet already carries a fresh, complete, non-self brief for the box (r8b NUMA-DECOUPLE-1, fix 5): the
    cross-repo path re-resolved the brief at origin/main, found none there, and forced a self-brief that hit its 7-turn
    / 150 s cap on both arms although a fresh hand brief was in the packet."""
    return (task.get("brief_state") == "fresh" and bool(task.get("where")) and bool(task.get("approach"))
            and bool(task.get("acceptance")) and str(task.get("brief_author") or "") != "self")


def phase1_or_skip(task: dict, lane: Path, tdir: Path, endpoint: str, family: str, spawn=None) -> dict | None:
    """Run phase 1 when needed and re-merge the brief into the task. None = nothing to do; a dict with ok False =
    the run ends NEEDS-BRIEF. A lane of another repo (the brief lives in epyc-root) resolves the box's brief in a
    separate epyc-root worktree at origin/main -- so an existing brief always reaches the packet fresh -- and a
    self-brief is written and committed there (`brief_branch`, never pushed here) before phase 2."""
    if task.get("brief_mode") == "off":         # A/B no-brief arm: no brief merge, no self-brief, ever
        return None
    if fresh_hand_brief(task):                  # fix 5: the packet's fresh hand brief wins; no re-merge, no phase 1
        return {"ok": True, "skipped": "fresh-hand-brief"}
    if task["repo"] == "epyc-root":
        if not needs_phase1(task, family):
            return None
        res = self_brief(task, lane, tdir, endpoint, family, spawn)
        (tdir / "brief.json").write_text(json.dumps({k: v for k, v in res.items() if k != "workers"}, indent=1))
        if res["ok"]:
            schema.merge_brief(task, lane)
        return res
    if not task.get("id"):
        return None
    repo, blane = _brief_lane(task, tdir)
    try:
        schema.merge_brief(task, blane)             # an existing brief reaches the packet (cloud families too)
        if not needs_phase1(task, family):
            return None
        res = self_brief(task, lane, tdir, endpoint, family, spawn, brief_root=blane)
        (tdir / "brief.json").write_text(json.dumps({k: v for k, v in res.items() if k != "workers"}, indent=1))
        if res["ok"]:
            schema.merge_brief(task, blane)
        return res
    finally:
        drop_lane(repo, blane)                      # a committed brief keeps its branch (drop_lane only deletes empty ones)


REVIEW_MAX_TOKENS = int(os.environ.get("TASKFLOW_REVIEW_MAX_TOKENS", "1024"))


VERDICTS = ("done", "not_done", "drift")
REVIEWER_ROLE_HEADER = "X-Taskflow-Role"     # a job proxy must not force enable_thinking onto this request (r8c fix 2)


def template_echo(v: dict) -> bool:
    """r8c NOFOLD-1 / WS4 think: the reviewer thought through its whole 1024 cap and the parser took the prompt's
    own template `{"verdict":"done|not_done|drift","reason":"<=150 chars"}` as the verdict."""
    verdict, reason = str(v.get("verdict") or ""), str(v.get("reason") or "")
    return "|" in verdict or "done|not_done|drift" in reason or reason.strip() == "<=150 chars"


def parse_review(msg: dict) -> dict:
    """JSON verdict from the reviewer's content, else from its reasoning content. r8b NOFOLD-1 (think arm): the
    server runs --reasoning on, the 200-token cap was spent on reasoning and content came back empty (fix 6).
    Only a real verdict (done|not_done|drift) that is not the prompt template counts (r8c fix 2)."""
    for txt in (msg.get("content") or "", msg.get("reasoning_content") or ""):
        if "{" in txt and "}" in txt:
            cands = [m.group(0) for m in re.finditer(r"\{[^{}]*\"verdict\"[^{}]*\}", txt)][::-1]
            for c in cands + [txt[txt.index("{"): txt.rindex("}") + 1]]:
                try:
                    d = json.loads(c)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("verdict") in VERDICTS and not template_echo(d):
                    return d
    content = msg.get("content") or ""
    echo = "done|not_done|drift" in content + (msg.get("reasoning_content") or "")
    return {"verdict": "unparseable", "reason": content[:150], "empty": not content.strip(), "template_echo": echo}


def reviewer_for(endpoint: str, model: str, max_tokens: int | None = None):
    """Reviewer hook: ONE chat call (one retry on an unparseable / template-echo verdict, at twice the cap), JSON
    verdict against the verbatim box text. Thinking is off for the reviewer (enable_thinking False plus the
    X-Taskflow-Role header so a job proxy does not re-enable it). Never edits."""
    def call(msg: str, cap: int) -> dict:
        body = {"model": model, "messages": [{"role": "user", "content": msg}],
                "max_tokens": cap, "temperature": 0,
                "cache_prompt": True, "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False}}
        req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                     {"content-type": "application/json", REVIEWER_ROLE_HEADER: "reviewer"})
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read())
        ch = resp["choices"][0]
        v = parse_review(ch.get("message") or {})
        v["usage"] = resp.get("usage")
        v["finish_reason"] = ch.get("finish_reason")
        return v

    def review(task: dict, diff: str) -> dict:
        msg = local_llm.POLICY + "\n" + verify.review_prompt(task, diff)
        cap = int(max_tokens or REVIEW_MAX_TOKENS)
        v = call(msg, cap)
        if v.get("verdict") not in VERDICTS:
            first = {k: v.get(k) for k in ("verdict", "reason", "template_echo", "finish_reason", "usage")}
            v = call(msg, cap * 2)
            v["retried"] = first
        return v
    return review


# r8b canary (FIX-HARNESS 2026-11-22, fix 8): the classifier said model-limitation 11/16; a hand audit found 1.
# Timeouts, environment test failures, denied paths, empty reviewer output and packet contradictions are not the model.
_ENV_FAIL = re.compile(r"ModuleNotFoundError|No module named|command not found|ImportError while loading conftest|"
                       r"error: unrecognized arguments|ERROR: usage|Permission denied|No such file or directory: '[^']*python")
_ENV_RC = (4, 5, 126, 127)      # pytest usage error / no tests collected; shell not-executable / not-found


def _env_test_failure(v: dict) -> bool:
    tail = str(v.get("test_tail") or "")
    rcs = [c.get("rc") for c in (v.get("evidence") or {}).get("commands") or [] if c.get("rc")]
    if not rcs:
        for c in v.get("checks") or []:
            if c.get("check") == "tests" and not c.get("ok"):
                rcs = [int(x) for x in re.findall(r"rc=(\d+)", str(c.get("why") or ""))]
    return bool(_ENV_FAIL.search(tail)) or (bool(rcs) and all(r in _ENV_RC for r in rcs))


_TEST_FILE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*test_[\w-]+\.py)\b")
_NOT_FOUND = re.compile(r"file or directory not found|no such file or directory", re.I)


def missing_test_file(v: dict, task: dict | None) -> bool:
    """r8c WS4 nothink: rc=4 was pytest's "file or directory not found" for the acceptance test the worker never
    wrote -- the model's failure, not the environment. True when the failing run names test files none of which the
    worker's diff touched and none of which is an existing input of the packet (or the tail says not found)."""
    if v.get("reason") != "tests-fail":
        return False
    rcs = [c.get("rc") for c in (v.get("evidence") or {}).get("commands") or [] if c.get("rc")]
    cmds = [c.get("cmd") or "" for c in (v.get("evidence") or {}).get("commands") or [] if c.get("rc")]
    if not rcs:
        for c in v.get("checks") or []:
            if c.get("check") == "tests" and not c.get("ok"):
                for part in str(c.get("why") or "").split("; "):
                    m = re.search(r"^(.*) rc=(\d+)$", part.strip())
                    if m:
                        cmds.append(m.group(1))
                        rcs.append(int(m.group(2)))
    if not rcs or not all(r in (4, 5) for r in rcs):
        return False
    if _NOT_FOUND.search(str(v.get("test_tail") or "")) and not _ENV_FAIL.search(str(v.get("test_tail") or "").replace(
            "No such file or directory", "")):
        return True
    if "paths" not in (v.get("evidence") or {}):
        return False            # no record of what the worker changed: cannot tell, leave it to the env rules
    named = {m.group(1) for c in cmds for m in _TEST_FILE.finditer(c)}
    touched = set((v.get("evidence") or {}).get("paths") or [])
    existing = set((task or {}).get("inputs") or [])
    return bool(named) and not (named & touched) and not (named & existing)


def packet_contradiction(task: dict | None) -> list[str]:
    """`where` targets the packet itself forbids (r8b INTAKE-VALIDATE-86: target under the forbidden `.claude/**`)."""
    if not task:
        return []
    import fnmatch
    named = set(task.get("inputs") or []) | set(task.get("outputs") or [])
    dirs = tuple(n for n in named if n.endswith("/")) or ("\0",)
    tgt = [p for p in verify.brief_paths(task) if p not in named and not p.startswith(dirs)]   # as verify.forbidden_hits
    return sorted(p for p in tgt if any(fnmatch.fnmatch(p, g) for g in task.get("forbidden") or []))


def _check_why(v: dict, name: str) -> list[str]:
    return [x for c in v.get("checks") or [] if c.get("check") == name for x in str(c.get("why") or "").split(",") if x]


def failure_class(w: dict, v: dict, task: dict | None = None) -> str | None:
    """model-limitation | harness | task | None (verified); job-level re-class: env-contention (contention_class). Order: packet defects (task) before harness/env, and the
    model is charged only when none of those explains the failure."""
    if v.get("verdict") == "verified":
        return None
    if packet_contradiction(task):
        return "task"           # r8b INTAKE-VALIDATE-86: the packet forbids its own target
    if task and task.get("stale_packet"):
        return "task"           # r8c fix 5: a done packet (INTAKE-VALIDATE-86, NUMA-DECOUPLE-1): no-change / rewrite
    if w.get("errors") and not w["usage"]["steps"]:
        return "harness"
    if v.get("reason") == "contract-unavailable":
        return "harness"
    if w.get("result") and w["result"].get("claimed_done") is False:
        return "task"           # the worker reported blocked/unclear: the box, not the model
    reason = v.get("reason")
    if reason == "outside-pathspec" and task:
        out = _check_why(v, "pathspec")
        named = verify.approach_new_paths(task)
        if out and all(p in named for p in out):
            return "task"       # r8b TU-GR-1: the approach named the files, the pathspec omitted them
    if reason in ("vacuous-acceptance", "contract-fail"):
        return "model-limitation"   # r8e fix 3 (TU-GR-1 think): the worker's test passes on a launcher error
    if missing_test_file(v, task):
        return "model-limitation"   # r8c WS4 nothink: rc=4 = the acceptance test was never written, not env
    real_test_fail = reason == "tests-fail" and not _env_test_failure(v)
    if w.get("timed_out"):
        if real_test_fail and (v.get("evidence") or {}).get("paths"):
            return "model-limitation"   # r8c LOOP-62 think: wrote asserts that fail 15/16; the clock did not write them
        if v.get("reason") == "no-change" and w.get("rc") == 130:
            return "model-limitation"   # r8g fix 3: the budget ran out with nothing written; env only via contention_class
        return "harness"        # r8b: 600 s GPU-sized budget on CPU prefill (WS4, MM-5, TU-GR-1 / LOOP-62 think)
    rv = v.get("review") or {}
    if (reason in ("reviewer-unparseable", "reviewer-None") or rv.get("empty") or rv.get("template_echo")
            or (str(reason or "").startswith("reviewer-") and "|" in str(reason))):
        return "harness"        # r8b NOFOLD-1 think: empty reviewer content; r8c NOFOLD/WS4 think: template echo
    if reason == "tests-fail" and _env_test_failure(v):
        return "harness"        # r8b MM-5: bare python3 -m pytest without fastapi, rc=4
    errs = [str(e) for e in w.get("tool_errors") or []]
    if any("external_directory" in e for e in errs):
        return "harness"        # r8b UFH-21: the work tree is outside the lane
    te = len(errs)
    if te and te * 2 >= max(1, len(w.get("tools") or [])):
        return "harness"        # r1 canary: denied shell / JS-sandbox errors were mislabelled model-limitation
    if reason in ("forbidden-path", "outside-pathspec", "tests-fail", "reviewer-not_done", "reviewer-drift",
                  "done-when-fail"):
        return "model-limitation"
    if reason == "no-change":
        return "model-limitation" if w["usage"]["steps"] else "harness"
    return "model-limitation"


# r8e fix 4 (WS4 think, rc=4 at 1739 s, decode median 6.3 tok/s vs 15 for the phase): a timeout whose measured decode is
# under half the phase's is env-contention, not the model -- but only against a CONTEXT-MATCHED reference. On CPU the
# 35B's decode falls with KV length (r8e: ~29 tok/s at 4k, ~12 at 40k, ~9-10 at 55k, ~6 at 85-92k); WS4 think ran at
# 76-92k with q0 held by r8e alone and q1/q2 idle in every keeper SNAPSHOT, so its slowdown was its own context. The
# literal "under 50% of the phase median" rule would have charged that to the host.
CONTENTION_FRACTION = 0.5
_MIN_DECODE_N = 32           # decode_tok_s of a 1-token reply is meaningless (r8e logged 1e6 for those)


def _ctx(r: dict) -> int:
    return int(r.get("prompt_n") or 0) + int(r.get("cache_n") or 0)


def _dec(rs: list[dict]) -> list[tuple[int, float]]:
    return [(_ctx(r), float(r["decode_tok_s"])) for r in rs
            if r.get("decode_tok_s") and int(r.get("predicted_n") or 0) >= _MIN_DECODE_N]


def _req_key(reqs: list[dict]) -> tuple | None:
    r = next((r for r in reqs if r.get("task")), None)
    return (r.get("arm"), r["task"]) if r else None


def _first_decode(reqs: list[dict]) -> tuple[int, float] | None:
    """(ctx, decode tok/s) of a unit's FIRST usable request: earliest by t0, among its first 3 (a 1-token reply has no rate)."""
    for r in sorted(reqs, key=lambda r: r.get("t0") or 0)[:3]:
        d = _dec([r])
        if d:
            return d[0]
    return None


def contention_check(unit_reqs: list[dict], phase_reqs: list[dict], ctx_band: float = 0.25, min_ref: int = 5,
                     job_reqs: list[dict] | None = None, min_first: int = 3) -> dict:
    """Unit decode vs references. `phase_reqs` may include the unit (it is excluded).
    1. context-matched phase reference (>= min_ref requests within ctx_band of the unit's median context);
    2. r8g fix 3: when that has < min_ref, the whole job's requests (all arms, all stints; `job_reqs`) in the same band;
    3. r8g fix 3: early-context check: the unit's first-request decode against the median of the OTHER units' first
       requests (>= min_first of them): at a few k tokens of context the host, not the KV length, sets the rate
       (r8f think WS4: 2.5-3.5 tok/s at 3.7k vs 20-27 for every other unit's first request).
    -> {unit_decode, phase_decode, ref_decode, ref_n, ref_scope, unit_ctx, first_decode, first_ref, first_n,
        slow (bool | None = no comparable reference), slow_by}."""
    import statistics as st
    ids = {id(r) for r in unit_reqs}
    ukey = _req_key(unit_reqs)
    others = lambda rs: [r for r in rs if id(r) not in ids and not (ukey and (r.get("arm"), r.get("task")) == ukey)]  # noqa: E731
    u = _dec(unit_reqs)
    ph = _dec(others(phase_reqs))
    jb = _dec(others(job_reqs or []))
    if not u or not (ph or jb):
        return {"slow": None, "why": "no decode samples"}
    uctx = st.median(c for c, _ in u)
    ud = st.median(d for _, d in u)
    out = {"unit_decode": round(ud, 1), "unit_ctx": int(uctx)}
    if ph:
        out["phase_decode"] = round(st.median(d for _, d in ph), 1)
    slow_by: list[str] = []
    verdicts: list[bool] = []
    for scope, pool in (("phase", ph), ("job", jb)):
        ref = [d for c, d in pool if abs(c - uctx) <= ctx_band * uctx]
        if len(ref) >= min_ref:
            out.update(ref_scope=scope, ref_n=len(ref), ref_decode=round(st.median(ref), 1))
            if ud < CONTENTION_FRACTION * out["ref_decode"]:
                slow_by.append(f"{scope}-context-matched")
            verdicts.append(ud < CONTENTION_FRACTION * out["ref_decode"])
            break
        out.setdefault("ref_n", len(ref))
    if "ref_scope" not in out:
        out["why"] = f"no context-matched reference (<{min_ref} requests within {ctx_band:.0%} of {int(uctx)} tok, phase or job)"
    uf = _first_decode(unit_reqs)
    if uf and job_reqs:
        by_unit: dict = {}
        for r in others(job_reqs):
            by_unit.setdefault((r.get("arm"), r.get("task")), []).append(r)
        firsts = [f[1] for f in (_first_decode(v) for v in by_unit.values()) if f]
        if len(firsts) >= min_first:
            out.update(first_decode=round(uf[1], 1), first_ctx=uf[0], first_ref=round(st.median(firsts), 1), first_n=len(firsts))
            verdicts.append(uf[1] < CONTENTION_FRACTION * out["first_ref"])
            if verdicts[-1]:
                slow_by.append("early-context-first-request")
    out["slow"] = any(verdicts) if verdicts else None
    if slow_by:
        out["slow_by"] = slow_by
    return out


def contention_class(row: dict, unit_reqs: list[dict], phase_reqs: list[dict], job_reqs: list[dict] | None = None) -> str | None:
    """Re-class a TIMED-OUT unit as env-contention when its decode was under half a reference (see contention_check).
    r8g fix 3: runs on every timed-out row whose class is not a packet defect -- no-change and harness included (r8f
    think WS4 was classed harness/no-change and never evaluated). Returns the new class, or None to keep the row's
    class. Writes row["contention"]."""
    if not row.get("timed_out") or row.get("failure_class") in (None, "task", "env-contention"):
        return None
    c = contention_check(unit_reqs, phase_reqs, job_reqs=job_reqs)
    row["contention"] = c
    return "env-contention" if c.get("slow") else None


def needs_brief_class(task: dict) -> str:
    """NEEDS-BRIEF is the box's fault unless a fresh hand brief existed (then the harness forced phase 1)."""
    return "harness" if fresh_hand_brief(task) else "task"


def apply_tick(task: dict, lane: Path, v: dict, w: dict) -> str:
    rec = {"slug": task["owner_slug"], "state": "ready", "box": task.get("id") or task["text_sha"],
           "task_text": task["goal"].split("\n")[0], "ticks": [task["goal"].split("\n")[0]],
           "progress_md": f"taskflow verified {task['key']}: {(w.get('result') or {}).get('summary', '')}",
           "paths": v["evidence"]["paths"], "belief": "no-belief: taskflow-verified-code-change",
           "evidence": v["evidence"], "message": f"taskflow: {task['key']} (verified, {v['reason']})",
           "trailers": ["Taskflow-Model: " + w["model"]]}
    p = lane / ".taskflow-wrapup.json"
    p.write_text(json.dumps(rec))
    r = subprocess.run([sys.executable, str(ROOT / "scripts/coordination/churn/wrapup.py"), "--json", str(p),
                        "--lane", str(lane)], capture_output=True, text=True)
    p.unlink(missing_ok=True)
    return (r.stdout.strip().splitlines() or ["?"])[-1]


NEEDS_BRIEF_AGENT = "taskflow"


def tag_needs_brief(task: dict, tdir: Path, reason: str, apply: bool = False, push=None) -> dict:
    """Write the NEEDS-BRIEF tag onto the box (`handoff_box.py needs-brief`, a `· NEEDS-BRIEF:` continuation line, the
    first line untouched) so box_index reads `needs_brief` and select.py skips the box. Done in a fresh epyc-root
    worktree at origin/main -- never in the shared clone -- committed on a `taskflow/needs-brief/<ID>` branch; with
    `apply` it is pushed like a tick (serialized_push). Returns {tagged, branch?, pushed?, detail?}."""
    out = {"tagged": False}
    if not task.get("id"):
        return dict(out, detail="box has no ID")
    repo = schema.REPOS["epyc-root"]
    try:
        _, tl, _ = make_lane(dict(task, repo="epyc-root", refs=[], external_readonly_inputs=[],
                                  key=str(task.get("key")) + "+tag"), tdir / "taglane",
                             f"taskflow/needs-brief/{task['id']}-{int(time.time())}")
    except (subprocess.CalledProcessError, LaneRefused) as e:
        return dict(out, detail=f"lane: {(getattr(e, 'stderr', None) or str(e))[-200:]}")
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
        try:
            import handoff_box
        finally:
            sys.path.pop(0)
        r = handoff_box.main(["needs-brief", "--file", str(tl / task["handoff"]), task["id"], "--reason", reason, "--root", str(tl)]) \
            if task.get("handoff") else 1
        if r != 0:
            return dict(out, detail="handoff_box needs-brief refused")
        rel = task["handoff"]
        if not _git(tl, "status", "--porcelain", "--", rel).stdout.strip():
            return dict(out, tagged=True, detail="already tagged")
        _git(tl, "add", "--", rel)
        _git(tl, "-c", "user.name=taskflow", "-c", "user.email=taskflow@localhost", "commit", "-q", "--no-verify",
             "-m", f"taskflow: tag {task['id']} NEEDS-BRIEF (two failed self-briefs)")
        out.update(tagged=True, branch=_git(tl, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip())
        if apply:
            out["pushed"] = (push or _push_tag)(tl)
        return out
    except Exception as e:  # noqa: BLE001 - tagging never fails the batch
        return dict(out, detail=f"{type(e).__name__}: {e}"[:300])
    finally:
        drop_lane(repo, tl)


def _push_tag(lane: Path) -> str:
    _git(lane, "branch", "--set-upstream-to=origin/main", check=False)
    r = subprocess.run([sys.executable, str(ROOT / "scripts/coordination/serialized_push.py"), "--agent", NEEDS_BRIEF_AGENT,
                        "--repo", str(lane), "--fetch", "--push", "--wait", "900"], capture_output=True, text=True)
    return "ok" if r.returncode == 0 else f"rc={r.returncode}"


def box_state_at_base(task: dict) -> str | None:
    """"open" | "ticked" | "gone" for the task's box in its handoff at epyc-root origin/main, resolved by TEXT
    (text_sha); None when that cannot be read (no handoff, no text_sha, git failure) -- unknown never skips."""
    if not task.get("handoff") or not task.get("text_sha"):
        return None
    try:
        r = subprocess.run(["git", "-C", str(schema.REPOS["epyc-root"]), "show", f"origin/main:{task['handoff']}"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    state = "gone"
    for ln in r.stdout.splitlines():
        m = re.match(r"\s*[-*] \[(.)\] ", ln)
        if m and schema.text_sha(ln) == task["text_sha"]:
            if m.group(1) not in "xX":
                return "open"           # [ ] and partial / blocked checkpoint states are still open
            state = "ticked"
    return state


def stale_packet(task: dict, lane: Path) -> str | None:
    """r8c fix 3 (INTAKE-VALIDATE-86, NUMA-DECOUPLE-1): the packet was already done -- the validator exited 0 on the
    lane and the decouple work had landed as a56df365b -- so the worker either found nothing to do (no-change) or
    rewrote landed code. Checked at selection time, before any model call: the box is ticked / gone at origin/main,
    or the packet's runnable acceptance already passes on the unchanged lane. Returns the reason, or None."""
    st = box_state_at_base(task)
    if st in ("ticked", "gone"):
        return f"box {st} at origin/main"
    acc = verify.acceptance_cmd(task)
    if acc:
        pre = verify.run_tests(lane, [acc])[0]
        if pre["rc"] == 0:
            return f"acceptance already passes on base: `{acc[:160]}`"
    return None


class _EndRun(Exception):
    """Phase 1 ended the run (needs-brief); the row is already filled."""


GNX_TRIGGER = ROOT / "scripts/gitnexus-reindex.py"


def gitnexus_trigger(batch_id: str, enabled: bool = True, script: Path | None = None, runner=None) -> str:
    """Once per batch: ask the gitnexus staleness trigger whether to re-index (it detaches itself).

    Fires on every real run (independent of --apply: a re-index is not a repo write). Skipped with --no-gitnexus-trigger and under pytest unless a fake `script` is injected. Never raises and never
    fails the dispatch; the outcome is logged to sweep.log and returned.
    """
    if not enabled:
        out = "skipped:flag"
    elif script is None and os.environ.get("PYTEST_CURRENT_TEST"):
        out = "skipped:test"
    else:
        try:
            r = (runner or subprocess.run)([sys.executable, str(script or GNX_TRIGGER), "trigger", "--batch-id", batch_id],
                                           capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
            out = f"rc={r.returncode} {(r.stdout or r.stderr or '').strip()[-200:]}"
        except Exception as e:  # noqa: BLE001 - the trigger never fails a dispatch
            out = f"error:{type(e).__name__}: {str(e)[:150]}"
    try:
        _sweep_log(f"gitnexus-trigger batch={batch_id} {out}")
    except Exception:  # noqa: BLE001
        pass
    return out


def run(tasks: list[dict], endpoint: str, out: Path, apply: bool, use_reviewer: bool, family: str = "local", gnx_trigger: bool = True,
        wall_budget: dict | None = None, check_fresh: bool = True) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    gitnexus_trigger(run_id, gnx_trigger)
    ledger = out / "ledger.jsonl"
    rows = []
    for n, task in enumerate(tasks):
        task = schema.apply_wall_budget(task, wall_budget)      # fix 1: wall_s from the measured rate, when given
        tdir = out / f"t{n:02d}"
        tdir.mkdir(exist_ok=True)
        t0 = time.time()
        row = {"n": n, "key": task["key"], "handoff": task["handoff"], "repo": task["repo"], "kind": task.get("kind"),
               "tier": task.get("tier"), "family": family, "wall_budget_s": task["budget"].get("wall_s")}
        try:
            repo, lane, base = make_lane(task, tdir, f"taskflow/{run_id}/{n:02d}-{hashlib.sha1(str(tdir).encode()).hexdigest()[:6]}")  # r4: same-second collision
        except (subprocess.CalledProcessError, LaneRefused) as e:
            row.update(verdict="error", reason="lane", failure_class="harness",
                       detail=(getattr(e, "stderr", None) or str(e))[-300:])
            rows.append(row); ledger.open("a").write(json.dumps(row) + "\n")
            continue
        pkt_acc = task.get("acceptance") if task.get("brief_state") == "fresh" else None
        try:
            why = stale_packet(task, lane) if check_fresh else None
            if why:                                              # r8c fix 3: done packets never reach the model
                row.update(verdict="skipped", reason="stale-packet", failure_class="task", detail=why)
                raise _EndRun()
            p1 = phase1_or_skip(task, lane, tdir, endpoint, family)
            if pkt_acc and task.get("acceptance") != pkt_acc:   # fix 2 (r8b MM-5): a re-merged origin/main brief
                row["acceptance_restored"] = {"merged": task.get("acceptance"), "packet": pkt_acc}
                task["acceptance"] = pkt_acc                    # never replaces the packet's fresh acceptance
            if p1 is not None:
                row["brief_phase"] = {k: p1.get(k) for k in ("ok", "attempts", "brief_path", "accepted", "missing",
                                                             "skipped")}
                if not p1["ok"] and not p1.get("skipped"):
                    row.update(verdict="needs-brief", reason="NEEDS-BRIEF:" + ";".join(p1.get("missing") or [])[:200],
                               failure_class=needs_brief_class(task))
                    row["tag"] = tag_needs_brief(task, tdir, row["reason"], apply)   # box_index then skips the box
                    raise _EndRun()
            if task.get("external_readonly_inputs") and (failure := external_refs.verify(lane, task)):
                row.update(verdict="error", reason="external-input-changed", failure_class="harness", detail=failure)
                raise _EndRun()
            lane_was_live = not lane_destroyed(lane)
            w = local_llm.spawn(task, lane, tdir / "worker", endpoint, family=family)
            if lane_was_live and lane_destroyed(lane):                            # r8g fix 2 (r8f MM-5): the worker removed its own lane
                row.update(verdict="error", reason="lane-destroyed-by-worker", failure_class="harness",
                           detail=f"{lane} is gone or no longer a git worktree after the worker ran; tools: "
                                  + ",".join(sorted({t for t in w.get("tools") or [] if "worktree" in t}) or ["?"]),
                           model=w.get("model"), rc=w.get("rc"), timed_out=w.get("timed_out"),
                           steps=(w.get("usage") or {}).get("steps"), tools=(w.get("tools") or [])[:40])
                raise _EndRun()
            committed = commit_lane(lane, task)
            if str(lane) in COMMIT_REPORTS:
                row["commit_tidy"] = COMMIT_REPORTS.pop(str(lane))      # r8e fix 2: reported, never silent
            reviewer = reviewer_for(endpoint, w["model"]) if use_reviewer else None
            v = verify.verify(task, lane, base, {"verdict": (w.get("result") or {}).get("summary", "")}, reviewer)
            if committed:
                (tdir / "diff.patch").write_text(_git(lane, "diff", f"{base}..HEAD").stdout)
            u = w["usage"]
            row.update(model=w["model"], rc=w["rc"], timed_out=w["timed_out"], steps=u["steps"],
                       tokens={"prompt": u["input"] + u["cache_read"], "cached": u["cache_read"],
                               "uncached": u["input"], "output": u["output"]},  # opencode `input` excludes cache reads
                       review_tokens=(v.get("review") or {}).get("usage"), claimed=w.get("result"),
                       verdict=v["verdict"], reason=v["reason"], checks=v["checks"],
                       failure_class=failure_class(w, v, task), worker_wall_s=w["wall_s"], tools=w["tools"][:40], edits=w.get("edits"), nudged=w.get("nudged"),
                       tool_errors=(w.get("tool_errors") or [])[:5],
                       errors=w["errors"][:3])
            if v.get("hold"):
                row["held"] = v["hold"]       # D3: accepted: pending -> the owner accepts brief + result at wrap-up
            if apply and v["verdict"] == "verified" and not v.get("hold"):
                row["applied"] = apply_tick(task, lane, v, w)
        except _EndRun:
            pass
        except Exception as e:  # noqa: BLE001 - one task never stops the batch
            row.update(verdict="error", reason=type(e).__name__, failure_class="harness", detail=str(e)[:300])
        finally:
            failed_with_work = row.get("verdict") in ("rejected", "error", "unchecked") and row.get("reason") != "no-change"
            if row.get("reason") == "lane-destroyed-by-worker":
                drop_lane(repo, lane)                           # nothing to keep; clears the lane meta (never prune)
            elif failed_with_work:
                keep_lane(lane, f"{row.get('verdict')}:{row.get('reason')}")
                row["lane_kept"] = str(lane)
            else:
                drop_lane(repo, lane)
        row["wall_s"] = round(time.time() - t0, 1)
        rows.append(row)
        with ledger.open("a") as f:
            f.write(json.dumps(row) + "\n")
    try:                                   # automatic orphan / expiry sweep at the end of every dispatch run
        sw = sweep_lanes()
        if sw.get("removed") or sw.get("failed"):
            with ledger.open("a") as f:
                f.write(json.dumps({"sweep": sw, "at": time.time()}) + "\n")
    except Exception as e:  # noqa: BLE001 - the sweep never fails a batch
        _sweep_log(f"sweep error {type(e).__name__}: {e}")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--keys", default="")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--out")
    r = sub.add_parser("run")
    r.add_argument("--tasks", required=True)
    r.add_argument("--endpoint", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--apply", action="store_true")
    r.add_argument("--reviewer", action="store_true")
    r.add_argument("--no-gitnexus-trigger", action="store_true")
    r.add_argument("--wall-budget", default="", help='JSON, e.g. {"prefill_tok_s":111,"decode_tok_s":17.4} (schema.WALL_BUDGET_DEFAULTS)')
    c = sub.add_parser("codex", help="route eligible boxes to unassisted Codex lanes (harness/codex.py)")
    c.add_argument("--file", action="append", default=[], help="handoff file(s) to draw from (default: churn files)")
    c.add_argument("--scope", choices=("default", "hygiene"), default="default")
    c.add_argument("--width", type=int, choices=range(1, 5), default=1)
    c.add_argument("--run-limit-s", type=float, default=3600)
    c.add_argument("--max-boxes", type=int, default=3)
    c.add_argument("--out", default="")
    c.add_argument("--apply", action="store_true", help="tick verified DONE / tag NEEDS-OWNER and push")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    c.add_argument("--max-rounds", type=int, default=10)
    c.add_argument("--trailer", action="append", default=[], help="commit trailer for lane + tick commits")
    c.add_argument("--d9-ack", default=os.environ.get("EPYC_D9_ACK", ""))
    sw = sub.add_parser("sweep")
    sw.add_argument("--release-filed", action="store_true",
                    help="also drop kept lanes whose row has a FILED marker in filing-done/")
    a = ap.parse_args(argv)
    if a.cmd == "codex":
        from taskflow.harness import codex as CX
        rows = CX.dispatch(out=Path(a.out) if a.out else CX.OUT_DEFAULT, files=tuple(a.file) or (None if a.scope == "hygiene" else CX.DEFAULT_FILES),
                           scope=a.scope, width=a.width, run_limit_s=a.run_limit_s,
                           n=a.max_boxes, apply=a.apply, dry_run=a.dry_run, codex=a.codex_bin, max_rounds=a.max_rounds,
                           trailers=a.trailer, env_ack=a.d9_ack)
        print(json.dumps(rows, indent=1))
        return 0
    if a.cmd == "sweep":
        print(json.dumps(sweep_lanes(release_filed=a.release_filed), indent=1))
        return 0
    if a.cmd == "plan":
        tasks = plan([k for k in a.keys.split(",") if k] or None, a.top)
        s = json.dumps(tasks, indent=1)
        Path(a.out).write_text(s) if a.out else print(s)
        return 0
    rows = run(json.loads(Path(a.tasks).read_text()), a.endpoint, Path(a.out), a.apply, a.reviewer, gnx_trigger=not a.no_gitnexus_trigger,
               wall_budget=json.loads(a.wall_budget) if a.wall_budget else None)
    print(json.dumps({"attempted": len(rows), "verified": sum(r.get("verdict") == "verified" for r in rows)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
