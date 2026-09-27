#!/usr/bin/env python3
"""ARCHSWAP-20260927: relabel logs/orchestrator_state.json to the swapped role bindings.

WHY. orchestrator_stack.py keys its process state by ROLE, and runtime_attestation checks each
state row against the launch contract of that row's `role`. After the swap lands (config +
`stack_change_pipeline.py update`) the servers keep running, so the state must say
  :8074 (Flash-Next) -> architect_general,  :8083 (27B) -> architect_critic,
  coder_escalation / ingest_long_context -> architect_critic on the LIVE :8083 pid.
Left unrelabeled: 41 attestation errors, and `stop architect_critic` would stop Flash-Next.
No sanctioned command relabels state (start never overwrites existing role keys).

It starts, stops and signals NOTHING. It reads /proc/<pid>/cmdline to prove identity, and it
refuses unless BOTH processes are exactly the ones the swap describes.

usage:
  relabel_state.py [--state PATH]            dry run: print the planned rows
  relabel_state.py [--state PATH] --apply    back up, write temp, atomic rename
  relabel_state.py [--state PATH] --reverse --apply   the rollback direction
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

DEFAULT_STATE = Path("/mnt/raid0/llm/epyc-orchestrator/logs/orchestrator_state.json")
M27 = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
MFN = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
ALIASES = ("coder_escalation", "ingest_long_context")


def cmdline(pid: int) -> list[str]:
    try:
        return [a.decode() for a in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")[:-1]]
    except OSError:
        return []


def flag(argv: list[str], name: str) -> str | None:
    for i, a in enumerate(argv[:-1]):
        if a == name:
            return argv[i + 1]
    return None


def prove(pid: int, port: int, model_sub: str) -> None:
    argv = cmdline(pid)
    if not argv:
        sys.exit(f"REFUSING: pid {pid} (claimed for :{port}) is not alive")
    if flag(argv, "--port") != str(port):
        sys.exit(f"REFUSING: pid {pid} does not listen on --port {port}: {flag(argv, '--port')}")
    m = flag(argv, "-m") or ""
    if model_sub not in m:
        sys.exit(f"REFUSING: pid {pid} on :{port} serves {m!r}, expected {model_sub!r}")


def main() -> int:
    args = sys.argv[1:]
    state_path = DEFAULT_STATE
    if "--state" in args:
        state_path = Path(args[args.index("--state") + 1])
    apply = "--apply" in args
    reverse = "--reverse" in args
    gpu_role, cpu_role = ("architect_critic", "architect_general")
    if reverse:
        gpu_role, cpu_role = cpu_role, gpu_role
    old_gpu_role, old_cpu_role = cpu_role, gpu_role

    raw = state_path.read_text()
    st = json.loads(raw)
    s83, s74 = st.get("server_8083"), st.get("server_8074")
    if not (isinstance(s83, dict) and isinstance(s74, dict)):
        sys.exit("REFUSING: state lacks server_8083/server_8074 rows")
    prove(int(s83["pid"]), 8083, M27)
    prove(int(s74["pid"]), 8074, MFN)
    if s83.get("role") != old_gpu_role or s74.get("role") != old_cpu_role:
        sys.exit(f"REFUSING: state is not in the expected pre-state (server_8083.role={s83.get('role')}, "
                 f"server_8074.role={s74.get('role')}); already relabeled?")

    new = dict(st)
    gpu = dict(s83, role=gpu_role)
    cpu = dict(s74, role=cpu_role)
    new["server_8083"] = gpu
    new["server_8074"] = cpu
    new.pop(old_gpu_role, None)
    new.pop(old_cpu_role, None)
    new[gpu_role] = dict(gpu)
    new[cpu_role] = dict(cpu)
    for alias in ALIASES:
        # aliases ride the LIVE :8083 process; repoint any stale pid (e.g. dead 2009477)
        new[alias] = dict(gpu)

    for k in ("server_8083", "server_8074", gpu_role, cpu_role, *ALIASES):
        v = new[k]
        print(f"{k:22s} role={v['role']:18s} pid={v['pid']:<8} port={v['port']}")
    if not apply:
        print("dry run (pass --apply to write)")
        return 0
    if state_path.read_text() != raw:
        sys.exit("REFUSING: state file changed while planning; re-run")
    backup = state_path.with_name(f"{state_path.name}.pre-archswap-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}")
    shutil.copy2(state_path, backup)
    tmp = state_path.with_name(state_path.name + ".archswap.tmp")
    tmp.write_text(json.dumps(new, indent=2))
    os.replace(tmp, state_path)
    print(f"backup: {backup}\nwrote:  {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
