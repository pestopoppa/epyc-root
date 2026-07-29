# v7 Stack Throughput — Full-Optimization Reference

> **⚠ READ FIRST — provenance/governance.**
> - **Kernel: `production-consolidated-v7` at frozen candidate `6ad45fa3ff` / binary `10098`.** The 2026-07-20 production cutover is complete; the table below still mixes production CPU-lane facts with pre-promotion experimental MI210 observations where marked.
> - **Most MI210 numbers remain OBSERVATION-grade** until the ratified `P-GPU-1` certification reruns on `production-consolidated-v7`.
> - **The live production stack remains CPU-role deployed unless a serving handoff explicitly says otherwise.** MI210 columns are BENCHMARKS / residency *candidates* (Gate-R), NOT live deployments.
> - "CPU opt" = the deployed CPU lane at its fastest validated config (native NEXTN-MTP / composed spec-dec + OMP/quant/context tuning), **not** a no-spec regression baseline.

## Table

| Role | Model / Quant | Spec-dec | **CPU opt t/s** (deployed lane) | MI210 bench t/s (candidate, NOT live) | Fits 64 GB? | 2K/8K/32K | Quality |
|---|---|---|---|---|---|---|---|
| **frontdoor** *(CPU-deployed)* | Qwen3.6-35B-A3B / Q8_0 | native NEXTN-MTP | **~34.5** (prod `draft-mtp`) — *the 21.6/17.1/10.2 is no-spec fallback, not this* | 119.7–122.8 (Gate-R bench) | ✅ ~36 GB | CPU-MTP curve **not measured on v7** (gap); GPU-MTP 123.6/119.7/105.2 | K5-clean |
| **worker** (general/math/toolrunner) *(CPU-deployed)* | gemma-4-26B-A4B / Q4_K_M + Q8 draft | `ngram-mod,draft-mtp` d=2 | **126.2 / 96.7 / 82.9** | single-slot ~158, but GPU free-form **quality-blocked** (K11.1) | ✅ (CPU-deployed) | short-prompt peak 175.8/110.0/97.6 | K5 +0.0% (live) |
| **architect** *(CPU-only)* | Qwen3.5-122B / UD-Q4_K_M (73 GiB) | native NEXTN, `-np 2` | **23.5 / 20.7** | — **Q4 does NOT fit 64 GB**. Research IQ2_M (37.6 GB) benches 43.7 single / 148 agg | ❌ (Q4). IQ2_M is a quality-traded research variant | >8K exceeds `-np2 -c16384` slot; ≥32K not measured (gap) | prod |
| **ingest** *(CPU-deployed)* | Qwen3-Next-80B-A3B / Q4_K_M (46 G) | none (default experts) | **20.5 / 15.9 / 9.7** | — CPU-deployed. Research IQ2_M (27.7 GB) benches 56.1 single | ✅ Q4 fits but CPU-deployed | 20.5/15.9/9.7 | prod |
| **worker_vision** *(CPU-deployed)* | Qwen2.5-VL-7B / Q4_K_M + mmproj-f16 | none | ~32–42 (fixtures; 2026-07-19) — **disagrees ~2× with the 2026-07-17 matrix (16.9–21.3)** | no clean device-labeled MI210 decode | ✅ (7B) but CPU-deployed | fixtures only (no depth curve) | 4/4 fixtures |
| **vision_escalation** — live alias *(CPU-deployed)* | Qwen2.5-VL-7B (same as worker_vision) | none | 32–42 (fixtures) | — | ✅ CPU-deployed | fixtures | 4/4 (temporary mitigation) |
| **vision_escalation** — approved, **NOT yet live** | MiniCPM-o-4_5 (`--reasoning off`) / Q4_K_M + F16 proj | none | 12–14 | 114.8–126.9 (bench; lane approved, registry flip not landed) | ✅ (~11% VRAM) | fixtures | 4/4 (`--reasoning off`) |
| GPU-reasoner **Qwable-v1** *(research route)* | 35B-A3B / IQ4_XS | plain / ngram | 16.0 | 100.3 (tg512) / 91.5 (tg1024); pp 2050/1951/1764 | ✅ ~18 GB | decode 100.3 tg512 | primary reasoning-heavy route |
| **GLM-5.2** *(research; rejected reviewer)* | 754B glm-moe-dsa / UD-IQ2_M (~238 GB) | native `draft-mtp` (α 0.93) | 2.49 no-spec → **5.33** MTP | — **never fits 64 GB** | ❌ CPU-only | 2.56 @12K, 1.20 @64K | rejected as patch reviewer (C-CRAB AUC 0.509); native-MTP ships available-not-required |

## How to read it
1. **Deployed lane, not baseline.** Every "CPU opt" is the fastest deployed config (MTP/spec-dec + OMP/quant/context). The OP-2 canonical `12.44 t/s` (frontdoor Q8 tg128) is a **CPU-regression control**, not a deployed number.
2. **GPU-eligibility splits by fit.** frontdoor / Qwable / vision-escalation fit the 64 GB MI210 (big GPU bench numbers); the **122B architect (Q4) and GLM-5.2 (238 GB) are CPU-only** — which is why GLM tops out at ~5 t/s.
3. **The final-smoke `worker 63.48` was smoke-grade** (degenerate output, 240/414 accept), NOT the deployed number — the worker's real optimized decode is **126.2** (2K).

## Open measurement gaps (`- [ ]` follow-ups; all operator/quiet-window-gated)
- [ ] **frontdoor CPU-MTP context curve on v7** — only the standing ~34.5 prod point exists; K35 measured frontdoor's *GPU*-MTP curve, not CPU-MTP at 2K/8K/32K.
- [ ] **worker_vision / vision MI210 decode + context curve** — no clean device-labeled MI210 number; the two CPU fixture measurements disagree ~2× (17–21 vs 32–42) on the same config.
- [ ] **GPU worker number** — free-form multi-slot determinism fails (K11.1); GPU worker eligibility unresolved despite the model fitting.
- [ ] **architect ≥32K** — exceeds the `-np 2 -c 16384` slot; no deep-context optimized rows.
- [ ] Re-run all rows as **decision-grade** under `P-GPU-1` **after** the v7 production promotion.
