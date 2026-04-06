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
| `handoffs_updated` | list[string] | Active handoff filenames amended with insights |
| `handoffs_created` | list[string] | New stub handoff filenames created |
| `citation_context` | string | Surrounding text where this was cited (seed entries only) |
| `notes` | string | Free-form analysis notes, deep-dive findings, revision history |

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
