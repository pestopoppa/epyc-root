#!/usr/bin/env python3
"""PM-SMOKEFIX 2026-11-22: (1) a running GPU smoke's own process tree is a gpu-quiet OCCUPANT ("held by smoke <id> until T"),
never "foreign KFD pids"; (2) GPU smokes run by priority_rank then FIFO (inline publish, batch re-pick, CPU-queue place order)."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402
import publish_row as pr  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="smf-")
        self.flags = os.path.join(self.d, "flags")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.kfd = os.path.join(self.d, "kfd")
        os.makedirs(self.kfd)
        self.old = rf.KFD_PROC
        rf.KFD_PROC = self.kfd
        self.procs = []

    def tearDown(self):
        rf.KFD_PROC = self.old
        for p in self.procs:
            p.kill()
            p.wait()
        shutil.rmtree(self.d, ignore_errors=True)

    def kfd_client(self, pid, gib):
        os.makedirs(os.path.join(self.kfd, str(pid)), exist_ok=True)
        open(os.path.join(self.kfd, str(pid), "vram_0"), "w").write(str(gib << 30))


class SmokeTreeIsOccupant(Base):
    def spawn_tree(self):
        # sh (RUNNING.json pid) -> sleep child (the "llama-server")
        p = subprocess.Popen(["sh", "-c", "sleep 60 & wait"], start_new_session=True)
        self.procs.append(p)
        kid = None
        for _ in range(50):
            out = subprocess.run(["ps", "-o", "pid=", "--ppid", str(p.pid)], capture_output=True, text=True).stdout.split()
            if out:
                kid = int(out[0])
                break
            time.sleep(0.05)
        self.assertIsNotNone(kid)
        return p.pid, kid

    def write_smoke(self, rid, pid, lock_only=False):
        dd = rf.dry_dir(self.flags, rid)
        os.makedirs(dd, exist_ok=True)
        if lock_only:
            rf.atomic_json(rf.smoke_lock_path(self.flags, rid), {"pid": pid})
        else:
            rf.atomic_json(rf.running_path(self.flags, rid), {"pid": pid, "pgid": pid, "regions": "mi210_0,184-191",
                                                               "deadline": "2026-11-22T09:10:00Z"})

    def gate(self):
        return rf.gpu_quiet_gate(self.flags, [], {}, lambda *_: None, set())

    def test_descendant_of_running_pid_is_not_foreign(self):
        pid, kid = self.spawn_tree()
        self.write_smoke("smk", pid)
        self.kfd_client(kid, 27)
        why = self.gate()
        self.assertIn("held by smoke smk until 2026-11-22T09:10:00Z", why)
        self.assertNotIn("foreign", why)
        self.assertIn("held by smoke smk", self.gate())   # never opens while the smoke holds it, however many samples

    def test_descendant_of_lock_holder_is_not_foreign(self):
        pid, kid = self.spawn_tree()
        self.write_smoke("smk", pid, lock_only=True)
        self.kfd_client(kid, 27)
        self.assertIn("held by smoke smk", self.gate())

    def test_unrelated_pid_stays_foreign(self):
        self.kfd_client(4242, 27)
        self.assertIn("foreign KFD pids 4242", self.gate())

    def test_smoke_plus_foreign_names_both(self):
        pid, kid = self.spawn_tree()
        self.write_smoke("smk", pid)
        self.kfd_client(kid, 27)
        self.kfd_client(4242, 27)
        why = self.gate()
        self.assertIn("held by smoke smk", why)
        self.assertIn("foreign KFD pids 4242", why)

    def test_dead_smoke_is_not_an_occupant(self):
        self.write_smoke("smk", 2 ** 22 + 999)
        self.assertIn("1/2", self.gate())


class SmokeOrder(Base):
    def queue(self, rid, rank, at):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rf.atomic_json(pr.queued_path(self.flags, rid), {"id": rid, "queued_at": at, "spec": {"priority_rank": rank}})

    def test_order_key_rank_then_fifo(self):
        self.queue("late-hi", 20, "2026-11-22T08:50:00Z")
        self.queue("early-lo", 200, "2026-11-22T08:40:00Z")
        self.queue("early-hi", 20, "2026-11-22T08:45:00Z")
        qs = glob_q(self.flags)
        got = [os.path.basename(os.path.dirname(q)) for q in sorted(qs, key=lambda q: pr.queue_order_key(self.flags, q))]
        self.assertEqual(got, ["early-hi", "late-hi", "early-lo"])

    def test_inline_smoke_yields_to_better_or_equal_queued(self):
        self.queue("q25", 25, "2026-11-22T08:40:00Z")
        self.assertTrue(pr.queued_smoke_ahead(self.flags, "r3", {"priority_rank": 200}))
        self.assertTrue(pr.queued_smoke_ahead(self.flags, "r3", {"priority_rank": 25}))
        self.assertFalse(pr.queued_smoke_ahead(self.flags, "r3", {"priority_rank": 10}))
        self.assertFalse(pr.queued_smoke_ahead(self.flags, "q25", {"priority_rank": 200}))   # its own marker never counts

    def test_batch_repicks_rank_each_iteration(self):
        self.queue("r200", 200, "2026-11-22T08:40:00Z")
        ran = []

        def fake(flags, rid, regions, smoke_s, **kw):
            ran.append(rid)
            if rid == "r200" or len(ran) == 1:
                if len(ran) == 1:
                    self.queue("r20", 20, "2026-11-22T08:59:00Z")   # arrives mid-batch, better rank
            return "FAIL", "x"
        old = pr.run_smoke, pr.alert_queued_nonpass
        pr.run_smoke, pr.alert_queued_nonpass = fake, lambda *a, **k: None
        try:
            self.queue("r100", 100, "2026-11-22T08:41:00Z")
            pr.run_gpu_queue(self.flags)
        finally:
            pr.run_smoke, pr.alert_queued_nonpass = old
        self.assertEqual(ran, ["r100", "r20", "r200"])


def glob_q(flags):
    import glob
    return glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json"))


if __name__ == "__main__":
    unittest.main()
