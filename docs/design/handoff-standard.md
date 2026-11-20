# Handoff Standard — structure, grammar, lifecycle, compiled view

Rev 1, 2026-11-19 (read-only audit subagent). Upstream of `DESIGN.md` (the dispatcher), the wrap-up skill and research-intake. Every claim cites `file:line` on origin/main or the working tree.

## 1. Current state, mapped

**Writers and readers of `handoffs/active/*.md`, and what each assumes**

| Surface | Writes | Assumes | Evidence |
|---|---|---|---|
| `handoff-index-authoring.md` | index rows | thin row `ID\|Track\|Handoff\|Next action\|Deps`; one owner row; status generated; history leaves the index; `Stop rule:` on measurement boxes; promote a box ≥32 lines; `**Scratch**` header | `:6-45`, `:47-49`, `:51-62`, `:129-177` |
| `SESSION_LIFECYCLE.md` Two axioms | box flips | dashboard counts checkbox state only; `✅ YYYY-MM-DD` appended; never tick another agent's box; frozen handoffs refuse new boxes; nonterminal outcomes add a child, never flip the parent; result tick carries `[belief: …]` + verdict on the line | "Two axioms" block, bullets 1–5 |
| `OPERATING_CONSTRAINTS.md` Dispatching Backlog Work | — (reads) | task TEXT is the identity, `file:LINE` a hint; screener proves well-formed not still-needed; AUD-2 typed dispatch (`task_text`, `screened_by`, `expected_occupancy`) | §"Dispatching Backlog Work" |
| `agents/commands/wrap-up.md` | ticks, new boxes, findings, index rows | Step 2: tick only when fully met, add discovered tasks as `- [ ]`, flip-count gate, belief-capture gate, derived-actionables gate; Step 3: index rows; prune only via `index_state` candidates | `:331-404`, `:411-475` |
| research-intake `SKILL.md` | appends boxes, creates stubs, index rows | Stage-4 "verbatim task lines to append", `previous_task_text` for refinement at same ID, stub template (`**Status**: stub`, `**Created**`), frozen/pointer check | `:626-640`, `:669`, `:715-718` |
| `index_state.py` | `.index-state.json`, master rollup | `## Track:` + `<!-- gate: … -->`; `[roll-up]` skipped; open/blocked/guarded via `backlog_row_check.classify`; prune blockers (`pointer`, `frozen`, `not-a-task-list`, `prose-open`); task_lint column warn-only | `:139-162`, `:270-308`, `:439-463`, `:1370-1418` |
| `backlog_row_check.py` | — | box = `^\s*[-*] \[( \|x)\] ` only (no `~ > !`); id = `**TOKEN**` prefix; blocked = child box saying "BLOCKED on/by", dependency-graph section, DO-NOT-DISPATCH section, owner prefix | `:209-210`, `:471`, `:526-603` |
| `task_lint.py` | — | rubric a–h + s; `[class]` tag wins over regex; `[roll-up]` non-dispatchable; `NEEDS-OWNER/OPERATOR/DECOMPOSITION` excuse a/d/f/h in migrate mode; publish mode refuses only c and s | usage text; audit `§5-6` |
| `flip_checkbox.py` | one line | anchor `- [ ] **<token>` unique; appends `✅ <date> (<note>)` | `:1-20` |
| `churn/wrapup.py` | ticks + progress + commit | tick resolved by TEXT to exactly one open box; appends `✅ <date> [belief: …]`; `belief ∈ cc\|clm_<id>\|no-belief: …` | `:6-9`, `:37`, `:123-151` |
| `worker_checkpoint.py` (`/log`) | tick or child box | `completed` flips exact box; `blocked`/`partial` add a checkpoint-keyed child | SESSION_LIFECYCLE bullet 4 |
| `publish_row.py` | — (binds rows) | `handoff_task` = `file.md:<TASK-ID>` or `:LINE`; lints that box in publish mode; relaxed to warn | `:17-22`, `:335-351` |
| `handoffs/README.md` | — | lifecycle CREATE/WORK/BLOCKED/COMPLETE/ARCHIVE; `blocked/` directory | lines "Handoff Lifecycle" |
| readiness audit 2026-11-02 | — | template `**ID** [class] deliverable — done when … · gate: · inputs: · owner:` + inference fields; five rules | `task-readiness-audit-20261102.md:83-100` |

**Measured adoption (33 active non-index handoffs, working tree):** 1,398 open boxes, 6,106 ticked, 1,755 ticked with a belief tag (29%). `## Track:`/`<!-- gate:` in 24 files, `**Scratch**` 29, `**Status**` 32, `Stop rule:` 13, `[class]` tags in 10, "done when" in 9, `NEEDS-OPERATOR` in 1. Lines: p50 2,517, p90 5,835, max 15,085; 19 files over 2,000 lines, 9 over 4,000. Header fields are free-form: 14 distinct bold keys (`Status` 53, `Created` 43, `Scratch` 36, `Priority` 36, `Categories` 30, `Parent index` 16, `Owner` 10, `Depends on` 6, `Gate` 5 …).

**Conflicts**
1. Three tick appenders, three formats: `flip_checkbox` writes `✅ date (note)`; `wrapup.py` writes `✅ date [belief: x]`; wrap-up.md asks for verdict/number on the line. Only `wrapup.py` enforces belief.
2. Two identity models: the doctrine says text is identity; `flip_checkbox`, `publish_row` and `index_state` gates key on `**TOKEN**` ids; `backlog_row_check._boxes` recognises only `[ ]`/`[x]`, so the `[~] [>] [!]` states `task_lint.CHECKBOX` accepts are invisible to the dashboard.
3. Blocked has four encodings: `handoffs/blocked/` directory (README), a child box reading "BLOCKED on X" (`backlog_row_check:354`), prose gates ("after X lands", 132 of 404 sampled boxes), and `<!-- gate: -->` at track level only. None is box-level and machine-readable.
4. Frozen has two: `❄ FROZEN <date> — resume only once …` prefixes inside the box text (`harness-program.md:343`), and the file-level `frozen` prune blocker regex (`index_state:273`). A frozen box still counts as open.
5. Intake appends at "the exact section" of a 4k-line file; wrap-up appends discovered tasks "in the relevant handoff"; no rule says *where* in the file, so boxes land under history blocks and `compile_state` picks them in file order (`handoff_sessions.py:2393`).
6. Audit template exists but nothing writes it: `task_lint` is advisory everywhere except the relaxed publish gate (`publish_row:20`).

**Undefined**: header schema; box-level deps/done-when/tier/owner fields; what "partial" looks like in a box; where findings live before `completed/`; a size limit per handoff; a compiled per-box view; who owns history compaction.

## 2. Structure

### 2.1 File anatomy (fixed order)
```
# <Title>
<front-matter block, one `**Key**:` per line, fixed keys>
**Status**: ACTIVE|FROZEN|POINTER|COMPLETE — one sentence       **Row**: RTG-58 (owning index row id)
**Created**: date   **Owner**: <session/role>   **Scratch**: <roots>   **Priority**: HIGH|MEDIUM|LOW
**Holds**: <operator hold ids or none>          **Size**: <generated: open/ticked/lines>
## Dispatch contract        (≤ 40 lines: how to work this file; no history)
## Track: <name>            (one or more; each starts with `<!-- gate: … -->`)
   ### Backlog              (open boxes, priority order, top = next)
   ### Done                 (ticked boxes, newest first; compacted per §3.7)
## Findings                 (durable conclusions with [belief] refs; pointers to docs/)
## History                  (dated log; compacted; never contains boxes)
```
Open boxes live **only** under `### Backlog`; a `- [ ]` anywhere else is a lint error. This single rule is what makes "file order = priority" true and lets the extractor read a box's section context deterministically.

### 2.2 Box grammar
```
- [ ] **<ID>** [<class>] <imperative task text, one sentence>
      · done when: <test command | file+field | tick verdict text | row PASS>
      · gate: <ID, ID | none>        · inputs: `<path>` `<path>`
      · tier: luna|terra|sol|haiku|sonnet|opus (optional)   · owner: <track|session> (optional)
      inference only: · model · build · harness · metric(dir) · rule · region · est <N s from <run>>
      · stop rule: <question / effect vs error / checkpoints / stop-on-answer / futility>
```
- **ID** `<DOMAIN>-<n>[.<sub>]`, unique in the repo, never reused (authoring guide `:19-21`); `duplicate_task_scan.py` guards. The `**ID**` prefix stays the anchor `flip_checkbox`/`publish_row` already use.
- **Class** one of `non-inference | inference | operator-decision | roll-up | blocked-external` — explicit tag wins over regex (`task_lint` usage: "an explicit [class] tag … wins").
- **Task text is the identity** (doctrine); the first line is immutable once published to rowflow or dispatched; refinement = new ID with `supersedes: <ID>` or intake's `previous_task_text` path (`SKILL.md:640`).
- **done when** mandatory for `non-inference`/`inference`; must be mechanically checkable (verifier §DESIGN 2.5). A box without it is a `roll-up` or a `NEEDS-OWNER` draft.
- **gate** box or row IDs only; prose prerequisites are a lint failure (field d). `none` is explicit.
- **inputs** paths that must exist at dispatch (field f); `/mnt/raid0/llm/tmp/*` allowed only with a `**Scratch**` root.
- **tier** optional hint; default by class (DESIGN §2.4).
- **owner** optional; default = the track's owner session; needed only when a box is adopted across tracks (guide `:94-96`).
- **States** — marker + annotation, never prose:
  `[ ]` open · `[x] ✅ date [belief: …] <verdict>` done · `[ ] … · gate: X` blocked (derived, not a marker) · `[ ] ❄ frozen until: <event|ID>` frozen (skipped by dispatch, counted separately) · `[roll-up]` parent (never dispatched, auto-ticks when children done) · partial = parent stays `[ ]`, child `**ID.p1**` added by `/log` (SESSION_LIFECYCLE bullet 4). The `[~] [>] [!]` markers are retired (invisible to `backlog_row_check:209`).
- **Ordering** within `### Backlog` is priority: top box is next. New boxes append at the bottom unless the author states a rank. Cross-track priority comes from `backlog-priority.json` row rank; no per-box numeric rank field.

### 2.3 Size and splitting
Limits (lint): `### Backlog` ≤ 40 open boxes per track; a box ≤ 16 continuation lines (p95 today, guide `:64`) else `[roll-up]` + children; file ≤ 2,500 lines (today's p50) with `## History` compacted first; a handoff over 4,000 lines or with > 3 tracks is split by track into its own file with a new row (guide `:51-85` promote rules). Fold back when ≤ 2 open boxes (guide `:81`).

## 3. Lifecycle operations — one owner, one tool, one gate

| Op | Who | Tool | Gate |
|---|---|---|---|
| Create | owning session, or intake Stage 4 | `scripts/handoffs/new_handoff.py <slug> --row <ID>` (new; renders §2.1 from the intake stub template `SKILL.md:715`) | `index_state --check`: header keys, one row, `## Dispatch contract` present |
| Append box (intake) | intake Stage 4 (operator-approved plan) | `handoff_box.py add --file --track --after <ID>\|end` with the §2.2 fields (new; replaces hand edits "at the exact section" `SKILL.md:626`) | `task_lint dispatch` on the new box; `[ ]` only under `### Backlog` |
| Append box (wrap-up discovered / out-of-scope finding) | the session that found it, in the owning handoff | same tool; class + done-when required or `NEEDS-OWNER` | same; wrap-up Step 2 derived-actionables gate (`wrap-up.md:404`) |
| Modify / split | owning session | `handoff_box.py split <ID>` → `[roll-up]` + children; `refine <ID>` requires `previous_task_text` | text-identity check: a changed first line on a rowflow-bound box is refused (`publish_row` `handoff_task`) |
| Tick with evidence | the agent whose task it is (INVARIANTS 9); dispatcher under owning identity | `churn/wrapup.py` (text-resolved, belief required `:123-151`) — `flip_checkbox.py` becomes its internal primitive and adopts the same suffix | wrap-up flip-count + belief-capture gates; `belief_capture_check.py` pre-commit (today advisory `pre-commit.extras:48`) → enforce for result ticks |
| Block / unblock | owning session | `handoff_box.py gate <ID> --add/--remove <ID>`; blocked is derived from open gates, no marker | `index_state` BAD GATE (`guide:115`); prose-prereq lint d |
| Freeze | operator or owning session on operator ruling | `handoff_box.py freeze <ID\|track\|file> --until <event>` writes `❄ frozen until:` / `**Status**: FROZEN` | dispatcher `select.py` skips; `index_state` counts `frozen` separately (new bucket) |
| Compact / prune history | wrap-up sweep (operator-invoked `/wrap-up`, CLAUDE.md "Wrap-up cadence") | `handoff_compact.py`: ticked boxes older than 30 d → one summary line per track in `### Done`, prose → `## History` or `handoffs/archived/<slug>-history-<date>.md` | `check_commit_hygiene.py` bloat guard (`pre-commit:72`); `closure_audit.py` before deleting ticked boxes |
| Complete + extract findings | owning session | wrap-up Step 2 (`:335`): findings → `docs/` or wiki, `git mv` to `completed/`, delete row | `index_state --check` prune candidate only via `prune.candidate` (`index_state:330-358`), never `open == 0` (`wrap-up.md:465`) |
| Index row | owning session applies; subagents prepare (ruling (b) 2026-08-16) | `index_state.py` regen | `--check` exit 0 before commit |
| Ownership | **belongs to the HANDOFF; sessions are replaceable** (operator 2026-11-20, "Sessions don't live forever") | `handoff_sessions.py`: a handoff with pending proposals (or an ownerless run-end) and no live owner gets a NEW owner session via the unowned-handoff path (`start_handoff`), first prompt = the pending work (`OWNER-SPAWNED <slug> handoff=<f> reason=proposals-pending`); a parked/suspended owner is woken by the `proposals-pending` event, never replaced | never for a `holds.yaml`-held handoff; width cap + token budget; ≤ 1 spawn per handoff per day; refused spawn → pipeline-mgmt review queue |
| Review proposals | the handoff's owner session (spawned if none) | wrap-up Step 2 "Proposals": accept / edit / reject (`handoff_box.py reject`); one `proposals-pending` turn per handoff per day | back-pressure: ≤ max(8, 20 %) pending per handoff; > 14 d pending → `[declined: taskflow-expiry]` by `index_regen.py` |

## 4. Compiled view (generated, never hand-written)

`scripts/handoffs/index_state.py` already emits `.index-state.json` (per-handoff counts, tracks, gates) and `backlog_priority.py` emits row rank. Add one generated artefact, `handoffs/active/.box-index.json` (schema `epyc.box-index.v1`), produced by `index_state.py` from the handoff files + `backlog-priority.json` + `holds.yaml`:

```
{ "<ID>": { "file", "line" (hint), "track", "text_sha" (identity), "text", "class", "done_when",
            "gate": [...], "gate_open": bool, "inputs": [...], "inputs_missing": [...], "tier",
            "state": open|done|frozen|rollup|needs-owner, "lint": {ok, fails:[...]},
            "row": "RTG-58", "row_rank": 12, "pos_in_backlog": 3, "frozen_until", "ticked": {date, belief} } }
```
Consumers: the dispatcher (`select.py` reads it instead of parsing files; DESIGN §2.1), the dashboard (`open/blocked/frozen/needs-owner` counts replace today's `classify()` heuristics), `stale_next_action.py`, `verdict_count.py`, rowflow `publish_row` (resolves `handoff_task` by ID and checks `text_sha`). Also generated: the `**Size**` header line, the `## Findings` belief-ref list (from the ledger), and the row rollup in `master-handoff-index.md` (already generated). Hand-written stays: title, Status sentence, dispatch contract, boxes, findings prose.

## 5. Propagation

| Target | Change | Path class |
|---|---|---|
| `docs/guides/agent-workflows/handoff-index-authoring.md` | add §2 anatomy + box grammar + size limits; replace "promote or inline" line counts with the lint limits | agent-editable docs |
| `agents/commands/wrap-up.md` Step 2 | new boxes via `handoff_box.py add` only; tick via `wrapup.py`; flip-count gate reads `.box-index.json`; derived-actionables gate requires class + done-when | agent-editable (commands) — verify not in `human_only_paths.yaml` |
| `.claude/skills/research-intake/SKILL.md` Stage 3/4 | "verbatim task lines" become §2.2 records; `handoffs_updated` records IDs; stub template → `new_handoff.py`; refinement keeps `previous_task_text` | skill file, agent-editable |
| `scripts/handoffs/index_state.py` | emit `.box-index.json`; `frozen` bucket; `[ ]` outside `### Backlog` = error; header-key check; task_lint a/f hard-fail **on boxes touched in the commit** (diff-scoped) | code |
| `scripts/handoffs/task_lint.py` | `dispatch` mode (parsed fields or missing list); class tag grammar; retire `[~][>][!]` | code |
| `scripts/coordination/flip_checkbox.py`, `churn/wrapup.py`, `worker_checkpoint.py` | one suffix format `✅ date [belief: …] <verdict>`; `flip_checkbox` used only through `wrapup.py`/`/log` | code |
| `scripts/coordination/rowflow/publish_row.py` | `handoff_task` = `file.md:<ID>` only; refuse when `text_sha` differs from the row's recorded one | code |
| `scripts/hooks/pre-commit.extras` | `belief_capture_check` strict for result ticks; box-placement check | hooks (check `human_only_paths.yaml` — hooks dir is not listed in the memory note, verify) |
| Dispatcher (`DESIGN.md`) | `select.py`/`extract.py` read `.box-index.json`; translation proposals become `NEEDS-OWNER` children via `handoff_box.py` | code |
| **Human-only** (`check_trust_boundary_edit.sh`, `coordination/session-bus/human_only_paths.yaml`): `agents/shared/SESSION_LIFECYCLE.md` (Two axioms: retire `[~][>][!]`, name the suffix format, cite `.box-index.json`), `agents/shared/OPERATING_CONSTRAINTS.md` (Dispatching Backlog Work: identity = `text_sha` of the first line, `.box-index.json` as the screener's source), `agents/shared/INVARIANTS.md` if invariant 9 wording changes, `CLAUDE.md` Handoff Workflow paragraph | **operator ratify script** — one apply-tested single-line command (`scripts/operator/ratify_*.sh` pattern, `ratification_receipt.py`) |

## 6. Migration

Scope: 1,398 open boxes in 33 active files today (2,808 counted on 11-02 across active+blocked before the folds); ~24–30% lint-OK.

1. **Enforce on touched boxes only (day 1).** Diff-scoped lint in `index_state --check`: a commit that adds or edits an open box must satisfy §2.2 or tag `NEEDS-OWNER`; untouched legacy boxes never block. Zero migration cost; stops the debt growing.
2. **Bulk mechanical pass (day 1–2, scripted, one commit per file, owner-reviewed diff).** Safe transforms only: move every `- [ ]` under its track's `### Backlog` preserving relative order; add `[class]` where `task_lint` classifies by *deliverable* (not advisory regex) — 1,100 of 2,808 were classified `deliverable` in the audit sample; rewrite `❄ FROZEN … — resume only once X` prefixes into `❄ frozen until: X`; convert child boxes reading "BLOCKED on <ID>" into `· gate: <ID>`; tag `[roll-up]` on boxes with nested children (70 of 1,635 top-level, guide `:65`); mark dangling `inputs` (`f`, 60 of 404 sampled) with `· inputs-missing:`. No text-line edits, so identities hold. Cost ≈ 1 Claude Sonnet day + 33 owner reviews of ~15 min.
3. **LLM-proposed rewrites for owners (week 1–2).** For boxes failing a/e/s (no done-when, oversized, no stop rule): one luna/haiku turn per box proposes `done when`, a split, or a stop rule, written as a `NEEDS-OWNER` child under the box (never edits the first line). Owners accept by deleting the tag; the dispatcher never runs an un-accepted proposal. Estimate: ~900 boxes × ~30 k uncached tokens ≈ 30 M tokens (< 1 day of this week's Codex burn, which was 560 M/24 h) plus ~900 owner decisions at ~1 min = 15 h spread across owning sessions' wrap-ups.
4. **Order by backlog priority.** Steps 2–3 run file by file in `backlog-priority.json` row order, top rows first; within a file, `### Backlog` top first. Two distinct thresholds (Stage C, 2026-11-20): **back-pressure** is per handoff — a file stops receiving proposals while it holds ≥ max(8, 20 % of its dispatchable+pending) pending proposals, and the run moves on to the next file (owners are asked by a once-a-day `proposals-pending` dispatcher event; ownerless files go to the pipeline-mgmt review queue; proposals pending > 14 d expire to `## History`). **Completion** of the pass is global — it is done when `needs-owner` + `lint-fail` boxes in the top-10 rows fall below 20 % of selectable boxes (DESIGN §2.6 skip-reason histogram).
5. **Compaction (week 2).** `handoff_compact.py` on the 9 files over 4,000 lines; `closure_audit.py` first.

## 7. Rollout and open questions

**Stage A (1 day):** `task_lint dispatch` mode, `.box-index.json` emitter, diff-scoped a/f gate, `handoff_box.py add/gate/freeze`, tests in `tests/handoffs/`. Canary: `index_state --check` exit 0 on origin/main; `.box-index.json` covers 100% of open boxes with `lint.ok` matching `task_lint report` within 1%.
**Stage B (2 days):** mechanical pass on the top-10 rows; wrap-up/intake skill text updated; `wrapup.py` suffix unification; dispatcher Stage 1 (DESIGN) starts reading `.box-index.json`. Canary: lint-OK fraction in those files ≥ 45% (from 24%); zero `[ ]` outside `### Backlog` in them.
**Stage C (1–2 weeks):** LLM proposals, compaction, ratify package for the human-only docs, remaining rows.

**Open questions for the operator**
1. Retire `[~] [>] [!]` markers and `flip_checkbox`'s `(note)` suffix in favour of one format — yes/no? (touches `SESSION_LIFECYCLE.md`, human-only.)
2. May the bulk pass **move** boxes within a file (into `### Backlog`) without owner review per file, given text lines are unchanged?
3. Is a `**Holds**` header plus `holds.yaml` acceptable as the single operator-exclusion surface, replacing hold prose in Status lines?
4. Hard limits: 40 open boxes per track, 2,500 lines per file, 16 continuation lines per box — accept, or set different numbers?
5. Should `done when` be mandatory for intake-derived boxes at Stage 4 (would slow intake) or allowed as `NEEDS-OWNER` drafts?
6. Who reviews LLM-proposed rewrites: owning sessions at wrap-up, or a one-off operator sweep on the top-10 rows?

## Operator decisions (2026-11-19)
1. Markers: retire [~] [>] [!]; only [ ] / [x] plus annotations; one tick suffix `✅ date [belief] verdict`, written only by wrapup.py. Human-only doc edits go through a ratify script the operator runs.
2. Mechanical migration moves (Backlog placement, class tags, frozen/roll-up marks, no first-line edits) land directly; each owning session gets a diff summary and may revert.
3. Holds: a `**Holds**` header per handoff plus one holds.yaml form the single exclusion source. Registry gates and rowflow prefixes become derived from it.
4. Limits (looser): ≤60 open boxes per track, ≤24 continuation lines per box, ≤4,000 lines per handoff; split by track past 6,000 lines.
5. `done when` is REQUIRED on new or touched boxes (diff-scoped lint fails). Legacy untouched boxes only warn.
6. LLM-proposed rewrites land as NEEDS-OWNER children; the owning session accepts or edits them at its wrap-ups.

## Indexes (added 2026-11-19, after Stage A)

### I.1 What exists and who touches it

| Layer | Hand-written? | Writers | Readers | Evidence |
|---|---|---|---|---|
| `master-handoff-index.md` (144 lines) | yes: domain table + operator decision queue; rollup block generated | wrap-up Step 3 (operator decisions with `Open since`), `index_state.py` regen | humans; `index_state --check` ("stale generated block") | `wrap-up.md:411-470`; master `:17-49` |
| 6 domain indices (30 rows total, 19 `Deps` edges, 16 rows with empty Deps, 0 over-long cells) | yes: `ID \| Track \| Handoff \| Next action \| Deps` | owning session only (ruling (b) 2026-08-16); intake Stage 4 adds a row per new stub (`SKILL.md:629-636`) | `index_state.py` (ownership, links, Deps → `.index-state`/`.index-graph`), `backlog_priority.py` (row rank), `stale_next_action.py` (reporter; 6 of 30 rows stale today), dashboard `handoff_parser.py`, `backlog_gen.py` | `handoff-index-authoring.md:6-45`, `index_state.py:135-137` |
| `backlog-priority.json` (+ `.override.json`, `backlog_priority_curated.json`) | generated from boxes + curated table | `backlog_priority.py` (curated entries hand-maintained) | `backlog_gen.py`/`handoff_sessions.py` (slot order `:1271-1280`), `box_index.py` (`row_rank`), inference-backlog-scheduling skill, dashboard — 11 files | `backlog_priority.py` docstring |
| `.index-state.json` / `.index-graph.json` | generated | `index_state.py` only (regen under the wrap-up lease) | 13 / 15 files: dashboard `panels.py`, `server.py`, `refresh_hub_view.sh`; `backlog_row_check.py:610-668` (readiness/blocked_by), `premise_screener.py`, `compute_ready_daemon.py`, `worker_checkpoint.py`, `churn/wrapup.py`, `session_bus_coordinator.py`, `check_lane_worktree.py`, `index_regen.py` | grep, this audit |
| `.box-index.json` (Stage A) | generated | `index_state.py` → `box_index.py` | dispatcher (DESIGN §2.1), nothing else yet | `ba3adabf1` |
| `CURRENT-CAMPAIGN.md` (303 lines) | yes: dated posture blocks, newest on top | mains at wrap-up (22 commits since 10-01); read by 10 scripts only as a path/pointer | humans; `prior_check.py`, timeline/duplicate scanners | `CURRENT-CAMPAIGN.md:1-14` |

Hooks: none gates the indices directly; `index_state --check` is run by sessions (wrap-up Step 3) and `check_commit_hygiene.py` bloat-guards handoff files. `human_only_paths.yaml` lists no index or handoff path, so every index layer is agent-editable; only the rules about them (`SESSION_LIFECYCLE.md`, `OPERATING_CONSTRAINTS.md`, `CLAUDE.md` § Handoff Workflow) are human-only.

### I.2 Decisions

**(a) Which layers earn their keep.** Keep as *hand-written*: the master router's domain table and operator decision queue (the only surface where a human-choice item is declared, `wrap-up.md:430`), and `CURRENT-CAMPAIGN.md` (operational posture, not backlog). Keep as *generated*: `.index-state.json`, `.index-graph.json`, `backlog-priority.json`, `.box-index.json` — they are already derived and have 11–15 readers each. **Demote the six domain indices from source to view**: every cell they carry is now derivable — `Handoff` from the file, `Track` from the header title / `**Row**`, `Next action` from the top dispatchable box in `.box-index.json` (`pos_in_backlog = 1`, `state = open`, `gate_open = false`), `Deps` from the union of that handoff's `gate:` row refs plus the header `**Depends on**`, and ordering from `backlog-priority.json`. The 30 hand-written rows cost a lease-guarded regen at every wrap-up and still rot (6/30 stale today, 34.5% anchor rot historically, `OPERATING_CONSTRAINTS` → Dispatching Backlog Work).

**(b) Generate the rows — yes, with two hand-written residues.** Generated: `Handoff`, `Next action`, `Deps`, rank. Hand-written residue, moved into the handoff header rather than the index: the **row id** (`**Row**: RTG-58`, already present in 16 files as `**Parent index**`) and the **domain** (`**Domain**: routing`), so ownership stays a one-line declaration in the owned file and "exactly one index" becomes a lint on headers instead of a cross-file hunt. The owning-session-applies rule survives unchanged: the owning session edits its own header; nobody edits a generated table. Until Stage C the generated `Next action` is emitted beside the hand-written one (`Next action (generated)`), so `stale_next_action.py` can measure agreement before the hand column is dropped.

**(c) Standard row format and placement.** `| ID | Handoff | Next action | Deps | Rank | Open/Blocked/Frozen | Last advanced |`, one row per active handoff, grouped by `**Domain**`, written between `<!-- generated:start -->`/`<!-- generated:end -->` markers in each domain index by `index_state.py` (same mechanism as the master rollup block). `Next action` = `**<ID>** <first 110 chars of box text>` of the top dispatchable box, or `BLOCKED: <gate ids>` / `FROZEN until <event>` / `NEEDS-OWNER: n boxes` when none is dispatchable. `## Cross-domain` and `## Reporting` sections stay hand-written prose. The master index keeps its two hand-written tables and gains nothing.

**(d) Migration and Stage B/C interaction.** Stage B (mechanical pass) adds `**Row**` and `**Domain**` headers to the 33 files from the current index rows (a scripted inverse of today's `rows → handoff` map in `.index-state.json`); `index_state.py` emits the generated table beside the hand-written one. Stage C: once `stale_next_action` shows generated ≥ hand on the top-10 rows for a week, drop the hand-written rows, make a hand-written row a `--check` error, and rewrite `handoff-index-authoring.md` §"The row contract" to the header contract. `backlog_row_check.py`, `premise_screener.py` and the dashboard keep reading `.index-state`/`.index-graph` unchanged (their schema does not change; `next_action` is just sourced differently). Dependency on Stage A fixes: generated `Next action` needs the Stage A ID-regex fix (today 1,101 of 1,409 box IDs are not recognised) and the fence/History exclusion, or it will name boxes that are not real tasks.

**(e) Human-only targets.** `agents/shared/SESSION_LIFECYCLE.md` (checkbox axiom wording cites the dashboard; add "and the generated row"), `agents/shared/OPERATING_CONSTRAINTS.md` (Dispatching Backlog Work: the screener's source becomes `.box-index.json`; ruling (b) wording "adding, deleting or re-pointing a row" becomes "editing the header `**Row**`/`**Domain**`"), `CLAUDE.md` § Handoff Workflow ("one thin row per handoff … hand-written" → generated). One ratify package, shipped with Stage C, not before. `agents/commands/wrap-up.md` Step 3, `handoff-index-authoring.md`, the research-intake skill item 4 and `dashboard/handoff_parser.py` are agent-editable and change in Stage B/C.

**Open questions (indexes):** (1) keep six domain files or one generated `BACKLOG-INDEX.md` with domain sections (fewer files, one lease)? (2) may the generated `Next action` replace the hand cell for rows whose owning session has not wrapped up in 14 days, before Stage C? (3) does `CURRENT-CAMPAIGN.md` stay a free-form log, or get a dated-block schema and a 30-day compaction like `## History`?

## AK audit items absorbed (2026-11-19, `/mnt/raid0/llm/tmp/autokernel-session-audit-20261119.md` §B)

- **B4 → §2.1 header + decision 3.** `holds.yaml` entries carry `id`, `targets` (handoffs/rows/boxes/files) **and `scope: loop-launch | all-rows | boxes`**. `loop-launch` holds only the handoff's agent sessions (dispatcher/taskflow and AK loop spawns); `all-rows` also refuses rowflow rows whose `handoff_task` points into the handoff; a row is admitted by **its own `owner`** against the hold's targets, never by the handoff's registry owner (today `publish_row.check_operator_gate` :322-345 keys on the session that owns the handoff — eight AK rows refused 11-19T08:16Z). `box_index.load_holds` already reads `targets`; add `scope`.
- **B10 → §4 / I.2(a).** Generated artefacts (`.index-state.json`, `.index-graph.json`, `.box-index.json`, the master rollup block, the Stage C generated rows) have **one writer**: the hub refresh / post-merge regen, not sessions. Measured: 360 commits to `.index-state.json` since 11-10 from ≥5 sessions, the push-race class in audit §2.9. Stage B: `index_state.py --check` downgrades "stale generated block/file" to a warning for a commit that does not touch them and `.box-index.json` is gitignored (regenerated on read, 3.6 s); Stage C: the regen commit comes from the hub job only, and wrap-up Step 3 drops the `index_state.py` regen step (keeps `--check`).
- **B11 → §3 gates / decision 5.** The diff-scoped rule extends from boxes to **index rows**: `PROSE` (>140 chars, `index_state.py:1113`), `Deps`, and link checks hard-fail only for rows the commit touches; pre-existing defects warn. Stage B, same `added_lines` mechanism as the box gate (after its Stage A S1 fix).
- **B13 → §3 "Tick with evidence".** `wrapup.py` reads the box's `done when` at tick time; when it names a test command / file+field it runs or checks it; when it names an artifact class the tick's evidence must name an artifact of that class, else refuse with the box text. Stage C (depends on `done when` adoption); DESIGN §2.5 carries the dispatcher side.
- **B5/C5 (code root).** Not a handoff-standard item, but the standard's tools (`handoff_box.py`, `task_lint.py`, `box_index.py`) join `INSTALL.manifest` so sessions run the hub-view copy and print `tool-commit <sha>`; see `AK-REQS-FIXES.md` F5.
