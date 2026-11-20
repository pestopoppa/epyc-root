#!/usr/bin/env python3
"""F9 (AK audit B9): publish refuses an owner no alert can reach; QUEUED-aged and UNDERUSED alerts go to the owner;
notify's inference fallback for a legacy non-roster owner logs owner-not-roster once per row."""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_TESTS)
sys.path.insert(0, os.path.join(_COORD, "rowflow"))
sys.path.insert(0, _COORD)
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
import notify  # noqa: E402
import toolroot  # noqa: E402


class Roster(unittest.TestCase):
    def setUp(self):
        self.hub = tempfile.mkdtemp(prefix="hub-")
        self.flags = tempfile.mkdtemp(prefix="own-")
        self.addCleanup(shutil.rmtree, self.hub, True)
        self.addCleanup(shutil.rmtree, self.flags, True)
        os.makedirs(os.path.join(self.hub, "coordination", "session-bus"))
        open(os.path.join(self.hub, "coordination", "session-bus", "config.yaml"), "w").write(
            "roster:\n  - id: autokernel\n    role: worker\n  - id: old-one\n    role: retired\n")
        json.dump({"sessions": {"akagg": {"handoff": "handoffs/active/a.md"}}},
                  open(os.path.join(self.flags, "handoff-sessions.json"), "w"))
        p = mock.patch.object(toolroot, "HUB", self.hub)
        p.start()
        self.addCleanup(p.stop)

    def check(self, owner):
        pr.check_owner_roster({"id": "r1", "owner": owner}, self.flags, enforce=True)

    def test_not_a_roster_id_refused(self):
        with self.assertRaises(rf.Refused) as e:
            self.check("not-a-roster-id")
        self.assertIn("config.yaml", str(e.exception))
        self.assertIn("session_bus.py roster add", str(e.exception))

    def test_roster_and_registered_handoff_owners_admitted(self):
        self.check("autokernel")
        self.check("handoff-akagg")
        self.check("h-akagg")

    def test_retired_and_unregistered_handoff_refused(self):
        for o in ("old-one", "handoff-nobody", "nobody", ""):
            with self.assertRaises(rf.Refused):
                self.check(o)

    def test_main_refuses_before_publish(self):
        spec = os.path.join(self.flags, "s.json")
        json.dump({"id": "r1", "owner": "not-a-roster-id", "handoff_task": "x.md", "estimate_s": 600}, open(spec, "w"))
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"ROWFLOW_ROSTER_CHECK": "1"}), mock.patch("sys.stdout", out), \
                mock.patch.object(pr, "refresh_view") as rv:
            self.assertEqual(pr.main([spec, "--flags", self.flags]), 2)
        rv.assert_not_called()
        self.assertIn("REFUSED: owner 'not-a-roster-id'", out.getvalue())

    def test_review_s1_bare_registered_slug_accepted(self):
        self.check("akagg")   # Codex publishes owner: <slug>

    def test_review_s1_warn_mode_logs_records_never_refuses(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"ROWFLOW_ROSTER_CHECK": "warn"}), redirect_stderr(err):
            pr.check_owner_roster({"id": "r1", "owner": "codex-ifbench"}, self.flags)
            pr.check_owner_roster({"id": "r2", "owner": "codex-ifbench"}, self.flags)
            pr.check_owner_roster({"id": "r3", "owner": "codex3"}, self.flags)
        self.assertIn("WARN owner-not-roster", err.getvalue())
        recs = [json.loads(x) for x in open(os.path.join(self.flags, pr.OWNER_NOT_ROSTER_FILE))]
        self.assertEqual([r["owner"] for r in recs], ["codex-ifbench", "codex3"])

    def test_review_s1_live_default_is_warn(self):
        with mock.patch.object(pr.rf.notify, "is_live", return_value=True), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ROWFLOW_ROSTER_CHECK", None)
            self.assertEqual(pr.owner_check_mode(self.flags), "warn")

    def test_review_s1_empty_owner_always_refused(self):
        for env in ("off", "warn", "refuse"):
            with mock.patch.dict(os.environ, {"ROWFLOW_ROSTER_CHECK": env}), self.assertRaises(rf.Refused):
                pr.check_owner_roster({"id": "r1", "owner": "  "}, self.flags)

    def test_scratch_flags_tree_not_enforced(self):
        pr.check_owner_roster({"id": "r1", "owner": "t"}, self.flags)   # tests / scratch trees never route alerts


class Alerts(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="alr-")
        self.addCleanup(shutil.rmtree, self.flags, True)
        os.makedirs(os.path.join(self.flags, "ready"))
        self.sent = []

    def emit(self, *a, **k):
        self.sent.append(a)
        return {"ok": 1}

    def test_queued_aged_to_owner_once_per_queueing(self):
        rid = "q-aged-20261120"
        rf.atomic_json(rf.smoke_queued_path(self.flags, rid), {"id": rid, "queued_at": "2026-11-20T00:00:00Z",
                                                                "spec": {"owner": "autokernel"}})
        t0 = rf.iso_epoch("2026-11-20T00:00:00Z")
        self.assertEqual(rf.queued_aged_alerts(self.flags, now=t0 + 3600, log=lambda m: None, emit=self.emit), [])
        self.assertEqual(rf.queued_aged_alerts(self.flags, now=t0 + 7300, log=lambda m: None, emit=self.emit), [rid])
        self.assertEqual([(a[1], a[2], a[6]) for a in self.sent], [("queued-aged", rid, "autokernel")])

    def test_queued_aged_real_emit_reaches_owner_inbox_once(self):
        rid = "q-aged2-20261120"
        rf.atomic_json(rf.smoke_queued_path(self.flags, rid), {"id": rid, "queued_at": "2026-11-20T00:00:00Z",
                                                                "spec": {"owner": "autokernel"}})
        t = rf.iso_epoch("2026-11-20T00:00:00Z") + 7300
        with mock.patch.object(notify, "_bus_send", return_value="skipped:test"):
            rf.queued_aged_alerts(self.flags, now=t, log=lambda m: None)
            rf.queued_aged_alerts(self.flags, now=t + 60, log=lambda m: None)
        lines = [json.loads(x) for x in open(os.path.join(self.flags, "rowflow-alerts.jsonl"))]
        self.assertEqual([(x["kind"], x["row_owner"]) for x in lines], [("queued-aged", "autokernel")])

    def test_underused_emits_to_owner(self):
        rid = "uu-20261120"
        json.dump({"id": rid, "owner": "autokernel"}, open(rf.ready_path(self.flags, rid), "w"))
        cpus = list(range(0, 24)) + list(range(96, 120))
        s0 = {c: (0, 0) for c in cpus}
        s1 = {c: (0, 1000) for c in cpus}
        with mock.patch.object(notify, "emit", side_effect=self.emit):
            rf.underused(self.flags, {"q0": rid}, lambda m: None, set(), sample=s0, now=1000.0)
            out = rf.underused(self.flags, {"q0": rid}, lambda m: None, set(), sample=s1, now=1000.0 + rf.UNDERUSED_S + 1)
        self.assertEqual(out[0][1], rid)
        self.assertIn(("underused", rid, "autokernel"), [(a[1], a[2], a[6]) for a in self.sent])

    def test_owner_not_roster_logged_once(self):
        err = io.StringIO()
        with redirect_stderr(err):
            notify._owner_not_roster_once(self.flags, "legacy-row", "codex-zz")
            notify._owner_not_roster_once(self.flags, "legacy-row", "codex-zz")
        self.assertEqual(err.getvalue().count("owner-not-roster legacy-row"), 1)


if __name__ == "__main__":
    unittest.main()
