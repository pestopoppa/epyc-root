# DeepSeek-V4.1-Flash Evaluation — Completed Scope (compacted 2026-09-26)

Historical ledger only; current work lives in
[`../active/deepseek-v41-flash-evaluation.md`](../active/deepseek-v41-flash-evaluation.md).

**Compacted**: 2026-09-26 (operator-invoked `/wrap-up`, Step 3). Finished (`- [x]`) detail moved out of the
active handoff **verbatim**, grouped under the heading it came from. No open task, gate or key-file location
moved: the one exception to "closed boxes only" is the history of the still-open DS41-C10, whose task text
stays in the active file. The C6 target ladder (a gate) stays active. Three superseded boxes (the `[~]` and `(scope)` DS41-B13 twins and `DS41-T6c (original)`) moved beside the done boxes that replaced them.

Earlier ledger (§C, C0-C19): [`deepseek-v41-flash-evaluation-completed-through-2026-09-24.md`](deepseek-v41-flash-evaluation-completed-through-2026-09-24.md).

## A — Acquisition and reference

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

## B — Port (experimental only; production stays frozen)

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

## K — GLM-5.3 AutoKernel keeps carried to V4.1

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

## B0 follow-on — the work items the audit actually produced

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
- [x] **DS41-B10 — KV-key adapter + arch delta. DONE 2026-09-23** — `experimental/deepseek41-port-20260923` @ `f493088b3` (pushed to fork), 13 files / +550-11, compiled and symbol-verified (`deepseek41.cpp.o`, 11 `deepseek41` symbols, engram tensor names in `libllama.so`). Adds a per-arch KV alias table (a shared-path change worth a review eye), `sqrtsoftplus` string->enum, ratios {0,1,2}, absent hash/nextn defaults, compressor/indexer tensors on the **source-layer** sets, engram tensors declared. `build_arch_graph` **deliberately aborts** instead of inheriting V4's graph, which would silently run plain SWA with the compressor/indexer/engram paths never built. Corrections found while implementing: the GGUF's `compress_ratios` has 40 entries (not 43), `rope_theta`/`compress_rope_theta` are UINT32 and `original_max_position_embeddings` FLOAT32 (type-strict getters, so no name alias), there is **no `rope_scaling.rope_type`** so the generic reader defaulted to *linear* and had to be overridden to YARN, and **no per-block name compat map is needed** — all 36 names already match, only presence differs. ✅ 2026-09-23 — original scope: The artifact's ~67 KV keys are **raw HF config
  names** (`deepseek41.hidden_size`, `.num_hidden_layers`, `.sliding_window`, `.hc_mult`, …), not
  llama.cpp canonical, so load fails in generic `load_hparams` before any V4.1 code runs. Map them;
  convert `scoring_func` string -> our `expert_gating_func` enum; accept `compress_ratios` {0,1,2}
  (today the loader throws on anything but {0,4,128}); supply `hash_layer_count=0`. Subclass
  `deepseek4`: make `output_hc_*`, `ffn_gate_tid2eid`, `nextn.*`, `attn_compressor_ape` and
  `indexer_compressor_*` non-required, move compressor/indexer creation to the *source-layer* sets,
  wire `indexer.attn_k`/`k_norm`, ignore `exp_probs_b_vl.bias`. Note `general.alignment = 16384`.
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

## C — DS41-C10 history (the box itself stays OPEN in the active file)

  **Partial 2026-09-24:** run 7 STOPPED ~10:18 on operator request at iteration 0, 0 measurements
  (`state-run7/STOPPED.txt`). First 27B proposal `akm-q4k-q82x4-weight-prefetch` landed in ~39 min (09:16→09:55)
  but was discarded by an actor-seat defect, and the critic then rejected a repair-fabricated stand-in
  (`src/verify/replay.ts`) — both fixed under DS41-C20. `serial_run` and `run.py` did not exit on SIGTERM and
  `run.py` respawned the actor after its death: stopping needed TERM on the actor, then KILL on `run.py` +
  `serial_run` (root cause and fix task: DS41-C22). Carried to run 8, launched after DS41-C20.
  **Run 8 launched 2026-09-24 13:06:55Z** from research main `21ca61b0` (seat + C22/C23, `--actor-seat plain`),
  `state-run8/serial-run.pid` = 3359620, same store/inputs, floor 5.097 loaded from the cache (no recalibration).
  Launch: from the research root, `EPYC_ROOT_REPO=/mnt/raid0/llm/worktrees/ak-seat-handoffs-20260924
  PYTHONPATH=.:scripts/kernel_rnd:/mnt/raid0/llm/epyc-orchestrator setsid nohup .venv/bin/python -m
  scripts.kernel_rnd.autokernel.loop.serial_run --state-dir …/state-run8 --resolved-campaign …/inputs/campaign-resolved.json
  --owned-targets …/inputs/owned-targets.json --common-args …/inputs/common-args.json --batch-iterations 1 --rounds 0`.
  `EPYC_ROOT_REPO` must name a root checkout carrying the VB-AK-SEAT contract (the shared clone's working tree is
  stale) — do NOT remove that worktree while run 8 runs.
  **Run 8 does NOT carry TD-21.29/30.** They landed on research main as `4915220f` + `34373dd8` (rebased on
  `21ca61b0`; 87 failures, identical to clean `21ca61b0`). The shared research clone stays at `21ca61b0` on
  purpose: each new batch's `run.py` imports from that clone, so a mid-run fast-forward would mix code versions
  across batches (the DS41-C19 mechanism). When comparing run 9 with run 8, note what changes in the actor
  replies with TD-21.29/30:
  - A repaired reply is re-validated against the original schema, so an omitted required field now raises
    `ProviderTransient` instead of receiving an invented value.
  - A fished object with wrong types goes to repair.
  - `actor_preparation` no longer burns its one-shot reservation on a malformed reply.
  - `REVIEW_SCHEMA` rejects extra keys.

  Expect somewhat more transients and fewer silently repaired replies.
  - [x] DS41-C10a — ✅ 2026-09-25 (closed on run 9c's first planner reply, see the end of this box) **Fast-forward the shared research clone to ≥ `34373dd8` only after run 8 stops, before run
    9.** Confirm run 8 is stopped (its `serial-run.pid` tree is dead) before any `git merge --ff-only`; never
    fast-forward mid-run. Acceptance: run 9's launch line names a research commit ≥ `34373dd8`, and its first
    planner reply is read against the semantics above.
    **Blocker found 2026-09-24 (wrap-up):** research main now tracks
    `artifacts/np_context_kvu_study_20260924/{driver,q38_27b_q8,q38_27b_q8_h,q38_27b_q8_depth}/` and
    `artifacts/speech_cpu_realtime_20260924/`, and the shared clone still holds untracked copies of the same files.
    `git merge --ff-only` refuses to overwrite untracked files, even identical ones (checked).
    - The kvu copies are checksum-identical to research `21cf444c`.
    - The speech copies are not: an `smtC` follow-up run kept writing there after the 17:14Z snapshot (RTG-57
      KVU-11a). Commit that delta first.
    - Then, before the fast-forward, `sha256sum -c SHA256SUMS` each copy against the committed checksums, remove
      only the copies that match, and fast-forward.
    - The 35B `q36_35b_a3b_q8_h/` directory is not tracked yet and must be left alone.
    **Prep done 2026-09-24 (~19:00Z):** the speech delta and the 35B directory were committed (research
    `07060eaa`, then `6afc7eed`), the shared clone's untracked copies were moved aside to
    `/mnt/raid0/llm/tmp/research-untracked-backup-20260924`, and the shared research clone was fast-forwarded; it
    is at `6afc7eed` (≥ `34373dd8`, checked with `merge-base --is-ancestor`). This box closes on run 9's launch
    line and first planner reply (its acceptance), not before.
    **Launch-line half satisfied 2026-09-25.** Run 9 launched from the shared clone at `6afc7eed`. Run 9b launched
    from `30631761` (cwd `/mnt/raid0/llm/epyc-inference-research`, read from `/proc`), and both are ≥
    `34373dd8`. Run 9 produced no planner reply to read: its one call was stopped at 61 min and recorded as rc −15.
    **Still open on run 9b's first planner reply** (opencode 3284175, in flight since 04:09Z). Read it against the
    TD-21.29/30 semantics above, then tick.
    **Closed 2026-09-25 on run 9c's reply, not 9b's.** Run 9b never produced one: a misused `STOP` killed its
    planner call after ~18 min (DS41-C28). Run 9c (launched 07:15:54Z from the shared clone at `30631761`) returned
    its first planner reply at 08:05Z: 36.8 min, 29 steps, 31 tool calls, 47.3k decoded, rc 0, schema-valid on the
    metrics row, and a sealed `actor_call.v1` line (not `v1_refused`). Peak context was 111,116 tokens, above the
    old 98,304 split-KV ceiling, so the reply was not truncated. No repair-invented field and no transient on that
    call. Record: `state-run9c/targets/674cc00c…/workers/actor-replies/actor-calls.jsonl` lines 0-1.
  **Run 8 STOPPED 2026-09-24 ~15:32Z** on operator request, for the stack-configuration window (`state-run8/STOPPED.txt`).
  - Why: `run.py` held every CPU region lock through the full-target floor calibration, and that timed out the
    production frontdoor's `/chat` on :8070.
  - State at stop: batch 0 lost its half-screen proposal to a mid-generation slot overflow. The 27B hit
    `finish=length` at the 98,304-token split-KV slot, and the C20 fix refused the empty reply safely, with no
    fabrication. This is the failure `-kvu` removes (RTG-57).
  - Batch 1 was ~2 h into the first full-target floor calibration (48 `matched_process_v2` launches, each reloading
    the 519 GB model). That partial was discarded.
  - Result: iteration 0, 0 measurements. The half-screen floor stays cached.
  - The stop needed KILL: TERM during calibration only drains (DS41-C26).
  - Relaunch as run 9 through DS41-C25.

## C — AutoKernel campaign (completed items)

- [x] DS41-C25 — ✅ 2026-09-25 (acceptance met by run 9c's first planner reply: 111,116-token peak, not truncated; see C10a) **Run 9 relaunch: do the prerequisites in this order.** Floors are bound to the anchor, so any
  anchor advance must land before run 9's first full-target calibration (~4 h per scope).
  1. OP-52 CPU window for the SW-9 spec-accept-probs fix. `experimental/mtp-spec-probs-fix-20260924` @ `2b57340bf`
     is the champion `ak/champion/llama-cpp-ffc1bac82eec` @ `8df1b5cf2` + 1. It needs build + tests + the MTP n_probs
     check + a speed A/B. The operator ADMIT was given 2026-09-24. Its preconditions are met: C1 STT/TTS finished
     17:10Z, and the operator skipped the Flash-Next matrix 17:25Z.
  2. Fast-forward the champion to the fix. This is the TD-21 session's step (SW-9).
  3. Rebase the DS41 port onto the new champion tip. The anchor `ebb68dc55` is a clean descendant of `8df1b5cf2`
     (+6), so the rebase is expected to be mechanical. This step is main-ak-seat's.
  4. Rebuild the anchor. Its first full-target floor calibration is owed (~4 h).
  5. DS41-C10a (shared research clone fast-forward to ≥ `34373dd8`, including the untracked-copy step) and
     DS41-C24 (`EPYC_ROOT_REPO` off the lane worktree).
  6. `-kvu` live on :8083 and `cache_ram` sized (RTG-57 KVU-1 / KVU-2, operator OP-54 / OP-55), so the planner
     gets a 196,608-token slot.

  Scheduling constraint: the full-target calibration holds every CPU region lock for hours and blocks the
  production frontdoor, so agree its window with the operator (OP-41 owns the admission-control design).
  Acceptance: run 9's launch line names the rebuilt anchor, a research commit ≥ `34373dd8`, no lane path, and a
  `-kvu` :8083. Its first planner reply is not truncated at 98,304 tokens.

  Progress 2026-09-24 (prerequisite steps; the parent box closes on the run-9 acceptance above):
  - [x] C25.1 — OP-52 CPU window: the TD-21 session validated the fix (probs 96/96, speed +0.43%, native 16/16).
    ✅ 2026-09-24
  - [x] C25.2 — champion fast-forwarded: `ak/champion/llama-cpp-ffc1bac82eec` = `2b57340bf` (SW-9, TD-21
    session). ✅ 2026-09-24
  - [x] C25.3 — port moved onto the new tip as a clean **merge**, not a rebase: anchor **`5a60152ae`** (merge of
    champion `2b57340bf` into port `ebb68dc55`) on `experimental/deepseek41-port-20260924`, worktree
    `/mnt/raid0/llm/llama.cpp-experimental-deepseek41-20260924`. ✅ 2026-09-24
  - [x] C25.4 — anchor rebuilt: `build-cpu/bin/llama-server` reports `version: 10313 (5a60152ae)`, sha256
    `763e1474f070fdf521f5f64ccbba890db191113fc14a08db6f9682f97f5ed8f7`; ggml linkage PASS;
    `tests/test_speculative.py` 9/9 PASS (7 existing + 2 n_probs), relayed to workspace-8d. Campaign inputs
    re-resolved (request r4): `TARGET_ID ds41-5a60152ae-cpu-t48-dspark-b2`, `verified_resolution`, 0 errors, in
    `campaign-manifest.json`, `campaign-resolved.json`, `owned-targets.json` and the launch/recipe JSONs under
    `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/inputs/`; run-8 inputs backed up to
    `inputs/bak-20260924-run8/`. Run-9 dry run rc=0. ✅ 2026-09-24
  - [x] C25.6 — `-kvu` live on :8083 with `cache_ram` sized (RTG-57 KVU-1 / KVU-2, OP-54 applied 18:45–18:55Z):
    `n_slots = 4, n_ctx_slot = 196608, kv_unified = 'true'`. ✅ 2026-09-24
  - C25.5 is C10a + C24: both are prepared (see those boxes) and close on the launch line.
  - **Both floors must recalibrate** (the anchor changed): ~8.5 h holding every CPU region lock. That overlaps
    the CPU speech cores 0-39 and blocks :8070. **Operator decision 2026-09-24 ~19:40Z: run 9 OFF-HOURS**,
    launched by main-ak-seat late tonight after the wrap-up, state dir `state-run9`. Before launch: the API reload
    for orch `c347600e` (TD-21.33c; `orchestrator_stack.py reload orchestrator`, API only; verify pid lstart >
    commit time).

  **Run 9 / 9b (2026-09-24 20:14Z → 2026-09-25 04:04Z, main-ak-seat).** Acceptance status: the launch line
  satisfies every clause:
  - target `ds41-5a60152ae-cpu-t48-dspark-b2`;
  - research `6afc7eed`, then `30631761`, both ≥ `34373dd8`;
  - no lane path;
  - :8083 `-kvu`, `n_ctx_slot` 196,608.

  The remaining clause, "first planner reply not truncated at 98,304", waits on run 9b's first planner reply
  (in flight since 04:09Z). Tick this box when that reply lands.
  - **First attempt REFUSED.** The store's champion of record was the old port anchor `ebb68dc55`, not the anchor
    `5a60152ae` (0 keeps, 1 experiment row). The operator approved the fresh-store route at 20:14Z, following the
    DS41-C13 precedent:
    - the old store is archived as `store-run8-cor-ebb68dc55/` (`ARCHIVED.txt`; reversible by `mv`);
    - a fresh `store/` carries over `inbox/` (the seeded hypotheses);
    - the refused state dir is kept as `state-run9-refused-cor/`.

    The run-9 dry run (rc=0) did not exercise this check (→ DS41-C27).
  - **Run 9 launched 2026-09-24 20:14:55Z**: `serial_run` 2580766, `run.py` 2580771, `state-run9/`.
  - **Half-screen floor written 2026-09-25 00:25Z**, in `store/runtime-source-floors/5b995a27…/3a0b8832…/`:
    - cores 0-47, `-t 48`, `matched_process_v2`, 48 launches (~4.7 min each);
    - **floor 5.789%** (interval 2.91-9.55%), between-launch SD 2.79%, MDE 3.0%;
    - run 7's floor on the old anchor was 5.097%.
  - **Loop order learned (the pre-launch plan was wrong).** It is: half floor → batch 0 half-screen PROPOSAL and
    its measurement → batch 1 full-target calibration (~4 h). It is NOT both floors back to back (~8.5 h). So the
    full-target calibration comes after batch 0, not overnight (→ DS41-C28).
  - **Run 9 STOPPED 2026-09-25 01:30Z** at the half-floor → batch-0 boundary, for the morning sequence (merge the
    integration lane, then run the INF-78 OAB-9 A/B). The batch-0 planner had been live 61 min on the old inline
    code, and that call was discarded. TERM went to `run.py` 2580771 and `serial_run` 2580766, and everything died,
    including opencode 3054534, with no KILL: **the DS41-C22 stop path worked on a live actor call.** The CPU
    locks were freed, and `state-run9/STOPPED.txt` was written.
  - **Research main fast-forwarded** `170c763c` → `30631761` (the integration lane: `f4a5d240`, `ce5800cb`,
    `0bf2d7c2`, `535391b6`, `8a9d2a40`, `30631761`). The shared clone was fast-forwarded after run 9 was dead.
  - **Run 9b launched 2026-09-25 04:04Z**:
    - `serial_run` 3279632, `run.py` 3279639, `state-run9b/`, same store;
    - default `inline` context mode (the OAB-9 winner), now with `node_profile` and per-call metrics;
    - `EPYC_ROOT_REPO=/mnt/raid0/llm/worktrees/root-main-epyc-root-repo`, a detached checkout of root
      `origin/main` `80c7c1df`, not a lane.

    The half floor was reused: it went straight to the planner call (opencode 3284175, 04:09Z) with no
    re-calibration. **Batch 1's full-target calibration (~4 h, every CPU region lock) follows batch 0's proposal and
    measurement, so it will likely run mid-day. That is a known daytime frontdoor (:8070) impact** (DS41-C28).
- [x] DS41-C28 — ✅ 2026-09-25 (closed as moot by operator ruling, not by building a scheduler) **Schedule batch 1's full-target calibration off-hours.** Run 9b reaches it after batch 0's
  proposal and measurement, likely mid-day on 2026-09-25. It holds every CPU region lock for ~4 h (48 launches
  × ~4.7 min, cores 0-95), which blocks the production frontdoor (:8070) and the CPU speech cores. Options:
  - let run 9b stop at the batch-0 → batch-1 boundary and relaunch in the evening (floors persist per anchor);
  - have `serial_run` hold calibration outside an operator-set window (OP-41 admission control).

  Until one of these exists, the operator is told of the expected daytime impact before it starts. Acceptance:
  the full-target floor for `5a60152ae` is written without a daytime frontdoor timeout.
  - **2026-09-25 04:26Z, a failed first try:** `touch state-run9b/STOP` was meant as a batch-boundary drain, but
    `serial_run` forwards SIGTERM to the running `run.py` as soon as it sees STOP (`serial_run.py` ~L2338). `run.py`
    abandoned batch 0's planner call after ~18 min (`stopped_mid_formation`, 0 measurements). No damage beyond that
    call: floors intact, all processes dead, CPU locks free. The right tools for a boundary stop are the serial
    control plane's `pause` (`serial_control.py`: it completes the current batch, then waits with no child or claims)
    or a bounded `--rounds N`. Decision: no daytime relaunch (the half-screen measurement uses cores 0-47, which
    overlap the speech cores and the frontdoor); relaunch in the evening as `state-run9c` on the same store, so
    batch 0 and batch 1's calibration run overnight.
  - **Operator ruling 2026-09-25 07:15Z, which closes this box:** nothing else uses compute besides AutoKernel,
    so there is no off-hours constraint on the CPU. The premise above (a daytime frontdoor impact to avoid) does
    not hold, so the evening-relaunch decision was wrong, and no window mechanism will be built. A campaign is
    never held or stopped for "off-hours". Cost of the wrong premise: the CPU sat idle 04:26Z → 07:15Z. Run 9c was
    relaunched at 07:15:54Z. Lesson: `docs/guides/agent-workflows/agent-loop-design.md` → *Operating lessons from
    runs 9c-10*.

  **Runs 9c, 9d and 10 (2026-09-25 07:15Z → 15:26Z, main-ak-seat).**
  - **Run 9c** launched 07:15:54Z (`serial_run` 3498589, `state-run9c/`, same store, half floor reused). Its first
    proposal was the Q4_K/Q5_K activation block-scale hoist out of `mul_mat_qX_K_q8_2_X4_T`
    (`iqk_gemm_kquants.cpp`), with falsifiers objdump + bit-identical MUL_MAT + a matched A/B above the floor. The
    Codex critic accepted it twice over two author rounds, and then `gates.op_scope` dropped it before build, with
    no disposition record (→ DS41-C29). Run 9c was stopped ~08:56Z on the operator's order, to free the host for
    the INF-78 OAB-10/11 A/B. The captured pids were dead in 2 s, and `STOPPED.txt` was written.
  - **Run 9d** launched ~10:53Z from research `300951de` (OAB-10/11 + C29 + C30), `serial_run` 348518, `--resume`
    on, control listener `127.0.0.1:8471`. The resumed hoist build failed at 11:35Z with `lane_error
    RatchetRefused` after 6.2 min, and the claim was consumed (→ DS41-C31). Batch 1 (the full-target calibration)
    then ran. Its envelope is cores 0-95, not 0-47 as first assumed. A control-API pause was requested at 12:27Z
    (observed `pausing`), but the calibration batch had not finished when the operator ordered the kill at
    ~14:40Z: TERM drained, and KILL cleared `serial_run` 348518 and `run.py` 417443. The CPU locks were freed, and
    the batch was discarded.
  - **Each calibration launch cost ~3.5 min of single-threaded model load** (~60% of one core, RSS ramping to
    492 GB) plus ~40 s of 48-thread measurement, so the host looked idle ~85% of the time. That led to the fast
    loader (INC-20260925; INF-65 V6R-4) and the re-anchor in DS41-C32.
- [x] DS41-C29 — ✅ 2026-09-25 **The op-scope gate dropped every Q4/Q5 dot-kernel candidate on the DS41 anchor.**
  Root cause: `gates.py` `_iqk_q45_dot_hunks_confined` required `unpack_q4_scales*` markers that exist only in the
  keeps-v10 tree. So `mul_mat_qX_K_q8_2_X4_T` (~30% of cycles) was unreachable on the DS41 anchor: 0 of ~15
  attempts across runs 3-9c ever built. Fix, research `c7215eb5`:
  - the gate admits trees without the keeps helpers;
  - every abandoned candidate is recorded with its retained patch;
  - disposals are logged.

  Retained patches: `store/patches/akm-q4k-x4-actscale-hoist.lane0.{29713a2b,1ea64959}*.patch`; both pass op_scope
  now. The operator's instruction behind it: "investigate why progress gets dropped by autokernel — this is not
  ok". The survey ranked stops as the largest drop class, which is DS41-C30.
- [x] DS41-C30 — ✅ 2026-09-25 **Resume checkpointed work on relaunch.** Research `1ef55655`: on relaunch,
  critic-accepted-unbuilt patches are re-queued to build/gate/measure and interrupted authors to author. Each is
  re-validated (apply, sha, anchor, gates) and resumed at most once, and a stop writes a checkpoint. `--resume` is
  on by default. The backfill tool wrote row `eab36f3e` (gate_refused op_scope, build checkpoint, round-2 patch
  `1ea64959`, sha `bf318caf`); a re-run reports it already present.
- [x] DS41-C31 — ✅ 2026-09-25 **A harness fault must not eat a resumed candidate.** Run 9d's resumed build hit
  `RatchetRefused`: `keep_the_diff` re-retained the patch, and the new sidecar `.json` differed from the immutable
  stored one. Fix, research `71c46655`:
  - reuse the retained patch;
  - an infrastructure `lane_error` releases the claim with a retry count;
  - a `resume reopen` CLI re-opens a consumed claim (`resume reopen eab36f3e…#0 --apply`, run from
    `scripts/kernel_rnd` with `PYTHONPATH=.`).

  Not exercised live: run 9d was killed before its next boundary, and run 10 started on a fresh store.
- [x] DS41-C32 — ✅ 2026-09-25 **Re-anchor on the fast loader and launch run 10.**
  - Anchor `00d118d44` (`experimental/fastload-ds41-20260925`, worktree
    `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925`) = the DS41 port + champion `90c12df42` (fast
    loader). It was rebuilt on the recipe (gcc-15, `build-cpu` version 10316), and `IDENTITY.json` was
    regenerated.
  - Fresh store, route (a) (the DS41-C13 precedent); the old store is archived as `store-run9d-cor-5a60152ae/`.
    The new `store/inbox/` carries the seeded hypotheses and both retained hoist patches (`*.json` + `*.patch`).
  - Inputs re-resolved as request r5 (`verified_resolution`).
  - Code root: the dedicated research worktree `/mnt/raid0/llm/worktrees/research-ds41-run10` @ `67cac838`, not the
    shared clone, which held a peer's uncommitted `actors.py` edits. `EPYC_ROOT_REPO` checkout at root `117370a8`.
  - `serial_run` 2762645, `state-run10/`, launched 15:26Z. `--resume` on; control listener `127.0.0.1:8471`, token
    `/mnt/raid0/llm/tmp/ak-ds41-control-token-run10`; `n_load_threads` auto.
  - **The first calibration launches took 163 / 170 / 167 s, against ~282 s per launch before.**
- [x] DS41-C35 — ✅ 2026-09-26 **Six AK lanes merged to research main `d643d794`.** Author-side lanes
  (`ak-author-medium`, `ak-sandbox`, `ak-bestof`) are recorded in INF-78 OAB-24..OAB-26. The loop-side lanes:
  - [x] DS41-C35a — `ak-scratch`: loop `ScratchRegistry` with iteration and call scopes, a sweep, and an inventory
    guard (later extended to ak-check and the best-of panel). ✅ 2026-09-26
  - [x] DS41-C35b — `ak-keephyp`: `patch_rounds_exhausted` / `scope_blocked` / `hypothesis_retired` outcomes,
    `--hypothesis-author-attempts 3`, resume reinstates; binds the measurement epoch (`3cbdccea`). ✅ 2026-09-26
  - [x] DS41-C35c — `ds41-scope`: `CPU_SOURCE_ROUTES` for `dense_q8_tinyblas`, `iqk_mmid_dispatch`,
    `iqk_dense_dispatch` and `cpu_graph_sync`, plus a gdb witness. ✅ 2026-09-26
  - [x] DS41-C35d — integration fix-ups:
    - `c1fe7750`;
    - `2945b8ef`: one registry, and `--actor-authors-min-free-gb` removed;
    - `3cbdccea`;
    - `a1c5812b`;
    - `4dbab2ce`;
    - `d643d794`.

    `loop/` has 3898 passing, and the failure set is identical to `origin/main`'s. ✅ 2026-09-26
- [x] DS41-C36 — ✅ 2026-09-26 **Planner abstention premise refuted.** Run 10g's planner abstained on every batch,
  citing a ~220 GB/s read ceiling. The measurement: `bench_readbw` 2026-09-26T10:55Z (raw
  `/mnt/raid0/llm/tmp/ds41-scope-20260926/readbw-20260926T105535Z.txt`; `interleave=all`, reps=5; the load average
  at start was 17-21, so this is not an idle-host reading).
  - Full screen, cores 0-95: read-sum 399.6 GB/s at 48 threads and 449.4 at 96.
  - Half screen, cores 0-47: 212.4 at 24 threads and 275.3 at 48.
  - The 220 figure is roughly the half screen at 24 threads, which is wrong for the full screen.

  Serving-shape decomposition (scope agent, in-loop node profile):
  - dense Q8_0 tinyBLAS: 40% of the cycle at ~52% of peak;
  - `MUL_MAT_ID` Q4_K: 32% at 82-94%;
  - barrier/straggler wall: ~21%.

  The inbox note `store/inbox/40-ds41-scope-widening-20260926.md` (with addendum) now drives the planner.
- [x] DS41-C37 — ✅ 2026-09-26 **Run 10g stopped, run 10h launched.**
  - 10g stopped at ~10:5xZ after 13 batches with 0 measurements.
  - 10h launched ~10:57Z on `d643d794` with `--retention-trigger-free-gb 350`, because the disk had 398 GiB free,
    below the default 400 trigger, with nothing reclaimable (→ DS41-C42).
  - The common args gained `--workers 1` (backup `inputs/bak-20260926-workers1/`), which best-of needs.
  - `akm-q4k-x4t-avx512` was reinstated: row `de5eeef007c7…`, at the author stage, with 1 of 3 attempts used, on
    measurement epoch `5225426c…`.
  - At 11:00:30Z it was being authored by two concurrent opencode authors, so best-of-2 is engaged.
- [x] DS41-C38 — ✅ 2026-09-26 **Worktree cleanup.**
  - Inventory: `/mnt/raid0/llm/tmp/worktree-inventory-20260926.md`. The operator approved removing the clean ones.
  - **133 removed without `--force`** (log `/mnt/raid0/llm/tmp/worktree-removal-20260926.log`), 0 refused.
  - 3 moved from SAFE to KEEP because live code references them:
    - `deepseek_v41_flash_recipe.py:180` `KERNEL_SOURCE_ROOT` → `llama.cpp-experimental-deepseek41-20260923`;
    - `autokernel/loop/production.py:93` `BASELINE_TREE` → `tmp/v9v-base-tree`;
    - `dflash2_followups.py:31`.
- [x] DS41-C39 — **First real candidate measurement on run 10h.** ✅ 2026-09-26 — **met on run 10i, which
  succeeded 10h. The candidate was KEPT.**
  - Starting point: at 11:00:30Z run 10h was authoring `akm-q4k-x4t-avx512` with 0 measurements.
  - Acceptance: the first candidate reaches build → gate → measure, and its disposition (keep, reject or refused,
    with its reason) is recorded here.
  - If the planner abstains again with the scope-widening note in its inbox, record the abstention reason
    verbatim. This also carries DS41-C33's hoist acceptance.
  - **Result:** `akm-ds41-gemm4xn-2x-unroll`, a 2x unroll of tinyBLAS `gemm4xN`.
    - It passed critic 2 and every gate at 15:31Z. It was measured in a full-screen paired A/B from 15:32Z.
    - **KEPT at +4.535%** (batch-000001, 204 min).
    - The keep's accumulate bench recorded **+7.304% compounded** against the champion of record.
    - The anchor advanced from `00d118d44876` to anchor-gen-001, `cafb59c3bf67`.
  - **The campaign's first locally-authored AutoKernel keep.**
    - Planner: `qwen-gpu/qwen3.8-27b`, local.
    - Author: best-of-2 on the same local model. The winner was `a0-off` (thinking off): 11 steps, and
      `ak-check` op-test PASS.
    - Critic: external `deepseek/deepseek-flash`.
    - It landed ~57.5 h after the first local planner launched (INC-20260926-local-actor-bringup).
  - **Caveat: serving-measurement variance.** The keep's anchor-guard A/A measured **+19.443%** between two builds
    with IDENTICAL code digests. The loop logged this as an "R21-10 instrument excursion". The serving gate
    (13.81% compounded, or every 4 keeps) is the real confirmation → DS41-C47.
  - DS41-C33's hoist acceptance is **not** met by this keep: the hoist is a different candidate. It stays open
    under C33.
  - Continuing after this keep hit a latent bug → DS41-C45.
- [x] DS41-C40 ✅ 2026-09-26 — Option A (switch both) chosen by the operator and ratified as `P-AK-SEARCH-1-A3.1` (ratify commit 1680efbb, run by the main session on the operator's explicit authorization; receipt `artifacts/operator/ratify_op60_measurement_epoch_20260926.json`). — **Operator decision: move planner-history comparability and the do-not-repeat gate from the full
  epoch to the measurement epoch.**
  - The two epochs:
    - the full epoch folds the actor roster in (`enrolled_manifest_digest` inside `host_state`), so a critic swap
      moved it `e0aefe6a` → `e384c2ad`;
    - the measurement epoch is the same inputs minus actor/backend config, and resume already binds on it
      (`ak-author-medium`, `3cbdccea`).
  - Option A, switch: planner history and do-not-repeat survive actor swaps. Cost: this touches the ratified
    P-AK-SEARCH-1-A3 clause 1 (`measurement/protocols/kernel-research.md`, human-amendment-only), so it needs an
    operator-run ratify script.
  - Option B, keep the full epoch: every actor-config change blanks the planner's history and lets it re-propose
    retired ideas.
  - **Recommendation: A.** A3's text defines an epoch as "anchor commit, build recipe, and declared host state".
    Whether actor config belongs in "host state" is the operator's reading, and that decides whether this is an
    amendment or a clarification.
- [x] DS41-C44 — **Switch planner-history `recall()` comparability and the do-not-repeat gate to the measurement epoch** ✅ 2026-09-26 — landed research `136ad3d0` (epoch_aliases backfill applied to the DS41 store: 4 aliases, 37 rows resolvable, 0 unresolved); live since run 10i. Also fixed: the do-not-repeat gate had never matched a real row (recall rows lacked the epoch keys). (A3.1 clause 1b). Records with no measurement identity fall back to the full epoch (clause 1c). Tests: an actor swap keeps same-anchor measured results visible and blocks re-proposal; an anchor/recipe/host change still separates; legacy rows fail closed. In progress 2026-09-26 on research lane `lane/op60-measurement-epoch-20260926`.
- [x] DS41-C45 — **An experimental CPU campaign must continue past its first keep.** ✅ 2026-09-26 — landed research `eae75696`: experimental continuations record `cor_anchor`; a legacy null chain recovers the COR from the `--resume-run` chain only when exact verification proves it (the tip is never a candidate); the COR check now passes `experimental=`; refusals publish the pre-claim marker; the dry run applies the same COR check. The verified 5.525% floor is reused (no 48-launch recalibration). Hit before in runs 2 and 9 (worked around by moving the store aside). Run 10j relaunched 2026-09-26 ~19:10Z from batch-000001's continuation.
  - Measured at 2026-09-26 17:51Z: after the DS41-C39 keep, the next batch refused with "restored champion of
    record differs from current anchor".
  - Cause: experimental continuations never carry `cor_anchor`. So after the anchor advanced to anchor-gen-001
    `cafb59c3bf67`, the next batch's restore check cannot match the champion of record against it.
  - Effect: every experimental campaign halts at every keep.
  - Fix in progress on research lane `lane/ak-cor-continue-20260926`.
  - Acceptance:
    - a keep followed by the next batch runs on the advanced anchor, with no refusal, in the INF-78 OAB-30 stub
      iteration;
    - the DS41 campaign relaunches from anchor-gen-001 and completes at least one post-keep batch.
- [x] DS41-C49 — **A keep must not orphan pending accepted work (carry-forward).** ✅ 2026-09-26 — research
  `36ebe3a7` + `846bef21`. Unmeasured author/critic1 checkpoints on an ancestor anchor carry forward; patch checkpoints
  rebase to critic2 when the patch applies, else demote to author with the old diff as feedback; another lineage stays
  refused; carries spend no author attempt but add a resume-depth hop. Live on run 10j: Q4_K X4_T carried at author,
  the prefetch patch demoted (its `sgemm.cpp:1535` hunk no longer applies after the unroll keep).
- [x] DS41-C21 — **Hand the seat over as the reference an orchestrator backend must beat.** ✅ 2026-09-24 — plain-seat numbers copied to INF-78 §Baseline; OAB-4 already names `driver.py`; INF-78 gained OAB-7 (context as a REPL variable) and OAB-8 (orchestrator-owned fan-out). Once C20 records
  the A/B, copy the winning arm's five numbers into `autokernel-orchestrator-actor-backend.md` §Baseline
  (INF-78) and point that handoff's OAB-4 at `driver.py`. No further orchestrator work in this handoff: the
  campaign keeps `opencode` + 27B :8083 planner and the cloud critic (operator, 2026-09-24).
- [x] DS41-C22 — **A stop must reap a forming lane's in-flight actor, and never retry it.** ✅ 2026-09-24 Run 7's halt
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
  **Done 2026-09-24, research `1c7d0a2d`** (lane `lane/ak-actor-seat-20260924-followups`, off `e9495971`;
  rides with the C20 seat merge, not on research `main`). `loop.ActorStopped(ActorTransient)`; `_iterate`
  routes propose / critic pass 1 / author / critic pass 2 through `actor_call()`, so a stop mid-call becomes
  the existing `stopped_mid_formation` outcome, still naming the in-flight hypothesis. With the loop's
  `should_stop` (now passed by `run.py` to `AgentPlanner`/`AgentCritic`), `_run_agent` runs the actor in its
  own process group, polls every `STOP_POLL_S` (1 s), and on stop TERMs the GROUP (opencode's MCP server and
  Bun workers included), KILLs after `STOP_GRACE_S` (15 s), records the call and raises `ActorStopped`; a
  signal death while a stop is asked is also a stop. `_with_backoff` draws no attempt and sleeps no backoff
  once a stop is asked, and never retries `ActorStopped`. **Kept as today, deliberately:** rc < 0 with NO stop
  asked is still a retried transient — an operator killing one hung actor, or earlyoom, wants the call
  retried; only a stop of the run means "do not relaunch". Only forming stages make actor calls, so the tail
  holder's drain is unchanged; `serial_run` already TERMs `run.py` and waits for its drain, which now ends
  promptly. Tests: `test_actor_stop.py` (11, real child + grandchild processes: the whole group dies, the
  planner launches exactly once, no backoff is slept, rc −15 without a stop stays a transient).
- [x] DS41-C23 — **`symbol_annotate` must resolve the short symbol name the planner actually types.** ✅ 2026-09-24 Run 7's
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
  **Done 2026-09-24, research `1c7d0a2d`** (same lane as C22). On "no samples", the typed name is resolved
  against the DSO's `perf report --sort symbol` rows: exact, else ONE symbol with the same core (no
  `(anonymous namespace)::`, return type, argument list or whitespace), else one substring match; several →
  the candidate list with overheads, never a guess between template instances (`<Q4K, 1>` vs `<Q4K, 2>`). An
  exact name still costs one perf call. The one allowed read-only smoke against the run-7 profile (3.7 s)
  found a second defect: perf 6.17 appends `IPC  [IPC Coverage]` columns (`-      -`) to `--sort symbol` rows,
  so the parsed name carried them and the resolved annotate missed. Fixed (the name ends at the first double
  space) and pinned by a test on that verbatim row shape; not re-smoked (one invocation was the budget). Tests:
  9 new in `test_actor_tools_mcp.py` with the real run-7 symbol names.
- [x] DS41-C24 — ✅ 2026-09-25 — acceptance met:
  - run 9's first `actor-calls.jsonl` line is `epyc.autokernel.actor_call.v1` (planner, rc −15 at the 01:30Z stop,
    `seat.arm` plain);
  - no launch line carries a lane path;
  - run 9b's `EPYC_ROOT_REPO` (read from `/proc`) is `/mnt/raid0/llm/worktrees/root-main-epyc-root-repo`, a detached
    checkout of root `origin/main` `80c7c1df` that carries the capture module.

  From run 9b on, the metrics line precedes each v1 line, so check the first `actor_call.v1` line (below).
  **Release run 8's pin on a lane worktree for `EPYC_ROOT_REPO`.** Run 8 reads the VB-AK-SEAT
  call-record contract from `/mnt/raid0/llm/worktrees/ak-seat-handoffs-20260924` because the shared clone's working
  tree (`/workspace`, the default) predates root `ee0d48f1`; that lane worktree is frozen while run 8 runs. Before
  run 9: point `EPYC_ROOT_REPO` at a root checkout that follows `origin/main` (the shared clone once its working tree
  carries `scripts/vidya/adapters/autokernel_actor_seat_capture.py`), drop the override from the launch recipe
  above, then remove the lane worktree (`git worktree remove`, never `--force`/`prune`). Acceptance: the run-9 launch
  line has no lane path and its first `actor-calls.jsonl` line is `epyc.autokernel.actor_call.v1`.
  **Prep done 2026-09-24:** the shared root clone `/workspace` carries
  `scripts/vidya/adapters/autokernel_actor_seat_capture.py`, so run 9 needs no `EPYC_ROOT_REPO` override, and the
  lane worktree `/mnt/raid0/llm/worktrees/ak-seat-handoffs-20260924` was removed (clean, on origin; plain `git
  worktree remove`). Closes on the run-9 launch line.
  **Watch the acceptance wording after DS41-C20h.** Once the metrics lane (`0bf2d7c2`) is merged, every call writes
  an `epyc.autokernel.actor_call_metrics.v1` line just BEFORE its `actor_call.v1` line. From then on the literal
  "first line is `actor_call.v1`" is false by design, so check the first `actor_call.v1` line. Run 9 was launched
  from pre-merge code (20:15Z) and has written no actor call yet (calibration), so its check is unaffected.

## C — DS41-C20 and its closed children (open C20d, C20f, C20g stay in the active file)

- [x] DS41-C20 — **Bounded opencode seat: merge gate.** ✅ 2026-09-24 — merged to research main `21ca61b0`
  (seat `e9495971` + follow-ups `1c7d0a2d`), `--actor-seat` default **plain** per the A/B verdict below (operator
  decision); run 8 launched from the merged tree (acceptance iii). Research worktree
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
  `run.py --actor-seat {bounded,plain}` (default `plain` on main, `bounded` on the lane), `--actor-fan-out`, `--actor-steps`; per-call
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
  verdict (C20c): PLAIN is the default.** One pair on the 27B, same prompt: **plain** 31.9 min, 23 steps, 25 tool
  calls, 57.7k decoded, 1 compaction, schema-valid (`unknown_source_screen`: keep `d8` scales in registers in
  `mul_mat_qX_K_q8_2_X4_T`); **bounded v2** 44.3 min (`wall_s` 2658.7), 34 steps, 35 tool calls (8 on the MCP
  tools), 60.2k decoded, 1 compaction (step 32), schema-valid and better grounded (`akm-q4k-x4-load-hoist`, cites
  `symbol_annotate`'s hottest instructions: q2/q3 loads + `vpsrlw $4` at 13–14% of the symbol). Bounded's wall loss
  is tool time, not decode: its perf-backed tools re-run `perf report` over the 25 MB profile per call (one 266 s
  step decoded 611 tokens; 22.6 vs 30.1 tok/s effective). Neither arm used a scout (the `task` tool was offered and
  allowed — `opencode debug agent` — but the 27B never considered delegating). The prompt fixes alone took the
  plain seat 40.3 → 31.9 min. n=1 per arm: a direction, not a magnitude.
  Acceptance: (i) A/B result recorded here
  with steps / tool calls / decoded tokens / wall / compactions per arm and the schema-valid verdict of each
  reply; (ii) committed on the lane and merged to research `main` only if `bounded` is not worse on wall AND
  yields a schema-valid hypothesis — otherwise keep `plain` as default and record why; (iii) the next
  campaign run launched from the merged tree, never from the worktree.
  - [x] DS41-C20a — seat committed on the research lane (`e9495971`, 8 files, 167 tests green) and the lane
    pushed as a backup; research `main` untouched pending (ii) ✅ 2026-09-24
  - [x] DS41-C20b — bounded v1 arm run and stopped; numbers above; its failure produced fixes (3)–(5) ✅ 2026-09-24
  - [x] DS41-C20c — plain (new prompt) and bounded v2 arms recorded above; default plain ✅ 2026-09-24
  - [x] DS41-C20e — ✅ 2026-09-25 — fixed in both context modes by research `8a9d2a40` (merged to main
    `30631761`). The new inline control prompt is 79,890 chars, sha256 `a265a03a…`. **`render_context` never prints `node_profile`**, although the program directive tells the
    planner to "Read node_profile". Found building `ce5800cb`. Fix it in BOTH context arms (inline and variable)
    before the INF-78 OAB-9 A/B, so the two arms stay comparable; it changes the inline control's prompt, so record
    the new prompt sha. In flight on the integration lane `lane/ak-planner-integ-20260924`.
  - [x] DS41-C20h — ✅ 2026-09-25:
    - run 9 was stopped at 01:30Z, at the half-floor → batch-0 boundary;
    - `lane/ak-planner-integ-20260924` was merged, fast-forwarding research main `170c763c` → `30631761`, and the
      shared clone was fast-forwarded after run 9 was dead;
    - INF-78 OAB-9 ran, and inline won;
    - run 9b was relaunched from the merged tree at 04:04Z on the default `inline` (C25's run 9 / 9b block).

    **merge the three reduced-scope lanes and relaunch.** At run 9's calibration boundary (~04:45Z),
    stop run 9 (floors persist per anchor). Merge `lane/ak-planner-integ-20260924`:
    - `ce5800cb`, `0bf2d7c2` and `f4a5d240`;
    - the C20e fix;
    - the pre-existing test fixes on research `origin/main`: the `oracle()` stand-ins lack `require_reference`
      after `37d326ac` (`test_loop_cpu_profile.py`, `test_shared_history.py`), and the `test_shared_history` WAL
      `-shm` mtime failure.

    Then run INF-78 OAB-9 and relaunch with the winning arm. Launch from the merged tree, never from a worktree.

## C6 — Targets (operator, 2026-09-23) and the arithmetic behind them

- [x] DS41-C8 — **The per-node profiler is compiled in at last.** INF-70 built it and there was
  never a CMake option, so it has never been in a binary we shipped: `strings libggml-cpu.so |
  grep -c GGML_CPU_PROF` returned **0**. Now `-DGGML_CPU_PROF=ON` in a separate `build-prof/`
  tree, verified by `GGML_CPU_PROF_JSON_FILE` (2 hits) and `LLAMA_HOST_PROF_JSON_FILE` (1). The
  measured build is untouched. ✅ 2026-09-23

## T — Gates (translated from INF-69 T0-T4 / T0-SPEC / T15)

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
