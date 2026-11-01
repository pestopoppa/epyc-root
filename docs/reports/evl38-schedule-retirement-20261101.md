# EVL38 scheduled gate retirement — 2026-11-01

The EVL38 scheduled candidate-gate workflow is retired. Its workflow file was removed by the task-workflow prune commit [`e897669a6a621332be3189e33f0e445f75001135`](https://github.com/pestopoppa/epyc-root/commit/e897669a6a621332be3189e33f0e445f75001135). GitHub Actions API workflow 376989682 (`.github/workflows/evl38-periodic-candidate-gate.yml`) reports state `deleted`, updated 2026-11-01 11:46:35 UTC. The EVL38 workflow is absent from the current ROOT source and is not an active schedule; this change does not restore it or weaken shared CI.

The latest scheduled execution, run 41223677301, captured its native receipt successfully (`capture_exit_code=0`) but the full candidate gate failed (`gate_exit_code=1`). The failure was reference validation on nine `/mnt/raid0/llm/tmp/...` scratch-file references unavailable in the hosted runner. The historical capture does not establish current readiness or a passing gate.

The shared `.github/workflows/tests.yml` gains only a generic `workflow_dispatch` event so the existing hermetic ROOT CI can be run on demand after source changes. Its jobs, permissions, selected test commands and push/pull-request triggers remain unchanged. No EVL-specific workflow or scheduled job is added.

Failed reference-validator rows from run 41223677301:

- `docs/guides/agent-workflows/INDEX.md -> /mnt/raid0/llm/tmp/compute-flags/FILLERS.md`
- `agents/coordinator-agent.md -> /mnt/raid0/llm/tmp/compute-flags/FILLERS.md`
- `docs/guides/agent-workflows/agent-loop-design.md -> /mnt/raid0/llm/tmp/ws58-canary-20261025/CANARY.md`
- `docs/guides/agent-workflows/codex3-lane-checkouts.md -> /mnt/raid0/llm/tmp/codex3-lane-git/README.md`
- `docs/guides/agent-workflows/compute-fillers.md -> /mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/IPC-CONTRACT.md`
- `docs/guides/agent-workflows/compute-fillers.md -> /mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/RULES-FROM-WS58.md`
- `docs/guides/agent-workflows/compute-fillers.md -> /mnt/raid0/llm/tmp/compute-flags/FILLERS.md`
- `docs/guides/agent-workflows/compute-fillers.md -> /mnt/raid0/llm/tmp/d4-why-20261022/REPORT.md`
- `docs/guides/agent-workflows/compute-fillers.md -> /mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md`
