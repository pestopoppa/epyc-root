# 2026-06-20 — Research-intake refinement + handoff merge (intake-695..720)

**Scope:** deep-dive-verify all 25 research-intake recommendations from the 2026-06-19 batch (intake-695..720 excl. 704), then merge the verified insights into the handoff system. Self-contained entry; sibling workstreams logged in `2026-06-20.md` and `2026-06-20-autopilot.md`.

## Problem

The 2026-06-19 `/research-intake` batch wrote provisional `recommended_actions` for 25 entries WITHOUT verifying current repo/handoff state, and Phase-4 handoff writes were deliberately skipped (every entry carried `handoffs_updated: []`). The operator asked to deep-dive each recommendation, refine it against actual code/handoffs, fix the intake index, and merge the insights into handoffs/indices.

## Root cause of the stale recommendations

Provisional recs were written from intake content alone. A 9-agent deep-dive (plus 3 explore agents) against actual code/handoffs found **not one recommendation survived as-is** — shipped work the recs didn't know about, mis-cited/closed handoff anchors, and several factual errors inside the intake entries themselves.

## Changes made

| Part | Artifact | Change |
|------|----------|--------|
| A | `research/intake_index.yaml` | Rewrote all 25 `recommended_actions` to verified text; fixed factual errors (see below); backfilled `handoffs_updated`/`handoffs_created` (Part D). |
| B1 | `research/deep-dives/2026-06-20-avb-offline-reward-stack.md` (NEW) | Consolidated digest for the AVB reward cluster (706/716/717/719); offline-only; companion to learned-routing-controller. |
| B1 | `handoffs/active/learned-routing-controller.md` | RIU section anchored on NEXT-A2/A3 (NEXT-A is closed/no-op), bidirectional link to digest. |
| B2 | 9 active handoffs | `## Research Intake Update — 2026-06-20` sections: eval-tower (713), autopilot (720+715), internal-kb-rag (698), hermes-outer-shell (696/697/700), dynamic-stack (701), opendataloader (718), gpu-acceleration (709), strand-rust (702), + glm51-reap & llama-cpp-dsa (699). |
| B2 | `research/deep-dives/optillm-test-time-techniques.md` | P21.B inputs section (Fusion 712/714); n-free judge-schema/invocation/recursion only; panel = n-degraded. |
| B3 | `handoffs/active/tool-use-eval-contract.md` | Stale-text correction (705): batched child-LLM structured-return shipped @`18b5ceb`; only single-query path remains; delegate exists (`chat_delegation.py`). |
| B3 | `handoffs/active/attention-matching-kv-compaction.md` | One-line cross-ref to Still (708); flagged deployed default = Expected-Attention (not AM), and stale "v3" vs prod v5. |
| B4 | `handoffs/active/summary-token-attention-readiness.md` | Still (708) watch-item row (GPU-CPT-gated, no public code as of 2026-06-05). |
| B4 | `handoffs/active/glm51-reap-cpu-evaluation.md`, `llama-cpp-dsa-contribution.md` | GLM-5.2 elevated to PRIMARY GLM target (699); DSA forward-pass (PR #21149) is the gate; UD-IQ2 (~238 GB) is the storage path. |
| B4 (operator-gated) | `handoffs/completed/large-moe-...-2026-05-28.md`, `08-doc-to-lora-prototype.md` | Dated addenda (append-only per MEASUREMENT.md): Kimi-K2.7-Code specifics (703); Code2LoRA reopen datapoint + hot-swap-vs-wiring correction (707). |
| B4 (governance) | `wiki/SCHEMA.md`, `.claude/skills/research-intake/references/intake-schema.md` | OKF `## Conformance`: adopted `schema_version` + permissive-consumption; rejected 5/6 already-covered conventions (710/711). |
| C | 6 domain sub-indices + `master-handoff-index.md` | Registered new tasks with gate tags; promoted READY offline reward-oracle row above gated classifier-rollout (operator-directed); master got 1 ACTIVE row + GLM-5.2 GATED. No existing headline rows reordered otherwise. |
| E | memory `project_unsloth_iq2_large_moe_storage.md` + `MEMORY.md` | Saved the unsloth UD-IQ2 / GLM-5.2-primary preference. |

### Factual errors corrected in the intake entries
- **703 Kimi-K2.7**: "~480 GB headroom" was RAM, not disk — raid0 has only ~633 GB free, so Q4_K_M (620 GB) is a storage near-blocker; MoonViT vision encoder is unsupported in the fork (text path only).
- **709 UniRL**: "no image/video generation role" was wrong — `sd_server`/ERNIE-Image-Turbo IS deployed; real blocker is no *training* GPU.
- **701 drove**: ONNX-ASR/`/v1/audio/transcriptions` facade already shipped (`whisper_server.py` + `start_whisper`).
- **705 OpenRouter subagent**: structured-return lift already shipped (`18b5ceb`, `combined_ops.py`); a delegate primitive already exists.
- **707 Code2LoRA**: llama.cpp LoRA hot-swap is DONE (Finding 1); the gap is orchestrator LoRA wiring (Finding 7).
- **706/716**: dropped the incorrect "meanmax = open P4/P6 pooling question" cross-ref (different model; P4.1.3 is an IRT audit).
- **699 GLM-5.2**: elevated to PRIMARY GLM target (supersedes 5.1) per operator; DSA forward-pass unimplemented (dense-MLA fallback), PR #21149 is the gate.

## Results

- `validate_intake.py`: **720 entries OK** (green after Part A, after the SCHEMA.md edit, and after Part D backfill).
- 11 active-handoff RIU sections present; digest created with verified bidirectional link.
- `handoffs_updated`/`handoffs_created` backfilled for all entries except 695 (downgraded to passive watch-item — no handoff edit) and 704 (excluded).
- Guardrails honored: did NOT touch `decision-aware-routing.md` (FROZEN), `meta-harness-optimization.md` (compacted), or any `docs/chapters/*` (recommendation-only); no P21.B body added to `routing-and-optimization-index.md` (stays in `program.md` + optillm digest).
- Committed as `e87cd8b` (28 files; parallel-agent noise — `llama.log`, `logs/`, `.devc/`, autopilot progress — deliberately excluded).

## Deferred / next work

- **READY now**: offline reward-oracle eval (AVB stack → LRC NEXT-A2/A3). NOTE: a parallel agent has already begun implementing the A9 evaluator (`evaluate_offline_reward_oracle.py`, 12 tests passing) per the main `2026-06-20.md` log — the next step is feeding it real AVB/checkpoint scores vs the binary `q_reward` baseline + paraphrase/synonym stress cases.
- **DRACO methodology** (713) → eval-tower EV-9: pos/neg rubric weighting, multi-judge ranking-stability via existing `src/bradley_terry.py`, saturation testing.
- **Gated**: GLM-5.2 (DSA PR #21149), Still (no code/GPU-CPT), Kimi-K2.7 (storage + approval), Code2LoRA/UniRL (GPU/DGX), Fusion P21.B (not built).
- Advisory: hook flagged an intake-720 `key_claims` line as a possible instruction-injection surface — it is descriptive paper content properly inside `key_claims`, left as-is.
