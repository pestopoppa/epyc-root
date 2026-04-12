---
name: agent-file-architecture
description: Design, refactor, and validate project agent files using a thin-map architecture (shared policy plus lean role overlays). Use when creating/updating `agents/*.md`, splitting monolithic agent instructions, enforcing role schema, or migrating long operational guidance into docs.
---

# Agent File Architecture

Use this skill for work in `agents/`.

Use when:

- Refactoring role prompts into schema-driven overlays.
- Moving duplicated policy into `agents/shared/`.
- Splitting long operational content into docs.

Do not use when:

- Implementing runtime code features in `src/` or `orchestration/`.
- Changing benchmark/model behavior unrelated to prompt architecture.

## Workflow

1. Apply the role schema in `references/schema.md`.
2. Use migration guidance in `references/migration.md`.
3. Run `scripts/validate_agents.py`.
4. If validation fails, fix schema or references before finalizing.

## Boundaries

- Keep role files concise.
- Keep cross-cutting policy in `agents/shared/`.
- Keep long operational details in `docs/guides/agent-workflows/`.

## Verification Gates

### Step 1 — Apply Role Schema
- Evidence: Each role file in `agents/*.md` contains all 6 required headers from `references/schema.md`.
- Gate: Schema compliance confirmed before Step 2.

### Step 2 — Migration Guidance
- Evidence: (1) No duplicated policy across role files, (2) operational blocks >20 lines moved to `docs/guides/agent-workflows/`, (3) cross-cutting policy in `agents/shared/`.
- Gate: Migration complete before Step 3.

### Step 3 — Run Validation
- Evidence: `scripts/validate_agents.py` returns exit code 0 (runs both structure and reference validators).
- Gate: Exit code 0 from both sub-validators.

### Step 4 — Fix and Re-validate
- Evidence: If Step 3 failed, errors listed, fixes applied, re-validation passes.
- Gate: Final validation pass is clean. Run the script again — no "it should be fine now."

## Anti-Rationalization

| Excuse | Rebuttal |
|--------|----------|
| "This role file is small enough, I don't need the schema check" | The schema defines 6 required headers. Even a 10-line file can miss required sections. Run the check. |
| "The duplicated policy is only in two files" | Two is when extraction should happen. Move it to `agents/shared/` now. |
| "This operational content is short enough to stay in the role file" | The question is kind, not length. Operational procedures belong in `docs/guides/agent-workflows/`. |
| "Validation failed but the error is cosmetic" | Cosmetic failures become semantic drift. Fix all validation errors before finalizing. |
| "I'll fix the broken references later" | Broken references mean agents get pointed at missing guidance and fail silently. Fix now. |
| "This role doesn't need all six headers — it's simple" | Simple roles still need all headers. An empty `## Inputs Required` communicates "needs no inputs" — omitting communicates nothing. |
