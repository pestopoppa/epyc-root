# Brief: Drop `-md <same-file>` double-load for embedded-NEXTN roles

**Current owner/status (2026-07-03):** handed off by the MI210 session to the CPU/RAM orchestrator lane. The launch-code fix, live reload, post-reload acceptance evidence, memory-delta evidence, post-reboot audit, legacy-backend guard, and quiet-window same-workload decode A/B are complete. The CPU A/B closed mixed: memory improved materially, but the no-`-md` embedded path was slower than same-file `-md` under the throwaway `/completion` harness.
**Original target:** a separate CPU / orchestrator session (execute directly).
**Type:** completed production launch-config fix. No GPU, no new inference was required to *decide* the fix; the quiet-window verification is now recorded below.
**Repo edited:** `epyc-orchestrator` (launch-config / arg builder). This brief lives in `epyc-root` (`handoffs/active/`).
**Index note:** the original brief said not to wire it into `master-handoff-index.md` without operator approval; the operator has now explicitly handed the CPU side to this lane, and the root indices/progress record the picked-up status.

---

## Problem

Before the 2026-07-03 fix, production Qwen NEXTN (embedded-MTP) roles were launched with `-md <same GGUF as -m>`. That made `llama-server` load a **second full copy** of the model as the "draft" and draft every token with a **full-model forward pass** — instead of using the embedded NEXTN head via the zero-extra-load self-spec path. The live stack now omits `-md` for same-realpath Qwen NEXTN roles while keeping Gemma's separate assistant-head `-md`.

## Evidence — code path

Repo `/mnt/raid0/llm/llama.cpp`, branch `production-consolidated-v6` (confirmed checked out this session). Read-only audit:

- `tools/server/server-context.cpp:1008` — `const bool has_draft = params.speculative.has_dft();`
- `common/common.h:369-371` — `has_dft()` returns `true` whenever the draft model path (or hf_repo) is **non-empty**, i.e. whenever `-md`/`--model-draft` is passed.
- `server-context.cpp:1172` — `if (has_draft)` enters the draft branch.
- `server-context.cpp:1199` — `llama_model_load_from_file(...)` loads a **second full copy** of the model.
- `server-context.cpp:1207-1209` — `if (spec_mtp)` only flips the context type to `LLAMA_CONTEXT_TYPE_MTP`; it does **not** skip the load above.
- `server-context.cpp:1220-1245` — the zero-extra-load self-spec path (`else if (spec_mtp)`): no new model load, `llama_init_from_model(model_tgt, ...)` at `:1235` **reuses the already-resident target weights**. This branch is reached **ONLY when `-md` is ABSENT** (because a present `-md` makes `has_draft` true and takes the `:1172` branch instead).

**Root cause:** passing `-md <same file>` unconditionally forces the expensive `:1172` branch and locks you out of the cheap `:1220` self-spec path.

## Evidence — measured (GPU, this session)

MI210, Qwen3.6-27B-MTP-Q8_0:
- `--spec-type draft-mtp -md <same file>` → decode **29.75 t/s** ≈ plain **29.51** (~0% MTP gain); server log printed `estimated memory usage of draft model is 26894 MiB` (a full second copy).
- Drop `-md` (`--spec-type draft-mtp` alone, embedded path) → **33.6 t/s (+15.6%)** with a cheap NEXTN draft.

The code path is backend-agnostic, so CPU takes the same branch.

**Honest nuance you MUST carry (do not overstate):**
- The **GPU performance** cost is measured and backend code-path evidence still shows same-file `-md` takes the separate draft branch. The **CPU performance** claim is not positive: the quiet-window CPU A/B below found embedded no-`-md` slower in this harness despite identical draft acceptance.
- The **RAM-doubling** is certain on GPU (separate HBM alloc). On **CPU it depends on mmap**: same file loaded twice **may share the mmap page cache** (→ little/no extra resident RAM), whereas `--no-mmap`/`--mlock` forces more resident pressure. The CPU measurements below show a real PSS reduction, but not a full model-size PSS drop in the throwaway harness.

## Which roles (critical scoping)

Applies **ONLY** to embedded-NEXTN roles where `realpath(-md) == realpath(-m)`.

- **AFFECTED BEFORE FIX** (resolved live 2026-07-03; post-reboot audit still `same_file_md_count=0`):
  - frontdoor `:8070` and its Qwen3.6 quarter replicas — Qwen3.6-35B-A3B-MTP, same-realpath draft/model.
  - architect `:8083` — Qwen3.5-122B-A10B-MTP, same-realpath draft/model.
  - Shared aliases such as **coder_escalation** and **worker_summarize** inherit the fixed frontdoor process rather than launching their own draft.
- **CORRECT — do NOT touch:** gemma-4-26B-A4B worker `:8072` launches `-md <a SEPARATE small assistant head>` (`gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf`). That is a genuine separate draft head. **Keep its `-md`.**

**Rule of thumb:** drop `-md` **only** when `realpath(-md) == realpath(-m)`; keep it when they differ.

## The implemented fix

The orchestrator launch-config / worker-pool arg builder now makes the `-md <same-file>` emission **conditional**:

- For embedded-NEXTN roles (`realpath(-md) == realpath(-m)`): emit `--spec-type draft-mtp` **WITHOUT `-md`** → takes the `:1220` self-spec path.
- For separate-head roles (paths differ): **keep `-md`**.

The implemented lever is in `epyc-orchestrator/scripts/server/` launch construction: generated same-file draft provenance is preserved, but literal `-md` emission is suppressed when target and draft resolve to the same path.

## Verification (three gates + measure)

The 2026-07-03 CPU lane applied this via `orchestrator_stack.py` and reloaded the stack. Audit gates:
1. **pipeline-green.**
2. **role actually starts.**
3. **live == config** — `ps` confirms the affected roles **no longer carry `-md <same file>`** (cross-ref the "verify live affinity/config, not just topology hash" memory).
4. **measured effect** — resident duplicate mapping pressure dropped; decode speed was mixed under the throwaway `/completion` A/B and remains evidence, not a quality promotion.

Cross-reference: stack-change three-gates (pipeline-green ≠ starts ≠ live==config).

## Risk / rollback

**Low.** Dropping the redundant full-model draft restores the intended embedded self-spec; correctness should be unchanged (verify coherence + that acceptance stats now appear). **Rollback = restore the `-md` arg.** Change **one NEXTN role at a time**; frontdoor is highest-value + highest-traffic → validate it **first, in a quiet window**.

## Expected win

Unlocks the real MTP self-spec speedup on GPU (~the +15.6% class measured on MI210) and frees host memory pressure by removing duplicate same-file draft mappings. On CPU, the same-workload A/B measured a memory win but no speed win; keep the production no-`-md` path for duplicate-load hygiene unless later representative eval-fanout evidence proves a throughput regression large enough to justify restoring same-file `-md`.

## Implementation status — 2026-07-03

Code fix landed in `epyc-orchestrator` commit `5b4d8147` (`Drop redundant self-draft model args`), pushed to `spec-dec-mtp-refresh-2026-06-22`.

- `scripts/server/orchestrator_stack.py` now emits `-md` only when `realpath(draft_model_path) != realpath(model_path)` while preserving `--spec-type draft-mtp` / `--spec-draft-n-max` for embedded NEXTN.
- `scripts/server/stack_commands.py` accepts embedded NEXTN launches with `--spec-type` and no `-md` as attestation-clean, but still warns when a separate draft-head role omits `-md`.
- Focused live-registry command smoke: `frontdoor` and `architect_general` build with `has_md=False`, `spec_type=draft-mtp`, `draft_max=4`; `worker_general` still builds with `-md /mnt/raid0/llm/models/gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf`.
- Validation: `uv run pytest -q tests/unit/test_build_server_command_helpers.py tests/unit/test_orchestrator_stack_reload.py` (`79 passed`); focused Ruff safety checks; `python3 -m py_compile`; `git diff --check`.

Applied live in a controlled quiet window later on 2026-07-03; see the reload section below.

## Pre-reload live baseline — 2026-07-03

Durable before snapshot landed in `epyc-orchestrator` commit `a8a94563`:

- `orchestration/reports/md_self_draft_preflight_20260703T140312Z.{json,md}`
- `orchestration/reports/md_self_draft_preflight_20260703T140312Z_affinity.json`

The report counts unique live PIDs (state aliases are recorded separately):

- `11` live spec processes.
- `6` same-file `-md` processes still live: `5` frontdoor/Qwen3.6 instances plus `1` architect/Qwen3.5 instance.
- `5` Gemma worker processes correctly still use a separate assistant-head `-md`.

Smallest deployment target was `orchestrator_stack.py reload frontdoor`; the actual reload window also refreshed the four Qwen3.6 quarter replicas and `architect_general`, because those were the remaining same-file CPU self-draft PIDs.

## Live reload / after snapshot — 2026-07-03

Durable after snapshot landed in `epyc-orchestrator` report artifacts:

- `orchestration/reports/md_self_draft_after_reload_20260703T142152Z.{json,md}`
- `orchestration/reports/md_self_draft_after_reload_20260703T142152Z_affinity.json`

Reload sequence:

- AutoPilot was paused, then its stale pre-pause planner/controller process tree was terminated after SIGTERM failed; SIGKILL verification confirmed the PIDs were gone. This created one `AUTOPILOT_KILLED` placeholder at trial `1084`.
- Reloaded `frontdoor` (`8070`) and `architect_general` (`8083`) through `orchestrator_stack.py reload`.
- The launcher reload path only targets the canonical role port, so the stale Qwen3.6 quarter PIDs on `8080/8180/8280/8380` were stopped by verified PID kill and restarted through `orchestrator_stack.py start --only frontdoor --numa-mode quarter --no-compile-registry --skip-host-prereqs --skip-stack-change-gate`.
- Reloaded the orchestrator API while AutoPilot was still stopped to activate pending backend/dashboard changes.
- Restarted AutoPilot with the required W4/W6/hints contract: `--max-trials 2000`, `AUTOPILOT_SEQ_VERDICT=1`, W6 audit flags, `AUTOPILOT_PLANNER_TIMEOUT=600`, `AUTOPILOT_PLANNER_HINTS=1`, and `AUTOPILOT_STEPPING_STONES=1`. New live process entered trial `1085`; phase health was current-code clean with no blockers.

After snapshot counts:

- `11` live spec processes.
- `0` same-file `-md` processes.
- `6` embedded self-draft Qwen processes with `--spec-type draft-mtp` and no `-md`: `5` frontdoor/Qwen3.6 instances plus `1` architect/Qwen3.5 instance.
- `5` Gemma worker processes still correctly use a separate assistant-head `-md`.

Smoke checks:

- `orchestrator_stack.py status` reported affected processes healthy/attestation `ok`.
- `dashboard/api/health` reported `status=ok`.
- Short completions on `8070` and `8083` both returned draft activity (`draft_n=18`, `draft_n_accepted=10`), confirming embedded NEXTN remains active without `-md`.

## Post-reload measurement update — 2026-07-03

Generated a fresh live acceptance report after AutoPilot resumed:

- `epyc-orchestrator/orchestration/reports/mtp_acceptance_report_20260703T145617Z.{json,md}`
- Failed MTP roles: none.
- Aggregate token acceptance: `0.8204` (`132795/161871`), including Gemma worker traffic.
- Affected Qwen roles with evidence:
  - `frontdoor`: token alpha `0.6188` (`5138/8303`), draft alpha `0.8281`; evidence on `8070` and `8280`. The other quarter replicas had no post-reload traffic yet, so this is activation evidence, not full per-replica coverage.
  - `architect_general`: token alpha `0.5556` (`10/18`), draft alpha `0.6000`; very small sample from one post-reload request.

Resident-memory delta was measured from the durable before/after process snapshots:

- `frontdoor` Qwen replicas: RSS `-197606.3 MiB`, PSS `-17407.4 MiB`.
- `architect_general`: RSS `-78540.4 MiB`, PSS `-3915.3 MiB`.
- Affected Qwen total: RSS `-276146.7 MiB` (~`269.7 GiB`), PSS `-21322.7 MiB` (~`20.8 GiB`).
- Gemma separate-draft control stayed flat: RSS `+216.8 MiB`, PSS `+217.0 MiB`.

Interpretation: the launch fix is live, embedded NEXTN remains active without `-md`, and the duplicate same-file mapping was materially reduced. The PSS delta is the better host-pressure estimate; the larger RSS delta mostly captures duplicate mappings counted per process. A decision-grade throughput speedup ratio was still open at this point because the pre-fix same-file logs were not preserved as a matched workload; the later quiet-window A/B below closes that tail as mixed/negative for CPU throughput.

## Verification-tail harness — 2026-07-03

Prepared the remaining quiet-window A/B as an executable CPU-only harness in `epyc-orchestrator`:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/benchmark/md_self_draft_ab.py
```

The harness:

- launches a throwaway local `llama-server` on port `18070` by default;
- runs the same `/completion` prompt against two arms: `same_file_md` (`-md <same GGUF>`) and `embedded_self_draft` (no `-md`);
- refuses to run while AutoPilot appears active unless `--skip-autopilot-idle-check` is passed for an intentional measured window;
- writes `orchestration/reports/md_self_draft_ab_<timestamp>/summary.{json,md}` plus per-arm logs;
- reports median/mean decode t/s, RSS/PSS samples, and parsed draft-acceptance lines.

Dry-run validation:

```bash
uv run python scripts/benchmark/md_self_draft_ab.py \
  --dry-run \
  --output-dir orchestration/reports/md_self_draft_ab_dryrun_20260703
```

Confirmed the two generated commands differ by the redundant same-file `-md` flag only. Focused unit coverage lives in `tests/unit/test_md_self_draft_ab.py`.

## Residual launcher hygiene — 2026-07-03

After operator clarification that this CPU/RAM lane owns the MI210 session's doc-only handoff, re-grepped adjacent launch surfaces. The production `orchestrator_stack.py` path was already fixed and live, but the legacy per-inference `LlamaCppBackend._build_command()` in `src/inference/model_server.py` still unconditionally emitted `-md` for a returned draft role.

`epyc-orchestrator` now applies the same realpath guard in that legacy backend: if `draft.model.full_path` resolves to the same file as `role_config.model.full_path`, it omits `-md`; separate draft heads still keep `-md`. This is not a production reload requirement because the live stack uses `scripts/server/orchestrator_stack.py`, not the legacy subprocess backend. Validation: GitNexus impact for `LlamaCppBackend` was LOW; Ruff and py_compile passed; focused model-server tests passed (`57` then `118` tests).

## Post-reboot audit — 2026-07-03

After the host reboot and stack restart, the CPU/RAM lane re-audited live `llama-server` command lines. Result: `same_file_md_count=0` across all current spec processes. The five Qwen3.6 frontdoor processes (`8070`, `8080`, `8180`, `8280`, `8380`) and the Qwen3.5 architect process (`8083`) run `--spec-type draft-mtp --spec-draft-n-max 4` with no `-md`; the five Gemma worker processes (`8072`, `8082`, `8182`, `8282`, `8382`) still correctly keep `-md /mnt/raid0/llm/models/gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf` because that is a separate assistant-head draft.

This confirmed the reboot did not regress the production launch fix. At this point the remaining open item was the quiet-window matched decode A/B via `scripts/benchmark/md_self_draft_ab.py`; the following section records that closeout.

## Quiet-window matched decode A/B — 2026-07-03

AutoPilot was paused and allowed to finish trial `1092` cleanly before measurement; it entered the paused loop at trial `1093`. The orchestrator API was also reloaded in the same quiet window to activate already-committed dashboard/backend changes: new API PID `1952555`, `dashboard/api/health` returned `status=ok`, and `orchestrator_stack.py status` showed the fleet healthy.

Two throwaway Qwen3.6-35B CPU `/completion` A/B runs were recorded in `epyc-orchestrator` commit `e846b165`:

- `orchestration/reports/md_self_draft_ab_20260703T180027Z/summary.{json,md}`: default mmap, 3 measured reps after 1 warmup. Result `embedded_self_draft_slower`; embedded/no-`-md` median `37.590` t/s vs same-file `-md` median `39.216` t/s, ratio `0.9586`. Embedded saved `4372.96` MiB load PSS. Draft acceptance was identical across arms: token alpha `0.7910`.
- `orchestration/reports/md_self_draft_ab_20260703T180149Z/summary.{json,md}`: production-shaped `--mlock`, 8 measured reps after 2 warmups. Result `embedded_self_draft_slower`; embedded/no-`-md` median `34.815` t/s vs same-file `-md` median `36.194` t/s, ratio `0.9619`. Embedded saved `4368.31` MiB load PSS. Draft acceptance was identical across arms: token alpha `0.7944`.

Conclusion: CPU duplicate-load hygiene and memory-pressure reduction are real, but CPU decode throughput did **not** improve in this harness. Do not claim a CPU speedup from dropping same-file `-md`. Keep Gemma's separate assistant-head `-md` untouched. If future production eval-fanout telemetry shows a sustained Qwen throughput regression from the no-`-md` path, the rollback is narrow: restore same-file `-md` only for the affected embedded-NEXTN CPU role and remeasure memory/throughput together.

---

## Steps (checklist)

- [x] `grep` `epyc-orchestrator/scripts/server/` (+ `model_registry`) for `-md` / `--model-draft` / `spec_draft` / `draft` emission on NEXTN roles.
- [x] Identify the lever (per-role registry field vs launch-map branch).
- [x] Make `-md` conditional: drop it when `realpath(-md) == realpath(-m)`; keep it otherwise.
- [x] Confirm gemma worker `:8072` still keeps its separate-head `-md`.
- [x] Capture durable pre-reload baseline of same-file vs separate-draft live processes.
- [x] Start with **frontdoor `:8070`** only, in a quiet window; reload via `orchestrator_stack.py`.
- [x] Gate 1: pipeline-green. Gate 2: role starts. Gate 3: `ps` shows no `-md <same file>`.
- [x] Repeat for architect `:8083` and the remaining Qwen3.6 frontdoor quarter replicas.
- [x] Record reload results in `progress/`; if all green, ask operator before touching `master-handoff-index.md`.
- [x] Measure: representative post-reload MTP acceptance and resident-RAM delta via live AutoPilot/eval traffic and durable before/after process snapshots.
- [x] Guard adjacent legacy `LlamaCppBackend._build_command()` against re-emitting same-file `-md`; keep separate draft heads unchanged.
- [x] Controlled same-workload decode speedup A/B: run `scripts/benchmark/md_self_draft_ab.py` in a quiet window; compare same-file `-md` versus embedded no-`-md` on the throwaway Qwen server artifact.
- [x] No rollback triggered by smoke checks or post-reload acceptance evidence.
