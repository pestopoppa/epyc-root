# Agent Execution Contract

This file is the top-level contract for agents working in the EPYC project.

## Project Structure

Use the canonical [repository map](../CLAUDE.md#repository-map) and dependency map
(`.claude/dependency-map.json`) for cross-repository placement and coupling.

## Scope

- This file is intentionally short.
- It points to canonical policy and workflow docs.
- It does not duplicate deep implementation details.

## Read Order

1. `agents/shared/OPERATING_CONSTRAINTS.md`
2. `agents/shared/MEASUREMENT_POLICY.md` (any task that produces or consumes performance/quality numbers)
3. `agents/shared/ENGINEERING_STANDARDS.md`
4. `agents/shared/WORKFLOWS.md`
5. `docs/guides/agent-workflows/INDEX.md`
6. Role file in `agents/*.md` relevant to the task — if you are coordinating other sessions on
   the session bus, that is `agents/coordinator-agent.md` plus
   `coordination/session-bus/BUS_PROTOCOL.md` (the contract)
7. Domain docs in `docs/` and current status in `CLAUDE.md`

## Non-Negotiables

- No writes outside `/mnt/raid0/` for LLM-related artifacts.
- Never run `pytest -n auto` on this host.
- Engineering invariants — feature flags, typed boundaries, tunable-vs-invariant numeric
  classification, no swallowed exceptions, small testable changes — are canonical in
  `agents/shared/ENGINEERING_STANDARDS.md` (read-order item 3), not restated here.
- Decisions gate on **claims**, not observations: a performance/quality number must cite a `MEASUREMENT.md` protocol; historical numbers are era-labeled first (`agents/shared/MEASUREMENT_POLICY.md`). Never edit historical records to "fix" them — append.
- **Fan out by default.** A main's own thread is for review, integration and task boundaries;
  execution goes to 3–5 concurrent subagents, model and effort matched to the task, and every result
  is PROPOSED work until its evidence and diffs are reviewed. Working serially is the defect. Full
  rule: [Parallel Subagent Fan-Out](shared/OPERATING_CONSTRAINTS.md#parallel-subagent-fan-out--the-default-working-mode-of-every-main).
- **Default is ACT — escalation must earn itself.** Before deferring, escalating, or writing a "Deferred /
  Open / Awaiting operator" item, name the specific decision only the operator can make, or the external
  event you await, in one sentence. If you cannot, **finish the work**. Find a bug → fix it; find a gap →
  close it. Work already approved is not re-openable by restating it as a question. An item recurring
  across two status reports with an unchanged blocker was never blocked. Full rule:
  [Act, Don't Defer](shared/OPERATING_CONSTRAINTS.md#act-dont-defer--the-admission-test-for-escalating-at-all).
- Operator input requests that pass that test follow the canonical [decision-package contract](shared/OPERATING_CONSTRAINTS.md#operator-decision-requests).

## Operator-Facing Language

Write all text for the operator in ASD-STE100 Simplified Technical English. This applies to
chat replies, status reports, decision packages, handoff prose, and commit messages.

- Use one approved meaning per word. Use the same word for the same thing every time.
- Use short sentences: 20 words maximum for procedures, 25 for descriptive text.
- Use the active voice. Name the agent of each action.
- Use one topic in each sentence. Use one instruction in each step.
- Write paragraphs of 6 sentences maximum.
- Use articles (`the`, `a`) and full clauses. Do not write telegraphic text.
- Use the simple verb tenses. Do not use `-ing` forms as nouns or as compound verbs.
- Do not use synonyms, idioms, jargon, or metaphor when a plain word is available.
- Keep technical names, command names, file paths, metric names, and quoted evidence exactly
  as they are. STE controls the prose around them, not the identifiers in them.
- Give warnings and cautions before the step that they apply to.

STE controls the FORM of the text. It does not change the content rules: the claim grammar in
`agents/shared/MEASUREMENT_POLICY.md` and the decision-package contract stay as they are.

## Output Contract

Each substantial task should end with:

1. What changed
2. Why this approach
3. Verification run (or why not run)
4. Risks and follow-up actions

## File Ownership Model

- `agents/shared/*.md`: cross-cutting policy and reusable workflows.
- `agents/*.md`: role behavior and role-specific playbooks.
- `docs/`: long-lived system-of-record knowledge.

If guidance conflicts:

1. Safety constraints win.
2. Architectural invariants win.
3. Role guidance applies next.
4. Local task prompt resolves remaining ambiguity.

## Validation Commands

- `python3 scripts/validate/validate_agents_structure.py`
- `python3 scripts/validate/validate_agents_references.py`
- `python3 scripts/validate/validate_claude_md_matrix.py`
