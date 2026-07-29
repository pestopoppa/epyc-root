# Task: static contract audit of the E8 harness (READ-ONLY)

**Assigned to** `fable-auditor` (roster id — use it verbatim for every bus command).
**Assigned by** coordinator-agent on operator direction, 2026-07-28.
**Mode: READ-ONLY.** You write no code, run no inference, take no region claim, and change no
file outside your own bus outbox/heartbeat/cursor. Your deliverable is findings.

## Why you exist

`codex` (window `agent:codex-inference`) is repairing the tail of an E8 quality-baseline
campaign. In roughly two hours it has produced **three consecutive failed-closed cycles, each
surfacing a DIFFERENT defect in a DIFFERENT layer**:

1. **18:06** — run saved all 298 unique generation rows, then failed closed after bounded
   API-reload watcher failures. Audit found two instrument defects: the snapshot publisher
   **overwrote an input root `source_binding` while retaining its stale self-hash**, and
   **watcher abort bypassed deterministic clean-journal / failure-ledger terminalization**.
2. **19:15** — mixed tail run completed all 13 generation requests under a clean 197-sample
   watcher, but **six exact saved rows timed out at 300s** (ordinals 138, 253, 296, 346, 475,
   493) and the runner refused publication. Race set still outstanding: 97, 203, 279.
3. **19:36** — codex ruled its own first c1 attempt **inadmissible**: the runner omitted the
   explicit **EvalTower sidecar dir** and used the **raw scoring-vector question instead of the
   sealed reconstructed execution question**. Row 138 produced a mismatched identity and an
   obviously wrong answer, so deterministic reuse was rejected.

Every one of those was caught rather than published — the instrument is behaving correctly. The
problem is the SHAPE: codex only discovers a contract violation when a run trips it, so each
defect costs a full cycle. **You are here to find the remaining violations statically, in one
pass, instead of one-run-at-a-time.** That is the entire value proposition — a serial
run-discover-fix loop with no visible bound, converted into a single audit.

Nothing has been applied. Failed evidence is immutable. All four CPU regions are currently free.

## PRIMARY SCOPE — do this first, and finish it before anything else

Audit the E8 harness **contract set as a whole**, not defect-by-defect. The three failures above
are your evidence that these contracts were never audited together. Look for the ones that have
not yet been tripped.

Contracts known to be load-bearing:

- **Copy-only terminalizer / clean-journal + failure-ledger path** — currently being implemented
  by codex. Does every abort path reach deterministic terminalization, or only the happy path?
  Failure 1 was precisely an abort path that bypassed it.
- **Snapshot publisher: `source_binding` + self-hash semantics.** Failure 1 overwrote an input
  root binding while keeping a stale self-hash. Where else can a hash outlive the thing it
  attests? Codex's stated fix is "root-only binding semantics" — verify that actually closes it
  rather than narrowing it.
- **Watcher abort vs terminalization ordering**, including the bounded-failure path that the two
  external API reloads (16:26:13Z, 16:40:48Z) exercised.
- **Runner question-sealing contract** — sealed reconstructed execution question vs raw
  scoring-vector question; explicit EvalTower sidecar dir. Failure 3. Are there other call sites
  that can pick the wrong question or omit the sidecar?
- **Timeout classes** — the 300s inner timeout vs the "exact outer-timeout class" codex is
  adding. Is a timeout distinguishable from a failure everywhere it matters, or only where it
  has already bitten?
- **Deterministic reuse / replay admissibility** — what makes a saved row eligible for
  deterministic reuse, and can an ineligible row slip through any path?
- **Race rows** (97, 203, 279) — retained for race-only retry. What guarantees a race row is
  never silently promoted to a clean row?

Where to look: `epyc-orchestrator` (`/mnt/raid0/llm/epyc-orchestrator`) —
`scripts/benchmark/finalize_e8_quality_baseline_v5_recovery_r2.py`,
`scripts/benchmark/validate_e8_quality_baseline_v5.py`,
`scripts/benchmark/prepare_e8_quality_baseline_v5_partial_r2_successor.py`,
`scripts/benchmark/operator_candidates/*e8*`, plus whatever they import. Also
`epyc-root/tests/test_e8_quality_*` (3 of those currently FAIL — that is pre-existing and is
itself evidence worth reading, but do not fix them).

**The question to answer for each contract: can it fail OPEN?** A contract that fails closed is
an inconvenience. One that fails open publishes a wrong number into a decision-gating baseline,
and that is the failure mode this whole instrument exists to prevent.

## SECONDARY SCOPE — only after the primary is complete and reported

The **entire embedding tier is dead** and has been for some time (PIDs far older than the rest of
the fleet): `server_8096` granite-embedding-97m-multilingual, `server_8097`
multilingual-e5-base-Q8_0, `server_8098` bge-m3-Q8_0. `whisper` (9000) is also dead. Everything
else in the stack is healthy, and Episodic FAISS reports 58,655/58,655 indexed (100%).

The question — the same shape as the primary scope: **do consumers of those embedding endpoints
fail closed, or silently fall back?** A fail-open fallback poisons the store it writes into, and
its detector often needs the very component that is down. Determine whether anything has been
quietly degrading: retrieval paths, reseeding, skill/strategy stores, episodic memory writes.

Report findings only. **Do NOT restart those services** — a reload freeze is in effect and the
session holding inference owns its own restarts.

## Hard constraints

- **READ-ONLY.** No code changes, no fixes, no commits, no pushes. If you find something urgent,
  report it — do not fix it.
- **No inference, no benchmarks, no `region-lock` claim.** codex owns E8 and still has ~9 ordinals
  of regeneration to run plus a canonical FG-4b re-anchor.
- **Do not reload or restart anything** — API, stack, or component. Freeze in effect.
- **Do not send keys to any tmux window**, do not create tmux sessions.
- **Do not edit files codex is working in.** It is actively editing the E8 scripts; read them,
  never write them.
- Interpreter for anything you run: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`.
- Do not tick any checkbox anywhere.

## Reporting

Register first, then drain and refresh your heartbeat at every task boundary:

    ./scripts/coordination/session_bus.py append --agent fable-auditor \
      --target heartbeat --json '{"state":"working","task_id":"e8-harness-contract-audit"}'

Report to `coordinator-agent` via `outbox/fable-auditor.jsonl` only. For each finding give:
the contract, the exact file:line, whether it can fail OPEN or only closed, a concrete failure
scenario, and severity. **Rank by whether a wrong number can reach a decision-gating baseline** —
that ordering is more useful to codex than a flat list.

Report the primary scope as soon as it is done; do not hold it back waiting on the secondary.
Time matters: codex is blocked on this tail and a host reboot is queued behind it.
