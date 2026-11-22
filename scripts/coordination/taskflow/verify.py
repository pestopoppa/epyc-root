#!/usr/bin/env python3
"""taskflow/verify.py — mechanical verification of one worker result (DESIGN.md §2.5), plus an optional reviewer hook.

verify(task, lane_dir, base_ref, evidence, reviewer=None) -> {"verdict": "verified"|"rejected"|"unchecked", checks}

Checks, in order (the first failing one decides `rejected`):
  commit       the lane has >= 1 commit over base_ref (the dispatcher commits the worker's tree)
  nonempty     the commit changes at least one path
  forbidden    no changed path matches task.forbidden (unless the box names that exact path as an input)
  pathspec     every changed path is in task.inputs ∪ task.outputs, or a new test file under tests/
  tests        every task.test_cmds command exits 0 in the lane (timeout 300 s); results go into evidence.commands
  done_when    scripts/handoffs/done_when.check(task.done_when, evidence) -- "fail" rejects; "unchecked" defers
  acceptance   (task-brief layer P4) the brief's acceptance command runs with the tests when it is a runnable shape;
               its result goes into evidence.acceptance and into the reviewer input
The task's own brief sidecar (task.brief_path, committed by phase 1) is exempt from forbidden/pathspec and does not
count as a change. A verified result whose brief is `accepted: pending` carries hold="accepted-pending" (D3): the
dispatcher never ticks it; the owner accepts brief + result at wrap-up.
Then: done_when ok -> verified. done_when unchecked -> the reviewer hook decides (done -> verified, else rejected);
no reviewer -> "unchecked" (never ticked).
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEST_TIMEOUT_S = 300


def _git(lane: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(lane), *args], capture_output=True, text=True, check=True).stdout


def changed_paths(lane: Path, base_ref: str) -> list[str]:
    return [p for p in _git(lane, "diff", "--name-only", f"{base_ref}..HEAD").splitlines() if p.strip()]


def brief_paths(task: dict) -> set[str]:
    """Paths the brief's `where` names in THIS task's repo (`repo:path::symbol` -> path)."""
    out = set()
    for w in task.get("where") or []:
        w = str(w)
        repo, _, rest = w.partition(":") if ":" in w.split("::")[0] else (task.get("repo"), "", w)
        if repo == task.get("repo") and rest:
            out.add(rest.split("::")[0])
    return out


def forbidden_hits(paths: list[str], task: dict) -> list[str]:
    named = set(task.get("inputs") or []) | set(task.get("outputs") or []) | brief_paths(task)
    dirs = tuple(n for n in named if n.endswith("/")) or ("\0",)
    return [p for p in paths if p not in named and not p.startswith(dirs)
            and any(fnmatch.fnmatch(p, g) for g in task.get("forbidden") or [])]


_NAMED = re.compile(r"(?<![\w/.:-])((?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]{1,6})(?![\w/])")


_NEGATED = re.compile(r"\b(?:not|never|don'?t|avoid|without|non-goal|leave\s+\S+\s+(?:alone|untouched))\b", re.I)


def approach_new_paths(task: dict) -> set[str]:
    """Repo-relative file paths the brief's approach (or acceptance) names. r8b TU-GR-1: the approach said "Add
    scripts/.../harness/isolation.py" and the acceptance ran .../tests/test_grader_isolation.py; the worker wrote exactly
    those two files and was rejected outside-pathspec because `where` omitted them (fix 4). A path named only in a
    negated clause ("do NOT touch src/x.py") or in non_goals is not admitted."""
    txt = " ".join(str(task.get(k) or "") for k in ("approach", "acceptance"))
    clauses = [c for c in re.split(r"[.;\n]\s|\n", txt) if not _NEGATED.search(c)]
    ng = " ".join(str(x) for x in task.get("non_goals") or [])
    banned = {m.group(1) for m in _NAMED.finditer(ng)}
    return {m.group(1) for c in clauses for m in _NAMED.finditer(c)
            if (not m.group(1).startswith((".", "/")) or m.group(1).startswith((".claude/", ".github/")))
            and m.group(1) not in banned}


_BARE = re.compile(r"(?<![\w/.-])([\w-]+(?:\.[\w-]+)*\.(?:py|sh|md|json|ya?ml|toml|txt|js|ts))(?![\w/])")


def approach_bare_names(task: dict) -> set[str]:
    """Bare file names (no directory) the approach names outside negated clauses / non_goals. r8c NUMA-DECOUPLE-1:
    "New test_decision_grade_decouple.py" next to the `where` test file."""
    txt = " ".join(str(task.get(k) or "") for k in ("approach", "acceptance"))
    ng = " ".join(str(x) for x in task.get("non_goals") or [])
    banned = {m.group(1) for m in _BARE.finditer(ng)}
    return {m.group(1) for c in re.split(r"[.;\n]\s|\n", txt) if not _NEGATED.search(c)
            for m in _BARE.finditer(c) if m.group(1) not in banned}


def outside_pathspec(paths: list[str], task: dict, added: set[str] | frozenset = frozenset(),
                     modified: set[str] | frozenset = frozenset()) -> list[str]:
    """`added` / `modified`: the lane's A / M paths. An approach-named path is admitted when the lane added it (r8b
    fix 4) or modified a file that already exists in base (r8c fix 4, NUMA-DECOUPLE-1: the decouple test the approach
    names existed in base and was rejected). Unnamed junk (r8c `tmp_extract_refs.py`) stays out."""
    allowed = (set(task.get("inputs") or []) | set(task.get("outputs") or []) | brief_paths(task)
               | (approach_new_paths(task) & (set(added) | set(modified))))
    touched = set(added) | set(modified)
    sib = {str(Path(a).parent) for a in allowed if not a.endswith("/")}
    bare = approach_bare_names(task)
    allowed |= {p for p in touched if Path(p).name in bare and str(Path(p).parent) in sib}   # named sibling file
    dirs = tuple(a for a in allowed if a.endswith("/"))
    return [p for p in paths if p not in allowed and not p.startswith(dirs or ("\0",))
            and not (p.startswith("tests/") and Path(p).name.startswith("test_"))]


def run_tests(lane: Path, cmds: list[str]) -> list[dict]:
    out = []
    for c in cmds:
        try:
            r = subprocess.run(c, shell=True, cwd=str(lane), capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
            out.append({"cmd": c, "rc": r.returncode, "tail": (r.stdout + r.stderr)[-600:]})
        except subprocess.TimeoutExpired:
            out.append({"cmd": c, "rc": 124, "tail": "timeout"})
    return out


_RUNNABLE = re.compile(r"^(?:pytest|python3?|bash|make|grep)\s")


_CD = re.compile(r"^cd\s+(\S+)\s*&&\s*(.+)$")


def lane_cmd(cmd: str | None, task: dict) -> str | None:
    """`cd <the task repo's shared-clone path> && X` -> `X` (run in the lane, which IS that repo at origin/main).
    r7 prep: hand-written briefs name `cd /workspace/repos/<repo> && pytest ...`, which neither the verifier
    (_RUNNABLE) nor the worker's shell policy (no cd/&&) could run, and which would test the SHARED clone."""
    a = " ".join(str(cmd or "").strip().strip("`").split())
    m = _CD.match(a)
    if m:
        d = m.group(1).rstrip("/")
        repo = str(task.get("repo") or "")
        roots = {"/workspace"} if repo == "epyc-root" else set()
        roots |= {f"/workspace/repos/{repo}", f"/mnt/raid0/llm/{repo}"}
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from taskflow import schema as _S
            roots.add(str(_S.REPOS.get(repo, "")).rstrip("/"))
        except Exception:  # noqa: BLE001
            pass
        finally:
            sys.path.pop(0)
        if d in roots:
            a = m.group(2).strip()
    return a or None


def acceptance_cmd(task: dict) -> str | None:
    a = lane_cmd(task.get("acceptance"), task)
    return a if a and _RUNNABLE.match(a) else None


def review_prompt(task: dict, diff: str) -> str:
    """Reviewer input (P4, §7): verbatim box + done-when + acceptance and its result + non-goals + the diff."""
    acc = task.get("acceptance")
    res = task.get("acceptance_result")
    res_txt = ("(not run: not a runnable command)" if res is None else
               f"rc={res.get('rc')}\n{str(res.get('tail') or '')[-400:]}")
    ng = task.get("non_goals") or []
    return ("# REVIEW\nYou review a worker's diff for the box below. Answer ONLY JSON "
            '{"verdict":"done|not_done|drift","reason":"<=150 chars"}. done = the diff fully does what the box '
            "asks AND meets its DONE WHEN; not_done = partial, wrong, or the DONE WHEN is not met; drift = changes "
            "things the box did not ask for, or does any NON-GOAL. Check the DONE WHEN clause item by item.\n\n## BOX\n"
            + task["goal"] + "\n\n## DONE WHEN\n" + str(task.get("done_when") or "(see box)")
            + "\n\n## ACCEPTANCE\n" + (str(acc) if acc else "(no brief acceptance)")
            + "\n\n## ACCEPTANCE RESULT\n" + res_txt
            + "\n\n## NON-GOALS\n" + ("\n".join(f"- {g}" for g in ng) if ng else "(none stated)")
            + "\n\n## DIFF\n" + diff[:12000])


def _done_when():
    sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
    try:
        import done_when
        return done_when
    finally:
        sys.path.pop(0)


def verify(task: dict, lane: Path, base_ref: str, evidence: dict | None = None, reviewer=None) -> dict:
    ev = dict(evidence or {})
    checks: list[dict] = []

    def rec(name, ok, why=""):
        checks.append({"check": name, "ok": ok, "why": why})
        return ok

    n = len([x for x in _git(lane, "rev-list", f"{base_ref}..HEAD").split() if x])
    if not rec("commit", n > 0, f"{n} commit(s) over {base_ref[:12]}"):
        return {"verdict": "rejected", "reason": "no-change", "checks": checks}
    own_brief = task.get("brief_path")
    allp = changed_paths(lane, base_ref)
    paths = [p for p in allp if p != own_brief]
    if own_brief and own_brief in allp:
        ev["brief_paths"] = [own_brief]
    ev["paths"] = paths
    if not rec("nonempty", bool(paths)):
        return {"verdict": "rejected", "reason": "no-change", "checks": checks}
    bad = forbidden_hits(paths, task)
    if not rec("forbidden", not bad, ",".join(bad)):
        return {"verdict": "rejected", "reason": "forbidden-path", "checks": checks, "evidence": ev}
    added = {p for p in _git(lane, "diff", "--name-only", "--diff-filter=A", f"{base_ref}..HEAD").splitlines() if p.strip()}
    modified = {p for p in _git(lane, "diff", "--name-only", "--diff-filter=M", f"{base_ref}..HEAD").splitlines() if p.strip()}
    out = outside_pathspec(paths, task, added, modified)
    if not rec("pathspec", not out, ",".join(out)):
        return {"verdict": "rejected", "reason": "outside-pathspec", "checks": checks, "evidence": ev}
    cmds = list(task.get("test_cmds") or [])
    acc = acceptance_cmd(task)
    if acc and acc not in [" ".join(c.split()) for c in cmds]:
        cmds.append(acc)
    runs = run_tests(lane, cmds)
    ev["commands"] = [{"cmd": r["cmd"], "rc": r["rc"]} for r in runs]
    acc_run = next((r for r in runs if acc and " ".join(r["cmd"].split()) == acc), None)
    if acc_run:
        ev["acceptance"] = {"cmd": acc, "rc": acc_run["rc"]}
    failed = [r for r in runs if r["rc"] != 0]
    if not rec("tests", not failed, "; ".join(f"{r['cmd']} rc={r['rc']}" for r in failed)):
        return {"verdict": "rejected", "reason": "tests-fail", "checks": checks, "evidence": ev,
                "test_tail": failed[0]["tail"]}
    res, why = _done_when().check(task.get("done_when"), ev, str(lane))
    rec("done_when", res != "fail", f"{res}: {why}")
    if res == "fail":
        return {"verdict": "rejected", "reason": "done-when-fail", "checks": checks, "evidence": ev}
    hold = {"hold": "accepted-pending"} if task.get("brief_accepted") == "pending" else {}
    if res == "ok":
        return {"verdict": "verified", "reason": "mechanical", "checks": checks, "evidence": ev, **hold}
    if reviewer is None:
        return {"verdict": "unchecked", "reason": "no-machine-done-when", "checks": checks, "evidence": ev}
    diff = _git(lane, "diff", f"{base_ref}..HEAD", "--", ".", *([f":(exclude){own_brief}"] if own_brief else []))
    rv = reviewer(dict(task, acceptance_result=acc_run), diff) or {}
    rec("reviewer", rv.get("verdict") == "done", f"{rv.get('verdict')}: {str(rv.get('reason', ''))[:200]}")
    ok = rv.get("verdict") == "done"
    return {"verdict": "verified" if ok else "rejected",
            "reason": "reviewer-" + str(rv.get("verdict")), "checks": checks, "evidence": ev, "review": rv,
            **(hold if ok else {})}
