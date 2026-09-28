# DeepSeek-V4.1-Flash Evaluation (deepseek41)

**Status**: active. The port is built and the AutoKernel CPU campaign runs on it on anchor `00d118d44` (DS41 port
+ champion `90c12df42` fast loader).
- Run 10h launched 2026-09-26 ~10:57Z on research `d643d794`, after six AK lanes were merged (§C,
  DS41-C35..C37).
- Run 10i took over after the 13:37Z-15:03Z fixes (`77f8bf58`, `7037165f`, `b8d6a046`, `2a060a41`). Its first keep
  moved the anchor from `00d118d44` to anchor-gen-001.
- The planner's ~220 GB/s abstention premise was refuted by a full-screen readbw run (DS41-C36).
- **First keep 2026-09-26 on run 10i** (DS41-C39): `akm-ds41-gemm4xn-2x-unroll`, +4.535% paired and +7.304%
  compounded. The anchor is now anchor-gen-001, `cafb59c3bf67`. The keep is unconfirmed at serving (DS41-C47).
- DS41-C45 (continue past a keep) and DS41-C49 (carry-forward) landed; run 10j relaunched ~19:10Z on research `846bef21`.
- The epoch clause is ratified as P-AK-SEARCH-1-A3.1 (DS41-C40); the code switch (DS41-C44) landed in `136ad3d0`.
- **Second keep 2026-09-27 08:11Z on run 10k**: `akm-ds41-dense-q8-tb-prefetch`, +3.440% paired. The anchor is now
  anchor-gen-002, `c0ef3961` (pushed to the fork). Compounded bench vs the champion of record reads +7.111% with 2 keeps
  (it read +7.304% with 1), so host noise dominates the compounded figure. The serving gate's threshold trigger is armed
  (`fires_next: true` in `store/loop-status.json`). Q4_K X4_T (`akm-q4k-x4t-avx512`) was retired at 3/3 author attempts.
- **DS41-C57 resolved 2026-09-27**: the CPU-0 theory was refuted. The real ~+11% tax is sleeping libgomp barriers,
  caused by the fast loader's auto 32-thread reader team running before the 48-thread compute team under 96
  `OMP_PLACES=cores` places. The fix is a declared runtime arm (DS41-C59) plus a loader-default code fix (V6R-4c in
  `autokernel-champion-aggregate.md`).
- **DS41-C68, serving gate PROMOTE, 2026-09-28 ~01:15Z**: the serving gate (DS41-C47) fired on run 10m's
  every-4-keeps cadence — `outcome: promote`, serving effect +7.113% vs the verified 5.525% floor, bench
  compounded +9.642% over 4 keeps. Champion of record advanced `00d118d44876` → `a1faab471e83be12398fc4da57a4c7a7e3f75d77`;
  accumulator reset to 0. Detail: DS41-C68 below.
- **DS41-C59 adopted 2026-09-28 ~04:44Z**: the declared runtime arm `load-threads-48` went through the
  keep-grade A/B (correctness 04:07Z, 10-launch paired serving A/B 04:08-04:44Z) — effect **+8.606%**,
  `decisive: true`, admission `keep_grade_matched_serving_floor`, noise floor 3.469%. Receipt
  `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/store/runtime-adoptions/runtime-recipe-adoption-dfd1fec2e06ec71b.json`.
  Detail: DS41-C59 below.
- **Next (start here)**: fold the confirmed DS41-C68 bundle toward the champion as a full experimental
  candidate, and re-read the DS41-C47 A/A excursion under the now-adopted C59 runtime recipe (new
  measurement epoch); then DS41-C51, DS41-C46, C50, C48, and C42's durable trigger.
- Bring-up retrospective: `docs/design/autokernel-local-actor-bringup-retro-20260926.md`.
- The 2026-09-22 status line ("download in progress, no port yet") is history.
**Created**: 2026-09-22 (operator retargeting of INF-69: "translate the GLM-5.3-Flash handoffs to
target DeepSeek-V4.1-Flash instead (assuming they are applicable)")
**Priority**: MEDIUM — novel-under-test model replacing the deleted GLM-5.3-Flash
**Categories**: inference_serving, local_inference, kernel_architecture, speculative_decoding
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-77, replaces INF-69)
**Related**:
- [`../completed/glm53-flash-evaluation.md`](../completed/glm53-flash-evaluation.md) — predecessor (INF-69), closed when its subject was deleted; the gate structure below is translated from it
- [GLM-5.3 AutoKernel source handoff](../../docs/reference/models/glm53-autokernel-handoff.md) — MTP rollback/replay gate contract and the lessons that transfer (row-exact verify, per-depth parity, multi-ubatch MTP width, cross-model regression)
- [`../completed/deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md) and [`../completed/deepseek-v4-flash-0731-dspark.md`](../completed/deepseek-v4-flash-0731-dspark.md) — V4 port history; the quality-gate runner and comparator carry forward
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) (INF-31) — owns the generic sparse-attention gates; do not duplicate them here
- [`engram-conditional-memory.md`](engram-conditional-memory.md) (INF-13) — Engram research context; this model is the first production-scale Engram checkpoint on this host
- [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md) — VB-DSV41 write-side hook

## Artifact identity

| Field | Value |
|---|---|
| Official source | `deepseek-ai/DeepSeek-V4.1-Flash`, `DeepseekV41ForCausalLM`, `model_type=deepseek_v41`, 763.2B params, FP8 block scale [32,32] (`scale_fmt=ue8m0`, `expert_dtype=fp4`), ~510 GB safetensors (48 shards) |
| Official non-weight files | `/mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash/` (`inference/` reference impl incl. `model.py`/`engram.py`/`kernel.py`, `encoding/`, `evaluation/dsh-minimal.patch`, tech report PDF, config, tokenizer) |
| Official harness | `/mnt/raid0/llm/deepseek-harness` (github `deepseek-ai/deepseek-harness` @ `c36a83ff6b`, MIT) |
| Serving artifact | `antirez/deepseek-v4.1-flash-gguf` Q4: `.part1` 480.0 GB + `.part2` 38.6 GB, joined into `DeepSeek-V4.1-Flash-Q4.gguf` (482.98 GiB) under `/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/` |
| GGUF architecture | **`deepseek41`**, not `deepseek4`. Calibrated for antirez's ds4 Metal runtime (`antirez/ds4`, branch `ds4.1flash`) |
| Quant mix | Q4_K routed experts; Q8 attention projections, shared experts and output; F16/F32 elsewhere (e.g. `attn_compressor_kv` F16) |
| Engram tables | Native FP8 stored as GGML `I8`; `blk.N.engram_embd.weight` shape (264, 384006168): 256 FP8 bytes + 8 scale bytes per row; 188.83 GiB total; ds4 streams rows from disk |
| MTP / DSpark | **CORRECTED 2026-09-22 (DS41-B0).** `num_nextn_predict_layers=3` is the 3-block **DSpark drafter**, not 3 next-token heads: block of 5, bidirectional in-block, own 128-expert/top-3 MoE, rank-256 Markov head and confidence head, embed/head tied to the backbone (`inference/model.py:1032-1156`). It ships in the official shards 44-46 (~8 GB, 2,401 `mtp.*` tensors). **The antirez GGUF does NOT contain it** — its converter omits every `mtp.*`/`vision.*`/`aligner.*` tensor (`gguf-tools/deepseek41_quantize.py:149`), and the header we read confirms 1046 tensors, `blk.0-39` only, zero `mtp.*`. The earlier "MTP retained" reading came from the embedded HF-config KV string, which antirez writes and never reads. vcruz's GGUF strips it too. |
| Tensor names | V4-family llama.cpp names (27/36 per-block names identical to vcruz305's converted GGUF); antirez extras `attn_compressor_{gate,kv,norm}`, `engram_{embd,kv,q_norm,k_norm}` |

**Config deltas vs V4 (from `config.json`, verify each against `inference/model.py`)**: 40 layers,
hidden 5120, 384 routed experts / top-6 + 1 shared, `sqrtsoftplus` scoring; sliding window 128;
cross-layer KV sharing (`kv_source_layer_ids=[2,8,14,20]`); indexer sharing
(`index_source_layer_ids=[2,8,14,20,24,28,32,36]`, 32 heads × 128, `index_topk=512`); two-level
candidate block selection (`candidate_source_layer_id=20`, `candidate_topk_blocks=2048`,
`candidate_block_size=8`); hyper-connections `hc_mult=4`, 20 Sinkhorn iterations; Engram at layers
1 and 14 (max n-gram 4, 8 heads × 256). The config's `dspark_*` fields (block 5, target layers 37-39, Markov rank 256, noise token
128799) are **live, and their weights ship under the `mtp.*` namespace** — the earlier "no DSpark
tensors" reading was wrong (DS41-B0).

## Runtime status (verified 2026-09-22)

- Production v9 (`0db32c06e`) has `deepseek4` (upstream #24162) with indexer top-k, compressor,
  hyper-connections and a `LLM_GRAPH_TYPE_DECODER_MTP` graph (`src/models/deepseek4.cpp`). It
  does **not** register `deepseek41`, so the artifact cannot load on any production binary.
- Upstream convert PR ggml-org/llama.cpp#28696 (vcruz305, open) adds `deepseek41` conversion.
  Runtime WIP is on `vcruz305/llama.cpp` branch `runtime/deepseek41`: loader, Engram and
  hyper-connections are reported verified against the reference; sparse attention is still open.
  vcruz's GGUFs strip MTP.
- **Required path**: an experimental port. Per the CLAUDE.md four-step workflow it starts from a
  fresh branch off the current champion/production lineage, and it must include (a) an Engram
  FP8-row get_rows/dequant op for the I8-packed table and (b) native 3-layer MTP. **Speculative
  decoding is required by the operator.**

## Translated from INF-69 — findings that carry over (verify on deepseek41 before relying on them)

1. **Dense-mask risk.** GLM-5.2's generic DSA path computed top-k and then ran final attention
   over full KV with a mask. Establish whether `deepseek4`'s `build_lid_top_k` path gathers
   sparsely or masks, then whether the V4.1 candidate-block level changes that. Never claim
   long-context sparse-compute value without the answer.
2. **Top-k cap corruption.** On GLM-5.2 an under-sized final-attention cap corrupted output past
   the cap. Re-derive this for `index_topk=512` plus the 2048-block candidate stage; do not
   transfer thresholds.
3. **MTP gate contract** (from the GLM-5.3 port): parallel verification must be row-exact
   (batch non-invariance alone reproduced the first GLM mismatch). Parity at one draft depth
   proves nothing about another. Multi-ubatch prefill needs its own MTP selection-width
   regression. Rollback must restore every stateful surface: KV, compressor, indexer, the
   cross-layer shared KV/index state, and hyper-connection streams.
4. **Evidence contract** for any long-output, throughput or quality probe: streaming progress,
   retained trace logs, server-log timing extraction, a minimum completion-token floor, and
   in-window contention witnesses. A GLM Q8 "win" of 1.0497x was an 8.41-vs-1.82 CPU-equivalent
   load artifact. Record every quality claim with `(prompt tokens, top-k settings)`.

## Completed Scope

Completed detail: [through 2026-09-24](../completed/deepseek-v41-flash-evaluation-completed-through-2026-09-24.md) (§C C0-C19) and [through 2026-09-26](../completed/deepseek-v41-flash-evaluation-completed-through-2026-09-26.md) (§A, §B, §K, §B0 follow-on, §C, §C6, §T).

| Item | One-line outcome | Where |
|---|---|---|
| DS41-C0 | Canonical recipe fixed at `-t 48` (decode-favoring) from a t24/48/96 sweep. | §C |
| DS41-C1 | Recipe codified as `deepseek_v41_flash_recipe.py`, CANDIDATE grade, 23 contract tests. | §C |
| DS41-C2 | Campaign config prepared; surfaced the gpt-6-sol/lifecycle/competing-inference blockers. | §C |
| DS41-C2b-gate | Competing-inference gate fixed to a work-based (utime+stime) test, not existence. | §C |
| DS41-C2c | Dry run steps 1-3 pass (binary self-ID, linkage, critic/planner probes). | §C |
| DS41-C2d | `draft-dspark` speculation type added; recipe layer can now express DSpark. | §C |
| DS41-C2e | Enrollment argv-parsing defect fixed; campaign uses the manifest/snapshot route instead. | §C |
| DS41-C2b | Campaign launched 2026-09-23 18:06 (`serial_run` 1586972) on the DSpark greedy-batched recipe. | §C |
| DS41-C3 | Campaign confirmed to measure the spec-dec-ON surface via `external_draft`/`draft-dspark`. | §C |
| DS41-C5 | Seeded hypotheses (H1-H7) written to the campaign inbox with falsifiers. | §C |
| DS41-C12 | All three in-tree profilers (Engram/node/host) wired into the loop and proven on run 3. | §C |
| DS41-C13 | Campaign restarted as run 3 on a fresh store, anchor rebound to `ebb68dc55`. | §C |
| DS41-C16 | Schema-constrained repair turn added for actor JSON replies (TD-1 idiom). | §C |
| DS41-C17 | Planner seat moved to `qwen-gpu/qwen3.8-27b` (MI210 :8083) off the CPU planner. | §C |
| DS41-C19 | v10 folded-lineage fix landed so the first candidate record does not raise. | §C |
| DS41-A0..A2 | Antirez Q4 downloaded, joined and header-verified: 1046 tensors, arch `deepseek41`, zero `mtp.*`. | sibling §A |
| DS41-B0 | Port route decided: (c), build on v10 `deepseek4` with vcruz as reference only. | sibling §B |
| DS41-B1a/B1b | Port branch `experimental/deepseek41-port-20260923` off the champion; CPU+HIP green, linkage PASS. | sibling §B |
| DS41-K0 | 28 GLM-5.3 keeps ported onto v10 as `experimental/glm53-keeps-on-v10-20260922`. | sibling §K |
| DS41-B7a/B7b | Engram gather op built, harness ready, folded into the champion (`8df1b5cf2`, no emitters yet). | sibling §B0 |
| DS41-B10 | KV-key adapter + arch delta on the port (`f493088b3`). | sibling §B0 |
| DS41-B13/B13b | DSpark drafter wired: 17.85 t/s on batched verify (1.56x); block 2 is the recipe default. | sibling §B0 |
| DS41-C8 | Per-node profiler compiled in (`-DGGML_CPU_PROF=ON`, separate `build-prof/`). | sibling §C6 |
| DS41-C10a/C25 | Run 9 prerequisites met (champion ff, anchor `5a60152ae`, `-kvu` :8083); accepted on run 9c. | sibling §C |
| DS41-C20 | Plain opencode seat merged as the campaign default (research `21ca61b0`); C20d/f/g stay open. | sibling §C |
| DS41-C21 | Seat baseline handed to INF-78 §Baseline. | sibling §C |
| DS41-C22/C23 | A stop reaps in-flight actors; `symbol_annotate` resolves short names (research `1c7d0a2d`). | sibling §C |
| DS41-C24 | `EPYC_ROOT_REPO` off lane worktrees; the first `actor_call.v1` line verified. | sibling §C |
| DS41-C28 | Off-hours scheduling closed as moot (operator 2026-09-25: never hold AutoKernel for off-hours). | sibling §C |
| DS41-C29..C31 | op-scope gate fixed, checkpointed work resumes on relaunch, harness faults release claims. | sibling §C |
| DS41-C32 | Re-anchored on the fast loader (`00d118d44`); run 10 launched. | sibling §C |
| DS41-C35 | Six AK lanes merged to research main `d643d794`. | sibling §C |
| DS41-C36 | The ~220 GB/s abstention premise refuted (399.6-449.4 GB/s full screen). | sibling §C |
| DS41-C37/C38 | Run 10h launched; 133 clean worktrees removed. | sibling §C |
| DS41-C39 | First keep `akm-ds41-gemm4xn-2x-unroll`, +4.535% paired; anchor now anchor-gen-001 (confirm: C47). | sibling §C |
| DS41-C40 | Measurement-epoch clause ratified as P-AK-SEARCH-1-A3.1. | sibling §C |
| DS41-C44/C45/C49 | Epoch switch (`136ad3d0`), keep continuation (`eae75696`), carry-forward (`36ebe3a7`, `846bef21`). | sibling §C |
| DS41-T6/T6c | First llama-bench baseline (tg128 13.18 @t48, pp512 ~145 @t96, placement proven); sampler fixed. | sibling §T |

## Tasks

### A — Acquisition and reference

- All acquisition boxes (DS41-A0..A2) are done; detail in the completed sibling.

### B — Port (experimental only; production stays frozen)

- DS41-B0 (route (c): build on v10 `deepseek4`, vcruz as reference only), B1a (port branch) and B1b (CPU+HIP builds) are done; detail in the completed sibling.
- [ ] DS41-B2 — Arch registration and loader for `deepseek41`, with a tested antirez-name compat
  map and every tensor shape/type validated before weights load.
- [ ] DS41-B3 — Engram: a custom FP8-row get_rows plus dequant op for the I8-packed
  (264-byte row = 256 FP8 + 8 scale) table, bit-exact against `inference/engram.py` on sampled
  rows. Decide residency: the host has 1.1 TB RAM, so full-resident mmap is feasible, unlike ds4's
  disk-streaming design, but measure page-cache/NUMA placement rather than assume it.
- [ ] DS41-B4 — Hyper-connections (`hc_*`, 4 streams, 20 Sinkhorn iterations): reuse the
  `deepseek4` ops; confirm V4.1 parity including the MTP blocks' `hc_*`.
- [ ] DS41-B5 — Attention deltas: sliding window 128, cross-layer KV sharing, indexer sharing,
  and candidate-block selection. Correctness first; sparse-gather value is INF-31's gate.
- [ ] DS41-B6 — Native 3-layer MTP through `--spec-type draft-mtp`: load `nextn` blocks and
  dispatch `DECODER_MTP` for depths 1-3. Validate target/draft hidden-state semantics and index
  or KV sharing into draft iterations.

### K — GLM-5.3 AutoKernel keeps carried to V4.1

The GLM-5.3 CPU campaign left 28 kernel keeps that are **not in v10**. All touch generic
ggml-cpu code only (`quants.c`, `ggml-cpu.c`, `ops.cpp`, `iqk_dispatch.cpp`,
`iqk_gemm_kquants.cpp`, `iqk_quantize_min.cpp`): Q4_K/Q5_K/Q8 dot paths, FA, the lightning-indexer
f16 dot, MoE expert cohorts and row-exact MoE (`akm-moe-rowexact-qact-2d-partition` +18.168%,
`akm-moe-rowexact-weighted-slabs` +3.179%). V4.1's Q4_K routed experts, Q8 attention and DSA
indexer run on these paths. Every gain was measured **only** on
`serving:glm53-c463f601b-cpu-mtp-depth3-b2048-ub512`; none is a claim about v10 or about V4.1.

- DS41-K0 (the 28 keeps ported onto v10) is done; detail in the completed sibling.
- [ ] DS41-K1 — Cross-workload admission of the ported branch vs v10 on the current CPU roles,
  under the AutoKernel cross-workload keep gate: speed paired with quality/coherence, per keep or
  bisected. Survivors become a **v11 champion candidate** through the standard four-step workflow
  (full-candidate bench, no cherry-picks at promotion). The row-exact keeps must also pass the
  MTP exact-trajectory gates on an MTP role.
- [ ] DS41-K2 — Re-measure the surviving keeps on deepseek41 once DS41-T1 passes, and evaluate the
  11 in-flight candidates as AutoKernel seeds on the V4.1 surface.

### B0 follow-on — the work items the audit actually produced

Sources pinned 2026-09-22: antirez runtime `antirez/ds4` **`main` @ `0aaea5a238fb41a35106a551e73c8409dfb751ac`** (MIT, reusable with notice; the branch `ds4.1flash` named on the model card **does not exist**); vcruz `runtime/deepseek41` @ `5210c7c5`; official reference under `models/deepseek-ai/DeepSeek-V4.1-Flash/`.

- DS41-B7a, B7b-prep and B7b (Engram gather op built, harness ready, folded into the champion) are done; detail in the completed sibling.
- [ ] DS41-B7c — re-screen the op as an ordinary keep once the deepseek41 graph emits it, and run
  the synthetic harness then (cold/warm, p50/p90/p99) for the page-fault answer the port needs. (**AutoKernel champion deliverable** — see *Kernel work
  rides the champion*; author it model-agnostically and fold it into the champion, do not leave it
  in the port branch).** The artifact ships `blk.{1,14}.engram_embd.weight` as
  GGML `I8`, `[264, rows]`, `deepseek41.engram.encoding = "e4m3_e8m0_32_row264"`: 256 E4M3 bytes +
  8 E8M0 bytes, one scale per 32 columns, `val = ldexpf(e4m3(code), scale-127)`, NaN guard on
  `code&127==127 || scale==255`. **`ggml_compute_forward_get_rows` has no I8 case — it `GGML_ABORT`s,
  and CPU `supports_op` returns true, so it builds and dies at the first forward.** Two routes:
  (i) a new I8-row gather + 264→256 dequant op, keeping the file as shipped; (ii) an offline
  requantize of the table to MXFP4 (97.3 GiB, whose scale *is* ue8m0) or Q8_0 (194.6 GiB), both
  already get_rows-supported. Price (i) against (ii) before writing either.
- [ ] **DS41-B8 — Engram addressing, host side.** 24 rows per token per engram layer (3 n-gram
  orders x 8 heads), 48 per token, 12.4 KB of random reads per token, on the decode critical path
  with no prefetch depth (the 4-gram suffix ends at the token just sampled). **The GGUF ships the
  complete hash spec** — `engram.token_map` (129,280 -> 99,092 distinct, `pad_id=2`), per-layer
  primes and offsets — so the HF normalizer chain does NOT have to be reimplemented. Verified:
  the 24 primes of L1 sum to 384,006,168 and L14 to 384,016,682, exactly the tensor `ne[1]`, and
  the multipliers reproduce bit-for-bit. Hash is `h = id0*m0`, then `h ^= idj*mj` for j=1..3,
  `row = h % prime[col] + offset[col]`. Bit-exact or garbage; no multi-probe, no collision handling.
- [ ] **DS41-B9 — Residency.** antirez `munmap`s the engram region after load
  (`ds4.c:2761-2796`) and `pread`s each 264-byte row through a separate fd, 16 concurrent readers,
  sorted and deduped, no LRU. Our v10 already auto-registers tensors >4 GiB as lazy mmap ranges
  with `POSIX_MADV_RANDOM` and suppresses `MAP_POPULATE` — **test that first**, it may approximate
  the same behaviour for free. Never with `--mlock`, `--no-mmap` or `--direct-io`. With 1.1 TB RAM,
  fully resident is also viable; measure page-fault cost per decode step either way.
- DS41-B10 (KV-key adapter + arch delta, `f493088b3`) is done; detail in the completed sibling.
- [ ] **DS41-B11 — RoPE and norm deltas.** RoPE covers only the last 64 of 512 dims as
  **interleaved adjacent pairs** (not NeoX half-split), and the **inverse rotation is applied to the
  attention output** because the cache holds one shared rotated latent; YaRN applies only on
  compressed layers at `compress_rope_theta=160000`, pure-SWA layers use theta=10000 with YaRN off.
  `rms_norm_eps=1e-20`, and the top-k normalization hardcodes 1e-20 rather than norm_eps.
- [ ] **DS41-B12 — Three unresolved graph divergences** (answerable only by reading `ds4.c`'s V4.1
  graph against `src/models/deepseek4.cpp`, do this first in B1): (a) the artifact has **no
  `output_hc_*`**, so how V4.1 collapses the 4 hyper-connection streams at the head is unspecified
  by the weights; (b) `attn_compressor_gate` exists on layers {2,8,14} but **not on layer 20**
  (ratio 1), so layer 20's compressor is an ungated projection; (c) ratios 1/2 vs our 4/128 change
  the pooling factor and therefore the DSv4 cache geometry.
- DS41-B13 (DSpark drafter wired, 1.56x on batched verify) and B13b (block 2 is the recipe default) are done, with their superseded in-progress and original-scope boxes; detail in the completed sibling.
- [ ] **DS41-B14 — Rollback is value-level, not a position rewind.** Every cache here is
  destructively mutated: the 128-slot window ring for all blocks, the compressor's fixed-size
  `kv_state`/`score_state` accumulators on the 4 kv-source layers, the compressed-KV and indexer
  row writes that fire only when a group completes, and the n-gram hash state. The accumulators
  cannot be undone by rewinding a counter — the pre-step slot values must be saved. A naive port of
  `llama_kv_cache_seq_rm` corrupts them silently. This is the precondition for DS41-T4.

### C — AutoKernel campaign (operator-directed 2026-09-23)

*"Start an autokernel routine to improve everything about the champion kernel running this model on
CPU"*, with *"I DO NOT CARE ABOUT BASELINE, ONLY MAX PERFORMANCE"* and **spec decode in the recipe**.

Closed §C items (C10a, C20 with C20a-c/e/h, C21-C25, C28-C32, C35-C40, C44, C45, C49) are in the completed siblings; the Completed Scope table indexes them.

- [ ] DS41-C4 — **Engram profiling: designed and prepared 2026-09-23**
  (`/mnt/raid0/llm/tmp/ds41-engram-profile/`, two patches, `git apply --check` clean against
  `7c18bb8c1`; not applied yet because the DSpark runtime patches land on the same files first).
  Split so the op keeps no `deepseek41` symbol: op-side counters keyed by the *table address*
  (champion), engram-side counters in `llama-dsv41-engram.*` (port), joined at run time by `dlsym`
  so `libllama` gains no dependency on the CPU backend; an op slot maps to a layer by row count, so
  the model file needs no edit.
  **Level 1 is ~0.013% of a 78 ms token**: calls, rows, bytes, thread-0 span + log2 histogram, host
  hashing time, the decode-step wall as denominator, plus per-layer distinct rows, repeat-of-previous
  and a simulated row cache at 4K/64K/1M/4M rows. **Level 2 (~0.2-0.5%/token) attributes minor vs
  major faults** per thread via `getrusage(RUSAGE_THREAD)`, and the artifact records `fault_source`
  so a level-1 zero can never be misread as "no faults".
  **The first number: gather share of the decode step.** 48 resident random reads cost ~4.8 us
  (0.006% of a token); 48 major faults cost ~4.8 ms (~6%). So if the share is under ~1%, **Engram is
  exonerated and the whole lever table dies at once** — which is exactly the result worth getting
  before a campaign spends its budget there.
  **Already refuted without running anything: prefetch, for plain decode.** All 24 columns include
  the token just sampled, so no column is knowable early; prefetch is reachable only behind
  speculative decoding. Not measurable and deliberately not faked: a resident-row *hit* (residency is
  only the absence of a fault, so re-hits undercount and can never become a hit rate), TLB/LLC/DRAM
  traffic, and whether Engram explains the flat 24->96 scaling at all — that needs a comparison arm,
  which is a protocol, not a counter.
  Remaining scope: time in the gather vs the rest of the token, rows/bytes touched, **major vs minor page
  faults** (disk vs page cache have opposite fixes), row-index distribution (does a cache pay?), and
  a machine-readable per-run artifact split by layer (1 and 14 differ). Prepared under
  `/mnt/raid0/llm/tmp/ds41-engram-profile/`.
- [ ] DS41-C4b — apply the profiling patches after the DSpark runtime lands, rebuild, and run an A/A
  first: every overhead figure above is arithmetic, not measured. Note the phase classifier
  (`n_tokens==1` -> decode) breaks once the 5-wide drafter lands, and the dlsym link surface is
  untested.

- [ ] DS41-C14 — `--node-profile` is opt-in in `run.py` (default OFF) because run.py's hermetic
  fixtures would gain a real build + a second launch if it defaulted on. Make the fixtures opt out
  explicitly, then flip the default so no future campaign can launch without the instrument.
- [ ] DS41-C15 — `node_profile` semantics under speculation: `llama-host-prof` counts one batched
  verify call as `n_eval=1`, so `decode_us_per_token` is per graph eval, not per token, when DSpark
  is on (carried as a limitation string; needs a no-drafter cross-check to state the ratio).
- [ ] DS41-C18 — **27B planner overflows its slot context** (found 09:42, run 7): `:8083` runs `-c 196608 -np 2`
  → 98,304 tokens per slot; the planner session passed it at ~45 agentic steps (103,679 and 98,441-token
  requests refused), and opencode recovered by `agent=compaction` (self-summary), which costs a call and
  drops detail each time. Levers, in order of cheapness: (a) `-np 1` on `:8083` while it serves the
  campaign (stack owner's; the role is idle otherwise); (b) cap tool-output bytes in the actor prompt;
  (c) opencode `--attach` with a larger `-c`. Measure proposals/hour before and after.
  Lever (b) now exists as the bounded seat's `tool_output` cap + output-capped MCP tools (DS41-C20);
  measure C18 on the `bounded` arm before reaching for (a) or (c).
  First data point (bounded v1, 2026-09-24): lever (b) alone did NOT prevent the overflow — tool output fell to
  42k chars yet the slot filled (97.7k) at step 12 from the model's own deliberation (1,626 decoded tokens/step);
  re-read C18 against bounded v2 and the plain arm (DS41-C20c) before choosing between (a) and (c).
  A/B read (C20c): every arm still compacted once (plain within 23 steps, bounded v2 at step 32) — opencode's
  conversation is append-only, so capping tool output only delays the overflow; the structural fix is a REPL
  context (INF-78 OAB-7/OAB-8), not lever (a)/(b)/(c).
- [ ] DS41-C10 — Watch run 7 (27B planner, schema repair active, started 09:10) into its first measured
  iteration; report planner→critic→author→build→A/B timings against the CPU planner's 41–97 min. Original:
  `state/loop-status.json` + `store/` (the 48 A/A launches each reload 519 GB, ~2 h); confirm the
  serving floor lands with a unit, the planner's first proposal cites the inbox, and the critic
  answers. Kill only `state/serial-run.pid`'s tree, verify dead.
  History of runs 7-9 under this box, including the closed DS41-C10a, is in the completed sibling (§C — DS41-C10 history).
- [ ] DS41-C27 — **The dry run must check the store's champion of record against the anchor.** Run 9's dry run
  returned rc=0, and the live launch was then refused on COR `ebb68dc55` ≠ anchor `5a60152ae`. A refusal found
  only at launch costs an off-hours window. Fix: `serial_run --dry-run` (and `run.py`'s dry path) reads the store's
  COR the same way the live preflight does and fails with the same refusal text. The failure should name the two
  remedies: the DS41-C13 fresh-store route, or rebinding the anchor. Test: a store whose COR differs from the
  resolved anchor makes the dry run exit non-zero with that reason; a matching store passes.
  **Still open 2026-09-25.** Run 10's re-anchor on `00d118d44` took the fresh-store route again, by hand (the old
  store is archived as `store-run9d-cor-5a60152ae/`). Nothing in the dry run checked the COR, so this is the second
  anchor change that relied on a manual comparison.
- [ ] DS41-C33 — **Read run 10's first results on anchor `00d118d44`.**
  - The half-screen floor is written. Compare its interval and between-launch SD with `5a60152ae`'s 5.789%
    (2.91-9.55%): the loader changed, the decode kernels did not.
  - Record the mean launch time over the whole series and the calibration's total wall, against run 9's ~4 h.
  - The hoist, now admitted by op_scope, is built and measured on this anchor, from the inbox patches or from a
    fresh proposal. It would be the first measured candidate for `mul_mat_qX_K_q8_2_X4_T`.

  Acceptance: the floor file path, the launch-time mean, and the hoist's measured disposition (keep, reject or
  refused, with its reason) are recorded here.
- [ ] DS41-C34 — **Delete the partial build dir left by the re-anchor, once the operator confirms.**
  `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925/build-cpu-cc-partial-20260925` is not used by run
  10 (its binary is `build-cpu/`). Deleting it needs an explicit operator confirmation.
- [ ] DS41-C41 — **25 dirty REVIEW worktrees from the 2026-09-26 inventory need an operator look.**
  - They are listed in `/mnt/raid0/llm/tmp/worktree-inventory-20260926.md` (REVIEW class).
  - Per worktree: keep, commit and push, or remove.
  - Never `--force`, and never `git worktree prune`.
- [ ] DS41-C42 — **Retention trigger default vs actual disk.**
  - The default `--retention-trigger-free-gb 400` can no longer be satisfied: 398 GiB was free with nothing
    reclaimable, so run 10h needed a manual 350 override.
  - Options:
    - (a) lower the default below the steady-state free space;
    - (b) make the trigger relative to what retention can actually reclaim, with no refusal when reclaimable = 0;
    - (c) keep 400 and reclaim disk.
  - Recommendation: (b), because it cannot go stale as the disk fills.
  - Acceptance: a relaunch with no override passes on today's disk.
  - 2026-09-27: run 10k refused on disk (`state-run10k-refused-disk`); the trigger was lowered **by hand to 300 GiB**
    for the relaunch. On operator approval, 24 of this session's worktrees were removed (330 → 381 GiB free). Audit:
    `/mnt/raid0/llm/tmp/disk-leak-audit-20260927.md`. The hand override is not the fix; (b) is still open.
- [ ] DS41-C43 — **Re-base the C6 ladder arithmetic on the 2026-09-26 readbw.** C6's "~165 GB/s gemv-pattern
  ceiling" comes from INF-70 C0 (2026-09-02). That predates the 2026-09-21 BIOS change.
  - On the full screen, today's gemv-2560 is 377.5 GB/s at 48 threads and 475.9 at 96.
  - Keep the operator's gate and target (30 / 45-50 t/s). Only re-derive the BW → t/s rows.
  - Repeat the reading on an idle host before quoting it as the ceiling.
- [ ] DS41-C46 — **CPU keep anchor builds at `-j1`: check gcc `-j64` reproducibility.**
  - R23-40 (`f4f13116`, 2026-09-04) moved `build_champion` to `-j1` because hipcc gfx90a `libggml-hip.so` is not
    reproducible at `-j64`. The rule applies to CPU/gcc campaigns too, where it costs ~1 h per keep with 95 cores
    idle.
  - R23-40's own probe found the CPU `llama-bench` executable byte-identical across `-j64` builds. It did not
    check the library the CPU anchor guard hashes.
  - Test: build the current champion's CPU tree twice at `-j64` in clean, separate build dirs, and compare the
    anchor guard's code digest (the same `anchor_integrity.build_digest` input the CPU guard uses).
  - If A = B, and it holds on a repeat under concurrent lane-build load, allow parallel anchor builds for CPU
    campaigns only. HIP stays at `-j1` until R23-41 (hipcc determinism flags).
  - If the digests differ, record which object differs and keep `-j1`.
  - The build takes CPU cores, so schedule it under a region claim that does not overlap a live measurement.
- [ ] DS41-C47 — **Confirm the first keep at the serving gate.**
  - Operator 2026-09-27: let the loop's serving gate decide (fires at 13.81% compounded or every 4 keeps); no early
    confirmation run. The keep's commit `cafb59c3` is now durable on `fork/experimental/fastload-ds41-20260925`
    (it was local-only). Not in `ak/champion` / v10.
  - After the gate confirms a bundle: fold it toward the champion as a full experimental candidate (fresh v10 +
    the confirmed sgemm keeps, validated as a whole — never a promotion-time cherry-pick). The gemm4xN change is
    generic tinyBLAS Q8_0 (n=2..8), so also A/B a production CPU Q8_0 role with multi-token verify before v11.
  - `akm-ds41-gemm4xn-2x-unroll` measured +4.535% on the paired A/B and +7.304% compounded (DS41-C39).
  - But its anchor-guard A/A read **+19.443% between two builds with identical code digests** (the "R21-10
    instrument excursion"). That is four times the keep's own delta, on the same code.
  - Until the serving gate fires (13.81% compounded, or every 4 keeps), quote the keep as "+4.535% paired A/B,
    unconfirmed at serving".
  - 2026-09-27: keep 2 (`akm-ds41-dense-q8-tb-prefetch`, +3.440% paired, anchor-gen-002 `c0ef3961`) joined the chain.
    The compounded bench fell from +7.304% (1 keep) to +7.111% (2 keeps), which is noise, not a regression. The
    loop's status reads fire threshold 3.885% with `fires_next: true`. Quote both keeps as paired A/B, unconfirmed
    at serving. The DS41-C57 barrier-sleep regime (up to 13% request spread) may also explain the +19.4% A/A excursion;
    re-read the A/A after DS41-C59 lands.
  - Acceptance:
    - the serving gate's verdict on the chain containing this keep is recorded here;
    - the A/A excursion is explained (host drift, launch variance, or instrument) or bounded by a repeat A/A.
  - **2026-09-28 ~01:15Z: the serving gate fired on the every-4-keeps cadence (run 10m), verdict `promote`**
    (`serving_decisive: true`, +7.113% serving vs the verified 5.525% floor, +9.642% compounded bench). First
    acceptance bullet satisfied; detail in DS41-C68. Second bullet (the A/A excursion) is still open — not
    re-read after DS41-C59. Item stays open until DS41-C59 lands and the A/A is re-read, and until the confirmed
    bundle is folded toward the champion as a full experimental candidate.
  - **2026-09-28 ~04:44Z: DS41-C59 is now ADOPTED** (`load-threads-48`, +8.606%, `decisive: true`; detail in
    DS41-C59 below). The A/A excursion re-read is unblocked but not yet done — it must run under the newly
    adopted runtime recipe's recalibrated floor (a new measurement epoch per the adoption receipt's floors rule).
    Item stays open until that re-read runs and the bundle is folded toward the champion.
- [ ] DS41-C48 — **A freshness gate on seeded numeric evidence in the campaign inbox.**
  - A stale "~220 GB/s" read ceiling, which predated the 2026-09-21 BIOS/config change, drove 13 batches of
    planner abstention (DS41-C36). The real figure was 399.6-449.4 GB/s full-screen.
  - Fix: every hard numeric ceiling seeded into `store/inbox/` carries its measurement timestamp and the host-config
    identity it was taken under. When a planner abstention cites a ceiling older than the last host-config change,
    re-measure it before a second abstention on the same ground.
  - Acceptance: a stub campaign seeded with a pre-change ceiling triggers the re-measure path instead of a
    repeated abstention.
- [ ] DS41-C50 — **An in-run keep still recalibrates 48 launches for the new anchor.** `ensure_source_floor` after an
  in-run keep does not reuse the COR arm's verified matched floor, unlike the startup path (4598cb87). Harmless at
  `--batch-iterations 1` (each batch restarts), a real cost at >1. Fix: reuse the COR frame's floor in-run, as at startup.
- [ ] DS41-C51 — **AK-H-NRI-1 falsifier (NUMA interleave of CPU_REPACK).** Operator hypothesis in
  `store/inbox/50-numa-repack-interleave-reassess-20260926.md`. The DS41 recipe already runs under `numactl
  --interleave=all`, which should interleave the repack allocation process-wide. A read-only `numa_maps` probe of the
  loop's own champion llama-server is armed (`/mnt/raid0/llm/tmp/ds41-scope-20260926/numa_maps_probe.py`, log beside
  it). Append the per-node page split to the inbox note; if skewed (>25%±10pp off), add a repack-alloc route to the
  admitted scope so the loop can port and A/B it.
- [ ] DS41-C52 — **Dense Q8_0 `gemm4xN` follow-ups from the GEMM-ladder intake (stage1, dives running).** Inbox note
  `store/inbox/41-ds41-gemm-ladder-hypotheses-20260926.md`: GGML_IQK_Q8_0=1 runtime arm (operator: let the loop
  propose it), spill check, offset-trick VNNI (bit-identical), B-scale hoist, zmm widening. Track what the loop tries.
  Stage-2 dives landed as intake-1822/1823 (renumbered from 1783/1784); the dives did not change the CPU set (not
  ladder-derived; stands on its own merit); add a static spill check of the gemm4xN disassembly before timing any
  register-raising variant (intake-1823#record).
  - Loop tries so far: B-side software prefetch in `gemm4xN` kept 2026-09-27 as `akm-ds41-dense-q8-tb-prefetch`
    (+3.440% paired, anchor-gen-002). The GGML_IQK_Q8_0 runtime arm has not been proposed yet.
  - PARKED 2026-09-27 (operator): one follow-up has landed through the loop: B-side prefetch, kept as `akm-ds41-dense-q8-tb-prefetch` (+3.440% paired, anchor-gen-002 `c0ef3961`). The GGML_IQK_Q8_0 runtime arm, offset-trick VNNI, B-scale hoist and zmm widening have not been proposed, and the static gemm4xN spill check is not built; resume by adding the static spill check of the gemm4xN disassembly (needed before any register-raising variant is timed) and leaving the remaining ideas to the loop through inbox note 41.
- [x] DS41-C53 — **Correctness oracle must exercise non-constant per-block scales.** Verify the AK kernel-mutation
  oracle's fixtures use varying Q8_0 `d` and Q4_K `d/dmin`/sub-scales. intake-1825 §5.3 reports a scale-layout bug on
  gfx90a that constant-scale fixtures hid (intake-1825#record). Read-only check; fix the fixture if constant.
  ✅ 2026-09-26 — research `f2f6d54c`: the CPU quant oracle fixture now varies every per-block scale.
- [x] DS41-C54 — **Observation first: `attn_wo_a` grouped projection at nt=1.** From an existing DS41 profile, read
  the `attn_wo_a` node share and path: a 3D batched Q8_0 `ggml_mul_mat` over groups with a permuted src1,
  `src/models/deepseek41.cpp:1219-1224`. If material, admit a dedicated M=1 grouped-GEMV route to the AK scope. The GPU
  analogue in intake-1825 §8.3 is self-reported; CPU transfer is unproven.
  ✅ 2026-09-27 — **NEGATIVE** (`store/inbox/51-ds41-attn-wo-a-grouped-projection-20260926.md`). The share clears 2%
  but none of it is grouped-specific. At serving N=3 the node already runs the shared `gemm4xN<3>` after the Q8_0
  src1 conversion makes it contiguous. A dedicated M=1 grouped GEMV targets nt=1, which serving does not run; its
  only specific nt=1 cost is one extra barrier (~0.15%). No route admitted.
- [x] DS41-C55 — **ak-check passed vacuously after a keep.** ✅ 2026-09-26 — research `a17284a2`. With the anchor build
  at `store/anchor-gen-001` (outside the source tree), `anchor_root_of()`'s `.git` walk returned the store, every changed
  TU read "no compile command", and ak-check returned NOTHING/exit 0: authors got no feedback and the best-of winner check
  passed a Q4_K patch that critic2 proved wrong (run 10j, ~3.9 h round). Root now from CMakeCache `CMAKE_HOME_DIRECTORY`;
  an unmappable changed source is status `error` (exit 2), never a pass. Applied live (the shim runs ak_check.py by path).
- [x] DS41-C56 — **Medium-author wall cost: 2 h timeout + uncharged retry.** Run 10j round 1: a1-medium timed out at 7200 s,
  was retried as a harness failure, and spent another 6667 s (total ~3.9 h) while a0-off gave up at 61 min. Decide a
  per-member wall budget for best-of (e.g. cap medium at ~60-75 min, or stop retrying a timed-out member when the other
  member already finished) and measure its effect on panel yield vs wall.
  ✅ 2026-09-27 — research `164cfb0e` (`13ad4317`, operator 2026-09-27): best-of author wall budgets 45/75/90 min, no
  in-round retry of a timed-out member, early cancel once the panel is decided. The yield-vs-wall effect is read from
  the loop's own actor metrics as batches accrue; it is not a separate experiment.
- [x] DS41-C57 — **Host contention on CPU 0 inflates thread-0-bound nodes (inferred).** The hc RMS_NORM node is ~42 µs wall
  but only 12-15 µs of its own work (chain ~10 µs, cold/cross-NUMA input +1-4 µs, barrier ~2.3 µs); ~25 µs is threads 0-2 slow
  or late. DS41's OMP `spread` puts threads 0/1/2 on CPUs 0/2/4; CPU 0 carries 14.6% lifetime sys time (vs 1.8% on 2/4) and
  ~3x the interrupts, and co-resident production CPU llama-servers pin their main thread to CPU 0 plus one compute thread per
  CPU on 0-95. May also feed the +19.4% A/A excursion. Probe (CPU window, needs inference): pinned profile
  `GGML_CPU_PROF_NNODES_EQ=5966 GGML_CPU_PROF_THREADS=1` with `/proc/stat` user/sys/irq sampled on CPUs 0/2/4. If confirmed,
  A/B DS41 with `OMP_PLACES` starting at CPU 2 (spread kept) — a recipe/epoch change needing operator sign-off — and review
  production CPU-server pinning. Evidence: `/mnt/raid0/llm/tmp/normsplit-route-20260927/bench/`, note draft 53.
  ✅ 2026-09-27 — **the CPU-0 theory is REFUTED; root cause found.** Findings and decision packages:
  `/mnt/raid0/llm/tmp/ds41-c57-cpu0-20260927/DS41-C57-findings-and-decision-packages.md` (21 launches in two CPU windows,
  under the CPU region claim, every PID verified dead).
  - The ~10 µs of dead time per hc node is libgomp barrier **sleep**: 60-95k voluntary switches per OMP thread.
  - Cause: the fast loader's AUTO reader team (`llama-model-loader.cpp:1689`, `min(32, max)`) runs 32 threads before the
    48-thread compute team under `OMP_PLACES=cores` (96 places), which leaves libgomp throttled for the process.
    Arms with or without CPU 0 sleep alike when there are 96 places. `--load-threads 48` spins, and so does a
    48-place list.
  - Spinning arms: 22.4-22.6 tok/s, request spread ≤0.3%. Sleeping arms: 19.6-20.6 tok/s, spread up to 13%. That is
    about **+11%**. `GGML_REPACK_THREADS=48` and `OMP_NUM_THREADS=48` still sleep.
  - CPU 0 itself costs ≤0.2% (run-queue wait). Production runs LLVM libomp with `KMP_BLOCKTIME=10`, so this libgomp
    defect is not expected there; that is unmeasured.
  - Follow-ups: DS41-C59 (runtime arm), V6R-4c (loader default), DS41-C60 (on-CPU hc-norm gap), DS41-C61 (production
    root-thread sampling), VB-DS41-C57 (vidya).
- [x] DS41-C59 — **Declared runtime-arm swap at the next DS41 boundary: `--load-threads 48`.** The DS41-C57 fix, taken
  through the loop's own keep-grade runtime-arm path (research `4d676163`, `--runtime-arms`, `--runtime-arm-evidence
  keep_grade`), as ratified in P-AK-SEARCH-1-A4 (root `101ed1b0`: bit-exact runtime recipes only, adoption is an epoch
  boundary).
  - Primary arm: `--load-threads 48` (`LLAMA_ARG_LOAD_THREADS=48`), with `OMP_PLACES=cores` and everything else unchanged.
    Measured once (1 launch): 22.59 tok/s, spinning.
  - Fallback arm A2: `OMP_PLACES={2}:47:2,{1}`. 22.45 tok/s over 2 launches, spinning. It moves every thread off its
    historical CPU.
  - Declare both at a batch boundary (no mid-batch relaunch). The matched compare against the current recipe decides.
  - Acceptance: the adoption receipt (evidence=keep_grade, floor sha, raw samples) is recorded here. The new epoch's
    floors are recalibrated, and older rows are labelled as the sleeping-barrier regime.
  - ✅ **ADOPTED 2026-09-28T04:44:07Z** — after the post-DS41-C68 promotion serving-floor recalibration
    (~01:15-04:07Z), the loop ran the declared arm `load-threads-48` (kind `load_threads`, candidate 48) through
    the A4 keep-grade path: correctness check 04:07Z, 10-launch paired serving A/B 04:08-04:44Z. Effect
    **+8.606%**, `decisive: true`, admission `keep_grade_matched_serving_floor`, noise floor 3.469%. Adopted
    runtime_surface_digest `905a37f1…`, execution_digest `cdb0535c…`. Receipt:
    `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/store/runtime-adoptions/runtime-recipe-adoption-dfd1fec2e06ec71b.json`.
    Fallback arm `omp-places-48-sib` (`{2}:47:2,{1}`) remains declared, not adopted. Per the receipt's floors rule,
    the next source comparison (DS41-C47's A/A re-read, DS41-C51, …) recalibrates the request-bound floor under
    this adopted recipe — a new measurement epoch per A4/OP-60. Progress:
    `progress/2026-09/2026-09-28-ak-ds41-main.md`.
- [ ] DS41-C60 — **The ~20 µs on-CPU hc-norm gap in serving.** Thread-0 compute on the hc RMS_NORM is 32-33 µs in
  every C57 arm (spinning or not), against ~12 µs in the isolated micro-bench. Run-queue wait is ≤0.2% and stime ≤2%,
  so the time is on-CPU work. Candidates: producer spread across CCDs/quadrants and `numactl --interleave=all` placing
  the input remote. Observation first, from the existing C57 per-node profiles, before any route or recipe change.
- [ ] DS41-C61 — **Production CPU root-thread sampling (C57 decision package B, P0).** The root threads of :8074 and
  :8070 are hard-pinned to CPU 0 (:8080's to 0/96), and whisper can land there. Sample the root threads' schedstat
  run-queue wait under real concurrent traffic in the next production-affecting window; two samples during load. Any
  placement change goes through `stack-change` and the operator's signature. Proposal P1 (distinct root places) is
  expected to be worth <0.5%.
- [x] DS41-C58 — **RMS_NORM within-row split route: built, bound too small.** ✅ 2026-09-27 — research `6b73fce2`
  (`cpu_norm_rowsplit` route, bit-identity + float64 reference, GDB witness incl. the fused variant). Measured: the bit-exact
  split saves ~0.1% (every task re-runs the serial 20480-add chain); a multi-accumulator sum (1-ulp, tolerance route) caps at
  ~0.5-0.6%. Not placed as a hypothesis (note 53 stays DRAFT); the real cost is DS41-C57.
- [x] DS41-C62 — **`float_tinyblas_plan` route for the hc_mixes F16 GEMM.** ✅ 2026-09-27 — research `29b2b350`
  (`565d6f3b`; its commit subject says "DS41-C55", a label collision with the ak-check item above). hc_mixes (F16
  [20480, 24], 80 nodes per verify) ran a 3-thread tile plan with 45 threads idle, 4.6-5.2% of the cycle. The route
  admits only the class `tinyBLAS::matmul` tile plan (bit-exact for F32/F16/BF16), with a GDB witness and float
  reference arms. Inbox note `52-ds41-hc-mixes-20260926.md` drives the planner.
- [x] DS41-C63 — **CPU windows: the loop yields its CPU-region claim during actor phases.** ✅ 2026-09-27 — research
  `5aadf3a4` (`90dd8201`, operator proposal relayed by workspace-8d). `--cpu-window-yield on` (default) releases the
  claim while no lane holds the tail and re-acquires it for every tail session and measurement window. The window is
  published to `/mnt/raid0/llm/autokernel/cpu-window.json` (state, est_close_at, cpus_reserved_by_loop, heartbeat).
  Used the same day to hand CPU windows to workspace-8d (UFH-12, HS-4, HS-19a).
- [x] DS41-C64 — **ak-check refuses cores a peer measurement holds.** ✅ 2026-09-27 — research `c85370d4`. Before a
  compile or op-test, ak-check reads region-lock occupancy read-only. If another role holds its cores, it waits up to
  `AK_CHECK_PEER_WAIT_S` (600 s), then refuses naming the peer (`peer_wait_s`, `refused_peer` in the metrics).
- [x] DS41-C65 — **Keep-grade evidence for declared runtime arms.** ✅ 2026-09-27 — research `4d676163`
  (`--runtime-arm-evidence keep_grade`, the default with `--runtime-arms`). A declared bit-exact arm is measured by
  `serving.compare` against the current recipe's matched floor; a decisive keep writes the selection artifact and
  adoption receipt and opens a new runtime-surface epoch. The governing rule is P-AK-SEARCH-1-A4, ratified on operator
  authorization (root `101ed1b0`). The operator chose to leave as written the older gap where 5-pair keep-grade source
  keeps sit below the "search-grade requires ALL of" text. DS41-C59 is its first use.
- [x] DS41-C66 — **Fused-helper dot witness broke on a helper the DS41 lineage never calls.** ✅ 2026-09-27 — research
  `1f7979d4`. `iqk_witness.run_fused_probe` put its helper breakpoint only on `iqk_moe_fused_up_gate`; the DS41
  llama.cpp lineage has no caller for that function, so the gate refused every `akm-ds41-q4k-x4t-weight-prefetch`
  candidate with `gate_refused` / `oracle_unavailable` ("exact fused helper and dot specialization hits in candidate
  DSO not proven", runs 10k 11:37Z and 10m 19:25Z) for the kernel carrying ~29% of sampled decode cycles
  (`mul_mat_qX_K_q8_2_X4_T`). GDB-traced on anchor-gen-002: the fused up-gate graph runs as two MUL_MAT_IDs through
  `iqk_mul_mat_moe_rows` (1 activation row) and `iqk_mul_mat_moe` (2+ rows). Fix: the dot witness now breaks on all
  three trusted IQK MoE helpers, still requiring first stop in the candidate DSO and first dot hit exactly the
  expected quant/width; `check_fused` unchanged. Verified end-to-end on the live candidate build: Q4_K+Q5_K widths
  1-8, 16/16 pass. Regression test added. Deployed: live run worktree `research-ds41-run10` moved to `1f7979d4`; the
  refused patch `43982b2b` has a build-stage resume checkpoint so it goes straight to the corrected gate plus
  measurement.
  - [x] Watch the first resumed build-stage checkpoint of `akm-ds41-q4k-x4t-weight-prefetch` pass the corrected
    Q4/Q5 dot witness and reach measurement. ✅ 2026-09-27 — satisfied in substance, not literally: a
    **re-authored** patch of the mechanism (batch 2 loaded the fixed witness), not the resumed build-stage
    checkpoint of the earlier refused patch (`43982b2b` / `e4ce1b1f`), passed the corrected Q4/Q5 dot witness at
    20:08Z and was measured and kept as `47b6865de` (+5.683%, DS41-C68 keep 3).
  - [ ] Triage the pre-existing research test failures surfaced alongside this fix (identical to baseline, not
    caused by `1f7979d4`): wider than first scoped — 72 failures across 22 files in the autokernel loop suite
    (e.g. `test_serial_roster`, `test_serving::LifecycleObservationHook`, `test_validation_semantic_adapter`,
    `test_gpu_runtime` x2, `test_seed` x3, `test_aggregate_feedback` x2, `test_native_server_t0_witness` errors).
- [x] DS41-C67 — **`oracle_unavailable` gate refusals were burning authoring attempts and orphaning build
  checkpoints.** ✅ 2026-09-27 — research `0a117b03`. After DS41-C66, the loop still could not recover the
  critic-accepted patch `e4ce1b1f` of `akm-ds41-q4k-x4t-weight-prefetch`: its three `oracle_unavailable` refusals
  (11:41, 19:25, 19:46Z) were each classified as an authoring failure (2 of 3 attempts spent), and their build
  checkpoints were refused by `resume.py` as "a verdict on the patch rather than a rule." `gate_rules_fingerprint`
  also hashed only `gates.py`, so the C66 oracle fix re-opened nothing. Fix: `oracle_unavailable` joins the rule
  gates in `loop._RULE_GATES` and `resume.RULE_GATES` (no authoring attempt spent; checkpoint resumes once the
  gate rules fingerprint changes), and `gate_rules_fingerprint` now also hashes `ORACLE_MODULES`. Resumed patches
  still re-run every current gate. 3 regression tests added in `test_resume.py`. Loop suite failure set identical
  to unmodified main (72 failures in 22 files, all pre-existing). Verified: dry scan of the live DS41 store shows
  the `e4ce1b1f` build checkpoints go from refused to ELIGIBLE (outrank the author checkpoint). Deployed: live run
  worktree `research-ds41-run10` moved to `0a117b03`; the next batch's child picks it up.
- [x] DS41-C68 — **Serving gate (DS41-C47) fired, PROMOTE.** ✅ 2026-09-28 (~01:15Z), run 10m. The every-4-keeps
  cadence fired the serving gate: `outcome: promote`, `serving_decisive: true`, serving effect **+7.113%** against
  the verified 5.525% serving floor; bench compounded **+9.642%** over the 4 keeps. Champion of record advanced
  `00d118d44876` → `a1faab471e83be12398fc4da57a4c7a7e3f75d77`; the accumulator reset to 0.
  - The 4 keeps: `akm-ds41-gemm4xn-2x-unroll` +4.535% (`cafb59c3b`), `akm-ds41-dense-q8-tb-prefetch` +3.440%
    (`c0ef39613`), `akm-ds41-q4k-x4t-weight-prefetch` +5.683% (`47b6865de`, 2026-09-27 ~20:50Z),
    `akm-ds41-q4k-x4t-weight-prefetch` +1.074% (`a1faab471`, ~23:18Z). Compounded bench after keep 3: +8.891%;
    after keep 4: +9.642%. Anchor guards, both inside the 5.525% floor: gen-003 +2.376%, gen-004 -2.202%.
  - Keeps 3-4 were unblocked by DS41-C66 (research `1f7979d4`) and DS41-C67 (research `0a117b03`).
  - Progress: `progress/2026-09/2026-09-28-ak-ds41-main.md`.
  - Follow-on: fold the confirmed bundle toward the champion as a full experimental candidate (fresh v10 + the
    confirmed keeps, validated as a whole) per DS41-C47's acceptance clause; not yet done.
  - DS41-C59 (`--load-threads 48` runtime-arm swap, keep-grade A/B per P-AK-SEARCH-1-A4) is now **ADOPTED**
    (2026-09-28 ~04:44Z, +8.606%, `decisive: true`); detail in DS41-C59.
- [ ] DS41-C26 — **A stop during floor calibration must stop launching.** DS41-C22 covers actor calls only.
  Measured when run 8 stopped (2026-09-24 ~15:32Z): TERM to `serial_run` and `run.py` drained, calibration started
  its next `matched_process_v2` launch (llama-server 3961920), and ending the run needed KILL on `run.py`,
  `serial_run` and the calibration server.
  - Fix: calibration consults `should_stop()` before each launch, and on a stop it TERMs its own captured
    llama-server pid, never a name pattern. Discard the partial floor, and never cache it.
  - Test: a fake calibration launcher with a stop asked mid-series → no further launch, the child is reaped, and
    the process exits.
- [ ] DS41-C11 — Pre-existing test failures found while landing `5125f7ab`, reproduced on a clean HEAD
  checkout: `test_existing_cpu_run` (3: `oracle()` unexpected kwarg `require_reference`) and
  `test_serial_roster` (3: "issued selection awaits settlement"). Not this session's change; fix or
  re-fixture.
  **Re-checked 2026-09-25 on research `605e8301`** (orchestrator venv pytest, cores 72-79):
  - `test_existing_cpu_run` passes (the `oracle()` stand-in was fixed by `535391b6`);
  - `test_serial_roster` still fails 3 of its tests, with the same `SerialSchedulingRefused: … issued selection
    awaits settlement`.

  That half is still open.
- DS41-C20 follow-ups still open (C20 itself ✅ 2026-09-24: plain seat merged as the campaign default, research `21ca61b0`; its detail and C20a-c/e/h are in the completed sibling):
  - [ ] DS41-C20d — **cache perf output in `actor_tools_mcp`** so `profile_top` / `symbol_annotate` run `perf report`
    once per (profile, dso, sort) and serve later calls from the cache; then re-run the bounded arm once on the same
    driver. Bounded's 12-minute wall deficit in C20c is tool time, and its proposal was the better grounded one.
    **Progress 2026-09-24 (evening, reduced-scope build): the cache is built and measured. The re-run is still
    pending, and the premise may be wrong.**
    - Built on research `lane/ak-perfcache-20260924` `f4a5d240` (unmerged, 111 tests): `perf_cache.py`, plus
      `actor_tools_mcp` `cache=`, which the live server always constructs. An optional `cpu_profile` prewarm is
      gated behind `AK_PERF_CACHE_PREWARM=1`, default OFF.
    - The key is the exact perf argv plus the profile's identity (realpath, size, `mtime_ns`, first/last-1 MiB
      hash) plus a memoized `perf --version`. `limit` never reaches perf, so one report serves every limit.
    - The cache lives beside, never inside, the integrity-checked `cpu-raw` dir.
    - Real run-7 profile (25.7 MB): uncached `perf report` 1.283 s, cache hit 0.0012 s, byte-identical.
    - **The premise is doubtful.** 1.3 s per call cannot explain a ~12-minute deficit, `annotate` is unmeasured,
      and the plain seat never calls these tools: the C20c plain export shows 25 calls, `{bash 11, glob 1,
      read 13}`, 0 MCP. The per-call metrics row (`actor_call_metrics.v1`, research `lane/ak-turns-20260924`
      `0bf2d7c2`) is what will show where the bounded seat's time went. Techniques write-up:
      `autokernel-orchestrator-actor-backend.md` → *Techniques learned in the opencode seat*.
    - Closes when the bounded arm is re-run once on the same driver with the cache and the metrics rows, and the
      deficit is attributed: to tool time from step timestamps, or explicitly "unknown" if the export lacks them.
    - [x] DS41-C20d1 — perf report/annotate cache built and measured (`f4a5d240`); built, not yet re-run ✅ 2026-09-24
    - [ ] DS41-C20d2 — re-run the bounded arm once with the cache and the metrics rows (after the integration lane
      merges; campaign-idle GPU window) and attribute the C20c deficit, or record it as unattributed
  - [x] DS41-C20f — **the plain planner reads the anchor build tree instead of its lane.** Run 8's first tool call ✅ 2026-09-25 — closed by INF-78 OAB-11 (research bdd0a951, lane guard: reads lane 4 / anchor 0, builds 0).
    went to `/mnt/raid0/llm/llama.cpp-experimental-deepseek41-20260923/...` (the target JSON's build dir), not to
    `workers/laneN`. A proposal grounded in the anchor tree can disagree with the lane's source. Point the
    context's source path at the lane and label the build dir "binary only". Fix task: INF-78 OAB-11.
  - [x] DS41-C20g — **the plain planner compiled `.o` files into `/tmp` despite "never build".** It burns CPU during ✅ 2026-09-25 — closed by INF-78 OAB-11 (research bdd0a951, lane guard: reads lane 4 / anchor 0, builds 0).
    a planner call (a competing-work witness hazard, DS41-C2b-gate) and ignores the directive. Deny compiler
    invocations to planner `bash` via `permission`, or detect them in the per-call metrics (tool parts naming
    `cc`/`c++`/`cmake`) and flag them. Fix task: INF-78 OAB-11.

### C6 — Targets (operator, 2026-09-23) and the arithmetic behind them

- [x] DS41-C6 — **Gate 30 t/s, target 45-50 t/s, CPU decode.** Operator agreed to this ladder
  rather than a single number, because the two halves have different costs. ✅ 2026-09-23

  | achieved read BW | kernel-only | x speculation 1.56 |
  |---|---|---|
  | 101 GB/s (today) | 11.6 t/s | **17.85 measured** |
  | ~165 GB/s (this host's gemv-pattern ceiling) | 19 t/s | **~30 = the gate** |
  | 250 GB/s | 29 t/s | ~45 |
  | 460.8 GB/s (sequential theoretical) | 53 t/s | ~83 (not reachable by decode) |

  **Do not quote 460.8 as the roofline for decode.** INF-70 C0 measured this host under the
  access pattern that matters: **gemv-pattern 153 GB/s at 48 threads, 167 at 96** (read-sum
  152.6/165.6; copy 212). Decode is a gather of 4-bit blocks with dequant, not a sequential
  stream, so ~165 GB/s is the pattern ceiling and we sit at ~61% of it, not 22% of 460.8.
  The remaining 3x to theoretical needs the access pattern to change, not better kernels.

  **Past ~45 t/s the lever is BYTES, not bandwidth**: dense attention is 5.01 GiB/token against
  4.56 GiB for the routed experts, and the two output projections alone are 2.99 GiB, still Q8.
  Taking those to 4-bit is ~1.4x on its own and compounds with streaming and with acceptance.
  Anything past ~60 t/s needs a quantization change whose quality cost is unmeasured — earn it,
  do not promise it.
- [ ] DS41-C7 — **Per-op-class achieved bandwidth, before the campaign starts.** The 101 GB/s is
  blended and the 8.7 GB/token is derived, not measured. The profiler (now actually compiled in,
  DS41-C8) reports bytes and GB/s per weight path. If the dense projections stream near 165 while
  the expert gather sits at 60, those are different problems with different fixes — and today we
  cannot tell them apart. Run this first; it decides where the campaign aims.
  - [x] DS41-C7a — first per-op-class decomposition from the in-loop node profile (DS41-C36):
    - dense Q8_0 tinyBLAS: 40% of the cycle at ~52% of peak;
    - `MUL_MAT_ID` Q4_K: 32% at 82-94%;
    - barrier/straggler wall: ~21%.

    ✅ 2026-09-26. C7 stays open: record absolute GB/s per weight path and state the peak basis. That peak basis
    moved with DS41-C43.
- [ ] DS41-C9 — **Host-side blind spot the node profiler can never see**: the dsv4 compressed-cache
  plan (visibility counts, five index vectors, the full `[n_kv, n_tokens]` mask) is rebuilt on the
  host **every ubatch** in O(n_tokens x ratio) loops, as is the engram hash and its 48-row scatter.
  At long context this is plausibly the dominant host term. Patch 0002 accumulates host phases per
  graph-input class; apply and verify it reconciles (attributed + unattributed within 5%).

### T — Gates (translated from INF-69 T0-T4 / T0-SPEC / T15)

- [ ] DS41-T1 — Load plus short-context coherence smoke on CPU with the canonical env (abort on
  repetition loops). Record `(arch, index_topk, candidate settings, window)` from the load log.
- [ ] DS41-T2 — Sparse-attention disposition: dense-mask vs sparse gather, and a top-k /
  candidate-block cap semantics probe **before** any quality run (findings 1-2). Correctness
  findings also update INF-31.
- [ ] DS41-T3a — **Prompt-rendering parity is available today**: `encoding/encoding.py` is a
  pure-stdlib renderer with 5 byte-exact goldens, and `tokenizer_config.json` has **no
  chat_template**, so `encoding.py` is the only normative prompt spec — any llama.cpp template is a
  fresh re-derivation. DSML tool tags are space-prefixed (`" calls"`, `" invoke"`, `" parameter"`),
  which is the V4->V4.1 delta. Gaps: the goldens cover 5 of ~10 paths, 4 of 5 end in EOS, and
  double-BOS against llama.cpp's own BOS handling is unverified. **The official harness is NOT a
  usable parity instrument**: it is a TypeScript agent framework speaking the Anthropic Messages
  protocol, needing Docker and external DeepSWE task images; llama-server's OpenAI endpoint cannot
  serve it without a provider-adapter patch.
- [ ] DS41-T3 — **Reference parity**: logits/top-k tokens vs the official `inference/` reference
  on a manageable fixture (the FP8 reference cannot run full-size on this host; use a layer-
  truncated or per-op comparison), plus the V4 quality-gate runner/comparator
  (`epyc-inference-research/scripts/benchmark/v4_quality_gate_{runner,compare}.py`). Run the
  `deepseek-harness` evaluation path (`evaluation/dsh-minimal.patch`) as the model-native task
  harness. Separate quantization drift (Q4_K experts vs FP4/FP8 source) from port defects.
  - *2026-09-23 (intake-1508):* before any KLD/divergence claim, audit whether the reference is a dequantized upcast of
    the FP8/FP4-native release (a 'BF16' release can sit on the FP8 grid, as shown for GLM-5.3-Flash) and name it
    `dequantized_from_quant` in the claim.
- [ ] DS41-T4 — **MTP exact rollback/replay**: forced rejection at every draft position; all
  accepted, none accepted, repeated cycles; rollback continuation vs replay of the accepted
  prefix; full vs chunked prefill; state save/restore; both KV-shared and index-shared layers.
- [ ] DS41-T5 — **Full-model trajectory gates**: plain vs MTP exact parity over the
  multi-prompt set (GLM precedent was 31 pairs), with real draft rejection witnessed. Measure
  depths 1/2/3 separately; depth parity does not generalize.
- DS41-T6 (first llama-bench baseline) and T6c (placement-sampler fix, with its superseded original box) are done; detail in the completed sibling.
- [ ] DS41-T6b — repeat at claim grade once the operating point is fixed: unit=launch, n>=3, the
  noise floor with its unit, and a serving-shaped run (`llama-server`, np sweep) — llama-bench
  tg128 must never be quoted as a serving rate.
- [ ] DS41-T6 — Throughput baseline at the canonical CPU recipe (interleave, no-mmap, t48/t64,
  r5), plain vs native MTP, prefill and decode separated. Observation-grade first.
- [ ] DS41-T7 — GPU (MI210) path. The 483 GiB model cannot be VRAM-resident, so scope what can
  (hybrid offload of attention/shared/MTP) and measure it with proven residency.
- [ ] DS41-T8 — **Performance admission vs champion** (**acceleration-path caveat**: if the
  experts land as MXFP4, they are served by CPU_REPACK's AVX2 `mxfp4_8x8_q8_0` GEMM and **not** by
  iqk — `iqk_typeA_supported` excludes MXFP4/NVFP4 — so a comparison against a Q4_K MoE baseline
  compares two different acceleration paths, and the INF-70 iqk work the rest of the fleet relies
  on does not apply. NVFP4 cannot even be produced here: `llama-quant.cpp` throws on that ftype.): run the cross-model CPU and HIP
  regression on the full candidate before any champion fold. GLM's core passed its own gates but
  held a −25.71% Flash-Next CPU signal. AutoKernel gets a pointer only after this passes (see D).
- [ ] DS41-T9 — Role/quality fit per the standard suites; GO / WAIT / KILL disposition with the
  disk-retention decision (~483 GiB in the novel-under-test keep bucket until this verdict).

### D — Downstream

- [ ] DS41-D1 — AutoKernel source handoff (`docs/reference/models/deepseek41-autokernel-handoff.md`)
  on the GLM-5.3 template: exact branch/commit, build and launch recipe, mandatory MTP gates, and
  the objective (MTP-on output tok/s under exact trajectories).
- [ ] DS41-D2 — Wire the belief kernel: add the `deepseek41` validation/serving producer row to
  `scripts/vidya/adapters/README.md` and complete VB-DSV41 **before the first measured run**
  (DS41-T1). Project through `claim_tuple.grade()`; categorical parity verdicts stay categorical.

## Not carried over from INF-69 (GLM-only)

- **KDA recurrent attention and conv-state rollback** — V4.1 has no linear/recurrent attention layers.
- **`kpool` pooled-key semantics** — GLM-specific; the V4.1 analogue (compressor plus 8-token
  candidate blocks) is re-derived under DS41-T2, not inherited.
- **GLM-5.3-Flash-DFlash2 drafter** — deleted, and GLM-specific. V4.1 uses native MTP. The config's
  `dspark_*` weights DO ship, under `mtp.*` — see DS41-B7.
- **T5-T14 GLM kernel experiments** (Q8 prefill, expert multirow, batched Q8, CPY outer rows) —
  measured on GLM shapes; the results live in the GLM docs. Re-test only on V4.1 profile evidence.
- **`glm5next`/`glm5-next` alias compatibility** — GLM naming.
- *mHC is **not** dropped*: V4.1's `hc_*` hyper-connections are the same family and are covered by DS41-B4.

## Constraints

### Kernel work rides the champion (operator directive, 2026-09-23)

*"If any custom kernel work is required, make it part of an autokernel champion."* So the port
splits in two, by where the code lives and how it is proven:

| Layer | Where it lives | How it is proven |
|---|---|---|
| Model/graph: arch registration, loader, KV-key adapter, compress-ratio and RoPE deltas, DSpark graph | `experimental/deepseek41-port-20260923` only | DS41-T gates (parity, MTP, coherence) |
| **Custom kernels**: the Engram I8/E4M3-row gather + dequant (DS41-B7), and any GEMM/quant work the port turns out to need | authored as **model-agnostic ggml commits** and folded into the AutoKernel champion `ak/champion/llama-cpp-<frozen-short>` | AutoKernel measurement against the champion's current headline, then folded in and the headline re-measured |

Rules that follow:
- A kernel commit must not depend on `deepseek41` symbols. The Engram op is a **generic I8 row
  gather with an E4M3+E8M0 264-byte row layout**, usable by any model that adopts that layout.
- Base every kernel lever on the **current champion tip**, never on this port branch and never on
  pristine upstream; measure against the champion's current headline, fold in on validation, and
  re-measure the headline immediately. Production promotion stays separately operator-gated.
- The port branch **rebases onto the champion** whenever the champion moves, so the port never
  accumulates on a stale tip (the INC-20260706 rule).
- Consequence for the schedule: DS41-B7 is an AutoKernel deliverable with its own keep gate, not an
  inline patch in the port branch. Its acceleration-path caveat is in DS41-T8.
- This also puts the 28 GLM-5.3 keeps on the same track: DS41-K1 admits them into the champion, and
  the port inherits them by rebasing, rather than by carrying a second branch.

- Production kernels are frozen; all work goes on `llama.cpp-experimental` branches. The
  `llama.cpp-deepseek-v4` tree (antirez's V4 fork) is reference only.
- Experimental inference runs under held physical CPU-region claims; host-health caveats stay explicit.
- Do NOT add a `model_registry.yaml` role without operator approval.
- Every launcher sets its own `LD_LIBRARY_PATH` and proves linkage (three ggml generations on host).
