# M4 GPU residency-window candidate

`residency-window.patch` is a source-only proposal against the private retired
`/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/speed-gpu/native/server_np_sweep.py`
SHA-256 `76e234550e6bfc45c21c2cfd9539441f8f6ebf7dd64ab88c5173a01ce0cb3859`.
It has not been applied to that source or registered. It requires a complete
own-PID residency sampling interval within the measured request-batch interval,
using one process's monotonic clock, and records the boundaries alongside the
native samples and in the prospective measurement payload. The preexisting
validation still checks every sample for positive own/device VRAM and KFD count
and the configured VRAM ceiling. A batch shorter than the sampling interval can
fail closed; that is intentional rather than a residency claim without evidence.

`test_residency_window.py` is an unexecuted, model-free helper control for a
separately patched candidate via `M4_GPU_SWEEP_SOURCE`; it covers outside,
straddling, malformed and wrong-PID windows. It does not exercise the actual
thread, server, request timing, ggml linkage, process-birth identity, source
seals, clean teardown, or the independently bound plan and resources. The
existing private reader cannot trust these values solely because they occur in
a self-reported row. An owner must review the source-bound runtime and reader,
add real-entry and failure-injection controls, re-seal inputs and use the
keeper's qualification before scheduling; this patch is not a READY row.
No tests or compute were run while preparing this proposal.
