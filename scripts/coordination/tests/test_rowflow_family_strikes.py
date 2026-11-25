#!/usr/bin/env python3
"""AK waste audit 2026-11-25 R2/R3/R5/R6/R7 (docs/design/ak-waste-audit-20261125.md §3): family strikes keyed by id_stem."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "akloop"))
import rowflow as rf  # noqa: E402
import family_strikes as fs  # noqa: E402
import publish_row as pr  # noqa: E402

NOW = 1_800_000_000.0   # 2027-01-15T08:00:00Z
BASE = "ak-c22-df2-devhandoff-gate-gpu-20261125"
STEM = rf.id_stem(BASE)   # ak-c22-df2-devhandoff-gate-gpu


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        for sub in ("ready", "grants", "dryrun"):
            os.makedirs(os.path.join(self.flags, sub))
        self.emitted = []

    def tearDown(self):
        self.tmp.cleanup()

    def emit(self, *a, **k):
        self.emitted.append(a)

    def manifest(self, rid, **kw):
        d = {"id": rid, "owner": "autokernel", "priority_rank": 50, "lane": "gpu"}
        d.update(kw)
        with open(rf.ready_path(self.flags, rid), "w") as f:
            json.dump(d, f)
        return d

    def fail(self, rid, t, **kw):
        dd = rf.dry_dir(self.flags, rid)
        os.makedirs(dd, exist_ok=True)
        p = os.path.join(dd, f"FAIL-{len(rf.fail_paths(self.flags, rid)) + 1}.json")
        with open(p, "w") as f:
            json.dump({"id": rid, "at": iso(t), "reason": "MISMATCH identity", **kw}, f)
        os.utime(p, (t, t))
        return p


class R2Park(Base):
    def test_strikes_persist_across_rN_and_job_sha(self):
        self.manifest(f"{BASE}-r2")
        fs.record_strike(self.flags, f"{BASE}-r2", "smoke", "MISMATCH", key="sha-a", now=NOW)
        self.assertIsNone(fs.park_reason(self.flags, STEM))
        self.manifest(f"{BASE}-r3")   # new -rN, new job sha: the family count is untouched by either
        fs.record_strike(self.flags, f"{BASE}-r3", "smoke", "MISMATCH", key="sha-b", now=NOW + 120)
        why = fs.park_reason(self.flags, STEM)
        self.assertIn(f"PARKED {STEM}: 2 failed smokes", why)
        self.assertIn(f"{BASE}-r2,{BASE}-r3", why)
        self.assertIn(f"rowflow.py unpark --family {STEM} --by <owner> --reason R", why)
        ok, msg = fs.republish_allowed(self.flags, {"id": f"{BASE}-r4", "lane": "gpu"}, now=NOW)
        self.assertFalse(ok); self.assertEqual(msg, why)

    def test_idempotent_same_failure(self):
        fs.record_strike(self.flags, f"{BASE}-r2", "smoke", "x", key="k", now=NOW)
        fs.record_strike(self.flags, f"{BASE}-r2", "smoke", "x", key="k", now=NOW)
        self.assertEqual(fs.load(self.flags, STEM)["count"], 1)

    def test_pass_resets(self):
        fs.record_strike(self.flags, f"{BASE}-r2", "smoke", "x", now=NOW)
        fs.record_clear(self.flags, f"{BASE}-r3", "PASS", now=NOW)
        fs.record_strike(self.flags, f"{BASE}-r4", "smoke", "x", now=NOW)
        self.assertIsNone(fs.park_reason(self.flags, STEM))

    def test_unpark_resets_owner_or_operator_only_and_logs(self):
        self.manifest(f"{BASE}-r2")
        for i in (2, 3):
            fs.record_strike(self.flags, f"{BASE}-r{i}", "smoke", "x", now=NOW)
        with self.assertRaises(rf.Refused):
            fs.unpark_family(self.flags, STEM, "someone-else", "reason", log=lambda m: None)
        with self.assertRaises(rf.Refused):
            fs.unpark_family(self.flags, STEM, "autokernel", "", log=lambda m: None)
        lines = []
        fs.unpark_family(self.flags, STEM, "autokernel", "new decide() fixes parse", log=lines.append)
        self.assertIsNone(fs.park_reason(self.flags, STEM))
        self.assertTrue(lines[0].startswith(f"UNPARK {STEM} by=autokernel"))
        with open(os.path.join(fs.family_dir(self.flags), "UNPARK.log")) as f:
            self.assertIn("UNPARK", f.read())
        for i in (4, 5):
            fs.record_strike(self.flags, f"{BASE}-r{i}", "smoke", "x", now=NOW)
        fs.unpark_family(self.flags, STEM, "operator", "operator says go", log=lambda m: None)
        self.assertEqual(fs.load(self.flags, STEM)["count"], 0)

    def test_record_smoke_outcome_feeds_family(self):
        rid = f"{BASE}-r2"
        self.manifest(rid)
        self.fail(rid, NOW)
        pr.record_smoke_outcome(self.flags, rid, "FAIL", "MISMATCH")
        rid3 = f"{BASE}-r3"
        self.manifest(rid3)
        self.fail(rid3, NOW)
        pr.record_smoke_outcome(self.flags, rid3, "FAIL", "MISMATCH")
        self.assertEqual(fs.load(self.flags, STEM)["count"], 2)
        self.assertEqual(len(fs.gpu_smokes_today(self.flags, STEM)), 2)

    def test_fresh_attempt_denied_for_parked_family(self):
        for i in (2, 3):
            fs.record_strike(self.flags, f"{BASE}-r{i}", "smoke", "x", now=NOW)
        self.assertFalse(rf.fresh_attempt(self.flags, f"{BASE}-r4", {}, "launcher-sha-new"))

    def test_cli_unpark_family(self):
        self.manifest(f"{BASE}-r2")
        for i in (2, 3):
            fs.record_strike(self.flags, f"{BASE}-r{i}", "smoke", "x", now=NOW)
        rc = rf.main(["--flags", self.flags, "unpark", "--family", f"{BASE}-r3", "--by", "autokernel", "--reason", "fixed"])
        self.assertEqual(rc, 0)
        self.assertEqual(fs.load(self.flags, STEM)["count"], 0)


class R3Harness(Base):
    def test_harness_failures_do_not_strike_family(self):
        for i in (2, 3):
            rid = f"{BASE}-r{i}"
            self.manifest(rid)
            self.fail(rid, NOW, failclass={"side": "harness"})
            pr.record_smoke_outcome(self.flags, rid, "FAIL", "pipeline fault")
        self.assertEqual(fs.load(self.flags, STEM)["count"], 0)
        self.assertIsNone(fs.park_reason(self.flags, STEM))
        self.assertEqual(len(fs.gpu_smokes_today(self.flags, STEM)), 0)
        self.assertEqual(fs.harness_strike({"native_verdict": "FUTILITY_HARNESS_IDENTITY"}), (False, ""))
        self.assertEqual(fs.harness_strike({"complete": True}, elapsed_s=11), (False, ""))

    def test_candidate_failures_park_and_push_owner_alert(self):
        import notify
        with mock.patch.object(notify, "_bus_send", return_value="skipped: test"), \
                mock.patch.object(notify, "_push_safe") as push:
            for i in (2, 3):
                rid = f"{BASE}-r{i}"
                self.manifest(rid)
                self.fail(rid, NOW, failclass={"side": "candidate"})
                pr.record_smoke_outcome(self.flags, rid, "FAIL", "candidate mismatch")
            self.assertEqual(fs.load(self.flags, STEM)["count"], 2)
            self.assertIsNotNone(fs.park_reason(self.flags, STEM))
            self.assertIn("family-parked", notify.PUSH_KINDS)
            args = push.call_args.args
            self.assertEqual(args[1]["kind"], "family-parked")
            self.assertEqual(args[1]["row_id"], rid)
            self.assertEqual(args[2], "autokernel")
            self.assertIn("unpark --family", args[1]["summary"])


class R5Stale(Base):
    def run_at(self, t):
        self.emitted = []
        return fs.stale_fail_escalations(self.flags, log=lambda m: None, emit=self.emit, now=t)

    def test_normal_2h_8h(self):
        rid = f"{BASE}-r2"
        self.manifest(rid, owner="ak")
        os.utime(rf.ready_path(self.flags, rid), (NOW - 60, NOW - 60))
        self.fail(rid, NOW)
        with open(os.path.join(rf.dry_dir(self.flags, rid), "unpublished.json"), "w") as f:
            json.dump({"id": rid, "owner": "ak", "priority_rank": 50}, f)
        os.utime(os.path.join(rf.dry_dir(self.flags, rid), "unpublished.json"), (NOW - 60, NOW - 60))
        self.assertEqual(self.run_at(NOW + 1.9 * 3600), [])
        self.assertEqual(self.run_at(NOW + 2.1 * 3600), [(rid, 1)])
        self.assertEqual(self.emitted[0][1], "smoke-fail-stale"); self.assertEqual(self.emitted[0][5], "warning")
        self.assertEqual(self.emitted[0][6], "ak")
        self.assertEqual(self.run_at(NOW + 8.1 * 3600), [(rid, 2)])
        self.assertEqual(self.emitted[0][5], "critical")
        nr = fs.needs_republish(self.flags, NOW + 3 * 3600)
        self.assertEqual(nr[0]["id"], rid); self.assertEqual(nr[0]["age_h"], 3.0)

    def test_urgent_rank_and_operator_approved_1h_4h(self):
        for rid, kw in ((f"a-gpu-20261125-r1", {"priority_rank": 5}), (f"b-gpu-20261125-r1", {"operator_approved": True})):
            self.manifest(rid, owner="ak", **kw)
            os.utime(rf.ready_path(self.flags, rid), (NOW - 60, NOW - 60))
            self.fail(rid, NOW)
            p = os.path.join(rf.dry_dir(self.flags, rid), "unpublished.json")
            with open(p, "w") as f:
                json.dump({"id": rid, "owner": "ak", "priority_rank": 50, **kw}, f)
            os.utime(p, (NOW - 60, NOW - 60))
        self.assertEqual(self.run_at(NOW + 0.9 * 3600), [])
        self.assertEqual(sorted(s for _, s in self.run_at(NOW + 1.1 * 3600)), [1, 1])
        self.assertEqual(sorted(s for _, s in self.run_at(NOW + 4.1 * 3600)), [2, 2])

    def test_republish_or_arm_fail_silences(self):
        rid = f"{BASE}-r2"
        self.manifest(rid)
        os.utime(rf.ready_path(self.flags, rid), (NOW - 60, NOW - 60))
        self.fail(rid, NOW)
        p = rf.ready_path(self.flags, f"{BASE}-r3")
        with open(p, "w") as f:
            json.dump({"id": f"{BASE}-r3"}, f)
        os.utime(p, (NOW + 600, NOW + 600))
        self.assertEqual(self.run_at(NOW + 9 * 3600), [])
        self.manifest("other-gpu-20261125")
        self.fail("other-gpu-20261125", NOW, kind="arm")
        self.assertEqual(self.run_at(NOW + 9 * 3600), [])

    def test_push_kind(self):
        import notify
        self.assertIn("smoke-fail-stale", notify.PUSH_KINDS)


class R6Budget(Base):
    def test_harness_failure_does_not_spend_gpu_budget_or_strike(self):
        rid = f"{BASE}-r2"
        self.manifest(rid)
        self.fail(rid, NOW, failclass={"side": "harness"})
        pr.record_family_outcome(self.flags, rid, "FAIL", "FUTILITY_HARNESS_WITNESS")
        self.assertEqual(fs.load(self.flags, STEM)["count"], 0)
        self.assertEqual(fs.gpu_smokes_today(self.flags, STEM), [])
        self.manifest(f"{BASE}-r3")
        pr.record_family_outcome(self.flags, f"{BASE}-r3", "PASS", "ok")
        self.assertEqual(len(fs.gpu_smokes_today(self.flags, STEM)), 1)

    def test_fourth_gpu_smoke_refused_operator_override(self):
        for i in (1, 2, 3):
            fs.record_gpu_smoke(self.flags, f"{BASE}-r{i}", "PASS", now=NOW)
        spec = {"id": f"{BASE}-r4", "lane": "gpu"}
        ok, why = fs.republish_allowed(self.flags, spec, now=NOW)
        self.assertFalse(ok); self.assertIn("SMOKE-BUDGET", why); self.assertIn("--smoke-budget-by operator", why)
        self.assertTrue(fs.republish_allowed(self.flags, {"id": f"{BASE}-r4", "lane": "cpu"}, now=NOW)[0])
        self.assertTrue(fs.republish_allowed(self.flags, spec, now=NOW + 86400)[0])   # next UTC day
        with self.assertRaises(rf.Refused):
            fs.override_budget(self.flags, STEM, "autokernel", "pls", now=NOW, log=lambda m: None)
        lines = []
        fs.override_budget(self.flags, STEM, "operator", "variant sweep", now=NOW, log=lines.append)
        self.assertTrue(lines[0].startswith("SMOKE-BUDGET-OVERRIDE"))
        self.assertTrue(fs.republish_allowed(self.flags, spec, now=NOW)[0])

    def test_main_records_operator_override_before_rehearsal(self):
        # 2026-11-25: the rehearsal runs the SMOKE-BUDGET check, so main() must record the override first.
        import json as _json, os as _os, tempfile as _tf
        for i in (1, 2, 3):
            fs.record_gpu_smoke(self.flags, f"{BASE}-r{i}", "PASS")
        spec = {"id": f"{BASE}-r4", "lane": "gpu"}
        p = _os.path.join(_tf.mkdtemp(), "spec.json")
        _json.dump(spec, open(p, "w"))
        seen = {}

        def fake_rehearse(s, flags, **kw):
            seen["allowed"] = fs.republish_allowed(flags, s)[0]
            return [] if seen["allowed"] else [("family", "SMOKE-BUDGET")]
        with mock.patch.object(pr, "rehearse", fake_rehearse), mock.patch.object(pr, "route_rerank", lambda *a, **k: False), \
                mock.patch.object(pr, "refresh_view", lambda *a, **k: None), \
                mock.patch.object(pr, "publish_smoked", lambda *a, **k: None):
            rc = pr.main([p, "--flags", self.flags, "--smoke-budget-by", "operator", "--reason", "operator: run ASAP"])
        self.assertTrue(seen["allowed"])
        self.assertEqual(rc, 0)

    def test_publish_smoked_refuses(self):
        for i in (1, 2, 3):
            fs.record_gpu_smoke(self.flags, f"{BASE}-r{i}", "FAIL")
        with mock.patch.object(pr, "smoke_in_flight", lambda f, r: None), \
                mock.patch.object(rf, "smoke_lock_holder", lambda f, r: None):
            with self.assertRaises(rf.Refused) as cm:
                pr.publish_smoked({"id": f"{BASE}-r4", "lane": "gpu"}, self.flags, "/x.json")
        self.assertIn("SMOKE-BUDGET", str(cm.exception))


class R7Preempt(Base):
    URG = f"{BASE}-r4"
    RUN = "ak-ub-arrival-sweep-gpu-20261125-r1"

    def setUp(self):
        super().setUp()
        self.sd = os.path.join(self.flags, "state"); os.makedirs(self.sd)
        self.p = [mock.patch.object(rf, "state_dir", lambda f: self.sd),
                  mock.patch.object(rf, "smoke_passed", lambda f, r, d=None: r == self.URG)]
        for p in self.p:
            p.start()
        self.manifest(self.RUN, priority_rank=31, resumable=False)
        self.manifest(self.URG, priority_rank=1)

    def tearDown(self):
        for p in self.p:
            p.stop()
        super().tearDown()

    def grant(self):
        return {"id": self.RUN, "start": iso(NOW - 2700), "end": iso(NOW + 7200), "holds": [rf.GPU]}

    def test_lost_s_line(self):
        out = rf.preempt_propose(self.flags, [self.grant()], {}, lambda m: None, now=NOW, emit=self.emit)
        self.assertEqual(out, [(self.URG, self.RUN)])
        self.assertIn("lost_s=2700", self.emitted[0][4])
        self.assertEqual(self.emitted[0][7]["lost_s"], 2700)

    def test_suppressed_when_family_struck_today(self):
        fs.record_strike(self.flags, f"{BASE}-r3", "smoke", "MISMATCH", now=NOW - 600)
        lines = []
        out = rf.preempt_propose(self.flags, [self.grant()], {}, lines.append, now=NOW, emit=self.emit)
        self.assertEqual(out, []); self.assertEqual(self.emitted, [])
        self.assertTrue(any("PREEMPT-SUPPRESSED" in ln for ln in lines))


if __name__ == "__main__":
    unittest.main()
