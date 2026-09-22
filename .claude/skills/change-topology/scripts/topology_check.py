#!/usr/bin/env python3
"""Assert a topology declaration before it is compiled. Exits non-zero on any violation.

Five checks, each recomputed from the source rather than compared against a copy:

  1. SHAPE TABLE PARITY  - every shape an instance names exists in BOTH _CPU_SHAPES
     and _SHAPE_CLASSES, and every shape in _CPU_SHAPES has a class. A shape in the
     first table only raises KeyError while building NUMA_INSTANCE_SHAPE_CLASSES, at
     import, for everyone.
  2. UNDERSUBSCRIPTION   - a non-GPU shape whose thread count is below its cpuset's
     PHYSICAL core count is fatal in _assert_instance_invariants. stack_numa.py carries
     no exemption mechanism, so such a shape may only be added together with one
     (`UNDERSUBSCRIBED_SHAPES`). This is the NUMA_FULL_T48 = ("0-95", 48) case.
  3. CO-PLACEMENT        - two instances of one role IN THE SAME SHAPE CLASS may not
     share cores. Full-vs-half intersection is the declared `numa_mode: both` shape and
     is not a violation; half-vs-half intersection is oversubscription with no name.
  4. PHANTOM INSTANCES   - a numa_config block for a role that launches no server of its
     own (it is an alias in someone's shared_with, or it has no role_launch_meta row).
     Phantoms consume capacity budget nothing allocates and produce declaration-parity
     violations that block every later pipeline stage.
  5. DEVICE PARITY       - the capacity report decides "GPU role" from
     shape_class == "gpu_host_lane" (stack_manifest.py:1429), NOT from the registry's
     `device:` key. A device move authored in the registry alone leaves the role summed
     against host RAM while its weights go to VRAM; a topology-only move raises for a
     missing vram_non_kv_gib. Both halves must move in one diff.

With --intent <yaml>, also gates n_ctx: a declared increase must carry either an
`n_ctx_evidence` reference or an explicit `UNVALIDATED: true`.

Read-only. Starts nothing, writes nothing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")


def parse_cpus(spec: str) -> set[int]:
    out: set[int] = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orchestrator", type=Path, default=ORCH)
    ap.add_argument("--intent", type=Path, help="stack-change intent YAML to gate n_ctx against")
    ap.add_argument("--physical-max", type=int, default=96,
                    help="highest PHYSICAL core id + 1 on this host (SMT siblings are above it)")
    args = ap.parse_args()

    sys.path.insert(0, str(args.orchestrator))
    sys.path.insert(0, str(args.orchestrator / "scripts" / "server"))
    try:
        import stack_numa as sn
        import stack_manifest as sm
    except Exception as exc:  # noqa: BLE001 - an import failure IS the finding
        print(f"FAIL: the declaration does not import: {type(exc).__name__}: {exc}")
        print("      stack_numa/stack_manifest validate at import; fix that before anything else.")
        return 1

    problems: list[str] = []

    # ---- 1. shape table parity -------------------------------------------------
    shapes = dict(sn._CPU_SHAPES)
    classes = dict(sn._SHAPE_CLASSES)
    for name in sorted(set(shapes) - set(classes)):
        problems.append(
            f"[shape-table] {name!r} is in _CPU_SHAPES but NOT in _SHAPE_CLASSES. "
            "NUMA_INSTANCE_SHAPE_CLASSES builds by _SHAPE_CLASSES[name] and will raise "
            "KeyError at import for the first instance that names it. Land both in one diff."
        )
    for name in sorted(set(classes) - set(shapes)):
        problems.append(
            f"[shape-table] {name!r} has a class but no cpuset in _CPU_SHAPES; "
            "a declaration naming it is rejected as an unknown shape."
        )
    declared_shapes = set()
    for role, names in getattr(sn, "NUMA_INSTANCE_SHAPE_NAMES", {}).items():
        declared_shapes.update(names)
    for role in sn.NUMA_CONFIG:
        cls = sn.NUMA_INSTANCE_SHAPE_CLASSES.get(role, ())
        if not cls:
            problems.append(f"[shape-table] role {role!r} has instances but no resolved shape classes")

    # ---- 2. undersubscription --------------------------------------------------
    numa_src = (args.orchestrator / "scripts" / "server" / "stack_numa.py").read_text()
    allow = set(re.findall(r'UNDERSUBSCRIBED_SHAPES[^\n]*?=\s*[^\n]*', numa_src))
    allowlisted = set(re.findall(r'"([A-Z0-9_]+)"', " ".join(allow)))
    # Shapes actually NAMED by a declared instance are fatal; an unused table entry that
    # could never be declared correctly is a TRAP, reported but not a blocker on someone
    # else's topology change (precedent: NUMA_NODE0/NUMA_NODE1, deleted 2026-08-11 for
    # exactly this shape of defect).
    in_use: set[str] = set()
    for names in getattr(sn, "NUMA_INSTANCE_SHAPE_NAMES", {}).values():
        in_use.update(names)
    if not in_use:  # loader did not export the names; fall back to matching cpusets
        for cfg in sn.NUMA_CONFIG.values():
            for cpus, _port, threads in (cfg.get("instances") or []):
                for name, (scpus, sthreads) in shapes.items():
                    if scpus == cpus and sthreads == threads:
                        in_use.add(name)
    traps: list[str] = []
    for name, (cpus, threads) in sorted(shapes.items()):
        if classes.get(name) == "gpu_host_lane":
            continue  # a host lane is not a decode instance; the rule does not apply
        phys = len([c for c in parse_cpus(cpus) if c < args.physical_max])
        if threads == phys:
            continue
        sink = problems if name in in_use else traps
        if threads > phys:
            sink.append(
                f"[undersubscription] shape {name!r} = ({cpus!r}, {threads}) is SMT-OVERsubscribed: "
                f"{threads} threads over {phys} physical cores. _assert_instance_invariants fatals "
                "on this at import."
            )
        elif name not in allowlisted:
            sink.append(
                f"[undersubscription] shape {name!r} = ({cpus!r}, {threads}) declares FEWER threads "
                f"than the {phys} physical cores in its cpuset. _assert_instance_invariants requires "
                "-t to EQUAL the physical core count, so this shape fatals at import unless "
                "stack_numa.py also gains an exemption naming it (an UNDERSUBSCRIBED_SHAPES set). "
                "_CPU_SHAPES + _SHAPE_CLASSES + the exemption land in ONE diff."
            )

    # ---- 3. co-placement -------------------------------------------------------
    for role, cfg in sorted(sn.NUMA_CONFIG.items()):
        insts = cfg.get("instances") or []
        klasses = sn.NUMA_INSTANCE_SHAPE_CLASSES.get(role, ())
        for i in range(len(insts)):
            for j in range(i + 1, len(insts)):
                ki = klasses[i] if i < len(klasses) else None
                kj = klasses[j] if j < len(klasses) else None
                if ki != kj or ki is None:
                    continue  # full-vs-half is the declared `both` shape
                shared = parse_cpus(insts[i][0]) & parse_cpus(insts[j][0])
                if shared:
                    problems.append(
                        f"[co-placement] {role}[{i}] :{insts[i][1]} and {role}[{j}] :{insts[j][1]} "
                        f"are both shape class {ki!r} and share {len(shared)} cores. Same-class "
                        "instances launch together; the capacity report counts them as independent."
                    )

    # ---- 4. phantom instances --------------------------------------------------
    launch_meta = set(sm._MANIFEST["role_launch_meta"])
    aliases: dict[str, str] = {}
    for host, row in sm.MASTER_SERVER_MODE.items():
        for alias in (row.get("shared_with") or []):
            aliases[alias] = host
    for role in sorted(sn.NUMA_CONFIG):
        if role in aliases:
            problems.append(
                f"[phantom] role {role!r} carries a numa_config block but is an ALIAS of "
                f"{aliases[role]!r} (server_mode.{aliases[role]}.shared_with). A role that launches "
                "no server of its own must carry NO numa wiring: the block produces phantom "
                "instances in the capacity report and declaration-parity violations downstream."
            )
        elif role not in launch_meta:
            problems.append(
                f"[phantom] role {role!r} carries a numa_config block but has no "
                "launch_manifest.role_launch_meta row, so nothing launches it."
            )

    # ---- 5. device parity ------------------------------------------------------
    for row in sm.serving_shape_instances():
        declared = (row.get("device") or "").strip() or None
        on_gpu = bool(row["on_gpu"])
        gpu_by_registry = bool(declared) and declared.lower() not in {"cpu", "host"}
        if on_gpu and not gpu_by_registry:
            problems.append(
                f"[device] {row['role']}[{row['numa_instance']}] :{row['port']} has shape_class "
                f"'gpu_host_lane' (=> the capacity report scores it against VRAM) while the master "
                f"registry declares device={declared!r}. Move BOTH or neither."
            )
        if gpu_by_registry and not on_gpu:
            problems.append(
                f"[device] {row['role']}[{row['numa_instance']}] :{row['port']} declares "
                f"device={declared!r} in the registry but its topology shape_class is "
                f"{row['shape_class']!r}, so the capacity report scores it against HOST RAM and it "
                "will never be checked for VRAM fit. This is the registry-only device move."
            )
        if on_gpu and not isinstance(row.get("vram_non_kv_gib"), (int, float)):
            problems.append(
                f"[device] {row['role']} is on the GPU leg with no serving_shape.vram_non_kv_gib. "
                "Re-measure it on a real load (scripts/measure/vram_headroom_probe.py); never copy "
                "vram_gib, which is KV-inclusive."
            )

    # ---- optional: n_ctx intent gate -------------------------------------------
    if args.intent:
        import yaml
        intent = yaml.safe_load(args.intent.read_text()) or {}
        topo = (intent.get("topology") or {})
        for role, spec in topo.items():
            if not isinstance(spec, dict) or "n_ctx" not in spec:
                continue
            try:
                current = sm.master_serving_shape(role)[0].get("n_ctx")
            except Exception:  # noqa: BLE001
                current = None
            new = spec["n_ctx"]
            if current is not None and new <= current:
                continue
            if not (spec.get("n_ctx_evidence") or spec.get("UNVALIDATED") is True):
                problems.append(
                    f"[n_ctx] intent raises {role} n_ctx {current} -> {new} with neither an "
                    "`n_ctx_evidence` reference nor `UNVALIDATED: true`. A context you have not "
                    "served at is a hypothesis; it may ship marked, not as a measured number."
                )

    if traps:
        print(f"NOTE: {len(traps)} unusable shape(s) in the table, named by ZERO instances. "
              "Not a blocker here; delete them rather than annotating them.")
        for t in traps:
            print("  " + t)

    if problems:
        print(f"TOPOLOGY CHECK FAIL: {len(problems)} violation(s)")
        for p in problems:
            print("  " + p)
        return 1
    print(f"TOPOLOGY CHECK PASS: {len(sn.NUMA_CONFIG)} roles, "
          f"{sum(len(c.get('instances') or []) for c in sn.NUMA_CONFIG.values())} instances, "
          f"{len(shapes)} shapes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
