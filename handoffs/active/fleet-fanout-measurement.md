# Fleet Fan-Out Measurement — per-subagent timing collector + failure grading

**Status**: stub — no code landed yet.
**Created**: 2026-08-13 (via `/research-intake` Stage 3, operator-approved plan; source round intake-1105…intake-1127, PARL/Kimi-agent-swarm sweep)
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Categories**: swarm_techniques, agent_architecture, benchmark_methodology, autonomous_research

## Objective

Our fan-out doctrine (`agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*) mandates
3–5 concurrent subagents unconditionally, with no completion feedback and no way to distinguish a main
that actually fanned out from one that worked serially and reported otherwise. The open item at
`session-bus-thin-dispatcher.md:2685` names this gap directly: *"nothing on this plane distinguishes a
main that dispatched five concurrent subagents from one that did the same work on its own thread — so
the only detector is the operator saying so, which is how it ran unchallenged to 1,070 open backlog
items."* `coordinator-role-failure-modes-and-refactor.md` F-15's `Recur: 0` currently rests on that same
self-report evidence.

This stub owns the measurement side: turn the assertion into a number, using data already on disk.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-1106 | Kimi K2.5: Visual Agentic Intelligence (arxiv:2602.02276) | high | worth_investigating — names "serial collapse", supplies no instrumentation |
| intake-1111 | OrchBench (arxiv:2607.25656) | high | dive-overturned — requires per-node durations as INPUT, but Appendix D-I's real-side metric definitions (declared/started/completed agents, parallel utilization, workflow depth) are a ready spec |
| intake-1109 | Single-Agent vs MAS at Equal Token Budgets (arxiv:2604.02460) | high | dive-verified — Appendix B four-bucket breadth-vs-synthesis diagnostic |
| intake-1127 | AdaMAST (arxiv:2607.16387) | high | dive-verified, adopt_component — Apache-2.0 trace grader, no success/failure oracle required |
| intake-1110 | MAST (arxiv:2503.13657) | medium | dive-overturned — 14-mode taxonomy, FC1/FC3 transfer to our topology, FC2 largely does not |

Related existing work (do NOT duplicate):
- [`session-bus-thin-dispatcher.md`](session-bus-thin-dispatcher.md) — owns the C36 substrate this collector builds on: per-backend transcript mechanics (Codex `thread_source`, Claude subagents in-process via `claude agents --json`), and the standing rule that **CPU delta is an invalid proxy** for subagent activity.
- [`coordinator-role-failure-modes-and-refactor.md`](coordinator-role-failure-modes-and-refactor.md) — F-15 (fan-out doctrine), R-17/R-23 (thread-attribution premise), the F-series failure ledger this stub's grading output would cross-walk against.
- [`repl-turn-efficiency.md`](repl-turn-efficiency.md) — S4 Omega A/B, the metric this collector's data would feed.

## Corpus, verified on disk 2026-08-13

- **Claude Code**: ~1,843 JSONL under `~/.claude/projects/-workspace/<session>/` (1,611 in `subagents/`, 232 session files). Fields: `agentId`, `parentUuid`, `isSidechain`, `uuid`, `timestamp`, `sessionId`, `promptId`, `message`, `toolUseResult`.
- **Codex**: ~4,422 rollout files under `~/.codex/sessions/YYYY/MM/DD/`. First record `session_meta` carries `payload.source.subagent.thread_spawn.{parent_thread_id, depth, agent_role}`; every record timestamped.
- `scripts/coordination/tmux_adapter.py:1376-1441` already opens both formats and parses the subagent structure — currently only for a boolean liveness check, discarding the timing.

## Tasks

- [ ] **FM-1 — Per-subagent timing collector.** Extract per-subagent start/finish timestamps from Claude
  Code and Codex transcripts into a durable record. Spec: OrchBench Appendix D-I real-side metric
  definitions — Declared/Started/Completed Agents, Parallel Utilization (`Σ subagent active time ÷ (max
  overlapping subagents × total workflow span)`), Workflow Depth. Do NOT infer edges by keyword-matching
  between subagent outputs (OrchBench's own weak proxy for this) — our Task/SendMessage records carry
  real parent→child edges; use those. Output should be joinable against `queue.jsonl` task IDs for a
  fleet-level view.
- [ ] **FM-2 — AdaMAST fixed-catalog grading pilot.** Stage 1 (now): `adamast judge --taxonomy
  adamast/core/mast.json` over a stratified sample of Codex rollouts and Claude transcripts, one LLM
  call per trace, no oracle required — the pipeline is deliberately outcome-blind
  (`outcome_blind_trace()` strips `outcome`/`final_gate_status` before the judge ever sees a trace).
  Two small enablers first: (a) a `base_url` passthrough in `providers.py` (`SUPPORTED_PROVIDERS =
  ("openai","anthropic","google","bedrock")`, client constructed with no kwargs) to point the judge at
  a local endpoint, ~5 lines; (b) a normalizer emitting the 4-field canonical schema
  (`problem_id, task, raw_trajectory, metadata`) from Claude JSONL, carrying `agentId`/`isSidechain`/
  `parentUuid` in `metadata`; Codex is detected natively but `thread_spawn` metadata is silently
  dropped upstream and should be preserved the same way. Stage 2 (after FM-4/oracle work, separately
  scoped): `adamast generate` to induce a fleet-specific taxonomy — the paper's own evidence (induced
  vocabulary κ=0.682 vs a hand-crafted comparator at κ=0.516 on TRAIL, and mean pairwise Jaccard 0.14
  across six domains for independently induced taxonomies) argues an imported 7-framework taxonomy
  should not be expected to fit our traces as well as one induced on them. Do not trust the repo's
  built-in agreement gate (four personas of one model, Fleiss κ, no human) as validation; build a small
  human-graded set if a faithfulness number is ever needed.
- [ ] **FM-3 — Breadth-vs-synthesis diagnostic.** Apply the four-bucket split from intake-1109 Appendix
  B (fan-out-right/single-right, single-right/fan-out-wrong, both-right, both-wrong) to FM-1's output
  once paired serial/fan-out task pairs exist, to answer: does fan-out win by surfacing more candidates,
  or lose at the integration/synthesis step?
- [ ] **FM-4 — Success/failure oracle.** Blocking prerequisite for FM-2 Stage 2 and for any accuracy-side
  A/B. Derive a machine-readable per-session verdict (task exit status, gate result, git outcome) —
  neither corpus carries one today.

## Notes

Corpus counts above supersede any earlier figure of "4,087 Claude transcripts" circulating from the
research-intake round that produced this stub (`intake-1110` dive_corrections) — that figure was
overstated ~2.2×.
