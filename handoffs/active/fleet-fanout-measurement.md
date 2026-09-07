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
| intake-1111#record | OrchBench (arxiv:2607.25656) | high | dive-overturned — requires per-node durations as INPUT, but Appendix D-I's real-side metric definitions (declared/started/completed agents, parallel utilization, workflow depth) are a ready spec |
| intake-1109 | Single-Agent vs MAS at Equal Token Budgets (arxiv:2604.02460) | high | dive-verified — Appendix B four-bucket breadth-vs-synthesis diagnostic |
| intake-1127 | AdaMAST (arxiv:2607.16387) | high | dive-verified, adopt_component — Apache-2.0 trace grader, no success/failure oracle required |
| intake-1110#00 | MAST (arxiv:2503.13657) | medium | dive-overturned — 14-mode taxonomy, FC1/FC3 transfer to our topology, FC2 largely does not |

Related existing work (do NOT duplicate):
- [`session-bus-thin-dispatcher.md`](session-bus-thin-dispatcher.md) — owns the C36 substrate this collector builds on: per-backend transcript mechanics (Codex `thread_source`, Claude subagents in-process via `claude agents --json`), and the standing rule that **CPU delta is an invalid proxy** for subagent activity.
- [`coordinator-role-failure-modes-and-refactor.md`](coordinator-role-failure-modes-and-refactor.md) — F-15 (fan-out doctrine), R-17/R-23 (thread-attribution premise), the F-series failure ledger this stub's grading output would cross-walk against.
- [`repl-turn-efficiency.md`](repl-turn-efficiency.md) — S4 Omega A/B, the metric this collector's data would feed.

## Corpus, verified on disk 2026-08-13

- **Claude Code**: ~1,843 JSONL under `~/.claude/projects/-workspace/<session>/` (1,611 in `subagents/`, 232 session files). Fields: `agentId`, `parentUuid`, `isSidechain`, `uuid`, `timestamp`, `sessionId`, `promptId`, `message`, `toolUseResult`.
- **Codex**: ~4,422 rollout files under `~/.codex/sessions/YYYY/MM/DD/`. First record `session_meta` carries `payload.source.subagent.thread_spawn.{parent_thread_id, depth, agent_role}`; every record timestamped.
- `scripts/coordination/tmux_adapter.py:1376-1441` already opens both formats and parses the subagent structure — currently only for a boolean liveness check, discarding the timing.

## Tasks

- [x] **FM-1 — Per-subagent timing collector.** ✅ 2026-08-23 — `scripts/coordination/fanout_timing.py`
  (collect-claude / collect-codex / merge, schema `fanout_timing.v1`), tests in
  `tests/coordination/test_fanout_timing.py` (14 passed), corpus run in
  `data/fanout_timing/` (2428 workflows, 4727 subagents; 52 workflows with >=2 overlapping
  subagents holding 3847 subagents; mean depth 1.38, max 4; 54 workflows joined to queue.jsonl).
  Extract per-subagent start/finish timestamps from Claude Code and Codex transcripts into a durable record. Spec: OrchBench Appendix D-I real-side metric
  definitions — Declared/Started/Completed Agents, Parallel Utilization (`Σ subagent active time ÷ (max
  overlapping subagents × total workflow span)`), Workflow Depth. Do NOT infer edges by keyword-matching
  between subagent outputs (OrchBench's own weak proxy for this) — our Task/SendMessage records carry
  real parent→child edges; use those. Output should be joinable against `queue.jsonl` task IDs for a
  fleet-level view.
- [x] **FM-5 — Per-subagent OUTCOME accounting (intake-1304; 2026-09-07).** ✅ 2026-09-07 — see the RESULT block below the FM-6 row; read the bounds before quoting any number. Extend the FM-1
  collector with an outcome bucket per subagent — `produced-and-used` / `produced-and-discarded` /
  `no-output` / `blocked` / `aborted` — and a token total per bucket, over the existing
  `data/fanout_timing/` corpus (2428 workflows, 4727 subagents). **Target metric: the share of
  fan-out tokens spent on subagents whose work was never used.** Comparator, from the only published
  per-outcome accounting of a large agent swarm: 80.2% of tokens went to non-merged runs and 51.6%
  to Aborted alone, and that paper's own remediation list projects a 3–10× cost reduction from
  fixing orchestration without better models. **This is a strictly WEAKER oracle than FM-4 and does
  NOT block on it** — "was the output used" is derivable from the parent's subsequent tool calls and
  git diff, and needs no task-success verdict. That is the whole reason to do it first.
- [x] **FM-6 — Reconnection requirement (intake-1299; 2026-09-07).** ✅ 2026-09-07 — orphan rate 35.0%; declared width 1,187 -> measured 928 (-21.8%). A fan-out record counts only if
  each subagent's output is linked to a backlog row or an artifact path; unlinked output is reported
  as `orphan` and excluded from the measured fan-out width. Adapted from Prove2Me's rule that work
  which does not reconnect to the mission decomposition earns no credit at all. Note the direct
  bearing on this handoff's own premise: an orphan-blind width count cannot distinguish a main that
  dispatched five subagents usefully from one that dispatched five and used none.

### FM-5 / FM-6 RESULT — 2026-09-07, and the bounds are part of the result

`scripts/coordination/fanout_timing.py` at schema `fanout_timing.v2` (a strict superset of v1;
v1 rows are counted as `schema_v1_no_outcome` and never folded into a bucket). Tests:
`tests/coordination/test_fanout_timing.py`, 14 -> 58, every positive paired with a mutation that
removes exactly the signal under test. Corpus: `data/fanout_timing/*.v2.jsonl` +
`outcome-report.v2.json`, **4,278 subagents over 14,004 workflows**.

| bucket | n | share of known | share of tokens |
|---|---|---|---|
| produced-and-used | 2,265 | 60.0% | 13.5% |
| produced-and-discarded | 1,281 | 33.9% | 79.7% |
| no-output | 122 | 3.2% | ~0% |
| aborted | 109 | 2.9% | 6.8% |
| blocked | 0 | 0.0% | 0.0% |
| *unknown* | *501* | *excluded* | *excluded* |

**HEADLINE, stated with its unit and its direction of error** (per the unit-of-work amendment
ratified today in `MEASUREMENT_POLICY.md`): over the **3,777 subagents whose outcome is known**,
**>= 86.5% of processed tokens and >= 83.8% of new tokens went to work never used**; by **head
count** the same figure is **>= 40.0%**. These are LOWER bounds on waste, because the `used` side
is the loose side of the oracle.

**Why the two units disagree by 46 points, which is itself the finding:** discarded subagents are
the token-heavy ones. Cost does not track head count here, so a width-based cost argument measures
the wrong thing — which is exactly what the ratified discarded-work clause says.

**Bounds you must carry when citing this:**
- **`produced-and-used` is an UPPER bound.** 2,094 of its 2,265 verdicts rest on `parent-reference`
  (a substring hit in a later parent record), which over-fires for a subagent citing a hot path.
  The **strict floor of PROVEN reuse is `git-landed` = 171 = 4.5% of known subagents.** So
  head-count waste sits in a wide band: **>= 40.0%, and <= 95.5%** if only proof counts.
- **`blocked` = 0 is a floor, not a finding.** Neither transcript format carries a blocked marker;
  only a narrow API-error tail is detectable. A subagent that reported a blocker in prose is
  sitting in `produced-and-discarded`.
- **Token totals are provider-cumulative and skewed** (Codex p50 1.27 M, p90 1.68 B): the token
  share is a statement about a handful of very long threads. The head-count figure is not.
- **501 `unknown`** (all Codex, parent rollout exceeded the 512 MB reuse-index cap) are reported
  separately and folded into nothing. They hold 0.1% of tokens.
- **Codex `written_paths` is a lower bound** (only `apply_patch` headers parsed), so the 38.0%
  Codex orphan rate is an upper bound.
- **The corpus is NOT reproducible.** Claude transcripts have been pruned since the v1 snapshot
  (1,546 -> 1,078 subagents) and the Codex corpus grew (2,344 -> 13,942 workflows). The v2 artifacts
  are committed *because* of this: a measurement whose corpus no longer exists is unfalsifiable.

**Comparator, for context only:** the external swarm reported 80.2% of tokens to non-merged runs
and 51.6% to aborted alone. **Our aborted share is 6.8% — an order of magnitude lower — and our
loss is concentrated in DISCARDED, not aborted.** Different failure, different remedy: their fix is
crash-loop repair, ours would be reconnection.

**Do NOT read this wave as an argument to narrow the 3–5 fan-out width.** The evidence points the
other way: in the one study that varied workers-per-task (1/3/5, intake-1305), the 3- and 5-worker
arms beat 1 worker on **both** wall-clock and token cost at matched completion, and the central
coordination tier was only ~11% of compute. The cost driver these sources identify is discarded
work, not width — which is what FM-5 measures.

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
research-intake round that produced this stub (`intake-1110#record` dive_corrections) — that figure was
overstated ~2.2×.
