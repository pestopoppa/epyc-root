# RTG-58 KPF-18 item 3 co-tenancy

The GPU correctness run started 2026-11-02 13:13:04 UTC. The INF-65 session reported its q1 build overlapped 13:13:03–13:13:39 UTC. q3 was held by an independent build when the GPU run started; this run uses GPU-only exclusive region-lock and GPU host threads 184–191. The measurement is diagnostic/correctness only; do not infer timing or performance from it. Retain the raw KPF and own-PID VRAM samples with this note.

This run was directly launched on the user's explicit instruction under the exclusive `gpu-quiet` region lock with RAM admission; it was not issued a rowflow grant. `gpu_window_id` is a run identifier, not an allocator receipt. Preserve this distinction when projecting or judging the resulting records.

RTG-57 subsequently identified the q3 holder as its TTS CPU build, which overlapped this run's GPU host SMT siblings 184–191 and was stopping near 13:20 UTC; exact overlap end was not independently timestamped. Treat this as correctness-only, with no timing claim.

Correction from RTG-57: TTS compiler workers were pinned to physical cores 72–75, not to GPU host-thread physical siblings 88–95; a brief CMake configure was unpinned. This supersedes the earlier statement that those compiler workers overlapped SMT siblings. Overall CPU co-tenancy and the no-timing restriction remain.
