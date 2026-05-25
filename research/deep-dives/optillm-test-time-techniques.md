# Deep Dive: OptiLLM & Test-Time-Compute Techniques — Autopilot-Scope Analysis

**Date**: 2026-05-24
**Source intakes**: intake-601 (OptiLLM repo), intake-602 (CoT-Decoding, arXiv:2402.10200), intake-603 (DeepConf, arXiv:2508.15260), intake-604 (Sharma inference-time-techniques theory, arXiv:2506.08060)
**Trigger**: `/research-intake https://github.com/algorithmicsuperintelligence/optillm` + user request to delineate which follow-up actions are autopilot-controllable vs dedicated-research-session work.
**Related handoffs**: [`per-request-reasoning-budget.md`](../../handoffs/active/per-request-reasoning-budget.md), [`routing-and-optimization-index.md`](../../handoffs/active/routing-and-optimization-index.md) (P21), [`routing-intelligence.md`](../../handoffs/active/routing-intelligence.md), [`autopilot-continuous-optimization.md`](../../handoffs/active/autopilot-continuous-optimization.md), [`meta-harness-optimization.md`](../../handoffs/active/meta-harness-optimization.md)

---

## Executive Summary

OptiLLM is a mature (Apache-2.0, ~4k stars) OpenAI-API-compatible proxy implementing 20+ test-time-compute techniques as swappable per-request modules. It is structurally an analogue of our orchestrator. **Key correction surfaced by this deep-dive**: OptiLLM's high-value *local* techniques (DeepConf, CoT-decoding, entropy-decoding, AutoThink, ThinkDeeper) are **HuggingFace-transformers-only** (in-process model + `register_forward_hook` + `output_attentions`) and **do not run over llama-server endpoints**. They are therefore *reimplementation* targets, not drop-in dependencies. OptiLLM is a **pattern reference**, not a component we vendor.

Of the four follow-up actions, the highest-ROI item is **DeepConf-offline**: it needs only `top_logprobs` (already exposed by llama-server), the token-reduction is a direct bandwidth win on our BW-bound CPU, and once built it drops cleanly into autopilot's NumericSwarm. CoT-decoding is decoder/fork work gated by a k× bandwidth multiplier (lowest priority). The follow-up literature intake and the OptiLLM-style method-selection axis round out the set.

**Decision (user, 2026-05-24)**: build **DeepConf-offline first**, then the **method-selection axis**; both are orchestrator-side and autopilot-tunable once built.

---

## The Autopilot-Scope Question (the core deliverable)

**What autopilot is** (`epyc-orchestrator/scripts/autopilot/`, per `program.md`): a continuous optimizer over the *orchestrator codebase*. Four species — Seeder (Q-value training), NumericSwarm (Optuna/NSGA-II numeric-knob sweep → hot-swap), PromptForge (prompt `.md` mutation), StructuralLab (feature-flag experiments + routing-model lifecycle + checkpointing) — scored by a tiered T0/T1/T2 quality eval tower under a git commit→eval→keep/revert safety loop. `program.md` explicitly grants authority to "modify ANYTHING in the orchestrator codebase as long as strict git versioning is in place."

**Hard boundaries** (decisive for this analysis):
- **Never touches the llama.cpp fork** — decoder/sampler work lives in `epyc-llama` / the experimental repo, outside autopilot's repo.
- **Model registry / quant / NUMA / accel-flags are guarded** — no changes without human approval.
- **No research intake** — no web/literature; index edits require explicit approval.
- **Eval tower runs *quality* loops, not speed benches**, and cannot overlap manual benchmarking (no-concurrent-inference rule).

**The dividing line**: autopilot *optimizes/tunes* things that are flag-, knob-, prompt-, or policy-shaped and already exist in (or can be authored within) the orchestrator repo. It does **not** do novel-technique bring-up (which needs a "does this even produce different output" sanity check first per `feedback_sanity_check_before_compute`), decoder/fork work, or literature intake. **Canonical pattern: a dedicated session builds + sanity-checks + exposes a flag/knob surface → autopilot owns the ongoing Pareto sweep.**

| # | Action | Autopilot-controllable? | Lives where |
|---|--------|-------------------------|-------------|
| 1 | DeepConf — **offline** (logprob trace filtering + confidence-weighted vote) | **Tune: YES** once built · Build: dedicated | orchestrator `src/` → NumericSwarm sweeps `n_traces / percentile-η / window / warmup` |
| 1 | DeepConf — **online** (mid-generation early-stop) | **NO** | `epyc-llama` fork (sampler loop) |
| 2 | CoT-decoding | **NO** (core) | `epyc-llama-experimental` + BW roofline + manual bench |
| 3 | Follow-up intake (17 cited papers + AutoThink SSRN) | **NO** | future `/research-intake` session |
| 4 | Method-selection axis (which technique, above role-routing) | **Optimize policy: YES** once built · Build: dedicated | orchestrator `src/` → StructuralLab + PromptForge |

---

## 1. OptiLLM (intake-601)

**Architecture**: per-request technique selection via model-name prefix (`mcts-gpt-4o`, `bon&rto-model`, `moa|cot_reflection-model`) or an `<optillm_approach>` tag; `&` = sequential, `|` = parallel composition. Pluggable module system + dynamic plugin loader. **No top-level auto-router** — selection is manual/static (AutoThink has an *internal* complexity classifier but it is not a proxy-level router).

**Backend compatibility matrix** (the crux):

| Class | Techniques | Over llama-server? |
|-------|-----------|--------------------|
| API-level | MCTS, self_consistency, PlanSearch, RTO, RStar, CoT-reflection, LEAP, RE2, MARS | **YES** |
| API-level, needs `n` multi-sample | BoN, MoA, CEPO | **DEGRADED** — llama.cpp lacks `n`; falls back to sequential generation (loses parallelism) |
| Local (transformers-only) | cot_decoding, entropy_decoding, autothink, deepconf, thinkdeeper | **NO** — in-process HF model + forward hooks; cannot run over an OpenAI endpoint |

**Maturity / risk**: Apache-2.0, ~4k stars, ~10 contributors (codelion-dominated → bus-factor risk), active (last push 2026-05-07), good test coverage. **23 open issues including unfixed RCE** (z3_solver `exec()`, unsandboxed code-execution plugin) — any adoption must scope these out.

**Verdict**: `adopt_patterns`. Redundant with our role-routing for the proxy shell; additive as a *method-selection axis*; the local techniques are reimplementation targets, not usable code. AutoThink steering is effectively off the table (needs layer-19 activation injection); only its complexity-classifier idea is portable.

## 2. DeepConf (intake-603) — highest ROI

**Mechanism**: token confidence = `-mean(logprobs of top-k candidates)` (needs `top_logprobs≈20`). Aggregated into **group confidence** over a sliding window (default 2048 tokens); the predictive metric is **bottom-10% group confidence** ("a chain is only as strong as its weakest link"). Two modes:
- **Offline**: generate all K traces → score → keep top-η% → confidence-weighted majority vote. Pure post-hoc; **proxy-implementable from logprobs alone**.
- **Online**: 16 warmup traces calibrate a threshold (η→percentile); subsequent traces early-terminate when group confidence drops below τ. **Requires sampler-loop integration** (fork).

**Results**: AIME 2025 up to 99.9% @ B=512; 43–85% fewer tokens vs unfiltered majority voting; vLLM PR #23201 (≈60 LOC) shows +2.5pp / −52.9% tokens / −31% latency at low budget on DeepSeek-R1-0528-8B.

**Knobs (autopilot sweep surface)**: `n_traces ∈ {8,16,32,64,128}`, `percentile-η ∈ {10..90}`, `window ∈ {512,1024,2048}`, `warmup ∈ {4,8,16,24}`, `online|offline`, `group-metric ∈ {avg, bottom-10%, tail}`.

**Feasibility on our stack**: **Real but must be validated at low budgets.** Gains shrink at the B=8–32 we can afford on CPU, and the 16-trace warmup only amortizes above ~B=64. Logprobs cost is marginal (<5%). Offline filtering is the proxy-only path; online needs a fork change. Reference impl: `facebookresearch/deepconf` + vLLM PR #23201. Candidate-bounded limitation applies (cannot recover a correct trace never sampled).

## 3. CoT-Decoding (intake-602) — lowest priority

**Mechanism**: branch into the **top-k first tokens only**, greedy-continue each of the k paths, score each by the answer-span confidence gap `Δ = mean(p_top1 − p_top2)`; pick max-Δ or aggregate duplicate answers. Needs only top-2 logprobs (exposed). Answer-span identification is **task-specific and fragile** (e.g., "last number" for GSM8K).

**Cost**: ≈ **k× decode** (prefill shared); papers use k≈10. On our BW-bound CPU this is a 6–10× bandwidth multiplier — and a plain explicit-thinking prompt costs only ~2–3×. Reported gains e.g. Qwen2.5-0.5B GSM8K 22.8→32.4 (+9.6pp), but **no cost-adjusted frontier published**.

**Feasibility**: decoder/fork territory → `epyc-llama-experimental` + a BW roofline (`feedback_cpu_decode_bw_bound`) + a **manual** speed bench (`feedback_speed_verify_via_llama_bench`). Out of autopilot scope. Likely net-negative vs thinking-prompt on CPU; treat as a research spike, not a deployment item.

## 4. Sharma inference-time-techniques theory (intake-604) — context only

Theoretical: a base transformer can approximate SFT via in-context learning within an error margin (Turing-completeness argument; "SFT refines latent knowledge"). **No empirical validation**; assumes unbounded compute + dataset access — assumptions our finite-context CPU regime violates. Single-author paper by the OptiLLM author (commercial bias toward justifying the proxy). File as the conceptual backing for intake-601; not an action item.

---

## EPYC Integration Plan (sequenced per 2026-05-24 decision)

### Phase A — DeepConf-offline (FIRST)
1. **Build** (dedicated orchestrator session): proxy-layer module in `src/` — issue N parallel llama-server completions with `top_logprobs`, compute bottom-10% group confidence per trace, keep top-η%, confidence-weighted majority vote. Behind a default-OFF feature flag.
2. **Sanity-check** (`feedback_sanity_check_before_compute`): on a local Qwen3 server, confirm confidence filtering selects *different* (and measurably better) traces than unfiltered voting on a small slice — **STOP the running autopilot first** (no-concurrent-inference).
3. **Expose knobs**: register `n_traces / percentile-η / window / warmup / group-metric` as a NumericSwarm surface; flag as a StructuralLab toggle.
4. **Hand to autopilot**: Pareto sweep quality × token-cost (tokens as the BW proxy). Validate the low-budget regime explicitly — do not assume the AIME headline.

### Phase B — Method-selection axis (SECOND)
1. **Build**: add a "which test-time technique" axis above role-routing. Start with **self_consistency** (only cheap llama.cpp-compatible technique needing no `n`); MCTS / PlanSearch / RTO also work over llama-server. Avoid BoN/MoA/CEPO until/unless `n` multi-sampling exists.
2. **Wire a method-routing classifier + flags**.
3. **Hand to autopilot**: StructuralLab flag experiments + routing-model lifecycle + PromptForge optimize the per-query-class method policy and thresholds.

### Not scheduled
- DeepConf-online, CoT-decoding → `epyc-llama` fork spikes, gated on the Phase-A offline result proving worthwhile and a BW roofline.
- Follow-up intake (17 papers + AutoThink SSRN 5253327) → future `/research-intake` run.

---

## Open Questions / Risks
- Does confidence correlate with correctness on *our* Qwen3.5-122B / gemma4 (calibration varies by model)? Must measure, not assume.
- Is the low-budget (B≤32) DeepConf win positive after the 16-trace warmup tax on CPU? This is the make-or-break number.
- AutoThink steering is infeasible without our own llama.cpp activation-steering (separate large lift) — only the complexity-classifier idea is portable.
- Security: never import OptiLLM's z3/code-exec plugins (unsandboxed RCE).

---

## P21.A Outcome — DeepConf built, validated, NOT adopted (2026-05-24, completed early 05-25)

**P21.A1 (build): DONE.** `epyc-orchestrator` branch `feat/p21a-deepconf` (commits `d894fd5` module+flag, `3f4eaee` runner+adapter). `src/test_time/deepconf.py` (pure scorer), `deepconf_runner.py` (live N-trace generation), `Features.deepconf` flag default-OFF, 41 unit tests. Built in an isolated worktree (autopilot was committing to orchestrator `main`). A2 surfaced that the production llama.cpp build returns OpenAI-style `top_logprobs[].logprob`, not the legacy `{probs:[{tok_str,prob}]}` shape — adapter now handles both.

**P21.A2 (sanity check): DONE — DECISIVE NEGATIVE.** Validated against the live Qwen3.6-35B-A3B server (`:8080`), thinking ON, 4 hard multiplications × 6 traces (autopilot stopped for the run):

| Metric | Result |
|---|---|
| Plain majority vote | 3/4 |
| DeepConf (confidence-weighted vote @ top-50%) | 3/4 — identical answers to majority |
| Top-1 **confidence** (DeepConf's filtering signal) | **1/4** |
| Correct-vs-wrong mean confidence gap | **−0.158 (NEGATIVE)** |

On 3 of 4 questions the single highest-confidence trace was **wrong** — the model is systematically overconfident on wrong short answers (`1`@14.3, `28`@12.8, `529`@13.7 each outscored correct traces). So confidence-filtering *hurts* (1/4 vs 3/4) and confidence-weighted voting *degenerates to plain majority* (3/4=3/4) — **zero accuracy gain for N× generation + `n_probs` logprob overhead** (~58 s/trace on CPU). Directly confirms the candidate-bounded / "confidently wrong" contradicting evidence at intake-601/603.

**P21.A3 (wire knob surface for autopilot): DO NOT PROCEED.** No accuracy benefit + real cost. The `program.md` gate is updated from "not-yet-built" to "do-not-wire (A2 negative)". The branch is preserved as a validated reference (default-OFF, not merged to `main`) in case a future, better-calibrated model or a much larger trace budget (N≫6) warrants a revisit — but the *confidence metric itself* is anti-correlated here, which more traces won't fix (they'd only help the vote, which already ties majority).

**Takeaway:** the sanity check did its job — it prevented wiring a no-gain technique into production and handing autopilot a useless, compute-burning knob surface.
