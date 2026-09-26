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
3. **Stage 3:** reconciles every actionable, distills them into reusable primitives and cheap decision
   probes, maps consumers, applies the six-control rigor floor, and records trigger-based escalation
   paths. Only the reviewed plan file is written.
4. **Stage 4:** after operator approval, applies exactly the handoff, index, and intake-entry changes
   named by the plan.

## Examples

```
/research-intake https://arxiv.org/abs/2402.12374
/research-intake https://arxiv.org/abs/2401.xxxxx https://arxiv.org/abs/2403.yyyyy
/research-intake https://github.com/user/repo
```

## Skill Reference

Full workflow defined in `.claude/skills/research-intake/SKILL.md`.
