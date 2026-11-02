"""Prospective M4 GPU process validation; no deployment or trusted plan is configured.

A caller must supply a separately reviewed Trust object, never one extracted
from a native record. This module is not registered for production ingestion.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError

SOURCE_KIND = "m4-gpu-recipe-speed-measurement"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _absolute(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute() or ".." in p.parts:
        raise ProjectionError("absolute path without parent traversal required")
    resolved = p.resolve(strict=True)
    if resolved != p:
        raise ProjectionError("symlink or noncanonical path")
    return resolved


def _read(path: str | Path) -> bytes:
    try:
        return _absolute(path).read_bytes()
    except (OSError, ValueError, TypeError) as exc:
        raise ProjectionError(f"cannot read sealed file: {exc}") from exc


def _file_sha(path: str | Path) -> str:
    try:
        with _absolute(path).open("rb") as fh:
            return hashlib.file_digest(fh, "sha256").hexdigest()
    except (OSError, ValueError, TypeError) as exc:
        raise ProjectionError(f"cannot hash sealed file: {exc}") from exc


def parse_grant(raw: bytes, identity: dict, *, qualification: bool) -> tuple[float, float]:
    try:
        parts = raw.decode().split()
        fields = dict(part.split("=", 1) for part in parts)
        required = {"regions", "start", "end"}
        if qualification:
            required |= {"holds", "schema", "id", "kind"}
            if set(fields) not in (required, required | {"admission_class"}):
                raise ValueError("unexpected fixture fields")
            if fields["schema"] != "epyc.rowflow.dryrun-grant.v1" or fields["kind"] != "rowflow-dryrun" or fields["id"] != identity["id"]:
                raise ValueError("fixture identity mismatch")
        elif set(fields) != required | {"holds"}:
            raise ValueError("live rowflow GPU-quiet grant required")
        if "holds" in fields and "gpu-quiet" not in fields["holds"].split(","):
            raise ValueError("grant does not hold GPU quiet")
        if len(parts) != len(fields) or fields["regions"] != identity["regions"]:
            raise ValueError("duplicate or wrong grant region")
        start = datetime.strptime(fields["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp()
        end = datetime.strptime(fields["end"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp()
        if start >= end:
            raise ValueError("invalid grant interval")
        return start, end
    except (KeyError, ValueError, UnicodeError, TypeError) as exc:
        raise ProjectionError(f"grant receipt invalid: {exc}") from exc


@dataclass(frozen=True)
class Trust:
    """Deployment-owned bindings independently authorized before capture."""
    capture_root: Path
    plan_path: Path
    plan_sha256: str
    sources: tuple[tuple[Path, str], ...]
    qualification_only: bool = False

    def plan(self) -> dict:
        if len(self.plan_sha256) != 64 or not self.sources:
            raise ProjectionError("trusted plan and source seals required")
        raw = _read(self.plan_path)
        if sha(raw) != self.plan_sha256:
            raise ProjectionError("trusted plan changed")
        for path, digest in self.sources:
            if sha(_read(path)) != digest:
                raise ProjectionError("trusted source changed")
        try:
            plan = json.loads(raw)
        except ValueError as exc:
            raise ProjectionError("invalid trusted plan") from exc
        if not isinstance(plan, dict) or plan.get("schema") != "epyc.m4.gpu.plan.v2":
            raise ProjectionError("invalid trusted plan schema")
        return plan


def _capture(path: str | Path, trust: Trust) -> Path:
    try:
        root = _absolute(trust.capture_root)
        path = _absolute(path)
    except OSError as exc:
        raise ProjectionError("capture path unavailable") from exc
    if root not in path.parents:
        raise ProjectionError("capture outside trusted root")
    return path


def validate_residency(samples: Any, *, pid: int, device: str, start_ns: int, end_ns: int, limit: int) -> None:
    if (type(pid) is not int or pid <= 0 or not isinstance(device, str) or not device
            or type(start_ns) is not int or type(end_ns) is not int or start_ns >= end_ns
            or type(limit) is not int or limit <= 0 or not isinstance(samples, list) or not samples):
        raise ProjectionError("invalid residency interval or configuration")
    inside = False
    for sample in samples:
        if (not isinstance(sample, dict) or sample.get("pid") != pid or sample.get("device") != device
                or type(sample.get("timestamp_ns")) is not int or type(sample.get("own_vram_bytes")) is not int
                or not 0 < sample["own_vram_bytes"] <= limit or type(sample.get("device_vram_bytes")) is not int
                or sample["device_vram_bytes"] <= 0 or type(sample.get("kfd_process_count")) is not int
                or sample["kfd_process_count"] < 1 or sample.get("error")):
            raise ProjectionError("invalid or unreadable residency sample")
        inside |= start_ns <= sample["timestamp_ns"] <= end_ns
    if not inside:
        raise ProjectionError("no residency sample inside request interval")


def validate_capture(path: str | Path, trust: Trust, *, require_guardian: bool = True) -> tuple[dict, dict, float]:
    plan = trust.plan()
    capture_path = _capture(path, trust)
    try:
        doc = json.loads(capture_path.read_bytes())
        key = doc["plan_cell"]
        expected = plan["cells"][key]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectionError("capture or planned cell missing") from exc
    if doc.get("schema") != "epyc.m4.gpu.capture.v2" or doc.get("plan_sha256") != trust.plan_sha256:
        raise ProjectionError("capture is not bound to trusted plan")
    # The complete execution identity is taken from the independent plan.
    for field in ("role", "arm", "source_commit", "model", "recipe", "argv", "environment", "device", "np"):
        if field not in expected or doc.get(field) != expected[field]:
            raise ProjectionError(f"planned {field} mismatch")
    if doc.get("arm") not in ("BASELINE", "CANDIDATE") or type(doc.get("np")) is not int or doc["np"] <= 0:
        raise ProjectionError("invalid arm or slot count")
    files = expected.get("files")
    if not isinstance(files, dict) or not files or not {"binary", "model", "prompt"}.issubset(files):
        raise ProjectionError("planned binary/model/prompt seals missing")
    for item in files.values():
        if not isinstance(item, dict) or _file_sha(item.get("path", "")) != item.get("sha256"):
            raise ProjectionError("planned file changed")
    maps = doc.get("mapped_ggml")
    expected_maps = expected.get("ggml")
    if not isinstance(maps, dict) or not maps or maps != expected_maps:
        raise ProjectionError("mapped ggml differs from independent plan")
    for name, digest in maps.items():
        if _file_sha(name) != digest:
            raise ProjectionError("mapped ggml changed")
    if (not isinstance(doc.get("process"), dict) or type(doc["process"].get("pid")) is not int
            or type(doc["process"].get("start_ticks")) is not int or doc["process"]["start_ticks"] <= 0
            or doc.get("cleanup") != {"owned_pid_dead": True, "start_ticks": doc["process"]["start_ticks"]}):
        raise ProjectionError("process identity or cleanup missing")
    if doc.get("grant") != expected.get("grant") or not doc.get("grant"):
        raise ProjectionError("grant does not match plan")
    validate_residency(doc.get("residency"), pid=doc["process"]["pid"], device=doc["device"],
                       start_ns=doc.get("request_start_ns"), end_ns=doc.get("request_end_ns"), limit=expected.get("vram_limit_bytes"))
    try:
        receipt = _capture(doc["grant_receipt_path"], trust).read_bytes()
        if sha(receipt) != doc["grant_receipt_sha256"]:
            raise ValueError("grant receipt hash")
        start, end = parse_grant(receipt, doc['grant'], qualification=trust.qualification_only)
        start *= 1_000_000_000
        end *= 1_000_000_000
        if not start <= doc["request_start_ns"] < doc["request_end_ns"] < end:
            raise ValueError("request outside grant")
    except (KeyError, OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ProjectionError(f"grant receipt invalid: {exc}") from exc
    if require_guardian:
        try:
            watch_path = _capture(expected["watch_result_path"], trust)
            watch_result = json.loads(watch_path.read_bytes())
        except (KeyError, OSError, ValueError, TypeError) as exc:
            raise ProjectionError("guardian completion receipt missing") from exc
        if (watch_result.get("status") != "closed" or watch_result.get("reason") != "none"
                or watch_result.get("rc") != 0 or watch_result.get("containment_empty") is not True
                or watch_result.get("cleanup_error")):
            raise ProjectionError("guardian did not close cleanly")
    raw_path = _capture(doc.get("requests_path", ""), trust)
    raw = raw_path.read_bytes()
    if sha(raw) != doc.get("requests_sha256"):
        raise ProjectionError("request seal mismatch")
    try:
        requests = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except ValueError as exc:
        raise ProjectionError("invalid request records") from exc
    if type(expected.get("request_count")) is not int or len(requests) != expected["request_count"] or not requests:
        raise ProjectionError("incomplete request denominator")
    planned_requests = expected.get("request_sha256")
    if (not isinstance(planned_requests, list) or len(planned_requests) != expected["request_count"]
            or any(not isinstance(h, str) or len(h) != 64 for h in planned_requests)):
        raise ProjectionError("planned request payload hashes missing")
    streams: dict[int, list[float]] = {}
    indices = set()
    for item in requests:
        if (not isinstance(item, dict) or item.get("success") is not True or item.get("http_status") != 200
                or item.get("error") or type(item.get("request_index")) is not int
                or item["request_index"] in indices or type(item.get("stream_id")) is not int
                or not 0 <= item["stream_id"] < doc["np"] or type(item.get("predicted_tokens")) is not int
                or item["predicted_tokens"] <= 0 or type(item.get("predicted_ms")) not in (int, float)
                or not math.isfinite(item["predicted_ms"]) or item["predicted_ms"] <= 0):
            raise ProjectionError("invalid or incomplete request")
        index = item["request_index"]
        if not 0 <= index < len(planned_requests) or item.get("request_sha256") != planned_requests[index]:
            raise ProjectionError("actual request payload differs from plan")
        response = item.get("response")
        timings = response.get("timings") if isinstance(response, dict) else None
        if (not isinstance(timings, dict) or response.get("stop") is not True
                or timings.get("predicted_n") != item["predicted_tokens"]
                or timings.get("predicted_ms") != item["predicted_ms"]):
            raise ProjectionError("raw response timing or completion mismatch")
        indices.add(index)
        counts = streams.setdefault(item["stream_id"], [0, 0.0])
        counts[0] += item["predicted_tokens"]
        counts[1] += item["predicted_ms"] / 1000
    if indices != set(range(expected["request_count"])):
        raise ProjectionError("request indices incomplete")
    value = sum(tokens / seconds for tokens, seconds in streams.values())
    if type(doc.get("aggregate_decode_tps")) not in (int, float) or not math.isclose(value, doc["aggregate_decode_tps"], rel_tol=1e-12, abs_tol=1e-12):
        raise ProjectionError("aggregate does not rederive")
    return doc, expected, value


def project(path: str | Path, trust: Trust) -> ClaimTuple:
    if trust.qualification_only:
        raise ProjectionError("qualification-only source cannot project measurement")
    doc, _, value = validate_capture(path, trust)
    raw = _read(_capture(doc["requests_path"], trust))
    return ClaimTuple(measurement_id=doc["measurement_id"], metric="aggregate_decode_tokens_per_s", value=value,
        date=doc["date"], category=doc["arm"], claim=f"{doc['arm']} aggregate decode throughput",
        metric_direction="higher_better", protocol_id="", reps=1, reps_basis="one fresh-server process",
        unit="tokens_per_second", attestation_path=doc["requests_path"], attestation_locator=doc["requests_path"],
        attestation_sha256=sha(raw), attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra={"plan_sha256":trust.plan_sha256, "role":doc["role"], "np":doc["np"]}, observation={})
