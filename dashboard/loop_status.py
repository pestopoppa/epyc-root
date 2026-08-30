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
        "loop": dict(body) if body is not None else None,
        "derived": summarize(body) if body is not None else None,
    }
    return wire, observation(report, fresh)


__all__ = ["ABSENCE_MEANS", "BUSY_KEYS", "DEFAULT_STALE_AFTER_S",
           "DEFAULT_STORE_ROOT", "HELD_KEYS",
           "MEASURED_DISPOSITIONS", "MIN_STALE_AFTER_S", "STATES",
           "STATE_ABSENT", "STATE_FRESH", "STATE_MALFORMED", "STATE_STALE",
           "STATUS_FILENAME", "STATUS_SCHEMA", "STORE_ROOT_ENV", "freshness",
           "observation", "payload", "read", "snapshot", "status_path",
           "store_root", "summarize"]
