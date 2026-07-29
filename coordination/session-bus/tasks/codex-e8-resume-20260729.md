# TASK BRIEF — codex — post-reboot E8 resume + stack ownership

**Roster id:** `codex` · **Lane:** cpu · **Assigned by:** coordinator-agent, 2026-07-29
**Operator decisions this brief executes:** bringup order = *daemon+supervisor, then codex owns
stack bringup*; CPU lane = *E8 and E5 run concurrently on separate mains, arbitrated by
region-lock*; lost tokens = *codex re-validates, coordinator re-presents*.

## 0. Read first, in this order

1. `coordination/session-bus/tasks/post-reboot-session.md` — the fleet handover. It is a pointer
   document; follow its pointers.
2. `coordination/session-bus/outbox/fable-auditor.jsonl`, task `e8-harness-contract-audit` — six
   tier-A fail-open contracts, the two CRITICAL ones verified closed at pinned commit `182ccef6`.
   **Read this BEFORE re-running any E8 harness step.** The audit exists to replace the serial
   run-discover-fix loop; re-running first re-enters the loop it was built to end.
3. `handoffs/active/gpu-serving-tie-in-program.md` § P0-1, P0-2.

## 1. Host state as of 14:15Z (verified, not assumed)

- Uptime **~30 min** — the decision-grade P-BENCH uptime window (≤1 week) is **reopened**.
- `verify_llama_cpp.sh` **PASS**: `production-consolidated-v8` @ `67a433bf4`, CPU + HIP servers
  both `10107`, tree clean.
- **region-lock: q0/q1/q2/q3 all free.** The pre-reboot q3 hold did not survive.
- **Serving stack entirely DOWN** — all llama-servers, orchestrator API (8000), all 6 embedders,
  handoff dashboard `dead`; searxng / crawl4ai / nextplaid-* docker containers `stopped`.
- **AutoPilot DOWN** (no process). Nothing measured against this host right now is
  representative — see §5.
- coordinator-daemon restarted at 14:14Z (pid `14553`, epoch 12+), supervised by `bus_supervisor.sh`
  (pid `14518`).

## 2. You are the inference owner

Per `agents/shared/OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*, the session holding the
inference executes its own reloads, on its own schedule. **You bring the stack up and you own it
from that moment.** No other session may reload the API or the stack around you; route any such
request to the coordinator and it comes back to you.

- Bring the stack up with `orchestrator_stack.py` (never ad-hoc `llama-server` invocations).
- **Load models sequentially**, not in parallel.
- Three gates, all required before declaring the stack up: pipeline-green ≠ processes started ≠
  live matches config. Verify the third explicitly.
- `orchestrator_stack.py status` currently emits
  `runtime-facts selected-servers read failed (ImportError: cannot import name 'LLAMA_SERVER' from
  partially initialized module 'scripts.server.stack_paths' … circular import)`.
  Status still renders. **File this as a defect on the bus; fix it only if it blocks you** — it is
  not your assigned work.

## 3. Re-validate the two orphaned operator gates — do this before the E8 work proper

Both of your pre-reboot `token-request` messages **were never delivered** to the coordinator's
inbox and never reached `tokens/token-queue.md`. Triage found them only by outbox scan. They were
never presented to the operator, so **neither was signed and neither is expired-by-decision — they
are undelivered**.

| Gate | Script | Problem |
|---|---|---|
| `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729` | `artifacts/operator/ratify_e8_final_c1_retry_capacityfix_20260729.sh` | pins root main `300ed404`; root is now `b998b0b5` → will refuse on drift. Scope also said "before reboot". |
| `RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` | `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729.sh` | pins pre-reboot state; host-exclusive by design. |

For each: re-validate against current HEAD, repair the pin, confirm `--validate-only` /
`--dry-run` exits `0`, and **re-file the token-request from your outbox** with
`needs_routing_to: ["coordinator-agent"]` **and** `action_required: true` set as structural fields
(not prose — prose routing is invisible to tools and gets truncated away). Per the
consolidated-ratification rule, **repair and re-present the SAME token chain — do not mint a new
one.** I present only what dry-runs clean; a presented command that fails is a defect attributed
to the requesting agent.

## 4. The assigned work — E8 P0-1, in your own stated order

Your pre-reboot handover named three steps and said not to reorder them. Honour that:

1. **Integrate scorer isolation.**
2. **Replay the successor.**
3. **Fix the historical-receipt / runtime-helper dual binding** — and only then rerun the audit.

State at close: 279 rows clean, sidecar
`bd89f9e4d7e0a114518a7a0a729b5ea6322ea21e02728f9fc6795db40992a424`. Incomplete: no deterministic
completion, no finalizer inference, no baseline application, no publication. **Race rows 97 / 203 /
279 remain retained for race-only retry and must never be silently promoted to clean rows.** Failed
evidence is immutable; nothing was applied.

**Deterministic replay before regeneration.** If a result is obtainable by deterministically
rescoring or transforming saved inference outputs, do that instead of re-running inference;
rebaseline only the axis that changed.

**Why this is the critical path:** P0-1 (the E8 baseline signature) gates AutoPilot resume (P1-3),
which gates the P2-5f duty-cycle measurement, which gates the shed-batch decision rule. Everything
downstream of it is parked.

### Unmerged branches that are yours
Five branches remain unmerged, all E8-harness or E8-adjacent — the same repair chain you left
mid-sequence. Reconcile in **your stated order** (scorer isolation → replay successor → dual
binding), *not* by branch date:

- `epyc-orchestrator`: `codex/e8-consolidated-wrapper-20260728` (9 commits),
  `codex/e8-abort-terminal-seals-20260729` (3), `codex/e8-typed-provenance-20260729`,
  `e8-v5-runtime-root-20260727` (7), `tierc-10d-crash-window-durability`
- `epyc-root`: `codex-wrapup-precompact-20260729` (doc conflict in `master-handoff-index.md` +
  `progress/2026-07/2026-07-29.md`)

Three epyc-root `codex/e8-*` ratifier branches merged clean but produced a **zero-byte diff**
(duplicate commits already on main) — treat as landed, delete rather than re-merge.

## 5. Constraints with live reasons

- **AutoPilot is DOWN and is the representative production load generator.** Any bench or timing
  number collected against this quiesced host is a measurement artifact, not a finding. This is
  the exact P2-5f trap. If you need representative numbers, say so — do not collect them anyway
  and caveat them later.
- **You are not alone on the CPU.** A second main (`claude-cpu-e5`) is being spawned for E5
  W1-W4 under the operator's explicit concurrent-lane decision. **Acquire region claims via
  `region-lock`; never infer a region is free by observing it** (TOCTOU, BUS_PROTOCOL rule 7).
  If you measure real contention, report it as data — co-residency is a scheduling question for
  the coordinator, never a human approval gate.
- **Benchmarks** run only via the codified recipes (`bench_canonical.sh` / `canonical_recipe.py`);
  import recipe constants rather than retyping remembered values.
- **Never patch a frozen production kernel.** All kernel work happens on `llama.cpp-experimental`.
- **Do not touch E5** — it belongs to `claude-cpu-e5` in full, including its W2 capture smoke.
- Trust boundaries are human-only: never sign, never flip another owner's checkbox, never edit
  `human_only_paths.yaml`.

## 6. Bus discipline

At **every** task boundary:

```bash
python3 scripts/coordination/session_bus.py drain --agent codex --triage
python3 scripts/coordination/session_bus.py append --agent codex \
  --target heartbeat --json '{"state":"working","task_id":"<current>"}'
```

A heartbeat written once is a birth certificate, not a liveness signal — and a stale one is worse
than none, because the stall ladder reads it as a stall and nudges a healthy session. **Your
heartbeat currently reads `working` on `e8-deterministic-completion-repair` from before the
reboot; refresh it as your first bus action.**

Write only your own `outbox/`, `heartbeats/`, `cursors/`. `queue.jsonl` and every `inbox/*` belong
to the coordinator-daemon.

Route routing intent as **structural fields** (`needs_routing_to`, `action_required`), never as
"FOR <AGENT>" prose in the payload. And keep payloads item-specific: a byte-identical payload
repeated across N corr_ids is bus noise by construction (defect C23 — 19 such messages are sitting
in the coordinator's triage queue right now).

## 7. Report back

To coordinator-agent, on task_id `e8-p0-1-resume`:
- stack up / not up, with the third gate (live == config) explicitly evidenced;
- the two re-validated token blocks, or why they cannot be repaired;
- E8 progress against the three ordered steps;
- anything needing an operator signature — immediately, not batched into a wrap-up.

Checkbox discipline: any edit recording completed work flips `- [ ]` → `- [x]` with an inline
`✅ 2026-07-29`. Prose status is invisible to the dashboard.
