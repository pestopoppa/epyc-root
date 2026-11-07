#!/usr/bin/env python3
"""Disk floor = PAUSE WITH HYSTERESIS + HOLD-ADMISSIONS (operator 2026-11-07). Each behaviour has a NEGATIVE CONTROL: the same
scenario with the property switched off (no hysteresis / no gate / legacy kill) must FAIL the assertion."""
import os
import signal
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COORD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(COORD, "rowflow"))
sys.path.insert(0, os.path.join(COORD, "rowflow2"))
import diskpause as dp  # noqa: E402
import rowflow2 as rf2  # noqa: E402

CFG = {"floor": 150.0, "resume": 180.0, "emergency": 50.0, "cover": 0.9, "sample_s": 0.0, "min_s": 0.0, "path": "/"}
MB = 1 << 20


def row(i, size, alive=True):
    return {"id": i, "pgid": "100" + i[-1], "birth": "b", "alive": alive, "size": size, "root": "/x"}


def seeded(rows_prev, t=0):
    st = dp.new_state()
    st["samples"] = {r["id"]: {"t": t, "size": r["size"]} for r in rows_prev}
    return st


class Pure(unittest.TestCase):
    def test_hysteresis_table(self):
        f = dp.next_paused
        self.assertTrue(f(False, 149.9, 150, 180))
        self.assertFalse(f(False, 150, 150, 180))
        self.assertTrue(f(True, 170, 150, 180))      # band: stays paused
        self.assertFalse(f(False, 170, 150, 180))    # band: stays running
        self.assertFalse(f(True, 180, 150, 180))
        for paused in (False, True):                 # rowflow2 mirror agrees everywhere
            for free in (10, 149, 150, 165, 179.9, 180, 400):
                self.assertEqual(f(paused, free, 150, 180), rf2.disk_pause_step(paused, free, 150, 180))

    def test_negative_control_no_hysteresis_flaps(self):
        # without a resume level above the floor (resume == floor) the band resumes at 160: the property must fail
        self.assertTrue(dp.next_paused(True, 160, 150, 180))
        self.assertFalse(dp.next_paused(True, 160, 150, 150), "control: no hysteresis resumes in the band")

    def test_pause_stops_largest_writers_covering_90pct(self):
        prev = [row("r1", 0), row("r2", 0), row("r3", 0), row("r4", 0)]
        now = [row("r1", 1000 * MB), row("r2", 300 * MB), row("r3", 5 * MB), row("r4", 0)]
        st, acts, ev = dp.decide(seeded(prev), 140, now, CFG, 10)
        self.assertTrue(st["paused"])
        self.assertEqual([r["id"] for k, r in acts if k == "stop"], ["r1", "r2"])   # 1000+300 = 99.6% of 1305; r3/r4 untouched
        self.assertEqual(sorted(st["paused_ids"]), ["r1", "r2"])
        self.assertTrue(ev[0].startswith("DISK-PAUSE ") and sum(e.startswith("DISK-PAUSE-STOP") for e in ev) == 2)

    def test_single_dominant_writer_only(self):
        prev = [row("r1", 0), row("r2", 0)]
        now = [row("r1", 1000 * MB), row("r2", 10 * MB)]
        _, acts, _ = dp.decide(seeded(prev), 100, now, CFG, 10)
        self.assertEqual([r["id"] for _, r in acts], ["r1"])

    def test_band_changes_nothing_and_resume_at_180(self):
        prev = [row("r1", 0)]
        now = [row("r1", 1000 * MB)]
        st, _, _ = dp.decide(seeded(prev), 140, now, CFG, 10)
        st2, acts, ev = dp.decide(st, 170, [row("r1", 1000 * MB)], CFG, 20)
        self.assertTrue(st2["paused"]); self.assertEqual((acts, ev), ([], []))       # band: silent, still paused
        st3, acts, ev = dp.decide(st2, 180, [row("r1", 1000 * MB)], CFG, 30)
        self.assertFalse(st3["paused"])
        self.assertEqual([(k, r["id"]) for k, r in acts], [("cont", "r1")])
        self.assertEqual(len(ev), 1); self.assertTrue(ev[0].startswith("DISK-RESUME"))
        self.assertEqual(st3["paused_ids"], {})

    def test_transition_only_logging(self):
        prev = [row("r1", 0)]
        st, _, ev1 = dp.decide(seeded(prev), 140, [row("r1", 1000 * MB)], CFG, 10)
        self.assertTrue(ev1)
        # steady state below the floor, row already stopped and no new writer: zero lines, zero actions, tick after tick
        for t in (20, 30, 40):
            st, acts, ev = dp.decide(st, 140, [row("r1", 1000 * MB)], CFG, t)
            self.assertEqual((acts, ev), ([], []))
        # no attributable writer: logged exactly once
        st = seeded([row("q", 5)])
        st, _, ev = dp.decide(st, 140, [row("q", 5)], CFG, 10)
        self.assertEqual(sum("NO-WRITER" in e for e in ev), 1)
        st, _, ev = dp.decide(st, 140, [row("q", 5)], CFG, 20)
        self.assertEqual(ev, [])

    def test_ended_row_dropped_from_paused_set(self):
        st, _, _ = dp.decide(seeded([row("r1", 0)]), 140, [row("r1", 1000 * MB)], CFG, 10)
        st, acts, _ = dp.decide(st, 140, [row("r1", 1000 * MB, alive=False)], CFG, 20)
        self.assertEqual(st["paused_ids"], {})

    def test_config_env(self):
        c = dp.config({"FILLER_DISK_FLOOR_GIB": "100", "FILLER_DISK_RESUME_GIB": "120", "FILLER_DISK_EMERGENCY_GIB": "30"})
        self.assertEqual((c["floor"], c["resume"], c["emergency"]), (100.0, 120.0, 30.0))
        c = dp.config({"FILLER_DISK_FLOOR_GIB": "20"})   # a smoke: emergency never above the floor
        self.assertEqual((c["floor"], c["emergency"]), (20.0, 20.0))
        d = dp.config({})
        self.assertEqual((d["floor"], d["resume"], d["emergency"]), (150.0, 180.0, 50.0))


class Signals(unittest.TestCase):
    """Real SIGSTOP/SIGCONT on children THIS test spawned (captured pgid + birth); nothing is matched by name."""

    def setUp(self):
        import tempfile
        self.d = tempfile.mkdtemp(prefix="dp-test-")
        self.flags, self.state = os.path.join(self.d, "flags"), os.path.join(self.d, "state")
        os.makedirs(os.path.join(self.flags, "grants")); os.makedirs(os.path.join(self.flags, "ready")); os.makedirs(self.state)
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.wait()
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def spawn(self, rid, birth=None):
        p = subprocess.Popen(["sleep", "300"], start_new_session=True)
        self.procs.append(p)
        open(os.path.join(self.flags, "grants", rid + ".grant"), "w").close()
        open(os.path.join(self.state, rid + ".inner.pgid"), "w").write(f"{p.pid} {birth or dp.proc_birth(p.pid)}\n")
        return p

    def st(self, p):
        return open(f"/proc/{p.pid}/stat").read().rsplit(") ", 1)[1].split()[0]

    def tick(self, free, sizes, t):
        fn = lambda rows: [r.__setitem__("size", sizes.get(r["id"])) for r in rows]  # noqa: E731
        return dp.tick(self.flags, log=lambda *_: None, state_dir=self.state, free_gib=free, cfg=dict(CFG, path="/"), now=t,
                       sleep=lambda s: None, measure_fn=fn)

    def test_stop_then_resume_real_processes(self):
        a, b = self.spawn("ra"), self.spawn("rb")
        self.tick(140, {"ra": 0, "rb": 0}, 1000.0)          # no history -> baseline (sample_s=0)
        ev = self.tick(140, {"ra": 900 * MB, "rb": 1 * MB}, 1020.0)
        time.sleep(0.2)
        self.assertEqual(self.st(a), "T"); self.assertEqual(self.st(b), "S")      # only the big writer stopped
        self.assertTrue(dp.is_paused(self.flags))
        self.assertEqual(os.path.exists(os.path.join(self.flags, "grants", "ra.ended")), False)   # id stays non-terminal
        self.assertEqual(self.tick(170, {"ra": 900 * MB}, 1040.0), [])                # band: nothing
        self.assertEqual(self.st(a), "T")
        ev = self.tick(185, {"ra": 900 * MB}, 1060.0)
        time.sleep(0.2)
        self.assertEqual(self.st(a), "S"); self.assertFalse(dp.is_paused(self.flags))
        self.assertTrue(any(e.startswith("DISK-RESUME") for e in ev))

    def test_reused_pid_never_signalled(self):
        a = self.spawn("ra", birth="999999999")              # captured birth does not match the live process
        self.tick(140, {"ra": 0}, 1000.0)
        ev = self.tick(140, {"ra": 900 * MB}, 1020.0)
        time.sleep(0.2)
        self.assertEqual(self.st(a), "S")

    def test_negative_control_gate_off_signals_nothing(self):
        a = self.spawn("ra")
        self.tick(160, {"ra": 0}, 1000.0)                    # above the floor: nothing happens, no PAUSED marker
        self.tick(160, {"ra": 900 * MB}, 1020.0)
        time.sleep(0.1)
        self.assertEqual(self.st(a), "S"); self.assertFalse(dp.is_paused(self.flags))

    def test_hold_admissions_gate(self):
        self.assertIsNone(dp.admission_gate(self.flags, persist=False))
        open(os.path.join(self.flags, "HOLD-ADMISSIONS"), "w").write("owner=op\nreason=deploy drain\n")
        why = dp.admission_gate(self.flags, persist=False)
        self.assertIn("owner=op", why); self.assertIn("deploy drain", why)
        os.remove(os.path.join(self.flags, "HOLD-ADMISSIONS"))
        self.assertIsNone(dp.admission_gate(self.flags, persist=False))      # control: no file, no gate


class Mirror(unittest.TestCase):
    def test_rowflow2_admission_hold_reasons_and_once_logging(self):
        import tempfile
        d = tempfile.mkdtemp()
        lines = []
        why, paused = rf2.admission_hold(d, False, 140.0, lines.append, None)
        self.assertTrue(paused and "DISK-PAUSE" in why and len(lines) == 1)
        why2, paused = rf2.admission_hold(d, paused, 170.0, lines.append, why)   # band: still paused, no new log
        self.assertTrue(paused and len(lines) == 1)
        why3, paused = rf2.admission_hold(d, paused, 185.0, lines.append, why2)
        self.assertFalse(paused); self.assertIsNone(why3); self.assertEqual(len(lines), 2)


class Launcher(unittest.TestCase):
    def test_filler_run15_static_contract(self):
        s = open(os.path.join(COORD, "rowflow", "filler_run15.sh")).read()
        self.assertIn("DISK-EMERGENCY", s)
        self.assertIn("FILLER_DISK_EMERGENCY_GIB:-50", s)
        self.assertIn("kill -CONT $pids", s)                                  # a stopped group must be CONTed before TERM
        self.assertNotIn('-lt "${FILLER_DISK_FLOOR_GIB:-150}" ] 2>/dev/null; then\n      reason=disk-floor', s)   # legacy single-threshold kill gone
        self.assertIn("diskpause.py", s)


if __name__ == "__main__":
    unittest.main()
