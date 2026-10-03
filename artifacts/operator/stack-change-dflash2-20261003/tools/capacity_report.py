#!/usr/bin/env python3
"""Both capacity legs, per instance, for one orchestrator tree (fresh import = the real gate).

usage: capacity_report.py <orch-tree>   (run with the orchestrator venv python)
Pure arithmetic over the tree's compiled lean + topology; reads /proc/meminfo; starts nothing.
"""
import json
import sys

tree = sys.argv[1]
sys.path.insert(0, tree)
try:
    import scripts.server.stack_manifest as sm
except Exception as exc:  # noqa: BLE001
    print(f"IMPORT-TIME CAPACITY/PARITY GATE: FAIL -> {type(exc).__name__}: {exc}")
    sys.exit(3)
print("IMPORT-TIME CAPACITY/PARITY GATE: PASS")
print(f"HOT_SERVERS  ports: {sorted({s.get('port') for s in sm.HOT_SERVERS if isinstance(s, dict)})}"
      if sm.HOT_SERVERS and isinstance(sm.HOT_SERVERS[0], dict) else f"HOT_SERVERS: {len(sm.HOT_SERVERS)}")
print(f"WARM_SERVERS: {[getattr(s, 'role', None) or (s.get('role') if isinstance(s, dict) else s) for s in sm.WARM_SERVERS]}")
print("\nper instance:")
print(f"  {'role':22} {'port':>5} {'shape_class':16} {'on_gpu':6} {'n_ctx':>7} {'kv_gib':>7} {'vram_nonkv':>10} {'host_w':>7}")
for r in sm.serving_shape_instances():
    print(f"  {r['role']:22} {str(r.get('port')):>5} {str(r.get('shape_class')):16} {str(r.get('on_gpu')):6} "
          f"{str(r.get('n_ctx')):>7} {r['kv_gib']:>7.2f} {str(r.get('vram_non_kv_gib')):>10} {str(r.get('host_weights_gib')):>7}")
rep = sm.serving_shape_capacity_report()
fit = rep["gpu"]["fit"]
print("\nGPU leg (ROCm0):")
print(json.dumps({"ok": fit.ok, "required_gib": fit.required_gib, "budget_gib": fit.budget_gib,
                  "capacity_gib": fit.capacity_gib, "headroom_gib": fit.headroom_gib,
                  "per_role_gib": fit.per_role, "source": str(fit.capacity_source)}, indent=1, default=str))
print("host leg (CPU RAM):")
print(json.dumps(rep["host"], indent=1, default=str))
