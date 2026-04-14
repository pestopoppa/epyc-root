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

### Operation 3 — Compile

Synthesize knowledge fragments into topic-organized wiki articles.

Invoke with: "compile the wiki" / "update the wiki" / "synthesize knowledge"

#### Step 1: Generate Source Manifest

Run the manifest scanner to identify compilable sources:

```
python3 .claude/skills/project-wiki/scripts/compile_sources.py
```

For a full recompilation (ignore last compile timestamp):
```
python3 .claude/skills/project-wiki/scripts/compile_sources.py --full
```

Review the `total_new` count. If 0, no compilation needed — inform the user and stop.

#### Step 2: Read and Analyze Sources

Read sources from the manifest. Prioritize by information density:
1. **Research deep-dives** (`research/deep-dives/`) — richest structured analyses
2. **Active handoffs** (`handoffs/active/`) — embedded findings and decisions
3. **Completed handoffs** (`handoffs/completed/`) — validated conclusions
4. **Progress logs** (`progress/`) — session-level observations
5. **Docs** (`docs/`) — operational context

Also load `research/intake_index.yaml` entries for the relevant categories — these provide paper metadata, verdicts, and credibility scores that inform the wiki articles.

For each source, extract:
- Key findings, decisions, and their rationale
- Patterns discovered or conventions established
- Open questions or unresolved tensions
- Cross-references to other categories or work items

#### Step 3: Cluster by Taxonomy Category

Map each finding to one or more categories from `wiki/SCHEMA.md`. Use the aliases section to normalize informal category names to canonical keys.

Categories with 3+ substantive sources get a full compiled article. Categories with fewer sources get stub entries in `wiki/INDEX.md` pointing to their raw sources.

#### Step 4: Synthesize Wiki Pages

For each category cluster, create or update `wiki/<category-key>.md`:

```markdown
# <Category Label>

**Category**: `<key>` from wiki/SCHEMA.md
**Confidence**: <verified|inferred|external>
**Last compiled**: YYYY-MM-DD
**Sources**: N documents

## Summary

<2-4 paragraph synthesis across all sources in this category>

## Key Findings

- <finding with [source citation](../path/to/source.md)>
- <finding referencing [intake-NNN] paper title>

## Open Questions

- <unresolved question from handoffs or research>

## Related Categories

- [Related Category](related-category.md) — <relationship>

## Source References

- [deep-dive title](../research/deep-dives/file.md) — <what it contributed>
- [handoff title](../handoffs/active/file.md) — <relevant finding>
- [intake-NNN] paper title — <key claim, credibility score>
```

Filename convention: `wiki/<category-key>.md` (e.g., `wiki/speculative-decoding.md`)

If a wiki page already exists for that category, merge new findings and update the "Last compiled" date. Never delete existing content without cause.

#### Step 5: Update Compile Timestamp

After successful compilation:
```
python3 .claude/skills/project-wiki/scripts/compile_sources.py --touch
```

#### Compilation Principles

- **Synthesize, don't copy.** Wiki pages distill knowledge across sources; they are not duplicates.
- **Cite sources.** Every claim traces to a source via the Source References section.
- **Cross-reference.** Link related wiki pages to each other via the Related Categories section.
- **Confidence levels.** Use `verified` for tested/measured findings, `inferred` for analysis, `external` for third-party claims.
- **Incremental.** Only process sources newer than `.last_compile` unless doing a full recompile.
- **Preserve existing.** Update wiki pages in place; merge new findings into existing structure.

## Boundaries

- The lint operation only reports issues — it does NOT auto-fix them.
- The query operation synthesizes from existing KB content — it does NOT fetch new external information.
- The compile operation reads all source streams but writes only to `wiki/`.
- For ingesting new material, use the research-intake skill.
- Scaling thresholds in `wiki.yaml` are advisory — the skill warns but does not enforce them.
