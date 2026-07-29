# EPYC Root — AI Assistant Guide

## Purpose

Umbrella repository for cross-repo coordination and governance. No application code lives here — orchestrator code is in `epyc-orchestrator`, research in `epyc-inference-research`, llama.cpp patches in `epyc-llama`.

## Repository Map

All repos are already cloned on this machine. Use the absolute paths below.

| Repo | Absolute Path | Purpose |
|------|---------------|---------|
| epyc-root (this) | `/mnt/raid0/llm/epyc-root` | Governance, agents, hooks, handoffs, progress |
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator` | Production orchestration (`src/`, `tests/`) |
| epyc-inference-research | `/mnt/raid0/llm/epyc-inference-research` | Benchmarks, seeding, model registry, research |
| epyc-llama | `/mnt/raid0/llm/llama.cpp` | Custom llama.cpp fork (production-consolidated-v8 — single kernel) |
| hermes-agent (upstream) | `/mnt/raid0/llm/hermes-agent` | Agent frontend (Nous Research, not a child repo) |

**2026-07-25 v8 final freeze**: production now runs on ONE kernel, **production-consolidated-v8** (canonical tree `/mnt/raid0/llm/llama.cpp`, frozen at `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server --version` reports `10107`). Final ratification is [`artifacts/operator/ratify_v8_final_freeze_20260725.json`](artifacts/operator/ratify_v8_final_freeze_20260725.json), SHA-256 `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`. v7 (`6ad45fa3ff6718c07c000061dbc6e29c1771f6e3`, binary `10098`) is the rollback/history anchor. `scripts/session/verify_llama_cpp.sh` enforces the current production branch. The earlier 2026-06-26 v6 cutover consolidated the gemma worker off the separate `ik_llama.cpp` binary — **ik_llama.cpp is fully deprecated as a serving path; there is no second binary** (the tree remains on disk as a reference/measurement instrument only).

**iqk coverage (v8)**: `GGML_IQK=1` accelerates the supported K/legacy quant types plus IQ2/IQ3 and IQ4_XS. **IQ1 remains stubbed and non-accelerated**. See [`handoffs/active/tq3-quantization-evaluation.md`](handoffs/active/tq3-quantization-evaluation.md).

### Experimental Kernel Workflow & Production-Kernel Immutability

**Production kernels are FROZEN.** `production-consolidated-v8` (and any future `-v9`, …) must NEVER be modified, rebased, built, or committed to unless the operator EXPLICITLY authorizes a specific change. We *version past* production to add features — we never patch production in place. **ALL** inference-research / kernel / benchmarking work happens on `llama.cpp-experimental` branches (that worktree exists precisely for this) — NEVER on production. Every new kernel feature follows four steps, in order:
1. **Pull fresh production → `llama.cpp-experimental`.** Start each effort from the *current* production tip so all production optimizations (iqk AVX-512 GEMM, CPU forward-ports, server work) are already present. Do NOT keep accumulating work on a long-lived experimental branch forked from an old production tip.
2. **Build** in `llama.cpp-experimental`.
3. **Validate no regressions** vs the production kernel (GPU + CPU; the CPU session audits CPU regressions).
4. **Deploy** the validated experimental kernel as a NEW production version (e.g. v9).

The experimental kernel MUST be the FULL build (fresh production + all new features) BEFORE promotion — NOT reconciled via cherry-picks at promotion time. REASON: a complete experimental kernel lets you regression-test the whole thing against production before deploying; deferring the production-merge (cherry-picking iqk/CPU work in at promotion) means those combined changes were never validated together, so regressions slip in unverified. Bench numbers must also come from the full experimental candidate binary — a bench build missing our own GPU opts is not the real spec. **Motivating failure:** the GPU-opts branch forked from v6 on 2026-06-22, but the iqk port landed on production 2026-06-25; because step 1 (fresh-pull) was skipped and the branch was never re-synced, it silently lacked the entire iqk subsystem (0 of 8 `GGML_IQK` references) — on track to "become v7" missing a core CPU-performance subsystem. Discovered + rectified 2026-07-06.

Key scripts by repo:
- **Seeding/benchmarking**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` (seed_specialist_routing.py, seeding_*.py)
- **Server management**: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/` (orchestrator_stack.py)
- **Model registry (full)**: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`
- **Model registry (lean)**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`
- **Hermes setup**: `/mnt/raid0/llm/epyc-root/scripts/hermes/` (setup, config, launch script)

**Single source of truth**: `/workspace/repos/<name>` is a symlink to `/mnt/raid0/llm/<name>` (or `/mnt/raid0/llm/llama.cpp` for `epyc-llama`). Both paths refer to the same physical tree — parallel agent sessions touching either path operate on the same clone, branch, and staging area. Always-good identity: `stat -c %i /workspace/repos/<name>/.git` equals `stat -c %i /mnt/raid0/llm/<name>/.git`.

For fresh setups: `scripts/clone-repos.sh` creates these symlinks (and falls back to a fresh `git clone` only if no canonical tree exists under `/mnt/raid0/llm/`). Idempotent — re-running converts any pre-existing plain-dir clone in `/workspace/repos/` into a symlink, after moving the old tree to `<name>.bak-<timestamp>`. Use `DRY_RUN=1 scripts/clone-repos.sh` to preview.

**If you see divergent commits between `/workspace/repos/<name>` and `/mnt/raid0/llm/<name>`**: the symlink was replaced by a real clone (a parallel agent ran `git clone` directly into the repos path, or `clone-repos.sh` predates the 2026-05-22 fix). Push any unique commits from both sides, then re-run `scripts/clone-repos.sh` to re-link. The script will back up the divergent clone before symlinking — verify the backup contains nothing unique before deleting.

## Dependency Map

See `.claude/dependency-map.json` for formal coupling edges between repos. Key relationships:
- **orchestrator -> llama**: Binary dependency (launches llama-server)
- **orchestrator -> research**: Data dependency (registry references benchmark results)
- **research -> llama**: Binary dependency (benchmarks invoke llama binaries)
- **root -> orchestrator**: Validation dependency (hooks validate artifacts)

## Governance Infrastructure

### Hooks (`scripts/hooks/`)
Pre/post tool-use hooks for Claude Code sessions. These enforce:
- Filesystem path safety (`check_filesystem_path.sh`)
- Agent file schema validation (`agents_schema_guard.sh`)
- Agent reference validation (`agents_reference_guard.sh`)
- Pytest memory safety (`check_pytest_safety.sh`)

### Validation (`scripts/validate/`)
Governance validators that run across repos:
- Agent structure validation
- CLAUDE.md matrix consistency
- Document drift detection
- Numeric literal auditing

### Agent Files (`agents/`)
Agent role definitions using thin-map architecture:
- `shared/` — Common standards (engineering, operating constraints, workflows)
- Role overlays — Per-agent specialization files

### Skills (`.claude/skills/`)
Reusable Claude Code skill definitions for common workflows.

### Commands (`.claude/commands/`)
Slash command definitions for Claude Code sessions.

## Handoff Workflow

Handoffs track cross-repo work items:
- `handoffs/active/` — In-progress work
- `handoffs/blocked/` — Waiting on dependencies
- `handoffs/archived/` — Historical reference

**Start here**: [`handoffs/active/master-handoff-index.md`](handoffs/active/master-handoff-index.md) — single entry point for discovering all active work. Dispatches to 6 domain-specific sub-indices (plus standalone strategy indices, e.g. harness-selection, reviewer-control-plane).

**Current architecture review (2026-06-12)**: the `handoffs/completed/fable5-findings-*` set is the standing strategic assessment - start at `fable5-findings-00-executive-summary.md`; the prioritized queue rewrite was applied into `handoffs/active/master-handoff-index.md` and the historical proposal now lives at `handoffs/completed/fable5-proposed-master-index-rewrite.md`.

### Handoff Index Documents

When creating an index that coordinates multiple handoffs, it must be an **actionable coordination point** — not a passive navigation document. Required sections:
1. **Prioritized task list with checkboxes** — extract all outstanding tasks from linked handoffs, ordered by priority and dependency
2. **Dependency graph** — which tasks block which
3. **Cross-cutting concerns** — how changes in one subsystem affect others
4. **Reporting instructions** — what to update after task completion
5. **Key file locations** — implementation targets

An agent pointed at an index should be able to autonomously discover, prioritize, and execute outstanding work across all linked subsystems.
- `handoffs/completed/` — Done

When completing handoffs, extract findings to docs, then move to `completed/`.

**Checkbox discipline (all sessions, including autonomous checkpoints):** the handoff dashboard's progress metric counts checkbox state only — prose status updates are invisible to it. Any handoff edit recording completed work must flip the matching `- [ ]` → `- [x]` (append `✅ YYYY-MM-DD` inline); work discovered mid-flight gets its own `- [ ]` task line (or `- [x] … ✅ date` if already done). Never record task completion as prose alone.

## Progress Tracking

Daily progress in `progress/YYYY-MM/YYYY-MM-DD.md`. Always update after significant work.

## Agent Logging

```bash
source scripts/utils/agent_log.sh
agent_session_start "Session purpose"
agent_task_start "Description" "Reasoning"
agent_task_end "Description" "success|failure"
```

Audit trail in `logs/agent_audit.log`. Analysis: `scripts/utils/agent_log_analyze.sh --summary`.

## Measurement & Claims

`/workspace/MEASUREMENT.md` is the instrument constitution (adopted 2026-06-12). The short form:
- A decision-gating number = `(metric, protocol-id, n/reps, date, attestation ref)`. A number without a protocol citation is an **observation** — usable for hypotheses, never to gate keep/revert/deploy/promote/buy/close decisions.
- **Historical numbers**: era-label first (`epyc-orchestrator/orchestration/instrument_eras.yaml`), then apply the verb — retro-certified → use; demoted-to-prior → hypothesis only (re-measure if it must gate); retired-view → consult the era-appropriate rebuilt view. Never edit historical records to "fix" them — append.
- Benchmarks run only via the codified recipes (`bench_canonical.sh`/`canonical_recipe.py`) with operator approval; agent digest at `agents/shared/MEASUREMENT_POLICY.md`.
- **Deterministic replay before regeneration** (operator-ratified 2026-07-27): if a result is obtainable by deterministically rescoring/transforming saved inference outputs, ALWAYS do that instead of re-running inference; rebaseline only the axis that changed. Full rule: `agents/shared/MEASUREMENT_POLICY.md` → *Deterministic replay before regeneration*.
- **Consolidated apply-time ratification** (operator-ratified 2026-07-27): evidence collection/validation never waits on a human signature; the human signs ONCE per trust boundary, at apply time, over a consolidated evidence bundle. Failed validations repair + re-present the same token — never a new chain. Never gate unrelated work on a pending boundary token. Full rule: `agents/shared/MEASUREMENT_POLICY.md` → *Consolidated apply-time ratification*.
- The measurement trust boundary (MEASUREMENT.md, eval tower, scoring, safety gates, era registry rows) is human-amendment-only.

## Session Management

- `scripts/session/session_init.sh` — Discover models, verify llama.cpp
- `scripts/session/health_check.sh` — System health
- `scripts/session/verify_llama_cpp.sh` — Check llama.cpp branch safety
- `scripts/nightshift/` — Autonomous overnight run infrastructure

## Web Search Routing

Two web-search paths are available in this session:

1. **Built-in `WebSearch` tool** — Anthropic-hosted, opaque engine selection, US-only. Best for one-shot lookups where a single result suffices.
2. **`bash scripts/search/searx.sh '<query>'`** — self-hosted SearxNG at `localhost:8888`, returns structured JSON with `engines[]`, `score`, `unresponsive_engines[]`. Best for engine-diversity / multilingual / bulk queries.

**Prefer SearxNG when**:
- Running ≥3 web searches in one phase (literature expansion, cluster surveys).
- Querying non-English content (Chinese-lab papers, EU/JP sources).
- Engine-consensus matters (consistent hits across DDG / Brave / Wikipedia / Qwant).
- You will pipe results through `jq` / `grep` before using them.

**Stick with `WebSearch` when**:
- One-shot factual lookup; the auto-summary is fine.
- SearxNG health check fails (script exits 2).

Health-check / fallback semantics: `searx.sh` exits 2 with a fallback message if `localhost:8888` is unreachable or the endpoint returns valid JSON that is not a SearXNG payload with a `.results` array. On exit 2, switch to `WebSearch` for that query. Do not probe `localhost:8090` for `/search`; ports `8090-8095` are BGE embedding servers and return llama-server 404s for SearXNG paths.

## Historical Documentation Warning

Documents in `handoffs/archived/`, `handoffs/completed/`, `progress/`, and `CHANGELOG.md` describe historical state — they may reference `/mnt/raid0/llm/claude` (the pre-split monorepo, archived 2026-02-25) and describe code structure that has since changed. **Always verify against actual code before trusting archived descriptions.** Use the repository structure documented above for current paths.

## Code Style

- Shell: `#!/bin/bash` with `set -euo pipefail`
- Always log all actions via agent_log.sh
- Run validation after producing artifacts

## Process Management

- When asked to kill a process, **verify it is actually dead** after the kill attempt. Run `ps -p <pid>` to confirm. If SIGINT/SIGTERM fails, immediately escalate to SIGKILL. Do not report success until `ps` confirms the PID is gone.
- When running autopilot or long-lived server processes, **always check if the running process is stale** (predates recent code changes) before declaring a fix is deployed. Compare process start time (`ps -o lstart -p <pid>`) against file modification times. Restart the process if needed.
- **API reload vs full stack reload**: when the orchestrator API (uvicorn, port 8000) needs a restart, reload only the API — do NOT reload the entire stack (which restarts llama-servers, embedders, etc). Use `orchestrator_stack.py reload orchestrator`. **API-only reload: do NOT stop autopilot first** — it will reconnect to the new API. **Full stack reload: stop autopilot first**, then reload, then restart it.
- **Reload ownership**: this HOW guidance does not authorize WHO may trigger a reload or WHEN — including the API-only case. If a session owns the inference, any reload (API-only or full stack) must be executed by that session, at a moment it chooses; it is never forced on its workflow from outside. Full rule + origin incident: `agents/shared/OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*.

## Research Intake

- **Never dismiss a research source, model, or technique as "not applicable" or "impractical" without asking the user first.** There is often existing infrastructure context that makes things feasible. When in doubt, flag it for review rather than rejecting.

## Debugging

- When debugging performance or quality issues, **always confirm the metric direction** (higher=better vs lower=better) and ensure you are comparing the correct baselines before proposing fixes. Do not patch symptoms — identify the actual root cause first.
- If unsure about the objective or metric semantics, ask before proceeding.

## Agents & Automation

- **Do not add intake entries, handoff stubs, or other index modifications via sub-agents without explicit user approval.** All index changes must be traceable to a direct user request.

### Codex Delegation Policy

- In Codex sessions, keep the main thread focused on high-level decomposition, risk and ownership decisions, reviewing and accepting delegated work, integration, and operator communication.
- Delegate independent, well-defined tasks whenever possible. Use the smallest capable `gpt-5.6-terra` or `gpt-5.6-luna` agent at the lowest adequate effort (`low`, `medium`, `high`, or `xhigh`).
- Treat every sub-agent result as proposed work: the main thread must review its evidence and diffs and run appropriate validation before accepting it.
- Delegate wrap-up routines to `gpt-5.6-luna` at `high` effort when available. If Luna is unavailable, automatically use `gpt-5.6-terra` at `high` effort without blocking or requesting an operator override.
- Run a formal wrap-up at every natural phase boundary or major campaign milestone. Update owning-handoff checkboxes and progress immediately as gates land; never defer dashboard truth until the next wrap-up.
- When the operator grants exclusive machine access, keep independent CPU and GPU lanes active concurrently. If inference is idle, use all protocol-permitted CPU cores for parallelizable preparation, validation, and analysis; serialize only for explicit protocol constraints, dependencies, or measured resource contention.
- **Long-horizon throughput contract (operator, 2026-07-27):** (1) *Run-first bias* — observation-grade evidence runs on the current validated instrument and fixes on failure; multi-pass adversarial review is reserved for decision-grade gates and trust-boundary artifacts, max ONE independent review per new instrument before its first run. (2) *Saturation scheduling* — maintain a deep-enough work queue that CPU and GPU always have a running task; on ANY block (operator token, review, build), immediately start the next queued item. (3) *Boundary tokens are presented only while compute is saturated* (see MEASUREMENT_POLICY → Consolidated apply-time ratification). (4) A failed operator-presented command is an agent defect; pre-validate end-to-end.

- **Bus drain (session bus M1, 2026-07-27):** at every task boundary, run
  `scripts/coordination/session_bus.py drain --agent <your-roster-id> --triage` and act on
  assignments and nudges; write acks and status to **your own** outbox (`outbox/<your-id>.jsonl`).
  The `--triage` section (2026-07-29) is the standing queue of messages ROUTED to you
  (`needs_routing_to` / `action_required`) — cursor-independent and printed in full; clear an item
  by responding from your outbox with `corr_id` set (a bare ack clears reach-only routing but not
  an action_required item). Never write another agent's file — `queue.jsonl` and `inbox/*` belong
  to the coordinator-daemon. Contract:
  [`coordination/session-bus/BUS_PROTOCOL.md`](coordination/session-bus/BUS_PROTOCOL.md).
- **Coordinating other sessions?** Your role file is
  [`agents/coordinator-agent.md`](agents/coordinator-agent.md) — cross-main sequencing, decision
  packages, lease grants, integration, and the session-lifecycle rules (an idle main with an empty
  queue is a coordination failure; `/clear` only after a wrap-up AND only when the next task is
  disjoint). Full lifecycle contract: `agents/shared/OPERATING_CONSTRAINTS.md` → *Session
  Lifecycle: wrap-up, clear, close*.
- **Refresh your heartbeat at the same boundary**, not just once at startup:
  `session_bus.py append --agent <id> --target heartbeat --json '{"state":"working","task_id":"<id>"}'`
  (`state`: `idle` | `working` | `draining`). A heartbeat written once is a birth certificate, not
  a liveness signal — and a stale one is actively harmful: the stall ladder reads it as a stall and
  nudges a healthy agent, while `tmux_adapter.py` refuses to nudge a genuinely idle one. Observed
  2026-07-27: a live session's heartbeat was 2h stale while it was mid-generation, and only the
  second signal prevented a spurious nudge.

## Operator Decision Requests

- **Never ask the operator an open-ended question when escalating a decision.** Every request for input is a decision package: 2–4 concrete options with tradeoffs (cost / risk / time / quality / reversibility) and supporting data, a recommendation with reasoning, and the default outcome if no choice is made. Claude Code sessions deliver this via the AskUserQuestion tool (recommended option first, labeled "(Recommended)"). Full contract: `agents/shared/OPERATING_CONSTRAINTS.md` → *Operator Decision Requests*.
- Pure factual gaps (missing credential, ambiguous reference) may be asked directly.

<!-- gitnexus:start -->
<!-- gitnexus:keep -->
# GitNexus — Code Intelligence

Indexed as **epyc-root** (29981 symbols, 34306 relationships, 139 execution flows). Use the `gitnexus` CLI; `gitnexus-*` skills auto-surface in the Skill tool.

**Re-index when stale:** `scripts/gitnexus-analyze.sh` — NOT bare `gitnexus analyze` (re-installs skills into a nested subdir). The wrapper takes a nonblocking per-repo lock at `/tmp/gitnexus-<repo>-analyze.lock`; exit `75` means another analyze is already running, so wait/retry rather than deleting `.gitnexus/` metadata. Interrupted incremental metadata should force GitNexus' normal rebuild path.

## Required before editing

- Run `gitnexus impact <symbol> --direction upstream`. Report blast radius + risk to the user. STOP and warn if HIGH or CRITICAL.
- Run `gitnexus status` once per session; re-analyze via wrapper if stale.

## Required for renames / refactors

- Run `gitnexus context <symbol>` to enumerate every caller/file BEFORE editing. Find-and-replace alone is unsafe.
- See the `gitnexus-refactoring` skill for the full workflow.

## Skills (invoke via Skill tool)

`gitnexus-exploring` · `gitnexus-impact-analysis` · `gitnexus-debugging` · `gitnexus-refactoring` · `gitnexus-guide` · `gitnexus-cli`

## Additional CLI

`gitnexus query <concept>` (execution flows) · `gitnexus cypher <query>` (graph) · `gitnexus wiki` (docs)
<!-- gitnexus:end -->
