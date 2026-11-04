"""Where the belief-kernel ledger lives (2026-10-21 plumbing fix).

ONE canonical ledger, outside every worktree, shared by all sessions on this host:

    /mnt/raid0/llm/state/vidya/ledger.jsonl        (override the directory: VIDYA_STATE_DIR)

Why there: /mnt/raid0/llm is the shared RAID root every worktree and session already
uses (same filesystem, same uid), it is outside any git tree so no worktree can shadow or
rebuild it, and it survives worktree deletion. The per-worktree `.vidya/ledger.jsonl`
copies (gitignored) were pure intake rebuilds that lacked every measurement frame.

Resolution order for the DEFAULT path (an explicit `--ledger` always wins over all of these):
  1. VIDYA_LEDGER=<path>        explicit override (tests, one-off studies)
  2. VIDYA_SCRATCH=1 / --scratch  worktree-local `<repo>/.vidya/ledger.jsonl` (tests only)
  3. canonical default above

Checkpoints are NOT moved: they stay committed under `<repo>/.vidya/checkpoints/` because git is
the external holder that upgrades the ledger from tamper-evident to tamper-proof (spec §11.0).
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIR = Path("/mnt/raid0/llm/state/vidya")


def state_dir() -> Path:
    return Path(os.environ.get("VIDYA_STATE_DIR") or DEFAULT_STATE_DIR)


def canonical_ledger_path() -> Path:
    return state_dir() / "ledger.jsonl"


def scratch_ledger_path(repo_root: Path = REPO_ROOT) -> Path:
    return Path(repo_root) / ".vidya" / "ledger.jsonl"


def scratch_requested() -> bool:
    return os.environ.get("VIDYA_SCRATCH", "") not in ("", "0")


def default_ledger_path(repo_root: Path = REPO_ROOT) -> Path:
    env = os.environ.get("VIDYA_LEDGER")
    if env:
        return Path(env)
    if scratch_requested():
        return scratch_ledger_path(repo_root)
    return canonical_ledger_path()


def checkpoint_dir_for(ledger: Path, repo_root: Path = REPO_ROOT) -> Path:
    """Committed checkpoints for the canonical/scratch default; beside the ledger otherwise."""
    ledger = Path(ledger)
    if ledger in (canonical_ledger_path(), scratch_ledger_path(repo_root)):
        return Path(repo_root) / ".vidya" / "checkpoints"
    return ledger.parent / "checkpoints"
