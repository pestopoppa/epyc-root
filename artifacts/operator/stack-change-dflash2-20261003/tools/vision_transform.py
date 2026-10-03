#!/usr/bin/env python3
"""STACKCHG-DFLASH2-20261003 — vision transform: Qwen3-VL-30B :8086 MI210 -> CPU, COLD (WARM tier).

Operator intent (2026-10-03, refined via workspace-89): the VL-30B vision server leaves the
MI210 so the :8083 27B can run DFlash2; it moves to a CPU placement, COLD/on-demand:
registered but NOT launched by a default `start` (WARM tier). NOT retired, NOT deprecated —
weights stay, it returns to a GPU when the 2nd MI210 arrives (operator reassesses topology then).

Every edit is exact-once; the script aborts on 0 or >1 anchor matches (drift).
usage: vision_transform.py <sandbox-root containing research/ and orchestrator/>
"""
from __future__ import annotations

import sys
from pathlib import Path

TAG = "STACKCHG-DFLASH2-20261003"

EDITS: list[tuple[str, str, str]] = [
    # ── master: server_mode.worker_vision ─────────────────────────────────────────────
    ("research/orchestration/model_registry.yaml",
     "    memory_gb: 0        # host RAM: weights are fully offloaded (-ngl 999)\n",
     f"    # {TAG}: CPU placement (cold). Host RAM = weights + mmproj on disk,\n"
     "    # 17.28 + 1.01 GiB (18,556,687,200 + 1,083,499,584 B). Was 0 while -ngl 999 put them in VRAM.\n"
     "    memory_gb: 18.3\n"
     "    # (was, MI210) memory_gb: 0        # host RAM: weights are fully offloaded (-ngl 999)\n"),
    ("research/orchestration/model_registry.yaml",
     "    # group's capacity check ever seeing it, which is the failure mode being closed.\n"
     "    tier: hot\n"
     "    # ── 2026-09-22: THIS ROLE STAYS ON THE MI210. ────────────────────────────────────\n",
     "    # group's capacity check ever seeing it, which is the failure mode being closed.\n"
     f"    # ── {TAG}: COLD. Operator 2026-10-03 \"Vision down, canonical DFlash2\", refined:\n"
     "    # CPU placement, registered but NOT started by a default `start` (WARM). It must not be\n"
     "    # hot-resident on CPU (DS41 runs continuous CPU A/Bs). Start on demand:\n"
     "    #   orchestrator_stack.py start --only worker_vision   (or --include-warm worker_vision)\n"
     "    # Returns to a GPU when the 2nd MI210 arrives; the operator reassesses topology then.\n"
     "    tier: warm\n"
     "    # (was) tier: hot\n"
     "    # ── 2026-09-22: THIS ROLE STAYS ON THE MI210. ────────────────────────────────────\n"
     f"    # ⚠ SUPERSEDED by {TAG} (operator 2026-10-03): DFlash2 on the 27B needs ~43 GiB\n"
     "    # and does not fit beside this role (gate: 65.16 needed vs 62.00 budget). The GPU-only\n"
     "    # fields below (vram_mb, serving_shape.vram_non_kv_gib, the 112.20 t/s MI210 prior) are\n"
     "    # KEPT as the GPU-restore record; nothing reads them off the gpu_host_lane.\n"),
    ("research/orchestration/model_registry.yaml",
     "    device: ROCm0\n"
     "    acceleration:\n"
     "      type: baseline    # VL + mmproj is not supported by the speculative binary\n"
     "    throughput: 112.20  # t/s decode, median over n=250 MMMU turns on MI210 (2026-07-31)\n",
     f"    device: none        # {TAG}: CPU (launcher emits --device none; CPU binary). Was ROCm0.\n"
     "    acceleration:\n"
     "      type: baseline    # VL + mmproj is not supported by the speculative binary\n"
     "    throughput: 112.20  # t/s decode, median over n=250 MMMU turns on MI210 (2026-07-31).\n"
     f"                        # {TAG}: MI210 figure. CPU throughput at the declared NUMA_HALF_A\n"
     "                        # placement is UNMEASURED (only CPU runs: 2026-07-17 K35, -t 96).\n"),
    # ── master: roles.worker_vision / roles.vision_escalation ─────────────────────────
    ("research/orchestration/model_registry.yaml",
     "    serving:\n"
     "      device: ROCm0\n"
     "      n_gpu_layers: 999\n"
     "      n_ctx: 16384             # MEASURED SHAPE.",
     "    serving:\n"
     f"      device: none             # {TAG}: CPU, cold (was ROCm0, n_gpu_layers: 999)\n"
     "      n_ctx: 16384             # MEASURED SHAPE."),
    ("research/orchestration/model_registry.yaml",
     "    memory:\n"
     "      residency: hot\n"
     "      pinned: false\n"
     "    server:\n"
     "      endpoint: \"http://localhost:8086\"\n",
     "    memory:\n"
     f"      residency: warm          # {TAG}: cold CPU, started on demand (was hot)\n"
     "      pinned: false\n"
     "    server:\n"
     "      endpoint: \"http://localhost:8086\"\n"),
    ("research/orchestration/model_registry.yaml",
     "    serving:\n"
     "      device: ROCm0\n"
     "      n_ctx: 16384            # the shape everything measured was taken at\n",
     "    serving:\n"
     f"      device: none            # {TAG}: rides worker_vision, now CPU (was ROCm0)\n"
     "      n_ctx: 16384            # the shape everything measured was taken at\n"),
    ("research/orchestration/model_registry.yaml",
     "    memory:\n"
     "      residency: hot\n"
     "      pinned: false\n"
     "      note: \"No additional residency — shares worker_vision's single 21049 MB VRAM allocation.",
     "    memory:\n"
     f"      residency: warm         # {TAG}: rides the cold worker_vision process (was hot)\n"
     "      pinned: false\n"
     "      note: \"No additional residency — shares worker_vision's single allocation (CPU since 2026-10-03; was 21049 MB VRAM)."),
    # ── master: process_layout ────────────────────────────────────────────────────────
    ("research/orchestration/model_registry.yaml",
     "  #   :8086                = worker_vision + vision_escalation (one process; now CPU, so the\n"
     "  #                          21049 MB VRAM figure that used to be quoted here is gone)\n",
     f"  #   :8086                = worker_vision + vision_escalation — {TAG}: MOVED to\n"
     "  #                          warm_mmap below (CPU, cold, started on demand).\n"),
    ("research/orchestration/model_registry.yaml",
     "  - ingest_long_context   # 2026-09-22: alias on the :8083 27B (host architect_critic since ARCHSWAP-20260927)\n"
     "  - worker_vision\n"
     "  - vision_escalation\n"
     "  warm_mmap: []\n",
     "  - ingest_long_context   # 2026-09-22: alias on the :8083 27B (host architect_critic since ARCHSWAP-20260927)\n"
     "  warm_mmap:\n"
     f"  - worker_vision         # {TAG}: CPU, COLD — registered, not started by a default `start`\n"
     "  - vision_escalation     # alias on the same :8086 process\n"),
    # ── orchestrator: launch_manifest ─────────────────────────────────────────────────
    ("orchestrator/orchestration/launch_manifest.yaml",
     "  - ingest_long_context\n"
     "  - worker_vision\n"
     "  - vision_escalation\n"
     "\n"
     "# Roles that must never run concurrently",
     "  - ingest_long_context\n"
     f"  # worker_vision / vision_escalation REMOVED {TAG}: :8086 is a COLD (warm-tier) CPU\n"
     "  # role while the MI210 carries DFlash2. Keeping them here would make the /health fallback\n"
     "  # probes report a deliberately-stopped server as down.\n"
     "\n"
     "# Roles that must never run concurrently"),
    ("orchestrator/orchestration/launch_manifest.yaml",
     "  worker_vision:\n"
     "    tier: hot\n"
     "    mode: vision\n",
     "  worker_vision:\n"
     f"    tier: warm   # {TAG}: CPU, cold — `start` skips it; start --only/--include-warm worker_vision\n"
     "    mode: vision\n"),
    # ── orchestrator: stack_topology numa_config.worker_vision ───────────────────────
    ("orchestrator/orchestration/stack_topology.yaml",
     "    instances:\n"
     "      - {cpu_shape: GPU_HOST_LANE, port: 8086}\n"
     "    gpu_host_lane: true\n"
     "    # 2026-08-01 W1 CUTOVER:",
     f"    # ── {TAG}: OFF THE MI210, onto CPU, COLD (tier warm). ──────────────────────\n"
     "    # Operator 2026-10-03: the 27B on :8083 runs DFlash2 (~43 GiB), which does not fit\n"
     "    # beside this 22.3 GiB VL on one MI210. The topology forces a cpuset for any launched\n"
     "    # role, so it is DECLARED: NUMA_HALF_A = cores 0-47 + SMT siblings 96-143 (NPS4 nodes\n"
     "    # 0,1), -t 48, interleave=0,1. GPU-disjoint (the 27B's host lane 184-191 is in half B).\n"
     "    # It overlaps frontdoor :8070 (0-95) and :8080 (half A) WHEN STARTED; it is never\n"
     "    # started by a default `start`. No mlock (cold: would pin 18.3 GiB while up).\n"
     "    # The operator reassesses this placement when the 2nd MI210 arrives.\n"
     "    instances:\n"
     "      - {cpu_shape: NUMA_HALF_A, port: 8086}\n"
     "    numa_pre_evict_gib: 40   # INF-70/C7 CPU role: force even interleave (see header)\n"
     "    numactl_policy: interleave=0,1\n"
     "    # (was, MI210) instances: [{cpu_shape: GPU_HOST_LANE, port: 8086}], gpu_host_lane: true,\n"
     "    # numactl_policy: membind=3 — restore these with device ROCm0 on the 2nd MI210.\n"
     "    # 2026-08-01 W1 CUTOVER:"),
    ("orchestrator/orchestration/stack_topology.yaml",
     "    # which is the exact cross-node defect the 2026-07-30 placement audit found.\n"
     "    numactl_policy: membind=3\n"
     "\n"
     "  # vision_escalation ENTRY REMOVED",
     "    # which is the exact cross-node defect the 2026-07-30 placement audit found.\n"
     "\n"
     "  # vision_escalation ENTRY REMOVED"),
    # ── orchestrator: stack_templates/default.yaml ───────────────────────────────────
    ("orchestrator/stack_templates/default.yaml",
     "    model: Qwen3-VL-30B-A3B-Instruct\n"
     "    quant: Q4_K_M\n"
     "    tier: HOT\n"
     "    ram_gb: 17.3\n"
     "    full:\n"
     "      port: 8086\n"
     "      numa: GPU_HOST_LANE\n"
     "      threads: 8\n",
     "    model: Qwen3-VL-30B-A3B-Instruct\n"
     "    quant: Q4_K_M\n"
     f"    tier: WARM   # {TAG}: CPU, cold — not launched by a default start (was HOT, MI210)\n"
     "    ram_gb: 17.3\n"
     "    full:\n"
     "      port: 8086\n"
     "      numa: HALF_A\n"
     "      threads: 48\n"),
    ("orchestrator/stack_templates/default.yaml",
     "#   * architect_critic and worker_vision are MI210 roles: the model is on the\n"
     "#     GPU and only 8 HOST threads are pinned, on GPU_HOST_LANE (184-191).\n",
     "#   * architect_critic is the MI210 role: the model is on the GPU and only 8\n"
     "#     HOST threads are pinned, on GPU_HOST_LANE (184-191). worker_vision is a\n"
     f"#     COLD CPU role on NUMA_HALF_A since {TAG} (WARM: not started by default).\n"),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    root = Path(sys.argv[1]).resolve()
    pending: dict[Path, str] = {}
    for rel, old, new in EDITS:
        path = root / rel
        text = pending.get(path) or path.read_text(encoding="utf-8")
        n = text.count(old)
        if n != 1:
            print(f"ABORT: {rel}: anchor matched {n} times (need 1):\n{old[:160]!r}")
            return 2
        pending[path] = text.replace(old, new)
    for path, text in pending.items():
        path.write_text(text, encoding="utf-8")
        print(f"edited {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
