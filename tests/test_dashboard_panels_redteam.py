"""AK6 operator surface — ADVERSARIAL regression locks for the consumer half.

Companion to ``tests/test_dashboard_panels.py``. That suite proves the surface
does what it claims; this one is what survived an attempt to REFUTE those claims.
Every test here corresponds to a way the panel/health surface was found to render
CLEAN over a dead, broken or absent producer — the scar it exists to close:

    Today's ``/kernel`` page is ABSENCE-TOLERANT OVER A MISSING DIRECTORY — it
    renders clean when its producer is dead, which is the exact shape of AutoPilot
    dying at trial 1302 and staying dead ~23 HOURS with every dashboard green.

Each class states the ATTACK it locks out, the observed pre-fix behaviour (which
is the bite: revert the fix and the test reproduces exactly that), and carries a
COMPLIANT-PATH CONTROL proving the guard does not forbid its own idiom — a
watchdog that fires on a working system gets turned off, which is worse than no
watchdog.

NO PROCESS IS STARTED. Payload functions are called directly and fed fixtures.
Run: ``pytest tests/test_dashboard_panels_redteam.py`` from ``/mnt/raid0/llm/epyc-root``.
"""
import functools
import json
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard import panels, server

_NOW_DT = datetime.now(timezone.utc)
_NOW = _NOW_DT.timestamp()
_DAY = 86400.0
_HOUR = 3600.0

_V2_SECTIONS = ("campaign", "champion", "backend_standing", "headroom",
                "blocking_conditions", "resource_claims", "release_package")


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _env(panel, **kw):
    kw.setdefault("artifact_present", True)
    return panels.envelope(panels.PANELS[panel], panels.Observation(**kw), now=_NOW)


def _healthy_total():
    """A TOTAL, healthy envelope set — one per registered panel."""
    envs = {}
    for name, src in panels.PANELS.items():
        if src.kind in panels.LIVE_KINDS:
            envs[name] = _env(name, timestamp=None, source="live-scan", populated=True)
        else:
            envs[name] = _env(name, timestamp=_NOW - 60, source=src.timestamp_field,
                              populated=True, watermark=f"{name}:1")
    return envs


class _Artifact:
    """Point one of the hub's artifact paths at a temp file for a block."""

    def __init__(self, attr, content):
        self.attr, self.content = attr, content

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "artifact.json"
        if self.content is not None:
            path.write_text(self.content if isinstance(self.content, str)
                            else json.dumps(self.content), encoding="utf-8")
        self._orig = getattr(server, self.attr)
        setattr(server, self.attr, path)
        server._watchdog_state.clear()
        return path

    def __exit__(self, *exc):
        setattr(server, self.attr, self._orig)
        server._watchdog_state.clear()
        self._tmp.cleanup()
        return False


# --------------------------------------------------------------------------- #
# ATTACK 1 — a timestamp in the FUTURE never ages
# --------------------------------------------------------------------------- #
class FutureTimestampTest(unittest.TestCase):
    """``age = max(0.0, now - ts)`` clamps at zero.

    PRE-FIX (observed): a kernel contract dated one year ahead read
    ``staleness_class=fresh``, ``reporting=observed``, ``watchdog=ok``,
    ``age_s=0.0`` — and the fold over it was ``ok``. It would have read that way
    forever, however long the loop had been dead. One producer host with a clock
    ahead, or a naive local timestamp parsed as UTC, buys permanent freshness.

    BITE: delete the ``FUTURE_SKEW_TOLERANCE_S`` branch in ``panels.envelope``
    and this class reproduces exactly that (fresh / observed / ok / fold ok).
    """

    def test_a_future_dated_report_is_undatable_not_fresh(self):
        env = _env("kernel", timestamp=_NOW + 365 * _DAY, source="produced_at",
                   populated=True, watermark="ak:1")
        self.assertEqual(env["staleness_class"], panels.CLASS_MISSING)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_FUTURE_TIMESTAMP)
        self.assertEqual(env["reporting"], panels.REPORTING_ABSENT)
        self.assertIn("IN THE FUTURE", env["watchdog"]["reason"])

    def test_a_future_dated_report_degrades_the_fold(self):
        envs = _healthy_total()
        envs["kernel"] = _env("kernel", timestamp=_NOW + _DAY, source="produced_at",
                              populated=True)
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_DEGRADED)
        self.assertEqual(out["status_set_by"]["panel"], "kernel")

    def test_it_fires_on_an_unwatched_panel_too(self):
        """A defect in the EVIDENCE is not a liveness question, so it is visible
        on a panel nobody watches for liveness."""
        env = _env("bus", timestamp=_NOW + _DAY, source="heartbeats", populated=True)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_FUTURE_TIMESTAMP)
        self.assertEqual(panels.panel_verdict(env)[0], panels.STATUS_DEGRADED)

    def test_ntp_jitter_inside_the_tolerance_is_still_fresh(self):
        """COMPLIANT-PATH CONTROL: two hosts are never perfectly in sync. A report
        a few seconds ahead is a healthy producer, not a defect."""
        env = _env("kernel", timestamp=_NOW + 5.0, source="produced_at",
                   populated=True, watermark="ak:1")
        self.assertEqual(env["staleness_class"], panels.CLASS_FRESH)
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_OK)
        self.assertEqual(env["age_s"], 0.0)

    def test_the_boundary_is_the_declared_tolerance(self):
        self.assertGreater(panels.FUTURE_SKEW_TOLERANCE_S, 0)
        inside = _env("kernel", timestamp=_NOW + panels.FUTURE_SKEW_TOLERANCE_S - 1,
                      source="produced_at", populated=True)
        outside = _env("kernel", timestamp=_NOW + panels.FUTURE_SKEW_TOLERANCE_S + 1,
                       source="produced_at", populated=True)
        self.assertEqual(inside["staleness_class"], panels.CLASS_FRESH)
        self.assertEqual(outside["staleness_class"], panels.CLASS_MISSING)


# --------------------------------------------------------------------------- #
# ATTACK 2 — a dead producer on a NON-GATING panel leaves the fold green
# --------------------------------------------------------------------------- #
class NonGatingAlarmTest(unittest.TestCase):
    """The scar, reachable through ``gates_health=False``.

    PRE-FIX (observed): with ``outcome`` (the panel the trial-1302 outage is
    literally named after) at ``watchdog=stopped_reporting`` after 23 h of
    silence, ``fold()`` returned ``status: ok`` with ``worst.verdict: degraded``.
    A badge reading ``.status`` was green over a dead autopilot — the outage
    rebuilt with better vocabulary.

    THE RULE NOW: ``gates_health`` governs NOISE (staleness, benign absence). A
    watchdog alarm always gates. A producer whose silence is genuinely normal
    declares ``watched=False``; a producer that has finished declares itself idle.

    BITE: restore ``if not env.get("gates_health"): continue`` ahead of the
    status raise in ``panels.fold`` and ``test_an_undeclared_dead_autopilot_...``
    goes green-over-dead again.
    """

    def test_an_undeclared_dead_autopilot_degrades_the_fold(self):
        envs = _healthy_total()
        envs["outcome"] = _env("outcome", timestamp=_NOW - 23 * _HOUR,
                               source="generated_at", populated=True,
                               watermark="trial:1302")
        out = panels.fold(envs)
        self.assertFalse(envs["outcome"]["gates_health"])
        self.assertEqual(envs["outcome"]["watchdog"]["state"], panels.WATCHDOG_STOPPED)
        self.assertEqual(out["status"], panels.STATUS_DEGRADED)
        self.assertEqual(out["status_set_by"]["panel"], "outcome")

    def test_the_not_advancing_arm_gates_too(self):
        state = {}
        panels.observe_watermark(state, "outcome", "trial:1302", now=_NOW - 8 * _HOUR)
        panels.observe_watermark(state, "outcome", "trial:1302", now=_NOW)
        env = panels.envelope(panels.PANELS["outcome"], panels.Observation(
            artifact_present=True, timestamp=_NOW - 30, source="generated_at",
            populated=True, watermark="trial:1302"), now=_NOW, watchdog_state=state)
        envs = _healthy_total()
        envs["outcome"] = env
        self.assertEqual(env["watchdog"]["state"], panels.WATCHDOG_NOT_ADVANCING)
        self.assertEqual(panels.fold(envs)["status"], panels.STATUS_DEGRADED)

    def test_a_declared_pause_stays_green(self):
        """COMPLIANT-PATH CONTROL #1 — the reason this watchdog will not be turned
        off. A Phase-0 stop-loss pause is legitimate and stays ok when the loop
        DECLARES it; only the producer may say so."""
        envs = _healthy_total()
        envs["outcome"] = _env("outcome", timestamp=_NOW - 23 * _HOUR,
                               source="generated_at", populated=True,
                               watermark="trial:1302", producer_idle=True)
        out = panels.fold(envs)
        self.assertEqual(envs["outcome"]["watchdog"]["state"], panels.WATCHDOG_IDLE)
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertIsNone(out["status_set_by"])

    def test_the_exporter_declares_the_pause_in_the_contract(self):
        """The declaration is read off the ORCHESTRATOR's contract, not inferred."""
        for doc in ({"outcome_progress": {"status": "paused"}},
                    {"outcome_progress": {"status": "ok", "paused": True}}):
            with self.subTest(doc=doc):
                obs = server._outcome_observation(
                    {**doc, "generated_at": _iso(_NOW_DT - timedelta(days=10))})
                self.assertTrue(obs.producer_idle)
        running = server._outcome_observation(
            {"outcome_progress": {"status": "ok"},
             "generated_at": _iso(_NOW_DT - timedelta(days=10))})
        self.assertFalse(running.producer_idle)

    def test_a_benign_absence_still_does_not_gate(self):
        """COMPLIANT-PATH CONTROL #2: the ``outcome`` exporter does not exist yet.
        Its absence must stay loud-but-green, or the surface cries wolf from the
        day it ships."""
        envs = _healthy_total()
        envs["outcome"] = _env("outcome", artifact_present=False, timestamp=None)
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertIn("outcome", [a["panel"] for a in out["absent"]])
        self.assertIn("outcome", [a["panel"] for a in out["attention"]])

    def test_an_unwatched_panel_never_alarms(self):
        """COMPLIANT-PATH CONTROL #3: ``bus``/``queue`` are deliberately unwatched
        because an idle fleet is legitimately silent. They still read
        ``unwatched`` rather than alarming into the fold."""
        envs = _healthy_total()
        envs["queue"] = _env("queue", timestamp=_NOW - 30 * _DAY,
                             source="rows[].ts", populated=True)
        out = panels.fold(envs)
        self.assertEqual(envs["queue"]["watchdog"]["state"], panels.WATCHDOG_UNWATCHED)
        self.assertEqual(out["status"], panels.STATUS_OK)


# --------------------------------------------------------------------------- #
# ATTACK 3 — fold over a partial universe
# --------------------------------------------------------------------------- #
class FoldTotalityTest(unittest.TestCase):
    """A fold is only a fold over its universe.

    PRE-FIX (observed): ``fold({})`` returned ``{"status": "ok"}``. A fold over
    NOTHING was green — the scar in its purest form. Any panel that dropped out
    of ``panel_envelopes()`` was subtracted from the verdict instead of named.

    BITE: delete the ``for panel in sorted(registry)`` loop in ``panels.fold``
    and ``test_an_empty_fold_is_not_ok`` returns ``ok`` again.
    """

    def test_an_empty_fold_is_not_ok(self):
        out = panels.fold({})
        self.assertEqual(out["status"], panels.STATUS_DEGRADED)
        self.assertEqual(len(out["attention"]), len(panels.PANELS))
        self.assertIsNotNone(out["status_set_by"])

    def test_a_panel_that_drops_out_of_the_fold_is_named(self):
        envs = _healthy_total()
        del envs["kernel"]
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_DEGRADED)
        self.assertEqual(out["status_set_by"]["panel"], "kernel")
        self.assertIn("REGISTERED BUT NOT FOLDED", out["status_set_by"]["why"])

    def test_a_total_healthy_fold_is_ok(self):
        """COMPLIANT-PATH CONTROL: totality did not make ``ok`` unreachable."""
        out = panels.fold(_healthy_total())
        self.assertEqual(out["status"], panels.STATUS_OK)
        self.assertEqual(out["attention"], [])
        self.assertIsNone(out["status_set_by"])

    def test_the_live_fold_is_total_over_the_registry(self):
        h = server.health_payload()
        self.assertEqual(set(h["panels"]), set(panels.PANELS))
        self.assertNotIn("REGISTERED BUT NOT FOLDED",
                         json.dumps(h["attention"]))


class FoldNamesTheOffenderTest(unittest.TestCase):
    """``worst`` is the worst by SCORE and need not be the panel that set
    ``status``.

    PRE-FIX (observed, live): ``/api/health`` answered ``status: absent`` —
    caused by ``kernel`` never having exported — while ``worst.panel`` was
    ``bus`` (an hour-old heartbeat, non-gating). A card pairing the colour of one
    with the sentence of the other points the operator at the wrong repository.

    BITE: drop ``status_set_by`` from ``panels.fold``/``health_payload`` and
    nothing on the wire connects the verdict to its cause.
    """

    def test_status_and_its_cause_are_both_on_the_wire(self):
        envs = _healthy_total()
        envs["kernel"] = _env("kernel", artifact_present=False, timestamp=None)
        envs["bus"] = _env("bus", timestamp=_NOW - 30 * _DAY, source="heartbeats",
                           populated=True)
        out = panels.fold(envs)
        self.assertEqual(out["status"], panels.STATUS_ABSENT)
        self.assertEqual(out["worst"]["panel"], "bus")        # worst by score
        self.assertEqual(out["status_set_by"]["panel"], "kernel")  # cause of status

    def test_status_set_by_is_never_null_while_status_is_not_ok(self):
        for envs in (self._absent(), self._degraded(), _healthy_total()):
            out = panels.fold(envs)
            with self.subTest(status=out["status"]):
                if out["status"] == panels.STATUS_OK:
                    self.assertIsNone(out["status_set_by"])
                else:
                    self.assertIsNotNone(out["status_set_by"])
                    self.assertEqual(out["status_set_by"]["verdict"], out["status"])

    def test_the_live_route_carries_it(self):
        h = server.API_ROUTES["/api/health"]()
        self.assertIn("status_set_by", h)
        if h["status"] != panels.STATUS_OK:
            self.assertIsNotNone(h["status_set_by"])

    def _absent(self):
        envs = _healthy_total()
        envs["kernel"] = _env("kernel", artifact_present=False, timestamp=None)
        return envs

    def _degraded(self):
        envs = _healthy_total()
        envs["timeline"] = _env("timeline", timestamp=_NOW - 30 * _DAY,
                                source="generated_at", populated=True)
        return envs


# --------------------------------------------------------------------------- #
# ATTACK 4 — a v2 contract in which NOBODY reported
# --------------------------------------------------------------------------- #
class KernelV2SelfReportTest(unittest.TestCase):
    """The hub trusted the producer's own ``unreported_sections`` summary.

    PRE-FIX (observed): a v2 document with a FRESH ``produced_at``, every one of
    the seven sections at ``not_reported``, and no ``unreported_sections`` key
    read ``fresh / observed / content=empty / watchdog=ok``, verdict ``ok``, fold
    ``ok``. One missing summary field in the producer and the consumer renders a
    clean card over a contract in which nothing was reported — absence tolerance
    reconstructed out of a self-report.

    BITE: put back ``unreported = data.get("unreported_sections")`` (trusting the
    summary) and drop the ``if not observed`` branch in
    ``server._kernel_observation``; all three tests below go green-over-nothing.
    """

    def _doc(self, **kw):
        doc = {"schema": server.KERNEL_SCHEMA_V2,
               "produced_at": _iso(_NOW_DT), "generated_at": _iso(_NOW_DT),
               "producer": {"run": {"campaign_id": "ak", "controller_seq": 1}},
               "sections": {n: {"status": "not_reported"} for n in _V2_SECTIONS}}
        doc.update(kw)
        return doc

    def test_no_observed_section_is_absence_however_fresh_produced_at_is(self):
        env = panels.envelope(panels.PANELS["kernel"],
                              server._kernel_observation(self._doc()), now=_NOW)
        self.assertTrue(env["artifact_present"])
        self.assertEqual(env["reporting"], panels.REPORTING_ABSENT)
        self.assertEqual(env["content"], panels.CONTENT_UNKNOWN)
        self.assertEqual(env["staleness_class"], panels.CLASS_MISSING)
        self.assertEqual(panels.panel_verdict(env)[0], panels.STATUS_ABSENT)

    def test_an_empty_self_report_does_not_launder_it(self):
        """The producer claiming ``unreported_sections: []`` while reporting
        nothing must not buy a clean card."""
        env = panels.envelope(panels.PANELS["kernel"],
                              server._kernel_observation(
                                  self._doc(unreported_sections=[])), now=_NOW)
        self.assertEqual(panels.panel_verdict(env)[0], panels.STATUS_ABSENT)
        self.assertEqual(sorted(env["unreported"]), sorted(_V2_SECTIONS))

    def test_unreported_is_derived_from_the_sections_not_the_summary(self):
        doc = self._doc()
        doc["sections"]["campaign"] = {"status": "observed", "stopped": False}
        doc["unreported_sections"] = []          # producer's summary LIES
        obs = server._kernel_observation(doc)
        self.assertIn("release_package", obs.unreported)
        self.assertNotIn("campaign", obs.unreported)

    def test_a_garbage_sections_map_dates_nothing(self):
        for bad in ("oops", [], {}, None, 7):
            with self.subTest(sections=bad):
                obs = server._kernel_observation(self._doc(sections=bad))
                self.assertIsNone(obs.timestamp)
                self.assertIsNone(obs.populated)

    def test_a_fully_reported_contract_still_reads_clean(self):
        """COMPLIANT-PATH CONTROL: a healthy v2 export is unaffected."""
        doc = self._doc(sections={n: {"status": "observed", "as_of": _iso(_NOW_DT)}
                                  for n in _V2_SECTIONS})
        env = panels.envelope(panels.PANELS["kernel"],
                              server._kernel_observation(doc), now=_NOW)
        self.assertEqual(env["reporting"], panels.REPORTING_OBSERVED)
        self.assertEqual(env["staleness_class"], panels.CLASS_FRESH)
        self.assertEqual(env["unreported"], [])
        self.assertEqual(panels.panel_verdict(env)[0], panels.STATUS_OK)

    def test_a_partially_reported_contract_is_still_dated_and_named(self):
        """COMPLIANT-PATH CONTROL: partial reporting is not treated as absence —
        it is dated normally and its missing owners are named."""
        doc = self._doc()
        doc["sections"]["campaign"] = {"status": "observed", "stopped": False}
        env = panels.envelope(panels.PANELS["kernel"],
                              server._kernel_observation(doc), now=_NOW)
        self.assertEqual(env["reporting"], panels.REPORTING_OBSERVED)
        self.assertEqual(env["staleness_class"], panels.CLASS_FRESH)
        self.assertIn("champion", env["unreported"])


# --------------------------------------------------------------------------- #
# ATTACK 5 — an unreadable artifact reported as "never exported"
# --------------------------------------------------------------------------- #
class UnreadableArtifactTest(unittest.TestCase):
    """A corrupt export and a missing one are different facts.

    PRE-FIX (observed): a kernel contract that existed but did not parse reported
    ``artifact_present=false`` and a watchdog reason of "NOBODY IS REPORTING …
    no campaign has ever exported one" — telling the operator the opposite of
    what happened and pointing the investigation at the wrong repository. A
    truncated write (the failure mode of a producer killed mid-export) reads as
    "the loop never ran".

    BITE: revert ``_read_json_object`` to returning ``False`` on
    ``JSONDecodeError`` and ``test_a_corrupt_export_is_present_and_broken``
    fails on ``artifact_present``.
    """

    def test_a_corrupt_export_is_present_and_broken(self):
        with _Artifact("KERNEL_DASHBOARD_JSON", "{truncated"):
            out = server.kernel_payload()
        fr = out["_freshness"]
        self.assertTrue(fr["artifact_present"])        # something IS there
        self.assertEqual(fr["reporting"], panels.REPORTING_ABSENT)  # nothing datable
        self.assertNotEqual(fr["watchdog"]["state"], panels.WATCHDOG_NEVER)
        self.assertIn("unreadable", fr["watchdog"]["reason"])
        self.assertIn("unreadable", panels.panel_verdict(fr)[1])

    def test_a_corrupt_export_is_not_labelled_a_legacy_v1_contract(self):
        """The degraded shell has no ``schema``, and unlabelled means v1 — so a
        corrupt file was being reported as a readable legacy contract."""
        with _Artifact("KERNEL_DASHBOARD_JSON", "{truncated"):
            self.assertIsNone(server.kernel_payload()["_contract_version"])

    def test_a_missing_export_still_says_never_exported(self):
        """COMPLIANT-PATH CONTROL: the never-exported diagnosis is preserved for
        the case it actually describes."""
        with _Artifact("KERNEL_DASHBOARD_JSON", None):
            fr = server.kernel_payload()["_freshness"]
        self.assertFalse(fr["artifact_present"])
        self.assertEqual(fr["watchdog"]["state"], panels.WATCHDOG_NEVER)
        self.assertIn("NOBODY IS REPORTING", fr["watchdog"]["reason"])

    def test_a_readable_export_is_unaffected(self):
        """COMPLIANT-PATH CONTROL."""
        doc = {"runs": [{"ts": _iso(_NOW_DT)}], "generated_at": _iso(_NOW_DT)}
        with _Artifact("KERNEL_DASHBOARD_JSON", doc):
            out = server.kernel_payload()
        self.assertEqual(out["_contract_version"], "v1")
        self.assertEqual(out["_freshness"]["reporting"], panels.REPORTING_OBSERVED)

    def test_every_file_backed_reader_uses_the_same_rule(self):
        for attr, payload in (("KERNEL_DASHBOARD_JSON", server.kernel_payload),
                              ("TIMELINE_PATH", server.timeline_payload),
                              ("AUTOPILOT_OUTCOME_JSON", server.outcome_payload),
                              ("BENCHMARK_ARTIFACT_INVENTORY",
                               server.benchmark_artifacts_payload)):
            with self.subTest(artifact=attr):
                with _Artifact(attr, "{truncated"):
                    fr = payload()["_freshness"]
                self.assertTrue(fr["artifact_present"], attr)
                self.assertEqual(fr["reporting"], panels.REPORTING_ABSENT, attr)
                with _Artifact(attr, None):
                    fr = payload()["_freshness"]
                self.assertFalse(fr["artifact_present"], attr)


class MalformedOutcomeContractTest(unittest.TestCase):
    """A document the reader could not understand must not date a report.

    PRE-FIX (observed): any JSON object carrying a fresh ``generated_at`` but no
    ``outcome_progress`` normalised to a shell whose ``generated_at`` survived —
    so it read ``fresh / observed / content=empty / watchdog=ok``, verdict ``ok``.
    An unparseable contract rendered as a healthy, empty autopilot card.

    BITE: drop the ``READER_ERROR_KEY`` short-circuit at the top of
    ``server._outcome_observation`` and this reads ``fresh``/``ok`` again.
    """

    def test_a_document_that_is_not_a_contract_dates_nothing(self):
        with _Artifact("AUTOPILOT_OUTCOME_JSON",
                       {"generated_at": _iso(_NOW_DT), "junk": True}):
            out = server.outcome_payload()
        fr = out["_freshness"]
        self.assertEqual(fr["staleness_class"], panels.CLASS_MISSING)
        self.assertEqual(fr["reporting"], panels.REPORTING_ABSENT)
        self.assertEqual(fr["content"], panels.CONTENT_UNKNOWN)
        self.assertIn("missing 'outcome_progress'", fr["detail"])

    def test_absent_blockers_are_null_not_an_empty_list(self):
        """``[]`` is a CLAIM — 'the exporter looked and found no blockers'.
        Emitting it over a producer that never reported is the conflation this
        surface exists to end."""
        with _Artifact("AUTOPILOT_OUTCOME_JSON", None):
            out = server.outcome_payload()
        self.assertIsNone(out["outcome_progress"]["blockers"])

    def test_the_deployed_page_still_tolerates_the_null(self):
        """COMPLIANT-PATH CONTROL: ``static/handoffs.html`` reads blockers through
        ``Array.isArray(op.blockers)?op.blockers:[]``, so the card renders exactly
        as before. Only the wire changed."""
        page = (Path(server.__file__).resolve().parent
                / "static" / "handoffs.html").read_text(encoding="utf-8")
        self.assertIn("Array.isArray(op.blockers)?op.blockers:[]", page)
        with _Artifact("AUTOPILOT_OUTCOME_JSON", None):
            json.dumps(server.outcome_payload())   # serialisable; cannot 500

    def test_a_real_contract_is_still_read(self):
        """COMPLIANT-PATH CONTROL, both contract forms."""
        for doc in ({"generated_at": _iso(_NOW_DT),
                     "outcome_progress": {"status": "ok", "blockers": []}},
                    {"generated_at": _iso(_NOW_DT), "status": "ok",
                     "rates": {}, "blockers": []}):
            with self.subTest(form=sorted(doc)):
                with _Artifact("AUTOPILOT_OUTCOME_JSON", doc):
                    fr = server.outcome_payload()["_freshness"]
                self.assertEqual(fr["reporting"], panels.REPORTING_OBSERVED)
                self.assertEqual(fr["staleness_class"], panels.CLASS_FRESH)


# --------------------------------------------------------------------------- #
# ATTACK 6 — getting a panel past the totality test
# --------------------------------------------------------------------------- #
def _fake_hub(name="fake_hub", *, extra=None, routes=None):
    mod = types.ModuleType(name)
    funcs = [s.payload_func for s in panels.PANELS.values()]
    exec("\n".join(f"def {f}(*a, **k):\n    return {{}}\n" for f in funcs),
         mod.__dict__)
    exec("\n".join(
        f"def {src.health_func}(*a, **k):\n    return 200, {{}}"
        for src in panels.PANELS.values() if src.health_func), mod.__dict__)
    for attr, value in (extra or {}).items():
        setattr(mod, attr, value(mod) if callable(value) else value)
    mod.API_ROUTES = {s.route: getattr(mod, s.payload_func)
                      for s in panels.PANELS.values() if s.route}
    mod.PANEL_HEALTH_ROUTES = {
        s.health_route: getattr(mod, s.health_func)
        for s in panels.PANELS.values() if s.health_route
    }
    for route, fn in (routes or {}).items():
        mod.API_ROUTES[route] = fn(mod) if callable(fn) else fn
    return mod


class RegistryEvasionTest(unittest.TestCase):
    """Two ways a panel used to get past ``registry_gaps``.

    PRE-FIX (observed):

    1. ``API_ROUTES["/api/kernel"] = functools.partial(outcome_payload)`` — the
       identity check was skipped whenever the handler had no ``__name__``, so
       the wrong producer sat behind a registered route and ``registry_gaps``
       returned NO GAPS.
    2. ``ghost_payload = functools.partial(kernel_payload)`` in the hub — a
       ``functools.partial``'s ``__module__`` is ``functools``, so discovery
       read it as "defined elsewhere" and an unsourced panel was invisible.

    BITE: restore ``if served_name is not None and served_name != ...`` in
    ``registry_gaps``, or the plain ``__module__`` comparison in
    ``discover_payload_functions``, and each test below reports no gaps.
    """

    def test_an_unidentifiable_route_handler_is_a_gap(self):
        mod = _fake_hub(routes={"/api/kernel":
                                lambda m: functools.partial(m.outcome_payload)})
        gaps = panels.registry_gaps(mod)
        self.assertTrue(any("/api/kernel" in m for m in gaps["route_mismatch"]),
                        gaps)
        self.assertIn("unidentifiable", " ".join(gaps["route_mismatch"]))

    def test_a_callable_object_panel_is_discovered(self):
        mod = _fake_hub(extra={"ghost_payload":
                               lambda m: functools.partial(m.kernel_payload)})
        self.assertIn("ghost_payload", panels.discover_payload_functions(mod))
        self.assertEqual(panels.registry_gaps(mod)["unregistered_payload_functions"],
                         ["ghost_payload"])

    def test_a_class_based_payload_is_discovered(self):
        mod = _fake_hub()

        class _Ghost:
            def __call__(self):
                return {}
        mod.ghost_payload = _Ghost()
        self.assertIn("ghost_payload", panels.discover_payload_functions(mod))

    def test_the_baseline_fake_hub_is_clean(self):
        """COMPLIANT-PATH CONTROL: the fixture the controls mutate is gap-free."""
        self.assertEqual({k: v for k, v in panels.registry_gaps(_fake_hub()).items()
                          if v}, {})

    def test_an_imported_payload_function_is_still_ignored(self):
        """COMPLIANT-PATH CONTROL: the widened discovery must not start counting
        a payload function the hub merely IMPORTS as a panel it serves."""
        mod = types.ModuleType("borrower")
        mod.kernel_payload = server.kernel_payload
        self.assertEqual(panels.discover_payload_functions(mod), set())

    def test_the_real_hub_still_has_no_gaps(self):
        """COMPLIANT-PATH CONTROL: the widened checks do not indict the real hub."""
        self.assertEqual({k: v for k, v in panels.registry_gaps(server).items()
                          if v}, {})


# --------------------------------------------------------------------------- #
# ATTACK 7 — thresholds so wide nothing is ever stale
# --------------------------------------------------------------------------- #
class ThresholdCredibilityTest(unittest.TestCase):
    """"Declares thresholds" was satisfiable by declaring meaningless ones.

    PRE-FIX (observed): ``stale_s = 100 years`` constructed fine. The entry
    passed every registry invariant and monitored nothing — the absence-tolerant
    page with a threshold bolted on. Likewise ``silent_after_s > stale_s`` gave a
    watchdog that stayed quiet while the panel already read stale, i.e. the
    louder signal arriving later than the quieter one.

    BITE: remove the ``MAX_STALE_S`` / ``silent_after_s <= stale_s`` checks in
    ``PanelSource.__post_init__`` and both refusals below construct happily.
    """

    def _src(self, **kw):
        base = dict(panel="x", kind=panels.KIND_ARTIFACT, payload_func="x_payload",
                    producer="p", producer_repo="r", evidence="e",
                    timestamp_field="t", absence_means="a" * 50,
                    warn_s=_HOUR, stale_s=_DAY)
        base.update(kw)
        return panels.PanelSource(**base)

    def test_an_unmonitorable_staleness_budget_is_refused(self):
        with self.assertRaises(panels.RegistryError) as ctx:
            self._src(stale_s=100 * 365 * _DAY)
        self.assertIn("MAX_STALE_S", str(ctx.exception))

    def test_a_silence_budget_wider_than_the_staleness_budget_is_refused(self):
        with self.assertRaises(panels.RegistryError) as ctx:
            self._src(watched=True, silent_after_s=30 * _DAY)
        self.assertIn("silent_after_s", str(ctx.exception))

    def test_a_realistic_entry_still_constructs(self):
        """COMPLIANT-PATH CONTROL: the widest real budget here (the benchmark
        inventory, 30 d) is still legal, and so is silence == staleness."""
        self.assertEqual(self._src(stale_s=panels.MAX_STALE_S).stale_s,
                         panels.MAX_STALE_S)
        self.assertEqual(self._src(watched=True, silent_after_s=_DAY).silent_after_s,
                         _DAY)

    def test_every_registered_panel_satisfies_the_invariants(self):
        for name, src in panels.PANELS.items():
            with self.subTest(panel=name):
                if src.stale_s is not None:
                    self.assertLessEqual(src.stale_s, panels.MAX_STALE_S)
                if src.watched:
                    self.assertLessEqual(src.silent_after_s, src.stale_s)


# --------------------------------------------------------------------------- #
# ATTACK 8 — the fold's own inputs
# --------------------------------------------------------------------------- #
class _EmptyBoard:
    """Point the hub's handoff scan at an empty tree, bypassing the TTL cache."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        for state in ("active", "blocked", "completed", "archived"):
            (root / state).mkdir(parents=True, exist_ok=True)
        self._orig = server.HANDOFF_DIR
        server.HANDOFF_DIR = root
        server._board_cache = None
        return root

    def __exit__(self, *exc):
        server.HANDOFF_DIR = self._orig
        server._board_cache = None
        return False


class FoldInputHonestyTest(unittest.TestCase):
    """The fold's own inputs were partly fabricated.

    PRE-FIX (observed), two independent defects on the same panel:

    1. ``panel_envelopes()["board"]`` was ``panels.live()`` — ``populated=True``
       hardcoded — so the fold's board card asserted content whatever the scan
       found, while ``board_payload()`` computed its own answer. Two answers for
       one panel, and ``/api/health`` carried the fabricated one.
    2. ``board_payload`` computed ``populated=bool(payload["columns"])``, and
       ``columns`` is a dict of FOUR LISTS that ``build_board`` always emits. It
       is truthy over an empty or missing handoff tree, so the *real* answer was
       also a constant ``True``: the one health-gating live panel could never
       report ``content=empty``.

    BITE: revert either (``lambda: panels.live()`` in ``panel_envelopes``, or
    ``bool(columns)`` in ``board_payload``) and
    ``test_an_empty_board_reports_empty_content`` reads ``populated`` over an
    empty tree.
    """

    def test_an_empty_board_reports_empty_content(self):
        with _EmptyBoard():
            direct = server.board_payload()["_freshness"]
            envs = server.panel_envelopes()
        self.assertEqual(direct["content"], panels.CONTENT_EMPTY)
        self.assertEqual(envs["board"]["content"], panels.CONTENT_EMPTY)

    def test_a_populated_board_still_reports_content(self):
        """COMPLIANT-PATH CONTROL: the real board is not now reported as empty."""
        direct = server.board_payload(force=True)["_freshness"]
        self.assertEqual(direct["content"], panels.CONTENT_POPULATED)
        self.assertEqual(server.panel_envelopes()["board"]["content"],
                         panels.CONTENT_POPULATED)

    def test_the_fold_and_the_board_route_agree(self):
        envs = server.panel_envelopes()
        direct = server.board_payload()["_freshness"]
        self.assertEqual(envs["board"]["content"], direct["content"])
        self.assertEqual(envs["board"]["panel"], "board")

    def test_the_bus_panel_presence_is_the_tree_not_the_parser(self):
        """PyYAML is optional for this hub. Deriving ``artifact_present`` from a
        successful parse made a stdlib-only interpreter report 'the session bus
        is not initialised in this checkout' over a perfectly healthy bus."""
        self.assertTrue((server._BUS_ROOT / "config.yaml").exists())
        self.assertTrue(server.bus_payload()["_freshness"]["artifact_present"])


class TransportPlaneStillSeparateTest(unittest.TestCase):
    """The fold got louder; the supervisor's probe must not have.

    ``scripts/dashboard/hub_supervisor.sh`` restarts the hub whenever ``/health``
    stops matching ``"status"…ok``. Every change above makes ``/api/health`` more
    willing to report ``degraded``; if any of it leaked into ``/health`` the hub
    would now restart-loop over a dead producer in another repository.
    """

    def test_the_probe_is_ok_with_every_producer_dead_or_broken(self):
        with _Artifact("KERNEL_DASHBOARD_JSON", "{truncated"), \
             _Artifact("AUTOPILOT_OUTCOME_JSON", None), \
             _Artifact("TIMELINE_PATH", None):
            body = json.dumps(server.transport_probe_payload())
            fold_status = server.health_payload()["status"]
        self.assertRegex(body, r'"status".*ok')
        self.assertNotEqual(fold_status, panels.STATUS_OK)   # the fold DID notice

    def test_no_fold_field_leaked_into_the_probe(self):
        probe = server.transport_probe_payload()
        for key in ("worst", "status_set_by", "panels", "attention", "absent"):
            self.assertNotIn(key, probe)


if __name__ == "__main__":
    unittest.main()
