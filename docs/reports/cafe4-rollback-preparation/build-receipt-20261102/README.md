# CAFE-4 target-bound CPU build receipt

The granted `cafe4-v10-diagnostic-build-20261102` ended rc0 with `reason=complete` on 2026-11-02. Its build-only decision rule is satisfied: `RESULT.json` binds v10 source `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, the target-state patch, candidate input, build logs/cache, built candidate, and `libllama` to recorded SHA-256 digests. The row's completion proof checks source identity, patch digest and artifact hashes and requires the recurrent target and configure/count markers in the relevant compiled artifacts. The build script checks the source before and after compilation, but these snapshots do not exclude a concurrent mutation restored between checks.

The retained `source.patch`, `candidate.cpp`, `build.log`, `configure.log`, and `CMakeCache.txt` match their recorded digests. The binary artifacts remain at the native paths in `RESULT.json`; the receipt retains their digests rather than copying binaries into the repository. `row-manifest.json` retains the actual historical route, which points to an earlier handoff pathname; it does not authorize ticking a parent task.

This is an experimental CPU build with a synthetic draft fixture. It does not establish model loading, MTP, rollback, injected-fault sensitivity, inference performance, or CAFE-4 completion.
