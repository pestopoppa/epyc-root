"""SC20 strict read side for the memento LoRA/SFT training belief row.

The producer (``memento_sft.py``, ``emit_training_belief``) writes ONE
``stage{stage}_belief_measurements.json`` beside the run record at train-stage
finalize — protocol ``epyc.memento_sft.lora_training.v1``. This reader PROJECTS
that row into the canonical :class:`ClaimTuple`; ``claim_tuple.grade()`` decides.
The reader never reconstructs a row from the run record or the adapter — a tuple
invented on read would claim an s/sample and an integrity verdict the run never
captured (the DF2-4 / ``benchmarks/results`` precedent).

THE CLAIM IS NARROW ON PURPOSE (the register contract): **"this configuration
trains at X s/sample with an adapter that provably updated"** — and NOTHING more.
It never claims "the model improved": SFT throughput and gradient movement say
nothing about post-training quality, which the MATH-500 gate decides separately.
The claim text carries this scope verbatim and the reader refuses any artifact
whose claim omits it.

Fail-closed on the producer's own fail-closed contract:
* protocol id must be ``epyc.memento_sft.lora_training.v1``;
* the integrity block must exist and must show a provably-updated adapter
  (``lora_B_total > 0`` and ``lora_B_nonzero == lora_B_total``; all tensors
  finite) — a refusal artifact (the producer's BeliefRefused path) projects
  ZERO rows, because the claim's second half is false;
* ``reps >= 1`` (zero scored samples is not a measurement);
* the attestation is recomputed on read: sha256 over the RUN RECORD content
  (``stage{stage}_metrics.json``, whose path the row pins as
  ``attestation_path``) must equal the row's ``attestation_sha256`` — a mismatch
  means the record the claim pins has moved; fail closed, zero rows.

Attestation honesty: the metrics file lives in the research repo's ``output/``
tree, which is NOT tracked by git, so the honest grade is ``Witnessed/Anchored``
(never ``Attested`` — there is no pinned revision to attest against).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

SOURCE_KIND = "memento-lora-training"
ADAPTER_ID = "vidya.adapters.memento_lora"
AUTHORITY = "measurement"
PROTOCOL_ID = "epyc.memento_sft.lora_training.v1"
SCOPE_CLAUSE = ("this configuration trains at X s/sample with an adapter that "
                "provably updated; never a claim about model quality")


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _content_hash(obj) -> str:
    """Canonical hash, byte-identical to the producer's own ``_content_hash``."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def refusal_reason(belief_path: str | Path) -> str | None:
    """Why this belief file cannot be projected, or None if it can."""
    path = Path(belief_path)
    if not path.exists():
        return "no emissions"
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"malformed belief JSON: {exc}"
    if not isinstance(row, dict):
        return "belief row is not an object"
    if row.get("protocol_id") != PROTOCOL_ID:
        return f"protocol mismatch: {row.get('protocol_id')!r} != {PROTOCOL_ID!r}"

    # The producer self-hashes the row (measurement_sha256 over the canonical
    # encoding of the row BEFORE the hash key was added). A row that does not
    # re-derive has been mutated since emit — fail closed.
    row_without_hash = {k: v for k, v in row.items() if k != "measurement_sha256"}
    recorded_hash = row.get("measurement_sha256") or ""
    if not recorded_hash or _content_hash(row_without_hash) != recorded_hash:
        return "measurement_sha256 mismatch — the row was mutated since emit"

    integrity = row.get("extra", {}).get("adapter_integrity")
    if not isinstance(integrity, dict):
        return "missing adapter_integrity block"
    total = integrity.get("lora_B_total")
    nonzero = integrity.get("lora_B_nonzero")
    if not isinstance(total, int) or total < 1:
        return "lora_B_total < 1 — the adapter did not provably update (producer refusal artifact)"
    if not isinstance(nonzero, int) or nonzero != total:
        return f"lora_B off zero-init: {nonzero}/{total} — the adapter did not provably update"
    if integrity.get("all_tensors_finite") is not True:
        return "all_tensors_finite is not true"

    try:
        reps = int(row.get("reps", 0))
    except (TypeError, ValueError):
        reps = 0
    if reps < 1:
        return "reps < 1 — zero scored samples is not a measurement"

    # Attestation recompute over the pinned run record. The producer nests the
    # attestation fields inside ``extra`` (verified against the emitted row,
    # 2026-08-27); top-level is tolerated for forward/backward shape changes.
    extra = row.get("extra") or {}
    locator = extra.get("attestation_locator") or row.get("attestation_locator") or ""
    pinned = extra.get("attestation_path") or row.get("attestation_path") or ""
    recorded = extra.get("attestation_sha256") or row.get("attestation_sha256") or ""
    if not pinned or not recorded:
        return "missing attestation path or sha256"
    record_path = Path(pinned)
    if not record_path.exists():
        return f"attestation target missing: {pinned}"
    # The producer attests the CANONICAL CONTENT of the metrics dict (its own
    # _content_hash over the parsed record), not the file bytes — the file on
    # disk is json.dumps(..., indent=2), which would never re-derive. A record
    # edited in content still fails: the canonical hash moves with the dict.
    try:
        record_content = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"attestation target unreadable: {exc}"
    actual = _content_hash(record_content)
    if actual != recorded:
        return (f"attestation mismatch: run record {locator} hashed "
                f"{actual[:12]}…, row pins {recorded[:12]}… — the pinned record moved")

    # Scope clause must ride in the claim.
    claim = row.get("claim") or ""
    if "provably updated" not in claim:
        return "claim omits the provably-updated scope clause"
    return None


def native_rows(belief_path: str | Path) -> tuple[dict, ...]:
    """One native row: the producer-authored belief row, retained intact."""
    path = Path(belief_path)
    reason = refusal_reason(path)
    if reason:
        raise ProjectionError(f"memento belief not projectable: {reason}")
    return (json.loads(path.read_text(encoding="utf-8")),)


def frames_for_records(belief_path: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (``claim_tuple.to_frames``)."""
    frames: list[dict] = []
    for native in native_rows(belief_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Revalidates so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict):
        raise ProjectionError("memento belief native must be the producer row")
    # Full revalidation — the same checks as refusal_reason, so a caller that
    # skips the gate still cannot project a refusal artifact.
    if native.get("protocol_id") != PROTOCOL_ID:
        raise ProjectionError("not a memento lora-training belief row")
    integrity = native.get("extra", {}).get("adapter_integrity") or {}
    if integrity.get("lora_B_total") != integrity.get("lora_B_nonzero") or \
            not integrity.get("lora_B_total"):
        raise ProjectionError("adapter did not provably update — refusal artifact")

    try:
        value = float(native["value"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"value is not a number: {exc!r}") from exc
    if value <= 0:
        raise ProjectionError("non-positive s/sample is not a measurement")

    claim = native.get("claim") or ""
    if "provably updated" not in claim:
        raise ProjectionError("claim omits the provably-updated scope clause")

    extra = dict(native.get("extra") or {})
    extra["scope"] = SCOPE_CLAUSE
    extra["measurement_id"] = native.get("measurement_id")
    extra["loss_quarters"] = native.get("extra", {}).get("loss_quarters")
    extra["loss_first"] = native.get("extra", {}).get("loss_first")
    extra["loss_last"] = native.get("extra", {}).get("loss_last")

    n_extra = native.get("extra") or {}
    return ClaimTuple(
        measurement_id=native.get("measurement_id") or "memento_sft_stage",
        metric=native.get("metric") or "sft_seconds_per_sample",
        value=value,
        unit=native.get("unit") or "s/sample",
        metric_direction=native.get("metric_direction") or "lower_better",
        category=native.get("category") or "BASELINE",
        claim=claim,
        protocol_id=native.get("protocol_id") or PROTOCOL_ID,
        reps=int(native.get("reps") or 0),
        reps_basis=native.get("reps_basis") or "",
        date=n_extra.get("date") or "",
        attestation_path=n_extra.get("attestation_path") or "",
        attestation_sha256=n_extra.get("attestation_sha256") or "",
        attestation_locator=n_extra.get("attestation_locator") or "",
        attestation_present=True,
        source_kind=SOURCE_KIND,
        extra=extra,
    )
