# Stage-2b combined ingest-and-dive brief (ws58 intake, 2026-10-31)

Read scratch:dive-ws58-20261031/briefs/dive_common.md FIRST and follow all of it (safety, read-depth,
no compute, grounding, output file rule). Also use the scoring rubrics in
scratch:dive-ws58-20261031/briefs/stage1_common.md. Each source you are given is NEW (not in the index)
and gets an intake ID assigned in your prompt. You do Stage 1 and Stage 2 in one pass.

Your output YAML has the dive_common sections (`entries`, `ledger`, `dive_surfaced_sources`, `artifact_audit`)
PLUS a `new_entries` list, one per assigned ID, holding the Stage-1 record:

```yaml
new_entries:
- id: intake-NNNN                 # as assigned
  arxiv_id: '<id>' or null        # null for repos/PRs/issues/blogs/cards (companion artifacts never carry the paper id)
  url: <canonical: arXiv -> https://arxiv.org/abs/<id>; GitHub -> https://github.com/<owner>/<repo>[/pull/N|/issues/N]; HF -> https://huggingface.co/<org>/<name>>
  source_type: paper | blog | repo
  title: '...'
  categories: [...]
  novelty: low|medium|high
  relevance: high|medium|low
  discovered_via: expansion
  expanded_from: intake-NNNN      # the entry whose dive surfaced it (given in your prompt)
  verdict: new_opportunity|worth_investigating|adopt_patterns|adopt_component|already_integrated|superseded|not_applicable
  ingested_date: '2026-10-31'
  authors: [...]
  key_claims: [...]               # same list you put in the matching `entries` record
  techniques: [...]
  reported_results: [...]
  cross_references: {chapters: [], handoffs: [<file.md>], experiments: [], intake_entries: [<bare intake-NNNN ids only>]}
  recommended_actions: [...]
  credibility_score: <int 0-6 or null>
  contradicting_evidence: [...] or null
  referenced_arxiv_ids: [<only ids you saw in the source AND title-checked on the abs page>]
  notes: '...'
  verification: stage1-unverified # the `entries` record promotes it
  handoffs_updated: []
  handoffs_created: []
  source_revision: '...'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'   # overwritten by the dive record
```
and the matching `entries` record (dive fields, as in dive_common) for the same ID. Anchors need a
source_text_path on disk. Dedup check: grep research/intake_index.yaml in the lane worktree for the URL/id first; if
it already exists, do NOT emit a new entry — report `{collision: intake-NNNN}` instead.
