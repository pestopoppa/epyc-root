# 2026-11-02 — handoff mi210-q8-dequant-gemv-roofline

## 00:14Z — Reconcile historical Q8 framing and qualify upstream MoE fusion issue provenance

Reviewed the INF37 inference candidates: SoA is conditional on poor coalescing; the governed IQ2 replay and Q4 candidate retain their stated prerequisites; the Q8 MoE fusion is a proposal with write-side capture still open. No row was published. Recorded the upstream issue reporter’s later isolation and uncertainty, and distinguished historical Q8 and prefetch claims from the governed verdict in the handoff. No compute, build or production changes.

## 01:37Z — Resolve MI210 inference-row prerequisites and correct stale decode attribution dependency

Checked the three listed inference tasks. SoA remains conditional on measured poor coalescing; the historical healthy assessment has no numeric counter receipt located in checked-in documentation. The --gen-tokens patch already landed as RVP-C4-4, and a governed aggregate decode trace exists, but it does not establish the IQ2_XXS-specialized attribution; the old 122B target is retired and OP-11 separately declined the seeded producer. Recorded the likely existing measurement projection scaffold and missing native producer fields for the proposed Q8 fusion screen. No row was published, no measurement or build was run. Previous wrap-up push reported failure but its changes are present on origin/main under rewritten commit d03b89a0a.

## 03:41Z — Recover failed wrap and qualify seeded attribution and MoE GLU prerequisites

Recovered prior failed wrap: the observer census target was tracked but absent from the sparse lane; restored the exact tracked file and the census passed. The earlier progress entry mischaracterized OP-11: v10 source includes --suite-seed and --repeat-suite from f744cc220e after v9; OP-11 declined a distinct AK_SENS_V1 producer. The available old HIP test binary lacks the generic flags, so an experimental source-bound build and preflight remain needed. Documented a GLU-only upstream source map and capture prerequisites; SoA remains conditional and the retired 122B must not be rerun. No compute, build, row publication or checkbox closure.
