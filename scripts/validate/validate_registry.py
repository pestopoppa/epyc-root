#!/usr/bin/env python3
"""Validate the per-model agent_file_compression_operating_point field in
both model registries.

Per handoffs/active/agent-file-prose-compression.md Phase 4 + the
/new-model Step 6.5 deployment gate:

- runtime_defaults.agent_file_compression_operating_point must be present
  and one of: none | mild | medium | aggressive.
- Per-role overrides (roles.<role>.agent_file_compression_operating_point)
  must use the same enum if present.

Exit 0 on pass, 1 on failure.

Usage:
  python3 scripts/validate/validate_registry.py [path-to-registry.yaml]
  # default: walks both known registries (orchestrator lean + research full).
"""

from __future__ import annotations

import sys
from pathlib import Path

# yaml is a runtime dep; the registry is read elsewhere in the codebase already.
import yaml


_VALID_OPERATING_POINTS = {"none", "mild", "medium", "aggressive"}
_FIELD = "agent_file_compression_operating_point"


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REGISTRIES = [
    _REPO_ROOT / "repos" / "epyc-orchestrator" / "orchestration" / "model_registry.yaml",
    _REPO_ROOT / "repos" / "epyc-inference-research" / "orchestration" / "model_registry.yaml",
]


def validate_registry(path: Path) -> list[str]:
    """Return a list of error strings; empty list = OK."""
    errors: list[str] = []

    if not path.exists():
        return [f"{path}: does not exist"]

    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"{path}: YAML parse error: {e}"]

    if not isinstance(data, dict):
        return [f"{path}: top-level is not a mapping"]

    # 1. runtime_defaults must declare the field.
    rd = data.get("runtime_defaults") or {}
    if _FIELD not in rd:
        errors.append(
            f"{path}: missing runtime_defaults.{_FIELD} "
            f"(expected one of {sorted(_VALID_OPERATING_POINTS)})"
        )
    else:
        v = rd[_FIELD]
        if v not in _VALID_OPERATING_POINTS:
            errors.append(
                f"{path}: runtime_defaults.{_FIELD}={v!r} not in {sorted(_VALID_OPERATING_POINTS)}"
            )

    # 2. Per-role overrides (when present) must use the same enum.
    roles = data.get("roles") or {}
    if isinstance(roles, dict):
        for role_name, role_cfg in roles.items():
            if not isinstance(role_cfg, dict):
                continue
            if _FIELD in role_cfg:
                v = role_cfg[_FIELD]
                if v not in _VALID_OPERATING_POINTS:
                    errors.append(
                        f"{path}: roles.{role_name}.{_FIELD}={v!r} "
                        f"not in {sorted(_VALID_OPERATING_POINTS)}"
                    )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        targets = [Path(p) for p in argv[1:]]
    else:
        targets = _DEFAULT_REGISTRIES

    all_errors: list[str] = []
    for path in targets:
        errs = validate_registry(path)
        if errs:
            all_errors.extend(errs)
        else:
            print(f"OK: {path}")

    if all_errors:
        print()
        print("registry validation failed:")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
