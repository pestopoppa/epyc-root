#!/usr/bin/env python3
"""Resolve the hub's launch spec from the orchestrator launch manifest.

Used by hub_supervisor.sh. The launch manifest
(`epyc-orchestrator/orchestration/launch_manifest.yaml`, entry
`handoff_dashboard`) decides where and how the :8100 hub runs: cwd, pythonpath,
env and argv. Orchestrator commit f5476148 (2026-09-09) points it at a reviewed
lane checkout on purpose. The supervisor used to hard-code `cwd=EPYC_ROOT`, so
every supervisor relaunch silently overrode the manifest.

Resolution matches `orchestrator_stack.start_aux_service`:
  * `{llm_root}`-style tokens use `stack_manifest._expand_paths`.
  * The entry is validated by `stack_manifest._aux_service`.
  * `{python}` becomes `sys.executable`, as `_resolve_aux_launch` does. Run this
    helper under the interpreter the hub should use (HUB_PYTHON).
  * env comes from `stack_env.build_service_env` plus the pythonpath prepend,
    as `_build_aux_env` does.
If the orchestrator modules cannot be imported, a local resolver with the same
token semantics is used, and `HUB_M_RESOLVER=local` says so.

Output: shell assignments quoted with shlex.quote, meant for `eval`.
HUB_M_ENV holds only the variables that DIFFER from this process's environment.
Exit 2 means the manifest is unreadable or the service is missing.
"""

from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path

DEFAULT_MANIFEST = "/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml"


def _local_tokens(orch_root: Path) -> dict[str, str]:
    # Same env keys/defaults as scripts/server/stack_paths._get_paths.
    llm_root = Path(os.environ.get("ORCHESTRATOR_PATHS_LLM_ROOT", "/mnt/raid0/llm"))
    return {
        "{models_dir}": os.environ.get("ORCHESTRATOR_PATHS_MODELS_DIR", str(llm_root / "models")),
        "{model_base}": os.environ.get("ORCHESTRATOR_PATHS_MODEL_BASE", str(llm_root / "models")),
        "{project_root}": os.environ.get("ORCHESTRATOR_PATHS_PROJECT_ROOT", str(orch_root)),
        "{cache_dir}": os.environ.get("ORCHESTRATOR_PATHS_CACHE_DIR", str(llm_root / "cache")),
        "{llm_root}": str(llm_root),
        "{tmp_dir}": os.environ.get("ORCHESTRATOR_PATHS_TMP_DIR", str(llm_root / "tmp")),
    }


def _local_expand(value, tokens):
    if isinstance(value, str):
        for token, rep in tokens.items():
            value = value.replace(token, rep)
        return value
    if isinstance(value, list):
        return [_local_expand(v, tokens) for v in value]
    if isinstance(value, dict):
        return {k: _local_expand(v, tokens) for k, v in value.items()}
    return value


def resolve(manifest: Path, service_name: str, orch_root: Path, force_local: bool):
    import yaml  # PyYAML; absent -> caller reports the manifest unreadable

    document = yaml.safe_load(manifest.read_text())
    entries = (document or {}).get("aux_services") or []
    raw = next((e for e in entries if isinstance(e, dict) and e.get("name") == service_name), None)
    if raw is None:
        raise LookupError(f"aux_services has no entry named {service_name!r}")

    resolver = "local"
    if not force_local:
        try:
            sys.path.insert(0, str(orch_root))
            from scripts.server.stack_env import build_service_env  # type: ignore
            from scripts.server.stack_manifest import _aux_service, _expand_paths  # type: ignore

            service = _aux_service(_expand_paths(raw))
            argv = [t.replace("{python}", sys.executable) for t in service.argv]
            env = build_service_env(service, os.environ.copy())
            if service.pythonpath:
                existing = env.get("PYTHONPATH", "")
                env["PYTHONPATH"] = os.pathsep.join(service.pythonpath) + (
                    f"{os.pathsep}{existing}" if existing else ""
                )
            return {
                "resolver": "orchestrator",
                "port": service.port,
                "cwd": service.cwd,
                "argv": argv,
                "env": env,
                "health_path": service.health_path,
                "backend": service.backend or "",
            }
        except Exception as exc:  # noqa: BLE001 - any import/validation failure -> local
            resolver = f"local (orchestrator resolver unavailable: {type(exc).__name__}: {exc})"

    entry = _local_expand(raw, _local_tokens(orch_root))
    for required in ("name", "port", "argv", "cwd"):
        if required not in entry:
            raise ValueError(f"{service_name!r} lacks {required!r}")
    argv = [str(t).replace("{python}", sys.executable) for t in entry["argv"]]
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in (entry.get("env") or {}).items()})
    ld = [str(p) for p in (entry.get("ld_library_path") or []) if str(p)]
    if ld:
        mode = entry.get("ld_library_path_mode", "prepend")
        ambient = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(ld) + (f":{ambient}" if ambient and mode == "prepend" else "")
    pp = [str(p) for p in (entry.get("pythonpath") or [])]
    if pp:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(pp) + (f"{os.pathsep}{existing}" if existing else "")
    return {
        "resolver": resolver,
        "port": int(entry["port"]),
        "cwd": str(entry["cwd"]),
        "argv": argv,
        "env": env,
        "health_path": str(entry.get("health_path", "/health")),
        "backend": str(entry.get("backend") or ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default=os.environ.get("HUB_LAUNCH_MANIFEST", DEFAULT_MANIFEST))
    ap.add_argument("--service", default="handoff_dashboard")
    ap.add_argument("--orchestrator-root", default=os.environ.get("HUB_ORCHESTRATOR_ROOT"),
                    help="default: $HUB_ORCHESTRATOR_ROOT, else two levels above the manifest")
    ap.add_argument("--local", action="store_true",
                    help="skip the orchestrator import and use the local resolver")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    try:
        orch_root = (Path(args.orchestrator_root) if args.orchestrator_root
                     else manifest.resolve().parents[1])
        spec = resolve(manifest, args.service, orch_root,
                       args.local or os.environ.get("HUB_SPEC_RESOLVER") == "local")
    except Exception as exc:  # noqa: BLE001
        print(f"hub_launch_spec: cannot resolve {args.service!r} from {manifest}: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if spec["backend"]:
        # A backend service needs kernel-path resolution and a linkage check that
        # this helper does not carry. The hub never declares one.
        print(f"hub_launch_spec: {args.service!r} declares backend={spec['backend']!r}; "
              "unsupported here", file=sys.stderr)
        return 2

    q = shlex.quote
    delta = [f"{k}={v}" for k, v in sorted(spec["env"].items()) if os.environ.get(k) != v]
    print(f"HUB_M_RESOLVER={q(spec['resolver'])}")
    print(f"HUB_M_PORT={q(str(spec['port']))}")
    print(f"HUB_M_CWD={q(spec['cwd'])}")
    print(f"HUB_M_HEALTH_PATH={q(spec['health_path'])}")
    print("HUB_M_ARGV=(" + " ".join(q(a) for a in spec["argv"]) + ")")
    print("HUB_M_ENV=(" + " ".join(q(e) for e in delta) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
