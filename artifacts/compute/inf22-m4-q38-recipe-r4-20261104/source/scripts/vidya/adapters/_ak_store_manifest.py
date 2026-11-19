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

TWO STRATEGIES, ONE OWNER (belief redesign P1-C/P1-D, unified 2026-10-21). A store's scope comes,
in this order, from

  1. `load(store)`          the loop's own status file (above): campaign-pinned, preferred;
  2. `load_from_rows(store)` the ONE native `research_scope` shared by every measured row of the
                            store's `experiments.db` (a bounded read of a few payloads): used only
                            when the status file pins nothing. Rows that disagree, or carry none,
                            give no scope -- unscoped is honest, a guessed scope is not.

`resolve(store)` runs them in that order and stamps which one answered (`strategy`). Both the
experiments adapter and the serving-floor adapter take their manifest from here; neither parses a
status file or a `research_scope` of its own. `row_scope(research_scope)` is the one place a
`research_scope` becomes applicability keys (the experiments adapter uses it per row too).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from pathlib import Path
from typing import Any, Mapping

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


_SERVING_SURFACE = re.compile(r"^serving:(?P<recipe>\S+)$")
_ROW_SCOPE_STATUSES = ("kept", "keep_candidate", "measured_null", "regression")
_ROW_SCOPE_LIMIT = 8


def row_scope(research_scope: Any) -> dict:
    """applicability keys of one row's native `research_scope`; {} when it names no model.

    `scope_basis` is NOT set here: the caller says `native` (this row's own) or `store_manifest`.
    """
    if not isinstance(research_scope, Mapping):
        return {}
    model = research_scope.get("model")
    path = model.get("path") if isinstance(model, Mapping) else model
    if not isinstance(path, str) or not path.strip():
        return {}
    out = {"model_file": path.strip()}
    sha = model.get("sha256") if isinstance(model, Mapping) else None
    if isinstance(sha, str) and _HEX64.match(sha.lower()):
        out["model_sha256"] = sha.lower()
    for key in ("quant", "backend"):
        value = research_scope.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()
    surface = research_scope.get("measurement_surface")
    match = _SERVING_SURFACE.match(surface.strip()) if isinstance(surface, str) else None
    if match:
        out["recipe"] = match.group("recipe")
    return out


def load_from_rows(store_dir: str | Path) -> dict:
    """Strategy 2: the uniform native scope of the store's measured rows, or {}.

    Reads at most `_ROW_SCOPE_LIMIT` payloads (`LIKE` over `payload`: on the 4.3 GB DS41 store
    that may walk many rows first, so callers cache the result per store).
    """
    path = Path(store_dir) / "experiments.db"
    if not path.is_file():
        return {}
    scopes: dict[str, dict] = {}
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=30)
    except sqlite3.Error:
        return {}
    try:
        conn.execute("PRAGMA query_only = ON")
        marks = ",".join("?" for _ in _ROW_SCOPE_STATUSES)
        cursor = conn.execute(
            f"SELECT payload FROM experiments WHERE status IN ({marks}) "
            "AND payload LIKE '%\"research_scope\"%' ORDER BY rowid LIMIT ?",
            (*_ROW_SCOPE_STATUSES, _ROW_SCOPE_LIMIT))
        for (raw,) in cursor:
            try:
                payload = json.loads(raw)
            except (ValueError, RecursionError):
                continue
            scope = row_scope(payload.get("research_scope")) if isinstance(payload, dict) else {}
            if scope:
                scopes[json.dumps(scope, sort_keys=True)] = scope
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    if len(scopes) != 1:
        return {}
    scope = dict(next(iter(scopes.values())))
    scope["scope_basis"] = "store_manifest"
    return {"schema": SCHEMA, "store": str(store_dir), "locator": str(path), "sha256": None,
            "campaign_id": None, "recipe": scope.get("recipe"), "scope": scope}


def resolve(store_dir: str | Path) -> dict:
    """Strategy 1, else strategy 2, else {}; stamped with `strategy` and the RESOLVED store path.

    The resolved path is what the experiments adapter digests into its measurement ids, so two
    spellings of one store never mint two ids.
    """
    for strategy, loader in (("loop_status", load), ("row_scope", load_from_rows)):
        manifest = loader(store_dir)
        if manifest:
            return {**manifest, "store": str(Path(store_dir).resolve()), "strategy": strategy}
    return {"schema": SCHEMA, "store": str(Path(store_dir).resolve()), "locator": None,
            "sha256": None, "campaign_id": None, "recipe": None, "scope": {},
            "strategy": "none"}


__all__ = ["SCHEMA", "STATUS_NAME", "load", "load_from_rows", "resolve", "row_scope"]
