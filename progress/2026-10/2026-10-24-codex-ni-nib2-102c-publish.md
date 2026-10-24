# 2026-10-24 — NIB2-102.c argv-safe import fixture publication

## Result

The reviewed argv-safe import fixture repair is published in `epyc-orchestrator` main. The original worker candidate was `7bf0b9b5a5ca0490e2cdffb7c78ab1230c00e6ba`, based on `3329083dc37a693953eea7878f32037695d851f6`. I integrated only that reviewed commit onto the actual fresh `origin/main` (`d2ce754d571c1ca2648e036175d77f2beb9f4e25`), whose current upstream prompt/output work remained intact. The integration commit is `9fdb62a92cd6f5ebac2f85e2045f6cd566604aed`; its stable patch ID matches the candidate (`a1112588916240bc212ec5614262e24dd62df00a`). It changed exactly the two reviewed files. A no-ff promotion reached `main` at `1f4c2bdb8632d9ac27657a784dcce68ee8cd6aa0`.

## What the test protects

The fixture keeps its original NI63 baseline commit constant, immutable declared capacity-policy input and YAML fixtures, and the real capacity guard plus oversized negative control. The stale source-closure hashes for `scripts/server/orchestrator_stack.py` and `src/registry/model_descriptors.py` were refreshed to the actual pinned source. The source pin for `src/registry/research_origin.py` was added because the property probe imports and blocks its resolver/materializer entry points. Existing unrelated source pins were retained.

The import property is now exercised under hostile argv with guards against argument parsing, process starts/re-execs, network connections, registry compilation, and research resolution/materialization. The test also checks no output and no process replacement. This protects lazy import behavior directly while retaining the external pinned clone's capacity-validation guarantees; it does not change production compiler or source code.

## Verification evidence

The calendar-granted job `codex-ni-nib2-102c-20261024` completed at `2026-10-24T14:54:56Z` on worker candidate `7bf0b9b5a5ca0490e2cdffb7c78ab1230c00e6ba`: 5 passed, 1 existing `SelectableGroups` deprecation warning, 1.79 seconds. Evidence remains under `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/nib2-102c/` (`test.log`, `status.json`). No test was repeated during publication. Integration gates: full source and target SHAs checked; stable patch IDs equal; changed-path set exactly matches the two approved files; `git diff --check` passed; promotion merged without conflict.

The root task checkbox remains owned by workspace-58, who will tick it after publication. Calendar owner received the source main SHA and main-review/5-pass proof at 2026-10-24T15:08:38Z (message `9610f81f...`). No handoff/index, wiki, production, API, reload, model, or build changes were made in this publication wrap-up. The sole source change was the reviewed two-file test fixture repair; tests were not repeated during publication. Root README freshness check produced no warnings. Vidya ledger check: fresh through intake-2510#record (2,491 entries; lag 0), last sync `2026-10-22T21:34:42Z`. The root progress note was prepared against root `origin/main` `8c15737d0f46d213b8ea05438f6f1b670da59b58` after source publication, then reviewed and approved by main before this one-file root publication.
