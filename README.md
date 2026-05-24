# epyc-root

Cross-repo governance, knowledge base, and coordination for the EPYC local-inference project — a CPU-only production multi-model orchestration system running on a single AMD EPYC 9655 (96C/192T, 1.13 TB DDR5-5600).

This umbrella repo holds the project's **knowledge base, research intake, handoff workflow, agent definitions, and governance tooling**. Application code lives in three sibling repos (orchestrator, research, llama.cpp fork).

---

## 📚 Knowledge Base — Start Here

If you're new to the project, these four indices are the entry points:

| Index | What's there | Size |
|---|---|---|
| **[wiki/INDEX.md](wiki/INDEX.md)** | 30 compiled wiki articles synthesizing every research thread, organized by topic (speculative decoding, KV cache, routing, autonomous research, …). Each article cites its sources. | 30 articles · 292 sources |
| **[handoffs/active/master-handoff-index.md](handoffs/active/master-handoff-index.md)** | Single entry point for active work. Prioritized queue, domain sub-indices (CPU inference, inference acceleration, routing, pipeline integration, research evaluation, hermes-agent). | 95 active handoffs |
| **[research/deep-dives/](research/deep-dives/)** | Long-form analyses of individual papers / techniques. Authored when a topic warrants more than an intake entry. | 105 deep-dives |
| **[research/intake_index.yaml](research/intake_index.yaml)** | Triaged list of every paper/repo/technique evaluated against the EPYC constraints. Each entry has a verdict (`adopt` / `worth_investigating` / `not_applicable`) and a credibility score. | 595 intake entries |

**Daily progress logs** live in [`progress/YYYY-MM/`](progress/) (manual session logs + autopilot daily digests, ~13 entries per month).

---

## Repositories

The codebase is split across three sibling repos; this one is governance-only.

| Repo | Path on this machine | Purpose |
|---|---|---|
| epyc-root (this) | `/mnt/raid0/llm/epyc-root` | Governance, knowledge base, handoffs, agents, hooks |
| [epyc-orchestrator](https://github.com/pestopoppa/epyc-orchestrator) | `/mnt/raid0/llm/epyc-orchestrator` | Production orchestration: 20 llama-server ports, AutoPilot, routing, REPL, MemRL |
| [epyc-inference-research](https://github.com/pestopoppa/epyc-inference-research) | `/mnt/raid0/llm/epyc-inference-research` | Benchmarks, 57K question pool, 30+ eval suites, model registry |
| [llama.cpp](https://github.com/pestopoppa/llama.cpp) (fork) | `/mnt/raid0/llm/llama.cpp` | Custom llama.cpp fork — current branch `production-consolidated-v5` |

`scripts/clone-repos.sh` sets up `/workspace/repos/<name>` symlinks pointing to the canonical paths above.

---

## Recent Results (last 60 days)

| Date | Win | Where to read |
|---|---|---|
| 2026-05-24 | **Autopilot exogenous-restart resilience** — operator-initiated orchestrator/llama reloads no longer pollute the experiment journal. Fleet markers + watcher + WAL-style crash recovery; 60/60 tests | [completed handoff](handoffs/completed/autopilot-exogenous-restart-resilience.md) |
| 2026-05-23 | **Constrained-creativity planner upgrade** — stagnation-gated rich prompt + 3-axis rubric + persisted falsifier sidecar | [research/deep-dives/2026-05-23-creativity-constrained-tail-search.md](research/deep-dives/2026-05-23-creativity-constrained-tail-search.md) |
| 2026-05-21 | **Learned routing controller wired end-to-end** — 92% → 98.7% classifier accuracy on fresh data; production wiring gap discovered + fixed | [handoffs/active/learned-routing-controller.md](handoffs/active/learned-routing-controller.md) |
| 2026-05-09 | **OMP idle-spin fix** — gemma4 MTP cores 95% → 0% via `KMP_BLOCKTIME=10`; frontdoor decode +78% | [wiki/inference-serving.md](wiki/inference-serving.md) |
| 2026-05-08 | **worker_general → gemma4-26B-A4B MTP** — +18pp tool_compliance, +36% throughput, 76.5 t/s solo via ik_llama.cpp PR #1744 | [wiki/moe-optimization.md](wiki/moe-optimization.md) |
| 2026-05-06 | **Qwen3.6 production upgrade complete** — frontdoor + coder_escalation + worker_summarize all share Qwen3.6-35B-A3B Q8 GGUF; 157 GB warm-tier reclaimed | [handoffs/active/qwen36-production-upgrade.md](handoffs/active/qwen36-production-upgrade.md) |
| 2026-04-24 | **NPS4 + CCD + Q8 8×8 AVX-512BW kernel** — single-instance 48-thread best at 46.6 t/s for 30B-A3B Q4_K_M; +31.8% at single-thread | [wiki/hardware-optimization.md](wiki/hardware-optimization.md) |

The full 2026-04+ run sits in [`progress/2026-04/`](progress/2026-04/) and [`progress/2026-05/`](progress/2026-05/).

---

## Repository Layout

```
epyc-root/
├── README.md                      # this file
├── CLAUDE.md                      # AI assistant guide (governance, repo map, common rules)
├── AGENTS.md                      # cross-agent shared standards
│
├── wiki/                          # ★ Compiled knowledge base
│   ├── INDEX.md                   #   topic-organized article list (start here)
│   ├── SCHEMA.md                  #   taxonomy (30 categories, 34 aliases)
│   ├── speculative-decoding.md    #   one .md per category, citing every source
│   ├── kv-cache.md
│   ├── ... (28 more)
│
├── research/                      # ★ Research intake + deep-dives
│   ├── intake_index.yaml          #   triaged paper/repo list (595 entries)
│   ├── deep-dives/                #   long-form analyses (105 files)
│   ├── taxonomy.yaml              #   research taxonomy
│   └── multilingual_ingest_test/  #   per-thread experiment data
│
├── handoffs/                      # ★ Cross-repo work tracking
│   ├── active/                    #   in-progress (95 active)
│   │   ├── master-handoff-index.md       # ←── prioritized queue across all domains
│   │   ├── cpu-inference-optimization-index.md
│   │   ├── inference-acceleration-index.md
│   │   ├── routing-and-optimization-index.md
│   │   ├── pipeline-integration-index.md
│   │   ├── research-evaluation-index.md
│   │   └── hermes-agent-index.md
│   ├── completed/                 #   finished (62 entries)
│   └── blocked/                   #   waiting on dependencies
│
├── progress/                      # ★ Daily session logs + autopilot digests
│   └── YYYY-MM/YYYY-MM-DD.md
│
├── agents/                        # Per-role agent file overlays
│   └── shared/                    #   common standards (engineering, ops, workflows)
│
├── scripts/
│   ├── hooks/                     # Pre/post tool-use hooks for Claude Code sessions
│   ├── validate/                  # Governance validators
│   ├── session/                   # session_init, health_check, verify_llama_cpp
│   ├── nightshift/                # autonomous overnight runs
│   ├── utils/                     # agent_log.sh, log analyzers
│   └── search/                    # SearXNG bash bridge (`searx.sh`)
│
├── docs/                          # Operational docs (recovery, hardware, agents)
│
└── .claude/
    ├── skills/                    # Reusable Claude Code skills
    ├── commands/                  # Slash commands (/wrap-up, /research-intake, ...)
    └── dependency-map.json        # Formal cross-repo coupling edges
```

---

## Governance Workflows

### Research intake

Every paper / repo / technique evaluated for the EPYC stack goes through `/research-intake` → entry in `research/intake_index.yaml` with verdict + credibility score. Promising ones get a `research/deep-dives/<topic>.md` long-form analysis. Compiled knowledge lands in `wiki/<category>.md` via the [`project-wiki` skill](.claude/skills/project-wiki/SKILL.md).

### Handoff workflow

Work items flow `active/` → `completed/`. The `master-handoff-index.md` is the prioritized queue. Each handoff is **actionable**: it lists the change, the gate criteria, the rollback plan, and the success metric. Completed handoffs are extracted into wiki articles before archival.

### Session lifecycle

```bash
scripts/session/session_init.sh    # discover models, verify llama.cpp branch
scripts/session/health_check.sh    # system health
# ... work happens ...
# end of session: /wrap-up skill compiles progress, updates indices, commits
```

### Agent logging

```bash
source scripts/utils/agent_log.sh
agent_session_start "Session purpose"
agent_task_start "Description" "Reasoning"
# ... work ...
agent_task_end "Description" "success|failure"
```

Audit trail in `logs/agent_audit.log`; query via `scripts/utils/agent_log_analyze.sh --summary`.

---

## Hardware

Single AMD EPYC 9655 "Turin", 96 cores / 192 threads (Zen 5), 12-channel DDR5-5600 ECC (1.13 TB, ~460 GB/s aggregate bandwidth), NPS4 NUMA. CPU-only inference — no GPU. DGX Spark (GB10) is the planned GPU complement; not yet acquired.

---

## License

MIT. Models are under their own licenses (see `research/intake_index.yaml` entries for per-model license notes).
