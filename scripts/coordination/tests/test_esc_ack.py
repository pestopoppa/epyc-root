#!/usr/bin/env python3
"""alerts --ack esc-<k> acks the escalation AND its source alert; the source ack alone stops escalation."""
import os, sys, tempfile, unittest, datetime as dt
from unittest import mock

_C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_C, "rowflow"), os.path.join(_C, "churn")]
import notify  # noqa: E402
import rowflow  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self.flags = os.path.join(tempfile.mkdtemp(prefix="escack-"), "flags")
        os.makedirs(os.path.join(self.flags, "filing-done"))
        mock.patch.dict(os.environ, {"ROWFLOW_BUS_ROOT": os.path.join(self.flags, "bus")}).start()
        mock.patch.object(notify, "_bus_send", return_value=True).start()
        mock.patch.object(notify, "_push_safe", return_value="x").start()

    def tearDown(self):
        mock.patch.stopall()

    def alert(self, rid):
        notify.emit(self.flags, "row-ended", rid, "d", f"{rid} ended", "critical", owner="o")
        return notify.event_key("row-ended", rid, "d")

    def escalate(self):
        late = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        return notify.escalate_stale(self.flags, lambda *a: True, now=late, after_s=1, log=lambda m: None)

    def cli(self, key):
        argv = ["alerts", "--ack", key]
        with mock.patch.object(sys, "argv", ["rowflow.py", "--flags", self.flags] + argv):
            try:
                return rowflow.main(["--flags", self.flags] + argv)
            except SystemExit as e:
                return e.code

    def test_ack_esc_acks_both(self):
        k = self.alert("r1"); self.assertEqual(self.escalate(), [k])
        self.assertEqual(self.cli("esc-" + k), 0)
        acks = notify.acked_keys(self.flags)
        self.assertIn(k, acks); self.assertIn("esc-" + k, acks)

    def test_source_ack_stops_escalation(self):
        k = self.alert("r2")
        self.assertEqual(self.cli(k), 0)
        self.assertEqual(self.escalate(), [])

    def test_unknown_refused(self):
        self.alert("r3")
        self.assertEqual(self.cli("esc-deadbeef"), 2)
        self.assertEqual(self.cli("nope"), 2)

    def test_filed_row_refusal_applies_via_esc_key(self):
        k = self.alert("r4")
        for s in (".ended",):
            os.makedirs(os.path.join(self.flags, "grants"), exist_ok=True)
            open(os.path.join(self.flags, "grants", "r4" + s), "w").write("rc=0\n")
        self.assertEqual(self.cli("esc-" + k), 3)
        self.assertNotIn(k, notify.acked_keys(self.flags))

    def test_push_line_keeps_key_when_long(self):
        line = notify.push_line({"kind": "alert-unacked", "row_id": "r", "key": "esc-abc", "detail": {"cause": "x" * 900}})
        self.assertTrue(line.endswith("key=esc-abc") and len(line) <= notify.PUSH_LINE_MAX)


if __name__ == "__main__":
    unittest.main()
