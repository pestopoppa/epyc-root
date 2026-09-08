# Champion maximum-performance sweep — Qwen3.8-27B-Q8_0 on MI210, 2026-09-08

**Status: CANONICAL. Cite this file; do not re-derive, and do not re-type the recipe.**
This is the postable number for the consolidated AutoKernel champion. Every figure below was measured in one
window on an otherwise idle host, with GPU residency **proven on every launch**.

> ## 79.25 tok/s single user · 179.12 tok/s aggregate at peak concurrency
> Qwen3.8-27B-Q8_0, MI210 (gfx90a, 64 GB), champion `ef81196d5`, DFlash2 speculative drafter.

---

## 1. The measurement

| slots (`np`) | aggregate tok/s | per slot | p95 dev across 3 launches | cv | runs |
|---:|---:|---:|---:|---:|---|
| **1** | **79.245** | 79.245 | **0.44%** | 0.222% | 79.200, 79.245, 79.594 |
| 2 | 109.408 | 54.704 | 1.60% | 0.891% | 109.408, 108.870, 111.154 |
| 4 | 167.759 | 41.940 | 3.33% | 1.897% | 167.759, 162.169, 169.667 |
| **8** | **179.122** | 22.390 | 1.82% | 1.005% | 182.381, 178.179, 179.122 |

Reported value is the **median of 3 launches** per point. `p95 dev` is `spread.p95_dev_pct` as computed by
`autokernel.loop.serving._spread` — the same statistic the serving floor is defined by.

### 1.1 Unit: **LAUNCH**

Every spread figure is **between-launch**. A fresh `llama-server` was started for each of the 12 samples. Do not
substitute an arm-unit or within-session floor for these numbers — that substitution is the 4-vs-4,780 error
(R23-55). A number quoted from this table without its unit is inadmissible.

### 1.2 What the curve says

- **`np=4` is the operating point.** Going 4 → 8 buys **+6.77% aggregate throughput** and costs **~47% of the
  per-user rate** (41.94 → 22.39 tok/s per slot). np=4 already delivers **93.7% of peak aggregate** while each
  user still sees ~42 tok/s. **The canonical recipe is already `np=4`; this measurement confirms that choice
  rather than changing it.**
- **Dispersion grows with concurrency** — 0.44% at np=1 against 3.33% at np=4, a **7.6× widening**. A single
  reading at np=4 is far less trustworthy than a single reading at np=1. Anything gated at np=4 must state its
  `n`. See `handoffs/active/autokernel-rebuild-program.md` → R23-61 for why an n=10 tail statistic is not fit
  for gating.
- **This is not a baseline comparison.** No production or pristine arm was run. The question asked was only
  *how fast does the champion go, at its best, right now* — see §4 for why a champion-vs-production ratio for
  this configuration does not exist and must not be quoted.

---

## 2. Exact conditions

### 2.1 Build

| field | value |
|---|---|
| champion commit | `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce` (`ef81196d5`) |
| branch | `ak/champion/llama-cpp-0db32c06e3e5` — GPU tip `bff30cebe` + CPU champion3 `9c4f73e29`, everything folded |
| build dir | `/mnt/raid0/llm/tmp/build-fold-ef81196d5` (the FOLD-2 candidate build) |
| source dir | `/mnt/raid0/llm/tmp/fold-ef81196d5-src`, tree **clean** |
| `libllama-common.so.0.0.10301` | sha256 `51e26826d5c183451c3d77f664439ad283259c3887c6f49497e9b7d5de389b4b` |
| `llama-server` | sha256 `869effe5f5cda7f72bd78c8ee168a30f5878b3f32558cd0c02cd38a62a77db37` |
| cmake | `GGML_HIP=ON` · `AMDGPU_TARGETS=gfx90a` · `GGML_HIP_ROCWMMA_FATTN=ON` · `GGML_NATIVE=ON` |

### 2.2 Recipe — `qwen3.8-27b-q8-gpu-dflash2-np4`, only `np` varied

Canonical source of truth:
`epyc-inference-research` → `artifacts/serving-recipes/qwen3.8-27b-q8-gpu-dflash2-np4.json`
(schema `epyc.autokernel.canonical_recipe.v1`). **Import it; never transcribe it** — a recipe transcribed by
hand into a handoff is the PROD-1 failure mode, and it cost seven MTP arms to a flag that does not exist.

| field | value |
|---|---|
| model | `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` |
| device / `ngl` | `ROCm0` / `99` |
| spec decode | `draft-dflash`, drafter `/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf`, `ngld=99`, `draft_n_max=8` |
| `np` | **the swept axis** — 1, 2, 4, 8 (recipe default 4) |
| ctx / batch / ubatch | 16384 / 2048 / 2048 |
| threads · `cpu_list` | 8 · **`184-191`** (the GPU host threads; **not** 88-95) |
| KV cache | `ctk=f16`, `ctv=f16`, `fa=on`, `kv_unified=false` |
| sampling | `n_predict=384`, `temperature=0.0`, `top_p=0.95`, `top_k=1` |
| metric | `aggregate_tok_s` |
| extra flags | none |

**`GGML_NOHUGEPAGE_PROCESS` is NOT set, and must not be.** See §5.

Per-point `recipe_hash` (identity, not name — a floor or gate keyed by name is unverified):

| `np` | `recipe_hash` |
|---:|---|
| 1 | `68fe27f39db72087735b192d6c3ead7077a6c14a9efeb2da40710471f59dd1c3` |
| 2 | `776c4d1a32bd16ad3b650922623e09e9d430082b0c101280dbaf197a9c972871` |
| 4 | `30950a3dbe1b94887252dc4a7c32ba5bdd1ad98fa747db38c7800c1956df76bc` |
| 8 | `356f368576327094999ee7fa2b36a4f9e744f21f992d5c1fd8797abab60181cc` |

### 2.3 Host

Exclusive: the operator had serialised the two campaigns, INF-70 had released the host at 16:15:31Z, and the
GPU was idle apart from this sweep. Total wall clock 397.6 s (49.3 + 76.2 + 96.3 + 175.8 s).

---

## 3. Residency evidence — proven, not asserted

"I invoked the HIP build" is not evidence of a HIP run, and `ldd` cannot prove one: llama.cpp *dlopens*
`libggml-hip.so`. Residency here was **sampled DURING each launch** by `autokernel.loop.residency.Sampler`
(schema `epyc.autokernel.serving_residency.v1`), landed on the serving path by **R23-60** the same day
(research `f00d78be`, merged `657910f1`). The sampler **refuses a launch measured non-resident** — these
numbers could not have been produced by a CPU fallback.

| `np` | status | resident / proven | peak VRAM | median VRAM | KFD procs | samples | sclk | covers request phase |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | `proven` | 3/3 · 3/3 | 33.09 GiB | 33.09 GiB | 1 | 198 | 1700 MHz, stable | yes |
| 2 | `proven` | 3/3 · 3/3 | 34.46 GiB | 34.46 GiB | 1 | 305 | 1700 MHz, stable | yes |
| 4 | `proven` | 3/3 · 3/3 | 37.67 GiB | 37.23 GiB | 1 | 386 | 1700 MHz, stable | yes |
| 8 | `proven` | 3/3 · 3/3 | 43.05 GiB | 42.55 GiB | 1 | 703 | 1695–1700 MHz, **not flat** | yes |

Resident floor 1 GiB. **One caveat, recorded rather than smoothed:** at np=8 the sampler reported
`clock_stable: false` — sclk dipped to 1695 MHz against 1700 at every other point. A 0.3% clock excursion
cannot explain a 6.8% throughput difference, so it does not change the operating-point conclusion, but the
np=8 row is the one point in this table not taken at a flat clock.

---

## 4. What this number is NOT

**It is not a ratio against production, and no such ratio exists for this configuration.** Production v9 never
ran this lane. `artifacts/operator/ratify_v9_final_freeze_20260811.json` → `production_certification` records
`qwen36_27b_q8_dflash: lane_ineligible_acceptance_below_floor`, `dflash_kernel_capability: certified`, and
`dflash_lineup_enabled: false` — the drafter is compiled in and **deliberately not enabled** for the 27B.
Three independent reasons the denominator does not exist:

1. **Different model** — the key names **Qwen3.6**-27B. Qwen3.8-27B replaced it in production on 2026-08-20/21,
   nine days *after* the 2026-08-11 freeze.
2. **The frozen binary cannot load our drafter** — v9 rejects the DFlash2 GGUF outright
   (`wrong number of tensors; expected 81, got 58`). Production's ceiling for Qwen3.8-27B is **MTP self-draft**.
3. **The lane was disabled by decision**, not by omission.

> **The champion's advantage on this surface is partly a CAPABILITY, not a speed delta.**

If a champion-vs-production headline is ever wanted it must measure production **at its own best** — its own
`np` sweep, its own supported spec configuration — never by forcing production through the DFlash2 recipe,
which would report a capability gap as a speed gap. Tracked as **PROD-BASE-1** in
`handoffs/active/autokernel-champion-aggregate.md`.

**It is also not comparable to any `tg128` llama-bench figure.** `llama-bench` cannot do speculative decoding
at all, so `tg128` is a **bench proxy** that understates this serving rate by ~2.5× (31.0 vs 79.25 tok/s at
np=1). The `tg128` surface stays valid for **kernel-vs-kernel A/B** — where the drafter's absence cancels on
both arms — and is never an absolute headline.

---

## 5. The launch recipe is PER-SURFACE

`GGML_NOHUGEPAGE_PROCESS=1` (`prctl(PR_SET_THP_DISABLE)`) is **adopted on the CPU decode path** (CHAMP-2,
operator ruling 2026-09-08) and **must NOT be added to this GPU serving recipe**. The transfer test **R23-58**
ran on 2026-09-08 over 48 launches and returned a **bounded null** — T0/D0, `p95_dev` ratio OFF/ON 0.713
(p = 0.3159), the ON arm if anything slightly *wider*, with the mechanism proven to have fired (ON-arm
AnonHugePages 0.0% on every launch, `THP_enabled` read back correct 48/48).

| surface | `GGML_NOHUGEPAGE_PROCESS=1` |
|---|---|
| CPU decode | **ON — adopted** |
| GPU serving (this recipe) | **NOT SET — do not add** |

Do not confuse it with `GGML_NOHUGEPAGE` (the madvise, already on). The names are close enough to be
transcribed wrong, which is exactly the PROD-1 failure mode.

---

## 6. Provenance

| artifact | location |
|---|---|
| raw sweep | `/mnt/raid0/llm/tmp/maxperf-20260908/sweep.json`, `sweep.log`, `sweep.py` |
| promoted into git | `epyc-inference-research` commit `48a6f6f2` (`data/`) |
| R23-58 (the per-surface ruling) | `/mnt/raid0/llm/tmp/r2358-shim-serving-20260908/` — `PREREGISTRATION.md` sha256 `0a72a0256a0c897768ce396fa20e21f7b969b42e588d28ebb54db8cb04c59d01`, frozen 2026-09-08T16:35:38Z |
| owning handoff | `handoffs/active/autokernel-champion-aggregate.md` |
| harness | `autokernel.loop.serving.calibrate_floor`, `autokernel.loop.residency.Sampler` |

Measured by the `ak-rebuild-20260828` lane, 2026-09-08, GPU exclusive.
