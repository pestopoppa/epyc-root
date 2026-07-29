# Knowledge Base Governance Improvements

**Status**: completed (all phases done 2026-04-07)
**Created**: 2026-04-06 (via research intake deep-dive)
**Updated**: 2026-04-07
**Categories**: governance, research-intake, skill-enhancement
**Origin**: intake-268 (Karpathy LLM Wiki), intake-269 (nvk/llm-wiki), intake-270 (tobi/qmd)

## Objective

Adopt patterns from three LLM knowledge-base research entries into epyc-root's research-intake skill and governance infrastructure. Adds credibility scoring, anti-confirmation-bias mechanisms, session persistence, and semantic search documentation.

Companion handoff in root-archetype: [`knowledge-base-linter.md`](/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md) — upstream patterns for all instances.

---

## Outstanding Tasks (Priority Order)

### Phase 0 — Knowledge base linter for epyc-root (P0)

- [x] Create lint implementation — ✅ 2026-04-07. ABSORBED by Phase 5b: `.claude/skills/project-wiki/scripts/lint_wiki.py` with 5 passes (orphan, stale, contradictory, un-actioned, missing cross-refs). First run found 4 real errors + 71 warnings.
- [x] Wire into nightshift — ✅ 2026-04-07. `knowledge-lint` task added to `nightshift.yaml` (priority 4, 72h interval).
- [ ] After root-archetype version is finalized, reconcile: epyc-root's linter should converge with the upstream template version

### Phase 1 — Research-intake skill enhancements (P1)

- [x] Add credibility scoring step to Phase 2 of `.claude/skills/research-intake/SKILL.md` — ✅ 2026-04-07. Added as step 5 (6-point rubric with tiers), renumbered verdict to step 6.
- [x] Add anti-confirmation-bias "Tier 2b" to Phase 3 (Literature Expansion) — ✅ 2026-04-07. Inserted after Tier 2, before Tier 3. Searches for criticism/limitations, records in `contradicting_evidence` field.
- [x] Update `references/intake-schema.md` with new fields — ✅ 2026-04-07. Added `credibility_score` (int 0-6 or null) and `contradicting_evidence` (list[str] or null).
- [x] Update `scripts/validate_intake.py` to validate `credibility_score` (integer 0-6 or null) and `contradicting_evidence` (list or null) — ✅ 2026-04-07. Both optional, existing entries pass.

### Phase 2 — Session persistence docs (P2)

- [x] Create `references/session-persistence.md` — ✅ 2026-04-07. Full schema, resume protocol, 7-day staleness warning, autopilot cross-reference.
- [x] Add checkpoint logic to SKILL.md — ✅ 2026-04-07. Phase 0 (session resume check) + Phase 5 checkpoint note (update after each append, delete on completion).

### Phase 3 — qmd semantic search addon docs (P2, optional)

- [x] Create `references/semantic-search-addon.md` — ✅ 2026-04-07. Covers qmd overview, model requirements (~2GB GGUF), MCP integration, corpus config, Phase 2 use case, chunking algorithm (break-point scoring with distance decay).
- [x] Note: actual deployment is a separate work item — ✅ documented in the reference file.

### Phase 5 — Project-wiki skill: build in epyc-root, then upstream (P1, intake-277 deep-dive)

epyc-root IS the testbed — it already has ~5.2 MB / 275 files / ~99.5k lines of LLM-compiled knowledge spread across research/, handoffs/, progress/, and deep-dives/. Build the project-wiki skill here first, validate it on our own KB, then extract the portable version to root-archetype.

**Phase 5a — wiki.yaml config + portability fix (epyc-root)**
- [x] Design `wiki.yaml` config schema at repo root — ✅ 2026-04-07. Created `wiki.yaml` with project, cross_references (env-var expandable), taxonomy (source + legacy), scaling thresholds, lint config, ingest flags.
- [x] Fix 4 hardcoded path references — ✅ 2026-04-07. validate_intake.py: refactored to `load_wiki_config()` + `_get_crossref_dirs()`. seed_index.py: `EPYC_RESEARCH_ROOT` env var. check_handoff_freshness.sh: relative path from script dir. reset_episodic_memory.sh: already used env var defaults, no change needed.
- [x] Create `wiki/SCHEMA.md` as living taxonomy — ✅ 2026-04-07. 30 canonical categories (24 original + 6 new: mechanistic_interpretability, emotion_psychology, llm_prompting, formal_verification, safety, reinforcement_learning) + 34 aliases mapping variant names to canonical categories. taxonomy.yaml also updated with the 6 new categories.

**Phase 5b — Lint operation (epyc-root, absorbs Phase 0)**
- [x] Build lint into the project-wiki skill — ✅ 2026-04-07. `.claude/skills/project-wiki/SKILL.md` (Operation 1) + `scripts/lint_wiki.py` (5 passes, config-driven via wiki.yaml). First run: 4 errors (2 stale, 2 contradictory), 71 warnings (69 un-actioned intake, 2 aging).
- [x] This absorbs Phase 0 tasks — ✅ the linter IS the lint operation

**Phase 5c — Query operation (epyc-root)**
- [x] Add query operation — ✅ 2026-04-07. Operation 2 in project-wiki SKILL.md. `scripts/query_wiki.py` pre-filters intake, handoffs, deep-dives with keyword scoring. Tested: "speculative decoding" returns 15 intake + handoff matches; "knowledge base" returns 45 results across 3 sources.
- [x] This fills the biggest gap — ✅ "what do we know about X?" now returns compiled results with citations

**Phase 5d — Upstream to root-archetype**
- [x] Extract epyc-specific config from wiki.yaml into `wiki.yaml.template` — ✅ 2026-04-07. Created `_templates/wiki.yaml.template` with `{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}` vars.
- [x] Copy validated project-wiki skill to root-archetype — ✅ 2026-04-07. `.claude/skills/project-wiki/` with SKILL.md, lint_wiki.py, query_wiki.py, lint-passes.md. EPYC-specific language removed.
- [x] Generalize scripts to be config-driven — ✅ 2026-04-07. Both lint_wiki.py and query_wiki.py read wiki.yaml, fall back to defaults. No project-specific assumptions.
- [x] Update root-archetype `init-project.sh` to scaffold wiki structure — ✅ 2026-04-07. Creates wiki/ dir, copies wiki.yaml from template with var substitution, scaffolds SCHEMA.md.
- [x] Reconcile with existing root-archetype `knowledge-base-linter.md` companion handoff — ✅ 2026-04-07. Phases 1-2 marked as superseded by project-wiki skill. Phase 3 credibility rubric created. Phase 4 (session persistence) deferred.

**Risk**: intake_index.yaml at 308 KB / 277 entries is straining. Hybrid storage (YAML index + markdown pages) doubles write surface. Decision needed: simultaneous writes vs periodic compile. Recommend: **ingest writes YAML only, periodic `wiki compile` operation generates/updates markdown pages** — keeps the hot path simple.

**Dependency**: Phase 0/5b linter should come first (validates lint design). Phase 1 credibility scoring independent but should land before 5d upstream.

### Phase 4 — Intake index maintenance (P0)

- [x] Update intake-268 verdict from `worth_investigating` → `adopt_patterns` in YAML body — ✅ already done in prior session
- [x] Update intake-269 verdict from `worth_investigating` → `adopt_patterns` in YAML body — ✅ already done in prior session
- [x] Update intake-270 verdict from `worth_investigating` → `adopt_component` in YAML body — ✅ fixed 2026-04-07 (was `adopt_patterns`, corrected to `adopt_component`)
- [x] Add `handoffs_created: [knowledge-base-governance-improvements.md]` to all three entries — ✅ already present
- [x] Add `handoffs_updated: [context-folding-progressive.md]` if not already present — ✅ already present

---

## Dependency Graph

```
✅ Phase 4 (intake index cleanup)         ── DONE 2026-04-07 ──
✅ Phase 5a (wiki.yaml + portability)     ── DONE 2026-04-07 ──
✅ Phase 5b (lint operation)              ── DONE 2026-04-07, absorbs Phase 0 ──
✅ Phase 1 (skill enhancements)           ── DONE 2026-04-07 ──
✅ Phase 5c (query operation)             ── DONE 2026-04-07 ──
   Phase 2 (session persistence docs)     ── P2, deferred ──
   Phase 3 (qmd addon docs)              ── P2, deferred, optional ──
✅ Phase 5d (upstream to root-archetype)  ── DONE 2026-04-07 ──
```

All P0/P1 phases complete. Only Phase 2 (session persistence docs) and Phase 3 (qmd semantic search docs) remain — both P2 priority, documentation-only.

---

## Cross-Cutting Concerns

1. **Credibility scoring ↔ routing-intelligence factual risk**: The routing-intelligence handoff has a factual-risk scoring system (`src/classifiers/factual_risk.py`). That scores *inference requests* for routing decisions. This credibility scoring scores *research sources* for intake quality. Different domains, no code overlap, but conceptually related — both assign trust scores.

2. **Anti-confirmation-bias ↔ autopilot diversity**: Autopilot maintains Pareto archive diversity (non-dominated solutions). The anti-confirmation-bias directive maintains *evidence* diversity in research intake. Same principle at different layers.

3. **Session persistence ↔ autopilot checkpoints**: Autopilot already has `checkpoint_state()` / `restore()` / `autopilot_state.json`. Research session persistence follows the same pattern but for a different workflow. Keep schemas independent — don't try to unify.

4. **qmd ↔ context-folding**: qmd's break-point scoring algorithm for markdown chunking (H1=100, H2=90...H6=50, code=80, with squared-distance decay) is directly applicable to context-folding segment boundary detection. If qmd is deployed, extract this algorithm as a reference for context-folding Phase 3c. Note this in `context-folding-progressive.md`.

5. **Root-archetype companion**: The linter and template patterns from this work are being upstreamed via `/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md`. **Updated 2026-04-07**: epyc-root is now the proving ground — build project-wiki skill here first (Phase 5a-c), validate on our ~5.2 MB / 275-file KB, then extract to root-archetype (Phase 5d). This reverses the original sequencing which treated epyc-root as a later migration target.

6. **epyc-root IS an LLM wiki**: Audit (2026-04-07) confirms 277 intake entries + 154 handoffs + 87 progress logs + 25 deep-dives = ~99.5k lines of LLM-compiled knowledge. **Updated 2026-04-07**: All three gaps now closed — query operation via `query_wiki.py`, lint operation via `lint_wiki.py` (5 passes), scaling thresholds in `wiki.yaml`. Remaining gap: semantic search (qmd deployment, Phase 3, deferred P2).

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
| Wiki config | `wiki.yaml` |
| Living taxonomy + aliases | `wiki/SCHEMA.md` |
| Project-wiki skill | `.claude/skills/project-wiki/SKILL.md` |
| KB linter (5 passes) | `.claude/skills/project-wiki/scripts/lint_wiki.py` |
| KB query helper | `.claude/skills/project-wiki/scripts/query_wiki.py` |
| Research-intake skill | `.claude/skills/research-intake/SKILL.md` |
| Intake schema reference | `.claude/skills/research-intake/references/intake-schema.md` |
| Cross-reference map | `.claude/skills/research-intake/references/cross-reference-map.md` |
| Intake validator | `.claude/skills/research-intake/scripts/validate_intake.py` |
| Intake index | `research/intake_index.yaml` |
| Taxonomy (legacy) | `research/taxonomy.yaml` |
| Context-folding handoff | `handoffs/active/context-folding-progressive.md` |
| Root-archetype companion | `/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md` |
| Root-archetype wiki template | `/mnt/raid0/llm/root-archetype/_templates/wiki.yaml.template` |
| Root-archetype project-wiki skill | `/mnt/raid0/llm/root-archetype/.claude/skills/project-wiki/` |

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
