# Stage-3 plan — ws58 research intake 2026-10-31 (intake-2545..2602)

Status: PROPOSED, awaiting operator approval. Nothing below is applied. Stage 4 is applied by the owning session after approval; no index row is added or changed by this plan.

Session: `intake-ws58-20261031`. Lane worktree `/mnt/raid0/llm/worktrees/intake-ws58-20261031`. Dive artifacts `/mnt/raid0/llm/tmp/dive-ws58-20261031/`.

## Scope and process

- 23 operator URLs plus 9 Stage-1 expansions (intake-2545..2576); every medium-or-higher source dived in wave 1 (29 entries).
- Stage-2b waves 2-4 ingested and dived 26 surfaced sources (intake-2577..2602). Waves 1-4 ran before the first plan; wave 5 (five helpers, 2026-11-01) answered the operator's revision points and re-dived intake-2563. Five of six permitted waves are used; the remaining surfaced items were declined with reasons recorded on the entries they came from.
- Verification: 57 dive-verified, 2 dive-overturned (intake-2553#record: d1-Omni does have a llama.cpp path; intake-2594#record: the Q8_0 collapse was a Metal bug, not quantization). Every anchor was re-found mechanically and checked by an independent second reader; 7 objections were resolved by dropping or narrowing anchors.
- Stage-1 defect caught: Stage-1 fetchers attached 7 cross-reference arXiv ids that were not in the fetched sources; all were removed before persisting.

## Revision 2 (2026-11-01): answers to the operator's eight points

1. **Soft-MTP / drafter fine-tuning: actionable now (P2, DF2-FT-1).** On a frozen trunk, Soft-MTP is forward KL toward the target. The first target is the served 27B DFlash2 drafter (1.9B parameters). It accepts 0.29-0.39 on production agentic traffic against 0.62-0.73 on the benchmark. Capture is 61,440 bytes per token, 50-75 GB, and at most 3 MI210-hours. Training is about 36 GB at bf16, at most 4 MI210-hours per arm. The pilot needs about 13 MI210-hours plus 4-6 desk days, and reuses NeMo Automodel train_dflash2 and the existing GGUF converter. Its arms are the incumbent, a convert-only round trip, a hard-label fine-tune and a KL fine-tune (two seeds), replayed twice on held-out traffic. It promotes at +0.05 acceptance and +8% decode speed with no benchmark loss. The scale-up is trigger prose gated on that result. The frontdoor 35B-A3B head and the Flash-Next head (+2-5% estimated, 1-2 weeks of porting) follow, named by DF2-FT-1. MTP-2 and MTP-4 are folded in.
2. **Upstream fold (P9, CH-32..CH-37, champion program).** Only #28123 is already in champion C5. CH-32 runs a merge-tree census at no compute cost. CH-33 folds the non-causal ubatch fix, a safety fix for embedding and decision models served at np>1. CH-34 folds the looped archs (Nanbeige merged upstream, Ouro open). CH-35 folds the audio/LFM3/realtime group, gated on CS-8.STT8 and CS-8.RT1. CH-36 folds systemone and H2O-Lightning, gated on the TD-23.D1 gates. CH-37 holds the recurrent-state/np>1 fixes, gated on DF2-12.1. The Metal-only fix is declined. The main conflict surface is server-context.cpp, where the champion is already +593 lines.
3. **Looped models on the GPU (P10).** The earlier pass did ignore the GPU. Sequential loops still cost about 1/L aggregate on the MI210, because batching removes only the weight term. Small MHA models like Ouro-1.4B are KV-bound beyond about 123 tokens of context. Parallel loops (PLT) are the form that fits the GPU. Filed: GPU-LOOP-1 (build and roofline grid), GPU-LOOP-2 (Ouro 1/2/4 loops as a high-concurrency reliability worker against Qwen3-4B, Qwen3-1.7B majority-of-4 and the incumbent), GPU-LOOP-3 (per-request loop count as an effort switch, promoted if a router keeps 97% of 4-loop accuracy at 0.6x cost), GPU-PLT-1 (LoopCoder-v2 quality screen) and GPU-PLT-2 (our own PLT port, 1.0-1.5k lines).
4. **Triggers turned into tasks.** PLT is ported by us (GPU-PLT-2). The gfx90a race executor is built now (RVP-RACE-2). ThinkingCap is an A/B for a thinking-on effort mode (AMS-TCAP-1). The ISA-level lowering probe is C5-ISA-2. The failure-to-rule loop runs on existing records (AK-FAILRULE-1). Every remaining trigger is gated either on one of our own probes (DF2-LAT, DF2-12.1, CF-AKV-0, RI-25, CS-8.STT8, TD-23) or on a named external release (Dessa weights, a served-vocabulary NCM generator, looped-MoE weights).
5. **Octopus-SI-OS (P12, re-dived as intake-2563).** Four mechanisms fix failure modes the intake has already recorded. ID-RI-ANCHOR-GATE adds script-written anchor marks and a cross-entry quote check, against fabricated citations. ID-RI-LANE-HEAD pins the lane revision and flags a stale epoch, against stale clones. ID-RI-STAGE-GUARD makes the stage write grant script-formed, against stage violations. ID-RI-DECLINE-VOCAB closes the list of decline codes, against dropped actionables. Four other Octopus mechanisms are declined as already covered.
6. **Resin vs Annex K.** Resin is weaker on every statistical axis. It has no A/A noise floor and no MDE, no e-process keep rule, no order-randomized interleave, no anchor gate, and no clock, governor or driver capture. Its only rule is to repeat a measurement when the gain is close to run-to-run variation. It is stronger in four places: a dirty-tree source digest, graph and overlap counters measured inside the timed window, a proof that JIT compilation finished before timing, and union-not-sum trace attribution. Those become AK-WIN-CNT-1 and AK-PROF-ATTR-1 (P3). The earlier AGENT-9 decline is reversed.
7. **Volta on gfx90a.** Port the race and deadlock checking now (RVP-RACE-2). Only the PTX front end is NVIDIA-specific; the event graph is ISA-neutral. The check runs at the AMDGCN code-object level, not LLVM IR. In the v10 code object, MMVQ, MMQ and both FA paths use s_barrier, and 15 of 31 AK GPU keeps touch synchronization. Cost: 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks. Milestone 1 covers MMVQ and FA-vec and must catch the seeded mutants. Equivalence checking is declined for the quantized kernels on coverage, because about 75% of AK GPU rows are bit-level code. A probe decides it for FA, GDN and float GEMV (RVP-EQV-1). RVP-RACE-1 is amended: a mutant counts as a miss if it passes even 1 of 20 runs.
8. **Qwenputer on a small GPU model.** Re-priced, it still loses: chip tokens run serially at 0.5-1 s per call, and accuracy only ties a tool call. It stays declined with this GPU reason (D1). The GDN exactness oracle (AKX-ALL-31.GDN) remains the transferable piece.
General. **GPU re-check of every CPU-bandwidth verdict.** LOOP-1/4/5, W2LOOP-1/2/3, MEM-3, LOOP-6 and the Volta decline were re-priced for the MI210. Five became tasks, and three stay declined with GPU-specific or external-event reasons.

## Top findings

1. **Live correctness exposure.** The :8070 frontdoor (Qwen3.6-35B-A3B, draft-MTP, np 4) and :8083 (27B DFlash2, np 4) run speculative decoding at np>1 with no token-identity record. llama.cpp #28286 reports cross-slot contamination with MTP at np>1 on Qwen3.8-Flash-Next and closed without a fix; #28019 adds an untested slot-reuse condition. Our tree has the same unwritten-snapshot-slot code shape. (P1)
2. **DCOCO is not new to us.** DFlash2 already ships a learned top-16, rank-256 candidate selector with a prefix-first walk. DCOCO's headline gain mostly comes from joint drafter retraining (+4.4% when the drafter is frozen). What matters is the remaining headroom, which one offline dump can measure. (P2)
3. **AK gate blind spots confirmed in code.** No race detector, no edge-value inputs, NMSE-only oracle. The AI-compiler papers show that formal verification costs speed and covers few hot kernels, so cheap planted-control checks and enumeration are the practical path. (P3)
4. **Upstream llama.cpp now serves end-to-end audio models.** LFM3-Audio/Omni and Voxtral Realtime run through `mtmd_audio_stream` and `/v1/realtime`, about 1,650 builds past v10. Only vendor numbers exist, so a scratch build and STT arms on our pinned clips decide. (P4)
5. **d1 decision models have a llama.cpp path** through `/v1/systemone`. They fit TD-23's missing local backend, but probabilities move with batch cut and build, so parity and batch-invariance gates come first. (P5)
6. **Drafter fine-tuning is actionable.** Soft-MTP on a frozen trunk is forward KL. The served 27B DFlash2 drafter accepts 0.29-0.39 on production traffic against 0.62-0.73 on the benchmark, and a KL fine-tune pilot fits the MI210 at about 13 GPU-hours. ThinkingCap becomes an A/B for a thinking-on effort mode, because thinking is off today only on account of degenerate loops. (P2, P8)

## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Temp-0 cross-slot token identity on the np>1 speculative roles, recurrent-state hash conformance, acceptance-collapse canary, multi-prefill promotion arm | handoffs/active/dflash2-block-drafter-experimental-build.md |
| P2 | DFlash2 lattice-headroom and point-mass probes; KL fine-tune pilot of the served 27B drafter on its own traffic (MI210) | handoffs/active/dflash2-block-drafter-experimental-build.md |
| P3 | AK correctness and planner gates: edge-value families, worst-error bound, quant-decode enumeration, GDN oracle, counter-grounded planning, in-window counters, failure-to-rule loop | handoffs/active/autokernel-all-devices-all-dimensions.md |
| P4 | Scratch upstream audio build; LFM3-Audio and Voxtral STT arms; /v1/realtime latency and turn contract | handoffs/active/conversation-stack.md |
| P5 | d1-2B as TD-23 local decision backend behind parity and batch-invariance gates; GGUF pin in the calibration receipt | handoffs/active/typed-decision-plane.md |
| P6 | Zero-inference agent-loop screens: fold replay, advertised tool surface, old tool-result context share | handoffs/active/routing-intelligence.md |
| P7 | Independent checker for the vidya gate certificate | handoffs/active/vidya-belief-substrate-program.md |
| K1 | Speculative-decoding knowledge notes (DFlash2 already has a learned selector; drafter recipes; Axis-E head on disk) | handoffs/active/dflash2-block-drafter-experimental-build.md |
| K2 | Architecture and roofline notes (looped models, GDN beta cap, stale llama.cpp-compatibility note) | handoffs/active/cpu-decode-roofline-program.md |
| K3 | KV editing and agent-loop design notes (history-keyed reuse, C2C mapping, single-loop caveat) | handoffs/active/kv-prefix-fork-and-paged-attention.md |
| K4 | Speech and decision-backend notes (Parakeet/transcribe.cpp already owned; realtime turn contract; d1 API subset) | handoffs/active/conversation-stack.md |
| K5 | Kernel-authoring notes (prompt-leak guard; agent-harness token cost) | handoffs/active/agentic-rocm-kernel-authoring.md |
| M1 | Speculative-decoding triggers gated on our own probes (trained selector port, Domino head, drafter scale-up after the pilot, thinking-repetition guard) and on an external NCM release | handoffs/active/dflash2-block-drafter-experimental-build.md |
| M3 | KV drop and cross-model cache triggers (gated on the context-share screen; fusers for served pairs) | handoffs/active/kv-prefix-fork-and-paged-attention.md |
| M4 | Speech and decision-model triggers (LFM3 as bake-off challenger, realtime adapter, Dessa, spoken-state decider, generic readout, hybrid prefix fix) | handoffs/active/conversation-stack.md |
| P8 | ThinkingCap Flash-Next as a thinking-on effort mode for architect_general (A/B, decision rule) | handoffs/active/architect-model-selection-bench.md |
| P9 | Fold upstream llama.cpp features into the champion: merge census, non-causal ubatch fix, looped archs, audio/realtime, systemone, recurrent-state fixes | handoffs/active/autokernel-champion-aggregate.md |
| P10 | Looped models on the MI210: build and roofline grid, reliability-worker probe, per-request loop count, LoopCoder-v2 screen and PLT port | handoffs/active/gpu-acceleration-path.md |
| P11 | GPU kernel verification on gfx90a: race-sensitivity controls, AMDGCN race/deadlock executor, equivalence probe, ISA archive and ISA-level lowering | handoffs/active/rocm-verify-profile-backend.md |
| P12 | Research-intake skill hardening from the Octopus ledger/grant design: script-written anchors, lane-revision pins, stage write grants, closed decline codes | handoffs/active/intake-derived-work-2026-07-25.md |

Ordering and concurrency: P1-P7 are independent and can run in parallel. Within P1, the rollback test inside DF2-12.1 runs first; G2-CONC.MP applies at the next promotion. Within P2, DF2-LAT and DF2-PM share one experimental build. P4 and P5 each use their own scratch upstream build. P6 and P7 are zero-inference. Twelve immediate packets survive because each has a different owner, consumer and gate; merging them would bundle unrelated work. P9 folds depend on the consumer measurements in P4, P5 and P10 and on DF2-12.1, as each fold task states; P11 milestone 1 uses the RVP-RACE-1 mutants.

Minimum-rigor controls. Empirical items (DF2-12.1, DF2-LAT, DF2-PM, DF2-FT-1, RVP-RACE-1, RVP-EQV-1, RVP-CTR-1, C5-ISA-2, CS-8.STT8, CS-8.RT1, TD-23.D1, AMS-TCAP-1, GPU-LOOP-1/2/3, GPU-PLT-1, RI-25, CF-AKV-0, AK-FAILRULE-1) each name in their task text a frozen input manifest, the incumbent baseline, per-item raw outputs, a holdout or repeat (dev/holdout prompts, a second seed, or interleaved pairs), the full denominator, and a predeclared decision rule. Deterministic items (KPF-RS-1, SPEC-CANARY.1, G2-CONC.MP, AKX-ALL-31.EDGE/b/c, C5-ISA-1, DF2-DRAFTER-CAPABILITY.OBJ, TD-18.1, UFH14-TOOLS-1, VB-CERT-1) have no holdout. Each instead names a planted mutation or forged case that must fail, plus a conformance check against the incumbent.

## Operator decisions

- **D1 (MEM-3, decline to confirm, re-priced for the GPU).** Do not serve a Qwenputer-style in-weights calculator. On a small model on the MI210, its chip tokens still run serially: 0.5-1 s per call, and a median 242 s per long division on an L4. Text tokens cost twice the weight bytes, and accuracy only ties a tool call. Recommendation: confirm the decline. The source stays as knowledge.
- **D2 (scratch upstream builds).** P4 and P5 use scratch upstream llama.cpp builds on llama.cpp-experimental as measurement instruments. Each has its own LD_LIBRARY_PATH and a linkage proof. P9 folds what proves out into the champion; production changes only through the version-past-production path. Recommendation: approve.
- **D3 (budget).** RVP-RACE-2 is 6-9 engineer-weeks, staged by milestone. DF2-FT-1 is about 13 MI210-hours plus 4-6 desk days. AMS-TCAP-1 is a 95.5 GB download. Recommendation: approve. Each first milestone has its own stop rule.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| AGENT-1 | intake-2565 Stage-2 dive w1 ledger | Run the fold article procedure as a zero-inference REPLAY over existing delegation records: for each delegate() role (worker_math, worker_general, worker_summarize, worker_vision, coder_escalation) compute from _delegations artifacts / delegation reports the ... | P6 / RI-25 |
| AGENT-10 | intake-2562 Stage-2 dive w1 ledger | Use Resin docs/cache-pool.md + architecture.md Prefix reuse as design reference for hybrid prefix reuse: its snapshots are taken at an alignment equal to the LCM of all group block sizes and restore attention, SWA and recurrent state at the same boundary, ... | K3 |
| AGENT-11 | intake-2562 Stage-2 dive w1 ledger | Decline engine/runner split as an adoption target: there is no CPU or ROCm runner, and production serving is llama.cpp (frozen v10). Treat the split as vocabulary only. | decline: the Resin engine/runner split has no CPU or ROCm runner and production serving is llama.cpp. |
| AGENT-12 | intake-2553#record Stage-2 dive w1 ledger | Screen d1-Omni-2B-GGUF (Q8_0, 1.85 GB) and d1-2B-GGUF as local typed-decision backends on a separate, scratch-built upstream llama-server (b11960+ in its own build dir; production tree untouched). Probe: replay a frozen set of already-routed orchestrator ... | P5 / TD-23.D1 |
| AGENT-13 | intake-2553#record Stage-2 dive w1 ledger | Speech turn-taking decider test (only after human-recorded strata exist): d1-Omni-2B reads a short audio window and answers noul/score questions (end of turn? backchannel needed?) on the CS-45 corpus; compare against the CS-22 controller policy and the D1 ... | M4 |
| AGENT-14 | intake-2553#record Stage-2 dive w1 ledger | Read LFM Open License v1.0 and the Open d1 blog before any use beyond a screen (licence is not Apache/MIT; sourcing policy is open-source only). | P5 / TD-23.D1 |
| AGENT-2 | intake-2565 Stage-2 dive w1 ledger | Count and cap the model-visible tool surface: REPL exposes ~55 globals (peek, grep, delegate, escalate, run_shell, registry_*, benchmark_*, ...) in environment.py _build_globals while tool_registry.yaml holds 55 further tools (TOOL/CALL/list_tools = already ... | P6 / UFH14-TOOLS-1 |
| AGENT-3 | intake-2565 Stage-2 dive w1 ledger | Add a per-fold eval: before folding any worker role into skills, require a frozen end-to-end set covering every production chain (architect -> coder_escalation, frontdoor -> worker_*) and every must-not-break rule, repeated >=2 times, reporting flipped tasks. ... | M3 |
| AGENT-4 | intake-2565 Stage-2 dive w1 ledger | Do NOT adopt the article single-loop thesis for our CPU stack without measurement: the article premise is frontier models with thinking on; our workers are local quantised Qwen3.x on a BW-bound CPU where a separate small-context worker call is cheaper per ... | K3 |
| AGENT-5 | intake-2559, intake-2576 Stage-2 dive w1 ledger | Bounded offline probe on CPU (HF transformers, no llama.cpp): with released nics-efc/C2C_Fuser qwen3_8b+qwen2.5_7b fuser, run n=200 frozen items from a MC set the stack already scores (e.g. MMLU-Redux subset used in canonical suites) in 4 arms: Receiver-only, ... | M3 |
| AGENT-6 | intake-2559, intake-2576 Stage-2 dive w1 ledger | Design note (no compute): map C2C onto llama.cpp. Feasible path = out-of-process fuser. Receiver and Sharer each prefill the same prompt; read per-layer K/V from each via llama_state_seq_get_data (include/llama.h:881) or /slots/{id}?action=save ... | K3 |
| AGENT-7 | intake-2559 Stage-2 dive w1 ledger | Role-pair candidate list, ranked: (1) architect_critic / coder_escalation (Qwen3.8-27B Q8_0, dense KV-densest per model_registry.yaml:541) as SHARER -> worker_general/worker_summarize (Qwen3.6-35B-A3B MoE, receiver; must check whether its layers are all full ... | M3 |
| AGENT-8 | intake-2576 Stage-2 dive w1 ledger | Read the thu-nics AKV repo (cache engineering for agents, follow-up to C2C, Apache-2.0, pushed 2026-10-21) before sizing any pair-training, since it may cover agent KV reuse without a per-pair trained fuser. | K3 |
| AGENT-9 | intake-2562 Stage-2 dive w1 ledger | Copy the measurement-discipline text, not code, into the AK actor context: (a) record cache/graph/placement state and compare on the same allocation, (b) locate the limiting interval from a trace BEFORE kernel edits, (c) report the spread and do not call ... | P3 / AK-WIN-CNT-1 / AK-PROF-ATTR-1 |
| KERN-1 | intake-2570, intake-2555 Stage-2 dive w1 ledger | Race-sensitivity mutation control for the GPU correctness gate. In a llama.cpp-experimental worktree, build 3 seeded-race HIP mutants, each deleting one __syncthreads/barrier: MMQ tile load, MMVQ partial-sum reduction, FA tile softmax. Run the existing AK ... | P11 / RVP-RACE-1 |
| KERN-10 | intake-2570 Stage-2 dive w1 ledger | Wire a CPU race detector for routes touching threading. Build a TSAN test-backend-ops (CPU), using LLVM libomp with Archer annotations because production uses OpenMP; GGML_OPENMP=OFF would test a different threading path. Run it on the v10 anchor first. | P11 / RVP-RACE-1 |
| KERN-11 | intake-2570, intake-2557 Stage-2 dive w1 ledger | Do not adopt upstream Volta or the Blackwell fork directly. Both are PTX/NVIDIA-only, and this host has no NVIDIA GPU. Reuse only the race model (KERN-2) and the scaffold code. | P11 / RVP-RACE-2 |
| KERN-2 | intake-2557, intake-2570 Stage-2 dive w1 ledger | Build a race-only symbolic executor for gfx90a AMDGCN: parse hipcc --save-temps asm, concrete thread/workgroup indices and launch params, per-byte LDS reader/writer sets between s_barrier, lgkmcnt/vmcnt waits as completion points, exec-mask lanes, wave64. ... | P11 / RVP-RACE-2 |
| KERN-3 | intake-2555 Stage-2 dive w1 ledger | Add structured edge-value input families to the AK op suite beside the AK_SENS scale transforms. Families: f16-range near-max (overflow), subnormal-scale (underflow), cancellation pairs within reduction rows, softmax rows that are all-equal or contain -inf, ... | P3 / AKX-ALL-31.EDGE |
| KERN-4 | intake-2555, intake-2570 Stage-2 dive w1 ledger | Exhaustive bit-level decode check per served quant type (Q4_K, Q6_K, IQ2_*, IQ3_*, IQ4_XS, MXFP4). Enumerate the full per-element code space (quant codes x sub-block scale/min codes) at d/dmin in {0, subnormal, 1, f16 max}. Compare the candidate CPU (AVX-512) ... | P3 / AKX-ALL-31.QDEC |
| KERN-5 | intake-2556 Stage-2 dive w1 ledger | Add a per-element worst-error bound next to NMSE on the GPU served-shape case set. Calibrate the anchor's max-abs error per (op, type, shape) over 5 seeds and gate on k x anchor, the way the CPU_REPACK oracle already does. | P3 / AKX-ALL-31.EDGE |
| KERN-6 | intake-2555, intake-2556 Stage-2 dive w1 ledger | Counter-grounded planner signals. For the top-1 hotspot kernel of each GPU screen, capture a fixed, declared counter subset via rocprofv2 (from the proven 465-counter taxonomy). Attach it to the hotspots rows. Adopt TAIC's rule that each hypothesis cites a ... | P3 / RVP-CTR-1 |
| KERN-7 | intake-2555, intake-2556 Stage-2 dive w1 ledger | Archive the hipcc AMDGCN ISA (--save-temps .s, or llvm-objdump of the code object) of the touched kernels into every AK GPU candidate record, next to the source diff and the hotspots table. | P11 / C5-ISA-1 |
| KERN-8 | intake-2555, intake-2556 Stage-2 dive w1 ledger | GCN-Gym probe of AI lowering on gfx90a. Build a standalone harness that assembles LLM-patched AMDGCN for one compute-bound kernel (MMQ Q4_K prefill tile or FA at long context) with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a, loads it via hipModuleLoad and ... | P11 / C5-ISA-2 |
| KERN-9 | intake-2556 Stage-2 dive w1 ledger | Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population. | K5 |
| LOOP-1 | intake-2547, intake-2571 Stage-2 dive w1 ledger | Add a knowledge note to the INF-70 roofline program: weight-reuse architectures. Sequential looping multiplies weight bytes per token by L, and with 32 MiB L3 per CCX (384 MiB total) a block above ~32 MiB per CCX cannot be cache-reused (e.g. a 7B 14-layer PLT ... | P10 / GPU-LOOP-1 |
| LOOP-2 | intake-2571, intake-2547 Stage-2 dive w1 ledger | Ingest and dive LoopCoder-v2 (arXiv 2606.18023): released 7B PLT 2-loop coder (Apache-2.0, HF Multilingual-Multimodal-NLP/LoopCoder-V2, 14 layers, hidden 5120, 8 KV heads) is the first PLT checkpoint we can actually run; card claims SWE-bench Verified 43.0 -> ... | P10 / GPU-PLT-1 |
| LOOP-3 | intake-2547 Stage-2 dive w1 ledger | Correct the stale gate: Ouro now has a community llama.cpp port (BrandeisPatrick/loop-transformer, ouro arch, 324 added lines, PR ggml-org/llama.cpp#29823, GGUFs for Ouro 1.4B/2.6B +Thinking) built on upstream looped-model machinery merged for Nanbeige4.2 (PR ... | P9 / CH-34 |
| LOOP-4 | intake-2547, intake-2551 Stage-2 dive w1 ledger | Bounded CPU probe on a llama.cpp-experimental branch with the Ouro port: Ouro-1.4B Q4_K_M (854 MB per card), llama-bench tg at num_loops 1/2/4 via --override-kv, reporting achieved GB/s counting bytes once per loop against the C0 153 GB/s ceiling. This ... | P10 / GPU-LOOP-1 / GPU-LOOP-2 |
| LOOP-5 | intake-2551 Stage-2 dive w1 ledger | Record in reasoning-compression.md only: looped MoE R=5 at 0.3B-1.3B reaches reasoning parity with 0.6B-2.9B at 1.8x training-compute-defined inference compute while trailing Overall 46.9 vs 50.2; no latency/bytes measured; no checkpoint released in the text. | decline: no looped-MoE checkpoint or code is released, and on the GPU looping a MoE multiplies expert byte reads rather than hiding them. |
| LOOP-6 | intake-2546, intake-2568 Stage-2 dive w1 ledger | Monitor NCM as a drafter source: trigger = a released NCM-style generator with a general-text tokenizer sharing a served model vocabulary, or any measured acceptance rate against an AR target. Do not build now: released checkpoints are per-dataset ~100M-725M ... | M1 |
| MEM-1 | intake-2550, intake-2574 Stage-2 dive w1 ledger | Add a deterministic one-hot RAM oracle case to the GATED_DELTA_NET tests of an EXPERIMENTAL champion-derived llama.cpp branch (tests/test-backend-ops.cpp test_gated_delta_net family, or a sibling test-gdn-ram): alpha=1 (g=0), beta=1, one-hot k and q, ... | P3 / AKX-ALL-31.GDN |
| MEM-2 | intake-2574 Stage-2 dive w1 ledger | Add a state-level conformance check to the hybrid checkpoint/fork path: after a restore (common_prompt_checkpoint load_tgt, or KPF fork from a checkpoint) serialise the recurrent half of source and destination with llama_state_seq_get_data_ext(PARTIAL_ONLY) ... | P1 / KPF-RS-1 |
| MEM-3 | intake-2550, intake-2574 Stage-2 dive w1 ledger | Do not pursue an in-weights calculator (compiled RISC-V/CHIP-8 layers) for the serving stack. Flag for operator review per the research-intake rule rather than closing silently. | decline: re-priced on the GPU, the in-weights calculator still loses: chip tokens are serial (0.5-1 s per call, median 242 s per long division on an L4), text tokens cost twice the weight bytes, and accuracy only ties a tool call; operator confirmation requested. |
| MEM-4 | intake-2558 Stage-2 dive w1 ledger | Write scripts/vidya/cert_check.py: a standalone verifier for the gate's epyc.vidya/certificate/v1, sharing NO imports with fold.py, gate.py or lattice.py. It reads the ledger JSONL and the ratified policy file directly, re-derives pro/con grade dominance and ... | P7 / VB-CERT-1 |
| MEM-5 | intake-2558 Stage-2 dive w1 ledger | No certificate/checker layer for scripts/handoffs/index_state.py or registry consistency checks. | decline: the handoff index check already re-derives and compares on every run, so a certificate layer adds nothing. |
| MEM-6 | intake-2558 Stage-2 dive w1 ledger | When writing MEM-4, make the checker read and compare certificate.frontier and as_of explicitly and record in the certificate's proves-field that a certificate binds to a frontier, not to the truth of the world. | P7 / VB-CERT-1 |
| MTP-1 | intake-2548#record, intake-2549 Stage-2 dive w1 ledger | Amend the DF2-DRAFTER-CAPABILITY trainer and data contract (the INF-62 record contract inherited from the cancelled DF2-QWOPUS) so the default objective is forward-KL self-distillation to the target's own teacher-forced NTP distribution rather than hard ... | P2 / DF2-FT-1 |
| MTP-2 | intake-2548#record, intake-2549 Stage-2 dive w1 ledger | Bounded frozen-trunk probe on the Soft-MTP repo (MI210, ROCm torch, <=4 GPU-h, no llama.cpp). Take the released 167M (or 332M) NTP checkpoint, set freeze_backbone=true, and train fresh K=3 DeepSeek-style heads under two arms with identical data order, seed, ... | P2 / DF2-FT-1 |
| MTP-3 | intake-2548#record Stage-2 dive w1 ledger | No change to Axis E. Restoring the Qwen3.8-Flash-Next MTP head loads the published unsloth shared-Q8_0 head (no training), so the MTP-objective choice does not touch it. | K1 |
| MTP-4 | intake-2548#record Stage-2 dive w1 ledger | Record a trigger on the speculative-decoding refresh. If a served fine-tune ships with a stock (base-co-trained) MTP head, as already observed for ThinkingCap and Qwopus, the remedy is head-only re-alignment on the frozen fine-tuned trunk against its own NTP ... | P2 / DF2-FT-1 |
| MTP-5 | intake-2548#record Stage-2 dive w1 ledger | Decline adopting Soft-MTP as a pretraining objective. | decline: Soft-MTP as a pretraining objective needs trunk training, which this stack does not do. |
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
| SPEECH-3 | intake-2575 Stage-2 dive w1 ledger | Estimate and record forward-port cost: experimental branch from current production-consolidated-v10, merge/cherry-pick the 7 LFM3 audio PRs plus their upstream prerequisites (b10303..b11960 is 1657 builds; PR 31257 alone +2721/-160 over 31 files, 30629 +998, ... | P9 / CH-32 |
| SPEECH-4 | intake-2575 Stage-2 dive w1 ledger | Reuse the upstream /v1/realtime (OpenAI-compatible) and Voxtral-Realtime support as a CS-20 backend interface option: write a realtime client adapter in the voice controller that speaks /v1/realtime beside the whisper :9000 / qwentts :9002 cascade. | M4 |
| SPEECH-5 | intake-2573 Stage-2 dive w1 ledger | No new STT action. Hex confirms the transcribe.cpp Parakeet Unified streaming path (Vulkan GPU only). Parakeet streaming vs whisper.cpp is already a measured-pending candidate: CS-8.STT0 40/40 CPU==GPU identity done, transcribe.cpp CPU 40-clip run 37/40 ... | K4 |
| SPEECH-6 | intake-2573 Stage-2 dive w1 ledger | Add Parakeet Unified English (streaming, lookahead variants) as a named arm check in CS-8.STT5 if not already present, noting hex pins fork rev 7045d1c0 (transcribe.cpp 0.4.1) while our build pins db678a03; record both pins. | K4 |
| SPEECH-7 | intake-2564 Stage-2 dive w1 ledger | Monitor Dessa for paper, weights or API; trigger = any released checkpoint or paper with benchmark numbers, then fold into the M8 full-duplex reference slot check (language gate D2 likely fails if English-only). | M4 |
| TCAP-1 | intake-2567, intake-2572 Stage-2 dive w1 ledger | Bounded A/B: base UD-IQ4_XS (current :8074 file) vs bottlecapai ThinkingCap IQ4_XS GGUF, llama-server, same recipe qwen38-flash-next-cpu-mtp, enable_thinking=true on /v1/chat/completions, frozen 40-60 prompt set (arch/plan-critique + reasoning, AIME-style, ... | P8 / AMS-TCAP-1 |
| TCAP-2 | intake-2572 Stage-2 dive w1 ledger | Record that INF-70 Axis-E "MTP needs FP8 re-download" is obsolete: head already on disk (mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf, 2.79 GB, 2026-09-02); no ThinkingCap download is needed for MTP | K1 |
| TCAP-3 | intake-2572 Stage-2 dive w1 ledger | If A/B runs, add arm B2 = ThinkingCap trunk + our unsloth shared-Q8_0 draft file vs embedded head, measure alpha for both | P8 / AMS-TCAP-1 |
| TCAP-4 | intake-2567 Stage-2 dive w1 ledger | Do not pursue the vendor PRO tier or method discovery | decline: the vendor PRO tier is closed and no method is disclosed. |
| W2KERN-1 | intake-2588 Stage-2 dive w2 ledger | Add an instruction-executed gate to the AMD kernel-authoring path: when a candidate claims a mechanism (MFMA use, LDS staging, buffer/global load width), require a rocprof instruction-mix counter or ISA-disassembly execution check on the real workload before ... | P11 / C5-ISA-1 |
| W2KERN-2 | intake-2588 Stage-2 dive w2 ledger | Compare AK candidate generation as plain multi-turn refinement vs agent-harness mode on token cost per accepted keep (PTXBench: agent harness cost 3.3-5.1x tokens and was worse on attention). Use existing AK run logs only; no new compute. | K5 |
| W2KERN-3 | intake-2589, intake-2588 Stage-2 dive w2 ledger | Close the verified AK gate gaps (no race detector, race_detector_id=None; no edge-value inputs; NMSE-only oracle) with a CAKE-style pre-GPU static filter tier: run the cheapest hazard/legality checks (LDS barrier ordering, wave64/exec-mask hazards from the ... | P3 / AKX-ALL-31.EDGE |
| W2KERN-4 | intake-2589 Stage-2 dive w2 ledger | Failure-to-rule loop for AK: after each rejected batch, classify the failure reason and, when a class recurs (>=3), have an agent propose a permanent static check or oracle input, merged only under corpus tests of all prior keeps (CAKE Sec 3.2). | P3 / AK-FAILRULE-1 |
| W2KERN-5 | intake-2590 Stage-2 dive w2 ledger | Bounded probe: tool-result KV drop+shift on a pure full-attention role in llama-server, using existing llama_memory_seq_rm + seq_add (as in the streaming-llm / context-shift path), on a recorded orchestrator agent trace. Measure (a) tokens re-prefilled per ... | M3 |
| W2KERN-6 | intake-2590 Stage-2 dive w2 ledger | Record the history-dependence correctness rule for any future KV-editing serving feature: a slot/prefix index keyed only by token prefix (src/inference/prefix_index.py) must also key on the drop/shift operation history, or mark the slot unmatchable after an ... | K3 |
| W2KERN-7 | intake-2590 Stage-2 dive w2 ledger | Decline porting AKV server (SGLang, Rust build, softmax-attention only) as a serving path; keep as design reference only. Hybrid/linear-attention models (our main Qwen line) are unsupported by the authors and by llama.cpp seq ops. | decline: the AKV server is SGLang and softmax-only; it stays a design reference. |
| W2LOOP-1 | intake-2585, intake-2586 Stage-2 dive w2 ledger | On an experimental llama.cpp branch freshly cut from production v10, cherry #25994 plus #29823 (about 590 added lines) and measure Ouro-1.4B Q8_0/Q4_K_M at --override-kv ouro.num_loops=int:1/2/4 on EPYC CPU (one quarter and full socket): tok/s, achieved GB/s ... | P10 / GPU-LOOP-1 |
| W2LOOP-2 | intake-2584 Stage-2 dive w2 ledger | Monitor triggers: (a) llama.cpp or vLLM PR adding iquestpltcoder / PLT, (b) an independent replication of LoopCoder-v2 R=2 SWE-bench Verified, (c) a timing number for PLT decode. Any one fires ingest-and-dive on it. | P10 / GPU-PLT-2 |
| W2LOOP-3 | intake-2587 Stage-2 dive w2 ledger | Knowledge-only: record that our GDN graph hard-caps beta at 1 (src/models/qwen3next.cpp:417 ggml_sigmoid) matching the Qwen3.5 control that failed to generalise hidden tracking; no probe. | K2 |
| W2LOOP-4 | intake-2585, intake-2586 Stage-2 dive w2 ledger | Correct the stale note in gpu-acceleration-path.md ~line 248 (intake-332 "Not llama.cpp compatible") to say nanbeige looped arch merged 2026-07-27 and Ouro is PR #29823 open; owning session applies. | K2 |
| W2SP-1 | intake-2579, intake-2575 Stage-2 dive w2 ledger | Build upstream master (or tag b11960+) as a SCRATCH llama-server on llama.cpp-experimental from fresh production; run examples/realtime_client.py with LFM3-Audio-2B Q8_0 and Q4_0 on the EPYC CPU and MI210 and record first-output-after-end-of-input, with a ... | P4 / CS-8.RT1 |
| W2SP-2 | intake-2579 Stage-2 dive w2 ledger | Specify the server-turn contract in CS-22: because /v1/realtime has turn_detection null, our controller (VAD + CS-47 semantic gate) must send commit/response.create/response.cancel; add this as the integration seam in CS-22.A1 rather than waiting on a server ... | K4 |
| W2SP-3 | intake-2582, intake-2581, intake-2583 Stage-2 dive w2 ledger | TD-23 screen: d1-2B-GGUF Q8_0 via /v1/systemone (scratch upstream build, CPU quarter or MI210 window) versus the constrained incumbent readout, on a frozen, row-pinned labelled routing set (the TD-11 / CJ-15 sealed workload; labels from the routing-replay ... | P5 / TD-23.D1 |
| W2SP-4 | intake-2582 Stage-2 dive w2 ledger | Record in TD-23 candidate list that d1-2B/3B are VL models with LFM Open License v1.0 and that the llama.cpp path supports noul/choice/score only; routing questions are choice+score so the subset is sufficient. | K4 |
| W2SP-5 | intake-2581 Stage-2 dive w2 ledger | Spoken-state decision probe (turn completeness / intent) with d1-Omni-2B on the CS-45 turn-taking corpus once human_recorded strata exist; score with the CS-45 measurands against the CS-47 semantic-gate arms. | M4 |
| W2SP-6 | intake-2580, intake-2383 Stage-2 dive w2 ledger | Add a Voxtral-Mini-4B-Realtime GGUF through mtmd-cli run_audio_stream arm to the CS-8.STT5 screen (ranks and rejects only) on a scratch upstream build; record encoder and decoder times separately as the CLI already prints them. | P4 / CS-8.STT8 |
| W3DEC-1 | intake-2593, intake-2594#record Stage-2 dive w3 ledger | Add a precision-and-backend parity gate to the TD-23 decision-backend screen BEFORE any quality or calibration number is read: for the chosen decision GGUF (d1-2B Q8_0 first), serve the BF16 file on CPU as reference, then Q8_0 on CPU, Q8_0 on HIP (MI210), and ... | P5 / TD-23.D1 |
| W3DEC-2 | intake-2595, intake-2593 Stage-2 dive w3 ledger | Add a batch-/schedule-invariance gate to the same screen: serve with -np 3, -b = -ub = 2048 (state must fit one ubatch), send request A alone (x5), then A concurrently with a shorter, a longer and an identical companion (x5 each, with a blocker request to ... | P5 / TD-23.D1 |
| W3DEC-3 | intake-2593, intake-2581, intake-2582 Stage-2 dive w3 ledger | Plan the build route for any /v1/systemone work: the frozen v10 tree has neither the endpoint (PR 29818 merge a4cb4c61 is not an ancestor of ffc1bac82; no systemone string; no *decision* file in tools/server) nor LFM3 (needs >= b11960). Cheapest honest route ... | P5 / TD-23.D1 |
| W3DEC-4 | intake-2593, intake-2582 Stage-2 dive w3 ledger | Record in the TD-18 calibration receipt the model pin that determines the probabilities: GGUF sha256, every decision.temperature.* metadata key/value (read with gguf-dump), llama.cpp build SHA, -b/-ub/-np, and the question kind plus option count (some ... | P5 / TD-18.1 |
| W3DEC-5 | intake-2593, intake-2595 Stage-2 dive w3 ledger | Pin the serving-safe API subset for the probe and any shim: only choice/score/noul; options within the model limit (52 openjev, 255 laya; read from the model, d1 limits unread); state must fit one ubatch (use -ub, not -b; 30073); avoid router mode with ... | K4 |
| W3DEC-6 | intake-2596, intake-2590 Stage-2 dive w3 ledger | Add one binding design line to the KV prefix-fork program: any future KV-editing operation (cell drop, position shift, ctx-shift variants) invalidates token-prefix matching as a correctness test; the orchestrator PrefixIndex and llama-server slot reuse key on ... | K3 |
| W3DEC-7 | intake-2596, intake-2590 Stage-2 dive w3 ledger | Zero-inference size screen before any AKV-style work: from existing orchestrator serving records and autopilot/REPL traces, compute for long agent loops the share of resident context tokens that are tool responses older than the latest 12 (the paper's drop ... | P6 / CF-AKV-0 |
| W3DEC-8 | intake-2596, intake-2590 Stage-2 dive w3 ledger | Conditional on W3DEC-7: a bounded semantics probe on an attention-only role model on llama.cpp-experimental: compare (a) seq_rm of old tool-response cells + seq_add repositioning (the drop+repos analogue) vs (b) re-prefill of the text with those responses ... | M3 |
| W3SPEC-1 | intake-2591 Stage-2 dive w3 ledger | Bounded probe (own scratch server, GPU correctness window, no region-lock needed per CORRECTNESS rule): on the production 27B shape (Q8_0, DFlash2 n-max 7, np 4, kv-unified, q8 KV, ROCm0) and on the frontdoor shape (Qwen3.6-35B-A3B-MTP Q8_0, draft-mtp n 4, np ... | P1 / DF2-12.1 |
| W3SPEC-2 | intake-2591 Stage-2 dive w3 ledger | Fold the DF2-12 row and W3SPEC-1 into one run; add the frontdoor :8070 MTP np4 shape (not covered by DF2-12, which names only Qwen3.8-27B DFlash2) and the cross-content canary. | P1 / DF2-12.1 |
| W3SPEC-3 | intake-2591 Stage-2 dive w3 ledger | If W3SPEC-1 shows divergence: reproduce on the experimental branch and try the PR #29454 approach (copy pre-ubatch state into unwritten snapshot slots every ubatch) as the candidate fix; it was never merged, so it must be carried as our own patch on a ... | P9 / CH-37 |
| W3SPEC-4 | intake-2592 Stage-2 dive w3 ledger | No action on our CPU/HIP stack; note in the speculative handoff that the n_vocab-sentinel failure is Vulkan-specific and fails loudly at src/llama-batch.cpp:52 (token validation), which our tree retains. | K1 |
| W3SPEC-x | intake-297 Stage-2 dive w3 ledger | DF2-DRAFTER-CAPABILITY input: z-lab/dflash @ 07ebd93db9f4 (2026-08-18, remote HEAD identical today) contains NO training code. 659-line dflash/model.py has only inference: CandidateSelector (selector_top_k=16 candidates per position via topk of the draft ... | K1 |
| W4UP-1 | intake-2597, intake-2598 Stage-2 dive w4 ledger | Temp-0 np>1 token-identity probe on :8070 (MTP np4) and :8083 (DFlash2 np4): per slot compare against an np=1 cold run of the same prompt AND the same np4 server with speculation off; include (i) mixed spec/non-spec interleaving, (ii) slot reuse: slot k ... | P1 / DF2-12.1 |
| W4UP-2 | intake-2598 Stage-2 dive w4 ledger | Run tests/test-recurrent-state-rollback (CPU, correctness only, no quiet host needed) on our qwen4exp-capable experimental binary with the frontdoor GGUF; require dirty-ctx and multi-seq split replay both pass. Prove binary freshness vs commit 0771238438 ... | P1 / DF2-12.1 |
| W4UP-3 | intake-2602, intake-2601, intake-2599, intake-2600 Stage-2 dive w4 ledger | d1 decision-model screen build must include a4cb4c61fd (#29818 systemone API) and 7e3eeee048 (#30361) if H2O-Lightning-4B is screened; cbe28bb3 (#30408) only for non-causal/embedding-mode decision models at np>1; 7e8324f5 (#30100) is Metal-only and NOT needed ... | P5 / TD-23.D1 |
| W4UP-4 | intake-2601 Stage-2 dive w4 ledger | Add a GENERIC-readout arm to TD-23 (any lineup chat model, thinking off, U+22B2 label readout) as a comparator to dedicated decision backends after the systemone base is in the screen build. | M4 |
| W4UP-5 | intake-2602 Stage-2 dive w4 ledger | Offer/track the group-parent checkpoint fix for hybrid decision models; evaluate by prompt-token count (1254 vs 827 shape) on our model before adopting. | M4 |
| W5FOLD-1 | intake-2599 Stage-2 wave-5 plan-revision analysis | Fold #30408 non-causal ubatch fix as a cheap champion safety fix after a defect-reproducing control | P9 / CH-33 |
| W5FOLD-2 | intake-2600 Stage-2 wave-5 plan-revision analysis | Decline #30100 (Metal MUL_MAT+ADD fusion) for the champion | decline: the fix touches only the Metal backend; no CPU or HIP code path in our stack changes. |
| W5FOLD-3 | intake-2601 Stage-2 wave-5 plan-revision analysis | Track draft PR #29832 as the possible replacement base for the systemone fold when it merges | P9 / CH-36 |
| W5FOLD-4 | intake-2575, intake-2579, intake-2580 Stage-2 wave-5 plan-revision analysis | Real conflict and ggml-delta census before any audio-group cherry-pick | P9 / CH-32 |
| W5FT-1 | intake-2548#record, intake-2549, intake-297 Stage-2 wave-5 plan-revision analysis | Candidate (a), the 27B DFlash2 drafter (1.9B, GGUF-verified). Capture: 5 taps + final hidden = 61,440 B/token, only for completions plus their 2,048-token window (the drafter attends a 2,048 sliding window). ~0.8-1.2M tokens = 50-75 GB. Capture runs on the ... | P2 / DF2-FT-1 |
| W5FT-2 | intake-2548#record, intake-2578 Stage-2 wave-5 plan-revision analysis | Candidate (c), the frontdoor Qwen3.6-35B-A3B MTP head (blk.40: 0.845B params, of which ~0.80B are 256x experts; hidden 2048; served from the same Q8_0 file at draft_max 4). Capture the trunk pre-head hidden at every position (4,096 B/token). It is both the ... | P2 / DF2-FT-1 |
| W5FT-3 | intake-2548#record, intake-2578 Stage-2 wave-5 plan-revision analysis | Candidate (b), the Qwen3.8-Flash-Next MTP head (shared-Q8_0 file: 32 tensors, 2.607B params, of which 2.517B are 512x experts; attention with a QSA indexer, top_k 2048; 4-stream hyper-connections). Capture: the hc stream state at 10,240 x bf16 = 20,480 ... | P2 / DF2-FT-1 |
| W5FT-4 | intake-2548#record, intake-2549 Stage-2 wave-5 plan-revision analysis | Settle KL versus hard labels on the real served drafter (arms H and K plus a second seed in DF2-FT-1), not on the Soft-MTP 167M toy. The toy result would not transfer: different module (non-causal block drafter with a selector), different vocabulary (50,304 ... | P2 / DF2-FT-1 |
| W5FT-5 | intake-2548#record Stage-2 wave-5 plan-revision analysis | Fold MTP-4 (realign a served finetune's stock head) into a standing onboarding rule. Any served drafter or MTP head not co-trained on the exact served trunk and quant gets frozen-trunk KL re-alignment on its own traffic. That covers fine-tunes (the ... | P2 / DF2-FT-1 |
| W5FT-6 | intake-2578 Stage-2 wave-5 plan-revision analysis | Scope SPEC2-4 (Nemotron Sec 3.4 recipe). Hidden-state sampling over earlier draft steps applies to recursive MTP heads (frontdoor, Flash-Next), not to DFlash2, which drafts its whole block in one non-causal pass from the anchor. T=2 versus T=1 is a free extra ... | P2 / DF2-FT-1 |
| W5GPU-1 | intake-2547, intake-2571, intake-2551 Stage-2 wave-5 plan-revision analysis | Restate LOOP-1 with GPU arithmetic: loops multiply weight bytes, KV reads and FLOPs equally, so aggregate is about 1/L at every batch; batching removes only the weight term; MHA KV (768 KiB/token at 4 loops) makes Ouro-1.4B KV-bound beyond about 123 tokens of ... | P10 / GPU-LOOP-1 |
| W5GPU-2 | intake-2585, intake-2586 Stage-2 wave-5 plan-revision analysis | Per-request num_loops (setter, graph-param/can_reuse, k-class batch split, prefix-cache rule k2<=k, k_max cache sizing) with a router-oracle decision rule. | P10 / GPU-LOOP-3 |
| W5GPU-3 | intake-2585, intake-2547 Stage-2 wave-5 plan-revision analysis | Looped small model as reliability-boosted GPU batch worker vs equal-cost dense and majority-of-4 controls, with the incumbent worker scored for the first time on the worker battery. | P10 / GPU-LOOP-2 |
| W5GPU-4 | intake-2584, intake-2571 Stage-2 wave-5 plan-revision analysis | Replace the LoopCoder-v2 monitor with a transformers-custom-code quality screen on the MI210 (HE+, LCB, BCB, coder suite) against Qwen3.8-27B and the CPU frontdoor. | P10 / GPU-PLT-1 |
| W5GPU-5 | intake-2584, intake-2571 Stage-2 wave-5 plan-revision analysis | Port PLT (CLP rows, shared loop-1 KV, 64-token gated window) as a new arch on llama.cpp-experimental with HF-parity and decode-step-ratio acceptance. | P10 / GPU-PLT-2 |
| W5GPU-6 | intake-2551 Stage-2 wave-5 plan-revision analysis | LOOP-5 re-check on the GPU: at batch above E/top_k every expert is touched each pass, so a looped MoE at R=5 reads about R x its total expert bytes (1.3B total x 5 = 6.5 GB vs 2.9B x 1 = 2.9 GB for a quality of 46.9 vs 50.2 Overall); GPU does not reverse the ... | decline: no looped-MoE checkpoint or code is released; reopen on a weights release. |
| W5GPU-7 | intake-2550, intake-2574 Stage-2 wave-5 plan-revision analysis | MEM-3 re-priced on the MI210 instead of the CPU: text tokens cost 18.7 GB / (1433 GB/s x 0.715 fp16 attainment) = 18 ms vs 9 ms for the 9.3 GB base (L4 check: 18.7/0.30 = 62 ms vs the 68 ms the author reports); chip tokens are serial and autoregressive, ... | decline: same GPU re-pricing as the calculator row; serial chip tokens dominate on any device. |
| W5GPU-8 | intake-2546, intake-2568 Stage-2 wave-5 plan-revision analysis | LOOP-6 re-check: the monitor was never CPU-bandwidth based; the constraints are a per-dataset VQ tokenizer at about 100M-725M parameters with no served-vocabulary checkpoint, finest level (the first token) generated last, and no acceptance number against an ... | decline: no NCM checkpoint shares a served vocabulary and no acceptance number exists; reopen on such a release. |
| W5GPU-9 | intake-2587 Stage-2 wave-5 plan-revision analysis | W2LOOP-3 re-check: GDN beta cap is a monitorability finding with no GPU lever; unchanged. | decline: a single-task, few-seed result with no performance lever on either device. |
| W5META-1 | intake-2563 Stage-2 wave-5 plan-revision analysis | Anchor mark written only by a script, plus cross-paste check, for fabricated citations | P12 / ID-RI-ANCHOR-GATE |
| W5META-10 | intake-2562 Stage-2 wave-5 plan-revision analysis | Summed vs active-union vs critical-path attribution and no cross-run subtraction | P3 / AK-PROF-ATTR-1 |
| W5META-11 | intake-2562 Stage-2 wave-5 plan-revision analysis | Resin vs Annex K / AK loop (Resin cite = docs/benchmarks.md, optimize-resin-performance SKILL.md; ours = measurement/protocols/kernel-research.md, bench-cpu.md, gpu-cross-device.md) / noise floor: Resin none (qualitative 'show the spread') vs ours A/A p95 phi ... | P3 / AK-WIN-CNT-1 / AK-PROF-ATTR-1 |
| W5META-2 | intake-2563 Stage-2 wave-5 plan-revision analysis | Pin lane revision per citation and emit stale_epoch for changed files, for stale clones | P12 / ID-RI-LANE-HEAD |
| W5META-3 | intake-2563 Stage-2 wave-5 plan-revision analysis | Script-formed stage write grant checked by main, replacing self-reported audit lines | P12 / ID-RI-STAGE-GUARD |
| W5META-4 | intake-2563 Stage-2 wave-5 plan-revision analysis | Closed decline-reason vocabulary so no actionable is closed by a free-text reason | P12 / ID-RI-DECLINE-VOCAB |
| W5META-5 | intake-2563 Stage-2 wave-5 plan-revision analysis | Typed capability interfaces for dive subagents | decline: the dive return schema plus the per-claim second reader already give typed, checked outputs. |
| W5META-6 | intake-2563 Stage-2 wave-5 plan-revision analysis | Durable append-only run records | decline: session resume already exists in the skill and the plan checkpoint carries the durable record. |
| W5META-7 | intake-2563 Stage-2 wave-5 plan-revision analysis | Policy-gated self-modification of the skill | decline: Octopus gates on path coverage only and itself says on-contract behaviour is not proven, so it adds nothing to plan review. |
| W5META-8 | intake-2563 Stage-2 wave-5 plan-revision analysis | Unverified ids | decline: the intake id resolver and the vidya citation gate already catch dangling ids. |
| W5META-9 | intake-2562 Stage-2 wave-5 plan-revision analysis | In-window path/compile counters missing from Annex K record grammar | P3 / AK-WIN-CNT-1 |
| W5VERIF-1 | intake-2570, intake-2557 Stage-2 wave-5 plan-revision analysis | Record the race/deadlock/equivalence coverage matrix per hot gfx90a kernel family (v10 code-object counts and source anchors in this file header) in rocm-verify-profile-backend.md beside RVP-RACE-2, so later scoping cites measured coverage, not the paper ... | P11 / RVP-RACE-2 |
| W5VERIF-2 | intake-2570 Stage-2 wave-5 plan-revision analysis | Equivalence-port decision: decline for bit-level quant kernels on coverage (1116/1497 AK GPU experiment rows); a seeded sub-tolerance mutant probe decides the FA/GDN/mmvf subclass. | P11 / RVP-EQV-1 |
| W5VERIF-3 | intake-2570 Stage-2 wave-5 plan-revision analysis | Fix the RVP-RACE-1 decision rule (>=1 of 20 passes is a miss, not all 20), add waves-per-WG and ISA s_barrier-delta controls, add the LDS-DMA site, and make its mutants RVP-RACE-2 fixtures rather than its trigger. | P11 / RVP-RACE-1 |
| W5VERIF-4 | intake-2570, intake-2557 Stage-2 wave-5 plan-revision analysis | Level choice for the gfx90a checker is AMDGCN ISA from the built code object, not LLVM IR or HIP source: IR lacks waitcnts and the inline-asm semantics the AMD hot paths rely on, and cannot see ISA-edited (C5-ISA-2) candidates. | P11 / RVP-RACE-2 |
| PRE-2545 | intake-2545 Stage-1 preliminary actionable | Identify the STT model/runtime from the linked GitHub repo (expansion seed) before scoring for the speech lane. | K4 |
| PRE-2546 | intake-2546 Stage-1 preliminary actionable | Read the paper (expansion seed arXiv 2610.14162) and judge whether coarse-to-fine parallel generation has a drafter or non-AR serving role for EPYC. | M1 |
| PRE-2547 | intake-2547 Stage-1 preliminary actionable | Dive: decide whether looped/parallel-loop decoding changes bytes-per-token on bandwidth-bound CPU decode, and whether any served or candidate model is looped. | P10 / GPU-LOOP-1 |
| PRE-2548 | intake-2548#record Stage-1 preliminary actionable | Dive: verify Table 2 and decide whether Soft-MTP is the objective to use if we train or restore MTP heads (Flash-Next Axis E, drafter training). | P2 / DF2-FT-1 |
| PRE-2549 | intake-2549 Stage-1 preliminary actionable | Dive with intake-2548#record: check the loss implementation and whether it composes with head-only training on a frozen trunk. | P2 / DF2-FT-1 |
| PRE-2550 | intake-2550 Stage-1 preliminary actionable | Dive: separate the transferable mechanism (exact GDN-state addressing) from the demo; decide if it informs GDN-hybrid serving or memory work. | P3 / AKX-ALL-31.GDN |
| PRE-2551 | intake-2551 Stage-1 preliminary actionable | Dive: check whether looped MoE trades weight bytes for compute in a way that suits bandwidth-bound EPYC decode. | K2 |
| PRE-2552 | intake-2552 Stage-1 preliminary actionable | Dive: establish the actual llama.cpp audio path and whether it can replace or augment the whisper.cpp + qwentts.cpp cascade on EPYC/MI210. | P4 / CS-8.STT8 |
| PRE-2553 | intake-2553#record Stage-1 preliminary actionable | Dive: compare with the d1/Jev decision-model lineage already indexed and decide whether an audio/vision decision front end serves orchestrator routing or the speech turn-taking loop. | P5 / TD-23.D1 |
| PRE-2554 | intake-2554 Stage-1 preliminary actionable | Dive: verify the llama.cpp realtime speech-server path and which ggml generation it needs relative to the frozen kernel set. | M4 |
| PRE-2555 | intake-2555 Stage-1 preliminary actionable | Dive: extract the loop design and the verified-vs-numeric gap; map onto the AK candidate gate and gfx90a/x86 targets. | P3 / AKX-ALL-31.EDGE |
| PRE-2556 | intake-2556 Stage-1 preliminary actionable | Dive with intake-2555: read the loop and trace layout for AK reuse. | P3 / RVP-CTR-1 |
| PRE-2557 | intake-2557 Stage-1 preliminary actionable | Dive: decide what an equivalence/race checker would add to the AK correctness gate on gfx90a and x86. | P11 / RVP-RACE-1 |
| PRE-2558 | intake-2558 Stage-1 preliminary actionable | Dive: test whether the certificate-plus-independent-checker pattern fits belief-kernel derivations or registry/handoff consistency checks. | P7 / VB-CERT-1 |
| PRE-2559 | intake-2559 Stage-1 preliminary actionable | Dive: decide whether cache-level handoff between our role models is feasible in llama.cpp and what it would save over text handoff. | M3 |
| PRE-2560 | intake-2560 Stage-1 preliminary actionable | Dive with intake-2561: read the corrector implementation to size a llama.cpp port onto the DFlash2 drafter path. | P2 / DF2-LAT |
| PRE-2561 | intake-2561 Stage-1 preliminary actionable | Dive: measure-first design — top-K coverage of the verifier token on our DFlash2 drafter logits decides whether a corrector is worth porting. | P2 / DF2-LAT |
| PRE-2562 | intake-2562 Stage-1 preliminary actionable | Dive: read the architecture docs and the optimize-performance skill; extract what transfers to AK loops or llama.cpp serving. | P3 / AK-WIN-CNT-1 |
| PRE-2563 | intake-2563 Stage-1 preliminary actionable | None beyond architectural context; no measured result. | P12 / ID-RI-ANCHOR-GATE |
| PRE-2564 | intake-2564 Stage-1 preliminary actionable | Dive (light): confirm availability and what is technically claimed; compare with full-duplex designs in the conversation-stack lane. | M4 |
| PRE-2565 | intake-2565 Stage-1 preliminary actionable | Dive: map the folding criteria onto the orchestrator REPL/agent loop (roles as subagents vs skills) and its tool count. | P6 / RI-25 |
| PRE-2566 | intake-2566 Stage-1 preliminary actionable | None: KB retrieval is ColBERT MaxSim; synthetic-only evidence. | decline: synthetic single-machine retrieval evidence, and KB retrieval uses ColBERT MaxSim, not cosine stores. |
| PRE-2567 | intake-2567 Stage-1 preliminary actionable | Dive: verify the table, check the HF card (quant/MTP head) and decide a same-recipe token-count and accuracy probe on our harness. | P8 / AMS-TCAP-1 |
| PRE-2568 | intake-2568 Stage-1 preliminary actionable | Dive with intake-2546. | M1 |
| PRE-2569 | intake-2569 Stage-1 preliminary actionable | Dive with intake-2561: sequential corrector baseline that DCOCO claims to beat under concurrency. | P2 / DF2-LAT |
| PRE-2570 | intake-2570 Stage-1 preliminary actionable | Dive: decide what a sound equivalence gate would need on gfx90a/x86 and which AK candidate classes it could cover. | P11 / RVP-RACE-1 |
| PRE-2571 | intake-2571 Stage-1 preliminary actionable | Dive with intake-2547. | P10 / GPU-LOOP-1 |
| PRE-2572 | intake-2572 Stage-1 preliminary actionable | Dive: verify config (qwen4_exp, MTP layers), whether the GGUFs carry nextn tensors, and fit against the INF-70 Axis-E MTP restoration need. | P8 / AMS-TCAP-1 |
| PRE-2573 | intake-2573 Stage-1 preliminary actionable | Dive: decide whether transcribe.cpp Parakeet streaming is a candidate STT against frozen whisper.cpp; check what the index already holds on transcribe.cpp. | K4 |
| PRE-2574 | intake-2574 Stage-1 preliminary actionable | Dive with intake-2550. | P3 / AKX-ALL-31.GDN |
| PRE-2575 | intake-2575 Stage-1 preliminary actionable | Dive: locate the llama.cpp code for the audio/realtime path and estimate the port onto llama.cpp-experimental; check ggml generation vs the speech kernel set. | P9 / CH-35 |
| PRE-2576 | intake-2576 Stage-1 preliminary actionable | Dive with intake-2559. | M3 |

## Handoff edits (Stage 4, after approval)

Each owner gets one appended section with the heading below. Checkbox lines are new tasks. Notes are prose with no checkbox. Trigger records stay prose until a reviewed session confirms their condition.

### `handoffs/active/agentic-rocm-kernel-authoring.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **C5-ISA-1 — Archive the AMDGCN ISA of every AK GPU candidate and check the claimed instructions executed (intake-2555#record, intake-2588#record).** Store the hipcc --save-temps .s (or llvm-objdump of the code object) of each touched kernel in the candidate record next to its source diff. When a candidate claims a mechanism (MFMA, LDS staging, buffer loads), confirm in the ISA, and with a rocprof instruction counter where one exists, that the instruction executes on the measured path; a candidate whose claimed instruction is absent is refused.
- [ ] **C5-ISA-2 — GCN-Gym: LLM-edited AMDGCN for a compute-bound gfx90a kernel whose limiter is register allocation (intake-2555#record, intake-2556#record).** Not trigger-gated, because the HIP-source levers on the target are measured out: AK-MMQ-H10 (J-cap) NEGATIVE, the ak-27b-gpu-verify stream-k MMQ hypotheses were all refused or retired, and the ROCm 6.2 AGPR copy tax and MMQ spills are compiler-side (INF03-REGAUDIT-1: Q8_0 J=64 at 256 VGPR with 37 spills; MMA-FA DKQ>=192 at 512 VGPR with hundreds of reloads per iteration). Build a standalone harness (1-2 weeks). Extract the gfx90a .s of one kernel from an experimental v10-tip build via gfx90a_isa_audit.py; let the agent edit it with unified-diff patch tools; reassemble with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a; load with hipModuleLoad; replay the served-shape launches (the RVP-RACE-2 capture shim); diff-test against the hipcc kernel with the AK oracle (host-double for Q8_0); require gfx90a_isa_audit.py diff to exit 0, and the RVP-RACE-2 verdict once M2 lands. Target 1: MMQ Q8_0 J=64 prefill tile. Target 2: MMA-FA DKQ>=192. Run 3 runs per target at a fixed declared token budget on a frozen shape manifest; time on the GPU window with ABBA (>=2 pairs) against the hipcc incumbent, keeping per-run raw candidate .s, oracle outputs and timings. Decision rule: if >=1 of 3 runs on a target reaches >=1.05x kernel time at the served prefill shape, passes the oracle, and its ABBA intervals do not overlap the incumbent, open an experimental-tree code-object override path for that kernel as an ISA-rung AK arm; otherwise record the null with traces and stop the ISA rung for that kernel class.
- *Intake knowledge note, K5, row KERN-9 (intake-2556#record):* Keep the AK-PL-1 prompt-leak guard. If diagnostic failure feedback (failing indices/values) is ever adopted from TAIC, generate it on a feedback seed disjoint from the acceptance seed population.
```

### `handoffs/active/agentic-serving-harness-fixes.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **UFH14-TOOLS-1 — Count and cap the model-visible tool surface per role (intake-2565#record).** Enumerate what each role's prompt actually advertises (about 55 REPL globals plus about 55 registry tools behind TOOL/CALL) and log the count per role and per turn. Frontdoor turns called a tool in only 3.8-4.9% of turns (this handoff, line 670), so a large advertised surface costs prompt tokens for little use. Propose a per-role allowlist with deferred loading for the rest, behind a flag, for a later A/B.
```

### `handoffs/active/architect-model-selection-bench.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off.
```

### `handoffs/active/autokernel-all-devices-all-dimensions.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **AKX-ALL-31.EDGE — Edge-value input families and a per-element worst-error bound beside NMSE (intake-2555#record, intake-2588#record, intake-2589#record).** Extend the AKX-ALL-31 gate chain, on both legs, with structured input families beyond uniform [-1,1] and the four scale transforms: near-max values that overflow f16 accumulation, subnormal-scale values, catastrophic-cancellation rows, and per-tile constant blocks. Add a per-element maximum absolute error next to the aggregate NMSE on the served-shape case set, calibrated per (op, type, shape) from the v10 anchor over 5 seeds, so a fault confined to one tile or row cannot hide in the aggregate. Each family gets a seeded-defect twin (a mutant that corrupts one tile, or one row) that must go red. Reuse the AKX-ALL-29.5 guard bands; no new framework.
- [ ] **AKX-ALL-31.QDEC — Exhaustive code-space decode check per served quant type (intake-2555#record).** For Q4_K, Q6_K, Q8_0, IQ2_*, IQ3_*, IQ4_XS and MXFP4, enumerate every per-element code together with every scale and min value that occurs in the served GGUFs, decode through the CPU and HIP dequant paths, and compare bit-for-bit with a scalar reference. First report how much of the code space the current random suite reaches; bit-level dequant is exactly the class an equivalence checker cannot prove, so enumeration is the sound substitute.
- [ ] **AKX-ALL-31.GDN — Deterministic one-hot GATED_DELTA_NET state oracle (intake-2574#record, intake-2550#record).** Add a test-backend-ops case on an experimental champion-derived branch that drives the delta rule with gate held at 1, beta at 1 and one-hot keys, so each step overwrites exactly one state row and a one-hot query must read back that row; compare against the closed-form result. Cover CPU f32, gfx90a f32 and BF16 state, and K > 1 snapshot slots. The current cases only compare backends on random data, which cannot detect a shared indexing error.
```

### `handoffs/active/autokernel-champion-aggregate.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **CH-32 — Upstream-delta fold census: dry-run merge of upstream tip into the champion C5 (c72ec82f5) to replace the PR line counts with real conflict and ggml-generation numbers (intake-2575#record, intake-2579#record, intake-2593#record, intake-2585#record, intake-2599#record).** Immediately, no compute: git fetch the upstream remote into the llama.cpp object store (no checkout, no branch move, production tree and champion ref untouched), then for each fold group (A cbe28bb3 non-causal ubatch; B b77d646751 Nanbeige4.2 plus Ouro #29823 head; C a4cb4c61fd + 7e3eeee048 systemone/H2O; D 30629, 30636, 31252, 31257, 31269, 31287, 31386, 31283 audio/LFM3/realtime) run git merge-tree --write-tree against c72ec82f5 and record per group files changed, conflicted hunks per file (expect tools/server/server-context.cpp, src/llama-context.cpp, src/llama-model.cpp), whether the group needs ggml ops or a ggml bump beyond v10 lineage (diff ggml/ include list), and the minimal prerequisite commit chain (b10303..b11960 is 1657 builds). Output table lands in docs/reference/kernel-manifests/llama-v11-manifest.md as pending-fold rows with a presence gate each (ancestry check), per README rule 4. Controls: frozen base sha, per-group raw merge-tree output kept, full group list, predeclared rule: a group with more than 3 conflicted files in server/ or any conflict in ggml-cpu, iqk or speculative code is cut by hand on a fresh experimental branch from C5 rather than cherry-picked in bulk.
- [ ] **CH-33 — Fold the non-causal multi-sequence ubatch fix (upstream #30408, cbe28bb3cb, +7/-7 over src/llama-batch.h, llama-context.cpp, llama-kv-cache.cpp, llama-kv-cache-iswa.cpp, llama-memory.h) into the champion as a safety fix (intake-2599#record, intake-2595#record).** Value: any bidirectional/embedding or decision model served at np>1 can currently have a request split across ubatches so answers change with the co-batched companions; the EmbeddingGemma 2 fold (REPL-EMB-2.6) and any d1 decision model are the consumers. Immediately (cheap, safety): fresh branch experimental/champion-c7-nonc-ubatch from the CURRENT champion tip, cherry-pick cbe28bb3cb, build CPU+HIP store images, gates: (a) non-causal batch-invariance, EmbeddingGemma 2 BF16 embeddings for one request alone vs co-batched at np 3 with shorter, longer and identical companions, unfixed C5 as the control (must reproduce the defect or the task records that no champion consumer is affected), fixed build must agree within 1e-3 cosine-distance of solo; (b) causal decode untouched: Q38FN and 27B DFlash2 greedy identity vs C5 on the fold_gate.py slice; (c) fold_gate.py expects libllama.so only. Rule: fold if (b) identical and (a) fixed or defect absent; manifest row V11 pending-to-in with ancestry presence gate.
- [ ] **CH-34 — Looped-model support fold group: Nanbeige4.2 (#25994 merged, b77d646751, +265/-1, 10 files incl. new src/models/nanbeige.cpp) plus Ouro (#29823, open, ~324 added lines, head sha to be pinned from the CH-32 fetch) (intake-2586#record, intake-2585#record, intake-2547#record).** Value: unblocks the looped-probe lane (GPU-LOOP-1: tg at ouro.num_loops 1/2/4, GB/s per effective token on EPYC; HIP run on MI210) without a hand port; files are disjoint from AK kernels, iqk and DFlash2 so expected cost is low. Immediately cut branch experimental/champion-plus-looped-arch from the current champion tip (fresh-tip rule), cherry-pick both, build CPU plus HIP store images, gates: test-llama-archs and the new-arch smoke load, no-regression greedy identity on Q38FN and one dense model vs champion, linkage proof. Fold decision is gated on the GPU-LOOP-1 probe: fold into the champion if Ouro-1.4B or Nanbeige4.2 runs coherent and the probe is not rejected on the predeclared tok/s-per-quality rule; otherwise keep the branch as the probe instrument and record the exclusion reason in the manifest. Open PR is not a block: the branch carries our own cherry-pick and is rebased when the PR merges.
- [ ] **CH-35 — Speech/omni fold group: mtmd_audio_stream + Voxtral realtime (#30629, 2851b3bcbf, +998/-20, 27 files in tools/mtmd), realtime transcription API (#30636, 1242be66f6, +512/-14, 9 files, server-context.cpp +316), LFM3 arch (#31252), LFM3 audio+omni (#31257, +2721/-160, 31 files), /v1/realtime conversation (#31269, +1423) with tool calls (#31287), codec quant (#31386), video (#31283) (intake-2575#record, intake-2579#record, intake-2580#record, intake-2552#record).** Value: serves LFM3-Audio/Omni and Voxtral Realtime end to end from the champion server for CS-8 STT/interlocutor arms and CS-20/CS-22 realtime; the speech kernels (whisper.cpp, qwentts.cpp) are separate trees and unaffected. Cost: the biggest group; conflicts concentrated in tools/server/server-context.cpp (champion already +593 vs v10) and src/llama-model.cpp; mtmd is new surface the champion has not touched; ggml delta from CH-32. Stage 1 immediately: build the scratch upstream audio build of CS-8.STT8 (instrument, not the fold). Stage 2 gated on CS-8.STT8 (paired bootstrap WER not above +1.0 pp vs whisper in en and it) or CS-8.RT1 (realtime first-output latency beats the cascade on the 20 frozen utterances): then cut experimental/champion-plus-lfm3-audio from the current champion tip, apply the PR chain in merge order, resolve server-context.cpp by hand, rebuild CPU+HIP, gates: Q38FN/27B greedy identity vs champion (server changes must not move text decode), CS-8.STT8 WER reproduced on the folded binary within bootstrap CI of the scratch build, np>1 safety rerun of DF2-12.1. If STT8 and RT1 both fail the rule the group is recorded EXCLUDED with numbers.
- [ ] **CH-36 — Decision-endpoint fold group: /v1/systemone (#29818, a4cb4c61fd, +2139/-15, 35 files, new server-decision.cpp 681 lines, server-context.cpp +210) and H2O-Lightning-4B (#30361, 7e3eeee048, +478/-15), depends on CH-33 and the LFM3 arch commits of CH-35 (intake-2593#record, intake-2582#record, intake-2602#record, intake-2601#record).** Value: gives TD-23 the missing local compact decision backend (d1-2B/3B, H2O-Lightning). Not for production fold until measured: the scratch build used by TD-23.D1 is the instrument. Gate for the fold: TD-23.D1 parity gate (BF16 vs Q8_0 on CPU and HIP, no argmax flip, probability difference not above 2.2e-2) and batch-invariance gate (np 1 vs np 3, 1e-3) both pass and d1-2B Q8_0 beats the constrained incumbent on the sealed row-pinned workload. If it passes: cut experimental/champion-plus-systemone from the current tip, resolve server-context.cpp by hand, add the np1 pin (hybrid-prefix re-read, issue 31475) to the launch recipe, gates as CH-35 plus TD-23.D1 rerun on the folded binary. Draft PR #29832 (model-agnostic systemone) merging upstream is the external event that would replace a4cb4c61fd as the base; until then the merged #29818 is used. #30100 is Metal-only and declined with that reason.
- [ ] **CH-37 — Recurrent-state / np>1 slot-contamination fix fold, gated on DF2-12.1 (intake-2597#record, intake-2598#record, intake-2591#record).** Already in the champion: #28123 rollback port 0771238438 (ancestor of C5 and C6 verified read-only). Open exposure: issues 26695 (seq_rm true without recurrent-state restore) and 28019 (multi-seq split replay corrupts rs when rollback enabled) plus the CH-31-DEF1 batched-decode divergence. Immediately: confirm by reading src/llama-memory-recurrent.cpp on C5 whether the 26695 and 28019 fix commits (find them with git log --grep on the fetched upstream) are ancestors; record the answer in the manifest. If DF2-12.1 (temp-0 cross-slot token identity at np 4 on :8083 and :8070 shapes) shows any divergence, this task becomes the fix: cherry-pick the upstream fixes onto a fresh branch from the champion tip, rerun DF2-12.1 as the gate (zero divergent tokens over the frozen set versus np 1) plus Q38FN greedy identity. If DF2-12.1 is clean, the manifest row records the ancestry check and the task closes.
```

### `handoffs/active/autokernel-orchestrator-actor-backend.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- *Intake knowledge note, K5, row W2KERN-2 (intake-2588#record):* Compare AK candidate generation as plain multi-turn refinement vs agent-harness mode on token cost per accepted keep (PTXBench: agent harness cost 3.3-5.1x tokens and was worse on attention). Use existing AK run logs only; no new compute.
```

### `handoffs/active/autokernel-rebuild-program.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **AK-FAILRULE-1 — Turn recurring AK rejection reasons into pre-GPU rules from existing records (intake-2589#record, intake-2588#record).** Zero inference: classify every rejected candidate in the existing CPU and GPU campaign stores by failure reason (compile, correctness gate and which gate, timing loss, noise, harness error). For each reason class with at least 3 occurrences, draft a cheap static or pre-GPU check (CAKE-style hazard filter) and replay it over the historical candidates. Adopt a rule only if it would have rejected at least one historical failure before GPU time and no historical keep.
```

### `handoffs/active/autokernel-research-loop.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **AK-WIN-CNT-1 — Record in-window path counters beside every T1/T2 timing record (intake-2562#record).** Annex K's record grammar (`measurement/protocols/kernel-research.md` "Record grammar") has no field proving the timed window ran the intended path; T0 checks a dispatch trace but T1/T2 do not re-prove it. Resin keeps `graph_counts` and `overlap_counts` that exclude warmup and checks no JIT compile after warmup for unseen shapes. Do: capture hipGraph replay count vs eager launches and code-object load/JIT events inside the timed window on MI210 (use an in-process counter in a llama.cpp-experimental branch if none exists; the port is the build cost), write them as a non-gating diagnostic sidecar next to the raw samples, and draft the Annex K grammar amendment (human-amendment-only) making a path mismatch a VOID window. Controls: frozen anchor and one candidate, degraded-negative with graphs disabled (counter must show zero replays), A/A, per-window raw counters kept. Decision rule: sidecar ships if the degraded-negative is flagged and A/A is not; amendment text goes to the operator package.
- [ ] **AK-PROF-ATTR-1 — Add GPU-active-union and a cross-run-subtraction lint to the profile report (intake-2562#record).** `scripts/kernel_rnd/autokernel/profile_report.py` / `profile_context.py` report `kernel_wall_share` and overlap tables but no GPU-active union versus summed kernel time. Resin's skill states overlapping kernel work is not additive and "Engine minus GPU timing is unattributed time ... do not subtract different profiler and benchmark runs" (optimize-resin-performance SKILL.md). Do: emit summed duration, active-union and critical-path per trace, and reject a derived "unattributed" figure built from two runs. Controls: a synthetic overlapping-kernel trace (sum greater than union), the hash-bound rocprofv2 trace already replayed in this handoff (~L444), a two-run subtraction negative. Decision rule: union less than sum on the synthetic case, existing wall-share values unchanged on the replayed trace, negative rejected.
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
- *Intake knowledge note, K2, row W2LOOP-3 (intake-2587#record):* Knowledge-only: record that our GDN graph hard-caps beta at 1 (src/models/qwen3next.cpp:417 ggml_sigmoid) matching the Qwen3.5 control that failed to generalise hidden tracking; no probe.
```

### `handoffs/active/dflash2-block-drafter-experimental-build.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **DF2-12.1 — Run the DF2-12 np>1 parity check on every production speculative role served at np>1, as one temp-0 cross-slot token-identity run (intake-2591#record, intake-2577#record, intake-2597#record).** Two shapes, each on its own scratch server in a GPU correctness window: the :8083 Qwen3.8-27B DFlash2 Q8_0 recipe (n-max 7, np 4) and the :8070 frontdoor Qwen3.6-35B-A3B draft-MTP recipe (n-max 4, np 4), which DF2-12 does not cover. Send c = 2, 3 and 5 equal-length salted prompts issued together so they prefill in one scheduler step, and compare every output token with the same prompt served alone at np 1. Add a slot-reuse arm (conversation A, then an unrelated conversation B in the same slot, compared with a cold B), which is the untested condition in llama.cpp #28019 (intake-2598#record). Controls: speculation off at np 4; an np-4 server carrying a single request; a low-entropy prompt pair; a repeat run for the numeric floor; a planted string that must never appear in another slot. Before the run, prove the binary is fresh and pass tests/test-recurrent-state-rollback including its dirty-context check; a failure there voids the run. Log per round draft_n, accepted count and rollback length versus batch length, and classify each first divergence as near-tie (small top-2 margin) or degenerative. Freeze the prompt manifest by sha256, keep per-request raw outputs and acceptance counters, and count every request in the denominator. Decision rule: a degenerative divergence that the speculation-off np-4 control does not show is a cross-slot defect, so file it against the champion, keep the role at its current shape and open the snapshot-slot patch trigger; zero such divergence across all arms closes the question for these two recipes. This run does not close G2-CONC, which belongs to the promotion candidate binary.
- [ ] **DF2-LAT — Zero-training lattice-headroom probe for the DFlash2 selector (intake-2561#record, intake-2560#record, intake-2569#record).** DFlash2 already ships a learned top-16 candidate lattice with a rank-256 transition score and a prefix-first walk (src/models/dflash.cpp:735-824, common/speculative.cpp:1658-1700 @ ffc1bac82), so the open question is how much headroom any re-selector has above it. On an experimental build, env-gated and off by default, dump per draft step the 16 candidate ids, unary logits, pair scores and chosen ids. In one MI210 correctness window (27B Q8_0 + DFlash2 Q8_0, n-max 7, np 1, temp 0, 1024-token cap) run the 12 DF2-4 olympiadbench prompts as dev and at least 36 disjoint agentic replay turns as holdout. Offline, exact at temp 0: arm A unary argmax, arm B the live walk (must reproduce the server accepted counts on every request or the probe is void), arm C the oracle that takes the verifier token whenever it is in the top 16, 8 or 4, and per-slot top-k coverage. Decision rule on the holdout with H = (tau_C16 - tau_B) / tau_B: H >= 0.25 on dev and holdout with a bootstrap 95% lower bound >= 0.15 opens a trained-selector port; H < 0.10 closes it; otherwise monitor.
- [ ] **DF2-PM — Point-mass draft proposals at production temperature (intake-2561#record).** Behind an env knob on the experimental build, make the DFlash2 temp>0 branch propose the argmax selector walk with a point-mass distribution instead of sampling softmax(scores/T); the verifier then accepts with p_target(draft) and resamples from the residual (common/sampling.cpp:740-766), which is lossless. A/B against the stock sampled walk on the DF2-4 protocol (12 prompts, temp 0.6, top-p 0.95, top-k 20) at np 1 and np 4, at least 5 interleaved pairs; primary metric weighted acceptance, secondary tok/s; the SPEC-PIT.1 distribution gate must pass. Adopt into the next champion fold only if weighted acceptance improves by at least 3% in at least 4 of 5 pairs at both np values, tok/s does not regress and SPEC-PIT.1 passes; otherwise record the per-pair numbers and close.
- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).
- *Intake knowledge note, K1, row SPEC-4 (intake-2560#record, intake-2561#record, intake-2569#record):* Prepare a text update (owning session applies) to the LiLiCorr monitor paragraph: name DCOCO (intake-2561#record) and Domino (intake-2569#record) as the same correction family; record that DFlash2 already ships a learned K=16 rank-256 selector lattice with a ...
- *Intake knowledge note, K1, row SPEC-6 (intake-2561#record, intake-2569#record):* CPU: no separate action. The 27B DFlash2 path is served on the MI210 only, and CPU speculative work for Flash-Next is MTP (Axis E). If SPEC-3 is ever built, its graph ops are backend-agnostic and must pass CPU no-regression in the four-step workflow.
- *Intake knowledge note, K1, row SPEC2-4 (intake-2578#record):* Add to DF2-DRAFTER-CAPABILITY the Nemotron Sec 3.4 head/drafter fine-tune recipe as an option: freeze target, sample hidden states from earlier draft steps, forward-KL T=2 to target logits on target on-policy rollouts at temp 1 (reference scale: 12K steps, bs ...
- *Intake knowledge note, K1, row SPEC2-5 (intake-1724#record):* Answer only (no entry): the z-lab card text does not say how the DFlash2 selector (top-16, rank-256 transition score) was trained, and reports no tau gain over DFlash 1 for Qwen3.8-27B. The inco.ai blog (sha256-12 99dc56f49911) gives the selector score ...
- *Intake knowledge note, K1, row W3SPEC-x (intake-297#record):* DF2-DRAFTER-CAPABILITY input: z-lab/dflash @ 07ebd93db9f4 (2026-08-18, remote HEAD identical today) contains NO training code. 659-line dflash/model.py has only inference: CandidateSelector (selector_top_k=16 candidates per position via topk of the draft ...
- *Intake knowledge note, K1, row MTP-3 (intake-2548#record):* No change to Axis E. Restoring the Qwen3.8-Flash-Next MTP head loads the published unsloth shared-Q8_0 head (no training), so the MTP-objective choice does not touch it.
- *Intake trigger record (no checkbox until it fires), M1, row SPEC-3 (intake-2560#record, intake-2561#record):* Port the DCOCO head to llama.cpp as a replacement DFlash2 selector, and train it on the frozen DFlash2 backbone. Gated on SPEC-1 PROMOTE. Port: converter keys/tensors for cand_proj, ctx_h_proj, cand_ctx_proj + LN, pair_proj and the 386->256->1 MLP (~100 LOC ...
- *Intake trigger record (no checkbox until it fires), M1, row SPEC-5 (intake-2569#record):* Domino-style GRU + full-vocab low-rank correction head on the DFlash2 drafter: no work now. It needs full drafter co-training with the curriculum, and its sequential head adds a 256x248320 logit-residual projection per position on the critical path. Revisit ...
- *Intake trigger record (no checkbox until it fires), M1, row LOOP-6 (intake-2546#record, intake-2568#record):* Monitor NCM as a drafter source: trigger = a released NCM-style generator with a general-text tokenizer sharing a served model vocabulary, or any measured acceptance rate against an AR target. Do not build now: released checkpoints are per-dataset ~100M-725M ...
- *Intake trigger record (no checkbox until it fires), M1, follow-on DF2-FT-2 gated on DF2-FT-1 promoting:* Scale the winning DF2-FT-1 objective to 3-5M on-policy tokens: fresh completions at the production sampler on role-matched architect_critic / coder_escalation / ingest_long_context contexts, generated at np8 on the :8083 argv (~5-10 MI210-h). Capture in rolling ~60 GB shards and train <=8 MI210-h. Keep the DF2-FT-1 holdout (C4) and a new held-out role set untouched. Run the serving keep gate: SL-2 verify steps/s plus aggregate tok/s at np 1/4/8, fresh server per arm, ABAB with >=5 pairs, the coherence gate, the DF2-6 greedy pass count not below the incumbent, and DF2-4 acceptance >= incumbent - 0.02. Keep only if held-out acceptance is >= incumbent + 0.05 and np4 aggregate tok/s clears the calibrated floor. On a keep, emit the stack-change package that repoints the registry drafters.dflash2.draft_model, keeping the incumbent file as the rollback anchor, for one operator signature.
```

### `handoffs/active/gpu-acceleration-path.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).
- [ ] **GPU-LOOP-3 — Loop count as a per-request serve-time effort switch in llama.cpp-experimental (intake-2585#record, intake-2586#record, intake-2547#record).** Today num_loops is a load-time GGUF key (PR #29823: --override-kv ouro.num_loops=int:N; PR #25994 expands hparams arrays to n_layer_phys*n_loops once in load_arch_hparams). Change set: (1) llama_context gains llama_set_n_loops(ctx,k), 1<=k<=file n_loops, carried in llm_graph_params and compared in can_reuse() so a changed k rebuilds the graph while graph_reserve still sizes the worst case; the builder loop bound becomes n_layer_phys*k and the LM-head tap is the shared final norm of loop k (the exit_at_step readout the HF code already has); about 150-250 lines. (2) server: parse n_loops or an effort alias (low/medium/high mapped by a GGUF key such as ouro.effort_loops) into slot params; update_slots splits the ubatch into one llama_decode per k-class (each class re-reads the weights, a cost that is small once np exceeds the weight/KV crossover of about 7 streams at C=1k); about 100-150 lines. (3) KV semantics, each point tested: a logical layer slot (loop j, layer i) holds KV only for sequences that ran loop j, so a prefix cached at k loops is valid for any request with k2<=k and invalid for k2>k (the deeper slots and the hidden states to recompute them are not stored), which makes the prompt-cache and ctx-checkpoint key carry n_loops_cached; a mid-request upgrade needs a re-prefill, a downgrade does not; cells are shared across layers, so a low-k request saves bandwidth and FLOPs but not VRAM unless the cache is sized with a k_max option (KV is 192 KiB per loop per token for Ouro-1.4B f16, 768 KiB at 4). (4) Validity gate: only checkpoints trained with per-loop supervision may expose the switch: Ouro yes (PR GSM8K F16 26.0/67.0/80.5 at 1/2/4), Nanbeige4.2 no (forced 1 loop is degenerate, 0.0 GSM8K), LoopCoder-v2 no (each R is a separately trained model, R=3 27.6 vs R=1 43.0 SWE-bench Verified). Acceptance tests: logits at per-request k on a file with n_loops=4 are bit-identical on CPU and within 1e-3 abs on HIP to a file loaded with num_loops=k, for k=1..4 on the 829-position fixture (this also verifies the claim that loop-j activations do not depend on the total loop count); four concurrent requests with k=1,2,3,4 reproduce their solo outputs; prefix-cache hit for k2<=k and miss for k2>k; throughput at np=16 with half k=1 and half k=4 within 0.8-1.2x of the byte-model prediction. Router oracle on the GPU-LOOP-2 per-item results: oracle minimum loops per item vs a no-oracle router (answer agreement between loops 2 and 4 on a calibration half, or the exit-gate probability); decision rule on the held-out half: PROMOTE the switch to a lane option if the router keeps at least 97% of the L=4 accuracy at mean loops at most 2.4 (cost at most 0.6x of L=4); else keep static L and record the oracle bound. Per-token adaptive exit is not offered: the PR does not convert the early_exit_gate and a batch graph saves nothing from it without row compaction.
- [ ] **GPU-PLT-2 — Parallel-Loop-Transformer architecture (iquestpltcoder) on llama.cpp-experimental: port, parity, and MI210 decode curves (intake-2584#record, intake-2571#record).** Not blocked by the absence of upstream code; estimate 1.0-1.5 kLOC, 3-5 agent-days, 3-4x the 265/324-line Nanbeige/Ouro ports because those only unroll layers and carry no CLP, shared-KV or sliding window: converter for IQuestPLTCoderForCausalLM (about 150: 14 layers, hidden 5120, 40 heads / 8 KV, FFN 27648, R, window 64, per-head gate tensors; read the HF modeling file at sha b87cf3a first); arch/hparams/tensors (about 250); graph (about 400): a decode step builds R rows per sequence, row r input = token embedding + h^(r-1) of the previous position (per-sequence state of (R-1) x n_embd, held in the recurrent-memory path so checkpoint and spec-decode rollback come with it), row 1 attends the normal full KV, rows >=2 attend the shared loop-1 K/V through the existing cross-layer KV-reuse hparams plus a private 64-entry window cache (extra logical layers in the iSWA cache) and mix with the head-wise sigmoid gate; prefill runs R shifted sweeps over the prompt; cache/state plumbing and tests (about 400-700). Acceptance: top-1 logits match the HF reference on >=1000 positions and greedy continuations match on 20 prompts, on CPU and HIP; measured decode step ratio PLT-2 vs the same weights run as a one-loop graph is <=1.15 at np<=16 (prediction 1.02-1.05, since 2 rows per stream stay under the Q8 knee of 64 rows through 32 streams) and a sequential two-loop graph on the same weights is >=1.8 (the ByteDance paper reports 4.9 vs 4.8 vs 9.4 ms at bs 4 and 8.6 vs 8.1 vs 16.1 ms at bs 32 in its own stack); KV measured at about 56 KiB/token + window; spec-decode (MTP/DFlash2) rollback test using the state snapshot. Quality and serving verdicts are GPU-PLT-1 and the SWE-40 legs, not this task; this task delivers the engine.
- *Intake knowledge note, K2, row W2LOOP-4 (intake-2585#record, intake-2586#record):* Correct the stale note in gpu-acceleration-path.md ~line 248 (intake-332 "Not llama.cpp compatible") to say nanbeige looped arch merged 2026-07-27 and Ouro is PR #29823 open; owning session applies.
```

### `handoffs/active/gpu-serving-tie-in-program.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **GPU-LOOP-2 — Looped small model as a reliability-boosted batch worker on the MI210: quality vs loops vs aggregate throughput against equal-cost dense and K-sample controls (intake-2585#record, intake-2547#record, intake-2551#record).** Question: at high concurrency (elastic-duty D1 batch-shedding class, np 16), does Ouro-1.4B (and 2.6B-Thinking as second tier) at 1/2/4 loops buy more correct worker answers per HBM byte than a non-looped model? Arms, served-cost arithmetic at np=16, C=1k, f16 KV (ideal step times, to be measured in GPU-LOOP-1): A1 Ouro-1.4B L=4 (5.76 GB weights/step + 12.9 GB KV, 13.0 ms, 1,230 tok/s); A2 L=2 (about 2,300); A3 L=1 (about 7,100 on the same weights); A4 Ouro-2.6B-Thinking L=4 (48 layers, about 11.3 GB weights/step, 1.5 MiB/token KV); C1 Qwen3-4B-Thinking-2507 Q8 (4.28 GB, 144 KiB/token, 3,420 tok/s, the equal-quality-class dense control); C2 Qwen3-1.7B Q8 majority-of-4 (about the same bytes per final answer as A1, 1,545 answer-equivalent tok/s: the K-sample route that the idle MFMA headroom makes free); C3 Qwen3-1.7B Q8 single sample (equal resident bytes); C0 the incumbent worker, Qwen3.6-35B-A3B on CPU :8070 (registry roles.worker_general.performance.quality_pct is null: it has never been scored on the worker battery, so it is measured here on the same frozen items). Frozen inputs: GSM8K-style math (n>=200, same problem list as the PR so the 26.0/67.0/80.5 published curve is a replication check) plus worker-battery items for explore, summarize, transform and strict tool-call JSON (n>=150 per suite), item list and scorer hashed before any generation; Ouro context stays under its trained 1024-token block (Ouro RECIPES: block_size 1024), longer prompts are a separate reported stratum. Per arm: pass@1 over 3 seeds, seed-to-seed agreement, JSON-validity rate, aggregate tok/s at np 16, wall-seconds per correct answer and correct answers per HBM GB moved; per-item raw outputs kept; correctness legs may share the card with :8083, throughput legs run in a GPU window with the host threads under the q3 claim. Controls: frozen inputs, incumbent baseline (C0 and C1), per-item raw outputs, 3-seed repeat with the A/B order alternated, full denominator including parse failures, predeclared rule. Decision rule: an Ouro arm earns a shadow-lane tenancy row (D3 shadow-only, no production traffic) only if (i) its paired accuracy vs C1 is within 2 points (McNemar not worse) and its seconds per correct answer at np=16 is at most 1.5x C1, or (ii) it beats C1 by at least 5 points at paired p<0.05 at no more than 2.5x C1 cost; the arithmetic predicts A1 costs 2.8x C1 per token, so (i) needs a real quality edge. Otherwise record NO-GO with the table and keep Ouro only as the vehicle for GPU-LOOP-3. Depends on the GPU-LOOP-1 build (our own task, not an external event).
- [ ] **GPU-PLT-1 — LoopCoder-v2 (7.6B PLT coder, Apache-2.0) quality screen on the MI210 through transformers custom code, before and independent of the GGUF port (intake-2584#record, intake-2571#record).** Load Multilingual-Multimodal-NLP/LoopCoder-V2 at the pinned HF sha b87cf3a (BF16, 7,615,749,680 params, 15.2 GB, fits the about 19 GiB headroom beside :8083 without a KV problem) in an isolated venv with the transformers version its configuration_iquestpltcoder.py needs (Ouro needed 4.57.x, the research venv has 5.15.0: do not assume); confirm torch.version.hip and bf16 on gfx90a first; read config.json to see whether the loop count is a config field (the paper trains R=1..4 as separate models, so a forced R=1 on the released weights is not the paper R=1). Frozen inputs: HumanEval+ (164), LiveCodeBench subset released after the model cutoff (n>=200), BigCodeBench-hard subset, plus the frozen coder-suite items used for coder_escalation (cruxeval and the others E-7 scored: math 85.0, mmlu_pro 27.5, gpqa_diamond 47.5, cruxeval 22.5 at terse template 1443ea9ab4bb). Arms: LoopCoder-v2 as released; incumbent coder_escalation Qwen3.8-27B Q8 on :8083 (same harness, thinking off and medium); frontdoor Qwen3.6-35B-A3B on CPU; size control Qwen3-4B-Instruct-2507 (on disk). Controls: frozen items and scorer hashes, incumbent baselines, per-item raw outputs, 2 seeds, full denominator, rule below. Replication check against the paper own table: R=2 reports HE+ 84.1, LCB 35.4, BCB 46.1 and SWE-bench Verified 64.4 (harness unnamed, single seed, vendor-authored); accept the replication if HE+ >= 80 and the LCB subset score is within 5 points of the paper 35.4 after harness adjustment stated. Decision rule: open the serving legs of GPU-PLT-2 (agentic SWE-40 on the same scaffold that scored Qwen3.8-27B 21/40 = 52.5%, shadow lane only) if pooled pass@1 over HE+ and LCB is non-inferior to Qwen3.8-27B within 8 points (paired bootstrap lower bound) or the replication check passes; otherwise record NO-GO with the table (the port of GPU-PLT-2 still completes as parity work). Arithmetic that motivates it: at np=16, C=8k, Q8 (about 8.1 GB incl. head, KV 56 KiB/token f16 because later loops share loop-1 KV and keep only a 64-token window) a PLT-2 step is about 15.2 GB / 1433 GB/s = 10.6 ms bandwidth vs 2.5 ms compute at 32 rows, i.e. 1,510 tok/s ideal aggregate (about 600 derated by the 27B np8 ratio 157/400), vs 94 tok/s live at 4 concurrent on the 27B.
```

### `handoffs/active/intake-derived-work-2026-07-25.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **ID-RI-ANCHOR-GATE — Make quote re-find a gate the author cannot satisfy by assertion (fabricated citations) (intake-2563#record, intake-1377#record).** Today `.claude/skills/research-intake/scripts/validate_intake.py` (~L436-441) only checks `claim_anchors` is non-empty and `verified_by` is self-written, so a fabricated or cross-pasted quote (the 2026-07-25 CORE ablation, also pasted into intake-895) passes. Borrow Octopus's rule that a mark is recorded only by the runtime after a verifier passes the artifact and nothing else can emit it (`docs/contracts/VERIFIERS.md`, "Nothing emits marks"). Change SKILL.md Stage-2 "Writes permitted" (claim_anchors bullet) and the Stage-2 Verification Gate: add `validate_intake.py --check-anchors` that (a) re-finds every anchor `quote` in the retained source via `scripts/vidya/machine_anchor.py:verify_source_anchor` / `raw_anchor_store.py` (dive wrapper must write the source into `EPYC_VIDYA_RAW_ANCHOR_ROOT`, today opt-in and unused by dives), (b) recomputes `quote_sha256`, (c) writes an `anchor_mark: {verifier, source_raw_sha256, found}` that only the script writes, and (d) flags any `quote_sha256` appearing under two different entries (cross-paste, needs no retained source). New dive-verified entries without an anchor_mark fail; legacy entries stay grandfathered. Controls: four frozen fixtures (verbatim quote, fabricated quote, whitespace-altered quote, same quote under two entries) plus the old validator output; per-fixture expected verdict recorded. Decision rule: ship only if all four fixtures give the predeclared verdict and a replay over the current index flags zero verbatim anchors. Passing proves containment, not entailment; the per-claim second reader stays.
- [ ] **ID-RI-LANE-HEAD — Pin the repo revision every in-house citation was read at and refuse stale ones mechanically (stale clones) (intake-2563#record).** SKILL.md L391-405 forbids the shared clone in prose only (2026-09-14 dives read /workspace @d372c953). Octopus pins descriptor hashes in every formed grant and refuses a movement against a changed checkpoint with a typed `stale_epoch` (`docs/contracts/LEDGER_INDEX.md`). Change: (1) Stage-2 dive brief template requires `lane_head` (full SHA of the lane worktree) in the returned YAML, and a `dive_preflight.py` run by main before dispatch asserts the named root is the lane worktree and its HEAD is not behind origin/main; (2) in-house `claim_anchors` locators `path:Lx-Ly @ sha7` get validated by `validate_intake.py --check-lane-anchors`: `git show sha7:path` must contain the quote, and `git diff --name-only sha7..origin/main -- path` non-empty emits typed `stale_epoch` that blocks Stage-3 plan citation of that anchor until re-read. Controls: replay the 2026-09-14 incident (anchor at d372c953 for a file since changed), a moved path, an unchanged path. Decision rule: stale_epoch fires on the first two and not the third; zero false positives over the current in-house anchors.
- [ ] **ID-RI-STAGE-GUARD — Compute the stage write grant by script and check the diff outside the agent (stage-gate violations) (intake-2563#record).** The skill's "May write" table (SKILL.md L50-58) and the Stage 1/2 gate "`git status handoffs/` clean" are prose run by the same agent that might violate them (2026-07-25: handoffs edited after an operator "you can edit"), and the dive `artifact_audit: clean` line is self-reported. Octopus forms the effective grant by a deterministic script at every arrival (ceiling intersect chain intersect bindings), enforces it outside the model and records a typed refusal row (`docs/architecture.md`, "How policy is formed"). Change: add `scripts/stage_grant.py form --stage N` (allowed paths: S1 index+.research-session.json; S2 index; S3 plan file; S4 the paths named by the approved plan, bound to `stage3_filing.plan_sha256` already checked at validate_intake.py ~L1084) and `check`, run by main at each stage boundary on `git status --porcelain` plus a tree hash taken at stage entry; violations append a typed row to the session JSON (`stage_write_outside_grant`, `plan_hash_stale`). Controls: replay the 2026-07-25 handoff-edit-in-Stage-2 case, a Stage-4 write outside the plan, and a clean stage. Decision rule: both violations refused, clean stage passes, no change to legacy validate_intake output.
- [ ] **ID-RI-DECLINE-VOCAB — Replace free-text decline reasons with a closed vocabulary (dropped actionables, operator Act-Do-Not-Defer rule) (intake-2563#record).** `validate_intake.py` ~L1132 accepts any `decline: <text>`, so "vendor-only", "upstream has not done it" or "not applicable" can close a row (the rules SKILL.md L40-48 forbid). Octopus refusals are typed rows from a closed set, "never a silent drop" (`docs/contracts/LEDGER_INDEX.md`). Change: a decline/closed-with-basis terminal must start with a code from {duplicate:<exact id>, superseded:<successor id>, measured-loss:<evidence ref>, math-constraint:<one-line proof>, external-event:<named event>, operator-ruled:<ruling ref>}; the validator rejects other prefixes and the forbidden phrases, and `external-event` requires a name that is not "upstream". Controls: freeze the current plan's decline rows as a fixture (expected: each maps to a code or is flagged for re-open), plus three negative fixtures (vendor-only, upstream-absent, not-applicable). Decision rule: negatives rejected, all legacy plans still pass under the unchanged legacy mode.
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
```

### `handoffs/active/rocm-verify-profile-backend.md` — append at the end of the file

```markdown
### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

- [ ] **RVP-CTR-1 — Counter-grounded planner signals for the GPU AK lane (intake-2556#record).** For the top hotspot kernel of each GPU screen, capture a fixed declared counter subset with rocprofv2 (occupancy, LDS bank conflicts, VALU/MFMA busy, memory unit stall, achieved bandwidth) and pass it to the planner with the rule that every proposed idea must cite a counter that is present, and a missing counter may not be treated as zero. Compare 2 planner rounds with and without counters on the same target and budget.
- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.
- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs.
- [ ] **RVP-EQV-1 — Decide the equivalence-checker port by measured miss rate, quant kernels declined on coverage (intake-2570#record, intake-2557#record).** Decision part 1, decline: no Volta-class equivalence for MMVQ, MMQ, quantize_q8_1 or dequant. They are bit-level (nibble unpack, rounding), which Volta does not cover (floats are reals, conversions are the identity), and they make up about 75% of AK GPU experiment rows (1116 of 1497). KERN-4 enumeration owns decode exactness. Decision part 2, a deciding probe for the real-valued subclass (FA-mma/FA-tile at parallel_blocks=1, GDN recurrence, mmvf float GEMV). In a llama.cpp-experimental worktree from the v10 tip, build 8 seeded sub-tolerance algebraic mutants: FA online-softmax rescale skipped only when the running max changes after the first KV tile; FA KV loop dropping the last KV column; FA-tile dropping one tail tile at a non-multiple context; GDN exp(g) decay dropped at a chunk boundary; GDN beta dropped for one head; mmvf dropping the final partial k-block at ne00 % tile != 0; and two controls with an O(1) error. Prove each mutant structurally (ISA diff of that kernel). Run the AK served-shape gate plus the AKX-ALL-31 edge families and the KERN-5 worst-element bound, 5 seeds each, on a frozen case manifest, keeping per-mutant per-seed raw verdicts and NMSE; the unmutated v10 build must pass 5/5 seeds. Decision rule: if any non-control mutant survives every gate on >=1 seed, open the equivalence milestone for that subclass on the RVP-RACE-2 interpreter (symbolic float values, v_exp_f32 as 2^x, cvt as identity, the 2 MFMA lane layouts in use, DPP/swizzle value moves, FA and GDN reference specs; estimate 4-6 kLoC, 4-6 engineer-weeks; advisory, never a speed-blocking gate, because intake-2555 Table 2 shows proof-restricted FA at 0.78x vs 1.37x). If all are caught, record the catch table and close the equivalence port with that table as the reason. Correctness-only, so no quiet host is needed.
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
        "PRE-2546 -> M1",
        "W5GPU-8 -> decline: no NCM checkpoint shares a served vocabulary and no acceptance number exists; reopen on such a releas"
      ]
    },
    {
      "id": "intake-2547",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-champion-aggregate.md",
        "gpu-acceleration-path.md",
        "gpu-serving-tie-in-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-1 -> P10 / GPU-LOOP-1",
        "LOOP-2 -> P10 / GPU-PLT-1",
        "LOOP-3 -> P9 / CH-34",
        "LOOP-4 -> P10 / GPU-LOOP-1 / GPU-LOOP-2",
        "PRE-2547 -> P10 / GPU-LOOP-1",
        "W5GPU-1 -> P10 / GPU-LOOP-1",
        "W5GPU-3 -> P10 / GPU-LOOP-2"
      ]
    },
    {
      "id": "intake-2548#record",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "MTP-1 -> P2 / DF2-FT-1",
        "MTP-2 -> P2 / DF2-FT-1",
        "MTP-3 -> K1",
        "MTP-4 -> P2 / DF2-FT-1",
        "MTP-5 -> decline: Soft-MTP as a pretraining objective needs trunk training, which this stack does not do.",
        "PRE-2548 -> P2 / DF2-FT-1",
        "W5FT-1 -> P2 / DF2-FT-1",
        "W5FT-2 -> P2 / DF2-FT-1",
        "W5FT-3 -> P2 / DF2-FT-1",
        "W5FT-4 -> P2 / DF2-FT-1",
        "W5FT-5 -> P2 / DF2-FT-1"
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
        "MTP-1 -> P2 / DF2-FT-1",
        "MTP-2 -> P2 / DF2-FT-1",
        "PRE-2549 -> P2 / DF2-FT-1",
        "W5FT-1 -> P2 / DF2-FT-1",
        "W5FT-4 -> P2 / DF2-FT-1"
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
        "MEM-3 -> decline: re-priced on the GPU, the in-weights calculator still loses: chip tokens are serial (0.5-1 s per call",
        "PRE-2550 -> P3 / AKX-ALL-31.GDN",
        "W5GPU-7 -> decline: same GPU re-pricing as the calculator row; serial chip tokens dominate on any device."
      ]
    },
    {
      "id": "intake-2551",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "cpu-decode-roofline-program.md",
        "gpu-acceleration-path.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-4 -> P10 / GPU-LOOP-1 / GPU-LOOP-2",
        "LOOP-5 -> decline: no looped-MoE checkpoint or code is released, and on the GPU looping a MoE multiplies expert byte rea",
        "PRE-2551 -> K2",
        "W5GPU-1 -> P10 / GPU-LOOP-1",
        "W5GPU-6 -> decline: no looped-MoE checkpoint or code is released; reopen on a weights release."
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
      "id": "intake-2553#record",
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
        "KERN-1 -> P11 / RVP-RACE-1",
        "KERN-3 -> P3 / AKX-ALL-31.EDGE",
        "KERN-4 -> P3 / AKX-ALL-31.QDEC",
        "KERN-6 -> P3 / RVP-CTR-1",
        "KERN-7 -> P11 / C5-ISA-1",
        "KERN-8 -> P11 / C5-ISA-2",
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
        "KERN-7 -> P11 / C5-ISA-1",
        "KERN-8 -> P11 / C5-ISA-2",
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
        "KERN-2 -> P11 / RVP-RACE-2",
        "KERN-11 -> P11 / RVP-RACE-2",
        "PRE-2557 -> P11 / RVP-RACE-1",
        "W5VERIF-1 -> P11 / RVP-RACE-2",
        "W5VERIF-4 -> P11 / RVP-RACE-2"
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
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-research-loop.md",
        "kv-prefix-fork-and-paged-attention.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "AGENT-9 -> P3 / AK-WIN-CNT-1 / AK-PROF-ATTR-1",
        "AGENT-10 -> K3",
        "AGENT-11 -> decline: the Resin engine/runner split has no CPU or ROCm runner and production serving is llama.cpp.",
        "PRE-2562 -> P3 / AK-WIN-CNT-1",
        "W5META-9 -> P3 / AK-WIN-CNT-1",
        "W5META-10 -> P3 / AK-PROF-ATTR-1",
        "W5META-11 -> P3 / AK-WIN-CNT-1 / AK-PROF-ATTR-1"
      ]
    },
    {
      "id": "intake-2563",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "intake-derived-work-2026-07-25.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "PRE-2563 -> P12 / ID-RI-ANCHOR-GATE",
        "W5META-1 -> P12 / ID-RI-ANCHOR-GATE",
        "W5META-2 -> P12 / ID-RI-LANE-HEAD",
        "W5META-3 -> P12 / ID-RI-STAGE-GUARD",
        "W5META-4 -> P12 / ID-RI-DECLINE-VOCAB",
        "W5META-5 -> decline: the dive return schema plus the per-claim second reader already give typed, checked outputs.",
        "W5META-6 -> decline: session resume already exists in the skill and the plan checkpoint carries the durable record.",
        "W5META-7 -> decline: Octopus gates on path coverage only and itself says on-contract behaviour is not proven, so it adds n",
        "W5META-8 -> decline: the intake id resolver and the vidya citation gate already catch dangling ids."
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
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "architect-model-selection-bench.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "TCAP-1 -> P8 / AMS-TCAP-1",
        "TCAP-4 -> decline: the vendor PRO tier is closed and no method is disclosed.",
        "PRE-2567 -> P8 / AMS-TCAP-1"
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
        "PRE-2568 -> M1",
        "W5GPU-8 -> decline: no NCM checkpoint shares a served vocabulary and no acceptance number exists; reopen on such a releas"
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
        "KERN-1 -> P11 / RVP-RACE-1",
        "KERN-2 -> P11 / RVP-RACE-2",
        "KERN-4 -> P3 / AKX-ALL-31.QDEC",
        "KERN-10 -> P11 / RVP-RACE-1",
        "KERN-11 -> P11 / RVP-RACE-2",
        "PRE-2570 -> P11 / RVP-RACE-1",
        "W5VERIF-1 -> P11 / RVP-RACE-2",
        "W5VERIF-2 -> P11 / RVP-EQV-1",
        "W5VERIF-3 -> P11 / RVP-RACE-1",
        "W5VERIF-4 -> P11 / RVP-RACE-2"
      ]
    },
    {
      "id": "intake-2571",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "gpu-acceleration-path.md",
        "gpu-serving-tie-in-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "LOOP-1 -> P10 / GPU-LOOP-1",
        "LOOP-2 -> P10 / GPU-PLT-1",
        "PRE-2571 -> P10 / GPU-LOOP-1",
        "W5GPU-1 -> P10 / GPU-LOOP-1",
        "W5GPU-4 -> P10 / GPU-PLT-1",
        "W5GPU-5 -> P10 / GPU-PLT-2"
      ]
    },
    {
      "id": "intake-2572",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "architect-model-selection-bench.md",
        "cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "TCAP-1 -> P8 / AMS-TCAP-1",
        "TCAP-2 -> K1",
        "TCAP-3 -> P8 / AMS-TCAP-1",
        "PRE-2572 -> P8 / AMS-TCAP-1"
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
        "MEM-3 -> decline: re-priced on the GPU, the in-weights calculator still loses: chip tokens are serial (0.5-1 s per call",
        "PRE-2574 -> P3 / AKX-ALL-31.GDN",
        "W5GPU-7 -> decline: same GPU re-pricing as the calculator row; serial chip tokens dominate on any device."
      ]
    },
    {
      "id": "intake-2575",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-champion-aggregate.md",
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEECH-1 -> P4 / CS-8.STT8",
        "SPEECH-2 -> M4",
        "SPEECH-3 -> P9 / CH-32",
        "SPEECH-4 -> M4",
        "W2SP-1 -> P4 / CS-8.RT1",
        "PRE-2575 -> P9 / CH-35",
        "W5FOLD-4 -> P9 / CH-32"
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
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "SPEC2-4 -> K1",
        "W5FT-2 -> P2 / DF2-FT-1",
        "W5FT-3 -> P2 / DF2-FT-1",
        "W5FT-6 -> P2 / DF2-FT-1"
      ]
    },
    {
      "id": "intake-2579",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-champion-aggregate.md",
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-1 -> P4 / CS-8.RT1",
        "W2SP-2 -> K4",
        "W5FOLD-4 -> P9 / CH-32"
      ]
    },
    {
      "id": "intake-2580",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-champion-aggregate.md",
        "conversation-stack.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2SP-6 -> P4 / CS-8.STT8",
        "W5FOLD-4 -> P9 / CH-32"
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
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "gpu-acceleration-path.md",
        "gpu-serving-tie-in-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-2 -> P10 / GPU-PLT-2",
        "W5GPU-4 -> P10 / GPU-PLT-1",
        "W5GPU-5 -> P10 / GPU-PLT-2"
      ]
    },
    {
      "id": "intake-2585",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "gpu-acceleration-path.md",
        "gpu-serving-tie-in-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-1 -> P10 / GPU-LOOP-1",
        "W2LOOP-4 -> K2",
        "W5GPU-2 -> P10 / GPU-LOOP-3",
        "W5GPU-3 -> P10 / GPU-LOOP-2"
      ]
    },
    {
      "id": "intake-2586",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "gpu-acceleration-path.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W2LOOP-1 -> P10 / GPU-LOOP-1",
        "W2LOOP-4 -> K2",
        "W5GPU-2 -> P10 / GPU-LOOP-3"
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
        "W2LOOP-3 -> K2",
        "W5GPU-9 -> decline: a single-task, few-seed result with no performance lever on either device."
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
        "W2KERN-1 -> P11 / C5-ISA-1",
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
        "W2KERN-4 -> P3 / AK-FAILRULE-1"
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
        "autokernel-champion-aggregate.md",
        "dflash2-block-drafter-experimental-build.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W3SPEC-1 -> P1 / DF2-12.1",
        "W3SPEC-2 -> P1 / DF2-12.1",
        "W3SPEC-3 -> P9 / CH-37"
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
      "id": "intake-2594#record",
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
        "autokernel-champion-aggregate.md",
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-3 -> P5 / TD-23.D1",
        "W5FOLD-1 -> P9 / CH-33"
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
        "W4UP-3 -> P5 / TD-23.D1",
        "W5FOLD-2 -> decline: the fix touches only the Metal backend; no CPU or HIP code path in our stack changes."
      ]
    },
    {
      "id": "intake-2601",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "autokernel-champion-aggregate.md",
        "typed-decision-plane.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "W4UP-3 -> P5 / TD-23.D1",
        "W4UP-4 -> M4",
        "W5FOLD-3 -> P9 / CH-36"
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
      "gap": "No oracle-headroom or per-slot coverage number exists for the incumbent selector; the temp>0 branch samples proposals although point-mass proposals are lossless; the capture contract omits the teacher distribution. The served drafter accepts 0.29-0.39 on production agentic temp-1 traffic against 0.62-0.73 on the benchmark shape, and no one has fine-tuned it on our traffic.",
      "operational_change": "Offline lattice-headroom probe, an env-gated point-mass A/B, and a KL-versus-hard-label fine-tune pilot of the served drafter on captured production traffic (DF2-FT-1).",
      "benefit_direction": "Possible higher acceptance at no training cost; greedy output and the lattice ABI unchanged; distribution exactness gated by SPEC-PIT.1.",
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "execution_conditions": "Experimental build, off by default; MI210 windows for the dump, capture (about 3 GPU-h) and training (about 4 GPU-h per arm); A/B replays in GPU windows; stack change only through an operator-signed package.",
      "closure_basis": "Immediate; a trained-selector port waits for the headroom rule (M1)."
    },
    "P3": {
      "project_objective": "AK keeps must be correct on the served shapes; the gate must catch faults that an aggregate NMSE over uniform inputs misses.",
      "implementation_ref": "epyc-inference-research autokernel evaluator/correctness.py:2377 (T0 gates), loop/gates.py:2990-3026, execution/t0_provider.py:305,3662 (race_detector_id=None); handoffs/active/autokernel-all-devices-all-dimensions.md AKX-ALL-31",
      "gap": "No edge-value inputs, aggregate-only NMSE, no exhaustive dequant check, no GDN exactness oracle, planner sees no counters, no in-window graph/overlap counters, no rejection-reason rules.",
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
      "closure_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test."
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
    "P8": {
      "project_objective": "Decide whether a thinking-on mode can raise architect_general quality on the CPU flagship.",
      "implementation_ref": "epyc-orchestrator main (read 2026-10-31) orchestration/model_registry.yaml architect_general enable_thinking false; handoffs/active/architect-model-selection-bench.md:203-204 (degenerate think loops, reasoning auto 0/4)",
      "gap": "Thinking is off because the base model loops; a shorter-thinking finetune of the same base has never been measured here.",
      "operational_change": "Three-arm A/B (base thinking off, base thinking on, ThinkingCap thinking on) with a shared-head arm.",
      "benefit_direction": "A higher-effort mode only if it beats thinking-off with bounded loops and tokens; production stays thinking-off otherwise.",
      "owner": "handoffs/active/architect-model-selection-bench.md",
      "execution_conditions": "95.5 GB download (one at a time), CPU window for the A/B; any mode change is an operator-signed stack change.",
      "closure_basis": "Immediate."
    },
    "P9": {
      "project_objective": "Keep the champion current with upstream features our consumers need, by version-past-production.",
      "implementation_ref": "champion ak/champion/llama-cpp-ffc1bac82eec at C5 c72ec82f5; upstream PRs 30629, 30636, 29818, 30361, 25994, 30408 not ancestors; 31252/31257/31269/31287/31386/31283/29823 not fetched; tools/server/server-context.cpp +593 lines in the champion",
      "gap": "Only #28123 of the surfaced fixes is in the champion; speech, decision, looped and np>1 consumers need code it lacks.",
      "operational_change": "Merge-tree census first, then fold groups gated on their consumer measurements; the non-causal ubatch fix and the np>1 fixes ride as safety.",
      "benefit_direction": "Consumers gain their features without a production patch; champion gates must pass on every fold.",
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "execution_conditions": "Experimental branches from the current champion tip; store images; promotion only through the kernel-promotion runbook.",
      "closure_basis": "Immediate."
    },
    "P10": {
      "project_objective": "Test whether looped models earn a place on the MI210, where compute is spare at concurrency.",
      "implementation_ref": "MI210 ridge 120.1 FLOP/B (handoffs/completed/mi210-mfma-compute-bound-paths.md); about 19 GiB free beside the :8083 server; upstream Nanbeige merged, Ouro PR open, PLT unported",
      "gap": "No looped model has been built or measured on our GPU; loop count is per-file upstream; the CPU-only verdicts never priced the GPU.",
      "operational_change": "Build plus roofline grid, a reliability-worker probe at high concurrency, a per-request loop switch, and a LoopCoder-v2 quality screen with a PLT port.",
      "benefit_direction": "A cheaper reliability boost or effort switch if loops pay at concurrency; sequential loops are expected near 1/L aggregate, PLT is the GPU-fit form.",
      "owner": "handoffs/active/gpu-acceleration-path.md",
      "execution_conditions": "Experimental branch; MI210 windows sized to the 19 GiB headroom; no production change.",
      "closure_basis": "Immediate."
    },
    "P11": {
      "project_objective": "Make the GPU correctness gate able to see synchronization faults in AK candidates.",
      "implementation_ref": "v10 gfx90a code object: s_barrier in MMVQ 161/279, MMQ 147/672, FA-mma 138/302, FA-vec 41/49 kernels; AK GPU work: 236/627 mechanisms and 15/31 keeps touch sync; ptx_verifier AMD scaffold records no events (analysis.rs:49-50)",
      "gap": "No race detector on the GPU path; the AMD scaffold passes trivially; equivalence coverage of quantized kernels is unknown.",
      "operational_change": "Seeded-race controls with a corrected rule, a staged AMDGCN race/deadlock executor (MMVQ plus FA-vec first), an equivalence probe for float kernels, ISA archives and an ISA-level lowering probe.",
      "benefit_direction": "Synchronization bugs caught before a keep; no runtime cost to serving.",
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "execution_conditions": "Research-repo tooling plus GPU correctness windows; 6-9 engineer-weeks for the executor, staged by milestone.",
      "closure_basis": "Immediate."
    },
    "P12": {
      "project_objective": "Stop the recorded intake failure modes (fabricated citations, stale clones, stage violations, dropped actionables) by construction.",
      "implementation_ref": ".claude/skills/research-intake/scripts/validate_intake.py (anchors checked for presence only; any decline text accepted); vidya verify_source_anchor",
      "gap": "Checks are self-reported or presence-only.",
      "operational_change": "Script-written anchor marks with a cross-entry check, lane-revision pins, script-formed stage write grants, and a closed decline-code list.",
      "benefit_direction": "Fewer silent intake defects; existing entries stay valid (grandfathered).",
      "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
      "execution_conditions": "Deterministic tooling; no compute; skill text changes through the owning handoff.",
      "closure_basis": "Immediate."
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
      "source_ref": "intake-2548#record claims 0-2; intake-2578 claims 0-2; intake-297 re-read",
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
        "AGENT-9",
        "KERN-3",
        "KERN-4",
        "KERN-5",
        "KERN-6",
        "MEM-1",
        "PRE-2550",
        "PRE-2555",
        "PRE-2556",
        "PRE-2562",
        "PRE-2574",
        "W2KERN-3",
        "W2KERN-4",
        "W5META-10",
        "W5META-11",
        "W5META-9"
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
        "SPEECH-1",
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
        "MTP-3",
        "PRE-2545",
        "PRE-2551",
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
        "LOOP-6",
        "PRE-2546",
        "PRE-2554",
        "PRE-2559",
        "PRE-2564",
        "PRE-2568",
        "PRE-2576",
        "SPEC-3",
        "SPEC-5",
        "SPEC2-3",
        "SPEECH-2",
        "SPEECH-4",
        "SPEECH-7",
        "W2KERN-5",
        "W2SP-5",
        "W3DEC-8",
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
        "LOOP-5",
        "MEM-3",
        "MEM-5",
        "MTP-5",
        "PRE-2566",
        "TCAP-4",
        "W2KERN-7",
        "W5FOLD-2",
        "W5GPU-6",
        "W5GPU-7",
        "W5GPU-8",
        "W5GPU-9",
        "W5META-5",
        "W5META-6",
        "W5META-7",
        "W5META-8"
      ],
      "basis": "Explicit grounded declines."
    },
    {
      "scan_id": "S14",
      "source_ref": "intake-2548#record claims; intake-2578 claims; wave-5 drafter costing",
      "implementation_ref": "handoffs/active/dflash2-block-drafter-experimental-build.md DF2-4, agentic-serving-harness-fixes.md:60-79 acceptance on production traffic",
      "mechanism": "Forward-KL fine-tuning of a draft model on a frozen trunk",
      "consumer": "Served 27B DFlash2 drafter on :8083",
      "application": "KL versus hard-label fine-tune pilot on captured traffic",
      "disposition": "actionable",
      "ledger_ids": [
        "MTP-1",
        "MTP-2",
        "MTP-4",
        "PRE-2548",
        "PRE-2549",
        "W5FT-1",
        "W5FT-2",
        "W5FT-3",
        "W5FT-4",
        "W5FT-5",
        "W5FT-6"
      ],
      "basis": "Measured traffic gap; trainer and converter exist."
    },
    {
      "scan_id": "S15",
      "source_ref": "intake-2567 claims; intake-2572 claims",
      "implementation_ref": "handoffs/active/architect-model-selection-bench.md:203-204",
      "mechanism": "Shorter-thinking finetune of the CPU flagship",
      "consumer": "architect_general effort mode",
      "application": "Thinking-on A/B with loop-rate gate",
      "disposition": "actionable",
      "ledger_ids": [
        "PRE-2567",
        "PRE-2572",
        "TCAP-1",
        "TCAP-3"
      ],
      "basis": "Thinking is off for a measurable reason the finetune targets."
    },
    {
      "scan_id": "S16",
      "source_ref": "intake-2575..2602 PR and issue records",
      "implementation_ref": "champion C5 c72ec82f5",
      "mechanism": "Upstream features absent from the champion",
      "consumer": "Champion fold program",
      "application": "Census then gated folds",
      "disposition": "actionable",
      "ledger_ids": [
        "LOOP-3",
        "PRE-2575",
        "SPEECH-3",
        "W3SPEC-3",
        "W5FOLD-1",
        "W5FOLD-3",
        "W5FOLD-4"
      ],
      "basis": "Ancestry checked read-only."
    },
    {
      "scan_id": "S17",
      "source_ref": "intake-2547, 2571, 2584, 2585, 2586",
      "implementation_ref": "MI210 ridge and headroom",
      "mechanism": "Weight reuse across loops; parallel loops",
      "consumer": "GPU worker and effort routing",
      "application": "Build, probes and port",
      "disposition": "actionable",
      "ledger_ids": [
        "LOOP-1",
        "LOOP-2",
        "LOOP-4",
        "PRE-2547",
        "PRE-2571",
        "W2LOOP-1",
        "W2LOOP-2",
        "W5GPU-1",
        "W5GPU-2",
        "W5GPU-3",
        "W5GPU-4",
        "W5GPU-5"
      ],
      "basis": "GPU roofline computed; no GPU measurement exists."
    },
    {
      "scan_id": "S18",
      "source_ref": "intake-2557, 2570 claims; v10 code object census",
      "implementation_ref": "research AK gate; RVP",
      "mechanism": "Race/deadlock and equivalence checking over GPU ISA",
      "consumer": "AK GPU correctness gate",
      "application": "Executor and probes",
      "disposition": "actionable",
      "ledger_ids": [
        "KERN-1",
        "KERN-10",
        "KERN-11",
        "KERN-2",
        "KERN-7",
        "KERN-8",
        "PRE-2557",
        "PRE-2570",
        "W2KERN-1",
        "W5VERIF-1",
        "W5VERIF-2",
        "W5VERIF-3",
        "W5VERIF-4"
      ],
      "basis": "Sync-touching keeps exist; no detector."
    },
    {
      "scan_id": "S19",
      "source_ref": "intake-2563 re-dive claims",
      "implementation_ref": "validate_intake.py",
      "mechanism": "Ledger rows for grants and refusals; per-arrival policy",
      "consumer": "research-intake skill",
      "application": "Four hardening tasks",
      "disposition": "actionable",
      "ledger_ids": [
        "PRE-2563",
        "W5META-1",
        "W5META-2",
        "W5META-3",
        "W5META-4"
      ],
      "basis": "Failure modes recorded in the skill."
    }
  ],
  "actionable_additions": [
    {
      "ledger_id": "W5FOLD-1",
      "source": "intake-2599 Stage-2 wave-5 plan-revision analysis",
      "action": "Fold #30408 non-causal ubatch fix as a cheap champion safety fix after a defect-reproducing control",
      "terminal_mapping": "P9 / CH-33"
    },
    {
      "ledger_id": "W5FOLD-2",
      "source": "intake-2600 Stage-2 wave-5 plan-revision analysis",
      "action": "Decline #30100 (Metal MUL_MAT+ADD fusion) for the champion",
      "terminal_mapping": "decline: the fix touches only the Metal backend; no CPU or HIP code path in our stack changes."
    },
    {
      "ledger_id": "W5FOLD-3",
      "source": "intake-2601 Stage-2 wave-5 plan-revision analysis",
      "action": "Track draft PR #29832 as the possible replacement base for the systemone fold when it merges",
      "terminal_mapping": "P9 / CH-36"
    },
    {
      "ledger_id": "W5FOLD-4",
      "source": "intake-2575, intake-2579, intake-2580 Stage-2 wave-5 plan-revision analysis",
      "action": "Real conflict and ggml-delta census before any audio-group cherry-pick",
      "terminal_mapping": "P9 / CH-32"
    },
    {
      "ledger_id": "W5FT-1",
      "source": "intake-2548#record, intake-2549, intake-297 Stage-2 wave-5 plan-revision analysis",
      "action": "Candidate (a), the 27B DFlash2 drafter (1.9B, GGUF-verified). Capture: 5 taps + final hidden = 61,440 B/token, only for completions plus their 2,048-token window (the drafter attends a 2,048 sliding window). ~0.8-1.2M tokens = 50-75 GB. Capture runs on the ...",
      "terminal_mapping": "P2 / DF2-FT-1"
    },
    {
      "ledger_id": "W5FT-2",
      "source": "intake-2548#record, intake-2578 Stage-2 wave-5 plan-revision analysis",
      "action": "Candidate (c), the frontdoor Qwen3.6-35B-A3B MTP head (blk.40: 0.845B params, of which ~0.80B are 256x experts; hidden 2048; served from the same Q8_0 file at draft_max 4). Capture the trunk pre-head hidden at every position (4,096 B/token). It is both the ...",
      "terminal_mapping": "P2 / DF2-FT-1"
    },
    {
      "ledger_id": "W5FT-3",
      "source": "intake-2548#record, intake-2578 Stage-2 wave-5 plan-revision analysis",
      "action": "Candidate (b), the Qwen3.8-Flash-Next MTP head (shared-Q8_0 file: 32 tensors, 2.607B params, of which 2.517B are 512x experts; attention with a QSA indexer, top_k 2048; 4-stream hyper-connections). Capture: the hc stream state at 10,240 x bf16 = 20,480 ...",
      "terminal_mapping": "P2 / DF2-FT-1"
    },
    {
      "ledger_id": "W5FT-4",
      "source": "intake-2548#record, intake-2549 Stage-2 wave-5 plan-revision analysis",
      "action": "Settle KL versus hard labels on the real served drafter (arms H and K plus a second seed in DF2-FT-1), not on the Soft-MTP 167M toy. The toy result would not transfer: different module (non-causal block drafter with a selector), different vocabulary (50,304 ...",
      "terminal_mapping": "P2 / DF2-FT-1"
    },
    {
      "ledger_id": "W5FT-5",
      "source": "intake-2548#record Stage-2 wave-5 plan-revision analysis",
      "action": "Fold MTP-4 (realign a served finetune's stock head) into a standing onboarding rule. Any served drafter or MTP head not co-trained on the exact served trunk and quant gets frozen-trunk KL re-alignment on its own traffic. That covers fine-tunes (the ...",
      "terminal_mapping": "P2 / DF2-FT-1"
    },
    {
      "ledger_id": "W5FT-6",
      "source": "intake-2578 Stage-2 wave-5 plan-revision analysis",
      "action": "Scope SPEC2-4 (Nemotron Sec 3.4 recipe). Hidden-state sampling over earlier draft steps applies to recursive MTP heads (frontdoor, Flash-Next), not to DFlash2, which drafts its whole block in one non-causal pass from the anchor. T=2 versus T=1 is a free extra ...",
      "terminal_mapping": "P2 / DF2-FT-1"
    },
    {
      "ledger_id": "W5GPU-1",
      "source": "intake-2547, intake-2571, intake-2551 Stage-2 wave-5 plan-revision analysis",
      "action": "Restate LOOP-1 with GPU arithmetic: loops multiply weight bytes, KV reads and FLOPs equally, so aggregate is about 1/L at every batch; batching removes only the weight term; MHA KV (768 KiB/token at 4 loops) makes Ouro-1.4B KV-bound beyond about 123 tokens of ...",
      "terminal_mapping": "P10 / GPU-LOOP-1"
    },
    {
      "ledger_id": "W5GPU-2",
      "source": "intake-2585, intake-2586 Stage-2 wave-5 plan-revision analysis",
      "action": "Per-request num_loops (setter, graph-param/can_reuse, k-class batch split, prefix-cache rule k2<=k, k_max cache sizing) with a router-oracle decision rule.",
      "terminal_mapping": "P10 / GPU-LOOP-3"
    },
    {
      "ledger_id": "W5GPU-3",
      "source": "intake-2585, intake-2547 Stage-2 wave-5 plan-revision analysis",
      "action": "Looped small model as reliability-boosted GPU batch worker vs equal-cost dense and majority-of-4 controls, with the incumbent worker scored for the first time on the worker battery.",
      "terminal_mapping": "P10 / GPU-LOOP-2"
    },
    {
      "ledger_id": "W5GPU-4",
      "source": "intake-2584, intake-2571 Stage-2 wave-5 plan-revision analysis",
      "action": "Replace the LoopCoder-v2 monitor with a transformers-custom-code quality screen on the MI210 (HE+, LCB, BCB, coder suite) against Qwen3.8-27B and the CPU frontdoor.",
      "terminal_mapping": "P10 / GPU-PLT-1"
    },
    {
      "ledger_id": "W5GPU-5",
      "source": "intake-2584, intake-2571 Stage-2 wave-5 plan-revision analysis",
      "action": "Port PLT (CLP rows, shared loop-1 KV, 64-token gated window) as a new arch on llama.cpp-experimental with HF-parity and decode-step-ratio acceptance.",
      "terminal_mapping": "P10 / GPU-PLT-2"
    },
    {
      "ledger_id": "W5GPU-6",
      "source": "intake-2551 Stage-2 wave-5 plan-revision analysis",
      "action": "LOOP-5 re-check on the GPU: at batch above E/top_k every expert is touched each pass, so a looped MoE at R=5 reads about R x its total expert bytes (1.3B total x 5 = 6.5 GB vs 2.9B x 1 = 2.9 GB for a quality of 46.9 vs 50.2 Overall); GPU does not reverse the ...",
      "terminal_mapping": "decline: no looped-MoE checkpoint or code is released; reopen on a weights release."
    },
    {
      "ledger_id": "W5GPU-7",
      "source": "intake-2550, intake-2574 Stage-2 wave-5 plan-revision analysis",
      "action": "MEM-3 re-priced on the MI210 instead of the CPU: text tokens cost 18.7 GB / (1433 GB/s x 0.715 fp16 attainment) = 18 ms vs 9 ms for the 9.3 GB base (L4 check: 18.7/0.30 = 62 ms vs the 68 ms the author reports); chip tokens are serial and autoregressive, ...",
      "terminal_mapping": "decline: same GPU re-pricing as the calculator row; serial chip tokens dominate on any device."
    },
    {
      "ledger_id": "W5GPU-8",
      "source": "intake-2546, intake-2568 Stage-2 wave-5 plan-revision analysis",
      "action": "LOOP-6 re-check: the monitor was never CPU-bandwidth based; the constraints are a per-dataset VQ tokenizer at about 100M-725M parameters with no served-vocabulary checkpoint, finest level (the first token) generated last, and no acceptance number against an ...",
      "terminal_mapping": "decline: no NCM checkpoint shares a served vocabulary and no acceptance number exists; reopen on such a release."
    },
    {
      "ledger_id": "W5GPU-9",
      "source": "intake-2587 Stage-2 wave-5 plan-revision analysis",
      "action": "W2LOOP-3 re-check: GDN beta cap is a monitorability finding with no GPU lever; unchanged.",
      "terminal_mapping": "decline: a single-task, few-seed result with no performance lever on either device."
    },
    {
      "ledger_id": "W5META-1",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Anchor mark written only by a script, plus cross-paste check, for fabricated citations",
      "terminal_mapping": "P12 / ID-RI-ANCHOR-GATE"
    },
    {
      "ledger_id": "W5META-10",
      "source": "intake-2562 Stage-2 wave-5 plan-revision analysis",
      "action": "Summed vs active-union vs critical-path attribution and no cross-run subtraction",
      "terminal_mapping": "P3 / AK-PROF-ATTR-1"
    },
    {
      "ledger_id": "W5META-11",
      "source": "intake-2562 Stage-2 wave-5 plan-revision analysis",
      "action": "Resin vs Annex K / AK loop (Resin cite = docs/benchmarks.md, optimize-resin-performance SKILL.md; ours = measurement/protocols/kernel-research.md, bench-cpu.md, gpu-cross-device.md) / noise floor: Resin none (qualitative 'show the spread') vs ours A/A p95 phi ...",
      "terminal_mapping": "P3 / AK-WIN-CNT-1 / AK-PROF-ATTR-1"
    },
    {
      "ledger_id": "W5META-2",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Pin lane revision per citation and emit stale_epoch for changed files, for stale clones",
      "terminal_mapping": "P12 / ID-RI-LANE-HEAD"
    },
    {
      "ledger_id": "W5META-3",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Script-formed stage write grant checked by main, replacing self-reported audit lines",
      "terminal_mapping": "P12 / ID-RI-STAGE-GUARD"
    },
    {
      "ledger_id": "W5META-4",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Closed decline-reason vocabulary so no actionable is closed by a free-text reason",
      "terminal_mapping": "P12 / ID-RI-DECLINE-VOCAB"
    },
    {
      "ledger_id": "W5META-5",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Typed capability interfaces for dive subagents",
      "terminal_mapping": "decline: the dive return schema plus the per-claim second reader already give typed, checked outputs."
    },
    {
      "ledger_id": "W5META-6",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Durable append-only run records",
      "terminal_mapping": "decline: session resume already exists in the skill and the plan checkpoint carries the durable record."
    },
    {
      "ledger_id": "W5META-7",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Policy-gated self-modification of the skill",
      "terminal_mapping": "decline: Octopus gates on path coverage only and itself says on-contract behaviour is not proven, so it adds nothing to plan review."
    },
    {
      "ledger_id": "W5META-8",
      "source": "intake-2563 Stage-2 wave-5 plan-revision analysis",
      "action": "Unverified ids",
      "terminal_mapping": "decline: the intake id resolver and the vidya citation gate already catch dangling ids."
    },
    {
      "ledger_id": "W5META-9",
      "source": "intake-2562 Stage-2 wave-5 plan-revision analysis",
      "action": "In-window path/compile counters missing from Annex K record grammar",
      "terminal_mapping": "P3 / AK-WIN-CNT-1"
    },
    {
      "ledger_id": "W5VERIF-1",
      "source": "intake-2570, intake-2557 Stage-2 wave-5 plan-revision analysis",
      "action": "Record the race/deadlock/equivalence coverage matrix per hot gfx90a kernel family (v10 code-object counts and source anchors in this file header) in rocm-verify-profile-backend.md beside RVP-RACE-2, so later scoping cites measured coverage, not the paper ...",
      "terminal_mapping": "P11 / RVP-RACE-2"
    },
    {
      "ledger_id": "W5VERIF-2",
      "source": "intake-2570 Stage-2 wave-5 plan-revision analysis",
      "action": "Equivalence-port decision: decline for bit-level quant kernels on coverage (1116/1497 AK GPU experiment rows); a seeded sub-tolerance mutant probe decides the FA/GDN/mmvf subclass.",
      "terminal_mapping": "P11 / RVP-EQV-1"
    },
    {
      "ledger_id": "W5VERIF-3",
      "source": "intake-2570 Stage-2 wave-5 plan-revision analysis",
      "action": "Fix the RVP-RACE-1 decision rule (>=1 of 20 passes is a miss, not all 20), add waves-per-WG and ISA s_barrier-delta controls, add the LDS-DMA site, and make its mutants RVP-RACE-2 fixtures rather than its trigger.",
      "terminal_mapping": "P11 / RVP-RACE-1"
    },
    {
      "ledger_id": "W5VERIF-4",
      "source": "intake-2570, intake-2557 Stage-2 wave-5 plan-revision analysis",
      "action": "Level choice for the gfx90a checker is AMDGCN ISA from the built code object, not LLVM IR or HIP source: IR lacks waitcnts and the inline-asm semantics the AMD hot paths rely on, and cannot see ISA-edited (C5-ISA-2) candidates.",
      "terminal_mapping": "P11 / RVP-RACE-2"
    }
  ],
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
    },
    {
      "seq": 3,
      "stage": 3,
      "ts": "2026-11-01T04:00:00Z",
      "verbatim": "The operator has NOT approved the plan yet. Revise it. [...] 1. Soft-MTP: \"isn't this a training/fine-tuning of the draft model though?\" [...] 2. \"We should consider which features from upstream llama.cpp we should fold into our champion.\" [...] 3. Looped transformers: \"what about the GPU? Did the research intake completely ignore it?\" [...] 4. The triggers [...] \"all seem relevant beyond just knowledge. Really the planner couldn't think of any actionables?\" [...] 5. Octopus-SI-OS: could it improve the quality of our research-intake skill? [...] 6. Resin: say exactly what about its measurement discipline is weaker [...] 7. Volta/ptx_verifier: \"NVIDIA-only is not a sufficient reason to discard unless there's also a reason we wouldn't benefit much from porting it to our hardware.\" [...] 8. Qwenputer: [...] On a SMALL model served on the GPU [...] does an in-weights calculator become worthwhile? [...] General: the intake under-weighted the GPU.",
      "disposition": "planned",
      "plan_ref": "P9",
      "reason": "Revision 2 answers all eight points: P2 drafter fine-tune pilot, P9 upstream fold, P10 looped models on the MI210, P8/P11/P3 triggers turned into tasks, P12 Octopus-derived skill hardening, Resin comparison in P3, GPU re-pricing of every CPU-bandwidth verdict."
    }
  ],
  "outcome_reviews": {
    "W3SPEC-1": {
      "required_outcome": "Bounded probe (own scratch server, GPU correctness window, no region-lock needed per CORRECTNESS rule): on the production 27B shape (Q8_0, DFlash2 n-max 7, np 4, kv-unified, q8 KV, ROCm0) and on the frontdoor shape (Qwen3.6-35B-A3B-MTP Q8_0, draft-mtp n 4, np ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-12.1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; KPF-RS-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; SPEC-CANARY.1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; G2-CONC.MP carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-PM carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "KERN-3": {
      "required_outcome": "Add structured edge-value input families to the AK op suite beside the AK_SENS scale transforms. Families: f16-range near-max (overflow), subnormal-scale (underflow), cancellation pairs within reduction rows, softmax rows that are all-equal or contain -inf, ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.QDEC carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.GDN carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant table (site, s_barrier delta, waves/WG, pass count out of 20, max NMSE) plus the 20/20 control, committed with raw verdicts; TSAN anchor report with suppression list; fixtures handed to RVP-RACE-2."
        }
      ]
    },
    "KERN-10": {
      "required_outcome": "Wire a CPU race detector for routes touching threading. Build a TSAN test-backend-ops (CPU), using LLVM libomp with Archer annotations because production uses OpenMP; GGML_OPENMP=OFF would test a different threading path. Run it on the v10 anchor first.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant table (site, s_barrier delta, waves/WG, pass count out of 20, max NMSE) plus the 20/20 control, committed with raw verdicts; TSAN anchor report with suppression list; fixtures handed to RVP-RACE-2."
        }
      ]
    },
    "KERN-6": {
      "required_outcome": "Counter-grounded planner signals. For the top-1 hotspot kernel of each GPU screen, capture a fixed, declared counter subset via rocprofv2 (from the proven 465-counter taxonomy). Attach it to the hotspots rows. Adopt TAIC's rule that each hypothesis cites a ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-CTR-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; C5-ISA-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; C5-ISA-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; CH-32 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-32",
          "task_text": "- [ ] **CH-32 — Upstream-delta fold census: dry-run merge of upstream tip into the champion C5 (c72ec82f5) to replace the PR line counts with real conflict and ggml-generation numbers (intake-2575#record, intake-2579#record, intake-2593#record, intake-2585#record, intake-2599#record).** Immediately, no compute: git fetch the upstream remote into the llama.cpp object store (no checkout, no branch move, production tree and champion ref untouched), then for each fold group (A cbe28bb3 non-causal ubatch; B b77d646751 Nanbeige4.2 plus Ouro #29823 head; C a4cb4c61fd + 7e3eeee048 systemone/H2O; D 30629, 30636, 31252, 31257, 31269, 31287, 31386, 31283 audio/LFM3/realtime) run git merge-tree --write-tree against c72ec82f5 and record per group files changed, conflicted hunks per file (expect tools/server/server-context.cpp, src/llama-context.cpp, src/llama-model.cpp), whether the group needs ggml ops or a ggml bump beyond v10 lineage (diff ggml/ include list), and the minimal prerequisite commit chain (b10303..b11960 is 1657 builds). Output table lands in docs/reference/kernel-manifests/llama-v11-manifest.md as pending-fold rows with a presence gate each (ancestry check), per README rule 4. Controls: frozen base sha, per-group raw merge-tree output kept, full group list, predeclared rule: a group with more than 3 conflicted files in server/ or any conflict in ggml-cpu, iqk or speculative code is cut by hand on a fresh experimental branch from C5 rather than cherry-picked in bulk.",
          "acceptance": "Table of 4 groups with conflicted-file counts, ggml delta yes/no and prerequisite chain committed as llama-v11-manifest.md pending-fold rows; raw merge-tree outputs under the scratch dir."
        }
      ]
    },
    "W2SP-6": {
      "required_outcome": "Add a Voxtral-Mini-4B-Realtime GGUF through mtmd-cli run_audio_stream arm to the CS-8.STT5 screen (ranks and rejects only) on a scratch upstream build; record encoder and decoder times separately as the CLI already prints them.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; CS-8.RT1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-18.1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; RI-25 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; UFH14-TOOLS-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; CF-AKV-0 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; VB-CERT-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; VB-CERT-1 carry the required behavior with controls and a decision rule.",
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-1",
          "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).",
          "acceptance": "Experimental branch + HIP/CPU build exist; parity receipt on gfx90a and CPU; the np x loops x ctx x KV grid with predictions and ratios is committed with raw JSON; the CPU leg and the GPU arithmetic table are filed; the 0.5-1.1x rule is applied to every cell."
        }
      ]
    },
    "LOOP-2": {
      "required_outcome": "Ingest and dive LoopCoder-v2 (arXiv 2606.18023): released 7B PLT 2-loop coder (Apache-2.0, HF Multilingual-Multimodal-NLP/LoopCoder-V2, 14 layers, hidden 5120, 8 KV heads) is the first PLT checkpoint we can actually run; card claims SWE-bench Verified 43.0 -> ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-PLT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-serving-tie-in-program.md",
          "task_id": "GPU-PLT-1",
          "task_text": "- [ ] **GPU-PLT-1 — LoopCoder-v2 (7.6B PLT coder, Apache-2.0) quality screen on the MI210 through transformers custom code, before and independent of the GGUF port (intake-2584#record, intake-2571#record).** Load Multilingual-Multimodal-NLP/LoopCoder-V2 at the pinned HF sha b87cf3a (BF16, 7,615,749,680 params, 15.2 GB, fits the about 19 GiB headroom beside :8083 without a KV problem) in an isolated venv with the transformers version its configuration_iquestpltcoder.py needs (Ouro needed 4.57.x, the research venv has 5.15.0: do not assume); confirm torch.version.hip and bf16 on gfx90a first; read config.json to see whether the loop count is a config field (the paper trains R=1..4 as separate models, so a forced R=1 on the released weights is not the paper R=1). Frozen inputs: HumanEval+ (164), LiveCodeBench subset released after the model cutoff (n>=200), BigCodeBench-hard subset, plus the frozen coder-suite items used for coder_escalation (cruxeval and the others E-7 scored: math 85.0, mmlu_pro 27.5, gpqa_diamond 47.5, cruxeval 22.5 at terse template 1443ea9ab4bb). Arms: LoopCoder-v2 as released; incumbent coder_escalation Qwen3.8-27B Q8 on :8083 (same harness, thinking off and medium); frontdoor Qwen3.6-35B-A3B on CPU; size control Qwen3-4B-Instruct-2507 (on disk). Controls: frozen items and scorer hashes, incumbent baselines, per-item raw outputs, 2 seeds, full denominator, rule below. Replication check against the paper own table: R=2 reports HE+ 84.1, LCB 35.4, BCB 46.1 and SWE-bench Verified 64.4 (harness unnamed, single seed, vendor-authored); accept the replication if HE+ >= 80 and the LCB subset score is within 5 points of the paper 35.4 after harness adjustment stated. Decision rule: open the serving legs of GPU-PLT-2 (agentic SWE-40 on the same scaffold that scored Qwen3.8-27B 21/40 = 52.5%, shadow lane only) if pooled pass@1 over HE+ and LCB is non-inferior to Qwen3.8-27B within 8 points (paired bootstrap lower bound) or the replication check passes; otherwise record NO-GO with the table (the port of GPU-PLT-2 still completes as parity work). Arithmetic that motivates it: at np=16, C=8k, Q8 (about 8.1 GB incl. head, KV 56 KiB/token f16 because later loops share loop-1 KV and keep only a 64-token window) a PLT-2 step is about 15.2 GB / 1433 GB/s = 10.6 ms bandwidth vs 2.5 ms compute at 32 rows, i.e. 1,510 tok/s ideal aggregate (about 600 derated by the 27B np8 ratio 157/400), vs 94 tok/s live at 4 concurrent on the 27B.",
          "acceptance": "Per-benchmark table with per-item outputs for all arms; replication verdict vs the paper numbers stated with harness differences; the non-inferiority rule applied and the GPU-PLT-2 serving legs opened or closed."
        }
      ]
    },
    "LOOP-3": {
      "required_outcome": "Correct the stale gate: Ouro now has a community llama.cpp port (BrandeisPatrick/loop-transformer, ouro arch, 324 added lines, PR ggml-org/llama.cpp#29823, GGUFs for Ouro 1.4B/2.6B +Thinking) built on upstream looped-model machinery merged for Nanbeige4.2 (PR ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CH-34 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-34",
          "task_text": "- [ ] **CH-34 — Looped-model support fold group: Nanbeige4.2 (#25994 merged, b77d646751, +265/-1, 10 files incl. new src/models/nanbeige.cpp) plus Ouro (#29823, open, ~324 added lines, head sha to be pinned from the CH-32 fetch) (intake-2586#record, intake-2585#record, intake-2547#record).** Value: unblocks the looped-probe lane (GPU-LOOP-1: tg at ouro.num_loops 1/2/4, GB/s per effective token on EPYC; HIP run on MI210) without a hand port; files are disjoint from AK kernels, iqk and DFlash2 so expected cost is low. Immediately cut branch experimental/champion-plus-looped-arch from the current champion tip (fresh-tip rule), cherry-pick both, build CPU plus HIP store images, gates: test-llama-archs and the new-arch smoke load, no-regression greedy identity on Q38FN and one dense model vs champion, linkage proof. Fold decision is gated on the GPU-LOOP-1 probe: fold into the champion if Ouro-1.4B or Nanbeige4.2 runs coherent and the probe is not rejected on the predeclared tok/s-per-quality rule; otherwise keep the branch as the probe instrument and record the exclusion reason in the manifest. Open PR is not a block: the branch carries our own cherry-pick and is rebased when the PR merges.",
          "acceptance": "Branch built and smoke-passed within one working session; manifest row IN or EXCLUDED-with-reason after W2LOOP-1 result."
        }
      ]
    },
    "LOOP-5": {
      "required_outcome": "Record in reasoning-compression.md only: looped MoE R=5 at 0.3B-1.3B reaches reasoning parity with 0.6B-2.9B at 1.8x training-compute-defined inference compute while trailing Overall 46.9 vs 50.2; no latency/bytes measured; no checkpoint released in the text.",
      "review_status": "closed-with-basis",
      "review_basis": "no looped-MoE checkpoint or code is released, and on the GPU looping a MoE multiplies expert byte reads rather than hiding them.",
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
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test.",
      "task_refs": []
    },
    "SPEC-5": {
      "required_outcome": "Domino-style GRU + full-vocab low-rank correction head on the DFlash2 drafter: no work now. It needs full drafter co-training with the curriculum, and its sequential head adds a 256x248320 logit-residual projection per position on the critical path. Revisit ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test.",
      "task_refs": []
    },
    "MTP-2": {
      "required_outcome": "Bounded frozen-trunk probe on the Soft-MTP repo (MI210, ROCm torch, <=4 GPU-h, no llama.cpp). Take the released 167M (or 332M) NTP checkpoint, set freeze_backbone=true, and train fresh K=3 DeepSeek-style heads under two arms with identical data order, seed, ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "MTP-4": {
      "required_outcome": "Record a trigger on the speculative-decoding refresh. If a served fine-tune ships with a stock (base-co-trained) MTP head, as already observed for ThinkingCap and Qwopus, the remedy is head-only re-alignment on the frozen fine-tuned trunk against its own NTP ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W3SPEC-3": {
      "required_outcome": "If W3SPEC-1 shows divergence: reproduce on the experimental branch and try the PR #29454 approach (copy pre-ubatch state into unwritten snapshot slots every ubatch) as the candidate fix; it was never merged, so it must be carried as our own patch on a ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CH-37 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-37",
          "task_text": "- [ ] **CH-37 — Recurrent-state / np>1 slot-contamination fix fold, gated on DF2-12.1 (intake-2597#record, intake-2598#record, intake-2591#record).** Already in the champion: #28123 rollback port 0771238438 (ancestor of C5 and C6 verified read-only). Open exposure: issues 26695 (seq_rm true without recurrent-state restore) and 28019 (multi-seq split replay corrupts rs when rollback enabled) plus the CH-31-DEF1 batched-decode divergence. Immediately: confirm by reading src/llama-memory-recurrent.cpp on C5 whether the 26695 and 28019 fix commits (find them with git log --grep on the fetched upstream) are ancestors; record the answer in the manifest. If DF2-12.1 (temp-0 cross-slot token identity at np 4 on :8083 and :8070 shapes) shows any divergence, this task becomes the fix: cherry-pick the upstream fixes onto a fresh branch from the champion tip, rerun DF2-12.1 as the gate (zero divergent tokens over the frozen set versus np 1) plus Q38FN greedy identity. If DF2-12.1 is clean, the manifest row records the ancestry check and the task closes.",
          "acceptance": "Ancestry answer committed; either DF2-12.1 clean or a fix branch with zero-divergence rerun."
        }
      ]
    },
    "SPEC2-3": {
      "required_outcome": "Note thinking-mode default sampling repetition risk: issue says model card recommends presence_penalty 0-2 and attributes loops to degenerate state amplified by temp 1.0 / top_k 20 / top_p 0.95; check the Flash-Next architect_general request sampler against ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test.",
      "task_refs": []
    },
    "LOOP-6": {
      "required_outcome": "Monitor NCM as a drafter source: trigger = a released NCM-style generator with a general-text tokenizer sharing a served model vocabulary, or any measured acceptance rate against an AR target. Do not build now: released checkpoints are per-dataset ~100M-725M ...",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test.",
      "task_refs": []
    },
    "LOOP-4": {
      "required_outcome": "Bounded CPU probe on a llama.cpp-experimental branch with the Ouro port: Ouro-1.4B Q4_K_M (854 MB per card), llama-bench tg at num_loops 1/2/4 via --override-kv, reporting achieved GB/s counting bytes once per loop against the C0 153 GB/s ceiling. This ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-1, GPU-LOOP-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-1",
          "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).",
          "acceptance": "Experimental branch + HIP/CPU build exist; parity receipt on gfx90a and CPU; the np x loops x ctx x KV grid with predictions and ratios is committed with raw JSON; the CPU leg and the GPU arithmetic table are filed; the 0.5-1.1x rule is applied to every cell."
        },
        {
          "owner": "handoffs/active/gpu-serving-tie-in-program.md",
          "task_id": "GPU-LOOP-2",
          "task_text": "- [ ] **GPU-LOOP-2 — Looped small model as a reliability-boosted batch worker on the MI210: quality vs loops vs aggregate throughput against equal-cost dense and K-sample controls (intake-2585#record, intake-2547#record, intake-2551#record).** Question: at high concurrency (elastic-duty D1 batch-shedding class, np 16), does Ouro-1.4B (and 2.6B-Thinking as second tier) at 1/2/4 loops buy more correct worker answers per HBM byte than a non-looped model? Arms, served-cost arithmetic at np=16, C=1k, f16 KV (ideal step times, to be measured in GPU-LOOP-1): A1 Ouro-1.4B L=4 (5.76 GB weights/step + 12.9 GB KV, 13.0 ms, 1,230 tok/s); A2 L=2 (about 2,300); A3 L=1 (about 7,100 on the same weights); A4 Ouro-2.6B-Thinking L=4 (48 layers, about 11.3 GB weights/step, 1.5 MiB/token KV); C1 Qwen3-4B-Thinking-2507 Q8 (4.28 GB, 144 KiB/token, 3,420 tok/s, the equal-quality-class dense control); C2 Qwen3-1.7B Q8 majority-of-4 (about the same bytes per final answer as A1, 1,545 answer-equivalent tok/s: the K-sample route that the idle MFMA headroom makes free); C3 Qwen3-1.7B Q8 single sample (equal resident bytes); C0 the incumbent worker, Qwen3.6-35B-A3B on CPU :8070 (registry roles.worker_general.performance.quality_pct is null: it has never been scored on the worker battery, so it is measured here on the same frozen items). Frozen inputs: GSM8K-style math (n>=200, same problem list as the PR so the 26.0/67.0/80.5 published curve is a replication check) plus worker-battery items for explore, summarize, transform and strict tool-call JSON (n>=150 per suite), item list and scorer hashed before any generation; Ouro context stays under its trained 1024-token block (Ouro RECIPES: block_size 1024), longer prompts are a separate reported stratum. Per arm: pass@1 over 3 seeds, seed-to-seed agreement, JSON-validity rate, aggregate tok/s at np 16, wall-seconds per correct answer and correct answers per HBM GB moved; per-item raw outputs kept; correctness legs may share the card with :8083, throughput legs run in a GPU window with the host threads under the q3 claim. Controls: frozen inputs, incumbent baseline (C0 and C1), per-item raw outputs, 3-seed repeat with the A/B order alternated, full denominator including parse failures, predeclared rule. Decision rule: an Ouro arm earns a shadow-lane tenancy row (D3 shadow-only, no production traffic) only if (i) its paired accuracy vs C1 is within 2 points (McNemar not worse) and its seconds per correct answer at np=16 is at most 1.5x C1, or (ii) it beats C1 by at least 5 points at paired p<0.05 at no more than 2.5x C1 cost; the arithmetic predicts A1 costs 2.8x C1 per token, so (i) needs a real quality edge. Otherwise record NO-GO with the table and keep Ouro only as the vehicle for GPU-LOOP-3. Depends on the GPU-LOOP-1 build (our own task, not an external event).",
          "acceptance": "Frozen item list + scorer hashes; per-arm table of accuracy, seed agreement, tok/s, seconds per correct answer and correct answers per GB; C0 worker-battery score recorded; the (i)/(ii) rule applied with paired statistics; GO tenancy row or NO-GO line committed."
        }
      ]
    },
    "W2LOOP-1": {
      "required_outcome": "On an experimental llama.cpp branch freshly cut from production v10, cherry #25994 plus #29823 (about 590 added lines) and measure Ouro-1.4B Q8_0/Q4_K_M at --override-kv ouro.num_loops=int:1/2/4 on EPYC CPU (one quarter and full socket): tok/s, achieved GB/s ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-1",
          "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).",
          "acceptance": "Experimental branch + HIP/CPU build exist; parity receipt on gfx90a and CPU; the np x loops x ctx x KV grid with predictions and ratios is committed with raw JSON; the CPU leg and the GPU arithmetic table are filed; the 0.5-1.1x rule is applied to every cell."
        }
      ]
    },
    "W2LOOP-2": {
      "required_outcome": "Monitor triggers: (a) llama.cpp or vLLM PR adding iquestpltcoder / PLT, (b) an independent replication of LoopCoder-v2 R=2 SWE-bench Verified, (c) a timing number for PLT decode. Any one fires ingest-and-dive on it.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-PLT-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-PLT-2",
          "task_text": "- [ ] **GPU-PLT-2 — Parallel-Loop-Transformer architecture (iquestpltcoder) on llama.cpp-experimental: port, parity, and MI210 decode curves (intake-2584#record, intake-2571#record).** Not blocked by the absence of upstream code; estimate 1.0-1.5 kLOC, 3-5 agent-days, 3-4x the 265/324-line Nanbeige/Ouro ports because those only unroll layers and carry no CLP, shared-KV or sliding window: converter for IQuestPLTCoderForCausalLM (about 150: 14 layers, hidden 5120, 40 heads / 8 KV, FFN 27648, R, window 64, per-head gate tensors; read the HF modeling file at sha b87cf3a first); arch/hparams/tensors (about 250); graph (about 400): a decode step builds R rows per sequence, row r input = token embedding + h^(r-1) of the previous position (per-sequence state of (R-1) x n_embd, held in the recurrent-memory path so checkpoint and spec-decode rollback come with it), row 1 attends the normal full KV, rows >=2 attend the shared loop-1 K/V through the existing cross-layer KV-reuse hparams plus a private 64-entry window cache (extra logical layers in the iSWA cache) and mix with the head-wise sigmoid gate; prefill runs R shifted sweeps over the prompt; cache/state plumbing and tests (about 400-700). Acceptance: top-1 logits match the HF reference on >=1000 positions and greedy continuations match on 20 prompts, on CPU and HIP; measured decode step ratio PLT-2 vs the same weights run as a one-loop graph is <=1.15 at np<=16 (prediction 1.02-1.05, since 2 rows per stream stay under the Q8 knee of 64 rows through 32 streams) and a sequential two-loop graph on the same weights is >=1.8 (the ByteDance paper reports 4.9 vs 4.8 vs 9.4 ms at bs 4 and 8.6 vs 8.1 vs 16.1 ms at bs 32 in its own stack); KV measured at about 56 KiB/token + window; spec-decode (MTP/DFlash2) rollback test using the state snapshot. Quality and serving verdicts are GPU-PLT-1 and the SWE-40 legs, not this task; this task delivers the engine.",
          "acceptance": "Branch with the arch + converter; parity receipt on CPU and HIP; decode-step ratio and KV measurements committed against the stated predictions; rollback test passes."
        }
      ]
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-2",
          "task_text": "- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs.",
          "acceptance": "M1 receipt: per-kernel verdicts (ACCEPT/RACE/UNKNOWN) on v10 MMVQ+FA-vec at the frozen served-shape manifest with 0 RACE; a mutant table showing every RVP-RACE-1 MMVQ/FA mutant and both ISA-only mutants flagged; runtime per instance. M3 done when t0_provider emits a non-null race_detector_id for a sync-touching GPU candidate."
        }
      ]
    },
    "KERN-8": {
      "required_outcome": "GCN-Gym probe of AI lowering on gfx90a. Build a standalone harness that assembles LLM-patched AMDGCN for one compute-bound kernel (MMQ Q4_K prefill tile or FA at long context) with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a, loads it via hipModuleLoad and ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; C5-ISA-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/agentic-rocm-kernel-authoring.md",
          "task_id": "C5-ISA-2",
          "task_text": "- [ ] **C5-ISA-2 — GCN-Gym: LLM-edited AMDGCN for a compute-bound gfx90a kernel whose limiter is register allocation (intake-2555#record, intake-2556#record).** Not trigger-gated, because the HIP-source levers on the target are measured out: AK-MMQ-H10 (J-cap) NEGATIVE, the ak-27b-gpu-verify stream-k MMQ hypotheses were all refused or retired, and the ROCm 6.2 AGPR copy tax and MMQ spills are compiler-side (INF03-REGAUDIT-1: Q8_0 J=64 at 256 VGPR with 37 spills; MMA-FA DKQ>=192 at 512 VGPR with hundreds of reloads per iteration). Build a standalone harness (1-2 weeks). Extract the gfx90a .s of one kernel from an experimental v10-tip build via gfx90a_isa_audit.py; let the agent edit it with unified-diff patch tools; reassemble with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a; load with hipModuleLoad; replay the served-shape launches (the RVP-RACE-2 capture shim); diff-test against the hipcc kernel with the AK oracle (host-double for Q8_0); require gfx90a_isa_audit.py diff to exit 0, and the RVP-RACE-2 verdict once M2 lands. Target 1: MMQ Q8_0 J=64 prefill tile. Target 2: MMA-FA DKQ>=192. Run 3 runs per target at a fixed declared token budget on a frozen shape manifest; time on the GPU window with ABBA (>=2 pairs) against the hipcc incumbent, keeping per-run raw candidate .s, oracle outputs and timings. Decision rule: if >=1 of 3 runs on a target reaches >=1.05x kernel time at the served prefill shape, passes the oracle, and its ABBA intervals do not overlap the incumbent, open an experimental-tree code-object override path for that kernel as an ISA-rung AK arm; otherwise record the null with traces and stop the ISA rung for that kernel class.",
          "acceptance": "Harness committed in the research repo; for each target, 3 run records (patched .s hash, oracle verdict, audit diff exit, ABBA timings) and the predeclared decision recorded."
        }
      ]
    },
    "W2KERN-4": {
      "required_outcome": "Failure-to-rule loop for AK: after each rejected batch, classify the failure reason and, when a class recurs (>=3), have an agent propose a permanent static check or oracle input, merged only under corpus tests of all prior keeps (CAKE Sec 3.2).",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AK-FAILRULE-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-rebuild-program.md",
          "task_id": "AK-FAILRULE-1",
          "task_text": "- [ ] **AK-FAILRULE-1 — Turn recurring AK rejection reasons into pre-GPU rules from existing records (intake-2589#record, intake-2588#record).** Zero inference: classify every rejected candidate in the existing CPU and GPU campaign stores by failure reason (compile, correctness gate and which gate, timing loss, noise, harness error). For each reason class with at least 3 occurrences, draft a cheap static or pre-GPU check (CAKE-style hazard filter) and replay it over the historical candidates. Adopt a rule only if it would have rejected at least one historical failure before GPU time and no historical keep.",
          "acceptance": "Reason table with counts over the full store manifest; each drafted rule replayed with its would-have-rejected and false-reject counts; adopted rules wired before GPU dispatch."
        }
      ]
    },
    "TCAP-1": {
      "required_outcome": "Bounded A/B: base UD-IQ4_XS (current :8074 file) vs bottlecapai ThinkingCap IQ4_XS GGUF, llama-server, same recipe qwen38-flash-next-cpu-mtp, enable_thinking=true on /v1/chat/completions, frozen 40-60 prompt set (arch/plan-critique + reasoning, AIME-style, ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AMS-TCAP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/architect-model-selection-bench.md",
          "task_id": "AMS-TCAP-1",
          "task_text": "- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off.",
          "acceptance": "All arms run with per-request outputs, token counts, loop/truncation labels and alpha retained; the decision rule applied and the verdict recorded; disk and download logged."
        }
      ]
    },
    "TCAP-3": {
      "required_outcome": "If A/B runs, add arm B2 = ThinkingCap trunk + our unsloth shared-Q8_0 draft file vs embedded head, measure alpha for both",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AMS-TCAP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/architect-model-selection-bench.md",
          "task_id": "AMS-TCAP-1",
          "task_text": "- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off.",
          "acceptance": "All arms run with per-request outputs, token counts, loop/truncation labels and alpha retained; the decision rule applied and the verdict recorded; disk and download logged."
        }
      ]
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
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test.",
      "task_refs": []
    },
    "PRE-2547": {
      "required_outcome": "Dive: decide whether looped/parallel-loop decoding changes bytes-per-token on bandwidth-bound CPU decode, and whether any served or candidate model is looped.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-1",
          "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).",
          "acceptance": "Experimental branch + HIP/CPU build exist; parity receipt on gfx90a and CPU; the np x loops x ctx x KV grid with predictions and ratios is committed with raw JSON; the CPU leg and the GPU arithmetic table are filed; the 0.5-1.1x rule is applied to every cell."
        }
      ]
    },
    "PRE-2548": {
      "required_outcome": "Dive: verify Table 2 and decide whether Soft-MTP is the objective to use if we train or restore MTP heads (Flash-Next Axis E, drafter training).",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "PRE-2549": {
      "required_outcome": "Dive with intake-2548#record: check the loss implementation and whether it composes with head-only training on a frozen trunk.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "PRE-2550": {
      "required_outcome": "Dive: separate the transferable mechanism (exact GDN-state addressing) from the demo; decide if it informs GDN-hybrid serving or memory work.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.GDN carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; CS-8.STT8 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; TD-23.D1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.EDGE carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; RVP-CTR-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant table (site, s_barrier delta, waves/WG, pass count out of 20, max NMSE) plus the 20/20 control, committed with raw verdicts; TSAN anchor report with suppression list; fixtures handed to RVP-RACE-2."
        }
      ]
    },
    "PRE-2558": {
      "required_outcome": "Dive: test whether the certificate-plus-independent-checker pattern fits belief-kernel derivations or registry/handoff consistency checks.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; VB-CERT-1 carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carry the required behavior with controls and a decision rule.",
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AK-WIN-CNT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-WIN-CNT-1",
          "task_text": "- [ ] **AK-WIN-CNT-1 — Record in-window path counters beside every T1/T2 timing record (intake-2562#record).** Annex K's record grammar (`measurement/protocols/kernel-research.md` \"Record grammar\") has no field proving the timed window ran the intended path; T0 checks a dispatch trace but T1/T2 do not re-prove it. Resin keeps `graph_counts` and `overlap_counts` that exclude warmup and checks no JIT compile after warmup for unseen shapes. Do: capture hipGraph replay count vs eager launches and code-object load/JIT events inside the timed window on MI210 (use an in-process counter in a llama.cpp-experimental branch if none exists; the port is the build cost), write them as a non-gating diagnostic sidecar next to the raw samples, and draft the Annex K grammar amendment (human-amendment-only) making a path mismatch a VOID window. Controls: frozen anchor and one candidate, degraded-negative with graphs disabled (counter must show zero replays), A/A, per-window raw counters kept. Decision rule: sidecar ships if the degraded-negative is flagged and A/A is not; amendment text goes to the operator package.",
          "acceptance": "Sidecar present on a GPU T1 window with the two control outcomes recorded; amendment draft filed for ratification."
        }
      ]
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
      "review_basis": "Main read the dive passage and the current consumer; RI-25 carry the required behavior with controls and a decision rule.",
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AMS-TCAP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/architect-model-selection-bench.md",
          "task_id": "AMS-TCAP-1",
          "task_text": "- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off.",
          "acceptance": "All arms run with per-request outputs, token counts, loop/truncation labels and alpha retained; the decision rule applied and the verdict recorded; disk and download logged."
        }
      ]
    },
    "PRE-2568": {
      "required_outcome": "Dive with intake-2546.",
      "review_status": "closed-with-basis",
      "review_basis": "Triggers: DF2-LAT promote rule opens a trained-selector port; low top-16 coverage with low headroom opens a Domino-style head; DF2-FT-1 promotion opens the scale-up and stack-change package; the collapse canary tripping on repetition opens a thinking-mode guard. External event: a released NCM-style generator sharing a served vocabulary, with an acceptance number, opens a drafter test.",
      "task_refs": []
    },
    "PRE-2569": {
      "required_outcome": "Dive with intake-2561: sequential corrector baseline that DCOCO claims to beat under concurrency.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-LAT carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant table (site, s_barrier delta, waves/WG, pass count out of 20, max NMSE) plus the 20/20 control, committed with raw verdicts; TSAN anchor report with suppression list; fixtures handed to RVP-RACE-2."
        }
      ]
    },
    "PRE-2571": {
      "required_outcome": "Dive with intake-2547.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-1",
          "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).",
          "acceptance": "Experimental branch + HIP/CPU build exist; parity receipt on gfx90a and CPU; the np x loops x ctx x KV grid with predictions and ratios is committed with raw JSON; the CPU leg and the GPU arithmetic table are filed; the 0.5-1.1x rule is applied to every cell."
        }
      ]
    },
    "PRE-2572": {
      "required_outcome": "Dive: verify config (qwen4_exp, MTP layers), whether the GGUFs carry nextn tensors, and fit against the INF-70 Axis-E MTP restoration need.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AMS-TCAP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/architect-model-selection-bench.md",
          "task_id": "AMS-TCAP-1",
          "task_text": "- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off.",
          "acceptance": "All arms run with per-request outputs, token counts, loop/truncation labels and alpha retained; the decision rule applied and the verdict recorded; disk and download logged."
        }
      ]
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
      "review_basis": "Main read the dive passage and the current consumer; AKX-ALL-31.GDN carry the required behavior with controls and a decision rule.",
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
      "review_basis": "Main read the dive passage and the current consumer; CH-35 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-35",
          "task_text": "- [ ] **CH-35 — Speech/omni fold group: mtmd_audio_stream + Voxtral realtime (#30629, 2851b3bcbf, +998/-20, 27 files in tools/mtmd), realtime transcription API (#30636, 1242be66f6, +512/-14, 9 files, server-context.cpp +316), LFM3 arch (#31252), LFM3 audio+omni (#31257, +2721/-160, 31 files), /v1/realtime conversation (#31269, +1423) with tool calls (#31287), codec quant (#31386), video (#31283) (intake-2575#record, intake-2579#record, intake-2580#record, intake-2552#record).** Value: serves LFM3-Audio/Omni and Voxtral Realtime end to end from the champion server for CS-8 STT/interlocutor arms and CS-20/CS-22 realtime; the speech kernels (whisper.cpp, qwentts.cpp) are separate trees and unaffected. Cost: the biggest group; conflicts concentrated in tools/server/server-context.cpp (champion already +593 vs v10) and src/llama-model.cpp; mtmd is new surface the champion has not touched; ggml delta from CH-32. Stage 1 immediately: build the scratch upstream audio build of CS-8.STT8 (instrument, not the fold). Stage 2 gated on CS-8.STT8 (paired bootstrap WER not above +1.0 pp vs whisper in en and it) or CS-8.RT1 (realtime first-output latency beats the cascade on the 20 frozen utterances): then cut experimental/champion-plus-lfm3-audio from the current champion tip, apply the PR chain in merge order, resolve server-context.cpp by hand, rebuild CPU+HIP, gates: Q38FN/27B greedy identity vs champion (server changes must not move text decode), CS-8.STT8 WER reproduced on the folded binary within bootstrap CI of the scratch build, np>1 safety rerun of DF2-12.1. If STT8 and RT1 both fail the rule the group is recorded EXCLUDED with numbers.",
          "acceptance": "Scratch build exists with verify_ggml_linkage proof (stage 1); fold branch or EXCLUDED row with STT8/RT1 numbers (stage 2)."
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AK-WIN-CNT-1, AK-PROF-ATTR-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-WIN-CNT-1",
          "task_text": "- [ ] **AK-WIN-CNT-1 — Record in-window path counters beside every T1/T2 timing record (intake-2562#record).** Annex K's record grammar (`measurement/protocols/kernel-research.md` \"Record grammar\") has no field proving the timed window ran the intended path; T0 checks a dispatch trace but T1/T2 do not re-prove it. Resin keeps `graph_counts` and `overlap_counts` that exclude warmup and checks no JIT compile after warmup for unseen shapes. Do: capture hipGraph replay count vs eager launches and code-object load/JIT events inside the timed window on MI210 (use an in-process counter in a llama.cpp-experimental branch if none exists; the port is the build cost), write them as a non-gating diagnostic sidecar next to the raw samples, and draft the Annex K grammar amendment (human-amendment-only) making a path mismatch a VOID window. Controls: frozen anchor and one candidate, degraded-negative with graphs disabled (counter must show zero replays), A/A, per-window raw counters kept. Decision rule: sidecar ships if the degraded-negative is flagged and A/A is not; amendment text goes to the operator package.",
          "acceptance": "Sidecar present on a GPU T1 window with the two control outcomes recorded; amendment draft filed for ratification."
        },
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-PROF-ATTR-1",
          "task_text": "- [ ] **AK-PROF-ATTR-1 — Add GPU-active-union and a cross-run-subtraction lint to the profile report (intake-2562#record).** `scripts/kernel_rnd/autokernel/profile_report.py` / `profile_context.py` report `kernel_wall_share` and overlap tables but no GPU-active union versus summed kernel time. Resin's skill states overlapping kernel work is not additive and \"Engine minus GPU timing is unattributed time ... do not subtract different profiler and benchmark runs\" (optimize-resin-performance SKILL.md). Do: emit summed duration, active-union and critical-path per trace, and reject a derived \"unattributed\" figure built from two runs. Controls: a synthetic overlapping-kernel trace (sum greater than union), the hash-bound rocprofv2 trace already replayed in this handoff (~L444), a two-run subtraction negative. Decision rule: union less than sum on the synthetic case, existing wall-share values unchanged on the replayed trace, negative rejected.",
          "acceptance": "Report fields and lint land with the three fixtures green; existing profile tests unchanged."
        }
      ]
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
      "review_basis": "re-priced on the GPU, the in-weights calculator still loses: chip tokens are serial (0.5-1 s per call, median 242 s per long division on an L4), text tokens cost twice the weight bytes, and accuracy only ties a tool call; operator confirmation requested.",
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-2",
          "task_text": "- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs.",
          "acceptance": "M1 receipt: per-kernel verdicts (ACCEPT/RACE/UNKNOWN) on v10 MMVQ+FA-vec at the frozen served-shape manifest with 0 RACE; a mutant table showing every RVP-RACE-1 MMVQ/FA mutant and both ISA-only mutants flagged; runtime per instance. M3 done when t0_provider emits a non-null race_detector_id for a sync-touching GPU candidate."
        }
      ]
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
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; ID-RI-ANCHOR-GATE carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
          "task_id": "ID-RI-ANCHOR-GATE",
          "task_text": "- [ ] **ID-RI-ANCHOR-GATE — Make quote re-find a gate the author cannot satisfy by assertion (fabricated citations) (intake-2563#record, intake-1377#record).** Today `.claude/skills/research-intake/scripts/validate_intake.py` (~L436-441) only checks `claim_anchors` is non-empty and `verified_by` is self-written, so a fabricated or cross-pasted quote (the 2026-07-25 CORE ablation, also pasted into intake-895) passes. Borrow Octopus's rule that a mark is recorded only by the runtime after a verifier passes the artifact and nothing else can emit it (`docs/contracts/VERIFIERS.md`, \"Nothing emits marks\"). Change SKILL.md Stage-2 \"Writes permitted\" (claim_anchors bullet) and the Stage-2 Verification Gate: add `validate_intake.py --check-anchors` that (a) re-finds every anchor `quote` in the retained source via `scripts/vidya/machine_anchor.py:verify_source_anchor` / `raw_anchor_store.py` (dive wrapper must write the source into `EPYC_VIDYA_RAW_ANCHOR_ROOT`, today opt-in and unused by dives), (b) recomputes `quote_sha256`, (c) writes an `anchor_mark: {verifier, source_raw_sha256, found}` that only the script writes, and (d) flags any `quote_sha256` appearing under two different entries (cross-paste, needs no retained source). New dive-verified entries without an anchor_mark fail; legacy entries stay grandfathered. Controls: four frozen fixtures (verbatim quote, fabricated quote, whitespace-altered quote, same quote under two entries) plus the old validator output; per-fixture expected verdict recorded. Decision rule: ship only if all four fixtures give the predeclared verdict and a replay over the current index flags zero verbatim anchors. Passing proves containment, not entailment; the per-claim second reader stays.",
          "acceptance": "Fixture suite in scripts/tests passes (4 verdicts as predeclared); `--check-anchors` run over the current index reports the count of unmarked legacy entries without failing them; SKILL.md Stage-2 gate text updated."
        }
      ]
    },
    "PRE-2566": {
      "required_outcome": "None: KB retrieval is ColBERT MaxSim; synthetic-only evidence.",
      "review_status": "closed-with-basis",
      "review_basis": "synthetic single-machine retrieval evidence, and KB retrieval uses ColBERT MaxSim, not cosine stores.",
      "task_refs": []
    },
    "W5FT-1": {
      "required_outcome": "Candidate (a), the 27B DFlash2 drafter (1.9B, GGUF-verified). Capture: 5 taps + final hidden = 61,440 B/token, only for completions plus their 2,048-token window (the drafter attends a 2,048 sliding window). ~0.8-1.2M tokens = 50-75 GB. Capture runs on the ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W5FT-2": {
      "required_outcome": "Candidate (c), the frontdoor Qwen3.6-35B-A3B MTP head (blk.40: 0.845B params, of which ~0.80B are 256x experts; hidden 2048; served from the same Q8_0 file at draft_max 4). Capture the trunk pre-head hidden at every position (4,096 B/token). It is both the ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W5FT-3": {
      "required_outcome": "Candidate (b), the Qwen3.8-Flash-Next MTP head (shared-Q8_0 file: 32 tensors, 2.607B params, of which 2.517B are 512x experts; attention with a QSA indexer, top_k 2048; 4-stream hyper-connections). Capture: the hc stream state at 10,240 x bf16 = 20,480 ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W5FT-4": {
      "required_outcome": "Settle KL versus hard labels on the real served drafter (arms H and K plus a second seed in DF2-FT-1), not on the Soft-MTP 167M toy. The toy result would not transfer: different module (non-causal block drafter with a selector), different vocabulary (50,304 ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W5FT-5": {
      "required_outcome": "Fold MTP-4 (realign a served finetune's stock head) into a standing onboarding rule. Any served drafter or MTP head not co-trained on the exact served trunk and quant gets frozen-trunk KL re-alignment on its own traffic. That covers fine-tunes (the ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W5FT-6": {
      "required_outcome": "Scope SPEC2-4 (Nemotron Sec 3.4 recipe). Hidden-state sampling over earlier draft steps applies to recursive MTP heads (frontdoor, Flash-Next), not to DFlash2, which drafts its whole block in one non-causal pass from the anchor. T=2 versus T=1 is a free extra ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; DF2-FT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
          "task_id": "DF2-FT-1",
          "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first).",
          "acceptance": "Committed report with the frozen manifest; the per-request JSONL for incumbent, round-trip, H, K and K-seed2 on all held-out C4 requests x 2 reps; DF2-4 results per arm; the converted candidate GGUF sha256s; the decision line (PROMOTE / one-more-shard / KILL plus the KL-vs-hard verdict) stated against the predeclared thresholds; and the DF2-DRAFTER-CAPABILITY amendment (objective verdict, onboarding rule, ordered next instances) applied by the owning session."
        }
      ]
    },
    "W5FOLD-1": {
      "required_outcome": "Fold #30408 non-causal ubatch fix as a cheap champion safety fix after a defect-reproducing control",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CH-33 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-33",
          "task_text": "- [ ] **CH-33 — Fold the non-causal multi-sequence ubatch fix (upstream #30408, cbe28bb3cb, +7/-7 over src/llama-batch.h, llama-context.cpp, llama-kv-cache.cpp, llama-kv-cache-iswa.cpp, llama-memory.h) into the champion as a safety fix (intake-2599#record, intake-2595#record).** Value: any bidirectional/embedding or decision model served at np>1 can currently have a request split across ubatches so answers change with the co-batched companions; the EmbeddingGemma 2 fold (REPL-EMB-2.6) and any d1 decision model are the consumers. Immediately (cheap, safety): fresh branch experimental/champion-c7-nonc-ubatch from the CURRENT champion tip, cherry-pick cbe28bb3cb, build CPU+HIP store images, gates: (a) non-causal batch-invariance, EmbeddingGemma 2 BF16 embeddings for one request alone vs co-batched at np 3 with shorter, longer and identical companions, unfixed C5 as the control (must reproduce the defect or the task records that no champion consumer is affected), fixed build must agree within 1e-3 cosine-distance of solo; (b) causal decode untouched: Q38FN and 27B DFlash2 greedy identity vs C5 on the fold_gate.py slice; (c) fold_gate.py expects libllama.so only. Rule: fold if (b) identical and (a) fixed or defect absent; manifest row V11 pending-to-in with ancestry presence gate.",
          "acceptance": "Branch, gate records and manifest row committed; guarded CAS only through the champion owner routine; fold_gate.py shows only libllama.so changed."
        }
      ]
    },
    "W5FOLD-3": {
      "required_outcome": "Track draft PR #29832 as the possible replacement base for the systemone fold when it merges",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CH-36 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-36",
          "task_text": "- [ ] **CH-36 — Decision-endpoint fold group: /v1/systemone (#29818, a4cb4c61fd, +2139/-15, 35 files, new server-decision.cpp 681 lines, server-context.cpp +210) and H2O-Lightning-4B (#30361, 7e3eeee048, +478/-15), depends on CH-33 and the LFM3 arch commits of CH-35 (intake-2593#record, intake-2582#record, intake-2602#record, intake-2601#record).** Value: gives TD-23 the missing local compact decision backend (d1-2B/3B, H2O-Lightning). Not for production fold until measured: the scratch build used by TD-23.D1 is the instrument. Gate for the fold: TD-23.D1 parity gate (BF16 vs Q8_0 on CPU and HIP, no argmax flip, probability difference not above 2.2e-2) and batch-invariance gate (np 1 vs np 3, 1e-3) both pass and d1-2B Q8_0 beats the constrained incumbent on the sealed row-pinned workload. If it passes: cut experimental/champion-plus-systemone from the current tip, resolve server-context.cpp by hand, add the np1 pin (hybrid-prefix re-read, issue 31475) to the launch recipe, gates as CH-35 plus TD-23.D1 rerun on the folded binary. Draft PR #29832 (model-agnostic systemone) merging upstream is the external event that would replace a4cb4c61fd as the base; until then the merged #29818 is used. #30100 is Metal-only and declined with that reason.",
          "acceptance": "TD-23.D1 gate results referenced; fold branch with gates or EXCLUDED row with numbers."
        }
      ]
    },
    "W5FOLD-4": {
      "required_outcome": "Real conflict and ggml-delta census before any audio-group cherry-pick",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; CH-32 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-champion-aggregate.md",
          "task_id": "CH-32",
          "task_text": "- [ ] **CH-32 — Upstream-delta fold census: dry-run merge of upstream tip into the champion C5 (c72ec82f5) to replace the PR line counts with real conflict and ggml-generation numbers (intake-2575#record, intake-2579#record, intake-2593#record, intake-2585#record, intake-2599#record).** Immediately, no compute: git fetch the upstream remote into the llama.cpp object store (no checkout, no branch move, production tree and champion ref untouched), then for each fold group (A cbe28bb3 non-causal ubatch; B b77d646751 Nanbeige4.2 plus Ouro #29823 head; C a4cb4c61fd + 7e3eeee048 systemone/H2O; D 30629, 30636, 31252, 31257, 31269, 31287, 31386, 31283 audio/LFM3/realtime) run git merge-tree --write-tree against c72ec82f5 and record per group files changed, conflicted hunks per file (expect tools/server/server-context.cpp, src/llama-context.cpp, src/llama-model.cpp), whether the group needs ggml ops or a ggml bump beyond v10 lineage (diff ggml/ include list), and the minimal prerequisite commit chain (b10303..b11960 is 1657 builds). Output table lands in docs/reference/kernel-manifests/llama-v11-manifest.md as pending-fold rows with a presence gate each (ancestry check), per README rule 4. Controls: frozen base sha, per-group raw merge-tree output kept, full group list, predeclared rule: a group with more than 3 conflicted files in server/ or any conflict in ggml-cpu, iqk or speculative code is cut by hand on a fresh experimental branch from C5 rather than cherry-picked in bulk.",
          "acceptance": "Table of 4 groups with conflicted-file counts, ggml delta yes/no and prerequisite chain committed as llama-v11-manifest.md pending-fold rows; raw merge-tree outputs under the scratch dir."
        }
      ]
    },
    "W5FOLD-2": {
      "required_outcome": "Decline #30100 (Metal MUL_MAT+ADD fusion) for the champion",
      "review_status": "closed-with-basis",
      "review_basis": "the fix touches only the Metal backend; no CPU or HIP code path in our stack changes.",
      "task_refs": []
    },
    "W5GPU-1": {
      "required_outcome": "Restate LOOP-1 with GPU arithmetic: loops multiply weight bytes, KV reads and FLOPs equally, so aggregate is about 1/L at every batch; batching removes only the weight term; MHA KV (768 KiB/token at 4 loops) makes Ouro-1.4B KV-bound beyond about 123 tokens of ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-1",
          "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1).",
          "acceptance": "Experimental branch + HIP/CPU build exist; parity receipt on gfx90a and CPU; the np x loops x ctx x KV grid with predictions and ratios is committed with raw JSON; the CPU leg and the GPU arithmetic table are filed; the 0.5-1.1x rule is applied to every cell."
        }
      ]
    },
    "W5GPU-2": {
      "required_outcome": "Per-request num_loops (setter, graph-param/can_reuse, k-class batch split, prefix-cache rule k2<=k, k_max cache sizing) with a router-oracle decision rule.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-3 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-LOOP-3",
          "task_text": "- [ ] **GPU-LOOP-3 — Loop count as a per-request serve-time effort switch in llama.cpp-experimental (intake-2585#record, intake-2586#record, intake-2547#record).** Today num_loops is a load-time GGUF key (PR #29823: --override-kv ouro.num_loops=int:N; PR #25994 expands hparams arrays to n_layer_phys*n_loops once in load_arch_hparams). Change set: (1) llama_context gains llama_set_n_loops(ctx,k), 1<=k<=file n_loops, carried in llm_graph_params and compared in can_reuse() so a changed k rebuilds the graph while graph_reserve still sizes the worst case; the builder loop bound becomes n_layer_phys*k and the LM-head tap is the shared final norm of loop k (the exit_at_step readout the HF code already has); about 150-250 lines. (2) server: parse n_loops or an effort alias (low/medium/high mapped by a GGUF key such as ouro.effort_loops) into slot params; update_slots splits the ubatch into one llama_decode per k-class (each class re-reads the weights, a cost that is small once np exceeds the weight/KV crossover of about 7 streams at C=1k); about 100-150 lines. (3) KV semantics, each point tested: a logical layer slot (loop j, layer i) holds KV only for sequences that ran loop j, so a prefix cached at k loops is valid for any request with k2<=k and invalid for k2>k (the deeper slots and the hidden states to recompute them are not stored), which makes the prompt-cache and ctx-checkpoint key carry n_loops_cached; a mid-request upgrade needs a re-prefill, a downgrade does not; cells are shared across layers, so a low-k request saves bandwidth and FLOPs but not VRAM unless the cache is sized with a k_max option (KV is 192 KiB per loop per token for Ouro-1.4B f16, 768 KiB at 4). (4) Validity gate: only checkpoints trained with per-loop supervision may expose the switch: Ouro yes (PR GSM8K F16 26.0/67.0/80.5 at 1/2/4), Nanbeige4.2 no (forced 1 loop is degenerate, 0.0 GSM8K), LoopCoder-v2 no (each R is a separately trained model, R=3 27.6 vs R=1 43.0 SWE-bench Verified). Acceptance tests: logits at per-request k on a file with n_loops=4 are bit-identical on CPU and within 1e-3 abs on HIP to a file loaded with num_loops=k, for k=1..4 on the 829-position fixture (this also verifies the claim that loop-j activations do not depend on the total loop count); four concurrent requests with k=1,2,3,4 reproduce their solo outputs; prefix-cache hit for k2<=k and miss for k2>k; throughput at np=16 with half k=1 and half k=4 within 0.8-1.2x of the byte-model prediction. Router oracle on the GPU-LOOP-2 per-item results: oracle minimum loops per item vs a no-oracle router (answer agreement between loops 2 and 4 on a calibration half, or the exit-gate probability); decision rule on the held-out half: PROMOTE the switch to a lane option if the router keeps at least 97% of the L=4 accuracy at mean loops at most 2.4 (cost at most 0.6x of L=4); else keep static L and record the oracle bound. Per-token adaptive exit is not offered: the PR does not convert the early_exit_gate and a batch graph saves nothing from it without row compaction.",
          "acceptance": "Patch on the experimental branch with the four acceptance tests green; oracle-vs-router table on held-out items; PROMOTE or keep-static decision recorded with the 0.6x / 97% rule."
        }
      ]
    },
    "W5GPU-3": {
      "required_outcome": "Looped small model as reliability-boosted GPU batch worker vs equal-cost dense and majority-of-4 controls, with the incumbent worker scored for the first time on the worker battery.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-LOOP-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-serving-tie-in-program.md",
          "task_id": "GPU-LOOP-2",
          "task_text": "- [ ] **GPU-LOOP-2 — Looped small model as a reliability-boosted batch worker on the MI210: quality vs loops vs aggregate throughput against equal-cost dense and K-sample controls (intake-2585#record, intake-2547#record, intake-2551#record).** Question: at high concurrency (elastic-duty D1 batch-shedding class, np 16), does Ouro-1.4B (and 2.6B-Thinking as second tier) at 1/2/4 loops buy more correct worker answers per HBM byte than a non-looped model? Arms, served-cost arithmetic at np=16, C=1k, f16 KV (ideal step times, to be measured in GPU-LOOP-1): A1 Ouro-1.4B L=4 (5.76 GB weights/step + 12.9 GB KV, 13.0 ms, 1,230 tok/s); A2 L=2 (about 2,300); A3 L=1 (about 7,100 on the same weights); A4 Ouro-2.6B-Thinking L=4 (48 layers, about 11.3 GB weights/step, 1.5 MiB/token KV); C1 Qwen3-4B-Thinking-2507 Q8 (4.28 GB, 144 KiB/token, 3,420 tok/s, the equal-quality-class dense control); C2 Qwen3-1.7B Q8 majority-of-4 (about the same bytes per final answer as A1, 1,545 answer-equivalent tok/s: the K-sample route that the idle MFMA headroom makes free); C3 Qwen3-1.7B Q8 single sample (equal resident bytes); C0 the incumbent worker, Qwen3.6-35B-A3B on CPU :8070 (registry roles.worker_general.performance.quality_pct is null: it has never been scored on the worker battery, so it is measured here on the same frozen items). Frozen inputs: GSM8K-style math (n>=200, same problem list as the PR so the 26.0/67.0/80.5 published curve is a replication check) plus worker-battery items for explore, summarize, transform and strict tool-call JSON (n>=150 per suite), item list and scorer hashed before any generation; Ouro context stays under its trained 1024-token block (Ouro RECIPES: block_size 1024), longer prompts are a separate reported stratum. Per arm: pass@1 over 3 seeds, seed-to-seed agreement, JSON-validity rate, aggregate tok/s at np 16, wall-seconds per correct answer and correct answers per HBM GB moved; per-item raw outputs kept; correctness legs may share the card with :8083, throughput legs run in a GPU window with the host threads under the q3 claim. Controls: frozen inputs, incumbent baseline (C0 and C1), per-item raw outputs, 3-seed repeat with the A/B order alternated, full denominator including parse failures, predeclared rule. Decision rule: an Ouro arm earns a shadow-lane tenancy row (D3 shadow-only, no production traffic) only if (i) its paired accuracy vs C1 is within 2 points (McNemar not worse) and its seconds per correct answer at np=16 is at most 1.5x C1, or (ii) it beats C1 by at least 5 points at paired p<0.05 at no more than 2.5x C1 cost; the arithmetic predicts A1 costs 2.8x C1 per token, so (i) needs a real quality edge. Otherwise record NO-GO with the table and keep Ouro only as the vehicle for GPU-LOOP-3. Depends on the GPU-LOOP-1 build (our own task, not an external event).",
          "acceptance": "Frozen item list + scorer hashes; per-arm table of accuracy, seed agreement, tok/s, seconds per correct answer and correct answers per GB; C0 worker-battery score recorded; the (i)/(ii) rule applied with paired statistics; GO tenancy row or NO-GO line committed."
        }
      ]
    },
    "W5GPU-4": {
      "required_outcome": "Replace the LoopCoder-v2 monitor with a transformers-custom-code quality screen on the MI210 (HE+, LCB, BCB, coder suite) against Qwen3.8-27B and the CPU frontdoor.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-PLT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-serving-tie-in-program.md",
          "task_id": "GPU-PLT-1",
          "task_text": "- [ ] **GPU-PLT-1 — LoopCoder-v2 (7.6B PLT coder, Apache-2.0) quality screen on the MI210 through transformers custom code, before and independent of the GGUF port (intake-2584#record, intake-2571#record).** Load Multilingual-Multimodal-NLP/LoopCoder-V2 at the pinned HF sha b87cf3a (BF16, 7,615,749,680 params, 15.2 GB, fits the about 19 GiB headroom beside :8083 without a KV problem) in an isolated venv with the transformers version its configuration_iquestpltcoder.py needs (Ouro needed 4.57.x, the research venv has 5.15.0: do not assume); confirm torch.version.hip and bf16 on gfx90a first; read config.json to see whether the loop count is a config field (the paper trains R=1..4 as separate models, so a forced R=1 on the released weights is not the paper R=1). Frozen inputs: HumanEval+ (164), LiveCodeBench subset released after the model cutoff (n>=200), BigCodeBench-hard subset, plus the frozen coder-suite items used for coder_escalation (cruxeval and the others E-7 scored: math 85.0, mmlu_pro 27.5, gpqa_diamond 47.5, cruxeval 22.5 at terse template 1443ea9ab4bb). Arms: LoopCoder-v2 as released; incumbent coder_escalation Qwen3.8-27B Q8 on :8083 (same harness, thinking off and medium); frontdoor Qwen3.6-35B-A3B on CPU; size control Qwen3-4B-Instruct-2507 (on disk). Controls: frozen items and scorer hashes, incumbent baselines, per-item raw outputs, 2 seeds, full denominator, rule below. Replication check against the paper own table: R=2 reports HE+ 84.1, LCB 35.4, BCB 46.1 and SWE-bench Verified 64.4 (harness unnamed, single seed, vendor-authored); accept the replication if HE+ >= 80 and the LCB subset score is within 5 points of the paper 35.4 after harness adjustment stated. Decision rule: open the serving legs of GPU-PLT-2 (agentic SWE-40 on the same scaffold that scored Qwen3.8-27B 21/40 = 52.5%, shadow lane only) if pooled pass@1 over HE+ and LCB is non-inferior to Qwen3.8-27B within 8 points (paired bootstrap lower bound) or the replication check passes; otherwise record NO-GO with the table (the port of GPU-PLT-2 still completes as parity work). Arithmetic that motivates it: at np=16, C=8k, Q8 (about 8.1 GB incl. head, KV 56 KiB/token f16 because later loops share loop-1 KV and keep only a 64-token window) a PLT-2 step is about 15.2 GB / 1433 GB/s = 10.6 ms bandwidth vs 2.5 ms compute at 32 rows, i.e. 1,510 tok/s ideal aggregate (about 600 derated by the 27B np8 ratio 157/400), vs 94 tok/s live at 4 concurrent on the 27B.",
          "acceptance": "Per-benchmark table with per-item outputs for all arms; replication verdict vs the paper numbers stated with harness differences; the non-inferiority rule applied and the GPU-PLT-2 serving legs opened or closed."
        }
      ]
    },
    "W5GPU-5": {
      "required_outcome": "Port PLT (CLP rows, shared loop-1 KV, 64-token gated window) as a new arch on llama.cpp-experimental with HF-parity and decode-step-ratio acceptance.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; GPU-PLT-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/gpu-acceleration-path.md",
          "task_id": "GPU-PLT-2",
          "task_text": "- [ ] **GPU-PLT-2 — Parallel-Loop-Transformer architecture (iquestpltcoder) on llama.cpp-experimental: port, parity, and MI210 decode curves (intake-2584#record, intake-2571#record).** Not blocked by the absence of upstream code; estimate 1.0-1.5 kLOC, 3-5 agent-days, 3-4x the 265/324-line Nanbeige/Ouro ports because those only unroll layers and carry no CLP, shared-KV or sliding window: converter for IQuestPLTCoderForCausalLM (about 150: 14 layers, hidden 5120, 40 heads / 8 KV, FFN 27648, R, window 64, per-head gate tensors; read the HF modeling file at sha b87cf3a first); arch/hparams/tensors (about 250); graph (about 400): a decode step builds R rows per sequence, row r input = token embedding + h^(r-1) of the previous position (per-sequence state of (R-1) x n_embd, held in the recurrent-memory path so checkpoint and spec-decode rollback come with it), row 1 attends the normal full KV, rows >=2 attend the shared loop-1 K/V through the existing cross-layer KV-reuse hparams plus a private 64-entry window cache (extra logical layers in the iSWA cache) and mix with the head-wise sigmoid gate; prefill runs R shifted sweeps over the prompt; cache/state plumbing and tests (about 400-700). Acceptance: top-1 logits match the HF reference on >=1000 positions and greedy continuations match on 20 prompts, on CPU and HIP; measured decode step ratio PLT-2 vs the same weights run as a one-loop graph is <=1.15 at np<=16 (prediction 1.02-1.05, since 2 rows per stream stay under the Q8 knee of 64 rows through 32 streams) and a sequential two-loop graph on the same weights is >=1.8 (the ByteDance paper reports 4.9 vs 4.8 vs 9.4 ms at bs 4 and 8.6 vs 8.1 vs 16.1 ms at bs 32 in its own stack); KV measured at about 56 KiB/token + window; spec-decode (MTP/DFlash2) rollback test using the state snapshot. Quality and serving verdicts are GPU-PLT-1 and the SWE-40 legs, not this task; this task delivers the engine.",
          "acceptance": "Branch with the arch + converter; parity receipt on CPU and HIP; decode-step ratio and KV measurements committed against the stated predictions; rollback test passes."
        }
      ]
    },
    "W5GPU-6": {
      "required_outcome": "LOOP-5 re-check on the GPU: at batch above E/top_k every expert is touched each pass, so a looped MoE at R=5 reads about R x its total expert bytes (1.3B total x 5 = 6.5 GB vs 2.9B x 1 = 2.9 GB for a quality of 46.9 vs 50.2 Overall); GPU does not reverse the ...",
      "review_status": "closed-with-basis",
      "review_basis": "no looped-MoE checkpoint or code is released; reopen on a weights release.",
      "task_refs": []
    },
    "W5GPU-7": {
      "required_outcome": "MEM-3 re-priced on the MI210 instead of the CPU: text tokens cost 18.7 GB / (1433 GB/s x 0.715 fp16 attainment) = 18 ms vs 9 ms for the 9.3 GB base (L4 check: 18.7/0.30 = 62 ms vs the 68 ms the author reports); chip tokens are serial and autoregressive, ...",
      "review_status": "closed-with-basis",
      "review_basis": "same GPU re-pricing as the calculator row; serial chip tokens dominate on any device.",
      "task_refs": []
    },
    "W5GPU-8": {
      "required_outcome": "LOOP-6 re-check: the monitor was never CPU-bandwidth based; the constraints are a per-dataset VQ tokenizer at about 100M-725M parameters with no served-vocabulary checkpoint, finest level (the first token) generated last, and no acceptance number against an ...",
      "review_status": "closed-with-basis",
      "review_basis": "no NCM checkpoint shares a served vocabulary and no acceptance number exists; reopen on such a release.",
      "task_refs": []
    },
    "W5GPU-9": {
      "required_outcome": "W2LOOP-3 re-check: GDN beta cap is a monitorability finding with no GPU lever; unchanged.",
      "review_status": "closed-with-basis",
      "review_basis": "a single-task, few-seed result with no performance lever on either device.",
      "task_refs": []
    },
    "W5VERIF-1": {
      "required_outcome": "Record the race/deadlock/equivalence coverage matrix per hot gfx90a kernel family (v10 code-object counts and source anchors in this file header) in rocm-verify-profile-backend.md beside RVP-RACE-2, so later scoping cites measured coverage, not the paper ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-2",
          "task_text": "- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs.",
          "acceptance": "M1 receipt: per-kernel verdicts (ACCEPT/RACE/UNKNOWN) on v10 MMVQ+FA-vec at the frozen served-shape manifest with 0 RACE; a mutant table showing every RVP-RACE-1 MMVQ/FA mutant and both ISA-only mutants flagged; runtime per instance. M3 done when t0_provider emits a non-null race_detector_id for a sync-touching GPU candidate."
        }
      ]
    },
    "W5VERIF-2": {
      "required_outcome": "Equivalence-port decision: decline for bit-level quant kernels on coverage (1116/1497 AK GPU experiment rows); a seeded sub-tolerance mutant probe decides the FA/GDN/mmvf subclass.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-EQV-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-EQV-1",
          "task_text": "- [ ] **RVP-EQV-1 — Decide the equivalence-checker port by measured miss rate, quant kernels declined on coverage (intake-2570#record, intake-2557#record).** Decision part 1, decline: no Volta-class equivalence for MMVQ, MMQ, quantize_q8_1 or dequant. They are bit-level (nibble unpack, rounding), which Volta does not cover (floats are reals, conversions are the identity), and they make up about 75% of AK GPU experiment rows (1116 of 1497). KERN-4 enumeration owns decode exactness. Decision part 2, a deciding probe for the real-valued subclass (FA-mma/FA-tile at parallel_blocks=1, GDN recurrence, mmvf float GEMV). In a llama.cpp-experimental worktree from the v10 tip, build 8 seeded sub-tolerance algebraic mutants: FA online-softmax rescale skipped only when the running max changes after the first KV tile; FA KV loop dropping the last KV column; FA-tile dropping one tail tile at a non-multiple context; GDN exp(g) decay dropped at a chunk boundary; GDN beta dropped for one head; mmvf dropping the final partial k-block at ne00 % tile != 0; and two controls with an O(1) error. Prove each mutant structurally (ISA diff of that kernel). Run the AK served-shape gate plus the AKX-ALL-31 edge families and the KERN-5 worst-element bound, 5 seeds each, on a frozen case manifest, keeping per-mutant per-seed raw verdicts and NMSE; the unmutated v10 build must pass 5/5 seeds. Decision rule: if any non-control mutant survives every gate on >=1 seed, open the equivalence milestone for that subclass on the RVP-RACE-2 interpreter (symbolic float values, v_exp_f32 as 2^x, cvt as identity, the 2 MFMA lane layouts in use, DPP/swizzle value moves, FA and GDN reference specs; estimate 4-6 kLoC, 4-6 engineer-weeks; advisory, never a speed-blocking gate, because intake-2555 Table 2 shows proof-restricted FA at 0.78x vs 1.37x). If all are caught, record the catch table and close the equivalence port with that table as the reason. Correctness-only, so no quiet host is needed.",
          "acceptance": "Catch table (mutant x gate x seed, with NMSE) committed with the 5/5 control; one of two outcomes recorded: an equivalence milestone opened with its named subclass, or the port closed with the table as its reason; the quant-kernel decline recorded with the 1116/1497 coverage count."
        }
      ]
    },
    "W5VERIF-3": {
      "required_outcome": "Fix the RVP-RACE-1 decision rule (>=1 of 20 passes is a miss, not all 20), add waves-per-WG and ISA s_barrier-delta controls, add the LDS-DMA site, and make its mutants RVP-RACE-2 fixtures rather than its trigger.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-1",
          "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.",
          "acceptance": "Per-mutant table (site, s_barrier delta, waves/WG, pass count out of 20, max NMSE) plus the 20/20 control, committed with raw verdicts; TSAN anchor report with suppression list; fixtures handed to RVP-RACE-2."
        }
      ]
    },
    "W5VERIF-4": {
      "required_outcome": "Level choice for the gfx90a checker is AMDGCN ISA from the built code object, not LLVM IR or HIP source: IR lacks waitcnts and the inline-asm semantics the AMD hot paths rely on, and cannot see ISA-edited (C5-ISA-2) candidates.",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; RVP-RACE-2 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-verify-profile-backend.md",
          "task_id": "RVP-RACE-2",
          "task_text": "- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs.",
          "acceptance": "M1 receipt: per-kernel verdicts (ACCEPT/RACE/UNKNOWN) on v10 MMVQ+FA-vec at the frozen served-shape manifest with 0 RACE; a mutant table showing every RVP-RACE-1 MMVQ/FA mutant and both ISA-only mutants flagged; runtime per instance. M3 done when t0_provider emits a non-null race_detector_id for a sync-touching GPU candidate."
        }
      ]
    },
    "W5META-1": {
      "required_outcome": "Anchor mark written only by a script, plus cross-paste check, for fabricated citations",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; ID-RI-ANCHOR-GATE carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
          "task_id": "ID-RI-ANCHOR-GATE",
          "task_text": "- [ ] **ID-RI-ANCHOR-GATE — Make quote re-find a gate the author cannot satisfy by assertion (fabricated citations) (intake-2563#record, intake-1377#record).** Today `.claude/skills/research-intake/scripts/validate_intake.py` (~L436-441) only checks `claim_anchors` is non-empty and `verified_by` is self-written, so a fabricated or cross-pasted quote (the 2026-07-25 CORE ablation, also pasted into intake-895) passes. Borrow Octopus's rule that a mark is recorded only by the runtime after a verifier passes the artifact and nothing else can emit it (`docs/contracts/VERIFIERS.md`, \"Nothing emits marks\"). Change SKILL.md Stage-2 \"Writes permitted\" (claim_anchors bullet) and the Stage-2 Verification Gate: add `validate_intake.py --check-anchors` that (a) re-finds every anchor `quote` in the retained source via `scripts/vidya/machine_anchor.py:verify_source_anchor` / `raw_anchor_store.py` (dive wrapper must write the source into `EPYC_VIDYA_RAW_ANCHOR_ROOT`, today opt-in and unused by dives), (b) recomputes `quote_sha256`, (c) writes an `anchor_mark: {verifier, source_raw_sha256, found}` that only the script writes, and (d) flags any `quote_sha256` appearing under two different entries (cross-paste, needs no retained source). New dive-verified entries without an anchor_mark fail; legacy entries stay grandfathered. Controls: four frozen fixtures (verbatim quote, fabricated quote, whitespace-altered quote, same quote under two entries) plus the old validator output; per-fixture expected verdict recorded. Decision rule: ship only if all four fixtures give the predeclared verdict and a replay over the current index flags zero verbatim anchors. Passing proves containment, not entailment; the per-claim second reader stays.",
          "acceptance": "Fixture suite in scripts/tests passes (4 verdicts as predeclared); `--check-anchors` run over the current index reports the count of unmarked legacy entries without failing them; SKILL.md Stage-2 gate text updated."
        }
      ]
    },
    "W5META-2": {
      "required_outcome": "Pin lane revision per citation and emit stale_epoch for changed files, for stale clones",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; ID-RI-LANE-HEAD carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
          "task_id": "ID-RI-LANE-HEAD",
          "task_text": "- [ ] **ID-RI-LANE-HEAD — Pin the repo revision every in-house citation was read at and refuse stale ones mechanically (stale clones) (intake-2563#record).** SKILL.md L391-405 forbids the shared clone in prose only (2026-09-14 dives read /workspace @d372c953). Octopus pins descriptor hashes in every formed grant and refuses a movement against a changed checkpoint with a typed `stale_epoch` (`docs/contracts/LEDGER_INDEX.md`). Change: (1) Stage-2 dive brief template requires `lane_head` (full SHA of the lane worktree) in the returned YAML, and a `dive_preflight.py` run by main before dispatch asserts the named root is the lane worktree and its HEAD is not behind origin/main; (2) in-house `claim_anchors` locators `path:Lx-Ly @ sha7` get validated by `validate_intake.py --check-lane-anchors`: `git show sha7:path` must contain the quote, and `git diff --name-only sha7..origin/main -- path` non-empty emits typed `stale_epoch` that blocks Stage-3 plan citation of that anchor until re-read. Controls: replay the 2026-09-14 incident (anchor at d372c953 for a file since changed), a moved path, an unchanged path. Decision rule: stale_epoch fires on the first two and not the third; zero false positives over the current in-house anchors.",
          "acceptance": "dive_preflight.py and --check-lane-anchors exist with the three replay fixtures passing; SKILL.md brief section references them."
        }
      ]
    },
    "W5META-3": {
      "required_outcome": "Script-formed stage write grant checked by main, replacing self-reported audit lines",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; ID-RI-STAGE-GUARD carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
          "task_id": "ID-RI-STAGE-GUARD",
          "task_text": "- [ ] **ID-RI-STAGE-GUARD — Compute the stage write grant by script and check the diff outside the agent (stage-gate violations) (intake-2563#record).** The skill's \"May write\" table (SKILL.md L50-58) and the Stage 1/2 gate \"`git status handoffs/` clean\" are prose run by the same agent that might violate them (2026-07-25: handoffs edited after an operator \"you can edit\"), and the dive `artifact_audit: clean` line is self-reported. Octopus forms the effective grant by a deterministic script at every arrival (ceiling intersect chain intersect bindings), enforces it outside the model and records a typed refusal row (`docs/architecture.md`, \"How policy is formed\"). Change: add `scripts/stage_grant.py form --stage N` (allowed paths: S1 index+.research-session.json; S2 index; S3 plan file; S4 the paths named by the approved plan, bound to `stage3_filing.plan_sha256` already checked at validate_intake.py ~L1084) and `check`, run by main at each stage boundary on `git status --porcelain` plus a tree hash taken at stage entry; violations append a typed row to the session JSON (`stage_write_outside_grant`, `plan_hash_stale`). Controls: replay the 2026-07-25 handoff-edit-in-Stage-2 case, a Stage-4 write outside the plan, and a clean stage. Decision rule: both violations refused, clean stage passes, no change to legacy validate_intake output.",
          "acceptance": "stage_grant.py with 3 fixture tests green; SKILL.md Verification Gates cite it instead of the manual git-status line."
        }
      ]
    },
    "W5META-4": {
      "required_outcome": "Closed decline-reason vocabulary so no actionable is closed by a free-text reason",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; ID-RI-DECLINE-VOCAB carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
          "task_id": "ID-RI-DECLINE-VOCAB",
          "task_text": "- [ ] **ID-RI-DECLINE-VOCAB — Replace free-text decline reasons with a closed vocabulary (dropped actionables, operator Act-Do-Not-Defer rule) (intake-2563#record).** `validate_intake.py` ~L1132 accepts any `decline: <text>`, so \"vendor-only\", \"upstream has not done it\" or \"not applicable\" can close a row (the rules SKILL.md L40-48 forbid). Octopus refusals are typed rows from a closed set, \"never a silent drop\" (`docs/contracts/LEDGER_INDEX.md`). Change: a decline/closed-with-basis terminal must start with a code from {duplicate:<exact id>, superseded:<successor id>, measured-loss:<evidence ref>, math-constraint:<one-line proof>, external-event:<named event>, operator-ruled:<ruling ref>}; the validator rejects other prefixes and the forbidden phrases, and `external-event` requires a name that is not \"upstream\". Controls: freeze the current plan's decline rows as a fixture (expected: each maps to a code or is flagged for re-open), plus three negative fixtures (vendor-only, upstream-absent, not-applicable). Decision rule: negatives rejected, all legacy plans still pass under the unchanged legacy mode.",
          "acceptance": "Validator rejects the three negative fixtures; opt-in flag keeps legacy plans valid; SKILL.md decline rules reference the code list."
        }
      ]
    },
    "W5META-5": {
      "required_outcome": "Typed capability interfaces for dive subagents",
      "review_status": "closed-with-basis",
      "review_basis": "the dive return schema plus the per-claim second reader already give typed, checked outputs.",
      "task_refs": []
    },
    "W5META-6": {
      "required_outcome": "Durable append-only run records",
      "review_status": "closed-with-basis",
      "review_basis": "session resume already exists in the skill and the plan checkpoint carries the durable record.",
      "task_refs": []
    },
    "W5META-7": {
      "required_outcome": "Policy-gated self-modification of the skill",
      "review_status": "closed-with-basis",
      "review_basis": "Octopus gates on path coverage only and itself says on-contract behaviour is not proven, so it adds nothing to plan review.",
      "task_refs": []
    },
    "W5META-8": {
      "required_outcome": "Unverified ids",
      "review_status": "closed-with-basis",
      "review_basis": "the intake id resolver and the vidya citation gate already catch dangling ids.",
      "task_refs": []
    },
    "W5META-9": {
      "required_outcome": "In-window path/compile counters missing from Annex K record grammar",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AK-WIN-CNT-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-WIN-CNT-1",
          "task_text": "- [ ] **AK-WIN-CNT-1 — Record in-window path counters beside every T1/T2 timing record (intake-2562#record).** Annex K's record grammar (`measurement/protocols/kernel-research.md` \"Record grammar\") has no field proving the timed window ran the intended path; T0 checks a dispatch trace but T1/T2 do not re-prove it. Resin keeps `graph_counts` and `overlap_counts` that exclude warmup and checks no JIT compile after warmup for unseen shapes. Do: capture hipGraph replay count vs eager launches and code-object load/JIT events inside the timed window on MI210 (use an in-process counter in a llama.cpp-experimental branch if none exists; the port is the build cost), write them as a non-gating diagnostic sidecar next to the raw samples, and draft the Annex K grammar amendment (human-amendment-only) making a path mismatch a VOID window. Controls: frozen anchor and one candidate, degraded-negative with graphs disabled (counter must show zero replays), A/A, per-window raw counters kept. Decision rule: sidecar ships if the degraded-negative is flagged and A/A is not; amendment text goes to the operator package.",
          "acceptance": "Sidecar present on a GPU T1 window with the two control outcomes recorded; amendment draft filed for ratification."
        }
      ]
    },
    "W5META-10": {
      "required_outcome": "Summed vs active-union vs critical-path attribution and no cross-run subtraction",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AK-PROF-ATTR-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-PROF-ATTR-1",
          "task_text": "- [ ] **AK-PROF-ATTR-1 — Add GPU-active-union and a cross-run-subtraction lint to the profile report (intake-2562#record).** `scripts/kernel_rnd/autokernel/profile_report.py` / `profile_context.py` report `kernel_wall_share` and overlap tables but no GPU-active union versus summed kernel time. Resin's skill states overlapping kernel work is not additive and \"Engine minus GPU timing is unattributed time ... do not subtract different profiler and benchmark runs\" (optimize-resin-performance SKILL.md). Do: emit summed duration, active-union and critical-path per trace, and reject a derived \"unattributed\" figure built from two runs. Controls: a synthetic overlapping-kernel trace (sum greater than union), the hash-bound rocprofv2 trace already replayed in this handoff (~L444), a two-run subtraction negative. Decision rule: union less than sum on the synthetic case, existing wall-share values unchanged on the replayed trace, negative rejected.",
          "acceptance": "Report fields and lint land with the three fixtures green; existing profile tests unchanged."
        }
      ]
    },
    "W5META-11": {
      "required_outcome": "Resin vs Annex K / AK loop (Resin cite = docs/benchmarks.md, optimize-resin-performance SKILL.md; ours = measurement/protocols/kernel-research.md, bench-cpu.md, gpu-cross-device.md) / noise floor: Resin none (qualitative 'show the spread') vs ours A/A p95 phi ...",
      "review_status": "preserved",
      "review_basis": "Main read the dive passage and the current consumer; AK-WIN-CNT-1, AK-PROF-ATTR-1 carry the required behavior with controls and a decision rule.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-WIN-CNT-1",
          "task_text": "- [ ] **AK-WIN-CNT-1 — Record in-window path counters beside every T1/T2 timing record (intake-2562#record).** Annex K's record grammar (`measurement/protocols/kernel-research.md` \"Record grammar\") has no field proving the timed window ran the intended path; T0 checks a dispatch trace but T1/T2 do not re-prove it. Resin keeps `graph_counts` and `overlap_counts` that exclude warmup and checks no JIT compile after warmup for unseen shapes. Do: capture hipGraph replay count vs eager launches and code-object load/JIT events inside the timed window on MI210 (use an in-process counter in a llama.cpp-experimental branch if none exists; the port is the build cost), write them as a non-gating diagnostic sidecar next to the raw samples, and draft the Annex K grammar amendment (human-amendment-only) making a path mismatch a VOID window. Controls: frozen anchor and one candidate, degraded-negative with graphs disabled (counter must show zero replays), A/A, per-window raw counters kept. Decision rule: sidecar ships if the degraded-negative is flagged and A/A is not; amendment text goes to the operator package.",
          "acceptance": "Sidecar present on a GPU T1 window with the two control outcomes recorded; amendment draft filed for ratification."
        },
        {
          "owner": "handoffs/active/autokernel-research-loop.md",
          "task_id": "AK-PROF-ATTR-1",
          "task_text": "- [ ] **AK-PROF-ATTR-1 — Add GPU-active-union and a cross-run-subtraction lint to the profile report (intake-2562#record).** `scripts/kernel_rnd/autokernel/profile_report.py` / `profile_context.py` report `kernel_wall_share` and overlap tables but no GPU-active union versus summed kernel time. Resin's skill states overlapping kernel work is not additive and \"Engine minus GPU timing is unattributed time ... do not subtract different profiler and benchmark runs\" (optimize-resin-performance SKILL.md). Do: emit summed duration, active-union and critical-path per trace, and reject a derived \"unattributed\" figure built from two runs. Controls: a synthetic overlapping-kernel trace (sum greater than union), the hash-bound rocprofv2 trace already replayed in this handoff (~L444), a two-run subtraction negative. Decision rule: union less than sum on the synthetic case, existing wall-share values unchanged on the replayed trace, negative rejected.",
          "acceptance": "Report fields and lint land with the three fixtures green; existing profile tests unchanged."
        }
      ]
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
    },
    {
      "owner": "handoffs/active/architect-model-selection-bench.md",
      "task_text": "- [ ] **AMS-TCAP-1 — A/B a thinking-on effort mode for architect_general with ThinkingCap-Qwen3.8-Flash-Next (intake-2567#record, intake-2572#record, intake-2577#record).** Thinking is off for every Flash-Next role today because the base model fell into degenerate think loops (this handoff, prep finding 4; registry reasoning_policy_observation: reasoning auto gave 0/4 final answers). A finetune that shortens thinking is therefore a candidate higher-effort mode, not a curiosity. Download the bottlecapai ThinkingCap IQ4_XS GGUF (95.5 GB; one download at a time, disk checked first) and run three arms on llama-server with the qwen38-flash-next-cpu-mtp recipe: A base UD-IQ4_XS thinking off (production), B base thinking on, C ThinkingCap thinking on, plus C2 = ThinkingCap trunk with our shared-Q8_0 MTP head versus its embedded head. Frozen 40-60 prompt set (architect planning and critique, AIME-style reasoning, about 15 tau2-style agentic turns), at least 4 seeds, paired by prompt; record accuracy, thinking and answer tokens, the degenerate-loop and truncation rate, MTP alpha, and llama-bench pp/tg in one alternating window. Decision rule: propose a thinking-on effort mode (an operator-signed stack change) only if arm C beats arm A on the reasoning family with a paired 95% lower bound above 0, has degenerate or truncated thinking on at most 1% of requests, uses at most 60% of arm B's median thinking tokens, and keeps alpha within 0.03 of base; otherwise record the null and keep thinking off."
    },
    {
      "owner": "handoffs/active/autokernel-rebuild-program.md",
      "task_text": "- [ ] **AK-FAILRULE-1 — Turn recurring AK rejection reasons into pre-GPU rules from existing records (intake-2589#record, intake-2588#record).** Zero inference: classify every rejected candidate in the existing CPU and GPU campaign stores by failure reason (compile, correctness gate and which gate, timing loss, noise, harness error). For each reason class with at least 3 occurrences, draft a cheap static or pre-GPU check (CAKE-style hazard filter) and replay it over the historical candidates. Adopt a rule only if it would have rejected at least one historical failure before GPU time and no historical keep."
    },
    {
      "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
      "task_text": "- [ ] **DF2-FT-1 — KL re-alignment pilot of the served 27B DFlash2 drafter on its own agentic traffic, target frozen (intake-2548#04, intake-2549#record, intake-2578#record, intake-297#record, intake-1848#record).** Why: at the production :8083 shape the drafter accepts 0.29-0.39 on real temp-1 agentic traffic (agentic-serving-harness-fixes.md:60,74,79). On the canonical benchmark shape it accepts 0.62-0.73. The two shapes differ in several factors, so this pilot is the deciding probe, not a presumed fix. Drafter facts (GGUF header): Qwen3.8-27B-DFlash2-Q8_0, size_label 1.9B, 81 tensors, 5 non-causal blocks with sliding window 2048, fc 25600->5120, selector codebooks 2 x 256 x 248320. It is headless and borrows the target's frozen token_embd and output (5120 x 248320 each). Steps: (0) Corpus = the DS41-C95 wire contexts under /mnt/raid0/llm/tmp/ds41-c95/results (36 wire-body captures; DF2-14 counted 320 turns / 630k generated tokens). Hold out every C4 run untouched. For each held-in request, regenerate 2 completions at the production sampler on the :8083 argv (X0_ARGV_8083.txt), capped at 2048 tokens, <=3 MI210-h; this also removes the need to reconstruct reasoning text from the wire bodies. (1) Write a feature-dump tool on a llama.cpp-experimental branch cut from the current champion tip. Per token it writes the 5 taps at target_layers [6,20,34,48,62] plus the target final post-norm hidden: 5 x 10,240 + 10,240 = 61,440 B/token, the DF2-DRAFTER-CAPABILITY.OBJ contract. It writes only each completion and its 2,048-token window prefix. Expect ~0.8-1.2M tokens = 50-75 GB in <=2 rolling shards. Capture held-out C4 the same way for the offline proxy. Prefill runs at the measured production-shape 410-574 t/s, <=3 MI210-h. (2) Train in a NEW ROCm venv; do not modify the two verified venvs. Use NeMo Automodel train_dflash2 @1667095 with the sdpa attention backend and an offline-feature dataset in place of the online target. Warm-start from z-lab/Qwen3.8-27B-DFlash2 bf16. The whole drafter is trainable: bf16 weights + fp32 master + AdamW ~16 B/param = ~31 GB, plus frozen embed/output 5.1 GB; that fits 64 GB because target features are precomputed. Arm H = Automodel hard block CE on the sampled tokens. Arm K = forward KL at T=1 to the teacher, computed from the final-hidden tap through the frozen output_norm + W with Automodel KDLoss (as in jetspec_core.py), chunked; its selector term is KL over the top-16 candidates, renormalized. Both arms share data order, seed, steps and LR; add a second seed for K; <=4 MI210-h total. (3) Convert with convert_hf_to_gguf.py (DFlash2DraftModel, --target-model-dir /mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw for config and tokenizer), then quantize to Q8_0. Six controls: (i) frozen manifest: sha256 of the target, served drafter and z-lab bf16; champion binary identity; held-out request list; sampler; seeds. (ii) Baselines: the served drafter, plus a round-trip arm (z-lab bf16 through our converter and quantizer, untrained) that must be tensor-equal after dequant or within the A/A band on DF2-4. (iii) Per-request raw draft_n, draft_n_accepted, predicted_n and timings in JSONL, plus the offline teacher-forced expected-accept-length proxy per held-out block. (iv) Holdout: all C4 runs, replayed twice ABAB on a fresh server per arm at the production argv, plus the DF2-4 12-prompt benchmark per arm. (v) Full denominator: every held-out request, failures counted. (vi) Predeclared rule. PROMOTE (open DF2-FT-2) if the best arm beats the incumbent on held-out weighted acceptance (sum accepted / sum drafted) by >=0.05 absolute on both reps (about +10% tokens per verify step at n_max 7), AND on held-out decode tok/s by >=8%, AND DF2-4 acceptance is >= incumbent - 0.02, AND the coherence gate is clean with the DF2-6 greedy pass count not below the incumbent. KL becomes the default drafter objective if K - H >= 0.02 on both reps and the seed-2 replicate has the same sign; |K - H| < 0.01 means cost-neutral (pick hard labels, which need no final-hidden tap). A gain of +0.02..+0.05 earns one more shard of <=1M fresh resamples, a retrain, and one more application of the rule. Below +0.02, KILL and record. Final step, on any verdict: amend DF2-DRAFTER-CAPABILITY with the objective verdict and an onboarding rule. The rule makes frozen-trunk re-alignment on the model's own served traffic the default for any served drafter or MTP head not co-trained on that exact trunk and quant. It names the next instances: the frontdoor 35B-A3B MTP head, then the Flash-Next head. Budget: ~13 MI210-h (~0.55 card-day) in GPU windows booked through the backlog-scheduling calendar, with :8083 drained per preempt-by-drain, plus 4-6 desk days (dump tool, trainer adaptation, venv; CPU-only smoke first)."
    },
    {
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "task_text": "- [ ] **CH-32 — Upstream-delta fold census: dry-run merge of upstream tip into the champion C5 (c72ec82f5) to replace the PR line counts with real conflict and ggml-generation numbers (intake-2575#record, intake-2579#record, intake-2593#record, intake-2585#record, intake-2599#record).** Immediately, no compute: git fetch the upstream remote into the llama.cpp object store (no checkout, no branch move, production tree and champion ref untouched), then for each fold group (A cbe28bb3 non-causal ubatch; B b77d646751 Nanbeige4.2 plus Ouro #29823 head; C a4cb4c61fd + 7e3eeee048 systemone/H2O; D 30629, 30636, 31252, 31257, 31269, 31287, 31386, 31283 audio/LFM3/realtime) run git merge-tree --write-tree against c72ec82f5 and record per group files changed, conflicted hunks per file (expect tools/server/server-context.cpp, src/llama-context.cpp, src/llama-model.cpp), whether the group needs ggml ops or a ggml bump beyond v10 lineage (diff ggml/ include list), and the minimal prerequisite commit chain (b10303..b11960 is 1657 builds). Output table lands in docs/reference/kernel-manifests/llama-v11-manifest.md as pending-fold rows with a presence gate each (ancestry check), per README rule 4. Controls: frozen base sha, per-group raw merge-tree output kept, full group list, predeclared rule: a group with more than 3 conflicted files in server/ or any conflict in ggml-cpu, iqk or speculative code is cut by hand on a fresh experimental branch from C5 rather than cherry-picked in bulk."
    },
    {
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "task_text": "- [ ] **CH-33 — Fold the non-causal multi-sequence ubatch fix (upstream #30408, cbe28bb3cb, +7/-7 over src/llama-batch.h, llama-context.cpp, llama-kv-cache.cpp, llama-kv-cache-iswa.cpp, llama-memory.h) into the champion as a safety fix (intake-2599#record, intake-2595#record).** Value: any bidirectional/embedding or decision model served at np>1 can currently have a request split across ubatches so answers change with the co-batched companions; the EmbeddingGemma 2 fold (REPL-EMB-2.6) and any d1 decision model are the consumers. Immediately (cheap, safety): fresh branch experimental/champion-c7-nonc-ubatch from the CURRENT champion tip, cherry-pick cbe28bb3cb, build CPU+HIP store images, gates: (a) non-causal batch-invariance, EmbeddingGemma 2 BF16 embeddings for one request alone vs co-batched at np 3 with shorter, longer and identical companions, unfixed C5 as the control (must reproduce the defect or the task records that no champion consumer is affected), fixed build must agree within 1e-3 cosine-distance of solo; (b) causal decode untouched: Q38FN and 27B DFlash2 greedy identity vs C5 on the fold_gate.py slice; (c) fold_gate.py expects libllama.so only. Rule: fold if (b) identical and (a) fixed or defect absent; manifest row V11 pending-to-in with ancestry presence gate."
    },
    {
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "task_text": "- [ ] **CH-34 — Looped-model support fold group: Nanbeige4.2 (#25994 merged, b77d646751, +265/-1, 10 files incl. new src/models/nanbeige.cpp) plus Ouro (#29823, open, ~324 added lines, head sha to be pinned from the CH-32 fetch) (intake-2586#record, intake-2585#record, intake-2547#record).** Value: unblocks the looped-probe lane (GPU-LOOP-1: tg at ouro.num_loops 1/2/4, GB/s per effective token on EPYC; HIP run on MI210) without a hand port; files are disjoint from AK kernels, iqk and DFlash2 so expected cost is low. Immediately cut branch experimental/champion-plus-looped-arch from the current champion tip (fresh-tip rule), cherry-pick both, build CPU plus HIP store images, gates: test-llama-archs and the new-arch smoke load, no-regression greedy identity on Q38FN and one dense model vs champion, linkage proof. Fold decision is gated on the GPU-LOOP-1 probe: fold into the champion if Ouro-1.4B or Nanbeige4.2 runs coherent and the probe is not rejected on the predeclared tok/s-per-quality rule; otherwise keep the branch as the probe instrument and record the exclusion reason in the manifest. Open PR is not a block: the branch carries our own cherry-pick and is rebased when the PR merges."
    },
    {
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "task_text": "- [ ] **CH-35 — Speech/omni fold group: mtmd_audio_stream + Voxtral realtime (#30629, 2851b3bcbf, +998/-20, 27 files in tools/mtmd), realtime transcription API (#30636, 1242be66f6, +512/-14, 9 files, server-context.cpp +316), LFM3 arch (#31252), LFM3 audio+omni (#31257, +2721/-160, 31 files), /v1/realtime conversation (#31269, +1423) with tool calls (#31287), codec quant (#31386), video (#31283) (intake-2575#record, intake-2579#record, intake-2580#record, intake-2552#record).** Value: serves LFM3-Audio/Omni and Voxtral Realtime end to end from the champion server for CS-8 STT/interlocutor arms and CS-20/CS-22 realtime; the speech kernels (whisper.cpp, qwentts.cpp) are separate trees and unaffected. Cost: the biggest group; conflicts concentrated in tools/server/server-context.cpp (champion already +593 vs v10) and src/llama-model.cpp; mtmd is new surface the champion has not touched; ggml delta from CH-32. Stage 1 immediately: build the scratch upstream audio build of CS-8.STT8 (instrument, not the fold). Stage 2 gated on CS-8.STT8 (paired bootstrap WER not above +1.0 pp vs whisper in en and it) or CS-8.RT1 (realtime first-output latency beats the cascade on the 20 frozen utterances): then cut experimental/champion-plus-lfm3-audio from the current champion tip, apply the PR chain in merge order, resolve server-context.cpp by hand, rebuild CPU+HIP, gates: Q38FN/27B greedy identity vs champion (server changes must not move text decode), CS-8.STT8 WER reproduced on the folded binary within bootstrap CI of the scratch build, np>1 safety rerun of DF2-12.1. If STT8 and RT1 both fail the rule the group is recorded EXCLUDED with numbers."
    },
    {
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "task_text": "- [ ] **CH-36 — Decision-endpoint fold group: /v1/systemone (#29818, a4cb4c61fd, +2139/-15, 35 files, new server-decision.cpp 681 lines, server-context.cpp +210) and H2O-Lightning-4B (#30361, 7e3eeee048, +478/-15), depends on CH-33 and the LFM3 arch commits of CH-35 (intake-2593#record, intake-2582#record, intake-2602#record, intake-2601#record).** Value: gives TD-23 the missing local compact decision backend (d1-2B/3B, H2O-Lightning). Not for production fold until measured: the scratch build used by TD-23.D1 is the instrument. Gate for the fold: TD-23.D1 parity gate (BF16 vs Q8_0 on CPU and HIP, no argmax flip, probability difference not above 2.2e-2) and batch-invariance gate (np 1 vs np 3, 1e-3) both pass and d1-2B Q8_0 beats the constrained incumbent on the sealed row-pinned workload. If it passes: cut experimental/champion-plus-systemone from the current tip, resolve server-context.cpp by hand, add the np1 pin (hybrid-prefix re-read, issue 31475) to the launch recipe, gates as CH-35 plus TD-23.D1 rerun on the folded binary. Draft PR #29832 (model-agnostic systemone) merging upstream is the external event that would replace a4cb4c61fd as the base; until then the merged #29818 is used. #30100 is Metal-only and declined with that reason."
    },
    {
      "owner": "handoffs/active/autokernel-champion-aggregate.md",
      "task_text": "- [ ] **CH-37 — Recurrent-state / np>1 slot-contamination fix fold, gated on DF2-12.1 (intake-2597#record, intake-2598#record, intake-2591#record).** Already in the champion: #28123 rollback port 0771238438 (ancestor of C5 and C6 verified read-only). Open exposure: issues 26695 (seq_rm true without recurrent-state restore) and 28019 (multi-seq split replay corrupts rs when rollback enabled) plus the CH-31-DEF1 batched-decode divergence. Immediately: confirm by reading src/llama-memory-recurrent.cpp on C5 whether the 26695 and 28019 fix commits (find them with git log --grep on the fetched upstream) are ancestors; record the answer in the manifest. If DF2-12.1 (temp-0 cross-slot token identity at np 4 on :8083 and :8070 shapes) shows any divergence, this task becomes the fix: cherry-pick the upstream fixes onto a fresh branch from the champion tip, rerun DF2-12.1 as the gate (zero divergent tokens over the frozen set versus np 1) plus Q38FN greedy identity. If DF2-12.1 is clean, the manifest row records the ancestry check and the task closes."
    },
    {
      "owner": "handoffs/active/gpu-acceleration-path.md",
      "task_text": "- [ ] **GPU-LOOP-1 — Looped-architecture build on llama.cpp-experimental (Nanbeige #25994 + Ouro #29823) and its MI210 + CPU roofline curves (intake-2585#record, intake-2586#record, intake-2547#record, intake-2571#record).** Cut a fresh llama.cpp-experimental branch from the production v10 tip (ffc1bac82), cherry #25994 (merged b77d646, 265 lines) then #29823 (open, head e79d8cab5, 324 lines) with no other change; build HIP gfx90a and CPU; convert ByteDance Ouro-1.4B and 2.6B (+Thinking) to GGUF Q8_0 and Q4_K_M and record sha256. Gate 1 (correctness, may share the card with :8083): tests/test-llama-archs passes for ouro and nanbeige on CPU and HIP, and top-1 logit parity vs the transformers reference on the PR 829-position fixture at loops 1/2/4 is reproduced on gfx90a (use -ngl 999: -ngl counts logical layers, 192 for 2.6B, and -ngl 99 spilled to 1.6 tok/s in the PR thread). Gate 2 (timing, in a GPU window, host threads on 184-191 under the q3 claim): llama-batched-bench tg at loops {1,2,4} x np {1,2,4,8,16,32} x ctx {512,1024,2048} x KV {f16,q8_0} for Ouro-1.4B Q8_0, with Qwen3-1.7B-Q8_0 and Qwen3-4B-Thinking-2507-Q8_0 (both on disk) as same-build dense comparators; per cell report aggregate tok/s, achieved GB/s under the byte model bytes/step = W_body*L + W_head + B*C*kv_per_slot*L against the 1433 GB/s measured roof, and the ratio to the ideal step time. Same build, CPU leg (replaces W2LOOP-1): loops 1/2/4 on one quarter and the full socket, GB/s vs the C0 153 GB/s ceiling. Predictions fixed before the run (arithmetic, Ouro-1.4B: W_body 1.41 GB Q8, head 0.11 GB, 24 layers, 16 MHA KV heads x 128 = 8 KiB per layer slot): aggregate falls as 1/L at every np (a 55 MB layer cannot sit in the 8 MB L2, so no reuse across loops); at C=1024, f16 KV, L=4 the np-to-infinity ceiling is 1433e9/(1024*786432) = 1,780 tok/s and np=16 gives 16/13.0 ms = 1,230 tok/s ideal vs 3,420 for Qwen3-4B Q8 (4.28 GB, 144 KiB/token); the KV share exceeds the weight share beyond np=7; compute time is under 1/5 of byte time at every np that fits (VRAM headroom beside the 43 GiB :8083 is about 19 GiB, so np about 23 at C=1k f16), so the B*=64 knee is not reached for C above about 123 tokens. Six controls: frozen GGUF sha256 and prompts; comparators on the same build; per-cell raw JSON kept; 3 repeats ABA-alternated with the noise floor stated with its unit; full grid denominator (no cell dropped, VRAM-skipped cells listed); the rule below. Decision rule: PASS if parity holds and every measured aggregate lies within 0.5-1.1x of the byte-model prediction; a cell below 0.5x opens a HIP-kernel root-cause row (stale-binary check first: strings the lib, compare mtime to the commit) and is not a verdict on looping; this task issues no quality verdict. Writes the GPU arithmetic table into cpu-decode-roofline-program.md as the GPU half of the weight-reuse note (LOOP-1)."
    },
    {
      "owner": "handoffs/active/gpu-serving-tie-in-program.md",
      "task_text": "- [ ] **GPU-LOOP-2 — Looped small model as a reliability-boosted batch worker on the MI210: quality vs loops vs aggregate throughput against equal-cost dense and K-sample controls (intake-2585#record, intake-2547#record, intake-2551#record).** Question: at high concurrency (elastic-duty D1 batch-shedding class, np 16), does Ouro-1.4B (and 2.6B-Thinking as second tier) at 1/2/4 loops buy more correct worker answers per HBM byte than a non-looped model? Arms, served-cost arithmetic at np=16, C=1k, f16 KV (ideal step times, to be measured in GPU-LOOP-1): A1 Ouro-1.4B L=4 (5.76 GB weights/step + 12.9 GB KV, 13.0 ms, 1,230 tok/s); A2 L=2 (about 2,300); A3 L=1 (about 7,100 on the same weights); A4 Ouro-2.6B-Thinking L=4 (48 layers, about 11.3 GB weights/step, 1.5 MiB/token KV); C1 Qwen3-4B-Thinking-2507 Q8 (4.28 GB, 144 KiB/token, 3,420 tok/s, the equal-quality-class dense control); C2 Qwen3-1.7B Q8 majority-of-4 (about the same bytes per final answer as A1, 1,545 answer-equivalent tok/s: the K-sample route that the idle MFMA headroom makes free); C3 Qwen3-1.7B Q8 single sample (equal resident bytes); C0 the incumbent worker, Qwen3.6-35B-A3B on CPU :8070 (registry roles.worker_general.performance.quality_pct is null: it has never been scored on the worker battery, so it is measured here on the same frozen items). Frozen inputs: GSM8K-style math (n>=200, same problem list as the PR so the 26.0/67.0/80.5 published curve is a replication check) plus worker-battery items for explore, summarize, transform and strict tool-call JSON (n>=150 per suite), item list and scorer hashed before any generation; Ouro context stays under its trained 1024-token block (Ouro RECIPES: block_size 1024), longer prompts are a separate reported stratum. Per arm: pass@1 over 3 seeds, seed-to-seed agreement, JSON-validity rate, aggregate tok/s at np 16, wall-seconds per correct answer and correct answers per HBM GB moved; per-item raw outputs kept; correctness legs may share the card with :8083, throughput legs run in a GPU window with the host threads under the q3 claim. Controls: frozen inputs, incumbent baseline (C0 and C1), per-item raw outputs, 3-seed repeat with the A/B order alternated, full denominator including parse failures, predeclared rule. Decision rule: an Ouro arm earns a shadow-lane tenancy row (D3 shadow-only, no production traffic) only if (i) its paired accuracy vs C1 is within 2 points (McNemar not worse) and its seconds per correct answer at np=16 is at most 1.5x C1, or (ii) it beats C1 by at least 5 points at paired p<0.05 at no more than 2.5x C1 cost; the arithmetic predicts A1 costs 2.8x C1 per token, so (i) needs a real quality edge. Otherwise record NO-GO with the table and keep Ouro only as the vehicle for GPU-LOOP-3. Depends on the GPU-LOOP-1 build (our own task, not an external event)."
    },
    {
      "owner": "handoffs/active/gpu-acceleration-path.md",
      "task_text": "- [ ] **GPU-LOOP-3 — Loop count as a per-request serve-time effort switch in llama.cpp-experimental (intake-2585#record, intake-2586#record, intake-2547#record).** Today num_loops is a load-time GGUF key (PR #29823: --override-kv ouro.num_loops=int:N; PR #25994 expands hparams arrays to n_layer_phys*n_loops once in load_arch_hparams). Change set: (1) llama_context gains llama_set_n_loops(ctx,k), 1<=k<=file n_loops, carried in llm_graph_params and compared in can_reuse() so a changed k rebuilds the graph while graph_reserve still sizes the worst case; the builder loop bound becomes n_layer_phys*k and the LM-head tap is the shared final norm of loop k (the exit_at_step readout the HF code already has); about 150-250 lines. (2) server: parse n_loops or an effort alias (low/medium/high mapped by a GGUF key such as ouro.effort_loops) into slot params; update_slots splits the ubatch into one llama_decode per k-class (each class re-reads the weights, a cost that is small once np exceeds the weight/KV crossover of about 7 streams at C=1k); about 100-150 lines. (3) KV semantics, each point tested: a logical layer slot (loop j, layer i) holds KV only for sequences that ran loop j, so a prefix cached at k loops is valid for any request with k2<=k and invalid for k2>k (the deeper slots and the hidden states to recompute them are not stored), which makes the prompt-cache and ctx-checkpoint key carry n_loops_cached; a mid-request upgrade needs a re-prefill, a downgrade does not; cells are shared across layers, so a low-k request saves bandwidth and FLOPs but not VRAM unless the cache is sized with a k_max option (KV is 192 KiB per loop per token for Ouro-1.4B f16, 768 KiB at 4). (4) Validity gate: only checkpoints trained with per-loop supervision may expose the switch: Ouro yes (PR GSM8K F16 26.0/67.0/80.5 at 1/2/4), Nanbeige4.2 no (forced 1 loop is degenerate, 0.0 GSM8K), LoopCoder-v2 no (each R is a separately trained model, R=3 27.6 vs R=1 43.0 SWE-bench Verified). Acceptance tests: logits at per-request k on a file with n_loops=4 are bit-identical on CPU and within 1e-3 abs on HIP to a file loaded with num_loops=k, for k=1..4 on the 829-position fixture (this also verifies the claim that loop-j activations do not depend on the total loop count); four concurrent requests with k=1,2,3,4 reproduce their solo outputs; prefix-cache hit for k2<=k and miss for k2>k; throughput at np=16 with half k=1 and half k=4 within 0.8-1.2x of the byte-model prediction. Router oracle on the GPU-LOOP-2 per-item results: oracle minimum loops per item vs a no-oracle router (answer agreement between loops 2 and 4 on a calibration half, or the exit-gate probability); decision rule on the held-out half: PROMOTE the switch to a lane option if the router keeps at least 97% of the L=4 accuracy at mean loops at most 2.4 (cost at most 0.6x of L=4); else keep static L and record the oracle bound. Per-token adaptive exit is not offered: the PR does not convert the early_exit_gate and a batch graph saves nothing from it without row compaction."
    },
    {
      "owner": "handoffs/active/gpu-serving-tie-in-program.md",
      "task_text": "- [ ] **GPU-PLT-1 — LoopCoder-v2 (7.6B PLT coder, Apache-2.0) quality screen on the MI210 through transformers custom code, before and independent of the GGUF port (intake-2584#record, intake-2571#record).** Load Multilingual-Multimodal-NLP/LoopCoder-V2 at the pinned HF sha b87cf3a (BF16, 7,615,749,680 params, 15.2 GB, fits the about 19 GiB headroom beside :8083 without a KV problem) in an isolated venv with the transformers version its configuration_iquestpltcoder.py needs (Ouro needed 4.57.x, the research venv has 5.15.0: do not assume); confirm torch.version.hip and bf16 on gfx90a first; read config.json to see whether the loop count is a config field (the paper trains R=1..4 as separate models, so a forced R=1 on the released weights is not the paper R=1). Frozen inputs: HumanEval+ (164), LiveCodeBench subset released after the model cutoff (n>=200), BigCodeBench-hard subset, plus the frozen coder-suite items used for coder_escalation (cruxeval and the others E-7 scored: math 85.0, mmlu_pro 27.5, gpqa_diamond 47.5, cruxeval 22.5 at terse template 1443ea9ab4bb). Arms: LoopCoder-v2 as released; incumbent coder_escalation Qwen3.8-27B Q8 on :8083 (same harness, thinking off and medium); frontdoor Qwen3.6-35B-A3B on CPU; size control Qwen3-4B-Instruct-2507 (on disk). Controls: frozen items and scorer hashes, incumbent baselines, per-item raw outputs, 2 seeds, full denominator, rule below. Replication check against the paper own table: R=2 reports HE+ 84.1, LCB 35.4, BCB 46.1 and SWE-bench Verified 64.4 (harness unnamed, single seed, vendor-authored); accept the replication if HE+ >= 80 and the LCB subset score is within 5 points of the paper 35.4 after harness adjustment stated. Decision rule: open the serving legs of GPU-PLT-2 (agentic SWE-40 on the same scaffold that scored Qwen3.8-27B 21/40 = 52.5%, shadow lane only) if pooled pass@1 over HE+ and LCB is non-inferior to Qwen3.8-27B within 8 points (paired bootstrap lower bound) or the replication check passes; otherwise record NO-GO with the table (the port of GPU-PLT-2 still completes as parity work). Arithmetic that motivates it: at np=16, C=8k, Q8 (about 8.1 GB incl. head, KV 56 KiB/token f16 because later loops share loop-1 KV and keep only a 64-token window) a PLT-2 step is about 15.2 GB / 1433 GB/s = 10.6 ms bandwidth vs 2.5 ms compute at 32 rows, i.e. 1,510 tok/s ideal aggregate (about 600 derated by the 27B np8 ratio 157/400), vs 94 tok/s live at 4 concurrent on the 27B."
    },
    {
      "owner": "handoffs/active/gpu-acceleration-path.md",
      "task_text": "- [ ] **GPU-PLT-2 — Parallel-Loop-Transformer architecture (iquestpltcoder) on llama.cpp-experimental: port, parity, and MI210 decode curves (intake-2584#record, intake-2571#record).** Not blocked by the absence of upstream code; estimate 1.0-1.5 kLOC, 3-5 agent-days, 3-4x the 265/324-line Nanbeige/Ouro ports because those only unroll layers and carry no CLP, shared-KV or sliding window: converter for IQuestPLTCoderForCausalLM (about 150: 14 layers, hidden 5120, 40 heads / 8 KV, FFN 27648, R, window 64, per-head gate tensors; read the HF modeling file at sha b87cf3a first); arch/hparams/tensors (about 250); graph (about 400): a decode step builds R rows per sequence, row r input = token embedding + h^(r-1) of the previous position (per-sequence state of (R-1) x n_embd, held in the recurrent-memory path so checkpoint and spec-decode rollback come with it), row 1 attends the normal full KV, rows >=2 attend the shared loop-1 K/V through the existing cross-layer KV-reuse hparams plus a private 64-entry window cache (extra logical layers in the iSWA cache) and mix with the head-wise sigmoid gate; prefill runs R shifted sweeps over the prompt; cache/state plumbing and tests (about 400-700). Acceptance: top-1 logits match the HF reference on >=1000 positions and greedy continuations match on 20 prompts, on CPU and HIP; measured decode step ratio PLT-2 vs the same weights run as a one-loop graph is <=1.15 at np<=16 (prediction 1.02-1.05, since 2 rows per stream stay under the Q8 knee of 64 rows through 32 streams) and a sequential two-loop graph on the same weights is >=1.8 (the ByteDance paper reports 4.9 vs 4.8 vs 9.4 ms at bs 4 and 8.6 vs 8.1 vs 16.1 ms at bs 32 in its own stack); KV measured at about 56 KiB/token + window; spec-decode (MTP/DFlash2) rollback test using the state snapshot. Quality and serving verdicts are GPU-PLT-1 and the SWE-40 legs, not this task; this task delivers the engine."
    },
    {
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "task_text": "- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list."
    },
    {
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "task_text": "- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs."
    },
    {
      "owner": "handoffs/active/rocm-verify-profile-backend.md",
      "task_text": "- [ ] **RVP-EQV-1 — Decide the equivalence-checker port by measured miss rate, quant kernels declined on coverage (intake-2570#record, intake-2557#record).** Decision part 1, decline: no Volta-class equivalence for MMVQ, MMQ, quantize_q8_1 or dequant. They are bit-level (nibble unpack, rounding), which Volta does not cover (floats are reals, conversions are the identity), and they make up about 75% of AK GPU experiment rows (1116 of 1497). KERN-4 enumeration owns decode exactness. Decision part 2, a deciding probe for the real-valued subclass (FA-mma/FA-tile at parallel_blocks=1, GDN recurrence, mmvf float GEMV). In a llama.cpp-experimental worktree from the v10 tip, build 8 seeded sub-tolerance algebraic mutants: FA online-softmax rescale skipped only when the running max changes after the first KV tile; FA KV loop dropping the last KV column; FA-tile dropping one tail tile at a non-multiple context; GDN exp(g) decay dropped at a chunk boundary; GDN beta dropped for one head; mmvf dropping the final partial k-block at ne00 % tile != 0; and two controls with an O(1) error. Prove each mutant structurally (ISA diff of that kernel). Run the AK served-shape gate plus the AKX-ALL-31 edge families and the KERN-5 worst-element bound, 5 seeds each, on a frozen case manifest, keeping per-mutant per-seed raw verdicts and NMSE; the unmutated v10 build must pass 5/5 seeds. Decision rule: if any non-control mutant survives every gate on >=1 seed, open the equivalence milestone for that subclass on the RVP-RACE-2 interpreter (symbolic float values, v_exp_f32 as 2^x, cvt as identity, the 2 MFMA lane layouts in use, DPP/swizzle value moves, FA and GDN reference specs; estimate 4-6 kLoC, 4-6 engineer-weeks; advisory, never a speed-blocking gate, because intake-2555 Table 2 shows proof-restricted FA at 0.78x vs 1.37x). If all are caught, record the catch table and close the equivalence port with that table as the reason. Correctness-only, so no quiet host is needed."
    },
    {
      "owner": "handoffs/active/agentic-rocm-kernel-authoring.md",
      "task_text": "- [ ] **C5-ISA-2 — GCN-Gym: LLM-edited AMDGCN for a compute-bound gfx90a kernel whose limiter is register allocation (intake-2555#record, intake-2556#record).** Not trigger-gated, because the HIP-source levers on the target are measured out: AK-MMQ-H10 (J-cap) NEGATIVE, the ak-27b-gpu-verify stream-k MMQ hypotheses were all refused or retired, and the ROCm 6.2 AGPR copy tax and MMQ spills are compiler-side (INF03-REGAUDIT-1: Q8_0 J=64 at 256 VGPR with 37 spills; MMA-FA DKQ>=192 at 512 VGPR with hundreds of reloads per iteration). Build a standalone harness (1-2 weeks). Extract the gfx90a .s of one kernel from an experimental v10-tip build via gfx90a_isa_audit.py; let the agent edit it with unified-diff patch tools; reassemble with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a; load with hipModuleLoad; replay the served-shape launches (the RVP-RACE-2 capture shim); diff-test against the hipcc kernel with the AK oracle (host-double for Q8_0); require gfx90a_isa_audit.py diff to exit 0, and the RVP-RACE-2 verdict once M2 lands. Target 1: MMQ Q8_0 J=64 prefill tile. Target 2: MMA-FA DKQ>=192. Run 3 runs per target at a fixed declared token budget on a frozen shape manifest; time on the GPU window with ABBA (>=2 pairs) against the hipcc incumbent, keeping per-run raw candidate .s, oracle outputs and timings. Decision rule: if >=1 of 3 runs on a target reaches >=1.05x kernel time at the served prefill shape, passes the oracle, and its ABBA intervals do not overlap the incumbent, open an experimental-tree code-object override path for that kernel as an ISA-rung AK arm; otherwise record the null with traces and stop the ISA rung for that kernel class."
    },
    {
      "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
      "task_text": "- [ ] **ID-RI-ANCHOR-GATE — Make quote re-find a gate the author cannot satisfy by assertion (fabricated citations) (intake-2563#record, intake-1377#record).** Today `.claude/skills/research-intake/scripts/validate_intake.py` (~L436-441) only checks `claim_anchors` is non-empty and `verified_by` is self-written, so a fabricated or cross-pasted quote (the 2026-07-25 CORE ablation, also pasted into intake-895) passes. Borrow Octopus's rule that a mark is recorded only by the runtime after a verifier passes the artifact and nothing else can emit it (`docs/contracts/VERIFIERS.md`, \"Nothing emits marks\"). Change SKILL.md Stage-2 \"Writes permitted\" (claim_anchors bullet) and the Stage-2 Verification Gate: add `validate_intake.py --check-anchors` that (a) re-finds every anchor `quote` in the retained source via `scripts/vidya/machine_anchor.py:verify_source_anchor` / `raw_anchor_store.py` (dive wrapper must write the source into `EPYC_VIDYA_RAW_ANCHOR_ROOT`, today opt-in and unused by dives), (b) recomputes `quote_sha256`, (c) writes an `anchor_mark: {verifier, source_raw_sha256, found}` that only the script writes, and (d) flags any `quote_sha256` appearing under two different entries (cross-paste, needs no retained source). New dive-verified entries without an anchor_mark fail; legacy entries stay grandfathered. Controls: four frozen fixtures (verbatim quote, fabricated quote, whitespace-altered quote, same quote under two entries) plus the old validator output; per-fixture expected verdict recorded. Decision rule: ship only if all four fixtures give the predeclared verdict and a replay over the current index flags zero verbatim anchors. Passing proves containment, not entailment; the per-claim second reader stays."
    },
    {
      "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
      "task_text": "- [ ] **ID-RI-LANE-HEAD — Pin the repo revision every in-house citation was read at and refuse stale ones mechanically (stale clones) (intake-2563#record).** SKILL.md L391-405 forbids the shared clone in prose only (2026-09-14 dives read /workspace @d372c953). Octopus pins descriptor hashes in every formed grant and refuses a movement against a changed checkpoint with a typed `stale_epoch` (`docs/contracts/LEDGER_INDEX.md`). Change: (1) Stage-2 dive brief template requires `lane_head` (full SHA of the lane worktree) in the returned YAML, and a `dive_preflight.py` run by main before dispatch asserts the named root is the lane worktree and its HEAD is not behind origin/main; (2) in-house `claim_anchors` locators `path:Lx-Ly @ sha7` get validated by `validate_intake.py --check-lane-anchors`: `git show sha7:path` must contain the quote, and `git diff --name-only sha7..origin/main -- path` non-empty emits typed `stale_epoch` that blocks Stage-3 plan citation of that anchor until re-read. Controls: replay the 2026-09-14 incident (anchor at d372c953 for a file since changed), a moved path, an unchanged path. Decision rule: stale_epoch fires on the first two and not the third; zero false positives over the current in-house anchors."
    },
    {
      "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
      "task_text": "- [ ] **ID-RI-STAGE-GUARD — Compute the stage write grant by script and check the diff outside the agent (stage-gate violations) (intake-2563#record).** The skill's \"May write\" table (SKILL.md L50-58) and the Stage 1/2 gate \"`git status handoffs/` clean\" are prose run by the same agent that might violate them (2026-07-25: handoffs edited after an operator \"you can edit\"), and the dive `artifact_audit: clean` line is self-reported. Octopus forms the effective grant by a deterministic script at every arrival (ceiling intersect chain intersect bindings), enforces it outside the model and records a typed refusal row (`docs/architecture.md`, \"How policy is formed\"). Change: add `scripts/stage_grant.py form --stage N` (allowed paths: S1 index+.research-session.json; S2 index; S3 plan file; S4 the paths named by the approved plan, bound to `stage3_filing.plan_sha256` already checked at validate_intake.py ~L1084) and `check`, run by main at each stage boundary on `git status --porcelain` plus a tree hash taken at stage entry; violations append a typed row to the session JSON (`stage_write_outside_grant`, `plan_hash_stale`). Controls: replay the 2026-07-25 handoff-edit-in-Stage-2 case, a Stage-4 write outside the plan, and a clean stage. Decision rule: both violations refused, clean stage passes, no change to legacy validate_intake output."
    },
    {
      "owner": "handoffs/active/intake-derived-work-2026-07-25.md",
      "task_text": "- [ ] **ID-RI-DECLINE-VOCAB — Replace free-text decline reasons with a closed vocabulary (dropped actionables, operator Act-Do-Not-Defer rule) (intake-2563#record).** `validate_intake.py` ~L1132 accepts any `decline: <text>`, so \"vendor-only\", \"upstream has not done it\" or \"not applicable\" can close a row (the rules SKILL.md L40-48 forbid). Octopus refusals are typed rows from a closed set, \"never a silent drop\" (`docs/contracts/LEDGER_INDEX.md`). Change: a decline/closed-with-basis terminal must start with a code from {duplicate:<exact id>, superseded:<successor id>, measured-loss:<evidence ref>, math-constraint:<one-line proof>, external-event:<named event>, operator-ruled:<ruling ref>}; the validator rejects other prefixes and the forbidden phrases, and `external-event` requires a name that is not \"upstream\". Controls: freeze the current plan's decline rows as a fixture (expected: each maps to a code or is flagged for re-open), plus three negative fixtures (vendor-only, upstream-absent, not-applicable). Decision rule: negatives rejected, all legacy plans still pass under the unchanged legacy mode."
    },
    {
      "owner": "handoffs/active/autokernel-research-loop.md",
      "task_text": "- [ ] **AK-WIN-CNT-1 — Record in-window path counters beside every T1/T2 timing record (intake-2562#record).** Annex K's record grammar (`measurement/protocols/kernel-research.md` \"Record grammar\") has no field proving the timed window ran the intended path; T0 checks a dispatch trace but T1/T2 do not re-prove it. Resin keeps `graph_counts` and `overlap_counts` that exclude warmup and checks no JIT compile after warmup for unseen shapes. Do: capture hipGraph replay count vs eager launches and code-object load/JIT events inside the timed window on MI210 (use an in-process counter in a llama.cpp-experimental branch if none exists; the port is the build cost), write them as a non-gating diagnostic sidecar next to the raw samples, and draft the Annex K grammar amendment (human-amendment-only) making a path mismatch a VOID window. Controls: frozen anchor and one candidate, degraded-negative with graphs disabled (counter must show zero replays), A/A, per-window raw counters kept. Decision rule: sidecar ships if the degraded-negative is flagged and A/A is not; amendment text goes to the operator package."
    },
    {
      "owner": "handoffs/active/autokernel-research-loop.md",
      "task_text": "- [ ] **AK-PROF-ATTR-1 — Add GPU-active-union and a cross-run-subtraction lint to the profile report (intake-2562#record).** `scripts/kernel_rnd/autokernel/profile_report.py` / `profile_context.py` report `kernel_wall_share` and overlap tables but no GPU-active union versus summed kernel time. Resin's skill states overlapping kernel work is not additive and \"Engine minus GPU timing is unattributed time ... do not subtract different profiler and benchmark runs\" (optimize-resin-performance SKILL.md). Do: emit summed duration, active-union and critical-path per trace, and reject a derived \"unattributed\" figure built from two runs. Controls: a synthetic overlapping-kernel trace (sum greater than union), the hash-bound rocprofv2 trace already replayed in this handoff (~L444), a two-run subtraction negative. Decision rule: union less than sum on the synthetic case, existing wall-share values unchanged on the replayed trace, negative rejected."
    }
  ]
}
```
