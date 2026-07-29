# BACKLOG DISPATCH QUEUE — pre-vetted work for idle mains

**Generated 2026-07-29** (sweep taken at repo tip `4dc445a2`). Read-only sweep. This file is the ONLY
artifact this session wrote; no handoff, checkbox, `queue.jsonl`, inbox, outbox, heartbeat or cursor was
touched, and this session ran no `git commit`. (A coordinator session committed an in-progress copy of
this file as `7adca72d` mid-write; the content below is the finished version.)

## Counts

| Metric | Value |
|---|---|
| Unchecked `- [ ]` tasks in `handoffs/active/` | **1103** at sweep start → **1082** at verification (mains are burning it live — see *Volatility*) |
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

## ⚠ Volatility — this queue is being consumed WHILE you read it

**Verified 2026-07-29, minutes after first write: 8 of the original TOP 40 were already closed by live
mains, and total unchecked fell 1103 → 1082.** Struck-through rows below are those confirmed-closed
entries, left in place so the next reader can see the burn rate rather than a silently shrinking table.
`llamacpp-v6-consolidation.md` also had lines inserted, shifting its anchors.

**Operating rule for the coordinator: line numbers are a hint, task text is the identity.**
Before assigning any row, run `grep -n '^\s*- \[ \]' <handoff>` and match on the description, not the
line. A row that has vanished is a row someone finished.

## Volatility — the two owned handoffs

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
| 1 | ~~`cpu-shape-specialized-gemv-decode.md:723`~~ **✅ CLOSED 2026-07-29** | pickup-checklist | none | S | (research only) | Check llama.cpp upstream for new CPU ukernel PRs |
| 2 | ~~`cpu-shape-specialized-gemv-decode.md:727`~~ **✅ CLOSED 2026-07-29** | pickup-checklist | none | S | fork commits 143ded626/c4e06b01e/59d2012b2 | Confirm TIDE early-exit paths dormant before any baseline |
| 3 | ~~`stale-open-audit-2026-07-18.md:92`~~ **✅ CLOSED 2026-07-29** | recommendations | none | S | dashboard backlog banner config | Publish corrected live-backlog figure (~544, board over-counts) |
| 4 | `decision-aware-routing.md:613` | speed-axis | none | S | `orchestration/instrument_eras.yaml` | Record instrument-era boundary row for reward values |
| 5 | `rlm-contested-claims-self-evaluation.md:68` | tasks | none | S | niah scorer module | Format-robust NIAH scorer (strict + lenient) |
| 6 | `reviewer-escalation-and-human-gate-policy.md:22` | tasks | none | S | SafetyGate protected-action config | Align protected-action list with existing SafetyGate |
| 7 | ~~`intake-derived-work-2026-07-25.md:87`~~ **✅ CLOSED 2026-07-29** | P3 process defects | none | S | `scripts/validate/`, research-intake cross-reference-map | Add path-resolution check for the intake cross-reference map |
| 8 | `agentic-rocm-kernel-authoring.md:78` | progress-checklist | none | S | `research/deep-dives/…geak-synthesis.md` | GEAK-family freshness sweep at each audit |
| 9 | ~~`gpu-acceleration-path.md:531`~~ **✅ CLOSED 2026-07-29** | 2026-07-29 fix | none | S | `gpu-acceleration-path.md` | Record reverse-KL on-policy-distillation negative as guardrail |
| 10 | ~~`tool-use-eval-contract.md:366`~~ **✅ CLOSED 2026-07-29** | intake 2026-07-21 | none | S | sentinel prompt definitions | Adopt negative-constraint + stated-consequence sentinel pattern |
| 11 | ~~`gpu-serving-tie-in-program.md:143`~~ **✅ CLOSED 2026-07-29** | P5 | none | S | `heterogeneous-slot-fabric-residency.md` | Add GPU host threads as a modeled slot-fabric consumer |
| 12 | ~~`model-stack-change-standardization-audit.md:229`~~ **TEMPLATE — DO NOT DISPATCH 2026-07-29** | update-checklist | none | S | `tests/unit/` priors/guard/enum-sync/q_scorer suites | Run focused unit tests for priors, guard, scorer, admission |
| 13 | ~~`eval-tower-verification.md:522`~~ **✅ CLOSED 2026-07-29** | de-anchoring | none | S | `autopilot.py:1431`, `paired_stats.py` | Unify autopilot's 2nd McNemar producer onto `verdict_from_result` |
| 14 | ~~`minddr-deep-research-mode.md:207`~~ **✅ CLOSED 2026-07-29** | search-time contamination | none | S | `minddr-deep-research-mode.md` | Demote BrowseComp/WideSearch/xbench anchors to observation-grade |
| 15 | ~~`engram-conditional-memory.md:379`~~ **✅ CLOSED 2026-07-29** | retrieval-policy rider | none | S | `engram-…md`, `unified-trace-memory-service.md` | Correct the ReasoningBank ranking claim in retrieval notes |
| 16 | ~~`unified-trace-memory-service.md:211`~~ **✅ CLOSED 2026-07-29** | UTM-M4 | none | S | `src/trace/harness_schema.py` | Mine ReasoningBank repo for its 3 prompts + JSON schema |
| 17 | ~~`autopilot-decision-plane-audit-2026-07-22.md:399`~~ **✅ CLOSED 2026-07-29** | deliverables | none | S | `q_scorer.py`, `episodic_store.py` | Apply find-or-update to `_update_escalation_memory` append-only rows |
| 18 | ~~`orchestration-robustness-audit-2026-07-11.md:240`~~ **✅ CLOSED 2026-07-29** | faiss orphans | none | S | `orchestration/repl_memory/faiss_store.py` | Startup sweep unlinking old unopened faiss tmp orphans |
| 19 | ~~`autopilot-control-plane-integration.md:23`~~ **✅ CLOSED 2026-07-29** | AP-3b.2 | none | S | `autopilot-control-plane-integration.md` | Decide whether draft-tree belongs in AP-3 |
| 20 | ~~`speculative-decoding-mtp-refresh.md:236`~~ **✅ CLOSED 2026-07-29** | intake 2a | none | S | `models/*.gguf` headers | Tensor-count header gate for the DavidAU Qwen3.6-27B MTP GGUFs |
| 21 | ~~`agent-file-prose-compression.md:244`~~ **✅ CLOSED 2026-07-29** | intake 2a | none | S | `agent-file-prose-compression.md` | Re-source `/doctor` behaviour from the CLI before speccing |
| 22 | ~~`learned-routing-controller.md:1613`~~ **✅ CLOSED 2026-07-29** | deep-dive correction | none | S | (guardrail note) | Standing guardrail: do not import intake-866 equivalence framing |
| 23 | ~~`document-parser-table-bench.md:144`~~ **✅ CLOSED 2026-07-29** | consequence | none | S | (guardrail note) | Guardrail: no MinerU/GLM-OCR downloads as odl_bench swaps |
| 24 | `scorer-fork-drift-audit-2026-07-22.md:257` | residual tasks | none | S | `scripts/benchmark/seeding_legacy.py` | Guard or delete the legacy ComparativeResult reward-injection path |
| 25 | ~~`autopilot-continuous-optimization.md:1529`~~ **✅ CLOSED 2026-07-29** | AP-32 | none | S | `wiki/agent-architecture.md`, `strategy_store.py` | Strike unmeasured +1.1% claim; guard the dead linter |
| 26 | ~~`architect-model-selection-bench.md:330`~~ **✅ CLOSED 2026-07-29** | follow-up tooling | none | S | `scripts/bench/gpu_lib.sh`, `run_arm.sh`, `run_budget.sh` | Promote scratchpad GPU driver scripts into the repo |
| 27 | ~~`context-folding-progressive.md:113`~~ **✅ CLOSED 2026-07-29** | deep-dive correction | none | S | `context-folding-progressive.md` | Record do-not-prioritize decision for ContextRot harness replication |
| 28 | ~~`scoring-infra-standardization.md:184`~~ **✅ CLOSED 2026-07-29** | intake 2a | none | S | `research/intake_index.yaml`, `benchmarks/instruction_precision` | Adopt six-point SWE-bench disclosure standard for intake-916/917/924 |
| 29 | ~~`tool-output-compression.md:442`~~ **✅ CLOSED 2026-07-29** | intake 2026-07-21 | none | S | `scripts/utils/compress_tool_output.py` | Bias Phase-3d fallback chain toward observation-dropping first |
| 30 | ~~`decision-aware-routing.md:185`~~ **✅ CLOSED 2026-07-29** | DAR-5 | none | S | `learned-routing-controller.md` | Document cold-start note for LRC P5 onboarding |
| 31 | ~~`ernie-image-turbo-evaluation.md:139`~~ **✅ CLOSED 2026-07-29** | progress-checklist | none | S | `research/deep-dives/` ernie dive | Record LongText-Bench harmonized ranking in the deep dive |
| 32 | ~~`intake-derived-work-2026-07-25.md:166`~~ **✅ CLOSED 2026-07-29** | P1b DFlash | none | S | capability registry yaml | Re-triage the stale dflash registry `forbid` row |
| 33 | ~~`model-stack-single-source-update-pipeline.md:325`~~ **✅ CLOSED 2026-07-29** | outstanding | none | S | `seeding_rewards.py`, `corpus_quality_gate.py`, `kv_compress.py` | Keep 3 re-audited surfaces unchurned absent a new duplicated fact |
| 34 | ~~`unified-trace-memory-service.md:219`~~ **✅ CLOSED 2026-07-29** | UTM-M6 | none | S | `research/intake_index.yaml` | File EvoMemBench 128K context-competition as a distinct failure mode |
| 35 | `rao-redel-substrate-spike.md:432` | intake 2026-07-21 | none | M | `orchestration/repl_memory/episodic_store.py` | Adopt SkyRL parent/child rollout-tree accounting shape |
| 36 | `reviewer-calibration-accounting.md:30` | RC | none | M | `src/trace/review_ledger.py` | Persist full rubric + per-item grades in corpus rows |
| 37 | `llamacpp-v6-consolidation.md` (F1 fold, re-grep: file shifted) | Stage-2 parity F1 | none | M | `llama.cpp-v6 ggml/src/ggml-cpu/ops.cpp` | Fold f1-paged-attn branch into v6, off-by-default |
| 38 | ~~`granite-97m-r2-bench-plan.md:233`~~ **✅ CLOSED 2026-07-29** | Phase C | none | M | `internal-kb-rag.md`, `colbert-…md`, `searxng-…md` | Phase C retriever promotion decision + downstream handoff updates |
| 39 | `frontier-f1-real-task-corpus.md:115` | W2c | none | M | `scripts/tasks/harvest_tasks.py`, its unit test | Port ~50-line Hermes SQLite reader instead of a letta dependency |
| 40 | ~~`benchmark-results-dashboard.md:47`~~ **✅ CLOSED 2026-07-29** | Phase 1 | none | S | `dashboard/`, both `model_registry.yaml` | Enumerate models on the system from both registries |

**Straight swap-ins for the 8 struck rows above (verified still open at 2026-07-29 verification):**
`decision-aware-routing.md:492` (standing prohibition, S/Y) · `intake-derived-work-2026-07-25.md:45`
(strike +1.1% claim, S/Y) · `intake-derived-work-2026-07-25.md:53` (do-not-trim guardrail, S/Y) ·
`model-stack-single-source-update-pipeline.md:350` (short_term_memory review, S/Y) ·
`model-stack-single-source-update-pipeline.md:352` (keep logs out of active indices, S/Y) ·
`unified-trace-memory-service.md:226` (ReasoningBank standing, S/Y) ·
`rlm-contested-claims-self-evaluation.md:80` (fold intake-925 Table 1, S/Y) ·
`speculative-decoding-mtp-refresh.md:233` (scope 122B DFlash acceptance-only, S/Y)

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
- L244 | none | S | Y | - | **CLOSED 2026-07-29** — Codex CLI evidence limits `/doctor` to diagnostics, not rewriting | Re-source /doctor behaviour from the CLI before speccing | handoff

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
- L330 | none | S | Y | - | **CLOSED 2026-07-29** — repo-relative sourcing, required v8 kernel label, and corrected 184-191 pinning | Promote scratchpad GPU driver scripts into the repo | scripts/bench/gpu_lib.sh, run_arm.sh
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
- L1529 | none | S | Y | - | **CLOSED 2026-07-29** — handoff AP-32 records diagnostic-only regression guard and removal of the external-paper-only claim | AP-32 strike unmeasured +1.1% claim; guard dead linter | wiki/agent-architecture.md, strategy_store.py
- L1530 | none | S | Y | - | Retarget utility-weighted-retrieval concern to live MemRL retriever | repl_memory/retriever.py
- L1536 | none | M | N | AP-29 gate | AP-29a budget write gate to cheapest adequate local judge | knowledge_distiller.py
- L1537 | none | M | Y | - | AP-29b replay-compare lexicographic vs scalarized objective selection | autopilot_journal.jsonl
- L1538 | none | S | Y | downstream of AP-19a/19b | AP-29c name GEPA-class optimizer of record | docs/chapters/08*, gepa_optimizer.py

## autopilot-control-plane-integration.md (4)
- L18 | cpu | L | N | AP-3b source proof; spec-dec quality clearance | AP-3 register restart-scoped spec-dec + per-role KV knobs | config_applicator.py, stack_priors.py
- L21 | cpu | M | N | launch probes need llama-server | AP-3b source-prove remaining launch fields | config_applicator.py
- L23 | none | S | Y | - | **CLOSED 2026-07-29** — current draft-tree degenerates to linear drafting; no independent tree controls exist | AP-3b.2 decide whether draft-tree belongs in AP-3 | handoff
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
- L399 | none | S | Y | - | **CLOSED 2026-07-29** — flag-gated escalation identity is exact reason + transition; routing/escalation partitions remain isolated | Apply find-or-update to _update_escalation_memory rows | q_scorer.py, episodic_store.py
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
- L47 | none | S | Y | - | **CLOSED 2026-07-29** — read-only inventory emits 166 deduplicated model/quant records while retaining source role references | Enumerate models on the system from both registries | dashboard/, model_registry.yaml x2
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
- L724 | none | S | Y | - | **CLOSED 2026-07-29** — primary-source sweep found no Zen 5-specific tinyBLAS benchmark; Zen 4 remains the only cited hardware prior | handoffs/active/cpu-shape-specialized-gemv-decode.md
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
- L185 | none | S | Y | - | **CLOSED 2026-07-29** — DAR-5.5 records spec-only initialization, observed-outcome refinement, and the reward-redesign prerequisite | Document cold-start note for LRC P5 onboarding | learned-routing-controller.md
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
- L144 | none | S | Y | - | **CLOSED 2026-07-29** — both require a separately scoped multi-call pipeline harness before any download or benchmark | Guardrail: no MinerU/GLM-OCR downloads as odl_bench swaps | ?
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
- L379 | none | S | Y | - | **CLOSED 2026-07-29** — records last-of-13 Cross-Episode Easy and retains schema rather than rank as the transferable signal | Correct the ReasoningBank ranking claim in retrieval notes | handoff, unified-trace-memory-service.md
- L385 | gpu | L | N | GPU budget authorization; gfx90a training viability | Allocate GPU, run frozen-vs-cotrained SmolLM-1.7B proxy | engram package, training driver
- L386 | gpu | L | N | needs GPU allocation (L385) | Build canonicalizer, train both configs, 30% recovery gate | scripts/build_canonicalizer.py
- L387 | gpu | L | N | Gate B0 pass required | File retrofit spike handoff, start Qwen3.6 Phase 1-4 surgery | engram-retrofit-qwen36-spike.md

## episodic-memory-integrity.md (4)
- L130 | cpu | M | N | needs ~2,000 fresh post-reseed trajectories | M-11a first re-distil of SkillBank with teacher LLM | seed_skills.py, autopilot/actions.py
- L153 | none | M | Y | coordinate with repl-session-memory-maturity | M-11a2 wire work-payload capture at live write sites | q_scorer.py, memory_record.py
- L178 | none | M | Y | post-reseed data accumulation | M-15 reopen intake-866 COMP_r under correct id_map resolution | faiss_store.py, COMP_r probe
- L316 | cpu | L | N | needs reseeded store + live traffic | M-12 memory-on vs memory-off A/B that never existed | episodic_store.py, benchmarks/

## ernie-image-turbo-evaluation.md (5)
- L139 | none | S | Y | - | **CLOSED 2026-07-29** — deep dive reconciles the EN/ZH mean ordering and preserves the vendor-self-report qualifier | Record LongText-Bench harmonized ranking in deep dive | research/deep-dives/ ernie
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
- L522 | none | S | Y | - | **CLOSED 2026-07-29** — sequential baseline payload uses `verdict_from_result`, observation-only and non-gating | Unify autopilot 2nd McNemar producer onto verdict_from_result | autopilot.py:1431, paired_stats.py
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
- L233 | none | M | Y | - | **CLOSED 2026-07-29** — conditional Granite default on consumer activation; existing BGE/ColBERT paths unchanged | Phase C retriever promotion decision + downstream updates | internal-kb-rag.md, colbert-…md, searxng-…md

## harness-selection-and-integration.md (11)
- L40 | none | M | Y | HS-2 ROI verdict LOW — dormant | HS-3 survey ACP-speaking open harnesses as extra candidates | handoff, acp-roi-analysis-2026-07.md
- L41 | none | M | N | **operator decision (HS-4 is operator-owned)** | HS-4 harness-selection gate: Hermes vs OpenCode vs ACP | handoff, hermes-outer-shell.md
- L134 | none | S | N | - | **CLOSED 2026-07-29** — HS-4 matrix records the adapter axis separately from current-host feasibility; operator ownership unchanged | handoffs/active/harness-selection-and-integration.md:134,137-145
- L136 | none | S | N | - | **CLOSED 2026-07-29** — already recorded as outer-loop, not HS-4, with containment/trial boundary | handoffs/active/harness-selection-and-integration.md:149 (root `c942728e`)
- L142 | none | L | N | - | HS-6 audit Layer-B against six/seven-dimension harness taxonomy | handoff, orchestrator layer-B sources
- L143 | none | S | N | - | **CLOSED 2026-07-29** — standing HS-4 re-targetability criterion and acceptance evidence are recorded | handoffs/active/harness-selection-and-integration.md:156,190-207
- L144 | none | L | Y | - | HS-8 extract run-level policy into editable NLAH-style document | agents/shared/, new policy doc
- L145 | cpu | L | Y | needs HS-8 policy document first | HS-9 probe whether open-weight models interpret NL policy faithfully | saved traces, eval harness
- L146 | none | M | Y | - | **CLOSED 2026-07-29** — evaluation-only randomization pattern plus P4.6 NULL counterexample recorded; no run was added | handoffs/active/harness-selection-and-integration.md:159,209
- L147 | none | S | N | - | **CLOSED 2026-07-29** — standing 5k-25k LM-call cost line is recorded and cross-linked | handoffs/active/harness-selection-and-integration.md:160; wiki/llm-prompting.md:160-162
- L148 | none | S | N | - | **CLOSED 2026-07-29** — corrected two-sided figure and observation-only boundary are recorded in handoff and both wiki references | handoffs/active/harness-selection-and-integration.md:161-164; wiki/agent-architecture.md:1055-1059; wiki/benchmark-methodology.md:1098-1101

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

## intake-derived-work-2026-07-25.md (34) — richest `none`-lane vein in the repo, but P3b rows collide on intake_index.yaml
- L26 | none | M | Y | task ID-1 (now closed) | Decide gepa dependency pin; re-run integration tests | pyproject.toml, test_gepa_integration.py
- L33 | none | M | Y | needs post-ID-1 gepa_optimize trials | Re-open AP-21 gepa_ratio 0.30 decision | autopilot.py, autopilot_state.json
- L39 | cpu | L | N | - | Gate KnowledgeDistiller on episodic-only control arm | knowledge_distiller.py, autopilot.py
- L45 | none | S | Y | - | **READY** Strike unmeasured +1.1% claim; precondition-gate audit | wiki/agent-architecture.md, strategy_store.py
- L50 | none | M | Y | - | Re-point memory-degradation evidence at live MemRL retriever | repl_memory/retriever.py
- L53 | none | S | Y | - | **READY** Record do-not-trim guardrail against vendor 80% claim | agent-file-prose-compression.md, CLAUDE.md
- L63 | none | M | Y | - | Add ordered_subsequence verifier with both graded metrics | answer_scoring.py, test_answer_scoring.py
- L66 | cpu | M | Y | needs sandboxed exec path | FrontierCS 10-problem floor probe on one arm | eval-tower-verification.md
- L69 | cpu | L | Y | - | Evaluate behavior-conditioned inference; score total pipeline tokens | reasoning-compression.md
- L87 | none | S | Y | - | **READY** Add path-resolution check for intake cross-reference map | scripts/validate/, cross-reference-map.md
- L92 | none | M | Y | - | Backfill handoffs_updated or stop treating as coverage | research/intake_index.yaml
- L95 | none | S | N | parallel v8 cutover session | Fix stale v6 kernel-immutability duplicate in agent file | agents/shared/ENGINEERING_STANDARDS.md
- L98 | none | M | N | - | Lossless structural de-dup of always-loaded governance surface | CLAUDE.md
- L105 | none | L | Y | no container host approved | Extract Fractal containment design; non-USD cost basis | mi210-kernel-rnd-loop-proposal.md
- L109 | none | M | Y | download pending | Header-gate DavidAU Qwen3.6-27B MTP GGUF twins | speculative-decoding-mtp-refresh.md
- L114 | none | M | Y | no license on GGUF repo | Rewrite ThinkingCap A/B; hold MTP constant across arms | architect-model-selection-bench.md
- L125 | none | S | N | task ID-7 + parallel v8 session | Offer graded ordered-coverage IF probe to v8 IQ arms | tq3-quantization-evaluation.md
- L128 | cpu | L | Y | - | Gate PageIndex adoption on measured per-query cost | internal-kb-rag.md, opendataloader-…md
- L132 | none | M | Y | - | Port ~50-line SQLite trajectory reader instead of adopting library | frontier-f1-…md, unified-trace-…md
- L136 | none | M | Y | operator decision | Decline TRL bridge; keep GPU-free OpenEnv trace-capture half | harness-selection-…md
- L147 | none | S | N | - | Retire obsolete no-llama.cpp-DFlash blocker across handoffs | speculative-decoding-mtp-refresh.md
- L150 | cpu | L | N | needs matching gemma-4 target weights | Measure gemma-4 DFlash drafter against worker_general | gemma-4-26B DFlash drafter
- L155 | none | S | N | - | Record Qwen3.5-122B DFlash watch item; scope acceptance-only | speculative-decoding-mtp-refresh.md
- L163 | none | S | N | parallel v8 session holds laguna edits | Downgrade quant-noise root cause to hypothesis | laguna-s21-cpu-port.md
- L166 | none | S | Y | - | **CLOSED 2026-07-29** — full registry retains registration gate but removes the stale runtime-availability forbid | Re-triage stale dflash registry forbid row | capability registry yaml
- L169 | none | S | N | - | Record headless non-causal target-locked DFlash architecture fact | laguna-…md, speculative-…md
- L179 | none | M | N | - | Recover dropped RLM negatives incl prefill-to-decode conversion | repl-turn-efficiency.md, intake_index.yaml
- L189 | none | M | N | - | Promote open-weight RLM system prompt + partitioning constants | repl-turn-efficiency.md
- L194 | none | S | N | - | Re-point both RLM entries; record lineage separation | research/intake_index.yaml
- L196 | none | S | N | - | Correct intake-578 reversed no-GGUF claim | intake_index.yaml, gpu-acceleration-path.md
- L199 | none | S | N | - | Index-hygiene one-liners: verdicts, notes, backfills, edges | research/intake_index.yaml
- L208 | none | M | Y | - | Cross-link llm-as-a-verifier to reviewer plane confidence | reviewer-calibration-accounting.md
- L211 | none | M | N | - | Correct false chunker-ABC claim; re-cost to DCC reimplementation | internal-kb-rag.md, intake_index.yaml
- L218 | none | S | N | - | Relabel Firecrawl not_applicable to superseded; fix record errors | intake_index.yaml, searxng-…md

## integration-test-coverage.md (5) — standing rules, not one-shot items
- L34 | none | S | N | - | Keep mocked integration tests separate from real inference tests | tests/ layout
- L35 | none | S | N | - | Label inference-backed tests so normal CI can skip them | tests/, pyproject.toml markers
- L36 | cpu | M | N | llama-server test fixture availability | Live-server fixtures: port, startup, teardown, stale-process checks | tests/conftest.py
- L37 | none | S | N | - | Avoid broad fixture rewrites without a failing contract test | tests/conftest.py
- L38 | none | S | Y | - | Check git status and test layout before adding code | tests/ (read-only)

## internal-interaction-lifecycle.md (5)
- L250 | cpu | L | N | autopilot trial window | Broaden T2/T3 shadow calibration of always-consult vs targeted | review_consult_gate.py
- L253 | none | M | N | needs 1 week P3-3 shadow data | Enable enforcement one signal at a time with rollback gate | review_consult_gate.py, src/features.py
- L261 | none | L | Y | P3 exit gate (30% advice value) | Instrument five consult integration-quality metrics | review_consult_gate.py
- L268 | none | M | N | task P4-1 metrics | Add separate consult_reward head to MemRL, unblended | repl_memory/q_reward.py
- L270 | none | S | Y | needs 4 weeks P4 metrics | Quarterly keep/tune/disable review per consult skill | handoff

## internal-kb-rag.md (15)
- L87 | none | L | Y | deferred: needs measured wiki-cross-link gap | K8 wikilink learning-loop scorer | src/retrieval/, wiki/INDEX.md
- L222 | none | S | N | HOPE-vs-Ekimetrics side-by-side from opendataloader Phase 2 | Bookmark Ekimetrics 5-metric impl as K7 eval scaffolding | handoff
- L223 | none | S | N | conditional: future K2 design review | Cite HOPE independence finding when defending K2 chunking | handoff
- L310 | cpu | M | Y | llama.cpp PR #22836 upstream | Confirm STQ1_0 1.25-bit GGUF loads or pick fallback | models/hy-mt2-1.8b/
- L311 | none | S | Y | download pending | Download Hy-MT2-1.8B weights | models/hy-mt2-1.8b/
- L312 | cpu | S | N | weights download (L311) | Verify Hy-MT2 chat template and sampling launch recipe | scripts/benchmark/
- L313 | none | S | Y | operator approval (per-run inference) | Obtain explicit per-run operator approval before pipeline run | ?
- L314 | none | M | Y | - | Freeze 40-snippet stratified sample set with provenance log | data/mt_eval/samples.jsonl
- L519 | none | S | N | - | Re-cost adaptive-chunking lift; library ships no adaptive selection | handoff
- L520 | cpu | M | N | offset provenance prerequisite (L521) | Scope DCC-only chunk-quality signal against existing encoder | markdown_chunker.py, colbert_encoder.py
- L521 | none | M | N | - | Add raw-source-offset provenance so chunks are exact substrings | markdown_chunker.py, its unit test
- L522 | none | S | N | - | Record both trigger conditions fired; work no longer deferred | handoff
- L523 | cpu | M | Y | measured per-query LLM-call bound (9/16 timed out) | Evaluate PageIndex as intra-document complement to ColBERT | scripts/kb_rag/, kb_rag.py
- L529 | cpu | L | N | requires a region claim | Bounded LFM2.5-ColBERT probe on K7 70-case pool | k7_cert_cases.json, colbert_encoder.py
- L530 | none | S | N | - | Correct intake-925 retriever reading before it informs index design | handoff, intake_index.yaml

## intra-process-tensor-parallel-decode.md (5) — dormant, no reopen trigger
- L24 | none | S | N | no reopen trigger established | State a new topology/workload trigger justifying CPU1 reopen | handoff
- L25 | cpu | M | N | reopen trigger (L24) | Apply P-BENCH protocols before any throughput claim | MEASUREMENT.md, bench scripts
- L26 | cpu | M | N | reopen trigger (L24) | Reproduce canonical baseline for target model and topology | bench_canonical.sh
- L27 | cpu | L | N | canonical baseline (L26) | Prove bottleneck is locality/barrier not DRAM-channel dominated | ggml-cpu/, perf artifacts
- L28 | none | S | N | profile result (L27) | Choose smallest next action: archive, probe, or redesigned TP | handoff

## iqk-iquant-enablement.md (4)
- L105 | cpu | L | N | operator inference approval; quiet window | T2 bench IQ4_KT vs Q4_K_M in ik_llama as instrument | ik_llama.cpp scratch build
- L106 | cpu | L | N | T2 must reach 95% tg128 gate | T3 port trellis KT types only if T2 clears gate | ggml-cpu/iqk/, CMakeLists.txt
- L140 | none | M | Y | - | Scope 1-bit family: vendoring, types, enums, missing traits | iqk_gemm_1bit.cpp, iqk_stubs.cpp
- L237 | cpu | L | N | quiet window; v8 frozen (post-v8 tranche) | Prefill-headroom bundle: func16, Q8_K_R16, fused MoE, flash-attn | iqk_gemm_iquants.cpp, iqk_mul_mat.cpp

## laguna-s21-cpu-port.md (2)
- L97 | none | M | Y | - | **READY** L-8 fold ad-hoc GPU smoke artifact into runner or delete | laguna_pgpu1_dflash_runner.py
- L120 | cpu | L | N | no CPU-resident Laguna role decision pending | L-9P conditional bounded four-cell CPU throughput/config discovery | laguna_q4_cpu_config_discovery.py

## large-moe-expert-parallelism.md (5)
- L37 | none | M | Y | - | CPU15-DISP reconcile deployment docs with downgraded EP verdict | cpu-inference-optimization-index.md
- L38 | cpu | L | N | CPU20 protocol + operator bench window | CPU15-REVAL fresh canonical no-EP/config/EP matrix, 3 reps | ep-dispatcher.cpp
- L43 | cpu | L | N | CPU24 perf-record evidence, >150B target | CPU15-ROOT bottleneck proof before new mechanism work | ggml-cpu.c, perf artifacts
- L44 | none | L | Y | CPU15-REVAL positive target | CPU15-UPSTREAM upstream ep_dispatcher only after positive gain | ep-dispatcher.cpp
- L45 | none | S | Y | MoE-Spec Phase 0 | CPU15-MOESPEC ordering note: mask/budget before EP broadcast | ggml-cpu.c, moe-spec handoff

## learned-routing-controller.md (21)
- L92 | none | L | Y | EPD-1/EPD-3 outcome-label defects | Re-run escalation probe after outcome label repaired | scripts/graph_router/, episodic_store.py
- L197 | none | M | N | - | Decide: update outcome with q_value or demote label | episodic_store.py
- L217 | cpu | L | N | needs BGE embed fleet window | Re-embed or partition store under one text convention | repair_episodic_embeddings.py
- L301 | cpu | L | N | 2026-06-12 routing-expansion guard | P1.5.2 collect 1000+ logit-probe requests | llama_server.py, data/logit_probe.jsonl
- L302 | none | M | Y | P1.5.2 collection | P1.5.3 train 512-param linear probe, evaluate accuracy | scripts/graph_router/
- L303 | none | S | Y | P1.5.3 | P1.5.4 decision gate 80%/60% on logit probe accuracy | handoff
- L311 | cpu | M | N | needs live /hidden-states server test | P2.3 collect mean-pooled hidden states per attention layer | llama.cpp-experimental server
- L312 | none | M | Y | P2.3 data | P2.4 train per-layer linear probes, find best layer | scripts/graph_router/
- L313 | none | M | Y | P2.4 | P2.5 learned attention pooling if layers complementary | scripts/graph_router/
- L314 | none | S | Y | P2.4/P2.5 | P2.6 decision gate 90%/80% to enter Phase 3 | handoff
- L318 | none | M | N | Phase 2 gate P2.6 | P3.1 swap BGE embedding for hidden-state features in MLP | routing_classifier.py
- L319 | none | M | N | P3.1 | P3.2 remove BGE model from inference path | src/backends/, orchestrator_stack.py
- L320 | none | L | N | P3.1 | P3.3 migrate episodic store schema to hidden-state vectors | episodic_store.py
- L379 | none | L | Y | trainable BGE-large ckpt + full torch env | P4 SVD-scale fine-tuning trial on extractor backbone | scripts/graph_router/, /mnt/raid0/llm/hf/
- L380 | cpu | L | N | needs cold-start surface + eval-tower fitness oracle | P4 sep-CMA-ES cold-start spike, ~10h overnight ES | eval_tower.py, scripts/graph_router/
- L393 | cpu | L | N | needs promotion-grade observed-outcome IRT scorer | P5.2 rerun cold-start acceptance gate with observed outcomes | irt_cold_start_ab.py, irt_scorer.py
- L394 | none | M | N | P5.2 decision gate | P5.3 ship onboarding CLI + document cold-start workflow | tools/onboard_specialist.py
- L854 | none | L | Y | P6.2 pass (deferred) | P6.3.1 port TinyRecursiveModels to CPU-only training mode | train_verifier_head.py
- L855 | none | M | N | P6.3.1 | P6.3.2 apply Augmented-HRM augmentation recipe | train_verifier_head.py
- L856 | none | M | N | P6.3.2 | P6.3.3 A/B recursive verifier vs P6.2 MLP, Brier gate | train_verifier_head.py
- L1613 | none | S | Y | - | **CLOSED 2026-07-29** — retains only the directly testable nearest-success feature; no equivalence-class claim enters policy or acceptance criteria | Standing guardrail: do not import intake-866 equivalence framing | ?

## lightning-attention-port.md (4)
- L32 | none | S | N | owner/operator role decision | LQ-1 decide Ring-mini role or park as architecture reference | handoff, model_registry.yaml
- L33 | cpu | L | Y | LQ-1 must keep a math/reasoning role | LQ-2 focused AIME/MATH/GPQA eval at reasoning_budget=0 | eval bundle artifacts
- L34 | cpu | L | Y | no compatible Ring-flash target exists | LQ-3 Ring-flash drafter acceptance-adjusted throughput check | llama.cpp fork
- L35 | cpu | L | Y | LQ-1/2/3 outcome (profile-gated) | LQ-4 profile-gated decision on dedicated L5 op | GGML_OP_LIGHTNING_ATTN path

## llama-cpp-dsa-contribution.md (4)
- L231 | gpu | L | Y | low priority | D4 root-cause flaky HIP bf16 LIGHTNING_INDEXER failure | ggml-cuda lightning-indexer, test-backend-ops.cpp
- L245 | none | L | N | runtime proof dense-mask scales with full KV | D2 sparse-attention upstream contribution | DSA attention path, glm4.cpp
- L246 | none | L | N | D2 real-sparse or new profile | D3 AVX-512BW Lightning Indexer CPU kernel | ggml-cpu lightning-indexer
- L247 | cpu | L | Y | GLM-5.2 UD-IQ2_M download pending | GLM-5.2 754B activation: download, verify, load-smoke | models/GLM-5.2-UD-IQ2_M

## llamacpp-v6-consolidation.md (6)
- L~77 (SHIFTED — re-grep) | none | M | Y | - | **READY** F1 fold paged-attn branch into v6, off-by-default | llama.cpp-v6 ops.cpp, ggml.h
- L100 | none | M | Y | operator review | Verify SWA slot-reuse fixes against upstream SWA | llama.cpp-v6 llama-kv-cache*.cpp
- L101 | none | S | Y | operator review | Decide fate of --moe-n-expert hard-mask CLI tool | llama.cpp-v6 common/arg.cpp
- L102 | none | L | Y | eval-gated; not in deployed registry | Decide on Differential-Transformer-V2 arch port | llama-model.cpp, convert_hf_to_gguf.py
- L97 | none | M | Y | operator review | Decide fate of streaming KV context-shift controls | llama.cpp-v6 server.cpp
- L98 | none | M | N | operator review; depends on F1 fold (L77) | Assess paged-attn overlap with upstream flash-attn | ops.cpp, ggml.h

## log-linear-gated-deltanet-readiness.md (3) — all external upstream watches
- L70 | none | S | Y | upstream release (external) | Check for public pretrained Log-Linear GDN checkpoint | handoff
- L71 | none | S | Y | upstream repo state (external) | Confirm reference repo ships inference code | handoff
- L72 | none | S | Y | upstream documentation (external) | Confirm architecture documented enough for GGUF converter | handoff

## loops-and-dashboards-audit-2026-07-05.md (1)
- L316 | cpu | L | N | **blocks OP-1**; owned by eval-tower/inference session | Root-cause real_suite_v1 run-instability, raise power below MDE 0.15 | eval_suite_discriminability.py

## master-handoff-index.md (3)
- L444 | none | S | N | operator ratification (human-amendment-only) | G1 ratify P-GPU-1 measurement trust boundary | MEASUREMENT.md
- L446 | gpu | L | Y | G1 P-GPU-1 ratification | G3 frontdoor residency bench under P-GPU-1 to Gate R | mi210-speed-campaign-summary.md
- L447 | gpu | L | Y | G0 and M4 verdicts | Fleet placement order: embedder/vision, op-offload prefill, drafters | mi210-big-model-…md

## mathsmith-hc-formalizer-eval.md (16)
- L108 | none | S | Y | operator/network approval | Check HF for MathSmith-HC GGUFs or upstream weights | ?
- L109 | none | L | N | HF weights download pending | Convert HF weights to Q4_K_M and Q8_0 GGUFs | convert_hf_to_gguf.py
- L110 | cpu | S | N | needs HC GGUF (L109) | Verify Q8_0 decode speed normal, confirm old conversion bug | scripts/benchmark/, summary.csv
- L111 | cpu | M | N | needs HC GGUF (L109) | Benchmark HC on existing formalizer test suite baseline | summary.csv rows 15-16
- L114 | cpu | M | N | needs HC-8B GGUF | Test Qwen3-0.6B as drafter for HC-8B | model_registry.yaml
- L115 | cpu | M | N | needs HC-8B GGUF | Test Qwen3-1.7B as drafter for HC-8B | model_registry.yaml
- L116 | cpu | S | N | needs L114/L115 drafter runs | Compare against Q4_K_M spec-decode n3 16.1 t/s ceiling | summary.csv
- L117 | cpu | M | N | ShortCoT artifact download pending | Evaluate MathSmith-HC-1.7B-ShortCoT drafter | model_registry.yaml
- L120 | none | M | Y | - | Design A/B protocol on aime and olympiadbench suites | dataset_adapters.py
- L121 | cpu | M | N | operator inference approval | Run baseline arm: solver answers raw problem directly | scripts/benchmark/
- L122 | cpu | L | N | needs HC artifact (L109) | Run formalizer arm: HC formalizes then solver answers | src/features.py input_formalizer
- L123 | cpu | M | N | solver availability + inference approval | Run A/B across three solver candidates | model_registry.yaml
- L124 | none | S | Y | needs S4 pipeline runs | Report accuracy delta, latency overhead, total pipeline time | scripts/analysis/
- L125 | none | S | Y | needs S4 runs across difficulty tiers | Analyze whether formalization gain scales with difficulty | scripts/analysis/
- L126 | none | M | Y | needs S4 runs | Report per-problem formalizer+solver token cost vs baseline | scripts/analysis/
- L127 | none | M | Y | - | Swap exact-match for Math-Verify answer comparison | dataset_adapters.py, eval scorer

## memento-block-reasoning-compression.md (5)
- L190 | gpu | L | N | peft/trl not installed; training window | S2 Stage-1 format-learning smoke on Qwen3-0.6B | memento_sft.py
- L191 | gpu | L | N | Stage-1 smoke passing | S2 Qwen3-1.7B LoRA validation, promote/stop decision | memento_sft.py
- L192 | gpu | L | N | env install + GPU training window | Install peft/trl, run the real Stage-1 SFT job | memento_sft.py
- L193 | none | M | Y | BLOCKED on S2 pass | S3 wire block-masking inference-time feature flag | orchestrator_stack.py
- L194 | cpu | L | N | BLOCKED on S2 pass | S3 Fold/Unfold toggle + short-m@k voting + Hadamard stacking | orchestrator_stack.py

## mi210-big-model-and-acceleration-roadmap.md (6)
- L127 | gpu | L | N | DR-3e P-GPU-1 certification outstanding | Complete broader K2 admission runner/package | dr3_…runner.py
- L156 | gpu | L | N | P-GPU-1 protocol + post-cutover operator gate | DR-3e rerun GPU claims under production kernel | dr3_*, data/dr3_*
- L159 | gpu | L | N | operator-gated; expert skew deprioritized | GLM-5.2 endgame expert-offload / REAP+IQ2 path | ?
- L161 | gpu | L | Y | K28.5 prototype gate | K28 default-off fused chunked GDN kernel for long prefill | gated_delta_net.cu
- L230 | gpu | L | N | needs cheap proof raising Phase-0 ceiling | K28.5 gate fused-recurrence prototype | gated_delta_net.cu
- L261 | gpu | L | Y | MI210 window + operator mid-stream quant decision | AXA-2 design/validate CPU→GPU re-prefill teleport cutover v1 | teleport.py, gpu_lease.py

## mi210-kernel-rnd-loop-proposal.md (4) — ORPHAN-adjacent
- L74 | none | M | N | - | Wire Pareto frontier + rewind-purge into kernel strategy store | scripts/kernel_rnd/kernel_store.py
- L75 | none | L | N | Phase 1 store wiring | Build nightshift outer planner + inner sweep-eval-Pareto loop | kernel_sweep.sh, scripts/nightshift/
- L76 | gpu | L | N | Phases 1-2 + operator GPU window | Run L3-MoE/L15 MMQ-family param sweep through the loop | ggml-cuda/mmq.cu, kernel_eval.sh
- L81 | none | L | N | Phase 1 strategy store | Build Phase 2 verify loop on OpenHyra Experience Bank pattern | kernel_store.py

## mi210-mfma-compute-bound-paths.md (1)
- L47 | none | S | Y | measurement gate failed both paths | Reopen MFMA kernel build only if a compute-bound path appears | ggml-cuda/mmq.cu, fattn*

## mi210-q8-dequant-gemv-roofline.md (3)
- L77 | gpu | L | N | operator-gated IQ2-vs-Q8 bench | Quantize 122B to IQ2 proxy; bench IQ2 vs Q8 decode/PPL | build-hip/, ggml-cuda/mmvq.cu
- L78 | gpu | L | N | only if coalescing measured poor (deemed healthy) | SoA-repack lever for Q8 weight layout | mmvq.cu, quantize.cu
- L79 | gpu | L | N | separate bet, not prioritized | Optional stream-K K-splitting for Q8-MMQ aggregate case | ggml-cuda/mmq.cu

## mi210-speed-campaign-summary.md (1)
- L70 | gpu | L | Y | **STALE?** MI-KB-1 declined harness (gfx942-only) | Run KernelBench baseline over v6 production kernel | kernel_eval.sh

## minddr-deep-research-mode.md (10)
- L13 | gpu | L | N | **gfx90a/ROCm training stack unverified** | Run gfx90a MI210 training-viability smoke for Phase 2 | ROCm/TRL smoke script
- L177 | none | M | Y | MD-9 not yet run | Consider PaperBench-style source-fidelity axis in MD-9 rubric | deep_research_sentinel.yaml
- L182 | cpu | L | N | inference window + search backend availability | MD-9 A/B sentinel suite with deep_research_mode 0/1 | deep_research_sentinel.yaml, src/graph/minddr/
- L183 | none | S | N | MD-9 must pass first | One-line dispatcher wiring for research-like route | chat.py dispatcher, minddr/graph.py
- L184 | none | M | Y | owned by eval-tower EV-9 | EV-9 multi-dimensional rubric scoring for non-structural MD-9 | rubric_scoring.py, safety_gate.py
- L185 | gpu | L | N | gfx90a training-viability smoke (L13) | Phase 2 MD-10..MD-13 four-stage RL specialization | ?
- L186 | none | L | N | durable >=5pp uplift over 3 weeks | Phase 3 MD-14 architect_planning/search/report role refactor | orchestrator_stack.py
- L195 | none | L | N | operator-review gate | Add rubric-as-execution-interface Review stage + adherence dimension | minddr/nodes.py, prompts/
- L207 | none | S | Y | - | **READY** Demote BrowseComp/WideSearch/xbench anchors to observation-grade | handoff
- L208 | none | M | Y | operator-review gate | Capture search trajectories for post-hoc leakage audit | SearxNG tool wrapper

## model-capability-descriptors.md (1)
- L40 | cpu | L | N | DAR-1 regret replay >=5% AND per-question eval vectors | Unified cascade: calibrated bilinear predictor + omega | model_descriptors.yaml, q_scorer.py

## model-stack-change-standardization-audit.md (7) — per-change procedural checklist
- L219 | none | S | N | fires per stack change | Identify the model-stack change type before touching inputs | ?
- L220 | none | S | N | L219 change-type identification | Update structured registry/descriptor inputs only | model_registry.yaml, stack_manifest.py
- L229 | none | S | Y | - | **TEMPLATE — DO NOT DISPATCH** — execute only during a concrete stack change; the owning runbook checkbox remains intentionally open | Run focused unit tests for priors, guard, scorer, admission | tests/unit/ suites
- L230 | none | M | Y | - | Run simulated mmap-swap, retirement, tier-change tests | tests/ simulated swap fixtures
- L234 | none | S | N | - | Update only generated summaries or explicitly historical docs | docs/runbooks/
- L235 | none | S | N | pre-launch gate | Require fresh priors + guard pass before any launch | stack-change gate, stack_priors.yaml
- L236 | none | S | N | post-launch of the stack | Compare live PIDs/ports/flags against priors, restart stale | stack_manifest.py --status

## model-stack-single-source-update-pipeline.md (7)
- L320 | none | M | Y | - | Preserve env override precedence + degraded fallbacks in migrations | src/config/models.py, stack_priors.py
- L322 | none | L | N | needs concrete duplicated-fact trigger | Migrate remaining high-risk P2 consumers | stack_change_surface_manifest.yaml
- L325 | none | S | Y | - | **CLOSED 2026-07-29** — audited generated-prior primary path and degraded fallbacks; no duplicated fact warrants churn | Keep three re-audited surfaces unchurned | seeding_rewards.py, corpus_quality_gate.py, kv_compress.py
- L330 | none | M | N | needs a newly migrated consumer to witness | Broaden W4 swap-CI as migrated consumers create witnesses | test_stack_priors_compiler.py
- L348 | none | S | Y | operator enablement/reload/attestation decision | Keep X-MAS production routing default-off | X-MAS policy config
- L350 | none | S | Y | - | Keep short_term_memory.md under review as live run state | scripts/autopilot/short_term_memory.md
- L352 | none | S | Y | - | Keep completed implementation logs out of active indices | progress/, handoffs indices

## model-stack-update-pipeline-audit.md (3) — ORPHAN
- L628 | none | M | Y | conditional on promotion-gate coverage proving insufficient | Add direct benchmark runtime enforcement | stack guard, promotion gate
- L631 | none | M | N | operator gate; native ctx_max not populated | Make null ctx_model_max a compile-blocking strict known-gap | model descriptors, model_registry.yaml
- L632 | none | L | N | - | Untangle scripts.server import cycle causing fail-open flake | runtime_facts_manifest.py, stack_paths.py

## moe-spec-cpu-spec-dec-integration.md (1)
- L404 | cpu | L | N | quiet window (no-concurrent-inference) | Live-MTP MoE verifier B-sweep with bit-exact guard | common/speculative.cpp

## multi-file-coding-completion-capability.md (4)
- L288 | cpu | L | N | coder-role A/B authorization; disk at 95% | Use bartowski Q8_0 for quant-matched coder-role A/B | model_registry.yaml, models dir
- L295 | none | M | N | needs clean-window A/B evidence + operator | Decide when routine coding edits auto-route to edit-mode | capability_registry.yaml, chat.py
- L296 | cpu | L | N | host-quiet window; pause J6 autopilot | Clean-window A/B over >=50 routine edit tasks with three gates | bep_edit_mode_wiring.py, bep_ab.py
- L297 | none | S | N | needs A/B evidence + one shadowed trial | Promote edit_transaction_auto_routing toward autopilot | capability_registry.yaml

## multimodal-pipeline.md (11)
- L177 | cpu | M | N | needs ratified ASR/MOS instrument or operator audition | M-2Q establish intelligibility/quality acceptance for TTS WAV | artifacts/minicpm-o-phase1-v8-…/m2-tts/
- L178 | gpu | L | N | **AutoPilot E8 baseline reseed must complete first** | M-3 execute vision role-swap via three-gates discipline | model_registry.yaml, promotion runbook
- L324 | cpu | M | Y | TTS deprioritized; Path D remains primary | Prototype FastAPI wrapper for Qwen3-TTS on port 8110 | ?
- L325 | cpu | M | N | depends on the Path-C prototype | Benchmark Qwen3-TTS VRAM and latency on EPYC | ?
- L326 | none | S | N | prototype + benchmark | Add feature-flagged worker_tts role to model registry | model_registry.yaml
- L327 | none | M | Y | - | Design voice-cloning guardrails before enabling TTS | docs/, handoff
- L406 | none | S | Y | **STALE?** Qwen3.5-Omni is API-only, no weights | Estimate CPU cost of ARIA audio-codec path on one NUMA node | handoff
- L503 | none | S | Y | upstream Alibaba weight release pending | Monitor for Qwen-Audio-3.0 open-weights/GGUF release | handoff
- L525 | cpu | M | N | operator trial approval + quiet window | Trial Z-Image-Turbo as latency-only candidate with Q8-vs-Q4 A/B | model_registry.yaml
- L526 | none | S | N | sd.cpp lora.hpp z_image key resolution unverified | Record rank-32 distill LoRA as Base↔Turbo conversion mechanism | sd.cpp lora.hpp
- L624 | cpu | L | N | queued after A2/RP-5; stack-down bench window | Bench MiniCPM-o Q4 CPU lane vs Qwen2.5-VL, decide promotion | artifacts/minicpm-o-*, runbook

## multiscreen-attention-evaluation.md (4)
- L320 | cpu | L | Y | download pending + inference window | HRM-1 fair HRM-Text-1B head-to-head vs Qwen3.5-1.7B | models/HRM-Text-1B, transformers CPU harness
- L321 | none | M | Y | HRM-1 result | HRM-2 decide llama.cpp investment vs transformers CPU | handoff, log-linear-gated-deltanet-readiness.md
- L322 | none | S | Y | HRM-1 must land first | HRM-3 defer any HRM production role assignment | handoff, model_registry.yaml
- L347 | none | S | Y | no cheap-first/edge/triage role opened | LFM2-1 standing no-bench/no-port posture for LFM2.5 | handoff

## non-inference-backlog.md (2)
- L56 | none | L | Y | DS-E1 evidence (Package B throughput, RI-10, DS-5) | NIB2-18 implement DS-6 QuarterScheduler after evidence | stack_templates.py, stack_numa.py
- L94 | none | M | Y | NIB2-32 live verdict | NIB2-46 STOP Phase 0 instrumentation: reserved token + hidden-state hook | llama.cpp server.cpp, src/graph/

## numa-prefill-decode-disaggregation.md (1)
- L76 | none | S | Y | xGMI KV-transfer falsification; multi-tenant shift | Reopen only on multi-tenant shift | handoff

## objective-task-rate-goodput.md (2)
- L46 | none | M | N | operator flip decision (Option C tripwire armed) | W3 flip live dominance to 3-D task_rate vector, retire t/s | tier_specs.py, pareto_archive.py
- L75 | cpu | L | N | next instrument era; batching integration | W5 add sparse/steady/burst offered-load profiles | eval_tower.py, tier_specs.py

## opendataloader-pipeline-integration.md (17) — **LIVE / OWNED, DO NOT DISPATCH** (line numbers shifted this session)
- L159 | gpu | L | N | needs full-set ODL re-baseline (L613) | LightOnOCR vs docling-fast as structural/table parser candidate | odl_bench/, pdf_router.py
- L160 | gpu | S | N | L159 parser-quality comparison | Measure LightOnOCR latency inside parser-quality comparison only | odl_bench/
- L161 | none | M | N | benchmark-backed routing-policy evidence | Three-way routing: ODL local, ODL hybrid, LightOnOCR | pdf_router.py, document_preprocessor.py
- L163 | cpu | L | N | external 200-PDF corpus (local ceiling 51) | Compare our pipeline vs ODL/docling/marker on 200 PDFs | pdf_fastpath_probe.py
- L164 | none | S | Y | L163 comparison run | Publish 200-PDF comparison results in progress log | progress/
- L405 | none | S | Y | Git LFS dataset download pending | Clone opendataloader-bench repo with 200 LFS PDFs | /mnt/raid0/llm/opendataloader-bench/
- L410 | gpu | L | N | L405 clone; dataset absent | Baseline pdftotext+LightOnOCR pipeline on 200 PDFs | odl_bench/, pdf_router.py
- L464 | none | S | N | conditional: cost becomes bottleneck | Cite W-RAC as prior art in Phase 2 design | handoff
- L512 | cpu | M | N | Phase 3 benchmark integration | Add intrinsic chunk-quality scores alongside NID/TEDS/MHS | odl_bench/
- L534 | cpu | M | N | liteparse dependency missing (51/51 fail) | Bench LiteParse vs ODL-local vs pdftotext | pdf_fastpath_probe.py
- L535 | none | S | N | L534 bench outcome | Route dense-table/scanned docs away from LiteParse | pdf_router.py
- L557 | gpu | L | N | PaddleOCR-VL arm voided (L615) | Compare LightOnOCR table-competent arm vs ODL/PaddleOCR | odl_bench/paddleocr_vl.py
- L613 | cpu | L | N | - | Re-baseline ODL end-to-end on full 1651-page OmniDocBench | odl_bench/, datasets/omnidocbench/
- L615 | gpu | L | N | PaddlePaddle PaddleOCRVL pipeline not installed | Void and re-run PaddleOCR-VL arm through real pipeline | odl_bench/paddleocr_vl.py
- L616 | gpu | L | N | GGUF/architecture pre-check + intake entries | P1 evaluate MinerU2.5-Pro and GLM-OCR | intake_index.yaml, odl_bench/
- L617 | gpu | L | N | model download; experimental branch only | P2 add Unlimited-OCR single-pass arm at Q5_K_M | odl_bench/, models/
- L629 | cpu | M | Y | PageIndex unbounded per-query LLM calls | Probe ODL markdown into PageIndex md_to_tree consumer | document_chunker.py

## orchestration-robustness-audit-2026-07-11.md (7)
- L155 | none | S | Y | operator run/pause decision | P0.1 operator decides run or pause for autopilot candidate species | start_fable_authority_daemon.py
- L156 | none | M | Y | **operator signature (MEASUREMENT human amendment)** | P0.2 sign P2 amendment bundle, discriminability gate, P3 canary | p0_2_amendment_bundle_inputs*.json
- L159 | none | M | Y | approval token ERA_FENCED_BLACKLIST_PURGE_2026_07_11 | P0.3 era-fenced blacklist purge + lever re-exploration | blacklist_purge_plan.py
- L184 | none | S | Y | file is root:root 0444; needs operator/sudo | Add seq_p0_2_bridge consent or apply formal amendment | orchestration/authority_consent.json
- L198 | none | L | Y | HIGH blast radius (22 upstream impacts) | W1 consolidate remaining runtime-facts readers | orchestrator_runtime_facts.json readers
- L240 | none | S | Y | - | **CLOSED 2026-07-29** — startup janitor excludes open inodes and is best-effort, with six focused tests | Startup sweep unlinking old unopened faiss tmp orphans | repl_memory/faiss_store.py
- L241 | none | S | N | depends on L240 sweep + 24h age | Sweep the 7 remaining 5.1GB tmp files once aged out | repl_memory/sessions/*.tmp

## outer-coordinator-learned-head.md (6) — a clean self-contained scoping arc, all `none`-lane
- L91 | none | M | N | - | OC-0.1 inventory per-turn autopilot decisions into a table | scripts/autopilot/, handoff
- L92 | none | S | N | OC-0.1 table | OC-0.2 classify each decision uniform/context-dependent/arbitrary | handoff
- L93 | none | M | N | - | OC-0.3 identify fitness signal the learned head optimises | handoff
- L94 | none | M | N | autopilot per-run token telemetry | OC-0.4 cost-benefit estimate of Claude tokens replaced | scripts/autopilot/digest.py
- L95 | none | M | N | - | OC-0.6 populate learned-coordinator design-space reference table | handoff
- L106 | none | S | N | OC-0.1..0.4 + OC-0.6 | OC-0.5 decide escalate to OC-1+ or close not_pursued | handoff

## per-request-reasoning-budget.md (4)
- L208 | cpu | M | N | needs running server | Step 3 force close-think at budget=0 for hybrid SSM | reasoning-budget.cpp, llama-context.cpp
- L209 | cpu | M | N | Step 3 (L208) | Step 4 verify budget cap and no pure-MoE regression | reasoning-budget.cpp, server-task.cpp
- L210 | none | M | Y | - | Thread thinking.budget_tokens through ChatRequest per role | ChatRequest model, orchestrator API
- L211 | none | M | Y | - | Design stop-signal abstraction for CGR/SpecExit exit hooks | reasoning-budget.cpp

## pipeline-integration-index.md (9) — index pointers
- L99 | gpu | L | Y | MI210 landed, unblocked | P0.5 prompt-enhancer, content-filter, typography, GPU DiT rebench | ernie-image-turbo-evaluation.md
- L100 | cpu | L | Y | - | P1 benchmark-backed ODL hybrid-vs-baseline + routing policy | pdf_router.py, opendataloader-…md
- L102 | cpu | L | Y | - | P2 Leanstral expert profiling, REAP prune, end-to-end proof | leanstral-architecture-analysis.md
- L103 | cpu | L | Y | - | P3 benchmark first viable TTS path with RTF/WER evidence | multimodal-pipeline.md
- L104 | cpu | M | Y | pending in owning multimodal-pipeline handoff | MiniCPM-O Phase 1 testing carried from retired vision row | multimodal-pipeline.md, src/vision/
- L105 | none | M | Y | needs measured wiki cross-link gap | P5 deferred K8 wikilink scorer | src/retrieval/, internal-kb-rag.md
- L106 | cpu | L | Y | inference-window gated | P5 AutoWiki model-backed page writer | internal-kb-rag.md, src/retrieval/
- L107 | none | S | N | decision-only from existing sweep | Decide recency_w0.3_s90 default-retrieval-weight promotion | src/retrieval/ default weights
- L108 | cpu | M | N | inference-window gated; measure-first | Measure K11 FTS5 lexical signal before default-weight promotion | src/retrieval/ FTS5 signal

## prompt-construction-determinism.md (2)
- L67 | cpu | L | N | clean window co-scheduled with N13 post-reboot bench | D3 manual canonical bench certifying sampling-quality changes 1-3 | bench_canonical.sh, canonical_recipe.py
- L68 | none | S | N | needs D3; human-amendment surface | D4 author sampling-determinism autopilot_quality era row | instrument_eras.yaml

## qwen-mtp-llamacpp-port.md (2) — ORPHAN
- L85 | cpu | L | N | operator gate + parent T1 dense gate-bench | P6b operator-gated model load and MTP gate bench | build-ap-mtp, Qwen3.6-35B-A3B-MTP-GGUF
- L86 | cpu | L | N | rides #22673 reconciliation; needs EPYC frequency map | P7 FR-Spec draft LM-head vocab-trim, measure end-to-end | qwen35.cpp, speculative.cpp, eagle3.cpp

## qwen36-27b-cpu-feasibility.md (4) — PARKED
- L115 | cpu | M | N | PARKED — reopen only if 27B is a real role candidate | P1 CPU throughput probe single-instance + NUMA-4-way Q4_K_M | scripts/benchmark/, model_registry.yaml
- L116 | cpu | L | N | PARKED — same reopen trigger | P2 coder-escalation quality A/B vs Qwen2.5-Coder-32B | scripts/benchmark/, dataset_adapters.py
- L117 | none | S | N | task P1 | Append measured P1 throughput + baseline comparison | handoff
- L118 | none | S | N | task P2 | Append agentic score table; propose registry swap if gates pass | handoff, model_registry.yaml

## rao-redel-substrate-spike.md (9)
- L414 | cpu | L | N | operator approval; no delegating workload | Run naturally-delegating workload A/B before Step 3 | rao_redel_step2_ab.py
- L415 | none | S | Y | operator decision | Push/PR sub-decision-taxonomy branch | subdecision_taxonomy.py, episodic_store.py
- L416 | none | L | N | delegation-positive re-test (L414) | Step 3 conditional substrate replacement, 400-800 LoC | repl_executor.py
- L431 | none | S | Y | superseded by 07-21 correction | Keep max_depth 0-1 default, recursion only for failing baselines | repl_executor.py
- L432 | none | M | Y | - | **READY** Adopt SkyRL parent/child rollout-tree accounting shape | episodic_store.py
- L445 | none | M | Y | - | Reframe depth as conditional surface gated on predicted failure | handoff, repl_executor.py
- L446 | none | L | N | needs learned-routing-controller surface | Build escalation-prediction surface jointly with COMP_r probe | src/classifiers/
- L447 | none | M | N | needs escalation surface (L446) | Gate depth escalation on expected value | repl_executor.py
- L453 | none | M | Y | source/licence check | Evaluate adopting OOLONG suite adapter sized to depth question | dataset_adapters.py, BENCHMARKS.md

## re4-protocol-redesign.md (5) — ORPHAN
- L147 | cpu | M | N | operator quiet window; autopilot stopped | RE-4.2 frontdoor 30-row non-saturation probe at R=4096 | longcot_mini_stack_runner.py
- L148 | cpu | L | N | RE-4.2 in-band; runner parity L151 | RE-4.3 full 402-row two-phase reference run both roles | longcot_mini_stack_runner.py
- L149 | cpu | L | N | RE-4.3 complete | RE-4.4 reasoning-budget ladder at R 512 to 4096 | longcot_mini_stack_runner.py
- L150 | none | S | N | RE-4.3/4.4 artifacts | RE-4.5 package artifacts, write terminal ledger row | inference-batch/bundles/RE-4/
- L151 | none | M | N | must precede RE-4.3 | Verify runner persistence, confidence provenance, infra-error exclusion | longcot_mini_stack_runner.py

## reasoning-compression.md (9)
- L96 | none | M | Y | difficulty-signal re-validation n>=100 | Implement enforce mode routing easy→worker, hard→architect | difficulty_signal.py, classifier_config.yaml
- L98 | cpu | L | Y | model server availability | Generate SEAL control vectors for Qwen3-32B (Action 8) | generate_pairs.py, eval_cvectors.py
- L103 | cpu | L | Y | shared with context-folding Phase 2 | Summarizer quality assessment via judge eval across model tiers | eval_trimr.py pattern
- L246 | cpu | L | Y | must be re-scoped per RC-RE-1; needs E7 tower | RC-RE-2 validate compression safety on held-out reasoning suites | eval tower suites
- L611 | none | S | N | - | Add Tier-0 pre-compressed-checkpoint rung seeded with ThinkingCap | handoff
- L612 | cpu | L | Y | - | Add Behavior-Conditioned Inference as Tier-1 candidate and measure | trace store, eval_metrics.py
- L613 | cpu | M | N | BCI candidate build (L612) | Score total pipeline tokens, not decode-only, for BCI claim | eval_metrics.py
- L614 | none | M | N | BCI adoption (L612) | Held-out validation gate + append-only behavior handbook guardrails | behavior handbook store
- L631 | none | S | Y | upstream Loopie artifact release pending | Loopie artifact watch: recheck HF/GitHub before port planning | intake_index.yaml, handoff

## reasoning-effort-levels.md (19)
- L103 | gpu | L | N | operator inference approval (P-GPU-1) | TB-1 sweep max_tokens per stack model, find truncation knee | v7_quality_gate_runner.py
- L109 | none | M | Y | needs TB-1 curves | Test single mostly-ok budget captures 90% of max accuracy | architect_bench_analyze.py
- L113 | none | S | Y | needs TB-1 knees | Audit live reasoning_budget ceilings against measured knees | model_registry.yaml
- L116 | gpu | L | N | needs TB-1 and E-2 | Measure 2-D effort x budget grid per model | v7_quality_gate_runner.py
- L140 | none | M | Y | operator gate (production config) | Plumb per-request max_tokens/reasoning_budget as router tunable | chat_pipeline/, model_registry.yaml
- L186 | gpu | L | N | - | Finish v8 np×L grids + prefill-to-depth RAG instrument | artifacts/np_context_study_v8_20260727/
- L204 | gpu | L | N | needs v8 grids terminal | Prefill-to-depth variant + extract per-model kv_bytes/token | artifacts/np_context_study_v8_…/
- L212 | cpu | L | N | CPU lineage window (session split) | A2 CPU 122B-Q4 np×context batching-collapse surface | study_np_context*.sh
- L215 | none | L | N | needs kv_per_token constants (TB-6-exec d) | VRAM+bandwidth-aware admission control | chat_pipeline/routing.py
- L242 | none | L | N | GPU joining orchestration stack (operator gate) | Wire np×budget surface into router as serving policy | orchestrator_stack.py
- L317 | gpu | M | N | operator inference approval | Test whether 122B loops on architect workload vs boxed prompts | probe_reppen.sh
- L321 | none | S | Y | operator gate (registry change) | Add per-model repeat_penalty 1.1 default for 122B-A10B | model_registry.yaml
- L324 | cpu | L | N | CPU quiet window (A2 arm) | Clean Q4-vs-IQ2 parity read with repetition fence on | v7_quality_gate_runner.py
- L332 | gpu | L | N | operator inference approval | E-2 sweep effort levels per model, build Pareto curve | v7_quality_gate_runner.py
- L341 | none | M | Y | needs E-2 curves | Score effort levels by rescue-rate not mean accuracy | architect_bench_analyze.py
- L345 | none | M | Y | needs E-2 frontdoor+architect curves | E-4 set per-role defaults as (model × level) pairs | model_registry.yaml
- L351 | none | M | Y | - | **READY** Add validator flagging stale effort level after model swap | model_registry.yaml, scripts/registry/
- L356 | none | L | Y | needs E-4 + difficulty signal | Router picks effort level from assessed task difficulty | difficulty_signal.py, routing.py
- L369 | gpu | M | N | operator inference approval | Retest reasoning-budget cap on non-saturated olympiadbench_numeric | run_budget.sh, e6_budget_analyze.py

## repl-session-memory-maturity.md (6)
- L77 | none | L | Y | not scheduled; needs real DataFrame workload | Typed columnar DataFrame codec instead of pickle allowlist | state.py, safe_pickle.py
- L140 | none | M | N | task D-c1 measurement | Carry executed code log into resume preamble | state.py, repl_executor.py
- L145 | none | M | N | needs T3 live-traffic slice | Instrument resumed sessions for preamble size, re-derivation | repl_executor.py, state.py
- L151 | none | S | Y | task D-c1 | Decide or close D-c on measured numbers | handoff
- L153 | none | L | N | - | Agent-facing annotate/pin curation layer over auto-save | state.py, repl_executor.py
- L162 | none | S | Y | task D-c1 | Decide whether to raise 12/8 resume truncation defaults | state.py

## repl-turn-efficiency.md (9) — **LIVE / OWNED, DO NOT DISPATCH**
- L18 | cpu | L | N | - | S4 Omega A/B: turns, token cost, accuracy delta | src/repl_environment/, agents/*.md
- L84 | none | S | Y | **WITHDRAWN** by 2026-07-21 correction | Port interval-F1 span scorer (do not port) | debug_scorer.py
- L106 | cpu | M | N | - | Strategy-prompt-length ablation across existing agent roles | agents/*.md, eval harness
- L107 | cpu | M | Y | - | Audit REPL prompt construction and slot prefix-cache hit rate | context.py, llama-server /slots
- L114 | none | S | Y | - | Record standing caution on RLM prefill-to-decode conversion | handoff
- L115 | none | M | N | - | Adopt Main Model Token Efficiency metric for scaffold A/Bs | eval tower metrics module
- L116 | none | S | Y | - | Compare RLM budget constants against our REPL constants | src/repl_environment/ config
- L118 | cpu | M | N | rides S4 Omega A/B | Add intake-537 open-weight RLM prompt as third arm | agents/ prompts
- L119 | cpu | M | N | - | Measure root vs sub-agent prefix-cache hit rates separately | /slots telemetry, context.py

## repo-readiness-scorer.md (2)
- L414 | none | L | Y | - | Close remaining root L5.self_optimizing_loop 13-item queue | repo_readiness_scorer.py
- L415 | none | L | Y | - | Raise epyc-llama from L3 to L4 across six readiness criteria | epyc-llama docs/CI surfaces

## research-evaluation-index.md (11) — index pointers
- L80 | cpu | S | N | EV-11b ECE-binning operator decision | Math-Verify scoring re-baseline after scorer flip | eval_tower.py
- L81 | none | M | N | serving-path freeze | Execution-free patch verifier live-dispatch gate wiring | patch_pre_gate.py
- L82 | cpu | M | N | - | Build review-finding-F1 suite from intake-658 | eval suite yaml, eval_tower.py
- L84 | none | S | N | owner handoff frontier-f1 | Fold Simula double-critic into F1-DGM scoping | frontier-f1-real-task-corpus.md
- L151 | cpu | L | N | W8 keepable-candidate evidence + operator cutover | N2 per-question ledger + sequential verdict readiness | sequential_verdict.py
- L152 | cpu | L | N | live promotion-eval evidence for W8 | N1+N4 evidence-plane instrument repair tails | eval_tower.py
- L153 | cpu | L | N | inference gate EV-4/5/8; EV-9 judge selection | Eval-tower tails EV-4/5/8/9/10 + MD-9 A/B | eval_tower.py
- L154 | cpu | M | N | observation accrual (1 of 100 compressed calls) | P4e rollout decision + repo-readiness remediation | tool-output compression module
- L156 | cpu | L | N | - | AP-16 token-bloat probe, ledger wiring, W2 close | eval_tower.py
- L158 | cpu | M | N | Gemma4 MTP serving fix | Granite Phase C decision + K-ROPE-1 matrix | embedder bench config
- L159 | none | S | N | - | Reasoning-compression tails and monitoring-only watches | reasoning-compression.md

## retrain-routing-models.md (3)
- L125 | cpu | M | N | operator rollout decision + clean window | Operator: run --keep-enabled bracket to enable live routing | routing_classifier_rollout_window.py
- L126 | none | L | Y | Fable 5 freeze gate (DAR-1 regret >=5%) | Step 4/5 GAT and SkillBank retrains | train_graph_router.py, distillation/pipeline.py
- L127 | none | S | N | steps 4/5 + rollout decision | Step 7 delete handoff once retrain sequence completes | handoff, master-handoff-index.md

## reviewer-calibration-accounting.md (5)
- L27 | none | S | Y | **operator PR (MEASUREMENT human-amendment-only)** | Land P-REV-1 blocks into MEASUREMENT | MEASUREMENT.md
- L29 | cpu | L | N | operator gate OP-6a/6b via RCP-W1 | RC-8 shadow self-review baseline on corpus v1; first FA/FR | reviewer_calibration_report.py
- L30 | none | M | Y | - | **READY** Persist full rubric + per-item grades in corpus rows | src/trace/review_ledger.py
- L105 | none | S | N | operator PR; do before RC-6a | Add chance-corrected agreement + confusion matrix to P-REV-1 | MEASUREMENT.md
- L106 | none | S | N | operator PR | Declare tie/abstention estimand and report its rate | MEASUREMENT.md

## reviewer-control-plane-index.md (7) — H0 rollups over 9 leaves
- L28 | none | L | N | - | P1/M1 trace materialization, durable resume, schemas, GBNF gating | src/trace/store.py, validate_ir.py
- L29 | cpu | L | N | P1/M1 | P2/M2 shadow decision plane, rubric reviewer, 50-q replay | sequential_verdict.py, gate_runner.py
- L30 | gpu | L | N | G1 P-GPU-1 ratification | P3 GLM reviewer gates, kernel follow-ups, GPU bets 1-4 | gemma-challenge-…md
- L31 | cpu | L | N | M2 | P4/M3 knob registration, Pareto axes, screening driver, tournament | eval_tower.py, src/features.py
- L32 | none | L | N | M3 | P5/M4 escalation policy from curves, escalate-default, gated rebuttal | src/roles.py, runtime_flags.json
- L87 | none | M | N | operator PR (human-amendment-only) | Add Cohen kappa + prevalence disclosure to P-REV-1 draft | MEASUREMENT.md
- L88 | none | S | N | operator PR (same P-REV-1 window) | Declare tie/abstention estimand explicitly | MEASUREMENT.md

## reviewer-decision-plane.md (1)
- L32 | cpu | L | Y | shadow reviewer window; feeds H-LB baseline | RD-12 per-decision latency/token accounting + 50-question replay | review_service.py, src/autopilot_core/

## reviewer-escalation-and-human-gate-policy.md (8)
- L20 | none | M | N | H4/H5 reliability curves do not exist yet | Per-domain confidence threshold policy from calibration curves | policy config
- L21 | none | S | N | HG-1 thresholds; H3 RD-3 events | Verifier-disagreement escalation rule for conclusive gates | reviewer policy module, SafetyGate
- L22 | none | S | Y | - | **READY** Protected-action list aligned with existing SafetyGate | SafetyGate protected-action config
- L23 | none | S | Y | operator decision (OP bundle cadence) | Escalation-precision human-audit sampling cadence protocol | handoff
- L24 | none | M | Y | - | Server-side escalation fields and x_* override | src/api /v1 response models
- L25 | cpu | L | N | offline A/B must show signed net-flip | Optional two-sided single rebuttal round pre-escalation | reviewer loop, A/B harness
- L26 | none | S | Y | HS-4 harness selection (FROZEN) | Harness-side escalation UX, frozen pointer only | harness-selection-…md
- L27 | cpu | L | N | P-AB-1 + P-REV-1 + H-LB LB-6 budget gate | Policy A/B and promotion of escalation thresholds | A/B harness, promotion gate

## reviewer-latency-and-sampling-budget.md (7)
- L20 | cpu | M | N | needs H3 RD-12 replay baseline | LB-1 reproduce and attribute review-latency throughput regression | eval_tower.py, proactive_delegation/
- L22 | none | M | N | - | LB-3 remaining k% sampling, quick_mode tiering, fan-out effort rules | proactive_delegation/, review_plane_knobs.yaml
- L23 | cpu | L | N | LB-3 policies + clean bench window | LB-4 paired throughput A/B per sampling policy under P-AB-1 | eval_tower.py, review_plane_knobs.yaml
- L25 | none | S | N | **operator gate OP-5(b) threshold value** | LB-6 budget gate: metric drafted, threshold still unpicked | review_plane_knobs.yaml
- L27 | none | S | N | **operator decision OP-5b (§A00)** | LB-6b operator picks one of three candidate gate thresholds | operator decision queue §A00
- L28 | cpu | L | N | needs H4 instrument + H5 anchor arms | LB-7 M3 baseline floor: full plane vs single augmented LLM | eval_tower.py, A0/A1 arms
- L29 | none | S | Y | LB-4/LB-7 numbers not yet measured | LB-8 publish standing numbers into the H0 index section | reviewer-control-plane-index.md

## reviewer-model-ablations.md (8) — all downstream of RM-3/RM-4
- L37 | gpu | L | N | A4g needs skew profile; Ref needs operator budget | RM-2 complete A4g hot-expert + external Ref judge arms | data/reviewer_model_ablations/
- L42 | cpu | L | N | placement-queue-not-/chat transport discipline | RM-3 define screening-tier protocol and Pareto promotion rule | screening_tier_runner.py
- L47 | gpu | L | N | RM-3 promotions + operator bench window | RM-4 confirmation-tier paired N>=100 with Holm correction | sequential_verdict.py
- L48 | gpu | L | Y | folds into RM-4 protocol | RM-5 six content-bias injection probes; score robustness rate | scripts/benchmark/
- L49 | gpu | M | Y | leading arm from RM-4 | RM-6 RA-8 field-order A/B: evidence-first vs verdict-first GBNF | screening_tier_runner.py
- L50 | gpu | M | Y | winning pair from RM-4 | RM-7 ablate with/without verifier-request access | scripts/benchmark/
- L51 | none | M | N | RM-4 and RM-7 results | RM-8 write report; annotate registry with calibration profiles | model_registry.yaml
- L52 | gpu | M | Y | A4 failed 2026-07-19 | RM-9 deferred A5 reviewer-as-architect GLM-5.2 solo arm | data/reviewer_model_ablations/

## reviewer-trace-materialization.md (1)
- L28 | cpu | M | Y | TM-7 parity closed; gates H4 | TM-8 coverage gate: 50-question replay, phase tags, executor-model-id | review_service.py, src/trace/query.py

## rlm-contested-claims-self-evaluation.md (6)
- L60 | cpu | L | N | inference availability (CPU window) | E1 measure Base vs Depth-1 on synthetic NIAH | fast-rlm niah_benchmark.py
- L68 | none | S | Y | - | **READY** Format-robust scorer, or strict plus lenient scoring | niah scorer module
- L71 | none | S | Y | rescoped to repl-session-memory-maturity D-c1 | Pointer only; no synthetic REPL-memory arm here | repl-session-memory-maturity.md
- L78 | cpu | L | N | inference availability; E1 first | E3 add non-RLM long-context baseline arm | fast-rlm _harness.py
- L80 | none | S | Y | - | Fold intake-925 Table 1 into E3 hypothesis | handoff, research/intake_index.yaml
- L89 | none | S | Y | needs E1/E3 first-party results | Write depth resolution into spike caveat and N17 | rao-redel-substrate-spike.md

## rocm-verify-profile-backend.md (8)
- L27 | none | M | Y | - | Pin GEAK/Apex/AgentKernelArena commits, check licenses, draft env recipe | research/deep-dives/…geak-synthesis.md
- L28 | gpu | L | N | operator GPU approval (P-GPU-1) | Install torch-ROCm, reproduce GEAK-eval + AgentKernelArena | scripts/kernel_rnd/
- L29 | gpu | L | N | MI210 bring-up | Harden oracle with exploit defenses and unseen-shape generator | c6_reward_integrity.py
- L30 | gpu | L | N | MI210 bring-up | Gate reward on vendor baseline, add E2E hot-patch exit gate | scripts/kernel_rnd/
- L31 | gpu | L | N | MI210 bring-up; rocprof-compute gfx90a subset | Derive usable gfx90a profiler-metric signal, three fallback tiers | scripts/kernel_rnd/
- L32 | gpu | L | N | C2/C3 hardening complete | Seed suites with EPYC ops, A/B controllers as adapters | scripts/kernel_rnd/
- L33 | gpu | L | N | Triton loop working | Add HIP arm toward hand-HIP kernels for llama.cpp fork | llama.cpp-mi210-hip/
- L58 | none | M | Y | host access outside devcontainer | Verify real sandbox backend on host, drop unsandboxed override | c6_reward_integrity.py

## routing-and-optimization-index.md (9) — index pointers
- L25 | none | M | Y | **STALE?** owning handoff marks this `[x]` 2026-07-22 | COMP_r leave-one-objective-out AUC probe | retriever.py, routing_classifier.py
- L31 | none | L | Y | EP probe refuted; needs EP-5 label fix | Develop escalation-prediction surface with competence feature | learned-routing-controller.md
- L651 | none | M | N | **operator-signed P0.1-P0.3 era-fence amendment** | Evidence-plane readiness/authority gates; stop accruing W8 | evidence-plane-ledger-…md
- L652 | none | M | Y | - | Stack-change SSoT upkeep; broaden swap-CI witness surfaces | scripts/validate/, model_registry.yaml
- L653 | none | L | Y | - | Offline reward-oracle eval on 20260707T015010Z collection rows | scripts/autopilot/, reports/
- L655 | cpu | L | N | enforce-arm factuality lift | Routing canaries and classifier rollout | factual_risk.py, classifier_config.yaml
- L656 | cpu | L | N | quiesce window | Dynamic stack, within-role placement, contention probes | orchestrator_stack.py, round_robin.py
- L657 | cpu | L | Y | P1 tier ahead of it | Delegation/context/edit harness DCP-5/J7 + BEP bake | scripts/autopilot/, src/api/
- L658 | cpu | L | Y | DAR/tri-role/OC frozen | Research-derived routing experiments, web tails, Fusion design | program.md, src/tools/web/

## routing-intelligence.md (9)
- L22 | cpu | L | N | hold: factuality_no_enforce_lift packet | RI-10 shadow-to-enforce canary decision on factual-risk control | ri10_canary_decision_report.py
- L30 | cpu | M | N | RI-10 pass | RI-11 expand enforce to frontdoor 100% + worker_general | classifier_config.yaml, factual_risk.py
- L31 | cpu | M | N | RI-11 pass | RI-12 global enforce + dashboard and q-scorer updates | classifier_config.yaml
- L32 | cpu | L | N | only if RI-10 suggests band/threshold change | RI-9b fresh threshold/Pareto sweep | seed_specialist_routing.py
- L33 | none | S | N | J14 swarm-fanout A/B gate (DAR-6) | RI-13 injection-risk classifier fork | handoff
- L34 | none | S | N | learned-routing-controller P5.2 pass | RI-X document new-model cold-start onboarding contract | handoff, onboard_specialist.py
- L116 | none | S | N | upstream J-space open-weight availability | RI-JS-1 monitor J-space tools for open-weight compatibility | handoff
- L117 | cpu | L | N | RI-JS-1; substrate unavailable for open weights | RI-JS-2 evaluate geometric routing augmenting MemRL retrieval | repl_memory/, src/classifiers/
- L128 | none | S | N | - | RI-CMP-1 file prompt-router encoder as monitor_only comparator | intake_index.yaml, handoff

## sarathi-serve-cpu-evaluation.md (2)
- L14 | cpu | L | N | operator bench window (E2 trigger already fired) | Re-evaluate chunked prefill for the eval-batch serving class | llama-server -ub sweep
- L141 | none | S | N | trigger materialized 2026-07-18; awaits re-promotion | Re-promote handoff status on the fired workload shift | handoff, master-handoff-index.md

## scaffold-autopilot-cost-lever-deployment.md (12)
- L104 | none | S | N | live autopilot agent holds daemon | T0.1 get daemon handback + operator go-ahead recorded | handoff
- L109 | gpu | M | N | T0.1 approval; MI210 residency Gate R | T0.2 host Qwable reasoner as stack-managed GPU service | orchestrator_stack.py, model_registry.yaml
- L112 | gpu | L | N | T0.2 | T1.1 build scaffold-then-nothink composite executor | chat_pipeline/, llama_server.py
- L113 | none | M | Y | T1.1 | T1.2 wire composite as a think_harder reasoning-effort rung | src/graph/think_harder.py
- L116 | gpu | L | N | T1.1 | T2.1 extend cost_metrics with GPU second-device term | q_reward.py, eval_tower.py
- L117 | none | S | Y | T2.1 | T2.2 decide/document composite route cost_tier assignment | eval_tower.py, safety_gate.py
- L120 | none | M | Y | - | **READY** T3.1 add scaffold_eligible sub_decision + difficulty-keyed retrieval | subdecision_taxonomy.py, episodic_store.py
- L121 | none | M | N | T2.1 and T3.1 | T3.2 feed composite outcomes into Q-value updates | q_reward.py, episodic_store.py
- L124 | none | L | Y | T3.1 signal shape | T4.1 replay traces offline to build eligibility table | journal_snapshot_replay.py
- L125 | none | S | N | T0.1 operator approval | T4.2 add placeholder scaffold_then_nothink capability row | capability_registry.yaml
- L128 | none | M | Y | operator protocol approval | T5.1 codify P-QUAL-T1 quality-parity + blended-cost deploy protocol | MEASUREMENT.md
- L129 | gpu | L | N | T5.1 gate + W4 preconditions | T5.2 shadow canary on eligible classes, then promote | capability_registry.yaml

## scorer-fork-drift-audit-2026-07-22.md (3)
- L256 | none | M | N | eval_tower.py single-writer (inference-batch loop) | Unify duplicated in-band-error and forced-role guard helpers | seeding_scoring.py, eval_tower.py
- L257 | none | S | Y | - | **READY** Guard or delete legacy ComparativeResult reward-injection path | seeding_legacy.py
- L258 | none | M | Y | - | Port B7 to research debug_scorer or stamp pre-B7 era | research debug_scorer.py

## scoring-infra-standardization.md (17)
- L35 | none | L | Y | - | Migrate research consumers to canonical answer_scoring; delete dup extractors | score_benchmarks.py, lib/scorer/
- L48 | none | L | Y | operator gate (production reward path) | Vendor canonical contract into orchestrator; fix truncation bias | review_service.py, debug_scorer.py
- L82 | none | M | N | needs +pids in cgroup.subtree_control (root) | Bound scorer process/thread count via cgroup v2 pids.max | code_exec_scorer.py
- L87 | none | M | N | bwrap package install | Wrap code_exec_scorer in bubblewrap sandbox with unshare-net | code_exec_scorer.py
- L104 | gpu | L | N | sequenced after 2b-laguna (operator) | Expand SWE gold slice 40 to 150+; rerun A3/A4 | artifacts/architect-code-eval-20260724/
- L107 | gpu | L | N | operator gate: llama.cpp kernel upgrade | Bring up Laguna-S-2.1, spec-dec sweep, SWE-oracle rung | model_registry.yaml, models/Laguna-S-2.1-GGUF/
- L130 | gpu | S | N | 2b-agentic-smoke | Re-verify testbed clean-at-base assumption on second trial | agentic_swe_harness.py
- L133 | gpu | M | N | GPU free post-Laguna kernel work | Live smoke of agentic harness then 10-instance pilot | agentic_swe_harness.py
- L144 | none | M | Y | operator + discriminativeness evidence | Prepare E7 eval-pool registration options package | instrument_eras.yaml, architect-bench-runbook.md
- L148 | gpu | L | Y | LCB v5/v6 dataset download | Pull post-cutoff LiveCodeBench window; re-validate oracle | dataset_adapters.py, data/
- L152 | none | M | Y | arms' results land (2b-confirm) | Replace runbook P2 placeholder with built coding ladder | architect-bench-runbook.md
- L158 | cpu | L | N | - | Run tool-use eval through orchestrator live REPL loop | agentic_swe_harness.py, src/graph/
- L162 | cpu | M | Y | Jackrong-family bench scheduled | Pin and verify per-model tool-call parser before Jackrong bench | scripts/benchmark/, model_registry.yaml
- L166 | none | S | Y | - | **CLOSED 2026-07-29** — handoff 2b-swe-hygiene applies all six fields to intake-916/917/924 | Adopt six-point SWE-bench disclosure standard for intake-916/917/924 | architect-bench-runbook.md, intake_index.yaml
- L182 | none | M | N | spaCy lemmatizer dependency | Add ordered_subsequence verifier to canonical answer_scoring | answer_scoring.py, its test
- L183 | none | S | N | verifier (L182) | Implement both Ordered Rate and Coverage-with-order metrics | answer_scoring.py
- L184 | none | S | Y | - | **READY** Record ACL-2025 provenance + 4-bit-vs-API leaderboard confound | intake_index.yaml, benchmarks/instruction_precision

## searxng-search-backend.md (7) — L353-355 all edit the SAME deep-dive note
- L208 | cpu | M | N | AR-3 Package D | SX-5 load test via web_research sentinel suite | config/searxng/settings.yml, research.py
- L209 | cpu | S | N | AR-3 warmup trial quality data | SX-6 swap SearXNG to default after regression check | src/tools/web/search.py
- L220 | none | M | N | needs Camofox (intake-524) | CA-6 wire escalate_to_camofox from _is_blocked_page | src/tools/web/research.py
- L353 | none | S | N | - | Relabel intake-364/365 verdict not_applicable→superseded | research intake registry
- L354 | none | S | N | - | Correct two outdated Firecrawl self-host objections | firecrawl-vs-crawl4ai deep dive
- L355 | none | S | N | - | Strengthen decisive objection: compose grew to seven services | firecrawl-vs-crawl4ai deep dive
- L356 | none | M | N | CA-6 / Camofox | Consider ranked engine-waterfall instead of substring blocklist | src/tools/web/research.py

## security-review-skill.md (1)
- L60 | none | M | Y | intentionally deferred; no enforcement workflow | CI gate + PR-summary min-severity integration | .claude/skills/security-review/SKILL.md

## session-bus-thin-dispatcher.md (26) — the fleet's own control plane; most rows edit tmux_adapter.py
- L313 | cpu | S | Y | operator deferred 2026-07-27 | R1a real llama-bench smoke acquiring/holding/releasing a region claim | region_lock_cli.py, bench_canonical.sh
- L536 | none | M | N | M5 triage hook (flag-gated, triage:off) | R9 automate replay-eligibility classification | session_bus.py, session_bus_coordinator.py
- L602 | none | L | Y | needs a working day of elapsed soak | M3 collect would-assign vs actual-choice accuracy evidence | advisory.jsonl, coordinator.py
- L655 | none | M | N | - | M3d widen queue seeding per-handoff so advisory evidence is meaningful | seed_queue.py, queue.jsonl
- L659 | none | L | N | M3 advisory-accuracy evidence + 48h soak | M4 48h zero-idle soak, induced stall, epoch-fencing restart | config.yaml, tokens/token-queue.md
- L699 | none | S | Y | coordinator re-assignment call | C-OWN assign a new owner for the unowned C-series arc | handoff, config.yaml
- L703 | none | S | N | **STALE?** deletion recorded done 2026-07-29 | C22 delete dead roster_window_names | tmux_adapter.py
- L708 | none | M | N | BUS_PROTOCOL.md owner | C23 allow bulk corr_id disposition | BUS_PROTOCOL.md, session_bus.py
- L762 | none | L | Y | per-feature operator flag grants | M5 remaining extensions: drain hook, hybrid triage, headless workers | .claude/settings.json, tmux_adapter.py
- L825 | none | S | N | operator decision on interval value | M5a ratify or change 600s --min-interval-s default | tmux_adapter.py, config.yaml
- L827 | none | S | Y | operator disposition | M5b disposition preserved roster-orphan heartbeat/outbox artifacts | heartbeats/, outbox/
- L831 | none | M | N | - | M5c nudge running mains to re-read changed standing instructions | BUS_PROTOCOL.md, tmux_adapter.py
- L938 | none | S | Y | **needs an independent reviewer, not the author** | C11 review live_mains/resolve_spawn_cap/cmd_spawn | tmux_adapter.py
- L945 | none | M | N | - | C12 anchor post-Enter echo below pre-Enter cursor | tmux_adapter.py, test_tmux_adapter_live.py
- L952 | none | S | N | deferred pending real annoyance evidence | C13 narrow @ nudge refusal to token-start only | tmux_adapter.py
- L1099 | none | S | Y | daemon owner restart / post-reboot | C18 restart daemon so unreachable-recipient notice activates | session_bus_coordinator.py, bus_supervisor.sh
- L1146 | none | S | Y | operator decision (reboot step vs flag flip) | C20 decide documented tmux new-session reboot step | BUS_PROTOCOL.md, config.yaml
- L1163 | none | S | N | **operator must state a number** | C15 raise max_concurrent_mains from saturated 4/4 | config.yaml
- L1222 | none | S | Y | needs an independent reviewer, not the author | C24 review whether live_mains can omit a genuinely live id | tmux_adapter.py
- L1226 | none | S | N | - | C25 derive spawned window name from endpoint, not roster id | tmux_adapter.py:899, :311-335
- L1244 | none | S | N | - | C26 add pid-liveness and uptime checks to daemon status | session_bus_coordinator.py:2233-2240
- L1258 | none | M | N | M4 authority still manual | C27 find why token-requests never became token-queue blocks | coordinator.py, tokens/token-queue.md
- L1279 | none | M | N | - | C28 track relay completion in daemon-owned ledger by message identity | coordinator.py, inbox/
- L1294 | none | S | N | warn-vs-refuse choice must be recorded | C29 make drain --agent enforce roster id like append does | session_bus.py:692-729
- L1307 | none | M | N | - | C30 record launch backend in roster; verify spawned window survives | tmux_adapter.py:899-931, config.yaml
- L1325 | none | M | N | must land with C24 fix | C31 key nudge rate limit on window instance, not roster id | tmux_adapter.py:559-560, :685-687

## shape-keyed-contention-gating.md (2)
- L29 | none | S | Y | do not land while a calibration run is live | Echo GateDecision fields into /chat response metadata | contention_gate.py, concurrency_aware.py
- L30 | cpu | L | N | operator bench approval + quiet window | Implement re-bench sample_fn drive loop on codified recipe | shapekeyed_step2_smoke.py, run_paired_ab.py

## sliders-local-validation.md (9) — handoff is PARKED pending an operator go
- L16 | none | S | Y | **operator decision** | Operator decides whether to evaluate SLIDERS now or stay parked | handoff
- L55 | none | M | Y | operator go (handoff parked) | 0.1 catalogue every GPT-4.1 call site in upstream SLIDERS repo | data/sliders_validation/01_call_site_catalog.md
- L56 | none | M | N | task 0.1 | 0.2 substitute OpenAI client with local Coder-30B adapter | 02_substitution_diff.md, scratch/sliders/
- L57 | cpu | L | N | task 0.2 + EDGAR reachability | 0.3 run SLIDERS end-to-end on FinQ5 with Coder-30B | 03_finq5_results.json
- L63 | none | S | N | task 0.3 results | Write Phase 0 gate verdict: not_viable_local or go_phase_1 | 04_phase0_verdict.md
- L70 | cpu | L | N | Phase 0 GO verdict | 1.1 run SLIDERS+Coder-30B on 10-question FinanceBench subset | scratch/sliders/
- L71 | cpu | M | Y | Phase 0 GO verdict | 1.2 run ColBERT chunk-RAG baseline on same 10 questions | internal-kb-rag K7 pipeline
- L72 | none | S | N | tasks 1.1 and 1.2 | Decide if SLIDERS beats ColBERT by 5pp threshold | data/sliders_validation/
- L76 | none | M | Y | Phase 1 escalation | Write scoping doc for SLIDERS as KB-RAG K3/K4 alternative | handoff

## speculative-decoding-mtp-refresh.md (14) — L231..L245 are record-keeping rows, all edit this handoff
- L96 | cpu | L | N | artifact-blocked: no matching Q4/Q4-MTP pair + P6b gate | T4 gate-bench Qwen3.6-35B-A3B MTP for frontdoor/coder | llama.cpp-experimental, models/
- L212 | none | S | Y | - | **READY** Audit whether MTP A/B sweeps enough depths for non-monotonic optimum | md_self_draft_ab.py
- L218 | cpu | M | N | GLM-5.2 higher-bpw artifact not landed (H-Q1) | Piggyback cheap alpha(IQ2_M→IQ3_XXS) measurement on H-Q1 download | ?
- L223 | cpu | L | N | Q8_0 128GB download pending disk free | Bench DFlash accept-rate on Laguna across three target quants | models/laguna/, data/dflash_accept/
- L224 | none | M | Y | gated on the DFlash accept-rate bench above | Scope the draft-dflash spec-path port from the laguna fork | common/speculative.cpp
- L231 | none | S | N | - | Retire the obsolete "DFlash has no llama.cpp/CPU path" framing | handoffs/active/*.md
- L232 | cpu | L | N | target-weight provenance match + L-6 acceptance floor | Measure z-lab gemma-4-26B DFlash drafter vs worker_general | models/gemma-4-26B-A4B-DFlash
- L233 | none | S | Y | - | **READY** Scope acceptance-only comparison for 122B DFlash drafter | handoff
- L234 | none | S | N | - | Record settled DFlash architecture facts | handoff, research/deep-dives/
- L235 | none | S | N | - | Record provenance/qualifiers for published DFlash speedup numbers | handoff
- L236 | none | S | Y | - | **CLOSED 2026-07-29** — 851 vs 866 tensors plus `qwen35.nextn_predict_layers` key; file size is non-evidence | Tensor-count header gate for DavidAU Qwen3.6-27B MTP GGUFs | models/*.gguf headers
- L237 | none | S | N | - | Record ThinkingCap MTP head is stock; flag confounded Q4_K_M pair | handoff
- L244 | none | S | N | - | Record KAT-Coder tokenizer-match + removed-MTP artifact facts | handoff, research/intake
- L245 | none | S | N | - | Adopt safetensors-index preflight rule over config.json checks | handoff, feedback rule file

## stack-change-governance-pipeline.md (1)
- L70 | none | L | N | - | Migrate remaining consumers to generated stack priors or degraded fallbacks | stack_change_surface_manifest.yaml

## stale-open-audit-2026-07-18.md (6) — ORPHAN; this is the meta-audit of the backlog itself
- L86 | none | M | Y | - | Re-anchor GEMV to live graph-fusion tasks, appendix the SIMD plan | cpu-shape-specialized-gemv-decode.md
- L87 | none | M | N | - | Close/relocate LANDED and SUPERSEDED handoffs to completed | handoffs/completed/, x-mas-text-routing.md
- L88 | none | M | Y | - | Split live rollout backlog from frozen gated expansion | learned-routing-controller.md, decision-aware-routing.md
- L90 | none | L | N | operator gate | Hard-archive stack cluster, migrate orphan boxes, repoint links | handoffs/completed/
- L92 | none | S | Y | - | **READY** Publish corrected live-backlog figure of about 544 | dashboard backlog banner config
- L93 | none | L | Y | - | Extend audit to ~105 un-flagged handoffs for exact live count | handoff

## standardized-stack-update-pipeline-finalization.md (5)
- L201 | none | M | N | SS-BENCH-GATE-b (durable fix) | Stack reload must gate on running CPU bench | scripts/orchestrator_stack.py
- L217 | none | M | N | - | Pin fleet and sidecars off CPU bench cores | orchestrator_stack.py, NUMA/core-pin config
- L232 | none | L | N | opportunistic — only on new GitNexus impact finding | Continue high-risk consumer migrations to generated truth | stack-change surface manifest
- L243 | none | L | N | opportunistic expansion as consumers migrate | Finish W4 swap-CI coverage for representative stack changes | test_stack_change_pipeline_simulated_fixtures.py
- L261 | none | S | N | - | Keep bench, launch, preflight wired to canonical gate | stack_change_pipeline.py, orchestrator_stack.py

## strand-rust-coder-rustevo2-verification.md (3)
- L258 | cpu | L | N | **USER APPROVAL REQUIRED per-run** | Sequential single-instance RustEvo2 bench of three models | rustevo2_bench_preflight.py
- L259 | none | M | N | Phase B results | Build score table + decision matrix, isolate fine-tune delta | RustEvo2 score artifacts
- L260 | none | S | Y | Phase C disposition | Push GO/NO-GO into intake-616, flip distillation status | swarm-dataset-distillation.md

## streaming-llm-baseline.md (4)
- L114 | cpu | L | N | operator inference window; v7/v8 promotion | Run 4-axis sweep: 3 workloads x 3 budgets x 2 models | epyc-llama fork, scripts/benchmark/
- L115 | none | M | Y | needs 4-axis sweep data | Evaluate loss thresholds per workload, track per-head entropy | scripts/analysis/
- L116 | none | S | Y | needs measured floor from sweep | Demote or promote KV-cluster handoffs against the measured floor | attention-matching-kv-compaction.md
- L117 | none | S | Y | operator input on open questions | Resolve K_sink/K_win values, F16 KV scope, PBKV ordering | handoff

## summary-token-attention-readiness.md (4) — all four are external-trigger watches
- L77 | none | S | N | external checkpoint release (none exists) | Gate A: KSA/GSA-style checkpoint for a served model family | handoff, intake_index.yaml
- L78 | none | S | N | upstream llama.cpp PR pending | Gate B: llama.cpp top-k chunk masking or summary KV support | handoff
- L79 | none | S | N | GPU/CPT budget acquisition | Gate C: GPU acquisition enabling our own continued pretraining | handoff
- L80 | none | S | N | major-lab model adoption (external) | Gate D: major lab adopts summary-token attention by default | handoff

## tidar-one-pass-variant-b.md (3)
- L23 | cpu | L | N | no Q4_K_M-quantizable TiDAR-class checkpoint exists | W2 checkpoint gate + Q4 quality delta go/no-go verdict | quantized TiDAR GGUF
- L24 | none | L | N | W2 go verdict | W3 unified causal+bidirectional one-pass draft+verify ggml op | llama.cpp-experimental ggml mask op
- L25 | cpu | M | N | W3 implementation | W4 canonical decode bench vs AR baseline + memo | bench artifacts, decision memo

## tool-output-compression.md (6)
- L417 | none | S | Y | awaiting_minimum_observations (100 calls) | Per-command rollout decision once P4c telemetry reaches minimum | tool_compression_topups.py
- L442 | none | S | Y | - | **READY** Bias Phase-3d fallback chain toward observation-dropping | compress_tool_output.py
- L448 | cpu | L | N | prerequisite artifact (L449) | First-party A/B: verbatim-append log vs summarize-and-compact | scripts/benchmark/, context_compression.py
- L449 | none | L | N | - | Produce grep-able trajectory artifact; audit live peek/grep impls | session_log.py, file_exploration.py
- L450 | none | M | Y | - | Instrument total (not peak) tokens per episode in A/B | session_log.py, scripts/analysis/
- L451 | none | M | Y | - | Map query_memory read API onto existing spill-pointer machinery | graph/helpers.py, episodic_store.py

## tool-use-eval-contract.md (1)
- L366 | none | S | Y | - | **CLOSED 2026-07-29** — epyc-orchestrator `e6b989b9`; handoff records `tests/test_tool_sentinels.py` 8/8 | Adopt negative-constraint + stated-consequence sentinel pattern | sentinel prompt definitions

## tq3-quantization-evaluation.md (13)
- L61 | cpu | M | N | upstream PR #21089 unmerged | Test TBQ3_0 KV cache on Qwen2.5-Coder-32B context extension | llama.cpp build, llama-bench
- L62 | none | M | Y | - | **READY** Read ChunkKV paper, assess llama.cpp implementability | handoff, research notes
- L63 | none | S | Y | upstream adoption + multi-model benchmarks | Revisit TQ3_1S weight quant only under four named conditions | handoff
- L89 | none | S | Y | upstream PR #22836 unmerged | Monitor llama.cpp PR #22836 STQ1_0 kernel for merge | model-probe-scoreboard.md
- L90 | cpu | M | N | PR #22836 merge + Hy-MT1.5 download | Canonical llama-bench Hy-MT1.5-1.8B 1.25bit vs Q4_K_M | model-probe-scoreboard.md
- L91 | none | S | Y | no QAT pipeline / sub-4-bit not in scope | Defer Tequila and DAQ until QAT or sub-4-bit deployment | handoff
- L127 | none | S | Y | operator decision | Operator decides lossless exponent-coding spike vs close thread | handoff
- L153 | none | S | Y | operator review + named prompt/producer fix | Parked Bonsai Q1_0/Q2_g64/Q2_0 reopen only on named fix | model-probe-scoreboard.md
- L164 | cpu | L | N | operator gate; owner moved to iqk-iquant-enablement | Bounded llama-bench of un-stubbed trellis IQ4_KT/IQ3_KT | CMakeLists.txt, iqk_stubs.cpp
- L165 | none | S | Y | - | Coordinate sub-2-bit angle with AngelSlim handoff | angelslim-techniques-evaluation.md
- L184 | none | M | N | ownership moved to iqk-iquant-enablement B1-B5 | Un-stub iqk iquant kernels for IQ2_XXS/IQ3_XXS/IQ2_S | iqk_stubs.cpp, iqk_dispatch.cpp
- L185 | cpu | L | N | operator inference approval; owner iqk T1-T3 | Measure IQ4_KT vs Q4_K_M and IQ2_KT vs IQ2_XXS in ik tree | ik_llama.cpp bench harness
- L186 | none | L | N | gated on STEP 2 win | Port trellis KT quant types into v7 tree if Step 2 wins | ggml-common.h, iqk_gemm_ktquants.cpp

## tri-role-coordinator-architecture.md (9) — TR-4/TR-5 FROZEN behind the DAR-regret gate
- L98 | none | M | N | **TR-4/5 frozen (DAR-regret gate)** | Compose assigned role with model selection in routing | chat_pipeline/routing.py
- L99 | none | M | N | TR-4/5 frozen | Give each role its own prompt template in consumers | seeding_types.py, chat_utils.py
- L100 | none | M | N | TR-4/5 frozen | Let multi-turn sessions read and adapt prior turn role | routing.py, chat_utils.py
- L101 | none | M | N | TR-4/5 frozen | Short-circuit dispatch when Verifier returns ACCEPT | chat_pipeline/routing.py
- L105 | none | M | Y | TR-4 wiring incomplete; TR-5 frozen | Define role-sensitive benchmark suite for the A/B | eval_tower.py, dataset_adapters.py
- L106 | cpu | L | N | TR-4 complete; TR-5 frozen | Run paired N=200/arm A/B with ROLE_AWARE_ROUTING on/off | role_taxonomy.py, eval_tower.py
- L107 | none | S | Y | needs TR-5.2 results | Apply +2pp promotion gate or document negative result | handoff, reports/
- L176 | none | M | Y | - | **READY** Cross-reference EvoScientist memory modules for StrategyStore | research/deep-dives/, repl_memory/
- L177 | none | M | Y | - | Evaluate EvoScientist distillation separation for Evolution Manager | research/deep-dives/, handoff

## triattention-kv-selection.md (4)
- L24 | cpu | L | N | bulk-inference campaign window | S8 sweep keep_ratio/layer_weights per role, persist Pareto profiles | epyc-orchestrator/src/, kv_compress.py
- L25 | none | M | N | S8 stable role profiles | S9 wire learned KV profiles into orchestrator auto-trigger | epyc-orchestrator/src/, program.md
- L26 | cpu | L | Y | optional comparator | S2 TriAttention concentration validation | llama-kv-compress.cpp
- L27 | cpu | L | Y | S8 + production compression need | S3 stack KV selection with quantization, or alternatives | llama-kv-compress.h/.cpp

## unified-trace-memory-service.md (13)
- L110 | none | M | Y | Hermes production-use gate | T7 optional Hermes session ingest into normalized trace events | src/trace/ingest_hermes.py
- L187 | cpu | L | Y | operator-review candidate; BGE embedders :8090-8095 | Add RRF(k=60) hybrid fusing FTS5 lexical with vector index | src/trace/navigation.py, store.py
- L200 | none | L | Y | operator-review candidate | Importance-scored background consolidation pass | repl_memory/memory_actions.py
- L208 | none | M | Y | AP-29 gate in autopilot-continuous-optimization | UTM-M1 adopt append-only store shape retaining raw trajectories | src/trace/store.py
- L209 | none | M | N | - | UTM-M2 scope additive dual-layer experience bank | src/trace/store.py, harness_schema.py
- L210 | none | M | Y | - | UTM-M3 add auditable delete verb + When-NOT-to-Use to skill records | repl_memory/memory_actions.py
- L211 | none | S | Y | - | **CLOSED 2026-07-29** — source audit records success/failure, judge, MaTTS prompts and `induce_memory.py` JSONL shape | UTM-M4 mine ReasoningBank repo for 3 prompts and JSON schema | src/trace/harness_schema.py
- L215 | cpu | L | Y | explicitly unblocked | UTM-M5 build per-window success-rate-vs-store-size curve instrument | scripts/analysis/, data/trace/events.sqlite
- L219 | none | S | Y | - | **CLOSED 2026-07-29** — records fixed-update-schedule context-budget competition as distinct from accumulated-store late decay | UTM-M6 file EvoMemBench 128K context-competition failure mode | handoff, intake_index.yaml
- L220 | none | M | N | - | UTM-M7 make retrieval injection budget-conditional | navigation.py, src/retrieval/
- L221 | none | M | N | - | UTM-M8 cap injection as fraction of remaining budget | navigation.py, src/retrieval/
- L222 | cpu | M | Y | operator gate (MEASUREMENT human amendment) | UTM-M9 add no-memory control arm to every memory A/B | MEASUREMENT.md, eval-tower row config
- L226 | none | S | Y | - | UTM-M10 correct ReasoningBank standing everywhere | handoff, intake_index.yaml

## within-role-placement-state-machine.md (9)
- L377 | cpu | L | N | operator approval + inference measurement window | WP-6/WP-7 ratify matrix re-bench + per-role dispatcher rollout | concurrency_aware.py, contention_matrix.yaml
- L380 | cpu | M | N | quiet host + operator bench approval | Higher-sample vision_escalation re-bench to ratify clean allow | data/contention_matrix/
- L381 | none | M | Y | - | **READY** Wire missing kv_migration_direction_total + thrash_skipped counters | concurrency_aware.py, api metrics route
- L403 | cpu | L | N | lineup+recert event, 0.5-1.5h quiet host | WP-9 move frontdoor/ingest half instances onto distinct NUMA halves | stack_numa.py, contention_matrix.yaml
- L404 | cpu | M | N | operator lever on matrix-measured status + recert | WP-10 add worker_math NUMA_CONFIG entry and recertify | stack_numa.py
- L408 | none | M | N | ESC-8 disarm agent owns writer fix | WP-14 fix runtime-facts writer recording phantom full lineup | runtime_facts_manifest.py
- L410 | none | S | Y | or confirm WP-12 deletes the reader on land | WP-14 harden stack_templates default-full env reader | src/config/stack_templates.py
- L412 | none | M | Y | - | **READY** WP-11 add PID-liveness stale-holder sweep at lock acquisition | src/runtime/cpu_region_lock.py
- L413 | none | L | N | GATED on WP-6/WP-7 dispatcher ratification | WP-8 largest-disjoint-subset max-safe-concurrency for eval fanout | instance_topology.py

## wp12-fleet-layer-design.md (1)
- L240 | none | L | N | soak completion + operator retires flag-off rollback | Retire legacy per-role build path and its guard tests | ServerURLsConfig, test_full_slot_demotion.py

## x-mas-text-routing.md (1)
- L49 | none | S | Y | - | **READY** Monitor post-enable telemetry for regressions and guard bypasses | xmas_winner_table.yaml, fable5_gate_report.py

## yarn-context-extension-research.md (1)
- L105 | none | S | Y | no concrete >32K workload requirement | Reactivate YaRN research when a >32K workload appears | handoff

---

# BLOCKED — DO NOT DISPATCH

Grouped by the thing that must move first. Anything here will bounce if you assign it.

## B1. Operator signature / trust-boundary write (human-amendment-only)
Nothing an agent does can clear these. They need the operator personally.

| Gate | What it unblocks | Rows waiting |
|---|---|---|
| **E8 quality-baseline ratification** (`gpu-serving-tie-in-program.md:48`, needs Codex's merged wrapper tree first) | The entire post-v8 campaign: AutoPilot resume, all model-stack/lineup/registry change | `autopilot-decision-plane-…:223,285,300,307,314,324` · `gpu-serving-…:64,66,90` · `autopilot-continuous-optimization.md:4` · `autopilot-sequential-allocation.md:127` · `multimodal-pipeline.md:178` · `eval-tower-loop-robustness-…:140` |
| **P0.1–P0.3 / rate-axis era-fence amendment** (`orchestration-robustness-…:156,159,184`) | Promotion is unreachable *by construction* until signed | `evidence-plane-ledger-…:337` · `routing-and-optimization-index.md:651` · `research-evaluation-index.md:151,152` · `fable5-…-03:71` |
| **P-REV-1 MEASUREMENT blocks** (`reviewer-calibration-accounting.md:27,105,106` · `reviewer-control-plane-index.md:87,88`) | Any decision-grade reviewer-calibration claim | `glm52-reviewer-capability-gates.md:121,127,233` · `inference-batch-loop.md:204` · `reviewer-escalation-…:27` |
| **P-GPU-1 ratification** (`master-handoff-index.md:444` · `fable5-…-03:65`) — *note: several handoffs believe this already happened 2026-07-19; reconcile before dispatching* | GPU claims as decision-grade | `master-handoff-index.md:446` · `reviewer-control-plane-index.md:30` · `agentic-rocm-…:73` · `gpu-drafter-control-redesign.md:97,135` · `mi210-big-model-…:127,156` |
| **OP-5(b) H-LB budget threshold** | Any enforce-mode in the reviewer plane | `reviewer-latency-…:25,27` · `reviewer-escalation-…:27` |
| **OP-6(a)+(b) quiet-window approval** | The whole reviewer-plane baseline window | `bulk-inference-campaign.md:624,625,626` · `inference-batch-loop.md:195,196` · `reviewer-calibration-accounting.md:29` |
| **Era-registry row appends** (`instrument_eras.yaml`) | core_v2 promotion, throttle-gate rescope, sampling determinism | `core-v2-design-note-…:157,161` · `batched-decode-measurement.md:520` · `prompt-construction-determinism.md:68` · `evidence-plane-instrument-repair.md:93` |
| **Misc operator decisions** | — | `glm52-…:159` (GC-4 residency) · `harness-selection-…:41` (HS-4) · `sliders-local-validation.md:16` · `tq3-…:127` · `autopilot-authority-…:99` · `session-bus-…:1163` (C15 number) · `objective-task-rate-goodput.md:46` · `decision-aware-routing.md:489` · `autopilot-sequential-allocation.md:78,99` · `agent-file-prose-compression.md:233` · `dynamic-stack-concurrency.md:42` (root edit) · `orchestration-robustness-…:155` |

## B2. Inference availability / quiet window (CPU)
Serialized behind the CPU lane. ~280 rows. The heaviest clusters:
- **E5 NUMA×batch sweep** (`batched-decode-measurement.md:26,521,522` · `gpu-serving-…:65`) gates
  `heterogeneous-slot-fabric-residency.md:141` and, through it, most of the slot-fabric arc (L142–L148).
- **Hermes live validation** — all 11 rows of `hermes-outer-shell.md` plus `hermes-agent-index.md:99,101,107,108,109,111,112,114`.
- **Eval-tower inference tails** — `eval-tower-verification.md:180,185,193,217,251,257,413,414,427,429,431,489,497,545,546`.
- **Reviewer-plane windows** — `reviewer-model-ablations.md` (all 8), `reviewer-latency-…:20,23,28`, `reviewer-decision-plane.md:32`.

## B3. GPU lane (MI210)
~160 rows, all behind the GPU lane's own sequence (P2-2c → Steps 0-7 → P3 bake-off).
Whole handoffs that are 100% GPU-gated: `mi210-q8-dequant-gemv-roofline` · `gpu-drafter-mi200-investigation` ·
`gpu-drafter-control-redesign` · `memento-block-reasoning-compression` (S2 training) ·
`fable5-window2-findings-05c` (the 13 lever rows).
**Single highest-leverage GPU unblock: the gfx90a training-viability smoke** (`minddr-…:13`) — one probe
that unblocks `frontier-f3-data-flywheel.md:33`, `engram-conditional-memory.md:385-387`,
`minddr-…:185`, and the EV-9 judge model.

## B4. Build / artifact / download gates
- **stack-freeze lift** → `inference-batch-loop.md:208,210,211` · `research-evaluation-index.md:81`
- **upstream llama.cpp PRs** — #22836 (STQ1_0): `tq3-…:89,90` · `angelslim-…:73,81,94` · `internal-kb-rag.md:310`; #21089 (TBQ3_0): `tq3-…:61`
- **downloads pending** — GLM-5.2 UD-IQ2_M (`llama-cpp-dsa-contribution.md:247`) · Laguna Q8 128GB (`speculative-…:223`) · MathSmith-HC (`mathsmith-…:109`) · Hy-MT2-1.8B (`internal-kb-rag.md:311`) · opendataloader-bench LFS (`opendataloader-…:405`) · Augment-v1 golden set (`eval-tower-verification.md:431`) · HRM-Text-1B (`multiscreen-…:320`) · Qwopus3.6-27B-Coder (`architect-…:503`)
- **host/root actions** — cgroup `pids` subtree (`scoring-infra-…:82`) · bwrap install (`scoring-infra-…:87`) · `perf` not installed (`cpu-shape-…:519`) · rocprof on MI210 (`agentic-rocm-…:76`) · earlyoom root edit (`dynamic-stack-concurrency.md:42`) · `authority_consent.json` is root:root 0444 (`orchestration-robustness-…:184`)

## B5. Frozen / parked by design — do not "unblock" these, they are deliberate
`tri-role-coordinator-architecture` TR-4/TR-5 (DAR-regret gate) · `decision-aware-routing` DAR-3/4/5/6 ·
`cpu-shape-specialized-gemv-decode` Phases 0-4 (E3 SIMD NO-GO) · `qwen36-27b-cpu-feasibility` (PARKED) ·
`sliders-local-validation` (PARKED) · `intra-process-tensor-parallel-decode` (dormant, no reopen trigger) ·
`yarn-context-extension-research` · `numa-prefill-decode-disaggregation` · `summary-token-attention-readiness`
(4 external-trigger watches) · `log-linear-gated-deltanet-readiness` (3 upstream watches) ·
`mi210-mfma-compute-bound-paths` (measurement gate failed both paths).

## B6. Blocked on another *agent's* uncommitted work
- `intake-derived-work-…:95,125,163` — the parallel v8-cutover session holds `laguna-s21-cpu-port.md` and `ENGINEERING_STANDARDS.md` edits.
- `gpu-serving-…:144` — unmerged crash-window branch owns `stack_numa.py`.
- `within-role-placement-…:408` / `autopilot-dashboard-…:267` — ESC-8 disarm agent owns `runtime_facts_manifest.py`.
- `session-bus-…:938,1222` — C11/C24 explicitly require a reviewer who is **not** the author.
- `scaffold-autopilot-…:104` — a live autopilot agent still holds the daemon.

---

# COLLISION MAP

Two mains must never hold two rows from the same block at once.

## C1. Hot shared files — one main at a time
| File | Rows that write it |
|---|---|
| `research/intake_index.yaml` | `intake-derived-work-…:92,194,196,199,218` · `searxng-…:353` · `context-folding-…:114,142,143` · `gpu-acceleration-path.md:524,531` · `internal-kb-rag.md:530` · `speculative-…:244` · `routing-intelligence.md:128` · `reasoning-compression.md:631` · `unified-trace-…:219,226` · `scoring-infra-…:184` |
| `scripts/autopilot/eval_tower.py` | **single-writer, owned by the inference-batch `/loop`** — `eval-tower-verification` (most rows) · `research-evaluation-index:153,156` · `scorer-fork-drift-…:256` · `reviewer-latency-…:20,23,28` · `fable5-…-03:71` · `objective-task-rate-…:75` · `scaffold-…:116,129` · `tri-role-…:105,106` |
| `scripts/coordination/tmux_adapter.py` | `session-bus-…:703,762,825,831,938,945,952,1222,1226,1307,1325` — the whole C-series. Serialize. |
| `orchestration/model_registry.yaml` | `reasoning-effort-levels:113,321,345` · `architect-…:334` · `multimodal-…:326` · `scoring-infra-…:107` · `lightning-attention-port.md:32` · `qwen36-…:118` · `mathsmith-…:114,115,117,123` · `reviewer-model-ablations.md:51` · `heterogeneous-…:142` |
| `orchestration/instrument_eras.yaml` | `decision-aware-routing.md:613` · `core-v2-…:161` · `autopilot-dashboard-…:286` · `prompt-construction-determinism.md:68` · `fable5-…-03:69` · `scoring-infra-…:144` · `evidence-plane-instrument-repair.md:93` |
| `/workspace/MEASUREMENT.md` | **human-amendment-only** — `reviewer-calibration-…:27,105,106` · `reviewer-control-plane-index.md:87,88` · `master-handoff-index.md:444` · `fable5-…-03:65` · `eval-tower-verification.md:487,488` · `scaffold-…:128` · `unified-trace-…:222` |
| `orchestration/repl_memory/episodic_store.py` | `learned-routing-…:92,197,320` · `episodic-memory-integrity.md:316` · `rao-redel-…:415,432` · `decision-aware-routing.md:124,125` · `scaffold-…:120,121` · `autopilot-decision-plane-…:399` · `tool-output-compression.md:451` |
| `src/dashboard/dashboard.py` | `autopilot-dashboard-…:283,289,324,325,326` — 5 rows, one file. |
| `scripts/server/orchestrator_stack.py` | `standardized-stack-…:201,217` · `heterogeneous-…:144` · `core-v2-…:192` · `memento-…:193,194` · `learned-routing-…:319` · `reasoning-effort-levels:242` · `scaffold-…:109` · `eval-tower-verification.md:194` |
| `research/deep-dives/firecrawl-vs-crawl4ai-…md` | `searxng-…:354,355` — 2 rows, same note. |
| `src/tools/web/research.py` | `colbert-…:263,283` · `searxng-…:208,220,356` |
| `ggml/src/ggml-cpu/zen5-ukernel.cpp` | `cpu-shape-…:531,543,544,558,559,560,561,575` |
| `ggml/src/ggml-cuda/mmvq.cu` | `fable5-…-05c:210,213,218` · `mi210-q8-…:78` |
| `CLAUDE.md` / `agents/shared/*` | `intake-derived-work-…:53,95,98` · `agent-file-prose-compression.md:241,243` · `harness-selection-…:144` |
| `handoffs/active/fable5-…-05c…md` | its own 9 taxonomy rows L223-L231 — **all one file**, dispatch as ONE task |
| `handoffs/active/speculative-decoding-mtp-refresh.md` | its own L231,233,234,235,236,237,244,245 record rows + `intake-derived-work-…:109,147,155,169` |

## C2. Cross-handoff DUPLICATES — the same unit of work filed twice. Dispatch ONE.
- `inference-acceleration-index.md:412` ≡ `qwen-mtp-llamacpp-port.md:85` (P6b gate-bench)
- `inference-acceleration-index.md:380,381` ≡ `llama-cpp-dsa-contribution.md:245` (D2 sparse attention)
- `research-evaluation-index.md:81` ≡ `backlog-roi-audit-…:16` (execution-free patch verifier)
- `research-evaluation-index.md:82` ≡ `backlog-roi-audit-…:17` ≡ `eval-tower-verification.md:429` (review-F1 suite)
- `research-evaluation-index.md:84` ≡ `backlog-roi-audit-…:19` (Simula → F1-DGM)
- `intake-derived-work-…:63` ≡ `scoring-infra-…:182` (ordered_subsequence verifier)
- `intake-derived-work-…:66` ≡ `eval-tower-verification.md:546` (FrontierCS floor probe)
- `intake-derived-work-…:132` ≡ `frontier-f1-real-task-corpus.md:115` (SQLite trajectory reader)
- `intake-derived-work-…:33` ≡ `autopilot-continuous-optimization.md:1525` (AP-21 gepa_ratio)
- `intake-derived-work-…:39` ≡ `autopilot-continuous-optimization.md:1526` (AP-29 control arm)
- `intake-derived-work-…:45` ≡ `autopilot-continuous-optimization.md:1529` (AP-32 +1.1% claim)
- `intake-derived-work-…:50` ≡ `autopilot-continuous-optimization.md:1530` (MemRL retriever retarget)
- `intake-derived-work-…:109` ≡ `speculative-decoding-mtp-refresh.md:236` (DavidAU header gate)
- `intake-derived-work-…:150` ≡ `speculative-decoding-mtp-refresh.md:232` (gemma-4 DFlash bench)
- `intake-derived-work-…:155` ≡ `speculative-decoding-mtp-refresh.md:233` (122B DFlash watch)
- `intake-derived-work-…:147` ≡ `speculative-decoding-mtp-refresh.md:231` (retire DFlash blocker)
- `intake-derived-work-…:196` ≡ `gpu-acceleration-path.md:524` (intake-578 correction)
- `intake-derived-work-…:218` ≡ `searxng-…:353` (Firecrawl relabel)
- `reviewer-control-plane-index.md:87,88` ≡ `reviewer-calibration-accounting.md:105,106` (P-REV-1 kappa/estimand)
- `eval-tower-loop-robustness-…:140` ≡ the H2.v8 contention remeasure also cited in `master-handoff-index`
- `routing-and-optimization-index.md:25` — **STALE**: `learned-routing-controller.md:1608` already marks it `[x]`
- `document-parser-table-bench.md:63,64` ≡ `opendataloader-…:613` (full-set ODL re-baseline) — spun out, both still open
- `cpu-inference-optimization-index.md:120,121,122` ≡ `iqk-iquant-enablement.md:105,106,140` (index pointer vs owner)
- `hermes-agent-index.md:99,101` ≡ `hermes-outer-shell.md:311,322` (reference client validation)
- `hermes-agent-index.md:107` ≡ `repl-turn-efficiency.md:18` (S4 Omega A/B)

## C3. Safe concurrent groups (verified disjoint file sets)
These four bundles can run on four mains simultaneously:
- **G-A doc/provenance**: `intake-derived-work-…:45,53,87` + `gpu-acceleration-path.md:531` + `minddr-…:207`
- **G-B orchestrator code**: `orchestration-robustness-…:240` + `within-role-placement-…:412` + `autopilot-decision-plane-…:399`
- **G-C trace/memory**: `unified-trace-…:211` + `engram-…:379` + `reviewer-calibration-accounting.md:30`
- **G-D kernel/bench desk work**: `cpu-shape-…:723,727` + `llamacpp-v6-consolidation.md:77` + `laguna-s21-cpu-port.md:97`

*(Do not mix G-A with the `research/intake_index.yaml` rows in C1 — G-A's three rows were chosen because they touch different files.)*
