"""2026-11-03 session review item 2: every status surface carries MEASURED utilisation (per-quarter CPU%, GPU%/VRAM);
a grant that is > IDLE_HELD_AFTER_S old on a region measuring < IDLE_PCT busy is IDLE-HELD; UNDERUSED alerts and
never blocks; the IDLE-VIOLATION alert carries the measurement and is routed to the operator alarm channel; `status`
prints a fixed short form with a deterministic `next` action."""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import hostutil  # noqa: E402
import rowflow as rf  # noqa: E402
from test_rowflow_arming_park import QUIET_OPT, Fixture  # noqa: E402

BUSY = {"q0": 97.0, "q1": 3.0, "q2": 0.0, "q3": 0.0, "gpu": {"busy": 100, "vram_pct": 74.5, "vram_gib": 47.6, "card": "card2"}}


class HostUtil(unittest.TestCase):
    def test_from_samples_is_pure_and_per_quarter(self):
        s0 = {c: (0, 0) for c in range(192)}
        s1 = {c: ((100 if c in hostutil.quarter_cpus("q0") else 0), 100) for c in range(192)}
        u = hostutil.from_samples(s0, s1, {"claim": [0, 1]}, gpu={"busy": 42, "vram_pct": 10.0, "vram_gib": 6.4, "card": "x"})
        self.assertEqual((u["q0"], u["q1"], u["q2"], u["q3"], u["claim"]), (100.0, 0.0, 0.0, 0.0, 100.0))
        self.assertEqual(hostutil.line(u), "util q0=100% q1=0% q2=0% q3=0% claim=100% gpu=42% vram=10%")

    def test_empty_window_reads_unknown_not_busy(self):
        u = hostutil.from_samples({}, {}, gpu=None)
        self.assertIsNone(u["q0"])
        self.assertEqual(hostutil.line(u), "util q0=? q1=? q2=? q3=? gpu=? vram=?")
        self.assertEqual(hostutil.idle_regions(u, ["q0", "gpu-quiet"]), [])   # unknown never counts as idle

    def test_regions_pct_and_idle_regions(self):
        self.assertEqual(hostutil.regions_pct(BUSY, ["q0", "q1", "gpu-quiet"]), {"q0": 97.0, "q1": 3.0, "gpu-quiet": 100})
        self.assertEqual(hostutil.idle_regions(BUSY, ["q0", "q1", "q2", "gpu-quiet"]), ["q1", "q2"])

    def test_parse_cpus(self):
        self.assertEqual(hostutil.parse_cpus("0-2,96, 98-99"), [0, 1, 2, 96, 98, 99])

    def test_measure_is_one_sample_window(self):
        calls = []
        u = hostutil.measure(0.0, sleep=calls.append)
        self.assertEqual(calls, [0.0])
        self.assertEqual(set(u), {"q0", "q1", "q2", "q3", "gpu"})


class StatusSurfaces(Fixture):
    def grant(self, rid, holds="q0,q1", age_s=0):
        p = os.path.join(self.flags, "grants", rid + ".grant")
        with open(p, "w") as f:
            f.write(f"regions=0-47 start=2026-11-03T18:00Z end=2026-11-03T20:00Z holds={holds}\n")
        os.utime(p, (time.time() - age_s, time.time() - age_s))
        return p

    def test_status_carries_next_logs_and_measured_util(self):
        rid = "row-run"
        self.row(rid, 10, QUIET_OPT, "quiet-host")
        self.grant(rid, age_s=120)
        st = rf.status(self.flags, rid, util=BUSY)
        self.assertEqual(st["state"], "running")
        self.assertEqual(st["held"], ["q0", "q1"])
        self.assertEqual(st["util"], {"q0": 97.0, "q1": 3.0})
        self.assertIn("IDLE-HELD q1", st["blocker"])
        self.assertEqual(st["next"], "-")
        self.assertEqual(st["logs"], rf.dry_dir(self.flags, rid))
        txt = rf.status_text(st)
        self.assertLessEqual(len(txt.splitlines()), 8)
        self.assertIn("util:    q0=97% q1=3%", txt)
        self.assertIn("blocker: IDLE-HELD q1", txt)

    def test_fresh_grant_is_not_idle_held_yet(self):
        rid = "row-fresh"
        self.row(rid, 10, QUIET_OPT, "quiet-host")
        self.grant(rid, age_s=5)
        st = rf.status(self.flags, rid, util=BUSY)
        self.assertNotIn("blocker", st)

    def test_next_action_is_deterministic_per_state(self):
        rid = "row-g"
        self.row(rid, 10, QUIET_OPT, "quiet-host")
        st = rf.status(self.flags, rid)
        self.assertEqual(st["state"], "grantable")
        self.assertIn("run_direct.sh " + rf.ready_path(self.flags, rid), st["next"])
        self.assertEqual(rf.next_action({"state": "done"}, self.flags, rid), "-")
        self.assertIn("publish_row.py", rf.next_action({"state": "failed", "fix_task": "fix X"}, self.flags, rid))
        self.assertEqual(rf.next_action({"state": "held", "fix": "rm /x/STOP"}, self.flags, rid), "rm /x/STOP")

    def test_guard_stopped_row_is_disk_paused_self_not_idle_held(self):
        import diskpause
        rid = "row-sp"
        self.row(rid, 10, QUIET_OPT, "quiet-host"); self.grant(rid, holds="q1", age_s=600)
        holders = {"q1": rid}
        out = rf.idle_held(self.flags, rf.open_grants(self.flags), holders, BUSY, self.lines.append, set())
        self.assertEqual(out, [("q1", rid, 3.0)])      # control: not guard-stopped -> IDLE-HELD
        os.makedirs(diskpause.dp_dir(self.flags), exist_ok=True)
        json.dump({rid: {}}, open(os.path.join(diskpause.dp_dir(self.flags), "stopped.json"), "w"))
        self.lines.clear()
        try:
            os.remove(os.path.join(rf.state_dir(self.flags), "logstate.json"))   # transition-only logging: reset the dedup memory
        except OSError:
            pass
        out = rf.idle_held(self.flags, rf.open_grants(self.flags), holders, BUSY, self.lines.append, set())
        self.assertEqual(out, [])
        self.assertTrue(any(l.startswith(f"DISK-PAUSED (self) q1 {rid}") for l in self.lines))
        self.assertFalse(any(l.startswith("IDLE-HELD") for l in self.lines))

    def test_idle_held_logs_measured_idle_grants_only(self):
        rid, fresh = "row-old", "row-new"
        self.row(rid, 10, QUIET_OPT, "quiet-host"); self.row(fresh, 11, QUIET_OPT, "quiet-host")
        self.grant(rid, holds="q1", age_s=600); self.grant(fresh, holds="q2", age_s=5)
        seen = set()
        out = rf.idle_held(self.flags, rf.open_grants(self.flags), {"q1": rid, "q2": fresh, "q0": "someone-else"}, BUSY, self.lines.append, seen)
        self.assertEqual(out, [("q1", rid, 3.0)])
        self.assertEqual(seen, {f"idle-held:q1:{rid}"})
        self.assertTrue([l for l in self.lines if l.startswith(f"IDLE-HELD q1 {rid}: measured 3% busy, grant")])

    def test_snapshot_line_carries_the_measurement_and_underused_never_blocks(self):
        rid = "quiet"
        self.row(rid, 30, QUIET_OPT, "quiet-host")
        rf.measure_util = lambda *a, **k: BUSY
        uu = os.path.join(rf.dry_dir(self.flags, rid), "UNDERUSED.json")
        os.makedirs(os.path.dirname(uu), exist_ok=True)
        rf.atomic_json(uu, {"id": rid, "busy_pct": 1.0})
        os.utime(uu, (time.time() + 5, time.time() + 5))   # newer than the ready file: used to bar the row
        out = self.tick()
        self.assertEqual([r for _, r, _ in out], [rid])
        snap = [l for l in self.lines if l.startswith("SNAPSHOT")][0]
        self.assertTrue(snap.endswith(hostutil.line(BUSY)), snap)

    def test_idle_violation_alert_carries_util_and_is_routed(self):
        routed = []
        rf.route_alert = lambda kind, msg, ev, log=print: routed.append((kind, msg, ev)) or True
        c = {"id": "quiet", "options": QUIET_OPT, "gib": 0, "ports": []}
        for _ in range(2):
            rf.idle_violation(self.flags, set(rf.REGIONS), [c], [], 1000.0, log=self.lines.append, util=BUSY)
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0][0], "idle-violation")
        self.assertIn(hostutil.line(BUSY), routed[0][1])
        self.assertEqual(routed[0][2]["util"], BUSY)
        rec = json.loads(open(os.path.join(self.flags, "ws58-keeper-alerts.jsonl")).readline())
        self.assertEqual(rec["util"], BUSY)

    def test_cli_status_and_list_print_the_fixed_form(self):
        rid = "row-cli"
        self.row(rid, 10, QUIET_OPT, "quiet-host")
        self.grant(rid, holds="q0", age_s=300)
        rf.measure_util = lambda *a, **k: BUSY
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(rf.main(["--flags", self.flags, "status", rid]), 0)
        self.assertEqual(buf.getvalue().splitlines()[0], f"id:      {rid}")
        self.assertIn("util:    q0=97%", buf.getvalue())
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(rf.main(["--flags", self.flags, "list"]), 0)
        lines = buf.getvalue().splitlines()
        self.assertEqual(lines[0], hostutil.line(BUSY))
        self.assertIn("q0=97%", lines[1])


class QueueStatusUtil(unittest.TestCase):
    def test_grant_covers_quarter(self):
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(here, "..", "..", "..", ".claude", "skills", "inference-backlog-scheduling", "scripts"))
        import queue_status as qs
        self.assertTrue(qs._grant_covers("0-95", "q2"))
        self.assertTrue(qs._grant_covers("mi210_0,24-47", "q1"))
        self.assertFalse(qs._grant_covers("24-40", "q1"))
        self.assertIs(qs._hostutil(), hostutil)


if __name__ == "__main__":
    unittest.main()
