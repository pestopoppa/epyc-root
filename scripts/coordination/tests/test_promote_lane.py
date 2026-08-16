#!/usr/bin/env python3
"""Tests for promote_lane.py — the P2-8 merge cadence.

WHAT THESE PIN, AND WHY.

Promotion is the one place in the pool pipeline where several writers' work
meets one branch, and the repo's failure ledger names three ways that goes
wrong. Each has a test class here, and each test is written so that the WRONG
implementation passes nothing:

  1. SERIALIZATION. `SerializationTests` runs two promotions genuinely
     concurrently (subprocesses, one holding the lock through a `--dwell-s`
     window) and requires the second to be REFUSED naming the holder — not
     queued, not silently skipped. It then asserts exactly ONE commit landed. A
     lock that reported success and protected nothing would fail this.
  2. NO AUTO-RESOLVE. `ConflictTests` sets up a real textual conflict and
     requires refusal with a distinct exit code, the working tree clean, no
     MERGE_HEAD, and no new commit. Auto-resolution would show up as a commit.
  3. NO PATHSPEC-LESS COMMIT. `PathspecTests` leaves another session's
     uncommitted edit in the target tree and proves the promotion commit does not
     contain it — and refuses outright when that edit is in a path the promotion
     itself touches. `SourceDisciplineTests` greps the module for `git add -A`
     and for any `commit` invocation that omits a `--` pathspec.

Every repo here is created fresh in a temp dir. Nothing touches the live tree,
the live bus, or the live push-lock directory: the lock dir is a temp path in
every test.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import promote_lane as pl  # noqa: E402
from scripts.coordination import serialized_push  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "coordination" / "promote_lane.py"


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {repo}: "
                             f"{proc.stderr or proc.stdout}")
    return proc.stdout


class PromoteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="promote-lane-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lock_dir = self.tmp / "locks"
        self.target = self.tmp / "main"
        self.target.mkdir()
        git(self.tmp, "init", "-q", "-b", "main", str(self.target))
        git(self.target, "config", "user.email", "test@example.invalid")
        git(self.target, "config", "user.name", "test")
        (self.target / "src").mkdir()
        (self.target / "src" / "widget.py").write_text("base\n", encoding="utf-8")
        (self.target / "src" / "other.py").write_text("other\n", encoding="utf-8")
        git(self.target, "add", "--", "src/widget.py", "src/other.py")
        git(self.target, "commit", "-q", "-m", "initial")
        self.base = git(self.target, "rev-parse", "HEAD").strip()

    def add_lane(self, name: str) -> Path:
        lane = self.tmp / name
        git(self.target, "worktree", "add", "-q", "-b", name, str(lane))
        git(lane, "config", "user.email", "test@example.invalid")
        git(lane, "config", "user.name", "test")
        return lane

    def lane_commit(self, lane: Path, rel: str, text: str, message: str = "work") -> str:
        path = lane / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        git(lane, "add", "--", rel)
        git(lane, "commit", "-q", "-m", message)
        return git(lane, "rev-parse", "HEAD").strip()

    def target_commit(self, rel: str, text: str, message: str = "target work") -> str:
        (self.target / rel).write_text(text, encoding="utf-8")
        git(self.target, "add", "--", rel)
        git(self.target, "commit", "-q", "-m", message)
        return git(self.target, "rev-parse", "HEAD").strip()

    def run_cli(self, *args: str, agent: str = "inference") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "promote", "--agent", agent,
             "--target", str(self.target), "--lock-dir", str(self.lock_dir), *args],
            capture_output=True, text=True)

    def promote(self, lane: Path, rng: str, *, apply: bool = False,
                agent: str = "inference", operator_ack: str | None = None,
                dwell_s: float = 0.0) -> dict:
        return pl.promote({"task_ids": ["T-1"], "lane_worktree": str(lane),
                           "commit_range": rng},
                          target=self.target, agent=agent, lock_dir=self.lock_dir,
                          apply=apply, operator_ack=operator_ack, dwell_s=dwell_s)

    def commit_count(self) -> int:
        return len(git(self.target, "rev-list", "HEAD").splitlines())


# ------------------------------------------------------------- happy path


class PromotionTests(PromoteTestCase):
    def test_dry_run_is_the_default_and_writes_nothing(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "promoted\n")
        before = self.commit_count()
        receipt = self.promote(lane, f"{self.base}..{head}")
        self.assertFalse(receipt["applied"])
        self.assertTrue(receipt["dry_run"])
        self.assertEqual(receipt["changed_paths"], ["src/widget.py"])
        self.assertIn("would_commit_with", receipt["plan"])
        self.assertEqual(self.commit_count(), before)
        self.assertEqual((self.target / "src" / "widget.py").read_text(), "base\n")

    def test_apply_lands_exactly_one_commit_with_the_lane_content(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "promoted\n")
        before = self.commit_count()
        receipt = self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertTrue(receipt["applied"])
        self.assertEqual(self.commit_count(), before + 1)
        self.assertEqual((self.target / "src" / "widget.py").read_text(), "promoted\n")
        self.assertIn("T-1", git(self.target, "log", "-1", "--format=%s"))
        self.assertEqual(git(self.target, "status", "--porcelain").strip(), "")

    def test_already_promoted_is_a_no_op_not_a_duplicate(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "promoted\n")
        git(self.target, "merge", "--ff-only", "-q", "lane0")
        before = self.commit_count()
        receipt = self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertTrue(receipt["already_promoted"])
        self.assertFalse(receipt["applied"])
        self.assertEqual(self.commit_count(), before)

    def test_lock_is_released_so_a_second_promotion_can_follow(self) -> None:
        lane_a = self.add_lane("lane0")
        head_a = self.lane_commit(lane_a, "src/widget.py", "from-a\n")
        self.promote(lane_a, f"{self.base}..{head_a}", apply=True)
        lane_b = self.add_lane("lane1")
        base_b = git(lane_b, "rev-parse", "HEAD").strip()   # forked from the new tip
        head_b = self.lane_commit(lane_b, "src/other.py", "from-b\n")
        receipt = self.promote(lane_b, f"{base_b}..{head_b}", apply=True)
        self.assertTrue(receipt["applied"])
        self.assertFalse(pl.serialized_push.lock_path(
            self.lock_dir, serialized_push.repo_key(self.target), pl.LOCK_NAME).exists())


# ---------------------------------------------------------- serialization


def _assert_fixture_ids_are_live(*ids: str) -> None:
    """Fail loudly if a fixture identity has since been RETIRED.

    P3-1 tombstoned mainA-D on 2026-08-16 and this file used them as lock
    holders; `serialized_push.acquire` refuses a retired id, so three cases went
    red for a reason that had nothing to do with promotion serialisation. The
    same thing hit test_routing_intent.py the same day. A retirement is a
    perfectly ordinary event — the fixture just has to notice it.
    """
    import re as _re
    cfg = (Path(__file__).resolve().parents[3] / "coordination" / "session-bus" / "config.yaml")
    if not cfg.exists():
        return
    text = cfg.read_text(encoding="utf-8")
    retired = []
    for i in ids:
        m = _re.search(rf"\{{id: {_re.escape(i)},\s*role:\s*(\w+)", text)
        if m and m.group(1) == "retired":
            retired.append(i)
    assert not retired, (
        f"fixture ids {retired} are now role: retired in {cfg}. A retired id is "
        f"REFUSED by serialized_push.acquire and by the routing linter, so every "
        f"case using one fails for an unrelated reason. Repoint them at live rows.")


_assert_fixture_ids_are_live("coordinator-agent", "inference", "workerpool")


class SerializationTests(PromoteTestCase):
    def test_a_held_lock_refuses_the_second_promotion_naming_the_holder(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "promoted\n")
        key = serialized_push.repo_key(self.target)
        serialized_push.acquire(self.lock_dir, key, "coordinator-agent", str(self.target),
                                mode="hold", name=pl.LOCK_NAME,
                                token_file=self.lock_dir / "holder.token")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True, agent="inference")
        self.assertEqual(ctx.exception.condition, "lock-held")
        self.assertEqual(ctx.exception.code, pl.EX_LOCK_HELD)
        self.assertIn("coordinator-agent", str(ctx.exception))
        self.assertEqual((self.target / "src" / "widget.py").read_text(), "base\n")

    def test_two_concurrent_promotions_serialize(self) -> None:
        """Genuinely concurrent, and both would succeed if the lock did nothing.

        The lanes touch DIFFERENT files, so there is no conflict to hide behind:
        if the second promotion were allowed to run it would land cleanly and the
        repo would show two commits. Exactly one must land, and the loser must be
        refused with the lock-held code — a lock that merely delayed the second
        writer would still let both commits appear.
        """
        lane_a = self.add_lane("lane0")
        head_a = self.lane_commit(lane_a, "src/widget.py", "from-a\n")
        lane_b = self.add_lane("lane1")
        head_b = self.lane_commit(lane_b, "src/other.py", "from-b\n")
        before = self.commit_count()

        proc_a = subprocess.Popen(
            [sys.executable, str(SCRIPT), "promote", "--agent", "inference",
             "--target", str(self.target), "--lock-dir", str(self.lock_dir),
             "--task-id", "T-A", "--lane-worktree", str(lane_a),
             "--range", f"{self.base}..{head_a}", "--apply", "--dwell-s", "3"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(1.0)
        proc_b = subprocess.run(
            [sys.executable, str(SCRIPT), "promote", "--agent", "workerpool",
             "--target", str(self.target), "--lock-dir", str(self.lock_dir),
             "--task-id", "T-B", "--lane-worktree", str(lane_b),
             "--range", f"{self.base}..{head_b}", "--apply"],
            capture_output=True, text=True)
        out_a, err_a = proc_a.communicate(timeout=120)

        self.assertEqual(proc_a.returncode, 0, f"first promotion failed: {err_a}")
        self.assertEqual(proc_b.returncode, pl.EX_LOCK_HELD,
                         f"second promotion was not refused: {proc_b.stdout}{proc_b.stderr}")
        self.assertEqual(json.loads(proc_b.stdout)["condition"], "lock-held")
        self.assertIn("inference", proc_b.stdout)
        self.assertEqual(self.commit_count(), before + 1,
                         "exactly one promotion may land while the lock is held")
        self.assertEqual((self.target / "src" / "widget.py").read_text(), "from-a\n")
        self.assertEqual((self.target / "src" / "other.py").read_text(), "other\n")

    def test_the_lock_is_the_shared_primitive_keyed_on_the_common_dir(self) -> None:
        """A lane worktree and the target must contend for ONE lock, not two."""
        lane = self.add_lane("lane0")
        self.assertEqual(serialized_push.repo_key(lane),
                         serialized_push.repo_key(self.target))
        self.assertEqual(pl.LOCK_NAME, "promote")
        serialized_push.validate_lock_name(pl.LOCK_NAME)


# ---------------------------------------------------------------- conflict


class ConflictTests(PromoteTestCase):
    def test_a_conflicting_promotion_is_refused_not_force_merged(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "lane version\n")
        self.target_commit("src/widget.py", "target version\n")
        before = self.commit_count()
        target_head = git(self.target, "rev-parse", "HEAD").strip()

        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertEqual(ctx.exception.condition, "conflict")
        self.assertEqual(ctx.exception.code, pl.EX_CONFLICT)
        self.assertIn("CONFLICT", str(ctx.exception))

        self.assertEqual(self.commit_count(), before, "no commit may be created")
        self.assertEqual(git(self.target, "rev-parse", "HEAD").strip(), target_head)
        self.assertEqual((self.target / "src" / "widget.py").read_text(), "target version\n")
        self.assertEqual(git(self.target, "status", "--porcelain").strip(), "",
                         "a refused promotion must leave the tree exactly as it found it")
        git_dir = Path(git(self.target, "rev-parse", "--path-format=absolute",
                           "--git-dir").strip())
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
            self.assertFalse((git_dir / marker).exists(),
                             f"{marker} exists — a merge was started and left behind")

    def test_a_lane_that_was_never_rebased_is_refused(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "lane version\n")
        # main rewrites the commit the lane forked from: the lane's base is now
        # contained nowhere in main's history — the stale-reconciliation shape.
        git(self.target, "commit", "-q", "--amend", "-m", "initial (rewritten)")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertEqual(ctx.exception.condition, "lane-not-rebased")

    def test_an_empty_range_is_refused_rather_than_reported_as_success(self) -> None:
        """Commits exist and are not contained in main; their NET effect is nothing."""
        lane = self.add_lane("lane0")
        self.lane_commit(lane, "src/widget.py", "changed\n", "change it")
        head = self.lane_commit(lane, "src/widget.py", "base\n", "put it back")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertEqual(ctx.exception.condition, "empty-range")

    def test_an_unresolvable_range_is_refused(self) -> None:
        lane = self.add_lane("lane0")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, "cafebabecafebabecafebabecafebabecafebabe..HEAD")
        self.assertEqual(ctx.exception.condition, "unresolvable-range")

    def test_a_lane_in_a_different_repository_is_refused(self) -> None:
        other = self.tmp / "elsewhere"
        other.mkdir()
        git(self.tmp, "init", "-q", "-b", "main", str(other))
        git(other, "config", "user.email", "t@e.invalid")
        git(other, "config", "user.name", "t")
        (other / "src").mkdir()
        (other / "src" / "widget.py").write_text("x\n", encoding="utf-8")
        git(other, "add", "--", "src/widget.py")
        git(other, "commit", "-q", "-m", "init")
        head = git(other, "rev-parse", "HEAD").strip()
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(other, f"{head}..{head}")
        self.assertEqual(ctx.exception.condition, "cross-repository")


# ---------------------------------------------------------------- pathspec


class PathspecTests(PromoteTestCase):
    def test_another_sessions_uncommitted_work_is_not_swept_into_the_commit(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "promoted\n")
        # Another session is mid-edit in a DIFFERENT file, and has staged it.
        (self.target / "src" / "other.py").write_text("someone else's WIP\n", encoding="utf-8")
        git(self.target, "add", "--", "src/other.py")

        receipt = self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertTrue(receipt["applied"])
        committed = git(self.target, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(committed, ["src/widget.py"],
                         "the promotion commit must contain ONLY its own pathspec")
        self.assertIn("src/other.py", git(self.target, "status", "--porcelain"))
        self.assertEqual((self.target / "src" / "other.py").read_text(),
                         "someone else's WIP\n")

    def test_an_uncommitted_edit_in_a_promoted_path_refuses(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "src/widget.py", "promoted\n")
        (self.target / "src" / "widget.py").write_text("someone else's WIP\n",
                                                       encoding="utf-8")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertEqual(ctx.exception.condition, "dirty-target")
        self.assertEqual((self.target / "src" / "widget.py").read_text(),
                         "someone else's WIP\n")

    def test_a_deletion_is_carried_by_the_pathspec(self) -> None:
        lane = self.add_lane("lane0")
        git(lane, "rm", "-q", "--", "src/other.py")
        git(lane, "commit", "-q", "-m", "drop other")
        head = git(lane, "rev-parse", "HEAD").strip()
        receipt = self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertTrue(receipt["applied"])
        self.assertFalse((self.target / "src" / "other.py").exists())
        self.assertEqual(git(self.target, "status", "--porcelain").strip(), "")


# -------------------------------------------------------------------- gates


class GateTests(PromoteTestCase):
    def test_a_human_only_path_is_refused_with_a_token_block(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "CLAUDE.md", "# rewritten by a robot\n")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertEqual(ctx.exception.condition, "gated")
        self.assertEqual(ctx.exception.code, pl.EX_GATED)
        self.assertIn("token_block", ctx.exception.detail["gate"])
        self.assertIn("CLAUDE.md", ctx.exception.detail["gate"]["token_block"])

    def test_the_d9_loop_plane_needs_an_operator_ack(self) -> None:
        lane = self.add_lane("lane0")
        head = self.lane_commit(lane, "scripts/coordination/new_thing.py", "x = 1\n")
        with self.assertRaises(pl.PromotionRefused) as ctx:
            self.promote(lane, f"{self.base}..{head}", apply=True)
        self.assertEqual(ctx.exception.condition, "gated")
        self.assertTrue(ctx.exception.detail["gate"]["loop_plane_gated"])

        receipt = self.promote(lane, f"{self.base}..{head}", apply=True,
                               operator_ack="OP-ACK-20260816")
        self.assertTrue(receipt["applied"])
        self.assertIn("OP-ACK-20260816", git(self.target, "log", "-1", "--format=%B"))

    def test_the_gate_list_is_the_real_one_and_verifies(self) -> None:
        """If the pinned gate list ever fails to load, every promotion must refuse."""
        gate = pl.merge_gate.load_gate_list()
        self.assertTrue(gate.get("paths"))


# ------------------------------------------------------- source discipline


class SourceDisciplineTests(unittest.TestCase):
    """Grep-level guards. The forbidden idioms are cheap to reintroduce."""

    def setUp(self) -> None:
        self.source = SCRIPT.read_text(encoding="utf-8")
        # The module docstring NAMES the forbidden idioms in order to forbid
        # them, so it must be excluded or the guard fires on its own rationale
        # (a guard that forbids its own idiom is a known defect shape here).
        body = self.source.split('"""', 2)[2]
        self.code = "\n".join(
            ln for ln in body.splitlines() if not ln.strip().startswith("#"))

    def test_no_git_add_dash_A_or_dot(self) -> None:
        for forbidden in ('"add", "-A"', '"add", "."', '"add", "--all"'):
            self.assertNotIn(forbidden, self.code,
                             f"{forbidden} sweeps other sessions' work in a shared tree")

    def test_every_git_add_and_commit_carries_an_explicit_pathspec(self) -> None:
        calls = re.findall(r'_git\((?:[^()]|\([^()]*\))*\)', self.code)
        for call in calls:
            if '"add"' in call or '"commit"' in call:
                self.assertIn('"--"', call,
                              f"pathspec-less git call: {call}")
                self.assertIn("*paths", call,
                              f"git call does not use the explicit path list: {call}")

    def test_the_module_never_resolves_a_conflict(self) -> None:
        for forbidden in ("-X theirs", "-X ours", "--strategy-option",
                          "checkout --theirs", "merge --no-ff", "rerere"):
            self.assertNotIn(forbidden, self.code,
                             f"{forbidden!r} would auto-resolve a conflict nobody reviewed")

    def test_apply_is_checked_before_it_is_run(self) -> None:
        self.assertIn("check_only=True", self.code)
        self.assertLess(self.code.index("check_only=True"),
                        self.code.index("check_only=False"),
                        "the --check must precede the real apply")


if __name__ == "__main__":
    unittest.main(verbosity=2)
