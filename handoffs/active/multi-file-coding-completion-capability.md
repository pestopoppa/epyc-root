---
title: Multi-file coding completion failure (coder_escalation = Qwen3.6-35B-A3B) — capability investigation
status: open — root issue isolated, awaiting a dedicated brainstorming/remediation session
created: 2026-05-27
owners: unassigned (operator will drive a dedicated session)
priority: HIGH (core coding-capability gap — affects every read-then-edit coding task)
related:
  - orchestration/model_registry.yaml  # coder_escalation role config (~line 903)
  - scripts/benchmark/bep_ab.py         # the multi-file task harness
  - data/bep_sandbox/                   # tasks + results + per-turn traces
---

# Multi-file coding completion failure — capability investigation

## The core issue (unresolved)

The orchestrator's coding role **`coder_escalation` (Qwen3.6-35B-A3B Q8, an MoE with ~3B active params,
shared with `frontdoor`)** cannot reliably complete multi-step coding tasks of the form
**"read an existing file → edit it → finish."** It succeeds *only* on pure create-from-scratch tasks
(where no prior file needs to be read). Every task that requires reading existing code before editing
runs to the turn cap without producing a correct, complete result.

This is a **capability/behavior gap of the model on the read→edit→finish loop**, not a tooling gap (the
execution harness was independently verified to be correct — see "How it was verified" below).

**Note on the model:** `coder_escalation` is a *general* model (Qwen3.6-35B-A3B Q8), not a coding
specialist. The dedicated coder (`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M`) was swapped OUT for it on
2026-05-06. So the role is currently a 3B-active general MoE doing all hard coding work.

## The test workload (where the failure is reproduced)

A fixed 5-task micro-benchmark in a clean scratch git repo, each task graded by a deterministic verifier
(`scripts/benchmark/bep_ab.py`, tasks in `data/bep_sandbox/tasks.jsonl`):

| Task | Kind | What it requires | Result |
|------|------|------------------|--------|
| `t1_create_util` | create | Write `mathutil.py` with `add(a,b)`. **No read.** | **PASSES** |
| `t2_add_and_use` | multi-file modify | Add `square(x)` to existing `calc.py`; import+use it in `main.py` (must print `25`). | FAILS |
| `t3_method_and_caller` | multi-file modify | Add `area()` to `Rect` in existing `shapes.py`; `report.py` already calls it (must print `20`). | FAILS |
| `t4_rename_module` | rename + import-fix | Rename `helpers.py`→`utils.py`; fix the import in `app.py`. | FAILS |
| `t5_bugfix` | single-file modify | Fix `total(price)` in existing `tax.py` (`*0.1` → `*1.1`). | FAILS |

**The discriminator is the READ step, not multi-file-ness:** `t5` is single-file and still fails; the
common factor across all four failures is "must read existing code first." `t1` is the only task needing
no read, and it is the only one that passes.

### Observed per-task failure modes (from per-turn traces)
The model, after (correctly) reading the file, exhibits one of:
- **Read-loop:** re-emits the same `peek(...)` read turn after turn, never advancing to a write (seen on
  `t3`, `t5`).
- **Write-then-stall:** writes a file but never calls `FINAL()`, so it never terminates; re-writes or goes
  idle until the turn cap (seen on `t2`).
- **Empty turns:** emits no code at all for several turns (`raw=""`) — see the confound below.
- **Wrong/incomplete edit:** writes *something* (touched>0) but the result fails the verifier (e.g. `t2`
  edited files but `main.py` didn't print `25`).

All failures terminate at the 8-turn cap with `quality_pass=False`.

## How it was verified that this is the MODEL, not the harness

Before concluding capability, the execution path was made provably correct end-to-end. With **all** of the
following confirmed working, the model still failed every read-then-edit task on **both** editing strategies:

1. **Reads return real content.** The model's `peek()`/`grep()` resolve to the task workspace and return
   the actual file contents (verified: the read content appears in the next prompt and the model echoes it
   back, e.g. reconstructing `calc.py`'s existing `double()` before adding `square()`).
2. **Writes land in the workspace.** `file_write_safe(<relative path>, ...)` writes to the task workspace
   (verified: `touched_files > 0`, writes confirmed on disk).
3. **Execution output feeds back.** The previous turn's stdout/result is injected into the next prompt
   (verified in the prompt builder and in traces).
4. **A hard loop-break intervention fires.** A guard detects ≥2 consecutive no-progress turns and injects a
   forceful directive ("stop repeating; you already have the content [included]; write the file now or call
   FINAL"). This was **proven to fire on the live path** (an instrumented probe showed the no-progress
   counter accumulating across turns, and traces showed the directive injected at the threshold). The model
   even **wrote a file in direct response** to it once — yet still did not complete the task.
5. **Both editing strategies fail equally.** Interleaved per-turn edits AND batched (sandbox-verified,
   transactional) patch application both yield **1/5** (only `t1`). So it is not specific to one edit path.

→ With reads, writes, feedback, and a forceful anti-loop nudge all working, the coder still cannot converge
on a correct multi-file edit + termination. That is the capability signal.

## ⚠ One confound to rule out FIRST (could change "capability" → "config fix")

Qwen3.6 has a documented **degenerate `<think>`-loop failure** unless `enable_thinking=false` is *applied*
(empty/looping output with no usable content). The registry **does** set `enable_thinking: false` for
`coder_escalation` — **but that setting only takes effect on the chat-completions path**
(`ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES`), not the plain `/completion` path. It was **not confirmed** that
`enable_thinking=false` is actually applied on the REPL coder turns used by this harness, and the observed
**empty (`raw=""`) turns are consistent with thinking-mode output being stripped to empty**.

**First action for the next session (cheap, high-leverage):** confirm the coder REPL turns run with
thinking genuinely off (inspect the path / look for degenerate thinking / verify the chat-completions route
covers `coder_escalation`). **If thinking is leaking on, this is partly a configuration bug, not a pure
capability gap** — and fixing it could materially change the pass rate. Do this before investing in
model/training remediation.

## Brainstorming directions (if it is genuinely capability)

- **Model choice:** the role is a 3B-active *general* MoE. Benchmark a coding-specialist (e.g. re-evaluate
  the swapped-out Qwen3-Coder-30B, or a current coder model) specifically on read→edit→finish multi-file
  tasks — the 2026-05-06 swap optimized other metrics and may have regressed multi-step editing.
- **Task scaffolding:** free-form REPL may be too unstructured for multi-step edits. Try an explicit
  state-machine prompt (read → plan → write file 1 → write file 2 → verify → FINAL) or a planning turn.
- **Edit affordance:** a structured diff/patch tool (apply-unified-diff with base-hash) may suit the model
  better than free-form `file_write_safe` of full file contents.
- **In-loop verification feedback:** the verifier currently runs post-hoc. Feeding a quick self-check / the
  verifier result back into the loop could let the model iterate to correctness instead of stalling.
- **Termination cue:** the model frequently fails to emit `FINAL()` after editing. A stronger
  "edits-done → FINAL" cue (or auto-FINAL when all target files are written + a self-check passes) may help.
- **Scope realism:** these are deliberately minimal micro-tasks. Re-check against the model's real
  production coding workload to gauge how much this generalizes vs. is a micro-task artifact.

## Reproduce

```bash
cd /mnt/raid0/llm/epyc-orchestrator
# Pause J6 first (it is the only inference load; concurrent runs poison timing — feedback_no_concurrent_inference).
python3 scripts/benchmark/bep_ab.py --reps 1 --max-turns 8 --host-quiet-confirmed \
  --output data/bep_sandbox/results-<name>
# For the live no-progress counter probe, set ORCHESTRATOR_LOOPGUARD_PROBE=1 in the run env
# (the loop-guard itself is flag-gated default-off via ORCHESTRATOR_REPL_LOOP_GUARD).
```
Inspect `data/bep_sandbox/results-<name>/results.jsonl` (per-task pass/turns/touched) and
`.../traces/<task>-<arm>-blk0.jsonl` (per-turn: what the model emitted, whether it wrote/FINAL'd).
Reference run with everything working + the issue reproduced: `data/bep_sandbox/results-readfix7/`.

## Key files / locations
- `orchestration/model_registry.yaml` — `coder_escalation` (~line 903): Qwen3.6-35B-A3B Q8, `enable_thinking: false`.
- `scripts/benchmark/bep_ab.py` — the A/B harness; `data/bep_sandbox/tasks.jsonl` — the 5 task definitions.
- `src/graph/helpers.py` `_execute_turn` — the LLM→REPL turn loop the model runs in.

## Constraint
`feedback_no_concurrent_inference`: J6 (the autopilot soak) is the only inference load on the host. Any A/B
run must pause J6 first and requires operator host-quiet approval; restore J6 afterward.
