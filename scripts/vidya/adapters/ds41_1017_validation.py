"""Read producer-authored DS41-1017 validation measurements (INF-77 DS41-W5/W6, VB-DS41-1017-WIRE).

Native capture: ``epyc-inference-research/scripts/benchmark/ds41_1017_capture.py`` writes one
self-hashed row per gate number into ``<run_dir>/belief_measurements.jsonl`` at the moment the
number exists, binding the 9 shard sha256s of the 1017 MXFP4-experts artifact (and the drafter
digest, or an explicit null with its reason). This adapter re-validates each row with the
producer's own validator, re-hashes the scored artifact, and projects; the shared measurement
ladder (`claim_tuple.grade`) alone assigns the grade. One invalid row voids its sidecar.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.ds41_1017_validation/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ds41-1017-validation"
RESEARCH_ROOT = Path("/workspace/repos/epyc-inference-research")
PRODUCER_REL = "scripts/benchmark/ds41_1017_capture.py"
PRODUCER_SHA256 = "0695c58efa8222027ae75cc9b2559c1adddda27a7345b3e7a2d673c6dda087f8"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _producer() -> ModuleType:
    path = RESEARCH_ROOT / PRODUCER_REL
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ProjectionError(f"DS41-1017 producer unavailable: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ProjectionError("DS41-1017 producer must be a regular file")
    if _sha256(path) != PRODUCER_SHA256:
        raise ProjectionError("DS41-1017 producer bytes differ from reviewed sha256")
    name = "_epyc_ds41_1017_capture_producer"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProjectionError("DS41-1017 producer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(f"DS41-1017 producer cannot be loaded: {exc}") from exc
    return module


def _check(row: Any, producer: ModuleType) -> None:
    problems = producer.validate_row(row)
    if problems:
        raise ProjectionError("DS41-1017 row refused: " + "; ".join(problems))
    if row.get("source_kind") != SOURCE_KIND:
        raise ProjectionError("DS41-1017 row source_kind drifted")


def _scored(row: dict, root: Path) -> Path:
    resolved = (root / row["scored_path"]).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ProjectionError("DS41-1017 scored artifact escapes the research repository")
    return resolved


def native_rows(sidecar_path: str | Path, *, root: Path | None = None) -> tuple[dict, ...]:
    root = root or RESEARCH_ROOT
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    producer = _producer()
    try:
        rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"DS41-1017 sidecar unreadable: {exc}") from exc
    seen: set[str] = set()
    for row in rows:
        _check(row, producer)
        if row["measurement_id"] in seen:
            raise ProjectionError("DS41-1017 sidecar duplicates a measurement")
        seen.add(row["measurement_id"])
    if len({r["run_id"] for r in rows}) > 1:
        raise ProjectionError("DS41-1017 sidecar mixes runs")
    return tuple({"row": r, "sidecar_path": str(path), "root": str(root)} for r in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("DS41-1017 native capture row missing")
    root = Path(native.get("root") or RESEARCH_ROOT)
    row = native["row"]
    _check(row, _producer())
    artifact = _scored(row, root)
    present = artifact.is_file()
    verified = present and _sha256(artifact) == row["scored_sha256"]
    scope = {"model_file": row["artifact"]["path"],
             "quant": "MXFP4-experts" if row["arm"] == "1017" else "Q4_K-experts",
             "backend": "cpu", "run_id": row["run_id"],
             "kernel": {"head": row["binary"]["head"], "binary_sha256": row["binary"]["binary_sha256"]}}
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=row["claim"],
        metric_direction=row["metric_direction"], protocol_id=row.get("protocol_id") or "",
        reps=row.get("reps"), reps_basis=row.get("reps_basis") or "", unit=row["unit"],
        attestation_sha256=row["scored_sha256"],
        attestation_locator=f"{row['run_id']}:{row['gate']}:{row['arm']}|{row['scored_path']}"
                            f"#sha256={row['scored_sha256']}",
        attestation_present=present, attestation_verified=True if verified else None,
        source_kind=SOURCE_KIND, applicability=scope,
        extra={"schema": row["schema"], "producer": row["producer"], "emitted_at": row["emitted_at"],
               "row_sha256": row["row_sha256"], "sidecar_path": native.get("sidecar_path", ""),
               "gate": row["gate"], "arm": row["arm"],
               "shard_sha256": [x["sha256"] for x in row["artifact"].get("shards", [])],
               "drafter": row["drafter"], "binary": row["binary"],
               "recipe": row["recipe"], "region": row["region"], **(row.get("extra") or {})},
    )
