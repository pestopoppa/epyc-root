# The autonomous research loop

Most of this site documents *findings*. This page documents the *machine that produces the findings* — because the meta-story is in some ways more interesting than any single result.

The project runs a continuously-active loop that ingests new research, evaluates it against the EPYC constraints, tries the promising approaches, measures, and either deploys or closes them. The loop runs across multiple agents in parallel, persists its state, and survives restarts. On a typical week it processes 20–40 new research artifacts and runs several optimization experiments overnight.

## The pieces

The loop has four stations:

**1. Research intake.** New papers, repositories, and blog posts come in through a structured pipeline (the `research-intake` skill). Each item is parsed for claims, deduplicated against an existing index of 595+ prior items, scored for credibility (commit history, test ratio, recognized-name signals — not README quality), and triaged into one of three verdicts: `adopt`, `worth_investigating`, or `not_applicable`. Each verdict is justified with a one-paragraph rationale. The output lives in `research/intake_index.yaml` and the long-form analyses (for items that need depth) land as files in `research/deep-dives/`. See [Autonomous Research](../topics/autonomous-research.md).

**2. Deep-dive synthesis.** When an item warrants more than a verdict — a new architecture, a non-obvious benchmark methodology, a falsified claim worth understanding — we produce a deep-dive (~3-10 pages, structured: claims, evidence, applicability to EPYC, falsifiable predictions). 105 deep-dives exist as of mid-2026; they're the long-form substrate of the wiki.

**3. Wiki compilation.** Periodically (currently manual, eventually scheduled) the wiki compiler scans for new intake entries, deep-dives, handoffs, and progress logs that haven't been folded into the topic syntheses yet. It clusters them by taxonomy category and writes/updates `wiki/<category>.md` articles. Each article is built to be agent-context-friendly: dense, tabular, citation-preserving. This site re-uses those articles as the [Topics](../topics/index.md) layer. [Knowledge Management](../topics/knowledge-management.md).

**4. AutoPilot.** The optimization runner. Given the current production stack as a baseline, AutoPilot proposes candidate configurations (model swaps, quantization variants, NUMA layouts, KV-compression settings, speculative-decode K values), runs benchmarks for each, and maintains a Pareto archive of measured trade-offs (throughput vs. quality vs. memory). Runs nightly when the production stack is idle. Findings either get promoted into the registry or closed as negatives. Recent additions include exogenous-restart resilience — AutoPilot now distinguishes "operator killed the server" from "the config crashed it" via fleet markers + a WAL-style journal, so a manual reboot doesn't poison the archive with false-failures. See the orchestrator's [SkillBank & Experience Distillation chapter](../subsystems/orchestrator/15-skillbank-experience-distillation.md).

## What makes this a loop and not a checklist

Three feedback edges:

1. **AutoPilot findings feed the wiki.** Every closed experiment (positive or negative) becomes a progress entry, which becomes a wiki update, which becomes part of the synthesis the next intake agent sees. The system gets demonstrably smarter about *what to try next* over time, because each agent has access to the cumulative findings.

2. **Wiki findings feed intake.** Intake triage is informed by what we already know. A paper proposing X gets a different read if the wiki already documents X-style approaches as net-negative on CPU. The credibility scoring is calibrated against what we've seen — papers from authors whose previous claims didn't replicate get appropriately downgraded.

3. **Production telemetry feeds AutoPilot.** The MemRL system (see [MemRL System](../subsystems/orchestrator/07-memrl-system.md)) records every routing decision and its outcome. AutoPilot uses that telemetry to identify configurations that look good on bench but underperform in production — the kind of gap that broke the worker_general swap until we fixed the OMP env. [Worker_general: 17 → 76 t/s](worker-general-story.md).

## What it costs

The honest accounting:

- **Compute**: AutoPilot runs ~6 nights/week, ~4-6 hours each. The production machine is otherwise idle overnight so the marginal cost is electricity.
- **Storage**: 595 intake entries, 105 deep-dives, ~30 wiki articles, ~60 days of progress logs. Maybe 50 MB of markdown total.
- **Human attention**: The intake-triage step still needs occasional human judgment for items the agent flags as ambiguous. Currently ~10–15 % of new items get a human review before final verdict. The remainder are agent-only, with a randomized 5 % audit by a human reviewer.
- **Failure cases**: The loop has failed in interesting ways. Intake agents have produced false-negative dismissals ("not applicable to our hardware" — sometimes wrong, see the `feedback_dont_dismiss_creative_uses` memory). AutoPilot has occasionally poisoned its Pareto archive by treating a host-throttle issue as a config-under-test regression (the `feedback_host_throttle_check` memory is the corrective).

The compounding lesson: **agent-driven workflows accumulate process debt the same way code does**. The remediations above are themselves part of the loop now. The `agent_log.sh` audit trail is what makes diagnosing them tractable.

## The pattern we're trying to demonstrate

The deeper claim the loop is meant to validate: **for a single-operator infrastructure project, an autonomous research-ingestion + experimentation loop produces more results per unit of human attention than the same operator working alone**.

We don't have a clean control experiment. What we have is a comparison of throughput before and after each pipeline piece landed:

| Period | Intake throughput | Experiments closed | Production stack changes |
|---|---|---|---|
| 2026-02 (before intake pipeline) | ~5/wk manual | 0 systematic | 0 |
| 2026-03 (intake online) | ~20/wk | ~2/wk | 3 model swaps, 5 config changes |
| 2026-04 (autopilot online) | ~25/wk | ~10/wk | 8 model swaps, 14 config changes |
| 2026-05 (full loop closed) | ~30/wk | ~12/wk | 11 model swaps, ~30 config changes |

Those are coarse numbers and not corrected for what was easy vs. hard, but the trend is clear: each closure step in the loop unlocked downstream throughput that wasn't accessible before.

## What this story is not

It's not a claim that the loop is *good*. It's a description of what it is, with concrete numbers about cost and output. The loop has measurable blind spots — see [What we tried and ruled out](ruled-out.md) for cases where the loop *did* try things and they didn't work, and [What we're investigating now](investigating-now.md) for the cases where we don't yet know.

It's also not a claim that you can do this without the production substrate. The loop only works because the production stack is the same hardware the experiments run on, the same registry the optimizations target, and the same orchestrator the routing-decision telemetry comes from. Decoupling research from production (a common pattern at larger orgs) would break most of the feedback edges above.

## What's next on this thread

If you want to see the loop's actual artifacts: [research deep-dives](../deep-dives/index.md) is the long-form output, [Topics](../topics/index.md) is the synthesis layer, and the GitHub `handoffs/active/` directory in [epyc-root](https://github.com/pestopoppa/epyc-root/tree/main/handoffs/active) is the live work queue (not published here by design, because most of it is operationally noisy). For the optimization side specifically, [Hardware Optimization](../topics/hardware-optimization.md) and [Benchmark Methodology](../topics/benchmark-methodology.md) are the two articles that compile the most AutoPilot output.
