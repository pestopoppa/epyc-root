"""One Kernel R&D surface, and the retired one must be UNREACHABLE, not unlinked.

WHAT HAPPENED (2026-08-30). Two dashboard pages carried this domain. The operator
asked twice why. On `/kernel` they read:

    AutoKernel loop / STOPPED / deployment `gpu-discovery-champion-v37` · last
    lifecycle event 2026-08-28 14:12:42Z (48 h ago) — authoring/build are
    event-silent by design

Every clause was true of the producer it observed. The controller genuinely
stopped. The defect was that a card labelled *AutoKernel loop* reported a
controller deployment while the rebuilt loop ran 46 iterations in, and no surface
said the other one existed. A correct reading of one producer was unreadable as
anything but a claim about the other.

THREE ATTEMPTS, AND ONLY THE THIRD IS THE ASK.

1. Make the two pages honest about each other (a cross-surface banner, a registry
   chip). Both pages still existed, so the question "why are there two" still had
   the same answer.
2. Turn `/kernel` into a labelled archive, out of the nav. Still a navigable
   surface rendering stale numbers — which is the thing that was supposed to stop
   existing. "So it's stale. Why keep it."
3. MERGE. `/loop` is the single Kernel R&D surface; `/kernel` is a 301 to it;
   `dashboard/static/kernel.html` is deleted; the `kernel` registry row is gone.

WHY DELETING RATHER THAN ARCHIVING IS CORRECT HERE. Every producer behind that
page was dead or frozen: the `gpu-discovery-champion-v37` controller (superseded,
never coming back), `kernel_dashboard.json` at 16.8 d, and
`kernel_progression.json` — whose FILE was still being rewritten while its
`observed_through` data horizon stood 16.7 d back and was not advancing. Those are
two different true facts about one file and folding them into a single "age" is
how a frozen dataset reads as a live one. A dashboard is a live instrument;
history belongs in git, the handoffs and the artifacts.

ONE producer there was live and MOVED rather than being dropped: the
operator-gated champion bundle (`+48.9%`). Its rendering is pinned in
`tests/test_dashboard_kernel_freshness_envelopes.py`; what is pinned HERE is that
it arrived, that it kept its own envelope, and that nothing else came with it.

WHY THE ASSERTIONS BELOW GO THROUGH A SOCKET. A route table is not a server. "It
is not in `HTML_ROUTES`" does not prove `/kernel` stops serving markup — a second
dispatch branch, a static-file fallback or a path-normalisation quirk would each
leave the page reachable with the table looking correct. These tests bind a real
port and issue real GETs.

WHY THE GREPS STRIP COMMENTS. This page's own prose NAMES the retired deployment
and the retired route, on purpose, to explain the retirement. A bare
`"gpu-discovery-champion" not in html` therefore fails on the sentence that exists
to tell the reader the thing is gone — and gets "fixed" by deleting the
explanation. What must be absent is the CODE, so the code is what is searched.
"""
from __future__ import annotations

import http.client
import json
import re
import shutil
import subprocess
import sys
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dashboard import server as S  # noqa: E402

STATIC = REPO / "dashboard" / "static"
LOOP_PAGE = STATIC / "loop.html"
RETIRED_PAGE = STATIC / "kernel.html"
REGISTRY = REPO / "dashboard" / "registry.json"

#: Ids and class names that only ever existed in the retired page's markup. Used
#: as a fingerprint: if one of these comes back over the wire, something is still
#: serving that page's DOM whatever the route tables say.
RETIRED_MARKUP = ("cmd-aggregate", "cmd-liveness", "which-loop",
                  "progression-headline", "autokernel-live-state-panel",
                  "v27-cumulative-panel")

#: Renderers that belonged to the retired surface. None of them may reappear on
#: the merged page: the champion card was supposed to move, not the surface.
RETIRED_RENDERERS = ("renderCommandBand", "renderWhichLoop", "renderProgression",
                     "renderLive", "renderV27Cumulative", "renderSections")


def _rows() -> dict:
    return {e["id"]: e
            for e in json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]}


def _inline_js(page: Path) -> str:
    """Inline script bodies only — `<script src=...>` has no body here."""
    return "\n".join(re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        page.read_text(encoding="utf-8"), re.S))


def _strip_comments(js: str) -> str:
    """Remove `/* … */` and `// …` so a grep cannot match its own explanation.

    Deliberately crude and deliberately conservative: it also blanks comment-like
    text inside string literals, which can only ever make these assertions
    STRICTER (a real occurrence in a string still fails). The failure mode that
    matters runs the other way.
    """
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return re.sub(r"(?m)//.*$", " ", js)


def _strip_html_comments(html: str) -> str:
    return re.sub(r"<!--.*?-->", " ", html, flags=re.S)


class _Hub:
    """A real hub on an ephemeral port, for the duration of one test class."""

    def __enter__(self):
        self.httpd = S.build_server("127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    def get(self, path: str, method: str = "GET"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            conn.request(method, path)
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()


class TestTheRetiredPageIsUnreachable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.hub = _Hub().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.hub.__exit__()

    def test_the_pages_markup_is_deleted_from_the_tree(self):
        """Not merely unrouted. An unserved HTML file is a page waiting for one
        table entry to come back."""
        self.assertFalse(
            RETIRED_PAGE.exists(),
            "dashboard/static/kernel.html is still on disk; a retired surface "
            "lives in git history, not beside the pages that are still served")

    def test_the_route_tables_agree_that_it_is_not_a_page(self):
        self.assertNotIn("/kernel", S.HTML_ROUTES)
        self.assertFalse(
            hasattr(S, "KERNEL_HTML"),
            "server.KERNEL_HTML still exists, so re-serving the retired page is "
            "one table entry away")
        self.assertEqual(S.REDIRECT_ROUTES.get("/kernel"), "/loop")

    def test_over_a_real_socket_it_answers_a_permanent_redirect(self):
        for spelling in ("/kernel", "/kernel/"):
            status, headers, _ = self.hub.get(spelling)
            self.assertEqual(status, 301, spelling)
            self.assertEqual(headers.get("Location"), "/loop", spelling)
            # A cached redirect must not outlive a future decision to change it.
            self.assertEqual(headers.get("Cache-Control"), "no-store", spelling)

    def test_no_spelling_of_the_static_file_is_served(self):
        """A redirect on `/kernel` while the file is still fetchable elsewhere is
        a half-retirement that looks complete."""
        for spelling in ("/static/kernel.html", "/kernel.html",
                         "/dashboard/static/kernel.html", "/loop/../kernel"):
            status, _, body = self.hub.get(spelling)
            self.assertNotEqual(status, 200, f"{spelling} still serves something")
            for token in RETIRED_MARKUP:
                self.assertNotIn(token.encode(), body, f"{spelling} -> {token}")

    def test_HEAD_on_the_retired_route_writes_no_body(self):
        """`do_HEAD = do_GET`, so every sender has to honour the method itself."""
        status, headers, body = self.hub.get("/kernel", method="HEAD")
        self.assertEqual(status, 301)
        self.assertEqual(headers.get("Location"), "/loop")
        self.assertEqual(body, b"")

    def test_no_enumerable_route_returns_the_retired_pages_markup(self):
        """The sweep the operator asked for: not a route table read back to
        itself, but every route this hub can serve, fetched and searched."""
        routes = (sorted(S.HTML_ROUTES) + sorted(S.REDIRECT_ROUTES)
                  + sorted(S.API_ROUTES) + sorted(S.PANEL_HEALTH_ROUTES)
                  + sorted(S.PROBE_ROUTES) + sorted(S.ASSET_ROUTES))
        self.assertGreaterEqual(len(routes), 15, "the route sweep is nearly empty")
        offenders = {}
        for route in routes:
            _, _, body = self.hub.get(route)
            hit = [t for t in RETIRED_MARKUP if t.encode() in body]
            if hit:
                offenders[route] = hit
        self.assertEqual(offenders, {},
                         f"routes still serving the retired page's DOM: {offenders}")

    def test_the_markup_sweep_can_actually_find_something(self):
        """NON-VACUITY CONTROL for the sweep above.

        If the fingerprint list or the fetch were broken, the sweep would report a
        clean result over a hub still serving the page. So: prove the same method
        finds a token that IS present, on the same wire, in the same shape.
        """
        _, _, body = self.hub.get("/loop")
        self.assertIn(b"sec-opgate", body)
        probe = [t for t in ("sec-opgate", "cmd-aggregate") if t.encode() in body]
        self.assertEqual(probe, ["sec-opgate"],
                         "the fingerprint method neither finds what is there nor "
                         "misses what is not")

    def test_no_surviving_page_links_a_reader_back_to_the_retired_route(self):
        """An `<a href="/kernel">` would still work — that is the problem. It sends
        a reader on a round trip to learn nothing, and reads as a live sibling
        surface in the meantime."""
        for page in sorted(STATIC.glob("*.html")):
            html = _strip_html_comments(page.read_text(encoding="utf-8"))
            links = re.findall(r'href="([^"]*)"', html)
            self.assertNotIn("/kernel", links, f"{page.name} links to /kernel")


class TestTheRegistryCarriesOneKernelRnDRow(unittest.TestCase):

    def test_exactly_one_row_owns_this_domain_and_it_is_the_live_page(self):
        rows = _rows()
        self.assertIn("autokernel-loop", rows)
        row = rows["autokernel-loop"]
        self.assertEqual(row["title"], "Kernel R&D",
                         "the row is named for the DOMAIN; 'AutoKernel loop' is the "
                         "current mechanism's name, and the mechanism is the part "
                         "that changes")
        self.assertEqual(row["path"], "/loop")
        self.assertEqual(row["port"], 8100)
        self.assertEqual(row["health_path"], "/api/loop/health",
                         "the row must name the DATA probe; /health is transport "
                         "only and stays green over a dead producer")

    def test_the_retired_route_has_no_registry_row(self):
        """No third status was invented. The plane rule's registry is a directory
        of PAGES, and `/kernel` is not a page any more — a row for it would put a
        dead link in every dashboard's nav, which is the drift the registry exists
        to end. `dashboard/README.md` records the choice."""
        rows = _rows()
        self.assertNotIn("kernel", rows)
        self.assertEqual(
            [i for i, r in rows.items() if r.get("path") == "/kernel"], [])

    def test_the_registry_and_the_served_pages_are_still_total_in_both_directions(self):
        rows = _rows()
        hub_paths = {r["path"] for r in rows.values() if r["port"] == 8100}
        self.assertEqual(hub_paths, set(S.HTML_ROUTES),
                         "a registry row with no page is a nav link to a 404; a "
                         "page with no row is a surface nobody learns exists")

    def test_the_nav_asset_offers_the_merged_page_and_not_the_retired_one(self):
        """Asserted against the asset's DATA, not its text.

        The first version of this test did `assertNotIn('"/kernel"', body)` and
        failed — on `nav.js`'s own comment explaining that `"/kernel/"` and
        `"/kernel"` normalise to the same route. The string was in the source and
        nowhere in the behaviour. A grep over a file that contains prose about the
        thing it is greping for cannot answer this question; parse what the browser
        actually receives.
        """
        body = S.nav_asset().decode("utf-8")
        inlined = re.search(r"window\.__EPYC_DASHBOARDS\s*=\s*(\[.*?\]);\n", body,
                            re.S)
        self.assertIsNotNone(inlined, "the nav asset inlines no registry at all")
        rows = json.loads(inlined.group(1))
        self.assertTrue(rows, "the inlined registry is empty")
        paths = {r.get("path") for r in rows}
        titles = {r.get("title") for r in rows}
        self.assertIn("/loop", paths)
        self.assertIn("Kernel R&D", titles)
        self.assertNotIn("/kernel", paths,
                         "the nav still ships the retired route to the browser")

    @unittest.skipIf(shutil.which("node") is None, "node unavailable")
    def test_the_rendered_nav_shows_one_kernel_rnd_link(self):
        """EXECUTED, not grepped. `"Kernel R&D" in nav.js` would pass over a nav
        that never builds an anchor; this runs nav.js against the hub's OWN inlined
        registry and reads the links back off the anchors it built."""
        import tempfile
        driver = r"""
const links = {}; const chips = {};
function anchor() {
  return { className: '', href: '', title: '', textContent: '',
           setAttribute() {},
           appendChild(child) { chips[this.textContent] = child.textContent; } };
}
const built = [];
const host = { id: '', textContent: '', classList: { add() {} },
               appendChild() {} };
global.window = {};
global.document = {
  getElementById: (id) => (id === 'epyc-nav' ? host : null),
  createElement: (tag) => { if (tag !== 'a') return { id: '', className: '',
                              textContent: '', appendChild() {} };
                            const a = anchor(); built.push(a); return a; },
  createTextNode: (t) => ({ t }),
  createDocumentFragment: () => ({ appendChild() {} }),
  head: { appendChild() {} }, documentElement: { appendChild() {} },
  body: { insertBefore() {}, firstChild: null },
  readyState: 'complete', addEventListener() {},
};
global.location = { port: '8100', protocol: 'http:', hostname: 'h',
                    pathname: '/loop' };
"""
        tail = ("\nfor (const a of built) links[a.textContent] = a.href;"
                "\nconsole.log(JSON.stringify({links, chips}));\n")
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "nav_drive.js"
            script.write_text(driver + "\n" + S.nav_asset().decode("utf-8") + tail,
                              encoding="utf-8")
            proc = subprocess.run(["node", str(script)], capture_output=True,
                                  text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
        out = json.loads(proc.stdout.splitlines()[-1])
        links, chips = out["links"], out["chips"]
        self.assertTrue(links, "the nav built no links at all")
        kernel_rnd = [t for t in links if t.startswith("Kernel R&D")]
        self.assertEqual(len(kernel_rnd), 1,
                         f"expected exactly one Kernel R&D link, got {list(links)}")
        self.assertTrue(links[kernel_rnd[0]].endswith("/loop"))
        self.assertFalse([h for h in links.values() if h.endswith("/kernel")],
                         f"the nav still offers the retired route: {links}")
        self.assertEqual(chips.get("Kernel R&D"), "live")
        self.assertEqual(chips.get("Legacy (:8000)"), "legacy",
                         "an unrelated row's chip was lost")
        self.assertNotIn("Handoffs", chips,
                         "a chipless row grew a chip — the fallback is too broad")


class TestTheOneLiveProducerMoved(unittest.TestCase):

    def test_the_loop_payload_carries_the_operator_gated_bundle(self):
        payload = S.loop_payload()
        self.assertIn("operator_gates", payload,
                      "the one live producer on the retired page did not move; it "
                      "was dropped")
        gates = payload["operator_gates"]
        self.assertIn("freshness", gates)
        self.assertIn(gates["freshness"]["state"],
                      set(S.OPERATOR_GATE_BUNDLE_STATES))

    def test_it_is_the_EXISTING_reader_not_a_second_one(self):
        """Two readers of one file drift, and the second one is always the one
        without the scars. Pointing the module constant at a temp path must move
        what `/api/loop` reports — which it can only do if there is one reader."""
        import tempfile
        original = S.OPERATOR_GATE_BUNDLE_JSON
        with tempfile.TemporaryDirectory() as td:
            S.OPERATOR_GATE_BUNDLE_JSON = Path(td) / "nothing-here.json"
            try:
                gates = S.loop_payload()["operator_gates"]
            finally:
                S.OPERATOR_GATE_BUNDLE_JSON = original
        self.assertFalse(gates["available"])
        self.assertEqual(gates["freshness"]["state"], "absent")
        self.assertIn("nothing-here.json", gates["evidence"],
                      "an absent reading must name the path it looked at, or the "
                      "investigation has nowhere to go")

    def test_the_two_envelopes_are_separate(self):
        """Neither producer may date the other. A merged page with one envelope is
        a page where the loudest live producer certifies every silent one."""
        payload = S.loop_payload()
        self.assertIn("_freshness", payload)
        self.assertIsNot(payload["_freshness"], payload["operator_gates"]["freshness"])
        self.assertNotEqual(payload["_freshness"].get("evidence"),
                            payload["operator_gates"].get("evidence"))

    def test_the_loop_probe_still_answers_for_the_loop_alone(self):
        """DECLARED SEAM, pinned so it cannot change silently.

        `/api/loop/health` was NOT widened to fold the bundle. Registering a
        second panel would change what `health_payload()` folds, and that function
        is under concurrent edit elsewhere. The bundle's verdict therefore travels
        in the body it dates, rendered on the card. `dashboard/README.md` carries
        this under Known open items; this test is what makes a future widening a
        deliberate act rather than an accident.
        """
        import tempfile
        original = S.OPERATOR_GATE_BUNDLE_JSON
        with tempfile.TemporaryDirectory() as td:
            S.OPERATOR_GATE_BUNDLE_JSON = Path(td) / "gone.json"
            try:
                status, body = S.loop_data_health()
            finally:
                S.OPERATOR_GATE_BUNDLE_JSON = original
        self.assertIn("status", body)
        self.assertNotIn("operator", json.dumps(body).lower(),
                         "the loop probe has started reporting the champion "
                         "bundle; if that is intended, register it as a panel "
                         "rather than letting one probe answer for two producers")


class TestTheRetiredSubsystemDidNotComeAlong(unittest.TestCase):

    def test_the_merged_page_has_no_controller_liveness_card(self):
        """A retired subsystem does not get a liveness card.

        Its STOPPED was CORRECT, which is exactly the problem: a correct statement
        about a dead thing, sitting on the live page, reads as a statement about
        the living one.
        """
        js = _strip_comments(_inline_js(LOOP_PAGE))
        for renderer in RETIRED_RENDERERS:
            self.assertNotIn(renderer, js,
                             f"{renderer} came across from the retired surface")
        self.assertNotIn("gpu-discovery-champion", js,
                         "the retired deployment is named in this page's CODE, not "
                         "just in the prose that explains its retirement")
        for token in ("STOPPED", "deployment_history", "cmd-pulse"):
            self.assertNotIn(token, js, token)

    def test_the_merged_page_never_fetches_the_retired_surfaces_data(self):
        """A link is fine; a data dependency is not. `/loop` must keep working
        while anything behind `/api/kernel` is broken."""
        js = _strip_comments(_inline_js(LOOP_PAGE))
        self.assertNotIn("/api/kernel", js)
        fetched = re.findall(r'fetch\(\s*"([^"]+)"', js)
        self.assertEqual(sorted(fetched), ["/api/loop"],
                         f"the page fetches more than its own contract: {fetched}")

    def test_the_prose_that_explains_the_retirement_is_still_there(self):
        """OPPOSITE-DIRECTION CONTROL, and it must fail in the other direction.

        The two assertions above are satisfied trivially by deleting the sentences
        that tell a reader what happened to `/kernel` — the page would pass while
        becoming less honest. This requires the explanation to survive, which is
        also what makes the comment-stripping above load-bearing rather than
        decorative.
        """
        html = LOOP_PAGE.read_text(encoding="utf-8")
        visible = _strip_html_comments(html)
        self.assertIn("gpu-discovery-champion-v37", visible,
                      "the page no longer names the retired deployment anywhere a "
                      "reader can see it")
        self.assertIn("2026-08-30", visible, "the retirement date is not on the page")
        self.assertIn("retired", visible.lower())

    def test_the_page_is_titled_for_the_domain_not_the_mechanism(self):
        html = LOOP_PAGE.read_text(encoding="utf-8")
        self.assertRegex(html, r"<title>[^<]*Kernel R&amp;D[^<]*</title>")
        self.assertRegex(html, r"<h1>\s*Kernel R&amp;D\s*</h1>")


class TestThePageOpensWithTheHeadline(unittest.TestCase):
    """Operator note, 2026-08-31: the three-producer taxonomy lecture at the
    top of the page goes entirely; the page opens with the headline. The one
    load-bearing sentence from it — where /kernel went — survives as a single
    short line at the BOTTOM (the footer), which is what keeps
    ``test_the_prose_that_explains_the_retirement_is_still_there`` honest
    rather than satisfied by a lecture."""

    def test_the_top_explainer_is_gone_and_the_headline_is_first(self):
        html = LOOP_PAGE.read_text(encoding="utf-8")
        # RENDERED text only: strip comments AND the script/style bodies, or
        # this grep matches the code's own explanations (the key-too-wide
        # fault this suite keeps relearning).
        visible = _strip_html_comments(html)
        visible = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", visible,
                         flags=re.S)
        self.assertNotIn("sec-scope", html,
                         "the top-of-page scope explainer is still in the markup")
        self.assertNotIn("three producers", visible,
                         "the producer-taxonomy lecture is still rendered")
        main = html.split("<main>", 1)[1]
        first_section = re.search(r'<section[^>]*id="([A-Za-z0-9_-]+)"', main)
        self.assertIsNotNone(first_section)
        self.assertEqual(first_section.group(1), "sec-champion",
                         "the page no longer opens with the champion headline")
        # Nothing VISIBLE sits between the (empty-by-default) freshness banner
        # and the headline section.
        between = main.split('id="banner"', 1)[1].split("<section", 1)[0]
        self.assertEqual(_strip_html_comments(between).replace("></div>", "")
                         .strip(), "",
                         "visible content sits above the headline")

    def test_the_retirement_pointer_survives_at_the_bottom(self):
        html = LOOP_PAGE.read_text(encoding="utf-8")
        footer = html.split("<footer>", 1)[1].split("</footer>", 1)[0]
        self.assertIn("gpu-discovery-champion-v37", footer)
        self.assertIn("2026-08-30", footer)
        self.assertIn("retired", footer.lower())


if __name__ == "__main__":
    unittest.main()
