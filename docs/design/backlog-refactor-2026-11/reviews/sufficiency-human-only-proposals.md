# Human-only proposals — measurement-sufficiency principle project-wide (ws58, 2026-11-02)

These paths are listed in `coordination/session-bus/human_only_paths.yaml` (CLAUDE.md; AGENTS.md is a
symlink to CLAUDE.md, so Codex/opencode read the same file; agents/shared/*.md incl. MEASUREMENT_POLICY.md).
Not applied by the agent. Operator applies (or grants a token) — one command each.

## 1. CLAUDE.md (== AGENTS.md) — "Measurement & Claims"

```diff
@@ ## Measurement & Claims
 The [measurement constitution](MEASUREMENT.md) is authoritative (...). The measurement trust boundary is human-amendment-only.
+
+**Measurement sufficiency:** every measurement states its question, expected effect versus sample-size error, checkpoints, and stop-on-answer / stop-on-futility rules; reuse valid evidence first, save incremental results, stop when the scoped question is answered. Formal-gate cells stay futility-only at interim looks until OP-ABSEQ / OP-PQP / OP-ALPHAWIN are decided. Canonical: [`measurement-sufficiency.md`](docs/guides/agent-workflows/measurement-sufficiency.md).
```

## 2. agents/shared/MEASUREMENT_POLICY.md — "Producing new numbers"

```diff
@@ ## Producing new numbers
+- **Stop rule (every run)**: declare question/decision, expected effect vs sample-size error, checkpoints, stop-on-answer and stop-on-futility before launch; reuse valid evidence first; write incremental records; stop when the scoped question is answered (`docs/guides/agent-workflows/measurement-sufficiency.md`). **Formal-gate cells (promotion/ratification) are futility-only at interim looks** — no interim pass verdict — until the operator decides OP-ABSEQ / OP-PQP / OP-ALPHAWIN.
 - **Throughput**: only via the codified recipes ...
```

## 3. MEASUREMENT.md — no change proposed
The guide explicitly does not amend gates, sample counts or the trust boundary; the futility-only caveat
keeps formal gates as they are. If OP-ABSEQ is ratified, the sequential method belongs in an annex.
