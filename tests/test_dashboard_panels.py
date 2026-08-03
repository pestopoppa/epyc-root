"""AK6 operator surface — the consumer half.

Covers ``dashboard/panels.py`` (the SSOT panel→producer registry, the per-panel
freshness envelope, the transport watchdog) and the parts of
``dashboard/server.py`` that feed them.

THE SCAR THESE TESTS EXIST FOR, quoted from
``handoffs/active/autokernel-research-loop.md``:

    Today's ``/kernel`` page is ABSENCE-TOLERANT OVER A MISSING DIRECTORY — it
    renders clean when its producer is dead, which is the exact shape of AutoPilot
    dying at trial 1302 and staying dead ~23 HOURS with every dashboard green.

Every guard below has a COMPLIANT-PATH CONTROL beside it, proving the guard does
not forbid its own legitimate idiom: an empty-but-reported panel is still allowed
to be empty, a producer that declares itself stopped is still allowed to be
silent, and the supervisor's transport probe is still allowed to say ok.

NO PROCESS IS STARTED. Payload functions are called directly and fed fixtures, the
way ``tests/test_dashboard_activity.py`` already does.
Run: ``pytest tests/test_dashboard_panels.py`` from ``/mnt/raid0/llm/epyc-root``.
"""
import importlib
import json
import os
import re
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard import freshness, panels, server


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


_NOW_DT = datetime.now(timezone.utc)
_NOW = _NOW_DT.timestamp()
_DAY = 86400.0
_HOUR = 3600.0


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
_V2_SECTIONS = ("campaign", "champion", "backend_standing", "headroom",
                "blocking_conditions", "resource_claims", "release_package")


def _v2_doc(*, produced_at, observed=("campaign",), stopped=False, seq=17,
            exported_at=None):
    """A minimal but shape-faithful contract-v2 document.

    Mirrors what ``autokernel.surface.dashboard_contract.build_contract`` emits:
    seven mandatory sections each carrying a ``status``, ``produced_at`` derived
    from the observed liveness sections, ``generated_at`` equal to it, and an
    ``exported_at`` wall clock that is deliberately NOT a freshness source.
    """
    sections = {}
    for name in _V2_SECTIONS:
        if name in observed:
            sec = {"status": "observed", "as_of": produced_at}
            if name == "campaign":
                sec.update({"campaign_id": "ak-demo", "state": "EVALUATING",
                            "seq": seq, "stopped": stopped})
            sections[name] = sec
        else:
            sections[name] = {"status": "not_reported", "as_of": None,
                              "reason": f"{name} owner did not report"}
    unreported = sorted(n for n in _V2_SECTIONS if n not in observed)
    return {
        "schema": server.KERNEL_SCHEMA_V2,
        "contract_version": 2,
        "campaign_id": "ak-demo",
        "produced_at": produced_at,
        "generated_at": produced_at,
        "exported_at": exported_at or _iso(_NOW_DT),
        "producer": {"module_id": "autokernel.surface.dashboard_contract/v2",
                     "run": {"campaign_id": "ak-demo", "controller_seq": seq,
                             "controller_state": "EVALUATING",
                             "ledger_receipt": "sha256:deadbeef"}},
        "sections": sections,
        "degraded": bool(unreported),
        "unreported_sections": unreported,
        "observation_notice": "OBSERVATION only.",
    }


class _KernelFile:
    """Point ``server.KERNEL_DASHBOARD_JSON`` at a temp file for one block."""

    def __init__(self, content):
        self.content = content

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "kernel_dashboard.json"
        if self.content is not None:
            path.write_text(self.content if isinstance(self.content, str)
                            else json.dumps(self.content), encoding="utf-8")
        self._orig = server.KERNEL_DASHBOARD_JSON
        server.KERNEL_DASHBOARD_JSON = path
        server._watchdog_state.clear()
        return path

    def __exit__(self, *exc):
        server.KERNEL_DASHBOARD_JSON = self._orig
        server._watchdog_state.clear()
        self._tmp.cleanup()
        return False


def _fake_hub(name="fake_hub", *, funcs=None, routes=None, extra_funcs=(),
              drop=()):
    """A synthetic module shaped like the hub, for the registry's NEGATIVE controls.

    Built from the real registry so the controls stay honest when a panel is added:
    they mutate a faithful copy rather than restating one.
    """
    mod = types.ModuleType(name)
    if funcs is None:
        funcs = [s.payload_func for s in panels.PANELS.values()]
    funcs = [f for f in funcs if f not in drop] + list(extra_funcs)
    exec("\n".join(f"def {f}(*a, **k):\n    return {{}}\n" for f in funcs),
         mod.__dict__)
    if routes is None:
        routes = {s.route: s.payload_func for s in panels.PANELS.values()
                  if s.route and s.payload_func not in drop}
    mod.API_ROUTES = {route: getattr(mod, fn) for route, fn in routes.items()}
    return mod


# --------------------------------------------------------------------------- #
# 1. The SSOT panel→producer registry
# --------------------------------------------------------------------------- #
class RegistryTotalityTest(unittest.TestCase):
    """THE test that matters: it FAILS when a panel has no registered source.

    Enumeration is REFLECTIVE — ``discover_payload_functions`` reads the hub's own
    module namespace and ``registry_gaps`` reads its route tables — so the check
    cannot go stale the way a hand-maintained roster does. A roster someone forgets
    to extend is the same defect the registry exists to fix, one level up.
    """

    def test_the_real_hub_has_no_registry_gaps(self):
        gaps = panels.registry_gaps(server)
        self.assertEqual(
            {k: v for k, v in gaps.items() if v}, {},
            f"dashboard/panels.py is not total over dashboard/server.py: {gaps}")

    def test_every_payload_function_is_discovered(self):
        found = panels.discover_payload_functions(server)
        self.assertEqual(found, {s.payload_func for s in panels.PANELS.values()})
        # Non-vacuous: discovery actually found things.
        self.assertGreaterEqual(len(found), 8)

    # ---- negative controls: each gap shape is detected --------------------- #
    def test_an_unregistered_panel_is_a_gap(self):
        gaps = panels.registry_gaps(_fake_hub(extra_funcs=("ghost_payload",)))
        self.assertEqual(gaps["unregistered_payload_functions"], ["ghost_payload"])

    def test_a_registered_panel_whose_function_vanished_is_a_gap(self):
        gaps = panels.registry_gaps(_fake_hub(drop=("kernel_payload",)))
        self.assertEqual(gaps["registered_without_function"], ["kernel_payload"])
        self.assertTrue(any("kernel" in m for m in gaps["route_mismatch"]))

    def test_a_route_bound_to_the_wrong_payload_is_a_gap(self):
        routes = {s.route: s.payload_func for s in panels.PANELS.values() if s.route}
        routes["/api/kernel"] = "board_payload"   # wrong producer behind the route
        gaps = panels.registry_gaps(_fake_hub(routes=routes))
        self.assertTrue(any("/api/kernel" in m for m in gaps["route_mismatch"]),
                        gaps["route_mismatch"])

    def test_a_served_route_with_no_registered_panel_is_a_gap(self):
        routes = {s.route: s.payload_func for s in panels.PANELS.values() if s.route}
        routes["/api/ghost"] = "kernel_payload"
        gaps = panels.registry_gaps(_fake_hub(routes=routes))
        self.assertEqual(gaps["unregistered_routes"], ["/api/ghost"])

    def test_the_baseline_fake_hub_is_clean(self):
        """COMPLIANT-PATH CONTROL: the fixture the negative controls mutate is
        itself gap-free, so each failure above is caused by the mutation and not
        by the fixture."""
        gaps = panels.registry_gaps(_fake_hub())
        self.assertEqual({k: v for k, v in gaps.items() if v}, {})

    def test_a_panel_that_loses_its_registry_entry_makes_the_hub_refuse_to_START(self):
        """The other direction is enforced HARDER than a test: the hub reads every
        threshold and builds every envelope through ``panels.source()``, so a panel
        with no registered producer raises at import instead of serving a card
        nobody can vouch for. (Verified by mutation: renaming the ``kernel`` entry
        makes ``import dashboard.server`` raise this error by name.)"""
        with self.assertRaises(panels.RegistryError) as ctx:
            panels.source("no_such_panel")
        self.assertIn("no_such_panel", str(ctx.exception))
        self.assertIn("nobody can vouch", str(ctx.exception))

    def test_the_hub_never_subscripts_the_registry_directly(self):
        """Bite for the guard above: a bare ``panels.PANELS[...]`` would bring the
        opaque ``KeyError`` back and take the whole module down at collection with
        no diagnosis."""
        import inspect
        self.assertNotIn("panels.PANELS[", inspect.getsource(server))
        self.assertIn("panels.source(", inspect.getsource(server))

    def test_a_registered_panel_resolves(self):
        """COMPLIANT-PATH CONTROL: the refusing lookup still resolves real panels."""
        self.assertIs(panels.source("kernel"), panels.PANELS["kernel"])

    def test_discovery_ignores_an_imported_payload_function(self):
        """A payload function IMPORTED from the hub is not a panel this module
        serves; counting it would register producers that live elsewhere."""
        mod = types.ModuleType("borrower")
        mod.kernel_payload = server.kernel_payload
        self.assertEqual(panels.discover_payload_functions(mod), set())


class RegistryContentTest(unittest.TestCase):
    def test_every_panel_declares_what_its_absence_means(self):
        for name, src in panels.PANELS.items():
            with self.subTest(panel=name):
                self.assertTrue(src.absence_means.strip(), name)
                self.assertGreater(len(src.absence_means), 40,
                                   f"{name}: absence_means must be a sentence an "
                                   "operator can act on, not a label")

    def test_a_panel_without_an_absence_meaning_cannot_be_constructed(self):
        with self.assertRaises(panels.RegistryError):
            panels.PanelSource(panel="x", kind=panels.KIND_ARTIFACT,
                               payload_func="x_payload", producer="p",
                               producer_repo="r", evidence="e",
                               timestamp_field="t", absence_means="   ",
                               warn_s=1, stale_s=2)

    def test_a_file_backed_panel_without_thresholds_cannot_be_constructed(self):
        with self.assertRaises(panels.RegistryError):
            panels.PanelSource(panel="x", kind=panels.KIND_ARTIFACT,
                               payload_func="x_payload", producer="p",
                               producer_repo="r", evidence="e",
                               timestamp_field="t",
                               absence_means="a" * 50)

    def test_a_watched_panel_without_a_silence_budget_cannot_be_constructed(self):
        with self.assertRaises(panels.RegistryError):
            panels.PanelSource(panel="x", kind=panels.KIND_ARTIFACT,
                               payload_func="x_payload", producer="p",
                               producer_repo="r", evidence="e",
                               timestamp_field="t", absence_means="a" * 50,
                               warn_s=1, stale_s=2, watched=True)

    def test_a_well_formed_entry_constructs(self):
        """COMPLIANT-PATH CONTROL for the three refusals above."""
        src = panels.PanelSource(panel="x", kind=panels.KIND_ARTIFACT,
                                 payload_func="x_payload", producer="p",
                                 producer_repo="r", evidence="e",
                                 timestamp_field="t", absence_means="a" * 50,
                                 warn_s=1, stale_s=2, silent_after_s=2,
                                 watched=True)
        self.assertEqual(src.panel, "x")

    def test_server_thresholds_are_read_from_the_registry(self):
        self.assertEqual(server._KERNEL_WARN_S, panels.PANELS["kernel"].warn_s)
        self.assertEqual(server._KERNEL_STALE_S, panels.PANELS["kernel"].stale_s)
        self.assertEqual(server._TIMELINE_WARN_S, panels.PANELS["timeline"].warn_s)
        self.assertEqual(server._OUTCOME_STALE_S, panels.PANELS["outcome"].stale_s)
        self.assertEqual(server._HEARTBEAT_STALE_S, panels.PANELS["bus"].stale_s)

    def test_there_is_exactly_one_age_classifier(self):
        self.assertIs(panels.classify_age, freshness.classify_age)


# --------------------------------------------------------------------------- #
# 2. Absent vs empty — the distinction the scar destroyed
# --------------------------------------------------------------------------- #
class AbsentVsEmptyTest(unittest.TestCase):
    # Looked up per test, never at class-body time: a registry regression must
    # produce a NAMED failure in RegistryTotalityTest, not an inscrutable
    # collection error that takes the whole module down before it can say why.
    @property
    def SRC(self):
        return panels.PANELS["kernel"]

    def test_reported_and_empty_is_structurally_not_absent(self):
        empty = panels.envelope(self.SRC, panels.Observation(
            artifact_present=True, timestamp=_NOW - 60, source="produced_at",
            populated=False), now=_NOW)
        gone = panels.envelope(self.SRC, panels.absent(
            self.SRC, "the producer wrote nothing"), now=_NOW)

        self.assertEqual(empty["reporting"], panels.REPORTING_OBSERVED)
        self.assertEqual(empty["content"], panels.CONTENT_EMPTY)
        self.assertTrue(empty["artifact_present"])
        self.assertEqual(empty["staleness_class"], "fresh")

        self.assertEqual(gone["reporting"], panels.REPORTING_ABSENT)
        self.assertEqual(gone["content"], panels.CONTENT_UNKNOWN)
        self.assertFalse(gone["artifact_present"])
        self.assertEqual(gone["staleness_class"], "missing")

        # Three independent fields differ. A renderer cannot show one as the other.
        for key in ("reporting", "content", "artifact_present"):
            self.assertNotEqual(empty[key], gone[key], key)

    def test_absence_never_reports_content_as_empty(self):
        """Bite: a reader that carelessly passes ``populated=False`` alongside an
        absent artifact must still not produce 'the producer said nothing'."""
        env = panels.envelope(self.SRC, panels.Observation(
            artifact_present=False, timestamp=None, populated=False), now=_NOW)
        self.assertEqual(env["content"], panels.CONTENT_UNKNOWN)

    def test_absence_carries_its_declared_meaning(self):
        env = panels.envelope(self.SRC, panels.absent(self.SRC, "gone"), now=_NOW)
        self.assertEqual(env["absence_means"], self.SRC.absence_means)

    def test_an_observed_panel_carries_no_absence_meaning(self):
        """COMPLIANT-PATH CONTROL: absence prose only travels with an absence."""
        env = panels.envelope(self.SRC, panels.Observation(
            artifact_present=True, timestamp=_NOW, source="produced_at",
            populated=True), now=_NOW)
        self.assertNotIn("absence_means", env)

    def test_an_unexplained_absence_cannot_be_constructed(self):
        with self.assertRaises(panels.RegistryError):
            panels.absent(self.SRC, "")

    def test_a_document_that_exists_but_reports_nothing_is_its_own_state(self):
        """The third state: an exporter ran, and every owner behind it was dead.

        ``artifact_present`` is True and ``reporting`` is absent — neither 'no
        file' nor 'reported and empty'.
        """
        env = panels.envelope(self.SRC, panels.Observation(
            artifact_present=True, timestamp=None, source="produced_at",
            detail="every section not_reported",
            unreported=tuple(_V2_SECTIONS)), now=_NOW)
        self.assertTrue(env["artifact_present"])
        self.assertEqual(env["reporting"], panels.REPORTING_ABSENT)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_NO_TIMESTAMP)
        self.assertEqual(sorted(env["unreported"]), sorted(_V2_SECTIONS))


# --------------------------------------------------------------------------- #
# 3. The transport watchdog
# --------------------------------------------------------------------------- #
class WatchdogTest(unittest.TestCase):
    """The AutoPilot-at-trial-1302 detector.

    Arm 1 (age): the newest SEMANTIC timestamp stopped advancing.
    Arm 2 (watermark): timestamps keep advancing, progress does not.
    """

    @property
    def OUT(self):
        return panels.PANELS["outcome"]

    def test_never_reported_and_stopped_reporting_are_different_verdicts(self):
        never = panels.envelope(self.OUT, panels.absent(self.OUT, "no export"),
                                now=_NOW)
        stopped = panels.envelope(self.OUT, panels.Observation(
            artifact_present=True, timestamp=_NOW - 23 * _HOUR,
            source="generated_at", populated=True, watermark="trial:1302"),
            now=_NOW)
        self.assertEqual(never["watchdog"]["state"], panels.WATCHDOG_NEVER)
        self.assertEqual(stopped["watchdog"]["state"], panels.WATCHDOG_STOPPED)
        self.assertEqual(stopped["reporting"], panels.REPORTING_SILENT)
        # The 1302 shape: populated, plausible, and dead.
        self.assertEqual(stopped["content"], panels.CONTENT_POPULATED)
        self.assertIn("1302", stopped["watchdog"]["reason"] + "trial:1302")

    def test_a_reporting_producer_is_ok(self):
        """COMPLIANT-PATH CONTROL: a producer inside its silence budget is ok."""
        env = panels.envelope(self.OUT, panels.Observation(
            artifact_present=True, timestamp=_NOW - 60, source="generated_at",
            populated=True, watermark="trial:1400"), now=_NOW)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_OK)
        self.assertEqual(env["reporting"], panels.REPORTING_OBSERVED)

    def test_watermark_arm_fires_on_fresh_timestamps_with_frozen_progress(self):
        state: dict = {}
        t0 = _NOW - 8 * _HOUR
        panels.observe_watermark(state, "outcome", "trial:1302", now=t0)
        panels.observe_watermark(state, "outcome", "trial:1302", now=_NOW)
        env = panels.envelope(self.OUT, panels.Observation(
            artifact_present=True, timestamp=_NOW - 30, source="generated_at",
            populated=True, watermark="trial:1302"),
            now=_NOW, watchdog_state=state)
        # Timestamp is 30 s old: the age arm sees nothing wrong.
        self.assertEqual(env["staleness_class"], "fresh")
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_NOT_ADVANCING)
        self.assertEqual(env["reporting"], panels.REPORTING_SILENT)

    def test_watermark_advance_resets_the_clock(self):
        """COMPLIANT-PATH CONTROL: a producer that IS advancing never trips arm 2."""
        state: dict = {}
        panels.observe_watermark(state, "outcome", "trial:1302", now=_NOW - 8 * _HOUR)
        panels.observe_watermark(state, "outcome", "trial:1303", now=_NOW)
        env = panels.envelope(self.OUT, panels.Observation(
            artifact_present=True, timestamp=_NOW - 30, source="generated_at",
            populated=True, watermark="trial:1303"),
            now=_NOW, watchdog_state=state)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_OK)

    def test_an_unreadable_watermark_is_not_pinned_to_a_stale_one(self):
        state = {"outcome": {"watermark": "trial:1302", "first_seen": _NOW - _DAY,
                             "last_seen": _NOW - _DAY, "polls": 9}}
        panels.observe_watermark(state, "outcome", None, now=_NOW)
        self.assertNotIn("outcome", state)

    def test_a_declared_idle_producer_may_be_silent(self):
        """COMPLIANT-PATH CONTROL: the producer's own 'I have stopped' is honoured.

        A finished campaign is not a dead one. Only the producer may say so — the
        hub never infers idleness.
        """
        env = panels.envelope(panels.PANELS["kernel"], panels.Observation(
            artifact_present=True, timestamp=_NOW - 30 * _DAY, source="produced_at",
            populated=True, producer_idle=True, watermark="ak-demo:17"), now=_NOW)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_IDLE)
        self.assertEqual(env["reporting"], panels.REPORTING_OBSERVED)
        self.assertEqual(panels.panel_verdict(env)[0], panels.STATUS_OK)

    def test_the_same_silence_without_the_idle_declaration_is_an_alarm(self):
        """Bite for the control above: idleness must be DECLARED, never assumed."""
        env = panels.envelope(panels.PANELS["kernel"], panels.Observation(
            artifact_present=True, timestamp=_NOW - 30 * _DAY, source="produced_at",
            populated=True, producer_idle=False, watermark="ak-demo:17"), now=_NOW)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_STOPPED)
        self.assertEqual(panels.panel_verdict(env)[0], panels.STATUS_DEGRADED)

    def test_an_unwatched_panel_says_so_rather_than_saying_ok(self):
        env = panels.envelope(panels.PANELS["bus"], panels.Observation(
            artifact_present=True, timestamp=_NOW - 10 * _DAY,
            source="heartbeats/*.json mtime (freshest)", populated=True), now=_NOW)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_UNWATCHED)


# --------------------------------------------------------------------------- #
# 4. The /kernel contract: v2 read, v1 kept readable
# --------------------------------------------------------------------------- #
class KernelContractV2Test(unittest.TestCase):
    def test_v2_is_dated_by_produced_at(self):
        doc = _v2_doc(produced_at=_iso(_NOW_DT - timedelta(hours=2)),
                      observed=_V2_SECTIONS)
        with _KernelFile(doc):
            out = server.kernel_payload()
        self.assertEqual(out["_contract_version"], "v2")
        fr = out["_freshness"]
        self.assertEqual(fr["source"], "produced_at")
        self.assertEqual(fr["staleness_class"], "fresh")
        self.assertEqual(fr["reporting"], panels.REPORTING_OBSERVED)
        self.assertEqual(fr["content"], panels.CONTENT_POPULATED)
        self.assertEqual(fr["unreported"], [])

    def test_exported_at_is_not_a_freshness_source(self):
        """A file rewritten NOW whose loop last advanced a month ago is STALE.

        This is the producer's structural guarantee arriving intact at the
        consumer: nothing the exporter does may move ``produced_at``.
        """
        doc = _v2_doc(produced_at=_iso(_NOW_DT - timedelta(days=30)),
                      observed=_V2_SECTIONS, exported_at=_iso(_NOW_DT))
        with _KernelFile(doc):
            fr = server.kernel_payload()["_freshness"]
        self.assertEqual(fr["staleness_class"], "stale")
        self.assertEqual(fr["watchdog"]["state"], panels.WATCHDOG_STOPPED)

    def test_a_v2_document_with_no_owner_reporting_does_not_render_clean(self):
        doc = _v2_doc(produced_at=None, observed=())
        with _KernelFile(doc):
            out = server.kernel_payload()
        fr = out["_freshness"]
        self.assertTrue(fr["artifact_present"])          # the exporter ran
        self.assertEqual(fr["reporting"], panels.REPORTING_ABSENT)  # nobody reported
        self.assertEqual(fr["staleness_class"], "missing")
        self.assertEqual(sorted(fr["unreported"]), sorted(_V2_SECTIONS))
        self.assertIn("absence_means", fr)

    def test_a_partially_unreported_v2_document_names_the_missing_owners(self):
        doc = _v2_doc(produced_at=_iso(_NOW_DT), observed=("campaign", "champion"))
        with _KernelFile(doc):
            fr = server.kernel_payload()["_freshness"]
        self.assertEqual(fr["reporting"], panels.REPORTING_OBSERVED)
        self.assertEqual(fr["staleness_class"], "fresh")
        # Fresh AND incomplete: the panel may not read clean.
        self.assertIn("release_package", fr["unreported"])
        self.assertEqual(panels.panel_verdict(fr)[0], panels.STATUS_ABSENT)

    def test_a_fully_reported_v2_document_reads_clean(self):
        """COMPLIANT-PATH CONTROL for the test above."""
        doc = _v2_doc(produced_at=_iso(_NOW_DT), observed=_V2_SECTIONS)
        with _KernelFile(doc):
            fr = server.kernel_payload()["_freshness"]
        self.assertEqual(panels.panel_verdict(fr)[0], panels.STATUS_OK)

    def test_a_stopped_controller_reads_idle_not_dead(self):
        doc = _v2_doc(produced_at=_iso(_NOW_DT - timedelta(days=30)),
                      observed=_V2_SECTIONS, stopped=True)
        with _KernelFile(doc):
            fr = server.kernel_payload()["_freshness"]
        self.assertEqual(fr["watchdog"]["state"], panels.WATCHDOG_IDLE)

    def test_the_watermark_is_the_controller_sequence(self):
        doc = _v2_doc(produced_at=_iso(_NOW_DT), observed=_V2_SECTIONS, seq=42)
        obs = server._kernel_observation(doc)
        self.assertEqual(obs.watermark, "ak-demo:42")

    def test_v1_generated_at_spelling_is_carried_by_v2(self):
        """A v1-only reader pointed at a v2 file must get the DERIVED timestamp,
        not the export time — otherwise an old consumer classifies a dead loop as
        fresh. The producer guarantees it; this asserts the consumer benefits."""
        doc = _v2_doc(produced_at=_iso(_NOW_DT - timedelta(days=30)),
                      observed=_V2_SECTIONS, exported_at=_iso(_NOW_DT))
        self.assertEqual(doc["generated_at"], doc["produced_at"])


class KernelContractV1Test(unittest.TestCase):
    def test_legacy_unlabelled_v1_is_still_read(self):
        doc = {"db_present": True, "runs": [{"ts": _iso(_NOW_DT - timedelta(hours=2))}],
               "totals": {"runs": 1}, "generated_at": _iso(_NOW_DT)}
        with _KernelFile(doc):
            out = server.kernel_payload()
        self.assertEqual(out["_contract_version"], "v1")
        self.assertEqual(out["_freshness"]["source"], "runs[].ts")
        self.assertEqual(out["_freshness"]["staleness_class"], "fresh")

    def test_an_explicit_v1_label_is_read_as_v1(self):
        doc = {"schema": server.KERNEL_SCHEMA_V1, "runs": [], "totals": {},
               "generated_at": _iso(_NOW_DT)}
        self.assertEqual(server.kernel_contract_version(doc), "v1")

    def test_an_unknown_schema_is_refused_not_coerced_to_v1(self):
        """Bite: coercion would read this as a FRESH v1 document. Refusal makes it
        undated, which every consumer renders as absent."""
        doc = {"schema": "epyc.autokernel.kernel_dashboard.v9",
               "runs": [{"ts": _iso(_NOW_DT)}], "generated_at": _iso(_NOW_DT)}
        self.assertEqual(server.kernel_contract_version(doc), "unknown")
        with _KernelFile(doc):
            fr = server.kernel_payload()["_freshness"]
        self.assertEqual(fr["staleness_class"], "missing")
        self.assertEqual(fr["reporting"], panels.REPORTING_ABSENT)
        self.assertIn("Refusing to guess", fr["detail"])


class KernelAbsenceOnTheWireTest(unittest.TestCase):
    def test_a_missing_export_yields_nulls_not_empty_lists(self):
        """``[]`` means 'the producer reported and there is nothing'; ``null``
        means 'no producer reported'. Conflating them is the scar."""
        with _KernelFile(None):
            out = server.kernel_payload()
        for key in ("runs", "pareto", "best_per_model", "totals"):
            self.assertIsNone(out[key], key)
        self.assertIsNone(out["_contract_version"])
        self.assertTrue(out["degraded"])
        self.assertIn("UNSOURCED", out["observation_notice"])
        self.assertEqual(out["_freshness"]["reporting"], panels.REPORTING_ABSENT)
        self.assertFalse(out["_freshness"]["artifact_present"])

    def test_the_deployed_page_still_tolerates_the_absence(self):
        """COMPLIANT-PATH CONTROL: absence tolerance is REQUIRED, not removed.

        ``static/kernel.html`` reads every one of these through ``x || []`` /
        ``x || {}``, so a null degrades to the same empty render it always did —
        the page must not crash on a dead producer. Only the wire changed.
        """
        with _KernelFile(None):
            out = server.kernel_payload()
        self.assertEqual(out.get("runs") or [], [])
        self.assertEqual(out.get("totals") or {}, {})
        json.dumps(out)  # serialisable; the route cannot 500

    def test_corrupt_json_is_absence_not_a_crash(self):
        with _KernelFile("{not json"):
            out = server.kernel_payload()
        self.assertIn("error", out)
        self.assertEqual(out["_freshness"]["reporting"], panels.REPORTING_ABSENT)

    def test_the_default_path_is_durable_not_scratch(self):
        env = dict(os.environ)
        env.pop("KERNEL_DASHBOARD_JSON", None)
        old = os.environ.pop("KERNEL_DASHBOARD_JSON", None)
        try:
            reloaded = importlib.reload(server)
            default = str(reloaded.KERNEL_DASHBOARD_JSON)
        finally:
            if old is not None:
                os.environ["KERNEL_DASHBOARD_JSON"] = old
            importlib.reload(server)
        self.assertEqual(default,
                         "/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json")
        # The three defects of the old default, asserted individually.
        self.assertNotIn("/mnt/raid0/llm/tmp", default)   # ephemeral sweep root
        self.assertNotIn("mi210-build", default)          # build scratch tree
        self.assertTrue(default.startswith("/mnt/raid0/"))  # survives reboots

    def test_the_env_override_still_works(self):
        """COMPLIANT-PATH CONTROL: the durable default did not remove testability."""
        os.environ["KERNEL_DASHBOARD_JSON"] = "/tmp/does-not-exist/k.json"
        try:
            reloaded = importlib.reload(server)
            self.assertEqual(str(reloaded.KERNEL_DASHBOARD_JSON),
                             "/tmp/does-not-exist/k.json")
        finally:
            os.environ.pop("KERNEL_DASHBOARD_JSON", None)
            importlib.reload(server)

    def test_the_hub_names_the_producers_schema_strings_exactly(self):
        """The hub is stdlib-only and never imports the producer's package, so the
        schema strings are literals here. They are pinned against the producer's
        own constants when that repo is importable, and asserted as literals when
        it is not — this test never skips."""
        self.assertEqual(server.KERNEL_SCHEMA_V1,
                         "epyc.autokernel.kernel_dashboard.v1")
        self.assertEqual(server.KERNEL_SCHEMA_V2,
                         "epyc.autokernel.kernel_dashboard.v2")
        self.assertEqual(server.KERNEL_SECTION_OBSERVED, "observed")
        producer = Path("/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd")
        schemas_py = producer / "autokernel" / "schemas.py"
        if schemas_py.is_file():
            text = schemas_py.read_text(encoding="utf-8")
            self.assertIn(f'SCHEMA_KERNEL_DASHBOARD_V2 = "{server.KERNEL_SCHEMA_V2}"',
                          text)
            self.assertIn(f'SECTION_OBSERVED = "{server.KERNEL_SECTION_OBSERVED}"',
                          text)


# --------------------------------------------------------------------------- #
# 5. The /health fold
# --------------------------------------------------------------------------- #
def _env(panel, **kw):
    kw.setdefault("artifact_present", True)
    return panels.envelope(panels.PANELS[panel], panels.Observation(**kw), now=_NOW)


class FoldTest(unittest.TestCase):
    def _all_fine(self):
        """A TOTAL, healthy set of envelopes — one per registered panel.

        Total because ``fold``'s universe is the registry: a fold over a SUBSET
        used to return ``ok`` (``fold({})`` was green), so a panel that dropped
        out of ``panel_envelopes()`` would have been subtracted from the verdict
        rather than named. Building the fixture by iterating ``PANELS`` also means
        a new panel joins these tests automatically instead of silently sitting
        outside them.
        """
        envs = {}
        for name, src in panels.PANELS.items():
            if src.kind in panels.LIVE_KINDS:
                envs[name] = _env(name, timestamp=None, source="live-scan",
                                  populated=True)
            else:
                envs[name] = _env(name, timestamp=_NOW - 60,
                                  source=src.timestamp_field, populated=True,
                                  watermark=f"{name}:1")
        return envs

    def test_a_healthy_board_is_ok_and_names_nothing(self):
        """COMPLIANT-PATH CONTROL: the fold is capable of saying ok."""
        out = panels.fold(self._all_fine())
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertEqual(out["attention"], [])
        self.assertEqual(out["absent"], [])

    def test_the_fold_is_never_green_over_a_dead_producer(self):
        envs = self._all_fine()
        envs["kernel"] = _env("kernel", artifact_present=False, timestamp=None)
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_ABSENT)
        self.assertEqual(out["worst"]["panel"], "kernel")
        self.assertIn("NOBODY IS REPORTING", out["worst"]["why"])
        self.assertEqual([a["panel"] for a in out["absent"]], ["kernel"])

    def test_a_watchdog_alarm_on_a_gating_panel_degrades(self):
        envs = self._all_fine()
        envs["kernel"] = _env("kernel", timestamp=_NOW - 30 * _DAY,
                              source="produced_at", populated=True,
                              watermark="ak:1")
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_DEGRADED)
        self.assertEqual(out["worst"]["panel"], "kernel")
        self.assertEqual(out["worst"]["watchdog"], panels.WATCHDOG_STOPPED)
        self.assertIn("stopped", out["worst"]["why"])

    def test_the_fold_names_which_panel_and_why(self):
        envs = self._all_fine()
        envs["timeline"] = _env("timeline", timestamp=_NOW - 30 * _DAY,
                                source="generated_at", populated=True)
        out = panels.fold(envs)
        self.assertEqual(out["worst"]["panel"], "timeline")
        self.assertTrue(out["worst"]["why"].startswith("timeline:"))
        self.assertTrue(out["worst"]["gates_health"])

    def test_a_benign_absence_is_loud_but_not_a_health_verdict(self):
        """``outcome`` has no exporter yet, so its absence is DECLARED benign — it
        must still appear in ``absent`` and ``attention``. Loud, not degraded."""
        envs = self._all_fine()
        envs["outcome"] = _env("outcome", artifact_present=False, timestamp=None)
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertEqual([a["panel"] for a in out["absent"]], ["outcome"])
        self.assertFalse(out["absent"][0]["anomalous"])
        self.assertIn("outcome", [a["panel"] for a in out["attention"]])

    def test_a_watchdog_alarm_gates_even_on_a_non_gating_panel(self):
        """THE trial-1302 shape, on the panel the outage is named after.

        ``outcome`` carries ``gates_health=False`` because its ABSENCE (no
        exporter exists yet) and its STALENESS must not colour the fold. That is
        not a licence to be dead quietly: the fold used to answer ``status: ok``
        beside ``worst.watchdog: stopped_reporting`` — a green dashboard over an
        autopilot that had been dead 23 h, which is the outage verbatim.
        """
        envs = self._all_fine()
        envs["outcome"] = _env("outcome", timestamp=_NOW - 23 * _HOUR,
                               source="generated_at", populated=True,
                               watermark="trial:1302")
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_DEGRADED)
        self.assertEqual(out["worst"]["panel"], "outcome")
        self.assertFalse(out["worst"]["gates_health"])
        self.assertEqual(out["status_set_by"]["panel"], "outcome")
        self.assertIn("outcome", [a["panel"] for a in out["attention"]])

    def test_a_declared_pause_is_still_allowed_to_be_silent(self):
        """COMPLIANT-PATH CONTROL for the test above — the one that stops this
        watchdog from being the kind that gets turned off.

        A Phase-0 stop-loss pause is a legitimate long silence. It stays green
        when the loop DECLARES it, exactly as the AutoKernel controller declares
        ``sections.campaign.stopped``. Only the producer may say so.
        """
        envs = self._all_fine()
        envs["outcome"] = _env("outcome", timestamp=_NOW - 23 * _HOUR,
                               source="generated_at", populated=True,
                               watermark="trial:1302", producer_idle=True)
        out = panels.fold(envs)
        self.assertEqual(envs["outcome"]["watchdog"]["state"], panels.WATCHDOG_IDLE)
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertIsNone(out["status_set_by"])

    def test_an_unwatched_panels_silence_never_gates(self):
        """COMPLIANT-PATH CONTROL: 'this producer is allowed to be quiet' is
        spelled ``watched=False`` (``bus``/``queue``), and that still says
        ``unwatched`` rather than alarming."""
        envs = self._all_fine()
        envs["bus"] = _env("bus", timestamp=_NOW - 10 * _DAY,
                           source="heartbeats", populated=True)
        out = panels.fold(envs)
        self.assertEqual(envs["bus"]["watchdog"]["state"], panels.WATCHDOG_UNWATCHED)
        # bus is non-gating, so its staleness is surfaced without setting status.
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertIn("bus", [a["panel"] for a in out["attention"]])


class HealthPayloadFoldTest(unittest.TestCase):
    def test_health_payload_covers_every_registered_panel(self):
        h = server.health_payload()
        self.assertEqual(set(h["panels"]), set(panels.PANELS))

    def test_health_payload_keeps_its_backwards_compatible_aliases(self):
        h = server.health_payload()
        for key in ("board", "timeline", "kernel", "outcome"):
            self.assertIs(h[key], h["panels"][key])
            self.assertIn("staleness_class", h[key])

    def test_health_payload_status_is_three_valued(self):
        self.assertIn(server.health_payload()["status"], panels.STATUS_ORDER)

    def test_a_dead_kernel_producer_is_named_by_the_live_fold(self):
        with _KernelFile(None):
            h = server.health_payload()
        self.assertNotEqual(h["status"], panels.STATUS_OK)
        self.assertIn("kernel", [a["panel"] for a in h["absent"]])

    def test_a_live_kernel_producer_clears_it(self):
        """COMPLIANT-PATH CONTROL for the test above."""
        with _KernelFile(_v2_doc(produced_at=_iso(_NOW_DT), observed=_V2_SECTIONS)):
            h = server.health_payload()
        self.assertNotIn("kernel", [a["panel"] for a in h["absent"]])
        self.assertEqual(h["panels"]["kernel"]["reporting"],
                         panels.REPORTING_OBSERVED)


# --------------------------------------------------------------------------- #
# 6. The transport plane must stay separate from the producer plane
# --------------------------------------------------------------------------- #
#: hub_supervisor.sh line 100: ``*'"status"'*'ok'*) return 0 ;;``. Mirrored here
#: so a change to the hub's /health body that would make the supervisor start
#: killing the hub fails a test instead of a live service.
_SUPERVISOR_PATTERN = re.compile(r'"status".*ok', re.S)


class TransportPlaneTest(unittest.TestCase):
    def test_the_probe_stays_ok_when_every_producer_is_dead(self):
        with _KernelFile(None):
            body = json.dumps(server.transport_probe_payload())
        self.assertRegex(body, _SUPERVISOR_PATTERN)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_the_probe_is_not_the_fold(self):
        """Bite: wiring ``health_payload`` into ``/health`` fails here.

        The supervisor restarts the hub whenever the body stops matching
        ``"status"…ok``, so a dead AutoKernel producer would put the DASHBOARD
        into a restart loop — and restarting the dashboard cannot revive a
        producer in another repository.
        """
        probe = server.transport_probe_payload()
        self.assertEqual(probe["probe"], "transport")
        for key in ("worst", "panels", "attention", "absent"):
            self.assertNotIn(key, probe)
        self.assertEqual(probe["producer_health"], "/api/health")
        self.assertNotIn(server.TRANSPORT_PROBE_ROUTE, server.API_ROUTES)
        self.assertIs(server.API_ROUTES["/api/health"], server.health_payload)

    def test_the_probe_route_is_still_enumerated(self):
        """The exemption is DECLARED, not an omission: /health is in the registry
        and in a route table, so ``registry_gaps`` still sees it."""
        self.assertIn("/health", server.PROBE_ROUTES)
        self.assertEqual(panels.PANELS["transport_probe"].route, "/health")

    def test_the_fold_route_carries_the_verdict(self):
        """COMPLIANT-PATH CONTROL: producer health is not suppressed, it is moved."""
        h = server.API_ROUTES["/api/health"]()
        self.assertIn("worst", h)
        self.assertIn("panels", h)


# --------------------------------------------------------------------------- #
# 7. Routing tables stay the enumeration source
# --------------------------------------------------------------------------- #
class RouteTableTest(unittest.TestCase):
    def test_every_api_route_is_bound_to_its_registered_payload(self):
        for route, func in server.API_ROUTES.items():
            src = next(s for s in panels.PANELS.values() if s.route == route)
            self.assertEqual(func.__name__, src.payload_func, route)

    def test_the_detail_route_is_bound_without_an_adapter(self):
        self.assertIs(server.API_ROUTES_WITH_STATUS["/api/handoff_detail"],
                      server.detail_payload)

    def test_html_routes_are_disjoint_from_api_routes(self):
        self.assertEqual(set(server.HTML_ROUTES) & set(server.API_ROUTES), set())
        self.assertNotIn(server.TRANSPORT_PROBE_ROUTE, server.HTML_ROUTES)


if __name__ == "__main__":
    unittest.main()
