"""Pure current assertion-kind projection precondition shared by intake consumers."""

def validate_assertion_kinds(entry: dict) -> dict[int, dict]:
    """Validate explicit CURRENT assertion kinds; never infer a kind from prose.

    Binding uses the exact current UTF-8 key_claims text, without normalization.
    Legacy entries have no metadata and retain their existing projection.
    """
    import hashlib

    if "claim_assertion_kinds" not in entry:
        return {}
    records = entry["claim_assertion_kinds"]
    claims = entry.get("key_claims")
    if not isinstance(records, list) or not isinstance(claims, list):
        raise ValueError("claim_assertion_kinds and key_claims must be lists")
    out = {}
    for rec in records:
        if not isinstance(rec, dict):
            raise ValueError("claim_assertion_kinds record must be a mapping")
        i = rec.get("claim_index")
        if type(i) is not int or not 0 <= i < len(claims) or i in out:
            raise ValueError("claim_assertion_kinds requires unique valid integer claim_index")
        text = claims[i]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("claim_assertion_kinds must bind nonempty current claim text")
        if rec.get("kind") not in ("source_claim", "record_status"):
            raise ValueError("claim_assertion_kinds kind must be source_claim or record_status")
        digest = rec.get("current_claim_text_sha256")
        if not isinstance(digest, str) or digest != hashlib.sha256(text.encode("utf-8")).hexdigest():
            raise ValueError("claim_assertion_kinds current text SHA-256 binding mismatch")
        reason = rec.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("claim_assertion_kinds requires a nonempty reviewed reason")
        out[i] = rec
    return out


