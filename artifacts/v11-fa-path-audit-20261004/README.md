# v11 FlashAttention path audit — durable copy (2026-10-04)

The audit is by workspace-89 (read-only: no builds, no GPU or CPU workloads). workspace-ec's wrap-up copied it here
from `/mnt/raid0/llm/tmp/v11-fa-path-audit-20261004/REPORT.md`. The register-audit scripts and the v10 kernel
register table came from the audit subagent's session scratchpad. Neither source location is durable.

| File | What |
|---|---|
| `REPORT.md` | The audit: what #26046 (rocWMMA FA removal) does to gfx90a D=256 routing, risks (DF2-9), ports, recommendation |
| `register-audit/split.py` | Splits a `libggml-hip.so` `.hip_fatbin` dump on `__CLANG_OFFLOAD_BUNDLE__` and unbundles the gfx90a objects into `co/` |
| `register-audit/notes.py` | Reads `llvm-readelf --notes` on each `co/*.co` and prints FA kernels' VGPR/AGPR/spill/LDS/scratch |
| `register-audit/fa_dm.tsv` | Output for v10 `kernels/builds/gpu-20260921-ffc1bac82/bin/libggml-hip.so.0.16.0` (1704 FA kernels) |

To use the scripts: `llvm-objcopy --dump-section .hip_fatbin=fb.bin <lib>`, then `python3 split.py fb.bin`, then
`python3 notes.py co > table.tsv`.

The actionables are filed as V11-FA-1..4 in
[`handoffs/active/kv-unified-stack-rollout.md`](../../handoffs/active/kv-unified-stack-rollout.md) section C. They gate
RTG-58 P4 (KPF-40..42).
