# 2026-11-02 — handoff mi210-q8-dequant-gemv-roofline

## 00:14Z — Reconcile historical Q8 framing and qualify upstream MoE fusion issue provenance

Reviewed the INF37 inference candidates: SoA is conditional on poor coalescing; the governed IQ2 replay and Q4 candidate retain their stated prerequisites; the Q8 MoE fusion is a proposal with write-side capture still open. No row was published. Recorded the upstream issue reporter’s later isolation and uncertainty, and distinguished historical Q8 and prefetch claims from the governed verdict in the handoff. No compute, build or production changes.
