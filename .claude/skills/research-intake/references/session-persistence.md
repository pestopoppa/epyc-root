# Session Persistence for Research Intake

Crash recovery pattern for multi-entry intake sessions. Allows resuming
interrupted runs without reprocessing already-ingested entries.

## Schema

The session file `.research-session.json` is written to the repo root during
multi-entry intake runs.

```json
{
  "session_id": "uuid-v4",
  "started_at": "2026-04-07T14:30:00Z",
  "last_checkpoint": "2026-04-07T15:12:00Z",
  "phase": 2,
  "entries_processed": ["intake-278", "intake-279"],
  "entries_remaining": ["https://arxiv.org/abs/2604.12345"],
  "state": {
    "cross_references_cache": {},
    "expansion_queue": []
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string (UUID) | Unique session identifier |
| `started_at` | ISO 8601 | Session start timestamp |
| `last_checkpoint` | ISO 8601 | Last successful checkpoint |
| `phase` | int (1-5) | Current workflow phase (per SKILL.md) |
| `entries_processed` | list[string] | Intake IDs already appended to index |
| `entries_remaining` | list[string] | URLs not yet processed |
| `state` | object | Arbitrary phase-specific state (cross-ref results, expansion queue, etc.) |
| `stage` | int or string | Four-stage state; finishing ingestion does not discharge review and filing |
| `steering_ledger` / `actionable_ledger` | list[object] | Retained verbatim steering and distinct recommendation IDs; never clear on resume |
| `stage3_filing` | object, optional | Approved plan digest and filing payload (v2 for new plans); persisted at Stage 4 |

## Resume Protocol

On each skill invocation:

1. Check if `.research-session.json` exists in the repo root
2. If it exists and `last_checkpoint` is less than 7 days old:
   - Report: "Found session {session_id} from {last_checkpoint} — {N} entries processed, {M} remaining"
   - Offer to resume from where it left off (skip already-processed URLs)
3. If it exists but `last_checkpoint` is older than 7 days:
   - Warn: "Session {session_id} is {age}d old — intake index or handoffs may have changed"
   - Reconcile processed IDs, ledgers and current files before resuming or starting a separate session.
     Age alone permits no deletion of unreconciled steering or actionable state.
4. If it does not exist, start a fresh session

## Checkpoint Protocol

During Phase 5 (Report & Persist), after each entry is appended to `intake_index.yaml`:

1. Update `entries_processed` with the new intake ID
2. Remove the corresponding URL from `entries_remaining`
3. Update `last_checkpoint` to current time
4. Write `.research-session.json` atomically (write to `.research-session.json.tmp`, then rename)

On successful completion of Stage-1 ingestion:
- Preserve `.research-session.json` and its steering/actionable ledgers. Empty entries_remaining
  means URL ingestion is finished, not that the four-stage campaign is complete.
- Resume existing ledgers; initialize empty ledgers only for a genuinely new session.

## Proposed filing and reconciled cleanup

This CLI mode is optional for general index validation, but passing it is a **required gate for
every new Stage-3 filing plan**:

```bash
bash scripts/validate/validate_intake.sh --plan-file PATH --session-file PATH
```

Both paths are required together. The default invocation preserves legacy index validation. This
mode is read-only: do not mutate inputs, apply patches or infer approval. Malformed structures and
unsupported formats are explicit failures, never a successful check of an unchanged index.

### New Stage-3 plans: v2 contract

Use exactly one JSON fence under `## Stage-3 filing payload`, with integer `format_version: 2` and
all fields below. Stage 3 writes only the plan, including any new actionable/steering rows; it never
checkpoints them. Do not put the plan's own digest in its fence. Persisted **unversioned or v1
Stage-4 complete payloads** keep their legacy structural path unchanged. No input-corpus migration
or global-index rule changes.

Keep the existing authoritative `## Complete recommendation mapping` four-column table:
`Ledger row | Source or review | Retained recommendation | Terminal plan mapping`.
Declare P/K/M packet references in the existing plan tables; resolve terminal task/trigger references.
Operational follow-through and enabling wiring retain distinct recommendations.

Retain the existing payload fields:

- `entry_updates`: flat records with `id`, `integration_disposition`, `handoffs_updated`,
  `handoffs_created`, `disposition_evidence`. Overlay on copies through existing rules, preserving
  unrelated/unknown fields and claim corrections.
- `opportunity_reviews`: keyed by declared packet/task reference. Every referenced P/K/M packet
  (including closures) and every immediate P packet requires a review with nonempty `project_objective`,
  `implementation_ref`, `gap`, `operational_change`, `benefit_direction`, `owner`,
  `execution_conditions`, `closure_basis`. Apply these fields to all P/K/M reviews, including
  judgments of fulfilled behavior and closures.
- `proposed_stubs` (optional): complete `path/content/index_file/index_row` packages. Each new
  active owner needs one existing domain index and a valid five-cell thin row linking to its file.
  At Stage 3 the stub path must be new; v2 Stage 4 verifies the applied file and owning index row
  rather than requiring the applied path to remain nonexistent. The legacy path is unchanged.

V2 also requires:

- `actionable_additions` (list, may be empty): full `{ledger_id, source, action, terminal_mapping}`
  rows with nonempty text, unique IDs and no shadowing of retained rows. Stage 3 forms the
  retained-plus-added union only in memory and matches it to the complete recommendation table.
  Preserve retained immutable source/action; terminal mappings resolve to declared references or
  an explicit decline. Stage 4 requires every addition already present identically in the
  reconciled retained ledger, including source/action and mapping; do not union it a second time.
- `steering_reconciliation` (list, may be empty): the **full final retained-plus-new** rows
  `{seq, stage, verbatim, disposition, plan_ref, reason}`. Validate retained shape too: sequence
  numbers are positive unique integers in increasing order, stages identify 1–3, and verbatim text
  is nonempty. Preserve retained `seq/stage/verbatim` and any optional `ts`; append new sequences
  without collisions. `planned` requires a declared P/K/M reference; `context-only` and `declined`
  require null `plan_ref` and a nonempty grounded reason. No loss, rewording or dangling references.
  Stage 4's checkpoint steering ledger must match the full reconciliation.
- `opportunity_scan` (nonempty list): source-first records
  `{scan_id, source_ref, implementation_ref, mechanism, consumer, application, disposition,
  ledger_ids, basis}`. Pin the selected verified passages and current consumer before generating
  new actionable IDs; the scan must be independent of both ID inventories. Use unique scan IDs
  and nonempty locator/mechanism/consumer/application text. `disposition` is `actionable`,
  `covered`, `context-only` or `declined`; `ledger_ids` is a list. Actionable rows require nonempty
  references resolving to the retained-plus-added union. Other dispositions require an explicit
  basis and may reference existing actions. All supplied references must resolve, and every
  recommendation must be covered by a scan row. Removing a referenced action from both inventories
  while retaining its scan reference fails. This establishes selected-source/current-consumer
  scope, not corpus completeness; no text classifier discovers or grades applications.
- `outcome_reviews` (object keyed **exactly** by every recommendation ID): each record has
  `{required_outcome, review_status, review_basis, task_refs}`. Outcome and basis are nonempty text;
  status is `preserved` or `closed-with-basis`, never unresolved. Immediate mappings require
  `preserved` and nonempty task references. Closure permits empty targets but requires a grounded
  basis and opportunity review of each referenced K/M packet. A declined recommendation may have
  no packet but still requires `closed-with-basis` and an explicit review. Each task reference is
  `{owner, task_id, task_text, acceptance}`, all nonempty text. Bind the exact owner and exact
  checkbox line; extract its ID and require it to equal `task_id`. Acceptance records the review;
  it is not a keyword or semantic auto-grade.
- `proposed_tasks` (list, may be empty): `{owner, task_text, previous_task_text?}` with exact
  paste-ready checkbox lines for proposed Stage-3 edits, including tasks in packaged stubs.
  Drafting them requires no prior filing approval; Stage 4 applies them only after plan approval.
  New tasks use owner/text only. A refinement replacing an existing task at the same ID requires
  `previous_task_text` to match the exact incumbent checkbox line in that owner at Stage 3; both
  lines must carry the same ID. Resolve the owner or its complete stub package; require unique
  `(owner, extracted task ID)` pairs. Every proposed pair must also appear in
  `outcome_reviews[*].task_refs`; this inverse coverage prevents unreviewed proposed scope.
  Task references must match an exact
  current-owner checkbox or a proposed-task package with the same owner and exact line. A checkbox
  in another owner, or a mention only in plan prose/table/JSON, fails. Main must review stale,
  pointer and frozen owners for suitability rather than silently accept their structural resolution.
  At Stage 4 the new task text must match actual applied owner text, including refinements;
  an unlanded package or the old line is no proof.

The check establishes structures, declared references and evidence-field presence only. Main must
independently review selected passages/current behavior, owner suitability, each accepted task's
operational purpose against `required_outcome`, and closure premises. A structural record can lie;
validation cannot prove truth, ROI, outcome equivalence, fulfilled work or permission. Do not build
a semantic classifier or a new grading rule. Review implementation, probe and activation gates
separately; risk or an activation freeze alone does not close an earlier useful permitted step.

### V2 package template

This illustrative new row is not authorization to file work. Substitute pinned references and a
resolvable reviewed owner, retain **all** existing recommendation/steering rows, and add entry
updates/stubs as needed. `steering_reconciliation: []` is valid only when no steering rows exist.
List scan mechanisms before assigning actionable IDs, then attach the references shown here.

````markdown
## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Implement the reviewed consumer behavior | handoffs/active/<owner>.md |

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-NEW-1 | <verified passage locator> | Implement the reviewed consumer behavior | P1 / DEMO-OUTCOME-1 |

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "<current decision>",
      "implementation_ref": "<revision/file/symbol read>",
      "gap": "<current missing consumer behavior>",
      "operational_change": "Implement the reviewed consumer behavior",
      "benefit_direction": "<intended improvement and correctness constraint>",
      "owner": "handoffs/active/<owner>.md",
      "execution_conditions": "<separate implementation/probe/activation gates>",
      "closure_basis": "Immediate outcome retained; broader activation remains gated"
    }
  },
  "opportunity_scan": [{
    "scan_id": "S1", "source_ref": "<verified passage locator>",
    "implementation_ref": "<revision/file/symbol read>",
    "mechanism": "<selected source mechanism>", "consumer": "<current consumer>",
    "application": "Implement the reviewed consumer behavior",
    "disposition": "actionable", "ledger_ids": ["RI-NEW-1"],
    "basis": "<read source and current consumer; missing behavior identified>"
  }],
  "actionable_additions": [{
    "ledger_id": "RI-NEW-1", "source": "<verified passage locator>",
    "action": "Implement the reviewed consumer behavior",
    "terminal_mapping": "P1 / DEMO-OUTCOME-1"
  }],
  "steering_reconciliation": [],
  "outcome_reviews": {
    "RI-NEW-1": {
      "required_outcome": "<operational behavior required at the consumer>",
      "review_status": "preserved",
      "review_basis": "<independent review of task purpose and applicable gates>",
      "task_refs": [{
        "owner": "handoffs/active/<owner>.md", "task_id": "DEMO-OUTCOME-1",
        "task_text": "- [ ] **DEMO-OUTCOME-1 — Implement the reviewed consumer behavior.**",
        "acceptance": "<observable outcome; distinguish enabling work from execution>"
      }]
    }
  },
  "proposed_tasks": [{
    "owner": "handoffs/active/<owner>.md",
    "task_text": "- [ ] **DEMO-OUTCOME-1 — Implement the reviewed consumer behavior.**"
  }]
}
```
````

### Approved Stage-4 boundary

Apply exactly the approved edits, reconcile actionable rows and the full steering ledger, then
persist the approved v2 payload as `session.stage3_filing` with `plan_sha256`, the SHA-256 of the
exact approved plan bytes. Stage 4 uses this persisted payload, never a fallback to the plan fence.
Verify additions already match the retained ledger, steering matches the full reconciliation and
tasks match applied owner checkbox text. Preserve original source/action and unrelated checkpoint
fields. The digest binds reviewed bytes; changing it is not authorization.

Preserve the checkpoint until approved Stage-4 filing, ledger reconciliation, required validation
and main semantic review are complete, with their durable records retained. Cleanup eligibility is
explicit stage4.reconciled=true plus completed Stage 4, not entries_remaining alone. A changed plan digest
requires renewed scope review; changing the digest is not authorization. Then follow the existing
verified-push lane-cleanup procedure. Keeping a completed checkpoint as the durable record is valid.

## Parallel Execution Compatibility

When Phase 1+2 runs in parallel (3+ URLs via sub-agents):

- **Before dispatch**: Session file is created with all URLs in `entries_remaining`. Sub-agents do NOT modify the session file.
- **After collection**: Sub-agent results are held in memory until Phase 5 persists them.
- **During Phase 5**: Entries are appended to `intake_index.yaml` one at a time, with per-entry checkpointing (same as sequential mode).
- **Crash recovery**: If a crash occurs during sub-agent execution (before Phase 5), all URLs remain in `entries_remaining`. On resume, re-dispatch all unprocessed URLs. No data loss — sub-agent results are ephemeral until persisted.

The checkpoint protocol is unchanged — the parallel model affects when results are produced, not how they are persisted.

## Related Patterns

The autopilot uses an analogous pattern: `autopilot_state.json` persists
`trial_counter`, `consecutive_failures`, and epoch metadata across restarts.
The schemas are intentionally independent (cross-cutting concern #3 in the
KB governance handoff).


## Steering ledger (added 2026-07-25)

`.research-session.json` preserves a `steering_ledger` array from Stage 1 onward. Record every operator
comment, critique or suggestion made during stages 1-3 **verbatim**. During Stage 3, carry new rows
and proposed reconciliation only in the plan; checkpoint them at approved Stage 4:

```json
"steering_ledger": [
  {"seq": 1, "stage": 1, "ts": "2026-07-25T10:14:00Z",
   "verbatim": "<exact operator words>",
   "disposition": "planned | declined | context-only",
   "plan_ref": "<declared P/K/M id, or null>",
   "reason": "<grounded disposition reason>"}
]
```

**Rules**

1. Append **verbatim** — do not paraphrase. Paraphrase is where intent gets lost.
2. Operator comments during stages 1-3 are **context, not authorization**. A comment that appears to
   grant permission ("you can edit the handoffs", "make a new one") is recorded with
   `disposition: planned` and folded into the Stage-3 plan. It does **not** license an immediate
   write. Approval of *scope* is not a waiver of the *review gate*.
3. **Stage 3 may not present a plan until every row has a disposition** and every `planned` row has a
   declared P/K/M `plan_ref`. `context-only` and `declined` have null references and nonempty grounded
   reasons. Carry the full retained-plus-new reconciliation in the v2 plan; preserve retained
   sequence/stage/verbatim and any timestamp, and persist it only at approved Stage 4.

**Why this exists.** In the 2026-07-25 session the operator made roughly a dozen steering comments
across the sweep. One ("you can edit the handoffs (or better, make a new one...)") was read as
authorization and a handoff was created mid-sweep, bypassing plan review. The operator's correction:
*"in the future, when this happens, I simply want you to tack it on to your handoff amendment plan."*
