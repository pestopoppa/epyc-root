# INF-12 Gate 2 checkpoint — r8 resume repair and smoke (2026-10-29)

[belief: cc]

## Scope

This checkpoint records the INF-12 failed-run repair and its READY submission. It does not close the full Gate 2 evaluation, make a quality decision, or claim full-population results.

## Failure and repair history

- **r6 granted run:** `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028-r7/outputs-r6-copy/20261028T225515Z-3137265/STATE.json` records `rc=75`, `partial=true`, and direct-child reap after its window. The subsequent resumed r6 run, `.../20261028T233953Z-3486732/`, failed with `ValueError: refusing resume row/identity index mismatch`. Inspection found multiple JSONL rows carrying the last loop's identity index rather than their own identity.
- **r7 attempts:** The 00:12 run ended partial (`rc=75`). In the 00:57 run, the evaluator wrote two valid-index base rows, then restarted with a newly generated wall-clock `{time_stamp}`. The changed prompt hash made the same logical rows appear new; it appended duplicates and failed final JSON/JSONL count validation (`json_jsonl_count_mismatch`, `rc=70`, 2 JSON records vs 4 JSONL rows). It did not inherit r6’s malformed row identities.
- **r8 repair:** In `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028-r8`, a result namespace now gets an atomically published, fsynced `EVALUATION-CONTEXT.json` bound to the run pin fingerprint. Its fixed timestamp is used in prompt construction and included in run/resume identity. Existing output without a valid context refuses. Resume validation rejects changed identity at the same logical row and duplicate logical identities; the aggregator checks the persisted context and row timestamps. Historical r6/r7 partial outputs remain separate and unchanged.

## Verification and smoke

- Targeted resume-identity tests: **14 passed**. Smoke-grant guard regressions cover current one-line grant records, malformed records, late grant arrival, STOP, hard cutoff, and foreign-child preservation. Normal-entry context and no-grant launcher checks passed; no job started without a grant. Source and runner manifest checks matched.
- Actual same-launcher r8 smoke: `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028-r8/launch.sh --smoke`, through the exclusive `gpu-quiet` path and taskset 184–185. Run `20261029T011224Z-215148` ended **rc 0**, 190 seconds wall / 130.681 seconds real generation. Each arm evaluated two real questions, restarted, and resumed the same two rows. Base and Delta JSON/JSONL outputs persisted with identities 0 and 1 and unchanged hashes across restart. Captured KFD/HIP and external per-process VRAM samples show positive VRAM during both first-pass arms and both resume subprocesses.
- State records direct-child cleanup only (`direct_child_reaped=true`, `descendants_censused=false`). No descendant-census claim is made.

## READY submission and remaining scope

The READY pair was published at:

- `/mnt/raid0/llm/tmp/compute-flags/ready/codex-ni-inf12-gate2-triton36-r8-20261029.json`
- `/mnt/raid0/llm/tmp/compute-flags/ready/codex-ni-inf12-gate2-triton36-r8-20261029.row.md`

The manifest is diagnostic: it describes the complete pinned population as the scheduled job, but the smoke itself covers only two questions per arm. Full Gate 2 remains open: 22 sources and enrolled rows still need to be collected and summarized. The READY hashes bind the r8 launcher, job, source/model/data/runtime manifests, smoke outputs, and residency evidence; the seven external symlink targets are listed for retention. This session wrote no grant, queue entry, receipt, or diagnostic seal.

At 2026-10-29 01:21:29 UTC, the keeper had accepted the row and moved its manifest to `ready/armed/` (`READY-RESULT ... QUEUED`, launcher PID 299268). The launcher logged `START` at 01:20:52Z, passed the normal-grant resource check and entered the exclusive GPU lock at 01:20:52Z; the first full-run base arm started at 01:21:11Z. It was still running at the observation time; this is not a completion or Gate 2 result.
