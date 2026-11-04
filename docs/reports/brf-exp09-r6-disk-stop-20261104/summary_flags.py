"""Pass-level predicates over either newly emitted or resumed native cell rows."""

def completion_flags(got):
    """Return (mechanism_fired, capture_complete) from (item, arm) -> cell records."""
    quote_rows = [
        rec for (item, arm), rec in got.items()
        if arm == "verified_quote"
    ]
    fired = bool(quote_rows) and all(
        rec.get("evidence", {}).get("planted_mismatch_rejected") is True for rec in quote_rows
    )
    captured = all(
        rec.get("view") is not None and rec.get("answer_raw") is not None
        for rec in got.values()
    )
    return fired, captured


def validate_completion(got, item_ids, arms, answer_cap=1024):
    """Return (valid, reasons) for the complete expected native-cell grid."""
    expected = {(item, arm) for item in item_ids for arm in arms}
    actual = set(got)
    reasons = []
    if not item_ids or len(set(item_ids)) != len(item_ids):
        reasons.append("manifest-item-ids-empty-or-duplicate")
    if len(arms) != 4 or len(set(arms)) != 4:
        reasons.append("arm-count-or-uniqueness")
    if actual != expected:
        reasons.append(f"grid-mismatch:expected={len(expected)} actual={len(actual)}")
    fired, captured = completion_flags(got)
    if not fired:
        reasons.append("mechanism-not-fired")
    if not captured:
        reasons.append("capture-incomplete")
    for key in sorted(actual & expected):
        rec = got[key]
        if rec.get("parsed") is not True:
            reasons.append(f"answer-unparsed:{key[0]}:{key[1]}")
        usage = (rec.get("answer_meta") or {}).get("usage") or {}
        tokens = usage.get("completion_tokens")
        if not isinstance(tokens, int) or tokens >= answer_cap:
            reasons.append(f"answer-cap-hit-or-unknown:{key[0]}:{key[1]}")
    return not reasons, reasons


def duplicate_cell_keys(rows):
    """List duplicate native (item, arm) keys without silently accepting overwrite."""
    seen = set()
    duplicates = set()
    for row in rows:
        if row.get("kind") != "cell":
            continue
        key = (row.get("item"), row.get("arm"))
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


FAILED_ID_REFERENCE_CAP = 10


def exact_failed_id_recall(answer, gold_failed_ids):
    """Report exact failed-ID recall, trimming whitespace only; never used for scoring."""
    refs = gold_failed_ids if isinstance(gold_failed_ids, list) else []
    refs = [value.strip() for value in refs[:FAILED_ID_REFERENCE_CAP]
            if isinstance(value, str) and value.strip()]
    predicted = answer.get("failed_ids") if isinstance(answer, dict) else None
    predicted = predicted if isinstance(predicted, list) else []
    predicted_ids = {value.strip() for value in predicted if isinstance(value, str) and value.strip()}
    hits = sum(reference in predicted_ids for reference in refs)
    return {
        "exact_failed_id_reference_count": len(refs),
        "exact_failed_id_hits": hits,
        "exact_failed_id_recall": round(hits / len(refs), 3) if refs else None,
        "exact_failed_id_reference_cap": FAILED_ID_REFERENCE_CAP,
    }


def completion_record(got, item_ids, arms, answer_cap=1024):
    """Build exactly one terminal summary kind: pass_complete or validation_incomplete."""
    valid, reasons = validate_completion(got, item_ids, arms, answer_cap=answer_cap)
    fired, captured = completion_flags(got)
    record = {
        "cells": len(got), "expected_cells": len(item_ids) * len(arms),
        "mechanism_fired": fired, "capture_complete": captured,
        "validation_reasons": reasons,
    }
    return ("pass_complete" if valid else "validation_incomplete"), record
