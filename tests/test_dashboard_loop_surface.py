"""The rebuilt AutoKernel loop's dashboard surface: page, registry row, probe.

WHY THIS SUITE EXISTS. The operator had ZERO visibility into the rebuilt loop:
the dashboard showed the superseded deployment ``gpu-discovery-champion-v37`` as
STOPPED — a true statement about a different process — while the new loop ran as
something nothing observed. These tests pin the three things the plane rule in
``dashboard/README.md`` requires (a registry entry, a health probe, a freshness
envelope) and, above all, the FOUR-VALUED freshness rendering.

THE FRESHNESS TESTS ARE THE POINT. ``absent`` / ``stale`` / ``fresh`` /
``malformed`` must stay four distinct renderings. Collapsing ``absent`` into
``stale`` is how a dead producer previously rendered as a clean, empty, trusted
page; collapsing ``malformed`` into ``absent`` points an investigation at
whether the loop exists when the real fault is in its writer. Every pair is
asserted distinct, in the payload, in the probe, and in the rendered DOM.

NO CROSS-REPO PINS. The producer owns ``epyc.autokernel.loop_status.v1`` in
epyc-inference-research; nothing here reads that repository, imports its
modules, or pins a path or digest of it. Fixtures are hand-built bodies in a
temp dir — the loop's real store root is never written to.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import loop_status, panels  # noqa: E402
from dashboard import server as S  # noqa: E402

PAGE = REPO / "dashboard/static/loop.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"
REGISTRY = REPO / "dashboard/registry.json"

#: A RECORDED body, captured verbatim from the running loop's own store root on
#: 2026-08-30 (hotspots/recent trimmed for size; no field renamed, no field
#: added). This is not a cross-repo pin — nothing here imports or resolves a
#: path in epyc-inference-research — it is an OBSERVATION of what the producer
#: actually writes, kept because the hand-built fixture below could not catch
#: the defect that made this file necessary: ``body()`` invented ``held_s`` and
#: ``busy_s``, the reader looked for ``held_s`` and ``busy_s``, the two agreed
#: with each other and disagreed with the producer, and 41 tests passed while
#: the GPU panel — the one panel this whole surface was built for — rendered
#: "the loop published no held/busy seconds" over a producer publishing them
#: every iteration.
SAMPLE = REPO / "tests/fixtures/autokernel_loop_status_sample.json"


def recorded(*, age_s: float = 45.0) -> dict:
    """The recorded producer body, re-stamped so it is not permanently stale.

    Only ``generated_at`` is rewritten. Every other field — the gpu key
    spellings above all — is the producer's own.
    """
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    stamped = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    payload["generated_at"] = stamped.isoformat().replace("+00:00", "Z")
    return payload

#: The registry row and the panel id for this surface.
DASHBOARD_ID = "autokernel-loop"
PANEL = "autokernel_loop"


def body(*, age_s: float = 45.0, state: str = "running",
         stale_after_s: int = 1800, gpu: dict | None = None,
         dispositions: dict | None = None) -> dict:
    """A well-formed ``epyc.autokernel.loop_status.v1`` body.

    Hand-built from the documented field list, NOT imported from the producer:
    the hub must be able to read this contract without the producer's repo on
    disk, and a test that imports it would silently become a cross-repo pin.
    """
    stamped = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    return {
        "schema": loop_status.STATUS_SCHEMA,
        "generated_at": stamped.isoformat().replace("+00:00", "Z"),
        "stale_after_s": stale_after_s,
        "state": state,
        "campaign_id": "ak-loop",
        "epoch_sha256": "e" * 64,
        "anchor_commit": "a" * 40,
        "surface": "pp512",
        "pairs": 5,
        "noise_floor_pct": 0.973,
        "iterations_planned": 10,
        "iterations_done": 6,
        "measurements_reached": 2,
        "dispositions": dispositions if dispositions is not None else {
            "compile_refused": 1, "kept": 1, "measured_null": 1,
            "planner_transient": 2, "refused_at_formation": 1},
        "champion_head": "c" * 40,
        "gpu": {"held_s": 7200.0, "busy_s": 331.0} if gpu is None else gpu,
        "hotspots": [{"signature": "mul_mat_q4_K", "total_duration_ns": 9_000_000_000,
                      "calls": 4210, "share_of_device_time": 0.41}],
        "recent": [
            {"status": "refused_at_formation", "mechanism_id": None,
             "effect_fraction": None, "reason": "already measured"},
            {"status": "planner_transient", "mechanism_id": None,
             "effect_fraction": None, "reason": "actor exited 1"},
            {"status": "measured_null", "mechanism_id": "akm-b",
             "effect_fraction": 0.002, "reason": "below the noise floor"},
            {"status": "kept", "mechanism_id": "akm-a",
             "effect_fraction": 0.031, "reason": ""},
        ],
    }


class _Fixture(unittest.TestCase):
    """Points the hub at a temp store root for the duration of one test."""

    def setUp(self) -> None:
        import os
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix="loop-status-fixture-")
        self._prior = os.environ.get(loop_status.STORE_ROOT_ENV)
        os.environ[loop_status.STORE_ROOT_ENV] = self._tmp
        self.root = Path(self._tmp)
        self.target = self.root / loop_status.STATUS_FILENAME
        # The watchdog's memory is process-global; a watermark left by another
        # test would make one test's verdict depend on another's ordering.
        with S._watchdog_lock:
            S._watchdog_state.clear()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        import os
        if self._prior is None:
            os.environ.pop(loop_status.STORE_ROOT_ENV, None)
        else:
            os.environ[loop_status.STORE_ROOT_ENV] = self._prior
        shutil.rmtree(self._tmp, ignore_errors=True)

    def write(self, content) -> None:
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2)
        self.target.write_text(content, encoding="utf-8")

    def absent(self) -> None:
        self.target.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# Four-valued freshness — the load-bearing distinction
# --------------------------------------------------------------------------- #
class Freshness(_Fixture):

    def test_absent_is_not_stale_is_not_malformed_is_not_fresh(self):
        """If any two collapse, a dead producer can render as a live one."""
        seen = {}
        self.absent()
        seen["absent"] = S.loop_payload()["freshness_state"]
        self.write(body(age_s=30))
        seen["fresh"] = S.loop_payload()["freshness_state"]
        self.write(body(age_s=9000))
        seen["stale"] = S.loop_payload()["freshness_state"]
        self.write("{not json")
        seen["malformed"] = S.loop_payload()["freshness_state"]
        self.assertEqual(seen, {"absent": "absent", "fresh": "fresh",
                                "stale": "stale", "malformed": "malformed"})
        self.assertEqual(len(set(seen.values())), 4,
                         "two freshness states collapsed into one rendering")

    def test_absence_carries_null_not_an_empty_body(self):
        """``[]``/``{}`` says the producer reported nothing; ``null`` says nobody
        reported. The old shell said the former for both."""
        self.absent()
        got = S.loop_payload()
        self.assertIsNone(got["loop"])
        self.assertIsNone(got["derived"])
        self.assertFalse(got["artifact_present"])
        self.assertIn("never published", got["detail"])

    def test_absence_says_what_absence_means(self):
        self.absent()
        got = S.loop_payload()
        self.assertTrue(got["absence_means"].strip())
        self.assertIn("absence_means", got["_freshness"])

    def test_a_stale_reading_still_carries_the_last_report_and_says_so(self):
        """Hiding the last report loses information; presenting it as current
        is a lie. The body stays, under a detail that says it is the LAST one."""
        self.write(body(age_s=9000))
        got = S.loop_payload()
        self.assertEqual(got["freshness_state"], "stale")
        self.assertIsNotNone(got["loop"])
        self.assertIn("LAST report", got["detail"])
        self.assertGreater(got["age_s"], 1800)

    def test_the_envelope_is_the_producers_own_not_a_hub_constant(self):
        """A loop that declares a longer cadence must not read as stale."""
        self.write(body(age_s=3600, stale_after_s=7200))
        self.assertEqual(S.loop_payload()["freshness_state"], "fresh")
        self.write(body(age_s=3600, stale_after_s=1800))
        self.assertEqual(S.loop_payload()["freshness_state"], "stale")

    def test_an_empty_file_is_malformed_not_absent(self):
        """Broken is not never-exported: one points at the writer, the other at
        whether the loop exists at all."""
        self.write("")
        got = S.loop_payload()
        self.assertEqual(got["freshness_state"], "malformed")
        self.assertTrue(got["artifact_present"])
        self.assertIn("empty", got["reader_error"])

    def test_a_half_written_file_is_malformed_and_names_the_fault(self):
        self.write(json.dumps(body())[:180])
        got = S.loop_payload()
        self.assertEqual(got["freshness_state"], "malformed")
        self.assertIn("not valid JSON", got["reader_error"])
        self.assertIsNone(got["loop"])

    def test_a_foreign_schema_is_refused_rather_than_rendered(self):
        """Field names from another contract would not mean what they say."""
        self.write({"schema": "epyc.something.else.v1", "generated_at": "2026-08-28T00:00:00Z"})
        got = S.loop_payload()
        self.assertEqual(got["freshness_state"], "malformed")
        self.assertIn("schema", got["reader_error"])

    def test_an_unparseable_stamp_is_malformed_not_fresh(self):
        broken = body()
        broken["generated_at"] = "not a timestamp"
        self.write(broken)
        self.assertEqual(S.loop_payload()["freshness_state"], "malformed")

    def test_a_future_stamp_cannot_buy_permanent_freshness(self):
        """A future timestamp never ages, so it would read fresh however long
        the producer has been dead."""
        self.write(body(age_s=-86400))
        got = S.loop_payload()
        self.assertEqual(got["freshness_state"], "malformed")
        self.assertIn("FUTURE", got["detail"])

    def test_nothing_is_cached_across_requests(self):
        """A cached value can outlive the envelope that is the point of the
        envelope."""
        self.write(body(age_s=30))
        self.assertEqual(S.loop_payload()["freshness_state"], "fresh")
        self.absent()
        self.assertEqual(S.loop_payload()["freshness_state"], "absent")
        self.write(body(age_s=30))
        self.assertEqual(S.loop_payload()["freshness_state"], "fresh")


# --------------------------------------------------------------------------- #
# The health probe — the /api/health KIND, not the /health kind
# --------------------------------------------------------------------------- #
class Probe(_Fixture):

    def test_fresh_is_ok_and_200(self):
        self.write(body(age_s=30))
        code, out = S.loop_data_health()
        self.assertEqual((code, out["status"]), (200, panels.STATUS_OK))
        self.assertEqual(out["probe"], "panel-data")

    def test_absent_is_absent_not_ok_and_not_degraded(self):
        """Three-valued: nobody-ever-ran is neither healthy nor broken."""
        self.absent()
        code, out = S.loop_data_health()
        self.assertEqual(out["status"], panels.STATUS_ABSENT)
        self.assertEqual(code, 503)
        self.assertTrue(out["absent"], "absence must be named, never merely implied")

    def test_stale_is_degraded(self):
        self.write(body(age_s=9000))
        code, out = S.loop_data_health()
        self.assertEqual((code, out["status"]), (503, panels.STATUS_DEGRADED))

    def test_malformed_is_degraded_not_absent(self):
        """A broken write must not inherit a cold start's benefit of the doubt."""
        self.write("{half")
        code, out = S.loop_data_health()
        self.assertEqual((code, out["status"]), (503, panels.STATUS_DEGRADED))
        self.assertIsNotNone(out["reader_error"])

    def test_a_declared_failure_is_degraded_even_while_perfectly_fresh(self):
        """A loop that crashed a minute ago is fresh AND dead. Answering 'ok' to
        'is this still true?' over a corpse is the failure this probe closes."""
        self.write(body(age_s=30, state="failed"))
        code, out = S.loop_data_health()
        self.assertEqual((code, out["status"]), (503, panels.STATUS_DEGRADED))
        self.assertEqual(out["loop_state"], "failed")
        self.assertIn("DECLARED", out["declared_failure"])
        # ...and freshness alone would indeed have said fresh.
        self.assertEqual(S.loop_payload()["freshness_state"], "fresh")

    def test_a_declared_completion_is_allowed_to_be_silent(self):
        """The compliant path: the hub never INFERS idleness, but it honours a
        producer that DECLARES it."""
        self.write(body(age_s=9000, state="complete"))
        code, out = S.loop_data_health()
        self.assertEqual((code, out["status"]), (200, panels.STATUS_OK))
        self.assertEqual(out["freshness"]["watchdog"]["state"], panels.WATCHDOG_IDLE)

    def test_the_probe_is_not_the_transport_probe(self):
        """/health stays green over a dead loop; that is why it may not be this
        route, and why the supervisor must never poll this one."""
        self.absent()
        _, out = S.loop_data_health()
        self.assertNotEqual(out["status"], S.transport_probe_payload()["status"])
        self.assertEqual(out["transport_health"], "/health")
        self.assertEqual(out["global_health"], "/api/health")

    def test_the_probe_does_not_recurse_through_the_global_fold(self):
        """A registry consumer must be able to see a live hub and a silent loop
        as two different facts."""
        self.absent()
        _, out = S.loop_data_health()
        self.assertEqual(out["panel"], PANEL)
        self.assertEqual([row["panel"] for row in out["attention"]], [PANEL])

    def test_every_freshness_state_maps_to_a_distinct_probe_answer(self):
        cases = {}
        self.absent()
        cases["absent"] = S.loop_data_health()[1]["status"]
        self.write(body(age_s=30))
        cases["fresh"] = S.loop_data_health()[1]["status"]
        self.write(body(age_s=9000))
        cases["stale"] = S.loop_data_health()[1]["status"]
        self.assertEqual(cases, {"absent": panels.STATUS_ABSENT,
                                 "fresh": panels.STATUS_OK,
                                 "stale": panels.STATUS_DEGRADED})


# --------------------------------------------------------------------------- #
# Registry entry, panel registry, routes — the plane rule's three things
# --------------------------------------------------------------------------- #
class Wiring(unittest.TestCase):

    def test_the_dashboard_registry_carries_the_page(self):
        """No unregistered pages: a page absent from the registry is invisible
        to the nav, has no probe, and nobody learns it exists."""
        entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]
        row = [e for e in entries if e.get("id") == DASHBOARD_ID]
        self.assertEqual(len(row), 1, f"{DASHBOARD_ID} must appear exactly once")
        row = row[0]
        self.assertEqual(row["path"], "/loop")
        self.assertEqual(row["port"], 8100)
        self.assertEqual(row["owner_repo"], "epyc-root")
        self.assertTrue(row["blurb"].strip())

    def test_the_registry_row_names_the_DATA_probe_not_the_transport_one(self):
        """A registry entry pointing at /health buys liveness of the SERVER, not
        freshness of the DATA — and this surface exists because of exactly that
        gap."""
        entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]
        row = next(e for e in entries if e["id"] == DASHBOARD_ID)
        self.assertEqual(row["health_path"], "/api/loop/health")
        self.assertNotEqual(row["health_path"], "/health")

    def test_the_page_is_reachable_from_the_shared_nav(self):
        asset = S.nav_asset().decode("utf-8")
        self.assertIn('"/loop"', asset)
        self.assertIn(DASHBOARD_ID, asset)

    def test_the_panel_registry_is_total_over_the_new_surface(self):
        gaps = panels.registry_gaps(S)
        self.assertEqual({k: v for k, v in gaps.items() if v}, {},
                         "the panel registry and the hub's code disagree")

    def test_the_panel_declares_a_freshness_envelope_and_what_absence_means(self):
        src = panels.source(PANEL)
        self.assertEqual(src.kind, panels.KIND_EXPORT)
        self.assertIsNotNone(src.warn_s)
        self.assertIsNotNone(src.stale_s)
        self.assertTrue(src.watched)
        self.assertIsNotNone(src.silent_after_s)
        self.assertIn("never published", src.absence_means)
        self.assertEqual(src.route, "/api/loop")
        self.assertEqual(src.health_route, "/api/loop/health")

    def test_the_routes_are_in_the_tables(self):
        self.assertIs(S.HTML_ROUTES["/loop"], S.LOOP_HTML)
        self.assertIs(S.API_ROUTES["/api/loop"], S.loop_payload)
        self.assertIs(S.PANEL_HEALTH_ROUTES["/api/loop/health"], S.loop_data_health)
        # The data probe may return 503; the supervisor's transport probe must
        # never be it.
        self.assertNotIn("/api/loop/health", S.PROBE_ROUTES)
        self.assertNotIn("/api/loop/health", S.API_ROUTES)

    def test_the_panel_is_folded_into_global_health(self):
        """``fold({})`` is not ``ok``; a panel that drops out of the fold is
        named as degraded rather than subtracted."""
        self.assertIn(PANEL, S.panel_envelopes())

    def test_the_existing_kernel_surface_is_untouched(self):
        """This is a SEPARATE surface. The Kernel-R&D panel keeps its own
        producer, route and probe — one contract's rewrite must not be another
        contract's outage."""
        self.assertIs(S.API_ROUTES["/api/kernel"], S.kernel_payload)
        self.assertIs(S.PANEL_HEALTH_ROUTES["/api/kernel/health"], S.kernel_data_health)
        self.assertNotEqual(panels.source("kernel").evidence,
                            panels.source(PANEL).evidence)
        self.assertNotEqual(panels.source("kernel").producer,
                            panels.source(PANEL).producer)


# --------------------------------------------------------------------------- #
# Derived views — folds, never invented claims
# --------------------------------------------------------------------------- #
class Derived(_Fixture):

    def test_the_negatives_are_counted_beside_the_keeps(self):
        """A board that shows only wins is how 0 promotions looked like progress
        for a month."""
        self.write(body())
        derived = S.loop_payload()["derived"]
        self.assertEqual(derived["kept"], 1)
        self.assertEqual(derived["negatives"], 5)
        self.assertEqual(derived["measured"], 2)
        self.assertEqual(derived["never_measured"], 4)

    def test_an_empty_gpu_map_reports_nothing_rather_than_a_fabricated_zero(self):
        """0s busy over 0s held is not 100% idle; it is no measurement. An
        invented number is worse than the silence it replaces."""
        self.write(body(gpu={}))
        gpu = S.loop_payload()["derived"]["gpu"]
        self.assertFalse(gpu["reported"])
        self.assertIsNone(gpu["busy_pct"])
        self.assertIsNone(gpu["idle_s"])

    def test_held_against_busy_becomes_an_idle_share(self):
        """The loop ran 95.4% idle on a held device for a month and nothing
        reported it, because the old surface reported iterations and receipts."""
        self.write(body(gpu={"held_s": 1000.0, "busy_s": 46.0}))
        gpu = S.loop_payload()["derived"]["gpu"]
        self.assertTrue(gpu["reported"])
        self.assertAlmostEqual(gpu["busy_pct"], 4.6)
        self.assertAlmostEqual(gpu["idle_s"], 954.0)

    def test_a_partial_gpu_map_is_not_half_reported(self):
        self.write(body(gpu={"held_s": 1000.0}))
        self.assertFalse(S.loop_payload()["derived"]["gpu"]["reported"])

    def test_iterations_remaining_is_a_fold_not_a_guess(self):
        self.write(body())
        self.assertEqual(S.loop_payload()["derived"]["iterations_remaining"], 4)


# --------------------------------------------------------------------------- #
# The page actually renders — runtime JS, not a syntax check
# --------------------------------------------------------------------------- #
@unittest.skipIf(shutil.which("node") is None, "node unavailable")
class Rendering(_Fixture):
    """Executes ``loop.html``'s script blocks under the shared DOM stubs.

    KNOWN LIMIT, stated rather than hidden (same as
    ``tests/test_dashboard_runtime_js.py``): stubs are not a browser. This proves
    the render path executes and emits the expected content, not that the page
    looks right.
    """

    def _page_js(self) -> str:
        html = PAGE.read_text(encoding="utf-8")
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
        self.assertTrue(blocks, "no inline script blocks found in loop.html")
        return "\n".join(blocks)

    def _render(self, payload: dict, page_js: str | None = None) -> dict:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="loop-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(page_js if page_js is not None else self._page_js(),
                                     encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json")],
            capture_output=True, text=True, timeout=60)
        self.assertTrue(proc.stdout.strip(),
                        f"harness produced no output; stderr={proc.stderr[:400]}")
        return json.loads(proc.stdout)

    def test_the_harness_CATCHES_a_runtime_fault(self):
        """Mutation, as a test: a harness that cannot fail proves nothing.

        APPENDED, not prepended — function declarations hoist, so a thrower
        placed before the real declaration is silently overridden by it.
        """
        self.write(body())
        broken = self._page_js() + "\nfunction render(d){ throw new Error('injected'); }\n"
        out = self._render(S.loop_payload(), page_js=broken)
        self.assertTrue(out["threw"], "the harness did not notice an injected fault")
        self.assertTrue(any("injected" in t for t in out["threw"]))

    def test_a_fresh_reading_renders_without_throwing(self):
        self.write(body())
        out = self._render(S.loop_payload())
        self.assertEqual(out["threw"], [])
        self.assertGreater(out["rendered_chars"], 500)

    def test_every_freshness_state_renders_a_DISTINCT_headline(self):
        """The whole suite in one assertion: four states, four renderings. If any
        two produce the same page, a dead producer can look like a live one."""
        heads = {}
        self.absent()
        heads["absent"] = self._render(S.loop_payload())["html"]
        self.write(body(age_s=9000))
        heads["stale"] = self._render(S.loop_payload())["html"]
        self.write("{half")
        heads["malformed"] = self._render(S.loop_payload())["html"]
        self.write(body(age_s=30))
        fresh_out = self._render(S.loop_payload())
        heads["fresh"] = fresh_out["html"]

        self.assertIn("ABSENT", heads["absent"])
        self.assertIn("has ever published here", heads["absent"])
        self.assertIn("STALE", heads["stale"])
        self.assertIn("LAST report", heads["stale"])
        self.assertIn("MALFORMED", heads["malformed"])
        self.assertIn("cannot trust", heads["malformed"])
        # ...and the fresh reading raises no LOOP banner at all. Keyed to the
        # banner ELEMENT, not the whole page: the other producers on this page
        # (the memory store above all) may honestly be ABSENT in this fixture
        # root, and their own cards MUST say so — a whole-page key here would
        # forbid exactly the honesty this page exists for.
        for shout in ("ABSENT", "STALE —", "MALFORMED"):
            self.assertNotIn(shout, fresh_out["by_id"].get("banner", ""),
                             f"a fresh reading rendered the {shout!r} banner")
        self.assertEqual(len(set(heads.values())), 4,
                         "two freshness states produced the same rendering")

    def test_an_absent_reading_never_renders_a_confident_empty_page(self):
        """Zero dispositions and no report are different claims."""
        self.absent()
        html = self._render(S.loop_payload())["html"]
        self.assertIn("No readable report", html)
        self.assertNotIn("has recorded no iteration outcome yet", html)

    def test_the_negatives_reach_the_rendered_page(self):
        self.write(body())
        html = self._render(S.loop_payload())["html"]
        for token in ("planner_transient", "refused_at_formation", "compile_refused",
                      "measured_null", "kept"):
            self.assertIn(token, html, f"disposition {token!r} is not on the page")
        self.assertIn("never measured", html)

    def test_the_page_shows_what_the_operator_asked_for(self):
        self.write(body())
        html = self._render(S.loop_payload())["html"]
        for token in ("6 / 10",          # iterations done/planned
                      "0.973%",          # the noise floor it gates on
                      "cccccccccccc",    # champion head (truncated)
                      "4.6%",            # GPU busy share
                      "+3.100%",         # a kept candidate's effect
                      "mul_mat_q4_K"):   # hotspot
            self.assertIn(token, html, f"{token!r} missing from the rendered page")

    def test_an_unreported_gpu_map_renders_nothing_rather_than_100_percent_idle(self):
        # Scoped to the GPU panel, not the whole page: a page-wide "100%" check
        # is a key too wide — it matches the "+3.100%" in the iteration table and
        # then fails (or passes) for a reason that has nothing to do with GPU.
        self.write(body(gpu={}))
        out = self._render(S.loop_payload())
        gpu = out["by_id"]["gpu"]
        self.assertIn("not reported", out["by_id"]["tiles"])
        self.assertIn("reports <strong>nothing</strong>", gpu)
        # STRUCTURAL, not a substring sweep: the panel's prose legitimately
        # mentions percentages ("rather than 0% busy", "95.4% idle") while
        # asserting nothing about this run. What must be absent is the MEASURED
        # rendering — the meter fill and the held/busy/idle figures.
        self.assertNotIn("var(--good)", gpu, "an unreported GPU panel drew a meter")
        self.assertNotIn('<dl class="kv"', gpu,
                         "an unreported GPU panel emitted held/busy/idle figures")

    def test_a_reported_gpu_map_DOES_draw_the_meter(self):
        """The mutation half of the test above: if the panel drew nothing either
        way, the assertion there would pass for the wrong reason."""
        self.write(body(gpu={"held_s": 1000.0, "busy_s": 46.0}))
        gpu = self._render(S.loop_payload())["by_id"]["gpu"]
        self.assertIn("4.6%", gpu)
        self.assertIn("var(--good)", gpu)

    def test_the_RECORDED_producer_body_draws_the_meter_too(self):
        """The render half of :class:`RealProducerSample`.

        Every GPU rendering assertion above runs on a body this suite wrote. On
        the body the PRODUCER writes, the panel rendered its not-reported prose
        for two days on a live device. Assert against the recording.
        """
        self.write(recorded())
        out = self._render(S.loop_payload())
        self.assertEqual(out["threw"], [])
        gpu = out["by_id"]["gpu"]
        self.assertIn("var(--good)", gpu,
                      "the GPU meter is dark on the producer's own body")
        self.assertNotIn("reports <strong>nothing</strong>", gpu)
        self.assertNotIn("not reported", out["by_id"]["tiles"])

    def test_an_unknown_gpu_dialect_names_the_READER_on_the_page(self):
        """And the mutation half of THAT: the panel must still go dark — while
        pointing at the right repository — when the keys really are unknown."""
        self.write(body(gpu={"gpu_seconds_of_something_new": 12.0}))
        out = self._render(S.loop_payload())
        gpu = out["by_id"]["gpu"]
        self.assertNotIn("var(--good)", gpu, "an unreadable GPU map drew a meter")
        self.assertIn("READER defect", gpu)
        self.assertIn("gpu_seconds_of_something_new", gpu)


# --------------------------------------------------------------------------- #
# The producer's OWN body — the fixture this suite could not invent
# --------------------------------------------------------------------------- #
class RealProducerSample(_Fixture):
    """Reads a body recorded from the running loop, not one this suite made up.

    WHY THIS CLASS EXISTS. Every other test here builds its fixture from
    :func:`body`, which was written from a field list and never checked against
    an actual export. It spelled the GPU seconds ``held_s``/``busy_s``; the
    producer has always written ``claim_held_s``/``device_seconds_under_load``.
    The reader agreed with the fixture, so 41 tests passed while ``/api/loop``
    served ``"reported": false`` over a producer reporting four GPU fields every
    iteration — and the page said *the loop published no held/busy seconds*,
    which was a false statement about the producer, aimed at the wrong repo.

    A hand-built fixture proves the reader is self-consistent. Only a recording
    proves it reads the thing that exists.
    """

    def test_the_recording_is_this_contract_and_carries_gpu_seconds(self):
        """Guards the fixture itself: a recording emptied of the field under
        test would make every assertion below pass for the wrong reason."""
        sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(sample["schema"], loop_status.STATUS_SCHEMA)
        self.assertTrue(sample.get("gpu"), "the recording carries no gpu map")
        self.assertTrue(
            set(sample["gpu"]) & set(loop_status.HELD_KEYS + loop_status.BUSY_KEYS),
            "the recording no longer carries any key this reader knows — "
            "re-record it and widen HELD_KEYS/BUSY_KEYS rather than deleting "
            "this assertion")

    def test_the_gpu_panel_is_not_dark_over_the_producers_own_body(self):
        self.write(recorded())
        gpu = S.loop_payload()["derived"]["gpu"]
        self.assertTrue(gpu["reported"],
                        f"GPU unreported over the real producer: {gpu}")
        self.assertIsNotNone(gpu["busy_pct"])
        self.assertIsNone(gpu["unreported_reason"])

    def test_the_derived_idle_share_agrees_with_the_producers_own_fold(self):
        """Cross-checked against a field the reader never looks at.

        ``idle_fraction_while_claimed`` is computed independently by the
        producer. If the reader picked up the wrong pair of keys but they
        happened to be numbers, ``reported`` would still be true and the panel
        would show a confident wrong percentage. This is the assertion that
        catches that.
        """
        sample = recorded()
        self.write(sample)
        gpu = S.loop_payload()["derived"]["gpu"]
        producer_busy_pct = 100.0 * (1.0 - sample["gpu"]["idle_fraction_while_claimed"])
        self.assertAlmostEqual(gpu["busy_pct"], producer_busy_pct, places=1)
        self.assertAlmostEqual(gpu["idle_s"],
                               sample["gpu"]["gpu_seconds_idle_while_claimed"],
                               places=0)

    def test_an_unknown_dialect_blames_the_READER_not_the_producer(self):
        """"The loop published no held/busy seconds" is a claim about the
        producer. When the loop published four of them under names this reader
        does not know, that claim is false and points the investigation at the
        wrong repository."""
        self.write(body(gpu={"joules_per_token": 3.0, "clock_mhz": 1700}))
        gpu = S.loop_payload()["derived"]["gpu"]
        self.assertFalse(gpu["reported"])
        self.assertIn("READER defect", gpu["unreported_reason"])
        self.assertIn("joules_per_token", gpu["unreported_reason"])

    def test_no_gpu_map_at_all_blames_nobody(self):
        self.write(body(gpu={}))
        gpu = S.loop_payload()["derived"]["gpu"]
        self.assertFalse(gpu["reported"])
        self.assertIn("no gpu map at all", gpu["unreported_reason"])
        self.assertNotIn("READER", gpu["unreported_reason"])

    def test_a_half_reported_map_is_neither_of_the_other_two(self):
        self.write(body(gpu={"claim_held_s": 900.0}))
        gpu = S.loop_payload()["derived"]["gpu"]
        self.assertFalse(gpu["reported"])
        self.assertIn("busy", gpu["unreported_reason"])
        self.assertNotIn("READER", gpu["unreported_reason"])

    def test_the_recording_also_exercises_the_rest_of_the_payload(self):
        """Not a GPU-only recording: the dispositions, hotspots and identity the
        page renders come from the same body."""
        self.write(recorded())
        payload = S.loop_payload()
        self.assertEqual(payload["freshness_state"], loop_status.STATE_FRESH)
        self.assertTrue(payload["loop"]["dispositions"])
        self.assertTrue(payload["loop"]["hotspots"])
        self.assertGreaterEqual(payload["derived"]["negatives"], 1)


if __name__ == "__main__":
    unittest.main()
