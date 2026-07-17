# K35 Optimized Stack Throughput-vs-Context Report - 2026-07-17

## Disposition

This report consolidates the current K35 release evidence for the experimental v7 kernel at `/mnt/raid0/llm/llama.cpp-experimental`, commit `d1e5a20eb`, `llama-server` version `10088`.

It is an operator-facing synthesis, not a v7 promotion sign-off. The 2026-07-17 memory-backfill pass covers the non-vision optimized rows, and the follow-up vision matrix covers the then-current production vision roles on four local OCR/chart fixtures. K35 remains open because the true `vision_escalation` lane has a measured quality failure and optional concurrency rows are not yet part of the canonical matrix.

Mitigation applied after the matrix: active `vision_escalation` on port `8087` is temporarily rebound to the same Qwen2.5-VL model/projector as `worker_vision`. This is a safety alias for call-site stability, not evidence that a higher-quality escalation model has been found.

## Run Discipline

| Field | Evidence |
|---|---|
| Kernel | experimental v7 only, `/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin/llama-server` |
| Version | `version: 10088 (d1e5a20eb)` |
| Production v6 | not touched |
| Environment | runner commands set `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin`; optimized CPU rows use `GGML_IQK=1` |
| Contention guard | runner `guard_state.json` files report empty `process_blockers` |
| Cleanup proof | successful canonical rows report dead server PIDs and empty `cleanup_process_blockers`; vision smoke/matrix verified server PIDs dead |
| GPU state | frontdoor/worker guard captured MI210 as `65520 MiB` total and `65416 MiB` free before runs; post-run ROCm checks reported no KFD PIDs |
| Memory backfill | `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json` reran non-vision optimized cells with `memory_samples`; `/mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z/summary.json` records the same memory sample shape for current production vision roles |

## Optimized Configs Used

| Role | Model | Model artifact size | Serving configuration | Evidence |
|---|---:|---:|---|---|
| `frontdoor` | `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` | `36G` | MI210 resident, `-ngl 99`, `q8_0/q8_0` KV, reasoning off, no spec; Stage-2 showed no-spec faster than native MTP or external draft-tree on this workload | `/mnt/raid0/llm/tmp/k35-frontdoor-canonical-20260717T132933Z/` |
| `worker_general` | `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` + assistant draft `gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf` | `16G` + `441M` | CPU, composed `ngram-mod,draft-mtp`, `draft_max=2`, q8 KV, reasoning off, production-shaped full-instance CPU flags | `/mnt/raid0/llm/tmp/k35-worker-canonical-20260717T133244Z/` |
| `architect_general` | `Qwen3.5-122B-A10B-UD-Q4_K_M` shards | `72.9 GiB` total | CPU, native same-file NEXTN via `draft-mtp`, `-np 2`, `q4_0/f16` KV, `--mlock`, `--jinja`, thinking disabled | `/mnt/raid0/llm/tmp/k35-arch-ingest-2k-20260717T121543Z/`, `/mnt/raid0/llm/tmp/k35-architect-8k-fixed-20260717T121856Z/` |
| `ingest_long_context` | `Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf` | `46G` | CPU, default experts, spec disabled, `q4_0/q4_0` KV, `--mlock`, `--jinja`; no `qwen3next.expert_used_count` override | `/mnt/raid0/llm/tmp/k35-ingest-default-2k8k-20260717T123107Z/`, `/mnt/raid0/llm/tmp/k35-ingest-default-deep-20260717T123308Z/` |
| `worker_vision` | `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` + `mmproj-model-f16.gguf` | `4.4G` + projector | CPU, `-np 2`, `-c 8192`, `-t 24`, flash attention on, four local OCR/chart fixtures | `/mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z/` |
| `vision_escalation` defect row | `Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf` + F16 projector | `18G` + projector | CPU, `-np 1`, `-c 16384`, `-t 96`, flash attention on, `qwen3vlmoe.expert_used_count=int:4`, four local OCR/chart fixtures | `/mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z/` |
| `vision_escalation` temporary active alias | `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` + `mmproj-model-f16.gguf` | `4.4G` + projector | CPU, port `8087`, `-np 1`, `-c 8192`, `-t 24`, flash attention on, no override; same model/projector as `worker_vision` | registry/stack-prior mitigation, 2026-07-17 |

Exact command lines are preserved in each artifact directory's `commands.sh`, `plan.json`, `server_argv.json`, or role-specific `server_argv.json`.

## Throughput Matrix

| Role | Nominal context | Prompt tokens | Completion tokens | Prompt t/s | Decode t/s | Acceptance / quality side data | Artifact |
|---|---:|---:|---:|---:|---:|---|---|
| `frontdoor` | 2K | `581` | `512` | `1356.15` | `99.44` | no spec; min-completion passed | `k35-frontdoor-canonical-20260717T132933Z` |
| `frontdoor` | 8K | `6725` | `512` | `2045.13` | `95.07` | no spec; min-completion passed | `k35-frontdoor-canonical-20260717T132933Z` |
| `frontdoor` | 32K | `31302` | `512` | `1757.86` | `78.17` | no spec; min-completion passed | `k35-frontdoor-canonical-20260717T132933Z` |
| `worker_general` | 2K | `582` | `512` | `308.71` | `126.18` | `492/666` draft tokens accepted | `k35-worker-canonical-20260717T133244Z` |
| `worker_general` | 8K | `6726` | `512` | `288.80` | `96.67` | `492/666` draft tokens accepted | `k35-worker-canonical-20260717T133244Z` |
| `worker_general` | 14K | `12535` | `512` | `249.20` | `82.94` | `492/666` draft tokens accepted | `k35-worker-canonical-20260717T133244Z` |
| `architect_general` | 2K | `837` | `256` | `144.96` | `23.53` | `203/205` draft tokens accepted | `k35-arch-ingest-2k-20260717T121543Z` |
| `architect_general` | 8K | `6725` | `512` | `140.94` | `20.72` | `408/409` draft tokens accepted | `k35-architect-8k-fixed-20260717T121856Z` |
| `ingest_long_context` | 2K | `575` | `512` | `192.15` | `19.82` | spec disabled; default experts | `k35-ingest-default-2k8k-20260717T123107Z` |
| `ingest_long_context` | 8K | `6719` | `512` | `175.78` | `15.94` | spec disabled; default experts | `k35-ingest-default-2k8k-20260717T123107Z` |
| `ingest_long_context` | 16K | `14528` | `512` | `130.99` | `13.00` | spec disabled; default experts | `k35-ingest-default-deep-20260717T123308Z` |
| `ingest_long_context` | 30K | `28528` | `512` | `100.51` | `10.13` | spec disabled; default experts | `k35-ingest-default-deep-20260717T123308Z` |

## Vision Matrix

The production vision rows use four fixed local fixtures: handwritten `7500`, receipt total payable `43.36`, chart country at 7 years `Tanzania`, and receipt doc number `CS00012465`. They are not context-depth rows, but they now include throughput, quality, memory, guard state, and cleanup proof.

| Role/scenario | Quality | Prompt-token range | Decode t/s range | Result | Artifact |
|---|---:|---:|---:|---|---|
| `worker_vision_cpu_qwen25vl` | `4/4` | `42-2249` | `16.91-21.32` | passed all fixed fixtures: `7500`, `43.36`, `Tanzania`, `CS00012465` | `k35-vision-matrix-20260717T1500Z` |
| `vision_escalation_cpu_qwen3vl30b_moe4` | `3/4` | `31-1709` | `35.87-50.17` | passed OCR/receipt fixtures; failed chart fixture (`Moldova` instead of `Tanzania`) | `k35-vision-matrix-20260717T1500Z` |

Diagnostic vision-escalation probes did not recover the chart failure:

| Scenario | Change Tested | Quality | Chart output | Artifact |
|---|---|---:|---|---|
| `vision_escalation_cpu_qwen3vl30b_moe4_image1024` | add warned `--image-min-tokens 1024 --image-max-tokens 1024` | `3/4` | `Suriname` | `k35-vision-escalation-image1024-20260717T1518Z` |
| `vision_escalation_cpu_qwen3vl30b_default_experts` | remove `qwen3vlmoe.expert_used_count=int:4` | `3/4` | `Suriname` | `k35-vision-escalation-default-experts-20260717T1520Z` |

The old one-image release smoke remains useful as a launch sanity check: `/mnt/raid0/llm/tmp/k35-vision-release-smoke-20260717T125719Z/summary.json` showed both production vision roles could answer `7500` and cleanly stop.

## Vision Escalation Mitigation

The Qwen3-VL-30B escalation row is faster than `worker_vision` on these short decode fixtures, but it is not production-quality-safe because it failed the chart fixture under all three tested shapes. The live stack was therefore recompiled so `vision_escalation` temporarily uses the Qwen2.5-VL artifact and projector that passed `4/4`, preserves port `8087`, uses a distinct 24-thread quarter mask, and emits no Qwen3-VL `override_kv`.

Validation for the mitigation: research registry validation reports `0 error(s)` with only pre-existing off-disk catalogue warnings; the orchestrator stack-change pipeline update passed with descriptor-removal waiver; the no-inference promotion suite plus stack-prior compiler coverage passed (`197 passed`). This closes the immediate unsafe-lane problem but leaves true escalation replacement open.

## Resident Memory Backfill

Memory values below come from the `after_request` sample in `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json`. Host values are `/proc/<pid>/status` `VmRSS` plus `smaps_rollup` PSS. GPU values are the ROCm reported `VRAM%` during that sample.

| Role | Nominal context | Decode t/s | Host VmRSS | PSS | VmPeak | MI210 VRAM | Acceptance |
|---|---:|---:|---:|---:|---:|---:|---|
| `frontdoor` | 2K | `99.77` | `1.37 GiB` | `1.36 GiB` | `80.32 GiB` | `55%` | no spec |
| `frontdoor` | 8K | `95.56` | `1.38 GiB` | `1.37 GiB` | `80.32 GiB` | `55%` | no spec |
| `frontdoor` | 32K | `78.48` | `1.40 GiB` | `1.39 GiB` | `80.32 GiB` | `56%` | no spec |
| `worker_general` | 2K | `122.75` | `17.48 GiB` | `17.48 GiB` | `36.14 GiB` | `0%` | `492/666` |
| `worker_general` | 8K | `97.80` | `17.74 GiB` | `17.73 GiB` | `35.53 GiB` | `0%` | `492/666` |
| `architect_general` | 2K | `22.76` | `75.56 GiB` | `75.55 GiB` | `100.01 GiB` | `0%` | `408/410` |
| `architect_general` | 8K | `19.37` | `76.46 GiB` | `76.46 GiB` | `99.17 GiB` | `0%` | `408/409` |
| `ingest_long_context` | 2K | `19.83` | `45.84 GiB` | `45.84 GiB` | `64.20 GiB` | `0%` | spec disabled |
| `ingest_long_context` | 8K | `15.86` | `46.11 GiB` | `46.10 GiB` | `65.75 GiB` | `0%` | spec disabled |
| `ingest_long_context` | 32K | `9.59` | `46.35 GiB` | `46.35 GiB` | `68.15 GiB` | `0%` | spec disabled |
| `worker_vision` | fixed fixtures | `16.91-21.32` | `6.05 GiB` | `6.04 GiB` | `6.34 GiB` | `3%` | `4/4` |
| `vision_escalation` | fixed fixtures | `35.87-50.17` | `19.69 GiB` | `19.69 GiB` | `19.73 GiB` | `2%` | `3/4`; chart failed |

## Invalidated Rows

Do not use these as K35 default ingest evidence:

| Artifact | Invalidated scope | Reason |
|---|---|---|
| `/mnt/raid0/llm/tmp/k35-arch-ingest-2k-20260717T121543Z/` | ingest row only | used stale `ingest_long_context_cpu_moe4` / `qwen3next.expert_used_count=int:4`; the architect row in the same artifact remains valid |
| `/mnt/raid0/llm/tmp/k35-arch-ingest-8k-20260717T121645Z/` | architect 8K attempt and ingest row | architect attempt had a harness context-accounting bug; ingest row used stale MoE4 override |
| `/mnt/raid0/llm/tmp/k35-ingest-deep-20260717T122029Z/` | ingest deep rows | used stale MoE4 override |

## Remaining K35 Gaps

- `vision_escalation` needs follow-up before it can be treated as the safe higher-quality VL lane. The former production Qwen3-VL-30B MoE4 row failed the chart fixture, neither the 1024-image-token diagnostic nor default-expert diagnostic fixed it, and the active 8087 lane is now only a temporary Qwen2.5-VL alias.
- Replacement/admission A/B remains open for Qwen3-VL-8B, MiniCPM-o, PaddleOCR-VL, SuperGemma4, and any other candidate intended to replace or specialize the current escalation role.
- Architect has valid 2K/8K optimized rows only. Deeper contexts exceed the production `-np 2 -c 16384` per-slot launch shape unless the operator authorizes a different architect launch.
- Concurrency rows remain optional/open. Current canonical rows are single-scenario quiet-host measurements, not mixed-stack concurrency service measurements.
- The Gemma4 draft-memory probe emitted a warning while fitting (`failed to measure draft model memory` because `Gemma4Assistant requires ctx_other`); throughput/acceptance still passed, but memory measurement for this lane needs a separate fix or external sampler.

## Next Measurements

1. Add a vision-escalation replacement/specialization A/B: current evidence says the Qwen2.5-VL worker model is safer than the former Qwen3-VL escalation model on the fixed chart fixture despite being smaller.
2. If operator wants service-level capacity, run a separate concurrency matrix; do not blend it into the quiet-host single-role K35 rows.
3. Improve GPU memory precision if needed: current ROCm snapshots report percentage, not exact MiB, in this runner configuration.
