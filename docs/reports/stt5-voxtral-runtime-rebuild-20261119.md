# Voxtral traced-runtime restoration — 2026-11-19

CS-8.STT5: published `stt5-voxtral-traced-runtime-rebuild-r1-20261119`.
Publisher **SMOKE PASS** on CPUs 116–119 at 15:26:19Z: a fresh traced ELF
object satisfied the native witness predicate, followed by clean stop rc75.
The full build is pending. No audio or model was opened by this build.

The historical 480/960 ms executables and Q8 weights are absent at their pinned
paths. Original CrispASR source `2aa8d7669fcaa18d98d61a4bc8a077464e6b9919`
remains in the existing clean source worktree. The build reuses it read-only,
checks its commit/diff/untracked state plus the ggml/c2pa commits and clean
state, and pins the retained 480/960 ms trace backends and 960 ms model overlay.
Fresh smoke and grant build directories are separate. It compiles the trace
backends, builds the complete CPU CLI, substitutes the 960 ms model archive
into its library and executable links, checks all three native token witnesses,
and emits final executable/library SHA-256 identities. Unknown link arguments
refuse rather than silently falling back. STOP/deadline drains only the captured
compiler session using the existing independent-runner helper. The publisher's
new-session warning is accounted for: subprocesses inherit the full environment,
including FILLER_ID, and owned compiler sessions are explicitly drained.

Eight model-free restoration controls pass: exact linker replacement, compile
recipe flag/cwd preservation, ambiguous/missing/malformed recipe refusal,
submodule drift/dirty refusal, parent-pin failure propagation and compiled
witness presence. Shared owned-session drain regression checks also pass.

These will be NEW runtime identities, not restoration of the historical binary
hashes. Full build completion proves neither historical byte identity nor
public-fixture parity. Restore the original Q8 model by its recorded revision
and digest, then obtain public-JFK native-token parity before any validation
continuation. Keep the existing 10 results and 11 exposures, including one
exposed UNKNOWN, immutable; never redraw or relabel old receipts with new source
or runtime hashes. CS-8.STT5 remains open; no WER, rate, test or promotion verdict.

Evidence is referenced in place; no logs, source trees or binaries copied into
repository evidence directories. Prepared inputs and publisher receipt:

- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/config.json` SHA-256 `cbab09525f9fcc6501eb35aa107dfe2f0de910a6d5c8f5bc046bb129c6eec5b5`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/spec.json` SHA-256 `b073a2a2366d1b72d9e59be5b29d41e0566039dc2542ff05c5e9b61f8f1c860c`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/stt5_voxtral_restore.py` SHA-256 `283a4b912c891bda7e7d821277e899c4a058d02d32e55fc679af71b035608226`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/stt5_transcribe_restore.py` SHA-256 `f0c75857f6bc932d3dca737081ccb17f4f03e6bfe37d57ef80555f216f580d03`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/stt5-voxtral-traced-runtime-rebuild-r1-20261119/PASS.json` SHA-256 `8602cce4f85272a19fb2ce238efdb863e0ac0290e93f9722dc8bfeb9b04d6134`.
