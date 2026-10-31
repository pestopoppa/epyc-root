# Stage-3 plan — ws58 research intake 2026-10-31 (intake-2545..2602)

Status: PROPOSED, awaiting operator approval. Nothing below is applied. Stage 4 is applied by the owning session after approval; no index row is added or changed by this plan.

Session: `intake-ws58-20261031`. Lane worktree `/mnt/raid0/llm/worktrees/intake-ws58-20261031`. Dive artifacts `/mnt/raid0/llm/tmp/dive-ws58-20261031/`.

## Scope and process

- 23 operator URLs plus 9 Stage-1 expansions (intake-2545..2576); every medium-or-higher source dived in wave 1 (29 entries).
- Stage-2b waves 2-4 ingested and dived 26 surfaced sources (intake-2577..2602). Four of six permitted waves were used; the remaining surfaced items were declined with reasons recorded on the bearing entries.
- Verification: 57 dive-verified, 2 dive-overturned (intake-2553: d1-Omni does have a llama.cpp path; intake-2594: the Q8_0 collapse was a Metal bug, not quantization). Every anchor was re-found mechanically and checked by an independent second reader; 7 objections were resolved by dropping or narrowing anchors.
- Stage-1 defect caught: Stage-1 fetchers attached 7 cross-reference arXiv ids that were not in the fetched sources; all were removed before persisting.

## Top findings

1. **Live correctness exposure.** The :8070 frontdoor (Qwen3.6-35B-A3B, draft-MTP, np 4) and :8083 (27B DFlash2, np 4) run speculative decoding at np>1 with no token-identity record. llama.cpp #28286 reports cross-slot contamination with MTP at np>1 on Qwen3.8-Flash-Next and closed without a fix; #28019 adds an untested slot-reuse condition. Our tree has the same unwritten-snapshot-slot code shape. (P1)
2. **DCOCO is not new to us.** DFlash2 already ships a learned top-16, rank-256 candidate selector with a prefix-first walk. DCOCO's headline gain mostly comes from joint drafter retraining (+4.4% when the drafter is frozen). What matters is the remaining headroom, which one offline dump can measure. (P2)
3. **AK gate blind spots confirmed in code.** No race detector, no edge-value inputs, NMSE-only oracle. The AI-compiler papers show that formal verification costs speed and covers few hot kernels, so cheap planted-control checks and enumeration are the practical path. (P3)
4. **Upstream llama.cpp now serves end-to-end audio models.** LFM3-Audio/Omni and Voxtral Realtime run through `mtmd_audio_stream` and `/v1/realtime`, about 1,650 builds past v10. Only vendor numbers exist, so a scratch build and STT arms on our pinned clips decide. (P4)
5. **d1 decision models have a llama.cpp path** through `/v1/systemone`. They fit TD-23's missing local backend, but probabilities move with batch cut and build, so parity and batch-invariance gates come first. (P5)
6. **Soft-MTP on a frozen trunk is direct forward KL.** The decision it changes is capture-time: add the target final-hidden tap before any drafter feature dump. ThinkingCap Flash-Next adds nothing while `architect_general` runs with thinking off, and its MTP head was never the Axis-E blocker. (P2, M6, K1)

## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Temp-0 cross-slot token identity on the np>1 speculative roles, recurrent-state hash conformance, acceptance-collapse canary, multi-prefill promotion arm | handoffs/active/dflash2-block-drafter-experimental-build.md |
| P2 | DFlash2 lattice-headroom and point-mass probes; drafter-training data contract | handoffs/active/dflash2-block-drafter-experimental-build.md |
| P3 | AK correctness gate: edge-value families, worst-error bound, quant-decode enumeration, GDN oracle, race sensitivity, ISA archive, counter-grounded planning | handoffs/active/autokernel-all-devices-all-dimensions.md |
| P4 | Scratch upstream audio build; LFM3-Audio and Voxtral STT arms; /v1/realtime latency and turn contract | handoffs/active/conversation-stack.md |
| P5 | d1-2B as TD-23 local decision backend behind parity and batch-invariance gates; GGUF pin in the calibration receipt | handoffs/active/typed-decision-plane.md |
| P6 | Zero-inference agent-loop screens: fold replay, advertised tool surface, old tool-result context share | handoffs/active/routing-intelligence.md |
| P7 | Independent checker for the vidya gate certificate | handoffs/active/vidya-belief-substrate-program.md |
| K1 | Speculative-decoding knowledge notes (DFlash2 already has a learned selector; drafter recipes; Axis-E head on disk) | handoffs/active/dflash2-block-drafter-experimental-build.md |
| K2 | Architecture and roofline notes (looped models, GDN beta cap, stale llama.cpp-compatibility note) | handoffs/active/cpu-decode-roofline-program.md |
| K3 | KV editing and agent-loop design notes (history-keyed reuse, C2C mapping, single-loop caveat) | handoffs/active/kv-prefix-fork-and-paged-attention.md |
| K4 | Speech and decision-backend notes (Parakeet/transcribe.cpp already owned; realtime turn contract; d1 API subset) | handoffs/active/conversation-stack.md |
| K5 | Kernel-authoring notes (prompt-leak guard; agent-harness token cost) | handoffs/active/agentic-rocm-kernel-authoring.md |
| M1 | Speculative-decoding triggers (trained selector port, Domino head, frozen-trunk objective probe, MTP head realign, snapshot patch, thinking-repetition guard, NCM drafter) | handoffs/active/dflash2-block-drafter-experimental-build.md |
| M2 | Looped-model triggers (PLT port or timing; Ouro probe) | handoffs/active/cpu-decode-roofline-program.md |
| M3 | KV drop and cross-model cache triggers (gated on the context-share screen; fusers for served pairs) | handoffs/active/kv-prefix-fork-and-paged-attention.md |
| M4 | Speech and decision-model triggers (LFM3 as bake-off challenger, realtime adapter, Dessa, spoken-state decider, generic readout, hybrid prefix fix) | handoffs/active/conversation-stack.md |
| M5 | Kernel-verification triggers (gfx90a race executor, ISA-level AI lowering, failure-to-rule loop) | handoffs/active/rocm-verify-profile-backend.md |
| M6 | ThinkingCap Flash-Next A/B trigger (only if thinking is enabled for a Flash-Next role) | handoffs/active/architect-model-selection-bench.md |

Ordering and concurrency: P1-P7 are independent and can run in parallel. Within P1, the rollback test inside DF2-12.1 runs first; G2-CONC.MP applies at the next promotion. Within P2, DF2-LAT and DF2-PM share one experimental build. P4 and P5 each use their own scratch upstream build. P6 and P7 are zero-inference. Seven packets survive compression because each has a different owner, consumer and gate; merging them would only bundle unrelated work.

Minimum-rigor controls. Empirical items (DF2-12.1, DF2-LAT, DF2-PM, RVP-RACE-1, RVP-CTR-1, CS-8.STT8, CS-8.RT1, TD-23.D1, RI-25, CF-AKV-0) each name in their task text a frozen input manifest, the incumbent baseline, per-item raw outputs, a holdout or repeat (dev/holdout prompts, a second seed, or interleaved pairs), the full denominator, and a predeclared decision rule. Deterministic items (KPF-RS-1, SPEC-CANARY.1, G2-CONC.MP, AKX-ALL-31.EDGE/b/c, C5-ISA-1, DF2-DRAFTER-CAPABILITY.OBJ, TD-18.1, UFH14-TOOLS-1, VB-CERT-1) have no holdout. Each instead names a planted mutation or forged case that must fail, plus a conformance check against the incumbent.

## Operator decisions

- **D1 (MEM-3, decline to confirm).** Decline an in-weights calculator (Qwenputer-style compiled layers) for serving. It costs about 1.6-2x weight bytes per token on our bandwidth-bound CPU, and the Python-tool arm matches it. The source stays as knowledge. Recommendation: confirm the decline.
- **D2 (P4 build footprint).** P4 and P5 each need a scratch upstream llama.cpp build on llama.cpp-experimental, isolated with its own LD_LIBRARY_PATH. These are measurement instruments, not a port onto v10. Recommendation: approve as instruments. Any adoption goes through the normal four-step version-past-production path.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| AGENT-1 | intake-2565 Stage-2 dive w1 ledger | Run the fold article procedure as a zero-inference REPLAY over existing delegation records: for each delegate() role (worker_math, worker_general, worker_summarize, worker_vision, coder_escalation) compute from _delegations artifacts / delegation reports the ... | P6 / RI-25 |
| AGENT-10 | intake-2562 Stage-2 dive w1 ledger | Use Resin docs/cache-pool.md + architecture.md Prefix reuse as design reference for hybrid prefix reuse: its snapshots are taken at an alignment equal to the LCM of all group block sizes and restore attention, SWA and recurrent state at the same boundary, ... | K3 |
| AGENT-11 | intake-2562 Stage-2 dive w1 ledger | Decline engine/runner split as an adoption target: there is no CPU or ROCm runner, and production serving is llama.cpp (frozen v10). Treat the split as vocabulary only. | decline: the Resin engine/runner split has no CPU or ROCm runner and production serving is llama.cpp. |
| AGENT-12 | intake-2553 Stage-2 dive w1 ledger | Screen d1-Omni-2B-GGUF (Q8_0, 1.85 GB) and d1-2B-GGUF as local typed-decision backends on a separate, scratch-built upstream llama-server (b11960+ in its own build dir; production tree untouched). Probe: replay a frozen set of already-routed orchestrator ... | P5 / TD-23.D1 |
| AGENT-13 | intake-2553 Stage-2 dive w1 ledger | Speech turn-taking decider test (only after human-recorded strata exist): d1-Omni-2B reads a short audio window and answers noul/score questions (end of turn? backchannel needed?) on the CS-45 corpus; compare against the CS-22 controller policy and the D1 ... | M4 |
| AGENT-14 | intake-2553 Stage-2 dive w1 ledger | Read LFM Open License v1.0 and the Open d1 blog before any use beyond a screen (licence is not Apache/MIT; sourcing policy is open-source only). | P5 / TD-23.D1 |
| AGENT-2 | intake-2565 Stage-2 dive w1 ledger | Count and cap the model-visible tool surface: REPL exposes ~55 globals (peek, grep, delegate, escalate, run_shell, registry_*, benchmark_*, ...) in environment.py _build_globals while tool_registry.yaml holds 55 further tools (TOOL/CALL/list_tools = already ... | P6 / UFH14-TOOLS-1 |
| AGENT-3 | intake-2565 Stage-2 dive w1 ledger | Add a per-fold eval: before folding any worker role into skills, require a frozen end-to-end set covering every production chain (architect -> coder_escalation, frontdoor -> worker_*) and every must-not-break rule, repeated >=2 times, reporting flipped tasks. ... | M3 |
| AGENT-4 | intake-2565 Stage-2 dive w1 ledger | Do NOT adopt the article single-loop thesis for our CPU stack without measurement: the article premise is frontier models with thinking on; our workers are local quantised Qwen3.x on a BW-bound CPU where a separate small-context worker call is cheaper per ... | K3 |
| AGENT-5 | intake-2559, intake-2576 Stage-2 dive w1 ledger | Bounded offline probe on CPU (HF transformers, no llama.cpp): with released nics-efc/C2C_Fuser qwen3_8b+qwen2.5_7b fuser, run n=200 frozen items from a MC set the stack already scores (e.g. MMLU-Redux subset used in canonical suites) in 4 arms: Receiver-only, ... | M3 |
| AGENT-6 | intake-2559, intake-2576 Stage-2 dive w1 ledger | Design note (no compute): map C2C onto llama.cpp. Feasible path = out-of-process fuser. Receiver and Sharer each prefill the same prompt; read per-layer K/V from each via llama_state_seq_get_data (include/llama.h:881) or /slots/{id}?action=save ... | K3 |
| AGENT-7 | intake-2559 Stage-2 dive w1 ledger | Role-pair candidate list, ranked: (1) architect_critic / coder_escalation (Qwen3.8-27B Q8_0, dense KV-densest per model_registry.yaml:541) as SHARER -> worker_general/worker_summarize (Qwen3.6-35B-A3B MoE, receiver; must check whether its layers are all full ... | M3 |
| AGENT-8 | intake-2576 Stage-2 dive w1 ledger | Read the thu-nics AKV repo (cache engineering for agents, follow-up to C2C, Apache-2.0, pushed 2026-10-21) before sizing any pair-training, since it may cover agent KV reuse without a per-pair trained fuser. | K3 |
| AGENT-9 | intake-2562 Stage-2 dive w1 ledger | Copy the measurement-discipline text, not code, into the AK actor context: (a) record cache/graph/placement state and compare on the same allocation, (b) locate the limiting interval from a trace BEFORE kernel edits, (c) report the spread and do not call ... | decline: the Resin measurement-discipline text is weaker than the Annex K protocol the loop already follows. |
| KERN-1 | intake-2570, intake-2555 Stage-2 dive w1 ledger | Race-sensitivity mutation control for the GPU correctness gate. In a llama.cpp-experimental worktree, build 3 seeded-race HIP mutants, each deleting one __syncthreads/barrier: MMQ tile load, MMVQ partial-sum reduction, FA tile softmax. Run the existing AK ... | P3 / RVP-RACE-1 |
| KERN-10 | intake-2570 Stage-2 dive w1 ledger | Wire a CPU race detector for routes touching threading. Build a TSAN test-backend-ops (CPU), using LLVM libomp with Archer annotations because production uses OpenMP; GGML_OPENMP=OFF would test a different threading path. Run it on the v10 anchor first. | P3 / RVP-RACE-1 |
| KERN-11 | intake-2570, intake-2557 Stage-2 dive w1 ledger | Do not adopt upstream Volta or the Blackwell fork directly. Both are PTX/NVIDIA-only, and this host has no NVIDIA GPU. Reuse only the race model (KERN-2) and the scaffold code. | decline: upstream Volta and its Blackwell fork are PTX-only and the host has no NVIDIA GPU; the race model transfers through the race trigger instead. |
| KERN-2 | intake-2557, intake-2570 Stage-2 dive w1 ledger | Build a race-only symbolic executor for gfx90a AMDGCN: parse hipcc --save-temps asm, concrete thread/workgroup indices and launch params, per-byte LDS reader/writer sets between s_barrier, lgkmcnt/vmcnt waits as completion points, exec-mask lanes, wave64. ... | M5 |
| KERN-3 | intake-2555 Stage-2 dive w1 ledger | Add structured edge-value input families to the AK op suite beside the AK_SENS scale transforms. Families: f16-range near-max (overflow), subnormal-scale (underflow), cancellation pairs within reduction rows, softmax rows that are all-equal or contain -inf, ... | P3 / AKX-ALL-31.EDGE |
| KERN-4 | intake-2555, intake-2570 Stage-2 dive w1 ledger | Exhaustive bit-level decode check per served quant type (Q4_K, Q6_K, IQ2_*, IQ3_*, IQ4_XS, MXFP4). Enumerate the full per-element code space (quant codes x sub-block scale/min codes) at d/dmin in {0, subnormal, 1, f16 max}. Compare the candidate CPU (AVX-512) ... | P3 / AKX-ALL-31.QDEC |
| KERN-5 | intake-2556 Stage-2 dive w1 ledger | Add a per-element worst-error bound next to NMSE on the GPU served-shape case set. Calibrate the anchor's max-abs error per (op, type, shape) over 5 seeds and gate on k x anchor, the way the CPU_REPACK oracle already does. | P3 / AKX-ALL-31.EDGE |
| KERN-6 | intake-2555, intake-2556 Stage-2 dive w1 ledger | Counter-grounded planner signals. For the top-1 hotspot kernel of each GPU screen, capture a fixed, declared counter subset via rocprofv2 (from the proven 465-counter taxonomy). Attach it to the hotspots rows. Adopt TAIC's rule that each hypothesis cites a ... | P3 / RVP-CTR-1 |
| KERN-7 | intake-2555, intake-2556 Stage-2 dive w1 ledger | Archive the hipcc AMDGCN ISA (--save-temps .s, or llvm-objdump of the code object) of the touched kernels into every AK GPU candidate record, next to the source diff and the hotspots table. | P3 / C5-ISA-1 |
| KERN-8 | intake-2555, intake-2556 Stage-2 dive w1 ledger | GCN-Gym probe of AI lowering on gfx90a. Build a standalone harness that assembles LLM-patched AMDGCN for one compute-bound kernel (MMQ Q4_K prefill tile or FA at long context) with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a, loads it via hipModuleLoad and ... | M5 |
| KERN-9 | intake-2556 Stage-2 dive w1 ledger | Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population. | K5 |
| LOOP-1 | intake-2547, intake-2571 Stage-2 dive w1 ledger | Add a knowledge note to the INF-70 roofline program: weight-reuse architectures. Sequential looping multiplies weight bytes per token by L, and with 32 MiB L3 per CCX (384 MiB total) a block above ~32 MiB per CCX cannot be cache-reused (e.g. a 7B 14-layer PLT ... | K2 |
| LOOP-2 | intake-2571, intake-2547 Stage-2 dive w1 ledger | Ingest and dive LoopCoder-v2 (arXiv 2606.18023): released 7B PLT 2-loop coder (Apache-2.0, HF Multilingual-Multimodal-NLP/LoopCoder-V2, 14 layers, hidden 5120, 8 KV heads) is the first PLT checkpoint we can actually run; card claims SWE-bench Verified 43.0 -> ... | K2 |
| LOOP-3 | intake-2547 Stage-2 dive w1 ledger | Correct the stale gate: Ouro now has a community llama.cpp port (BrandeisPatrick/loop-transformer, ouro arch, 324 added lines, PR ggml-org/llama.cpp#29823, GGUFs for Ouro 1.4B/2.6B +Thinking) built on upstream looped-model machinery merged for Nanbeige4.2 (PR ... | K2 |
| LOOP-4 | intake-2547, intake-2551 Stage-2 dive w1 ledger | Bounded CPU probe on a llama.cpp-experimental branch with the Ouro port: Ouro-1.4B Q4_K_M (854 MB per card), llama-bench tg at num_loops 1/2/4 via --override-kv, reporting achieved GB/s counting bytes once per loop against the C0 153 GB/s ceiling. This ... | M2 |
| LOOP-5 | intake-2551 Stage-2 dive w1 ledger | Record in reasoning-compression.md only: looped MoE R=5 at 0.3B-1.3B reaches reasoning parity with 0.6B-2.9B at 1.8x training-compute-defined inference compute while trailing Overall 46.9 vs 50.2; no latency/bytes measured; no checkpoint released in the text. | K2 |
| LOOP-6 | intake-2546, intake-2568 Stage-2 dive w1 ledger | Monitor NCM as a drafter source: trigger = a released NCM-style generator with a general-text tokenizer sharing a served model vocabulary, or any measured acceptance rate against an AR target. Do not build now: released checkpoints are per-dataset ~100M-725M ... | M1 |
| MEM-1 | intake-2550, intake-2574 Stage-2 dive w1 ledger | Add a deterministic one-hot RAM oracle case to the GATED_DELTA_NET tests of an EXPERIMENTAL champion-derived llama.cpp branch (tests/test-backend-ops.cpp test_gated_delta_net family, or a sibling test-gdn-ram): alpha=1 (g=0), beta=1, one-hot k and q, ... | P3 / AKX-ALL-31.GDN |
| MEM-2 | intake-2574 Stage-2 dive w1 ledger | Add a state-level conformance check to the hybrid checkpoint/fork path: after a restore (common_prompt_checkpoint load_tgt, or KPF fork from a checkpoint) serialise the recurrent half of source and destination with llama_state_seq_get_data_ext(PARTIAL_ONLY) ... | P1 / KPF-RS-1 |
| MEM-3 | intake-2550, intake-2574 Stage-2 dive w1 ledger | Do not pursue an in-weights calculator (compiled RISC-V/CHIP-8 layers) for the serving stack. Flag for operator review per the research-intake rule rather than closing silently. | decline: an in-weights calculator costs about 1.6 to 2 times the weight bytes per token on a bandwidth-bound host and the tool arm already matches it; operator confirmation requested. |
| MEM-4 | intake-2558 Stage-2 dive w1 ledger | Write scripts/vidya/cert_check.py: a standalone verifier for the gate's epyc.vidya/certificate/v1, sharing NO imports with fold.py, gate.py or lattice.py. It reads the ledger JSONL and the ratified policy file directly, re-derives pro/con grade dominance and ... | P7 / VB-CERT-1 |
| MEM-5 | intake-2558 Stage-2 dive w1 ledger | No certificate/checker layer for scripts/handoffs/index_state.py or registry consistency checks. | decline: the handoff index check already re-derives and compares on every run, so a certificate layer adds nothing. |
| MEM-6 | intake-2558 Stage-2 dive w1 ledger | When writing MEM-4, make the checker read and compare certificate.frontier and as_of explicitly and record in the certificate's proves-field that a certificate binds to a frontier, not to the truth of the world. | P7 / VB-CERT-1 |
| MTP-1 | intake-2548, intake-2549 Stage-2 dive w1 ledger | Amend the DF2-DRAFTER-CAPABILITY trainer and data contract (the INF-62 record contract inherited from the cancelled DF2-QWOPUS) so the default objective is forward-KL self-distillation to the target's own teacher-forced NTP distribution rather than hard ... | P2 / DF2-DRAFTER-CAPABILITY.OBJ |
| MTP-2 | intake-2548, intake-2549 Stage-2 dive w1 ledger | Bounded frozen-trunk probe on the Soft-MTP repo (MI210, ROCm torch, <=4 GPU-h, no llama.cpp). Take the released 167M (or 332M) NTP checkpoint, set freeze_backbone=true, and train fresh K=3 DeepSeek-style heads under two arms with identical data order, seed, ... | M1 |
| MTP-3 | intake-2548 Stage-2 dive w1 ledger | No change to Axis E. Restoring the Qwen3.8-Flash-Next MTP head loads the published unsloth shared-Q8_0 head (no training), so the MTP-objective choice does not touch it. | K1 |
| MTP-4 | intake-2548 Stage-2 dive w1 ledger | Record a trigger on the speculative-decoding refresh. If a served fine-tune ships with a stock (base-co-trained) MTP head, as already observed for ThinkingCap and Qwopus, the remedy is head-only re-alignment on the frozen fine-tuned trunk against its own NTP ... | M1 |
| MTP-5 | intake-2548 Stage-2 dive w1 ledger | Decline adopting Soft-MTP as a pretraining objective. | decline: Soft-MTP as a pretraining objective needs trunk training, which this stack does not do. |
| SPEC-1 | intake-2561, intake-2560 Stage-2 dive w1 ledger | DF2-LAT zero-training lattice-headroom probe. (i) Experimental build from the current champion tip, env-gated and off by default: append the 16 unary draft logits to each packed DFlash2 lattice row (src/models/dflash.cpp build_post_sampling; row is K+K*K=272 ... | P2 / DF2-LAT |
| SPEC-2 | intake-2561 Stage-2 dive w1 ledger | DF2-PM point-mass proposal screen at production temperature. Behind an env knob in the experimental build, the DFlash2 temp>0 branch takes the argmax selector walk instead of sampling softmax(scores/T), and emits dist {id, prob 1.0} per slot. The existing ... | P2 / DF2-PM |
| SPEC-3 | intake-2561, intake-2560 Stage-2 dive w1 ledger | Port the DCOCO head to llama.cpp as a replacement DFlash2 selector, and train it on the frozen DFlash2 backbone. Gated on SPEC-1 PROMOTE. Port: converter keys/tensors for cand_proj, ctx_h_proj, cand_ctx_proj + LN, pair_proj and the 386->256->1 MLP (~100 LOC ... | M1 |
| SPEC-4 | intake-2561, intake-2560, intake-2569 Stage-2 dive w1 ledger | Prepare a text update (owning session applies) to the LiLiCorr monitor paragraph: name DCOCO (intake-2561#record) and Domino (intake-2569#record) as the same correction family; record that DFlash2 already ships a learned K=16 rank-256 selector lattice with a ... | K1 |
| SPEC-5 | intake-2569 Stage-2 dive w1 ledger | Domino-style GRU + full-vocab low-rank correction head on the DFlash2 drafter: no work now. It needs full drafter co-training with the curriculum, and its sequential head adds a 256x248320 logit-residual projection per position on the critical path. Revisit ... | M1 |
| SPEC-6 | intake-2561, intake-2569 Stage-2 dive w1 ledger | CPU: no separate action. The 27B DFlash2 path is served on the MI210 only, and CPU speculative work for Flash-Next is MTP (Axis E). If SPEC-3 is ever built, its graph ops are backend-agnostic and must pass CPU no-regression in the four-step workflow. | K1 |
| SPEC2-1 | intake-2577 Stage-2 dive w2 ledger | Add a per-request MTP health canary to the Flash-Next serving gate: flag any request with >=64 drafted tokens and zero accepted, or a repeated n-gram window in the generated tail (reuse coherence_gate tiers 0-2), and log per-request accepted/drafted from ... | P1 / SPEC-CANARY.1 |
| SPEC2-2 | intake-2577 Stage-2 dive w2 ledger | Extend G2-CONC with a simultaneous-multi-prefill probe: c in {2,3,5} identical-length prompts differing by a salt, issued at the same instant, temp 0, ignore-eos 128 tokens, MTP on vs MTP off, compare every request token-for-token to its solo -np 1 output; ... | P1 / G2-CONC.MP |
| SPEC2-3 | intake-2577 Stage-2 dive w2 ledger | Note thinking-mode default sampling repetition risk: issue says model card recommends presence_penalty 0-2 and attributes loops to degenerate state amplified by temp 1.0 / top_k 20 / top_p 0.95; check the Flash-Next architect_general request sampler against ... | M1 |
| SPEC2-4 | intake-2578 Stage-2 dive w2 ledger | Add to DF2-DRAFTER-CAPABILITY the Nemotron Sec 3.4 head/drafter fine-tune recipe as an option: freeze target, sample hidden states from earlier draft steps, forward-KL T=2 to target logits on target on-policy rollouts at temp 1 (reference scale: 12K steps, bs ... | K1 |
| SPEC2-5 | intake-1724 Stage-2 dive w2 ledger | Answer only (no entry): the z-lab card text does not say how the DFlash2 selector (top-16, rank-256 transition score) was trained, and reports no tau gain over DFlash 1 for Qwen3.8-27B. The inco.ai blog (sha256-12 99dc56f49911) gives the selector score ... | K1 |
| SPEECH-1 | intake-2552, intake-2554, intake-2575 Stage-2 dive w1 ledger | Bounded probe LFM3-1: build an experimental llama.cpp tree (fresh v10 + upstream b11960 audio path: PRs 31252, 30629, 30636, 31257, 31269, 31287, 31386) on CPU only first; run LFM3-Audio-2B Q8_0 ASR over the 40 pinned FLEURS clips (en/it/de/fr x10) and ... | P4 / CS-8.STT8 |
| SPEECH-2 | intake-2552, intake-2554, intake-2575 Stage-2 dive w1 ledger | Add LFM3-Audio-2B/Omni-2B as a third challenger in the CS-8 G1/G3/G4 interlocutor bake-off: G1 en/it TTS intelligibility via llama-tts (note voice chat is English-only per card, so Italian only for TTS/ASR), G3 tool-call slot quality from speech, G4 ... | M4 |
| SPEECH-3 | intake-2575 Stage-2 dive w1 ledger | Estimate and record forward-port cost: experimental branch from current production-consolidated-v10, merge/cherry-pick the 7 LFM3 audio PRs plus their upstream prerequisites (b10303..b11960 is 1657 builds; PR 31257 alone +2721/-160 over 31 files, 30629 +998, ... | P4 / CS-8.STT8 |
| SPEECH-4 | intake-2575 Stage-2 dive w1 ledger | Reuse the upstream /v1/realtime (OpenAI-compatible) and Voxtral-Realtime support as a CS-20 backend interface option: write a realtime client adapter in the voice controller that speaks /v1/realtime beside the whisper :9000 / qwentts :9002 cascade. | M4 |
| SPEECH-5 | intake-2573 Stage-2 dive w1 ledger | No new STT action. Hex confirms the transcribe.cpp Parakeet Unified streaming path (Vulkan GPU only). Parakeet streaming vs whisper.cpp is already a measured-pending candidate: CS-8.STT0 40/40 CPU==GPU identity done, transcribe.cpp CPU 40-clip run 37/40 ... | K4 |
| SPEECH-6 | intake-2573 Stage-2 dive w1 ledger | Add Parakeet Unified English (streaming, lookahead variants) as a named arm check in CS-8.STT5 if not already present, noting hex pins fork rev 7045d1c0 (transcribe.cpp 0.4.1) while our build pins db678a03; record both pins. | K4 |
| SPEECH-7 | intake-2564 Stage-2 dive w1 ledger | Monitor Dessa for paper, weights or API; trigger = any released checkpoint or paper with benchmark numbers, then fold into the M8 full-duplex reference slot check (language gate D2 likely fails if English-only). | M4 |
| TCAP-1 | intake-2567, intake-2572 Stage-2 dive w1 ledger | Bounded A/B: base UD-IQ4_XS (current :8074 file) vs bottlecapai ThinkingCap IQ4_XS GGUF, llama-server, same recipe qwen38-flash-next-cpu-mtp, enable_thinking=true on /v1/chat/completions, frozen 40-60 prompt set (arch/plan-critique + reasoning, AIME-style, ... | M6 |
| TCAP-2 | intake-2572 Stage-2 dive w1 ledger | Record that INF-70 Axis-E "MTP needs FP8 re-download" is obsolete: head already on disk (mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf, 2.79 GB, 2026-09-02); no ThinkingCap download is needed for MTP | K1 |
| TCAP-3 | intake-2572 Stage-2 dive w1 ledger | If A/B runs, add arm B2 = ThinkingCap trunk + our unsloth shared-Q8_0 draft file vs embedded head, measure alpha for both | M6 |
| TCAP-4 | intake-2567 Stage-2 dive w1 ledger | Do not pursue the vendor PRO tier or method discovery | decline: the vendor PRO tier is closed and no method is disclosed. |
| W2KERN-1 | intake-2588 Stage-2 dive w2 ledger | Add an instruction-executed gate to the AMD kernel-authoring path: when a candidate claims a mechanism (MFMA use, LDS staging, buffer/global load width), require a rocprof instruction-mix counter or ISA-disassembly execution check on the real workload before ... | P3 / C5-ISA-1 |
| W2KERN-2 | intake-2588 Stage-2 dive w2 ledger | Compare AK candidate generation as plain multi-turn refinement vs agent-harness mode on token cost per accepted keep (PTXBench: agent harness cost 3.3-5.1x tokens and was worse on attention). Use existing AK run logs only; no new compute. | K5 |
| W2KERN-3 | intake-2589, intake-2588 Stage-2 dive w2 ledger | Close the verified AK gate gaps (no race detector, race_detector_id=None; no edge-value inputs; NMSE-only oracle) with a CAKE-style pre-GPU static filter tier: run the cheapest hazard/legality checks (LDS barrier ordering, wave64/exec-mask hazards from the ... | P3 / AKX-ALL-31.EDGE |
| W2KERN-4 | intake-2589 Stage-2 dive w2 ledger | Failure-to-rule loop for AK: after each rejected batch, classify the failure reason and, when a class recurs (>=3), have an agent propose a permanent static check or oracle input, merged only under corpus tests of all prior keeps (CAKE Sec 3.2). | M5 |
| W2KERN-5 | intake-2590 Stage-2 dive w2 ledger | Bounded probe: tool-result KV drop+shift on a pure full-attention role in llama-server, using existing llama_memory_seq_rm + seq_add (as in the streaming-llm / context-shift path), on a recorded orchestrator agent trace. Measure (a) tokens re-prefilled per ... | M3 |
| W2KERN-6 | intake-2590 Stage-2 dive w2 ledger | Record the history-dependence correctness rule for any future KV-editing serving feature: a slot/prefix index keyed only by token prefix (src/inference/prefix_index.py) must also key on the drop/shift operation history, or mark the slot unmatchable after an ... | K3 |
| W2KERN-7 | intake-2590 Stage-2 dive w2 ledger | Decline porting AKV server (SGLang, Rust build, softmax-attention only) as a serving path; keep as design reference only. Hybrid/linear-attention models (our main Qwen line) are unsupported by the authors and by llama.cpp seq ops. | decline: the AKV server is SGLang and softmax-only; it stays a design reference. |
| W2LOOP-1 | intake-2585, intake-2586 Stage-2 dive w2 ledger | On an experimental llama.cpp branch freshly cut from production v10, cherry #25994 plus #29823 (about 590 added lines) and measure Ouro-1.4B Q8_0/Q4_K_M at --override-kv ouro.num_loops=int:1/2/4 on EPYC CPU (one quarter and full socket): tok/s, achieved GB/s ... | M2 |
| W2LOOP-2 | intake-2584 Stage-2 dive w2 ledger | Monitor triggers: (a) llama.cpp or vLLM PR adding iquestpltcoder / PLT, (b) an independent replication of LoopCoder-v2 R=2 SWE-bench Verified, (c) a timing number for PLT decode. Any one fires ingest-and-dive on it. | M2 |
| W2LOOP-3 | intake-2587 Stage-2 dive w2 ledger | Knowledge-only: record that our GDN graph hard-caps beta at 1 (src/models/qwen3next.cpp:417 ggml_sigmoid) matching the Qwen3.5 control that failed to generalise hidden tracking; no probe. | K2 |
| W2LOOP-4 | intake-2585, intake-2586 Stage-2 dive w2 ledger | Correct the stale note in gpu-acceleration-path.md ~line 248 (intake-332 "Not llama.cpp compatible") to say nanbeige looped arch merged 2026-07-27 and Ouro is PR #29823 open; owning session applies. | K2 |
| W2SP-1 | intake-2579, intake-2575 Stage-2 dive w2 ledger | Build upstream master (or tag b11960+) as a SCRATCH llama-server on llama.cpp-experimental from fresh production; run examples/realtime_client.py with LFM3-Audio-2B Q8_0 and Q4_0 on the EPYC CPU and MI210 and record first-output-after-end-of-input, with a ... | P4 / CS-8.RT1 |
| W2SP-2 | intake-2579 Stage-2 dive w2 ledger | Specify the server-turn contract in CS-22: because /v1/realtime has turn_detection null, our controller (VAD + CS-47 semantic gate) must send commit/response.create/response.cancel; add this as the integration seam in CS-22.A1 rather than waiting on a server ... | K4 |
| W2SP-3 | intake-2582, intake-2581, intake-2583 Stage-2 dive w2 ledger | TD-23 screen: d1-2B-GGUF Q8_0 via /v1/systemone (scratch upstream build, CPU quarter or MI210 window) versus the constrained incumbent readout, on a frozen, row-pinned labelled routing set (the TD-11 / CJ-15 sealed workload; labels from the routing-replay ... | P5 / TD-23.D1 |
| W2SP-4 | intake-2582 Stage-2 dive w2 ledger | Record in TD-23 candidate list that d1-2B/3B are VL models with LFM Open License v1.0 and that the llama.cpp path supports noul/choice/score only; routing questions are choice+score so the subset is sufficient. | K4 |
| W2SP-5 | intake-2581 Stage-2 dive w2 ledger | Spoken-state decision probe (turn completeness / intent) with d1-Omni-2B on the CS-45 turn-taking corpus once human_recorded strata exist; score with the CS-45 measurands against the CS-47 semantic-gate arms. | M4 |
| W2SP-6 | intake-2580, intake-2383 Stage-2 dive w2 ledger | Add a Voxtral-Mini-4B-Realtime GGUF through mtmd-cli run_audio_stream arm to the CS-8.STT5 screen (ranks and rejects only) on a scratch upstream build; record encoder and decoder times separately as the CLI already prints them. | P4 / CS-8.STT8 |
| W3DEC-1 | intake-2593, intake-2594 Stage-2 dive w3 ledger | Add a precision-and-backend parity gate to the TD-23 decision-backend screen BEFORE any quality or calibration number is read: for the chosen decision GGUF (d1-2B Q8_0 first), serve the BF16 file on CPU as reference, then Q8_0 on CPU, Q8_0 on HIP (MI210), and ... | P5 / TD-23.D1 |
| W3DEC-2 | intake-2595, intake-2593 Stage-2 dive w3 ledger | Add a batch-/schedule-invariance gate to the same screen: serve with -np 3, -b = -ub = 2048 (state must fit one ubatch), send request A alone (x5), then A concurrently with a shorter, a longer and an identical companion (x5 each, with a blocker request to ... | P5 / TD-23.D1 |
| W3DEC-3 | intake-2593, intake-2581, intake-2582 Stage-2 dive w3 ledger | Plan the build route for any /v1/systemone work: the frozen v10 tree has neither the endpoint (PR 29818 merge a4cb4c61 is not an ancestor of ffc1bac82; no systemone string; no *decision* file in tools/server) nor LFM3 (needs >= b11960). Cheapest honest route ... | P5 / TD-23.D1 |
| W3DEC-4 | intake-2593, intake-2582 Stage-2 dive w3 ledger | Record in the TD-18 calibration receipt the model pin that determines the probabilities: GGUF sha256, every decision.temperature.* metadata key/value (read with gguf-dump), llama.cpp build SHA, -b/-ub/-np, and the question kind plus option count (some ... | P5 / TD-18.1 |
| W3DEC-5 | intake-2593, intake-2595 Stage-2 dive w3 ledger | Pin the serving-safe API subset for the probe and any shim: only choice/score/noul; options within the model limit (52 openjev, 255 laya; read from the model, d1 limits unread); state must fit one ubatch (use -ub, not -b; 30073); avoid router mode with ... | K4 |
| W3DEC-6 | intake-2596, intake-2590 Stage-2 dive w3 ledger | Add one binding design line to the KV prefix-fork program: any future KV-editing operation (cell drop, position shift, ctx-shift variants) invalidates token-prefix matching as a correctness test; the orchestrator PrefixIndex and llama-server slot reuse key on ... | K3 |
| W3DEC-7 | intake-2596, intake-2590 Stage-2 dive w3 ledger | Zero-inference size screen before any AKV-style work: from existing orchestrator serving records and autopilot/REPL traces, compute for long agent loops the share of resident context tokens that are tool responses older than the latest 12 (the paper's drop ... | P6 / CF-AKV-0 |
| W3DEC-8 | intake-2596, intake-2590 Stage-2 dive w3 ledger | Conditional on W3DEC-7: a bounded semantics probe on an attention-only role model on llama.cpp-experimental: compare (a) seq_rm of old tool-response cells + seq_add repositioning (the drop+repos analogue) vs (b) re-prefill of the text with those responses ... | M3 |
| W3SPEC-1 | intake-2591 Stage-2 dive w3 ledger | Bounded probe (own scratch server, GPU correctness window, no region-lock needed per CORRECTNESS rule): on the production 27B shape (Q8_0, DFlash2 n-max 7, np 4, kv-unified, q8 KV, ROCm0) and on the frontdoor shape (Qwen3.6-35B-A3B-MTP Q8_0, draft-mtp n 4, np ... | P1 / DF2-12.1 |
| W3SPEC-2 | intake-2591 Stage-2 dive w3 ledger | Fold the DF2-12 row and W3SPEC-1 into one run; add the frontdoor :8070 MTP np4 shape (not covered by DF2-12, which names only Qwen3.8-27B DFlash2) and the cross-content canary. | P1 / DF2-12.1 |
| W3SPEC-3 | intake-2591 Stage-2 dive w3 ledger | If W3SPEC-1 shows divergence: reproduce on the experimental branch and try the PR #29454 approach (copy pre-ubatch state into unwritten snapshot slots every ubatch) as the candidate fix; it was never merged, so it must be carried as our own patch on a ... | M1 |
| W3SPEC-4 | intake-2592 Stage-2 dive w3 ledger | No action on our CPU/HIP stack; note in the speculative handoff that the n_vocab-sentinel failure is Vulkan-specific and fails loudly at src/llama-batch.cpp:52 (token validation), which our tree retains. | K1 |
| W3SPEC-x | intake-297 Stage-2 dive w3 ledger | DF2-DRAFTER-CAPABILITY input: z-lab/dflash @ 07ebd93db9f4 (2026-08-18, remote HEAD identical today) contains NO training code. 659-line dflash/model.py has only inference: CandidateSelector (selector_top_k=16 candidates per position via topk of the draft ... | K1 |
| W4UP-1 | intake-2597, intake-2598 Stage-2 dive w4 ledger | Temp-0 np>1 token-identity probe on :8070 (MTP np4) and :8083 (DFlash2 np4): per slot compare against an np=1 cold run of the same prompt AND the same np4 server with speculation off; include (i) mixed spec/non-spec interleaving, (ii) slot reuse: slot k ... | P1 / DF2-12.1 |
| W4UP-2 | intake-2598 Stage-2 dive w4 ledger | Run tests/test-recurrent-state-rollback (CPU, correctness only, no quiet host needed) on our qwen4exp-capable experimental binary with the frontdoor GGUF; require dirty-ctx and multi-seq split replay both pass. Prove binary freshness vs commit 0771238438 ... | P1 / DF2-12.1 |
| W4UP-3 | intake-2602, intake-2601, intake-2599, intake-2600 Stage-2 dive w4 ledger | d1 decision-model screen build must include a4cb4c61fd (#29818 systemone API) and 7e3eeee048 (#30361) if H2O-Lightning-4B is screened; cbe28bb3 (#30408) only for non-causal/embedding-mode decision models at np>1; 7e8324f5 (#30100) is Metal-only and NOT needed ... | P5 / TD-23.D1 |
| W4UP-4 | intake-2601 Stage-2 dive w4 ledger | Add a GENERIC-readout arm to TD-23 (any lineup chat model, thinking off, U+22B2 label readout) as a comparator to dedicated decision backends after the systemone base is in the screen build. | M4 |
| W4UP-5 | intake-2602 Stage-2 dive w4 ledger | Offer/track the group-parent checkpoint fix for hybrid decision models; evaluate by prompt-token count (1254 vs 827 shape) on our model before adopting. | M4 |
| PRE-2545 | intake-2545 Stage-1 preliminary actionable | Identify the STT model/runtime from the linked GitHub repo (expansion seed) before scoring for the speech lane. | K4 |
| PRE-2546 | intake-2546 Stage-1 preliminary actionable | Read the paper (expansion seed arXiv 2610.14162) and judge whether coarse-to-fine parallel generation has a drafter or non-AR serving role for EPYC. | M1 |
| PRE-2547 | intake-2547 Stage-1 preliminary actionable | Dive: decide whether looped/parallel-loop decoding changes bytes-per-token on bandwidth-bound CPU decode, and whether any served or candidate model is looped. | K2 |
| PRE-2548 | intake-2548 Stage-1 preliminary actionable | Dive: verify Table 2 and decide whether Soft-MTP is the objective to use if we train or restore MTP heads (Flash-Next Axis E, drafter training). | P2 / DF2-DRAFTER-CAPABILITY.OBJ |
| PRE-2549 | intake-2549 Stage-1 preliminary actionable | Dive with intake-2548: check the loss implementation and whether it composes with head-only training on a frozen trunk. | P2 / DF2-DRAFTER-CAPABILITY.OBJ |
| PRE-2550 | intake-2550 Stage-1 preliminary actionable | Dive: separate the transferable mechanism (exact GDN-state addressing) from the demo; decide if it informs GDN-hybrid serving or memory work. | P3 / AKX-ALL-31.GDN |
| PRE-2551 | intake-2551 Stage-1 preliminary actionable | Dive: check whether looped MoE trades weight bytes for compute in a way that suits bandwidth-bound EPYC decode. | K2 |
| PRE-2552 | intake-2552 Stage-1 preliminary actionable | Dive: establish the actual llama.cpp audio path and whether it can replace or augment the whisper.cpp + qwentts.cpp cascade on EPYC/MI210. | P4 / CS-8.STT8 |
| PRE-2553 | intake-2553 Stage-1 preliminary actionable | Dive: compare with the d1/Jev decision-model lineage already indexed and decide whether an audio/vision decision front end serves orchestrator routing or the speech turn-taking loop. | P5 / TD-23.D1 |
| PRE-2554 | intake-2554 Stage-1 preliminary actionable | Dive: verify the llama.cpp realtime speech-server path and which ggml generation it needs relative to the frozen kernel set. | M4 |
| PRE-2555 | intake-2555 Stage-1 preliminary actionable | Dive: extract the loop design and the verified-vs-numeric gap; map onto the AK candidate gate and gfx90a/x86 targets. | P3 / AKX-ALL-31.EDGE |
| PRE-2556 | intake-2556 Stage-1 preliminary actionable | Dive with intake-2555: read the loop and trace layout for AK reuse. | P3 / RVP-CTR-1 |
| PRE-2557 | intake-2557 Stage-1 preliminary actionable | Dive: decide what an equivalence/race checker would add to the AK correctness gate on gfx90a and x86. | P3 / RVP-RACE-1 |
| PRE-2558 | intake-2558 Stage-1 preliminary actionable | Dive: test whether the certificate-plus-independent-checker pattern fits belief-kernel derivations or registry/handoff consistency checks. | P7 / VB-CERT-1 |
| PRE-2559 | intake-2559 Stage-1 preliminary actionable | Dive: decide whether cache-level handoff between our role models is feasible in llama.cpp and what it would save over text handoff. | M3 |
| PRE-2560 | intake-2560 Stage-1 preliminary actionable | Dive with intake-2561: read the corrector implementation to size a llama.cpp port onto the DFlash2 drafter path. | P2 / DF2-LAT |
| PRE-2561 | intake-2561 Stage-1 preliminary actionable | Dive: measure-first design — top-K coverage of the verifier token on our DFlash2 drafter logits decides whether a corrector is worth porting. | P2 / DF2-LAT |
| PRE-2562 | intake-2562 Stage-1 preliminary actionable | Dive: read the architecture docs and the optimize-performance skill; extract what transfers to AK loops or llama.cpp serving. | K3 |
| PRE-2563 | intake-2563 Stage-1 preliminary actionable | None beyond architectural context; no measured result. | decline: a research-preview agent OS with no measurements and no touchpoint in the serving stack. |
| PRE-2564 | intake-2564 Stage-1 preliminary actionable | Dive (light): confirm availability and what is technically claimed; compare with full-duplex designs in the conversation-stack lane. | M4 |
| PRE-2565 | intake-2565 Stage-1 preliminary actionable | Dive: map the folding criteria onto the orchestrator REPL/agent loop (roles as subagents vs skills) and its tool count. | P6 / RI-25 |
| PRE-2566 | intake-2566 Stage-1 preliminary actionable | None: KB retrieval is ColBERT MaxSim; synthetic-only evidence. | decline: synthetic single-machine retrieval evidence, and KB retrieval uses ColBERT MaxSim, not cosine stores. |
| PRE-2567 | intake-2567 Stage-1 preliminary actionable | Dive: verify the table, check the HF card (quant/MTP head) and decide a same-recipe token-count and accuracy probe on our harness. | M6 |
| PRE-2568 | intake-2568 Stage-1 preliminary actionable | Dive with intake-2546. | M1 |
| PRE-2569 | intake-2569 Stage-1 preliminary actionable | Dive with intake-2561: sequential corrector baseline that DCOCO claims to beat under concurrency. | P2 / DF2-LAT |
| PRE-2570 | intake-2570 Stage-1 preliminary actionable | Dive: decide what a sound equivalence gate would need on gfx90a/x86 and which AK candidate classes it could cover. | P3 / RVP-RACE-1 |
| PRE-2571 | intake-2571 Stage-1 preliminary actionable | Dive with intake-2547. | K2 |
| PRE-2572 | intake-2572 Stage-1 preliminary actionable | Dive: verify config (qwen4_exp, MTP layers), whether the GGUFs carry nextn tensors, and fit against the INF-70 Axis-E MTP restoration need. | M6 |
| PRE-2573 | intake-2573 Stage-1 preliminary actionable | Dive: decide whether transcribe.cpp Parakeet streaming is a candidate STT against frozen whisper.cpp; check what the index already holds on transcribe.cpp. | K4 |
| PRE-2574 | intake-2574 Stage-1 preliminary actionable | Dive with intake-2550. | P3 / AKX-ALL-31.GDN |
| PRE-2575 | intake-2575 Stage-1 preliminary actionable | Dive: locate the llama.cpp code for the audio/realtime path and estimate the port onto llama.cpp-experimental; check ggml generation vs the speech kernel set. | P4 / CS-8.STT8 |
| PRE-2576 | intake-2576 Stage-1 preliminary actionable | Dive with intake-2559. | M3 |

## Handoff edits (Stage 4, after approval)

Each owner gets one appended section with the heading below. Checkbox lines are new tasks. Notes are prose with no checkbox. Trigger records stay prose until a reviewed session confirms their condition.

### `handoffs/active/agentic-rocm-kernel-authoring.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).** Store the hipcc --save-temps .s (or llvm-objdump of the code object) of each touched kernel in the candidate record next to its source diff. When a candidate claims a mechanism (MFMA, LDS staging, buffer loads), confirm in the ISA, and with a rocprof instruction counter where one exists, that the instruction executes on the measured path; a candidate whose claimed instruction is absent is refused.
- *Intake knowledge note, K5, row KERN-9 (intake-2556#record):* Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population.
- *Intake trigger record (no checkbox until it fires), M5, row KERN-8 (intake-2555#record, intake-2556#record):* GCN-Gym probe of AI lowering on gfx90a. Build a standalone harness that assembles LLM-patched AMDGCN for one compute-bound kernel (MMQ Q4_K prefill tile or FA at long context) with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a, loads it via hipModuleLoad and ...
```

### `handoffs/active/agentic-serving-harness-fixes.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **UFH14-TOOLS-1 — Count and cap the model-visible tool surface per role (intake-2565#record).** Enumerate what each role's prompt actually advertises (about 55 REPL globals plus about 55 registry tools behind TOOL/CALL) and log the count per role and per turn. Frontdoor turns called a tool in only 3.8-4.9% of turns (this handoff, line 670), so a large advertised surface costs prompt tokens for little use. Propose a per-role allowlist with deferred loading for the rest, behind a flag, for a later A/B.
```

### `handoffs/active/architect-model-selection-bench.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake trigger record (no checkbox until it fires), M6, row TCAP-1 (intake-2567#record, intake-2572#record):* Bounded A/B: base UD-IQ4_XS (current :8074 file) vs bottlecapai ThinkingCap IQ4_XS GGUF, llama-server, same recipe qwen38-flash-next-cpu-mtp, enable_thinking=true on /v1/chat/completions, frozen 40-60 prompt set (arch/plan-critique + reasoning, AIME-style, ...
```

### `handoffs/active/autokernel-all-devices-all-dimensions.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework.
- [ ] **AKX-ALL-31.QDEC — Exhaustive code-space decode check per served quant type (intake-2555#record).** For Q4_K, Q6_K, Q8_0, IQ2_*, IQ3_*, IQ4_XS and MXFP4, enumerate every per-element code together with every scale and min value that occurs in the served GGUFs, decode through the CPU and HIP dequant paths, and compare bit-for-bit with a scalar reference. First report how much of the code space the current random suite reaches; bit-level dequant is exactly the class an equivalence checker cannot prove, so enumeration is the sound substitute.
- [ ] **AKX-ALL-31.GDN — Deterministic one-hot GATED_DELTA_NET state oracle (intake-2574#record, intake-2550#record).** Add a test-backend-ops case on an experimental champion-derived branch that drives the delta rule with gate held at 1, beta at 1 and one-hot keys, so each step overwrites exactly one state row and a one-hot query must read back that row; compare against the closed-form result. Cover CPU f32, gfx90a f32 and BF16 state, and K > 1 snapshot slots. The current cases only compare backends on random data, which cannot detect a shared indexing error.
```

### `handoffs/active/autokernel-orchestrator-actor-backend.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake knowledge note, K5, row W2KERN-2 (intake-2588#record):* Compare AK candidate generation as plain multi-turn refinement vs agent-harness mode on token cost per accepted keep (PTXBench: agent harness cost 3.3-5.1x tokens and was worse on attention). Use existing AK run logs only; no new compute.
```

### `handoffs/active/autokernel-rebuild-program.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake trigger record (no checkbox until it fires), M5, row W2KERN-4 (intake-2589#record):* Failure-to-rule loop for AK: after each rejected batch, classify the failure reason and, when a class recurs (>=3), have an agent propose a permanent static check or oracle input, merged only under corpus tests of all prior keeps (CAKE Sec 3.2).
```

### `handoffs/active/context-folding-progressive.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **CF-AKV-0 — Zero-inference screen: how much resident context old tool results hold (intake-2590#record, intake-2596#record).** From existing orchestrator serving records and REPL traces, compute per long agent loop the share of resident context held by tool responses older than the last two turns, and the share of decode steps above 48K context. Escalate to the trigger-gated KV-drop semantics probe only if the median long loop holds at least 40% old tool results and at least 20% of decode steps exceed 48K tokens.
- *Intake trigger record (no checkbox until it fires), M3, row W2KERN-5 (intake-2590#record):* Bounded probe: tool-result KV drop+shift on a pure full-attention role in llama-server, using existing llama_memory_seq_rm + seq_add (as in the streaming-llm / context-shift path), on a recorded orchestrator agent trace. Measure (a) tokens re-prefilled per ...
```

### `handoffs/active/conversation-stack.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence.
- [ ] **CS-8.RT1 — /v1/realtime first-output latency and turn contract on EPYC and MI210 (intake-2579#record, intake-2575#record).** With the CS-8.STT8 scratch build, run the upstream realtime client against LFM3-Audio-2B on a CPU quarter and on the MI210, and measure time from end of input audio to first output audio over a frozen set of 20 utterances, plus barge-in: response.cancel latency to silence. The server does no turn detection (turn_detection is null), so the test drives commit, response.create and response.cancel from the client exactly as the CS-22 controller would. Compare against the cascade measured on the same utterances.
- *Intake knowledge note, K4, row SPEECH-5 (intake-2573#record):* No new STT action. Hex confirms the transcribe.cpp Parakeet Unified streaming path (Vulkan GPU only). Parakeet streaming vs whisper.cpp is already a measured-pending candidate: CS-8.STT0 40/40 CPU==GPU identity done, transcribe.cpp CPU 40-clip run 37/40 ...
- *Intake knowledge note, K4, row SPEECH-6 (intake-2573#record):* Add Parakeet Unified English (streaming, lookahead variants) as a named arm check in CS-8.STT5 if not already present, noting hex pins fork rev 7045d1c0 (transcribe.cpp 0.4.1) while our build pins db678a03; record both pins.
- *Intake knowledge note, K4, row W2SP-2 (intake-2579#record):* Specify the server-turn contract in CS-22: because /v1/realtime has turn_detection null, our controller (VAD + CS-47 semantic gate) must send commit/response.create/response.cancel; add this as the integration seam in CS-22.A1 rather than waiting on a server ...
- *Intake trigger record (no checkbox until it fires), M4, row SPEECH-2 (intake-2552#record, intake-2554#record, intake-2575#record):* Add LFM3-Audio-2B/Omni-2B as a third challenger in the CS-8 G1/G3/G4 interlocutor bake-off: G1 en/it TTS intelligibility via llama-tts (note voice chat is English-only per card, so Italian only for TTS/ASR), G3 tool-call slot quality from speech, G4 ...
- *Intake trigger record (no checkbox until it fires), M4, row SPEECH-4 (intake-2575#record):* Reuse the upstream /v1/realtime (OpenAI-compatible) and Voxtral-Realtime support as a CS-20 backend interface option: write a realtime client adapter in the voice controller that speaks /v1/realtime beside the whisper :9000 / qwentts :9002 cascade.
- *Intake trigger record (no checkbox until it fires), M4, row SPEECH-7 (intake-2564#record):* Monitor Dessa for paper, weights or API; trigger = any released checkpoint or paper with benchmark numbers, then fold into the M8 full-duplex reference slot check (language gate D2 likely fails if English-only).
- *Intake trigger record (no checkbox until it fires), M4, row W2SP-5 (intake-2581#record):* Spoken-state decision probe (turn completeness / intent) with d1-Omni-2B on the CS-45 turn-taking corpus once human_recorded strata exist; score with the CS-45 measurands against the CS-47 semantic-gate arms.
- *Intake trigger record (no checkbox until it fires), M4, row AGENT-13 (intake-2553#record):* Speech turn-taking decider test (only after human-recorded strata exist): d1-Omni-2B reads a short audio window and answers noul/score questions (end of turn? backchannel needed?) on the CS-45 corpus; compare against the CS-22 controller policy and the D1 ...
```

### `handoffs/active/cpu-decode-roofline-program.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **G2-CONC.MP — Add a simultaneous multi-prefill arm to the G2-CONC promotion gate (intake-2577#record).** For every speculative recipe on the promotion candidate binary: c in {2, 3, 5} equal-length prompts that differ only by a salt, issued at the same instant, temp 0, speculation on and off, each output compared token for token with a solo np-1 run. The vLLM defect on the same model family corrupted state only when two or more prompts prefilled in one scheduler step, which a staggered concurrency test never exercises.
- *Intake knowledge note, K1, row TCAP-2 (intake-2572#record):* Record that INF-70 Axis-E "MTP needs FP8 re-download" is obsolete: head already on disk (mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf, 2.79 GB, 2026-09-02); no ThinkingCap download is needed for MTP
- *Intake knowledge note, K2, row LOOP-1 (intake-2547#record, intake-2571#record):* Add a knowledge note to the INF-70 roofline program: weight-reuse architectures. Sequential looping multiplies weight bytes per token by L, and with 32 MiB L3 per CCX (384 MiB total) a block above ~32 MiB per CCX cannot be cache-reused (e.g. a 7B 14-layer PLT ...
- *Intake knowledge note, K2, row LOOP-2 (intake-2547#record, intake-2571#record):* Ingest and dive LoopCoder-v2 (arXiv 2606.18023): released 7B PLT 2-loop coder (Apache-2.0, HF Multilingual-Multimodal-NLP/LoopCoder-V2, 14 layers, hidden 5120, 8 KV heads) is the first PLT checkpoint we can actually run; card claims SWE-bench Verified 43.0 -> ...
- *Intake knowledge note, K2, row LOOP-5 (intake-2551#record):* Record in reasoning-compression.md only: looped MoE R=5 at 0.3B-1.3B reaches reasoning parity with 0.6B-2.9B at 1.8x training-compute-defined inference compute while trailing Overall 46.9 vs 50.2; no latency/bytes measured; no checkpoint released in the text.
- *Intake knowledge note, K2, row W2LOOP-3 (intake-2587#record):* Knowledge-only: record that our GDN graph hard-caps beta at 1 (src/models/qwen3next.cpp:417 ggml_sigmoid) matching the Qwen3.5 control that failed to generalise hidden tracking; no probe.
- *Intake trigger record (no checkbox until it fires), M2, row LOOP-4 (intake-2547#record, intake-2551#record):* Bounded CPU probe on a llama.cpp-experimental branch with the Ouro port: Ouro-1.4B Q4_K_M (854 MB per card), llama-bench tg at num_loops 1/2/4 via --override-kv, reporting achieved GB/s counting bytes once per loop against the C0 153 GB/s ceiling. This ...
- *Intake trigger record (no checkbox until it fires), M2, row W2LOOP-1 (intake-2585#record, intake-2586#record):* On an experimental llama.cpp branch freshly cut from production v10, cherry #25994 plus #29823 (about 590 added lines) and measure Ouro-1.4B Q8_0/Q4_K_M at --override-kv ouro.num_loops=int:1/2/4 on EPYC CPU (one quarter and full socket): tok/s, achieved GB/s ...
- *Intake trigger record (no checkbox until it fires), M2, row W2LOOP-2 (intake-2584#record):* Monitor triggers: (a) llama.cpp or vLLM PR adding iquestpltcoder / PLT, (b) an independent replication of LoopCoder-v2 R=2 SWE-bench Verified, (c) a timing number for PLT decode. Any one fires ingest-and-dive on it.
```

### `handoffs/active/dflash2-block-drafter-experimental-build.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary.
- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor.
- [ ] **DF2-PM — Point-mass draft proposals at production temperature (intake-2561#record).** Behind an env knob on the experimental build, make the DFlash2 temp>0 branch propose the argmax selector walk with a point-mass distribution instead of sampling softmax(scores/T); the verifier then accepts with p_target(draft) and resamples from the residual (common/sampling.cpp:740-766), which is lossless. A/B against the stock sampled walk on the DF2-4 protocol (12 prompts, temp 0.6, top-p 0.95, top-k 20) at np 1 and np 4, at least 5 interleaved pairs; primary metric weighted acceptance, secondary tok/s; the SPEC-PIT.1 distribution gate must pass. Adopt into the next champion fold only if weighted acceptance improves by at least 3% in at least 4 of 5 pairs at both np values, tok/s does not regress and SPEC-PIT.1 passes; otherwise record the per-pair numbers and close.
- [ ] **DF2-DRAFTER-CAPABILITY.OBJ — Fix the drafter-training data contract before any capture (intake-2548#record, intake-2578#record, intake-297#record).** Amend the capture contract inherited from INF-62 ("hard next-token labels") so every feature dump also taps the target's final post-norm hidden state (5120 x bf16 = 10,240 bytes per token, +20% over the current taps), which yields the exact teacher distribution through the frozen output head. Make forward KL toward the target distribution the default objective with hard labels as the fallback arm (with a frozen trunk, Soft-MTP's gradient equals direct forward KL), and record the Nemotron 3 Ultra frozen-backbone recipe (temperature 2, hidden states sampled from earlier draft steps) as an option. Note that z-lab/dflash @ 07ebd93 ships no training code, so any drafter or selector training is research, not a port.
- *Intake knowledge note, K1, row SPEC-4 (intake-2560#record, intake-2561#record, intake-2569#record):* Prepare a text update (owning session applies) to the LiLiCorr monitor paragraph: name DCOCO (intake-2561#record) and Domino (intake-2569#record) as the same correction family; record that DFlash2 already ships a learned K=16 rank-256 selector lattice with a ...
- *Intake knowledge note, K1, row SPEC-6 (intake-2561#record, intake-2569#record):* CPU: no separate action. The 27B DFlash2 path is served on the MI210 only, and CPU speculative work for Flash-Next is MTP (Axis E). If SPEC-3 is ever built, its graph ops are backend-agnostic and must pass CPU no-regression in the four-step workflow.
- *Intake knowledge note, K1, row SPEC2-4 (intake-2578#record):* Add to DF2-DRAFTER-CAPABILITY the Nemotron Sec 3.4 head/drafter fine-tune recipe as an option: freeze target, sample hidden states from earlier draft steps, forward-KL T=2 to target logits on target on-policy rollouts at temp 1 (reference scale: 12K steps, bs ...
- *Intake knowledge note, K1, row SPEC2-5 (intake-1724#record):* Answer only (no entry): the z-lab card text does not say how the DFlash2 selector (top-16, rank-256 transition score) was trained, and reports no tau gain over DFlash 1 for Qwen3.8-27B. The inco.ai blog (sha256-12 99dc56f49911) gives the selector score ...
- *Intake knowledge note, K1, row W3SPEC-x (intake-297#record):* DF2-DRAFTER-CAPABILITY input: z-lab/dflash @ 07ebd93db9f4 (2026-08-18, remote HEAD identical today) contains NO training code. 659-line dflash/model.py has only inference: CandidateSelector (selector_top_k=16 candidates per position via topk of the draft ...
- *Intake knowledge note, K1, row MTP-3 (intake-2548#record):* No change to Axis E. Restoring the Qwen3.8-Flash-Next MTP head loads the published unsloth shared-Q8_0 head (no training), so the MTP-objective choice does not touch it.
- *Intake trigger record (no checkbox until it fires), M1, row SPEC-3 (intake-2560#record, intake-2561#record):* Port the DCOCO head to llama.cpp as a replacement DFlash2 selector, and train it on the frozen DFlash2 backbone. Gated on SPEC-1 PROMOTE. Port: converter keys/tensors for cand_proj, ctx_h_proj, cand_ctx_proj + LN, pair_proj and the 386->256->1 MLP (~100 LOC ...
- *Intake trigger record (no checkbox until it fires), M1, row SPEC-5 (intake-2569#record):* Domino-style GRU + full-vocab low-rank correction head on the DFlash2 drafter: no work now. It needs full drafter co-training with the curriculum, and its sequential head adds a 256x248320 logit-residual projection per position on the critical path. Revisit ...
- *Intake trigger record (no checkbox until it fires), M1, row MTP-2 (intake-2548#record, intake-2549#record):* Bounded frozen-trunk probe on the Soft-MTP repo (MI210, ROCm torch, <=4 GPU-h, no llama.cpp). Take the released 167M (or 332M) NTP checkpoint, set freeze_backbone=true, and train fresh K=3 DeepSeek-style heads under two arms with identical data order, seed, ...
- *Intake trigger record (no checkbox until it fires), M1, row W3SPEC-3 (intake-2591#record):* If W3SPEC-1 shows divergence: reproduce on the experimental branch and try the PR #29454 approach (copy pre-ubatch state into unwritten snapshot slots every ubatch) as the candidate fix; it was never merged, so it must be carried as our own patch on a ...
- *Intake trigger record (no checkbox until it fires), M1, row LOOP-6 (intake-2546#record, intake-2568#record):* Monitor NCM as a drafter source: trigger = a released NCM-style generator with a general-text tokenizer sharing a served model vocabulary, or any measured acceptance rate against an AR target. Do not build now: released checkpoints are per-dataset ~100M-725M ...
```

### `handoffs/active/gpu-acceleration-path.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake knowledge note, K2, row LOOP-3 (intake-2547#record):* Correct the stale gate: Ouro now has a community llama.cpp port (BrandeisPatrick/loop-transformer, ouro arch, 324 added lines, PR ggml-org/llama.cpp#29823, GGUFs for Ouro 1.4B/2.6B +Thinking) built on upstream looped-model machinery merged for Nanbeige4.2 (PR ...
- *Intake knowledge note, K2, row W2LOOP-4 (intake-2585#record, intake-2586#record):* Correct the stale note in gpu-acceleration-path.md ~line 248 (intake-332 "Not llama.cpp compatible") to say nanbeige looped arch merged 2026-07-27 and Ouro is PR #29823 open; owning session applies.
```

### `handoffs/active/kv-prefix-fork-and-paged-attention.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **KPF-RS-1 — Recurrent-state hash conformance after checkpoint restore and fork (intake-2574#record, intake-2591#record).** On an experimental champion-derived branch, extend `test-recurrent-state-rollback` and the KPF fork path to hash the full recurrent state (all Gated-DeltaNet state tensors and every snapshot slot, written and unwritten) after a checkpoint restore, after a fork from a checkpoint, and after a speculative rollback at np 1 and np 4, and compare against the state reached by re-prefilling the same tokens. Today the test compares logits to 1e-5 only, which can pass while an unwritten snapshot slot carries another sequence's state. Include a planted mutation (skip one snapshot write) that must fail. CPU and gfx90a legs.
- *Intake knowledge note, K3, row W2KERN-6 (intake-2590#record):* Record the history-dependence correctness rule for any future KV-editing serving feature: a slot/prefix index keyed only by token prefix (src/inference/prefix_index.py) must also key on the drop/shift operation history, or mark the slot unmatchable after an ...
- *Intake knowledge note, K3, row W3DEC-6 (intake-2590#record, intake-2596#record):* Add one binding design line to the KV prefix-fork program: any future KV-editing operation (cell drop, position shift, ctx-shift variants) invalidates token-prefix matching as a correctness test; the orchestrator PrefixIndex and llama-server slot reuse key on ...
- *Intake knowledge note, K3, row AGENT-4 (intake-2565#record):* Do NOT adopt the article single-loop thesis for our CPU stack without measurement: the article premise is frontier models with thinking on; our workers are local quantised Qwen3.x on a BW-bound CPU where a separate small-context worker call is cheaper per ...
- *Intake knowledge note, K3, row AGENT-6 (intake-2559#record, intake-2576#record):* Design note (no compute): map C2C onto llama.cpp. Feasible path = out-of-process fuser. Receiver and Sharer each prefill the same prompt; read per-layer K/V from each via llama_state_seq_get_data (include/llama.h:881) or /slots/{id}?action=save ...
- *Intake knowledge note, K3, row AGENT-8 (intake-2576#record):* Read the thu-nics AKV repo (cache engineering for agents, follow-up to C2C, Apache-2.0, pushed 2026-10-21) before sizing any pair-training, since it may cover agent KV reuse without a per-pair trained fuser.
- *Intake knowledge note, K3, row AGENT-10 (intake-2562#record):* Use Resin docs/cache-pool.md + architecture.md Prefix reuse as design reference for hybrid prefix reuse: its snapshots are taken at an alignment equal to the LCM of all group block sizes and restore attention, SWA and recurrent state at the same boundary, ...
- *Intake trigger record (no checkbox until it fires), M3, row W3DEC-8 (intake-2590#record, intake-2596#record):* Conditional on W3DEC-7: a bounded semantics probe on an attention-only role model on llama.cpp-experimental: compare (a) seq_rm of old tool-response cells + seq_add repositioning (the drop+repos analogue) vs (b) re-prefill of the text with those responses ...
- *Intake trigger record (no checkbox until it fires), M3, row AGENT-5 (intake-2559#record, intake-2576#record):* Bounded offline probe on CPU (HF transformers, no llama.cpp): with released nics-efc/C2C_Fuser qwen3_8b+qwen2.5_7b fuser, run n=200 frozen items from a MC set the stack already scores (e.g. MMLU-Redux subset used in canonical suites) in 4 arms: Receiver-only, ...
- *Intake trigger record (no checkbox until it fires), M3, row AGENT-7 (intake-2559#record):* Role-pair candidate list, ranked: (1) architect_critic / coder_escalation (Qwen3.8-27B Q8_0, dense KV-densest per model_registry.yaml:541) as SHARER -> worker_general/worker_summarize (Qwen3.6-35B-A3B MoE, receiver; must check whether its layers are all full ...
```

### `handoffs/active/qwen-mtp-llamacpp-port.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake knowledge note, K1, row W3SPEC-4 (intake-2592#record):* No action on our CPU/HIP stack; note in the speculative handoff that the n_vocab-sentinel failure is Vulkan-specific and fails loudly at src/llama-batch.cpp:52 (token validation), which our tree retains.
- *Intake trigger record (no checkbox until it fires), M6, row TCAP-3 (intake-2572#record):* If A/B runs, add arm B2 = ThinkingCap trunk + our unsloth shared-Q8_0 draft file vs embedded head, measure alpha for both
```

### `handoffs/active/rocm-verify-profile-backend.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree build three seeded-race HIP mutants, each deleting one barrier in MMQ, MMVQ and the FA kernel, and run the served-shape suite 20 times each. CPU: build test-backend-ops with ThreadSanitizer, using LLVM libomp with Archer annotations, and run the threaded ops. Decision rule: if any GPU mutant passes the gate in all 20 runs, open the gfx90a race-only symbolic-executor trigger; if all are caught, record the gate as race-sensitive at these sites. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.
- [ ] **RVP-CTR-1 — Counter-grounded planner signals for the GPU AK lane (intake-2556#record).** For the top hotspot kernel of each GPU screen, capture a fixed declared counter subset with rocprofv2 (occupancy, LDS bank conflicts, VALU/MFMA busy, memory unit stall, achieved bandwidth) and pass it to the planner with the rule that every proposed idea must cite a counter that is present, and a missing counter may not be treated as zero. Compare 2 planner rounds with and without counters on the same target and budget.
- *Intake trigger record (no checkbox until it fires), M5, row KERN-2 (intake-2557#record, intake-2570#record):* Build a race-only symbolic executor for gfx90a AMDGCN: parse hipcc --save-temps asm, concrete thread/workgroup indices and launch params, per-byte LDS reader/writer sets between s_barrier, lgkmcnt/vmcnt waits as completion points, exec-mask lanes, wave64. ...
```

### `handoffs/active/routing-intelligence.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **RI-25 — Zero-inference fold replay over delegation records (intake-2565#record).** Apply the fold criteria (fold a sub-agent only if the folded version does not score worse; inspect which tasks flip; repeat runs) to existing orchestrator delegation records: for each delegate() role (worker_math, worker_general, worker_summarize share one model), measure from records how often a chain needs the role's own context, how much of the 4,000-character truncated hand-off (src/repl_environment/routing.py:581) reaches the worker, and how often the delegated answer is re-asked by the caller. Output a per-role fold-candidate table; no serving change.
```

### `handoffs/active/speculative-decoding-mtp-refresh.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **SPEC-CANARY.1 — Per-request acceptance-collapse canary for every speculative serving role (intake-2577#record).** In the orchestrator's llama-server telemetry, flag any request with at least 64 drafted tokens and zero accepted, and any request whose last 256 generated tokens repeat one n-gram block, recording role, port, slot, n_parallel, draft settings and request id. Ship it as a passive counter with a dashboard health field; it changes no serving behaviour. Test it with a replayed log containing a planted zero-acceptance run and a planted repetition tail.
- *Intake trigger record (no checkbox until it fires), M1, row MTP-4 (intake-2548#record):* Record a trigger on the speculative-decoding refresh. If a served fine-tune ships with a stock (base-co-trained) MTP head, as already observed for ThinkingCap and Qwopus, the remedy is head-only re-alignment on the frozen fine-tuned trunk against its own NTP ...
- *Intake trigger record (no checkbox until it fires), M1, row SPEC2-3 (intake-2577#record):* Note thinking-mode default sampling repetition risk: issue says model card recommends presence_penalty 0-2 and attributes loops to degenerate state amplified by temp 1.0 / top_k 20 / top_p 0.95; check the Flash-Next architect_general request sampler against ...
```

### `handoffs/active/tool-use-eval-contract.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake trigger record (no checkbox until it fires), M3, row AGENT-3 (intake-2565#record):* Add a per-fold eval: before folding any worker role into skills, require a frozen end-to-end set covering every production chain (architect -> coder_escalation, frontdoor -> worker_*) and every must-not-break rule, repeated >=2 times, reporting flipped tasks. ...
```

### `handoffs/active/typed-decision-plane.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.
- [ ] **TD-18.1 — Pin GGUF decision backends in the TD-18 calibration receipt (intake-2593#record).** For llama.cpp decision backends, the receipt records the GGUF sha256, every decision.temperature.* metadata value (the endpoint scales probabilities by them and exposes no request-time override), the server build commit, and the -np/-b/-ub flags, because each of these changes the probabilities being calibrated.
- *Intake knowledge note, K4, row W2SP-4 (intake-2582#record):* Record in TD-23 candidate list that d1-2B/3B are VL models with LFM Open License v1.0 and that the llama.cpp path supports noul/choice/score only; routing questions are choice+score so the subset is sufficient.
- *Intake knowledge note, K4, row W3DEC-5 (intake-2593#record, intake-2595#record):* Pin the serving-safe API subset for the probe and any shim: only choice/score/noul; options within the model limit (52 openjev, 255 laya; read from the model, d1 limits unread); state must fit one ubatch (use -ub, not -b; 30073); avoid router mode with ...
- *Intake trigger record (no checkbox until it fires), M4, row W4UP-4 (intake-2601#record):* Add a GENERIC-readout arm to TD-23 (any lineup chat model, thinking off, U+22B2 label readout) as a comparator to dedicated decision backends after the systemone base is in the screen build.
- *Intake trigger record (no checkbox until it fires), M4, row W4UP-5 (intake-2602#record):* Offer/track the group-parent checkpoint fix for hybrid decision models; evaluate by prompt-token count (1254 vs 827 shape) on our model before adopting.
```

### `handoffs/active/vidya-belief-substrate-program.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **VB-CERT-1 — Independent checker for the gate certificate (intake-2558#record).** Write scripts/vidya/cert_check.py, a standalone verifier of epyc.vidya/certificate/v1 that shares no imports with fold.py, gate.py or lattice code, re-derives the verdict from the certificate's stated inputs, and compares certificate.frontier and as_of explicitly. Today certificate_hash is a self-hash and input_attestations holds labels rather than the digests the spec section 11.2 requires (scripts/vidya/gate.py:130-166). Add forged-certificate tests (altered verdict, swapped frontier, stale as_of, label-only attestation) that must be rejected.
```

## Index edits

None. No new handoff is created. All tasks land in existing owners that already hold exactly one domain-index row. After Stage 4, run `python3 scripts/handoffs/index_state.py` and then `--check`.

## Intake-entry updates (Stage 4)

From `entry_updates`: `integration_disposition`, `handoffs_updated` and `disposition_evidence` on intake-2545..2602.

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {
      "id": "intake-2545",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "PRE-2545 -> K4"
      ]
    },
    {
      "id": "intake-2546",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-6 -> M1",
        "PRE-2546 -> M1"
      ]
    },
    {
      "id": "intake-2547",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md",
        "gpu-acceleration-path.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-1 -> K2",
        "LOOP-2 -> K2",
        "LOOP-3 -> K2",
        "LOOP-4 -> M2",
        "PRE-2547 -> K2"
      ]
    },
    {
      "id": "intake-2548",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md",
        "speculative-decoding-mtp-refresh.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "MTP-1 -> P2 / DF2-DRAFTER-CAPABILITY.OBJ",
        "MTP-2 -> M1",
        "MTP-3 -> K1",
        "MTP-4 -> M1",
        "MTP-5 -> decline: Soft-MTP as a pretraining objective needs trunk training, which this stack does not do.",
        "PRE-2548 -> P2 / DF2-DRAFTER-CAPABILITY.OBJ"
      ]
    },
    {
      "id": "intake-2549",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "MTP-1 -> P2 / DF2-DRAFTER-CAPABILITY.OBJ",
        "MTP-2 -> M1",
        "PRE-2549 -> P2 / DF2-DRAFTER-CAPABILITY.OBJ"
      ]
    },
    {
      "id": "intake-2550",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-all-devices-all-dimensions.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "MEM-1 -> P3 / AKX-ALL-31.GDN",
        "MEM-3 -> decline: an in-weights calculator costs about 1.6 to 2 times the weight bytes per token on a bandwidth-bound h",
        "PRE-2550 -> P3 / AKX-ALL-31.GDN"
      ]
    },
    {
      "id": "intake-2551",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-4 -> M2",
        "LOOP-5 -> K2",
        "PRE-2551 -> K2"
      ]
    },
    {
      "id": "intake-2552",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEECH-1 -> P4 / CS-8.STT8",
        "SPEECH-2 -> M4",
        "PRE-2552 -> P4 / CS-8.STT8"
      ]
    },
    {
      "id": "intake-2553",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md",
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "AGENT-12 -> P5 / TD-23.D1",
        "AGENT-13 -> M4",
        "AGENT-14 -> P5 / TD-23.D1",
        "PRE-2553 -> P5 / TD-23.D1"
      ]
    },
    {
      "id": "intake-2554",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEECH-1 -> P4 / CS-8.STT8",
        "SPEECH-2 -> M4",
        "PRE-2554 -> M4"
      ]
    },
    {
      "id": "intake-2555",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "agentic-rocm-kernel-authoring.md",
        "autokernel-all-devices-all-dimensions.md",
        "rocm-verify-profile-backend.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "KERN-1 -> P3 / RVP-RACE-1",
        "KERN-3 -> P3 / AKX-ALL-31.EDGE",
        "KERN-4 -> P3 / AKX-ALL-31.QDEC",
        "KERN-6 -> P3 / RVP-CTR-1",
        "KERN-7 -> P3 / C5-ISA-1",
        "KERN-8 -> M5",
        "PRE-2555 -> P3 / AKX-ALL-31.EDGE"
      ]
    },
    {
      "id": "intake-2556",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "agentic-rocm-kernel-authoring.md",
        "autokernel-all-devices-all-dimensions.md",
        "rocm-verify-profile-backend.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "KERN-5 -> P3 / AKX-ALL-31.EDGE",
        "KERN-6 -> P3 / RVP-CTR-1",
        "KERN-7 -> P3 / C5-ISA-1",
        "KERN-8 -> M5",
        "KERN-9 -> K5",
        "PRE-2556 -> P3 / RVP-CTR-1"
      ]
    },
    {
      "id": "intake-2557",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "rocm-verify-profile-backend.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "KERN-2 -> M5",
        "KERN-11 -> decline: upstream Volta and its Blackwell fork are PTX-only and the host has no NVIDIA GPU; the race model tra",
        "PRE-2557 -> P3 / RVP-RACE-1"
      ]
    },
    {
      "id": "intake-2558",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "vidya-belief-substrate-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "MEM-4 -> P7 / VB-CERT-1",
        "MEM-5 -> decline: the handoff index check already re-derives and compares on every run, so a certificate layer adds not",
        "MEM-6 -> P7 / VB-CERT-1",
        "PRE-2558 -> P7 / VB-CERT-1"
      ]
    },
    {
      "id": "intake-2559",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "AGENT-5 -> M3",
        "AGENT-6 -> K3",
        "AGENT-7 -> M3",
        "PRE-2559 -> M3"
      ]
    },
    {
      "id": "intake-2560",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEC-1 -> P2 / DF2-LAT",
        "SPEC-3 -> M1",
        "SPEC-4 -> K1",
        "PRE-2560 -> P2 / DF2-LAT"
      ]
    },
    {
      "id": "intake-2561",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEC-1 -> P2 / DF2-LAT",
        "SPEC-2 -> P2 / DF2-PM",
        "SPEC-3 -> M1",
        "SPEC-4 -> K1",
        "SPEC-6 -> K1",
        "PRE-2561 -> P2 / DF2-LAT"
      ]
    },
    {
      "id": "intake-2562",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "AGENT-9 -> decline: the Resin measurement-discipline text is weaker than the Annex K protocol the loop already follows.",
        "AGENT-10 -> K3",
        "AGENT-11 -> decline: the Resin engine/runner split has no CPU or ROCm runner and production serving is llama.cpp.",
        "PRE-2562 -> K3"
      ]
    },
    {
      "id": "intake-2563",
      "integration_disposition": "declined",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "PRE-2563 -> decline: a research-preview agent OS with no measurements and no touchpoint in the serving stack."
      ]
    },
    {
      "id": "intake-2564",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEECH-7 -> M4",
        "PRE-2564 -> M4"
      ]
    },
    {
      "id": "intake-2565",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "agentic-serving-harness-fixes.md",
        "kv-prefix-fork-and-paged-attention.md",
        "routing-intelligence.md",
        "tool-use-eval-contract.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "AGENT-1 -> P6 / RI-25",
        "AGENT-2 -> P6 / UFH14-TOOLS-1",
        "AGENT-3 -> M3",
        "AGENT-4 -> K3",
        "PRE-2565 -> P6 / RI-25"
      ]
    },
    {
      "id": "intake-2566",
      "integration_disposition": "declined",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "PRE-2566 -> decline: synthetic single-machine retrieval evidence, and KB retrieval uses ColBERT MaxSim, not cosine stores."
      ]
    },
    {
      "id": "intake-2567",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "architect-model-selection-bench.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "TCAP-1 -> M6",
        "TCAP-4 -> decline: the vendor PRO tier is closed and no method is disclosed.",
        "PRE-2567 -> M6"
      ]
    },
    {
      "id": "intake-2568",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-6 -> M1",
        "PRE-2568 -> M1"
      ]
    },
    {
      "id": "intake-2569",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEC-4 -> K1",
        "SPEC-5 -> M1",
        "SPEC-6 -> K1",
        "PRE-2569 -> P2 / DF2-LAT"
      ]
    },
    {
      "id": "intake-2570",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-all-devices-all-dimensions.md",
        "rocm-verify-profile-backend.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "KERN-1 -> P3 / RVP-RACE-1",
        "KERN-2 -> M5",
        "KERN-4 -> P3 / AKX-ALL-31.QDEC",
        "KERN-10 -> P3 / RVP-RACE-1",
        "KERN-11 -> decline: upstream Volta and its Blackwell fork are PTX-only and the host has no NVIDIA GPU; the race model tra",
        "PRE-2570 -> P3 / RVP-RACE-1"
      ]
    },
    {
      "id": "intake-2571",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-1 -> K2",
        "LOOP-2 -> K2",
        "PRE-2571 -> K2"
      ]
    },
    {
      "id": "intake-2572",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "architect-model-selection-bench.md",
        "cpu-decode-roofline-program.md",
        "qwen-mtp-llamacpp-port.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "TCAP-1 -> M6",
        "TCAP-2 -> K1",
        "TCAP-3 -> M6",
        "PRE-2572 -> M6"
      ]
    },
    {
      "id": "intake-2573",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEECH-5 -> K4",
        "SPEECH-6 -> K4",
        "PRE-2573 -> K4"
      ]
    },
    {
      "id": "intake-2574",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-all-devices-all-dimensions.md",
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "MEM-1 -> P3 / AKX-ALL-31.GDN",
        "MEM-2 -> P1 / KPF-RS-1",
        "MEM-3 -> decline: an in-weights calculator costs about 1.6 to 2 times the weight bytes per token on a bandwidth-bound h",
        "PRE-2574 -> P3 / AKX-ALL-31.GDN"
      ]
    },
    {
      "id": "intake-2575",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEECH-1 -> P4 / CS-8.STT8",
        "SPEECH-2 -> M4",
        "SPEECH-3 -> P4 / CS-8.STT8",
        "SPEECH-4 -> M4",
        "W2SP-1 -> P4 / CS-8.RT1",
        "PRE-2575 -> P4 / CS-8.STT8"
      ]
    },
    {
      "id": "intake-2576",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "AGENT-5 -> M3",
        "AGENT-6 -> K3",
        "AGENT-8 -> K3",
        "PRE-2576 -> M3"
      ]
    },
    {
      "id": "intake-2577",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md",
        "speculative-decoding-mtp-refresh.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEC2-1 -> P1 / SPEC-CANARY.1",
        "SPEC2-2 -> P1 / G2-CONC.MP",
        "SPEC2-3 -> M1"
      ]
    },
    {
      "id": "intake-2578",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEC2-4 -> K1"
      ]
    },
    {
      "id": "intake-2579",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-1 -> P4 / CS-8.RT1",
        "W2SP-2 -> K4"
      ]
    },
    {
      "id": "intake-2580",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-6 -> P4 / CS-8.STT8"
      ]
    },
    {
      "id": "intake-2581",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "conversation-stack.md",
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-3 -> P5 / TD-23.D1",
        "W2SP-5 -> M4",
        "W3DEC-3 -> P5 / TD-23.D1"
      ]
    },
    {
      "id": "intake-2582",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-3 -> P5 / TD-23.D1",
        "W2SP-4 -> K4",
        "W3DEC-3 -> P5 / TD-23.D1",
        "W3DEC-4 -> P5 / TD-18.1"
      ]
    },
    {
      "id": "intake-2583",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-3 -> P5 / TD-23.D1"
      ]
    },
    {
      "id": "intake-2584",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-2 -> M2"
      ]
    },
    {
      "id": "intake-2585",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md",
        "gpu-acceleration-path.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-1 -> M2",
        "W2LOOP-4 -> K2"
      ]
    },
    {
      "id": "intake-2586",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md",
        "gpu-acceleration-path.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-1 -> M2",
        "W2LOOP-4 -> K2"
      ]
    },
    {
      "id": "intake-2587",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-3 -> K2"
      ]
    },
    {
      "id": "intake-2588",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "agentic-rocm-kernel-authoring.md",
        "autokernel-all-devices-all-dimensions.md",
        "autokernel-orchestrator-actor-backend.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2KERN-1 -> P3 / C5-ISA-1",
        "W2KERN-2 -> K5",
        "W2KERN-3 -> P3 / AKX-ALL-31.EDGE"
      ]
    },
    {
      "id": "intake-2589",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-all-devices-all-dimensions.md",
        "autokernel-rebuild-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2KERN-3 -> P3 / AKX-ALL-31.EDGE",
        "W2KERN-4 -> M5"
      ]
    },
    {
      "id": "intake-2590",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "context-folding-progressive.md",
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2KERN-5 -> M3",
        "W2KERN-6 -> K3",
        "W2KERN-7 -> decline: the AKV server is SGLang and softmax-only; it stays a design reference.",
        "W3DEC-6 -> K3",
        "W3DEC-7 -> P6 / CF-AKV-0",
        "W3DEC-8 -> M3"
      ]
    },
    {
      "id": "intake-2591",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3SPEC-1 -> P1 / DF2-12.1",
        "W3SPEC-2 -> P1 / DF2-12.1",
        "W3SPEC-3 -> M1"
      ]
    },
    {
      "id": "intake-2592",
      "integration_disposition": "knowledge_only",
      "handoffs_updated": [
        "qwen-mtp-llamacpp-port.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3SPEC-4 -> K1"
      ]
    },
    {
      "id": "intake-2593",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3DEC-1 -> P5 / TD-23.D1",
        "W3DEC-2 -> P5 / TD-23.D1",
        "W3DEC-3 -> P5 / TD-23.D1",
        "W3DEC-4 -> P5 / TD-18.1",
        "W3DEC-5 -> K4"
      ]
    },
    {
      "id": "intake-2594",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3DEC-1 -> P5 / TD-23.D1"
      ]
    },
    {
      "id": "intake-2595",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3DEC-2 -> P5 / TD-23.D1",
        "W3DEC-5 -> K4"
      ]
    },
    {
      "id": "intake-2596",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "context-folding-progressive.md",
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3DEC-6 -> K3",
        "W3DEC-7 -> P6 / CF-AKV-0",
        "W3DEC-8 -> M3"
      ]
    },
    {
      "id": "intake-2597",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-1 -> P1 / DF2-12.1"
      ]
    },
    {
      "id": "intake-2598",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-1 -> P1 / DF2-12.1",
        "W4UP-2 -> P1 / DF2-12.1"
      ]
    },
    {
      "id": "intake-2599",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-3 -> P5 / TD-23.D1"
      ]
    },
    {
      "id": "intake-2600",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-3 -> P5 / TD-23.D1"
      ]
    },
    {
      "id": "intake-2601",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-3 -> P5 / TD-23.D1",
        "W4UP-4 -> M4"
      ]
    },
    {
      "id": "intake-2602",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-3 -> P5 / TD-23.D1",
        "W4UP-5 -> M4"
      ]
    }
  ],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "Production speculative roles (:8070 frontdoor MTP np 4, :8083 27B DFlash2 np 4) must stay token-exact under concurrency; promotion candidates must not regress it.",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) orchestration/model_registry.yaml:1787-1796 (frontdoor slots 4); handoffs/active/dflash2-block-drafter-experimental-build.md DF2-12 (open, np>1 untested); llama.cpp production tree @ ffc1bac82 (v10) src/models/delta-net-base.cpp:595-596 (unwritten snapshot slots), common/common.h:390-394 (rollback armed for MTP/DFlash)",
      "gap": "No np>1 token-identity record exists for either production speculative role; the upstream report on the same model family (llama.cpp #28286) closed without a root cause; the rollback test compares logits only.",
      "operational_change": "One temp-0 cross-slot run on both recipes with a slot-reuse arm, a state-hash conformance test, a passive collapse canary and a multi-prefill arm in the promotion gate.",
      "benefit_direction": "Detects or rules out silent cross-request contamination in served output; no throughput claim; serving shape unchanged unless a defect is found.",
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "execution_conditions": "Correctness windows on own scratch servers (no quiet host needed); experimental branch for the test changes; production activation unchanged; G2-CONC arm applies to the next promotion candidate.",
      "closure_basis": "Immediate; a divergence opens the snapshot-slot patch trigger (M1)."
    },
    "P2": {
      "project_objective": "Raise DFlash2 acceptance on the production 27B MI210 path and set the drafter-training data contract before any capture.",
      "implementation_ref": "llama.cpp production tree @ ffc1bac82 (v10) src/models/dflash.cpp:735-824 (rank-256 selector), common/speculative.cpp:1658-1700 (walk), common/sampling.cpp:740-766 (point-mass verify); handoffs/active/dflash2-block-drafter-experimental-build.md:196 DF2-DRAFTER-CAPABILITY and INF-62 hard-label contract",
      "gap": "No oracle-headroom or per-slot coverage number exists for the incumbent selector; the temp>0 branch samples proposals although point-mass proposals are lossless; the capture contract omits the teacher distribution.",
      "operational_change": "Offline lattice-headroom probe from one dump, an env-gated point-mass A/B, and an amended capture contract.",
      "benefit_direction": "Possible higher acceptance at no training cost; greedy output and the lattice ABI unchanged; distribution exactness gated by SPEC-PIT.1.",
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "execution_conditions": "Experimental build, off by default; one MI210 correctness window for the dump; A/B in a GPU window; contract edit is text only.",
      "closure_basis": "Immediate; a trained-selector port waits for the headroom rule (M1)."
    },
    "P3": {
      "project_objective": "AK keeps must be correct on the served shapes; the gate must catch faults that an aggregate NMSE over uniform inputs misses.",
      "implementation_ref": "epyc-inference-research autokernel evaluator/correctness.py:2377 (T0 gates), loop/gates.py:2990-3026, execution/t0_provider.py:305,3662 (race_detector_id=None); handoffs/active/autokernel-all-devices-all-dimensions.md AKX-ALL-31",
      "gap": "No race detector, no edge-value inputs, aggregate-only NMSE, no exhaustive dequant check, no GDN exactness oracle, no ISA record, planner sees no hardware counters.",
      "operational_change": "Add the families, bounds and checks to the existing gate chain and candidate record, each with a planted control.",
      "benefit_direction": "Fewer false keeps and better-grounded candidates; the champion incumbent and historical keeps must still pass.",
      "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
      "execution_conditions": "Experimental branches and the research repo; correctness work needs no quiet host; GPU mutant runs in a correctness window.",
      "closure_basis": "Immediate; a gfx90a race executor waits for the race-sensitivity result (M5)."
    },
    "P4": {
      "project_objective": "Choose the speech interlocutor and STT path on measured WER and latency (CS-8 bake-off).",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) src/voice/http_clients.py:28-31, src/voice/cascade.py (whisper :9000 -> qwentts :9002); handoffs/active/conversation-stack.md CS-8.STT5; llama.cpp production tree @ ffc1bac82 (v10) has no lfm3 arch, mtmd_audio_stream or server realtime",
      "gap": "Upstream llama.cpp now serves end-to-end audio models and a realtime API that our frozen tree lacks; no measurement exists on EPYC or the MI210.",
      "operational_change": "One isolated scratch upstream build, two STT arms on the pinned clips, and a realtime latency and cancel measurement.",
      "benefit_direction": "A possible lower-latency single-model speech path; frozen speech kernels untouched; vendor tables carry no weight.",
      "owner": "handoffs/active/conversation-stack.md",
      "execution_conditions": "Scratch build on llama.cpp-experimental with its own LD_LIBRARY_PATH and linkage proof; CPU quarter and an MI210 window; no production change.",
      "closure_basis": "Immediate; bake-off admission waits for the STT rule (M4)."
    },
    "P5": {
      "project_objective": "TD-23 needs one local compact decision backend; Jev techniques are a current focus.",
      "implementation_ref": "handoffs/active/typed-decision-plane.md:599 TD-23 (local backends only), :464 TD-18; llama.cpp production tree @ ffc1bac82 (v10) has no /v1/systemone (PR 29818 merge a4cb4c61 not an ancestor)",
      "gap": "No local backend is named for TD-23; decision probabilities depend on quant, batch cut and GGUF temperatures that the receipt does not pin.",
      "operational_change": "Name d1-2B as the backend arm and gate it on parity and batch invariance before any quality read; pin the GGUF in TD-18.",
      "benefit_direction": "A one-pass typed decider with probabilities instead of generated text; incumbent routing unchanged until TD-23 decides.",
      "owner": "handoffs/active/typed-decision-plane.md",
      "execution_conditions": "Scratch upstream build as an instrument; gates on a CPU quarter and HIP; the screen itself keeps TD-23 prerequisites and its mi210-window gate.",
      "closure_basis": "Immediate; generic readout and hybrid-prefix items are triggers (M4)."
    },
    "P6": {
      "project_objective": "Make the orchestrator agent loop cheaper and more accurate per task without new inference first.",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) src/repl_environment/routing.py:581 (4,000-char hand-off), :813; handoffs/active/agentic-serving-harness-fixes.md:670 (tool use 3.8-4.9% of turns); src/inference/prefix_index.py:36-38",
      "gap": "No measurement of which delegated roles could fold, how large the advertised tool surface is per role, or how much resident context old tool results hold.",
      "operational_change": "Three zero-inference screens from existing records and traces.",
      "benefit_direction": "Decides which later A/Bs are worth running; no serving change.",
      "owner": "handoffs/active/routing-intelligence.md",
      "execution_conditions": "Zero inference; reads existing records only.",
      "closure_basis": "Immediate; KV-drop and C2C work are triggers (M3)."
    },
    "P7": {
      "project_objective": "Belief-kernel gate decisions must be independently checkable.",
      "implementation_ref": "scripts/vidya/gate.py:130-166 (self-hash, label attestations); docs/design/vidya-pilot-spec.md section 11.2",
      "gap": "The certificate has no independent checker and its attestations carry labels, not digests.",
      "operational_change": "A standalone checker with forged-certificate tests.",
      "benefit_direction": "Forged or stale certificates are refused; no change to fold or grading.",
      "owner": "handoffs/active/vidya-belief-substrate-program.md",
      "execution_conditions": "Deterministic infrastructure; no compute.",
      "closure_basis": "Immediate."
    },
    "K1": {
      "project_objective": "Keep the speculative-decoding record accurate.",
      "implementation_ref": "llama.cpp production tree @ ffc1bac82 (v10) src/models/dflash.cpp:735-824; handoffs/active/dflash2-block-drafter-experimental-build.md:560 LiLiCorr monitor; handoffs/active/cpu-decode-roofline-program.md:86-88 Axis-E head on disk",
      "gap": "No missing behavior: the finding corrects or records context for an existing owner.",
      "operational_change": "Append the dated note to the owner (prose, no checkbox).",
      "benefit_direction": "Prevents re-deriving or mis-citing the finding.",
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "execution_conditions": "Text only at Stage 4.",
      "closure_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only."
    },
    "K2": {
      "project_objective": "Keep the roofline program honest about weight-reuse architectures.",
      "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md INF-70; llama.cpp production tree @ ffc1bac82 (v10) src/models/qwen3next.cpp:417 (beta sigmoid); handoffs/active/gpu-acceleration-path.md:248",
      "gap": "No missing behavior: the finding corrects or records context for an existing owner.",
      "operational_change": "Append the dated note to the owner (prose, no checkbox).",
      "benefit_direction": "Prevents re-deriving or mis-citing the finding.",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Text only at Stage 4.",
      "closure_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale."
    },
    "K3": {
      "project_objective": "Keep KV-reuse designs correct.",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) src/inference/prefix_index.py:36-38; llama.cpp production tree @ ffc1bac82 (v10) llama_state_seq_get_data/set_data",
      "gap": "No missing behavior: the finding corrects or records context for an existing owner.",
      "operational_change": "Append the dated note to the owner (prose, no checkbox).",
      "benefit_direction": "Prevents re-deriving or mis-citing the finding.",
      "owner": "handoffs/active/kv-prefix-fork-and-paged-attention.md",
      "execution_conditions": "Text only at Stage 4.",
      "closure_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack."
    },
    "K4": {
      "project_objective": "Avoid duplicate speech and decision work.",
      "implementation_ref": "handoffs/active/conversation-stack.md CS-8.STT2..STT6; handoffs/active/typed-decision-plane.md TD-23",
      "gap": "No missing behavior: the finding corrects or records context for an existing owner.",
      "operational_change": "Append the dated note to the owner (prose, no checkbox).",
      "benefit_direction": "Prevents re-deriving or mis-citing the finding.",
      "owner": "handoffs/active/conversation-stack.md",
      "execution_conditions": "Text only at Stage 4.",
      "closure_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence."
    },
    "K5": {
      "project_objective": "Keep AK agent loops leak-free and token-efficient.",
      "implementation_ref": "handoffs/active/agentic-rocm-kernel-authoring.md AK-PL-1; handoffs/active/autokernel-orchestrator-actor-backend.md",
      "gap": "No missing behavior: the finding corrects or records context for an existing owner.",
      "operational_change": "Append the dated note to the owner (prose, no checkbox).",
      "benefit_direction": "Prevents re-deriving or mis-citing the finding.",
      "owner": "handoffs/active/agentic-rocm-kernel-authoring.md",
      "execution_conditions": "Text only at Stage 4.",
      "closure_basis": "Retained: diagnostic feedback must come from a separate seed; agent-harness mode cost several times the tokens of plain refinement in PTXBench."
    },
    "M1": {
      "project_objective": "Escalate drafter work only on measured headroom.",
      "implementation_ref": "handoffs/active/dflash2-block-drafter-experimental-build.md DF2-LAT, DF2-12.1",
      "gap": "The useful step depends on a result or release that does not exist yet.",
      "operational_change": "Owned trigger prose only; no checkbox or index next action.",
      "benefit_direction": "Work starts only when its deciding condition holds.",
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "execution_conditions": "Materialize a task only when the named trigger fires in a reviewed session.",
      "closure_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test."
    },
    "M2": {
      "project_objective": "Consider looped models only when one can win on a bandwidth-bound host.",
      "implementation_ref": "handoffs/active/cpu-decode-roofline-program.md INF-70; upstream llama.cpp PR 25994 merged, PR 29823 open",
      "gap": "The useful step depends on a result or release that does not exist yet.",
      "operational_change": "Owned trigger prose only; no checkbox or index next action.",
      "benefit_direction": "Work starts only when its deciding condition holds.",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Materialize a task only when the named trigger fires in a reviewed session.",
      "closure_basis": "Triggers: a llama.cpp or vLLM PLT port, an independent LoopCoder-v2 replication, or a published PLT decode timing opens the Ouro/PLT CPU probe."
    },
    "M3": {
      "project_objective": "Edit or share KV only where context share justifies it.",
      "implementation_ref": "handoffs/active/context-folding-progressive.md CF-AKV-0; epyc-orchestrator main (read 2026-10-31) llama_memory_seq_rm/seq_add use",
      "gap": "The useful step depends on a result or release that does not exist yet.",
      "operational_change": "Owned trigger prose only; no checkbox or index next action.",
      "benefit_direction": "Work starts only when its deciding condition holds.",
      "owner": "handoffs/active/kv-prefix-fork-and-paged-attention.md",
      "execution_conditions": "Materialize a task only when the named trigger fires in a reviewed session.",
      "closure_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval."
    },
    "M4": {
      "project_objective": "Admit new speech or decision models only on our measurements.",
      "implementation_ref": "handoffs/active/conversation-stack.md CS-8, CS-22, CS-45; handoffs/active/typed-decision-plane.md TD-23",
      "gap": "The useful step depends on a result or release that does not exist yet.",
      "operational_change": "Owned trigger prose only; no checkbox or index next action.",
      "benefit_direction": "Work starts only when its deciding condition holds.",
      "owner": "handoffs/active/conversation-stack.md",
      "execution_conditions": "Materialize a task only when the named trigger fires in a reviewed session.",
      "closure_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest."
    },
    "M5": {
      "project_objective": "Build verification tooling only where the gate is blind.",
      "implementation_ref": "handoffs/active/rocm-verify-profile-backend.md RVP-RACE-1; handoffs/active/agentic-rocm-kernel-authoring.md C5-ISA-1",
      "gap": "The useful step depends on a result or release that does not exist yet.",
      "operational_change": "Owned trigger prose only; no checkbox or index next action.",
      "benefit_direction": "Work starts only when its deciding condition holds.",
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "execution_conditions": "Materialize a task only when the named trigger fires in a reviewed session.",
      "closure_basis": "Triggers: a GPU race mutant passing all 20 runs opens a gfx90a race-only symbolic executor; an ISA archive plus a compute-bound target opens an ISA-level lowering probe; a recurring rejection class (3 or more) opens a failure-to-rule loop."
    },
    "M6": {
      "project_objective": "Value of a thinking-length finetune of the CPU flagship.",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) orchestration/model_registry.yaml architect_general enable_thinking false; handoffs/active/architect-model-selection-bench.md:203-204",
      "gap": "The useful step depends on a result or release that does not exist yet.",
      "operational_change": "Owned trigger prose only; no checkbox or index next action.",
      "benefit_direction": "Work starts only when its deciding condition holds.",
      "owner": "handoffs/active/architect-model-selection-bench.md",
      "execution_conditions": "Materialize a task only when the named trigger fires in a reviewed session.",
      "closure_basis": "Trigger: the operator enables thinking on a Flash-Next role, or the architect bench reopens a thinking arm; then run the ThinkingCap IQ4_XS A/B with a shared-head arm."
    }
  },
  "opportunity_scan": [
    {
      "scan_id": "S1",
      "source_ref": "intake-2591 claims 0-2; intake-2577 claims 1-3; intake-2598 claim 4",
      "implementation_ref": "llama.cpp production tree @ ffc1bac82 (v10) delta-net-base.cpp:595; registry :8070/:8083",
      "mechanism": "Speculative rollback snapshot slots and simultaneous prefill can leak state across slots on GDN hybrids",
      "consumer": "np>1 speculative serving roles and the promotion gate",
      "application": "Cross-slot token-identity run, state-hash test, canary, multi-prefill arm",
      "disposition": "actionable",
      "ledger_ids": [
        "MEM-2",
        "SPEC2-1",
        "SPEC2-2",
        "W3SPEC-1",
        "W3SPEC-2",
        "W4UP-1",
        "W4UP-2"
      ],
      "basis": "Read the issue threads and our tree; no np>1 record exists."
    },
    {
      "scan_id": "S2",
      "source_ref": "intake-2561 claims 0,4,7,9; intake-2569 claims 0,5",
      "implementation_ref": "llama.cpp production tree @ ffc1bac82 (v10) dflash.cpp:735-824; speculative.cpp:1658-1700",
      "mechanism": "Candidate-lattice re-selection and point-mass proposals",
      "consumer": "DFlash2 drafter on :8083",
      "application": "Headroom probe and point-mass A/B",
      "disposition": "actionable",
      "ledger_ids": [
        "SPEC-1",
        "SPEC-2",
        "PRE-2560",
        "PRE-2561",
        "PRE-2569"
      ],
      "basis": "Incumbent already has a selector; headroom unmeasured."
    },
    {
      "scan_id": "S3",
      "source_ref": "intake-2548 claims 0-2; intake-2578 claims 0-2; intake-297 re-read",
      "implementation_ref": "handoffs/active/dflash2-block-drafter-experimental-build.md:196 and INF-62 contract",
      "mechanism": "Training draft heads against the target distribution on a frozen trunk",
      "consumer": "DF2-DRAFTER-CAPABILITY capture contract",
      "application": "Final-hidden tap and KL default",
      "disposition": "actionable",
      "ledger_ids": [
        "MTP-1",
        "PRE-2548",
        "PRE-2549"
      ],
      "basis": "The tap cannot be added after capture."
    },
    {
      "scan_id": "S4",
      "source_ref": "intake-2555 claims 1-3; intake-2570 claims 0-1; intake-2588; intake-2589",
      "implementation_ref": "epyc-inference-research AK evaluator/correctness.py:2377; t0_provider.py:305",
      "mechanism": "Verification and adversarial inputs for generated kernels; profile-grounded planning",
      "consumer": "AK correctness gate and planner",
      "application": "Edge families, worst-error bound, enumeration, race sensitivity, ISA record, counters",
      "disposition": "actionable",
      "ledger_ids": [
        "KERN-1",
        "KERN-10",
        "KERN-3",
        "KERN-4",
        "KERN-5",
        "KERN-6",
        "KERN-7",
        "MEM-1",
        "PRE-2550",
        "PRE-2555",
        "PRE-2556",
        "PRE-2557",
        "PRE-2570",
        "PRE-2574",
        "W2KERN-1",
        "W2KERN-3"
      ],
      "basis": "Gate gaps confirmed in code."
    },
    {
      "scan_id": "S5",
      "source_ref": "intake-2574 claims 2-3; intake-2550 claim 1",
      "implementation_ref": "llama.cpp production tree @ ffc1bac82 (v10) GATED_DELTA_NET test-backend-ops cases",
      "mechanism": "Exact addressable state writes in a delta-rule layer",
      "consumer": "GDN kernel tests and hybrid restore path",
      "application": "One-hot oracle and state-hash conformance",
      "disposition": "actionable",
      "ledger_ids": [
        "MEM-1",
        "MEM-2",
        "PRE-2550",
        "PRE-2574"
      ],
      "basis": "Current tests compare backends on random data only."
    },
    {
      "scan_id": "S6",
      "source_ref": "intake-2552; intake-2575; intake-2579; intake-2580",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) src/voice/cascade.py; handoffs/active/conversation-stack.md CS-8.STT5",
      "mechanism": "End-to-end audio LM and realtime server in upstream llama.cpp",
      "consumer": "Speech STT screen and voice controller",
      "application": "Scratch build, STT arms, realtime latency",
      "disposition": "actionable",
      "ledger_ids": [
        "PRE-2552",
        "PRE-2575",
        "SPEECH-1",
        "SPEECH-3",
        "W2SP-1",
        "W2SP-6"
      ],
      "basis": "Upstream path exists; no local measurement."
    },
    {
      "scan_id": "S7",
      "source_ref": "intake-2581..2583; intake-2593; intake-2595; intake-2599; intake-2602",
      "implementation_ref": "handoffs/active/typed-decision-plane.md TD-23, TD-18",
      "mechanism": "One-pass typed decision model served by /v1/systemone",
      "consumer": "TD-23 local backend and calibration receipt",
      "application": "Gated d1-2B backend arm and GGUF pin",
      "disposition": "actionable",
      "ledger_ids": [
        "AGENT-12",
        "AGENT-14",
        "PRE-2553",
        "W2SP-3",
        "W3DEC-1",
        "W3DEC-2",
        "W3DEC-3",
        "W3DEC-4",
        "W4UP-3"
      ],
      "basis": "TD-23 names no backend; probabilities depend on unpinned factors."
    },
    {
      "scan_id": "S8",
      "source_ref": "intake-2565 claims 0-3",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) src/repl_environment/routing.py:581",
      "mechanism": "Fold sub-agents into one loop only where evals say so; limit advertised tools",
      "consumer": "Orchestrator delegate() roles and REPL tool surface",
      "application": "Fold replay and tool-surface count",
      "disposition": "actionable",
      "ledger_ids": [
        "AGENT-1",
        "AGENT-2",
        "PRE-2565"
      ],
      "basis": "No per-role fold or tool-count data exists."
    },
    {
      "scan_id": "S9",
      "source_ref": "intake-2590 claims; intake-2596 claims 0-4; intake-2559; intake-2576",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) src/inference/prefix_index.py:36-38",
      "mechanism": "Dropping old tool results from KV; cross-model KV fusion",
      "consumer": "Agent-loop context and llama-server slots",
      "application": "Context-share screen first; KV-drop and C2C gated",
      "disposition": "actionable",
      "ledger_ids": [
        "W3DEC-7"
      ],
      "basis": "Size of the opportunity is unmeasured."
    },
    {
      "scan_id": "S10",
      "source_ref": "intake-2558 claims 0-2",
      "implementation_ref": "scripts/vidya/gate.py:130-166",
      "mechanism": "Untrusted engine emits a certificate; a small independent checker re-derives it",
      "consumer": "Vidya gate certificate",
      "application": "Standalone checker with forged tests",
      "disposition": "actionable",
      "ledger_ids": [
        "MEM-4",
        "MEM-6",
        "PRE-2558"
      ],
      "basis": "Certificate is self-hashed today."
    },
    {
      "scan_id": "S11",
      "source_ref": "K-packet findings across dives",
      "implementation_ref": "owners named per note",
      "mechanism": "Corrections and context with no missing behavior",
      "consumer": "Handoff readers",
      "application": "Dated notes",
      "disposition": "context-only",
      "ledger_ids": [
        "AGENT-10",
        "AGENT-4",
        "AGENT-6",
        "AGENT-8",
        "KERN-9",
        "LOOP-1",
        "LOOP-2",
        "LOOP-3",
        "LOOP-5",
        "MTP-3",
        "PRE-2545",
        "PRE-2547",
        "PRE-2551",
        "PRE-2562",
        "PRE-2571",
        "PRE-2573",
        "SPEC-4",
        "SPEC-6",
        "SPEC2-4",
        "SPEC2-5",
        "SPEECH-5",
        "SPEECH-6",
        "TCAP-2",
        "W2KERN-2",
        "W2KERN-6",
        "W2LOOP-3",
        "W2LOOP-4",
        "W2SP-2",
        "W2SP-4",
        "W3DEC-5",
        "W3DEC-6",
        "W3SPEC-4",
        "W3SPEC-x"
      ],
      "basis": "Each retains a correction or context; no consumer gap."
    },
    {
      "scan_id": "S12",
      "source_ref": "M-packet findings across dives",
      "implementation_ref": "owners named per trigger",
      "mechanism": "Follow-ons that depend on an unmet condition",
      "consumer": "Trigger owners",
      "application": "Owned trigger prose",
      "disposition": "covered",
      "ledger_ids": [
        "AGENT-13",
        "AGENT-3",
        "AGENT-5",
        "AGENT-7",
        "KERN-2",
        "KERN-8",
        "LOOP-4",
        "LOOP-6",
        "MTP-2",
        "MTP-4",
        "PRE-2546",
        "PRE-2554",
        "PRE-2559",
        "PRE-2564",
        "PRE-2567",
        "PRE-2568",
        "PRE-2572",
        "PRE-2576",
        "SPEC-3",
        "SPEC-5",
        "SPEC2-3",
        "SPEECH-2",
        "SPEECH-4",
        "SPEECH-7",
        "TCAP-1",
        "TCAP-3",
        "W2KERN-4",
        "W2KERN-5",
        "W2LOOP-1",
        "W2LOOP-2",
        "W2SP-5",
        "W3DEC-8",
        "W3SPEC-3",
        "W4UP-4",
        "W4UP-5"
      ],
      "basis": "Covered by named triggers under the deciding tasks."
    },
    {
      "scan_id": "S13",
      "source_ref": "declined rows",
      "implementation_ref": "see decline reasons",
      "mechanism": "Techniques without a viable consumer here",
      "consumer": "none",
      "application": "none",
      "disposition": "declined",
      "ledger_ids": [
        "AGENT-11",
        "AGENT-9",
        "KERN-11",
        "MEM-3",
        "MEM-5",
        "MTP-5",
        "PRE-2563",
        "PRE-2566",
        "TCAP-4",
        "W2KERN-7"
      ],
      "basis": "Explicit grounded declines."
    }
  ],
  "actionable_additions": [],
  "steering_reconciliation": [
    {
      "seq": 1,
      "stage": 1,
      "ts": "2026-10-31T21:20:00Z",
      "verbatim": "Accept all recommended deep dives and literature expansions for up to six stage 2 waves.",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Governed Stage-2 scope: four waves run of six permitted; every medium+ source dived; Stage-2b declines recorded with reasons."
    },
    {
      "seq": 2,
      "stage": 1,
      "ts": "2026-10-31T21:40:00Z",
      "verbatim": "Operator correction, which overrides the \"Context for grounding\" section of your brief: the subagent fan-out policy is NOT the point of these sources. Drop that framing, and treat the handoff pointers I gave you only as examples, not as the scope. Explore freely and widely how each source's insights could improve the CAPABILITY and PERFORMANCE of our production stack. That covers the models, the llama.cpp kernels and serving on the EPYC + MI210, speculative decoding, the orchestrator's routing, agent loops and REPL, speech, compilers and verification tooling, and anything else the evidence supports. Ground each recommendation in the current implementation, by reading the relevant handoffs, the code in /workspace/repos/epyc-orchestrator, and the research repo. Prefer concrete, measurable changes and bounded deciding probes.",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Applied as the scoring and grounding lens: every packet names the current implementation it changes (registry, llama.cpp tree, AK gate, voice cascade, REPL routing) and a deciding probe."
    }
  ],
  "outcome_reviews": {
    "W3SPEC-1": {
      "required_outcome": "Bounded probe (own scratch server, GPU correctness window, no region-lock needed per CORRECTNESS rule): on the production 27B shape (Q8_0, DFlash2 n-max 7, np 4, kv-unified, q8 KV, ROCm0) and on the frontdoor shape (Qwen3.6-35B-A3B-MTP Q8_0, draft-mtp n 4, np ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-12.1",
          "task_text": "- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary.",
          "acceptance": "Both shapes and the slot-reuse arm run with all controls after a passing rollback test; per-request outputs, per-round rollback logs, near-tie/degenerative labels and the manifest sha256 retained; a stated verdict per shape under the predeclared rule."
        }
      ]
    },
    "W3SPEC-2": {
      "required_outcome": "Fold the DF2-12 row and W3SPEC-1 into one run; add the frontdoor :8070 MTP np4 shape (not covered by DF2-12, which names only Qwen3.8-27B DFlash2) and the cross-content canary.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-12.1",
          "task_text": "- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary.",
          "acceptance": "Both shapes and the slot-reuse arm run with all controls after a passing rollback test; per-request outputs, per-round rollback logs, near-tie/degenerative labels and the manifest sha256 retained; a stated verdict per shape under the predeclared rule."
        }
      ]
    },
    "W4UP-1": {
      "required_outcome": "Temp-0 np>1 token-identity probe on :8070 (MTP np4) and :8083 (DFlash2 np4): per slot compare against an np=1 cold run of the same prompt AND the same np4 server with speculation off; include (i) mixed spec/non-spec interleaving, (ii) slot reuse: slot k ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-12.1",
          "task_text": "- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary.",
          "acceptance": "Both shapes and the slot-reuse arm run with all controls after a passing rollback test; per-request outputs, per-round rollback logs, near-tie/degenerative labels and the manifest sha256 retained; a stated verdict per shape under the predeclared rule."
        }
      ]
    },
    "W4UP-2": {
      "required_outcome": "Run tests/test-recurrent-state-rollback (CPU, correctness only, no quiet host needed) on our qwen4exp-capable experimental binary with the frontdoor GGUF; require dirty-ctx and multi-seq split replay both pass. Prove binary freshness vs commit 0771238438 ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-12.1",
          "task_text": "- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary.",
          "acceptance": "Both shapes and the slot-reuse arm run with all controls after a passing rollback test; per-request outputs, per-round rollback logs, near-tie/degenerative labels and the manifest sha256 retained; a stated verdict per shape under the predeclared rule."
        }
      ]
    },
    "MEM-2": {
      "required_outcome": "Add a state-level conformance check to the hybrid checkpoint/fork path: after a restore (common_prompt_checkpoint load_tgt, or KPF fork from a checkpoint) serialise the recurrent half of source and destination with llama_state_seq_get_data_ext(PARTIAL_ONLY) ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; KPF-RS-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/kv-prefix-fork-and-paged-attention.md",
          "task_id": "KPF-RS-1",
          "task_text": "- [ ] **KPF-RS-1 — Recurrent-state hash conformance after checkpoint restore and fork (intake-2574#record, intake-2591#record).** On an experimental champion-derived branch, extend `test-recurrent-state-rollback` and the KPF fork path to hash the full recurrent state (all Gated-DeltaNet state tensors and every snapshot slot, written and unwritten) after a checkpoint restore, after a fork from a checkpoint, and after a speculative rollback at np 1 and np 4, and compare against the state reached by re-prefilling the same tokens. Today the test compares logits to 1e-5 only, which can pass while an unwritten snapshot slot carries another sequence's state. Include a planted mutation (skip one snapshot write) that must fail. CPU and gfx90a legs.",
          "acceptance": "State hashes match re-prefill on every restore, fork and rollback case on both legs, the planted mutation fails, and any mismatch is filed with the case that produced it."
        }
      ]
    },
    "SPEC2-1": {
      "required_outcome": "Add a per-request MTP health canary to the Flash-Next serving gate: flag any request with >=64 drafted tokens and zero accepted, or a repeated n-gram window in the generated tail (reuse coherence_gate tiers 0-2), and log per-request accepted/drafted from ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; SPEC-CANARY.1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/speculative-decoding-mtp-refresh.md",
          "task_id": "SPEC-CANARY.1",
          "task_text": "- [ ] **SPEC-CANARY.1 — Per-request acceptance-collapse canary for every speculative serving role (intake-2577#record).** In the orchestrator's llama-server telemetry, flag any request with at least 64 drafted tokens and zero accepted, and any request whose last 256 generated tokens repeat one n-gram block, recording role, port, slot, n_parallel, draft settings and request id. Ship it as a passive counter with a dashboard health field; it changes no serving behaviour. Test it with a replayed log containing a planted zero-acceptance run and a planted repetition tail.",
          "acceptance": "Counter live on all speculative roles, both planted cases flagged in the replay test, zero flags on a clean replay, dashboard field registered with its freshness envelope."
        }
      ]
    },
    "SPEC2-2": {
      "required_outcome": "Extend G2-CONC with a simultaneous-multi-prefill probe: c in {2,3,5} identical-length prompts differing by a salt, issued at the same instant, temp 0, ignore-eos 128 tokens, MTP on vs MTP off, compare every request token-for-token to its solo -np 1 output; ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; G2-CONC.MP carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/cpu-decode-roofline-program.md",
          "task_id": "G2-CONC.MP",
          "task_text": "- [ ] **G2-CONC.MP — Add a simultaneous multi-prefill arm to the G2-CONC promotion gate (intake-2577#record).** For every speculative recipe on the promotion candidate binary: c in {2, 3, 5} equal-length prompts that differ only by a salt, issued at the same instant, temp 0, speculation on and off, each output compared token for token with a solo np-1 run. The vLLM defect on the same model family corrupted state only when two or more prompts prefilled in one scheduler step, which a staggered concurrency test never exercises.",
          "acceptance": "G2-CONC carries the multi-prefill arm with both speculation states, and a candidate cannot pass G2-CONC while any arm diverges."
        }
      ]
    },
    "SPEC-1": {
      "required_outcome": "DF2-LAT zero-training lattice-headroom probe. (i) Experimental build from the current champion tip, env-gated and off by default: append the 16 unary draft logits to each packed DFlash2 lattice row (src/models/dflash.cpp build_post_sampling; row is K+K*K=272 ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-LAT",
          "task_text": "- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor.",
          "acceptance": "Dump instrument merged off-by-default with a symbol-absent rebuild check; arm B reproduces live accepted counts; H with interval reported per split; verdict recorded under the rule."
        }
      ]
    },
    "SPEC-2": {
      "required_outcome": "DF2-PM point-mass proposal screen at production temperature. Behind an env knob in the experimental build, the DFlash2 temp>0 branch takes the argmax selector walk instead of sampling softmax(scores/T), and emits dist {id, prob 1.0} per slot. The existing ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-PM carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-PM",
          "task_text": "- [ ] **DF2-PM — Point-mass draft proposals at production temperature (intake-2561#record).** Behind an env knob on the experimental build, make the DFlash2 temp>0 branch propose the argmax selector walk with a point-mass distribution instead of sampling softmax(scores/T); the verifier then accepts with p_target(draft) and resamples from the residual (common/sampling.cpp:740-766), which is lossless. A/B against the stock sampled walk on the DF2-4 protocol (12 prompts, temp 0.6, top-p 0.95, top-k 20) at np 1 and np 4, at least 5 interleaved pairs; primary metric weighted acceptance, secondary tok/s; the SPEC-PIT.1 distribution gate must pass. Adopt into the next champion fold only if weighted acceptance improves by at least 3% in at least 4 of 5 pairs at both np values, tok/s does not regress and SPEC-PIT.1 passes; otherwise record the per-pair numbers and close.",
          "acceptance": "Knob merged off-by-default; five interleaved pairs at np 1 and np 4 retained; SPEC-PIT.1 result attached; adopt-or-close verdict under the rule."
        }
      ]
    },
    "MTP-1": {
      "required_outcome": "Amend the DF2-DRAFTER-CAPABILITY trainer and data contract (the INF-62 record contract inherited from the cancelled DF2-QWOPUS) so the default objective is forward-KL self-distillation to the target's own teacher-forced NTP distribution rather than hard ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-DRAFTER-CAPABILITY.OBJ carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-DRAFTER-CAPABILITY.OBJ",
          "task_text": "- [ ] **DF2-DRAFTER-CAPABILITY.OBJ — Fix the drafter-training data contract before any capture (intake-2548#record, intake-2578#record, intake-297#record).** Amend the capture contract inherited from INF-62 (\"hard next-token labels\") so every feature dump also taps the target's final post-norm hidden state (5120 x bf16 = 10,240 bytes per token, +20% over the current taps), which yields the exact teacher distribution through the frozen output head. Make forward KL toward the target distribution the default objective with hard labels as the fallback arm (with a frozen trunk, Soft-MTP's gradient equals direct forward KL), and record the Nemotron 3 Ultra frozen-backbone recipe (temperature 2, hidden states sampled from earlier draft steps) as an option. Note that z-lab/dflash @ 07ebd93 ships no training code, so any drafter or selector training is research, not a port.",
          "acceptance": "Contract text amended in the handoff with the tap, default objective, fallback arm and recipe option; the capture script refuses to start without the final-hidden tap."
        }
      ]
    },
    "KERN-3": {
      "required_outcome": "Add structured edge-value input families to the AK op suite beside the AK_SENS scale transforms. Families: f16-range near-max (overflow), subnormal-scale (underflow), cancellation pairs within reduction rows, softmax rows that are all-equal or contain -inf, ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.EDGE",
          "task_text": "- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework.",
          "acceptance": "All families and the max-error bound run by default on CPU and HIP, every seeded twin is red, the champion incumbent and all historical keeps pass."
        }
      ]
    },
    "KERN-5": {
      "required_outcome": "Add a per-element worst-error bound next to NMSE on the GPU served-shape case set. Calibrate the anchor's max-abs error per (op, type, shape) over 5 seeds and gate on k x anchor, the way the CPU_REPACK oracle already does.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.EDGE",
          "task_text": "- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework.",
          "acceptance": "All families and the max-error bound run by default on CPU and HIP, every seeded twin is red, the champion incumbent and all historical keeps pass."
        }
      ]
    },
    "W2KERN-3": {
      "required_outcome": "Close the verified AK gate gaps (no race detector, race_detector_id=None; no edge-value inputs; NMSE-only oracle) with a CAKE-style pre-GPU static filter tier: run the cheapest hazard/legality checks (LDS barrier ordering, wave64/exec-mask hazards from the ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.EDGE",
          "task_text": "- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework.",
          "acceptance": "All families and the max-error bound run by default on CPU and HIP, every seeded twin is red, the champion incumbent and all historical keeps pass."
        }
      ]
    },
    "KERN-4": {
      "required_outcome": "Exhaustive bit-level decode check per served quant type (Q4_K, Q6_K, IQ2_*, IQ3_*, IQ4_XS, MXFP4). Enumerate the full per-element code space (quant codes x sub-block scale/min codes) at d/dmin in {0, subnormal, 1, f16 max}. Compare the candidate CPU (AVX-512) ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.QDEC carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.QDEC",
          "task_text": "- [ ] **AKX-ALL-31.QDEC — Exhaustive code-space decode check per served quant type (intake-2555#record).** For Q4_K, Q6_K, Q8_0, IQ2_*, IQ3_*, IQ4_XS and MXFP4, enumerate every per-element code together with every scale and min value that occurs in the served GGUFs, decode through the CPU and HIP dequant paths, and compare bit-for-bit with a scalar reference. First report how much of the code space the current random suite reaches; bit-level dequant is exactly the class an equivalence checker cannot prove, so enumeration is the sound substitute.",
          "acceptance": "Coverage of the current suite reported per type; full enumeration passes bit-exact on both legs, or each mismatch is filed with type, code and backend."
        }
      ]
    },
    "MEM-1": {
      "required_outcome": "Add a deterministic one-hot RAM oracle case to the GATED_DELTA_NET tests of an EXPERIMENTAL champion-derived llama.cpp branch (tests/test-backend-ops.cpp test_gated_delta_net family, or a sibling test-gdn-ram): alpha=1 (g=0), beta=1, one-hot k and q, ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.GDN carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.GDN",
          "task_text": "- [ ] **AKX-ALL-31.GDN — Deterministic one-hot GATED_DELTA_NET state oracle (intake-2574#record, intake-2550#record).** Add a test-backend-ops case on an experimental champion-derived branch that drives the delta rule with gate held at 1, beta at 1 and one-hot keys, so each step overwrites exactly one state row and a one-hot query must read back that row; compare against the closed-form result. Cover CPU f32, gfx90a f32 and BF16 state, and K > 1 snapshot slots. The current cases only compare backends on random data, which cannot detect a shared indexing error.",
          "acceptance": "Oracle case passes exactly on every leg and slot count, with a planted index-off-by-one mutant that fails."
        }
      ]
    },
    "KERN-1": {
      "required_outcome": "Race-sensitivity mutation control for the GPU correctness gate. In a llama.cpp-experimental worktree, build 3 seeded-race HIP mutants, each deleting one __syncthreads/barrier: MMQ tile load, MMVQ partial-sum reduction, FA tile softmax. Run the existing AK ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree build three seeded-race HIP mutants, each deleting one barrier in MMQ, MMVQ and the FA kernel, and run the served-shape suite 20 times each. CPU: build test-backend-ops with ThreadSanitizer, using LLVM libomp with Archer annotations, and run the threaded ops. Decision rule: if any GPU mutant passes the gate in all 20 runs, open the gfx90a race-only symbolic-executor trigger; if all are caught, record the gate as race-sensitive at these sites. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant pass/fail counts over 20 runs, the TSAN report on the anchor, and the stated verdict."
        }
      ]
    },
    "KERN-10": {
      "required_outcome": "Wire a CPU race detector for routes touching threading. Build a TSAN test-backend-ops (CPU), using LLVM libomp with Archer annotations because production uses OpenMP; GGML_OPENMP=OFF would test a different threading path. Run it on the v10 anchor first.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree build three seeded-race HIP mutants, each deleting one barrier in MMQ, MMVQ and the FA kernel, and run the served-shape suite 20 times each. CPU: build test-backend-ops with ThreadSanitizer, using LLVM libomp with Archer annotations, and run the threaded ops. Decision rule: if any GPU mutant passes the gate in all 20 runs, open the gfx90a race-only symbolic-executor trigger; if all are caught, record the gate as race-sensitive at these sites. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant pass/fail counts over 20 runs, the TSAN report on the anchor, and the stated verdict."
        }
      ]
    },
    "KERN-6": {
      "required_outcome": "Counter-grounded planner signals. For the top-1 hotspot kernel of each GPU screen, capture a fixed, declared counter subset via rocprofv2 (from the proven 465-counter taxonomy). Attach it to the hotspots rows. Adopt TAIC's rule that each hypothesis cites a ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-CTR-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-CTR-1",
          "task_text": "- [ ] **RVP-CTR-1 — Counter-grounded planner signals for the GPU AK lane (intake-2556#record).** For the top hotspot kernel of each GPU screen, capture a fixed declared counter subset with rocprofv2 (occupancy, LDS bank conflicts, VALU/MFMA busy, memory unit stall, achieved bandwidth) and pass it to the planner with the rule that every proposed idea must cite a counter that is present, and a missing counter may not be treated as zero. Compare 2 planner rounds with and without counters on the same target and budget.",
          "acceptance": "Counter capture recorded per screen; planner inputs carry the counters; the with/without comparison reports accepted-keep rate and wasted candidates on the same budget."
        }
      ]
    },
    "KERN-7": {
      "required_outcome": "Archive the hipcc AMDGCN ISA (--save-temps .s, or llvm-objdump of the code object) of the touched kernels into every AK GPU candidate record, next to the source diff and the hotspots table.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; C5-ISA-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/agentic-rocm-kernel-authoring.md",
          "task_id": "C5-ISA-1",
          "task_text": "- [ ] **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).** Store the hipcc --save-temps .s (or llvm-objdump of the code object) of each touched kernel in the candidate record next to its source diff. When a candidate claims a mechanism (MFMA, LDS staging, buffer loads), confirm in the ISA, and with a rocprof instruction counter where one exists, that the instruction executes on the measured path; a candidate whose claimed instruction is absent is refused.",
          "acceptance": "Every GPU candidate record carries its ISA; the mechanism check refuses a planted candidate whose claimed MFMA path never executes."
        }
      ]
    },
    "W2KERN-1": {
      "required_outcome": "Add an instruction-executed gate to the AMD kernel-authoring path: when a candidate claims a mechanism (MFMA use, LDS staging, buffer/global load width), require a rocprof instruction-mix counter or ISA-disassembly execution check on the real workload before ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; C5-ISA-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/agentic-rocm-kernel-authoring.md",
          "task_id": "C5-ISA-1",
          "task_text": "- [ ] **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).** Store the hipcc --save-temps .s (or llvm-objdump of the code object) of each touched kernel in the candidate record next to its source diff. When a candidate claims a mechanism (MFMA, LDS staging, buffer loads), confirm in the ISA, and with a rocprof instruction counter where one exists, that the instruction executes on the measured path; a candidate whose claimed instruction is absent is refused.",
          "acceptance": "Every GPU candidate record carries its ISA; the mechanism check refuses a planted candidate whose claimed MFMA path never executes."
        }
      ]
    },
    "SPEECH-1": {
      "required_outcome": "Bounded probe LFM3-1: build an experimental llama.cpp tree (fresh v10 + upstream b11960 audio path: PRs 31252, 30629, 30636, 31257, 31269, 31287, 31386) on CPU only first; run LFM3-Audio-2B Q8_0 ASR over the 40 pinned FLEURS clips (en/it/de/fr x10) and ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/conversation-stack.md",
          "task_id": "CS-8.STT8",
          "task_text": "- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence.",
          "acceptance": "Scratch build proven by the linkage check on both devices; both arms scored on the same pinned clips with per-clip outputs retained; advance or reject per arm under the rule."
        }
      ]
    },
    "SPEECH-3": {
      "required_outcome": "Estimate and record forward-port cost: experimental branch from current production-consolidated-v10, merge/cherry-pick the 7 LFM3 audio PRs plus their upstream prerequisites (b10303..b11960 is 1657 builds; PR 31257 alone +2721/-160 over 31 files, 30629 +998, ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/conversation-stack.md",
          "task_id": "CS-8.STT8",
          "task_text": "- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence.",
          "acceptance": "Scratch build proven by the linkage check on both devices; both arms scored on the same pinned clips with per-clip outputs retained; advance or reject per arm under the rule."
        }
      ]
    },
    "W2SP-6": {
      "required_outcome": "Add a Voxtral-Mini-4B-Realtime GGUF through mtmd-cli run_audio_stream arm to the CS-8.STT5 screen (ranks and rejects only) on a scratch upstream build; record encoder and decoder times separately as the CLI already prints them.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/conversation-stack.md",
          "task_id": "CS-8.STT8",
          "task_text": "- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence.",
          "acceptance": "Scratch build proven by the linkage check on both devices; both arms scored on the same pinned clips with per-clip outputs retained; advance or reject per arm under the rule."
        }
      ]
    },
    "W2SP-1": {
      "required_outcome": "Build upstream master (or tag b11960+) as a SCRATCH llama-server on llama.cpp-experimental from fresh production; run examples/realtime_client.py with LFM3-Audio-2B Q8_0 and Q4_0 on the EPYC CPU and MI210 and record first-output-after-end-of-input, with a ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.RT1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/conversation-stack.md",
          "task_id": "CS-8.RT1",
          "task_text": "- [ ] **CS-8.RT1 — /v1/realtime first-output latency and turn contract on EPYC and MI210 (intake-2579#record, intake-2575#record).** With the CS-8.STT8 scratch build, run the upstream realtime client against LFM3-Audio-2B on a CPU quarter and on the MI210, and measure time from end of input audio to first output audio over a frozen set of 20 utterances, plus barge-in: response.cancel latency to silence. The server does no turn detection (turn_detection is null), so the test drives commit, response.create and response.cancel from the client exactly as the CS-22 controller would. Compare against the cascade measured on the same utterances.",
          "acceptance": "Per-utterance latencies for both devices and the cascade, cancel-to-silence times, and a written note on which CS-22 controller messages the realtime backend needs."
        }
      ]
    },
    "AGENT-12": {
      "required_outcome": "Screen d1-Omni-2B-GGUF (Q8_0, 1.85 GB) and d1-2B-GGUF as local typed-decision backends on a separate, scratch-built upstream llama-server (b11960+ in its own build dir; production tree untouched). Probe: replay a frozen set of already-routed orchestrator ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "AGENT-14": {
      "required_outcome": "Read LFM Open License v1.0 and the Open d1 blog before any use beyond a screen (licence is not Apache/MIT; sourcing policy is open-source only).",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "W2SP-3": {
      "required_outcome": "TD-23 screen: d1-2B-GGUF Q8_0 via /v1/systemone (scratch upstream build, CPU quarter or MI210 window) versus the constrained incumbent readout, on a frozen, row-pinned labelled routing set (the TD-11 / CJ-15 sealed workload; labels from the routing-replay ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "W3DEC-1": {
      "required_outcome": "Add a precision-and-backend parity gate to the TD-23 decision-backend screen BEFORE any quality or calibration number is read: for the chosen decision GGUF (d1-2B Q8_0 first), serve the BF16 file on CPU as reference, then Q8_0 on CPU, Q8_0 on HIP (MI210), and ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "W3DEC-2": {
      "required_outcome": "Add a batch-/schedule-invariance gate to the same screen: serve with -np 3, -b = -ub = 2048 (state must fit one ubatch), send request A alone (x5), then A concurrently with a shorter, a longer and an identical companion (x5 each, with a blocker request to ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "W3DEC-3": {
      "required_outcome": "Plan the build route for any /v1/systemone work: the frozen v10 tree has neither the endpoint (PR 29818 merge a4cb4c61 is not an ancestor of ffc1bac82; no systemone string; no *decision* file in tools/server) nor LFM3 (needs >= b11960). Cheapest honest route ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "W4UP-3": {
      "required_outcome": "d1 decision-model screen build must include a4cb4c61fd (#29818 systemone API) and 7e3eeee048 (#30361) if H2O-Lightning-4B is screened; cbe28bb3 (#30408) only for non-causal/embedding-mode decision models at np>1; 7e8324f5 (#30100) is Metal-only and NOT needed ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "W3DEC-4": {
      "required_outcome": "Record in the TD-18 calibration receipt the model pin that determines the probabilities: GGUF sha256, every decision.temperature.* metadata key/value (read with gguf-dump), llama.cpp build SHA, -b/-ub/-np, and the question kind plus option count (some ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-18.1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-18.1",
          "task_text": "- [ ] **TD-18.1 — Pin GGUF decision backends in the TD-18 calibration receipt (intake-2593#record).** For llama.cpp decision backends, the receipt records the GGUF sha256, every decision.temperature.* metadata value (the endpoint scales probabilities by them and exposes no request-time override), the server build commit, and the -np/-b/-ub flags, because each of these changes the probabilities being calibrated.",
          "acceptance": "Receipt schema carries the four fields and a receipt written without them is refused."
        }
      ]
    },
    "AGENT-1": {
      "required_outcome": "Run the fold article procedure as a zero-inference REPLAY over existing delegation records: for each delegate() role (worker_math, worker_general, worker_summarize, worker_vision, coder_escalation) compute from _delegations artifacts / delegation reports the ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RI-25 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/routing-intelligence.md",
          "task_id": "RI-25",
          "task_text": "- [ ] **RI-25 — Zero-inference fold replay over delegation records (intake-2565#record).** Apply the fold criteria (fold a sub-agent only if the folded version does not score worse; inspect which tasks flip; repeat runs) to existing orchestrator delegation records: for each delegate() role (worker_math, worker_general, worker_summarize share one model), measure from records how often a chain needs the role's own context, how much of the 4,000-character truncated hand-off (src/repl_environment/routing.py:581) reaches the worker, and how often the delegated answer is re-asked by the caller. Output a per-role fold-candidate table; no serving change.",
          "acceptance": "Per-role table with denominators over a frozen record manifest, and a one-line fold/keep recommendation per role for a later inference A/B."
        }
      ]
    },
    "AGENT-2": {
      "required_outcome": "Count and cap the model-visible tool surface: REPL exposes ~55 globals (peek, grep, delegate, escalate, run_shell, registry_*, benchmark_*, ...) in environment.py _build_globals while tool_registry.yaml holds 55 further tools (TOOL/CALL/list_tools = already ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; UFH14-TOOLS-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/agentic-serving-harness-fixes.md",
          "task_id": "UFH14-TOOLS-1",
          "task_text": "- [ ] **UFH14-TOOLS-1 — Count and cap the model-visible tool surface per role (intake-2565#record).** Enumerate what each role's prompt actually advertises (about 55 REPL globals plus about 55 registry tools behind TOOL/CALL) and log the count per role and per turn. Frontdoor turns called a tool in only 3.8-4.9% of turns (this handoff, line 670), so a large advertised surface costs prompt tokens for little use. Propose a per-role allowlist with deferred loading for the rest, behind a flag, for a later A/B.",
          "acceptance": "Per-role advertised tool count recorded; the allowlist exists behind a default-off flag with a test that the default prompt is unchanged."
        }
      ]
    },
    "W3DEC-7": {
      "required_outcome": "Zero-inference size screen before any AKV-style work: from existing orchestrator serving records and autopilot/REPL traces, compute for long agent loops the share of resident context tokens that are tool responses older than the latest 12 (the paper's drop ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CF-AKV-0 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-folding-progressive.md",
          "task_id": "CF-AKV-0",
          "task_text": "- [ ] **CF-AKV-0 — Zero-inference screen: how much resident context old tool results hold (intake-2590#record, intake-2596#record).** From existing orchestrator serving records and REPL traces, compute per long agent loop the share of resident context held by tool responses older than the last two turns, and the share of decode steps above 48K context. Escalate to the trigger-gated KV-drop semantics probe only if the median long loop holds at least 40% old tool results and at least 20% of decode steps exceed 48K tokens.",
          "acceptance": "Shares reported over a frozen trace manifest with the full denominator, and the escalation decision stated."
        }
      ]
    },
    "MEM-4": {
      "required_outcome": "Write scripts/vidya/cert_check.py: a standalone verifier for the gate's epyc.vidya/certificate/v1, sharing NO imports with fold.py, gate.py or lattice.py. It reads the ledger JSONL and the ratified policy file directly, re-derives pro/con grade dominance and ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; VB-CERT-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/vidya-belief-substrate-program.md",
          "task_id": "VB-CERT-1",
          "task_text": "- [ ] **VB-CERT-1 — Independent checker for the gate certificate (intake-2558#record).** Write scripts/vidya/cert_check.py, a standalone verifier of epyc.vidya/certificate/v1 that shares no imports with fold.py, gate.py or lattice code, re-derives the verdict from the certificate's stated inputs, and compares certificate.frontier and as_of explicitly. Today certificate_hash is a self-hash and input_attestations holds labels rather than the digests the spec section 11.2 requires (scripts/vidya/gate.py:130-166). Add forged-certificate tests (altered verdict, swapped frontier, stale as_of, label-only attestation) that must be rejected.",
          "acceptance": "Checker passes every genuine certificate in the current ledger sample and rejects every forged case; the label-versus-digest gap is either fixed in gate.py or recorded as a refusal reason."
        }
      ]
    },
    "MEM-6": {
      "required_outcome": "When writing MEM-4, make the checker read and compare certificate.frontier and as_of explicitly and record in the certificate's proves-field that a certificate binds to a frontier, not to the truth of the world.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; VB-CERT-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/vidya-belief-substrate-program.md",
          "task_id": "VB-CERT-1",
          "task_text": "- [ ] **VB-CERT-1 — Independent checker for the gate certificate (intake-2558#record).** Write scripts/vidya/cert_check.py, a standalone verifier of epyc.vidya/certificate/v1 that shares no imports with fold.py, gate.py or lattice code, re-derives the verdict from the certificate's stated inputs, and compares certificate.frontier and as_of explicitly. Today certificate_hash is a self-hash and input_attestations holds labels rather than the digests the spec section 11.2 requires (scripts/vidya/gate.py:130-166). Add forged-certificate tests (altered verdict, swapped frontier, stale as_of, label-only attestation) that must be rejected.",
          "acceptance": "Checker passes every genuine certificate in the current ledger sample and rejects every forged case; the label-versus-digest gap is either fixed in gate.py or recorded as a refusal reason."
        }
      ]
    },
    "SPEC-4": {
      "required_outcome": "Prepare a text update (owning session applies) to the LiLiCorr monitor paragraph: name DCOCO (intake-2561#record) and Domino (intake-2569#record) as the same correction family; record that DFlash2 already ships a learned K=16 rank-256 selector lattice with a ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "SPEC-6": {
      "required_outcome": "CPU: no separate action. The 27B DFlash2 path is served on the MI210 only, and CPU speculative work for Flash-Next is MTP (Axis E). If SPEC-3 is ever built, its graph ops are backend-agnostic and must pass CPU no-regression in the four-step workflow.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "SPEC2-4": {
      "required_outcome": "Add to DF2-DRAFTER-CAPABILITY the Nemotron Sec 3.4 head/drafter fine-tune recipe as an option: freeze target, sample hidden states from earlier draft steps, forward-KL T=2 to target logits on target on-policy rollouts at temp 1 (reference scale: 12K steps, bs ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "SPEC2-5": {
      "required_outcome": "Answer only (no entry): the z-lab card text does not say how the DFlash2 selector (top-16, rank-256 transition score) was trained, and reports no tau gain over DFlash 1 for Qwen3.8-27B. The inco.ai blog (sha256-12 99dc56f49911) gives the selector score ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "W3SPEC-x": {
      "required_outcome": "DF2-DRAFTER-CAPABILITY input: z-lab/dflash @ 07ebd93db9f4 (2026-08-18, remote HEAD identical today) contains NO training code. 659-line dflash/model.py has only inference: CandidateSelector (selector_top_k=16 candidates per position via topk of the draft ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "MTP-3": {
      "required_outcome": "No change to Axis E. Restoring the Qwen3.8-Flash-Next MTP head loads the published unsloth shared-Q8_0 head (no training), so the MTP-objective choice does not touch it.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "W3SPEC-4": {
      "required_outcome": "No action on our CPU/HIP stack; note in the speculative handoff that the n_vocab-sentinel failure is Vulkan-specific and fails loudly at src/llama-batch.cpp:52 (token validation), which our tree retains.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "TCAP-2": {
      "required_outcome": "Record that INF-70 Axis-E \"MTP needs FP8 re-download\" is obsolete: head already on disk (mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf, 2.79 GB, 2026-09-02); no ThinkingCap download is needed for MTP",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: DCOCO and Domino are the same correction family as LiLiCorr and DFlash2 already has a learned selector; drafter recipes and the absence of upstream training code; Axis E needs no FP8 download; the n_vocab-sentinel failure is Vulkan-only.",
      "task_refs": []
    },
    "LOOP-1": {
      "required_outcome": "Add a knowledge note to the INF-70 roofline program: weight-reuse architectures. Sequential looping multiplies weight bytes per token by L, and with 32 MiB L3 per CCX (384 MiB total) a block above ~32 MiB per CCX cannot be cache-reused (e.g. a 7B 14-layer PLT ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "LOOP-2": {
      "required_outcome": "Ingest and dive LoopCoder-v2 (arXiv 2606.18023): released 7B PLT 2-loop coder (Apache-2.0, HF Multilingual-Multimodal-NLP/LoopCoder-V2, 14 layers, hidden 5120, 8 KV heads) is the first PLT checkpoint we can actually run; card claims SWE-bench Verified 43.0 -> ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "LOOP-3": {
      "required_outcome": "Correct the stale gate: Ouro now has a community llama.cpp port (BrandeisPatrick/loop-transformer, ouro arch, 324 added lines, PR ggml-org/llama.cpp#29823, GGUFs for Ouro 1.4B/2.6B +Thinking) built on upstream looped-model machinery merged for Nanbeige4.2 (PR ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "LOOP-5": {
      "required_outcome": "Record in reasoning-compression.md only: looped MoE R=5 at 0.3B-1.3B reaches reasoning parity with 0.6B-2.9B at 1.8x training-compute-defined inference compute while trailing Overall 46.9 vs 50.2; no latency/bytes measured; no checkpoint released in the text.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "W2LOOP-3": {
      "required_outcome": "Knowledge-only: record that our GDN graph hard-caps beta at 1 (src/models/qwen3next.cpp:417 ggml_sigmoid) matching the Qwen3.5 control that failed to generalise hidden tracking; no probe.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "W2LOOP-4": {
      "required_outcome": "Correct the stale note in gpu-acceleration-path.md ~line 248 (intake-332 \"Not llama.cpp compatible\") to say nanbeige looped arch merged 2026-07-27 and Ouro is PR #29823 open; owning session applies.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "W2KERN-6": {
      "required_outcome": "Record the history-dependence correctness rule for any future KV-editing serving feature: a slot/prefix index keyed only by token prefix (src/inference/prefix_index.py) must also key on the drop/shift operation history, or mark the slot unmatchable after an ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "W3DEC-6": {
      "required_outcome": "Add one binding design line to the KV prefix-fork program: any future KV-editing operation (cell drop, position shift, ctx-shift variants) invalidates token-prefix matching as a correctness test; the orchestrator PrefixIndex and llama-server slot reuse key on ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "AGENT-4": {
      "required_outcome": "Do NOT adopt the article single-loop thesis for our CPU stack without measurement: the article premise is frontier models with thinking on; our workers are local quantised Qwen3.x on a BW-bound CPU where a separate small-context worker call is cheaper per ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "AGENT-6": {
      "required_outcome": "Design note (no compute): map C2C onto llama.cpp. Feasible path = out-of-process fuser. Receiver and Sharer each prefill the same prompt; read per-layer K/V from each via llama_state_seq_get_data (include/llama.h:881) or /slots/{id}?action=save ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "AGENT-8": {
      "required_outcome": "Read the thu-nics AKV repo (cache engineering for agents, follow-up to C2C, Apache-2.0, pushed 2026-10-21) before sizing any pair-training, since it may cover agent KV reuse without a per-pair trained fuser.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "AGENT-10": {
      "required_outcome": "Use Resin docs/cache-pool.md + architecture.md Prefix reuse as design reference for hybrid prefix reuse: its snapshots are taken at an alignment equal to the LCM of all group block sizes and restore attention, SWA and recurrent state at the same boundary, ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "SPEECH-5": {
      "required_outcome": "No new STT action. Hex confirms the transcribe.cpp Parakeet Unified streaming path (Vulkan GPU only). Parakeet streaming vs whisper.cpp is already a measured-pending candidate: CS-8.STT0 40/40 CPU==GPU identity done, transcribe.cpp CPU 40-clip run 37/40 ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "SPEECH-6": {
      "required_outcome": "Add Parakeet Unified English (streaming, lookahead variants) as a named arm check in CS-8.STT5 if not already present, noting hex pins fork rev 7045d1c0 (transcribe.cpp 0.4.1) while our build pins db678a03; record both pins.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "W2SP-2": {
      "required_outcome": "Specify the server-turn contract in CS-22: because /v1/realtime has turn_detection null, our controller (VAD + CS-47 semantic gate) must send commit/response.create/response.cancel; add this as the integration seam in CS-22.A1 rather than waiting on a server ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "W2SP-4": {
      "required_outcome": "Record in TD-23 candidate list that d1-2B/3B are VL models with LFM Open License v1.0 and that the llama.cpp path supports noul/choice/score only; routing questions are choice+score so the subset is sufficient.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "W3DEC-5": {
      "required_outcome": "Pin the serving-safe API subset for the probe and any shim: only choice/score/noul; options within the model limit (52 openjev, 255 laya; read from the model, d1 limits unread); state must fit one ubatch (use -ub, not -b; 30073); avoid router mode with ...",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "KERN-9": {
      "required_outcome": "Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: diagnostic feedback must come from a separate seed; agent-harness mode cost several times the tokens of plain refinement in PTXBench.",
      "task_refs": []
    },
    "W2KERN-2": {
      "required_outcome": "Compare AK candidate generation as plain multi-turn refinement vs agent-harness mode on token cost per accepted keep (PTXBench: agent harness cost 3.3-5.1x tokens and was worse on attention). Use existing AK run logs only; no new compute.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: diagnostic feedback must come from a separate seed; agent-harness mode cost several times the tokens of plain refinement in PTXBench.",
      "task_refs": []
    },
    "SPEC-3": {
      "required_outcome": "Port the DCOCO head to llama.cpp as a replacement DFlash2 selector, and train it on the frozen DFlash2 backbone. Gated on SPEC-1 PROMOTE. Port: converter keys/tensors for cand_proj, ctx_h_proj, cand_ctx_proj + LN, pair_proj and the 386->256->1 MLP (~100 LOC ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "SPEC-5": {
      "required_outcome": "Domino-style GRU + full-vocab low-rank correction head on the DFlash2 drafter: no work now. It needs full drafter co-training with the curriculum, and its sequential head adds a 256x248320 logit-residual projection per position on the critical path. Revisit ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "MTP-2": {
      "required_outcome": "Bounded frozen-trunk probe on the Soft-MTP repo (MI210, ROCm torch, <=4 GPU-h, no llama.cpp). Take the released 167M (or 332M) NTP checkpoint, set freeze_backbone=true, and train fresh K=3 DeepSeek-style heads under two arms with identical data order, seed, ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "MTP-4": {
      "required_outcome": "Record a trigger on the speculative-decoding refresh. If a served fine-tune ships with a stock (base-co-trained) MTP head, as already observed for ThinkingCap and Qwopus, the remedy is head-only re-alignment on the frozen fine-tuned trunk against its own NTP ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "W3SPEC-3": {
      "required_outcome": "If W3SPEC-1 shows divergence: reproduce on the experimental branch and try the PR #29454 approach (copy pre-ubatch state into unwritten snapshot slots every ubatch) as the candidate fix; it was never merged, so it must be carried as our own patch on a ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "SPEC2-3": {
      "required_outcome": "Note thinking-mode default sampling repetition risk: issue says model card recommends presence_penalty 0-2 and attributes loops to degenerate state amplified by temp 1.0 / top_k 20 / top_p 0.95; check the Flash-Next architect_general request sampler against ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "LOOP-6": {
      "required_outcome": "Monitor NCM as a drafter source: trigger = a released NCM-style generator with a general-text tokenizer sharing a served model vocabulary, or any measured acceptance rate against an AR target. Do not build now: released checkpoints are per-dataset ~100M-725M ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "LOOP-4": {
      "required_outcome": "Bounded CPU probe on a llama.cpp-experimental branch with the Ouro port: Ouro-1.4B Q4_K_M (854 MB per card), llama-bench tg at num_loops 1/2/4 via --override-kv, reporting achieved GB/s counting bytes once per loop against the C0 153 GB/s ceiling. This ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: a llama.cpp or vLLM PLT port, an independent LoopCoder-v2 replication, or a published PLT decode timing opens the Ouro/PLT CPU probe.",
      "task_refs": []
    },
    "W2LOOP-1": {
      "required_outcome": "On an experimental llama.cpp branch freshly cut from production v10, cherry #25994 plus #29823 (about 590 added lines) and measure Ouro-1.4B Q8_0/Q4_K_M at --override-kv ouro.num_loops=int:1/2/4 on EPYC CPU (one quarter and full socket): tok/s, achieved GB/s ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: a llama.cpp or vLLM PLT port, an independent LoopCoder-v2 replication, or a published PLT decode timing opens the Ouro/PLT CPU probe.",
      "task_refs": []
    },
    "W2LOOP-2": {
      "required_outcome": "Monitor triggers: (a) llama.cpp or vLLM PR adding iquestpltcoder / PLT, (b) an independent replication of LoopCoder-v2 R=2 SWE-bench Verified, (c) a timing number for PLT decode. Any one fires ingest-and-dive on it.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: a llama.cpp or vLLM PLT port, an independent LoopCoder-v2 replication, or a published PLT decode timing opens the Ouro/PLT CPU probe.",
      "task_refs": []
    },
    "W3DEC-8": {
      "required_outcome": "Conditional on W3DEC-7: a bounded semantics probe on an attention-only role model on llama.cpp-experimental: compare (a) seq_rm of old tool-response cells + seq_add repositioning (the drop+repos analogue) vs (b) re-prefill of the text with those responses ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "W2KERN-5": {
      "required_outcome": "Bounded probe: tool-result KV drop+shift on a pure full-attention role in llama-server, using existing llama_memory_seq_rm + seq_add (as in the streaming-llm / context-shift path), on a recorded orchestrator agent trace. Measure (a) tokens re-prefilled per ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "AGENT-3": {
      "required_outcome": "Add a per-fold eval: before folding any worker role into skills, require a frozen end-to-end set covering every production chain (architect -> coder_escalation, frontdoor -> worker_*) and every must-not-break rule, repeated >=2 times, reporting flipped tasks. ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "AGENT-5": {
      "required_outcome": "Bounded offline probe on CPU (HF transformers, no llama.cpp): with released nics-efc/C2C_Fuser qwen3_8b+qwen2.5_7b fuser, run n=200 frozen items from a MC set the stack already scores (e.g. MMLU-Redux subset used in canonical suites) in 4 arms: Receiver-only, ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "AGENT-7": {
      "required_outcome": "Role-pair candidate list, ranked: (1) architect_critic / coder_escalation (Qwen3.8-27B Q8_0, dense KV-densest per model_registry.yaml:541) as SHARER -> worker_general/worker_summarize (Qwen3.6-35B-A3B MoE, receiver; must check whether its layers are all full ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "SPEECH-2": {
      "required_outcome": "Add LFM3-Audio-2B/Omni-2B as a third challenger in the CS-8 G1/G3/G4 interlocutor bake-off: G1 en/it TTS intelligibility via llama-tts (note voice chat is English-only per card, so Italian only for TTS/ASR), G3 tool-call slot quality from speech, G4 ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "SPEECH-4": {
      "required_outcome": "Reuse the upstream /v1/realtime (OpenAI-compatible) and Voxtral-Realtime support as a CS-20 backend interface option: write a realtime client adapter in the voice controller that speaks /v1/realtime beside the whisper :9000 / qwentts :9002 cascade.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "SPEECH-7": {
      "required_outcome": "Monitor Dessa for paper, weights or API; trigger = any released checkpoint or paper with benchmark numbers, then fold into the M8 full-duplex reference slot check (language gate D2 likely fails if English-only).",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "W2SP-5": {
      "required_outcome": "Spoken-state decision probe (turn completeness / intent) with d1-Omni-2B on the CS-45 turn-taking corpus once human_recorded strata exist; score with the CS-45 measurands against the CS-47 semantic-gate arms.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "AGENT-13": {
      "required_outcome": "Speech turn-taking decider test (only after human-recorded strata exist): d1-Omni-2B reads a short audio window and answers noul/score questions (end of turn? backchannel needed?) on the CS-45 corpus; compare against the CS-22 controller policy and the D1 ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "W4UP-4": {
      "required_outcome": "Add a GENERIC-readout arm to TD-23 (any lineup chat model, thinking off, U+22B2 label readout) as a comparator to dedicated decision backends after the systemone base is in the screen build.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "W4UP-5": {
      "required_outcome": "Offer/track the group-parent checkpoint fix for hybrid decision models; evaluate by prompt-token count (1254 vs 827 shape) on our model before adopting.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "KERN-2": {
      "required_outcome": "Build a race-only symbolic executor for gfx90a AMDGCN: parse hipcc --save-temps asm, concrete thread/workgroup indices and launch params, per-byte LDS reader/writer sets between s_barrier, lgkmcnt/vmcnt waits as completion points, exec-mask lanes, wave64. ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: a GPU race mutant passing all 20 runs opens a gfx90a race-only symbolic executor; an ISA archive plus a compute-bound target opens an ISA-level lowering probe; a recurring rejection class (3 or more) opens a failure-to-rule loop.",
      "task_refs": []
    },
    "KERN-8": {
      "required_outcome": "GCN-Gym probe of AI lowering on gfx90a. Build a standalone harness that assembles LLM-patched AMDGCN for one compute-bound kernel (MMQ Q4_K prefill tile or FA at long context) with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a, loads it via hipModuleLoad and ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: a GPU race mutant passing all 20 runs opens a gfx90a race-only symbolic executor; an ISA archive plus a compute-bound target opens an ISA-level lowering probe; a recurring rejection class (3 or more) opens a failure-to-rule loop.",
      "task_refs": []
    },
    "W2KERN-4": {
      "required_outcome": "Failure-to-rule loop for AK: after each rejected batch, classify the failure reason and, when a class recurs (>=3), have an agent propose a permanent static check or oracle input, merged only under corpus tests of all prior keeps (CAKE Sec 3.2).",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: a GPU race mutant passing all 20 runs opens a gfx90a race-only symbolic executor; an ISA archive plus a compute-bound target opens an ISA-level lowering probe; a recurring rejection class (3 or more) opens a failure-to-rule loop.",
      "task_refs": []
    },
    "TCAP-1": {
      "required_outcome": "Bounded A/B: base UD-IQ4_XS (current :8074 file) vs bottlecapai ThinkingCap IQ4_XS GGUF, llama-server, same recipe qwen38-flash-next-cpu-mtp, enable_thinking=true on /v1/chat/completions, frozen 40-60 prompt set (arch/plan-critique + reasoning, AIME-style, ...",
      "review_status": "closed-with-basis",
      "review_basis": "Trigger: the operator enables thinking on a Flash-Next role, or the architect bench reopens a thinking arm; then run the ThinkingCap IQ4_XS A/B with a shared-head arm.",
      "task_refs": []
    },
    "TCAP-3": {
      "required_outcome": "If A/B runs, add arm B2 = ThinkingCap trunk + our unsloth shared-Q8_0 draft file vs embedded head, measure alpha for both",
      "review_status": "closed-with-basis",
      "review_basis": "Trigger: the operator enables thinking on a Flash-Next role, or the architect bench reopens a thinking arm; then run the ThinkingCap IQ4_XS A/B with a shared-head arm.",
      "task_refs": []
    },
    "PRE-2545": {
      "required_outcome": "Identify the STT model/runtime from the linked GitHub repo (expansion seed) before scoring for the speech lane.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "PRE-2546": {
      "required_outcome": "Read the paper (expansion seed arXiv 2610.14162) and judge whether coarse-to-fine parallel generation has a drafter or non-AR serving role for EPYC.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "PRE-2547": {
      "required_outcome": "Dive: decide whether looped/parallel-loop decoding changes bytes-per-token on bandwidth-bound CPU decode, and whether any served or candidate model is looped.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "PRE-2548": {
      "required_outcome": "Dive: verify Table 2 and decide whether Soft-MTP is the objective to use if we train or restore MTP heads (Flash-Next Axis E, drafter training).",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-DRAFTER-CAPABILITY.OBJ carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-DRAFTER-CAPABILITY.OBJ",
          "task_text": "- [ ] **DF2-DRAFTER-CAPABILITY.OBJ — Fix the drafter-training data contract before any capture (intake-2548#record, intake-2578#record, intake-297#record).** Amend the capture contract inherited from INF-62 (\"hard next-token labels\") so every feature dump also taps the target's final post-norm hidden state (5120 x bf16 = 10,240 bytes per token, +20% over the current taps), which yields the exact teacher distribution through the frozen output head. Make forward KL toward the target distribution the default objective with hard labels as the fallback arm (with a frozen trunk, Soft-MTP's gradient equals direct forward KL), and record the Nemotron 3 Ultra frozen-backbone recipe (temperature 2, hidden states sampled from earlier draft steps) as an option. Note that z-lab/dflash @ 07ebd93 ships no training code, so any drafter or selector training is research, not a port.",
          "acceptance": "Contract text amended in the handoff with the tap, default objective, fallback arm and recipe option; the capture script refuses to start without the final-hidden tap."
        }
      ]
    },
    "PRE-2549": {
      "required_outcome": "Dive with intake-2548: check the loss implementation and whether it composes with head-only training on a frozen trunk.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-DRAFTER-CAPABILITY.OBJ carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-DRAFTER-CAPABILITY.OBJ",
          "task_text": "- [ ] **DF2-DRAFTER-CAPABILITY.OBJ — Fix the drafter-training data contract before any capture (intake-2548#record, intake-2578#record, intake-297#record).** Amend the capture contract inherited from INF-62 (\"hard next-token labels\") so every feature dump also taps the target's final post-norm hidden state (5120 x bf16 = 10,240 bytes per token, +20% over the current taps), which yields the exact teacher distribution through the frozen output head. Make forward KL toward the target distribution the default objective with hard labels as the fallback arm (with a frozen trunk, Soft-MTP's gradient equals direct forward KL), and record the Nemotron 3 Ultra frozen-backbone recipe (temperature 2, hidden states sampled from earlier draft steps) as an option. Note that z-lab/dflash @ 07ebd93 ships no training code, so any drafter or selector training is research, not a port.",
          "acceptance": "Contract text amended in the handoff with the tap, default objective, fallback arm and recipe option; the capture script refuses to start without the final-hidden tap."
        }
      ]
    },
    "PRE-2550": {
      "required_outcome": "Dive: separate the transferable mechanism (exact GDN-state addressing) from the demo; decide if it informs GDN-hybrid serving or memory work.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.GDN carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.GDN",
          "task_text": "- [ ] **AKX-ALL-31.GDN — Deterministic one-hot GATED_DELTA_NET state oracle (intake-2574#record, intake-2550#record).** Add a test-backend-ops case on an experimental champion-derived branch that drives the delta rule with gate held at 1, beta at 1 and one-hot keys, so each step overwrites exactly one state row and a one-hot query must read back that row; compare against the closed-form result. Cover CPU f32, gfx90a f32 and BF16 state, and K > 1 snapshot slots. The current cases only compare backends on random data, which cannot detect a shared indexing error.",
          "acceptance": "Oracle case passes exactly on every leg and slot count, with a planted index-off-by-one mutant that fails."
        }
      ]
    },
    "PRE-2551": {
      "required_outcome": "Dive: check whether looped MoE trades weight bytes for compute in a way that suits bandwidth-bound EPYC decode.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "PRE-2552": {
      "required_outcome": "Dive: establish the actual llama.cpp audio path and whether it can replace or augment the whisper.cpp + qwentts.cpp cascade on EPYC/MI210.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/conversation-stack.md",
          "task_id": "CS-8.STT8",
          "task_text": "- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence.",
          "acceptance": "Scratch build proven by the linkage check on both devices; both arms scored on the same pinned clips with per-clip outputs retained; advance or reject per arm under the rule."
        }
      ]
    },
    "PRE-2553": {
      "required_outcome": "Dive: compare with the d1/Jev decision-model lineage already indexed and decide whether an audio/vision decision front end serves orchestrator routing or the speech turn-taking loop.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/typed-decision-plane.md",
          "task_id": "TD-23.D1",
          "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload.",
          "acceptance": "Both gates pass, or fail with retained per-request probabilities, on CPU and HIP before any TD-23 quality read; the build commit set, the batch flags and the GGUF sha256 recorded."
        }
      ]
    },
    "PRE-2554": {
      "required_outcome": "Dive: verify the llama.cpp realtime speech-server path and which ggml generation it needs relative to the frozen kernel set.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "PRE-2555": {
      "required_outcome": "Dive: extract the loop design and the verified-vs-numeric gap; map onto the AK candidate gate and gfx90a/x86 targets.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.EDGE",
          "task_text": "- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework.",
          "acceptance": "All families and the max-error bound run by default on CPU and HIP, every seeded twin is red, the champion incumbent and all historical keeps pass."
        }
      ]
    },
    "PRE-2556": {
      "required_outcome": "Dive with intake-2555: read the loop and trace layout for AK reuse.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-CTR-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-CTR-1",
          "task_text": "- [ ] **RVP-CTR-1 — Counter-grounded planner signals for the GPU AK lane (intake-2556#record).** For the top hotspot kernel of each GPU screen, capture a fixed declared counter subset with rocprofv2 (occupancy, LDS bank conflicts, VALU/MFMA busy, memory unit stall, achieved bandwidth) and pass it to the planner with the rule that every proposed idea must cite a counter that is present, and a missing counter may not be treated as zero. Compare 2 planner rounds with and without counters on the same target and budget.",
          "acceptance": "Counter capture recorded per screen; planner inputs carry the counters; the with/without comparison reports accepted-keep rate and wasted candidates on the same budget."
        }
      ]
    },
    "PRE-2557": {
      "required_outcome": "Dive: decide what an equivalence/race checker would add to the AK correctness gate on gfx90a and x86.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree build three seeded-race HIP mutants, each deleting one barrier in MMQ, MMVQ and the FA kernel, and run the served-shape suite 20 times each. CPU: build test-backend-ops with ThreadSanitizer, using LLVM libomp with Archer annotations, and run the threaded ops. Decision rule: if any GPU mutant passes the gate in all 20 runs, open the gfx90a race-only symbolic-executor trigger; if all are caught, record the gate as race-sensitive at these sites. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant pass/fail counts over 20 runs, the TSAN report on the anchor, and the stated verdict."
        }
      ]
    },
    "PRE-2558": {
      "required_outcome": "Dive: test whether the certificate-plus-independent-checker pattern fits belief-kernel derivations or registry/handoff consistency checks.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; VB-CERT-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/vidya-belief-substrate-program.md",
          "task_id": "VB-CERT-1",
          "task_text": "- [ ] **VB-CERT-1 — Independent checker for the gate certificate (intake-2558#record).** Write scripts/vidya/cert_check.py, a standalone verifier of epyc.vidya/certificate/v1 that shares no imports with fold.py, gate.py or lattice code, re-derives the verdict from the certificate's stated inputs, and compares certificate.frontier and as_of explicitly. Today certificate_hash is a self-hash and input_attestations holds labels rather than the digests the spec section 11.2 requires (scripts/vidya/gate.py:130-166). Add forged-certificate tests (altered verdict, swapped frontier, stale as_of, label-only attestation) that must be rejected.",
          "acceptance": "Checker passes every genuine certificate in the current ledger sample and rejects every forged case; the label-versus-digest gap is either fixed in gate.py or recorded as a refusal reason."
        }
      ]
    },
    "PRE-2559": {
      "required_outcome": "Dive: decide whether cache-level handoff between our role models is feasible in llama.cpp and what it would save over text handoff.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "PRE-2560": {
      "required_outcome": "Dive with intake-2561: read the corrector implementation to size a llama.cpp port onto the DFlash2 drafter path.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-LAT",
          "task_text": "- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor.",
          "acceptance": "Dump instrument merged off-by-default with a symbol-absent rebuild check; arm B reproduces live accepted counts; H with interval reported per split; verdict recorded under the rule."
        }
      ]
    },
    "PRE-2561": {
      "required_outcome": "Dive: measure-first design — top-K coverage of the verifier token on our DFlash2 drafter logits decides whether a corrector is worth porting.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-LAT",
          "task_text": "- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor.",
          "acceptance": "Dump instrument merged off-by-default with a symbol-absent rebuild check; arm B reproduces live accepted counts; H with interval reported per split; verdict recorded under the rule."
        }
      ]
    },
    "PRE-2562": {
      "required_outcome": "Dive: read the architecture docs and the optimize-performance skill; extract what transfers to AK loops or llama.cpp serving.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: KV editing makes the reuse key history-dependent; C2C maps onto out-of-process state get/set; the single-loop thesis is untested on our CPU stack.",
      "task_refs": []
    },
    "PRE-2564": {
      "required_outcome": "Dive (light): confirm availability and what is technically claimed; compare with full-duplex designs in the conversation-stack lane.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CS-8.STT8 advance rule admits LFM3 to the bake-off gates; a running realtime backend opens a CS-20 adapter; a Dessa paper or weights opens a reference slot; human-recorded strata open the spoken-state decider test; TD-23 completion opens a generic-readout arm; an upstream hybrid-prefix fix opens a decision np>1 retest.",
      "task_refs": []
    },
    "PRE-2565": {
      "required_outcome": "Dive: map the folding criteria onto the orchestrator REPL/agent loop (roles as subagents vs skills) and its tool count.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RI-25 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/routing-intelligence.md",
          "task_id": "RI-25",
          "task_text": "- [ ] **RI-25 — Zero-inference fold replay over delegation records (intake-2565#record).** Apply the fold criteria (fold a sub-agent only if the folded version does not score worse; inspect which tasks flip; repeat runs) to existing orchestrator delegation records: for each delegate() role (worker_math, worker_general, worker_summarize share one model), measure from records how often a chain needs the role's own context, how much of the 4,000-character truncated hand-off (src/repl_environment/routing.py:581) reaches the worker, and how often the delegated answer is re-asked by the caller. Output a per-role fold-candidate table; no serving change.",
          "acceptance": "Per-role table with denominators over a frozen record manifest, and a one-line fold/keep recommendation per role for a later inference A/B."
        }
      ]
    },
    "PRE-2567": {
      "required_outcome": "Dive: verify the table, check the HF card (quant/MTP head) and decide a same-recipe token-count and accuracy probe on our harness.",
      "review_status": "closed-with-basis",
      "review_basis": "Trigger: the operator enables thinking on a Flash-Next role, or the architect bench reopens a thinking arm; then run the ThinkingCap IQ4_XS A/B with a shared-head arm.",
      "task_refs": []
    },
    "PRE-2568": {
      "required_outcome": "Dive with intake-2546.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; a drafter capture start opens the frozen-trunk objective probe; native-MTP acceptance 0.05 below base on a served finetune opens head re-alignment; a DF2-12.1 degenerative divergence opens the snapshot-slot patch; the collapse canary tripping on repetition opens a thinking-mode guard; an NCM-style generator sharing a served vocabulary opens a drafter test.",
      "task_refs": []
    },
    "PRE-2569": {
      "required_outcome": "Dive with intake-2561: sequential corrector baseline that DCOCO claims to beat under concurrency.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-LAT",
          "task_text": "- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor.",
          "acceptance": "Dump instrument merged off-by-default with a symbol-absent rebuild check; arm B reproduces live accepted counts; H with interval reported per split; verdict recorded under the rule."
        }
      ]
    },
    "PRE-2570": {
      "required_outcome": "Dive: decide what a sound equivalence gate would need on gfx90a/x86 and which AK candidate classes it could cover.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree build three seeded-race HIP mutants, each deleting one barrier in MMQ, MMVQ and the FA kernel, and run the served-shape suite 20 times each. CPU: build test-backend-ops with ThreadSanitizer, using LLVM libomp with Archer annotations, and run the threaded ops. Decision rule: if any GPU mutant passes the gate in all 20 runs, open the gfx90a race-only symbolic-executor trigger; if all are caught, record the gate as race-sensitive at these sites. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant pass/fail counts over 20 runs, the TSAN report on the anchor, and the stated verdict."
        }
      ]
    },
    "PRE-2571": {
      "required_outcome": "Dive with intake-2547.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: sequential loops multiply weight bytes per token; parallel-loop decode does not; our GDN graph caps beta at 1; the gpu-acceleration-path compatibility note is stale.",
      "task_refs": []
    },
    "PRE-2572": {
      "required_outcome": "Dive: verify config (qwen4_exp, MTP layers), whether the GGUFs carry nextn tensors, and fit against the INF-70 Axis-E MTP restoration need.",
      "review_status": "closed-with-basis",
      "review_basis": "Trigger: the operator enables thinking on a Flash-Next role, or the architect bench reopens a thinking arm; then run the ThinkingCap IQ4_XS A/B with a shared-head arm.",
      "task_refs": []
    },
    "PRE-2573": {
      "required_outcome": "Dive: decide whether transcribe.cpp Parakeet streaming is a candidate STT against frozen whisper.cpp; check what the index already holds on transcribe.cpp.",
      "review_status": "closed-with-basis",
      "review_basis": "Retained: Parakeet/transcribe.cpp is already owned; the realtime server has no turn detection; d1 serving covers choice/score/noul only under the LFM licence.",
      "task_refs": []
    },
    "PRE-2574": {
      "required_outcome": "Dive with intake-2550.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.GDN carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
          "task_id": "AKX-ALL-31.GDN",
          "task_text": "- [ ] **AKX-ALL-31.GDN — Deterministic one-hot GATED_DELTA_NET state oracle (intake-2574#record, intake-2550#record).** Add a test-backend-ops case on an experimental champion-derived branch that drives the delta rule with gate held at 1, beta at 1 and one-hot keys, so each step overwrites exactly one state row and a one-hot query must read back that row; compare against the closed-form result. Cover CPU f32, gfx90a f32 and BF16 state, and K > 1 snapshot slots. The current cases only compare backends on random data, which cannot detect a shared indexing error.",
          "acceptance": "Oracle case passes exactly on every leg and slot count, with a planted index-off-by-one mutant that fails."
        }
      ]
    },
    "PRE-2575": {
      "required_outcome": "Dive: locate the llama.cpp code for the audio/realtime path and estimate the port onto llama.cpp-experimental; check ggml generation vs the speech kernel set.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carries the required behavior with its controls and decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/conversation-stack.md",
          "task_id": "CS-8.STT8",
          "task_text": "- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence.",
          "acceptance": "Scratch build proven by the linkage check on both devices; both arms scored on the same pinned clips with per-clip outputs retained; advance or reject per arm under the rule."
        }
      ]
    },
    "PRE-2576": {
      "required_outcome": "Dive with intake-2559.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: CF-AKV-0 escalation rule opens the attention-only KV-drop semantics probe; a released or trainable fuser for a served role pair opens a C2C screen; a fold decision from RI-25 opens a per-fold end-to-end eval.",
      "task_refs": []
    },
    "AGENT-9": {
      "required_outcome": "Copy the measurement-discipline text, not code, into the AK actor context: (a) record cache/graph/placement state and compare on the same allocation, (b) locate the limiting interval from a trace BEFORE kernel edits, (c) report the spread and do not call ...",
      "review_status": "closed-with-basis",
      "review_basis": "the Resin measurement-discipline text is weaker than the Annex K protocol the loop already follows.",
      "task_refs": []
    },
    "AGENT-11": {
      "required_outcome": "Decline engine/runner split as an adoption target: there is no CPU or ROCm runner, and production serving is llama.cpp (frozen v10). Treat the split as vocabulary only.",
      "review_status": "closed-with-basis",
      "review_basis": "the Resin engine/runner split has no CPU or ROCm runner and production serving is llama.cpp.",
      "task_refs": []
    },
    "MEM-3": {
      "required_outcome": "Do not pursue an in-weights calculator (compiled RISC-V/CHIP-8 layers) for the serving stack. Flag for operator review per the research-intake rule rather than closing silently.",
      "review_status": "closed-with-basis",
      "review_basis": "an in-weights calculator costs about 1.6 to 2 times the weight bytes per token on a bandwidth-bound host and the tool arm already matches it; operator confirmation requested.",
      "task_refs": []
    },
    "MEM-5": {
      "required_outcome": "No certificate/checker layer for scripts/handoffs/index_state.py or registry consistency checks.",
      "review_status": "closed-with-basis",
      "review_basis": "the handoff index check already re-derives and compares on every run, so a certificate layer adds nothing.",
      "task_refs": []
    },
    "MTP-5": {
      "required_outcome": "Decline adopting Soft-MTP as a pretraining objective.",
      "review_status": "closed-with-basis",
      "review_basis": "Soft-MTP as a pretraining objective needs trunk training, which this stack does not do.",
      "task_refs": []
    },
    "KERN-11": {
      "required_outcome": "Do not adopt upstream Volta or the Blackwell fork directly. Both are PTX/NVIDIA-only, and this host has no NVIDIA GPU. Reuse only the race model (KERN-2) and the scaffold code.",
      "review_status": "closed-with-basis",
      "review_basis": "upstream Volta and its Blackwell fork are PTX-only and the host has no NVIDIA GPU; the race model transfers through the race trigger instead.",
      "task_refs": []
    },
    "TCAP-4": {
      "required_outcome": "Do not pursue the vendor PRO tier or method discovery",
      "review_status": "closed-with-basis",
      "review_basis": "the vendor PRO tier is closed and no method is disclosed.",
      "task_refs": []
    },
    "W2KERN-7": {
      "required_outcome": "Decline porting AKV server (SGLang, Rust build, softmax-attention only) as a serving path; keep as design reference only. Hybrid/linear-attention models (our main Qwen line) are unsupported by the authors and by llama.cpp seq ops.",
      "review_status": "closed-with-basis",
      "review_basis": "the AKV server is SGLang and softmax-only; it stays a design reference.",
      "task_refs": []
    },
    "PRE-2563": {
      "required_outcome": "None beyond architectural context; no measured result.",
      "review_status": "closed-with-basis",
      "review_basis": "a research-preview agent OS with no measurements and no touchpoint in the serving stack.",
      "task_refs": []
    },
    "PRE-2566": {
      "required_outcome": "None: KB retrieval is ColBERT MaxSim; synthetic-only evidence.",
      "review_status": "closed-with-basis",
      "review_basis": "synthetic single-machine retrieval evidence, and KB retrieval uses ColBERT MaxSim, not cosine stores.",
      "task_refs": []
    }
  },
  "proposed_tasks": [
    {
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "task_text": "- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary."
    },
    {
      "owner": "handoffs/active/kv-prefix-fork-and-paged-attention.md",
      "task_text": "- [ ] **KPF-RS-1 — Recurrent-state hash conformance after checkpoint restore and fork (intake-2574#record, intake-2591#record).** On an experimental champion-derived branch, extend `test-recurrent-state-rollback` and the KPF fork path to hash the full recurrent state (all Gated-DeltaNet state tensors and every snapshot slot, written and unwritten) after a checkpoint restore, after a fork from a checkpoint, and after a speculative rollback at np 1 and np 4, and compare against the state reached by re-prefilling the same tokens. Today the test compares logits to 1e-5 only, which can pass while an unwritten snapshot slot carries another sequence's state. Include a planted mutation (skip one snapshot write) that must fail. CPU and gfx90a legs."
    },
    {
      "owner": "handoffs/active/speculative-decoding-mtp-refresh.md",
      "task_text": "- [ ] **SPEC-CANARY.1 — Per-request acceptance-collapse canary for every speculative serving role (intake-2577#record).** In the orchestrator's llama-server telemetry, flag any request with at least 64 drafted tokens and zero accepted, and any request whose last 256 generated tokens repeat one n-gram block, recording role, port, slot, n_parallel, draft settings and request id. Ship it as a passive counter with a dashboard health field; it changes no serving behaviour. Test it with a replayed log containing a planted zero-acceptance run and a planted repetition tail."
    },
    {
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "task_text": "- [ ] **G2-CONC.MP — Add a simultaneous multi-prefill arm to the G2-CONC promotion gate (intake-2577#record).** For every speculative recipe on the promotion candidate binary: c in {2, 3, 5} equal-length prompts that differ only by a salt, issued at the same instant, temp 0, speculation on and off, each output compared token for token with a solo np-1 run. The vLLM defect on the same model family corrupted state only when two or more prompts prefilled in one scheduler step, which a staggered concurrency test never exercises."
    },
    {
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "task_text": "- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor."
    },
    {
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "task_text": "- [ ] **DF2-PM — Point-mass draft proposals at production temperature (intake-2561#record).** Behind an env knob on the experimental build, make the DFlash2 temp>0 branch propose the argmax selector walk with a point-mass distribution instead of sampling softmax(scores/T); the verifier then accepts with p_target(draft) and resamples from the residual (common/sampling.cpp:740-766), which is lossless. A/B against the stock sampled walk on the DF2-4 protocol (12 prompts, temp 0.6, top-p 0.95, top-k 20) at np 1 and np 4, at least 5 interleaved pairs; primary metric weighted acceptance, secondary tok/s; the SPEC-PIT.1 distribution gate must pass. Adopt into the next champion fold only if weighted acceptance improves by at least 3% in at least 4 of 5 pairs at both np values, tok/s does not regress and SPEC-PIT.1 passes; otherwise record the per-pair numbers and close."
    },
    {
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "task_text": "- [ ] **DF2-DRAFTER-CAPABILITY.OBJ — Fix the drafter-training data contract before any capture (intake-2548#record, intake-2578#record, intake-297#record).** Amend the capture contract inherited from INF-62 (\"hard next-token labels\") so every feature dump also taps the target's final post-norm hidden state (5120 x bf16 = 10,240 bytes per token, +20% over the current taps), which yields the exact teacher distribution through the frozen output head. Make forward KL toward the target distribution the default objective with hard labels as the fallback arm (with a frozen trunk, Soft-MTP's gradient equals direct forward KL), and record the Nemotron 3 Ultra frozen-backbone recipe (temperature 2, hidden states sampled from earlier draft steps) as an option. Note that z-lab/dflash @ 07ebd93 ships no training code, so any drafter or selector training is research, not a port."
    },
    {
      "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
      "task_text": "- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework."
    },
    {
      "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
      "task_text": "- [ ] **AKX-ALL-31.QDEC — Exhaustive code-space decode check per served quant type (intake-2555#record).** For Q4_K, Q6_K, Q8_0, IQ2_*, IQ3_*, IQ4_XS and MXFP4, enumerate every per-element code together with every scale and min value that occurs in the served GGUFs, decode through the CPU and HIP dequant paths, and compare bit-for-bit with a scalar reference. First report how much of the code space the current random suite reaches; bit-level dequant is exactly the class an equivalence checker cannot prove, so enumeration is the sound substitute."
    },
    {
      "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
      "task_text": "- [ ] **AKX-ALL-31.GDN — Deterministic one-hot GATED_DELTA_NET state oracle (intake-2574#record, intake-2550#record).** Add a test-backend-ops case on an experimental champion-derived branch that drives the delta rule with gate held at 1, beta at 1 and one-hot keys, so each step overwrites exactly one state row and a one-hot query must read back that row; compare against the closed-form result. Cover CPU f32, gfx90a f32 and BF16 state, and K > 1 snapshot slots. The current cases only compare backends on random data, which cannot detect a shared indexing error."
    },
    {
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree build three seeded-race HIP mutants, each deleting one barrier in MMQ, MMVQ and the FA kernel, and run the served-shape suite 20 times each. CPU: build test-backend-ops with ThreadSanitizer, using LLVM libomp with Archer annotations, and run the threaded ops. Decision rule: if any GPU mutant passes the gate in all 20 runs, open the gfx90a race-only symbolic-executor trigger; if all are caught, record the gate as race-sensitive at these sites. The v10 anchor must produce zero TSAN reports beyond a documented suppression list."
    },
    {
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "task_text": "- [ ] **RVP-CTR-1 — Counter-grounded planner signals for the GPU AK lane (intake-2556#record).** For the top hotspot kernel of each GPU screen, capture a fixed declared counter subset with rocprofv2 (occupancy, LDS bank conflicts, VALU/MFMA busy, memory unit stall, achieved bandwidth) and pass it to the planner with the rule that every proposed idea must cite a counter that is present, and a missing counter may not be treated as zero. Compare 2 planner rounds with and without counters on the same target and budget."
    },
    {
      "owner": "handoffs/active/agentic-rocm-kernel-authoring.md",
      "task_text": "- [ ] **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).** Store the hipcc --save-temps .s (or llvm-objdump of the code object) of each touched kernel in the candidate record next to its source diff. When a candidate claims a mechanism (MFMA, LDS staging, buffer loads), confirm in the ISA, and with a rocprof instruction counter where one exists, that the instruction executes on the measured path; a candidate whose claimed instruction is absent is refused."
    },
    {
      "owner": "handoffs/active/conversation-stack.md",
      "task_text": "- [ ] **CS-8.STT8 — Scratch upstream audio build and end-to-end speech-model STT arms (intake-2552#record, intake-2575#record, intake-2579#record, intake-2580#record).** On a llama.cpp-experimental branch, build current upstream (b11960 or later, which carries the LFM3 architecture, mtmd_audio_stream and the /v1/realtime server) for CPU and gfx90a in an isolated prefix with its own LD_LIBRARY_PATH, proven with verify_ggml_linkage.sh. Record the forward-port distance from v10 (PRs 31252, 31257, 30629, 30636, 31269, 31287, 31386) and the build effort. Then add two arms to the CS-8.STT5 screen on the pinned FLEURS en/it clips with the CS-8.STT1 scorer: LFM3-Audio-2B (ASR mode) and Voxtral-Mini-4B-Realtime via mtmd-cli streaming, baselines frozen whisper large-v3-turbo and parakeet-cli. Rule: an arm advances to the CS-8 bake-off gates only if its paired 95% bootstrap WER difference versus whisper is not above +1.0 pp in both en and it; vendor tables are not evidence."
    },
    {
      "owner": "handoffs/active/conversation-stack.md",
      "task_text": "- [ ] **CS-8.RT1 — /v1/realtime first-output latency and turn contract on EPYC and MI210 (intake-2579#record, intake-2575#record).** With the CS-8.STT8 scratch build, run the upstream realtime client against LFM3-Audio-2B on a CPU quarter and on the MI210, and measure time from end of input audio to first output audio over a frozen set of 20 utterances, plus barge-in: response.cancel latency to silence. The server does no turn detection (turn_detection is null), so the test drives commit, response.create and response.cancel from the client exactly as the CS-22 controller would. Compare against the cascade measured on the same utterances."
    },
    {
      "owner": "handoffs/active/typed-decision-plane.md",
      "task_text": "- [ ] **TD-23.D1 — Prepare d1-2B as TD-23's local compact decision backend, behind parity and batch-invariance gates (intake-2582#record, intake-2581#record, intake-2593#record, intake-2595#record, intake-2602#record).** Build a scratch upstream llama-server on llama.cpp-experimental from a fresh production tip that contains the /v1/systemone endpoint (PR 29818, merge a4cb4c61) as a measurement instrument, not a port onto v10; include the non-causal ubatch fix (PR 30408) only if the screened model is non-causal; read the LFM Open License v1.0 first. Before any quality number: (1) parity gate, the same d1-2B GGUF at BF16 and Q8_0 on CPU and on HIP, stop on any argmax flip or a worst probability difference above 2.2e-2; (2) batch-invariance gate, request alone at np 1 versus the same request co-batched at np 3 with shorter, longer and identical companions and across two batch cuts, threshold 1e-3. Run the screen at np 1 per decision server until an upstream hybrid-prefix fix lands, and pin np, n_batch and n_ubatch in the receipt. Only choice, score and noul answers are served. When CJ-15 and HS-TD-4 exist, d1-2B Q8_0 is the TD-23 local backend arm against the constrained incumbent on the sealed row-pinned workload."
    },
    {
      "owner": "handoffs/active/typed-decision-plane.md",
      "task_text": "- [ ] **TD-18.1 — Pin GGUF decision backends in the TD-18 calibration receipt (intake-2593#record).** For llama.cpp decision backends, the receipt records the GGUF sha256, every decision.temperature.* metadata value (the endpoint scales probabilities by them and exposes no request-time override), the server build commit, and the -np/-b/-ub flags, because each of these changes the probabilities being calibrated."
    },
    {
      "owner": "handoffs/active/routing-intelligence.md",
      "task_text": "- [ ] **RI-25 — Zero-inference fold replay over delegation records (intake-2565#record).** Apply the fold criteria (fold a sub-agent only if the folded version does not score worse; inspect which tasks flip; repeat runs) to existing orchestrator delegation records: for each delegate() role (worker_math, worker_general, worker_summarize share one model), measure from records how often a chain needs the role's own context, how much of the 4,000-character truncated hand-off (src/repl_environment/routing.py:581) reaches the worker, and how often the delegated answer is re-asked by the caller. Output a per-role fold-candidate table; no serving change."
    },
    {
      "owner": "handoffs/active/agentic-serving-harness-fixes.md",
      "task_text": "- [ ] **UFH14-TOOLS-1 — Count and cap the model-visible tool surface per role (intake-2565#record).** Enumerate what each role's prompt actually advertises (about 55 REPL globals plus about 55 registry tools behind TOOL/CALL) and log the count per role and per turn. Frontdoor turns called a tool in only 3.8-4.9% of turns (this handoff, line 670), so a large advertised surface costs prompt tokens for little use. Propose a per-role allowlist with deferred loading for the rest, behind a flag, for a later A/B."
    },
    {
      "owner": "handoffs/active/context-folding-progressive.md",
      "task_text": "- [ ] **CF-AKV-0 — Zero-inference screen: how much resident context old tool results hold (intake-2590#record, intake-2596#record).** From existing orchestrator serving records and REPL traces, compute per long agent loop the share of resident context held by tool responses older than the last two turns, and the share of decode steps above 48K context. Escalate to the trigger-gated KV-drop semantics probe only if the median long loop holds at least 40% old tool results and at least 20% of decode steps exceed 48K tokens."
    },
    {
      "owner": "handoffs/active/vidya-belief-substrate-program.md",
      "task_text": "- [ ] **VB-CERT-1 — Independent checker for the gate certificate (intake-2558#record).** Write scripts/vidya/cert_check.py, a standalone verifier of epyc.vidya/certificate/v1 that shares no imports with fold.py, gate.py or lattice code, re-derives the verdict from the certificate's stated inputs, and compares certificate.frontier and as_of explicitly. Today certificate_hash is a self-hash and input_attestations holds labels rather than the digests the spec section 11.2 requires (scripts/vidya/gate.py:130-166). Add forged-certificate tests (altered verdict, swapped frontier, stale as_of, label-only attestation) that must be rejected."
    }
  ]
}
```
