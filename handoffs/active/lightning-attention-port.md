# Lightning Attention Port to llama.cpp

**Status**: COMPACTED 2026-05-28 - v1 Ring-mini port complete; active only for production-suitability decisions.
**Created**: 2026-04-29
**Updated**: 2026-05-28
**Priority**: MEDIUM
**Categories**: ssm_hybrid, context_extension, kv_cache, training_distillation, inference_serving
**Workstream**: Inference Acceleration + CPU Engineering
**Parent index**: [inference-acceleration-index.md](inference-acceleration-index.md)
**Completed ledger**: [lightning-attention-port-v1-completed-through-2026-05-28.md](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md)

## Executor Start Here

Do not restart the Lightning Attention port. The historical ledger preserves the full implementation, benchmark, and quality notes. Current work is to decide whether Ring-mini-linear-2.0 has a live production role and to run only the validation slice needed for that decision.

| Current question | Executor rule |
|---|---|
| Is L1-L4 still open? | No. Treat the v1 llama.cpp port as complete unless the branch no longer builds or the model no longer loads. |
| Should L5 get implemented? | No by default. Dedicated `GGML_OP_LIGHTNING_ATTN` work is profile-gated and only justified if traces show constant-`g` materialization or head-thread underutilization as a material bottleneck. |
| Can Ring-mini draft Qwen3-Coder? | No. The F1 drafter check found tokenizer mismatch and impossible throughput math for that target. |
| What is the likely useful role? | Q-scorer/routing classifier, AIME-style direct-answer math specialist, same-family Ring-flash drafter if Ring-flash appears, or parked architecture reference. |

## Outstanding Tasks

- [ ] **LQ-1 role decision**: decide whether Ring-mini remains active as `q_scorer`, routing classifier, math specialist, same-family drafter candidate, or parked reference. Record the role and owner in this file.
- [ ] **LQ-2 broader quality eval**: if keeping a math/reasoning role, run a focused AIME/MATH/GPQA-style bundle with `reasoning_budget=0`, exact prompt templates, and explicit safety exclusions.
- [ ] **LQ-3 Ring-flash drafter check**: only if a compatible Ring-flash target is available. Measure acceptance-adjusted throughput; raw Ring-mini t/s is not enough.
- [ ] **LQ-4 profile-gated L5 decision**: only profile after LQ-1/2/3 gives a reason to keep the model. Promote a dedicated op only when the profile proves a material bottleneck.

## Dependency Forks

| Outcome | Next action |
|---|---|
| Quality pass + useful live role | Keep active, schedule the narrow follow-up validation for that role, and update the relevant domain index. |
| Quality pass but no production role | Park as architecture reference; keep the completed ledger as the durable implementation record. |
| Quality fail or safety/agentic regression remains material | Close as negative/limited-use after preserving the result; do not spend L5 effort. |
| Branch or model load regresses | Reopen only the minimum build/load fix, then rerun the smallest sanity benchmark before any quality claim. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| L1-L4 v1 llama.cpp port | Complete. Ring-mini Q4_K_M reached coherent decode at 40.68 t/s on commit `33b60b925`. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| F1 drafter compatibility | NO-GO for Qwen3-Coder target due to tokenizer mismatch and throughput math. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| F2 long-context smoke | PASS at 32K with stable prefill/decode; representative results include pp512 858.4, tg128 44.3, pp1024+tg128 283.6, pp8192+tg128 661.7, pp32768+tg128 560.2. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| F3 AIME sentinel | AIME 2025 #1 returned correct answer `70`. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| L4+ quality eval | `reasoning_budget=0` fix produced 67/90 total, 23/30 pass, 0 empties; agentic and safety regressions remain. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/llama.cpp` or the relevant experimental fork containing `LLM_ARCH_BAILINGMOE_LINEAR`
- `/mnt/raid0/llm/epyc-inference-research/` for model/eval artifacts
- [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md)
- [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md)
- [qwen36-27b-cpu-feasibility.md](qwen36-27b-cpu-feasibility.md)
- [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md)
- `research/deep-dives/ling-linear-lightning-attention-hybrid.md`

## Reporting Instructions

After any LQ task, update this active handoff with the command, model artifact, exact prompt/eval set, result, and the role decision. If a task resolves the remaining production decision, update [inference-acceleration-index.md](inference-acceleration-index.md) and [master-handoff-index.md](master-handoff-index.md).
