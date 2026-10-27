"""Per-role runtime-requirements lookup from the model registry.

Reads `server_mode.<entry>.runtime_requirements` to discover whether a role
needs a non-default binary directory and/or extra LD_LIBRARY_PATH entries. Returns
(None, None) when no entry has runtime_requirements or the role is absent —
the launcher falls back to the default LLAMA_SERVER + canonical env stack
in that case.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.registry_loader import RegistryLoader


def runtime_requirements_for_role(
    registry: "RegistryLoader | None", role_name: str
) -> tuple[str | None, list[str] | None]:
    """Return (binary_dir, ld_library_paths) for `role_name` from server_mode entries.

    Walks `registry._raw["server_mode"]` for the entry whose `model_role`
    matches `role_name`. Launch branches use this for role-specific binary
    and dynamic-library overrides while defaulting to the canonical binary.
    """
    if not registry or not hasattr(registry, "_raw"):
        return None, None
    sm = registry._raw.get("server_mode", {}) or {}
    for entry in sm.values():
        if not isinstance(entry, dict):
            continue
        if entry.get("model_role") != role_name:
            continue
        rt = entry.get("runtime_requirements") or {}
        return rt.get("binary_dir"), rt.get("ld_library_path")
    return None, None
