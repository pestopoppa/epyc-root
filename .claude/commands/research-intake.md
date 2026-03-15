# Research Intake

Process research material (papers, blog posts, repos) through the intake pipeline.

## Usage

```
/research-intake <url1> [url2] [url3] ...
```

## What It Does

1. Fetches and extracts claims/techniques from each URL
2. Deduplicates against the persistent intake index (`research/intake_index.yaml`)
3. Cross-references against chapters, handoffs, and experiments
4. Scores novelty and relevance
5. Expands literature (reference chasing, related work search, implementation discovery)
6. Updates matched active handoffs with new research context
7. Proposes handoff stubs for high-relevance new opportunities
8. Produces a structured report and appends to the index

## Examples

```
/research-intake https://arxiv.org/abs/2402.12374
/research-intake https://arxiv.org/abs/2401.xxxxx https://arxiv.org/abs/2403.yyyyy
/research-intake https://github.com/user/repo
```

## Skill Reference

Full workflow defined in `.claude/skills/research-intake/SKILL.md`.
