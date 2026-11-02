"""Prospective native-output capture for KVU-19a-2; projection only.

Called by the producer at the end of its own execution, with observations it
just recorded. Historical files cannot be imported through this API. Missing
observations remain in the native result and emit no numeric measurement.
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ProjectionError, register, to_frames  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402

SCHEMA = "epyc.vidya.kvu19a2.native.v1"
SOURCE_KIND = "kvu19a2-native"


def row_problems(row: Any) -> list[str]:
    problems = ns.common_problems(row, schema=SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return problems
    extra = row["extra"]
    if row.get("protocol_id") != "" or row.get("metric") != "fa_output_nan_elements":
        problems.append("unexpected protocol or metric")
    if not ns.nonneg_int(row.get("value")) or row.get("reps") != 1:
        problems.append("nan count must be a nonnegative integer from one launch")
    for key in ("arm", "case", "source_archive_sha256", "executable_sha256", "hip_sha256", "raw_sha256"):
        if not ns.text(extra.get(key)):
            problems.append(f"missing {key}")
    for key in ("source_archive_sha256", "executable_sha256", "hip_sha256", "raw_sha256"):
        if not ns.SHA256.fullmatch(str(extra.get(key, ""))):
            problems.append(f"invalid {key}")
    if not isinstance(extra.get("mapped_ggml"), dict):
        problems.append("mapped_ggml must preserve the observed mapping or an empty object")
    if not ns.nonneg_int(extra.get("index")):
        problems.append("invalid observation index")
    if not problems:
        try:
            if not ns.results_present(row):
                raise ValueError("native result missing or changed")
            data = json.loads(Path(row["results_path"]).read_text())
            observation = data["observations"][extra["index"]]
            if (data.get("run_id") != row["run_id"] or observation.get("observed") is not True
                    or observation.get("nan_elements") != row["value"]
                    or any(observation.get(k) != extra.get(k) for k in observation)):
                raise ValueError("native observation mismatch")
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            problems.append("native result missing, changed, or mismatched")
    if not problems:
        problems += ns.check_identity(row, {"run_id": row["run_id"], "index": extra["index"],
                                            "results": row["results_sha256"]}, "kvu19a2")
    return problems + ns.self_hash_problems(row)


def record_run(output_dir: Path, *, run_id: str, producer: str, observations: list[dict]) -> tuple[Path, Path | None]:
    """Write native evidence then the source-side sidecar, exactly once per fresh run.

    Every observation must carry arm, case, observed, source_archive_sha256,
    executable_sha256, hip_sha256, mapped_ggml, raw_sha256, and either an
    observed nan_elements integer or a missing_reason. Caller supplies no
    protocol grade; timestamps are recorded now, not from a historical file.
    """
    if not ns.text(run_id) or not ns.text(producer) or not observations:
        raise ns.CaptureError("run identity and observations required")
    for obs in observations:
        if not isinstance(obs, dict) or type(obs.get("observed")) is not bool:
            raise ns.CaptureError("observation status required")
        if obs["observed"]:
            if not ns.nonneg_int(obs.get("nan_elements")):
                raise ns.CaptureError("observed nan count required")
            for key in ("source_archive_sha256", "executable_sha256", "hip_sha256", "raw_sha256"):
                if not ns.SHA256.fullmatch(str(obs.get(key, ""))):
                    raise ns.CaptureError(f"observed {key} required")
            if obs.get("arm") not in ("base", "candidate") or not ns.text(obs.get("case")) or not isinstance(obs.get("mapped_ggml"), dict):
                raise ns.CaptureError("observed identity and mapped library record required")
            raw_path = Path(obs.get("raw_path", ""))
            if not raw_path.is_absolute() or not raw_path.is_file() or ns.file_sha256(raw_path) != obs["raw_sha256"]:
                raise ns.CaptureError("raw output missing or digest mismatch")
            raw = raw_path.read_bytes()
            if not raw or len(raw) % 4 or sum(math.isnan(x[0]) for x in struct.iter_unpack("<f", raw)) != obs["nan_elements"]:
                raise ns.CaptureError("raw F32 NaN count mismatch")
        elif not ns.text(obs.get("missing_reason")) or obs.get("nan_elements") is not None:
            raise ns.CaptureError("missing observation requires reason and no numeric value")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = output_dir / "kvu19a2-native.json"
    native = {"schema": "kvu19a2.native-run.v1", "run_id": run_id, "producer": producer,
              "captured_at": now, "observations": observations}
    with result.open("x") as stream:
        stream.write(ns.canonical_json(native) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    digest = ns.file_sha256(result)
    rows = []
    for index, obs in enumerate(observations):
        if not obs["observed"]:
            continue
        identity = {"run_id": run_id, "index": index, "results": digest}
        extra = dict(obs, index=index)
        row = {"schema": SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": now,
               "date": now, "measurement_id": "kvu19a2_" + ns.content_hash(identity)[:24],
               "metric": "fa_output_nan_elements", "value": obs["nan_elements"], "unit": "elements",
               "metric_direction": "lower_better", "category": "BASELINE" if obs["arm"] == "base" else "CANDIDATE",
               "claim": f"Observed {obs['nan_elements']} NaN output elements for {obs['arm']} {obs['case']} in one native launch",
               "protocol_id": "", "reps": 1, "reps_basis": "one native process execution; no repeatability conclusion",
               "results_path": str(result.resolve()), "results_sha256": digest, "extra": extra}
        ns.seal(row)
        if errors := row_problems(row):
            raise ns.CaptureError("invalid capture: " + "; ".join(errors))
        rows.append(row)
    return result, ns.write_rows_atomic(output_dir / "belief_measurements.jsonl", rows) if rows else None


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("producer-authored row required")
    row = native["row"]
    if problems := row_problems(row):
        raise ProjectionError("invalid producer row: " + "; ".join(problems))
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND,
                             locator=f"kvu19a2:{row['run_id']}:{row['extra']['index']}",
                             sidecar_path=native.get("sidecar_path", ""))


def native_rows(sidecar: Path):
    return ns.native_rows(sidecar, row_problems)


def frames_for_sidecar(sidecar: Path, *, as_of: str):
    return [frame for native in native_rows(sidecar)
            for frame in to_frames(project(native), as_of=as_of,
                                   adapter_id="vidya.adapters.kvu19a2_native/v1", authority="measurement")]
