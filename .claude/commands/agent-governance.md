# Agent Governance Workflow

Maintain alignment across prompts, CLAUDE accounting, hooks, and skills.

## Required Checks

```bash
python3 scripts/validate/validate_agents_structure.py
python3 scripts/validate/validate_agents_references.py
python3 scripts/validate/validate_claude_md_matrix.py
python3 scripts/validate/validate_doc_drift.py
```

## CLAUDE Accounting

When governance scope changes for any `CLAUDE.md` file:

1. Update `docs/reference/agent-config/CLAUDE_MD_MATRIX.md`
2. Update `docs/reference/agent-config/claude_md_matrix.json`
3. Keep root `CLAUDE.md` explicitly accounted for. If child-repo policy scope changes, verify the child repo directly; for llama.cpp use `repos/epyc-llama/CLAUDE.md`.

## Skill Surface Sync

When updating `.claude/commands/*`, verify the corresponding packaged skill under `.claude/skills/*` is still consistent.
