# Repo-Readiness Scorer (Agent-Readiness Model)

**Status**: stub
**Created**: 2026-06-03 (via research intake → factory.ai deep-dive)
**Categories**: benchmark_methodology, autonomous_research, knowledge_management

## Objective

Build a CPU-only scorer that rates each of our repos against an "agent-readiness" maturity model (adapted from Factory's Agent Readiness Model), so we can (a) quantify how amenable our codebase is to autonomous agents, (b) track it over time, and (c) feed failing criteria into the autopilot as a remediation queue. We have **no equivalent** today.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-657 | Factory.ai docs (Agent Readiness Model / `/readiness-report`) | high | adopt_patterns |

Full mining → [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 3E + verbatim rubric).

## The model (adapted from Factory)

**5 levels**, unlock the next by passing **80% of the prior level's criteria**:
1. **Functional** — runs, manual setup, little automated validation (README, linter, type checker, unit tests)
2. **Documented** — process written down (AGENTS.md/CLAUDE.md, devcontainer, pre-commit hooks, branch protection)
3. **Standardized** — processes enforced via automation (integration tests, secret scanning, tracing, metrics)
4. **Optimized** — fast feedback + data-driven improvement (fast CI, deploy frequency, flaky-test detection)
5. **Autonomous** — self-improving with orchestration

**9 technical pillars**: Style & Validation · Build System · Testing · Documentation · Dev Environment · Debugging & Observability · Security · Task Discovery · Product & Experimentation.

**Scoring**: fractional `n / sub-apps` (repository-scope criteria evaluated once; application-scope per sub-app). Our 4 sub-apps = epyc-root, epyc-orchestrator, epyc-inference-research, epyc-llama.

## Open Questions

- Factory does **not** publish the full per-criterion list (only the 5 levels, 9 pillars, 80% rule, scoring format, one example) — so we author our own criteria. What's the minimal credible criterion set per pillar?
- Where do we already score *high* (Task Discovery = handoff-index + kb-search; Product&Experimentation = autopilot Pareto archive; Observability = `logs/agent_audit.log` + `unified-trace-memory-service.md`) vs *low*? A first pass may mostly confirm strengths.
- Should detectors be pure shell/python file-presence + config-parse checks (cheap, deterministic) or LLM-judged (richer, noisier)? Lean deterministic per `feedback_observe_before_diagnosing`.
- Integration target: a `/readiness-fix`-analog autopilot remediation queue, or a passive dashboard alongside the tier-segregated Pareto dashboard?

## Notes

- Anti-false-positive discipline (shared across Factory's review/scoring features): a criterion passes only on a concrete, verifiable check — mirrors our eval-tower verifier philosophy.
- Cross-refs: `eval-tower-verification.md` (rubric discipline), `autopilot-continuous-optimization.md` (remediation loop), `claude-md-accounting` skill (governance coverage = a Documentation-pillar input), CLAUDE.md repo-map.
