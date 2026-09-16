#!/usr/bin/env python3
"""The :8100 backlog graph must RENDER the producer's `readiness`, never derive it.

RTG-46 (`handoffs/active/handoff-index-and-backlog-graph.md`). `index_graph.v2` (commit
`457abd40`) stamps `readiness` in {ready, blocked, no_open} and `blocked_by` on every node, but
`dashboard/static/handoffs.html` never read either field, so a node gated on an open dep target
looked identical to a dispatchable one — and a dep cycle (INF-06 <-> INF-64, 2026-09-07) could
only be found by running the computation by hand.

Plane rule (`dashboard/README.md`): the data contract stays with its producer. So the page may
READ `readiness` / `readiness_counts` / `readiness_values`, and must not recompute them.

Two layers, same split as ``test_dashboard_static_js.py``:

* structural checks, pure Python, always run;
* an execution check that runs the page's real ``loadGraph`` under node against a tiny DOM stub,
  paired with a MUTATION (the same graph minus `readiness`, i.e. a v1 sidecar) proving that the
  hatch comes from the field and not from something else in the fixture. Skips without node.

Run: ``python3 -m unittest tests.test_dashboard_handoff_graph_readiness``
"""
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PAGE = _REPO / "dashboard" / "static" / "handoffs.html"


def _producer():
    spec = importlib.util.spec_from_file_location(
        "index_state", _REPO / "scripts" / "handoffs" / "index_state.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _graph_js() -> str:
    html = _PAGE.read_text(encoding="utf-8")
    start = html.index("const IDX_COLOR")
    fn = html.index("async function loadGraph(")
    end = html.index("\n}\n", fn) + 3
    return html[start:end]


class StructuralReadinessTests(unittest.TestCase):
    def test_page_reads_producer_readiness_fields(self):
        js = _graph_js()
        for field in ("n.readiness", "n.blocked_by", "g.readiness_counts", "g.readiness_values"):
            self.assertIn(field, js, f"graph renderer never reads {field}")

    def test_every_producer_readiness_value_has_a_legend_style(self):
        counts = _producer().derive_readiness([], [])
        js = _graph_js()
        block = re.search(r"const READINESS_STYLE = \{(.*?)\n\};", js, re.S)
        self.assertIsNotNone(block, "READINESS_STYLE table missing")
        styled = set(re.findall(r"^\s*(\w+):\s*\{", block.group(1), re.M))
        self.assertEqual(styled, set(counts),
                         "page legend and producer readiness values have drifted")

    def test_page_does_not_derive_readiness(self):
        js = _graph_js()
        # Assigning either derived field in the page would be a second grading rule.
        self.assertNotRegex(js, r"(?<!dataset)\.readiness\s*=[^=]")
        self.assertNotRegex(js, r"\.blocked_by\s*=[^=]")


_HARNESS = r"""
const fs = require("fs");
class El {
  constructor(tag){ this.tag=tag; this.attrs={}; this.children=[]; this.dataset={};
    this.style={}; this.innerHTML=""; this.textContent=""; this.className="";
    this.classList={ toggle(){}, remove(){}, add(){} }; }
  setAttribute(k,v){ this.attrs[k]=String(v); }
  getAttribute(k){ return this.attrs[k]; }
  appendChild(c){ this.children.push(c); return c; }
  append(...cs){ cs.forEach(c=>this.children.push(c)); }
  removeChild(c){ this.children=this.children.filter(x=>x!==c); }
  get firstChild(){ return this.children[0]; }
  addEventListener(){}
  getBoundingClientRect(){ return {left:0,top:0,width:1200}; }
}
const byId = {"#graph-svg": new El("svg"), "#graph-tip": new El("div"),
              "#graph-note": new El("p"), "#graph-legend": new El("div")};
globalThis.document = { createElementNS:(ns,t)=>new El(t), createElement:t=>new El(t) };
globalThis.$ = s => byId[s];
globalThis.setBadge = ()=>{};
globalThis.installZoom = ()=>{};
globalThis.loadDetail = ()=>{};
const graph = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
globalThis.getJSON = async ()=>graph;
eval(fs.readFileSync(process.argv[3], "utf8") + "\nglobalThis.__lg = loadGraph;");
globalThis.__lg().then(()=>{
  const out = {nodes:{}, legend:[]};
  for (const g of byId["#graph-svg"].children) for (const c of g.children) {
    if (c.tag !== "g") continue;
    const discs = c.children;
    out.nodes[JSON.stringify([discs[0].attrs.cx, discs[0].attrs.cy])] = {
      readiness: c.attrs["data-readiness"],
      hatched: discs.some(d => d.attrs.fill === "url(#gate-hatch)"),
      opacity: discs[0].attrs["fill-opacity"] || null };
  }
  out.legend = byId["#graph-legend"].children.map(s => s.innerHTML || s.textContent);
  process.stdout.write(JSON.stringify(out));
}).catch(e => { console.error(e); process.exit(1); });
"""


def _node(tag: str, domain: str, open_: int) -> dict:
    return {"id": tag, "domain": domain, "track": tag, "open": open_, "closed": 0,
            "blocked": 0, "state": "active", "age_days": 3, "last_advanced": None,
            "handoff": f"{tag}.md", "next_action": ""}


@unittest.skipUnless(shutil.which("node"), "node not available")
class ExecutedReadinessTests(unittest.TestCase):
    def _run(self, graph: dict) -> dict:
        with tempfile.TemporaryDirectory() as d:
            gp, jp, hp = (Path(d) / "g.json", Path(d) / "graph.js", Path(d) / "h.js")
            gp.write_text(json.dumps(graph))
            jp.write_text(_graph_js())
            hp.write_text(_HARNESS)
            res = subprocess.run(["node", str(hp), str(gp), str(jp)],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        out["nodes"] = list(out["nodes"].values())
        return out

    def _graph(self) -> dict:
        nodes = [_node("A-1", "inference-research", 2),       # gated on B-1
                 _node("B-1", "inference-research", 1),       # ready
                 _node("C-1", "research-evaluation", 0)]      # no_open
        edges = [{"from": "A-1", "to": "B-1", "kind": "dep"}]
        counts = _producer().derive_readiness(nodes, edges)
        return {"schema": "index_graph.v2", "nodes": nodes, "edges": edges,
                "readiness_counts": counts, "readiness_values": {}}

    def test_blocked_is_hatched_ready_solid_no_open_faded(self):
        out = self._run(self._graph())
        by = {n["readiness"]: n for n in out["nodes"]}
        self.assertEqual(set(by), {"ready", "blocked", "no_open"})
        self.assertTrue(by["blocked"]["hatched"])
        self.assertFalse(by["ready"]["hatched"])
        self.assertIsNone(by["ready"]["opacity"])
        self.assertEqual(by["no_open"]["opacity"], "0.3")
        legend = " ".join(out["legend"])
        self.assertIn("blocked", legend)
        self.assertIn("(1)", legend)          # counts are the producer's tally

    def test_mutation_v1_graph_renders_no_hatch_and_says_why(self):
        g = self._graph()
        g["schema"] = "index_graph.v1"
        for n in g["nodes"]:
            n.pop("readiness"); n.pop("blocked_by")
        g.pop("readiness_counts")
        out = self._run(g)
        self.assertFalse(any(n["hatched"] for n in out["nodes"]))
        self.assertIn("needs index_graph.v2", " ".join(out["legend"]))


if __name__ == "__main__":
    unittest.main()
