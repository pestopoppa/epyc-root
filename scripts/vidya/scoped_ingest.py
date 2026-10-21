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

   Loop-belief redesign Phase 1 extends the same entry point, per store (`_store_dirs`):
     * P1-B: each receipt also yields ONE capture-level v2 claim (`legacy-serving-v2:<capture>`,
       value-bearing) beside its two v1 arm claims; a capture with v1 but no v2 is reopened once;
     * P1-D: `serving-floor.*.json` (one glob) -> `autokernel_serving_floor`, scoped by the
       store manifest (`adapters/_ak_store_manifest.py`) when the recipe matches;
     * P1-C: `experiments.db` -> lane C's `autokernel_experiments` (ImportError-guarded),
       incrementally above a per-db rowid watermark kept in the memo, with the store manifest
       built once per store and cached there too; `experiments_full=True` is the backfill.

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


def _read_memo_body(path: Path | None) -> dict:
    """The whole memo: `refused` receipts/floors, per-db experiments `watermarks`, and cached
    per-store experiment `manifests`. Missing keys (an older memo) read as empty."""
    if path is None:
        return {}
    try:
        body = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return body if isinstance(body, dict) and body.get("schema") == MEMO_SCHEMA else {}


def _read_memo(path: Path | None) -> dict:
    return dict(_read_memo_body(path).get("refused") or {})


def _write_memo(path: Path | None, refused: Mapping[str, Any], *,
                watermarks: Mapping[str, Any] | None = None,
                manifests: Mapping[str, Any] | None = None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    body: dict[str, Any] = {"schema": MEMO_SCHEMA, "refused": dict(refused)}
    if watermarks:
        body["watermarks"] = dict(watermarks)
    if manifests:
        body["manifests"] = dict(manifests)
    tmp.write_text(json.dumps(body, sort_keys=True))
    os.replace(tmp, path)


V2_SOURCE_PREFIX = "src_legacy-serving-v2:"


def _ledger_capture_ids(frames: Iterable[Mapping[str, Any]]) -> set[str]:
    """Captures whose every arm's LAST source observation already carries a scope, AND whose
    capture-level v2 claim (§5.1) is already in the ledger.

    A capture ingested before VB-LOOP-SCOPE (no applicability) is NOT known: it is reopened so
    the filter can emit its one re-observation frame. A capture ingested before P1-B (v1 arms
    only) is NOT known either: it is reopened once so its v2 claim is added beside the v1 arms.
    """
    scoped: dict[str, dict[str, bool]] = {}
    has_v2: set[str] = set()
    for frame in frames:
        if frame.get("frame_type") == FT_SOURCE:
            assertion = frame.get("assertion") or {}
            sid = str(assertion.get("source_id") or "")
            if sid.startswith("src_legacy-serving:") and sid.count(":") == 2:
                _, capture, arm = sid.split(":")
                scoped.setdefault(capture, {})[arm] = bool(assertion.get("applicability"))
            elif sid.startswith(V2_SOURCE_PREFIX):
                has_v2.add(sid[len(V2_SOURCE_PREFIX):])
    return {capture for capture, arms in scoped.items()
            if arms and all(arms.values()) and capture in has_v2}


def _ledger_source_ids(frames: Iterable[Mapping[str, Any]], prefix: str) -> set[str]:
    return {str((f.get("assertion") or {}).get("source_id"))
            for f in frames if f.get("frame_type") == FT_SOURCE
            and str((f.get("assertion") or {}).get("source_id") or "").startswith(prefix)}


def _store_dirs(store_root: Path) -> list[Path]:
    """Loop stores under `store_root`: itself when it is one, else its direct children that are.

    A store is a directory holding `experiments.db`, `serving-beliefs/` or a serving floor. One
    level, never a walk -- the same discipline as `_receipt_dirs`.
    """
    def is_store(path: Path) -> bool:
        return ((path / EXPERIMENTS_DB).is_file() or (path / RECEIPT_DIR).is_dir()
                or any(path.glob("serving-floor.*.json")))

    if is_store(store_root):
        return [store_root]
    try:
        children = sorted(p for p in store_root.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return []
    return [p for p in children if is_store(p)]


# ------------------------------------------------------------------------------ experiments
#
# Lane C's `adapters/autokernel_experiments.py` (P1-C) projects `<store>/experiments.db` rows.
# Planning time reads it INCREMENTALLY: one read-only SQLite query per store for the rows above a
# per-db rowid high-water mark kept in the memo (§5.2: the DS41 db is 4.3 GB with payloads up to
# ~6 MB, so a full read is a backfill operation, never a planning-step one). The store manifest
# the refusal rows are scoped by is built once per store and cached in the same memo.
#
# Watermark rules (per `<store>/experiments.db`):
#   * present                         -> rows with rowid > watermark;
#   * absent, `experiments_full=True` -> every row (the backfill);
#   * absent, db <= _FULL_READ_BYTES  -> every row (a young store: cheap, and complete);
#   * absent, larger db               -> nothing projected, the watermark is set to the current
#                                        max(rowid): history is the backfill's job (P1-F), and
#                                        from this step on every new row is ingested.
# The watermark advances to the max(rowid) read BEFORE the adapter's query, so a row inserted
# concurrently is re-read next time (and deduplicated by the filter), never skipped.

EXPERIMENTS_DB = "experiments.db"
_FULL_READ_BYTES = 256 << 20


def _experiments_adapter():
    """Lane C's adapter, or None before it lands (this branch must work without it)."""
    try:
        from adapters import autokernel_experiments as exp  # noqa: PLC0415
    except ImportError:
        return None
    if not (callable(getattr(exp, "native_rows", None)) and callable(getattr(exp, "project", None))):
        return None
    return exp


def _max_rowid(db: Path) -> int:
    import sqlite3  # noqa: PLC0415

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5.0)
    try:
        row = conn.execute("SELECT max(rowid) FROM experiments").fetchone()
    finally:
        conn.close()
    return int(row[0] or 0)


def _store_manifest(exp: Any, store: Path, cache: dict, report: dict) -> dict:
    """THE store manifest, built at most once per store per memo: the floor and experiments paths
    share this one cache (keyed by store path, invalidated when the experiments adapter id
    changes), so a planning step never runs `_ak_store_manifest.resolve` -- whose second strategy
    is a `LIKE` over `experiments.db` payloads -- twice, or again on the next step."""
    key = str(store)
    entry = cache.get(key)
    adapter_id = str(getattr(exp, "ADAPTER_ID", ""))
    if isinstance(entry, dict) and entry.get("adapter") == adapter_id \
            and isinstance(entry.get("manifest"), dict):
        return entry["manifest"]
    builder = getattr(exp, "build_store_manifest", None)
    if not callable(builder):
        from adapters import _ak_store_manifest as owner  # noqa: PLC0415
        builder = owner.resolve
    manifest = dict(builder(store))
    try:
        json.dumps(manifest, sort_keys=True)
    except (TypeError, ValueError):
        report["experiments_notes"].append(f"{store}: manifest not JSON; not cached")
        return manifest
    cache[key] = {"adapter": adapter_id, "manifest": manifest}
    report["experiments_manifests_built"] += 1
    return manifest


def _experiment_frames(exp: Any, store: Path, *, as_of: str, watermarks: dict,
                       manifests: dict, full: bool, report: dict) -> list[dict]:
    from claim_tuple import ProjectionError, to_frames  # noqa: PLC0415

    db = store / EXPERIMENTS_DB
    key = str(db)
    since = watermarks.get(key)
    since = since if type(since) is int and since >= 0 else None
    high = _max_rowid(db)
    if since is None and not full and db.stat().st_size > _FULL_READ_BYTES:
        watermarks[key] = high
        report["experiments_deferred"].append(
            {"db": key, "watermark": high,
             "reason": "no watermark and the db is too large for a planning-step full read; "
                       "history is the backfill's job, new rows are ingested from here"})
        return []
    if since is not None and since >= high:
        return []
    manifest = _store_manifest(exp, store, manifests, report)
    rows = exp.native_rows(store, since_rowid=since)
    report["experiments_rows_read"] += len(rows)
    out: list[dict] = []
    authority = getattr(exp, "AUTHORITY", "measurement")
    adapter_id = getattr(exp, "ADAPTER_ID", "vidya.adapters.autokernel_experiments/v1")
    for row in rows:
        try:
            tup = exp.project(row, store_manifest=manifest)
            if tup is None:
                continue
            out.extend(to_frames(tup, as_of=as_of, adapter_id=adapter_id,
                                 authority=authority))
            report["experiments_projected"] += 1
        except (ProjectionError, ValueError, KeyError, TypeError) as exc:
            ident = row.get("attempt_id") if isinstance(row, Mapping) else None
            report["refusals"].append({"experiment": f"{key}#{ident}",
                                       "reason": f"{type(exc).__name__}: {exc}"[:300]})
    watermarks[key] = high
    return out


# ------------------------------------------------------------------------------ floors


def _floor_frames(store: Path, *, as_of: str, known: set[str], refused_memo: dict,
                  report: dict, manifest_for: Any) -> list[dict]:
    """`manifest_for()` is the shared, memo-cached store manifest (`_store_manifest`)."""
    from adapters import autokernel_serving_floor as floor  # noqa: PLC0415
    from claim_tuple import ProjectionError, to_frames  # noqa: PLC0415

    paths = floor.floor_paths(store)
    report["floors_listed"] += len(paths)
    if not paths:
        return []
    manifest = manifest_for()
    out: list[dict] = []
    for path in paths:
        stat = path.stat()
        memo_key = str(path)
        if refused_memo.get(memo_key, {}).get("stat") == [stat.st_size, stat.st_mtime_ns]:
            report["floors_memo_refused"] += 1
            continue
        try:
            document, digest = floor.read_floor(path)
            natives = floor.native_rows(document, locator=f"{floor.LOCATOR_PREFIX}{path}",
                                        sha256=digest, store_manifest=manifest)
            for native in natives:
                tup = floor.project(native)
                if f"src_{tup.measurement_id}" in known:
                    report["floors_known"] += 1
                    continue
                out.extend(to_frames(tup, as_of=as_of, adapter_id=floor.ADAPTER_ID,
                                     authority=floor.AUTHORITY))
                report["floors_projected"] += 1
        except (ProjectionError, OSError, ValueError) as exc:
            reason = f"{type(exc).__name__}: {exc}"[:300]
            report["refusals"].append({"floor": str(path), "reason": reason})
            refused_memo[memo_key] = {"stat": [stat.st_size, stat.st_mtime_ns], "reason": reason}
    return out


def ingest_scoped_store(ledger: Ledger | str | Path, store_root: str | Path, *, as_of: str,
                        dry_run: bool = False, memo_path: str | Path | None = None,
                        frames: list[Mapping[str, Any]] | None = None,
                        experiments_full: bool = False) -> dict:
    """Ingest the loop beliefs of ONE loop store (or a campaign's stores).

    Per store: the serving A/B receipts (v1 arm claims AND, since P1-B, one v2 capture claim
    each), the serving floors (P1-D), and -- when lane C's adapter is present -- the
    `experiments.db` rows above the memo watermark (P1-C; `experiments_full=True` is the
    backfill). Idempotent: a capture whose v1 and v2 sources are already in the ledger is not
    reopened, a known floor is not re-emitted, and a re-run appends nothing. `frames` (the
    ledger's frames the caller already read) skips one ledger read on the fast path. Returns a
    report; raises only on an invalid ledger.
    """
    from adapters import autokernel_corpus as corpus  # noqa: PLC0415
    from adapters import autokernel_legacy_serving as serving  # noqa: PLC0415
    from adapters import autokernel_serving_floor as floor  # noqa: PLC0415
    from claim_tuple import ProjectionError, to_frames  # noqa: PLC0415

    started = time.monotonic()
    led = ledger if isinstance(ledger, Ledger) else Ledger(Path(ledger))
    root = Path(store_root)
    memo = Path(memo_path) if memo_path else None
    memo_body = _read_memo_body(memo)
    refused_memo = dict(memo_body.get("refused") or {})
    watermarks = dict(memo_body.get("watermarks") or {})
    manifests = dict(memo_body.get("manifests") or {})
    report: dict[str, Any] = {"schema": REPORT_SCHEMA, "store_root": str(root), "as_of": as_of,
                              "receipt_dirs": [], "receipts_listed": 0, "receipts_known": 0,
                              "receipts_memo_refused": 0, "receipts_read": 0,
                              "rows_projected": 0, "v2_projected": 0, "refusals": [],
                              "floors_listed": 0, "floors_known": 0, "floors_memo_refused": 0,
                              "floors_projected": 0, "experiments_adapter": False,
                              "experiments_rows_read": 0, "experiments_projected": 0,
                              "experiments_manifests_built": 0, "experiments_deferred": [],
                              "experiments_notes": [], "new_claims": 0,
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
    stores = _store_dirs(root)
    exp = _experiments_adapter()
    report["experiments_adapter"] = exp is not None
    has_floors = any(floor.floor_paths(store) for store in stores)
    has_experiments = exp is not None and any((s / EXPERIMENTS_DB).is_file() for s in stores)
    if not listed and not has_floors and not has_experiments:
        report["seconds"] = round(time.monotonic() - started, 3)
        return report

    ledger_frames = list(frames if frames is not None else (r.frame for r in led.read_all()))
    known = _ledger_capture_ids(ledger_frames)
    incoming: list[dict] = []
    for store in stores:
        incoming.extend(_floor_frames(
            store, as_of=as_of, refused_memo=refused_memo, report=report,
            known=_ledger_source_ids(ledger_frames, f"src_{floor.MEASUREMENT_PREFIX}"),
            manifest_for=lambda store=store: _store_manifest(exp, store, manifests, report)))
        if exp is not None and (store / EXPERIMENTS_DB).is_file():
            try:
                incoming.extend(_experiment_frames(
                    exp, store, as_of=as_of, watermarks=watermarks, manifests=manifests,
                    full=experiments_full, report=report))
            except Exception as exc:  # noqa: BLE001 - one store's db fault is reported, not fatal
                report["refusals"].append({"experiments": str(store / EXPERIMENTS_DB),
                                           "reason": f"{type(exc).__name__}: {exc}"[:300]})
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
            continue
        # P1-B: the capture-level v2 claim, emitted BESIDE the v1 arms (never instead of them;
        # the reader dedupes by the shared receipt locator). Its own try: a v2 refusal must not
        # cost the v1 arms. The receipt is then memo'd so it is not re-read every planning step;
        # its v1 arms are appended by this same run, so nothing is lost by skipping it later.
        try:
            for native in serving.native_rows_v2(document, receipt_locator=f"autokernel:{path}",
                                                 receipt_sha256=digest):
                tup = corpus._carry_verification(serving.project_v2(native), native, digest)
                incoming.extend(to_frames(tup, as_of=as_of, adapter_id=serving.ADAPTER_ID_V2,
                                          authority=getattr(serving, "AUTHORITY", None)))
                report["v2_projected"] += 1
        except (ProjectionError, OSError, ValueError) as exc:
            reason = f"v2 {type(exc).__name__}: {exc}"[:300]
            report["refusals"].append({"receipt": str(path), "reason": reason})
            refused_memo[memo_key] = {"stat": [stat.st_size, stat.st_mtime_ns], "reason": reason}
    if incoming:
        result = append_scoped(led, incoming, as_of=as_of, dry_run=dry_run)
        for key in ("new_claims", "rescoped", "already_present"):
            report[key] = result[key]
        report["frames_appended"] = 0 if dry_run else result["frames"]
        report["filter_refused"] = result["refused"][:20]
    if not dry_run:
        _write_memo(memo, refused_memo, watermarks=watermarks, manifests=manifests)
    report["seconds"] = round(time.monotonic() - started, 3)
    return report


__all__ = ["Collector", "append_scoped", "ingest_scoped_store", "scope_aware_frames"]
