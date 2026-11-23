"""E5 starvation fixes 2026-11-23 (inf45-e5v2-stageb-r8-20261122, quiet-host, lost a second night).
A: an orphaned llama-server (pid 2003761, spec-stale1-build :8080, launcher dead) ran outside every grant; the keeper granted
   E5 the whole host 4 times and its clean-runtime gate refused each time. foreign_server_gate keeps quiet-host / whole-host
   rows out of planning while such a server runs, logs WAIT, alerts once, never kills.
B: WAIT-FOR-SMOKE kept the quiet-host row out of planning behind queued better-ranked GPU smokes before any drain formed;
   smoke_wait_starved releases it after qh_smoke_wait_max_s (default 20 min)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

ORPHAN = {"pid": 2003761, "ppid": 1, "pgid": 2003761, "birth": "99", "comm": "llama-server",
          "cmd": "llama-server -m spec-stale1.gguf --port 8080"}


def cand(rid, shape, rank=25):
    return {"id": rid, "shape": shape, "rank": rank, "options": [frozenset({"q0", "q1", "q2", "q3", "gpu-quiet"})]}


class ForeignServer(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="e5gate-")
        os.makedirs(os.path.join(self.flags, "grants"))
        os.makedirs(os.path.join(self.flags, "ready"))
        self.lines, self.alerts = [], []

    def emit(self, *a, **k):
        self.alerts.append(a)

    def gate(self, cands, procs, grants=(), stack=None, parent=None, dry=False):
        return rf.foreign_server_gate(self.flags, cands, list(grants), self.lines.append, dry=dry, procs=procs,
                                      stack=stack or {}, parent=parent, emit=self.emit)

    def test_orphan_blocks_quiet_host_and_host_rows_only(self):
        cs = [cand("e5", "quiet-host"), cand("wide", "host"), cand("q", "quarter")]
        kept, waits = self.gate(cs, [ORPHAN])
        self.assertEqual([c["id"] for c in kept], ["q"])
        self.assertEqual({c["id"] for c, _ in waits}, {"e5", "wide"})
        self.assertTrue(any(l.startswith("WAIT e5: foreign inference server pid=2003761 cmd=") and "(no grant owns it)" in l
                            for l in self.lines))
        self.assertEqual(len(self.alerts), 2)   # one per (row, pid); notify.emit dedupes repeats on its key
        self.assertEqual(self.alerts[0][1], "foreign-inference-server")
        self.assertEqual(self.alerts[0][3], "2003761:99")

    def test_no_foreign_server_no_change(self):
        cs = [cand("e5", "quiet-host")]
        kept, waits = self.gate(cs, [])
        self.assertEqual(kept, cs)
        self.assertEqual(waits, [])

    def test_grant_tree_owns_server(self):
        g = {"id": "row-a", "pid": 5000, "holds": set()}
        srv = dict(ORPHAN, pid=5002, ppid=5001, pgid=5001)
        parents = {5002: 5001, 5001: 5000, 5000: 1}
        f = rf.foreign_inference_servers(self.flags, [g], procs=[srv], stack={}, parent=lambda p: parents.get(p, 0))
        self.assertEqual(f, [])

    def test_live_smoke_tree_owns_server(self):
        d = os.path.join(self.flags, "dryrun", "smk")
        os.makedirs(d)
        rf.atomic_json(os.path.join(d, "RUNNING.json"), {"pid": 7000, "pgid": 7000})
        srv = dict(ORPHAN, pid=7005, ppid=7000, pgid=7000)
        self.assertEqual(rf.foreign_inference_servers(self.flags, [], procs=[srv], stack={}), [])

    def test_stack_service_requires_port_match(self):
        self.assertEqual(rf.foreign_inference_servers(self.flags, [], procs=[ORPHAN], stack={2003761: 8080}), [])
        # a stale state file whose pid was reused by a server on another port is NOT stack-managed
        self.assertEqual(len(rf.foreign_inference_servers(self.flags, [], procs=[ORPHAN], stack={2003761: 8070})), 1)

    def test_stack_state_file_parsed(self):
        p = os.path.join(self.flags, "orchestrator_state.json")
        rf.atomic_json(p, {"server_8070": {"pid": 26641, "port": 8070}, "searxng": {"pid": -1, "port": 8888}, "x": 3})
        self.assertEqual(rf.stack_service_pids(p), {26641: 8070})

    def test_dry_tick_never_alerts(self):
        self.gate([cand("e5", "quiet-host")], [ORPHAN], dry=True)
        self.assertEqual(self.alerts, [])

    def test_scan_matches_server_names(self):
        for n in ("llama-server", "sd-server", "whisper-server", "whisper-cli"):
            self.assertTrue(rf.INFER_SERVER_RE.match(n), n)
        for n in ("llama-bench", "python3", "earlyoom"):
            self.assertFalse(rf.INFER_SERVER_RE.match(n), n)

    def test_gate_never_kills(self):
        src = open(rf.__file__).read()
        start = src.index("def inference_server_procs")
        body = src[start:src.index("def qh_smoke_wait_max_s")]
        self.assertNotIn("os.kill", body)
        self.assertNotIn("killpg", body)


class SmokeWaitStarvation(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="e5smoke-")
        os.environ.pop("ROWFLOW_QH_SMOKE_WAIT_MAX_S", None)

    def test_released_after_default_20_min(self):
        e5, g = cand("e5", "quiet-host"), cand("gpu-row", "gpu-q3")
        t0 = 1_800_000_000.0
        self.assertEqual(rf.smoke_wait_starved(self.flags, [e5, g], now=t0), [])
        self.assertEqual(rf.smoke_wait_starved(self.flags, [e5, g], now=t0 + 1199), [])
        self.assertEqual(rf.smoke_wait_starved(self.flags, [e5, g], now=t0 + 1200), ["e5"])   # gpu rows still wait

    def test_clock_resets_when_row_stops_waiting(self):
        e5 = cand("e5", "quiet-host")
        t0 = 1_800_000_000.0
        rf.smoke_wait_starved(self.flags, [e5], now=t0)
        rf.smoke_wait_starved(self.flags, [], now=t0 + 600)
        self.assertEqual(rf.smoke_wait_starved(self.flags, [e5], now=t0 + 1300), [])

    def test_configurable(self):
        rf.atomic_json(os.path.join(self.flags, "allocator.json"), {"quiet_smoke_wait_max_s": 300})
        self.assertEqual(rf.qh_smoke_wait_max_s(self.flags), 300.0)
        os.environ["ROWFLOW_QH_SMOKE_WAIT_MAX_S"] = "60"
        try:
            self.assertEqual(rf.qh_smoke_wait_max_s(self.flags), 60.0)
        finally:
            del os.environ["ROWFLOW_QH_SMOKE_WAIT_MAX_S"]


if __name__ == "__main__":
    unittest.main()
