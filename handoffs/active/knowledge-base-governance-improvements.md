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

### Phase 5 — Project-wiki skill: build in epyc-root, then upstream (P1, intake-277 deep-dive)

epyc-root IS the testbed — it already has ~5.2 MB / 275 files / ~99.5k lines of LLM-compiled knowledge spread across research/, handoffs/, progress/, and deep-dives/. Build the project-wiki skill here first, validate it on our own KB, then extract the portable version to root-archetype.

**Phase 5a — wiki.yaml config + portability fix (epyc-root)**
- [ ] Design `wiki.yaml` config schema at repo root: cross-reference targets (replacing hardcoded `/mnt/raid0/` paths in validate_intake.py:34,36 and seed_index.py:24), taxonomy (absorbs research/taxonomy.yaml), ingest pipeline flags, scaling thresholds (50/200/500 from Hermes PR#5635)
- [ ] Fix 4 hardcoded path references: `validate_intake.py` (2), `seed_index.py` (1), `reset_episodic_memory.sh` (1) — read from wiki.yaml or env vars
- [ ] Create `wiki/SCHEMA.md` as living taxonomy (replaces static `references/taxonomy.md`). Backfill missing categories (mechanistic_interpretability appears 19x in intake but not in taxonomy)

**Phase 5b — Lint operation (epyc-root, absorbs Phase 0)**
- [ ] Build lint into the project-wiki skill (not as a separate validator script): orphan handoffs, stale entries (>14d aging, >30d stale), contradictory status vs directory, un-actioned intake entries >7d, missing cross-refs between handoffs
- [ ] This absorbs Phase 0 tasks — the linter IS the lint operation

**Phase 5c — Query operation (epyc-root)**
- [ ] Add query operation: read wiki.yaml for targets → scan index for relevant entries → read matching handoffs/deep-dives → synthesize answer with citations → optionally persist as new deep-dive page
- [ ] This fills the biggest gap: currently no way to ask "what do we know about X?" and get compiled knowledge back

**Phase 5d — Upstream to root-archetype**
- [ ] Extract epyc-specific config from wiki.yaml into `wiki.yaml.template` with `{{TEMPLATE_VARS}}`
- [ ] Copy validated project-wiki skill to root-archetype `.claude/skills/project-wiki/`
- [ ] Generalize validate_wiki.py to be config-driven (no project-specific assumptions)
- [ ] Update root-archetype `init-project.sh` to scaffold wiki structure on clone
- [ ] Reconcile with existing root-archetype `knowledge-base-linter.md` companion handoff

**Risk**: intake_index.yaml at 308 KB / 277 entries is straining. Hybrid storage (YAML index + markdown pages) doubles write surface. Decision needed: simultaneous writes vs periodic compile. Recommend: **ingest writes YAML only, periodic `wiki compile` operation generates/updates markdown pages** — keeps the hot path simple.

**Dependency**: Phase 0/5b linter should come first (validates lint design). Phase 1 credibility scoring independent but should land before 5d upstream.

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
Phase 5a (wiki.yaml + portability)     ── P0, no deps, can parallel w/ Phase 4 ──
Phase 5b (lint operation)              ── P0, absorbs Phase 0 ──
Phase 1 (skill enhancements)           ── P1, independent ──
Phase 5c (query operation)             ── P1, after 5a ──
Phase 2 (session persistence docs)     ── P2, independent ──
Phase 3 (qmd addon docs)              ── P2, independent, optional ──
Phase 5d (upstream to root-archetype)  ── P1, after 5a+5b+5c validated in epyc-root ──
```

Phase 4 and 5a can run in parallel (no deps). Phase 5b absorbs Phase 0 (the linter IS the lint operation). Phase 5d only happens after the skill is proven in epyc-root.

---

## Cross-Cutting Concerns

1. **Credibility scoring ↔ routing-intelligence factual risk**: The routing-intelligence handoff has a factual-risk scoring system (`src/classifiers/factual_risk.py`). That scores *inference requests* for routing decisions. This credibility scoring scores *research sources* for intake quality. Different domains, no code overlap, but conceptually related — both assign trust scores.

2. **Anti-confirmation-bias ↔ autopilot diversity**: Autopilot maintains Pareto archive diversity (non-dominated solutions). The anti-confirmation-bias directive maintains *evidence* diversity in research intake. Same principle at different layers.

3. **Session persistence ↔ autopilot checkpoints**: Autopilot already has `checkpoint_state()` / `restore()` / `autopilot_state.json`. Research session persistence follows the same pattern but for a different workflow. Keep schemas independent — don't try to unify.

4. **qmd ↔ context-folding**: qmd's break-point scoring algorithm for markdown chunking (H1=100, H2=90...H6=50, code=80, with squared-distance decay) is directly applicable to context-folding segment boundary detection. If qmd is deployed, extract this algorithm as a reference for context-folding Phase 3c. Note this in `context-folding-progressive.md`.

5. **Root-archetype companion**: The linter and template patterns from this work are being upstreamed via `/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md`. **Updated 2026-04-07**: epyc-root is now the proving ground — build project-wiki skill here first (Phase 5a-c), validate on our ~5.2 MB / 275-file KB, then extract to root-archetype (Phase 5d). This reverses the original sequencing which treated epyc-root as a later migration target.

6. **epyc-root IS an LLM wiki**: Audit (2026-04-07) confirms 277 intake entries + 154 handoffs + 87 progress logs + 25 deep-dives = ~99.5k lines of LLM-compiled knowledge. Missing: query operation (can't ask "what do we know about X?"), lint operation (no systematic orphan/stale/contradiction detection), scaling thresholds (intake_index.yaml growing unbounded at 308 KB).

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
| intake-277 | Hermes Agent PR#5100: LLM Wiki Skill | medium | already_integrated |

## Research Intake Update — 2026-04-07

### New Related Research
- **[intake-277] "Hermes Agent PR#5100: LLM Wiki Skill (Karpathy Pattern)"** (github:NousResearch/hermes-agent/pull/5100)
  - Relevance: Upstream Hermes implementation of the Karpathy LLM Wiki pattern we're adopting
  - Key technique: Three-layer architecture (raw sources / wiki pages / schema) with ingest/query/lint operations
  - Reported results: Merged into hermes-agent main via PR#5635 on 2026-04-06
  - Delta from current approach: Our Phase 0 KB linter aligns with their lint operation (contradictions, orphans, outdated content). Their entity/concept/comparison page taxonomy could inform cross-reference-map.md structure. PR#5635 bundled a skill configuration interface worth reviewing.
