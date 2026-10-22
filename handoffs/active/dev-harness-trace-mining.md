# Dev-Harness Trace Mining

**Status**: stub
**Created**: 2026-10-22 (via research intake, operator-approved plan of 2026-10-22)
**Categories**: agent_architecture, benchmark_methodology, knowledge_management

## Objective

Mine EPYC's own development-harness transcripts (Claude Code, Codex, opencode) for operator-signal series,
guard behaviour and lesson efficacy, so that lessons, hooks and harness rules are kept or promoted on
measured recurrence rather than on anecdote. Measurement only; hook and policy edits stay human-applied.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-2387 | Beacon cross-harness trace capture and distillation | high | adopt_patterns | dive-verified |
| intake-2395 | Measure Before You Manage (working memory) | medium | worth_investigating | dive-verified |
| intake-2396 | Agent memory distillation (disjoint-split protocol) | medium | worth_investigating | dive-verified |
| intake-2397 | SWE-chat (real coding-agent sessions) | medium | worth_investigating | dive-verified |
| intake-2426 | Invisible failures in human-AI interaction | medium | worth_investigating | dive-verified |
| intake-2428 | Transluce coding-agent misalignment in the wild | medium | worth_investigating | dive-verified |
| intake-2429 | Anthropic: measuring agent autonomy in practice | medium | worth_investigating | dive-verified |

## Tasks

- [ ] **DHM-1 — Mechanical operator-signal series: count both interrupt markers (plain and for-tool-use) and the Codex/opencode abort analogues per 1000 turns with Wilson CIs, split main vs subagent and by harness; keyword pass for operator corrections in ~/.claude/history.jsonl since 2026-03 (intake-2397, intake-2429).**
  - *(2026-10-22, workspace-f8 / mining-m1.)* **Code done; full run scheduled** (main thread, outside the quiet window): `scripts/dev_harness/mine_m1.py` (tests `tests/dev_harness/test_mine_m1.py`), aggregate `dhm1.aggregate.json` (dev-harness-aggregate.v1) under `<private-root>/mining/<run>/m1/aggregates/`. Turn = deduplicated assistant model call; split harness x source x main/subagent plus a monthly series; Codex child threads replay parent history with FRESH timestamps at birth (measured: one parent's aborts copied into 32 forks), so events within 5 s of a child's birth are excluded from numerator and denominator (raw kept); a marker copied into a Claude child with the same ts counts once. Sample (`sample-20261022`, 66 units, tiny N): claude main 2.3/1000 turns (1/429, CI 0.4-13.1), subagent 0/2752; opencode 19/1000 (2/105); codex 0/541. Correction keyword pass is implemented (`--tasks history --history <file>`) but NOT run: its only input, `~/.claude/history.jsonl`, is a live store this lane may not open; the main thread decides whether to pass it.
    Full run: `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m1.py --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z` (est. 5-10 min, peak RSS ~1.5 GB; covers DHM-1, DHM-5, OAB-LB1, UFH14-LB8).
- [ ] **DHM-2 — Retrospective guard audit over sampled sessions per harness: predicates for pattern kills, edits of a running script, writes outside the allowlist, wholesale git add, piped gate push, glob rm -rf, git clean, llama-cli without timeout and the monitor-evasion surface forms (no-verify, hooks path to /dev/null, skipped or deleted tests), plus a hook-denial and tool-error census; report would-fire, blocked and slipped-through per class and harness (intake-2387, intake-2428).**
  - 2026-10-22 (f8, branch `f8/mining-m2-20261022`): code done; full run scheduled. `scripts/dev_harness/m2_guards.py`: 21 classes; the hooked ones reuse the production scanners (pattern-kill, filesystem containment, llama-cli, shell_scan); outcome from the paired result (blocked_hook / blocked_user / errored / slipped_through / no_result) and hook era (git add-date). Denial census by hook name; tool-error census per tool. Sample `sample-20261022` (65 units, 4,050 tool calls): 63 would-fire, 43 of them containment refusals, all blocked by the hook; 75 hook denials, all Claude Code. Full run: driver `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m2.py --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z`.
- [ ] **DHM-3 — Lesson registry and interrupted-time-series pilot: register feedback memories, incident rules and CLAUDE.md rules with date, channel and a mechanical detector; write the ITS spec (violation, operator-signal and mechanical verified-outcome families; tool-call exposure with a per-turn companion; segmented regression with trend and model/harness change points; permission-mode, work-mode and specificity covariates; session and day clustering, never-lessoned control classes, campaign-grouped self-exclusion); run 3-5 lessons with forbidden surface forms as violations per 1000 tool calls pre/post, split prose-only vs hook-enforced, with the delivered-context rate (intake-2395, intake-2396, intake-2426, intake-2429).**
  - 2026-10-22 (f8): registry + spec done, pilot code done; full run scheduled (same driver). `scripts/dev_harness/lesson_registry.json` (290 lessons: 227 feedback memories, 38 incidents, 25 CLAUDE.md rules; 22 with a detector, 9 hook-enforced; built by `m2_lessons.py build-registry`, read-only on its sources). Spec: `docs/design/dev-harness-its-pilot-spec.md`. Pilot: pattern_kill, llama_cli_unbounded, wholesale_git_add (prose then hook), piped_gate_push, glob_rm (prose-only), with never-lessoned control classes and delivered-context rates. The sample covers 3 days only, so it carries no pre/post read.
- [ ] **DHM-4 — Prepare a 100-item operator labelling sheet of interrupts plus the next operator message with the reason clusters (correction, slow/hanging, next step myself, requirement change, other) and a lesson-provenance template (harness, session, event range; trigger-phrased applicability) for new incident and feedback lessons; agent labels are not used (intake-2429).**
  - 2026-10-22 (f8): code done; the sheet is generated by the scheduled full run into `/mnt/raid0/llm/private/dev-harness-traces/mining/full-20261022T1310Z/dhm4_label_sheet.{csv,md}` (PRIVATE, never commit). 100 items stratified by harness x source; the operator fills `label` (correction / slow_hanging / next_step_myself / requirement_change / other) + `note`; `m2_label_sheet.read_labels` validates. Provenance template in the sheet and the ITS spec §7. Blocked after the run only on operator labelling.
- [ ] **DHM-5 — Measure the always-on prefix (CLAUDE.md plus the MEMORY.md index) in tokens per turn from transcript usage fields, per harness (intake-2408, intake-2410).**
  - *(2026-10-22, workspace-f8 / mining-m1.)* **Code done; full run scheduled** (same driver, `dhm5.aggregate.json`). Per harness x source x role: first-turn prompt tokens (input incl. cache = the observed per-turn floor), mean prompt per turn, cache-read share, and the always-on files (claude main CLAUDE.md+MEMORY.md, subagent CLAUDE.md, codex/opencode AGENTS.md) in tokens per turn. Finding: Claude Code JSONL `usage.output_tokens` is a stale streamed value (calibrates to 14.5 chars/token), so it is excluded from chars/token calibration; opencode/codex calibrate, else 3.6 assumed (flagged). Sample: claude main first-turn p50 27.9k tok, mean prompt 211k/turn, always-on files ~12.4k tok/turn (3.6 chars/token assumed: nothing calibrated in the sample) = 5.9% of prompt tokens (44% of the first-turn floor); subagents ~6.1k = 3.7%.
- [x] **DHM-6 — Draft the guard-denial ledger proposal: every PreToolUse refusal appends ts, hook, session, harness, rule and fidelity=observed to one private JSONL (enables detecting a command executed after its denial); hook edits stay human-applied (intake-2387).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / mining-m1.)* Proposal written: [`docs/design/guard-denial-ledger-proposal.md`](../../docs/design/guard-denial-ledger-proposal.md) (record schema `dev-harness-guard-denial.v1` with keyed-HMAC command blocks joinable to projector tool_call events, best-effort flock append, the 11 refusing Claude hooks + Codex/opencode containment guards, tests, rollout order). Applying it is a human hook edit.
- [ ] **DHM-7 — Write a pure-python converter from Claude Code, Codex and opencode transcripts to AgentRun-style JSON (tool calls and results, both interrupt markers kept, sessions split into capped task-window segments, private output), then run a no-LLM clustering baseline over tool-error and denial segments (CPU sentence embedding, k-means, mechanical facets) validated by planted recovery of known incident classes, reporting a cluster only with at least 3 distinct sessions and 2 distinct days (intake-2443, intake-2444).**
  - [x] **DHM-7.1 — converter** ✅ 2026-10-22: `scripts/dev_harness/agentrun.py` (stdlib; Docent AgentRun shape
    written from scratch) → `/mnt/raid0/llm/private/dev-harness-traces/agentrun/<run>/<harness>/<unit>.seg-NNN.json`
    + `index.jsonl`; task windows split at operator prompts and capped (120 msgs / 60k chars / 4k per message); both
    Claude markers kept verbatim, Codex/opencode aborts as synthesized markers. Sample `sample-20261022`: 291
    segments (122 with a tool error, 64 with a denial, 3 with an interrupt), 1.4 s.
  - [ ] **DHM-7.2 — no-LLM clustering baseline** over the index's tool-error/denial segments (CPU sentence embedding,
    - 2026-10-22 (f8): code done; full run scheduled. `scripts/dev_harness/m2_cluster.py`: signed-hashed TF-IDF (D=1024) as the CPU embedding, because /usr/bin/python3 has no onnxruntime or sentence-transformers and `embed()` is the drop-in point; spherical k-means; 5 planted incident classes; reports a cluster only with >=3 sessions and >=2 days. Sample: 122 docs, 6 clusters reported; 3 of 5 planted classes recovered at k=8 (two merged), which is expected at sample size.
    k-means, mechanical facets, planted recovery, ≥3 sessions and ≥2 days per reported cluster); needs the full run
    (UTM-LB2.1) for the day spread.

## Open Questions

- Does a memory-only lesson change its violation rate at all, or only hook-enforced ones?
- What fraction of interrupts are agent errors (operator labels, DHM-4) versus slow/hanging or scope change?

## Notes

- **Sources (operator 2026-10-22, scope ruling: mine EVERYTHING; every record carries a `source` tag epyc|host|twyne).**
  opencode: the read-only hourly snapshots `/mnt/raid0/llm/opencode-db/{epyc.db,host-daniele.db}` (symlink to
  `/mnt/raid0/llm/opencode/readonly/`; at most ~1 h stale, full history; open `file:<path>?mode=ro`, retry once if the open
  fails because the copy is being replaced; tables `session`/`message`/`part`, never `event`). Claude Code + Codex:
  `/mnt/raid0/llm/cloud-llm-vault/{host,twyne,epyc}/{claude,codex}/` (append-only JSONL). The LIVE opencode stores
  (`~/.local/share/opencode/opencode.db`, `/mnt/raid0/llm/opencode/<src>/opencode.db`) are never opened for mining.
  Shared helper: `scripts/dev_harness/dh_sources.py` (`OPENCODE_RO_DBS`, `open_ro`, `refuse_live_opencode_path`).
- Inputs are read from the existing conversation backup (the nightly cloud-llm-vault sync and the ai-sessions tarballs;
  coverage checked by UTM-LB1) through the private projector (UTM-LB2); no parallel backup is built. Outputs are
  aggregate-only and private (F3-LB1). epyc-root is a public repository: never commit transcript content.
- Hosted annotators are not used on our data (typed-decision ruling); labels come from the operator.
- harness-improvement-loop.md excludes the shell surface from its mutation loop, which is why this measurement
  work has its own owner.
