"""AutoKernel serving floors as BASELINE observations (loop-belief redesign §3.3, §5.1, P1-D).

A floor file (`<store>/serving-floor.<recipe>.requests-<digest>.json`, schema
`epyc.autokernel.serving_floor.v1`, written by the research loop's `serving.write_floor`) is the
A/A calibration of one serving recipe: the median aggregate rate over `n` independent server
launches and the p95 run-to-run deviation every later keep is judged against. It is the answer to
"what does this target actually serve, and how noisy is that?" -- and until this adapter no belief
carried it.

PROJECTION ONLY. One floor file -> one `BASELINE` tuple: value = `median_tok_s`, reps = `n`, the
floor as `observation.noise_floor_rel`, `observation.outcome = "floor"`. `claim_tuple.grade()`
decides; a floor cites no protocol, so it grades `Judged/Located` -- an observation, never
decision-gating, which is what it is.

Strict where the record lets it be: when the launches that defined the floor are in the row, the
median must re-derive from them, `n` must count them and `spread.p95_dev_pct` must equal
`floor_pct`; a floor that does not re-derive is refused, never repaired.

Retrofit (DP-1 (a)): the floor writer has no belief hook, so every floor projected today is a
retrofit and says so (`observation.retrofit`, and `provenance.retrofit` on its source frame).

Scope: the floor names its recipe and its residency backend, never the GGUF. The model comes
from the store manifest (`_ak_store_manifest`), and only when the manifest's recipe IS this
floor's recipe; then `applicability.scope_basis = "store_manifest"`. A manifest that disagrees
with the floor's own backend scopes nothing.

`epyc.autokernel.serving_floor.v2` (matched-process floors) states no median and is read by the
DS41-1017 validation path (design D6, Phase 2); this adapter projects nothing for it.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_serving_floor/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-serving-floor"
FLOOR_SCHEMA = "epyc.autokernel.serving_floor.v1"
FLOOR_GLOB = "serving-floor.*.json"
MEASUREMENT_PREFIX = "ak-floor:v1:"
LOCATOR_PREFIX = "autokernel-floor:"
_MAX_BYTES = 16 << 20
_UNITS = frozenset({"process", "arm", "session"})
_BACKENDS = frozenset({"cpu", "gpu"})


def read_floor(path: str | Path) -> tuple[Any, str]:
    """(document, sha256 of the exact bytes read). Bounded, no symlinks, stable during read."""
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= _MAX_BYTES:
            raise ProjectionError("serving floor is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(_MAX_BYTES + 1)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns) or len(raw) != before.st_size:
            raise ProjectionError("serving floor changed during read")
    finally:
        os.close(fd)
    try:
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"serving floor is not JSON: {exc}") from exc


def native_rows(document: Any, *, locator: str, sha256: str,
                store_manifest: dict | None = None) -> list[dict]:
    """One native row for a v1 floor; [] for any other document (nothing to project)."""
    if not isinstance(document, dict) or document.get("schema") != FLOOR_SCHEMA:
        return []
    if not isinstance(locator, str) or not locator.startswith(LOCATOR_PREFIX):
        raise ProjectionError("serving floor needs its original file locator")
    if not isinstance(sha256, str) or len(sha256) != 64:
        raise ProjectionError("serving floor needs the sha256 of the bytes it was read from")
    return [{"floor": document, "locator": locator, "sha256": sha256,
             "store_manifest": dict(store_manifest or {})}]


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _checked(doc: dict) -> dict:
    """The fields the tuple is built from, after the floor re-derives from its own launches."""
    metric, recipe = doc.get("metric"), doc.get("recipe")
    if not isinstance(metric, str) or not metric.strip():
        raise ProjectionError("serving floor names no metric")
    if not isinstance(recipe, str) or not recipe.strip():
        raise ProjectionError("serving floor names no recipe")
    value, floor = doc.get("median_tok_s"), doc.get("floor_pct")
    if not _finite(value) or value <= 0:
        raise ProjectionError("serving floor median is not a positive finite number")
    if not _finite(floor) or floor < 0:
        raise ProjectionError("serving floor_pct is not a non-negative finite number")
    n = doc.get("n")
    if type(n) is not int or n < 1:
        n = doc.get("samples")
    if type(n) is not int or n < 1:
        raise ProjectionError("serving floor states no sample count (R23-61)")
    runs = doc.get("runs")
    if runs is not None:
        if (not isinstance(runs, list) or len(runs) != n
                or any(not _finite(v) or v <= 0 for v in runs)):
            raise ProjectionError("serving floor launches do not match its stated n")
        if median(runs) != value:
            raise ProjectionError("serving floor median does not re-derive from its launches")
    spread = doc.get("spread")
    if isinstance(spread, dict) and "p95_dev_pct" in spread and spread["p95_dev_pct"] != floor:
        raise ProjectionError("serving floor_pct differs from its own spread.p95_dev_pct")
    unit = doc.get("unit")
    if unit is not None and unit not in _UNITS:
        raise ProjectionError(f"serving floor unit {unit!r} is not a recorded floor unit")
    residency = doc.get("residency") if isinstance(doc.get("residency"), dict) else {}
    ci = doc.get("floor_ci") if isinstance(doc.get("floor_ci"), dict) else {}
    return {"metric": metric, "recipe": recipe, "value": value, "floor": floor, "n": n,
            "unit": unit, "residency": residency, "ci": ci, "np": doc.get("np"),
            "recipe_hash": doc.get("recipe_hash"), "request_digest": doc.get("request_digest")}


def _date(residency: dict) -> str:
    end = residency.get("window_end")
    if not _finite(end):
        return ""
    return datetime.fromtimestamp(end, timezone.utc).isoformat()


def _scope(fields: dict, manifest: dict) -> dict:
    scope: dict = {"recipe": fields["recipe"]}
    if type(fields["np"]) is int and fields["np"] > 0:
        scope["np"] = fields["np"]
    backend = fields["residency"].get("backend")
    if isinstance(backend, str) and backend in _BACKENDS:
        scope["backend"] = backend
    pinned = manifest.get("scope") if isinstance(manifest.get("scope"), dict) else {}
    if manifest.get("recipe") == fields["recipe"] and pinned.get("model_file"):
        # The manifest may only ADD what the floor does not state; a disagreement on what the
        # floor does state means the manifest is about another target, and scopes nothing.
        if "backend" in scope and pinned.get("backend") not in (None, scope["backend"]):
            return dict(scope, scope_basis="native")
        for key in ("model_file", "model_sha256", "backend"):
            if key in pinned and key not in scope:
                scope[key] = pinned[key]
        scope["scope_basis"] = "store_manifest"
        return scope
    scope["scope_basis"] = "native"
    return scope


def _claim(fields: dict) -> str:
    residency = fields["residency"]
    status = residency.get("status") or residency.get("gpu_residency") or "unstated"
    backend = residency.get("backend") or "backend?"
    ci = fields["ci"]
    ci_text = (f", 95% CI {ci['low_pct']}-{ci['high_pct']}%"
               if _finite(ci.get("low_pct")) and _finite(ci.get("high_pct")) else "")
    unit = fields["unit"] or "unit-unstated"
    return (f"serving floor [{fields['recipe']}] {backend}: median {fields['value']:.2f} t/s "
            f"({fields['metric']}) over n={fields['n']} {unit} launches; A/A noise floor "
            f"{fields['floor']}%{ci_text}; residency {status} -- calibration observation, "
            "protocol unqualified")


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    rows = native_rows(native.get("floor"), locator=native.get("locator"),
                       sha256=native.get("sha256"), store_manifest=native.get("store_manifest"))
    if native not in rows:
        raise ProjectionError("serving floor projected row differs")
    try:
        fields = _checked(native["floor"])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f"serving floor refused: {exc}") from exc
    metric = fields["metric"]
    return ClaimTuple(
        measurement_id=f"{MEASUREMENT_PREFIX}{fields['recipe']}:{native['sha256'][:16]}",
        metric=metric, value=fields["value"],
        unit="t/s" if metric.endswith("tok_s") else "",
        date=_date(fields["residency"]), category="BASELINE", claim=_claim(fields),
        metric_direction="higher_better", protocol_id="", reps=fields["n"],
        reps_basis=f"scored:{fields['unit'] or 'unstated-unit'} launches of one build (A/A)",
        attestation_locator=native["locator"], attestation_sha256=native["sha256"],
        attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND,
        extra={"recipe_hash": fields["recipe_hash"], "request_digest": fields["request_digest"],
               "floor_ci": fields["ci"] or None, "residency_status": fields["residency"].get("status"),
               "store_manifest": {k: native["store_manifest"].get(k)
                                  for k in ("locator", "sha256")} or None},
        applicability=_scope(fields, native["store_manifest"]),
        observation={"outcome": "floor", "noise_floor_rel": fields["floor"] / 100.0,
                     "retrofit": True})


def floor_paths(store_dir: str | Path) -> list[Path]:
    """The floor files of ONE store directory (one glob, never a walk)."""
    return sorted(p for p in Path(store_dir).glob(FLOOR_GLOB)
                  if p.is_file() and not p.is_symlink())


__all__ = ["ADAPTER_ID", "AUTHORITY", "FLOOR_GLOB", "FLOOR_SCHEMA", "MEASUREMENT_PREFIX",
           "SOURCE_KIND", "floor_paths", "native_rows", "project", "read_floor"]
