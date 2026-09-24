# DeepSeek-V4.1-Flash Evaluation (deepseek41)

**Status**: active — artifact download in progress (started 2026-09-22 09:51, about 13 h at
~11 MB/s); official reference implementation and harness fetched. No port, build or inference yet.
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

## Tasks

### A — Acquisition and reference

- [x] DS41-A0 — Start the antirez Q4 download (two raw parts). ✅ 2026-09-22 09:51
- [x] DS41-A1 — Fetch the official non-weight files (reference `inference/`, `encoding/`,
  `evaluation/`, tech report, config, tokenizer) and clone `deepseek-ai/deepseek-harness`
  @ `c36a83ff6b`. ✅ 2026-09-22
- [x] DS41-A2 — Join and verify the download. **DONE 2026-09-23**: both parts match their published SHA-256 (`6442b1f9…`, `7c3e1064…`) and exact sizes; joined to 518,596,067,328 B; header parses — GGUF v3, **1046 tensors**, `general.architecture=deepseek41`, alignment 16384, `engram.rows=[384006168, 384016682]`, `encoding=e4m3_e8m0_32_row264`, last tensor `blk.14.engram_embd.weight` ending 3,248 pad bytes before EOF, and **zero `mtp.*`** as expected. `part2` is retained for now (39 GB, deletable). ✅ 2026-09-23 — original text: **The parts MUST be joined**: `blk.14.engram_embd`
  is the last tensor and straddles the boundary (starts at 417,215,660,032; part1 ends at
  480,000,000,000). Expect 1046 tensors / 518,583,635,408 B = 482.97 GiB total, engram 188.83 GiB,
  main weights 294.14 GiB, padded to a 16,384 multiple. Confirmed from the part1 header already:
  `blk.0-39` only, **zero `mtp.*`** (see DS41-B13). Confirm both parts' byte sizes against the HF
  manifest, then join per the upstream downloader (append `.part2` onto `.part1`, needs ~37 GiB
  free headroom, not a second full copy). Verify the joined size equals the sum of parts
  (482.98 GiB) and any publisher checksum, then remove the parts. Read the header: `general.architecture=deepseek41`,
  block count, `nextn` layers = 3, and the Engram tensor shapes/types listed above. Record ~200 GB
  free after the join; flag anything under that.

### B — Port (experimental only; production stays frozen)

- [x] DS41-B0 — **Decision package: port from vcruz `runtime/deepseek41` or write fresh on
  `deepseek4`.** (a) Adapt a pinned vcruz head: loader, Engram and hyper-connections are already
  reported against the reference, but sparse attention is unfinished, MTP is stripped, and the
  tensor names differ from antirez (9/36 per-block names plus the antirez extras need a compat
  map). (b) Extend production `deepseek4` fresh: MTP graph and hyper-connections already exist
  locally, but Engram, KV/index sharing and candidate blocks are written from `inference/model.py`.
  (c) Hybrid: take vcruz's Engram/loader deltas as reference only and build on `deepseek4`.
  Recommendation: **(c)**. Source-audit first (pin SHAs, diff vs `deepseek4.cpp`), same shape as
  the GLM-5.3 T0 audit. This is an engineering choice, not an operator gate; proceed on (c) unless
  the audit shows vcruz's sparse path is further along than reported.
  **RESOLVED 2026-09-22 → (c), reference only.** Four read-only audits (vcruz branch, our v10
  `deepseek4`, the antirez artifact + `antirez/ds4`, the official reference). Findings:
  - **vcruz `runtime/deepseek41` pinned at `5210c7c5ed61dddaee6ed476623abf4b63093d16`** (2026-09-12),
    16 commits / 20 files / +1866-63 over merge-base `311d4211` — which is **not** an ancestor of
    v10, is 228 commits behind master, and needs `ggml_rope_set_offset` back-ported. Its two most
    edited files (`src/models/deepseek4.cpp`, `src/llama-kv-cache-dsv4.cpp`) are exactly where v10
    carries our fused `ggml_dsv4_hc_pre/post` path, so a merge is HIGH conflict. Its sparse
    attention is still a **dense mask + top-k**, not a gather (`deepseek41.cpp:781-797`); the
    two-level candidate mask is absent and **caps the context** (`:32-34`); MTP absent. MIT, no DCO.
  - **v10 already covers ~55-60% of the non-Engram, non-vision backbone.** Free: `sqrtsoftplus`
    (v10 *requires* it), hyper-connections + Sinkhorn (parametric, `hc==4` asserted, fused CPU+CUDA
    op — better than vcruz's), MoE bias/route_scale/norm_topk_prob, Q4_K/Q8_0/MXFP4 experts,
    `TENSOR_READ_LAZY`. The lightning indexer is near-verbatim reusable and **already
    block-granular**; our top-k path is a real gather where vcruz's is a mask.
  - **Take from vcruz as reference/port, never as a merge**: the Engram host-side hash +
    `set_input`, the `{pre,post,comb}` lag refactor, the ratio/overlap generalisation in
    `llama-kv-cache-dsv4.cpp`, three shared-code fixes (kv-cache reuse loop, `build_input_k_rot`
    zero-layer guard, `has_cell_ext`), and the engram q/k quantization skip.
  - **Not in the brief, and now priced**: RoPE covers only the last 64 of 512 dims as *interleaved
    pairs*, with the **inverse rotation applied to the attention output** (no llama.cpp DeepSeek
    path does this); `compress_ratios` are {0,1,2} while our loader throws on anything but
    {0,4,128}; FP8 block scale is [32,32] `ue8m0` while our converter hardcodes 128; expert FP4
    scales run along K only, per output row.
  Effort, component by component: attention skeleton S · indexer S · HC free · MoE free · quant
  free · compress ratios M · cross-layer KV share S-M · index share M · candidate blocks S ·
  loader/converter M · **Engram L** · **DSpark L** · vision L (dropped). ✅ 2026-09-22
- [x] DS41-B1a — Branch created: **`experimental/deepseek41-port-20260923`** off the **current
  AutoKernel champion** `ak/champion/llama-cpp-ffc1bac82eec`, which today is exactly
  `ffc1bac82` = production-consolidated-v10 (champion reseeded on the freeze; 0 commits either
  way). Worktree `/mnt/raid0/llm/llama.cpp-experimental-deepseek41-20260923`. The frozen tree was
  not touched (still on `production-consolidated-v10`, clean). ✅ 2026-09-23
- [x] DS41-B1b — Build CPU and HIP **DONE 2026-09-23**: both green at version 10303 (`ffc1bac82`), `$ORIGIN` runpath, `verify_ggml_linkage.sh` PASS for each. ✅ 2026-09-23 — original text: on that branch and prove linkage with
  `verify_ggml_linkage.sh`; record the build dirs under `kernels/builds/` (pre-flight P4: never
  build into `tmp`, evidence from an ephemeral root is inadmissible). Re-base onto the champion tip
  whenever the champion moves, per *Kernel work rides the champion* below.
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

- [x] DS41-K0 — Preserve and port. The source branch `ak/glm53-recovered-accumulator-20260912` is
  pushed to `fork` (it was 5 commits ahead). It is cherry-picked onto v10 as
  `experimental/glm53-keeps-on-v10-20260922` (fork): 28 keeps plus the row-exact MTP prerequisite
  `04ffb8ad0`. Its generic ggml/llama-context/server parts are ported, and its GLM5Next-only tests are
  dropped. There was one conflict, in `tests/CMakeLists.txt`. The CPU build compiles, with iqk symbols
  present. `test-rowexact-backend-toggle {dense,densef32,mmid}` exits 3 (`difference_witness=0`)
  **identically on the original `614ff2ba0`**, so this is not a port regression. The test's witness
  does not engage on this host as written; fix or retire it in K1. The 11 in-flight lane diffs from
  the deleted runs are in `artifacts/autokernel/glm53-inflight-candidates-20260922/`; they are
  unmeasured. ✅ 2026-09-22
- [ ] DS41-K1 — Cross-workload admission of the ported branch vs v10 on the current CPU roles,
  under the AutoKernel cross-workload keep gate: speed paired with quality/coherence, per keep or
  bisected. Survivors become a **v11 champion candidate** through the standard four-step workflow
  (full-candidate bench, no cherry-picks at promotion). The row-exact keeps must also pass the
  MTP exact-trajectory gates on an MTP role.
- [ ] DS41-K2 — Re-measure the surviving keeps on deepseek41 once DS41-T1 passes, and evaluate the
  11 in-flight candidates as AutoKernel seeds on the V4.1 surface.

### B0 follow-on — the work items the audit actually produced

Sources pinned 2026-09-22: antirez runtime `antirez/ds4` **`main` @ `0aaea5a238fb41a35106a551e73c8409dfb751ac`** (MIT, reusable with notice; the branch `ds4.1flash` named on the model card **does not exist**); vcruz `runtime/deepseek41` @ `5210c7c5`; official reference under `models/deepseek-ai/DeepSeek-V4.1-Flash/`.

- [x] **DS41-B7a — Engram gather op implemented** (2026-09-23): `ggml_gather_rows_e4m3_e8m0` on `ak/lever/engram-gather-20260923` @ `f13ab7669` (pushed), +188-4. A **dedicated op**, not an I8 case in `get_rows`: no existing graph can reach it, so champion-foldability is provable by inspection. Row width from `ne[0]/33`, so 264 bytes is just `k=8`; scalar CPU forward on the existing row/column-chunk split; vectorization deliberately left as a measured lever. Unit test compares bit-exact against hand-computed magnitudes over three geometries and passes — **its own spot-check was wrong on first run** (asserted -1.0 at a column carrying +1.0); corrected, and both columns kept. A second commit `8df1b5cf2` refreshes a stale `GGML_OP_COUNT` assert in `ggml-rpc.h` (101 vs the tree's 103; it only compiles under `GGML_RPC`, so it had drifted silently). **Not yet measured, not yet folded.**
- [x] DS41-B7b-prep — measurement harness ready 2026-09-23 (not yet run):
  `/mnt/raid0/llm/tmp/ds41-engram-bench/` — a perf harness patch against the lever (`git apply
  --check` passes), `run_gather_bench.sh`, `PROTOCOL.md`, `FOLD.md`. It mmaps a 64 GiB synthetic
  table at production geometry with `POSIX_MADV_RANDOM`, gathers 48 random rows per iteration, and
  reports min/p50/p90/p99/max and GiB/s — never a bare mean — across three arms over identical
  bytes in identical order (the op, a memcpy-only gather, an f32 `get_rows` at the same row
  stride), with major/minor fault deltas and a `mincore` residency sample as witnesses. Cold is
  `posix_fadvise(DONTNEED)` on that file only, not a global flush (unprivileged, and a global
  `drop_caches` is refused while a region claim is held, so any flush must precede the claim). The
  driver exports the canonical OMP/affinity/NUMA stack, verifies ggml linkage fail-closed, and
  holds a CPU region claim per rep. **This is not llama-bench and carries no protocol id**, so its
  output is an OBSERVATION, never a serving claim; the floor is a calibrated A/A at unit=process,
  n=24 with an interval. ✅ 2026-09-23
- [x] **DS41-B7b — folded into the champion 2026-09-23.** `ak/champion/llama-cpp-ffc1bac82eec`
  ffc1bac82 -> `8df1b5cf2`, a fast-forward, **published to `fork` only**: the local ref could not be
  moved because `/mnt/raid0/llm/tmp/ak-loop-tree` has that branch checked out (clean, at the old
  tip); its owner fast-forwards when convenient. Evidence, all structural plus the tests: additive
  diff (8 files, +406-4, of which 218 lines are the test), the new enum appended immediately before
  `GGML_OP_UNARY` with **no existing ordinal moved**, `grep` shows the symbol only in its own
  declaration and definition — **zero emitters anywhere in `src/`, `tools/`, `examples/`** — so no
  existing graph can reach it; unit test passes bit-exact, `test-backend-ops -o MUL_MAT` passes.
  The synthetic gather numbers are **not** a gate on this fold and were not run for it: nothing
  reaches the op, so the champion headline cannot move, and a headline re-measure here would be a
  control with no knob fired. The harness (B7b-prep) stands ready for when a graph does emit the
  op, which is when this becomes an ordinary keep under AKX-P5a.
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
- [x] **DS41-B10 — KV-key adapter + arch delta. DONE 2026-09-23** — `experimental/deepseek41-port-20260923` @ `f493088b3` (pushed to fork), 13 files / +550-11, compiled and symbol-verified (`deepseek41.cpp.o`, 11 `deepseek41` symbols, engram tensor names in `libllama.so`). Adds a per-arch KV alias table (a shared-path change worth a review eye), `sqrtsoftplus` string->enum, ratios {0,1,2}, absent hash/nextn defaults, compressor/indexer tensors on the **source-layer** sets, engram tensors declared. `build_arch_graph` **deliberately aborts** instead of inheriting V4's graph, which would silently run plain SWA with the compressor/indexer/engram paths never built. Corrections found while implementing: the GGUF's `compress_ratios` has 40 entries (not 43), `rope_theta`/`compress_rope_theta` are UINT32 and `original_max_position_embeddings` FLOAT32 (type-strict getters, so no name alias), there is **no `rope_scaling.rope_type`** so the generic reader defaulted to *linear* and had to be overridden to YARN, and **no per-block name compat map is needed** — all 36 names already match, only presence differs. ✅ 2026-09-23 — original scope: The artifact's ~67 KV keys are **raw HF config
  names** (`deepseek41.hidden_size`, `.num_hidden_layers`, `.sliding_window`, `.hc_mult`, …), not
  llama.cpp canonical, so load fails in generic `load_hparams` before any V4.1 code runs. Map them;
  convert `scoring_func` string -> our `expert_gating_func` enum; accept `compress_ratios` {0,1,2}
  (today the loader throws on anything but {0,4,128}); supply `hash_layer_count=0`. Subclass
  `deepseek4`: make `output_hc_*`, `ffn_gate_tid2eid`, `nextn.*`, `attn_compressor_ape` and
  `indexer_compressor_*` non-required, move compressor/indexer creation to the *source-layer* sets,
  wire `indexer.attn_k`/`k_norm`, ignore `exp_probs_b_vl.bias`. Note `general.alignment = 16384`.
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
- [~] **DS41-B13 — DSpark drafter: IN PROGRESS 2026-09-23** (operator: wire it in). Official shards
  44-46 downloading (~8 GB); the tied `embed`/`head`/`norm` live in shards 2 and 43 and are **not**
  being downloaded — they come from the GGUF we already serve, saving ~21 GB. Conversion and runtime
  are being built in parallel (`/mnt/raid0/llm/tmp/ds41-dspark-convert/`,
  `/mnt/raid0/llm/tmp/ds41-dspark-runtime/`). The runtime must carry acceptance-rate instrumentation
  (accepted/proposed per position) so the campaign measures alpha instead of assuming it. Original
  scope:
- [x] **DS41-B13 — DONE 2026-09-23: the drafter is wired, measured and profitable.**
  Drafter GGUF `DeepSeek-V4.1-Flash-DSpark.gguf` (9.32 GiB, 83 tensors, arch `deepseek41-dspark`),
  16/16 conversion checks incl. a bit-exact expert round-trip and tokenizer KVs identical to the
  target. Runtime on the port branch (patches 01-06 + 10): the tree already had a DSpark driver for
  V4, so this was four V4.1 deltas, not a new runtime. **Serving-class results, -t 48 -tb 96:**

  | arm | decode t/s | vs control |
  |---|---|---|
  | no drafter | 11.43 | — |
  | greedy, serial verify (today's default path) | 7.18 | 0.63x |
  | **greedy, batched verify** | **17.85 median** | **1.56x** |
  | low-entropy prompts, batched | 18.79-22.08 | up to 1.75x |

  Two traps caught on the way: a first crash was **not** the "missing target_hidden_size" warnings
  (both paths independently computed the right 15360) but a graph input constructed at 5120 while
  fed 15360 — and fixing only that would have traded a loud crash for **silent corruption**, since
  `llama_decode` strides an embd batch at `n_embd_inp()` before the graph is built. The width is now
  derived from the drafter's own `main_proj` weight, so a drafter distilled onto a differently-sized
  target is rejected rather than silently mis-strided.
- [x] DS41-B13b — **Block width matters more than the drafter**: block 5 is break-even (8.24),
  block 3 gives 10.26 and block 2 gives 10.48 at temp 0.7, acceptance 31.3 / 44.4 / 51.6%. Verify
  cost is ~86 ms + ~23 ms per block token, so break-even needs ~1.7 accepted at block 5 but ~1.1 at
  block 3. Recipe default is block 2. ✅ 2026-09-23
- [ ] **DS41-B13 (scope) — DSpark drafter (the spec-dec path), separately.** DSpark **does exist for this
  model**: the official checkpoint ships 2,401 `mtp.*` tensors in shards 44-46 (~8 GB) and
  `inference/model.py:1032-1156` implements it — a 3-block draft transformer over a **5-token
  block, bidirectional in-block**, own 128-expert/top-3 MoE, rank-256 Markov bias and a confidence
  head, embed/head tied to the backbone, fed by the hc-mean of the attention input at layers
  37-39. antirez neither ships nor implements it (`docs/MODELS.md:50`), and vcruz strips it, so
  **our artifact has no drafter**. Cheap fix: fetch only shards 44-46 and convert them into a
  separate draft GGUF; no 510 GB re-download. **The accept/verify loop does not exist even in the
  reference** (`generate.py` never calls `forward_spec`) — we would write it. Our `graph_mtp`
  asserts `n_layer_nextn == 1` and is the wrong axis (sequential depth, not block-parallel);
  `LLM_ARCH_DFLASH` is the closer template.
- [ ] **DS41-B14 — Rollback is value-level, not a position rewind.** Every cache here is
  destructively mutated: the 128-slot window ring for all blocks, the compressor's fixed-size
  `kv_state`/`score_state` accumulators on the 4 kv-source layers, the compressed-KV and indexer
  row writes that fire only when a group completes, and the n-gram hash state. The accumulators
  cannot be undone by rewinding a counter — the pre-step slot values must be saved. A naive port of
  `llama_kv_cache_seq_rm` corrupts them silently. This is the precondition for DS41-T4.

### C — AutoKernel campaign (operator-directed 2026-09-23)

*"Start an autokernel routine to improve everything about the champion kernel running this model on
CPU"*, with *"I DO NOT CARE ABOUT BASELINE, ONLY MAX PERFORMANCE"* and **spec decode in the recipe**.

- [x] DS41-C0 — **Preliminary canonical recipe fixed at `-t 48`** (operator: decode matters more
  than prefill). Basis: tg128 13.18 @48t vs 12.74/12.81 @96t; tg512 11.70 @48t vs 10.59 @96t;
  pp512 144-146 @96t vs 137.0 @48t. Prefill keeps 96 where a tool supports the split
  (`--threads-batch`); llama-bench does not. ✅ 2026-09-23
- [x] DS41-C1 — **Codified 2026-09-23**, research `2c68bc1a`: `scripts/lib/deepseek_v41_flash_recipe.py`
  on the qwen38 sibling precedent, inheriting the canonical prefix/OMP/IQK/pre-evict/placement-proof
  with `assert_inherits_canonical()` proving no fork; 23 contract tests pass. Category **CANDIDATE,
  not OPTIMUM**. Every `SPEC_DEC` field is present and `None` with an explicit `flips_on`, and
  `build_serve_command()` **refuses by default** unless the caller passes `spec_dec=False`, so the
  unmet max-performance requirement surfaces at the call site instead of silently. **The thread
  split cannot be expressed by the bench path**: `llama-bench` parses only `-t` and calls
  `llama_set_n_threads(ctx, n, n)`, and the autokernel serving path raises on `-tb != -t` — only a
  direct `llama-server`/`llama-cli` launch can carry 48/96, so a bench pp512 row is not this
  recipe's served prefill rate. ✅ 2026-09-23
- [x] DS41-C2 — **Campaign config prepared 2026-09-23** (`/mnt/raid0/llm/tmp/ds41-ak-config/`:
  CONFIG/LIFECYCLE/LAUNCH/SPECDEC + three ready config files). Four findings:
  1. **`gpt-6-sol` does not exist** — the model cache lists `gpt-5.6-sol`, `gpt-6-astra`,
     `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`; zero occurrences of `gpt-6-sol` anywhere in either
     repo, and no hosted fallback (`OPENAI_API_KEY` unset, the `openai` backend pinned to gpt-4o
     with no live dispatcher). **Reachable gpt-6 is `gpt-6-astra`, effort `high`** → OPERATOR
     DECISION (queued).
  2. **Both actor swaps are CLI flags, not code**, on the unified loop plane (`loop/run.py:670-679`
     exposes `--planner-model/-effort` and `--critic-model/-effort`). The sealed GPU
     `discovery_controller` cannot host a CPU campaign at all (roster exact-equality,
     `ALLOWED_DEVICE_IDS={"mi210_0"}`). Planner needs no source change either: add an
     openai-compatible provider at `http://127.0.0.1:8074/v1` in the opencode config. Smoke-test
     first that the local model holds the structured-output contract.
  3. **Lifecycle: NO — the loop cannot touch :8074.** Every kill targets a `Popen` handle, a
     `start_new_session` pgid or an owned cgroup leaf; the ban on name-pattern signalling is
     enforced by four AST auditors plus a regression test, not convention. Zero `orchestrator_stack`
     call sites, zero `drop_caches`/`munlock`/pre-evict code. The server also runs `--mlock
     --no-mmap`, so its weights are unevictable. The guarantee is structural — there is no knob
     because there is no path.
  4. **The blocker is the inverse of the question**: `competing_inference_witness()` classifies any
     UNOWNED `llama-server` as competing and **raises**. :8074's parent is a containerd shim, so it
     is outside every owned scope and there is no allowlist parameter. **The server is safe; the
     campaign is blocked.** → OPERATOR DECISION (queued). ✅ 2026-09-23
- [x] DS41-C2b-gate — **Competing-inference block resolved and landed** (research `a46c9d3d`): the
  gate now brackets each measured span with cumulative `utime+stime` reads for the unowned
  INFERENCE_LIKE processes, so it asks whether one did WORK, not whether one exists. Monotone
  counters mean a burst between samples cannot hide. Allowance pinned to measurement: over a 279 s
  idle observation all 13 resident servers accrued <= 0.06 core-seconds, so 0.5 core-s + 0.02
  cores/s sits ~100x above idle and ~46x below one busy core. It also converts the operator's "the
  planner never runs during measurement" into a checked invariant. 303 tests. ✅ 2026-09-23
- [x] DS41-C2c — **Dry run steps 1-3 pass.** Binary rebuilt from the committed tree so it
  self-identifies (`version 10310 (ad932bbd9)`, clean tree — it previously reported `7c18bb8c1`
  from an uncommitted build, exactly the INF-70 C9 shape); `verify_ggml_linkage.sh` PASS;
  `verify_llama_cpp.sh` PASS on the frozen tree; critic `gpt-6-sol` high answered a live probe;
  planner answered `{"ok":true}` through the loop's OWN invocation
  (`opencode run -m qwen-local/qwen3.8-flash-next --variant high`), which was the genuinely
  uncertain step since `Backend.argv` always passes `--variant`. Campaign store populated at
  `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/`. ✅ 2026-09-23
- [x] **DS41-C2d — LAUNCH BLOCKER: the recipe layer cannot express DSpark.** ✅ 2026-09-23 — research
  `3d1bf4b2` (type, argv mapping, `--parallel 1` refusal, `LLAMA_SPEC_EXACT` required for greedy with a
  `process_environ` witness) and `5125f7ab` (a greedy draft-dspark template was still not expressible
  as a *canonical* launch: the projection is env-less by construction while the guard requires a
  declared env — the compare now strips env and the frozen launch env is checked instead).
  `loop/resolved_recipe.py:27` has `SPECULATION_TYPES = {"none", "draft-dflash", "draft-mtp"}` —
  no `draft-dspark` — so the prepared recipe is forced to `spec_decode: {"type": "none"}` and the
  campaign would optimise the NO-DRAFTER surface we have already beaten by 1.56x. Patch in
  preparation adds the type, the `-md`/`--spec-type`/`--spec-draft-n-max` mapping, the
  `--parallel 1` refusal (the server refuses multi-slot for draft-dspark), `LLAMA_SPEC_EXACT` as a
  declared measurement key with a witness (its absence must REFUSE, not fall back to the serial
  path — that silent fallback produced the 7.18 t/s reading today), and the drafter in the recipe
  identity.
- [x] DS41-C2e — **Enrollment tooling defect, fixed** ✅ 2026-09-23 (orchestrator `c3f2cbc2`: re-exec moved
  under `__main__`; `test_orchestrator_stack_import_is_argv_safe.py`). Not used by the launch — the
  campaign runs on the roster-free `--manifest` + `--registry-snapshot` route, which is orthogonal to
  the production roster (operator, 2026-09-23). Original note:
  `epyc-orchestrator/scripts/server/autokernel_enrollment.py:276` does
  `from scripts.server import orchestrator_stack`, and that module parses `sys.argv` at import, so
  it sees the ENROLLMENT's flags, prints stack status and exits 0 without writing the output. The
  campaign resolver accepts `--registry-snapshot` as an alternative to `--production-enrollment`
  (`campaign_cli.py:201`), which is the route taken: a
  `epyc.autokernel.artifact_registry_snapshot.v1` file carrying model/build/recipe identities
  (`{schema, kind, ref, path, sha256}` each). Fix the import-time argparse separately.
- [x] DS41-C2b — **LAUNCHED 2026-09-23 18:06** ✅ 2026-09-23 — `serial_run` PID `1586972` (run.py `1586978`),
  store `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/`, inputs built by
  `inputs/build_inputs.py` through the loop's own validators (canonical_launch.v1, frozen prompt v2,
  IDENTITY receipt on `build-cpu`, manifest + snapshot, `--verify-artifacts` passed on all 5).
  Serving metric `aggregate_tok_s` on the DSpark greedy-batched recipe, `--rounds 0`,
  planner `opencode:qwen-local/qwen3.8-flash-next@high` (the live :8074 server, unchanged), critic
  `codex:gpt-6-sol@high`. First launch had `perf record`+`perf stat` attached. It opens with the
  loop's 48 matched calibration launches. Superseded launch note (llama-bench surface): `--surface tg128` (the default
  is `pp512` and MUST be overridden), `--confirm-surfaces dec-b4,dec-b8`, `-t 48`, cpu_list 0-95,
  np 1. There is no `tg512` surface. `Recipe` carries one `threads` field, so pp512 rows from this
  target are off-optimum and must not be reported as prefill results — prefill is a second target.
- [x] DS41-C3 — **The campaign measures the spec-dec-on surface** ✅ 2026-09-23 — target declares
  `speculation: external_draft` + `drafter_ref local:ds41:drafter-dspark`; new type `draft-dspark`, not
  `draft-mtp` (the assumption below was wrong, as suspected). Original:
  Blocked on DS41-B13. The schema already supports it (`TargetSpec.speculation` ∈
  `{none,self_draft,external_draft}` + `drafter_ref`; `spec_decode:{type:"draft-mtp",…}` →
  `-md/-ngld/--spec-type/--spec-draft-n-max`, `draft_n_max: 5` from DSpark's block). The target
  declares `speculation` from day one so no interim number can be mistaken for a spec-dec result,
  and the drafter lands as a **second target**, not an edit. **Biggest unverified assumption:**
  whether `--spec-type draft-mtp` can drive an *external* DSpark-shaped drafter at all — it was
  built for self-drafting heads and may need a new speculation type plus a server path.
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
- [x] DS41-C5 — Seeded ✅ 2026-09-23 as `store/inbox/30-ds41-seeded-hypotheses.md` (ranked H2 requant
  ladder, H1b verify-marginal attribution, H3 rowexact-on-dense, H4 entropy-gated block, H1 demoted,
  H6, H7; measured basis and falsifiers; re-read by the planner every iteration). The
  `opportunities.json` profile form stays unbound (placeholder digests) — the inbox is the channel.
  Budget guidance: **decode is flat 24->96 threads**, so barrier and
  dispatch levers cannot pay on this model. Point the campaign at the memory path (engram gather,
  expert gemv), not at parallelism.

- [x] DS41-C12 — **All three in-tree profilers wired into the loop** ✅ 2026-09-23 (operator: "give
  autokernel access to ALL the profiling tools"). llama.cpp `ebb68dc55`: Engram gather/per-layer
  counters landed, compile-gated on `GGML_CPU_PROF` with `LLAMA_ENGRAM_PROF_JSON_FILE` (measured
  `build-cpu` carries zero instrumentation strings). Research `c6a46674` (`loop/node_profile.py`,
  17 tests on real dumps) + `e59c87ea`: `reprofile()` builds a `-DGGML_CPU_PROF=ON` sibling of the
  anchor, launches it only inside the profile window with `GGML_CPU_PROF_JSON_FILE`,
  `LLAMA_HOST_PROF_JSON_FILE`, `LLAMA_ENGRAM_PROF_JSON_FILE`, level 2, parses the three dumps into
  `node_profile` in the planner context (per-op shares, host phases, Engram fault mix), cached by the
  perf capture's key, never in a ranked A/B; `--node-profile` rides `--common-args`; teardown waits
  180 s so a `--no-mmap` server's atexit dumps survive. Proven on run 3's anchor at 19:38:
  `teardown: terminated`, all three `observed`; experts 42.1% / dense 38.3% of wall,
  `ctx.graph_compute` 99.2% of the decode step, Engram 0 major / 0 minor faults per decode token.
- [x] DS41-C13 — **Campaign restarted as run 3** ✅ 2026-09-23 19:28 (`state-run3/serial-run.pid`
  = 1953258). Run 1 (perf only) stopped and archived (`store-run1-ad932bbd9`); run 2 refused —
  the shared store pinned run 1's champion-of-record `ad932bbd9` against anchor `ebb68dc55`
  ("never relabel the tip build"), so run 3 uses a fresh store with the inbox carried over.
  Anchor/inputs/resolution rebound to `ebb68dc55`, artifact verification 5/5.
- [ ] DS41-C14 — `--node-profile` is opt-in in `run.py` (default OFF) because run.py's hermetic
  fixtures would gain a real build + a second launch if it defaulted on. Make the fixtures opt out
  explicitly, then flip the default so no future campaign can launch without the instrument.
- [ ] DS41-C15 — `node_profile` semantics under speculation: `llama-host-prof` counts one batched
  verify call as `n_eval=1`, so `decode_us_per_token` is per graph eval, not per token, when DSpark
  is on (carried as a limitation string; needs a no-drafter cross-check to state the ratio).
- [x] DS41-C16 — **Schema-constrained repair turn for actor replies** ✅ 2026-09-24 (research `ad2b89ff`,
  `HEAD`, `loop/actors.py` `_parse_reply`/`_schema_repair`): the typed-decision plane's TD-1 idiom
  applied to the loop's planner/author/critic replies — when the agentic reply's JSON is missing or
  incomplete, two constrained `response_format json_schema` turns on the same local server (explicit
  decline boolean, then pure extraction; reviews skip the boolean). Proven on the 27B with the report
  lost at 03:09 plus four shapes, 2–12 s each; three refuted designs recorded in the module.
  **Intake gap:** `typed-decision-plane.md` never listed AutoKernel's actors as a consumer of the
  pattern; the loop was the largest free-text-JSON consumer in the stack.
- [x] DS41-C17 — **Planner seat moved to `qwen-gpu/qwen3.8-27b`** (MI210, :8083) ✅ 2026-09-24
  08:52, run 6, request r3. Measured basis: 27B 86 t/s decode / 302 t/s prefill vs flash-next 50 / 92;
  CPU planner proposals 97 and 41 min (prefill-bound, 124 k tokens of tool output), authoring #1 killed
  at the 7200 s budget after 91 k output tokens (decode-bound). `--variant` is a no-op on a plain
  OpenAI-compatible provider. Related fixes: `--actor-timeout-s` (`ef287ba9`), raw reply persistence +
  stderr fallback (`704ef037`), partial output kept on timeout (`3471fe3c`), `stage_timeout_s` 900→2700
  (perf profile was refused at the 900 s cap). Filed: planner server :8074 runs `-t 96` while the registry
  recipe says `threads: 48` (`NUMA_FULL_T48`) — launch/registry divergence, stack owner's.
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
- [ ] DS41-C10 — Watch run 7 (27B planner, schema repair active, started 09:10) into its first measured
  iteration; report planner→critic→author→build→A/B timings against the CPU planner's 41–97 min. Original:
  `state/loop-status.json` + `store/` (the 48 A/A launches each reload 519 GB, ~2 h); confirm the
  serving floor lands with a unit, the planner's first proposal cites the inbox, and the critic
  answers. Kill only `state/serial-run.pid`'s tree, verify dead.
  **Partial 2026-09-24:** run 7 STOPPED ~10:18 on operator request at iteration 0, 0 measurements
  (`state-run7/STOPPED.txt`). First 27B proposal `akm-q4k-q82x4-weight-prefetch` landed in ~39 min (09:16→09:55)
  but was discarded by an actor-seat defect, and the critic then rejected a repair-fabricated stand-in
  (`src/verify/replay.ts`) — both fixed under DS41-C20. `serial_run` and `run.py` did not exit on SIGTERM and
  `run.py` respawned the actor after its death: stopping needed TERM on the actor, then KILL on `run.py` +
  `serial_run` (root cause and fix task: DS41-C22). Carried to run 8, launched after DS41-C20.
- [ ] DS41-C11 — Pre-existing test failures found while landing `5125f7ab`, reproduced on a clean HEAD
  checkout: `test_existing_cpu_run` (3: `oracle()` unexpected kwarg `require_reference`) and
  `test_serial_roster` (3: "issued selection awaits settlement"). Not this session's change; fix or
  re-fixture.
- [x] DS41-C19 — **v10 folded-lineage fix reaches this campaign** ✅ 2026-09-23 (non-inference ROI session,
  research `714777e4`, fast-forwarded into the shared research clone 20:3xZ). At v10
  `MEASUREMENT_COMMIT == PRODUCTION_COMMIT`, so `candidate_record.build_candidate_record`'s old
  "instrument parents == (production,)" rule was unsatisfiable: the FIRST CPU candidate of this campaign to
  reach recording (`campaign.py:5011`) would have raised `ValueError("instrument commit is not the ratified
  single-child of the production base")`. The shared `worktree.instrument_lineage_ok` now accepts the folded
  identity and still requires the source to descend from production (`ebb68dc55` descends from v10
  `ffc1bac82` — verified). Same fix in `live_controls` preflight. Nothing had hit it yet (run3 still in
  batch 0; no lineage error anywhere under the campaign dir). The running batch process keeps its
  already-imported modules; the next batch process loads the fix — no mid-process version mixing
  (all three modules are imported at load time).
- [ ] DS41-C20 — **Bounded opencode seat: merge gate.** Research worktree
  `/mnt/raid0/llm/tmp/ak-actor-seat-20260924` (`lane/ak-actor-seat-20260924`, committed as research
  `e9495971` and pushed to the LANE only, not to research `main`). Fixes the two
  defects that cost run 7's iteration 0: (1) `_run_agent` discarded any rc≠0 reply unread — opencode exits 1
  after a recovered tool error (`(res.stderr || "").trim is not a function`), so a complete hypothesis was
  retried from zero; now a reply COMPLETE for the caller's schema is salvaged, and only when rc > 0 (a signal
  death stays a transient); anything else stays a transient;
  (2) `_parse_reply` ran the constrained repair over an EMPTY retry reply and it invented
  `replay-verification / src/verify/replay.ts`; now no repair runs without a report, and a repaired
  `target_surface`/`target_symbol` the report never names is refused. Also: the opencode prompt now rides
  STDIN — opencode 1.18 re-quotes any positional with a space and backslash-escaped all 2,982 quotes of the
  run-7 prompt (and a ~100 KB prompt sat near the 128 KiB per-argument limit); prompt diet
  (`_dedupe_subtrees`, `_slim_shared_history`: 95.7k → 75.9k chars on the run-7 prompt); `ActorSeat` +
  `loop/actor_opencode_config.py` (per-run agent prompt, step cap, `tool_output` cap, read-only scout fan-out,
  `MAX_CONCURRENT_SUBAGENTS=2`) + `loop/actor_tools_mcp.py` (outline / read_range / grep / code_search /
  profile_top / symbol_annotate, output-capped; runs under the orchestrator venv, the only one with `mcp`);
  `run.py --actor-seat {bounded,plain}` (default `bounded`), `--actor-fan-out`, `--actor-steps`; per-call
  `actor-replies/actor-calls.jsonl`. Later fixes the same day, all found by the A/B itself:
  (3) **template echo** — opencode's compaction summary quotes the prompt's `{"abstain":"<reason>"}` template,
  and the bounded-v1 driver recorded exactly that object as its "hypothesis"; `_extract_json` now skips
  template-echo objects and refuses them as abstentions; (4) **actor stdout/stderr go to FILES, not pipes** —
  opencode/Bun exits without draining a pipe: the same session export read 65,536 / 98,304 bytes via a pipe vs
  328,871 via a file (`/mnt/raid0/llm/tmp/ak-seat-ab/bounded-ses_*.json` is the 98,304-byte truncated copy), and
  the reply JSON is the TAIL, so a long run would lose it; (5) **config v2** — guidance rides an opencode
  `instructions` file instead of an agent `prompt` that REPLACED opencode's terse default system prompt (the v1
  cause below). Tests: actor suites **167** green (`test_actors`, `test_actor_opencode_config`,
  `test_actor_tools_mcp`, `test_actor_lifecycle`, `test_actor_preparation`); full `autokernel/loop` suite shows
  the same 152 pre-existing failures as the branch point `e485008a` plus one flaky test
  (`test_gpu_runtime::test_gpu_calibration_actual_http_keeps_both_original_claims_and_device_trace`) failing
  intermittently on both — no regression. Planner A/B `plain` vs `bounded` on the same (un-escaped, dieted)
  run-7 prompt, 27B :8083, own detached lane `/mnt/raid0/llm/tmp/ak-seat-ab/lane` @ `ebb68dc55`
  (`/mnt/raid0/llm/tmp/ak-seat-ab/driver.py`). Reference for the plain seat,
  first 27B proposal (run-7 opencode export): 71 steps, 70 tool calls (54 bash), 63.8k decoded tokens, 40.3 min,
  2 compactions, 46k-token initial prompt, tool results 275k chars total (max 58 KB). **Bounded v1** (agent
  `prompt` replaces opencode's system prompt): STOPPED at ~35 min (`wall_s` 2180.5,
  `result-bounded-v1-stopped.json`) after **12 steps**, median **1,626 decoded tokens/step vs 266** on the plain
  seat, one step 19k tokens, context full (97.7k) at step 12 → 1 compaction, tool outputs only 42k chars, 0
  scouts used, no hypothesis (template echo). Reading: the context is filled by the model's own deliberation,
  not by tool output — the output caps worked, the replaced system prompt made each step ~6x longer. **A/B
  verdict PENDING**: the plain arm (new prompt) has run since ~11:19, bounded v2 is queued after it.
  Acceptance: (i) A/B result recorded here
  with steps / tool calls / decoded tokens / wall / compactions per arm and the schema-valid verdict of each
  reply; (ii) committed on the lane and merged to research `main` only if `bounded` is not worse on wall AND
  yields a schema-valid hypothesis — otherwise keep `plain` as default and record why; (iii) the next
  campaign run launched from the merged tree, never from the worktree.
  - [x] DS41-C20a — seat committed on the research lane (`e9495971`, 8 files, 167 tests green) and the lane
    pushed as a backup; research `main` untouched pending (ii) ✅ 2026-09-24
  - [x] DS41-C20b — bounded v1 arm run and stopped; numbers above; its failure produced fixes (3)–(5) ✅ 2026-09-24
  - [ ] DS41-C20c — record the plain (new prompt) and bounded v2 arms with the five numbers + schema verdict.
- [ ] DS41-C21 — **Hand the seat over as the reference an orchestrator backend must beat.** Once C20 records
  the A/B, copy the winning arm's five numbers into `autokernel-orchestrator-actor-backend.md` §Baseline
  (INF-78) and point that handoff's OAB-4 at `driver.py`. No further orchestrator work in this handoff: the
  campaign keeps `opencode` + 27B :8083 planner and the cloud critic (operator, 2026-09-24).
- [ ] DS41-C22 — **A stop must reap a forming lane's in-flight actor, and never retry it.** Run 7's halt
  (2026-09-24 ~10:17): TERM to `serial_run` + `run.py` did not end the run, and after the actor was TERM'd
  `run.py` launched a new one (two `rc-15` replies, 10:17:04 and 10:17:49, in `state-run7/.../actor-replies/`).
  Code read (research `e9495971`): SIGTERM is by design a *drain* (`run.py` `_ask_stop` → forming lanes abandon
  at their next stage boundary; the tail holder finishes its A/B) — but a planner/critic call IS the stage, so a
  forming lane waits out the whole actor call (up to `--actor-timeout-s`), and the actor retry inside that call
  never consults `should_stop()`, so a signal-killed actor (rc −15) is retried as a transient. Fix: pass
  `should_stop` into the actor call; when a stop is asked, TERM the in-flight actor of a FORMING lane (it holds no
  device time) and treat its death as an abandon, never a retry; a lane holding the tail keeps today's drain.
  Test: a fake backend killed by SIGTERM with stop asked → zero relaunches, lane abandoned, process exits.
  Build it in a fresh worktree off `e9495971`, never in `/mnt/raid0/llm/tmp/ak-actor-seat-20260924` while C20c
  runs (the queued bounded-v2 arm imports `actors.py` from there; editing it changes the arm under test).
- [ ] DS41-C23 — **`symbol_annotate` must resolve the short symbol name the planner actually types.** Run 7's
  planner ran `perf annotate --symbol='mul_mat_qX_K_q8_2_X4_T<DequantizerQ4K_AVX2, 1>' --dsos=libggml-cpu.so`
  twice and got `... measurement-record.data data has no samples!`. The profile is NOT empty (checked read-only
  2026-09-24: `store/cpu-profiles/cpu-raw-0316509f.../measurement-record.data` 25.7 MB, 114K `cycles:u` samples;
  the same session's `perf report` shows that symbol at 19.28%). perf matches `--symbol` against the FULL
  demangled name `void (anonymous namespace)::mul_mat_qX_K_q8_2_X4_T<(anonymous namespace)::DequantizerQ4K_AVX2,
  1>(int, void const*, unsigned long, DataInfo const&, int)` and reports a filter that matched nothing as "no
  samples". The bounded seat's `symbol_annotate` passes the name through unchanged, so it inherits the trap (its
  message at least points at `profile_top`). Fix: resolve the requested name against the DSO's `perf report
  --sort symbol` rows (exact, else a unique substring after stripping `(anonymous namespace)::` and the argument
  list; ambiguous → list the candidates), then annotate the resolved full name. Test on the fixture with a
  templated name. Same worktree rule as C22 (the A/B's MCP server is spawned from the worktree's file).

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
- [x] DS41-C8 — **The per-node profiler is compiled in at last.** INF-70 built it and there was
  never a CMake option, so it has never been in a binary we shipped: `strings libggml-cpu.so |
  grep -c GGML_CPU_PROF` returned **0**. Now `-DGGML_CPU_PROF=ON` in a separate `build-prof/`
  tree, verified by `GGML_CPU_PROF_JSON_FILE` (2 hits) and `LLAMA_HOST_PROF_JSON_FILE` (1). The
  measured build is untouched. ✅ 2026-09-23
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
- [x] **DS41-T6 — first throughput baseline, 2026-09-23.** Canonical recipe (`taskset -c 0-95`,
  `numactl --interleave=all`, OMP stack, `GGML_IQK=1`, `-fa 1 -mmp 0`), binary
  `experimental/deepseek41-port-20260923` @ `7c18bb8c1` (build 10303), model
  `DeepSeek-V4.1-Flash-Q4.gguf` (482.97 GiB, 754.64 B params reported).

  | test | t=24 | t=48 | t=64 | t=96 | t=192 |
  |---|---|---|---|---|---|
  | pp512 | — | 137.03 ± 1.20 | 137.66 ± 1.52 | **144.03 / 145.80** | 104.09 ± 1.24 |
  | tg128 | 12.89 ± 0.01 | **13.18 ± 0.04** | 12.90 ± 0.01 | 12.74 / 12.81 | 4.99 ± 0.03 |
  | tg512 | — | **11.70** | — | 10.59 | — |

  Also: pp256 122.05, pp2048 119.45 ± 0.32, tg64 10.58, tg256 11.00 ± 0.04 (all t=96). The t=96
  columns are two independent runs in one sweep, so they double as a repeatability control (0.5%
  on tg128, 1.2% on pp512).

  **Operating point: prefill wants 96 threads, decode wants 48** — on a server that is
  `--threads 48 --threads-batch 96`. Both phases collapse at 192 (SMT siblings): decode -61%.

  **The shape matters more than the peak for kernel work: decode is FLAT from 24 to 96 threads**
  (12.89 -> 12.81 t/s). 4x the cores moves it under 1%, so the decode ceiling is not parallelism
  or barrier cost — it is memory. INF-70's t48>t96 finding transfers directionally, but the
  mechanism differs: there the gap was large, here it is 3% at tg128 and 10% at tg512.

  **Placement proven in-window** (the gate INF-70/C7 exists for): sampled 4x on the live process,
  resident 47.6 -> 187.8 GiB, **25.0% on each of the four nodes at every sample**, independent
  `numa_placement_check.sh` PASS at the 40% threshold. So these are not skewed-placement numbers.

  Caveats: single-model, host otherwise idle but with the orchestration stack resident; llama-bench
  is a proxy, not a serving rate (no speculation, no drafter, np=1); no DSpark drafter exists yet;
  and F32 vs the reference's bf16 rounding is unresolved (T3).
- [ ] DS41-T6b — repeat at claim grade once the operating point is fixed: unit=launch, n>=3, the
  noise floor with its unit, and a serving-shaped run (`llama-server`, np sweep) — llama-bench
  tg128 must never be quoted as a serving rate.
- [x] **DS41-T6c — FIXED 2026-09-23**, research `2c68bc1a`. Root cause, one line:
  `read -r kids < "$f" || kids=""` — `/proc/<pid>/task/<tid>/children` has **no trailing
  newline**, so `read` returns 1 at EOF *after* assigning and the `||` guard then threw the pid list
  away. `largest_rss_descendant` therefore never enqueued a child, always returned the root subshell
  (~2.3 MB), never cleared the 1 GiB floor, and the failure was swallowed by `|| true`. Region-lock
  daemonizing, the `>(tee)` subshell, the floor and the RSS-stability condition were each checked
  and **exonerated** — the walk would have found the binary on iteration one. Failure is now loud
  (`placement.log.reason` with a diagnosis and descendant dump), and selection stays structural over
  our own descendants: no `/proc` scan, no name pattern. ✅ 2026-09-23 — original:
- [ ] DS41-T6c (original) — **defect in `bench_canonical.sh`**: its in-window placement sampler never fired on
  this model (no `placement.log`, no `.rc`) across five runs, so every canonical run self-reported
  as OBSERVATION. `largest_rss_descendant` walks `/proc/<pid>/task/*/children` from the wrapper
  chain (region-lock -> env -> taskset -> numactl -> llama-bench) and did not reach the binary;
  selecting by `comm == llama-bench` works and is what captured the proof above. Fix it in the
  research repo so a 483 GiB no-mmap load — precisely the case the gate was written for — cannot
  silently skip its own proof.
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
