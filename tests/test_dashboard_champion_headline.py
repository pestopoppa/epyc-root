"""The champion headline: ONE number, ONE named anchor, allowed to be absent.

WHY THIS FILE EXISTS (operator, 2026-08-30)
-------------------------------------------
`/loop` carried ``+48.9%`` in the largest type on the page, sourced from the
operator-gated manual-research bundle, directly beside a loop whose own champion
was worth roughly a tenth of that. Different producers, different anchors,
different questions -- rendered side by side with nothing saying so. The operator
read the page and reasonably asked why the champion said +48.9% when they had
been told +9%.

The ruling: the champion headline is the champion tree's collective performance
gain over the FROZEN PRODUCTION KERNEL and nothing else competes for that slot;
capabilities the tree enables may be listed beside it.

AND IT MUST RENDER HONESTLY AS UNMEASURED. There is no direct champion-vs-v9 A/B
for the current champion ``5ad3e36d``. The last one was several commits ago; run
17 added 30 commits (audited as a block at +3.942% against *what that run started
from*) and run 18 added one. Those are MARGINALS against an anchor that advances
on every keep, and composing them would manufacture a measurement no run ever
took -- the derived-marginal error this program already made once.

WHERE THE FIXTURES COME FROM, AND WHY IT MATTERS
------------------------------------------------
A fixture written from the READER's expectations proves only that the reader is
self-consistent. That is exactly how the GPU panel stayed dark through 41 passing
tests: ``body()`` invented ``held_s``, the reader looked for ``held_s``, and both
disagreed with the producer's ``claim_held_s``.

So every value here is lifted from a record that exists on disk:

  * the loop body is ``tests/fixtures/autokernel_loop_status_sample.json`` -- a
    verbatim recording of the running loop's own store root;
  * the operator-gated bundle is the REAL emitted file, read from the host, and
    these tests SKIP rather than invent one if it is not there;
  * the champion bundle's *values* are lifted from real records too: its baseline
    commit from the real bundle's ``production_anchor.commit``, its champion
    commit from the real loop status's ``champion_head``, and its effect, surface,
    pairs and noise floor from ``run17-audit/total.json``, the real audit record.

The CARRIER is new -- nothing writes ``champion-vs-production.json`` yet, which is
the whole point of the panel -- so its key names cannot be recorded from a
producer. They are stated once, here, as the contract the emitter must meet, and
``test_the_contract_this_file_pins_is_the_one_the_reader_reads`` keeps this file
and the reader from drifting apart silently. The one field with no real analogue
at all, ``capabilities``, is marked as such below.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dashboard import loop_status  # noqa: E402
from dashboard import server as S  # noqa: E402

PAGE = REPO / "dashboard/static/loop.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"
SAMPLE = REPO / "tests/fixtures/autokernel_loop_status_sample.json"

#: The real emitted operator-gated bundle, on this host. Read, never invented:
#: it is the producer of the number that caused the confusion, and a hand-written
#: stand-in would let this file and the page agree with each other while both
#: disagreed with the emitter.
REAL_BUNDLE = Path("/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json")
#: The real run-17 block audit. Its fields are where this file's champion-bundle
#: numbers come from, so no measurement value below is invented.
REAL_AUDIT = Path("/mnt/raid0/llm/autokernel/loop-memory/run17-audit/total.json")


def _stamp(seconds_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
            ).isoformat().replace("+00:00", "Z")


def recorded_loop(*, age_s: float = 45.0, state: str = "running") -> dict:
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    body["generated_at"] = _stamp(age_s)
    body["state"] = state
    return body


def real_bundle() -> dict:
    if not REAL_BUNDLE.is_file():
        raise unittest.SkipTest(
            f"{REAL_BUNDLE} is not on this host; refusing to invent the emitted "
            "bundle whose mislabelling is the subject of this file")
    return json.loads(REAL_BUNDLE.read_text(encoding="utf-8"))


def real_audit() -> dict:
    if not REAL_AUDIT.is_file():
        raise unittest.SkipTest(f"{REAL_AUDIT} is not on this host")
    return json.loads(REAL_AUDIT.read_text(encoding="utf-8"))


def champion_bundle(*, age_s: float = 3600.0, champion_commit: str | None = None,
                    baseline_commit: str | None = None,
                    capabilities: object = "unset") -> dict:
    """A well-formed ``epyc.autokernel.champion_vs_production.v1`` body.

    Values from real records (see the module docstring); the carrier is the new
    contract. ``capabilities`` is the ONE field with no on-disk analogue anywhere
    under the campaign -- there is no FlashAttention2 record of any kind on this
    host -- so the entry below is the test's own, used only to prove the render
    path exists for a producer that publishes one. Nothing in the shipped page
    contains a capability name.
    """
    audit = real_audit()
    bundle = real_bundle()
    body = {
        "schema": loop_status.CHAMPION_SCHEMA,
        "generated_at": _stamp(age_s),
        "stale_after_s": int(loop_status.CHAMPION_DEFAULT_STALE_AFTER_S),
        "baseline": {
            "commit": (baseline_commit if baseline_commit is not None
                       else bundle["production_anchor"]["commit"]),
            "label": loop_status.FROZEN_PRODUCTION_LABEL,
        },
        "champion": {"commit": (champion_commit if champion_commit is not None
                                else recorded_loop()["champion_head"])},
        "effect_fraction": audit["effect"],
        "metric": "tg128_tok_s",
        "metric_direction": "higher_better",
        "surface": audit["surface"],
        "pairs": audit["pairs"],
        "noise_floor_pct": audit["noise_floor_pct"],
        "evidence": str(REAL_AUDIT),
    }
    if capabilities != "unset":
        body["capabilities"] = capabilities
    return body


class _Store(unittest.TestCase):
    """Points the hub's loop store root and gate path at a temp directory."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="champ-headline-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        prior = os.environ.get(loop_status.STORE_ROOT_ENV)
        os.environ[loop_status.STORE_ROOT_ENV] = str(self.root)
        self.addCleanup(self._restore_env, prior)
        self.prior_gate = S.OPERATOR_GATE_BUNDLE_JSON
        self.addCleanup(setattr, S, "OPERATOR_GATE_BUNDLE_JSON", self.prior_gate)
        with S._watchdog_lock:
            S._watchdog_state.clear()

    @staticmethod
    def _restore_env(prior: str | None) -> None:
        if prior is None:
            os.environ.pop(loop_status.STORE_ROOT_ENV, None)
        else:
            os.environ[loop_status.STORE_ROOT_ENV] = prior

    def write_loop(self, body: object) -> None:
        target = self.root / loop_status.STATUS_FILENAME
        target.write_text(body if isinstance(body, str) else json.dumps(body),
                          encoding="utf-8")

    def write_champion(self, body: object) -> None:
        target = self.root / loop_status.CHAMPION_FILENAME
        target.write_text(body if isinstance(body, str) else json.dumps(body),
                          encoding="utf-8")

    def use_real_bundle(self) -> None:
        """Copy the REAL emitted bundle in, so its mtime is inside its envelope."""
        source = real_bundle()
        target = self.root / "operator_gate_bundle.json"
        target.write_text(json.dumps(source), encoding="utf-8")
        S.OPERATOR_GATE_BUNDLE_JSON = target

    def block(self) -> dict:
        return S.loop_payload()["champion_vs_production"]


# --------------------------------------------------------------------------- #
# The reader
# --------------------------------------------------------------------------- #
class Contract(_Store):

    def test_the_contract_this_file_pins_is_the_one_the_reader_reads(self):
        """NON-VACUITY / anti-drift.

        Every fixture below is built against key names stated in this file
        because no producer writes this carrier yet. If the reader renamed a
        field, every test here would keep passing against its own spelling --
        the self-consistent-fixture failure, one level up. So the reader's own
        accepted body is round-tripped and the derived block must carry the
        values through.
        """
        self.write_loop(recorded_loop())
        body = champion_bundle()
        self.write_champion(body)
        got = self.block()
        self.assertTrue(got["measured"])
        self.assertEqual(got["effect_fraction"], body["effect_fraction"])
        self.assertEqual(got["surface"], body["surface"])
        self.assertEqual(got["pairs"], body["pairs"])
        self.assertEqual(got["metric"], body["metric"])
        self.assertEqual(got["champion"]["measured_commit"],
                         body["champion"]["commit"])

    def test_the_anchor_is_the_frozen_production_kernel_and_is_stated_always(self):
        """Named on EVERY reading -- measured, absent, refused. A percentage
        with no named anchor is the defect that produced this whole revision."""
        self.write_loop(recorded_loop())
        for label, setup in (("absent", lambda: None),
                             ("malformed", lambda: self.write_champion("{half")),
                             ("measured",
                              lambda: self.write_champion(champion_bundle()))):
            with self.subTest(label):
                if label != "absent":
                    (self.root / loop_status.CHAMPION_FILENAME).unlink(
                        missing_ok=True)
                setup()
                got = self.block()
                self.assertEqual(got["baseline"]["commit"],
                                 loop_status.FROZEN_PRODUCTION_COMMIT)
                self.assertEqual(got["baseline"]["label"],
                                 loop_status.FROZEN_PRODUCTION_LABEL)

    def test_the_frozen_commit_is_the_one_the_repo_froze(self):
        """The anchor is a fact about the repository, not a spelling choice."""
        self.assertEqual(loop_status.FROZEN_PRODUCTION_COMMIT,
                         real_bundle()["production_anchor"]["commit"])

    def test_a_bundle_measured_against_another_anchor_is_REFUSED(self):
        """The forgery this panel exists to prevent: a marginal against the
        loop's advancing anchor, or against an older production, promoted into
        the cumulative-vs-frozen-production slot by renaming the carrier."""
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle(
            baseline_commit=recorded_loop()["anchor_commit"]))
        got = self.block()
        self.assertFalse(got["measured"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIn("not the frozen production kernel", got["reader_error"])
        self.assertIsNone(got["effect_fraction"])

    def test_absent_is_not_a_measured_zero(self):
        self.write_loop(recorded_loop())
        got = self.block()
        self.assertFalse(got["measured"])
        self.assertIsNone(got["effect_fraction"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_ABSENT)
        self.assertIn("not been taken", got["absence_means"])
        self.assertIn("direct A/B", got["would_populate"])
        self.assertIn(loop_status.FROZEN_PRODUCTION_COMMIT[:12],
                      got["would_populate"])

    def test_absent_is_not_malformed_is_not_stale_is_not_fresh(self):
        """Four states, four verdicts, in the SAME vocabulary the loop badge and
        the operator-gate badge use. Three producers spelling `stale` three ways
        is a page nobody can read at a glance."""
        self.write_loop(recorded_loop())
        seen = {}
        seen["absent"] = self.block()
        self.write_champion("")
        seen["malformed"] = self.block()
        self.write_champion(champion_bundle(
            age_s=60 * 86400))
        seen["stale"] = self.block()
        self.write_champion(champion_bundle())
        seen["fresh"] = self.block()
        states = {k: v["freshness"]["state"] for k, v in seen.items()}
        self.assertEqual(states, {"absent": "absent", "malformed": "malformed",
                                  "stale": "stale", "fresh": "fresh"})
        self.assertEqual(len({v["freshness"]["detail"] for v in seen.values()}), 4)
        for state in states.values():
            self.assertIn(state, loop_status.STATES)
        # A stale bundle still CARRIES its number -- the measurement happened.
        self.assertTrue(seen["stale"]["measured"])

    def test_an_empty_file_is_malformed_not_absent(self):
        self.write_loop(recorded_loop())
        self.write_champion("")
        got = self.block()
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIn("empty", got["reader_error"])

    def test_a_future_stamp_cannot_buy_permanent_freshness(self):
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle(age_s=-86400))
        got = self.block()
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIn("FUTURE", got["freshness"]["detail"])

    def test_a_measurement_for_a_superseded_champion_says_so(self):
        """The normal case, not an edge one: a cumulative A/B is expensive and
        the champion advances on every keep."""
        self.write_loop(recorded_loop())
        older = real_bundle()["champion"]["commit"]
        self.write_champion(champion_bundle(champion_commit=older))
        got = self.block()
        self.assertTrue(got["measured"])
        self.assertIsNotNone(got["supersession"])
        self.assertEqual(got["supersession"]["measured_for"], older)
        self.assertEqual(got["supersession"]["current_champion"],
                         recorded_loop()["champion_head"])
        self.assertIn("cannot be added", got["supersession"]["detail"])

    def test_the_same_commit_raises_no_supersession(self):
        """Compliant-path control: the flag must not fire on every reading."""
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle())
        self.assertIsNone(self.block()["supersession"])

    def test_the_marginals_are_declared_uncomposable_on_every_reading(self):
        self.write_loop(recorded_loop())
        for label in ("absent", "measured"):
            with self.subTest(label):
                if label == "measured":
                    self.write_champion(champion_bundle())
                note = self.block()["not_composable"]
                self.assertIn("must never be summed", note)
                self.assertIn("advances on every keep", note)


class Capabilities(_Store):

    def test_unknown_is_stated_with_a_reason_and_a_remedy(self):
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle())
        caps = self.block()["capabilities"]
        self.assertFalse(caps["known"])
        self.assertEqual(caps["items"], [])
        self.assertIn("no producer attributes a capability list",
                      caps["unknown_reason"])
        self.assertIn("capabilities", caps["would_populate"])

    def test_a_published_list_is_carried_verbatim_with_its_evidence(self):
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle(capabilities=[
            {"name": "FlashAttention2 on gfx90a", "evidence": "gate fa2_supported"},
            "iqk IQ4_XS coverage",
        ]))
        caps = self.block()["capabilities"]
        self.assertTrue(caps["known"])
        self.assertEqual([i["name"] for i in caps["items"]],
                         ["FlashAttention2 on gfx90a", "iqk IQ4_XS coverage"])
        self.assertEqual(caps["items"][0]["evidence"], "gate fa2_supported")
        self.assertIsNone(caps["items"][1]["evidence"])
        self.assertIsNone(caps["unknown_reason"])

    def test_a_DECLARED_EMPTY_list_is_not_unknown(self):
        """Two different facts. 'The producer looked and found none' is a
        statement; 'nobody has been asked' is the absence of one."""
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle(capabilities=[]))
        caps = self.block()["capabilities"]
        self.assertTrue(caps["known"])
        self.assertEqual(caps["items"], [])
        self.assertIsNone(caps["unknown_reason"])

    def test_the_shipped_page_names_no_capability_of_its_own(self):
        """The list must be DERIVED, never typed. If a capability name ever
        appears in the markup, it is a memory wearing a measurement's clothes --
        and there is no FlashAttention2 record anywhere under the campaign for
        it to have come from."""
        html = PAGE.read_text(encoding="utf-8")
        # Comments explain the rule and may name the example the operator gave;
        # strip them so this greps the CODE, not its own rationale.
        code = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
        code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
        code = "\n".join(re.sub(r"//.*$", "", line) for line in code.splitlines())
        for banned in ("FlashAttention", "FlashAttention2", "GGML_IQK",
                       "IQ4_XS", "rocwmma"):
            self.assertNotIn(banned, code,
                             f"{banned!r} is typed into the shipped page")


# --------------------------------------------------------------------------- #
# The run's lifecycle, which is NOT its freshness
# --------------------------------------------------------------------------- #
class Lifecycle(_Store):

    def test_a_stopped_run_is_FINISHED_not_STALE(self):
        """Run 18 was stopped with a STOP sentinel. The loop drains the current
        iteration and exits through the normal `complete` path, so half an hour
        later a freshness-keyed banner would accuse a producer that did exactly
        what it was told."""
        self.write_loop(recorded_loop(age_s=10800, state="complete"))
        payload = S.loop_payload()
        self.assertEqual(payload["freshness_state"], loop_status.STATE_STALE)
        self.assertEqual(payload["notice"]["kind"], loop_status.NOTICE_FINISHED)
        self.assertEqual(payload["notice"]["run_state"], "complete")
        self.assertIn("STOP sentinel", payload["notice"]["detail"])

    def test_a_declared_failure_is_FAILED_while_perfectly_fresh(self):
        """Freshness alone draws NO banner here: the run published on its way
        out, so the reading is current and the run is dead."""
        self.write_loop(recorded_loop(age_s=20, state="failed"))
        payload = S.loop_payload()
        self.assertEqual(payload["freshness_state"], loop_status.STATE_FRESH)
        self.assertEqual(payload["notice"]["kind"], loop_status.NOTICE_FAILED)

    def test_an_unexplained_silence_is_STALE(self):
        """The compliant-path control for the two above: a run that declared no
        end and went quiet is still stale, and must not be excused as finished."""
        self.write_loop(recorded_loop(age_s=10800, state="running"))
        payload = S.loop_payload()
        self.assertEqual(payload["notice"]["kind"], loop_status.NOTICE_STALE)

    def test_a_live_run_raises_no_notice_at_all(self):
        self.write_loop(recorded_loop(age_s=20, state="running"))
        self.assertEqual(S.loop_payload()["notice"]["kind"],
                         loop_status.NOTICE_NONE)

    def test_absent_and_malformed_outrank_any_declared_state(self):
        """With no trustworthy body there is no declared state to believe."""
        self.assertEqual(S.loop_payload()["notice"]["kind"],
                         loop_status.NOTICE_ABSENT)
        self.write_loop('{"schema": "epyc.autokernel.loop_status.v1", "state": "com')
        self.assertEqual(S.loop_payload()["notice"]["kind"],
                         loop_status.NOTICE_MALFORMED)

    def test_every_run_state_maps_to_a_notice_and_they_are_distinct(self):
        seen = {}
        for state in loop_status.RUN_STATES:
            self.write_loop(recorded_loop(age_s=20, state=state))
            seen[state] = S.loop_payload()["notice"]["kind"]
        self.assertEqual(seen["complete"], loop_status.NOTICE_FINISHED)
        self.assertEqual(seen["failed"], loop_status.NOTICE_FAILED)
        self.assertEqual(seen["running"], loop_status.NOTICE_NONE)
        self.assertEqual(seen["starting"], loop_status.NOTICE_NONE)
        for kind in seen.values():
            self.assertIn(kind, loop_status.NOTICES)


# --------------------------------------------------------------------------- #
# The rendered page
# --------------------------------------------------------------------------- #
@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class Rendering(_Store):
    """Executes the real page JS. Stubs are not a browser: this proves the
    render path emits the content, not that the page looks right."""

    def _page_js(self) -> str:
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                            PAGE.read_text(encoding="utf-8"), re.S)
        self.assertTrue(blocks, "no inline script blocks found in loop.html")
        return "\n".join(blocks)

    def _render(self, page_js: str | None = None) -> dict:
        tmp = Path(tempfile.mkdtemp(prefix="champ-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(
            page_js if page_js is not None else self._page_js(), encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json")],
            capture_output=True, text=True, timeout=60)
        self.assertTrue(proc.stdout.strip(),
                        f"harness produced no output; stderr={proc.stderr[:400]}")
        out = json.loads(proc.stdout)
        self.assertEqual(out["threw"], [])
        # Keyed to the ELEMENT, never to the whole page: a whole-page substring
        # key is how "100%" once matched "+3.100%".
        self.assertIn("champ", out["by_id"])
        return out

    @staticmethod
    def _text(html: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()

    def test_the_harness_CATCHES_an_injected_fault(self):
        """Mutation, as a test. APPENDED, not prepended: declarations hoist."""
        self.write_loop(recorded_loop())
        broken = self._page_js() + "\nfunction renderChampion(d){ throw new Error('injected'); }\n"
        tmp = Path(tempfile.mkdtemp(prefix="champ-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(broken, encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json")],
            capture_output=True, text=True, timeout=60)
        out = json.loads(proc.stdout)
        self.assertTrue(out["threw"], "the harness did not notice an injected fault")
        self.assertTrue(any("injected" in t for t in out["threw"]))

    def test_an_unmeasured_headline_renders_words_never_a_number(self):
        self.write_loop(recorded_loop())
        card = self._text(self._render()["by_id"]["champ"])
        self.assertIn("NOT YET MEASURED", card)
        self.assertIn("not yet measured", card)
        self.assertIn("What would produce this number", card)
        # No percentage anywhere in the card. A 0.0% here would be a fabricated
        # measurement, and any other figure would be an invented one.
        self.assertNotRegex(card, r"[-+]?\d+\.\d+%")

    def test_the_headline_number_never_renders_without_its_anchor(self):
        """One element, both facts. There is no code path that emits the figure
        without the 'vs'."""
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle())
        card = self._text(self._render()["by_id"]["champ"])
        pct = f"+{champion_bundle()['effect_fraction'] * 100:.1f}%"
        self.assertIn(pct, card)
        self.assertIn("vs the frozen production kernel", card)
        self.assertIn(loop_status.FROZEN_PRODUCTION_LABEL, card)
        self.assertIn(loop_status.FROZEN_PRODUCTION_COMMIT[:12], card)
        # And the figure sits in front of its anchor, not somewhere else on the
        # page: the two are within one short span of each other.
        self.assertLess(card.index("vs the frozen") - card.index(pct), 40)

    def test_a_long_dead_measurement_is_dated_in_days_not_hours(self):
        """One age vocabulary across all three producers. This panel's envelope
        is weeks, so without a days branch a two-month-old measurement rendered
        `1416.0h ago` — a figure an operator has to do arithmetic on to discover
        is unusable."""
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle(age_s=59 * 86400))
        out = self._render()
        badge = out["text_by_id"]["champ-badgetxt"]
        self.assertTrue(badge.startswith("STALE"), badge)
        self.assertTrue(badge.endswith("d ago"), badge)
        self.assertIn("59.0d", badge)

    def test_a_superseded_measurement_is_marked_in_the_card(self):
        self.write_loop(recorded_loop())
        self.write_champion(champion_bundle(
            champion_commit=real_bundle()["champion"]["commit"]))
        out = self._render()
        card = self._text(out["by_id"]["champ"])
        self.assertIn("SUPERSEDED CHAMPION", card)
        self.assertIn(real_bundle()["champion"]["commit"][:12], card)
        self.assertIn(recorded_loop()["champion_head"][:12], card)

    def test_the_champion_card_and_the_gate_card_cannot_be_confused(self):
        """THE defect, in one assertion. Both cards carry a large percentage;
        each must name its own anchor, its own producer and its own question."""
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        self.write_champion(champion_bundle())
        out = self._render()
        champ = self._text(out["by_id"]["champ"])
        gate = self._text(out["by_id"]["opgate"])
        self.assertIn("This is not the champion headline", gate)
        self.assertIn("different anchor", gate)
        # The gate card names ITS anchor beside ITS number.
        #
        # NOT keyed on the bare commit prefix: this bundle's champion BRANCH is
        # `ak/champion/llama-cpp-0db32c06e3e5`, so `0db32c06e3e5 in gate` is
        # satisfied by the branch name and stayed green through a mutation that
        # dropped the anchor entirely. The key has to be the claim, not a
        # substring that happens to co-occur with it.
        self.assertIn("+48.9%", gate)
        anchor = real_bundle()["production_anchor"]["commit"][:12]
        self.assertIn(f"the frozen production kernel {anchor}", gate)
        self.assertNotIn("an anchor this bundle does not name", gate)
        # ...and says which commit it measured, against the loop's current one.
        self.assertIn(real_bundle()["champion"]["commit"][:12], gate)
        self.assertIn("a different tree", gate)
        # The champion card does not carry the gate bundle's figure at all.
        self.assertNotIn("+48.9%", champ)
        self.assertNotIn("48.9", champ)

    def test_the_gate_cards_measured_points_carry_BOTH_arms(self):
        """A `delta_pct` with no baseline beside it is the headline defect one
        level down. These are the rows the +48.9% is drawn from."""
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        gate = self._text(self._render()["by_id"]["opgate"])
        points = [g for g in real_bundle()["gates"]
                  if g["gate"] == "dflash2_vs_production_serving_path"][0]["points"]
        for point in points:
            with self.subTest(in_flight=point["in_flight"]):
                self.assertIn(f"{point['champion_tps']:.3f}", gate)
                self.assertIn(f"{point['production_ceiling_tps']:.3f}", gate)
        self.assertIn("production ceiling", gate)
        self.assertIn("frozen anchor", gate)

    def test_a_stopped_run_renders_FINISHED_and_a_lost_one_renders_STALE(self):
        """Executed, not reasoned about: three renderings, three banners."""
        seen = {}
        self.write_loop(recorded_loop(age_s=10800, state="complete"))
        seen["finished"] = self._render()["by_id"]["banner"]
        self.write_loop(recorded_loop(age_s=10800, state="running"))
        seen["stale"] = self._render()["by_id"]["banner"]
        self.write_loop(recorded_loop(age_s=20, state="failed"))
        seen["failed"] = self._render()["by_id"]["banner"]
        self.write_loop(recorded_loop(age_s=20, state="running"))
        seen["live"] = self._render()["by_id"]["banner"]

        self.assertIn("FINISHED", self._text(seen["finished"]))
        self.assertIn("STOP sentinel", self._text(seen["finished"]))
        self.assertNotIn("STALE", self._text(seen["finished"]))
        self.assertIn("STALE", self._text(seen["stale"]))
        self.assertIn("FAILED", self._text(seen["failed"]))
        self.assertEqual(self._text(seen["live"]), "")
        self.assertEqual(len(set(seen.values())), 4,
                         "two run outcomes produced the same banner")

    #: Phrases that NAME a baseline. A percentage is acceptable only if one of
    #: these sits within `_ANCHOR_WINDOW` characters of it.
    _ANCHORING = ("of the ANCHOR", "of claim-held seconds", "of held",
                  "vs the frozen production kernel", "vs anchor at the time",
                  "Share of device time in the champion profile",
                  "vs that baseline", "the frozen production kernel",
                  "production's ceiling", "of the anchor", "production ceiling",
                  "frozen anchor", "marginal", "must not be summed",
                  # The producer's own reason text names the bar it was measured
                  # against ("did not clear the 1.188% noise floor"), and that IS
                  # a named baseline — it is not the page's to relabel.
                  "noise floor")
    _ANCHOR_WINDOW = 160

    @classmethod
    def _unanchored(cls, html: str, pid: str) -> list:
        """Every percentage in ``html`` with no baseline named near it.

        TABLES ARE READ BY COLUMN, so a cell's label is its ``<th>``, however
        many characters of kernel signature sit between them. A flat character
        window over the panel's text models a paragraph, not a table, and would
        report the hotspot Share column as unlabelled while a reader sees its
        header perfectly well.

        TILES ARE READ ONE AT A TIME, so each is scored ALONE. Scored together,
        the noise-floor tile's "of the ANCHOR's mean" sat within 160 characters
        of the GPU tile's percentage and exempted it — a mutation that stripped
        the GPU tile's denominator survived on its neighbour's label. Panels are
        exactly the wrong grain: the whole point is that each figure carries its
        own anchor.
        """
        offenders = []
        rest = html or ""
        for table in re.findall(r"<table.*?</table>", rest, re.S):
            rest = rest.replace(table, " ")
            head = cls._text("".join(re.findall(r"<thead.*?</thead>", table, re.S)))
            for row in re.findall(r"<tr.*?</tr>", table, re.S):
                text = cls._text(row)
                if not re.search(r"[-+]?\d+(?:\.\d+)?%", text):
                    continue
                if not any(p in head or p in text for p in cls._ANCHORING):
                    offenders.append(f"#{pid} table row with no labelled "
                                     f"baseline in its header or itself: {text[:200]}")
        segments = rest.split('<div class="tile">')
        for segment in segments:
            text = cls._text(segment)
            for match in re.finditer(r"[-+]?\d+(?:\.\d+)?%", text):
                lo = max(0, match.start() - cls._ANCHOR_WINDOW)
                window = text[lo:match.end() + cls._ANCHOR_WINDOW]
                if not any(phrase in window for phrase in cls._ANCHORING):
                    offenders.append(f"#{pid} {match.group()!r} in …{window}…")
        return offenders

    def test_every_percentage_on_the_page_states_what_it_is_a_percentage_of(self):
        """THE SWEEP the operator asked for. Every figure on the page must name
        its baseline; an unlabelled percentage is the defect that produced this
        revision, and it does not stop being one in a small tile.

        PER FIGURE, NOT PER PANEL. The first version of this test asked whether
        an anchoring phrase appeared ANYWHERE in the panel, and three separate
        mutations survived it: one labelled figure elsewhere in the same panel
        exempted every unlabelled one beside it. That is the same key-too-wide
        fault this whole page revision exists to correct, committed by its own
        test.
        """
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        self.write_champion(champion_bundle())
        out = self._render()
        offenders = []
        for pid in ("champ", "tiles", "recent", "gpu", "hot", "opgate"):
            offenders += self._unanchored(out["by_id"].get(pid, ""), pid)
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_the_percentage_sweep_can_actually_find_something(self):
        """NON-VACUITY CONTROL. The sweep above passes trivially if it finds no
        percentages, or if every window is wide enough to catch some phrase by
        accident. So: prove it counts real figures, and prove it rejects one
        with nothing near it."""
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        self.write_champion(champion_bundle())
        out = self._render()
        found = sum(len(re.findall(r"[-+]?\d+(?:\.\d+)?%",
                                   self._text(out["by_id"].get(pid, ""))))
                    for pid in ("champ", "tiles", "recent", "gpu", "hot", "opgate"))
        self.assertGreater(found, 10, "the sweep found almost no percentages")
        # ...and it REJECTS an unanchored figure, in both of its two modes.
        self.assertTrue(self._unanchored(
            "<div>the champion got +12.5% and that is all we will say</div>", "x"))
        self.assertTrue(self._unanchored(
            "<table><thead><tr><th>Thing</th><th>Effect</th></tr></thead>"
            "<tbody><tr><td>a</td><td>+12.5%</td></tr></tbody></table>", "x"))
        # ...and ACCEPTS a labelled one, so it is not simply always-red.
        self.assertFalse(self._unanchored(
            "<table><thead><tr><th>Thing</th><th>Δ vs that baseline</th></tr>"
            "</thead><tbody><tr><td>a</td><td>+12.5%</td></tr></tbody></table>",
            "x"))

    def test_the_iteration_table_labels_its_effects_as_marginals(self):
        """The column header is the label a reader actually sees beside the
        number; a caption at the top of the panel is not within reach of a row
        thirty lines down."""
        self.write_loop(recorded_loop())
        recent = self._text(self._render()["by_id"]["recent"])
        self.assertIn("Effect vs anchor at the time", recent)
        self.assertIn("must not be summed", recent)

    def test_an_unreachable_hub_clears_all_three_producers(self):
        """A last successful champion render left on screen under a dead hub is
        an arbitrarily old reading presented as the current one."""
        self.write_loop(recorded_loop())
        # Driven through the harness's OWN entry-point argument rather than by
        # appending a bare call: an appended call runs at eval time, and the
        # harness then invokes `render` afterwards and paints the cleared card
        # straight back over it. That is not a hypothetical — it is what this
        # test did on its first run, and it passed nothing while looking green
        # in the other direction.
        js = self._page_js() + (
            "\nfunction __probeFetchFailure(){ renderFetchFailure('boom'); }\n")
        tmp = Path(tempfile.mkdtemp(prefix="champ-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(js, encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json"),
             "__probeFetchFailure"],
            capture_output=True, text=True, timeout=60)
        out = json.loads(proc.stdout)
        self.assertEqual(out["ran"], 1, f"the probe never ran: {out}")
        self.assertEqual(out["class_by_id"].get("champ-badge"), "badge malformed")
        self.assertEqual(out["text_by_id"].get("champ-badgetxt"), "UNKNOWN")
        self.assertIn("hub could not be reached", self._text(out["by_id"]["champ"]))


class Wiring(unittest.TestCase):

    def test_the_registry_row_advertises_the_headline(self):
        rows = {e["id"]: e for e in json.loads(
            (REPO / "dashboard/registry.json").read_text(encoding="utf-8")
        )["dashboards"]}
        blurb = rows["autokernel-loop"]["blurb"]
        self.assertIn("champion headline", blurb)
        self.assertIn("frozen production kernel", blurb)

    def test_the_page_declares_the_headline_section_and_reads_it(self):
        html = PAGE.read_text(encoding="utf-8")
        for element in ("sec-champion", "champ", "champ-badge", "champ-badgetxt"):
            self.assertIn(f'id="{element}"', html, element)

    def test_the_headline_is_the_first_section_on_the_page(self):
        """Position is part of the ruling: nothing competes for this slot."""
        html = PAGE.read_text(encoding="utf-8")
        body = html[html.index("<main>"):]
        first = re.search(r'<section id="([a-z-]+)"', body)
        self.assertEqual(first.group(1), "sec-champion")
        self.assertLess(body.index('id="sec-champion"'),
                        body.index('id="sec-opgate"'),
                        "the operator-gated card outranks the champion headline")


if __name__ == "__main__":
    unittest.main()
