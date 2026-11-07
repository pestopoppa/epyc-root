"""queue_status.py reads live rowflow state (ready/grants/dryrun/filing-done/keeper log), never FILLERS.md."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", ".claude", "skills", "inference-backlog-scheduling", "scripts"))
import queue_status as qs  # noqa: E402


def w(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text if isinstance(text, str) else json.dumps(text))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.f = f = self.td.name
        w(os.path.join(f, "FILLERS.md"), "| garbage |\n")   # must be ignored
        def row(i, **kw):
            w(os.path.join(f, "ready", i + ".json"), {"id": i, "owner": "o-" + i, "shape": "quarter", "priority_rank": 5.0, **kw})
        row("run1", shape="gpu-q3")
        w(f + "/grants/run1.grant", "regions=mi210_0,184-191 start=2026-11-07T17:13Z end=2026-11-07T22:06Z holds=x\n")
        row("ready-cpu"); w(f + "/dryrun/ready-cpu/PASS.json", {})
        row("ready-gpu", shape="gpu-q3"); w(f + "/dryrun/ready-gpu/PASS.json", {})
        row("smoke"); w(f + "/dryrun/smoke/GPU-SMOKE-QUEUED.json", {"queued_at": "T0"})
        row("failed"); w(f + "/dryrun/failed/FAIL-1.json", {"reason": "boom"})
        row("parked")
        for n in (1, 2, 3):
            w(f + f"/dryrun/parked/FAIL-{n}.json", {"reason": f"bad{n}"})
        stop = os.path.join(f, "STOPFILE"); w(stop)
        row("stopped", stop_file=stop)
        row("done-filed"); w(f + "/grants/done-filed.ended", "rc=0"); w(f + "/filing-done/done-filed.FILED")
        row("done-unfiled"); w(f + "/grants/done-unfiled.complete")
        w(os.path.join(f, "ready", "gone.json.withdrawn-x"), {"id": "gone"})
        w(f + "/" + qs.KEEPER_LOG,
          "2026-11-07T17:00:00Z SNAPSHOT free=q2 busy=q0:old\n2026-11-07T17:00:00Z IDLE-WHY q9: stale\n"
          "2026-11-07T17:05:00Z SNAPSHOT free=q2,q3 busy=gpu-quiet:run1,q0:x\n"
          "2026-11-07T17:05:00Z IDLE-WHY q2: nothing fits\n")

    def tearDown(self):
        self.td.cleanup()

    def test_classify(self):
        r = qs.classify(self.f)
        ids = lambda k: sorted(x["id"] for x in r[k])  # noqa: E731
        self.assertEqual(ids("RUNNING"), ["run1"])
        self.assertEqual(ids("GRANTABLE"), ["ready-cpu", "ready-gpu"])
        self.assertEqual(ids("SMOKE-QUEUED"), ["smoke"])
        self.assertEqual(ids("FAILED"), ["failed"])
        self.assertEqual(ids("PARKED"), ["parked"])
        self.assertEqual(ids("BLOCKED"), ["stopped"])
        self.assertEqual(r["UNFILED-ENDED"], 1)
        g = {x["id"]: x for x in r["GRANTABLE"]}
        self.assertIsNone(g["ready-cpu"]["gpu_wait"])
        self.assertIn("gpu-quiet:run1", g["ready-gpu"]["gpu_wait"])
        self.assertEqual(r["keeper"]["idle_why"], {"q2": "nothing fits"})

    def test_json_and_text(self):
        qs.measure_util = lambda: None
        for argv in (["--flags", self.f, "--json"], ["--flags", self.f]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(qs.main(argv), 0)
            out = buf.getvalue()
            if "--json" in argv:
                j = json.loads(out)
                self.assertEqual([x["id"] for x in j["buckets"]["RUNNING"]], ["run1"])
                self.assertEqual(j["unfiled_ended"], 1)
            else:
                for h in ("RUNNING (1)", "GRANTABLE/QUEUED (2)", "PARKED/BLOCKED (2)", "IDLE", "UNFILED-ENDED: 1", "GPU: waiting"):
                    self.assertIn(h, out)
                self.assertNotIn("FILLERS", out.replace("FILLERS.md is retired", ""))


if __name__ == "__main__":
    unittest.main()
