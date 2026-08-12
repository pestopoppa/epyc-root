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


@pytest.mark.parametrize("rel_path", UNTRACKED_CLASSES)
def test_runtime_class_is_ignored(rel_path: str) -> None:
    assert _is_ignored(rel_path), f"{rel_path} should be gitignored"


@pytest.mark.parametrize("rel_path", UNTRACKED_CLASSES)
def test_runtime_class_is_not_tracked(rel_path: str) -> None:
    """Guards against the pathspec-commit resurrection hazard the item 2
    commit message documents: gitignored is not the same guarantee as
    actually removed from the index. Only meaningful for paths that exist
    on disk right now (a live bus keeps writing); a path this test cannot
    find is skipped rather than treated as a pass, so the check stays
    honest about what it verified."""
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
