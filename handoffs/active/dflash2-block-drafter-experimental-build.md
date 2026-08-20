# dFlash2 block drafter — experimental build + measured comparison vs MTP

**Status**: active (created 2026-08-20) — READY TO START, no blockers, needs an experimental-branch build
**Categories**: speculative_decoding, hardware_optimization, local_inference, kernel_experimental
**Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Related**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) (this is its Qwen3.8 rider),
[`deepseek-v4-flash-0731-dspark.md`](deepseek-v4-flash-0731-dspark.md) (working DFlash-family sidecar workflow on v9),
[`autokernel-research-loop.md`](autokernel-research-loop.md); completed:
[`dflash-block-diffusion-speculation.md`](../completed/dflash-block-diffusion-speculation.md) (DFlash NO-GO on **CPU** — sequential
DeltaNet verification, not a DFlash defect; does not apply to this GPU path)

## Objective

Decide, on measured evidence, whether the dFlash2 block-diffusion drafter beats our in-file MTP head for
**Qwen3.8-27B on the MI210**. This is an *alternative* to MTP, not additive — `--spec-type` takes one value.

## Why this is a build task and not a bench task

v9 already ships `--spec-type draft-dflash` and `draft-dspark` (verified 2026-08-19 from `llama-server --help`),
so DFlash1/DSpark drafters run on frozen production today. **dFlash2 weights do not.** Only DFlash2 GGUFs are
published for Qwen3.8-27B — there is no DFlash1 build of this drafter — and v9's loader is the DFlash1
implementation. Measured, not assumed:

```
load_arch_hparams: missing target_hidden_size; using legacy draft hidden size 5120
llama_model_load: error loading model: done_getting_tensors:
    wrong number of tensors; expected 81, got 58
```

The file is a valid GGUF declaring `dflash.*` keys; v9 requires 81 tensors and a `target_hidden_size` key
(`src/models/dflash.cpp:19-21`) that DFlash2 weights do not carry. 58-vs-81 is a **format difference, not a bad
download**. Evidence: `epyc-inference-research/artifacts/architect-bench-gpu-20260814/dflash2_20260819/dflash2_n8/server.stderr`.

So this needs llama.cpp **PR #27342** (open, NOT merged as of 2026-08-18), built per the four-step workflow in
`CLAUDE.md`: pull fresh production → build on `llama.cpp-experimental` → validate no regressions (GPU + CPU) →
deploy as a NEW production version. **The frozen v9 tree is never edited.**

## The bar it has to clear — measured 2026-08-19, not assumed

There was **no plain-vs-MTP baseline for Qwen3.8-27B anywhere in the repo** before this. There is now.
Protocol: np=1, 12 real olympiadbench prompts, 2048-token cap, v9 `0db32c06e` / build `10125`, one flag varied.
Artifacts: `artifacts/architect-bench-gpu-20260814/mtp_ab_20260819/` and `mtp_nmax_sweep_20260819/`.

| `--spec-draft-n-max` | plain | 2 | 3 | 4 | 6 | **8** | 12 |
|---|---|---|---|---|---|---|---|
| decode t/s | 27.78 | 39.77 | 46.61 | 51.03 | 55.22 | **55.46** | 51.14 |
| draft acceptance | — | 0.842 | 0.773 | 0.702 | 0.579 | 0.482 | — |

- **MTP is worth 1.85× at n-max 4 and 2.00× at n-max 8.** dFlash2 must beat **55.46 t/s**, not 27.78.
- The vendor's 2.7–4.6× headline is versus *plain*, at batch 1, on an Apple M5 Max. We already capture 2.00×
  of that for free from the in-file head. Their like-for-like claim is 4.80 vs MTP's 4.28 accepted tokens ≈ **+12%**.
- **Suffix decay is real on our own drafter**: acceptance nearly halves from depth 2 → 8. That is the effect
  dFlash2 claims to fix, so the headroom is real — but it is ~12%, not 2.7×.

## Tasks

- [ ] **DF2-1 — Build.** Fresh production tip → `llama.cpp-experimental`, apply PR #27342, build HIP/gfx90a.
      Forward-port our local gfx90a patches into the candidate, **notably `a6b4b5263`** (routes small Q8_0
      MTP-verify batches to MMQ, `ne11<=1`, +17.4% single-stream MTP on MI210).
- [ ] **DF2-2 — Check the MMQ patch still fires.** `a6b4b5263` is *MTP-verify-shaped* (`ne11<=1`); a dFlash2
      block verify has `ne11≈8` and may land on a less-tuned path. **This is the single most likely cause of a
      disappointing first number** — confirm before attributing any shortfall to dFlash2 itself.
- [ ] **DF2-3 — No-regression validation vs v9** (GPU + CPU) before any comparison is quoted.
- [ ] **DF2-4 — Matched comparison.** Replay the exact protocol above (same 12 prompts, np=1, 2048 cap) with
      `--spec-type draft-dflash` + `incoai/Qwen3.8-27B-DFlash2-GGUF:Q8_0`
      (already downloaded: `/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf`, 2,056,414,752 bytes, Apache-2.0).
      Report decode t/s **and** acceptance against the table above.
- [ ] **DF2-5 — Concurrency.** Re-run at np=2/4/8 against the MTP grid (47.6 / 75.4 / 108.7 / 157.3 t/s).
      PR reviewers report **scaling problems at concurrency >1 and setups where dFlash2 loses to MTP**; our
      production role runs np up to 8, so this is on-target, not a footnote.
- [ ] **DF2-6 — Greedy-parity check.** dFlash2 claims losslessness; verify exact-token parity vs `--spec-type none`
      at temp 0, same method as `deepseek-v4-flash-0731-dspark.md`.

## Known negative evidence — do not wave this away

`llama.cpp` issue #25117 reports DFlash at **0.48× baseline** on AMD (gfx1151 APU, Q4_K MoE target), attributed
partly to a BF16-trained drafter meeting a quantized target and partly to HIP-backend immaturity. That is an APU
with a MoE target, not our discrete MI210 with a dense Q8_0 target — but it is a **real AMD-specific negative
datapoint** and DF2-2/DF2-5 are the checks that would catch the same failure mode here.

## Decision rule

If dFlash2 does not beat **55.46 t/s single-stream** *and* hold up at np=8, it does not displace MTP. A ~12%
acceptance gain bought with a 2.0 GB extra resident model and its KV-injection overhead is not obviously worth
it; say so plainly rather than shipping a marginal win.

## Adjacent finding this surfaced (separate work, not part of DF2)

The v9 24-cell throughput grid was captured at `--spec-draft-n-max 4`, i.e. **below peak** — 6–8 is optimal,
worth ~8% single-stream. Re-collecting that grid at n-max 8 is outstanding. Also `model_registry.yaml:849` ships
`draft_max: 4` while `epyc-orchestrator/stack_templates/default.yaml:148` ships `24`; **measured, both are wrong**
(24 is far past the turnover). That config conflict gates the pending Qwen3.6→3.8 registry swap and belongs with
whoever owns the swap, not with this handoff.

## Sources

[inco.ai/blog/dflash2](https://inco.ai/blog/dflash2/) · [z-lab/dflash (MIT)](https://github.com/z-lab/dflash) ·
[Qwen3.8-27B-DFlash2-GGUF (Apache-2.0)](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2-GGUF) ·
[llama.cpp PR #27342](https://github.com/ggml-org/llama.cpp/pull/27342) ·
[llama.cpp issue #25117](https://github.com/ggml-org/llama.cpp/issues/25117) ·
[arXiv 2602.06036](https://arxiv.org/html/2602.06036v2)

All vendor speedup figures above are **CLAIMS**, unverified on gfx90a. Every number in the n-max table is a
**measured OBSERVATION** (MEASUREMENT.md) — none gates a keep/deploy decision on its own.
