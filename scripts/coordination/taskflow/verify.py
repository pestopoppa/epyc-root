#!/usr/bin/env python3
"""taskflow/verify.py — mechanical verification of one worker result (DESIGN.md §2.5), plus an optional reviewer hook.

verify(task, lane_dir, base_ref, evidence, reviewer=None) -> {"verdict": "verified"|"rejected"|"unchecked", checks}

Checks, in order (the first failing one decides `rejected`):
  commit       the lane has >= 1 commit over base_ref (the dispatcher commits the worker's tree)
  nonempty     the commit changes at least one path
  forbidden    no changed path matches task.forbidden (unless the box names that exact path as an input)
  pathspec     every changed path is in task.inputs ∪ task.outputs, or a new test file under tests/
  tests        every task.test_cmds command exits 0 in the lane (timeout 300 s); results go into evidence.commands
  acceptance   (task-brief layer P4) the brief's acceptance command runs with the tests when it is a runnable shape;
               its result goes into evidence.acceptance and into the reviewer input
  contract     TU-GR-1 and MM-5 have independent behavioral checks before the verdict can reach the reviewer
  done_when    scripts/handoffs/done_when.check(task.done_when, evidence) -- "fail" rejects; "unchecked" defers
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


_LRANGE = re.compile(r"#L\d+(?:-\d+)?$")   # the `#L<a>(-<b>)?` where-range suffix brief._WHERE accepts


def brief_paths(task: dict) -> set[str]:
    """Paths the brief's `where` names in THIS task's repo (`repo:path::symbol` -> path)."""
    out = set()
    for w in task.get("where") or []:
        w = str(w)
        repo, _, rest = w.partition(":") if ":" in w.split("::")[0] else (task.get("repo"), "", w)
        if repo == task.get("repo") and rest:
            out.add(_LRANGE.sub("", rest.split("::")[0]))   # r8h: `path#L<a>-<b>` names `path` (r8g WS4)
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


_RA_LINE = re.compile(r"^(PASSED|SKIPPED|XFAIL|XPASS|FAILED|ERROR) .*$", re.M)


def ra_lines(text: str, cap: int = 40) -> list[str]:
    """pytest `-rA` short-summary lines (pass / skip / xfail / ...) -- r8e fix 3: the reviewer sees which tests ran."""
    # Preserve the diagnostic after a long test path and launcher prefix on skip lines.
    return [m[0][:(1000 if m[1] == "SKIPPED" else 200)] for m in _RA_LINE.finditer(text or "")][:cap]


def with_ra(cmd: str) -> str:
    """Append `-rA` to a pytest command that does not already pick its own -r report chars."""
    toks = cmd.split()
    if "pytest" in cmd and not any(t.startswith("-r") for t in toks):
        return cmd + " -rA"
    return cmd


def run_tests(lane: Path, cmds: list[str]) -> list[dict]:
    out = []
    for c in cmds:
        try:
            r = subprocess.run(c, shell=True, cwd=str(lane), capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
            out.append({"cmd": c, "rc": r.returncode, "tail": (r.stdout + r.stderr)[-600:],
                        "ra": ra_lines(r.stdout + r.stderr)})
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


# r8e fix 5 (WS4-WAKE-IMPERATIVE): the done-when's "a live woken session acts on one" cannot be shown by the packet
# acceptance. A packet with verify_scope: acceptance-only is reviewed on what the acceptance can show, and its verified
# result is held (never ticks the box; the live clause stays open).
ACCEPTANCE_ONLY = "acceptance-only"
REPRODUCER_ONLY = "reproducer-only"


def verification_scope(task: dict) -> str | None:
    scope = task.get("verify_scope")
    if scope is None and (task.get("id") or task.get("key")) == "LOOP-62":
        # The r8 packets predate the explicit scope field and already declare this calibration.
        if str(task.get("approach") or "").startswith("RE-SCOPED r8") and "xfail" in str(task.get("done_when") or ""):
            return REPRODUCER_ONLY
    return scope


_GUARD = re.compile(r"vacuous|never pass|must (?:yield|fail|raise|report|deny|skip)|pytest\.skip|skip with", re.I)


def approach_guards(task: dict) -> list[str]:
    """The approach's "never pass vacuously" clauses (r8e fix 3: TU-GR-1 think passed a vacuous isolation test)."""
    txt = str(task.get("approach") or "")
    return [c.strip() for c in re.split(r"(?<=[.;])\s+|\n", txt) if c.strip() and _GUARD.search(c)][:8]


# r8e fix 3 (TU-GR-1 think, false verify): the probe returned {"ok": False, "launcher_error": "json-parse-failed"} because
# the launcher exec'd the sentinel dir as $0, and the "isolated launch denies" test asserted only ok is False. A probe
# that errored is not a denial. Deterministic guard: the diff's code produces a launcher_error-shaped result, a test
# asserts a denial through ok/unreachable, and no test line distinguishes a real denial (errno / ENOENT / EACCES /
# launcher_error) from the error.
_LAUNCHER_ERR = re.compile(r"""["'](?:launcher_error|probe_error)["']\s*:|json-parse-failed""")
# r8f fix 1 (TU-GR-1 nothink, false verify): the child printed nothing and `probe_grader_access` mapped empty stdout to
# {"ok": False, "errno": "no-output"}, a denial-shaped result, so the isolation test passed with no isolation. Empty
# child stdout is an error, never a denial. Two shapes: a quoted no-output / empty-stdout token, and an
# `if not <stdout-ish>:` branch that returns a dict carrying `ok: False`.
_EMPTY_STDOUT_DENIAL = re.compile(
    r"""["'](?:no[-_]output|empty[-_](?:stdout|output)|no[-_]stdout)["']"""
    r"""|if\s+not\s+[\w.]*(?:out|stdout|output)\w*(?:\.strip\(\))?\s*:[^\n]*\n(?:[^\n]*\n){0,4}?[^\n]*return\s*\{[^}]*["']ok["']\s*:\s*False""")
_DENIAL_ASSERT = re.compile(r"""assert\s+not\s+[\w.\[\]"'()]*ok\b|\.get\(\s*["']ok["']\s*\)\s*(?:is\s+False|==\s*False)|"""
                            r"""\[\s*["']ok["']\s*\]\s*(?:is\s+False|==\s*False)|assert_\w*unreachable\s*\(""")
_DISCRIMINATES = re.compile(r"\berrno\b|\bE(?:NOENT|ACCES|PERM)\b|launcher_error|probe_error|open_errno")


def _diff_files(diff: str) -> dict[str, tuple[bool, list[str]]]:
    """{path: (new_file, added_lines)} from a unified git diff."""
    out: dict[str, tuple[bool, list[str]]] = {}
    cur, new = None, False
    for ln in diff.splitlines():
        if ln.startswith("diff --git "):
            cur, new = None, False
        elif ln.startswith("new file mode"):
            new = True
        elif ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
            if cur:
                out[cur] = (new, [])
        elif cur and ln.startswith("+") and not ln.startswith("+++"):
            out[cur][1].append(ln[1:])
    return out


def _code_only(src: str, whole: bool) -> str:
    """Source without comments and docstrings (ast for a whole new file; comment strip for a partial hunk)."""
    if whole:
        try:
            import ast
            tree = ast.parse(src)
            for node in ast.walk(tree):
                body = getattr(node, "body", None)
                if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                        and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
                    body.pop(0)
                    if not body:
                        body.append(ast.Pass())
            return ast.unparse(tree)
        except (SyntaxError, ValueError):
            pass
    return "\n".join(re.sub(r"\s#.*$|^\s*#.*$", "", ln) for ln in src.splitlines())


def vacuity_hits(diff: str) -> list[str]:
    """Reasons the acceptance can pass without exercising the thing under test ([] = no finding)."""
    files = _diff_files(diff)
    src, tests = [], []
    for p, (new, lines) in files.items():
        if not p.endswith(".py"):
            continue
        code = _code_only("\n".join(lines), new)
        (tests if Path(p).name.startswith("test_") else src).append((p, code))
    hits = []
    err = [p for p, c in src + tests if _LAUNCHER_ERR.search(c) or _EMPTY_STDOUT_DENIAL.search(c)]
    deny = [p for p, c in tests if _DENIAL_ASSERT.search(c)]
    disc = [p for p, c in tests if _DISCRIMINATES.search(c)]
    if err and deny and not disc:
        hits.append(f"launcher_error: {','.join(err)} returns an error-shaped probe result (launcher_error / empty child stdout mapped to ok=False) and {','.join(deny)} "
                    "asserts a denial without checking errno / launcher_error, so a launcher failure passes as a denial")
    return hits


_CONTROL_LINE = re.compile(r"\bcontrol\b|pytest\.raises|\bfails? on\b", re.I)
_SKIP_LINE = re.compile(r"\bskip(?:s|ped|ping)?\b", re.I)


def reviewer_context(task: dict) -> tuple[list[str], list[str]]:
    """r8h (TF-R8G-REVIEWER-CONTROL, r8g think TU-GR-1): the done-when CONTROL tests (they pass by asserting the failure
    mode) and the packet-SANCTIONED skips (with their reasons). Explicit brief fields `control_tests` /
    `sanctioned_skips` first; otherwise the approach sentences that define them."""
    ctl = [str(x) for x in task.get("control_tests") or []]
    skp = [str(x) for x in task.get("sanctioned_skips") or []]
    sents = [c.strip() for c in re.split(r"(?<=[.;])\s+|\n", str(task.get("approach") or "")) if c.strip()]
    if not ctl:
        ctl = [c for c in sents if _CONTROL_LINE.search(c) and not _SKIP_LINE.search(c)]
    if not skp:
        skp = [c for c in sents if _SKIP_LINE.search(c)]
    return ctl, skp


REVIEW_CONTROL_RULE = (
    "A passing CONTROL meets a 'fails on ...' clause when it establishes the specified trigger and then checks "
    "the expected failure. If the trigger is a reachable artifact, require an assertion on the child's structured "
    "result that it accessed that artifact before pytest.raises. Launcher/setup errors, crashes, and missing or "
    "malformed probe output must fail distinctly; they cannot count as reachability or denial.\n"
    "A SANCTIONED SKIP excuses execution only. Check both the actual skip reason and the predicate in the code: "
    "both must identify the exact allowed condition (e.g. unshare itself reported EPERM), without also accepting "
    "unrelated errors. Even on a sanctioned skip, trace the unexecuted code from launcher argv to child and "
    "assertions. For a mount-based isolation test, verify that the launcher actually hides the sentinel path, "
    "the shell receives the mount target and child argv in the correct positions, and the child checks the same "
    "sentinel and reports a real access denial. Comments, a new namespace alone, or a skip label cannot establish "
    "these facts. Answer not_done for broken or missing logic, a broad skip, or an unwitnessed control trigger. "
    "A correct implementation with the exact sanctioned skip and a witnessed passing control can be done."
)


def _control_block(task: dict) -> str:
    ctl, skp = reviewer_context(task)
    if not (ctl or skp):
        return ""
    return ("\n\n## CONTROL TESTS (pass by asserting the failure mode)\n" + ("\n".join(f"- {c}" for c in ctl) or "(none)")
            + "\n\n## SANCTIONED SKIPS (allowed by the packet, with reasons)\n" + ("\n".join(f"- {c}" for c in skp) or "(none)")
            + "\n\nRULE: " + REVIEW_CONTROL_RULE)


def review_prompt(task: dict, diff: str) -> str:
    """Reviewer input (P4, §7): box, done-when, acceptance and result, non-goals, and the complete diff."""
    acc = task.get("acceptance")
    res = task.get("acceptance_result")
    res_txt = ("(not run: not a runnable command)" if res is None else
               f"rc={res.get('rc')}\n{str(res.get('tail') or '')[-400:]}")
    if res is not None and res.get("ra"):
        res_txt += "\n\n## ACCEPTANCE LOG (pytest -rA: every test's outcome)\n" + "\n".join(res["ra"])
    ng = task.get("non_goals") or []
    approach = str(task.get("approach") or "").strip()
    guards = approach_guards(task)
    return ("# REVIEW\nYou review a worker's diff for the box below. Answer ONLY JSON "
            '{"verdict":"done|not_done|drift","reason":"<=150 chars"}. done = the diff fully does what the box '
            "asks AND meets its DONE WHEN; not_done = partial, wrong, or the DONE WHEN is not met; drift = changes "
            "things the box did not ask for, or does any NON-GOAL. Read deletions, replacements, and added sections in "
            "the diff. For an additive task, deleting unrelated content or duplicating existing rules is drift even "
            "when the requested additions and acceptance both succeed. Check the DONE WHEN clause item by item. A test that "
            "passes without exercising what it claims (e.g. a probe/launcher error counted as a denial) "
            "does not meet the DONE WHEN. Reject skips unless the SANCTIONED SKIPS rule below applies.\n\n## BOX\n"
            + task["goal"] + "\n\n## DONE WHEN\n" + str(task.get("done_when") or "(see box)")
            + ("\n\n## SCOPE: ACCEPTANCE ONLY\nJudge the DONE WHEN only as far as the ACCEPTANCE can show it. A clause "
               "the acceptance cannot show (e.g. a live session acting on it) is out of scope here: not a reason for "
               "not_done, and a done verdict does not close it." if verification_scope(task) == ACCEPTANCE_ONLY else "")
            + ("\n\n## SCOPE: REPRODUCER ONLY\nJudge the calibrated reproducer and its pinned stress recipe. "
               "The underlying source fix remains a separate task." if verification_scope(task) == REPRODUCER_ONLY else "")
            + "\n\n## ACCEPTANCE\n" + (str(acc) if acc else "(no brief acceptance)")
            + "\n\n## ACCEPTANCE RESULT\n" + res_txt
            + "\n\n## NON-GOALS\n" + ("\n".join(f"- {g}" for g in ng) if ng else "(none stated)")
            + ("\n\n## APPROACH\n" + approach if approach else "")
            + _control_block(task)
            + ("\n\n## MUST NOT PASS VACUOUSLY (from the approach)\n" + "\n".join(f"- {g}" for g in guards)
               if guards else "")
            + "\n\n## DIFF\n" + diff)


def _done_when():
    sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
    try:
        import done_when
        return done_when
    finally:
        sys.path.pop(0)


def _candidate_contract(task_id: str, lane: Path, acceptance: str | None) -> str | None:
    if task_id == "TU-GR-1":
        from . import tu_grader_isolation

        return tu_grader_isolation.validate(lane, acceptance or "", TEST_TIMEOUT_S)
    if task_id == "LOOP-62":
        from . import loop_contract

        return loop_contract.validate(lane)
    from . import vision_contract

    ok, why = vision_contract.check(lane)
    return None if ok else why


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
    acc_ra = with_ra(acc) if acc else None              # r8e fix 3: the acceptance runs with -rA for the reviewer
    runs = run_tests(lane, [acc_ra if acc and " ".join(c.split()) == acc else c for c in cmds])
    for r in runs:                                      # evidence / done_when see the command as the packet wrote it
        if acc and " ".join(r["cmd"].split()) == acc_ra:
            r["cmd"], r["ran"] = acc, acc_ra
    ev["commands"] = [{"cmd": r["cmd"], "rc": r["rc"]} for r in runs]
    acc_run = next((r for r in runs if acc and " ".join(r["cmd"].split()) == acc), None)
    if acc_run:
        ev["acceptance"] = {"cmd": acc, "rc": acc_run["rc"]}
    failed = [r for r in runs if r["rc"] != 0]
    if not rec("tests", not failed, "; ".join(f"{r['cmd']} rc={r['rc']}" for r in failed)):
        return {"verdict": "rejected", "reason": "tests-fail", "checks": checks, "evidence": ev,
                "test_tail": failed[0]["tail"]}
    diff = _git(lane, "diff", f"{base_ref}..HEAD", "--", ".", *([f":(exclude){own_brief}"] if own_brief else []))
    vac = vacuity_hits(diff)                            # r8e fix 3: deterministic, before done_when and the reviewer
    if not rec("vacuity", not vac, "; ".join(vac)[:300]):
        return {"verdict": "rejected", "reason": "vacuous-acceptance", "checks": checks, "evidence": ev}
    task_id = task.get("id") or task.get("key")
    scope = verification_scope(task)
    if task_id in ("TU-GR-1", "MM-5") or (task_id == "LOOP-62" and scope == REPRODUCER_ONLY):
        try:
            failure = _candidate_contract(task_id, lane, acc)
        except (ImportError, AttributeError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            rec("candidate-contract", False, f"{task_id}: {str(exc)[:400]}")
            return {"verdict": "rejected", "reason": "contract-unavailable", "checks": checks, "evidence": ev,
                    "test_tail": str(exc)}
        if not rec("candidate-contract", failure is None, f"{task_id}: {failure or 'checked'}"[:400]):
            return {"verdict": "rejected", "reason": "contract-fail", "checks": checks, "evidence": ev,
                    "test_tail": failure}
    res, why = _done_when().check(task.get("done_when"), ev, str(lane))
    rec("done_when", res != "fail", f"{res}: {why}")
    if res == "fail":
        return {"verdict": "rejected", "reason": "done-when-fail", "checks": checks, "evidence": ev}
    hold = {"hold": "accepted-pending"} if task.get("brief_accepted") == "pending" else {}
    if scope in (ACCEPTANCE_ONLY, REPRODUCER_ONLY):
        hold = {"hold": (hold.get("hold") + "," if hold else "") + scope}
    if res == "ok":
        return {"verdict": "verified", "reason": "mechanical", "checks": checks, "evidence": ev, **hold}
    if reviewer is None:
        return {"verdict": "unchecked", "reason": "no-machine-done-when", "checks": checks, "evidence": ev}
    rv = reviewer(dict(task, acceptance_result=acc_run), diff) or {}
    rec("reviewer", rv.get("verdict") == "done", f"{rv.get('verdict')}: {str(rv.get('reason', ''))[:200]}")
    ok = rv.get("verdict") == "done"
    return {"verdict": "verified" if ok else "rejected",
            "reason": "reviewer-" + str(rv.get("verdict")), "checks": checks, "evidence": ev, "review": rv,
            **(hold if ok else {})}
