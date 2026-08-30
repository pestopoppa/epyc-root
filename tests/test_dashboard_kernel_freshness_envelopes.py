"""The two headline numbers on /kernel must not be readable as live when dead.

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

WHY THE FIXTURES ARE COPIES OF THE REAL RECORDS. Every fixture below is
``operator_gate_bundle.json`` / ``kernel_progression.json`` as the emitters
actually wrote them, mutated. Hand-authoring the key names is how a reader and its
fixture come to agree with each other and disagree with the producer — the exact
defect that left this surface's GPU panel dark while 41 tests passed over it. If
the real records are not on this host these tests SKIP loudly rather than fall
back to an invented record.

WHY THE RENDER ASSERTIONS EXECUTE THE PAGE. Asserting that a string appears in
``kernel.html`` proves the source contains it, not that a reader ever sees it. The
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
PAGE = REPO / "dashboard/static/kernel.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"

REAL_BUNDLE = Path("/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json")
REAL_PROGRESSION = Path("/mnt/raid0/llm/autokernel/surface/kernel_progression.json")

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


@pytest.fixture
def progression_at(tmp_path, monkeypatch):
    raw = _real(REAL_PROGRESSION)
    target = tmp_path / "kernel_progression.json"

    def place(*, body_edit=None, drop=(), raw_bytes=None, delete=False):
        if delete:
            target.unlink(missing_ok=True)
        elif raw_bytes is not None:
            target.write_bytes(raw_bytes)
        else:
            value = json.loads(raw)
            for key in drop:
                value.pop(key, None)
            if body_edit:
                value.update(body_edit)
            target.write_text(json.dumps(value))
        monkeypatch.setattr(server, "KERNEL_PROGRESSION_JSON", target)
        return server._read_kernel_progression()

    place.raw = raw
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
    assert blocks, "no script blocks found in kernel.html"
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
def live_payload() -> dict:
    """The REAL /api/kernel/live payload — the one renderCommandBand is fed."""
    return server._discovery_live_read()[0]


@pytestmark_node
def test_a_stale_bundle_renders_a_stale_verdict_beside_the_number(
        bundle_at, live_payload, tmp_path):
    """The regression this exists for: a dead number that read as live."""
    payload = dict(live_payload)
    payload["operator_gates"] = bundle_at(age_days=16.7)
    out = _render(payload, "renderCommandBand", tmp_path)
    sub = out["by_id"]["#cmd-aggregate-sub"]
    assert "48.9%" in sub, "the operator-gated figure did not render at all"
    assert "STALE" in sub, "the number rendered with no staleness verdict beside it"
    assert "16.7 d" in sub
    # And the card must not be painted as a live gain.
    assert "STALE" in sub.split("48.9%")[0], (
        "the verdict must precede the number, not trail it")


@pytestmark_node
def test_a_fresh_bundle_renders_no_stale_badge(bundle_at, live_payload, tmp_path):
    """The negative control: the badge must be caused by the data, not printed
    unconditionally. Without this, the assertion above passes over a page that
    always says STALE."""
    payload = dict(live_payload)
    payload["operator_gates"] = bundle_at(age_days=0)
    sub = _render(payload, "renderCommandBand", tmp_path)["by_id"]["#cmd-aggregate-sub"]
    assert "48.9%" in sub
    assert "STALE" not in sub and "ABSENT" not in sub and "MALFORMED" not in sub


@pytestmark_node
def test_absent_and_malformed_bundles_render_differently(
        bundle_at, live_payload, tmp_path):
    absent = dict(live_payload); absent["operator_gates"] = bundle_at(delete=True)
    broken = dict(live_payload)
    broken["operator_gates"] = bundle_at(raw_bytes=bundle_at.raw[: len(bundle_at.raw) // 2])
    a = _render(absent, "renderCommandBand", tmp_path)["by_id"]["#cmd-aggregate-sub"]
    m = _render(broken, "renderCommandBand", tmp_path)["by_id"]["#cmd-aggregate-sub"]
    assert a != m, "an absent emitter and a broken one render identically"
    assert "48.9%" not in a and "48.9%" not in m
    assert "cannot read" in m, m
    assert "unmeasured" in a, a


# --------------------------------------------------------------------------- #
# GAP B — the funnel
# --------------------------------------------------------------------------- #

def _progression_payload(progression: dict) -> dict:
    return {"_progression": progression, "_activity": {"current_state": {}}}


@pytestmark_node
def test_the_collapsed_summary_carries_the_funnels_staleness(
        progression_at, tmp_path):
    """Visible WITHOUT expanding anything — the whole point of gap B.

    ``#progression-headline`` is the text inside the panel's ``<summary>``: it is
    what a reader sees while the section is shut.
    """
    payload = _progression_payload(progression_at())
    out = _render(payload, "renderProgression", tmp_path)
    summary = out["by_id"]["#progression-headline"] or out["text_by_id"]["#progression-headline"]
    assert summary, "the summary line rendered nothing"
    assert "STALE" in summary, (
        "the collapsed summary shows funnel numbers with no staleness verdict: "
        + summary)


@pytestmark_node
def test_a_fresh_projection_leaves_the_summary_unbadged(progression_at, tmp_path):
    """Negative control for the badge above."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = _progression_payload(progression_at(body_edit={"observed_through": now}))
    out = _render(payload, "renderProgression", tmp_path)
    summary = out["by_id"]["#progression-headline"] or out["text_by_id"]["#progression-headline"]
    assert "STALE" not in summary and "ABSENT" not in summary, summary


@pytestmark_node
def test_the_stale_banner_is_not_inside_a_disclosure(progression_at, tmp_path):
    """A verdict a reader has to click for is a verdict a reader does not read."""
    out = _render(_progression_payload(progression_at()), "renderProgression", tmp_path)
    box = out["by_id"]["#progression"]
    head, _, _ = box.partition("<details")
    assert "STALE" in head, (
        "the staleness banner is only rendered inside a <details>")
    assert head.index("STALE") < head.index("hero-card"), (
        "the banner must precede the hero cards it qualifies")


@pytestmark_node
def test_a_missing_funnel_count_renders_unknown_not_zero(
        progression_at, tmp_path):
    """`funnel.candidate||0` made a missing number indistinguishable from a real
    zero — and `0 -> 0 -> 0 -> 0` is a perfectly plausible funnel."""
    out = _render(_progression_payload(progression_at(drop=["funnel"])),
                  "renderProgression", tmp_path)
    box = out["by_id"]["#progression"]
    value = box.split('<div class="hero-label">Funnel</div>')[1].split("</div>")[0]
    assert "?" in value, f"a missing funnel count did not render as unknown: {value}"
    assert "0" not in value, f"a missing funnel count rendered as a number: {value}"
    assert "not reported" in box


@pytestmark_node
def test_a_real_zero_still_renders_as_zero(progression_at, tmp_path):
    """The other half: unknown must not swallow a genuine measured zero. The real
    record already reports `champion: 0` and `promotable: 0`."""
    out = _render(_progression_payload(progression_at()), "renderProgression", tmp_path)
    box = out["by_id"]["#progression"]
    value = box.split('<div class="hero-label">Funnel</div>')[1].split("</div>")[0]
    assert "38" in value and "0" in value, value
    assert "?" not in value, f"a reported count rendered as unknown: {value}"


@pytestmark_node
def test_an_absent_projection_says_absent_not_stale(progression_at, tmp_path):
    out = _render(_progression_payload(progression_at(delete=True)),
                  "renderProgression", tmp_path)
    box = out["by_id"]["#progression"]
    summary = out["by_id"]["#progression-headline"] or out["text_by_id"]["#progression-headline"]
    assert "ABSENT" in summary, summary
    assert "STALE" not in summary, summary
    assert "no producer" in box


@pytestmark_node
def test_a_malformed_projection_says_malformed_not_absent(
        progression_at, tmp_path):
    out = _render(
        _progression_payload(
            progression_at(raw_bytes=progression_at.raw[: len(progression_at.raw) // 2])),
        "renderProgression", tmp_path)
    summary = out["by_id"]["#progression-headline"] or out["text_by_id"]["#progression-headline"]
    box = out["by_id"]["#progression"]
    assert "MALFORMED" in summary, summary
    assert "ABSENT" not in summary, summary
    assert "cannot read it" in box, box
