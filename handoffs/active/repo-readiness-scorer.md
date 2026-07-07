# Repo-Readiness Scorer (Agent-Readiness Model)

**Status**: v1 deterministic scorer landed 2026-06-13; deterministic remediation queue export, advisory Markdown rendering, passive AutoPilot pickup JSON, root no-inference candidate eval gate, dashboard summary, and default-off AutoPilot planner advisory bridge are live. Current 2026-07-06 artifacts show `epyc-root`, `epyc-orchestrator`, and `epyc-inference-research` at Autonomous/L5; `epyc-llama` remains Standardized/L3 with six blocking L4 workflow-surface gaps. The passive pickup artifact remains planning context only (`mode=advisory_only`, `authority_gate=false`) and is not an acceptance gate, promotion gate, or substitute for a true self-optimization loop. Future launches through `scripts/autopilot/start_fable_authority_daemon.py` inject the newest passive pickup unless `AUTOPILOT_REPO_READINESS_PICKUP` is explicitly set.
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
- Integration target: a `/readiness-fix`-analog autopilot remediation queue, or a passive dashboard alongside the tier-segregated Pareto dashboard? **Answered for passive consumption**: `--output-remediation-json` exports a deterministic remediation queue; `--output-autopilot-remediation-json` emits a passive AutoPilot pickup artifact with explicit non-authority metadata; the dashboard reads the latest report/queue; and the Fable authority launcher now wires the newest pickup into the planner prompt on future restarts. Any authority-bearing remediation workflow remains a separate protocol.

## Current Artifacts

- Scorer: `/mnt/raid0/llm/epyc-root/scripts/validate/repo_readiness_scorer.py`
- Tests: `/mnt/raid0/llm/epyc-root/tests/validate/test_repo_readiness_scorer.py`
- JSON report: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_2026-07-06.json`
- Markdown report: `/mnt/raid0/llm/epyc-root/progress/2026-07/repo-readiness-2026-07-06.md`
- Remediation queue export: `scripts/validate/repo_readiness_scorer.py --output-remediation-json <path>` (landed in root `7e6b3ee18864f1d86e8b5ce4651449a5fd7c8ee2`)
- Current remediation queue JSON: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_remediation_queue_2026-07-06.json`
- Current remediation queue Markdown: `/mnt/raid0/llm/epyc-root/progress/2026-07/repo-readiness-remediation-2026-07-06.md`
- Current passive AutoPilot pickup JSON: `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_autopilot_pickup_2026-07-06.json`

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
- A one-repo scorer run reported `epyc-inference-research` L3 at `100.0%`;
  the next gate was L4 Optimized with pass rate `55.6%`.
- Validation: `git diff --check -- handoffs/active/master-handoff-index.md`;
  research `make lint`; research `make test`;
  `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

2026-06-27 research health-automation update:

- `epyc-inference-research` commit `2b6b97f` adds
  `scripts/session/health_check.sh` and exposes it as `make health`.
- The health check is no-inference: it verifies required repo paths, `uv`
  availability, maintained Python entrypoints, and dry-runs AA-Omniscience plus
  clean-window manifest generation into `/tmp`.
- A one-repo scorer run now reports `epyc-inference-research` L4 at `66.7%`;
  `L4.health_automation` passes.
- Remaining L4 blockers are `L4.generated_docs`, `L4.analysis_reports`, and
  `L4.security_audit`. These should be implemented only as real workflow
  surfaces, not placeholders.
- Validation: GitNexus impact for research `Makefile` LOW
  (`impactedCount=0`); research `make health`; research `make lint`; research
  `make test`; `repo_readiness_scorer.py --repo epyc-inference-research=/mnt/raid0/llm/epyc-inference-research`.

2026-06-27 research generated-docs update:

- `epyc-inference-research` commit `935a8ea` adds
  `scripts/docs/generate_docs_index.py`, `scripts/docs/test_generate_docs_index.py`,
  `make docs`, `make docs-check`, and the generated
  `docs/reference/GENERATED_DOCS_INDEX.md` artifact.
- The generated-docs lane is deterministic and no-inference: `--check` fails when
  the committed index is stale.
- A one-repo scorer run now reports `L4.generated_docs` as passing for
  `epyc-inference-research`.
- Remaining L4 blockers are `L4.analysis_reports` and `L4.security_audit`.
- Validation: research `uv run --with ruff ruff check
  scripts/docs/generate_docs_index.py scripts/docs/test_generate_docs_index.py`;
  `uv run --with pytest pytest -q scripts/docs/test_generate_docs_index.py`;
  `make docs-check`; `make lint`; `make test`; and the root one-repo readiness
  scorer for `epyc-inference-research`.

2026-06-27 research analysis-reports update:

- `epyc-inference-research` commit `f347809` adds
  `scripts/analysis/generate_analysis_reports_index.py`,
  `scripts/analysis/test_generate_analysis_reports_index.py`, `make analysis`,
  `make analysis-check`, and the generated
  `docs/reference/ANALYSIS_REPORTS_INDEX.md` artifact.
- The analysis-reports lane is deterministic and no-inference: it indexes
  existing Markdown/JSON analysis/report/summary artifacts and `--check` fails
  when the committed index is stale.
- A one-repo scorer run now reports `epyc-inference-research` as Optimized (L4)
  with L4 pass rate `88.9%`; `L4.analysis_reports` passes.
- Remaining L4 blocker is `L4.security_audit`.
- Validation: research `uv run --with ruff ruff check
  scripts/analysis/generate_analysis_reports_index.py
  scripts/analysis/test_generate_analysis_reports_index.py`; `uv run --with
  pytest --with pyyaml pytest -q
  scripts/analysis/test_generate_analysis_reports_index.py`; `make
  analysis-check`; `make lint`; `make test`; and the root one-repo readiness
  scorer for `epyc-inference-research`.

2026-06-27 research security-audit update:

- `epyc-root` commit `f077b197` teaches the deterministic scorer to count
  concrete `scripts/security/**` audit surfaces for `L4.security_audit`.
- `epyc-inference-research` commit `7638f0b` adds
  `scripts/security/audit_repository.py`,
  `scripts/security/test_audit_repository.py`, and `make security-check`.
- The audit is no-inference and scans tracked files only. It fails on
  secret-like tracked filenames, high-confidence credential literals in
  source/config/doc surfaces, and unexpected large tracked artifacts outside
  known benchmark result/image paths.
- A one-repo scorer run now reports `epyc-inference-research` as Optimized (L4)
  with L4 pass rate `100.0%`; the next gate is L5 Autonomous.
- Validation: research `python3 -m py_compile
  scripts/security/audit_repository.py
  scripts/security/test_audit_repository.py`; `uv run --with pytest pytest -q
  scripts/security/test_audit_repository.py`; `make security-check`; `uv run
  --with ruff ruff check scripts/security/audit_repository.py
  scripts/security/test_audit_repository.py`; `make lint`; `make test`; and the
  root one-repo readiness scorer for `epyc-inference-research`.

2026-06-28 orchestrator setup-gate update:

- `epyc-orchestrator` commit `c1cac72e` adds a top-level `scripts/setup.sh`
  entrypoint that delegates to the existing `scripts/setup/bootstrap.sh`.
- The bootstrap prerequisite check now accepts `uv`, `pip3`, or `pip` for the
  Python package manager prerequisite, matching the existing install path that
  already prefers `uv sync`.
- A one-repo scorer run now reports `epyc-orchestrator` as Standardized (L3)
  with L3 pass rate `88.9%`; the next gate is L4 Optimized.
- Remaining orchestrator blockers include `L3.security_automation` and L4
  workflow surfaces (`L4.generated_docs`, `L4.health_automation`,
  `L4.security_audit`, `L4.prioritized_tasks`). These should be implemented as
  real maintained surfaces rather than placeholders.
- Validation: GitNexus impact for `scripts/setup.sh`,
  `scripts/setup/bootstrap.sh`, and `check_prerequisites` returned UNKNOWN
  targets with `impactedCount=0`; `bash -n scripts/setup.sh
  scripts/setup/bootstrap.sh`; `./scripts/setup.sh --check-only`; and the root
  one-repo readiness scorer for
  `epyc-orchestrator=/mnt/raid0/llm/epyc-orchestrator`.

2026-06-28 default-off AutoPilot advisory bridge:

- `epyc-orchestrator` adds a default-off planner prompt section for passive
  repo-readiness pickup artifacts.
- The bridge is inert unless `AUTOPILOT_REPO_READINESS_PICKUP` points to a JSON
  artifact. It accepts only `mode=advisory_only` with `authority_gate=false` and
  otherwise renders an ignored/unavailable message.
- The rendered section is planner context only: it explicitly does not override
  owning handoffs, GitNexus impact checks, measurement gates, or scorer reruns.
- This closes the first safe live-consumption protocol for the passive pickup
  artifact without making repo-readiness a controller authority or acceptance
  gate. Existing running AutoPilot processes will not see it until a future
  restart with the env var set.
- Validation: GitNexus impact for `CONTROLLER_PROMPT_TEMPLATE` and
  `_run_loop_inner` returned LOW; `uv run pytest
  tests/unit/test_autopilot_actions.py tests/unit/test_autopilot_system_card.py
  -q` -> 82 passed; `uv run ruff check scripts/autopilot/autopilot.py
  tests/unit/test_autopilot_actions.py`; `python3 -m py_compile
  scripts/autopilot/autopilot.py tests/unit/test_autopilot_actions.py`.

2026-06-28 orchestrator security automation/audit update:

- `epyc-orchestrator` adds `.github/dependabot.yml` for weekly `uv` and
  GitHub Actions dependency updates, closing the deterministic
  `L3.security_automation` criterion with a real supply-chain automation
  surface.
- `epyc-orchestrator` adds `scripts/security/audit_repository.py`,
  `scripts/security/test_audit_repository.py`, and `make security-check`.
  The audit is no-inference and scans tracked files only. It fails on
  secret-like tracked filenames, high-confidence credential literals in
  source/config/doc/test surfaces, and unexpected large tracked artifacts
  outside known benchmark/report/repl-memory paths. The only secret-literal
  allowlist is the existing credential-redaction fixture test.
- A one-repo scorer run now reports `epyc-orchestrator` with
  `L3.security_automation=true`, `L4.security_audit=true`, and L3 pass rate
  `100.0%`. Remaining L4 blockers are `L4.generated_docs`,
  `L4.health_automation`, and `L4.prioritized_tasks`.
- Validation: GitNexus impact for the new security/dependabot targets returned
  UNKNOWN with `impactedCount=0`; `python3 -m py_compile
  scripts/security/audit_repository.py scripts/security/test_audit_repository.py`;
  `uv run --with pytest pytest -q scripts/security/test_audit_repository.py`
  -> 4 passed; `uv run --with ruff ruff check
  scripts/security/audit_repository.py scripts/security/test_audit_repository.py`;
  `make security-check`; `git diff --check` on the touched paths; and the root
  one-repo readiness scorer for
  `epyc-orchestrator=/mnt/raid0/llm/epyc-orchestrator`.

2026-06-28 orchestrator L4 closeout:

- `epyc-orchestrator` adds deterministic generated-docs, health, and local task
  coordination surfaces:
  `scripts/docs/generate_docs_index.py`,
  `scripts/docs/test_generate_docs_index.py`,
  `docs/reference/GENERATED_DOCS_INDEX.md`,
  `scripts/session/health_check.sh`, and
  `handoffs/active/master-handoff-index.md`.
- The generated-docs lane indexes committed `docs/**/*.md` files and supports
  `--check`; Makefile targets now expose `docs`, `docs-check`, and `health`.
- The session health lane is no-inference: it checks core repo artifacts,
  py-compiles stack/phase/security health entrypoints, and runs the tracked-file
  security audit.
- The local handoff index is explicitly subordinate to the root master index and
  carries prioritized tasks, dependencies, cross-cutting concerns, reporting
  rules, and key files for orchestrator-only work.
- A one-repo scorer run now reports `L4.generated_docs=true`,
  `L4.health_automation=true`, `L4.prioritized_tasks=true`, and the only
  remaining failed orchestrator criterion as `L5.autonomous_security_review`.
- Validation: GitNexus impact for existing `Makefile` returned LOW; new-target
  GitNexus checks for docs/health/index paths returned UNKNOWN with
  `impactedCount=0`; `python3 -m py_compile` for docs/security scripts and
  tests; `uv run --with pytest pytest -q scripts/docs/test_generate_docs_index.py`
  -> 2 passed; `uv run --with ruff ruff check
  scripts/docs/generate_docs_index.py scripts/docs/test_generate_docs_index.py`;
  `make health`; `make security-check`; `make docs-check`; `git diff --check`;
  and the root one-repo readiness scorer for `epyc-orchestrator`.

2026-06-28 orchestrator autonomous-security-review closeout:

- `epyc-orchestrator` commit `4b27fd5d` adds an orchestrator-scoped
  security-review skill and slash command:
  `.claude/skills/security-review/SKILL.md`,
  `.claude/skills/security-review/agents/openai.yaml`, and
  `.claude/commands/security-review.md`.
- The skill is exploit-path gated and specific to orchestrator attack
  surfaces: API/OpenAI-compatible routes, AutoPilot/controller paths,
  StrategyStore and runtime state, tool/REPL/MCP execution, stack launch/config
  surfaces, generated artifacts, dependencies, and shell/CI changes.
- A one-repo scorer run now reports `epyc-orchestrator` as **Autonomous (L5)**
  with all level rates at `1.0`, including
  `L5.autonomous_security_review=true`.
- Validation: new-file GitNexus impact checks returned UNKNOWN with
  `impactedCount=0`; skill frontmatter and `agents/openai.yaml` parsed with
  PyYAML; path-scoped `git diff --check` passed; and the root one-repo
  readiness scorer for `epyc-orchestrator` reported no failed criteria.

2026-06-28 portfolio artifact refresh:

- Regenerated the full four-repo readiness report, remediation queue, advisory
  Markdown queue, and passive AutoPilot pickup artifact after the orchestrator
  L5 and research L4 closeouts.
- Current portfolio level is **Optimized (L4)** with L5 as the next gate.
  Repo levels: `epyc-orchestrator` Autonomous/L5, `epyc-root` Optimized/L4,
  `epyc-inference-research` Optimized/L4, and `epyc-llama` Standardized/L3.
- A follow-up detector refinement recognized llama-native evidence already
  present in the fork: `docs/ops/**` and bench scripts now count for
  experiment surfaces, `flake.nix`/`CMakePresets.json` count for standardized
  dev environment, and sanitizer workflows count as security automation. This
  removed false-positive llama blockers without editing the llama repo.
- The deterministic remediation queue now has `24` open items, down from the
  stale `49`-item 2026-06-21 pickup. The remaining blocking candidates are
  L5 autonomy surfaces for research/root plus the true `epyc-llama` task-index
  gap on the path to L4. The passive pickup remains `mode=advisory_only` and
  `authority_gate=false`.
- Validation: GitNexus impact was LOW for `score_repositories`,
  `build_remediation_queue`, and `build_criteria`; the generic `main` lookup
  was ambiguous but no code edit was made. `repo_readiness_scorer.py`
  regenerated the artifacts without errors, focused tests passed, and generated
  JSON was inspected with `jq` for portfolio level, queue count, and
  non-authority pickup fields.

2026-06-28 research L5 and llama task-index update:

- `epyc-inference-research` commits `8cef3d4`, `817ccdf`, `8ffdc51`, and
  `7c4929c` close the remaining deterministic L5 readiness surfaces with real
  no-inference workflow entrypoints:
  - `.claude/skills/security-review/SKILL.md` and
    `.claude/commands/security-review.md` add an exploit-path-gated,
    research-specific security review surface.
  - `scripts/autopilot/candidate_eval_gate.py` plus `make autopilot-gate`
    chains docs, analysis, security, health, and focused tests as a fail-closed
    candidate gate.
  - `scripts/halo/closed_loop_observation_surface.py` and
    `scripts/halo/convert_tap_to_otel.py` convert benchmark/log/report JSONL
    into deterministic closed-loop observation envelopes.
  - `scripts/session/emergency_cleanup.sh` adds a dry-run-first stale-PID
    cleanup surface, and `scripts/session/health_check.sh` now syntax/smoke
    checks the new L5 surfaces.
- Validation: research `make autopilot-gate` passed end-to-end
  (`docs-check`, `analysis-check`, `security-check`, `health`, and `17`
  focused tests); focused `py_compile`, `ruff`, `pytest`, `bash -n`, and
  `git diff --check` passed on the touched surfaces. A one-repo readiness
  scorer run reports `epyc-inference-research` as **Autonomous (L5)** with
  L1-L5 all `100.0%`.
- `epyc-llama` commits `cc29b7a6a` and `4412872ca` add a docs-only readiness
  index plus detector-visible `handoffs/active/master-handoff-index.md`.
  A one-repo scorer run now reports `epyc-llama` L3 at `100.0%` and
  `L4.prioritized_tasks=true`; remaining llama next-gate blockers are the real
  L4 workflow surfaces (`incremental_validation`, `generated_docs`,
  `health_automation`, `analysis_reports`, `security_audit`, and
  `replay_analysis`).

2026-07-03 artifact refresh:

- Regenerated the four-repo readiness report, remediation queue, advisory
  Markdown queue, and passive AutoPilot pickup artifact after the research L5
  closeout, root candidate-gate closeout, and current repo-state updates.
- Added `scripts/validate/candidate_eval_gate.sh` as the root no-inference
  candidate gate. It bundles root validator syntax checks, agent governance
  validators, CLAUDE.md matrix validation, registry operating-point validation,
  the held-out PII fixture eval, a temp repo-readiness regeneration, and focused
  scorer tests. Wiki/source-manifest drift is intentionally opt-in via
  `--strict-doc-drift` until the wiki refresh lane is clean.
- Refined the root L5 detector so the candidate gate satisfies
  `L5.auto_eval_gates`. A parallel audit rejected crediting passive
  repo-readiness pickup artifacts as `L5.self_optimizing_loop`; the scorer test
  now pins that guardrail, and the passive pickup remains advisory planning
  context only.
- Current portfolio level is now **Autonomous (L5)**: `epyc-root`,
  `epyc-orchestrator`, and `epyc-inference-research` are Autonomous/L5;
  `epyc-llama` is Standardized/L3 with L4 pass rate `33.3%`.
- The deterministic remediation queue is down to `13` open items. The stale
  root `L5.auto_eval_gates` row is gone; remaining rows are the true root
  `L5.self_optimizing_loop` gap plus `epyc-llama` L4/L5 workflow surfaces.
- Attempted to refresh the stale `epyc-llama` GitNexus index before editing
  llama readiness docs; the rebuild repeatedly timed out on large backend
  translation units and then crashed in the Node/NAPI parser. Do not edit the
  llama fork until its GitNexus index is repaired, likely by narrowing
  `.gitnexusignore` for parser-hostile generated/backend files and rebuilding.
- Validation: GitNexus impact was LOW for `build_criteria` and
  `score_repositories`; the generic `main` lookup was ambiguous but max LOW.
  `scripts/validate/candidate_eval_gate.sh` passed, the focused scorer tests
  passed, Ruff passed for the touched scorer/test files, and
  `repo_readiness_scorer.py` regenerated all durable artifacts without errors.

## Notes

- Anti-false-positive discipline (shared across Factory's review/scoring features): a criterion passes only on a concrete, verifiable check — mirrors our eval-tower verifier philosophy.
- Cross-refs: `eval-tower-verification.md` (rubric discipline), `autopilot-continuous-optimization.md` (remediation loop), `claude-md-accounting` skill (governance coverage = a Documentation-pillar input), CLAUDE.md repo-map.

## Progress checklist

- [x] v1 deterministic scorer + tests landed ✅
- [x] remediation queue / advisory MD / passive AutoPilot pickup / candidate-eval-gate / default-off advisory bridge live ✅
- [x] epyc-root, epyc-orchestrator, epyc-inference-research all at Autonomous/L5 ✅
- [ ] Close remaining root L5.self_optimizing_loop gap (13-item queue)
- [ ] Bring epyc-llama Standardized/L3 -> L4 (incremental_validation, generated_docs, health_automation, analysis_reports, security_audit, replay_analysis)
- [ ] Repair stale epyc-llama GitNexus index (narrow .gitnexusignore) before editing llama readiness docs
