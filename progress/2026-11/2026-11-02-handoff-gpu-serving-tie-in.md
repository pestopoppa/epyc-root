# 2026-11-02 — handoff gpu-serving-tie-in

## 09:47Z — M4 GPU residency and P4/P5 instrument preparation

Prepared an isolated M4 source-bound patch that requires an own-PID GPU residency sample wholly within the measured request batch, plus model-free test source. Prepared a default-disabled P4 typed validator and synthetic controls without AutoPilot integration, and a P5 gold-input/report binder with tests. These are untested preparation, not a qualified row or completed gate. P4 still needs current tenant/bounds and integration; P5 needs its actual scorer and gold execution. M4 needs current source/plan/resource binding, safe launcher and qualification.

## 09:49Z — Correct P1-2 scope and route the suspended E5 re-measurement to its existing owner

Corrected P1-2: the Stage-B throughput and placement rankings were withdrawn for the NUMA defect, and the corrected CPU re-measurement, R1–R4 and operator artifact are owned by batched-decode-measurement (INF-07). P2-5d is a decision proposal, not a CPU inference row; P2-5e requires representative AutoPilot operation. No duplicate inference rows published.

## 09:52Z — Prepare P4-1 typed-knob design against current policy

P4-1 preparation: stock and FF weights in the old task were deleted; P3-5 owns replacement bake-off arms and new measured ceiling rows. A source-grounded typed-policy design is being prepared for review without activation. GPU-LEAK-1 remains open for the kernel owner's versioned promotion; CH-30 is in the experimental champion and the v10 guard remains necessary.

## 09:54Z — Prepare P3-4 native-MTP versus DFlash2 serving measurement design

P3-4 design preparation commissioned against the serving handoff and measurement constitution, including paired serving metrics and launch-bound mode-switch costs. This is a design task; the champion promotion decision and operator grant precede compute.

## 09:55Z — Review and land P4-1 typed-knob implementation contract

Prepared the P4-1 implementation contract against orchestrator 9e138e3a, including feature gating, tenant-specific measured ceilings, typed seed and 5xx tests. Independent review added the solo-resident restriction and an independently verified artifact-attestation requirement; current target source must be re-reviewed and deleted stock/FF tenants cannot be seeded as live. The implementation remains open pending work in the orchestrator lane and replacement measured tenant policies.

## 09:58Z — Prepare P3-4 serving comparison measurement design

Delegated a native-MTP versus DFlash2 serving A/B design with measurement-constitution review, pinned candidate identities, duty-mix and launch-bound mode-switch costs. Registered its completion event for owner review. This is preparation only; no compute or promotion is authorized by it.

## 10:00Z — Prepare P3-4 paired serving comparison design

Prepared a P3-4 native-MTP versus DFlash2 serving comparison proposal with common model and binary, paired workload strata, explicit launch-switch economics, quality and latency outcomes, residency and identity proofs, and applicable protocol limits. Candidate identities, sustained-serving protocol and decision thresholds remain to be settled before booking; no measurement or adoption is claimed.

## 10:04Z — Prepare P3-5 replacement-arm decision package

Prepared the P3-5 operator package: recommend Qwen3.8-27B versus the previously specified A4 sequential control; alternatives restore the deleted historical stock/FF pair or measure only the Qwen3.8 baseline. Operator selection remains outstanding. Verify artifacts and recipe, measure new ceiling rows and use the proper orchestrator worktree before configuration changes; no activation or inference follows from the package.

## 10:07Z — Run P5 known-gold binding helper controls

Ran the nine model-free tests for the existing P5 gold-binding helper: all passed. Documented their scope and limitation: the synthetic controls validate binding/report coverage only, not gold-patch execution or the still-unbound P5 scorer. GPU-PLT-1 preparation lacks pinned custom code, isolated runtime, frozen corpora and its four-arm harness; it is not ready to publish.

## 10:10Z — Repair P5 gold report consistency validation

Found and reproduced a P5 helper defect: a report can mark a case resolved while also marking it incomplete or empty-patch and receive REPORT_COVERAGE_MATCH. Delegated a fail-closed repair with synthetic negative controls and registered its completion event. GitNexus impact is unavailable because the lane is unindexed and CPU admission denied indexing; direct source search found the helper's documented CLI and tests. The actual agentic scorer and known-gold controls remain unvalidated.
