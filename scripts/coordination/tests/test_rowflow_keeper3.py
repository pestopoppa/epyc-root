"""PM-KEEPER3 2026-11-23 (AutoKernel requests).
#1 quiet gate: a requires_quiet_host row is granted only onto quarters measuring < 15% (foreign) busy, never on the NUMA
   side of a whole-host / bandwidth-heavy grant (and a heavy row never beside a running quiet row).
#2 short GPU smoke slot: smokes <= SHORT_SMOKE_S are named for the next GPU grant boundary; the batch runner can run
   only the short ones (--max-smoke-s).
#3 supersede race: publishing `supersedes: X` blocks X at once (requeue / capcut / resume / re-grant), even while the
   successor still waits for its smoke."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402
import publish_row as pr  # noqa: E402


def cand(rid, opts, rank=20, shape="quarter"):
    return {"id": rid, "shape": shape, "rank": rank, "kind": "grant", "options": [frozenset(o) for o in opts]}


UTIL_QUIET = {"q0": 2.0, "q1": 3.0, "q2": 1.0, "q3": 4.0}


class QuietGate(unittest.TestCase):
    def test_flags(self):
        self.assertTrue(rf.quiet_required({"requires_quiet_host": True}))
        self.assertTrue(rf.quiet_required({"quiet_guard_regions": ["q0"]}))
        self.assertFalse(rf.quiet_required({"busy_fraction": 1.0}))
        self.assertTrue(rf.bandwidth_heavy({"busy_fraction": 0.6}))
        self.assertFalse(rf.bandwidth_heavy({"busy_fraction": 0.59}))
        self.assertFalse(rf.bandwidth_heavy({}))                       # undeclared is not heavy
        self.assertFalse(rf.bandwidth_heavy({"busy_fraction": 1.0, "bandwidth_heavy": False}))
        self.assertTrue(rf.bandwidth_heavy({"bandwidth_heavy": True}))

    def test_foreign_busy_drops_option(self):
        rows = {"gdn": {"requires_quiet_host": True}}
        c = cand("gdn", [{"q0"}, {"q1"}, {"q2"}])
        kept, waits, lines = rf.quiet_gate([c], rows, [], dict(UTIL_QUIET, q1=48.0))
        self.assertEqual(kept[0]["options"], [frozenset({"q0"}), frozenset({"q2"})])
        self.assertEqual(waits, [])

    def test_all_options_busy_waits_with_line(self):
        rows = {"gdn": {"requires_quiet_host": True}}
        c = cand("gdn", [{"q0", "q1"}])
        kept, waits, lines = rf.quiet_gate([c], rows, [], dict(UTIL_QUIET, q1=48.0))
        self.assertEqual(kept, [])
        self.assertEqual(lines["gdn"], "WAIT gdn: foreign busy 48% on q1 (quiet-host needs <15%)")
        self.assertIn("WAIT: foreign busy 48% on q1", waits[0][1])

    def test_threshold_boundary_and_unknown(self):
        rows = {"a": {"requires_quiet_host": True}}
        self.assertEqual(rf.quiet_gate([cand("a", [{"q0"}])], rows, [], dict(UTIL_QUIET, q0=14.9))[0][0]["id"], "a")
        self.assertEqual(rf.quiet_gate([cand("a", [{"q0"}])], rows, [], dict(UTIL_QUIET, q0=15.0))[0], [])
        self.assertEqual(rf.quiet_gate([cand("a", [{"q0"}])], rows, [], {"q0": None})[0], [])   # unknown never quiet

    def test_core_tokens_map_to_quarter(self):
        rows = {"a": {"requires_quiet_host": True}}
        kept, _, _ = rf.quiet_gate([cand("a", [{"c24", "t120"}])], rows, [], dict(UTIL_QUIET, q1=30.0))
        self.assertEqual(kept, [])

    def test_not_beside_heavy_or_whole_host_on_same_side(self):
        rows = {"a": {"requires_quiet_host": True}, "heavy": {"busy_fraction": 0.9}, "light": {"busy_fraction": 0.2}}
        c = cand("a", [{"q0"}, {"q2"}])
        g = [{"id": "heavy", "holds": {"q1"}}]
        self.assertEqual(rf.quiet_gate([c], rows, g, UTIL_QUIET)[0], [])   # DRAM-wide: any quarter blocks
        g = [{"id": "light", "holds": {"q1"}}]
        self.assertEqual(rf.quiet_gate([c], rows, g, UTIL_QUIET)[0][0]["options"], c["options"])
        rows["wh"] = {"shape": "host", "busy_fraction": 0.1}
        kept, waits, lines = rf.quiet_gate([c], rows, [{"id": "wh", "holds": {"q0", "q1", "q2", "q3"}}], UTIL_QUIET)
        self.assertEqual(kept, [])
        self.assertIn("shares its NUMA side", lines["a"])

    def test_build_claim_is_bandwidth_heavy(self):
        rows = {"a": {"requires_quiet_host": True}}
        kept, _, _ = rf.quiet_gate([cand("a", [{"q0"}])], rows, [{"id": "build-x", "holds": {"c72", "t168"}}], UTIL_QUIET)
        self.assertEqual(kept, [])

    def test_heavy_not_placed_beside_running_quiet_row(self):
        rows = {"q": {"requires_quiet_host": True}, "h": {"bandwidth_heavy": True}}
        kept, _, _ = rf.quiet_gate([cand("h", [{"q1"}, {"q2"}])], rows, [{"id": "q", "holds": {"q0"}}], UTIL_QUIET)
        self.assertEqual(kept, [])

    def test_plain_rows_untouched(self):
        c = cand("p", [{"q0"}])
        self.assertEqual(rf.quiet_gate([c], {"p": {}}, [], {"q0": 99.0})[0], [c])

    def test_noise_names_unclaimed_process(self):
        flags = tempfile.mkdtemp(prefix="k3noise-")
        prev = {4242: ("b1", 0.0, 30, "python3"), 77: ("b2", 0.0, 2, "idle")}
        cur = {4242: ("b1", 4.0, 30, "python3"), 77: ("b2", 4.0, 2, "idle")}
        out = rf.quiet_noise(flags, {"q1"}, [], census=cur, prev=prev, dt_s=10.0)
        self.assertEqual([(q, pid, pct) for q, pid, _, pct, _ in out], [("q1", 4242, 40.0)])


class BuildClaimReverse(unittest.TestCase):
    def test_build_refused_while_quiet_row_runs(self):
        flags = tempfile.mkdtemp(prefix="k3build-")
        os.makedirs(os.path.join(flags, "grants"))
        g = [{"id": "quiet-a", "holds": {"q0"}}]
        with self.assertRaises(rf.Refused) as e:
            rf.claim_build(flags, "pm", "72-87", 10, log=lambda *_: None, grants=g,
                           allrows={"quiet-a": {"requires_quiet_host": True}}, free=set())
        self.assertIn("quiet-host row quiet-a is running", str(e.exception))


class FilingFallback(unittest.TestCase):
    def test_workdir_out_result(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "churn"))
        import file_result as fr
        wd = tempfile.mkdtemp(prefix="k3file-")
        self.assertEqual(fr.result_fallback({"workdir": wd}), "")
        os.makedirs(os.path.join(wd, "out"))
        p = os.path.join(wd, "out", "RESULT.json")
        open(p, "w").write('{"verdict": "FUTILITY_CONTENTION", "units": 0}')
        self.assertEqual(fr.result_fallback({"workdir": wd}), p)
        m, sha = fr.load_result(p, "json")
        self.assertEqual(m["verdict"], "FUTILITY_CONTENTION")
        self.assertIsNotNone(sha)


class ShortSmokeSlot(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="k3slot-")

    def q(self, rid, smoke_s, rank=50):
        d = os.path.join(self.flags, "dryrun", rid)
        os.makedirs(d, exist_ok=True)
        rf.atomic_json(os.path.join(d, "GPU-SMOKE-QUEUED.json"), {"id": rid, "smoke_s": smoke_s,
                                                                  "spec": {"priority_rank": rank}, "queued_at": "2026-11-23T10:01:00Z"})

    def test_short_list(self):
        self.q("c19attr", 300)
        self.q("long", 1800)
        self.assertEqual(rf.short_gpu_smokes(self.flags), [("c19attr", 300)])

    def test_runner_skips_long_in_short_slot(self):
        self.q("c19attr", 120, rank=30)
        self.q("long", 1800, rank=10)
        ran = []
        orig = pr.run_smoke
        pr.run_smoke = lambda flags, rid, *a, **k: (ran.append(rid), ("FAIL", "test"))[1]
        orig_alert = pr.alert_queued_nonpass
        pr.alert_queued_nonpass = lambda *a, **k: None
        try:
            pr.run_gpu_queue(self.flags, max_smoke_s=300)
        finally:
            pr.run_smoke, pr.alert_queued_nonpass = orig, orig_alert
        self.assertEqual(ran, ["c19attr"])


class SupersedeBlock(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="k3sup-")
        for d in ("ready", "grants", "dryrun"):
            os.makedirs(os.path.join(self.flags, d))
        self.lines = []

    def test_block_marker_and_log(self):
        out = rf.supersede_block(self.flags, {"id": "r2", "supersedes": "r1"}, log=self.lines.append)
        self.assertEqual(out, ["r1"])
        self.assertTrue(self.lines[0].startswith("SUPERSEDED-BLOCK r1 by r2"))
        self.assertEqual(rf.superseded_by(self.flags, "r1"), "r2")
        rf.supersede_block(self.flags, {"id": "r2", "supersedes": ["r1"]}, log=self.lines.append)
        self.assertEqual(len(self.lines), 1)   # idempotent
        self.assertEqual(rf.superseded_by(self.flags, "r2"), "")

    def test_unsmoked_successor_visible(self):
        d = os.path.join(self.flags, "dryrun", "r2")
        os.makedirs(d)
        rf.atomic_json(os.path.join(d, "unpublished.json"), {"id": "r2", "supersedes": "r1"})
        self.assertEqual(rf.superseded_by(self.flags, "r1"), "r2")
        self.assertEqual(rf.capcut_closed(self.flags, "r1"), "superseded by r2")

    def test_queued_marker_spec_visible(self):
        d = os.path.join(self.flags, "dryrun", "r2")
        os.makedirs(d)
        rf.atomic_json(os.path.join(d, "GPU-SMOKE-QUEUED.json"), {"id": "r2", "spec": {"supersedes": ["r1"]}})
        self.assertEqual(rf.superseded_by(self.flags, "r1"), "r2")

    def test_autorequeue_refused_for_superseded_resumable(self):
        rf.atomic_json(rf.ready_path(self.flags, "r1"), {"id": "r1", "resumable": True})
        with open(os.path.join(self.flags, "grants", "r1.ended"), "w") as f:
            f.write("rc=75 time=2026-11-23T11:00:00Z reason=partial-native-incomplete\n")
        self.assertEqual(rf.autorequeue_decision(self.flags, "r1")[0], "requeue")
        rf.supersede_block(self.flags, {"id": "r2", "supersedes": "r1"}, log=self.lines.append)
        self.assertIsNone(rf.autorequeue_decision(self.flags, "r1")[0])


if __name__ == "__main__":
    unittest.main()
