"""The operator-gated headline must not be readable as live when dead.

TWO GAPS, ONE SHAPE.

A. The operator-gated ``+48.9%`` — the largest figure on the page — was read by
   ``server._read_operator_gate_bundle``, which validated schema and authority
   meticulously and **read no timestamp at all**. It therefore rendered
   identically forever after its emitter died.

B. The discovery funnel's staleness verdict existed and was correct, and was
   rendered inside a ``<details class="result-detail">`` nested inside the
   ``<details class="panel">`` that wraps the whole section — while the collapsed
   summary line showed undated lane leaders and a pursued count. A reader who
   expanded nothing read a 16-day-dead funnel as a live one. Alongside it,
   ``esc(funnel.candidate||0)`` coerced *missing* into a confident ``0``.

GAP B WENT AWAY WITH ITS PAGE, WHICH IS NOT THE SAME AS BEING FIXED. On
2026-08-30 the two AutoKernel surfaces merged: ``/kernel`` became a 301 to
``/loop`` and ``dashboard/static/kernel.html`` was deleted, because every
producer behind it was dead or frozen — ``kernel_progression.json`` among them
(the file was still being rewritten while its ``observed_through`` horizon stood
16.7 d back and was not advancing). The funnel's render assertions are therefore
gone from this file: they asserted against markup that no longer exists. The
reader ``server._read_kernel_progression`` is untouched and still serves
``/api/kernel``; nothing here covers its rendering any more, because nothing
renders it. That is a real reduction in coverage and it is recorded rather than
quietly absorbed.

GAP A MOVED. The operator-gated bundle was the ONE live producer on that page, so
its card moved to ``/loop`` and the render assertions below moved with it — same
reader, new host element (``#opgate``, and on ``/loop`` the absent state is
rendered rather than hidden, because there is no command band above it to say so).

GAP A's FIX THEN OVERCORRECTED, AND THIS FILE CHANGED WITH THE CONTRACT
(2026-08-31). The first envelope closed "forever fresh" with a 3-day wall-clock
band borrowed from a STREAMING surface — and this producer is EPISODIC, one
bundle per human campaign, not a stream. The live, perfectly current measurement
crossed its own file's third birthday and the card alarmed STALE; the operator
read it as "stale/broken — why keep it?". Staleness is now SUBJECT-ANCHORED
(``loop_status.opgate_subject_verdict``): a readable bundle is ``relevant`` /
``superseded`` / ``unverifiable`` by git facts (champion lineage, production
anchor vs the currently-resolved frozen kernel), never by clock; ``absent`` and
``malformed`` remain the artifact-level states. Age is informational, with an
ADVISORY sentence past an extreme threshold. The tests below that used to pin
the wall-clock STALE now pin the new contract; what each one GUARDS (a dead or
moved-past number must not read live; dating must be labelled; the two
producers' envelopes never merge) is unchanged — only the mechanism that
answers "is it still true" moved from the clock to the subject.

WHY THE FIXTURES ARE COPIES OF THE REAL RECORDS. Every fixture below is
``operator_gate_bundle.json`` / ``kernel_progression.json`` as the emitters
actually wrote them, mutated. Hand-authoring the key names is how a reader and its
fixture come to agree with each other and disagree with the producer — the exact
defect that left this surface's GPU panel dark while 41 tests passed over it. If
the real records are not on this host these tests SKIP loudly rather than fall
back to an invented record.

WHY THE RENDER ASSERTIONS EXECUTE THE PAGE. Asserting that a string appears in
``loop.html`` proves the source contains it, not that a reader ever sees it. The
node harness runs the real render functions against these payloads and the
assertions read the resulting innerHTML/textContent of the specific element.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "dashboard/static/loop.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"

REAL_BUNDLE = Path("/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json")

sys.path.insert(0, str(REPO))
from dashboard import loop_status  # noqa: E402
from dashboard import server  # noqa: E402
# The temp-repo builders are shared with the champion-headline suite on
# purpose: one way to pose as the frozen tree and the champion tree, not two
# that drift.
from tests.test_dashboard_champion_headline import (  # noqa: E402
    advance_production_repo, make_production_repo)

FIVE_STATES = {"relevant", "superseded", "unverifiable", "absent", "malformed"}


# --------------------------------------------------------------------------- #
# Fixtures built from the REAL emitted records
# --------------------------------------------------------------------------- #

def _real(path: Path) -> bytes:
    if not path.is_file():
        pytest.skip(f"no emitted record at {path}; refusing to invent one")
    return path.read_bytes()


class _Subject:
    """Temp champion + frozen trees posing as the SUBJECT the bundle measured.

    Every subject-anchored state is three lines of git here rather than a
    thought experiment: ``tip``/``parent`` are in the champion lineage,
    ``divergent`` is provably outside it, ``promote()`` moves production past
    every anchored bundle, and the ``break_*`` helpers make a side
    unresolvable. No 40-hex literal appears anywhere — every sha is minted by
    the temp repos.
    """

    def __init__(self, tmp_path: Path, monkeypatch) -> None:
        self._monkeypatch = monkeypatch
        self.champ = tmp_path / "champ-tree"
        self.parent = make_production_repo(
            self.champ, branch="ak/champion/llama-cpp-test")
        subprocess.run(["git", "-C", str(self.champ), "checkout", "-q", "-b",
                        "side"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.champ), "-c", "user.name=t",
                        "-c", "user.email=t@t", "commit", "-q",
                        "--allow-empty", "-m", "divergent side work"],
                       check=True, capture_output=True)
        self.divergent = subprocess.run(
            ["git", "-C", str(self.champ), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", str(self.champ), "checkout", "-q",
                        "ak/champion/llama-cpp-test"],
                       check=True, capture_output=True)
        self.tip = advance_production_repo(self.champ)
        assert self.divergent != self.tip
        self.frozen = tmp_path / "frozen-tree"
        self.prod = make_production_repo(self.frozen)
        self._missing = tmp_path / "no-such-tree"
        monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV, str(self.champ))
        monkeypatch.setenv(loop_status.FROZEN_TREE_ENV, str(self.frozen))

    def aligned(self, *, measured: str | None = None,
                anchor: str | None = None) -> dict:
        """A ``body_edit`` pointing the bundle at THIS subject."""
        return {"champion": {"branch": "ak/champion/llama-cpp-test",
                             "commit": measured or self.tip},
                "production_anchor": {"commit": anchor or self.prod}}

    def promote(self) -> str:
        return advance_production_repo(
            self.frozen, rename_to="production-consolidated-v10")

    def break_champion(self) -> None:
        self._monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV,
                                 str(self._missing))

    def break_frozen(self) -> None:
        self._monkeypatch.setenv(loop_status.FROZEN_TREE_ENV,
                                 str(self._missing))


@pytest.fixture
def subject(tmp_path, monkeypatch) -> _Subject:
    return _Subject(tmp_path, monkeypatch)


@pytest.fixture
def bundle_at(tmp_path, monkeypatch, subject):
    """Point the reader at a copy of the real bundle and return a mutator.

    The reader's verdict is subject-anchored, so the fixture ALWAYS stands up
    the posing subject trees — by default the bundle is re-pointed at them in
    the RELEVANT position (measured = champion tip, anchor = posing production
    HEAD), and a test moves the subject (or passes its own ``body_edit``) to
    reach the other states. Without this re-pointing every test would silently
    measure the REAL host trees, and a promotion on the host would flip this
    suite.
    """
    raw = _real(REAL_BUNDLE)
    target = tmp_path / "operator_gate_bundle.json"

    def place(*, body_edit=None, age_days=None, raw_bytes=None, delete=False,
              align=True):
        if delete:
            target.unlink(missing_ok=True)
        elif raw_bytes is not None:
            target.write_bytes(raw_bytes)
        else:
            value = json.loads(raw)
            if align:
                value.update(subject.aligned())
            if body_edit:
                value.update(body_edit)
            target.write_text(json.dumps(value))
        if age_days is not None:
            old = time.time() - age_days * 86400
            os.utime(target, (old, old))
        monkeypatch.setattr(server, "OPERATOR_GATE_BUNDLE_JSON", target)
        return server._read_operator_gate_bundle()

    place.raw = raw
    place.path = target
    place.subject = subject
    return place


# --------------------------------------------------------------------------- #
# GAP A — the reader
# --------------------------------------------------------------------------- #

def test_the_real_record_carries_no_date_of_its_own(bundle_at):
    """The premise of the mtime fallback, pinned against the producer.

    If a future emitter adds ``generated_at`` this fails, and the reader's
    ``generated_at_source`` labelling stops being load-bearing. That is worth
    being told about rather than discovering as a silent behaviour change.
    """
    assert "generated_at" not in json.loads(bundle_at.raw)


def test_a_relevant_bundle_reads_relevant_and_says_how_it_was_dated(bundle_at):
    # Was ``test_a_fresh_bundle_reads_fresh..``: same guard (the healthy state
    # is reachable, and the dating source is LABELLED), new verdict name — the
    # healthy state is now earned from the subject, not from a young mtime.
    got = bundle_at(age_days=0)
    fresh = got["freshness"]
    assert got["available"] is True
    assert fresh["state"] == "relevant"
    assert fresh["generated_at_source"] == "file_mtime"
    assert fresh["age_s"] is not None and fresh["age_s"] < 60
    # The weaker fact must be labelled as the weaker fact.
    assert "mtime" in fresh["detail"]


def test_an_old_bundle_with_an_unmoved_subject_reads_RELEVANT_not_stale(
        bundle_at):
    """THE defect this revision fixes, in one assertion.

    Was ``test_a_dead_emitter_reads_stale_and_the_number_is_still_carried``,
    which pinned the wall-clock STALE at 16.7 d. That test conflated two
    facts: "the emitter has not written lately" (true, and meaningless for an
    episodic producer) and "the number is no longer true" (unknowable from a
    clock). What it actually GUARDED — the number is still carried, and the
    age is still reported honestly — is kept below; the alarm that age alone
    used to raise is exactly what the operator called broken, and it is gone.
    """
    got = bundle_at(age_days=16.7)
    assert got["available"] is True
    assert got["freshness"]["state"] == "relevant"
    assert got["freshness"]["basis"] == "subject"
    # The number still rides, and the age is still an honest, visible fact...
    assert got["headline"]["effect_fraction"] == pytest.approx(0.489, abs=0.01)
    assert got["freshness"]["age_s"] == pytest.approx(16.7 * 86400, rel=0.01)
    assert "16.7 d" in got["freshness"]["detail"]
    # ...but it is informational: no advisory yet, and never an alarm state.
    assert got["freshness"]["advisory"] is None


def test_an_EXTREME_age_earns_an_advisory_sentence_not_an_alarm(bundle_at):
    """Past the advisory threshold (default 30 d) the reading says "consider
    re-measuring" — text riding on a still-calm verdict, never a state."""
    got = bundle_at(age_days=45)
    fresh = got["freshness"]
    assert fresh["state"] == "relevant"
    assert fresh["age_s"] > fresh["advisory_after_s"]
    assert fresh["advisory"] and "consider re-measuring" in fresh["advisory"]
    assert "consider re-measuring" in fresh["detail"]


def test_ancestry_broken_reads_SUPERSEDED_naming_the_champion_fact(bundle_at):
    """Subject fact one: the measured commit fell out of the champion lineage."""
    subject = bundle_at.subject
    got = bundle_at(body_edit=subject.aligned(measured=subject.divergent),
                    age_days=0.1)
    fresh = got["freshness"]
    assert fresh["state"] == "superseded"
    assert fresh["moved"] == [loop_status.OPGATE_MOVED_CHAMPION]
    assert "no longer in the champion lineage" in fresh["detail"]
    assert "promoted past" not in fresh["detail"]
    # The evidence itself still rides — superseded is not absent.
    assert got["available"] is True
    assert got["headline"]["effect_fraction"] == pytest.approx(0.489, abs=0.01)


def test_production_promoted_reads_SUPERSEDED_naming_the_anchor_fact(bundle_at):
    """Subject fact two: production moved past the bundle's baseline — and a
    freshly-written file must NOT save it, or a copy could launder a superseded
    measurement back to healthy."""
    subject = bundle_at.subject
    edit = subject.aligned()          # anchored on the PRE-promotion HEAD
    subject.promote()
    got = bundle_at(body_edit=edit, age_days=0)
    fresh = got["freshness"]
    assert fresh["state"] == "superseded"
    assert fresh["moved"] == [loop_status.OPGATE_MOVED_PRODUCTION]
    assert "promoted past" in fresh["detail"]
    assert "production-consolidated-v10" in fresh["detail"]
    assert "no longer in the champion lineage" not in fresh["detail"]


def test_both_subject_facts_moved_and_the_verdict_names_both(bundle_at):
    subject = bundle_at.subject
    edit = subject.aligned(measured=subject.divergent)
    subject.promote()
    got = bundle_at(body_edit=edit)
    fresh = got["freshness"]
    assert fresh["state"] == "superseded"
    assert set(fresh["moved"]) == {loop_status.OPGATE_MOVED_CHAMPION,
                                   loop_status.OPGATE_MOVED_PRODUCTION}
    assert "no longer in the champion lineage" in fresh["detail"]
    assert "promoted past" in fresh["detail"]


def test_an_unresolvable_tree_reads_UNVERIFIABLE_never_relevant(bundle_at):
    """"We cannot say" is its own verdict — folded into neither ``relevant``
    (an unanswerable comparison rendering healthy) nor a silent wall-clock
    fallback. Each broken side is named."""
    subject = bundle_at.subject
    edit = subject.aligned()

    subject.break_champion()
    got = bundle_at(body_edit=edit, age_days=0)
    assert got["freshness"]["state"] == "unverifiable"
    assert "champion side cannot be established" in got["freshness"]["detail"]
    assert got["available"] is True

    subject2 = _Subject(bundle_at.path.parent / "s2", bundle_at.subject._monkeypatch)
    edit2 = subject2.aligned()
    subject2.break_frozen()
    got = bundle_at(body_edit=edit2)
    assert got["freshness"]["state"] == "unverifiable"
    assert "frozen production tree cannot be resolved" in got["freshness"]["detail"]


def test_a_provably_moved_anchor_outranks_an_unverifiable_champion(bundle_at):
    """Proven movement wins: production was promoted past the anchor, so the
    verdict is SUPERSEDED even while the champion tree is unreadable."""
    subject = bundle_at.subject
    edit = subject.aligned()
    subject.promote()
    subject.break_champion()
    got = bundle_at(body_edit=edit)
    assert got["freshness"]["state"] == "superseded"
    assert got["freshness"]["moved"] == [loop_status.OPGATE_MOVED_PRODUCTION]


def test_absent_and_malformed_are_different_readings(bundle_at):
    absent = bundle_at(delete=True)
    malformed = bundle_at(raw_bytes=bundle_at.raw[: len(bundle_at.raw) // 2])
    assert absent["freshness"]["state"] == "absent"
    assert absent["artifact_present"] is False
    assert malformed["freshness"]["state"] == "malformed"
    assert malformed["artifact_present"] is True
    assert absent["freshness"]["detail"] != malformed["freshness"]["detail"]


def test_an_empty_bundle_is_malformed_not_absent(bundle_at):
    """A writer that died between create and rename is an emitter bug."""
    got = bundle_at(raw_bytes=b"")
    assert got["freshness"]["state"] == "malformed"
    assert got["artifact_present"] is True


def test_a_body_generated_at_overrides_a_freshly_touched_file(bundle_at):
    """A copied file has a new mtime and no new measurement behind it.

    This used to assert the 20-day body stamp produced STALE. What it GUARDS is
    the dating, not the alarm: the age the page shows must come from the
    producer's own stamp, so a copy or a ``touch`` cannot make old evidence
    look newly measured. The subject verdict is orthogonal and stays calm.
    """
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                          time.gmtime(time.time() - 20 * 86400))
    got = bundle_at(body_edit={"generated_at": stamp}, age_days=0)
    assert got["freshness"]["generated_at_source"] == "body_generated_at"
    assert got["freshness"]["age_s"] == pytest.approx(20 * 86400, rel=0.01)
    assert got["freshness"]["state"] == "relevant"


def test_a_future_dated_bundle_is_malformed_not_silently_dated(bundle_at):
    # The guard survives the contract change unweakened: an impossible date is
    # an emitter defect and must not be rendered as an informational age —
    # even though age no longer decides any verdict.
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                          time.gmtime(time.time() + 86400))
    got = bundle_at(body_edit={"generated_at": stamp})
    assert got["freshness"]["state"] == "malformed"
    assert "FUTURE" in got["freshness"]["detail"]


def test_a_refused_bundle_still_carries_an_envelope(bundle_at):
    """Refusal on authority must not drop back to the old envelope-less shape."""
    got = bundle_at(body_edit={"promotion_claim": True})
    assert got["available"] is False
    assert got["freshness"]["state"] in FIVE_STATES


def test_every_reading_carries_an_envelope_and_only_the_five_states(bundle_at):
    """Structural: no path out of the reader returns an unverdicted number —
    and every one of the five states is actually reachable."""
    subject = bundle_at.subject
    divergent_edit = subject.aligned(measured=subject.divergent)
    unverifiable_edit = subject.aligned()
    seen = set()
    cases = [{"age_days": 0}, {"age_days": 30},
             {"body_edit": divergent_edit},
             {"delete": True},
             {"raw_bytes": b""}, {"raw_bytes": b"{not json"},
             {"raw_bytes": b"[]"},
             {"body_edit": {"schema": "epyc.autokernel.cumulative_performance.v2"}},
             {"body_edit": {"authority": "nonpromotable_candidate_only_discovery"}},
             {"body_edit": {"promotion_claim": True}}]
    for kwargs in cases:
        got = bundle_at(**kwargs)
        assert "freshness" in got, kwargs
        state = got["freshness"]["state"]
        assert state in FIVE_STATES, (kwargs, state)
        seen.add(state)
    subject.break_champion()
    got = bundle_at(body_edit=unverifiable_edit)
    assert got["freshness"]["state"] in FIVE_STATES
    seen.add(got["freshness"]["state"])
    assert FIVE_STATES <= seen


def test_a_producer_declared_budget_is_honoured_and_clamped(bundle_at):
    """The declared ``stale_after_s`` still wins and is still clamped exactly
    as before — its CONSEQUENCE changed (it is the ADVISORY threshold now,
    ``advisory_after_s``), not the honouring or the clamps, and the last
    assertions pin that crossing it advises rather than alarms."""
    from dashboard import panels
    assert bundle_at(body_edit={"stale_after_s": 60 * 60})["freshness"][
        "advisory_after_s"] == 3600
    # A threshold wider than any real horizon declares itself and monitors
    # nothing; a zero threshold nags on every reading between two emissions.
    assert bundle_at(body_edit={"stale_after_s": 10 ** 9})["freshness"][
        "advisory_after_s"] == float(panels.MAX_STALE_S)
    assert bundle_at(body_edit={"stale_after_s": 0})["freshness"][
        "advisory_after_s"] == server.OPERATOR_GATE_BUNDLE_ADVISORY_AFTER_S
    # Crossing the declared threshold produces ADVICE on a calm verdict — the
    # clamp cannot be "honoured" back into a wall-clock alarm.
    crossed = bundle_at(body_edit={"stale_after_s": 60 * 60}, age_days=0.5)
    assert crossed["freshness"]["state"] == "relevant"
    assert crossed["freshness"]["advisory"]


# --------------------------------------------------------------------------- #
# The rendered page
# --------------------------------------------------------------------------- #

pytestmark_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node not available")


def _page_js() -> str:
    html = PAGE.read_text(encoding="utf-8")
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    assert blocks, "no script blocks found in loop.html"
    return "\n".join(blocks)


def _render(payload: dict, fn: str, tmp_path: Path) -> dict:
    (tmp_path / "page.js").write_text(_page_js(), encoding="utf-8")
    (tmp_path / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        ["node", str(HARNESS), str(tmp_path / "page.js"),
         str(tmp_path / "payload.json"), fn],
        capture_output=True, text=True, timeout=120)
    assert proc.stdout.strip(), f"harness produced no output; stderr={proc.stderr[:600]}"
    out = json.loads(proc.stdout)
    assert out["threw"] == [], f"{fn} threw: {out['threw']}"
    assert out["ran"] == 1, f"{fn} did not run (ran={out['ran']})"
    return out


@pytest.fixture(scope="module")
def loop_body() -> dict:
    """The REAL ``/api/loop`` payload — the one ``render`` is fed in a browser.

    Its ``operator_gates`` key is overwritten per test with a mutated bundle; every
    other key stays the server's own, so a page-side fault outside the champion
    card still surfaces here rather than being fixtured away.
    """
    return server.loop_payload()


def _text(html: str) -> str:
    """Tag-stripped text of a rendered fragment.

    A sentence a reader sees as one phrase can be split across an ``<em>`` in the
    markup, so a substring assertion against innerHTML fails on a rewording that
    changes nothing visible — and gets "fixed" by weakening it. Assert on what the
    reader reads.
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _opgate(payload: dict, tmp_path: Path) -> str:
    """Render the whole page and return the champion card's innerHTML.

    The FULL ``render``, not ``renderOperatorGate`` alone: the card sits on a page
    with another producer on it, and a card that only renders when called directly
    is a card a reader never sees. The harness keys ``by_id`` by BARE id for a page
    that uses ``getElementById`` — asking it for ``"#opgate"`` returns ``""`` for
    every input, which is a probe outside the tool, passing for the wrong reason on
    all of them at once.
    """
    out = _render(payload, "render", tmp_path)
    assert "opgate" in out["by_id"], (
        "the harness reported no #opgate element at all; the card did not render "
        f"and every assertion about its content would be vacuous. ids: "
        f"{sorted(out['by_id'])}")
    return out["by_id"]["opgate"]


@pytestmark_node
def test_a_superseded_bundle_renders_a_loud_verdict_beside_the_number(
        bundle_at, loop_body, tmp_path):
    """The regression this exists for: a moved-past number that read as live.

    Was ``test_a_stale_bundle_renders_a_stale_verdict_beside_the_number``. The
    guard is IDENTICAL — a number whose claim no longer holds must carry a loud
    verdict before it and lose its live colour — only the cause changed: the
    subject moving (here, ancestry broken), not the file aging.
    """
    subject = bundle_at.subject
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(
        body_edit=subject.aligned(measured=subject.divergent), age_days=0.1)
    card = _opgate(payload, tmp_path)
    assert "48.9%" in card, "the operator-gated figure did not render at all"
    assert "SUPERSEDED" in card, (
        "the number rendered with no supersession verdict beside it")
    assert "no longer in the champion lineage" in _text(card)
    assert "SUPERSEDED" in card.split("48.9%")[0], (
        "the verdict must precede the number, not trail it")
    # And it must not be painted as a live gain. `og-num dated` is the amber
    # rendering; `og-num pos` is the green one.
    assert "og-num dated" in card and "og-num pos" not in card, (
        "a figure whose subject moved was painted as a current gain")


@pytestmark_node
def test_a_promoted_past_bundle_renders_the_loud_verdict_too(
        bundle_at, loop_body, tmp_path):
    """The OTHER subject fact, executed at the page: production promoted past
    the bundle's anchor renders the same loud treatment, naming the anchor."""
    subject = bundle_at.subject
    edit = subject.aligned()
    subject.promote()
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(body_edit=edit, age_days=0)
    card = _opgate(payload, tmp_path)
    assert "SUPERSEDED" in card
    assert "promoted past" in _text(card)
    assert "og-num dated" in card and "og-num pos" not in card


@pytestmark_node
def test_an_unverifiable_subject_says_so_and_renders_no_calm_state(
        bundle_at, loop_body, tmp_path):
    """Unresolvable trees must not fold into the healthy rendering — and must
    not fall back to a wall-clock word either."""
    subject = bundle_at.subject
    edit = subject.aligned()
    subject.break_champion()
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(body_edit=edit, age_days=0)
    card = _opgate(payload, tmp_path)
    assert "UNVERIFIABLE" in card
    assert "cannot be established" in _text(card)
    assert "STALE" not in card
    assert "og-num dated" in card and "og-num pos" not in card, (
        "an unverifiable figure was painted as a current gain")


@pytestmark_node
def test_a_relevant_OLD_bundle_renders_CALM(bundle_at, loop_body, tmp_path):
    """The operator's exact scenario, executed: 3.1 days old, subject unmoved.

    The old contract alarmed STALE here (3-day wall-clock band). The new card
    must be calm: no alarm banner, the age informational in the summary line
    with the single-slot guarantee spelled out, and the number in its live
    colour — not amber.
    """
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(age_days=3.1)
    out = _render(payload, "render", tmp_path)
    card = out["by_id"]["opgate"]
    assert "48.9%" in card
    for alarm in ("STALE", "SUPERSEDED", "UNVERIFIABLE", "ABSENT", "MALFORMED"):
        assert alarm not in card, f"a calm state rendered the {alarm} alarm"
    assert "og-verdict" not in card, "a banner rendered over the healthy state"
    text = _text(card)
    assert "measured 3.1d ago" in text
    assert "no newer serving measurement exists" in text
    assert "og-num pos" in card and "og-num dated" not in card, (
        "age alone ambered a relevant figure")
    # The badge is the neutral evidence pill, not the stale/amber style.
    badge = out["text_by_id"].get("opgate-badgetxt") or ""
    assert badge.startswith("evidence ·"), badge
    assert out["class_by_id"].get("opgate-badge") == "badge relevant"


@pytestmark_node
def test_an_EXTREME_age_renders_advice_and_stays_calm(
        bundle_at, loop_body, tmp_path):
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(age_days=45)
    card = _opgate(payload, tmp_path)
    assert "consider re-measuring" in _text(card)
    for alarm in ("STALE", "SUPERSEDED", "UNVERIFIABLE"):
        assert alarm not in card
    assert "og-num pos" in card and "og-num dated" not in card, (
        "the >30d advisory coloured the number amber on its own")


@pytestmark_node
def test_absent_and_malformed_bundles_render_differently(
        bundle_at, loop_body, tmp_path):
    absent = dict(loop_body)
    absent["operator_gates"] = bundle_at(delete=True)
    broken = dict(loop_body)
    broken["operator_gates"] = bundle_at(
        raw_bytes=bundle_at.raw[: len(bundle_at.raw) // 2])
    a = _opgate(absent, tmp_path)
    m = _opgate(broken, tmp_path)
    assert a != m, "an absent emitter and a broken one render identically"
    assert "48.9%" not in a and "48.9%" not in m
    assert "ABSENT" in a and "MALFORMED" not in a
    assert "MALFORMED" in m and "ABSENT" not in m


@pytestmark_node
def test_an_absent_bundle_is_rendered_not_hidden(bundle_at, loop_body, tmp_path):
    """The behaviour that had to CHANGE when the card moved.

    On the retired page this box hid itself (``display:none``) when the bundle was
    absent, because a command band above it carried the same fact. There is no
    command band on ``/loop``, so hiding it would put the original defect back in a
    new place: a section that renders nothing is indistinguishable from a section
    whose producer died.
    """
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(delete=True)
    card = _opgate(payload, tmp_path)
    assert card.strip(), "an absent bundle rendered an empty card"
    assert "ABSENT" in card
    assert "not a measured zero" in _text(card).lower(), (
        "the card must say what absence is NOT, or a reader supplies the meaning")
    # And it must name the path it looked at, or the investigation has nowhere to go.
    assert "operator_gate_bundle.json" in card


@pytestmark_node
def test_every_state_renders_a_DISTINCT_card(bundle_at, loop_body, tmp_path):
    """Structural: no two of the FIVE collapse into the same rendering.

    Collapsing any pair is how a dead producer renders as a live one — the same
    rule the loop's own banner obeys, applied to the second producer on the page.
    ``unverifiable`` folding into ``relevant`` is the pair that matters most: an
    unanswerable comparison rendering as a healthy one.
    """
    subject = bundle_at.subject
    promoted_edit = subject.aligned()
    cases = {
        "relevant": {"age_days": 0},
        "superseded": {"body_edit": subject.aligned(
            measured=subject.divergent)},
        "absent": {"delete": True},
        "malformed": {"raw_bytes": b"{not json"},
    }
    seen = {}
    for label, kwargs in cases.items():
        payload = dict(loop_body)
        payload["operator_gates"] = bundle_at(**kwargs)
        seen[label] = _opgate(payload, tmp_path)
    subject.break_champion()
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(body_edit=promoted_edit)
    seen["unverifiable"] = _opgate(payload, tmp_path)
    assert len(set(seen.values())) == 5, (
        "two or more verdict states render identically: "
        + repr({k: v[:80] for k, v in seen.items()}))


@pytestmark_node
def test_the_loops_freshness_never_dates_the_champion_bundle(
        bundle_at, loop_body, tmp_path):
    """Two producers on one page, and neither may certify the other's verdict.

    A live loop beside a SUPERSEDED bundle must still read SUPERSEDED on the
    card, and the loop's badge must not catch it. This is the merge's central
    risk: one page, one header badge, and a reader who dates everything on it
    by the loudest green thing in view. The guard is envelope INDEPENDENCE and
    it is unchanged from the wall-clock era — only the alarming verdict's name
    moved (STALE → SUPERSEDED), because for this producer the alarm is now
    earned by its subject moving rather than by its file aging.
    """
    subject = bundle_at.subject
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(
        body_edit=subject.aligned(measured=subject.divergent), age_days=30)
    out = _render(payload, "render", tmp_path)
    assert out["by_id"]["opgate"], "the card did not render"
    assert "SUPERSEDED" in out["by_id"]["opgate"]
    assert "SUPERSEDED" in (out["text_by_id"].get("opgate-badgetxt") or ""), (
        "the champion card's own badge did not carry its own verdict")
    # ...while the loop's own badge is reporting the loop, not the bundle.
    assert "SUPERSEDED" not in (out["text_by_id"].get("freshtxt") or ""), (
        "the loop's badge inherited the bundle's verdict; the two envelopes "
        "have been folded together")

    # THE CLASS, NOT ONLY THE WORD. A badge says its verdict twice: in its text
    # and in the className that colours it. Driving the class from the OTHER
    # producer yields a green pill reading "SUPERSEDED" — which the two
    # assertions above both pass. That mutation survived this test until the
    # harness was taught to report className at all.
    classes = out["class_by_id"]
    assert classes.get("opgate-badge") == "badge superseded", (
        "the champion badge is not COLOURED by its own producer's state: "
        f"{classes.get('opgate-badge')!r}")
    assert classes.get("fresh") == "badge fresh", (
        "the loop's badge is not coloured by the loop's state: "
        f"{classes.get('fresh')!r}")

    # And the independence holds in the CALM direction too: an old-but-relevant
    # bundle must not paint the loop old, and the loop's liveness must not be
    # what made the bundle calm (the calm came from the subject verdict).
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(age_days=30)
    out = _render(payload, "render", tmp_path)
    assert out["class_by_id"].get("opgate-badge") == "badge relevant"
    assert "30.0d" in (out["text_by_id"].get("opgate-badgetxt") or "")
