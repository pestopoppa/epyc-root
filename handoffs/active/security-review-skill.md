# Security-Review Skill (two-pass STRIDE + OWASP)

**Status**: stub
**Created**: 2026-06-03 (via research intake → factory.ai deep-dive)
**Categories**: agent_architecture, benchmark_methodology, tool_implementation

## Objective

Add a dedicated **security-review** skill (we have a general code-review skill but no security reviewer) that performs a two-pass, framework-driven security analysis of a diff or codebase, with exploit-path-gated severity to suppress false positives. The OWASP-LLM:2025 checklist is directly load-bearing for our own agent/orchestrator/autopilot stack.

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
- Scope presets (base-branch compare / uncommitted / specific commit / custom) — adopt all four?
- Does this become a `.claude/skills/security-review/` skill, a `/code-review`-style command, or both? Should it share the 8-gate filter + finding schema with the existing code-review skill (recommended)?
- CI integration: PR-summary + min-severity threshold gate — wire later.

## Notes

- Pairs with the **code-review 8-gate bug filter + P0–P3 + finding schema** upgrade to our existing code-review skill (harvest Part 3E) — adopt both together so they share the finding schema.
- Cross-refs: `eval-tower-verification.md` (two-pass = verifier), code-review skill, `privacy-hygiene-precommit-hooks.md` (secret scanning overlap), `feedback_observe_before_diagnosing`.
