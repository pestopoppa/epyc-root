---
name: research-intake
description: Process research URLs (papers, blogs, repos) through a structured intake pipeline. Extracts claims, deduplicates against a persistent index, cross-references existing work, expands literature, updates active handoffs, proposes handoff stubs, and produces a structured report. Use when ingesting new research material into the EPYC compendium.
---

# Research Intake

Use this skill to process research material into the persistent intake index.

Use when:

- Ingesting new papers, blog posts, or repository links.
- Expanding literature from existing entries.
- Cross-referencing new material against chapters, handoffs, and experiments.

Do not use when:

- Writing or editing chapter content directly.
- Running benchmarks or evaluations.
- Working on orchestrator code.

## Workflow

Execute these 5 phases in order for each invocation.

### Phase 0 — Session Resume Check

Before starting Phase 1, check for an existing `.research-session.json` in the repo root. If found and less than 7 days old, offer to resume (skip already-processed URLs). If older than 7 days, warn about staleness and suggest starting fresh. See `references/session-persistence.md` for the full schema and protocol.

### Phase 1 — Fetch & Extract

For each URL provided:

1. **Parse the URL**:
   - arXiv: extract the arXiv ID (e.g., `2402.12374` from any arxiv.org URL variant)
   - GitHub: note as `source_type: repo`
   - Other: note as `source_type: blog`

2. **Check for duplicates**: Read `research/intake_index.yaml`. If the arXiv ID or URL already exists:
   - Report it as a duplicate in the output
   - Set `novelty: duplicate`
   - Skip phases 3-4 for this entry
   - Still include in the report

3. **Fetch content**:
   - arXiv papers: use `https://ar5iv.org/abs/{arxiv_id}` (HTML version) via WebFetch
   - Blog posts: fetch directly via WebFetch
   - GitHub repos: fetch `https://raw.githubusercontent.com/{owner}/{repo}/main/README.md` via WebFetch, plus the repo page itself

4. **Extract structured information**:
   - Title, authors (if available)
   - Key claims (3-5 bullet points)
   - Named techniques introduced or applied
   - Reported results (metrics, speedups, comparisons)
   - arXiv IDs referenced in the paper (for Phase 3 expansion)

### Phase 2 — Cross-Reference

For each non-duplicate entry:

1. **Load cross-reference map**: Read `references/cross-reference-map.md` to determine which files to search based on the entry's categories.

2. **Search across the codebase**:
   - **Chapters** (`epyc-inference-research/docs/chapters/*.md`): search by arXiv ID, title keywords, technique names
   - **Active handoffs** (`epyc-root/handoffs/active/*.md`): search by arXiv ID and technique keywords
   - **Completed handoffs** (`epyc-root/handoffs/completed/*.md`): same
   - **Experiments** (`epyc-inference-research/docs/experiments/*.md`): same
   - **Intake index** (`research/intake_index.yaml`): by categories and techniques
   - **Research notes** (`epyc-root/research/*.md`): by arXiv ID

3. **Score novelty**:
   - `duplicate`: arXiv ID or URL already in index
   - `low`: technique/approach already well-covered in chapters
   - `medium`: related work exists but this adds new perspective or results
   - `high`: novel technique or significant new results not covered

4. **Score relevance**:
   - `high`: directly applicable to active work (matches active handoff or current optimization focus)
   - `medium`: related to EPYC's domain but not immediately actionable
   - `low`: tangentially related
   - `none`: out of scope

5. **Score source credibility** (record as `credibility_score`, integer 0-6 or null):
   - Peer-reviewed venue (top conference or journal): +2
   - Published within 12 months: +1 / older than 24 months: -1
   - Author authority (major lab affiliation, known contributor to the field): +1
   - Identified bias (commercial product promotion, methodological conflict of interest): -1
   - Independent corroboration (other papers/repos confirming results): +1 per source (max +2)
   - Tiers: High (4-6), Medium (2-3), Low (0-1)
   - Skip scoring (set null) for repos, blog posts with no empirical claims, or duplicate entries

6. **Assign verdict**:
   - `already_integrated`: technique covered in chapters/experiments
   - `new_opportunity`: novel + high relevance → warrants investigation
   - `worth_investigating`: medium novelty or relevance → worth tracking
   - `not_applicable`: low relevance to EPYC
   - `superseded`: newer work has replaced this approach

### Phase 3 — Literature Expansion

Only expand from entries with `relevance >= medium`. Max 10 new entries per run. Max depth: 2 hops.

**Tier 1 — Reference chasing**:
- Extract arXiv IDs from the paper's references section
- Check each against the intake index
- Queue unseen, relevant-looking ones (based on title/context)

**Tier 2 — Targeted search**:
- Use WebSearch for `"{technique}" {category} 2025 2026`
- Check top 5 results for new relevant material

**Tier 2b — Contradicting evidence search**:
For each key claim from entries with `credibility_score >= 3` (or any entry with `verdict: new_opportunity`):
- WebSearch for `"{key_claim}" criticism` OR `"{technique}" limitations`
- Check top 3 results for contradicting evidence, failed replications, or known caveats
- Record findings in the `contradicting_evidence` field (list of strings, or null if none found)
- If all key claims align with existing work and no contradictions are found, explicitly note: "No contradicting evidence found — possible confirmation bias risk"
- This step prevents the intake pipeline from accumulating only supporting evidence

**Tier 3 — Implementation discovery**:
- WebSearch for `"{paper_title}" site:github.com`
- WebSearch for `"{technique}" llama.cpp` or `"{technique}" vllm`

For each discovered entry, run Phase 1 (extract) and Phase 2 (cross-reference) on it. Mark `discovered_via: expansion` or `search`, and set `expanded_from` to the parent entry ID.

### Phase 4 — Handoff Integration

#### 4a — Update Active Handoffs

For each active handoff that cross-references matched:

1. Read the handoff's current content
2. Append a section at the end:

```markdown
## Research Intake Update — {YYYY-MM-DD}

### New Related Research
- **[{intake_id}] "{title}"** (arxiv:{arxiv_id})
  - Relevance: {why this matters to this handoff}
  - Key technique: {what's new}
  - Reported results: {metrics if available}
  - Delta from current approach: {what's different from what we're doing}
```

3. Record the handoff filename in the entry's `handoffs_updated` field.

#### 4b — Propose Handoff Stubs

For entries with `verdict: new_opportunity` AND `relevance: high` that don't match any existing handoff:

1. Create a stub in `handoffs/active/` named after the technique (kebab-case, e.g., `heap-tree-speculation.md`)
2. Use this format:

```markdown
# {Technique Name}

**Status**: stub
**Created**: {YYYY-MM-DD} (via research intake)
**Categories**: {cat1}, {cat2}

## Objective

{1-2 sentence summary of what this technique could enable for EPYC}

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| {id} | {title} | {relevance} | {verdict} |

## Open Questions

- {Question about applicability to our stack}
- {Question about implementation feasibility}

## Notes

{Any initial observations from the intake analysis}
```

3. Record the handoff filename in the entry's `handoffs_created` field.

### Phase 5 — Report & Persist

1. **Print structured report** to the conversation:

```
## Research Intake Report — {date}

### Processed Entries

| ID | Title | Type | Novelty | Relevance | Verdict |
|----|-------|------|---------|-----------|---------|
| intake-NNN | ... | paper | high | high | new_opportunity |

### Cross-References Found
- {entry}: matched {chapter/handoff/experiment} — {reason}

### Literature Expansion
- {N} new entries discovered via reference chasing
- {N} new entries discovered via search

### Handoff Updates
- Updated: {list of handoffs amended}
- Created stubs: {list of new stub handoffs}

### Recommended Actions
- {Prioritized list of follow-up actions}
```

2. **Append entries to `research/intake_index.yaml`**:
   - Continue the ID sequence from the last entry
   - Set `ingested_date` to today
   - Include all fields from the schema
   - After each entry is appended, update `.research-session.json` checkpoint (move URL from `entries_remaining` to `entries_processed`). On completion of all entries, delete the session file.

3. **Run validation**: Execute `python3 .claude/skills/research-intake/scripts/validate_intake.py` to verify index integrity.

## Boundaries

- Do NOT modify chapter files directly — flag needed updates in recommended actions.
- DO update active handoffs with research context (Phase 4a).
- DO create handoff stubs for new opportunities (Phase 4b).
- Respect the 10-entry expansion cap per run.
- Always run validation after persisting.
