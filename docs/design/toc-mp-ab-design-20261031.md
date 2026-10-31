# TOC-MP A/B design: arm set (TOC-MP-2) and reliability requirements (TOC-MP-3)

Date: 2026-10-31. Design text, zero inference. Owner handoff:
[`handoffs/active/tool-output-compression.md`](../../handoffs/active/tool-output-compression.md),
the first-party verbatim-log A/B box and tasks TOC-MP-2 / TOC-MP-3. Code read at
epyc-orchestrator `origin/main` @ `367df713`. Sources: intake-2522..2534, intake-914, intake-919
(`intake-2528#record` for the wall-time item).

## 0. What the code does today (the facts the arms are built on)

1. **The REPL turn prompt carries no conversation history.** `_execute_turn`
   (`src/graph/helpers.py:1386-1430`) rebuilds every prompt from the task prompt, REPL state,
   the last output/error (through `_spill_if_truncated`) and `_session_log_prompt_block(state)`.
   Earlier turns reach the model only as the session summary.
2. **`_maybe_compact_context` does not change what the model sees.** It rewrites
   `TaskState.context`, which is never rendered into a prompt (UFH14-B1 comment,
   `src/graph/compaction.py:248-257`). Its trigger also measures `state.context`, not the prompt.
3. **The "full log" pointer points at a truncated journal.** `_session_log_prompt_block`
   (`src/graph/session_summary.py:351-362`) appends `Full log: peek(99999, file_path=…)`, and
   that file is written by `append_turn_record` from `TurnRecord.to_markdown_block`
   (`src/graph/session_log.py:89-107, 905-917`): code as an 8-char hash plus its first line,
   output cut to 200 chars, error cut to 300. A value printed past char 200 of an output is not
   in the log. The only verbatim copies are spill files (`_spill_if_truncated`,
   `src/graph/file_artifacts.py:100-139`), which exist only for outputs over the preview cap.
4. **The production summary is 2-4 sentences** (`build_session_summary_prompt`,
   `session_log.py:969-979`, worker `n_tokens=300`), built from 200-char previews and refreshed
   every 2 turns (`_SESSION_LOG_REGEN_INTERVAL`).

So none of arms 1-5 exists as a runnable configuration. Each needs a history renderer and a
verbatim log. The arms below are defined so that they differ in one factor each, and section 3
lists the code they need.

## 1. TOC-MP-2: context budget C and the arm set

**C = 16,384 tokens**, the same for every arm and every backbone (A/B-C), recorded in each
trajectory's `final` event as `context_budget_tokens`. It is a harness-side cap on the rendered
prompt, well inside the served window (frontdoor `:8070` is 65,536 per slot; the served `n_ctx`
stays recorded per turn), so all arms run on the same unmodified server. Reason for 16K and not
the 64K window: no REPL trajectory in the standing corpus came near 64K (the largest is 12,649
prompt chars; TOC-SP-5). At 64K no arm would ever externalize and the A/B would compare five
identical prompts. TOC-MP-4's fixture (>4,000-char outputs) crosses 0.5 x C in about 6-8 turns.

**The boundary is shared by all arms.** Before the first boundary, every arm renders the full
verbatim history: each prior turn's code, output and error, with outputs over the preview cap
still passed through `_spill_if_truncated` as today. A boundary fires when the rendered history
reaches f x C. Primary f = 0.5; A/B-TRIG also requires runs at f = 0.25. TOC-MP-4 instead forces
boundaries at fixed turn indices. At a boundary, history up to that turn is replaced as the arm
says. Turns after it build up verbatim until the next boundary, and summary arms then use the
update prompt. **Verbatim tail** = the most recent whole turns that fit in 0.20 x C = 3,276
tokens (at least one turn), the same ratio as `session_compaction_keep_recent_ratio`.

| # | Arm (`ORCHESTRATOR_CONTEXT_ARM`) | After a boundary, the prompt carries | Pointer | Summarizer call | Source shape |
|---|---|---|---|---|---|
| 1 | `summary_only` | OpenClaw summary + verbatim tail | none (the verbatim log is still written, never named) | yes | MemGPT DMR baseline (intake-2530) |
| 2 | `summary_pointer` | OpenClaw summary + verbatim tail + `Full log: peek(<chars>, file_path="<verbatim log>")` | verbatim log | yes | production `_session_log_prompt_block`, Cursor / Claude Code / OpenClaw (intake-2524, intake-2534) |
| 3 | `pointer_only` | verbatim tail + full-log pointer + the continuation sentence (below) | verbatim log | no | Mainplane (intake-2522, intake-2523) |
| 4 | `prune_pointer` | full history with old tool results pruned: outside the last 3 turns, results over 4,000 chars are soft-trimmed (head 1,500 + `...` + tail 1,500); if still >= f x C, hard-cleared oldest first. Code and model text are never pruned | in every trimmed or cleared result | no | OpenClaw session pruning (intake-2534), plus the pointer OpenClaw lacks |
| 5 | `full_history` | full verbatim history; no boundary | none needed | no | reference |

Notes on the table:

- **Arm 2 vs production.** Arm 2 keeps production's structure (summary block, then
  `Full log: peek(...)`) but changes three things so the summary arm is not a straw man: the
  summary is OpenClaw's prompt over verbatim turns, the pointer names the verbatim log, and the
  shared tail is added. Today's 2-4-sentence summary over 200-char previews is the A/B-CTRL
  question, not an arm here. A/B-CTRL still decides what the live path runs.
- **Arms 1-3 differ in one factor each.** 1 vs 2 isolates the pointer, and 2 vs 3 isolates the
  summary.
- **Arm 4 placeholder** (OpenClaw's default text plus our pointer):
  `[Old tool result content cleared; full text: peek(<chars>, file_path="<verbatim log>", offset=<k>)]`.
  A soft-trim puts the same `peek(..., offset=k)` marker at its `...`, in `_spill_if_truncated`'s
  exact-span format. Keeping the last 3 turns whole is OpenClaw's rule. The 4,000 / 1,500 / 1,500
  thresholds are ours, because OpenClaw's soft-trim numbers were not pinned.
- **Arm 5 over C.** When the full history exceeds C, the task ends as
  `terminal_state=context-exhausted` and scores a failure. Arm 5 reports its fit rate, and every
  arm is also reported on the subset of tasks where arm 5 fit.
- **Arm 3 continuation sentence (pinned):** `Earlier turns of this task are not shown. You are
  continuing the same task: retrieve exact lines from the full log with peek() or grep() as you
  need them.` This adapts Mainplane's `You are continuing session X. Retrieve key context from it
  as you go.` (intake-2522).

**Pinned OpenClaw summary prompt (arms 1-2).** Source: `openclaw/openclaw`
`packages/agent-core/src/harness/compaction/compaction.ts` @
`0e7b5c34292cc28707a0e5a0b730cff295ef0f8a` (2026-06-10; file sha256
`83b7fb64…3833449`). The three template-literal bodies, byte-exact, with their sha256:

| Constant (line) | chars | sha256 |
|---|---|---|
| `SUMMARIZATION_SYSTEM_PROMPT` (437) | 317 | `78c24210d5ba3e2fbcb8b13289c2488d52f3d5317fe5bfc4055dfc126e4b8570` |
| `SUMMARIZATION_PROMPT` (441), first boundary | 879 | `9b00aa68df1a64279bc36e9093367f638701d48ec82e3d08436f65092a515f9b` |
| `UPDATE_SUMMARIZATION_PROMPT` (474), later boundaries | 1257 | `240c52982209146eae47d73c7172f6ba1dab60f44520bcb6a6ec1a883fef2ec7` |

Message assembly is the same as `generateSummary`: system = `SUMMARIZATION_SYSTEM_PROMPT`; user =
`<conversation>\n{turns}\n</conversation>\n\n` + (`<previous-summary>\n{prev}\n</previous-summary>\n\n`
on update) + the prompt. `{turns}` is the verbatim turns behind the boundary, passed through
`neutralise_control_tokens`. The implementation vendors these strings as constants (MIT, with
attribution) and a unit test checks the three sha256 values. First-boundary prompt body for
reference (sections: Goal / Constraints & Preferences / Progress {Done, In Progress, Blocked} /
Key Decisions / Next Steps / Critical Context, closing with "Keep each section concise. Preserve
exact file paths, function names, and error messages."). Summarizer settings: role from
`_session_summary_worker_role()`, recorded per run; `n_tokens = 1,024` (OpenClaw's own cap,
0.8 x reserveTokens = 13,107, is close to C itself); temperature 0. The summary is regenerated
only at boundaries, not every 2 turns.

### Arm to code map

| Arm element | Code site | Change |
|---|---|---|
| Boundary detection (all arms) | `compaction.py` `_maybe_compact_context` (called each turn from `helpers.py:1290`, forced on `ContextOverflowError`) | When `context_arm_ab` is on, a new branch runs **before** the `session_compaction` early return. It measures the **rendered history block** (not `state.context`) against f x C, ignores the `len(state.context) > 12000` char trigger, honours `ORCHESTRATOR_CONTEXT_FORCE_TURNS`, records `state.history_boundaries.append(turn)` and calls `trajectory_artifact.note_history_rewrite`. The `state.context` rewrite stays as it is (unrendered). |
| C | `compaction.py` `_get_model_max_context` | Returns `min(real, ORCHESTRATOR_CONTEXT_BUDGET_TOKENS)` when the flag is on. |
| Verbatim log + history source (all arms) | `session_summary.py` `_record_session_turn` | Behind `session_log_verbatim`: append full code, output and error per turn to `session_<task>.verbatim.md`, keep a per-turn byte-offset table in state (for arm-4 `offset=`), and keep in-memory verbatim turns for the renderer. The location follows TOC-MP-1's fix, so the pointer is readable in task-root and request-scope modes. |
| Summary + pointer render (arms 1-3, 5) | `session_summary.py` `_session_log_prompt_block` | When the flag is on, it delegates to a new `_session_history_prompt_block(state, arm)`. It renders pre-boundary history, summary (arms 1-2), tail, pointer (arms 2-3) or sentence (arm 3), and returns the production block byte-identically when the flag is off. |
| Summary producer (arms 1-2) | `session_summary.py` `_maybe_refresh_session_summary` | When the flag is on and the arm is 1 or 2, it calls the OpenClaw prompt at boundaries only. Otherwise it does not refresh. |
| Pruning + pointer (arm 4) | `file_artifacts.py` `_spill_if_truncated` | Reuse its `peek(n, file_path=..., offset=k)` marker for soft-trim and placeholder text, pointing into the verbatim log. Spilling of the *current* output stays unchanged in every arm. |
| Confounders, OFF in every arm | `session_compaction`, `session_compaction_llm_index`, `two_level_condensation`, `session_scratchpad`, `tool_result_clearing`, `REPL_SPILL_ERROR_PRESERVE`, `REPL_LOOP_GUARD` | These are recorded in the run manifest. `session_log`, `output_spill_to_file` and `trajectory_artifact` (+ `ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR`) are ON in every arm. |

**Feature flags needed.** None exist today.

- `session_log_verbatim`: new `FeatureSpec` in `src/features.py`, env
  `ORCHESTRATOR_SESSION_LOG_VERBATIM`, default off in both test and prod. All five arms need it.
- `context_arm_ab`: new `FeatureSpec`, env `ORCHESTRATOR_CONTEXT_ARM_AB`, default off. It
  requires `session_log_verbatim`. Arm parameters are env knobs read per call (feature flags are
  boolean-only):
  - `ORCHESTRATOR_CONTEXT_ARM` = `summary_only|summary_pointer|pointer_only|prune_pointer|full_history`
  - `ORCHESTRATOR_CONTEXT_BUDGET_TOKENS=16384`
  - `ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION=0.5` (or `0.25`)
  - `ORCHESTRATOR_CONTEXT_FORCE_TURNS` (comma list, for TOC-MP-4)
  - `ORCHESTRATOR_SESSION_SUMMARY_PROMPT=openclaw_0e7b5c3` (arms 1-2)
- Flag-off acceptance: prompt bytes are identical to `origin/main` (exact-string test), and
  `runtime_flags.spec.yaml` is re-synced with `--sync-spec`.

## 2. TOC-MP-3: reliability, retrieval-miss, literal-recoverability and wall-time requirements

- **(a) Trials and estimators.** n = 4 trials per task per arm (the tau2 protocol, intake-2532),
  and never fewer than 2. With c = successes in n trials, compute per task and then average over
  tasks:
  - pass^k = C(c,k)/C(n,k)
  - pass@k = 1 - C(n-c,k)/C(n,k)

  Report both at k = 1, 2, 4 (intake-2533), with a task-level bootstrap CI. Never compute p^k of
  the mean success. Success is the external scorer's grade, never `final.solved`, which is the
  finish flag. Report the instability gap pass@k - pass^k per arm (intake-2527: compression lowers
  pass^2 more than accuracy).
- **(b) Post-boundary blocked/error actions.** For each boundary at turn b, count turns b+1..b+5
  whose outcome is `error` or `blocked`, beside the same count over b-5..b-1 (intake-2527).
  `blocked` means the REPL refused the action, for example a `_validate_file_path` denial or a
  rejected status. Deliberate re-reads are retrieval calls on the verbatim log, ctx file or a
  spill file. They are counted apart and never as errors.
- **(c) Retrieval misses.** A miss is a task whose needed fact, after the last boundary before
  the answer, sits only in the externalized log (absent from that turn's rendered prompt) and is
  never read back before the answer. Report the miss rate per arm beside log-follow counts. Also
  report **re-fetch** cost: execution turns whose code hash equals an earlier turn's (a re-run in
  place of a read), with their output tokens and their wall time (intake-2522, intake-2526: CWL
  recovers only by re-running).
- **(d) Literal-recoverability strata.** Each probe is tagged `direct` (the needed literal appears
  in the query), `paraphrase` or `two_hop` (intake-2531). Every metric in (a)-(c) is reported per
  stratum. A pointer arm's grep advantage is expected only on `direct`.
- **(e) Compaction wall share.** Sum of boundary work (summarizer call, render, log write) over
  task end-to-end wall time, per arm (`intake-2528#record`). This is separate from
  `compressor_wall_s`, which today times only tool-output compression (`helpers.py:1363`).
- A/B-COST, A/B-TRIG and A/B-STRAT (already ticked) apply unchanged.

**Metric directions.**

| Direction | Metrics |
|---|---|
| Higher is better | pass^k, pass@k, exact recall (TOC-MP-4), arm-5 fit rate |
| Lower is better | the gap pass@k - pass^k; post-boundary blocked+error count and its excess over pre-boundary; retrieval-miss rate; re-fetch tokens; re-fetch wall; compaction wall share; rolling input tokens; end-to-end wall |
| Descriptive, no direction | log-pointer follows. A follow that prevents a miss is good; one that repeats a read is cost. Read it only beside (c). |

### Field mapping

| Need | Existing field (`trajectory_artifact.py` @ `367df713`) | Schema addition (filed here) |
|---|---|---|
| arm, C, f, trial | none | `final.arm`, `final.context_budget_tokens`, `final.trigger_fraction`, `final.trial_index`; grade joined in the `toc_ab` sidecar by (task_id, arm, trial_index) |
| boundaries | `prefix_cache_invalidations` (count only) | `boundary` event: `turn`, `history_tokens_before`, `history_tokens_after`, `summary_tokens`, `wall_s` |
| error / blocked per turn | `turn.outcome` (ok/error/final) | `turn.blocked` (bool) |
| deliberate re-reads | `turn.spill_follows` (spill paths, `peek`/`grep` only) | `turn.log_follows`: same shape for the verbatim log and ctx paths, and `_FOLLOW_RE` extended to `read_file` (compaction's pointer form) |
| needed fact in prompt | none (hashes only) | `turn.probe_literals_present`: ids of fixture-registered literals found in the rendered prompt (ids only, no text; literal list supplied by the fixture manifest) |
| re-fetch | none | `turn.code_sha256`, `turn.turn_wall_s` |
| wall share | `compressor_wall_s` (tool-output only) | `final.boundary_wall_s`, `final.task_wall_s` |
| stratum | none | fixture manifest `probe_class` in {direct, paraphrase, two_hop}, joined by task_id |

These additions ship with the `context_arm_ab` implementation (handoff task TOC-MP-2i), default
off and fail-silent like the existing writer hooks.
