# Repo-Readiness Scorer (Agent-Readiness Model)

**Status**: v1 deterministic scorer landed 2026-06-13; first report generated; deterministic remediation queue export landed in root commit `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2`; AutoPilot consumption remains future work
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

- Factory does **not** publish the full per-criterion list (only the 5 levels, 9 pillars, 80% rule, scoring format, one example) — so we authored a v1 criteria catalog: one concrete deterministic criterion per pillar per level (45 total).
- Where do we already score *high* (Task Discovery = handoff-index + kb-search; Product&Experimentation = autopilot Pareto archive; Observability = `logs/agent_audit.log` + `unified-trace-memory-service.md`) vs *low*? A first pass may mostly confirm strengths.
- Should detectors be pure shell/python file-presence + config-parse checks (cheap, deterministic) or LLM-judged (richer, noisier)? **Decision for v1**: deterministic only per `feedback_observe_before_diagnosing`; a pass means an artifact exists, not that quality is certified.
- Integration target: a `/readiness-fix`-analog autopilot remediation queue, or a passive dashboard alongside the tier-segregated Pareto dashboard? **Partially answered**: `--output-remediation-json` now exports a deterministic remediation queue; wiring that queue into AutoPilot or a dashboard remains next work.

## Current Artifacts

- Scorer: `/mnt/raid0/llm/epyc-root/scripts/validate/repo_readiness_scorer.py`
- Tests: `/mnt/raid0/llm/epyc-root/tests/validate/test_repo_readiness_scorer.py`
- JSON report: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_2026-06-13.json`
- Markdown report: `/mnt/raid0/llm/epyc-root/progress/2026-06/repo-readiness-2026-06-13.md`
- Remediation queue export: `scripts/validate/repo_readiness_scorer.py --output-remediation-json <path>` (landed in root `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2`)

2026-06-13 first-run summary:

- Portfolio level: **Documented (L2)**.
- `epyc-root`: Optimized (L4), next gate Autonomous.
- `epyc-orchestrator`: Documented (L2), next gate Standardized.
- `epyc-inference-research`: Documented (L2), next gate Standardized.
- `epyc-llama`: Documented (L2), next gate Standardized.
- Lowest portfolio criteria: L3 security automation and standardized dev environment; L4 generated docs, health automation, prioritized task discovery, and security audit; L5 agent doc loop, auto eval gates, autonomous security review, self-optimizing loop.

Validation:

- `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`
- `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 3 passed.

2026-06-14 remediation-export update:

- Root commit `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2` added deterministic remediation queues via `--output-remediation-json`.
- Changed files: `/workspace/scripts/validate/repo_readiness_scorer.py` and `/workspace/tests/validate/test_repo_readiness_scorer.py`.
- Validation from the implementation sidecar: `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 5 passed.
- Remaining integration work: feed the exported queue into AutoPilot remediation planning or a passive dashboard without letting the scorer become a decision gate without a protocol.

## Notes

- Anti-false-positive discipline (shared across Factory's review/scoring features): a criterion passes only on a concrete, verifiable check — mirrors our eval-tower verifier philosophy.
- Cross-refs: `eval-tower-verification.md` (rubric discipline), `autopilot-continuous-optimization.md` (remediation loop), `claude-md-accounting` skill (governance coverage = a Documentation-pillar input), CLAUDE.md repo-map.
