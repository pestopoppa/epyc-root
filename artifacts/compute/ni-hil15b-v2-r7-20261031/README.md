# HIL15b-v2 canonical R7 READY source capsule — 2026-10-31

This is the final canonical R7 source and bounded qualification proof for `codex-ni-hil15b-v2-native60-r7-20261031`. It preserves the 20-task frozen set and warrants, one native Python process for all 60 attempts, the original driver integration, source/model pins, same-entry noncohort qualification, and model-free cutoff accounting. The 77 KiB APP Git bundle and multi-megabyte filler review logs are intentionally omitted; APP source is already in its own history and those logs are not part of the candidate proof.

## Candidate and scope

The READY requests one 8-hour any-CPU-quarter window with at least 6.5 useful hours, 48 GiB, one original 20-task × 3-repeats native cohort, max wall 21,600 seconds, no redraw, and parent HIL-15b remains OPEN until full assessment. The earlier per-slot client-reset diagnostic was withdrawn before any frozen attempt or grant. No frozen HIL15b task has been exposed by prior packets.

Canonical driver SHA-256 is `75abff0842a550051b3a25f3bf079a505044120a9ee57e80cc08ef2661bb4c63`; frozen taskset SHA-256 is `0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312`. `R7-SHAPE-PROOF.json` records one `live_deps`, one `run_all`, and one `LLMPrimitives` construction site, with the native repeat loop unchanged. `SOURCE-PINS.json` and `R7-SHA256SUMS` retain the source identities. The native full cohort entry, scoring guardrails, task assets, and READY row/manifest are preserved beside this README.

## Qualification proof and limits

The R7 noncohort qualification passed on SMT 128–129 in 236.7 seconds (rounded 241-second total): one request returned `391`, one step-bearing run joined to one outcome (1/1), L2 writer rc 0, replay rc 0/clean, and `content_cache=False`. The serving PID `1282968` was checked after cleanup; `pid-check.stderr` records `ps_exit=1` and stdout is empty. Linkage resolved to the frozen production CPU store. This proves transport/writer readiness only; it is not a frozen task attempt, empirical difficulty result, or quality verdict. The single-class qualification had insufficient AUC and correctly skipped the AUC sidecar.

The model-free cutoff control returned rc 75 with `partial=true`, original denominator 60, 0 complete, 1 exposed-incomplete UNKNOWN, and 59 unexposed. The full R7 job reports a partial original denominator honestly and makes no partial quality claim. No performance, adoption, or equivalence claim is made.

## Contents and verification

`qualification-native-r7/` contains the assessment, invocation, source-head, linkage, server and native logs, native attempt ledger, and minimal native output manifest/L2/replay artifacts. `ready/` contains the actual R7 READY JSON, queue row and smoke log. The 77 KiB APP bundle is omitted as redundant with APP source history. `CAPSULE-SHA256.json` records every included file's digest and byte count, plus the process-death probe. The original source checksum list remains at `R7-SHA256SUMS`; the capsule manifest provides local paths for exact verification.
