#!/usr/bin/env python3
"""ws58 2026-11-02: publish smoke must never wait on held regions. The manifest survives only a smoke PASS, an old FAIL
memo is never reused as this smoke's result, and the engine's smoke claim is the smoke's own cpus (no region-lock)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
_RF = os.path.join(os.path.dirname(_TESTS), "rowflow")
sys.path.insert(0, _RF)
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        self.rid = "r1"
        self.dd = rf.dry_dir(self.flags, self.rid)
        os.makedirs(self.dd)
        with open(os.path.join(self.dd, "FAIL-1.json"), "w") as f:
            json.dump({"reason": "old 00:07Z fail"}, f)

    def _publish(self, spec, flags, source=None):
        rf.atomic_json(rf.ready_path(flags, self.rid), {"id": self.rid})
        return {"id": self.rid}

    def _run(self, verdict):
        seen = {}

        def dry(flags, rid, regions, one_quarter=False, smoke_s=None):
            seen["fails_at_start"] = rf.fail_paths(flags, rid)
            if verdict == "FAIL":
                rf.atomic_json(os.path.join(rf.dry_dir(flags, rid), "FAIL-1.json"), {"reason": "new"})
            if verdict == "RAISE":
                raise rf.Refused("boom")
            return verdict, "msg"
        with mock.patch.object(pr, "smoke_regions", return_value="0-3"), mock.patch.object(rf, "publish", self._publish), \
                mock.patch.object(rf, "dryrun_run", dry), mock.patch.object(rf, "tail", return_value=[]):
            try:
                pr.publish_smoked({"lane": "cpu"}, self.flags, "t")
                ok = True
            except rf.Refused:
                ok = False
        return ok, seen

    def test_pass_keeps_manifest_and_retires_old_fail(self):
        ok, seen = self._run("PASS")
        self.assertTrue(ok)
        self.assertEqual(seen["fails_at_start"], [])
        self.assertTrue(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertTrue(os.listdir(os.path.join(self.dd, "superseded")))

    def test_fail_or_refusal_leaves_no_manifest(self):
        for v in ("FAIL", "RAISE"):
            ok, _ = self._run(v)
            self.assertFalse(ok, v)
            self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)), v)
            self.assertTrue(os.path.exists(pr.unpublished_path(self.flags, self.rid)), v)

    def test_wait_is_queued_for_the_keeper_not_failed(self):
        """operator 2026-11-05: an immediate smoke that only WAITed (lock / held host) is queued, never a FAIL."""
        ok, _ = self._run("WAIT")
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertTrue(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)))
        self.assertEqual(rf.fail_paths(self.flags, self.rid), [])

    def test_no_whole_host_refusal_or_key(self):
        for name in ("rowflow.py", "publish_row.py"):
            src = open(os.path.join(_RF, name)).read()
            self.assertNotIn("dryrun_whole_host", src)
            self.assertNotIn("cannot dry-run on one quarter", src)

    def test_engine_smoke_claim_is_smoke_cpus_without_region_lock(self):
        src = open(os.path.join(_RF, "filler_run15.sh")).read()
        self.assertIn('SMOKE_NOLOCK=1; CLAIM_CPUS=${WS58_REGIONS:-$CLAIM_CPUS}', src)
        self.assertIn('if [ "$CLASS" = gpu ]; then rlargs=(--gpu-quiet shared); else rlargs=(); fi', src)
        self.assertIn('setsid taskset -c "${CLAIM_CPUS:-$CPUS}"', src)


if __name__ == "__main__":
    unittest.main()
