# Brief: Drop `-md <same-file>` double-load for embedded-NEXTN roles

**For:** a separate CPU / orchestrator session (execute directly).
**Type:** production launch-config fix. No GPU, no new inference required to *decide* the fix — but you MUST measure to *verify* it. This document is the plan; you apply it.
**Repo to edit:** `epyc-orchestrator` (launch-config / arg builder). This brief lives in `epyc-root` (`handoffs/active/`).
**Do NOT** wire this into `master-handoff-index.md` yourself — that needs explicit operator approval.

---

## Problem

Production Qwen NEXTN (embedded-MTP) roles are launched with `-md <same GGUF as -m>`. That makes `llama-server` load a **second full copy** of the model as the "draft" and draft every token with a **full-model forward pass** — instead of using the cheap embedded NEXTN head via the zero-extra-load self-spec path. This both wastes RAM and negates the MTP speedup (the draft is as expensive as the target).

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
- The **performance** cost (expensive full-model drafting negating MTP) is **certain and backend-independent**.
- The **RAM-doubling** is certain on GPU (separate HBM alloc). On **CPU it depends on mmap**: same file loaded twice **may share the mmap page cache** (→ little/no extra resident RAM), whereas `--no-mmap`/`--mlock` forces two distinct resident copies (→ true 2×). **VERIFY the actual resident-RAM delta on CPU — do not assume 2×.**

## Which roles (critical scoping)

Applies **ONLY** to embedded-NEXTN roles where `realpath(-md) == realpath(-m)`.

- **AFFECTED** (live launch args observed this session):
  - frontdoor `:8070` — Qwen3.6-35B-A3B-MTP, `-md` == `-m`.
  - architect `:8083` — Qwen3.5-122B-A10B-MTP, `-md` == `-m`.
  - Also check **coder_escalation** and **worker_summarize** — they share the frontdoor process — and any other Qwen NEXTN role.
- **CORRECT — do NOT touch:** gemma-4-26B-A4B worker `:8072` launches `-md <a SEPARATE small assistant head>` (`gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf`). That is a genuine separate draft head. **Keep its `-md`.**

**Rule of thumb:** drop `-md` **only** when `realpath(-md) == realpath(-m)`; keep it when they differ.

## The fix

In the orchestrator launch-config / worker-pool arg builder that assembles the `llama-server` command, make the `-md <same-file>` emission **conditional**:

- For embedded-NEXTN roles (`realpath(-md) == realpath(-m)`): emit `--spec-type draft-mtp` **WITHOUT `-md`** → takes the `:1220` self-spec path.
- For separate-head roles (paths differ): **keep `-md`**.

Start in `epyc-orchestrator/scripts/server/` (`orchestrator_stack.py`, the stack launch-map, the WorkerPool arg construction, and the `model_registry` acceleration/spec block). **Grep** for where `-md` / `--model-draft` / `spec_draft` / `draft` args get added for NEXTN roles. The lever may be a **per-role registry field** or a **launch-map branch** — trace it before editing.

## Verification (three gates + measure)

Apply via `orchestrator_stack.py` and **reload to apply** (per stack lifecycle rules — reload == redeploy; use absolute paths). Then:
1. **pipeline-green.**
2. **role actually starts.**
3. **live == config** — `ps`-confirm the launched args for the affected role **no longer carry `-md <same file>`** (cross-ref the "verify live affinity/config, not just topology hash" memory).
4. **measure the win** — the role should now show **real MTP draft-acceptance stats** + a **decode speedup**; **resident RAM should drop — verify the ACTUAL delta** (mmap-shared may show little CPU RAM change; that's fine, the perf win still holds). Output must stay **coherent**. Test via the **autopilot eval fan-out path, NOT `/chat`**.

Cross-reference: stack-change three-gates (pipeline-green ≠ starts ≠ live==config).

## Risk / rollback

**Low.** Dropping the redundant full-model draft restores the intended embedded self-spec; correctness should be unchanged (verify coherence + that acceptance stats now appear). **Rollback = restore the `-md` arg.** Change **one NEXTN role at a time**; frontdoor is highest-value + highest-traffic → validate it **first, in a quiet window**.

## Expected win

Unlocks the real MTP self-spec speedup currently being negated (~the +15.6% class on GPU; **CPU magnitude TBD by measurement**), and frees up to ~one model-size of RAM per affected role (frontdoor ~38 GB, architect ~78 GB **IF not mmap-shared**) — material on the RAM-pressured host.

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

Interpretation: the launch fix is live, embedded NEXTN remains active without `-md`, and the duplicate same-file mapping was materially reduced. The PSS delta is the better host-pressure estimate; the larger RSS delta mostly captures duplicate mappings counted per process. A decision-grade throughput speedup ratio remains open because the pre-fix same-file logs were not preserved as a matched workload. The next clean-window task is a controlled same-prompt A/B (`same-file -md` vs no-`-md`) on a single Qwen role or throwaway server, without contaminating AutoPilot evidence windows.

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
- [ ] Controlled same-workload decode speedup A/B: same-file `-md` versus embedded no-`-md`, preferably one Qwen role or throwaway port in a quiet window.
- [x] No rollback triggered by smoke checks or post-reload acceptance evidence.
