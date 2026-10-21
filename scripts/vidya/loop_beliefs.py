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
consumer's target(s) by applicability scope, never by nearness, into THREE TIERS that are never
mixed (belief redesign 2026-10-21, §7.1):

  * target  -- the scope names the target's weights (model_file basename, or model_sha256) and
               every other dimension it declares (quant, backend, device, context_tokens) equals
               the target's. A device-only scope never reaches this tier.
  * sibling -- a different file of the target's declared `MODEL_LINEAGE` family on the same
               backend. Rendered "measured on <file>, recipe <r>; transfer unproven"; never
               target evidence.
  * host    -- device-only scopes (e.g. INF-70 roofline): at most 3 lines, labelled "host
               ceiling, not about this model", and NOT reliance-eligible.
  * knob    -- (§12.3) a target-tier claim whose `knob_family` is one of the target's
               `knob_families` (AutoPilot role targets); ranked above plain target lines and
               sharing their budget. Lines print the claim's `varied` and fixed `knobs`.
  * lineup  -- (§12.3) a lineup target `{scope: "lineup", stack_regime}` matches only claims
               declaring the same `stack_regime`; else "No beliefs at this regime".
  The declared scope table (`SOURCE_SCOPES`) covers sources written before VB-APPLICABILITY whose
  producer contract pins the whole scope; it is tiered by the same rule.

Each matched claim gets a status from fold/gate output only:

  * verified   -- gate ALLOW at the floor; the newest complete run per source. A negative result
                  (null, regression, correctness refusal) is a verified claim with a negative
                  `observation.outcome`, a dead end the planner can trust.
  * contested  -- gate refused for conflict/review/correction. Must not be built on.
  * withdrawn  -- support retracted. A previously believed result that no longer stands.
  * refuted    -- `belief.verdict(floor)` is Opposed: opposing evidence clears the floor.

Rendering is value-bearing when the evidence frame carries the carrier's `observation` block
(value, unit, n, effect vs anchor, floor, outcome, mechanism id), ranked inside the target tier
(flagged, decisive, refusals, nulls, anchors/floors, older epochs), one line per (mechanism,
recipe), followed by a tried-mechanisms index. Frames without an observation render their text
exactly as before. v1 serving arm claims are hidden behind the v2 capture claim for the same
receipt.

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
import math
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

from fold import Verdict, fold  # noqa: E402
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
#: Section budget (belief redesign §7.3): target 16 + sibling 8 + host 3 detailed claims, an
#: 80-id tried-mechanisms index, 14 KB in all.
DEFAULT_MAX_CLAIMS = 27
DEFAULT_MAX_BYTES = 14000
#: Tiers in rank order. `knob` (belief redesign §12.3) is a target-model match whose
#: `knob_family` is one the target can change; it shares the target budget and ranks above plain
#: target lines. `lineup` matches a lineup target by `stack_regime` (AutoPilot's own trials).
TIERS = ("knob", "target", "lineup", "sibling", "host")
TIER_CAPS = {"knob": 16, "target": 16, "lineup": 8, "sibling": 8, "host": 3}
#: Tiers whose ids are planner evidence for the target (reliance-eligible); host is not.
_MODEL_TIERS = ("knob", "target")
#: AutoPilot knob families (belief redesign §12.1). A target may only name these; a claim's
#: unknown family never reaches the knob tier.
KNOB_FAMILIES = frozenset({"spec_draft", "kv_profile", "kv_compaction", "placement", "routing",
                           "orchestrator", "slot_serving"})
INDEX_CAP = 80
TRIED_JSON_CAP = 400
CLAIM_TEXT_CAP = 440
CONTEXT_TEXT_CAP = 220
STATEMENT_CAP = 140
EARLIER_CAP = 3
REASON_CAP = 200
FLAGGED_CAP = 8
OMITTED_CAP = 24
#: The declared use policy. Floor `Judged/Located`: the lowest grade at which a claim names where
#: it came from; an observation is shown AS an observation (its grade printed beside it).
POLICY = {"use": "planner-context", "floor": "Judged/Located", "standard": "DV"}
DEVICE_BY_BACKEND = {"gpu": "gfx90a", "cpu": "epyc-9655"}
#: Dimensions compared after the model identity (model_file / model_sha256) is settled.
_MATCH_KEYS = ("quant", "backend", "device", "context_tokens")
#: Gate reasons that mean "the evidence disagrees or is under review", not merely "too weak".
_CONTESTED_MARKERS = ("conflict", "oppos", "correction", "review", "dependency")
#: Flagged buckets, in render order (contested, withdrawn, then refuted).
FLAG_BUCKETS = ("contested", "withdrawn", "refuted")
#: `observation.outcome` vocabulary (belief redesign §4.1). Anything else reads as "" (no outcome).
OUTCOMES = frozenset({"improved", "null", "regressed", "refused_correctness", "refused_scope",
                      "divergence", "anchor", "floor"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")

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
    """What a planning step is about. Every field compared is compared exactly.

    `model_sha256`, `recipe` and `focus_symbols` are optional (belief redesign §7.5). The sha
    identifies the weights even when the file name differs. `recipe` and `focus_symbols` only
    change the ORDER of target-tier lines (same recipe first, then claims on a focus symbol);
    they never filter. A consumer that passes none of them is read exactly as before."""

    model_file: str
    quant: str
    backend: str
    device: str
    context_tokens: int | None = None
    label: str = ""
    model_sha256: str = ""
    recipe: str = ""
    focus_symbols: tuple[str, ...] = ()
    role: str = ""
    knob_families: tuple[str, ...] = ()
    stack_regime: str = ""
    scope: str = "model"

    @property
    def is_lineup(self) -> bool:
        return self.scope == "lineup"

    @property
    def key(self) -> tuple[str, ...]:
        """Identity of this target inside one answer (several roles may share one model)."""
        if self.is_lineup:
            return ("lineup", self.stack_regime)
        return (self.model_file, self.backend, self.role)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "Target":
        """`model_file`, or `model_path` reduced to its basename. An incomplete target raises:
        it is not a wildcard. `device` defaults from the backend on this host. `recipe` is taken
        as given, else from an AutoKernel `surface` of the form `serving:<recipe>`."""
        families = _target_families(raw)
        role = str(raw.get("role") or "").strip()
        regime = str(raw.get("stack_regime") or "").strip()
        if str(raw.get("scope") or "").strip().lower() == "lineup":
            # The lineup target (belief redesign §12.3): AutoPilot's lineup-wide knobs, matched
            # only by stack_regime. No model, so no target/sibling/host tier can reach it.
            return cls(model_file="", quant="", backend="", device="",
                       label=str(raw.get("label") or ""), role=role, knob_families=families,
                       stack_regime=regime, scope="lineup")
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
        sha = str(raw.get("model_sha256") or "").strip().lower()
        if sha and not _SHA256_RE.fullmatch(sha):
            raise ValueError("model_sha256 must be a 64-character hex digest when given")
        recipe = str(raw.get("recipe") or "").strip()
        surface = str(raw.get("surface") or "").strip()
        if not recipe and surface.startswith("serving:"):
            recipe = surface.removeprefix("serving:").strip()
        focus = raw.get("focus_symbols") or ()
        if isinstance(focus, str) or not isinstance(focus, (list, tuple)):
            raise ValueError("focus_symbols must be a list of symbol names when given")
        symbols = tuple(sorted({str(s).strip() for s in focus if str(s).strip()}))
        return cls(context_tokens=depth, label=str(raw.get("label") or ""), model_sha256=sha,
                   recipe=recipe, focus_symbols=symbols, role=role, knob_families=families,
                   stack_regime=regime, **values)

    def as_dict(self) -> dict[str, Any]:
        return {"model_file": self.model_file, "quant": self.quant, "backend": self.backend,
                "device": self.device, "context_tokens": self.context_tokens,
                "label": self.label, "model_sha256": self.model_sha256, "recipe": self.recipe,
                "focus_symbols": list(self.focus_symbols), "role": self.role,
                "knob_families": list(self.knob_families), "stack_regime": self.stack_regime,
                "scope": self.scope}


def _target_families(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """`knob_families` (list) or `knob_family` (one name). Only declared families are accepted:
    a misspelt family on a target would silently match nothing."""
    value = raw.get("knob_families")
    if value is None:
        value = raw.get("knob_family")
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ValueError("knob_families must be a list of family names when given")
    names = {str(v).strip() for v in value if str(v).strip()}
    unknown = sorted(names - KNOB_FAMILIES)
    if unknown:
        raise ValueError(f"unknown knob families {unknown}; declared: {sorted(KNOB_FAMILIES)}")
    return tuple(sorted(names))


def claim_families(scope: Mapping[str, Any]) -> tuple[str, ...]:
    """A claim's declared `knob_family` (one name, or a list), as recorded."""
    value = scope.get("knob_family") if isinstance(scope, Mapping) else None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(sorted({str(v).strip() for v in value if str(v).strip()}))


@dataclass(frozen=True)
class ModelFamily:
    """One declared lineage: GGUF files that share an architecture but differ in weights or
    quant mix. Evidence measured on one member is shown to another as SIBLING context, labelled
    "transfer unproven", and never counted as target evidence."""

    family: str
    members: Mapping[str, str]   # GGUF basename -> short label used in rendered lines
    basis: str


#: The declared lineage table (belief redesign §7.1), like `SOURCE_SCOPES`: a row exists only
#: with a basis sentence. Files not listed here have no siblings.
MODEL_LINEAGE: dict[str, ModelFamily] = {fam.family: fam for fam in (
    ModelFamily(
        family="DS41",
        members={"DeepSeek-V4.1-Flash-Q4.gguf": "DS41-Q4",
                 "DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf": "DS41-1017"},
        basis=("both are DeepSeek-V4.1-Flash GGUFs from one producer directory "
               "(models/antirez/deepseek-v4.1-flash-gguf/), same architecture; the 1017 file is "
               "a different release with MXFP4 experts, so weights and quant mix differ")),
    ModelFamily(
        family="Q38FN",
        members={"Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf": "Q38FN-UD-IQ4_XS",
                 "Qwen3.8-Flash-Next-IQ4_XS-uniform.gguf": "Q38FN-IQ4_XS-uniform"},
        basis=("the same Qwen3.8-Flash-Next weights quantised two ways: the served unsloth "
               "UD-IQ4_XS 3-shard mix and the IQ4_XS-uniform single file the INF-70 decode "
               "campaign measured; this family has shown 15.2%-class artifact effects, so the "
               "two are never cross-quoted")),
)}
_FAMILY_OF: dict[str, ModelFamily] = {name: fam for fam in MODEL_LINEAGE.values()
                                      for name in fam.members}


def model_label(model_file: str) -> str:
    """Short label for a GGUF basename: the lineage label, else the basename without `.gguf`."""
    for fam in MODEL_LINEAGE.values():
        if model_file in fam.members:
            return fam.members[model_file]
    return re.sub(r"\.gguf$", "", model_file) if model_file else ""


def _model_match(scope: Mapping[str, Any], target: Target) -> bool | None:
    """None when the scope declares no model; else whether it names the target's weights
    (basename, or model_sha256 when both sides carry one; a sha disagreement always fails)."""
    file = scope.get("model_file")
    sha = str(scope.get("model_sha256") or "").strip().lower()
    if not file and not sha:
        return None
    if sha and target.model_sha256 and sha != target.model_sha256:
        return False
    if file and PurePath(str(file)).name == target.model_file:
        return True
    return bool(sha and target.model_sha256 and sha == target.model_sha256)


def _dims_match(scope: Mapping[str, Any], target: Target) -> bool:
    for key in _MATCH_KEYS:
        if key not in scope or scope[key] in (None, ""):
            continue
        value = scope[key]
        if key == "quant":
            if target.quant and str(value).upper() != target.quant.upper():
                return False
        elif key == "context_tokens":
            if target.context_tokens is not None and value != target.context_tokens:
                return False
        elif str(value).strip().lower() != getattr(target, key):
            return False
    return True


def applicability_matches(scope: Mapping[str, Any], target: Target) -> bool:
    """TARGET tier (belief redesign §7.1): the scope names the target's weights (model_file
    basename or model_sha256) and every other dimension it declares equals the target's. A
    device-only scope never matches here -- it is host context, not evidence about a model."""
    if not isinstance(scope, Mapping) or not _model_match(scope, target):
        return False
    return _dims_match(scope, target)


def sibling_matches(scope: Mapping[str, Any], target: Target) -> bool:
    """SIBLING tier: a different file in the target's declared `MODEL_LINEAGE` family, on the
    target's backend (the scope must declare backend or device, and what it declares must
    equal the target's). Quant is not compared: siblings differ in quant mix by definition."""
    if not isinstance(scope, Mapping) or not scope.get("model_file"):
        return False
    if _model_match(scope, target) is not False:
        return False
    family = _FAMILY_OF.get(PurePath(str(scope["model_file"])).name)
    if family is None or family is not _FAMILY_OF.get(target.model_file):
        return False
    backend, device = scope.get("backend"), scope.get("device")
    if not backend and not device:
        return False
    if backend and str(backend).strip().lower() != target.backend:
        return False
    return not (device and str(device).strip().lower() != target.device)


def host_matches(scope: Mapping[str, Any], target: Target) -> bool:
    """HOST tier: no model declared, a device declared, every declared dimension equal (the
    pre-tier device-only rule). Rendered as a host ceiling, never as evidence about a model."""
    if not isinstance(scope, Mapping) or _model_match(scope, target) is not None:
        return False
    return bool(scope.get("device")) and _dims_match(scope, target)


def lineup_matches(scope: Mapping[str, Any], target: Target) -> bool:
    """LINEUP tier: a lineup target and a claim declaring the same, non-empty stack_regime."""
    regime = str(scope.get("stack_regime") or "").strip() if isinstance(scope, Mapping) else ""
    return target.is_lineup and bool(regime) and regime == target.stack_regime


def tier_of(scope: Mapping[str, Any], target: Target) -> str | None:
    if target.is_lineup:
        return "lineup" if lineup_matches(scope, target) else None
    if applicability_matches(scope, target):
        families = set(claim_families(scope)) & KNOB_FAMILIES
        if families & set(target.knob_families):
            return "knob"
        return "target"
    if sibling_matches(scope, target):
        return "sibling"
    if host_matches(scope, target):
        return "host"
    return None


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
    """refuted | contested | withdrawn | weak, for a claim the gate did not ALLOW. Fold/gate
    output only: `refuted` is `belief.verdict(floor) == Opposed` (opposition clears the floor and
    support does not); the rest is the pre-tier rule unchanged."""
    if belief is not None and hasattr(belief, "verdict"):
        try:
            if belief.verdict(_policy().floor) == Verdict.OPPOSED:
                return "refuted"
        except Exception:  # noqa: BLE001 -- a fixture belief without paths is not refuted
            pass
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


# ---- reading one claim (defensive: the observation block may be absent, partial or malformed)


_DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


def _num(value: Any) -> float | None:
    """THE number reader for evidence fields. The canonical ledger encoding forbids floats, so
    the carrier writes numeric observation fields as decimal strings; ints and (synthetic
    fixtures only) floats are accepted too. Anything else, or a non-finite number, is absent."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not _DECIMAL.fullmatch(text):
            return None
        value = float(text)
    elif isinstance(value, int):
        value = float(value)
    elif not isinstance(value, float):
        return None
    return value if math.isfinite(value) else None


def _count(value: Any) -> int | None:
    """A positive integer count (n_pairs), as int or decimal-integer string."""
    number = _num(value)
    if number is None or number < 1 or number != int(number):
        return None
    return int(number)


def _str(value: Any) -> str:
    return " ".join(str(value).split()) if isinstance(value, (str, int, float)) \
        and not isinstance(value, bool) else ""


def _recency(stamp: str) -> float:
    try:
        moment = _ts(stamp)
    except (TypeError, ValueError):
        return 0.0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def read_observation(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """The value-bearing part of an evidence assertion (belief redesign §4.1/§4.2): `metric`,
    `value`, `unit` and the `observation` block. Every key is optional; anything malformed reads
    as absent, so a frame written before the carrier change renders exactly as before."""
    raw = evidence.get("observation") if isinstance(evidence, Mapping) else None
    obs = raw if isinstance(raw, Mapping) else {}
    mech = obs.get("mechanism")
    if isinstance(mech, str):
        mech = {"id": mech}
    elif not isinstance(mech, Mapping):
        mech = {}
    outcome = _str(obs.get("outcome")).lower()
    decisive = obs.get("decisive")
    return {
        "metric": _str(evidence.get("metric")) if isinstance(evidence, Mapping) else "",
        "value": _num(evidence.get("value")) if isinstance(evidence, Mapping) else None,
        "unit": _str(evidence.get("unit")) if isinstance(evidence, Mapping) else "",
        "has_observation": bool(obs),
        "outcome": outcome if outcome in OUTCOMES else "",
        "outcome_native": _str(obs.get("outcome_native")),
        "outcome_reason": _str(obs.get("outcome_reason")),
        "anchor_value": _num(obs.get("anchor_value")),
        "effect_rel": _num(obs.get("effect_rel")),
        "noise_floor_rel": _num(obs.get("noise_floor_rel")),
        "decisive": decisive if isinstance(decisive, bool) else None,
        "n_pairs": _count(obs.get("n_pairs")),
        "mechanism_id": _str(mech.get("id")),
        "statement": _str(mech.get("statement")),
        "falsifier": _str(mech.get("falsifier")),
        "serving_claim_id": _str(obs.get("serving_claim_id")),
        "retrofit": obs.get("retrofit") is True,
    }


def _table_scope(table: SourceScope) -> dict[str, Any]:
    return {"model_file": table.model_file, "quant": table.quant, "backend": table.backend,
            "device": table.device}


def _tier(scope: Mapping[str, Any], targets: list[Target]) -> tuple[str | None, list[Target]]:
    """The best tier this claim reaches for any target (target > sibling > host), and the
    targets it reaches it for. A claim lands in exactly one tier."""
    hits: dict[str, list[Target]] = {}
    for target in targets:
        tier = tier_of(scope, target)
        if tier:
            hits.setdefault(tier, []).append(target)
    for tier in TIERS:
        if tier in hits:
            return tier, hits[tier]
    return None, []


_V1_SERVING = re.compile(r"^clm_legacy-serving:(?P<cap>[^:|]+):")
_V2_SERVING = re.compile(r"^clm_legacy-serving-v2:(?P<cap>[^:|]+)")


def _dedup_serving(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """v1 arm claims hidden behind the v2 capture claim for the same receipt (belief redesign
    §7.4/§8): same capture id, or the same receipt locator. The ledger keeps both."""
    caps, locators = set(), set()
    for row in rows:
        match = _V2_SERVING.match(row["raw_id"]) or _V2_SERVING.match(row["claim_id"])
        if match:
            caps.add(match["cap"])
            if row["locator"]:
                locators.add(row["locator"])
    if not caps:
        return rows, []
    kept, hidden = [], []
    for row in rows:
        match = _V1_SERVING.match(row["raw_id"]) or _V1_SERVING.match(row["claim_id"])
        if match and (match["cap"] in caps or (row["locator"] and row["locator"] in locators)):
            hidden.append(row)
        else:
            kept.append(row)
    return kept, hidden


_SERVING_NUMBERS = ("metric", "value", "unit", "anchor_value", "effect_rel", "noise_floor_rel",
                    "decisive", "n_pairs")


def _merge_linked(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                         list[dict[str, Any]]]:
    """An experiment claim whose `observation.serving_claim_id` names a serving-v2 claim for the
    same capture becomes ONE line: the experiment claim (mechanism statement, falsifier,
    producer verdict) carrying the serving claim's numbers. Both ids stay reliance-eligible
    (`linked_claim_ids`). Only two usable claims on the same tier merge; a flagged partner is
    shown on its own."""
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_id.setdefault(row["raw_id"], row)
        by_id.setdefault(row["claim_id"], row)
    merged: list[dict[str, Any]] = []
    merged_ids: set[str] = set()
    for row in rows:
        link = row["serving_claim_id"]
        if not link or row["claim_id"] in merged_ids:
            continue
        partner = by_id.get(link if link.startswith("clm_") else f"clm_{link}")
        if (partner is None or partner is row or partner["claim_id"] in merged_ids
                or partner["tier"] != row["tier"] or partner["status"] != "verified"
                or row["status"] != "verified"):
            continue
        for key in _SERVING_NUMBERS:
            if partner[key] not in (None, ""):
                row[key] = partner[key]
        for key in ("outcome", "outcome_native", "mechanism_id", "symbol", "recipe", "epoch",
                    "build_sha", "np"):
            if row[key] in (None, "") and partner[key] not in (None, ""):
                row[key] = partner[key]
        row["linked_claim_ids"] = sorted(set(row["linked_claim_ids"]) | {partner["claim_id"]})
        merged_ids.add(partner["claim_id"])
        merged.append(partner)
    return [row for row in rows if row["claim_id"] not in merged_ids], merged


def _epoch_tier(row: Mapping[str, Any]) -> str:
    return "target" if row["tier"] in ("knob", "target") else row["tier"]


def _mark_stale_epochs(rows: list[dict[str, Any]]) -> None:
    """Per (tier, model, recipe, source kind) the newest row that declares an epoch names the
    current epoch; a row on another epoch is stale (its number is not comparable, the fact that
    it was tried still stands). Rows that declare no epoch are never stale."""
    current: dict[tuple, tuple[float, str, str]] = {}
    for row in rows:
        if not row["epoch"]:
            continue
        key = (_epoch_tier(row), row["model_file"], row["recipe"], row["source_kind"])
        cand = (row["recency"], row["revision"], row["epoch"])
        if key not in current or cand > current[key]:
            current[key] = cand
    for row in rows:
        key = (_epoch_tier(row), row["model_file"], row["recipe"], row["source_kind"])
        row["stale_epoch"] = bool(row["epoch"]) and current[key][2] != row["epoch"]


def collect(frames: list[Mapping[str, Any]], targets: Iterable[Target], *, as_of: str,
            fold_result: Any = None) -> dict[str, Any]:
    """Every claim that applies to the targets, tiered and gated, before any cap. Usable rows
    (gate ALLOW, newest complete run per source) are `rows`; refused-but-decision-relevant ones
    are in `flagged`. Public so acceptance checks can count what the caps hide."""
    targets = list(targets)
    visible = visible_frames(frames, as_of)
    result = fold_result if fold_result is not None else fold(visible, as_of=as_of)
    policy = _policy()
    sources: dict[str, Mapping[str, Any]] = {}
    source_prov: dict[str, Mapping[str, Any]] = {}
    claims: dict[str, Mapping[str, Any]] = {}
    support: dict[str, Mapping[str, Any]] = {}
    reasons: dict[str, tuple[str, ...]] = {}
    for frame in visible:
        kind, assertion = str(frame.get("frame_type", "")), frame.get("assertion") or {}
        if kind.endswith("source_observed/v1"):
            sid = str(assertion.get("source_id", ""))
            sources[sid] = assertion
            source_prov[sid] = frame.get("provenance") or {}
        elif kind.endswith("claim_proposed/v1"):
            claims[str(assertion.get("claim_id", ""))] = assertion
        elif kind.endswith("evidence_supports_claim/v1"):
            cid = str(assertion.get("claim_id", ""))
            support[cid] = assertion
            reasons[cid] = tuple(str(r) for r in
                                 (frame.get("provenance") or {}).get("grade_reasons") or ())

    omitted: list[dict[str, Any]] = []
    flagged: dict[str, list[dict[str, Any]]] = {b: [] for b in FLAG_BUCKETS}
    runs: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    expected: dict[tuple[str, str | None], frozenset] = {}
    seen: set[str] = set()
    matched_any = False
    for raw_id, claim in claims.items():
        sid = str(claim.get("source_id", ""))
        source = sources.get(sid)
        if source is None:
            continue
        kind = str(source.get("source_kind", ""))
        scope_raw = source.get("applicability")
        table = SOURCE_SCOPES.get(kind)
        if scope_raw:
            if not isinstance(scope_raw, Mapping):
                continue
            scope: Mapping[str, Any] = scope_raw
        elif table is not None:
            scope = _table_scope(table)
        else:
            continue
        tier, hits = _tier(scope, targets)
        if tier is None:
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
        evidence = support.get(raw_id) or {}
        obs = read_observation(evidence)
        model_file = PurePath(str(scope.get("model_file") or "")).name if scope.get(
            "model_file") else ""
        pro = getattr(belief, "pro", None)
        revision = str(source.get("revision_observed", ""))
        np_value = scope.get("np")
        row = {"claim_id": claim_id, "raw_id": raw_id, "source_kind": kind, "run": run,
               "key": key, "context_tokens": depth,
               "grade": str(pro) if pro is not None else "",
               "grade_rank": (pro.q + pro.t, pro.q) if pro is not None else (0, 0),
               "locator": locator.split("|", 1)[0], "revision": revision,
               "recency": _recency(revision),
               "protocol_id": str(evidence.get("protocol_id") or ""),
               "reps": evidence.get("reps"),
               "text": str(claim.get("display_text", "")),
               "grade_reasons": reasons.get(raw_id, ()),
               "targets": sorted({t.model_file for t in hits}),
               "target_keys": sorted({t.key for t in hits}),
               "knob_family": ",".join(claim_families(scope)),
               "knobs": dict(scope["knobs"]) if isinstance(scope.get("knobs"), Mapping) else {},
               "varied": [str(v) for v in scope["varied"]]
               if isinstance(scope.get("varied"), (list, tuple)) else [],
               "role": _str(scope.get("role")), "stack_regime": _str(scope.get("stack_regime")),
               "tier": tier, "status": "verified",
               "model_file": model_file, "label": model_label(model_file),
               "backend": str(scope.get("backend") or hits[0].backend).strip().lower(),
               "recipe": _str(scope.get("recipe")), "epoch": _str(scope.get("epoch")),
               "build_sha": _str(scope.get("build_sha")),
               "np": np_value if isinstance(np_value, int) and not isinstance(np_value, bool)
               else None,
               "symbol": _str(scope.get("symbol")), "op": _str(scope.get("op")),
               "hit_recipes": sorted({t.recipe for t in hits if t.recipe}),
               "hit_focus": sorted({s for t in hits for s in t.focus_symbols}),
               "stale_epoch": False, "earlier": [], "linked_claim_ids": [], **obs}
        row["retrofit"] = bool(obs["retrofit"] or source_prov.get(sid, {}).get("retrofit") is True)
        if not isinstance(row["reps"], int) or isinstance(row["reps"], bool):
            row["reps"] = None
        if verdict.outcome != Outcome.ALLOW:
            bucket = _bucket(belief, verdict)
            gate_reason = (verdict.reasons or [""])[0]
            if bucket in flagged:
                flagged[bucket].append({**row, "status": bucket,
                                        "gate_outcome": verdict.outcome,
                                        "gate_reason": _cap(gate_reason, REASON_CAP)})
            omitted.append(_omit(kind, f"gate_refused:{verdict.outcome}", run=run,
                                 claim_id=claim_id, detail=gate_reason))
            continue
        runs.setdefault((kind, run), []).append(row)

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

    every = candidates + [row for bucket in FLAG_BUCKETS for row in flagged[bucket]]
    kept, hidden = _dedup_serving(every)
    hidden_ids = {row["claim_id"] for row in hidden}
    for row in hidden:
        omitted.append(_omit(row["source_kind"], "superseded_by_v2", run=row["run"],
                             claim_id=row["claim_id"],
                             detail="v1 arm claim; the v2 capture claim for the same receipt "
                                    "is shown"))
    candidates = [row for row in candidates if row["claim_id"] not in hidden_ids]
    candidates, merged = _merge_linked(candidates)
    merged_ids = {row["claim_id"] for row in merged}
    for row in merged:
        omitted.append(_omit(row["source_kind"], "merged_into_experiment_line", run=row["run"],
                             claim_id=row["claim_id"],
                             detail="serving-v2 numbers shown on the linked experiment claim"))
    kept = [row for row in kept if row["claim_id"] not in merged_ids]
    for bucket in FLAG_BUCKETS:
        flagged[bucket] = [row for row in flagged[bucket] if row["claim_id"] not in hidden_ids]
    _mark_stale_epochs(kept)
    candidates.sort(key=lambda row: (row["source_kind"], row["locator"], row["claim_id"]))
    for bucket in flagged.values():
        bucket.sort(key=lambda row: (row["source_kind"], row["locator"], row["claim_id"]))
    return {"fold": result, "frontier": result.frontier, "rows": candidates,
            "flagged": flagged, "omitted": omitted, "run_rows": run_rows,
            "whole_runs": set(expected), "matched_any": matched_any}


# ---- ranking (belief redesign §7.2)

_OUTCOME_GROUP = {"improved": 1, "regressed": 1, "refused_correctness": 2, "refused_scope": 2,
                  "divergence": 2, "null": 3, "anchor": 4, "floor": 4}


def _group(row: Mapping[str, Any]) -> int:
    """0 flagged · 1 current-epoch decisive (improved/regressed) · 2 correctness/scope refusals
    and divergences · 3 nulls · 4 anchors/floors · 5 claims with no outcome (pre-observation
    frames) · 6 older epochs."""
    if row["status"] != "verified":
        return 0
    if row["stale_epoch"]:
        return 6
    return _OUTCOME_GROUP.get(row["outcome"], 5)


def _rank_key(row: Mapping[str, Any]) -> tuple:
    group = _group(row)
    flag_order = FLAG_BUCKETS.index(row["status"]) if row["status"] in FLAG_BUCKETS else 0
    recipe_boost = 0 if row["recipe"] and row["recipe"] in row["hit_recipes"] else 1
    focus_boost = 0 if row["symbol"] and row["symbol"] in row["hit_focus"] else 1
    grade = (-row["grade_rank"][0], -row["grade_rank"][1])
    inner = ((-row["recency"],) + grade) if group in (1, 4) else (grade + (-row["recency"],))
    return (group, flag_order, recipe_boost, focus_boost) + inner + (row["claim_id"],)


def _mechanism_key(row: Mapping[str, Any]) -> tuple | None:
    if row["status"] != "verified":
        return None
    if row["mechanism_id"]:
        return (row["model_file"], row["mechanism_id"], row["recipe"])
    if row["outcome"] in ("anchor", "floor"):
        return (row["model_file"], f"<{row['outcome']}>", row["recipe"], row["source_kind"])
    return None


def _fold_mechanisms(ranked: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                              list[dict[str, Any]]]:
    """At most one detailed line per (mechanism, recipe): the best-ranked row carries the others
    as `earlier` captures."""
    reps: dict[tuple, dict[str, Any]] = {}
    out, folded = [], []
    for row in ranked:
        key = _mechanism_key(row)
        if key is None:
            out.append(row)
        elif key in reps:
            reps[key]["earlier"].append(row)
            folded.append(row)
        else:
            row["earlier"] = []
            reps[key] = row
            out.append(row)
    return out, folded


def _units(ranked: list[dict[str, Any]], whole: set) -> list[list[dict[str, Any]]]:
    """Packing units in rank order. A run that declares its complete key set packs whole (a
    truncated matrix would read as an incomplete one). Inside one rank bucket, units are
    interleaved round-robin across source kinds so one large source cannot crowd the others
    out of the cap."""
    units: list[list[dict[str, Any]]] = []
    run_unit: dict[tuple, list[dict[str, Any]]] = {}
    for row in ranked:
        key = (row["source_kind"], row["run"])
        if key in whole and row["status"] == "verified":
            if key in run_unit:
                run_unit[key].append(row)
                continue
            run_unit[key] = [row]
            units.append(run_unit[key])
        else:
            units.append([row])
    out: list[list[dict[str, Any]]] = []
    index = 0
    while index < len(units):
        bucket = _rank_key(units[index][0])[:4]
        end = index
        while end < len(units) and _rank_key(units[end][0])[:4] == bucket:
            end += 1
        queues: dict[str, list[list[dict[str, Any]]]] = {}
        for unit in units[index:end]:
            queues.setdefault(unit[0]["source_kind"], []).append(unit)
        lanes = list(queues.values())
        while any(lanes):
            for lane in lanes:
                if lane:
                    out.append(lane.pop(0))
        index = end
    return out


def _forced(unit: list[dict[str, Any]]) -> bool:
    """The newest serving floor per recipe is always shown on the target tier."""
    return any(r["outcome"] == "floor" and r["status"] == "verified" for r in unit)


def _select(units: list[list[dict[str, Any]]], cap: int, *, force: bool,
            flagged_cap: int = FLAGGED_CAP) -> list[list[dict[str, Any]]]:
    chosen: set[int] = set()
    count = 0
    if force:
        for i, unit in enumerate(units):
            if _forced(unit):
                chosen.add(i)
                count += len(unit)
    per_bucket: dict[str, int] = {}
    for i, unit in enumerate(units):
        if i in chosen or count + len(unit) > cap:
            continue
        status = unit[0]["status"]
        if status in FLAG_BUCKETS:
            if per_bucket.get(status, 0) >= flagged_cap:
                continue
            per_bucket[status] = per_bucket.get(status, 0) + 1
        chosen.add(i)
        count += len(unit)
    return [units[i] for i in sorted(chosen)]


# ---- tried-mechanisms index

_INDEX_CODE = {"improved": "improved", "regressed": "regressed", "null": "null",
               "refused_correctness": "refused", "refused_scope": "refused-scope",
               "divergence": "divergence", "": "recorded"}


def tried_index(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per (tier, model file, mechanism) on the target and sibling tiers: the
    best-ranked capture's outcome, plus how many captures exist. Anchors and floors are not
    mechanisms and are not indexed."""
    best: dict[tuple, dict[str, Any]] = {}
    counts: dict[tuple, int] = {}
    for row in rows:
        if row["tier"] in ("host", "lineup") or not row["mechanism_id"] or row["outcome"] in (
                "anchor", "floor"):
            continue
        tier = "target" if row["tier"] in _MODEL_TIERS else row["tier"]
        key = (tier, row["model_file"], row["mechanism_id"])
        counts[key] = counts.get(key, 0) + 1
        if key not in best or _rank_key(row) < _rank_key(best[key]):
            best[key] = row
    order = sorted(best, key=lambda k: (TIERS.index(k[0]), model_label(k[1]), k[1],
                                        _rank_key(best[k])))
    out = []
    for key in order:
        row = best[key]
        out.append({"mechanism_id": row["mechanism_id"], "outcome": row["outcome"] or "recorded",
                    "knob_family": row["knob_family"],
                    "outcome_native": row["outcome_native"], "effect_rel": row["effect_rel"],
                    "noise_floor_rel": row["noise_floor_rel"],
                    "reason": _cap(row["outcome_reason"], 80) if row["outcome_reason"] else "",
                    "tier": key[0], "model_file": row["model_file"],
                    "label": row["label"], "recipe": row["recipe"], "status": row["status"],
                    "stale_epoch": row["stale_epoch"], "claim_id": row["claim_id"],
                    "date": row["revision"], "captures": counts[key]})
    return out


def _index_text(entry: Mapping[str, Any]) -> str:
    code = _INDEX_CODE.get(entry["outcome"] if entry["outcome"] != "recorded" else "",
                           entry["outcome"])
    if entry["effect_rel"] is not None:
        detail = f"({entry['effect_rel'] * 100:+.1f}%)"
    elif entry["reason"]:
        detail = f"({_cap(entry['reason'], 40)})"
    else:
        detail = ""
    text = f"{entry['mechanism_id']} {code}{detail}"
    if entry["captures"] > 1:
        text += f" x{entry['captures']}"
    if entry["status"] != "verified":
        text += f" [{entry['status']}]"
    elif entry["stale_epoch"]:
        text += " [stale epoch]"
    return text


# ---- rendering (belief redesign §7.3)

TIER_TITLES = {
    "knob": ("### Usable, knob tier -- the target's own weights AND a knob family this target "
             "can change (varied / fixed knobs printed)"),
    "target": "### Usable, target tier -- claims scoped to the target's own weights",
    "lineup": ("### Usable, lineup tier -- the planner's own trials at this stack regime "
               "(lineup-wide knobs)"),
    "sibling": ("### Usable, sibling tier -- measured on a sibling file of the same lineage "
                "(other weights, quant or recipe); transfer unproven, never target evidence"),
    "host": ("### Host tier -- host ceiling, not about this model; not evidence for a "
             "proposal"),
}
FLAG_TITLES = {
    "contested": ("### Contested -- the evidence disagrees or is under review; do not build on "
                  "these without new evidence"),
    "withdrawn": "### Withdrawn -- support retracted; the result no longer stands",
    "refuted": "### Refuted -- opposing evidence clears the floor; do not rely on these",
}
STALE_NOTE = ("Older epochs (stale epoch -- the number is not comparable; the fact that the "
              "mechanism was tried still stands):")
_WORD = {"improved": "IMPROVED", "regressed": "REGRESSED", "null": "NULL",
         "divergence": "DIVERGENCE"}


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value) >= 1000:
        return f"{value:.0f}"
    return f"{value:.4g}"


def _pct(rel: float | None, signed: bool = True) -> str:
    if rel is None:
        return ""
    return f"{rel * 100:+.2f}%" if signed else f"{rel * 100:.2f}%"


def _n_text(row: Mapping[str, Any], *, pairs_first: bool = True) -> str:
    if pairs_first and row["n_pairs"]:
        return f"{row['n_pairs']} pairs"
    if row["reps"] is not None:
        return f"n={row['reps']}"
    if row["n_pairs"]:
        return f"n={row['n_pairs']}"
    return "n unrecorded"


def _value_text(value: float | None, unit: str) -> str:
    return f"{_fmt(value)} {unit}".strip() if value is not None else ""


def _where(row: Mapping[str, Any], tier: str) -> str:
    extras = []
    if row["build_sha"]:
        extras.append(f"build {row['build_sha'][:8]}")
    if row["epoch"]:
        extras.append(f"epoch {row['epoch'][:8]}")
    if row["np"] is not None:
        extras.append(f"np {row['np']}")
    if row.get("role"):
        extras.append(f"role {row['role']}")
    if row.get("knob_family"):
        extras.append(f"family {row['knob_family']}")
    if row.get("varied"):
        extras.append(f"varied [{', '.join(row['varied'])}]")
    if row.get("knobs"):
        fixed = ", ".join(f"{k}={_cap(v, 40)}" for k, v in sorted(row["knobs"].items()))
        extras.append(f"knobs {{{_cap(fixed, 160)}}}")
    tail = (" " + " ".join(extras)) if extras else ""
    if tier == "lineup":
        return f"lineup regime {row['stack_regime'][:12]}{tail}"
    if tier == "host":
        return "host ceiling, not about this model"
    if tier == "sibling":
        recipe = f", recipe {row['recipe']}" if row["recipe"] else ""
        return (f"sibling: measured on {row['model_file'] or row['locator']}{recipe}; "
                f"transfer unproven{tail}")
    name = row["label"] or row["model_file"] or "target"
    recipe = f" {row['recipe']}" if row["recipe"] else ""
    return f"{name}/{row['backend']}{recipe}{tail}"


def _subject(row: Mapping[str, Any]) -> str:
    if row["mechanism_id"]:
        return row["mechanism_id"] + (f" @ {row['symbol']}" if row["symbol"] else "")
    return row["symbol"] or row["metric"] or "measurement"


def _what(row: Mapping[str, Any]) -> str:
    """The value-bearing second line, or "" when the frame carries no value and no outcome."""
    outcome, unit = row["outcome"], row["unit"]
    value, anchor = row["value"], row["anchor_value"]
    if outcome in _WORD:
        detail = []
        if value is not None:
            detail.append(_value_text(value, unit)
                          + (f" vs anchor {_value_text(anchor, unit)}" if anchor is not None
                             else ""))
        elif anchor is not None:
            detail.append(f"anchor {_value_text(anchor, unit)}")
        if row["noise_floor_rel"] is not None:
            detail.append(f"floor {_pct(row['noise_floor_rel'], False)}")
        detail.append(_n_text(row))
        if row["decisive"] is not None:
            detail.append("decisive" if row["decisive"] else "not decisive")
        effect = f" {_pct(row['effect_rel'])} vs anchor" if row["effect_rel"] is not None else ""
        text = f"{_subject(row)}: {_WORD[outcome]}{effect} ({'; '.join(detail)})"
        if row["outcome_native"]:
            text += f" -- producer verdict {row['outcome_native']}"
        if outcome == "divergence" and row["outcome_reason"]:
            text += f': "{_cap(row["outcome_reason"], REASON_CAP)}"'
        return text
    if outcome in ("refused_correctness", "refused_scope"):
        gate = "correctness" if outcome == "refused_correctness" else "scope"
        metric = f" ({row['metric']})" if row["metric"] and ":" in row["metric"] else ""
        reason = f': "{_cap(row["outcome_reason"], REASON_CAP)}"' if row["outcome_reason"] else ""
        return f"{_subject(row)}: REFUSED by the {gate} gate{metric}{reason}"
    if outcome == "floor":
        parts = [f"median {_value_text(value, unit)}" if value is not None else "",
                 f"floor {_pct(row['noise_floor_rel'], False)}"
                 if row["noise_floor_rel"] is not None else "",
                 _n_text(row, pairs_first=False)]
        return "serving floor: " + "; ".join(p for p in parts if p)
    if outcome == "anchor":
        return (f"{_subject(row)}: ANCHOR {_value_text(value, unit)} "
                f"({_n_text(row, pairs_first=False)})").replace("  ", " ")
    if value is not None:
        return f"{_subject(row)}: {_value_text(value, unit)} ({_n_text(row, pairs_first=False)})"
    return ""


def _earlier_text(row: Mapping[str, Any]) -> str:
    earlier = row.get("earlier") or []
    if not earlier:
        return ""
    bits = []
    for other in earlier[:EARLIER_CAP]:
        label = other["outcome"] or "recorded"
        eff = f" {_pct(other['effect_rel'])}" if other["effect_rel"] is not None else (
            f" {_value_text(other['value'], other['unit'])}" if other["value"] is not None
            else "")
        stale = " stale epoch" if other["stale_epoch"] else ""
        bits.append(f"{label}{eff} {other['revision'][:10]}{stale}".strip())
    more = " ..." if len(earlier) > EARLIER_CAP else ""
    return f" (+{len(earlier)} earlier captures: {'; '.join(bits)}{more})"


def row_lines(row: Mapping[str, Any], *, first_of_source: bool = False) -> list[str]:
    """One claim, value-bearing when its evidence frame carries an observation, else the
    pre-observation text line."""
    tier = row["tier"]
    tags = [row["grade"] or "ungraded", row["status"]]
    if row["retrofit"]:
        tags.append("retrofit")
    if row["stale_epoch"]:
        tags.append("stale epoch")
    linked = f" (+ {', '.join(row['linked_claim_ids'])})" if row.get("linked_claim_ids") else ""
    head = f"- {row['claim_id']}{linked} [{' · '.join(tags)}] {_where(row, tier)}"
    what = _what(row)
    lines: list[str] = []
    if what:
        lines.append(head)
        lines.append(f"  {what}{_earlier_text(row)}")
        if tier in _MODEL_TIERS and row["statement"]:
            falsifier = (f"; falsifier: {_cap(row['falsifier'], STATEMENT_CAP // 2)}"
                         if row["falsifier"] else "")
            lines.append(f"  mechanism: {_cap(row['statement'], STATEMENT_CAP)}{falsifier}")
    else:
        if first_of_source and tier != "host":
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
        cap = CLAIM_TEXT_CAP if tier in _MODEL_TIERS + ("lineup",) else CONTEXT_TEXT_CAP
        lines.append(f"{head}: {row['locator']} ({'; '.join(facts)}): {_cap(row['text'], cap)}")
        if tier in _MODEL_TIERS and row["grade_reasons"]:
            lines.append(f"  grade notes: {_cap(row['grade_reasons'][0], REASON_CAP)}")
    if row["status"] in FLAG_BUCKETS:
        lines.append(f"  gate: {_cap(row.get('gate_reason') or '', REASON_CAP // 2)}")
    return lines


def _target_label(target: Target) -> str:
    return f"lineup:{target.stack_regime or 'unrecorded'}" if target.is_lineup \
        else target.model_file


def _target_name(target: Target) -> str:
    role = f", role {target.role}" if target.role else ""
    return f"{target.model_file} ({target.backend}{role})"


def banner_text(targets: list[Target], empty: list[Target]) -> str | None:
    """The empty-target banner (belief redesign §7.3, §12.3), or None when every target has
    beliefs of its own. A lineup target with none says "No beliefs at this regime"."""
    if not empty:
        return None
    models = [t for t in empty if not t.is_lineup]
    lineups = [t for t in empty if t.is_lineup]
    parts = []
    if models:
        parts.append(f"No beliefs are scoped to {', '.join(_target_name(t) for t in models)}.")
    if lineups:
        regimes = ", ".join(t.stack_regime or "regime unrecorded" for t in lineups)
        parts.append(f"No beliefs at this regime ({regimes}).")
    text = " ".join(parts)
    if len(empty) == len(targets):
        text += " The lines below are sibling/host context only."
    return text


def render(targets: list[Target], rows: list[dict[str, Any]],
           flagged: Mapping[str, list[dict[str, Any]]], *, frontier: int | None, as_of: str,
           max_claims: int = DEFAULT_MAX_CLAIMS, max_bytes: int = DEFAULT_MAX_BYTES,
           reply_field: str = "relies_on_claims",
           whole_runs: set[tuple[str, str | None]] | None = None,
           tried: list[dict[str, Any]] | None = None, banner: str | None = None,
           ) -> tuple[str, list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Bounded, tiered block. Returns (section, shown usable rows, shown flagged rows by bucket,
    info). ("", [], {...}, info) when nothing fits. Tiers are never mixed: each has its own cap
    and heading; flagged claims of any tier are listed first."""
    empty_flags: dict[str, list[dict[str, Any]]] = {b: [] for b in FLAG_BUCKETS}
    info: dict[str, Any] = {"tiers_shown": {t: 0 for t in TIERS}, "index_shown": 0,
                            "folded": [], "selected": []}
    flagged_rows = [row for b in FLAG_BUCKETS for row in (flagged.get(b) or [])]
    if (not rows and not flagged_rows) or max_claims < 1:
        return "", [], empty_flags, info
    whole = whole_runs or set()
    selected: dict[str, list[list[dict[str, Any]]]] = {}
    remaining = max_claims
    model_budget = TIER_CAPS["target"]          # knob + target share the target budget
    for tier in TIERS:
        pool = [row for row in list(rows) + flagged_rows if row["tier"] == tier]
        ranked, folded = _fold_mechanisms(sorted(pool, key=_rank_key))
        info["folded"].extend(folded)
        cap = max(0, min(TIER_CAPS[tier], remaining,
                         model_budget if tier in _MODEL_TIERS else TIER_CAPS[tier]))
        selected[tier] = _select(_units(ranked, whole), cap, force=(tier in _MODEL_TIERS))
        used = sum(len(unit) for unit in selected[tier])
        remaining -= used
        if tier in _MODEL_TIERS:
            model_budget -= used
    entries = list((tried or [])[:INDEX_CAP])
    names = "; ".join(
        (f"lineup / regime {t.stack_regime or 'unrecorded'}" if t.is_lineup else
         f"{t.model_file} / {t.quant or 'quant unstated'} / {t.backend} / {t.device}")
        + (f" / context {t.context_tokens}" if t.context_tokens else "")
        + (f" / recipe {t.recipe}" if t.recipe else "")
        + (f" / role {t.role}" if t.role else "")
        + (f" / knob families {','.join(t.knob_families)}" if t.knob_families else "")
        for t in targets)
    head = [SECTION_HEADER] + ([banner] if banner else []) + [
        f"Target(s): {names}.",
        "Claims are tiered by declared applicability: knob (the target's own weights and a "
        "knob family it can change), target (the target's own weights), lineup (this stack "
        "regime), "
        "sibling (same declared lineage, other weights or recipe; transfer unproven), host "
        "(device-only scope; a ceiling, not about this model). Grade is the folded "
        f"claim_tuple.grade() Q/T at ledger frontier {frontier}, as of {as_of}."]
    tail = [f"Optional reply field {reply_field}: a list of the knob-, target-, lineup- or "
            "sibling-tier claim ids above that the proposal depends on; omit it when it depends "
            "on none. Host-tier "
            "lines and contested, withdrawn or refuted claims are not evidence for a proposal."]

    def compose() -> str:
        body: list[str] = []
        chosen = {tier: [row for unit in selected[tier] for row in unit] for tier in TIERS}
        for bucket in FLAG_BUCKETS:
            lines = []
            for tier in TIERS:
                for row in chosen[tier]:
                    if row["status"] == bucket:
                        lines.extend(row_lines(row))
            if lines:
                body.extend([FLAG_TITLES[bucket]] + lines)
        for tier in TIERS:
            usable = [row for row in chosen[tier] if row["status"] == "verified"]
            if not usable:
                continue
            body.append(TIER_TITLES[tier])
            described: set[tuple[str, str | None]] = set()
            stale_noted = False
            for row in usable:
                if row["stale_epoch"] and not stale_noted:
                    body.append(STALE_NOTE)
                    stale_noted = True
                key = (row["source_kind"], row["run"])
                body.extend(row_lines(row, first_of_source=key not in described))
                described.add(key)
        if entries:
            body.append("### Tried mechanisms -- every mechanism with a projected outcome here "
                        "(the detailed lines above are capped; this index is not)")
            groups: dict[tuple[str, str], list[str]] = {}
            for entry in entries:
                groups.setdefault((entry["tier"], entry["model_file"]), []).append(
                    _index_text(entry))
            for (tier, model_file), texts in groups.items():
                label = model_label(model_file) or model_file
                prefix = (f"Tried on {label}:" if tier in _MODEL_TIERS
                          else f"Tried on {label} (sibling; transfer unproven):")
                line = prefix
                for text in texts:
                    if len(line) + len(text) + 2 > 220 and line != prefix:
                        body.append(line)
                        line = " "
                    line += (" " if line in (prefix, " ") else "; ") + text
                body.append(line)
        shown_counts = {t: sum(len(u) for u in selected[t]) for t in TIERS}
        flags = {b: sum(1 for t in TIERS for r in chosen[t] if r["status"] == b)
                 for b in FLAG_BUCKETS}
        total = {t: sum(1 for r in list(rows) + flagged_rows if r["tier"] == t) for t in TIERS}
        count = (f"Shown {shown_counts['knob']} of {total['knob']} knob, "
                 f"{shown_counts['target']} of {total['target']} target, "
                 f"{shown_counts['lineup']} of {total['lineup']} lineup, "
                 f"{shown_counts['sibling']} of {total['sibling']} sibling, "
                 f"{shown_counts['host']} of {total['host']} host claim(s) "
                 f"({flags['contested']} contested, {flags['withdrawn']} withdrawn, "
                 f"{flags['refuted']} refuted); tried index {len(entries)} of "
                 f"{len(tried or [])} mechanism(s); bounded at {max_claims} claims / "
                 f"{max_bytes} bytes.")
        if not body:
            return ""
        return "\n".join(head + body + [count] + tail)

    def trim_once() -> bool:
        for tier in ("host", "sibling"):
            if selected[tier]:
                selected[tier].pop()
                return True
        if entries:
            entries.pop()
            return True
        if selected["lineup"]:
            selected["lineup"].pop()
            return True
        for tier in ("target", "knob"):
            units = selected[tier]
            for i in range(len(units) - 1, -1, -1):
                if not _forced(units[i]):
                    units.pop(i)
                    return True
        for tier in ("target", "knob"):
            if selected[tier]:
                selected[tier].pop()
                return True
        return False

    section = compose()
    while section and len(section.encode("utf-8")) > max_bytes:
        if not trim_once():
            section = ""
            break
        section = compose()
    if not section:
        return "", [], empty_flags, info
    shown: list[dict[str, Any]] = []
    shown_flagged: dict[str, list[dict[str, Any]]] = {b: [] for b in FLAG_BUCKETS}
    for tier in TIERS:
        for unit in selected[tier]:
            for row in unit:
                info["selected"].append(row)
                info["tiers_shown"][tier] += 1
                if row["status"] == "verified":
                    shown.append(row)
                else:
                    shown_flagged[row["status"]].append(row)
    info["index_shown"] = len(entries)
    return section, shown, shown_flagged, info


def _claim_view(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"claim_id": row["claim_id"], "source_kind": row["source_kind"], "run": row["run"],
            "grade": row["grade"], "locator": row["locator"], "tier": row["tier"],
            "status": row["status"], "outcome": row["outcome"],
            "mechanism_id": row["mechanism_id"], "value": row["value"], "unit": row["unit"],
            "effect_rel": row["effect_rel"], "noise_floor_rel": row["noise_floor_rel"],
            "anchor_value": row["anchor_value"], "n_pairs": row["n_pairs"],
            "reps": row["reps"], "recipe": row["recipe"], "model_file": row["model_file"],
            "stale_epoch": row["stale_epoch"], "retrofit": row["retrofit"],
            "linked_claim_ids": list(row["linked_claim_ids"]),
            "knob_family": row["knob_family"], "role": row["role"],
            "varied": list(row["varied"]), "knobs": dict(row["knobs"]),
            "stack_regime": row["stack_regime"],
            "not_evidence": row["tier"] == "host"}


def evaluate_frames(frames: list[Mapping[str, Any]], targets: Iterable[Target], *, as_of: str,
                    max_claims: int = DEFAULT_MAX_CLAIMS, max_bytes: int = DEFAULT_MAX_BYTES,
                    fold_result: Any = None, reply_field: str = "relies_on_claims",
                    ) -> dict[str, Any]:
    """The evidence half of a `ready` answer, from frames already verified."""
    targets = list(targets)
    col = collect(frames, targets, as_of=as_of, fold_result=fold_result)
    if not col["matched_any"]:
        return _evidence_empty("no_applicable_claims", as_of=as_of, frontier=col["frontier"],
                               targets=targets)
    rows, flagged, omitted = col["rows"], col["flagged"], col["omitted"]
    every = rows + [row for bucket in FLAG_BUCKETS for row in flagged[bucket]]
    tiers = {tier: sum(1 for row in every if row["tier"] == tier) for tier in TIERS}
    own = _MODEL_TIERS + ("lineup",)
    target_keys = {key for row in every if row["tier"] in own for key in row["target_keys"]}
    empty_targets = [t for t in targets if t.key not in target_keys]
    banner = banner_text(targets, empty_targets)
    tried = tried_index(every)
    section, shown, shown_flagged, info = render(
        targets, rows, flagged, frontier=col["frontier"], as_of=as_of, max_claims=max_claims,
        max_bytes=max_bytes, reply_field=reply_field, whole_runs=col["whole_runs"],
        tried=tried, banner=banner)
    shown_ids = {row["claim_id"] for row in info["selected"]}
    folded_ids = {row["claim_id"] for row in info["folded"]}
    for row in rows:
        if row["claim_id"] in shown_ids:
            continue
        reason = "folded_into_mechanism_line" if row["claim_id"] in folded_ids else "bounded"
        detail = ("an earlier capture of a mechanism shown on one line"
                  if reason != "bounded" else f"cap {max_claims} claims / {max_bytes} bytes")
        omitted.append(_omit(row["source_kind"], reason, run=row["run"],
                             claim_id=row["claim_id"], detail=detail))
    presented_runs: dict[tuple[str, str | None], list[str]] = {}
    for row in shown:
        presented_runs.setdefault((row["source_kind"], row["run"]), []).append(row["claim_id"])
    run_rows = [{"source_kind": kind, "run": run, "status": "presented", "reason": "",
                 "claim_ids": sorted(ids)} for (kind, run), ids in sorted(
                     presented_runs.items(), key=lambda item: (item[0][0], str(item[0][1])))] \
        + col["run_rows"]
    flagged_ids = {b: [r["claim_id"] for r in rows_b] for b, rows_b in shown_flagged.items()}
    host_ids = [row["claim_id"] for row in shown if row["tier"] == "host"]
    in_section = {(e["tier"], e["model_file"], e["mechanism_id"])
                  for e in tried[:info["index_shown"]]}
    in_section |= {(r["tier"], r["model_file"], r["mechanism_id"]) for r in info["selected"]
                   if r["mechanism_id"]}
    tried_json = [{**entry, "in_section": (entry["tier"], entry["model_file"],
                                           entry["mechanism_id"]) in in_section}
                  for entry in tried[:TRIED_JSON_CAP]]
    status = "presented" if (shown or any(flagged_ids.values())) else "omitted"
    return {
        "status": status, "reasons": sorted({o["reason"] for o in omitted}),
        "frontier": col["frontier"], "as_of": as_of,
        # Reliance-eligible ids: usable target- and sibling-tier claims shown in the section.
        "claim_ids": [cid for row in shown if row["tier"] != "host"
                      for cid in [row["claim_id"], *row["linked_claim_ids"]]],
        "contested_claim_ids": flagged_ids["contested"],
        "withdrawn_claim_ids": flagged_ids["withdrawn"],
        "refuted_claim_ids": flagged_ids["refuted"],
        # Shown as host context only; never evidence for a proposal (refused as reliance).
        "host_claim_ids": host_ids, "not_evidence_claim_ids": host_ids,
        "claims": [_claim_view(row) for row in shown],
        "flagged": {b: [{k: row[k] for k in ("claim_id", "source_kind", "grade", "locator",
                                             "gate_outcome", "gate_reason", "tier", "outcome",
                                             "mechanism_id")} for row in rows_b]
                    for b, rows_b in shown_flagged.items()},
        "tiers": tiers, "tiers_shown": dict(info["tiers_shown"]),
        "nonempty_target": any(tiers[t] > 0 for t in own),
        "empty_targets": [_target_label(t) for t in empty_targets],
        "banner": banner, "tried_index": tried_json,
        "tried_index_count": len(tried),
        "runs": run_rows, "omitted": omitted[:OMITTED_CAP], "omitted_count": len(omitted),
        "section": section,
        "section_sha256": hashlib.sha256(section.encode()).hexdigest() if section else "",
        "section_bytes": len(section.encode()),
    }


def _evidence_empty(reason: str, *, as_of: str, frontier: int | None = None,
                    error: str | None = None,
                    targets: Iterable[Target] = ()) -> dict[str, Any]:
    targets = list(targets)
    return {"status": "omitted", "reasons": [reason], "frontier": frontier, "as_of": as_of,
            "claim_ids": [], "contested_claim_ids": [], "withdrawn_claim_ids": [],
            "refuted_claim_ids": [], "host_claim_ids": [], "not_evidence_claim_ids": [],
            "claims": [], "flagged": {b: [] for b in FLAG_BUCKETS},
            "tiers": {t: 0 for t in TIERS}, "tiers_shown": {t: 0 for t in TIERS},
            "nonempty_target": False, "empty_targets": [_target_label(t) for t in targets],
            "banner": banner_text(targets, targets) if targets else None,
            "tried_index": [], "tried_index_count": 0, "runs": [], "omitted": [],
            "omitted_count": 0, "section": "", "section_sha256": "", "section_bytes": 0,
            **({"error": error} if error else {})}


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
                "ledger_state": None, "evidence": None, "banner": None, "alarm": alarm,
                "last_known_good": _known_good_summary(kg_path)}
    except Exception as exc:  # noqa: BLE001 -- an unexpected failure is a refusal, never a plan
        detail = f"{type(exc).__name__}: {exc}"[:500]
        alarm = raise_refusal_alarm(consumer, "reader_error", detail,
                                    escalate_after_s=escalate_after_s, alarm_state=alarm_state,
                                    alarm_config=alarm_config, api=alarm_api)
        return {**base, "status": "refused", "reason": "reader_error", "detail": detail,
                "ledger_state": None, "evidence": None, "banner": None, "alarm": alarm,
                "last_known_good": _known_good_summary(kg_path)}
    cleared = clear_refusal_alarm(consumer, alarm_state=alarm_state, alarm_config=alarm_config,
                                  api=alarm_api)
    return {**base, "status": "ready", "reason": None, "detail": "",
            "targets": [t.as_dict() for t in parsed], "ledger_state": state,
            "ledger_state_digest": state_digest(state), "evidence": evidence,
            "banner": evidence.get("banner"),
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
