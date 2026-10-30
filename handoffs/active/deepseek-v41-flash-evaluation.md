# DeepSeek-V4.1-Flash Evaluation (deepseek41)

**Scratch**: `/mnt/raid0/llm/tmp/ds41-1017-swap/` (DS41-W; KEEP-marked until W7 lands)

**Status**: active. The port is built and the AutoKernel CPU campaign runs on it on anchor `00d118d44` (DS41 port
- **2026-10-22 08:4xZ operator directive: every DS41-1017 test except the noise floor is DISREGARDED until AutoKernel kernel work is done** ("not meaningful until kernel research work has been performed first"). The 06:30Z 24-pair floor (DS41-W5b-floor, 2.862%) stands. These are deferred and their runs cancelled, none ticked: W5b-compare, W6.2, W6.1, W5.1a (+ qdq build-test), W5.1a-floor (until the operator launches AK on a changed anchor), W8a, T3.2, T3.3c, T5.1.1, C7.2, CONF.1, T7.1a. Still live: W8c (done), W8d, the floor registration, and W7.2 (Sept DSpark rm, pending operator).
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
- **2026-10-04 lanes PARKED for the backlog drain** (operator 05:45Z): the Q38FN lane stopped 05:50Z (before
  calibrating), DS41 parked 06:03:08Z with `WATCHDOG3_HOLD` set. Shared schedule
  `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md`; :8083 stays parked until the backlog is exhausted (operator's
  final word). Restart plan: DS41-C121.
- **2026-10-04 all-keeps fold** (fold ledger: [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) →
  *all-keeps fold (candidate "Y")*): the DS41 port and the 7 serving-gated keeps (bundles `a1faab471` +7.113% and COR
  `053c3bd82` +11.18%) are in the global champion, now `b0ba1d427` after three more folds the same day. The 14 held
  keeps failed two bundle gates and stay off it (rebased as Z' `70e7133a1`, DS41-C125). C112 resolved (culprit
  `9b148baab`, shape-gated). **DS41 and Q38FN both relaunched on `b0ba1d427` 2026-10-05** after a bundle-ancestry
  refusal and a fresh-store fix (DS41-C126) — see DS41-C121/C126 for the chain, the unlanded fixes (a)-(c) and the
  calibration-priority ruling (d).
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

**2026-10-20: swap to the 1017 finetune in progress (§W).** Serving moves to antirez's 1017 MXFP4-experts 9-shard build; the Sept Q4 row above is retired at DS41-W7.

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
   **2026-10-04 (code reading, DS41-C123):** V4.1's final attention masks densely (−inf over all compressed rows)
   and concatenates the full compressed plane every step; it does not gather sparsely.
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
- [x] ~~DS41-B6 — Native 3-layer MTP through `--spec-type draft-mtp`: load `nextn` blocks and~~ (closed 2026-10-29 audit: SUPERSEDED → Premise corrected by DS41-B0 (:74): nextn x3 blocks are the DSpark drafter, wired as draft-dspark in DS41-B13/B13b (Completed table :155-156; 1.56x); draft-mtp path not applicable)
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
- [x] ~~DS41-K2 — Re-measure the surviving keeps on deepseek41 once DS41-T1 passes, and evaluate the~~ (closed 2026-10-29 audit: SUPERSEDED → Replaced by the DS41 AutoKernel campaign (section C, run 10+; keeps re-measured on deepseek41, e.g. C39/C68, :20-37) and C107 seed ledger (:950))
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
  - *(2026-10-20, workspace-f8.)* RoPE (interleaved pairs, inverse rotation, YaRN placement) anchored and MATCH; only the top-k renorm epsilon remains: official model.py:825 adds 1e-20, ours clamps 6.1035e-5 at src/llama-graph.cpp:2260 @ dd3d9721c; evidence /mnt/raid0/llm/tmp/zero-inference-20261020/DS41-B12.1/REPORT.md.
- [x] **DS41-B12 — Three unresolved graph divergences** (answerable only by reading `ds4.c`'s V4.1
  graph against `src/models/deepseek4.cpp`, do this first in B1): (a) the artifact has **no
  `output_hc_*`**, so how V4.1 collapses the 4 hyper-connection streams at the head is unspecified
  by the weights; (b) `attn_compressor_gate` exists on layers {2,8,14} but **not on layer 20**
  (ratio 1), so layer 20's compressor is an ungated projection; (c) ratios 1/2 vs our 4/128 change
  the pooling factor and therefore the DSv4 cache geometry. ✅ 2026-10-20 closed by DS41-B12.1: (a) head collapse, (b) layer-20 ungated compressor, (c) ratio 1/2 geometry all MATCH official model.py vs champion dd3d9721c (evidence `/mnt/raid0/llm/tmp/zero-inference-20261020/DS41-B12.1/REPORT.md`); DS41-B11 stays open for the top-k renorm epsilon only.
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
- [x] ~~DS41-C18 — **27B planner overflows its slot context** (found 09:42, run 7): `:8083` runs `-c 196608 -np 2`~~ (closed 2026-10-29 audit: SUPERSEDED → Text :317-319: structural fix is a REPL context (INF-78 OAB-7/OAB-8), not levers (a)-(c); C20c showed every arm compacts once)
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
- [x] ~~DS41-C10 — Watch run 7 (27B planner, schema repair active, started 09:10) into its first measured~~ (closed 2026-10-29 audit: OBSOLETE → Run 7 watch box; runs 7-9 history moved to completed sibling (:326); campaign is at run 10s and later 1017 swap)
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
- [x] DS41-C42 — **Retention trigger default vs actual disk.** ✅ 2026-10-29 (audit: research 0a82880e0 (2026-09-27) 'serial build retention never refuses above a hard floor (DS41-C42)' on origin/main, option (b) 'no refusal when reclaimable=0') [no-belief: audit-reconciliation]
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
- [x] DS41-C46 ✅ 2026-10-23 — **CPU keep anchor builds at `-j1`: check gcc `-j64` reproducibility.**
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
  - **PASS (2026-10-23, job `ds41-c46-j64-repro`, done 16:52Z on q2; `/mnt/raid0/llm/tmp/ds41-c46/RESULT.json`).** Four clean
    `-j64` builds of champion `141e4bcf5`: A and B serial, C and D concurrent under load. `object_digest` identical across all
    four (303 objects, `e6802d0e…`); only informational difference is `tools/ui` `ui.cpp.o` (known non-deterministic web-UI
    bundle). Libs: `libggml-base` SAME; `libggml-cpu`, `libggml`, `libllama` EXPLAINED (code identical, build-path/build-id
    only) via libcmp. Closes the "holds under concurrent lane-build load" clause; `-j64` CPU anchor builds stay valid
    (`anchor_build_jobs`, research `f1bf8d17d`). HIP stays `-j1` until R23-41.
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
  - **2026-10-04: the fold half is done.** The confirmed bundle (and the COR bundle) folded into the global champion
    with the 2026-10-04 all-keeps fold (`1bceceb05` → `61bdb185c`; ledger in `autokernel-champion-aggregate.md`;
    DS41 X vs COR −1.56%, floor 4.533%, not decisive, i.e. the gated keeps reproduce on the new base). The
    gemm4xN production-Q8_0-role A/B before v11 and the A/A excursion re-read remain; the item stays open on those.
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
  - **2026-09-28 08:21Z**: after the DS41-C59 recipe's floor recalibrated to 1.876% (DS41-C69, batch 5 anchor
    `fe8ee8f3…`), the fallback arm `omp-places-48-sib` was measured +1.340% on top of that floor — below it, so
    `runtime_observed` and not adopted. Batch 6 returned to source authoring. Progress:
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
  - 2026-09-28 (DS41-C70, batch 6): a follow-on hypothesis on this route, `akm-ds41-hcmix-narrow-m-plan`,
    measured **−3.833%** — a DECISIVE regression against the new 1.876% floor (09:52Z); rejected.
  - 2026-09-28 (DS41-C72, 21:33Z): a second plan-only variant, `akm-ds41-float-tinyblas-rowplan`, measured
    **−6.586%** — a second DECISIVE regression on the route; rejected. See DS41-C72 follow-up on closing the
    route if a third plan-only variant is proposed.
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
    confirmed keeps, validated as a whole) per DS41-C47's acceptance clause. **Done 2026-10-04**: all-keeps fold
    `1bceceb05` → `61bdb185c` (ledger in `autokernel-champion-aggregate.md`).
  - DS41-C59 (`--load-threads 48` runtime-arm swap, keep-grade A/B per P-AK-SEARCH-1-A4) is now **ADOPTED**
    (2026-09-28 ~04:44Z, +8.606%, `decisive: true`); detail in DS41-C59.
- [x] DS41-C69 — **Floor carry-forward + serving-gate cadence 8.** ✅ 2026-09-28 (~06:30-08:40Z), `ak-ds41-main`.
  Operator directive 2026-09-28 ("let's be more clever about this. Wasting sooo much time over this is silly."):
  stop recalibrating the serving noise floor (~3 h, 48 launches) after every source-only champion-of-record
  promotion; operator also chose (AskUserQuestion) to raise the serving-gate keep cadence from 4 to 8 (amends
  R23-54; the +13.8% fire_multiple threshold trigger unchanged; operator can always force an advance).
  - Governance finding: no ratification needed — `measurement/protocols/kernel-research.md` already says the
    campaign noise floor φ "is a property of the instrument under this host state, not of any candidate";
    P-AK-SEARCH-1-A4 requires recalibration only after a runtime-recipe adoption. The per-execution-identity
    floor keying was a research-lane code choice.
  - Research commits on epyc-inference-research main: `41f7ba71` (floor carry-forward: `_carry_forward_floor` /
    `_select_source_floor` in loop/run.py; lookup order exact tip floor → COR floor → carried-forward lineage
    floor → 24-pair calibration; carries only the newest valid floor of the SAME runtime recipe hash, only when
    every anchor-guard A/A on the current anchor after that floor is `anchor_verified` within it; read-only;
    provenance `carried_forward` + `serving_floor_carry` record; `--no-floor-carry-forward` restores old
    behaviour; 12 tests in `test_floor_carry_forward.py`; failure set identical to main) and `6787ee00`
    (`SERVING_GATE_EVERY_KEEPS` 4→8; cadence behaviour tests pin `every_keeps=4` explicitly;
    `test_the_ruling_is_eight_keeps`). The cadence edit was first attempted by a subagent and refused by the
    auto-mode classifier because the instruction reached it as a mid-task coordinator message; the owning
    session, holding the operator's direct approval, applied it itself.
  - Dry check (read-only, live store): as of 01:15Z the carry would have picked the 5.525% floor (A/A 23:54Z
    −2.202%) and skipped the 01:15-04:07Z recalibration. Recipe changes still recalibrate by construction.
  - Deployed: live run worktree `/mnt/raid0/llm/worktrees/research-ds41-run10` moved to `6787ee00` (effective
    from the next batch).
  - Related: after the load-threads-48 adoption (DS41-C59, 04:44Z), the floor recalibrated under the new recipe
    (hash `fe8ee8f3…`) to **1.876%** (was 5.525%; ~3x tighter) at 07:45Z; the fallback arm `omp-places-48-sib`
    then measured +1.340% on top, below the 1.876% floor → not adopted (`runtime_observed`, 08:21Z). Batch 6
    returned to source authoring at 08:21Z. Detail in DS41-C59 above.
  - Progress: `progress/2026-09/2026-09-28-ak-ds41-main.md`.
  - [ ] Confirm the first post-promotion launch under the new code logs `request-bound floor … [carried_forward]`
    instead of scheduling calibration.
  - [ ] Test-isolation hazard found by the subagent: `test_runtime_keep_source_continuity` and one
    `test_serial_run` test hang while holding the real host lock
    `/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock` (on main too) — fix the isolation.
- [x] DS41-C70 — **Planner output cap 16,384 → 32,000.** ✅ 2026-09-28 (~11:25-11:50Z), `ak-ds41-main`. Two
  consecutive DS41 planner calls produced nothing (10m run): batch 7 `planner_transient budget_exhausted`
  (10:38Z — the session reached ~171k of the 196k context, opencode compacted, then burned the rest of the
  2700 s budget) and batch 8 `planner_transient output_capped_empty` (11:23Z — the final step was pure
  reasoning, 45.8k chars, hit the 16,384-token output cap, `finish=length`, 0-char report). No external
  traffic on :8083 at the time (only DS41's own opencode connected; the peer's UFH-13 pilot driver had been
  idle since 05:05Z).
  - Fix: research `9a64aec8` on epyc-inference-research main raises `DEFAULT_PLANNER_OUTPUT_LIMIT` 16,384 →
    32,000 in `loop/actor_opencode_config.py` — exactly opencode's own ceiling, so no `output_ceiling_env` is
    needed; the pool rule (output < context − 32768) still holds and the critic inherits the new limit; 237
    tests pass across the six actor test files.
  - Deployed: the live run worktree moved to `9a64aec8`, effective from the next batch (batch 9's planner
    still ran on the old 16,384 limit).
  - Also recorded: batch 6's `akm-ds41-hcmix-narrow-m-plan` measured **−3.833%**, a DECISIVE regression
    against the new 1.876% floor (09:52Z) — rejected (the tighter floor made a −3.8% call decisive).
  - [x] Follow-up: if planner `budget_exhausted` recurs after C70 (the context-growth/compaction path, batch
    7's mode), raise `--actor-planner-budget-s` from 2700 or cap planner tool-output size. Ties to INF-78
    OAB-34 (16384 output-cap hit rate per role) — OAB-34's premise changed for the planner now that its
    default is 32,000. ✅ 2026-09-28 — recurred on batch 9; resolved by DS41-C71 raising the wall budget.
    Tool-output capping was not needed.
- [x] DS41-C71 — **Planner wall budget 2700 → 4500 s.** ✅ 2026-09-28 (~12:10-12:25Z), `ak-ds41-main`. Batch
  9's planner (started before DS41-C70 deployed) also ended `planner_transient budget_exhausted` at 2700 s
  (12:08Z) — the third consecutive empty planner call (batches 7, 8, 9). Prompt size was unchanged (~120k
  chars) across the three; the failed sessions ran 21-39 tool steps with single reasoning steps of 15-16k
  output tokens (batch 7: 22 steps, compacted at ~171k context, 42.8 min; batch 9: 39 steps, 43.1 min, still
  working when cut). Cause: session length on the thinking-on 27B, not prompt growth.
  - Fix: research `5bb48c98` on epyc-inference-research main raises `--actor-planner-budget-s` default 2700 →
    4500 s in `loop/run.py` (matches the thinking-on author member budget; under `--actor-timeout-s` 7200;
    the planner phase holds no CPU measurement, so the longer wall costs only GPU time). Tests: 220 pass.
  - Deployed: the live run worktree `/mnt/raid0/llm/worktrees/research-ds41-run10` moved to `5bb48c98`,
    effective from batch 11 (batch 10, started 12:09Z, has the 32,000 output cap but still the 2700 s
    budget).
  - [x] Follow-up: verify batch 11+ planner calls complete within 4500 s; if planner calls still exceed it,
    lower planner thinking effort or cap tool-output size. ✅ 2026-09-28 — recurred on batch 15 at 4500 s;
    addressed by DS41-C72's salvage turn rather than lowering effort or capping tool-output size.
- [x] DS41-C72 — **One planner salvage turn on budget exhaustion.** ✅ 2026-09-28 (~22:50-23:40Z),
  `ak-ds41-main`. DS41-C71's follow-up recurred: batches 11, 13, 14 completed (28-34 min, 15-16 steps), but
  batch 15's planner ended `budget_exhausted` at 4500 s (22:49Z) — 46 steps, 47 tool calls, ~87k output
  tokens, no report. 5 of 9 planner calls on 2026-09-28 produced nothing; successful sessions run 15-19
  steps, failures 21-46.
  - Rejected alternatives: an opencode step cap (`agent.steps`) — at the cap opencode 1.18.31 injects a
    "CRITICAL - MAXIMUM STEPS REACHED ... This constraint overrides ALL other instructions ..." message that
    would replace the proposal JSON with a summary; a soft planner prompt rule — the planner already ignores
    the concise-analysis rule.
  - Fix: research `23305d81` on epyc-inference-research main. When a PLANNER opencode call ends by its wall
    budget without a complete reply and its root session id is known, the loop makes ONE follow-up call
    continuing that session (`--session <id>`, same backend/model/variant/config, fixed stdin message: stop
    investigating, no tools, output the proposal JSON now or abstain) under `--actor-planner-salvage-s`
    (default 900 s; 0 = off, byte-identical), bounded by `--actor-timeout-s`. A valid proposal lets the
    iteration proceed, stamped `planner_report_source: "salvage_turn"`; otherwise `budget_exhausted` as
    before with the salvage outcome appended. New actor-calls.jsonl row
    `epyc.autokernel.actor_salvage_turn.v1`; salvage arm `+salvage` excluded from the CPU-window phase
    estimator. Planner only. Tests: 28 new (incl. two live wire tests against opencode 1.18.31), 227 pass;
    the loop suite's failure set is identical to main (13 pre-existing in 7 files).
  - Deployed: live worktree `/mnt/raid0/llm/worktrees/research-ds41-run10` at `23305d81` (no restart needed:
    default on, child imports fresh code each batch), effective from batch 17 (batch 16's planner had
    already started on the old code).
  - Also recorded: `akm-ds41-dense-q8-offset-vnni` +0.801% (`14386242a`, 17:02Z) kept, anchor guard gen-005
    +1.624% inside 1.876%, accumulate +2.342%; `akm-ds41-dense-q8-prefetch-deep` measured_null −0.478%
    (19:57Z) rejected; `akm-ds41-float-tinyblas-rowplan` DECISIVE REGRESSION −6.586% (21:33Z) rejected, the
    `float_tinyblas_plan` route's second decisive loss (see DS41-C62 note).
  - [ ] Follow-up: verify the first salvage turn in production (actor-calls.jsonl `actor_salvage_turn.v1`
    rows; does the 27B obey "no tool calls"?); if salvage turns burn 900 s calling tools, consider lowering
    planner thinking effort.
  - [x] Follow-up: if the planner proposes a third plan-only variant on the `float_tinyblas_plan` route,
    consider closing the route (two decisive regressions: DS41-C70's `hcmix-narrow-m-plan` −3.833% and this
    batch's `float-tinyblas-rowplan` −6.586%). Resolved by DS41-C75: a third variant
    (`akm-ds41-float-tinyblas-narrowm-plan`, −3.485%) and a fourth (`…-narrowm-workfill`, −4.589%) both
    appeared and both decisively regressed. Inbox note 54 added instead of formal closure; formal closure if
    a post-note variant appears.
- [x] DS41-C73 — **Pre-existing getenv opt-in is not a new env probe.** ✅ 2026-09-29 (~00:05-00:35Z),
  `ak-ds41-main`. DS41 run 10m batch 16 (planner finished in ~51 min on the old code, within 4500 s): an
  author patch for `akm-ds41-dense-q8-iqk` was refused `integrity_refused` / `reward_hack_scan` at 00:03Z on
  `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:59:environment_probe:static const bool e = []() { const char * s =
  getenv("GGML_IQK_Q8_0");`.
  - Root cause: the patch's whole mechanism was flipping the `GGML_IQK_Q8_0` opt-in default in
    `iqk_q8_0_enabled` (unset → on, routing dense Q8_0 through iqk), which the admitted `iqk_dense_dispatch`
    route explicitly names as a target (the opt-in has defaulted off since `aebb556b1`). Rewriting the
    existing `getenv` line made the added-lines scanner treat it as a new environment probe, so that route
    target could never be edited.
  - Fix: research `5b7f757a` on epyc-inference-research main. `loop/integrity.py`
    `_without_preexisting_env_reads` drops an `environment_probe` finding only when every probe on the added
    line is `getenv`/`secure_getenv` of a literal NAME the anchor's version of the SAME file already reads;
    new names, mixed lines (`getpid`, `sched_getcpu`, `/proc`, tool names) and new files keep the finding.
    Verified on the real refused patch (finding dropped, no other findings). Tests: 6 new in
    `test_integrity.py`; 92 pass across integrity/author-recovery/path-normalization/reward_hack_scan/
    instrument_integrity.
  - Deployed: live worktree `/mnt/raid0/llm/worktrees/research-ds41-run10` at `5b7f757a` (includes C72
    salvage turn `23305d81`), effective from the next batch.
  - Note: routing Q8_0 into iqk changes the activation quantization, so outputs are not bit-identical to
    tinyBLAS (the route's own documented caveat) — the correctness gates will judge it.
  - [ ] Follow-up: watch whether `akm-ds41-dense-q8-iqk` is re-authored and now reaches the gates/measurement
    (dense Q8_0 is the largest single lever, ~40% of cycles).
- [x] DS41-C74 — **Two lanes, lane 1 on an external planner/author model (deepseek/deepseek-flash).**
  ✅ 2026-09-29 (~01:30-03:25Z), `ak-ds41-main`. Operator decision (AskUserQuestion): second lane on an
  external model, motivated by the host CPU sitting ~98% idle during every actor phase and no peer using the
  windows; two lanes on the local 27B were ruled out because `:8083`'s single unified 196,608-token KV pool
  is shared by all slots (planner sessions reach 100-170k tokens, a full pool + MTP has crashed the server,
  and halving per-lane context to ~90k would cripple the planner).
  - Implementation: research `48ed3f77` on epyc-inference-research main. `--batch-iterations N>1` now admitted
    in scheduled mode only for a single-target derived manifest (stage outcome folds to the worst iteration
    class; derived stage bound D × N; multi-iteration children never train the cost forecast; validation/LOO
    forced to 1 iteration; seeds with a pending CPU-screen candidate refused at startup). New
    `--lane-actor-models K=provider/model[@effort]` (lane 0 never overridden): lane 1 planner + single author
    on `deepseek/deepseek-flash@high`, critic stays global, no qwen-specific thinking kwargs sent to deepseek,
    salvage turn stays on, best-of panel counts only lanes on the global provider. Fixes found on the way:
    runtime arms shared across lanes via `ArmLanes`; every ak-check takes the pool's shared fence
    (`AK_CHECK_FENCE`, OAB-28); CPU-window estimator keys phase medians by lane model.
    `POOL_ACTOR_FLAGS` excluded from `resume_binding` (OP-60). Tests: 27 new in `test_lane_actors.py` plus
    additions in three other suites; 189 pass, failure set identical to main.
  - Launch: dry-run proved the wiring first. `swap_twolane_10n.sh` paused run 10m at the batch boundary
    (accepted 02:10Z, landed 03:22:49Z after batch 18; 10m ran 33.5 h, 18 batches), moved the live worktree to
    `48ed3f77`, installed `--workers 2 --lane-actor-models 1=deepseek/deepseek-flash`, and launched run 10n
    (pid 2279409, `--batch-iterations 2`) seeded from 10m's last continuation at 03:22:55Z. New watchdog v2
    (2 iterations/child, falls back to single-lane at 1) started 03:24:25Z; watchdog v1 left running but held.
  - Known costs (documented, not bugs): a keep in one lane supersedes the other lane's in-flight candidate;
    lane 1 is deepseek authoring + deepseek critic (self-review); lane-1 prompts (up to ~100-170k tokens)
    egress to the external provider; `_last_call_evidence` may attribute authoring-failure evidence to the
    other lane's row.
  - [ ] Follow-up: confirm lane 1 (deepseek) produces proposals/patches that reach measurement and that the
    shared tail serializes measurements (no overlap).
  - [ ] Follow-up: measure the throughput change (measurements per hour vs run 10m's single lane).
  - [ ] Follow-up: watch supersession waste (keeps in one lane discarding the other lane's candidate).
- [x] DS41-C75 — **Batch size 6, dead-end steering, planner context arms (arm B live).** ✅ 2026-09-29
  (~07:30-11:31Z), `ak-ds41-main`. With `--batch-iterations 2`, each child gave each lane one iteration, so
  fast lane 1 (deepseek, ~15-20 min/iteration) idled while lane 0 (27B, 1-2 h/iteration) finished — the pool
  shares one iteration budget (`pipeline.run_pool`: `while budget.take()`). Relaunched at 6 iterations/child
  (run 10o, 08:45:27Z, seeded from run 10n batch-000001, via
  `/mnt/raid0/llm/tmp/ds41-scope-20260926/swap_bi6_10o.sh`); run 10o batch 1 took 41 min vs 1.5-3.5 h/batch at
  N=2. New watchdog v3 (`ds41_watchdog3.sh`, reads batch-iterations from
  `/mnt/raid0/llm/tmp/ds41-scope-20260926/ds41_batch_iterations`, hold file `WATCHDOG3_HOLD`, log
  `ds41_watchdog3.log`); v1/v2 held permanently.
  - Peer window: DS41 paused 07:03:59-07:09:29Z at a batch boundary for workspace-8d's `:8083` runbook (27B
    relaunched on production v10 under `architect_critic`, B2 slot-dir drift cleared; their champion-HIP A/B
    did not complete and moves to `:8086`) — no overlap with a DS41 measurement. An earlier peer CPU sidecar
    stayed up past a window close and died at 03:36:17Z, before lane 1's A/B began — no contamination; their
    watcher now aborts on anything but `open`.
  - Results since C74: lane 1's first deepseek patch `akm-ds41-mmid-verify-slab` measured_null −0.99%; keep
    `akm-ds41-gemm4xn-4x-unroll` (0c8b896ee) +0.395%, anchor guard gen-006 −0.794% inside 1.876%; accumulated
    to 2 keeps the compound fell to +0.38% (the earlier +2.342% was mostly noise). Both dense-Q8 iqk
    default-flip hypotheses retired: they fail the independent scalar Q8_0 reference at widths 1-8
    (Q8_2_X4 activation re-quantization is not bit-identical — a genuine correctness verdict, not a harness
    defect). `float_tinyblas_plan` route: `akm-ds41-float-tinyblas-narrowm-plan` −3.485% and
    `…-narrowm-workfill` −4.589%, both decisive regressions (4 total on the route).
  - Inbox steering notes (re-read every iteration): `store/inbox/53-ds41-dense-q8-iqk-flip-settled-20260929.md`
    and `store/inbox/54-ds41-float-tinyblas-plan-settled-20260929.md`. Route not formally closed (2026-09-26
    operator route widening); close it if a new tile-plan variant is proposed after 10:08Z.
  - Context arms (operator directive: test dropping old reasoning plus REPL-style context, aiming at a second
    27B lane). Research commits on epyc-inference-research main (`c1abfe1f`): `35c62028` new
    `--actor-planner-reasoning-history {keep,drop}` (planner only; `drop` sets opencode `interleaved:
    {field: "reasoning_history_dropped"}` — opencode 1.18.31 re-sends every prior step's reasoning,
    llama-server v10 keeps it, and `qwen3.8-froggeric-v22.3` renders it within one tool chain;
    `preserve_thinking=false` does not help within a chain); `360bcd6a` arm flags are actor provenance, not
    continuation identity; `c1abfe1f` `test_scratch` allowlist fix. 14 new tests, 193 pass.
  - Side finding: `--planner-effort high` never reached the server for qwen-gpu (no `reasoning_effort` /
    `chat_template_kwargs` on the wire; config-only model has no variants) — planner has run at the
    template's default (medium) throughout. Decision: leave at default, test "high" later as its own arm.
  - Measured context composition (recent long sessions): prompt ≈134k chars (~35k tokens), tool output
    20-105k chars, reasoning 24-182k chars, peak context 62-131k tokens. 27B concurrency (measured
    2026-09-08): 79.25 tok/s at 1 slot, 109.41 aggregate at 2, 167.76 at 4 — two 27B lanes would add real
    aggregate throughput; the binding constraint is the single 196,608-token unified KV pool. 2026-09-25
    OAB-9 A/B (`artifacts/autokernel_ctx_ab_20260925`): `variable` lost on wall/steps/peak-context without a
    cap; OAB-9b's re-open trigger (≤98k, n≥3 ABBA) is met by a 90k cap.
  - Arm B live: run 10p launched 11:29:27Z (`state-run10p`, 6 iterations/child) via
    `/mnt/raid0/llm/tmp/ds41-scope-20260926/swap_args.sh <args> <name> <label>`; common args = previous +
    `--actor-context-limit 90112 --actor-planner-reasoning-history drop --actor-authors single` (backup
    `inputs/bak-20260929T112927-run10p/`). Arm C staged, not launched: `inputs/next/armC/common-args.json`
    (arm B + `--actor-context-mode variable`). Caveat: context limit/mode are global, so lane 1 and the
    critic inherit them too — lane-0 per-call metrics stay clean, but campaign-level arm yield comparisons do
    not isolate lane 0.
  - [x] Follow-up: collect ≥3 lane-0 planner sessions under arm B; compare completion rate, wall, peak
    context (`context_max_tokens`), compactions, output-capped steps vs arm A baseline (runs 10n/10o lane-0
    sessions). ✅ 2026-09-29 — arm B 0/3 valid; superseded by arm C (DS41-C76).
  - [x] Follow-up: then run arm C for ≥3 sessions. (Tracked as DS41-C77.) ✅ 2026-09-30 — arm C 5/5 valid.
  - [ ] Follow-up: if arms hold, design a second 27B lane (pool math: two sessions at 90k can reach ~205k
    worst case, over the 196,608 pool — needs C≈77k and author output under 40,960, or lane-0-only limits via
    `lane_actors.seat_for`).
  - [ ] Follow-up: planner effort "high" arm, later.
  - [ ] Follow-up: consider pinning lane 1 to its own context limit if campaign-level arm comparisons are
    wanted.
- [x] DS41-C76 — **Escape mandate confined the search to four closed categories → abstention storm; fixed.**
  ✅ 2026-09-29, `ak-ds41-main`. Experiments rows 134-143 (14:18-14:53Z) were all
  `abstained`, 0 measurements.
  - Cause: `render_context` (`scripts/kernel_rnd/autokernel/loop/actors.py`) emitted "DIMINISHING-RETURNS
    ESCAPE — mandatory for this turn" whenever any mechanism family had ≥3 resolved failures, ordering the next
    hypothesis to target one of graph scheduling, row/work partitioning, NUMA/memory placement, or
    expert/load balance. All four were already tried, so both lanes abstained honestly; lane 0 (row 141)
    named the dense MUL_MAT per-core efficiency gap — the route every kept win came from.
  - Fix: research `4fefe923` (origin/main). The block bans variants of the listed families and allows either
    an unlisted profile-supported family or a causal escalation; closed escalation categories are not grounds
    to abstain. Heading kept (`actor_context.py` matches it). New test
    `test_family_escape_bans_the_family_not_the_rest_of_the_search`; `test_actors` + `test_actor_context` 160
    pass. Follow-up `56dfdccf`: a keep resets its family (the keyword bucket "local quant/dot kernel" had stayed
    exhausted through its own dense Q8_0 keeps), and the rule bans cosmetic variants rather than whole families;
    `test_a_keep_resets_an_exhausted_family`, 161 pass. Deployed via swap to run 10r (same arm C args) at the next batch boundary
    (`/mnt/raid0/llm/tmp/ds41-scope-20260926/swap_c76_10r.log`).
  - Arm B verdict (run 10p): 0/3 lane-0 calls valid — walls 16.4/68.9/53.2 min, peaks 52,398/66,291/61,404,
    1/2/2 compactions; the ~52.7k-token inline first prompt means compaction near ~58k drops the JSON output
    contract. Arm A baseline: 8/10 valid, median 38.2 min, peak median 114,367.
  - Arm C (arm B + `--actor-context-mode variable`, run 10q from 14:01:56Z, 12 iterations/batch): first
    lane-0 call valid — 46.0 min, first prompt 19,200 tokens (vs ~53k), peak 59,038, 2 compactions, 12 bundle
    tool calls. Pre-C76 arm C calls are outcome-contaminated by the abstain mandate; context metrics stay
    valid.
- [x] DS41-C77 — collect ≥3 arm C lane-0 planner calls on C76 code (run 10r); compare vs arm A (completion,
  wall, peak context, compactions); decide second 27B lane (pool: two sessions at 90k worst case ~205k vs
  196,608 unified KV). ✅ 2026-09-30
  - Verdict: arm C 5/5 valid (one via the 15-min salvage turn), median 43.0 min, median first prompt ~20.8k,
    median peak ~59k (max 75.6k) — vs arm A 8/10, 38.2 min, peak median 114k (max 149k); arm B 0/3. A second
    27B lane was memory-feasible (~180k of 196,608).
  - Lane decision superseded by the operator's 2026-09-30 lineup change (DS41-C80): the 27B left DS41. Every
    keep since C76 came from deepseek (lane 1: 3 keeps / 4 hypotheses; 27B 0/5) — mostly model capability;
    harness confounds carried to DS41-C83.
- [x] DS41-C78 — resume advances a superseded continuation after a mid-batch crash (bf07f204). ✅ 2026-09-30
  - Anchor-gen retention keeps 1 generation, so after a mid-batch crash the newest complete continuation named
    a pruned anchor-gen-006 and every relaunch would have failed; resume now re-derives anchor/COR from proven
    exact builds only. Dry-run on live data: HEAD 1ef72c228766=anchor-gen-009, COR 053c3bd82d00=anchor-gen-007.
- [x] DS41-C79 — floor carry refuses only on two A/A excursions (e66f2bad; operator 2026-09-30). ✅ 2026-09-30
  - Under the old one-excursion rule a single -2.145% anchor-guard excursion (row 168) forced a 48-launch COR
    floor recalibration (22:31-01:12Z); two-sample persistence now required.
- [x] DS41-C80 — lineup gpt-6.1-sol @low planner / claude-opus-5-5 @xhigh critic; codex daemon binary; planner/critic flags out of the resume binding (30b1bc2d, 336f946d); live run10s 02:36Z. ✅ 2026-09-30
  - Operator lineup change: gpt-6.1-sol also authors; deepseek and the local 27B dropped → MI210/`:8083` freed.
    Codex runs from the auto-updated daemon build (npm CLI 0.157 refused gpt-6.1-sol). A lineup change had
    refused resume ("different stable resume inputs") until planner/critic flags joined `POOL_ACTOR_FLAGS`.
  - Serving gate 2026-09-29T18:07Z (row 159) promoted offset-vnni + gemm4xn-4x-unroll + zmm-widen at +11.18%
    serving, decisive (bench +11.876%, 5/5 pairs separated); COR now 053c3bd82d00.
- [ ] DS41-C81 — serving floor 4.533% was inflated by our own test activity during calibration (operator: keep for now); at the next COR promotion quarantine it and recalibrate with zero test/dry-run activity.
  - The recalibration ran while pytest/dry-runs/find ran (some pinned to SMT siblings 184-191 of DS41 cores
    0-95); low samples clustered 00:06-00:14 and 00:30-00:48Z (20.9-23.4 vs a 24.2-25.1 band); previous floor
    1.876%. Candidates now need >4.5% to be decisive (gate threshold 11.333%).
- [ ] DS41-C82 — loop full-CPU pytest fixtures take the real MI210 device lock (claim.DEVICE_LOCK); make fixtures use a private lock by default so tests can't block or hang behind a live loop.
  - Path: `_q3_cpu_gpu_quiet_window` (run.py:124) takes `/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock`.
    Workaround meanwhile: private-lock runner `/mnt/raid0/llm/tmp/c78-dry/runtests.py`.
  - Note 2026-09-30: DS41-C84 made pytest fixtures exit when their parent dies, which covers orphaned fixtures
    but not the shared device lock itself; still open.
- [x] DS41-C83 — 27B planner quality investigation on the freed GPU: replay fixed DS41 planning contexts through qwen3.8-27b vs deepseek/gpt-6.1-sol with a neutral critic; separate capability from harness (compaction, effort not reaching the server, same-family critic). ✅ 2026-09-30
  - Post-C76 the 27B went 0/5 (2 critic rejections on source grounds, 1 abstain, 1 authoring failure, 1 patch
    rejection); it found the earlier keeps (gemm4xn-2x/4x-unroll, q4k-x4t-weight-prefetch, dense-q8-offset-vnni).
  - Verdict (`/mnt/raid0/llm/tmp/ds41-c83-planner-gap-report.md`): ~45% capability / ~40% harness / ~15%
    scheduling; no critic bias (27B accepted 9/13 vs deepseek 6/11); the 27B found then lost zmm-widen to
    compaction. Harness: effort never reached the server, lane-0-only reasoning-drop, fast lane got 2-10x the
    calls. Replay experiment → DS41-C95.
- [x] DS41-C84 — orphaned ak-check op-test (PID 930091, 25 h, deleted cwd/exe) fixed by per-call process scope (research a4436986; analysis c453f997). ✅ 2026-09-30
  - Root cause: setsid child of ak_check survived opencode's 120 s group TERM; `_end_group` reached only the
    actor group; fence flock released with ak-check. Fix: `AK_PROC_SCOPE` cookie swept by pidfd TERM→KILL,
    ak-check PDEATHSIG/signal handlers, MeasurementWatch contention invalidation, parent-watch fixtures (319
    tests). Remaining gap → DS41-C94.
- [x] DS41-C85 — prompts >100,000 bytes go to codex/claude on stdin, not argv (7123c503). ✅ 2026-09-30
  - MAX_ARG_STRLEN (128 KiB) killed the Opus critic pass-2 with E2BIG (lane_error, rows 173-175).
- [x] DS41-C86 — resume drops anchor-bound `experimental_source_keeps` from the in-memory continuation (08d3c15d). ✅ 2026-09-30
  - Seeds from a batch that kept crashed on pruned anchor-gen-009 (07:19-07:23Z); unreceipted kept commits are
    now named (bscale-cvtph 6f8e232aa41f → DS41-C93).
- [x] DS41-C87 — a new anchor with no A/A yet carries the lineage floor; only ≥2 above-floor A/As refuse (fb684136). ✅ 2026-09-30
  - Operator: no more calibrations. Runs 10v/10w carried gen-009's 3.412% with zero calibration.
- [x] DS41-C88 — `_extract_json` uses `raw_decode` instead of brace counting (b148d218). ✅ 2026-09-30
  - An unbalanced `{` in a 27B compaction summary had turned a finished, op-test-passing patch into "author
    abstained"; 129 actor tests.
- [x] DS41-C89 — dedup refusal text corrected; diagnosis of a per-champion retry bug was wrong (588c74bc). ✅ 2026-09-30
  - Rows 185/186 were both lanes proposing the same bytes at once (oracle_unavailable); only the misleading
    "configuration closed infeasible" text changed. Follow-up → DS41-C91.
- [x] DS41-C90 — integrity `literal_shape_predicate` requires the literal to be a comparison operand with the tensor subject (a35b679f). ✅ 2026-09-30
  - `>` inside `->` parked `akm-ds41-mmid-verify-flat-slabs` (+2.285%, row 190) on two false positives; the
    parked candidate is not auto-revived; 36 integrity tests.
- [ ] DS41-C91 — planner "formed but never measured — consider FIRST" list should drop superseded ideas already re-proposed/queued on the new champion (contradicts "do NOT re-propose"; invited both lanes to re-propose at once).
- [ ] DS41-C92 — floor selection prefers the COR exact floor (4.533%, contaminated) over the cleaner carried lineage floor after each anchor advance; quarantine the 4.533 record or re-order selection (operator decision pending).
- [ ] DS41-C93 — reconstruct the fold receipt for bscale-cvtph 6f8e232aa41f (lost when run10s stopped mid-batch) before the C47/C68 fold.
  2026-10-04: `6f8e232aa` is one of the 14 held keeps (fold inventory `/mnt/raid0/llm/tmp/fold-allkeeps-20261004/inventory.tsv`, now `853a1a00e` on Z'); it was not folded, so the receipt matters only if Z' is re-gated (DS41-C125).
- [ ] DS41-C94 — C84 remaining gap: per-call cgroup v2 scopes so a SIGKILLed run.py's cookie-less children (llama-server, builds) are killed, not just flagged.
- [x] DS41-C95 — C83 replay experiment (27B arms vs deepseek/gpt-6.1-sol, blinded Opus critic; ~8 GPU-h minimal) — operator go 2026-09-30. ✅ 2026-10-01
  - Results (arm table in `progress/2026-10/2026-10-01-ak-ds41-main.md` §DS41-C95): P(keep) DS 0.75 (3 exact, 0 errors);
    27B as-ran 0.0, ×codex-inline 0.50 (2 partial), ×Hermes 0.33, ×opencode 0.25, ×codex-variable 0/2; none contaminated.
  - Verdict (indicative, n tiny): harness matters some (codex inline best, found C1 zmm-widen), capability dominates
    (no exact match, 2-3.5 factual errors vs 0, ≥50% no reply in ~90 min). orv/orsv not run → DS41-C102.
  - Report: `/mnt/raid0/llm/tmp/ds41-c95/grading/report.md` (+ `report.json`); design `/mnt/raid0/llm/tmp/ds41-c95/README.md`.
  - **F12 follow-up (UFH14-A1, 2026-10-03)** — 8 solo codex calls on DFlash2 :8083 (C2, C4), graded blind with the other arms:
    cxf12 (F1 serving fixes + F2 answer protocol) P(keep) 0.75 (0 exact, 3 partial), 4/4 answered, 2.25 mean errors, median wall
    3880 s; cxf1 (F1 only) 0.50 (2 partial), 4/4 answered, 1 call contaminated (C2/cxf1/r2 browsed the live store anchor-gen-007);
    unfixed cx 0.50 with 2/4 answered; DeepSeek as-ran 0.75 (3 exact, 0 errors). The fixes recover the no-reply calls but not
    exactness: the 27B still finds no exact keep and makes 2-2.25 factual errors per answer against DeepSeek's 0. Detail and the
    sandbox fix: [`agentic-serving-harness-fixes.md`](agentic-serving-harness-fixes.md) UFH14-A1/A6.
- [x] DS41-C96 — graph-sync gate fault: `GLU`/`UNARY` passed to `test-backend-ops -o` match no `op_desc()`, so the suite was always 0/0; `backend_ops_selector` expands them to sub-ops (e29dca63). ✅ 2026-10-01
  - Route now 29 ops (incl. TOPK_MOE chain; EXP/EXPM1 excluded, fail on anchor); empty suite still fails
    closed. Caused the run 10w abstention storm (rows 203-224). Shared-walk-defect caveat → DS41-C99.
- [x] DS41-C97 — runtime treatments deduplicated by normalized launch delta in a sidecar identity ledger; duplicates refused `refused_duplicate` / gate `runtime_treatment_identity` (42f434a5). ✅ 2026-10-01
  - Both passive-wait rows map to identity 746aeb3181543057; `serial_scheduling` outcome classes fixed. Limit:
    simultaneous same-treatment proposals from two lanes are not deduplicated.
- [x] DS41-C98 — keep admission: 8 bench keeps since the +11.18% promotion summed to +0.101% serving (row 253 measured_divergence). Rethink admitting keeps on non-decisive positive bench A/Bs (e.g. require decisiveness, or a cheaper serving confirm per keep) — decision package for operator. ✅ 2026-10-03 — **operator chose D: status quo** (keep admitting positive non-decisive keeps; HOLD on a diverged gate).
  - Package: `/mnt/raid0/llm/tmp/ds41-c98-package-20261003.md` (options A decisive-only, B confirm re-measure (recommended), C provisional tier + ROLLBACK, D status quo).
  - **Findings that stand regardless of the choice:**
    - Post-053c keeps are statistically indistinguishable from noise. 15 same-build anchor-guard A/As (5 pairs): mean +0.24%,
      SD 1.35%, max |2.38|%. All 9 post-053c keeps (+0.37 to +2.27%) sit inside that envelope. Of 26 measured post-053c source
      candidates, 10 were positive (all-null expectation 13 ± 2.5); mean effect −0.49%.
    - In DS41 "bench" and "serving" are the same instrument (`matched_process_v2`, 5 pairs, recipe `ds41-00d118d44-cpu-t48-dspark-b2`).
      Gate 3's divergence is winner's curse on positive noise draws, not a proxy that fails to transfer, so there is no cheaper
      per-keep serving confirm: a confirm is one more A/B.
    - The floor drives everything (DS41-C92): at 4.533% a real +2% effect is almost never admissible by any rule; at 1.876% most are.
    - The real wins came from decisive keeps (load-threads-48, tinyblas-zmm-widen); only one non-decisive keep (gemm4xn-2x-unroll) is independently confirmed.
  - Consequence of D: the tip keeps accumulating unverified changes and gate 4 (after 8 keeps) is expected to diverge again.
  - Keep since the decision: run 10z kept `akm-ds41-q8-rn3-single-pair-loop` (+0.568%, 5 pairs, floor 3.412%, not decisive; commit
    `b3e0b0902` at 14:20Z, `sgemm.cpp` only) and built anchor-gen-017 from it (its experiments.db row was not yet written at 14:26Z, while the anchor guard A/A ran). That is held keep 10 on the tip, 2/8 toward gate 4,
    and like the others it is inside the A/A envelope.
  - Defects found by the package → DS41-C104/C105/C106.
- [ ] DS41-C99 — e2e correctness oracle for scheduling-only routes (cpu_graph_sync): compare --autokernel-harden output hashes vs anchor; op-level suites can't see shared deterministic walk defects (C96 caveat).
- [ ] DS41-C100 — UFH-12 context.search (hybrid lexical+dense, rrf_fuse, pointers only) in the orchestrator REPL; add an orsv arm to C95 once deployed (coordinate the API reload with workspace-8d).
  - 2026-10-01: built and live (orch `b384cdbb`; branch d02942f7 + 002b6fc4, dense-index timeout fix by workspace-8d →
    `lexical_fallback:index_timeout`). `repl_embedding_pool` is runtime-only: any API reload resets it. orsv pending C102.
- [ ] DS41-C101 — wire the C95 graded results into the belief kernel (source row in scripts/vidya/adapters/README.md + task in vidya-belief-substrate-program.md), per CLAUDE.md.
  - 2026-10-01: graded results `/mnt/raid0/llm/tmp/ds41-c95/grading/report.json` (+ `report.md`, `grades/`, `key.json`);
    source row and task drafted in the C95 wrap-up, applied by the owning session. Copy the dir durably first (`tmp` is scratch).
- [ ] DS41-C102 — orv/orsv arms (27B via orchestrator REPL; + UFH-12 context.search) orchestrator 500 int('') bug FIXED 2026-10-01 (orch 2d97ade2: context.get dict-style default; root cause model wrote context.get('inbox','')); operator chose a DS41 pause to run them 2026-10-01; needs frontdoor quiet (REPL delegates to worker roles on :8070) and repl_embedding_pool re-enabled after any API reload.
- [ ] DS41-C103 — if the 27B is reconsidered as a planner: use codex with INLINE context (best arm, P(keep) 0.5 partial) and a longer budget; the 4500 s budget is the main failure (≥50% no-reply).
- [x] DS41-C104 — belief-kernel defect: `keep_claims()` in research `scripts/kernel_rnd/autokernel/loop/claims.py:27-48` stamps `effect.status = verified` (basis `oracle`+`paired_ab`) on every kept row with an oracle pass and any pairs, decisive or not, so all 14 non-decisive keeps read as verified effects. Mark `verified` only when the comparison is decisive; non-decisive keeps get `unverified` (or a `within_floor` status), plus a test and a re-projection of existing kept rows. A defect, not a choice — independent of the C98 ruling. ✅ 2026-10-29 (audit: research 9299b0a6f (2026-10-07, on origin/main) 'Require decisive comparisons for verified keep effects': claims.py + test_claims.py +33; re-projection of existing rows not evidenced) [no-belief: audit-reconciliation]
- [x] DS41-C105 — ✅ 2026-10-04 — the DS41 loop takes the `mi210_0` GPU device claim although the campaign is CPU-only, which blocks GPU windows (X0, UFH-14) for no reason. Drop the GPU claim for CPU-only targets. A fix is in progress on a research branch (another session's subagent); close when it lands and a live run shows no `mi210_0` claim.
  - 2026-10-03: **fixed, pending deploy.** Research main `4a815f00` adds `--cpu-measurement-gpu-quiet {off,q3}`, default `off`. Root cause: `loop/run.py:124-153` `_q3_cpu_gpu_quiet_window` took the claim on purpose — measurement hygiene from INF-70 (2026-09-08) to keep GPU work off the CPU floor — and it never excluded production :8083 anyway. It deploys through the DS41 boundary swap already armed (`/mnt/raid0/llm/tmp/ds41-scope-20260926/swap_noclaim_10aa.log`; at 15:23Z it showed only the run 10z pause request). Flip when that log shows run 10aa alive and a live run holds no `mi210_0` claim.
  - 2026-10-04: **deployed and verified.** Runs 10aa/10ab and the current watchdog run (`state-wd3-20261004T023130`) run research main with the default `--cpu-measurement-gpu-quiet off`; their argv carries no `q3`. The GPU windows that followed ran on `mi210_0` while the loop was live — the CPU window's neighbours and the EXL3-LB1 seed #1 A/B (02:11–02:24Z) — with no claim refusal.
- [x] DS41-C106 — `AccumulatorPolicy` names a `ROLLBACK` divergence action (research `scripts/kernel_rnd/autokernel/loop/accumulate.py:141`) that nothing in `run.py` handles; `run.py:3049` always builds the HOLD default. Either implement ROLLBACK (reset the tip to the champion of record, discard the bundle, re-anchor) or remove the enum value so a config cannot select a no-op. ✅ 2026-10-07 — exact Research product `3613455d5114d78968fab464b9cdc8a18df2f306` removes unsupported ROLLBACK and refuses invalid constructor selectors; original whole16 synthetic conformance accepted by MAIN, [originals/scope](../../artifacts/ni08/c106-hold-source-acceptance-20261007/README.md). Default HOLD/floor/cadence/keep/serving remain; no loop reload or live/runtime acceptance.
- [ ] DS41-C107 — AutoKernel seed ledger: Fable CPU seeds (inbox 56) + structural seeds (inbox 57). Operator 2026-10-04: "I want to see autokernel progressively nail all of these".
  - Sources: `/mnt/raid0/llm/tmp/cpu-lowbit-seeds-20261003/hypotheses-fable-cpu.md` (inbox 56) and
    `/mnt/raid0/llm/tmp/cpu-structural-seeds-20261004/hypotheses-structural.md` (inbox 57 = DS41 note; Q38FN note in the
    same dir, not yet in any campaign inbox). The inbox copies live in the campaign store
    (`store/inbox/56-ds41-fable-cpu-lowbit-seeds-20261003.md`, `57-ds41-structural-sync-numa-seeds-20261004.md`); the
    `tmp` originals are scratch.
    2026-10-04: the Q38FN structural note is now Q38FN-lane inbox 61
    (`/mnt/raid0/llm/tmp/q38fn-lane-inputs-20261003/inbox/61-q38fn-structural-seeds-20261004.md`, read when the
    DS41-C111 lane starts). DS41 inbox 55 (blocked `cpu_graph_sync`) is marked SUPERSEDED, since C96 repaired that route.
  - **Attempt ledger 2026-10-03 16:00Z → 2026-10-04 04:00Z** (`store/experiments.db`; accumulator tip `7ef803926`, COR
    still `053c3bd82`):
    - kept: `akm-ds41-dense-qact-flat-block-partition` +1.82% (01:02Z, loop-originated, not a numbered seed);
      `akm-ds41-rmsnorm-eight-double-chains` +1.26% (21:40Z, Fable seed 4 = s04); `akm-ds41-rmsnorm-single-pass-output`
      +0.13% (23:03Z, after a −2.2% measured_null first try at 22:19Z).
    - keep_candidate: `akm-ds41-hc-norm-mixes-splitk-fusion` +2.23% (19:01Z, Fable seed 3 = s03); the `akm-cpu-` variant
      +0.19% (19:50Z).
    - measured_null: `akm-ds41-q4q5-metadata-allocation-reuse` −0.47%, `akm-ds41-dense-q8-flat-conversion-blocks`
      −1.69%, `akm-ds41-mmid-verify-block-qact` −0.72%, `akm-ds41-mmid-expert-owned-map` −1.67% (the last two are MoE
      N>1 neighbours of s12, not s12 itself).
    - 03:53Z: one `anchor_guard_excursion` at 4.09% (anchor A/A guard). Read it before trusting the next keep.
  - Every sub-task closes the same way: the loop keeps it, rejects it with a measured A/B, or abstains with a recorded
    reason. Cite the experiments.db row. Q38FN-only seeds wait for the Q38FN lane (DS41-C111). Do not re-seed the
    classes both notes list (barrier primitives, OMP wait, pairwise fusion, map-owner, NUMA_MIRROR, in-body gemm4xN).
  - [x] DS41-C107-s00a — no-code falsifier: `bench_readbw` 2×2 at 48t, {interleave, local} × {4K, THP}; ≤1.05× kills s01+s13. DS41+Q38FN. Closes: run + recorded verdict.
    ✅ 2026-10-04 — CPU window 2 step 0 (`artifacts/cpu-window2-20261004/step0_struct_falsifiers/REPORT.txt`, ABBA, 2 GiB × 3 arrays, 10 reps): local/4K ×1.000 and local/THP ×1.018
    vs interleave/4K (read-sum 419–427, read-dot 445–504, gemv-2560 406–414 GB/s). Both ≤ 1.05× → **KILL s01 and
    s13(A)** (the NUMA/THP placement lever).
  - [x] DS41-C107-s00b — no-code falsifier: `GGML_CPU_PROF` node profile, served Q38FN recipe N=5; sets kill thresholds for s14-s17/s19. Q38FN. Closes: profile + thresholds recorded.
    ✅ 2026-10-04 — same report (instrumented build: SHARES, not speed; 72 accumulated evals, 4480 nodes/eval, 77.7 ms
    wall, barriers 5.7 ms; MUL_MAT 29.4%, MUL_MAT_ID 26.9%, CPY 9.4%, GATED_DELTA_NET 8.3%). Q38FN verdicts:
    s16 KEEP (7.6%), s15 KEEP (5.0%), s17 KEEP (3.5%), s19 DROP (5.4% < 12%), s14 DROP for Q38FN (0% recoverable).
    Dense mul_mat runs ~195 GB/s on wall vs a ~407 GB/s gemv read ceiling: the largest single gap. Delivered to the
    Q38FN lane as inbox note 62 (`.../ak-q38fn-cpu-decode-20261003/store/inbox/62-q38fn-structural-falsifier-verdicts-20261004.md`).
  - [x] DS41-C107-s01 — `akm-cpu-numa-quartered-weights`: mbind row quarter q to node q (PLACE, +10-25%). DS41+Q38FN. Gated by s00a. Closes: keep / measured-A/B reject / recorded abstain.
    ✅ 2026-10-04 — killed by its gate s00a (local vs interleave ≤ 1.018×). Do not re-seed without new placement evidence.
  - [ ] DS41-C107-s02 — `akm-cpu-q8-rn5plus-single-pass`: mnpack streams A twice at N=5..7, so make it one pass (+15-20% UD). Q38FN-UD. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s03 — `akm-cpu-hc-norm-mixes-splitk-fusion`: rms_norm→hc_mixes as one 48t split-K op (TOL, +5-6%). DS41. Closes: keep / measured-A/B reject / recorded abstain.
    2026-10-03: attempted twice. Both reached keep_candidate, not kept: +2.23% (`akm-ds41-` id, 19:01Z) and +0.19%
    (`akm-cpu-` id, 19:50Z). Closes when the candidate is admitted or rejected.
  - [x] DS41-C107-s04 — `akm-cpu-rmsnorm-vector-sumsq`: vectorise the serial double Σx² chain (TOL, +2.5-3%), bundle with s03. DS41+Q38FN. Closes: keep / measured-A/B reject / recorded abstain. ✅ 2026-10-03 — kept as `akm-ds41-rmsnorm-eight-double-chains`, +1.26% (experiments.db 2026-10-03T21:40:43Z). The Q38FN half still needs the C111 lane.
  - [ ] DS41-C107-s05 — `akm-cpu-q8k-bsums-vector` + `akm-cpu-q82x4-zmm-quant`: vectorise the activation quantisers (+2-3% Q38FN, +1-2% DS41). Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s06 — `akm-cpu-small-node-prelude-collapse`: cut the 7.7 µs/node fixed cost (+1.5-3%). DS41+Q38FN. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s07 — `akm-cpu-q8-gemv-n1-4row-zmm`: real N=1 Q8_0 kernel in place of the ymm vec_dot (TOL, +3-8%). Q38FN-UD. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s08 — `akm-cpu-iq4xs-scale-fold`: fewer int ops per IQ4_XS superblock (BE-int, +3-6%). Q38FN-uniform. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s09 — `akm-cpu-next-node-slab-prefetch`: prefetch next-node rows during barrier spin (+1-3%). DS41+Q38FN. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s10 — `akm-cpu-qwen4exp-fused-decode-nle8`: model-code workstream, not a kernel route. Q38FN. Expected to close as a recorded abstain (the structural note says do not seed it).
  - [ ] DS41-C107-s11 — `akm-cpu-q4k-vector-scale-unpack`: SIMD make_q4_scales (+1-3%); never pair with a 2-row unroll. DS41. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s12 — `akm-cpu-mmid-n2plus-prelude-parallel`: parallelise the MoE N>1 prelude (+0.5-1%); bundle or drop. DS41+Q38FN. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s13 — `akm-cpu-struct-moe-expert-group-numa`: (A) node-affine MoE slab with s01 (+5-15% MoE path); (B) after R1. DS41+Q38FN. Closes: keep / measured reject / recorded abstain.
    2026-10-04: (A) KILLED by s00a. (B) (after R1) stays open.
  - [ ] DS41-C107-s14 — `akm-cpu-struct-cogroup-independent-nodes`: siblings on 12t groups (+3-5% DS41, +6-10% Q38FN). Needs R1. Closes: keep / measured-A/B reject / recorded abstain.
    2026-10-04: the Q38FN half DROPPED by s00b (0% recoverable from routed‖shared co-grouping). The DS41 half stays open.
  - [ ] DS41-C107-s15 — `akm-cpu-struct-norm-to-q8-fusion`: norm quantises src1 into wdata (+2-3% DS41, +3-5% Q38FN); carrier: new_helpers. Closes: keep / measured-A/B reject / recorded abstain.
    2026-10-04: Q38FN half KEPT by s00b (5.0% ≥ 3%).
  - [ ] DS41-C107-s16 — `akm-cpu-struct-solo-rows-verify-width`: key the solo gate on graph N≤8 (+1-2% DS41, +4-8% Q38FN). cpu_graph_sync. Closes: keep / measured-A/B reject / recorded abstain.
    2026-10-04: Q38FN half KEPT by s00b (770 solo nodes × 7.7 µs ≈ 7.6% ≥ 3%).
  - [ ] DS41-C107-s17 — `akm-cpu-struct-sibling-gemv-pack`: pack same-input projections at load (+1-3% DS41, +2-4% Q38FN). Needs R2. Closes: keep / measured-A/B reject / recorded abstain.
    2026-10-04: Q38FN half KEPT by s00b (240 nodes, 3.5% ≥ 2%).
  - [ ] DS41-C107-s18 — DS41 width arm: draft-dspark n-max 3 (N=4) as a declared runtime arm (no code). DS41. Closes: keep / measured-A/B reject / recorded abstain.
  - [ ] DS41-C107-s19 — `akm-cpu-struct-q4e-hc-fused-ops`: port DS41 fused HC ops to qwen4exp (~1,500 nodes/token, +12-20%). Needs R2. Q38FN. Closes: keep / measured reject / recorded abstain.
    2026-10-04: DROPPED by s00b (hc ops 5.4% of wall < the 12% bar). Expected to close as a recorded abstain once the Q38FN lane reads inbox 62; the planner may re-propose on new evidence.
  - [ ] DS41-C107-s20 — `akm-cpu-struct-mtp-width-arm`: spec-draft-n-max 5/6 runtime arm; flat on UD until s02. Recipe change = operator ruling. Q38FN. Closes: measured A/B or recorded abstain.
- [x] DS41-C108 — new AutoKernel admission routes R1/R2/R3 for the structural seeds (spec: `hypotheses-structural.md` §Routes). ✅ 2026-10-04 — all three on research main `e2ccd6b8` (pushed; `test_structural_routes.py`). The residual closure terms (deployed at a DS41 boundary, one admitted candidate per route) moved to DS41-C108a.
  - [x] DS41-C108-R1 — `cpu_graph_sched` (extends `cpu_graph_sync`: graph_plan/compute bodies, threadpool field appends; repetition + model identity on both targets), unlocks s13(B)/s14. ✅ 2026-10-04 (research `e2ccd6b8`)
  - [x] DS41-C108-R2 — `cpu_model_fused_op` (qwen4exp builders/loader + append-only ggml op; model_identity, + DS41 serving A/B if shared files touched), unlocks s17/s19. ✅ 2026-10-04 (research `e2ccd6b8`)
  - [x] DS41-C108-R3 — `cpu_graph_optimize` (optional: the NULL `graph_optimize` hook annotates co-groups at plan time; gated like R1), an alternative home for s14/s13(B). ✅ 2026-10-04 (research `e2ccd6b8`)
- [ ] DS41-C108a — **deploy R1/R2/R3 at a DS41 boundary and confirm each route admits a seed candidate.** (filed 2026-10-04) Relaunch DS41 (and the C111 Q38FN lane) on a research checkout that contains `e2ccd6b8`. Then cite one experiments.db row per route whose candidate was admitted, meaning built and gated rather than refused at admission: R1 via s13(B)/s14, R2 via s17/s19, R3 via s14 or dropped with a reason.
- [x] DS41-C109 — per-keep measurement overhead cut: `--accumulate-bench-every-keeps` (3) + `--anchor-guard-aa-window-s` (21600, digest-proven A/A skip) (research 42309a9a). ✅ 2026-10-03
- [x] DS41-C110 — widened CPU source admission: `new_helpers`, multi-route bodies, routes `cpu_norm_numerics`/`cpu_mul_mat_body`/`cpu_weight_placement`, fusion ref (e36b879f). ✅ 2026-10-03
- [x] DS41-C111 — Q38FN lane binding (`lane_targets.py`, `--lane-targets/--lane`, cross-target keep veto; research 741c85d8) landed, not started. Closes when a Q38FN lane run starts.
  2026-10-04: the Q38FN lane anchor build is the last step of CPU window 2 (armed, waiting). The lane's seed inbox is 61 (see C107).
  ✅ 2026-10-04 04:41Z — the lane run started. Fork `dd6c9cdbd` (DS41 tip), branch `experimental/q38fn-ak-20261004` in
  `/mnt/raid0/llm/llama.cpp-experimental-q38fn-20261004` (build rc 0, `version 10338 (dd6c9cdbd)`, linkage and knobs
  proven), pinned research worktree `research-q38fn-run1` @ `aef2da6c`, campaign `ak-q38fn-cpu-decode-20261003`, state
  `state-run1-20261004T044414`. Scripts and logs: `/mnt/raid0/llm/tmp/q38fn-lane-run1-20261004/` (KEEP; `relaunch.sh`
  restarts it). Both worktrees are git-locked as load-bearing. Two launch defects were fixed:
  - (a) the shared research venv's editable install shadowed the pinned worktree's `scripts.lib.canonical_recipe`, so
    `PYTHONPATH` must START with the worktree root (`PYTHONPATH=.:scripts/kernel_rnd:...` from inside it);
  - (b) `heldout_frozen_prompts` in owned-targets makes `run.py` refuse ("run explicit --cpu-calibrate-heldout first"),
    and `serial_run` cannot schedule that step. They were dropped to match DS41; the held-out floor is DS41-C119.
  Parked 05:50Z on operator direction, before calibrating (verified dead). Restart: DS41-C121.
- [x] DS41-C112 — **the held keeps after COR cut Qwen3.8-Flash-Next prefill 30–40%: bisect before any champion fold.** ✅ 2026-10-04 (filed 2026-10-04) CPU window 2026-10-03 (INF-70 XFER-1,
  2026-10-04: the bisect is backlog item c4 (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c4/run.sh`, ~50 min, worst 75), row 6 of `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md`.
  `/mnt/raid0/llm/tmp/q38fn-transfer-20261003/run2.log`): vs champion `90c12df42`, COR `053c3bd82` gives Q38FN uniform pp256 −4.4% (inconclusive) and pp5 −7.2% (slower 3/3), but the
  held-keep tip `b3e0b0902` (anchor-gen-017) gives pp256 **−29.4% [−38.6, −20.2]** (UD n=1: −40.6%); decode +2–10% unresolved, token-identical greedy output. Bisect the keeps between
  COR and `b3e0b0902` on Q38FN pp256 (and pp5), name the culprit, and make cross-model prefill part of the gate-4 / champion-fold check (DS41-C111's cross-target veto is the mechanism).
  ✅ **Resolved by c4** (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c4/runs/20261004T104009Z/report.md`): first bad =
  `9b148baab` `akm-ds41-mmid-verify-flat-slabs` (its multi-token slab path), Q38FN pp256 about −25%;
  `GGML_MMID_SLAB=0` recovers it. Fix: an in-code shape gate (slab only when per-expert rows ≤ 8; DS41's N=3 verify
  shapes take the identical slab path), the last commit of the held-keep series (`2c4a1f2d2` → Z `9c60b2867` → Z'
  `70e7133a1`). It travels with the held keeps, which were not folded (DS41-C125), so the champion carries neither.
  Cross-model prefill is now part of the fold check: every 2026-10-04 fold ran a Q38FN arm (5g/Yfa/W gates, ledger in
  `autokernel-champion-aggregate.md`). Z vs X on Q38FN read −1.40% overall (5 pairs, no calibrated floor).
  *(2026-10-23, workspace-f8: protocol defect.)* 17 of the 28 c4 arm files carry `"autokernel_hardened": true`
  without `--autokernel-harden` (llama-bench uninitialised `autokernel_harden`, V11-103), mixed inside every ABAB
  pair, so the bisect compared protocols as well as commits. The first-bad verdict stands only if it holds on
  like-protocol pairs or a V11-103 re-run. Disposition tracked in LBH-2, `autokernel-rebuild-program.md`.
  *(2026-10-23, llama-bench harden UB, 3c4ca599: UNRELIABLE as filed; like-protocol re-analysis done, no compute.)* Re-read from the per-run
  `bench-q38-r*-*.jsonl` (hardened flag per row) in the c4 run dir, keeping only same-round pairs whose arms share a protocol, pp256 effect vs reference B:
  e038b28f1 r1 -25.0% (both hardened; r2 mixed); 6f8e232aa NO usable pair (both rounds mixed, the "GOOD" is protocol-confounded);
  9b148baab r1 -23.4% (both ordinary) plus the repeat `s3-9b148baab-x` r2 -24.8% (both hardened); ad8979943 r2 +1.1% (both hardened; r1 mixed);
  phase0 SLAB=0 arm X vs B +7.7% (r1, ordinary) and +2.6% (r2, hardened), while T (dd6c9cdbd) has no like pair. Result: the verdict
  **survives** (9b148baab BAD in 2 like-protocol pairs, ad8979943 GOOD in 1 like pair, boundary sits between idx 3 and 4, the step-2 gap does not matter),
  and the SLAB=0 recovery holds in both like pairs. Strength is low: n=1 like pair per step, no floor. Cannot support any -25% magnitude beyond sign.
  *(2026-10-23, workspace-f8, independent re-analysis.)* Pairing like-protocol runs across rounds within each step (same binaries, same minutes) also yields 6f8e232aa -2.55% / -0.37% (GOOD) and keeps every step verdict (closest effect 8.8 pp from G/2 = -11.38%); the same COR binary reads 287.25 t/s hardened (n=7) vs 286.80 ordinary (n=4) at pp256 (+0.15%), so the protocol barely moves pp256 here. Agrees: first bad = 9b148baab, sign only.
- [ ] DS41-C113 — **the DS41 launchers depend on a scratch worktree path.** (filed 2026-10-04; INC-20261004-cleanup-removed-load-bearing-worktree) `ds41_watchdog.sh`, `swap_*.sh` in
  `/mnt/raid0/llm/tmp/ds41-scope-20260926/` export `EPYC_ROOT_REPO=/mnt/raid0/llm/worktrees/root-main-epyc-root-repo`; its removal on 2026-10-04 crashed DS41 (02:25Z, relaunched 02:36Z).
  Point it at a pinned, marked-LOAD-BEARING path (or the canonical root clone), make the launcher fail fast with a named error when the path is missing, and stop the
  watchdog from falling to fallback args on a missing-dependency death. Robustness work in progress by another ak-ds41-main subagent; close when the relaunched loop runs on the new path.
  - [x] DS41-C113a — declare the two load-bearing worktrees. ✅ 2026-10-04 — `root-main-epyc-root-repo` is git-locked as "load-bearing: DS41 EPYC_ROOT_REPO (INC-20261004)" and `research-ds41-run10` as "load-bearing: DS41 live loop worktree". `scripts/system/worktree_gate.py` (root `837ebf6f`) refuses locked trees and trees named by a live process environment or launcher.
  - [ ] DS41-C113b — the launchers still hardcode the path (`ds41_watchdog{,2,3}.sh`, `swap_*.sh`, `pause_probe_restart.sh`), and none of them fails fast when it is missing. Do the fail-fast check and the watchdog no-fallback change at the next DS41 relaunch. Never edit a running script; copy it to a new name.
- [ ] DS41-C114 — **Plan: lossless MXFP4 routed experts** (filed 2026-10-04; operator 2026-10-03/04: "plan it"). Cross-ref DS41-T8.
  2026-10-04: gate (i), the MXFP4-vs-Q4_K microbench, is a step in CPU window 2 (armed, waiting).
  2026-10-04 05:00Z: window 2 refused it on host load (unlocked subagent CPU work; INC-20261004-subagent-unlocked-cpu-in-held-window). Re-scheduled as backlog item c2 (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c2/`).
  - [x] DS41-C114a — **gate (i) measured: no speed case, quality only.** ✅ 2026-10-04 — c2
    (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c2/runs/`, MUL_MAT_ID microbench at DS41 expert shapes, t48): MXFP4
    (CPU_REPACK) vs Q4_K (iqk) **×1.00 at N=1, ×1.04 at N=3**. The −2.0%/−3.5% byte saving does not show up as speed;
    MXFP4 is not slower either, so the "speed regression" branch of gate (i) did not trigger. The case for C114 is
    quality alone (KLD 0.0290 → 0.0102 public evidence). Gate (ii) (disk) and the splice are unchanged. c2's side
    finding (anchor-gen-022 slower than the iqk-allow build on Q4_K gate/up N=1) was not real: DS41-C124.
  - "Lossless": the native checkpoint's routed experts are already FP4 (`config.json` `expert_dtype: fp4`, MXFP4-class
    E2M1 + E8M0 per 32 = 4.25 bpw, `.weight` + `.scale` per expert). Repacking those blocks bit-for-bit into GGUF MXFP4
    is lossless; antirez's Q4_K experts (4.5 bpw) are a lossy requant (unsloth: ~5.2% RMSE). DS4-Flash public
    evidence: KLD 0.0290 → 0.0102, top-1 +2.3 pp. Bytes −2.0% (N=1) / −3.5% (N=3 verify): ~+1–2% decode plus a
    possible DSpark α gain. Source: `docs/reviews/cpu-quant-research-20261003.md` §1.4, §3.3; `docs/reviews/quant-variant-survey-20261003.md` §2.
  - Gate (i): MXFP4-vs-Q4_K CPU microbench in the next CPU window at DS41 expert shapes (from the GGUF header), N=1
    and N=3, t48, champion experimental build. MXFP4 runs on CPU_REPACK `mxfp4_8x8_q8_0` (AVX2), not iqk
    (`iqk_typeA_supported` excludes it); the 2026-10-03 iqk IQ4_NL/MXFP4 allowlist `8c4b282ae` was slower and diverged
    (INF-70 XFER-4) and was not folded. If MXFP4 repack is slower than iqk Q4_K at N=3, the swap is quality-only
    with a speed regression — decide with the operator then.
  - Gate (ii): disk. The FP4 source is **not on disk** (`models/deepseek-ai/DeepSeek-V4.1-Flash/` is 17 MB of
    metadata; the index lists 510.3 GB in 48 shards, 43 carrying experts). Spliced file ≈ 502 GB; the incumbent
    antirez file stays; a streaming shard-by-shard splice peaks at ≈ 513 GB vs 500 GB free on 2026-10-04 → needs an
    operator disk plan or a reclaim before the download.
  - Work once gated: splice tool keeping antirez's `e4m3_e8m0_32_row264` engram and KV names (loader
    `src/models/deepseek41.cpp:26-40`), bit-identity check on sampled blocks, coherence + KLD vs incumbent, the
    DSpark α A/B, T8 admission. ~2 sessions.
- [x] DS41-C115 — **AutoKernel local-model actors through the orchestrator passthrough.** ✅ 2026-10-04 — research `cd71b331` (pushed): `--actor-local-via-orchestrator`, default off. The passthrough already takes the CPU region locks per call, so the loop must hold no outer region lock around it. Caveat: a call waits up to 180 s for a lock.
  - [ ] DS41-C115a — **trial it.** Run one lane with `--actor-local-via-orchestrator` at a DS41 boundary. Record the lock-wait distribution against the 180 s bound and whether it sends 503 `contention_denied` to the loop. Then decide default-on or keep-off, with a reason. Until this runs the flag is landed but off.
- [x] DS41-C116 — **kernel feature-preservation gate.** ✅ 2026-10-04 — research `4f8f11c7` (merged as `3bb5c3b0`, pushed): `kernel_coverage.py`, gate G0 at fold, `KERNEL-REPLACES:` declarations for a candidate that removes a kernel on purpose, and a replay test of INC-20260925 (the parallel repack lost in a bundled revert).
- [x] DS41-C117 — **rework the per-target champion lineage. It must not split the ONE champion.** (filed 2026-10-04) `cross_target.py` in the same research commit adds per-lane champion branches plus an `ak-trunk`. It is on research main but NOT deployed: no run uses it. As written it breaks the ONE-champion invariant (`agents/shared/OPERATING_CONSTRAINTS.md` → *The Single Champion*). It also implies per-model production builds, which the operator flagged for its promotion, lean-registry and stack impact. The rework keeps one champion tip. Per-target evidence (the C111 cross-target veto, the C112 prefill check) gates keeps on that tip and never forks it. A model-specific kernel is a dispatch inside the one build. Rework in progress. Close when the reworked lineage lands and the per-lane branch code is removed or disabled with a test.
  ✅ 2026-10-04 — research `e4a7556d` (one champion; lane working branches fold into it) + `be23ac25` (audit fixes: a
  fold stands once the champion ref moves; the env-gate veto sees any getenv/environ), both on research origin/main,
  Fable-audited. Supersedes the per-target lineage of `3bb5c3b0`/`4f8f11c7`. The trunk IS the champion: the binding's
  `champion` must equal `champion.CANONICAL_BRANCH`, each lane names its own `working_branch`, and the old shape
  (`trunk` + per-lane `champion_branch`) is refused with a "second lineage" error (`test_cross_target.py`). A keep that
  regresses no peer folds by plumbing (merge-tree + commit-tree + CAS update-ref) after the G0 kernel-coverage check;
  a keep that regresses a peer stays on its working branch and queues a gate-by-model/arch/shape hypothesis. Folding
  is opt-in via the lane-targets `champion` + `working_branch` keys; no run uses it yet (DS41-C121). DS41's working
  branch carries 27 un-ledgered commits over the champion, so opting DS41 in needs those dispositioned first (C121).
- [ ] DS41-C118 — **DS41's coherence gate must be built on `coherence_gate`, never on the INF-70 classifier.** (filed 2026-10-04) workspace-ec found that the INF-70 classifier (`scripts/inf70/harness1/classify.py`) was fed synthetic token ids, so only its word and ascii rules could fire: a 200-token stuck loop classifies COHERENT. It is on hold, and the `coherence_gate` library replaces it (tiers 0/1/2; research `feat/coherence-gate-ec`). The rectification list (`/mnt/raid0/llm/tmp/classifier-rectify/RECTIFY.md` §e) has no DS41 handoff entry. It lists the research recipe `scripts/lib/deepseek_v41_flash_recipe.py:369` ("coherence gate at production prompt length") as a future requirement that should use `coherence_gate`. Close when the DS41 recipe's coherence gate and the C112 bisect's quality arm both run through `coherence_gate`.
- [ ] DS41-C119 — **the Q38FN lane's held-out floor.** (filed 2026-10-04) `heldout_frozen_prompts` in owned-targets makes
  `run.py` refuse until an explicit `--cpu-calibrate-heldout` has run, and `serial_run` cannot schedule that step, so
  run 1 launched without held-out prompts (matching DS41). Either run `--cpu-calibrate-heldout` once at the lane's
  restart (inputs: `/mnt/raid0/llm/tmp/q38fn-lane-run1-20261004/owned-targets.with-heldout.json`) or teach `serial_run`
  to schedule it. Done when a Q38FN lane run carries a held-out floor, or the gap is recorded as accepted with a reason.
- [ ] DS41-C120 — **opencode's 120 s shell timeout TERMs ak-check during its peer wait.** (filed 2026-10-04) Research
  `aef2da6c` makes ak-check wait up to 2700 s on another loop's `autokernel-cpu` claim (and is deployed into DS41's
  pinned worktree as local commit `5d947693`). An actor running ak-check through opencode's shell tool is killed at
  120 s, so a peer wait ends as a TERM the author reads as a failure rather than as a refusal. Fix one of: ak-check
  returns a "peer busy, retry" refusal before the harness timeout; the actor seat raises the shell timeout for
  ak-check; or the wait moves out of the actor's shell. Done with a test and one observed peer wait that ends as a
  refusal or a completed check.
- [x] DS41-C121 — **restart both lanes after the backlog drain, opted into ONE-champion folding.** (filed 2026-10-04)
  After the backlog (`/mnt/raid0/llm/tmp/backlog-schedule-20261004.md`) is exhausted: remove `WATCHDOG3_HOLD` and
  relaunch DS41 at a batch boundary on its lane0 args; relaunch the Q38FN lane with
  `/mnt/raid0/llm/tmp/q38fn-lane-run1-20261004/relaunch.sh`. Both run research ≥ `be23ac25` (which contains `aef2da6c`,
  `e2ccd6b8`) with lane-targets `champion` + `working_branch`, pinned to the then-current champion tip including the
  KVU-19 fold. Before DS41 opts in, disposition the 27 un-ledgered commits its working branch carries over the champion
  (ledger, fold through G0, or drop), so folding does not carry unmeasured commits into the champion. Fold in C113b,
  C108a and C119 at the same boundary. Done when both lanes run with folding enabled and the first fold or deferral is
  ledgered. ✅ 2026-10-05 — both lanes relaunched (DS41-C126), but **not** carrying C113b/C108a/C119 at this
  boundary — those three remain open and are now untethered from a boundary that already happened.
  - [x] DS41-C126 — **relaunch on `b0ba1d427` REFUSED on bundle/anchor ancestry; fixed with a fresh per-anchor
    store, not a code change.** Anchor builds done 03:18:59Z; `prepare_inputs` + 4 dry runs rc=0; DS41 launched
    03:19:35Z and refused: `bundle recovery required: invalid tip/anchor ancestry: persisted tip dd6c9cdbdf85 is
    not an ancestor of anchor b0ba1d427835`. The persisted accumulator bundle from the pre-backlog-drain epoch
    pinned an old tip; `seed_bundle` is documented as not the repair for this. Fix applied: each lane got a fresh
    store `store-b0ba1d427` (accumulator `champion_of_record` = tip = `b0ba1d427`, keeps `[]`, inbox notes copied
    across; old stores left untouched). DS41 relaunched 03:24:35Z (`serial_run` pid 3987149, watchdog4 3979082);
    Q38FN relaunched 03:25:05Z (pid 3988340). Prep dir `/mnt/raid0/llm/tmp/ak-lanes-relaunch-20261005/`
    (`RELAUNCH.md` has the full timeline). Gaps this surfaced:
    - [x] **(a) no supported path to start a new epoch on a new anchor.** Landed research 5aa6cc5b (`--new-anchor-epoch <COMMIT>` ancestry-refusal only, bound to the anchor's full SHA, journal-locked, archives under store/archived-epochs/, dry-run honors it) + `accumulate.would_refuse_anchor`/`peek_refusal` pre-flight.
    - [ ] **(b) `dryrun.sh` exited 0 on failure.** Fixed ad hoc in the prep dir
      (`/mnt/raid0/llm/tmp/ak-lanes-relaunch-20261005/`); pre-flight API now exists; wire it into the relaunch dryrun before the build lock.
    - [x] **(c) research commit `6cb5f0c5` (accept `--longctx-surface` in common args) is UNPUSHED** on branch
      `fix/ak-lanes-relaunch-20261005` in `epyc-inference-research` — ✅ pushed fd925e66 + 5da038ad.
    - [ ] **(d) the newcomer-lane calibration-vs-incumbent-batch race.** Q38FN cannot start hosted planning
      until its startup CPU calibration runs; with DS41 holding the CPU it waited >30 min past its wait bound.
      Operator ruling 2026-10-05: *"if the calibration is indispensable, prioritize making space for it."* Applied:
      DS41 pause queued via its control endpoint (`pause-for-q38fn-calibration-20261005`, takes effect at the next
      batch boundary ~05:30Z); watcher `resume_ds41_v3.py` resumes DS41 after Q38FN's calibration plus
      workspace-ec's decode check and the :8083 relaunch (gated on files `EC_DECODE_CHECK_DONE`,
      `EC_8083_RELAUNCH_DONE`; 120-min bound). Structural follow-up, still open: the loop should schedule a
      newcomer lane's calibration ahead of the incumbent's next batch automatically, rather than needing this
      per-incident watcher.
    - [ ] **(e) serial-control: offer a supported way to resume a drained lane (or make the control UI warn that drain is terminal).** 2026-10-05 Q38FN incident: drained at 11:11Z to open a measurement window sooner; drain is terminal for that state, so the lane could not be resumed from that point.
- [x] DS41-C127 — **served-shape calibration landed and applied on both lanes; new anchors.** ✅
  2026-10-06/07 Research commits, in order: `9a548baf` (`--timeout-s`, calibration exceeds 1h on
  DS41), `bed81e59` (three-regime NMSE cap: keep the old served-shape bound wherever the old policy
  accepted), `ac97318f` (deterministic per-case seeding; refuse binaries built before per-case
  seeding), `1bace97d` (sharded calibration under ONE build-role region-lock claim; fixes two Codex
  Astra BLOCKs in the sharded `--execute` claim), `a23af0a7` (shards confined to the lock's own cpu
  list; default `shards = min(16, cases, lock_cpus // 4)`).
  - Q38FN: 250 cases, 3392 s, no anchor-relative exception.
  - DS41: 348 cases, 5252 s on 24 cpus. Two IQ3_XXS shared-expert cases exceeded the 5e-4 NMSE cap
    and were applied with `--anchor-exceeds-generic` (anchor-relative acceptance, a known low-bit
    lead): `shexp_down` n=2 = 5.96e-4, `shexp_gate_up` n=4 = 5.22e-4.
  - Input-identity checks PASS: DS41 348/348, Q38FN 32/32, 0 mismatches.
  - New anchors: DS41 `3376147f8`, Q38FN `6ed37bec8`.
  - **Relaunch**: Q38FN on `q38fn_watchdog2.sh` / `state-6ed37b-*`, `LONGCTX=1`, live since
    2026-10-06T22:18Z. DS41's `ds41_watchdog5.sh` / `state-337614-*` launch was **REFUSED** by build
    retention (free disk 86 GiB < 100 GiB floor); disk cleanup in progress (see
    `agents/shared/OPERATING_CONSTRAINTS.md` → disk-retention lesson, 2026-10-07). The prior
    watchdogs on both lanes died on stale-epoch continuation seeding ("continuation binding does
    not match its own original arguments") — a new-epoch watchdog must seed only from the new
    epoch, never continue off the old one. DS41's `owned-targets.json` lacked `cor_build`; the
    operator added it 2026-10-07.
  - **Floor contamination, filed not fixed**: Q38FN's floor of 6.528% was contaminated by a
    5.5-minute degraded block during calibration (previously ~0.65%). A `REMEASURE_REQUEST` was
    filed for recipe `cff9ad900700…`. The matched-floor outlier guard that would have caught this
    (Astra R21-R24, research `e3bcf010`) landed the same cycle: a suspect floor never carries
    forward; an unguarded floor more than 3x the previous floor is refused and writes an atomic
    `REMEASURE_REQUEST.json` under `<store>/runtime-source-floors/<recipe_hash>/`.
  - **Harness fix in the same window**: research `de02a21d` — `run.py` was missing the `Mapping`
    import, a NameError that killed Q38FN's longctx keep-gate batches; adds
    `test_no_undefined_runtime_names.py` (package-wide AST guard).
  - 2026-10-07 03:03Z: **REMEASURE_REQUEST resolved** — the `cff9ad900700…` request is now
    `REMEASURE_REQUEST.claimed-20261007T030349159542Z-1658951.json`, consumed automatically when
    Q38FN relaunched on the new epoch (DS41-C128 below). No action needed.
  - Disk retention note above is now **resolved**: operator ran
    `/mnt/raid0/llm/tmp/disk-audit-20261007/delete_safe.sh`; free disk is 175 GiB (was 86 GiB).
- [x] DS41-C128 — **critic swap: both AK lanes now run with zero Claude models.** ✅ 2026-10-07
  03:03Z — critic switched from `claude-opus-5-5` to `gpt-6-astra@high` in all 4 common-args files
  under `/mnt/raid0/llm/tmp/ak-lanes-relaunch-20261005/` (backups `*.bak-20261007-critic`).
  New-epoch watchdogs (same directory): `q38fn_watchdog3.sh` (`state-6ed37a-*`, `LONGCTX=1`),
  `ds41_watchdog6.sh` (`state-337615-*`, hold file `DS41_WATCHDOG6_HOLD`). Confirms the DS41-C127
  continuation-binding lesson generalizes to any common-args edit (`serial_run.py:824-827`), not
  just a served-shape recalibration: seeding from an old continuation dies with "continuation
  binding does not match its own original arguments" regardless of what changed in the config.
  - 2026-10-07 ~02:55Z: Q38FN was SIGKILLed mid-batch (SIGTERM did not stop it within minutes) for
    an EC Jet-Long GPU window; EC then cancelled the window anyway. A control-endpoint pause only
    lands at batch boundaries (~3.4h), too coarse for a window request.
    - [ ] Give `serial_run`/`run.py` a pause/yield that lands at measurement granularity (one case),
      so a GPU-window request doesn't need a kill. Tracked in `autokernel-unified-surface-program.md`
      → AKU-RED-LOOP.
- [x] DS41-C121a — disposition the 27 commits DS41's working branch carried over the champion. ✅ 2026-10-04 — fold
    inventory `/mnt/raid0/llm/tmp/fold-allkeeps-20261004/inventory.tsv` (`orig → new` sha, keep id, gate evidence,
    disposition): 4 port + 1 profiling (`ebb68dc55`, compiled out unless `GGML_CPU_PROF`) + 7 serving-gated keeps
    FOLDED; 14 held keeps NOT folded (DS41-C125); `74ee5c502` excluded (un-ledgered, `measurement_invalid`); 3 empty
    merges dropped. Ledger: `autokernel-champion-aggregate.md` → *all-keeps fold*.
  - 2026-10-04 ~21:20Z: the champion is `b0ba1d427` (four folds today). DS41 relaunches on it with folding enabled at
    ~03:00Z 10-05, after workspace-ec's YaRN CPU leg (backlog row 9). Still to do at that boundary: C113b, C108a, C119.
- [x] DS41-C122 — **ak-check must treat another loop's `autokernel-cpu` claim as a peer.** ✅ 2026-10-04 — research
  `aef2da6c` (on origin/main). With two loops, both claim under the shared role `autokernel-cpu`, and
  `default_peer_status` / `wait_for_peer_region` excluded that role as "the loop's own claim". One loop's author would
  then compile and op-test on its affinity tail (184-191, the SMT siblings of 88-95) inside the other loop's live
  measurement. Now only GLOBAL is skipped; `DEFAULT_PEER_WAIT_S` 600 → 2700; the best-of ak-check validator timeout
  1800 → 3600, so a peer wait ends as a refusal, never as a timeout scored as a failure. Deployed into DS41's pinned
  worktree `research-ds41-run10` as local commit `5d947693` (ak_check.py only); the Q38FN worktree runs `aef2da6c`.
  Residual: DS41-C120.
- [ ] DS41-C123 — **Final attention is a dense −inf mask plus a full compressed-plane concat; the long-context lever
  is the graph/mask/host path, not the FA kernel.** (filed 2026-10-04, from the AutoKernel long-context audit
  `/mnt/raid0/llm/tmp/ak-longctx-audit-20261004/REPORT.md` §5; code reading at `dd6c9cdbd`, arithmetic not measured.)
  `deepseek41.cpp:1095-1100`: the top-k becomes a −inf mask over all compressed rows (`build_top_k_mask`), and
  `ggml_concat(raw_k, comp_k)` copies the full compressed plane in every layer at every step (~29 KiB per context
  token per step: ~0.9 GiB at 32k, ~3.6 GiB at 128k, against ~8.7 GB/token of weights). The CPU FA kernel skips −inf
  cells one by one (`ops.cpp:9367`), so FA dot products stay at ~640 rows per head; what grows with context is the
  concat, the mask fill / set_rows / add, the lightning indexer and `top_k` over the whole compressed set on 8
  index-source layers, and the host-side mask rebuild (DS41-C9). Attention design from GGUF metadata: sliding window
  128; compression ratio 2 on layers 2–19 and 1 on 20–39; `index_topk 512`; 64 heads over a 512-dim shared latent
  (K = V). This partly answers finding 1 and DS41-T2's disposition question (dense mask, at the final-attention
  stage); the cap-semantics half of T2 stays open. AutoKernel work on it is INF-81 AKX-ALL-12 (DS41 attention-graph
  route, which needs the AKX-ALL-4 long surface and the AKX-ALL-5 restore-identity gate). Done when AKX-ALL-12
  measures one candidate on this path at depth, or a measured profile at depth shows the concat/mask/indexer share
  is immaterial.
- [x] DS41-C124 — **The c2 "Q4_K regression" on anchor-gen-022 was not real.** ✅ 2026-10-04 (filed and closed the
  same day) c2 read anchor-gen-022 slower than the iqk-allow build on Q4_K MUL_MAT_ID gate/up at N=1, from one launch
  per arm in a fixed order. c5 (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c5/runs/20261004T103459Z/report.md`, 6
  interleaved rounds, 4 arms incl. v10) found every Q4_K delta inside the between-round noise (D vs V −5.10%
  [−19.44, +1.46], CV 9.5% → NOT REAL); the bisect phase was skipped. Lesson: `docs/guides/agent-workflows/benchmark-analyst.md`
  → *Gating and folding AutoKernel keeps*.
- [ ] DS41-C125 — **The 14 held keeps after COR: re-gate or drop.** (filed 2026-10-04) Each kept on a 5-pair
  keep-grade A/B, but two bundle gates were null: `dca32b0e3` (8 keeps) DIVERGED, +0.10% vs the 4.533% floor; and Z
  (X + 14 keeps + the C112 shape gate) vs X on 2026-10-04: DS41 **−2.51%** (floor 4.533%), Q38FN −1.40%, greedy
  identical (`/mnt/raid0/llm/tmp/fold-allkeeps-20261004/runs/20261004T125648Z/`). Not folded. Rebased onto Y as Z'
  `70e7133a1` (`fold/champion-Zp-20261004`, CPU image `cpu-20261004-70e7133a1`, full CPU suite PASS). Options: (a)
  drop them and let the relaunched loop re-find what is real on the new champion; (b) re-gate Z' on the
  `b0ba1d427` champion once the DS41 floor is cleaner (DS41-C92). Recommendation (a): two nulls at bundle level, and
  the loop re-proposes on the new base anyway. Done when Z' is dropped or re-gated with a ledgered verdict.
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

### W — 1017 weight swap (operator 2026-10-20)

`deepseek-ai/DeepSeek-V4.1-Flash-1017` (HF `1bae0e10`) is a drop-in finetune: config.json and the
96,085-tensor shard map are byte-identical to the September release, and all 48 shards changed,
including the DSpark shards 44-46. Operator: swap the served weights.

**Operator rulings 2026-10-20:**
1. Serve antirez's 1017 **MXFP4-experts** build directly: "if we can run the MXFP4 quant directly that
   would be best". On DS4-Flash the public KLD was 0.0102 for native MXFP4 and 0.0290 for the FP4->Q4_K
   requant (DS41-C114). The MXFP4 experts are a lossless repack of the official FP4 weights.
2. Delete the Sept Q4: "No point keeping it. the 1017 variant is strictly better."

The other routes were checked and rejected:
- No publisher ships a 1017 Q4_K-experts build in the antirez layout.
- Every unsloth 1017 GGUF uses the upstream PR #30817 layout and does not load in the port.

Working notes (scratch, KEEP until W7): `/mnt/raid0/llm/tmp/ds41-1017-swap/` (`alt-quants.md`,
`requant-feasibility.md`, `requant-types.txt`, `download_1017.sh` and its log).

- [x] DS41-W1 — **Download** `antirez/deepseek-v4.1-flash-gguf` ✅ 2026-10-29 (audit: download_1017.done present; log 'ALL DONE' 2026-10-21T08:22:38Z, 9 shards sha256 OK, 501,602,535,360 B (text :1363; 'main reviews the close')) [no-belief: audit-reconciliation]
  `DeepSeek-V4.1-Flash-1017-MXFP4-experts-0000{1..9}-of-00009.gguf` (501,602,535,360 B) into the
  served model dir.
  - Script: `tmp/ds41-1017-swap/download_1017.sh`. One file at a time, resumable; each file must match
    its HF LFS sha256 before it is renamed.
  - Running since 15:25Z. It was restarted at 16:33Z to move the HF token off curl's argv into a 0600
    header file, and resumed from 42.07 GB.
  - Progress is in `download_1017.log`; the flag file is `download_1017.{done,failed}`. About 10 MB/s,
    finishing roughly 2026-10-21 05:00Z.
  - Also fetched: the unsloth 1017 imatrix (`models/unsloth/DeepSeek-V4.1-Flash-1017-GGUF/`, sha256
    `22ed7e8f...`). All 120 expert tensors have an entry under the same name. It is kept for a requant,
    should W3 ever be needed.
  - 2026-10-21 NOTE (ETA above is stale): `download_1017.log` shows PAUSED 2026-10-20T23:19:58Z by nemotron-bolt-dl (operator: prioritize Nemotron), RESUMED 2026-10-21T02:15:26Z, and `ALL DONE` at 08:22:38Z with `download_1017.done` present; all nine shards logged OK with sha256 and total 501,602,535,360 B on disk in the served model dir. Checkbox untouched (main reviews the close).
- [x] DS41-W2 — **Disk / Sept Q4 disposition.** ✅ 2026-10-20: operator approved deleting
  `/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-Q4.gguf`
  (518,596,067,328 B). The deletion is executed in W7. Until then it stays as the only loadable DS41
  artifact, because the 1017 shards are incomplete. `assert_not_mapped.sh` at 16:30Z: no readable
  process holds it.
- **DS41-W3/W4 (requant MXFP4 -> Q4_K with the unsloth imatrix): not pursued, by ruling 1.** It remains
  the fallback if W5 fails a gate. The feasibility notes stay in `requant-feasibility.md`: the
  expert-only `--tensor-type-file`, and the warning that a bare Q4_K run would requantize Q8_0/F16 and
  abort on the I8 engram.
- [ ] DS41-W5 — **Validate the 1017 MXFP4 build in the port.**
  - Load check: 9-shard split load, 1046 tensors, `deepseek41` KVs, `general.alignment=32`. The Sept
    file was 16384-aligned, so re-check anything that assumed 16 KiB direct-IO alignment.
  - Gates: ppl on the standard text (compare with the Sept Q4 record), the coherence gate at
    production prompt length, NMSE spot checks, and DSpark alpha once W6 lands.
  - Serving speed vs the Sept Q4 AK headline. The MXFP4 CPU path is the AVX2 `mxfp4_8x8_q8_0`
    repack, not iqk. It was x1.00 at N=1 and x1.04 at N=3 against Q4_K iqk *before* the keeps
    (DS41-C114a).
  - This starts a new DS41 measurement era.
  - *(2026-10-21, correctness half.)* Port `experimental/ds41-ak-20261005` @ `3376147f8`, CPU build `build-cpu`
    (binaries built 4 min after HEAD, tree clean), q0 (`region-lock --role build --cpu-list 0-23`), `-t 24`.
    Results, harness and capture rows: `epyc-inference-research/data/ds41-1017-w5-20261021/` (SUMMARY.md).
    The rows are written by the VB-DS41-1017-WIRE producer and bind the 9 shard sha256s. No protocol id,
    so they are OBSERVATIONS.
    - Load: **PASS.** 9-shard split load, 1046 tensors, `deepseek41`, `general.alignment=32`. The direct-IO
      reader rounds its offsets to `st_blksize`, so no 16 KiB assumption bites. Both arms log
      `unused tensor blk.N.exp_probs_b_vl.bias` on all 40 layers; that is not new in 1017.
    - Coherence: **PASS.** Paired `coherence_gate`, base = Sept Q4, cand = 1017, greedy. 0 regressions over
      5 items at 7/41/65/235/2041 prompt tokens. The p220 `BOTH_BAD` is the needle scorer missing Sept's
      `(1,6)` spacing; both arms answer correctly. 1017 is also coherent at 2030 prompt tokens. Shared
      quirk: a raw prompt of article + question + `Answer:` gets an immediate EOS in both arms at 309+
      tokens (DS41-W5b).
    - ppl (wiki.test.raw, c=512, 32 chunks): 1017 **2.6675 ± 0.0675** vs Sept Q4 **2.6122 ± 0.0655**
      (+2.1%, within 1 sigma). This is a different finetune, not a pure quant delta. It is measured
      without the W5.1 FP8 round trip.
    - NMSE spot checks: **not run** (DS41-W5a).
    - Serving speed: **DONE** ✅ 2026-10-21 (ABA per the operator ruling; INDICATIVE). Full table and caveats in
      `data/ds41-1017-w5-20261021/SUMMARY.md` (research `da71fa603`). Served decode, 1017 vs Sept Q4 under identical
      conditions (segment B, beside the f8 G1 GPU job): 15.01 vs 13.89 t/s, +8.1% for 1017. llama-bench tg128
      -5.1% and pp512 -29.9% for 1017 (the `mxfp4_8x8_q8_0` repack prefill is slower than iqk Q4_K). 1017 drifted
      12.87 (A1) -> 15.01 -> 16.34 -> 15.99 (A2); A1 is a cold-state outlier. GPU impact B2 (on) vs A2 (off)
      +2.2%, within drift: no measurable penalty on full-host CPU decode. Each 1017 server holds ~276 GiB private
      RAM plus ~463 GiB mapped; two concurrent servers caused the 15:57Z earlyoom kills.
      *(2026-10-23, workspace-f8: protocol defect; the served numbers above are unaffected.)* The llama-bench pair
      crosses protocols: `bench-B-sept-q4.json` rows say `"autokernel_hardened": true` with no `--autokernel-harden` in
      its argv, while `bench-B-1017.json` ran ordinary (llama-bench uninitialised `autokernel_harden`, V11-103). The
      tg128 -5.1% and pp512 -29.9% are therefore INVALID until re-measured on a V11-103 build, and the DS41-W8a /
      S5 premise needs that re-measure first. Disposition tracked in LBH-2, `autokernel-rebuild-program.md`.
      *(2026-10-23, llama-bench harden UB, 3c4ca599.)* Verdict: the "1017 vs Sept" llama-bench delta (tg128 -5.1%, pp512 -29.9%) is **INVALID**
      (Sept arm hardened, 1017 arm ordinary) and **permanently unrecoverable** (operator ruling 2026-10-23: the Sept Q4 GGUF was deleted
      2026-10-21 and will NOT be re-downloaded; closed INVALID, not "re-measure later"). The S5 / W8a premise is re-tested without the Sept model
      by DS41-W5d below (1017-only baseline + model-free MUL_MAT_ID microbench). Tasks below.
      - [x] **DS41-W5c — same-protocol re-measure of llama-bench 1017 vs Sept Q4 (tg128, pp512).** ✅ 2026-10-23 **CLOSED INVALID, unrecoverable** (operator ruling 2026-10-23: no Sept re-download; the Sept Q4 GGUF is gone, so a like-for-like arm cannot exist). Nothing was run: the prepared re-measure (`/mnt/raid0/llm/tmp/ds41-w5-remeasure-20261024/`, record only, see its `CLOSED.md`) is dead. Replaced by DS41-W5d. (derived 2026-10-23 from LBH-2; closed by 3c4ca599)
        - *(2026-10-23, workspace-f8.)* Per-row evidence: both files use build 3376147f8/10339 with the same argv and no `--autokernel-harden`: `runs-aba/bench-B-1017.json` pp512 87.945 / tg128 16.666 hardened false; `runs-aba/bench-B-sept-q4.json` pp512 125.386 / tg128 17.568 hardened true. No same-protocol subset exists. Additional blocker: the Sept Q4 GGUF was deleted 2026-10-21T19:00Z (W7, graveyard row 99), so a like-for-like re-measure needs a ~519 GB re-download. Cheaper premise test when DS41 work unfreezes: extend the c2 MUL_MAT_ID microbench (MXFP4 repack vs Q4_K iqk) to pp512 shapes (8/16/64 rows per expert); no model load. The served decode figure (+8.1%) is llama-server and unaffected. The live campaign inbox S5 note (`ak-ds41-1017-cpu-decode-20261021/store/inbox/30-...md`) still quotes -29.9%: its owner should annotate it.
      - [ ] **DS41-W5d — 1017 baseline + MUL_MAT_ID premise microbench (operator choice "1017-only + microbench", 2026-10-23): (a) clean UNHARDENED absolute pp512/tg128 baseline of the 1017 (6 llama-bench processes, `-r 3`, with its 95% CI, no comparison arm) on the CH-28-fixed image `kernels/builds/cpu-20261023-141e4bcf5-lbh`; (b) model-free MUL_MAT_ID microbench at the 1017 pp512 expert shapes (gate/up 5120x2304, down 2304x5120, 384 experts, 6 used, MXFP4; N=512 tokens = 8 rows/expert): does the served MXFP4 CPU_REPACK path lose to the Q4_K iqk path by more than 3.0% (unit = per-round layer-time ratio, uncalibrated), i.e. is the DS41-W8a / AK seed S5 premise real, and what share of the pp512 wall could S5 recover.** Prepared (predeclared, sha-pinned, self-tested, NOT armed) at `/mnt/raid0/llm/tmp/ds41-1017-baseline-mmid-20261023` (`PREDECLARED.md`, `job.sh`, `analyze.py`, `ROW.md` = the 18-cell FILLERS row `ds41-w5d-baseline-mmid`, ~45 min typical / 90 bound, 739 GiB, whole host, block-timing-quiet). ARMED 2026-10-23 (no longer blocked; ch28 fold done): FILLERS row `ds41-w5d-baseline-mmid` is booked for 2026-10-24 ~10:00Z; the operator's DS41-1017 hold is lifted for this one task. Supersedes the earlier workspace-f8-filed wording of this ID (same intent: extend the c2 microbench to pp512 shapes, which has no 1017/pp512 baseline). (derived 2026-10-23 from the LBH-2 W5 note above; re-scoped by 3c4ca599 per the operator decision)
        - 2026-10-27 harvest (ds41-w5d-baseline-mmid, ended 2026-10-24T06:37Z rc 0 complete): predeclared sha `fd6a3ab8…`, `/mnt/raid0/llm/tmp/ds41-1017-baseline-mmid-20261023/out/RESULT.json`. (b) MXFP4 CPU_REPACK (served) vs Q4_K iqk MUL_MAT_ID layer-time ratio at N=512: gm 1.783 (95% CI 1.778-1.789), >1 in 6/6 rounds vs the 1.03 bar: **PREMISE_STANDS** (N=1024 1.785, N=4096 4.07; native MXFP4 arm 2.448x; S5 ceiling about 22.2% of the pp512 wall, MMID share about 50.6%; arm CV 0.15-0.18%). (a) absolute 1017 baseline: pp512 mean 103.55 t/s (CI 100.55-106.56, CV 2.8%), tg128 mean 15.22 t/s (CI 13.32-17.11, CV 11.87% > 4.0% cap): **INVALID_NOISY**, so no baseline is quotable. Classification: performance premise (microbench, uncalibrated ratio), baseline invalid. The (b) number is already quoted in W5e below. [belief: cc]
        - [ ] **DS41-W5d.1 — re-run part (a) only (6 llama-bench processes of the 1017, quiet whole host) to get a tg128 baseline under the 4.0% process-CV cap; the 10-24 run's tg128 values drifted 11.75 -> 16.65 t/s across processes (first process lowest), so check warm-up/page-cache residency before the re-run.** (filed 2026-10-27, harvest of ds41-w5d-baseline-mmid)
      - [ ] **DS41-W5e — annotate the live campaign inbox note `ak-ds41-1017-cpu-decode-20261021/store/inbox/30-ds41-1017-mxfp4-seeds-20261021.md`: its -29.9% pp512 premise for seed S5 is INVALID (cross-protocol, LBH-2 item 1).** The campaign store is the campaign owner's single-writer surface, so the owner writes the note; a wrap-up subagent does not. (derived 2026-10-23 from the LBH-2 W5 note above; filed by the workspace-f8 midday wrap-up)
        - *(2026-10-24, workspace-f8 vidya batch; box stays open, per this task's own rule.)* The annotation text is prepared: `/mnt/raid0/llm/tmp/f8-vb-batch-20261024/ds41-w5e/ANNOTATION-for-inbox-30.md` (sha256 `4a42eb55...`). It marks -29.9% INVALID and unrecoverable, and replaces it with the DS41-W5d result from 06:37Z today: (b) the MXFP4 CPU_REPACK MUL_MAT_ID takes 1.783x the Q4_K iqk per-layer time at the pp512 shapes (95% CI 1.778-1.789, PREMISE_STANDS, S5 ceiling about 22% of the pp512 wall); (a) the absolute baseline is INVALID_NOISY. The campaign `ak-ds41-1017-cpu-decode-20261021` has never launched, so no planner has read the note yet. Named event: the campaign owner appends it (or adds it as note `32-...`) before the first launch.
  - [ ] **DS41-W5a — NMSE spot checks for the MXFP4 expert path.** The CPU-only build has no second backend,
    so `test-backend-ops` has nothing to compare against. Use a served-shape MUL_MAT_ID MXFP4 case set (the
    `served_shape_cases.py` lane profile from the 1017 GGUF) against an f32-dequant reference, cap 5e-4.
    (derived 2026-10-21 from DS41-W5)
    - *(2026-10-21, weight half DONE, no server; research `73aab47cc`, `data/ds41-1017-w5-20261021/w5a/`.)*
      The 1017 experts are **natively MXFP4**. HF stores them as `I8` packed E2M1 with an `F8_E8M0` scale per 32.
      In the GGUF, the E2M1 codes and E8M0 scales are **bit-identical** to the source on 4/4 checked expert matrices,
      so NMSE = 0.0 by construction. Q8_0 non-experts vs their FP8 E4M3 source (32x32 E8M0 blocks) measure NMSE
      2.92e-5 to 2.99e-5 on 4 tensors. F16 tensors vs F32 source measure about 4e-8.
    - *(2026-10-21, kernel half: existing evidence VACUOUS.)* The AK served-shape calibration's MXFP4 NMSE = 0.0
      proves nothing about the served path: `test-backend-ops` allocates plain CPU buffers, so it never runs the
      `CPU_REPACK` `mxfp4_8x8_q8_0` GEMV that the 1017 server uses for every routed row, and both of its arms
      execute the same generic kernel. A real-weight harness is built (`w5a/mxfp4_repack_nmse.cpp`). It compares
      CPU_REPACK and plain-buffer MUL_MAT_ID against an f32 reference at n = 1 to 512, asserts that the weights
      were repacked, and runs no server. It is armed as step W5A of the DS41-W6.2 slot driver (starts >= 2026-10-22T23:30Z).
      Close this box when `w5a_kernel.jsonl` shows every case at or under 5e-4 with `repacked` true.
  - [ ] **DS41-W5b — raw-completion empty-EOS on article + question + `Answer:` prompts.** Both arms
    (Sept Q4 and 1017) emit EOS as the first token at 309-2041 prompt tokens. A question-first variant
    answers fine at 2030 tokens. Check whether this is a template/BOS effect (DS41-T3.3b) or model
    behaviour before using raw-completion prompts in any long-prompt gate. Rows:
    `data/ds41-1017-w5-20261021/raw/coh-1017-len.rows.jsonl`. (derived 2026-10-21 from DS41-W5)
    - *(2026-10-21, static findings; research `73aab47cc`, `data/ds41-1017-w5-20261021/w5b/`.)*
      - Ruled out: tokenization, double BOS, the chat template and the harness. llama.cpp ids equal HF
        `tokenizer.json` (1017) on all 10 W5 prompts, there is a single BOS, `/completion` applies no template,
        and `coherence.py` is plain greedy with no stop strings.
      - The only token-level difference between failing and passing prompts: every failing prompt ends with the
        merged token `?Ċ` before `Answer:`, while `q40`/`p220` end `.Ċ`/`.ĊĊ`. The failing prompts are also
        wikitext-formatted and cut mid-word.
      - `qfirst9000` passing does not clear the port: its answer is inside the last ~128 tokens.
      - Decisive run armed: step W5B of the slot driver. One target-only server runs 20 probes with `n_probs`:
        suffix, content and length-ladder variants, EOS-banned controls and a chat-rendered arm. The
        reading table is in `w5b/README.md`.
- [ ] DS41-W5b - **Run the DS41-1017 target-only baseline (24 A/A pairs, then champion vs candidate C) on the AK loop's `matched_process_v2` instrument.** Armed 2026-10-21: `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/chained_launch.sh` (starts itself at 2026-10-22T06:30Z, then blocks on the region lock and takes q0-q3 plus gpu-quiet exclusive in one claim, runs a 9-shard page-cache warm-up, `calibrate` 24 pairs, `compare` 5 pairs; refuses unless `APPROVED` matches `gate_1017.py` and `PREDECLARED.md` and `SMOKE_OK` is newer than `APPROVED`). Recipe `ds41-1017-mxfp4-cpu-t48-targetonly` (template_hash `65f1c793...`, request digest `e50732d9...`, split-model digest `ba9f129c...`), predeclared counts N_AA=24 / N_CMP=5, effect = median(C)/median(champion)-1 judged against the instrument's floor. Done when `RUN_RECORD.json` exists with the floor file path (first DS41-1017 process-level floor, not comparable to the Sept 3.412%/4.533%) and the compare row. Retirement independence checked 2026-10-21: a guarded dry-run (stat/open/listdir/scandir/access/readlink/subprocess patched to raise, plus an audit hook) of `gate_1017.py --dry-run` and `calibrate` plan shows ZERO touches of the Sept Q4 or the DSpark drafter, so deleting them does not affect the run. (filed 2026-10-21) — *(2026-10-22: the floor half is done, see DS41-W5b-floor; the compare half is DEFERRED, see DS41-W5b-compare; operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done.)*
  - 2026-10-21 smoke gate PASS (`SMOKE_OK` 12:37Z): champion `dd3d9721c` and candidate `f0c96dc1f` both load and serve the 1017 split GGUF with the exact recipe argv/env/port; frozen request x2 deterministic with 256 tokens; the two builds are token-identical; load 95-105 s; 16.8-17.2 tok/s (single run, no claim beyond load/coherence/determinism); text coherent. First sight of 1017 target-only decode speed on these builds; not a baseline.
  - 2026-10-21 (c2-regate) **candidate switched C -> C2** (`c-plus-nemotron-bolt-20261021` @ `49550eda5`, approved by main): arm now `chained_launch_c2.sh`, patched `gate_1017.py`/`PREDECLARED.md` re-approved; evidence `/mnt/raid0/llm/tmp/c2-regate-20261021/SMOKE_C2.json` (C2 loads 1017 via mmap, 2x256 tokens deterministic, coherent, 256/256 identical to the champion in the SAME config).
  - 2026-10-21 **LESSON: DS41-1017 greedy output depends on the thread count (and load mode).** The same champion build at `-t 40` mmap vs `-t 48 --no-mmap` diverged from token 10 (244/256 tokens differ); C2 vs champion at identical `-t 40` mmap config was 256/256 identical. Gates and smokes must compare only same-config arms (same `-t`, same load mode, same cpuset); never compare tokens across configs, and never read a cross-config mismatch as a build regression without the same-config control. Source: `/mnt/raid0/llm/tmp/c2-regate-20261021/SMOKE_C2.json` + `SMOKE_CTL_champion.json`.
  - [x] **DS41-W5b-floor — first DS41-1017 process-level serving floor: COMPLETE.** ✅ 2026-10-22 Stage-3 baseline from 06:30Z (`gate_1017.py`, `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/`): floor **2.862%** (unit = process, n = 24 A/A pairs, gates k = 5-pair compares), interval 1.974-5.757%, 7394 s, build `cpu-20261020-dd3d9721c`, `matched_process_v2`. Floor file `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/aa/floor-store/serving-floor.ds41-1017-mxfp4-cpu-t48-targetonly.requests-e50732d9ce365259d5bb95fe31e36995f98bcd0986dc0e48d489f99390e42f58.matched_process_v2.pairs-5.json`. Sensitivity check (`FLOOR_SENSITIVITY.md` there): STANDS as decision-grade; every exclusion variant LOWERS the floor (2.33-2.55%), tagged launches show no systematic shift, and PREDECLARED forbids post-hoc exclusion. Annotation, verbatim: "launch 1 is a cold-start outlier (10.67 tok/s, before any disclosed activity); floor without it is 2.445%; launch 39 (14.85) dips inside a disclosed-activity window; post-hoc exclusion forbidden by PREDECLARED". **Valid ONLY for build `dd3d9721c` (pre-W5.1a numerics epoch)**; not comparable to the Sept 3.412%/4.533%. Host-activity disclosure: `HOST_ACTIVITY_DISCLOSURES.md` there (an f8 subagent's pytest + prior_check ran ~08:10-08:50Z; cleared by the sensitivity check). (f8, 2026-10-22)
  - [ ] **DS41-W5b-compare — champion `dd3d9721c` vs candidate C2 `49550eda5` (5 alternating pairs = 10 launches) and `RUN_RECORD.json`.** RUNNING at 08:41Z (launch 2 of 10 recorded; started 08:36Z in `chained_launch_c2.sh`, `cmp/launches-compare.jsonl`); judge the effect against the 2.862% floor, tag every compare launch against `HOST_ACTIVITY_DISCLOSURES.md`, flag any >3xMAD outlier. Done when `RUN_RECORD.json` exists with the compare row; then DS41-W5b, CH-20.1 (i) and VB-DS41-1017-BASELINE-WIRE can be settled. (filed 2026-10-22) — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; stage-3 stopped the compare and its server at ~08:5xZ, ~739 GiB freed; no compare row exists). Not done; reopen when AK kernel work has landed.
  - [x] record the 2.862% floor in the MASTER model registry (orchestration/model_registry.yaml, per-model `serving_floors` entry with its annotation and dd3d9721c/pre-W5.1a validity) — operator decision 2026-10-22: floors live in the master registry, not a separate store (owner f8, filed 2026-10-22). Registry + AKX-AUTO-6 `champion_reanchor` + the `serial_run --new-anchor-epoch` pass-through are built on research `f8/floor-registry` and root `f8/floor-registry`; their tests are not yet run (run in today's granted windows, then register; the registered row carries the pre-W5.1a-epoch limit above). ✅ 2026-10-22 recorded: research `d077d6c55` (first `serving_floors` entry in `orchestration/model_registry.yaml`, `floor_pct: 2.862`, process, n=24, k=5, 48 threads, quiet, decision grade, pre-W5.1a, `dd3d9721c`); orchestrator `e945ca37` records `serving_floors` as a lean-compile drop.
- [x] DS41-W6 — **DSpark drafter for 1017.** ✅ 2026-10-21 The 1017 MTP shards changed, so the Sept drafter
  `models/deepseek-ai/DeepSeek-V4.1-Flash-DSpark.gguf` no longer matches the target.
  - unsloth's `dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf` (7,976,914,240 B) does not load as is. It is
    arch `dflash`, lacks `token_embd`/`output`, `hc_head_*` and `dspark_variant`, and has an `add_bos`
    mismatch.
  - It is convertible with gguf-py: rename `fc`, `enc.output_norm`, `markov_w{1,2}` and `conf_proj` to
    the `dspark_*` names; copy `token_embd`/`output` from the **1017** target; rewrite the KVs to
    `deepseek41-dspark.*`.
  - Our loader's BF16 acceptance for the markov tables is unverified.
  - The original safetensors converter (`tmp/ds41-dspark-convert`) is lost.
  - Gate: the DS41-B13 conversion checks plus an alpha A/B.
  - *(2026-10-21.)* `models/deepseek-ai/DeepSeek-V4.1-Flash-1017-DSpark.gguf` (10,004,006,720 B, sha256
    d9ddd4be…4ebd), converted by research `c11c512f2`; B13 checks pass; loads and spec-decodes on 1017; alpha
    1017 0.582/0.476 vs Sept 0.609/0.486 (blocks 2/3, 16 prompts).
  - [ ] **DS41-W6.2 — Confirm the 1017-vs-Sept drafter alpha gap with more pairs.** (Numbered W6.2 because
    DS41-W6.1 already exists below.) Partial result: n=2 pairs block 2, A−B −1.9 pp, CI [−4.2, −0.0]; n=1 block 3,
    −0.9 pp; research `37cc352cc`. Needs ≥3 more pairs, run one server at a time, plus a greedy identity pass.
    The Sept DSpark drafter is kept until then.
    - **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; driver2 stopped via STOP, exited rc=3 08:40Z; the Sept DSpark drafter is therefore no longer needed, see DS41-W7.2). Not done; reopen when AK kernel work has landed.
    - *(2026-10-21, ARMED; research `73aab47cc` + `d0b392982` + `c036eaa40`, `artifacts/ds41_w6_dspark_1017_20261021/w6.2/`.)*
      - Driver: `/mnt/raid0/llm/tmp/ds41-w5ab-w62-20261021/driver2.sh`, PID 1645930 (setsid group). It dies on a
        host reboot and nothing re-arms it. It replaced `driver.sh` PID 1360538 after the coordinator's window
        change; that driver was stopped while still waiting.
      - Start gate: CS-47 now runs first. The driver waits for the later of a fresh
        `compute-flags/grants/cs47-latency.ended` and 2026-10-22T23:30Z, falling back to 23:35Z if the flag never
        appears, then takes ONE build claim on 0-47.
      - Steps: W5A, then W5B, then pairs p3 A,B (+ full greedy pass), p4 B,A, p5 A,B, and p6 B,A if it fits.
        Arms run sequentially at `-t 48`, seeds `1000p+234+i`.
      - Every load passes a MemAvailable ≥ 400 GiB gate and a no-other-DS41-server gate. Every step is bounded
        to the 2026-10-23T02:00Z hard stop.
      - Timeline: `compute-flags/DS41_W62_TIMELINE.txt`. End flag: `compute-flags/DS41_W62_ENDED`.
      - Dry run PASS.
      - Post-run: `analyze_post.py --agent <id> --commit --push` (paired-t CI over all complete pairs, old plus
        new; it reproduces W6.1 exactly on the old rows; greedy identity p3A vs p3B; it also writes the producer
        belief rows).
- [ ] DS41-W7 — **Cut over and retire the Sept artifacts.**
  - Update `epyc-inference-research/scripts/lib/deepseek_v41_flash_recipe.py`. The trunk is now a
    9-shard split, so `TRUNK_GGUF` becomes shard 1 plus a shard/sha256 list, following the
    `qwen38_flash_next_recipe.py` `TRUNK_SHARDS` precedent. `assert_artifacts_exist` currently assumes
    a single file. Also update `TRUNK_GGUF_VERSION` and `DRAFT_GGUF`.
  - Do not land the recipe before the shards are complete: every live DS41 launcher asserts the
    pinned artifacts.
  - Then delete the Sept Q4 (approved in W2) via `guarded_rm.sh --bypass-guard` after
    `assert_not_mapped.sh` passes, and record its graveyard row.
  - [x] Recipe cutover ✅ 2026-10-21 (research `ada2bf38a`).
  - [x] Sept Q4 deletion ✅ 2026-10-21T19:00:05Z (518,596,067,328 B; `assert_not_mapped.sh` PASS 18:59Z; graveyard
    row 98 -> 99, research `7f2f7fece`).
  - The Sept DSpark drafter (9.4 GiB) goes once the W6 drafter passes. That deletion is not yet
    approved; confirm it with the operator.
  - [ ] **DS41-W7.2 — delete the Sept DSpark drafter `/mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash-DSpark.gguf` (10,004,008,256 B), then record its graveyard row. PENDING OPERATOR.** No longer needed since DS41-W6.2 was cancelled 2026-10-22. Unmapped, with no live references (checked 2026-10-22). workspace-58's `rm` was BLOCKED by the auto-mode classifier, so the operator runs or approves it. Write no graveyard row until the file is gone. (filed 2026-10-22, workspace-58)
- [ ] DS41-W8 — **Re-point AutoKernel at the MXFP4 expert path.** The DS41 keeps (+7.11% serving;
  keeps 3 and 4 target the Q4_K X4_T kernel) do not apply to MXFP4 experts. After W5, re-anchor the
  DS41 AK campaign on the 1017 MXFP4 artifact and seed the AVX2 `mxfp4_8x8_q8_0` repack GEMV/GEMM as
  the target surface (AK decides knobs; low-bit perf is AK's job).
  - *(2026-10-21, note; W8 stays open.)* MXFP4 served-shape oracle (research `3cf5e5b0f`), calibrated at anchor
    `06b169e27` with 360 + 8 routed cases; 2 IQ3_XXS cases held anchor-relative (operator).
    `--require-serving-floor` (`577f50d44`) and `--serving-calibration-only` (`c5997024e`). New campaign
    `ak-ds41-1017-cpu-decode-20261021`; the old campaign `ak-ds41-cpu-decode-20260923` is SUPERSEDED (operator).
    The floor is booked for 2026-10-22 18:00–22:00Z (launcher PID 4188290). *(Superseded: the operator cancelled that booking 2026-10-21 21:2xZ, launcher stopped, in favour of one calibration post-C2-CAS + W5.1a; on 2026-10-22 that became DS41-W5.1a-floor, now deferred until the operator launches AK on a changed anchor.)*
  - *(2026-10-21, seeds; W8 stays open until the loop has run on them.)* Two operator-inbox notes were seeded into the
    new store (the inbox is re-read on every iteration by `controller/inbox.read_inbox`; the same channel as old
    notes 10–74): `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-1017-cpu-decode-20261021/store/inbox/30-ds41-1017-mxfp4-seeds-20261021.md`
    (sha256 `40d5eebe…`) and `…/31-ds41-1017-carried-lessons-20261021.md` (sha256 `88d0ab29…`).
    - Source finding: MXFP4 is in neither the iqk repack-diversion list (`repack.cpp:4547`) nor
      `iqk_typeA_supported`, so the experts run CPU_REPACK `mxfp4_8x8_q8_0`. Its `forward_mul_mat_id` calls one
      `gemv` per routed row (never `gemm`), quantizes src1 on 1–6 threads, and builds the row map on thread 0
      alone. None of the champion's MMID keeps reach that path.
    - Seeds S1–S4 target the N=1 decode the target measures:
      - S1 `akm-ds41-1017-mxfp4-mmid-flat-activation-quant`, a port of the champion's `4348de400`;
      - S2 `akm-ds41-1017-mxfp4-gemv-weight-prefetch`;
      - S3 `akm-ds41-1017-mxfp4-gemv-zmm-two-groups`;
      - S4 `akm-ds41-1017-mxfp4-gemv-vector-e8m0-scale`.
    - S5 `akm-ds41-1017-mxfp4-mmid-gemm-tiles` (premise: the repacked MXFP4 MMID prefill GEMM is slower than iqk Q4_K; the −29.9% pp512 once quoted
      for it, research `da71fa603`, is INVALID and unrecoverable, see DS41-W5) is record-only until the premise is tested by DS41-W5d (microbench at the
      pp512 shapes). This target (`-np 1`, no drafter, cached 45-token prompt) cannot see prefill.
    - Memory (276 GiB repack copy) is not an AK objective. The `capacity` dimension is only a guard.
- [x] **DS41-W9 — Re-check 2026-10-30: unsloth "Dynamic V3.1" 1017 GGUFs vs the served antirez MXFP4-experts build. Verdict: keep antirez; download nothing, delete nothing (intake-2511#record to intake-2521#record).** ✅ 2026-10-30 [belief: cc]
  - UD-Q4_K_XL is byte-identical (sha256) to the 2026-10-20 file this section already rejected; V3.1 re-quantized only UD-IQ1_M / UD-IQ1_S / UD-Q2_K_XL. Its routed experts are the same native MXFP4 as ours (40/40 layers); its dense path is lower precision (Q8_0 token_embd / compressor / indexer vs antirez F16); both Engram tables are lossless FP8 (MXFP8 type 43 vs I8 rows). Header-derived bytes/token: 0.979x of ours.
  - No EPYC tree loads any unsloth 1017 GGUF: v10 has no `deepseek41`; the DS41 port (`dd3d9721c`, champion `c72ec82f5`) reads only the antirez layout and rejects type 43. Upstream: #30817 (MXFP8 = 43) closed unmerged; #31086 (b11870) ships `deepseek41` with a single `per_layer_token_embd` BF16 table and `ple.*` keys; #27512 made type 43 = `GGML_TYPE_F8_E4M3`, so MXFP8-table unsloth quants (Q3_K_XL / Q4_K_XL / Q8_K_XL) load as gibberish on master (#31385).
  - Effort if ever wanted: Route A, the port reads the #31086/unsloth layout (ple keys, single-table row views, `engram_gate` as q_norm with k_norm = 1, `get_rows` for Q5_K/Q6_K/IQ4_NL tables, MXFP8 remapped to I8 with an interleaved gather), about 300-450 LOC in 6-9 files. Route B, an offline MXFP8-only converter (per-row byte shuffle, lossless), about 200-300 LOC gguf-py plus about 203 GB temporary disk.
  - AK carry-over for any weight change: dense Q8_0 keeps (`gemm4xn-2x-unroll`, `dense-q8-tb-prefetch`), `load-threads-48` and MXFP4 seeds S1-S5 apply to UD-Q4_K_XL; low-bit quants move experts to iqk IQ2/IQ3, generic Q3_K and stubbed IQ1 paths that no keep touches. The 2.862% floor binds the antirez artifact (split digest `ba9f129c`), so any new weights need their own 24-pair floor.
  - Local unsloth files `dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf` and `imatrix_unsloth.gguf_file` are sha256-identical to HF @ `8a6ec9cf`; keep, never re-download.
  - *Trigger (monitor, no task until it fires):* when the operator lifts the DS41 hold for serving or port work, add a prompt-prefix-reuse / checkpoint-restore conformance check to the port gates (controls `cache_prompt:false`, `-ctxcp 0`, two concurrent sequences). Upstream DS4.1 corrupts single tokens on reused prefixes (#30944, open; PR #31292 did not fix it); whether our port shares it is untested (intake-2517#record).
  - *Trigger (monitor):* if the operator reopens DS41 low-bit serving after AK kernel work, compare antirez's 1017 IQ2_XXS-Q2_K (loads as-is, 365.7 GB) against UD-Q2_K_XL / UD-IQ2_XXS / ISTA GSQ-RCO (all need Route A). The header bound is at most 19-24% fewer bytes per token; vendor KLD 0.138-0.203 vs 0.009 (intake-2511#record, intake-2512#record, intake-2518#record).

### T — Gates (translated from INF-69 T0-T4 / T0-SPEC / T15)

  - [ ] **DS41-W8a — give the DS41-1017 AK target a prefill surface.** The campaign target runs `-np 1`, no drafter, one cached 45-token prompt, so it cannot see prefill; seed S5 (`akm-ds41-1017-mxfp4-mmid-gemm-tiles`; premise: the repacked MXFP4 MMID prefill GEMM is slower than iqk Q4_K) stays record-only (*2026-10-23: the -29.9% pp512 once quoted for it is INVALID and unrecoverable, operator ruling, no Sept re-download, see DS41-W5/W5c; the premise is now tested by DS41-W5d, microbench at the 1017 pp512 shapes. Gate this item on the W5d verdict `PREMISE_STANDS` with an S5 ceiling above tolerance*) until the target adds `--keep-dimensions prefill_at_depth` with a `--longctx-surface` (or the W6 drafter's verify shapes). Needs its own floor (new recipe). (filed 2026-10-21 from the AK-seeding report) — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; FILLERS row `ds41-1017-w8a-longctx-floor` CANCELLED). Not done; reopen when AK kernel work has landed.
    - *(2026-10-21, note; W8a stays open.)* Traced on research `c036eaa40` (autokernel code = `c5997024e`).
      **W8a does not invalidate the 2026-10-22 decode floor.** The decode floor path is built only from the
      launch template, the anchor execution digest and the frozen decode requests (`run.py` 1113-1127, 1615-1636,
      3302-3311). `longctx.derive_launch` builds a SEPARATE recipe, `ds41-1017-cpu-t48-nospec-lc32k-2e0d3fb7`
      (hash `7959844b...`, `-c 35840`). That recipe has its own slot and its own 24-pair floor under
      `store/longctx/<target>/` (`longctx.py` 256-286, 669-784). `serial_run` classes both flags as keep policy
      (`serial_run.py` 331-361). A dry-run with both flags added differs from the armed one only by the two
      flags (same target revision, recipe `a22332136f30`, floor dir). **Gap:** `--serving-calibration-only`
      never calibrates the longctx surface, because `ensure_slot`/`ensure_floor` run only inside a keep A/B. So
      adding the flags to tomorrow's launcher would add nothing. Decision: (a) keep tomorrow's run as armed.
      Prepared:
      - spec `inputs/ds41-1017-longctx-32k.longctx.json` (digest `2e0d3fb7`; depth 32768, tail 2048,
        wikitext2, tokenizer round-trip checked);
      - args, dry-runs and a 16-line research patch `w8a-longctx-calibration-only.patch` that calibrates the
        surface in the calibration-only exit (test files pass), all in `/mnt/raid0/llm/tmp/ds41-1017-w8a-20261021/`;
      - FILLERS row `ds41-1017-w8a-longctx-floor` (block-timing-quiet, ~2.5-4.5 h, ready n).

      Next: land the patch on research main, then book the block after the decode floor exists.
  - [ ] **DS41-W8b — in-place / mmap-friendly MXFP4 CPU repack (non-AK engineering).** The repack copies all experts into ~276 GiB of anonymous RAM per server (INC-20261021-earlyoom-session-kills); `block_mxfp4` and `block_mxfp4x8` are both 17 B per 32 weights, so the repack only reorders bytes and could run in place. AK's `capacity` dimension is a pass/fail guard, so a memory-only win can never be kept by AK. First verify the RssFile figure with `smaps_rollup` (the target runs `--no-mmap`). Experimental branch only; a fold is a champion-owner decision. (filed 2026-10-21)
  - [x] **DS41-W8c — CPU_REPACK correctness gate; NO DS41 keep may land before it is live.** The served-shape layer (a) runs through test-backend-ops, which never runs the repacked `mxfp4_8x8_q8_0` expert kernel (its MXFP4 NMSE = 0.0 is vacuous), and seeds S1–S5 all change that path. Code: research branch `ak-ds41-repack-gate-20261021` @ `63d7b920e` (worktree `/mnt/raid0/llm/tmp/ak-repack-gate-20261021/research`, not yet on main): `autokernel/loop/cpu_repack_cases.py` + `cpu_repack_probe.cpp`, `gates.check_cpu_repack_case_set` (ppl_contract layer (a), the bundle, and every other DS41 CPU keep), new route `cpu_repack_gemv`. It fails closed without `<store>/cpu_repack/manifest.json`. Next: land the branch on research main, then run FILLERS row `ak-ds41-repack-gate` (block-correctness, one quarter): it compiles the probe, calibrates on anchor `06b169e27`, runs the broken-kernel fixture regression, and installs the manifest. Progress: `progress/2026-10/2026-10-21-ak-repack-gate.md`. (filed 2026-10-21, operator "act on this advice")
    ✅ 2026-10-22 — gate ran on q1 (09:57–10:01Z, research 42daa0ac9): calibrate 8 cases / 72 rows OK (max anchor NMSE 2.93e-5, max rel 0.052); anchor check PASS (repack engaged on every case); fixture regression PASS (both broken fixtures caught, engagement negative fired); 43 pytest pass. Manifest installed at `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-1017-cpu-decode-20261021/store/cpu_repack/manifest.json`. Run dir `/mnt/raid0/llm/tmp/ak-repack-gate-20261021/runner/results/`.
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
  - *(2026-10-21 note, wrap-up 3c4ca599-c; box stays open.)* The 1017 MXFP4 target-only baseline (A/A floor N=24 plus champion `dd3d9721c` vs candidate C `f0c96dc1f`, N=5; recipe `ds41-1017-mxfp4-cpu-t48-targetonly`) is built and ARMED, not run: launcher `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/chained_launch.sh` (PID 1676247, started 2026-10-21 10:33:58Z, still alive at 11:39Z) sleeps to the 2026-10-22 06:30Z slot, is gated on a fresh `SMOKE_OK`, and then runs under `region-lock run --cpu-list 0-95 --role bench --gpu-quiet exclusive`. It dies on host reboot and nothing re-arms it. The belief-kernel write side is `VB-DS41-1017-BASELINE-WIRE` in `vidya-belief-substrate-program.md`. The smoke test finished 12:37:35Z with `all_ok` true and champion and candidate token-identical (`SMOKE_OK` written), so the gate is open; no baseline result exists yet.
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
- [x] ~~DS41-D2 — Wire the belief kernel: add the `deepseek41` validation/serving producer row to~~ (closed 2026-10-29 audit: DUPLICATE → Same work tracked as VB-DSV41 in vidya-belief-substrate-program.md:1213 (canonical); adapters README row already filed (scripts/vidya/adapters/README.md:337))
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

2026-10-07 NI08 source preparation: DS41-C104-FUTURE-WRITER-SOURCE and its native companion are prospectively enrolled in the belief-source program. Research1880877 propagates only the already-authored decisive flag into future effect status; the actual Comparison predicate remains unchanged. All8 whole-module source controls and complete static closure must be frozen/reviewed before isolated hosted capture. Source is proposed, not accepted. DS41-C104 parent, historical14 kept-row reprojection and live owner boundary remain open.

- [x] **DS41-C104-FUTURE-WRITER-SOURCE — propagate the existing native decisive comparison flag into future effect claims.** Review exact Research188087701c963d57eb622ff8279081fae55f8049 two-file claims/test correction on currentc497 preimages: effect verified requires existing oracle+pairs plus decisive is literal True; actual Comparison/Outcome producer controls and missing/False/None/nonbool refusal preserve input records. Existing native comparison floor/calibration/drift predicate, keep disposition, mechanism/ablation statuses, schema and shared grade are unchanged. Source-only child of DS41-C104; historical14 keeps/reprojection/store changes and live owner reload remain separate. Native companion VB-DS41-C104-FUTURE-WRITER-CONFORMANCE; MAIN accepts only after exact prospective original review. ✅ 2026-10-07 — [MAIN exact source/original8 acceptance](../../artifacts/ni08/c104-decisive-source-acceptance-20261007/README.md); Research9299 publishes only the accepted two blobs. Parent/historical14/live-owner gates remain open.

2026-10-07 C106 source preparation: MAIN reviewed the existing task option to remove unused ROLLBACK, exact private sourceb223b53 and all16 AST controls. [Source/caller review](../../artifacts/ni08/c106-hold-source-preparation-20261007/README.md) confirms current default operator HOLD and no contrary selector consumer. Existing DS41-C106 remains unchecked until original synthetic conformance and exact product publication; no duplicate source child is added. VB-DS41-C106-HOLD-CONFORMANCE is enrolled before future hosted capture; no local project execution or owner runtime claim.


## Bounded C26 initial-floor cancellation source — 2026-10-07

- [x] **DS41-C26-CANCEL-SOURCE — poll stop at initial serving-floor legacy, matched and replacement launch boundaries and finish after owned child/claim cleanup.** Private Research0858dc64 changes four source/test files; consume only marked calibration ActorStopped, retain ExitStack cleanup before terminal full-run/stopped-continuation/complete-heartbeat finalization, publish no partial floor, and preserve unrelated errors/default floor/keep behavior. Whole20 startup parameters plus26 serving methods and their assertions are frozen for one original isolated native capture after MAIN review. The mixed DS41-C26 parent remains open for actual runtime evidence; this child warrants source conformance only. Companion VB-DS41-C26-CANCEL-CONFORMANCE uses the existing native CI family and unchanged shared grade. ✅ 2026-10-07

  Historical pre-reconciliation checkpoint: original0858/e69 remains native NULL (46 testcase nodes,17 failures, suite count49); private840bc1/26ab86 had no subsequent capture approval. The separately reviewed current-tip reconciliation and fresh original5933 capture below supersede that proposed next action without rewriting those originals.

  2026-10-07 MAIN accepted current source checkpoint: Research `e136226d00421742645bf2f157737a8cedf348f1` is public on main; original ROOT `5933d75d2d935edc2f3d542fd3240863548be8ab` push attempt passed all46 selected fixtures. Complete1588-path readset, seven stable inventories, five typed snapshots/6407 regular-file checks and existing shared Judged/Located grade are independently accepted. The original0858 NULL, aad7 FALSE and17f FALSE remain unchanged. This completes only the bounded source/control tasks; actual C26 runtime/floor/cadence evidence remains with its owner. [Accepted source and original custody](../../artifacts/ni08/c26-current-source-acceptance-20261007/README.md).

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **DS41-CED.1 — CED-aware prefill spike on the experimental DS41 port (intake-2117#record, intake-2116#record, intake-2125#record).** Behind a default-off flag in deepseek41.cpp, after layer 19 keep only a tail of prompt rows for decoder layers 20-39 while layer 20's KV-source path (compressor, index K, shared plane) still runs on every row: arm (a) EXACT tail = last 20x128+128 = 2688 rows (decoder SWA receptive field, YOCO-exact for the compressed plane), arm (b) vendor bounded replay = last KEEP in {134, 140} rows (approximate). Report per arm: last-row logit max-abs/KL vs full prefill (arm (a) must sit inside the f32 reduction-order floor measured by an A/A full-prefill pair; if not, the exactness premise is falsified and the non-tail-local decoder state is named), decode-continuation greedy identity for 128 tokens, and prefill t/s at 8K/32K/128K next to the layer-count bound 0.5*(1 - tail/N). Correctness first (build-role claim, region-lock 0-95), timing only in a CPU window; production v10 untouched; arm (b) never becomes a default without DS41-CED.2.
  - *(2026-10-23 15:12Z, f8.)* Deliberately NOT dispatched. Its consumer run KPF-28 (`kpf-28-ds41-ckpt`) is held by the operator's DS41-1017 ruling (2026-10-22: only the DS41 noise floor runs until the AK kernel work). The FILLERS blocker now names that hold. Re-open both when it lifts.
- [ ] **DS41-CED.2 — Quality gate for the approximate decoder bounded replay before any default (intake-2117#record, intake-2127#record, intake-2128#record).** Frozen prompt manifest with sha256; incumbent = full prefill on the same binary; arms = replay tail k in {134, 256, 512, 2688(exact)}. Measure: teacher-forced KL and top-1 agreement on the final 256 tokens and at cache-resume offsets; passkey/NIAH at 2K/8K/16K/32K; RULER variable tracing and multi-hop QA at the same lengths (stacked-SWA collapse case); short-context parity (HellaSwag/WinoGrande/ARC subsets) with paired-bootstrap CI; the coherence gate at production prompt length. Holdout = a second prompt manifest drawn after the k is chosen; count every invalid/timeout. Predeclared rule: the smallest k whose every long-context metric is within the full-prefill A/A noise floor becomes the candidate default; if none below 2688 passes, ship arm (a) only and record the negative.
- [ ] **DS41-W5.1 — Port fidelity vs the 1017 reference code deltas (intake-2121#record).** The 1017 inference/model.py quantize-dequantizes the attention output to FP8 (block 32, ue8m0) before wo_a in the main and DSpark attention (L787, L1073) and always publishes shared index_k (L548); our wo_a call site (deepseek41.cpp:1221 @ dd3d9721c) has no round trip. (1) read-only: confirm the index-key owner path matches L548 when no compression group completes; (2) per-op fixture: NMSE of the layer output with vs without the round trip; add a flag-gated emulation only if NMSE exceeds the Q8_0 activation noise. Correctness class (shard + build-role claim), no quiet host.
  - *(2026-10-21, part 1, static read; source `/mnt/raid0/llm/tmp/ds41-w51-20261021/REPORT.md`.)* For the
    1017 config, the index-key owner path matches reference L548. KV sources are layers 2/8/14/20, and
    index-source layers 24-36 all resolve to owner 20. The port stops walking back at a ratio change and the
    reference does not; this config cannot reach that case.
  - *(2026-10-21, part 2, same report.)* On a synthetic fixture, the FP8 e4m3/ue8m0/32 round trip before
    wo_a gives NMSE ~7e-4, against Q8_0 noise of 2.9e-5 to 1.25e-4 (6-25x). That exceeds the gate, so an
    emulation is recommended.
  - [ ] **DS41-W5.1a — flag-gated FP8 (e4m3, ue8m0, block 32) QDQ of the attention output before wo_a (main + DSpark, deepseek41.cpp ~1221), default off, then a real-model ppl/NMSE A/B on the 1017 build.** (derived 2026-10-21 from /mnt/raid0/llm/tmp/ds41-w51-20261021/REPORT.md) — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; FILLERS rows `ds41-qdq-build-test` and `ds41-w51a-ab` CANCELLED; the build-test launcher the operator armed 08:43Z was stopped at the operator's choice, killed and verified dead). Not done; reopen when AK kernel work has landed.
    - *(2026-10-21 note, workspace-58 subagent; code only, not built or run.)* Flag and op are on llama.cpp branch `experimental/ds41-qdq-flag-20261021` (from champion dd3d9721c; worktree `/mnt/raid0/llm/worktrees/llama-ds41-qdq-flag-20261021`, pushed to `fork`).
      `ac496d6f3` adds `src/llama-qdq.{h,cpp}`: `llama_build_qdq`, built on ggml_map_custom1 and CPU only. Its
      scale and rounding rules are copied bit for bit from kernel.py act_quant/fp4_quant (inplace). The same
      commit adds `tests/test-dsv41-qdq.cpp`, which checks against an independent enumerated-code oracle. `c17db6af9`
      wires `LLAMA_DSV41_QDQ=wo_a` before wo_a in the main attention (deepseek41.cpp) and the DSpark attention
      (dflash-dspark41.cpp). With the flag off, no node is added. Known residual delta: the reference input is bf16, ours is f32.
      Queued in FILLERS.md: `ds41-qdq-build-test` (build plus tests, not DS41-class), then `ds41-w51a-ab`
      (DS41-class). That runs three arms on the W5 ppl recipe: off, champion vs off (KLD must be 0), and wo_a
      (PPL plus KLD vs off). Scripts and results are in `/mnt/raid0/llm/tmp/ds41-qdq-20261021/`.
    - *(2026-10-22, note, workspace-58; scheduling only.)* W5.1a is now scheduled: evening chain v7 (`/mnt/raid0/llm/tmp/compute-flags/grant-chain-20261022-evening-v7.sh`, RAM-admitted) runs `ds41-qdq-build-test` and then `ds41-w51a-ab` first tonight. Both launchers were prepared on 10-21 but never armed; arming them needs the operator (the session permission classifier refused it).
  - [ ] **DS41-W5.1a-floor — post-CAS DS41-1017 AK floor.** FILLERS row `ds41-1017-ak-floor-postcas`, trigger: C2 CAS landed AND W5.1a decided. The morning 1017 floor is registered by f8 as decision-grade (pre-W5.1a epoch); this floor re-measures after W5.1a so AK keeps are compared in the right epoch. Owner: workspace-58. The 2.862% floor is valid only for `dd3d9721c` (pre-W5.1a epoch); this is the separate post-C2-CAS, post-W5.1a recalibration on the new anchor. (operator guarantee via f8, 2026-10-22) — **DEFERRED 2026-10-22 until the operator launches AK on a changed anchor** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; FILLERS row `ds41-1017-ak-floor-postcas` CANCELLED). Not done.
  - [x] **DS41-W8d — wire `ram_admit` into AutoKernel `run.py` server launches (after 7b's 14:30-18:00Z test; harness change).** Script: `/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh <peak_host_GiB> [ds41]` (root copy pending D9 ack); a DS41-1017 launch needs `739 ds41`. Today only the calendar grant writers and the W6.2 memgate call it, so an AK server start is unguarded. (filed 2026-10-22, workspace-58)
    ✅ 2026-10-23 (workspace-58 subagent; code + tests, nothing launched): research `ws58/ds41-w8d-20261023` @ `6c5ea618d`. New `loop/ram_admit.py` mirrors `ram_admit.sh` (MemAvailable − need ≥ 64 GiB; ds41 mode adds the assert_not_mapped walk of cmdline + maps for the 1017 shard 00001, own pid and ancestors skipped, read-only) until OP-RAMADMIT-D9 lands the tracked root `scripts/coordination/ram_admit.sh`. `guard_launch(argv)` runs before Popen at all four loop model-server starts: `serving._measure_once` (A/A floor, calibrate, compare, anchor/candidate, held-out), `model_identity.serve`, `capacity_probe.run` and `ab_server_pair.ServerPair.start`. DS41-class = a `-m/--model/-md` value whose basename starts with `DeepSeek-V4.1` (need 739 GiB). A refusal in `_measure_once` is a `ServerDied` instrument failure, never a candidate result. Argv, env and AK identity are unchanged. Tests: `test_ram_admit.py` 12 passed; serving/model_identity/keep_dimensions/shakedown/longctx/structural-route files pass. Two consequences: a paired DS41 `ServerPair` refuses its B arm while A is up (one DS41-class server host-wide, as the script intends), and a launch outside the loop still relies on the calendar writers' `ram_admit.sh`.
- [ ] **DS41-T3.2 — KV fake-quant attribution for reference parity (intake-2117#record, intake-2116#record).** The official reference round-trips window KV (FP8 ue8m0/32), main compressed KV (FP4 E2M1 + E4M3 per 16) and indexer K/Q (FP4 E8M0/32) before caching (model.py L546/L552/L707/L760/L1042); the port stores at the llama.cpp KV type with no QDQ. (1) On a layer-truncated fixture run the reference with its QDQ on and off to size its own sensitivity; (2) add an opt-in QDQ graph op on the experimental port; (3) re-run the DS41-T3 logit comparison with it on and label the claim kv_fakequant_matched. Never read a T3 divergence as a port defect before (1)-(3). Correctness class. — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; FILLERS row `ds41-t32-kvfq` CANCELLED). Not done; reopen when AK kernel work has landed.
  - *(2026-10-21 note, workspace-58 subagent; code only, not built or run.)* Step (2) is written: `ac496d6f3` (the op, modes
    FP8 e4m3 ue8m0/32, FP4 e2m1 ue8m0/32 and FP4 e2m1 + e4m3/16, with `test-dsv41-qdq`) and `156b3ea94` (the sites).
    The sites are opt-in through `LLAMA_DSV41_QDQ`: kv_win (main window KV, plus the DSpark ring and block KV), kv_comp, idx_k, idx_q, and the alias kv for all four. Each sits before the Hadamard K rotation; with the flag off, no node is added. Branch: llama.cpp branch `experimental/ds41-qdq-flag-20261021` (from champion dd3d9721c; worktree `/mnt/raid0/llm/worktrees/llama-ds41-qdq-flag-20261021`, pushed to `fork`).
    Step (1) fixture finding: **no layer-truncated reference fixture exists on this host.** Three things are missing:
    (a) The 1017 weights. None of its safetensors are on disk: `/mnt/raid0/llm/tmp/dive-deepinfer-1017/` holds code and
    `model.safetensors.index.json` only, and the three local Sept MTP shards (44-46) do not help. A fixture up to layer 3 (SWA,
    engram, first KV and index source) needs 1017 shards 00002 (embed), 00003-00006 (L0-L3), 00047 (L1 engram) and
    00043 (head and norm). The indexer-reuse layers 24-36 need most of the model. The alternative is to dequantize from the 1017
    GGUF; the claim is then `dequantized_from_quant`.
    (b) A tilelang-free CPU shim of inference/kernel.py. `lib/qdq_size.py` already notes it is absent;
    `llama_qdq_ref` is a C reference of the act-quant part only.
    (c) The DS41-T3 comparison harness itself (not written), plus a matching truncated port run.
    Step (3), port side, is queued as `ds41-t32-kvfq` (DS41-class, after the build). Arms: off, kv, kv_win, kv_comp and idx, each as KLD vs off at ctx 2048 (at 512 the indexer's top-512 selects every row). Label: kv_fakequant_port_sensitivity, not kv_fakequant_matched. Results: `/mnt/raid0/llm/tmp/ds41-qdq-20261021/t32-kvfq/`.
  - [ ] **DS41-T3.2a — build the reference side of the T3.2 step (1) fixture.** Missing (2026-10-21 tooling report): (i) 1017 reference weights for a layer-truncated fixture — HF safetensors shards 00002 (embed), 00003–00006 (layers 0–3), 00043 (head/norm), 00047 (layer-1 engram); or dequantize from the 1017 GGUF and label the claim `dequantized_from_quant`; the indexer-reuse layers 24–36 need most of the model; (ii) a CPU (no tilelang) port of `inference/kernel.py`; (iii) the DS41-T3 comparison harness + a matching truncated port run. Until then the port-side runner (`ds41-t32-kvfq`, QDQ branch `experimental/ds41-qdq-flag-20261021` @ `156b3ea94`) reports `kv_fakequant_port_sensitivity` only. (filed 2026-10-21)
- [ ] **DS41-B3.1 — Make the Engram gate exact at dot == +0.0 (intake-2124#record).** Replace ggml_sgn(dot) in the deepseek41.cpp engram gate with a +1-at-zero sign (copysign semantics of inference/model.py and the trained kernel); pure graph change, no new op. Done when a zero-key row's gate equals the reference value and decode logits are bit-identical elsewhere on the T1 smoke.
  - *(2026-10-20.)* Implemented as `sgn = 1 - 2*step(-dot)` on `experimental/intake-fixes-20261020` @ abcd831fb, queued for tests: exact at +0.0; at -0.0 it still yields +1 where torch copysign yields -1 — decide whether that case matters before closing.
  - *(2026-10-21.)* `test-dsv41-engram-gate` pass=14 fail=0 (graph-level, small tensors: exact at +0.0, bit-identical elsewhere) on `experimental/intake-fixes-20261020` @ 6b8291de5.
  - [x] **DS41-B3.1.1 — T1 smoke decode-logit bit-identity on the real model, and decide the −0.0 case** (it still yields +1 where torch copysign gives −1). ✅ 2026-10-21: bit-identical logits/tokens/top-10 on 4 prompts × 65 rows, research `48ee3b970`.
    - *(2026-10-21.)* The −0.0 case was decided: it does not matter. dot = sum·rstd·dim^-0.5 has positive scales, and RN summation from a +0 accumulator never yields −0.0, so the fix's +1 matches torch copysign. Only the T1 real-model smoke remains.
- [x] **DS41-B12.1 — Cite-and-close DS41-B12 (a)(b)(c) and anchor DS41-B11 from source (intake-2116#record).** Head collapse = last FFN sub-layer pre-mix (official model.py:1268; DeepInfer deepseek.py:229-232; ours deepseek41.cpp:1372); layer-20 compressor gate absent because the single-token softmax is 1 (model.py:461-462); ratio 1/2 non-overlapping APE-free geometry; RoPE per intake-2116#record. Tick DS41-B12 with these anchors; DS41-B11 stays open only for the top-k renorm epsilon (dormant trigger below). No compute. ✅ 2026-10-20 — B12 (a) head collapse, (b) layer-20 ungated compressor, (c) ratio 1/2 geometry all MATCH official model.py vs champion dd3d9721c deepseek41.cpp; evidence /mnt/raid0/llm/tmp/zero-inference-20261020/DS41-B12.1/REPORT.md.
- [ ] **DS41-T3.3 — Token-id parity of the DS41 serving path against two official renderers (intake-2118#record, intake-2121#record).** Oracles: the 1017 encoding/encoding.py (it differs from the September copy: tool-result-only user turns no longer start a turn) and deepseek-recipe @ 935817c. Render the 5 goldens plus tool, thinking, effort, mid-system and reasoning-retention cases (the second reader found the recipe drops reasoning for non-prefix assistant turns where encoding.py keeps it), tokenize with the DS41 GGUF vocab and diff against llama-server /apply-template + /tokenize as served; report the first divergence per case and which oracle disagrees. Host-side only, no inference.
  - [x] **DS41-T3.3 first run (job 60) — harness finding, not a parity result** ✅ 2026-10-20: 0/14 token-identical vs both encodings because neither DS41 GGUF (Sept Q4, 1017 shard 1) carries `tokenizer.chat_template` and llama.cpp has no V4/V4.1 built-in (`src/llama-chat.cpp` stops at deepseek3/deepseek-ocr), so the server rendered its ChatML fallback. Results `/mnt/raid0/llm/tmp/ds41-parity-20261021/ds41-t33-token-parity/`.
  - [ ] **DS41-T3.3b — template-arm token parity.** Authored `/mnt/raid0/llm/models/chat-templates/deepseek-v41-flash-epyc-v1.jinja` (sha256 4cab67bd5c8e…, targets the 1017 encoding.py 13231c59…99e2): 14/14 text-identical to both the Sept and 1017 encodings under a jinja2 proxy (tojson as llama.cpp renders it). Run CPU queue job `61-ds41-t33-template-parity.sh` (`--jinja --chat-template-file`); report per-case first token divergence for both oracles, check the add_special column for a double BOS, confirm the template loads in llama.cpp's jinja runtime and passes the object-arguments capability probe; then decide whether the template goes into the DS41 launch recipe. Known deliberate divergence: tools with no system message (encoding.py drops them; the template synthesises a system message).
    - [x] **DS41-T3.3b job 61 run (template arm)** ✅ 2026-10-21: the template loads and renders in llama.cpp's jinja runtime (served text is DeepSeek-format, not the ChatML fallback; evidence is behavioural — the template-load grep matched nothing). 0/14 token-identical at add_special=false because the template emits no BOS (add_special adds exactly one; no double BOS); with BOS added 6/14 identical (thinking, effort high/max/int75, reasoning-retention prefix/non-prefix); golden1 diverges at id 586/622, golden2–4 and the tool cases at id 6, mid_system at id 3, golden5 HTTP 500 (image, no mmproj). The jinja2 proxy's 14/14 text identity did not transfer to the real runtime. Results `/mnt/raid0/llm/tmp/ds41-parity-20261021/ds41-t33-template-parity/`.
    - [ ] **DS41-T3.3c — close the T3.3b divergences.** (1) Chat-mode cases are served with a `Reasoning Effort` preamble, i.e. thinking is on when the request sends no `chat_template_kwargs`: send `enable_thinking:false` for chat cases and decide the launch-recipe default; (2) save the served prompt text per case in `t33.py`; (3) locate golden1's divergence at id 586/622 (likely final-turn reasoning retention or tool_result); (4) add the object-arguments capability probe and send tool-call arguments as the server delivers them; (5) skip or mmproj-load golden5; (6) decide BOS (template emits it vs server add_special) so add_special=false and true agree; (7) rerun on the 1017 GGUF WITH `--jinja --chat-template-file`. — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; queue launcher `ds41-t33c` killed, verified dead). Not done; reopen when AK kernel work has landed.
      - Note 2026-10-21 (operator ruling, via workspace-5c): Sept-GGUF arm moot; one job on 1017 (job 65-ds41-t33c-1017, released) compares against both oracle encodings (Sept and 1017 encoding.py, text specs). Header check: arch deepseek41, 9 shards, binary libggml-cpu has mxfp4_8x8.
      - *(2026-10-21 note)* Harness fixed in `lib/t33.py` v2: explicit `enable_thinking` per case, served prompt saved, object-arguments probe, golden5 = SKIP(no mmproj) kept in the denominator, add_special false/true both reported (BOS undecided); template v1 confirmed chat-by-default when `enable_thinking` is false (no v2 needed). Jobs `62-ds41-t33c-sept` / `-1017` queued (first attempts killed rc=125 by the pairguard, requeued). Still open: (3) golden1 divergence location and (6) BOS decision, from the rerun.
      - *(2026-10-21, workspace-58 queue prep, no inference run; offline analysis of `ds41-t33c-1017b`)* Findings: **(6) BOS decided** = `add_special=true`: the template emits no BOS, the server adds it; 9/13 evaluated cases are token-identical with it, 0/13 without. **(3) golden1 localized**: the residual divergence of golden1 (id 586/622) and golden2/3/4 is in the FINAL assistant turn only (<= 165 chars from the end): golden1 served `<think><think>` where encoding.py has one; golden2/3 re-render the final assistant reasoning as `<think>..</think>` in chat mode where encoding.py drops it; golden4 loses the `<｜action｜>` task marker (the `task` field does not reach the template). **(4) arguments probe still UNDETERMINED** in v2 (the call was the last message; both forms rendered neither form). (1), (2), (5), (7) done earlier. What still needs running: ONE rerun, `t33.py` v3 (round-trip probe + reasoning_content/task variants for golden1-4; ~0.5 h, one load, no generation); the residual divergences themselves need a template/server fix first (not made here), then a second rerun to close. Analysis `t33c/analyze_t33c.py`, result `/mnt/raid0/llm/tmp/ds41-queue-20261021/t33c_offline_analysis.json`; research `2a40ce4b4`, `artifacts/ds41_queue_20261021/` and `artifacts/ds41_w6_dspark_1017_20261021/w6.1c/`; queue row in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (launcher armed, idles until a grant; DS41-class, refuses via ps scan if another DS41 server is live), id `ds41-t33c`.
    - [x] **DS41-T3.3 1017 shard rerun (job 60-ds41-t33-token-parity-1017)** ✅ 2026-10-21: ran without the template; 0/14 vs both encodings with the ChatML fallback — the same artefact as the Sept run, not a parity result. Results `/mnt/raid0/llm/tmp/ds41-parity-20261021/ds41-t33-token-parity-1017/`.
  - [ ] **DS41-T3a note — Sept vs 1017 encoding differ** in `find_last_user_index` under thinking mode: Sept counts a tool-result-only user turn as the last user turn (dropping the earlier assistant reasoning), 1017 does not. The cutover checkpoint must be served with the 1017 rule; add a T3.3 case for a trailing tool-result-only turn in thinking mode.
- [ ] **DS41-T4.1 — Golden-forced exactness driver for DS41-T4/T5 (intake-2116#record).** Force one fixed token sequence (>=8 prompts, 2 context lengths) through the DS41 server once batched-with-DSpark and once single-plain, diff (token id, logprob, top-5) per row at zero tolerance and report the first diverging row with its top-1/top-2 margin; reuse the LLAMA_SPEC_EXACT modes. Observation grade until the unit and noise floor are named.
  - *(2026-10-21, job 60-ds41-t41-golden-exactness, sept-q4, n=1 per cell.)* The zero-tolerance diff's "16/16 diverge" is dominated by missing logprobs: the speculative serial path returned no logprob/top-5 for 491/512 rows (ids identical). At token-id level, serial is 16/16 identical to plain; batched 11/16 (first id divergences ctx512 p6 row 10, p7 row 22; ctx2048 p0 row 14, p1 row 29, p4 row 13). Results `/mnt/raid0/llm/tmp/ds41-parity-20261021/ds41-t41-golden-exactness/`.
  - [ ] **DS41-T4.1.1 — obtain logprobs/top-5 on the speculative serial path** (the server returns none for accepted tokens), then rerun the logprob/top-5 diff; until then only the token-id result stands.
    - Note 2026-10-21 (operator ruling, via workspace-5c): retargeted to 1017 MXFP4: job 66-ds41-t41b-1017 (held). Plain arm unconditional; dspark_batched/dspark_serial gated on /mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash-1017-DSpark.gguf (DS41-W6 conversion) plus marker DSPARK_1017_OK, else recorded SKIPPED(drafter-not-ready). The Sept DSpark drafter matches Sept Q4 only. Also recheck anything assuming 16 KiB direct-IO alignment: 1017 has general.alignment=32.
  - [ ] **DS41-T4.1.2 — capture per-step top-n_probs in the serial verify loop** (read logits at `tok_idx` right after `common_sampler_sample`, before the next `llama_decode`; feed `result.probs`/`prob` in the accept loop instead of `verify_idxs[i]`); then rerun the logprob/top-5 diff.
    - *(2026-10-21 note)* Cause: `server-context.cpp` `sample_and_accept_dspark_serial()` leaves n_probs empty (`TODO(TD-1d.2)`). `lib/t41.py` v2 compares ids only where probs are unavailable and reports logprob/top-5 NOT AVAILABLE/PARTIAL; old rows recomputed: serial vs plain 0/16 token-id divergence, only 21/512 rows had comparable probs. Job `63-ds41-t41b` queued (parked until the window allows). Server-side fix: DS41-T4.1.2.
    - *(2026-10-21 note, workspace-58)* Code + test committed: llama `experimental/ds41-t412-serial-verify-nprobs-20261021` @ `02c139f11` (from champion `dd3d9721c`). `sample_and_accept_dspark_serial()` captures prob/top-n_probs per sampled row via `populate_token_probs()` (pre- and post-sampling) before the next `llama_decode`; the accept loop uses those for serial rounds. Test `test_n_probs_serial_verify_matches_plain[pre|post]` (stories15M MoE + q4_0 draft, `LLAMA_SPEC_EXACT=serial`, temp 0) requires per-row id, prob and top-n to equal the no-draft run. NOT yet built or run (quiet block): CPU build + tests via `/mnt/raid0/llm/tmp/ds41-t412-20261021/run.sh <cpus>` under `region-lock run --role build --tag ds41-t412`, then the DS41 logprob/top-5 rerun (job 66 retarget) on this branch or a champion that folds it.
- [ ] **DS41-T5.1 — n-invariance audit of the DS41 verify path (intake-2116#record).** For each op class on verify rows (MoE gemv/gemm, attention, compressor, indexer) measure the bit difference of row r computed inside an n-row batch (n = 1, 2, 4, 6) vs alone on CPU; output a ranked list of ops whose accumulation order depends on n (the list, not a fix). Cross-reference intake-2037/2039 for the GPU side. Correctness class.
  - *(2026-10-21, jobs 60-ds41-t51-ninv-q4 / -1017.)* Only the first differing op is informative: dense matmul `qr-0` is n-variant at n=2 row 0 in both eras (n=1 control 0/3395 differ, as required). ~99% of downstream nodes differ by propagation, so the per-op ranking and `max_rel_diff` (1e30–1e32, a +1e-30-denominator artefact) are not an n-invariance list. Results `/mnt/raid0/llm/tmp/ds41-parity-20261021/ds41-t51-ninv-{q4,1017}/`.
  - [ ] **DS41-T5.1.1 — fix the n-invariance harness**: compare each node with its inputs substituted from the single-row reference (or stop each op class at its first differing node with matching inputs) so MoE gemv, attention, compressor and indexer are attributed per op; rerun both eras. — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; f8 cancelled job 67 (`67-ds41-t51b-1017`, 10:45-14:15Z)). Not done; reopen when AK kernel work has landed.
    - Note 2026-10-21 (operator ruling, via workspace-5c): retargeted to the 1017 MXFP4 GGUF only (Sept Q4 being deleted): queue job 67-ds41-t51b-1017 (released). MXFP4 experts take the AVX2 mxfp4_8x8_q8_0 path, not iqk Q4_K, so the audit sees different expert kernels and is not node-comparable with the Sept ds41-t51 evidence.
    - *(2026-10-21 note)* Harness v2 (`lib/ds41_ninv.cpp`, marker `ninv_v2_inputs_matched`): a node is n-variant only if its output row differs and every comparable input is bit-identical to the single-row reference (strict); incomparable inputs = cand, differing inputs = prop (not attributed); rel diff floored, max_abs reported. Not yet rebuilt; job `64-ds41-t51b` builds it and runs Q4 (+1017 when verified), parked until the window allows.
- [ ] **DS41-W6.1 — DSpark alpha and block-2/3 speedup at the card sampling (temperature 1.0, top_p 1.0) on the 1017 weights, beside the W6 temperature-0.7 and greedy arms (intake-2121#record).** State the sampling triple in every claim tuple; same frozen prompt manifest and binary for all arms; >=5 interleaved pairs; count every invalid run. — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; queue launcher `ds41-w61` killed, verified dead). Not done; reopen when AK kernel work has landed.
  - *(2026-10-21, workspace-58 queue prep, no inference run)* Card-sampling arm added in `w6.1c/`: T=1.0 top_p=1.0 sent with top_k=0 min_p=0 repeat_penalty=1 explicit (server defaults are top_k=40, min_p=0.05), sampling triple on every row and in `sampling.json` with the server `/props` read-back. Arms are strictly sequential (one DS41 server): pair = plain target-only arm + dspark arm, ABBA, same cpus/-t; T=0.7 reference arm in the same pair; greedy identity in pair 1; every invalid row counted; 5 pairs. Speedup = dspark tok/s / plain tok/s (indicative host, no baseline claim). research `2a40ce4b4`, `artifacts/ds41_queue_20261021/` and `artifacts/ds41_w6_dspark_1017_20261021/w6.1c/`; queue row in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (launcher armed, idles until a grant; DS41-class, refuses via ps scan if another DS41 server is live), id `ds41-w61`.
- [ ] **DS41-W7.1 — Record the vendor sampling contract in the DS41 recipe at cutover (intake-2121#record).** In deepseek_v41_flash_recipe.py add temperature 1.0 / top_p 1.0 (1017 card) as RECOMMENDED_SAMPLING with the citation, and make every DS41 quality or A/B harness send it explicitly or record the deviation; lands with DS41-W7, not before the shards are complete.
- [ ] **DS41-C123.1 — Gather-form final attention for decode (intake-2116#record, intake-2122#record).** Replace the concat(raw window, whole compressed plane) + top-k -inf mask (deepseek41.cpp:1091-1097 @ dd3d9721c) on decode and verify widths 1-3 by get_rows(top-512 compressed rows) ++ window rows and flash attention over ~640 rows, using the indexed-op interface fixed in DSA-IDX.1; prefill keeps the mask path. Gate: with identical top-k sets, gather (ggml FA) vs mask (ggml FA) is bitwise identical under the DS41-T2 cap probe, and gather (iqk) vs gather (ggml) is tolerance-class (bit-identity holds only with the same kernel and row order; intake-2506); then a timed A/B at 32K/64K/128K in a CPU window (frozen manifest, champion baseline, 5 interleaved pairs, predeclared keep at >= the window noise floor). Kernel work is authored model-agnostically and folded into the champion.
  - [ ] **DS41-C123.1a — CPU kernel template and port hazards for the gathered decode attention (intake-2506, intake-2507).** Template: ik #2165's T=1 indexed branch (heads split over threads, one shared gather, one sink per head at normalisation; `iqk_flash_attn.cpp` L193-L240 @ 7945404) WITH #2511's sinks + first offset and #2287's K==V reuse (ik master c12b5ac L165-L216). Port #2165's sink_stride change with it (`iqk_flash_impl.h`, `iqk_fa_templates.h` normalize_and_store_1row, every `iqk_fa_*.cpp`), because the port reads one sink per call (port `iqk_fa_templates.h` L1129 @ 9a338d4f1). Close three port hazards: (a) bound the mask-to-index writes in release builds (ik relies on an assert); (b) reuse K as V only when row_size_k == row_size_v (#2287 compares pointers only); (c) index-from-mask assumes a binary mask (selected = mask == 0), so take the indices from the top-k set through the DSA-IDX.1 int32-index contract, not from an additive mask. Verify widths 2-3: ik's per-row N > 1 branch keeps only N threads busy (`iqk_flash_attn.cpp` L242-L253 @ 7945404); use a (row x head) split. Sinks tests follow the AKX-ALL-10.1 rule. Implementation and correctness now; the timed A/B waits with the other DS41 tests until AutoKernel kernel work lands (operator, 2026-10-22).
- [ ] **DS41-C7.2 — Break out GGML_OP_TOP_K and the indexer from the DS41-C8 node profile (intake-2120#record, intake-2130#record).** At ctx 8K/32K/128K report the decode-step share of top-k (8 index-source layers + the 2048-block candidate stage), its thread occupancy at nrows = 1 (the CPU top-k is std::partial_sort, one row per thread), and the lid_kq node count (must be 8: reuse layers must not recompute the indexer). Decides whether a single-pass threshold-filter top-k (DeepSelect pattern) is worth an AutoKernel op lane. — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; queue launcher `ds41-c72` killed, verified dead). Not done; reopen when AK kernel work has landed.
  - *(2026-10-21, workspace-58 queue prep, no inference run)* Instrument = the DS41-C8 `build-cpu-prof` sibling (not the champion build, which has no `GGML_CPU_PROF`; shares transfer, absolutes do not). `c72/run_c72.sh` runs one profiled 1017 target-only server per ctx (8K/32K/128K) with an exact-N-token id prompt so `GGML_CPU_PROF_SKIP` is exact, 64 decode steps; `group_nodes.py` groups TOP_K (index-source `lid_top_k` vs candidate stage), `lid_*` indexer nodes and counts `lid_kq` (gate == 8), with per-thread effective-thread occupancy. research `2a40ce4b4`, `artifacts/ds41_queue_20261021/` and `artifacts/ds41_w6_dspark_1017_20261021/w6.1c/`; queue row in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (launcher armed, idles until a grant; DS41-class, refuses via ps scan if another DS41 server is live), id `ds41-c72`. The 128K ctx needs a >= 2 h window and resumes across grants.
- [ ] **DS41-KV.1 — Compressed-plane KV type A/B on the DS41 port (intake-2116#record, intake-2122#record).** q8_0 first, then an NVFP4-layout plane (ggml NVFP4 is 288 B per 512-dim token with the same ue4m3-per-16 scale rule as the vendor FP4 KV; block interleave differs). Measure NMSE and ppl vs f16 KV at 8K and 32K, then decode/prefill t/s in a CPU window; stop the NVFP4 arm if NMSE is worse than q4_0; report the minimal patch if NVFP4 is not a selectable KV type. Frozen manifest, champion baseline, interleaved pairs, predeclared keep rule.
- [ ] **DS41-CONF.1 — DSpark confidence-head reliability probe (intake-2116#record, intake-2116#record).** On the experimental branch log, per draft position, the head value, the cumulative product and whether the position was accepted (read the head with a negligible p_min so nothing is truncated), over >= 500 verify rounds of real DS41 traffic at the recipe block width; report AUC of confidence vs acceptance, of the cumulative product, of position index alone, and a 10-bin reliability table per position, plus DeepInfer's batch calibration error. Holdout = a later traffic window. Rule: cumulative-confidence AUC >= position-only AUC + 0.05 opens the cost-aware truncation (dormant trigger below); otherwise record the decline. No timing claim. — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; queue launcher `ds41-conf1` killed, verified dead). Not done; reopen when AK kernel work has landed.
  - *(2026-10-21, workspace-58 queue prep, no inference run)* Logging patch: llama.cpp branch `experimental/ds41-conf1-logging-20261021` @ `b428d7392` (from champion `dd3d9721c`, worktree `/mnt/raid0/llm/worktrees/ds41-conf1-20261021`). Env `LLAMA_DSPARK_CONF_LOG=<jsonl>` (default off, one JSON line per verify round: conf, cum, accepted, evaluated) and `LLAMA_DSPARK_CONF_PMIN_LOG` (default 0 = nothing truncated). **Authored WITHOUT a compile proof** (region-lock q0 was held): the queue driver builds it inside its first grant and proves the knob with `strings` before any run. Analysis: `conf_reliability.py` (AUC conf/cum/position, 10-bin reliability per position, ECE approximation of DeepInfer's batch calibration error, 0.05 rule, holdout). Driver runs main then a separate holdout server with disjoint prompts; each needs >= 500 rounds. research `2a40ce4b4`, `artifacts/ds41_queue_20261021/` and `artifacts/ds41_w6_dspark_1017_20261021/w6.1c/`; queue row in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md` (launcher armed, idles until a grant; DS41-class, refuses via ps scan if another DS41 server is live), id `ds41-conf1`.
- [ ] **DS41-T7.1 — Price the DSpark drafter on the MI210 from existing logs (intake-2116#record).** From existing llama-server timing logs extract draft ms per step and its share of the DS41 step at block 2; if the share is >= 5%, scope a drafter-only HIP placement (whole 128-expert drafter resident, ~7-9 GiB) with proven residency; otherwise close. Zero inference for the pricing step.
  - *(2026-10-20, workspace-f8.)* NOT JUDGEABLE at the 5% threshold: drafter graph (410 nodes) seen 382x but accumulated 0 in the CPU probes, so its own ms/step was never logged; residual upper bound only (non-verify share 6.7-9.1%, median ~8.7%, CPU drafter, n_max 2), no lower bound; box stays open; evidence /mnt/raid0/llm/tmp/zero-inference-20261020/DS41-T7.1/REPORT.md.
  - *(2026-10-24, f8 sweep.)* Re-checked for a pricing source that would let this close from logs: no log anywhere under `/mnt/raid0/llm/tmp`, the orchestrator logs or the research artifacts/benchmarks carries `draft timing draft-dspark` (the INFO line from `206f9ef34`) or `t_draft_us`, so no DS41 run on the timing patch has happened. The pricing step still needs DS41-T7.1a (one profiled decode run, model load), which is on the operator's 2026-10-22 hold (DS41 tests other than the noise floor wait until AutoKernel kernel work lands). Not a log task any more: reopen with T7.1a.
- [ ] **DS41-T7.1a — one profiled DS41 decode run that accumulates the DSpark drafter graph time** (or prints t_draft_us), prerequisite of DS41-T7.1. (derived 2026-10-20 from /mnt/raid0/llm/tmp/zero-inference-20261020/DS41-T7.1/REPORT.md) — **DEFERRED 2026-10-22, run cancelled** (operator 2026-10-22 08:4xZ: DS41-1017 tests other than the noise floor wait until AutoKernel kernel work is done; FILLERS row `ds41-t71a-drafter-timing` CANCELLED). Not done; reopen when AK kernel work has landed.
  - *(2026-10-21 note, workspace-58 subagent; code only, not built or run.)* Why T7.1 saw 0: the CPU profiler accumulates
    one graph shape (the NNODES filter picked the verify graph), and the server's own `t_draft_us` (`dur(b,g,a)`) is
    printed only at TRACE. `process()` was also untimed, and that is where the DSpark encoder and the KV inject decode
    run on every verify step. Commit `206f9ef34` on llama.cpp branch `experimental/ds41-qdq-flag-20261021` (from champion dd3d9721c; worktree `/mnt/raid0/llm/worktrees/llama-ds41-qdq-flag-20261021`, pushed to `fork`) times `process()`. It also prints at INFO, per slot release:
    `draft timing draft-dspark: draft = X ms / N calls, process = Y ms / M calls, ...`. It is default on because it is zero-cost (two clock reads per call); numerics are unchanged.
    Queued as `ds41-t71a-drafter-timing` (DS41-class, after the build): the W6.2 server recipe at n_max 2 with 9 greedy requests. `/mnt/raid0/llm/tmp/ds41-qdq-20261021/t71a_parse.py` turns each request's figures into drafter ms per step and a share of eval time, which T7.1 compares with its 5% threshold.

**Dormant triggers (no checkbox, no index next action; materialize a task only when the trigger is observed). 'An' in a row means that intake entry's own dive-ledger row n:**

- DI-005 (intake-2117): monitor: re-open if KPF/KVU prefix-store memory for DS41 sessions exceeds ~10% of host RAM or checkpoint save/restore time shows up in the TTFT budget; the encoder-variant replay (last 128 tokens, global KV untouched) would then be the drop-in fallback, gated by A2.
- DI-006 (intake-2117): monitor: when the DS41 DSpark gate tuning reopens block size beyond 2 or concurrency>1, measure the verify-cost curve first and implement the survival-times-curve policy per intake-738/2607.05147; no task now because this report adds no numbers.
- DI-012 (intake-2118): monitor: when DS41 gets an orchestrator registry role (DS41-W swap lands), check that the role config sets max_tokens against the served -c value; no task before then.
- DI-021 (intake-2120): monitor: A1 result shows GGML_OP_TOP_K above the AutoKernel noise floor of the step, then open an AutoKernel op lane (AKX-ALL) for it; draft line: **AKX-ALL-<next> — GGML_OP_TOP_K CPU single-pass threshold-filter kernel, parity with partial_sort set semantics** @ handoffs/active/autokernel-all-devices-all-dimensions.md
- DI-022 (intake-2120): monitor: a DSA/DS41 model is scheduled onto MI210 with ncols>1024 per row (op unsupported -> CPU fallback or full argsort)
- DI-034 (intake-2122): monitor: DS41 weight swap to the 1017 finetune changes projection quantization, or MI210/CPU FP8 emulation shows attention small-op overhead in the DS41-C8 profile
- DI-042 (intake-2124): monitor: a DS41 or other MXFP4 requantisation step is planned with llama-quantize (then compare NMSE of ceil-pow2 vs floor scale recipes on the same tensor before choosing)
- DI-056 (intake-2116#record): monitor: cost-aware cumulative-confidence truncation for draft-dspark is worth building only if the confidence head is informative; trigger = the DS41 confidence reliability probe passes its predeclared AUC rule. Then: measure verify time per width k = 1..5 at the serving np from server timings (not llama-bench), fit a + b*k, threshold the cumulative confidence at rate*b with an online slope correction, A/B vs the best static block width and n-max 3, >= 5 interleaved pairs, greedy identity 100%, keep at >= +1.0% above the window floor. Vendor evidence is an estimate on EP64 GPUs with a -1.5% sign flip at low concurrency, so no gain is presumed.
- DI-074 (intake-2116#record): monitor: DS41-T3 per-layer parity harness - trigger: any token-layer whose selected-score sum < 6.2e-5, or any route-weight mismatch > 1e-6 against official model.py; then add a deepseek41-gated '+1e-20' path
- DI-076 (intake-2116#record): monitor: DS41-C123 depth profile - trigger: lid_kq + lid_top_k on layers 24-36 exceed 3% of the decode step at >= 64k context; then open it as a sub-item of DS41-C123.1
- DI-077 (intake-2116#record): monitor: Engram row pre-touch at set_input (madvise WILLNEED on the 48 row ranges, one helper pass for all engram layers with a per-layer completion flag, never in the compute pool; never --mlock/--no-mmap/--direct-io) is only worth it if page faults cost something; trigger = the existing Engram cold/warm per-step measurement (the B7c harness) shows a per-step delta above its measured noise floor. Also reword the B8 note to 'no cross-step prefetch; intra-step overlap available' when that task is next edited.
- DI-087 (intake-2116#record): monitor: open a task only after DS41-T3.2 shows the reference KV roundtrip changes logits materially (else the cheaper q8_0/bf16 KV is not 'wrong', merely different) and DS41 KV bytes/token becomes the binding capacity limit at the target context; trigger = DS41-T3.2 result + a long-context KV footprint figure from the C6/T8 runs
- DI-101 (intake-2129): monitor: exact candidate restriction of the four candidate-consumer indexer layers (24/28/32/36) to the 2048x8 candidate rows; the HISA dive sized it at roughly 218 to 101 MB per token at 128K against ~3.6 GiB per token for the dense concat path, so the concat path comes first. Trigger: after the gather-form final attention lands, the depth profile shows the indexer logits plus top-k on those layers above 3% of the decode step at >= 64K; then gate on identical top-512 sets and greedy identity, decide by a timed A/B at 64K and 128K.
- DI-102 (intake-2129): monitor: a measured profile at >=64K shows the unrestricted source/ratio-2 index scan (layers 2/8/14/20) above 5% of decode time after C123 and A2 land
- DI-113 (intake-2133): monitor: DS41 expert tensors (or any MXFP4-quantized MoE weights) are placed on the MI210 as part of a hybrid CPU/GPU offload; at that point, prototype a 16-entry-LUT MXFP4->FP16 register dequant feeding MFMA and compare against a bandwidth-roofline estimate from mi210-q8-dequant-gemv-roofline.md before committing kernel-authoring effort (agentic-rocm-kernel-authoring.md owns the authoring process)
- DI-119 (intake-2135): monitor: folded into the Engram pre-touch trigger (same trigger, adds the vendor shape: one fetch issue for all engram layers at forward start with a per-layer completion point).
- DI-120 (intake-2135): monitor: price a batched engram-row H2D (tokens x 24 x 264 B per layer) vs mapped-host reads only if the DS41 hybrid placement work places an engram layer on the MI210; until then the CPU-resident engram needs none of it.
- DI-141 (intake-2140): monitor: DS41-T7 decision places an engram layer or hot-expert set on MI210; then fold the gather kernel into the T7 microbench @ handoffs/active/deepseek-v41-flash-evaluation.md

**Retained knowledge (no task):**

- DI-004 (intake-2117): knowledge-only: retained for (a) A3 parity work and (b) any future KV-format candidate list in tq3-quantization-evaluation.md; revisit only if a measured KV-capacity or KV-bandwidth bottleneck appears on a lane (e.g. MI210 np4 unified-KV residency); not an unmeasured CPU/MI210 "no" - the paper just provides no quality number for a non-QAT model.
- DI-007 (intake-2117): knowledge-only: confirmation that the port matches the report on layer map (claim 0); keep for DS41-T3 reference-parity context.
- DI-013 (intake-2118): knowledge-only: retained as the reference for what a token-aware parser needs; our DS41 tool path is gated by DS41-T3a/T4 first.
- DI-024 (intake-2120): knowledge-only: input spec for A2 (fold the end-bound into A2 if built)
- DI-029 (intake-2121#record): knowledge-only: retained to bound citation of the 1017 table (vendor-reported, unreplicated).
- DI-031 (intake-2122): knowledge-only: retained use = byte-layout equivalence note and the 3% arithmetic when anyone proposes an FP8 KV type
- DI-033 (intake-2122): knowledge-only: seed to AutoKernel planner as an idea for the FA op; read docs/20260930-ascend-prefill-deep-dive.md algorithm recap L60-L75 before any build
- DI-038 (intake-2123): knowledge-only: retained as an independent statement of indexer-logit semantics for DS41-B5 review; the official inference/model.py remains the first-party oracle
- DI-041 (intake-2124): knowledge-only: DS41-B4 parity uses the first-party inference/kernel.py hc_split_sinkhorn as the oracle; TileKernels refs are a corroborating second statement, no task
- DI-043 (intake-2124): knowledge-only: AMD status settled (no HIP path in TileKernels; TileLang HIP covered by intake-2029); revisit only if a DS41 op moves onto the MI210
- DI-082 (intake-2116#record): knowledge-only: retained as the reason a dense-4-bit DS41 variant must be treated as EPYC-original and unproven; cite intake-2116#record in any plan that proposes it
- DI-083 (intake-2116#record): knowledge-only: supports choosing full-resident over disk streaming for DS41-B9 (still measure page-fault cost per decode step as B9 already requires)
- DI-085 (intake-2116#record): knowledge-only: do not cite offline_decode_ppl.json values as a parity reference; reuse only the prompt pair as a T1/T3 smoke input; true T3 reference stays the official inference/ per-op / layer-truncated comparison (handoffs/active/deepseek-v41-flash-evaluation.md:L1403)
- DI-095 (intake-2127): knowledge-only: folded into the DS41-CED.1 spike as an optional diagnostic; becomes a task only if replay-length sweep shows a quality cliff between 128 and 512.
- DI-100 (intake-2129): knowledge-only: sizing result that orders the work - fix the DS41-C123 concat/mask path first, then restrict candidate-consumer layers; fold into the C123 measurement rather than a new task
- DI-103 (intake-2130): knowledge-only: independent evidence for why V4.1 reuses indices (per-layer top-k cost) and why quality is trained-in, so any attempt to share indices in a non-V4.1 model must be re-validated
- DI-121 (intake-2135): knowledge-only: sizing formula to apply to B9b once B7c has a per-row cold fault latency; DeepEP constants are not transferable
