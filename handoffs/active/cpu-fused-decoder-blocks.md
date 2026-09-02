# CPU Fused Decoder Blocks (batch-1 decode megakernel)

**Status**: **PLAN APPROVED by operator 2026-08-30** — bit-exactness prioritized (NMSE ≤1e-4 acceptable fallback); qwen4exp-first with the GDN family in mind; op-based execution model (direct fast-path acceptable if diligent); decode prioritized, pp desirable; plan persisted before work begins.
**Created**: 2026-08-30
**Priority**: HIGH — the last identified path to 20-60 t/s batch-1 CPU decode
**Categories**: hardware_optimization, inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-67; the kernel-tree commit tags historically said INF-64)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) (INF-10) — the direct predecessor: same diagnosis (barrier/op-count-bound, not BW), 4 fusion arms REFUTED, the +2.6% DeltaNet-native-fused-wqkv precedent this project scales up
- [`batched-decode-measurement.md`](batched-decode-measurement.md) — the NUMA×placement canonical recipe (interleave+no-mmap), the same family's reference numbers
- [`autokernel-research-loop.md`](autokernel-research-loop.md) — the GPU megakernel/persistent-kernel literature (L4 lever) this project is the CPU analogue of
- `handoffs/active/master-handoff-index.md` — the router

**Framing superseded 2026-09-02 (INF-70 audit)**: this file remains the fused decoder's design record
and phase checklist. The live viability task list (A1–A4, A-GATE), the corrected measurement ledger and
the program this work now belongs to are in [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md)
(INF-70). The section below is the historical design premise: the 74 ms anchor does not reproduce
(INF-68 measured ~110 ms UD / ~95 ms uniform on a clean build), the 28/46 ms split and the 65 µs/9.4 ms
constants are in no committed profiler record, and the measured node count is 7,906 pre-fusion /
~6,890 on the baseline build, not ~5,850. Do not quote this section's numbers; quote INF-70's ledger.

## The measured problem (2026-08-29/30, qwen4exp IQ4_XS UD, interleave baseline)

Batch-1 decode = ~74 ms/token (~13.5 t/s, t48; t64 sweet spot ~14). Breakdown, all in situ:
- ~28 ms real gemv work (expert mul_mat_id ~9.4 ms at ~65 μs/call median; dense ~18 ms) — at the machine's real memory rate (~100-180 GB/s in situ)
- ~46 ms of non-gemv dispatch: ~5,850 nodes × ~5-8 μs each (barrier + dispatch + tiny elementwise compute)
- Four clean-room kernel experiments (fused hc_mix op, elementwise chain fusion ×3, gemv software pipelining) all measured NEUTRAL or NEGATIVE in situ despite clean-room wins up to +55%. The per-node machinery cost is irreducible per-node; the only way down is fewer, fatter nodes.

## The idea

Collapse the ~6,800-node decode graph to ~100 nodes: **one fused op per layer** (GGML_OP_GATED_DELTA_NET_FUSED_LAYER ×36 + GGML_OP_FULL_ATTN_FUSED_LAYER ×12 + PLE/head tail). The layer's math runs as one sequential kernel — data flows in registers/L2, no graph barriers between the layer's micro-ops. The per-node machinery runs once per layer instead of once per micro-op.

**Target**: ~28 ms gemv + ~96×15 μs fused overhead (~1.5 ms) + state/attention (~5 ms) ≈ 35-45 ms → **22-28 t/s**, with gemv micro-tuning inside the fused kernels (where dispatch can no longer eat it) reaching 30-40.

## Operator decisions (locked 2026-08-30)

1. **Numerics contract**: bit-exactness PRIORITIZED (mirror the decomposed op order internally); NMSE ≤1e-4 acceptable where bit-exactness costs too much freedom. The arch test's CPU-vs-GPU NMSE bar applies as the floor.
2. **Scope**: qwen4exp-first; the GDN family (qwen3.5/qwen3next/qwen35moe) served by the same fused ops if it isn't disproportionate — the layer structure is shared via `llm_build_delta_net_base`.
3. **Execution model**: op-based (new GGML ops, ~100-node graph, fits the scheduler/backends). A direct decode fast-path outside the graph is permitted if it becomes clearly better — diligence required (the blast radius is real).
4. **Priority**: decode first; pp acceleration via the same ops (batched) is desirable but secondary.

## Phases

| Phase | Deliverable | Milestone / gate |
|---|---|---|
| **0** | Measurement infra: fix the logit-dump tool (was crashing), standard A/B harness at the interleave baseline, in-situ profiler runs (all present from prior rounds) | reproducible fused-vs-decomposed logit diff ≤1e-4 |
| **1** | Fused GDN-layer function (36 layers): hc_mix + qkvz + conv + GDN scan (the ggml_gated_delta_net kernel) + output proj + MoE (router/top-k/topk-norm weights/expert dots/shexp) + hc_combine; recurrent + conv state in/out | decode 74 → ~45 ms; logit diff + greedy generation + arch test |
| **2** | Fused full-attn layer function (12 layers): QSA indexer (top-k blocks) + attention + gate + MoE; KV cache + indexer cache interfaces | decode → ~38 ms |
| **3** | PLE + head + tail; the process_ubatch hook; full fused decode | full fused decode + logit-diff validation |
| **4** | Thread-pool integration + gemv/activation micro-opt INSIDE the fused kernels (safe now — no dispatch to lose it) | 30-40 t/s |

Checklist (the dashboard gate — flipped as the phases land):
- [x] Phase 0: logit-dump tool fixed and verified; A/B harness + in-situ profiler established
- [x] Phase 1: fused GDN-layer function committed (`e57e1d542`) — compiles clean, single-threaded
- [ ] Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the hook)
- [x] Phase 3 partial: fused_head + fused_decode_token skeleton committed (`2d699f02c`)
- [x] Phase 2: full-attn layer function committed (`95902fefa`) — QSA indexer + flash-kernel attention; rotations + long-context indexer rope marked for the validation pass
- [x] Phase 3 partial: fused_ple committed (`8fd4c7f15`); head + decode-loop skeleton already in; the process_ubatch hook committed (`99a1c111e`)
- [ ] Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the MoE fix)
- [ ] Phase 4: thread-pool integration + fused-kernel micro-opt

## Validation strategy (learned the hard way — the arch test is self-consistent and cannot see graph-math errors)

1. **Logit comparison** (the dump tool, fixed in Phase 0): fused vs decomposed per-token, ≤1e-4, per layer type, before any perf claim.
2. **Greedy generation test** (Paris-style) — the real gate; every change.
3. **test-llama-archs** — necessary, insufficient.
4. **In-situ profiler** (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — the ONLY trustworthy perf instrument; clean-room numbers have lied 4/4 times.

## Risks

- **Numerics**: the fused op's internal order must mirror the decomposed (bit-exact) or stay within the NMSE — the hc_mix revert (the 2·sigmoid fold bug) is the standing warning: graph-math errors pass the arch test and show as garbage generation.
- **State machinery**: the recurrent/conv state + QSA indexer + PLE interfaces are the hardest correctness surface — Phase 1 deliberately picks the uniform layer type first.
- **The MoE routing** (dynamic expert selection) inside a fused kernel.
- Effort: 4-8 focused sessions; the branch `exp/cpu-fusion-qwen4exp-20260829` and the worktree `/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` are the workspace (champion `270b48ed6` + 4 qwen4exp backports + confirmed fusion ops mean_d1/moe_topk_norm + profiling tooling).

## Phase 0 DONE (2026-08-30) — tooling + fast-path hook design

- Logit-dump tool fixed and verified: `/tmp/qwen4exp-builds/dump_logits2` — the `-1` text_len convention is gone in this API (caused `std::length_error` in `llama_vocab::tokenize`); the two-pass tokenize returns the negative buffer size; the tool now writes the full 248,320 logits to a file for the fused-vs-decomposed diff.
- A/B harness: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — all established from the prior rounds.
- **Fast-path hook design**: `llama_context::process_ubatch` (src/llama-context.cpp:1320) is the single hook point — after the mctx apply, a branch: `model.supports_fused_decode() && gtype == LLM_GRAPH_TYPE_DEFAULT && batch-1 decode && CPU backend` → the fused decode writes the logits into the `llm_graph_result` and returns; the graph machinery untouched otherwise. State access via the memory context (the hybrid-idx cast, like the graph does); weights via the model's layers. The user permitted the direct fast-path blast radius.

## Phase 1 progress (2026-08-30) — foundation committed

- `src/models/qwen4exp-fused.cpp` committed (`6321806b3`): the kernel-mirror helpers (FusedMM, lora_mm, hc_rms_norm_gamma, hc_stream_mean, hc_mix) — each mirrors the graph's exact function/order for bit-exactness. Single-threaded for now (correctness first).
- `e57e1d542` committed the FULL fused GDN-layer function: hc_mix + qkvz + conv state + 4-tap causal conv + l2 norms + the ggml_gated_delta_net kernel (scratch ctx + 1-thread pool) + z-gated rms + ssm_out + fused_moe (softmax router, argsort top-k, topk-norm weights, expert dots, shared expert) + hc_combine x2. Every op mirrors the graph's function/order for bit-exactness. Single-threaded (correctness first). Compiles clean, tree green.
- Next: thread-pool integration (the mms + the GDN kernel at nth>1), then the full-attn layers + PLE + head, then the process_ubatch hook + logit-diff validation.

## Current tree state (starting point)

- Branch `exp/cpu-fusion-qwen4exp-20260829` @ `7cdd7c97b` — clean, arch suite 0 FAILs, "Paris" verified.
- The measurement recipe: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler.
- Decode baseline: ~12.4-14.9 t/s depending on the box state.

## Validation round 1 (2026-08-31) — the hook is wired; five correctness fixes landed; MoE NaN open

- The `process_ubatch` fast-path hook (committed `99a1c111e`, env-gated `GGML_FUSED_DECODE_OFF`
  for A/B): single-token decode on a CPU-resident qwen4exp runs `fused_decode`; any failure or
  unsupported cache type falls through to the graph.
- **A/B harness** (`validation/dump_logits_seq`): one model, two contexts; both decode the prompt
  batch through the graph (sanity: bit-identical, and bit-reproduces the Aug-30 `logits-ref.bin`),
  then 8 single-token steps — the graph ctx (env OFF) drives the greedy token stream, the fused
  ctx runs the fast path; per-step max-abs-diff + NMSE. Graph-only control: clean (0.0 diffs).
- **Five fixes** (commit `9a915a823`, ASAN-verified, `build-asan`):
  1. GDN kernel `wdata` null → segfault; sized scratch `S_v + 16` floats.
  2. `qkv` span: `ssm_d_inner` (6144) is the v-span; `wqkv` writes 10240 → 16 KB heap overflow.
  3. Conv-state staging `rl->ne[0]*4` → the row is `(d_conv-1)*conv_channels == rl->ne[0]`; 4×
     copy-back overrun.
  4. z-gate one scalar per head vs the graph's elementwise `sigmoid(z)`.
  5. `ssm_norm` OOB: `znorm[h*S_v+i]` on a `{head_v_dim}` tensor → garbage → NaN `final_in` →
     NaN router logits → `fused_moe` wrote `probs[-1]`.
- **Full-attn wiring rewrite**: KV/indexer writes were going to local copies at `pos` (OOB and
  lost). The caller now derives the used/visible cells from the cells API (`get_cells` passthrough
  on `llama_kv_cache_context`); the layer writes into the cache views at the current cell
  (n_used-1) and masks the current cell out of the attention; the QSA block path scores the
  visible cells only.
- **FIXED — the MoE NaN (commit `2fcfc5bc1`)**: the IQ4_NL down-expert tensors live in the
  **CPU_REPACK** buffer (8x8-interleaved rows on AVX2; the repack compute handles that layout,
  the plain vec_dot cannot). The fused MoE detects `tensor->extra` and mirrors
  `ggml_gemv_iq4_nl_8x8_q8_0_generic`. Also fixed in the same pass: the conv kernels read
  transposed (tap-fast per `c[i0 + i1*nc]`), the GDN state copy-back froze the recurrence
  (must copy tgd's state region, not ts), the F16 attention/indexer caches (staged F32 view +
  cast-back writes), the IMROPE 4-position format, the rope/flash kernel wdata + threadpool,
  and the meta-only result ctx (logits into the previous graph's sched-known t_logits).
- ~~flash_attn_ext is NaN on this model's real activations~~ — **RETRACTED (2026-08-31
  external audit)**: the NaN was the repro's own staging bug — it staged Q as F16 while the
  CPU kernel reads Q as `const float*` unconditionally (4096 NaNs = 16 overflowed heads × 256).
  The graph never uses flash (flash_attn=false → manual MHA), but the flash staging with F32 Q
  was the better path and will be retried in the ATTN rewrite. The manual `fused_attn_qsa`
  used meanwhile is itself broken (see the rewrite section).
- **Current**: the complete fused decode runs all 8 validation steps without crashing or NaN;
  the per-step logit diff vs the graph is O(10). The same-position layer comparison
  (env-gated dumps) shows layer 0 differs by ~5.8 with identical inputs. The op-id mapping is
  corrected (aae8cae1d): the graph's layer-0 hc_mix runs the MANUAL build_hc_mix (no DSV4
  machinery — no hc_fn tensor), but its rms_norm passes the input through (norm ~1) and the
  gate is effectively 1 — the mixed = the input — while the fused's manual hc_mix (per-stream
  rms → lo/gate → mean) differs. **The first divergence is the hc_mix's rms_norm/gate
  behavior.**
- **The graph's step-1 rms_norm is identity-like** (b0edc7177): the batch decode's rms_norm
  output is properly normalized (-0.0309...), but the step-1's output equals the input exactly
  (norm ~1) — the fused's per-stream rms gives [0.965, 1.81, 1.54, 1.36]. The fused's hc_mix
  diverges at the very first rms_norm.
- **ROOT CAUSE found** (580e0e5ed): the graph's step-1 `hc_init` has DIFFERENT per-stream
  values (rms [0.451, 0.479, 0.153, 0.284]) — the graph's layer-0 input is NOT the embedding
  repeated 4× — while the fused path builds res_hc as 4 identical copies. The graph's rms_norm
  is identity on its input (gamma ≈ 1.05). The stream-dependent input is the root divergence.
- ~~ROOT CAUSE confirmed~~ (f36ea436c / 3fccd0ddf / ac4532bab / 2794abc7f) — **RETRACTED as a
  correctness bug by the 2026-08-31 external audit**: the gallocr mechanism is real (zero-size
  requests alias live free blocks without consuming them; input tensors are freed after last
  use; the gate scalar really overwrites the token's bytes — and the pre-fix allocator is
  byte-identical to upstream), but the graph's only consumer of inp_tokens is node 0 and the
  overwrite happens at node 144+ — nothing ever reads the corrupted bytes. The graph greedy was
  13 hours before the fix and 13 after; the fused path was the diverging side all along. The
  "evidence" was post-compute dumps of memory-reusing buffers (the instrumentation class the
  session had already declared unreliable). The patch changed the debugger's view, not the
  computation: NOT a correctness bug, do NOT upstream it as one; the graph-path validation
  stands. (The fused PLE n-gram predecessor-order fix in 2794abc7f was a genuine fused-side bug.)
- PLE component verification (a56a79cc0): token embed, rows, key, key_n, value are ALL
  graph==fused EXACT (verified via pre-compute eval-callback dumps; post-compute dumps
  read freed memory and were the source of the earlier phantom divergences).
- BREAKTHROUGH (e3ddf1583): the "query weight differs" theory (78922ed81) was IMPOSSIBLE and
  is RETRACTED — both paths dereference the same tensor object; the GGUF ground truth says
  blk.1.ple_norm_query.weight[0] = 0.8261719 (the fused value); the harness's "1.02417" was
  blk.0.hc_ffn_norm.weight[0] picked up by the pattern-matching eval callback latching onto the
  wrong MUL node. The fix in e3ddf1583 was right; the theory on the record was wrong. The
  real bugs — all fixed:
  1) conv windows (GDN ssm_conv + PLE dilated conv) are channel-major (tap k, channel i at
     i*ncs + k); the fused built them column-major (transposed state, wrong tap/channel pairing).
  2) the GDN q/k l2_norm normalizes per ne[0] column (per head); the fused normalized flat once.
  3) the PLE layer is ALSO recr: the graph runs the full GDN+ffn block after build_ple; the
     fused's else-if skipped it.
  Layers 0-2 now bit-exact (l_last 1.3e-7); greedy g=13 f=13 (was 89). Logit diff 7.2 starts
  at layer 3 = the first full-ATTN layer.
- ATTN REWRITE DONE (470730838): the ≥6 audit defects fixed — fused_rope now stages the
  graph's [n_embd_head, n_head] tensor (heads 6-23 were never roped); the q/k/v/wo lora
  scales restored (the pre-rope Q/K divergence); the attention replaced by the graph's OWN
  flash kernel staged with F32 Q (the earlier F16-Q staging was the NaN source — the audit
  was right; flash_attn defaults to AUTO in this tree, so the graph IS the flash path); the
  k/v stage builds AFTER the current-cell write (the pre-write stage read the stale cell —
  the actual source of the 1.2 attention diff); the current cell is attended; the indexer
  uses ratio[il] + the pooled/query ropes.
  Validation: attn_pregate/Qcur/Kcur/Vcur/gate/gated/wo EXACT (max_abs=0) at layers 3+7;
  layers 0-6 bit-exact (l_last 1.3e-7); greedy 13=13; logit diff 7.19 -> 0.684 (nmse 1.7e-2).
- Repack guard INVESTIGATED (79fceb05d): the expert types are all handled (up/gate IQ3_S
  plain, down IQ4_NL repacked-with-mirror or Q8_0 plain; verified via per-call dumps). The
  ~1.6e-4 routed diff at layer 7 traced to the layer-7 ffn-side hc_mixed (2.6e-4) — the
  input to moe2 — while the ffn-side xn is 6.7e-6 (the layer-7 res after the attn-combine;
  the inject/attn_out/res_in all exact). The amplification (6.7e-6 xn -> 2.6e-4 mixed -> 
  1.6e-4 routed -> 1.6e-4 l_last) is the remaining divergence chain — bisection continues
  (the res's 6.7e-6 source is the open question).
- CRASH FIXED (5c575e211): the deterministic crash was the "hc_mix w:" debug print (added
  during the repack investigation) — it evaluated ggml_type_name(w_inject->type)
  unconditionally, and the head's hc_mix is called with w_inject=nullptr — a NULL deref in
  the print, not in the compute. Isolated via the instrumentation-strip test (per the
  2026-08-31 audit follow-up): the gates→0 build passed, the bisect named the print. The
  user's ASAN-vacuity point is confirmed (GGML_SANITIZE_ADDRESS=OFF for libggml-cpu; both
  scratch overflows lived in that blind spot) — a sanitized ggml rebuild is queued before
  the next corruption hunt. Two genuine overflows were also fixed along the way: the flash
  staging's wdata (16 floats short of the kernel's 6976 need) and the GDN kernel's 3.2 MB
  state write past the ne-sized 24 KB scratch tensor. Current state: full-instrumentation
  runs exit 0, logit diff 0.684, greedy 13=13, layers 0-6 bit-exact, layer 7 at 1.6e-4.
- THE SEED FIXED (2c09c1e9e): the IQ4_NL repacked mirror must round PER-K, not per-block —
  the graph's ggml_gemv_iq4_nl_8x8_q8_0_generic accumulates sumf[j] += sumi_k * d * a per k;
  the mirror accumulated the whole sumi and did ONE product per block (~1e-8 rounding).
  With the per-k products: layers 0-11 are now EXACT (layer 7: 1.553e-4 -> 1.341e-7).
- Layer-12 bisection (b494e1599): the GDN body is exact; the ffn diverges via the same
  chain: the ffn-side xn 6.7e-6 (the norm's ~56x of the ~1.2e-7 res) -> the hc_mixed
  4.05e-4 (~60x) -> the up/gate dots 1.3e-3 -> the ffn_out 1.25e-4.
- Silu sites on the graph's SIMD kernels: the PLE conv silu (8f7bc6974 — logit 0.947 ->
  0.6335) and the GDN conv silu (96ec5827a, neutral) use ggml_vec_silu_f32 (the graph's
  ggml_v_silu/ggml_v_expf, 1.45-ulp). The ffn glu's SIMD-silu was NEGATIVE (reverted); the
  PLE gate's SIMD sigmoid was NEGATIVE (c9b0cc488, reverted).
- The ~1.2e-7 seed is still open — the PLE chain: the layer-0's l_last 1.49e-8 (the GDN)
  -> the PLE query_n 4.8e-7 (the norm ~32x) -> the gate dot 8.2e-8 -> the norm_conv 1.9e-6
  -> the padded 4.8e-6 -> the conv_out 1.34e-7 (unchanged by the SIMD silu) -> the l_last
  1.27e-7. Current: logit 0.660, greedy 13=13, layers 0-6 exact; the remaining candidates:
  the gate's dot (the key_n*query_n FMA vs the graph's mul+sum_rows), the query_n's norm,
  or the layer-0's GDN.
- Sequence: logit gate ≤1e-4 → Paris → arch suite stays; no perf claims before it passes.
  Then the honest baseline (uniform IQ4_XS requant control, ~12 min) + one symbol profile of
  the 46 ms non-gemv composition before Phase 4.
- SESSION-OWNED operational note (2026-09-01, operator-ruled, owned by this session):
  ~/.local/share/opencode/opencode.db is ~210 GB (the host's largest file, ~44% of the free
  space after yesterday's 435 GB reclaim; churning tens of GB, not a steady trend — three
  samples 186/224.9/210.3 GB). The plan, owned here: LEAVE ALONE while this session is live
  (held open by pid 433986, actively written). At a natural boundary — the INF-67 ≤1e-4
  gate or a /clear+close — run a maintenance window with the process stopped: back the DB
  up, then VACUUM (needs ~2× transient, only with the free space confirmed), and prune
  sessions only after the campaign's findings are committed, never mid-effort. The
  mechanism hypothesis (tool outputs stored verbatim per message — this campaign moved
  genuinely large artifacts) is worth knowing independently: every large tool output is
  paid for twice. No action taken; not deferred — operator-ruled, tracked here.
- **CLOSED 2026-09-02 — the premise no longer holds; no maintenance needed.** Ownership passed to
  the adhoc-audit session after the INF-67 session was closed. Measured on the live host:
  `/mnt/raid0/users/daniele/.local/share/opencode/opencode.db` is **315 MB**, not ~210 GB; the whole
  opencode tree is **403 MB** (`log` 73 MB, `snapshot` 5.8 MB, everything else under 1 MB). It is the
  ONLY `opencode.db` on the host, and no `.db` anywhere under `/mnt/raid0` exceeds 1 GB.
  - **A VACUUM would reclaim ~0.** `freelist_count = 0` and `auto_vacuum = 0` — the file is fully
    packed live data, no free pages. Occupancy: `event` 260 MB (82%), `part` 27 MB, `message` 21 MB.
  - **Therefore the shrink was not an in-place delete.** With `auto_vacuum` off, deleting rows leaves
    free pages behind; a zero freelist means the file was replaced or vacuumed, not merely pruned.
    Which of the two is NOT determined here — do not record a mechanism that was not observed.
  - **History survived**: 228 sessions spanning 2026-04-28 → 2026-09-02. The campaign-window days
    (08-29 → 08-31) hold no sessions, consistent with that data being what went; 09-01 (83) and
    09-02 (110) are present. The campaign's substance is in git regardless.
  - **Not acted on, deliberately**: a live `opencode` (pid 500205, a DIFFERENT devcontainer — the path
    resolves only via its mount namespace) holds the db/wal/shm open read-write. Nothing was killed,
    stopped or written; the DB was inspected via a throwaway copy. The operator's "no opencode
    sessions open" is true of THIS devcontainer, not of the host.
  - **Policy note for any future attempt**: that path is outside `/mnt/raid0/llm/`, so the filesystem
    containment guard blocks writes to it — real maintenance would need an explicit operator
    `EPYC_FS_ACK`, on top of stopping the holder.
  - **Residual risk: a watch item, not a task.** ~193 of the 228 sessions are from the last two days
    and the `event` table carries 82% of the bytes, so ordinary growth is ~100s of MB/day — immaterial
    against 736 GB free. The original 210 GB was real (three samples) and its mechanism was never
    confirmed, so if a single artifact ever again approaches tens of GB, re-measure before assuming
    the old hypothesis. Do not pre-build maintenance for it.
- SAFETY contract (audit item 3, before any serving exposure): the hook must become OPT-IN
  (today `GGML_FUSED_DECODE_OFF` is an opt-out with `supports_fused_decode()` unconditionally
  true and zero residency checks); all persistent state (PLE history, conv/ssm, KV cells)
  must commit atomically at end-of-token; the t_logits write relies on allocation-ordering
  luck; repack guards on tensor->extra + type; the debug I/O must be stripped before any
  perf measurement.

