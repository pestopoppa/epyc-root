#!/usr/bin/env python3
"""Tests for ``scripts/coordination/check_lane_worktree.py``.

The compliant path is tested as hard as the violating one. A worktree guard that
only proves it can say "no" is a guard that will be turned off within a day: the
expensive failure mode here is not missing a violation, it is flagging the
session bus -- which is *supposed* to be written in the shared clone -- and
thereby teaching agents to route around the guard or to break the bus.

So every "not flagged" assertion below also asserts WHY it was not flagged, and
asserts the input set was non-empty. A check that passes because it examined
zero paths is a vacuous pass, and it is the single most common defect this
suite exists to avoid becoming.

Every git operation here happens in a throwaway repository under pytest's
``tmp_path``, created and destroyed by the test. Nothing in this file reads or
writes the real repository's git state; the two host-conditional tests at the
end ``stat()`` real paths and run no git commands at all.
"""

from __future__ import annotations

import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# Import the module under test by path (scripts/ is not an importable package,
# matching the convention in scripts/coordination/tests/test_unblock_artifact.py)
# --------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _REPO_ROOT / "scripts" / "coordination" / "check_lane_worktree.py"


def _load_module():
    """Load the guard by COMPILING ITS CURRENT SOURCE -- never through __pycache__.

    The obvious ``spec_from_file_location`` + ``exec_module`` route goes through
    ``SourceFileLoader``, which accepts a cached ``.pyc`` whenever the source's
    (mtime-in-SECONDS, size) pair is unchanged. That is not a theoretical hole:
    mutation-testing this suite, the one mutation that swapped a single
    character for another single character (``EXIT_LOCATION = 4`` -> ``= 0``,
    turning fail-closed into fail-open) left the file the same size, landed in
    the same wall-clock second, and the tests loaded STALE BYTECODE and passed.
    A guard whose test suite can silently validate a previous version of the
    guard is worse than no suite. Compiling the source text directly removes
    the cache from the path entirely.

    The module is also registered in ``sys.modules`` BEFORE execution, because
    ``@dataclass`` resolves annotations via ``sys.modules[cls.__module__]``; an
    unregistered module makes that lookup return ``None`` and the whole file
    fails to collect with an AttributeError raised inside ``dataclasses``.
    """
    name = "check_lane_worktree_uut"
    source = _MODULE_PATH.read_text()
    mod = types.ModuleType(name)
    mod.__file__ = str(_MODULE_PATH)
    sys.modules[name] = mod
    exec(compile(source, str(_MODULE_PATH), "exec"), mod.__dict__)
    return mod


guard = _load_module()


def test_module_under_test_exists():
    """If this fails, every other test in the file is meaningless."""
    assert _MODULE_PATH.is_file(), f"module under test not found at {_MODULE_PATH}"


# --------------------------------------------------------------------------
# Throwaway repo fixtures
# --------------------------------------------------------------------------

#: Work-plane files seeded into every throwaway clone.
WORK_FILES = (
    "scripts/coordination/check_lane_worktree.py",
    "scripts/coordination/WORKTREE_MIGRATION.md",
    "docs/guides/example.md",
    "handoffs/active/example-handoff.md",
    "tests/coordination/test_example.py",
    ".claude/settings.json",
    "CLAUDE.md",
)

#: Runtime-plane files seeded into every throwaway clone.
RUNTIME_FILES = (
    "coordination/session-bus/queue.jsonl",
    "coordination/session-bus/inbox/mainA.jsonl",
    "coordination/session-bus/heartbeats/mainA.json",
    "coordination/session-bus/tokens/token-queue.md",
    "logs/agent_audit.log",
)


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    # Hermetic: never inherit ambient identity, hooks, templates or a GIT_DIR
    # pointing at the real repository.
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_AUTHOR_NAME": "guard-test",
            "GIT_AUTHOR_EMAIL": "guard-test@example.invalid",
            "GIT_COMMITTER_NAME": "guard-test",
            "GIT_COMMITTER_EMAIL": "guard-test@example.invalid",
        }
    )
    for stray in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_TEMPLATE_DIR"):
        env.pop(stray, None)
    return env


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, env=_git_env()
    )
    assert proc.returncode == 0, f"git {' '.join(args)} failed in {cwd}: {proc.stderr}"
    return proc


def _write(root: Path, rel: str, text: str = "seed\n") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A throwaway stand-in for the shared clone: a repo whose main worktree it is."""
    root = tmp_path / "clone"
    root.mkdir()
    _git(["init", "-b", "main", "."], root)
    _git(["config", "commit.gpgsign", "false"], root)
    for rel in WORK_FILES + RUNTIME_FILES:
        _write(root, rel)
    _git(["add", "-A"], root)
    _git(["commit", "-m", "seed"], root)
    return root


@pytest.fixture
def lane(clone: Path, tmp_path: Path) -> Path:
    """A throwaway lane worktree on ``lane/mainT``, located outside the clone.

    Outside deliberately: the real lane worktrees live at
    /mnt/raid0/llm/worktrees/mains/<agent>, not inside the clone, and a worktree
    nested inside the clone would also pollute the clone's own git status.
    """
    wt = tmp_path / "worktrees" / "mainT"
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(["worktree", "add", "-b", "lane/mainT", str(wt), "main"], clone)
    return wt


def _report(root: Path, paths: list[str] | None):
    loc = guard.detect_location(root)
    return guard.build_report(loc, paths, root)


# ==========================================================================
# VIOLATING PATH -- work-plane changes in the shared clone
# ==========================================================================


def test_work_paths_in_shared_clone_are_flagged(clone: Path):
    rep = _report(clone, list(WORK_FILES))

    assert rep.examined == len(WORK_FILES), "vacuity guard: expected every path examined"
    assert rep.examined > 0
    assert rep.location.is_shared_clone
    flagged = {f.rel for f in rep.violations}
    assert flagged == set(WORK_FILES), f"expected all work paths flagged, got {flagged}"


def test_staged_work_change_detected_from_git_status(clone: Path):
    """The default collection path (git status), not just argv."""
    _write(clone, "docs/guides/example.md", "edited\n")
    _git(["add", "docs/guides/example.md"], clone)

    rep = _report(clone, None)

    assert rep.examined > 0, "vacuity guard: git status yielded nothing to classify"
    assert "docs/guides/example.md" in {f.rel for f in rep.violations}


def test_strict_exits_nonzero_on_violation(clone: Path, capsys):
    code = guard.main(["--root", str(clone), "--strict", *WORK_FILES])
    capsys.readouterr()
    assert code == guard.EXIT_VIOLATIONS
    assert code != 0


def test_default_mode_is_advisory_and_exits_zero(clone: Path, capsys):
    """Report, do not enforce: violations are printed but the exit stays 0."""
    code = guard.main(["--root", str(clone), *WORK_FILES])
    out = capsys.readouterr().out

    assert code == guard.EXIT_OK, "default mode must not hard-fail"
    assert "WORK-PLANE CHANGES IN THE SHARED CLONE" in out, (
        "advisory mode must still REPORT the violation -- silence would make the "
        "default mode useless rather than merely lenient"
    )


def test_guard_own_source_in_shared_clone_is_flagged(clone: Path):
    """No self-exclusion. Editing the guard in the shared clone is a violation.

    Pinned deliberately: a guard that whitelists its own file is the classic
    'passes by deleting what it inspects' defect. The guard's own source is
    ordinary work-plane code and is treated as such.
    """
    own = "scripts/coordination/check_lane_worktree.py"
    rep = _report(clone, [own])

    assert rep.examined == 1
    assert [f.rel for f in rep.violations] == [own]


# ==========================================================================
# COMPLIANT PATH -- equally important
# ==========================================================================


def test_runtime_paths_in_shared_clone_are_not_flagged(clone: Path):
    """The session bus is SUPPOSED to be written at the canonical clone."""
    rep = _report(clone, list(RUNTIME_FILES))

    assert rep.examined == len(RUNTIME_FILES) > 0, "vacuity guard: nothing examined"
    assert rep.location.is_shared_clone, "must be the shared clone, or this proves nothing"
    assert rep.violations == []
    # WHY they were not flagged: classified runtime, not merely unmatched.
    planes = {f.plane for f in rep.findings}
    assert planes == {guard.RUNTIME}, f"expected all runtime, got {planes}"


def test_runtime_paths_not_flagged_in_strict_mode_either(clone: Path, capsys):
    code = guard.main(["--root", str(clone), "--strict", *RUNTIME_FILES])
    capsys.readouterr()
    assert code == guard.EXIT_OK, "strict mode must still permit bus writes in the clone"


def test_modified_bus_files_from_git_status_are_not_flagged(clone: Path, capsys):
    """Same thing through the default collection path, with real git status."""
    for rel in RUNTIME_FILES:
        _write(clone, rel, "runtime update\n")

    rep = _report(clone, None)
    assert rep.examined > 0, "vacuity guard: git status yielded nothing"
    assert set(RUNTIME_FILES) <= {f.rel for f in rep.findings}, "bus edits must be examined"
    assert rep.violations == []

    code = guard.main(["--root", str(clone), "--strict"])
    capsys.readouterr()
    assert code == guard.EXIT_OK


def test_work_paths_in_lane_worktree_are_not_flagged(lane: Path):
    """Work in a lane worktree is exactly what is supposed to happen."""
    rep = _report(lane, list(WORK_FILES))

    assert rep.examined == len(WORK_FILES) > 0, "vacuity guard: nothing examined"
    assert not rep.location.is_shared_clone
    assert rep.location.kind == guard.LINKED_WORKTREE
    assert rep.location.lane == "mainT"
    assert rep.violations == []
    # WHY: still classified WORK. The exemption comes from the LOCATION, not
    # from quietly reclassifying work as runtime.
    assert {f.plane for f in rep.findings} == {guard.WORK}


def test_work_paths_in_lane_worktree_pass_strict(lane: Path, capsys):
    code = guard.main(["--root", str(lane), "--strict", *WORK_FILES])
    capsys.readouterr()
    assert code == guard.EXIT_OK


def test_modified_work_files_in_lane_worktree_pass_strict(lane: Path, capsys):
    for rel in WORK_FILES:
        _write(lane, rel, "lane edit\n")

    rep = _report(lane, None)
    assert rep.examined > 0, "vacuity guard: git status yielded nothing"
    assert set(WORK_FILES) <= {f.rel for f in rep.findings}

    code = guard.main(["--root", str(lane), "--strict"])
    capsys.readouterr()
    assert code == guard.EXIT_OK


def test_guard_own_source_and_doc_do_not_trip_it_in_a_lane_worktree(lane: Path, capsys):
    """The guard's own source and design note, edited where they belong."""
    own = "scripts/coordination/check_lane_worktree.py"
    doc = "scripts/coordination/WORKTREE_MIGRATION.md"
    _write(lane, own, "# edited guard\n")
    _write(lane, doc, "# edited doc\n")

    rep = _report(lane, [own, doc])
    assert rep.examined == 2
    assert rep.violations == []
    assert {f.plane for f in rep.findings} == {guard.WORK}, (
        "they must still classify as WORK -- unflagged because of location, "
        "never because the guard exempts itself"
    )

    code = guard.main(["--root", str(lane), "--strict"])
    capsys.readouterr()
    assert code == guard.EXIT_OK


def test_clean_tree_exits_zero(clone: Path, capsys):
    """A clean tree is the one legitimate case where examining nothing is correct."""
    rep = _report(clone, None)
    assert rep.examined == 0, f"fixture is not clean: {[f.rel for f in rep.findings]}"
    assert rep.violations == []

    assert guard.main(["--root", str(clone)]) == guard.EXIT_OK
    assert guard.main(["--root", str(clone), "--strict"]) == guard.EXIT_OK
    capsys.readouterr()


# ==========================================================================
# Location detection -- fail closed and loud
# ==========================================================================


def test_detect_location_identifies_shared_clone(clone: Path):
    loc = guard.detect_location(clone)
    assert loc.kind == guard.SHARED_CLONE
    assert loc.is_shared_clone
    assert loc.branch == "main"
    assert loc.lane is None


def test_detect_location_identifies_lane_worktree(lane: Path):
    loc = guard.detect_location(lane)
    assert loc.kind == guard.LINKED_WORKTREE
    assert not loc.is_shared_clone
    assert loc.branch == "lane/mainT"
    assert loc.lane == "mainT"


def test_common_dir_alone_cannot_distinguish_the_planes(clone: Path, lane: Path):
    """Pins the reason detection uses git-dir vs git-common-dir identity.

    Both planes report the SAME common dir, so any implementation keying off
    --git-common-dir would classify a lane worktree as the shared clone.
    """
    a, b = guard.detect_location(clone), guard.detect_location(lane)
    assert guard._same_dir(a.common_dir, b.common_dir), "premise changed"
    assert a.kind != b.kind, "yet the two planes must still be told apart"


def test_non_repo_fails_closed_and_loud(tmp_path: Path, capsys):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()

    with pytest.raises(guard.NotAGitWorkingTree) as exc:
        guard.detect_location(outside)
    assert str(outside) in str(exc.value), "error must name the offending path"

    code = guard.main(["--root", str(outside)])
    err = capsys.readouterr().err
    assert code == guard.EXIT_LOCATION, "must fail closed even in advisory mode"
    assert code != 0
    assert "NotAGitWorkingTree" in err, "error must name the cause, not a generic message"


def test_missing_directory_fails_closed(tmp_path: Path):
    with pytest.raises(guard.NotAGitWorkingTree):
        guard.detect_location(tmp_path / "does-not-exist")


# ==========================================================================
# Path resolution -- symlinks and alternate spellings
# ==========================================================================


def test_symlinked_root_still_resolves(clone: Path, tmp_path: Path):
    """realpath(given) != given: the clone reached through a symlinked path."""
    alias = tmp_path / "alias"
    alias.symlink_to(clone, target_is_directory=True)

    loc = guard.detect_location(alias)
    assert loc.is_shared_clone

    rel = guard.repo_relative(alias / "docs" / "guides" / "example.md", loc.toplevel)
    assert rel == "docs/guides/example.md", "symlinked spelling must map back into the tree"


def test_child_repo_through_symlink_is_out_of_scope(clone: Path, tmp_path: Path):
    """repos/<name> is a symlink to a DIFFERENT repository -- not our jurisdiction.

    Resolving the path first would relocate it outside the clone and lose the
    fact that it belongs to another repo, so the literal spelling is tried first.
    """
    other = tmp_path / "other-repo"
    other.mkdir()
    _git(["init", "-b", "main", "."], other)
    _write(other, "src/kernel.c", "int main(){}\n")

    (clone / "repos").mkdir(exist_ok=True)
    (clone / "repos" / "child").symlink_to(other, target_is_directory=True)

    rep = _report(clone, [str(clone / "repos" / "child" / "src" / "kernel.c")])

    assert rep.examined == 1
    assert rep.findings[0].rel == "repos/child/src/kernel.c", (
        "must keep the in-clone spelling, not the resolved other-repo path"
    )
    assert rep.findings[0].plane == guard.OUT_OF_SCOPE
    assert rep.violations == []


def test_path_outside_the_working_tree_is_reported_not_flagged(clone: Path, tmp_path: Path):
    rep = _report(clone, [str(tmp_path / "elsewhere" / "file.md")])
    assert rep.examined == 1
    assert rep.findings[0].plane == guard.OUT_OF_TREE
    assert rep.violations == []


def test_identity_relative_handles_nonexistent_paths(clone: Path):
    """Deleted files and rename sources cannot be stat-ed; the walk must degrade."""
    ghost = clone / "docs" / "deleted" / "gone.md"
    assert not ghost.exists()
    assert guard._identity_relative(ghost, clone) == "docs/deleted/gone.md"


@pytest.mark.skipif(
    not (Path("/workspace").is_dir() and Path("/mnt/raid0/llm/epyc-root").is_dir()),
    reason="host-specific: both spellings of the shared clone must be present",
)
def test_bind_mounted_alternate_spelling_maps_home():
    """The trap that defeats both prefix-matching AND realpath, on the real host.

    /workspace and /mnt/raid0/llm/epyc-root are the SAME directory (identical
    st_dev/st_ino) but neither is a symlink to the other, so realpath does not
    unify them. Only inode identity does. Read-only: stat, no git, no writes.
    """
    a, b = Path("/workspace"), Path("/mnt/raid0/llm/epyc-root")
    if a.stat().st_ino != b.stat().st_ino or a.stat().st_dev != b.stat().st_dev:
        pytest.skip("host no longer exposes the two spellings as one directory")

    assert a.resolve() != b.resolve(), "premise: realpath does NOT unify them"
    assert guard.repo_relative(b / "scripts" / "x.py", a) == "scripts/x.py"
    assert guard.repo_relative(a / "scripts" / "x.py", b) == "scripts/x.py"


# ==========================================================================
# Classification rules
# ==========================================================================


@pytest.mark.parametrize(
    "rel,expected",
    [
        # Runtime: correct in the shared clone.
        ("coordination/session-bus/queue.jsonl", guard.RUNTIME),
        ("coordination/session-bus/inbox/mainA.jsonl", guard.RUNTIME),
        ("coordination/session-bus/tokens/token-queue.md", guard.RUNTIME),
        ("logs/agent_audit.log", guard.RUNTIME),
        ("tmp/scratch.txt", guard.RUNTIME),
        # Work: belongs in a lane worktree.
        ("scripts/coordination/check_lane_worktree.py", guard.WORK),
        ("scripts/coordination/WORKTREE_MIGRATION.md", guard.WORK),
        ("tests/coordination/test_check_lane_worktree.py", guard.WORK),
        ("docs/guides/x.md", guard.WORK),
        ("handoffs/active/x.md", guard.WORK),
        ("progress/2026-08/2026-08-12-mainA.md", guard.WORK),
        ("agents/coordinator-agent.md", guard.WORK),
        ("wiki/INDEX.md", guard.WORK),
        ("CLAUDE.md", guard.WORK),
        (".gitignore", guard.WORK),
        # Dotfile trees: regression pin for a normalisation bug that stripped
        # the leading dot and demoted these to "unmatched".
        (".claude/settings.json", guard.WORK),
        (".github/workflows/ci.yml", guard.WORK),
        # Out of scope: a different repository.
        ("repos/epyc-llama/ggml/src/ggml.c", guard.OUT_OF_SCOPE),
    ],
)
def test_classification_table(rel: str, expected: str):
    plane, rule = guard.classify(rel)
    assert plane == expected, f"{rel} classified {plane} by rule {rule}"


@pytest.mark.parametrize(
    "rel",
    [
        "handoffs/active/.index-state.json",
        "handoffs/active/.index-graph.json",
        "coordination/BLOCKED_TASKS.md",
        "coordination/inference-batch/ledger.jsonl",
    ],
)
def test_ambiguous_paths_are_unknown_and_never_flagged(rel: str):
    """Ambiguity is surfaced, not guessed.

    A wrong WORK verdict blocks correct work; a wrong RUNTIME verdict hides the
    hazard. UNKNOWN is reported to a human and flagged by neither mode.
    """
    plane, _ = guard.classify(rel)
    assert plane == guard.UNKNOWN
    assert plane not in guard.FLAGGABLE


def test_runtime_rules_are_checked_before_the_ambiguous_coordination_prefix():
    """Rule ORDER is load-bearing, not incidental."""
    assert guard.classify("coordination/session-bus/queue.jsonl")[0] == guard.RUNTIME
    assert guard.classify("coordination/other/thing.md")[0] == guard.UNKNOWN


def test_generated_state_is_checked_before_the_handoffs_work_prefix():
    assert guard.classify("handoffs/active/.index-state.json")[0] == guard.UNKNOWN
    assert guard.classify("handoffs/active/other.md")[0] == guard.WORK


def test_unknown_is_not_flaggable_end_to_end(clone: Path, capsys):
    rel = "handoffs/active/.index-state.json"
    rep = _report(clone, [rel])
    assert rep.examined == 1
    assert rep.findings[0].plane == guard.UNKNOWN
    assert rep.violations == []

    code = guard.main(["--root", str(clone), "--strict", rel])
    capsys.readouterr()
    assert code == guard.EXIT_OK


# ==========================================================================
# CLI surface
# ==========================================================================


def test_stdin_input_is_classified(clone: Path, capsys, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(WORK_FILES) + "\n"))
    code = guard.main(["--root", str(clone), "--stdin", "--strict"])
    capsys.readouterr()
    assert code == guard.EXIT_VIOLATIONS


def test_json_output_exposes_examined_count(clone: Path, capsys):
    import json

    code = guard.main(["--root", str(clone), "--json", *WORK_FILES])
    payload = json.loads(capsys.readouterr().out)

    assert code == guard.EXIT_OK
    assert payload["examined"] == len(WORK_FILES) > 0, (
        "the examined count must be machine-readable so a caller can refuse to "
        "trust an empty run"
    )
    assert len(payload["violations"]) == len(WORK_FILES)
    assert payload["location"]["kind"] == guard.SHARED_CLONE
