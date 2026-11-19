# 2026-11-16 AutoKernel (roster `autokernel`, ad-hoc) -- includes 2026-11-15 items

| Item | Result |
|---|---|
| c11-fatopk split (r2) | DROP (0.986); filed |
| ak-q38fn reliance proof r6 | PASS; filed |
| Upstream b12421 bundle1, CPU r2 | KEEP, +1.5% geomean, KLD 0, no new fails |
| Upstream b12421 bundle1, GPU r3 | tok/s FAIL (P3 0.942), explained as MTP draft-acceptance noise by `up-bundle1-gpu-bisect-20261116`; per-step cost bundle/fold 1.005 (16k) / 1.009 (28k). Re-run with per-step-cost gate ordered |
| convsnap | view-bounds assert fixed (316ed0720, missing upstream bbb02c93e); CPU r3 DROP (0.996, identity exact); GPU r4 inconclusive (TOPK_MOE_ASM flake vs equality gate), r5 queued, gate to be replaced by per-step cost |
| farows-bound (GPU, architect_critic Q8_0 np4, 35-42k fill) | PORT-WORTHY: decode gain bound 33%, verify 21.6%; KV share 0.56/0.67; MASK_SKIP captures 61% of skippable work; A1/A2 drift 0.8%/0.5%. Filed pass |
| test-backend-ops parser defect | `FAIL_RE` missed `[OP] ... test failed FAIL` lines (vacuous n_fail=0); fixed in r2+ rows via `Failing tests:` block |
| Missing `ignore_eos` | invalidated first GPU A/Bs; fixed |

All 11 earlier verdicts confirmed already FILED (NOOP); `up-farows-bound-gpu-20261115` filed by this session.

Handoff changes (`handoffs/active/kernel-champion-and-promotion.md`): UP-B12421-FAROWS-BOUND ticked; new open boxes UP-B12421-FAROWS-HIP-PORT and GPU-MTP-ACCEPTANCE-METRIC; status appended to CONVSNAP, BUNDLE1 (not ticked) and C11-GPUPROOF-ANSI-PARSE (not ticked).
Lessons added to `docs/guides/agent-workflows/compute-fillers.md`.

## C12 fold recorded (operator-approved 2026-11-16)

Champion candidate C12 = `457d5fc523ba5cc687a333a588c1dc15db9346f4` (branch `llama.cpp-experimental-up-bundle1-20261115` = C11 fold `8b9bf3031` + upstream b12421 bundle1). Evidence: up-bundle1-cpu-20261115-r2 pass (geomean 1.015, 0 new fails, KLD 0); up-bundle1-gpu-20261115-r5 pass (per-step geomean 1.030, P2 1.064, P3 0.998; one unconfirmed TOPK_MOE flake).

Handoff: UP-B12421-BUNDLE1 ticked; C12-CPU-FOLLOWON box added; FAROWS-HIP-PORT must rebase onto `457d5fc52` before any keep run. Manifest `docs/reference/kernel-manifests/llama-v11-manifest.md` gains V11-141 (C11 fold) and V11-142 (bundle1). No compiles or inference run.
