"""Read producer-authored v10 MI210 KV-quant sweep measurements.

One invalid row voids its entire sidecar. The adapter projects the native capture;
the shared measurement ladder alone assigns its grade.
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

ADAPTER_ID = "vidya.adapters.kv_quant_27b_v10/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "kv-quant-27b-v10-measurement"
RESEARCH_ROOT = Path("/workspace/repos/epyc-inference-research")
PRODUCER_PATH = RESEARCH_ROOT / "scripts/benchmark/kv_quant_27b_v10_sweep.py"
PRODUCER_SHA256 = "b268e3067fb576f05915310b0df1b29ca0507442c87d6e3fb0a2be209c390cb5"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _producer() -> ModuleType:
    try:
        metadata = PRODUCER_PATH.lstat()
    except OSError as exc:
        raise ProjectionError(f"KV-quant producer unavailable: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_nlink != 1:
        raise ProjectionError("KV-quant producer must be a regular single-link file")
    if _sha256(PRODUCER_PATH) != PRODUCER_SHA256:
        raise ProjectionError("KV-quant producer bytes differ from reviewed sha256")
    name = "_epyc_kv_quant_27b_v10_producer"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PRODUCER_PATH)
    if spec is None or spec.loader is None:
        raise ProjectionError("KV-quant producer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(f"KV-quant producer cannot be loaded: {exc}") from exc
    return module


def _check_row(row: Any, producer: ModuleType) -> None:
    try:
        problems = producer.validate_row(row)
    except Exception as exc:
        raise ProjectionError(f"KV-quant row validator failed: {exc}") from exc
    if problems:
        raise ProjectionError("KV-quant row refused: " + "; ".join(problems))
    extra = row["extra"]
    arm = extra.get("arm")
    if not isinstance(arm, dict):
        raise ProjectionError("KV-quant arm evidence missing")
    if extra.get("source_kind") != SOURCE_KIND or extra.get("instrument_class") != "bench" \
            or extra.get("duty_cycle") != "bursty":
        raise ProjectionError("KV-quant source or bench-surface cautions missing")
    if arm.get("cache_k") != arm.get("cache_v") or arm.get("flash_attention") != "on" \
            or arm.get("flash_attention_policy") != producer.FA_FIXED_REASON \
            or arm.get("mixed_kv_policy") != producer.MIXED_KV_REFUSAL:
        raise ProjectionError("KV-quant fixed FA or homogeneous K/V policy drifted")
    if arm.get("prefill_depth_target_tokens") not in {2048, 32768} \
            or not isinstance(arm.get("prefill_tokens_measured"), (int, float)):
        raise ProjectionError("KV-quant prefill depth evidence missing")
    if not all(isinstance(extra.get(k), (int, float)) for k in
               ("kv_buffer_k_mib", "kv_buffer_v_mib")):
        raise ProjectionError("KV-quant separate K and V buffer figures missing")
    locator = extra.get("locator")
    if not isinstance(locator, str) or locator != (
        f"kvq:{row['run_id']}:"
        f"{next((c.name for c in producer.CELLS if c.cache_k == arm['cache_k']), '')}:"
        f"{next((d.name for d in producer.DEPTHS if d.target_prefill_tokens == arm['prefill_depth_target_tokens']), '')}:"
        f"{row['metric']}"):
        raise ProjectionError("KV-quant locator does not bind run, arm, depth and metric")
    if row["measurement_id"] != producer.measurement_identity(
            run_id=row["run_id"], cell=locator.split(":")[2],
            depth=locator.split(":")[3], metric=row["metric"],
            scored_sha256=row["scored_sha256"]):
        raise ProjectionError("KV-quant measurement identity does not rederive")
    if row["category"] != ("BASELINE" if arm["cache_k"] == "f16" else "CANDIDATE"):
        raise ProjectionError("KV-quant reference-arm category drifted")
    if row["protocol_id"] not in ("", "P-GPU-1"):
        raise ProjectionError("KV-quant protocol route is unknown")
    kernel = extra.get("kernel")
    if not isinstance(kernel, dict):
        raise ProjectionError("KV-quant kernel provenance missing")
    if row["protocol_id"] == "P-GPU-1" and not kernel.get("production_named"):
        raise ProjectionError("KV-quant P-GPU-1 route lacks production kernel evidence")


def _scored_path(row: dict) -> Path:
    supplied = Path(row["scored_path"])
    candidate = supplied if supplied.is_absolute() else RESEARCH_ROOT / supplied
    resolved = candidate.resolve()
    if not resolved.is_relative_to(RESEARCH_ROOT.resolve()):
        raise ProjectionError("KV-quant scored artifact escapes research repository")
    return resolved


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    producer = _producer()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"KV-quant sidecar unreadable: {exc}") from exc
    if not rows:
        return ()
    identities: set[str] = set()
    locators: set[str] = set()
    for row in rows:
        _check_row(row, producer)
        if row["measurement_id"] in identities or row["extra"]["locator"] in locators:
            raise ProjectionError("KV-quant sidecar duplicates a measurement")
        identities.add(row["measurement_id"])
        locators.add(row["extra"]["locator"])
        _scored_path(row)
    if len({(row["run_id"], row["scored_path"], row["scored_sha256"])
            for row in rows}) != 1:
        raise ProjectionError("KV-quant sidecar mixes runs or scored artifacts")
    return tuple({"row": row, "sidecar_path": str(path)} for row in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("KV-quant native capture row missing")
    row = native["row"]
    _check_row(row, _producer())
    artifact = _scored_path(row)
    present = artifact.is_file()
    verified = present and _sha256(artifact) == row["scored_sha256"]
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"],
        value=row["value"], date=row["date"], category=row["category"],
        claim=(f"{row['claim']} K buffer {row['extra']['kv_buffer_k_mib']} MiB; "
               f"V buffer {row['extra']['kv_buffer_v_mib']} MiB; "
               "mixed K/V structurally absent; prefill depth is part of the key."),
        metric_direction=row["metric_direction"],
        protocol_id=row["protocol_id"], reps=row["reps"],
        reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["scored_sha256"],
        attestation_locator=(f"{row['extra']['locator']}|{row['scored_path']}"
                             f"#sha256={row['scored_sha256']}"),
        attestation_present=present, attestation_verified=True if verified else None,
        source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "row_sha256": row["row_sha256"],
               "sidecar_path": native.get("sidecar_path", ""),
               "scored_path": row["scored_path"], **row["extra"]},
    )
