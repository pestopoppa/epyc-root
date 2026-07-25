# Intake Index Entry Schema

Each entry in `research/intake_index.yaml` follows this schema.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID, format `intake-NNN` (zero-padded 3 digits) |
| `arxiv_id` | string or null | arXiv identifier (e.g., `"2402.12374"`). Primary dedup key. Null for non-arXiv sources. |
| `url` | string | Source URL |
| `source_type` | enum | `paper`, `blog`, or `repo` |
| `title` | string | Title of the work |
| `categories` | list[string] | 1+ category keys from `taxonomy.yaml` |
| `novelty` | enum | `high`, `medium`, `low`, or `duplicate` |
| `relevance` | enum | `high`, `medium`, `low`, or `none` |
| `discovered_via` | enum | `seed`, `input`, `expansion`, or `search` |
| `verdict` | enum | `new_opportunity`, `already_integrated`, `worth_investigating`, `not_applicable`, `superseded`, `adopt_patterns`, or `adopt_component` |
| `ingested_date` | string | ISO date (YYYY-MM-DD) |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `authors` | list[string] | Author names |
| `key_claims` | list[string] | 3-5 key claims extracted from the work |
| `techniques` | list[string] | Named techniques introduced or applied |
| `reported_results` | list[string] | Key metrics/results reported |
| `cross_references` | object | Cross-reference targets (see below) |
| `expanded_from` | string or null | ID of the entry this was expanded from |
| `recommended_actions` | list[string] | Suggested follow-up actions |
| `credibility_score` | integer or null | Source credibility score (0-6). Rubric: peer-reviewed +2, recent +1/old -1, authority +1, bias -1, corroboration +1/source max +2. Null for repos/blogs without empirical claims. |
| `contradicting_evidence` | list[string] or null | Contradicting evidence found during Tier 2b search. Null if none found or search not performed. |
| `handoffs_updated` | list[string] | Active handoff filenames amended with insights |
| `handoffs_created` | list[string] | New stub handoff filenames created |
| `citation_context` | string | Surrounding text where this was cited (seed entries only) |
| `notes` | string | Free-form analysis notes, deep-dive findings, revision history |
| `verification` | enum | `stage1-unverified` (default on Stage-1 persist) · `dive-verified` · `dive-overturned`. **Set by Stage 1; promoted only by a Stage-2 dive that read primary source.** |
| `dive_corrections` | string | Dated record of what a Stage-2 dive changed, so an overturned conclusion cannot be re-derived. Append-only. |

## Cross-References Object

```yaml
cross_references:
  chapters: ["01-speculative-decoding.md"]
  handoffs: ["tree-speculation-numa-drafting.md"]
  experiments: ["specexec-verification-profile.md"]
  intake_entries: ["intake-003"]
```

## ID Sequencing

IDs must be sequential: `intake-001`, `intake-002`, etc. The `seed_index.py` script assigns initial IDs. New entries appended by the skill continue the sequence.

## Deduplication

- Primary key: `arxiv_id` (exact match)
- Secondary: `url` (exact match for non-arXiv)
- Duplicate entries get `novelty: duplicate` and are not expanded

## Schema versioning & permissive consumption (added 2026-06-20, intake-710/711)

The intake index follows a **permissive-consumption contract**: `validate_intake.py`
validates the REQUIRED fields and enum values listed above, but PRESERVES
unknown/extra keys — it does not reject an entry for carrying fields beyond the
required set. This makes new optional fields forward-compatible: a field can be
added by one agent without breaking validation for parallel agents that do not
yet know about it.

The taxonomy and this schema are versioned (`schema_version: "1.0"`) so consumers
can detect drift. See `wiki/SCHEMA.md` → `## Conformance` for the canonical
statement of both the version stamp and the permissive-consumption contract.


## Verification lifecycle (added 2026-07-25)

Every entry carries a `verification` state:

| State | Set by | Meaning |
|---|---|---|
| `stage1-unverified` | Stage 1 persist | Extracted from a fetch/summary pass. Claims are **provisional**. |
| `dive-verified` | Stage 2 dive | Claims checked against primary source (quoted `file:line` or passage). |
| `dive-overturned` | Stage 2 dive | A load-bearing claim was falsified; see `dive_corrections`. |

**The unverified contract.** No number, quoted metric, or named mechanism from a
`stage1-unverified` entry may be quoted in a Stage-3 plan item or a handoff task line. It must first
be promoted by a dive.

**Why this exists.** On 2026-07-25 two Stage-1 summariser agents invented specifics that were
persisted to the index and read as evidence: a paper ablation whose four numbers appear nowhere in
the paper (and which had additionally been cross-pasted into an *unrelated* entry), and a four-step
tool behaviour absent from its source, which contained two generic sentences. Both survived until a
Stage-2 dive read the primary sources. The `verification` field makes that provisional status visible
instead of invisible.

**Cross-contamination check.** Before persisting, verify each entry's `key_claims` and
`reported_results` reference only its **own** source. A figure belonging to a different entry is a
defect, not a stylistic issue.
