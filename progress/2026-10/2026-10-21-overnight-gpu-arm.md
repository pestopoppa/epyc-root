# 2026-10-21 overnight-gpu-arm
- Prepared and armed two chained GPU launchers for the 2026-10-22 D4g window (see `/mnt/raid0/llm/tmp/overnight-gpu-arm-20261022/`).
- Job 1 chunk-KV P0 GPU stages (champion gpu-20261020-dd3d9721c): starts on GPU_ALLOWED_FROM + PB_QCOST_1_ENDED, hard stop 04:15Z.
- Job 2 speech D1 probes (Step-Audio-2-mini, Qwen3-Omni-30B-A3B): starts on job1 flag or 04:15Z, hard stop 06:00Z. Downloads hash-verified against HF.
- Both skip the CPU region lock by agreement with f8 (via 5c); host threads 184-191; labelled "GPU job beside f8 s4". Launchers die on host reboot.
- Fixes in p0_timing.sh: nested region-lock bypass, added nvme stage, O_DIRECT dropped (unsupported on overlay fs), P0_OUT and GPU_BIN_OVERRIDE.
