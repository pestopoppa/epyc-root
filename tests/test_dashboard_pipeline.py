"""Pipeline page: step mapping, compute fold, route + registry + panel wiring (hermetic fixtures)."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from dashboard import panels, pipeline_status as ps, server

NOW = time.time()


def _fixture(root: Path, sessions: dict, report: dict | None = None, log: str = "", snap: str = ""):
    (root / "grants").mkdir()
    (root / "ready").mkdir()
    (root / "dryrun").mkdir()
    (root / "handoff-sessions.json").write_text(json.dumps(
        {"max_live": 5, "sessions": sessions, "dispatcher": {"last_pass": "2027-01-15T08:00:00Z"}}))
    for slug in sessions:
        (root / "handoff-sessions" / slug).mkdir(parents=True)
        if report is not None:
            (root / "handoff-sessions" / slug / "report.json").write_text(json.dumps(report))
    (root / "handoff-sessions.log").write_text(log)
    (root / "ws58-calendar-keeper.log").write_text(snap)


class StepMapping(unittest.TestCase):
    def test_report_next_wins(self):
        e = {"status": "live"}
        self.assertEqual(ps.step_of(e, {"next": "non-inference"}, True, None)[0], "working")
        self.assertEqual(ps.step_of(e, {"next": "inference"}, True, None)[0], "making-ready")
        self.assertEqual(ps.step_of(e, {"next": "blocked", "blocked_by": ["r1"]}, False, None)[0], "paused")
        self.assertEqual(ps.step_of(e, {"next": "done"}, False, None)[0], "done")

    def test_fallback_from_liveness_and_log(self):
        self.assertEqual(ps.step_of({"status": "live"}, None, True, {"kind": "RESUME", "event": "idle"})[0], "working")
        self.assertEqual(ps.step_of({"status": "live"}, None, True, {"kind": "NUDGE"})[0], "nudged")
        self.assertEqual(ps.step_of({"status": "live", "noop_reason": "4 own inference task(s) to publish"}, None, True, None)[0], "making-ready")
        self.assertEqual(ps.step_of({"status": "suspended", "await_event": True}, None, False, None)[0], "paused")
        self.assertEqual(ps.step_of({"status": "suspended"}, None, False, None)[0], "queued")

    def test_every_step_has_an_owner_and_a_label(self):
        self.assertEqual(set(ps.STEP_OWNER), set(ps.STEPS))
        self.assertTrue(set(ps.STEP_OWNER.values()) <= {"DET", "AI"})
        self.assertEqual(ps.STEP_OWNER["working"], "AI")
        self.assertEqual(ps.STEP_OWNER["paused"], "DET")

    def test_pid_alive_rejects_junk(self):
        self.assertTrue(ps.pid_alive(os.getpid()))
        for bad in (None, 0, -1, True, "1"):
            self.assertFalse(ps.pid_alive(bad))


class Payload(unittest.TestCase):
    def test_missing_registry_is_absent_not_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = ps.build_payload(Path(d), NOW)
            self.assertFalse(p["present"])

    def test_sessions_compute_and_blocked_rows(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sess = {"live-a": {"status": "live", "pid": os.getpid(), "engine": "codex", "handoff": "h/a.md"},
                    "wait-b": {"status": "suspended", "pid": None, "engine": "codex", "await_event": True},
                    "q-c": {"status": "suspended", "pid": None, "engine": "codex"}}
            _fixture(root, sess, snap="2027-01-15T08:00:00Z SNAPSHOT free=q0,q1 busy=q3:rowrun,gpu-quiet:rowrun cands=0\n",
                     log="2027-01-15T07:59:00Z YIELD q-c: handoff rank #9 score=1.0 is below the live cap\n")
            (root / "handoff-sessions" / "wait-b" / "report.json").write_text(
                json.dumps({"next": "blocked", "blocked_by": ["rowready", "rowrun"]}))
            (root / "grants" / "rowrun.grant").write_text("regions=0-1 start=a end=b holds=q3,gpu-quiet\n")
            (root / "grants" / "rowdone.grant").write_text("holds=q0\n")
            (root / "grants" / "rowdone.complete").write_text("")
            for r in ("rowready", "rowrun", "rowfail"):
                (root / "ready" / f"{r}.json").write_text("{}")
            (root / "dryrun" / "rowready").mkdir()
            (root / "dryrun" / "rowready" / "PASS.json").write_text("{}")
            (root / "dryrun" / "rowfail").mkdir()
            (root / "dryrun" / "rowfail" / "FAIL-1.json").write_text("{}")
            p = ps.build_payload(root, NOW)
            by = {s["slug"]: s for s in p["sessions"]}
            self.assertEqual(by["live-a"]["step"], "working")
            self.assertEqual(by["live-a"]["owner"], "AI")
            self.assertEqual(by["live-a"]["slot"], 1)
            self.assertEqual(by["wait-b"]["step"], "paused")
            self.assertEqual(by["wait-b"]["owner"], "DET")
            self.assertEqual({b["id"]: b["state"] for b in by["wait-b"]["blocked_by"]},
                             {"rowready": "ready", "rowrun": "running"})
            self.assertEqual([q["slug"] for q in p["queued_next"]], ["q-c"])
            self.assertEqual(p["queued_next"][0]["rank"], 9.0)
            c = p["compute"]["counts"]
            self.assertEqual((c["ready"], c["running"], c["dryrun-fail"]), (1, 1, 1))
            self.assertEqual(c["filed_24h"], 1)
            regs = {r["region"]: r for r in p["compute"]["regions"]}
            self.assertEqual(regs["q3"]["row"], "rowrun")
            self.assertEqual(regs["q0"]["state"], "free")


class StoppedRows(unittest.TestCase):
    def test_stopped_row_is_not_ready_and_returns_when_stop_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _fixture(root, {})
            lp = root / "launch.sh"
            lp.write_text('#!/bin/bash\nD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)\n'
                          'exec /x/filler_run15.sh --id rowstop --stop "$D/x.STOP"\n')
            for r, row in (("rowstop", {"stop_file": "$D/x.STOP", "launcher": {"path": str(lp)}}),
                           ("rowunknown", {"stop_file": "$OTHER/x.STOP", "launcher": {"path": str(lp)}})):
                (root / "ready" / f"{r}.json").write_text(json.dumps(row))
                (root / "dryrun" / r).mkdir()
                (root / "dryrun" / r / "PASS.json").write_text("{}")
            (root / "x.STOP").write_text("")
            c = ps.build_payload(root, NOW)["compute"]["counts"]
            self.assertEqual((c["ready"], c["stopped"]), (1, 1))
            (root / "x.STOP").unlink()
            c = ps.build_payload(root, NOW)["compute"]["counts"]
            self.assertEqual((c["ready"], c["stopped"]), (2, 0))


class Overview(unittest.TestCase):
    def test_classes_from_graph_and_rowflow(self):
        def node(h, tier, openn=3):
            return {"handoff": h, "state": "active", "open": openn, "priority_basis": {"tier": tier}}
        graph = {"nodes": [node("a.md", 2), node("a.md", 5), node("b.md", 5), node("c.md", 6),
                           node("d.md", 0), node("e.md", 2, 0)]}
        rows = {"r1": {"id": "r1", "state": "ready", "handoff": "handoffs/active/b.md"},
                "r2": {"id": "r2", "state": "dryrun-fail", "handoff": "handoffs/active/c.md"}}
        o = ps.classify_handoffs(graph, rows)
        cls = {h["handoff"]: h["class"] for h in o["handoffs"]}
        self.assertEqual(cls, {"a.md": "non-inference", "b.md": "readied-waiting", "c.md": "needs-ready",
                               "d.md": "needs-ready", "e.md": "done"})
        self.assertEqual(o["class_counts"], {"non-inference": 1, "readied-waiting": 1, "needs-ready": 2, "done": 1})
        self.assertEqual([h["id"] for h in o["handoffs"]][0], "active/a")
        self.assertFalse(ps.classify_handoffs(None, {})["present"])


class Wiring(unittest.TestCase):
    def test_panel_registered_with_route_probe_and_envelope(self):
        src = panels.source("pipeline")
        self.assertEqual(src.route, "/api/pipeline")
        self.assertEqual(src.health_route, "/api/pipeline/health")
        self.assertTrue(src.absence_means and src.warn_s and src.stale_s)
        self.assertNotIn("/pipeline", server.HTML_ROUTES)
        self.assertIn("/api/pipeline", server.API_ROUTES)
        self.assertIn("/api/pipeline/health", server.PANEL_HEALTH_ROUTES)

    def test_no_separate_page_or_registry_entry(self):
        reg = json.loads((Path(server.REPO) / "dashboard" / "registry.json").read_text())
        self.assertEqual([x for x in reg["dashboards"] if x["id"] == "pipeline"], [])
        self.assertFalse((Path(server.REPO) / "dashboard" / "static" / "pipeline.html").exists())

    def test_region_cpus_and_phase(self):
        self.assertEqual(ps.region_cpus("q1")[:2], [24, 25])
        self.assertIn(120, ps.region_cpus("q1"))
        self.assertEqual(ps.region_cpus("gpu-quiet"), list(range(184, 192)))

    def test_page_marks_det_and_ai_with_legend(self):
        html = (Path(server.REPO) / "dashboard" / "static" / "handoffs.html").read_text()
        for needle in ("handoff_detail", "class_counts", "DET", "AI-powered", "deterministic", "setInterval(load,30000)", "pipeline-sec", "/api/pipeline"):
            self.assertIn(needle, html)
        self.assertGreaterEqual(html.count("o:'AI'"), 3)
        self.assertGreaterEqual(html.count("o:'DET'"), 8)

    def test_live_payload_shape(self):
        p = server.pipeline_payload()
        self.assertIn("_freshness", p)
        self.assertIn("overview", p)
        status, body = server.pipeline_health()
        self.assertIn(status, (200, 503))
        self.assertEqual(body["panel"], "pipeline")


if __name__ == "__main__":
    unittest.main()
