#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""row_intake.py — the two receipts a queue row must carry at BIRTH.

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Consumers:      backlog_queue_gen.py (--generate), seed_queue.py, session_bus_coordinator.intake

WHY THIS EXISTS. `a06780f4` made the coordinator-daemon's AUTOMATIC dispatch refuse
any queue row that does not carry BOTH

    screened_by          — a receipt that backlog_row_check.py ran on the row, and
    expected_occupancy   — how long the work should hold the hardware (F-14),

and `9bed637f` added both fields to the queue-row schema and the task-assign payload.
Nothing populated them. Measured on the live bus 2026-08-12, before this module:

    21 folded rows · 0 with `screened_by` · 0 with a resolvable occupancy

so the gate — correctly, fail-closed — would have refused EVERY row and the daemon
would have dispatched nothing at all, for ever. A gate with no producer behind it is
not a safety property; it is an off switch nobody labelled.

The fix is not to loosen the gate. It is to populate the fields WHERE ROWS ARE BORN,
which is the three call sites named above. This module is the one place the two
derivations live, so every birth site produces the same receipt under the same rule
and an auditor reads ONE file to know what a receipt means.

    THE HONEST DEFAULT, stated because it is the whole design. A row this module
    cannot estimate is emitted WITH NO `expected_occupancy` KEY AT ALL — not zero,
    not a default, not a guess. The daemon's gate then refuses it and a HUMAN
    dispatches it by hand. That is the intended outcome, not a failure of this
    module: `expected_occupancy` exists because seconds-long work was queued at a
    card that needed hours (F-14), and a fabricated number would re-create that
    exact defect while looking like it had been fixed. An unestimated row is a row
    a human must dispatch.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCREENER = Path(__file__).resolve().parent / "backlog_row_check.py"

#: Verdicts `backlog_row_check.emit_verdict` can print. The grammar is
#: `verdict=<V> ref=<file.md:LINE|> exit=<int>` on STDOUT, one line, unconditional.
VERDICT_LINE = re.compile(r"^verdict=(?P<verdict>\S+)\s+ref=(?P<ref>\S*)\s+exit=(?P<exit>-?\d+)\s*$")

#: The only verdict that admits a row as READY.
READY_VERDICT = "DISPATCHABLE"

#: Verdicts meaning "the row's identity could not be resolved" — it needs a human to
#: re-anchor it, not a dispatch. NOT_DISPATCHABLE is separate: the row resolved fine
#: and is simply not dispatchable work (guarded, blocked, a standing constraint).
REANCHOR_VERDICTS = frozenset({"ANCHOR_ROT", "UNRESOLVABLE", "AMBIGUOUS", "REFUSING", "NO_VERDICT"})

#: The queue's own status for "this cannot be dispatched until a human acts". Chosen
#: from the EXISTING `session_bus.queue.v1` status enum rather than invented: READY is
#: a lie, STALE_REQUEUED means "put it back in the pool" (which would re-offer an
#: unresolvable row for ever), and INFRA_BLOCKED is already the daemon's word for a row
#: that is not re-assignable without a human. See session_bus.schema.json#queue_row.
NEEDS_REANCHOR_STATUS = "INFRA_BLOCKED"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


@dataclass(frozen=True)
class ScreenResult:
    """One screener run, and the receipt string that records it."""

    verdict: str
    ref: str
    exit_code: int
    receipt: str
    argv: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """May this row be emitted READY? Only a positive DISPATCHABLE verdict."""
        return self.verdict == READY_VERDICT

    @property
    def needs_reanchor(self) -> bool:
        """Did the screen fail to RESOLVE the row (as opposed to rejecting it)?"""
        return self.verdict in REANCHOR_VERDICTS


def screen(*, ref: Optional[str] = None, row: Optional[str] = None) -> ScreenResult:
    """Run backlog_row_check.py on one row and return its verdict + a receipt.

    Exactly one of `ref` (`file.md:LINE`) or `row` (the task TEXT) — the screener's
    own mutually-exclusive group. Prefer `row` at any site whose output carries the
    text as the dispatch identity; `ref` is the cheap form for a caller that has just
    read the box out of the file and therefore knows the anchor is live.

    STDERR IS NOT CAPTURED, NOT REDIRECTED AND NOT SUPPRESSED — it is inherited, so
    the screener's human-readable detail lands on this process's stderr where a
    reader and a CI log both see it. That is deliberate and it is the exact defect
    fixed on 2026-08-12: the idiom `out=$(backlog_row_check.py --ref "$x" 2>/dev/null)`
    turns a rotted anchor into an empty string and a discarded exit code, i.e. into
    something indistinguishable from a clean pass, while anchor rot runs at 34.5%
    queue-wide. `emit_verdict` added the STDOUT line so a wrapper cannot lose the
    verdict; this function must not then throw away the prose that explains it.
    """
    if (ref is None) == (row is None):
        raise ValueError("screen() takes exactly one of ref= or row=")
    flag, value = ("--ref", ref) if ref is not None else ("--row", row)
    argv = (sys.executable, str(SCREENER), flag, str(value))
    # stdout is captured because the verdict line is a RETURN VALUE. stderr is left
    # alone on purpose — see the docstring. Never add stderr= here.
    proc = subprocess.run(argv, stdout=subprocess.PIPE, text=True, check=False)

    verdict, vref = "NO_VERDICT", ""
    for line in (proc.stdout or "").splitlines():
        m = VERDICT_LINE.match(line.strip())
        if m:
            verdict, vref = m.group("verdict"), m.group("ref")
    # A missing verdict line is a FAILURE, never a pass: `emit_verdict` prints one
    # unconditionally at every terminal path, so its absence means the screener did
    # not run or crashed, and "no verdict at all" must never read as "fine".
    receipt = (f"backlog_row_check.py {flag} {value!r} @{_utcnow()} "
               f"verdict={verdict} exit={proc.returncode}")
    return ScreenResult(verdict=verdict, ref=vref, exit_code=proc.returncode,
                        receipt=receipt, argv=argv)


# ---------------------------------------------------------------------------
# expected_occupancy — the derivation, in the order a human should read it.
# ---------------------------------------------------------------------------

_NUM = r"\d+(?:\.\d+)?"
_UNIT = r"(?:h(?:ours?|rs?)?|m(?:in(?:ute)?s?)?|d(?:ays?)?)"

#: An occupancy CUE. A bare number-and-unit anywhere in a sentence is not a duration
#: claim — "re-check within 24h" is a deadline and "the 3h window closed" is history.
#: Requiring a cue keeps the rule readable and keeps the false-positive class out.
_CUE = (r"(?:~|≈|approx(?:\.|imately)?|about|est(?:\.|imated?|imate)?|takes?|"
        r"runs?(?:\s+for)?|budget(?:ed)?|wall[- ]?clock|duration|expect(?:ed|s)?|"
        r"occupanc(?:y|ies)|est_wall_clock_h|est_h)")

#: `est 2-3h`, `~90 min`, `takes about 4 hours`, `est_wall_clock_h: 1.5`
_CUED_RANGE = re.compile(rf"{_CUE}[\s:=of]{{0,6}}({_NUM})\s*(?:-|–|—|to)\s*({_NUM})\s*({_UNIT})\b", re.I)
_CUED_ONE = re.compile(rf"{_CUE}[\s:=of]{{0,6}}({_NUM})\s*({_UNIT})\b", re.I)
#: `est_wall_clock_h: 1.5` — a bare number is hours ONLY under an hours-named field.
_CUED_FIELD_H = re.compile(rf"(est_wall_clock_h|est_h)\s*[:=]\s*({_NUM})\b", re.I)
#: `2h sweep`, `40-minute run`, `three-hour soak` (numeric forms only).
_TRAILING = re.compile(
    rf"({_NUM})\s*[- ]?\s*({_UNIT})\b[\s-]*"
    # `window` is deliberately NOT in this list: "the 3h window closed before anyone
    # looked" is history and "re-check inside the 2h window" is a deadline, and neither
    # is a statement about how long THIS task runs.
    r"(?:run|runs|sweep|bench(?:mark)?|soak|eval|job|occupancy|of\s+work|wall[- ]?clock)", re.I)
#: A named duration with no number. `overnight` is the only one this corpus uses.
_OVERNIGHT = re.compile(r"\bovernight\b", re.I)
_OVERNIGHT_H = 8.0

_UNIT_H = {"h": 1.0, "m": 1.0 / 60.0, "d": 24.0}

#: RULE 3's floor. Half an hour for a `lane: none` row — see `estimate_occupancy`.
LANE_NONE_FLOOR_H = 0.5


def _unit_hours(unit: str) -> float:
    return _UNIT_H[unit[0].lower()]


def _stated_durations(text: str) -> list[tuple[float, str]]:
    """Every (hours, matched-phrase) this text explicitly STATES. May be empty."""
    out: list[tuple[float, str]] = []
    for m in _CUED_RANGE.finditer(text):
        # A range reserves its UPPER bound. Under-reserving is the F-14 failure;
        # over-reserving only costs a little scheduling slack.
        out.append((float(m.group(2)) * _unit_hours(m.group(3)), m.group(0).strip()))
    for m in _CUED_ONE.finditer(text):
        out.append((float(m.group(1)) * _unit_hours(m.group(2)), m.group(0).strip()))
    for m in _CUED_FIELD_H.finditer(text):
        out.append((float(m.group(2)), m.group(0).strip()))
    for m in _TRAILING.finditer(text):
        out.append((float(m.group(1)) * _unit_hours(m.group(2)), m.group(0).strip()))
    if _OVERNIGHT.search(text):
        out.append((_OVERNIGHT_H, f"overnight (={_OVERNIGHT_H:g}h by convention)"))
    return [(h, p) for h, p in out if h > 0]


def estimate_occupancy(text: str, *, lane: Optional[str] = None,
                       gating: Optional[str] = None,
                       declared_h: Optional[float] = None) -> Optional[dict]:
    """`{est_h, basis, gating?}` for this row, or **None** if it cannot be estimated.

    THE RULES, in precedence order. Each is a rule a human can read off this
    function and audit against the row; none of them is a guess dressed as data.

      1. DECLARED. The proposer stated `est_wall_clock_h` as a FIELD. Their number
         wins over anything inferred from prose — it is the only input here that is
         somebody's actual judgment about this specific task.

      2. STATED IN THE TEXT. The row's own words give a duration next to an
         occupancy cue (`~2h`, `est 90 min`, `takes about 4 hours`, `2h sweep`,
         `overnight`). The LARGEST such statement wins, and a range reserves its
         upper bound, because under-reserving is the failure F-14 records and
         over-reserving merely wastes slack. The matched phrase is quoted verbatim
         into `basis`, so a reader can check the derivation against the row without
         re-running anything.

      3. LANE CLASS `none`, AND ONLY `none`. A row whose lane and gating are both
         `none` is code/doc work that holds NO inference lane, so its occupancy
         number cannot mis-schedule any hardware — the harm `expected_occupancy`
         exists to prevent is structurally unreachable for it. Only there is a
         synthesised floor honest, and `basis` says in words that it is a floor and
         not a measurement.

      4. OTHERWISE: **None.** A `cpu` or `gpu` row that states no duration gets NO
         `expected_occupancy` key. That is precisely the case where a made-up number
         DOES mis-schedule hardware, so this function refuses to make one up. The
         row is emitted without the field, the daemon's `dispatch_gate` refuses it,
         and a human dispatches it by hand after deciding how long it should run.
         Returning 0.0 here would be worse than returning nothing: the gate reads
         `hours <= 0` as unusable anyway, but a zero in the row would LOOK like an
         answered question to every human and every report downstream.
    """
    gate = {"gating": gating} if gating else {}

    if declared_h is not None:
        try:
            value = float(declared_h)
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            return {"est_h": value,
                    "basis": "declared-field:est_wall_clock_h — the proposer's own estimate, "
                             "not measured",
                    **gate}

    stated = _stated_durations(text or "")
    if stated:
        hours, phrase = max(stated, key=lambda p: p[0])
        return {"est_h": round(hours, 4),
                "basis": f"stated-in-row-text:{phrase!r} — read off the row's own words, "
                         f"not measured",
                **gate}

    if lane == "none" and gating in (None, "none"):
        return {"est_h": LANE_NONE_FLOOR_H,
                "basis": f"lane-class:none — code/doc work holds no inference lane, so this "
                         f"number cannot mis-schedule hardware (F-14 is unreachable here); "
                         f"{LANE_NONE_FLOOR_H:g}h is a conservative floor, NOT a measurement",
                **gate}

    return None


def occupancy_note(occ: Optional[dict]) -> str:
    """One human line about the occupancy decision, for a generator's report."""
    if occ is None:
        return ("NO occupancy — HAND-DISPATCH ONLY. The row states no duration and no lane "
                "class permits a synthesised floor, so no number can be derived honestly. "
                "Decide it yourself when you dispatch this.")
    return f"occupancy {occ['est_h']:g}h — {occ['basis']}"
