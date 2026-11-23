"""Per-surface accumulator card on /loop (AKU-18): contract reader, ESTIMATE rule, freshness, placement."""
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import accumulator_surfaces as A  # noqa: E402
from dashboard import panels  # noqa: E402
from dashboard import server as S  # noqa: E402

PAGE = (REPO / "dashboard" / "static" / "loop.html").read_text(encoding="utf-8")
EST = "ESTIMATE (product of solo keep effects, not a measurement of the bundle)"


def surface(**over):
    s = {"surface": "cpu", "n_keeps": 3, "measurement_validity": "stale_external_tip_advance",
         "figure": {"kind": "estimate", "pct": 3.3, "label": EST}, "floor_pct": None,
         "keeps_since_serving_gate": 2, "every_keeps": 8, "fire_multiple": 2.5,
         "fire": {"decision": "cannot_decide", "trigger": None, "reason": "no calibrated serving floor"},
         "fold_estimates": [{"recipe": "r.h1", "n_keeps": 3, "pct": 13.5, "label": EST,
                             "provisional_keeps": 3}]}
    s.update(over)
    return s


class SurfaceCardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "accumulator_surfaces.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, surfaces, generated="2026-11-23T00:00:00Z", schema=A.SCHEMA):
        self.path.write_text(json.dumps({"schema": schema, "generated_at": generated,
                                         "surfaces": surfaces}))

    def test_present_record_is_fresh_and_keeps_surfaces(self):
        now = time.time()
        self.write([surface(), surface(surface="gpu")],
                   generated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 60)))
        d = S.accumulator_surfaces_payload(self.path, now=now)
        self.assertTrue(d["present"])
        self.assertEqual([s["surface"] for s in d["surfaces"]], ["cpu", "gpu"])
        self.assertEqual(d["_freshness"]["staleness_class"], "fresh")
        self.assertEqual(panels.panel_verdict(d["_freshness"])[0], "ok")

    def test_old_record_ages_to_stale_not_green(self):
        now = time.time()
        self.write([surface()], generated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 10 * 86400)))
        d = S.accumulator_surfaces_payload(self.path, now=now)
        self.assertEqual(d["_freshness"]["staleness_class"], "stale")
        self.assertNotEqual(panels.panel_verdict(d["_freshness"])[0], "ok")

    def test_missing_file_reads_absent_with_meaning(self):
        d = S.accumulator_surfaces_payload(self.path)
        self.assertFalse(d["present"])
        self.assertEqual(d["_freshness"]["reporting"], "absent")
        self.assertIn("absence_means", d["_freshness"])
        self.assertEqual(panels.panel_verdict(d["_freshness"])[0], "absent")

    def test_estimate_without_label_is_refused_never_relabelled(self):
        for bad in (surface(figure={"kind": "estimate", "pct": 3.3, "label": "measured"}),
                    surface(fold_estimates=[{"recipe": "r", "label": "MEASURED"}])):
            self.write([bad])
            d = A.build(self.path)
            self.assertFalse(d["present"])
            self.assertIn("ESTIMATE", d["error"])

    def test_unknown_schema_and_decision_refused(self):
        self.write([surface()], schema="other")
        self.assertFalse(A.build(self.path)["present"])
        self.write([surface(fire={"decision": "maybe"})])
        self.assertFalse(A.build(self.path)["present"])

    def test_registered_probed_and_placed_beside_akflow(self):
        src = panels.source("accumulator_surfaces")
        self.assertEqual((src.route, src.health_route),
                         ("/api/accumulator_surfaces", "/api/accumulator_surfaces/health"))
        self.assertIn("/api/accumulator_surfaces", S.API_ROUTES)
        self.assertIn("/api/accumulator_surfaces/health", S.PANEL_HEALTH_ROUTES)
        code, body = S.accumulator_surfaces_health()
        self.assertIn(code, (200, 503))
        sec = PAGE[PAGE.index('<section id="akflow-sec">'):]
        sec = sec[:sec.index("</section>")]
        self.assertIn('id="aks-cards"', sec)
        self.assertLess(sec.index('id="akflow-items"'), sec.index('id="aks-cards"'))

    def test_page_renders_estimate_label_and_adds_no_section_before_trajectory(self):
        self.assertIn("aksCard", PAGE)
        self.assertIn("/api/accumulator_surfaces", PAGE)
        body = PAGE[PAGE.index("<main>"):]
        self.assertEqual(re.findall(r'<section id="([a-z-]+)"', body)[:2],
                         ["akflow-sec", "sec-trajectory"])


if __name__ == "__main__":
    unittest.main()
