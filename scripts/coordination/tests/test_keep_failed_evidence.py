"""FAIL/FUTILITY rows keep out/logs, out/prof, out/servers/*.log until the successor ends (or 72 h)."""
import io
import contextlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
for p in (str(_COORD), str(_COORD / "churn"), str(_COORD / "rowflow")):
    if p not in sys.path:
        sys.path.insert(0, p)
import filing  # noqa: E402
import keep_failed  # noqa: E402
import reclaim_row  # noqa: E402
import scratch_guard  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.flags = os.path.join(self.root, "flags")
        for d in ("ready", "grants", "filing-done"):
            os.makedirs(os.path.join(self.flags, d))
        self._env = patch.dict(os.environ, {"RECLAIM_TMP_ROOT": os.path.dirname(self.root)})
        self._env.start()
        scratch_guard.TMP_ROOT = os.path.dirname(self.root)

    def tearDown(self):
        self._env.stop(); self.tmp.cleanup()

    def mk(self, rid, verdict, end_age_h=0.0, scratch=True):
        sr = os.path.join(self.root, "s-" + rid)
        for sub in ("out/logs", "out/prof", "out/servers", "out/other"):
            os.makedirs(os.path.join(sr, sub), exist_ok=True)
        for f in ("out/logs/a.log", "out/prof/p0.json", "out/servers/s.log", "out/other/x.bin", "RESULT.json"):
            Path(sr, f).write_text(json.dumps({"verdict": verdict}))
        m = {"schema": "epyc.row.v3", "id": rid, "scratch_root": sr, "result_path": os.path.join(sr, "RESULT.json"),
             "published_at": "2026-11-25T00:00:00Z"}
        Path(self.flags, "ready", rid + ".json").write_text(json.dumps(m))
        self.end(rid, end_age_h)
        Path(self.flags, "filing-done", rid + ".verdict.json").write_text(json.dumps({"row_verdict": verdict}))
        Path(self.flags, "filing-done", rid + ".FILED").write_text("FILED\n")
        return sr

    def end(self, rid, age_h=0.0):
        p = os.path.join(self.flags, "grants", rid + ".ended")
        Path(p).write_text("rc=0\n")
        t = time.time() - age_h * 3600
        os.utime(p, (t, t))

    def reclaim(self, rid):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), \
                patch.object(reclaim_row.wg, "gather_probe", lambda: type("P", (), {"busy": lambda s, r: None})()), \
                patch.object(reclaim_row, "open_fd_under", lambda r: None):
            reclaim_row.main([rid, "--flags", self.flags, "--pre-filed"])
        return buf.getvalue()

    def reaped(self, out, sub):
        return any(f"verdict=REAP" in ln and f"/{sub}" in ln for ln in out.splitlines())

    def test_fail_row_keeps_logs(self):
        self.mk("kf-r1", "FAIL_CORRECTNESS_TBO")
        out = self.reclaim("kf-r1")
        self.assertIn("RECLAIM-KEEP-FAILED kf-r1: logs kept until successor ends", out)
        for sub in ("out/logs", "out/prof", "out/servers"):
            self.assertFalse(self.reaped(out, sub), out)
        self.assertTrue(self.reaped(out, "out/other"), out)
        self.assertTrue(os.path.exists(os.path.join(self.flags, "reclaim-deferred", "kf-r1.json")))

    def test_futility_keeps_and_reclaimed_after_successor_ended(self):
        self.mk("kf-r1", "FUTILITY_X")
        self.assertNotIn("out/logs", "".join(l for l in self.reclaim("kf-r1").splitlines() if "REAP" in l and "KEEP" not in l))
        self.end("kf-r2")
        out = self.reclaim("kf-r1")
        self.assertNotIn("RECLAIM-KEEP-FAILED", out)
        self.assertTrue(self.reaped(out, "out/logs") or self.reaped(out, "out"), out)

    def test_72h_fallback(self):
        self.mk("kf-r1", "FAIL_X", end_age_h=73)
        self.assertNotIn("RECLAIM-KEEP-FAILED", self.reclaim("kf-r1"))
        self.mk("kf-r3", "FAIL_X", end_age_h=71)
        self.assertIn("RECLAIM-KEEP-FAILED", self.reclaim("kf-r3"))

    def test_pass_row_reclaimed_as_before(self):
        self.mk("kf-r1", "PASS")
        out = self.reclaim("kf-r1")
        self.assertNotIn("RECLAIM-KEEP-FAILED", out)
        self.assertTrue(self.reaped(out, "out"), out)
        self.assertFalse(os.path.exists(os.path.join(self.flags, "reclaim-deferred", "kf-r1.json")))

    def test_prof_trim_over_2gib(self):
        sr = self.mk("kf-r1", "FAIL_X")
        for i in range(25):
            p = Path(sr, "out/prof", f"p{i:02d}.json"); p.write_text("x")
            os.utime(p, (1000 + i, 1000 + i))
        with patch.object(keep_failed, "PROF_MAX_BYTES", 10):
            Path(sr, "out/prof/big").write_text("y" * 50)
            lines = []
            keep = keep_failed.evidence_paths(sr, lines.append, "kf-r1")
        profs = [k for k in keep if "/out/prof" in k]
        self.assertEqual(len(profs), 20)
        self.assertTrue(any("RECLAIM-KEEP-TRIM" in l for l in lines))
        self.assertIn(os.path.join(sr, "out/logs"), keep)

    def test_deferred_marker_released_only_after_hold(self):
        self.mk("kf-r1", "FAIL_X")
        filing.defer_keep_failed(self.flags, "kf-r1", "FAIL_X")
        calls = []
        with patch.object(reclaim_row, "main", lambda argv: calls.append(argv) or 0):
            self.assertEqual(filing.run_deferred_reclaims(self.flags, log=lambda *_: None), [])
            self.end("kf-r2")
            self.assertEqual(filing.run_deferred_reclaims(self.flags, log=lambda *_: None), ["kf-r1"])
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
