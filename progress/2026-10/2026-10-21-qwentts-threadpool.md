# qwentts-threadpool: persistent threadpool + non-spinning barrier for qwentts and whisper.cpp, folded into the speech champions (work 2026-10-20/21)

- **Problem.** The frozen speech kernels build and free a ggml threadpool on every graph compute and wait in a pure `_mm_pause` barrier spin, so any core sharing collapses N>1-thread synthesis (CS-45 follow-up: 8T + 8 spinners 9754 ms/frame vs 24 quiet). Operator directive 2026-10-20: fix it on experimental branches so the speech champion can advance; whisper.cpp added to scope the same day.
- **Changes** (production trees untouched; branches cut from `production-speech-v1`, all on the fork remotes):

| Repo | Branch / sha | Change |
|---|---|---|
| qwentts.cpp | `qwentts.cpp-experimental-threadpool-20261020` @ `b1a1ec7` | persistent per-backend pool (poll 0), `--threads` / `QT_CPU_THREADS`, `QT_THREADPOOL=0` opt-out, ggml pointer bump |
| ggml (qwentts submodule) | `ggml-experimental-threadpool-20261020` @ `05e1ad6c` | `GGML_CPU_BARRIER=futex` (default) / `yield` / `spin`, adaptive spin budget 2000/200 |
| whisper.cpp | `whisper.cpp-experimental-threadpool-20261020` @ `fa5321e4` | lazy persistent pool per CPU backend, `WHISPER_THREADPOOL=0` opt-out, same barrier patch |

- **Results.** Greedy identity vs production on 10 texts (WAV/PCM sha, codec token ids, 25 dump tensors) and 10 whisper clips at T1/T8 in every barrier mode; CPU `test-backend-ops` 0 FAIL incl. `FLASH_ATTN_EXT` 5097/5097 (default and stock-spin) and 9219/9219 (stress). qwentts quiet within A/A; co-run 11.3x (+1 spinner), 20x (+8), 31.6x (+real llama-bench neighbour, which got 28x more throughput). whisper: correctness and quiet PASS, co-run total latency 2.4-2.5x, so the predeclared >=5x target is **MISSED** (decode phase 13-34x; encoder compute-bound).
- **Fold.** Fast-forwarded `champion/speech-qwentts` -> `b1a1ec7`, `champion/speech-qwentts-ggml` -> `05e1ad6c`, `champion/speech-whisper` -> `fa5321e4` (champion only; not promoted). `speech-v2-manifest.md` SP2-005/006 updated in the same commit; fold note under CS-45 in `conversation-stack.md`.
- **Deviations.** q1 co-run for builds/correctness (coordinator-authorised, no claim); q0 reps overlapping the coordinator's co-run windows discarded and re-run; CS-45 `nprocs_shim.so` deleted mid-run and re-created; first q2 matrix (older builds) stopped early; spin tuning set `tune2` not relied on; one test-backend-ops stop a few minutes short (finished later via the FA-only reruns).
- **Deferred, with named blocker.** None blocked. Filed as tasks: CS-50 (whisper per-call thread spawning), CS-51 (parakeet.cpp pool), CS-52 (idle pool on the GPU path; needs an inference-owner window), CS-53 (check the llama.cpp champion barrier). Declined: a whisper A/A block and 1T/pinned legs (not filed: the co-run and quiet verdicts do not depend on them; recorded in the CS-45 note).
- Evidence: `artifacts/qwentts_threadpool_20261020/` (start at `timing/timing_summary.md`).
