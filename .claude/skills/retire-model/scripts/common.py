"""Shared loaders for the retire-model / change-role assertion scripts.

Every path here is a SOURCE of truth per `stack-change/DERIVATION.md`. Nothing in
this module reads a derived artifact, because a derived artifact tells you what
the last compile believed, not what the sources say.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

RESEARCH = Path(os.environ.get("EPYC_RESEARCH", "/mnt/raid0/llm/epyc-inference-research"))
ORCH = Path(os.environ.get("EPYC_ORCHESTRATOR", "/mnt/raid0/llm/epyc-orchestrator"))

MASTER_REGISTRY = RESEARCH / "orchestration" / "model_registry.yaml"
TOPOLOGY = ORCH / "orchestration" / "stack_topology.yaml"
LAUNCH_MANIFEST = ORCH / "orchestration" / "launch_manifest.yaml"
PROCEDURES = ORCH / "orchestration" / "procedures"
STACK_TEMPLATES = ORCH / "stack_templates"
SERVING_RECIPES = RESEARCH / "artifacts" / "serving-recipes"
AUTOKERNEL = RESEARCH / "scripts" / "kernel_rnd" / "autokernel"
MODELS_PY = ORCH / "src" / "config" / "models.py"
ROLES_PY = ORCH / "src" / "roles.py"


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        die(f"source file is missing: {path}")
    with path.open() as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        die(f"not a YAML mapping: {path}")
    return data


def load_sources(scratch: str | None = None) -> dict[str, Any]:
    """Load every hand-edited source. `scratch` re-roots both repos.

    stack-change phases 2-5 run against a scratch copy; pass --scratch so these
    assertions read the SAME bytes the operator will sign, not the live tree.
    """
    global RESEARCH, ORCH, MASTER_REGISTRY, TOPOLOGY, LAUNCH_MANIFEST
    global PROCEDURES, STACK_TEMPLATES, SERVING_RECIPES, AUTOKERNEL, MODELS_PY, ROLES_PY
    if scratch:
        root = Path(scratch)
        RESEARCH = root / "epyc-inference-research"
        ORCH = root / "epyc-orchestrator"
        MASTER_REGISTRY = RESEARCH / "orchestration" / "model_registry.yaml"
        TOPOLOGY = ORCH / "orchestration" / "stack_topology.yaml"
        LAUNCH_MANIFEST = ORCH / "orchestration" / "launch_manifest.yaml"
        PROCEDURES = ORCH / "orchestration" / "procedures"
        STACK_TEMPLATES = ORCH / "stack_templates"
        SERVING_RECIPES = RESEARCH / "artifacts" / "serving-recipes"
        AUTOKERNEL = RESEARCH / "scripts" / "kernel_rnd" / "autokernel"
        MODELS_PY = ORCH / "src" / "config" / "models.py"
        ROLES_PY = ORCH / "src" / "roles.py"
    master = load_yaml(MASTER_REGISTRY)
    return {
        "master": master,
        "roles": master.get("roles") or {},
        "server_mode": master.get("server_mode") or {},
        "deprecated_models": master.get("deprecated_models") or [],
        "topology": load_yaml(TOPOLOGY),
        "manifest": load_yaml(LAUNCH_MANIFEST),
    }


def artifacts_of(row: Any) -> set[str]:
    """Every GGUF path/basename a registry row names."""
    out: set[str] = set()

    def add(v: Any) -> None:
        if isinstance(v, str) and v.strip():
            out.add(v.strip())
            out.add(os.path.basename(v.strip()))

    if isinstance(row, dict):
        model = row.get("model")
        if isinstance(model, dict):
            add(model.get("path"))
            add(model.get("mmproj_path"))
            add(model.get("name"))
        else:
            add(model)
        for key in ("model_path", "mmproj_path", "draft_model", "path"):
            add(row.get(key))
    return {a for a in out if a}


def is_deprecated(row: Any) -> bool:
    return isinstance(row, dict) and bool(row.get("deprecated"))


def live_roles(sources: dict[str, Any]) -> set[str]:
    """Role names that a launch can actually reach.

    A role is LIVE if it has a non-deprecated `server_mode` row, rides one via
    `shared_with`, or the launcher still names it (`port_map`, `hot_roles`,
    `role_launch_meta`). Anything narrower misses a role the launcher would
    still start -- which is how `stack_templates/default.yaml` nearly relaunched
    three retired models on 2026-09-22.
    """
    out: set[str] = set()
    for name, cfg in (sources["server_mode"] or {}).items():
        if not isinstance(cfg, dict) or is_deprecated(cfg):
            continue
        out.add(str(name))
        for alias in cfg.get("shared_with") or []:
            out.add(str(alias))
    manifest = sources["manifest"]
    for key in ("port_map", "role_launch_meta"):
        section = manifest.get(key) or {}
        if isinstance(section, dict):
            out.update(str(k) for k in section)
    for role in manifest.get("hot_roles") or []:
        out.add(str(role))
    return out


def server_for_role(sources: dict[str, Any], role: str) -> tuple[str | None, dict | None, str]:
    """Mirror of `src/registry/stack_priors.py::_server_for_role` resolution order.

    Direct row -> `model_role` back-reference -> `shared_with` membership.
    Kept in this order deliberately: a different order answers a different
    question than the compiler does, and a check that disagrees with the
    compiler is worse than no check.
    """
    sm = sources["server_mode"]
    direct = sm.get(role)
    if isinstance(direct, dict):
        return role, direct, "server_mode.direct"
    for name, cfg in sm.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("model_role") == role:
            return str(name), cfg, "server_mode.model_role"
        shared = cfg.get("shared_with")
        if isinstance(shared, list) and role in shared:
            return str(name), cfg, "server_mode.shared_with"
    return None, None, "unresolved"


def scan_files(roots: list[Path], pattern, exts: set[str], max_bytes: int = 4_000_000):
    """Yield (path, lineno, line, matched-text) for each textual hit.

    `pattern` is a compiled regex, not a substring set. A substring set is how
    the role name `worker` matched `controller-worker:` in this script's own
    first run -- the same class of defect as classifying a backend by
    `"build-hip" in path`.
    """
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file() or path in seen:
                continue
            if path.suffix not in exts and path.is_file() and root.is_dir():
                continue
            if "__pycache__" in path.parts:
                continue
            try:
                if path.stat().st_size > max_bytes:
                    continue
                text = path.read_text(errors="replace")
            except OSError:
                continue
            seen.add(path)
            for i, line in enumerate(text.splitlines(), 1):
                m = pattern.search(line)
                if m:
                    yield path, i, line.strip()[:160], m.group(0)
