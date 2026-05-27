---
title: Multi-file coding completion — suspected gap on read→edit→finish (coder_escalation = Qwen3.6-35B-A3B)
status: open — SIGNAL ONLY (not cleanly demonstrated); needs a clean confirmation run + a model comparison
created: 2026-05-27
owners: unassigned (operator will drive a dedicated session)
priority: HIGH (if real, it is a core coding-capability gap)
related:
  - orchestration/model_registry.yaml   # coder_escalation OPERATIONAL role config at line 381 (enable_thinking:false); model-catalog block at ~903 is separate
  - scripts/benchmark/bep_ab.py          # the multi-file task harness
  - data/bep_sandbox/                    # tasks + results + per-turn traces
---

# Multi-file coding completion — suspected read→edit→finish gap

## The suspected issue (NOT yet cleanly demonstrated)

There is a **signal** that the orchestrator's coding role **`coder_escalation` (Qwen3.6-35B-A3B Q8 — a
general MoE, ~3B active, shared with `frontdoor`; NOT a coding specialist)** struggles to complete
multi-step **"read an existing file → edit it → call FINAL"** coding tasks, while it completes pure
create-from-scratch tasks fine. The discriminator of interest is the **read step** (a single-file
read-then-edit, `t5`, is in the suspect set — it is not specifically about multi-file).

**This is a hypothesis, not a proven verdict.** The one A/B run that appeared to show it
(`results-readfix7`) is **contaminated** (see below), so it does not cleanly separate model capability
from infrastructure noise. The next session's job is to get a **clean** signal and then a **comparison**,
not to assume the gap is real.

**Model context:** `coder_escalation` is currently `Qwen3.6-35B-A3B Q8` (general). The dedicated coder
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M` was swapped OUT for it on 2026-05-06 (optimizing other metrics). So
a general 3B-active MoE is doing all hard coding — relevant to whether the gap (if real) is model choice.

## The test workload

5 micro-tasks in a clean scratch git repo, verifier-graded (`scripts/benchmark/bep_ab.py`, tasks in
`data/bep_sandbox/tasks.jsonl`), run as an OFF (interleaved edits) vs ON (batched edits) A/B:

| Task | Kind | Requires | Verifier |
|------|------|----------|----------|
| `t1_create_util` | create | write `mathutil.py` (**no read**) | `import mathutil; add(2,3)==5` |
| `t2_add_and_use` | multi-file modify | add `square` to `calc.py`; use in `main.py` | `python3 main.py` == `25` |
| `t3_method_and_caller` | multi-file modify | add `area()` to `Rect` in `shapes.py`; `report.py` calls it | `python3 report.py` == `20` |
| `t4_rename_module` | rename + import-fix | rename `helpers.py`→`utils.py`; fix import in `app.py` | `helpers.py` gone & `python3 app.py`==`hi` |
| `t5_bugfix` | single-file modify | fix `total()` in `tax.py` (`*0.1`→`*1.1`) | `tax.total(100)==110` |

## ⚠ The reference run (`results-readfix7`) is CONTAMINATED — read this before trusting any "it fails" claim

Per-turn trace inspection shows **none** of the failing tasks failed cleanly on model behavior:

Per-turn bucket counts (mutually-exclusive; from the trace `raw_output`s, n=8 turns each unless noted):

| Task / arm | turn breakdown | verdict |
|------------|----------------|---------|
| t1-off | 1 turn: wrote file → PASS | PASS |
| t1-on  | 2 turns: 1 model turn + batch edit applied → PASS | PASS |
| **t4-off** | **8/8 `[ERROR: Backend unavailable (circuit open): :8070]`** | INFRA — discard |
| **t5-off** | **8/8 backend-unavailable** | INFRA — discard |
| **t4-on**  | **3 connection-refused + 3 backend-unavailable + 2 forbidden `open()` attempts** | INFRA-dominated — discard |
| t2-off | 1 write + 1 other model turn + **4 empty** + **2 inference-timeout** | MIXED — not clean |
| t2-on  | 1 model turn + 4 empty + 3 inference-timeout (0 writes) | MIXED — not clean |
| t3-off | 4 model turns (no write) + 3 inference-timeout + 1 empty | MIXED — not clean |
| t3-on  | **6 model turns (no write) + 2 inference-timeout** | closest to model-behavior, still 2 infra turns |
| t5-on  | 3 model turns + **5 empty** (no backend error; 0 writes) | model-ish, but empties unexplained |

So the headline "OFF 1/5, ON 1/5" **must not be read as a 1/5 capability rate.** A mid-run backend outage
on `:8070` knocked out t4/t5-off and t4-on entirely; inference timeouts hit t2/t3; and the empty-output
turns (t2, t3, t5-on) are unexplained (could be model behavior OR the thinking confound below). **There is
no clean capability data point in this run.**

## What IS solidly established (so the next session doesn't re-litigate it)

- **The execution harness mechanics are correct** — file reads resolve to the task workspace and return
  real content; the `file_write_safe` write tool works *when invoked*; previous-turn output feeds back into
  the next prompt; and a hard loop-break intervention is wired and was **proven to fire** (instrumented
  live probe: the no-progress counter accumulates across turns; the directive is injected at the threshold;
  the model wrote a file in direct response once). **Do NOT re-debug the loop-guard** — that bug is resolved
  separately (flag-gated default-off `ORCHESTRATOR_REPL_LOOP_GUARD`; probe `ORCHESTRATOR_LOOPGUARD_PROBE`).
- **BUT** "the write tool is functional" is NOT "the model reliably chooses and completes the right edits."
  In this run most failing tasks never produced meaningful target-file writes at all (t3/t4/t5-off: 0 target
  writes; on-arm mostly created solution artifacts or stalled; only t2-off wrote and still failed). Whether
  that is model behavior vs. the contamination above is exactly what the clean run must separate.

## Confound to settle definitively (narrowed)

Qwen3.6 degenerates into empty/`<think>`-loop output unless `enable_thinking=false` is applied. The
orchestrator code **already supports this** for `coder_escalation`: it defaults the role onto the
chat-completions route and injects the registry `chat_template_kwargs` (`src/llm_primitives/backend.py:76`,
`src/backends/llama_server.py:493`), and the registry sets `enable_thinking: false` at the **operational
role config** (`orchestration/model_registry.yaml:381`; the separate model-catalog block ~line 903 carries
`disable_thinking: true` but is NOT the runtime role config — inspect line 381). So the open question is
**not** "does the code support it?" — it is
**"did the live A/B run's process env + request payload actually carry `enable_thinking=false`?"** The empty
turns (t2/t3/t5-on) are consistent with thinking output stripped to empty, so this must be confirmed at
runtime (capture/inspect the actual request payload for a coder REPL turn), not assumed from the code path.

## The actual next step: a CLEAN confirmation matrix

Before concluding anything about capability, run a clean, controlled matrix:
1. **Backend-health preflight** — assert all coder backends (`:8070` etc.) are up + circuits closed
   *immediately before* the run, and abort/skip on any backend-unavailable turn (don't score it).
2. **Prove `enable_thinking=false` in the live payload** — capture the actual request payload for a
   `coder_escalation` REPL turn and confirm the flag is present (rules out the confound at runtime).
3. **Rerun the suspect tasks** (`t2`, `t3`, `t5`) with the above clean, several reps each, and classify each
   failure by *reason* (read-loop / no-write / wrong-edit / FINAL-missing), not by aggregate pass rate.
4. **Compare models** — run the same clean matrix on the current general `Qwen3.6-35B-A3B` route vs a real
   coding-specialist route. If a specialist clears the read→edit tasks and the general model doesn't, that
   is the real signal (and points at the 2026-05-06 swap as the regression). Coding specialists confirmed
   available — exact GGUF paths verified on disk:
   - **`Qwen3-Coder-30B-A3B-Instruct` Q4_K_M** — `/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
     (18.5 GB). **Cleanest comparison: this WAS `coder_escalation` until the 2026-05-06 swap to the general
     Qwen3.6**, so it directly tests whether the swap regressed multi-file editing. MoE, ~3B active.
   - **`Qwen2.5-Coder-32B-Instruct` Q4_K_M** — `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf`
     (19.8 GB). A **dense 32B** coding specialist (dense-vs-MoE is a useful second axis).
   - Note: `/mnt/raid0/llm/models/` holds SEAL-concise fine-tunes of both + `Qwen3-Coder-REAP-246B-A35B-Q4_K_M.gguf`
     (a larger pruned-MoE option), NOT the two baseline files above — use the `lmstudio/` paths for a clean baseline.

Only after 1–3 are clean and 4 shows a model-attributable gap should this be called a capability problem.

## Brainstorming directions (only if a clean run confirms a real gap)
- **Model choice:** general 3B-active MoE vs a coding specialist for `coder_escalation`.
- **Task scaffolding:** explicit read→plan→write→verify→FINAL state machine vs free-form REPL.
- **Edit affordance:** structured diff/patch tool (base-hash) vs free-form full-file `file_write_safe`.
- **In-loop verification feedback:** feed a quick self-check / the verifier result back so the model iterates.
- **Termination cue:** stronger "edits-done → FINAL" (the model frequently fails to terminate after editing).

## Reproduce
```bash
cd /mnt/raid0/llm/epyc-orchestrator
# Pause J6 first (only inference load; concurrent runs poison timing — feedback_no_concurrent_inference).
# Add a backend-health preflight (see step 1 above) before trusting results.
python3 scripts/benchmark/bep_ab.py --reps 1 --max-turns 8 --host-quiet-confirmed \
  --output data/bep_sandbox/results-<name>     # ORCHESTRATOR_LOOPGUARD_PROBE=1 for the live counter probe
```
Then classify per-task by failure REASON from `.../traces/<task>-<arm>-blk0.jsonl` (the `raw_output` per
turn shows backend errors vs timeouts vs empties vs real model code). Contaminated reference run (do NOT
re-use as evidence): `data/bep_sandbox/results-readfix7/`.

## Key files
- `orchestration/model_registry.yaml:381` — `coder_escalation` OPERATIONAL role config (`chat_template_kwargs.enable_thinking: false`, `model_role: qwen36_q8_0`). The model-catalog block at ~903 (`disable_thinking: true`) is NOT the runtime role config — inspect line 381.
- `src/llm_primitives/backend.py:76`, `src/backends/llama_server.py:493` — chat-completions route + chat_template_kwargs injection (code supports thinking-off).
- `scripts/benchmark/bep_ab.py`; `data/bep_sandbox/tasks.jsonl` — harness + task defs.
- `src/graph/helpers.py` `_execute_turn` — the LLM→REPL turn loop.

## Constraint
`feedback_no_concurrent_inference`: J6 (autopilot soak) is the only inference load. Any run must pause J6
first + needs operator host-quiet approval; restore J6 afterward. The `:8070` backend outage that
contaminated `results-readfix7` is itself a reminder to preflight backend health before scoring.
