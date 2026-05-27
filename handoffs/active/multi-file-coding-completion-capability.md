---
title: Multi-file coding completion — suspected agentic read→edit→finish gap (coder_escalation = Qwen3.6-35B-A3B)
status: DIAGNOSED 2026-05-27 — agentic protocol/tool-loop problem, NOT model coding capability (one-shot file-edit ablation passed 5/5 on the same tasks+verifiers while the REPL/BEP loop fails). Remediation = edit-protocol redesign; model swap is moot. Open = building/validating the protocol fix.
created: 2026-05-27
owners: unassigned (operator will drive a dedicated session)
priority: HIGH (if real, it is a core tool-mediated coding-completion gap)
related:
  - orchestration/model_registry.yaml   # coder_escalation OPERATIONAL role config at line 381 (enable_thinking:false); model-catalog block at ~903 is separate
  - scripts/benchmark/bep_ab.py          # the multi-file task harness
  - data/bep_sandbox/                    # tasks + results + per-turn traces
---

# Multi-file coding completion — suspected agentic read→edit→finish gap

## The suspected issue (NOT yet cleanly demonstrated)

There is a **signal** that the orchestrator's coding role **`coder_escalation` (Qwen3.6-35B-A3B Q8 —
general MoE, ~3B active, shared with `frontdoor`)** struggles inside the current REPL/BEP contract on
multi-step **"read an existing file → edit it → call FINAL"** tasks, while it completes pure
create-from-scratch tasks fine. The discriminator of interest is the **read→state→edit→finish loop**
(a single-file read-then-edit, `t5`, is in the suspect set — it is not specifically about multi-file).

This should **not** be treated as evidence that Qwen3.6 is weak at coding in the usual benchmark sense.
The registry records the opposite: the deployed Qwen3.6 role scored **29/30 (97%) on the coder suite**,
**26/30 (87%) on the agentic suite**, and **170/183 (93%) overall** under the May-4 Claude-as-Judge
battery (`orchestration/model_registry.yaml:920`). The open question is narrower: whether the current
tool-mediated completion protocol makes a strong model fail to convert read context into edits and a
terminating `FINAL`.

**This is a hypothesis, not a proven verdict.** The one A/B run that appeared to show it
(`results-readfix7`) is **contaminated** (see below), so it does not cleanly separate model capability
from infrastructure/protocol noise. The next session's job is to get a **clean** signal and then run
targeted ablations, not to assume the gap is real.

**Model context:** `coder_escalation` is currently `Qwen3.6-35B-A3B Q8` (general, but benchmark-strong).
The dedicated coder `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M` was swapped OUT for it on 2026-05-06 because
Qwen3.6 outscored it on the canonical coder battery. That makes a simple "bad coding model" diagnosis
unlikely; model comparison is still useful, but only as one ablation among protocol/runtime checks.

## ✅ RESOLVED via one-shot ablation (2026-05-27) — it's protocol/tooling, NOT capability

The protocol ablation (clean-matrix step 4) was run and is **decisive**. Given the file contents in a
single `direct`-mode prompt (no REPL / `peek` / `FINAL` / batch `patchset` choreography) and asked for the
complete new files, `coder_escalation` (Qwen3.6) **solved all 5 tasks — 5/5 PASS — under the SAME
verifiers**, including every read-first task that fails the REPL/BEP loop (t4 correctly emitted a delete +
two rewrites). Clean run: `:8070` healthy, **no `<think>` leakage** (the `enable_thinking` confound is also
ruled out — the model produced concise correct output), all deterministically verifier-graded.

| Task | one-shot `direct` | REPL/BEP loop |
|------|-------------------|---------------|
| t1 create | PASS | PASS |
| t2 add+use | **PASS** | fail |
| t3 method+caller | **PASS** | fail |
| t4 rename+import (delete + 2 rewrites) | **PASS** | fail |
| t5 bugfix | **PASS** | fail |

**Conclusion:** the model produces every correct edit one-shot → the multi-file failures are an **agentic
protocol / tool-interaction problem** (read→`peek`→edit→`FINAL` loop discipline), **NOT coding capability and
NOT a thinking misconfig**. The model-swap comparison (step 5 below) is therefore **moot** — Qwen3.6 is
demonstrably capable; remediation belongs entirely in the interaction contract (see Remediation). Driver:
`scripts/benchmark/bep_oneshot_ablation.py`; raw model outputs: `/mnt/raid0/llm/tmp/bep_oneshot/out_*.txt`.

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

## Working hypothesis

My current read is that the first-order suspect is **agentic protocol fit**, not raw model coding capability.
The traces show failures around the interaction contract: repeated reads after content was available, empty
turns, forbidden `open()` attempts in the batch arm, no target-file writes, and missing `FINAL` after edits.
Those are tool-use/state/termination failures under a constrained REPL loop. They are different from "can the
model solve a coding task when the files are provided and it can answer with a patch?"

So the next run should not just ask "does Qwen3.6 lose to a coding specialist?" It should first ask whether
Qwen3.6 can solve the same tasks under a simpler one-shot file-edit contract. If it can, the work belongs in
prompt/protocol/tooling (state machine, patch affordance, verifier feedback, termination). If it cannot, then
model capability or role choice becomes the stronger explanation.

## The actual next step: a CLEAN confirmation matrix

Before concluding anything about capability, run a clean, controlled matrix:
1. **Backend-health preflight** — assert all coder backends (`:8070` etc.) are up + circuits closed
   *immediately before* the run, and abort/skip on any backend-unavailable turn (don't score it).
2. **Prove `enable_thinking=false` in the live payload** — capture the actual request payload for a
   `coder_escalation` REPL turn and confirm the flag is present (rules out the confound at runtime).
3. **Rerun the suspect tasks** (`t2`, `t3`, `t5`) with the above clean, several reps each, and classify each
   failure by *reason* (read-loop / no-write / wrong-edit / FINAL-missing), not by aggregate pass rate.
4. **Protocol ablation** — run the same tasks in a simpler one-shot file-edit mode: provide the required file
   contents in the prompt and ask for a patch/full-file replacement, with no multi-turn REPL, no batch arm
   `patchset` choreography, and no separate `FINAL` step. Verify with the same task verifiers. This separates
   code understanding from tool-loop discipline.
5. **Compare models** — run the same clean matrix on the current general `Qwen3.6-35B-A3B` route vs a real
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

**UPDATE 2026-05-27 — step 4 (the one-shot ablation) was run: Qwen3.6 passed 5/5 while the REPL/BEP loop
fails. So per the rule below, the diagnosis IS protocol/tooling, not coding skill, and step 5 (model
comparison) is moot.** Steps 1–3 / the contaminated-run cleanup remain useful only if you later want a
clean REPL-path failure-mode breakdown to guide the protocol fix.

## Remediation (the ablation confirmed this is the right layer — fix the contract, not the model)
The one-shot ablation passed 5/5, so the work is the **interaction contract**. In rough priority:
- **Give a one-shot / full-file (or structured-patch) edit affordance** for read→edit tasks — the model
  demonstrably succeeds with exactly this shape (hand it the files, take back the complete new files).
  Highest-leverage: it sidesteps the read→`peek`→edit→`FINAL` loop the model can't navigate.
- **Edit affordance:** structured diff/patch tool (base-hash) vs free-form full-file `file_write_safe`.
- **Termination cue:** auto-`FINAL` once all target files are written + a self-check passes (missing-FINAL is
  a top failure mode in the REPL traces).
- **In-loop verification feedback:** feed a quick self-check / verifier result back so the model can iterate.
- **Explicit state machine:** read→plan→write→verify→`FINAL` scaffold vs free-form REPL.
- **Model choice:** MOOT — Qwen3.6 is proven capable one-shot; do NOT pursue a model swap for this problem.

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
- `orchestration/model_registry.yaml:920` — benchmark context: Qwen3.6 role is 29/30 coder, 26/30 agentic, 170/183 overall.
- `src/llm_primitives/backend.py:76`, `src/backends/llama_server.py:493` — chat-completions route + chat_template_kwargs injection (code supports thinking-off).
- `scripts/benchmark/bep_ab.py`; `data/bep_sandbox/tasks.jsonl` — harness + task defs.
- `src/graph/helpers.py` `_execute_turn` — the LLM→REPL turn loop.

## Constraint
`feedback_no_concurrent_inference`: J6 (autopilot soak) is the only inference load. Any run must pause J6
first + needs operator host-quiet approval; restore J6 afterward. The `:8070` backend outage that
contaminated `results-readfix7` is itself a reminder to preflight backend health before scoring.
