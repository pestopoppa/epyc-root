# Root-Archetype: Linter Generalization + Brevity Templates Upstream

**Status**: REFRESHED 2026-05-28 — cleanup-only cross-repo upstreaming; local clone exists but has unrelated dirty files
**Created**: 2026-04-09
**Updated**: 2026-05-28 (blocker corrected; executor rules clarified)
**Priority**: MEDIUM
**Categories**: governance, upstream

---

## 2026-05-28 Audit Reset — Executor Start Here

This is not a root-repo implementation task. The epyc-root side is already done; remaining work is in `/mnt/raid0/llm/root-archetype`.

Current local state observed 2026-05-28:

- `/mnt/raid0/llm/root-archetype` exists.
- It has unrelated dirty log/progress files. Do not revert or fold those into this task.
- Open work remains the three cleanup items below.

Executor rules:

- Touch only root-archetype files needed for the linter/template upstreaming task.
- If the linter test fails because root-archetype's wiki layout differs, update the template/linter assumptions explicitly; do not special-case epyc-root paths.
- Update this handoff, `research-evaluation-index.md`, and the progress log after cross-repo work.

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

### 4. Wiki Compile Operation (DONE — 2026-04-14)
- Imported root-archetype's compile pipeline concept into epyc-root
- Created `compile_sources.py` (265 lines) adapted for epyc-root's flat directory layout
- Added Operation 3 (Compile) to `project-wiki` SKILL.md
- Added `compile:` section to `wiki.yaml`
- Compiled 24 wiki articles (327KB) from 219 sources
- Note: epyc-root version differs from root-archetype (flat dirs vs per-user dirs) — not a direct upstream candidate, but validates the pipeline design

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
