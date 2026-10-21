"""The PRE-P1-A `claim_tuple.to_frames`, frozen verbatim (origin/main 3f756e6cf, 2026-10-21).

The loop-belief redesign (P1-A) added a conditional `observation` emission to the evidence frame.
Its contract is that every tuple WITHOUT an observation emits the byte-identical frames -- and so
the identical frame ids -- it emitted before. The only honest "before" is the old code itself, so
it is kept here, unchanged, as the reference the byte-identity checks compare against
(`test_claim_tuple.py` and the session-wide recorder in `conftest.py`). Never edit the body.
"""
from __future__ import annotations


def legacy_to_frames(tup, *, as_of: str, adapter_id: str,
                     authority: str = "measurement") -> list[dict]:
    from claim_tuple import grade
    from frames import make_frame

    q, t, reasons = grade(tup)
    ident = tup.measurement_id
    source_id, claim_id = f"src_{ident}", f"clm_{ident}"
    claim_assertion = {"claim_id": claim_id, "display_text": tup.claim, "source_id": source_id}
    if tup.decided_proposition:
        claim_assertion["decided_proposition"] = tup.decided_proposition
    if tup.binding_kind:
        claim_assertion["binding_kind"] = tup.binding_kind
    if tup.binding_ref:
        claim_assertion["binding_ref"] = tup.binding_ref
    source_assertion = {"source_id": source_id,
                        "locator": tup.attestation_locator or tup.attestation_path or f"measurement:{ident}",
                        "source_kind": tup.source_kind, "title": tup.metric,
                        "revision_observed": tup.date}
    if tup.applicability:
        source_assertion["applicability"] = dict(tup.applicability)
    return [
        make_frame(
            frame_type="epyc.vidya/frame/source_observed/v1",
            assertion=source_assertion,
            provenance={"method": adapter_id, "about": ident, "retrofit": False},
            actor=adapter_id, authority_scope=authority, created_at=as_of),
        make_frame(
            frame_type="epyc.vidya/frame/claim_proposed/v1",
            assertion=claim_assertion,
            provenance={"method": adapter_id, "derived_from": source_id, "about": ident},
            actor=adapter_id, authority_scope=authority, created_at=as_of),
        make_frame(
            frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
            assertion={"claim_id": claim_id, "evidence_id": f"evd_{ident}",
                       "grade": {"Q": q, "T": t}, "source_id": source_id,
                       "protocol_id": tup.protocol_id, "reps": tup.reps,
                       "category": tup.category, "metric_direction": tup.metric_direction},
            provenance={"evidence": f"evd_{ident}", "about": claim_id, "method": adapter_id,
                        "grade_reasons": reasons, "reps_basis": tup.reps_basis},
            actor=adapter_id, authority_scope=authority, created_at=as_of),
    ]


def outcome(fn, tup, **kw):
    """(\"ok\", canonical bytes) or (\"raise\", exception type and message): both doors must agree
    on failure too, or an emission that started raising would pass as 'not compared'."""
    from canonical import canonical_bytes

    try:
        return ("ok", canonical_bytes(fn(tup, **kw)))
    except Exception as exc:  # noqa: BLE001
        return ("raise", f"{type(exc).__name__}: {exc}")
