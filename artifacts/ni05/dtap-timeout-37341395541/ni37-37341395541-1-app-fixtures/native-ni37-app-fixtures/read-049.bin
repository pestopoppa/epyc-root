"""Project prospective DFlash2 experimental-runtime rows into ``ClaimTuple``.

The measurement reader is owned by the research producer and is loaded only
when its exact reviewed bytes are present.  It independently reopens the
campaign closure and re-derives every producer-authored row before this thin
adapter constructs the shared carrier.  Pre-hook DF2-4 records deliberately
project zero rows; no tuple is reconstructed from historical output.
"""

from __future__ import annotations

import hashlib
import importlib.util
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402


ADAPTER_ID = "vidya.adapters.dflash2_experimental_runtime/v1"
PROJECTION_NAME = "dflash2_experimental_runtime"
SOURCE_SCHEMA = "epyc.df2.experimental_runtime_campaign.v1"
PRE_HOOK_SCHEMA = "epyc.df2.matched_np1_campaign.v1"
PRODUCER_COMMIT = "71b81a8e849a7b4f75160fceb9d720e1f91dc11b"
PRODUCER_SHA256 = "d1b197fb67182d2e0948c7e0435d680575df08e0d8c77c4287ef9ac159b7872c"
PRODUCER_ID = "scripts.benchmark.dflash2_beliefs/v1"
AUTHORITY = "experimental_runtime_no_kernel_champion_no_promotion"
DEFAULT_PRODUCER_PATH = (
    Path("/workspace/repos/epyc-inference-research") /
    "scripts/benchmark/dflash2_beliefs.py"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _producer(path: Path | None = None) -> ModuleType:
    source = Path(path or DEFAULT_PRODUCER_PATH)
    try:
        meta = source.lstat()
    except FileNotFoundError as exc:
        raise ProjectionError(f"reviewed DFlash2 producer is absent: {source}") from exc
    if (not stat.S_ISREG(meta.st_mode) or stat.S_ISLNK(meta.st_mode)
            or meta.st_nlink != 1):
        raise ProjectionError("reviewed DFlash2 producer must be a regular single-link file")
    observed = _sha256(source)
    if observed != PRODUCER_SHA256:
        raise ProjectionError(
            f"DFlash2 producer bytes drifted from {PRODUCER_COMMIT}: {observed}")
    name = f"_epyc_df2_beliefs_{observed}"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ProjectionError("reviewed DFlash2 producer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(f"reviewed DFlash2 producer cannot be loaded: {exc}") from exc
    return module


def native_rows(source: str | Path | Mapping[str, Any], *,
                producer_path: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Reopen a native campaign through the exact reviewed producer reader."""
    module = _producer(producer_path)
    try:
        rows = module.native_rows(source)
    except module.DFlash2BeliefRefusal as exc:
        raise ProjectionError(f"DFlash2 campaign refused: {exc}") from exc
    if not isinstance(rows, list):
        raise ProjectionError("DFlash2 native reader returned a non-list")
    return tuple(rows)


@register(PROJECTION_NAME)
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one exact producer-authored row; grading remains centralized."""
    module = _producer()
    try:
        values = module.project(native)
    except module.DFlash2BeliefRefusal as exc:
        raise ProjectionError(f"DFlash2 measurement refused: {exc}") from exc
    if not isinstance(values, dict):
        raise ProjectionError("DFlash2 projection did not return ClaimTuple fields")
    extra = values.get("extra")
    if not isinstance(extra, dict) or (
        extra.get("authority") != AUTHORITY
        or extra.get("experimental_runtime") is not True
        or extra.get("source_mutation_strategy") is not False
        or extra.get("kernel_champion_authority") is not False
        or extra.get("promotion_authority") is not False
        or extra.get("production_authority") is not False
    ):
        raise ProjectionError("DFlash2 experimental-runtime authority boundary drifted")
    if values.get("metric_direction") != "higher_better":
        raise ProjectionError("DFlash2 metric direction is not producer-authored higher_better")
    try:
        return ClaimTuple(**values)
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"DFlash2 ClaimTuple grammar mismatch: {exc}") from exc


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "PRE_HOOK_SCHEMA", "PRODUCER_COMMIT",
    "PRODUCER_SHA256", "SOURCE_SCHEMA", "native_rows", "project",
]
