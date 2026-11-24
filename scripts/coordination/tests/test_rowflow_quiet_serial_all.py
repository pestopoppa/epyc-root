"""QUIET-SERIAL-ALL + EXCLUSIVE-CPU-HOLD (AK 2026-11-23 23:43Z): c20-fold-cpu-r4 (q0) and ak-cpu-aa-calibration-q-a3b (q2) ran
together because neither MANIFEST carried requires_quiet_host; both ran in-run quiet guards. QUIET-SERIAL now covers every
quiet-sensitive row class (declared, spec-source, job-code derived); exclusive_cpu is an owner opt-in host CPU hold."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

UTIL = {"q0": 2.0, "q1": 3.0, "q2": 1.0, "q3": 4.0}


def cand(rid, opts, rank=20, shape="quarter", est=None):
    c = {"id": rid, "shape": shape, "rank": rank, "kind": "grant", "options": [frozenset(o) for o in opts]}
    if est:
        c["estimate_s"] = est
    return c


def jobdir(td, name, code):
    d = os.path.join(td, name)
    os.makedirs(d)
    with open(os.path.join(d, "launch.sh"), "w") as f:
        f.write("#!/bin/bash\n")
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(code)
    return {"launcher": {"path": os.path.join(d, "launch.sh"), "sha256": name}, "workdir": d}


class Derived(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        rf._QUIET_SCAN.clear()

    def test_classes(self):
        self.assertTrue(rf.quiet_sensitive({"quiet_sensitive": True}))
        self.assertTrue(rf.quiet_sensitive(jobdir(self.td, "a", "g = H.quiet_guard(phys, rb, out)\n")))
        self.assertTrue(rf.quiet_sensitive(jobdir(self.td, "b", "PAIRS, QUIET_BUSY_P95 = 24, 15.0\n")))
        self.assertFalse(rf.quiet_sensitive(jobdir(self.td, "c", "print('loud')\n")))
        # explicit owner opt-out wins over the code scan
        self.assertFalse(rf.quiet_sensitive(dict(jobdir(self.td, "d", "H.run_quiet(m)\n"), requires_quiet_host=False)))
        # the library file alone is not a call site
        d = jobdir(self.td, "e", "x = 1\n")
        with open(os.path.join(d["workdir"], "ak_row_harness.py"), "w") as f:
            f.write("def quiet_guard(c):\n    pass\n")
        self.assertFalse(rf.quiet_sensitive(d))
        # spec source says requires_quiet_host though the manifest lost it (stale-publisher drop, c20-fold-cpu-r4)
        sp = os.path.join(self.td, "spec.json")
        with open(sp, "w") as f:
            json.dump({"requires_quiet_host": True}, f)
        self.assertTrue(rf.quiet_sensitive({"published_from": sp}))
        self.assertFalse(rf.quiet_required({"published_from": sp}))   # the foreign-busy gate is not widened

    def test_incident_cross_quarter_co_grant_refused(self):
        rows = {"c20": jobdir(self.td, "c20", "H.quiet_guard(p, r, o)\n"),
                "cal": jobdir(self.td, "cal", "QUIET_BUSY_P95 = 15.0\n"),
                "spec": dict(jobdir(self.td, "spec", "print(1)\n"), requires_quiet_host=False)}
        grants = [{"id": "spec", "holds": {"q1"}}, {"id": "cal", "holds": {"q2"}}]
        kept, waits, lines = rf.quiet_gate([cand("c20", [{"q0"}], rank=5)], rows, grants, UTIL)
        self.assertEqual(kept, [])
        self.assertEqual(lines["c20"], "QUIET-SERIAL c20 waits for running quiet cal")
        # with only the non-quiet specpit row running, c20 is granted (no foreign-busy gate on a derived row)
        kept, _, _ = rf.quiet_gate([cand("c20", [{"q0"}], rank=5)], rows, grants[:1], {"q0": 40.0})
        self.assertEqual([c["id"] for c in kept], ["c20"])

    def test_shortest_first_across_derived_and_declared(self):
        rows = {"a": {"requires_quiet_host": True}, "b": jobdir(self.td, "b", "H.run_quiet(m)\n"), "n": {}}
        cs = [cand("a", [{"q0"}], est=9000), cand("b", [{"q2"}], est=600, rank=60), cand("n", [{"q1"}])]
        kept, _, lines = rf.quiet_gate(cs, rows, [], UTIL)
        self.assertEqual(sorted(c["id"] for c in kept), ["b", "n"])
        self.assertEqual(lines["a"], "QUIET-SERIAL a waits for running quiet b")

    def test_urgent_rank_beats_shortest(self):
        """2026-11-24 deadlock: a shorter non-urgent row won QUIET-SERIAL while QUIET-RESERVE held it for the urgent one."""
        rows = {"u": {"requires_quiet_host": True}, "s": {"requires_quiet_host": True}}
        cs = [cand("u", [{"q0"}], est=20000, rank=5), cand("s", [{"q1"}], est=600, rank=40)]
        kept, _, lines = rf.quiet_gate(cs, rows, [], UTIL)
        self.assertIn("u", [c["id"] for c in kept])
        self.assertEqual(lines["s"], "QUIET-SERIAL s waits for running quiet u")


class ExclusiveCpu(unittest.TestCase):
    def rows(self, **kw):
        return {"x": dict({"requires_quiet_host": True, "priority_rank": 5, "exclusive_cpu": True}, **kw), "n": {}, "g": {"lane": "gpu"}}

    def test_hold_logs_and_spares_gpu(self):
        cs = [cand("n", [{"q1"}]), dict(cand("g", [{"gpu-quiet", "c88"}]), lane="gpu")]
        kept, waits, lines = rf.quiet_gate(cs, self.rows(), [{"id": "x", "holds": {"q0"}}], UTIL)
        self.assertEqual([c["id"] for c in kept], ["g"])
        self.assertTrue(lines["n"].startswith("EXCLUSIVE-CPU-HOLD x"))

    def test_off_by_default_and_rank_gated(self):
        g = [{"id": "x", "holds": {"q0"}}]
        for rows in (self.rows(exclusive_cpu=None), self.rows(priority_rank=11)):
            kept, _, _ = rf.quiet_gate([cand("n", [{"q1"}])], rows, g, UTIL)
            self.assertEqual([c["id"] for c in kept], ["n"])

    def test_not_running_no_hold(self):
        kept, _, _ = rf.quiet_gate([cand("n", [{"q1"}])], self.rows(), [], UTIL)
        self.assertEqual([c["id"] for c in kept], ["n"])



class QuietUrgentPending(unittest.TestCase):
    """QUIET-URGENT-PENDING (2026-11-24 incident): c21-fold-cpu-20261124-r2 (rank 9) in smoke; q0 freed at 10:03:42Z and
    ak-cpu-gdn-state-fwd-20261123-r2 (rank 100) was granted until 14:55Z."""
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        rf._QUIET_SCAN.clear()

    def urgent(self, rid="c21-fold-cpu-20261124-r2", age=60, smoke_s=None, **extra):
        dd = os.path.join(self.flags, "dryrun", rid)
        os.makedirs(dd, exist_ok=True)
        with open(os.path.join(dd, "unpublished.json"), "w") as f:
            json.dump({"id": rid, "priority_rank": 9, "requires_quiet_host": True, "owner": "autokernel"}, f)
        if smoke_s:
            with open(os.path.join(dd, "SMOKE-QUEUED.json"), "w") as f:
                json.dump({"smoke_s": smoke_s}, f)
        for k, v in extra.items():
            with open(os.path.join(dd, k), "w") as f:
                f.write(v)
        t = __import__("time").time() - age
        for n in os.listdir(dd):
            os.utime(os.path.join(dd, n), (t, t))
        return rid

    ROWS = {"ak-cpu-gdn-state-fwd-20261123-r2": {"quiet_sensitive": True, "priority_rank": 100},
            "plain": {"priority_rank": 100, "requires_quiet_host": False},
            "gpuq": {"lane": "gpu", "shape": "gpu", "quiet_sensitive": True},
            "urg2": {"quiet_sensitive": True, "priority_rank": 5}}

    def cands(self):
        return [cand("ak-cpu-gdn-state-fwd-20261123-r2", [{"q0"}], rank=100), cand("plain", [{"q1"}], rank=100),
                dict(cand("gpuq", [{"q3"}], rank=100, shape="gpu"), lane="gpu"), cand("urg2", [{"q2"}], rank=5)]

    def test_incident_replay(self):
        self.urgent()
        pend = rf.urgent_quiet_pending(self.flags)
        self.assertEqual([p[0] for p in pend], ["c21-fold-cpu-20261124-r2"])
        kept, waits, logs, _ = rf.quiet_urgent_hold(self.cands(), self.ROWS, pend)
        ids = {c["id"] for c in kept}
        self.assertNotIn("ak-cpu-gdn-state-fwd-20261123-r2", ids)
        self.assertTrue({"plain", "urg2"} <= ids)
        self.assertIn("QUIET-URGENT-PENDING c21-fold-cpu-20261124-r2 holds ak-cpu-gdn-state-fwd-20261123-r2", logs)
        self.assertEqual(len(waits), 1)

    def test_pass_releases(self):
        self.urgent(**{"PASS.json": "{\"verdict\": \"PASS\"}"})
        self.assertEqual(rf.urgent_quiet_pending(self.flags), [])

    def test_fail_releases(self):
        self.urgent(**{"FAIL-1.json": "{}"})
        self.assertEqual(rf.urgent_quiet_pending(self.flags), [])

    def test_granted_not_pending(self):
        self.urgent()
        self.assertEqual(rf.urgent_quiet_pending(self.flags, [{"id": "c21-fold-cpu-20261124-r2"}]), [])

    def test_expired_default_and_budget(self):
        self.urgent(age=46 * 60)
        kept, _, logs, exp = rf.quiet_urgent_hold(self.cands(), self.ROWS, rf.urgent_quiet_pending(self.flags))
        self.assertIn("ak-cpu-gdn-state-fwd-20261123-r2", {c["id"] for c in kept})
        self.assertTrue(exp["c21-fold-cpu-20261124-r2"].startswith("QUIET-URGENT-PENDING-EXPIRED"))
        self.urgent(rid="u-b", age=500, smoke_s=200)   # 500 > 2*200
        self.assertTrue(all("holds" not in l for l in
                            rf.quiet_urgent_hold(self.cands(), self.ROWS, rf.urgent_quiet_pending(self.flags))[2]))

    def test_non_urgent_smoke_no_hold(self):
        dd = os.path.join(self.flags, "dryrun", "slow")
        os.makedirs(dd)
        with open(os.path.join(dd, "unpublished.json"), "w") as f:
            json.dump({"priority_rank": 50, "quiet_sensitive": True}, f)
        self.assertEqual(rf.urgent_quiet_pending(self.flags), [])

    def test_stop_held_urgent_holds_and_expires(self):
        sf = os.path.join(self.flags, "c21.STOP")
        open(sf, "w").close()
        with open(os.path.join(self.flags, "ready", "c21-fold-cpu-r2.json"), "w") as f:
            json.dump({"priority_rank": 9, "requires_quiet_host": True, "stop_file": sf}, f)
        rows = dict(self.ROWS, **{"calib-a3b": {"quiet_sensitive": True, "priority_rank": 60}})
        cs = [cand("calib-a3b", [{"q0"}], rank=60)]
        pend = rf.urgent_quiet_pending(self.flags)
        self.assertEqual([p[0] for p in pend], ["c21-fold-cpu-r2"])
        kept, _, logs, _ = rf.quiet_urgent_hold(cs, rows, pend)
        self.assertEqual(kept, [])
        self.assertIn("QUIET-URGENT-PENDING c21-fold-cpu-r2 holds calib-a3b", logs)
        t = __import__("time").time() - 46 * 60
        os.utime(sf, (t, t))
        kept, _, logs, exp = rf.quiet_urgent_hold(cs, rows, rf.urgent_quiet_pending(self.flags))
        self.assertEqual([c["id"] for c in kept], ["calib-a3b"])
        self.assertIn("c21-fold-cpu-r2", exp)
        os.remove(sf)
        self.assertEqual(rf.urgent_quiet_pending(self.flags), [])

    def test_stale_over_one_day_ignored(self):
        self.urgent(rid="ak-q38fn-relianceproof-c10-20261110-r5", age=1100000)
        self.assertEqual(rf.urgent_quiet_pending(self.flags), [])

    def test_waiting_incident_replay(self):
        """11:20Z: c21-r3 (rank 9, quiet-host) GRANTABLE but foreign busy on q0 (rka-r5); specpit-r4 (rank 40) got q0."""
        rows = {"c21-fold-cpu-20261124-r3": {"requires_quiet_host": True, "priority_rank": 9, "shape": "quiet-host"},
                "specpit-r4": {"quiet_sensitive": True, "priority_rank": 40}, "plain": {"requires_quiet_host": False}}
        pre = [cand("c21-fold-cpu-20261124-r3", [{"q0", "q1", "q2"}], rank=9, shape="quiet-host"),
               cand("specpit-r4", [{"q0"}], rank=40), cand("plain", [{"q1"}], rank=100)]
        util = {"q0": 90.0, "q1": 1.0, "q2": 1.0, "q3": 1.0}
        post, _, qlines = rf.quiet_gate(pre, rows, [], util)
        self.assertNotIn("c21-fold-cpu-20261124-r3", {c["id"] for c in post})
        self.assertIn("specpit-r4", {c["id"] for c in post})   # the hole
        pend, st = rf.urgent_quiet_waiting(pre, post, qlines, rows, {}, now=1000.0)
        self.assertEqual([p[0] for p in pend], ["c21-fold-cpu-20261124-r3"])
        kept, _, logs, exp = rf.quiet_urgent_hold(post, rows, pend, now=1000.0)
        self.assertEqual([c["id"] for c in kept], ["plain"])
        self.assertIn("QUIET-URGENT-WAITING c21-fold-cpu-20261124-r3 holds specpit-r4", logs)
        pend, st = rf.urgent_quiet_waiting(pre, post, qlines, rows, st, now=1000.0 + 46 * 60)
        self.assertEqual(st, {"c21-fold-cpu-20261124-r3": 1000.0})
        kept, _, _, exp = rf.quiet_urgent_hold(post, rows, pend, now=1000.0 + 46 * 60)
        self.assertIn("specpit-r4", {c["id"] for c in kept})
        self.assertTrue(exp["c21-fold-cpu-20261124-r3"].startswith("QUIET-URGENT-WAITING-EXPIRED"))
        _, st = rf.urgent_quiet_waiting(pre, pre, {}, rows, st)   # granted / placeable -> state cleared
        self.assertEqual(st, {})

    def test_light_claim_refused_for_urgent_whole_host(self):
        self.assertIsNone(rf.urgent_whole_host_quiet(self.flags, [], {}))
        os.makedirs(rf.state_dir(self.flags), exist_ok=True)
        with open(os.path.join(rf.state_dir(self.flags), rf.QUIET_URGENT_WAITING_STATE), "w") as f:
            json.dump({"c21-fold-cpu-20261124-r3": __import__("time").time() - 60}, f)
        rows = {"c21-fold-cpu-20261124-r3": {"shape": "quiet-host", "priority_rank": 9, "requires_quiet_host": True}}
        self.assertEqual(rf.urgent_whole_host_quiet(self.flags, [], rows), "c21-fold-cpu-20261124-r3")
        with self.assertRaises(rf.Refused) as cm:
            rf._claim_light_locked(self.flags, "pipeline-mgmt", "84-87", 10, grants=[], allrows=rows, free=set())
        self.assertIn("LIGHT-REFUSED urgent-quiet-pending c21-fold-cpu-20261124-r3", str(cm.exception))
        self.assertIsNone(rf.urgent_whole_host_quiet(self.flags, [{"id": "c21-fold-cpu-20261124-r3"}], rows))

if __name__ == "__main__":
    unittest.main()
