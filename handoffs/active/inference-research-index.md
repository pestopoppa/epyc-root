# Inference Research — Active Backlog

**Purpose**: dispatch. Kernels, quantization, serving performance, models. CPU and GPU both live here — sub-area is the Track column, not a separate file.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/inference-research-index-history-through-2026-08-10.md`](../archived/inference-research-index-history-through-2026-08-10.md).

**IDs are stable.** `INF-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-01 | 01 speculative decoding | [01-speculative-decoding.md](01-speculative-decoding.md) | Retire this compatibility pointer and redirect its external citations to the live spec-decode handoffs | — |
| INF-02 | agent collab rnd harness | [agent-collab-rnd-harness.md](agent-collab-rnd-harness.md) | (Optional spike, gate on operator interest) Point orx at EPYC's llama.cpp via OpenCode as a DISPOSABLE test vehicle (--backend local, custo… | — |
| INF-03 | agentic rocm kernel authoring | [agentic-rocm-kernel-authoring.md](agentic-rocm-kernel-authoring.md) | Supervise immutable-worktree r15 to a terminal aggregate, then validate its receipt chain before comparison | INF-48, EVL-47 |
| INF-04 | angelslim techniques evaluation | [angelslim-techniques-evaluation.md](angelslim-techniques-evaluation.md) | BLOCKED: reopen when llama.cpp PR #22836 (AngleSlim kernels) merges + QAT checkpoints exist | — |
| INF-05 | attention matching kv compaction | [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md) | P2 refresh validation against current-stack long-context/coding workload (Qwen3.6-era + Coder-32B), inference-window-gated | — |
| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | After reboot, run the matched IQK evidence campaigns, generate the real v2 pair, and materialize its archive | INF-48, EVL-47 |
| INF-07 | batched decode measurement | [batched-decode-measurement.md](batched-decode-measurement.md) | E5 — the never-measured NUMA×batch 2D sweep; needs a post-promotion quiet window | — |
| INF-09 | cpu prefill compute large models | [cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) | PC-4 — experimental qwen35 prefill barrier/graph-fusion prototype: | — |
| INF-10 | cpu shape specialized gemv decode | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Measure tinyBLAS on/off first (Phase 0) — sgemm.cpp is already compiled in, so it confounds every later A/B | — |
| INF-11 | deepseek v4 flash 0731 dspark | [deepseek-v4-flash-0731-dspark.md](deepseek-v4-flash-0731-dspark.md) | Run the matched standardized-versus-control DFlash throughput, acceptance and exact-parity comparison | — |
| INF-12 | delta mem reproduction | [delta-mem-reproduction.md](delta-mem-reproduction.md) | Gate 2 MemoryAgentBench accuracy reproduction - GPU-only (CPU-infeasible) | — |
| INF-13 | engram conditional memory | [engram-conditional-memory.md](engram-conditional-memory.md) | Make k budget-conditional rather than fixed (intake-936 rider) | — |
| INF-14 | fable5 window2 findings 05b mi210 inference  | [fable5-window2-findings-05b-mi210-inference-architecture.md](fable5-window2-findings-05b-mi210-inference-architecture.md) | Extract the MI210 architecture findings into docs, then move to completed/ (6 active handoffs cite it — relink first) | — |
| INF-16 | gemma challenge kernel techniques v7 | [gemma-challenge-kernel-techniques-v7.md](gemma-challenge-kernel-techniques-v7.md) | K10 — (follow-up) Lever A quiet-host re-eval: on a quiesced host (fresh-server/run, fprintf(stderr) keylog to confirm the nodes0 collision… | — |
| INF-17 | glm51 reap cpu evaluation | [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | Run the five-prompt short-context smoke (greeting, code, reasoning, structured, tool-call) — one positive is not a set | — |
| INF-18 | gpu acceleration path | [gpu-acceleration-path.md](gpu-acceleration-path.md) | Explain the bidirectional-only mechanism before this becomes a placement input | — |
| INF-19 | gpu cot scaffold sidecar | [gpu-cot-scaffold-sidecar.md](gpu-cot-scaffold-sidecar.md) | G3-4 — future decision instrument (separate from G3-3). Select and run a decision-grade, | — |
| INF-20 | gpu drafter control redesign | [gpu-drafter-control-redesign.md](gpu-drafter-control-redesign.md) | DR-3 — broader K2 admission runner/package: build the dry-run-first K2 | — |
| INF-21 | gpu drafter mi200 investigation | [gpu-drafter-mi200-investigation.md](gpu-drafter-mi200-investigation.md) | Re-anchor to the live next step: Stage-1 end-to-end speedup / co-residency redesign (Stage 4 stays blocked on failed Stages 1–3) | — |
| INF-22 | gpu serving tie in program | [gpu-serving-tie-in-program.md](gpu-serving-tie-in-program.md) | P0-1 (operator) — run the E8 ratification once Codex presents the apply-ready D4 bundle | — |
| INF-23 | heterogeneous slot fabric residency | [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) | Model GPU host threads as a fabric slot (gpu-host) — design only, gated on the residency verdict | — |
| INF-24 | inference batch loop | [inference-batch-loop.md](inference-batch-loop.md) | P0 RCP prologue — RCP-W1 (reference relaunch + preflight), RCP-W2 (ledger materialize), RCP-W3 (calibration smoke) — gated OP-6a/6b + OP-st… | — |
| INF-25 | intra process tensor parallel decode | [intra-process-tensor-parallel-decode.md](intra-process-tensor-parallel-decode.md) | Keep as the intra-process TP standing-constraint holder; reopen only if tensor-parallel decode is reconsidered | — |
| INF-26 | iqk iquant enablement | [iqk-iquant-enablement.md](iqk-iquant-enablement.md) | T2 — Gate trellis in ik_llama.cpp, not in our tree. /mnt/raid0/llm/ik_llama.cpp is already on disk and is the reference implementation. Bui… | — |
| INF-28 | laguna s21 cpu port | [laguna-s21-cpu-port.md](laguna-s21-cpu-port.md) | L-9P — conditional CPU throughput/config discovery. The prepared | — |
| INF-29 | large moe expert parallelism | [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md) | CPU15-REVAL — Fresh canonical matrix if reopening: before enabling EP anywhere, run: | — |
| INF-30 | lightning attention port | [lightning-attention-port.md](lightning-attention-port.md) | LQ-2 broader quality eval: if keeping a math/reasoning role, run a focused AIME/MATH/GPQA-style bundle with reasoning_budget=0, exact promp… | — |
| INF-31 | llama cpp dsa contribution | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md) | D4 — root-cause the HIP bf16 LIGHTNING_INDEXER numerical failure (flaky, ERR≈1.0, | — |
| INF-32 | llamacpp v6 consolidation | [llamacpp-v6-consolidation.md](llamacpp-v6-consolidation.md) | SWA slot-reuse fixes (d1c72d7fc / 603702769) — verify vs upstream SWA before drop. | — |
| INF-33 | log linear gated deltanet readiness | [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md) | Pretrained Log-Linear Gated DeltaNet model checkpoint publicly available (any size) | — |
| INF-34 | mi210 big model and acceleration roadmap | [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) | DR-3 broader K2 admission runner/package: implement the dry-run-first K2 | — |
| INF-37 | mi210 q8 dequant gemv roofline | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) | Resolve approval; clean-replay Q4_K branchless decode and durable IQ2 model paths | INF-48, EVL-47 |
| INF-39 | moe aggregate deployment wins brief | [moe-aggregate-deployment-wins-brief.md](moe-aggregate-deployment-wins-brief.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| INF-40 | moe spec cpu spec dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | Current live-MTP MoE verifier B-sweep: run on actual frontdoor/worker/architect verification batches with speed, acceptance, and quality/bi… | — |
| INF-41 | multimodal pipeline | [multimodal-pipeline.md](multimodal-pipeline.md) | S-9 — wire start_tts() into orchestrator_stack.py (port 9002 reserved); capability exists, wiring does not | — |
| INF-42 | multiscreen attention evaluation | [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | HRM-1: Pull huggingface.co/sapientinc/HRM-Text-1B and run a fair head-to-head against Qwen3.5-1.7B-Instruct on our benchmark suite (MMLU, A… | — |
| INF-43 | numa placement defect | [numa-placement-defect-20260730.md](numa-placement-defect-20260730.md) | T3 — Re-run the 27 confounded E5 cells on declared placement. Per model the grid must | — |
| INF-44 | numa prefill decode disaggregation | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | BLOCKED: feasibility-gated (xGMI KV-transfer falsification); reopen on multi-tenant shift | — |
| INF-45 | numa topology cutover resume | [numa-topology-cutover-resume-20260730.md](numa-topology-cutover-resume-20260730.md) | P0-1 — fix the 30 net-new breaking tests across 14 files; this blocks the commit | — |
| INF-46 | qwen mtp llamacpp port | [qwen-mtp-llamacpp-port.md](qwen-mtp-llamacpp-port.md) | P6b Operator-gated fresh-v9-experimental model-load + gate bench on unsloth/Qwen3.6-35B-A3B-MTP-GGUF, with matched Q4 no-spec vs Q4-MTP art… | — |
| INF-47 | qwen36 27b cpu feasibility | [qwen36-27b-cpu-feasibility.md](qwen36-27b-cpu-feasibility.md) | P1 CPU throughput probe (single-instance + NUMA-4-way) on Qwen3.6-27B Q4_K_M - inference-blocked; PARKED 2026-07-14, reopen only if 27B bec… | — |
| INF-48 | rocm verify profile backend | [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md) | After r15, run governed 122B decode attribution and capture real EPYC C3/C5 workload evidence | EVL-47 |
| INF-49 | sarathi serve cpu evaluation | [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md) | Re-evaluate Sarathi-Serve chunked-prefill for the eval-batch serving class (batched-decode E2 keep-candidate = the fired multi-tenant trigg… | — |
| INF-50 | speculative decoding mtp refresh | [speculative-decoding-mtp-refresh.md](speculative-decoding-mtp-refresh.md) | SW-2 — confirm SW-1 against a live server when a lane is free and no protected bench region is held: POST a completion carrying speculative… | — |
| INF-51 | streaming llm baseline | [streaming-llm-baseline.md](streaming-llm-baseline.md) | Run 4-axis inference sweep: 3 workloads (retrieval/reasoning/dialogue) x 3 budgets (25/50/75%) x 2 models | — |
| INF-52 | summary token attention readiness | [summary-token-attention-readiness.md](summary-token-attention-readiness.md) | Gate A — Pretrained checkpoint of a model we serve (Qwen2.5/3.5/3.6 family, or any base we already deploy) released with KSA-style summary… | — |
| INF-53 | tidar one pass variant b | [tidar-one-pass-variant-b.md](tidar-one-pass-variant-b.md) | W2 — checkpoint gate + Q4 quality validation (bench-only when gate fires): watch for a Q4_K_M-quantizable TiDAR-class checkpoint (none exis… | — |
| INF-54 | tq3 quantization evaluation | [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | Prototype faithful ChunkKV on a fresh llama.cpp-experimental tree | — |
| INF-55 | tree draft forward port plan | [tree-draft-forward-port-plan.md](tree-draft-forward-port-plan.md) | Decide forward-port vs drop for the tree-draft plan now that v9 is frozen; the read-only investigation is complete | — |
| INF-56 | triattention kv selection | [triattention-kv-selection.md](triattention-kv-selection.md) | S8 autopilot exploration: sweep keep_ratio and layer_weights per production role; persist Pareto profiles with quality, speed, cost, and re… | — |
| INF-57 | v7 promotion | [v7-promotion.md](v7-promotion.md) | Move to completed/ — the v7 cutover closed and is twice superseded (v8, v9); relink the 14 active handoffs citing it | — |
| INF-58 | v9 kernel per request speculative params | [v9-kernel-per-request-speculative-params.md](v9-kernel-per-request-speculative-params.md) | Implement and prospectively ratify the sealed resident promotion fast path with fresh-server fallback | INF-11 |
| INF-59 | yarn context extension research | [yarn-context-extension-research.md](yarn-context-extension-research.md) | QUEUED (LOW): reactivate when context_extension is a concrete workload requirement tolerating >32K position-discrimination loss | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
