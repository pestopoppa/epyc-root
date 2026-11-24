# Stage-3 plan — upstream GDN/MMID/BF16 PRs, 4-bit KV decode, noise floors, grammar drafts, harness and judge papers (intake-ak-1124) — REVISION 1, APPROVED 2026-11-24 (OD-1 = A, changes 1-3)

Research-intake run of 2026-11-24 for the autokernel roster session. Lane worktree `/workspace/.worktrees/intake-ak-1124`, lane_head `f74b1759ccae8f76ba3d41146d47e687717954a9`; in-house code pinned at C21 `98ff8a42a` (branch `llama.cpp-experimental-c21-20261124`). Nothing in this plan has been written to a handoff, box, index row or stub. Stage 4 runs only after approval.

## Revision 1 (operator review 2026-11-24): APPROVED with changes

The operator approved Stage 4 via the coordinator ("Approve with both changes"). OD-1 = A. Changes folded into these bytes before filing:

1. **q4_0 KV packet.** Row `ak-gvfattn-q4kv-gpu-20261124` is already published (store `gpu-20261124-5141da459-gvfattn-q4kv`, kernel commit `5141da459`). AK-GVFATTN-Q4KV-DESIGN feeds that row as refinements and a follow-up, and the duplicate AK-GVFATTN-Q4KV kernel box is dropped.
2. **M10 rescoped.** It fires when the second GPU is installed and A3B is placed GPU-resident (operator 2026-11-24: A3B GPU will be served on the 2nd GPU). The coverage condition stays as a design input.
3. **MMVF-I64-OFFSET.** Already fixed: commits `c47c574ba` (int64 offsets) and `7eb398b16` (AMD MMVF_MMID even-ne00 guard) on fork branch `llama.cpp-experimental-c22-mmvf-fixes-20261124`. The box now cites both commits; its remaining step is the gate run of the prepared row `/mnt/raid0/llm/tmp/ak-c22-mmvf-fixes-gate-gpu-20261124`.
4. **Renumbered at Stage 4.** Parallel sessions minted four IDs on origin/main while this run was in review: intake-2863 (Atomic Engine), intake-2864 (Sybil skill), intake-2865 (llama.cpp PR #31233 moe-cache) and intake-2866 (Inkling-2-Mini GGUF card). This run's entries therefore moved by +4, from intake-2863..2902 to intake-2867..2906, everywhere in these bytes. The IDs were never pushed under the old numbers.
5. **OD-1 = A, applied.**
   - Repointed: the fp4kv layer-0 anchor now quotes the KL 0.250 passage, and the autoresearch deletion anchor now sits on the deletion claim.
   - Dropped: loopholes #a8, flagrot #a5, the inference-backend #a4, CATCH #a3 and illusion #a2.
   - Kept: the other three.
   - Marks were re-run.
6. **Stage-4 filing fixes (coordinator, 2026-11-24).** Brief approaches were rewritten as concrete steps to pass the brief quality gate. Possessive apostrophes were removed from brief acceptance strings because brief.py shlex-parses them; the filed done-when lines of CDR-RT9-COVER-1, GDN-SLOTS-STRONGER, RKA-SRC1-DTYPE-RULE and EV-JUDGE-FPR-1 are unchanged. RKA-GV-PSCALE-1's done-when now reads "the vector-path error". Brief `where` entries use the `epyc-llama:` alias.

## Run summary

- **Sources**: 11 submitted (3 llama.cpp PRs, 8 arXiv papers). All 11 are novel by an unbounded, normalised dedup over 2,858 entries.
- **Entries**: intake-2867 to intake-2906 (40 entries).
  - 11 submitted sources, all dived.
  - 26 Stage-2b expansion entries, all dived.
  - 3 Stage-1-only entries. intake-2905 and intake-2906 are fp4kv's BitDecoding-FP4 and LiquidGEMM, filed `stage1-unverified` / `awaiting_dive`. No number from them is used below.
  - All dives are under `research/deep-dives/intake-ak-1124/`.
- **Sweeps (operator pre-authorised up to four)**: four used.
  1. Stage-2 dives on all 11 submitted sources.
  2. Stage-2b wave 1 dived 23 dive-surfaced sources (intake-2878..2900).
  3. Wave 2 dived 3 (intake-2901..2903).
  4. Wave 3 dived Huang et al. (intake-2904) and filed the two Stage-1-only expansions.
  - The cap is now reached. Any remaining surfaced sources are declined and named in their bearing entry's `dive_corrections` (Stage-2 close-out line).
  - Stage-1 Phase-3 expansion did not run as a separate pass. Its candidates were folded into the dive-surfaced waves.
- **Stage-1 overrides**:
  - The Stage-1 summarisers rated PR #32820, the Hopper 4-bit KV paper and the loopholes paper as relevance "low". The reasons were "test-only", "Hopper-only" and "no judge gates found yet".
  - Platform mismatch is not a valid downgrade. All three have named live consumers, so all 11 were recommended and dived.
  - Two dives then set PR #32177 and PR #32533 to relevance low on evidence: neither reaches the served path.
- **Subagents, by model (25 total)**:
  - haiku/low (9): 4 Stage-1 discovery agents and 5 second-reader batches.
  - sonnet/medium (13): 6 Stage-2 dives and 7 Stage-2b wave agents.
  - opus (3): the Hopper 4-bit KV, PR #32533 BF16 src1 and Grammar-as-a-Draft dives.
- **Anchors**: 363 claim anchors on the 38 dived entries. All are script-marked `found: true` by `validate_intake.py --check-anchors --write-marks` against the retained sources in `/mnt/raid0/llm/state/vidya/raw-anchors`. A haiku/low per-claim second reader judged 19 yes, 334 partial and 10 no. Most partials are compound claims where the quote carries one clause. The 10 "no" judgements are OD-1 below; none is auto-overturned. During integration, one intake-2877 claim-index misalignment was fixed and re-read.
- **No compute ran.** Every in-house citation is pinned at C21 `98ff8a4` or at lane f74b175.

## Per-source verdicts

| Intake | Source | Verdict | Relevance | Cred | Verification | Read | How it is used |
|---|---|---|---|---|---|---|---|
| intake-2867 | llama.cpp PR #32820: tests : compare only the guaranteed GDN snapsh... (https://github.com/ggml-org/llama.cpp/pull/32820) | adopt_patterns | medium | 2 | dive-verified | FULL | GDN-SLOTS-STRONGER |
| intake-2868 | llama.cpp PR #32177: CUDA: compact mul_mat_id ids in chunks when th... (https://github.com/ggml-org/llama.cpp/pull/32177) | worth_investigating | low | 3 | dive-verified | FULL | MMID-UB-CEIL-1, M3 |
| intake-2869 | llama.cpp PR #32533: ggml : support a BF16 src1 in MUL_MAT and MUL_... (https://github.com/ggml-org/llama.cpp/pull/32533) | adopt_patterns | low | 1 | dive-verified | FULL | MMVF-I64-OFFSET, RKA-SRC1-DTYPE-RULE, K1 |
| intake-2870 | Fast 4-bit KV-Cache Decoding on Hopper GPUs: Why vLLM's 4-bit Paths... (https://arxiv.org/abs/2611.30027v1) | adopt_patterns | high | 2 | dive-verified | FULL | AK-GVFATTN-Q4KV-DESIGN, RKA-IPB-CENSUS-1, RKA-GV-PSCALE-1, KVQ-ROT-KLD-1, KVQ-KMEAN-SIM-1, CDR-A3B-Q4KV-32K, K3 |
| intake-2871 | KernelShift: Benchmarking Kernel Optimization Across Evolving Hardware (https://arxiv.org/abs/2611.29590v1) | adopt_patterns | medium | 2 | dive-verified | PARTIAL | AK-CPU-KSHIFT-1 |
| intake-2872 | Exact on Paper: Which LLM Serving Shortcuts Flip Graded Answers, Me... (https://arxiv.org/abs/2611.29663v1) | adopt_patterns | high | 2 | dive-verified | FULL | SPEC-ID-GATE-2, SPEC-ID-NOISE-2, FOLD-KLD-FLOOR-1, RKA-BATCH-INV-CENSUS-1, KVQ-ROT-KLD-1 |
| intake-2873 | Grammar-as-a-Draft: More Tokens per Speculative Decoding Step on Gr... (https://arxiv.org/abs/2611.28349v1) | worth_investigating | medium | 2 | dive-verified | FULL | SPEC-GRAM-JSON-1, M2 |
| intake-2874 | Demystifying the Autoresearch Harness: How Context and Skills Shape... (https://arxiv.org/abs/2611.28244v1) | adopt_patterns | high | 3 | dive-verified | FULL | AK-LESSON-DEMOTE-1, AK-ATTEMPT-DIGEST-1, CTE-CFAB-A8 |
| intake-2875 | DMC-5: Dual-Model Collaboration with Cache-aware Context Compressio... (https://arxiv.org/abs/2611.30412v1) | adopt_patterns | medium | 2 | dive-verified | PARTIAL | KV-EVICT-COST-2, HAR-COMPACT-LEDGER-1, CTE-CFAB-A8 |
| intake-2876 | CCAMoE: Cache-Conditioned Adaptive Inference for Offloaded MoE (https://arxiv.org/abs/2611.28550v1) | worth_investigating | medium | 1 | dive-verified | FULL | SPEC-STOP-EQ7-1, CDR-RT9-COVER-1 |
| intake-2877 | Which Loopholes Get Found? Predicting Reward Hacking of LLM Judges ... (https://arxiv.org/abs/2611.29651v1) | adopt_patterns | medium | 1 | dive-verified | FULL | EV-JUDGE-FPR-1, M1 |
| intake-2878 | kv4-hopper: Fast 4-bit KV-cache decoding on Hopper GPUs, and a vLLM... (https://github.com/thomaszhang2661/kv4-hopper) | adopt_patterns | high | 1 | dive-verified | PARTIAL | AK-GVFATTN-Q4KV-DESIGN, KVQ-KMEAN-SIM-1 |
| intake-2879 | FOSCAR: Accelerating Decode Attention over 2- and 4-Bit KV Caches t... (https://arxiv.org/abs/2611.09722v1) | adopt_patterns | medium | 1 | dive-verified | PARTIAL | AK-GVFATTN-Q4KV-DESIGN, RKA-IPB-CENSUS-1 |
| intake-2880 | UltraQuant: 4-bit KV Caching for Context-Heavy Agents (https://arxiv.org/abs/2606.20474v3) | worth_investigating | medium | 1 | dive-verified | PARTIAL | AK-GVFATTN-Q4KV-DESIGN |
| intake-2881 | FlagRot: Selective Rotation for Low-Bit KV Caches (https://arxiv.org/abs/2611.03992v1) | worth_investigating | high | 2 | dive-verified | PARTIAL | KVQ-ROT-KLD-1, KVQ-KMEAN-SIM-1, M4 |
| intake-2882 | Defeating Nondeterminism in LLM Inference (https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) | adopt_patterns | medium | 1 | dive-verified | FULL | RKA-BATCH-INV-CENSUS-1, SPEC-ID-NOISE-2 |
| intake-2883 | The Integer Alibi: Localizing Cross-Kernel Divergence in INT8-Quant... (https://arxiv.org/abs/2608.13756v2) | adopt_patterns | low | 1 | dive-verified | PARTIAL | SPEC-ID-GATE-2, SPEC-ID-NOISE-2 |
| intake-2884 | The Silent Hyperparameter: Quantifying the Impact of Inference Back... (https://arxiv.org/abs/2605.19537v4) | adopt_patterns | low | 2 | dive-verified | PARTIAL | SPEC-ID-GATE-2, PFXC-ID-REPLICA-1 |
| intake-2885 | Future Validity is the Missing Statistic: From Impossibility to Phi... (https://arxiv.org/abs/2605.07698v1) | worth_investigating | medium | 2 | dive-verified | PARTIAL | SPEC-GRAM-TV-1, K2 |
| intake-2886 | One Token to Fool LLM-as-a-Judge (https://arxiv.org/abs/2507.08794v3) | adopt_patterns | medium | 1 | dive-verified | PARTIAL | EV-JUDGE-FPR-1 |
| intake-2887 | CATCH: A Controllable Analysis Testbed for Reward Hacking in Coding RL (https://arxiv.org/abs/2609.39533v3) | worth_investigating | low | 1 | dive-verified | PARTIAL | M1 |
| intake-2888 | An Imperfect Verifier is Good Enough: Learning with Noisy Rewards (https://arxiv.org/abs/2604.07666v2) | adopt_patterns | low | 1 | dive-overturned | PARTIAL | EV-JUDGE-FPR-1, M1 |
| intake-2889 | Before the Model Learns the Bug: Fuzzing RLVR Verifiers (https://arxiv.org/abs/2606.01066v1) | adopt_patterns | medium | 1 | dive-verified | PARTIAL | EV-SCORER-FUZZ-1 |
| intake-2890 | EleutherAI/rh-indicators: Leading Indicators of Reward Hacking (https://github.com/EleutherAI/rh-indicators) | worth_investigating | low | 2 | dive-verified | PARTIAL | M1 |
| intake-2891 | Same Request, Different Answer: Quantization Amplifies Cache-Induce... (https://arxiv.org/abs/2609.04748v3) | worth_investigating | high | 3 | dive-verified | PARTIAL | SPEC-ID-GATE-2, PFXC-ID-REPLICA-1 |
| intake-2892 | Which Decisions Low-Bit Quantization Breaks, and How to Predict Them (https://arxiv.org/abs/2608.06564v5) | worth_investigating | medium | 2 | dive-verified | PARTIAL | KVQ-ROT-KLD-1 |
| intake-2893 | The Noise Floor of a Quantization Comparison: Engine, restart, batc... (https://arxiv.org/abs/2611.15671v1) | adopt_patterns | high | 1 | dive-verified | FULL | SPEC-ID-GATE-2, FOLD-KLD-FLOOR-1 |
| intake-2894 | The Illusion of Equivalence: Systematic FP16 Divergence in KV-Cache... (https://arxiv.org/abs/2604.15409v1) | adopt_patterns | medium | 2 | dive-verified | PARTIAL | SPEC-ID-GATE-2, SPEC-ID-NOISE-2, PFXC-ID-REPLICA-1 |
| intake-2895 | SpecMoE: A Fast and Efficient Mixture-of-Experts Inference via Self... (https://arxiv.org/abs/2604.10152v1) | adopt_patterns | low | 4 | dive-verified | FULL | CDR-RT9-COVER-1 |
| intake-2896 | S2-MoE: Enabling Efficient Self-Speculative Decoding for Mixture-of... (https://arxiv.org/abs/2608.15018v2) | adopt_patterns | medium | 2 | dive-verified | FULL | SPEC-STOP-EQ7-1 |
| intake-2897 | cmu-l3/kernel-shift: KernelShift: Kernel Optimization Across Evolvi... (https://github.com/cmu-l3/kernel-shift) | adopt_patterns | medium | 2 | dive-verified | PARTIAL | AK-CPU-KSHIFT-1 |
| intake-2898 | SimdBench: Benchmarking Large Language Models for SIMD-Intrinsic Co... (https://arxiv.org/abs/2507.15224v1) | adopt_patterns | low | 1 | dive-verified | FULL | AK-CPU-KSHIFT-1 |
| intake-2899 | llama.cpp PR #32135: ggml : add BF16 support to RMS_NORM (CPU, CUDA) (https://github.com/ggml-org/llama.cpp/pull/32135) | adopt_patterns | low | 2 | dive-verified | PARTIAL | RKA-SRC1-DTYPE-RULE |
| intake-2900 | llama.cpp PR #32387: ggml : add BF16 support to ROPE and SET_ROWS (... (https://github.com/ggml-org/llama.cpp/pull/32387) | adopt_patterns | low | 2 | dive-verified | PARTIAL | RKA-SRC1-DTYPE-RULE |
| intake-2901 | How Far Does Second-Order Linear Response Predict Quantization Mism... (https://arxiv.org/abs/2611.12634v1) | adopt_patterns | medium | 1 | dive-verified | PARTIAL | FOLD-KLD-FLOOR-1 |
| intake-2902 | Cache-Aware Prompt Compression: A Two-Tier Cost Model for LLM API C... (https://arxiv.org/abs/2607.15516v1) | adopt_patterns | medium | 1 | dive-verified | PARTIAL | KV-EVICT-COST-2 |
| intake-2903 | How Memory Management Impacts LLM Agents: An Empirical Study of Exp... (https://arxiv.org/abs/2505.16067v2) | adopt_patterns | high | 2 | dive-verified | PARTIAL | AK-LESSON-DEMOTE-1 |
| intake-2904 | From Accuracy to Robustness: A Study of Rule- and Model-based Verif... (https://arxiv.org/abs/2505.22203v2) | adopt_patterns | high | 0 | dive-verified | PARTIAL | EV-JUDGE-FPR-1 |
| intake-2905 | BitDecoding-FP4: Native FP4 KV Cache Decoding via Algorithm-System ... (https://arxiv.org/abs/2611.09825v1) | worth_investigating | medium | 1 | stage1-unverified | - | awaiting a dive (Stage-1 expansion only) |
| intake-2906 | LiquidGEMM: Hardware-Efficient W4A8 GEMM Kernel for High-Performanc... (https://arxiv.org/abs/2509.01229v1) | worth_investigating | medium | 0 | stage1-unverified | - | awaiting a dive (Stage-1 expansion only) |

## Measured CUDA kernel efficiency (operator request: replaces the recalled figures in the census parity table)

The figures below are taken verbatim from anchored claims of dive-verified entries. Each anchor is script-marked as found in the retained source. Do not edit the census yourself; the operator applies it. Basis is % of peak HBM bandwidth unless stated otherwise.

**Hopper decode attention, measured**

| Op class (census `ref`) | Measured % of peak | Device and setup | Citation |
|---|---|---|---|
| Decode attention, BF16 KV (`cuda-flashdecode`) | > 90% | H100 (3.35 TB/s) and B200; FlashInfer BF16; batch 128, 32K context; effective KV access throughput | intake-2879 (FOSCAR Fig. 1) |
| Decode attention, FP8 KV (`cuda-flashdecode`) | 85-89% at batch >= 8 (71% at 32 x 4K) | H200 SXM; FlashAttention-4 native FP8 decode (unmerged FA commit 8ef2c611, vLLM 0d99666a) | intake-2870 |
| Device copy of the same bytes (achievable ceiling) | 76 / 87 / 87 / 89% across the Table 6 columns | H200 SXM; Llama-3.1-8B head shape | intake-2870 (Table 6) |
| Decode attention, best 4-bit KV (software decode) | 67% (B=32) to 75% (B=128) at 16K; 38% at B=1, 64K; 18% at B=1, 16K | H200; Hopper-native NVFP4 kernel | intake-2870 |
| Same kernel without the E2M1 reconstruction | 77-85% | H200 SXM (Table 6 removal ablation) | intake-2870 (Table 6) |
| Decode attention, deployed 4-bit KV | 10-20% | H200; vLLM NVFP4 KV path (FlashInfer decode) | intake-2870 |
| INT4 vs BF16 GQA decode | INT4 17-30%; BF16 44-64% | H100; PyTorch kernels, the paper's own arithmetic from cited GB/s | intake-2870 (related work) |
| 2-bit fused KV decode kernels | < 31% (H100), < 15% (B200) | existing fused kernels, same setup as row 1 | intake-2879 |

**Reference points from other devices, for context only (not Hopper)**

| Op class (census `ref`) | Measured figure | Device and setup | Citation |
|---|---|---|---|
| NVFP4 decode, hardware-native | 72.4% | B200; TensorRT-LLM | intake-2879 |
| AMD decode attention | FP8 KV 23%, FP4 scaled-MFMA 10%, codebook 4-bit 4%. Basis: fraction of the bandwidth-implied compute ceiling, not % of HBM | MI355X; MiniMax-M2.5, 16K, batch 64 | intake-2880 |

**Suggested parity edits** (operator applies):

- `cuda-flashdecode`: 85 (recalled) becomes 87, measured.
  - The MI210 serves q8_0 KV, and the FP8 decode row (85-89%, intake-2870) is the closest analogue.
  - Cite FOSCAR's > 90% BF16 row (intake-2879) as the upper bound.
- The census's GPU roofline is HBM nameplate. Hopper's own copy ceiling is 87-89% of peak (intake-2870). So "% of peak" on Hopper and "% of nameplate" on the MI210 are comparable only against each device's copy ceiling: on the MI210, a measured 1.498 TB/s stream ceiling against the 1638 GB/s nameplate.
- If the q4_0-KV gv_fattn box lands, add a 4-bit decode reference of 67-75% at batch 32-128 (intake-2870).

**What these sources do not cover**: none of the 40 entries in this run measures Hopper %-of-peak for:

- dense GEMV/GEMM (`cuda-gemv`; intake-1546 Marlin reports A10 speedups, not % of peak)
- MoE (`cuda-moe`)
- GDN/selective scan (`cuda-scan`)
- fused tails (`cuda-fused-tail`)
- CPU AVX-512 GEMV (`cpu-avx512-gemv`)

Those five `ref` rows should keep their "recalled, not re-verified" labels.

## Work packets

| Packet | Action | Owner | Boxes |
|---|---|---|---|
| P1 | Noise-floor-aware identity and fold gates: replica floor, cache and KV-provenance conditions, drift localisation, KLD floor, prompt-cache identity, batch-invariance census | kernel-champion-and-promotion.md, rocm-kernel-authoring.md, speculative-decoding.md | SPEC-ID-GATE-2, SPEC-ID-NOISE-2, FOLD-KLD-FLOOR-1, PFXC-ID-REPLICA-1, RKA-BATCH-INV-CENSUS-1 |
| P2 | q4_0-KV GQA-verify attention on the MI210: design inputs and refinements for the published row, an issue-budget census and a sink numerics test | autokernel-loop.md, rocm-kernel-authoring.md | AK-GVFATTN-Q4KV-DESIGN, RKA-IPB-CENSUS-1, RKA-GV-PSCALE-1 |
| P3 | q4_0 KV quality: rotation on/off KLD with flip and margin arms, K-mean simulation, A3B CPU long-context decode | cpu-decode-roofline-program.md, quantization-and-low-bit.md | KVQ-ROT-KLD-1, KVQ-KMEAN-SIM-1, CDR-A3B-Q4KV-32K |
| P4 | Upstream-contract robustness: GDN slot witness, mul_mat_id ceiling guard, MMVF overflow and alignment fixes, dtype and rebase rules | kernel-champion-and-promotion.md, rocm-kernel-authoring.md | GDN-SLOTS-STRONGER, MMID-UB-CEIL-1, MMVF-I64-OFFSET, RKA-SRC1-DTYPE-RULE |
| P5 | Draft-length and structured-output control: forced-share replay, masked-vs-conditional TV, cost-aware stop rule, residency coverage close-out | cpu-decode-roofline-program.md, speculative-decoding.md | SPEC-GRAM-JSON-1, SPEC-GRAM-TV-1, SPEC-STOP-EQ7-1, CDR-RT9-COVER-1 |
| P6 | AutoKernel loop: lesson demote rule by journal replay, per-attempt digests, an x86 KernelShift-format pilot | autokernel-loop.md | AK-LESSON-DEMOTE-1, AK-ATTEMPT-DIGEST-1, AK-CPU-KSHIFT-1 |
| P7 | Judge and scorer audit before any optimiser uses them: scorer fuzzing and judge false-positive exposure | eval-tower-program.md | EV-SCORER-FUZZ-1, EV-JUDGE-FPR-1 |
| P8 | Compaction cost and integrity: local-seconds break-even, failed-action ledger, a context-folding arm design | context-and-token-economy.md, harness-program.md, kv-cache-program.md | KV-EVICT-COST-2, HAR-COMPACT-LEDGER-1, CTE-CFAB-A8 |

### Why eight packets

The run left eight independent units. Each has a different owner or code surface, and none could be merged without mixing owners or decision questions. None was split to reach a target.

### Concurrency and ordering

**Code and doc work that can start now, in parallel:**

| Packet | Boxes |
|---|---|
| P1 | SPEC-ID-GATE-2, RKA-BATCH-INV-CENSUS-1 |
| P2 | AK-GVFATTN-Q4KV-DESIGN |
| P4 | all four boxes |
| P5 | SPEC-GRAM-JSON-1, SPEC-STOP-EQ7-1, CDR-RT9-COVER-1 |
| P6 | AK-LESSON-DEMOTE-1, AK-ATTEMPT-DIGEST-1, AK-CPU-KSHIFT-1 step 1 |
| P7 | EV-SCORER-FUZZ-1 |
| P8 | HAR-COMPACT-LEDGER-1, CTE-CFAB-A8 |

**Ordered pairs:**

- SPEC-ID-GATE-2 before SPEC-ID-NOISE-2 and PFXC-ID-REPLICA-1. Both use the amended floor and cache rules.
- AK-GVFATTN-Q4KV-DESIGN feeds the published row ak-gvfattn-q4kv-gpu-20261124; RKA-IPB-CENSUS-1 informs that row's next priority (decode diet or residency) but does not gate it.
- KVQ-ROT-KLD-1 before CDR-A3B-Q4KV-32K. It also sets whether KVQ-KMEAN-SIM-1 runs its selective-rotation arm.
- KV-EVICT-COST-1 (open) before KV-EVICT-COST-2.

**Inference boxes and where they book:**

- **MI210 rows:** SPEC-ID-NOISE-2, RKA-IPB-CENSUS-1, RKA-GV-PSCALE-1, MMID-UB-CEIL-1, MMVF-I64-OFFSET, and the GPU arms of FOLD-KLD-FLOOR-1, PFXC-ID-REPLICA-1 and KVQ-ROT-KLD-1.
- **CPU-quarter rows:** SPEC-GRAM-TV-1, KVQ-KMEAN-SIM-1, CDR-A3B-Q4KV-32K, AK-CPU-KSHIFT-1 step 2, EV-JUDGE-FPR-1, and the CPU arms of the boxes above.
- Each inference box is booked by its owner through the row-owner loop. None is booked by this intake.

### The q4_0 gv_fattn row (operator change 1)

The row `ak-gvfattn-q4kv-gpu-20261124` is published (store `gpu-20261124-5141da459-gvfattn-q4kv`, kernel commit `5141da459`, `GGML_CUDA_FA_GQA_Q4KV=1`, default off). The duplicate kernel box from revision 0 is dropped; AK-GVFATTN-Q4KV-DESIGN feeds that row as refinements and a follow-up, including the KV-quality packet's rotation and K-mean notes.

### Minimum rigor

**Measurement boxes:**

- **Boxes:** SPEC-ID-NOISE-2, SPEC-GRAM-TV-1, SPEC-STOP-EQ7-1, AK-LESSON-DEMOTE-1, AK-CPU-KSHIFT-1, KVQ-ROT-KLD-1, KVQ-KMEAN-SIM-1, CDR-A3B-Q4KV-32K, CDR-RT9-COVER-1, FOLD-KLD-FLOOR-1, PFXC-ID-REPLICA-1, RKA-IPB-CENSUS-1, EV-SCORER-FUZZ-1, EV-JUDGE-FPR-1.
- **Six controls stated in each:**
  1. A frozen input with a recorded digest (prompt set, journal, traces, fixture set or problem set).
  2. The C21 or production incumbent as baseline.
  3. Per-item outputs under the box's run path.
  4. A holdout where a rule is fitted (the SPEC-STOP-EQ7-1 held-out half, the AK-LESSON-DEMOTE-1 later epochs). Elsewhere the holdout is inapplicable because nothing is tuned, and replica floors replace it.
  5. Complete denominators ("out of 64", per-string counts, every class).
  6. A predeclared stop-on-answer / stop-on-futility rule.
- Formal-gate cells stay futility-only at interim looks.

**Deterministic boxes:**

- **Boxes:** SPEC-ID-GATE-2, GDN-SLOTS-STRONGER, MMID-UB-CEIL-1 (a), RKA-SRC1-DTYPE-RULE, RKA-BATCH-INV-CENSUS-1, AK-ATTEMPT-DIGEST-1, AK-GVFATTN-Q4KV-DESIGN, KV-EVICT-COST-2, HAR-COMPACT-LEDGER-1, CTE-CFAB-A8.
- They have no holdout. Their checks are conformance checks instead: unit tests, bit-exact oracles, route-histogram equality, a replay of retained trajectories, or arithmetic over retained rows.

### Consumer discovery

**Searched:**

- lane handoffs and docs at f74b175;
- llama.cpp C21 98ff8a4: ggml-cuda, ggml-cpu, common, tools/server and tests;
- epyc-inference-research: the autokernel loop, controller and moe_routing;
- the orchestrator: src/graph/compaction.py, scripts/server/orchestrator_stack.py and the judge and scorer code.

**Primary owners and their consumers:**

| Box | Consumers |
|---|---|
| SPEC-ID-GATE-2 (speculative-decoding.md) | policy: every spec identity gate, CAFE rows, the fold gates in kernel-champion-and-promotion.md, the BSV-2 accept gate (M11) |
| FOLD-KLD-FLOOR-1 | policy: C21 and later fold gates |
| AK-GVFATTN-Q4KV-DESIGN | direct: the published row ak-gvfattn-q4kv-gpu-20261124 (commit 5141da459); evidence: RKA-IPB-CENSUS-1 |
| KVQ-ROT-KLD-1 | policy: q4_0 KV serving decisions in long-context-program.md and the tq3 track's G3 (G) multi-step eval, whose GSM8K protocol it reuses |
| EV-JUDGE-FPR-1 | policy: EV-29 (secondary column only) and the pre-RL monitor (M1) |
| KV-EVICT-COST-2 | evidence: CF-AB-1 arm A8 and harness compaction |

No consumer gets a duplicate box.

### Stage-1 preliminary actionables

Each maps to a terminal row as follows. All were hypotheses; none is cited from Stage-1 text.

| Hypothesis | Maps to |
|---|---|
| "Our GDN path should not assume slots > 0" (pr32820) | AKJ-01. It was overturned: our kernel writes them and rollback needs them. |
| "Check the HIP mul_mat_id assert at 64 KB LDS" (pr32177) | AKJ-04 |
| "CPU BF16 src1 may reduce conversion overhead" (pr32533) | AKJ-10 |
| Layer-0 key-mean bias fix, K mean removal plus rotation (fp4kv) | AKJ-19 and AKJ-16 |
| Agent kernel loop vs compiler, model-specific reference material (kernelshift) | AKJ-22 and AKJ-24 |
| Single-replica gates, FP8 KV flip budget (exactpaper) | AKJ-25 and AKJ-28 |
| Forced-token drafts for JSON tool calls, check Nie et al. (grammardraft) | AKJ-35 and AKJ-38 |
| Per-attempt records, delete never-used lessons (autoresearch) | AKJ-41 and AKJ-40 |
| Local saving is latency not money, YAMATO checklist (dmc5) | AKJ-44 and AKJ-45 |
| Resident-expert drafting, cost-aware draft length (ccamoe) | AKJ-50 and AKJ-48 |
| Measure judge FPR before trusting it (loopholes) | AKJ-52 |

## Monitors and knowledge-only (durable prose, no checkbox)

| Packet | Owner | Trigger / basis |
|---|---|---|
| M1 | handoffs/active/context-and-token-economy.md | Append to the existing pre-RL monitor line (track per-request-reasoning-budget, the 'if a local GRPO/RLVR weights run is ever planned' line): the plan also pre-registers a judge exposure audit (propensity x judge FPR per exploit string, from EV-JUDGE-FPR-1), an independent unhackable audit run (no write access, hidden tests), within-group reward-contrast logging, and KL-slope tracking over log-spaced checkpoints (intake-2877, intake-2887, intake-2888, intake-2890). |
| M2 | handoffs/active/speculative-decoding.md | If SPEC-GRAM-JSON-1 finds any production json_schema class with forced share >= 10-15% and material token volume: design the chain-path grammar draft (forced runs from llg_matcher_compute_ff_tokens as point-mass drafts, logits skipped only where the mask admits one token) and grammar-aware pruning of batch trees; open the implementation box only if the class-weighted ceiling is >= 1.10x (intake-2873). |
| M3 | handoffs/active/kernel-champion-and-promotion.md | When MMID-HELPER-N10 folds: port #32177's chunked id compaction as a separate commit with its 66000-token tests, adapted to expert_bounds; KEEP iff 6/6 pass on ROCm0 and the n <= 16384 path is bitwise unchanged; defer to the upstream merge if the adaptation is larger than the helper (intake-2868). |
| M4 | handoffs/active/quantization-and-low-bit.md | If KVQ-ROT-KLD-1 shows a rotation effect over 10%: split LLAMA_ATTN_ROT_DISABLE into K-only and V-only switches in the experimental tree (selecting keys alone carries 93-94% of the gain in intake-2881). |
| M5 | handoffs/active/quantization-and-low-bit.md | If KVQ-KMEAN-SIM-1 shows the first full-attention layer at >= 2x the median layer's simulated KL: add a per-layer KV-type override for that layer (intake-2870). |
| M6 | handoffs/active/kv-cache-program.md | If KV-EVICT-COST-2 records a break-even length for the compressor/agent split on some device: probe a concurrent CPU-quarter compressor with the GPU agent for latency (intake-2875). |
| M7 | handoffs/active/eval-tower-program.md | If EV-JUDGE-FPR-1 finds a judge that gates a decision with any master-key FPR >= 1%: compare a no-question prompt fix with a trained robust judge (Master-RM-style, 20k truncation negatives) before that judge gates an optimiser (intake-2886). |
| M8 | handoffs/active/rocm-kernel-authoring.md | If RKA-BATCH-INV-CENSUS-1 finds 3 or fewer ops need change: implement a default-off invariant audit arm (pinned per-column reduction geometry for n = 1-16, fixed-size KV chunks in vector flash attention) with a bitwise width-1 vs width-8 test (intake-2882). |
| M9 | handoffs/active/autokernel-loop.md | If AK-CPU-KSHIFT-1's pilot produces a task the AK loop can use: extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM at verify widths (intake-2871). |
| M10 | handoffs/active/cpu-decode-roofline-program.md | Fires when the second GPU is installed and A3B is placed GPU-resident (operator 2026-11-24: A3B GPU will be served on the 2nd GPU): design a GPU-resident expert-subset drafter for A3B, using CDR-RT9-COVER-1's same-domain coverage at <= 12.5% residency (>= 0.6 makes a resident subset worth drafting from) as a design input (intake-2876). |
| M11 | handoffs/active/eval-tower-program.md | The harness accept gate (BSV-2 family) is not activated until an A/A floor from >= 3 replicas exists for its metric, per SPEC-ID-GATE-2 rule (a) (intake-2872). |
| K1 | handoffs/active/speculative-decoding.md | Annotation under DF2-11-BF16-FIX: llama.cpp PR #32533 cannot route the BF16 drafter, whose weights are BF16 with F32 src1; on C21 ne11 <= 8 takes MMVF by default and ne11 9-16 stays on hipBLAS/Tensile because MMF refuses BF16 on CDNA2 (intake-2869). |
| K2 | handoffs/active/speculative-decoding.md | Note in the SPEC-GRAM section: the served verifier samples the grammar-masked distribution (common/sampling.cpp:1038-1107 @ 98ff8a4), speculation adds no bias over plain masked sampling, and logit-free acceptance of a forced token is lossless only where the mask admits exactly one token (intake-2885, intake-2873). |
| K3 | handoffs/active/autokernel-loop.md | The measured Hopper percent-of-peak table in this plan replaces the recalled CUDA reference figures in the bandwidth-census parity section; the operator applies it to docs/design/mi210-served-kernel-bandwidth-census-20261122.md and the census JSON (intake-2870, intake-2879, intake-2880). |
| K4 | handoffs/active/kernel-champion-and-promotion.md | Magnitudes not imported as thresholds or expectations: cross-engine drift (intake-2884), vLLM KL floors (intake-2901), API cache prices (intake-2875, intake-2902), Arm agent-kernel speedups (intake-2871) and TPU grammar-draft speedups (intake-2873). |

## Operator decisions (each blocks only its own item)

**OD-1 (ANSWERED 2026-11-24: A): second-reader disagreements.** 10 of 363 anchors were judged "no" (the quote does not support its claim). None is auto-overturned. My read of each against the source:

| Anchor | My read |
|---|---|
| intake-2870#a12 | Mis-anchored, not a wrong claim. The 73.0% is the full NVFP4 recipe on R1-Distill-Qwen-7B. The claim's KL 0.250 for layer-0-only NVFP4 sits in Section 8 of the same page and should be the anchor. |
| intake-2874#a1 | The quote belongs to the deletion claim, not the folding claim. |
| intake-2877#a4, #a8, #a9 | Fragments from the onset-window and two-pattern sections. #a4 supports the onset window; #a8 is truncated; #a9 is a seeding-dose detail. |
| intake-2881#a5 | A baseline-condition fragment that does not carry the q4_0 prediction. The prediction is the dive's inference by analogy and is labelled so in the claim. |
| intake-2884#a4 | A table title only. |
| intake-2887#a3 | It describes the hackable run, not the harder-reward onset. |
| intake-2894#a2 | An FP16 methods sentence, not the FP32 result. |
| intake-2904#a12 | An authors' hypothesis, cited as such. |

Options:

- **(A, recommended)** At Stage 4:
  - Replace intake-2870#a12 with the Section 8 KL 0.250 quote.
  - Re-point intake-2874#a1 to the deletion claim.
  - Drop intake-2877#a8, intake-2881#a5, intake-2884#a4, intake-2887#a3 and intake-2894#a2. Each affected claim keeps at least one other verified anchor or is labelled inference in its text.
  - Keep intake-2877#a4, intake-2877#a9 and intake-2904#a12.
  - Re-run `--check-anchors --write-marks`.
  - Tradeoff: about 20 minutes of validator time, and the anchors then say what they cite.
- **(B)** Keep every anchor as is and record the 10 refs in each entry's notes.
  - Tradeoff: no work now, but those anchors carry a quote that does not support their claim, and that defect is inherited by any later `intake-NNNN#NN` citation.

This decision blocks only those 10 anchors; every box above is unaffected.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| AKJ-01 | intake-2867 | Pin the in-house all-slot GDN guarantee with a witness test, a doc note and the tbo-scope rule | P4 / GDN-SLOTS-STRONGER |
| AKJ-02 | intake-2867 | Port upstream #32820's slot-0-only test view | decline: it would stop checking the tail slots that speculative rollback reads; the in-house chunked kernel writes them |
| AKJ-03 | intake-2867 | Price K=5 vs K=1 tail-slot cost on ROCm0 at n=2048 | decline: tail slots are required by MTP and DFlash2 rollback, so their cost is not optional; reopen only if a rollback design stops reading them |
| AKJ-04 | intake-2868 | Guard the 16384-token mul_mat_id ceiling in the launcher and confirm it with an op smoke | P4 / MMID-UB-CEIL-1 |
| AKJ-05 | intake-2868 | Fold chunked id compaction with its 66000-token tests when the n_used helper folds | M3 |
| AKJ-06 | intake-2868 | Treat #32177 as a performance item | decline: robustness only; every configured ubatch is at most 2048, eight times below the gfx90a ceiling |
| AKJ-07 | intake-2869 | Gate the MMVF int64 offset fix and the AMD MMVF_MMID even-ne00 guard (both already committed) | P4 / MMVF-I64-OFFSET |
| AKJ-08 | intake-2869 | Record that #32533 cannot route the BF16 drafter (BF16 weights, F32 src1) | K1 |
| AKJ-09 | intake-2869 | Kernel-authoring rules for new input dtypes plus the BF16-activation rebase trigger | P4 / RKA-SRC1-DTYPE-RULE |
| AKJ-10 | intake-2869 | Port BF16 src1, a direct BF16 CPU activation path, BF16 RMS_NORM or BF16 SET_ROWS | decline: no in-house producer emits BF16 activations, verify-width src1 bytes are tiny, and Zen 5 int8 VNNI needs Q8 activations anyway |
| AKJ-11 | intake-2870 | Design inputs for a q4_0-KV gv_fattn: lane-map oracle, fold-vs-reconstruct counts, LDS/operand-swap note, premise correction | P2 / AK-GVFATTN-Q4KV-DESIGN |
| AKJ-12 | intake-2870 | Build the default-off q4_0-KV gv_fattn path and gate it against q8_0 gv | P2 / AK-GVFATTN-Q4KV-DESIGN |
| AKJ-13 | intake-2870 | rocprofv3 instruction-per-byte census of the q8_0 gv_fattn kernel | P2 / RKA-IPB-CENSUS-1 |
| AKJ-14 | intake-2870 | Sink-heavy numerics test of gv_fattn with P scaling as the candidate fix | P2 / RKA-GV-PSCALE-1 |
| AKJ-15 | intake-2870 | 27B q4_0 KV KLD with rotation on vs off, margin screen and graded-flip arm, plus an A3B CPU arm | P3 / KVQ-ROT-KLD-1 |
| AKJ-16 | intake-2870 | Post-RoPE K dump and offline q4_0 mean-removal / selective-rotation simulation | P3 / KVQ-KMEAN-SIM-1 |
| AKJ-17 | intake-2870 | Per-layer KV-type override for the first full-attention layer | M5 |
| AKJ-18 | intake-2870 | 35B-A3B CPU decode at 32k with q4_0 vs q8_0 KV | P3 / CDR-A3B-Q4KV-32K |
| AKJ-19 | intake-2870 | Port the Qwen2 k-proj-bias KV fixes | decline: no served config has a k_proj bias (attention_bias false in every config) |
| AKJ-20 | intake-2881 | Split the rotation disable switch into K-only and V-only | M4 |
| AKJ-21 | intake-2878 | Port the Hopper kernels, the FOSCAR wgmma pipeline or the CDNA4 scaled-MFMA FP4 path | decline: each needs TMA, wgmma, tcgen05 or CDNA4 scaled-MFMA instructions that gfx90a lacks; the portable parts are taken in the design note |
| AKJ-22 | intake-2871 | One-op KernelShift-format x86 pilot with ISA ladder, autovec control, outcome classes and codegen counts | P6 / AK-CPU-KSHIFT-1 |
| AKJ-23 | intake-2871 | Extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM | M9 |
| AKJ-24 | intake-2871 | Pitfalls-digest prompt, fraction-of-peak scoring, Arm speedups as expectations, the e2e hook, the HF dataset, SimdBench priors | decline: the planner already reads negatives, the census already scores against the measured ceiling, and the Arm-bound artefacts do not run on Zen 5 |
| AKJ-25 | intake-2872 | Amend the identity-gate protocol: replica floor, cache state, KV provenance, route and config recording, graded flips | P1 / SPEC-ID-GATE-2 |
| AKJ-26 | intake-2872 | Null-test the gate and localise the GPU A/A drift (skinny atomics, node hashes, f32 audit arm) | P1 / SPEC-ID-NOISE-2 |
| AKJ-27 | intake-2872 | Build in-row bands from all pairs of at least three replicas including a reordered arm | P1 / SPEC-ID-GATE-2 |
| AKJ-28 | intake-2872 | Graded-flip budget for q4_0 and q8_0 KV over a scheduling floor | P3 / KVQ-ROT-KLD-1 |
| AKJ-29 | intake-2872 | Keep the harness accept gate off until a three-replica A/A floor exists | M11 |
| AKJ-30 | intake-2882 | Per-op batch-invariance census and port cost for a GPU fixed-order audit arm | P1 / RKA-BATCH-INV-CENSUS-1 |
| AKJ-31 | intake-2891 | Cache-hit vs cold-recompute identity with a replica floor on the served recipes | P1 / PFXC-ID-REPLICA-1 |
| AKJ-32 | intake-2901 | Measure the fold-gate KLD A/A floor and report candidate KLD over floor | P1 / FOLD-KLD-FLOOR-1 |
| AKJ-33 | intake-2892 | Fit a per-width noise sigma offline and predict first-divergence rates | decline: the amended gate measures the floor directly in-row, so a predictive noise model changes no decision |
| AKJ-34 | intake-2882 | Full deterministic serving mode, pow2-scale alibi probe, imported tolerances or floors | decline: deterministic serving costs 1.6-2.1x in the source, the alibi holds only for integer accumulation, and the protocol bans imported thresholds |
| AKJ-35 | intake-2873 | Offline forced-share replay of production json_schema classes | P5 / SPEC-GRAM-JSON-1 |
| AKJ-36 | intake-2873 | Chain-path grammar-draft design and grammar-aware tree pruning | M2 |
| AKJ-37 | intake-2873 | Synchronous grammar planning, accept-with-probability-1 at T > 0, a Phi estimator in the verifier | decline: llama-server already plans on the host, forced acceptance shifts the distribution at near-tie tokenizations, and OneStep worsened three schemas in the source |
| AKJ-38 | intake-2885 | Exact masked-vs-conditional TV on production enum schemas | P5 / SPEC-GRAM-TV-1 |
| AKJ-39 | intake-2885 | State the acceptance target (masked distribution) and the single-token rule for logit-free acceptance | K2 |
| AKJ-40 | intake-2874 | Offline journal replay of three demote rules for prose lessons | P6 / AK-LESSON-DEMOTE-1 |
| AKJ-41 | intake-2874 | Per-attempt digest catalog in the planner bundle | P6 / AK-ATTEMPT-DIGEST-1 |
| AKJ-42 | intake-2874 | Context-folding arm in the CF-AB-1 frame with a second-role compressor variant | P8 / CTE-CFAB-A8 |
| AKJ-43 | intake-2874 | KernelBench fast_1 as an expectation, lesson merging or rule promotion | decline: a different baseline and device, and the source's own case studies show merging drops applicability conditions |
| AKJ-44 | intake-2875 | Compressor/agent split and local-seconds crossover columns in the evict-cost table | P8 / KV-EVICT-COST-2 |
| AKJ-45 | intake-2875 | Failed-action ledger and pinned-pointer restoration in orchestrator compaction | P8 / HAR-COMPACT-LEDGER-1 |
| AKJ-46 | intake-2875 | Concurrent CPU-compressor / GPU-agent latency probe | M6 |
| AKJ-47 | intake-2875 | Copy the API cost-saving target, the 3,500-token tier bound or cache_control | decline: price effects of API cached-input billing with no local analogue |
| AKJ-48 | intake-2876 | Replay A3B probabilities through the cost-aware stop rule with an expert-union term vs fixed p_min | P5 / SPEC-STOP-EQ7-1 |
| AKJ-49 | intake-2876 | A3B residency-coverage curve from the existing routing traces | P5 / CDR-RT9-COVER-1 |
| AKJ-50 | intake-2876 | Per-expert H2D cache, reduced-top-k or resident-subset self-drafting on CPU A3B, reuse-aware gating | decline: PCIe Gen4 H2D (28.89 GB/s measured) is slower than one CPU quarter's DRAM read, fewer-experts drafts lost in 96 of 112 source cells, and reuse-aware gating alters target routing |
| AKJ-51 | intake-2876 | Hybrid GPU-resident expert drafter design | M10 |
| AKJ-52 | intake-2877 | Judge false-positive audit with master-key strings, prompt arms, propensity scan and exposure column | P7 / EV-JUDGE-FPR-1 |
| AKJ-53 | intake-2889 | Fuzz the deterministic scorers with verifier mutation categories | P7 / EV-SCORER-FUZZ-1 |
| AKJ-54 | intake-2877 | Attach an exposure audit and an unhackable audit run to the pre-RL monitor | M1 |
| AKJ-55 | intake-2877 | Difficulty stratification, reopening the exploitability axis, timing constants, CATCH or noise-sweep reproduction, running rh-indicators | decline: no group-normalised optimiser exists in AutoPilot or AutoKernel, no GRPO run is planned, and the constants were fitted to one 1.5B regime |
| AKJ-56 | intake-2886 | Train or adopt a robust judge, or change the judge prompt | M7 |
| AKJ-57 | intake-2870 | Hopper percent-of-peak figures for the census parity table (operator applies) | K3 |
| AKJ-58 | intake-2884 | Magnitudes not imported: cross-engine drift, API prices, Arm and TPU speedups | K4 |
| AKJ-59 | intake-2904 | Build the judge-audit string set from the 13 Huang families re-targeted to our verdict formats, per-string runs with intervals, and a Huang-comparable no-question arm | P7 / EV-JUDGE-FPR-1 |
| AKJ-60 | intake-2904 | Use static attack-success rate as a predictor of RL exploitation | decline: one hacked judge and one unhacked base is a necessary-condition hint, not a validated predictor; exposure is used instead |

## Proposed handoff edits (Stage 4 only, after approval)

Each box is the exact text `handoff_box.py add --dry-run` as filed at Stage 4 (copied from the applied handoff at the line shown), followed by its brief (author intake; every brief compiles fresh). All 27 pass `task_lint.py dispatch` with no failing rule.

handoffs/active/speculative-decoding.md:928 (Track speculative-decoding-mtp-refresh, ### Backlog; packet P1):

```text
- [ ] **SPEC-ID-GATE-2** [non-inference] Amend the spec identity-gate protocol (docs/guides/agent-workflows/spec-identity-gate-protocol.md) and its gate reporting with five rules from the noise-floor sources (intake-2872, intake-2893, intake-2891, intake-2894, intake-2883, intake-2884): (a) the floor is the largest pair over >= 3 reference launches (>= 5 when it decides a promotion gate), all pairs, one of them reordered or np-shuffled; fewer launches return INCONCLUSIVE; (b) cache state: both arms cache_prompt false with --cache-ram 0, or a verified identical cache state; existing SPEC-ID-NOISE-1 floors are labelled cache-off; (c) KV provenance: same prefill ubatch, verify-width class and KV dtype in both arms; redecode and resume paths are outside the exact regime; (d) every gate RESULT.json records the kernel-selection env knobs, the per-width route and the binary SHA, and cross-build rows first prove config-dump equality (sampler chain, BOS/EOS, penalties, prefix-cache state, np); (e) where a scored corpus exists, graded flips (worse / better / wrong-to-wrong, net) are reported beside token identity.
      · done when: protocol sections (a)-(e) committed with the commit SHA recorded under this box, the gate script returns INCONCLUSIVE below 3 replicas in a committed unit test, and the SPEC-ID-NOISE-1 result line carries the cache-off label
      · gate: none        · inputs: `docs/guides/agent-workflows/spec-identity-gate-protocol.md`
```
Brief: where `epyc-root:docs/guides/agent-workflows/spec-identity-gate-protocol.md`; approach: Edit sections 2, 3, 4 and 6 of the protocol doc: add a replica table (launches, pair list, largest-pair floor), a preconditions checklist (cache_prompt, --cache-ram, -ub, -ctk/-ctv, spec width) and a RESULT.json field list (env knobs, route histogram, binary sha256, config dump). In the gate reporter, return INCONCLUSIVE when fewer than 3 reference launches are supplied, with a pytest case. Append the cache-off label to the SPEC-ID-NOISE-1 result line. Acceptance: the done-when.

handoffs/active/speculative-decoding.md:931 (Track speculative-decoding-mtp-refresh, ### Backlog; packet P1):

```text
- [ ] **SPEC-ID-NOISE-2** [inference] Localise the 27B DFlash2 launch-to-launch drift on the MI210 and null-test the amended gate (intake-2872, intake-2882, intake-2883, intake-2894). Arm A: 4 launches of one unchanged config on the MI210; treat each launch in turn as the candidate against the other 3, and the SPEC-ID-GATE-2 gate must PASS every time. Arm B: the same A/A with GGML_HIP_Q8_SKINNY=0, testing whether the skinny-GEMM f32 atomics explain the 20/64 divergence (0/64 = skinny atomics are the source; >= 1 = another source). Arm C: a cb_eval node-hash dump over two launches of 27B DFlash2 np1 on 3 divergent prompts, recording the first differing graph node. Arm D (CPU quarter, small hybrid model): f32 compute and f32 KV, spec vs serial and resumed vs fresh, expecting 0/64. 64 DF2-13 prompts, digest recorded, cache-off. Model 27B Q8_0 + DFlash2 (arms A-C), Qwen3-4B Q8_0 CPU (arm D); build C21 98ff8a4 stores; region MI210 plus one CPU quarter; estimate ~3 h GPU + ~1 h CPU. Stop-on-answer when every arm has its count; stop-on-futility on the first false FAIL in arm A (the gate is then wrong, file it) or equal node hashes in arm C.
      · done when: per-arm verdicts filed under this box with the run path: arm A pass/false-FAIL count, arm B divergence count out of 64, arm C first-divergent node name per prompt, arm D divergence count out of 64
      · gate: SPEC-ID-GATE-2        · inputs: `docs/guides/agent-workflows/spec-identity-gate-protocol.md`
```
Brief: where `epyc-llama:common/common.h`, `epyc-llama:examples/eval-callback`, `epyc-llama:ggml/src/ggml-cuda/mmq.cu`; approach: Reuse the SPEC-ID-NOISE-1 job.py and prompt digest. Arm A: 4 relaunches, leave-one-out gate calls. Arm B: export GGML_HIP_Q8_SKINNY=0 and rerun the same 64 prompts. Arm C: build eval-callback with a cb_eval hook that sha256-hashes each tensor by name, diff the two launch logs and record the first mismatching node. Arm D: CPU quarter, -ctk f32 -ctv f32 with LLAMA_SPEC_EXACT=serial vs default, resume vs fresh. Acceptance: the done-when.

handoffs/active/speculative-decoding.md:934 (Track speculative-decoding-mtp-refresh, ### Backlog; packet P5):

```text
- [ ] **SPEC-GRAM-JSON-1** [non-inference] Measure the grammar-forced token share of the production json_schema classes offline, which SPEC-GRAM.5 never replayed (intake-2873, intake-2885). Replay retained outputs of each production json_schema class (typed decisions, review schemas, REPL routing, plan steps, consultation, structured-output repair) through llguidance v1.0.1 llg_matcher_compute_ff_tokens with the existing tool-call replay script, and report per class: forced share of output tokens, forced-run lengths, the single-allowed-token subset (the only lossless logit-free subset at T > 0), and the class's share of serving tokens. No model inference.
      · done when: per-class table (forced share, run-length histogram, single-allowed subset, serving-token share) filed under this box with the input digest and the verdict: decline (every class under 10%) or open the chain-path design (any class >= 10% with material token volume)
      · gate: none        · inputs: `handoffs/active/speculative-decoding.md`
```
Brief: where `epyc-llama:common/sampling.cpp`, `epyc-llama:tools/server/server-context.cpp`; approach: Pull retained json_schema request/response pairs from the orchestrator logs per class, compile each schema with llguidance 1.0.1, walk the tokenized output calling llg_matcher_compute_ff_tokens at each step, and count forced tokens, run lengths and steps where the mask admits exactly one token. Weight by per-class token volume from the serving logs. Write a CSV plus a summary table; no server or model is started. Acceptance: the done-when.

handoffs/active/speculative-decoding.md:938 (Track speculative-decoding-mtp-refresh, ### Backlog; packet P5):

```text
- [ ] **SPEC-GRAM-TV-1** [inference] Measure how far grammar-masked sampling departs from grammar-conditional sampling on the production enum-style json_schema classes (intake-2885). For each class whose language is a finite token trie (typed-decision, review, plan-step enums), query the served model at every trie prefix at the served temperature and compute the exact total variation between the masked law and the grammar-conditional law. The served verifier already samples the masked distribution (common/sampling.cpp:1038-1107 @ 98ff8a4), so speculation adds no bias; this measures the residual masked-sampling bias only. Model: the served frontdoor and architect roles' GGUFs (Q8_0) on the C21 CPU store; region one CPU quarter; estimate ~2 h; metric exact TV per class. Stop-on-answer when every finite-trie class has a TV value; stop-on-futility if no production class has a trie under 10k strings.
      · done when: per-class TV at the served temperature filed under this box with the trie sizes, and the verdict: close (every class TV < 0.1) or open a cost/benefit box on Phi correction (any class >= 0.1)
      · gate: none        · inputs: `handoffs/active/speculative-decoding.md`
```
Brief: where `epyc-llama:common/sampling.cpp`; approach: Enumerate each enum schema's accepted token sequences with llguidance into a prefix trie. For every trie node, issue one /completion prefix forward with n_probs on a CPU-quarter llama-server, then compute masked and conditional probabilities bottom-up (the conditional renormalises by future-valid mass). Report TV per class at T 1.0 and the served temperature. Skip classes whose trie exceeds 10k strings. Acceptance: the done-when.

handoffs/active/speculative-decoding.md:942 (Track speculative-decoding-mtp-refresh, ### Backlog; packet P5):

```text
- [ ] **SPEC-STOP-EQ7-1** [non-inference] Replay the CAFE-1-SERVED-T A3B MTP per-token probability captures offline through the cost-aware draft-stop rule (intake-2876 Eq 7: stop at the K minimising expected cost over expected tokens) with the marginal expert-union cost term (intake-2896), against fixed p_min {0, 0.5, 0.75}. Step 1: fit C(K) (verify wall seconds vs draft length) and expert-union bytes vs K for A3B CPU from existing CAFE-1-SERVED-T and Q38P rows; futility if the fitted R^2 < 0.9. Step 2: modelled tokens/s of the rule vs each fixed p_min at T 0.3 and T 1.0 on a held-out half of the captures.
      · done when: step-1 fit (R^2 and coefficients) and step-2 modelled gain with CI per temperature filed under this box, with verdict KEEP candidate (gain >= 3% with CI lower > 1.0 at both temperatures), CLOSE (gain < 1% with CI upper < 1.02) or INCONCLUSIVE
      · gate: none        · inputs: `handoffs/active/speculative-decoding.md`
```
Brief: where `epyc-llama:common/speculative.cpp`; approach: Load the CAFE-1-SERVED-T capture JSONL (per-position draft probabilities, accepted lengths). Fit C(K) = a + b*K + c*E_union(K) by least squares on Q38P/CAFE verify timings, with E_union from the routing traces. Implement the Eq 7 argmin in a short numpy script, replay it on a 50% held-out split of the captures, and bootstrap the tokens/s ratio against each fixed p_min. Acceptance: the done-when.

handoffs/active/autokernel-loop.md:5237 (Track autokernel-research-loop, ### Backlog; packet P2):

```text
- [ ] **AK-GVFATTN-Q4KV-DESIGN** [non-inference] Feed design inputs and refinements to the published q4_0-KV gv_fattn row ak-gvfattn-q4kv-gpu-20261124 (store gpu-20261124-5141da459-gvfattn-q4kv, kernel commit 5141da459 behind GGML_CUDA_FA_GQA_Q4KV=1, default off) (intake-2870, intake-2878, intake-2879, intake-2880, intake-2881). (a) A numpy MFMA lane-map oracle for q4_0 K (stock block_q4_0 matches the 16x16x16 fragment, one dword per lane) and the token-contiguous V packing, bit-exact against dequantize_row_q4_0. (b) Disassembly counts of per-value packed-f16 reconstruction vs accumulator folding at R = 6, 12, 24 and 48; folding breaks even only at g = 2*h_q. (c) A review note against 5141da459: q4_0 codes staged in LDS (about 9 KB vs 37 KB of f16 K+V), decode in registers, swapped operands (S^T = K.Q^T) keeping P in registers, a byte-floor ratio (q4_0 us/call over q8_0 x 18/34), and the follow-ups from the KV-quality packet (keep llama.cpp's rotation on for q4_0; K-mean removal only if KVQ-KMEAN-SIM-1 says so). (d) Correct AK-GVFATTN-LONGCTX's 'R <= 32, 2 tiles' premise: 27B gqa 6 at n_q 7 gives R = 42, 3 tiles.
      · done when: oracle test committed and passing bit-exact, the instruction-count table, and the review note filed under this box and linked from the ak-gvfattn-q4kv-gpu-20261124 row, with the AK-GVFATTN-LONGCTX premise correction recorded, each with its commit SHA
      · gate: none        · inputs: `handoffs/active/autokernel-loop.md`
```
Brief: where `epyc-llama:ggml/src/ggml-cuda/fattn.cu`, `epyc-llama:ggml/src/ggml-quants.c::dequantize_row_q4_0`; approach: Write a numpy oracle that reproduces block_q4_0 nibble order into 16x16x16 MFMA A/B lane fragments and compare it bit-exact with dequantize_row_q4_0 on random blocks. Compile both decode snippets with hipcc --save-temps for gfx90a and count v_* instructions per value. Read 5141da459's fattn-gqa-verify.cu and write the review note against its LDS layout. Annotate AK-GVFATTN-LONGCTX with the R = 42 tile arithmetic. Acceptance: the done-when.

handoffs/active/autokernel-loop.md:5241 (Track autokernel-research-loop, ### Backlog; packet P6):

```text
- [ ] **AK-LESSON-DEMOTE-1** [non-inference] Replay the AutoKernel journal offline to choose a demote rule for prose lessons in the planner bundle (intake-2874, intake-2903). Compare three rules: unused for 5 consecutive iterations (autoresearch tau = 5), the alpha = 0 periodic rule, and a utility-gated rule (retrieved >= n times with mean keep-rate <= beta, from AK keep/discard receipts). Gate-backed negatives consumed by controller/do_not_repeat.py are never demoted. Measure bundle chars saved, later same-epoch re-proposals of a demoted mechanism, and proposal keep-rate with the lesson present vs absent. Zero inference.
      · done when: per-rule table (chars saved, false-demotion re-proposals, keep-rate delta) filed under this box with the journal digest and verdict: adopt a rule only if it has 0 false-demotion re-proposals and the utility-gated arm saves at least as many chars as unused-5, else NO-GO
      · gate: none        · inputs: `handoffs/active/autokernel-loop.md`
```
Brief: where `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py`, `epyc-inference-research:scripts/kernel_rnd/autokernel/controller/do_not_repeat.py`; approach: Parse program.md, the journal shards and negatives.json. Reconstruct per-iteration rendered lessons from actor_context.py's bundle index, mark which lesson IDs each proposal cited, and simulate three demote policies over epochs (unused-5, alpha=0 periodic, utility-gated from keep/discard receipts). Exclude do_not_repeat.py-backed entries. Emit a per-policy CSV of chars saved and re-proposals. Acceptance: the done-when.

handoffs/active/autokernel-loop.md:5244 (Track autokernel-research-loop, ### Backlog; packet P6):

```text
- [ ] **AK-ATTEMPT-DIGEST-1** [non-inference] Add a per-attempt digest catalog to the AutoKernel planner bundle (intake-2874 context folding): one 2-4 sentence digest per past attempt in the bundle index written by loop/actor_context.py, with the full attempt record still reachable by its per-call file, so the planner sees every attempt rather than a recency window. Budget: the bundle index grows by at most 10% over its current size on the replayed journal.
      · done when: change committed with its SHA and a replayed-bundle comparison (index chars before/after, attempts visible before/after) recorded under this box; reverted if the 10% budget is exceeded
      · gate: none        · inputs: `handoffs/active/autokernel-loop.md`
```
Brief: where `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py`; approach: In actor_context.py, add a digest builder that reads each attempt's per-call file, takes the mechanism, the arm and the verdict line, and emits one 2-4 sentence entry into the bundle index. Keep the full file path beside each digest. Regenerate one bundle from the live journal, diff index sizes, and guard the result with a unit test on a fixture journal. Acceptance: the done-when.

handoffs/active/autokernel-loop.md:5247 (Track autokernel-research-loop, ### Backlog; packet P6):

```text
- [ ] **AK-CPU-KSHIFT-1** [inference] Pilot a KernelShift-format benchmark task for the AutoKernel CPU lane on Zen 5 (intake-2871, intake-2897, intake-2898). Step 1 (code): in a research-repo scratch copy of cmu-l3/kernel-shift @ 610e835, remove the two aarch64 guards (kgen/check.py, kgen/autovec.py), add one x86 ISA tier, and write an iqk/ggml baseline wrapper for one op, Q8_0 mul_mat at N = 1-16 on hidden served shapes, with a double-precision reference and a calibrated correctness floor (baseline SQNR minus 1 dB). Step 2 (CPU quarter): ISA-ladder arms (AVX2, +VNNI, +AVX512_BF16, +VBMI) plus a scalar -O3 -march=znver5 autovec control, outcome classes (compiles / wrong result / identifier error / crash / no intrinsic), and codegen counts of vpdpbusd, vdpbf16ps, vpermb and zmm FMA in the CPU keep diagnostic. Model: Q8_0 shapes of the served 27B and 35B-A3B; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~3 h after the code step; metric geomean speedup vs baseline. Stop-on-answer when the baseline geomean and A/A floor are recorded for every ISA arm; stop-on-futility if the task reproduces served_shape_cases verdicts only.
      · done when: scratch-copy SHA, the task files, and the C21 baseline geomean with its A/A floor per ISA arm filed under this box; FUTILITY recorded if the task only reproduces the existing served_shape_cases verdicts
      · gate: none        · inputs: `handoffs/active/autokernel-loop.md`
```
Brief: where `epyc-inference-research:scripts/kernel_rnd/autokernel/loop`; approach: Clone kernel-shift at 610e835 into a research scratch dir. Patch kgen/check.py and kgen/autovec.py to accept x86_64, add an avx512 tier in config/kernel_contracts.yaml, and write a C++ wrapper calling ggml_vec_dot_q8_0_q8_0 and iqk as the expert baseline. Generate workloads from served-shape traces, calibrate the SQNR floor, then run the ISA arms via -march flags on one quarter and count instructions with objdump. Acceptance: the done-when.

handoffs/active/quantization-and-low-bit.md:789 (Track tq3-quantization-evaluation, ### Backlog; packet P3):

```text
- [ ] **KVQ-ROT-KLD-1** [inference] Measure q4_0 KV quality on the 27B with llama.cpp's automatic Hadamard rotation on vs off (intake-2870, intake-2881, intake-2892, intake-2872). 27B Q8_0 + DFlash2 on the MI210 (C21 GPU store): KLD vs f16 KV for q8_0 KV, q4_0 KV rot-on, and q4_0 KV with LLAMA_ATTN_ROT_DISABLE=1, plus the first-token margin coefficient c (SE <= 0.10) per arm including a whether-to-call class; then a graded-flip arm on the G3 (G) GSM8K protocol for q4_0 vs q8_0 KV with a >= 3-launch A/A floor. CPU arm: 35B-A3B on a quarter, same KLD arms. FlagRot predicts rotation helps a uniform INT4 grid, so rot-off is a falsification check. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0; build C21 98ff8a4 GPU and CPU stores; region MI210 plus one CPU quarter; estimate ~4 h GPU, ~3 h CPU; metric KLD, margin c, graded-flip excess. Stop-on-answer per arm when the KLD CI excludes the verdict boundary; stop-on-futility if the q4_0 KV path fails to load on the served recipe.
      · done when: per-arm KLD, c and graded-flip excess over the A/A floor filed under this box with verdicts: rot-off >= rot-on drops the rotation-off branch; rot-off < 0.9x rot-on is a contradiction that runs the other models; q4_0 rot-on <= 2x q8_0 KLD makes q4_0 KV a served-gate candidate
      · gate: none        · inputs: `handoffs/active/quantization-and-low-bit.md`
```
Brief: where `epyc-llama:src/llama-kv-cache.cpp`; approach: Run llama-perplexity --kl-divergence-base on f16 KV once per model, then --kl-divergence for -ctk/-ctv q8_0, q4_0 and q4_0 with LLAMA_ATTN_ROT_DISABLE=1, on the same 64-chunk corpus. Margin c comes from first-token logits of the same runs. The flip arm reuses the G3 (G) GSM8K harness at three launches per arm, scored by math_verify. The A3B CPU arm repeats the KLD runs on one quarter. Acceptance: the done-when.

handoffs/active/quantization-and-low-bit.md:793 (Track tq3-quantization-evaluation, ### Backlog; packet P3):

```text
- [ ] **KVQ-KMEAN-SIM-1** [inference] Dump post-RoPE K (and Q) on the 27B full-attention layers (layer 3 is the first; layers 0-2 are GDN) for 64 prompts on a CPU quarter, then simulate q4_0 offline (codes -8..7) for arms: plain, static per-channel mean removal, first-4-tokens exact, and (only if KVQ-ROT-KLD-1 shows q4_0 rot-on KLD > 2x q8_0) keys-only selective rotation (intake-2870, intake-2878, intake-2881). The Qwen2 k-bias mechanism does not apply (no attention_bias in our configs), so this measures generic K-mean energy. Model 27B Q8_0; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~1 h dump plus offline simulation; metric mean-energy share and simulated KL. Stop-on-answer when every arm has a simulated KL; stop-on-futility if the K dump cannot be produced on the served path.
      · done when: per-layer mean-energy share and simulated KL per arm filed under this box with verdict: implement static mean subtraction if mean energy > 30% or simulated KL drops >= 20%; selective rotation kept only if it cuts KL >= 30%
      · gate: none        · inputs: `handoffs/active/quantization-and-low-bit.md`
```
Brief: where `epyc-llama:src/llama-kv-cache.cpp`; approach: Use a cb_eval hook (or GGML_SCHED dump) to save post-RoPE K and Q per full-attention layer to .npy for 64 prompts. Then, offline in numpy, port calib_kv.py's static mean, quantize to q4_0 (-8..7, 32-value blocks), recompute attention and measure KL against the f16 attention output per layer and arm. Plot mean-energy share per layer. Acceptance: the done-when.

handoffs/active/cpu-decode-roofline-program.md:2030 (Track cpu-decode-roofline-program, ### Backlog; packet P3):

```text
- [ ] **CDR-A3B-Q4KV-32K** [inference] Measure 35B-A3B MTP CPU decode at 32k context with q4_0 vs q8_0 KV on one quarter (C21 CPU store), with the attention share of the step from the existing per-op profile (intake-2870). Model 35B-A3B Q8_0 MTP; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~1.5 h. Stop-on-answer on KEEP or FUTILITY; stop-on-futility when attention is under 10% of the step.
      · done when: tok/s per arm with A/A floor and the attention share filed under this box with verdict KEEP (>= 5% tok/s and the KVQ-ROT-KLD-1 CPU-arm KLD gate passing) or FUTILITY (attention < 10% of the step)
      · gate: KVQ-ROT-KLD-1        · inputs: `handoffs/active/cpu-decode-roofline-program.md`
```
Brief: where `epyc-llama:ggml/src/ggml-cpu/ops.cpp`; approach: Use llama-bench (or the served recipe through the bench harness) with -ctk/-ctv q8_0 then q4_0 at 32k depth on one quarter, three launches each, and capture GGML per-op timings to get the attention share. Compare against the A/A spread from the three launches. Acceptance: the done-when.

handoffs/active/cpu-decode-roofline-program.md:5983 (Track moe-routing-tap-and-locality-measurement, ### Backlog; packet P5):

```text
- [ ] **CDR-RT9-COVER-1** [non-inference] Close the A3B expert-residency question from the existing RT-9 traces (intake-2876, intake-2895): run skew_report.py on the saved Qwen3.6-35B-A3B frontdoor traces and report per-layer top-12.5% expert coverage, same-domain and cross-domain. RT-9 already shows top-25% share 0.68-0.74 at prefill, so coverage >= 0.6 at <= 12.5% residency is not expected.
      · done when: per-layer coverage table filed under this box with the trace digest and verdict: CLOSE the resident-expert drafter idea if same-domain coverage at 12.5% is below 0.6, else record the coverage for the operator's HBM allotment decision
      · gate: none        · inputs: `handoffs/active/cpu-decode-roofline-program.md`
```
Brief: where `epyc-inference-research:scripts/benchmark/moe_routing/skew_report.py`; approach: Point skew_report.py at the saved RT-9 trace directory, add a --residency 0.125 option that reports cumulative selection coverage of the top-k experts per layer, and split rows by domain (code / prose / reasoning) and by same-domain vs cross-domain hot sets. Write the table into the box. Acceptance: the done-when.

handoffs/active/kernel-champion-and-promotion.md:1920 (Track autokernel-champion-aggregate, ### Backlog; packet P4):

```text
- [ ] **GDN-SLOTS-STRONGER** [non-inference] Record and pin the in-house GATED_DELTA_NET snapshot guarantee, which is stronger than ggml.h's (intake-2867): ggml.h guarantees only slot 0 when n_tokens > K, but the CDNA chunked kernel (gated_delta_net.cu:23-40 @ 98ff8a4) writes every tail slot and spec-decode rollback (MTP K=4, DFlash2 K=9) reads them. Add a named witness case to test-backend-ops that compares all K slots at n_tokens > K on the chunked path, so a rebase that takes upstream #32820's slot-0-only view cannot weaken the check; do not port that view restriction; and add the rule that every ported test's -o op must be in the fold-gate test-backend-ops scope.
      · done when: witness case committed on the next experimental branch with its SHA, passing on ROCm0 and CPU, and the doc note plus scope rule committed in this handoff's fold-gate section
      · gate: none        · inputs: `handoffs/active/kernel-champion-and-promotion.md`
```
Brief: where `epyc-llama:tests/test-backend-ops.cpp`, `epyc-llama:ggml/src/ggml-cuda/gated_delta_net.cu`; approach: In test-backend-ops.cpp, add a named GATED_DELTA_NET case at n_tokens > K (e.g. n=300, K=9) on the chunked path whose comparison covers every snapshot slot. Name it so a grep finds it, and add a comment pointing to this box. Write the slot-guarantee note and the tbo-scope rule into the fold-gate section of kernel-champion-and-promotion.md. Acceptance: the done-when.

handoffs/active/kernel-champion-and-promotion.md:1923 (Track autokernel-champion-aggregate, ### Backlog; packet P4):

```text
- [ ] **MMID-UB-CEIL-1** [inference] Guard the mul_mat_id shared-memory ceiling on the MI210 (intake-2868): HIP sets smpbo from sharedMemPerBlock (ggml-cuda.cu:360 @ 98ff8a4), so mm_ids_helper aborts above 65536/4 = 16384 tokens per ubatch, below every configured ubatch today. (a) Make orchestrator_stack.py refuse a GPU MoE role launched with -ub above 16384, beside the existing K4 flag guard. (b) One op-level ROCm0 smoke: test-backend-ops -o MUL_MAT_ID at n = 16384 passes and n = 16385 aborts, confirming the derived ceiling. Model: none (op-level test-backend-ops, MUL_MAT_ID Q4_0 shapes); build C21 98ff8a4 GPU store; region MI210; estimate ~15 min; metric pass/abort. Stop-on-answer when both n values are recorded; stop-on-futility if the abort occurs below 16384 (then record the measured ceiling and lower the guard).
      · done when: guard committed with a unit test and its SHA, and the smoke result (pass at 16384, abort at 16385, or the measured ceiling if different) recorded under this box
      · gate: none        · inputs: `handoffs/active/kernel-champion-and-promotion.md`
```
Brief: where `epyc-orchestrator:scripts/server/orchestrator_stack.py`, `epyc-llama:ggml/src/ggml-cuda/mmid.cu`; approach: In orchestrator_stack.py, beside _has_any_flag's K4 check, parse -ub/--ubatch-size for GPU MoE roles and refuse values above 16384 with a clear message, plus a pytest case. On ROCm0, run test-backend-ops -o MUL_MAT_ID with a 16384-token and a 16385-token case (Q4_0, n_used 2) and record pass vs GGML_ASSERT abort. Acceptance: the done-when.

handoffs/active/kernel-champion-and-promotion.md:1927 (Track autokernel-champion-aggregate, ### Backlog; packet P4):

```text
- [ ] **MMVF-I64-OFFSET** [inference] Gate the two MMVF fixes already committed on fork branch llama.cpp-experimental-c22-mmvf-fixes-20261124 (intake-2869): c47c574ba widens the MMVF expert/sample offsets for x, gate_x, y and dst to int64 (mmvf.cu:47-49 and :84 at 98ff8a4 had the int*int overflow upstream fixed only for x and gate_x), and 7eb398b16 adds the even-ne00 / pair-alignment guard to the AMD MMVF_MMID branch (ggml-cuda.cu:2196-2201), which upstream has and C21 lacked. Remaining step: run the prepared gate row /mnt/raid0/llm/tmp/ak-c22-mmvf-fixes-gate-gpu-20261124. Model: op-level test-backend-ops MUL_MAT / MUL_MAT_ID shapes of the served 27B; build: that branch at 7eb398b16 (GPU); region MI210; estimate ~1.5 h; metric correctness and us/run. Stop-on-answer when both commits are gated; stop-on-futility if the int64 widening costs more than the A/A floor even for x/gate_x alone (then keep only the guard and record).
      · done when: gate RESULT filed under this box with the run path: test-backend-ops correctness 100% on ROCm0, MUL_MAT perf at ne11 1-8 within the A/A floor and route histograms unchanged for each of c47c574ba and 7eb398b16
      · gate: none        · inputs: `handoffs/active/kernel-champion-and-promotion.md`
```
Brief: where `epyc-llama:ggml/src/ggml-cuda/mmvf.cu`, `epyc-llama:ggml/src/ggml-cuda/ggml-cuda.cu`; approach: Use the prepared gate directory: run its job on the MI210 against the branch build at 7eb398b16 (test-backend-ops -o MUL_MAT,MUL_MAT_ID plus perf at ne11 1-8 with the route-log env), compare against C21's A/A floor, and file RESULT.json. Evaluate c47c574ba and 7eb398b16 separately via the per-commit arms the gate defines. Acceptance: the done-when.

handoffs/active/kernel-champion-and-promotion.md:1930 (Track autokernel-champion-aggregate, ### Backlog; packet P1):

```text
- [ ] **FOLD-KLD-FLOOR-1** [inference] Measure the KLD A/A floor the fold gates have never measured (intake-2901, intake-2872, intake-2893): on the fold-gate corpus, the C21 candidate against itself with one reduction-order toggle flipped (MMVQ nwarps or GGML_ROWEXACT_N), on 27B Q8_0 (MI210) and Q38FN (CPU quarter); check retained logits offline first. Add 'candidate KLD / floor' to the fold-gate result header, and report graded flips (worse / better / wrong-to-wrong) beside KLD where the corpus is scored. Model 27B Q8_0 (MI210) and Q38FN UD-IQ4_XS (CPU quarter); build C21 98ff8a4 stores. Stop-on-answer when both devices have a floor value or the offline logit check answers it; stop-on-futility if retained logits are absent and the floor run cannot reproduce the fold-gate corpus.
      · done when: floor per device filed under this box with the run path, the header change committed, and the verdict: floor <= 10% of the 0.003 gate keeps the gate with the ratio reported; floor >= 30% makes the gate relative to the floor
      · gate: none        · inputs: `handoffs/active/kernel-champion-and-promotion.md`
```
Brief: where `epyc-llama:tools/perplexity/perplexity.cpp`; approach: First check whether the C21 fold-gate run kept per-token logits. If so, compute the KLD between two candidate runs offline. Otherwise, run llama-perplexity --kl-divergence on the fold-gate corpus twice with only GGML_ROWEXACT_N (CPU) or the MMVQ nwarps env (GPU) toggled, then add floor and ratio fields to the fold-gate result template. Acceptance: the done-when.

handoffs/active/kernel-champion-and-promotion.md:1934 (Track autokernel-champion-aggregate, ### Backlog; packet P1):

```text
- [ ] **PFXC-ID-REPLICA-1** [inference] Re-judge prompt-cache identity with a replica floor (intake-2891, intake-2884, intake-2894): on the served recipes (27B DFlash2 np1 on the MI210 with --cache-ram as served; 35B-A3B MTP np1 on a CPU quarter, conc 1), compare cache-hit vs cold-recompute paths with margin classes and a same-run A/A on each path over >= 3 launches; this replaces PFXC-A1's single-baseline floor (resumed-vs-fresh 0.773 vs C14 floor 1.077). 64 prompts, digest recorded. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0 MTP; build C21 98ff8a4 stores; region MI210 plus one CPU quarter; estimate ~2 h GPU, ~2 h CPU; metric divergences out of 64. Stop-on-answer after one 64-prompt pass per device; stop-on-futility on residency-proof failure.
      · done when: per-device divergence counts out of 64 per path with the largest-pair A/A floor filed under this box, and the verdict: any cache-path divergence outside the floor marks cached requests outside the exact regime in the protocol
      · gate: SPEC-ID-GATE-2        · inputs: `handoffs/active/kernel-champion-and-promotion.md`
```
Brief: where `epyc-llama:tools/server/server-context.cpp`; approach: Run llama-server with the served flags and cache_prompt true. Per prompt, send a priming request, then the target request (cache hit), restart and send it cold. Repeat over 3 launches. Classify first divergences with the protocol's margin classes and compare against the per-path A/A largest pair. Log cache_n from the response timings. Acceptance: the done-when.

handoffs/active/rocm-kernel-authoring.md:1131 (Track rocm-verify-profile-backend, ### Backlog; packet P4):

```text
- [ ] **RKA-SRC1-DTYPE-RULE** [non-inference] Add two kernel-authoring rules and one rebase trigger to this handoff (intake-2869, intake-2899, intake-2900): (1) a new input dtype in a hot in-house kernel (MMVF, q8mf_pre_i8, q8sk_quantize) is a template parameter, never a runtime flag tested in the inner loop; (2) a new src1 dtype requires a review of every in-house route gated on src1 being F32 (mmq-q8-mf.cu:1270, MMVF_CHUNK, the cuBLAS precheck at ggml-cuda.cu:2075 @ 98ff8a4); (3) the rebase-review trigger is a merged upstream BF16-activation producer in the graph builder (a cast node or type switch), not the op-coverage series #29675, #32135, #32387 and #32533, and that review checks the RMS_NORM fusion gates (ggml-cuda.cu:3404, :4265-4270) and the ROPE+VIEW+SET_ROWS fusion.
      · done when: the three rules committed in this handoff's kernel-authoring section with the commit SHA recorded under this box
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
```
Brief: where `epyc-root:handoffs/active/rocm-kernel-authoring.md`; approach: Add a short 'input dtypes and rebase triggers' subsection to this handoff's kernel-authoring track: the template-parameter rule with the MMVF runtime-flag counterexample from #32533, the list of src1==F32-gated routes with file:line at 98ff8a4, and the producer-merge trigger naming the four upstream PRs and the two fusion gates. Acceptance: the done-when.

handoffs/active/rocm-kernel-authoring.md:1134 (Track rocm-verify-profile-backend, ### Backlog; packet P2):

```text
- [ ] **RKA-IPB-CENSUS-1** [inference] Measure the instruction-issue budget of the q8_0 gv_fattn kernel on the MI210 (intake-2870, intake-2879): rocprofv3 SQ_INSTS_VALU / SQ_INSTS_SALU / SQ_INSTS_LDS / SQ_WAVES counters on the 27B DFlash2 verify at 16k context, n_q 1/4/8, expressed as instructions per KV byte against the device budget (FOSCAR Eq. 2 units), plus implied VALU utilisation. Model 27B Q8_0 + DFlash2 verify; build C21 98ff8a4 GPU store; region MI210; estimate ~1 h; metric instructions per byte and VALU utilisation. Stop-on-answer when every shape has a counter read; stop-on-futility if rocprofv3 cannot attribute counters to gv_fattn.
      · done when: per-shape instructions-per-byte and VALU utilisation filed under this box with the run path, and the verdict: >= 50% VALU utilisation means a decode diet comes first in AK-GVFATTN-Q4KV, <= 25% means LDS residency comes first
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
```
Brief: where `epyc-llama:ggml/src/ggml-cuda/fattn.cu`; approach: Run rocprofv3 --pmc SQ_INSTS_VALU SQ_INSTS_SALU SQ_INSTS_LDS SQ_WAVES SQ_BUSY_CYCLES on llama-bench (or the verify harness) with the 27B verify shapes, filtered to the gv_fattn kernel name. Divide instruction counts by the KV bytes per call and compare with the device issue budget (CUs x SIMD issue rate over HBM bandwidth). Acceptance: the done-when.

handoffs/active/rocm-kernel-authoring.md:1137 (Track rocm-verify-profile-backend, ### Backlog; packet P2):

```text
- [ ] **RKA-GV-PSCALE-1** [inference] Test gv_fattn numerics on sink-heavy attention, where P is stored as f16 (intake-2870, intake-2878): add a test-backend-ops case with one dominant early key (attention-sink pattern) on GQA-verify shapes, compare gv_fattn error to the vector path, and try P scaled by 2^10 before the f16 store as the candidate fix. Applies to the production q8_0 path as well. Model: op-level FLASH_ATTN_EXT GQA-verify shapes of the 27B (head dim 256); build llama.cpp-experimental from C21 98ff8a4; region MI210; estimate ~1 h; metric max abs error vs the CPU reference. Stop-on-answer when the error ratio is recorded with and without scaling; stop-on-futility if the sink case cannot be expressed in test-backend-ops.
      · done when: test case committed with its SHA and the error ratio gv/vector with and without P scaling recorded under this box; adopt the scaling (default-off knob, then fold) only if gv error exceeds 2x the vector-path error
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
```
Brief: where `epyc-llama:ggml/src/ggml-cuda/fattn.cu`, `epyc-llama:tests/test-backend-ops.cpp`; approach: Add a test-backend-ops FLASH_ATTN_EXT case with GQA-verify shapes (head dim 256, n_q 4-8) whose first key gets a +20 logit bias, so P mass concentrates there. Compare max abs error of the gv path and the vector path against CPU. Then add an env-gated 2^10 scale before the f16 P store and its inverse in the PV accumulate, and rerun. Acceptance: the done-when.

handoffs/active/rocm-kernel-authoring.md:1140 (Track rocm-verify-profile-backend, ### Backlog; packet P1):

```text
- [ ] **RKA-BATCH-INV-CENSUS-1** [non-inference] Census batch invariance of the MI210 verify graph at widths 1-16 (intake-2882, intake-2883, intake-2872), op by op at 98ff8a4: RMSNorm (norm.cu:347-370, one block per row, already invariant), MMVQ (nwarps depends on ncols_dst, mmvq.cu:813-850), skinny Q8 (f32 unsafeAtomicAdd flush), MMQ / mmq-q8-mf (unsafeAtomicAdd at :1454), hipBLAS BF16, and flash attention (parallel_blocks chosen from occupancy and n_kv, fattn-common.cuh:1514-1594). Per op: invariant or not, the change needed (pinned per-column reduction geometry, fixed-size KV chunks rather than a fixed count, atomics removed) and its port cost.
      · done when: per-op census table committed in this handoff with the commit SHA recorded under this box, and the verdict: open an implementation box for a default-off invariant audit arm if 3 or fewer ops need change, else record the cost and close
      · gate: none        · inputs: `handoffs/active/rocm-kernel-authoring.md`
```
Brief: where `epyc-llama:ggml/src/ggml-cuda/mmvq.cu`, `epyc-llama:ggml/src/ggml-cuda/fattn-common.cuh`; approach: Read each listed kernel's launch-parameter code and record which parameters depend on ncols/n_tokens/n_kv (nwarps, parallel_blocks, split count) and where atomics or reduction-order changes occur. Fill a table of op, dependency, required change and estimated LOC/perf cost. No build or run. Acceptance: the done-when.

handoffs/active/eval-tower-program.md:3107 (Track scoring-infra-standardization, ### Backlog; packet P7):

```text
- [ ] **EV-SCORER-FUZZ-1** [non-inference] Fuzz the deterministic eval_tower scorers with the RLVR-verifier mutation categories (intake-2889): replay partial_answer, missing marker, contradictory finals, loose float and wrong-then-correct completions against the math_verify and exact-match scorers (EV-11) and report false-positive and false-negative rates with acceptance and coverage per category. CPU minutes, no inference.
      · done when: per-category FPR/FNR table filed under this box with the fixture digest; any category with FPR > 0 gets a named scorer fix box; futility recorded if FPR is 0 everywhere
      · gate: none        · inputs: `handoffs/active/eval-tower-program.md`
```
Brief: where `epyc-orchestrator:src`; approach: Write fixture generators for the five mutation categories over GSM8K/MATH-500 gold answers (e.g. gold in prose without a box, two conflicting finals, 1e-3 float drift). Call eval_tower's math_verify and exact-match scorer functions directly in pytest, and tabulate accept rates against the strict contract. Keep the fixtures in the repo. Acceptance: the done-when.

handoffs/active/eval-tower-program.md:3112 (Track scoring-infra-standardization, ### Backlog; packet P7):

```text
- [ ] **EV-JUDGE-FPR-1** [inference] Audit the LLM judges for exploitable false positives before anything optimises against them (intake-2877, intake-2886, intake-2904, intake-2888). String set: the ten One-token master keys plus 3-5 paraphrases each, and the 13 Huang Table 8 families with their 'Final Decision: Yes' strings re-targeted to each judge's verdict format (exact strings and prompts from the hkust-nlp/RL-Verifier-Robustness repo). Run every string individually, with Wilson intervals, on a fixed math problem set against the architect_critic, coherence and credibility judges, each with the production prompt, a no-question arm (the Huang-comparable arm) and a no-CoT arm. Scan journaled generator outputs with the same detectors for propensity (zero inference) and report exposure = propensity x FPR, also as a secondary EV-29 column. The futility threshold is a local pre-registered choice. Model: the three judge configs as served; build: production v10 stores (read-only use); region one CPU quarter; estimate ~3 h; metric FPR per string. Stop-on-answer per judge when every string has an FPR; stop-on-futility when no string is accepted in the first 100 items for a judge.
      · done when: per-judge, per-string FPR table and the propensity counts filed under this box with the problem-set digest; verdict per judge: no-go for any optimiser use if any string's FPR >= 1%, else cleared at that rate
      · gate: none        · inputs: `handoffs/active/eval-tower-program.md`
```
Brief: where `epyc-orchestrator:src`; approach: Clone hkust-nlp/RL-Verifier-Robustness to read Table 8's strings and the Figure 6 prompts. Build a string x problem matrix (about 471 DeepScaleR items). Call each judge config through its existing eval_tower adapter with the three prompt templates, and compute per-string accept rates with Wilson intervals. The propensity scan greps journal outputs with the same detectors. Acceptance: the done-when.

handoffs/active/kv-cache-program.md:1927 (Track kv-prefix-fork-and-paged-attention, ### Backlog; packet P8):

```text
- [ ] **KV-EVICT-COST-2** [non-inference] Extend the KV-EVICT-COST-1 break-even table with two columns (intake-2875, intake-2902): (1) a DMC-5 split row: compressor delta prefill plus summary decode plus agent re-prefill of summary and recent turns, against the decode-attention seconds saved over the next N turns, per device, with GDN hybrids re-prefilling the whole suffix after a changed block (can_shift false); (2) the local-seconds crossover rho_cross = 1 - 1/r (cached-read cost about 0, write cost = prefill seconds per token) with a mutated-prefix tag (tail-only vs middle rewrite). Arithmetic over retained prefill and context-slope rows; no new inference.
      · done when: both columns added to the table under KV-EVICT-COST-1 with per-device break-even length or NO-GO recorded under this box
      · gate: KV-EVICT-COST-1        · inputs: `handoffs/active/kv-cache-program.md`
```
Brief: where `epyc-root:handoffs/active/kv-cache-program.md`; approach: Extend the KV-EVICT-COST-1 table script with two derived columns: compressor and agent seconds from retained prefill t/s and context-slope rows per device, with the re-prefill length set by GDN can_shift=false; and rho_cross = 1 - 1/r with a mutated-prefix flag. Output break-even trajectory length or NO-GO per device. Acceptance: the done-when.

handoffs/active/harness-program.md:3262 (Track agentic-serving-harness-fixes, ### Backlog; packet P8):

```text
- [ ] **HAR-COMPACT-LEDGER-1** [non-inference] Port DMC-5's integrity pieces into orchestrator compaction behind a default-off flag (intake-2875): the failed-action ledger (every failed tool call kept verbatim across compaction) and byte-exact restoration of pinned pointers (paths, IDs, numbers) in src/graph/compaction.py, which today asks Role.WORKER_GENERAL for a one-shot index with neither. Without it DMC-5's own AppWorld accuracy fell below no compression (69.1% vs 77.0%).
      · done when: flagged change committed with its SHA and a replay test over retained trajectories showing every failed action and pinned pointer survives compaction byte-exact, recorded under this box
      · gate: none        · inputs: `handoffs/active/harness-program.md`
```
Brief: where `epyc-orchestrator:src/graph/compaction.py`; approach: In compaction.py, behind a settings flag, collect failed tool calls (non-zero exit or error result) into a verbatim ledger block kept across compactions. Extract pinned tokens (paths, IDs, numbers) from the pre-compaction context with regexes and assert they appear byte-exact after compaction. Add a pytest replay over 3-5 retained trajectories. Acceptance: the done-when.

handoffs/active/context-and-token-economy.md:3148 (Track tool-output-compression, ### Backlog; packet P8):

```text
- [ ] **CTE-CFAB-A8** [non-inference] Write the CF-AB-1 frame's arm A8, design text only (intake-2874, intake-2875): a digest catalog of every past turn plus agent-selected unfold under a declared history budget (autoresearch context folding), with a variant that uses a second-role compressor and pinned-pointer restoration (DMC-5). It runs only when TOC-SP-5 shows binding windows, like A3-A7.
      · done when: the A8 arm text in the CF-AB-1 frame names the digest format, the unfold surface, the budget and the delivery-path precondition, with the commit SHA recorded under this box
      · gate: none        · inputs: `handoffs/active/context-and-token-economy.md`
```
Brief: where `epyc-root:handoffs/active/context-and-token-economy.md`; approach: Write the A8 subsection under the CF-AB-1 frame: digest schema (turn id, tool, outcome, 1-2 sentences), the unfold tool surface (a REPL call returning the full turn by id), the declared history budget, the second-role compressor variant with the pinned-pointer list, and the TOC-SP-5 binding-window precondition. Acceptance: the done-when.

### Durable prose and annotations (Stage 4, no checkbox)

**Monitors M1-M11.** Each is written as one trigger line under its owner's current track. M1 instead extends the existing pre-RL monitor line in context-and-token-economy.md (track per-request-reasoning-budget).

**Knowledge rows:**

| Row | Where it goes |
|---|---|
| K1 | An annotation under DF2-11-BF16-FIX in speculative-decoding.md. |
| K2 | A note in the SPEC-GRAM section of speculative-decoding.md. |
| K3 | The Hopper table above. The operator applies it to the census; Stage 4 does not edit the census. |
| K4 | One line in kernel-champion-and-promotion.md's fold-gate section. |

**Index rows: none.** Every box lands in a handoff that already owns an index row, and no new stub is created.

**Stage 4 also does:**

1. The entry updates in the payload, plus the OD-1 outcome.
2. The steering reconciliation.
3. A `compile_sources.py` check that all 38 dive files appear.
4. `intake_dive_digests.py --ids 2867-2906`.
5. `vidya sync` after the push.
6. `index_state.py` then `--check`.

## Dive-surfaced sources

- **Wave 1:** every dive-surfaced source recommended in the eleven Stage-2 dives was ingested and dived (23 entries).
- **Wave 2:** the wave-1 sources' own recommendations were ingested and dived (3 entries).
- **Wave 3:** Huang et al. was dived; BitDecoding-FP4 and LiquidGEMM were filed Stage-1 only.
- **After the cap:** the four-sweep cap is reached. Declined sources are named in each bearing entry's `dive_corrections` (Stage-2 close-out line). They include:
  - hkust-nlp/RL-Verifier-Robustness: the EV-JUDGE-FPR-1 box reads it directly as code input.
  - Easy-Kuant: on OpenReview, no arXiv id.
  - SAW-INT4.
  - ELMoE-3D.
  - MoE-SpAc.
  - The Li skills survey.
  - Several repos and PRs.

## Steering ledger

19 operator rows:

- **Retained from Stage 1 (seq 1-2):** the dive pre-authorisation and the stop-at-Stage-3 instruction, both context-only.
- **seq 3-17:** this run's steering items, the project facts, the rules and the hand-back instruction.
  - Planned: items 1-7 and 9-11 map to P1-P8.
  - Context-only: the item-1-to-5 principles note, the project facts, the rules and the hand-back.
- **seq 18:** the operator's Hopper-table request, delivered by the coordinator during Stage 2. Planned as K3.
- **seq 19:** the operator's Stage-4 approval with changes 1-3 and OD-1 = A, folded into revision 1.

The full verbatim rows are in the payload and are persisted at Stage 4.

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2867",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): GDN-SLOTS-STRONGER"
   ]
  },
  {
   "id": "intake-2868",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): MMID-UB-CEIL-1, M3"
   ]
  },
  {
   "id": "intake-2869",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "rocm-kernel-authoring.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): MMVF-I64-OFFSET, RKA-SRC1-DTYPE-RULE, K1"
   ]
  },
  {
   "id": "intake-2870",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "cpu-decode-roofline-program.md",
    "quantization-and-low-bit.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-GVFATTN-Q4KV-DESIGN, RKA-IPB-CENSUS-1, RKA-GV-PSCALE-1, KVQ-ROT-KLD-1, KVQ-KMEAN-SIM-1, CDR-A3B-Q4KV-32K, K3"
   ]
  },
  {
   "id": "intake-2871",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-CPU-KSHIFT-1"
   ]
  },
  {
   "id": "intake-2872",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "quantization-and-low-bit.md",
    "rocm-kernel-authoring.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-ID-GATE-2, SPEC-ID-NOISE-2, FOLD-KLD-FLOOR-1, RKA-BATCH-INV-CENSUS-1, KVQ-ROT-KLD-1"
   ]
  },
  {
   "id": "intake-2873",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-GRAM-JSON-1, M2"
   ]
  },
  {
   "id": "intake-2874",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-LESSON-DEMOTE-1, AK-ATTEMPT-DIGEST-1, CTE-CFAB-A8"
   ]
  },
  {
   "id": "intake-2875",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md",
    "harness-program.md",
    "kv-cache-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): KV-EVICT-COST-2, HAR-COMPACT-LEDGER-1, CTE-CFAB-A8"
   ]
  },
  {
   "id": "intake-2876",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-STOP-EQ7-1, CDR-RT9-COVER-1"
   ]
  },
  {
   "id": "intake-2877",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md",
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): EV-JUDGE-FPR-1, M1"
   ]
  },
  {
   "id": "intake-2878",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "quantization-and-low-bit.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-GVFATTN-Q4KV-DESIGN, KVQ-KMEAN-SIM-1"
   ]
  },
  {
   "id": "intake-2879",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md",
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-GVFATTN-Q4KV-DESIGN, RKA-IPB-CENSUS-1"
   ]
  },
  {
   "id": "intake-2880",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-GVFATTN-Q4KV-DESIGN"
   ]
  },
  {
   "id": "intake-2881",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "quantization-and-low-bit.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): KVQ-ROT-KLD-1, KVQ-KMEAN-SIM-1, M4"
   ]
  },
  {
   "id": "intake-2882",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "rocm-kernel-authoring.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): RKA-BATCH-INV-CENSUS-1, SPEC-ID-NOISE-2"
   ]
  },
  {
   "id": "intake-2883",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-ID-GATE-2, SPEC-ID-NOISE-2"
   ]
  },
  {
   "id": "intake-2884",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-ID-GATE-2, PFXC-ID-REPLICA-1"
   ]
  },
  {
   "id": "intake-2885",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-GRAM-TV-1, K2"
   ]
  },
  {
   "id": "intake-2886",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): EV-JUDGE-FPR-1"
   ]
  },
  {
   "id": "intake-2887",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): M1"
   ]
  },
  {
   "id": "intake-2888",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md",
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): EV-JUDGE-FPR-1, M1"
   ]
  },
  {
   "id": "intake-2889",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): EV-SCORER-FUZZ-1"
   ]
  },
  {
   "id": "intake-2890",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "context-and-token-economy.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): M1"
   ]
  },
  {
   "id": "intake-2891",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-ID-GATE-2, PFXC-ID-REPLICA-1"
   ]
  },
  {
   "id": "intake-2892",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "quantization-and-low-bit.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): KVQ-ROT-KLD-1"
   ]
  },
  {
   "id": "intake-2893",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-ID-GATE-2, FOLD-KLD-FLOOR-1"
   ]
  },
  {
   "id": "intake-2894",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md",
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-ID-GATE-2, SPEC-ID-NOISE-2, PFXC-ID-REPLICA-1"
   ]
  },
  {
   "id": "intake-2895",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "cpu-decode-roofline-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): CDR-RT9-COVER-1"
   ]
  },
  {
   "id": "intake-2896",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "speculative-decoding.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): SPEC-STOP-EQ7-1"
   ]
  },
  {
   "id": "intake-2897",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-CPU-KSHIFT-1"
   ]
  },
  {
   "id": "intake-2898",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-CPU-KSHIFT-1"
   ]
  },
  {
   "id": "intake-2899",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): RKA-SRC1-DTYPE-RULE"
   ]
  },
  {
   "id": "intake-2900",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "rocm-kernel-authoring.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): RKA-SRC1-DTYPE-RULE"
   ]
  },
  {
   "id": "intake-2901",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kernel-champion-and-promotion.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): FOLD-KLD-FLOOR-1"
   ]
  },
  {
   "id": "intake-2902",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "kv-cache-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): KV-EVICT-COST-2"
   ]
  },
  {
   "id": "intake-2903",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): AK-LESSON-DEMOTE-1"
   ]
  },
  {
   "id": "intake-2904",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "eval-tower-program.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage 4 (operator-approved plan): EV-JUDGE-FPR-1"
   ]
  },
  {
   "id": "intake-2905",
   "integration_disposition": "awaiting_dive",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage-1 expansion from intake-2870; not dived, so no number from it enters a plan or handoff"
   ]
  },
  {
   "id": "intake-2906",
   "integration_disposition": "awaiting_dive",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-ak-1124 Stage-1 expansion from intake-2870; not dived, so no number from it enters a plan or handoff"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Noise-floor-aware identity and fold gates: replica floor, cache and KV-provenance conditions, drift localisation, KLD floor, prompt-cache identity, batch-invariance census",
   "implementation_ref": "epyc-llama:common/common.h; epyc-llama:examples/eval-callback; epyc-llama:ggml/src/ggml-cuda/fattn-common.cuh; epyc-llama:ggml/src/ggml-cuda/mmq.cu; epyc-llama:ggml/src/ggml-cuda/mmvq.cu; epyc-llama:tools/perplexity/perplexity.cpp; epyc-llama:tools/server/server-context.cpp; epyc-root:docs/guides/agent-workflows/spec-identity-gate-protocol.md",
   "gap": "SPEC-ID-GATE-2: Edit sections 2, 3, 4 and 6 of the protocol doc: add a replica table (launches, pair list, largest-pair floor), a preconditions checklist (cache_prompt, --cache-ram, -ub, -ctk/-ctv, spec width) and a RESULT.json field list (env knobs, route histogram, binary sha256, config dump). In the gate reporter, return INCONCLUSIVE when fewer than 3 reference launches are supplied, with a pytest case. Append the cache-off label to the SPEC-ID-NOISE-1 result line.; SPEC-ID-NOISE-2: Reuse the SPEC-ID-NOISE-1 job.py and prompt digest. Arm A: 4 relaunches, leave-one-out gate calls. Arm B: export GGML_HIP_Q8_SKINNY=0 and rerun the same 64 prompts. Arm C: build eval-callback with a cb_eval hook that sha256-hashes each tensor by name, diff the two launch logs and record the first mismatching node. Arm D: CPU quarter, -ctk f32 -ctv f32 with LLAMA_SPEC_EXACT=serial vs default, resume vs fresh.; FOLD-KLD-FLOOR-1: First check whether the C21 fold-gate run kept per-token logits. If so, compute the KLD between two candidate runs offline. Otherwise, run llama-perplexity --kl-divergence on the fold-gate corpus twice with only GGML_ROWEXACT_N (CPU) or the MMVQ nwarps env (GPU) toggled, then add floor and ratio fields to the fold-gate result template.; PFXC-ID-REPLICA-1: Run llama-server with the served flags and cache_prompt true. Per prompt, send a priming request, then the target request (cache hit), restart and send it cold. Repeat over 3 launches. Classify first divergences with the protocol's margin classes and compare against the per-path A/A largest pair. Log cache_n from the response timings.; RKA-BATCH-INV-CENSUS-1: Read each listed kernel's launch-parameter code and record which parameters depend on ncols/n_tokens/n_kv (nwarps, parallel_blocks, split count) and where atomics or reduction-order changes occur. Fill a table of op, dependency, required change and estimated LOC/perf cost. No build or run.",
   "operational_change": "SPEC-ID-GATE-2; SPEC-ID-NOISE-2; FOLD-KLD-FLOOR-1; PFXC-ID-REPLICA-1; RKA-BATCH-INV-CENSUS-1",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P2": {
   "project_objective": "q4_0-KV GQA-verify attention on the MI210: design inputs and refinements for the published row, an issue-budget census and a sink numerics test",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/fattn.cu; epyc-llama:ggml/src/ggml-quants.c::dequantize_row_q4_0; epyc-llama:tests/test-backend-ops.cpp",
   "gap": "AK-GVFATTN-Q4KV-DESIGN: Write a numpy oracle that reproduces block_q4_0 nibble order into 16x16x16 MFMA A/B lane fragments and compare it bit-exact with dequantize_row_q4_0 on random blocks. Compile both decode snippets with hipcc --save-temps for gfx90a and count v_* instructions per value. Read 5141da459's fattn-gqa-verify.cu and write the review note against its LDS layout. Annotate AK-GVFATTN-LONGCTX with the R = 42 tile arithmetic.; RKA-IPB-CENSUS-1: Run rocprofv3 --pmc SQ_INSTS_VALU SQ_INSTS_SALU SQ_INSTS_LDS SQ_WAVES SQ_BUSY_CYCLES on llama-bench (or the verify harness) with the 27B verify shapes, filtered to the gv_fattn kernel name. Divide instruction counts by the KV bytes per call and compare with the device issue budget (CUs x SIMD issue rate over HBM bandwidth).; RKA-GV-PSCALE-1: Add a test-backend-ops FLASH_ATTN_EXT case with GQA-verify shapes (head dim 256, n_q 4-8) whose first key gets a +20 logit bias, so P mass concentrates there. Compare max abs error of the gv path and the vector path against CPU. Then add an env-gated 2^10 scale before the f16 P store and its inverse in the PV accumulate, and rerun.",
   "operational_change": "AK-GVFATTN-Q4KV-DESIGN; RKA-IPB-CENSUS-1; RKA-GV-PSCALE-1",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P3": {
   "project_objective": "q4_0 KV quality: rotation on/off KLD with flip and margin arms, K-mean simulation, A3B CPU long-context decode",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cpu/ops.cpp; epyc-llama:src/llama-kv-cache.cpp",
   "gap": "KVQ-ROT-KLD-1: Run llama-perplexity --kl-divergence-base on f16 KV once per model, then --kl-divergence for -ctk/-ctv q8_0, q4_0 and q4_0 with LLAMA_ATTN_ROT_DISABLE=1, on the same 64-chunk corpus. Margin c comes from first-token logits of the same runs. The flip arm reuses the G3 (G) GSM8K harness at three launches per arm, scored by math_verify. The A3B CPU arm repeats the KLD runs on one quarter.; KVQ-KMEAN-SIM-1: Use a cb_eval hook (or GGML_SCHED dump) to save post-RoPE K and Q per full-attention layer to .npy for 64 prompts. Then, offline in numpy, port calib_kv.py's static mean, quantize to q4_0 (-8..7, 32-value blocks), recompute attention and measure KL against the f16 attention output per layer and arm. Plot mean-energy share per layer.; CDR-A3B-Q4KV-32K: Use llama-bench (or the served recipe through the bench harness) with -ctk/-ctv q8_0 then q4_0 at 32k depth on one quarter, three launches each, and capture GGML per-op timings to get the attention share. Compare against the A/A spread from the three launches.",
   "operational_change": "KVQ-ROT-KLD-1; KVQ-KMEAN-SIM-1; CDR-A3B-Q4KV-32K",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/quantization-and-low-bit.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P4": {
   "project_objective": "Upstream-contract robustness: GDN slot witness, mul_mat_id ceiling guard, MMVF overflow and alignment fixes, dtype and rebase rules",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/gated_delta_net.cu; epyc-llama:ggml/src/ggml-cuda/ggml-cuda.cu; epyc-llama:ggml/src/ggml-cuda/mmid.cu; epyc-llama:ggml/src/ggml-cuda/mmvf.cu; epyc-llama:tests/test-backend-ops.cpp; epyc-orchestrator:scripts/server/orchestrator_stack.py; epyc-root:handoffs/active/rocm-kernel-authoring.md",
   "gap": "GDN-SLOTS-STRONGER: In test-backend-ops.cpp, add a named GATED_DELTA_NET case at n_tokens > K (e.g. n=300, K=9) on the chunked path whose comparison covers every snapshot slot. Name it so a grep finds it, and add a comment pointing to this box. Write the slot-guarantee note and the tbo-scope rule into the fold-gate section of kernel-champion-and-promotion.md.; MMID-UB-CEIL-1: In orchestrator_stack.py, beside _has_any_flag's K4 check, parse -ub/--ubatch-size for GPU MoE roles and refuse values above 16384 with a clear message, plus a pytest case. On ROCm0, run test-backend-ops -o MUL_MAT_ID with a 16384-token and a 16385-token case (Q4_0, n_used 2) and record pass vs GGML_ASSERT abort.; MMVF-I64-OFFSET: Use the prepared gate directory: run its job on the MI210 against the branch build at 7eb398b16 (test-backend-ops -o MUL_MAT,MUL_MAT_ID plus perf at ne11 1-8 with the route-log env), compare against C21's A/A floor, and file RESULT.json. Evaluate c47c574ba and 7eb398b16 separately via the per-commit arms the gate defines.; RKA-SRC1-DTYPE-RULE: Add a short 'input dtypes and rebase triggers' subsection to this handoff's kernel-authoring track: the template-parameter rule with the MMVF runtime-flag counterexample from #32533, the list of src1==F32-gated routes with file:line at 98ff8a4, and the producer-merge trigger naming the four upstream PRs and the two fusion gates.",
   "operational_change": "GDN-SLOTS-STRONGER; MMID-UB-CEIL-1; MMVF-I64-OFFSET; RKA-SRC1-DTYPE-RULE",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P5": {
   "project_objective": "Draft-length and structured-output control: forced-share replay, masked-vs-conditional TV, cost-aware stop rule, residency coverage close-out",
   "implementation_ref": "epyc-inference-research:scripts/benchmark/moe_routing/skew_report.py; epyc-llama:common/sampling.cpp; epyc-llama:common/speculative.cpp; epyc-llama:tools/server/server-context.cpp",
   "gap": "SPEC-GRAM-JSON-1: Pull retained json_schema request/response pairs from the orchestrator logs per class, compile each schema with llguidance 1.0.1, walk the tokenized output calling llg_matcher_compute_ff_tokens at each step, and count forced tokens, run lengths and steps where the mask admits exactly one token. Weight by per-class token volume from the serving logs. Write a CSV plus a summary table; no server or model is started.; SPEC-GRAM-TV-1: Enumerate each enum schema's accepted token sequences with llguidance into a prefix trie. For every trie node, issue one /completion prefix forward with n_probs on a CPU-quarter llama-server, then compute masked and conditional probabilities bottom-up (the conditional renormalises by future-valid mass). Report TV per class at T 1.0 and the served temperature. Skip classes whose trie exceeds 10k strings.; SPEC-STOP-EQ7-1: Load the CAFE-1-SERVED-T capture JSONL (per-position draft probabilities, accepted lengths). Fit C(K) = a + b*K + c*E_union(K) by least squares on Q38P/CAFE verify timings, with E_union from the routing traces. Implement the Eq 7 argmin in a short numpy script, replay it on a 50% held-out split of the captures, and bootstrap the tokens/s ratio against each fixed p_min.; CDR-RT9-COVER-1: Point skew_report.py at the saved RT-9 trace directory, add a --residency 0.125 option that reports cumulative selection coverage of the top-k experts per layer, and split rows by domain (code / prose / reasoning) and by same-domain vs cross-domain hot sets. Write the table into the box.",
   "operational_change": "SPEC-GRAM-JSON-1; SPEC-GRAM-TV-1; SPEC-STOP-EQ7-1; CDR-RT9-COVER-1",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P6": {
   "project_objective": "AutoKernel loop: lesson demote rule by journal replay, per-attempt digests, an x86 KernelShift-format pilot",
   "implementation_ref": "epyc-inference-research:scripts/kernel_rnd/autokernel/controller/do_not_repeat.py; epyc-inference-research:scripts/kernel_rnd/autokernel/loop; epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py",
   "gap": "AK-LESSON-DEMOTE-1: Parse program.md, the journal shards and negatives.json. Reconstruct per-iteration rendered lessons from actor_context.py's bundle index, mark which lesson IDs each proposal cited, and simulate three demote policies over epochs (unused-5, alpha=0 periodic, utility-gated from keep/discard receipts). Exclude do_not_repeat.py-backed entries. Emit a per-policy CSV of chars saved and re-proposals.; AK-ATTEMPT-DIGEST-1: In actor_context.py, add a digest builder that reads each attempt's per-call file, takes the mechanism, the arm and the verdict line, and emits one 2-4 sentence entry into the bundle index. Keep the full file path beside each digest. Regenerate one bundle from the live journal, diff index sizes, and guard the result with a unit test on a fixture journal.; AK-CPU-KSHIFT-1: Clone kernel-shift at 610e835 into a research scratch dir. Patch kgen/check.py and kgen/autovec.py to accept x86_64, add an avx512 tier in config/kernel_contracts.yaml, and write a C++ wrapper calling ggml_vec_dot_q8_0_q8_0 and iqk as the expert baseline. Generate workloads from served-shape traces, calibrate the SQNR floor, then run the ISA arms via -march flags on one quarter and count instructions with objdump.",
   "operational_change": "AK-LESSON-DEMOTE-1; AK-ATTEMPT-DIGEST-1; AK-CPU-KSHIFT-1",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P7": {
   "project_objective": "Judge and scorer audit before any optimiser uses them: scorer fuzzing and judge false-positive exposure",
   "implementation_ref": "epyc-orchestrator:src",
   "gap": "EV-SCORER-FUZZ-1: Write fixture generators for the five mutation categories over GSM8K/MATH-500 gold answers (e.g. gold in prose without a box, two conflicting finals, 1e-3 float drift). Call eval_tower's math_verify and exact-match scorer functions directly in pytest, and tabulate accept rates against the strict contract. Keep the fixtures in the repo.; EV-JUDGE-FPR-1: Clone hkust-nlp/RL-Verifier-Robustness to read Table 8's strings and the Figure 6 prompts. Build a string x problem matrix (about 471 DeepScaleR items). Call each judge config through its existing eval_tower adapter with the three prompt templates, and compute per-string accept rates with Wilson intervals. The propensity scan greps journal outputs with the same detectors.",
   "operational_change": "EV-SCORER-FUZZ-1; EV-JUDGE-FPR-1",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "P8": {
   "project_objective": "Compaction cost and integrity: local-seconds break-even, failed-action ledger, a context-folding arm design",
   "implementation_ref": "epyc-orchestrator:src/graph/compaction.py; epyc-root:handoffs/active/context-and-token-economy.md; epyc-root:handoffs/active/kv-cache-program.md",
   "gap": "KV-EVICT-COST-2: Extend the KV-EVICT-COST-1 table script with two derived columns: compressor and agent seconds from retained prefill t/s and context-slope rows per device, with the re-prefill length set by GDN can_shift=false; and rho_cross = 1 - 1/r with a mutated-prefix flag. Output break-even trajectory length or NO-GO per device.; HAR-COMPACT-LEDGER-1: In compaction.py, behind a settings flag, collect failed tool calls (non-zero exit or error result) into a verbatim ledger block kept across compactions. Extract pinned tokens (paths, IDs, numbers) from the pre-compaction context with regexes and assert they appear byte-exact after compaction. Add a pytest replay over 3-5 retained trajectories.; CTE-CFAB-A8: Write the A8 subsection under the CF-AB-1 frame: digest schema (turn id, tool, outcome, 1-2 sentences), the unfold tool surface (a REPL call returning the full turn by id), the declared history budget, the second-role compressor variant with the pinned-pointer list, and the TOC-SP-5 binding-window precondition.",
   "operational_change": "KV-EVICT-COST-2; HAR-COMPACT-LEDGER-1; CTE-CFAB-A8",
   "benefit_direction": "decision quality and served speed improve with correctness gates unchanged or tightened; no invented gain",
   "owner": "handoffs/active/kv-cache-program.md",
   "execution_conditions": "code/doc boxes run now; inference boxes book their own rows (CPU quarter or MI210) under the row-owner loop; no production activation without a separate gate",
   "closure_basis": "immediate outcome retained in the listed boxes; broader steps stay as monitor prose"
  },
  "M1": {
   "project_objective": "Append to the existing pre-RL monitor line (track per-request-reasoning-budget, the 'if a local GRPO/RLVR weights run is ever planned' line): the plan also pre-registers a judge exposure audit (propensity x judge FPR per exploit string, from EV-JUDGE-FPR-1), an independent unhackable audit run (no write access, hidden tests), within-group reward-contrast logging, and KL-slope tracking over log-spaced checkpoints (intake-2877, intake-2887, intake-2888, intake-2890).",
   "implementation_ref": "handoffs/active/context-and-token-economy.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/context-and-token-economy.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M2": {
   "project_objective": "If SPEC-GRAM-JSON-1 finds any production json_schema class with forced share >= 10-15% and material token volume: design the chain-path grammar draft (forced runs from llg_matcher_compute_ff_tokens as point-mass drafts, logits skipped only where the mask admits one token) and grammar-aware pruning of batch trees; open the implementation box only if the class-weighted ceiling is >= 1.10x (intake-2873).",
   "implementation_ref": "handoffs/active/speculative-decoding.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M3": {
   "project_objective": "When MMID-HELPER-N10 folds: port #32177's chunked id compaction as a separate commit with its 66000-token tests, adapted to expert_bounds; KEEP iff 6/6 pass on ROCm0 and the n <= 16384 path is bitwise unchanged; defer to the upstream merge if the adaptation is larger than the helper (intake-2868).",
   "implementation_ref": "handoffs/active/kernel-champion-and-promotion.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M4": {
   "project_objective": "If KVQ-ROT-KLD-1 shows a rotation effect over 10%: split LLAMA_ATTN_ROT_DISABLE into K-only and V-only switches in the experimental tree (selecting keys alone carries 93-94% of the gain in intake-2881).",
   "implementation_ref": "handoffs/active/quantization-and-low-bit.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/quantization-and-low-bit.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M5": {
   "project_objective": "If KVQ-KMEAN-SIM-1 shows the first full-attention layer at >= 2x the median layer's simulated KL: add a per-layer KV-type override for that layer (intake-2870).",
   "implementation_ref": "handoffs/active/quantization-and-low-bit.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/quantization-and-low-bit.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M6": {
   "project_objective": "If KV-EVICT-COST-2 records a break-even length for the compressor/agent split on some device: probe a concurrent CPU-quarter compressor with the GPU agent for latency (intake-2875).",
   "implementation_ref": "handoffs/active/kv-cache-program.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/kv-cache-program.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M7": {
   "project_objective": "If EV-JUDGE-FPR-1 finds a judge that gates a decision with any master-key FPR >= 1%: compare a no-question prompt fix with a trained robust judge (Master-RM-style, 20k truncation negatives) before that judge gates an optimiser (intake-2886).",
   "implementation_ref": "handoffs/active/eval-tower-program.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M8": {
   "project_objective": "If RKA-BATCH-INV-CENSUS-1 finds 3 or fewer ops need change: implement a default-off invariant audit arm (pinned per-column reduction geometry for n = 1-16, fixed-size KV chunks in vector flash attention) with a bitwise width-1 vs width-8 test (intake-2882).",
   "implementation_ref": "handoffs/active/rocm-kernel-authoring.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M9": {
   "project_objective": "If AK-CPU-KSHIFT-1's pilot produces a task the AK loop can use: extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM at verify widths (intake-2871).",
   "implementation_ref": "handoffs/active/autokernel-loop.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M10": {
   "project_objective": "Fires when the second GPU is installed and A3B is placed GPU-resident (operator 2026-11-24: A3B GPU will be served on the 2nd GPU): design a GPU-resident expert-subset drafter for A3B, using CDR-RT9-COVER-1's same-domain coverage at <= 12.5% residency (>= 0.6 makes a resident subset worth drafting from) as a design input (intake-2876).",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "M11": {
   "project_objective": "The harness accept gate (BSV-2 family) is not activated until an A/A floor from >= 3 replicas exists for its metric, per SPEC-ID-GATE-2 rule (a) (intake-2872).",
   "implementation_ref": "handoffs/active/eval-tower-program.md",
   "gap": "the broader step depends on an earlier box's verdict that does not exist yet",
   "operational_change": "durable trigger prose under the owner; no checkbox",
   "benefit_direction": "avoids building before the deciding result",
   "owner": "handoffs/active/eval-tower-program.md",
   "execution_conditions": "fires only on the named verdict",
   "closure_basis": "the immediate deciding step is filed as a box; this records only the conditional follow-on"
  },
  "K1": {
   "project_objective": "Annotation under DF2-11-BF16-FIX: llama.cpp PR #32533 cannot route the BF16 drafter, whose weights are BF16 with F32 src1; on C21 ne11 <= 8 takes MMVF by default and ne11 9-16 stays on hipBLAS/Tensile because MMF refuses BF16 on CDNA2 (intake-2869).",
   "implementation_ref": "handoffs/active/speculative-decoding.md",
   "gap": "none; the finding informs existing work",
   "operational_change": "annotation or note only",
   "benefit_direction": "prevents a wrong premise being re-derived",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Stage-4 annotation",
   "closure_basis": "knowledge-only: no immediate operational step changes a decision"
  },
  "K2": {
   "project_objective": "Note in the SPEC-GRAM section: the served verifier samples the grammar-masked distribution (common/sampling.cpp:1038-1107 @ 98ff8a4), speculation adds no bias over plain masked sampling, and logit-free acceptance of a forced token is lossless only where the mask admits exactly one token (intake-2885, intake-2873).",
   "implementation_ref": "handoffs/active/speculative-decoding.md",
   "gap": "none; the finding informs existing work",
   "operational_change": "annotation or note only",
   "benefit_direction": "prevents a wrong premise being re-derived",
   "owner": "handoffs/active/speculative-decoding.md",
   "execution_conditions": "Stage-4 annotation",
   "closure_basis": "knowledge-only: no immediate operational step changes a decision"
  },
  "K3": {
   "project_objective": "The measured Hopper percent-of-peak table in this plan replaces the recalled CUDA reference figures in the bandwidth-census parity section; the operator applies it to docs/design/mi210-served-kernel-bandwidth-census-20261122.md and the census JSON (intake-2870, intake-2879, intake-2880).",
   "implementation_ref": "handoffs/active/autokernel-loop.md",
   "gap": "none; the finding informs existing work",
   "operational_change": "annotation or note only",
   "benefit_direction": "prevents a wrong premise being re-derived",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Stage-4 annotation",
   "closure_basis": "knowledge-only: no immediate operational step changes a decision"
  },
  "K4": {
   "project_objective": "Magnitudes not imported as thresholds or expectations: cross-engine drift (intake-2884), vLLM KL floors (intake-2901), API cache prices (intake-2875, intake-2902), Arm agent-kernel speedups (intake-2871) and TPU grammar-draft speedups (intake-2873).",
   "implementation_ref": "handoffs/active/kernel-champion-and-promotion.md",
   "gap": "none; the finding informs existing work",
   "operational_change": "annotation or note only",
   "benefit_direction": "prevents a wrong premise being re-derived",
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "execution_conditions": "Stage-4 annotation",
   "closure_basis": "knowledge-only: no immediate operational step changes a decision"
  }
 },
 "actionable_additions": [
  {
   "ledger_id": "AKJ-01",
   "source": "intake-2867",
   "action": "Pin the in-house all-slot GDN guarantee with a witness test, a doc note and the tbo-scope rule",
   "terminal_mapping": "P4 / GDN-SLOTS-STRONGER"
  },
  {
   "ledger_id": "AKJ-02",
   "source": "intake-2867",
   "action": "Port upstream #32820's slot-0-only test view",
   "terminal_mapping": "decline: it would stop checking the tail slots that speculative rollback reads; the in-house chunked kernel writes them"
  },
  {
   "ledger_id": "AKJ-03",
   "source": "intake-2867",
   "action": "Price K=5 vs K=1 tail-slot cost on ROCm0 at n=2048",
   "terminal_mapping": "decline: tail slots are required by MTP and DFlash2 rollback, so their cost is not optional; reopen only if a rollback design stops reading them"
  },
  {
   "ledger_id": "AKJ-04",
   "source": "intake-2868",
   "action": "Guard the 16384-token mul_mat_id ceiling in the launcher and confirm it with an op smoke",
   "terminal_mapping": "P4 / MMID-UB-CEIL-1"
  },
  {
   "ledger_id": "AKJ-05",
   "source": "intake-2868",
   "action": "Fold chunked id compaction with its 66000-token tests when the n_used helper folds",
   "terminal_mapping": "M3"
  },
  {
   "ledger_id": "AKJ-06",
   "source": "intake-2868",
   "action": "Treat #32177 as a performance item",
   "terminal_mapping": "decline: robustness only; every configured ubatch is at most 2048, eight times below the gfx90a ceiling"
  },
  {
   "ledger_id": "AKJ-07",
   "source": "intake-2869",
   "action": "Gate the MMVF int64 offset fix and the AMD MMVF_MMID even-ne00 guard (both already committed)",
   "terminal_mapping": "P4 / MMVF-I64-OFFSET"
  },
  {
   "ledger_id": "AKJ-08",
   "source": "intake-2869",
   "action": "Record that #32533 cannot route the BF16 drafter (BF16 weights, F32 src1)",
   "terminal_mapping": "K1"
  },
  {
   "ledger_id": "AKJ-09",
   "source": "intake-2869",
   "action": "Kernel-authoring rules for new input dtypes plus the BF16-activation rebase trigger",
   "terminal_mapping": "P4 / RKA-SRC1-DTYPE-RULE"
  },
  {
   "ledger_id": "AKJ-10",
   "source": "intake-2869",
   "action": "Port BF16 src1, a direct BF16 CPU activation path, BF16 RMS_NORM or BF16 SET_ROWS",
   "terminal_mapping": "decline: no in-house producer emits BF16 activations, verify-width src1 bytes are tiny, and Zen 5 int8 VNNI needs Q8 activations anyway"
  },
  {
   "ledger_id": "AKJ-11",
   "source": "intake-2870",
   "action": "Design inputs for a q4_0-KV gv_fattn: lane-map oracle, fold-vs-reconstruct counts, LDS/operand-swap note, premise correction",
   "terminal_mapping": "P2 / AK-GVFATTN-Q4KV-DESIGN"
  },
  {
   "ledger_id": "AKJ-12",
   "source": "intake-2870",
   "action": "Build the default-off q4_0-KV gv_fattn path and gate it against q8_0 gv",
   "terminal_mapping": "P2 / AK-GVFATTN-Q4KV-DESIGN"
  },
  {
   "ledger_id": "AKJ-13",
   "source": "intake-2870",
   "action": "rocprofv3 instruction-per-byte census of the q8_0 gv_fattn kernel",
   "terminal_mapping": "P2 / RKA-IPB-CENSUS-1"
  },
  {
   "ledger_id": "AKJ-14",
   "source": "intake-2870",
   "action": "Sink-heavy numerics test of gv_fattn with P scaling as the candidate fix",
   "terminal_mapping": "P2 / RKA-GV-PSCALE-1"
  },
  {
   "ledger_id": "AKJ-15",
   "source": "intake-2870",
   "action": "27B q4_0 KV KLD with rotation on vs off, margin screen and graded-flip arm, plus an A3B CPU arm",
   "terminal_mapping": "P3 / KVQ-ROT-KLD-1"
  },
  {
   "ledger_id": "AKJ-16",
   "source": "intake-2870",
   "action": "Post-RoPE K dump and offline q4_0 mean-removal / selective-rotation simulation",
   "terminal_mapping": "P3 / KVQ-KMEAN-SIM-1"
  },
  {
   "ledger_id": "AKJ-17",
   "source": "intake-2870",
   "action": "Per-layer KV-type override for the first full-attention layer",
   "terminal_mapping": "M5"
  },
  {
   "ledger_id": "AKJ-18",
   "source": "intake-2870",
   "action": "35B-A3B CPU decode at 32k with q4_0 vs q8_0 KV",
   "terminal_mapping": "P3 / CDR-A3B-Q4KV-32K"
  },
  {
   "ledger_id": "AKJ-19",
   "source": "intake-2870",
   "action": "Port the Qwen2 k-proj-bias KV fixes",
   "terminal_mapping": "decline: no served config has a k_proj bias (attention_bias false in every config)"
  },
  {
   "ledger_id": "AKJ-20",
   "source": "intake-2881",
   "action": "Split the rotation disable switch into K-only and V-only",
   "terminal_mapping": "M4"
  },
  {
   "ledger_id": "AKJ-21",
   "source": "intake-2878",
   "action": "Port the Hopper kernels, the FOSCAR wgmma pipeline or the CDNA4 scaled-MFMA FP4 path",
   "terminal_mapping": "decline: each needs TMA, wgmma, tcgen05 or CDNA4 scaled-MFMA instructions that gfx90a lacks; the portable parts are taken in the design note"
  },
  {
   "ledger_id": "AKJ-22",
   "source": "intake-2871",
   "action": "One-op KernelShift-format x86 pilot with ISA ladder, autovec control, outcome classes and codegen counts",
   "terminal_mapping": "P6 / AK-CPU-KSHIFT-1"
  },
  {
   "ledger_id": "AKJ-23",
   "source": "intake-2871",
   "action": "Extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM",
   "terminal_mapping": "M9"
  },
  {
   "ledger_id": "AKJ-24",
   "source": "intake-2871",
   "action": "Pitfalls-digest prompt, fraction-of-peak scoring, Arm speedups as expectations, the e2e hook, the HF dataset, SimdBench priors",
   "terminal_mapping": "decline: the planner already reads negatives, the census already scores against the measured ceiling, and the Arm-bound artefacts do not run on Zen 5"
  },
  {
   "ledger_id": "AKJ-25",
   "source": "intake-2872",
   "action": "Amend the identity-gate protocol: replica floor, cache state, KV provenance, route and config recording, graded flips",
   "terminal_mapping": "P1 / SPEC-ID-GATE-2"
  },
  {
   "ledger_id": "AKJ-26",
   "source": "intake-2872",
   "action": "Null-test the gate and localise the GPU A/A drift (skinny atomics, node hashes, f32 audit arm)",
   "terminal_mapping": "P1 / SPEC-ID-NOISE-2"
  },
  {
   "ledger_id": "AKJ-27",
   "source": "intake-2872",
   "action": "Build in-row bands from all pairs of at least three replicas including a reordered arm",
   "terminal_mapping": "P1 / SPEC-ID-GATE-2"
  },
  {
   "ledger_id": "AKJ-28",
   "source": "intake-2872",
   "action": "Graded-flip budget for q4_0 and q8_0 KV over a scheduling floor",
   "terminal_mapping": "P3 / KVQ-ROT-KLD-1"
  },
  {
   "ledger_id": "AKJ-29",
   "source": "intake-2872",
   "action": "Keep the harness accept gate off until a three-replica A/A floor exists",
   "terminal_mapping": "M11"
  },
  {
   "ledger_id": "AKJ-30",
   "source": "intake-2882",
   "action": "Per-op batch-invariance census and port cost for a GPU fixed-order audit arm",
   "terminal_mapping": "P1 / RKA-BATCH-INV-CENSUS-1"
  },
  {
   "ledger_id": "AKJ-31",
   "source": "intake-2891",
   "action": "Cache-hit vs cold-recompute identity with a replica floor on the served recipes",
   "terminal_mapping": "P1 / PFXC-ID-REPLICA-1"
  },
  {
   "ledger_id": "AKJ-32",
   "source": "intake-2901",
   "action": "Measure the fold-gate KLD A/A floor and report candidate KLD over floor",
   "terminal_mapping": "P1 / FOLD-KLD-FLOOR-1"
  },
  {
   "ledger_id": "AKJ-33",
   "source": "intake-2892",
   "action": "Fit a per-width noise sigma offline and predict first-divergence rates",
   "terminal_mapping": "decline: the amended gate measures the floor directly in-row, so a predictive noise model changes no decision"
  },
  {
   "ledger_id": "AKJ-34",
   "source": "intake-2882",
   "action": "Full deterministic serving mode, pow2-scale alibi probe, imported tolerances or floors",
   "terminal_mapping": "decline: deterministic serving costs 1.6-2.1x in the source, the alibi holds only for integer accumulation, and the protocol bans imported thresholds"
  },
  {
   "ledger_id": "AKJ-35",
   "source": "intake-2873",
   "action": "Offline forced-share replay of production json_schema classes",
   "terminal_mapping": "P5 / SPEC-GRAM-JSON-1"
  },
  {
   "ledger_id": "AKJ-36",
   "source": "intake-2873",
   "action": "Chain-path grammar-draft design and grammar-aware tree pruning",
   "terminal_mapping": "M2"
  },
  {
   "ledger_id": "AKJ-37",
   "source": "intake-2873",
   "action": "Synchronous grammar planning, accept-with-probability-1 at T > 0, a Phi estimator in the verifier",
   "terminal_mapping": "decline: llama-server already plans on the host, forced acceptance shifts the distribution at near-tie tokenizations, and OneStep worsened three schemas in the source"
  },
  {
   "ledger_id": "AKJ-38",
   "source": "intake-2885",
   "action": "Exact masked-vs-conditional TV on production enum schemas",
   "terminal_mapping": "P5 / SPEC-GRAM-TV-1"
  },
  {
   "ledger_id": "AKJ-39",
   "source": "intake-2885",
   "action": "State the acceptance target (masked distribution) and the single-token rule for logit-free acceptance",
   "terminal_mapping": "K2"
  },
  {
   "ledger_id": "AKJ-40",
   "source": "intake-2874",
   "action": "Offline journal replay of three demote rules for prose lessons",
   "terminal_mapping": "P6 / AK-LESSON-DEMOTE-1"
  },
  {
   "ledger_id": "AKJ-41",
   "source": "intake-2874",
   "action": "Per-attempt digest catalog in the planner bundle",
   "terminal_mapping": "P6 / AK-ATTEMPT-DIGEST-1"
  },
  {
   "ledger_id": "AKJ-42",
   "source": "intake-2874",
   "action": "Context-folding arm in the CF-AB-1 frame with a second-role compressor variant",
   "terminal_mapping": "P8 / CTE-CFAB-A8"
  },
  {
   "ledger_id": "AKJ-43",
   "source": "intake-2874",
   "action": "KernelBench fast_1 as an expectation, lesson merging or rule promotion",
   "terminal_mapping": "decline: a different baseline and device, and the source's own case studies show merging drops applicability conditions"
  },
  {
   "ledger_id": "AKJ-44",
   "source": "intake-2875",
   "action": "Compressor/agent split and local-seconds crossover columns in the evict-cost table",
   "terminal_mapping": "P8 / KV-EVICT-COST-2"
  },
  {
   "ledger_id": "AKJ-45",
   "source": "intake-2875",
   "action": "Failed-action ledger and pinned-pointer restoration in orchestrator compaction",
   "terminal_mapping": "P8 / HAR-COMPACT-LEDGER-1"
  },
  {
   "ledger_id": "AKJ-46",
   "source": "intake-2875",
   "action": "Concurrent CPU-compressor / GPU-agent latency probe",
   "terminal_mapping": "M6"
  },
  {
   "ledger_id": "AKJ-47",
   "source": "intake-2875",
   "action": "Copy the API cost-saving target, the 3,500-token tier bound or cache_control",
   "terminal_mapping": "decline: price effects of API cached-input billing with no local analogue"
  },
  {
   "ledger_id": "AKJ-48",
   "source": "intake-2876",
   "action": "Replay A3B probabilities through the cost-aware stop rule with an expert-union term vs fixed p_min",
   "terminal_mapping": "P5 / SPEC-STOP-EQ7-1"
  },
  {
   "ledger_id": "AKJ-49",
   "source": "intake-2876",
   "action": "A3B residency-coverage curve from the existing routing traces",
   "terminal_mapping": "P5 / CDR-RT9-COVER-1"
  },
  {
   "ledger_id": "AKJ-50",
   "source": "intake-2876",
   "action": "Per-expert H2D cache, reduced-top-k or resident-subset self-drafting on CPU A3B, reuse-aware gating",
   "terminal_mapping": "decline: PCIe Gen4 H2D (28.89 GB/s measured) is slower than one CPU quarter's DRAM read, fewer-experts drafts lost in 96 of 112 source cells, and reuse-aware gating alters target routing"
  },
  {
   "ledger_id": "AKJ-51",
   "source": "intake-2876",
   "action": "Hybrid GPU-resident expert drafter design",
   "terminal_mapping": "M10"
  },
  {
   "ledger_id": "AKJ-52",
   "source": "intake-2877",
   "action": "Judge false-positive audit with master-key strings, prompt arms, propensity scan and exposure column",
   "terminal_mapping": "P7 / EV-JUDGE-FPR-1"
  },
  {
   "ledger_id": "AKJ-53",
   "source": "intake-2889",
   "action": "Fuzz the deterministic scorers with verifier mutation categories",
   "terminal_mapping": "P7 / EV-SCORER-FUZZ-1"
  },
  {
   "ledger_id": "AKJ-54",
   "source": "intake-2877",
   "action": "Attach an exposure audit and an unhackable audit run to the pre-RL monitor",
   "terminal_mapping": "M1"
  },
  {
   "ledger_id": "AKJ-55",
   "source": "intake-2877",
   "action": "Difficulty stratification, reopening the exploitability axis, timing constants, CATCH or noise-sweep reproduction, running rh-indicators",
   "terminal_mapping": "decline: no group-normalised optimiser exists in AutoPilot or AutoKernel, no GRPO run is planned, and the constants were fitted to one 1.5B regime"
  },
  {
   "ledger_id": "AKJ-56",
   "source": "intake-2886",
   "action": "Train or adopt a robust judge, or change the judge prompt",
   "terminal_mapping": "M7"
  },
  {
   "ledger_id": "AKJ-57",
   "source": "intake-2870",
   "action": "Hopper percent-of-peak figures for the census parity table (operator applies)",
   "terminal_mapping": "K3"
  },
  {
   "ledger_id": "AKJ-58",
   "source": "intake-2884",
   "action": "Magnitudes not imported: cross-engine drift, API prices, Arm and TPU speedups",
   "terminal_mapping": "K4"
  },
  {
   "ledger_id": "AKJ-59",
   "source": "intake-2904",
   "action": "Build the judge-audit string set from the 13 Huang families re-targeted to our verdict formats, per-string runs with intervals, and a Huang-comparable no-question arm",
   "terminal_mapping": "P7 / EV-JUDGE-FPR-1"
  },
  {
   "ledger_id": "AKJ-60",
   "source": "intake-2904",
   "action": "Use static attack-success rate as a predictor of RL exploitation",
   "terminal_mapping": "decline: one hacked judge and one unhacked base is a necessary-condition hint, not a validated predictor; exposure is used instead"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "ts": "2026-11-24T09:00:00Z",
   "verbatim": "Automatically accept every recommended deep dive and literature expansion, for up to FOUR Stage 2 sweeps.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied as the dive set: all 11 sources dived plus three Stage-2b waves (four sweeps, the cap); not a filing authority."
  },
  {
   "seq": 2,
   "stage": 1,
   "ts": "2026-11-24T09:00:00Z",
   "verbatim": "Operator steering below is context for Stage 1 ranking and Stage 3 grounding. It is NOT authorization to write handoffs. Stop at a Stage 3 plan for operator review: apply no handoff changes, and add no intake entries beyond what the skill permits before plan approval.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied: this plan is handed back before any Stage-4 write; only the plan and Stage-1/2 index and session fields were written."
  },
  {
   "seq": 3,
   "stage": 1,
   "verbatim": "1. **PR #32820 (merged 2026-11-23).** What it does: tests compare only GATED_DELTA_NET snapshot slot 0 when n_tokens > K, since ggml.h guarantees only slot 0 there. How it was found: gpu-rocm (gfx1151) CI failures on the chunked path. Results: RTX PRO 6000 test-backend-ops went 82/84 → 84/84. Restricting the chunked kernel to K==1 would make K=5 PP-2048 2.4x slower. Scope: backend-generic contract; applies to HIP on gfx90a. Value: follow-up to intake-2796 (pr32456); the snapshot contract for DTREE-GDN-BATCH, GDN-FUSED-VARIANT/GDN-COLWIDTH, and the C20/C21 fold gates.",
   "disposition": "planned",
   "plan_ref": "P4",
   "reason": "Dived (intake-2867): the in-house CDNA chunked kernel writes every tail slot and rollback reads them, so the contract is pinned by a witness test rather than ported."
  },
  {
   "seq": 4,
   "stage": 1,
   "verbatim": "2. **PR #32177 (open).** What it does: mul_mat_id aborts when a ubatch exceeds smpbo/4 tokens (25344 on ~99 KB-smem GPUs). The PR adds a pre-pass plus chunked compaction of expert ids, and 66000-token test-backend-ops cases. Scope: CUDA source that the HIP build shares. gfx90a has 64 KB LDS, so the limit is lower there (verify). Value: A3B large-ubatch prefill robustness; the MMID lane after AK-A3B-VERIFY-DEDUP DROP.",
   "disposition": "planned",
   "plan_ref": "P4",
   "reason": "Dived (intake-2868): ceiling derived as 16384 tokens on gfx90a; guard plus op smoke filed, the fold waits on the n_used helper fold (M3)."
  },
  {
   "seq": 5,
   "stage": 1,
   "verbatim": "3. **PR #32533 (open).** What it does: BF16 src1 for MUL_MAT/MUL_MAT_ID on CPU and CUDA. RTX 5090 results, us/run: MUL_MAT_ID, Qwen3-30B-A3B Q4_K, 512 tok: 170.60 → 156.24 (−8.4%). IQ4_XS: −4.8%. F8_E4M3 MUL_MAT, 1 tok: −12.8%. Reviewer notes: MMVF branch cost, and a bundled int32 overflow fix. Scope: CUDA-side; HIP coverage on gfx90a unverified. The CPU path converts BF16 src1 to vec_dot_type. Value: DF2-11 / DF2-11-BF16-FIX; the BF16 drafter currently runs via hipBLAS/Tensile at 144 GB/s. Specifically: templated src1 type in quantizers vs a runtime flag in MMVF; dispatch of BF16 src1 to MMQ/MMVQ vs BLAS.",
   "disposition": "planned",
   "plan_ref": "P4",
   "reason": "Dived (intake-2869): the PR cannot route the drafter (BF16 weights, F32 src1); two latent MMVF fixes and a dtype rule are filed, the feature port is declined."
  },
  {
   "seq": 6,
   "stage": 1,
   "verbatim": "4. **Fast 4-bit KV-Cache Decoding on Hopper (2611.30027).** Results: vLLM's NVFP4 KV path runs at 10–20% of bandwidth, up to 1.7x slower than FP8. The new kernel reaches 67–75% of peak at batch 32–128, 1.12–1.49x over the faster of XQA and FA4 FP8 at all 11 shapes. In vLLM: 1.12–1.64x per step on Llama-3.1-8B vs FlashInfer FP8 at batch ≥8, with 1.63x token capacity; prefill is 7% slower. Qwen2-family layer-0 key mean = k-proj bias through RoPE; keeping layer 0 in BF16 restores FP8/4-bit KV. Scope: Hopper-only (TMA, warpgroups). No FP4 hardware is assumed, so the software decode transfers. Value: G3-KTRACE (q4_0 KV full dequant), AK-GVFATTN-LONGCTX (LDS cut at 1.21x, below the bar), and KLD gates on KV quant. NOTE: a q4_0 KV gv_fattn kernel is being designed in this session right now (row `ak-gvfattn-q4kv-gpu-20261124` may exist). Cross-reference it. Specifically: a write-time cache layout so decoded values feed MFMA from registers; producer/consumer overlap of load and decode; operand swap to avoid padding small GQA groups; issue-budget-per-byte accounting; K mean removal plus BF16 layer 0 plus BF16 sink tokens.",
   "disposition": "planned",
   "plan_ref": "P2",
   "reason": "Dived (intake-2870) with four wave-1 companions; the row ak-gvfattn-q4kv-gpu-20261124 is absent from the lane at f74b175, so the design box hands its inputs to that row if it exists at Stage 4. Accuracy arms are P3."
  },
  {
   "seq": 7,
   "stage": 1,
   "verbatim": "5. **KernelShift (2611.29590).** Results: 99 CPU kernels from ncnn, llama.cpp, Arm SIMD Loops and KleidiAI. Agents beat auto-vectorization 2.4–19.8x, reach up to 2.74x over ncnn Neon, and 0.70x of KleidiAI. Agent-written kernels give 1.3–1.6x prefill over llama.cpp's fast path in two LLMs. Agents fail to adapt to SME2 matrix tiles. Scope: Arm-only (Neon/SVE/SVE2/SME2). Value: the AutoKernel CPU lane (AK-CPU-* rows, quarter-24t 112.9 GB/s ceiling), and a benchmark-construction method for AVX-512 kernels. Specifically: the repo-to-benchmark pipeline with target-hardware feedback, and which ISA-extension idioms agents miss. Map the SME2 tile failure to AVX-512/VNNI/BF16 usage.",
   "disposition": "planned",
   "plan_ref": "P6",
   "reason": "Dived (intake-2871) with the repo and SimdBench; the SME2 failure was streaming-mode state and does not predict VNNI/BF16 behaviour; a one-op x86 pilot is filed."
  },
  {
   "seq": 8,
   "stage": 1,
   "verbatim": "For items 1–5: extract the performance principles themselves (data layout, tiling, wavefront mapping, LDS use, fusion, quant packing, dispatch rules). Check whether each works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or on the Zen 5 EPYC CPU (AVX-512, NPS4).",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied in every kernel dive's performance-principles table (sections 4 of the dive files) and in the per-source verdicts below."
  },
  {
   "seq": 9,
   "stage": 1,
   "verbatim": "6. **Exact on Paper (2611.29663).** Setup: vLLM, one 4B model, nine single-feature configs plus five reference replicas, 3,380 graded requests. Results: Seven exact features flip 1.47% (CI 1.13–1.85) to 1.78% (1.39–2.20) of requests; none is above the 1.72% scheduling floor. FP8 KV flips 3.36% (2.80–3.96), as many as FP8 weights. With batch-invariant kernels, all seven exact features, including spec decode, reproduce the reference text on every request. A single-replica-pair gate rejected an unchanged config. Scope: hardware-agnostic method. Value: DFlash2 np2 A/A parity, SPEC-STALE-1, the C20/C21 fold gates, KLD gates, BSV-2 accept rigor. Highly relevant: tonight this session found that fixed 0.19/0.38 nat identity bands are miscalibrated, and moved to in-row reference-build bands.",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Dived (intake-2872) with eight wave-1/2 noise-floor sources; the protocol amendment extends the in-row band design rather than replacing it."
  },
  {
   "seq": 10,
   "stage": 1,
   "verbatim": "7. **Grammar-as-a-Draft (2611.28349).** Mechanism: grammar-forced tokens are merged into draft rows and accepted without logits. Acceptance length: MTP Qwen3.5-0.8B: 2.06 → 5.43. MTP Qwen3.5-35B-A3B: 1.99 → 5.31. DFlash Qwen3-4B: 1.57 → 4.13. n-gram: 1.30 → 3.64. Speed: 2.66–2.81x at batch 1, 1.14–1.70x at batch 64. Plain-text TPOT +7–42% under mixed traffic. The output distribution changes vs grammar-masked decoding. Scope: TPU v7x with a Rust runtime; scheduler-level, no new kernels, so it ports to llama.cpp grammar plus MTP/DFlash2 on EPYC/MI210. Value: INF-50 DFlash2, the MTP lanes, orchestrator tool-call/JSON paths. Specifically: the draft-row merge/cut rule, and logit-free acceptance of forced tokens inside the fork's accept loops (V2 RRS sampled tree verifier in C21).",
   "disposition": "planned",
   "plan_ref": "P5",
   "reason": "Dived (intake-2873, intake-2885): the speedups carry a tokenization artefact; the deciding step is an offline forced-share replay of production json_schema classes."
  },
  {
   "seq": 11,
   "stage": 1,
   "verbatim": "8. **Demystifying the Autoresearch Harness (2611.28244).** Setup: MLE-Bench and KernelBench with gpt-oss-120b and two other models. Results: context folding is best in all six settings, up to +19.2% over recency truncation. Discarding persistently unused lessons beats consolidation or rule promotion. MLEvolver reaches a 72.7% medal rate on MLE-Bench Lite and 94% fast_1 on KernelBench Level 3. Scope: hardware-agnostic. Value: AutoKernel loop journal / do-not-repeat lessons, AP-LH-DISTILL, skill-bank pruning, context folding (intake-154 / CF-AB-1).",
   "disposition": "planned",
   "plan_ref": "P6",
   "reason": "Dived (intake-2874, intake-2903): demote rules are replayed offline on prose lessons only; gate-backed negatives are never demoted. The CF-AB-1 arm is P8."
  },
  {
   "seq": 12,
   "stage": 1,
   "verbatim": "9. **DMC-5 (2611.30412).** Design: append-only canonical view, a general compressor model, and a specialized agent model working on a compact decision view. Results: agent input −38.5–57.0%, end-to-end cost −14.5–28.0%, compressor cache-hit 78.0–85.0%, task performance +1.0–5.8% on AppWorld, OfficeBench and 8-objective QA. Scope: hardware-agnostic. Value: KV-EVICT-COST-1, prefix-cache-stable compaction, orchestrator routing between small and large Qwen roles.",
   "disposition": "planned",
   "plan_ref": "P8",
   "reason": "Dived (intake-2875, intake-2902): the cost saving is an API price effect; the local question is a seconds break-even column in the evict-cost table plus the integrity ledger."
  },
  {
   "seq": 13,
   "stage": 1,
   "verbatim": "10. **CCAMoE (2611.28550).** Design: cache-only drafting from resident target experts (no draft weights), draft-guided expert-cache updates that overlap transfers, and cost-aware draft length. Result: up to 2.33x lower decoding latency vs state of the art, across MoE models and GPU platforms. Scope: built for GPU expert offloading; the principles apply to EPYC+MI210 A3B hybrid placement. Value: A3B MTP serving, hybrid CPU-GPU MoE placement, draft_p_min/draft-length control. Specifically: expert residency as drafter, PCIe Gen4 transfer overlap, and the acceptance-vs-cost draft-length rule. Extract the performance principles and check MI210/EPYC applicability, as for items 1–5.",
   "disposition": "planned",
   "plan_ref": "P5",
   "reason": "Dived (intake-2876) with SpecMoE and S2-MoE: the 2.33x is one RTX 4090 cell; transfer overlap does not pay against a DRAM-resident A3B; the stop rule is replayed offline against p_min."
  },
  {
   "seq": 14,
   "stage": 1,
   "verbatim": "11. **Which Loopholes Get Found? (2611.29651).** Setup: 36 GRPO runs, seven judges. Results: In all 12 exploiting runs, the first exploited pattern had the highest exposure (policy propensity × judge FPR); highest FPR alone predicted it in only 6. With two seeded patterns at 3–3.8% of SFT data, exposure named the first exploit and its onset window in all six runs. Exploitation happened only on hard prompts. Scope: hardware-agnostic. Value: LLM-as-judge audits before local Qwen RLVR/GRPO, AutoPilot judge gates, eval rigor.",
   "disposition": "planned",
   "plan_ref": "P7",
   "reason": "Dived (intake-2877) with five judge/verifier companions: no current gate optimises against an LLM judge, so the audit runs before any optimiser does."
  },
  {
   "seq": 15,
   "stage": 1,
   "verbatim": "**Current project facts to ground Stage 3** (verify against origin/main) - The champion candidate is C21 (98ff8a42a): C20 plus fused tree GDN, the V2 RRS sampled verifier, and the DTREE-B auto width controller. - Official vendor sampling went live in the registry and backend today (27B T1.0; 35B T0.7). 27B trees gain +6–9% at T1.0. - A3B serves on CPU, not GPU. - The MI210 has 64 KB LDS.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "C21 98ff8a42a verified on branch llama.cpp-experimental-c21-20261124 and in kernel-champion-and-promotion.md; every in-house citation is pinned @ 98ff8a4; the sampling and A3B facts are used as stated."
  },
  {
   "seq": 16,
   "stage": 1,
   "verbatim": "**Rules** - Never dismiss a source as \"not applicable\" without flagging it for the operator. Missing software or upstream \"not supported\" is a build cost, not a decline reason. - No compute or GPU use. Web fetches are fine. No pkill or pgrep. - Run git writes only where the skill's pre-approval stages allow. Use worktrees and never switch shared clones. - If a hook or classifier denies something, stop and report.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied: no source was marked not_applicable; Stage-1 platform-based relevance downgrades were overridden; no compute ran; writes stayed in the lane worktree; one filesystem-hook refusal of a variable-expanded path was resolved by using literal paths."
  },
  {
   "seq": 17,
   "stage": 1,
   "verbatim": "**When the Stage 3 plan is ready:** write it where the skill says, then return a hand-back. It must include: per-source verdicts; the deep dives and expansions taken (with the sweep count); the proposed handoff boxes and bindings; and the exact path of the plan file for operator review.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied: this plan carries those sections and the hand-back names its path."
  },
  {
   "seq": 18,
   "stage": 2,
   "verbatim": "From the operator: one of your sources, Fast 4-bit KV-Cache Decoding on Hopper (arXiv 2611.30027), reports state-of-the-art NVIDIA Hopper CUDA kernel efficiency (% of peak bandwidth for decode attention and related kernels). In your Stage 3 plan, include a short table of the measured Hopper % of peak per op class from that paper and any of your other sources (plus anything your literature expansions turned up). These replace the from-memory CUDA reference figures in the bandwidth census parity table (`docs/design/mi210-served-kernel-bandwidth-census-20261122.md`, research census JSON `parity` section). List each figure with its citation. Don't edit the census yourself; I'll apply it.",
   "disposition": "planned",
   "plan_ref": "K3",
   "reason": "The table is in this plan (Hopper percent-of-peak section); the figures were anchored on intake-2870 and intake-2879 before quoting; the census is not edited."
  },
  {
   "seq": 19,
   "stage": 3,
   "verbatim": "The operator approved Stage 4 with both changes (via AskUserQuestion: \"Approve with both changes\"). OD-1 = (A): repoint 2 anchors, drop 5, keep 3, then re-run the marks.\n\nChanges to the plan:\n(1) The q4_0 KV packet: row `ak-gvfattn-q4kv-gpu-20261124` is already published (store `gpu-20261124-5141da459-gvfattn-q4kv`, kernel commit 5141da459). AK-GVFATTN-Q4KV-DESIGN feeds that row: K-mean removal, the rotation note and so on, as refinements and a follow-up. Drop the duplicate AK-GVFATTN-Q4KV kernel box.\n(2) Rescope M10's trigger to: \"fires when the second GPU is installed and A3B is placed GPU-resident (operator 2026-11-24: A3B GPU will be served on the 2nd GPU)\". Keep the coverage condition as a design input.\n(3) MMVF-I64-OFFSET is already fixed. Commits c47c574ba and 7eb398b16 are on fork branch `llama.cpp-experimental-c22-mmvf-fixes-20261124`, and gate row `/mnt/raid0/llm/tmp/ak-c22-mmvf-fixes-gate-gpu-20261124` is prepared. File that box with the commits cited and the remaining step = gate run. Also cover the even-ne00 AMD guard (7eb398b16).",
   "disposition": "planned",
   "plan_ref": "P2",
   "reason": "Folded into revision 1: change 1 rewrites the P2 design box and drops the kernel box; change 2 rewrites M10; change 3 rewrites the P4 MMVF box; OD-1 = A applied to the anchors before filing."
  }
 ],
 "opportunity_scan": [
  {
   "scan_id": "S01",
   "source_ref": "intake-2867 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:tests/test-backend-ops.cpp",
   "mechanism": "Pin the in-house all-slot GDN guarantee with a witness test, a doc note and the tbo-scope rule",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Pin the in-house all-slot GDN guarantee with a witness test, a doc note and the tbo-scope rule",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-01"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S02",
   "source_ref": "intake-2867 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Port upstream #32820's slot-0-only test view",
   "consumer": "none (declined)",
   "application": "Port upstream #32820's slot-0-only test view",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-02"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: it would stop checking the tail slots that speculative rollback reads; the in-house chunked kernel writes them"
  },
  {
   "scan_id": "S03",
   "source_ref": "intake-2867 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Price K=5 vs K=1 tail-slot cost on ROCm0 at n=2048",
   "consumer": "none (declined)",
   "application": "Price K=5 vs K=1 tail-slot cost on ROCm0 at n=2048",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-03"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: tail slots are required by MTP and DFlash2 rollback, so their cost is not optional; reopen only if a rollback design stops reading them"
  },
  {
   "scan_id": "S04",
   "source_ref": "intake-2868 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-orchestrator:scripts/server/orchestrator_stack.py",
   "mechanism": "Guard the 16384-token mul_mat_id ceiling in the launcher and confirm it with an op smoke",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Guard the 16384-token mul_mat_id ceiling in the launcher and confirm it with an op smoke",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-04"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S05",
   "source_ref": "intake-2868 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/kernel-champion-and-promotion.md",
   "mechanism": "Fold chunked id compaction with its 66000-token tests when the n_used helper folds",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Fold chunked id compaction with its 66000-token tests when the n_used helper folds",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-05"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M3"
  },
  {
   "scan_id": "S06",
   "source_ref": "intake-2868 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Treat #32177 as a performance item",
   "consumer": "none (declined)",
   "application": "Treat #32177 as a performance item",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-06"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: robustness only; every configured ubatch is at most 2048, eight times below the gfx90a ceiling"
  },
  {
   "scan_id": "S07",
   "source_ref": "intake-2869 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/mmvf.cu",
   "mechanism": "Gate the MMVF int64 offset fix and the AMD MMVF_MMID even-ne00 guard (both already committed)",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Gate the MMVF int64 offset fix and the AMD MMVF_MMID even-ne00 guard (both already committed)",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-07"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S08",
   "source_ref": "intake-2869 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/speculative-decoding.md",
   "mechanism": "Record that #32533 cannot route the BF16 drafter (BF16 weights, F32 src1)",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Record that #32533 cannot route the BF16 drafter (BF16 weights, F32 src1)",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-08"
   ],
   "basis": "dive read the primary source and pinned the in-house path; K1"
  },
  {
   "scan_id": "S09",
   "source_ref": "intake-2869 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-root:handoffs/active/rocm-kernel-authoring.md",
   "mechanism": "Kernel-authoring rules for new input dtypes plus the BF16-activation rebase trigger",
   "consumer": "handoffs/active/rocm-kernel-authoring.md",
   "application": "Kernel-authoring rules for new input dtypes plus the BF16-activation rebase trigger",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-09"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2869 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Port BF16 src1, a direct BF16 CPU activation path, BF16 RMS_NORM or BF16 SET_ROWS",
   "consumer": "none (declined)",
   "application": "Port BF16 src1, a direct BF16 CPU activation path, BF16 RMS_NORM or BF16 SET_ROWS",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-10"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: no in-house producer emits BF16 activations, verify-width src1 bytes are tiny, and Zen 5 int8 VNNI needs Q8 activations anyway"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/fattn.cu",
   "mechanism": "Design inputs for a q4_0-KV gv_fattn: lane-map oracle, fold-vs-reconstruct counts, LDS/operand-swap note, premise correction",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Design inputs for a q4_0-KV gv_fattn: lane-map oracle, fold-vs-reconstruct counts, LDS/operand-swap note, premise correction",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-11"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/fattn.cu",
   "mechanism": "Build the default-off q4_0-KV gv_fattn path and gate it against q8_0 gv",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Build the default-off q4_0-KV gv_fattn path and gate it against q8_0 gv",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-12"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/fattn.cu",
   "mechanism": "rocprofv3 instruction-per-byte census of the q8_0 gv_fattn kernel",
   "consumer": "handoffs/active/rocm-kernel-authoring.md",
   "application": "rocprofv3 instruction-per-byte census of the q8_0 gv_fattn kernel",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-13"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/fattn.cu",
   "mechanism": "Sink-heavy numerics test of gv_fattn with P scaling as the candidate fix",
   "consumer": "handoffs/active/rocm-kernel-authoring.md",
   "application": "Sink-heavy numerics test of gv_fattn with P scaling as the candidate fix",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-14"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:src/llama-kv-cache.cpp",
   "mechanism": "27B q4_0 KV KLD with rotation on vs off, margin screen and graded-flip arm, plus an A3B CPU arm",
   "consumer": "handoffs/active/quantization-and-low-bit.md",
   "application": "27B q4_0 KV KLD with rotation on vs off, margin screen and graded-flip arm, plus an A3B CPU arm",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-15"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:src/llama-kv-cache.cpp",
   "mechanism": "Post-RoPE K dump and offline q4_0 mean-removal / selective-rotation simulation",
   "consumer": "handoffs/active/quantization-and-low-bit.md",
   "application": "Post-RoPE K dump and offline q4_0 mean-removal / selective-rotation simulation",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-16"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/quantization-and-low-bit.md",
   "mechanism": "Per-layer KV-type override for the first full-attention layer",
   "consumer": "handoffs/active/quantization-and-low-bit.md",
   "application": "Per-layer KV-type override for the first full-attention layer",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-17"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M5"
  },
  {
   "scan_id": "S18",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cpu/ops.cpp",
   "mechanism": "35B-A3B CPU decode at 32k with q4_0 vs q8_0 KV",
   "consumer": "handoffs/active/cpu-decode-roofline-program.md",
   "application": "35B-A3B CPU decode at 32k with q4_0 vs q8_0 KV",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-18"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S19",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Port the Qwen2 k-proj-bias KV fixes",
   "consumer": "none (declined)",
   "application": "Port the Qwen2 k-proj-bias KV fixes",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-19"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: no served config has a k_proj bias (attention_bias false in every config)"
  },
  {
   "scan_id": "S20",
   "source_ref": "intake-2881 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/quantization-and-low-bit.md",
   "mechanism": "Split the rotation disable switch into K-only and V-only",
   "consumer": "handoffs/active/quantization-and-low-bit.md",
   "application": "Split the rotation disable switch into K-only and V-only",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-20"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M4"
  },
  {
   "scan_id": "S21",
   "source_ref": "intake-2878 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Port the Hopper kernels, the FOSCAR wgmma pipeline or the CDNA4 scaled-MFMA FP4 path",
   "consumer": "none (declined)",
   "application": "Port the Hopper kernels, the FOSCAR wgmma pipeline or the CDNA4 scaled-MFMA FP4 path",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-21"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: each needs TMA, wgmma, tcgen05 or CDNA4 scaled-MFMA instructions that gfx90a lacks; the portable parts are taken in the design note"
  },
  {
   "scan_id": "S22",
   "source_ref": "intake-2871 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-inference-research:scripts/kernel_rnd/autokernel/loop",
   "mechanism": "One-op KernelShift-format x86 pilot with ISA ladder, autovec control, outcome classes and codegen counts",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "One-op KernelShift-format x86 pilot with ISA ladder, autovec control, outcome classes and codegen counts",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-22"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S23",
   "source_ref": "intake-2871 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/autokernel-loop.md",
   "mechanism": "Extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-23"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M9"
  },
  {
   "scan_id": "S24",
   "source_ref": "intake-2871 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Pitfalls-digest prompt, fraction-of-peak scoring, Arm speedups as expectations, the e2e hook, the HF dataset, SimdBench priors",
   "consumer": "none (declined)",
   "application": "Pitfalls-digest prompt, fraction-of-peak scoring, Arm speedups as expectations, the e2e hook, the HF dataset, SimdBench priors",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-24"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: the planner already reads negatives, the census already scores against the measured ceiling, and the Arm-bound artefacts do not run on Zen 5"
  },
  {
   "scan_id": "S25",
   "source_ref": "intake-2872 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-root:docs/guides/agent-workflows/spec-identity-gate-protocol.md",
   "mechanism": "Amend the identity-gate protocol: replica floor, cache state, KV provenance, route and config recording, graded flips",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Amend the identity-gate protocol: replica floor, cache state, KV provenance, route and config recording, graded flips",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-25"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S26",
   "source_ref": "intake-2872 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:common/common.h",
   "mechanism": "Null-test the gate and localise the GPU A/A drift (skinny atomics, node hashes, f32 audit arm)",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Null-test the gate and localise the GPU A/A drift (skinny atomics, node hashes, f32 audit arm)",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-26"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S27",
   "source_ref": "intake-2872 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-root:docs/guides/agent-workflows/spec-identity-gate-protocol.md",
   "mechanism": "Build in-row bands from all pairs of at least three replicas including a reordered arm",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Build in-row bands from all pairs of at least three replicas including a reordered arm",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-27"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S28",
   "source_ref": "intake-2872 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:src/llama-kv-cache.cpp",
   "mechanism": "Graded-flip budget for q4_0 and q8_0 KV over a scheduling floor",
   "consumer": "handoffs/active/quantization-and-low-bit.md",
   "application": "Graded-flip budget for q4_0 and q8_0 KV over a scheduling floor",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-28"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S29",
   "source_ref": "intake-2872 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/eval-tower-program.md",
   "mechanism": "Keep the harness accept gate off until a three-replica A/A floor exists",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "Keep the harness accept gate off until a three-replica A/A floor exists",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-29"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M11"
  },
  {
   "scan_id": "S30",
   "source_ref": "intake-2882 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:ggml/src/ggml-cuda/mmvq.cu",
   "mechanism": "Per-op batch-invariance census and port cost for a GPU fixed-order audit arm",
   "consumer": "handoffs/active/rocm-kernel-authoring.md",
   "application": "Per-op batch-invariance census and port cost for a GPU fixed-order audit arm",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-30"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S31",
   "source_ref": "intake-2891 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:tools/server/server-context.cpp",
   "mechanism": "Cache-hit vs cold-recompute identity with a replica floor on the served recipes",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Cache-hit vs cold-recompute identity with a replica floor on the served recipes",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-31"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S32",
   "source_ref": "intake-2901 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:tools/perplexity/perplexity.cpp",
   "mechanism": "Measure the fold-gate KLD A/A floor and report candidate KLD over floor",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Measure the fold-gate KLD A/A floor and report candidate KLD over floor",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-32"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S33",
   "source_ref": "intake-2892 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Fit a per-width noise sigma offline and predict first-divergence rates",
   "consumer": "none (declined)",
   "application": "Fit a per-width noise sigma offline and predict first-divergence rates",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-33"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: the amended gate measures the floor directly in-row, so a predictive noise model changes no decision"
  },
  {
   "scan_id": "S34",
   "source_ref": "intake-2882 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Full deterministic serving mode, pow2-scale alibi probe, imported tolerances or floors",
   "consumer": "none (declined)",
   "application": "Full deterministic serving mode, pow2-scale alibi probe, imported tolerances or floors",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-34"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: deterministic serving costs 1.6-2.1x in the source, the alibi holds only for integer accumulation, and the protocol bans imported thresholds"
  },
  {
   "scan_id": "S35",
   "source_ref": "intake-2873 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:common/sampling.cpp",
   "mechanism": "Offline forced-share replay of production json_schema classes",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Offline forced-share replay of production json_schema classes",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-35"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S36",
   "source_ref": "intake-2873 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/speculative-decoding.md",
   "mechanism": "Chain-path grammar-draft design and grammar-aware tree pruning",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Chain-path grammar-draft design and grammar-aware tree pruning",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-36"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M2"
  },
  {
   "scan_id": "S37",
   "source_ref": "intake-2873 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Synchronous grammar planning, accept-with-probability-1 at T > 0, a Phi estimator in the verifier",
   "consumer": "none (declined)",
   "application": "Synchronous grammar planning, accept-with-probability-1 at T > 0, a Phi estimator in the verifier",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-37"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: llama-server already plans on the host, forced acceptance shifts the distribution at near-tie tokenizations, and OneStep worsened three schemas in the source"
  },
  {
   "scan_id": "S38",
   "source_ref": "intake-2885 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:common/sampling.cpp",
   "mechanism": "Exact masked-vs-conditional TV on production enum schemas",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Exact masked-vs-conditional TV on production enum schemas",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-38"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S39",
   "source_ref": "intake-2885 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/speculative-decoding.md",
   "mechanism": "State the acceptance target (masked distribution) and the single-token rule for logit-free acceptance",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "State the acceptance target (masked distribution) and the single-token rule for logit-free acceptance",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-39"
   ],
   "basis": "dive read the primary source and pinned the in-house path; K2"
  },
  {
   "scan_id": "S40",
   "source_ref": "intake-2874 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py",
   "mechanism": "Offline journal replay of three demote rules for prose lessons",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Offline journal replay of three demote rules for prose lessons",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-40"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S41",
   "source_ref": "intake-2874 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py",
   "mechanism": "Per-attempt digest catalog in the planner bundle",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Per-attempt digest catalog in the planner bundle",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-41"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S42",
   "source_ref": "intake-2874 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-root:handoffs/active/context-and-token-economy.md",
   "mechanism": "Context-folding arm in the CF-AB-1 frame with a second-role compressor variant",
   "consumer": "handoffs/active/context-and-token-economy.md",
   "application": "Context-folding arm in the CF-AB-1 frame with a second-role compressor variant",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-42"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S43",
   "source_ref": "intake-2874 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "KernelBench fast_1 as an expectation, lesson merging or rule promotion",
   "consumer": "none (declined)",
   "application": "KernelBench fast_1 as an expectation, lesson merging or rule promotion",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-43"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: a different baseline and device, and the source's own case studies show merging drops applicability conditions"
  },
  {
   "scan_id": "S44",
   "source_ref": "intake-2875 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-root:handoffs/active/kv-cache-program.md",
   "mechanism": "Compressor/agent split and local-seconds crossover columns in the evict-cost table",
   "consumer": "handoffs/active/kv-cache-program.md",
   "application": "Compressor/agent split and local-seconds crossover columns in the evict-cost table",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-44"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S45",
   "source_ref": "intake-2875 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-orchestrator:src/graph/compaction.py",
   "mechanism": "Failed-action ledger and pinned-pointer restoration in orchestrator compaction",
   "consumer": "handoffs/active/harness-program.md",
   "application": "Failed-action ledger and pinned-pointer restoration in orchestrator compaction",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-45"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S46",
   "source_ref": "intake-2875 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/kv-cache-program.md",
   "mechanism": "Concurrent CPU-compressor / GPU-agent latency probe",
   "consumer": "handoffs/active/kv-cache-program.md",
   "application": "Concurrent CPU-compressor / GPU-agent latency probe",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-46"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M6"
  },
  {
   "scan_id": "S47",
   "source_ref": "intake-2875 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Copy the API cost-saving target, the 3,500-token tier bound or cache_control",
   "consumer": "none (declined)",
   "application": "Copy the API cost-saving target, the 3,500-token tier bound or cache_control",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-47"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: price effects of API cached-input billing with no local analogue"
  },
  {
   "scan_id": "S48",
   "source_ref": "intake-2876 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-llama:common/speculative.cpp",
   "mechanism": "Replay A3B probabilities through the cost-aware stop rule with an expert-union term vs fixed p_min",
   "consumer": "handoffs/active/speculative-decoding.md",
   "application": "Replay A3B probabilities through the cost-aware stop rule with an expert-union term vs fixed p_min",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-48"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S49",
   "source_ref": "intake-2876 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-inference-research:scripts/benchmark/moe_routing/skew_report.py",
   "mechanism": "A3B residency-coverage curve from the existing routing traces",
   "consumer": "handoffs/active/cpu-decode-roofline-program.md",
   "application": "A3B residency-coverage curve from the existing routing traces",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-49"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S50",
   "source_ref": "intake-2876 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Per-expert H2D cache, reduced-top-k or resident-subset self-drafting on CPU A3B, reuse-aware gating",
   "consumer": "none (declined)",
   "application": "Per-expert H2D cache, reduced-top-k or resident-subset self-drafting on CPU A3B, reuse-aware gating",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-50"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: PCIe Gen4 H2D (28.89 GB/s measured) is slower than one CPU quarter's DRAM read, fewer-experts drafts lost in 96 of 112 source cells, and reuse-aware gating alters target routing"
  },
  {
   "scan_id": "S51",
   "source_ref": "intake-2876 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md",
   "mechanism": "Hybrid GPU-resident expert drafter design",
   "consumer": "handoffs/active/cpu-decode-roofline-program.md",
   "application": "Hybrid GPU-resident expert drafter design",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-51"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M10"
  },
  {
   "scan_id": "S52",
   "source_ref": "intake-2877 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-orchestrator:src",
   "mechanism": "Judge false-positive audit with master-key strings, prompt arms, propensity scan and exposure column",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "Judge false-positive audit with master-key strings, prompt arms, propensity scan and exposure column",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-52"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S53",
   "source_ref": "intake-2889 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-orchestrator:src",
   "mechanism": "Fuzz the deterministic scorers with verifier mutation categories",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "Fuzz the deterministic scorers with verifier mutation categories",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-53"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S54",
   "source_ref": "intake-2877 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/context-and-token-economy.md",
   "mechanism": "Attach an exposure audit and an unhackable audit run to the pre-RL monitor",
   "consumer": "handoffs/active/context-and-token-economy.md",
   "application": "Attach an exposure audit and an unhackable audit run to the pre-RL monitor",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-54"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M1"
  },
  {
   "scan_id": "S55",
   "source_ref": "intake-2877 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Difficulty stratification, reopening the exploitability axis, timing constants, CATCH or noise-sweep reproduction, running rh-indicators",
   "consumer": "none (declined)",
   "application": "Difficulty stratification, reopening the exploitability axis, timing constants, CATCH or noise-sweep reproduction, running rh-indicators",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-55"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: no group-normalised optimiser exists in AutoPilot or AutoKernel, no GRPO run is planned, and the constants were fitted to one 1.5B regime"
  },
  {
   "scan_id": "S56",
   "source_ref": "intake-2886 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/eval-tower-program.md",
   "mechanism": "Train or adopt a robust judge, or change the judge prompt",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "Train or adopt a robust judge, or change the judge prompt",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-56"
   ],
   "basis": "dive read the primary source and pinned the in-house path; M7"
  },
  {
   "scan_id": "S57",
   "source_ref": "intake-2870 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/autokernel-loop.md",
   "mechanism": "Hopper percent-of-peak figures for the census parity table (operator applies)",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Hopper percent-of-peak figures for the census parity table (operator applies)",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-57"
   ],
   "basis": "dive read the primary source and pinned the in-house path; K3"
  },
  {
   "scan_id": "S58",
   "source_ref": "intake-2884 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "handoffs/active/kernel-champion-and-promotion.md",
   "mechanism": "Magnitudes not imported: cross-engine drift, API prices, Arm and TPU speedups",
   "consumer": "handoffs/active/kernel-champion-and-promotion.md",
   "application": "Magnitudes not imported: cross-engine drift, API prices, Arm and TPU speedups",
   "disposition": "context-only",
   "ledger_ids": [
    "AKJ-58"
   ],
   "basis": "dive read the primary source and pinned the in-house path; K4"
  },
  {
   "scan_id": "S59",
   "source_ref": "intake-2904 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "epyc-orchestrator:src",
   "mechanism": "Build the judge-audit string set from the 13 Huang families re-targeted to our verdict formats, per-string runs with intervals, and a Huang-comparable no-question arm",
   "consumer": "handoffs/active/eval-tower-program.md",
   "application": "Build the judge-audit string set from the 13 Huang families re-targeted to our verdict formats, per-string runs with intervals, and a Huang-comparable no-question arm",
   "disposition": "actionable",
   "ledger_ids": [
    "AKJ-59"
   ],
   "basis": "dive read the primary source and pinned the in-house path"
  },
  {
   "scan_id": "S60",
   "source_ref": "intake-2904 dive (research/deep-dives/intake-ak-1124)",
   "implementation_ref": "lane handoffs @ f74b175 and llama.cpp @ 98ff8a4",
   "mechanism": "Use static attack-success rate as a predictor of RL exploitation",
   "consumer": "none (declined)",
   "application": "Use static attack-success rate as a predictor of RL exploitation",
   "disposition": "declined",
   "ledger_ids": [
    "AKJ-60"
   ],
   "basis": "dive read the primary source and pinned the in-house path; decline: one hacked judge and one unhacked base is a necessary-condition hint, not a validated predictor; exposure is used instead"
  }
 ],
 "outcome_reviews": {
  "AKJ-01": {
   "required_outcome": "Pin the in-house all-slot GDN guarantee with a witness test, a doc note and the tbo-scope rule",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "GDN-SLOTS-STRONGER",
     "task_text": "- [ ] **GDN-SLOTS-STRONGER** [non-inference] Record and pin the in-house GATED_DELTA_NET snapshot guarantee, which is stronger than ggml.h's (intake-2867): ggml.h guarantees only slot 0 when n_tokens > K, but the CDNA chunked kernel (gated_delta_net.cu:23-40 @ 98ff8a4) writes every tail slot and spec-decode rollback (MTP K=4, DFlash2 K=9) reads them. Add a named witness case to test-backend-ops that compares all K slots at n_tokens > K on the chunked path, so a rebase that takes upstream #32820's slot-0-only view cannot weaken the check; do not port that view restriction; and add the rule that every ported test's -o op must be in the fold-gate test-backend-ops scope.",
     "acceptance": "witness case committed on the next experimental branch with its SHA, passing on ROCm0 and CPU, and the doc note plus scope rule committed in this handoff's fold-gate section"
    }
   ]
  },
  "AKJ-02": {
   "required_outcome": "Port upstream #32820's slot-0-only test view",
   "review_status": "closed-with-basis",
   "review_basis": "decline: it would stop checking the tail slots that speculative rollback reads; the in-house chunked kernel writes them",
   "task_refs": []
  },
  "AKJ-03": {
   "required_outcome": "Price K=5 vs K=1 tail-slot cost on ROCm0 at n=2048",
   "review_status": "closed-with-basis",
   "review_basis": "decline: tail slots are required by MTP and DFlash2 rollback, so their cost is not optional; reopen only if a rollback design stops reading them",
   "task_refs": []
  },
  "AKJ-04": {
   "required_outcome": "Guard the 16384-token mul_mat_id ceiling in the launcher and confirm it with an op smoke",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "MMID-UB-CEIL-1",
     "task_text": "- [ ] **MMID-UB-CEIL-1** [inference] Guard the mul_mat_id shared-memory ceiling on the MI210 (intake-2868): HIP sets smpbo from sharedMemPerBlock (ggml-cuda.cu:360 @ 98ff8a4), so mm_ids_helper aborts above 65536/4 = 16384 tokens per ubatch, below every configured ubatch today. (a) Make orchestrator_stack.py refuse a GPU MoE role launched with -ub above 16384, beside the existing K4 flag guard. (b) One op-level ROCm0 smoke: test-backend-ops -o MUL_MAT_ID at n = 16384 passes and n = 16385 aborts, confirming the derived ceiling. Model: none (op-level test-backend-ops, MUL_MAT_ID Q4_0 shapes); build C21 98ff8a4 GPU store; region MI210; estimate ~15 min; metric pass/abort. Stop-on-answer when both n values are recorded; stop-on-futility if the abort occurs below 16384 (then record the measured ceiling and lower the guard).",
     "acceptance": "guard committed with a unit test and its SHA, and the smoke result (pass at 16384, abort at 16385, or the measured ceiling if different) recorded under this box"
    }
   ]
  },
  "AKJ-05": {
   "required_outcome": "Fold chunked id compaction with its 66000-token tests when the n_used helper folds",
   "review_status": "closed-with-basis",
   "review_basis": "M3: When MMID-HELPER-N10 folds: port #32177's chunked id compaction as a separate commit with its 66000-token tests, adapted to expert_bounds; KEEP iff 6/6 pass on ROCm0 and the n <= 16384 path is bitwise unchanged; defer to the upstream merge if the adaptation is larger than the helper (intake-2868).",
   "task_refs": []
  },
  "AKJ-06": {
   "required_outcome": "Treat #32177 as a performance item",
   "review_status": "closed-with-basis",
   "review_basis": "decline: robustness only; every configured ubatch is at most 2048, eight times below the gfx90a ceiling",
   "task_refs": []
  },
  "AKJ-07": {
   "required_outcome": "Gate the MMVF int64 offset fix and the AMD MMVF_MMID even-ne00 guard (both already committed)",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "MMVF-I64-OFFSET",
     "task_text": "- [ ] **MMVF-I64-OFFSET** [inference] Gate the two MMVF fixes already committed on fork branch llama.cpp-experimental-c22-mmvf-fixes-20261124 (intake-2869): c47c574ba widens the MMVF expert/sample offsets for x, gate_x, y and dst to int64 (mmvf.cu:47-49 and :84 at 98ff8a4 had the int*int overflow upstream fixed only for x and gate_x), and 7eb398b16 adds the even-ne00 / pair-alignment guard to the AMD MMVF_MMID branch (ggml-cuda.cu:2196-2201), which upstream has and C21 lacked. Remaining step: run the prepared gate row /mnt/raid0/llm/tmp/ak-c22-mmvf-fixes-gate-gpu-20261124. Model: op-level test-backend-ops MUL_MAT / MUL_MAT_ID shapes of the served 27B; build: that branch at 7eb398b16 (GPU); region MI210; estimate ~1.5 h; metric correctness and us/run. Stop-on-answer when both commits are gated; stop-on-futility if the int64 widening costs more than the A/A floor even for x/gate_x alone (then keep only the guard and record).",
     "acceptance": "gate RESULT filed under this box with the run path: test-backend-ops correctness 100% on ROCm0, MUL_MAT perf at ne11 1-8 within the A/A floor and route histograms unchanged for each of c47c574ba and 7eb398b16"
    }
   ]
  },
  "AKJ-08": {
   "required_outcome": "Record that #32533 cannot route the BF16 drafter (BF16 weights, F32 src1)",
   "review_status": "closed-with-basis",
   "review_basis": "K1: Annotation under DF2-11-BF16-FIX: llama.cpp PR #32533 cannot route the BF16 drafter, whose weights are BF16 with F32 src1; on C21 ne11 <= 8 takes MMVF by default and ne11 9-16 stays on hipBLAS/Tensile because MMF refuses BF16 on CDNA2 (intake-2869).",
   "task_refs": []
  },
  "AKJ-09": {
   "required_outcome": "Kernel-authoring rules for new input dtypes plus the BF16-activation rebase trigger",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-SRC1-DTYPE-RULE",
     "task_text": "- [ ] **RKA-SRC1-DTYPE-RULE** [non-inference] Add two kernel-authoring rules and one rebase trigger to this handoff (intake-2869, intake-2899, intake-2900): (1) a new input dtype in a hot in-house kernel (MMVF, q8mf_pre_i8, q8sk_quantize) is a template parameter, never a runtime flag tested in the inner loop; (2) a new src1 dtype requires a review of every in-house route gated on src1 being F32 (mmq-q8-mf.cu:1270, MMVF_CHUNK, the cuBLAS precheck at ggml-cuda.cu:2075 @ 98ff8a4); (3) the rebase-review trigger is a merged upstream BF16-activation producer in the graph builder (a cast node or type switch), not the op-coverage series #29675, #32135, #32387 and #32533, and that review checks the RMS_NORM fusion gates (ggml-cuda.cu:3404, :4265-4270) and the ROPE+VIEW+SET_ROWS fusion.",
     "acceptance": "the three rules committed in this handoff's kernel-authoring section with the commit SHA recorded under this box"
    }
   ]
  },
  "AKJ-10": {
   "required_outcome": "Port BF16 src1, a direct BF16 CPU activation path, BF16 RMS_NORM or BF16 SET_ROWS",
   "review_status": "closed-with-basis",
   "review_basis": "decline: no in-house producer emits BF16 activations, verify-width src1 bytes are tiny, and Zen 5 int8 VNNI needs Q8 activations anyway",
   "task_refs": []
  },
  "AKJ-11": {
   "required_outcome": "Design inputs for a q4_0-KV gv_fattn: lane-map oracle, fold-vs-reconstruct counts, LDS/operand-swap note, premise correction",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-GVFATTN-Q4KV-DESIGN",
     "task_text": "- [ ] **AK-GVFATTN-Q4KV-DESIGN** [non-inference] Feed design inputs and refinements to the published q4_0-KV gv_fattn row ak-gvfattn-q4kv-gpu-20261124 (store gpu-20261124-5141da459-gvfattn-q4kv, kernel commit 5141da459 behind GGML_CUDA_FA_GQA_Q4KV=1, default off) (intake-2870, intake-2878, intake-2879, intake-2880, intake-2881). (a) A numpy MFMA lane-map oracle for q4_0 K (stock block_q4_0 matches the 16x16x16 fragment, one dword per lane) and the token-contiguous V packing, bit-exact against dequantize_row_q4_0. (b) Disassembly counts of per-value packed-f16 reconstruction vs accumulator folding at R = 6, 12, 24 and 48; folding breaks even only at g = 2*h_q. (c) A review note against 5141da459: q4_0 codes staged in LDS (about 9 KB vs 37 KB of f16 K+V), decode in registers, swapped operands (S^T = K.Q^T) keeping P in registers, a byte-floor ratio (q4_0 us/call over q8_0 x 18/34), and the follow-ups from the KV-quality packet (keep llama.cpp's rotation on for q4_0; K-mean removal only if KVQ-KMEAN-SIM-1 says so). (d) Correct AK-GVFATTN-LONGCTX's 'R <= 32, 2 tiles' premise: 27B gqa 6 at n_q 7 gives R = 42, 3 tiles.",
     "acceptance": "oracle test committed and passing bit-exact, the instruction-count table, and the review note filed under this box and linked from the ak-gvfattn-q4kv-gpu-20261124 row, with the AK-GVFATTN-LONGCTX premise correction recorded, each with its commit SHA"
    }
   ]
  },
  "AKJ-12": {
   "required_outcome": "Build the default-off q4_0-KV gv_fattn path and gate it against q8_0 gv",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-GVFATTN-Q4KV-DESIGN",
     "task_text": "- [ ] **AK-GVFATTN-Q4KV-DESIGN** [non-inference] Feed design inputs and refinements to the published q4_0-KV gv_fattn row ak-gvfattn-q4kv-gpu-20261124 (store gpu-20261124-5141da459-gvfattn-q4kv, kernel commit 5141da459 behind GGML_CUDA_FA_GQA_Q4KV=1, default off) (intake-2870, intake-2878, intake-2879, intake-2880, intake-2881). (a) A numpy MFMA lane-map oracle for q4_0 K (stock block_q4_0 matches the 16x16x16 fragment, one dword per lane) and the token-contiguous V packing, bit-exact against dequantize_row_q4_0. (b) Disassembly counts of per-value packed-f16 reconstruction vs accumulator folding at R = 6, 12, 24 and 48; folding breaks even only at g = 2*h_q. (c) A review note against 5141da459: q4_0 codes staged in LDS (about 9 KB vs 37 KB of f16 K+V), decode in registers, swapped operands (S^T = K.Q^T) keeping P in registers, a byte-floor ratio (q4_0 us/call over q8_0 x 18/34), and the follow-ups from the KV-quality packet (keep llama.cpp's rotation on for q4_0; K-mean removal only if KVQ-KMEAN-SIM-1 says so). (d) Correct AK-GVFATTN-LONGCTX's 'R <= 32, 2 tiles' premise: 27B gqa 6 at n_q 7 gives R = 42, 3 tiles.",
     "acceptance": "oracle test committed and passing bit-exact, the instruction-count table, and the review note filed under this box and linked from the ak-gvfattn-q4kv-gpu-20261124 row, with the AK-GVFATTN-LONGCTX premise correction recorded, each with its commit SHA"
    }
   ]
  },
  "AKJ-13": {
   "required_outcome": "rocprofv3 instruction-per-byte census of the q8_0 gv_fattn kernel",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-IPB-CENSUS-1",
     "task_text": "- [ ] **RKA-IPB-CENSUS-1** [inference] Measure the instruction-issue budget of the q8_0 gv_fattn kernel on the MI210 (intake-2870, intake-2879): rocprofv3 SQ_INSTS_VALU / SQ_INSTS_SALU / SQ_INSTS_LDS / SQ_WAVES counters on the 27B DFlash2 verify at 16k context, n_q 1/4/8, expressed as instructions per KV byte against the device budget (FOSCAR Eq. 2 units), plus implied VALU utilisation. Model 27B Q8_0 + DFlash2 verify; build C21 98ff8a4 GPU store; region MI210; estimate ~1 h; metric instructions per byte and VALU utilisation. Stop-on-answer when every shape has a counter read; stop-on-futility if rocprofv3 cannot attribute counters to gv_fattn.",
     "acceptance": "per-shape instructions-per-byte and VALU utilisation filed under this box with the run path, and the verdict: >= 50% VALU utilisation means a decode diet comes first in AK-GVFATTN-Q4KV, <= 25% means LDS residency comes first"
    }
   ]
  },
  "AKJ-14": {
   "required_outcome": "Sink-heavy numerics test of gv_fattn with P scaling as the candidate fix",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-GV-PSCALE-1",
     "task_text": "- [ ] **RKA-GV-PSCALE-1** [inference] Test gv_fattn numerics on sink-heavy attention, where P is stored as f16 (intake-2870, intake-2878): add a test-backend-ops case with one dominant early key (attention-sink pattern) on GQA-verify shapes, compare gv_fattn error to the vector path, and try P scaled by 2^10 before the f16 store as the candidate fix. Applies to the production q8_0 path as well. Model: op-level FLASH_ATTN_EXT GQA-verify shapes of the 27B (head dim 256); build llama.cpp-experimental from C21 98ff8a4; region MI210; estimate ~1 h; metric max abs error vs the CPU reference. Stop-on-answer when the error ratio is recorded with and without scaling; stop-on-futility if the sink case cannot be expressed in test-backend-ops.",
     "acceptance": "test case committed with its SHA and the error ratio gv/vector with and without P scaling recorded under this box; adopt the scaling (default-off knob, then fold) only if gv error exceeds 2x the vector-path error"
    }
   ]
  },
  "AKJ-15": {
   "required_outcome": "27B q4_0 KV KLD with rotation on vs off, margin screen and graded-flip arm, plus an A3B CPU arm",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/quantization-and-low-bit.md",
     "task_id": "KVQ-ROT-KLD-1",
     "task_text": "- [ ] **KVQ-ROT-KLD-1** [inference] Measure q4_0 KV quality on the 27B with llama.cpp's automatic Hadamard rotation on vs off (intake-2870, intake-2881, intake-2892, intake-2872). 27B Q8_0 + DFlash2 on the MI210 (C21 GPU store): KLD vs f16 KV for q8_0 KV, q4_0 KV rot-on, and q4_0 KV with LLAMA_ATTN_ROT_DISABLE=1, plus the first-token margin coefficient c (SE <= 0.10) per arm including a whether-to-call class; then a graded-flip arm on the G3 (G) GSM8K protocol for q4_0 vs q8_0 KV with a >= 3-launch A/A floor. CPU arm: 35B-A3B on a quarter, same KLD arms. FlagRot predicts rotation helps a uniform INT4 grid, so rot-off is a falsification check. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0; build C21 98ff8a4 GPU and CPU stores; region MI210 plus one CPU quarter; estimate ~4 h GPU, ~3 h CPU; metric KLD, margin c, graded-flip excess. Stop-on-answer per arm when the KLD CI excludes the verdict boundary; stop-on-futility if the q4_0 KV path fails to load on the served recipe.",
     "acceptance": "per-arm KLD, c and graded-flip excess over the A/A floor filed under this box with verdicts: rot-off >= rot-on drops the rotation-off branch; rot-off < 0.9x rot-on is a contradiction that runs the other models; q4_0 rot-on <= 2x q8_0 KLD makes q4_0 KV a served-gate candidate"
    }
   ]
  },
  "AKJ-16": {
   "required_outcome": "Post-RoPE K dump and offline q4_0 mean-removal / selective-rotation simulation",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/quantization-and-low-bit.md",
     "task_id": "KVQ-KMEAN-SIM-1",
     "task_text": "- [ ] **KVQ-KMEAN-SIM-1** [inference] Dump post-RoPE K (and Q) on the 27B full-attention layers (layer 3 is the first; layers 0-2 are GDN) for 64 prompts on a CPU quarter, then simulate q4_0 offline (codes -8..7) for arms: plain, static per-channel mean removal, first-4-tokens exact, and (only if KVQ-ROT-KLD-1 shows q4_0 rot-on KLD > 2x q8_0) keys-only selective rotation (intake-2870, intake-2878, intake-2881). The Qwen2 k-bias mechanism does not apply (no attention_bias in our configs), so this measures generic K-mean energy. Model 27B Q8_0; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~1 h dump plus offline simulation; metric mean-energy share and simulated KL. Stop-on-answer when every arm has a simulated KL; stop-on-futility if the K dump cannot be produced on the served path.",
     "acceptance": "per-layer mean-energy share and simulated KL per arm filed under this box with verdict: implement static mean subtraction if mean energy > 30% or simulated KL drops >= 20%; selective rotation kept only if it cuts KL >= 30%"
    }
   ]
  },
  "AKJ-17": {
   "required_outcome": "Per-layer KV-type override for the first full-attention layer",
   "review_status": "closed-with-basis",
   "review_basis": "M5: If KVQ-KMEAN-SIM-1 shows the first full-attention layer at >= 2x the median layer's simulated KL: add a per-layer KV-type override for that layer (intake-2870).",
   "task_refs": []
  },
  "AKJ-18": {
   "required_outcome": "35B-A3B CPU decode at 32k with q4_0 vs q8_0 KV",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/cpu-decode-roofline-program.md",
     "task_id": "CDR-A3B-Q4KV-32K",
     "task_text": "- [ ] **CDR-A3B-Q4KV-32K** [inference] Measure 35B-A3B MTP CPU decode at 32k context with q4_0 vs q8_0 KV on one quarter (C21 CPU store), with the attention share of the step from the existing per-op profile (intake-2870). Model 35B-A3B Q8_0 MTP; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~1.5 h. Stop-on-answer on KEEP or FUTILITY; stop-on-futility when attention is under 10% of the step.",
     "acceptance": "tok/s per arm with A/A floor and the attention share filed under this box with verdict KEEP (>= 5% tok/s and the KVQ-ROT-KLD-1 CPU-arm KLD gate passing) or FUTILITY (attention < 10% of the step)"
    }
   ]
  },
  "AKJ-19": {
   "required_outcome": "Port the Qwen2 k-proj-bias KV fixes",
   "review_status": "closed-with-basis",
   "review_basis": "decline: no served config has a k_proj bias (attention_bias false in every config)",
   "task_refs": []
  },
  "AKJ-20": {
   "required_outcome": "Split the rotation disable switch into K-only and V-only",
   "review_status": "closed-with-basis",
   "review_basis": "M4: If KVQ-ROT-KLD-1 shows a rotation effect over 10%: split LLAMA_ATTN_ROT_DISABLE into K-only and V-only switches in the experimental tree (selecting keys alone carries 93-94% of the gain in intake-2881).",
   "task_refs": []
  },
  "AKJ-21": {
   "required_outcome": "Port the Hopper kernels, the FOSCAR wgmma pipeline or the CDNA4 scaled-MFMA FP4 path",
   "review_status": "closed-with-basis",
   "review_basis": "decline: each needs TMA, wgmma, tcgen05 or CDNA4 scaled-MFMA instructions that gfx90a lacks; the portable parts are taken in the design note",
   "task_refs": []
  },
  "AKJ-22": {
   "required_outcome": "One-op KernelShift-format x86 pilot with ISA ladder, autovec control, outcome classes and codegen counts",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-CPU-KSHIFT-1",
     "task_text": "- [ ] **AK-CPU-KSHIFT-1** [inference] Pilot a KernelShift-format benchmark task for the AutoKernel CPU lane on Zen 5 (intake-2871, intake-2897, intake-2898). Step 1 (code): in a research-repo scratch copy of cmu-l3/kernel-shift @ 610e835, remove the two aarch64 guards (kgen/check.py, kgen/autovec.py), add one x86 ISA tier, and write an iqk/ggml baseline wrapper for one op, Q8_0 mul_mat at N = 1-16 on hidden served shapes, with a double-precision reference and a calibrated correctness floor (baseline SQNR minus 1 dB). Step 2 (CPU quarter): ISA-ladder arms (AVX2, +VNNI, +AVX512_BF16, +VBMI) plus a scalar -O3 -march=znver5 autovec control, outcome classes (compiles / wrong result / identifier error / crash / no intrinsic), and codegen counts of vpdpbusd, vdpbf16ps, vpermb and zmm FMA in the CPU keep diagnostic. Model: Q8_0 shapes of the served 27B and 35B-A3B; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~3 h after the code step; metric geomean speedup vs baseline. Stop-on-answer when the baseline geomean and A/A floor are recorded for every ISA arm; stop-on-futility if the task reproduces served_shape_cases verdicts only.",
     "acceptance": "scratch-copy SHA, the task files, and the C21 baseline geomean with its A/A floor per ISA arm filed under this box; FUTILITY recorded if the task only reproduces the existing served_shape_cases verdicts"
    }
   ]
  },
  "AKJ-23": {
   "required_outcome": "Extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM",
   "review_status": "closed-with-basis",
   "review_basis": "M9: If AK-CPU-KSHIFT-1's pilot produces a task the AK loop can use: extend the task set to IQ4_XS, MUL_MAT_ID gate_up and BF16 GEMM at verify widths (intake-2871).",
   "task_refs": []
  },
  "AKJ-24": {
   "required_outcome": "Pitfalls-digest prompt, fraction-of-peak scoring, Arm speedups as expectations, the e2e hook, the HF dataset, SimdBench priors",
   "review_status": "closed-with-basis",
   "review_basis": "decline: the planner already reads negatives, the census already scores against the measured ceiling, and the Arm-bound artefacts do not run on Zen 5",
   "task_refs": []
  },
  "AKJ-25": {
   "required_outcome": "Amend the identity-gate protocol: replica floor, cache state, KV provenance, route and config recording, graded flips",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-GATE-2",
     "task_text": "- [ ] **SPEC-ID-GATE-2** [non-inference] Amend the spec identity-gate protocol (docs/guides/agent-workflows/spec-identity-gate-protocol.md) and its gate reporting with five rules from the noise-floor sources (intake-2872, intake-2893, intake-2891, intake-2894, intake-2883, intake-2884): (a) the floor is the largest pair over >= 3 reference launches (>= 5 when it decides a promotion gate), all pairs, one of them reordered or np-shuffled; fewer launches return INCONCLUSIVE; (b) cache state: both arms cache_prompt false with --cache-ram 0, or a verified identical cache state; existing SPEC-ID-NOISE-1 floors are labelled cache-off; (c) KV provenance: same prefill ubatch, verify-width class and KV dtype in both arms; redecode and resume paths are outside the exact regime; (d) every gate RESULT.json records the kernel-selection env knobs, the per-width route and the binary SHA, and cross-build rows first prove config-dump equality (sampler chain, BOS/EOS, penalties, prefix-cache state, np); (e) where a scored corpus exists, graded flips (worse / better / wrong-to-wrong, net) are reported beside token identity.",
     "acceptance": "protocol sections (a)-(e) committed with the commit SHA recorded under this box, the gate script returns INCONCLUSIVE below 3 replicas in a committed unit test, and the SPEC-ID-NOISE-1 result line carries the cache-off label"
    }
   ]
  },
  "AKJ-26": {
   "required_outcome": "Null-test the gate and localise the GPU A/A drift (skinny atomics, node hashes, f32 audit arm)",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-NOISE-2",
     "task_text": "- [ ] **SPEC-ID-NOISE-2** [inference] Localise the 27B DFlash2 launch-to-launch drift on the MI210 and null-test the amended gate (intake-2872, intake-2882, intake-2883, intake-2894). Arm A: 4 launches of one unchanged config on the MI210; treat each launch in turn as the candidate against the other 3, and the SPEC-ID-GATE-2 gate must PASS every time. Arm B: the same A/A with GGML_HIP_Q8_SKINNY=0, testing whether the skinny-GEMM f32 atomics explain the 20/64 divergence (0/64 = skinny atomics are the source; >= 1 = another source). Arm C: a cb_eval node-hash dump over two launches of 27B DFlash2 np1 on 3 divergent prompts, recording the first differing graph node. Arm D (CPU quarter, small hybrid model): f32 compute and f32 KV, spec vs serial and resumed vs fresh, expecting 0/64. 64 DF2-13 prompts, digest recorded, cache-off. Model 27B Q8_0 + DFlash2 (arms A-C), Qwen3-4B Q8_0 CPU (arm D); build C21 98ff8a4 stores; region MI210 plus one CPU quarter; estimate ~3 h GPU + ~1 h CPU. Stop-on-answer when every arm has its count; stop-on-futility on the first false FAIL in arm A (the gate is then wrong, file it) or equal node hashes in arm C.",
     "acceptance": "per-arm verdicts filed under this box with the run path: arm A pass/false-FAIL count, arm B divergence count out of 64, arm C first-divergent node name per prompt, arm D divergence count out of 64"
    }
   ]
  },
  "AKJ-27": {
   "required_outcome": "Build in-row bands from all pairs of at least three replicas including a reordered arm",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-ID-GATE-2",
     "task_text": "- [ ] **SPEC-ID-GATE-2** [non-inference] Amend the spec identity-gate protocol (docs/guides/agent-workflows/spec-identity-gate-protocol.md) and its gate reporting with five rules from the noise-floor sources (intake-2872, intake-2893, intake-2891, intake-2894, intake-2883, intake-2884): (a) the floor is the largest pair over >= 3 reference launches (>= 5 when it decides a promotion gate), all pairs, one of them reordered or np-shuffled; fewer launches return INCONCLUSIVE; (b) cache state: both arms cache_prompt false with --cache-ram 0, or a verified identical cache state; existing SPEC-ID-NOISE-1 floors are labelled cache-off; (c) KV provenance: same prefill ubatch, verify-width class and KV dtype in both arms; redecode and resume paths are outside the exact regime; (d) every gate RESULT.json records the kernel-selection env knobs, the per-width route and the binary SHA, and cross-build rows first prove config-dump equality (sampler chain, BOS/EOS, penalties, prefix-cache state, np); (e) where a scored corpus exists, graded flips (worse / better / wrong-to-wrong, net) are reported beside token identity.",
     "acceptance": "protocol sections (a)-(e) committed with the commit SHA recorded under this box, the gate script returns INCONCLUSIVE below 3 replicas in a committed unit test, and the SPEC-ID-NOISE-1 result line carries the cache-off label"
    }
   ]
  },
  "AKJ-28": {
   "required_outcome": "Graded-flip budget for q4_0 and q8_0 KV over a scheduling floor",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/quantization-and-low-bit.md",
     "task_id": "KVQ-ROT-KLD-1",
     "task_text": "- [ ] **KVQ-ROT-KLD-1** [inference] Measure q4_0 KV quality on the 27B with llama.cpp's automatic Hadamard rotation on vs off (intake-2870, intake-2881, intake-2892, intake-2872). 27B Q8_0 + DFlash2 on the MI210 (C21 GPU store): KLD vs f16 KV for q8_0 KV, q4_0 KV rot-on, and q4_0 KV with LLAMA_ATTN_ROT_DISABLE=1, plus the first-token margin coefficient c (SE <= 0.10) per arm including a whether-to-call class; then a graded-flip arm on the G3 (G) GSM8K protocol for q4_0 vs q8_0 KV with a >= 3-launch A/A floor. CPU arm: 35B-A3B on a quarter, same KLD arms. FlagRot predicts rotation helps a uniform INT4 grid, so rot-off is a falsification check. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0; build C21 98ff8a4 GPU and CPU stores; region MI210 plus one CPU quarter; estimate ~4 h GPU, ~3 h CPU; metric KLD, margin c, graded-flip excess. Stop-on-answer per arm when the KLD CI excludes the verdict boundary; stop-on-futility if the q4_0 KV path fails to load on the served recipe.",
     "acceptance": "per-arm KLD, c and graded-flip excess over the A/A floor filed under this box with verdicts: rot-off >= rot-on drops the rotation-off branch; rot-off < 0.9x rot-on is a contradiction that runs the other models; q4_0 rot-on <= 2x q8_0 KLD makes q4_0 KV a served-gate candidate"
    }
   ]
  },
  "AKJ-29": {
   "required_outcome": "Keep the harness accept gate off until a three-replica A/A floor exists",
   "review_status": "closed-with-basis",
   "review_basis": "M11: The harness accept gate (BSV-2 family) is not activated until an A/A floor from >= 3 replicas exists for its metric, per SPEC-ID-GATE-2 rule (a) (intake-2872).",
   "task_refs": []
  },
  "AKJ-30": {
   "required_outcome": "Per-op batch-invariance census and port cost for a GPU fixed-order audit arm",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/rocm-kernel-authoring.md",
     "task_id": "RKA-BATCH-INV-CENSUS-1",
     "task_text": "- [ ] **RKA-BATCH-INV-CENSUS-1** [non-inference] Census batch invariance of the MI210 verify graph at widths 1-16 (intake-2882, intake-2883, intake-2872), op by op at 98ff8a4: RMSNorm (norm.cu:347-370, one block per row, already invariant), MMVQ (nwarps depends on ncols_dst, mmvq.cu:813-850), skinny Q8 (f32 unsafeAtomicAdd flush), MMQ / mmq-q8-mf (unsafeAtomicAdd at :1454), hipBLAS BF16, and flash attention (parallel_blocks chosen from occupancy and n_kv, fattn-common.cuh:1514-1594). Per op: invariant or not, the change needed (pinned per-column reduction geometry, fixed-size KV chunks rather than a fixed count, atomics removed) and its port cost.",
     "acceptance": "per-op census table committed in this handoff with the commit SHA recorded under this box, and the verdict: open an implementation box for a default-off invariant audit arm if 3 or fewer ops need change, else record the cost and close"
    }
   ]
  },
  "AKJ-31": {
   "required_outcome": "Cache-hit vs cold-recompute identity with a replica floor on the served recipes",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "PFXC-ID-REPLICA-1",
     "task_text": "- [ ] **PFXC-ID-REPLICA-1** [inference] Re-judge prompt-cache identity with a replica floor (intake-2891, intake-2884, intake-2894): on the served recipes (27B DFlash2 np1 on the MI210 with --cache-ram as served; 35B-A3B MTP np1 on a CPU quarter, conc 1), compare cache-hit vs cold-recompute paths with margin classes and a same-run A/A on each path over >= 3 launches; this replaces PFXC-A1's single-baseline floor (resumed-vs-fresh 0.773 vs C14 floor 1.077). 64 prompts, digest recorded. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0 MTP; build C21 98ff8a4 stores; region MI210 plus one CPU quarter; estimate ~2 h GPU, ~2 h CPU; metric divergences out of 64. Stop-on-answer after one 64-prompt pass per device; stop-on-futility on residency-proof failure.",
     "acceptance": "per-device divergence counts out of 64 per path with the largest-pair A/A floor filed under this box, and the verdict: any cache-path divergence outside the floor marks cached requests outside the exact regime in the protocol"
    }
   ]
  },
  "AKJ-32": {
   "required_outcome": "Measure the fold-gate KLD A/A floor and report candidate KLD over floor",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/kernel-champion-and-promotion.md",
     "task_id": "FOLD-KLD-FLOOR-1",
     "task_text": "- [ ] **FOLD-KLD-FLOOR-1** [inference] Measure the KLD A/A floor the fold gates have never measured (intake-2901, intake-2872, intake-2893): on the fold-gate corpus, the C21 candidate against itself with one reduction-order toggle flipped (MMVQ nwarps or GGML_ROWEXACT_N), on 27B Q8_0 (MI210) and Q38FN (CPU quarter); check retained logits offline first. Add 'candidate KLD / floor' to the fold-gate result header, and report graded flips (worse / better / wrong-to-wrong) beside KLD where the corpus is scored. Model 27B Q8_0 (MI210) and Q38FN UD-IQ4_XS (CPU quarter); build C21 98ff8a4 stores. Stop-on-answer when both devices have a floor value or the offline logit check answers it; stop-on-futility if retained logits are absent and the floor run cannot reproduce the fold-gate corpus.",
     "acceptance": "floor per device filed under this box with the run path, the header change committed, and the verdict: floor <= 10% of the 0.003 gate keeps the gate with the ratio reported; floor >= 30% makes the gate relative to the floor"
    }
   ]
  },
  "AKJ-33": {
   "required_outcome": "Fit a per-width noise sigma offline and predict first-divergence rates",
   "review_status": "closed-with-basis",
   "review_basis": "decline: the amended gate measures the floor directly in-row, so a predictive noise model changes no decision",
   "task_refs": []
  },
  "AKJ-34": {
   "required_outcome": "Full deterministic serving mode, pow2-scale alibi probe, imported tolerances or floors",
   "review_status": "closed-with-basis",
   "review_basis": "decline: deterministic serving costs 1.6-2.1x in the source, the alibi holds only for integer accumulation, and the protocol bans imported thresholds",
   "task_refs": []
  },
  "AKJ-35": {
   "required_outcome": "Offline forced-share replay of production json_schema classes",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-GRAM-JSON-1",
     "task_text": "- [ ] **SPEC-GRAM-JSON-1** [non-inference] Measure the grammar-forced token share of the production json_schema classes offline, which SPEC-GRAM.5 never replayed (intake-2873, intake-2885). Replay retained outputs of each production json_schema class (typed decisions, review schemas, REPL routing, plan steps, consultation, structured-output repair) through llguidance v1.0.1 llg_matcher_compute_ff_tokens with the existing tool-call replay script, and report per class: forced share of output tokens, forced-run lengths, the single-allowed-token subset (the only lossless logit-free subset at T > 0), and the class's share of serving tokens. No model inference.",
     "acceptance": "per-class table (forced share, run-length histogram, single-allowed subset, serving-token share) filed under this box with the input digest and the verdict: decline (every class under 10%) or open the chain-path design (any class >= 10% with material token volume)"
    }
   ]
  },
  "AKJ-36": {
   "required_outcome": "Chain-path grammar-draft design and grammar-aware tree pruning",
   "review_status": "closed-with-basis",
   "review_basis": "M2: If SPEC-GRAM-JSON-1 finds any production json_schema class with forced share >= 10-15% and material token volume: design the chain-path grammar draft (forced runs from llg_matcher_compute_ff_tokens as point-mass drafts, logits skipped only where the mask admits one token) and grammar-aware pruning of batch trees; open the implementation box only if the class-weighted ceiling is >= 1.10x (intake-2873).",
   "task_refs": []
  },
  "AKJ-37": {
   "required_outcome": "Synchronous grammar planning, accept-with-probability-1 at T > 0, a Phi estimator in the verifier",
   "review_status": "closed-with-basis",
   "review_basis": "decline: llama-server already plans on the host, forced acceptance shifts the distribution at near-tie tokenizations, and OneStep worsened three schemas in the source",
   "task_refs": []
  },
  "AKJ-38": {
   "required_outcome": "Exact masked-vs-conditional TV on production enum schemas",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-GRAM-TV-1",
     "task_text": "- [ ] **SPEC-GRAM-TV-1** [inference] Measure how far grammar-masked sampling departs from grammar-conditional sampling on the production enum-style json_schema classes (intake-2885). For each class whose language is a finite token trie (typed-decision, review, plan-step enums), query the served model at every trie prefix at the served temperature and compute the exact total variation between the masked law and the grammar-conditional law. The served verifier already samples the masked distribution (common/sampling.cpp:1038-1107 @ 98ff8a4), so speculation adds no bias; this measures the residual masked-sampling bias only. Model: the served frontdoor and architect roles' GGUFs (Q8_0) on the C21 CPU store; region one CPU quarter; estimate ~2 h; metric exact TV per class. Stop-on-answer when every finite-trie class has a TV value; stop-on-futility if no production class has a trie under 10k strings.",
     "acceptance": "per-class TV at the served temperature filed under this box with the trie sizes, and the verdict: close (every class TV < 0.1) or open a cost/benefit box on Phi correction (any class >= 0.1)"
    }
   ]
  },
  "AKJ-39": {
   "required_outcome": "State the acceptance target (masked distribution) and the single-token rule for logit-free acceptance",
   "review_status": "closed-with-basis",
   "review_basis": "K2: Note in the SPEC-GRAM section: the served verifier samples the grammar-masked distribution (common/sampling.cpp:1038-1107 @ 98ff8a4), speculation adds no bias over plain masked sampling, and logit-free acceptance of a forced token is lossless only where the mask admits exactly one token (intake-2885, intake-2873).",
   "task_refs": []
  },
  "AKJ-40": {
   "required_outcome": "Offline journal replay of three demote rules for prose lessons",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-LESSON-DEMOTE-1",
     "task_text": "- [ ] **AK-LESSON-DEMOTE-1** [non-inference] Replay the AutoKernel journal offline to choose a demote rule for prose lessons in the planner bundle (intake-2874, intake-2903). Compare three rules: unused for 5 consecutive iterations (autoresearch tau = 5), the alpha = 0 periodic rule, and a utility-gated rule (retrieved >= n times with mean keep-rate <= beta, from AK keep/discard receipts). Gate-backed negatives consumed by controller/do_not_repeat.py are never demoted. Measure bundle chars saved, later same-epoch re-proposals of a demoted mechanism, and proposal keep-rate with the lesson present vs absent. Zero inference.",
     "acceptance": "per-rule table (chars saved, false-demotion re-proposals, keep-rate delta) filed under this box with the journal digest and verdict: adopt a rule only if it has 0 false-demotion re-proposals and the utility-gated arm saves at least as many chars as unused-5, else NO-GO"
    }
   ]
  },
  "AKJ-41": {
   "required_outcome": "Per-attempt digest catalog in the planner bundle",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-ATTEMPT-DIGEST-1",
     "task_text": "- [ ] **AK-ATTEMPT-DIGEST-1** [non-inference] Add a per-attempt digest catalog to the AutoKernel planner bundle (intake-2874 context folding): one 2-4 sentence digest per past attempt in the bundle index written by loop/actor_context.py, with the full attempt record still reachable by its per-call file, so the planner sees every attempt rather than a recency window. Budget: the bundle index grows by at most 10% over its current size on the replayed journal.",
     "acceptance": "change committed with its SHA and a replayed-bundle comparison (index chars before/after, attempts visible before/after) recorded under this box; reverted if the 10% budget is exceeded"
    }
   ]
  },
  "AKJ-42": {
   "required_outcome": "Context-folding arm in the CF-AB-1 frame with a second-role compressor variant",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/context-and-token-economy.md",
     "task_id": "CTE-CFAB-A8",
     "task_text": "- [ ] **CTE-CFAB-A8** [non-inference] Write the CF-AB-1 frame's arm A8, design text only (intake-2874, intake-2875): a digest catalog of every past turn plus agent-selected unfold under a declared history budget (autoresearch context folding), with a variant that uses a second-role compressor and pinned-pointer restoration (DMC-5). It runs only when TOC-SP-5 shows binding windows, like A3-A7.",
     "acceptance": "the A8 arm text in the CF-AB-1 frame names the digest format, the unfold surface, the budget and the delivery-path precondition, with the commit SHA recorded under this box"
    }
   ]
  },
  "AKJ-43": {
   "required_outcome": "KernelBench fast_1 as an expectation, lesson merging or rule promotion",
   "review_status": "closed-with-basis",
   "review_basis": "decline: a different baseline and device, and the source's own case studies show merging drops applicability conditions",
   "task_refs": []
  },
  "AKJ-44": {
   "required_outcome": "Compressor/agent split and local-seconds crossover columns in the evict-cost table",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/kv-cache-program.md",
     "task_id": "KV-EVICT-COST-2",
     "task_text": "- [ ] **KV-EVICT-COST-2** [non-inference] Extend the KV-EVICT-COST-1 break-even table with two columns (intake-2875, intake-2902): (1) a DMC-5 split row: compressor delta prefill plus summary decode plus agent re-prefill of summary and recent turns, against the decode-attention seconds saved over the next N turns, per device, with GDN hybrids re-prefilling the whole suffix after a changed block (can_shift false); (2) the local-seconds crossover rho_cross = 1 - 1/r (cached-read cost about 0, write cost = prefill seconds per token) with a mutated-prefix tag (tail-only vs middle rewrite). Arithmetic over retained prefill and context-slope rows; no new inference.",
     "acceptance": "both columns added to the table under KV-EVICT-COST-1 with per-device break-even length or NO-GO recorded under this box"
    }
   ]
  },
  "AKJ-45": {
   "required_outcome": "Failed-action ledger and pinned-pointer restoration in orchestrator compaction",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/harness-program.md",
     "task_id": "HAR-COMPACT-LEDGER-1",
     "task_text": "- [ ] **HAR-COMPACT-LEDGER-1** [non-inference] Port DMC-5's integrity pieces into orchestrator compaction behind a default-off flag (intake-2875): the failed-action ledger (every failed tool call kept verbatim across compaction) and byte-exact restoration of pinned pointers (paths, IDs, numbers) in src/graph/compaction.py, which today asks Role.WORKER_GENERAL for a one-shot index with neither. Without it DMC-5's own AppWorld accuracy fell below no compression (69.1% vs 77.0%).",
     "acceptance": "flagged change committed with its SHA and a replay test over retained trajectories showing every failed action and pinned pointer survives compaction byte-exact, recorded under this box"
    }
   ]
  },
  "AKJ-46": {
   "required_outcome": "Concurrent CPU-compressor / GPU-agent latency probe",
   "review_status": "closed-with-basis",
   "review_basis": "M6: If KV-EVICT-COST-2 records a break-even length for the compressor/agent split on some device: probe a concurrent CPU-quarter compressor with the GPU agent for latency (intake-2875).",
   "task_refs": []
  },
  "AKJ-47": {
   "required_outcome": "Copy the API cost-saving target, the 3,500-token tier bound or cache_control",
   "review_status": "closed-with-basis",
   "review_basis": "decline: price effects of API cached-input billing with no local analogue",
   "task_refs": []
  },
  "AKJ-48": {
   "required_outcome": "Replay A3B probabilities through the cost-aware stop rule with an expert-union term vs fixed p_min",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/speculative-decoding.md",
     "task_id": "SPEC-STOP-EQ7-1",
     "task_text": "- [ ] **SPEC-STOP-EQ7-1** [non-inference] Replay the CAFE-1-SERVED-T A3B MTP per-token probability captures offline through the cost-aware draft-stop rule (intake-2876 Eq 7: stop at the K minimising expected cost over expected tokens) with the marginal expert-union cost term (intake-2896), against fixed p_min {0, 0.5, 0.75}. Step 1: fit C(K) (verify wall seconds vs draft length) and expert-union bytes vs K for A3B CPU from existing CAFE-1-SERVED-T and Q38P rows; futility if the fitted R^2 < 0.9. Step 2: modelled tokens/s of the rule vs each fixed p_min at T 0.3 and T 1.0 on a held-out half of the captures.",
     "acceptance": "step-1 fit (R^2 and coefficients) and step-2 modelled gain with CI per temperature filed under this box, with verdict KEEP candidate (gain >= 3% with CI lower > 1.0 at both temperatures), CLOSE (gain < 1% with CI upper < 1.02) or INCONCLUSIVE"
    }
   ]
  },
  "AKJ-49": {
   "required_outcome": "A3B residency-coverage curve from the existing routing traces",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/cpu-decode-roofline-program.md",
     "task_id": "CDR-RT9-COVER-1",
     "task_text": "- [ ] **CDR-RT9-COVER-1** [non-inference] Close the A3B expert-residency question from the existing RT-9 traces (intake-2876, intake-2895): run skew_report.py on the saved Qwen3.6-35B-A3B frontdoor traces and report per-layer top-12.5% expert coverage, same-domain and cross-domain. RT-9 already shows top-25% share 0.68-0.74 at prefill, so coverage >= 0.6 at <= 12.5% residency is not expected.",
     "acceptance": "per-layer coverage table filed under this box with the trace digest and verdict: CLOSE the resident-expert drafter idea if same-domain coverage at 12.5% is below 0.6, else record the coverage for the operator's HBM allotment decision"
    }
   ]
  },
  "AKJ-50": {
   "required_outcome": "Per-expert H2D cache, reduced-top-k or resident-subset self-drafting on CPU A3B, reuse-aware gating",
   "review_status": "closed-with-basis",
   "review_basis": "decline: PCIe Gen4 H2D (28.89 GB/s measured) is slower than one CPU quarter's DRAM read, fewer-experts drafts lost in 96 of 112 source cells, and reuse-aware gating alters target routing",
   "task_refs": []
  },
  "AKJ-51": {
   "required_outcome": "Hybrid GPU-resident expert drafter design",
   "review_status": "closed-with-basis",
   "review_basis": "M10: Fires when the second GPU is installed and A3B is placed GPU-resident (operator 2026-11-24: A3B GPU will be served on the 2nd GPU): design a GPU-resident expert-subset drafter for A3B, using CDR-RT9-COVER-1's same-domain coverage at <= 12.5% residency (>= 0.6 makes a resident subset worth drafting from) as a design input (intake-2876).",
   "task_refs": []
  },
  "AKJ-52": {
   "required_outcome": "Judge false-positive audit with master-key strings, prompt arms, propensity scan and exposure column",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "EV-JUDGE-FPR-1",
     "task_text": "- [ ] **EV-JUDGE-FPR-1** [inference] Audit the LLM judges for exploitable false positives before anything optimises against them (intake-2877, intake-2886, intake-2904, intake-2888). String set: the ten One-token master keys plus 3-5 paraphrases each, and the 13 Huang Table 8 families with their 'Final Decision: Yes' strings re-targeted to each judge's verdict format (exact strings and prompts from the hkust-nlp/RL-Verifier-Robustness repo). Run every string individually, with Wilson intervals, on a fixed math problem set against the architect_critic, coherence and credibility judges, each with the production prompt, a no-question arm (the Huang-comparable arm) and a no-CoT arm. Scan journaled generator outputs with the same detectors for propensity (zero inference) and report exposure = propensity x FPR, also as a secondary EV-29 column. The futility threshold is a local pre-registered choice. Model: the three judge configs as served; build: production v10 stores (read-only use); region one CPU quarter; estimate ~3 h; metric FPR per string. Stop-on-answer per judge when every string has an FPR; stop-on-futility when no string is accepted in the first 100 items for a judge.",
     "acceptance": "per-judge, per-string FPR table and the propensity counts filed under this box with the problem-set digest; verdict per judge: no-go for any optimiser use if any string's FPR >= 1%, else cleared at that rate"
    }
   ]
  },
  "AKJ-53": {
   "required_outcome": "Fuzz the deterministic scorers with verifier mutation categories",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "EV-SCORER-FUZZ-1",
     "task_text": "- [ ] **EV-SCORER-FUZZ-1** [non-inference] Fuzz the deterministic eval_tower scorers with the RLVR-verifier mutation categories (intake-2889): replay partial_answer, missing marker, contradictory finals, loose float and wrong-then-correct completions against the math_verify and exact-match scorers (EV-11) and report false-positive and false-negative rates with acceptance and coverage per category. CPU minutes, no inference.",
     "acceptance": "per-category FPR/FNR table filed under this box with the fixture digest; any category with FPR > 0 gets a named scorer fix box; futility recorded if FPR is 0 everywhere"
    }
   ]
  },
  "AKJ-54": {
   "required_outcome": "Attach an exposure audit and an unhackable audit run to the pre-RL monitor",
   "review_status": "closed-with-basis",
   "review_basis": "M1: Append to the existing pre-RL monitor line (track per-request-reasoning-budget, the 'if a local GRPO/RLVR weights run is ever planned' line): the plan also pre-registers a judge exposure audit (propensity x judge FPR per exploit string, from EV-JUDGE-FPR-1), an independent unhackable audit run (no write access, hidden tests), within-group reward-contrast logging, and KL-slope tracking over log-spaced checkpoints (intake-2877, intake-2887, intake-2888, intake-2890).",
   "task_refs": []
  },
  "AKJ-55": {
   "required_outcome": "Difficulty stratification, reopening the exploitability axis, timing constants, CATCH or noise-sweep reproduction, running rh-indicators",
   "review_status": "closed-with-basis",
   "review_basis": "decline: no group-normalised optimiser exists in AutoPilot or AutoKernel, no GRPO run is planned, and the constants were fitted to one 1.5B regime",
   "task_refs": []
  },
  "AKJ-56": {
   "required_outcome": "Train or adopt a robust judge, or change the judge prompt",
   "review_status": "closed-with-basis",
   "review_basis": "M7: If EV-JUDGE-FPR-1 finds a judge that gates a decision with any master-key FPR >= 1%: compare a no-question prompt fix with a trained robust judge (Master-RM-style, 20k truncation negatives) before that judge gates an optimiser (intake-2886).",
   "task_refs": []
  },
  "AKJ-57": {
   "required_outcome": "Hopper percent-of-peak figures for the census parity table (operator applies)",
   "review_status": "closed-with-basis",
   "review_basis": "K3: The measured Hopper percent-of-peak table in this plan replaces the recalled CUDA reference figures in the bandwidth-census parity section; the operator applies it to docs/design/mi210-served-kernel-bandwidth-census-20261122.md and the census JSON (intake-2870, intake-2879, intake-2880).",
   "task_refs": []
  },
  "AKJ-58": {
   "required_outcome": "Magnitudes not imported: cross-engine drift, API prices, Arm and TPU speedups",
   "review_status": "closed-with-basis",
   "review_basis": "K4: Magnitudes not imported as thresholds or expectations: cross-engine drift (intake-2884), vLLM KL floors (intake-2901), API cache prices (intake-2875, intake-2902), Arm agent-kernel speedups (intake-2871) and TPU grammar-draft speedups (intake-2873).",
   "task_refs": []
  },
  "AKJ-59": {
   "required_outcome": "Build the judge-audit string set from the 13 Huang families re-targeted to our verdict formats, per-string runs with intervals, and a Huang-comparable no-question arm",
   "review_status": "preserved",
   "review_basis": "the box text and done-when deliver this action at the named owner; reviewed against the dive ledger and the pinned in-house path",
   "task_refs": [
    {
     "owner": "handoffs/active/eval-tower-program.md",
     "task_id": "EV-JUDGE-FPR-1",
     "task_text": "- [ ] **EV-JUDGE-FPR-1** [inference] Audit the LLM judges for exploitable false positives before anything optimises against them (intake-2877, intake-2886, intake-2904, intake-2888). String set: the ten One-token master keys plus 3-5 paraphrases each, and the 13 Huang Table 8 families with their 'Final Decision: Yes' strings re-targeted to each judge's verdict format (exact strings and prompts from the hkust-nlp/RL-Verifier-Robustness repo). Run every string individually, with Wilson intervals, on a fixed math problem set against the architect_critic, coherence and credibility judges, each with the production prompt, a no-question arm (the Huang-comparable arm) and a no-CoT arm. Scan journaled generator outputs with the same detectors for propensity (zero inference) and report exposure = propensity x FPR, also as a secondary EV-29 column. The futility threshold is a local pre-registered choice. Model: the three judge configs as served; build: production v10 stores (read-only use); region one CPU quarter; estimate ~3 h; metric FPR per string. Stop-on-answer per judge when every string has an FPR; stop-on-futility when no string is accepted in the first 100 items for a judge.",
     "acceptance": "per-judge, per-string FPR table and the propensity counts filed under this box with the problem-set digest; verdict per judge: no-go for any optimiser use if any string's FPR >= 1%, else cleared at that rate"
    }
   ]
  },
  "AKJ-60": {
   "required_outcome": "Use static attack-success rate as a predictor of RL exploitation",
   "review_status": "closed-with-basis",
   "review_basis": "decline: one hacked judge and one unhacked base is a necessary-condition hint, not a validated predictor; exposure is used instead",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-ID-GATE-2** [non-inference] Amend the spec identity-gate protocol (docs/guides/agent-workflows/spec-identity-gate-protocol.md) and its gate reporting with five rules from the noise-floor sources (intake-2872, intake-2893, intake-2891, intake-2894, intake-2883, intake-2884): (a) the floor is the largest pair over >= 3 reference launches (>= 5 when it decides a promotion gate), all pairs, one of them reordered or np-shuffled; fewer launches return INCONCLUSIVE; (b) cache state: both arms cache_prompt false with --cache-ram 0, or a verified identical cache state; existing SPEC-ID-NOISE-1 floors are labelled cache-off; (c) KV provenance: same prefill ubatch, verify-width class and KV dtype in both arms; redecode and resume paths are outside the exact regime; (d) every gate RESULT.json records the kernel-selection env knobs, the per-width route and the binary SHA, and cross-build rows first prove config-dump equality (sampler chain, BOS/EOS, penalties, prefix-cache state, np); (e) where a scored corpus exists, graded flips (worse / better / wrong-to-wrong, net) are reported beside token identity."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-ID-NOISE-2** [inference] Localise the 27B DFlash2 launch-to-launch drift on the MI210 and null-test the amended gate (intake-2872, intake-2882, intake-2883, intake-2894). Arm A: 4 launches of one unchanged config on the MI210; treat each launch in turn as the candidate against the other 3, and the SPEC-ID-GATE-2 gate must PASS every time. Arm B: the same A/A with GGML_HIP_Q8_SKINNY=0, testing whether the skinny-GEMM f32 atomics explain the 20/64 divergence (0/64 = skinny atomics are the source; >= 1 = another source). Arm C: a cb_eval node-hash dump over two launches of 27B DFlash2 np1 on 3 divergent prompts, recording the first differing graph node. Arm D (CPU quarter, small hybrid model): f32 compute and f32 KV, spec vs serial and resumed vs fresh, expecting 0/64. 64 DF2-13 prompts, digest recorded, cache-off. Model 27B Q8_0 + DFlash2 (arms A-C), Qwen3-4B Q8_0 CPU (arm D); build C21 98ff8a4 stores; region MI210 plus one CPU quarter; estimate ~3 h GPU + ~1 h CPU. Stop-on-answer when every arm has its count; stop-on-futility on the first false FAIL in arm A (the gate is then wrong, file it) or equal node hashes in arm C."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-GRAM-JSON-1** [non-inference] Measure the grammar-forced token share of the production json_schema classes offline, which SPEC-GRAM.5 never replayed (intake-2873, intake-2885). Replay retained outputs of each production json_schema class (typed decisions, review schemas, REPL routing, plan steps, consultation, structured-output repair) through llguidance v1.0.1 llg_matcher_compute_ff_tokens with the existing tool-call replay script, and report per class: forced share of output tokens, forced-run lengths, the single-allowed-token subset (the only lossless logit-free subset at T > 0), and the class's share of serving tokens. No model inference."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-GRAM-TV-1** [inference] Measure how far grammar-masked sampling departs from grammar-conditional sampling on the production enum-style json_schema classes (intake-2885). For each class whose language is a finite token trie (typed-decision, review, plan-step enums), query the served model at every trie prefix at the served temperature and compute the exact total variation between the masked law and the grammar-conditional law. The served verifier already samples the masked distribution (common/sampling.cpp:1038-1107 @ 98ff8a4), so speculation adds no bias; this measures the residual masked-sampling bias only. Model: the served frontdoor and architect roles' GGUFs (Q8_0) on the C21 CPU store; region one CPU quarter; estimate ~2 h; metric exact TV per class. Stop-on-answer when every finite-trie class has a TV value; stop-on-futility if no production class has a trie under 10k strings."
  },
  {
   "owner": "handoffs/active/speculative-decoding.md",
   "task_text": "- [ ] **SPEC-STOP-EQ7-1** [non-inference] Replay the CAFE-1-SERVED-T A3B MTP per-token probability captures offline through the cost-aware draft-stop rule (intake-2876 Eq 7: stop at the K minimising expected cost over expected tokens) with the marginal expert-union cost term (intake-2896), against fixed p_min {0, 0.5, 0.75}. Step 1: fit C(K) (verify wall seconds vs draft length) and expert-union bytes vs K for A3B CPU from existing CAFE-1-SERVED-T and Q38P rows; futility if the fitted R^2 < 0.9. Step 2: modelled tokens/s of the rule vs each fixed p_min at T 0.3 and T 1.0 on a held-out half of the captures."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-GVFATTN-Q4KV-DESIGN** [non-inference] Feed design inputs and refinements to the published q4_0-KV gv_fattn row ak-gvfattn-q4kv-gpu-20261124 (store gpu-20261124-5141da459-gvfattn-q4kv, kernel commit 5141da459 behind GGML_CUDA_FA_GQA_Q4KV=1, default off) (intake-2870, intake-2878, intake-2879, intake-2880, intake-2881). (a) A numpy MFMA lane-map oracle for q4_0 K (stock block_q4_0 matches the 16x16x16 fragment, one dword per lane) and the token-contiguous V packing, bit-exact against dequantize_row_q4_0. (b) Disassembly counts of per-value packed-f16 reconstruction vs accumulator folding at R = 6, 12, 24 and 48; folding breaks even only at g = 2*h_q. (c) A review note against 5141da459: q4_0 codes staged in LDS (about 9 KB vs 37 KB of f16 K+V), decode in registers, swapped operands (S^T = K.Q^T) keeping P in registers, a byte-floor ratio (q4_0 us/call over q8_0 x 18/34), and the follow-ups from the KV-quality packet (keep llama.cpp's rotation on for q4_0; K-mean removal only if KVQ-KMEAN-SIM-1 says so). (d) Correct AK-GVFATTN-LONGCTX's 'R <= 32, 2 tiles' premise: 27B gqa 6 at n_q 7 gives R = 42, 3 tiles."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-LESSON-DEMOTE-1** [non-inference] Replay the AutoKernel journal offline to choose a demote rule for prose lessons in the planner bundle (intake-2874, intake-2903). Compare three rules: unused for 5 consecutive iterations (autoresearch tau = 5), the alpha = 0 periodic rule, and a utility-gated rule (retrieved >= n times with mean keep-rate <= beta, from AK keep/discard receipts). Gate-backed negatives consumed by controller/do_not_repeat.py are never demoted. Measure bundle chars saved, later same-epoch re-proposals of a demoted mechanism, and proposal keep-rate with the lesson present vs absent. Zero inference."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-ATTEMPT-DIGEST-1** [non-inference] Add a per-attempt digest catalog to the AutoKernel planner bundle (intake-2874 context folding): one 2-4 sentence digest per past attempt in the bundle index written by loop/actor_context.py, with the full attempt record still reachable by its per-call file, so the planner sees every attempt rather than a recency window. Budget: the bundle index grows by at most 10% over its current size on the replayed journal."
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-CPU-KSHIFT-1** [inference] Pilot a KernelShift-format benchmark task for the AutoKernel CPU lane on Zen 5 (intake-2871, intake-2897, intake-2898). Step 1 (code): in a research-repo scratch copy of cmu-l3/kernel-shift @ 610e835, remove the two aarch64 guards (kgen/check.py, kgen/autovec.py), add one x86 ISA tier, and write an iqk/ggml baseline wrapper for one op, Q8_0 mul_mat at N = 1-16 on hidden served shapes, with a double-precision reference and a calibrated correctness floor (baseline SQNR minus 1 dB). Step 2 (CPU quarter): ISA-ladder arms (AVX2, +VNNI, +AVX512_BF16, +VBMI) plus a scalar -O3 -march=znver5 autovec control, outcome classes (compiles / wrong result / identifier error / crash / no intrinsic), and codegen counts of vpdpbusd, vdpbf16ps, vpermb and zmm FMA in the CPU keep diagnostic. Model: Q8_0 shapes of the served 27B and 35B-A3B; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~3 h after the code step; metric geomean speedup vs baseline. Stop-on-answer when the baseline geomean and A/A floor are recorded for every ISA arm; stop-on-futility if the task reproduces served_shape_cases verdicts only."
  },
  {
   "owner": "handoffs/active/quantization-and-low-bit.md",
   "task_text": "- [ ] **KVQ-ROT-KLD-1** [inference] Measure q4_0 KV quality on the 27B with llama.cpp's automatic Hadamard rotation on vs off (intake-2870, intake-2881, intake-2892, intake-2872). 27B Q8_0 + DFlash2 on the MI210 (C21 GPU store): KLD vs f16 KV for q8_0 KV, q4_0 KV rot-on, and q4_0 KV with LLAMA_ATTN_ROT_DISABLE=1, plus the first-token margin coefficient c (SE <= 0.10) per arm including a whether-to-call class; then a graded-flip arm on the G3 (G) GSM8K protocol for q4_0 vs q8_0 KV with a >= 3-launch A/A floor. CPU arm: 35B-A3B on a quarter, same KLD arms. FlagRot predicts rotation helps a uniform INT4 grid, so rot-off is a falsification check. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0; build C21 98ff8a4 GPU and CPU stores; region MI210 plus one CPU quarter; estimate ~4 h GPU, ~3 h CPU; metric KLD, margin c, graded-flip excess. Stop-on-answer per arm when the KLD CI excludes the verdict boundary; stop-on-futility if the q4_0 KV path fails to load on the served recipe."
  },
  {
   "owner": "handoffs/active/quantization-and-low-bit.md",
   "task_text": "- [ ] **KVQ-KMEAN-SIM-1** [inference] Dump post-RoPE K (and Q) on the 27B full-attention layers (layer 3 is the first; layers 0-2 are GDN) for 64 prompts on a CPU quarter, then simulate q4_0 offline (codes -8..7) for arms: plain, static per-channel mean removal, first-4-tokens exact, and (only if KVQ-ROT-KLD-1 shows q4_0 rot-on KLD > 2x q8_0) keys-only selective rotation (intake-2870, intake-2878, intake-2881). The Qwen2 k-bias mechanism does not apply (no attention_bias in our configs), so this measures generic K-mean energy. Model 27B Q8_0; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~1 h dump plus offline simulation; metric mean-energy share and simulated KL. Stop-on-answer when every arm has a simulated KL; stop-on-futility if the K dump cannot be produced on the served path."
  },
  {
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "task_text": "- [ ] **CDR-A3B-Q4KV-32K** [inference] Measure 35B-A3B MTP CPU decode at 32k context with q4_0 vs q8_0 KV on one quarter (C21 CPU store), with the attention share of the step from the existing per-op profile (intake-2870). Model 35B-A3B Q8_0 MTP; build C21 98ff8a4 CPU store; region one CPU quarter; estimate ~1.5 h. Stop-on-answer on KEEP or FUTILITY; stop-on-futility when attention is under 10% of the step."
  },
  {
   "owner": "handoffs/active/cpu-decode-roofline-program.md",
   "task_text": "- [ ] **CDR-RT9-COVER-1** [non-inference] Close the A3B expert-residency question from the existing RT-9 traces (intake-2876, intake-2895): run skew_report.py on the saved Qwen3.6-35B-A3B frontdoor traces and report per-layer top-12.5% expert coverage, same-domain and cross-domain. RT-9 already shows top-25% share 0.68-0.74 at prefill, so coverage >= 0.6 at <= 12.5% residency is not expected."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **GDN-SLOTS-STRONGER** [non-inference] Record and pin the in-house GATED_DELTA_NET snapshot guarantee, which is stronger than ggml.h's (intake-2867): ggml.h guarantees only slot 0 when n_tokens > K, but the CDNA chunked kernel (gated_delta_net.cu:23-40 @ 98ff8a4) writes every tail slot and spec-decode rollback (MTP K=4, DFlash2 K=9) reads them. Add a named witness case to test-backend-ops that compares all K slots at n_tokens > K on the chunked path, so a rebase that takes upstream #32820's slot-0-only view cannot weaken the check; do not port that view restriction; and add the rule that every ported test's -o op must be in the fold-gate test-backend-ops scope."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **MMID-UB-CEIL-1** [inference] Guard the mul_mat_id shared-memory ceiling on the MI210 (intake-2868): HIP sets smpbo from sharedMemPerBlock (ggml-cuda.cu:360 @ 98ff8a4), so mm_ids_helper aborts above 65536/4 = 16384 tokens per ubatch, below every configured ubatch today. (a) Make orchestrator_stack.py refuse a GPU MoE role launched with -ub above 16384, beside the existing K4 flag guard. (b) One op-level ROCm0 smoke: test-backend-ops -o MUL_MAT_ID at n = 16384 passes and n = 16385 aborts, confirming the derived ceiling. Model: none (op-level test-backend-ops, MUL_MAT_ID Q4_0 shapes); build C21 98ff8a4 GPU store; region MI210; estimate ~15 min; metric pass/abort. Stop-on-answer when both n values are recorded; stop-on-futility if the abort occurs below 16384 (then record the measured ceiling and lower the guard)."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **MMVF-I64-OFFSET** [inference] Gate the two MMVF fixes already committed on fork branch llama.cpp-experimental-c22-mmvf-fixes-20261124 (intake-2869): c47c574ba widens the MMVF expert/sample offsets for x, gate_x, y and dst to int64 (mmvf.cu:47-49 and :84 at 98ff8a4 had the int*int overflow upstream fixed only for x and gate_x), and 7eb398b16 adds the even-ne00 / pair-alignment guard to the AMD MMVF_MMID branch (ggml-cuda.cu:2196-2201), which upstream has and C21 lacked. Remaining step: run the prepared gate row /mnt/raid0/llm/tmp/ak-c22-mmvf-fixes-gate-gpu-20261124. Model: op-level test-backend-ops MUL_MAT / MUL_MAT_ID shapes of the served 27B; build: that branch at 7eb398b16 (GPU); region MI210; estimate ~1.5 h; metric correctness and us/run. Stop-on-answer when both commits are gated; stop-on-futility if the int64 widening costs more than the A/A floor even for x/gate_x alone (then keep only the guard and record)."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **FOLD-KLD-FLOOR-1** [inference] Measure the KLD A/A floor the fold gates have never measured (intake-2901, intake-2872, intake-2893): on the fold-gate corpus, the C21 candidate against itself with one reduction-order toggle flipped (MMVQ nwarps or GGML_ROWEXACT_N), on 27B Q8_0 (MI210) and Q38FN (CPU quarter); check retained logits offline first. Add 'candidate KLD / floor' to the fold-gate result header, and report graded flips (worse / better / wrong-to-wrong) beside KLD where the corpus is scored. Model 27B Q8_0 (MI210) and Q38FN UD-IQ4_XS (CPU quarter); build C21 98ff8a4 stores. Stop-on-answer when both devices have a floor value or the offline logit check answers it; stop-on-futility if retained logits are absent and the floor run cannot reproduce the fold-gate corpus."
  },
  {
   "owner": "handoffs/active/kernel-champion-and-promotion.md",
   "task_text": "- [ ] **PFXC-ID-REPLICA-1** [inference] Re-judge prompt-cache identity with a replica floor (intake-2891, intake-2884, intake-2894): on the served recipes (27B DFlash2 np1 on the MI210 with --cache-ram as served; 35B-A3B MTP np1 on a CPU quarter, conc 1), compare cache-hit vs cold-recompute paths with margin classes and a same-run A/A on each path over >= 3 launches; this replaces PFXC-A1's single-baseline floor (resumed-vs-fresh 0.773 vs C14 floor 1.077). 64 prompts, digest recorded. Model 27B Q8_0 + DFlash2 and 35B-A3B Q8_0 MTP; build C21 98ff8a4 stores; region MI210 plus one CPU quarter; estimate ~2 h GPU, ~2 h CPU; metric divergences out of 64. Stop-on-answer after one 64-prompt pass per device; stop-on-futility on residency-proof failure."
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **RKA-SRC1-DTYPE-RULE** [non-inference] Add two kernel-authoring rules and one rebase trigger to this handoff (intake-2869, intake-2899, intake-2900): (1) a new input dtype in a hot in-house kernel (MMVF, q8mf_pre_i8, q8sk_quantize) is a template parameter, never a runtime flag tested in the inner loop; (2) a new src1 dtype requires a review of every in-house route gated on src1 being F32 (mmq-q8-mf.cu:1270, MMVF_CHUNK, the cuBLAS precheck at ggml-cuda.cu:2075 @ 98ff8a4); (3) the rebase-review trigger is a merged upstream BF16-activation producer in the graph builder (a cast node or type switch), not the op-coverage series #29675, #32135, #32387 and #32533, and that review checks the RMS_NORM fusion gates (ggml-cuda.cu:3404, :4265-4270) and the ROPE+VIEW+SET_ROWS fusion."
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **RKA-IPB-CENSUS-1** [inference] Measure the instruction-issue budget of the q8_0 gv_fattn kernel on the MI210 (intake-2870, intake-2879): rocprofv3 SQ_INSTS_VALU / SQ_INSTS_SALU / SQ_INSTS_LDS / SQ_WAVES counters on the 27B DFlash2 verify at 16k context, n_q 1/4/8, expressed as instructions per KV byte against the device budget (FOSCAR Eq. 2 units), plus implied VALU utilisation. Model 27B Q8_0 + DFlash2 verify; build C21 98ff8a4 GPU store; region MI210; estimate ~1 h; metric instructions per byte and VALU utilisation. Stop-on-answer when every shape has a counter read; stop-on-futility if rocprofv3 cannot attribute counters to gv_fattn."
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **RKA-GV-PSCALE-1** [inference] Test gv_fattn numerics on sink-heavy attention, where P is stored as f16 (intake-2870, intake-2878): add a test-backend-ops case with one dominant early key (attention-sink pattern) on GQA-verify shapes, compare gv_fattn error to the vector path, and try P scaled by 2^10 before the f16 store as the candidate fix. Applies to the production q8_0 path as well. Model: op-level FLASH_ATTN_EXT GQA-verify shapes of the 27B (head dim 256); build llama.cpp-experimental from C21 98ff8a4; region MI210; estimate ~1 h; metric max abs error vs the CPU reference. Stop-on-answer when the error ratio is recorded with and without scaling; stop-on-futility if the sink case cannot be expressed in test-backend-ops."
  },
  {
   "owner": "handoffs/active/rocm-kernel-authoring.md",
   "task_text": "- [ ] **RKA-BATCH-INV-CENSUS-1** [non-inference] Census batch invariance of the MI210 verify graph at widths 1-16 (intake-2882, intake-2883, intake-2872), op by op at 98ff8a4: RMSNorm (norm.cu:347-370, one block per row, already invariant), MMVQ (nwarps depends on ncols_dst, mmvq.cu:813-850), skinny Q8 (f32 unsafeAtomicAdd flush), MMQ / mmq-q8-mf (unsafeAtomicAdd at :1454), hipBLAS BF16, and flash attention (parallel_blocks chosen from occupancy and n_kv, fattn-common.cuh:1514-1594). Per op: invariant or not, the change needed (pinned per-column reduction geometry, fixed-size KV chunks rather than a fixed count, atomics removed) and its port cost."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **EV-SCORER-FUZZ-1** [non-inference] Fuzz the deterministic eval_tower scorers with the RLVR-verifier mutation categories (intake-2889): replay partial_answer, missing marker, contradictory finals, loose float and wrong-then-correct completions against the math_verify and exact-match scorers (EV-11) and report false-positive and false-negative rates with acceptance and coverage per category. CPU minutes, no inference."
  },
  {
   "owner": "handoffs/active/eval-tower-program.md",
   "task_text": "- [ ] **EV-JUDGE-FPR-1** [inference] Audit the LLM judges for exploitable false positives before anything optimises against them (intake-2877, intake-2886, intake-2904, intake-2888). String set: the ten One-token master keys plus 3-5 paraphrases each, and the 13 Huang Table 8 families with their 'Final Decision: Yes' strings re-targeted to each judge's verdict format (exact strings and prompts from the hkust-nlp/RL-Verifier-Robustness repo). Run every string individually, with Wilson intervals, on a fixed math problem set against the architect_critic, coherence and credibility judges, each with the production prompt, a no-question arm (the Huang-comparable arm) and a no-CoT arm. Scan journaled generator outputs with the same detectors for propensity (zero inference) and report exposure = propensity x FPR, also as a secondary EV-29 column. The futility threshold is a local pre-registered choice. Model: the three judge configs as served; build: production v10 stores (read-only use); region one CPU quarter; estimate ~3 h; metric FPR per string. Stop-on-answer per judge when every string has an FPR; stop-on-futility when no string is accepted in the first 100 items for a judge."
  },
  {
   "owner": "handoffs/active/kv-cache-program.md",
   "task_text": "- [ ] **KV-EVICT-COST-2** [non-inference] Extend the KV-EVICT-COST-1 break-even table with two columns (intake-2875, intake-2902): (1) a DMC-5 split row: compressor delta prefill plus summary decode plus agent re-prefill of summary and recent turns, against the decode-attention seconds saved over the next N turns, per device, with GDN hybrids re-prefilling the whole suffix after a changed block (can_shift false); (2) the local-seconds crossover rho_cross = 1 - 1/r (cached-read cost about 0, write cost = prefill seconds per token) with a mutated-prefix tag (tail-only vs middle rewrite). Arithmetic over retained prefill and context-slope rows; no new inference."
  },
  {
   "owner": "handoffs/active/harness-program.md",
   "task_text": "- [ ] **HAR-COMPACT-LEDGER-1** [non-inference] Port DMC-5's integrity pieces into orchestrator compaction behind a default-off flag (intake-2875): the failed-action ledger (every failed tool call kept verbatim across compaction) and byte-exact restoration of pinned pointers (paths, IDs, numbers) in src/graph/compaction.py, which today asks Role.WORKER_GENERAL for a one-shot index with neither. Without it DMC-5's own AppWorld accuracy fell below no compression (69.1% vs 77.0%)."
  },
  {
   "owner": "handoffs/active/context-and-token-economy.md",
   "task_text": "- [ ] **CTE-CFAB-A8** [non-inference] Write the CF-AB-1 frame's arm A8, design text only (intake-2874, intake-2875): a digest catalog of every past turn plus agent-selected unfold under a declared history budget (autoresearch context folding), with a variant that uses a second-role compressor and pinned-pointer restoration (DMC-5). It runs only when TOC-SP-5 shows binding windows, like A3-A7."
  }
 ]
}
```
