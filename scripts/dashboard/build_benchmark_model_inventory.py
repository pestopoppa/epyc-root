#!/usr/bin/env python3
"""Build the read-only model inventory consumed by the benchmark dashboard.

The dashboard hub deliberately uses only the Python standard library, while
the registry source of truth is YAML.  Keep YAML parsing in this explicit,
offline builder and emit a small JSON contract for the hub to read later.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml")
DEFAULT_ORCHESTRATOR = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml")
DEFAULT_OUTPUT = ROOT / "data" / "benchmark_model_inventory.json"


def _load_roles(path: Path) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    roles = data.get("roles", {}) if isinstance(data, dict) else {}
    return roles if isinstance(roles, dict) else {}


def build_inventory(research_path: Path, orchestrator_path: Path) -> dict[str, Any]:
    """Return model/quant records deduplicated across source registries."""
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for source, path in (("research_full", research_path), ("orchestrator_active", orchestrator_path)):
        for role, record in _load_roles(path).items():
            if not isinstance(record, dict) or not isinstance(record.get("model"), dict):
                continue
            model = record["model"]
            name = str(model.get("name") or "").strip()
            if not name:
                continue
            quant = str(model.get("quant") or "unknown")
            model_path = str(model.get("path") or model.get("huggingface_id") or "")
            key = (name, quant, model_path)
            entry = grouped.setdefault(
                key,
                {
                    "model": name,
                    "quant": quant,
                    "path": model_path or None,
                    "architecture": model.get("architecture"),
                    "size_gb": model.get("size_gb"),
                    "deprecated": bool(record.get("deprecated") or model.get("deprecated")),
                    "sources": defaultdict(list),
                },
            )
            entry["sources"][source].append(role)
    models = []
    for entry in grouped.values():
        entry["sources"] = {source: sorted(roles) for source, roles in sorted(entry["sources"].items())}
        models.append(entry)
    models.sort(key=lambda row: (row["deprecated"], row["model"].lower(), row["quant"], row["path"] or ""))
    return {
        "schema_version": "benchmark_model_inventory.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sources": {"research_full": str(research_path), "orchestrator_active": str(orchestrator_path)},
        "models": models,
        "counts": {"unique_model_quants": len(models), "research_roles": len(_load_roles(research_path)), "orchestrator_roles": len(_load_roles(orchestrator_path))},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-registry", type=Path, default=DEFAULT_RESEARCH)
    parser.add_argument("--orchestrator-registry", type=Path, default=DEFAULT_ORCHESTRATOR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_inventory(args.research_registry, args.orchestrator_registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
