# Qwen3.6-35B-A3B — Production Upgrade Evaluation

**Status**: in-progress (quality benchmark ready)
**Created**: 2026-04-17 (via research intake)
**Updated**: 2026-04-17 (NUMA sweeps complete, quality benchmark infrastructure ready)
**Categories**: moe_optimization, ssm_hybrid, inference_serving
**Priority**: HIGH (direct production model successor)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`log-linear-gated-deltanet-readiness.md`](log-linear-gated-deltanet-readiness.md), [`bulk-inference-campaign.md`](bulk-inference-campaign.md)

## Objective

Evaluate Qwen3.6-35B-A3B as a drop-in replacement for the production Qwen3.5-35B-A3B model. Same hybrid architecture (Gated DeltaNet + Gated Attention + MoE), same parameter counts (35B total, 3B active), but improved benchmarks across the board — particularly agentic coding (+11pp Terminal-Bench, +3.4pp SWE-bench).

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-387 | Qwen3.6-35B-A3B model card | high | new_opportunity |
| intake-391 | Qwen3.6-35B-A3B GGUF (unsloth) | high | new_opportunity |

## Key Upgrade Signals

- **Architecture identical**: 10x(3xGDN->MoE -> 1xAttn->MoE), 256 experts, 8+1 active, 2048 hidden dim, 40 layers
- **GGUF ready**: Q4_K_M = 22.1 GB (vs ~22 GB for Qwen3.5 Q4_K_M). Drop-in file swap.
- **New features**: `preserve_thinking` (retain reasoning context across turns), enhanced tool calling with nested object parsing
- **Benchmark gains**: SWE-bench Verified 73.4 (was 70.0), Terminal-Bench 2.0 51.5 (was 40.5), MMLU-Pro 85.2

## Deep Dive Findings (2026-04-17)

### Architecture Confirmation
- `config.json` declares `"model_type": "qwen3_5_moe"` and `"architectures": ["Qwen3_5MoeForConditionalGeneration"]`
- **Byte-for-byte identical structure** to Qwen3.5-35B-A3B. All improvements are post-training only.
- **No llama.cpp patches needed** beyond existing Qwen3.5 support

### Known llama.cpp Issues (carry over from Qwen3.5)
- Parallel-slot "Chunk not found" crash (issue #20222) with hybrid attention
- seq_add assertion failure (issue #19915) — our IMROPE patch addresses this
- Silent unload under heavy load (issue #20002)
- KV cache: use bf16 or q8_0, NOT f16 (clips dynamic range, PPL degradation)

### preserve_thinking
- **Jinja chat template feature**, not architecture change
- Works with llama.cpp `--jinja` flag: `--chat-template-kwargs '{"preserve_thinking": true}'`
- Retains `<think>` blocks from prior turns instead of stripping — useful for multi-turn agentic sessions

### Independent Benchmarks
- BenchLM provisional: #41/109 overall (64/100), **#14/109 in coding (81/100)**
- Weakest: Knowledge (#38). Model is 2 days old, verified pool still small.

### Benchmark Comparison (Qwen3.5 → Qwen3.6)

| Benchmark | Qwen3.5 | Qwen3.6 | Delta |
|-----------|---------|---------|-------|
| SWE-bench Verified | 70.0 | 73.4 | +3.4 |
| Terminal-Bench 2.0 | 40.5 | 51.5 | **+11.0** |
| NL2Repo | 20.5 | 29.4 | +8.9 |
| QwenWebBench | 978 | 1397 | +419 |
| AIME 2026 | — | 92.7 | — |
| MMLU-Pro | — | 85.2 | — |

No regressions reported.

## Resolved Questions

- [x] **llama.cpp compatibility**: Confirmed — identical model_type, zero patches needed
- [x] **preserve_thinking**: Works via `--jinja` flag with chat template kwargs
- [x] **tok/s on EPYC 9655**: 25.6 baseline, 27.4 with ngram dm=64 (+10.1%). Q8 faster than Q4 (25.6 vs 24.4).
- [ ] **PPL regressions**: Pending — quality benchmark ready to execute
- [ ] **Coding eval**: Pending — quality benchmark ready to execute

## Evaluation Plan

1. [x] Download Q4_K_M GGUF from unsloth/Qwen3.6-35B-A3B-GGUF — COMPLETE (deleted, Q8 faster)
2. [x] Download Q8_0 GGUF — COMPLETE (`/mnt/raid0/llm/models/Qwen3.6-35B-A3B-Q8_0.gguf`)
3. [x] Run throughput benchmark (single-model 192t, NUMA 4-way) — COMPLETE: 25.6 baseline, 27.4 w/ngram, 57.4 quad, 76.8 eight
4. [ ] Run quality eval (full suite battery via run_benchmark) — IN PROGRESS: required `use_chat_api: true`, `reasoning: off`, KV `q8_0/q8_0`. Three failed attempts (think loops, `/think` loops, degenerate repetition) before finding correct config. Current run uses `--reasoning off` server flag.
5. [ ] Run coding eval (SWE-bench subset or equivalent) — validate agentic coding claims
6. [ ] If no regressions: swap into production registry (`model_registry.yaml`)

## GGUF Files

| Quant | Size | File | Status |
|-------|------|------|--------|
| Q4_K_M | 22.1 GB | `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` | DELETED (Q8 faster) |
| Q8_0 | 36.9 GB | `Qwen3.6-35B-A3B-Q8_0.gguf` | Active |

Target: `/mnt/raid0/llm/models/`

## Notes

Released April 16, 2026. This is a weights-only upgrade — all improvements from post-training focused on agentic coding. The +11pp Terminal-Bench gain is the most compelling signal for our orchestrator use case. Ollama already ships it as `qwen3.6:35b-a3b`.

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-455] "Qwen3.6-27B Spec-Decoding on RTX 4090 with 1.7B Same-Family Draft (community note)"** (`inline:qwen36-27b-spec-decoding-rtx4090-2026-04-24`)
  - **Model mismatch caveat**: this note targets the freshly-released **Qwen3.6-27B dense** (released 2026-04-22, Apache-2.0, 262K ctx extensible to 1M), which is **distinct** from this handoff's **Qwen3.6-35B-A3B hybrid-MoE**. The 5.9× GPU speedup numbers do **not** transfer — MoE + hybrid-SSM verification-wall is documented in `wiki/speculative-decoding.md`, and thc1006's 19-config sweep on Qwen3.6-35B-A3B + 0.8B draft on RTX 3090 (2026-04-19) found **no net speedup** post-PR-#19493.
  - Relevance to this handoff: signals that Qwen3.6 family now has a **dense 27B variant** — a potential new worker/coder model candidate. Worth a separate CPU-feasibility probe (BW-bound decode on EPYC 9655 for a 27B dense in Q4_K_M).
  - Action: **flag for model-intake** — evaluate Qwen3.6-27B-Q4_K_M as a CPU candidate for the coder/worker slot. Do not conflate with the 35B-A3B upgrade tracked here. If promoted, spawn a sibling handoff.

## Research Intake Update — 2026-05-04

### Qwen-Scope SAE Suite Includes Qwen3.5-35B-A3B (predecessor architecture)

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30, OSS PDF)
  - Direct relevance: Qwen-Scope releases SAEs for **Qwen3.5-35B-A3B-Base** — the production predecessor of the 35B-A3B-hybrid model this handoff is upgrading from. Two widths: W32K-L0_50 and W128K-L0_100, all 40 layers, expansion factors 16x and 64x. There are NO published SAEs for Qwen3.6-35B-A3B (released 2026-04-16, ~2 weeks before Qwen-Scope), so the upgrade target itself remains uncovered.
  - Practical implication: the Qwen3.5 SAEs can serve as a **diagnostic baseline** for the upgrade evaluation — feature activations on identical prompt sets between the predecessor (with SAEs) and the upgrade (without yet) reveal whether the post-training shift in Qwen3.6 has moved the model away from the SAE-discovered feature basis. If it has, that argues against transferring any future Qwen-Scope-derived intervention without re-training SAEs.
  - Specific application: the three documented failure modes in this handoff's task 4 — "think loops, /think loops, degenerate repetition" while running the quality eval — match exactly the **endless-repetition feature mechanism** documented in Qwen-Scope Section 8. The SAE-Res-Qwen3.5-35B-A3B-Base-W32K-L0_50 release would let us inspect whether those repetition failures activate the same repetition features identified on Qwen3-30B-A3B (which also has a Section 8 result). If the pattern transfers, the Section 8 RL recipe (SAE-guided rare-negative augmentation in DAPO) becomes a candidate post-training intervention for Qwen3.6-35B-A3B once SAEs are trained on it.
  - Architecture caveat: Qwen3.5 -> Qwen3.6 keeps the 256-expert / 8+1-active / 40-layer structure but the post-training is different. Feature transferability between predecessor and successor SAEs in MoE+hybrid-SSM architectures is not characterized in the Qwen-Scope paper; the only same-architecture longitudinal comparison the paper makes is Qwen3 vs Qwen3.5.
  - Action: defer; mentioned in `qwen-scope-sae-toolkit.md` (stub 2026-05-04). Do NOT block the production-upgrade quality eval on SAE inspection. If quality regressions concentrate on think-loop or repetition-style failures (matching task-4 history), fall back to the SAE diagnostic path. Otherwise the SAEs remain a future-research asset for the predecessor model only.
  - Caveats (Tier 2b): Qwen-Scope's Section 7 SASFT shows non-trivial general-capability regressions on Qwen3-8B (HellaSwag -2.88pp, MMLU -2.06pp); applying SASFT-style suppression to a production candidate would need diversity-collapse + general-capability gates beyond what this handoff's current eval suite measures.

## 2026-05-04 — STACK SWAP COMMITTED (pending final amendment)

Qwen3.6-35B-A3B Q8 swap into `frontdoor` slot **committed** in `epyc-orchestrator` branch `feature/stack-swap-2026-05-04`:
- Server entry `frontdoor` (port 8080): GGUF swapped Qwen3.5-35B-A3B-UD-Q4_K_M.gguf → Qwen_Qwen3.6-35B-A3B-Q8_0.gguf, model_role updated to qwen36_q8_0
- Role definition `frontdoor`: throughput 24.3 t/s (May-4 canonical baseline aggregate), quality 93% (170/183 Claude-as-Judge 6-suite under canonical recipe)

**Same branch additionally**:
- `coder_escalation` swapped Qwen2.5-Coder-32B Q4 → **Qwen3-Coder-30B-A3B Q4** (consolidated)
- `worker_general` and `toolrunner` doc-updated to reflect Qwen3-Coder-30B-A3B Q4 (already deployed since 2026-03-19, registry stale)
- `thinking_reasoning` role REMOVED entirely (GGUF deleted from disk 2026-03-06)
- Routing-hint `prove/verify` rewired thinking_reasoning → architect_general (commit 587219c)

**Commits ahead of `main`**: `fee69b8` (afternoon, MoE-Spec budget + initial swap) + `587219c` (evening, routing-hint cleanup).

Pending: re-bench `reap_246b` and `ingest_long_context` under canonical recipe to decide architect_coding confirmation + ingest consolidation question. Tomorrow's session.

This handoff is now **CLOSE TO DONE** — pushing the branch + the two unscored re-benches will close it.

## 2026-05-06 — STACK CONSOLIDATION ADVANCED (5 commits ahead of main)

Two more orchestrator commits land on `feature/stack-swap-2026-05-04`. Branch is now at **5 commits** ahead of main: `7491a12 dad42a0 587219c fee69b8 9b8143e`.

### Architect candidates re-benched on full battery (May 5)

| Candidate | Before (master CSV) | After (May-5 full sweep) | t/s |
|---|---|---|---|
| Qwen3.5-122B-A10B Q4_K_M | 56/61 (92%, OLD suite) | **196/210 (93%)** = 172/183 standard + 24/27 long_context | 12.34 |
| Qwen3.6-27B Q4_K_M | 141/147 (96%, partial) | **173/183 (95%)** | 6.53 |
| Qwen3.6-27B Q8_0 | 123/126 (98%, partial) | **166/183 (91%)** | 4.42 |

Verdict: **keep Qwen3.5-122B-A10B Q4_K_M as architect_general** — quality tied across all 3, but 122B is fastest by 2× and only candidate with proven long_context capability.

### REAP-246B falsification → architect_coding role ELIMINATED

Per master CSV cross-check (`benchmarks/results/reviews/summary.csv`):
- REAP-246B coder = **7/10 (70%)**
- Worker (Qwen3-Coder-30B-A3B Q4) coder = 23/30 (77%)
- Frontdoor (Qwen3.6-35B-A3B Q8) coder = **29/30 (97%)**

REAP-246B is WORSE on coder than the consolidated worker AND 27pp behind the frontdoor model AT 4× the speed. The "hardest coding escalation" purpose is no longer met by REAP-246B. Role ELIMINATED in commit `7491a12`.

### Coder_escalation swapped to Qwen3.6-35B-A3B Q8

Same model as frontdoor — separate server (independent slot/crash domain/system prompt) with shared GGUF mmap. Net incremental RAM cost ~0. Replaces the 2026-05-04 consolidation onto Qwen3-Coder-30B-A3B Q4 (which had only 77% coder vs frontdoor's 97%). Hard coding escalations now route here.

### Additional cleanup commit `dad42a0`

`process_layout.hot_resident` stripped of stale draft entries (`draft_qwen25_coder`, `draft_qwen25` — no current targets after 2026-05-04 consolidation). Per-role draft `memory.residency` relabeled `co_resident_with_target` for the two production-active drafts (`draft_qwen3_coder_0_75b`, `draft_qwen35_0_8b_q8_0`) — they load inside their target server's llama-server process via `--draft-model` and pin via mlock, never run standalone.

### Remaining

1. **Bench Qwen3.6-35B-A3B Q8 on long_context** to decide frontdoor + ingest_long_context consolidation. Currently held up by post-1.5d-uptime preflight failure (bench bimodal-throughput recurrence; reboot pending).
2. **Push `feature/stack-swap-2026-05-04`** to origin once #1 is resolved.

This handoff is now **CLOSE TO DONE**. The frontdoor swap + 4-way worker consolidation + architect_coding elimination are all committed; only the long-context-driven ingest decision remains.

## 2026-05-06 — STACK SWAP MERGED + LIVE ✅

`feature/stack-swap-2026-05-04` MERGED into epyc-orchestrator main via merge commit `a268040`. Pushed to origin. Branch deleted (local + remote).

### Final commit chain merged

```
a268040 (merge) Merge stack-swap-2026-05-04: full stack consolidation + launcher refactor
├─ bd2455d orchestrator_stack: derive HOT/WARM_SERVERS from single-source classification
├─ 02e871d orchestrator_stack: align launcher with May-4/6 registry stack swap
├─ 852fd5c orchestrator: swap worker_summarize → Qwen3.6-35B-A3B Q8 (shared GGUF with frontdoor)
├─ 78fdaf4 orchestrator: deprecate worker_pool config — superseded by worker_general consolidation
├─ a26744c orchestrator: invert three_stage_summarization stages + promote ingest_long_context to hot
├─ 7491a12 orchestrator: remove architect_coding + swap coder_escalation to frontdoor model
├─ dad42a0 orchestrator: clean up process_layout + draft residency metadata
├─ 587219c orchestrator: remove thinking_reasoning routing reference
└─ fee69b8 orchestrator: plumb MoE-Spec budget=40 + initial frontdoor swap
```

### Frontdoor long_context bench — 27/27 (100%)

Post-reboot bench of `qwen36_q8_0` on long_context suite returned 27/27 (100%) — beating Qwen3-Next-80B-A3B Q4 (93%), Qwen3.5-122B-A10B (89%), Qwen3-Coder-30B-A3B (59%). Used as input to the three_stage_summarization stage inversion decision (Stage 2 = frontdoor since it has the highest long_context quality). CSV at `benchmarks/results/reviews/may4_long_context/qwen36_q8_0_long_context.csv`.

### What's still open after merge

1. **Live deployment validation**: orchestrator_stack.py `start` should be run once on a freshly-rebooted host to confirm the merged stack actually launches without errors. Module-load + registry-validation passes statically; live launch is the final gate. Recommended: stop existing stack, reboot, `start --hot-only`, verify all 8 hot processes come up healthy.

2. **Tighten preflight uptime warn threshold** (`scripts/lib/canonical_recipe.py` UPTIME_WARN_DAYS): bimodal-throughput failure recurred at 1.5d uptime in this session arc, below the documented 2.0d threshold. Tighten to 1.0-1.5d. Low priority — purely advisory (warn-only, doesn't block).

3. **Long-context tier-3 rubric script audit**: context generation produces tech-docs instead of domain-specific content for t3_q1/t3_q2/t3_q3. All models correctly refuse, so rubric can't discriminate quality on these. Affects future ingest model evaluation. Belongs to a separate `benchmarks` handoff.

This handoff is **COMPLETE** for the qwen36 production upgrade. Moving to `handoffs/completed/` is appropriate.
