"""Hub-side reader for the rebuilt AutoKernel loop's own status contract.

WHY THIS IS A SEPARATE MODULE
-----------------------------
The operator had **zero visibility** into the rebuilt loop: the dashboard showed
only the superseded deployment ``gpu-discovery-champion-v37`` as STOPPED — which
was correct, it *was* stopped at 2026-08-28T14:23Z — while the new loop ran as a
process the dashboard knew nothing about. A loop nobody can see is a loop nobody
can trust.

It is NOT bolted onto the existing Kernel-R&D surface in ``server.py``. That
surface pins 29 source paths and 47 content digests of another repository's
modules and is slated for wholesale rewrite; adding to it would re-arm that
landmine and couple a brand-new contract to a dying one. This is a small, clean,
separate surface with its own page, its own registry row and its own data probe.

THE PRODUCER OWNS THE SCHEMA; THIS SIDE ONLY READS
--------------------------------------------------
Contract: ``epyc.autokernel.loop_status.v1``, written atomically by
``scripts/kernel_rnd/autokernel/loop/status.py`` in **epyc-inference-research**
into the loop's store root (in practice
``/mnt/raid0/llm/autokernel/loop-memory/loop-status.json``). Per the plane rule
in ``dashboard/README.md`` the data contract lives with the subsystem it
observes; the page, the nav row and the probe live here. The hub **never imports
that package** — exactly as it never imports ``autokernel.dashboard`` for the
``kernel`` panel — so this module re-reads the same file with the same
semantics rather than pinning a cross-repo module path or digest.

FOUR-VALUED FRESHNESS, AND THE FOURTH IS NOT A LUXURY
-----------------------------------------------------
``absent`` / ``malformed`` / ``stale`` / ``fresh``. Collapsing ``absent`` into
``stale`` is how a dead producer renders as a clean, empty, trusted page — the
same lesson ``server.py`` records in its ``[]``-vs-``null`` comment on
``_read_kernel_contract``: ``[]`` says "the producer reported and there is
nothing", ``null`` says "no producer reported". So ``payload()["loop"]`` is
``None``, never ``{}``, when nothing readable was found.

ONE DELIBERATE REFINEMENT over the producer's own helper: its ``read()`` returns
``None`` for a file that exists but cannot be parsed, and ``freshness(None)``
then says ``absent``. Here a corrupt, empty or half-written file reads
``malformed`` and carries ``reader_error``, because **broken is not the same
fact as never-exported** (``server.py``'s ``READER_ERROR_KEY``): one points the
investigation at the producer's writer, the other at the producer's existence.
The three states the contract requires stay distinct; a fourth is added, none
are merged.

NOTHING IS CACHED. Every call re-reads the file. A cached value can outlive the
freshness envelope that is the entire point of the envelope.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, Optional

from dashboard import panels

#: The producer's schema string. A body carrying anything else is not this
#: contract and is refused as malformed rather than rendered on a page whose
#: field names would then mean something else.
STATUS_SCHEMA = "epyc.autokernel.loop_status.v1"
STATUS_FILENAME = "loop-status.json"

#: Mirrors ``status.DEFAULT_STALE_AFTER_S``. Used only when a body omits its own
#: budget; the producer's declared ``stale_after_s`` always wins.
DEFAULT_STALE_AFTER_S = 1800.0

#: Narrowest budget the hub will honour from a producer-declared value. A tiny
#: budget would make every reading stale between two publishes.
MIN_STALE_AFTER_S = 60.0

#: Where the loop keeps its memory, and therefore its status file. Overridable
#: for tests and for a second store root; resolved PER CALL, never at import, so
#: a test can point one request somewhere else without reloading the hub.
STORE_ROOT_ENV = "AUTOKERNEL_LOOP_STORE_ROOT"
DEFAULT_STORE_ROOT = Path("/mnt/raid0/llm/autokernel/loop-memory")

STATE_FRESH = "fresh"
STATE_STALE = "stale"
STATE_ABSENT = "absent"
STATE_MALFORMED = "malformed"
#: The four are distinct on purpose. If any two collapse, a dead producer can
#: render as a live one.
STATES = (STATE_FRESH, STATE_STALE, STATE_ABSENT, STATE_MALFORMED)

#: What absence MEANS here, in one sentence, travelling with every absent
#: reading. A panel that renders nothing without saying what nothing means is
#: the panel an operator reads as "fine".
ABSENCE_MEANS = (
    "the rebuilt AutoKernel loop has never published a status in this store "
    "root. It is not 'quiet' and it is not 'between iterations' — no process "
    "has written the contract at all. The loop publishes at start, after every "
    "iteration and on exit (including on failure), so a running loop is never "
    "absent here.")

#: Dispositions that mean a candidate actually reached the instrument. Mirrors
#: the producer's ``measurements_reached`` fold; kept here only to split the
#: rest out as NEGATIVES for the page.
MEASURED_DISPOSITIONS = ("kept", "measured_null")

#: The producer's OWN names first, then the shorter spellings this reader also
#: accepts. Getting this list wrong is not a cosmetic fault: it was wrong from
#: the surface's first commit — the reader looked only for ``held_s``/``busy_s``
#: while ``autokernel/loop/run.py`` has always written ``claim_held_s`` and
#: ``device_seconds_under_load`` — so the one panel this surface was built for
#: rendered "the loop published no held/busy seconds" over a producer that was
#: publishing them every iteration. The synthetic fixture invented the short
#: names and agreed with the code, so 41 tests passed over a dark panel.
HELD_KEYS = ("claim_held_s", "held_s", "held_seconds", "held")
BUSY_KEYS = ("device_seconds_under_load", "busy_s", "busy_seconds", "busy")

# --------------------------------------------------------------------------- #
# THE RUN'S LIFECYCLE IS NOT ITS FRESHNESS
# --------------------------------------------------------------------------- #
#: What the producer writes in ``state``. ``run.py`` publishes exactly these four:
#: ``starting`` once, ``running`` at every beat, and then ``complete`` or
#: ``failed`` on the way out — including after a STOP sentinel, which is drained
#: at the next iteration boundary and exits through the normal ``complete`` path.
RUN_STARTING = "starting"
RUN_RUNNING = "running"
RUN_COMPLETE = "complete"
RUN_FAILED = "failed"
RUN_STATES = (RUN_STARTING, RUN_RUNNING, RUN_COMPLETE, RUN_FAILED)

#: The banner the page must draw, which is NOT the freshness state.
#:
#: A run that was stopped on purpose goes quiet by design: it publishes
#: ``complete`` and exits, and thirty minutes later its last report is outside
#: the envelope. Keyed on freshness alone that renders "STALE — the loop has
#: stopped reporting", which accuses a producer that did exactly what it was
#: told. The reverse hole is worse: a loop that DECLARED ``failed`` one minute
#: ago is perfectly fresh, so freshness alone draws no banner at all over a dead
#: run — ``loop_data_health`` already refuses to make that mistake (it raises
#: ``failed`` to degraded explicitly) and the page must not make it either.
#:
#: So lifecycle and freshness are folded into ONE banner key here, server-side,
#: where a test can execute it. The freshness badge keeps the four-valued
#: vocabulary untouched; this is a second, orthogonal axis, never a fifth
#: freshness state.
NOTICE_ABSENT = "absent"
NOTICE_MALFORMED = "malformed"
NOTICE_STALE = "stale"
NOTICE_FINISHED = "finished"
NOTICE_FAILED = "failed"
NOTICE_NONE = "none"
NOTICES = (NOTICE_ABSENT, NOTICE_MALFORMED, NOTICE_STALE, NOTICE_FINISHED,
           NOTICE_FAILED, NOTICE_NONE)


def store_root() -> Path:
    """The loop's store root, resolved at call time."""
    return Path(os.environ.get(STORE_ROOT_ENV) or DEFAULT_STORE_ROOT)


def status_path(root: Optional[Path] = None) -> Path:
    return (store_root() if root is None else Path(root)) / STATUS_FILENAME


def read(root: Optional[Path] = None) -> dict:
    """``{artifact_present, body, reader_error}`` for the status file.

    Three outcomes, never two: no file (``artifact_present=False``), a file the
    hub could not turn into this contract (``reader_error`` set, ``body`` None),
    and a readable body. Absence and corruption are different facts about
    different subsystems and must not share a rendering.
    """
    path = status_path(root)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"artifact_present": False, "body": None, "reader_error": None,
                "path": str(path)}
    except OSError as exc:
        return {"artifact_present": path.exists(), "body": None,
                "reader_error": f"loop status unreadable: {exc}", "path": str(path)}
    if not raw.strip():
        # An EMPTY file is not an absent one: something opened it. Most likely a
        # writer that died between create and rename, which is a producer bug.
        return {"artifact_present": True, "body": None,
                "reader_error": "loop status is empty (0 bytes of content) — a "
                                "writer created the file and never finished it",
                "path": str(path)}
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"artifact_present": True, "body": None,
                "reader_error": f"loop status is not valid JSON: {exc}",
                "path": str(path)}
    if not isinstance(body, dict):
        return {"artifact_present": True, "body": None,
                "reader_error": "loop status is not a JSON object", "path": str(path)}
    schema = body.get("schema")
    if schema != STATUS_SCHEMA:
        return {"artifact_present": True, "body": None,
                "reader_error": (f"loop status declares schema {schema!r}, not "
                                 f"{STATUS_SCHEMA!r} — the field names on this "
                                 "page would not mean what they say"),
                "path": str(path)}
    return {"artifact_present": True, "body": body, "reader_error": None,
            "path": str(path)}


def _stamp_epoch(value: Any) -> Optional[float]:
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _budget(body: Mapping[str, Any]) -> float:
    """The producer's declared staleness budget, clamped to something usable.

    Clamped for the same reason ``panels.MAX_STALE_S`` exists: a budget wider
    than any real cadence satisfies "declares a threshold" and monitors nothing,
    and a budget of zero makes every reading stale between two publishes. The
    producer still owns the number inside those bounds — a loop that declares a
    longer cadence must not read as stale.
    """
    raw = body.get("stale_after_s")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_STALE_AFTER_S
    if value != value or value in (float("inf"), float("-inf")):  # NaN/inf
        return DEFAULT_STALE_AFTER_S
    return max(MIN_STALE_AFTER_S, min(value, float(panels.MAX_STALE_S)))


def freshness(report: Mapping[str, Any], *, now: Optional[float] = None) -> dict:
    """Fold one :func:`read` result into the four-valued freshness verdict."""
    now = time.time() if now is None else float(now)
    body = report.get("body")
    if body is None:
        if not report.get("artifact_present"):
            return {"state": STATE_ABSENT, "age_s": None, "stale_after_s": None,
                    "generated_at": None, "detail": ABSENCE_MEANS}
        return {"state": STATE_MALFORMED, "age_s": None, "stale_after_s": None,
                "generated_at": None,
                "detail": (report.get("reader_error")
                           or "the loop status file exists but could not be read "
                              "as this contract")}
    stamped = body.get("generated_at")
    written = _stamp_epoch(stamped)
    if written is None:
        return {"state": STATE_MALFORMED, "age_s": None,
                "stale_after_s": _budget(body), "generated_at": stamped,
                "detail": (f"unparseable generated_at {stamped!r} — a report "
                           "nobody can date cannot be trusted to be current")}
    age = now - written
    budget = _budget(body)
    if age < 0:
        # A report dated in the FUTURE cannot age, so it would read fresh forever
        # however long the producer has been dead. Same rule as
        # ``panels.FUTURE_SKEW_TOLERANCE_S``, applied to this contract's own
        # verdict so the page and the fold agree.
        if -age > panels.FUTURE_SKEW_TOLERANCE_S:
            return {"state": STATE_MALFORMED, "age_s": None,
                    "stale_after_s": budget, "generated_at": stamped,
                    "detail": (f"the loop dated this report {-age:.0f}s IN THE "
                               "FUTURE; a future timestamp cannot age, so it is "
                               "treated as undated rather than as fresh")}
        age = 0.0
    fresh = age <= budget
    return {
        "state": STATE_FRESH if fresh else STATE_STALE,
        "age_s": round(age, 1),
        "stale_after_s": budget,
        "generated_at": stamped,
        "detail": ("current" if fresh else
                   f"last heard from the loop {age / 60:.1f} min ago, past its "
                   f"own {budget / 60:.0f} min envelope — the reading below is "
                   "the loop's LAST report, not its current state"),
    }


def notice(report: Mapping[str, Any], fresh: Mapping[str, Any]) -> dict:
    """Fold freshness AND the run's declared lifecycle into ONE banner verdict.

    Six outcomes, and the two that freshness alone cannot reach are the point:

      * ``finished`` — the run DECLARED ``complete``. Its silence afterwards is
        compliance, not an outage. A STOP sentinel lands here: the loop drains
        the current iteration and exits through the same path, so "the operator
        stopped it" and "it ran out of planned iterations" are the same
        producer-visible fact and neither is a fault.
      * ``failed``   — the run DECLARED ``failed``. It published on the way out,
        so this reading can be perfectly FRESH and the run perfectly dead.
        Freshness alone draws no banner here at all.

    Lifecycle wins over staleness because a declared end explains the silence;
    an undeclared silence does not explain itself. ``absent`` and ``malformed``
    win over both, because with no trustworthy body there is no declared state
    to believe.
    """
    state = fresh.get("state")
    if state == STATE_ABSENT:
        return {"kind": NOTICE_ABSENT, "run_state": None,
                "detail": fresh.get("detail")}
    if state == STATE_MALFORMED:
        return {"kind": NOTICE_MALFORMED, "run_state": None,
                "detail": fresh.get("detail")}
    body = report.get("body") or {}
    run_state = body.get("state")
    run_state = str(run_state) if run_state is not None else None
    if run_state == RUN_FAILED:
        return {"kind": NOTICE_FAILED, "run_state": run_state,
                "detail": ("the loop DECLARED state=failed and published on its "
                           "way out. This reading may be perfectly fresh; the "
                           "run is over and it ended badly.")}
    if run_state == RUN_COMPLETE:
        return {"kind": NOTICE_FINISHED, "run_state": run_state,
                "detail": ("the loop DECLARED state=complete: it finished the "
                           "iteration it was on and exited. Everything below is "
                           "its FINAL report — a finished run, not a lost "
                           "producer. A STOP sentinel ends a run this way too, "
                           "so this is also what an operator-stopped run looks "
                           "like.")}
    if state == STATE_STALE:
        return {"kind": NOTICE_STALE, "run_state": run_state,
                "detail": fresh.get("detail")}
    return {"kind": NOTICE_NONE, "run_state": run_state, "detail": None}


def _gpu(body: Mapping[str, Any]) -> dict:
    """Held seconds against busy seconds — or an honest "not reported".

    The loop held a device 95.4% idle for a month and nothing reported it,
    because the old surface reported iterations and receipts. But an EMPTY gpu
    map must not be folded into "0s busy, 100% idle": that would be a fabricated
    measurement, which is worse than the silence it replaces. Absent inputs
    yield ``reported: false`` and no numbers.
    """
    raw = body.get("gpu")
    raw = dict(raw) if isinstance(raw, Mapping) else {}

    def _num(*names):
        for name in names:
            value = raw.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value != value:  # NaN
                continue
            return float(value)
        return None

    held = _num(*HELD_KEYS)
    busy = _num(*BUSY_KEYS)
    out = {"reported": held is not None and busy is not None,
           "held_s": held, "busy_s": busy, "idle_s": None, "busy_pct": None,
           "raw": raw, "unreported_reason": None}
    if not out["reported"]:
        # WHY nothing is reported is a different fact depending on who is at
        # fault, and a page that says "the loop published no held/busy seconds"
        # over a loop that published four of them is making a false claim about
        # the producer. Three cases, named apart:
        if not raw:
            out["unreported_reason"] = (
                "the loop published no gpu map at all")
        elif not any(key in raw for key in HELD_KEYS + BUSY_KEYS):
            out["unreported_reason"] = (
                "the loop published a gpu map, but this reader recognises none "
                f"of its keys ({', '.join(sorted(raw))}) as held or busy "
                "seconds — that is a READER defect, not a silent producer")
        else:
            missing = [name for name, value in (("held", held), ("busy", busy))
                       if value is None]
            out["unreported_reason"] = (
                f"the loop published a gpu map with no usable "
                f"{' and '.join(missing)} seconds (present keys: "
                f"{', '.join(sorted(raw))})")
    if out["reported"] and held > 0:
        out["idle_s"] = round(max(0.0, held - busy), 1)
        out["busy_pct"] = round(100.0 * min(busy, held) / held, 1)
    elif out["reported"]:
        # Held for zero seconds: nothing to be a percentage OF.
        out["idle_s"] = 0.0
    return out


def summarize(body: Mapping[str, Any]) -> dict:
    """Derived view fields — folds, never new claims."""
    dispositions = body.get("dispositions")
    dispositions = dict(dispositions) if isinstance(dispositions, Mapping) else {}
    counts = {key: int(value) for key, value in dispositions.items()
              if isinstance(value, (int, float)) and not isinstance(value, bool)}
    kept = counts.get("kept", 0)
    total = sum(counts.values())
    measured = sum(counts.get(key, 0) for key in MEASURED_DISPOSITIONS)
    planned = body.get("iterations_planned")
    done = body.get("iterations_done")
    remaining = None
    if isinstance(planned, int) and isinstance(done, int):
        remaining = max(0, planned - done)
    return {
        "kept": kept,
        # Everything that is NOT a keep. On the page beside the keeps, always:
        # a board that shows only wins is how 0 promotions looked like progress
        # for a month.
        "negatives": max(0, total - kept),
        "measured": measured,
        "never_measured": max(0, total - measured),
        "iterations_remaining": remaining,
        "gpu": _gpu(body),
    }


def observation(report: Mapping[str, Any], fresh: Mapping[str, Any]
                ) -> panels.Observation:
    """The panel-registry observation for this reading.

    ``silence_budget_s`` hands the PRODUCER'S declared cadence to the envelope,
    so the hub does not hold a second, drifting opinion about when this loop is
    late. The watermark is the loop's progress identity: a producer that keeps
    rewriting its status with fresh timestamps and an unmoving iteration count
    is alive enough to publish and dead enough to make no progress.
    """
    body = report.get("body")
    if body is None:
        if not report.get("artifact_present"):
            return panels.absent(panels.source("autokernel_loop"), ABSENCE_MEANS)
        return panels.Observation(
            artifact_present=True, timestamp=None, source=None,
            detail=fresh.get("detail"), evidence=report.get("path"))
    timestamp = _stamp_epoch(body.get("generated_at"))
    state = str(body.get("state") or "unknown")
    if timestamp is None:
        return panels.Observation(
            artifact_present=True, timestamp=None, source=state,
            detail=fresh.get("detail"), evidence=report.get("path"))
    return panels.Observation(
        artifact_present=True,
        timestamp=timestamp,
        source=state,
        populated=bool(body.get("iterations_done")),
        detail=fresh.get("detail"),
        evidence=report.get("path"),
        watermark=(f"{state}|{body.get('iterations_done')}|"
                   f"{body.get('measurements_reached')}|{body.get('champion_head')}"),
        # A loop that has DECLARED it finished is allowed to be silent. A loop
        # that declared it FAILED is not treated as idle here: its silence is
        # expected, but so is an operator being told about it, and the data
        # probe raises `failed` to degraded on its own (see server.loop_data_health).
        producer_idle=(state == "complete"),
        silence_budget_s=_budget(body),
    )


# --------------------------------------------------------------------------- #
# THE CHAMPION HEADLINE — one number, one named anchor, allowed to be absent
# --------------------------------------------------------------------------- #
# THE RULING (operator, 2026-08-30): "the champion headline number shown should
# JUST BE THE COLLECTIVE PERFORMANCE GAIN VS FROZEN PRODUCTION KERNEL", with the
# capabilities that tree enables listed beside it. One number. One anchor.
#
# WHY THIS NEEDED A RULING. The page carried a +48.9% in its largest type, from
# the operator-gated manual-research bundle, beside a loop whose own champion
# was worth roughly a tenth of that by its own A/B. Different producers,
# different anchors, different questions — displayed side by side with nothing
# saying so, and the operator reasonably asked why the champion said +48.9% when
# they had been told +9%. A percentage with no named anchor is not a small
# labelling fault; it is the whole defect.
#
# WHY THIS READS A FILE NOBODY WRITES YET, AND WHY THAT IS THE CORRECT SHAPE.
# There is no measured champion-vs-v9 number for the current champion. The last
# direct A/B was several commits ago; since then run 17 added 30 commits and run
# 18 one more. Those are MARGINALS against an anchor that advances on every keep
# — different baselines, one per keep — and composing them arithmetically would
# manufacture a measurement no run ever took. This program already made that
# error once. So the slot renders NOT MEASURED and names what would fill it.
# An empty slot that says why is worth more than a number nobody measured.

#: The anchor, and it is not negotiable: this headline is DEFINED as the gain
#: over the frozen production kernel. A bundle measured against anything else is
#: some other number and is refused rather than shown under this heading.
FROZEN_PRODUCTION_COMMIT = "0db32c06e3e550065b78311a6031ef3dd2c4f27c"
FROZEN_PRODUCTION_LABEL = "production-consolidated-v9"

CHAMPION_SCHEMA = "epyc.autokernel.champion_vs_production.v1"
CHAMPION_FILENAME = "champion-vs-production.json"
#: A cumulative A/B is a deliberate, expensive act, not a per-iteration beat, so
#: the envelope is days rather than minutes. The producer still owns the number
#: inside the same clamps every other contract on this page is held to.
CHAMPION_DEFAULT_STALE_AFTER_S = 14 * 86400.0

CHAMPION_ABSENCE_MEANS = (
    "no direct A/B of the champion tree against the frozen production kernel "
    "has ever been published here. This is NOT 'the champion has no gain' and "
    "NOT 'the gain is zero' — it is 'the measurement this headline names has "
    "not been taken for this commit'.")

CHAMPION_NOT_COMPOSABLE = (
    "The per-iteration effects on this page are MARGINALS against an anchor "
    "that advances on every keep, so each one has a different baseline. They "
    "must never be summed, multiplied or otherwise composed into a cumulative "
    "figure: a composed number would claim a measurement no run ever took. "
    "This headline can only ever come from one direct A/B.")


def _champion_would_populate(path: Path) -> str:
    return (f"one direct A/B — the champion commit built and benched against "
            f"the frozen production kernel {FROZEN_PRODUCTION_COMMIT[:12]} "
            f"({FROZEN_PRODUCTION_LABEL}) on the loop's own surface and pair "
            f"count, both arms measured in the same session — published as "
            f"{CHAMPION_SCHEMA} at {path}.")


#: Why the capability list cannot be sourced today, stated as what was CHECKED
#: rather than as a shrug — three candidate sources, each rejected for a reason
#: that survives being looked up:
#:
#:   * the loop's build recipe (``autokernel.controller.build_recipe``) declares
#:     four flags, all matching production by construction ("Matches production
#:     on every flag"), so a list derived from it would render EMPTY — and empty
#:     reads as "this tree enables nothing", which is a claim, and a false one;
#:   * a flag DIFF against production cannot be computed either: that module
#:     sets ``PRODUCTION_RECIPE_IS_VERIFIABLE = False`` and the frozen tree's
#:     build directory carries no ``CMakeCache.txt``, so production's own recipe
#:     is not recoverable from disk;
#:   * the anchor build's ``CMakeCache.txt`` names how ONE build was compiled and
#:     carries no commit attribution, so nothing ties it to a champion.
#:
#: Nothing anywhere under the campaign's store or surface records a feature list
#: for the champion tree — there is no FlashAttention2 record of any kind — so a
#: list typed here would be a memory wearing a measurement's clothes.
CHAMPION_CAPABILITIES_UNKNOWN = (
    "no producer attributes a capability list to a champion commit. The "
    "champion-vs-production contract carries an optional `capabilities` array "
    "and none has been published. Build flags are not a substitute: the loop's "
    "recipe declares zero divergences from production by construction, so a "
    "list derived from it would be empty — and empty would read as 'this tree "
    "enables nothing' rather than 'nobody has said' — and a flag DIFF is not "
    "computable either, because production's own recipe is not recoverable from "
    "disk (the recipe module declares it unverifiable and the frozen build "
    "directory has no CMakeCache).")

CHAMPION_CAPABILITIES_WOULD_POPULATE = (
    "a `capabilities` array in the champion-vs-production bundle: one entry per "
    "capability, each naming the evidence that establishes it (the commit, the "
    "gate, or the artifact). Typed here by hand it would be a memory, not a "
    "measurement.")


def champion_path(root: Optional[Path] = None) -> Path:
    return (store_root() if root is None else Path(root)) / CHAMPION_FILENAME


def read_champion(root: Optional[Path] = None) -> dict:
    """``{artifact_present, body, reader_error}`` for the champion A/B bundle.

    The same three-outcome shape as :func:`read`, for the same reason: a file
    nobody ever wrote and a file somebody wrote badly point at different
    subsystems and must not share a rendering.
    """
    path = champion_path(root)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"artifact_present": False, "body": None, "reader_error": None,
                "path": str(path)}
    except OSError as exc:
        return {"artifact_present": path.exists(), "body": None,
                "reader_error": f"champion bundle unreadable: {exc}",
                "path": str(path)}
    if not raw.strip():
        return {"artifact_present": True, "body": None,
                "reader_error": ("the champion bundle is empty (0 bytes of "
                                 "content) — a writer created it and never "
                                 "finished it"),
                "path": str(path)}
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"artifact_present": True, "body": None,
                "reader_error": f"the champion bundle is not valid JSON: {exc}",
                "path": str(path)}
    if not isinstance(body, dict):
        return {"artifact_present": True, "body": None,
                "reader_error": "the champion bundle is not a JSON object",
                "path": str(path)}
    schema = body.get("schema")
    if schema != CHAMPION_SCHEMA:
        return {"artifact_present": True, "body": None,
                "reader_error": (f"the champion bundle declares schema "
                                 f"{schema!r}, not {CHAMPION_SCHEMA!r} — its "
                                 "field names would not mean what this headline "
                                 "says they mean"),
                "path": str(path)}
    baseline = body.get("baseline")
    baseline = baseline if isinstance(baseline, Mapping) else {}
    measured_against = baseline.get("commit")
    if measured_against != FROZEN_PRODUCTION_COMMIT:
        # REFUSED, not relabelled. This headline is DEFINED as the gain over the
        # frozen production kernel; a bundle measured against the loop's
        # advancing anchor, or against an older production, is a different
        # number, and showing it here under this heading is exactly the
        # anchor-swap that produced the confusion this panel exists to end.
        return {"artifact_present": True, "body": None,
                "reader_error": (
                    f"the champion bundle names baseline "
                    f"{str(measured_against)[:12] or '(none)'}, not the frozen "
                    f"production kernel {FROZEN_PRODUCTION_COMMIT[:12]}. This "
                    f"headline is defined as the gain over frozen production, "
                    f"so a measurement against any other anchor is a different "
                    f"number and is refused rather than shown here"),
                "path": str(path)}
    return {"artifact_present": True, "body": body, "reader_error": None,
            "path": str(path)}


def _champion_budget(body: Mapping[str, Any]) -> float:
    raw = body.get("stale_after_s")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return CHAMPION_DEFAULT_STALE_AFTER_S
    if isinstance(raw, bool) or value != value or value in (
            float("inf"), float("-inf")) or value <= 0:
        return CHAMPION_DEFAULT_STALE_AFTER_S
    return max(MIN_STALE_AFTER_S, min(value, float(panels.MAX_STALE_S)))


def champion_freshness(report: Mapping[str, Any], *,
                       now: Optional[float] = None) -> dict:
    """The same four-valued verdict as the loop's, over the champion bundle.

    Same vocabulary on purpose — ``fresh``/``stale``/``absent``/``malformed``,
    the words the loop badge and the operator-gate badge already use. Three
    producers on one page saying "stale" three different ways is a page nobody
    can read at a glance.
    """
    now = time.time() if now is None else float(now)
    body = report.get("body")
    if body is None:
        if not report.get("artifact_present"):
            return {"state": STATE_ABSENT, "age_s": None, "stale_after_s": None,
                    "generated_at": None, "detail": CHAMPION_ABSENCE_MEANS}
        return {"state": STATE_MALFORMED, "age_s": None, "stale_after_s": None,
                "generated_at": None,
                "detail": (report.get("reader_error")
                           or "a champion bundle exists but could not be read "
                              "as this contract")}
    stamped = body.get("generated_at")
    written = _stamp_epoch(stamped)
    budget = _champion_budget(body)
    if written is None:
        return {"state": STATE_MALFORMED, "age_s": None, "stale_after_s": budget,
                "generated_at": stamped,
                "detail": (f"unparseable generated_at {stamped!r} — a "
                           "measurement nobody can date cannot be shown as the "
                           "current standing")}
    age = now - written
    if age < 0:
        if -age > panels.FUTURE_SKEW_TOLERANCE_S:
            return {"state": STATE_MALFORMED, "age_s": None,
                    "stale_after_s": budget, "generated_at": stamped,
                    "detail": (f"this measurement is dated {-age:.0f}s IN THE "
                               "FUTURE; a future timestamp cannot age, so it is "
                               "treated as undated rather than as fresh")}
        age = 0.0
    fresh = age <= budget
    return {
        "state": STATE_FRESH if fresh else STATE_STALE,
        "age_s": round(age, 1),
        "stale_after_s": budget,
        "generated_at": stamped,
        "detail": ("current" if fresh else
                   f"this A/B was measured {age / 86400:.1f} d ago, past its "
                   f"own {budget / 86400:.1f} d envelope — it is the LAST "
                   "champion-vs-production measurement, not a current one"),
    }


def _champion_capabilities(body: Optional[Mapping[str, Any]]) -> dict:
    """The capability list, or an honest "nobody has said" with the reason.

    Entries are the producer's, verbatim: ``{"name", "evidence"}``. Nothing is
    inferred and nothing is defaulted — a capability the page invents is worse
    than a capability nobody listed, because it cannot be traced back to a
    commit when someone asks how we know.
    """
    out = {"known": False, "source": None, "items": [],
           "unknown_reason": CHAMPION_CAPABILITIES_UNKNOWN,
           "would_populate": CHAMPION_CAPABILITIES_WOULD_POPULATE}
    raw = body.get("capabilities") if body is not None else None
    if not isinstance(raw, (list, tuple)):
        if body is not None and raw is not None:
            out["unknown_reason"] = (
                "the champion bundle carries a `capabilities` field that is not "
                "a list, so this reader cannot enumerate it; the emitter's "
                "writer is at fault, not the absence of evidence.")
        return out
    items = []
    for entry in raw:
        if isinstance(entry, Mapping):
            name = entry.get("name")
            evidence = entry.get("evidence")
        else:
            name, evidence = entry, None
        if name is None or not str(name).strip():
            continue
        items.append({"name": str(name),
                      "evidence": None if evidence is None else str(evidence)})
    out["items"] = items
    out["source"] = f"{CHAMPION_SCHEMA} `capabilities`"
    if not items:
        # DECLARED EMPTY is not UNKNOWN. The producer published the array and
        # put nothing in it; that is a statement, and it is a different one from
        # never having been asked.
        out["known"] = True
        out["unknown_reason"] = None
        out["would_populate"] = None
        return out
    out["known"] = True
    out["unknown_reason"] = None
    out["would_populate"] = None
    return out


def champion_snapshot(root: Optional[Path] = None, *,
                      now: Optional[float] = None,
                      champion_head: Optional[str] = None) -> dict:
    """The wire block for the champion headline.

    ``champion_head`` is the loop's CURRENT champion, passed in rather than
    re-read, so the page can say whether the measurement it is showing is even
    about the tree the loop is running. A cumulative A/B is expensive and the
    champion advances on every keep, so "measured, but three keeps ago" is the
    normal case and must be visible — a number that silently re-anchors to
    whatever the champion is today is the same defect one level down.
    """
    report = read_champion(root)
    fresh = champion_freshness(report, now=now)
    body = report.get("body")
    path = champion_path(root)

    effect = None
    if body is not None:
        raw = body.get("effect_fraction")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) \
                and raw == raw and raw not in (float("inf"), float("-inf")):
            effect = float(raw)

    measured_commit = None
    if body is not None:
        champ = body.get("champion")
        champ = champ if isinstance(champ, Mapping) else {}
        measured_commit = champ.get("commit")
        measured_commit = str(measured_commit) if measured_commit else None

    supersession = None
    if measured_commit and champion_head and measured_commit != champion_head:
        supersession = {
            "measured_for": measured_commit,
            "current_champion": champion_head,
            "detail": (
                f"this A/B measured champion {measured_commit[:12]}; the loop's "
                f"champion is now {str(champion_head)[:12]}. The number stands "
                f"for the tree it measured and for no other. The commits added "
                f"since were screened as marginals against an advancing anchor "
                f"and cannot be added to it."),
        }

    return {
        "schema": CHAMPION_SCHEMA,
        "evidence": str(path),
        "artifact_present": bool(report.get("artifact_present")),
        "reader_error": report.get("reader_error"),
        # `measured` is the whole question this panel answers, and it is False
        # for absent AND for malformed: a bundle the hub refused is not a
        # measurement it may show.
        "measured": body is not None and effect is not None,
        "freshness": fresh,
        # The anchor is stated on EVERY reading, present or not. The headline is
        # a claim about a comparison; naming only one side of it is how a
        # percentage becomes unreadable.
        "baseline": {"commit": FROZEN_PRODUCTION_COMMIT,
                     "label": FROZEN_PRODUCTION_LABEL,
                     "kind": "frozen production kernel"},
        "champion": {"measured_commit": measured_commit,
                     "loop_champion_head": champion_head},
        "supersession": supersession,
        "effect_fraction": effect,
        "metric": (body or {}).get("metric"),
        "metric_direction": (body or {}).get("metric_direction"),
        "surface": (body or {}).get("surface"),
        "pairs": (body or {}).get("pairs"),
        "noise_floor_pct": (body or {}).get("noise_floor_pct"),
        "measurement_evidence": (body or {}).get("evidence"),
        "capabilities": _champion_capabilities(body),
        "absence_means": CHAMPION_ABSENCE_MEANS,
        "would_populate": _champion_would_populate(path),
        "not_composable": CHAMPION_NOT_COMPOSABLE,
    }


def payload(root: Optional[Path] = None, *, now: Optional[float] = None) -> dict:
    """The wire payload for ``/api/loop``, minus the panel envelope.

    ``loop`` is ``None`` — never ``{}`` — when nothing readable was found.
    """
    return snapshot(root, now=now)[0]


def snapshot(root: Optional[Path] = None, *, now: Optional[float] = None
             ) -> tuple:
    """``(payload, observation)`` from ONE read of the file.

    One read, so the body the page renders and the body the health probe judges
    cannot be two different files written a second apart.
    """
    report = read(root)
    fresh = freshness(report, now=now)
    body = report.get("body")
    wire = {
        "schema": STATUS_SCHEMA,
        "evidence": report.get("path"),
        "store_root": str(store_root() if root is None else Path(root)),
        "artifact_present": bool(report.get("artifact_present")),
        "reader_error": report.get("reader_error"),
        "freshness_state": fresh["state"],
        "age_s": fresh["age_s"],
        "stale_after_s": fresh["stale_after_s"],
        "generated_at": fresh["generated_at"],
        "detail": fresh["detail"],
        "absence_means": ABSENCE_MEANS,
        # Freshness answers "is this report current"; `notice` answers "what
        # should the operator be told", and a finished run is the case where
        # those two disagree. Folded here, not in the page, so a test can
        # EXECUTE it instead of grepping the markup for a branch.
        "notice": notice(report, fresh),
        "loop": dict(body) if body is not None else None,
        "derived": summarize(body) if body is not None else None,
        # A THIRD producer, and it dates neither of the other two. It is read
        # here rather than in `server.loop_payload` only so that the loop's own
        # champion head — which lives in the body read one line above — can be
        # handed to it without a second read of the status file.
        "champion_vs_production": champion_snapshot(
            root, now=now,
            champion_head=(body or {}).get("champion_head")),
    }
    return wire, observation(report, fresh)


__all__ = ["ABSENCE_MEANS", "BUSY_KEYS", "CHAMPION_ABSENCE_MEANS",
           "CHAMPION_CAPABILITIES_UNKNOWN",
           "CHAMPION_CAPABILITIES_WOULD_POPULATE",
           "CHAMPION_DEFAULT_STALE_AFTER_S", "CHAMPION_FILENAME",
           "CHAMPION_NOT_COMPOSABLE", "CHAMPION_SCHEMA",
           "DEFAULT_STALE_AFTER_S",
           "DEFAULT_STORE_ROOT", "FROZEN_PRODUCTION_COMMIT",
           "FROZEN_PRODUCTION_LABEL", "HELD_KEYS",
           "MEASURED_DISPOSITIONS", "MIN_STALE_AFTER_S",
           "NOTICES", "NOTICE_ABSENT", "NOTICE_FAILED", "NOTICE_FINISHED",
           "NOTICE_MALFORMED", "NOTICE_NONE", "NOTICE_STALE",
           "RUN_COMPLETE", "RUN_FAILED", "RUN_RUNNING", "RUN_STARTING",
           "RUN_STATES", "STATES",
           "STATE_ABSENT", "STATE_FRESH", "STATE_MALFORMED", "STATE_STALE",
           "STATUS_FILENAME", "STATUS_SCHEMA", "STORE_ROOT_ENV",
           "champion_freshness", "champion_path", "champion_snapshot",
           "freshness", "notice",
           "observation", "payload", "read", "read_champion", "snapshot",
           "status_path", "store_root", "summarize"]
