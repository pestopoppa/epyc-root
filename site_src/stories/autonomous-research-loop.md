# The autonomous research loop

Most of this site documents findings. This page documents the machine that produces the findings, because the meta-story is in some ways more interesting than any single result.

The project runs a continuously-active loop that ingests new research, evaluates it against the EPYC constraints, tries the promising approaches, measures, and either deploys or closes them. The loop runs across multiple agents in parallel, persists its state, and survives restarts. On a typical week it processes 20-40 new research artifacts and runs several optimization experiments overnight. Almost nothing in the production stack as it currently exists was chosen by hand: a paper got intake-triaged, became a deep-dive when it survived triage, fed a wiki article that synthesized findings across half a dozen related papers, and eventually an experiment that either landed in production or earned a ruled-out entry.

## The shape

There are four stations and they form a cycle, not a pipeline.

Research intake is where new papers, repositories, and blog posts enter. Each item is parsed for claims, deduplicated against an index of 595+ prior items, scored for credibility (commit history, test ratio, recognized-name signals — not README quality), and triaged into one of `adopt`, `worth_investigating`, or `not_applicable`. The verdict is justified with a one-paragraph rationale and the item joins `research/intake_index.yaml`. See [Autonomous Research](../topics/autonomous-research.md).

When an item warrants more than a verdict — a new architecture, a non-obvious benchmark methodology, a falsified claim worth understanding — the next agent in the loop produces a deep-dive: three to ten pages, structured around claims, evidence, applicability to EPYC, and (where the paper makes them) falsifiable predictions. There are 105 deep-dives as of mid-2026 and they are the long-form substrate underneath everything else on this site.

Periodically the wiki compiler scans for new intake entries, deep-dives, handoffs, and progress logs that haven't yet been folded into a topic synthesis. It clusters them by taxonomy category and writes or updates `wiki/<category>.md` articles. The wiki is built to be agent-context-friendly — dense, tabular, citation-preserving — so the next intake agent has the cumulative project knowledge readily available when triaging the next paper. This site re-uses those articles as the [Topics](../topics/index.md) layer.

The fourth station is AutoPilot, which actually runs experiments. Given the production stack as a baseline, AutoPilot proposes candidate configurations (model swaps, quantization variants, NUMA layouts, KV-compression settings, speculative-decode K values), runs benchmarks for each, and maintains a Pareto archive of measured trade-offs across throughput, quality, and memory. It runs nightly when the production stack is idle, which is the same hardware. Findings either get promoted into the registry or closed as negatives. Recent work added exogenous-restart resilience: AutoPilot now distinguishes "operator killed the server" from "the config crashed it" via fleet markers and a WAL-style journal, so a manual reboot doesn't poison the archive with false-failures. See [SkillBank & Experience Distillation](../subsystems/orchestrator/15-skillbank-experience-distillation.md).

## What makes it a loop, not a checklist

Three feedback edges close the cycle.

AutoPilot's findings feed the wiki. Every closed experiment, positive or negative, becomes a progress entry, which becomes wiki content, which becomes part of the synthesis the next intake agent sees. The system gets demonstrably smarter about *what to try next* over time because each agent has access to the cumulative findings rather than starting from a blank prior.

The wiki feeds intake. Triage is informed by what we already know — a paper proposing X gets a different read if the wiki documents X-style approaches as net-negative on CPU, and the credibility scoring is calibrated against what we've seen. Authors whose previous claims didn't replicate get appropriately downgraded.

And production telemetry feeds AutoPilot. The [MemRL System](../subsystems/orchestrator/07-memrl-system.md) records every routing decision and its outcome; AutoPilot uses that telemetry to identify configurations that look good on bench but underperform in production. That's the gap that broke the worker_general swap until the OMP idle-spin fix landed — see [Worker_general: 17 → 76 t/s](worker-general-story.md).

## What it costs

AutoPilot runs about six nights a week, four to six hours each, on the production machine while the production machine is otherwise idle. Marginal cost is electricity. The accumulated text — 595 intake entries, 105 deep-dives, ~30 wiki articles, ~60 days of progress logs — is maybe 50 MB of markdown. Human attention is the binding resource: roughly 10-15 % of new intake items need a human verdict because the agent flags them as ambiguous, and a randomized 5 % of the rest get audited.

The loop has failed in interesting ways. Intake agents have produced false-negative dismissals — papers marked `not_applicable` that, on second look, had a creative deployment we missed. AutoPilot has occasionally poisoned its Pareto archive by treating host-throttle issues as if they were regressions in the config under test. Both classes of failure are recoverable, but only because the audit trail (`agent_log.sh`) and the project's accumulated memory of past mistakes (the `feedback_*` notes in the orchestrator's memory store) let us trace them. The compounding lesson: agent-driven workflows accumulate process debt the same way code does, and the remediations are themselves part of the loop now.

## Is it actually working

The honest answer is that we don't have a clean control experiment. What we have is a comparison of throughput before and after each piece of the pipeline landed:

| Period | Intake throughput | Experiments closed | Production stack changes |
|---|---:|---:|---:|
| 2026-02 (manual only) | ~5 / wk | 0 systematic | 0 |
| 2026-03 (intake online) | ~20 / wk | ~2 / wk | 3 model swaps, 5 config changes |
| 2026-04 (AutoPilot online) | ~25 / wk | ~10 / wk | 8 model swaps, 14 config changes |
| 2026-05 (full loop closed) | ~30 / wk | ~12 / wk | 11 model swaps, ~30 config changes |

These numbers don't correct for what was easy versus hard, but the direction is unambiguous: each closure step unlocked downstream throughput that wasn't accessible before.

The deeper bet the loop is meant to validate is that for a single-operator infrastructure project, an autonomous research-ingestion and experimentation loop produces meaningfully more results per unit of human attention than the same operator working alone. This page is part of the evidence for that bet. The [topic articles](../topics/index.md), the [deep-dives](../deep-dives/index.md), and the [ruled-out](ruled-out.md) page are the rest.

The loop only works because the production stack is the same hardware the experiments run on, the same registry the optimizations target, and the same orchestrator the routing-decision telemetry comes from. Decoupling research from production — the common pattern at larger organizations — would break most of the feedback edges and most of the speed.
