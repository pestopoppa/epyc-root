"""Read counter: how often did a belief read find something (VB-REFOCUS-READ-COUNTER).

Standing metric per consumer / per target: reads whose TARGET tier was non-empty vs empty
(DESIGN.md 7.4 `evidence.nonempty_target`). A consumer whose reads are all empty never changes
an outcome, and that must be visible without a manual review (the 933-empty-reads finding).

Two writers/sources, one report:
  * the READ LOG -- one self-describing JSON line per `loop_beliefs.prepare`, appended by
    `record_read` (default `reads.jsonl` beside the resolved ledger; override with the
    `read_log=` kwarg or VIDYA_READ_LOG). A failed write never fails `prepare`.
  * the consumers' own RECEIPTS, so history from before the read log counts too:
    AutoKernel `belief-receipts.jsonl` (v1 = no tiers: non-empty iff it exposed a claim;
    v2 = `evidence_v2.nonempty_target`), AutoPilot `planner_archive.jsonl` rows carrying
    `vidya_loop_beliefs` (status "ready" -> `nonempty_target`; absent/degraded = `no_read`).

A read present in both (same consumer + as_of) is counted once, the read-log row winning.
No grading happens here: this only tallies an already-computed boolean.

    python3 scripts/vidya/read_counter.py [--days N | --since TS --until TS] [--json]
        [--read-log P] [--autokernel-root DIR] [--autopilot-archive P]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

log = logging.getLogger("vidya.read_counter")

SCHEMA = "epyc.vidya.read_record.v1"
REPORT_SCHEMA = "epyc.vidya.read_counter.v1"
DEFAULT_AUTOKERNEL_ROOT = Path("/mnt/raid0/llm/autokernel")
DEFAULT_AUTOPILOT_ARCHIVE = Path("/mnt/raid0/llm/epyc-orchestrator/logs/planner_archive.jsonl")
OUTCOMES = ("nonempty", "empty", "refused", "no_read")


def read_log_path(ledger: str | Path | None, explicit: str | Path | None = None) -> Path:
    """explicit arg > VIDYA_READ_LOG > `reads.jsonl` beside the ledger."""
    if explicit:
        return Path(explicit)
    env = os.environ.get("VIDYA_READ_LOG")
    if env:
        return Path(env)
    return Path(ledger).parent / "reads.jsonl" if ledger else Path("reads.jsonl")


def build_record(answer: Mapping[str, Any]) -> dict[str, Any]:
    ev = answer.get("evidence") if isinstance(answer.get("evidence"), Mapping) else {}
    tiers = ev.get("tiers") if isinstance(ev.get("tiers"), Mapping) else {}
    targets = answer.get("targets") or []
    labels = sorted({_label(t) for t in targets if isinstance(t, Mapping)}) or \
        [str(x) for x in ev.get("empty_targets") or []]
    ready = answer.get("status") == "ready"
    return {"schema": SCHEMA, "consumer": answer.get("consumer") or "unknown",
            "target_key": ",".join(labels) or "unknown", "as_of": answer.get("as_of"),
            "status": answer.get("status"), "reason": answer.get("reason"),
            "nonempty_target": bool(ev.get("nonempty_target")) if ready else False,
            "usable_count": len(ev.get("claim_ids") or []) if ready else 0,
            "tier_counts": {str(k): int(v) for k, v in tiers.items() if isinstance(v, int)}}


def _label(t: Mapping[str, Any]) -> str:
    if t.get("is_lineup") or t.get("lineup"):
        return f"lineup:{t.get('stack_regime') or 'unrecorded'}"
    mf = t.get("model_file") or t.get("model_path") or "unknown"
    return os.path.basename(str(mf))


def record_read(answer: Mapping[str, Any], *, ledger: str | Path | None = None,
                read_log: str | Path | None = None) -> str | None:
    """Append one record. Never raises; returns an error string (also logged) or None."""
    try:
        path = read_log_path(ledger or answer.get("ledger_path"), read_log)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            fh.write(json.dumps(build_record(answer), sort_keys=True, separators=(",", ":"),
                                default=str) + "\n")
        return None
    except Exception as exc:  # noqa: BLE001 -- the read log must never fail a plan
        msg = f"{type(exc).__name__}: {exc}"[:300]
        log.warning("read log write failed: %s", msg)
        return msg


# --------------------------------------------------------------------------- sources


def _ts(value: Any) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _jsonl(path: Path) -> Iterable[dict]:
    try:
        with open(path) as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    yield row
    except OSError:
        return


def _readlog_events(path: Path):
    for r in _jsonl(path):
        if r.get("schema") != SCHEMA:
            continue
        out = ("refused" if r.get("status") != "ready" else
               "nonempty" if r.get("nonempty_target") else "empty")
        yield {"source": "read_log", "consumer": r.get("consumer") or "unknown",
               "target": r.get("target_key") or "unknown", "as_of": r.get("as_of"),
               "ts": _ts(r.get("as_of")), "outcome": out}


def _ak_target(t: Any) -> str:
    if not isinstance(t, Mapping):
        return "unknown"
    mp = t.get("model_file") or t.get("model_path")
    return os.path.basename(str(mp)) if mp else str(t.get("surface") or "unknown")


def _autokernel_events(root: Path):
    if not root.is_dir():
        return
    for p in sorted(root.rglob("belief-receipts.jsonl")):
        for r in _jsonl(p):
            v2 = r.get("evidence_v2") if isinstance(r.get("evidence_v2"), Mapping) else None
            if r.get("status") == "refused":
                out = "refused"
            elif v2 is not None and isinstance(v2.get("nonempty_target"), bool):
                out = "nonempty" if v2["nonempty_target"] else "empty"
            else:  # v1: no tiers; a read that exposed a usable claim is the closest honest proxy
                out = "nonempty" if r.get("claim_ids") else "empty"
            yield {"source": "autokernel_receipt", "consumer": r.get("consumer") or "autokernel.planner",
                   "target": _ak_target(r.get("target")), "as_of": r.get("as_of"),
                   "ts": _ts(r.get("ts") or r.get("as_of")), "outcome": out}


def _autopilot_events(path: Path):
    for r in _jsonl(path):
        v = r.get("vidya_loop_beliefs")
        if not isinstance(v, Mapping):
            continue
        if v.get("status") == "ready":
            out = "nonempty" if v.get("nonempty_target") else "empty"
        else:
            out = "no_read"
        yield {"source": "autopilot_receipt", "consumer": v.get("consumer") or "autopilot.planner",
               "target": "unknown", "as_of": v.get("as_of"),
               "ts": _ts(r.get("ts") or v.get("as_of")), "outcome": out}


# --------------------------------------------------------------------------- report


def build_report(*, read_log: Path | None = None, autokernel_root: Path | None = None,
                 autopilot_archive: Path | None = None, since: datetime | None = None,
                 until: datetime | None = None) -> dict[str, Any]:
    events: list[dict] = []
    seen: set[tuple] = set()
    streams = []
    if read_log:
        streams.append(_readlog_events(Path(read_log)))  # first: wins the dedup
    if autokernel_root:
        streams.append(_autokernel_events(Path(autokernel_root)))
    if autopilot_archive:
        streams.append(_autopilot_events(Path(autopilot_archive)))
    deduped = 0
    for stream in streams:
        for ev in stream:
            if since and (ev["ts"] is None or ev["ts"] < since):
                continue
            if until and (ev["ts"] is None or ev["ts"] > until):
                continue
            if ev["as_of"]:
                key = (ev["consumer"], str(ev["as_of"]))
                if key in seen and ev["source"] != "read_log":
                    deduped += 1
                    continue
                seen.add(key)
            events.append(ev)

    def tally(keyf):
        out: dict[str, dict[str, Any]] = {}
        for ev in events:
            row = out.setdefault(keyf(ev), {o: 0 for o in OUTCOMES} | {"total": 0})
            row[ev["outcome"]] += 1
            row["total"] += 1
        for row in out.values():
            judged = row["nonempty"] + row["empty"]
            row["nonempty_rate"] = round(row["nonempty"] / judged, 4) if judged else None
        return dict(sorted(out.items()))

    return {"schema": REPORT_SCHEMA, "window": {"since": since.isoformat() if since else None,
                                                "until": until.isoformat() if until else None},
            "sources": sorted({e["source"] for e in events}), "deduplicated": deduped,
            "total": len(events), "by_consumer": tally(lambda e: e["consumer"]),
            "by_consumer_target": tally(lambda e: f'{e["consumer"]} | {e["target"]}'),
            "by_source": tally(lambda e: e["source"])}


def render(rep: Mapping[str, Any]) -> str:
    lines = [f"read counter: {rep['total']} reads, sources {rep['sources']}, "
             f"{rep['deduplicated']} duplicate(s) collapsed"]
    for title, key in (("per consumer", "by_consumer"), ("per consumer | target", "by_consumer_target")):
        lines.append(f"-- {title}")
        for name, r in rep[key].items():
            rate = "n/a" if r["nonempty_rate"] is None else f"{100 * r['nonempty_rate']:.1f}%"
            lines.append(f"  {name}: nonempty {r['nonempty']}  empty {r['empty']}  "
                         f"refused {r['refused']}  no_read {r['no_read']}  (nonempty rate {rate})")
    return "\n".join(lines)


def _default_read_log() -> Path:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ledger_home
        return read_log_path(ledger_home.default_ledger_path())
    except Exception:  # noqa: BLE001
        return Path("/mnt/raid0/llm/state/vidya/reads.jsonl")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--read-log", default=None)
    ap.add_argument("--autokernel-root", default=str(DEFAULT_AUTOKERNEL_ROOT))
    ap.add_argument("--autopilot-archive", default=str(DEFAULT_AUTOPILOT_ARCHIVE))
    ap.add_argument("--no-receipts", action="store_true", help="read log only")
    ap.add_argument("--days", type=float, default=None)
    ap.add_argument("--since", default=None)
    ap.add_argument("--until", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    since = _ts(a.since) if a.since else None
    until = _ts(a.until) if a.until else None
    if a.days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=a.days)
    rep = build_report(read_log=Path(a.read_log) if a.read_log else _default_read_log(),
                       autokernel_root=None if a.no_receipts else Path(a.autokernel_root),
                       autopilot_archive=None if a.no_receipts else Path(a.autopilot_archive),
                       since=since, until=until)
    print(json.dumps(rep, indent=1, sort_keys=True) if a.json else render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
