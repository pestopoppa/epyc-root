# Security-Review Skill (two-pass STRIDE + OWASP)

**Status**: v1 skill scaffold landed 2026-06-13; CI/command integration deferred
**Created**: 2026-06-03 (via research intake → factory.ai deep-dive)
**Categories**: agent_architecture, benchmark_methodology, tool_implementation

## Objective

Add a dedicated **security-review** skill (we have a general code-review skill but no security reviewer) that performs a two-pass, framework-driven security analysis of a diff or codebase, with exploit-path-gated severity to suppress false positives. The OWASP-LLM:2025 checklist is directly load-bearing for our own agent/orchestrator/autopilot stack.

## Implementation Status

**Landed 2026-06-13**:

- `.claude/skills/security-review/SKILL.md`
- `.claude/skills/security-review/agents/openai.yaml`

The v1 skill covers the Factory-derived mechanism:

- STRIDE + OWASP Web/API Top 10 + OWASP LLM Top 10 2025 + supply-chain checks.
- Two-pass candidate discovery and exploit validation.
- P0/P1/P2/P3 severity mapped to concrete exploit-path gates.
- Structured finding schema: title, location, problem, exploit path, suggested fix, residual risk, checks run.
- Explicit false-positive guard: do not emit a finding unless attacker capability, reachability, trust-boundary crossing, vulnerable sink, unblocked mitigation analysis, concrete impact, minimal fix, and file/line evidence all pass.

Decision: no separate slash command or CI gate in v1. The skill is sufficient for manual/autonomous review invocation; CI and PR-summary integration stay deferred until a concrete enforcement workflow exists.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-658 | Factory.ai code-review benchmark + security-review feature | high | adopt_patterns |

Full mining → [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 3E).

## Mechanism to reproduce (from Factory's `security-reviewer`)

- **Frameworks (checklists)**: STRIDE (Spoofing/Tampering/Repudiation/Info-Disclosure/DoS/EoP) + OWASP Top10:2021 + **OWASP Top10-LLM:2025** (prompt injection, excessive agency, insecure output handling, embedding weaknesses) + supply-chain (lockfiles, typosquatting, install scripts, broad version ranges, brand-new deps).
- **Two-pass**: pass 1 = trace changed data flows across the 7 trust boundaries (auth, authz, validation, database, network, filesystem, **LLM**) → candidate findings; pass 2 = **validate each candidate for reachability/exploitability** before emitting (anti-FP, same verifier discipline as eval-tower).
- **Severity = Critical/High/Medium/Low ↔ P0–P3, each requiring a concrete exploit path** (built-in FP suppression).
- **Structured finding schema** (shared with the code-review 8-gate upgrade): title ≤80 imperative / problem / file+line / severity / suggested fix / 1–3 sentence overall assessment → eval-gradeable.
- Optional per-repo `threat-model.md` injected as focusing context.

## Open Questions

- Which local model(s) drive it? OWASP-LLM analysis of our own stack ideally uses a cross-family reviewer (avoid self-blindness) — tie to eval-tower EV-6.
- Scope presets (base-branch compare / uncommitted / specific commit / custom) — skill text supports all four by scope, but no wrapper command exists yet.
- Existing code-review skill upgrade — no local `.claude/skills/code-review` exists in this repo. The reusable 8-gate filter and finding schema live in `security-review/SKILL.md`; fold them into a future code-review skill if/when one is added.
- CI integration: PR-summary + min-severity threshold gate — wire later.

## Notes

- Pairs with the **code-review 8-gate bug filter + P0–P3 + finding schema** upgrade to our existing code-review skill (harvest Part 3E) — adopt both together so they share the finding schema.
- Cross-refs: `eval-tower-verification.md` (two-pass = verifier), code-review skill, `privacy-hygiene-precommit-hooks.md` (secret scanning overlap), `feedback_observe_before_diagnosing`.
