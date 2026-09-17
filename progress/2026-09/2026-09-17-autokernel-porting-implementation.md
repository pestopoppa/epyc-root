# AutoKernel porting-method implementation — 2026-09-17

The operator asked this session to implement the generic verifiable-porting-loop items filed as AK-PORT-1/2/3, not to import an unverified CUDA port or its claimed speedups. Production v9 was untouched.

## Live correctness gap and repair

Review of v22 found that the source candidate edited CPU gated-delta-net in `ggml/src/ggml-cpu/ops.cpp`, while the existing gate defaulted to `test-backend-ops -o MUL_MAT`. That test could pass without exercising the edited operation. v22 stopped cleanly at batch 2; its two measured screens (+0.296% HALF and +0.064% FULL) are candidate-only, not keeps. The source tip `614ff2ba02e0`, 28 historical keeps, store and champion remain intact.

Research lane commits `b4f08d6d`, `032db5e5`, `c8e79e4c` route actual changed source to an affected native op, require a nonempty selected-backend suite, then apply an independent scalar GDN reference before timing. The GDN probe checks 16,896 exactly representable F32 attention/state outputs and distinguishes wrong outputs from setup failure. Unknown/shared CPU source routes, including IQK/x86 edits that lack edited-path engagement or an independent fallback, refuse before build. This is deliberately narrower than saying a passing CPU-vs-CPU test proves correctness. Whole-source and LOO gates apply GDN parity without retroactively vetoing the 28 older keeps.

The remaining CPU coverage is material: past GLM attempts touched IQK matmul, graph scheduling and x86 quant paths. Native `use_ref` bypasses some IQK/fusion paths, and IQK emits an ACTIVE marker, but the current generic marker does not bind the edited quant function to a selected passing case. These paths need a bounded engagement/reference check before prospective keeps; otherwise they are not admitted. Low-precision cosine/PSNR and max-abs/MSE thresholds are not installed without a validated reference/threshold recipe. AK-PORT-1 therefore remains open; AK-PORT-2 is complete for the admitted routes.

## Codegen diagnostics and belief provenance

Research lane commits `cb345057`, `19739cb9`, `43bc268b`, `09bc8fc3` add a bounded, immutable, build-framed codegen sidecar on source KEEPs. At most eight standalone AMD code objects of at most 8 MiB each are read; disassembler subprocess time is capped at 12 seconds total and output at 1 MiB per object. Tool or object absence is represented as unavailable and cannot veto a keep. The producer writes a diagnostic-only ClaimTuple bound to attempt, source commit/tree, backend, recipe/toolchain frame and object/core hashes. Root commit `7e46f3ca` adds a strict advisory reader that re-derives those bindings and uses the shared grader. CPU machine-code summaries and embedded-only HIP fatbins are not yet extracted; runtime-only keeps have no new codegen and say so. AK-PORT-3 remains open to universal retained-variant coverage; the live source-KEEP Vidya write/read task is closed.

## Verification and relaunch boundary

Combined focused research tests: 114 passed, four cross-target variants deselected. Three of those variants fail identically on untouched `84aaaf8d` with the same startup refusal. Real existing anchor binary: native CPU GDN selected suite 38/38 passed; independent scalar probe 16,896/16,896 passed. Root strict-reader tests: 14 passed. Research code compiled and `git diff --check` passed. No benchmark or kernel speed gain was claimed by these checks.

The v23 dry run resolved the same GLM model, source tip, 28-keep store, full CPU placement and matched-process instrument. A continuous controller started at 16:32 UTC in `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260917-v23`, with child PID 2765563 captured from `serial-state.json` and parent PID 2765473. At this checkpoint it is running batch 0; startup alone is not proof that an authored candidate reached the new GDN gate or a valid measurement. The producer's `current-serial-run.json` points the dashboard to v23 automatically. Continue monitoring; if it fails, stop at the batch boundary and repair the observed fault without discarding the retained campaign.
