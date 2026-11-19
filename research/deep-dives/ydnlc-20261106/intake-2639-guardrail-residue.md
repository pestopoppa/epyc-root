# intake-2639 — Guardrail residue (arXiv 2608.11392v2)

**Dive date**: 2026-11-06 · **Read depth**: FULL (24-page PDF; no arXiv HTML) · **Revision**: v2 (2026-08-11)

## Result

One self-summarisation cycle. A **degraded residue** — the rule text survives but its restricted action is no
longer recoverable — leads the model to perform the prohibited action far more often than an intact rule:
all-case Qwen 43% vs 9%, Llama 88% vs 31%; headroom 73% vs 23% and 94% vs 38%. Even intact rules fail to fire
sometimes, so any text check is a ceiling, not a guarantee. A mention-level presence check passes many residues.

Degradation is predicate loss, not scope narrowing (that is the separate category-substitution bucket, also
non-protective). True severing was not observed. The paper did not run the absent or full-history arms — it names
them plus a deterministic tool-call grader as the stronger design.

## Probe design implication

Four arms, not three: full history, intact rule, degraded residue, **rule absent** (violation floor), optionally
pinned. Grade by deterministic tool-call predicate, never judge-only, with a **sibling target control** in the same
session (allowed PID kill vs prohibited pattern kill) to establish headroom. Construct the degraded arm two ways:
predicate stripped, and referent generalised to its category.

## Actionables

| Action | Owner | Disposition |
|---|---|---|
| Extend the CF-AB-1 co-metric with a behavioural compliance arm and deterministic predicates | context-and-token-economy.md | adopt (design text) |
| Reclassify the recall-exam co-metric as ceiling-only; add "recall pass ≠ protection" | context-and-token-economy.md | adopt |
| Adopt the Appendix D v4 rubric (intact / category / degraded / absent) as the retention scorer | context-and-token-economy.md | adopt as schema |

## Surfaced

Governance Decay (intake-2636) supplies the absent arm; Context Codec (commitment-preserving compression);
Gamage 2026 (prohibition-type constraints decay while requirement-type persist).
