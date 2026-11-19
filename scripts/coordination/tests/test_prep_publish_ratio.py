"""RTG-100 "Sessions over-prepare instead of publishing": the read-only prep/published detector."""
import contextlib
import io
import json
import shutil
from datetime import datetime, timezone
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prep_publish_ratio as ppr  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def touch(p, t, text="x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)
    os.utime(p, (t, t))


class PrepRatioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ppr-")
        self.flags = os.path.join(self.tmp, "compute-flags")
        iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # job A: prepared 10 days ago and published 9 days ago (converted); owner alice
        touch(os.path.join(self.tmp, "jobA", "PREDECLARATION.md"), NOW - 10 * DAY)
        touch(os.path.join(self.flags, "ready", "rowA.json"), NOW - 9 * DAY, json.dumps(
            {"id": "rowA", "owner": "alice", "published_at": iso(NOW - 9 * DAY), "scratch_root": os.path.join(self.tmp, "jobA")}))
        # job B: packet 8 days ago, never published; spec names bob
        touch(os.path.join(self.tmp, "jobB", "packet.md"), NOW - 8 * DAY)
        touch(os.path.join(self.tmp, "jobB", "spec.json"), NOW - 8 * DAY, json.dumps({"owner": "bob"}))
        # bob, last 48 h: 6 prep artifacts, 0 rows
        for i in range(6):
            touch(os.path.join(self.tmp, f"jobC{i}", "PREDECLARATION.md"), NOW - 3600)
            touch(os.path.join(self.tmp, f"jobC{i}", "spec.json"), NOW - 3600, json.dumps({"owner": "bob"}))
        # alice, last 48 h: one row
        touch(os.path.join(self.tmp, "jobD", "spec.json"), NOW - 7200, json.dumps({"owner": "alice"}))
        touch(os.path.join(self.flags, "ready", "rowD.json"), NOW - 3600, json.dumps(
            {"id": "rowD", "owner": "alice", "published_at": iso(NOW - 3600), "launcher": {"path": os.path.join(self.tmp, "jobD", "l.sh")}}))
        for t in (self.tmp,) + tuple(os.path.join(self.tmp, d) for d in os.listdir(self.tmp)):
            os.utime(t, (NOW, NOW))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = ppr.main(["--flags", self.flags, "--tmp", self.tmp, "--now", str(NOW), *extra])
        return rc, json.loads(out.getvalue())

    def test_session_ratio(self):
        rc, rep = self.run_main()
        self.assertEqual(rc, 0)
        self.assertEqual(rep["sessions"]["bob"]["published"], 0)
        self.assertEqual(rep["sessions"]["bob"]["prep"], 12)
        self.assertIsNone(rep["sessions"]["bob"]["prep_per_published"])
        self.assertEqual(rep["sessions"]["alice"]["published"], 1)
        self.assertEqual(rep["sessions"]["alice"]["prep"], 1)

    def test_step_conversion_and_cut_candidate(self):
        _, rep = self.run_main()
        self.assertEqual(rep["steps"]["predeclaration"]["converted"], 1)
        self.assertFalse(rep["steps"]["predeclaration"]["cut_candidate"])
        self.assertTrue(rep["steps"]["packet"]["cut_candidate"])          # aged 8 d, no row
        self.assertEqual(rep["steps"]["packet"]["aged"], 1)

    def test_alert_exit(self):
        rc, rep = self.run_main("--alert-ratio", "3")
        self.assertEqual(rc, 3)
        self.assertEqual(rep["alerts"], ["bob"])


if __name__ == "__main__":
    unittest.main()
