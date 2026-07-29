# RAO + RLM Cluster Deep-Dive — 2026-05-19

**Author**: research-intake follow-up (Phase 6, deep-dive cluster #1 of 8)
**Scope**: 7 intakes (intake-536, 541, 537, 547, 548, 549, 550) + canonical RLM (intake-153) context.
**Status**: deep-dive (not a handoff). Findings feed `meta-harness-optimization.md`, `halo-trace-loop-spike.md`, `tri-role-coordinator-architecture.md`, `outer-coordinator-learned-head.md`, `hermes-outer-shell.md`, `repl-turn-efficiency.md`, `context-folding-progressive.md`.

---

## Executive Summary

After going one level deeper than the intake notes, the picture sharpens in three ways. First, the **RLM-side already has more empirical depth than the RAO-side** thanks to the Wang reproduction (intake-547), which directly quantifies the depth-2 cliff (DeepSeek v3.2 S-NIAH wallclock 3.6s → 89.3s → 344.5s for depth 0/1/2; OOLONG accuracy 0.0 → 42.1 → 33.7) and matches what EPYC's `01-fast-rlm-budget-controls` already enforces with hard recursion-depth and call-count caps — so the user's intuition that RLM-side was under-weighted in the intake is correct: the field-evidence is now stronger than the original arxiv:2512.24601 paper alone. Second, **ReDel (intake-550) is a near-perfect off-the-shelf substrate** for both the RLM-style inference harness AND the RAO-style training harness — same delegation primitive, MIT-licensed but with a Commons Clause restricting resale (not a problem for EPYC, which is single-user research-only). Third, **the single highest-leverage EPYC action is NOT to train an RAO policy**, it is to **adopt ReDel's `DelegateWait` (deferred-delegation, asyncio.gather) and event-stream logger as drop-in replacements for the current REPL-executor delegation surface**, AND to use the orchestration-trace survey's (intake-548) 5-sub-decision taxonomy to formally tag the existing autopilot trace store so that every future RL/learned-head decision can be sliced by sub-decision class. Training-side RAO replication remains gated by GPU compute we do not have (DGX Spark not yet — see `project_dgx_spark_target`).

The single highest-leverage action: open a spike (≤200 LoC, 1 person-week) that wraps `epyc-orchestrator`'s existing REPL executor in a ReDel-compatible event stream, then mirrors `halo-trace-loop-spike` HALO-2 conversion so the orchestration-trace taxonomy (intake-548) labels every span by `{when-to-spawn, whom-to-delegate, how-to-communicate, how-to-aggregate, when-to-stop}`. This is a pure substrate change with no training cost and immediately unblocks both the outer-coordinator learned-head (intake-474 / `outer-coordinator-learned-head.md` OC-0.3 "fitness signal" question) and the meta-harness Tier 3 design.

## Intakes Covered

- **intake-153** — Recursive Language Models (Zhang/Kraska/Khattab, arxiv:2512.24601). Canonical RLM. `already_integrated`, ~80% pattern coverage. The anchor.
- **intake-536** — Recursive Agent Optimization (Gandhi/Chakraborty/Wang/Kumar/Neubig, CMU, arxiv:2605.06639). RL training paradigm for recursive agents; LLM-judge node rewards + mean-of-children + LOO + depth-inverse-frequency.
- **intake-541** — @neural_avb X-post breakdown of RAO. Secondary/pedagogical.
- **intake-537** — TDS blog "RLMs: An All-in-One Deep Dive" by Avishek Biswas. Pedagogical recap of intake-153; `already_integrated`.
- **intake-547** — "Think, But Don't Overthink: Reproducing RLMs" (Daren Wang, arxiv:2603.02615). First independent RLM reproduction; depth-2 overthinking + 96× wallclock cliff quantified.
- **intake-548** — "RL for LLM-based MAS through Orchestration Traces" (Chenchen Zhang, arxiv:2605.02801). Survey + 5-sub-decision taxonomy + 8-reward-family taxonomy + 84-paper tagged pool. Identifies stopping-decision-RL as the structural gap.
- **intake-549** — Tree-GRPO (Ji et al, arxiv:2509.21240, ICLR 2026). Tree-structured GRPO where each node is a complete agent interaction step; prefix-sharing rollouts; Apache-2.0 code (github.com/AMAP-ML/Tree-GRPO, 355 stars).
- **intake-550** — ReDel (Zhu/Dugan/Callison-Burch, arxiv:2408.02248, EMNLP 2024 Demo). Open-source recursive multi-agent toolkit. MIT + Commons Clause, 93 stars, pushed 2026-05-11 (active), Python 3.10+, built on `kani`.

## The RLM-RAO Stack as a Whole

The cluster fragments into three architectural layers and three roles within each layer. The 5-sub-decision taxonomy of intake-548 is the glue that makes them comparable.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3 — TRAINING SIGNAL (RL or none)                                       │
│  • RAO (536):   per-node LLM-judge + mean-of-children + depth-inv-freq + LOO │
│  • Tree-GRPO (549): step-DPO via tree-structured group baselines             │
│  • Context-Folding (154): FoldGRPO with process rewards                      │
│  • RLM (153):   none — uses off-the-shelf models                             │
│  • ReDel (550): none — substrate only                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ LAYER 2 — POLICY ARCHITECTURE                                                │
│  • RAO:   recursive-spawn decision learned per node                          │
│  • RLM:   recursive-spawn hand-coded via REPL llm_query() calls              │
│  • ReDel: recursive-spawn via delegate() tool, scheme-pluggable              │
│  • Tree-GRPO: orthogonal — applies to any agent policy                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ LAYER 1 — EXECUTION SUBSTRATE (the harness)                                  │
│  • Python REPL sandbox + asyncio.gather (all three)                          │
│  • Tool-calling protocol on parent side                                      │
│  • Event-stream logger (ReDel ships this; RAO/RLM assume it)                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

The 5 sub-decisions (intake-548) cut across all layers and let us name what each paper trains vs hard-codes:

| Sub-decision | RAO (intake-536) | RLM (intake-153) | ReDel (intake-550) | Tree-GRPO (intake-549) | Survey (intake-548) verdict |
|---|---|---|---|---|---|
| when-to-spawn | **LEARNED** (mean-of-children reward) | heuristic (depth=1 cap, llm_query in code) | heuristic (LLM emits `delegate()` call) | optimizer-agnostic | covered by orchestration-rewards family |
| whom-to-delegate | LEARNED (single policy, all children same model) | hand-coded (single model) | pluggable (configurable per node) | optimizer-agnostic | covered |
| how-to-communicate | hand-coded (child output = Python value to parent) | hand-coded (FINAL(var) / FINAL(str)) | hand-coded (chat-message return value) | optimizer-agnostic | partial coverage |
| how-to-aggregate | hand-coded (parent reasoning) | hand-coded | hand-coded | optimizer-agnostic | partial coverage |
| **when-to-stop** | **hand-coded (depth/step cap)** | hand-coded (depth=1) | hand-coded (depth limit triggers) | hand-coded | **NO published RL method as of May 2026** |

The "when-to-stop" row is the survey's headline gap. RAO does not close it — it caps depth and lets a fixed budget enforce stopping. RLM defaults depth=1 (intake-547 reproduces that this is correct). ReDel relies on its `depth_limit` trigger. **This is the highest-leverage EPYC-specific opportunity** because on CPU every token costs an order of magnitude more than on frontier GPU stacks, and our autopilot already has the trace-density to derive a process-level stopping reward.

## Cross-Paper Comparison Tables

### Table A: Training-signal architecture

| System | Reward locality | Anti-exploit measure | Baseline | Depth handling | Stop policy | Compute claim |
|---|---|---|---|---|---|---|
| RAO (intake-536) | per-node LLM-judge (gpt-5-mini) | **MEAN** (not sum) of children success | leave-one-out (LOO) across rollout group | inverse-frequency depth weighting | fixed depth/step cap | (to verify — paper-level extracts not retrievable via ar5iv; X-post says "30B trained") |
| Tree-GRPO (intake-549) | step-level from outcome (derived) | prefix-sharing forces sibling diversity | intra-tree group-relative + inter-tree | implicit via tree shape | none (rollout-level) | 11 datasets × 3 QA types; (to verify model sizes) |
| Context-Folding (intake-154) | process rewards per branch | folding penalty | standard GRPO | learned via FoldGRPO | terminal | (to verify) |
| RLM (intake-153) | none (no training) | n/a | n/a | depth-1 default in paper | hard cap | API-cost report only |
| ReDel (intake-550) | none (substrate) | n/a | n/a | configurable | trigger-based | n/a |

### Table B: Execution-substrate alignment with EPYC's existing REPL

| Feature | EPYC `repl_executor` | ReDel | RLM (paper) | RAO (paper) | Notes |
|---|---|---|---|---|---|
| Sandbox | Python REPL (Pyodide-style? — to verify) | Python in-process | Python REPL | Python REPL | All converge on Python+REPL |
| Async parallel children | **partial** (per `01-fast-rlm-budget-controls`) | `asyncio.gather` via `DelegateWait` | `asyncio.gather` | `asyncio.gather` | Full parity |
| Child output exposure | variable assignment + truncation cap (5000 tok) | return value from tool call | Python variable | Python variable | All "pass-by-reference" |
| Recursion-depth cap | `state.repl_executions` budget | `depth_limit` trigger | depth=1 hard-coded | adaptive ~4 | EPYC closest to RLM cap |
| Event stream | inline diagnostics in `repl_executor.py` | first-class `events.py` (97 LoC) | not specified | not specified | **ReDel has the cleanest event surface** |
| Tool plug-in | `tools/` (orchestrator-side) | `tool_config.py` + `tools/` directory | not specified | not specified | Both pluggable |
| Visual debugger | none | web UI (Vue/FastAPI), event replay | none | none | **ReDel is the only one with a UI** |
| Backend swap | local llama-server | OpenAI/Anthropic via `kani`; OPENAI_BASE_URL swap works | LLM-agnostic in paper | LLM-agnostic | All three swappable |

### Table C: Reported costs, model sizes, benchmarks

| Source | Model trained / served | Benchmark | Headline number | Cost note |
|---|---|---|---|---|
| RAO (intake-536 / intake-541) | 30B-class (from X-post; size class to verify from paper) | TextCraft-Synth (hard) | 0.88 vs ~0 single-agent | (to verify GPU-hours) |
| RAO | same | Oolong-Real (10-12pg D&D, 32K ctx) | 30B recursive ≈ frontier Claude/o3/GPT-5-mini | (to verify) |
| RAO | same | DeepDive | adaptive depth ~4, ~18× single-agent latency | (to verify) |
| RAO | same | ART-E (ablation) | (to verify) | (to verify) |
| RLM-Repro (intake-547) | DeepSeek v3.2 | S-NIAH (20 samples) | depth 0/1/2 acc = 100/85/70%, wallclock = 3.6/89.3/**344.5s** | API cost |
| RLM-Repro | DeepSeek v3.2 | OOLONG trec_coarse (20, 1K-64K) | depth 0/1/2 acc = 0.0/42.1/33.7% | API cost |
| RLM-Repro | Kimi K2 | S-NIAH | depth 0/1/2 acc = 100/90/— (depth-2 crashed) | API cost |
| RLM-Repro | Kimi K2 | OOLONG | depth 0/1/2 acc = 86.6/60.0/55.0% | **depth-0 better than depth-1!** for OOLONG on Kimi K2 |
| RLM (intake-153) | RLM-Qwen3-8B (fine-tuned) | CodeQA / BrowseComp+ / OOLONG | 32 / 14 / 32 | $0.99/query (BrowseComp+) |
| RLM | Qwen3-Coder-480B + RLM | CodeQA / BC+ / OOLONG | 56 / 44.7 / 48 | open-source-only frontier |
| RLM | GPT-5 + RLM | CodeQA / BC+ / OOLONG / OOLONG-Pairs | 62 / 91.3 / 56.5 / 58 | frontier upper bound |
| Tree-GRPO (intake-549) | (model sizes to verify) | 11 datasets × 3 QA types | "outperforms chain-GRPO" | ICLR 2026 accept |
| ReDel (intake-550) | GPT-4o / GPT-3.5-turbo demo | FanOutQA / TravelPlanner / WebArena (demo branch) | qualitative, demo paper | n/a |

The Wang reproduction (intake-547) is the only paper in the cluster with **independently reproduced numbers** on the exact RLM framework. Note: the "depth-1 better than depth-0" effect is only present on OOLONG (linear-aggregation task); on S-NIAH (constant-retrieval task) depth-0 always wins. **This empirically supports `repl-turn-efficiency.md` and `01-fast-rlm-budget-controls.md`'s posture: do not blanket-default to recursive — gate on task complexity class.**

## EPYC Integration Path

### Option 1: ReDel as substrate (RECOMMENDED, low risk)

ReDel is the right substrate to evaluate as a replacement for EPYC's current REPL delegation surface. Evidence:

- **License**: MIT base + Commons Clause that bars resale (`gh api repos/zhudotexe/redel/contents/LICENSE`). For internal research-only use this is fully permissive. **CAVEAT**: the Commons Clause was added 2025-02-27 (commit `376920c1`). It would block a hypothetical future "EPYC-as-a-service" offering but does NOT affect any current scope or any of the open-source contribution paths.
- **Codebase size**: 98.9 KB Python (delegation module alone is 4 files / ~14 KB). pyproject shows minimal core deps: `kani>=1.1.0,<2.0.0`, `kani-ratelimits`, `pydantic>=2.0`, `rapidfuzz>=3.9`. Optional web extra adds FastAPI/uvicorn/websockets — already in EPYC stack.
- **Repo activity**: 93 stars, default branch `main`, last push 2026-05-11 (one week ago), 2 open issues. Active maintenance.
- **Backend swap**: built on `kani`, which exposes `OPENAI_BASE_URL` and `OPENAI_API_KEY` swap for any OpenAI-compatible server — our llama-server already serves this surface. **No fork required.**
- **Two delegation primitives**:
  - `DelegateOne` (5.6 KB, blocking) — equivalent to today's sequential `llm_call` in `repl_executor.py`.
  - `DelegateWait` (5.6 KB, non-blocking, `asyncio.gather`-compatible) — directly fills the "partial async parallel sub-LM calls" gap noted in intake-153 EPYC integration status.
- **Net new patterns over current EPYC code**: (a) first-class event stream (`events.py`, 2.9 KB) with replay; (b) web visual debugger; (c) clean separation of `tool_config.py` from execution; (d) `kani`'s built-in `kani-ratelimits` integration.
- **Predates RAO by ~1 year and is the engineering substrate RAO assumes** — using ReDel makes any later RAO replication a code-localized addition (a learned head over the delegate-vs-execute decision), not a from-scratch build.

### Option 2: RAO training recipe on EPYC (DEFERRED — gated by hardware)

RAO claims to train a model that learns recursive decomposition. The training recipe's three tricks are reproducible from the methodology section (multi-task objective sampled across tree depths; LOO baseline shared across rollout group; inverse-frequency depth weighting). The blocker is compute:

- **Forward-pass evaluation on EPYC**: feasible — EPYC serves 30B-A3B Q4 at 76.5 t/s solo (per `project_worker_general_swap_2026_05_08`).
- **RL training itself**: requires gradient updates. RAO uses LLM-judge rewards from gpt-5-mini (external API), so the judge cost is per-rollout API spend, not local compute. The policy-update step needs autodiff. EPYC's CPU stack does not currently support training; DGX Spark target is not yet acquired (per `project_dgx_spark_target`). **Until DGX Spark is acquired, RAO training is API-bench-only experimentation against a fixed off-the-shelf policy — i.e., RLM, not RAO.**
- **Target model**: when DGX Spark lands, the right RAO-replication target is `Qwen3-8B` to match intake-153's RLM-Qwen3-8B baseline (32% CodeQA, 14% BrowseComp+, 32% OOLONG after RLM fine-tune on 1000 unrelated-domain samples). Direct head-to-head against RLM-Qwen3-8B becomes possible. Larger targets (Qwen3-1.7B drafter, gemma4-26B-A4B) are out-of-scope for RAO replication because LOO+depth-inverse-frequency assumes per-rollout batch size that DGX Spark may or may not support at those sizes.

### Option 3: Tree-GRPO as a methodological alternative (LOWER PRIORITY)

Tree-GRPO (intake-549) is Apache-2.0 (github.com/AMAP-ML/Tree-GRPO, 355 stars, last push 2026-01-26, 5.3 MB). It is a methodological alternative to RAO's LOO baseline — uses prefix-sharing across siblings instead. **Same hardware blocker as Option 2.** Worth tagging in `decision-aware-routing.md` as a future option but not implementable now. The equivalence-proof contribution (intra-tree group-relative = step-level DPO) is a result-only artefact — does not require code to consume.

### Connection to existing handoffs

| Handoff | What this cluster changes | Specific edit |
|---|---|---|
| `meta-harness-optimization.md` | Already updated (line 419) with RAO. Add ReDel evaluation as Tier 3 substrate option + 5-sub-decision taxonomy as the labelling schema for Tier 3 prompt-template search-space cells. | Append "RAO+RLM cluster deep-dive 2026-05-19" subsection pointing here. |
| `halo-trace-loop-spike.md` | HALO-2 converter should emit 5-sub-decision labels as OpenInference span attributes (one extra ~10-LoC mapper). Lets a single labeller serve both HALO analysis AND any future RAO/Conductor-style outer-coordinator training. | Update HALO-2 task spec to mandate the 5-sub-decision attribute. |
| `tri-role-coordinator-architecture.md` | The intake-548 taxonomy is **orthogonal** to the Trinity (T/W/V) role axis: role = WHAT the call does; sub-decision = WHERE in the orchestration lifecycle the call sits. Useful clarification, no scope change. | Add a one-line note in TR-1 deliverable that the role axis composes with the sub-decision axis. |
| `outer-coordinator-learned-head.md` | OC-0.3 ("identify the fitness signal") is exactly the survey's "when-to-stop" gap. The deep-dive answers OC-0.3 partially: terminal task success × stopping efficiency (tokens-to-correct-stop) is the natural fitness signal because it is the one sub-decision NO published RL method covers, so the differential value is highest. | Strengthen OC-0.3 with a forward pointer to this deep-dive. |
| `hermes-outer-shell.md` | Already updated (line 400) with RAO. Tag in: ReDel's `DelegateWait` is what Hermes's "delegate from outer to inner" primitive looks like in code today. | Append ReDel detail (license caveat + 4-file delegation module size) to the existing RAO subsection. |
| `repl-turn-efficiency.md` | Confirms the depth-1 default is right; depth-2 is 96× slower on retrieval and accuracy-NEGATIVE on Kimi K2 OOLONG (86.6 → 60.0). **Strengthens the no-deeper-recursion posture.** | Add a "Wang 2026 reproduction" data row to the budget-rationale section. |
| `context-folding-progressive.md` | Context-Folding's FoldGRPO is the closest published analogue to a stop-decision-trained policy (folding = "stop here, summarize, continue"). Worth a cross-reference. | Note intake-547+intake-548 as supporting evidence for the folding hypothesis. |

## Failure Modes & Contradicting Evidence

Consolidated from the intake entries plus the fresh fetches above:

1. **Depth≥2 overthinking (intake-547, EMPIRICAL)** — DeepSeek v3.2 S-NIAH accuracy drops from 100% → 85% → 70% at depth 0/1/2; Kimi K2 depth-2 outright crashed on S-NIAH. The 96× wallclock blow-up on S-NIAH is concrete cost data, not anecdote. **Action: hard-cap recursion at depth=1 in any EPYC integration until a learned stop policy is in place.**
2. **Stopping-decision gap (intake-548, STRUCTURAL)** — NO published RL method as of May 2026 trains the stopping decision. RAO uses fixed depth/step caps; this exposes it to "deferred-failure" reward hacking (delegate forever) and "undercommitment" (always stop early).
3. **Process-reward / LLM-judge reward hacking (intake-536, RISK)** — RAO's per-node gpt-5-mini judge is the proxy reward class with the most documented reward-hacking attack surface (the "judge writes the script" failure mode). RAO does not include a robustness audit in the seed-entry-level evidence we have; would need to verify from full paper text whether the authors run held-out judges.
4. **Mean-of-children masks individual catastrophic failures (intake-536, BIAS)** — Mean-of-children reward is good for blocking trivial-spawn (sum-of-children-success would reward splitting unnecessarily), but it ALSO biases the parent toward splits where on AVERAGE children succeed — even if one child catastrophically fails. **No ablation in the intake-level material separates "helpful average delegation" from "lucky averaging".** (to verify whether full paper covers this).
5. **ReDel infinite-delegation loop (intake-550, ENGINEERING)** — ReDel's authors specifically call out "undercommitment" failure: agents assume child agents have tools they don't, leading to infinite delegation until depth-limit triggers. Also: "overcommitment" where context-window saturation truncates the original instructions. **EPYC's `repl_executions` budget already mitigates overcommitment; the undercommitment loop is a new failure mode to watch for after any ReDel integration.**
6. **Kimi K2 OOLONG: depth-0 BEATS depth-1 (intake-547, COUNTERINTUITIVE)** — for Kimi K2 specifically, vanilla long-context inference (86.6%) beats depth-1 RLM (60.0%). **Direction-of-effect is model-dependent — RLM is not a universal accuracy lift.** Hidden assumption in the RLM paper (intake-153) is that the base model is depth-0-weak; for sufficiently long-context-capable models, RLM is a regression.
7. **Tool-call repetition with no loop detection (intake-550)** — ReDel's event-stream logger flags this but does not auto-suppress. EPYC's `_repl_turn_token_cap` is the existing mitigation.
8. **No native depth-controller in any of these papers** — Context-Folding (intake-154) gets closest with FoldGRPO process rewards, but does not formalize stop-decision separately. **The "learned depth controller" is genuinely net-new territory if EPYC chose to pursue it.**

## Concrete Spike Proposal

Three sequenced steps with explicit gating. The pattern intentionally mirrors `halo-trace-loop-spike.md`'s gate-style structure (Day 1 pre-flight, Day 1 PM falsification, conditional Day 2+).

### Step 1 (smallest) — ReDel pre-flight gate, 1 day, ~$0 compute

**Goal**: prove `kani` + `ReDel` can connect to EPYC's llama-server, drive a `DelegateOne` call against `worker_general` (gemma4-26B-A4B Q4 MTP), and return a non-empty result.

```bash
# In a throwaway venv (NOT in /workspace tree)
python3.11 -m venv /tmp/redel-spike && source /tmp/redel-spike/bin/activate
pip install "redel[all] @ git+https://github.com/zhudotexe/redel.git@main"
# Point kani at our llama-server
export OPENAI_API_KEY=local
export OPENAI_BASE_URL=http://localhost:<worker_general_port>/v1
python -c "
from kani.engines.openai import OpenAIEngine
from redel import ReDel
import asyncio
engine = OpenAIEngine(model='worker_general', temperature=0.7)
ai = ReDel(root_engine=engine, delegate_engine=engine, title='spike')
async def main():
    async for ev in ai.query('What is 2+2? Delegate the answer to a sub-agent.'):
        print(ev)
asyncio.run(main())
"
```

**Gate criteria** (≥3 of 4 must pass):
1. ReDel installs cleanly under Python ≥3.10.
2. `kani.engines.openai.OpenAIEngine` accepts the local `OPENAI_BASE_URL`.
3. `DelegateOne` triggers a non-empty child response from llama-server.
4. The event stream yields ≥1 `DelegationEvent` per child spawn.

**Estimated dev cost**: 20 LoC of glue, 2-4 hours including troubleshooting.
**Estimated compute cost**: <100K tokens against local llama-server (zero $).
**Success criteria for Step 2**: ≥3/4 gates pass AND the event stream is JSON-serializable.

### Step 2 (medium) — Single-call A/B: ReDel `DelegateWait` vs current `repl_executor`, 1 person-week, ~10 CPU-hours

**Goal**: run a paired A/B on a fixed RLM-style workload (10 OOLONG-equivalent samples drawn from existing autopilot eval-tower benchmarks) comparing:
- **Arm A**: current `epyc-orchestrator/src/api/routes/chat_pipeline/repl_executor.py` delegation surface.
- **Arm B**: ReDel `DelegateWait`-driven delegation, with EPYC's existing budget guards (`_repl_turn_token_cap`, `repl_executions`, depth=1 cap) wrapped around it.

Telemetry to capture per call:
- Sub-decision tag (from intake-548 taxonomy) — emitted as a custom event in arm B; reconstructed from log heuristics in arm A.
- Wallclock per call, tokens-in, tokens-out.
- Accuracy on the 10-sample workload (binary).
- Number of delegation events; max depth reached.

**Gate criteria** (any 1 must pass to escalate to Step 3):
1. ReDel arm shows ≥10% wallclock improvement on parallel delegation (`asyncio.gather` working as advertised).
2. ReDel arm shows event-stream taxonomy is rich enough to drive autopilot trace summarisation without further parsing.
3. ReDel arm shows ≤0 regression on accuracy.

**Estimated dev cost**: ~200 LoC (ReDel adapter, 5-sub-decision event emitter, A/B harness, telemetry exporter); ~1 person-week.
**Estimated compute cost**: 10 OOLONG samples × 2 arms × depth-1 RLM cost ≈ 60-90 minutes wall against local llama-server (per the Wang reproduction's ~89s/sample at depth-1 number). ~3-5 CPU-hours total including warm-up + replays.
**Success criteria for Step 3**: ≥1 gate passes AND the implementation is small enough to land into `epyc-orchestrator` behind a feature flag.

### Step 3 (full) — Replace `repl_executor` delegation surface with ReDel + 5-sub-decision tagging, 3-4 person-weeks, ongoing operational cost

**Goal**: land ReDel as the delegation substrate inside `epyc-orchestrator`, behind a feature flag `RLM_USE_REDEL=1` (mirrors `ORCHESTRATOR_ROLE_AWARE_ROUTING` precedent from `tri-role-coordinator-architecture.md`). Wire the 5-sub-decision taxonomy into the episodic memory schema. Connect to HALO-2 converter (per `halo-trace-loop-spike.md`) so traces export to OpenInference with sub-decision attributes.

Phased rollout (NOT exhaustive — designed for the spike proposal slot only):
- **Phase A** (1 person-week): Adapter behind feature flag. Both code paths coexist; flag OFF by default. Telemetry on both for paired comparison.
- **Phase B** (1 person-week): Schema migration — add `orchestration_subdecision TEXT` column to `episodic_store.py memories` table (idempotent ALTER, mirroring TR-2.2 precedent). Backfill heuristic for legacy rows.
- **Phase C** (1-2 person-weeks): A/B at scale across autopilot trial set (≥N=200). Decision gate: Δ ≥ +5% wallclock OR ≥+2 points accuracy on at least one benchmark with no regression > −1 point. If pass, flip default ON. If fail, keep flag, document negative result, close out.

**Estimated dev cost**: ~800-1200 LoC across `epyc-orchestrator/src/api/routes/chat_pipeline/`, `src/classifiers/`, `orchestration/repl_memory/episodic_store.py`, plus tests.
**Estimated compute cost**: A/B at N=200 per arm = roughly 200 × 2 × (avg autopilot trial cost). At current 30B-A3B Q4 throughput plus depth-1 RLM overhead, conservative estimate is 50-80 CPU-hours total.
**Success criteria**: A/B promotes the ReDel path OR the negative result is published in a follow-up handoff with concrete reasoning (matches the `tri-role-coordinator-architecture.md` TR-5 pattern).

**RAO training itself is NOT in this proposal.** Per `project_dgx_spark_target`, training is gated by hardware EPYC does not currently have. The spike sets the substrate up so that, when DGX Spark lands, an RAO-style learned head can be added with minimal substrate change. Until then, the 5-sub-decision tag enables every existing autopilot run to contribute observational data toward whichever learned policy lands first.

## Revised EPYC Priority

Reassessment after the deep-dive (vs original intake-level priorities):

- **intake-536 (RAO)**: original `new_opportunity`. **Revised: `new_opportunity, deferred`** — training-side is hardware-blocked until DGX Spark; meaningful EPYC work is the substrate, not the training recipe. The training recipe is well-documented enough to re-evaluate immediately upon DGX Spark acquisition.
- **intake-547 (RLM-Repro)**: original `worth_investigating`. **Revised: `adopt_findings, no_implementation`** — the empirical findings (depth-1 default; Kimi K2 OOLONG inversion; 96× wallclock cliff) are now the operational baseline for EPYC RLM work. No code to write; treat as posture-setting evidence.
- **intake-548 (Survey)**: original `worth_investigating`. **Revised: `adopt_taxonomy`** — the 5-sub-decision schema should be wired into the EPYC trace store as the canonical labelling axis. This is concrete, ~50 LoC.
- **intake-549 (Tree-GRPO)**: original `worth_investigating`. **Revised: `tag_only_until_hardware`** — same blocker as RAO; methodological alternative tagged in `decision-aware-routing.md` for future revisit.
- **intake-550 (ReDel)**: original `worth_investigating`. **Revised: `adopt_substrate, spike_now`** — this is the highest-leverage actionable item. License + activity + code size + backend compat all check out. The spike proposal above is the path.
- **intake-541 (X-post)**: original `worth_investigating`. **Revised: `reference_only`** — pedagogical asset; no further work needed.
- **intake-537 (TDS blog)**: original `already_integrated`. **No change.**

**Cluster-level priority verdict**: this cluster yields ONE production-track action (ReDel substrate spike), ONE research-data action (taxonomy wiring), and one deferred-by-hardware (RAO/Tree-GRPO training). The RLM side that the user flagged as under-weighted gains a clearer empirical floor (the Wang reproduction) and a clearer integration path (ReDel) — both of which strengthen `repl-turn-efficiency.md` and `01-fast-rlm-budget-controls.md`'s existing posture rather than overturning it.

## Open Questions for User

1. **Is the ReDel Commons Clause acceptable?** It does not block research use but would block any future "EPYC-as-a-service" offering. Confirm research-only use is the operating model.
2. **Are we willing to fork `kani` (or use it as-is) to add custom event types for the 5-sub-decision taxonomy?** ReDel's `events.py` is small (2.9 KB); adding a `SubDecisionTag` event is ~20 LoC but it lives in our dependency layer.
3. **What is the relationship between the per-call role axis (Trinity, in `tri-role-coordinator-architecture.md`) and the orchestration-trace sub-decision axis?** I treated them as orthogonal in Table A above (role = WHAT, sub-decision = WHERE). Confirm or revise. If orthogonal, the episodic store grows by two columns (`assigned_role` already in TR-2.1; add `orchestration_subdecision`). If not orthogonal, one collapses into the other.
4. **Acceptable to spike with API models initially (e.g., gpt-5-mini for the LLM-judge step if we ever try a mini-RAO replication)?** Or must everything stay local-only? Memory `feedback_opensource_only` says self-hosted only — but the reward-model judge in RAO is conceptually replaceable with a local 30B-class model; need confirmation that "self-hosted" extends to reward signals.
5. **Should this deep-dive promote to a handoff (`rao-redel-substrate-spike.md`)?** Per `feedback_handoff_driven_tracking`, multi-phase work must be persisted to a handoff. The 3-step spike proposal in this document is exactly that shape. Recommend: yes, with a stub linking back here. Per CLAUDE.md "Agents & Automation" rule, the handoff stub creation needs explicit user approval — flagging here rather than acting.

## References

### Intake entries
- `/workspace/research/intake_index.yaml` lines 23919–24008 (intake-536, RAO).
- `/workspace/research/intake_index.yaml` lines 24009–24064 (intake-537, TDS blog).
- `/workspace/research/intake_index.yaml` lines 24269–24333 (intake-541, X-post).
- `/workspace/research/intake_index.yaml` lines 24675–24728 (intake-547, RLM-Repro).
- `/workspace/research/intake_index.yaml` lines 24729–24786 (intake-548, Survey).
- `/workspace/research/intake_index.yaml` lines 24787–24843 (intake-549, Tree-GRPO).
- `/workspace/research/intake_index.yaml` lines 24844–24899 (intake-550, ReDel).
- `/workspace/research/intake_index.yaml` lines 3234–3286 (intake-153, RLM canonical).

### Papers
- arxiv:2605.06639 — Gandhi/Chakraborty/Wang/Kumar/Neubig, "Recursive Agent Optimization", https://arxiv.org/abs/2605.06639
- arxiv:2603.02615 — Daren Wang, "Think, But Don't Overthink: Reproducing Recursive Language Models", https://arxiv.org/abs/2603.02615
- arxiv:2605.02801 — Chenchen Zhang, "RL for LLM-based MAS through Orchestration Traces", https://arxiv.org/abs/2605.02801
- arxiv:2509.21240 — Ji et al, "Tree Search for LLM Agent Reinforcement Learning (Tree-GRPO)", https://arxiv.org/abs/2509.21240
- arxiv:2408.02248 — Zhu/Dugan/Callison-Burch, "ReDel: A Toolkit for LLM-Powered Recursive Multi-Agent Systems", EMNLP 2024 Demos, https://arxiv.org/abs/2408.02248
- arxiv:2512.24601 — Zhang/Kraska/Khattab, "Recursive Language Models" (canonical RLM, anchor for this cluster), https://arxiv.org/abs/2512.24601

### Repositories
- github.com/zhudotexe/redel — MIT + Commons Clause, Python 3.10+, 93 stars, last push 2026-05-11. Top-level structure: `redel/` (package, 98.9 KB Python including `delegation/_base.py`, `delegate_one.py`, `delegate_and_wait.py`, `events.py`, `eventlogger.py`, `app.py`), `server.py`, `terminal.py`, `viz/` (Vue/TS), `docs/`, `sandbox/`. `pyproject.toml` declares minimal core deps; web extra ships FastAPI/uvicorn/websockets.
- github.com/AMAP-ML/Tree-GRPO — Apache-2.0, 355 stars, last push 2026-01-26, 5.3 MB.
- github.com/avbiswas/fast-rlm — already referenced from `handoffs/completed/01-fast-rlm-budget-controls.md`.

### EPYC handoffs (cross-referenced)
- `/workspace/handoffs/active/meta-harness-optimization.md` (lines 419–438 — existing RAO subsection).
- `/workspace/handoffs/active/halo-trace-loop-spike.md` (HALO-2 converter touchpoint).
- `/workspace/handoffs/active/tri-role-coordinator-architecture.md` (TR-1 taxonomy intersect).
- `/workspace/handoffs/active/outer-coordinator-learned-head.md` (OC-0.3 fitness signal).
- `/workspace/handoffs/active/hermes-outer-shell.md` (lines 400–406 — existing RAO subsection).
- `/workspace/handoffs/active/repl-turn-efficiency.md`.
- `/workspace/handoffs/active/context-folding-progressive.md`.
- `/workspace/handoffs/completed/01-fast-rlm-budget-controls.md`.
- `/workspace/handoffs/completed/rlm-orchestrator-roadmap.md`.

### EPYC code touchpoints (for spike Step 3)
- `epyc-orchestrator/src/api/routes/chat_pipeline/repl_executor.py` — current delegation surface to replace/wrap.
- `epyc-orchestrator/src/graph/helpers.py` — `_repl_turn_token_cap`, `_frontdoor_repl_non_tool_token_cap`.
- `epyc-orchestrator/src/graph/state.py` — `repl_executions`, `aggregate_tokens` counters.
- `epyc-orchestrator/orchestration/repl_memory/episodic_store.py` — schema migration target.
- `epyc-orchestrator/src/classifiers/role_taxonomy.py` — precedent for adding a `subdecision_taxonomy.py` sibling.
- `epyc-orchestrator/src/features.py` — feature-flag home (`RLM_USE_REDEL`).

### Memories invoked
- `project_slot_promotion_shelved` — speculative-decoding dispatcher shelved; reminds us a similarly speculative routing rewrite needs strong A/B evidence before promotion. The 3-step spike pattern above is the methodology.
- `project_dgx_spark_target` — RAO/Tree-GRPO training blocked until DGX Spark.
- `feedback_no_concurrent_inference` — no benches without per-run approval; Step 1 pre-flight should request approval before running.
- `feedback_handoff_driven_tracking` — multi-phase work persists to handoffs; recommendation under Open Question 5.
- `feedback_audit_parallel_agent_first` — before any spike, audit recent autopilot state via progress logs / commits / handoff updates.
- `feedback_opensource_only` — local-only constraint; informs Open Question 4.
