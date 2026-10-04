# Research Intake

Process research material (papers, blog posts, repos) through the intake pipeline.

## Usage

```
/research-intake <url1> [url2] [url3] ...
```

## What It Does

1. **Stage 1:** fetches, deduplicates, cross-references, expands, and persists provisional entries as
   `stage1-unverified`.
2. **Stage 2:** deep-dives operator-selected sources against primary evidence and closes the
   dive-surfaced-source gate.
3. **Stage 3:** independently checks selected verified source mechanisms against current EPYC
   consumers before reconciling actionables into concrete operational changes/probes and justified
   enabling work. New plans carry the version-2 filing payload: opportunity scan, owner/task-text-bound
   outcome reviews, plan-only actionable additions and verbatim steering reconciliation. Apply the
   six-control rigor floor and separate implementation, evaluation and activation conditions.
   Only the plan file is written; mechanical checks do not replace main semantic review.
4. **Stage 4:** after operator approval, applies exactly the named changes and reconciles preserved
   steering/actionable state with the approved plan binding. Checkpoint cleanup follows reconciled,
   validated Stage-4 close-out; completed Stage-1 ingestion does not authorize deletion.

## Examples

```
/research-intake https://arxiv.org/abs/2402.12374
/research-intake https://arxiv.org/abs/2401.xxxxx https://arxiv.org/abs/2403.yyyyy
/research-intake https://github.com/user/repo
```

## Skill Reference

Full workflow defined in `.claude/skills/research-intake/SKILL.md`.
