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

---

## Steps (checklist)

- [ ] `grep` `epyc-orchestrator/scripts/server/` (+ `model_registry`) for `-md` / `--model-draft` / `spec_draft` / `draft` emission on NEXTN roles.
- [ ] Identify the lever (per-role registry field vs launch-map branch).
- [ ] Make `-md` conditional: drop it when `realpath(-md) == realpath(-m)`; keep it otherwise.
- [ ] Confirm gemma worker `:8072` still keeps its separate-head `-md`.
- [ ] Start with **frontdoor `:8070`** only, in a quiet window; reload via `orchestrator_stack.py`.
- [ ] Gate 1: pipeline-green. Gate 2: role starts. Gate 3: `ps` shows no `-md <same file>`.
- [ ] Measure: MTP acceptance stats present, decode speedup, resident-RAM delta (verify actual), output coherent — via autopilot eval fan-out.
- [ ] If good, repeat one-at-a-time for architect `:8083` and any other affected Qwen NEXTN role (coder_escalation / worker_summarize).
- [ ] Record results in `progress/`; if all green, ask operator before touching `master-handoff-index.md`.
- [ ] Rollback if regression: restore `-md` and reload.
