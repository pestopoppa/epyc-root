#!/usr/bin/env python3
"""The shared belief substrate for agent loops: one reader every planning loop calls.

WHY ONE MODULE. Operator decision 2026-10-21: agent loops (AutoKernel first, AutoPilot second,
future loops after) lean on ONE belief substrate instead of each building its own reader. Each
consumer keeps only its consumer-specific half (how it names its target, where it writes its
receipt, what "already-planned work" means for it); everything that decides whether the ledger is
current, which claims apply and how they are shown lives here.

MANDATORY, NOT ADVISORY (operator correction 2026-10-21). Belief context is the reason the loops
exist to construct meaningful hypotheses, so a plan without it must be impossible:

  1. Before every planning step the consumer calls `prepare()` (or the `prepare` CLI). It checks
     the canonical ledger's freshness against its sources and, when stale, runs the incremental
     ingest itself (`sync.sync()`, the plumbing fast path), then verifies the hash chain.
  2. If the ledger cannot be made current -- missing, no sync module, ingest error, still stale
     after the ingest, chain verification failure, or any reader error -- the answer is
     `status: "refused"`. The consumer must generate NO new hypothesis/strategy, keep compute busy
     only with already-planned work, and `prepare()` has already raised the operator alarm
     (`scripts/coordination/alarm_channel.py`, key `belief-ledger-not-current.<consumer>`),
     escalated to a `critical` alarm once it has been active longer than `escalate_after_s`.
     A later `ready` answer clears both.
  3. A `ready` answer carries `ledger_state` (path, frame count, head seq + hash, as-of, freshness
     report). Every plan/decision receipt embeds it, so each decision names the exact ledger it
     was made against.

WHAT IT READS (nothing here grades). `Ledger.verify()/read_all()` -> `fold()` -> `gate.evaluate()`
under the declared `POLICY`, WITHOUT writing a `query_served` frame. Claims are matched to the
consumer's target(s) by applicability scope, never by nearness:

  * persisted scope (VB-APPLICABILITY): a `source_observed` assertion carrying `applicability`.
    The claim applies when it declares at least one of model_file/device, and EVERY dimension it
    declares among model_file (basename), quant (case-folded), backend, device, context_tokens
    equals the target's. A dimension the claim does not declare is not compared -- the producer
    declared the scope, the reader does not narrow or widen it.
  * declared scope table (`SOURCE_SCOPES`): sources written before VB-APPLICABILITY whose producer
    contract pins the whole scope (same rule the AutoKernel reader used since 2026-09-25).

Matched claims are sorted into three decision-relevant buckets, each from fold/gate output only:

  * usable     -- gate ALLOW at the floor; the newest complete run per source. Reuse candidates.
  * contested  -- gate refused for conflict/review/correction (evidence opposes, unadjudicated
                  correction, dependency alert). A contradiction the planner must not build on.
  * withdrawn  -- support retracted. A previously believed result that no longer stands.

Stdlib + ROOT `scripts/vidya` modules only; consumers in other repos run this file as a child
process (`python3 loop_beliefs.py prepare ...`) so a slow ledger is killed at their deadline.
Exit code: 0 ready, 3 refused, 2 usage error. stdout is exactly one JSON object.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import inspect
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any, Callable, Iterable, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from fold import fold  # noqa: E402
from gate import Outcome, UsePolicy, evaluate  # noqa: E402
from lattice import parse_grade  # noqa: E402
from ledger import Ledger  # noqa: E402

SCHEMA = "epyc.vidya.loop_beliefs.v1"
LEDGER_STATE_SCHEMA = "epyc.vidya.ledger_state.v1"
#: The plumbing fix's canonical ledger (scripts/vidya/ledger_home.py). Used when ledger_home is
#: not importable (plumbing not merged); never a per-worktree `.vidya/ledger.jsonl` copy, which
#: lacks every measurement frame.
CANONICAL_LEDGER = Path("/mnt/raid0/llm/state/vidya/ledger.jsonl")
ALARM_MODULE = REPO_ROOT / "scripts" / "coordination" / "alarm_channel.py"
ALARM_KEY = "belief-ledger-not-current"
ESCALATED_KEY = "belief-ledger-not-current-escalated"
DEFAULT_ESCALATE_AFTER_S = 3600.0
EXIT_READY, EXIT_USAGE, EXIT_REFUSED = 0, 2, 3

SECTION_HEADER = "## Belief-kernel evidence (Vidya ledger, read-only)"
DEFAULT_MAX_CLAIMS = 12
DEFAULT_MAX_BYTES = 10000
CLAIM_TEXT_CAP = 440
REASON_CAP = 200
FLAGGED_CAP = 8
OMITTED_CAP = 24
#: The declared use policy. Floor `Judged/Located`: the lowest grade at which a claim names where
#: it came from; an observation is shown AS an observation (its grade printed beside it).
POLICY = {"use": "planner-context", "floor": "Judged/Located", "standard": "DV"}
DEVICE_BY_BACKEND = {"gpu": "gfx90a", "cpu": "epyc-9655"}
_MATCH_KEYS = ("model_file", "quant", "backend", "device", "context_tokens")
#: Gate reasons that mean "the evidence disagrees or is under review", not merely "too weak".
_CONTESTED_MARKERS = ("conflict", "oppos", "correction", "review", "dependency")

REFUSAL_REASONS = ("ledger_missing", "sync_unavailable", "ingest_failed", "still_stale",
                   "chain_broken", "reader_error")


class LedgerNotCurrent(Exception):
    """The ledger cannot be made current; planning must not proceed."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail[:500]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _cap(text: Any, limit: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    head = (limit * 2) // 3
    return f"{text[:head]} ... {text[-(limit - head - 5):]}"


def _load_file_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------ ledger + freshness


def resolve_ledger(explicit: str | Path | None = None) -> Path:
    """`explicit` > ledger_home's default (VIDYA_LEDGER / VIDYA_STATE_DIR / canonical) > the
    canonical constant. Path overrides only; no switch here turns belief context off."""
    if explicit:
        return Path(explicit)
    if (HERE / "ledger_home.py").is_file():
        try:
            return Path(_load_file_module("ledger_home", HERE / "ledger_home.py")
                        .default_ledger_path(REPO_ROOT))
        except Exception:  # noqa: BLE001 -- fall through to the constant
            pass
    return CANONICAL_LEDGER


def load_sync():
    """ROOT's plumbing sync module (`sync.status` / `sync.sync`); LedgerNotCurrent when absent.
    Without it freshness cannot be established, and an unknown-freshness ledger is not current."""
    path = HERE / "sync.py"
    if not path.is_file():
        raise LedgerNotCurrent("sync_unavailable",
                               f"{path} absent (plumbing branch f8/vidya-plumbing not merged?)")
    try:
        return _load_file_module("vidya_sync", path)
    except Exception as exc:  # noqa: BLE001
        raise LedgerNotCurrent("sync_unavailable", f"{type(exc).__name__}: {exc}") from exc


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _ingest_sources(ledger_path: Path, source_roots: Iterable[str | Path], *,
                    memo_dir: Path | None, scoped_module: Any = None) -> list[dict[str, Any]]:
    """Producer-time ingest of the consumer's own stores (VB-LOOP-SCOPE): new AutoKernel serving
    A/B receipts are projected (with their native applicability) before the plan is made, so the
    loop's latest outcomes are beliefs at its next planning step. Idempotent; LedgerNotCurrent
    on any failure, because an un-ingested source means the ledger is not current."""
    roots = [Path(r) for r in source_roots]
    if not roots:
        return []
    if scoped_module is None:
        path = HERE / "scoped_ingest.py"
        if not path.is_file():
            raise LedgerNotCurrent("ingest_failed", f"{path} absent (VB-LOOP-SCOPE not landed)")
        try:
            scoped_module = _load_file_module("vidya_scoped_ingest", path)
        except Exception as exc:  # noqa: BLE001
            raise LedgerNotCurrent("ingest_failed", f"{type(exc).__name__}: {exc}") from exc
    reports = []
    for root in roots:
        memo = None
        if memo_dir is not None:
            memo = memo_dir / ("memo-" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
                               + ".json")
        try:
            report = dict(scoped_module.ingest_scoped_store(
                ledger_path, root, as_of=_now(), memo_path=memo))
        except Exception as exc:  # noqa: BLE001
            raise LedgerNotCurrent("ingest_failed",
                                   f"source {root}: {type(exc).__name__}: {exc}") from exc
        reports.append({k: report.get(k) for k in (
            "store_root", "receipts_listed", "receipts_read", "new_claims", "rescoped",
            "frames_appended", "seconds")} | {"refusals": len(report.get("refusals") or [])})
    return reports


def ensure_current(ledger_path: str | Path, *, index_path: str | Path | None = None,
                   sync_module: Any = None, source_roots: Iterable[str | Path] = (),
                   source_memo_dir: str | Path | None = None, scoped_module: Any = None,
                   ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Make the ledger current (incremental ingest when stale), verify it, and return
    (ledger_state, frames). Raises LedgerNotCurrent with a reason in REFUSAL_REASONS."""
    ledger_path = Path(ledger_path)
    # Default source is the plumbing's merged truth (origin/main:research/intake_index.yaml,
    # fetched once per check); an explicit index path reads that file (tests, previews).
    index_arg = Path(index_path) if index_path else None
    if not ledger_path.is_file():
        raise LedgerNotCurrent("ledger_missing", str(ledger_path))
    sync_mod = sync_module if sync_module is not None else load_sync()

    def call(fn, fetch: bool):
        try:
            accepts_fetch = "fetch" in inspect.signature(fn).parameters
        except (TypeError, ValueError):
            accepts_fetch = False
        return dict(fn(ledger_path, index_arg, **({"fetch": fetch} if accepts_fetch else {})))

    try:
        before = call(sync_mod.status, True)
    except Exception as exc:  # noqa: BLE001
        raise LedgerNotCurrent("ingest_failed", f"status: {type(exc).__name__}: {exc}") from exc
    report: dict[str, Any] = {"action": "already-fresh", "frames_emitted": 0}
    if not before.get("fresh"):
        try:
            report = call(sync_mod.sync, False)
        except Exception as exc:  # noqa: BLE001
            raise LedgerNotCurrent("ingest_failed", f"{type(exc).__name__}: {exc}") from exc
        try:
            after = call(sync_mod.status, False)
        except Exception as exc:  # noqa: BLE001
            raise LedgerNotCurrent("ingest_failed", f"status: {type(exc).__name__}: {exc}") from exc
        if not after.get("fresh"):
            raise LedgerNotCurrent("still_stale",
                                   f"after ingest ({report.get('action')}): lag "
                                   f"{after.get('lag_entries')} entries")
    else:
        after = before
    source_reports = _ingest_sources(
        ledger_path, source_roots, scoped_module=scoped_module,
        memo_dir=Path(source_memo_dir) if source_memo_dir else ledger_path.parent / "loop-memo")
    ledger = Ledger(ledger_path)
    try:
        errors = ledger.verify()
    except Exception as exc:  # noqa: BLE001
        raise LedgerNotCurrent("chain_broken", f"{type(exc).__name__}: {exc}") from exc
    if errors:
        raise LedgerNotCurrent("chain_broken", str(errors[0]))
    try:
        records = ledger.read_all()
    except Exception as exc:  # noqa: BLE001
        raise LedgerNotCurrent("chain_broken", f"{type(exc).__name__}: {exc}") from exc
    head = records[-1] if records else None
    state = {
        "schema": LEDGER_STATE_SCHEMA,
        "ledger_path": str(ledger_path),
        "frame_count": len(records),
        "head_seq": head.seq if head else None,
        "head_hash": head.frame_hash if head else None,
        "verified_at": _now(),
        "fresh": True,
        "freshness": {
            "index_source": str(after.get("index") or index_arg or "origin/main"),
            "index_sha256": after.get("index_sha256") or (
                _sha256_file(index_arg) if index_arg else None),
            "index_max_id": after.get("index_max_id"), "synced_max_id": after.get("synced_max_id"),
            "last_sync": after.get("last_sync"), "was_fresh": bool(before.get("fresh")),
            "sync_action": report.get("action"),
            "frames_emitted": int(report.get("frames_emitted") or 0),
            "sync_seconds": report.get("seconds"),
            "sources": source_reports,
        },
    }
    return state, [record.frame for record in records]


def state_digest(state: Mapping[str, Any]) -> str:
    """Short identity of the ledger state a decision was made against (for logs and rows)."""
    body = {k: state.get(k) for k in ("ledger_path", "frame_count", "head_seq", "head_hash")}
    return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


# ------------------------------------------------------------------------------ targets + scopes


@dataclass(frozen=True)
class Target:
    """What a planning step is about. Every field compared is compared exactly."""

    model_file: str
    quant: str
    backend: str
    device: str
    context_tokens: int | None = None
    label: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "Target":
        """`model_file`, or `model_path` reduced to its basename. An incomplete target raises:
        it is not a wildcard. `device` defaults from the backend on this host."""
        model = str(raw.get("model_file") or "").strip()
        if not model and raw.get("model_path"):
            model = PurePath(str(raw["model_path"])).name
        backend = str(raw.get("backend") or "").strip().lower()
        device = str(raw.get("device") or DEVICE_BY_BACKEND.get(backend, "")).strip().lower()
        values = {"model_file": PurePath(model).name if model else "",
                  "quant": str(raw.get("quant") or "").strip(), "backend": backend,
                  "device": device}
        # quant may be unknown to the caller (a split GGUF regime names none): the GGUF basename
        # already pins one file and so one quant mix; quant is compared only when both declare it.
        missing = sorted(key for key, value in values.items() if not value and key != "quant")
        if missing:
            raise ValueError(f"target incomplete: missing {missing}")
        if backend not in DEVICE_BY_BACKEND:
            raise ValueError(f"backend must be cpu or gpu (got {backend!r})")
        depth = raw.get("context_tokens")
        if depth is not None and (not isinstance(depth, int) or isinstance(depth, bool)
                                  or depth < 1):
            raise ValueError("context_tokens must be a positive integer when given")
        return cls(context_tokens=depth, label=str(raw.get("label") or ""), **values)

    def as_dict(self) -> dict[str, Any]:
        return {"model_file": self.model_file, "quant": self.quant, "backend": self.backend,
                "device": self.device, "context_tokens": self.context_tokens,
                "label": self.label}


def applicability_matches(scope: Mapping[str, Any], target: Target) -> bool:
    """Persisted-scope rule (see module doc): declares model_file or device, and every declared
    dimension equals the target's."""
    if not isinstance(scope, Mapping) or not (scope.get("model_file") or scope.get("device")):
        return False
    for key in _MATCH_KEYS:
        if key not in scope or scope[key] in (None, ""):
            continue
        value = scope[key]
        if key == "model_file":
            if PurePath(str(value)).name != target.model_file:
                return False
        elif key == "quant":
            if target.quant and str(value).upper() != target.quant.upper():
                return False
        elif key == "context_tokens":
            if target.context_tokens is not None and value != target.context_tokens:
                return False
        elif str(value).strip().lower() != getattr(target, key):
            return False
    return True


@dataclass(frozen=True)
class SourceScope:
    """A pre-VB-APPLICABILITY source whose producer contract pins its whole scope."""

    source_kind: str
    model_file: str
    quant: str
    backend: str
    device: str
    basis: str
    limits: str
    locator_re: re.Pattern[str] | None = None
    key_groups: tuple[str, ...] = ()
    expected_keys: frozenset[tuple[str, ...]] = frozenset()
    depth_tokens: Mapping[str, int] = field(default_factory=dict)

    def applies_to(self, target: Target) -> bool:
        return (target.model_file == self.model_file
                and (not target.quant or target.quant.upper() == self.quant.upper())
                and target.backend == self.backend and target.device == self.device)

    def parse(self, locator: str) -> tuple[str | None, tuple[str, ...] | None, int | None]:
        if self.locator_re is None:
            return None, None, None
        match = self.locator_re.match(locator)
        if match is None:
            return None, None, None
        groups = match.groupdict()
        key = tuple(groups.get(name) or "" for name in self.key_groups) or None
        return groups.get("run"), key, self.depth_tokens.get(groups.get("depth") or "")


_KVQ_ARMS = ("A_f16_kv", "B_q8_0_kv", "C_q4_0_kv")
_KVQ_DEPTHS = ("d2k", "d32k")
_KVQ_METRICS = ("gpu_decode_tps", "gpu_prefill_tps")

SOURCE_SCOPES: dict[str, SourceScope] = {scope.source_kind: scope for scope in (
    SourceScope(
        source_kind="kv-quant-27b-v10-measurement",
        model_file="Qwen3.8-27B-Q8_0.gguf", quant="Q8_0", backend="gpu", device="gfx90a",
        basis=("producer scripts/benchmark/kv_quant_27b_v10_sweep.py refuses any model other "
               "than /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf at its pinned byte length "
               "(model_identity_valid) and runs on MI210 device mi210_0; ROOT adapter "
               "kv_quant_27b_v10.py pins the producer bytes by sha256 and calls validate_row()"),
        limits=("llama-bench instrument, bursty duty cycle (not a serving rate); "
                "production-consolidated-v10 kernel; -fa on in every arm; K and V cache types "
                "equal per arm (f16, q8_0, q4_0), mixed K/V not measured; prefill depth is part "
                "of each claim's key"),
        locator_re=re.compile(r"^kvq:(?P<run>[^:|]+):(?P<arm>[^:|]+):(?P<depth>[^:|]+):"
                              r"(?P<metric>[^:|]+)(?:\||$)"),
        key_groups=("arm", "depth", "metric"),
        expected_keys=frozenset((a, d, m) for a in _KVQ_ARMS for d in _KVQ_DEPTHS
                                for m in _KVQ_METRICS),
        depth_tokens={"d2k": 2048, "d32k": 32768}),
)}


# ------------------------------------------------------------------------------ evidence


def _policy() -> UsePolicy:
    return UsePolicy(use=POLICY["use"], floor=parse_grade(POLICY["floor"]),
                     standard=POLICY["standard"])


def _omit(source_kind: str, reason: str, *, run: str | None = None,
          claim_id: str | None = None, detail: str = "") -> dict[str, Any]:
    return {"source_kind": source_kind, "run": run, "claim_id": claim_id, "reason": reason,
            "detail": _cap(detail, REASON_CAP) if detail else ""}


def _bucket(belief: Any, verdict: Any) -> str:
    """contested | withdrawn | weak, for a claim the gate did not ALLOW. Fold/gate output only."""
    if belief is not None and getattr(belief, "retracted_support", None) \
            and not getattr(belief, "pro_witnesses", None):
        return "withdrawn"
    text = " ".join(str(r) for r in (getattr(verdict, "reasons", None) or [])).lower()
    if belief is not None and (getattr(belief, "con_witnesses", None)
                               or getattr(belief, "corrections", None)
                               or getattr(belief, "dependency_alerts", None)):
        return "contested"
    if any(marker in text for marker in _CONTESTED_MARKERS):
        return "contested"
    return "weak"


def visible_frames(frames: list[Mapping[str, Any]], as_of: str) -> list[Mapping[str, Any]]:
    cutoff = _ts(as_of)
    return [f for f in frames if not (f.get("pubinfo") or {}).get("created_at")
            or _ts(f["pubinfo"]["created_at"]) <= cutoff]


def evaluate_frames(frames: list[Mapping[str, Any]], targets: Iterable[Target], *, as_of: str,
                    max_claims: int = DEFAULT_MAX_CLAIMS, max_bytes: int = DEFAULT_MAX_BYTES,
                    fold_result: Any = None, reply_field: str = "relies_on_claims",
                    ) -> dict[str, Any]:
    """The evidence half of a `ready` answer, from frames already verified."""
    targets = list(targets)
    visible = visible_frames(frames, as_of)
    result = fold_result if fold_result is not None else fold(visible, as_of=as_of)
    policy = _policy()
    sources: dict[str, Mapping[str, Any]] = {}
    claims: dict[str, Mapping[str, Any]] = {}
    support: dict[str, Mapping[str, Any]] = {}
    reasons: dict[str, tuple[str, ...]] = {}
    for frame in visible:
        kind, assertion = str(frame.get("frame_type", "")), frame.get("assertion") or {}
        if kind.endswith("source_observed/v1"):
            sources[str(assertion.get("source_id", ""))] = assertion
        elif kind.endswith("claim_proposed/v1"):
            claims[str(assertion.get("claim_id", ""))] = assertion
        elif kind.endswith("evidence_supports_claim/v1"):
            cid = str(assertion.get("claim_id", ""))
            support[cid] = assertion
            reasons[cid] = tuple(str(r) for r in
                                 (frame.get("provenance") or {}).get("grade_reasons") or ())

    omitted: list[dict[str, Any]] = []
    flagged: dict[str, list[dict[str, Any]]] = {"contested": [], "withdrawn": []}
    runs: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    expected: dict[tuple[str, str | None], frozenset] = {}
    seen: set[str] = set()
    matched_any = False
    for raw_id, claim in claims.items():
        source = sources.get(str(claim.get("source_id", "")))
        if source is None:
            continue
        kind = str(source.get("source_kind", ""))
        scope_raw = source.get("applicability")
        table = SOURCE_SCOPES.get(kind)
        hits = ([t for t in targets if applicability_matches(scope_raw, t)] if scope_raw
                else [t for t in targets if table is not None and table.applies_to(t)])
        if not hits:
            continue
        matched_any = True
        claim_id = result.alias_map.get(raw_id, raw_id)
        if claim_id in seen:
            continue
        seen.add(claim_id)
        locator = str(source.get("locator", ""))
        if scope_raw:
            run = scope_raw.get("run_id")
            run_keys = scope_raw.get("run_expected_keys")
            key = (locator.split("|", 1)[0],)
            depth = scope_raw.get("context_tokens")
            if run is not None and run_keys:
                expected[(kind, run)] = frozenset((k,) for k in run_keys)
        else:
            run, key, depth = table.parse(locator)
            if table.expected_keys:
                if run is None or key not in table.expected_keys:
                    omitted.append(_omit(kind, "incomplete_run", run=run, claim_id=claim_id,
                                         detail=f"locator {locator.split('|', 1)[0]!r} outside "
                                                "the declared run key set"))
                    continue
                expected[(kind, run)] = table.expected_keys
        verdict = evaluate(claim_id, result, policy)
        belief = result.beliefs.get(claim_id)
        row = {"claim_id": claim_id, "source_kind": kind, "run": run, "key": key,
               "context_tokens": depth,
               "grade": str(belief.pro) if belief is not None else "",
               "locator": locator.split("|", 1)[0],
               "revision": str(source.get("revision_observed", "")),
               "protocol_id": str((support.get(raw_id) or {}).get("protocol_id") or ""),
               "reps": (support.get(raw_id) or {}).get("reps"),
               "text": str(claim.get("display_text", "")),
               "grade_reasons": reasons.get(raw_id, ()),
               "targets": sorted({t.model_file for t in hits})}
        if not isinstance(row["reps"], int) or isinstance(row["reps"], bool):
            row["reps"] = None
        if verdict.outcome != Outcome.ALLOW:
            bucket = _bucket(belief, verdict)
            gate_reason = (verdict.reasons or [""])[0]
            if bucket in flagged:
                flagged[bucket].append({**row, "gate_outcome": verdict.outcome,
                                        "gate_reason": _cap(gate_reason, REASON_CAP)})
            omitted.append(_omit(kind, f"gate_refused:{verdict.outcome}", run=run,
                                 claim_id=claim_id, detail=gate_reason))
            continue
        runs.setdefault((kind, run), []).append(row)

    if not matched_any:
        return _evidence_empty("no_applicable_claims", as_of=as_of, frontier=result.frontier)

    candidates: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    by_kind: dict[str, dict[str | None, list[dict[str, Any]]]] = {}
    for (kind, run), rows in runs.items():
        by_kind.setdefault(kind, {})[run] = rows
    refused_runs = {(o["source_kind"], o["run"]) for o in omitted if o["run"]}
    for kind in sorted(set(by_kind) | {k for k, _ in refused_runs}):
        groups = by_kind.get(kind, {})
        if all(run is None for run in groups) and not any(k == kind for k, _ in refused_runs):
            candidates.extend(groups.get(None, []))
            continue
        complete, incomplete = [], []
        for run in set(groups) | {r for k, r in refused_runs if k == kind}:
            rows = groups.get(run, [])
            keys = [row["key"] for row in rows]
            need = expected.get((kind, run))
            if run is None or (need is None and rows) or (
                    need is not None and len(keys) == len(set(keys)) and set(keys) == need):
                complete.append((max((row["revision"] for row in rows), default=""), run, rows))
            else:
                incomplete.append((run, len(set(keys)), len(need or ())))
        for run, have, need in sorted(incomplete, key=lambda item: str(item[0])):
            omitted.append(_omit(kind, "incomplete_run", run=run,
                                 detail=f"{have} of {need} declared keys pass the gate"))
            run_rows.append({"source_kind": kind, "run": run, "status": "omitted",
                             "reason": "incomplete_run", "claim_ids": []})
        complete.sort(key=lambda item: (item[0], str(item[1])), reverse=True)
        newest_done = False
        for _, run, rows in complete:
            if run is None:
                candidates.extend(rows)
                continue
            if not newest_done:
                candidates.extend(rows)
                newest_done = True
                continue
            omitted.append(_omit(kind, "superseded_run", run=run, detail="newer complete run"))
            run_rows.append({"source_kind": kind, "run": run, "status": "omitted",
                             "reason": "superseded_run",
                             "claim_ids": sorted(row["claim_id"] for row in rows)})

    candidates.sort(key=lambda row: (row["source_kind"], row["locator"]))
    for bucket in flagged.values():
        bucket.sort(key=lambda row: (row["source_kind"], row["locator"]))
    section, shown, shown_flagged = render(targets, candidates, flagged,
                                           frontier=result.frontier, as_of=as_of,
                                           max_claims=max_claims, max_bytes=max_bytes,
                                           reply_field=reply_field,
                                           whole_runs=set(expected))
    shown_ids = {row["claim_id"] for row in shown}
    for row in candidates:
        if row["claim_id"] not in shown_ids:
            omitted.append(_omit(row["source_kind"], "bounded", run=row["run"],
                                 claim_id=row["claim_id"],
                                 detail=f"cap {max_claims} claims / {max_bytes} bytes"))
    presented_runs: dict[tuple[str, str | None], list[str]] = {}
    for row in shown:
        presented_runs.setdefault((row["source_kind"], row["run"]), []).append(row["claim_id"])
    run_rows = [{"source_kind": kind, "run": run, "status": "presented", "reason": "",
                 "claim_ids": sorted(ids)} for (kind, run), ids in sorted(
                     presented_runs.items(), key=lambda item: (item[0][0], str(item[0][1])))] \
        + run_rows
    flagged_ids = {b: [r["claim_id"] for r in rows] for b, rows in shown_flagged.items()}
    status = "presented" if (shown or any(flagged_ids.values())) else "omitted"
    return {
        "status": status, "reasons": sorted({o["reason"] for o in omitted}),
        "frontier": result.frontier, "as_of": as_of,
        "claim_ids": [row["claim_id"] for row in shown],
        "contested_claim_ids": flagged_ids["contested"],
        "withdrawn_claim_ids": flagged_ids["withdrawn"],
        "claims": [{k: row[k] for k in ("claim_id", "source_kind", "run", "grade", "locator")}
                   for row in shown],
        "flagged": {b: [{k: row[k] for k in ("claim_id", "source_kind", "grade", "locator",
                                             "gate_outcome", "gate_reason")} for row in rows]
                    for b, rows in shown_flagged.items()},
        "runs": run_rows, "omitted": omitted[:OMITTED_CAP], "omitted_count": len(omitted),
        "section": section,
        "section_sha256": hashlib.sha256(section.encode()).hexdigest() if section else "",
        "section_bytes": len(section.encode()),
    }


def _evidence_empty(reason: str, *, as_of: str, frontier: int | None = None,
                    error: str | None = None) -> dict[str, Any]:
    return {"status": "omitted", "reasons": [reason], "frontier": frontier, "as_of": as_of,
            "claim_ids": [], "contested_claim_ids": [], "withdrawn_claim_ids": [], "claims": [],
            "flagged": {"contested": [], "withdrawn": []}, "runs": [], "omitted": [],
            "omitted_count": 0, "section": "", "section_sha256": "", "section_bytes": 0,
            **({"error": error} if error else {})}


def render(targets: list[Target], rows: list[dict[str, Any]],
           flagged: Mapping[str, list[dict[str, Any]]], *, frontier: int | None, as_of: str,
           max_claims: int = DEFAULT_MAX_CLAIMS, max_bytes: int = DEFAULT_MAX_BYTES,
           reply_field: str = "relies_on_claims",
           whole_runs: set[tuple[str, str | None]] | None = None,
           ) -> tuple[str, list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Bounded, neutral block; ("", [], {}) when nothing fits. Contradiction/withdrawn flags are
    packed first (they are the cheap, high-value lines); usable claims fill the rest."""
    empty = {"contested": [], "withdrawn": []}
    if (not rows and not any(flagged.values())) or max_claims < 1:
        return "", [], empty
    names = "; ".join(
        f"{t.model_file} / {t.quant} / {t.backend} / {t.device}"
        + (f" / context {t.context_tokens}" if t.context_tokens else "") for t in targets)
    head = [SECTION_HEADER,
            f"Target(s): {names}.",
            "Ingested claims whose declared applicability scope equals the target. Grade is the "
            f"folded claim_tuple.grade() Q/T at ledger frontier {frontier}, as of {as_of}."]
    tail = [f"Optional reply field {reply_field}: a list of the USABLE claim ids above that "
            "the proposal depends on; omit it when it depends on none. Contested or withdrawn "
            "claims are not evidence for a proposal."]
    body: list[str] = []
    shown_flagged: dict[str, list[dict[str, Any]]] = {"contested": [], "withdrawn": []}

    def size(lines: list[str]) -> int:
        return len("\n".join(head + lines + tail).encode("utf-8")) + 120

    titles = {"contested": ("### Contested -- the evidence disagrees or is under review; "
                            "do not build on these without new evidence"),
              "withdrawn": ("### Withdrawn -- support retracted; the result no longer "
                            "stands")}
    for bucket in ("contested", "withdrawn"):
        rows_b = flagged.get(bucket) or []
        if not rows_b:
            continue
        lines = [titles[bucket]]
        for row in rows_b[:FLAGGED_CAP]:
            line = (f"- {row['claim_id']} [{row['gate_outcome']}] {row['locator']}: "
                    f"{_cap(row['text'], CLAIM_TEXT_CAP // 2)} (gate: "
                    f"{_cap(row['gate_reason'], REASON_CAP // 2)})")
            if size(body + lines + [line]) > max_bytes:
                break
            lines.append(line)
            shown_flagged[bucket].append(row)
        if shown_flagged[bucket]:
            body.extend(lines)

    shown: list[dict[str, Any]] = []
    described: set[tuple[str, str | None]] = set()

    def lines_for(row: dict[str, Any], first: bool) -> list[str]:
        lines: list[str] = []
        if first:
            scope = SOURCE_SCOPES.get(row["source_kind"])
            run = f", run {row['run']}" if row["run"] else ""
            limits = f" Limits: {scope.limits}." if scope else ""
            lines.append(f"Source {row['source_kind']}{run}.{limits}")
        facts = [f"protocol {row['protocol_id'] or 'none'}",
                 f"n={row['reps']}" if row["reps"] is not None else "n unrecorded"]
        if row["context_tokens"] is not None:
            facts.insert(0, f"context {row['context_tokens']}")
        if row["revision"]:
            facts.append(row["revision"])
        lines.append(f"- {row['claim_id']} [{row['grade']}] {row['locator']} "
                     f"({'; '.join(facts)}): {_cap(row['text'], CLAIM_TEXT_CAP)}")
        if row["grade_reasons"]:
            lines.append(f"  grade notes: {_cap(row['grade_reasons'][0], REASON_CAP)}")
        return lines

    # Packing unit: a whole run when the run declares its complete key set (a truncated matrix
    # would read as an incomplete one), else one claim. Units are interleaved round-robin across
    # source kinds so one large source cannot crowd every other source out of the cap.
    whole = whole_runs or set()
    by_kind: dict[str, list[list[dict[str, Any]]]] = {}
    for row in rows:
        kind_units = by_kind.setdefault(row["source_kind"], [])
        key = (row["source_kind"], row["run"])
        if (key in whole and kind_units
                and (kind_units[-1][0]["source_kind"], kind_units[-1][0]["run"]) == key):
            kind_units[-1].append(row)
        else:
            kind_units.append([row])
    units: list[list[dict[str, Any]]] = []
    queues = [list(by_kind[kind]) for kind in sorted(by_kind)]
    while any(queues):
        for queue in queues:
            if queue:
                units.append(queue.pop(0))
    usable_lines: list[str] = []
    for unit in units:
        if len(shown) + len(unit) > max_claims:
            continue
        lines: list[str] = []
        for index, row in enumerate(unit):
            lines.extend(lines_for(row, index == 0 and (row["source_kind"], row["run"])
                                   not in described))
        header = [] if usable_lines else ["### Usable -- gate ALLOW at the declared floor"]
        if size(body + usable_lines + header + lines) > max_bytes:
            continue
        usable_lines.extend(header + lines)
        described.update((row["source_kind"], row["run"]) for row in unit)
        shown.extend(unit)
    body.extend(usable_lines)
    if not shown and not any(shown_flagged.values()):
        return "", [], empty
    count = (f"Shown {len(shown)} of {len(rows)} usable claim(s), "
             f"{len(shown_flagged['contested'])} contested, "
             f"{len(shown_flagged['withdrawn'])} withdrawn; bounded at {max_claims} claims / "
             f"{max_bytes} bytes.")
    return "\n".join(head + body + [count] + tail), shown, shown_flagged


# ------------------------------------------------------------------------------ alarms


def _alarm_api():
    return _load_file_module("vidya_alarm_channel", ALARM_MODULE)


def raise_refusal_alarm(consumer: str, reason: str, detail: str, *,
                        escalate_after_s: float = DEFAULT_ESCALATE_AFTER_S,
                        alarm_state: str | Path | None = None,
                        alarm_config: str | Path | None = None,
                        api: Any = None) -> dict[str, Any]:
    """Raise `belief-ledger-not-current.<consumer>` (warning); once it has been active longer
    than `escalate_after_s`, also raise the `critical` escalation key. Never raises."""
    out: dict[str, Any] = {"key": f"{ALARM_KEY}.{consumer}", "raised": None, "escalated": None}
    try:
        api = api or _alarm_api()
        cfg = api.load_config(Path(alarm_config)) if alarm_config else None
        state = Path(alarm_state) if alarm_state else None
        message = (f"{consumer}: belief ledger cannot be made current ({reason}); "
                   "no new hypotheses are being generated, only already-planned work runs")
        evidence = {"consumer": consumer, "reason": reason, "detail": _cap(detail, 300)}
        with contextlib.redirect_stdout(sys.stderr):
            raised = api.raise_alarm(out["key"], "warning", message, evidence, cfg=cfg,
                                     state_file=state)
        out["raised"] = raised.get("action")
        active = raised.get("active") or {}
        since = active.get("raised_at")
        age = ((datetime.now(timezone.utc) - _ts(since)).total_seconds() if since else 0.0)
        out["active_for_s"] = round(age, 1)
        if age >= escalate_after_s:
            with contextlib.redirect_stdout(sys.stderr):
                esc = api.raise_alarm(f"{ESCALATED_KEY}.{consumer}", "critical",
                                      f"OPERATOR: {message}; unresolved for {int(age)} s",
                                      evidence, cfg=cfg, state_file=state)
            out["escalated"] = esc.get("action")
    except Exception as exc:  # noqa: BLE001 -- the refusal stands even if the alarm fails
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return out


def clear_refusal_alarm(consumer: str, *, alarm_state: str | Path | None = None,
                        alarm_config: str | Path | None = None, api: Any = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        api = api or _alarm_api()
        cfg = api.load_config(Path(alarm_config)) if alarm_config else None
        state = Path(alarm_state) if alarm_state else None
        with contextlib.redirect_stdout(sys.stderr):
            for key in (f"{ALARM_KEY}.{consumer}", f"{ESCALATED_KEY}.{consumer}"):
                out[key] = api.clear_alarm(key, cfg=cfg, state_file=state).get("action")
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return out


# ------------------------------------------------------------------------------ known-good + seeds
#
# Degraded mode (operator refinement 2026-10-21). While the ledger cannot be made current a loop
# generates NO new hypothesis, but it may run already-planned measurements AND preseeded,
# not-yet-tested hypotheses (planned earlier against a known-good ledger state, or seeded by the
# operator / a Fable architect), because those are not blind. Rules:
#   * each such work item names the ledger state it was seeded against (its receipt records it);
#   * a seed whose declared premises the LAST KNOWN-GOOD state already flags (contested or
#     withdrawn) is skipped (`check_seeds` against the snapshot `prepare` wrote at the last ready);
#   * when the ledger recovers, results produced in degraded mode are re-checked against the
#     current beliefs (`check_seeds` against the fresh snapshot) and any whose premise has since
#     been refuted is flagged for review -- never silently reversed.

KNOWN_GOOD_SCHEMA = "epyc.vidya.loop_known_good.v1"
SEED_CHECK_SCHEMA = "epyc.vidya.seed_check.v1"
DEFAULT_KNOWN_GOOD_DIR = CANONICAL_LEDGER.parent / "loop-known-good"


def known_good_path(consumer: str, explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", consumer)
    return DEFAULT_KNOWN_GOOD_DIR / f"{safe}.json"


def global_flags(result: Any) -> dict[str, list[str]]:
    """Every claim the fold currently flags, ledger-wide (not only the target's): withdrawn =
    support retracted with no live support left; contested = opposing evidence, a recorded
    correction or a dependency alert. Fold output only; no grade is computed here."""
    contested, withdrawn = [], []
    for claim_id, belief in result.beliefs.items():
        if belief.retracted_support and not belief.pro_witnesses:
            withdrawn.append(claim_id)
        elif belief.con_witnesses or belief.corrections or belief.dependency_alerts:
            contested.append(claim_id)
    return {"contested": sorted(contested), "withdrawn": sorted(withdrawn),
            "aliases": dict(sorted(result.alias_map.items()))}


def write_known_good(path: Path, consumer: str, state: Mapping[str, Any],
                     flags: Mapping[str, Any], *, frontier: int | None, as_of: str) -> None:
    body = {"schema": KNOWN_GOOD_SCHEMA, "consumer": consumer, "as_of": as_of,
            "frontier": frontier, "ledger_state": dict(state),
            "ledger_state_digest": state_digest(state), **flags}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(body, sort_keys=True))
    os.replace(tmp, path)


def read_known_good(path: Path) -> dict[str, Any] | None:
    try:
        body = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(body, dict) or body.get("schema") != KNOWN_GOOD_SCHEMA:
        return None
    return body


def check_seeds(items: Iterable[Mapping[str, Any]],
                known_good: Mapping[str, Any] | None) -> dict[str, Any]:
    """Per work item `{id, premises: [claim ids], seeded_against: ...}`. `seeded_against` is the
    ledger_state (or its digest) the item was planned against, or for an operator / Fable-architect
    seed a provenance object `{"kind": "operator"|"architect", "author": ..., "at": ...}`; either way
    it must be present and is recorded verbatim in the result.
    admissible unless a premise is contested/withdrawn in `known_good`. An item without a
    `seeded_against` is NOT admissible in degraded mode (it would be blind). With no known-good
    snapshot at all nothing is admissible: there is no non-blind basis to run a seed on."""
    rows = []
    flags = known_good or {}
    contested = set(flags.get("contested") or ())
    withdrawn = set(flags.get("withdrawn") or ())
    aliases = flags.get("aliases") or {}
    for item in items:
        item_id = str(item.get("id", ""))
        premises = [str(p) for p in (item.get("premises") or [])]
        reasons: list[str] = []
        flagged: list[dict[str, str]] = []
        if known_good is None:
            reasons.append("no_known_good_state")
        if not item.get("seeded_against"):
            reasons.append("no_seeded_against_state")
        for premise in premises:
            canon = aliases.get(premise, premise)
            if canon in withdrawn:
                flagged.append({"claim_id": premise, "status": "withdrawn"})
            elif canon in contested:
                flagged.append({"claim_id": premise, "status": "contested"})
        if flagged:
            reasons.append("premise_flagged")
        rows.append({"id": item_id, "admissible": not reasons, "reasons": reasons,
                     "flagged_premises": flagged, "premises": premises,
                     "seeded_against": item.get("seeded_against")})
    return {"schema": SEED_CHECK_SCHEMA,
            "checked_against": (known_good or {}).get("ledger_state"),
            "checked_against_digest": (known_good or {}).get("ledger_state_digest"),
            "items": rows,
            "admissible_ids": [r["id"] for r in rows if r["admissible"]],
            "flagged_ids": [r["id"] for r in rows if r["flagged_premises"]]}


# ------------------------------------------------------------------------------ prepare


def prepare(consumer: str, targets: Iterable[Mapping[str, Any]] | Mapping[str, Any], *,
            ledger: str | Path | None = None, index_path: str | Path | None = None,
            as_of: str | None = None, escalate_after_s: float = DEFAULT_ESCALATE_AFTER_S,
            alarm_state: str | Path | None = None, alarm_config: str | Path | None = None,
            max_claims: int = DEFAULT_MAX_CLAIMS, max_bytes: int = DEFAULT_MAX_BYTES,
            known_good: str | Path | None = None, reply_field: str = "relies_on_claims",
            source_roots: Iterable[str | Path] = (), source_memo_dir: str | Path | None = None,
            sync_module: Any = None, scoped_module: Any = None,
            alarm_api: Any = None) -> dict[str, Any]:
    """The one call before every planning step. Never raises.

    `ready`: ledger current + verified; `ledger_state` and `evidence` set (evidence may be empty
    when no claim applies -- that is still a plan WITH belief context). `refused`: the consumer
    must not plan; the alarm has been raised."""
    as_of = as_of or datetime.now(timezone.utc).isoformat()
    if isinstance(targets, Mapping):
        targets = [targets]
    path = resolve_ledger(ledger)
    kg_path = known_good_path(consumer, known_good)
    base = {"schema": SCHEMA, "consumer": consumer, "as_of": as_of, "ledger_path": str(path),
            "policy": dict(POLICY), "known_good_path": str(kg_path)}
    try:
        parsed: list[Target] = []
        target_errors: list[str] = []
        for raw in targets:
            try:
                parsed.append(Target.from_mapping(raw))
            except ValueError as exc:
                target_errors.append(str(exc))
        state, frames = ensure_current(path, index_path=index_path, sync_module=sync_module,
                                       source_roots=source_roots,
                                       source_memo_dir=source_memo_dir,
                                       scoped_module=scoped_module)
        result = fold(visible_frames(frames, as_of), as_of=as_of)
        if parsed:
            evidence = evaluate_frames(frames, parsed, as_of=as_of, max_claims=max_claims,
                                       max_bytes=max_bytes, fold_result=result,
                                       reply_field=reply_field)
        else:
            evidence = _evidence_empty("inapplicable_target", as_of=as_of,
                                       error="; ".join(target_errors) or "no target")
        if target_errors and parsed:
            evidence["target_errors"] = target_errors
        flags = global_flags(result)
        kg_error = None
        try:
            write_known_good(kg_path, consumer, state, flags, frontier=result.frontier,
                             as_of=as_of)
        except OSError as exc:  # the plan still has belief context; degraded mode will not
            kg_error = f"{type(exc).__name__}: {exc}"[:300]
    except LedgerNotCurrent as exc:
        alarm = raise_refusal_alarm(consumer, exc.reason, exc.detail,
                                    escalate_after_s=escalate_after_s, alarm_state=alarm_state,
                                    alarm_config=alarm_config, api=alarm_api)
        return {**base, "status": "refused", "reason": exc.reason, "detail": exc.detail,
                "ledger_state": None, "evidence": None, "alarm": alarm,
                "last_known_good": _known_good_summary(kg_path)}
    except Exception as exc:  # noqa: BLE001 -- an unexpected failure is a refusal, never a plan
        detail = f"{type(exc).__name__}: {exc}"[:500]
        alarm = raise_refusal_alarm(consumer, "reader_error", detail,
                                    escalate_after_s=escalate_after_s, alarm_state=alarm_state,
                                    alarm_config=alarm_config, api=alarm_api)
        return {**base, "status": "refused", "reason": "reader_error", "detail": detail,
                "ledger_state": None, "evidence": None, "alarm": alarm,
                "last_known_good": _known_good_summary(kg_path)}
    cleared = clear_refusal_alarm(consumer, alarm_state=alarm_state, alarm_config=alarm_config,
                                  api=alarm_api)
    return {**base, "status": "ready", "reason": None, "detail": "",
            "targets": [t.as_dict() for t in parsed], "ledger_state": state,
            "ledger_state_digest": state_digest(state), "evidence": evidence,
            "flag_counts": {k: len(flags[k]) for k in ("contested", "withdrawn")},
            "known_good_error": kg_error, "alarm": {"cleared": cleared}}


def _known_good_summary(path: Path) -> dict[str, Any] | None:
    body = read_known_good(path)
    if body is None:
        return None
    return {"path": str(path), "as_of": body.get("as_of"),
            "ledger_state": body.get("ledger_state"),
            "ledger_state_digest": body.get("ledger_state_digest")}


def validate_ready(answer: Any) -> dict[str, Any]:
    """What consumers call before using an answer to plan: a plan without a verified,
    current ledger state is impossible by construction. Raises ValueError otherwise."""
    if not isinstance(answer, Mapping) or answer.get("schema") != SCHEMA:
        raise ValueError("not a loop_beliefs answer")
    if answer.get("status") != "ready":
        raise ValueError(f"belief context refused: {answer.get('reason')}")
    state = answer.get("ledger_state")
    if (not isinstance(state, Mapping) or state.get("schema") != LEDGER_STATE_SCHEMA
            or not state.get("fresh") or not isinstance(state.get("frame_count"), int)
            or not state.get("head_hash") or not isinstance(answer.get("evidence"), Mapping)):
        raise ValueError("belief context lacks a verified ledger state")
    return dict(answer)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="make the ledger current and read the consumer's evidence")
    p.add_argument("--consumer", required=True)
    p.add_argument("--target-json", required=True, help="a target object or a list of them")
    p.add_argument("--ledger", default=None)
    p.add_argument("--index", default=None)
    p.add_argument("--as-of", default=None)
    p.add_argument("--escalate-after-s", type=float, default=DEFAULT_ESCALATE_AFTER_S)
    p.add_argument("--alarm-state", default=None)
    p.add_argument("--alarm-config", default=None)
    p.add_argument("--max-claims", type=int, default=DEFAULT_MAX_CLAIMS)
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    p.add_argument("--known-good", default=None,
                   help="known-good snapshot path (default <state>/loop-known-good/<consumer>.json)")
    p.add_argument("--source-root", action="append", default=[],
                   help="a store this consumer produces into; its new AutoKernel serving A/B "
                        "receipts are ingested before planning (repeatable)")
    p.add_argument("--source-memo-dir", default=None,
                   help="refusal memo dir for --source-root (default <ledger dir>/loop-memo)")
    p.add_argument("--reply-field", default="relies_on_claims",
                   help="the consumer's reply field for declared reliance (AutoPilot: vidya_claim_ids)")
    c = sub.add_parser("check-seeds", help="admissibility of preseeded/degraded-mode work items "
                                           "against a known-good snapshot")
    c.add_argument("--consumer", required=True)
    c.add_argument("--items-json", required=True,
                   help="list of {id, premises: [claim ids], seeded_against}")
    c.add_argument("--known-good", default=None)
    a = sub.add_parser("alarm", help="raise the refusal alarm for a consumer-side failure "
                                     "(e.g. this reader timed out)")
    a.add_argument("--consumer", required=True)
    a.add_argument("--reason", required=True)
    a.add_argument("--detail", default="")
    a.add_argument("--escalate-after-s", type=float, default=DEFAULT_ESCALATE_AFTER_S)
    a.add_argument("--alarm-state", default=None)
    a.add_argument("--alarm-config", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "alarm":
        out = raise_refusal_alarm(args.consumer, args.reason, args.detail,
                                  escalate_after_s=args.escalate_after_s,
                                  alarm_state=args.alarm_state, alarm_config=args.alarm_config)
        print(json.dumps(out, sort_keys=True))
        return EXIT_READY
    if args.cmd == "check-seeds":
        try:
            items = json.loads(args.items_json)
            if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
                raise ValueError("items must be a JSON list of objects")
        except ValueError as exc:
            print(json.dumps({"schema": SEED_CHECK_SCHEMA, "status": "usage_error",
                              "detail": str(exc)}))
            return EXIT_USAGE
        kg = read_known_good(known_good_path(args.consumer, args.known_good))
        print(json.dumps(check_seeds(items, kg), sort_keys=True, default=str))
        return EXIT_READY
    try:
        raw = json.loads(args.target_json)
        if not isinstance(raw, (dict, list)):
            raise ValueError("target must be a JSON object or list")
    except ValueError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "usage_error", "detail": str(exc)}))
        return EXIT_USAGE
    answer = prepare(args.consumer, raw, ledger=args.ledger, index_path=args.index,
                     as_of=args.as_of, escalate_after_s=args.escalate_after_s,
                     alarm_state=args.alarm_state, alarm_config=args.alarm_config,
                     max_claims=args.max_claims, max_bytes=args.max_bytes,
                     known_good=args.known_good, reply_field=args.reply_field,
                     source_roots=args.source_root, source_memo_dir=args.source_memo_dir)
    print(json.dumps(answer, sort_keys=True, default=str))
    return EXIT_READY if answer["status"] == "ready" else EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
