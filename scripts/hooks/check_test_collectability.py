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

Exit 0 = clean · 1 = a defective file · 2 = usage error. Never blocks a test run.
"""
from __future__ import annotations

import ast
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
        "CASES table drives a PreToolUse hook against the real shared repo; its dirty "
        "fixture writes into the repo root. Kept self-run so a bare pytest cannot touch it.",
    "scripts/coordination/tests/test_unblock_artifact.py":
        "self-runner over coordination artifacts; collectable form not yet reviewed for "
        "shared-state writes. Exempt until it is.",
}

FIXTURE_NAMES = frozenset({
    "tmp_path", "tmpdir", "monkeypatch", "capsys", "capfd", "caplog",
    "request", "pytestconfig", "recwarn", "tmp_path_factory",
})


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
    sibs = [q for q in parent.glob("test_*.py") if q.is_file()]
    if len(sibs) < 2:
        return False
    self_runners = 0
    for q in sibs:
        collectable, _ = analyse(q)
        if not collectable and has_main_block(q):
            self_runners += 1
    return self_runners > 0


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
        paths = [
            p for p in repo.rglob("test_*.py")
            if not any(part in skip or part.startswith(".venv") for part in p.parts)
        ]
    paths = [p for p in paths if p.is_file() and p.name.startswith("test_")]

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
