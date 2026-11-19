# KPF-41 backend GPU r2: INCONCLUSIVE

Row `kpf41-backend-gpu-qualification-r2-20261119` ended wrapper rc1. The child backend process exited 0 and its raw log ends with `2978/2978 tests passed`, `Backend ROCm0: OK`, and `2/2 backends passed` (CPU skipped). These are partial observations, not a qualification PASS.

`parse_corpus` expects each case and status on one line; the first rejected case instead contains `ggml_backend_cuda_graph_compute: CUDA graph warmup complete`. HIP graph diagnostics interleave with case output. The parser exception occurs before `linkage_after=check()`, so the required post-run source, five artifact hashes and loader custody checks were not captured. Full case counts, unsupported counts and shared-trunk coverage have not been reconciled. No kernel failure is established.

The owned backend PID was 3126765. Of 5726 live samples, 5723 contain both positive KFD VRAM and the expected HIP mapping. This supports residency during execution only.

Evidence remains in place (no copied logs or binaries):

- `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/out/RESULT.json`, SHA-256 `62016e3e27859933b6dbf3268d56c9b2ef85f21b78c6afb91e16e5ae9e2e9f5c`.
- `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/out/corpus.log`, SHA-256 `00f32fda75481a50e864a3bb5abb1597378768a3143d5b97bfd46b440cc48537`.
- `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/job.py`, SHA-256 `1f93091859e5a1b7a5d89bce19b9e1d51a76956f2253622619ae409085785479`; `parse_corpus` and the post-run check sequence explain the refusal.

Next: repair the parser using retained interleaved-output fixtures and negative controls; reconcile all cases and unsupported/shared-trunk counts. A strict qualification still needs the missing post-run custody evidence; rerun through a published row if that evidence cannot be recovered. Filing uses `--no-reclaim` to preserve original logs and launcher for this follow-up.
