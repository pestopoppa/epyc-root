# Knowledge Base Governance Improvements

**Status**: active
**Created**: 2026-04-06 (via research intake deep-dive)
**Categories**: governance, research-intake, skill-enhancement
**Origin**: intake-268 (Karpathy LLM Wiki), intake-269 (nvk/llm-wiki), intake-270 (tobi/qmd)

## Objective

Adopt patterns from three LLM knowledge-base research entries into epyc-root's research-intake skill and governance infrastructure. Adds credibility scoring, anti-confirmation-bias mechanisms, session persistence, and semantic search documentation.

Companion handoff in root-archetype: [`knowledge-base-linter.md`](/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md) — upstream patterns for all instances.

---

## Outstanding Tasks (Priority Order)

### Phase 0 — Knowledge base linter for epyc-root (P0)

- [ ] Create `scripts/validate/lint_knowledge_base.py` with 4 lint passes:
  1. **Orphan handoff detection**: parse all `*-index.md` in `handoffs/active/`, extract referenced filenames, flag unreferenced `.md` files
  2. **Stale handoff flagging**: stat each file, flag >14d as aging, >30d as stale (complement existing `check_handoff_freshness.sh`)
  3. **Contradictory status detection**: extract `**Status**:` line, compare against directory placement (`active/` vs `completed/`)
  4. **Un-actioned intake detection**: find `research/intake_index.yaml` entries with `verdict: worth_investigating` or `new_opportunity` that have no `handoffs_created` field and are >7 days old
- [ ] Wire into nightshift: add `knowledge-lint` task to epyc-root's nightshift config (if present) or document as a periodic manual check
- [ ] After root-archetype version is finalized, reconcile: epyc-root's linter should converge with the upstream template version

### Phase 1 — Research-intake skill enhancements (P1)

- [ ] Add credibility scoring step to Phase 2 of `.claude/skills/research-intake/SKILL.md`:
  - After scoring novelty and relevance, score source credibility using rubric:
    - Peer-reviewed venue: +2
    - Published within 12 months: +1 / older than 24 months: -1
    - Author authority: +1
    - Identified bias: -1
    - Independent corroboration: +1/source (max +2)
  - Add `credibility_score` field to intake entries (integer, optional)
- [ ] Add anti-confirmation-bias "Tier 2b" to Phase 3 (Literature Expansion):
  - After Tier 2 targeted search, add: "Tier 2b — Contradicting evidence search"
  - `WebSearch for "{key_claim} criticism" OR "{technique} limitations"`
  - Any contradicting evidence noted in `contradicting_evidence:` field (list of strings)
- [ ] Update `references/intake-schema.md` with new fields
- [ ] Update `scripts/validate_intake.py` to validate `credibility_score` (integer 0-6 or null) and `contradicting_evidence` (list or null)

### Phase 2 — Session persistence docs (P2)

- [ ] Create `references/session-persistence.md` documenting crash recovery pattern:
  - `.research-session.json` schema: `{session_id, started_at, last_checkpoint, phase, entries_processed, entries_remaining, state}`
  - Resume protocol: check for existing session file on invocation, offer to resume
  - 7-day staleness warning
- [ ] Add checkpoint logic description to SKILL.md Phase 5: after each entry appended, write checkpoint; on invocation, check for session file

### Phase 3 — qmd semantic search addon docs (P2, optional)

- [ ] Create `references/semantic-search-addon.md` documenting:
  - qmd (tobi/qmd): local hybrid search using BM25 + vector + LLM reranking via node-llama-cpp
  - ~2GB GGUF models (embedding 300M, reranker 600M, query expansion 1.7B) on CPU
  - MCP server integration: add to Claude Code config, get `query`/`get` tools
  - Corpus: point at `/workspace` root (~359 markdown files)
  - Use case: replace grep-based cross-referencing in Phase 2 with semantic search
  - Natural markdown chunking algorithm details (break-point scoring with distance decay)
- [ ] Note: actual deployment is a separate work item, not part of this handoff

### Phase 4 — Intake index maintenance (P0)

- [ ] Update intake-268 verdict from `worth_investigating` → `adopt_patterns` in YAML body
- [ ] Update intake-269 verdict from `worth_investigating` → `adopt_patterns` in YAML body
- [ ] Update intake-270 verdict from `worth_investigating` → `adopt_component` in YAML body
- [ ] Add `handoffs_created: [knowledge-base-governance-improvements.md]` to all three entries
- [ ] Add `handoffs_updated: [context-folding-progressive.md]` if not already present

---

## Dependency Graph

```
Phase 4 (intake index cleanup)         ── P0, no deps, do first ──
Phase 1 (skill enhancements)           ── P1, independent ──
Phase 2 (session persistence docs)     ── P2, independent ──
Phase 3 (qmd addon docs)              ── P2, independent, optional ──
```

Phase 4 should be done first to keep intake cross-references accurate. Phases 1-3 are independent.

---

## Cross-Cutting Concerns

1. **Credibility scoring ↔ routing-intelligence factual risk**: The routing-intelligence handoff has a factual-risk scoring system (`src/classifiers/factual_risk.py`). That scores *inference requests* for routing decisions. This credibility scoring scores *research sources* for intake quality. Different domains, no code overlap, but conceptually related — both assign trust scores.

2. **Anti-confirmation-bias ↔ autopilot diversity**: Autopilot maintains Pareto archive diversity (non-dominated solutions). The anti-confirmation-bias directive maintains *evidence* diversity in research intake. Same principle at different layers.

3. **Session persistence ↔ autopilot checkpoints**: Autopilot already has `checkpoint_state()` / `restore()` / `autopilot_state.json`. Research session persistence follows the same pattern but for a different workflow. Keep schemas independent — don't try to unify.

4. **qmd ↔ context-folding**: qmd's break-point scoring algorithm for markdown chunking (H1=100, H2=90...H6=50, code=80, with squared-distance decay) is directly applicable to context-folding segment boundary detection. If qmd is deployed, extract this algorithm as a reference for context-folding Phase 3c. Note this in `context-folding-progressive.md`.

5. **Root-archetype companion**: The linter and template patterns from this work are being upstreamed via `/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md`. Changes here inform what gets upstreamed. Coordinate timing.

---

## Reporting Instructions

After completing any task:
1. Check the task checkbox in this index
2. Update the relevant skill/reference file
3. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
4. If changes affect the intake skill workflow, re-run `python3 .claude/skills/research-intake/scripts/validate_intake.py`

---

## Key File Locations

| Resource | Path |
|----------|------|
| Research-intake skill | `.claude/skills/research-intake/SKILL.md` |
| Intake schema reference | `.claude/skills/research-intake/references/intake-schema.md` |
| Cross-reference map | `.claude/skills/research-intake/references/cross-reference-map.md` |
| Intake validator | `.claude/skills/research-intake/scripts/validate_intake.py` |
| Intake index | `research/intake_index.yaml` |
| Taxonomy | `research/taxonomy.yaml` |
| Context-folding handoff | `handoffs/active/context-folding-progressive.md` |
| Root-archetype companion | `/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md` |

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-268 | LLM Wiki (Karpathy) | high | adopt_patterns |
| intake-269 | nvk/llm-wiki | high | adopt_patterns |
| intake-270 | tobi/qmd | high | adopt_component |
