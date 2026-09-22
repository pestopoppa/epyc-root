#!/usr/bin/env python3
"""PHASE 3 of change-role: assert every alias relationship is well-formed.

    assert_alias_clean.py --alias A --host H [--scratch DIR]
    assert_alias_clean.py --all [--scratch DIR]

Exit 0 clean · 2 one or more refusals · 1 usage.

Each check exists because the corresponding defect blocked a real cutover on
2026-09-22. None of them compares one restatement against another: every one
recomputes from `server_mode` and diffs.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "retire-model" / "scripts"))
from common import artifacts_of, load_sources  # noqa: E402


class Fails:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def add(self, rule: str, locator: str, detail: str) -> None:
        self.items.append((rule, locator, detail))


def hosts_of(sm: dict) -> dict[str, str]:
    """alias -> host, recomputed from `shared_with`. The ONLY binding."""
    out: dict[str, str] = {}
    for host, cfg in sm.items():
        if not isinstance(cfg, dict):
            continue
        for alias in cfg.get("shared_with") or []:
            out[str(alias)] = str(host)
    return out


def check(src: dict, alias: str, host: str | None, f: Fails) -> None:
    sm, roles = src["server_mode"], src["roles"]
    manifest, topo = src["manifest"], src["topology"]
    binding = hosts_of(sm)
    row = sm.get(alias) if isinstance(sm.get(alias), dict) else None

    # R1 -- alias_of without shared_with
    declared_host = row.get("alias_of") if row else None
    bound_host = binding.get(alias)
    if declared_host and not bound_host:
        f.add("R1 alias_of-without-shared_with", f"server_mode.{alias}.alias_of={declared_host}",
              "`alias_of` is DOCUMENTATION; `shared_with` is the binding. `server_mode.worker` had "
              "the first and not the second on 2026-09-22, so the registry validator could not "
              "resolve its numa_ports to any launching topology and REFUSED to start the stack "
              "('a fleet nothing launches is a phantom'). Add the alias to "
              f"server_mode.{declared_host}.shared_with.")
    if declared_host and bound_host and declared_host != bound_host:
        f.add("R1b alias_of disagrees with shared_with", f"server_mode.{alias}",
              f"alias_of={declared_host} but shared_with puts it on {bound_host}. The binding wins; "
              "the documentation key must not contradict it.")

    host = host or bound_host or declared_host
    if host is None:
        f.add("R0 no host", f"server_mode.{alias}",
              "this role is not in any host's shared_with and declares no alias_of -- it is not "
              "an alias at all. Classify the change first (classify.py).")
        return
    host_cfg = sm.get(host)
    if not isinstance(host_cfg, dict):
        f.add("R0 missing host row", f"server_mode.{host}", "the named host has no server_mode row")
        return

    # R2 -- an alias with its own PROCESS declaration
    if row is not None:
        for key in ("numa_ports", "numa_instances"):
            if row.get(key):
                f.add("R2 alias declares its own process", f"server_mode.{alias}.{key}={row[key]!r}",
                      "an alias has NO process of its own. A routing-metadata row is legal; a row "
                      "that declares NUMA fanout is a second server the launcher will try to start.")
        if row.get("port") is not None and host_cfg.get("port") is not None \
                and row["port"] != host_cfg["port"]:
            f.add("R2b alias port differs from host", f"server_mode.{alias}.port={row['port']}",
                  f"host {host} serves on {host_cfg['port']}. The dead-:8070 coder_escalation row "
                  "was exactly this defect.")

        # R5 -- model_role pointing at a different artifact than the host's
        if row.get("model_role") and host_cfg.get("model_role") \
                and row["model_role"] != host_cfg["model_role"]:
            f.add("R5 model_role mismatch", f"server_mode.{alias}.model_role={row['model_role']!r}",
                  f"host {host} runs model_role={host_cfg['model_role']!r}. model_role is "
                  "LOAD-BEARING, not documentation (model_descriptors.py substitutes the "
                  "model_role row's config for an alias). On 2026-09-22 frontdoor.model_role still "
                  "named the NON-MTP qwen36_q8_0 while the process ran the MTP artifact, and "
                  "compile_descriptors refused it with 'Role-server conflict'.")
        alias_arts, host_arts = artifacts_of(row), artifacts_of(host_cfg)
        if alias_arts and host_arts and not (alias_arts & host_arts):
            f.add("R5b alias row names a different artifact", f"server_mode.{alias}.model",
                  f"{sorted(alias_arts)} vs host {sorted(host_arts)}")

    # R3 -- numa_config for a role that launches nothing
    if (topo.get("numa_config") or {}).get(alias):
        f.add("R3 alias has a numa_config block", f"stack_topology.numa_config.{alias}",
              "a role with no process must carry no NUMA wiring. Leaving worker_general's and "
              "ingest_long_context's blocks in place kept the launcher declaring :8072/:8082/:8182 "
              "and :8085/:8185/:8285 against a master that no longer had those ports -- the "
              "declaration-parity violation that blocked the cutover.")

    # R4 -- role_launch_meta for a role that launches nothing
    if (manifest.get("role_launch_meta") or {}).get(alias):
        f.add("R4 alias has a role_launch_meta entry", f"launch_manifest.role_launch_meta.{alias}",
              "every other alias is absent from this table; an entry here tags the role as one the "
              "launcher starts.")

    # R6 -- roles.<alias>.model naming a previous lineup's artifact
    role_row = roles.get(alias)
    host_arts = artifacts_of(host_cfg)
    if isinstance(role_row, dict):
        a = artifacts_of(role_row)
        if a and host_arts and not (a & host_arts):
            f.add("R6 roles.<alias>.model is stale", f"roles.{alias}.model",
                  f"names {sorted(x for x in a if '/' in x) or sorted(a)} while the server it rides "
                  f"runs {sorted(x for x in host_arts if '/' in x) or sorted(host_arts)}. "
                  "compile_descriptors refuses this ('Role-server conflict'). On 2026-09-22 "
                  "roles.worker_math still named Qwen2.5-Math-7B and roles.toolrunner still named "
                  "Qwen3-Coder-30B -- artifacts those roles had not been served by for two lineups.")

    # R7 -- port_map restatement
    pm = (manifest.get("port_map") or {}).get(alias)
    if pm is not None and host_cfg.get("port") is not None and pm != host_cfg["port"]:
        f.add("R7 port_map disagrees with the host", f"launch_manifest.port_map.{alias}={pm}",
              f"host {host} serves on {host_cfg['port']}. port_map is a restatement of "
              "`shared_with`; the manifest's own header says Phase 2 stops restating it.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alias")
    ap.add_argument("--host")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scratch")
    args = ap.parse_args()
    if not args.all and not args.alias:
        ap.error("pass --alias A [--host H] or --all")

    src = load_sources(args.scratch)
    f = Fails()
    if args.all:
        targets = sorted(set(hosts_of(src["server_mode"])) |
                         {n for n, c in src["server_mode"].items()
                          if isinstance(c, dict) and c.get("alias_of")})
        print(f"checking {len(targets)} alias relationship(s): {', '.join(targets)}\n")
        for alias in targets:
            check(src, alias, None, f)
    else:
        check(src, args.alias, args.host, f)

    for rule, locator, detail in f.items:
        print(f"REFUSE  {rule}")
        print(f"        {locator}")
        print(f"        {detail}\n")
    if f.items:
        print(f"REFUSED: {len(f.items)} alias defect(s).", file=sys.stderr)
        return 2
    print("PASS: every alias relationship checked is well-formed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
