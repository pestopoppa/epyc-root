# RAO + ReDel Substrate Spike

**Status**: ready-to-claim (3-step spike, Step 1 = 1 day, Step 2 = 1 person-week, Step 3 = conditional)
**Created**: 2026-05-19 (post-cluster-deep-dive)
**Categories**: agent_architecture, autonomous_research, tool_implementation
**Priority**: HIGH (substrate enables all future RAO/RLM/Tree-GRPO work)
**Depends on**: `meta-harness-optimization.md`, `repl-turn-efficiency.md`, `halo-trace-loop-spike.md`
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-rao-rlm-cluster.md`](../../research/deep-dives/2026-05-19-rao-rlm-cluster.md)

## Objective

Validate whether `ReDel` (intake-550, MIT + Commons Clause, `github.com/zhudotexe/redel`, last push 2026-05-11) is the right substrate for EPYC's recursive-agent harness work — replacing in-house build of the asyncio + REPL + delegate-as-tool scaffolding that RAO (intake-536), RLM (intake-153), and Tree-GRPO (intake-549) all presume.

If ReDel passes the pre-flight gate, lift its delegation primitives (`DelegateOne` blocking, `DelegateWait` non-blocking with `asyncio.gather`), event-stream logger, and web debugger into our orchestrator stack rather than rebuilding from scratch.

If it fails, fall back to in-house design per `meta-harness-optimization.md` Tier 3.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-536 | RAO — Recursive Agent Optimization (arxiv:2605.06639) | high | new_opportunity (training-side; hardware-blocked) |
| intake-541 | @neural_avb X-post RAO breakdown | high | worth_investigating (teaching asset) |
| intake-547 | Wang RLM reproduction (arxiv:2603.02615) | high | worth_investigating (depth caveat — **load-bearing**) |
| intake-548 | Orchestration-trace survey (arxiv:2605.02801) | high | worth_investigating (5-sub-decision taxonomy) |
| intake-549 | Tree-GRPO (arxiv:2509.21240, ICLR 2026) | medium | worth_investigating (methodological alt) |
| intake-550 | ReDel toolkit (arxiv:2408.02248, EMNLP 2024 Demos) | high | worth_investigating (substrate candidate — **focus of this spike**) |
| intake-537 | TDS RLM deep-dive blog (Avishek Biswas) | high | already_integrated |
| intake-153 | RLM canonical paper (Zhang/Kraska/Khattab arxiv:2512.24601) | high | already_integrated (~80% pattern coverage) |

## Key Findings from Deep-Dive

- **ReDel substrate**: MIT + Commons Clause license (research use OK; resale blocked), 98.9 KB Python core, Python 3.10+, built on `kani`, **swappable to local llama-server via `OPENAI_BASE_URL` env var** — drops onto our stack with zero llama.cpp changes.
- **Wang reproduction caveat** (intake-547): on **Kimi K2 OOLONG, depth-0 (86.6%) BEATS depth-1 RLM (60.0%)**. Direction-of-effect is model-dependent. Depth=2 DeepSeek v3.2 S-NIAH inflates wall-clock 96× (3.6s → 89.3s → 344.5s). **`max_depth=1` is the load-bearing default for any RAO/RLM-style integration on EPYC.**
- **Stopping-decision gap** (intake-548): no published RL method as of May 2026 explicitly trains the stopping decision. On CPU EPYC where every token is BW-expensive, a learned stop policy has more differential value than anywhere else. The 5-sub-decision taxonomy `{when-to-spawn, whom-to-delegate, how-to-communicate, how-to-aggregate, when-to-stop}` should be wired into the episodic store as a labelling axis (~50 LoC, mirrors `tri-role-coordinator-architecture.md` TR-2.2's `assigned_role` precedent).
- **RAO training is hardware-blocked** (`project_dgx_spark_target` — DGX Spark not yet acquired). The substrate spike prepares the ground so whichever learned policy arrives first can land with minimal substrate change.

## Spike Plan (3 steps, gated)

### Step 1 — ReDel pre-flight gate (1 day, ~$0 compute)

**Goal**: prove ReDel + `kani` can connect to EPYC's llama-server, drive a `DelegateOne` call against `worker_general` (gemma4-26B-A4B Q4_K_M MTP), and return a non-empty result.

```bash
# In a throwaway venv (NOT in /workspace tree)
python3.11 -m venv /tmp/redel-spike && source /tmp/redel-spike/bin/activate
pip install "redel[all] @ git+https://github.com/zhudotexe/redel.git@main"
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
**Estimated compute cost**: <100 K tokens against local llama-server (zero $).
**Success criteria for Step 2**: ≥3/4 gates pass AND the event stream is JSON-serializable.

### Step 2 — Paired A/B vs current `repl_executor` (1 person-week, ~10 CPU-hours)

**Goal**: paired A/B on a fixed RLM-style workload (10 OOLONG-equivalent samples drawn from existing autopilot eval-tower benchmarks) comparing:
- **A**: current in-house `repl_executor` recursive harness (`max_depth=1`)
- **B**: ReDel `DelegateWait` with `asyncio.gather` (`max_depth=1`, mirrored config)

**Metrics**: accuracy, wall-clock, total tokens, dev complexity (LoC delta if we adopt B).

**Gate criteria**: ReDel matches or beats current harness on ≥2 of 3 numerical metrics AND adoption LoC delta ≤ 500 net additions (i.e. lift patterns; do not vendor entire dependency tree if it exceeds this).

### Step 3 — Conditional substrate replacement (2-3 person-weeks, gated on Step 2)

If Step 2 passes, draft a feature-flagged substrate replacement: ReDel-style delegation primitives + event-stream logger + 5-sub-decision-taxonomy labelling on episodic store. Default-off, A/B for 1 week against production traffic, promote on parity.

**Dev cost**: ~800-1200 LoC including tests + flag + telemetry. Targets:
- `repl-turn-efficiency.md` Tier-2 already in scope
- `unified-trace-memory-service.md` for event-stream persistence
- `tri-role-coordinator-architecture.md` TR-2.2 for the 5-sub-decision labelling

## Non-Goals for This Spike

- **RAO training itself**: hardware-blocked. The training recipe (mean-of-children + LOO + depth-IF) is reproducible-from-paper but should be deferred until GPU compute lands (`project_dgx_spark_target`).
- **Tree-GRPO** (intake-549): same training-blocker as RAO. Track methodologically; do not implement.
- **Vendoring ReDel**: do NOT add ReDel as a runtime dependency. Lift the *patterns* (delegation primitives, event stream, debugger). Per `feedback_minimum_imports`.

## Failure Modes to Watch

- **Infinite-delegation loops**: ReDel-class harnesses can spawn until `max_depth` cap without making progress. Implement loop detection on tool-call repetition.
- **Reward hacking via LLM-judge proxies**: if/when we ever train a delegation policy, the per-node LLM-judge reward (RAO's design) is exactly the proxy-reward attack surface. Counter-measure: per-child (not mean) failure tracking + judge-output sanity audit.
- **Mean-of-children masking catastrophic child failure**: RAO's mean-aggregation reward biases the parent toward over-delegating easy splits. Counter-measure: report MIN-child-success alongside mean during evaluation.

## Open Questions for User

1. **Substrate scope**: pure pattern-lift (in-house re-implementation drawing from ReDel design) vs hybrid (vendor `kani` for the engine surface, in-house everything else) vs full vendor (`pip install redel[all]`)? Pattern-lift is the `feedback_minimum_imports`-aligned default.
2. **Stopping-policy research direction**: should Step 3 explicitly include a learned-stop-policy experiment (intake-548 gap as a research target), or stay focused on substrate replacement only?
3. **Trace store extension**: the 5-sub-decision taxonomy labelling needs a column on episodic store events. OK to add to `unified-trace-memory-service.md` schema?

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-rao-rlm-cluster.md`
- ReDel repo: `https://github.com/zhudotexe/redel`
- RAO paper: `https://arxiv.org/abs/2605.06639`
- Wang RLM reproduction: `https://arxiv.org/abs/2603.02615`
- Orchestration-trace survey: `https://arxiv.org/abs/2605.02801`
- Tree-GRPO: `https://arxiv.org/abs/2509.21240`
- Related handoffs: `meta-harness-optimization.md`, `halo-trace-loop-spike.md`, `repl-turn-efficiency.md`, `tri-role-coordinator-architecture.md`, `unified-trace-memory-service.md`
