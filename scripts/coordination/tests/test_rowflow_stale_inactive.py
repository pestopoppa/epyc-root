"""R5 stale smoke alerts follow queue and family park state."""
import json
import os

from test_rowflow_family_strikes import Base, BASE, NOW, STEM
import family_strikes as fs
import notify


class TestStaleInactive(Base):
    def setUp(self):
        super().setUp()
        self.rid = f"{BASE}-r2"
        self.fail(self.rid, NOW)

    def queue(self):
        self.manifest(self.rid)
        os.utime(os.path.join(self.flags, "ready", self.rid + ".json"), (NOW - 60, NOW - 60))

    def alert(self, key, kind="smoke-fail-stale"):
        notify._append_line(notify.inbox_path(self.flags),
                            {"key": key, "row_id": self.rid, "kind": kind})

    def scan(self):
        return fs.stale_fail_escalations(self.flags, log=lambda _: None, emit=self.emit, now=NOW + 9 * 3600)

    def test_absent_resolves_existing_stages_only(self):
        self.alert("first")
        self.alert("second")
        self.alert("other", "smoke-fail")
        self.assertEqual(self.scan(), [])
        self.assertEqual(notify.acked_keys(self.flags), {"first", "second"})
        self.assertEqual(self.scan(), [])
        self.assertEqual(len(notify._read_jsonl(notify.acks_path(self.flags))), 2)

    def test_withdrawn_even_if_ready_exists(self):
        self.queue()
        wd = os.path.join(self.flags, "ready", ".withdrawn")
        os.makedirs(wd)
        with open(os.path.join(wd, self.rid + ".json"), "w") as f:
            json.dump({"id": self.rid}, f)
        self.alert("withdrawn")
        self.assertEqual(self.scan(), [])
        self.assertIn("withdrawn", notify.acked_keys(self.flags))

    def test_parked_family_resolves_alert(self):
        self.queue()
        for i in (1, 2):
            fs.record_strike(self.flags, self.rid, "smoke", "fail", key=str(i), now=NOW)
        self.assertIsNotNone(fs.park_reason(self.flags, STEM))
        self.alert("parked")
        self.assertEqual(self.scan(), [])
        self.assertIn("parked", notify.acked_keys(self.flags))

    def test_queued_stale_failure_still_alerts(self):
        self.queue()
        self.alert("open")
        self.assertEqual(self.scan(), [(self.rid, 2)])
        self.assertEqual(notify.acked_keys(self.flags), set())
        self.assertEqual(self.emitted[0][1], "smoke-fail-stale")
