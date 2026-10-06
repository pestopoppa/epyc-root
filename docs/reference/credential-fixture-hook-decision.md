# Credential-fixture scanner decision

**DECIDED 2026-10-06: operator chose 1B — keep both credential-redaction test files scanned.** The two proposed global whole-file exclusions are rejected and remain unapplied. No scanner exemption is granted.

`tests/unit/test_credential_redaction.py` and `tests/unit/test_credential_redaction_truncated_pem.py` remain subject to ordinary staged-blob scanning in every repository using the shared hook. Preserve the realistic regression literals; do not split or obscure them to evade scanning. Passing synthetic tests does not create policy authority.

The [rejected exact patch](../../artifacts/operator/decisions/TOC-RD-1a-credential-fixtures-20261006.patch) is retained unchanged as historical proposal evidence. It would have skipped both entire files, including future real credentials. SHA-256 `c26bd1965aa272a00e5f7595bd17ba0379de270b067c3cf67bc54cbfe6875df2`; the earlier static checks and `git apply --check` did not apply it. [ED25519 recognition](../../artifacts/ni07/run-37474797195/README.md) is separately completed and confers no fixture exception.

## Narrower route for a future concrete fixture edit

The existing `scripts/hooks/fixture_snapshot_provenance.py` reads exact staged Git blobs and validates reviewed hash/source identities plus complete native receipt/readset custody. Its candidates are copies under `artifacts/ni05/.../native-.../read-N.bin`; it does not exempt ordinary APP test-file edits. It currently registers the older credential-redaction fixture, not the truncated-PEM fixture. Extending the table alone would therefore not solve the APP editing workflow.

A future proposal must identify the actual blocked APP edit, review its exact synthetic bytes, and define an APP-side staged-content authorization bound to repository, immutable source revision and exact fixture hash. Changed or unknown content, an added credential, missing or ambiguous custody, wrong repository/revision/path, unsupported index mode and an unmerged index must retain ordinary scanning. Required controls include both exact fixtures, changed bytes, same-path unreviewed content, near-miss paths, wrong provenance and unrelated real-pattern credentials. No path or directory wildcard and no global whole-file skip.

This is preparation guidance, not an approved scanner-policy change. No content-based exception has been applied, and the settled 1B decision is not reopened. A concrete security-policy exception would require its own reviewed package before application.
