#!/usr/bin/env python3
"""A FILED row's rowflow alerts are resolved: never escalate, acked at filing, best effort."""
import os, sys, tempfile, unittest, datetime as dt
from unittest import mock

_C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_C, "rowflow"), os.path.join(_C, "churn")]
import notify  # noqa: E402
import file_result  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self.flags = os.path.join(tempfile.mkdtemp(prefix="autoack-"), "flags")
        os.makedirs(os.path.join(self.flags, "filing-done"))
        self.env = mock.patch.dict(os.environ, {"ROWFLOW_BUS_ROOT": os.path.join(self.flags, "bus")})
        self.env.start()
        self.p = mock.patch.object(notify, "_bus_send", return_value=True)
        self.p.start()
        self.p2 = mock.patch.object(notify, "_push_safe", return_value="x")
        self.p2.start()

    def tearDown(self):
        mock.patch.stopall()

    def alert(self, rid):
        r = notify.emit(self.flags, "row-ended", rid, "d", f"{rid} ended", "critical", owner="o")
        return notify.event_key("row-ended", rid, "d")

    def filed(self, rid):
        open(os.path.join(self.flags, "filing-done", rid + ".FILED"), "w").write("FILED\n")

    def esc(self):
        routed = []
        late = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        d = notify.escalate_stale(self.flags, lambda *a: routed.append(a) or True, now=late, after_s=1, log=lambda m: None)
        return d, routed

    def test_filed_never_escalates_and_is_acked(self):
        k = self.alert("rf"); self.filed("rf")
        d, routed = self.esc()
        self.assertEqual((d, routed), ([], []))
        self.assertIn(k, notify.acked_keys(self.flags))

    def test_unfiled_still_escalates(self):
        k = self.alert("ru")
        d, routed = self.esc()
        self.assertEqual(d, [k]); self.assertEqual(len(routed), 1)

    def test_filing_acks_open_alerts(self):
        k1 = self.alert("rg"); k2 = self.alert("other")
        file_result.ack_row_alerts(self.flags, "rg")
        ak = notify.acked_keys(self.flags)
        self.assertIn(k1, ak); self.assertNotIn(k2, ak)

    def test_ack_failure_does_not_break_filing(self):
        with mock.patch.object(notify, "ack_filed", side_effect=RuntimeError("boom")):
            file_result.ack_row_alerts(self.flags, "rg")   # must not raise


if __name__ == "__main__":
    unittest.main()
