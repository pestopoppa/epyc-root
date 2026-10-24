# M26 distillation-pool producer/reader publication — 2026-10-24

**Agent:** `codex-ni-01a16d6b`

Published the M26 producer and reader to both project `main` branches after validating the source candidates and integrating them against fresh remote tips. The ROOT candidate was rebased by ordered cherry-picks onto the S4 wrap-up promotion, preserving the existing S4 fixture helper and registration alongside M26's separate fixture helper and registration.

| Repository | Tested source pin | Published source commit | Main promotion | Changed paths |
|---|---|---|---|---:|
| epyc-root | `90482f6beb0a78de745e074ffb93023ea3a503a3` | `0d9b34e152c9f1b5960960377b69e27ead1ddb61` | `2387f65d75289471b112e992575164efddeff2ea` | 5 |
| epyc-orchestrator | `ae32f964c09113d6a0d262ae4bd8c277faf1adb1` | `71210d1f2fc854b52f52e202bf3ed1a267a02980` | `2cefc241152b36f125e76bacb38b4fe9e1b016cf` | 4 |

Validation evidence already completed for the exact tested pins (no jobs were rerun during publication):

- ROOT focused producer/reader validation: 5 passed; 0 carrier violations.
- Orchestrator focused validation: 5 passed; one dependency deprecation warning.
- Supplemental CLI job R2: exit 0, 10 passed; JUnit has 10 cases and zero failures, errors, or skips; carrier output reports 6 tuples checked and 0 violations. Status is complete at `2026-10-24T15:22:15Z`. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/m26-cli-v2/status.json`, `test.log`, and `/mnt/raid0/llm/tmp/codex-ni-20261024-m26-wire/cli-supplemental-v3-logs/`.
- Tests used fixtures and the temporary ledger. No teacher/model call or real pool capture was run; no efficacy or skill-quality claim is made.
- The adapter preserves the native Boolean integrity verdict in the receipt and `extra.native_verdict`, projects it as integer 0/1 under `false_0_true_1`, and delegates grading to the existing `claim_tuple.grade()` path. No shared grading code changed.

Publication used fresh ROOT `origin/main` `3758a0ca8ec05e1d6f8c7918985b94c96ffe35f7` and fresh orchestrator `origin/main` `be208213775a032aefde26a3c1df4ac4ca2d445e`. Both final candidate diffs passed `git diff --check`; ROOT changed exactly five expected source/test paths and orchestrator exactly four. Both pushes were verified against `ls-remote` and a post-push fetch. Wrap-up and push locks were released. Main reviewed and applied the source-table update and completion of the existing `VB-M26-DISTILL-POOL-WRITE` checkbox before this documentation closeout. Main also refreshed EVL-37’s next action to the remaining S4-T1 live proof and first real Omega capture ingestion.
