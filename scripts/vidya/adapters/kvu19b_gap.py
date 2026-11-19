"""VB-FA-MASKSKIP: prospective KVU-19b same-binary p3batch records (``kvu19b-gap.clean.v1``); projection, not grading.

Source: ``belief_measurements.jsonl`` lines (``epyc.native_claim_tuple.v1``, ``source_family`` VB-FA-MASKSKIP) written by the
producer's ``belief_write.write_child`` after each verified full-mode native child, each bound to an immutable
``child-NN.json`` (``kvu19b-gap.child-warrant.v1``) holding the original row, raw stdout/stderr digests, source/build/model
identities and the write-time live-GPU samples.

Doctrine: PROJECTION ONLY. ``claim_tuple.grade()`` decides; there is no ladder here. The reader re-derives what it can from the
child warrant and refuses on any difference: the attestation file must still hash to the authored digest, the value must equal
the warrant's own ``ms_per_step``, the measurement id must re-derive, the child must have exited 0 with verified cleanup, the raw
stdout/stderr must still hash to the warrant, and at least two in-window samples must show own-PID VRAM > 0 with mapped libggml.
``protocol_id`` must be empty (no ratified protocol), so the ladder caps the tuple at an observation. The scope is a synthetic
p3batch microbenchmark: not serving speed, not causal attribution, not a 27B result.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402

RECORD_SCHEMA = "epyc.native_claim_tuple.v1"
CHILD_SCHEMA = "kvu19b-gap.child-warrant.v1"
SOURCE_FAMILY = "VB-FA-MASKSKIP"
SOURCE_KIND = "kvu19b-gap"
ADAPTER_ID = "vidya.adapters.kvu19b_gap/v1"
AUTHORITY = "measurement"
SIDECAR_NAME = "belief_measurements.jsonl"
METRIC = "p3batch_synchronized_step_ms"
_FIELDS = {f.name for f in dataclasses.fields(ClaimTuple)}


def _child(tup: dict) -> dict:
    path = Path(tup["attestation_path"])
    if not path.is_file() or ns.file_sha256(path) != tup["attestation_sha256"]:
        raise ValueError("attestation changed or missing")
    child = json.loads(path.read_text())
    if child.get("schema") != CHILD_SCHEMA:
        raise ValueError("not a kvu19b child warrant")
    return child


def record_problems(record: Any) -> list[str]:
    if not isinstance(record, dict) or record.get("schema") != RECORD_SCHEMA or record.get("source_family") != SOURCE_FAMILY:
        return ["not a VB-FA-MASKSKIP native claim-tuple record"]
    tup = record.get("claim_tuple")
    if not isinstance(tup, dict):
        return ["claim_tuple missing"]
    try:
        if set(tup) - _FIELDS:
            raise ValueError("unknown ClaimTuple field")
        child = _child(tup)
        row, assets = child["row"], child["assets"]
        idx = row["index"]
        if (tup["metric"] != METRIC or tup["metric_direction"] != "lower_better" or tup["protocol_id"] != "" or
                tup["source_class"] != "measurement" or tup["reps"] != 1 or not ns.finite(tup["value"]) or
                tup["value"] != row["metrics"]["ms_per_step"] or
                tup["measurement_id"] != f"{Path(tup['attestation_path']).parent.name}:{idx}:ms_per_step" or
                tup["category"] != ("CANDIDATE" if row["kvu"] else "BASELINE")):
            raise ValueError("tuple differs from its child warrant")
        if row.get("rc") != 0 or not row.get("cleanup", {}).get("verified_dead") or not row.get("completed_utc"):
            raise ValueError("child not verified complete")
        for name in ("stdout", "stderr"):
            p = Path(row[name])
            if not p.is_file() or ns.file_sha256(p) != row["raw_sha256"][name]:
                raise ValueError("raw native output changed: " + name)
        live = [s for s in row["samples"] if s["own_vram_b"] > 0 and
                all(v for k, v in s["mapped_libraries"].items() if k.startswith("libggml"))]
        if len(live) < 2:
            raise ValueError("no in-window live GPU warrant")
        app = tup["applicability"]
        if (app.get("model_sha256") != assets["model"]["sha256"] or app.get("model_file") != assets["model"]["path"] or
                app.get("kernel") != assets["source_commit"] or app.get("device") != live[0]["gpu_bdf"] or
                app.get("knobs", {}).get("kv_unified") != row["kvu"]):
            raise ValueError("applicability differs from warrant identity")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, IndexError):
        return ["native evidence missing, changed, or inconsistent"]
    return []


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    record = native.get("record") if isinstance(native, dict) else None
    if problems := record_problems(record):
        raise ProjectionError("invalid producer record: " + "; ".join(problems))
    tup = dict(record["claim_tuple"])
    app = dict(tup["applicability"])
    app["model_file"] = Path(app["model_file"]).name       # planner targets match on the file name
    # The planner scopes a GPU target by backend class, and the record names the card by PCI BDF, not architecture;
    # inventing an architecture would be inventing scope, so the BDF stays authored custody in ``extra`` instead.
    if app.get("backend") == "HIP":
        app["backend"] = "gpu"
    bdf = app.pop("device", "")
    tup["applicability"] = app
    tup["attestation_locator"] = "kvu19b:" + tup["measurement_id"]
    tup["extra"] = {**tup.get("extra", {}), "device_bdf": bdf, "sidecar_path": native.get("sidecar_path", "")}
    return ClaimTuple(**tup)


def native_rows(sidecar: Path):
    sidecar = Path(sidecar)
    if not sidecar.is_file():
        return ()
    records = []
    for line in sidecar.read_text().splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            raise ProjectionError("kvu19b sidecar invalid")
        if record_problems(record):
            raise ProjectionError("kvu19b sidecar invalid or changed")
        records.append(record)
    ids = [r["claim_tuple"]["measurement_id"] for r in records]
    if len(set(ids)) != len(ids):
        raise ProjectionError("kvu19b sidecar repeats a measurement id")
    return tuple({"record": r, "sidecar_path": str(sidecar)} for r in records)


def frames_for_sidecar(sidecar: Path, *, as_of: str):
    return [f for native in native_rows(sidecar) for f in
            to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority="measurement")]
