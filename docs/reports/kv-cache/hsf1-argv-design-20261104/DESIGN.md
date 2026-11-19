# HSF-1 receipt design17 (source-only)

This is a review artifact only. It changes no orchestrator or lane target and
produces no launch/measurement evidence.

## Optional effective argv privacy design

This candidate has the producer pass the exact final argv vector that it supplies to
`subprocess.Popen` after argument construction. The receipt builder serializes
that ordered vector as compact UTF-8 JSON and uses an injected
`encrypt_argv(bytes) -> (key_id, ciphertext_bytes)` provider. The intended
provider uses authenticated envelope encryption for an authorized audit
recipient, with the private key held outside the receipt store. Persisted fields
contain the key identifier, opaque ciphertext, and a ciphertext digest. No
plaintext argv, redacted argv, or unkeyed digest of plaintext argv is persisted.
The digest validates the captured envelope; it is not an argv fingerprint and
does not permit recovery without decryption authority.

If this design is selected, the integration owner must select and validate the concrete encryption
provider, recipient/key rotation and access policy before production use. The
unit tests inject a deliberately fake provider only to check that the complete
argv bytes cross the encryption boundary and that receipt output contains no
plaintext. They do not validate cryptography, key custody, or integration
correctness.

## Durability

Receipt content is flushed and fsynced before its immutable no-overwrite hard
link is published. The containing directory is fsynced after publication so
the new name is covered by the durability boundary. A directory-fsync error is
surfaced to the caller.

## Offline check

`python3 test_receipt.py` passes 3 source-only tests: encrypted capture shape
and plaintext exclusion, envelope validation, and writer file/directory fsync
plus no-overwrite behavior.

This is one optional design, not a selected project-wide encryption or key-management policy. No production integration or deployment has occurred.
