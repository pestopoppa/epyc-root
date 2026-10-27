# META host-view private candidate and owner packet — preparation complete

Preparation completed 2026-10-27. The previously accepted diagnostic capture established that a qwen4exp reshape in a Meta graph had a ROCm_Host MEAN_D1 backing tensor and hit the Meta buffer assertion. The capture establishes neither root cause nor correctness.

A C5-based private candidate preserves the existing OP_NONE exemption and accepts only host view operations with matching backing buffer, valid offset and extent, and bounded storage provenance. It guards reduction lookahead across foreign tensors and includes trailing foreign views after a partial reduction. Actual Meta graph impact is **UNKNOWN**: native graph analysis missed the backend vtable dispatch. The candidate, direct Meta partial-reduction fixture and reject controls have not been compiled or executed.

The complete owner build packet is under `/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep`, source seal SHA-256 `06b35586d98858a2b24d377e75c0295a0feb84694b6c777f6fd6c41bc5edbf9b`. Its unarmed `ROW-BACKLOG.md` requests one atomic 3600-second CPU build grant for 48-71, with 24 GiB aggregate RSS limit and both CPU and HIP house profiles. It runs model-free fixtures only; the direct Meta graph is not an exact scheduler reproduction. T1 and synthetic normal validator, grant check and admission passed; temporary processes drained. Normal owner build is still required.

Source ref: `codex/meta-host-view-fix-20261027` at `520ad4f55d805a544862be88d652ec68fcd194ab`, parent C5 `c72ec82f5417bb2937310326120f149b665e8400`. Owner worktree `/mnt/raid0/llm/worktrees/meta-fix-c5` stays at C5 plus the sealed diff; do not remove it before owner build.

Remaining parent work is open: owner-granted CPU/HIP compilation and meaningful fixture outcomes; owner-granted architecture tests and captured residency where applicable; source root-cause confirmation, independent review, and coordinated champion fold gates. No correctness, performance, measurement or fold claim is made. This preparation did not produce a new measurement or verified finding needing a Belief Kernel source.
