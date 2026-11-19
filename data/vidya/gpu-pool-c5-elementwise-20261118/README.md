# Prospective C5 elementwise support comparison

This task follows the original single-seed c463 elementwise capture: 105 selected cases included 17 unsupported descriptions (NORM 10, SUM 1, SUM_ROWS 6). The prospective C5 comparison preserves those descriptions and seed 2026102603. Each operator invocation also includes one explicitly separate original supported control case to exercise native allocation; the target and control counts remain distinct. The historical 544 unsupported observations cover 32 seeds and remain separate.

C5 identity is bound to the manifest-pinned test executable `dd9888f1a009dec291a3e3748b8e132ee9a9edf6dd3c9361f0dae10120270431` and HIP library `23d39c91a82fad0a83743829dd59a10df91bfe0c4a933f0cce693fc7a831beb4`, with all other input and mapped-library identities recorded by the private packet. The old c463 inventory is a historical comparator and supplies no current-C5 support outcome.

The packet writes its request before native execution. Native dispositions, failures and missing descriptions remain explicit. The existing GPU-pool carrier and shared grade apply. Publisher smoke proves readiness only; an official allocator run and exact-candidate planning canary are separate acceptance steps. No production, performance, promotion or RVP-C2-2 finding follows from preparation.

`scratch-cleanup.json` records removal of superseded copied model and test scratch. The current KVQ source worktree remains load-bearing and is retained.

The first publisher qualification retained all 17 target descriptions as explicit unsupported outcomes, but all in-window VRAM samples were zero, so it failed residency acceptance. That smoke is diagnostic only. The revised 20-case design adds three supported controls in the same native processes without weakening the two-positive-VRAM-sample requirement.

The second qualification recorded all 20 selected descriptions, three passing controls, three tuples and 44 qualifying residency samples. The publisher still rejected it because the smoke-result comparison did not survive JSON round-trip serialization. The raw qualification evidence and producer version are retained in `failed-qualification-2/`; this is not an official allocator result.

Publisher qualification PASS and row publication completed for `ni-gpu-pool-elementwise-20261118-v5` at 2026-11-18T20:33:16Z. `publisher-PASS.json` and `ready-manifest.json` retain the readiness receipts. The final producer normalizes shared-grade output before JSON equality checks and uses the smoke receipt for dry-run completion. Four focused synthetic controls passed. Official capture and exact-candidate planning-context acceptance remain open in SC18-GPU-POOL-C5-LIVE.
