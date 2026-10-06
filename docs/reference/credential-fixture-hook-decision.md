# Credential-fixture scanner exception: operator choice

TOC-RD-1a explicitly reserves the fixture exception as an operator decision. The ED25519 recognition child is complete; this proposal remains unapplied.

The [exact two-entry patch](../../artifacts/operator/decisions/TOC-RD-1a-credential-fixtures-20261006.patch) exempts `tests/unit/test_credential_redaction.py` and `tests/unit/test_credential_redaction_truncated_pem.py` from the shared staged-blob scanner. These exact repo-relative patterns apply in any repository using the hook. They skip the entire matching file, so a future real token or key anywhere inside it would also evade this scanner. No wildcard is proposed.

Approve these two exact exclusions to preserve the deliberate credential-shaped regression literals, or retain scanning and leave those literal-fixture edits blocked. The hook's existing rationale rejects hiding credential literals by splitting the existing APP fixtures. MAIN recommends an explicit choice; passing synthetic tests confer no exemption or privacy authority. Any approved implementation must add exact-path and nonallowlisted/near-miss staged-index controls before promotion.

The corrected patch passed `git apply --check` without application and static exact/near-miss regex checks. SHA-256 `c26bd1965aa272a00e5f7595bd17ba0379de270b067c3cf67bc54cbfe6875df2`. Original [ED25519 synthetic evidence](../../artifacts/ni07/run-37474797195/README.md) does not include this exception.
