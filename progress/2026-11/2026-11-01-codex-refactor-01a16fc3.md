# Codex refactor session — 2026-11-01

- Withdrew the 19 dead-launcher STALE-ARMED rows owned by `codex-refactor-01a16fc3`; moved the one additional `refactor`-owned C6 IQKFA row to BACKLOG with a LOOP-49 plus >=12 GiB RSS hold, removed its quarter queue entry, and verified its exact launcher PID was dead. Post-action owner queue count: 0 STALE-ARMED. Fleetwide scope remains with other owners. Evidence: [withdrawal record](../../artifacts/engineering/refactor-stale-armed-withdrawal-20261101/RESULT.md).
- Reopened S0-V34-LOCK-LOSS-REPRODUCER after audit found no implementation SHA, committed artifact, test, or receipt supporting its prior tick. The historical prose remains as context, not completion evidence.
- LOOP-50 implementation is present in commit `24975d5d55d35fb8314cda9562a9712f2601b534`; blocking pre-commit hook regression suite passed. The task-line evidence and hook gate are being reconciled in this lane.
- LOOP-49 implementation candidate is under review. Independent review identified qualification/production placement mismatch, keeper grant-path hard-gate gaps, and insufficient receipt/grant integration coverage; these are being repaired before any CPU qualification grant.

- LOOP-50 replay initially exposed a false positive: its failure-state words were in the task specification, not the completion evidence. Fixed evidence-clause parsing in `8dd30dc08` and added `tests/test_belief_capture_check.py`; all three controls, collectability, committed-range replay and the full pre-commit wrapper regression passed.

- Reopened `S0-V34-LOCK-LOSS-REPRODUCER` after the tick audit found no SHA, Git artifact, test or receipt for the old completion assertion. The audit is linked from the owning handoff; the historical prose is explicitly non-evidentiary.

### A4A C4/27B budget repair — 2026-11-01

- Reviewed retained pair evidence and prepared successor `refactor-a4a-c4-27b-pair-r2-20261101`. Its proposed full-pair envelope is **7,500 s**: two provisional 3,600 s actor-call caps, 180 s cutoff/teardown margin, and 120 s orchestration/reader slack. Comparable treatment decode observations were 25.72 and 27.58 tok/s; 25.72 tok/s × 3,600 s = 92,592 tokens only under continuous decode, not an output or completion estimate. Remaining task/tool work is unknown. The corrected manifest uses `native-diagnostic`: two model-free fixture items with the exact completion-predicate command SHA-256 pinned; its qualification projection uses two CPUs and no GPU-quiet lock, disjoint from production CPUs. This profile makes no model/throughput claim; earlier model-free 40 tok/s fields have been removed. Production still requires the exact MI210 GPU region (`mi210_0,184-191`) and exclusive GPU quiet. Actual keeper qualification remains **NOT_RUN** because CPU locks were unavailable, no qualification receipt exists, and the candidate remains unqualified / **NOT_READY**; static checks and candidate dry-run also remain **NOT_RUN** (q3 occupied; q0–q2 occupied). [Packet](</mnt/raid0/llm/tmp/refactor-a4a-c4-27b-pair-successor-20261101/READY-CANDIDATE.md>).

### CS8.STT7 resume packet — 2026-11-01

- Prepared revised raw-prediction producer resume packet for 1,842 VoxPopuli items × four arms. Empty hypotheses against nonempty references are recorded as item WER=1.0; nonempty hypotheses remain unscored by this producer. Retained records cover 3,450/7,368 predictions; resume starts at index 862 and preserves intact records without redrawing corpus/audio. Retained-rate RTF forecast is 3,809 s; the proposed 9,000 s window budgets 2× forecast plus 1,200 s startup/validation/stop-drain reserve, rounded up, and is not a completion guarantee. Offline admission passed (`ADMIT_PASS`, no production grant, grant polling, or inference), while keeper-side LOOP49 native-diagnostic qualification is still required; full launcher/job dry-run is **NOT_RUN**. Producer remains **NOT_READY**; full collection, STT3 acceptance, WER/scoring and fitting screen remain outstanding. [Packet](</mnt/raid0/llm/tmp/refactor-cs8-stt7-predictions-20261031/READY-SUCCESSOR.json>).
- Refreshed offline preflight against the updated bindings: all 3,450 existing receipts were identity/raw-hash validated and skipped; the empty-transcript fixture (empty hypothesis WER=1.0), shell syntax, refreshed launcher fingerprint (stdout SHA-256 `b1f5474a71876a9017ec75c8a8407575ccba66d54a15de75ddfedcc009e0b528`), offline admission (`ADMIT_PASS`, stdout SHA-256 `c162a29a93b45e7c4591225246a8dc5f71787db41e9df3da2ee7a75450c5b706`), and LOOP49 static manifest/row/engine/source/allowlist check passed. Keeper nonce-bound qualification receipt and full launcher/job dry-run remain NOT_RUN; packet remains NOT_READY, with no production grant or inference. [Refreshed evidence](</mnt/raid0/llm/tmp/refactor-cs8-stt7-predictions-20261031/LOOP49-PREFLIGHT-EVIDENCE.json>).

### LOOP-49 source completion — 2026-11-01

- Completed source implementation in `66074ef20dbd2528c0c9f96d7f1876db3296cf36`. Post-commit offline fixture validation passed: **79 tests, 14 subtests**; evidence `docs/reports/loop49-validation-20261101.md`. This verifies component regressions; full keeper dry-run acceptance remains outside that test run. [no-belief: tooling-repair]
- Refreshed review candidate `/mnt/raid0/llm/tmp/loop49-keeper-v7f-candidate/v7f-r3/`; `SHA256SUMS` SHA-256 `b474feafa361f206c17edcc7f3ab134303aca22fbf4f383a71cd84c5243f75a8`. v7f remains **unpinned / live-disabled pending owner pin**. No keeper, production grant, arming, or inference action was performed.
- Corrected the historical count separately from the preserved task text: committed audit `docs/reports/failed-run-audit-20261031.md` records **135/405** FAILED-RUN receipts, not 136/405.

### README freshness checker repair — 2026-11-01

- Fixed false missing-README warnings when the checker runs from a nested lane: `.claude/skills/project-wiki/scripts/check_readme_freshness.py` now prefers valid umbrella repository entries, then discovers Git repository roots from the nearest ancestor outward. Six region-locked regression tests in `.claude/skills/project-wiki/scripts/tests/test_check_readme_freshness.py` passed; the README freshness check is now clean. [no-belief: tooling-repair]

### C6 IQKFA remainder RAM correction — 2026-11-01

- Corrected the candidate packet and live FILLERS row to 12 GiB (`gib=12`, `rss_limit_GiB=12`, `process_limit_GiB=12`). The live row remains `BACKLOG`/`ready=n`, explicitly blocked on the LOOP49 canonical engine/checker pin and qualification. The former 8 GiB `ready/armed` manifest was withdrawn byte-identically to `/mnt/raid0/llm/tmp/compute-flags/ready/withdrawn-c6-stale-armed-20261101T023954Z/refactor-c6-iqkfa-remainder-729599d69-20261031.json` (SHA-256 `9943f022c114fcf1ab89d229637e0dfdf6a89ffa9d552ef4b88f76d542ad6e0e`); receipt `/mnt/raid0/llm/tmp/compute-flags/ready/withdrawn-c6-stale-armed-20261101T023954Z/WITHDRAWAL.json` SHA-256 `f09af5a6dc7f07d114e602a3cdcbe1ebcbcae24f0132ad2cdfc2760846f9e4b0`.
- R11 static validation on SMT siblings 144,145 passed: `bash -n` 1/1; `py_compile` 3/3; `validate_fillers --row` checked 1 row with 0 refusals/0 row warnings (two unrelated global blank-line warnings at lines 55 and 157). Peak RSS was 18,256 KiB under the 8 GiB virtual-memory cap. All 28 correctness cells remain **UNTESTED**; this is not a feasibility or throughput result. [no-belief: static correction only]

### Current queue checkpoint — 2026-11-01

- MHS-11 operator-guide symbol citation update is committed as orchestrator `8359d0c7f22f4994e67fa273e4df0dfb1bd29953` on `lane/refactor-app-code-20261031` and published to that remote lane. `git diff --check` passed; no tests were applicable to the docs-only edit. It is not ticked yet because the change has not been promoted to `origin/main`.
- Rechecked CPU prep ranks: rank 15 M4 recut build had completed successfully on 2026-10-27, but its launcher/job and source manifest are now retired/stale; do not reuse its ID or call it READY. Rank 16 LB49 graph packet is a static-only proposal, not LOOP49-qualified; normal/cutoff smokes remain unrun pending a keeper-pinned canonical engine. Audits: `/mnt/raid0/llm/tmp/refactor-01a16fc3/loop49-lb49-port-static-20261101/LOOP49-AUDIT.md`.
- NEMO PROF reseg rc70 root cause is a deterministic 200 GiB resource-gate expectation vs the row/caller's 8 GiB envelope. A fresh successor packet is being prepared with the 8/8 GiB cap intact; no scheduler, grant, build, trace or inference has run in this checkpoint.
- Root GitNexus status is stale (indexed 2026-10-24). The wrapper refused refresh without a canonical filler grant; no source edit was made against the stale graph. Scoreboard at 02:56Z showed code 0/5 and CPU READY 0/1.

### NEMO-PROF-RESEG partial analysis — 2026-11-01

- Reworked the retained-trace analyzer to use the measured L/P and B/M request windows from `run.json` monotonic timing marks. The marks and rocprof timestamps share the same clock. The analyzer sums all complete GPU dispatches in each request window, divides by the server-reported generated-token count, and independently checks that count and wall time against the server's final `eval time` row.
- L: 160 generated tokens, 332,946 in-window dispatches, 33.0175 ms GPU busy per token and 56.98 ms server wall per token. B: 96 tokens, 179,633 dispatches, 22.2745 ms GPU busy per token and 33.92 ms server wall per token. These are request-window averages per generated token; no individual per-token GPU interval or cause for the host/device wall gap is claimed.
- `python3 resegment.py`, `python3 -m py_compile resegment.py`, and retained raw `SHA256SUMS` validation passed. Artifact commit `3c3c9b759`; evidence at `docs/reference/autokernel/nemo-gpu-prof-reseg-20261031/`.

### S0-V34-LOCK-LOSS-REPRODUCER — 2026-11-01

- Reproduced the legacy v33 `/proc/locks` false refusal under a real q3 region-lock build claim: `RuntimeError: lock lost` occurred at iteration 30 while owner FD rows still showed exclusive GLOBAL and build locks. No model/server/GPU work ran.
- Durable scripts, source identities, launcher log, result, and checksum custody are in `artifacts/compute/refactor-s0-v34-lock-loss-repro-20261101/`. `python3 test_result.py` passes. Handoff tick will cite the implementation/evidence commit.
