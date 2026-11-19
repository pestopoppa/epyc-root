CAFE-3 full HIP gfx90a candidate build (2026-11-19)
================================================

Row `df2-cafe3-full-hip-build-20261119` builds the same full source candidate as
CPU row `df2-cafe3-full-cpu-build-20261119`. Its detached source worktree is
`/mnt/raid0/llm/tmp/df2/cafe3-full-source-20261119`, based on production commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. It reads that worktree and builds
outside it, so the CPU and HIP build rows do not share generated build state.
`inputs.json` binds the full tracked diff, all generated source and headers,
source manifest, driver, launcher and existing STOP/deadline supervisor.
Unexpected untracked source is refused. The production kernel is unchanged.

The four-CPU publisher smoke compiles the transformed server-context.cpp with
ROCm Clang and checks adaptive environment, launch-context, durable journal
schema and poisoned-journal markers in the resulting object. It also requires
the real IQK translation unit to fail with `enum-constexpr-conversion`, then
pass unchanged with `-Wno-enum-constexpr-conversion`. Smoke produces no model
observations and does not build the full HIP image.

The scheduled full build enables HIP, disables backend dynamic loading,
selects ROCm Clang and gfx90a, and preserves the IQK compatibility flag.
The receipt hashes llama-server, CMake cache, logs and llama/ggml libraries.
All llama/ggml linkage must resolve locally under the row's own LD_LIBRARY_PATH;
the HIP library is required. The CPU library must define exact code exports
`iqk_mul_mat` and `ggml_iqk_try_mul_mat`; the HIP library must define
`ggml_backend_cuda_reg` and contain the gfx90a image marker. Undefined imports,
data symbols and substring lookalikes cannot satisfy the export gate.

Stop on a validated full receipt. A source, compiler, marker, export, linkage,
STOP or deadline failure ends the attempt. The pinned supervisor drains only
captured descendants. No GPU execution, model identity, throughput, native
launch-context validation or P9 qualification is claimed by this build row.
No model preparation or weight hashing takes place inside the grant.

Publisher smoke PASS at 2026-11-19T17:54:18Z on cores 116–119, rc 75 after
validated first progress.

Two validator regressions cover stale receipt bases, tampered artifacts,
missing artifact bindings/markers, absent IQK failure witnesses and export
lookalikes. Full-build and native P9 verdicts remain outstanding.

[no-belief: build qualification contract and synthetic validator controls only]

Build exit attribution repair (2026-11-19)
----------------------------------------

The original scheduled build failed qualification after linking the server;
its supervisor rc75 did not distinguish STOP, deadline, signal or surviving
descendants. That historical cause remains unknown. The revised driver uses
`cafe3-build/supervise.py` with an additional report-path argument. It records
explicit reasons, child rc and child PIDs before draining, then persists the
drain outcome. Leftover descendants still refuse successful qualification.
The inherited pidfd identity checks and verified drain are unchanged; the
new exit-boundary tests mock process execution/draining.

Replacement inputs must pin this revised supervisor and driver in a NEW
scratch packet/row. Existing published packets and inputs.json snapshots
remain historical and are not compatible with the changed supervisor CLI.
New inputs must declare `supervisor_protocol: epyc.cafe3.supervisor.v1`;
the revised input checker refuses older packets before executing a command.
No replacement row is claimed published by this source repair.

The revised full-build marker gate reads the hash-bound
`libllama-server-impl.so`, which carries server-context code in this source
layout, and requires it in local linkage. The executable, cache and linkage
log must also be hash-bound. UI building and prebuilt UI fetching are disabled
and checked in CMakeCache. Full-build synthetic receipts exercise the linked
component gate for CPU and HIP; no new full build or native P9 verdict exists.
