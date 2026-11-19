# KVU-19a-2 repeatability GPU row preparation

Prepared row ID: `handoff-kvu-kvu19a2-repeatability-20261104`.
This static predeclaration is routed to `handoffs/active/kv-cache-program.md`.
The launcher is runnable only through its future rowflow grant; this session did
not start it, publish it, or execute GPU work.

The row tests within-arm repeatability for historical cases 78, 79, and 80, using
five fresh harness processes per case/arm. It records raw output bytes and SHA-256,
requires exactly one supported case ID in stdout and exact output sizes (case 78:
131,072 bytes; 79: 8,388,608; 80: 65,536), samples the captured child's
mapped HIP DSO plus its own KFD VRAM while it is alive, and cleans only the process
group created for that child. It never inserts a sleep to force residency. If a
short invocation ends before HIP/KFD evidence is sampled, that invocation is
inconclusive; this is not evidence of absent GPU execution or repeatability.
Missing, empty, unsupported, duplicate, or wrong-size case output is refused as
inconclusive.

Set `KVU_GPU_QUALIFICATION=1` under a separate GPU grant to execute case 78 on
both arms, one fresh process per arm, with exactly four actual granted CPUs.
`FILLER_DRYRUN=1` invokes this same GPU smoke; it never substitutes an offline control.
Full mode runs all three cases on both
arms. Both modes pass a fresh allowlisted child environment with only
`GGML_CUDA_FA_MASK_SKIP=0`; inherited `GGML_*` overrides cannot alter dispatch.

Measurement sufficiency is fixed: the first within-arm output hash mismatch for a
case answers that case as observed variable and stops further repetitions for that
case/arm while preserving the partial record. A matching set of five is only “no
mismatch observed in five runs.” There is no aggregate pass or formal-gate early
pass. STOP, deadline, input/hash change, child failure, missing output, linkage
failure, missing HIP mapping, or missing own-PID KFD residency stops the row as
inconclusive, preserving completed records.

The preserved harness build row is explicitly filed **inconclusive**. Its native
result says the harness binary was compiled from the pinned source during
qualification, but the publisher rejected qualification as satisfying the
declared full-build rule. This row records that verdict and uses the binary only
as a preserved, source-hash-bound artifact; it does not relabel that build row
PASS or claim a full harness build. The baseline/candidate ggml artifacts come
from the separate source-bound build-pair row. Same-UID mutation remains a source
custody limitation.

The scratch root contains independent copies of all sources, catalog, receipts,
headers, harness and libraries. It has no runtime dependency on this worktree,
another row's scratch, or shared mutable lock modules. The private lock source
and loader are copied byte-for-byte from p3-row-r2 support. No binaries are copied
into the durable lane. `source.sha256` and `runtime.sha256` bind final bytes.

Only `KVU_OFFLINE_CONTROL=1` skips GPU work: it returns `status=inconclusive`,
`mode=offline_control`, empty runs, and explicitly cannot qualify the row.
The offline tests ran custody/mutation, actual affinity rejection, stdout recipe,
STOP/deadline and real owned benign process cleanup controls. They ran no GPU.
Output dimensions use `hsv=512`, not `hsk=576`; the historical source and original
raw sizes agree: 78=131072, 79=8388608, 80=65536 bytes.

Runnable spec: `/mnt/raid0/llm/tmp/kvu/kvu19a2-gpu-repeat-20261104/spec.json`.
Smoke uses four CPUs inside the allocator GPU grant (`WS58_REGIONS` and `FILLER_CPUS`);
the producer selects four CPUs within the actual grant and inherited affinity,
sets its own affinity to those four, verifies it, and children inherit the set. Native smoke
executes case78 once per arm, validates full stdout recipe, raw size, live own-PID
HIP/KFD maps/residency and verified child teardown. Full mode retains at most five
repetitions and first-mismatch stop per arm/case.

Completion is status-aware: qualification requires `qualified_gpu_smoke`; full
requires `completed_sample` or `observed_mismatch`. Failed qualification returns1,
preserves an attempt-local result, and creates no requested native result. Every
retry has a fresh attempt directory. Full inconclusive returns75. Offline control
writes only `OFFLINE-CONTROL.json`, returns1, and never writes the requested native
result. Captured children register their PID and birth in the engine PID registry
and receive SIGKILL on owning producer death. `FILLER_NEEDGPU=1` is mandatory.

Result publication uses a private temporary file, file fsync, atomic no-replace
hard link, and directory fsync; interruption before publication leaves no target.
