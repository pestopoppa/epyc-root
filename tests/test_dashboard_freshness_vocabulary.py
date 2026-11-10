"""One freshness vocabulary at the hub/orchestrator seam.

The orchestrator envelope spells the four states fresh/aging/stale/dead; the hub
spells them fresh/aging/stale/missing (AK6: fresh/warn/stale/ABSENT). The shim in
dashboard/freshness.py is the single mapping; /nav.js carries the same table.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import freshness, server  # noqa: E402

ORCH_SPELLINGS = {"fresh": "fresh", "aging": "aging", "stale": "stale", "dead": "missing"}


def test_orchestrator_vocabulary_maps_onto_hub_classes():
    for theirs, ours in ORCH_SPELLINGS.items():
        assert freshness.canonical_class(theirs) == ours
    assert freshness.canonical_class("warn") == "aging"
    assert freshness.canonical_class("ABSENT") == "missing"
    assert freshness.canonical_class(" Dead ") == "missing"


def test_every_hub_class_is_a_fixed_point():
    for c in freshness.CLASSES:
        assert freshness.canonical_class(c) == c


def test_unmapped_values_are_not_coerced():
    for v in ("unknown", "", None, 3, "divergent"):
        assert freshness.canonical_class(v) is None


def test_aliases_only_target_hub_classes():
    assert set(freshness.ALIASES.values()) <= set(freshness.CLASSES)
    assert not set(freshness.ALIASES) & set(freshness.CLASSES)


def test_nav_asset_inlines_the_same_table():
    body = server.nav_asset().decode()
    m = re.search(r"window\.__EPYC_FRESH_ALIASES = (\{.*?\});", body)
    assert m, "alias table missing from /nav.js"
    table = json.loads(m.group(1))
    assert table == {**{c: c for c in freshness.CLASSES}, **freshness.ALIASES}
    assert "window.epycFreshClass" in body


def test_pages_reading_orchestrator_envelopes_use_the_shim():
    for page in ("machine.html", "autopilot.html"):
        text = (REPO / "dashboard" / "static" / page).read_text(encoding="utf-8")
        assert "epycFreshClass" in text, page
