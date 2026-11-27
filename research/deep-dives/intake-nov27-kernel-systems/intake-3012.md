# Qwen3-0.6B in raw x86-64 machine code: Gemini 4 Neon vs Claude Opus 5.5

[Primary source](https://github.com/alesha-pro/machine-code-llm-battle) · intake-3012 · 2026-11-27

On a 47-online-core Zen 2 EPYC 7642 with 4 populated DDR4 channels and 16 × 16 MiB L3, specialized Qwen3-0.6B Q8_0 engines reproduce exact prompt and greedy IDs across four prompts × 1/4/8/16 threads. Neon reports 188.35 mean tok/s against 103.82 at 32T, Opus 125.13 against the same recorded baseline; three repeats on one 34p/64g prompt, shortened context envelope (Opus 1024 positions), engine-reported decode separated from prefill, and hard-coded historical llama-bench lookup. Comparison uses row-split .asmbin against GGUF, different harness path, absent baseline commit/build/kernel/NUMA settings, and no raw paired repetition/dispersion for comparator. High-thread speed sweeps still check prompt 0, separate from all-four prompt qualification. Both entrants use THP copy, software prefetch and topology-aware workers; Neon uses 32-element block-scaled signed int16 activations, single monotonic row stream, mixed temporal/non-temporal prefetch covering cache lines and per-CCX resident-row partitions. The Q15 path resolves reported Q8_0 activation divergences at near ties; global Q15 missed a token; changing reduction order on the two-row Q15 variant also diverged. Opus f32 Q8_0 uses 4-row grouping and explicitly reports its own L3 partition experiment gave no gain and ~10% loss at 1T. Neon reports an inferred rather than directly counter-verified L3 residency/383 MB-per-token explanation. Its progression table bundles several changes in v7/v8/v9 and cannot isolate their effects. Format §2 suggests an integer-activation path that both reports found insufficient for exact test identity.

Full reads of README, opus/REPORT.md, neon/REPORT.md, FORMAT_SPEC.md and read of entire verifier. Engine hex not exhaustively audited. X post https://x.com/superalesha/status/2126041962272690479 returned 403 and is provenance only. No external code was executed.

The direct X endpoint returned HTTP 403. On 2026-11-27 the public FxTwitter mirror returned post 2126041962272690479, dated 2026-11-26 19:54:38 UTC, with 63,398 views and 1,708 likes. These mutable counters describe reception only. [Public post mirror](https://api.fxtwitter.com/status/2126041962272690479)

## Evidence

- Neon reports 188.35 mean/188.93 peak vs recorded 103.82 tok/s at 32T. [neon/REPORT.md:L128-L136 @ 2d53727](https://raw.githubusercontent.com/alesha-pro/machine-code-llm-battle/2d53727ebb7a6e5fedd344298b405de50bdff1bc/neon/REPORT.md)
- The Neon report records a one-token error with global-scale Q15. [neon/REPORT.md:L144-L149 @ 2d53727](https://raw.githubusercontent.com/alesha-pro/machine-code-llm-battle/2d53727ebb7a6e5fedd344298b405de50bdff1bc/neon/REPORT.md)
- Opus’s L3-residency attempt gave no speedup and cost ~10% at 1T. [opus/REPORT.md:L119-L121 @ 2d53727](https://raw.githubusercontent.com/alesha-pro/machine-code-llm-battle/2d53727ebb7a6e5fedd344298b405de50bdff1bc/opus/REPORT.md)
- Comparator values are a recorded EPYC 7642 baseline lookup, not contemporary measurements in the verifier. [scripts/verify_battle.py:L19-L28 @ 2d53727](https://raw.githubusercontent.com/alesha-pro/machine-code-llm-battle/2d53727ebb7a6e5fedd344298b405de50bdff1bc/scripts/verify_battle.py)
- The candidate storage is a row-wise split quantized matrix layout. [FORMAT_SPEC.md:L34-L45 @ 2d53727](https://raw.githubusercontent.com/alesha-pro/machine-code-llm-battle/2d53727ebb7a6e5fedd344298b405de50bdff1bc/FORMAT_SPEC.md)

## Scope and local transfer

Replace any universal or EPYC 9655 speed claim with an EPYC 7642 single-prompt three-repeat externally reported comparison against a fixed table. Mixed T0/NTA benefits are design-specific. Opus reported a negative L3 experiment; do not attribute Neon’s full gain to this one knob. Four golden outputs are narrow token agreement. Near-tie probes require change-controlled numerics, broad prompts, and identity on the same engine against its own reference.

9655: Stage-3 candidate for experimental current-champion same-kernel fixed shape/affinity baseline. Q15 per block vs existing quant and f32 reference with deliberate near-tie controls, separate speculative/plain and thread-count results; compare throughput and paired output/logit accuracy. Selective residence only as part of the existing NTA seed: compare T0, NTA-only, and budgeted policy where measured per-CCD fit survives worker placement. Compare hugepage relocation vs mmap while accounting for actual hugepages/TLB, cold load and warm service. Lane handoffs/active/autokernel-akx-program.md:1393–1395 closed generic CPU-NT-WEIGHT-STREAM as seed on NTA256 +0.69% [-1.8,+3.2]. MI210: Zen prefetch instructions and partition policy are CPU-specific. Existing MI210 non-temporal weight-streaming result is an independent control cited by that handoff. The transferable question is whether per-32 higher-precision activation quantization moves quality/speed on gfx90a at batch 1 or concurrent small-model serving versus FP16/int8 library paths, while recording HBM/L2 bytes and dequant cost. Avoid porting the ELF/layout wholesale.

The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest before sampling. Replay near-tie and ordinary rows with incumbent Q8, per-block signed Q15 and FP32 reference. Save top-two gaps, argmax flips, accumulators and conversion cost; verify AVX-512 signed-word dot semantics and overflow against a scalar oracle.

The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity. Compare resident and streaming layer subsets for a draft head after accounting for per-CCD weight duplication, KV and scratch. Isolate four-row blocking, worker pinning, barriers and THP; include a 27B bandwidth-bound negative control.

Golden greedy prompts exercise too few shapes for kernel promotion. Wall time, turns and cost are author-reported and provide planning context. Retain exact-token checks across thread counts as an additional witness when a generated CPU candidate reaches operator, numerical and served gates.

## Sources surfaced

- https://github.com/alesha-pro/llm.asm — Same maintainer’s parent exporter/reference. Read provenance, layout and baseline build/flags if available. Related artifact, no independent corroboration.
