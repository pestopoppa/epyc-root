# Repo-Readiness Scorer (Agent-Readiness Model)

**Status**: v1 deterministic scorer landed 2026-06-13; first report generated; deterministic remediation queue export landed in root commit `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2`; advisory Markdown queue rendering and refreshed 2026-06-20 queue artifacts are live. Passive AutoPilot pickup JSON landed 2026-06-21; it is planning context only (`mode=advisory_only`, `authority_gate=false`) and is not a live controller input or acceptance gate.
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
- Integration target: a `/readiness-fix`-analog autopilot remediation queue, or a passive dashboard alongside the tier-segregated Pareto dashboard? **Partially answered**: `--output-remediation-json` exports a deterministic remediation queue; `--output-autopilot-remediation-json` now emits a passive AutoPilot pickup artifact with explicit non-authority metadata. Live AutoPilot consumption still requires a separate protocol/default-off gate.

## Current Artifacts

- Scorer: `/mnt/raid0/llm/epyc-root/scripts/validate/repo_readiness_scorer.py`
- Tests: `/mnt/raid0/llm/epyc-root/tests/validate/test_repo_readiness_scorer.py`
- JSON report: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_2026-06-21.json`
- Markdown report: `/mnt/raid0/llm/epyc-root/progress/2026-06/repo-readiness-2026-06-21.md`
- Remediation queue export: `scripts/validate/repo_readiness_scorer.py --output-remediation-json <path>` (landed in root `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2`)
- Current remediation queue JSON: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_remediation_queue_2026-06-20.json`
- Current remediation queue Markdown: `/mnt/raid0/llm/epyc-root/progress/2026-06/repo-readiness-remediation-2026-06-20.md`
- Current passive AutoPilot pickup JSON: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_autopilot_pickup_2026-06-21.json`

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

2026-06-20 advisory-queue rendering update:

- Added `--output-remediation-md` plus `--remediation-md-limit` to render the deterministic queue as a Markdown pickup artifact while keeping JSON complete.
- Generated refreshed artifacts: `data/repo_readiness/repo_readiness_2026-06-20.json`, `progress/2026-06/repo-readiness-2026-06-20.md`, `data/repo_readiness/repo_readiness_remediation_queue_2026-06-20.json`, and `progress/2026-06/repo-readiness-remediation-2026-06-20.md`.
- Current queue: 49 open items; top P0 blockers include `epyc-inference-research` L3 style/test/task/dev-env/security gaps, `epyc-llama` L3 task/dev-env/security/experiment gaps, and `epyc-root` L5 auto-eval/self-optimizing-loop gaps. Markdown output is explicitly advisory and not an AutoPilot authority gate.
- Validation: GitNexus LOW on `score_repositories`, `build_remediation_queue`, and `render_markdown`; `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 7 passed; JSON and diff checks passed.

2026-06-21 passive AutoPilot pickup update:

- Added `--output-autopilot-remediation-json` plus `--autopilot-remediation-limit` to render the deterministic remediation queue as a passive planner-context artifact.
- Generated refreshed artifacts: `data/repo_readiness/repo_readiness_2026-06-21.json`, `progress/2026-06/repo-readiness-2026-06-21.md`, `data/repo_readiness/repo_readiness_remediation_queue_2026-06-21.json`, `progress/2026-06/repo-readiness-remediation-2026-06-21.md`, and `data/repo_readiness/repo_readiness_autopilot_pickup_2026-06-21.json`.
- Current pickup JSON carries `mode=advisory_only`, `authority_gate=false`, `source_item_count=49`, and the top 12 candidate items with required preflight rules (`review owning handoff`, GitNexus impact, generated/runtime artifact discipline, rerun scorer). This feeds planning only; it does not mutate AutoPilot or create a decision gate.
- Validation: GitNexus LOW on `build_remediation_queue`, `render_remediation_markdown`, `score_repositories`, and `main`; `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 9 passed; generated pickup JSON inspected with `jq` for passive-mode/non-authority fields.

2026-06-27 portability update:

- Root `19e1ac84` removes hardcoded canonical repo roots from the default scorer map.
- Default repo discovery now derives root from the script location, supports `/workspace/repos/<name>` fallbacks, keeps `/mnt/raid0/llm/...` as canonical fallback, and accepts explicit env overrides: `EPYC_ROOT_REPO`, `EPYC_ORCHESTRATOR_REPO`, `EPYC_INFERENCE_RESEARCH_REPO`, and `EPYC_LLAMA_REPO`.
- This is offline-only scorer hygiene; it does not change scoring criteria, remediation priorities, or AutoPilot authority.
- Validation: GitNexus LOW on implementation symbols per sidecar; main-thread verification `python3 -m py_compile scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py`; `uv run --with pytest pytest -q tests/validate/test_repo_readiness_scorer.py` -> 10 passed; `uv run --with ruff ruff check scripts/validate/repo_readiness_scorer.py tests/validate/test_repo_readiness_scorer.py` passed.

2026-06-27 research Standardized-gate update:

- `epyc-inference-research` commit `bfa785c` adds a top-level `Makefile`,
  `scripts/setup.sh`, and `.github/dependabot.yml`.
- The Makefile exposes green `lint` and `test` smoke targets over the
  maintained X-MAS function-axis table tooling instead of the legacy whole
  `scripts/` tree, which still has historical Ruff/pytest debt.
- `scripts/setup.sh` standardizes local setup through `uv sync --all-extras`;
  Dependabot adds weekly Python dependency security automation.
- A one-repo scorer run now reports `epyc-inference-research` as
  **Standardized (L3)** with L3 pass rate `88.9%`; the remaining L3 blocker is
  `L3.machine_task_index`.
- Validation: `make lint`; `make test`; `bash -n scripts/setup.sh`;
  `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

2026-06-27 research machine-task-index update:

- `epyc-inference-research` commit `7d778e0` adds
  `handoffs/active/master-handoff-index.md` as a research-scoped machine task
  index.
- The index includes a prioritized task list, dependency graph, cross-cutting
  concerns, reporting instructions, and key file locations. It explicitly
  avoids claiming authority over production flips, which remain governed from
  root/orchestrator handoffs.
- A one-repo scorer run now reports `epyc-inference-research` L3 at `100.0%`;
  the next gate is L4 Optimized with pass rate `55.6%`.
- Remaining blockers are L4 criteria: generated docs, health automation,
  analysis reports, and security audit. These should be implemented only as
  real workflow surfaces, not placeholders.
- Validation: `git diff --check -- handoffs/active/master-handoff-index.md`;
  research `make lint`; research `make test`;
  `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

## Notes

- Anti-false-positive discipline (shared across Factory's review/scoring features): a criterion passes only on a concrete, verifiable check — mirrors our eval-tower verifier philosophy.
- Cross-refs: `eval-tower-verification.md` (rubric discipline), `autopilot-continuous-optimization.md` (remediation loop), `claude-md-accounting` skill (governance coverage = a Documentation-pillar input), CLAUDE.md repo-map.
