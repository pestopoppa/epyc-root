# About

## Hardware

Single **AMD EPYC 9655 "Turin"** — 96 cores / 192 threads (Zen 5), 1.13 TB DDR5-5600 ECC across 12 channels (~460 GB/s aggregate bandwidth), NPS4 NUMA topology. 3.7 TB RAID-0 NVMe storage, 120 GB root SSD. **CPU-only inference** — no GPU. A DGX Spark (GB10) is the planned GPU complement; not yet acquired.

## Design philosophy

- **Open-source only.** Every model and tool ships under a self-hostable license. No SaaS dependencies.
- **CPU as a first-class inference target.** The default assumption that real LLM inference needs GPUs is wrong for a non-trivial portion of production workloads. This project is the proof.
- **Build, measure, falsify.** Every speedup claim is benchmarked under a canonical baseline protocol. Every "this should work" hypothesis is empirically validated or marked closed-negative. The wiki documents both.
- **Multi-model orchestration over single-model scaling.** Routing the right task to the right model wins more wall-clock than throwing more parameters at every problem.
- **Knowledge accumulates.** Research intake, deep-dives, handoffs, and progress logs are all preserved — the site you're reading is the curated synthesis layer over that history.

## Source repositories

| Repo | Role |
|---|---|
| [pestopoppa/epyc-root](https://github.com/pestopoppa/epyc-root) | Knowledge base, handoffs, agent definitions, governance tooling — and the source of this site |
| [pestopoppa/epyc-orchestrator](https://github.com/pestopoppa/epyc-orchestrator) | Production orchestration: routing, REPL, MemRL, autopilot, calibration |
| [pestopoppa/epyc-inference-research](https://github.com/pestopoppa/epyc-inference-research) | Benchmarks, eval suites, model registry, research deep-dives |
| [pestopoppa/llama.cpp](https://github.com/pestopoppa/llama.cpp) | Custom llama.cpp fork |

## License

Project: MIT. Models are under their own licenses (see individual research intake entries).

## Site

Built with [MkDocs](https://www.mkdocs.org/) + [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/). Sources are markdown files in the three repos above; the GitHub Actions workflow clones each repo at build time and assembles the unified site. Search is client-side and built into the theme.
