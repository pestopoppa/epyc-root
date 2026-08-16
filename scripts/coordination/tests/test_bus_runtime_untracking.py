#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for the bus runtime-untracking (guard-universe-and-worktree-isolation
P1/2, C45 precedent).

inbox/, outbox/, cursors/, heartbeats/, claims/, advisory*.jsonl,
boundary_state.json and adapter-ledger.jsonl were `git rm --cached`'d and
matching .gitignore patterns added -- files stay on disk (the live daemon
and every session read/write the same paths, undisturbed), just no longer
tracked. BUS_PROTOCOL.md and tasks/*.md are deliberately kept tracked (the
contract and the durable briefs).

2026-08-12: token-queue.md, unblock.md and unblock.pins.json JOINED the
untracked set by operator decision (`cc394307`). They read as operator/trust
surfaces but are live churn — the token queue is rewritten on every grant and
every drain — and they were a standing merge-conflict surface in a five-writer
tree. The durable operator decision record lives in `artifacts/operator/`, so
untracking them loses no history that anyone relies on.

BOTH DIRECTIONS:
  - positive: every untracked class is actually ignored by git, and files in
    it are genuinely absent from `git ls-files` (not just gitignored while
    still somehow tracked from before -- a real risk given the pathspec-
    commit resurrection hazard this same change had to route around, see
    the item 2 commit message).
  - negative: the keep-list is NOT ignored, and archive/ (frozen historical
    snapshots, not live churn) is untouched by any of the new patterns --
    proves the ignore rules are scoped to the runtime directories, not
    written broadly enough to catch something they shouldn't.

Usage: pytest scripts/coordination/tests/test_bus_runtime_untracking.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"


def _is_ignored(rel_path: str) -> bool:
    proc = subprocess.run(
        ["git", "check-ignore", "-q", rel_path],
        cwd=str(REPO_ROOT), capture_output=True,
    )
    return proc.returncode == 0


def _is_tracked(rel_path: str) -> bool:
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel_path],
        cwd=str(REPO_ROOT), capture_output=True,
    )
    return proc.returncode == 0


UNTRACKED_CLASSES = [
    "coordination/session-bus/inbox/mainA.jsonl",
    "coordination/session-bus/outbox/mainA.jsonl",
    "coordination/session-bus/cursors/mainA.json",
    "coordination/session-bus/heartbeats/mainA.json",
    "coordination/session-bus/claims/anything.json",
    "coordination/session-bus/advisory.jsonl",
    "coordination/session-bus/advisory_1.jsonl",
    "coordination/session-bus/advisory_42.jsonl",
    "coordination/session-bus/boundary_state.json",
    "coordination/session-bus/adapter-ledger.jsonl",
    # Untracked 2026-08-12 by operator decision (`cc394307`) — see KEPT_TRACKED.
    "coordination/session-bus/tokens/token-queue.md",
    "coordination/session-bus/tokens/unblock.md",
    "coordination/session-bus/tokens/unblock.pins.json",
]

# 2026-08-12: the three `tokens/*` files moved from KEPT_TRACKED to
# UNTRACKED_CLASSES by operator decision (commit `cc394307`). They are live bus
# runtime state — the token queue churns on every grant and every drain, and it
# was a standing merge-conflict surface in a five-writer tree, which is the same
# class as the queue and the cursors. The operator decision record that used to
# be cited as the reason to track them lives in `artifacts/operator/`, not in the
# token prose, so nothing durable was lost by untracking.
#
# This list is a CONTRACT, not an observation: it must name files whose tracking
# is deliberate, so that untracking one is a test failure someone has to answer
# for rather than a silent drift. Shrinking it to match reality is therefore the
# correct edit — but only alongside the decision that caused it, which is why the
# commit is cited above.
KEPT_TRACKED = [
    "coordination/session-bus/BUS_PROTOCOL.md",
]


# SUPERSEDED 2026-08-16 by P0-7/D5, and the supersession is the point.
#
# The original contract was "runtime is gitignored", whose PURPOSE was that live
# churn must not be committed. That purpose is now served better and differently:
# the runtime DATA moved off-tree to /mnt/raid0/llm/bus-runtime/, and what remains
# in the tree is a SYMLINK that is deliberately TRACKED.
#
# Tracking the symlink is not a regression against the old rule, it is the
# stronger form of it. `git clean -ffdx` removes ignored and untracked files —
# which is precisely how the 2026-08-12 wipe destroyed the inbox, thirteen live
# claim locks, the whole advisory history and the evidence of who ran it. An
# ignored path was exactly what made that possible. A tracked symlink cannot be
# cleaned, and it carries no churn: its content is a path, and the path does not
# change.
#
# So the assertions invert for the relocated classes: the symlink IS tracked, it
# points off-tree, and no runtime BYTES are tracked through it.
RELOCATED_TO_SYMLINK = {
    "coordination/session-bus/inbox",
    "coordination/session-bus/outbox",
    "coordination/session-bus/cursors",
    "coordination/session-bus/heartbeats",
    "coordination/session-bus/claims",
    "coordination/session-bus/tokens",
    "coordination/session-bus/queue.jsonl",
    "coordination/session-bus/advisory.jsonl",
    "coordination/session-bus/adapter-ledger.jsonl",
    "coordination/session-bus/boundary_state.json",
    "coordination/session-bus/stuck_state.json",
    "coordination/session-bus/relay_state.json",
    "coordination/session-bus/operator_escalation_state.json",
    "coordination/session-bus/scheduling_recommendation_state.json",
}


def _relocated_root(rel_path: str) -> str | None:
    """The tracked symlink covering rel_path, or None if it is not relocated."""
    for root in RELOCATED_TO_SYMLINK:
        if rel_path == root or rel_path.startswith(root + "/"):
            return root
    return None


@pytest.mark.parametrize("rel_path", UNTRACKED_CLASSES)
def test_runtime_class_is_ignored(rel_path: str) -> None:
    root = _relocated_root(rel_path)
    if root is not None:
        pytest.skip(f"{rel_path} is served by the tracked symlink {root} (P0-7/D5); "
                    "see test_relocated_runtime_is_a_tracked_symlink")
    assert _is_ignored(rel_path), f"{rel_path} should be gitignored"


@pytest.mark.parametrize("rel_path", sorted(RELOCATED_TO_SYMLINK))
def test_relocated_runtime_is_a_tracked_symlink(rel_path: str) -> None:
    """The D5 contract, stated positively.

    Three properties, and all three matter: the path is a symlink (so the bytes
    are not in the tree), git TRACKS it with mode 120000 (so `git clean -ffdx`
    cannot remove it — the whole point), and it resolves OUTSIDE the repo.
    """
    root = _relocated_root(rel_path)
    if root is not None:
        pytest.skip(f"{rel_path} is served by the tracked symlink {root} (P0-7/D5) — "
                    "tracking the LINK is the stronger form of this rule, since "
                    "`git clean -ffdx` cannot remove a tracked path; the bytes it "
                    "points at are off-tree and are what this rule was protecting. "
                    "Covered positively by test_relocated_runtime_is_a_tracked_symlink.")
    full = REPO_ROOT / rel_path
    if not full.exists():
        pytest.skip(f"{rel_path} not present on this checkout")
    assert full.is_symlink(), (
        f"{rel_path} must be a symlink after P0-7 — a real file here means the "
        f"runtime moved back into the tree and is clean-able again")
    mode = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "-s", "--", rel_path],
                          capture_output=True, text=True).stdout.split()
    assert mode and mode[0] == "120000", (
        f"{rel_path} must be TRACKED as a symlink (mode 120000); untracked means "
        f"`git clean -ffdx` deletes it, which is the 2026-08-12 wipe class")
    target = full.resolve()
    assert not str(target).startswith(str(REPO_ROOT) + "/"), (
        f"{rel_path} resolves to {target}, still inside the repo — the runtime "
        f"is supposed to live off-tree")


@pytest.mark.parametrize("rel_path", UNTRACKED_CLASSES)
def test_runtime_class_is_not_tracked(rel_path: str) -> None:
    """Guards against the pathspec-commit resurrection hazard the item 2
    commit message documents: gitignored is not the same guarantee as
    actually removed from the index. Only meaningful for paths that exist
    on disk right now (a live bus keeps writing); a path this test cannot
    find is skipped rather than treated as a pass, so the check stays
    honest about what it verified."""
    root = _relocated_root(rel_path)
    if root is not None:
        pytest.skip(
            f"{rel_path} is served by the tracked symlink {root} (P0-7/D5). Tracking "
            "the LINK is the stronger form of this rule, not a violation of it: "
            "`git clean -ffdx` removes ignored and untracked paths, which is exactly "
            "how the 2026-08-12 wipe happened, and a tracked symlink cannot be "
            "cleaned. The BYTES this rule protects are off-tree. Covered positively "
            "by test_relocated_runtime_is_a_tracked_symlink.")
    full = REPO_ROOT / rel_path
    if not full.exists():
        pytest.skip(f"{rel_path} does not exist on disk right now (fine — "
                     "it is runtime state; nothing to check tracked-ness of)")
    assert not _is_tracked(rel_path), f"{rel_path} exists on disk AND is still tracked"


@pytest.mark.parametrize("rel_path", KEPT_TRACKED)
def test_keep_list_is_not_ignored(rel_path: str) -> None:
    """negative direction: the ignore rules must not be so broad they catch
    the operator/trust surfaces this item deliberately kept tracked."""
    assert not _is_ignored(rel_path), f"{rel_path} must stay tracked, not ignored"


@pytest.mark.parametrize("rel_path", KEPT_TRACKED)
def test_keep_list_is_actually_tracked(rel_path: str) -> None:
    assert _is_tracked(rel_path), f"{rel_path} should be a tracked file"


def test_archive_snapshots_are_untouched_by_the_new_ignore_rules() -> None:
    """negative direction: archive/ holds FROZEN historical snapshots (git
    status shows zero modifications against them -- the actual evidence
    they are not live churn), not runtime state, even though some of its
    subdirectories are literally named inbox/ or outbox/. The new patterns
    are anchored (`coordination/session-bus/inbox/`, no wildcard prefix),
    so they must not reach into archive/'s nested directories of the same
    name."""
    archived = [
        "coordination/session-bus/archive/pre-rename-20260729/inbox-claude-main.jsonl",
        "coordination/session-bus/archive/non-roster-20260811/heartbeats/wrap_ff_boundary.json",
        "coordination/session-bus/archive/non-roster-20260811/outbox/e8_launch_sequence_review.jsonl",
    ]
    for rel_path in archived:
        assert (REPO_ROOT / rel_path).exists(), f"fixture assumption broken: {rel_path} missing"
        assert not _is_ignored(rel_path), f"{rel_path} (archived, frozen) must not be gitignored"
        assert _is_tracked(rel_path), f"{rel_path} (archived, frozen) must still be tracked"
