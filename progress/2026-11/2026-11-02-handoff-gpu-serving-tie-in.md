# 2026-11-02 — handoff gpu-serving-tie-in

## 09:47Z — M4 GPU residency and P4/P5 instrument preparation

Prepared an isolated M4 source-bound patch that requires an own-PID GPU residency sample wholly within the measured request batch, plus model-free test source. Prepared a default-disabled P4 typed validator and synthetic controls without AutoPilot integration, and a P5 gold-input/report binder with tests. These are untested preparation, not a qualified row or completed gate. P4 still needs current tenant/bounds and integration; P5 needs its actual scorer and gold execution. M4 needs current source/plan/resource binding, safe launcher and qualification.

## 09:49Z — Correct P1-2 scope and route the suspended E5 re-measurement to its existing owner

Corrected P1-2: the Stage-B throughput and placement rankings were withdrawn for the NUMA defect, and the corrected CPU re-measurement, R1–R4 and operator artifact are owned by batched-decode-measurement (INF-07). P2-5d is a decision proposal, not a CPU inference row; P2-5e requires representative AutoPilot operation. No duplicate inference rows published.

## 09:52Z — Prepare P4-1 typed-knob design against current policy

P4-1 preparation: stock and FF weights in the old task were deleted; P3-5 owns replacement bake-off arms and new measured ceiling rows. A source-grounded typed-policy design is being prepared for review without activation. GPU-LEAK-1 remains open for the kernel owner's versioned promotion; CH-30 is in the experimental champion and the v10 guard remains necessary.
