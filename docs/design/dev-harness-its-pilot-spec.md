# Dev-harness lesson efficacy: interrupted-time-series pilot spec (DHM-3)

**Status**: spec + pilot code, 2026-10-22. Owner: `handoffs/active/dev-harness-trace-mining.md` (DHM-3).
Code: `scripts/dev_harness/m2_lessons.py` (registry + pilot), `m2_guards.py` (detectors), `mine_m2.py`
(driver). Registry: `scripts/dev_harness/lesson_registry.json`. Sources: intake-2395#record, intake-2396#record,
intake-2426#record, intake-2429#record.

## Question

Does registering a lesson change how often agents do the thing it forbids? Does a lesson that lives only
in prose (a feedback memory, an incident entry, a CLAUDE.md rule) behave differently from one that a
PreToolUse hook enforces? This is measurement only. Hook and policy edits stay human-applied.

## 1. Lesson registry

`m2_lessons.py build-registry` writes one entry per lesson. It only reads the memory dir,
`docs/reference/agent-config/INCIDENT_LOG.md` and `CLAUDE.md`:

| field | meaning |
|---|---|
| `id` | memory file stem, `INC-…` id, or `claude_md:<section>:<n>` |
| `kind` / `channel` | `feedback_memory`/`memory`, `incident_rule`/`incident_log`, `claude_md_rule`/`claude_md` |
| `date`, `date_basis` | memory: the earliest ISO date in the text (the origin event), else the file mtime. Incident: the date in the id. CLAUDE.md: the git pickaxe commit of the **current wording**, which is an upper bound on the origin date. |
| `detector` | DHM-2 guard classes that match the lesson's forbidden surface form. `[]` means the lesson has no mechanical surface form and is out of scope for this pilot. That is recorded, not hidden. |
| `enforced_by` | hook file, covered harnesses and hook add-date, for detector classes a production hook enforces |

The detector map is hand-curated (`DETECTOR_MAP`, `CLAUDE_MD_KEYWORDS`). A test fails if a mapped id
disappears from the sources.

## 2. Outcome families

1. **Violation**: a would-fire of the lesson's detector on a tool call. The predicate is applied
   retroactively, so it answers "would today's rule fire?" (DHM-2). Where a hook exists, the predicate
   *is* the hook's scanner. A violation's outcome comes from its paired tool result: `blocked_hook`,
   `blocked_user`, `errored`, `slipped_through` or `no_result`.
2. **Operator signal**: interrupts (both Claude markers plus the Codex and opencode abort analogues),
   operator rejections (`blocked_user`) and the operator-labelled correction share (DHM-4). This family
   uses operator labels only. Agent labels are never used.
3. **Mechanical verified outcome**: the same session's later gate results, such as tests passing after
   the violating call or the commit-join (`commits.jsonl`) landing on main. This family is defined here
   and is not yet computed by the pilot.

## 3. Exposure and rates

- **Primary exposure**: tool calls. Rate = violations per 1000 tool calls.
- **Per-turn companion**: violations per 1000 operator turns (`human` user messages). It guards against
  a change in tool-call density masquerading as a lesson effect.
- **Intervals**: 95% Poisson log-normal intervals. When k = 0, the upper bound uses the rule of three.

## 4. Design

**Segments**, defined per lesson:

| segment | window |
|---|---|
| `pre_lesson` | before the lesson date |
| `post_lesson_prose_only` | from the lesson date until the hook date, or until the end of data if there is no hook |
| `post_hook` | from the hook date, on harnesses the hook covers |
| `post_hook_harness_uncovered` | after the hook date, on harnesses the hook does not cover. This is the in-period control for the hook. |

**Model, as specified**: segmented regression on daily counts, Poisson or negative-binomial, with a
log(tool calls) offset. Terms:

- level and trend;
- level and slope change at the lesson date;
- level and slope change at the hook date;
- change points at model and harness changes (`gen_ai.request.model` and the harness version in
  `source_schema_key`);
- covariates: permission mode (`meta` permission-mode records), work mode (main vs subagent, and
  operator-present vs autonomous via operator-turn density) and lesson specificity (whether the
  forbidden form is a literal command or a class of commands).

Standard errors are clustered by session and by day.

**Model, as piloted**: the pilot fits an exposure-weighted OLS on daily rates with the same level,
trend and change-point terms (`segmented_regression` in the aggregate), plus segment rate ratios. It
has no covariates and no clustered errors. It is a feasibility readout, not the inference.

**Never-lessoned control classes**: detector classes that have no lesson, or whose lesson is later than
the window, give the secular trend. Examples are `git_reset_hard`, `no_verify` and `hooks_path_null`
(check `lesson_registry.json`: `detector` lists them for no lesson; `m2_lessons.CONTROL_CLASSES`). A lesson
effect is only read against these controls, as a difference-in-differences on the segmented terms. The
pilot reports the controls' rate in each lesson segment as `control_per_1k_tool_calls`.

**Campaign-grouped self-exclusion**: the session that produced a lesson, and its campaign siblings,
would otherwise count their own corrected behaviour as a post-lesson effect. The pilot excludes every
unit whose first event falls on the lesson's origin day (`self_excluded_units`). The full model
excludes by campaign: units sharing a worktree or branch prefix, or a parent session, with the origin
session.

**Delivered-context rate**: the share of exposure in which the lesson's channel was mechanically in
context. The measure has fidelity=inferred. Rules by channel:

- `memory`: Claude Code sessions of the `/workspace` project, whose auto-memory index loads, or any
  session that reads the memory file.
- `claude_md`: Claude Code sessions on the epyc source, or any session that reads CLAUDE.md.
- `incident_log`: only sessions that read INCIDENT_LOG.md.

A prose lesson whose delivered rate is low cannot show an effect, and that result is reported as
**not delivered**, never as **no effect**.

## 5. Pilot lessons

Five lessons, each with a literal forbidden surface form. The table lists them by `m2_lessons.PILOT`
class:

| class | lesson (date) | hook (add-date) | form |
|---|---|---|---|
| `pattern_kill` | INC-20260731-broad-process-pattern-kills (07-31) | check_process_pattern_kill (08-12, Claude only) | `pkill` on a name pattern |
| `llama_cli_unbounded` | feedback_llama_cli_repl_must_be_killed (08-28) | check_llama_cli_guard (09-01, Claude only) | `llama-cli` without `timeout` |
| `wholesale_git_add` | feedback_no_wholesale_git_add_shared_files (05-27) | check_commit_hygiene Rule A (07-27, Claude only) | `git add -A/./-u`, `commit -a` |
| `piped_gate_push` | INC-20260929-piped-gate-push (09-29) | none, prose-only | `<gate> \| tail && git push` |
| `glob_rm` | INC-20261004-glob-rm-deleted-receipt-evidence (10-04) | none, prose-only | `rm -r/-f` with an unquoted glob |

The mix gives two prose-only lessons and three lessons that went prose → hook. For the hooked three,
Codex and opencode are the uncovered-harness controls.

## 6. Threats

- **Retroactive predicates**: they over-fire on shapes that the rule's authors would have allowed.
  The predicates are kept invocation-scoped (`shell_scan`) and are tested against both firing and
  quiet cases.
- **Truncation**: AgentRun caps a message at 4000 characters, which can cut a heredoc terminator. A
  truncated command's unterminated heredoc is treated as data. The `truncated_commands` exposure
  counter reports how often this happens.
- **Dates**: hook dates are git add-dates, and registration in the harness settings can lag them.
  CLAUDE.md dates are upper bounds.
- **Lesson attribution**: one class can carry several lessons (memory, incident and CLAUDE.md). The
  pilot dates the class by its earliest pilot lesson and reports delivery for all of its channels.

## 7. Lesson-provenance template (DHM-4)

Fill one block per new incident or feedback lesson, so that the next registry build can date it and
attach a detector:

```
- harness: claude_code | codex | opencode
- source: epyc | host | twyne
- session: <unit_key>
- event range: <first_ts> .. <last_ts>  (or segment ids)
- trigger-phrased applicability: "When <situation the agent can recognise>, <do / never do> <action>."
- forbidden surface form (if any): <command / edit shape a detector can match>
- channel: memory | incident_log | claude_md | hook
```
