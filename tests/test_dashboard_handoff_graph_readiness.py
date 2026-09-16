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


_PACK_HARNESS = r"""
const fs = require("fs");
globalThis.document = { createElementNS:()=>({}), createElement:()=>({}) };
const spec = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8") + "\nglobalThis.__pb = packBands;");
const items = spec.items.map(it => ({n:{id:it.id, domain:it.domain}, r:it.r}));
globalThis.__pb(items, spec.colX, spec.half, spec.opts);
process.stdout.write(JSON.stringify(items.map(it => ({id:it.n.id, domain:it.n.domain,
  r:it.r, x:it.x, y:it.y}))));
"""

_OPTS = {"W": 1200, "BAND": 158, "PAD": 26, "SEP": 14, "RELAX": 400}


def _page_jitter() -> float:
    m = re.search(r"JITTER=([0-9.]+)", _graph_js())
    assert m, "loadGraph no longer declares JITTER"
    return float(m.group(1))


def _band_spec(jitter: float) -> dict:
    """A deterministic three-band population shaped like the live graph: one dense band,
    one mid, one sparse, radii from the page's own open-count formula."""
    pops = {"inference-research": 58, "routing-and-optimization": 30, "research-evaluation": 9}
    items = []
    for d, n in pops.items():
        for k in range(n):
            open_ = (k * 7) % 23
            items.append({"id": f"{d[:3].upper()}-{k:02d}", "domain": d,
                          "r": max(5, min(15, 3.4 + 1.9 * open_ ** 0.5))})
    total, inner, minw = len(items), 1200 - 2 * 26, 118
    slack = inner - minw * len(pops)
    col_x, half, x0 = {}, {}, 26
    for d, n in pops.items():
        w = minw + slack * n / total
        col_x[d], half[d] = x0 + w / 2, w / 2
        x0 += w
    return {"items": items, "colX": col_x, "half": half, "opts": {**_OPTS, "JITTER": jitter}}


def _aligned(nodes, key) -> float:
    """Fraction of nodes sharing a coordinate (±0.5px) with a NEAR same-band node (centres
    within 60px, ~1.5 cells): the implied local rows/columns that read as a lattice. Far pairs
    are excluded — in a 58-node band two distant nodes sharing a y by chance draw no line."""
    hit = 0
    for a in nodes:
        hit += any(b is not a and b["domain"] == a["domain"] and abs(a[key] - b[key]) < 0.5
                   and ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5 < 60
                   for b in nodes)
    return hit / len(nodes)


@unittest.skipUnless(shutil.which("node"), "node not available")
class LayoutTests(unittest.TestCase):
    """Box "Graph layout reads as a lattice". A human judges the look; the proxy asserted here is
    ALIGNMENT (nodes sharing an exact row/column) must be rare while the separation that made the
    grid seed necessary (zero halo overlaps, the SEP gap, domains inside their own band) holds."""

    def _pack(self, jitter: float) -> list:
        with tempfile.TemporaryDirectory() as d:
            sp, jp, hp = (Path(d) / "s.json", Path(d) / "graph.js", Path(d) / "h.js")
            sp.write_text(json.dumps(_band_spec(jitter)))
            jp.write_text(_graph_js())
            hp.write_text(_PACK_HARNESS)
            res = subprocess.run(["node", str(hp), str(sp), str(jp)],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_page_layout_is_not_a_lattice(self):
        nodes = self._pack(_page_jitter())
        self.assertLess(_aligned(nodes, "y"), 0.2)
        self.assertLess(_aligned(nodes, "x"), 0.2)

    def test_mutation_zero_jitter_is_a_lattice(self):
        # Proves the alignment metric detects the defect the box describes. The unjittered seed
        # is staggered, so its columns repeat only every second row (outside the 60px window);
        # its rows are the tell.
        nodes = self._pack(0.0)
        self.assertGreater(_aligned(nodes, "y"), 0.8)

    def test_separation_survives_the_jitter(self):
        nodes = self._pack(_page_jitter())
        sep = _OPTS["SEP"]
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                gap = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5 - a["r"] - b["r"]
                self.assertGreaterEqual(gap, sep - 0.5, f"{a['id']} / {b['id']} crowd")
            self.assertGreaterEqual(a["y"], _OPTS["BAND"])
            self.assertTrue(_OPTS["PAD"] <= a["x"] <= _OPTS["W"] - _OPTS["PAD"])

    def test_domains_stay_in_their_own_band(self):
        spec = _band_spec(_page_jitter())
        for n in self._pack(_page_jitter()):
            cx, h = spec["colX"][n["domain"]], spec["half"][n["domain"]]
            self.assertLessEqual(abs(n["x"] - cx), h + n["r"], f"{n['id']} left its band")

    def test_layout_is_deterministic(self):
        # Per-id hash, not Math.random: the 2-minute refresh must not reshuffle the picture.
        self.assertEqual(self._pack(_page_jitter()), self._pack(_page_jitter()))
        self.assertNotIn("Math.random", _graph_js())


if __name__ == "__main__":
    unittest.main()
