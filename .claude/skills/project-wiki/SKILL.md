---
name: project-wiki
description: Lint, query, and maintain the project knowledge base. Use when auditing KB health, searching for compiled knowledge, or checking governance hygiene. Do not use when ingesting new research (use research-intake).
---

# Project Wiki

Use this skill to maintain and query the project's knowledge base.

Use when:

- Auditing knowledge base health (orphan handoffs, stale entries, contradictions)
- Asking "what do we know about X?" and getting compiled answers with citations
- Checking governance hygiene before handoff reviews or before nightshift runs
- Verifying that all intake entries have been actioned

Do not use when:

- Ingesting new research material (use the research-intake skill instead)
- Writing or editing chapter content directly
- Working on orchestrator code or running benchmarks

## Configuration

Reads `wiki.yaml` at repo root for paths, thresholds, and enabled lint passes.
Falls back to sensible defaults if `wiki.yaml` is not present.

## Operations

### Operation 1 — Lint

Audit the knowledge base for hygiene issues. Run via:
```
python3 .claude/skills/project-wiki/scripts/lint_wiki.py
```

Or invoke this skill with: "lint the knowledge base" / "check KB health"

#### Lint Passes

1. **Orphan handoff detection**:
   - Parse all `*-index.md` files in `handoffs/active/`
   - Extract referenced handoff filenames via `[filename.md]` markdown link pattern
   - Flag any `.md` file in `handoffs/active/` that is not referenced by any index
   - Index files themselves are excluded from orphan detection

2. **Stale entry flagging**:
   - Stat each file in `handoffs/active/`
   - Flag files older than `lint.aging_days` (default 14d) as WARNING
   - Flag files older than `lint.stale_days` (default 30d) as ERROR
   - Age is based on file modification time

3. **Contradictory status detection**:
   - Extract `**Status**:` line from each handoff in active/
   - Flag if status text contains "completed", "archived", or "done" but file is in active/
   - Also check completed/ files that claim status "active"

4. **Un-actioned intake detection**:
   - Load `research/intake_index.yaml`
   - Find entries with verdict `worth_investigating` or `new_opportunity`
   - That have no `handoffs_created` field
   - And `ingested_date` older than `lint.unactioned_intake_days` (default 7d)

5. **Missing cross-reference detection**:
   - For each active handoff, extract markdown links `[text](target.md)`
   - Verify each target file exists (relative to handoffs/active/ or handoffs/completed/)
   - Flag broken links

#### Output

Structured report grouped by pass, with severity levels:
- **ERROR**: Must fix (stale >30d, contradictory status, broken cross-refs)
- **WARNING**: Should review (aging 14-30d, orphan handoffs, un-actioned intake)
- **INFO**: Informational (counts, summary statistics)

Exit code 1 if any ERRORs found, 0 otherwise.

### Operation 2 — Query

Answer questions about compiled knowledge with citations.

Invoke with: "what do we know about {topic}?"

#### Workflow

1. **Parse query**: Extract key terms, infer categories from `wiki/SCHEMA.md` taxonomy
2. **Load config**: Read `wiki.yaml` for cross-reference targets
3. **Scan intake index**: Search `research/intake_index.yaml` for entries matching query terms in title, key_claims, techniques, categories, notes
4. **Scan handoffs**: Search active handoffs for matching content (title, headings, body)
5. **Scan deep-dives**: Search `research/deep-dives/*.md` for matching content
6. **Rank results**: Score by relevance (exact match > category match > keyword match)
7. **Synthesize answer**: Compile findings into a structured response:

```markdown
## Answer: {query}

{synthesized response}

### Sources
- [{intake-NNN}] {title} — {relevance note}
- [{handoff}] {title} — {relevant section}

### Related
- {links to related but not directly answering entries}
```

#### Helper Script

Pre-filter large files to reduce context:
```
python3 .claude/skills/project-wiki/scripts/query_wiki.py "{query}"
```

Returns JSON with matching intake entries, handoffs, and deep-dives.

## Boundaries

- The lint operation only reports issues — it does NOT auto-fix them.
- The query operation synthesizes from existing KB content — it does NOT fetch new external information.
- For ingesting new material, use the research-intake skill.
- Scaling thresholds in `wiki.yaml` are advisory — the skill warns but does not enforce them.
