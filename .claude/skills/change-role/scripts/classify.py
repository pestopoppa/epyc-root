#!/usr/bin/env python3
"""PHASE 2 of change-role: decide WHICH of the three shapes this change is.

    classify.py <role> --alias-of <host>     # candidate shape (a)
    classify.py <role> --to <model-row-id>   # candidate shape (b)
    classify.py <role> --own-server          # candidate shape (c)

Exit 0  shape (a) or (b); the printed surface list is the change set
Exit 3  shape (c) -- this is a TOPOLOGY event; run `change-topology`
Exit 2  the requested change contradicts the sources (message says how)
Exit 1  usage

Classify first, because the blast radius differs by an order of magnitude: an
alias re-point touches five restatements and launches nothing new, while a role
becoming its own server changes cpusets and triggers the contention-matrix
recert cascade. Doing (c) with (a)'s checklist is how a lineup change turns into
nine pipeline runs with the stack down.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# common.py is shared with the retire-model sub-skill; both read the same
# sources and must resolve a role to its server the same way the compiler does.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "retire-model" / "scripts"))
from common import artifacts_of, load_sources, server_for_role  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--alias-of", metavar="HOST")
    g.add_argument("--to", metavar="MODEL_ROW_ID")
    g.add_argument("--own-server", action="store_true")
    ap.add_argument("--scratch")
    args = ap.parse_args()

    src = load_sources(args.scratch)
    sm, roles = src["server_mode"], src["roles"]
    manifest, topo = src["manifest"], src["topology"]
    role = args.role

    own_row = sm.get(role) if isinstance(sm.get(role), dict) else None
    numa = (topo.get("numa_config") or {}).get(role)
    meta = (manifest.get("role_launch_meta") or {}).get(role)
    cur_server, cur_cfg, cur_binding = server_for_role(src, role)
    is_alias_now = cur_binding in ("server_mode.model_role", "server_mode.shared_with") or (
        own_row is not None and own_row.get("alias_of")
    )

    print(f"role            {role}")
    print(f"currently       server={cur_server} binding={cur_binding} "
          f"own_server_mode_row={'yes' if own_row else 'no'} "
          f"numa_config={'yes' if numa else 'no'} role_launch_meta={'yes' if meta else 'no'}")

    def surfaces(rows: list[tuple[str, str]]) -> None:
        print("\nchange set (every row goes in the patch; a surface you skip is one you must"
              "\nbe able to say why you skipped):")
        for where, what in rows:
            print(f"  - {where:<46} {what}")

    # ---------------- shape (c) ------------------------------------------
    if args.own_server:
        print("\nSHAPE (c)  alias becomes its own server -- a TOPOLOGY event, not a role edit.")
        print("It gains a server_mode row, a numa_config block, a role_launch_meta entry and a")
        print("port; that changes cpusets, so the contention-matrix recert cascade applies")
        print("(role-alias-change-runbook.md, Procedure B tail).")
        print("\nROUTE: run `change-topology`. Do not continue here.", file=sys.stderr)
        return 3

    # ---------------- shape (b) ------------------------------------------
    if args.to:
        target = roles.get(args.to)
        if not isinstance(target, dict):
            print(f"\nREFUSED: no `roles.{args.to}` row. The row key is the identity, not the "
                  "GGUF filename.", file=sys.stderr)
            return 2
        if target.get("deprecated"):
            print(f"\nREFUSED: roles.{args.to} is deprecated. Assigning a live role to a retired "
                  "model is the mirror of the defect that blocked the 2026-09-22 cutover.",
                  file=sys.stderr)
            return 2
        if is_alias_now and own_row is None:
            print(f"\nSHAPE (c)  {role} is an ALIAS today ({cur_binding}); giving it a model of "
                  "its own means giving it a process of its own.")
            print("\nROUTE: run `change-topology`. Do not continue here.", file=sys.stderr)
            return 3
        print(f"\nSHAPE (b)  model swap on host role {role}.")
        surfaces([
            (f"server_mode.{role}.model / model_path / model_role", f"-> {args.to}"),
            (f"server_mode.{role}.serving_shape", "DERIVE from the GGUF header, never hand-compute"),
            (f"server_mode.{role}.draft_model + acceleration", "re-validate the pair (`draft-compat`)"),
            (f"roles.{role}.model", "the role's own metadata must name the SAME artifact"),
            ("every name in this row's shared_with", "each alias's roles.<alias>.model too"),
            ("stack_topology.numa_config." + role, "memory footprint, mlock, numa_pre_evict_gib"),
            ("launch_manifest capacity", "host + GPU legs recomputed, per instance"),
            ("quality + speed evidence for the NEW model IN THIS ROLE", "needs-measurement"),
        ])
        print("\nNOTE: `serving_shape.kv_kib_per_token_f16` is DERIVED. Hand-computing it from the")
        print("documented formula over-declared six models by 4.06x on 2026-09-22, because")
        print("Qwen3.6/3.8 set `full_attention_interval: 4` and the formula counted every layer.")
        return 0

    # ---------------- shape (a) ------------------------------------------
    host = args.alias_of
    host_cfg = sm.get(host)
    if not isinstance(host_cfg, dict):
        print(f"\nREFUSED: `server_mode.{host}` does not exist. An alias rides a HOST's server "
              "row; there is nothing to ride.", file=sys.stderr)
        return 2
    if host_cfg.get("alias_of"):
        print(f"\nREFUSED: {host} is itself an alias of {host_cfg['alias_of']}. Point at the host "
              "that owns the process, not at another rider.", file=sys.stderr)
        return 2

    demotion = bool(numa or meta or (own_row and own_row.get("numa_ports")))
    print(f"\nSHAPE (a)  alias re-point{' (DEMOTION: this role owns a process today)' if demotion else ''}"
          f"  {role} -> rides server_mode.{host}")
    rows = [
        (f"server_mode.{host}.shared_with", f"APPEND {role} -- this is the load-bearing binding"),
        (f"server_mode.<old host>.shared_with", f"REMOVE {role}"),
        (f"server_mode.{role}", "delete it, or keep it ONLY as routing metadata with alias_of + "
                                "the host's port/url/model_role and no numa_ports"),
        (f"roles.{role}.model", f"must name the host's artifact: "
                                f"{sorted(artifacts_of(host_cfg)) or '(host declares none)'}"),
        (f"launch_manifest.port_map.{role}", f"-> {host_cfg.get('port')}"),
        ("src/config/models.py ServerURLsConfig", f"{role} delegates to _server_url_default({host!r})"),
        ("src/roles.py _FALLBACK_MAP", "remove same-fleet edges -- they are retry-the-same-metal "
                                       "no-ops that produced 90x churn"),
        ("orchestration/procedures/*.yaml role enums", "regenerate, never hand-edit"),
    ]
    if demotion:
        rows += [
            (f"stack_topology.numa_config.{role}", "DELETE -- a role with no process must carry no "
                                                   "NUMA wiring"),
            (f"launch_manifest.role_launch_meta.{role}", "DELETE -- it no longer launches"),
            ("the vacated ports", "record them as freed; several fail-open paths treat an unknown "
                                  "port as lock-free"),
            ("stack_templates/*.yaml", "the template is what `start` ACTUALLY launches"),
        ]
    surfaces(rows)
    print("\nThen: scripts/assert_alias_clean.py --alias "
          f"{role} --host {host}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
