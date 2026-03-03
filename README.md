# epyc-root

Cross-repo coordination, governance, and tooling for the EPYC inference project.

This is the umbrella repository that ties together three child repositories:

| Repository | Purpose |
|------------|---------|
| [epyc-orchestrator](https://github.com/pestopoppa/epyc-orchestrator) | Production multi-model orchestration system |
| [epyc-inference-research](https://github.com/pestopoppa/epyc-inference-research) | Benchmarks, experiments, model evaluation |
| [epyc-llama](https://github.com/pestopoppa/llama.cpp) | Custom llama.cpp fork with AMD EPYC patches |

## Quick start

```bash
git clone https://github.com/pestopoppa/epyc-root.git
cd epyc-root
./scripts/setup.sh
```

This clones all child repos into `repos/`, installs the orchestrator, and checks for llama.cpp builds.

## What's here

This repo contains **governance and coordination infrastructure** — not application code.

```
.claude/
  settings.json       Hooks configuration
  skills/             Claude Code skill definitions
  commands/           Claude Code slash commands
  dependency-map.json Cross-repo dependency edges
agents/               Agent file definitions (shared + role overlays)
scripts/
  setup.sh            Full setup: clone, install, verify
  clone-repos.sh      Just clone the child repos
  hooks/              Pre/post tool-use hooks for Claude Code
  validate/           Governance validation scripts
  session/            Session management, health checks
  nightshift/         Autonomous overnight run infrastructure
  system/             System audit scripts
  utils/              Agent logging functions
docs/
  infrastructure/          Hardware and storage documentation (2 chapters)
  guides/agent-workflows/  Agent persona documentation
  recovery/                Recovery and triage procedures
  reference/agent-config/  Agent file logic, CLAUDE.md matrix
handoffs/             Cross-repo task handoffs (active, blocked, archived)
progress/             Daily progress reports
logs/                 Agent audit trail
```

## Dependency graph

```
              epyc-root (this repo)
               /         |         \
              /           |          \
    epyc-orchestrator     |      epyc-llama
              \           |          /
               \          |         /
            epyc-inference-research
```

See `.claude/dependency-map.json` for detailed coupling edges.

## License

MIT
