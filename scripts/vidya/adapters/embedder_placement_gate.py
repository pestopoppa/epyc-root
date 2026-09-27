"""Read producer-authored UFH-12 embedder placement gate sidecars (VB-UFH12-PLACEMENT).

The producer is ``epyc-orchestrator`` ``scripts/server/embedder_placement_gate.py``; its write side,
``scripts/server/embedder_placement_capture.py``, emits ``<record-stem>.belief_measurements.jsonl``
beside each gate record. This reader loads that capture module pinned by sha256 and uses ITS
``validate_row``, so writer and reader share one definition of a well-formed row.

One malformed row voids the whole sidecar. G1 (frontdoor decode, per port), G2 (pool scaling) and
G3 (speech non-regression) stay separate claims: each row is one metric of one gate. The adapter
projects; ``claim_tuple.grade()`` alone decides (``protocol_id`` is empty, so every row is an
observation until a protocol for this gate is codified).
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

ADAPTER_ID = "vidya.adapters.embedder_placement_gate/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "embedder-placement-gate"
ORCHESTRATOR_ROOT = Path("/workspace/repos/epyc-orchestrator")
PRODUCER_PATH = ORCHESTRATOR_ROOT / "scripts/server/embedder_placement_capture.py"
PRODUCER_SHA256 = "63a5ea185dc8d00e1b18e99e7f306dcbd5816be1e1909d4d6f5c3627deae02a4"
DEFAULT_ROOT = Path("/mnt/raid0/llm/epyc-orchestrator/data/embedder_placement")

#: every metric a gate emits for one unit (per port for G1, per run otherwise)
_G1_CORE = {"g1_s_over_q_median", "g1_q_decode_tps_median"}
_G2 = {"g2_scaling_ratio", "g2_one_port_texts_per_s", "g2_whole_pool_texts_per_s"}
_G3 = {"g3_saturated_stt_rtf_median", "g3_saturated_stt_rtf_worst",
       "g3_saturated_tts_first_packet_s_median", "g3_saturated_tts_first_packet_s_worst"}


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
        raise ProjectionError(f"placement-gate capture module unavailable: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ProjectionError("placement-gate capture module must be a regular single-link file")
    if _sha256(PRODUCER_PATH) != PRODUCER_SHA256:
        raise ProjectionError("placement-gate capture module bytes differ from reviewed sha256")
    name = "_epyc_embedder_placement_capture"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PRODUCER_PATH)
    if spec is None or spec.loader is None:
        raise ProjectionError("placement-gate capture module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ProjectionError(f"placement-gate capture module cannot be loaded: {exc}") from exc
    return module


def _check_row(row: Any, producer: ModuleType) -> None:
    try:
        problems = producer.validate_row(row)
    except Exception as exc:
        raise ProjectionError(f"placement-gate row validator failed: {exc}") from exc
    if problems:
        raise ProjectionError("placement-gate row refused: " + "; ".join(problems))
    if row["source_kind"] != SOURCE_KIND:
        raise ProjectionError("placement-gate row names a foreign source")


def _record_path(sidecar: Path, row: dict, producer: ModuleType) -> Path:
    record = sidecar.parent / row["record_file"]
    if producer.sidecar_path(record).name != sidecar.name:
        raise ProjectionError("placement-gate sidecar is not the sidecar of its named record")
    return record


def _check_coverage(rows: list[dict]) -> None:
    gates = {row["gate"] for row in rows}
    if gates not in ({"G1", "G2"}, {"G3"}):
        raise ProjectionError(f"placement-gate sidecar mixes or omits gates: {sorted(gates)}")
    metrics = {(row["port"], row["metric"]) for row in rows}
    if "G3" in gates:
        if {m for _, m in metrics} != _G3:
            raise ProjectionError("placement-gate G3 sidecar lacks a speech metric")
        return
    if {m for p, m in metrics if p is None} != _G2:
        raise ProjectionError("placement-gate G2 claims incomplete")
    ports = {p for p, _ in metrics if p is not None}
    for port in ports:
        have = {m for p, m in metrics if p == port}
        if not _G1_CORE <= have:
            raise ProjectionError(f"placement-gate G1 :{port} lacks its ratio or idle baseline")
    fd_ports = rows[0]["extra"]["provenance"]["instrument"]["method"].get("fd_ports")
    if sorted(ports) != sorted(fd_ports or []):
        raise ProjectionError("placement-gate G1 ports differ from the run's frontdoor ports")


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    producer = _producer()
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"placement-gate sidecar unreadable: {exc}") from exc
    if not rows:
        return ()
    identities: set[str] = set()
    for row in rows:
        _check_row(row, producer)
        key = (row["measurement_id"], row["extra"]["locator"])
        if key[0] in identities or key[1] in identities:
            raise ProjectionError("placement-gate sidecar duplicates a measurement")
        identities.update(key)
        _record_path(path, row, producer)
    if len({(r["run_id"], r["record_file"], r["record_sha256"], r["extra"]["provenance_sha256"])
            for r in rows}) != 1:
        raise ProjectionError("placement-gate sidecar mixes runs, records or provenance")
    _check_coverage(rows)
    return tuple({"row": row, "sidecar_path": str(path)} for row in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("placement-gate native capture row missing")
    row = native["row"]
    producer = _producer()
    _check_row(row, producer)
    sidecar = Path(native.get("sidecar_path") or "")
    record = _record_path(sidecar, row, producer)
    present = record.is_file()
    verified = present and _sha256(record) == row["record_sha256"]
    prov = row["extra"]["provenance"]
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=row["claim"],
        metric_direction=row["metric_direction"], protocol_id=row["protocol_id"],
        reps=row["reps"], reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_path=str(record), attestation_sha256=row["record_sha256"],
        attestation_locator=f"{row['extra']['locator']}|{record}#sha256={row['record_sha256']}",
        attestation_present=present, attestation_verified=True if verified else None,
        source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "row_sha256": row["row_sha256"],
               "sidecar_path": str(sidecar), "gate": row["gate"], "port": row["port"],
               "run_id": row["run_id"], "samples": row["samples"],
               "locator": row["extra"]["locator"], "label": row["extra"]["label"],
               "load_mode": row["extra"]["load_mode"],
               "instrument_class": row["extra"]["instrument_class"],
               "topology_hash": prov["topology_hash"],
               "placement_digest": prov["placement_digest"],
               "provenance_sha256": row["extra"]["provenance_sha256"],
               "provenance": prov},
    )
