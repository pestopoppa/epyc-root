#!/usr/bin/env python3
"""Isolated prototype for receipt-backed candidate-driver PRELOAD_MODELS."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from verify_receipt import EXPECTED_RECEIPT_SHA256, VerificationError, stat_identity, verify


def draft_shape(drafter: dict[str, Any]) -> dict[str, Any]:
    """Match the candidate's draft_cache_shape contract from verified receipt metadata."""
    metadata = drafter.get("metadata")
    if not isinstance(metadata, dict):
        raise VerificationError("drafter verified metadata missing")
    # verify() has already checked every field and exact bool pattern element.
    return {
        "draft_base_layers": 0,
        "draft_swa_layers": 5,
        "source": "receipt-verified dflash metadata; five layers, 2048 SWA all layers",
        "metadata": metadata,
    }


def unchanged_models(preload_models: dict[str, Any]) -> None:
    """Repeat the candidate's stat identity check without reading model bytes."""
    for role in ("target", "drafter"):
        item = preload_models[role]
        current = stat_identity(item["path"])
        if current != item["stat_identity"]:
            raise VerificationError(f"{role} model stat identity changed across preload/capture")


def load_preload_models(receipt_path: Path, manifest_path: Path) -> dict[str, Any]:
    """Build the existing PRELOAD_MODELS shape from a pinned identity receipt."""
    result = verify(receipt_path, manifest_path, EXPECTED_RECEIPT_SHA256)
    models = {model["role"]: {
        "path": model["path"], "sha256": model["sha256"],
        "tensor_count": model["tensor_count"], "metadata": model["metadata"],
        "stat_identity": model["stat_identity"],
    } for model in result["models"]}
    models["draft_cache_shape"] = draft_shape(models["drafter"])
    # Second stat check at the integration boundary, after materializing entries.
    unchanged_models(models)
    return models
