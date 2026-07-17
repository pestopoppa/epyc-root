# K35 Optimized Stack Throughput-vs-Context Report - 2026-07-17

## Disposition

This report consolidates the current K35 release evidence for the experimental v7 kernel at `/mnt/raid0/llm/llama.cpp-experimental`, commit `d1e5a20eb`, `llama-server` version `10088`.

It is an operator-facing synthesis, not a v7 promotion sign-off. The 2026-07-17 memory-backfill pass covers the non-vision optimized rows, and the follow-up vision matrix covers the then-current production vision roles on four local OCR/chart fixtures. K35 remains open for the `vision_escalation` activation decision; the broader MiniCPM-o/frontdoor service matrix now covers 2K/8K active-overlap fixture traffic, so the remaining question is policy/capacity rather than basic co-residency.

Mitigation applied after the matrix: active `vision_escalation` on port `8087` is temporarily rebound to the same Qwen2.5-VL model/projector as `worker_vision`. MiniCPM-o with `--reasoning off` is now a fast quality-clean replacement candidate and has passed frontdoor co-residency, service-tax, and broader fixture service-matrix probes, but it has not been flipped into the live stack.

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
| Memory backfill | `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json` reran non-vision optimized cells with `memory_samples`; `/mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z/summary.json` records the same memory sample shape for current production vision roles; `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-coresidency-20260717T191849Z/` records the MiniCPM-o/frontdoor MI210 co-residency smoke; `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-service-tax-20260717T192427Z/` records the follow-up idle-vs-active service-tax probe; `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json` records the broader 2K/8K service matrix |
| Operational metric discipline | Baseline/no-spec rows are controls for attribution only. Serving decisions use the fastest quality-clean lane that would actually be deployed, with the run labeled isolated or concurrent. |
| Frontdoor 1024-token replay | `/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z/summary.json` reran the MI210-resident frontdoor operational lane with `max_tokens=1024`; cleanup blockers were empty and post-run ROCm reported no KFD PIDs |

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
| `vision_escalation` rejected candidate | `Qwen3VL-8B-Instruct-Q4_K_M.gguf` + F16 projector | `4.7G` + projector | CPU and MI210 candidate rows, `-np 1`, `-c 8192`, `-t 24`, flash attention on; MI210 tested with 1024 image tokens and default image-token shape | `/mnt/raid0/llm/tmp/k35-qwen3vl8-candidate-20260717T185330Z/`, `/mnt/raid0/llm/tmp/k35-qwen3vl8-mi210-default-image-20260717T185459Z/` |
| `vision_escalation` quality-clean candidate | `MiniCPM-o-4_5-Q4_K_M.gguf` + vision F16 projector | `4.7G` + projector | CPU and MI210 candidate rows, `-np 1`, `-c 8192`, `-t 24`, flash attention on, `--reasoning off`; co-residency, service-tax, and 2K/8K active-overlap matrix tested beside MI210 frontdoor | `/mnt/raid0/llm/tmp/k35-minicpm-o45-reasoning-off-20260717T1911Z/`, `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json` |
| `vision_escalation` quality-clean non-preferred candidate | `supergemma4-26b-abliterated-multimodal-Q8_0.gguf` + F16 projector | `26G` + projector | CPU and MI210 candidate rows, `-np 1`, `-c 8192`, `-t 96`, flash attention on, q8 KV, `--reasoning off`, `--repeat-penalty 1.05`; MI210 uses `-ngl 99` | `/mnt/raid0/llm/tmp/k35-supergemma4-candidate-20260717T193120Z/` |
| `document_extraction` specialist candidate | `PaddleOCR-VL-1.6-GGUF.gguf` + PaddleOCR mmproj | `0.87G` + `0.82G` projector | MI210 transient server, `-np 1`, `-c 8192`, `-t 24`, flash attention on, `-ngl 99`, `--reasoning off`; tested as document/OCR extraction plus guarded `odl_bench` producer, not a general vision QA replacement | `/mnt/raid0/llm/tmp/paddleocr-vl-first-smoke-20260717T194332Z/`, `/mnt/raid0/llm/tmp/paddleocr-vl-receipt-extract-20260717T194415Z/`, `/mnt/raid0/llm/tmp/odl-paddleocr-vl-demo-20260717T200212Z/` |

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

### Frontdoor 1024-Token Operational Replay

The 512-token K35 row above remains the canonical cross-role table row. A longer operational replay was added to reduce short-output artifacts for the MI210 frontdoor lane:

| Nominal context | Prompt tokens | Completion tokens | Prompt t/s | Decode t/s | Artifact |
|---|---:|---:|---:|---:|---|
| 2K | `134` | `1024` | `672.33` | `100.55` | `k35-frontdoor-operational-1024-20260717T201842Z` |
| 8K | `6214` | `1024` | `2039.00` | `95.56` | `k35-frontdoor-operational-1024-20260717T201842Z` |
| 32K | `30791` | `1024` | `1762.93` | `77.67` | `k35-frontdoor-operational-1024-20260717T201842Z` |

Interpretation: this confirms the existing K35 frontdoor serving posture under a longer decode. It is an optimized operational row, not an apples-to-apples baseline/control run.

## Vision Matrix

The production vision rows use four fixed local fixtures: handwritten `7500`, receipt total payable `43.36`, chart country at 7 years `Tanzania`, and receipt doc number `CS00012465`. They are not context-depth rows, but they now include throughput, quality, memory, guard state, and cleanup proof.

| Role/scenario | Quality | Prompt-token range | Decode t/s range | Result | Artifact |
|---|---:|---:|---:|---|---|
| `worker_vision_cpu_qwen25vl` | `4/4` | `42-2249` | `16.91-21.32` | passed all fixed fixtures: `7500`, `43.36`, `Tanzania`, `CS00012465` | `k35-vision-matrix-20260717T1500Z` |
| `vision_escalation_cpu_qwen3vl30b_moe4` | `3/4` | `31-1709` | `35.87-50.17` | passed OCR/receipt fixtures; failed chart fixture (`Moldova` instead of `Tanzania`) | `k35-vision-matrix-20260717T1500Z` |
| `vision_candidate_cpu_qwen3vl8b_q4` | `4/4` | `31-1709` | `10.81-13.39` | passed all fixtures, but slower than the temporary Qwen2.5-VL alias and verbose on chart | `k35-qwen3vl8-candidate-20260717T185330Z` |
| `vision_candidate_mi210_qwen3vl8b_q4` | `3/4` | `31-1709` | `110.02-125.72` | fast but failed chart fixture (`Moldova` instead of `Tanzania`) with 1024 image-token shape | `k35-qwen3vl8-candidate-20260717T185330Z` |
| `vision_candidate_mi210_qwen3vl8b_q4_default_image` | `3/4` | `31-1709` | `109.61-120.32` | fast but failed chart fixture (`Moldova` instead of `Tanzania`) with default image-token shape | `k35-qwen3vl8-mi210-default-image-20260717T185459Z` |
| `vision_candidate_cpu_minicpm_o45_q4` | `4/4` | `91-626` | `11.98-14.13` | reasoning-off passed all fixtures exactly; default reasoning kept answers in `reasoning_content` and failed content scoring | `k35-minicpm-o45-reasoning-off-20260717T1911Z` |
| `vision_candidate_mi210_minicpm_o45_q4` | `4/4` | `91-626` | `110.81-122.18` | reasoning-off passed all fixtures exactly; first fast quality-clean escalation candidate | `k35-minicpm-o45-reasoning-off-20260717T1911Z` |
| `frontdoor + vision_candidate_mi210_minicpm_o45_q4` | mixed smoke passed | frontdoor `48`; MiniCPM-o chart `230` | frontdoor `99.97`; MiniCPM-o `108.68` on 4-token answer | both MI210 servers healthy together at `66%` VRAM; concurrent frontdoor 512-token text request and MiniCPM-o chart request passed; cleanup proof recorded | `k35-minicpm-frontdoor-coresidency-20260717T191849Z` |
| `frontdoor service tax with MiniCPM-o resident` | text-tax probe | frontdoor prompt `51`; MiniCPM-o long chart prompt `258` | frontdoor alone `101.68/101.84`; frontdoor with MiniCPM idle `101.89/101.86`; active overlap frontdoor `80.16/80.34`, MiniCPM-o `90.49/90.23` | idle residency had no measurable frontdoor tax; active concurrent vision cost about `21%` frontdoor decode on this synthetic pair | `k35-minicpm-frontdoor-service-tax-20260717T192427Z` |
| `frontdoor + MiniCPM-o broader service matrix` | active overlap passed `8/8` | frontdoor `581/6725`; MiniCPM-o `91-626` | frontdoor alone mean `96.33`; MiniCPM idle mean `96.48`; active overlap frontdoor mean `94.77`; MiniCPM-o active mean `85.22` | all four fixtures passed at 2K and 8K; idle residency remained free; active overlap averaged about `1.6%` frontdoor tax in this operational fixture pattern | `k35-minicpm-service-matrix-20260717T2045Z` |
| `vision_candidate_cpu_supergemma4_mm_q8` | `4/4` | `78-285` | `25.58-31.76` | passed all fixtures; quality-clean but heavy CPU resident footprint | `k35-supergemma4-candidate-20260717T193120Z` |
| `vision_candidate_mi210_supergemma4_mm_q8` | `4/4` | `78-285` | `80.35-83.87` | passed all fixtures; slower and heavier than MiniCPM-o MI210 | `k35-supergemma4-candidate-20260717T193120Z` |

Diagnostic vision-escalation probes did not recover the chart failure:

| Scenario | Change Tested | Quality | Chart output | Artifact |
|---|---|---:|---|---|
| `vision_escalation_cpu_qwen3vl30b_moe4_image1024` | add warned `--image-min-tokens 1024 --image-max-tokens 1024` | `3/4` | `Suriname` | `k35-vision-escalation-image1024-20260717T1518Z` |
| `vision_escalation_cpu_qwen3vl30b_default_experts` | remove `qwen3vlmoe.expert_used_count=int:4` | `3/4` | `Suriname` | `k35-vision-escalation-default-experts-20260717T1520Z` |

The old one-image release smoke remains useful as a launch sanity check: `/mnt/raid0/llm/tmp/k35-vision-release-smoke-20260717T125719Z/summary.json` showed both production vision roles could answer `7500` and cleanly stop.

The Qwen3-VL-8B candidate result is intentionally split by device. CPU is quality-clean on this small fixture set but slower than the alias that already passed. MI210 is fast enough to be operationally interesting, but it failed the chart fixture under both tested launch shapes, so it is not a serving candidate despite the throughput.

The MiniCPM-o candidate result is also intentionally split by launch mode. Default reasoning mode read the images and placed correct answers in `reasoning_content`, but failed the production-visible content channel. The realistic `--reasoning off` lane passed the fixed fixture set on both CPU and MI210. Its MI210 row is the first fast quality-clean escalation replacement candidate in this matrix. The follow-up smoke shows it can co-reside with the MI210 frontdoor lane for one mixed request, the two-rep service-tax probe bounds a worst-case synthetic active collision, and the broader 2K/8K service matrix shows all fixture/context overlaps passing with about `1.6%` average frontdoor tax. Live routing still needs an activation/capacity decision because activation changes MI210 scheduling policy.

SuperGemma4-26B multimodal Q8_0 is quality-clean on this same small fixture set, unlike Qwen3-VL candidates, but it is not the preferred replacement: its MI210 decode (`80.35-83.87 t/s`) is slower than MiniCPM-o (`110.81-122.18 t/s`), and its MI210 residency uses about `42%` VRAM versus MiniCPM-o's about `11%`. Treat it as a quality-clean fallback/cross-check, not the leading service lane.

PaddleOCR-VL-1.6 is a separate document/OCR extraction specialist. The downloaded GGUF+mmproj pair loaded through the v7 MI210 `llama-server`; digit OCR decoded at `484.36 t/s`, invoice markdown extraction at `489.82 t/s`, and a realistic receipt full-extraction prompt included `CS00012465` at `487.55 t/s` over a 768-token cap. The Wave-3 `odl_bench` producer now writes `<stem>.md` predictions from GT page images and reuses the structural/table/reading-order scorer. Its first operational demo at `/mnt/raid0/llm/tmp/odl-paddleocr-vl-demo-20260717T200212Z/model_gated_row_set.json` processed `18/18` pages, captured one `peg-native` model error as an empty prediction, and reported median decode `485.30 t/s`, median page latency `2918.78 ms`, text-block edit distance `0.343019`, reading-order edit distance `0.337318`, and table TEDS `0.0`. A follow-up `html_tables` prompt-profile run at `/mnt/raid0/llm/tmp/odl-paddleocr-vl-htmltables-20260717T201106Z/model_gated_row_set.json` completed `18/18` pages with no model errors and improved reading-order edit distance to `0.285753`, but emitted zero HTML `<table>` tags, kept table TEDS at `0.0`, worsened text-block edit distance to `0.429062`, and slowed median latency to `3245.60 ms`. The table result makes this producer/runtime evidence plus a post-processing/parser gap, not a final document-parser quality win.

## Vision Escalation Mitigation

The Qwen3-VL-30B escalation row is faster than `worker_vision` on these short decode fixtures, but it is not production-quality-safe because it failed the chart fixture under all three tested shapes. The Qwen3-VL-8B MI210 candidate repeated the chart failure even though it was much faster. SuperGemma4 passes the fixtures but is slower and heavier than MiniCPM-o. MiniCPM-o with `--reasoning off` remains the leading candidate: it is quality-clean, fast on MI210, passed frontdoor co-residency, and the broader service matrix passed all active fixture/context pairs with idle residency free and active frontdoor mean `94.77 t/s` vs `96.33 t/s` alone. The earlier two-rep synthetic collision still shows active overlap can cost more when requests are forced to collide. The live stack still uses the Qwen2.5-VL artifact and projector that passed `4/4`, preserves port `8087`, uses a distinct 24-thread quarter mask, and emits no Qwen3-VL `override_kv` until the operator decides whether the MI210 service lane should become active.

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
| `Qwen3-VL-8B CPU candidate` | fixed fixtures | `10.81-13.39` | `6.35-6.86 GiB` | `6.34-6.85 GiB` | `18.15-20.39 GiB` | `2-3%` | `4/4`; slower than alias |
| `Qwen3-VL-8B MI210 candidate` | fixed fixtures | `109.61-125.72` | `1.02-1.68 GiB` | `1.02-1.67 GiB` | `18.11-19.20 GiB` | `11-12%` | `3/4`; chart failed |
| `MiniCPM-o CPU candidate` | fixed fixtures | `11.98-14.13` | `6.29-6.70 GiB` | `6.28-6.70 GiB` | `17.61-20.31 GiB` | `2%` | `4/4`; slower than alias |
| `MiniCPM-o MI210 candidate` | fixed fixtures | `110.81-122.18` | `0.96-1.20 GiB` | `0.95-1.20 GiB` | `17.59-18.13 GiB` | `11%` | `4/4`; isolated quality candidate |
| `frontdoor + MiniCPM-o MI210 co-residency` | mixed smoke | frontdoor `99.97`; MiniCPM-o `108.68` on 4-token answer | frontdoor `1.31 GiB`; MiniCPM-o `1.02 GiB` | frontdoor `1.22 GiB`; MiniCPM-o `0.93 GiB` | frontdoor `46.63 GiB`; MiniCPM-o `17.80 GiB` | `66%` combined | frontdoor 512-token text passed; MiniCPM-o chart answered `Tanzania`; no KFD PIDs after cleanup |
| `frontdoor + MiniCPM-o service matrix` | 2K/8K fixture overlap | frontdoor active mean `94.77`; MiniCPM-o active mean `85.22` | frontdoor `~1.65-1.72 GiB`; MiniCPM-o `~1.05-1.35 GiB` active | sampled per active pair | frontdoor `~47 GiB`; MiniCPM-o `~18 GiB` | `66-67%` combined | all `8/8` active fixture/context pairs passed; idle resident frontdoor mean `96.48 t/s` vs `96.33 t/s` alone |
| `SuperGemma4 CPU candidate` | fixed fixtures | `25.58-31.76` | `26.44-26.72 GiB` | `26.44-26.72 GiB` | `39.16-39.83 GiB` | `2%` | `4/4`; heavy CPU footprint |
| `SuperGemma4 MI210 candidate` | fixed fixtures | `80.35-83.87` | `1.47-1.87 GiB` | `1.47-1.86 GiB` | `39.10-39.95 GiB` | `42%` | `4/4`; slower/heavier than MiniCPM-o |

## Invalidated Rows

Do not use these as K35 default ingest evidence:

| Artifact | Invalidated scope | Reason |
|---|---|---|
| `/mnt/raid0/llm/tmp/k35-arch-ingest-2k-20260717T121543Z/` | ingest row only | used stale `ingest_long_context_cpu_moe4` / `qwen3next.expert_used_count=int:4`; the architect row in the same artifact remains valid |
| `/mnt/raid0/llm/tmp/k35-arch-ingest-8k-20260717T121645Z/` | architect 8K attempt and ingest row | architect attempt had a harness context-accounting bug; ingest row used stale MoE4 override |
| `/mnt/raid0/llm/tmp/k35-ingest-deep-20260717T122029Z/` | ingest deep rows | used stale MoE4 override |

## Remaining K35 Gaps

- `vision_escalation` has a fast quality-clean candidate now: MiniCPM-o Q4_K_M + vision projector with `--reasoning off` on MI210. The basic frontdoor co-residency smoke passed, the two-rep service-tax probe shows the synthetic active-collision bound, and the broader 2K/8K fixture service matrix passed `8/8` active overlaps with idle residency free and about `1.6%` average frontdoor tax. SuperGemma4 is also quality-clean on the fixture set but is slower and heavier. The remaining blocker is the activation/capacity decision: keep the active 8087 lane as the temporary Qwen2.5-VL CPU alias or flip to MiniCPM-o on MI210 with explicit scheduling policy.
- Replacement/admission A/B remains open for document specialization: PaddleOCR-VL now has artifact+runtime+first-extraction smoke evidence plus a guarded `odl_bench` Wave-3 producer and two scored demos. Prompt-only HTML-table recovery failed, so the remaining document gap is table post-processing / parser comparison and a matched LightOnOCR/ODL structural comparison. Qwen3-VL-8B has been tested and rejected as the active replacement unless a later tuned lane fixes the chart failure; SuperGemma4 has been tested and retained only as a quality-clean fallback/cross-check.
- Architect has valid 2K/8K optimized rows only. Deeper contexts exceed the production `-np 2 -c 16384` per-slot launch shape unless the operator authorizes a different architect launch.
- Multi-request stress rows remain optional/open. The MiniCPM-o/frontdoor service matrix is a targeted two-server coexistence check across fixtures and 2K/8K contexts, while the current canonical throughput-vs-context rows are still single-scenario quiet-host measurements.
- The Gemma4 draft-memory probe emitted a warning while fitting (`failed to measure draft model memory` because `Gemma4Assistant requires ctx_other`); throughput/acceptance still passed, but memory measurement for this lane needs a separate fix or external sampler.

## Next Measurements

1. Decide whether to activate the fast MiniCPM-o MI210 lane now that the targeted frontdoor co-residency, service-tax, and 2K/8K fixture service-matrix probes passed, or keep the current Qwen2.5-VL CPU alias pending multi-request stress data.
2. Add PaddleOCR-VL table post-processing / HTML conversion or compare another parser arm, then rerun the guarded `odl_bench` producer against LightOnOCR/ODL on structural/table/reading-order metrics.
3. If operator wants capacity beyond the current two-server service matrix, run a separate multi-request stress/text-tax matrix; do not blend it into the quiet-host single-role K35 rows.
4. Improve GPU memory precision if needed: current ROCm snapshots report percentage, not exact MiB, in this runner configuration.
