# EPYC Root — AI Assistant Guide

## Purpose

Umbrella repository for cross-repo coordination and governance. No application code lives here — orchestrator code is in `epyc-orchestrator`, research in `epyc-inference-research`, llama.cpp patches in `epyc-llama`.

## Act, Don't Defer — read this before deciding to stop

**The default is ACT.** Escalation is the exception and must earn itself. Before deferring, escalating, or
writing anything into a "Deferred / Open / Awaiting operator" list:

> **Name the specific decision only the operator can make, or the external event you are waiting on.**
> If you cannot name one in a single sentence, you are not blocked — **finish the work.**

- **Find a bug → fix it.** **Find a gap → close it.** Neither is an "open item".
- **Work the operator already approved is not re-openable** by restating it as a question.
- A genuine choice → decision package (options + tradeoffs + recommendation) — and **keep going on
  everything that does not depend on the answer.** A pending decision blocks its own item, never the rest.
- **Recurrence check:** an item appearing in two consecutive wrap-ups or status reports with an unchanged
  blocker is proof it was never blocked. Do it *before* writing anything else.
- Mentioning something in passing is fine. Mentioning it **instead of doing it** is the failure.

The operator should not have to hand-hold a workflow to a clean conclusion. Full rule, with the admission
test and its origin: [`agents/shared/OPERATING_CONSTRAINTS.md` → *Act, Don't
Defer*](agents/shared/OPERATING_CONSTRAINTS.md#act-dont-defer--the-admission-test-for-escalating-at-all).

## Repository Map

| Repo | Working path | Contents |
|---|---|---|
| epyc-root (this) | `/workspace` | Governance, handoffs, measurement constitution, agent files |
| epyc-orchestrator | `/workspace/repos/epyc-orchestrator` | Orchestrator, API, autopilot, registries |
| epyc-inference-research | `/workspace/repos/epyc-inference-research` | Benchmarks, canonical recipes, research |
| epyc-llama | `/workspace/repos/epyc-llama` → `/mnt/raid0/llm/llama.cpp` | Production llama.cpp kernel tree (FROZEN) |
| epyc-whisper | `/mnt/raid0/llm/whisper.cpp` | Production STT kernel (FROZEN, `production-speech-v1`) |
| epyc-qwentts | `/mnt/raid0/llm/qwentts.cpp` | Production TTS kernel (FROZEN, `production-speech-v1`) |

Coupling edges: `.claude/dependency-map.json`.

**2026-07-25 v8 final freeze**: production runs ONE kernel, **production-consolidated-v8** (canonical tree `/mnt/raid0/llm/llama.cpp`, frozen at `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server --version` reports `10107`). Ratification: [`artifacts/operator/ratify_v8_final_freeze_20260725.json`](artifacts/operator/ratify_v8_final_freeze_20260725.json), SHA-256 `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`. v7 (`6ad45fa3ff6718c07c000061dbc6e29c1771f6e3`, binary `10098`) is the rollback anchor. `scripts/session/verify_llama_cpp.sh` enforces the production branch. **ik_llama.cpp is fully deprecated as a serving path** (tree on disk = reference/measurement instrument only).

**iqk coverage (v8)**: `GGML_IQK=1` accelerates supported K/legacy quants plus IQ2/IQ3 and IQ4_XS; **IQ1 remains stubbed**. See [`handoffs/active/tq3-quantization-evaluation.md`](handoffs/active/tq3-quantization-evaluation.md).

### Experimental Kernel Workflow & Production-Kernel Immutability

**2026-07-31 speech-kernel freeze**: the freeze covers a production **KERNEL SET**, not one kernel — `llama.cpp` @ `production-consolidated-v8`, `whisper.cpp` @ `production-speech-v1` (`b30737922`, ggml 0.18.0, STT), `qwentts.cpp` @ `production-speech-v1` (`2c1b5182e`, ggml 0.17.0, TTS). Ratification: [`artifacts/operator/ratify_speech_kernel_freeze_20260731.json`](artifacts/operator/ratify_speech_kernel_freeze_20260731.json). Both speech kernels carry load-bearing gfx90a/ROCm-6.2 patches that were UNCOMMITTED until this ratification. The three trees run three different ggml generations, so **every launcher must set its own `LD_LIBRARY_PATH`** and prove it with `epyc-inference-research/scripts/utils/verify_ggml_linkage.sh` (it lives in the research repo, not root) — a binary that inherits another tree's ggml runs silently wrong. `scripts/session/verify_speech_kernels.sh` enforces the speech branches.

**Production kernels are FROZEN.** `production-consolidated-v8` (and future `-v9`, …) must NEVER be modified, rebased, built, or committed to unless the operator EXPLICITLY authorizes it. We *version past* production — never patch it in place. ALL kernel/benchmarking work happens on `llama.cpp-experimental` branches. Every new kernel feature follows four steps, in order:

1. **Pull fresh production → `llama.cpp-experimental`** — start from the *current* production tip so all its optimizations are present; never accumulate on a long-lived branch forked from an old tip (origin: INC-20260706-iqk-missing-subsystem, `docs/reference/agent-config/INCIDENT_LOG.md`).
2. **Build** in `llama.cpp-experimental`.
3. **Validate no regressions** vs production (GPU + CPU).
4. **Deploy** as a NEW production version. The candidate must be the FULL build (fresh production + all new features) validated as a whole — never reconciled via cherry-picks at promotion time; bench numbers come from the full candidate binary. Promotion checklist includes baking the project agent-file overlay (`docs/reference/agent-config/llama-tree-overlay/`) into the candidate so the new production tree ships freeze-aware agent files.

## Working-tree identity

**Single source of truth**: `/workspace/repos/<name>` is a symlink to `/mnt/raid0/llm/<name>` (`/mnt/raid0/llm/llama.cpp` for `epyc-llama`) — parallel sessions on either path share one clone, branch, and staging area. Identity check: `stat -c %i /workspace/repos/<name>/.git` equals the target's. `scripts/clone-repos.sh` (idempotent, `DRY_RUN=1` to preview) creates/repairs the symlinks and backs up divergent clones — if the two paths ever show divergent commits, push unique commits from both sides first, then re-run it.

## Handoff Workflow

- `handoffs/active/` — In-progress · `handoffs/blocked/` — Waiting · `handoffs/completed/` — Done · `handoffs/archived/` — Historical
- **Start here**: [`handoffs/active/master-handoff-index.md`](handoffs/active/master-handoff-index.md) — single entry point; dispatches to 6 domain sub-indices plus standalone strategy indices.
- Standing strategic assessment (2026-06-12): `handoffs/completed/fable5-findings-*`, start at the executive summary.
- **Checkbox discipline**: the dashboard counts checkbox state ONLY — any edit recording completed work flips `- [ ]` → `- [x]` (append `✅ YYYY-MM-DD`); mid-flight discoveries get their own task line. Full axioms: `agents/shared/SESSION_LIFECYCLE.md`.
- Authoring a coordination index: `docs/guides/agent-workflows/handoff-index-authoring.md`. On completion, extract findings to docs, move to `completed/`.

## Progress Tracking

Daily progress in `progress/YYYY-MM/YYYY-MM-DD.md`. Always update after significant work.

## Agent Logging

```bash
source scripts/utils/agent_log.sh
agent_session_start "Session purpose"
agent_task_start "Description" "Reasoning"
agent_task_end "Description" "success|failure"
```

Audit trail in `logs/agent_audit.log`; analysis via `scripts/utils/agent_log_analyze.sh --summary`.

## Measurement & Claims

The [measurement constitution](MEASUREMENT.md) is authoritative (protocol annexes in `measurement/protocols/`); use its agent digest, [MEASUREMENT_POLICY.md](agents/shared/MEASUREMENT_POLICY.md), for claim grammar, era handling, codified recipes, deterministic replay, and consolidated ratification. The measurement trust boundary is human-amendment-only.

## Session Management

- `scripts/session/session_init.sh` — discover models, verify llama.cpp
- `scripts/session/health_check.sh` — system health
- `scripts/session/verify_llama_cpp.sh` — branch safety
- `scripts/nightshift/` — autonomous overnight runs

## Historical Documentation Warning

`handoffs/archived|completed/`, `progress/`, and `CHANGELOG.md` describe historical state (possibly the pre-2026-02-25 monorepo at `/mnt/raid0/llm/claude`). **Verify against actual code before trusting archived descriptions.**

## Code Style

- Shell: `#!/bin/bash` with `set -euo pipefail`
- Run validation after producing artifacts

## Process Management

- **Kill only PIDs you captured yourself. NEVER `pkill`/`pgrep` on a name pattern on this host** — it is a shared box, so any name pattern is a wildcard over other sessions' processes, and a guard process's argv necessarily contains the names it guards (origin: INC-20260731-broad-process-pattern-kills — `llama-server -m` killed another agent's server twice, and `earlyoom` died because its command line contains `--ignore ^(llama-server|sd-server)$`).
- After killing a process, **verify it is dead** (`ps -p <pid>`); escalate SIGTERM → SIGKILL; never report success until confirmed.
- Before declaring a fix deployed to a long-lived process, check the running process isn't stale (`ps -o lstart -p <pid>` vs file mtimes); restart if needed.
- **API reload vs full stack**: orchestrator API (uvicorn :8000) restarts via `orchestrator_stack.py reload orchestrator` — do NOT reload the whole stack. API-only: do NOT stop autopilot (it reconnects). Full stack: stop autopilot first.
- **Reload ownership**: HOW above ≠ WHO/WHEN — if a session owns the inference, all reloads are executed by that session at its own boundary. Full rule: `agents/shared/OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*.

## Research Intake

- **Never dismiss a research source, model, or technique as "not applicable" without asking the user first** — existing infrastructure often makes things feasible. When in doubt, flag for review.

## Debugging

- **Always confirm metric direction** (higher/lower=better) and correct baselines before proposing fixes; identify root cause, don't patch symptoms.
- If unsure about objective or metric semantics, ask before proceeding.

## Agents & Automation

- **No intake entries, handoff stubs, or index modifications via sub-agents without explicit user approval.**
- **Codex delegation & long-horizon throughput contract**: `agents/shared/OPERATING_CONSTRAINTS.md` → *Codex Delegation & Long-Horizon Throughput*.
- **Bus drain (M1)**: at every task boundary run `scripts/coordination/session_bus.py drain --agent <your-roster-id> --triage`; act on assignments/nudges; write acks to **your own** outbox with `corr_id` for routed items; never write another agent's file. Contract: [`coordination/session-bus/BUS_PROTOCOL.md`](coordination/session-bus/BUS_PROTOCOL.md).
- **Coordinating other sessions?** Role file: [`agents/coordinator-agent.md`](agents/coordinator-agent.md). Session lifecycle (wrap-up, `/clear`, close, idle-main axiom): `agents/shared/SESSION_LIFECYCLE.md`.
- **Refresh your heartbeat at the same boundary**: `session_bus.py append --agent <id> --target heartbeat --json '{"state":"working","task_id":"<id>"}'` (`idle`|`working`|`draining`). A heartbeat written once is a birth certificate, not a liveness signal (origin: INC-20260727-stale-heartbeat).

## Operator Decision Requests

See **Act, Don't Defer** at the top of this file before escalating anything. When a choice genuinely is
the operator's, use the canonical [operator decision-package contract](agents/shared/OPERATING_CONSTRAINTS.md#operator-decision-requests).
