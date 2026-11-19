"""Scratch verifier for precomputed identities; never opens model files."""
import hashlib
import json
import os
from pathlib import Path


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _stat_identity(path, stat_fn):
    s = stat_fn(path)
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def verify_precomputed(receipt_path, pinned_models_path, *, receipt_sha256,
                       pinned_models_sha256, stat_fn=os.stat):
    """Bind a small receipt to pinned model paths/hashes and current stat identity.

    Receipt/model-list bytes are small metadata. Model paths are only stat'ed;
    this function never reads or hashes model contents.
    """
    if _digest(receipt_path) != receipt_sha256:
        raise ValueError("precomputed model identity receipt digest mismatch")
    if _digest(pinned_models_path) != pinned_models_sha256:
        raise ValueError("pinned original-model list digest mismatch")
    receipt = json.loads(Path(receipt_path).read_text())
    pinned = json.loads(Path(pinned_models_path).read_text())
    if set(receipt) != {"target", "drafter"} or set(pinned) != {"target", "drafter"}:
        raise ValueError("model identity roles mismatch")
    for role in ("target", "drafter"):
        item, expected = receipt[role], pinned[role]
        if item.get("path") != expected.get("path") or item.get("sha256") != expected.get("sha256"):
            raise ValueError("precomputed model identity differs from pinned model list: " + role)
        if item.get("stat_identity") != _stat_identity(item["path"], stat_fn):
            raise ValueError("model stat identity drift: " + role)
    draft = receipt["drafter"].get("metadata", {})
    arch = draft.get("general.architecture")
    if (not isinstance(arch, str) or "dflash" not in arch.lower()
            or draft.get(arch + ".block_count") != 5
            or draft.get(arch + ".attention.sliding_window") != 2048
            or draft.get(arch + ".attention.sliding_window_pattern") != [True] * 5):
        raise ValueError("precomputed drafter cache shape is not the pinned five-layer 2048 recipe")
    receipt["draft_cache_shape"] = {
        "draft_base_layers": 0, "draft_swa_layers": 5,
        "source": "retained precomputed metadata receipt; no in-grant GGUF read",
    }
    return receipt
