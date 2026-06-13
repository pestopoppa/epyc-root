# Safety

**Category**: `safety`
**Confidence**: verified
**Last compiled**: 2026-06-13
**Sources**: 4 documents

## Summary

Safety in the current EPYC stack is mostly about agentic trust boundaries: what external text may influence, which generated findings are allowed to become action items, and how review tools suppress false positives. The Fable 5 frontier review promoted one specific risk from background concern to concrete work: research intake and web research ingest arbitrary external text, then future agents read the resulting handoffs with repo-write authority. That makes source text an instruction-injection surface unless it is explicitly treated as data.

The first hardening pass is complete. External content is now policy-scoped as data, rendered in `SOURCE-QUARANTINE` blocks with provenance metadata, checked by a warn-mode validator, and covered by a synthetic canary. The orchestrator `web_research` path also quarantines source-derived synthesis before it enters downstream agent context. This is intentionally not a history rewrite; old handoffs remain historical, and the convention applies to new intake/research outputs.

Security review has a separate but complementary tool surface. The v1 security-review skill runs STRIDE, OWASP Web/API Top 10, OWASP LLM Top 10 2025, and supply-chain checks, then validates exploitability before emitting findings. Severity is gated by concrete exploit paths, which keeps the skill aligned with the project's general verifier discipline.

## Key Findings

- **External content is data, not instructions.** A source may be quoted, summarized, and cited, but not copied into action positions unless an operator or project agent explicitly authors the instruction outside quarantine. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **Quarantine needs provenance.** New source-derived blocks carry URL, retrieval timestamp, and SHA prefix, making later review and validator warnings traceable. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **Security-review findings require exploit validation.** The security skill's two-pass design avoids listing theoretical issues unless attacker capability, reachability, trust boundary crossing, vulnerable sink, mitigation bypass, concrete impact, minimal fix, and file/line evidence are all present. Source: [security-review-skill.md](../handoffs/active/security-review-skill.md).
- **Safety work composes with the evidence plane.** Injection hardening prevents adversarial narrative contamination; the evidence plane prevents accidental narrative contamination from re-entering planner memory. Both are provenance problems. Sources: [Fable 5 executive summary](../handoffs/active/fable5-findings-00-executive-summary.md), [evidence-plane-event-sourcing-and-narrative.md](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md).

## Open Questions

- When should the warn-mode injection validator become blocking? It needs false-positive data from real intake diffs first.
- Should the security-review skill gain a wrapper command or CI gate, or remain manual until a concrete enforcement workflow exists?
- Which local reviewer model is best for OWASP-LLM analysis of the EPYC stack without self-blindness?

## Related Categories

- [Tool Implementation](tool-implementation.md) — security-review and quarantine validators are tooling surfaces.
- [Agent Architecture](agent-architecture.md) — lab jobs and intake workflows must preserve trust boundaries.
- [Knowledge Management](knowledge-management.md) — source provenance determines whether compiled wiki facts are safe to reuse.

## Source References

- [Frontier F5 intake injection hardening](../handoffs/completed/frontier-f5-intake-injection-hardening.md) — completed quarantine policy, renderer, validator, and canary.
- [Security-review skill](../handoffs/active/security-review-skill.md) — two-pass STRIDE/OWASP/LLM/supply-chain review skill.
- [Fable 5 executive summary](../handoffs/active/fable5-findings-00-executive-summary.md) — evidence-plane framing.
- [Evidence-plane event sourcing and narrative](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md) — provenance-first narrative regeneration plan.
