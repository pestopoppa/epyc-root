# Stage-2b (wave 3) dive: FlashStates_Release.pdf, "FlashStates: Unlocking Flexible Hybrid State Management for Agentic LLM Inference" (intake-2788)

- **Source read:** `w3/FlashStates_Release.pdf`, sha256 `8bb41e1b8b3331dab13c9fdd71c918f4f4490871d1c51cdffd3b9e34abb4ada3`, 32 pages, pdfTeX. Fetched from `FutureMLS-Lab/FlashStates` @ `e3ff1fdb46e5…/docs/FlashStates_Release.pdf`. Authors: Chenxi Li, Weili Xu, Tianyi Zhang, Jue Wang, Zhongzhu Zhou, Chenfeng Xu (Together AI, UIUC, UT Austin).
- **How it was read.** The Read tool cannot render PDFs on this host (pdftoppm absent). Installing pypdf was denied. The text was instead extracted with a small stdlib-only parser (zlib + object streams + content-stream text operators) written in the session scratchpad. That parser covers:
  - all 32 pages of body text: §1-§6, references, and appendices A-J including every proof;
  - Tables 1-7, which are text and were read in full;
  - the text labels inside the vector figures (Form XObjects): Figures 4, 5, 6, 7, 8, 9, 10 and 12.

  Not readable: figure data points beyond their printed labels (curves in Figures 2, 5, 6, 8, 10 and 11). Some equations and inter-word spaces are garbled by the extraction.
- **read_depth: PARTIAL** (figure curves; the brief's UNANCHORABLE rule). **verification: stage1-unverified.** Anchors are MANUAL, checked against the extracted text of this exact PDF.
- **lane_head:** 4b428f15153d0a32b37e6302849691b2212a49ab. In-house code cites are the C17 `ed5d94969` copies in `extra/`.
- **Bearing dives read first:** `flashstates-repo/dive.md` (intake-2772), `2611.26020v1/dive.md` (FR, intake-2758), `pr31669/dive.md`. Plan boxes: P1 (RS-REPLAY-*, KPF-64-CUTS, KPF-64-SNAPSLOT-READ, FR-UFH14-DIVERGE) and the M2 monitor.

## Verdict
The paper is the system and evaluation write-up behind the repo, and it settles the three open questions.

1. **Measured numbers.**
   - Hardware: NVIDIA B200, 2 GPUs per engine, TP2.
   - Baseline: vLLM at commit ec8a372 (0.32.0rc1.dev105) in align mode. FlashStates is built into the same build. The release fork is vLLM v0.33.0 (README), which is a different version.
   - Workload: SemiAnalysis Claude Code traces replayed closed-loop with recorded tool times.
   - Models: GLM-5.3-Flash NVFP4 (KDA), Qwen3.8-Flash-Next FP8 (GDN, the family of our Q38FN), Nemotron 3 Super FP8 (Mamba-2).
   - At 48 sessions (Fig. 5 labels):

     | Model | Decode | Prefill | Median uncached tokens | p90 TTFT |
     |---|---|---|---|---|
     | GLM | 3.02× | 3.14× | −96% | −88% |
     | Nemotron | 2.32× | 2.27× | −97% | −77% |
     | Qwen3.8-Flash-Next | 1.54× | 1.54× | −66% | −79% |

   - The gain tracks the baseline's block size (3,136-8,320 tokens). "FlashStates lowers the median uncached tokens per request by about 70% of a block relative to vLLM." It is a cure for vLLM's block-grid placement, which llama.cpp does not have.
2. **Export kernel design (App. H, Algorithm 1).**
   - Signature: PrefillExport(X, S0, c) → (O, S_final, R_c), one offset per sequence per prefill call.
   - KDA exports at a 16-token tile boundary.
   - GDN supports **16-aligned offsets inside its 64-token tiles**. For an interior offset, it builds the state from the tile's pre-state and the tile's own intermediates with one bounded local prefix update (PrefixState). The main recurrence is left untouched.
   - Overhead is stated only asymptotically: one 4·d_S-byte fp32 output, Θ(d_S) work (KDA), or one local prefix update (GDN). **No measured export overhead appears anywhere.**
3. **GDN export was never used in serving.** "In the main serving experiments (Section 5), in-chunk export is enabled only for the KDA kernel backend of GLM-5.3-Flash." Qwen3.8-Flash-Next (GDN) and Nemotron use exact request-completion capture only. **Every GDN-model gain in the paper therefore comes from end-of-request capture plus admission/eviction**, which is the PFXC-A1 part we already have in C17. No GDN result measures export.

**Does this change the plan's export-vs-replay choice? No, it sharpens it.**
- The choice stays structural: export when targets are known before the batch, replay only for targets that are not.
- llama.cpp's four checkpoint targets are all known before the batch (`c17_server_context.cpp` L5297-5333).
- The paper provides no measured case for either route on GDN. So the export route must stay behind KPF-64-CUTS. The M2 text should, however, stop tying export to RS-REPLAY-PORT and should name the kernel form, which is the prefix update.

**KPF-64-SNAPSLOT-READ is untouched by the PDF.** The PDF has no speculative per-position material. The design doc (intake-2787) gives the precedent for it, and the pricing caveat comes from our own code (the n−4 cut adds an iteration but no ubatch).

## Claim verification

| # | Claim (intake-2772 / plan / README) | Status | Evidence (PDF) |
|---|---|---|---|
| 0 | Up to 3.14× prefill, 3.02× decode, −88% p90 TTFT vs vLLM | CONFIRMED, NARROWED | GLM-5.3-Flash NVFP4, 1M context, 48 sessions, 2×B200, vs vLLM ec8a372 align mode (4,352-token blocks). Qwen3.8-Flash-Next is 1.54×, Nemotron 2.27× prefill (Abstract, §1, Fig. 5 labels). |
| 1 | In-chunk export is part of the measured system | **OVERTURNED for GDN** | App. H closing paragraph: export is on only for KDA (GLM). Qwen and Nemotron use request-completion capture. Nemotron's Fig. 11 uses the upstream Mamba2 checkpoint path. |
| 2 | GDN export grain is 64 tokens (intake-2772, from the design doc) | NARROWED | Kernel: "GDN supports offsets aligned to 16 tokens within its 64-token tiles". The design doc's 64 is the layer-declared serving alignment. |
| 3 | Export is "nearly free" | NOT-FOUND-IN-SOURCE (as a measurement) | Only Θ-level costs are given. GDN interior offsets cost one extra local prefix update. |
| 4 | ASC alone delivers the gain | NARROWED | Ablation Table 3 (Qwen3.8-Flash-Next 512K). At 48 sessions, ASC alone gives ~70% of the gain (decode 24.1 → 34.2 K TPM; full 38.8). **At 32 sessions ASC alone is below vLLM** (26.0 vs 30.1; p90 TTFT 1.93 vs 0.83 s) because LRU keeps all the extra checkpoints. Full FlashStates is 30.4 vs 30.1, not significant. |
| 5 | Math (decode-heavy) gain comes from end-of-request capture | CONFIRMED | §5.4: decode +2.0-9.6%; vLLM "saves no recurrent checkpoint during decoding". |
| 6 | Retaining recent superseded states helps after context edits | CONFIRMED (App. E, one run per arm) | 3.85% of source requests change the preceding prefix. A two-turn delay before superseded states are marked for eviction cuts extra prefill among shortened-context requests from 55.1% to 16.2% (64 sessions) and from 58.7% to 18.2% (72), with p90 TTFT −18.1% and −19.4%. Unpaired runs. |
| 7 | GDS beats a tuned Marconi | CONFIRMED (one load) | Table 7: Qwen3.8-Flash-Next, 40 sessions. FlashStates 73.4 K output TPM vs the best α = 0.1 at 71.2 (+2.9%, within 2 SE); +10.2% vs the tuner's choice α = 0. |

## Export kernel design, mapped to our GDN kernels
- **Contract (Eq. 1):** R_c equals the checkpoint the same backend produces when the call is truncated at c. O and S_final are identical to the no-export call. Exactly one checkpoint is exported, and the side output never feeds back into the live state. This is the same pair of invariants as the design doc.
- **GDN interior offset.** The kernel keeps its 64-token tile grid and computes R_c from the tile's pre-state S and intermediates Z for the first c−b tokens. On our C8-6 chunked kernel (`c17_gdn.cu` L23-38: per chunk T = (I+A)⁻¹, Delta' = T X, S_L = exp(G_{L−1}) S0 + (K·exp(G_{L−1}−G))ᵀ Delta'), the analogue restricts the same formulas to the leading c−b rows of the already-built T and Delta' and writes that partial-chunk S_L as R_c.
  - T is unit lower triangular, so its leading block equals the inverse of the leading block of (I+A).
  - Whether the result is *byte*-identical to the state the cut path checkpoints (a partial last chunk of length c−b) depends on matching the reduction order. That should be the first test.
  - The alternative, ending a chunk at c, is simpler but breaks output identity after c.
- **64-aligned offset:** one store of the inter-chunk state the scan holds. **Recurrent HIP kernel and CPU op:** token-granular, so any offset is one store.
- **Wave64 / LDS / MFMA:** no change to cross-lane reductions. The prefix update reuses the tile's MFMA-built T/Delta' rows already in LDS or registers, and adds one partial-chunk state product over those leading rows, with the same MFMA shapes the scan already uses (inferred; not costed).
- **The CuTe/2-CTA mechanism** is irrelevant on gfx90a.

## Principles

| Principle | Source evidence | MI210 gfx90a | Zen 5 CPU | Port cost | EPYC consumer |
|---|---|---|---|---|---|
| Capture the exact end-of-request state with zero copy; this is where the GDN gains come from | §3.1, §5.3, App. G, App. H last paragraph | Done in C17 (PFXC-A1, host copy) | same | — (done) | PFXC-A1 |
| Export one interior checkpoint per call by a bounded prefix update from tile intermediates, leaving the main recurrence untouched | §3.2, App. H, Alg. 1 | C8-6: restrict T/Delta' to the leading rows; recurrent kernel: a store | per-token loop: a store | M | M2 export clause |
| Extra checkpoints only pay with dependency-aware admission/eviction; unmanaged, they hurt below capacity | §5.5, Table 3 | Applies only where checkpoints share a budget with KV (llama.cpp `--cache-ram` host tier); per-slot checkpoints do not compete with slot KV | same | S | decline now (KPF-64: pool not binding) |
| Keep recent superseded states for about 2 turns to survive context edits | App. E, Table 5 | C17 `create_checkpoint` min-step thinning (L3328-3342) erases earlier tasks' checkpoints within checkpoint_min_step of a kept one: the analogue of "immediately marking superseded" | same | S | FR-UFH14-DIVERGE |
| Cost-density priority (restore seconds per freed block + watermark), parameter-free | §4.3, App. I, Table 7 | host pool only | same | S | decline (pool not binding) |

## Grounding vs current EPYC state
- **PFXC-A1 post-generation checkpoint:** `c17_server_context.cpp` L3380-3401. It requires `pos_max + 1 == n_tokens` (no pending draft) but has no check that the cached tokens equal the text the client keeps.
- **Min-step thinning of other tasks' checkpoints:** L3328-3342. **PFXC-A2 anchor keep:** L3346-3351.
- **Cut positions:** L5297-5333. The checkpoint is created before `llama_decode`: L5406-5410.
- **GDN chunked kernel:** `c17_gdn.cu` L23-38 (chunk 64, keep_rs tail) and L718-731 (slot mapping). No export input: searched `c17_gdn.cu` op params (K at L1300-1302, tree parent src[6]).
- **Plan boxes:**
  - KPF-64-CUTS (plan L190-196);
  - KPF-64-SNAPSLOT-READ (L198-204);
  - FR-UFH14-DIVERGE (L182-188);
  - M2 (L395-397);
  - RS-REPLAY-PORT/-GATE (L147-164), unaffected: replay serves spec rollback, which the paper does not touch. Its App. F calls ReplaySSM "a different stage".

## Adversarial pass (2 queries, shared with intake-2787)
- Only an aggregator restating the headline numbers was found (restatement). There is no replication, review or failed reproduction; the release is days old.
- Internal weaknesses:
  - Each Table 3 load is one run, with the four configurations run concurrently on separate GPUs.
  - Table 4 runs were collected separately per stack.
  - App. E runs are unpaired.
  - The 60 GiB Nemotron experiment states "no uncertainty across repeated runs is estimated".
  - The baseline is vLLM's known-weak block grid (4,352-8,320-token blocks), so most of the uncached-token reduction is the "70% of a block" effect.
  - SGLang (256-token grid) has placement misses of only ~0.2K tokens per request.

## Plan impact (explicit)
1. **Monitor change, M2.** Replace the clause
   > split-free checkpoint prototype with the replay-only GDN op when KPF-64-CUTS is material and RS-REPLAY-PORT has landed (intake-2758#record); or, for known checkpoint targets, a per-sequence export-offset input on the GDN op with bit-identity tests under the same trigger (intake-2772#record);

   with
   > when KPF-64-CUTS is material: a per-sequence export-offset input on the GDN op for the known checkpoint targets (user-message starts, reorder junctions, n-(4+n_ubatch)), one offset per sequence per op call relative to its ubatch, needing no RS-REPLAY-PORT; on C8-6 a 64-aligned offset stores the inter-chunk state and an interior offset uses one bounded prefix update from the chunk's T and Delta' rows, not a chunk split; gate: exported state byte-identical to the checkpoint the current cut path takes at that offset, output and final state byte-identical to the no-export call, offset 0 writes nothing (intake-2772#record, intake-2787#record, intake-2788#record); the split-free prototype with the replay-only GDN op only for targets not known when the batch is built, after RS-REPLAY-PORT has landed (intake-2758#record);

   Also update the M2 `execution_conditions` to "KPF-64-CUTS material (export route); plus RS-REPLAY-PORT landed (replay route only)".
2. **Changed box text, FR-UFH14-DIVERGE** (done-when). Proposed:
   > · done when: a table of the 41 turns by first-divergence position (inside previous output, at template boundary, earlier) with the PFXC-A1 coverage of each, counting separately turns whose post-generation checkpoint lies past the kept text (for example a stop string inside accepted drafts, which the FlashStates fork refuses to publish) and turns whose matching earlier checkpoint create_checkpoint's min-step thinning would have erased (the FlashStates App. E two-turn retention case), is filed under UFH14-A7 with the verdict: file a template-stable-end checkpoint box only if at least half the turns are not served by PFXC-A1, otherwise close

   Append `intake-2787#record, intake-2788#record` to the box's citation list.
3. **KPF-64-CUTS and KPF-64-SNAPSLOT-READ text changes:** given in the intake-2787 dive (cut-kind split; n−4 pricing). The PDF adds nothing further to them.
4. **No new box.** Neither GDS eviction nor the two-turn retention gets its own box: the pool is not binding (KPF-64), and the retention question is folded into FR-UFH14-DIVERGE.
5. **Knowledge note** (kv-cache-program.md track notes, K-style): FlashStates' GDN-model gains (Qwen3.8-Flash-Next 1.54×) come from end-of-request capture plus retention, with no GDN export in serving. For llama.cpp that capture is PFXC-A1, and the paper's block-size effect does not transfer because llama.cpp has no block grid.

## Derived-actionables ledger

| id | action | owner | bears on | disposition |
|---|---|---|---|---|
| flashstates-pdf-A1 | M2 clause rewrite (text above): export first, no RS-REPLAY-PORT dependency, prefix-update kernel form, invariants as the gate | handoffs/active/kv-cache-program.md | M2 | task (monitor text change) |
| flashstates-pdf-A2 | FR-UFH14-DIVERGE done-when: add the past-kept-text and min-step-thinning coverage classes | handoffs/active/harness-program.md | FR-UFH14-DIVERGE | task (box text change) |
| flashstates-pdf-A3 | Knowledge note: GDN gains in FlashStates come from capture, not export; the block-size effect does not transfer to llama.cpp | handoffs/active/kv-cache-program.md | KPF-64 | task (note) |
| flashstates-pdf-A4 | Dependency-aware admission/GDS for the `--cache-ram` host tier | — | 2611.26020v1-A4 | decline: KPF-64 found `--cache-ram` adds nothing at 4/4 load; the Table 3 harm mechanism needs checkpoints and KV sharing one budget |
| flashstates-pdf-A5 | Two-turn superseded-state retention change in `create_checkpoint` | — | FR-UFH14-DIVERGE | decline as a standalone box: open only if A2's thinning class is non-zero |

## Dive-surfaced sources (from the PDF's references)
- **vLLM PR #50551** "Retain finalized Mamba decode checkpoints for prefix caching" and **PR #53803** "Retain align-mode mamba grid and decode-end checkpoints" (refs vLLM 2026a/b). **decline:** C17 already has the equivalent (PFXC-A1).
- **arXiv 2610.15755**, Kang, "Native dual pools or shared paging? memory organization for concurrent hybrid LLM serving". **decline:** llama.cpp checkpoints are host-RAM byte vectors separate from slot KV, so the dual-pool question does not arise.
- **arXiv 2610.22863**, Arya et al., "Understanding KV residency in production-scale agentic LLM workloads". **decline:** workload characterisation; our retention regime is measured directly by KPF-64.
- **SGLang issue 36935** (branch reuse collapses under LRU when kv_pool_tokens/chunked_prefill_size > max_mamba_cache_size). **decline:** SGLang-specific.

artifact audit: clean
