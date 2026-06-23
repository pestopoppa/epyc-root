# llama.cpp v6 Consolidation — production-consolidated-v6

**Status**: Stage 1 DONE + functionally verified (committed, NOT promoted). Stage 2 parity backlog + post-reboot bench gate the promotion.
**Last updated**: 2026-06-19

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

- [ ] **Paged attention** (`GGML_OP_FLASH_ATTN_EXT_PAGED` + `ops.cpp` impl + `ggml.h` enum/OP_COUNT) — commits `6843e1274..18b2ebfde`. CHECK upstream native flash-attn first (may be UPSTREAM-NATIVE now).
- [ ] **KV compaction stack** — Attention-Matching (`f1cf9bd9f` / `042ca88b1` / `45b4849ac`) + Expected-Attention (`894e048e3`, the deployed default compactor) — `src/llama-graph.cpp`, server integration.
- [ ] **Hadamard KV smoothing** (`ea6ab859c`, production config) — CHECK upstream #21038. The Hadamard FWHT hint IS already in v6 via upstream → may be PARITY-already-present.
- [ ] **IMROPE seq_add/seq_div + K-shift** for qwen35moe hybrids (`935e9bbbd`) — required for the deployed Qwen3.5 hybrid (architect).
- [ ] **Server slot management** (`55fa088e8` / `ffcb1baf4`).

---

## Triage classification of the 107-commit fork

### DEAD — do NOT port (~54 commits)
TIDE early-exit (deprecated dead-end), CPU15 EP (closed), slot-promotion (shelved), NUMA_WEIGHTS family (hard-stripped in v5), op-fusion (reverted; upstream has its own), CPU22 work-stealing (gate-failed), `RMS_NORM_PARALLEL` / `GDN_K_PER_HEAD` (stripped), MoE-Spec (default-off), Lightning / ring-linear (not deployed).

### UPSTREAM-NATIVE — drop (~4 commits)
MTP bench tooling, tree/DySpec speculation, fail-closed-spec, tree-spec capacity fix. Upstream ships native MTP / spec / EAGLE3.

### NEEDS-OPERATOR-REVIEW (6)
- [ ] SWA slot-reuse fixes (`d1c72d7fc` / `603702769`) — verify vs upstream SWA before drop.
- [ ] `--moe-n-expert` Hard-Mask CLI tool (`86901388a`).
- [ ] Differential-Transformer-V2 arch (`36ceed44d` / `23973ea66`) — eval-gated, not in deployed registry.
- [ ] Streaming KV context-shift controls (`632ce0f92`).
- [ ] Paged-attn upstream-overlap.

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

`verify_llama_cpp.sh` enforces production stays on `production-consolidated-v5` until then.

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
- Related handoffs: `speculative-decoding-mtp-refresh.md`, `qwen-mtp-llamacpp-port.md`, `inference-acceleration-index.md`, `cpu-inference-optimization-index.md`
- Related memory: `project_cpu1_software_levers_exhausted`, `feedback_verify_live_affinity_not_just_topology_hash`, `project_concurrent_split_throughput`, `project_dual_half_concurrency_negative`
