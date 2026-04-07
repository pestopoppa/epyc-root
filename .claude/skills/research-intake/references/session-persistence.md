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

## Resume Protocol

On each skill invocation:

1. Check if `.research-session.json` exists in the repo root
2. If it exists and `last_checkpoint` is less than 7 days old:
   - Report: "Found session {session_id} from {last_checkpoint} — {N} entries processed, {M} remaining"
   - Offer to resume from where it left off (skip already-processed URLs)
3. If it exists but `last_checkpoint` is older than 7 days:
   - Warn: "Session {session_id} is {age}d old — intake index or handoffs may have changed"
   - Suggest starting fresh (delete session file and reprocess all URLs)
4. If it does not exist, start a fresh session

## Checkpoint Protocol

During Phase 5 (Report & Persist), after each entry is appended to `intake_index.yaml`:

1. Update `entries_processed` with the new intake ID
2. Remove the corresponding URL from `entries_remaining`
3. Update `last_checkpoint` to current time
4. Write `.research-session.json` atomically (write to `.research-session.json.tmp`, then rename)

On successful completion of all entries:
- Delete `.research-session.json` (session complete, no resume needed)

## Related Patterns

The autopilot uses an analogous pattern: `autopilot_state.json` persists
`trial_counter`, `consecutive_failures`, and epoch metadata across restarts.
The schemas are intentionally independent (cross-cutting concern #3 in the
KB governance handoff).
