"""The store-manifest scope of one AutoKernel loop store (loop-belief redesign §3.1, §4.1).

Some AutoKernel records name no model of their own: a refusal row in `experiments.db` carries no
`research_scope`, and a serving floor (`serving-floor.*.json`) names its recipe but not the GGUF
it launched. Their scope is the STORE's: one loop store serves one target, and the loop pins that
target in `<store>/loop-status.json` (`target.original_target.execution` -- backend, model path
and model sha256 -- and `target.selected_id`, the recipe the loop serves). This is the same
"the producer contract pins the whole scope" basis `loop_beliefs.SOURCE_SCOPES` already accepts.

Two rules keep it honest:

  * the manifest scopes a record only when the record's own recipe equals the manifest's
    `recipe` (a store's loop can move between recipes; a floor calibrated under another recipe
    is not claimed for this one) -- callers check that, this module only reads;
  * every scope key it returns came from the status file verbatim, and the tuple says so with
    `applicability.scope_basis = "store_manifest"`.

Read-only; never walks the store; returns {} for anything it cannot read exactly.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

SCHEMA = "epyc.vidya.ak_store_manifest.v1"
STATUS_NAME = "loop-status.json"
STATUS_SCHEMA = "epyc.autokernel.loop_status.v1"
_MAX_BYTES = 4 << 20
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_BACKENDS = frozenset({"cpu", "gpu"})


def _bounded_read(path: Path) -> bytes | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= _MAX_BYTES:
            return None
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(_MAX_BYTES + 1)
    finally:
        os.close(fd)
    return raw if len(raw) <= _MAX_BYTES else None


def load(store_dir: str | Path) -> dict:
    """{schema, store, locator, sha256, campaign_id, recipe, scope} or {} when unreadable.

    `scope` holds applicability keys only (`model_file`, `model_sha256`, `backend`, `recipe`,
    `scope_basis`). A status file that names no model scopes nothing.
    """
    path = Path(store_dir) / STATUS_NAME
    raw = _bounded_read(path)
    if raw is None:
        return {}
    try:
        doc = json.loads(raw)
    except (ValueError, RecursionError):
        return {}
    if not isinstance(doc, dict) or doc.get("schema") != STATUS_SCHEMA:
        return {}
    target = doc.get("target")
    if not isinstance(target, dict):
        return {}
    original = target.get("original_target")
    execution = original.get("execution") if isinstance(original, dict) else None
    if not isinstance(execution, dict):
        return {}
    model = execution.get("model")
    model_path = model.get("path") if isinstance(model, dict) else None
    if not isinstance(model_path, str) or not model_path.strip():
        return {}
    scope: dict = {"model_file": model_path}
    sha = model.get("sha256")
    if isinstance(sha, str) and _HEX64.match(sha):
        scope["model_sha256"] = sha
    backend = execution.get("backend")
    if isinstance(backend, str) and backend.strip().lower() in _BACKENDS:
        scope["backend"] = backend.strip().lower()
    recipe = target.get("selected_id")
    if not isinstance(recipe, str) or not recipe.strip():
        recipe = None
    else:
        scope["recipe"] = recipe
    scope["scope_basis"] = "store_manifest"
    campaign = target.get("campaign_id")
    return {"schema": SCHEMA, "store": str(store_dir), "locator": str(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "campaign_id": campaign if isinstance(campaign, str) else None,
            "recipe": recipe, "scope": scope}


__all__ = ["SCHEMA", "STATUS_NAME", "load"]
