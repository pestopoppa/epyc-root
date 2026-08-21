#!/usr/bin/env python3
"""Refuse a `test_*.py` that can report success while executing nothing.

TWO SHAPES, both measured on 2026-08-20 and both nearly trusted:

  A. pytest-style file (``test_*`` functions taking fixtures) with NO ``__main__``.
     ``python3 the_file.py`` executes NOTHING and exits 0. A session read that
     green exit as a real pass
     (epyc-inference-research/scripts/benchmark/test_v7_quality_gate_runner.py).

  B. self-runner (logic in ``__main__``) with NO collectable ``test_*`` function.
     ``pytest the_file.py`` collects 0 and reports success having run nothing
     (scripts/hooks/tests/test_commit_hygiene.py, and the merge-gate and
     unblock-artifact suites beside it).

WHY A LINT AND NOT A conftest COLLECTION FLOOR. The obvious fix -- raise when a
test file yields 0 items -- has to run inside pytest, where a mis-fire breaks
every invocation for every session. It also cannot express "this file is a
self-runner ON PURPOSE": scripts/coordination/tests/test_merge_gate.py overwrites
coordination/session-bus/human_only_paths.sha256 to simulate drift and restores it
in a finally, so making it collectable would mutate a shared trust-boundary file on
every repo-wide test run, and an interrupted run would leave the fleet's merge gate
failed closed. A lint runs at authoring time, cannot break a test run, and forces
each exemption to be written down with a reason.

DISCOVERY. pytest's default ``python_files`` is ``test_*.py`` AND ``*_test.py``;
globbing only the first hid a self-runner that printed "Regression: YES" and exited 0
(research seal_multi_role_test.py, since renamed seal_multi_role_regression_check.py).
Both globs are walked, and an explicitly passed
path of EITHER shape is accepted -- silently dropping a path handed to the gate is
itself a vacuous pass.

ADVISORY: assertion density. A file whose collectable tests contain no assertion in
aggregate is reported, never blocked. Resolution follows ONE level of same-file
indirection (a test calling a local helper that asserts IS asserting), and anything
unresolvable counts as asserting -- under-flagging is safe for an advisory, while a
lint with false positives gets switched off.

Exit 0 = clean · 1 = a defective file · 2 = usage error. Never blocks a test run.
"""
from __future__ import annotations

import ast
import builtins
import functools
import sys
from pathlib import Path

#: Self-runners that must NOT become pytest-collectable, each with the reason.
#: An entry here is a decision, not a silencer -- it says "running this under a
#: bare `pytest` would be WORSE than not collecting it".
DELIBERATE_SELF_RUNNERS: dict[str, str] = {
    "scripts/coordination/tests/test_merge_gate.py":
        "mutates coordination/session-bus/human_only_paths.sha256 (drift simulation, "
        "restored in a finally). Collectable => every repo-wide pytest run rewrites a "
        "shared trust-boundary file; an interrupted run leaves the merge gate failed closed.",
    "scripts/hooks/tests/test_commit_hygiene.py":
        "CASES drive the live PreToolUse hook against the REAL shared repo (cwd=REPO_ROOT, "
        "git subprocesses per case), and main() writes .hook_dirty_probe into the repo root "
        "for the path-restore case. Collectable => two parallel repo-wide pytest runs race on "
        "that probe (one run's unlink flips the other's expected rc 2 to 0), and an interrupted "
        "run leaves a stray untracked file that rides into the next `git add -A`. The FRESH/STALE "
        "cases also key off real FETCH_HEAD mtime, i.e. flaky-by-design off the self-run path. "
        "Bridging needs a throwaway clone, not a bridge. Reviewed and kept 2026-08-21 (VT-4).",
}

FIXTURE_NAMES = frozenset({
    "tmp_path", "tmpdir", "monkeypatch", "capsys", "capfd", "caplog",
    "request", "pytestconfig", "recwarn", "tmp_path_factory",
})

#: pytest's default ``python_files``. BOTH, or the gate has a blind spot by name.
TEST_FILE_GLOBS = ("test_*.py", "*_test.py")


def is_test_filename(name: str) -> bool:
    return name.startswith("test_") or name.endswith("_test.py")


#: Callables that ARE an assertion however they were imported.
ASSERTING_CALL_NAMES = frozenset({"raises", "fail", "warns", "assert_"})


@functools.lru_cache(maxsize=None)
def analyse(path: Path) -> tuple[list[str], list[str]]:
    """Return (collectable_test_names, fixture_using_test_names) plus __main__ flag."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return [], []
    collectable, fixture_using = [], []

    def consider(node, drop_self: bool) -> None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        if not node.name.startswith("test_"):
            return
        args = [a.arg for a in node.args.args]
        if drop_self and args and args[0] in ("self", "cls"):
            args = args[1:]
        # pytest COLLECTS any test_* callable regardless of its parameters. A
        # parameter it cannot resolve becomes a loud setup ERROR, which is the
        # opposite of a vacuous pass -- so arg shape must not decide collectability.
        # Filtering on a builtin-fixture allowlist misjudged every suite using a
        # conftest fixture: it reported ordinary class-based orchestrator suites
        # (e.g. tests/unit/test_repl_state.py, TestREPLStateCheckpoint) as "runs
        # nothing either way". Third false-positive class found before filing.
        collectable.append(node.name)
        if args:
            fixture_using.append(node.name)

    for node in tree.body:
        consider(node, drop_self=False)
        # pytest also collects methods of `Test*` classes -- missing them made this
        # lint report 237 orchestrator files as "runs nothing either way" when they
        # were ordinary class-based suites. A lint with false positives gets switched
        # off, so it must model the collector it is reasoning about.
        # ANY top-level class, not just `Test*`: pytest collects unittest.TestCase
        # subclasses by base class, whatever they are named. Restricting to the
        # Test* prefix reported scripts/coordination/tests/test_promote_lane.py --
        # from which pytest collects 22 tests -- as running nothing. Over-counting
        # collectables is the SAFE direction for a gate; under-counting blocks
        # legitimate commits, and this one was already live when it was found.
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                consider(sub, drop_self=True)
    return collectable, fixture_using


@functools.lru_cache(maxsize=None)
def has_main_block(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.If):
            src = ast.dump(node.test)
            if "__main__" in src:
                return True
    return False


@functools.lru_cache(maxsize=None)
def _mixed_convention_dir(parent: Path) -> bool:
    """Does this file's directory hold BOTH pytest suites and self-runners?"""
    sibs = sorted({q for g in TEST_FILE_GLOBS for q in parent.glob(g) if q.is_file()})
    if len(sibs) < 2:
        return False
    self_runners = 0
    for q in sibs:
        collectable, _ = analyse(q)
        if not collectable and has_main_block(q):
            self_runners += 1
    return self_runners > 0


_BUILTIN_NAMES = frozenset(dir(builtins))


def _call_target(node: ast.Call) -> tuple[str, str | None]:
    """Return (kind, name) for a call: ('name', f) / ('self', m) / ('attr', a)."""
    fn = node.func
    if isinstance(fn, ast.Name):
        return "name", fn.id
    if isinstance(fn, ast.Attribute):
        if isinstance(fn.value, ast.Name) and fn.value.id in ("self", "cls"):
            return "self", fn.attr
        return "attr", fn.attr
    return "other", None


@functools.lru_cache(maxsize=None)
def _assertion_model(path: Path) -> tuple[dict[str, bool], frozenset[str], frozenset[str]]:
    """Per-function 'does it assert (directly)' map, local def names, imported names."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return {}, frozenset(), frozenset()

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                imported.add(a.asname or a.name)

    funcs: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.setdefault(node.name, node)

    direct: dict[str, bool] = {}
    for name, node in funcs.items():
        found = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assert):
                found = True
                break
            if isinstance(sub, ast.Call):
                kind, target = _call_target(sub)
                if target and (target.startswith("assert") or target in ASSERTING_CALL_NAMES):
                    found = True
                    break
        direct[name] = found
    return direct, frozenset(funcs), frozenset(imported)


def _function_asserts(path: Path, node: ast.AST, depth: int = 1) -> bool:
    """Does this function assert, following `depth` levels of same-file calls?

    Unresolvable targets count as ASSERTING: an advisory that over-flags gets
    switched off, and a missed zero-assertion file costs only this notice.
    """
    direct, local_defs, imported = _assertion_model(path)
    calls: list[tuple[str, str]] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Assert):
            return True
        if isinstance(sub, ast.Call):
            kind, target = _call_target(sub)
            if target is None:
                continue
            if target.startswith("assert") or target in ASSERTING_CALL_NAMES:
                return True
            calls.append((kind, target))

    if depth <= 0:
        return False

    _, funcs_tree = _parsed_funcs(path)
    for kind, target in calls:
        if kind == "attr":
            continue                      # module/object method from elsewhere
        if target in local_defs:
            if direct.get(target) or _function_asserts(path, funcs_tree[target], depth - 1):
                return True
            continue
        if kind == "self":
            return True                   # inherited helper -- unresolvable, assume asserts
        if target in imported or target in _BUILTIN_NAMES:
            continue
        return True                       # bare name defined nowhere we can see
    return False


@functools.lru_cache(maxsize=None)
def _parsed_funcs(path: Path) -> tuple[bool, dict[str, ast.AST]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return False, {}
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return True, out


def collectable_tests_assert(path: Path) -> bool:
    """Do this file's collectable test_* functions assert, in aggregate?"""
    ok, funcs = _parsed_funcs(path)
    if not ok:
        return True
    tests = [n for name, n in funcs.items() if name.startswith("test_")]
    if not tests:
        return True
    return any(_function_asserts(path, t) for t in tests)


def check(repo: Path, paths: list[Path]) -> tuple[list[str], list[str]]:
    """Return (blocking_problems, advisories)."""
    problems: list[str] = []
    advisories: list[str] = []
    for p in paths:
        rel = p.relative_to(repo).as_posix()
        collectable, fixture_using = analyse(p)
        main_block = has_main_block(p)

        if not collectable and not main_block:
            problems.append(f"{rel}: no collectable test_* AND no __main__ -- runs nothing either way")
            continue

        if not collectable:                                  # shape B
            if rel in DELIBERATE_SELF_RUNNERS:
                continue
            problems.append(
                f"{rel}: SELF-RUNNER -- `pytest` collects 0 here and reports success.\n"
                f"    Add a bridge:  def test_all() -> None: assert main() == 0\n"
                f"    (reference: scripts/coordination/tests/test_bus_supervisor.py)\n"
                f"    Or, if it must NOT be collectable, add it to DELIBERATE_SELF_RUNNERS\n"
                f"    in {Path(__file__).name} WITH the reason."
            )
            continue

        # Shape A is only a HAZARD in a MIXED-CONVENTION directory -- one holding
        # both pytest suites and self-runners. There, someone reasonably runs
        # `python3 the_file.py` and trusts the exit code, which is exactly the
        # 2026-08-20 misread. In a pure-pytest tree with a conftest nobody invokes
        # files directly, so flagging all ~1000 of them would be noise that gets the
        # whole lint switched off. Measured: unrefined, this fired on 989 of 1206
        # files; refined, it fires only where the ambiguity actually exists.
        # ADVISORY ONLY. The directory-level "mixed convention" proxy is too coarse to
        # block on: ONE self-runner in a 450-file tests/ dir flags every sibling
        # (measured on epyc-orchestrator). Shape A is also normal and harmless inside a
        # repo's collection scope, where nobody invokes files directly. Reported so it
        # is visible, never blocking -- a lint that cries wolf gets switched off.
        if fixture_using and not main_block and _mixed_convention_dir(p.parent):   # shape A
            advisories.append(
                f"{rel}: fixture-based suite with no __main__ -- "
                f"`python3 {rel}` executes nothing and exits 0.\n"
                f"    Add the refusing stanza:\n"
                f"        if __name__ == \"__main__\":\n"
                f"            raise SystemExit(\"REFUSING: pytest-fixture suite; run: \"\n"
                f"                             \"python -m pytest {rel} -q\")"
            )
        # ADVISORY: assertion density. A collectable suite whose tests assert
        # nothing passes for free. Resolution follows one level of same-file
        # indirection so a suite that factors its asserts into helpers is NOT
        # flagged -- that omission would re-create false-positive class #3.
        if not collectable_tests_assert(p):
            advisories.append(
                f"{rel}: {len(collectable)} collectable test(s), ZERO assertions in "
                f"aggregate -- this file passes without checking anything.\n"
                f"    Add assertions, or rename it to check_*/probe_* if it is a probe script."
            )
    return problems, advisories


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"usage: {Path(argv[0]).name} <repo-root> [paths...]", file=sys.stderr)
        return 2
    repo = Path(argv[1]).resolve()
    if not repo.is_dir():
        print(f"not a directory: {repo}", file=sys.stderr)
        return 2

    if len(argv) > 2:
        paths = [Path(a).resolve() for a in argv[2:]]
    else:
        skip = {".git", "__pycache__", "node_modules", "repos", "tmp", "artifacts",
                "worktrees"}   # nested checkouts of THIS repo -- same files, counted twice
        # Skip-matching is RELATIVE to the repo root: matching on absolute parts
        # made every path under a `/tmp/...` checkout invisible to the gate.
        paths = sorted({
            p for glob in TEST_FILE_GLOBS for p in repo.rglob(glob)
            if not any(part in skip or part.startswith(".venv")
                       for part in p.relative_to(repo).parts)
        })
    # An explicitly passed path of EITHER shape is checked. Filtering on
    # `test_` alone silently DROPPED every `*_test.py` handed to the gate by the
    # pre-commit hook -- a vacuous pass in the gate itself.
    paths = [p for p in paths if p.is_file() and is_test_filename(p.name)]

    problems, advisories = check(repo, paths)
    for problem in problems:
        print(f"VACUOUS-PASS: {problem}", file=sys.stderr)
    for note in advisories:
        print(f"advisory: {note}", file=sys.stderr)
    print(f"checked {len(paths)} test file(s); "
          f"{len(problems)} blocking, {len(advisories)} advisory")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
