"""VB-MHS-OPS: project the RTG-55 mutation-safety guard into ``ClaimTuple`` rows.

Producers (orchestrator; the guard and its operability live on ``sub/gate-frontier-20260916``,
under review and unmerged; AP-53's ledger is on ``main`` at ``753343f5``):

* ``orchestration/autopilot_rejected_mutations.jsonl`` -- AP-53, harness-written, one record
  per rejected mutation (``rejected_mutation_ledger.build_record``). A guard rejection is a
  ``rejecting_gate == "transfer_safety"`` record whose ``gate_detail`` is the mutation's
  ``safety_reason``: ``eval_instance_leakage:*`` (MHS-3),
  ``eval_leakage_vocabulary_unavailable:*`` (MHS-3, fail-closed), ``effect_risk_gate:*``
  (MHS-4), or any other static-screen / integrity reason.
* ``orchestration/autopilot_journal*.jsonl`` -- trial rows (the denominator) and the ledger
  events ``{"type": "eval_leakage_guard", "event": preflight_failed | alarm_raised |
  alarm_cleared}`` written by ``scripts/autopilot/eval_leakage_monitor.py`` through
  ``ExperimentJournal.append_ledger_event`` (which stamps ``timestamp``).

Two projections, both measurement class, both PROJECT ONLY -- ``claim_tuple.grade()`` decides.
No codified protocol covers loop telemetry, so every tuple is an OBSERVATION and the shared
ladder grades it so; nothing here lifts it.

1. ``mhs_guard_verdict_rate`` -- one row per (closed UTC-day window, reason class). The value
   is a RATE, never a single verdict (one rejection is categorical, README row). Denominator:
   the mutations the guard SCREENED in the window, joined by ``trial_id``:

   * journal rows with ``action_type`` in ``prompt_mutation``/``code_mutation`` that either
     carry an AP-53 record from a screened gate, or reached eval (``outcome_status`` is not
     ``skipped``);
   * a skipped row with NO ledger record (prompt file missing, handler no-op) never produced a
     mutation, and a ``syntax_validation`` reject was refused BEFORE the guard verdict was
     read (``actions.py`` checks syntax first); both are held out and counted in ``extra``.

   ``eval_leakage_vocabulary_unavailable`` rejections are an INSTRUMENT failure: they are held
   out of the ``eval_instance_leakage`` denominator, never folded in (VB-MHS-GATES).

2. ``mhs_guard_operability`` -- one row per ``preflight_failed`` event, and one per CLOSED
   ``alarm_raised -> alarm_cleared`` interval (the instrument-unavailable interval). An open
   interval has no end and yields no row (``open_alarm_intervals`` reports it). A raise that a
   later raise supersedes without a clear (an autopilot restart resets the monitor) has no
   observed end either and yields no row. A clear with no open raise cannot be written by this
   producer and REFUSES the unit.

Absence is recorded, never filled (spec §4.7):

* **pre-hook data gets zero rows.** The AP-53 ledger predates the guard, and nothing the guard
  persists marks a CLEAN window as screened, so the verdict source needs the hook epoch -- the
  moment the gate-frontier producer went live -- from ``VIDYA_MHS_GUARD_HOOK_SINCE`` or
  ``HOOK_SINCE``. Unset, the verdict source declines every unit. Rows before the epoch are
  ignored and the first window starts at the epoch. Operability events are self-dating: the
  event type exists only in the hooked producer.
* **only closed windows project.** A day window is closed when the journal or ledger already
  holds a row at or after its end, so a re-ingest never re-values an existing claim id.
* a window with nothing screened projects nothing: an idle loop is not a 0 % rate.

Attestation: both files are live append-only logs, so no whole-file digest can stay true. The
SHA-256 of the canonical rows a window used rides in ``extra.window_rows_sha256`` as
re-derivation evidence; the locator names the file and the window.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.mhs_guard/v1"
AUTHORITY = "measurement"
VERDICT_PROJECTION = "mhs_guard_verdict_rate"
OPS_PROJECTION = "mhs_guard_operability"
PRODUCER_BRANCH = "sub/gate-frontier-20260916"

#: The hook epoch (ISO-8601, tz-aware). Empty until the gate-frontier producer is live;
#: ``VIDYA_MHS_GUARD_HOOK_SINCE`` overrides it.
HOOK_SINCE = ""
HOOK_SINCE_ENV = "VIDYA_MHS_GUARD_HOOK_SINCE"

LEDGER_FILENAME = "autopilot_rejected_mutations.jsonl"
JOURNAL_GLOB = "autopilot_journal*.jsonl"
LEDGER_SCHEMA_VERSION = 1

# --- producer vocabulary, pinned by tests/vidya/test_mhs_guard_adapter.py ------------------------
#: AP-53 record fields this reader relies on.
LEDGER_FIELDS = ("schema_version", "writer", "timestamp", "trial_id", "rejecting_gate",
                 "gate_detail", "artifact_kind")
#: Journal trial-row fields this reader relies on.
TRIAL_FIELDS = ("trial_id", "timestamp", "action_type", "outcome_status")
#: ``eval_leakage_guard`` ledger-event fields, per event.
EVENT_TYPE = "eval_leakage_guard"
ALARM_KEY = "autopilot-eval-leakage-vocab-unavailable"
EVENT_ACTOR = "autopilot.eval_leakage_monitor"
EVENT_FIELDS = {
    "preflight_failed": ("error", "problem_paths", "sources", "elapsed_s"),
    "alarm_raised": ("consecutive", "threshold", "error", "problem_paths", "alarm_delivered"),
    "alarm_cleared": ("after_consecutive", "alarm_delivered"),
}
MUTATION_ACTIONS = frozenset({"prompt_mutation", "code_mutation"})
GUARD_GATE = "transfer_safety"
#: Gates that refuse a mutation before its guard verdict is read.
PRE_GUARD_GATES = frozenset({"syntax_validation"})
LEAKAGE = "eval_instance_leakage"
VOCAB_UNAVAILABLE = "eval_leakage_vocabulary_unavailable"
EFFECT_RISK = "effect_risk_gate"
OTHER_SCREEN = "other_transfer_safety"
#: reason class -> ``gate_detail`` prefix (the producer's ``safety_reason`` prefixes).
REASON_PREFIXES = {
    LEAKAGE: "eval_instance_leakage:",
    VOCAB_UNAVAILABLE: "eval_leakage_vocabulary_unavailable:",
    EFFECT_RISK: "effect_risk_gate:",
}
REASON_CLASSES = (LEAKAGE, VOCAB_UNAVAILABLE, EFFECT_RISK, OTHER_SCREEN)
METRIC_PREFIX = "autopilot.mutation_guard"
OPS_METRICS = {
    "preflight_failed": "autopilot.eval_leakage_guard.preflight_failed",
    "alarm_interval": "autopilot.eval_leakage_guard.alarm_open_s",
}


# --- reading -------------------------------------------------------------------------------------

def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        ts = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        return None  # a naive stamp has no UTC window; never guessed
    return ts.astimezone(timezone.utc)


def hook_since(value: str | None = None) -> datetime | None:
    """The hook epoch, or None when unset. A malformed epoch is refused, not ignored."""
    raw = value if value is not None else (os.environ.get(HOOK_SINCE_ENV, "") or HOOK_SINCE)
    if not str(raw or "").strip():
        return None
    ts = _parse_ts(raw)
    if ts is None:
        raise ProjectionError(f"{HOOK_SINCE_ENV}={raw!r} is not a tz-aware ISO-8601 timestamp")
    return ts


def _dir_of(unit: str | Path) -> Path:
    path = Path(unit)
    return path.parent if path.is_file() else path


def _dir_tag(journal_dir: Path) -> str:
    return hashlib.sha256(str(journal_dir.resolve()).encode()).hexdigest()[:10]


def _jsonl(path: Path) -> Iterator[tuple[int, Any]]:
    """(line number, parsed value or None for a non-JSON line)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                yield n, json.loads(line)
            except json.JSONDecodeError:
                yield n, None


def journal_shards(journal_dir: Path) -> list[Path]:
    return sorted(p for p in journal_dir.glob(JOURNAL_GLOB) if p.is_file())


def _read_journal(journal_dir: Path) -> tuple[list[dict], list[dict], int, datetime | None]:
    """(trial rows, eval_leakage_guard events, unreadable lines, latest timestamp)."""
    trials: list[dict] = []
    events: list[dict] = []
    unreadable = 0
    latest: datetime | None = None
    for shard in journal_shards(journal_dir):
        for n, row in _jsonl(shard):
            if not isinstance(row, dict):
                unreadable += 1
                continue
            ts = _parse_ts(row.get("timestamp"))
            if ts is not None and (latest is None or ts > latest):
                latest = ts
            if row.get("type") == EVENT_TYPE:
                events.append({"row": row, "ts": ts, "where": f"{shard.name}:{n}"})
            elif "trial_id" in row:
                trials.append({"row": row, "ts": ts})
    return trials, events, unreadable, latest


def _read_ledger(journal_dir: Path) -> tuple[list[dict], datetime | None]:
    path = journal_dir / LEDGER_FILENAME
    records: list[dict] = []
    latest: datetime | None = None
    for n, row in _jsonl(path):
        if not isinstance(row, dict):
            raise ProjectionError(f"{path.name}:{n}: non-JSON line in a harness-written ledger")
        missing = [f for f in LEDGER_FIELDS if f not in row]
        if missing:
            raise ProjectionError(f"{path.name}:{n}: AP-53 record lacks {missing}")
        if row["schema_version"] != LEDGER_SCHEMA_VERSION or row["writer"] != "harness":
            raise ProjectionError(
                f"{path.name}:{n}: not an AP-53 v{LEDGER_SCHEMA_VERSION} harness record")
        ts = _parse_ts(row["timestamp"])
        if ts is None:
            raise ProjectionError(f"{path.name}:{n}: unparseable timestamp {row['timestamp']!r}")
        latest = ts if latest is None or ts > latest else latest
        records.append({"row": row, "ts": ts, "line": n})
    return records, latest


def reason_class(gate_detail: str) -> str:
    for cls, prefix in REASON_PREFIXES.items():
        if gate_detail.startswith(prefix):
            return cls
    return OTHER_SCREEN


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


# --- guard verdicts ------------------------------------------------------------------------------

def verdict_windows(unit: str | Path, *, since: str | None = None) -> list[dict]:
    """Closed post-hook day windows with their screened set and reason counts."""
    journal_dir = _dir_of(unit)
    epoch = hook_since(since)
    if epoch is None or not (journal_dir / LEDGER_FILENAME).is_file():
        return []
    trials, _events, unreadable, j_latest = _read_journal(journal_dir)
    records, l_latest = _read_ledger(journal_dir)
    latest = max((t for t in (j_latest, l_latest) if t is not None), default=None)

    mutations: dict[int, dict] = {}
    for item in trials:
        row, ts = item["row"], item["ts"]
        if row.get("action_type") not in MUTATION_ACTIONS or ts is None or ts < epoch:
            continue
        missing = [f for f in TRIAL_FIELDS if f not in row]
        if missing:
            raise ProjectionError(f"journal mutation row lacks {missing}")
        tid = row["trial_id"]
        if not isinstance(tid, int) or tid in mutations:
            raise ProjectionError(f"post-hook mutation trial_id {tid!r} is not a unique int; "
                                  "ledger records cannot be joined")
        mutations[tid] = item

    by_trial: dict[int, dict] = {}
    for rec in records:
        if rec["ts"] < epoch:
            continue
        tid = rec["row"]["trial_id"]
        if tid not in mutations:
            raise ProjectionError(
                f"{LEDGER_FILENAME}:{rec['line']}: post-hook record for trial {tid!r} has no "
                "post-hook mutation row in the journal")
        if tid in by_trial:
            raise ProjectionError(f"{LEDGER_FILENAME}:{rec['line']}: second record for trial {tid}")
        by_trial[tid] = rec

    windows: dict[datetime, dict] = {}
    for tid, item in sorted(mutations.items()):
        day = item["ts"].replace(hour=0, minute=0, second=0, microsecond=0)
        start, end = max(day, epoch), day + timedelta(days=1)
        if latest is None or latest < end:
            continue  # window still open
        win = windows.setdefault(start, {
            "start": start, "end": end, "screened": [], "unscreened_skips": [],
            "pre_guard_rejects": [], "counts": dict.fromkeys(REASON_CLASSES, 0),
            "other_gate_rejects": 0, "rows": [],
        })
        rec = by_trial.get(tid)
        status = item["row"].get("outcome_status")
        if rec is None:
            if status == "skipped":
                win["unscreened_skips"].append(tid)
                continue
        elif rec["row"]["rejecting_gate"] in PRE_GUARD_GATES:
            win["pre_guard_rejects"].append(tid)
            continue
        win["screened"].append(tid)
        entry = {"trial_id": tid, "action_type": item["row"]["action_type"],
                 "outcome_status": status, "timestamp": item["row"]["timestamp"]}
        if rec is not None:
            gate = rec["row"]["rejecting_gate"]
            entry.update(rejecting_gate=gate, gate_detail=rec["row"]["gate_detail"],
                         diff_sha256=rec["row"].get("diff_sha256", ""))
            if gate == GUARD_GATE:
                win["counts"][reason_class(str(rec["row"]["gate_detail"]))] += 1
            else:
                win["other_gate_rejects"] += 1
        win["rows"].append(entry)
    out = []
    for start in sorted(windows):
        win = windows[start]
        win["unreadable_journal_lines"] = unreadable
        win["journal_dir"] = str(journal_dir)
        win["epoch"] = epoch
        out.append(win)
    return out


def native_rows(unit: str | Path, *, since: str | None = None) -> tuple[dict, ...]:
    """One native per (closed window, reason class) with a non-zero denominator."""
    out: list[dict] = []
    for win in verdict_windows(unit, since=since):
        screened = len(win["screened"])
        if screened == 0:
            continue
        digest = hashlib.sha256(_canon(win["rows"]).encode()).hexdigest()
        for cls in REASON_CLASSES:
            denominator = screened - (win["counts"][VOCAB_UNAVAILABLE] if cls == LEAKAGE else 0)
            if denominator < 1:
                continue
            out.append({
                "kind": VERDICT_PROJECTION, "reason_class": cls,
                "rejections": win["counts"][cls], "denominator": denominator,
                "screened": screened, "counts": dict(win["counts"]),
                "window_start": win["start"].isoformat(), "window_end": win["end"].isoformat(),
                "hook_since": win["epoch"].isoformat(), "journal_dir": win["journal_dir"],
                "unscreened_skips": list(win["unscreened_skips"]),
                "pre_guard_rejects": list(win["pre_guard_rejects"]),
                "other_gate_rejects": win["other_gate_rejects"],
                "unreadable_journal_lines": win["unreadable_journal_lines"],
                "window_rows_sha256": digest,
            })
    return tuple(out)


@register(VERDICT_PROJECTION)
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one window-class rate. Grading stays in ``claim_tuple.grade()``."""
    if not isinstance(native, Mapping) or native.get("kind") != VERDICT_PROJECTION:
        raise ProjectionError("not a mhs_guard verdict-rate native (use native_rows)")
    cls = native.get("reason_class")
    if cls not in REASON_CLASSES:
        raise ProjectionError(f"unknown reason class {cls!r}")
    k, n, screened = native.get("rejections"), native.get("denominator"), native.get("screened")
    counts = native.get("counts") or {}
    if not all(isinstance(v, int) for v in (k, n, screened)) or not 0 <= k <= n <= screened:
        raise ProjectionError("rate must satisfy 0 <= rejections <= denominator <= screened")
    expected_n = screened - (counts.get(VOCAB_UNAVAILABLE, 0) if cls == LEAKAGE else 0)
    if n != expected_n or n < 1:
        raise ProjectionError(
            "denominator does not re-derive: vocabulary-unavailable rejections are held out of "
            "the leakage denominator only, and an empty window is not a rate")
    if len(str(native.get("window_rows_sha256") or "")) != 64:
        raise ProjectionError("window_rows_sha256 must be the 64-hex digest of the rows used")
    start, end = str(native["window_start"]), str(native["window_end"])
    journal_dir = str(native["journal_dir"])
    tag = _dir_tag(Path(journal_dir))
    held_out = (f"; {counts.get(VOCAB_UNAVAILABLE, 0)} vocabulary-unavailable rejection(s) held "
                "out of the denominator" if cls == LEAKAGE else "")
    return ClaimTuple(
        measurement_id=(f"mhs_guard_{tag}_{start[:19].replace(':', '')}_{cls}"
                        f"_h{native['hook_since'][:19].replace(':', '')}"),
        metric=f"{METRIC_PREFIX}.{cls}_rate",
        value=round(k / n, 6),
        date=start[:10],
        category="BASELINE",
        claim=(f"AutoPilot mutation guard, window {start} .. {end}: {k} of {n} screened "
               f"mutation(s) rejected as {cls} ({k / n:.4f}){held_out}; first-firing reason "
               "per mutation, from the AP-53 ledger joined to journal trial rows"),
        metric_direction="lower_better",
        protocol_id="",
        reps=n,
        reps_basis="scored: mutations whose guard verdict was recorded in the window",
        unit="fraction",
        attestation_locator=f"{journal_dir}/{LEDGER_FILENAME}#window={start}/{end}",
        source_kind="measurement",
        extra={
            "producer_branch": PRODUCER_BRANCH, "reason_class": cls,
            "rejections": k, "denominator": n, "screened": screened, "counts": dict(counts),
            "hook_since": native["hook_since"], "window_start": start, "window_end": end,
            "unscreened_skips": list(native.get("unscreened_skips") or []),
            "pre_guard_rejects": list(native.get("pre_guard_rejects") or []),
            "other_gate_rejects": native.get("other_gate_rejects", 0),
            "unreadable_journal_lines": native.get("unreadable_journal_lines", 0),
            "window_rows_sha256": native["window_rows_sha256"],
        },
    )


# --- operability ---------------------------------------------------------------------------------

def _validated_events(journal_dir: Path) -> list[dict]:
    _trials, events, _unreadable, _latest = _read_journal(journal_dir)
    out = []
    for item in events:
        row, where = item["row"], item["where"]
        event = row.get("event")
        if event not in EVENT_FIELDS:
            raise ProjectionError(f"{where}: unknown {EVENT_TYPE} event {event!r}")
        if row.get("alarm_key") != ALARM_KEY or row.get("actor") != EVENT_ACTOR:
            raise ProjectionError(f"{where}: {EVENT_TYPE} row not written by {EVENT_ACTOR}")
        missing = [f for f in EVENT_FIELDS[event] if f not in row]
        if missing:
            raise ProjectionError(f"{where}: {event} lacks {missing}")
        if item["ts"] is None:
            raise ProjectionError(f"{where}: {event} has no tz-aware timestamp")
        out.append(item)
    out.sort(key=lambda i: i["ts"])
    return out


def _intervals(journal_dir: Path) -> tuple[list[dict], list[dict]]:
    """(closed intervals, raises with no observed end)."""
    closed: list[dict] = []
    unended: list[dict] = []
    open_raise: dict | None = None
    for item in _validated_events(journal_dir):
        event = item["row"]["event"]
        if event == "alarm_raised":
            if open_raise is not None:
                unended.append({**open_raise, "superseded_by": item["where"]})
            open_raise = item
        elif event == "alarm_cleared":
            if open_raise is None:
                raise ProjectionError(
                    f"{item['where']}: alarm_cleared with no open alarm_raised; this producer "
                    "journals a clear only while its alarm is active")
            closed.append({"raised": open_raise, "cleared": item})
            open_raise = None
    if open_raise is not None:
        unended.append(open_raise)
    return closed, unended


def open_alarm_intervals(unit: str | Path) -> list[dict]:
    """Raises with no observed end (still open, or superseded after a restart)."""
    return [{"raised_at": i["ts"].isoformat(), "where": i["where"],
             "error": i["row"].get("error"), "superseded_by": i.get("superseded_by")}
            for i in _intervals(_dir_of(unit))[1]]


def ops_native_rows(unit: str | Path) -> tuple[dict, ...]:
    journal_dir = _dir_of(unit)
    if not journal_shards(journal_dir):
        return ()
    out: list[dict] = []
    for item in _validated_events(journal_dir):
        if item["row"]["event"] == "preflight_failed":
            out.append({"kind": OPS_PROJECTION, "event": "preflight_failed",
                        "journal_dir": str(journal_dir), "where": item["where"],
                        "row": item["row"]})
    for pair in _intervals(journal_dir)[0]:
        out.append({"kind": OPS_PROJECTION, "event": "alarm_interval",
                    "journal_dir": str(journal_dir),
                    "where": f"{pair['raised']['where']}..{pair['cleared']['where']}",
                    "raised": pair["raised"]["row"], "cleared": pair["cleared"]["row"]})
    return tuple(out)


@register(OPS_PROJECTION)
def project_ops(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one operability finding. Grading stays in ``claim_tuple.grade()``."""
    if not isinstance(native, Mapping) or native.get("kind") != OPS_PROJECTION:
        raise ProjectionError("not a mhs_guard operability native (use ops_native_rows)")
    journal_dir = str(native.get("journal_dir") or "")
    tag = _dir_tag(Path(journal_dir))
    locator = f"{journal_dir}/{native.get('where')}"
    if native.get("event") == "preflight_failed":
        row = native["row"]
        ts = _parse_ts(row.get("timestamp"))
        if row.get("event") != "preflight_failed" or ts is None:
            raise ProjectionError("preflight native does not carry its producer event")
        stamp = ts.strftime("%Y%m%dT%H%M%S")
        return ClaimTuple(
            measurement_id=f"mhs_ops_{tag}_preflight_{stamp}",
            metric=OPS_METRICS["preflight_failed"], value=1, date=ts.date().isoformat(),
            category="BASELINE",
            claim=(f"AutoPilot eval-leakage guard startup preflight FAILED at {ts.isoformat()} "
                   f"({row['error']}); the MHS-3 guard could not screen, so every mutation is "
                   f"rejected fail-closed. Problem path(s): {', '.join(row['problem_paths'])}"),
            metric_direction="lower_better", protocol_id="", reps=1,
            reps_basis="events: one journaled preflight", unit="event",
            attestation_locator=locator, source_kind="measurement",
            extra={"producer_branch": PRODUCER_BRANCH, "event": "preflight_failed",
                   "timestamp": row["timestamp"], "error": row["error"],
                   "problem_paths": list(row["problem_paths"]), "elapsed_s": row["elapsed_s"],
                   "event_sha256": hashlib.sha256(_canon(row).encode()).hexdigest()},
        )
    if native.get("event") != "alarm_interval":
        raise ProjectionError(f"unknown operability event {native.get('event')!r}")
    raised, cleared = native.get("raised") or {}, native.get("cleared") or {}
    t0, t1 = _parse_ts(raised.get("timestamp")), _parse_ts(cleared.get("timestamp"))
    if (raised.get("event"), cleared.get("event")) != ("alarm_raised", "alarm_cleared") \
            or t0 is None or t1 is None or t1 < t0:
        raise ProjectionError("alarm interval must be a raised -> cleared pair in time order")
    seconds = round((t1 - t0).total_seconds(), 3)
    return ClaimTuple(
        measurement_id=f"mhs_ops_{tag}_alarm_{t0.strftime('%Y%m%dT%H%M%S')}",
        metric=OPS_METRICS["alarm_interval"], value=seconds, date=t0.date().isoformat(),
        category="BASELINE",
        claim=(f"AutoPilot eval-leakage guard was UNAVAILABLE (alarm {ALARM_KEY} open) from "
               f"{t0.isoformat()} to {t1.isoformat()} ({seconds} s): raised after "
               f"{raised['consecutive']} consecutive fail-closed verdicts ({raised['error']}), "
               f"cleared after {cleared['after_consecutive']}"),
        metric_direction="lower_better", protocol_id="", reps=1,
        reps_basis="events: one journaled raised->cleared interval", unit="s",
        attestation_locator=locator, source_kind="measurement",
        extra={"producer_branch": PRODUCER_BRANCH, "event": "alarm_interval",
               "raised_at": raised["timestamp"], "cleared_at": cleared["timestamp"],
               "consecutive_at_raise": raised["consecutive"], "threshold": raised["threshold"],
               "error": raised["error"], "problem_paths": list(raised["problem_paths"]),
               "after_consecutive": cleared["after_consecutive"],
               "raise_delivered": raised["alarm_delivered"],
               "clear_delivered": cleared["alarm_delivered"],
               "events_sha256": hashlib.sha256(_canon([raised, cleared]).encode()).hexdigest()},
    )


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "HOOK_SINCE", "HOOK_SINCE_ENV", "LEDGER_FIELDS", "TRIAL_FIELDS",
    "EVENT_FIELDS", "REASON_PREFIXES", "REASON_CLASSES", "hook_since", "reason_class",
    "verdict_windows", "native_rows", "project", "ops_native_rows", "project_ops",
    "open_alarm_intervals",
]
