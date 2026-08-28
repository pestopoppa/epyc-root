"""Walk the AutoKernel runtime corpus and emit frames through the shared carrier.

WHY THIS EXISTS
---------------
Ten AutoKernel adapters were written, tested, and verified against the real corpus.
Run over `/mnt/raid0/llm/autokernel` they project **2,601 gradeable ClaimTuples**, and
the adapters that should refuse do refuse. Not one had ever been persisted: the
belief-substrate CLI hard-limited ingest to `choices=["intake"]`, so the read side was
fully built and the write side had never fired. This module is the missing walk.

It is a DISPATCHER, not a grader. Each adapter still projects its own native record
into a `ClaimTuple` and `claim_tuple.grade()` decides -- one ladder, shared carrier,
per `docs/design/vidya-pilot-spec.md` §4.7. Nothing here interprets a measurement.

Adapters fall into three call shapes. The first two are walked; the third is reported
as unwired with its reason, because a dispatcher that silently skipped them would read
as "the corpus is covered" when it is not.

  A. receipt + locator/sha/attestation   gpu_screening, aux_receipt, rocm_diagnostic,
                                         governed_receipt, reward_integrity
  B. a single event/journal source       property, evaluation_event
  C. bespoke multi-document signatures   planner_reduction (needs manifest + panel +
                                         prefilter contract), scaffold_panel (needs a
                                         panel document, not a receipt)

`fault_rehearsal` is deliberately absent: it returns dependency classifications and
emits no `ClaimTuple` at all, by design.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterator

from claim_tuple import ProjectionError, to_frames  # noqa: E402

from adapters import (  # noqa: E402
    autokernel_aux_receipt,
    autokernel_evaluation_event,
    autokernel_governed_receipt,
    autokernel_gpu_screening,
    autokernel_property,
    autokernel_reward_integrity,
    autokernel_rocm_diagnostic,
)

ADAPTER_ID = "vidya.adapters.autokernel_corpus/v1"

# Call-shape A: strict receipt readers taking a locator, a file digest and an
# attestation flag.
_RECEIPT_ADAPTERS = (
    autokernel_gpu_screening,
    autokernel_aux_receipt,
    autokernel_rocm_diagnostic,
    autokernel_governed_receipt,
    autokernel_reward_integrity,
)

# Call-shape B: readers that take one event or journal envelope.
_EVENT_ADAPTERS = (
    autokernel_property,
    autokernel_evaluation_event,
)

# Call-shape C: known-good adapters this walk cannot drive from a single file.
UNWIRED = {
    "autokernel_planner_reduction":
        "needs the execution manifest, planner panel and prefilter contract alongside "
        "the reduction receipt; a corpus walk cannot pair them safely",
    "autokernel_scaffold_panel":
        "reads a scaffold panel document plus its arena evaluations, not a receipt",
    "autokernel_fault_rehearsal":
        "emits dependency classifications only, never a ClaimTuple, by design",
}


def _schema_map() -> dict[str, Any]:
    """schema id -> adapter module, built from each adapter's own constants.

    Read off the modules rather than restated here, so a schema rename in an adapter
    cannot leave a stale duplicate in this file pointing at the wrong reader.
    """
    mapping: dict[str, Any] = {}
    for module in (*_RECEIPT_ADAPTERS, *_EVENT_ADAPTERS):
        for name in dir(module):
            if not name.isupper() or not name.endswith("SCHEMA"):
                continue
            value = getattr(module, name)
            # Only source schemas -- never a module's own projection schema, which
            # names its OUTPUT and would make the walk feed an adapter its own rows.
            if (not isinstance(value, str) or not value.startswith("epyc.")
                    or name.startswith("PROJECTION")):
                continue
            mapping.setdefault(value, module)
    return mapping


SCHEMA_TO_ADAPTER = _schema_map()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _dispatch_schema(document: dict) -> str | None:
    """The schema this document dispatches on.

    Receipts declare `schema` at the top level. Journal records declare
    `journal_schema` and carry the real event in `payload` -- the event adapters
    accept that envelope whole and unwrap it themselves, so the envelope is what
    gets dispatched. Keying only on `schema` would miss every journal record.
    """
    for key in ("schema", "journal_schema"):
        value = document.get(key)
        if isinstance(value, str) and value.startswith("epyc."):
            return value
    return None


def iter_documents(root: Path) -> Iterator[tuple[Path, dict, str]]:
    """Every schema-bearing JSON object under `root`, with its digest.

    Both shapes are walked. Receipts are whole `.json` files; the event adapters read
    records that live one-per-line inside journal `.jsonl` shards, so walking only
    `.json` would silently miss the entire property/evaluation-event family -- which
    is the largest projected family in the corpus.
    """
    for path in sorted(root.rglob("*.json")):
        try:
            raw = path.read_bytes()
            document = json.loads(raw)
        except (OSError, json.JSONDecodeError, RecursionError):
            continue
        if isinstance(document, dict) and _dispatch_schema(document):
            yield path, document, _sha256_bytes(raw)

    for path in sorted(root.rglob("*.jsonl")):
        try:
            lines = path.read_bytes().splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except (json.JSONDecodeError, RecursionError):
                continue
            if isinstance(document, dict) and _dispatch_schema(document):
                yield path.with_name(f"{path.name}#L{number}"), document, _sha256_bytes(line)


def rows_for_document(path: Path, document: dict, digest: str) -> list[dict]:
    """Native rows for one document, or [] if no adapter claims its schema."""
    module = SCHEMA_TO_ADAPTER.get(_dispatch_schema(document) or "")
    if module is None:
        return []
    if module in _RECEIPT_ADAPTERS:
        return list(module.native_rows(
            document, receipt_locator=f"autokernel:{path}",
            receipt_sha256=digest, attestation_present=True))
    return list(module.native_rows(document))


def ingest_corpus(ledger, *, root: Path, as_of: str, limit: int | None = None,
                  dry_run: bool = False,
                  on_refusal: Callable[[Path, str], None] | None = None) -> dict:
    """Project every admissible AutoKernel record under `root` into the ledger.

    A `ProjectionError` is a REFUSAL, not a crash: the strict readers exist to reject
    records that do not exactly rederive, and a corpus walk must count those rather
    than abort on the first one. Refusals are reported, never silently dropped.
    """
    frames: list[dict] = []
    seen = refused = projected = unaccepted = no_rows = 0
    refusals: list[dict] = []
    by_adapter: dict[str, int] = {}

    for path, document, digest in iter_documents(root):
        dispatch = _dispatch_schema(document)
        if dispatch not in SCHEMA_TO_ADAPTER:
            continue
        seen += 1
        module = SCHEMA_TO_ADAPTER[dispatch]
        try:
            natives = rows_for_document(path, document, digest)
        except ProjectionError as exc:
            # A reader saying "unsupported schema" is this dispatcher's mapping being
            # imprecise -- the schema constant exists on the module but names an inner
            # document, not an entry point. That is NOT the adapter refusing a record
            # that failed to rederive, and conflating the two would inflate the refusal
            # count and hide the real ones.
            if "unsupported" in str(exc).lower():
                unaccepted += 1
                continue
            refused += 1
            refusals.append({"path": str(path), "schema": dispatch,
                             "reason": str(exc)})
            if on_refusal is not None:
                on_refusal(path, str(exc))
            continue
        if not natives:
            # The adapter accepted the document and declined to project it -- a
            # pre-hook receipt, a void event, a status that carries no measurement.
            # This is the single most common honest outcome and it is NOT a refusal;
            # counting it separately is what makes the accounting balance.
            no_rows += 1
            continue
        for native in natives:
            try:
                tuples = module.project(native)
            except ProjectionError as exc:
                refused += 1
                refusals.append({"path": str(path), "schema": dispatch,
                                 "reason": str(exc)})
                continue
            emitted = to_frames(tuples, as_of=as_of,
                                adapter_id=getattr(module, "ADAPTER_ID", ADAPTER_ID),
                                authority=getattr(module, "AUTHORITY", None))
            frames.extend(emitted)
            projected += 1
            name = module.__name__.rsplit(".", 1)[-1]
            by_adapter[name] = by_adapter.get(name, 0) + 1
        if limit is not None and projected >= limit:
            break

    if not dry_run and frames:
        for frame in frames:
            ledger.append(frame)

    return {
        "root": str(root),
        "documents_matched": seen,
        "rows_projected": projected,
        "frames_emitted": len(frames),
        "refused": refused,
        # Schema matched this dispatcher's map but the adapter does not accept that
        # document as an entry point. A mapping miss, not a rederivation failure.
        "schema_not_an_entry_point": unaccepted,
        # Accepted, and deliberately projected nothing (pre-hook, void, non-measurement).
        "documents_yielding_no_rows": no_rows,
        "by_adapter": dict(sorted(by_adapter.items())),
        # Bounded: the point is to surface that refusals happened and what kind, not
        # to reproduce the whole corpus in a report.
        "refusal_sample": refusals[:20],
        "unwired_adapters": UNWIRED,
        "dry_run": dry_run,
    }
