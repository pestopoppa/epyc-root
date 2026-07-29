# BACKLOG DISPATCH QUEUE — pre-vetted work for idle mains

**Generated 2026-07-29** (repo tip `4dc445a2`). Read-only sweep. This file is the ONLY artifact written;
no handoff, checkbox, `queue.jsonl`, inbox, outbox, heartbeat or cursor was touched.

## Counts

| Metric | Value |
|---|---|
| Unchecked `- [ ]` tasks in `handoffs/active/` | **1103** at sweep start / **1094** at write time (see *Volatility* below) |
| Files carrying them | **153** of 177 |
| **`none`-lane AND unblocked → DISPATCHABLE RIGHT NOW** | **~232** |
| `none`-lane but blocked | ~430 |
| `cpu`-lane (needs a model server / bench) | ~280 |
| `gpu`-lane (needs MI210) | ~160 |
| Already have `READY` rows in `queue.jsonl` | 19 (11 opendataloader + 8 repl-turn-efficiency) — **all now stale, see below** |

## Coverage — what this sweep did and did not cover

**Covered: 100% of `handoffs/active/*.md`.** Every file containing a `- [ ]` line was read and every
such line classified. This is a *superset* of the index tree: I enumerated the whole directory rather
than only following links, so nothing reachable from `master-handoff-index.md` can be missing.

Index tree traversed and confirmed: `master-handoff-index.md` → 6 domain sub-indices
(`routing-and-optimization-index`, `inference-acceleration-index`, `cpu-inference-optimization-index`,
`research-evaluation-index`, `hermes-agent-index`, `pipeline-integration-index`) + the 2 standalone
strategy indices (`harness-selection-and-integration`, `reviewer-control-plane-index`).

**6 handoffs carry open tasks but are linked from NO index** (orphans — a coordinator would never find
them by navigation; they are included here):
`agent-collab-rnd-harness` · `autopilot-authority-autoenable-proposal` · `core-v2-design-note-2026-07-23` ·
`qwen-mtp-llamacpp-port` · `re4-protocol-redesign` · `stale-open-audit-2026-07-18`.

**NOT covered (deliberately):** `handoffs/archived/`, `handoffs/completed/`, `progress/`, `CHANGELOG.md` — history, per instruction.

**Honest edges — read these before trusting a row:**
1. **Size estimates are the weakest axis.** They are judgement from reading the task text and its
   context, not from opening the target code. Treat S/M/L as a dispatch hint, not a commitment.
2. **~40 rows list `?` for files** because the handoff itself names no concrete target. Those need a
   scoping pass before they are truly "ready".
3. **Index-pointer rows double-count.** `cpu-inference-optimization-index`, `research-evaluation-index`,
   `routing-and-optimization-index`, `pipeline-integration-index`, `hermes-agent-index` and
   `inference-acceleration-index` contain rows that *point at* work owned elsewhere. Known duplicate
   pairs are named in the Collision Map. Dispatching both halves is wasted effort.
4. **Some unchecked rows are already done in prose** (checkbox never flipped). Ten confirmed-stale rows
   are flagged inline with `STALE?`. There are probably more.

## Volatility — re-grep before you dispatch

Two handoffs changed *while this sweep ran*: a live main closed 9 tasks in
`opendataloader-pipeline-integration.md` (22→17) and `repl-turn-efficiency.md` (13→9), and both files
are dirty in `git status`. **All 19 `READY` rows in `queue.jsonl` point at these two handoffs by line
number, and those line anchors have shifted.** Treat both handoffs as OWNED and do not dispatch them.
For every other handoff, `grep -n '^\s*- \[ \]' <file>` before assigning — line numbers are the anchor.

---

# TOP 40 — READY NOW

`none` lane · no blocker · parallel-safe · small. Fire any of these at an idle main immediately.
No two rows in this table touch the same file, so all 40 can run concurrently.

| # | Task (path:line) | Handoff § | Lane | Size | Files touched | What it is |
|---|---|---|---|---|---|---|
| 1 | `cpu-shape-specialized-gemv-decode.md:723` | pickup-checklist | none | S | (research only) | Check llama.cpp upstream for new CPU ukernel PRs |
| 2 | `cpu-shape-specialized-gemv-decode.md:727` | pickup-checklist | none | S | fork commits 143ded626/c4e06b01e/59d2012b2 | Confirm TIDE early-exit paths dormant before any baseline |
| 3 | `stale-open-audit-2026-07-18.md:92` | recommendations | none | S | dashboard backlog banner config | Publish corrected live-backlog figure (~544, board over-counts) |
| 4 | `decision-aware-routing.md:613` | speed-axis | none | S | `orchestration/instrument_eras.yaml` | Record instrument-era boundary row for reward values |
| 5 | `rlm-contested-claims-self-evaluation.md:68` | tasks | none | S | niah scorer module | Format-robust NIAH scorer (strict + lenient) |
| 6 | `reviewer-escalation-and-human-gate-policy.md:22` | tasks | none | S | SafetyGate protected-action config | Align protected-action list with existing SafetyGate |
| 7 | `intake-derived-work-2026-07-25.md:87` | P3 process defects | none | S | `scripts/validate/`, research-intake cross-reference-map | Add path-resolution check for the intake cross-reference map |
| 8 | `agentic-rocm-kernel-authoring.md:78` | progress-checklist | none | S | `research/deep-dives/…geak-synthesis.md` | GEAK-family freshness sweep at each audit |
| 9 | `gpu-acceleration-path.md:531` | 2026-07-29 fix | none | S | `gpu-acceleration-path.md` | Record reverse-KL on-policy-distillation negative as guardrail |
| 10 | `tool-use-eval-contract.md:366` | intake 2026-07-21 | none | S | sentinel prompt definitions | Adopt negative-constraint + stated-consequence sentinel pattern |
| 11 | `gpu-serving-tie-in-program.md:143` | P5 | none | S | `heterogeneous-slot-fabric-residency.md` | Add GPU host threads as a modeled slot-fabric consumer |
| 12 | `model-stack-change-standardization-audit.md:229` | update-checklist | none | S | `tests/unit/` priors/guard/enum-sync/q_scorer suites | Run focused unit tests for priors, guard, scorer, admission |
| 13 | `eval-tower-verification.md:522` | de-anchoring | none | S | `autopilot.py:1431`, `paired_stats.py` | Unify autopilot's 2nd McNemar producer onto `verdict_from_result` |
| 14 | `minddr-deep-research-mode.md:207` | search-time contamination | none | S | `minddr-deep-research-mode.md` | Demote BrowseComp/WideSearch/xbench anchors to observation-grade |
| 15 | `engram-conditional-memory.md:379` | retrieval-policy rider | none | S | `engram-…md`, `unified-trace-memory-service.md` | Correct the ReasoningBank ranking claim in retrieval notes |
| 16 | `unified-trace-memory-service.md:211` | UTM-M4 | none | S | `src/trace/harness_schema.py` | Mine ReasoningBank repo for its 3 prompts + JSON schema |
| 17 | `autopilot-decision-plane-audit-2026-07-22.md:399` | deliverables | none | S | `q_scorer.py`, `episodic_store.py` | Apply find-or-update to `_update_escalation_memory` append-only rows |
| 18 | `orchestration-robustness-audit-2026-07-11.md:240` | faiss orphans | none | S | `orchestration/repl_memory/faiss_store.py` | Startup sweep unlinking old unopened faiss tmp orphans |
| 19 | `autopilot-control-plane-integration.md:23` | AP-3b.2 | none | S | `autopilot-control-plane-integration.md` | Decide whether draft-tree belongs in AP-3 |
| 20 | `speculative-decoding-mtp-refresh.md:236` | intake 2a | none | S | `models/*.gguf` headers | Tensor-count header gate for the DavidAU Qwen3.6-27B MTP GGUFs |
| 21 | `agent-file-prose-compression.md:244` | intake 2a | none | S | `agent-file-prose-compression.md` | Re-source `/doctor` behaviour from the CLI before speccing |
| 22 | `learned-routing-controller.md:1613` | deep-dive correction | none | S | (guardrail note) | Standing guardrail: do not import intake-866 equivalence framing |
| 23 | `document-parser-table-bench.md:144` | consequence | none | S | (guardrail note) | Guardrail: no MinerU/GLM-OCR downloads as odl_bench swaps |
| 24 | `scorer-fork-drift-audit-2026-07-22.md:257` | residual tasks | none | S | `scripts/benchmark/seeding_legacy.py` | Guard or delete the legacy ComparativeResult reward-injection path |
| 25 | `autopilot-continuous-optimization.md:1529` | AP-32 | none | S | `wiki/agent-architecture.md`, `strategy_store.py` | Strike unmeasured +1.1% claim; guard the dead linter |
| 26 | `architect-model-selection-bench.md:330` | follow-up tooling | none | S | `scripts/bench/gpu_lib.sh`, `run_arm.sh`, `run_budget.sh` | Promote scratchpad GPU driver scripts into the repo |
| 27 | `context-folding-progressive.md:113` | deep-dive correction | none | S | `context-folding-progressive.md` | Record do-not-prioritize decision for ContextRot harness replication |
| 28 | `scoring-infra-standardization.md:184` | intake 2a | none | S | `research/intake_index.yaml`, `benchmarks/instruction_precision` | Adopt six-point SWE-bench disclosure standard for intake-916/917/924 |
| 29 | `tool-output-compression.md:442` | intake 2026-07-21 | none | S | `scripts/utils/compress_tool_output.py` | Bias Phase-3d fallback chain toward observation-dropping first |
| 30 | `decision-aware-routing.md:185` | DAR-5 | none | S | `learned-routing-controller.md` | Document cold-start note for LRC P5 onboarding |
| 31 | `ernie-image-turbo-evaluation.md:139` | progress-checklist | none | S | `research/deep-dives/` ernie dive | Record LongText-Bench harmonized ranking in the deep dive |
| 32 | `intake-derived-work-2026-07-25.md:166` | P1b DFlash | none | S | capability registry yaml | Re-triage the stale dflash registry `forbid` row |
| 33 | `model-stack-single-source-update-pipeline.md:325` | outstanding | none | S | `seeding_rewards.py`, `corpus_quality_gate.py`, `kv_compress.py` | Keep 3 re-audited surfaces unchurned absent a new duplicated fact |
| 34 | `unified-trace-memory-service.md:219` | UTM-M6 | none | S | `research/intake_index.yaml` | File EvoMemBench 128K context-competition as a distinct failure mode |
| 35 | `rao-redel-substrate-spike.md:432` | intake 2026-07-21 | none | M | `orchestration/repl_memory/episodic_store.py` | Adopt SkyRL parent/child rollout-tree accounting shape |
| 36 | `reviewer-calibration-accounting.md:30` | RC | none | M | `src/trace/review_ledger.py` | Persist full rubric + per-item grades in corpus rows |
| 37 | `llamacpp-v6-consolidation.md:77` | Stage-2 parity F1 | none | M | `llama.cpp-v6 ggml/src/ggml-cpu/ops.cpp` | Fold f1-paged-attn branch into v6, off-by-default |
| 38 | `granite-97m-r2-bench-plan.md:233` | Phase C | none | M | `internal-kb-rag.md`, `colbert-…md`, `searxng-…md` | Phase C retriever promotion decision + downstream handoff updates |
| 39 | `frontier-f1-real-task-corpus.md:115` | W2c | none | M | `scripts/tasks/harvest_tasks.py`, its unit test | Port ~50-line Hermes SQLite reader instead of a letta dependency |
| 40 | `benchmark-results-dashboard.md:47` | Phase 1 | none | S | `dashboard/`, both `model_registry.yaml` | Enumerate models on the system from both registries |

**Runner-up bench (also `none`+unblocked+parallel-safe, use when the top 40 are claimed):**
`decision-aware-routing.md:492` · `decision-aware-routing.md:614` · `rlm-…:80` ·
`reviewer-escalation-…:24` · `intake-derived-work-…:45,50,53,63,92,132,208` ·
`agentic-rocm-…:74` · `gpu-acceleration-path.md:524` · `gpu-serving-…:53` ·
`model-stack-change-…:230` · `model-stack-single-source-…:320,350,352` ·
`tq3-quantization-evaluation.md:62` · `unified-trace-…:210,226` ·
`autopilot-decision-plane-…:483` · `integration-test-coverage.md:38` ·
`internal-kb-rag.md:314` · `backlog-roi-audit-…:16` · `agent-collab-rnd-harness.md:42` ·
`speculative-decoding-mtp-refresh.md:212,233` · `multimodal-pipeline.md:327` ·
`within-role-placement-…:381,412` · `autopilot-dashboard-…:319` ·
`routing-and-optimization-index.md:652,653` · `large-moe-expert-parallelism.md:37` ·
`scorer-fork-drift-…:258` · `autopilot-continuous-optimization.md:1511,1512,1513,1530,1537` ·
`architect-model-selection-bench.md:166,329,473,504` · `harness-selection-…:144,146` ·
`mathsmith-hc-formalizer-eval.md:120,127` · `scaffold-autopilot-…:120` ·
`tri-role-coordinator-architecture.md:176,177` · `rocm-verify-profile-backend.md:27` ·
`agent-world-env-synthesis.md:278,279` · `iqk-iquant-enablement.md:140` ·
`reasoning-effort-levels.md:351` · `context-folding-progressive.md:84` ·
`scoring-infra-standardization.md:35` · `fable5-window2-findings-03-…:69,70` ·
`tool-output-compression.md:450,451` · `repo-readiness-scorer.md:414,415` ·
`stale-open-audit-2026-07-18.md:86,88,93` · `per-request-reasoning-budget.md:210,211` ·
`laguna-s21-cpu-port.md:97` · `x-mas-text-routing.md:49` · `deepseek-v4-flash-cpu-port.md:443`

---
# BY HANDOFF

Row format: `L<line> | lane | size | psafe | blocker | description | files`.
`blocker = -` means READY. Handoffs are alphabetical. Line numbers are the dispatch anchor —
re-grep before assigning.

## agent-collab-rnd-harness.md (3)
- L42 | none | M | Y | - | Feature-mine OpenHyra trusted-evaluator + anti-TOCTOU scoring integrity | agent-collab-rnd-harness.md, rocm-verify-profile-backend.md
- L43 | cpu | L | Y | operator interest gate | Optional spike pointing orx at EPYC llama.cpp via OpenCode | opencode.json, orx harness/mod.rs
- L44 | cpu | M | Y | macOS-only sandbox; needs external container | Optional spike: third OpenHyra backend adapter to llama.cpp | OpenHyra llm_backend adapter

## agent-file-prose-compression.md (5)
- L233 | none | S | Y | operator decision | Operator picks immediate shared rollout vs n=30 expansion | handoff
- L241 | none | M | N | - | AFC-P5.0 lossless structural deletion pass before Phase-5 compression | CLAUDE.md, agents/shared/*.md
- L242 | cpu | L | N | operator approval + host-quiet window | AFC-P5.1 falsify vendor 80%-cut claim through compliance gate | tests/compliance/agent_file/live_runner.py
- L243 | none | M | N | - | AFC-P5.2 de-duplicate four triple-stated policies, fix v6/v7 drift | agents/shared/ENGINEERING_STANDARDS.md, CLAUDE.md
- L244 | none | S | Y | - | Re-source /doctor behaviour from the CLI before speccing | handoff

## agent-world-env-synthesis.md (7)
- L278 | none | M | Y | - | Implement plan-executor divergence halt in SolvabilityGate | env_synth/verifier_builder.py
- L279 | none | M | Y | - | Evaluate TaleSuite/Jericho as public long-horizon agent eval | env_synth/, eval_tower.py
- L284 | cpu | L | N | operator inference window (48h) | 48h bootstrap discovery run with incremental persistence | env_synth/, orchestration/reports/
- L285 | cpu | L | N | endless-terminals dataset download pending | Pull dataset + PPL checkpoints, re-eval TB-2.0 transfer gap | env_synth/, data/
- L286 | cpu | L | N | AW-7 dataset; operator inference window | Reproduce Endless-Terminals Stages I-IV with gemma4 filter | env_synth/
- L287 | cpu | L | N | Agent-World weights release/download | Corroboration probe on released 8B/14B via SWE-Bench/GAIA | env_synth/
- L288 | gpu | L | N | MI210 GRPO smoke; Phase 1 | Multi-environment GRPO training of co-evolving policy | env_synth/

## agentic-rocm-kernel-authoring.md (10)
- L68 | gpu | L | Y | GEAK-eval reproduction (L73) | Integrate KernelBench as C3 correctness substrate | GEAK-eval harness, kernel_eval.sh
- L69 | gpu | L | N | task AK-KB-1 | Establish KernelBench baseline over llama.cpp-HIP kernels | GEAK-eval harness
- L73 | gpu | L | Y | P-GPU-1 protocol write-up (L74) | Reproduce GEAK-eval compile/correctness/timing on gfx90a | GEAK-eval repo
- L74 | none | M | Y | - **STALE?** P-GPU-1 already ratified 2026-07-19 | Write P-GPU-1 protocol | MEASUREMENT.md, p-gpu-1-ratification-package
- L75 | gpu | L | Y | AgentKernelArena is gfx942-only, needs port | Register six controllers as arena adapters; A/B gfx90a | AgentKernelArena adapters
- L76 | gpu | L | Y | needs rocprof on MI210 | Build gfx90a profiler-metric analyzer via raw rocprof | C4 profiler analyzer
- L77 | gpu | L | Y | robust-kbench gfx942-only | Anti-reward-hacking layer with unseen-shape generalization | C6 anti-hacking layer
- L78 | none | S | Y | - | GEAK-family freshness sweep at each audit | research/deep-dives/…geak-synthesis.md
- L83 | gpu | L | Y | needs C5/GEAK-eval substrate | Seed C5 with HyRA kernels; re-author and re-attest gfx90a | C5 seed corpus
- L84 | gpu | L | Y | scope after FP8-upcast path exists | Add FP8-weight→bf16-MFMA upcast GEMV authoring target | HIP FP8-upcast GEMV kernel

## angelslim-techniques-evaluation.md (3)
- L73 | none | S | Y | llama.cpp PR #22836 merge + QAT checkpoints | Watch item: reopen when STQ1_0 kernels and QAT weights exist | handoff, tq3-quantization-evaluation.md
- L81 | cpu | M | Y | operator-gated; PR #22836 | Include Hy3-FP8 flagship-MoE as AngelSlim compression test vector | handoff, speculative-decoding-mtp-refresh.md
- L94 | cpu | L | Y | operator-gated Hy3 bench; ~90GB download | Official IQ1_M GGUF is authoritative path if Hy3 bench runs | model_registry.yaml

## architect-model-selection-bench.md (16)
- L166 | none | S | Y | - | Confirm MMLU-Pro control re-runs under hardened protocol | architect-model-selection-2026-07-20.md
- L167 | none | L | Y | Phase 2 approval | Build/validate SWE-bench-Verified agentic FAIL_TO_PASS scorer | debug_scorer.py, dataset_adapters.py
- L176 | gpu | L | N | gate 2: inference-batch-loop outstanding tests | Phase 1 A1-A4 across AIME25/GPQA-D/MMLU-Pro paired arms | artifacts/architect-bench-gpu-20260720/
- L187 | gpu | L | N | deprioritized by operator (~4pp MDE) | GPU arms full n=198 gpqa_diamond_cot primary CoT measure | artifacts/architect-bench-gpu-20260720/
- L188 | gpu | M | N | - | MMLU-Pro control re-run under hardened protocol | dataset_adapters.py
- L329 | none | L | Y | - | Interleaved-per-question sequential runner with e-process stopping | bench runner, architect-bench-runbook.md
- L330 | none | S | Y | - | Promote scratchpad GPU driver scripts into the repo | scripts/bench/gpu_lib.sh, run_arm.sh
- L332 | gpu | L | N | Phase 1 completion | Resolve Phase-1 decision tree; conditionally build and run A5 | artifacts/architect-bench-gpu-20260720/
- L333 | gpu | L | N | Phase 1 decision + operator approval | Phase 2 tool-using planning bench on surviving arms | SWE agentic scorer
- L334 | none | S | N | Phase 1/2 results | Record architect decision, route to AXA-1 + registry | handoff, model_registry.yaml
- L462 | cpu | L | Y | needs CPU-resident Laguna role proposal; weights deleted | L-Q4P CPU config-selector + throughput sweep | artifacts/laguna-q4-cpu-v8-20260726/
- L473 | none | M | Y | - | A3-tc token-efficiency instrument via zero-inference FG-1 replay | artifacts/…/fg1-fine-grain-replay-20260727/
- L484 | none | M | Y | operator must design/ratify refusal-behavior screen | A3-ff behavioral/abliteration candidacy gate unratified | gpu-cot-scaffold-sidecar.md
- L497 | gpu | L | Y | conditional: FF/TC advances to role candidacy | FG-6 BCB-hard pre-deployment regression screen, no-think | BCB-hard suite
- L503 | gpu | L | Y | download pending + JSON tool-call parser verification | Collect and bench Qwopus3.6-27B-Coder MTP-Q8_0 same-era | model download dir
- L504 | none | M | Y | - | Zero-inference per-layer weight-delta geometry probe across finetunes | local Q8 GGUFs, new analysis script

## attention-matching-kv-compaction.md (4)
- L272 | cpu | L | N | inference-window-gated | Refresh AM validation on Qwen3.6-era long-context/coding workload | data/am_kv/
- L273 | cpu | L | N | inference window; shares P2 harness | Compare AM quality vs Expected Attention at 5x/10x/20x | data/am_kv/
- L274 | cpu | L | N | depends on P2/P3 + inference window | Test AM + Hadamard q4_0 stacking under dual compression | data/am_kv/
- L275 | none | L | Y | deferred, not yet needed | Implement true NNLS attention scoring via graph modification | llama.cpp graph path

## autopilot-authority-autoenable-proposal.md (1) — ORPHAN (no index links here)
- L99 | none | S | Y | operator approval of trust-boundary gate | Operator ruling on five trust-boundary decision points | handoff

## autopilot-continuous-optimization.md (21)
- L4 | cpu | S | N | needs E8 baseline signature (gpu-serving P0-1/P1-3) | Bring :8000 stack up and verify HEALTHY before resume | orchestrator_stack.py, autopilot_state.json
- L488 | none | M | N | - | AP-RC-1 root-cause Jul-8 silent death, add death breadcrumb | scripts/autopilot/autopilot.py
- L516 | cpu | L | Y | AP-26/27 operator gate packet | AP-26 test dspy.RLM on long-horizon autopilot benchmark analysis | src/dspy_signatures/config.py
- L517 | none | L | Y | AP-26/27 operator gate packet | AP-27 formalize T0/T1/T2 tiers as RLVR verification functions | rlvr_tiers.py, export_rlvr_environment.py
- L1068 | cpu | L | N | needs paired sentinel runs on quiet stack | BSV-2 differential behavior testing before mutation accept | bsv_paired_report.py, safety_gate.py
- L1069 | none | M | N | - | BSV-3 conflict-aware acceptance beyond observe-only ledger | scripts/autopilot/autopilot.py
- L1469 | none | M | N | AP-29 KnowledgeDistiller wiring deferred | Apply predictability + staleness gate when AP-29 is wired | knowledge_distiller.py
- L1509 | none | M | N | - | Harden keep/revert into explicit self-scoring candidate contract | autopilot.py, safety_gate.py
- L1510 | none | M | N | - | Adopt run-manifest sha256 provenance as experiment attestation | autopilot.py, controller_io.py
- L1511 | none | S | Y | - | Evaluate OpenHyra evidence-gated stop controller vs keep/revert | ?
- L1512 | none | S | Y | - | Mine orx experiment-tree lineage model for autopilot | ?
- L1513 | none | S | Y | - | Mine orx stacked-bushes tree shape and refill loop | ?
- L1523 | cpu | M | N | next stack bring-up + operator-watched window | AP-19b supervised first live gepa_optimize run | species/gepa_optimizer.py
- L1524 | none | S | Y | AP-19b live run first | AP-42 decide the gepa package pin (0.0.26 vs main) | pyproject.toml
- L1525 | none | M | Y | AP-19b live evidence | AP-21 re-open gepa_ratio decision on corrected journal facts | autopilot_state.json
- L1526 | none | M | N | - | AP-29 gate: design episodic-only control arm distiller must beat | knowledge_distiller.py
- L1529 | none | S | Y | - | AP-32 strike unmeasured +1.1% claim; guard dead linter | wiki/agent-architecture.md, strategy_store.py
- L1530 | none | S | Y | - | Retarget utility-weighted-retrieval concern to live MemRL retriever | repl_memory/retriever.py
- L1536 | none | M | N | AP-29 gate | AP-29a budget write gate to cheapest adequate local judge | knowledge_distiller.py
- L1537 | none | M | Y | - | AP-29b replay-compare lexicographic vs scalarized objective selection | autopilot_journal.jsonl
- L1538 | none | S | Y | downstream of AP-19a/19b | AP-29c name GEPA-class optimizer of record | docs/chapters/08*, gepa_optimizer.py

## autopilot-control-plane-integration.md (4)
- L18 | cpu | L | N | AP-3b source proof; spec-dec quality clearance | AP-3 register restart-scoped spec-dec + per-role KV knobs | config_applicator.py, stack_priors.py
- L21 | cpu | M | N | launch probes need llama-server | AP-3b source-prove remaining launch fields | config_applicator.py
- L23 | none | S | Y | - | AP-3b.2 decide whether draft-tree belongs in AP-3 | handoff
- L24 | cpu | M | N | server-wired EA/evict fields not source-proven | AP-3c expose Expected-Attention launch policy | config_applicator.py

## autopilot-dashboard-fidelity-audit-2026-07-22.md (9)
- L267 | none | M | Y | other-agent ownership (ESC-8 writer) | Verify manifest writer emits realized not intended lineup | runtime_facts_manifest.py
- L271 | none | M | Y | out of dashboard-file ownership | Unify env/SoT across the --workers 6 pool | scripts/server/*, launch config
- L283 | none | S | N | - | [E8-PANELS-a] Unify frontier_rerun_required vs rerun_pending_clear | src/dashboard/dashboard.py
- L286 | none | S | Y | needs operator receipt reference | [E8-PANELS-b] Commit the ratified E8 eval_quality era row | orchestration/instrument_eras.yaml
- L289 | none | M | N | owner overlap with loops-and-dashboards audit | [E8-PANELS-c] Surface absolute all_tasks_done + newly-filed series | dashboard.py, :8100 hub
- L319 | none | M | Y | - | [E8-TRIALS-COLD-GUARD] Enforce prewarm predicate on frontier evidence | frontier terminalizer, receipt schema
- L324 | none | M | N | deferred stretch | H1 circuit-breaker / forced-role-fallback dashboard panel | dashboard.py
- L325 | none | M | N | deferred stretch | H2 REL-1 eval error-rate surface | dashboard.py
- L326 | none | L | N | untouched backlog cluster | H3/M1/M3/M4/L1 contention provenance, lock SoT, lane attribution | dashboard.py

## autopilot-decision-plane-audit-2026-07-22.md (11)
- L223 | cpu | L | N | **baseline write crosses human trust boundary** | E8 baseline reseed — GATES the whole post-v8 campaign | autopilot_state.json, instrument_eras.yaml
- L285 | cpu | L | N | structured timeout provenance open | Execute only protocol-required c1 race/finalizer path | complete_e8_quality_baseline_v5_final_c1.py
- L300 | none | M | N | review vs isolation commit 79f3d2f3 | Integrate scorer isolation, then rerun bounded completion | codex/debug-scorer-isolation-20260729 branch
- L307 | none | M | N | needs scorer-isolation integration first | Resolve BigCodeBench ordinal-418 score divergence fail-closed | e8 correction ledger
- L314 | none | L | N | audit blocker at final_c1.py:139-166 | Repair producer-pin + abort-terminalization recurrence | final_c1.py:139-166
- L324 | cpu | L | N | final-C1/finalizer inference + single human apply | Collect complete v5 evidence bundle, then human-only apply | autopilot_state.json baseline_state
- L348 | none | L | Y | other owners; export_rlvr_environment.py mid-edit | Non-owned H2/H3/M1-M6/F2 audit findings | structural_lab.py, actions.py
- L398 | none | M | N | **STALE?** likely superseded by 2026-07-23 H4 deploy | Operator runs migrate-swap-flag-remeasure deploy plan | consolidate_q_append_only.py
- L399 | none | S | Y | - | Apply find-or-update to _update_escalation_memory rows | q_scorer.py, episodic_store.py
- L402 | cpu | L | N | per-token logprobs not persisted | EV-CONF-2 answer-span confidence + re-baseline math AUROC | eval sidecar writer, ESC-7 draft §5
- L483 | none | M | Y | - | Hermeticize live host lock seams and mock timing waits | test_dispatch_placement_state_machine.py

## autopilot-sequential-allocation.md (10)
- L59 | none | M | N | SEQ-A1 operator decision | Fix sticky refuted label contradicting state_name() | sequential_verdict.py, learning_exclusions.py
- L78 | none | S | Y | operator ruling (human-amendment-only) | Operator: recompute verdict per trial or keep stickiness | handoff
- L84 | none | M | N | SEQ-B1 operator decision | Resolve unreachable joint quality-rate promotion gate | autopilot.py:1953-1966
- L99 | none | S | Y | operator ruling (trust boundary) | Operator: joint gate or rate axis advisory | handoff
- L109 | cpu | L | N | E8 era mismatch; choose SEQ-3a/3b | Resume candidate 70902e4b to a sequential verdict | autopilot_journal*.jsonl
- L122 | cpu | L | N | operator era-comparability ruling | Bridge era and spend ~10 trials to verdict | instrument_eras.yaml
- L127 | cpu | L | N | E8 quality-baseline reseed ratification | Restart candidate at k=0 under E8, ~49 trials | autopilot_journal*.jsonl
- L137 | none | M | N | SEQ-A1 operator decision | Pointer: sticky refuted label | sequential_verdict.py
- L138 | none | M | N | SEQ-B1 operator decision | Pointer: frozen baseline-promotion gate | autopilot.py
- L139 | none | M | Y | - | Re-examine 9 candidates refuted by allocation heuristic | readjudicate_sequential_candidates.py

## backlog-roi-audit-2026-07-14.md (5)
- L15 | cpu | M | Y | re-baseline window for affected suites | RE-1 flip math suites to math_verify and re-baseline | eval-tower-verification.md, question_pool.py
- L16 | none | M | Y | - | RE-2 execution-free patch verifier as coder_escalation pre-gate | src/gate_runner.py
- L17 | cpu | M | Y | Augment v1 145-bug golden set acquisition | RE-3 build local review-finding-F1 code-review suite | scripts/benchmark/
- L18 | cpu | L | Y | clean-window package; RE-4 protocol gates | RE-4 LongCoT-Mini calibration run on local models | bulk-inference-campaign.md, re4-protocol-redesign.md
- L19 | none | S | Y | F1-DGM scoping window | RE-5 fold Simula double-critic into F1-DGM scoping | frontier-f1-real-task-corpus.md

## batched-decode-measurement.md (6)
- L26 | cpu | L | N | operator quiet window; post-v7 queue | **E5** NUMA x batch 2D interaction sweep | server_numa_np_sweep.py, e5_cell_manifests.py
- L520 | none | S | N | operator (human-amendment-only) | Operator decision on era row for throttle gate rescope | instrument_eras.yaml, MEASUREMENT.md
- L521 | cpu | M | N | operator quiet window | W2 focused post-fix generated-answer capture smoke | server_numa_np_sweep.py
- L522 | cpu | L | N | operator quiet window; W2 smoke (reboot done) | **E5 W1-W4** Stage-B decision-grade runs | data/batched_decode/e5_pre_reboot_20260728/
- L537 | none | M | Y | needs E5 mapping data | Decide eval-batch serving lane: none, CPU fleet, or MI210 | heterogeneous-slot-fabric-residency.md
- L706 | none | S | N | - | C4 relabel C1 as provisioning candidate, refresh waypoint prose | handoff

## batched-edit-parallel-apply.md (4)
- L38 | cpu | L | Y | inference-gated; only if answer changes keep/retire | BEP-2/J8 batch-edit vs interleaved Root LM CPU latency A/B | src/batch_edit_runner.py
- L39 | none | M | Y | BEP-2 positive result | BEP-3 expose batch-vs-interleaved as autopilot knob | species/StructuralLab, src/config features
- L41 | none | L | N | safety-gated design review | BEP-5 generalize sandbox-before-disk, per-file accept/reject | src/batch_edit_runner.py, batch_edit.py
- L43 | cpu | M | N | inference-gated, opt-in | BEP-4 cheap-worker LM repair lane when apply fails | batch_edit_runner.py, graph/helpers.py

## benchmark-results-dashboard.md (7)
- L47 | none | S | Y | - | Enumerate models on the system from both registries | dashboard/, model_registry.yaml x2
- L48 | none | L | N | - | Ingest summary/results artifacts into a per-model view | dashboard/ ingest module
- L50 | none | L | N | - | Filterable table + per-model drill-down page on :8100 | dashboard/server.py, static/
- L51 | none | M | N | - | Tag every number with MEASUREMENT grade and kernel/era | dashboard render, instrument_eras.yaml
- L53 | none | S | N | - | Handle sparse benchmark coverage gracefully | dashboard ingest+render
- L58 | none | L | Y | Phase 1 ingest layer | Persist ingested results into a queryable SQLite store | dashboard/ SQLite store module
- L59 | none | M | N | Phase 2 store (L58) | Backfill archival database from existing artifacts | dashboard/ store module

## bep-dcp-falsification-harness.md (3)
- L19 | cpu | L | N | host-quiet boundary; attestation warnings | Clear attestation warnings then run DCP-6 inference gate | dcp_j7_ab.py, attestation/latest.md
- L20 | cpu | L | N | optional; only if batch-edit keep/kill needed | J8 legacy batch-edit vs interleaved-REPL A/B | bep_ab.py, data/bep_sandbox/
- L21 | none | S | Y | - | Keep production rollout decisions out of this handoff | handoff, multi-file-coding-…md

## bulk-inference-campaign.md (5)
- L87 | cpu | L | N | clean window + RE-4 protocol repair | LongCoT-Mini ~500-easy calibration run | longcot_mini_adapter.py
- L185 | none | S | Y | operator decision + post-v8 architect verdicts | MiniMax-M2.7 227GB keep-vs-delete decision | models/MiniMax-M2.7-GGUF/
- L624 | cpu | M | N | **operator gate OP-6(a)+(b)** | RCP-W1 reference-lineup relaunch, preflight, flag propagation | orchestrator_stack.py, affinity_preflight.py
- L625 | cpu | L | N | RCP-W1 | RCP-W2 paired shadow-OFF/ON 50-question replay | data/trace/events.sqlite, src/trace/query.py
- L626 | cpu | L | N | RCP-W1 | RCP-W3 RC-8 shadow smoke over 100-200 near-miss rows | reviewer_calibration_report.py

## capability-registry-and-promotion.md (2)
- L24 | cpu | L | N | evidence-plane-ledger gate | Build safe role-restart applicator with health gate + rollback | config_applicator, orchestrator_stack.py
- L25 | none | M | N | W3 applicator; shadow attestation ledger | Monthly promotion pass on first-cohort capability rows | capability_registry.yaml

## colbert-reranker-web-research.md (10)
- L263 | none | M | N | AR-3 irrelevant-page gate (NO-GO 2026-06-12) | Flag-gated ColBERT snippet reranker in web_research | src/tools/web/research.py, colbert_reranker.py
- L269 | cpu | M | N | S5 implementation | A/B reranked vs DDG-order on web_research questions | analyze_web_research_baseline.py
- L283 | cpu | L | N | S5/S6 confirming reranker value | Surprisal-based page chunking feeding ColBERT MaxSim | research.py, llama.cpp /tokenize
- L407 | cpu | M | N | LateOn INT8 export run deferred | Benchmark LateOn CPU latency vs GTE-ModernColBERT | bench_colbert_rerank.py
- L408 | cpu | M | N | AR-3 Package D data accumulation | A/B LateOn vs current model on sentinel queries | bench_colbert_rerank.py
- L409 | cpu | M | Y | BGE-small retention bottleneck trigger | Evaluate DenseOn for probe-first pool retention | colbert_reranker.py
- L422 | cpu | M | N | LateOn INT8 export execution | Re-run CPU latency benchmark with LateOn INT8 | bench_colbert_rerank.py
- L423 | none | M | Y | - | Write xxhash64 13-gram decontamination protocol script | decontaminate_against_embeddings_training.py
- L424 | cpu | M | N | AR-3 Package D + S7 decontamination | A/B LateOn vs GTE on decontaminated sentinel queries | bench_colbert_rerank.py
- L430 | gpu | L | Y | DGX Spark GPU availability + S5 stable | Local NV-Retriever fine-tune on REPL/sentinel queries | fine-tune scripts (unwritten)

## context-folding-progressive.md (18)
- L17 | cpu | L | Y | production-question gate | L5 single-sentence compression check vs L3 sweet spot | scripts/benchmark/, session_summary.py
- L18 | cpu | L | N | flags off + P3d anti-thrashing | Validate CompactionQualityMonitor on live traffic telemetry | session_log.py, session_summary.py
- L84 | none | S | Y | - | Frame CF-3c A/B around observation-dropping-first ordering | handoff
- L85 | none | S | N | superseded by L111 | Add give-up / uncertain-incorrect compaction-quality dimensions | session_log.py
- L86 | cpu | M | Y | owned by reasoning-compression.md | Test keep_k_latest_wo_reasoning arm | context_compression.py
- L109 | none | S | N | **STALE?** already landed 921f71d1 | Fix inverted reference-miss detector to use granular_blocks | session_summary.py
- L110 | none | M | N | flags off (inert until enabled) | Persist CompactionQualityMonitor into state projection + writer | langgraph/state.py, session_log.py
- L111 | none | M | N | - | Join give-up + no-answer/max-turns detectors to compaction state | pipeline_monitor/anomaly.py
- L112 | cpu | L | Y | needs working compaction telemetry | 2xk sweep of TOOL_OUTPUT_AGE_THRESHOLD and summary half | context_compression.py
- L113 | none | S | Y | - | Record do-not-prioritize decision for ContextRot replication | handoff
- L114 | none | S | N | - | Record correction: BGE self-hosting claim was wrong | handoff, research/intake_index.yaml
- L132 | none | S | N | operator decision | Flip role_aware_compaction + helpfulness_scoring to shadow | src/features.py
- L138 | cpu | L | Y | CF-3c A/B harness | Add observation-masking/truncation anchor arm to CF-3c | context_compression.py
- L139 | cpu | L | Y | CF-3c A/B harness | Add ACM Base agent-initiated-trigger arm with context meter | context_compression.py, prompts/
- L140 | cpu | M | Y | ACM Base arm (L139) | Run ACM's unreported re_mem_noquery ablation | scripts/benchmark/
- L141 | none | S | N | non-termination counter (L111) | Pair any ACM/AREX adoption with non-termination counter | pipeline_monitor/anomaly.py
- L142 | none | S | N | - | Record AREX +11.8pt ACU figure as non-citable triple confound | research/intake_index.yaml
- L143 | none | S | N | - | Record ARC-AGI-3 provenance downgrade for intake-919 | research/intake_index.yaml

## core-v2-design-note-2026-07-23.md (6) — ORPHAN
- L157 | none | M | Y | operator (human-owned) | Operator reviews core_v2 items, vl inclusion, stale vl era row | core_v2.jsonl, instrument_eras.yaml
- L161 | none | S | N | operator (human-amendment-only) | Append E4-quality-core-v2 era row with activation timestamp | instrument_eras.yaml
- L185 | none | S | Y | era-row append (L161) | Re-run promotion validator; expect promotion_ready true | core_v2_promotion_report.py
- L188 | cpu | S | N | validator promotion-ready (L185) | Launch autopilot with AUTOPILOT_T1_CORE_ID=core_v2 | scripts/autopilot/
- L192 | cpu | S | N | launch step (L188) | Restart running process so it picks up new env | orchestrator_stack.py
- L193 | cpu | S | N | restart + first T1 trial | Verify live eval_details shows core_id core_v2, n=50 | eval_tower.py

## cpu-inference-optimization-index.md (8) — index pointers; work lives in owning handoffs
- L120 | cpu | L | N | quiet window; per-model B1-B5 evidence | P0 iqk IQ-quant enablement build + coherence/speed gates | iqk-iquant-enablement.md
- L121 | none | M | N | must not block B5 | P1 scope iqk 1bit family un-stub cost for Hy3-IQ1_M | iqk-iquant-enablement.md
- L122 | cpu | L | N | tree cannot produce or load KT GGUF | P2 gate IQ4_KT vs Q4_K_M before any trellis port | iqk-iquant-enablement.md
- L123 | cpu | L | Y | quiet window before default path change | P0 capture EvalTower telemetry for batched decode E2/E3 | eval_batch_serving_evaltower_window.py
- L126 | none | S | Y | only if legacy DeepSeek V3.2/GLM-5.1 in scope | MED refresh DSA PR #21149 snapshot | llama-cpp-dsa-contribution.md
- L128 | cpu | L | Y | clean-window protocol; operator bench approval | P1 claim-grade AMD perf-counter CPU roofline benches | cpu-kernel-env-flags-inventory.md
- L129 | cpu | L | Y | needs staged immutable on/off binary pair | P1 reopen frontdoor Q8_0 barrier-count fusion A/B | cpu-shape-specialized-gemv-decode.md
- L130 | cpu | M | Y | deprioritized; falsification-gate only | P2 keep xGMI KV-transfer falsification gate active | numa-prefill-decode-disaggregation.md

## cpu-prefill-compute-large-models.md (1)
- L152 | cpu | L | N | check current v7 promotion branch state first | PC-4 experimental qwen35 prefill barrier/graph-fusion prototype | llama.cpp-experimental qwen35.cpp

## cpu-shape-specialized-gemv-decode.md (38) — NOTE: whole SIMD lever is deprioritized (E3 NO-GO)
- L515 | none | S | Y | SIMD lever deprioritized | Read justine.lol/matmul, extract Zen 4 Q8_0 ukernel pattern | research/deep-dives/
- L516 | none | S | Y | SIMD lever deprioritized | Read Gope arXiv:2501.00032, extract GEMV register blocking | research/deep-dives/
- L518 | cpu | L | N | SIMD lever deprioritized | Rebuild with GGML_USE_LLAMAFILE on/off, record tok/s delta | llamafile/sgemm.cpp
- L519 | cpu | M | N | perf not installed on host | Profile matmul vs DeltaNet vs norm time, IPC, cache hits | ggml-cpu.c, GGML_PERF build
- L530 | cpu | M | N | Phase 0 gate | Standalone matmul benchmark harness | ukernel-bench.cpp
- L531 | none | L | N | SIMD lever deprioritized (E3 NO-GO) | Implement templated AVX-512 ukernel, register-block 1x32/1x16 | zen5-ukernel.cpp
- L533 | none | M | N | needs ukernel (L531) | Integrate as ggml op override behind EPYC_UKERNEL_MLP_UP | ggml-cpu.c, zen5-ukernel.cpp
- L535 | cpu | S | N | needs Phase 1 measurement | Gate: proceed at >=1.15x, abandon below 1.10x | data/cpu_optimization/
- L543 | none | L | N | Phase 1 gate | Ukernels for remaining four Qwen3.6-27B shapes | zen5-ukernel.cpp
- L544 | cpu | L | N | Phase 1 gate | Q4_K_M dequant-into-FMA variants, per-shape perf | zen5-ukernel.cpp
- L545 | none | M | N | needs ukernel set | Shape-dispatch table keyed on K,N,quant_type | ggml-cpu.c
- L546 | cpu | M | N | needs full coverage | Benchmark end-to-end decode at full coverage | data/cpu_optimization/
- L547 | cpu | L | N | needs full coverage | Correctness battery: WikiText-2 PPL, MMLU, SWE-bench mini | benchmarks/
- L548 | cpu | M | N | quiet window | Verify no thermal downclock over 30min sustained load | data/cpu_optimization/
- L549 | cpu | M | N | quiet window | Verify NUMA 4-way aggregate throughput also scales | stack_numa.py
- L550 | none | S | N | needs Phase 2 data | Gate: 1.5x decode + correctness tolerance | handoff
- L558-L561 | none | L | N | Phase 2 gate | Ukernels for 35B-A3B MoE / Coder-30B / Coder-480B / SG4+M2.7 | zen5-ukernel.cpp
- L562 | none | M | N | Phase 2 gate | Merge ukernel work into production-consolidated branch | llama.cpp production branch
- L563 | none | S | Y | Phase 2 gate | Update orchestrator_stack.py for quant-format changes | orchestrator_stack.py
- L564 | cpu | L | N | quiet window | Full regression sweep across all production models | data/cpu_optimization/
- L565 | none | M | Y | Phase 2 gate | Document ukernel catalog and code-gen pattern | docs/, research/deep-dives/
- L573 | none | S | Y | Phase 3 complete | Open llama.cpp discussion with our benchmark data | ?
- L574 | none | M | Y | Phase 3 complete | Upstream PR for ukernel registry/dispatch infrastructure | ggml-cpu.c
- L575 | none | L | N | PR L574 first | Upstream PR for model-specific shape kernels | zen5-ukernel.cpp
- L576 | none | S | Y | external party | Coordinate with Justine Tunney if tinyBLAS upstream-blocked | ?
- L721 | none | S | Y | - | Re-read handoff end-to-end incl. 2026-04-23 audit block | handoff
- L722 | none | S | Y | - | Check master + CPU indices for status changes | master-handoff-index.md
- L723 | none | S | Y | - | **READY** Check llama.cpp upstream for new CPU ukernel PRs | (research)
- L724 | none | S | Y | - | **READY** Check for new Justine Tunney tinyBLAS Zen 5 benchmarks | (research)
- L725 | none | S | N | - | Anchor experimental worktree on production branch before starting | /mnt/raid0/llm/llama.cpp-experimental
- L726 | cpu | M | N | SIMD lever deprioritized | Measure tinyBLAS on/off as first Phase 0 step | llamafile/sgemm.cpp
- L727 | none | S | Y | - | **READY** Confirm TIDE early-exit code paths dormant | fork commits 143ded626 etc
- L728 | cpu | L | N | quiet window | Run Phase 0 baseline measurements | data/cpu_optimization/
- L729 | none | S | Y | - | Start new progress entry before Phase 1 work | progress/YYYY-MM/
- L730 | none | S | N | - | Update handoff Status field as phases close | handoff

## decision-aware-routing.md (36) — DAR-3/4/5 rescoped to triage gate; most rows gated on reward redesign
- L118 | none | M | N | DAR-3 rescoped (superseded) | Implement SPO+ decision-aware loss | q_scorer.py, retriever.py
- L123 | none | S | N | **explicitly forbidden** 2026-07-21 (L492) | Add 10% epsilon-greedy exploration | retriever.py L225-368
- L124 | cpu | L | N | superseded — 386K counterfactuals already in store | Accumulate counterfactual outcomes across 2+ models | episodic_store.py
- L125 | none | M | N | DAR-3 rescope + reward redesign | Replace TD update with SPO+ gradient | episodic_store.py, q_scorer.py
- L126 | cpu | M | N | needs DAR-3 implementation | Measure routing accuracy/quality/latency/Q convergence | scripts/analysis/
- L127 | none | S | N | DAR-3 frozen | Wire exploration flag to staged_scorer bonus | retriever.py
- L133 | none | L | N | retrain-on-fixed-reward precondition | Replace per-action Q with bilinear scorer | bilinear_scorer.py
- L137 | none | S | N | needs DAR-4 scorer skeleton | Expose six model features to bilinear scorer | q_scorer.py ScoringConfig
- L144 | none | M | N | - | Create new bilinear_scorer.py module | bilinear_scorer.py
- L145 | none | M | N | needs bilinear_scorer.py | Switch retriever selection to bilinear scorer | retriever.py
- L146 | none | M | N | needs DAR-4 scorer | Simulated-new-model cold-start convergence test | tests/unit/test_bilinear_scorer.py
- L147 | none | S | N | needs DAR-4 scorer | Zero cold-start from spec features for new models | bilinear_scorer.py
- L162 | cpu | M | Y | inference availability | Live omega-sweep routing shift + latency-quality Pareto | reports/dar4b_sweep_*
- L182 | none | L | N | gated behind reward redesign | Learned d-dim model identity vector | bilinear_scorer.py
- L183 | none | M | N | needs DAR-5.2 | Concatenate IRT 2-D output onto BGE embedding | irt_scorer.py
- L184 | none | M | Y | needs DAR-5.2/5.3 | Offline A/B versus frozen DAR-4 on val set | scripts/analysis/
- L185 | none | S | Y | - | **READY** Document cold-start note for LRC P5 onboarding | learned-routing-controller.md
- L213 | none | M | Y | DAR-6 frozen per fable5-findings-02 | Build 0-1 injection-risk trigger score for fanout | src/classifiers/
- L216 | cpu | L | N | inference gate J14 + operator approval | Two-arm injection-suite A/B: escalation vs swarm fanout | src/swarm_fanout.py
- L409 | cpu | L | N | eval-tower P8 calibration gate + J10 | Calibrated uncertainty escalation signal orthogonal to Q | difficulty_signal.py
- L410 | none | M | Y | shared trace schema (unified-trace EXM-3) | Persist escalation/approval decisions as harness state | trace store schema
- L411 | none | M | N | URE-1 calibration quality | Feed calibrated uncertainty back as routing feature | difficulty_signal.py
- L455 | none | M | N | - | Add cache_affinity_bonus and cold re-prefill penalty | q_reward.py, retriever.py
- L456 | none | M | N | - | Session-sticky routing state + per-request hybrid | routing.py
- L457 | none | L | N | - | Make action space model x thinking-level | routing.py, q_scorer.py
- L489 | none | S | Y | operator ruling (human-amendment-only) | Operator defines which regret the 5% gate means | handoff
- L492 | none | S | Y | - | **READY** Standing prohibition: no epsilon-greedy counterfactual manufacture | handoff
- L534 | none | S | N | - | Re-scope DAR-3/4/5 as triage gate, not policy | handoff
- L536 | none | M | N | - | Design graded reward on the decisive subset | repl_memory/q_reward.py
- L549 | none | M | N | - | Redesigned reward must carry speed axis | repl_memory/q_reward.py
- L612 | none | M | N | needs protocol id for p50/p90 baselines | Add wall-clock task-duration reward term | q_reward.py
- L613 | none | S | Y | - | **READY** Record instrument-era boundary for reward values | instrument_eras.yaml
- L614 | none | M | Y | - | Optional replay-rescore of historical episodic rows | scripts/analysis/, episodic.db
- L625 | none | L | N | needs post-fix reward corpus accrual | Retrain DAR-4 bilinear predictor on fixed reward | bilinear_scorer.py
- L626 | none | L | N | reward redesign | DAR-5 gated behind reward redesign | irt_scorer.py
- L636 | none | M | N | - | Split stage field out of producer_role | progress_logger.py, q_reward.py

## deepseek-v4-flash-cpu-port.md (4)
- L442 | none | S | Y | operator decision; needs D2 floor | Operator go/park on Strategy-A API translation | handoff, ik_llama feature/deepseek4-port
- L443 | none | M | Y | - | Recalibrate 18 t/s floor to V4-arch-aware baseline | handoff, bench_canonical.sh
- L444 | cpu | M | N | Mac/ds4 reference logprobs | Repurpose quality gate as architect_general candidacy probe | v4 quality gate script
- L445 | none | M | N | external reference host (Mac/ds4) | Unblock quality gate on external reference logprobs | v4 quality gate script

## delegation-context-preassembly.md (2)
- L46 | cpu | L | N | host-quiet window; AutoPilot stopped | DCP-6 larger quality-scored live A/B before enablement | dcp_j7_ab.py, context_discovery.py
- L102 | cpu | L | N | DCP live A/B already latency-unfavorable | Add ColBERT KB as gated prior-decisions source | context_discovery.py, context_assembly.py

## delta-mem-reproduction.md (4)
- L215 | gpu | L | N | GPU availability (CPU-infeasible) | Gate 2 MemoryAgentBench accuracy reproduction | MemoryAgentBench harness
- L216 | gpu | L | N | GPU availability | Gate 3 wider LoCoMo eval, 25-50 samples | LoCoMo eval harness
- L217 | cpu | L | N | Gate 2/3 magnitude evidence | Phase 2 KV-extension prototype and A/B vs B1 | M.3 prototype, SQLite B1 store
- L218 | cpu | L | N | Phase 2 outcome | Phase 3 full GGML op and cross-session bank | ggml delta-mem op

## document-parser-table-bench.md (16)
- L52 | none | S | Y | download pending | Trigger PP-DocLayoutV3 weight resolution, record cache path | venvs/paddleocr
- L53 | cpu | S | Y | Phase-A weight download | Confirm CPU-only layout stage works on EPYC | venvs/paddleocr
- L56 | cpu | S | N | operator approval (Phase B) | Start experimental-v7 llama-server with PaddleOCR GGUF+mmproj | models/PaddleOCR-VL-1.6-GGUF
- L57 | cpu | M | N | Phase-B server start + operator approval | Run documented pipeline on table-bearing pages | odl_bench/paddleocr_vl.py
- L59 | none | S | N | Phase-B smoke run | Gate: confirm HTML table markup actually emitted | odl_bench outputs
- L60 | cpu | S | N | Phase-B smoke run | Capture K35 cleanup proof: no stray server, no KFD | ?
- L63 | cpu | L | N | operator approval + Phase B gate | Re-baseline ODL end-to-end on full 1651-page set | odl_bench/, omnidocbench
- L64 | cpu | L | N | operator approval + Phase B gate | Score PaddleOCR-VL-1.6 full pipeline on same set | odl_bench/paddleocr_vl.py
- L65 | none | M | N | Phase-C runs | Report all-language and English-only splits per metric | odl_bench compare-existing
- L66 | none | M | N | Phase-C runs | Report table TEDS n=665 + edit-distance metrics | odl_bench scorer reports
- L67 | none | S | N | Phase-C runs | Persist results via odl_bench compare-existing | data/odl_existing_comparison/
- L70 | none | S | Y | Phase C English-only table TEDS | Decide table path: ODL, hybrid, or PaddleOCR wholesale | handoff
- L71 | none | M | Y | Phase-D decision | Consider MinerU2.5-Pro / GLM-OCR only if PaddleOCR underperforms | handoff
- L72 | cpu | L | Y | - | Domain-transfer check on real orchestrator-ingested PDF corpus | odl_bench/, local PDF corpus
- L144 | none | S | Y | - | **READY** Guardrail: no MinerU/GLM-OCR downloads as odl_bench swaps | ?
- L145 | none | M | Y | PaddleOCR-VL pipeline proof | Scope MinerU2.5-Pro-2605 as separate pipeline-harness project | ?

## dynamic-stack-concurrency.md (6)
- L31 | none | L | N | DS-E1-equivalent evidence trigger (parked) | Implement QuarterScheduler dynamic quarter reassignment | concurrency_aware_backend.py
- L35 | cpu | L | Y | attention-matching-kv-compaction P2 validation | Prototype q4_0 KV offset estimation for shared-codebase contexts | KVCOMM prototype (new)
- L36 | none | L | N | DS-F1 passing | Design anchor pool + wire cache-aware routing plus metrics | concurrency_aware_backend.py
- L42 | none | S | Y | operator root edit + systemctl restart | Add claude/codex to earlyoom --ignore regex | /etc/default/earlyoom
- L43 | none | S | N | - | Decide whether pause-model-loads-after-kill hook is worth wiring | orchestrator_stack.py
- L44 | none | S | N | - | Decide whether a pre-kill -P remediation hook is safe | orchestrator_stack.py

## engram-conditional-memory.md (6)
- L377 | cpu | L | N | co-owned with unified-trace-memory-service store/schema | Layer CORE utility-aware retrieval over ReasoningBank schema | src/trace retrieval module
- L378 | cpu | M | N | depends on retrieval design (L377) | Make k budget-conditional; sweep with no-memory control arm | retrieval sweep harness
- L379 | none | S | Y | - | **READY** Correct the ReasoningBank ranking claim in retrieval notes | handoff, unified-trace-memory-service.md
- L385 | gpu | L | N | GPU budget authorization; gfx90a training viability | Allocate GPU, run frozen-vs-cotrained SmolLM-1.7B proxy | engram package, training driver
- L386 | gpu | L | N | needs GPU allocation (L385) | Build canonicalizer, train both configs, 30% recovery gate | scripts/build_canonicalizer.py
- L387 | gpu | L | N | Gate B0 pass required | File retrofit spike handoff, start Qwen3.6 Phase 1-4 surgery | engram-retrofit-qwen36-spike.md

## episodic-memory-integrity.md (4)
- L130 | cpu | M | N | needs ~2,000 fresh post-reseed trajectories | M-11a first re-distil of SkillBank with teacher LLM | seed_skills.py, autopilot/actions.py
- L153 | none | M | Y | coordinate with repl-session-memory-maturity | M-11a2 wire work-payload capture at live write sites | q_scorer.py, memory_record.py
- L178 | none | M | Y | post-reseed data accumulation | M-15 reopen intake-866 COMP_r under correct id_map resolution | faiss_store.py, COMP_r probe
- L316 | cpu | L | N | needs reseeded store + live traffic | M-12 memory-on vs memory-off A/B that never existed | episodic_store.py, benchmarks/

## ernie-image-turbo-evaluation.md (5)
- L139 | none | S | Y | - | **READY** Record LongText-Bench harmonized ranking in deep dive | research/deep-dives/ ernie
- L142 | cpu | M | N | inference window / operator approval | Run content-filter audit live and review outputs | content-filter audit harness ed6f65f5
- L143 | cpu | M | N | inference availability | 20-prompt EN/ZH typography spot-check vs 0.9655 claim | spot-check prompt set
- L144 | gpu | L | N | MI210 window | GPU rebench of 8-step distilled DiT on MI210 | ROCm/HIP DiT path
- L145 | none | S | Y | product requirement decision | Re-litigate FLUX.1-schnell alternative if bilingual unneeded | handoff

## eval-benchmark-cost-reduction.md (2)
- L64 | cpu | L | Y | Harbor adapter + TB Core baseline | MR difficulty filter needs Harbor adapter and baseline | Harbor/Terminus adapter, TB Core tasks
- L77 | none | M | N | EV-11 math re-baseline; EV-11b ECE operator decision | Promote screen_paired_arms McNemar to decision-gating recipe | eval_tower.py, entries/20-eval-tower.yaml

## eval-tower-architecture-audit-2026-07-20.md (5)
- L275 | none | M | N | loop agent research-repo landing | Close question_pool shadow surfaces for deterministic module identity | question_pool.py, dataset_adapters.py
- L315 | none | M | N | A3-era pool rebuild (after A2) | Finish loader accounting with A3-era pool rebuild invariant | dataset_adapters.py, question_pool.py
- L336 | none | L | N | loop agent queue | Extract concurrency ladder, import bootstrap, rubric parsing seams | eval_tower.py, stat_tests.py
- L338 | none | M | N | SCORE-07 clamp rides B7 sign-off | Repair SCORE-07 clamp + bug-enshrining scorer tests | tests/unit/test_eval_tower_*.py
- L341 | none | L | N | - | **E5 [agent] LOWs sweep** — twelve remaining LOW findings | eval_tower.py, stat_tests.py, rlvr_tiers.py

## eval-tower-loop-robustness-audit-2026-07-20.md (2)
- L140 | cpu | L | N | **E8 quality baseline must be sealed**; operator-authorized run | H2.v8 remeasure six-role contention matrix under frozen v8 | contention_matrix.yaml, contention_matrix.py
- L143 | none | M | Y | operator owns final confidence/gating decision | Neutralize constant-0.0 ECE/AUC as observation-only | eval-tower-verification.md

## eval-tower-verification.md (28)
- L180 | cpu | L | N | v7 contention-matrix recertification | EV-4 decision-grade HE-R+ calibration baseline | eval_tower.py, eval ledger
- L183 | none | M | Y | - | **READY** Choose rebaseline wall-clock protocol option | MEASUREMENT.md, eval_tower.py ladder
- L185 | cpu | L | N | chained behind EV-11c window | Rerun calibration axes on Option-A code-execution scorer | eval_tower.py, HE-R+ artifacts
- L186 | none | S | N | needs EV-4b + EV-11c data | Identify which question types produce miscalibrated confidence | eval_tower.py, calibration reports
- L187 | none | S | N | needs EV-4b | Record baseline as comparison point for verification improvements | eval ledger
- L193 | cpu | M | Y | no GGUF; needs convert_hf_to_gguf | EV-5 download ThinkPRM-1.5B, quantize to Q4_K_M | convert_hf_to_gguf.py
- L194 | none | S | N | needs EV-5 download | Add sequential-load ThinkPRM server config | orchestrator_stack.py
- L195 | none | L | N | needs download + server config | Implement T2 uncertain-question process-verification pass | eval_tower.py (eval_t2)
- L200 | none | S | N | needs EV-5 wiring | Enforce ThinkPRM family differs from evaluated model family | eval_tower.py check_cross_family
- L217 | cpu | L | N | Ouro P7 validation | EV-7 integrate Ouro-2.6B as T0 sentinel verification candidate | eval_tower.py, model_registry.yaml
- L251 | cpu | L | N | inference availability | EV-8 one-day diversity baseline 4 roles x 20 prompts x 4 completions | autopilot_baseline.yaml, tools/diversity/metrics.py
- L257 | cpu | L | N | deferred; needs EV-8 baseline | Temperature-ladder experiment + CoT-suppression ablation | tools/diversity/metrics.py
- L413 | cpu | L | N | K-SKILL-1 deploy window | EV-10 deploy/restart + paired-mutation A/B for skill-efficacy gate | skill_efficacy.py
- L414 | cpu | M | N | inference-gated verifier-session authoring | Wire surrogate-verifier assertion authoring producer path | skill_efficacy.py
- L427 | cpu | L | N | EV-CONF + architecture-audit Phase A | EV-11 fresh math re-baseline at prod temp+seed42, era-labeled | eval_tower.py, Wave-3 manifest
- L429 | cpu | M | N | EV-13b run leg | EV-13 review-finding-F1 suite parent | benchmark/review_f1/
- L431 | cpu | L | N | Augment-v1 golden-set download + batch manifest | Run review-F1 harness on local models with judge-swap | review_f1/assemble_golden_set.py
- L487 | none | S | Y | operator gate (eval trust boundary) | Adopt anchor rule pairing judge metrics with independent verifier | MEASUREMENT_POLICY.md
- L488 | none | S | Y | operator gate (eval trust boundary) | Adopt de-anchoring rule for judges used in selection | MEASUREMENT_POLICY.md
- L489 | cpu | M | N | operator-review gate | Dual-judge offline audit: clean vs bias-augmented rubric gap | rubric_scoring.py, judge prompts
- L490 | none | M | Y | operator-review gate | Extend bias probe set with CHERRL families + exploitability axis | judge bias probe set
- L491 | none | M | Y | operator-review gate | Retro-check best-of-N gains resting on judge-only scores | autopilot journal, analysis script
- L497 | cpu | L | N | inference-batch loop slot | Offline A/B: show-candidate vs commit-first judge FPR | judge harness, stat_tests.py
- L498 | none | S | Y | three absent-source suites download (operator ask) | Attach web-egress check to any GAIA eval run | suites.py, dataset_adapters.py
- L500 | none | L | N | E5 NUMA x batch mapping; next EV-4-class run | Node-partitioned cross-fleet arm-parallelism for rebaselines | eval runner, contention_matrix.yaml
- L522 | none | S | Y | - | **READY** Unify autopilot 2nd McNemar producer onto verdict_from_result | autopilot.py:1431, paired_stats.py
- L545 | cpu | M | N | needs EV-10a gate live | Single-artifact admission prefilter re-attempting originating failure | skill_efficacy.py
- L546 | cpu | L | N | dataset acquisition + exec-sandbox harness | FrontierCS 10-problem floor probe on one production arm | new FrontierCS adapter, suites.py

## evidence-plane-event-sourcing-and-narrative.md (2)
- L80 | cpu | M | N | controlled AutoPilot restart window | W3 demonstrate bounded startup cost after controlled restart | journal_snapshot_replay.py
- L83 | none | M | N | - | W6 remaining strategy-consumer audits before provenance closure | strategy_store.py, strategy_projection_report.py

## evidence-plane-instrument-repair.md (3)
- L93 | none | M | N | operator-owned E4/core era promotion | Promote core_v2 via E4 era row decision | instrument_eras.yaml, core_v2_promotion_report.py
- L94 | cpu | L | N | needs alarm-free live audit evidence | Collect clean W6 rotating-audit evidence before overfit claim | eval_tower.py, audit_block_report.py
- L96 | cpu | L | N | needs keepable replayable candidate | Wire promotion evals; confirm candidate with fresh stratified draw | eval_tower.py, planner evidence

## evidence-plane-ledger-and-sequential-verdicts.md (1)
- L337 | cpu | L | N | **P0 rate-axis era-fence amendment operator signature** | W8b live keepable candidate + sequential/promotion evidence | sequential_verdict.py, planner_evidence.py

## fable5-window2-findings-03-portfolio-and-master-queue.md (12)
- L65 | none | S | Y | operator ratification | Ratify P-GPU-1 measurement protocol | MEASUREMENT.md
- L66 | gpu | L | Y | - | Canonical-tree HIP build + qwen35moe/qwen3next op-coverage smoke | llama.cpp/build-hip/
- L67 | gpu | L | N | G1 ratification + G2 build | Frontdoor GPU residency bench feeding Gate-R | scripts/benchmark/, model_registry.yaml
- L69 | none | M | Y | - | Rebuild core_v2 selection from ledger; demote calibration lineage | core_v2_select.py, instrument_eras.yaml
- L70 | none | M | Y | - | Run DAR-1 regret replay over live evidence ledger | src/autopilot_core/
- L71 | cpu | L | Y | owner: evidence-plane-ledger handoff | Produce W8 promotion-eval evidence tail | eval_tower.py, sequential_verdict.py
- L75 | none | L | Y | gate: G3 >=1.8x | Orchestrator GPU plumbing: device block, launch args, attestation | model_registry.yaml, orchestrator_stack.py
- L76 | gpu | L | N | GPU window | Architect ncmoe sweep, op-offload prefill probe, batch-K curve | llama.cpp common/arg.cpp
- L77 | cpu | M | N | 1-2h quiet window | 33-flip-item discriminating re-run at conc 1 vs 3 | scripts/benchmark/, reports/
- L80 | none | M | Y | Gate-R decision (G3) | Re-plan campaign post-Gate-R with substrate field | bulk-inference-campaign.md
- L81 | cpu | L | N | after W8 (N2-tail) | Run accept-path bundle per-item, flag-isolated | safety_gate.py
- L82 | cpu | L | Y | Gate R | Held levers: E3 GEMM SIMD, MoE-Spec CPU Phase-0, sarathi re-read | ggml/src/ggml-cpu/

## fable5-window2-findings-05c-mi210-lever-category-matrix.md (22) — 9 taxonomy rows all edit THIS file
- L199 | gpu | M | N | **STALE?** superseded by a8afd338 measured-negative | Re-run n-gram/prompt-lookup spec-dec on GPU | common/speculative.cpp
- L201 | gpu | M | N | L14 scoped DEFER, rider-only GPU window | KV-quant single-stream 64k long-context measurement | ?
- L204 | gpu | L | N | needs trained EAGLE-3 head | Train/relax EAGLE-3 head, bench pure-dense and gemma-MoE | common/speculative.cpp
- L205 | gpu | L | N | needs multi-GB code-corpus cache build | Build vocab-locked corpus bigram cache, then A/B | common/ngram-cache.cpp
- L206 | gpu | L | N | needs CDNA2 sub-4-bit dequant kernel | Measure IQ2/TQ capacity and throughput, PPL-gated | ggml-cuda/mmq.cu
- L207 | gpu | L | N | no split-substrate spec path exists | GPU drafter feeding CPU-resident MoE/GDN target | common/speculative.cpp
- L210 | gpu | M | Y | L2 measured 3.37%, hot-path correctness risk | Fuse/cache quantize_q8_1 requant into GEMV prologue | ggml-cuda/quantize.cu, mmvq.cu
- L213 | gpu | L | Y | **STALE?** gate on TCC_EA_RDREQ_32B; L3 retired | Repack Q8_0 to SoA if sub-line read amplification high | ggml-cuda/mmvq.cu
- L215 | gpu | L | Y | prefill MFMA gate already failed | Route compute-bound GEMMs to MFMA where profile-gated | ggml-cuda/
- L217 | gpu | L | Y | quality gate (PPL/eval parity); kernel unauthored | Improve Q4_K dequant efficiency toward ~47 t/s | ggml-cuda/mmq.cu
- L218 | gpu | M | Y | measured negative at low batch; needs 256-expert vehicle | Apply mmid max-batch threshold, measure MoE step-rate | ggml-cuda/mmvq.cu
- L219 | gpu | L | Y | no ROCm/HIP diffusion serving path exists | Stand up DiT serving path, then run all DiT levers | ?
- L220 | gpu | M | Y | no aux model ever benchmarked on card | Benchmark BGE encode + VL vision-encoder prefill baselines | ?
- L223-L231 (9 rows) | none | S | **N — all edit this same file** | - | Taxonomy gaps: add Dense-Q4_K category (223); split pure-MoE from GDN-hybrid (224); add sub-4-bit/IQ-codebook (225); add MLA-attention MoE (226); add Mamba2-hybrid (227); add lightning/linear-attention hybrid (228); split VL vision-encoder from decoder (229); add ultra-sparse MoE 256-of-8 (230); add ASR/speech encoder-decoder (231) | this handoff

## frontier-f1-real-task-corpus.md (1)
- L115 | none | M | Y | - | **READY** W2c port ~50-line Hermes SQLite reader instead of letta dep | harvest_tasks.py, test_task_harvester.py

## frontier-f2-self-running-lab.md (2)
- L32 | cpu | L | N | quiet window (AutoPilot + llama-servers) + cloud reviews | W3 collect real shadow/reviewed verdicts; script as only promotion path | scripts/lab/promote_job.py
- L33 | cpu | L | N | W3 ladder evidence | W4 expand lab to intake triage then deep-dive drafting | orchestration/lab_jobs.yaml

## frontier-f3-data-flywheel.md (2)
- L23 | none | M | Y | publish/adoption decision | Add upload/publish step, broaden raw-trace secret redaction | raw_trace_publish_preflight.py
- L33 | gpu | L | N | **gfx90a training-viability smoke unverified** | W3 GPU fine-tunes: planner-distill, drafters, EV-9 judge model | build_planner_sft.py, training scripts

## frontier-f4-continuity-backup.md (2)
- L21 | none | M | N | no off-host/off-array target configured (operator picks) | W2 nightly verifiable T0 snapshot to a real off-array target | backup_critical.sh, continuity_backup.py
- L22 | none | M | N | W2 real snapshot | Pass one full restore cycle, wire backup-age into ATTESTATION | verify_restore.sh, check_latest_backup.sh

## frontier-f6-upstream-publication.md (4)
- L19 | cpu | L | Y | standing bench-approval for D1 smoke | W1 D1 smoke then submit D2 sparse-path PR upstream | llama.cpp DSA sparse path
- L20 | none | L | Y | host-attestation IDs / current-era rerun decision | W2 finish methodology post; attestation + external scrub | canonical-cpu-benchmarking-methodology-draft.md
- L21 | none | L | Y | 31 attestation rows + 18 protocol-tag rows | W3 clear retained-row attestation blockers for public results | generate_public_results.py
- L22 | none | S | Y | first monthly publication review | W4 maintain one-artifact-per-month publication candidate queue | handoff

## gemma-challenge-kernel-techniques-v7.md (9)
- L120 | gpu | M | N | verify re-capture must prove measured bottleneck; quiet host | Quiet-host re-eval of Lever A shape-aware graph key | lever-a-shape-key.patch, ggml-cuda.cu
- L140 | gpu | L | N | MI210 quiet-window inference availability | Root-cause free-form sampler/stop nondeterminism on GPU worker | k11_gemma4_determinism_runner.py
- L405 | cpu | L | Y | - | K24 implement x86 Q5_0/Q6_0/Q8_0 repack kernels + canonical benches | ggml-cpu/repack.cpp, iqk/
- L410 | gpu | L | N | K28.5 cheap proof gate | Write faster fused chunked GDN recurrence HIP kernel | gated_delta_net.cu, delta-net-base.cpp
- L416 | gpu | L | N | rocprof tooling install + GPU window | Cheap GDN attribution or throwaway fused prototype gate | delta-net-base.cpp
- L418 | none | L | Y | only if slot-save teleport option (i) is pursued | Composed-spec get_state save/restore for prompt-cache checkpoints | common/speculative.cpp
- L419 | none | L | N | - | Design server-safe Expected-Attention reclaim; audit DSA prompt path | llama-kv-compress.cpp, llama-kv-cache-dsa.cpp
- L421 | none | L | N | K31(a) reclaim design | Keep Expected-Attention server-safe reclaim open, distinct from DSA | llama-kv-compress.cpp
- L475 | none | L | Y | needs concrete parser-quality hypothesis | Improve table post-processing or compare a stronger document parser | odl_bench/paddleocr_vl.py

## glm51-reap-cpu-evaluation.md (11)
- L66 | cpu | M | N | quiet window; top-k schedule | Run full five-prompt short-context smoke on GLM-5.2 | glm52_reviewer_corpus_direct_runner.py
- L67 | none | S | N | needs smoke set (L66) | GATE: abort and document if repetition loops appear | handoff
- L72 | cpu | L | N | quiet window; long timeout | Long-context >64K needle probe on current-source GLM DSA | data/glm52_dsa_probe/
- L83 | cpu | L | N | DSA-DENSE-MASK; needs sparse path | Implement sparse top-k KV gather or capture backend skip evidence | src/models/glm-dsa.cpp
- L87 | cpu | L | N | quiet window; Phase 1/2 gates | 192t and NUMA 2x96t prefill/gen throughput + TTFT | scripts/benchmark/
- L89 | none | S | Y | needs representative workload profile | Record GPU non-fit note; expert-offload reopen conditions | mi210-big-model-and-acceleration-roadmap.md
- L93 | cpu | L | N | Phase 1/3 gates; quality blocker | Run standard suites vs architect_general and architect_coding | benchmarks/
- L104 | none | L | Y | needs oracle or operator label sign-off | Add executable oracle for full-patch accept controls | glm52_reviewer_corpus_direct_runner.py
- L107 | none | S | N | Phases 1-4 | Record GO/WAIT/KILL disposition, update indices | inference-acceleration-index.md
- L113 | cpu | L | N | needs representative calibration corpus | Repeat imatrix expert-count for Zipfian test | extract_imatrix_expert_counts.py
- L114 | none | L | Y | GLM quality re-clear | Decide native GLM-MTP tail-tensor + DECODER_MTP graph port | src/models/glm-dsa.cpp

## glm52-reviewer-capability-gates.md (5)
- L121 | cpu | L | N | P-REV-1 corpus + MEASUREMENT amendment | GC-1a claim-grade strict-IF typed-emission gate rerun | glm52_reviewer_capability_direct_runner.py
- L124 | cpu | L | N | needs frontier-authored reference task set | GC-2a rubric-authoring claim-grade gate with axis diversity | glm52_…direct_runner.py
- L127 | cpu | L | N | P-REV-1 sign-off + corpus-v1 | GC-3a why-diagnosis corpus-v1 claim-grade retest | glm52_reviewer_corpus_direct_runner.py
- L159 | none | S | Y | **operator decision (OP-5c / §A00)** | GC-4 RAM-residency policy: resident vs swap-in vs review-windows | glm52-ram-residency-decision-input doc
- L233 | cpu | L | N | UD-IQ3_XXS download (~300-340GB) + P-REV-1 | H-Q1 rerun C-CRAB slice on higher-bpw GLM | glm52_reviewer_corpus_direct_runner.py

## gpu-acceleration-path.md (8)
- L507 | gpu | M | Y | operator-approved GPU measurement window | Rerun Gate R residency bench on production kernel | data/k35_stack_context_matrix/
- L509 | gpu | M | Y | - | Probe -ot exps=CPU / --n-cpu-moe hybrid MoE offload | llama-bench invocation
- L510 | none | M | Y | operator FUND-OR-CLOSE decision | DFlash/DDTree HIP re-scope: confirm-negative vs MTP-less niche | handoff, gpu-drafter-mi200-investigation.md
- L511 | gpu | L | Y | - | Splitwise GPU-prefill/CPU-decode KV handoff probe | llama.cpp server KV handoff path
- L517 | gpu | L | Y | needs maintained server/parser path | Diffusion-aware constrained decode or maintained admission path | examples/diffusion/diffusion.cpp
- L524 | none | S | Y | - | **READY** Record intake-578 deployment fact is now backwards | research/intake_index.yaml
- L530 | gpu | M | Y | - | Patch ERNIE ROCm f32 matmul precision; re-test 896/960/1024 | ernie_image.hpp, ggml_extend.hpp
- L531 | none | S | Y | - | **READY** Record reverse-KL on-policy-distillation negative as guardrail | handoff, research/intake_index.yaml

## gpu-cot-scaffold-sidecar.md (1)
- L21 | gpu | L | Y | only if a concrete deployment decision is proposed | G3-4 context-matched decision-grade generator/receiver instrument | /mnt/raid0/llm/tmp/cot-g1/

## gpu-drafter-control-redesign.md (2)
- L97 | gpu | L | N | DR-3e P-GPU-1 certification | Broader K2 admission runner: task slice, bands, lease proof | dr3_quant_asym_k2_admission_runner.py
- L135 | gpu | M | N | operator GPU window under production kernel | Rerun required GPU claims as production-named P-GPU-1 certification | dr3_…runner.py

## gpu-drafter-mi200-investigation.md (2)
- L36 | gpu | L | N | Stage-1/2 economics failed; needs new control design | Redesign Stage-1 speedup and co-residency | data/specdec_frontdoor_alpha/
- L495 | gpu | L | N | Stages 1-3 failed/blocked | Stage 4 MTP head split for gemma4 worker_general | build-hip/llama-server

## gpu-serving-tie-in-program.md (29) — the live campaign spine; most rows serialize on P0-1 or the GPU lane
- L48 | none | M | N | **Codex merged-tree fix + operator signature** | P0-1 operator runs E8 ratification on apply-ready bundle | ratify_and_apply_e8_quality_baseline_v5.sh
- L53 | none | S | Y | - | **READY** Relay to Codex naming this handoff program authority | coordination/session-bus/tasks/
- L54 | none | S | Y | operator review of G3 scaffold results | Delete ThinkingCap weights after G3 review + lsof check | models/ThinkingCap-Qwen3.6-27B-GGUF
- L64 | none | M | N | P0-1 E8 bundle | P1-1 close pre-reboot terminating set, issue reboot request | handoff, session-bus
- L65 | cpu | L | N | host reboot | P1-2 run E5 W1-W4 grid, republish artifact in place | server_numa_np_sweep.py, e5_w0_offline_score.py
- L66 | cpu | M | N | P0-1 E8 signature + reboot | P1-3 resume AutoPilot on existing CPU surfaces | scripts/autopilot/
- L73 | gpu | M | N | reboot; only P2-2c remains | P2-2 land two-tenant set: dense-27B stock + MiniCPM-o | gpu_shadow_lane_tenancy.yaml
- L76 | gpu | M | N | reboot + runbook P1 operator grant | P2-3 execute MiniCPM-o promotion runbook Steps 1-6 | vision-escalation-minicpmo-promotion.md
- L88 | none | S | Y | P3 bake-off verdict | Decide whisper W1 CPU-stay vs W2 whisper.cpp HIP port | gpu_shadow_lane_np_ceiling.yaml
- L90 | none | M | N | Codex E8 bundle presentation | P0-1a verify merged wrapper tree before SAFE-TO-SIGN | ratify_and_apply_e8_…sh
- L94 | none | S | N | operator complexity-threshold decision | Resolve complexity threshold + stress-level decision-rule inputs | p2-5a-shed-trade-measurement-spec.md
- L95 | cpu | M | N | P1-3 autopilot resume | Measure stress duty cycle as third threshold condition | scripts/autopilot/ journal
- L96 | gpu | L | N | G1 q3 lock + Steps 0-7 + operator grant | Run four-arm P2-5a shed-trade measurement campaign | gpu_shadow_lane_lease.py
- L97 | cpu | M | N | P0-1 then P1-3 | Measure duty cycle only after representative AutoPilot window | scripts/autopilot/ journal
- L112 | gpu | L | N | Steps 0-7 activation + P2-2c | P3-1 run stock-27B vs FF bake-off arms | p3-shadow-bakeoff-spec.md, critic_tasks_v1.json
- L113 | none | M | N | P3-1 results | P3-2 build per-duty tenancy decision package | p3-shadow-bakeoff-spec.md
- L114 | none | S | N | P3-2 package + operator three gates | P3-3 operator sign-off, coder_escalation rebind or keep-A4 | model_registry.yaml
- L117 | none | L | Y | P3-3 production sign-off | P4-1 Stage-2 typed autopilot knobs for tenant + np_ceiling | src/autopilot_core/, src/features.py
- L118 | none | M | N | P4-1 review, N clean trials | P4-2 stage widening of autopilot knob space | src/autopilot_core/
- L121 | none | L | Y | P2 lane stable | P5-1 build agentic tool-using SWE-bench harness + exec sandbox | scripts/benchmark/swe_agentic/
- L122 | none | M | N | P5-1 harness | P5-2 validate FAIL_TO_PASS scorer on gold patches, pin manifest | swe_agentic/, question manifest
- L123 | gpu | L | N | P5-2 scorer validation + operator windows | P5-3 run SWE-agentic arms, decide 122B keep or shrink | swe_agentic/, artifacts/
- L125 | gpu | L | N | post-reboot operator grant; P2-5j first | Measure architect-lane pair, maybe mint q3-smt-hi region | contention_matrix.yaml, region-lock
- L132 | none | S | N | - | Fix corpus-scope + arm-contradiction defects in P-SHED-1 spec | p2-5a-shed-trade-measurement-spec.md
- L133 | cpu | L | N | post-reboot, operator grant, never pre-E8 | Measure 122B at 72t/3-quadrant, lane absent vs active | canonical 122B recipe
- L135 | gpu | L | N | P2-2c + Steps 0-7 + operator authorization | P2-5j sweep four host-thread placements | p2-5j-host-thread-placement-sweep-protocol.md
- L143 | none | S | Y | - | **READY** Add GPU host threads as modeled slot-fabric consumer | heterogeneous-slot-fabric-residency.md
- L144 | none | S | Y | orchestrator file owner; unmerged crash-window branch | Fix stale NUMA-node-count and 12.19 t/s comments | scripts/server/stack_numa.py
- L145 | none | S | N | - | Shape arm A1 reporting per-role, pin co-tenant state per arm | p2-5a-shed-trade-measurement-spec.md

## granite-97m-r2-bench-plan.md (1)
- L233 | none | M | Y | - | **READY** Phase C retriever promotion decision + downstream updates | internal-kb-rag.md, colbert-…md, searxng-…md

## harness-selection-and-integration.md (11)
- L40 | none | M | Y | HS-2 ROI verdict LOW — dormant | HS-3 survey ACP-speaking open harnesses as extra candidates | handoff, acp-roi-analysis-2026-07.md
- L41 | none | M | N | **operator decision (HS-4 is operator-owned)** | HS-4 harness-selection gate: Hermes vs OpenCode vs ACP | handoff, hermes-outer-shell.md
- L134 | none | S | N | - | HS-5 add weight-space RL adapter column to decision matrix | handoff
- L136 | none | S | N | - | Record Fractal as outer-loop orchestrator, not an HS-4 candidate | handoff
- L142 | none | L | N | - | HS-6 audit Layer-B against six/seven-dimension harness taxonomy | handoff, orchestrator layer-B sources
- L143 | none | S | N | - | HS-7 record re-targetable-harness principle as standing criterion | handoff
- L144 | none | L | Y | - | HS-8 extract run-level policy into editable NLAH-style document | agents/shared/, new policy doc
- L145 | cpu | L | Y | needs HS-8 policy document first | HS-9 probe whether open-weight models interpret NL policy faithfully | saved traces, eval harness
- L146 | none | M | Y | - | HS-10 file harness randomization as evaluation-side pattern | scoring-infra-standardization.md
- L147 | none | S | N | - | HS-11 record DSPy/GEPA compile budget as standing cost line | handoff
- L148 | none | S | N | - | HS-12 carry corrected capability-vs-harness figures with counterweight | handoff, wiki/

## hermes-agent-index.md (11) — index pointers into hermes-outer-shell / repl-turn-efficiency
- L99 | cpu | M | N | quiet window | Reference non-Hermes client live send/streaming validation | scripts/hermes/, src/api/
- L101 | cpu | M | N | quiet window + orchestrator 8000 up | Orchestrator override-semantics validation | scripts/hermes/, src/api/
- L102 | cpu | L | N | upstream target selection | Hermes upstream pin bump, breaking-change audit, smoke | /mnt/raid0/llm/hermes-agent
- L104 | none | M | N | checkout ahead of origin/main | Select, fetch, checkout, set up upstream Hermes target | /mnt/raid0/llm/hermes-agent
- L106 | none | L | Y | deferred while single-user | Multi-user auth flow for Hermes outer shell | scripts/hermes/, src/api/
- L107 | cpu | L | N | quiet window + MEASUREMENT.md protocol | repl-turn-efficiency S4 Omega A/B measurement gate | repl-turn-efficiency.md
- L108 | cpu | L | N | inference availability | Native-tools sentinel/parity + cost-aware delegation | tool-use-eval-contract.md
- L109 | cpu | L | N | inference-gated; blocks tool-output-compression P4e | Journal nonzero total_tool_calls + usefulness evidence | seeding_diagnostics.jsonl
- L111 | cpu | M | N | LangGraph migration | Test x_max_escalation against the full graph | hermes-outer-shell.md ~L252
- L112 | cpu | L | N | quiet window | Live Hermes end-to-end smoke across six behaviors | scripts/hermes/, MEMORY.md
- L114 | cpu | M | N | quiet window + P-SMOKE-1 | Hermes CLI code exec, memory persistence, latency, compression | scripts/hermes/, MEMORY.md

## hermes-outer-shell.md (11) — ALL cpu-lane, all need a live llama-server
- L189 | cpu | S | N | live Hermes backend quiet window | Validate multi-turn context referencing prior answer | launch_hermes_backend.sh
- L190 | cpu | S | N | live Hermes backend quiet window | Validate Hermes code execution writing/running Python | launch_hermes_backend.sh
- L191 | cpu | S | N | live Hermes backend quiet window | Validate MEMORY.md persistence across sessions | ~/.hermes/MEMORY.md
- L192 | cpu | S | N | live Hermes backend quiet window | Measure first-token and total latency on Hermes turns | launch_hermes_backend.sh
- L193 | cpu | M | N | live Hermes backend quiet window | Verify compression trigger compacts long conversation | hermes_config.yaml
- L194 | cpu | M | N | live Hermes backend quiet window | Verify subagent delegation uses same local endpoint | hermes_config.yaml
- L252 | cpu | S | N | inference availability | Validate streaming compatibility with new x_* override params | openai_compat.py
- L253 | cpu | S | N | inference availability | Test x_disable_repl end-to-end against live endpoint | openai_compat.py
- L254 | cpu | M | N | LangGraph migration | Test x_max_escalation enforcement with full routing graph | openai_compat.py, src/escalation.py
- L311 | cpu | M | N | live validation window (L322 open) | Stand up reference non-Hermes client | reference_openai_client.py
- L322 | cpu | M | N | quiet window | Run live --send validation of overrides, metadata, streaming | reference_openai_client.py

## heterogeneous-slot-fabric-residency.md (9) — ALL gated
- L137 | none | M | Y | lane-residency verdict; P2-5j must run first | Model GPU host threads as a gpu-host fabric slot (design) | handoff, gpu-serving-tie-in-program.md
- L141 | none | M | N | **E5 NUMA x batch sweep** | Consume E5 to set CPU (N,K) provisioning and lanes question | stack_numa.py
- L142 | none | L | N | post-v7-promotion gate | Invert role-keyed NUMA/spec config into model-keyed capability cards | stack_numa.py, model_registry.yaml
- L143 | none | L | N | post-v7 promotion + E5 | Design GPU-as-placement-target extension to slot fabric | concurrency_aware.py
- L144 | none | L | N | post-v7 promotion + operator authorization | Layer-2 residency actuator verb + swap protocol + kill-switch | orchestrator_stack.py
- L145 | none | L | N | needs GPU placement target (L143) | Teleport-to-GPU as re-prefill-from-transcript migration variant | concurrency_aware.py
- L146 | none | M | N | post-v7 promotion gate | Tracked-session index wired to router + escalation predicates | src/scheduling/placement.py
- L147 | none | L | N | needs Layer-2 actuator + shadow data | Layer-3 autopilot residency policy | migration_counters.py
- L148 | none | M | N | needs measured swap cost C | N-dwell hysteresis for GPU residency swaps | concurrency_aware.py

## inference-acceleration-index.md (7) — index pointers
- L217 | cpu | L | N | EvalTower telemetry gate before default flip | Batched decode E2 quality/reliability/throughput telemetry gate | eval_tower.py
- L218 | cpu | M | N | consolidated quiet window | DS-E1 dynamic-stack KV measurement | orchestrator_stack.py, k35 runner
- L367 | gpu | L | N | v8 promotion + operator window | DR-3e rerun K2/frontdoor GPU claims under P-GPU-1 | dr3_…runner.py
- L380 | cpu | L | N | quality recoverable + D2 blocker audit | GLM-5.2 real sparse final-attention implementation | llama.cpp src/models/glm4.cpp
- L381 | cpu | L | N | task D2 scout result | D2 blocker audit: indexed-attention path or backend skip proof | DSA attention op
- L410 | cpu | L | N | artifact/protocol quant-parity gate | T4 Qwen3.6-35B-A3B MTP model-load / gate-bench | qwen-mtp-llamacpp-port.md
- L412 | cpu | M | N | operator gate | P6b qwen-mtp model-load operator gate-bench | qwen-mtp-llamacpp-port.md

## inference-batch-loop.md (13) — the /loop owns ledger.jsonl; NOT parallel-safe
- L195 | cpu | L | N | **operator gate OP-6a/6b + stack-restart approval** | Run RCP prologue W1/W2/W3 reference relaunch chain | entries/00-rcp-prologue.yaml
- L196 | cpu | L | N | RCP-W1 (P0) | Run reviewer-plane riders RC-8/RM-6/LB-1/LB-4/RD-12/TM-8 | entries/10-reviewer-plane.yaml
- L197 | cpu | L | N | B7 scorer-semantics sign-off | Run eval-tower entries EV-4/11c/10a/RE-4/H5-RM3 | entries/20-eval-tower.yaml
- L198 | cpu | M | Y | - | Redesign LongCoT-Mini for bounded reasoning + deterministic extraction | longcot_mini_adapter.py
- L199 | cpu | L | N | K-ROPE + paddleocr-VL build gates | Run remaining P3 bulk-campaign entries | entries/30-bulk-campaign.yaml
- L202 | cpu | M | N | manifest-owner ledger reconciliation | Reconcile then run remaining kernel/routing entries | entries/50-kernel-op2.yaml
- L203 | cpu | L | N | needs named repair hypothesis | GLM window only under repair hypothesis or capability gate | entries/60-glm-decision.yaml
- L204 | cpu | L | N | **operator gate OP-5a P-REV-1** | Decision-grade confirmations RC8/LB7/RM4/RM8/RELABEL/RM2-A3 | entries/10-reviewer-plane.yaml
- L208 | none | L | N | **stack-freeze lift** | Wire semantics reducer/authority/escalation into live serving | src/reviewer/review_service.py
- L209 | none | M | Y | PaddleOCR-VL download, OP-VL-INFERENCE-APPROVAL | Build _extract_with_paddleocr VL backend adapter | src/services/pdf_router.py
- L210 | none | M | N | **stack-freeze lift** | Add control/data delimiter to reviewer prompt rendering | review_service.py, test_candidate_security.py
- L211 | none | M | Y | **stack-freeze lift** | Wire patch pre-gate into live escalation dispatch | patch_pre_gate.py
- L263 | none | S | Y | operator/loop-owner decision | Promote or decline ContextRot signature probe entry | inference-batch/entries/

