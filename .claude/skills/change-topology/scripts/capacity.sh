#!/bin/bash
# Recompute the capacity report for the DECLARED lineup, both legs, per instance.
#
# Non-zero when either leg fails, and non-zero when the HOST leg is UNGATED: "capacity
# unknown" and "capacity fine" must not look the same. Pure arithmetic over the
# declarations -- it starts nothing and reads no running process.
#
# The GPU leg is only populated for instances whose TOPOLOGY shape_class is
# gpu_host_lane. A role moved between devices in the registry alone is absent from this
# leg entirely, which is why topology_check.py runs first.
set -euo pipefail
ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
cd "$ORCH"
exec uv run python - "$@" <<'PY'
import sys
sys.path.insert(0, "scripts/server")
import stack_manifest as sm

r = sm.serving_shape_capacity_report()
print(f"{'role':<22}{'inst':>5}{'port':>7}{'class':>15}{'dev':>8}{'n_ctx':>9}"
      f"{'slots':>7}{'kv GiB':>10}{'nonKV GiB':>11}")
for row in r["instances"]:
    print(f"{row['role']:<22}{row['numa_instance']:>5}{row['port']:>7}"
          f"{str(row['shape_class']):>15}{('GPU' if row['on_gpu'] else 'host'):>8}"
          f"{row['n_ctx']:>9}{row['slots']:>7}{row['kv_gib']:>10.3f}"
          f"{(row['vram_non_kv_gib'] if row['vram_non_kv_gib'] is not None else float('nan')):>11.2f}")

g, h = r["gpu"], r["host"]
print(f"\nGPU  required {g['required_gib']:.2f} GiB / budget {g['budget_gib']:.2f} GiB "
      f"(capacity {g['capacity_gib']:.2f}), KV {g['kv_gib']:.2f} -> "
      f"{'OK' if g['fit'].ok else 'OVERSUBSCRIBED'}")
for role, gib in sorted(g["per_role"].items()):
    print(f"       {role:<24}{gib:>8.2f} GiB")
print(f"HOST required {h['required_gib']:.2f} GiB "
      f"({h['weights_gib']:.2f} weights + {h['kv_gib']:.2f} KV) / budget "
      f"{h['budget_gib'] if h['budget_gib'] is not None else 'UNGATED'} GiB")

rc = 0
if not g["fit"].ok:
    print("FAIL: GPU leg oversubscribed. Lower n_ctx or quantise kv_quant for a role on ROCm0.")
    rc = 1
if not h["gated"]:
    print("FAIL: HOST leg UNGATED (/proc/meminfo unreadable). A check that did not run is not a pass.")
    rc = 1
elif not h["ok"]:
    print("FAIL: HOST leg oversubscribed.")
    rc = 1
print("CAPACITY PASS" if rc == 0 else "CAPACITY FAIL")
sys.exit(rc)
PY
