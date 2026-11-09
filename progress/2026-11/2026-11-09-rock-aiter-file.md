# 2026-11-09 ROCK-AITER-GFX90A step 2: packet A filed, packet B made publishable

Filed (file_result.py, --no-reclaim so packet B's inputs survive; no box ticked, step 2 timing not yet run):
- rock-aiter-build-20261105: SUPERSEDED by rock-aiter-tests-r3 (rc=75 STOP at 11-05 15:14Z, no RESULT.json, partial per-op log).
- rock-aiter-prebuild-r4-20261105: pass (ran to verdict; ops_ready 3 of 11, six modules failed).
- rock-aiter-tests-r3-20261105: pass (RESULT.json complete; passed[] rmsnorm, fused_add_rmsnorm, rope, gemm_a8w8_ck, gemm_bf16_tuned, paged_attn, mha_ck; failed fused_moe_ck2stage, mha_varlen_ck; activation errored; moe_sorting unsupported). mha_ck waited ~19 min on a stale JIT baton lock, then ran.

Packet B (/mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-timing-20261105): the build row never wrote out/RESULT.json, so
precond/job were repointed to the real gate artifact rock-aiter-tests-20261105/out/RESULT.json (complete + passed[] still required),
job SRC moved to the tested src-gfx90a tree + pydeps, regions/claim set to mi210_0,88-95,184-191, SOURCE.sha256 resealed for precond.py and job.py.
Diff: artifacts/analysis/rock-aiter-file-20261109/packetB-gate-repoint.diff. publish_row lint + task lint pass; NOT published.
