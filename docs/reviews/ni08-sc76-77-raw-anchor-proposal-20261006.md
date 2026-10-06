# SC76 / SC77 prospective raw-anchor provenance proposal

Status: private engineering proposal only. Based on epyc-root `621eed0927a1cae6bbcdfb73155ec91dff607153`; no source, index, ledger, or handoff has been changed. This proposal does not authorize a historical regrade or claim that any existing machine anchor has been re-verified.

## Current source finding

The active task is `SC76 (S3-VID-02)` and its dependent `SC77 (S3-VID-03)` in `handoffs/active/vidya-belief-substrate-program.md` at the pinned source commit. SC76 asks for quote re-verification against the original raw fetched artifact; SC77 asks that the literature adapter derive its traceability tier from that verification.

At this commit, `scripts/vidya/machine_anchor.py` (`05046e1d36f2b2b04fbbdaf341e85f4f0d70d9b003ae0440cd60cf10506a8380`) implements `fetch_text()` by reading response bytes, decoding with replacement, stripping markup, and returning only normalized text. For an arXiv `/abs/` or `/pdf/` input it strips a requested `vN` and fetches the unversioned `/abs/{id}` URL. It retains neither raw response bytes nor effective URL, redirect chain, content type, retrieval time, extractor identity, or a durable snapshot locator. `anchor_entry()` hashes `canonical.normalized_quote(quote)` and emits `quote_sha256`, `locator`, `located_by: machine`, and `verified_by`, but has no original-source binding.

`research_intake.py` (`16d62a85df95e47951d9e9f3424d0ee9d14a6f2b751b2be08c62eb9792c5261d`) projects these records. `_t_level()` caps `located_by: machine` at `MachineLocated` when a quote hash exists, while a non-machine anchor with a quote/locator, `quote_sha256`, and `source_revision` becomes `Attested`. This is a shape check, not source verification. The existing `literature` class and its one registered ladder are already the source authority; this change must not register another class or alter `grade_for_entry()` policy.

The research-intake skill at `.claude/skills/research-intake/SKILL.md` (`b070b1c79db3f72a7f1692f8425201f4231b7eb6449d617871ed447c168d418f`) requires raw Stage-2 artifacts to be fetched into `/mnt/raid0/llm/tmp/dive-*` and hashed before extraction. That scratch location is not a durable retained original. The skill also requires version-pinned arXiv HTML first and source route/revision recorded. The current machine fetcher diverges from that version-pinning policy.

## Bounded implementation shape

1. Add a prospective capture helper at the fetch/write boundary. It receives the exact response bytes from one read, computes SHA-256 over those bytes, and parses/extracts from that same in-memory byte string. It must not hash one fetch and parse a second fetch. Record the requested URL, effective URL after redirects, redirect chain when exposed by the transport, retrieval UTC, response media type, byte length, raw SHA-256, extractor name/version or source digest, and a stable snapshot ID. For arXiv, preserve the explicit `/html/{id}v{N}` requested revision and reject an unexpected unversioned redirect when exact version identity cannot be established; never silently downgrade to bare `/abs/{id}`.

2. Store the raw response as a content-addressed object beneath an explicitly configured durable private artifact root, named by its SHA-256. Create with exclusive/no-follow semantics, verify any pre-existing same-name object byte-for-byte, fsync file and parent directory, and refuse conflicting content. Require regular files, bounded size, restrictive directory/file permissions, and reject symlinks, path traversal, and root escape. A write-once file is not immutable against a privileged later edit; every read must recompute and compare the digest. Do not put copyrighted source bytes into public Git. If no approved durable private root is configured or retention is unavailable, keep the anchor descriptive and mark source verification unknown.

3. Extend each new machine anchor additively with an explicit `source_artifact` binding (schema version, snapshot ID/relative object path, raw SHA-256, byte length, requested/effective URL and source revision, retrieval time, media type, extractor ID/version or digest). Preserve existing anchor fields and quote hash semantics. `source_revision` must identify the exact observed version/route, not merely the submitted URL. The artifact reference is untrusted input until its root, path, file type, byte length, raw hash, extractor compatibility, and source metadata all validate.

4. Implement one shared re-verifier used by validation and SC77 tier projection. It resolves only the configured artifact root; it rejects absolute paths, `..`, symlink components, non-regular files, oversized data, missing objects, hash mismatch, unsupported schema, and extractor identity mismatch. It re-extracts from the retained raw bytes using the recorded extractor implementation/version, then requires the stored quote to be a substring of the extracted original and recomputes SHA-256 over `canonical.normalized_quote(quote)`. Do not treat a self-consistent quote/hash pair as verified when the original is absent. Any refusal yields an explicit unknown/unverified result, not a fabricated lower or higher warrant.

5. Tie SC77 to that result. Only a valid source-bound anchor may follow the existing `Attested` path for a human-authored anchor. A machine-authored anchor remains capped at `MachineLocated` even after successful re-verification; verification proves source identity and quote location, not semantic support. Missing/invalid evidence must not become `Attested` from `located_by` labels, `source_revision` strings, or hashes alone. Preserve the current single `literature` ladder and its other Q/T behavior.

6. Keep existing records immutable and non-authoritative for this new verifier unless they already have all required native source bindings and the original artifact is found and independently hash-verified. No network refetch may stand in for the historical original. Do not backfill artifact metadata, re-anchor, rewrite the intake index, mutate the Vidya ledger, retroactively change grades, or claim historical verification. Existing legacy anchors without retained raw sources report `unknown: original artifact unavailable`.

## Required hosted controls before any capture is considered

Controls should use disposable temporary roots and synthetic bytes, never the canonical index, ledger, real source network, or project runtime. The acceptance set must cover:

- successful write, close/reopen, raw digest and byte-length match, same-read parse binding, versioned arXiv URL retention, and exact normalized quote/hash re-verification;
- redirect/effective-URL metadata, explicit requested-versus-effective revision mismatch refusal, and extractor identity/version mismatch refusal;
- missing artifact, raw-byte tamper, quote absent, wrong quote hash, wrong raw digest, schema/version unknown, unsupported extractor, and malformed metadata all project unknown and never `Attested`;
- existing digest object is verified and reused idempotently; conflicting bytes, concurrent duplicate creation, symlink at root/file/component, traversal, non-regular file, oversized source, and unsafe permissions are rejected;
- human anchor with a valid raw binding can reach only the already-defined human tier; machine anchor remains `MachineLocated`; legacy human-shaped anchor with no original remains non-attested;
- regression confirms one `literature` ladder only, no change to source class registry, no mutation of old entry/ledger bytes, and no second hash/normalization implementation.

The capture receipt must identify exact source commit, changed paths and Git blob hashes, locked interpreter/dependency closure, selected test node IDs, and generated artifact member hashes. The tests must be hosted in the repository's accepted native carrier and pass through the existing shared grade projection; do not add a grader or report a hand-run local test as native evidence. Any eventual capture requires separate parent review of the exact workflow/readset before dispatch.

## Remaining concrete boundary

The one necessary policy choice is the approved durable private retention root and its retention/access policy. A private root avoids publishing source contents but needs an operator-owned retention guarantee; absent that guarantee the honest behavior is unknown, not a temporary-path citation. This decision does not block source-only implementation of schema, same-read hashing/parsing, refusal behavior, and synthetic tests. It does block claiming the current scratch directory is durable or issuing source-verification warrants from it.
