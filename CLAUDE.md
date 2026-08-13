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

**2026-08-11 v9 final freeze**: production runs ONE kernel, **production-consolidated-v9** (canonical tree `/mnt/raid0/llm/llama.cpp`, frozen at `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, `llama-server --version` reports `10125`). Ratification: [`artifacts/operator/ratify_v9_final_freeze_20260811.json`](artifacts/operator/ratify_v9_final_freeze_20260811.json), SHA-256 `21c396477c1cdcc71dbaffd7452dd43e7bbf5941b1f199c8a5d217da830945ed`. v8 (`67a433bf45a8a091d83b4ea0b32ff0735fd51800`, binary `10107`) is the rollback anchor. `scripts/session/verify_llama_cpp.sh` enforces the production branch, commit, version, and CPU/HIP binary digests. **ik_llama.cpp is fully deprecated as a serving path** (tree on disk = reference/measurement instrument only).

**iqk coverage (v9, inherited from v8)**: `GGML_IQK=1` accelerates supported K/legacy quants plus IQ2/IQ3 and IQ4_XS; **IQ1 remains stubbed**. See [`handoffs/active/tq3-quantization-evaluation.md`](handoffs/active/tq3-quantization-evaluation.md).

### Experimental Kernel Workflow & Production-Kernel Immutability

**2026-08-11 production kernel set**: the freeze covers a production **KERNEL SET**, not one kernel — `llama.cpp` @ `production-consolidated-v9`, `whisper.cpp` @ `production-speech-v1` (`b30737922`, ggml 0.18.0, STT), `qwentts.cpp` @ `production-speech-v1` (`2c1b5182e`, ggml 0.17.0, TTS). The speech-kernel ratification remains [`artifacts/operator/ratify_speech_kernel_freeze_20260731.json`](artifacts/operator/ratify_speech_kernel_freeze_20260731.json). Both speech kernels carry load-bearing gfx90a/ROCm-6.2 patches. The three trees run three different ggml generations, so **every launcher must set its own `LD_LIBRARY_PATH`** and prove it with `epyc-inference-research/scripts/utils/verify_ggml_linkage.sh` (it lives in the research repo, not root) — a binary that inherits another tree's ggml runs silently wrong. `scripts/session/verify_speech_kernels.sh` enforces the speech branches.

**Production kernels are FROZEN.** `production-consolidated-v9` (and future `-v10`, …) must NEVER be modified, rebased, built, or committed to unless the operator EXPLICITLY authorizes it. We *version past* production — never patch it in place. ALL kernel/benchmarking work happens on `llama.cpp-experimental` branches. Every new kernel feature follows four steps, in order:

1. **Pull fresh production → `llama.cpp-experimental`** — start from the *current* production tip so all its optimizations are present; never accumulate on a long-lived branch forked from an old tip (origin: INC-20260706-iqk-missing-subsystem, `docs/reference/agent-config/INCIDENT_LOG.md`).
2. **Build** in `llama.cpp-experimental`.
3. **Validate no regressions** vs production (GPU + CPU).
4. **Deploy** as a NEW production version. The candidate must be the FULL build (fresh production + all new features) validated as a whole — never reconciled via cherry-picks at promotion time; bench numbers come from the full candidate binary. Promotion checklist includes baking the project agent-file overlay (`docs/reference/agent-config/llama-tree-overlay/`) into the candidate so the new production tree ships freeze-aware agent files.

## Working-tree identity

**Single source of truth**: `/workspace/repos/<name>` is a symlink to `/mnt/raid0/llm/<name>` (`/mnt/raid0/llm/llama.cpp` for `epyc-llama`) — parallel sessions on either path share one clone, branch, and staging area. Identity check: `stat -c %i /workspace/repos/<name>/.git` equals the target's. `scripts/clone-repos.sh` (idempotent, `DRY_RUN=1` to preview) creates/repairs the symlinks and backs up divergent clones — if the two paths ever show divergent commits, push unique commits from both sides first, then re-run it.

## Handoff Workflow

- `handoffs/active/` — In-progress · `handoffs/blocked/` — Waiting · `handoffs/completed/` — Done · `handoffs/archived/` — Historical
- **Start here**: [`handoffs/active/master-handoff-index.md`](handoffs/active/master-handoff-index.md) — **router only** (~70 lines): a domain table, the operator decision queue, and a generated backlog rollup. It owns no backlog rows. Live campaign posture is in [`handoffs/active/CURRENT-CAMPAIGN.md`](handoffs/active/CURRENT-CAMPAIGN.md).
- **Six domain indices** carry the work, one thin row per handoff (`ID | Track | Handoff | Next action | Deps`). **Every active handoff is owned by exactly one index** — a second row is a defect. Liveness (`open`, `last_advanced`, blocked) is **generated**, never hand-written: `python3 scripts/handoffs/index_state.py` writes `handoffs/active/.index-state.json` + the master rollup; `--check` gates coverage/schema/freshness and must exit 0 before committing.
- Standing strategic assessment (2026-06-12): `handoffs/completed/fable5-findings-*`, start at the executive summary.
- **Checkbox discipline**: the dashboard counts checkbox state ONLY — any edit recording completed work flips `- [ ]` → `- [x]` (append `✅ YYYY-MM-DD`); mid-flight discoveries get their own task line. Full axioms: `agents/shared/SESSION_LIFECYCLE.md`.
- **Dispatching or claiming a row: the task TEXT is the identity, `file.md:LINE` is only a hint** —
  if they disagree the text wins; re-resolve with `scripts/coordination/backlog_row_check.py --row
  "<text>"`. Anchor rot is structural, not carelessness (34.5% queue-wide on 2026-08-11, up from
  27% twelve days earlier). And a screener proves **WELL-FORMED, not STILL-NEEDED** — four of eight
  screened rows fact-checked on 2026-08-12 were already satisfied in reality, so verify the row's
  premise before pointing a main at it. Full rule: [Dispatching Backlog
  Work](agents/shared/OPERATING_CONSTRAINTS.md#dispatching-backlog-work--the-task-text-is-the-identity).
- Authoring/editing an index: `docs/guides/agent-workflows/handoff-index-authoring.md` — the thin-row contract. Rows carry a pointer and a next step; **status, evidence and history never go in a row**. On completion, extract findings to docs, move to `completed/`, and delete the row.

## Dashboards

Adding or changing a dashboard surface? The **plane rule** is one paragraph in
[`dashboard/README.md`](dashboard/README.md): data contracts live with the subsystem they observe;
pages, nav and the registry live with the hub (`:8100`); every new dashboard needs a registry entry
**plus** a health probe **plus** a freshness envelope; no unregistered pages. Note which probe:
`/health` is transport-only (*the process is serving*) and stays green over a dead producer —
`/api/health` is the three-valued fold that answers *is what this page shows still true*.

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

## Belief Kernel — wiring new sources

If a process you are working on produces **measurements or verified findings**, surface the wiring
task *immediately*: add a row to the source table in
[`scripts/vidya/adapters/README.md`](scripts/vidya/adapters/README.md) and a task in
[`handoffs/active/vidya-belief-substrate-program.md`](handoffs/active/vidya-belief-substrate-program.md).
Not later, not "when the substrate is ready".

Wiring the **write** side is cheap and permanent; retrofitting the **read** side is impossible — a
tuple invented on read claims warrant the original run never captured. `benchmarks/results` is the
standing proof: 4,562 files, no write-side hook, 0 of 200 sampled carry a usable claim tuple, so
they can never gate a decision.

**Do not write a new grading rule.** An adapter *projects* its native record into a `ClaimTuple`
and `claim_tuple.grade()` decides; the carrier is shared but each source class has exactly one
ladder, and the registry refuses a second. Contract: `docs/design/vidya-pilot-spec.md` §4.7.

**Citing an intake entry as rationale?** `python3 scripts/vidya/cli.py cite-check --as-of <ts>`
gates `intake-NNN` citations in handoffs, wiki and docs (exit 3 on a refuted, conflicted, or
dangling one). Three forms: `intake-896` relies on the whole entry and **inherits every defect of
every claim in it**; `intake-896#03` relies on one claim; `intake-896#record` *discusses* the record
and asserts nothing. Prefer the precise forms — and note that writing *about* an entry in prose is
itself a citation, so a findings write-up needs `#record` or it flags its own report. The consumer
table is in [`scripts/vidya/adapters/README.md`](scripts/vidya/adapters/README.md).

## Debugging

- **Always confirm metric direction** (higher/lower=better) and correct baselines before proposing fixes; identify root cause, don't patch symptoms.
- If unsure about objective or metric semantics, ask before proceeding.
- **A measurement whose window does not overlap the phenomenon is not evidence of its absence.**
  Sample DURING, never after — a post-exit sample cannot distinguish *never resident* from
  *finished*. Any idle/absent/stalled claim rests on a condition **persisting across several
  samples**: `llama-bench` exits between probes, so 0% util and 0% VRAM are the normal reading
  inside a healthy sweep, and one-at-a-time dispatch manufactures idle-looking hardware. Full
  rule: [Observation
  Windows](agents/shared/OPERATING_CONSTRAINTS.md#observation-windows--a-sample-that-misses-the-phenomenon-proves-nothing).
- **"I invoked the HIP build" is not evidence of a HIP run, and `ldd` cannot prove one** —
  llama.cpp *dlopens* `libggml-hip.so`, so the executable shows zero HIP linkage either way while
  `/etc/environment` puts the CPU build early in `LD_LIBRARY_PATH` (the three-ggml-generations
  hazard above). Prove residency: `verify_ggml_linkage.sh`, non-zero VRAM sampled during the run,
  KFD process count. Full rule: [Inference and
  Benchmarks](agents/shared/OPERATING_CONSTRAINTS.md#inference-and-benchmarks).

## Agents & Automation

- **Fan out subagents by default — always, not only when a dispatch says so.** Your own thread is for
  review, integration and task boundaries; execution (implementation, docs, research, analysis,
  verification harnesses) goes to **3–5 subagents running concurrently**, model and effort matched to
  the task. Every subagent result is PROPOSED work — review evidence and diffs before accepting. A main
  working serially is a defect in the agent files, not a nudge target. Operator, 2026-08-12: *"this
  should ALWAYS be the case."* Full rule: [Parallel Subagent Fan-Out](agents/shared/OPERATING_CONSTRAINTS.md#parallel-subagent-fan-out--the-default-working-mode-of-every-main).
- **No intake entries, handoff stubs, or index modifications via sub-agents without explicit user approval.**
- **Codex delegation & long-horizon throughput contract**: `agents/shared/OPERATING_CONSTRAINTS.md` → *Codex Delegation & Long-Horizon Throughput*.
- **Bus drain (M1)**: at every task boundary run `scripts/coordination/session_bus.py drain --agent <your-roster-id> --triage`; act on assignments/nudges; write acks to **your own** outbox with `corr_id` for routed items; never write another agent's file. Contract: [`coordination/session-bus/BUS_PROTOCOL.md`](coordination/session-bus/BUS_PROTOCOL.md).
- **Coordinating other sessions?** Role file: [`agents/coordinator-agent.md`](agents/coordinator-agent.md). Session lifecycle (wrap-up, `/clear`, close, idle-main axiom): `agents/shared/SESSION_LIFECYCLE.md`.
- **Refresh your heartbeat at the same boundary**: `session_bus.py append --agent <id> --target heartbeat --json '{"state":"working","task_id":"<id>"}'` (`idle`|`working`|`draining`). A heartbeat written once is a birth certificate, not a liveness signal (origin: INC-20260727-stale-heartbeat).
- **Reading ANOTHER session's state? Three states, not two — working / compacting / idle.** A
  session compacting its context renders IDENTICALLY to a finished one (goal line, "Pursuing goal"
  timer and background-terminal count all vanish at once), so pane text can never clear a main.
  The authoritative instrument is `tmux_adapter.py`'s runtime check, and **an adapter refusal
  citing runtime state is a finding about the world, not an obstacle to retry past.** Heartbeats
  lie in the other direction — measured 2026-08-12: `working` while 446s stale, pane idle for
  three watcher cycles, GPU at 0%. When heartbeat, pane and hardware disagree the hardware wins,
  provided the hardware reading persists across samples. Full rule: [Reading another session's
  liveness](agents/shared/SESSION_LIFECYCLE.md#reading-another-sessions-liveness--three-states-not-two).

## Operator Decision Requests

See **Act, Don't Defer** at the top of this file before escalating anything. When a choice genuinely is
the operator's, use the canonical [operator decision-package contract](agents/shared/OPERATING_CONSTRAINTS.md#operator-decision-requests).

<!-- gitnexus:start -->
<!-- gitnexus:keep -->
# GitNexus — Code Intelligence

Indexed as **epyc-root** (42864 nodes, 57165 edges, 462 clusters, 300 execution flows). Use the `gitnexus` CLI; `gitnexus-*` skills auto-surface in the Skill tool.

**Re-index when stale:** `scripts/gitnexus-analyze.sh` — NOT bare `gitnexus analyze` (re-installs skills into a nested subdir and rewrites this block). The wrapper takes a nonblocking per-repo lock at `/tmp/gitnexus-<repo>-analyze.lock`; exit `75` means another analyze is already running — wait/retry, never delete `.gitnexus/` metadata.

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
