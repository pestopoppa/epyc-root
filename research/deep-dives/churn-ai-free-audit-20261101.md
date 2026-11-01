# Churn pipeline: AI-free audit (2026-11-01)

Operator question, routed through ws58: which steps of the backlog churn pipeline that an LLM performs today could a deterministic script do instead, for robustness and to save tokens?
Pipeline sources: `docs/guides/agent-workflows/backlog-churn-flow.md`, `scripts/coordination/{handoff_sessions,backlog_gen,flow_scoreboard}.py`, `rowflow/`, `churn/` and `GOAL-codex-gen.md`.

## 1. Measurement

**Source.** All 703 Codex rollouts in `~/.codex/sessions/2026/11/01/`. The 76 handoff-session `exec --json` transcripts under `compute-flags/handoff-sessions/*/` have no `token_count` events. Their spend was therefore measured through the rollouts they produce, which include the sub-agents they spawn.

**Method.**
- Each `token_count.last_token_usage` is split equally across the tool calls made since the previous `token_count`.
- Each call is classified by a regex over its command text or tool name. The first match wins, in the order of the tables below.
- The script is at `/tmp/claude-1000/sp/m.py`. It is scratch, so regenerate it if needed.
- The classification is heuristic. `other_work` holds the real engineering (code edits, analysis scripts) plus every call that matched no other class.

**Rollout roles.**
- 678 rollouts were handoff sessions or their sub-agents.
- 4 were codex-gen.
- 21 were other or unlabelled.
- Claude-side ws58 subagents do not write Codex rollouts, so they were not measured.

### Handoff sessions plus sub-agents

Totals: 6.43 G input tokens (99.0% cached), 15.4 M uncached, 18.1 M output.

| Class | Input (M) | Uncached (M) | Output (k) | Turns | Share | Bookkeeping? |
|---|---:|---:|---:|---:|---:|---|
| other_work (engineering + unmatched) | 2005 | 13.9 | 4451 | 12568 | 31.2% | no |
| read_brief (BACKLOG/brief/handoff reads, grep, sed) | 1412 | 30.8 | 4007 | 11368 | 22.0% | mostly |
| monitor_wait (`wait_agent`, `list_agents`, sleep, ps/status) | 893 | 13.1 | 2710 | 6941 | 13.9% | yes |
| subagent_orch (spawn/send/followup) | 728 | 8.6 | 1701 | 5178 | 11.3% | partly |
| wrapup_mech (progress, tick, commit, push, cherry, index_state) | 412 | 5.1 | 1575 | 3103 | 6.4% | yes |
| reasoning/message-only turns | 337 | 3.3 | 685 | 2685 | 5.3% | n/a |
| spec_fix (`result_path`, spec fields, apply_patch on specs) | 334 | 2.2 | 1566 | 2134 | 5.2% | mostly |
| filing_verdict | 108 | 1.5 | 751 | 800 | 1.7% | partly |
| republish after a dry-run failure (`publish_row`, `--dry-run`) | 98 | 1.9 | 358 | 698 | 1.5% | yes |
| rebase/merge/worktree/fetch | 70 | 1.4 | 185 | 595 | 1.1% | yes |
| duplicate-notice handling | 18 | 0.3 | 125 | 98 | 0.3% | yes |

### codex-gen

Totals: 546 M input, about 1.5 M uncached, 0.23 M output, across 4 rollouts.

| Class | Share |
|---|---:|
| monitor_wait | 22.0% |
| other_work | 21.1% |
| wrapup_mech | 14.9% |
| subagent_orch | 12.8% |
| reasoning/message-only | 8.7% |
| read_brief | 7.6% |
| rebase/merge | 7.0% |
| republish | 4.8% |
| filing_verdict | 0.6% |
| spec_fix | 0.2% |

More than half of codex-gen's spend goes to waiting, wrap-up and git plumbing.

### What the numbers mean

- **Turn count drives the cost, not output.** Every turn re-reads about 100 k cached tokens of context, so removing turns is what saves tokens. Shorter outputs barely matter.
- **Pure bookkeeping is almost a quarter of handoff-session spend.** monitor_wait + wrapup_mech + republish + rebase + duplicate notices come to about 1.49 G input over 11.4 k turns, which is 23.2% of handoff-session spend. The same classes take about 38% of codex-gen's spend.
- **Most of read_brief (22%) is re-reading.** On every resume, agents re-read the regenerated `BACKLOG-handoff-<slug>.md` and their brief, then grep for their own state.

## 2. Classification of each class

The kinds are those in the brief: (a) fully mechanizable; (b) mechanizable once the agent outputs a structured decision; (c) needs judgment.

| Class | Kind | Replacement |
|---|---|---|
| monitor_wait | (a) | The dispatcher already resumes sessions on `grants/<id>.ended` or `.complete`, so agents should stop polling. Add a brief rule: "end the turn after publishing; you will be resumed". For sub-agent waits, the session ends its turn and a zero-token watcher resumes it when the sub-agent outputs land. `handoff_sessions.py` already decides WHEN to resume, deterministically, so no LLM decision is involved. |
| wrapup_mech | (b) | `wrapup.py --json wrapup.json`. Input: `{slug, task_text, ticks:[text], progress_md, paths:[...], belief:"cc|clm_x|no-belief:..", message}`. It appends progress, ticks by task text (using the text-is-identity resolver), runs `index_state.py --check`, commits in a worktree with a pathspec and trailers, pushes through `serialized_push.py`, checks that `git cherry` is empty, then writes the `last_wrapup` sha and WRAPPED. The agent only writes the JSON. |
| filing_verdict | (a) when `decision_rule` is numeric, (b) otherwise | `file_result.py <row>` reads the `result_path` JSON and evaluates the row's machine-checkable `decision_rule` (for example `tps_delta >= +2% and ppl_delta <= 0.1%`). It writes the verdict record, then calls `wrapup.py`. For a non-numeric rule, the agent writes `{verdict, rationale}` JSON and the script applies it. |
| republish after a dry-run failure | (a) for known failure classes | `publish_row.py --repair` handles two known classes, then re-runs the dry-run. (1) A `result_path` that points at a completion marker (`.complete`, `.ended`, `.done`) is rewritten to the declared results JSON in the same run directory. (2) Missing spec fields that can be derived (`scratch_root`, `raw/keep`, region shape from the launcher, min-window from the estimate, booking class) are filled from the launcher or from defaults. Only unknown failure classes go to the agent. |
| spec_fix | (a) or (b) | The same repair table, plus a spec linter at publish time so these errors never reach a session. |
| rebase/merge | (a) | `wrapup.py` does the fetch and the rebase onto origin/main in a fresh worktree. Conflicts on generated files (`.index-state.json`, `backlog-priority.json`) are resolved by regenerating the file, not by hand. Only real source conflicts escalate. |
| duplicate notices | (a) | The dispatcher dedupes on the key `(grant_id, rc, end_line sha)` in its registry. A second `.ended` or `.complete` with the same key is dropped before any resume. |
| read_brief | (b) | `backlog_gen.py` computes a compact delta for the resume prompt, for example "your rows: X running, Y ended rc=0 result=...; next task text: ...". The prompt carries that delta instead of telling the agent to re-read the whole BACKLOG file. |
| subagent_orch | mostly (c) | Fan-out is a judgment call. The review sub-agents (`handoff_review`, `row_review`) have a fixed shape, though, and could become a schema linter that checks the row JSON against the publish contract. |
| codex-gen small tasks | (a) or (b) | Tasks of the form "regenerate X, commit, push" or "republish row Y" go straight to the scripts above. codex-gen keeps only the tasks that write code. |
| other_work; interpreting non-numeric results; picking the next research step | (c) | Stays with the LLM. |

## 3. Ranked proposals

Ranked by tokens saved per day multiplied by robustness gain. The estimates assume about 70% of each class can be removed. G = 10^9 input tokens, almost all of them cached.

| Rank | Proposal | Estimated saving per day | Robustness gain | Effort |
|---:|---|---|---|---|
| 1 | No-poll rule, plus watcher-driven resume of sessions that wait on sub-agents or grants | ~0.7 G input and ~5 k turns in handoff sessions, plus ~0.1 G in codex-gen | High: removes busy loops and decisions made on stale state | S (brief) + M (sub-agent completion watcher) |
| 2 | `wrapup.py` (progress, tick, commit, push, cherry and WRAPPED from a JSON, including the rebase) | ~0.35 G and ~2.5 k turns in handoff sessions, plus ~0.1 G in codex-gen | Very high: unpushed or unlanded wrap-ups and staged files riding along on someone else's commit become impossible | M |
| 3 | Compact resume delta instead of a full BACKLOG re-read | ~0.5 G and ~4 k turns | Medium | S/M |
| 4 | `publish_row.py --repair` plus a spec linter | ~0.3 G and ~2 k turns | High: a dry-run failure stops costing a full session turn cycle | M |
| 5 | `file_result.py`: auto-file verdicts when the `decision_rule` is numeric | ~0.08 G and ~0.6 k turns; the main gain is latency | High: verdicts become reproducible and thresholds cannot be misread | M |
| 6 | Dispatcher dedupe of duplicate run-end events | ~0.015 G | Medium: prevents double filing | S |
| 7 | Replace the review sub-agents with a schema linter | Part of the 0.73 G spent on sub-agent orchestration | Medium | M |

### Owning handoff and draft task lines

None of the active indices has a section for the churn pipeline. The dispatcher's own handoff is `handoffs/active/session-bus-thin-dispatcher.md`, so the recommendation is a new section there: "Churn AI-free mechanization (2026-11-01)".

These draft task lines are for ws58 to apply. They have not been applied.

```
- [ ] **CAF-1 — no-poll resume.** Briefs forbid wait/sleep/list loops; `handoff_sessions.py` resumes a session when its grant ends OR its sub-agent outputs land. Deps: none. Evidence: research/deep-dives/churn-ai-free-audit-20261101.md §3.
- [ ] **CAF-2 — `scripts/coordination/churn/wrapup.py`.** JSON in → progress, tick-by-text, index check, pathspec commit, serialized_push, cherry-empty, WRAPPED + last_wrapup. Deps: none.
- [ ] **CAF-3 — resume delta.** `backlog_gen.py` emits a per-slug state delta; the resume prompt carries it instead of "re-read BACKLOG". Deps: none.
- [ ] **CAF-4 — `publish_row.py --repair` + spec lint.** Auto-fix result_path→completion-marker and derivable spec fields; re-dry-run. Deps: none.
- [ ] **CAF-5 — `file_result.py`.** Numeric decision_rule auto-files verdict, then calls wrapup.py; non-numeric takes agent verdict JSON. Deps: CAF-2.
- [ ] **CAF-6 — run-end dedupe.** Dispatcher drops repeat .ended/.complete for the same (grant_id, rc, end_line). Deps: none.
- [ ] **CAF-7 — codex-gen routing.** Bookkeeping-only gen tasks call CAF-2/4/5 scripts directly. Deps: CAF-2, CAF-4.
```

## Caveats

- The regex attribution splits each turn's tokens evenly across its calls, so the class boundaries are approximate, give or take several percent.
- The handoff-session JSONLs carry no token events; all numbers come from the rollouts.
- The Claude-side ws58 subagents (filing, reclaim plans, intake) were not measured, because their transcripts were out of scope.
