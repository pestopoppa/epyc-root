# HSF-1 receipt preparation 20

**Review-only proposal.** This folder is an isolated copy prepared from the repository candidate; it does not alter the candidate, the orchestrator, any lane, or any external repository. It is not an HSF-1 producer, launch receipt, measurement, or acceptance claim. No model/process launch occurred.

## Review changes

- Made test import relative to the test file so the copy can run from any checkout/location without relying on the obsolete `hsf1-next15` absolute path.
- Retained no-plaintext argv capture. `argv_sha256` hashes the original effective argv list encoded as compact UTF-8 JSON before it is discarded, so it binds the effective list rather than a redacted rendering.
- Added machine-readable digest contract fields that explicitly state SHA-256 is unkeyed and may permit guessing low-entropy secret-bearing argv values. This is a limitation statement, not a secrecy guarantee or a proposed encryption requirement.
- Fsync the destination directory after atomic no-overwrite publication, in addition to fsyncing file content.

## Offline checks

Run from this directory: `python3 test_receipt.py` (5 tests pass) and `python3 -m py_compile receipt.py test_receipt.py` (pass). Tests cover successful phase durations and custody, hot/unknown cache classification, spawn failure, phase ordering and required failure metadata, secret value omission with effective-argv digest sensitivity, and atomic no-overwrite writing.

These are unit checks of this isolated draft only. Integration still requires source-bound review of the real lifecycle event/parser and owner integration; this packet does not prove runtime capture or receipt completeness.

The retained digest binds an argv representation but does not capture the effective argv as the handoff requires. The unkeyed digest is not a secrecy mechanism. The copied code is not integrated or deployed.
