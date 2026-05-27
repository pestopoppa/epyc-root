---
title: Multi-file coding completion — diagnosed agentic read→edit→finish protocol gap (coder_escalation = Qwen3.6-35B-A3B)
status: REMEDIATION BUILT 2026-05-27 — diagnosed as an agentic protocol/tool-loop problem, NOT model coding capability (one-shot ablation 5/5 on the same tasks+verifiers while the REPL/BEP loop fails); model swap moot. Fix shipped = first-class flag-gated `force_mode="edit"` one-shot edit transaction (default-OFF): module validated 5/5, live server path validated 3/3. 5-point review hardening landed 2026-05-27 (fail-closed 412 / scope caps / clean syntax-check / all-or-nothing / cc-roles single-source-of-truth — d4fafdf; stat-before-read scope cap fba6c84). Open = production rollout decision (when/how routine coding edits auto-route to edit-mode) + smart target selection + optional functional-verifier-in-the-loop (self-check is syntax-only today).
created: 2026-05-27
owners: unassigned (operator will drive a dedicated session)
priority: HIGH (core tool-mediated coding-completion gap; diagnosis proven, remediation open)
related:
  - orchestration/model_registry.yaml   # coder_escalation OPERATIONAL role config at line 381 (enable_thinking:false); model-catalog block at ~903 is separate
  - scripts/benchmark/bep_ab.py          # the multi-file task harness
  - data/bep_sandbox/                    # tasks + results + per-turn traces
---

# Multi-file coding completion — diagnosed agentic read→edit→finish protocol gap

## Diagnosis

The orchestrator's coding role **`coder_escalation` (Qwen3.6-35B-A3B Q8 — general MoE, ~3B active,
shared with `frontdoor`)** is strong enough to solve the BEP scratch coding workload, but the current
REPL/BEP interaction contract prevents reliable completion on read-first edits. The failing surface is
not "multi-file coding" in general; it is the **read→state→edit→finish protocol**: repeated reads,
empty turns, forbidden `open()` attempts in the batch arm, missing writes, and missing `FINAL`.

This should **not** be treated as evidence that Qwen3.6 is weak at coding in the usual benchmark sense.
The registry records the opposite: the deployed Qwen3.6 role scored **29/30 (97%) on the coder suite**,
**26/30 (87%) on the agentic suite**, and **170/183 (93%) overall** under the May-4 Claude-as-Judge
battery (`orchestration/model_registry.yaml:920`). The one-shot ablation below directly confirms that
benchmark context: Qwen3.6 solves the exact failed read-first tasks when the edit contract is changed.

**Model context:** `coder_escalation` is currently `Qwen3.6-35B-A3B Q8` (general, but benchmark-strong).
The dedicated coder `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M` was swapped OUT for it on 2026-05-06 because
Qwen3.6 outscored it on the canonical coder battery. That makes a simple "bad coding model" diagnosis
wrong for this issue. **Do not pursue a model swap as remediation for BEP-2 multi-file completion.**

## ✅ RESOLVED via one-shot ablation (2026-05-27) — it's protocol/tooling, NOT capability

The protocol ablation was run and is **decisive**. Given the file contents in a single `direct`-mode prompt
(no REPL / `peek` / `FINAL` / batch `patchset` choreography) and asked for the complete new files,
`coder_escalation` (Qwen3.6) **solved all 5 tasks — 5/5 PASS — under the SAME
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
NOT a thinking misconfig**. The model-swap comparison is therefore **moot** — Qwen3.6 is
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
  writes; on-arm mostly created solution artifacts or stalled; only t2-off wrote and still failed). The
  one-shot ablation separates that from raw coding skill: the remaining problem is how the REPL/BEP contract
  asks the model to read, retain state, write, and terminate.

## Thinking/runtime confounds ruled out

Qwen3.6 degenerates into empty/`<think>`-loop output unless `enable_thinking=false` is applied. The
orchestrator code **already supports this** for `coder_escalation`: it defaults the role onto the
chat-completions route and injects the registry `chat_template_kwargs` (`src/llm_primitives/backend.py:76`,
`src/backends/llama_server.py:493`), and the registry sets `enable_thinking: false` at the **operational
role config** (`orchestration/model_registry.yaml:381`; the separate model-catalog block ~line 903 carries
`disable_thinking: true` but is NOT the runtime role config — inspect line 381). The one-shot ablation also
returned concise correct outputs with `think=False` for all 5 tasks. That rules out the thinking-template
confound for the diagnosed issue.

`results-readfix7` still has value as a contaminated REPL/BEP trace set, but not as a capability measurement:
backend outage, inference timeouts, and empty turns prevent treating its OFF/ON score as a clean rate. Use it
only for failure-mode examples while designing the protocol fix.

## Remediation — ✅ first-class edit transaction BUILT + validated (2026-05-27)
The ablation localized the fix to the **interaction contract**, and the recommended fix shape is now
implemented and validated end-to-end (flag-gated, default-OFF, zero production behavior change until enabled):

- **`src/edit_transaction.py`** — assemble workspace files → ask the model **once** for the complete
  new files (`<<<FILE: path>>>…<<<END>>>`, fenced-block fallback) → **transactional apply**
  (snapshot → write/delete → **syntax-check via `compile()`** → promote, or **roll back the whole
  transaction** on any failure; any unsafe/escape path also aborts the whole transaction) → return a
  concise summary. Path-safe (`_safe_join` preserves nested dirs, rejects `..`/absolute escapes). Scope is
  **capped (≤50 files / ≤400 KB, checked by `stat` before any read)**. The REPL is untouched.
- **Wired as `force_mode="edit"`** (chat.py `_handle_chat` branch 8b2): the model is called once via the
  same `_execute_direct` path, the transaction is applied, and the turn **auto-finalizes** (`turns=1`,
  no multi-turn read→write→`FINAL` choreography). gitnexus: `_handle_chat` LOW risk.
  **Safety gate:** fires only when **both** `ORCHESTRATOR_EDIT_TRANSACTION=1` **and** a scoped
  `ORCHESTRATOR_EDIT_ROOT` are set; an explicit `force_mode="edit"` with either missing **fails closed
  (HTTP 412)** rather than silently using the REPL. Without the scoped root, assembly would read/rewrite
  the whole orchestrator repo — so the gate is mandatory.
- **Validated:** `tests/unit/test_edit_transaction.py` + `test_chat_completions_roles.py` **21/21** (incl.
  rollback-on-syntax-error, **all-or-nothing escape-abort**, **scope caps via `stat`**, **no-`__pycache__`**
  self-check); module end-to-end through the real coder **5/5** (`scripts/benchmark/bep_edit_transaction_validate.py`);
  **live server `force_mode=edit` 3/3** (`scripts/benchmark/bep_edit_mode_wiring.py` — create / read-first
  multi-file / rename+delete, `mode=='edit'` + verifier PASS on the scratch the server edited); +55 chat
  route/endpoint/canary tests green.

**✅ Hardened (review 2026-05-27 — commits `d4fafdf` + `fba6c84`):**
- **Fail-closed edit mode** — explicit `force_mode="edit"` with the flag/root missing now returns **HTTP 412**
  (was: silent REPL fall-through, which would reintroduce the loop this work avoids). Live-verified 412.
- **Scope caps** — `assemble_context` fail-closes (no model call, no writes) above 50 files / 400 KB, checked
  by `stat().st_size` **before any content read** (bounds IO/memory, not just model calls — fba6c84).
- **Self-contained commits** — the series was rewritten so each commit contains ONLY this work; parallel-agent
  topology (`backend.py`) + inference-tap (`chat.py`/`requests.py`) changes that had been transiently swept in
  were returned to the working tree for their owners. Clean-worktree build verified.
- **Clean syntax-check** — `compile(src, path, "exec")` (no `__pycache__`/`.pyc` side effects the rollback
  wouldn't track).
- **All-or-nothing** — any unsafe (escape/absolute) path aborts the WHOLE transaction (nothing written).
- **cc-roles SoT** — `src/chat_completions_roles.py` is now the single source of truth; chat.py (3 sites) +
  backend.py share it (was divergent inline defaults, and the env var is unset in prod → defaults were
  load-bearing → latent double-templating for `coder_escalation`). Direct ablation **5/5** with the canonical
  default confirms `coder_escalation` correctly relies on server-side jinja — no regression.

**Post-rewrite audit (Codex wrap-up 2026-05-27):**
- Clean detached worktree at `fba6c84` constructs prewarm backends successfully, so the earlier swept-in
  `topology_role` constructor mismatch is gone.
- Clean detached worktree tests: `tests/unit/test_edit_transaction.py` + `test_chat_completions_roles.py`
  **21/21 PASS**; `test_chat_routes.py` + `test_chat_endpoints.py` + `test_bep_canary.py` **55/55 PASS**.
- Residual polish only: `src/edit_transaction.py` still has one stale docstring phrase saying
  `py_compile self-check` although implementation uses `compile()`, and the HTTP 412 fail-closed behavior is
  live-probed but should get a committed route regression test before broad rollout.

**Open / not-yet-done (rollout decisions, not blockers):**
- **Default routing.** Edit-mode is opt-in (`force_mode="edit"` + flags). Routine coding edits do NOT yet
  auto-route to it — needs a routing decision (which tasks/roles, and a non-scratch edit-root policy).
- **Smart target selection.** Scope caps are the safety *floor*; selecting the *relevant* files (vs assembling
  the whole scoped root) is the enhancement for larger repos. A structured base-hash patch form is an option.
- **Functional verifier in the loop.** The self-check is **syntax-only** (`compile`) — it does not run a task's
  functional verifier or re-prompt on failure. Iterate-on-verifier-failure is a possible enhancement.
- **Model choice:** MOOT — Qwen3.6 is proven capable one-shot; do NOT pursue a model swap for this problem.

## Reproduce
```bash
cd /mnt/raid0/llm/epyc-orchestrator
# Pause J6 first (only inference load; concurrent runs poison timing — feedback_no_concurrent_inference).

# Reproduce the decisive one-shot protocol ablation.
python3 scripts/benchmark/bep_oneshot_ablation.py | tee /mnt/raid0/llm/tmp/bep_oneshot/run.log

# Optional: reproduce the contaminated REPL/BEP failure traces for failure-mode inspection.
# Add a backend-health preflight before trusting any new REPL/BEP result.
python3 scripts/benchmark/bep_ab.py --reps 1 --max-turns 8 --host-quiet-confirmed \
  --output data/bep_sandbox/results-<name>     # ORCHESTRATOR_LOOPGUARD_PROBE=1 for the live counter probe
```
Then classify per-task by failure REASON from `.../traces/<task>-<arm>-blk0.jsonl` (the `raw_output` per
turn shows backend errors vs timeouts vs empties vs real model code). Contaminated reference run (do NOT
re-use as evidence): `data/bep_sandbox/results-readfix7/`.

## Key files
- `orchestration/model_registry.yaml:381` — `coder_escalation` OPERATIONAL role config (`chat_template_kwargs.enable_thinking: false`, `model_role: qwen36_q8_0`). The model-catalog block at ~903 (`disable_thinking: true`) is NOT the runtime role config — inspect line 381.
- `orchestration/model_registry.yaml:920` — benchmark context: Qwen3.6 role is 29/30 coder, 26/30 agentic, 170/183 overall.
- `scripts/benchmark/bep_oneshot_ablation.py` — protocol ablation driver; path-safe (preserves nested paths under scratch, rejects `..`/absolute escapes) so it is reusable beyond the 5 top-level sandbox tasks.
- **`src/edit_transaction.py`** — the shipped one-shot edit-transaction module (assemble → one-shot → parse → transactional apply w/ rollback). Flag: `edit_transaction_enabled()` ⇐ `ORCHESTRATOR_EDIT_TRANSACTION=1`.
- **`src/api/routes/chat.py`** branch **8b2** — `force_mode="edit"` wiring (`_execute_direct` llm_call closure → `run_edit_transaction` → auto-finalize). Allowlist + `force_mode` doc updated (`src/api/models/requests.py`).
- **`tests/unit/test_edit_transaction.py` + `tests/unit/test_chat_completions_roles.py`** (21) · **`scripts/benchmark/bep_edit_transaction_validate.py`** (module 5/5) · **`scripts/benchmark/bep_edit_mode_wiring.py`** (live server 3/3) — the validation ladder.
- `src/llm_primitives/backend.py:76`, `src/backends/llama_server.py:493` — chat-completions route + chat_template_kwargs injection (code supports thinking-off).
- `scripts/benchmark/bep_ab.py`; `data/bep_sandbox/tasks.jsonl` — harness + task defs.
- `src/graph/helpers.py` `_execute_turn` — the LLM→REPL turn loop.

## Constraint
`feedback_no_concurrent_inference`: J6 (autopilot soak) is the only inference load. Any run must pause J6
first + needs operator host-quiet approval; restore J6 afterward. The `:8070` backend outage that
contaminated `results-readfix7` is itself a reminder to preflight backend health before scoring.
