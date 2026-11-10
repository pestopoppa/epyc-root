#!/usr/bin/env python3
"""ws58 2026-11-02: a smoke that completes the whole job files it as done (never a row); estimate_s < 300 is refused;
two rows declaring the same port are never co-scheduled."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402


class TinyRowTests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        self.rid = "tiny1"
        self.res = os.path.join(self.flags, "out", "RESULT.json")
        self.pkt = os.path.join(self.flags, "pkt")
        os.makedirs(self.pkt)
        # live ready manifests always bind the engine by path + sha256 (completed-smoke filing checks it)
        self.engine = os.path.join(self.pkt, "filler_run15.sh")
        with open(self.engine, "w") as f:
            f.write("#!/bin/bash\nexit 0\n")

    def _launcher(self, body="", complete_cmd=None):
        """A row launcher: optional pre-engine body, then the filler_run15.sh engine line (never executed here)."""
        lp = os.path.join(self.pkt, "launcher.sh")
        cc = complete_cmd or f"test -s {self.res}"
        with open(lp, "w") as f:
            f.write("#!/bin/bash\nset -euo pipefail\n" + body +
                    f"exec /bin/bash {self.engine} --id {self.rid} --class cpu --min-window 600 "
                    f"--cmd '/bin/true' --complete-cmd '{cc}' --stop {self.pkt}/STOP --workdir {self.pkt}\n")
        return lp

    def _smoke(self, complete, launcher=None, write_result=True):
        rid, res = self.rid, self.res
        lp = launcher or self._launcher()

        def publish(spec, flags, source=None):
            row = {"schema": rf.SCHEMA, "id": rid, "result_path": res, "scratch_root": os.path.join(self.flags, "out"),
                   "launcher": {"path": lp, "sha256": rf.sha256(lp)},
                   "engine": {"path": self.engine, "sha256": rf.sha256(self.engine)}, "workdir": self.pkt}
            rf.atomic_json(rf.ready_path(flags, rid), row)
            return row

        def dry(flags, rid_, regions, one_quarter=False, smoke_s=None):
            dd = rf.dry_dir(flags, rid_)
            os.makedirs(dd, exist_ok=True)
            if write_result:
                os.makedirs(os.path.dirname(res), exist_ok=True)
                open(res, "w").write("{}")
            open(os.path.join(dd, "ended"), "w").write("rc=0 reason=complete\n")
            rf.atomic_json(rf.pass_path(flags, rid_), {"id": rid_, "result_path": res, "job_complete": complete,
                                                      "launcher_sha256": rf.sha256(lp),
                                                      "engine_sha256": rf.sha256(self.engine)})
            return "PASS", "1 unit(s)"
        with mock.patch.object(pr, "smoke_regions", return_value="0-3"), mock.patch.object(rf, "publish", publish), \
                mock.patch.object(rf, "dryrun_run", dry):
            return pr.publish_smoked({"lane": "cpu"}, self.flags, "t")

    def _assert_not_filed(self, out):
        self.assertIsNotNone(out)
        g = os.path.join(self.flags, "grants")
        self.assertFalse(os.path.exists(os.path.join(g, self.rid + ".complete")))
        self.assertFalse(os.path.exists(os.path.join(g, self.rid + ".ended")))
        self.assertTrue(os.path.exists(rf.ready_path(self.flags, self.rid)))

    def test_complete_in_smoke_is_filed_not_queued(self):
        # a launcher with NO smoke branch whose full-job --complete-cmd holds on the job's own result: the smoke was the job
        self.assertIsNone(self._smoke(True))
        g = os.path.join(self.flags, "grants")
        self.assertTrue(os.path.exists(os.path.join(g, self.rid + ".complete")))
        self.assertTrue(os.path.exists(os.path.join(g, self.rid + ".ended")))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertTrue(os.path.exists(self.res))

    def test_partial_smoke_stays_a_row(self):
        self.assertIsNotNone(self._smoke(False))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "grants", self.rid + ".complete")))

    def test_filler_smoke_branch_in_launcher_never_filed_complete(self):
        # regression (akxall8 v5, 2026-11-02): a 10 s FILLER_SMOKE run was filed as the 4 h job
        lp = self._launcher(body='if [[ ${FILLER_SMOKE:-0} == 1 ]]; then echo smoke; fi\n')
        self._assert_not_filed(self._smoke(True, launcher=lp))

    def test_filler_dryrun_branch_in_complete_cmd_script_never_filed_complete(self):
        cd = os.path.join(self.pkt, "complete_dispatch.sh")
        with open(cd, "w") as f:
            f.write("#!/bin/bash\nif [[ ${FILLER_DRYRUN:-0} == 1 ]]; then exit 0; fi\nexit 1\n")
        lp = self._launcher(complete_cmd=f"/bin/bash {cd}")
        self._assert_not_filed(self._smoke(True, launcher=lp))

    def test_full_job_predicate_unsatisfied_never_filed_complete(self):
        # no smoke branch, but the full-job artifact the --complete-cmd reads is absent. Since the completed-smoke
        # result contract (D9-acked 2026-11-04) a job_complete PASS whose declared result is missing REFUSES and the
        # row is quarantined out of READY (same rule as test_churn_file_result's missing-result case), never filed.
        with self.assertRaises(rf.Refused):
            self._smoke(True, write_result=False)
        g = os.path.join(self.flags, "grants")
        self.assertFalse(os.path.exists(os.path.join(g, self.rid + ".complete")))
        self.assertFalse(os.path.exists(os.path.join(g, self.rid + ".ended")))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)))

    def test_check_scrubs_smoke_env_before_rerunning_predicate(self):
        # the predicate detects the smoke variable without naming it (naming it would itself be a smoke branch)
        lp = self._launcher(complete_cmd='! env | grep -q "^FILLER_[S]MOKE="')
        with mock.patch.dict(os.environ, {"FILLER_SMOKE": "1"}):
            ok, why = rf.smoke_completion_check({"launcher": {"path": lp}})
        self.assertTrue(ok, why)

    @unittest.skipUnless(os.path.isfile("/usr/bin/python3") and os.path.getsize(os.path.realpath("/usr/bin/python3"))
                         > rf.SMOKE_SCAN_MAX_BYTES and rf.smoke_trusted_interpreter("/usr/bin/python3"),
                         "needs a root-owned /usr/bin/python3 larger than the scan cap")
    def test_c6_python_interpreter_launcher_scores_complete(self):
        # regression (c6-native-residency-20261109-r3, c6-26-corpus-repin-20261109-r3): `--cmd "/usr/bin/python3 -B
        # job.py"` read the interpreter as "too large to scan" and scored a finished job incomplete
        ck = os.path.join(self.pkt, "check.py")
        with open(ck, "w") as f:
            f.write("import sys\nsys.exit(0)\n")
        lp = self._launcher(complete_cmd=f"/usr/bin/python3 -I {ck}")
        self.assertEqual(rf.smoke_branch_files({"launcher": {"path": lp}}), [])
        ok, why = rf.smoke_completion_check({"launcher": {"path": lp}})
        self.assertTrue(ok, why)

    def test_python_script_with_smoke_branch_still_incomplete(self):
        ck = os.path.join(self.pkt, "check.py")
        with open(ck, "w") as f:
            f.write("import os, sys\nsys.exit(0 if os.environ.get('FILLER_SMOKE') else 1)\n")
        lp = self._launcher(complete_cmd=f"/usr/bin/python3 -I {ck}")
        ok, why = rf.smoke_completion_check({"launcher": {"path": lp}})
        self.assertFalse(ok)
        self.assertIn("check.py", why)

    def test_unscannable_custom_binary_still_refused(self):
        big = os.path.join(self.pkt, "python3")  # interpreter NAME, but row-owned and outside system bin dirs
        with open(big, "wb") as f:
            f.write(b"\0" * (rf.SMOKE_SCAN_MAX_BYTES + 1))
        os.chmod(big, 0o755)
        self.assertFalse(rf.smoke_trusted_interpreter(big))
        lp = self._launcher(complete_cmd=f"{big} -c true")
        ok, why = rf.smoke_completion_check({"launcher": {"path": lp}})
        self.assertFalse(ok)
        self.assertIn("too large to scan", why)

    def test_dryrun_native_result_never_filed_complete(self):
        ok, why = rf.smoke_completion_check({"launcher": {"path": self._launcher()}, "dryrun_native_result": True})
        self.assertFalse(ok)
        self.assertIn("dryrun_native_result", why)

    def test_short_estimate_refused(self):
        spec = os.path.join(self.flags, "s.json")
        json.dump({"id": "x", "estimate_s": 120}, open(spec, "w"))
        with mock.patch("builtins.print") as p:
            self.assertEqual(pr.main([spec, "--flags", self.flags]), 2)
        self.assertIn("under 5 min: run it in your turn, not as a row", str(p.call_args))


class PortTests(unittest.TestCase):
    def _c(self, rid, region, ports):
        return {"id": rid, "kind": "grant", "lane": "cpu", "rank": 1, "lane_count": 0, "gib": 0, "bench": False,
                "options": [frozenset({region})], "ports": ports}

    def test_same_port_never_co_scheduled(self):
        q = sorted(rf.QUARTERS)
        out, idle, pend = rf.plan(set(q[:2]), [self._c("a", q[0], [8070]), self._c("b", q[1], [8070])], 1000)
        self.assertEqual([c["id"] for c, _ in out], ["a"])
        self.assertEqual([c["id"] for c in pend], ["b"])
        self.assertIn("port 8070", idle[q[1]])

    def test_port_held_by_running_grant_waits(self):
        q = sorted(rf.QUARTERS)
        out, idle, pend = rf.plan({q[0]}, [self._c("a", q[0], [8070])], 1000, held_ports={8070})
        self.assertEqual(out, [])
        self.assertIn("held by a running grant", idle[q[0]])
        out, _, _ = rf.plan({q[0]}, [self._c("a", q[0], [8071])], 1000, held_ports={8070})
        self.assertEqual(len(out), 1)


class DrainBackfillTests(unittest.TestCase):
    """11:28Z: quiet-host akx-auto10 drained to T=11:53; a GPU row ending 11:58 was backfilled and T slid to 12:00."""
    def _c(self, rid, opts, est, shape=None):
        return {"id": rid, "kind": "grant", "lane": "cpu", "rank": 1 if shape else 5, "lane_count": 0, "gib": 0,
                "bench": False, "options": [frozenset(o) for o in opts], "estimate_s": est, "shape": shape}

    def test_no_slide_and_gap_packed(self):
        now = 1000.0
        quiet = self._c("akx", [rf.REGIONS], 3600, "quiet-host")
        gpu_long = self._c("kvu16a", [{rf.GPU}], 2400)       # books 0.75*2400 = 1800 s > T on a region the quiet row needs
        q_short = self._c("short", [{"q1"}], 600)
        q_longer = self._c("longer", [{"q1"}], 1200)
        free = {"q1", "q2", rf.GPU}
        out, _, _ = rf.plan(free, [quiet, gpu_long, q_short, q_longer], 1000, now=now, grant_ends=[now + 1500])
        ids = [c["id"] for c, _ in out]
        self.assertNotIn("kvu16a", ids)
        self.assertIn("longer", ids)          # longest that fits by T first
        self.assertNotIn("short", ids)
        self.assertEqual(rf.plan.last_drain[1], now + 1500)
        # next tick: running grants now end later; persisted T never moves later
        rf.plan(free, [quiet], 1000, now=now + 60, grant_ends=[now + 2400], drain_prev={"akx": now + 1500})
        self.assertEqual(rf.plan.last_drain[1], now + 1500)

    def test_unneeded_region_granted_ignoring_T(self):
        now = 1000.0
        quiet = self._c("akx", [{"q0", "q1"}], 3600, "quiet-host")
        far = self._c("far", [{"q2"}], 99999)
        out, _, _ = rf.plan({"q1", "q2"}, [quiet, far], 1000, now=now, grant_ends=[now + 600])
        self.assertIn("far", [c["id"] for c, _ in out])


if __name__ == "__main__":
    unittest.main()
