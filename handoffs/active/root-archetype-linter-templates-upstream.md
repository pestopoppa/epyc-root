# Root-Archetype: Linter Generalization + Brevity Templates Upstream

**Status**: in-progress
**Created**: 2026-04-09
**Priority**: MEDIUM
**Categories**: governance, upstream

---

## Objective

Upstream proven governance patterns from epyc-root to root-archetype for use by all Claude Code projects.

## Components

### 1. Generalized KB Linter (DONE)
- Removed hardcoded `parents[4]` root detection — now walks up to wiki.yaml/.git
- Configurable paths via wiki.yaml `lint.paths` section
- Configurable index patterns via `lint.index_patterns`
- File: `.claude/skills/project-wiki/scripts/lint_wiki.py`

### 2. Brevity Templates (DONE)
- Format-specific word limits (not vague "be concise")
- Templates at `_templates/prompts/`:
  - `worker_general.md.template` — MC, yes/no, factual, open-ended limits
  - `worker_math.md.template` — MC, numeric, proof limits
  - `thinking_reasoning.md.template` — <50w answer suffix
  - `BREVITY_ADOPTION.md` — adoption guide with research basis

### 3. wiki.yaml.template (PREVIOUSLY DONE)
- Already exists at `_templates/wiki.yaml.template`

## Remaining Work
- [ ] Test generalized linter against root-archetype's own wiki structure
- [ ] Update init-project.sh to copy brevity templates during project scaffold
- [ ] Document in root-archetype README

## Cross-References
| Handoff | Relationship |
|---------|-------------|
| reasoning-compression.md | Actions 12-13 are the source for brevity templates |
| knowledge-base-governance-improvements.md | Phase 5 is the source for linter |
| research-evaluation-index.md | Action 15 upstream tracking |
