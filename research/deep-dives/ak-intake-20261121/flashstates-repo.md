# Stage-2b dive: FlashStates, Unlocking Flexible Hybrid State Management for Agentic LLM Inference (repo, intake-2772)

- **Source read:**
  - The README at `FutureMLS-Lab/FlashStates` @ `e3ff1fdb46e560ef1b1755662727ae2f1e83b23a` (flashstates-repo/extracted.txt, in full). It is the anchor text.
  - Clone (depth 1, same SHA) at `extra/flashstates/`: read `docs/what-flashstate-changes.md` and `docs/how-the-image-is-built.md`.
  - The submodule pins: vllm `3cfd432cd83a`, mooncake `59ca03f3c441`. The vLLM fork is one squash commit, "FlashStates for vLLM v0.33.0", and I listed its 120 changed files via the GitHub API. From it I fetched `docs/design/hybrid_state_checkpoints.md` (196 lines) and `vllm/v1/core/hybrid_checkpoint/export.py` into `extra/flashstates-vllm-3cfd432/`.
- **read_depth: PARTIAL.** README, the two docs and the fork design doc were read in full. Not read:
  - `docs/FlashStates_Release.pdf`: no PDF text extractor on the host (pdftotext/pdftoppm/pypdf absent), so its export-kernel measurements are unread.
  - The CuTe DSL export kernel (`vllm/third_party/flashinfer_gdn/gated_delta_net_chunked.py`, 5,501 lines) and the FlashKDA `.cuh` files.

  The mechanism below comes from the fork's design doc, which is not anchorable. The anchors are README only, as the brief requires.
- **lane_head:** ac1347f5d3218531bb369c286837630bf842ff74. In-house cites: lane `@ ac1347f`; fork code read-only from C17 `ed5d94969`.
- **Bearing dive:** `2611.26020v1/dive.md` (FrontierReplay, intake-2758). It asked:
  - what "in-kernel state export" is;
  - whether export is a cheaper route than replay for llama.cpp turn-boundary checkpoints;
  - its HIP/CPU portability.

## Verdict
**dive-verified (narrowed).** FlashStates is a vLLM v0.33.0 + Mooncake fork with three default-off mechanisms:

1. **Frontier checkpoints.** Keep a finished request's running state at its exact end. Decode passes every position, so this is free; the fork also snapshots the state at the last block boundary the output crossed.
2. **In-chunk state export.** A non-final prefill chunk runs *past* a position where a state must be cached, and the backend's own chunked-prefill kernel writes the state at that offset into a workspace row. There is one export position per request per step, 64-token aligned for GDN and 16 for FlashKDA.
3. **GreedyDual-Size eviction** of whole recovery units (a state plus the pages only it needs), with leaf-last tiers and an optional Mooncake host tier.

Two caveats on the claims:
- **The README headline numbers are vendor-measured.** They are closed-loop replays of SemiAnalysis coding-agent traces on 2× B200 per engine (and a GB300 Kimi run). They are not re-derivable here.
- **The export kernels exist only for SM100** (compute capability 10.0, CuTe DSL; FlashKDA built for 10.0f/10.0a). Elsewhere vLLM keeps upstream's checkpoint paths.

**FrontierReplay never ran FlashStates.** Its §6.4 compares against its own "multi-target in-kernel state export (M_cap = 8, inspired by FlashStates)". So "export beats replay by 1.5-2.5% on fine-chunk GDN" describes FR's reimplementation, not FlashStates. FlashStates' real export is single-target per step (FR's own §7 says so too).

**For llama.cpp the answer to the bearing question is: export is the cheaper route.** Turn-boundary checkpoint targets in our server are known before the batch is built: user-message starts, reorder junctions, n−(4+n_ubatch), n−4 (`server-context.cpp:5297-5333 @ ed5d94969`). Each target currently *ends the batch* (a cut). An export writes one extra state copy inside the forward:
- 27B: 48 × 3 MiB + conv ≈ 150 MiB, ~0.1 ms on the MI210.
- That copy is needed anyway for the host checkpoint.

Replay instead needs F32 input logs (~1.55 MiB/token on the 27B) plus a replay kernel. Replay wins only when the target is not known at forward time (FR's dynamic targets), which our server does not need. FR's objections to export are that it modifies native kernels, adds CUDA-graph signatures, and couples cost to coarse tiles. They weigh little for us: we own the ggml kernels, our CPU and HIP recurrent GDN paths are token-granular, and the HIP chunked path's tile is 64.

## Claim verification

| # | Claim (bearing dives / README) | Status | Evidence |
|---|---|---|---|
| 0 | "Arbitrary state checkpointing" at any token position: end of prompt, inside a long prefill, end of request | CONFIRMED, NARROWED | README ASC bullet. Design doc: end-of-request = the exact running state (any position). Inside a prefill = export at a **64-token-aligned** (GDN) / 16-aligned (KDA) offset on the prefix-cache grid, one per request per step. With no export, or off-grid, the chunk is still cut. So "any token position" holds for request ends, not for in-prefill positions. |
| 1 | Up to 3.02× decode, 3.14× prefill throughput, −96% median uncached tokens, −88% p90 TTFT vs vLLM | CONFIRMED as stated (vendor) | README Results: GLM-5.3-Flash NVFP4, 48 sessions, 2× B200 per server. The vLLM baseline recomputes the previous turn's tail from block-boundary checkpoints. Kimi-K3.1-Pro GB300: +36% output throughput/GPU, p90 TTFT 2.0 s vs 9.1 s. |
| 2 | FR dive: "FlashStates' export wins 1.5-2.5% on fine-chunk GDN, loses on coarse-tile Mamba-2" | **REATTRIBUTED** | FR §6.4 measured FR's own M_cap = 8 multi-target export "inspired by FlashStates" (538 LOC, 3 kernels) on vLLM 0.30.0/A800. FlashStates is single-target per step and SM100-only. FR's comparison does not measure FlashStates. |
| 3 | "In-kernel export" is a cheaper route than replay for checkpointing at turn boundaries | CONFIRMED for llama.cpp (our analysis) | Design doc: "no extra prefill runs and the chunk is not cut". Exported state is bit-identical to "the final state of its sequence cut at the offset" (invariant 1). Our targets are known pre-batch (code cited above). |
| 4 | HIP/CPU portable | **Code: no. Principle: yes** | Kernels are CuTe DSL with 2-CTA clusters, SM100 only. The principle maps directly onto ggml (see Principles). |

## What "in-kernel state export" is (from the fork design doc, unanchored)

- **Scheduler side.** The scheduler plans each non-final chunk so it contains at most one cache position (`export.plan_export`). If the backend can write it (`is_mamba_prefill_checkpoint_valid`), the chunk runs past it, and `prefill_checkpoint_positions` flows to `compute_mamba_prefill_checkpoints`.
- **GDN.** A vendored FlashInfer chunked kernel writes each exporting sequence's state at its own offset into a workspace row. The rows are then copied into cache blocks. When few sequences leave SMs idle, (sequence, value head) runs as two half-row tiles in a 2-CTA cluster.
- **KDA.** FlashKDA stores the checkpoint and final state from registers.
- **Invariants:**
  1. Output and final state are bit-identical to the no-export call.
  2. Offset 0 exports nothing.
  3. Calls without offsets run the original kernel.
  4. Offsets are aligned to the layer's grain.
- **Cost caveat stated in the doc.** A long single sequence that exports must take FlashInfer's non-context-parallel route, "which can be slower than the context-parallel route".
- **Separate mechanism, `--mamba-spec-state-layout compact`.** It writes no per-draft states and folds accepted updates after sampling, using upstream RecoverSSM verify/commit, "the mechanism Kimi-K3 uses under `--use-replayssm`". It is the ReplaySSM/PR31669 family, and pr31669-A1 already covers it.

## Mapping onto llama.cpp (C17 `ed5d94969`)

- **End-of-request frontier.** Already integrated in our champion. PFXC-A1 (`checkpoint_after_gen`, default on in C17, `common.h:666`; kernel-champion-and-promotion.md:35) checkpoints the slot at the end of every generation. Its row filed a pass: +3.00 hit-rate points, prefill 0.914×. **Production v10 `ffc1bac82` lacks it** (`checkpoint_min_step` = 8192, no flag). So the FR dive's "creates none during generation" (UFH14-A7, a v10 code read) is stale for C17.
- **In-prefill export: we already have a restricted form.**
  - `ggml_gated_delta_net(..., K)` writes K snapshots for the **last K positions of the ubatch** (`ggml.h:2694-2696 @ ed5d94969`).
  - The C8-6 chunked kernel processes the last K tokens as single-token chunks precisely "so every per-token snapshot the cache keeps is materialised exactly" (`gated_delta_net.cu:37-38`).
  - With speculative decoding on (n_rs_seq ≥ 4: MTP d4, DFlash2 n_max 7), the state "4 tokens before the end" plausibly already sits in snapshot slot 4 after the last prompt ubatch. If so, the n−4 cut is redundant whenever spec is on.
  - This is not verified here. It needs a code read of the snapshot retention through `find_slot`/`seq_rm`, and the conv snapshot must also exist.
- **Mid-prompt checkpoints** (user-message starts, junctions, n−(4+n_ubatch)) would need a true export:
  - **CPU op:** a per-token loop, so writing the state at any offset is a store of a register/L2-resident tile.
  - **HIP recurrent kernel:** the same, token-granular.
  - **HIP chunked kernel:** the inter-chunk state is materialized in-scan at every 64-token boundary, so a 64-aligned export costs one extra state store. FlashStates' 64-token GDN grain is the same constraint.
  - The ggml surface: an optional I32 "export offset per seq" input plus an extra output region.
  - Whether cuts are worth removing is exactly 2611.26020v1-A2: count the cuts and price them from existing logs.
- **Wave64 / LDS notes for a HIP export.** No cross-lane changes are needed. The state is already held per column-block (1 col per warp in our recurrent kernel; 16 × NC columns per block in C8-6). Export adds one global store per state tile at the chosen boundary: no `__ballot`, no LDS, no MFMA change. The 2-CTA cluster split has no gfx90a equivalent and is not needed at our np ≤ 4.

## Principles

| Principle | Source evidence | MI210 gfx90a | Zen 5 CPU | Port cost | EPYC consumer |
|---|---|---|---|---|---|
| Keep the exact end-of-request state (frontier); decode passes every position so it is free | README ASC; design doc "Frontier checkpoints" | Already in C17 (PFXC-A1) | Already in C17 | — (done) | PFXC-A1 (kernel-champion-and-promotion.md:35) |
| Export a cached state from inside the forward instead of cutting the batch; bit-identical to the cut-at-offset final state | design doc "In-chunk state export", invariant 1 | Recurrent kernel: any offset. C8-6 chunked: 64-aligned boundary store. Last-K positions are already exported via K snapshots | GDN op is a per-token loop, so any offset is one state store | S (last-K reuse) / M (true mid-prompt export op input) | kv-cache-program.md; 2611.26020v1-A2; UFH14-A7 |
| Evict a state together with the pages only it needs, by prefill-saved per freed block (GreedyDual-Size, leaf-last) | README cost-aware bullet; design doc GDS | Applies to llama.cpp host-RAM checkpoints only under pressure | same | S | decline now (2611.26020v1-A4: pool not binding, KPF-64) |
| Compact spec-state layout: no per-draft states, fold accepted updates after sampling | what-flashstate-changes.md | = pr31669-A1 | same | — | pr31669-A1 |

## Grounding vs current EPYC state
- **Checkpoint placement and cuts:** `server-context.cpp:5297-5333 @ ed5d94969`. It breaks at user-message starts (min step 1024 after PFXC-A1), at reorder junctions, and at n−(4+n_ubatch) and n−4. Checkpoints are host copies (`create_checkpoint`, L3325) capped at 32 per slot, and PFXC-A2 keeps the oldest anchor.
- **Generation-end checkpoint:** C17 yes (PFXC-A1), v10 no. UFH14-A7 (harness-program.md:2991) and its p3 "generation-time checkpoints every N tokens" (harness-program.md:3023) were scoped from a v10 code read. Re-check them against C17 before building.
- **K-snapshot op and C8-6 last-K materialization:** `ggml.h:2694-2696`, `gated_delta_net.cu:37-38 @ ed5d94969`. No explicit export-offset input exists. Searched: the `ggml_gated_delta_net*` declarations in `ggml/include/ggml.h` and `ggml/src/ggml-cuda/gated_delta_net.cu`.
- **Retention:** KPF-64 (kv-cache-program.md) found checkpointing is the whole effect at 4 sessions / 4 slots, so eviction policy is not binding (per the FR dive).

## Adversarial pass (1 search)
- "FlashStates FutureMLS-Lab hybrid state checkpoint vLLM" finds one secondary aggregator page that restates the README numbers (3.14× prefill, −88% TTFT) and claims SGLang adopted the cost-aware eviction (restatement, unverified). There is no independent replication or criticism; the repo is days old.
- Internal caveats:
  - Every figure is the authors' own replay on B200/GB300 with NVFP4/FP8 weights.
  - The baseline vLLM align mode is the known-weak block-grid policy (the same baseline FR beats).
  - Export forces the non-context-parallel route for long single sequences.
  - Frontier checkpoints are refused with ReplaySSM, KV events and context parallelism. So FlashStates' frontiers and ReplaySSM spec decoding do not compose in that fork; only the compact layout does.

## Derived-actionables ledger

| id | action | owner | bears on | disposition |
|---|---|---|---|---|
| flashstates-repo-A1 | Code read plus design note. With spec on (n_rs_seq ≥ 4), does the last prompt ubatch's K-snapshot set (GDN slot 4 + conv snapshot) already hold the n−4 state, so the n−4 batch cut can be replaced by copying the snapshot slot into the checkpoint (export for free, no kernel change)? If yes, file the experimental change with the PFXC resumed==fresh unit as its gate | handoffs/active/kv-cache-program.md | 2611.26020v1-A2, UFH14-A7 | task |
| flashstates-repo-A2 | GDN export-offset op input: per-seq I32 offset, extra state output. CPU per-token, HIP recurrent per-token, C8-6 at 64-aligned boundaries. Invariant tests: output/final state bit-identical to no-export; export bit-identical to cut-at-offset. Replaces mid-prompt cuts at user-message starts | handoffs/active/kv-cache-program.md | 2611.26020v1-A2/A3 | task, gated on 2611.26020v1-A2 showing material cut cost; supersedes the replay route of 2611.26020v1-A3 for known targets |
| flashstates-repo-A3 | Re-scope UFH14-A7.p3 (generation-time checkpoints every N tokens) against C17, which already checkpoints at end of generation (PFXC-A1) | handoffs/active/harness-program.md | UFH14-A7.p3 (:3023) | task (note) |
| flashstates-repo-A4 | Frontier (end-of-request) checkpoints | — | PFXC-A1 | decline: already integrated in C17 (default on); v10 lacks it, promotion is operator-only |
| flashstates-repo-A5 | GreedyDual-Size recovery-unit eviction, leaf-last tiers, Mooncake tier | — | 2611.26020v1-A4 | decline: KPF-64 shows the checkpoint pool is not binding at our load; Mooncake is not in our stack |
| flashstates-repo-A6 | Port the CuTe DSL / 2-CTA export kernel | — | — | decline: the principle ports as A1/A2 into our own kernels; the SM100 cluster split solves an SM-occupancy problem we do not have at np ≤ 4 |

## Dive-surfaced sources
- `FutureMLS-Lab/vllm` @ `3cfd432cd83a`, `docs/design/hybrid_state_checkpoints.md`. This is the primary mechanism text (export planning, kernel invariants, requirements) and the only primary description of export. **ingest-and-dive** (as a companion artifact, so the export claims become anchorable).
- `FutureMLS-Lab/FlashStates/docs/FlashStates_Release.pdf` @ `e3ff1fdb46e5`. It would settle the export-kernel overhead numbers and ablations (unread: no PDF extractor on host). **ingest-and-dive** once the PDF can be extracted.
- arXiv 2609.15030 (GLM-5.3-Flash hybrid-state cache recovery, vLLM + LMCache; search result). **decline:** GLM/LMCache-specific.

artifact audit: clean
