# CF-HF-1 official HarnessFactory source comparison

Read-only source review, no code execution, vendoring, inference, or canonical writes. Source pin is JIT-Agent repository `bingreeky/JIT` commit `ababa06c2f54d799fd9fbc356e5368f61a452260` (resolved with `git ls-remote` then fetched as a sparse private clone). The reviewed files are `harness_factory/README.md`, all 11 `harness_factory/descriptions/*.md`, all 11 `harness_factory/harnesses/<name>/{memory,planning,action,tool_policy}.py` implementations and `scripts/kernel/protocols.py`.

Private source checkout: `/mnt/raid0/llm/tmp/ni08-equation-designs-20261006/jit-readonly`. Raw-file SHA-256 manifest: `/mnt/raid0/llm/tmp/ni08-equation-designs-20261006/jit-source-sha256.manifest` (92 files including README, LICENSE, kernel protocols, seed-bank descriptions and harness files); manifest digest `2d631a71c46dc310032f204d8d7af8155c06209489f4627439810355035a1122`.

## What is actually shared

The official README calls `harness_factory/` a seed bank of hand-written complete harnesses under a shared protocol and says it contains 11 architectures. It specifies each implementation has `memory.py`, `planning.py`, `action.py`, `tool_policy.py`, `prompt.yaml`, and metadata; code is copied to a workspace by the runner, not imported in-place during a normal run. `scripts/kernel/protocols.py` confirms four common abstract contracts: memory (`initialize`, `build_context`, `update`, `update_plan`, `update_summary`), planning (`init_plan`, `should_replan`, `update_plan`, `get_directive`), action (`run` owns the loop), and tool policy (`initialize`, `select_tools`, optional skills prompt). All 11 export the same `MemoryStrategy`, `PlanningStrategy`, `ActionStrategy`, `ToolPolicyStrategy` class names. Shared interface here means pluggable module seams, not equal internal complexity, calls, or compute.

## The 11 implementations at that pin

| Harness | Plan/control | Memory mechanism | Action / distinguishing system behavior |
|---|---|---|---|
| `plan_and_execute` | Linear 3–7 step roadmap; periodic progress review | Full uncompressed ordered history | JSON ReAct, multiple sequential tool calls per step; no tool filtering |
| `flash_searcher` | DAG of parallel goals with sequential fallback paths | Full history | ReAct advances unresolved goals; periodic replanning; no tool filtering |
| `agentfold` | Flash-Searcher-style DAG | Explicit agent-issued contiguous-range context folds | ReAct with optional compression directive; same all-tools policy |
| `resum` | Linear roadmap | Token-budget summarization resets working context while retaining full trajectory log | ReAct; threshold-triggered summary and periodic plan review |
| `hiagent` | No-op planner | Value-based step sampling using boundaries and observation novelty; omitted-history markers | Flat ReAct with no explicit plan |
| `memobrain` | No-op planner | Reasoning-graph nodes/edges; passive recall/flush under token pressure | Marker-based ReAct; memory patch after tool calls |
| `deepagent` | No-op planner | On-demand folding into episodic, working, and tool memory | Marker protocol with one action, catalog search, and thought-fold operations |
| `gam` | Flash-Searcher DAG | Per-step abstractions in searchable pages; periodic retrieve/integrate passes | ReAct over integrated memory plus recent raw steps |
| `roma` | Atomize, recursively decompose into dependency DAG, then synthesize | Isolated subtask memories plus dependency artifacts | Recursive execution, topological scheduling, final aggregator |
| `aggagent` | No-op planner | Separate full-history memory per rollout | Four independent exploration rollouts, then an adjudicator queries trajectories/evidence with meta-tools |
| `oagent` | No-op outer planner; heterogeneous workers | Fresh full history per expert; workspace reset/isolation | Plan-and-Execute worker plus two ReAct workers, then critic selects/synthesizes |

Code-confirmed commonality: the supplied tool policies are all-tools/unfiltered baselines (the aggregator in AggAgent has its own internal meta-tools). Thus the strongest experimental contrasts in this seed bank vary planning/control flow, memory selection/compression, and action orchestration, while holding the module signatures and ordinary tool exposure broadly fixed. Any EPYC reuse should treat this as an interface-aligned design catalogue, not a claim that the algorithms or evaluation runs are equivalent. ROMA's thread-pool scheduling, OAgent's per-expert workspace resets, and AggAgent's separate rollout memories (its supplied rollout loop is sequential) are meaningful execution differences; their shared `ActionStrategy.run()` shape does not erase those differences.

## Source separation and licensing correction

CF-HF-1's target is JIT-Agent's shipped HarnessFactory seed bank, described in its own repository. At this commit the repository root `LICENSE` is MIT and explicitly says the license covers code only; benchmark data under `benchmarks/` retains third-party licensing. That supports the existing narrow phrase “MIT source reading only”; no code is copied or adapted, so no license notice was added. Official source pointers to pin in the handoff should be the [JIT-Agent HarnessFactory README](https://github.com/bingreeky/JIT/blob/ababa06c2f54d799fd9fbc356e5368f61a452260/harness_factory/README.md) and [the JIT-Agent LICENSE](https://github.com/bingreeky/JIT/blob/ababa06c2f54d799fd9fbc356e5368f61a452260/LICENSE), with commit ID above.

Do not conflate these 11 JIT adaptations with the original AgentFold/ReSum works already represented by local intake entries `intake-155#record` and `intake-157#record`. Original upstream repositories have their own source/license scope. Neither original repo was needed to compare the 11 JIT implementations. Preserve the handoff's “no claims carried” qualifier: this source review compares module seams and implementation structure only, and makes no result, quality, performance, or adoption claim.

MAIN independently reopened the source manifest against all 92 pinned Git blobs, statically verified all 44 exported class/alias seams, and sampled protocol, folding, summarization, memory, rollout and workspace code. No external module was imported or executed. Public hashes: [source manifest](../../artifacts/ni08/harnessfactory-source-survey-20261006/source-sha256.manifest), [MAIN review](../../artifacts/ni08/harnessfactory-source-survey-20261006/MAIN-source-review.json).
