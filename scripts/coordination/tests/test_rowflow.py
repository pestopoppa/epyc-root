#!/usr/bin/env python3
"""End-to-end tests of the simplified row flow (scripts/coordination/rowflow/): publish -> keeper dry run on the real
engine (filler_run15.sh under a stub region-lock) -> grantable -> stale on launcher change; FAIL records, parking,
legacy migration, unit counting, grant_ok v4. Everything runs in a temp dir; no live compute-flags file is touched."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RF = os.path.join(_COORD, "rowflow")
sys.path.insert(0, _RF)
import rowflow as rf  # noqa: E402


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    if mode:
        os.chmod(path, mode)


class Fixture:
    """A temp compute-flags tree; rowflow's job-dir root (TMP) is pointed at it."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="rowflow-test-")
        rf.TMP = self.root + "/"
        self.flags = os.path.join(self.root, "compute-flags")
        os.makedirs(os.path.join(self.flags, "grants"))
        os.makedirs(os.path.join(self.flags, "ready"))
        os.makedirs(os.path.join(self.flags, "bin", "rowflow"))
        for f in ("filler_run15.sh", "filler_lib.sh", "dryrun_disk_policy.json"):
            shutil.copy(os.path.join(_RF, f), os.path.join(self.flags, "bin", "rowflow", f))
        self.engine = os.path.join(self.flags, "bin", "rowflow", "filler_run15.sh")
        self.rl = os.path.join(self.root, "region-lock")
        write(self.rl, textwrap.dedent("""\
            #!/bin/bash
            # stub region-lock: everything free; `run ... -- CMD...` execs CMD
            if [ "$1" = status ]; then printf '  q0  free\\n  q1  free\\n  q2  free\\n  q3  free\\ngpu-quiet  free\\n'; exit 0; fi
            while [ $# -gt 0 ]; do [ "$1" = -- ] && { shift; break; }; shift; done
            exec "$@"
            """), 0o755)
        rf.FLAGS = self.flags
        rf.RL = self.rl
        os.environ["FILLER_RL"] = self.rl
        os.environ["ROWFLOW_FLAGS"] = self.flags
        os.environ["FILLER_DISK_FLOOR_GIB"] = "0"

    def job(self, rid, behaviour="ok"):
        """A job dir with a launcher on filler_run15.sh. behaviour: ok (one unit every 2 s, honours the stop file),
        crash (exit 1 before any unit), noexit (writes units, ignores the stop file)."""
        d = os.path.join(self.root, rid)
        os.makedirs(os.path.join(d, "out"), exist_ok=True)
        body = {
            "ok": 'for i in 1 2 3 4 5 6 7 8 9 10; do [ -e "$FILLER_STOPFILE" ] && exit 75; echo "{\\"item\\": $i, \\"score\\": 1}" >> "$D/out/results.jsonl"; sleep 2; done; exit 0',
            "crash": 'echo "model path missing" >&2; exit 1',
            "noexit": 'for i in $(seq 1 400); do echo "{\\"item\\": $i}" >> "$D/out/results.jsonl"; sleep 2; done',
        }[behaviour]
        write(os.path.join(d, "job.sh"), f'#!/bin/bash\nD={d}\n{body}\n', 0o755)
        write(os.path.join(d, "launch.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            set -euo pipefail
            D={d}
            ENGINE={self.engine}
            exec bash "$ENGINE" --id {rid} --class cpu --min-window 300 --stop "$D/STOP" \\
              --complete-cmd "test -e $D/out/COMPLETE" --workdir "$D" --cmd "bash '$D/job.sh'"
            """), 0o755)
        return d

    def spec(self, rid, d, **kw):
        s = {"id": rid, "owner": "codex-test", "launcher": os.path.join(d, "launch.sh"), "lane": "cpu",
             "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "score>=1 on every item",
             "estimate_s": 600, "handoff_task": "handoffs/active/test.md:T-1", "priority_rank": 5, "dryrun_timeout_s": 60}
        s.update(kw)
        return s

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


class RowflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_01_publish_derives_everything(self):
        fx = self.fx
        d = fx.job("t-pub-20261101")
        row = rf.publish(fx.spec("t-pub-20261101", d), fx.flags)
        self.assertEqual(row["schema"], "epyc.row.v3")
        self.assertEqual(row["min_window_s"], 300)
        self.assertEqual(row["regions"], "any-cpu-quarter")
        self.assertEqual(row["result_format"], "jsonl")
        self.assertGreaterEqual(row["window_s"], 300 + 300)
        self.assertEqual(row["window_s"] % 60, 0)
        self.assertTrue(row["scratch_root"].startswith(fx.root))
        self.assertIn("out/results.jsonl", row["keep"])
        self.assertEqual(row["launcher"]["sha256"], rf.sha256(os.path.join(d, "launch.sh")))
        self.assertEqual(rf.status(fx.flags, "t-pub-20261101")["state"], "needs-dryrun")
        # spec errors are one refusal each
        bad = fx.spec("t-pub-20261101", d, lane="gpu")
        with self.assertRaises(rf.Refused):
            rf.publish(bad, fx.flags)
        bad = fx.spec("t-pub-20261101", d, min_window_s=999)
        with self.assertRaises(rf.Refused):
            rf.publish(bad, fx.flags)

    def test_02_dryrun_pass_then_grantable_then_stale(self):
        fx = self.fx
        rid = "t-ok-20261101"
        d = fx.job(rid)
        rf.publish(fx.spec(rid, d), fx.flags)
        picks = rf.dryrun_pick(fx.flags)
        self.assertTrue(any(p[0] == rid for p in picks), picks)
        v, msg = rf.dryrun_run(fx.flags, rid)
        self.assertEqual(v, "PASS", msg + "\n" + "\n".join(rf.tail(os.path.join(rf.dry_dir(fx.flags, rid), "launcher.out"), 40)))
        p = json.load(open(rf.pass_path(fx.flags, rid)))
        self.assertGreaterEqual(p["units"], 1)
        self.assertTrue(p["ended"].startswith("rc=75") or p["ended"].startswith("rc=0"), p["ended"])
        self.assertFalse(os.path.exists(os.path.join(fx.flags, "grants", rid + ".grant")), "dry-run grant must be gone")
        self.assertFalse(os.path.exists(os.path.join(fx.flags, "grants", rid + ".ended")), "the real id must not be consumed")
        self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable")
        rc, line = rf.grant_check(fx.flags, rid)
        self.assertEqual(rc, 0, line)
        # the launcher changes -> a new dry run is needed, automatically, and the writer is refused
        with open(os.path.join(d, "launch.sh"), "a") as f:
            f.write("# edited\n")
        self.assertEqual(rf.status(fx.flags, rid)["state"], "stale")
        rc, line = rf.grant_check(fx.flags, rid)
        self.assertEqual(rc, 2, line)
        # grant_ok v4 through the shell with a stub ram_admit
        ram = os.path.join(fx.root, "ram_admit.sh")
        write(ram, "#!/bin/bash\necho admit-stub\n", 0o755)
        env = dict(os.environ, GRANT_OK_TEST_RAM_ADMIT=ram, ROWFLOW_PY=os.path.join(_RF, "rowflow.py"))
        r = subprocess.run(["bash", os.path.join(_RF, "grant_ok_v4.sh"), rid, "8"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)
        self.assertIn("stale", r.stdout)

    def test_03_dryrun_fail_is_one_fix_task_and_parks_after_three(self):
        fx = self.fx
        rid = "t-crash-20261101"
        d = fx.job(rid, "crash")
        rf.publish(fx.spec(rid, d, dryrun_timeout_s=40), fx.flags)
        v, msg = rf.dryrun_run(fx.flags, rid)
        self.assertEqual(v, "FAIL", msg)
        st = rf.status(fx.flags, rid)
        self.assertEqual(st["state"], "failed")
        self.assertIn("fix dry-run failure", st["fix_task"])
        # unchanged launcher: not retried
        self.assertEqual(rf.dryrun_run(fx.flags, rid)[0], "WAIT")
        self.assertFalse(any(p[0] == rid for p in rf.dryrun_pick(fx.flags)))
        # two more edits -> two more fails -> parked + escalation note
        for i in range(2):
            with open(os.path.join(d, "launch.sh"), "a") as f:
                f.write(f"# attempt {i}\n")
            self.assertEqual(rf.status(fx.flags, rid)["state"], "needs-dryrun")
            self.assertEqual(rf.dryrun_run(fx.flags, rid)[0], "FAIL")
        st = rf.status(fx.flags, rid)
        self.assertEqual(st["state"], "parked", st)
        self.assertTrue(os.path.exists(os.path.join(fx.flags, "operator-escalations", "t-crash.md")))
        # lineage_reset in a fresh spec re-admits
        rid2 = "t-crash-r2-20261101"
        d2 = fx.job(rid2)
        rf.publish(fx.spec(rid2, d2, lineage_reset=3), fx.flags)
        self.assertEqual(rf.status(fx.flags, rid2)["state"], "needs-dryrun")

    def test_04_noexit_job_fails_clean_truncation(self):
        fx = self.fx
        rid = "t-noexit-20261101"
        d = fx.job(rid, "noexit")
        rf.publish(fx.spec(rid, d, dryrun_timeout_s=60), fx.flags)
        rf.STOP_GRACE_S = 12
        try:
            v, msg = rf.dryrun_run(fx.flags, rid)
        finally:
            rf.STOP_GRACE_S = 180
        self.assertEqual(v, "FAIL", msg)
        self.assertIn("did not stop", msg)
        self.assertFalse(os.path.exists(os.path.join(fx.flags, "grants", rid + ".grant")))

    def test_05_count_units(self):
        fx = self.fx
        p = os.path.join(fx.root, "u.jsonl")
        write(p, '{"a":1}\nnot json\n{"b":2}\n')
        self.assertEqual(rf.count_units(p, "jsonl"), 2)
        p2 = os.path.join(fx.root, "u.json")
        write(p2, '{"results": [1,2,3]}')
        self.assertEqual(rf.count_units(p2, "json"), 3)
        write(p2, '{"t_s": 1.2}')
        self.assertEqual(rf.count_units(p2, "json"), 1)
        write(p2, 'partial{')
        self.assertEqual(rf.count_units(p2, "json"), 0)
        p3 = os.path.join(fx.root, "u.csv")
        write(p3, "a,b\n1,2\n3,4\n")
        self.assertEqual(rf.count_units(p3, "csv"), 2)
        self.assertEqual(rf.count_units(os.path.join(fx.root, "missing.jsonl"), "jsonl"), 0)
        self.assertEqual(rf.count_units(os.path.join(fx.root, "u*.jsonl"), "jsonl"), 2)
        self.assertEqual(rf.count_units(p, "custom:test -s " + p), 1)

    def test_06_legacy_migration_rewrites_engine(self):
        fx = self.fx
        rid = "t-legacy-20261030"
        d = fx.job(rid)
        lp = os.path.join(d, "launch.sh")
        old = open(lp).read().replace("bin/rowflow/filler_run15.sh", "bin/qual-v1/filler_run14.sh")
        write(lp, old, 0o755)
        legacy = {"id": rid, "owner": "codex3", "regions": "any-cpu-quarter", "window_s": 3600, "min_window_s": 300, "gib": 8,
                  "launcher": {"path": lp, "sha256": "x"}, "scratch_root": d, "keep": "*.json,out/*.jsonl",
                  "decision_rule": "legacy rule", "result_path": os.path.join(d, "out", "results.jsonl"), "priority_rank": 100}
        spec = rf.spec_from_legacy(legacy, fx.flags)
        self.assertTrue(spec["launcher"].endswith("launch.v15.sh"))
        self.assertIn("bin/rowflow/filler_run15.sh", open(spec["launcher"]).read())
        self.assertNotIn("filler_run14", open(spec["launcher"]).read())
        self.assertEqual(open(lp).read(), old, "the original launcher is untouched")
        row = rf.publish(spec, fx.flags, source="migrate")
        self.assertEqual(row["keep"][:2], ["*.json", "out/*.jsonl"])
        self.assertEqual(row["lane"], "cpu")
        self.assertEqual(rf.status(fx.flags, rid)["state"], "needs-dryrun")

    def test_07_parse_live_launcher_shapes(self):
        """Real launcher shapes seen on the host (GPU exclusive with env-defaulted claim cpus; backslash continuations)."""
        fx = self.fx
        d = os.path.join(fx.root, "shape-gpu")
        write(os.path.join(d, "launch.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            set -euo pipefail
            D={d}
            ENGINE={fx.engine}
            CLAIM_CPUS="${{WS58_QUAL_CPUS:-${{FILLER_CPUS:-184-191}}}}"
            exec bash "$ENGINE" \\
              --id shape-gpu \\
              --class gpu --gpu-quiet exclusive --claim-cpus "$CLAIM_CPUS" \\
              --role bench --min-window 6000 \\
              --stop "$D/STOP" \\
              --port 18397 \\
              --complete-cmd "python3 -B '$D/completion_check.py'" \\
              --workdir "$D" \\
              --requires-tool /usr/bin/python3.13 \\
              --qual-interpreter /usr/bin/python3.13 \\
              --cmd "bash '$D/job.sh'"
            """), 0o755)
        o = rf.parse_launcher(os.path.join(d, "launch.sh"))
        self.assertEqual((o["id"], o["class"], o["min_window"], o["ports"], o["gpu_quiet"]), ("shape-gpu", "gpu", 6000, [18397], "exclusive"))
        self.assertEqual(o["workdir"], d)
        self.assertEqual(o["stop"], d + "/STOP")

    def test_08_lane_helpers(self):
        self.assertEqual(rf.quarters_of("0-23"), {"q0"})
        self.assertEqual(rf.quarters_of("72-95"), {"q3"})
        self.assertEqual(rf.quarters_of("0-47,96-143"), {"q0", "q1"})
        self.assertEqual(rf.quarters_of("mi210_0,184-191"), set())
        self.assertEqual(rf.quarters_of("q2"), {"q2"})
        free = {"q0", "q1", "q2", "q3", "gpu-quiet"}
        self.assertEqual(rf.resolve_regions(self.fx.flags, "any-cpu-quarter", free, [("x", "0-23")]), "24-47")
        self.assertFalse(rf.lane_free(self.fx.flags, "mi210_0,184-191", free, [("y", "mi210_0,184-191")]))
        self.assertTrue(rf.lane_free(self.fx.flags, "mi210_0,184-191", free, [("y", "0-23")]))
        self.assertFalse(rf.lane_free(self.fx.flags, "24-47", free, [("y", "0-95")]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
