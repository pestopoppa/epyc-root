# Inference Research — Active Backlog

**Purpose**: dispatch. Kernels, quantization, serving performance, models. CPU and GPU both live here — sub-area is the Track column, not a separate file.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**Compute-gated rows** are packed onto the host by the calendar owner under [`.claude/skills/inference-backlog-scheduling/`](../../.claude/skills/inference-backlog-scheduling/SKILL.md); a row is QUEUED only when ARMED with a live launcher, otherwise BACKLOG with a named blocker.

**History**: superseded narration for this index lives in [`../archived/inference-research-index-history-through-2026-08-10.md`](../archived/inference-research-index-history-through-2026-08-10.md).

**IDs are stable.** `INF-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-02 | agent collab rnd harness | [agent-collab-rnd-harness.md](agent-collab-rnd-harness.md) | Spike S3-ACH-01's actor allowlist; scope AC-CHECKPOINT-ALLOC against eligible independent continuations | — |
| INF-03 | agentic rocm kernel authoring | [agentic-rocm-kernel-authoring.md](agentic-rocm-kernel-authoring.md) | the C5 backlog; REGAUDIT-3 and AGPR-1 parked (operator 2026-09-27; resume steps in file) | INF-48, EVL-47 |
| INF-04 | angelslim techniques evaluation | [angelslim-techniques-evaluation.md](angelslim-techniques-evaluation.md) | BLOCKED: reopen when llama.cpp PR #22836 (AngleSlim kernels) merges + QAT checkpoints exist | — |
| INF-05 | attention matching kv compaction | [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md) | P2 refresh validation against current-stack long-context/coding workload (Qwen3.6-era + Coder-32B), inference-window-gated | — |
| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | GPU MMQ seeds parked (operator 2026-09-27): resume by running window_ab.sh in a GPU window (AK-MMQ-H10a/b), then AK-MMQ-H3 iglp_opt arm | INF-48, EVL-47, INF-64 |
| INF-64 | autokernel restart-loop fix | [autokernel-restart-and-strip.md](autokernel-restart-and-strip.md) | Complete per-file reference/entrypoint/HOLD manifest before individually safe deletion and footprint changes | — |
| INF-65 | autokernel aggregate candidate (champion) | [autokernel-champion-aggregate.md](autokernel-champion-aggregate.md) | Remove CH-30b workaround on C5; C6 fold (CH-LB1.1+UFH14-LB1.1); META-ASSERT-1a: land 520ad4f55 + GPU test-llama-archs; gate subshell bug | INF-06, INF-62, INF-64 |
| INF-66 | autokernel teardown and rebuild | [autokernel-rebuild-program.md](autokernel-rebuild-program.md) | R23-62 (R23-64 done 10-25: t48 stays); LBH-2.1 re-run (low) | INF-06, INF-64, INF-65 |
| INF-07 | batched decode measurement | [batched-decode-measurement.md](batched-decode-measurement.md) | E5 — the never-measured NUMA×batch 2D sweep; needs a post-promotion quiet window | — |
| INF-09 | cpu prefill compute large models | [cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) | PC-4 — experimental qwen35 prefill barrier/graph-fusion prototype: | — |
| INF-10 | cpu shape specialized gemv decode | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Receipts-only holder for the CPU gemv axis; live re-ranking is INF-70 — reopen only on the CPU18/CPU26 or intake re-surface triggers | — |
| INF-67 | cpu fused decoder blocks | [cpu-fused-decoder-blocks.md](cpu-fused-decoder-blocks.md) | FD-DIV-1b persists on C5: locate and fix the fused-yarn divergence in the champion; FD-OFF-PROD closes at V11-106 | INF-10 |
| INF-62 | dflash2 block drafter experimental build | [dflash2-block-drafter-experimental-build.md](dflash2-block-drafter-experimental-build.md) | DF2 open rows (DF2-DRAFTER-CAPABILITY, DF2-11/12/13/15/16/20, DF2-LB1); Qwopus items CANCELLED 2026-10-27 | INF-06, INF-50 |
| INF-12 | delta mem reproduction | [delta-mem-reproduction.md](delta-mem-reproduction.md) | Gate 2 MemoryAgentBench accuracy reproduction - GPU-only (CPU-infeasible) | — |
| INF-13 | engram conditional memory | [engram-conditional-memory.md](engram-conditional-memory.md) | Make k budget-conditional rather than fixed (intake-936 rider) | — |
| INF-16 | gemma challenge kernel techniques v7 | [gemma-challenge-kernel-techniques-v7.md](gemma-challenge-kernel-techniques-v7.md) | K10 — on a quiesced host, confirm the nodes[0] collision via stderr keylog, then re-eval Lever A and decide land/drop | — |
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | CLS-RECT-1, then G2-CONC on coherence_gate; XFER-3 paired task eval (uniform IQ4_XS); XFER-4b allowlist prefill A/B + task eval | INF-67, INF-10 |
| INF-72 | moe routing locality tap | [moe-routing-tap-and-locality-measurement.md](moe-routing-tap-and-locality-measurement.md) | RT-1 (Q38FN) + RT-9 (Q36) traced/analysed, RT-5 gate not met; RT-10 DS41 tap hook (C++), then RT-6/7 on DS41 | INF-34, INF-70 |
| INF-77 | deepseek v41 flash evaluation | [deepseek-v41-flash-evaluation.md](deepseek-v41-flash-evaluation.md) | W5 closed INVALID; W5d baseline+MMID 10-24 ~10:00Z, C46 j64 repro 10-23 q2; rest held for AK kernel work; W8d ram_admit | INF-31, RTG-57 |
| INF-78 | autokernel orchestrator actor backend | [autokernel-orchestrator-actor-backend.md](autokernel-orchestrator-actor-backend.md) | OAB-30 stub e2e (incl. keep→continuation); OAB-34 16384 output-cap hit rate per role | INF-77, INF-66, EVL-37, RTG-56, UFH-01 |
| INF-79 | conversation stack (speech) | [conversation-stack.md](conversation-stack.md) | CS-8.L4a/b done (year fix fd1a8941); CS-5 D1 Omni+Step PASS; run CS-8.STT0..STT3, CS-22.V0, CS-43.1 | — |
| INF-80 | exl3 cpu mi210 implementation | [exl3-cpu-mi210-implementation.md](exl3-cpu-mi210-implementation.md) | EXL3-6c5a: emit epyc.exl3.measurement.v1 rows (10-04 copy + research data/exl3-6c5-quality), ingest, tick; 6c5b p1 margin | — |
| INF-18 | gpu acceleration path | [gpu-acceleration-path.md](gpu-acceleration-path.md) | Explain the bidirectional-only mechanism before this becomes a placement input | — |
| INF-19 | gpu cot scaffold sidecar | [gpu-cot-scaffold-sidecar.md](gpu-cot-scaffold-sidecar.md) | G3-4 — future decision instrument (separate from G3-3). Select and run a decision-grade, | — |
| INF-22 | gpu serving tie in program | [gpu-serving-tie-in-program.md](gpu-serving-tie-in-program.md) | Bind per-role recipes/resources; run M4 all-role speed/quality gate; then PB-QCOST-1, GPU-ZOS-2.2 and CH-30 | — |
| INF-23 | heterogeneous slot fabric residency | [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) | HSF-5.P: re-run microbench (-lv 4, G4 amendment) on GPU after v11-086-cpu ~10-25 00:00Z | — |
| INF-24 | inference batch loop | [inference-batch-loop.md](inference-batch-loop.md) | P0 RCP prologue — RCP-W1 relaunch + preflight, RCP-W2 ledger materialize, RCP-W3 calibration smoke; gated OP-6a/6b + stack-restart approval | — |
| INF-26 | iqk iquant enablement | [iqk-iquant-enablement.md](iqk-iquant-enablement.md) | C-L3-Q38FN: profile why GSQ IQ3_XXS decode is 28% slower than UD-IQ4_XS, then a low-bit kernel branch; NEW-8 steps 0-1 | — |
| INF-28 | laguna s21 cpu port | [laguna-s21-cpu-port.md](laguna-s21-cpu-port.md) | L-9P — conditional CPU throughput/config discovery. The prepared | — |
| INF-29 | large moe expert parallelism | [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md) | CPU15-REVAL — Fresh canonical matrix if reopening: before enabling EP anywhere, run: | — |
| INF-30 | lightning attention port | [lightning-attention-port.md](lightning-attention-port.md) | LQ-2 — Run a focused AIME/MATH/GPQA bundle (reasoning_budget=0, exact templates); waits on an owned current-era q-scorer/routing A/B | — |
| INF-31 | llama cpp dsa contribution | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md) | D4 residual — pin the faulty `dequantize_V_bf16` line and file upstream (D4 done: c49a37c4) | — |
| INF-33 | log linear gated deltanet readiness | [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md) | Wire hattention_recurrent() into HGatedDeltaNetAttention.forward and confirm it reproduces chunk-path logits on CPU | INF-48 |
| INF-34 | mi210 big model and acceleration roadmap | [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) | PF1 — measure the CPU-vs-MI210 prefill crossover on the served Qwen3.8-Flash-Next UD-IQ4_XS (DR-3e retired 2026-10-28, 122B deprecated) | — |
| INF-37 | mi210 q8 dequant gemv roofline | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) | Resolve Q4/IQ2 approvals; scope INF37-MOE-Q8-FUSION's experimental GLU correctness slice | INF-48, EVL-47 |
| INF-40 | moe spec cpu spec dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | After the AutoKernel window: 5-rep moe_spec_budget sweep on qwen4exp + champion ef81196d5 (future architect_critic), MTP n-max≥3 | — |
| INF-41 | multimodal pipeline | [multimodal-pipeline.md](multimodal-pipeline.md) | Run S-18 paired 60-item CPU cohort; project/canary via VB-SERVING-DF2 | — |
| INF-42 | multiscreen attention evaluation | [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | G1 closed (100% recall to 128K, q8 = f16); pick the next multiscreen row or archive the handoff | — |
| INF-43 | numa placement defect | [numa-placement-defect-20260730.md](numa-placement-defect-20260730.md) | T3 — Re-run the 27 confounded E5 cells on declared 1-full + 2-half placement, incl. 0-95 --interleave=all, per P-BENCH-PLACEMENT-1 | — |
| INF-44 | numa prefill decode disaggregation | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | Blocked on INF-34 PF1 (CPU-vs-MI210 prefill crossover); then run NPD-1 or close the GPU-prefill branch | INF-34 |
| INF-45 | numa topology cutover resume | [numa-topology-cutover-resume-20260730.md](numa-topology-cutover-resume-20260730.md) | P0-3 — cold-start the stack, re-bench the contention matrix, commit + push all three repos | — |
| INF-46 | qwen mtp llamacpp port | [qwen-mtp-llamacpp-port.md](qwen-mtp-llamacpp-port.md) | P6b — Operator-gated load + gate bench of unsloth/Qwen3.6-35B-A3B-MTP-GGUF on fresh experimental: matched Q4 no-spec vs Q4-MTP | — |
| INF-48 | rocm verify profile backend | [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md) | Repair audited C6 carriers, wire oracle/Ghost boundary | EVL-47 |
| INF-49 | sarathi serve cpu evaluation | [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md) | Re-evaluate Sarathi-Serve chunked-prefill for the eval-batch serving class (the multi-tenant trigger fired by batched-decode E2) | — |
| INF-50 | speculative decoding mtp refresh | [speculative-decoding-mtp-refresh.md](speculative-decoding-mtp-refresh.md) | Run XGRAMMAR-A2 raw p95 and 16-prompt parity; qualify new benchmark symbols separately before any fold | — |
| INF-51 | streaming llm baseline | [streaming-llm-baseline.md](streaming-llm-baseline.md) | Run 4-axis inference sweep: 3 workloads (retrieval/reasoning/dialogue) x 3 budgets (25/50/75%) x 2 models | — |
| INF-52 | summary token attention readiness | [summary-token-attention-readiness.md](summary-token-attention-readiness.md) | Monitor Gates A–D (served-model KSA/GSA checkpoint, llama.cpp support PR, CPT-capable GPU, major-lab adoption); no work until one fires | — |
| INF-53 | tidar one pass variant b | [tidar-one-pass-variant-b.md](tidar-one-pass-variant-b.md) | W2 — Watch for a Q4_K_M-quantizable TiDAR-class checkpoint; on release, quantize it and return a go/no-go quality verdict | — |
| INF-54 | tq3 quantization evaluation | [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | Prototype faithful ChunkKV on a fresh llama.cpp-experimental tree | — |
| INF-56 | triattention kv selection | [triattention-kv-selection.md](triattention-kv-selection.md) | S8 — Sweep keep_ratio and layer_weights per production role; persist quality/speed/cost/reliability Pareto profiles | — |
| INF-58 | v9 kernel per request speculative params | [v9-kernel-per-request-speculative-params.md](v9-kernel-per-request-speculative-params.md) | Implement and prospectively ratify the sealed resident promotion fast path with fresh-server fallback | — |
| INF-59 | yarn context extension research | [yarn-context-extension-research.md](yarn-context-extension-research.md) | Re-plan YARN-128K-MI210 (128K items off CPU quarters); extension arms; optional YARN-AGG-1f power | RTG-57 |
| INF-60 | model refresh | [qwen38-27b-replace-qwen36.md](qwen38-27b-replace-qwen36.md) | Q38-T7b closed; run Q38-T7a passive log read, then VB-SERVING-DF2; Q38-T10.1 gate after | — |
| INF-61 | model refresh | [gpu-candidates-surface-qwen38-update.md](gpu-candidates-surface-qwen38-update.md) | Run a same-window n-max 4 vs 8 ABA at np≥2 before shipping the re-collected grid; then depth-sweep A4, A3, A1, FF and Laguna | INF-60 |
| INF-73 | autokernel unified surface | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) | LIVE GPU leg (serving-owner grant, ws58) | INF-66, INF-65, INF-70 |
| INF-74 | autokernel concurrent targets | [autokernel-concurrent-target-coordination.md](autokernel-concurrent-target-coordination.md) | Land INF-74-CGROUP-ROOT (root-owned cgroup delegation, Codex script), add escape tests, re-run gate; cutover rejected until then | INF-73 |
| INF-75 | autokernel cross-workload keep gate | [autokernel-cross-workload-keep-gate.md](autokernel-cross-workload-keep-gate.md) | AKX-P0d — run the W1–W6 base census on the current champion-of-record under stage claims, then AKX-P1b replay 732389d6 | INF-73, INF-66, INF-65 |
| INF-81 | autokernel all devices all dimensions | [autokernel-all-devices-all-dimensions.md](autokernel-all-devices-all-dimensions.md) | AKX-ALL-30b: write G3-first order + G1/G2 re-rank (R=1.73) into the seed draft; AKX-ALL-LB3.2 re-run via akxlb32 v2 | INF-73, INF-75, INF-77, INF-62, RTG-57, RTG-58 |
| INF-76 | paw compiled specialists | [paw-compiled-specialists.md](paw-compiled-specialists.md) | PAW-2 — self-hosted compile spike (intake-1481 server + intake-1478 weights); then PAW-5 candidates list | EVL-08 |
## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
