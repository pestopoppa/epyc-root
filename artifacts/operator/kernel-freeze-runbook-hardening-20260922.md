# Kernel-freeze runbook hardening — post-mortem of the v10 promotion (2026-09-21/22)

**Status: PROPOSAL. Nothing applied, nothing committed.**
Patch: `artifacts/operator/kernel-freeze-runbook-hardening-20260922.patch` — `git apply --check` PASSES.

**Prerequisite.** The patch is cut against the **working-tree** runbook, i.e. it assumes
`artifacts/operator/kernel-freeze-runbook-step6-fix-20260921.patch` is already applied (it is, as an
uncommitted modification: `git status` shows ` M docs/reference/kernel-freeze-runbook.md`, +63/-3).
Apply against a clean HEAD and it will reject.

Everything below was verified on disk on 2026-09-22 unless marked otherwise. Three items in the
operator's reconstruction are **corrected**, one is **refuted**, and two **new live defects** were
found that nobody has recorded.

---

## A. Verified failure table

| # | What the runbook said | What actually happened | Cost | Text change that prevents it |
|---|---|---|---|---|
| 1 | Pre-2026-09-21 step 6 was two `ln -sfn` lines with **no** RPATH requirement and no `readelf` (see the removed lines in `artifacts/operator/kernel-freeze-runbook-step6-fix-20260921.patch`). | **VERIFIED.** `readelf -d /mnt/raid0/llm/tmp/build-fold-ef81196d5/bin/llama-server` → `RUNPATH = /mnt/raid0/llm/tmp/build-fold-ef81196d5/bin:/opt/rocm/lib:`. Production carries `$ORIGIN` (cpu) / `$ORIGIN:/opt/rocm/lib` (gpu). Promoting it would have made `production/gpu` load ggml out of `tmp`. `patchelf` is not installed → full rebuild, not a repair. | A full rebuild of both backends. | Already partly fixed by step 6a. **Still insufficient**: 6a sits at *promotion* time, after the bench spend, and `-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON` is **configure-time and cannot be retrofitted**. Patch moves it to **PRE-FLIGHT P1**, with the "patchelf is not installed" consequence spelled out. |
| 2 | `docs/reference/kernel-freeze-runbook.md` step 6 (pre-fix): "archive `<old build dir>`". | **VERIFIED.** `/mnt/raid0/llm/kernels/STORE-STATE.md` §1: "`archive/` is empty. It has never been written to… step 6 has never executed." `production/{cpu,gpu}` pointed at `llama.cpp/build{,-hip}/bin` — accretive artifact dirs holding `libllama.so.0.0.1012{1..5}` side by side, not CMake trees. Anchors were first created 2026-09-21 19:42 (`archive/{cpu,gpu}-20260810-0db32c06e`). | Seven weeks with **no rollback path at all**; build 10196 (`58c345093`) lost from `tmp`. | New **step 0 rollback drill** in the patch: the anchor must *exist*, pass `sha256sum -c`, show `$ORIGIN`, pass `verify_ggml_linkage.sh` under `env -u LD_LIBRARY_PATH`, and **have its `--version` executed and recorded**, before anything moves. |
| 3 | `kernel-freeze-runbook.md:28-29`: "the `cpu` backend serves 10 roles across 5 distinct models; `gpu`, `stt` and `tts` serve none". | **CORRECTED — worse than you said.** Ground truth from the compiled priors: **gpu = 4 roles / 2 models** (`architect_general`, `coder_escalation`, `vision_escalation`, `worker_vision`; Qwen3.8-27B-Q8_0 and Qwen3-VL-30B-A3B-Q4_K_M) and **cpu = 12 roles / 6 models**, not 10/5. **But `kernel_freeze_scope.py --backend gpu` today returns 0 roles / 0 models** — see Gate gap G1. So the mandated tool is *also* wrong, in the same direction as the stale prose. | Trusting either would skip the entire GPU gate. The VL-30B cell is the one that caught the −30%. | Patch **deletes the counts**, forbids quoting a scope from the page, mandates the command per backend, **and** adds a reconcile-against-priors cross-check with an explicit "if they disagree, the tool is wrong and the freeze is not scoped". |
| 4 | Nothing in the runbook required a complete target set or a binary-set comparison. | **VERIFIED, with your number confirmed on one counting and refined on another.** `builds/cpu-20260921-ef81196d5/bin` and `…-d0d70c5fe/bin`: 22 files, **2 executables** (`llama-server`, `llama-bench`). `builds/cpu-20260810-0db32c06e/bin` (archived v9): **92 executables** (48 of them `llama-*`). So "2 vs 92" is right on total executables; a subagent's "2 vs 48" counts only `llama-*`. `executor.py:77-83,869` resolves `llama-completion`/`llama-speculative`/`llama-lookup`/`llama-cli`/`llama-mtmd-cli` → those roles `FileNotFoundError` at launch. Rebuilt in full at 20:03; `verify_kernel_store.sh` companion-tools block written 20:16; symlinks repointed 20:17. | A rollback plus a full rebuild, late in the day. | **PRE-FLIGHT P2** (no bare `--target` pair) and **P3** (mechanical `comm -23` name diff vs the incumbent, empty or justified in the record). |
| 5 | The runbook has never mentioned launcher path resolution at all. | **VERIFIED**, and the code says so in its own words — `epyc-orchestrator/scripts/lib/executor_paths.py:63-78`: "that left executor.py launching the OLD kernel (the stale path still exists, so it resolves and serves silently) while stack_priors, orchestrator_stack and env.sh had all followed the promotion. Split-brain kernel resolution, detectable only by reading argv of a running server." Fixed by overriding `base_dir` with `kernel_paths.backend_dir("cpu")`. **Correction: `executor_paths.py` is not new** — tracked since commit `84273c4c`, modified today (+33/-5). **Residual, unfixed:** `executor.py:77` and `:90` still hard-code `/mnt/raid0/llm/llama.cpp/build/bin` on the registry-load-failure path. | Part of the fleet served v9 after the cutover, silently. | **Step 8c** literal sweep, with `executor.py:77,90` named as a standing offender, plus the root-cause note at `kernel_paths.py:83` (`path.resolve()` dereferences the symlink). |
| 6 | `kernel-freeze-runbook.md:124-125`: "Neither registry changes. No launcher changes." | **The claim is FALSE — VERIFIED and quantified.** The cutover touched **20 files in `epyc-orchestrator`, +612/-109** (`stack_priors.yaml`, `model_registry.yaml`, `gpu_shadow_lane_tenancy.yaml`, `env.sh`, `executor_paths.py`, `orchestrator_stack.py`, `gpu_shadow_lane.py`, `stack_paths.py`, `src/registry/stack_priors.py`, `test_stack_priors_compiler.py`, …) plus 3 in `epyc-root`. **But your stated mechanism is REFUTED:** `orchestrator_stack.py start` is *not* refused. All 9 `source_artifacts` pins in the regenerated `stack_priors.yaml:55-75` currently **hash-match** (re-hashed on disk), and `stack_change_guard.py:74-76` is a **commit-time** gate — no start path consults it (`orchestrator_stack.py`, `stack_commands.py`, `src/registry/stack_priors.py` contain no reference). The real failure mode is **silent**: a skipped regeneration fails at commit, not at launch. | Hours of half-applied stack; the belief that a promotion is config-free is what caused it. | Patch **replaces** the false sentence with the measured file count, the `kernel_paths.py:83` root cause, and the split-brain description; **step 8a/8b** make regeneration + pin refresh mandatory and state plainly that the gate is commit-time only. |
| 7 | `kernel-freeze-runbook.md:48-49`: "Speculative decoding must not change output." | **VERIFIED as unsatisfiable.** `handoffs/active/dflash2-block-drafter-experimental-build.md:292-315`: batched speculative verification alone diverges at near-ties (upstream #27407, reproduces with `draft-simple`); frozen v9 carries EPYC-local `a6b4b5263` (`ggml-cuda/mmvq.cu:341-344`) deliberately routing Q8_0 differently at `ne11>=2`, self-described "numerically-valid (not bit-exact)", taken for +17.4%; the same `N==1`/`N>1` split exists on both CPU paths, so "batch invariance is not a property any of our three compute planes holds". The **actual** v9 gate was `gates.quality` = MMLU-Pro (n=200) + GPQA (n=195) vs the v8 incumbent, plus a narrow `gates.dspark_q8_parity` at `-np 1`, 18 drafted / 9 accepted. v10 used the same shape (`gates.cpu_quality`); **no bitwise gate appears in the v10 artifact at all.** | A clause every promotion must argue past = no clause. | Patch rewrites step 4 to the **quality-eval form**: MMLU-Pro/GPQA vs incumbent per gated role with per-arm sha256, one explicitly-scoped `np1` token-parity spot check, coherence at production prompt length. "Bitwise divergence is reportable, never blocking." |
| 8 | The runbook never mentions test fallout. | **VERIFIED.** `tests/unit/test_stack_priors_compiler.py` `@@ -649,14 +649,25 @@`: removed `assert runtime["binary_path"].endswith("/llama.cpp/build/bin/llama-server")`; added `assert runtime["binary_path"] == str(_store_server_binary("cpu"))`. | A red suite mid-cutover. | **Step 8d**, with the rule that matters: fix by asserting **store resolution**, never by hard-coding the new path, or the next promotion breaks it again. |
| 9 | Step 6b (post-fix) says "copy, never move — the bench evidence still cites the build path". | **VERIFIED, and the step-6 fix is self-contradictory here.** `check_evidence_durability.py:115-124` (present only on worktrees, e.g. `/workspace/worktrees/audit-build-recovery-7c59fa1/scripts/validate/`): `EPHEMERAL_ROOTS = ("/mnt/raid0/llm/tmp", "/tmp", "/var/tmp", "/dev/shm", "/run/user")`, with "this tuple is the one thing in the file that must never acquire an exemption". Evidence cited from a `tmp` build path is inadmissible **even when the binary survives**. Build 10196 was lost outright. | Evidence produced at cost that cannot be cited. | **PRE-FLIGHT P4**: build directly under `kernels/builds/<B>-<YYYYMMDD>-<short-sha>/`. This makes step 6b's "the evidence cites the build path" rationale moot rather than contradictory. |

### Could not verify / corrections you should know about

* **No written record of the cutover exists.** There is no `progress/2026-09/2026-09-22.md`. `progress/2026-09/2026-09-21.md:225` still says "**Runbook steps 6-7 (symlink promotion + re-verify) are NOT executed.**" So do `artifacts/operator/v10-qualification-20260921-ffc1bac82.json` (`not_executed`) and `STORE-STATE.md`. **All three are now false**: `production/{cpu,gpu}` were repointed at 20:17 on 2026-09-21 and serve `10303 (ffc1bac82)`. No ratification receipt, no progress entry, no authorization record. → step 8g.
* **The whole promotion is uncommitted.** `epyc-root` HEAD `5ac3f9a0`; `epyc-orchestrator` HEAD `2a609f5c` (2026-09-18). `verify_kernel_store.sh` and the v10 qualification JSON are untracked; the runbook fix, `env.sh`, `session_init.sh` and 20 orchestrator files are unstaged. A `git clean` or a fresh checkout loses the promotion's entire software half while the symlinks stay moved.
* **"the gate passed it" (your item 4) is imprecise.** `verify_kernel_store.sh` has mtime Sep 21 **20:16** — one minute *before* the repoint, and after the 20:03 full rebuild. It is untracked with zero git history, so there is no way to prove what an earlier version checked. The in-file rationale for the companion-tools block ("observed 2026-09-21") supports your account, but it is **PARTIAL**, not verified: the file may never have existed in a llama-server-only form on disk.
* **The −30% was found and fixed, not accepted.** `v10-qualification…json` `defects_found_and_fixed[1]`: `ae6031aaa` introduced a CPU-only fused MoE op (`GGML_OP_MOE_TOPK_NORM`) with no CUDA/HIP implementation, so the scheduler split the graph at every MoE layer → "−30% on every MoE model on GPU"; fixed by `ffc1bac82`; `found_by: "git bisect over 89 revisions, llama-bench tg128 oracle"`. `progress/2026-09-21.md:~215`: "**Dense models never build the node** — which is exactly why the Qwen3.8-27B cell passed and this sat in the champion for three weeks. A headline-only GPU comparison would have shipped it." A second defect, `d0d70c5fe`, fixed a gemma MTP drafter load failure that made "4 of 8 gated CPU roles unservable".
* **Qualification artifact carries an unseparated confound**, honestly recorded: the host BIOS bundle (memory interleave ON, 4800→5600 MT/s) changed in the same window — `"attribution": "BUNDLE - no arm separates the two items"`. Not a runbook defect, but it means the v10 speed ratios are not clean kernel attribution.

---

## B. The patch

`artifacts/operator/kernel-freeze-runbook-hardening-20260922.patch` (309 lines). Adds:

1. **Scope section rewrite** — deletes the stale counts, forbids quoting a scope from the page,
   mandates `kernel_freeze_scope.py` per backend, and adds the reconcile-against-priors cross-check
   because the tool is itself broken by promotion (G1).
2. **`## Pre-flight`** — P1 relocatability (configure-time, `patchelf` absent), P2 complete target
   set, P3 mechanical binary-set parity vs the incumbent, P4 durable build location, P5 anchor.
3. **Step 0 rollback drill** — anchor exists, `sha256sum -c`, `$ORIGIN`, standalone linkage, and
   `--version` *executed* and recorded.
4. **Step 4 rewritten** to the quality-eval criterion.
5. **Step 6d** gains the anchor precondition; the "Neither registry changes" paragraph is replaced
   with the measured blast radius and the `kernel_paths.py:83` root cause.
6. **Step 7** gains `verify_kernel_store.sh`; new **step 8** post-promotion: 8a regenerate derived
   artifacts, 8b refresh `source_artifacts` pins (commit-time gate, not start-time), 8c literal
   sweep with named offenders, 8d test fallout, 8e dashboard `PRODUCTION_STABLE_LINKS`, 8f re-pin
   `verify_llama_cpp.sh` + `CLAUDE.md` + production branch, 8g write the receipt.
7. **Gate section** — the one-`ln -sfn` rollback claim corrected to "repoint + re-run step 8", plus
   the restart requirement (a running server holds its own argv).

---

## C. Gate gaps — checks a human had to notice

| ID | Unguarded check | Evidence it is unguarded | Should be owned by |
|---|---|---|---|
| **G1** | **The scope tool mis-attributes backends after a promotion.** `kernel_freeze_scope.py:35-44` classifies by `"build-hip" in binary_path`; the v10 store paths carry no such marker, so all 4 GPU roles fall through to `cpu`. Tool now reports gpu=0. File is unmodified — it was not updated with the promotion. **Live defect, nobody has recorded it.** | Ran read-only: `--backend gpu` → 0 roles / 0 models; priors carry 4 roles at `kernels/builds/gpu-20260921-ffc1bac82/bin`. | `kernel_freeze_scope.py` — resolve via `kernel_paths.backend_dir()`, not a substring. A unit test asserting non-empty gpu scope while any gpu role exists. |
| **G2** | **Nothing compares the promoted binary SET against the archived one.** `verify_kernel_store.sh` tests a hardcoded 5-name companion list; a build missing the 6th…40th tool passes. **Live: v10 ships 91 executables vs v9's 92** — `test-gguf-model-data` and `test-quant-type-selection` dropped, `llama-rowexact` added. Unflagged. | `comm -23` of `builds/cpu-20260810-0db32c06e/bin` vs `builds/cpu-20260921-ffc1bac82/bin`. | `verify_kernel_store.sh` — diff `production/<B>` against the newest `archive/<B>-*`; FAIL on any name present there and absent here, unless a `PROVENANCE.md` waiver names it. |
| **G3** | **Nothing asserts the promoted kernel's `--version` matches the attested commit.** Deliberate: the verifier's header says "It says nothing about which commit built the target" and it never execs the binary. Result: `verify_llama_cpp.sh:14-18` attests v9 against the untouched *source tree* and passes, while the store serves `10303 (ffc1bac82)` — the two session gates disagree about what production is. The promoted commit is on `ak/champion/llama-cpp-0db32c06e3e5`, not a `production-consolidated-v10` branch, so no branch gate covers it. | `production/cpu/llama-server --version` → `10303 (ffc1bac82)`; `verify_llama_cpp.sh` constants unchanged. | A new identity check in `verify_kernel_store.sh`, or a third verifier: parse `<build-dir>/PROVENANCE.md`, exec `--version`, compare, FAIL on mismatch. Plus a promotion-time edit to `verify_llama_cpp.sh`'s constants (8f). |
| **G4** | **RUNPATH / `$ORIGIN` is never checked by any script.** No `readelf` anywhere in `verify_kernel_store.sh`. Worse, its linkage check runs with the composed `LD_LIBRARY_PATH` prepended, which **masks** a bad RUNPATH for gpu/stt/tts. The absolute-RUNPATH defect is the documented reason the first candidate was unpromotable. | Grep: zero `readelf` in the verifier. | `verify_kernel_store.sh` — `readelf -d` on the primary binary, FAIL on any absolute path component. |
| **G5** | **`SHA256SUMS` is written but never read.** The runbook tells you to generate it in every build dir; no script verifies it. Also: archived v9 dirs carry `PROVENANCE.md`, the promoted v10 dirs do not. | No `sha256sum` call in the verifier; `ls builds/*-ffc1bac82/` shows `SHA256SUMS` but no `PROVENANCE.md`. | `verify_kernel_store.sh` — `sha256sum -c` on the resolved target and on the newest archive anchor; FAIL on a missing `PROVENANCE.md`. |
| **G6** | **The archive anchor is not a precondition of the repoint.** The verifier's archive section is WARN-only and runs after the fact; there is no assertion linking "`production/<B>` points at X" to "`archive/` contains X's predecessor". | Verifier §archive: reports only. | `verify_kernel_store.sh` — FAIL when `production/<B>` resolves under `builds/` and no `archive/<B>-*` exists. |
| **G7** | **The store verifier is a warning, not a gate, at session start.** `session_init.sh:120-131` prints "⛔ WARNING" and continues; it never exits non-zero. | `git diff scripts/session/session_init.sh`. | `session_init.sh` — make store failure fatal, as `verify_llama_cpp.sh` is. |
| **G8** | **Nothing detects split-brain resolution across consumers.** The v10 split-brain was "detectable only by reading argv of a running server" (the code's own words). ~29 sites still hard-code `llama.cpp/build{-hip}/bin`. | `executor_paths.py:63-78`; `executor.py:77,90`; `gpu_shadow_lane.py:49-50`; `gpu_shadow_lane_tenancy.yaml:47`. | A CI/preflight lint: no source file outside `kernel_paths.py` may contain `llama.cpp/build{,-hip}/bin`. Plus a runtime check comparing every serving process's argv[0] against `backend_dir()`. |
| **G9** | **The two silent `except` fallbacks defeat the store's fail-closed design.** `orchestrator_stack.py:156-167` and `stack_priors.py:1930-1954` swallow `KernelPathError` → CPU-only literal, empty `LD_LIBRARY_PATH`. A dangling `production/gpu` compiles a CPU path instead of failing. Already filed as KBS-4 in `kernel-build-store-durability-20260921.draft.md`, still open. | Cited in `STORE-STATE.md` §7 and the v10 qualification JSON. | `orchestrator_stack.py` / `src/registry/stack_priors.py` — let `KernelPathError` propagate. |
| **G10** | **The dashboard's expectation table is a hardcoded literal, and it is now wrong.** `dashboard/server.py:565-570` still names the 2026-07-31 targets; `matches_expected` is false for cpu and gpu right now. It is also, per `STORE-STATE.md` §7, "the ONLY thing that checks the symlink→target mapping, and it is a dashboard, not a gate". | Read `dashboard/server.py:565-570`, compared against `readlink -f`. | `dashboard/server.py` — derive from `kernel_paths.describe()` instead of a literal; the freeze receipt becomes the expectation source. |
| **G11** | **Derived artifacts pin the dereferenced build dir, so the symlink's entire purpose is defeated.** `kernel_paths.py:83` returns `path.resolve()`. Every promotion *and every rollback* therefore needs a recompile of `stack_priors.yaml`. | `stack_priors.yaml` working-tree diff: `binary_path: …/kernels/builds/cpu-20260921-ffc1bac82/bin/llama-server`, never `…/kernels/production/cpu/…`. | Design decision for the operator: either `backend_dir()` stops resolving (compiled priors carry the stable symlink, rollback returns to one `ln -sfn`), or the runbook permanently owns step 8a. Recommend the former; it is the design the store was built for. |

---

## D. Ordering for the next promotion

Serialisation mechanism is `epyc-orchestrator/scripts/region-lock` (`run --cpu-list … --role bench`
/ `status`; exit 75 = could not acquire). The hard constraints: **a GPU bench voids a concurrent CPU
bench** (pinned GPU host threads degrade the CPU floor ~9x), **a build contends with any bench**, and
the region lock is the only arbiter. Everything that is pure file/graph reading is free.

**Phase 0 — scope and anchor (no lock, fully parallel, minutes).**
`kernel_freeze_scope.py` per backend **plus** the priors cross-check (G1) ‖ step-0 anchor drill on
each backend ‖ record the incumbent's binary-name manifest (`ls -1 $OLD | sort`) ‖ confirm
`check_evidence_durability.py` accepts the intended build root. **Gate: no anchor, no promotion.**

**Phase 1 — build (region lock HELD, exclusive; no bench may run).**
Configure with `-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON`, build **all targets**, directly into
`kernels/builds/<B>-<date>-<sha>/`. CPU and GPU builds are separate artefacts but both are
CPU-bound compiles — serialise them or share one lock window. Generate `SHA256SUMS` and
`PROVENANCE.md` at the end of this phase, not later.

**Phase 2 — pre-flight verification (no lock, parallel, cheap).**
P1 `readelf` ‖ P2/P3 `comm -23` parity diff ‖ 6c standalone linkage under `env -u LD_LIBRARY_PATH` ‖
`--version` vs the attested commit. **Gate: all four before any bench time.** This is the phase the
v10 promotion skipped, and it is the cheapest phase in the whole sequence.

**Phase 3 — benches (region lock HELD; CPU and GPU MUST NOT overlap).**
3a CPU speed cells, all roles in the CPU scope, `n>=3`, production recipes → release lock.
3b GPU speed cells → release lock. Never interleave; an ABA re-measure of one incumbent cell at the
end of each arm is what catches host drift (~3% over hours).
Quality evals (MMLU-Pro/GPQA) are themselves inference and take the lock — run them inside the arm
that owns the backend they gate, not as a separate window.
Only the *analysis* of 3a and 3b is parallel-safe; write the qualification artifact from both.

**Phase 4 — cutover (no lock; human-only trust boundary).**
Stop anything serving the affected backend → `ln -sfn` archive, `ln -sfn` production →
`verify_kernel_store.sh` → `verify_ggml_linkage.sh` against the new target. Serialise strictly; this
is two commands and a proof.

**Phase 5 — post-promotion (partly parallel, but all of it before the session ends).**
Serial first: 8a regenerate derived artifacts → 8b refresh pins → `stack_change_guard.py`.
Then parallel: 8c literal sweep ‖ 8d test suite ‖ 8e dashboard table ‖ 8f `verify_llama_cpp.sh`
constants + `CLAUDE.md` + production branch ‖ 8g receipt and progress entry.
**Then commit both repos.** Phase 5 is not optional and not deferrable: between phase 4 and the end
of phase 5 the fleet is split-brain, and the only symptom is a server quietly serving the old kernel.

**Immediate follow-ups, independent of the next promotion** (all are live now, all are "find a gap →
close it", not open items): G1 classifier fix; G3/G10 the stale `verify_llama_cpp.sh` pins,
`CLAUDE.md` freeze block and dashboard table; G8 `executor.py:77,90`; and the missing receipt +
progress entry for a cutover that three artifacts still claim did not happen.
