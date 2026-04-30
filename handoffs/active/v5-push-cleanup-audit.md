# v5 Kernel Push — Cleanup Audit

**Status**: ACTIVE — pending execution
**Priority**: HIGH (gates `production-consolidated-v5` branch creation)
**Created**: 2026-04-30
**Owner**: TBD (single dedicated session)
**Parent indexes**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Replaces / does not replace**: NOT a replacement for [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md). That handoff covers the v4 push (status: COMPLETE). It is preserved as historical record. **Do not modify it.** This handoff is a fresh document for v5.

**Source documents** (read these first):
- [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md) — env-flag inventory + cherry-pick scope + per-arch deployment matrix
- [`model-registry-v5-deployment-draft.yaml`](model-registry-v5-deployment-draft.yaml) — staging file for per-role binary_path + env (becomes the model_registry update post-v5)

**Triggering work**: this audit exists because user said during 2026-04-30 /wrap-up: *"shall we review what we plan to push into production to make sure code is clean, minimal and refactored? I don't want a sloppy mess."*

---

## 1. Why this audit exists

The v4 push (handled by `llama-cpp-kernel-push-rebase.md`) was a clean rebase against a relatively small patch set: 22 patches + 1 build fix, mostly KV cache + paged attention + server slot management + OpenMP + a few model variants. v4 finalized 2026-04-23 with a working sanity smoke across 5 models.

v5 has a much larger and more heterogeneous scope:

- **CPU1 stack** (CCD threadpool partitioning + barrier + work-distribution + DEPRECATED `NUMA_WEIGHTS`)
- **CPU2 stack** (AVX-512BW Q8_0 8x8 ukernel + AVX-512BW Q6_K 8x8 ukernel + auto-mbind kill-switch)
- **CPU15 EP family** (7 commits — inter-process Expert Parallelism, master + drone + shard + control plane)
- **Slot-promotion dispatcher v1** (`--spec-numa-quarters` K-parallel verify, +386 LOC, gate not met)
- **CPU4 op-coalesced barriers** (`GGML_BARRIER_COALESCE`, +109 LOC, gate not met but neutral)
- **CPU22 work-stealing prototype** (failed gate; decision needed: strip vs keep-gated)
- **MoE-Spec verification budget** (`--moe-spec-budget`, REAP=40 deployable)
- **Toolchain change** — clang-20 + libomp + `-march=znver5` + LLVM PGO universal binary; per-role BOLT-libggml binary for Coder-30B

In addition to the live work, the experimental tree carries ~340 LOC of dead-by-default code from 4 falsified mechanisms:
- `GGML_NUMA_WEIGHTS` (CPU1 Phase 1.3 NUMA-aware weight placement — DEPRECATED unstable)
- `GGML_RMS_NORM_PARALLEL` (parallel inner-axis reduction in rms_norm — net-negative −9% at 96t)
- `GGML_GDN_K_PER_HEAD` (gated_delta_net K-axis sub-chunking — no current effect)
- `GGML_EXPERT_CCD_SHARDING` (CPU15 Phase 1 intra-process expert sharding — superseded by Phase 3.2)

Without a deliberate strip/refactor pass, all this dead code ships into production along with the live work — known footguns gated only by env-default-off, plus uncached `getenv` calls in at least one repack path, plus unconditional debug `fprintf` lines that fire on every model load, plus 6 instances of bare `16` block-tile-size constants without a single comment explaining the choice.

The audit's goal: produce a **clean, minimal, refactored** v5 branch where every line is justified.

---

## 2. Cleanliness assessment (current state of the tree)

Findings from a 2026-04-30 exploration of `/mnt/raid0/llm/llama.cpp-experimental` HEAD `9f6191581` (branch `feature/cpu-ep-inter-process`). All file:line references are at this HEAD; verify before acting.

### 2.1 Commit-baseline mismatch (BLOCKER)

The cherry-pick hashes listed in `cpu-kernel-env-flags-inventory.md` "Definitely cherry-pick" section do NOT all appear in the current branch's `git log`:

- ✓ `9f6191581` (CPU4) — present
- ✓ `d45126db5` (slot-promotion dispatcher v1) — present
- ✗ 12 CPU1 commits (`a64d27dee`, `218325a14`, `61b00eb53`, `4f7f8bac4`, `04abecd13`, `d922314cc`, `0ade7bd4d`, `69b4c3fa4`, `9407a167e`, `315f891b0`, `c24a6c801`, `acb1bbdd7`) — NOT FOUND
- ✗ CPU2 ukernel `1d18efce3` — NOT FOUND
- ✗ CPU15 EP family range `aa6476ab0` → `43c65b926` — NOT FOUND
- ✗ CPU2 mbind kill-switch `e84a5c82f` — NOT FOUND (functionality present via different commits per inventory)

Likely cause: the listed hashes are from a squashed/rebased history, possibly a different branch (e.g., the original `cpu-optimization/backlog-2026-04-23` branch referenced in the NPS-reboot runbook), or the inventory was written against a snapshot that has since been re-applied with new SHAs. The actual cherry-pick base must be reconciled before the audit can proceed.

### 2.2 Env-flag access pattern (mostly healthy)

13 of 14 audited env-gated flags use the cached static-init pattern:

```c
static int s_<flag> = -1;
if (s_<flag> < 0) {
    const char *e = getenv("GGML_<FLAG>");
    s_<flag> = e ? atoi(e) : 0;
}
```

Verified at: `ggml-cpu.c:701` (BARRIER_STRICT), `ggml-cpu.c:1531` (CCD_WORK_DIST), `ggml-cpu.c:1671` (EP_WORKER_DRONE), `ggml-cpu.c:1688` (EP_MASTER_PARK), `ggml-cpu.c:1712` (EP_WORK_STEALING), `ggml-cpu.c:2010` (EXPERT_CCD_SHARDING), `ggml-cpu.c:3758` (BARRIER_COALESCE), `ggml-cpu.c:3814` (BARRIER_LOCAL_BETWEEN_OPS), `ggml-cpu.c:4040` (CCD_POOLS, single threadpool-init call), `repack.cpp:5031` (Q8_0_8X8), `ops.cpp:3761` (RMS_NORM_PARALLEL), `ops.cpp:11062` (GDN_K_PER_HEAD, compile-time lambda).

**Outlier**: `repack.cpp:5168` — `GGML_NUMA_REPACK_INTERLEAVE` is read directly without static caching. The line context (per inventory `cb046ff58`) is the per-graph-compute repack phase — likely once per model load, not per inference token, but verify before declaring safe. If it IS in a hot path, this is a per-graph getenv that costs measurable CPU.

### 2.3 Deprecated flag code state

All 4 falsified mechanisms remain in tree, env-gated default-OFF, no `// DEPRECATED` markers:

| Flag | File:line | Gated path LOC | Inventory verdict |
|---|---|---|---|
| `GGML_NUMA_WEIGHTS` | `llama-mmap.cpp:471` + `llama-model-loader.cpp:1548` | ~60 mmap + ~120 warmup = ~180 | DEPRECATED — unstable on shared file-cache hosts |
| `GGML_RMS_NORM_PARALLEL` | `ops.cpp:3761` | ~60 (block 3765-3810) | Net-negative −9% at 96t per inline comment |
| `GGML_GDN_K_PER_HEAD` | `ops.cpp:11062` | ~10 (block 11061-11066) | "No current effect" per inline comment |
| `GGML_EXPERT_CCD_SHARDING` | `ggml-cpu.c:2010` | ~150 (block 2014-2160+) | CPU15 Phase 1 — superseded by Phase 3.2 inter-process EP |

Total: **~340 LOC of dead-by-default code with no in-source markers signaling deprecation status to a future reader.**

### 2.4 Debug instrumentation density

Counted across the 4 hot files. Severity ordering: in-loop > on-every-call > on-every-model-load > error-path > startup-once.

- **`ggml-cpu.c`** — 16 `fprintf/printf` total
  - 1 unconditional duplicate-init warning (line 767, ggml_numa_init) — startup-once, fine
  - 7 pthread error-path warnings (lines 2821, 2838, 2859, 3166, 3215, 3251, 3283, 3308) — error-gated, fine
  - 3 op-dispatch failure messages (lines 3123-3127) — error-path, fine
  - 1 commented-out debug printf (line 1317) — **dead code, remove**
  - 3 `snprintf` for sysfs path construction (lines 786, 794, 827) — not stdio, fine
- **`ggml-ep-bootstrap.cpp`** — 11 `fprintf/printf` total
  - **5 unconditional informational lines** (lines 61, 68, 77, 86, 119, 129, 157, 225, 247) — fire on every model load in EP mode. Not in inner loop, but pollute server logs. Should gate behind `GGML_EP_VERBOSE` (default-off).
  - 4 error-gated, fine
- **`ggml-ep-shard.cpp`** — 5 `fprintf/printf` total
  - **2 unconditional shard-warmup status lines** (lines 163, 232) — fire on every model load. Same gating recommendation.
  - 3 error-gated, fine
- **`repack.cpp`** — 0 `fprintf/printf`. Uses `GGML_LOG_WARN`/`GGML_LOG_INFO` macros correctly. **This is the model.**

### 2.5 Magic numbers

Block tile size `16` repeated 6× in `mul_mat`/`mul_mat_id` without commentary:

| File:line | Context |
|---|---|
| `ggml-cpu.c:1331-1332` | `const int64_t blck_0 = 16; const int64_t blck_1 = 16;` (mul_mat) |
| `ggml-cpu.c:1338` | `float tmp[32];` (16 × 2 for dual accumulation) |
| `ggml-cpu.c:1372` | `vec_dot(..., 16, ...)` stride |
| `ggml-cpu.c:1376` | `tmp + (cn * 16)` offset |
| `ggml-cpu.c:1750-1751` | `const int64_t blck_0 = 16; const int64_t blck_1 = 16;` (mul_mat_id) |
| `ggml-cpu.c:1753` | `float tmp[16];` |

The choice of 16 is architectural (cache line × SIMD width tuning for Zen 4/5 AVX-512), but no comment explains it. Refactor candidate: name it `MUL_MAT_BLOCK_SIZE` (or similar) with a one-line header comment.

### 2.6 TODOs

94 TODO/FIXME/XXX comments across `ggml/src/ggml-cpu/`. Top 5 most concerning:

1. **`repack.cpp:4944`** — `// TODO: this branch seems wrong` in Q8_0 8x8 repack. **Potential correctness bug in the kernel we plan to ship**. MUST investigate before keeping CPU2 Q8 ukernel.
2. **`ggml-cpu.c:1360`, `1772`** — `// TODO: this is a bit of a hack, we should probably have a better way to handle this` in mul_mat src indexing for non-contiguous src1 (5 LOC each instance). Design debt; not blocking but worth a follow-up handoff.
3. **`ggml-cpu.c:701`, `1531`** — `// TODO: add support for explicit memory order` in barrier init. Memory ordering may be incomplete on weak-ordering platforms (not a concern on x86-64, but worth noting for future ARM port if any).
4. **`ops.cpp:3761`** — `// TODO: smarter multi-threading` (4× nearby) in threading heuristics. Threading balance suboptimal; non-blocking.
5. **`repack.cpp` cases 128/512/1024** — `{ break; } // TODO` for unimplemented quantization-block-size branches (12 instances). **Silent break could mean silent failure on certain weight shapes**. Audit needs to verify these paths are unreachable with our model lineup OR replace `break;` with `GGML_ABORT("unimplemented block size")`.

### 2.7 Outdated comments

- `llama-mmap.cpp:471` (NUMA_WEIGHTS) — comment correctly documents the 2026-04-26 fix from process-wide `set_mempolicy` to per-region `mbind`. But describes the old broken behavior. If we STRIP the flag, both code AND comment go.
- `repack.cpp:5154-5156` — Phase 1.3 reference + acknowledgment of the redundancy with `set_mempolicy(MPOL_INTERLEAVE)`. Correct but verbose; tighten.
- Phase taxonomy — `ggml-cpu.c` has extensive `Phase 1.0`/`Phase 1.1`/`CPU15 Phase 1`/`CPU15 Phase 2` labels. **Most are correct historical labels**, but the CPU15 Phase 1 (expert-sharding) and Phase 2 (local-node anonymous copy redirection) blocks at `ggml-cpu.c:1996` + `2202` are SUPERSEDED by Phase 3.2 inter-process EP. Either strip (per Phase 1 audit) or add a "// Superseded by Phase 3.2; kept for fallback" note.
- `repack.cpp:5068` — "CPU25 NUMA_MIRROR Phase 1c" comment refers to falsified mechanism (decisive negative on single-socket NPS4). Either strip or mark superseded.

---

## 3. Phase 0 — Baseline reconciliation (BLOCKER)

**Goal**: identify the actual production-consolidated-v4 → experimental delta. Cannot proceed to Phase 1 without this.

### Steps

```bash
cd /mnt/raid0/llm/llama.cpp-experimental

# Enumerate the actual cherry-pick scope
git log --oneline production-consolidated-v4..feature/cpu-ep-inter-process > v5-cherry-pick-scope.txt

# Cross-reference with inventory
grep -E "(CPU1|CPU2|CPU4|CPU15|CPU22|slot-promotion|EP|MoE-Spec)" v5-cherry-pick-scope.txt
```

Reconcile each line against `cpu-kernel-env-flags-inventory.md` "Definitely cherry-pick" list. For each inventory hash that does NOT appear in the actual scope:
- Search by commit message (`git log --all --grep="<keyword>"`)
- Search by file diff (`git log --all -S"<unique-string>" -- ggml/src/ggml-cpu/`)
- Identify the current SHA that does the same logical work

### Output

Update `cpu-kernel-env-flags-inventory.md` "Definitely cherry-pick" subsection with verified current SHAs. Note: this is the FIRST modification to the inventory by this audit, and the only one that mutates the cherry-pick list before Phase 1 decisions are recorded.

### Time estimate

30 min.

### Exit criterion

A reconciled cherry-pick manifest exists in this handoff (append a "Reconciled commits" subsection here) AND in the inventory document. Every commit listed has been verified to exist in the repo.

---

## 4. Phase 1 — Strip-vs-Keep audit

**Goal**: per-flag/per-track explicit verdict.

### Verdict rubric

- **STRIP** = delete code + remove env var declaration. Apply when: superseded by a live mechanism AND not useful as fallback; OR unstable mechanism that's been decisively replaced; OR no realistic reopen path on this hardware.
- **KEEP-GATED** = preserve env-gated default-OFF. Apply when: closure-via-test recorded but mechanism is correct (not buggy); useful as fallback; clear reopen criteria documented.
- **REFACTOR-AND-KEEP** = preserve, but address code-quality issues (hot-loop env-cache, magic-number naming, comment hygiene, debug logging gating, header comment with measurement-evidence link).

### Pre-populated decision table

Reviewer fills in "Final verdict" + initials + date. Defaults from this row are starting suggestions, not coercive — deviate with justification.

| Track / flag | Suggested verdict | Rationale | Final verdict | Reviewer | Date |
|---|---|---|---|---|---|
| `GGML_NUMA_WEIGHTS` | **STRIP** | DEPRECATED (unstable on shared file-cache hosts); ~180 LOC removed; not useful as fallback (only worsens behavior). Replacement under research (private anon mmap + custom file-load, OR mlock+mbind+MOVE_PAGES) is itself a future handoff, not this one. Strip now to avoid shipping a known footgun. | | | |
| `GGML_RMS_NORM_PARALLEL` | **STRIP** | Net-negative (-9% on Qwen3.6-27B Q8 at 96t per inline comment 3754-3755). 60 LOC of dead-by-default code with no realistic reopen criterion on EPYC 9655 + Zen 5 + AVX-512. Future research can revive from git history if shape regime changes. | | | |
| `GGML_GDN_K_PER_HEAD` | **STRIP** | "No current effect" per `ops.cpp:11055`. 10 LOC dormant. Not actively researched. | | | |
| `GGML_EXPERT_CCD_SHARDING` (CPU15 Phase 1) | **STRIP** | Superseded by CPU15 Phase 3.2 inter-process EP. ~150 LOC dormant when `ep_active`. Strip + add a note in Phase 3.2 code citing the prior approach for future readers ("// Phase 3.2 supersedes the intra-process Phase 1 expert-sharding; see git history before 2026-NN-NN for that approach"). | | | |
| `GGML_BARRIER_STRICT` | **KEEP-GATED** | Diagnostic, ~3 LOC. Useful for debugging memory-ordering bugs. | | | |
| `GGML_NUMA_WARMUP_CCD` | **KEEP-GATED** | Diagnostic, useful for debugging first-touch placement. | | | |
| `GGML_NUMA_WARMUP_PHYS_PER_CCD` | **KEEP-GATED** | Diagnostic. | | | |
| `GGML_NUMA_WARMUP_MIN_BYTES` | **KEEP-GATED** | Diagnostic. | | | |
| **CPU1 stack** (`CCD_POOLS`, `CCD_WORK_DIST`, `BARRIER_LOCAL_BETWEEN_OPS`) | **REFACTOR-AND-KEEP** | Validated +1.8% on Coder-30B Q4_K_M (CPU21 P3 isolation 2026-04-26). All 3 flags individually safe. Audit checklist applies (Phase 2). | | | |
| `GGML_Q8_0_8X8` (legacy) | **STRIP** if superseded by AVX variant, else **KEEP-GATED** | Reviewer to confirm whether `repack.cpp:5031` Q8_0_8X8 is still needed once `GGML_Q8_0_8X8_AVX` is whitelisted. | | | |
| `GGML_Q8_0_8X8_AVX` (CPU2 AVX-512BW Q8_0 8x8) | **REFACTOR-AND-KEEP** | +31.8% @ 1t, +1-3% @ 12-96t (BW-saturated). Audit checklist applies. **MUST investigate `repack.cpp:4944` "TODO: this branch seems wrong" before keeping** — potential correctness bug. | | | |
| `GGML_Q6_K_8X8_AVX` (CPU2 AVX-512BW Q6_K 8x8) | **REFACTOR-AND-KEEP** | PPL bit-exact 32-chunk on Coder-30B + REAP-246B (2026-04-28). Production-ready. Audit checklist applies. | | | |
| `GGML_NUMA_REPACK_INTERLEAVE` (CPU2 mbind kill-switch, default-on) | **REFACTOR-AND-KEEP** | +6% AND stabilizing on Q8 MoE; -0.9% on Q4_K_M MoE. Default-on with kill-switch. **Specific issue**: `repack.cpp:5168` env read is uncached — verify it's in single-init path, not per-graph-compute. If hot, refactor to static-cached pattern. | | | |
| **CPU15 inter-process EP** (7 flags: `GGML_EP_ROLE`, `_N_INSTANCES`, `_NUMA_PIN`, `_MASTER_ALL_NODES`, `_SHARD`, `_WORKER_DRONE`, `_MASTER_PARK`) | **REFACTOR-AND-KEEP** | +17% Q8 frontdoor when activated (g.1 = drone+shard, N=2). Audit checklist: gate the 5 unconditional `fprintf` informational lines in `ggml-ep-bootstrap.cpp` + 2 in `ggml-ep-shard.cpp` behind `GGML_EP_VERBOSE` (default-off). | | | |
| **Slot-promotion dispatcher v1** (`--spec-numa-quarters`) | **KEEP-GATED** | Closure-via-test (gate not met on canonical workload + drafter). Mechanism is correct and race-free; +386 LOC stays default-off (CLI defaults to K=1). Reopen criteria documented in `handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md`. | | | |
| **CPU4 op-coalesced barriers** (`GGML_BARRIER_COALESCE`) | **KEEP-GATED** | Phase A re-test 2026-04-29 evening showed +0.19% NEUTRAL (not regression as originally measured under broken-OMP baseline). Default-off. MUL_MAT wdata race finding stands (correctness — independent of perf). Allowlist excludes MUL_MAT/MUL_MAT_ID. | | | |
| **CPU22 work-stealing** (`GGML_EP_WORK_STEALING`) | **STRIP** *(decision flagged — see below)* | Closure-via-test failed on 3 sync-bound MoE models (Phase D verified under canonical: -0.89% Coder, +0.18% Next-80B, -0.32% REAP-246B). Inventory says "preserve compile-time env-gated for hardware where atomic latency is lower" — but no concrete reopen workload identified. Recommend **strip**; reopen criterion (sync share >25% per perf-record on a specific model) can be re-implemented from a fresh design if it ever fires. **Reviewer must explicitly confirm or flip.** | | | |
| **MoE-Spec verification budget** (`--moe-spec-budget`) | **REFACTOR-AND-KEEP** | REAP-246B B=40 deployable (+13-16% pp32 / +3% e2e); Coder-30B B=64 NOT deployable (varies wildly). Per-role opt-in via CLI. Audit checklist applies. | | | |

### Decisions flagged for explicit reviewer attention

1. **CPU22 work-stealing** — strip vs keep-gated. Default suggestion: strip. Counter-argument: it's compile-time-gated and costs nothing if the env is unset, so keep for documentation value. Reviewer's call.
2. **Legacy `GGML_Q8_0_8X8`** vs new `GGML_Q8_0_8X8_AVX` — verify whether the legacy variant is still on a code path before deciding. If superseded, strip.
3. **CPU1 `GGML_NUMA_WEIGHTS`** — strip is the suggestion, but reviewer may want a separate "future research replacement" handoff before deletion (so the design history isn't lost). Path: extract the gated block into a research deep-dive document, THEN strip code.

### Time estimate

1.5 hr (most decisions are pre-thought; reviewer time is verification + flagged-decision resolution + filling the table).

---

## 5. Phase 2 — Code-quality punch list per kept commit/track

For each track classified KEEP-GATED or REFACTOR-AND-KEEP in Phase 1, apply this universal checklist + per-track specifics.

### Universal checklist (per track)

- [ ] Dead code / commented-out blocks removed (specific item: `ggml-cpu.c:1317` commented-out printf)
- [ ] Debug `fprintf`/`printf` removed OR gated behind env (`GGML_EP_VERBOSE`, `GGML_DEBUG`, etc.)
- [ ] Magic numbers named (e.g., `MUL_MAT_BLOCK_SIZE` instead of bare `16`)
- [ ] TODOs triaged — file follow-up handoff OR delete OR mark `// FUTURE: <concrete reopen criterion>` (no bare `TODO:` left in shipped tracks)
- [ ] Outdated comments referencing superseded mechanisms removed or marked
- [ ] Header comments document the env flag(s) gating the code AND cite the measurement-evidence bundle path (e.g., `// Gated by GGML_CCD_POOLS=1. Validated +1.8% on Coder-30B Q4_K_M tg32 — see data/cpu_optimization/2026-04-26-cpu1-p3-isolation/`)
- [ ] Per-iteration `getenv` replaced with cached lookup at plan-time (verify static-init pattern at every env-read site)
- [ ] Bit-exact PPL gate verified on at least one Q4 + one Q8 model with default-off vs default-on (no behavior change at default config)

### Per-track specifics

**CPU2 ukernels (Q8_0 / Q6_K AVX-512BW)**
- [ ] Investigate `repack.cpp:4944` "TODO: this branch seems wrong" — read the surrounding code, determine if correctness bug exists. If yes: file a separate fix handoff and BLOCK keeping the Q8 ukernel until resolved. If no: replace TODO with a comment explaining why the branch is correct.
- [ ] Address 12 silent `break;` cases for unimplemented quantization-block sizes 128/512/1024 in `repack.cpp` — replace with `GGML_ABORT("unimplemented block size for Q*_*X*")` so failures are loud, not silent.
- [ ] Document the `16` block-tile-size choice (cache-line × SIMD-width tuning for Zen 4/5 AVX-512).

**CPU1 stack (`CCD_POOLS`, `CCD_WORK_DIST`, `BARRIER_LOCAL_BETWEEN_OPS`)**
- [ ] Verify the per-CCD threadpool partitioning code at `ggml-cpu.c:4040` reads env once at threadpool init — should already be the case, confirm.
- [ ] Verify per-op CCD work-distribution at `ggml-cpu.c:1531`, `3610` reads cached `s_ccd_wd_env` not direct `getenv` — already correct, confirm.
- [ ] Verify barrier-local-between-ops at `ggml-cpu.c:3814` is consistent with the conservative allowlist used by CPU4 coalesce.
- [ ] Add header comment to each gated block: "Gated by GGML_<FLAG>=1. Validated on <model class> at <Δ%>. Bundle: <path>."

**CPU2 NUMA_REPACK_INTERLEAVE auto-mbind**
- [ ] **Specific fix**: refactor `repack.cpp:5168` direct `getenv` to static-cached pattern matching the rest of the codebase. If the read is genuinely once per model load, the cost is trivial and the refactor is for consistency only.
- [ ] Document the kill-switch semantics: default-on, `=0` to disable. Cite the kill-switch isolation evidence bundle.

**CPU15 inter-process EP (7 flags)**
- [ ] **Specific fix**: introduce `GGML_EP_VERBOSE` (default-off) env flag. Gate the 5 unconditional `fprintf` lines in `ggml-ep-bootstrap.cpp` (61, 68, 77, 86, 119, 129, 157, 225, 247) + 2 in `ggml-ep-shard.cpp` (163, 232) behind it. Or convert to `GGML_LOG_INFO` if a startup-info logger already exists in the upstream macro family.
- [ ] Verify EP-master loop at `ggml-cpu.c:1671`, `1688`, `2259` doesn't read env per-graph (already cached per static patterns, confirm).
- [ ] Document each of the 7 EP env flags with a comment block at the env-read site explaining the intended deployment posture (e.g., master vs drone, shard vs replicate).

**Slot-promotion dispatcher v1 (`--spec-numa-quarters`)**
- [ ] Verify the K=1 fast path at `tools/server/server-context.cpp` is bit-exact with K=1 baseline (CLI default). The K-parallel branch should be unreachable when K=1.
- [ ] Add a one-line CLI help string referencing the closure: "K-parallel candidate verify. Default K=1 (off); higher K explored 2026-04-30 — gate not met on canonical workload, see hybrid-ssm-slot-promotion-spec-dec.md."

**CPU4 op-coalesced barriers (`GGML_BARRIER_COALESCE`)**
- [ ] Verify the conservative allowlist (`RMS_NORM`, `NORM`, `ROPE`, `MUL`, `ADD`, `SCALE`, `UNARY`, `GLU` — excludes MUL_MAT/MUL_MAT_ID per Phase 1 wdata-race discovery) is enforced correctly at `ggml-cpu.c` Phase 1 dispatch site.
- [ ] Verify the MUL_MAT wdata race remediation comment is in place at `ggml-cpu.c:1467-1487` (the original site of the race).

**MoE-Spec verification budget (`--moe-spec-budget`)**
- [ ] Per-role budget validated only for REAP-246B B=40. Verify the CLI parser rejects unrealistic values OR clamps with a warning.
- [ ] Header comment cites the deployment-draft per-role binding.

### Time estimate

2-3 hr (per-track checklists, file edits, smoke validation per change).

---

## 6. Phase 3 — Cleanup commits BEFORE cherry-picks (clean branch strategy)

### Branching plan

```
production-consolidated-v4 (start; status COMPLETE per llama-cpp-kernel-push-rebase.md)
  ↓
[STRIP COMMITS — one per stripped flag, atomic, reviewable]
  - "ggml-cpu: remove deprecated GGML_NUMA_WEIGHTS path (CPU1 Phase 1.3)"
  - "ggml-cpu: remove net-negative GGML_RMS_NORM_PARALLEL path"
  - "ggml-cpu: remove no-effect GGML_GDN_K_PER_HEAD path"
  - "ggml-cpu: remove superseded GGML_EXPERT_CCD_SHARDING path (CPU15 Phase 1)"
  - (optional) "ggml-cpu: remove failed CPU22 GGML_EP_WORK_STEALING prototype"
  ↓
[REFACTOR COMMITS — one per cross-cutting cleanup]
  - "ggml-cpu: name MUL_MAT_BLOCK_SIZE constant for tile dimensions"
  - "ggml-cpu/repack: replace silent break; with GGML_ABORT for unimplemented quant sizes"
  - "ggml-ep: gate informational logs behind GGML_EP_VERBOSE env"
  - "ggml-cpu/repack: cache GGML_NUMA_REPACK_INTERLEAVE env at init (consistency)"
  - "ggml-cpu: add measurement-evidence header comments to env-gated blocks"
  - "ggml-cpu: triage TODOs (delete obsolete, file follow-up handoffs for design debt)"
  ↓
[CHERRY-PICK COMMITS — KEEP-GATED + REFACTOR-AND-KEEP, in dependency order]
  - CPU1 stack:
      1. CCD_POOLS (threadpool init must come first)
      2. CCD_WORK_DIST (depends on per-CCD pools)
      3. BARRIER_LOCAL_BETWEEN_OPS (independent but pairs with CCD work-dist)
  - CPU2 mbind kill-switch (NUMA_REPACK_INTERLEAVE — base for CPU2 ukernels)
  - CPU2 AVX-512BW Q8_0 8x8 ukernel (Q8_0_8X8_AVX)
  - CPU2 AVX-512BW Q6_K 8x8 ukernel (Q6_K_8X8_AVX)
  - CPU15 EP family (7 commits, dependency-ordered):
      1. EP_ROLE / EP_N_INSTANCES (control plane)
      2. EP_NUMA_PIN
      3. EP_MASTER_ALL_NODES
      4. EP_WORKER_DRONE
      5. EP_MASTER_PARK
      6. EP_SHARD (the actual sharding feature)
      7. (any remaining infra commits)
  - Slot-promotion dispatcher v1 (--spec-numa-quarters; default K=1 = off)
  - CPU4 op-coalesced barriers (GGML_BARRIER_COALESCE; default-off; allowlist verified)
  - MoE-Spec verification budget (--moe-spec-budget)
  - Diagnostic flags (BARRIER_STRICT, NUMA_WARMUP_*)
  ↓
[BUILD-SYSTEM COMMIT]
  - "CMake: switch default to clang-20 + libomp + -march=znver5 + LLVM PGO use"
  - "CMake: per-role BOLT-libggml support for Coder-30B binary (build_libomp_pgo_bolt/bin_bolted/)"
  ↓
production-consolidated-v5 (push-ready)
```

### Rationale for refactor-before-cherry-pick

1. **Reviewability** — each cleanup commit is small (10-200 LOC), focused on one concern, easy to review.
2. **Bisect-friendly** — if v5 has a regression, `git bisect` lands on a single change, not a multi-feature cherry-pick.
3. **Blame hygiene** — the cherry-pick commits land their full historical change unmuddied. Future agents reading `git blame` see the original commit message + author + date for the feature work, not "drive-by cleanup as part of push".
4. **Failure containment** — if a cherry-pick fails to apply cleanly, the cleanup commits ahead of it are still on the branch and can be preserved.

### Time estimate

1-2 hr (mostly mechanical once Phase 1 + 2 decisions are made).

---

## 7. Phase 4 — Validation gates

Before declaring v5 ready to push, run all of these gates. ALL must pass.

### 7.1 Build gate

```bash
cd /mnt/raid0/llm/llama.cpp  # production repo
git checkout production-consolidated-v5

# Build with both compilers; v5 default toolchain is clang-20+libomp+znver5+PGO
cmake -B build_v5_clang -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang-20 -DCMAKE_CXX_COMPILER=clang++-20 \
  -DCMAKE_C_FLAGS="-march=znver5 -fprofile-instr-use=$PROFDATA -Wall -Wextra -Wpedantic" \
  -DCMAKE_CXX_FLAGS="-march=znver5 -fprofile-instr-use=$PROFDATA -Wall -Wextra -Wpedantic" \
  -DGGML_OPENMP=ON -DGGML_LLAMAFILE=ON
cmake --build build_v5_clang -j 96 2>&1 | tee build_v5_clang.log

# GCC sanity build (no PGO, just compile-clean check)
cmake -B build_v5_gcc -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_FLAGS="-Wall -Wextra -Wpedantic" \
  -DCMAKE_CXX_FLAGS="-Wall -Wextra -Wpedantic"
cmake --build build_v5_gcc -j 96 2>&1 | tee build_v5_gcc.log
```

Pass criterion: zero warnings introduced relative to v4 baseline (compare warning counts). Errors are obviously fail.

### 7.2 PPL bit-exact gate

At default-OFF env (no opt-in flags), v5 PPL must match v4 byte-for-byte on:

| Model | Quant | Chunks | Expected PPL (from v4) |
|---|---|---|---|
| Qwen3-Coder-30B-A3B | Q4_K_M | 1-12 | 11.1146 ± 0.62405 |
| Qwen3.6-35B-A3B | Q8_0 | 1-12 | (from v4 baseline — read from `data/cpu_optimization/2026-04-28-cpu11-pgo/q8_pgo_use.log`) |
| REAP-246B-A35B | Q4_K_M | 1-12 | (from v4 baseline) |
| gemma-4-31B-it | Q4_K_M | 1-12 | (from v4 baseline) |

```bash
# Per model
LD_LIBRARY_PATH=$BUILD/bin OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all -- taskset -c 0-95 \
  $BUILD/bin/llama-perplexity -m $MODEL -f $WIKI_TEST -t 96 -fa 1 --chunks 12
```

### 7.3 Reproducibility tripwire

Per `feedback_omp_env_stack_required.md` and `feedback_canonical_baseline_protocol.md`:

```bash
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all -- taskset -c 0-95 \
  $BUILD/bin/llama-bench -m $CODER_30B_Q4KM \
  -t 96 -fa 1 --mmap 0 -p 0 -n 32 -r 5
```

Pass criterion: ≥ 47 t/s (cold-boot canonical lower bound). If host has been warm > 1 hour, ≥ 50 t/s expected.

### 7.4 Per-role smoke

For each role in `model-registry-v5-deployment-draft.yaml` `roles:` section:

```bash
# Launch llama-server with the role's binary_path + env block + role-specific CLI
# Smoke 5 prompts via curl /completion
# Verify timings.predicted_per_second within ±5% of expected_throughput
```

Specific roles to smoke (drawn from deployment-draft):
- `worker` — Coder-30B-A3B Q4_K_M (CPU1 stack + BOLT binary)
- `architect_coding` — REAP-246B-A35B Q4_K_M (PGO-only + moe_spec_budget=40)
- `frontdoor` — Qwen3.6-35B-A3B Q8_0 (PGO-only + EP stack)
- `hybrid_ssm_dense` — Nemotron-9B-v2 Q8_0 (CPU1 + mbind off) — ONLY if rostered
- `hybrid_ssm_moe` — Qwen3-Next-80B-A3B Q4_K_M (default v5)

### 7.5 No-regression gate (default config)

At default-OFF env (no opt-in), v5 throughput must be within ±2% of v4 default-config canonical numbers across all 4 production model classes:

| Model | v4 canonical (no env, mmap=0, --interleave=all + OMP env) | v5 must achieve |
|---|---|---|
| Coder-30B Q4_K_M tg32 | ~47-49 t/s cold-boot | ≥ 46 t/s |
| Qwen3.6-35B Q8_0 tg32 | ~23 t/s cold-boot | ≥ 22.5 t/s |
| REAP-246B Q4_K_M tg32 | ~6.3 t/s cold-boot | ≥ 6.15 t/s |
| gemma-31B Q4_K_M tg64 | ~6.4 t/s | ≥ 6.25 t/s |

### 7.6 Time estimate

3-4 hr wall-clock (PPL gates ~30 min per model × 4 models = 2 hr; smoke ~30 min; bench ~1 hr; plus build time).

---

## 8. Phase 5 — Output artifacts

The audit produces, in this order:

1. **Updated `cpu-kernel-env-flags-inventory.md`** — current SHAs, decision-resolved per-flag table (Final verdict column filled).
2. **`production-consolidated-v5` branch** in `/mnt/raid0/llm/llama.cpp` — clean linear history (strips → refactors → cherry-picks → build-system).
3. **CPU20 audit bundle** at `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-NN-NN-v5-cleanup-audit/`:
   - `README.md` — top-level summary
   - `phase0-reconciliation.md` — commit-hash mapping (inventory hash → current SHA)
   - `phase1-strip-keep-decisions.md` — completed Phase 1 decision table with reviewer initials
   - `phase2-punch-list-completed.md` — checklist with all items checked
   - `phase3-branch-log.txt` — `git log --oneline production-consolidated-v4..production-consolidated-v5`
   - `phase4-validation-gates/` — sub-bundle with build logs, PPL outputs, smoke logs, bench results
   - `decision.md` — final go/no-go for v5 push
4. **PR-ready commit** in `epyc-orchestrator` updating `model_registry.yaml` per the deployment-draft (only after v5 validation gates pass — NOT before).
5. **`v5-push-cleanup-audit.md` handoff** updated to status COMPLETE, moved to `handoffs/completed/`.

---

## 9. Time estimates (overall)

| Phase | Estimate |
|---|---|
| Phase 0 (baseline reconciliation) | 30 min |
| Phase 1 (strip-vs-keep audit) | 1.5 hr |
| Phase 2 (code-quality punch list) | 2-3 hr |
| Phase 3 (cleanup commits + cherry-picks) | 1-2 hr |
| Phase 4 (validation gates) | 3-4 hr |
| Phase 5 (artifacts + push) | 30 min |
| **Total** | **9-12 hr wall-clock — single dedicated session** |

This is too large for a side task. Schedule as primary work for one full day OR split across two sessions (Phases 0-3 in one, Phases 4-5 in another with the validation-gate compute running between them).

---

## 10. References

### Active handoffs
- [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md) — env-flag inventory + Per-Arch Deployment Matrix + cherry-pick scope
- [`model-registry-v5-deployment-draft.yaml`](model-registry-v5-deployment-draft.yaml) — staging file for per-role binary_path + env
- [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) — parent CPU optimization index
- [`inference-acceleration-index.md`](inference-acceleration-index.md) — broader acceleration index
- [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) — CPU20 protocol (artifact bundle requirements)
- [`cpu4-deferred-avenues-design-note.md`](cpu4-deferred-avenues-design-note.md) — CPU4 Phase 1 + Phase A re-test framing
- [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) — MoE-Spec REAP=40 deployment story

### Completed handoffs
- [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md) — v4 push reference (status COMPLETE — read for branching pattern, do not modify)
- [`hybrid-ssm-slot-promotion-spec-dec.md`](../completed/hybrid-ssm-slot-promotion-spec-dec.md) — slot-promotion closure
- [`mab-tree-shape-selector.md`](../completed/mab-tree-shape-selector.md) — MAB closure (Phase C reframe)

### Data bundles (measurement evidence)
- `2026-04-28-cpu11-pgo/` — v4 PGO baseline (PPL chunks 1-12 reference)
- `2026-04-28-cpu12-bolt/` — BOLT-libggml per-role-Coder evidence
- `2026-04-28-cpu21-libomp-chunks/` — CPU21 P3 isolation (CPU1 stack +1.8% Coder)
- `2026-04-28-cpu22-work-stealing/` — CPU22 closure-via-test
- `2026-04-29-remediation-phase-A-cpu4/` — CPU4 +0.19% NEUTRAL re-test
- `2026-04-29-remediation-phase-D-cpu22/` — CPU22 verification under canonical
- `2026-04-29-multi-arch-coverage-canonical/` — per-arch matrix
- `2026-04-29-workload-shape-canonical/` — Probe B (pp512/pp2048/tg64)
- `2026-04-30-hybrid-ssm-next80b-followup/` — Hybrid SSM generalization test
- `2026-04-30-state-sync-cost-probe/` — slot-promotion dispatcher gate
- `2026-04-29-mab-phase-0-prime-prime-replication/` + `2026-04-29-remediation-phase-C-mab/` — MAB closure + reframe

### Memories (apply per session)
- `feedback_canonical_baseline_protocol.md` — `taskset -c 0-95 -t 96 -fa 1 --mmap 0` + OMP env stack + numactl --interleave=all = canonical
- `feedback_omp_env_stack_required.md` — without OMP env, post-reboot is 3-4× degraded (NEW 2026-04-29 — was the discovery that triggered this audit's scope expansion)
- `feedback_host_throttle_check.md` — pre-bench freq scaling check
- `feedback_no_concurrent_inference.md` — never launch llama-bench/server without explicit per-run approval

### Critical files (read paths)
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ggml-cpu.c` — main hot loop, env-flag access patterns, barrier code, threadpool init
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/repack.cpp` — Q8/Q6 ukernels + NUMA_REPACK_INTERLEAVE
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ops.cpp` — RMS_NORM_PARALLEL (3761), GDN_K_PER_HEAD (11062)
- `/mnt/raid0/llm/llama.cpp-experimental/src/llama-mmap.cpp` — NUMA_WEIGHTS (471)
- `/mnt/raid0/llm/llama.cpp-experimental/src/llama-model-loader.cpp` — NUMA_WEIGHTS warmup (1548)
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ggml-ep-bootstrap.cpp` — EP control plane + informational logs
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ggml-ep-shard.cpp` — EP shard logic + informational logs
- `/mnt/raid0/llm/llama.cpp-experimental/tools/server/server-context.cpp` — slot-promotion dispatcher v1

### Existing patterns to reuse (don't reinvent)
- **Static-cached env-var lookup** — already used at 11+ sites in `ggml-cpu.c`. Apply to the one outlier (`repack.cpp:5168`).
- **`GGML_LOG_*` macro family** — already used cleanly in `repack.cpp` (no `fprintf` litter). Apply to `ggml-ep-*.cpp` to gate informational output.
- **v4 push-rebase handoff's table format** — "Patches to KEEP" / "Drop" / "Deferred" / "Build fix" structure. Port for v5 cherry-picks.
- **CPU20 bundle structure** — `system-state.txt`, `process-pre.txt`, `process-post.txt` (with credential scrubber per `cpu-benchmark-rigor-and-revalidation.md` 2026-04-30 update), `decision.md`, `results.csv`. Apply to v5 audit bundle.

---

## 11. Out of scope for this handoff

Explicit non-goals (avoid scope creep when executing):

- ❌ Touching `llama-cpp-kernel-push-rebase.md` (v4-specific, status COMPLETE; preserve as historical record).
- ❌ Modifying `model_registry.yaml` in `/mnt/raid0/llm/epyc-orchestrator` BEFORE v5 validation gates pass. The deployment-draft is the staging file; the registry update is gated on validation.
- ❌ Code review of upstream llama.cpp commits not in our cherry-pick scope. Anything touching files we don't modify is out.
- ❌ Re-litigating per-arch deployment matrix or any closure framings. Phase A-D Remediation already settled those.
- ❌ Implementing replacement for stripped `GGML_NUMA_WEIGHTS`. The replacement (private anon mmap + custom file-load, OR mlock+mbind+MOVE_PAGES) is its own future research handoff.
- ❌ Adding new env flags or new mechanisms. v5 is a CLEANUP push, not a feature push.

---

## 12. Open questions for executing reviewer

Resolve at start of execution:

1. **CPU22 work-stealing**: strip or keep-gated? Default suggestion: strip. Reviewer's call.
2. **Legacy `GGML_Q8_0_8X8`**: still on a code path? If superseded by `GGML_Q8_0_8X8_AVX`, strip.
3. **`GGML_NUMA_WEIGHTS` strip vs preserve-as-research-record**: extract to a research deep-dive document before deletion, or just delete and let git history serve as the record?
4. **`production-consolidated-v4` baseline location**: confirm the production v4 branch lives at `/mnt/raid0/llm/llama.cpp` (production repo) and the experimental work is at `/mnt/raid0/llm/llama.cpp-experimental` (experimental repo) — the audit assumes we cherry-pick FROM experimental TO production. If both repos share a remote and the v4 branch is on the experimental repo too, the cherry-pick can be done in-place; otherwise the workflow is `git format-patch` + `git am`.
5. **Toolchain commit ordering**: should the build-system commit (clang+libomp+znver5+PGO) come BEFORE or AFTER the cherry-picks? Default: AFTER (cherry-picks land on the v4 toolchain, then we switch). Counter: BEFORE (cherry-picks land on the v5 toolchain, so PPL gate runs once at the end). Reviewer's call.

---

**End of handoff.** Owner reviewer: append "Reconciled commits" subsection (Phase 0 output), filled decision table (Phase 1 output), checked-off punch list (Phase 2 output), and final disposition at the end of this document.
