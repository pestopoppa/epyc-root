"""AK parallel-loop flow panel: data contract (akloop/flow_status.py), hub wiring, and a Node render smoke."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "coordination" / "akloop"))

import flow_status as FS  # noqa: E402
from dashboard import panels, server  # noqa: E402
from tests.test_dashboard_machine_provenance import _extract_function  # noqa: E402

NOW = time.time()


def _iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _fixture(root: Path):
    flags, spool, lin = root / "flags", root / "spool", root / "lineage"
    for d in ("ready", "grants", "filing-done", "dryrun"):
        (flags / d).mkdir(parents=True)
    spool.mkdir()
    (spool / "cand-h1-abc.json").write_text(json.dumps({
        "id": "cand-h1-abc", "hypothesis_id": "h1", "base_sha": "a" * 40, "patch_sha": "b" * 40,
        "lane": "lane0", "emitted_at": _iso(NOW - 600)}))

    def row(rid, owner="autokernel", result=None):
        m = {"id": rid, "owner": owner, "published_at": _iso(NOW - 3000)}
        if result is not None:
            rp = root / f"{rid}.RESULT.json"
            rp.write_text(json.dumps(result))
            m["result_path"] = str(rp)
        (flags / "ready" / f"{rid}.json").write_text(json.dumps(m))

    row("akc-h1-build-20261121")                                    # running chain build
    (flags / "grants" / "akc-h1-build-20261121.grant").write_text("{}")
    row("akc-h1-oracle-kld-20261121")                               # queued
    row("akc-h1-rbdeadbee-ab-timing-20261121",                       # filed rebase timing row
        result={"row": "x", "answer": "FAIL", "polar": "FAIL"})
    (flags / "grants" / "akc-h1-rbdeadbee-ab-timing-20261121.ended").write_text("rc=0")
    (flags / "filing-done" / "akc-h1-rbdeadbee-ab-timing-20261121.verdict.json").write_text(json.dumps(
        {"answer": "FAIL timing", "row_verdict": "fail", "filed_at": _iso(NOW - 100)}))
    (flags / "filing-done" / "akc-h1-rbdeadbee-ab-timing-20261121.FILED").write_text("")
    row("akc-h1-op-perf-20261121")                                  # queued op-perf screen (RSL-R3)
    row("someone-else-build-20261121", owner="pipeline-mgmt")       # not AK: ignored
    row("ak-misc-thing-20261121")                                   # AK, no stage
    (lin / "20261121T000000Z-composite-c17-fold-x").mkdir(parents=True)
    return flags, spool, lin


def _detect(owner, flags=None, now=None):
    return {"as_of": _iso(now + 3600), "counts": {"hold-hit": 1},
            "events": [{"kind": "hold-hit", "subject": "autokernel-rebuild", "summary": "hold stops 3 boxes"}]}


class FlowContract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.flags, self.spool, self.lin = _fixture(self.tmp)
        self.d = FS.build(str(self.flags), str(self.spool), str(self.lin), now=NOW, detect=_detect, holds=os.devnull, inbox=str(self.flags / "no-inbox"), census=str(self.flags / "no-census.json"), path_gates=str(self.flags / "no-gates.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_schema_and_every_node(self):
        self.assertEqual(self.d["schema"], "epyc.akloop.flow.v1")
        self.assertEqual(set(self.d["nodes"]), {n[0] for n in FS.NODES})
        for a, b in self.d["edges"]:
            self.assertIn(a, self.d["nodes"]); self.assertIn(b, self.d["nodes"])
        owners = {k: v["owner"] for k, v in self.d["nodes"].items()}
        self.assertEqual({k for k, v in owners.items() if v == "AI"}, {"planner", "critic", "author"})

    def test_llm_nodes_are_null_not_zero(self):
        for nid in ("planner", "critic"):
            self.assertIsNone(self.d["nodes"][nid]["count"])
            self.assertEqual(self.d["nodes"][nid]["state"], "uninstrumented")
        self.assertIn("lane0", self.d["nodes"]["author"]["note"])

    def test_stage_states(self):
        n = self.d["nodes"]
        self.assertEqual((n["build"]["in_flight"], n["build"]["state"]), (1, "active"))
        self.assertEqual(n["oracle-kld"]["queued"], 1)
        self.assertEqual((n["op-perf"]["queued"], n["op-perf"]["count"]), (1, 1))   # a chain op-perf row has its own node
        self.assertEqual(n["ab-timing"]["done"], 1)
        self.assertEqual(n["rebase"]["count"], 1)
        self.assertEqual(n["gate_eval"]["items"][0]["state"], "fail")
        self.assertEqual(n["file"]["done"], 1)
        self.assertEqual(n["failclass"]["items"][0]["state"], "candidate")
        self.assertEqual(n["lineage"]["count"], 1)
        self.assertEqual(n["candidate"]["count"], 1)
        self.assertEqual(n["decisions"]["queued"], 1)

    def test_glance(self):
        g = self.d["glance"]
        self.assertEqual((g["running_n"], g["queued_n"], g["chain_rows"]), (1, 3, 4))
        self.assertEqual(g["other_rows"]["queued"], 1)          # ak-misc, never the pipeline-mgmt row
        self.assertEqual(g["decisions_n"], 1)

    def test_op_perf_sits_between_oracle_and_timing(self):
        e = [tuple(x) for x in self.d["edges"]]
        self.assertIn(("oracle-kld", "op-perf"), e)
        self.assertIn(("op-perf", "ab-timing"), e)
        self.assertNotIn(("oracle-kld", "ab-timing"), e)
        self.assertEqual(FS.stage_of("ak-x-op-perf-20261121")[0], "op-perf")

    def test_serving_screen_rows_have_a_node_and_never_reach_fold(self):
        self.assertEqual(FS.stage_of("akc-k1-serving-screen-20261124"), ("serving-screen", True, False))
        self.assertEqual(FS.stage_of("ak-k1-serving-screen-20261124")[0], "serving-screen")
        self.assertIn("serving-screen", self.d["nodes"])
        self.assertIn(("candidate", "serving-screen"), [tuple(e) for e in self.d["edges"]])
        self.assertFalse([e for e in self.d["edges"] if e[0] == "serving-screen"])   # nothing consumes it: no fold input

    def test_path_gates_absent_is_unknown_never_gated(self):
        pg = self.d["path_gates"]
        self.assertFalse(pg["present"])
        self.assertEqual(pg["paths"], [])
        self.assertIn("unknown", self.d["nodes"]["op-perf"]["note"])

    def test_decisions_as_of_does_not_date_the_loop(self):
        self.assertLess(FS._epoch(self.d["last_event"]), NOW + 1800)

    def test_detector_failure_is_stated(self):
        def boom(*a, **k):
            raise RuntimeError("x")
        d = FS.build(str(self.flags), str(self.spool), str(self.lin), now=NOW, detect=boom, holds=os.devnull, inbox=str(self.flags / "no-inbox"), census=str(self.flags / "no-census.json"), path_gates=str(self.flags / "no-gates.json"))
        self.assertFalse(d["decisions"]["present"])
        self.assertIsNone(d["nodes"]["decisions"]["count"])


class HubWiring(unittest.TestCase):
    def test_registered_panel_route_and_probe(self):
        src = panels.PANELS["akflow"]
        self.assertEqual((src.route, src.health_route), ("/api/akflow", "/api/akflow/health"))
        self.assertIs(server.API_ROUTES["/api/akflow"], server.akflow_payload)
        self.assertTrue(callable(server.akflow_payload))

    def test_absent_flags_reads_absent(self):
        orig = server._akflow_module

        class M:
            @staticmethod
            def build():
                return {"schema": FS.SCHEMA, "sources": {"rowflow": {"present": False}}, "nodes": {}}
        server._akflow_module = lambda: M
        try:
            d = server.akflow_payload(force=True)
            self.assertFalse(d["present"])
            self.assertEqual(server.akflow_health()[0], 503)
        finally:
            server._akflow_module = orig
            server._akflow_cache = None


@unittest.skipUnless(shutil.which("node"), "node not available")
class RenderSmoke(unittest.TestCase):
    def test_render_fixture(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            d = FS.build(*map(str, _fixture(tmp)), now=NOW, detect=_detect, holds=os.devnull, inbox=os.path.join(str(tmp), "ib"), census=os.path.join(str(tmp), "c.json"), path_gates=os.path.join(str(tmp), "pg.json"))
        finally:
            shutil.rmtree(tmp)
        page = (REPO / "dashboard/static/loop.html").read_text()
        self.assertIn('id="akflow-sec"', page)
        start = page.index("const AKF_POS="); end = page.index(";", page.index("decisions:[", start)) + 1
        js = page[start:end] + "\n" + page[page.index("const AKF_DASH="):page.index("\n", page.index("const AKF_DASH="))] + "\n" + \
            "".join(_extract_function(page, f) + "\n" for f in
                    ("akfEsc", "akfAge", "akfGlance", "akfPathGates", "akfClip", "akfSvg", "akfItems"))
        d["path_gates"] = {"present": True, "ungated_n": 1, "paths": [
            {"key": "a3b|cpu", "device": "cpu", "timing": "ungated", "quality": "quality-ungated", "op_perf": "floored",
             "status": "ungated+quality-ungated", "gaps": ["ungated", "quality-ungated"]}]}
        js += f"const d={json.dumps(d)};\n"
        js += ("process.stdout.write(JSON.stringify({g:akfGlance(d),s:akfSvg(d,'build'),i:akfItems(d,'build'),"
               "none:akfItems(d,null),abs:akfGlance({present:false,error:'gone'}),nopg:akfPathGates({present:false,error:'no report'})}));")
        out = json.loads(subprocess.run(["node", "-e", js], check=True, capture_output=True, text=True,
                                        timeout=30).stdout)
        self.assertEqual(out["s"].count('class="node'), len(FS.NODES))
        self.assertEqual(out["s"].count('marker-end'), len(FS.EDGES))
        self.assertIn("not instrumented", out["s"])
        self.assertIn('class="ai"', out["s"]); self.assertIn('class="det"', out["s"])
        self.assertIn("akc-h1-build-20261121", out["i"])
        self.assertIn("Decisions needed (1)", out["g"])
        self.assertIn("quality-ungated", out["g"]); self.assertIn("Per-path gates", out["g"])
        self.assertIn("ABSENT", out["abs"])
        self.assertIn("UNKNOWN", out["nopg"])
        self.assertIn("Click a node", out["none"])
        art = os.environ.get("AKFLOW_RENDER_OUT")
        if art:
            Path(art).write_text("<!doctype html><meta charset=utf-8><body style='background:#0d1117;color:#c9d1d9'>"
                                 + out["g"] + out["s"] + out["i"] + "</body>")


class PathGates(unittest.TestCase):
    REP = {"27b-q8_0|mi210": {"status": "live", "device": "mi210", "timing": "cell", "quality": "gated", "op_perf": "floored"},
           "a3b-q8_0|cpu": {"status": "live", "device": "cpu", "timing": "ungated", "quality": "quality-ungated",
                            "op_perf": "ungated"},
           "x|cpu": {"status": "planned", "device": "cpu", "timing": "cell", "quality": "quality-ungated", "op_perf": "floored"},
           "y|cpu": {"status": "live", "device": "cpu", "timing": None, "quality": "gated", "op_perf": "floored"}}

    def test_per_path_status_and_node_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pg.json"
            p.write_text(json.dumps({"at": 1.0, "report": self.REP}))
            d = FS.build(str(Path(tmp) / "f"), str(Path(tmp) / "s"), str(Path(tmp) / "l"), now=NOW, detect=_detect,
                         holds=os.devnull, inbox=str(Path(tmp) / "ib"), census=str(Path(tmp) / "c.json"), path_gates=str(p))
        by = {x["key"]: x for x in d["path_gates"]["paths"]}
        self.assertEqual(by["27b-q8_0|mi210"]["status"], "gated")
        self.assertEqual(by["a3b-q8_0|cpu"]["status"], "ungated+quality-ungated+op-perf-ungated")
        self.assertEqual(by["x|cpu"]["status"], "quality-ungated")
        self.assertEqual(by["y|cpu"]["gaps"], ["timing-unknown"])      # a null cell is unknown, not ok
        self.assertEqual(d["path_gates"]["ungated_n"], 3)
        self.assertEqual([i["id"] for i in d["nodes"]["op-perf"]["items"]], sorted(self.REP))
        self.assertEqual(d["nodes"]["op-perf"]["count"], 0)             # path rows are not op-perf rows

    def test_only_floored_counts_as_op_perf_gated(self):
        """N2: a grid with no floor decides nothing, so it is a gap; the legacy bare `grid` is a gap too."""
        base = {"status": "live", "device": "mi210", "timing": "cell", "quality": "gated"}
        got = {v: FS.path_gate_status({**base, "op_perf": v}) for v in
               ("floored", "grid-no-floor", "no-lane", "grid", "ungated", None, "weird")}
        self.assertEqual((got["floored"]["status"], got["floored"]["gaps"]), ("gated", []))
        self.assertEqual(got["grid-no-floor"]["status"], "op-perf-no-floor")
        self.assertEqual(got["no-lane"]["status"], "op-perf-no-lane")
        self.assertEqual(got["grid"]["status"], "op-perf-floor-unproven")     # old value: never counted as gated
        self.assertEqual(got["ungated"]["status"], "op-perf-ungated")
        self.assertEqual(got[None]["gaps"], ["op-perf-unknown"])
        self.assertEqual(got["weird"]["gaps"], ["op-perf-unknown"])
        for v in ("grid-no-floor", "no-lane", "grid"):
            self.assertNotEqual(got[v]["status"], "gated")
            self.assertEqual(got[v]["op_perf"], v)

    def test_path_gates_counts_unfloored_paths_as_gaps(self):
        rep = {"a|mi210": {"status": "live", "device": "mi210", "timing": "cell", "quality": "gated", "op_perf": "grid-no-floor"},
               "b|cpu": {"status": "live", "device": "cpu", "timing": "cell", "quality": "gated", "op_perf": "no-lane"},
               "c|cpu": {"status": "live", "device": "cpu", "timing": "cell", "quality": "gated", "op_perf": "floored"}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pg.json"
            p.write_text(json.dumps({"at": 1.0, "report": rep, "registry": {"status": "registry-snapshot-failed"}}))
            d = FS.build(str(Path(tmp) / "f"), str(Path(tmp) / "s"), str(Path(tmp) / "l"), now=NOW, detect=_detect,
                         holds=os.devnull, inbox=str(Path(tmp) / "ib"), census=str(Path(tmp) / "c.json"), path_gates=str(p))
        by = {x["key"]: x["status"] for x in d["path_gates"]["paths"]}
        self.assertEqual(by, {"a|mi210": "op-perf-no-floor", "b|cpu": "op-perf-no-lane", "c|cpu": "gated"})
        self.assertEqual(d["path_gates"]["ungated_n"], 2)
        self.assertIn("registry-snapshot-failed", d["nodes"]["op-perf"]["note"])   # N9: shown, not silent

    def test_errored_or_unreadable_report_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pg.json"
            p.write_text(json.dumps({"at": 1.0, "error": "RuntimeError: registry unreadable"}))
            self.assertIn("registry unreadable", FS.read_path_gates(str(p))["error"])
            self.assertFalse(FS.read_path_gates(str(p))["present"])
            p.write_text("{not json")
            self.assertFalse(FS.read_path_gates(str(p))["present"])
            p.write_text(json.dumps({"report": {}}))
            self.assertFalse(FS.read_path_gates(str(p))["present"])


class HoldAndCensus(unittest.TestCase):
    def test_held_lanes_inbox_and_census(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "holds.yaml").write_text("holds:\n- id: akagg\n  sessions:\n  - akagg\n  scope: loop-launch\n  launch_only: true\n  since: '2026-11-19T02:12:51Z'\n")
            (t / "ib").mkdir(); (t / "ib" / "01-x.md").write_text("x")
            (t / "c.json").write_text(json.dumps({"surfaces": [{"id": "a", "saving_ms_per_step": 2.0}, {"id": "b", "stale": True, "saving_ms_per_step": 1.0}], "applied": ["s1"]}))
            d = FS.build(str(t / "f"), str(t / "s"), str(t / "l"), now=NOW, detect=_detect,
                         holds=str(t / "holds.yaml"), inbox=str(t / "ib"), census=str(t / "c.json"), path_gates=str(t / "pg.json"))
            self.assertEqual(d["nodes"]["planner"]["state"], "held")
            self.assertEqual(d["glance"]["hold"]["id"], "akagg")
            self.assertEqual(d["nodes"]["inbox"]["done"], 1)
            self.assertEqual(d["nodes"]["census"]["count"], 2)
            self.assertIn("1 stale", d["nodes"]["census"]["note"])
            self.assertIn(["file", "census"], d["edges"])
            # an unreadable holds file fails closed: lanes read held, never "free"
            d2 = FS.build(str(t / "f"), str(t / "s"), str(t / "l"), now=NOW, detect=_detect,
                          holds=str(t / "missing.yaml"), inbox=str(t / "ib"), census=str(t / "c.json"), path_gates=str(t / "pg.json"))
            self.assertEqual(d2["nodes"]["planner"]["state"], "held")


if __name__ == "__main__":
    unittest.main()
