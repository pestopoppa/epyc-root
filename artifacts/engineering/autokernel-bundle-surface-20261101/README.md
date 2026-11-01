# AutoKernel `Bundle.surface` implementation and verification

Status: Main accepted the literal task after source review and the final focused R6 batch. The implementation is published on Research `origin/main` at `a25f5ff79b2db6c4c883d7eb1402ada87ca46c63` (`Isolate AutoKernel accumulator bundles by surface`) plus follow-up `064d758ee4218014628eb021d9526eaafff7f456` (`Read explicit bundle authority in champion reanchor`). The follow-up was integrated with unrelated accepted U3 readiness artifacts; final merge `55b64bb1c37b4848cf87a505b2d5d5b80af85be2` is verified equal to `origin/main`. Do not tick broader P2 exit criteria or native floor/A/B/rebaseline tasks.

## Original task and applied checkbox

Original queue row, unchanged:

```text
[M] handoffs/active/autokernel-unified-surface-program.md:1396 — `Bundle.surface`; per-surface store filenames; `load_bundle()` per surface; shared cor invariant test
```

Applied completion line for the P2 section:

```text
- [x] `Bundle.surface`; per-surface store filenames; `load_bundle()` per surface; shared cor invariant test ✅ 2026-11-01 — Research `a25f5ff79b2db6c4c883d7eb1402ada87ca46c63` + `064d758ee4218014628eb021d9526eaafff7f456` adds opt-in CPU/GPU typed v3 bundle snapshots, isolated per-surface filenames/journals, read-only surface selection, shared-COR refusal/CAS promotion, epoch archive/recovery isolation, and lock ordering. Legacy unscoped filenames/schema/caller behavior remain the default. Focused tests: 74 bundle/journal tests + 1 explicit CPU caller + 1 legacy CPU caller + 19 reanchor tests passed; changed-line Ruff and scoped diff checks passed under R6. [no-belief: source-only storage isolation and synthetic correctness verification; no native measurement, live-store mutation, or promotion]
```

The owning session applied this exact checkbox after integrating the published source and evidence below; no index row or higher-level P2 criterion was changed.

## Implementation and source pins

Primary commit `a25f5ff` has these 10 owned paths:

- `scripts/kernel_rnd/autokernel/journal.py`
- `scripts/kernel_rnd/autokernel/loop/accumulate.py`
- `scripts/kernel_rnd/autokernel/loop/new_epoch.py`
- `scripts/kernel_rnd/autokernel/loop/run.py`
- `scripts/kernel_rnd/autokernel/loop/seed_bundle.py`
- `scripts/kernel_rnd/autokernel/loop/serving_gate.py`
- `scripts/kernel_rnd/autokernel/loop/test_bundle_recovery.py`
- `scripts/kernel_rnd/autokernel/loop/test_bundle_surface.py`
- `scripts/kernel_rnd/autokernel/loop/test_existing_cpu_run.py`
- `scripts/kernel_rnd/autokernel/loop/test_promotion_targets.py`

The primary commit is 713 insertions / 81 deletions. Source blob SHA-256 values:
- `scripts/kernel_rnd/autokernel/journal.py` — `47193ab42e9c3e710d31307d8d248905945e3f07a7a4e582c3869a32bf0015d7`
- `scripts/kernel_rnd/autokernel/loop/accumulate.py` — `a886881a4304ad4f9a96138ebf01e4efa9909707e155007d1f59fed46d3bd446`
- `scripts/kernel_rnd/autokernel/loop/new_epoch.py` — `707f68110b43995458e2fc2347f0a8d994472f5b4d7c7939f53ded36b3ba312e`
- `scripts/kernel_rnd/autokernel/loop/run.py` — `a4033bd40b601ce54346208dfb9f16537955f736ddf648f46acf338ed4a3d717`
- `scripts/kernel_rnd/autokernel/loop/seed_bundle.py` — `9bd80ff5cc3ee7f2dfcede242b637da6bb96042334f4c5d08cf98837caa807a8`
- `scripts/kernel_rnd/autokernel/loop/serving_gate.py` — `8c3f20578865e116fbe57d1fe8dbea9a9fcf5586ae1cf1478a9fc6e738f35961`
- `scripts/kernel_rnd/autokernel/loop/test_bundle_recovery.py` — `a2fda8c23a84f82f272dbd1189a18f976ff9e52405eb3c5db248caaadcb383a3`
- `scripts/kernel_rnd/autokernel/loop/test_bundle_surface.py` — `e7030a85c1a5d707e8e86b98432fc2613cbcef5c677f6a3c7366d3c7e4fcda5b`
- `scripts/kernel_rnd/autokernel/loop/test_existing_cpu_run.py` — `1039fdab726fde5bb00e429338886d12d026d1a43b3f9e7990af8f904aa8716f`
- `scripts/kernel_rnd/autokernel/loop/test_promotion_targets.py` — `bba47ef739a4c5f25ae2d094d464ccd78aea2e7a6672c19b4a1618ef0baf5de0`

Follow-up commit `064d758ee421` adds `scripts/kernel_rnd/autokernel/loop/champion_reanchor.py` and `scripts/kernel_rnd/autokernel/loop/test_champion_reanchor.py` (68 insertions / 7 deletions). Their final source SHA-256 values are `6806fa6d0c06d4f339a7e75575e2471acf922375609a36ef77245d2367cd8e89` and `92c3d734b5e3a1f2d76366b7cda6345ebc2a054383c113628d25846e53a3c144`.

## Semantics and acceptance limits

- `Bundle.surface` opts into CPU or GPU v3 snapshots. Without it, the existing v2 legacy snapshot name and unscoped launch behavior remain unchanged.
- Explicit CPU/GPU stores use separate bundle files and journals with one shared COR authority file. Each save requires a matching typed bundle. Legacy/ambiguous state is refused instead of relabeled; explicit read-only peeks do not initialize storage.
- Journal/archive/recovery and serving promotion follow shared-COR then surface-journal lock order. Promotion compare-and-swaps authority with the new surface snapshot; another surface whose snapshot has the prior COR refuses as stale until separately rebaselined.
- In focused tests, CAS was exercised only against temporary fixtures. No native benchmark, build, kernel promotion, live store, serving process, or measurement ran. P2 floor calibration, CPU A/B, and rebaseline work remain open.
- `champion_reanchor.read_campaign()` consumes the canonical shared-COR parser for explicit stores, preserves legacy fallback only when there are no surface paths, and refuses missing/corrupt authority. Its global ancestry follows the shared COR; a stale peer surface stays stale and is never relabeled. Tests cover explicit-only, legacy, missing/corrupt authority, and stale peer behavior. GitNexus was stale (2026-10-31 index); its LOW impact was treated as UNKNOWN and current source callers were traced directly, with no reindex run.

## Follow-up R6 receipt

Receipt: `/mnt/raid0/llm/tmp/codex-ni-autokernel-surfaces-20261101/reanchor-followup/R6-WRAPPER-RECEIPT.json`
Log SHA-256: `af148964b327efcbd374c36a24a219a098c70388f774b1929407c681bd99c43a`
Wrapper SHA-256: `f783ba0b757d7ee40d5a68de7895064a26ce929cca58420b4cba054b81bdb4c7`

- All 19 `test_champion_reanchor.py` tests passed; changed-line Ruff 0 (121 unchanged-line diagnostics excluded); scoped diff check passed.
- Same R6 pair/mask admission: pair34-35, CPUs130–131; only disjoint non-timing correctness grants; 0.913s; sampled peak RSS 50,700,288B; wrapper PID64819/birth163072328, test PID64847/birth163072336; same boot ID; descendants drained.

## Primary R6 receipt

Receipt: `/mnt/raid0/llm/tmp/codex-ni-autokernel-surfaces-20261101/R6-WRAPPER-RECEIPT.json`
Focused log: `/mnt/raid0/llm/tmp/codex-ni-autokernel-surfaces-20261101/publication.log`
Focused log SHA-256: `e5ab6044e76b35d1df815533de4bcb9181b6155ad8d81d165d888b53e7262c66`
Adapted wrapper SHA-256: `6a72fb703c0a1f8cbb3dc594199e52866cab0d5a3f90b7de724ddf850d9ba943`

- Admission used the existing R6 guard adapted from ROOT `artifacts/engineering/akx-p4a-keep-screen-20261101/evidence/run_r6_postmerge_wrapper.py`; source/input closure was limited to the AutoKernel bundle implementation/test paths and pre-existing peer WIP was preserved.
- Pair mutex: `/mnt/raid0/llm/tmp/compute-flags/prep-locks/34-35.lock`; actual CPUs 130–131 (SMT siblings for physical 34–35); OMP=1. Start/end live grant snapshots showed only non-timing correctness grants on `mi210_0,184-191`, `48-71`, and `0-23`; none named the selected CPUs or timing-overlapped physical 34–35.
- Wall time 6.462 s, below 900 s. Sampled process-tree RSS peak 84,340,736 bytes, below 8 GiB. Wrapper PID 4144222 / birth ticks 163034714; test-command PID 4144248 / birth ticks 163034721; boot ID `3be2fb1a-7293-4c34-b733-c85d772b9474`. Captured child identities were drained and kernel child set was empty.
- Results: 74 passed; explicit CPU caller 1 passed (6 deselected); legacy CPU caller 1 passed (73 deselected); changed-line Ruff 0 diagnostics (108 unchanged-line legacy diagnostics excluded); scoped `git diff --check` passed.
