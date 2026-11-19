#!/usr/bin/env python3
"""c8-lcattn-gate-r2 2026-11-07: the device-quiet wait fast-paths ONE sample after OUR grant's exit (INVARIANTS 13 is
about unknown processes; a foreign/unknown client keeps two-sample persistence), and IDLE-WHY names the quiet wait."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

DEAD = 2 ** 22 + 12345   # beyond pid_max on this host: never alive


class GpuHeldBack(unittest.TestCase):
    def row(self, rid, rank, bench, gpu=True):
        return {"id": rid, "rank": rank, "bench": bench, "options": [{rf.GPU, "q0"} if gpu else {"q1"}]}

    def test_worse_ranked_shared_row_waits_behind_exclusive(self):
        ex, sh, cpu = self.row("c8", 14, True), self.row("vidya", 24, False), self.row("cpu", 30, False, gpu=False)
        self.assertEqual([c["id"] for c in rf.gpu_held_back([ex, sh, cpu])], ["c8", "vidya"])

    def test_better_ranked_shared_row_still_runs(self):
        ex, sh = self.row("c8", 14, True), self.row("vidya", 5, False)
        self.assertEqual([c["id"] for c in rf.gpu_held_back([ex, sh])], ["c8"])

    def test_no_exclusive_waiting_holds_nothing(self):
        self.assertEqual(rf.gpu_held_back([self.row("vidya", 24, False)]), [])


class QuietOwnExit(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="qoe-")
        self.flags = os.path.join(self.d, "flags")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.kfd = os.path.join(self.d, "kfd")
        os.makedirs(self.kfd)
        self.old = rf.KFD_PROC
        rf.KFD_PROC = self.kfd

    def tearDown(self):
        rf.KFD_PROC = self.old
        shutil.rmtree(self.d, ignore_errors=True)

    def foreign(self, pid=4242, gib=2):
        os.makedirs(os.path.join(self.kfd, str(pid)), exist_ok=True)
        open(os.path.join(self.kfd, str(pid), "vram_0"), "w").write(str(gib << 30))

    def gate(self, grants=()):
        return rf.gpu_quiet_gate(self.flags, list(grants), {}, lambda *_: None, set())

    def own_grant(self, ended=True, pid=DEAD):
        g = {"id": "row-a", "holds": [rf.GPU], "pid": pid, "path": os.path.join(self.flags, "grants", "row-a")}
        self.assertIsNone(self.gate([g]))   # grant open: records the owner
        if ended:
            open(os.path.join(self.flags, "grants", "row-a.ended"), "w").write("rc=0 reason=complete\n")

    def test_own_exit_one_sample(self):
        self.own_grant()
        self.assertIsNone(self.gate())

    def test_no_prior_owner_needs_two(self):
        self.assertIn("1/2", self.gate())
        self.assertIsNone(self.gate())

    def test_not_ended_needs_two(self):
        self.own_grant(ended=False)
        self.assertIn("1/2", self.gate())

    def test_pid_still_alive_needs_two(self):
        self.own_grant(pid=os.getpid())
        self.assertIn("1/2", self.gate())

    def test_foreign_client_resets_to_full_persistence(self):
        self.own_grant()
        self.foreign()
        self.assertIn("not quiet", self.gate())
        os.remove(os.path.join(self.kfd, "4242", "vram_0"))
        os.rmdir(os.path.join(self.kfd, "4242"))
        self.assertIn("1/2", self.gate())      # the foreign sighting dropped the own-exit record
        self.assertIsNone(self.gate())


class QuietSmokeExit(QuietOwnExit):
    """One sample for the row whose own smoke exited and whose tree ps proves dead; anything else keeps two."""
    def setUp(self):
        super().setUp()
        self.record("row-a")

    def record(self, rid, pgid=DEAD, pids=(DEAD,)):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rf.record_smoke_exit(self.flags, rid, pgid, dict.fromkeys(pids, "1"), [])

    def cand(self, rid="row-a", rank=10):
        return {"id": rid, "rank": rank, "bench": True, "options": [{rf.GPU}]}

    def one(self, *cands):
        got = set()
        why = rf.gpu_quiet_gate(self.flags, [], {}, lambda *_: None, set(), cands=list(cands or [self.cand()]), one_sample=got)
        self.assertIn("1/2", why)   # the device-wide verdict never opens early
        return got

    def test_proven_exit_names_only_that_row(self):
        self.assertEqual(self.one(), {"row-a"})

    def test_tree_alive_session_member(self):
        self.record("row-a", pgid=os.getpgid(0))
        self.assertEqual(self.one(), set())

    def test_recycled_pid_is_not_proof(self):
        self.record("row-a", pids=(os.getpid(),))
        self.assertEqual(self.one(), set())

    def test_child_of_recorded_pid_alive(self):
        self.record("row-a", pids=(os.getppid(),))
        self.assertEqual(self.one(), set())

    def test_missing_record(self):
        os.remove(rf.smoke_exited_path(self.flags, "row-a"))
        self.assertEqual(self.one(), set())

    def test_stale_record(self):
        self.assertFalse(rf.smoke_tree_proven_dead(self.flags, "row-a", now=time.time() + rf.SMOKE_EXIT_FRESH_S + 60))

    def test_survivors_write_no_record(self):
        rf.record_smoke_exit(self.flags, "row-a", DEAD, {DEAD: "1"}, [DEAD])
        self.assertFalse(os.path.exists(rf.smoke_exited_path(self.flags, "row-a")))

    def test_running_record_present(self):
        open(rf.running_path(self.flags, "row-a"), "w").write("{}")
        self.assertEqual(self.one(), set())

    def test_ps_failure_is_not_proof(self):
        with mock.patch.object(rf.subprocess, "run", side_effect=OSError("no ps")):
            self.assertEqual(self.one(), set())

    def test_another_rows_process_small_kfd_owner(self):
        self.foreign(gib=0)   # under the VRAM threshold, still an owner
        self.assertEqual(self.one(), set())

    def test_unreadable_kfd_is_not_empty(self):
        shutil.rmtree(self.kfd)
        self.assertEqual(self.one(), set())

    def test_other_rows_record_does_not_help(self):
        self.assertEqual(self.one(self.cand("row-b")), set())

    def test_better_ranked_waiter_keeps_two(self):
        self.assertEqual(self.one(self.cand("row-a", 20), self.cand("row-b", 5)), set())

    def test_foreign_after_exit_then_gone_needs_two(self):
        self.foreign()
        self.assertIn("not quiet", self.gate())
        shutil.rmtree(os.path.join(self.kfd, "4242"))
        self.assertEqual(self.one(), set())

    def test_sighting_before_exit_still_qualifies(self):
        rf.atomic_json(os.path.join(rf.state_dir(self.flags), "gpu_quiet.json"), {"quiet_n": 0, "last_kfd_at": "2026-01-01T00:00:00Z"})
        self.assertEqual(self.one(), {"row-a"})

    def test_second_sample_is_ordinary(self):
        self.one()
        self.assertIsNone(self.gate())


if __name__ == "__main__":
    unittest.main()
