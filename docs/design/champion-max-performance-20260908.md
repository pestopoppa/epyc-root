# Champion maximum-performance sweeps — MI210, 2026-09-08

**Status: CANONICAL. Cite this file; do not re-derive, and do not re-type the recipe.**
These are the postable numbers for the consolidated AutoKernel champion (`ef81196d5`), on **two models**,
both measured on an otherwise idle host with GPU residency **proven on every launch**.

> ## Qwen3.8-27B-Q8_0 (dense) — 79.25 tok/s single user · 179.12 tok/s aggregate at peak
> MI210 (gfx90a, 64 GB), champion `ef81196d5`, DFlash2 speculative drafter, peak at `np=8`.
>
> ## Qwen3.6-35B-A3B-MTP-Q8_0 (MoE) — 112.68 tok/s single user · 310.96 tok/s aggregate at 16 slots
> Same GPU, same champion, **MTP self-drafting** (no separate drafter). **The curve has NOT saturated at
> 16 slots** — this is the highest measured point, not the ceiling.

**The two models are not a kernel comparison.** They are two different architectures measured on one
kernel; see §7 for why the *larger* model is the *faster* one, and §6.4 for why each gets different
operating-point advice.

| | Qwen3.8-27B-Q8_0 | Qwen3.6-35B-A3B-MTP-Q8_0 |
|---|---:|---:|
| section | §1–§5 | §6 |
| architecture | dense (`qwen35`, 65 blocks, d=5120) | MoE (`qwen35moe`, 41 blocks, d=2048, 256 experts / 8 routed) |
| GGUF on disk | 27.05 GiB + 1.92 GiB drafter | **35.21 GiB**, no drafter file |
| speculative decode | DFlash2 external drafter, `draft_n_max=8` | **MTP self-draft**, `draft_n_max=4` |
| single user (`np=1`) | **79.25** tok/s (p95 dev 0.44%, n=3) | **112.68** tok/s (p95 dev **2.70%**, n=6) |
| best aggregate measured | **179.12** tok/s at `np=8` (**curve turns over**) | **310.96** tok/s at `np=16` (**still climbing**) |
| recommended operating point | `np=4` — 93.7% of peak, ~42 tok/s/user | `np=16` measured best; ~19 tok/s/user (see §6.4) |

---

## 1. The measurement — Qwen3.8-27B-Q8_0 (dense, DFlash2)

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

## 2. Exact conditions — Qwen3.8-27B

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

## 3. Residency evidence — proven, not asserted (Qwen3.8-27B)

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

## 4. What the 27B number is NOT

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

## 6. Second model — Qwen3.6-35B-A3B-MTP-Q8_0 (MoE, MTP self-draft)

Same champion binary, same GPU, same host discipline, measured 2026-09-08 **19:37:30Z – 20:14:00Z** on an idle
host (the GPU had been released; nothing else running). Recipe `qwen3.6-35b-a3b-q8-gpu-mtp` — **new**, added
in `epyc-inference-research` commit `c3e362a1` — with **only `np` varied**. 24 launches in total, **residency
`proven` on all 24**, 2,952 residency samples, sclk pinned at 1700 MHz and `clock_stable: true` at *every*
point. Total wall clock 736.8 s.

### 6.1 The measurement

| slots (`np`) | aggregate tok/s | per slot | p95 dev | cv | peak VRAM | launches | runs |
|---:|---:|---:|---:|---:|---:|---:|---|
| **1** | **112.676** | 112.676 | **2.696%** | 1.684% | 36.61 GiB | **6** | 112.96, 110.59, 112.39, 115.71, 110.21, 114.02 |
| 2 | 130.540 | 65.270 | 1.378% | 0.717% | 36.90 GiB | 3 | 128.74, 130.54, 130.87 |
| 4 | 189.575 | 47.394 | 1.128% | 0.559% | 37.50 GiB | 3 | 189.57, 189.37, 191.71 |
| 8 | 242.755 | 30.344 | 1.226% | 0.984% | 38.78 GiB | 3 | 239.88, 245.73, 242.75 |
| 12 | 268.120 | 22.343 | 1.877% | 1.446% | 40.16 GiB | 3 | 263.66, 273.15, 268.12 |
| **16** | **310.958** | 19.435 | 2.530% | 1.325% | 41.37 GiB | 3 | 318.83, 309.41, 310.96 |

Reported value is the **median of the launches** at each point. Unit is **LAUNCH**, exactly as in §1.1 — a
fresh `llama-server` per sample. `p95 dev` is `spread.p95_dev_pct` from `autokernel.loop.serving._spread`.

`np=1` was measured twice, independently: a first batch of 3 (median **111.412** tok/s, p95 dev 2.350%) and
then a second batch of 6 (the headline row). The two batches agree to **1.1%**, and both carry the same
`recipe_hash` `89556d8f…`.

### 6.2 The curve has NOT saturated, and the ceiling is UNMEASURED

| step | aggregate change |
|---|---:|
| 1 → 2 | +15.85% |
| 2 → 4 | +45.22% |
| 4 → 8 | **+28.05%** |
| 8 → 12 | +10.45% |
| 12 → 16 | **+15.98%** |

Two things follow, and both are recorded rather than smoothed:

- **The marginal gain is not monotonically decaying.** 12 → 16 (+15.98%) is *larger* than 8 → 12 (+10.45%).
  Given p95 deviations of 1.9% and 2.5% at those two points, the non-monotonicity is not itself a claim — but a
  curve whose last step is its second-largest is nowhere near the flattening that would justify calling `np=16`
  a peak.
- **Memory is not the constraint either.** Peak VRAM at `np=16` is **41.37 GiB of the card's 64 GiB**, and it
  grows only ~1.2 GiB per doubling above `np=4`. There is headroom for `np=24` and `np=32` by every visible
  measure.

> **310.96 tok/s at `np=16` is the HIGHEST MEASURED POINT, not the ceiling. Do not quote it as a maximum.**

The sweep was stopped here by operator instruction (*"lets stop here"*) after 24 and 32 slots were offered and
declined. The unmeasured tail is tracked as an open task in
`handoffs/active/autokernel-champion-aggregate.md` (**HEAD-3**), so the gap is a recorded decision, not an
oversight.

### 6.3 The `np=1` spread is a PROPERTY, not a small sample

The single-slot dispersion **did not tighten when the sample was doubled**:

| n | median tok/s | p95 dev | cv |
|---:|---:|---:|---:|
| 3 | 111.412 | 2.350% | 1.453% |
| **6** | **112.676** | **2.696%** | 1.684% |

More data made it *slightly wider*. Compare the 27B at the same slot count: **0.44%** p95 dev — a **6.1×**
difference on the same GPU, same binary, same window, same host state.

> **Any single-user headline for the 35B carries a ~2.7% between-launch dispersion.** State it. A 27B-grade
> ±0.5% precision is not available on this model at `np=1`, and quoting one implies a stability that was
> measured and is not there.

This is also why the headline for this model is `n=6` and not `n=3`: under `FLOOR-UNIT-1` a dispersion figure
is only usable with its `n`, and 2.696% at n=6 is the more honest of the two.

### 6.4 Operating point — DIFFERENT ADVICE PER MODEL

The two models do not share an operating point, and the difference is structural, not a tuning accident:

| | Qwen3.8-27B (dense) | Qwen3.6-35B-A3B (MoE) |
|---|---|---|
| shape of the curve | **turns over at 4 → 8** (+6.8% aggregate for ~half the per-user rate) | **still climbing at 16** (+16.0% on the last step) |
| recommended `np` | **4** — 93.7% of peak aggregate, ~42 tok/s per user | **16 of what was measured** — 311 aggregate, ~19 tok/s per user |
| the real tradeoff | already past the knee; more slots buy little | per-user rate is the binding cost, not throughput |
| dispersion at that point | 3.33% p95 dev | 2.53% p95 dev |

If the requirement is **per-user responsiveness**, the 35B's own `np=4` (47.4 tok/s per slot) still beats the
27B's `np=1` **and** its `np=4`, at 189.6 tok/s aggregate. If the requirement is **fleet throughput**, `np=16`
is the best measured configuration on this host and the curve says a larger one exists.

### 6.5 Exact conditions — Qwen3.6-35B-A3B

Canonical source of truth for the recipe:
`epyc-inference-research` → `artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json`
(schema `epyc.autokernel.canonical_recipe.v1`, added in `c3e362a1`). **Import it; never transcribe it.**

| field | value |
|---|---|
| champion | `ef81196d5`, build dir `/mnt/raid0/llm/tmp/build-fold-ef81196d5` — the same binary as §2.1 |
| model | `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (35.21 GiB) |
| device / `ngl` | `ROCm0` / `99` |
| spec decode | `draft-mtp`, `draft_n_max=4`, **no `drafter` key — the model drafts for itself** |
| `np` | **the swept axis** — 1, 2, 4, 8, 12, 16 (recipe default 4) |
| ctx / batch / ubatch | 16384 / 2048 / 2048 |
| threads · `cpu_list` | 8 · **`184-191`** (the GPU host threads; **not** 88-95) |
| KV cache | `ctk=f16`, `ctv=f16`, `fa=on`, `kv_unified=false` |
| sampling | `n_predict=384`, `temperature=0.0`, `top_p=0.95`, `top_k=1` |
| metric | `aggregate_tok_s` |
| extra flags | none — and `GGML_NOHUGEPAGE_PROCESS` is **NOT set** here either (§5) |

Per-point `recipe_hash` (identity, not name):

| `np` | `recipe_hash` |
|---:|---|
| 1 | `89556d8f43bda310f45d9a85b85b6d8d19ef1331fb88be530b8f007d3025a815` |
| 2 | `52942f58cf630606f03f3e1f9aae3618c50b0e68444e81f105d046f92d118901` |
| 4 | `773ea5a59aa9335170b5a2cd97027f55aabb35ef84f467d2470dcedcb8767fe4` |
| 8 | `8762bffd946a8bd51e1af30cbc6817869fd2e50b6d86f3c0385890688e65edcf` |
| 12 | `a28b951447d344e10f5f04224de63c4ace8b44d2fd9b942c08dac146106b7d51` |
| 16 | `a1191ee27f15e8677f857e595e4cf9f05f2f91103035364fd849d5ab3b6c1bf9` |

### 6.6 Residency — proven on all 24 launches

| `np` | status | resident / proven | peak VRAM | median VRAM | KFD procs | samples | sclk | covers request phase |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 (n=3) | `proven` | 3/3 · 3/3 | 36.74 GiB | 35.55 GiB | 1 | 211 | 1700 MHz, stable | yes |
| 1 (n=6) | `proven` | 6/6 · 6/6 | 36.61 GiB | 35.55 GiB | 1 | 375 | 1700 MHz, stable | yes |
| 2 | `proven` | 3/3 · 3/3 | 36.90 GiB | 36.89 GiB | 1 | 261 | 1700 MHz, stable | yes |
| 4 | `proven` | 3/3 · 3/3 | 37.50 GiB | 37.49 GiB | 1 | 325 | 1700 MHz, stable | yes |
| 8 | `proven` | 3/3 · 3/3 | 38.78 GiB | 38.77 GiB | 1 | 474 | 1700 MHz, stable | yes |
| 12 | `proven` | 3/3 · 3/3 | 40.16 GiB | 40.10 GiB | 1 | 611 | 1700 MHz, stable | yes |
| 16 | `proven` | 3/3 · 3/3 | 41.37 GiB | 41.36 GiB | 1 | 695 | 1700 MHz, stable | yes |

Unlike the 27B's `np=8` row, **every** point here was taken at a flat 1700 MHz clock.

---

## 7. Why the LARGER model is the FASTER one — this is ARCHITECTURE, not a kernel result

The 35B beats the 27B at both ends of the curve — **+42.2%** single-user (112.68 vs 79.25) and **+73.6%**
peak-to-peak aggregate (310.96 vs 179.12) — while being the bigger file on disk (35.21 GiB against 27.05 GiB,
or 28.97 GiB counting the 27B's DFlash2 drafter). **Nothing about that is a statement about the champion
kernel.** Both numbers came from the same binary.

The cause is in the GGUF metadata, and it is not subtle:

| | Qwen3.8-27B | Qwen3.6-35B-A3B |
|---|---|---|
| `general.architecture` | `qwen35` — **dense** | `qwen35moe` — **mixture of experts** |
| blocks | 65 | 41 |
| `embedding_length` | 5120 | **2048** |
| FFN width | `feed_forward_length` 17408, **every token through all of it** | `expert_feed_forward_length` 512 × **8 of 256 experts routed** + one shared expert of 512 |
| attention heads (q/kv) | 24 / 4 | 16 / 2 |

Decode is **weight-bandwidth-bound**: the rate is set by how many bytes of weights must be read to produce one
token, not by how many bytes the file occupies. The dense 27B reads essentially all of its 27 GiB every token.
The MoE 35B routes **8 of 256 experts** per token, so the great majority of its 35 GiB is resident in VRAM and
*not read* on any given token — its per-token weight traffic is a small fraction of its footprint, and it is
smaller in every other dimension too (half the embedding width, two-thirds the depth, half the KV heads).

> **Record this wherever the two numbers appear together: the 35B is faster because it is an MoE, not because
> the kernel is better on it.** A reader who takes "35B > 27B" as a kernel result will conclude the champion
> scales with model size, which is the opposite of true.

The same reasoning explains the concurrency curves in §6.4. A dense model saturates the memory system early,
so extra slots quickly stop buying throughput — the 27B turns over between 4 and 8. An MoE at low batch is
*not* bandwidth-saturated: extra concurrent tokens route to experts that are already being fetched, so batching
amortises the expert reads. That is why the 35B is still climbing at 16 slots and why its ceiling is somewhere
above the measurements we have.

### 7.1 A capability this unlocks — the 27B is ALSO MTP-capable

The 27B GGUF carries the MTP head tensors: `blk.64.nextn.eh_proj.weight`, `.enorm`, `.hnorm`,
`.shared_head_norm`, with `qwen35.nextn_predict_layers = 1` — the same shape the 35B has at `blk.40`. **The
27B can self-draft.** Until `c3e362a1` made `spec_decode.drafter` optional this was *inexpressible as a
recipe*, so it had never been measured through the loop.

That matters because **MTP self-draft is exactly what production supports for Qwen3.8-27B** (§4, reason 2:
frozen v9 cannot load the DFlash2 GGUF at all). A `qwen3.8-27b-q8-gpu-mtp` recipe is now writable, and it is
the missing denominator PROD-BASE-1 has been waiting for. Tracked in
`handoffs/active/autokernel-champion-aggregate.md`.

---

## 8. Provenance

| artifact | location |
|---|---|
| raw sweep, 27B | `/mnt/raid0/llm/tmp/maxperf-20260908/sweep.json`, `sweep.log`, `sweep.py` |
| raw sweep, 35B | `/mnt/raid0/llm/tmp/maxperf-35b-20260908/` — `sweep.json` (np 1,2,4,8), `sweep-hi.json` (np 12,16), `sweep-np1-n6.json` (np=1 at n=6), plus `.log`/`.py` for each |
| 35B recipe + the self-draft fix | `epyc-inference-research` commit `c3e362a1` (recipe JSON, `serving.py`, `test_selfdraft_recipe.py`) |
| promoted into git | `epyc-inference-research` commit `48a6f6f2` (`data/`) — **27B only; the 35B sweep is still in scratch and needs promoting** |
| R23-58 (the per-surface ruling) | `/mnt/raid0/llm/tmp/r2358-shim-serving-20260908/` — `PREREGISTRATION.md` sha256 `0a72a0256a0c897768ce396fa20e21f7b969b42e588d28ebb54db8cb04c59d01`, frozen 2026-09-08T16:35:38Z |
| owning handoff | `handoffs/active/autokernel-champion-aggregate.md` |
| harness | `autokernel.loop.serving.calibrate_floor`, `autokernel.loop.residency.Sampler` |

Measured by the `ak-rebuild-20260828` lane, 2026-09-08, GPU exclusive.
27B sweep 17:17:50-17:24:28Z; 35B sweep 19:37:30-20:14:00Z (both windows from the residency sampler).
