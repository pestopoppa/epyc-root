#!/usr/bin/env python3
"""tests/test_dashboard_nav.py — the dashboard directory and the ONE shared nav.

RTG-47 Phase 0 (``handoffs/active/dashboard-architecture-restructure.md``). The
defect this suite locks down is *drift*, not a crash: navigation was per-page
hand-rolled, the five pages were written at different times, and the link matrix
grew holes — reaching AutoKernel meant routing through the handoff board, and
cross-server URLs were re-derived ad hoc in three places. Hand-copied navigation
cannot be tested by looking at any one page, because every page is individually
self-consistent; it can only be tested against a SINGLE SOURCE OF TRUTH.

So the checks here are all about the seam:

1. ``dashboard/registry.json`` parses and is well-formed (ids unique, ports ints,
   paths absolute).
2. Page ↔ registry, BOTH DIRECTIONS. A hub page missing from the registry is
   unreachable from every nav; a registry row with no page is a nav link to a 404.
   Checking one direction is how half a drift survives.
3. Every hub page actually mounts the shared nav (``id="epyc-nav"`` +
   ``src="/nav.js"``) — adoption is what makes the registry load-bearing.
4. The RETIRED per-page idioms are gone: no ``id="autopilot-link"``, no
   hand-built ``:8000/dashboard`` link inside a ``<nav>``.
5. The ``/nav.js`` asset the hub serves really carries the registry.

NO SERVER IS STARTED and NO NETWORK IS USED: the asset builder and the registry
reader are called as plain functions. ``dashboards_payload()`` — which probes
127.0.0.1 — is deliberately NOT exercised here; its contract is the panel
registry's, and it is covered by the panel suites.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import panels, server  # noqa: E402

REGISTRY_PATH = REPO / "dashboard" / "registry.json"
NAV_JS_PATH = REPO / "dashboard" / "static" / "nav.js"

#: Every entry field the nav and the directory strip read. A row missing any of
#: them renders a link with no label, no tooltip or no probe target.
REQUIRED_FIELDS = ("id", "title", "port", "path", "owner_repo", "health_path",
                   "blurb")

#: The retired per-page idiom: an anchor whose href was rewritten in page JS to
#: point at another server. With JS disabled it pointed at the page's own root.
RETIRED_AUTOPILOT_LINK = 'id="autopilot-link"'

_NAV_BLOCK_RE = re.compile(r"<nav\b.*?</nav>", re.DOTALL | re.IGNORECASE)
_PORT_8000_RE = re.compile(r":8000\s*/\s*dashboard|:\$\{?8000|8000/dashboard")


def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _entries() -> list:
    return _registry()["dashboards"]


# --------------------------------------------------------------------------- #
# 1. The registry file itself
# --------------------------------------------------------------------------- #
class RegistryFileTest(unittest.TestCase):
    def test_the_registry_exists_and_parses(self):
        self.assertTrue(REGISTRY_PATH.is_file(), REGISTRY_PATH)
        data = _registry()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("schema"), server.DASHBOARD_REGISTRY_SCHEMA)
        self.assertIsInstance(data.get("dashboards"), list)
        self.assertTrue(data["dashboards"], "an empty directory is not a directory")

    def test_every_entry_declares_every_field_with_the_right_type(self):
        for entry in _entries():
            with self.subTest(entry=entry.get("id")):
                for field in REQUIRED_FIELDS:
                    self.assertIn(field, entry)
                self.assertIsInstance(entry["id"], str)
                self.assertIsInstance(entry["title"], str)
                self.assertIsInstance(entry["owner_repo"], str)
                self.assertIsInstance(entry["blurb"], str)
                for field in ("id", "title", "owner_repo", "blurb"):
                    self.assertTrue(entry[field].strip(), f"{field} is blank")
                # ``bool`` is an ``int`` subclass; a True port would sail through a
                # bare isinstance check and build the URL ``http://host:True/``.
                self.assertIsInstance(entry["port"], int)
                self.assertNotIsInstance(entry["port"], bool)
                self.assertTrue(0 < entry["port"] < 65536, entry["port"])

    def test_ids_are_unique(self):
        ids = [e["id"] for e in _entries()]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate dashboard id in {ids}")

    def test_paths_are_absolute(self):
        for entry in _entries():
            with self.subTest(entry=entry["id"]):
                self.assertTrue(entry["path"].startswith("/"), entry["path"])
                self.assertTrue(entry["health_path"].startswith("/"),
                                entry["health_path"])

    def test_the_hub_reader_returns_the_file(self):
        """The hub's own reader — not a second parse in this test — is the thing
        the nav and ``/api/dashboards`` both go through."""
        present, entries, err = server._read_dashboard_registry()
        self.assertTrue(present)
        self.assertIsNone(err)
        self.assertEqual([e["id"] for e in entries],
                         [e["id"] for e in _entries()])
        self.assertEqual(server.registry_dashboards(), entries)


# --------------------------------------------------------------------------- #
# 2. Page ↔ registry, both directions
# --------------------------------------------------------------------------- #
class PageRegistryBidirectionalTest(unittest.TestCase):
    """A page the registry does not know about is unreachable from every nav; a
    registry row with no page is a nav link to a 404. One direction catches half.
    """

    HUB_PORT = 8100

    def test_every_hub_page_has_a_registry_entry(self):
        by_path = {e["path"]: e for e in _entries() if e["port"] == self.HUB_PORT}
        for route in server.HTML_ROUTES:
            with self.subTest(route=route):
                self.assertIn(
                    route, by_path,
                    f"{route} is served by the hub but is in no registry row, so "
                    "no nav can link to it")

    def test_every_hub_registry_entry_is_a_served_page(self):
        for entry in _entries():
            if entry["port"] != self.HUB_PORT:
                continue
            with self.subTest(entry=entry["id"]):
                self.assertIn(
                    entry["path"], server.HTML_ROUTES,
                    f"registry row {entry['id']!r} points at {entry['path']}, "
                    "which this hub does not serve — a nav link to a 404")

    def test_the_off_hub_entries_name_a_different_port_and_owner(self):
        """COMPLIANT-PATH CONTROL for the two checks above: the bidirectional rule
        is scoped to port 8100 on purpose, and the registry really does carry an
        entry outside it (the legacy :8000 page) that neither check may reject."""
        off = [e for e in _entries() if e["port"] != self.HUB_PORT]
        self.assertTrue(off, "the directory has stopped describing anything but "
                             "this hub — the cross-server case is untested")
        for entry in off:
            self.assertNotEqual(entry["owner_repo"], "epyc-root", entry["id"])

    def test_the_dashboards_route_is_registered_and_bound(self):
        src = panels.source("dashboards")
        self.assertEqual(src.route, "/api/dashboards")
        self.assertEqual(src.payload_func, "dashboards_payload")
        self.assertIs(server.API_ROUTES["/api/dashboards"], server.dashboards_payload)
        self.assertEqual(src.kind, panels.KIND_LIVE)


# --------------------------------------------------------------------------- #
# 3. Adoption — every page mounts the shared nav
# --------------------------------------------------------------------------- #
def _page_paths() -> dict:
    return {route: Path(path) for route, path in server.HTML_ROUTES.items()}


class SharedNavAdoptionTest(unittest.TestCase):
    """Each page is checked only if its file EXISTS.

    ``/machine`` and ``/autopilot`` are being written by parallel sessions in this
    same working tree (RTG-47 Phase 1a). Skipping a file that is not there yet is
    honest; asserting over a file that IS there is not optional, so the skip is
    keyed on existence rather than on a hardcoded page list that would go stale
    the moment those two land.
    """

    def test_at_least_the_four_original_pages_are_present(self):
        """Non-vacuity guard: the skips above must never be able to empty this
        suite. If every page vanished, the adoption tests would all skip and the
        suite would pass green over an unadopted nav."""
        present = [p for p in _page_paths().values() if p.is_file()]
        self.assertGreaterEqual(len(present), 4, present)

    def test_every_existing_page_mounts_the_shared_nav(self):
        for route, path in _page_paths().items():
            with self.subTest(route=route):
                if not path.is_file():
                    self.skipTest(f"{path.name} not written yet (RTG-47 Phase 1a "
                                  "parallel build); it will exist at CI time")
                text = path.read_text(encoding="utf-8")
                self.assertIn('id="epyc-nav"', text,
                              f"{path.name} has no shared-nav mount point")
                self.assertIn('src="/nav.js"', text,
                              f"{path.name} never loads the shared nav")

    def test_no_page_carries_the_retired_autopilot_link(self):
        for route, path in _page_paths().items():
            with self.subTest(route=route):
                if not path.is_file():
                    self.skipTest(f"{path.name} not written yet")
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(
                    RETIRED_AUTOPILOT_LINK, text,
                    f"{path.name} still carries the retired hand-rolled "
                    "cross-server link; its href was JS-rewritten and pointed at "
                    "the page's own root when that JS did not run")

    def test_no_page_hand_builds_a_cross_server_nav_link(self):
        """Scoped to ``<nav>`` regions ON PURPOSE. Content links inside a card
        body are legitimate prose (the handoff board's outcome card points at the
        orchestrator dashboard in a sentence, and must keep doing so); a
        hand-built link in the NAV is the drift."""
        for route, path in _page_paths().items():
            with self.subTest(route=route):
                if not path.is_file():
                    self.skipTest(f"{path.name} not written yet")
                text = path.read_text(encoding="utf-8")
                for block in _NAV_BLOCK_RE.findall(text):
                    self.assertIsNone(
                        _PORT_8000_RE.search(block),
                        f"{path.name}: a cross-server URL is hand-built inside "
                        f"<nav>: {block[:200]!r}")
                    self.assertNotIn("<a ", block,
                                     f"{path.name}: the nav still contains a "
                                     "hand-authored anchor; links come from "
                                     "dashboard/registry.json")

    def test_the_nav_script_is_a_real_file(self):
        self.assertTrue(NAV_JS_PATH.is_file(), NAV_JS_PATH)
        text = NAV_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("__EPYC_DASHBOARDS", text)
        self.assertIn("epyc-nav", text)


# --------------------------------------------------------------------------- #
# 4. The /nav.js asset the hub actually serves
# --------------------------------------------------------------------------- #
class NavAssetTest(unittest.TestCase):
    def test_the_asset_route_is_declared_with_a_javascript_content_type(self):
        self.assertIn("/nav.js", server.ASSET_ROUTES)
        content_type, builder = server.ASSET_ROUTES["/nav.js"]
        self.assertIn("javascript", content_type)
        self.assertIs(builder, server.nav_asset)

    def test_the_asset_carries_the_registry_and_every_id(self):
        body = server.nav_asset().decode("utf-8")
        self.assertIn("window.__EPYC_DASHBOARDS", body)
        for entry in _entries():
            with self.subTest(entry=entry["id"]):
                self.assertIn(json.dumps(entry["id"]), body)
        # And the renderer itself rode along, not just the data.
        self.assertIn("epyc-nav-link", body)

    def test_the_asset_builder_is_not_a_panel(self):
        """Assets sit outside the panel-registry universe (see ASSET_ROUTES). The
        exemption rests on the NAME, so the name is what is pinned: rename
        ``nav_asset`` to ``nav_payload`` and the panel suites' totality test
        fails on an unregistered payload function."""
        self.assertFalse(server.nav_asset.__name__.endswith(panels.PAYLOAD_SUFFIX))
        self.assertNotIn("nav_asset",
                         {s.payload_func for s in panels.PANELS.values()})

    def test_asset_routes_do_not_collide_with_the_other_tables(self):
        assets = set(server.ASSET_ROUTES)
        self.assertEqual(assets & set(server.HTML_ROUTES), set())
        self.assertEqual(assets & set(server.API_ROUTES), set())
        self.assertEqual(assets & set(server.PROBE_ROUTES), set())


if __name__ == "__main__":
    unittest.main()
