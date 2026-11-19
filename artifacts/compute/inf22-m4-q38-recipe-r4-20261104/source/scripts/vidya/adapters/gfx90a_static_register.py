"""Read gfx90a static register/ISA audit documents (SC84 VB-VGPR-STATIC + SC84a widening).

The producer is ``epyc-inference-research`` ``scripts/kernel_rnd/gfx90a_isa_audit.py``
(schema ``epyc.gfx90a.isa_audit.v1``, research ``e603216f``). Zero-GPU reads of existing
binaries: per kernel instance, the AMDGPU ``.note`` register counts, spills, private bytes and
the hot-loop ISA counts (in-loop spill reloads, ``v_accvgpr_*`` copies), with the toolchain id
and MFMA-form regime recorded per document.

This reader loads that producer pinned by sha256 (the hashed bytes are the executed bytes) and
uses ITS ``claim_projection``, so writer and reader share one definition of a claim. It adds
the checks the producer leaves to the reader: every row must re-derive its ``self_sha256``,
row identity must be unique and bound to the document's binary, and a governed document must
carry the fields a claim is made of. Any failure refuses the whole document.

Absence is recorded, never filled (spec §4.7): a document that states no ``category`` (every
audit written before the write-side hook, including the 2026-09-26 artifacts) yields zero rows
and never loads the producer. One tuple per (kernel row, metric); stub rows and absent metrics
yield nothing. The adapter projects; ``claim_tuple.grade()`` alone decides (``protocol_id`` is
empty, so every tuple is an OBSERVATION: register counts, never throughput).
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import CATEGORIES, ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.gfx90a_static_register/v1"
AUTHORITY = "measurement"
SCHEMA = "epyc.gfx90a.isa_audit.v1"
#: the producer's claim_projection stamps its schema as the tuple's source kind
SOURCE_KIND = SCHEMA
DEFAULT_PRODUCER = Path(
    "/workspace/repos/epyc-inference-research/scripts/kernel_rnd/gfx90a_isa_audit.py")
PRODUCER_SHA256 = "a26dd2c1cb19f8d5a4cadbbfff176dbf0e729cc590f8ce0e1af0cb4bf277fcae"  # e603216f

#: exactly the keyword set the pinned claim_projection emits; anything else is refused
_NATIVE_KEYS = frozenset({
    "measurement_id", "metric", "value", "unit", "date", "category", "metric_direction",
    "protocol_id", "reps", "reps_basis", "claim", "attestation_path", "attestation_sha256",
    "attestation_locator", "attestation_present", "source_kind", "extra"})
_DOC_KEYS = ("tool_id", "tool_sha256", "created_utc", "toolchain", "mfma_form_regime",
             "source", "n_rows", "rows")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _producer(path: str | Path | None = None) -> ModuleType:
    source = Path(path or DEFAULT_PRODUCER)
    try:
        metadata = source.stat()
        data = source.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"reviewed gfx90a ISA-audit producer unavailable: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ProjectionError("gfx90a ISA-audit producer must be a regular file")
    if hashlib.sha256(data).hexdigest() != PRODUCER_SHA256:
        raise ProjectionError("gfx90a ISA-audit producer differs from reviewed bytes")
    name = "_epyc_gfx90a_isa_audit"
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(source)
    # The producer defines dataclasses under `from __future__ import annotations`, which resolve
    # their module through sys.modules: register before executing the hashed bytes.
    sys.modules[name] = module
    try:
        exec(compile(data, str(source), "exec"), module.__dict__)  # noqa: S102 -- pinned bytes
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(f"gfx90a ISA-audit producer cannot be loaded: {exc}") from exc
    return module


def _load(path: Path) -> tuple[bytes, Any]:
    try:
        raw = path.read_bytes()
        doc = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
    except (OSError, ValueError, EOFError) as exc:
        raise ProjectionError(f"unreadable gfx90a audit document: {exc}") from exc
    return raw, doc


def _check_doc(doc: dict) -> None:
    missing = [key for key in _DOC_KEYS if key not in doc]
    if missing:
        raise ProjectionError(f"governed gfx90a audit lacks {missing}")
    if doc["category"] not in CATEGORIES:
        raise ProjectionError(f"gfx90a audit states an unknown category {doc['category']!r}")
    if not isinstance(doc["created_utc"], str) or len(doc["created_utc"]) < 10:
        raise ProjectionError("governed gfx90a audit has no creation date")
    if not isinstance(doc["rows"], list) or doc["n_rows"] != len(doc["rows"]):
        raise ProjectionError("gfx90a audit row count does not match its rows")
    if not isinstance(doc["source"], dict) or not doc["source"].get("sha256"):
        raise ProjectionError("gfx90a audit names no binary digest")
    for key in ("toolchain", "mfma_form_regime"):
        if not isinstance(doc[key], list) or not doc[key]:
            raise ProjectionError(f"gfx90a audit {key} is not a non-empty list")


def native_rows(path: str | Path, *, producer_path: str | Path | None = None) -> list[dict]:
    """Per-metric claim kwargs for every non-stub row of one governed audit document."""
    path = Path(path)
    raw, doc = _load(path)
    if not isinstance(doc, dict):
        raise ProjectionError("gfx90a audit document is not a JSON object")
    if doc.get("schema") != SCHEMA:
        return []  # foreign document: declined, never coerced
    if doc.get("category") is None:
        return []  # pre-hook audit: no claim identity was stated, so none is invented
    _check_doc(doc)
    module = _producer(producer_path)
    sha = hashlib.sha256(raw).hexdigest()
    seen: set[str] = set()
    out: list[dict] = []
    for row in doc["rows"]:
        if not isinstance(row, dict) or row.get("schema") != SCHEMA:
            raise ProjectionError("foreign row inside gfx90a audit document")
        body = {k: v for k, v in row.items() if k != "self_sha256"}
        try:
            derived = hashlib.sha256(module.canonical(body)).hexdigest()
        except (TypeError, ValueError) as exc:
            raise ProjectionError(f"gfx90a audit row not canonicalizable: {exc}") from exc
        if derived != row.get("self_sha256"):
            raise ProjectionError(f"row {row.get('row_id')} does not re-derive its self_sha256")
        if row.get("row_id") in seen:
            raise ProjectionError(f"gfx90a audit duplicates row {row.get('row_id')}")
        seen.add(row.get("row_id"))
        if row.get("binary_sha256") != doc["source"]["sha256"]:
            raise ProjectionError(f"row {row.get('row_id')} is not a row of the audited binary")
        try:
            out.extend(module.claim_projection(row, doc, attestation_path=str(path),
                                               attestation_sha256=sha))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectionError(f"row {row.get('row_id')} lacks a claim field: {exc}") from exc
    return out


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict):
        raise ProjectionError("gfx90a static register native row missing")
    keys = set(native)
    if keys != _NATIVE_KEYS:
        raise ProjectionError(
            f"gfx90a static register row shape differs from the pinned producer: "
            f"missing {sorted(_NATIVE_KEYS - keys)}, unexpected {sorted(keys - _NATIVE_KEYS)}")
    if native["source_kind"] != SOURCE_KIND:
        raise ProjectionError("wrong source class for gfx90a static register reads")
    if native["protocol_id"] != "":
        raise ProjectionError("gfx90a static register reads have no codified protocol")
    value = native["value"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProjectionError(f"gfx90a static register value is not a count: {value!r}")
    extra = native["extra"]
    if not isinstance(extra, dict) or extra.get("schema") != SCHEMA:
        raise ProjectionError("gfx90a static register row carries no producer provenance")
    # Presence and the digest are re-derived here, never taken from the row: the producer
    # stamps attestation_present=True at read time, which says nothing about the disk now.
    attestation = Path(native["attestation_path"] or "")
    present = attestation.is_file()
    verified = None
    if present:
        if _sha256(attestation) != native["attestation_sha256"]:
            raise ProjectionError("gfx90a audit document changed since it was read")
        verified = True
    fields = dict(native, attestation_present=present, attestation_verified=verified)
    try:
        return ClaimTuple(**fields)
    except (ValueError, TypeError) as exc:
        raise ProjectionError(f"gfx90a static register read refused: {exc}") from exc
