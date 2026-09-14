# AutoKernel concurrency handoff — 2026-09-14

Documentation only. The operator requested a detailed, independently reviewable handoff rooted in current code, and explicitly withheld permission to build or implement the proposed features.

Created [concurrent target coordination](../../handoffs/active/autokernel-concurrent-target-coordination.md), registered INF-74 and linked it from INF-73. The handoff maps current supervisor, callback, claim, interval accounting, history and hot-residency seams to proposed changes. It specifies model-independent footprints and preserves the existing GPU profile/screen/confirmation/serving workflow.

Corrected two earlier planning errors: historical cold-load/build contamination does not establish a universal prohibition on warmed GPU inference overlapping CPU measurements; the enrolled production Qwen native-MTP/np2 recipe is not interchangeable with historical DFlash2/np4 research. Ordinary foreign-load policy remains governed by the owning protocol.

One documentation checkbox completed; operator review plus eight implementation/acceptance tasks remain unchecked and explicitly approval-gated. No code, kernel, runtime configuration, campaign state or measurement artifact changed. Wiki compilation/pruning are outside this documentation task. The session-bus drain could not resolve the historical lane name as a current roster ID; no new roster identity was created.
