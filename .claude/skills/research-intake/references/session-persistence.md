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
| `stage3_filing` | object, optional | Approved plan digest, affected-entry updates and context/opportunity reviews; persisted at Stage 4 |

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

The optional structural check is:

```bash
bash scripts/validate/validate_intake.sh --plan-file PATH --session-file PATH
```

Both paths are required together. The default invocation preserves legacy index validation. This
mode reads; it neither applies patches nor approves work. The main reviews the semantics separately.

During Stage 3, carry proposed entry_updates, opportunity_reviews and optional proposed_stubs in one JSON fence under
`## Stage-3 filing payload` in the plan. The validator may combine it with the retained checkpoint
in memory; Stage 3 still writes only the plan. Do not embed the plan's own digest inside its fence.
At the approved Stage-4 boundary persist session.stage3_filing with:

- plan_sha256: SHA-256 of the exact approved plan bytes, not a self-referential checksum.
- entry_updates: a list of flat records containing id, integration_disposition, handoffs_updated,
  handoffs_created and disposition_evidence. Overlay these on copies of the actual entries through
  existing payload rules; preserve unrelated/unknown fields and existing claim corrections.
- opportunity_reviews: an object keyed by authoritative packet/task reference (for example P1).
  Each record has nonempty project_objective, implementation_ref, gap, operational_change,
  benefit_direction, owner, execution_conditions and closure_basis. Existing fulfilled behavior
  and monitor/knowledge-only opportunity judgments belong in those grounded reviews.
- proposed_stubs (optional): complete path/content/index_file/index_row packages; each new active
  owner needs one existing domain index and a valid five-cell thin row linking to its packaged file.

Reconcile actionable_ledger.ledger_id and its terminal_mapping to the plan's authoritative complete
recommendation table, preserving each original source/action. Operational follow-through and enabling
wiring remain distinct recommendations. Resolve plan/task/trigger references and existing owners;
a new owner requires its approved complete stub and one owning domain-index-row package. Ambiguous
or unsupported payload/inventory formats are explicit errors, never a successful check of an
unchanged index. The check establishes structure, references and evidence-field presence only.
It cannot establish truth, ROI, suitability, fulfilled work or permission; those require main review.

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
   "plan_ref": "<plan item id, or null>"}
]
```

**Rules**

1. Append **verbatim** — do not paraphrase. Paraphrase is where intent gets lost.
2. Operator comments during stages 1-3 are **context, not authorization**. A comment that appears to
   grant permission ("you can edit the handoffs", "make a new one") is recorded with
   `disposition: planned` and folded into the Stage-3 plan. It does **not** license an immediate
   write. Approval of *scope* is not a waiver of the *review gate*.
3. **Stage 3 may not present a plan until every row has a disposition** and every `planned` row has a
   non-null `plan_ref`, or is an explicit written decline.

**Why this exists.** In the 2026-07-25 session the operator made roughly a dozen steering comments
across the sweep. One ("you can edit the handoffs (or better, make a new one...)") was read as
authorization and a handoff was created mid-sweep, bypassing plan review. The operator's correction:
*"in the future, when this happens, I simply want you to tack it on to your handoff amendment plan."*
