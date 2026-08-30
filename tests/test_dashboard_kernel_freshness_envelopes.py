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
reader, same four states, new host element (``#opgate``, and on ``/loop`` the
absent state is rendered rather than hidden, because there is no command band
above it to say so).

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
from dashboard import server  # noqa: E402

FOUR_STATES = {"fresh", "stale", "absent", "malformed"}


# --------------------------------------------------------------------------- #
# Fixtures built from the REAL emitted records
# --------------------------------------------------------------------------- #

def _real(path: Path) -> bytes:
    if not path.is_file():
        pytest.skip(f"no emitted record at {path}; refusing to invent one")
    return path.read_bytes()


@pytest.fixture
def bundle_at(tmp_path, monkeypatch):
    """Point the reader at a copy of the real bundle and return a mutator."""
    raw = _real(REAL_BUNDLE)
    target = tmp_path / "operator_gate_bundle.json"

    def place(*, body_edit=None, age_days=None, raw_bytes=None, delete=False):
        if delete:
            target.unlink(missing_ok=True)
        elif raw_bytes is not None:
            target.write_bytes(raw_bytes)
        else:
            value = json.loads(raw)
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


def test_a_fresh_bundle_reads_fresh_and_says_how_it_was_dated(bundle_at):
    got = bundle_at(age_days=0)
    fresh = got["freshness"]
    assert got["available"] is True
    assert fresh["state"] == "fresh"
    assert fresh["generated_at_source"] == "file_mtime"
    assert fresh["age_s"] is not None and fresh["age_s"] < 60
    # The weaker fact must be labelled as the weaker fact.
    assert "mtime" in fresh["detail"]


def test_a_dead_emitter_reads_stale_and_the_number_is_still_carried(bundle_at):
    """Stale is not absent: the measurement happened, its currency is in doubt."""
    got = bundle_at(age_days=16.7)
    assert got["available"] is True
    assert got["freshness"]["state"] == "stale"
    assert got["freshness"]["age_s"] > got["freshness"]["stale_after_s"]
    assert got["headline"]["effect_fraction"] == pytest.approx(0.489, abs=0.01)
    assert "16.7 d" in got["freshness"]["detail"]


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
    """A copied file has a new mtime and no new measurement behind it."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                          time.gmtime(time.time() - 20 * 86400))
    got = bundle_at(body_edit={"generated_at": stamp}, age_days=0)
    assert got["freshness"]["generated_at_source"] == "body_generated_at"
    assert got["freshness"]["state"] == "stale"


def test_a_future_dated_bundle_cannot_read_fresh_forever(bundle_at):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                          time.gmtime(time.time() + 86400))
    got = bundle_at(body_edit={"generated_at": stamp})
    assert got["freshness"]["state"] == "malformed"
    assert "FUTURE" in got["freshness"]["detail"]


def test_a_refused_bundle_still_carries_an_envelope(bundle_at):
    """Refusal on authority must not drop back to the old envelope-less shape."""
    got = bundle_at(body_edit={"promotion_claim": True})
    assert got["available"] is False
    assert got["freshness"]["state"] in FOUR_STATES


def test_every_reading_carries_an_envelope_and_only_the_four_states(bundle_at):
    """Structural: no path out of the reader returns an undated number."""
    seen = set()
    for kwargs in ({"age_days": 0}, {"age_days": 30}, {"delete": True},
                   {"raw_bytes": b""}, {"raw_bytes": b"{not json"},
                   {"raw_bytes": b"[]"},
                   {"body_edit": {"schema": "epyc.autokernel.cumulative_performance.v2"}},
                   {"body_edit": {"authority": "nonpromotable_candidate_only_discovery"}},
                   {"body_edit": {"promotion_claim": True}}):
        got = bundle_at(**kwargs)
        assert "freshness" in got, kwargs
        state = got["freshness"]["state"]
        assert state in FOUR_STATES, (kwargs, state)
        seen.add(state)
    assert {"fresh", "stale", "absent", "malformed"} <= seen


def test_a_producer_declared_budget_is_honoured_and_clamped(bundle_at):
    from dashboard import panels
    assert bundle_at(body_edit={"stale_after_s": 60 * 60})["freshness"][
        "stale_after_s"] == 3600
    # A budget wider than any real cadence declares a threshold and monitors
    # nothing; a zero budget makes every reading stale between two emissions.
    assert bundle_at(body_edit={"stale_after_s": 10 ** 9})["freshness"][
        "stale_after_s"] == float(panels.MAX_STALE_S)
    assert bundle_at(body_edit={"stale_after_s": 0})["freshness"][
        "stale_after_s"] == server.OPERATOR_GATE_BUNDLE_STALE_AFTER_S


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
def test_a_stale_bundle_renders_a_stale_verdict_beside_the_number(
        bundle_at, loop_body, tmp_path):
    """The regression this exists for: a dead number that read as live."""
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(age_days=16.7)
    card = _opgate(payload, tmp_path)
    assert "48.9%" in card, "the operator-gated figure did not render at all"
    assert "STALE" in card, "the number rendered with no staleness verdict beside it"
    assert "16.7 d" in card
    assert "STALE" in card.split("48.9%")[0], (
        "the verdict must precede the number, not trail it")
    # And it must not be painted as a live gain. `og-num dated` is the amber
    # rendering; `og-num pos` is the green one.
    assert "og-num dated" in card and "og-num pos" not in card, (
        "a figure outside its envelope was painted as a current gain")


@pytestmark_node
def test_a_fresh_bundle_renders_no_stale_badge(bundle_at, loop_body, tmp_path):
    """The negative control: the badge must be caused by the data, not printed
    unconditionally. Without this, the assertion above passes over a page that
    always says STALE."""
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(age_days=0)
    card = _opgate(payload, tmp_path)
    assert "48.9%" in card
    assert "STALE" not in card and "ABSENT" not in card and "MALFORMED" not in card
    assert "og-num pos" in card, "a current, positive figure was not rendered as one"


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
    """Structural: no two of the four collapse into the same rendering.

    Collapsing any pair is how a dead producer renders as a live one — the same
    rule the loop's own banner obeys, applied to the second producer on the page.
    """
    cases = {
        "fresh": {"age_days": 0},
        "stale": {"age_days": 30},
        "absent": {"delete": True},
        "malformed": {"raw_bytes": b"{not json"},
    }
    seen = {}
    for label, kwargs in cases.items():
        payload = dict(loop_body)
        payload["operator_gates"] = bundle_at(**kwargs)
        seen[label] = _opgate(payload, tmp_path)
    assert len(set(seen.values())) == 4, (
        "two or more freshness states render identically: "
        + repr({k: v[:80] for k, v in seen.items()}))


@pytestmark_node
def test_the_loops_freshness_never_dates_the_champion_bundle(
        bundle_at, loop_body, tmp_path):
    """Two producers on one page, and neither may certify the other's silence.

    A fresh loop beside a stale bundle must still read STALE on the card. This is
    the merge's central risk: one page, one header badge, and a reader who dates
    everything on it by the loudest green thing in view.
    """
    payload = dict(loop_body)
    payload["operator_gates"] = bundle_at(age_days=30)
    out = _render(payload, "render", tmp_path)
    assert out["by_id"]["opgate"], "the card did not render"
    assert "STALE" in out["by_id"]["opgate"]
    assert "STALE" in (out["text_by_id"].get("opgate-badgetxt") or ""), (
        "the champion card's own badge did not carry its own verdict")
    # ...while the loop's own badge is reporting the loop, not the bundle.
    assert "STALE" not in (out["text_by_id"].get("freshtxt") or ""), (
        "the loop's badge inherited the bundle's staleness; the two envelopes "
        "have been folded together")

    # THE CLASS, NOT ONLY THE WORD. A badge says its verdict twice: in its text
    # and in the className that colours it. Driving the class from the OTHER
    # producer yields a green pill reading "STALE" — which the two assertions
    # above both pass. That mutation survived this test until the harness was
    # taught to report className at all.
    classes = out["class_by_id"]
    assert classes.get("opgate-badge") == "badge stale", (
        "the champion badge is not COLOURED by its own producer's state: "
        f"{classes.get('opgate-badge')!r}")
    assert classes.get("fresh") == "badge fresh", (
        "the loop's badge is not coloured by the loop's state: "
        f"{classes.get('fresh')!r}")
