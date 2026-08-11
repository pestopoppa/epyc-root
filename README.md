# epyc-root

Cross-repo governance, knowledge base, and coordination for the EPYC local-inference project — a CPU-first production multi-model orchestration system running on a single AMD EPYC 9655 (96C/192T, 1.13 TB DDR5-5600), with an AMD Instinct MI210 as a second serving lane since 2026-07-02.

This umbrella repo holds the project's **knowledge base, research intake, handoff workflow, agent definitions, measurement constitution, and governance tooling**. Application code lives in three sibling repos (orchestrator, research, llama.cpp fork).

---

## 📚 Knowledge Base — Start Here

If you're new to the project, these four indices are the entry points:

| Index | What's there | Size |
|---|---|---|
| **[wiki/INDEX.md](wiki/INDEX.md)** | Compiled wiki articles synthesizing every research thread, organized by topic (speculative decoding, KV cache, routing, autonomous research, …). Each article cites its sources. | 29 articles · 749 sources scanned (2026-07-29 compile) |
| **[handoffs/active/master-handoff-index.md](handoffs/active/master-handoff-index.md)** | Single entry point for active work. Prioritized queue, domain sub-indices (CPU inference, inference acceleration, routing, pipeline integration, research evaluation, hermes-agent, reviewer control plane). | 175 active handoffs |
| **[research/deep-dives/](research/deep-dives/)** | Long-form analyses of individual papers / techniques. Authored when a topic warrants more than an intake entry. | 138 deep-dives |
| **[research/intake_index.yaml](research/intake_index.yaml)** | Triaged list of every paper/repo/technique evaluated against the EPYC constraints. Each entry has a verdict (`adopt` / `worth_investigating` / `not_applicable`) and a credibility score. | 936 intake entries |

**Daily progress logs** live in [`progress/YYYY-MM/`](progress/) (manual session logs + autopilot daily digests).

**Searching the knowledge base**: prefer the `kb-search` skill ([`.claude/skills/kb-search/`](.claude/skills/kb-search/)) over blind grep — a ColBERT-backed semantic index over `wiki/`, `handoffs/`, `research/`, and `progress/` that returns ranked chunks with file path and heading breadcrumb.

---

## Repositories

The codebase is split across three sibling repos; this one is governance-only.

| Repo | Path on this machine | Purpose |
|---|---|---|
| epyc-root (this) | `/mnt/raid0/llm/epyc-root` | Governance, knowledge base, handoffs, agents, hooks |
| [epyc-orchestrator](https://github.com/pestopoppa/epyc-orchestrator) | `/mnt/raid0/llm/epyc-orchestrator` | Production orchestration: multi-model llama-server fleet, AutoPilot, routing, REPL, MemRL |
| [epyc-inference-research](https://github.com/pestopoppa/epyc-inference-research) | `/mnt/raid0/llm/epyc-inference-research` | Benchmarks, 79K-question eval pool across 38 suites, model registry |
| [llama.cpp](https://github.com/pestopoppa/llama.cpp) (fork) | `/mnt/raid0/llm/llama.cpp` | Custom llama.cpp fork — production branch `production-consolidated-v9`, **frozen** at `0db32c06e` |

Production runs **one** kernel. `production-consolidated-v9` is frozen and is never patched in place — new kernel work happens on `llama.cpp-experimental` branches and is promoted as a new version. `scripts/session/verify_llama_cpp.sh` enforces the current production branch, commit, version, and binary digests.

`scripts/clone-repos.sh` sets up `/workspace/repos/<name>` symlinks pointing to the canonical paths above.

---

## Recent Results

The two most recent months. The running record is [`progress/`](progress/); what is currently live is the [master handoff index](handoffs/active/master-handoff-index.md).

| Date | Win | Where to read |
|---|---|---|
| 2026-08-11 | **`production-consolidated-v9` frozen** at `0db32c06e` (version `10125`) after complete v8 comparison, production-named GPU certification, and exact Q8 DSpark cap-0/cap-3 parity. The Qwen3.6-27B Q8 DFlash lane remains disabled: 2.458× speed but 35.954% acceptance, below its 60% lineup floor | [final freeze attestation](artifacts/operator/ratify_v9_final_freeze_20260811.json) |
| 2026-07-26 | **`production-consolidated-v8` frozen** at `67a433bf4` (`llama-server` version `10107`) — a *capability* release (Laguna arch, iqk IQ2/IQ3, DFlash thread-safety), not a performance one. Paired quality gate: worker and architect each ran 200 MMLU-Pro + 195 GPQA on v7 and v8 with zero errors; both exact ties | [progress/2026-07/2026-07-26.md](progress/2026-07/2026-07-26.md) |
| 2026-07-21 | **Eval instrument overhaul** — question pool rebuilt from 53k questions / 21 suites to 79k / 41; B7 scorer ratified; real-confidence gating landed | [handoffs/active/eval-tower-architecture-audit-2026-07-20.md](handoffs/active/eval-tower-architecture-audit-2026-07-20.md) |
| 2026-07-20 | **`production-consolidated-v7` cutover** at `6ad45fa3ff` (version `10098`) — quarter-mode stack live, final live smoke `21/21`, promotion gate `183 passed` | [handoffs/active/v7-promotion.md](handoffs/active/v7-promotion.md) |
| 2026-07-19 | **`P-GPU-1` ratified into MEASUREMENT.md** — GPU throughput claims now require a production-named kernel plus mandatory `rocm-smi` clock/power/temp attestation before and after. Every prior experimental GPU number is observation-grade until re-run | [MEASUREMENT.md](MEASUREMENT.md) |
| 2026-07-02 | **AMD Instinct MI210 brought online** (gfx90a / CDNA2, 64 GB HBM2e). Vulkan proven architecturally impossible on the compute-only MI200 family — ROCm/HIP is the path. First-touch observation: gemma4-31B Q4_K_M `30.01 → 43.25 t/s` with native MTP (1.44×, 59.7% draft acceptance) | [progress/2026-07/2026-07-02-mi210.md](progress/2026-07/2026-07-02-mi210.md) |
| 2026-06-26 | **v6 + iqk single-kernel cutover** — the iqk AVX-512 GEMM ported into our fork; the gemma worker at `42.78 t/s` now *beats* the separate ik_llama.cpp binary (`38.63`, +11%), so ik_llama.cpp was deprecated as a serving path. gemma-4-31B prefill `155.9 → 232.5 t/s` (+49%), output byte-identical | [handoffs/completed/v6-iqk-promotion.md](handoffs/completed/v6-iqk-promotion.md) |
| 2026-06-25 | **Native-MTP max-optimization sweep** across the stack — frontdoor Qwen3.6-35B-A3B Q8 `20.7 → 41.8 t/s` (+103%, 0.82 draft acceptance); architect Qwen3.5-122B-A10B `10.96 → 20.75 t/s` (+89%) | [progress/2026-06/2026-06-25.md](progress/2026-06/2026-06-25.md) |
| 2026-06-12 | **MEASUREMENT.md adopted** as the instrument constitution, out of the Fable 5 architecture review. A claim = `(metric, protocol-id, n/reps, date, host-attestation ref)`; anything else is an observation and may not gate a decision | [MEASUREMENT.md](MEASUREMENT.md) · [fable5-findings-00](handoffs/completed/fable5-findings-00-executive-summary.md) |

---

## Repository Layout

```
epyc-root/
├── README.md                      # this file
├── CLAUDE.md                      # AI assistant guide (governance, repo map, common rules)
├── AGENTS.md                      # cross-agent shared standards
├── MEASUREMENT.md                 # ★ instrument constitution — how numbers become claims
│
├── wiki/                          # ★ Compiled knowledge base
│   ├── INDEX.md                   #   topic-organized article list (start here)
│   ├── SCHEMA.md                  #   taxonomy (categories + aliases)
│   ├── source_manifest.json       #   what was scanned into the last compile
│   ├── speculative-decoding.md    #   one .md per category, citing every source
│   ├── kv-cache.md
│   ├── ... (27 more)
│
├── research/                      # ★ Research intake + deep-dives
│   ├── intake_index.yaml          #   triaged paper/repo list (936 entries)
│   ├── deep-dives/                #   long-form analyses (138 files)
│   ├── taxonomy.yaml              #   research taxonomy
│   ├── recommendations.md       #   standing recommendations
│   └── fixtures/                  #   per-thread experiment data
│
├── handoffs/                      # ★ Cross-repo work tracking
│   ├── active/                    #   in-progress (175 active)
│   │   ├── master-handoff-index.md       # ←── prioritized queue across all domains
│   │   ├── cpu-inference-optimization-index.md
│   │   ├── inference-acceleration-index.md
│   │   ├── routing-and-optimization-index.md
│   │   ├── pipeline-integration-index.md
│   │   ├── research-evaluation-index.md
│   │   ├── reviewer-control-plane-index.md
│   │   └── user-facing-harness-index.md
│   ├── completed/                 #   finished (154 entries)
│   └── blocked/                   #   waiting on dependencies
│
├── progress/                      # ★ Daily session logs + autopilot digests
│   └── YYYY-MM/YYYY-MM-DD.md
│
├── coordination/                  # Multi-session coordination
│   └── session-bus/               #   file bus: BUS_PROTOCOL.md, inbox/outbox, heartbeats
│
├── artifacts/                     # Operator ratification receipts + campaign artifacts
│
├── agents/                        # Per-role agent file overlays
│   └── shared/                    #   common standards (engineering, ops, measurement policy)
│
├── scripts/
│   ├── hooks/                     # Pre/post tool-use hooks for Claude Code sessions
│   ├── validate/                  # Governance validators
│   ├── session/                   # session_init, health_check, verify_llama_cpp
│   ├── coordination/              # session_bus.py + coordinator daemon
│   ├── dashboard/                 # handoff dashboard hub
│   ├── nightshift/                # autonomous overnight runs
│   ├── operator/                  # operator-facing ratification tooling
│   ├── utils/                     # agent_log.sh, log analyzers
│   └── search/                    # SearXNG bash bridge (`searx.sh`)
│
├── docs/                          # Operational docs (infrastructure, runbooks, recovery, reference)
│
└── .claude/
    ├── skills/                    # Reusable Claude Code skills (kb-search, research-intake, ...)
    ├── commands/                  # Slash commands (/wrap-up, /research-intake, ...)
    └── dependency-map.json        # Formal cross-repo coupling edges
```

---

## Governance Workflows

### Research intake

Every paper / repo / technique evaluated for the EPYC stack goes through `/research-intake`, a **four-stage** pipeline ([skill](.claude/skills/research-intake/SKILL.md)):

1. **Stage 1** — sweep, dedup, expand literature; every entry persisted as `stage1-unverified` in `research/intake_index.yaml`, with ranked deep-dive recommendations.
2. **Stage 2** — deep-dive the operator-selected entries, verifying each claim against primary source. Each dive emits a derived-actionables ledger *and* a dive-surfaced sources list.
3. **Stage 2b** (the *dive-surfaced source gate*) — sources discovered **during** a dive are presented to the operator and the selected ones ingested-and-dived in a combined pass, **before** planning. Stage 3 may not begin until every dive-surfaced source is ingested or explicitly declined.
4. **Stage 3** (plan mode) — audited action plan naming every handoff to amend/create, index row, and explicit decline; iterated until the operator approves. **Stage 4** implements exactly that plan.

Operator comments during stages 1–3 are *context, not authorization*, and are logged verbatim to a steering ledger. Promising entries get a `research/deep-dives/<topic>.md` long-form analysis; compiled knowledge lands in `wiki/<category>.md` via the [`project-wiki` skill](.claude/skills/project-wiki/SKILL.md).

### Measurement discipline

[`MEASUREMENT.md`](MEASUREMENT.md) is the instrument constitution. A decision-gating number is `(metric, protocol-id, n/reps, date, host-attestation ref)`; a number without a protocol citation is an **observation** — fine for hypotheses, never for gating keep/revert/deploy/promote decisions. Benchmarks run only via the codified recipes (`bench_canonical.sh` / `canonical_recipe.py`). Historical numbers are era-labelled via `instrument_eras.yaml` rather than edited. The agent-facing digest is [`agents/shared/MEASUREMENT_POLICY.md`](agents/shared/MEASUREMENT_POLICY.md).

### Handoff workflow

Work items flow `active/` → `completed/`. The `master-handoff-index.md` is the prioritized queue. Each handoff is **actionable**: it lists the change, the gate criteria, the rollback plan, and the success metric. Progress is tracked by checkbox state, not prose — a completed task flips `- [ ]` → `- [x]`. Completed handoffs are extracted into wiki articles before archival.

### Session coordination

Multiple agent sessions run concurrently against the same trees. They coordinate through a file-based **session bus** — inbox/outbox/heartbeat JSONL under [`coordination/session-bus/`](coordination/session-bus/), driven by `scripts/coordination/session_bus.py`. Contract: [`coordination/session-bus/BUS_PROTOCOL.md`](coordination/session-bus/BUS_PROTOCOL.md).

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

Single AMD EPYC 9655 "Turin", 96 cores / 192 threads (Zen 5), 12-channel DDR5-5600 ECC (1.13 TB, ~460 GB/s aggregate bandwidth), 4 NUMA nodes (NPS4), 2× 2 TB NVMe in RAID0.

Since **2026-07-02** the box also carries one **AMD Instinct MI210** (gfx90a / CDNA2, 64 GB HBM2e) on ROCm 6.2, used via HIP — no Vulkan ICD supports the compute-only MI200 family. Inference remains CPU-first; the MI210 is a second serving lane and the GPU-kernel research substrate. (The DGX Spark once floated as the GPU complement was never acquired.)

Details: [`docs/infrastructure/01-hardware-system.md`](docs/infrastructure/01-hardware-system.md) · [`wiki/hardware-optimization.md`](wiki/hardware-optimization.md).

---

## License

MIT. Models are under their own licenses (see `research/intake_index.yaml` entries for per-model license notes).
