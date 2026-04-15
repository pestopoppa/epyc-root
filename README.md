# epyc-root

Cross-repo coordination, governance, and tooling for the EPYC local inference project.

Umbrella repository for a production multi-model orchestration system running on AMD EPYC 9655 (96C/192T, 1.13TB DDR5). No application code lives here — this repo manages handoffs, agent definitions, governance hooks, and progress tracking across 4 child repositories.

## Repositories

| Repository | Purpose | Key Metrics |
|------------|---------|-------------|
| [epyc-orchestrator](https://github.com/pestopoppa/epyc-orchestrator) | Production orchestration — 30 model servers, AutoPilot, routing | 192 trials, 64 t/s, 30+ eval suites |
| [epyc-inference-research](https://github.com/pestopoppa/epyc-inference-research) | Benchmarks, model evaluation, 57K question pool | 30+ suites, code execution, LLM-judge scoring |
| [epyc-llama](https://github.com/pestopoppa/llama.cpp) | Custom llama.cpp fork — paged attention, SWA, AM KV compaction | production-consolidated-v3, 538 upstream commits |

## Current State (April 2026)

- **AutoPilot AR-3** running autonomously (192+ trials, continuous optimization)
- **llama.cpp v3** in production — coder +101% t/s, REAP +50% from upstream spec decode gains
- **AM KV compaction** — native `POST /slots/{id}?action=compact` endpoint, 5x compression at zero quality cost
- **Bulk Inference Campaign** — 5/6 packages complete (A+B+C+E+F done, D running)
- **39-question sentinel pool** — GPQA, olympiad math, multi-hop, tool-use, structured extraction

## What's Here

```
handoffs/
  active/              In-progress cross-repo work items (~25 active)
  completed/           Historical reference
  master-handoff-index.md  → Start here to discover all work
agents/
  shared/              Engineering standards, operating constraints
  (role overlays)      Per-agent specialization
scripts/
  hooks/               Pre/post tool-use hooks for Claude Code
  validate/            Governance validators (agent schema, CLAUDE.md matrix)
  session/             Health checks, smoke tests, stack verification
progress/              Daily progress reports (YYYY-MM/YYYY-MM-DD.md)
docs/                  Infrastructure docs, recovery procedures, agent guides
.claude/
  skills/              Reusable Claude Code skills (research-intake, benchmark, etc.)
  commands/            Slash commands (/wrap-up, /commit, etc.)
```

## Handoff Workflow

Start at [`handoffs/active/master-handoff-index.md`](handoffs/active/master-handoff-index.md) — dispatches to 5 domain indices covering routing, inference acceleration, research, pipeline integration, and agent architecture.

## Dependency Graph

```
              epyc-root (governance)
               /         |         \
              /           |          \
    epyc-orchestrator     |      epyc-llama
     (production)         |      (llama.cpp)
              \           |          /
               \          |         /
            epyc-inference-research
               (benchmarks)
```

## License

MIT
