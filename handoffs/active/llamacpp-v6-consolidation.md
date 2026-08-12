# llama.cpp v6 Consolidation — production-consolidated-v6

> **Historical / superseded 2026-07-29:** production is frozen on
> `production-consolidated-v8`; do not modify or build this v6 branch. Any future
> kernel work starts from fresh v8 in `llama.cpp-experimental`. The remaining F1
> v6-fold checkbox below is retired rather than executable; see
> `handoffs/completed/v6-iqk-promotion.md` for the cutover record.

**Status**: Stage 1 DONE + functionally verified (committed, NOT promoted). Stage 2 parity backlog + post-reboot bench gate the promotion. **2026-06-26 v6 cutover: registry/launcher/governance config converged onto production-consolidated-v6 (now incl. iqk kernels); the gemma worker IS being consolidated onto v6 (the 2026-06-25 "do NOT cut gemma to v6" verdict is SUPERSEDED — see below). Live throughput + garbage verification PENDING (operator deploy gate). Tracking: `handoffs/active/v6-iqk-promotion.md`.**
**Last updated**: 2026-06-26

> All performance numbers in this doc are **OBSERVATIONS**, not decision-gating metrics. Host is at 25-day uptime → absolute t/s are throttle-suspect; only multipliers are robust. Any number used to gate keep/revert/promote requires the canonical recipe (`bench_canonical.sh` / `canonical_recipe.py`) + operator approval. See `/workspace/MEASUREMENT.md`.

---

## Start here

`production-consolidated-v6` is a fresh upstream `origin/master` (commit `f8cc15f16`) with our surviving production-ACTIVE CPU kernels forward-ported on top. It resolves the long-standing fork: **fresh-upstream (gets new MTP/framework, loses our kernels) vs reimplement-in-our-fork (keeps kernels, can't get MTP)**. v6 gets BOTH.

Why now:
- v5 fork is **903 commits behind** upstream.
- The #22673 Qwen-MTP cherry-pick into v5 was **INFEASIBLE** (new upstream `llama_model_base` model-framework gap).

What upstream `f8cc15f16` brings natively:
- New `llama_model_base` model framework
- Native MTP (PR #22673)
- gemma-4 MTP (PR #23398)
- EAGLE3 speculation

Worktree / branch:
- Worktree: `/mnt/raid0/llm/llama.cpp-v6` (branch `production-consolidated-v6`). Build dir: `build/`.
- **NEVER touch production `/mnt/raid0/llm/llama.cpp`** (stays on `production-consolidated-v5`; `verify_llama_cpp.sh` enforces).
- v5 baseline for the port: `production-consolidated-v5` (`a6c793fc6`); merge-base with upstream = `81df3f7cf` (2026-04-20); our fork = **107 commits** over merge-base.

Branch commits so far:
- `814e81782` — Stage 1a (CPU2 AVX-512BW repack kernels)
- `c159997e0` — Stage 1b (CPU1/CPU4 CCD threadpool code)

---

## Stage 1 — DONE + verified (committed, NOT promoted)

### Stage 1a — `814e81782` — CPU2 AVX-512BW repack kernels
- Files: `ggml/src/ggml-cpu/arch/x86/repack.cpp`, `arch/x86/avx512-helpers.h` (AVX-512BW 8x8 Q8_0 GEMV + Q6_K 8x8 SIMD + Q6_K T1 prefetch), `repack.cpp` (OpenMP repack parallelization + self-contained CPU_REPACK NUMA mbind via raw syscall + `GGML_NUMA_REPACK_INTERLEAVE` kill-switch), `repack.h`, `arch-fallback.h`.
- Env-gated **default-off** (`GGML_Q8_0_8X8` / `GGML_Q6_K_8X8_AVX`), matching v5 posture.
- Upstream barely touched these across 903 commits → grafted near-clean. Only fix needed: drop 3 stale `q1_0`/`q4_1` generic-alias macros that upstream removed (caused a multiple-definition link error).
- **ACTIVE under OpenMP-ON.**

### Stage 1b — `c159997e0` — CPU1/CPU4 CCD threadpool code
- 3-way merge of `ggml-cpu.c` (base / v5 / upstream) was **CLEAN (0 conflicts)** = upstream's `ggml-cpu.c` (op-fusion, COL2IM_1D, Hadamard FWHT hint, GDN cplan sizing fix) + our CCD code.
- Dead code excised during the merge:
  - All **36 EP refs** (CPU15 inter-process expert-parallel) removed — `mul_mat_id`/`one_chunk` swapped to upstream's clean versions; ep helpers / drone-block / bootstrap dropped.
  - Paged-attn dispatch (`GGML_OP_FLASH_ATTN_EXT_PAGED` x3) stripped → deferred to Stage 2.
- CCD code retained: per-CCD 2-level barrier, `ggml_barrier_local`, `GGML_CCD_WORK_DIST`, `GGML_BARRIER_LOCAL_BETWEEN_OPS`, `GGML_CCD_POOLS` init.

### Verification (functional only; perf bench is post-reboot)
- Both stages build clean.
- Qwen3.5-9B-Q4_K_M + `--spec-type draft-mtp --spec-draft-n-max 3` → ~89% draft acceptance, correct output (all 25 primes), no deadlock.

---

## ⚠ KEY FINDING — CCD is compiled OUT in production (OpenMP-ON)

The ENTIRE CCD path (per-CCD barriers, work-dist, pools, between-ops barrier) lives inside `#ifndef GGML_USE_OPENMP` blocks — i.e. the custom-pthread-threadpool path, NOT the OpenMP path.

Production builds ALL use `GGML_OPENMP=ON` — verified across every `/mnt/raid0/llm/llama.cpp/build*/CMakeCache.txt` and the launched `build/bin/llama-server`.

**Consequence**: the `GGML_CCD_POOLS=1` / `GGML_CCD_WORK_DIST=1` / `GGML_BARRIER_LOCAL_BETWEEN_OPS=1` env vars set in `epyc-orchestrator/scripts/server/stack_env.py` (lines 67/99) are **vestigial no-ops on the live binary** — the CPU1 CCD optimization is NOT active in production. v6 (OpenMP-ON) matches this posture (CCD inert). Code is retained so an OpenMP-OFF build can activate/measure the custom-pool CCD path later.

(Relates to memory `project_cpu1_software_levers_exhausted`.)

**OPERATOR-REVIEW ITEM**: decide between
- (a) build OpenMP-OFF to actually activate + measure CCD gains, or
- (b) clean up the vestigial `GGML_CCD_*` env vars in `stack_env.py`.

---

## Stage 2 — PARITY backlog (NOT yet ported; required before v6 replaces v5)

Production-deployed features still on v5 only. **For EACH: first check whether upstream `f8cc15f16` now provides it natively** (several likely do).

- [x] **Paged attention** (`GGML_OP_FLASH_ATTN_EXT_PAGED` + `ops.cpp` impl + `ggml.h` enum/OP_COUNT) — commits `6843e1274..18b2ebfde`. CHECK upstream native flash-attn first (may be UPSTREAM-NATIVE now). ✅ 2026-07-14 F1 RESOLVED+VERIFIED 2026-06-24 (branch `f1-paged-attn` `112022a0b`; see F1-RESOLUTION)
- [x] **RETIRED — do not fold `f1-paged-attn` (`112022a0b`) into `production-consolidated-v6`.** ✅ 2026-07-29 — v6 is a historical superseded production version; the frozen v8 immutability contract prohibits this in-place patch. Re-evaluate only as an experimental candidate freshly based on v8, under its own regression protocol.
- [x] **KV compaction stack** — Attention-Matching (`f1cf9bd9f` / `042ca88b1` / `45b4849ac`) + Expected-Attention (`894e048e3`, the deployed default compactor) — `src/llama-graph.cpp`, server integration. ✅ 2026-07-14 F2/F3 DONE + BEHAVIORALLY VALIDATED (`3f9df4bd3`; knorm legacy scorer deliberately not ported)
- [x] **Hadamard KV smoothing** (`ea6ab859c`, production config) — CHECK upstream #21038. The Hadamard FWHT hint IS already in v6 via upstream → may be PARITY-already-present. ✅ 2026-07-14 ALREADY-NATIVE in v6, no port needed
- [x] **IMROPE seq_add/seq_div + K-shift** for qwen35moe hybrids (`935e9bbbd`) — required for the deployed Qwen3.5 hybrid (architect). ✅ 2026-07-14 F5 DONE + VALIDATED incl. 122B deep validation (`00fe78602`)
- [x] **Server slot management** (`55fa088e8` / `ffcb1baf4`). ✅ 2026-07-14 F6 DONE + BEHAVIORALLY VALIDATED (`60c270203`)

---

## Triage classification of the 107-commit fork

### DEAD — do NOT port (~54 commits)
TIDE early-exit (deprecated dead-end), CPU15 EP (closed), slot-promotion (shelved), NUMA_WEIGHTS family (hard-stripped in v5), op-fusion (reverted; upstream has its own), CPU22 work-stealing (gate-failed), `RMS_NORM_PARALLEL` / `GDN_K_PER_HEAD` (stripped), MoE-Spec (default-off), Lightning / ring-linear (not deployed).

### UPSTREAM-NATIVE — drop (~4 commits)
MTP bench tooling, tree/DySpec speculation, fail-closed-spec, tree-spec capacity fix. Upstream ships native MTP / spec / EAGLE3.

### NEEDS-OPERATOR-REVIEW (6)
- [x] SWA slot-reuse fixes (`d1c72d7fc` / `603702769`) — verified vs upstream SWA. **Verdict: DROP.** ✅ 2026-08-12
      — see [§ SWA slot-reuse verification — 2026-08-12](#swa-slot-reuse-verification--2026-08-12). The pair does
      not merely duplicate upstream; it **replaces** upstream's per-sequence check with a per-sequence-**blind**
      one, so it is a regression to carry forward, not a feature to port.
- [ ] `--moe-n-expert` Hard-Mask CLI tool (`86901388a`).
- [ ] Differential-Transformer-V2 arch (`36ceed44d` / `23973ea66`) — eval-gated, not in deployed registry.
- [ ] Streaming KV context-shift controls (`632ce0f92`).
- [ ] Paged-attn upstream-overlap.

---

## SWA slot-reuse verification — 2026-08-12

Read-only `git -C /mnt/raid0/llm/llama.cpp` archaeology. No branch was switched, nothing was built, and the
frozen production tree was only ever read via `git show <rev>:<path>`.

**Containment.** Neither commit is an ancestor of any production version from v6 on:

| commit | subject | in v6 | v7 | v8 | v9 (`0db32c06e`) |
|---|---|---|---|---|---|
| `d1c72d7fc148a708` | kv-cache : optimize SWA slot reuse with forward-looking masking | no | no | no | **no** |
| `603702769cef373f` | kv-cache: fix SWA cell reuse to ensure mathematical correctness | no | no | no | **no** |

`git branch --contains` puts both only on the v4/v5 lineage and its feature branches. They have been out of
production for four consecutive kernel versions, so "before drop" is retrospective: they are already dropped;
what was open was whether anything was *lost*.

**Nothing was lost — the opposite.** These commits did not *add* SWA slot reuse; upstream already had it and
`d1c72d7fc` **deleted** it. Its own diff removes these two lines:

```c
const llama_seq_id seq_id_cell = cells.seq_get(idx);
if (llama_hparams::is_masked_swa(n_swa, swa_type, pos_cell, cells.seq_pos_max(seq_id_cell) + 1)) {
```

and substitutes `pos_batch_max + 1` (later `pos_batch_min + 1` in `603702769`) taken from the *incoming*
`ubatch`. v9 carries the original upstream form verbatim — `llama-kv-cache.cpp:1053-1059` of
`0db32c06e3e550065b78311a6031ef3dd2c4f27c`:

```c
const llama_seq_id seq_id_cell = cells.seq_get(idx);
// SWA mask
if (llama_hparams::is_masked_swa(n_swa, swa_type, pos_cell, cells.seq_pos_max(seq_id_cell) + 1)) {
    can_use = true;
}
```

**Why the fork version is worse, not just different.** The enclosing guard is `cells.seq_count(idx) == 1` — the
cell has exactly **one** owner sequence, but nothing requires that owner to be the sequence being inserted.
Upstream answers *"is this cell outside the window of its own sequence's newest token?"*. The fork, having
deleted the `seq_get(idx)` lookup, answers *"is this cell outside the window of the token I am inserting right
now?"* — a cell belonging to an idle or slower slot is judged against a busy slot's positions and can be
declared reusable while still inside its owner's window. That is a **multi-slot serving** hazard, and multi-slot
is our production posture.

The commit's own message records its validation as *"Gemma-3-12B (n_swa=1024) + Gemma-3-1B draft, 1504 tokens
generated"* — single-sequence speculative decode, which cannot exercise the cross-sequence path at all. So the
evidence attached to the change is real but orthogonal to the property the change broke. This is not a claim
that a production incident occurred; it is the reason the pair must not be resurrected onto a future
`llama.cpp-experimental` branch.

**Action**: none. Row closed as DROP. If SWA reuse is ever revisited, the question to ask is whether upstream's
backward-looking test is too conservative for speculative decode (the fork's original motivation) — and any such
change must keep the `seq_get(idx)` lookup.

---

## Post-reboot NUMA topology bench (the NEXT gate)

Host needs reboot (25-day uptime). Operator chose **build v6 first, then bench on v6**.

Matrix:
- Models (dense): {Qwen3.5-9B, gemma-4-31B}
- Mode: {baseline, MTP `draft-mtp dm=3`}
- Topology: {quarter = 1 NPS4 node / 24c, half = 2 nodes / 48c, full = 4 nodes / 96c}

Phases:
- **Phase A** — single-instance (latency).
- **Phase B** — concurrent (4× quarter vs 2× half vs 1× full, aggregate t/s). Prior decode-only result: quarters **+44–58%**, dual-half **NEGATIVE** (observations).
- **NEW dimension** (from the CCD finding): also compare **OpenMP-ON vs OpenMP-OFF (+CCD active)** to settle whether the custom-pool CCD path is worth it.

Methodology: `--no-mmap --mlock` + `numactl --cpunodebind/--membind`, full OMP env stack, `-fa 1`, `affinity_preflight.py` for live-affinity verification (topology_hash alone is insufficient — verify the live thread-union mask).

Outcome: winning topology → bake into v6 launch config (orchestrator `process_layout`).

---

## Promotion gate

v6 replaces v5 in production ONLY after ALL of:
1. Stage 2 parity complete (or confirmed upstream-native).
2. Positive post-reboot operator bench vs v5 (quality + speed via canonical recipe).
3. MTP / role validation.

Historical note: `verify_llama_cpp.sh` enforced `production-consolidated-v5` during this v6 staging window. That guard is superseded; the current guard enforces `production-consolidated-v7`.

---

## Dependency graph

```
Stage 1a (814e81782)  ─┐
Stage 1b (c159997e0)  ─┴─► v6 builds + functional verify  [DONE]
                              │
                              ▼
                        Stage 2 parity backlog
                        (each item: check upstream-native FIRST)
                              │
                              ▼
            Post-reboot NUMA topology bench (needs host reboot)
            + OpenMP-ON vs OpenMP-OFF(CCD) comparison
                              │
                              ▼
                    Promotion gate (3 conditions)
                              │
                              ▼
                  v6 replaces v5 in production
                  (bake winning topology into process_layout)
```

Independent operator-review items (can resolve in parallel, do not block the chain): CCD env-var cleanup vs OpenMP-OFF build; the 6 NEEDS-OPERATOR-REVIEW commits.

---

## Cross-cutting concerns

- **OpenMP build flag drives whether CCD code is live** — affects bench methodology (new ON/OFF dimension), `stack_env.py` env-var hygiene, and any future CPU1 work. This is the most load-bearing finding here.
- **Upstream-native overlap** — Stage 2 + several DEAD/REVIEW items may already exist in `f8cc15f16`; porting before checking risks reintroducing conflicts/dead code. Always diff against upstream first.
- **Production safety** — all v6 work is in the `/mnt/raid0/llm/llama.cpp-v6` worktree; production `/mnt/raid0/llm/llama.cpp` must stay untouched and on v5 until the promotion gate passes.
- **Measurement** — no t/s number from this work may gate a decision without the canonical recipe + operator approval; current host uptime makes absolutes throttle-suspect.
- **Registry/launch wiring** — promotion requires per-role `binary_path`/env updates in the orchestrator stack; coordinate with `process_layout` and the v5→v6 cutover.

---

## Reporting instructions

After any task here:
1. Append progress to `progress/2026-06/2026-06-19.md` (or current-day file).
2. Update the checkboxes in this handoff (Stage 2 / NEEDS-OPERATOR-REVIEW lists).
3. On bench completion: record numbers as observations with protocol-id (canonical recipe), n/reps, date, attestation ref. Do NOT inline raw t/s as decision-gating without the citation.
4. On promotion: update `verify_llama_cpp.sh` expectations and the orchestrator launch config; move this handoff toward `completed/` only when v6 is live + Stage 2 closed.
5. Index/cross-link edits to the master/sub-indices are owner-gated — do not edit indices without explicit operator approval.

---

## Key files / commands

- Worktree: `/mnt/raid0/llm/llama.cpp-v6` (branch `production-consolidated-v6`: `814e81782` Stage 1a, `c159997e0` Stage 1b)
- Build:
  ```bash
  cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_CUDA=OFF \
        -DGGML_OPENMP=ON -DLLAMA_CURL=OFF && \
  cmake --build build -j 96 --target llama-server
  ```
- Functional verify scripts: `/mnt/raid0/llm/tmp/v6_smoke.sh`, `/mnt/raid0/llm/tmp/v6_ccd_smoke.sh`
- Vestigial CCD env vars: `epyc-orchestrator/scripts/server/stack_env.py` (lines 67/99)
- Production guard: `verify_llama_cpp.sh` (keeps production on `production-consolidated-v5`)
- Triage source: this session's 107-commit triage (CORE / PARITY / DEAD / UPSTREAM-NATIVE)
- Related handoffs: `speculative-decoding-mtp-refresh.md`, `qwen-mtp-llamacpp-port.md`, `inference-research-index.md`, `inference-research-index.md`
- Related memory: `project_cpu1_software_levers_exhausted`, `feedback_verify_live_affinity_not_just_topology_hash`, `project_concurrent_split_throughput`, `project_dual_half_concurrency_negative`

---

## Live validation workflow (approved 2026-06-23, executing)

Approved full-auto plan to **prove v6 is more performant WITHOUT regressing production behavior**. Entirely in the `/mnt/raid0/llm/llama.cpp-v6` experimental worktree — **NO production push, NO reboot**. Host is at **26-day uptime** → all absolute t/s are throttle-suspect **observations**; conclusions rely on **same-session relative comparisons** (v6 opt-OFF vs opt-ON, v6 vs v5 baseline run in the same window, OpenMP-ON vs OpenMP-OFF), never cross-session absolutes.

Approved plan file: `/home/node/.claude/plans/fix-index-edits-and-cuddly-gadget.md`.

### Phases

- **Phase 1 — Correctness + no-regression + reboot-assessment (single-instance).** Smallest→largest on v6 **OpenMP-ON**: Qwen3.5-9B → gemma-4-26B-A4B → gemma-4-31B → Qwen3.6-35B-A3B → Qwen3-Next-80B → Qwen3.5-122B. Per model:
  - loads on the new framework + produces correct output;
  - opt-OFF vs opt-ON (`GGML_Q8_0_8X8`) **byte-identical**;
  - llama-bench t/s vs the v5 baseline.
  - **Reboot-assessment**: if v6 ≥ v5 (within ≥−3%) → **no reboot needed**; if v6 is **>8% below** the tripwire → **HALT for operator** (reboot signal).
- **Phase 2 — CCD (OpenMP-OFF build).** Build a `GGML_OPENMP=OFF` variant (activates the `#ifndef GGML_USE_OPENMP` custom-pool CCD path), measure vs OpenMP-ON. **Activate only if ≥+3% with no regression.**
- **Phase 3 — NUMA topology bench.** `{9B, 31B} × {baseline, MTP} × {quarter / half / full}`. **Phase A** single-instance (latency), **Phase B** intentional concurrent (4×quarter / 2×half / 1×full, aggregate t/s).
- **Phase 4 — Stage 2 parity** (paged-attn, KV-compaction, Hadamard, IMROPE). Check **upstream-native first**; port only what is genuinely missing AND deployed.
- **Phase 5 — gemma-MTP consolidation onto v6.** Re-convert the assistant head `gemma4_mtp` → `gemma4_assistant`; if v6 ≥ ik_llama.cpp AND correct → **retire the second kernel**.
- **Phase 6 — synthesis.**

### Guardrails (verbatim)

- **(a) Experimental-only.** All work in `/mnt/raid0/llm/llama.cpp-v6`; the production worktree `/mnt/raid0/llm/llama.cpp` stays untouched on `production-consolidated-v5` (`verify_llama_cpp.sh` enforces). **No promotion** in this workflow.
- **(b) Host-ownership, not "sequential-only".** Confirm there is **no FOREIGN inference** running before each measurement window — but **Phase-3B concurrency is intentional and mine** (it is the experiment, not a contention bug).
- **(c) EVERY speed number is paired with an output-correctness + opt-on-vs-opt-off bit-exact check — a fast-but-garbage config is discarded, not recorded (this has bitten us before).**
- **(d) Speed via standalone `llama-bench`** + `/completion` for MTP, **never `run_benchmark.py`**.

### Halt-gates

- Model **load-fail or regression** vs v5.
- **opt-ON ≠ opt-OFF** (not bit-exact) → kernel bug.
- v6 **materially below v5** (reboot signal; >8% below tripwire in Phase 1).

---

## Execution status / results (updating)

> **2026-06-26 v6 cutover — SUPERSEDES the 2026-06-25 "do NOT cut the gemma worker to v6" verdict.** The reason that verdict held (v6 was ~25-34% slower than ik_llama on the gemma worker, the IK-KERNEL-FINDING below) has been overturned by the **iqk-port** result: ik's `iqk_mul_mat` AVX-512 GEMM kernels are now merged onto `production-consolidated-v6` (runtime-gated `GGML_IQK=1`), and same-window the v6+iqk worker now **BEATS** ik_llama by **+11%** (gemma-26B MTP draft=2, chat: v6-iqk+Q8head 42.78 t/s @ accept 0.80 vs ik_llama PR#1744 38.63 @ 0.66 — see `iqk-port.md`). The gemma worker IS therefore being consolidated onto v6 in the **2026-06-26 cutover**; ik_llama.cpp is FULLY DEPRECATED (no second binary). Registry/launcher/governance config converged (no-inference gates green, 174 promotion-gate tests pass), canonical binary built; **live throughput + garbage verification PENDING (operator deploy gate)**. Tracking: `handoffs/active/v6-iqk-promotion.md`.

**STANDING VERDICT (final, v6 = branch `production-consolidated-v6`, worktree `/mnt/raid0/llm/llama.cpp-v6`, HEAD `a4e2b4f86`):** v6 = clean upstream `origin/master` + 3 validated functional ports. **F5✅ F6✅ F2/F3✅ (all validated); F1✅ RESOLVED + verified (branch `f1-paged-attn` HEAD `112022a0b` — see F1-RESOLUTION note below; ready to fold into v6). Forward-ported CPU kernels DEPRECATED (reverted as dead-weight). gemma MTP-consolidation CORRECT-but-SLOWER 2026-06-25 (works on v6, but ~25-34% slower than ik_llama — see IK-KERNEL-FINDING; ~~do NOT cut the gemma worker to v6~~ — SUPERSEDED 2026-06-26 by the iqk-port: v6+iqk now beats ik +11%, gemma worker IS being cut to v6, see cutover note above).** v6's speed lead over v5 (122B +34%, 35B +18%) is from the UPSTREAM framework (op-fusion, GDN cplan fix), NOT our kernels.

**IK-KERNEL-FINDING (2026-06-25) — ik_llama is ~18-30% faster than v6/mainline for CPU quantized decode, GENERALLY (not gemma-specific).** Same-host same-window single-stream no-MTP /completion (CODING prompt; OBSERVATIONS, not canonical bench): Qwen3.6-35B-A3B Q8 **non-gemma** v6 25.75 → ik 33.14 (+29%); gemma-4-26B-A4B Q4_K_M MoE v6 37.86 → ik 49.28 (+30%); gemma-4-31B Q4_K_M **dense** v6 7.31 → ik 8.59 (+18%); gemma MTP Q4_K_M v6 n4 63.0 vs ik dm4 84.5 (+34% — but the gap is the KERNEL not MTP: no-MTP base already +30%). Cause: ik's `iqk_mul_mat` (`ggml/src/iqk/`, ~38K LOC incl. `iqk_gemm_kquants.cpp` ~5K Q4_K AVX-512 GEMM + fused-MoE + row-interleave); v6/mainline has NO `iqk/`. Our deprecated Q8_0 8x8 kernel was the PARTIAL version. **v6's value is the FRAMEWORK (new models, native MTP, GDN fix), NOT kernels.** Strategic options: (1) switch primary engine to ik (loses v6 framework/features + single-maintainer cadence); (2) **PORT iqk into v6** = best-of-both, ~20-30% stack-wide prize, license-clean — RECOMMENDED pending feasibility (mainline ggml diverged from ik's base → real integration work); (3) hybrid status-quo (two kernels). **Immediate:** keep ik for the gemma worker. Detail: [[project_ik_llama_iqk_kernel_advantage]]. Also measured: **paged-attn (F1) single-stream overhead is NEUTRAL** (Qwen3.6-35B Q8: off 25.75 → on 25.60, −0.6%); concurrent -np 8 paged A/B needs a clean redo (bench `wait`-hang bug).

**GEMMA-MTP-RESOLUTION (2026-06-25) — gemma-4 MTP works on v6; ik_llama worker dependency retireable.** Two root-causes, both now solved:
1. **Lineage mismatch (the 0%-accept / "de de de" cause):** the v6-format assistant head (`gemma-4-26B-A4B-it-assistant-v6-f16.gguf`, `gemma4-assistant` arch, `embedding_length_out=2816`) had been paired with the **unsloth-QAT** base (different-lineage weights → head projections don't match → 0% draft acceptance). FIX: self-convert the **original** `google/gemma-4-26B-A4B-it` base (lineage-matched to the head). Downloaded (52GB safetensors, integrity-verified: 1013 tensors, exact sizes) + converted via `conversion/gemma.py` with the delta-Mem venv → `/mnt/raid0/llm/models/gemma-4-26B-A4B-it-ORIG-Q8_0.gguf` (26.9GB, 658 tensors). Metadata byte-identical to the working unsloth base (same rope_freqs tensor; the `Unknown RoPE type: proportional` convert warning is BENIGN — the gemma-specific `generate_extra_tensors` writes the correct ROPE_FREQS).
2. **Test-method artifact (the "still garbage" red herring):** gemma-4-26B-A4B-it is **instruct-tuned** — raw `/completion` degenerates ("ifying-ifying"). With the proper chat template (`--jinja` `/v1/chat/completions`) the base is coherent ("capital of France is Paris"; correct Rayleigh-scattering explanation).
**VERDICT (chat-template, original base + matched head, `--spec-type draft-mtp --spec-draft-n-max 3`):** coherent correct output + **draft acceptance 0.59–0.72** (was 0%), mean accept length 2.7–3.1, **37–42 t/s** (q8_0). gemma MTP is functional on v6 → the worker no longer architecturally requires ik_llama.
**Worker cutover recipe:** base `gemma-4-26B-A4B-it-ORIG` (make Q4_K_M for prod via `llama-quantize`), draft `…-assistant-v6-f16.gguf`, flags `--spec-type draft-mtp -md <head> --spec-draft-n-max 3 -fa on -ctk q8_0 -ctv q8_0 -np 1 -ub 512 --no-mmap --jinja`. **t/s-parity FOLLOW-UP (before actual prod cutover):** bench Q4_K_M base + swept draft-n-max vs the ik_llama 60.7 baseline apples-to-apples (this q8_0/n-max=3 number is not directly comparable). Cutover rides the overall v6 promotion gate (out of scope this session).

**F1-RESOLUTION (2026-06-24) — paged-attn was NEVER broken; the "never activates" symptom was a false alarm.** Deep debug on branch `f1-paged-attn` (worktree `/mnt/raid0/llm/llama.cpp-v6-f1`) proved the full path works. Root cause of the symptom: the activation confirmation line was `LLAMA_LOG_INFO`, which is **filtered during context creation** → the only operator-visible signal of activation never printed, making a working path look inert. ERROR-level bisect probes (since removed) + an op-dispatch probe established the chain end-to-end:
- **Plain attention (Qwen3.6-35B-A3B Q8_0):** `enable_blocks(512)` called → `GGML_OP_FLASH_ATTN_EXT_PAGED` forward dispatched during decode → output correct AND **byte-identical to paged-off** (greedy, seed 42).
- **SWA/iswa (gemma-4-31B Q4_K_M):** activation WARN fires ×2 (base + SWA inner caches) → paged op dispatched on the iswa graph → output correct. (This path also needed a genuine code fix: the iswa graph was never wired for the block table — fixed in `ea50522a7` by the parallel agent.)
- **Hybrid (Qwen3.5-9B):** activation confirmed on the inner attn cache.

Two real fixes are on the branch (none functional-to-correctness-affecting for the off-by-default path): `ea50522a7` (iswa graph block-table wiring + `--paged-attn` CLI example-gating + WARN-on-bad-env) and `112022a0b` (promote activation log INFO→WARN so it is visible at the default level). Paged-attn is **opt-in, off by default** (`LLAMA_PAGED_ATTN=<blocksize>` / `--paged-attn`), bit-exact vs non-paged → safe to fold into v6. Not currently deployed by any production role, so folding it in is inert until explicitly enabled.

**KERNEL DEPRECATION (done):** reverted Stage 1a (repack kernels, `358f0c748`) + Stage 1b (CCD, `7c88df85a`). Rationale (all measured): Q8_0 AVX-512BW kernel neutral@24t / −9%@96t + not byte-exact; CCD broken (OpenMP-OFF garbles with quantized KV via broken Hadamard-FWHT-on-custom-pool, on BOTH dense and MoE) + never engages; CPU_REPACK NUMA mbind neutral-to-negative (35B 27.5 on / 28.4 off, 31B 11.4 / 11.7). Clean v6 rebuilt + decode-verified.

Scaffold for the executor to fill as phases complete. v5 baselines below are **observations** (throttle-suspect; for same-session relative comparison only).

Known v5 baselines (t/s):
- gemma-4-26B-A4B: 44.7 (baseline) / 60.7 (MTP)
- Qwen3.6-35B-A3B Q8: 24.3
- Qwen3.5-122B: 12.19
- Qwen3-Next-80B: 14.4–20.8
- gemma-4-31B (dense): 6.87

v6 t/s shown as **llama-bench tg / completion** (single-instance, v6 OpenMP-ON build, host at **26-day uptime** → t/s are **throttle-suspect observations**). opt-off = deterministic reference; opt-on = `GGML_Q8_0_8X8` AVX-512BW kernel forced on.

| Phase | Model/Config | loads? | correct? | opt-off==opt-on bit-exact? | v6 t/s (tg / completion) | v5 baseline | verdict |
|-------|--------------|--------|----------|----------------------------|--------------------------|-------------|---------|
| 1 | Qwen3.5-9B Q4_K_M (dense, candidate) | yes | yes (prime list) | BIT-EXACT (Q8_0 kernel n/a on Q4 weights) | 30.1 / 16.1 | none | PASS |
| 1 | gemma-4-26B-A4B Q4_K_M (MoE, worker role) | yes | **NO — GARBAGE** ("DO NOT…OVERSIGHT-OVERSIGHT…" repetition) | n/a (both paths garble) | 52 bench but OUTPUT GARBAGE | 44.7 / 60.7 (ik_llama) | **BLOCKER** |
| 1 | gemma-4-31B Q4_K_M (dense) | yes | yes (prime list) | BIT-EXACT | 12.1 / 10.6 | 6.87 (SuperGemma31B) | PASS |
| 1 | Qwen3.6-35B-A3B Q8_0 (MoE, frontdoor/coder) | yes | yes | BIT-EXACT (Q8_0 kernel fully engaged) | 28.7 / 24.8 | 24.3 | PASS (v6 ≥ v5) |
| 1 | Qwen3-Next-80B-A3B Q4_K_M (SSM-MoE, ingest) | yes | yes (prime list) | BIT-EXACT | n/a (bench skipped, needs override-kv) / 30.1 | 14.4–20.8 | PASS |
| 1 | Qwen3.5-122B-A10B Q4_K_M (GDN, architect) | yes | yes (prime list) | opt-off DETERMINISTIC (4d58… ×2 @ n=200); opt-ON Q8_0-kernel DIVERGES (near-tie flip, output still correct) | 16.4 / 15.1 | 12.19 (canonical) | PASS opt-off; Q8_0 kernel non-byte-exact here |
| 2 | Qwen3.6-35B-A3B OpenMP-OFF (custom-pool ±CCD) | yes | **NO — GARBAGE** (server format-error → empty) | n/a | 30.5 tg but OUTPUT GARBAGE | OpenMP-ON 29.7 (correct) | CCD NOT viable; OpenMP-ON stays |
| 3A | 9B single-instance topology | yes | all OK | n/a (cross-topo differs by reduction order) | qtr 11.8 / half 15.1 / full 32.1 | — | full wins single-stream |
| 3A | gemma-31B single-instance topology | yes | all OK | n/a | qtr 3.1 / half 4.4 / full 12.4 | — | full wins single-stream |
| 3B | 9B CONCURRENT aggregate | yes | (per 3A) | n/a | 1×full 30.7 / 2×half 30.6 / **4×qtr 50.4** | — | **4×quarter +64%** |
| 3B | gemma-31B CONCURRENT aggregate | yes | (per 3A) | n/a | 1×full 12.1 / 2×half 10.2 / 4×qtr 10.2 | — | **1×full wins; quartering −16%** |
| 3-MTP | 9B MTP × topology | yes | all OK 87% accept | n/a | qtr 21.8(+85%) / half 24.9 / full 30.8(neutral) | — | MTP value inversely ∝ threads |
| Q8 | 35B Q8 OpenMP-ON, GGML_Q8_0_8X8 on vs off | yes | yes | not byte-exact | qtr 9.42/9.42 (±0%) / full 27.55→25.09 (−9%) | — | **DO NOT ENABLE — keep OFF** |
| CCD | dense 9B/31B OpenMP-OFF, quantized KV (`-ctk q8_0`) | yes | **NO — GARBAGE** | n/a | — | — | CCD-on-dense ALSO broken (Hadamard FWHT) |
| F5 | IMROPE 9B coherence at -c 768 (K-shift guard ported) | yes | yes (749 coherent tokens, no crash) | n/a | — | — | ✅ **DONE + VALIDATED `00fe78602`** |
| F6 | slot force-release: erase-during-generation cancel test | yes | yes (force-cancelled long gen at +6s; HTTP ERROR "Slot erased while processing (external timeout)"; no hang; server healthy after) | n/a | — | — | ✅ **DONE + BEHAVIORALLY VALIDATED `60c270203`** |
| F2/F3 | Expected-Attention KV-compaction: `action=compact` test | yes | yes (evicted 487/972 tokens, keep_ratio 0.5, pos_max_after 981; slot generated coherently "red, green, and blue…" — no KV corruption) | n/a | — | — | ✅ **DONE + BEHAVIORALLY VALIDATED `3f9df4bd3`** |
| F1 | paged-attn activation across 3 model types (hybrid 9B / SWA 31B / plain 35B) | compiles | **NON-FUNCTIONAL — never activates** (env-read at kv-cache.cpp:411 `LLAMA_PAGED_ATTN` doesn't fire at runtime — env confirmed in /proc/pid/environ but no "paged attention enabled" log; `--paged-attn` CLI flag rejected "invalid argument") | n/a | — | — | ⚠ **REVERTED `a4e2b4f86`** (cherry-picked `0e485a91b` then reverted); preserved on branch `f1-paged-attn` (`8c6393335`, worktree `/mnt/raid0/llm/llama.cpp-v6-f1`) |
| 5 | gemma-4-26B-A4B unsloth QAT GGUF `…-it-qat-UD-Q4_K_XL` (build 2026-06-05, post-#22804) | yes | yes (prime list + sum) | n/a | — | 44.7/60.7 (ik_llama) | ✅ **BASE-CONSOLIDATION UNBLOCKED** — v6 can serve the gemma-4-26B-A4B worker |
| 5 | gemma-4-26B-A4B v6refresh GGUF (repo `ae4d537a`, re-uploaded Apr-12) | yes | **NO — GARBAGE** ("MILES-AKT (AKT-100000…") | n/a | — | 44.7/60.7 (ik_llama) | superseded — Apr-12 GGUF still pre-#22804; use unsloth QAT 2026-06-05 |

- **Reboot-necessity verdict: NO REBOOT NEEDED.** v6 on the current (26-day-uptime) host meets or exceeds the v5 baselines (122B 16.4 vs 12.19 canonical; 35B 28.7 vs 24.3; 80B 30.1 vs 14.4–20.8). If throttle were crippling throughput we'd see ~half these — we don't. (Caveat: v6-vs-v5 not perfectly apples-to-apples on measurement context/config, but the direction is unambiguous: not throttle-limited.)
- **Key finding A (CORRECTED) — the gemma-4-26B-A4B garble is a STALE GGUF, not a v6 bug.** Mainline v6 fully supports gemma4-MoE (purpose-built, commit #22804 2026-05-08; `gemma4.cpp` has the complete MoE path). The on-disk Q4_K_M GGUF is a ggml-org PREVIEW dated 2026-04-04 — ~1 month older than mainline's working support — with stale-converter fingerprints (`add_bos_token=0`, no `tokenizer.ggml.pre`, no `general.name`). It loads (tensors/hparams match: `expert_count=128`, `used=8`) but mis-decodes numerically vs the finalized v6 graph → coherent-but-wrong "OVERSIGHT" repetition. (Also: the GGUF DOES embed a `chat_template` — the earlier "no chat_template" was wrong; irrelevant on raw /completion anyway.) FIX: re-fetch the current ggml-org gemma-4-26B-A4B-it-GGUF (local copy pinned to stale Apr-4 commit `4006d4d9`) → v6 decode smoke → if correct, consolidate the worker off ik_llama. No HF base safetensors on disk (re-convert path would need a ~52GB gated download). Keep ik_llama as the fallback meanwhile.
- **Key finding B — Q8_0 AVX-512BW kernel is distribution-preserving, NOT strictly byte-exact:** bit-exact on the 35B (pure Q8_0) but flipped a greedy near-tie on the 122B (correct output, last-bit FP diff). Off by default (no role sets GGML_Q8_0_8X8). Enabling it for speed carries the same near-tie caveat as MTP — operator decision.
- **Q8_0 AVX-512BW kernel — DO NOT ENABLE (decided).** Measured OpenMP-ON, 35B Q8: quarter(24t) off 9.42 / on 9.42 (±0%); full(96t) off 27.55 / on 25.09 (**−9%**). No speed gain at our operating points + not byte-exact → keep `GGML_Q8_0_8X8` **OFF** (the v6 default). **Meta-finding:** v6's speed advantage over v5 (122B +34%, 35B +18%) comes from **UPSTREAM framework improvements** (op-fusion, GDN cplan fix), **NOT** our forward-ported kernels (Q8_0 GEMV is neutral/negative; CCD is broken). The ported kernels are inert-but-harmless.
- **CCD-on-dense (answers the prior open question): ALSO broken.** OpenMP-OFF garbles whenever KV is quantized (`-ctk q8_0`) — root cause is v6's auto-enabled Hadamard FWHT being broken on the non-OpenMP custom-pool — affecting **BOTH dense (9B/31B garbled) and MoE**. (The earlier "9B dense OpenMP-OFF correct" result was with f16 KV / Hadamard-off.) CCD verdict is now airtight: **OpenMP-ON only.**
- **F5 (IMROPE K-shift guard) — PORTED + VALIDATED** (v6 branch `00fe78602`): drops the `n_pos_per_embd` asserts in `seq_add`/`seq_div` + the `get_can_shift` `n_pos_per_embd>1` guard (keeps STEP35). Builds; IMROPE 9B context-shift coherent at `-c 768` (749 coherent tokens, no crash). Recommended deeper validation: the architect chunk-reuse K-shift scenario (remaining).
- **F6 (slot force-release) — PORTED + BEHAVIORALLY VALIDATED** (v6 branch `60c270203`): erase-during-generation at +6s force-cancelled the long gen (returned at +6s, not full run); HTTP got ERROR "Slot erased while processing (external timeout)" (no hang); server healthy after; logs confirm force-release + send_error. Skipped v5's `--slot-save-path` route-ungate (prod always sets it).
- **F2/F3 (Expected-Attention KV-compaction) — PORTED + BEHAVIORALLY VALIDATED** (v6 branch `3f9df4bd3`): `action=compact` evicted 487/972 tokens (keep_ratio 0.5, pos_max_after 981); slot generated coherently afterward ("red, green, and blue…") — no KV corruption. The knorm legacy scorer was deliberately NOT ported (depends on v5 AM state-serialization layout incompatible with v6 KV state format; EA is the autopilot's production default). Behavioral validation done (NOT deferred).
- **F1 (paged-attn) — REVERTED, NOT in v6** (cherry-picked `0e485a91b` then reverted at HEAD `a4e2b4f86`): compiles but NON-FUNCTIONAL. Behavioral validation across 3 model types (hybrid Qwen3.5-9B, SWA gemma-4-31B, plain Qwen3.6-35B) showed paged-attn NEVER activates — the env-read at `kv-cache.cpp:411` (`LLAMA_PAGED_ATTN`) doesn't fire at runtime (env confirmed in `/proc/<pid>/environ` but no "paged attention enabled" log) AND the `--paged-attn` CLI flag is rejected by llama-server ("invalid argument"). Following the clean-base principle, reverted from v6; work is PRESERVED on branch `f1-paged-attn` (commit `8c6393335`, worktree `/mnt/raid0/llm/llama.cpp-v6-f1`). FOLLOW-UP: debug the activation wiring (why the kv-cache ctor env-read doesn't execute / fix CLI arg registration) + runtime A/B correctness on the actual paged-attn target models before it can be added back.
- **CCD verdict: NOT VIABLE on v6 → OpenMP-ON stays.** Measured (Phase 2): the OpenMP-OFF custom-pthread-pool build — the only build where the `#ifndef GGML_USE_OPENMP` CCD code compiles in — produces GARBAGE on production MoE models (Qwen3.6-35B-A3B garbles on OpenMP-OFF both bare-custom-pool AND +CCD-env; 9B dense is correct on OpenMP-OFF). Additionally the CCD init never engages via the llama-server threadpool path (no `[GGML_CCD_POOLS] enabled/disabling` log ever appears — upstream's framework creates threadpools outside the ported `ggml_threadpool_new_impl` CCD path). So CCD can neither be cleanly activated NOR safely used. This confirms by measurement what was inferred (the GGML_CCD_* env vars are vestigial): the CPU1 CCD optimization is dead on v6. OpenMP-ON is the production build. Root cause of the OpenMP-OFF MoE garbage (Stage-1b port vs upstream non-OpenMP MoE path) not pursued — low value since OpenMP-ON works; flag for future only if CCD is ever revisited.
- **NUMA topology winner: model-size-dependent.** Single-stream latency → 1×full (all sizes). Concurrent throughput → 4×quarter for SMALL models (9B +64%; halves never win), but 1×full for LARGE dense (31B: quartering HURTS −16%, severe BW contention). MTP speedup inversely ∝ thread count (quarter +85%, full neutral) → MTP pairs with quartering. Projected champion for small-model serving = 4×quarter+MTP (concurrent 4×quarter-MTP aggregate = top unrun follow-up). Matches + validates production's existing strategy (quarter the small-active roles, full for the 122B architect).
- **gemma consolidation: UNBLOCKED (base path).** The unsloth QAT GGUF `gemma-4-26B-A4B-it-qat-UD-Q4_K_XL` (build 2026-06-05, post-#22804 / May-8; downloaded to `/mnt/raid0/llm/models/gemma-4-26B-A4B-it-Q4_K_M-current.gguf`, sha256-verified) **DECODES CORRECTLY on v6** (prime list + sum). So v6 CAN serve the gemma-4-26B-A4B worker → **ik_llama retirement is viable for the base path.** REMAINING for full worker consolidation: gemma MTP (spec-dec) on v6's mainline `gemma4_assistant` #23398 path (assistant head in mainline format + verify). NOTE: an HF token exists (`/mnt/raid0/llm/cache/huggingface/token`) and `google/gemma-4-26B-A4B-it` is no longer gated, so a true Q4_K_M self-convert is also possible. The stale Apr-4 ggml-org GGUF (and the Apr-12 refresh, `-v6refresh.gguf`, repo `ae4d537a`) both garbled ("MILES-AKT (AKT-100000…", both pre-#22804) — only the 2026-06-05 unsloth QAT works. (The `-v6refresh.gguf` is a 16.8GB dead artifact on disk — operator may delete.)

## Stage-2 parity port backlog

From the Phase-4 audit (check each against upstream-native FIRST):

- **PORTED + VALIDATED (3):**
  - **IMROPE K-shift guard relaxation** (F5, `00fe78602`).
  - **Slot force-release** (F6, `60c270203`).
  - **Expected-Attention KV-compaction** (F2/F3, `3f9df4bd3`) — knorm legacy scorer deliberately NOT ported (v5 AM state-serialization layout incompatible with v6 KV state format; EA is the autopilot production default).
- **REVERTED — NOT in v6:**
  - **Paged attention** (F1) — cherry-picked `0e485a91b` then reverted (`a4e2b4f86`); compiles but activation broken (never fires). Preserved on branch `f1-paged-attn` (`8c6393335`, worktree `/mnt/raid0/llm/llama.cpp-v6-f1`).
- **ALREADY-NATIVE (no port):** Hadamard KV — v6 auto-enables it on quantized KV; just drop `--kv-hadamard` from launches.

### Per-feature difficulty / status

- **F5 — IMROPE K-shift guard:** ✅ **DONE + VALIDATED incl. 122B deep validation (2026-06-24).** (`00fe78602`). IMROPE 9B context-shift at `-c 768` → 749 coherent tokens. **122B architect (qwen35moe, IMROPE n_pos_per_embd=4) deep validation**: forced a real overflow context-shift (`--context-shift -c 768`, prompt+gen=997 tok) → shift fired, F5 `seq_add` relaxation correctly let it proceed, **600 tokens coherent @ 13.65 t/s, no crash, server healthy — with f16 K**. **CAVEAT (new, NOT a F5 bug): with quantized K (`-ctk q4_0`, the architect's prod config) the same shift CRASHES** — `ggml_compute_forward_dup` aborts `ops.cpp:321: not implemented` (×96 threads) because the CPU dup op can't handle the q4_0 dup the rope-shift graph needs (classic quantized-K + shift limitation; CPU-backend gap, arch-independent). **Not a prod blocker as configured**: architect enables neither `--context-shift` nor `--cache-reuse` (both default-off; zero matches in orchestrator config). Workaround if shift/reuse is ever enabled for the architect: use **f16 K cache** (or implement the missing quantized dup path). Regression-vs-preexisting on v5 not separately tested (the dup limitation is in the shared CPU backend → almost certainly pre-existing).
- **F6 — slot force-release:** ✅ **DONE + BEHAVIORALLY VALIDATED** (`60c270203`). Hand-ported into the refactored `server-context.cpp` (v6 map :4547 gate / :2612-2618 defer / :5225 `handle_slots_erase`). Erase-during-generation force-cancelled the gen at +6s; HTTP ERROR "Slot erased while processing (external timeout)", no hang, server healthy after. (Skipped v5's `--slot-save-path` route-ungate — prod always sets it.)
- **F2/F3 — KV-compaction:** ✅ **DONE + BEHAVIORALLY VALIDATED** (`3f9df4bd3`). Expected-Attention `action=compact` evicted 487/972 tokens (keep_ratio 0.5, pos_max_after 981); slot generated coherently afterward — no KV corruption. knorm legacy scorer NOT ported (v5 AM state-serialization layout incompatible with v6 KV state format).
- **F1 — paged-attn:** ✅ **RESOLVED + VERIFIED (branch `f1-paged-attn` HEAD `112022a0b`).** The "never activates" report was a false alarm — the activation confirmation was an INFO log filtered during context creation. Runtime-verified end-to-end: plain attention (Qwen3.6-35B, op dispatched + byte-identical to paged-off) and SWA/iswa (gemma-4-31B, op dispatched ×caches + correct). Real fixes: `ea50522a7` (iswa graph block-table wiring — the genuine missing piece for SWA models — + CLI arg example-gating + WARN-on-bad-env) and `112022a0b` (INFO→WARN so activation is visible). Opt-in / off-by-default / bit-exact → ready to fold into v6. See **F1-RESOLUTION** note under Execution status. *(NOTE: the older "REVERTED / NON-FUNCTIONAL" prose elsewhere in this doc is superseded as-of-investigation history.)*

### Remaining items

- [x] ~~**F1 paged-attn** — activation-fix + runtime A/B follow-up~~ ✅ **RESOLVED 2026-06-24** (branch `f1-paged-attn` `112022a0b`; verified plain + SWA paths, bit-exact). Optional next: fold the branch into `production-consolidated-v6` (low-risk, off-by-default).
- [x] ~~**gemma MTP-on-v6 verify**~~ ✅ **CORRECT but SLOWER 2026-06-25** — original base self-convert + matched head → coherent (chat) + accept 0.59–0.72. BUT same-window Q4_K_M MTP: v6 n4 **63.0** vs ik_llama dm4 **84.5** t/s → cutting the gemma worker to v6 was a **~25-34% regression**. ~~KEEP ik_llama for the gemma worker.~~ Root cause = ik's iqk kernels (see IK-KERNEL-FINDING), not MTP. **RESOLVED / SUPERSEDED 2026-06-26: the iqk kernels are now PORTED onto production-consolidated-v6 (`GGML_IQK=1`); same-window v6-iqk worker now BEATS ik_llama +11% → the gemma worker IS being cut to v6 in the 2026-06-26 cutover (config converged + committed, live verification pending). See `iqk-port.md` + `v6-iqk-promotion.md`.**
- [~] **(NEW, strategic) iqk-kernel port into v6** — SCOPED 2026-06-25 = **GO (MODERATE-ADAPTATION, leaning easy)**. Prize (canonical llama-bench, same-GGUF): decode +15-36%, **prefill +53-148%** (Qwen3.6-35B Q8 ~2.5×), general across families. Feasibility (gitnexus-assisted): ik `block_q4_K`/`block_q8_0` BYTE-IDENTICAL to v6 (zero-conversion reads); REPACK-FREE (sidesteps the x86_kquant_repack blocker); ~40-line hook at `ggml-cpu/ggml-cpu.c:1245` `ggml_compute_forward_mul_mat`; no CMake change (-march=native gives AVX512 macros); vendor iqk gemm files + `quantize_row_q8_2_x4` + `block_q8_2`. **Stage-1 (dense Q4_K/Q8_0, flag-gated `GGML_USE_IQK_MULMAT=OFF`): 3-5 person-days, single PR.** Stage-2 (MoE `mul_mat_id` — needed for our MoE stack's expert GEMMs + Q5_K/Q6_K): +3-5d. NOT bit-exact (Q8_2_X4 vs v6 Q8_K activation) → validate cosine-sim/max-abs-err vs F32 ref + eval parity, NOT bitwise. Detail: [[project_ik_llama_iqk_kernel_advantage]]. ~~**AWAITING operator greenlight to implement**~~ ✅ **DONE 2026-06-25 → CUT OVER 2026-06-26.** Greenlit + implemented: Stage 1 (dense Q4_K/Q8_0) + Stage 2 (MoE `mul_mat_id`, all 3 stack quant patterns) COMPLETE + verified on branch `iqk-port` (worktree `/mnt/raid0/llm/llama.cpp-v6-iqk`), prefill +22.5–49%, decode +7.9–8.8% (Q4_K), correct/crash-free. Merged onto production-consolidated-v6 for the 2026-06-26 v6+iqk cutover (config converged + committed; eval-suite parity = operator deploy gate). Detail: `handoffs/completed/iqk-port.md`, `handoffs/active/v6-iqk-promotion.md`.
- [x] ~~**architect chunk-reuse K-shift deeper validation**~~ ✅ **DONE 2026-06-24**: 122B context-shift validated — F5 holds, runs coherently with **f16 K**; quantized-K (`q4_0`) shift crashes (`forward_dup` CPU gap, not a prod path). See F5 entry above. Optional follow-up: implement the quantized-K dup path OR confirm v5 has the same limitation if the architect ever needs shift/reuse with q4_0 K.
