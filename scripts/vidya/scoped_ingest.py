#!/usr/bin/env python3
"""VB-LOOP-SCOPE: scope-aware, idempotent ingest for loop belief sources.

TWO JOBS, ONE RULE.

1. `scope_aware_frames(existing, incoming)` decides which projected frames a ledger still needs,
   per claim bundle (source_observed + claim_proposed + evidence_supports_claim):

     * new claim (nothing in the ledger)            -> the whole bundle is appended;
     * live claim, same `applicability` as the ledger's LAST source_observed for its source
                                                    -> nothing (idempotent re-run);
     * live claim whose scope differs (typically: written before VB-APPLICABILITY, so it has
       none)                                        -> ONE re-observation: the freshly projected
       source_observed frame for the same source_id, carrying the scope. The claim and its
       evidence are NOT re-emitted, so support is never counted twice. Emitted only when the
       re-projected claim assertion and evidence assertion equal the ledger's -- a re-observation
       that disagrees with the recorded claim is reported (`diverged`), never written;
     * partial ledger state, or a claim whose support was withdrawn -> reported, never written
       (an automatic ingest must not revive withdrawn evidence; same stance as `--only-new`).

   Why the re-observation is benign: `fold` reads source_observed frames for exactly one thing,
   the source's locator (last observation wins), which keys support by SOURCE for independence
   counting. A claim's support count, grades, verdict, corrections and gate outcome do not move;
   `tests/vidya/test_scoped_ingest.py` pins that over the fold and the gate. The loop reader keeps
   the LAST source_observed per source_id, so the scope becomes visible to it.

2. `ingest_scoped_store(ledger, store_root, as_of=...)` is the producer-time entry point a loop's
   planning-step freshness check calls for ITS OWN store. It ingests AutoKernel direct-serving
   receipts (`<store>/serving-beliefs/<capture_id>.json`, `epyc.vidya.legacy_serving_receipt.v1`,
   the candidate-vs-anchor serving A/B the loop archives per experiment) through the unchanged
   strict adapter and the corpus walker's own dispatch + SC69 verification stamp. It never walks
   the store recursively: it lists one directory per store, and only receipts whose capture id has
   no source in the ledger are opened. Optional `memo_path` remembers refused receipts by
   (name, size, mtime_ns) so a strict refusal is not re-derived on every planning step.

Stdlib + ROOT `scripts/vidya` only. The ledger write happens under the ledger's own writer lock.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fold import FT_CLAIM, FT_OPPOSE, FT_SOURCE, FT_SUPPORT, fold  # noqa: E402
from ledger import Ledger  # noqa: E402

RECEIPT_DIR = "serving-beliefs"
_RECEIPT_NAME = re.compile(r"[0-9a-f]{64}\.json\Z")
MEMO_SCHEMA = "epyc.vidya.scoped_ingest_memo.v1"
REPORT_SCHEMA = "epyc.vidya.scoped_ingest_report.v1"


# ------------------------------------------------------------------------------ the filter


def _bundles(frames: Iterable[Mapping[str, Any]]) -> tuple[dict, dict, dict]:
    """claim_id -> (source frame, claim frame, [evidence frames]) of a PROJECTED batch."""
    sources: dict[str, Mapping[str, Any]] = {}
    claims: dict[str, Mapping[str, Any]] = {}
    evidence: dict[str, list[Mapping[str, Any]]] = {}
    for frame in frames:
        ftype, assertion = frame.get("frame_type"), frame.get("assertion") or {}
        if ftype == FT_SOURCE:
            sources[str(assertion.get("source_id"))] = frame
        elif ftype == FT_CLAIM:
            claims[str(assertion.get("claim_id"))] = frame
        elif ftype in (FT_SUPPORT, FT_OPPOSE):
            evidence.setdefault(str(assertion.get("claim_id")), []).append(frame)
        else:
            raise ValueError(f"scoped ingest cannot filter frame type {ftype!r}")
    return sources, claims, evidence


def _payload(frame: Mapping[str, Any]) -> dict:
    """A frame's content without its id and its ingest timestamp (repeat projections compare)."""
    out = {k: v for k, v in frame.items() if k != "frame_id"}
    out["pubinfo"] = {k: v for k, v in (frame.get("pubinfo") or {}).items() if k != "created_at"}
    return out


def scope_aware_frames(existing: list[Mapping[str, Any]], incoming: list[Mapping[str, Any]], *,
                       as_of: str, fold_result: Any = None) -> tuple[list[dict], dict]:
    """(frames to append, report). `existing` is the ledger in ledger order. Pure: no I/O."""
    result = fold_result if fold_result is not None else fold(existing, as_of=as_of)
    live = {cid for cid, belief in result.beliefs.items() if belief.pro_paths or belief.con_paths}
    last_source: dict[str, Mapping[str, Any]] = {}
    last_claim: dict[str, Mapping[str, Any]] = {}
    last_evidence: dict[str, Mapping[str, Any]] = {}
    for frame in existing:
        ftype, assertion = frame.get("frame_type"), frame.get("assertion") or {}
        if ftype == FT_SOURCE:
            last_source[str(assertion.get("source_id"))] = assertion
        elif ftype == FT_CLAIM:
            last_claim[str(assertion.get("claim_id"))] = assertion
        elif ftype in (FT_SUPPORT, FT_OPPOSE):
            last_evidence[str(assertion.get("claim_id"))] = assertion

    sources, claims, evidence = _bundles(incoming)
    report: dict[str, Any] = {"new_claims": 0, "rescoped": 0, "already_present": 0,
                              "refused": []}
    keep_ids: set[str] = set()
    rescope_sources: set[str] = set()
    for cid, claim_frame in claims.items():
        sid = str(claim_frame["assertion"].get("source_id"))
        if sid not in sources or cid not in evidence:
            report["refused"].append({"claim_id": cid, "reason": "partial projected bundle"})
            continue
        present = (sid in last_source, cid in last_claim, cid in last_evidence)
        if not any(present):
            keep_ids.add(cid)
            report["new_claims"] += 1
            continue
        if not all(present):
            report["refused"].append({"claim_id": cid, "reason": "partial ledger state"})
            continue
        if result.alias_map.get(cid, cid) not in live:
            report["refused"].append({"claim_id": cid, "reason": "historical claim with no live "
                                      "evidence; never revived by an automatic ingest"})
            continue
        wanted = sources[sid]["assertion"].get("applicability") or {}
        if (last_source[sid].get("applicability") or {}) == wanted:
            report["already_present"] += 1
            continue
        if (claim_frame["assertion"] != last_claim[cid]
                or any(frame["assertion"] != last_evidence[cid] for frame in evidence[cid])):
            report["refused"].append({"claim_id": cid, "reason": "diverged: the re-projected "
                                      "claim/evidence differ from the ledger; not re-scoped"})
            continue
        rescope_sources.add(sid)
        report["rescoped"] += 1

    keep_sources = {str(claims[cid]["assertion"].get("source_id")) for cid in keep_ids}
    emitted: dict[tuple[str, str], dict] = {}
    kept: list[dict] = []
    for frame in incoming:
        ftype, assertion = frame["frame_type"], frame["assertion"]
        if ftype == FT_SOURCE:
            ident = str(assertion.get("source_id"))
            keep = ident in keep_sources or ident in rescope_sources
        else:
            ident = str(assertion.get("claim_id"))
            keep = ident in keep_ids
        if not keep:
            continue
        key = (ftype, ident)
        payload = _payload(frame)
        if key in emitted:
            if emitted[key] != payload:
                raise ValueError(f"conflicting projected frames for {ident}")
            continue
        emitted[key] = payload
        kept.append(dict(frame))
    report["frames"] = len(kept)
    return kept, report


def append_scoped(ledger: Ledger, incoming: list[dict], *, as_of: str,
                  dry_run: bool = False) -> dict:
    """Filter `incoming` against the ledger and append, as one critical section."""
    with ledger.write_lock():
        records = ledger.read_all()
        problems = ledger.verify() if records else []
        if problems:
            raise ValueError("refusing to ingest into an invalid ledger: " + "; ".join(problems))
        kept, report = scope_aware_frames([r.frame for r in records], incoming, as_of=as_of)
        if not dry_run:
            for frame in kept:
                ledger.append(frame)
    report["dry_run"] = dry_run
    return report


class Collector:
    """A ledger stand-in for producers that append as they project (`ingest_corpus`)."""

    def __init__(self) -> None:
        self.frames: list[dict] = []

    def append(self, frame: dict) -> None:
        self.frames.append(frame)


# ------------------------------------------------------------------------------ producer entry


def _receipt_dirs(store_root: Path) -> list[Path]:
    """`<store>/serving-beliefs`, or each `<campaign>/<store>/serving-beliefs` one level down."""
    own = store_root / RECEIPT_DIR
    if own.is_dir():
        return [own]
    return sorted(path for path in store_root.glob(f"*/{RECEIPT_DIR}") if path.is_dir())


def _read_memo(path: Path | None) -> dict:
    if path is None:
        return {}
    try:
        body = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return body.get("refused", {}) if body.get("schema") == MEMO_SCHEMA else {}


def _write_memo(path: Path | None, refused: Mapping[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"schema": MEMO_SCHEMA, "refused": dict(refused)}, sort_keys=True))
    os.replace(tmp, path)


def _ledger_capture_ids(frames: Iterable[Mapping[str, Any]]) -> set[str]:
    """Captures whose every arm's LAST source observation already carries a scope.

    A capture ingested before VB-LOOP-SCOPE (no applicability) is NOT known: it is reopened so
    the filter can emit its one re-observation frame.
    """
    scoped: dict[str, dict[str, bool]] = {}
    for frame in frames:
        if frame.get("frame_type") == FT_SOURCE:
            assertion = frame.get("assertion") or {}
            sid = str(assertion.get("source_id") or "")
            if sid.startswith("src_legacy-serving:") and sid.count(":") == 2:
                _, capture, arm = sid.split(":")
                scoped.setdefault(capture, {})[arm] = bool(assertion.get("applicability"))
    return {capture for capture, arms in scoped.items() if arms and all(arms.values())}


def ingest_scoped_store(ledger: Ledger | str | Path, store_root: str | Path, *, as_of: str,
                        dry_run: bool = False, memo_path: str | Path | None = None,
                        frames: list[Mapping[str, Any]] | None = None) -> dict:
    """Ingest the AutoKernel serving A/B receipts of ONE loop store (or a campaign's stores).

    Idempotent: a capture whose source is already in the ledger is not reopened, and a re-run
    appends nothing. `frames` (the ledger's frames the caller already read) skips one ledger
    read on the fast path. Returns a report; raises only on an invalid ledger.
    """
    from adapters import autokernel_corpus as corpus  # noqa: PLC0415
    from adapters import autokernel_legacy_serving as serving  # noqa: PLC0415
    from claim_tuple import ProjectionError, to_frames  # noqa: PLC0415

    started = time.monotonic()
    led = ledger if isinstance(ledger, Ledger) else Ledger(Path(ledger))
    root = Path(store_root)
    memo = Path(memo_path) if memo_path else None
    refused_memo = _read_memo(memo)
    report: dict[str, Any] = {"schema": REPORT_SCHEMA, "store_root": str(root), "as_of": as_of,
                              "receipt_dirs": [], "receipts_listed": 0, "receipts_known": 0,
                              "receipts_memo_refused": 0, "receipts_read": 0,
                              "rows_projected": 0, "refusals": [], "new_claims": 0,
                              "rescoped": 0, "already_present": 0, "frames_appended": 0,
                              "dry_run": dry_run}
    dirs = _receipt_dirs(root)
    report["receipt_dirs"] = [str(d) for d in dirs]
    listed: list[Path] = []
    for directory in dirs:
        with os.scandir(directory) as entries:
            listed.extend(Path(e.path) for e in entries
                          if _RECEIPT_NAME.fullmatch(e.name) and e.is_file(follow_symlinks=False))
    listed.sort()
    report["receipts_listed"] = len(listed)
    if not listed:
        report["seconds"] = round(time.monotonic() - started, 3)
        return report

    known = _ledger_capture_ids(frames if frames is not None
                                else (r.frame for r in led.read_all()))
    incoming: list[dict] = []
    for path in listed:
        capture = path.stem
        if capture in known:
            report["receipts_known"] += 1
            continue
        stat = path.stat()
        memo_key = str(path)
        if refused_memo.get(memo_key, {}).get("stat") == [stat.st_size, stat.st_mtime_ns]:
            report["receipts_memo_refused"] += 1
            continue
        report["receipts_read"] += 1
        try:
            raw = path.read_bytes()
            document = json.loads(raw)
            digest = hashlib.sha256(raw).hexdigest()
            if document.get("schema") != serving.RECEIPT_SCHEMA:
                raise ProjectionError("not a legacy serving receipt")
            natives = corpus.rows_for_document(path, document, digest)
            for native in natives:
                tup = corpus._carry_verification(serving.project(native), native, digest)
                incoming.extend(to_frames(tup, as_of=as_of, adapter_id=serving.ADAPTER_ID,
                                          authority=getattr(serving, "AUTHORITY", None)))
                report["rows_projected"] += 1
        except (ProjectionError, OSError, ValueError) as exc:
            reason = f"{type(exc).__name__}: {exc}"[:300]
            report["refusals"].append({"receipt": str(path), "reason": reason})
            refused_memo[memo_key] = {"stat": [stat.st_size, stat.st_mtime_ns], "reason": reason}
    if incoming:
        result = append_scoped(led, incoming, as_of=as_of, dry_run=dry_run)
        for key in ("new_claims", "rescoped", "already_present"):
            report[key] = result[key]
        report["frames_appended"] = 0 if dry_run else result["frames"]
        report["filter_refused"] = result["refused"][:20]
    if not dry_run:
        _write_memo(memo, refused_memo)
    report["seconds"] = round(time.monotonic() - started, 3)
    return report


__all__ = ["Collector", "append_scoped", "ingest_scoped_store", "scope_aware_frames"]
