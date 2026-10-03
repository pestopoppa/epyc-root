#!/usr/bin/env python3
"""STACKCHG-DFLASH2-20261003 — re-pin the tests that DELIBERATELY pin worker_vision's placement.

Each of these tests says, in its own words, that a re-roster of the VL role must fail it and
be re-pinned in the same change ("if anyone re-rosters the VL role ... all three must move
together or this fails"). They are updated to the NEW intent at the SAME strength — the device,
cpuset, shape class, thread count and pre-evict decision stay asserted, with polarity moved
to the cold CPU placement (NUMA_HALF_A, device none). Nothing is loosened or deleted.
Exact-once replacements; aborts on drift.
usage: update_test_pins.py <orch-tree>
"""
import sys
from pathlib import Path

T = "STACKCHG-DFLASH2-20261003"
EDITS = [
    ("tests/unit/test_build_server_command_helpers.py",
     "    # Was \"none\" (CPU-only 7B lane); the unified VL process is MI210-resident.\n"
     "    assert _flag_value(cmd, \"--device\") == \"ROCm0\"\n",
     f"    # Was \"none\" (CPU-only 7B lane), then ROCm0 (MI210, 2026-08-01). {T}: the VL\n"
     "    # process is a COLD CPU role while the MI210 carries DFlash2 -> \"none\" again.\n"
     "    assert _flag_value(cmd, \"--device\") == \"none\"\n"),
    ("tests/unit/test_build_server_command_helpers.py",
     "    from scripts.server.stack_numa import GPU_HOST_LANE\n"
     "\n"
     "    lane_cpus, lane_threads = GPU_HOST_LANE\n"
     "    assert oss.NUMA_CONFIG[\"worker_vision\"][\"gpu_host_lane\"] is True\n"
     "    assert oss.NUMA_CONFIG[\"worker_vision\"][\"instances\"][0][0] == lane_cpus\n"
     "    assert {\n"
     "        entry[\"cpu_shape_class\"]\n"
     "        for entry in _stack_prior_role(\"worker_vision\")[\"serving\"][\"launch\"][\"entries\"]\n"
     "    } == {\"gpu_host_lane\"}\n"
     "    assert cmd[cmd.index(\"-t\") + 1] == str(lane_threads)\n",
     f"    # {T}: re-rostered, as this test demands, all together: the VL role is a COLD\n"
     "    # CPU role on NUMA_HALF_A (0-47,96-143, -t 48) while the MI210 carries DFlash2.\n"
     "    from scripts.server.stack_numa import NUMA_HALF_A\n"
     "\n"
     "    half_cpus, half_threads = NUMA_HALF_A\n"
     "    assert \"gpu_host_lane\" not in oss.NUMA_CONFIG[\"worker_vision\"]\n"
     "    assert oss.NUMA_CONFIG[\"worker_vision\"][\"instances\"][0][0] == half_cpus\n"
     "    assert {\n"
     "        entry[\"cpu_shape_class\"]\n"
     "        for entry in _stack_prior_role(\"worker_vision\")[\"serving\"][\"launch\"][\"entries\"]\n"
     "    } == {\"half\"}\n"
     "    assert cmd[cmd.index(\"-t\") + 1] == str(half_threads)\n"
     "    assert _flag_value(cmd, \"--device\") == \"none\"\n"),
    ("tests/unit/test_build_server_command_helpers.py",
     "    cmd = oss.build_server_command(None, 8086, vision_mode=True, vision_type=\"worker\")\n"
     "\n"
     "    assert _flag_value(cmd, \"--device\") == \"ROCm0\"\n"
     "    assert \"none\" not in _all_flag_values(cmd, \"--device\")\n",
     "    cmd = oss.build_server_command(None, 8086, vision_mode=True, vision_type=\"worker\")\n"
     "\n"
     f"    # {T}: the shared :8086 process is a COLD CPU role -> exactly one `--device none`,\n"
     "    # never a GPU device (the dispatcher must not re-add ROCm0 behind the builder).\n"
     "    assert _all_flag_values(cmd, \"--device\") == [\"none\"]\n"),
    ("tests/unit/test_build_server_command_helpers.py",
     "    assert out == [\"VISION\", \"--device\", \"ROCm0\"]\n",
     f"    # {T}: vision_escalation rides the COLD CPU :8086 process -> \"none\" (declared, not\n"
     "    # assumed: the tail still reads the role's compiled declaration).\n"
     "    assert out == [\"VISION\", \"--device\", \"none\"]\n"),
    ("tests/unit/test_orchestrator_stack_threads.py",
     "    assert registry[\"worker_vision\"][\"device\"] == \"ROCm0\"\n",
     f"    # {T}: COLD CPU role while the MI210 carries DFlash2 (was ROCm0).\n"
     "    assert registry[\"worker_vision\"][\"device\"] == \"none\"\n"),
    ("tests/unit/test_orchestrator_stack_threads.py",
     "    assert stack_numa.NUMA_INSTANCE_SHAPE_CLASSES[\"worker_vision\"] == (\"gpu_host_lane\",)\n"
     "    assert (cpus, threads) == stack_numa.GPU_HOST_LANE\n"
     "    assert stack_numa.NUMA_CONFIG[\"worker_vision\"][\"gpu_host_lane\"] is True\n"
     "    assert _nodes_spanned(cpus) == {3}, \"the GPU host lane is node-aligned on node 3\"\n",
     f"    # {T}: one CPU half (NPS4 nodes 0,1), GPU-disjoint from the 27B's lane on node 3.\n"
     "    assert stack_numa.NUMA_INSTANCE_SHAPE_CLASSES[\"worker_vision\"] == (\"half\",)\n"
     "    assert (cpus, threads) == stack_numa.NUMA_HALF_A\n"
     "    assert \"gpu_host_lane\" not in stack_numa.NUMA_CONFIG[\"worker_vision\"]\n"
     "    assert _nodes_spanned(cpus) == {0, 1}, \"NUMA_HALF_A spans exactly NPS4 nodes 0 and 1\"\n"
     "    assert stack_numa.NUMA_CONFIG[\"worker_vision\"][\"numactl_policy\"] == \"interleave=0,1\"\n"),
    ("tests/unit/test_stack_numa_evict.py",
     "CPU_LLAMA_SERVER_ROLES = {\"frontdoor\", \"eval_batch_frontdoor\", \"architect_general\"}\n"
     "GPU_HOST_LANE_ROLES = {\"architect_critic\", \"worker_vision\"}\n",
     f"# {T}: worker_vision moved GPU host lane -> cold CPU (NUMA_HALF_A): it is now a CPU\n"
     "# llama-server role and pre-evicts like every other one.\n"
     "CPU_LLAMA_SERVER_ROLES = {\"frontdoor\", \"eval_batch_frontdoor\", \"architect_general\", \"worker_vision\"}\n"
     "GPU_HOST_LANE_ROLES = {\"architect_critic\"}\n"),
]


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    pending: dict[Path, str] = {}
    for rel, old, new in EDITS:
        p = root / rel
        text = pending.get(p) or p.read_text(encoding="utf-8")
        n = text.count(old)
        if n != 1:
            print(f"ABORT: {rel}: anchor matched {n} times:\n{old[:200]!r}")
            return 2
        pending[p] = text.replace(old, new)
    for p, text in pending.items():
        p.write_text(text, encoding="utf-8")
        print(f"edited {p.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
