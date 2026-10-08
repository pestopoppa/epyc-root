"""Read only prospective Unlimited-OCR records written by ``odl_bench``.

Legacy demo JSON is deliberately not upgraded here: a read-side tuple cannot supply the write-time
input, prompt, or producer identity that the original run never captured.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import stat
import uuid
from datetime import datetime
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

# Frame authority names the existing measurement source class; it grants no ratification.
AUTHORITY = "measurement"

ADAPTER_ID = "vidya.adapters.odl_model_gated/v1"
SCHEMA = "epyc.odl_bench.unlimited_ocr_run/v1"
PROTOCOL = "odl-bench/unlimited-ocr-model-gated/v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_PAYLOAD_KEYS = {"schema", "record_id", "created_at", "protocol_id", "category", "source",
                 "producer", "inputs", "measurement", "run_metrics", "locator", "outputs"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _regular_bytes(path: Path) -> bytes:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ProjectionError(f"ODL record artifact is missing: {current}") from exc
        if current.is_symlink():
            raise ProjectionError(f"ODL record artifact path contains a symlink: {current}")
        if current != absolute and not current.is_dir():
            raise ProjectionError(f"ODL record parent is not a directory: {current}")
        if current == absolute and not stat.S_ISREG(info.st_mode):
            raise ProjectionError(f"ODL record artifact is not a regular file: {current}")
    try:
        fd = os.open(absolute, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ProjectionError(f"ODL record artifact changed type while opening: {absolute}")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                return handle.read()
        finally:
            os.close(fd)
    except OSError as exc:
        raise ProjectionError(f"ODL record artifact cannot be safely opened: {absolute}") from exc


def _bound_output(run_dir: Path, item: dict) -> None:
    if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
        raise ProjectionError("ODL output digest row has unknown or missing fields")
    path_text = item["path"]
    if not isinstance(path_text, str) or not path_text:
        raise ProjectionError("ODL output path is missing")
    path = Path(path_text)
    if not path.is_absolute() or ".." in path.parts:
        raise ProjectionError("ODL output path must be normalized and remain inside its run")
    try:
        relative = path.relative_to(run_dir)
    except ValueError as exc:
        raise ProjectionError("ODL output path escapes its run directory") from exc
    if not relative.parts or relative == Path("."):
        raise ProjectionError("ODL output path must name a file below its run directory")
    data = _regular_bytes(path)
    if (type(item["bytes"]) is not int or item["bytes"] != len(data)
            or not isinstance(item["sha256"], str) or not _SHA256.fullmatch(item["sha256"])
            or hashlib.sha256(data).hexdigest() != item["sha256"]):
        raise ProjectionError(f"ODL output bytes changed after write: {path}")


def _validate_payload(payload: Any, record_path: Path) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ProjectionError("ODL native record has unknown or missing top-level fields")
    if payload["schema"] != SCHEMA or payload["protocol_id"] != PROTOCOL:
        raise ProjectionError("ODL native record schema or protocol is unsupported")
    if payload["category"] != "CANDIDATE":
        raise ProjectionError("ODL source record category must be its producer-authored CANDIDATE")
    try:
        uuid.UUID(payload["record_id"])
        created = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProjectionError("ODL run record id or timestamp is malformed") from exc
    if created.tzinfo is None:
        raise ProjectionError("ODL run record timestamp must include a timezone")
    source = payload["source"]
    if (not isinstance(source, dict) or set(source) != {"repository", "commit", "working_tree_clean",
                                                       "checked_after_commit", "checked_after_clean"}
            or source["repository"] != "epyc-inference-research"
            or not isinstance(source["commit"], str) or not _GIT_COMMIT.fullmatch(source["commit"])
            or source["working_tree_clean"] is not True
            or source["checked_after_commit"] != source["commit"]
            or source["checked_after_clean"] is not True):
        raise ProjectionError("ODL producer source identity is absent or not clean")
    producer = payload["producer"]
    expected_producer = {"engine", "entrypoint", "prompt_profile", "prompt_sha256",
                         "prompt_source_sha256", "binary_path", "binary_sha256", "model_path",
                         "model_sha256", "mmproj_path", "mmproj_sha256", "context", "threads",
                         "parallel", "device", "gpu_layers", "max_tokens"}
    if not isinstance(producer, dict) or set(producer) != expected_producer:
        raise ProjectionError("ODL producer configuration has unknown or missing fields")
    if (producer["engine"] != "unlimited_ocr"
            or not isinstance(producer["prompt_profile"], str) or not producer["prompt_profile"]
            or not isinstance(producer["prompt_sha256"], str)
            or not _SHA256.fullmatch(producer["prompt_sha256"])):
        raise ProjectionError("ODL producer identity or effective prompt digest is malformed")
    for name in ("binary_path", "model_path", "mmproj_path", "device"):
        if not isinstance(producer[name], str) or not producer[name]:
            raise ProjectionError(f"ODL producer {name} must be explicitly recorded")
    for name in ("context", "threads", "parallel", "max_tokens"):
        if type(producer[name]) is not int or producer[name] < 1:
            raise ProjectionError(f"ODL producer {name} must be a positive integer")
    # Match the producer CLI's device-domain: -1 requests all layers, 0 is CPU-only;
    # all other producer integer fields above remain strictly positive.
    if type(producer["gpu_layers"]) is not int or producer["gpu_layers"] < -1:
        raise ProjectionError("ODL producer gpu_layers must be -1 or a nonnegative integer")
    for name in ("binary_sha256", "model_sha256", "mmproj_sha256"):
        if producer[name] is not None and (not isinstance(producer[name], str)
                                           or not _SHA256.fullmatch(producer[name])):
            raise ProjectionError(f"ODL optional {name} must be an exact SHA-256 or unknown")
    inputs = payload["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {"schema", "ground_truth", "images",
                                                       "image_bytes_sent_to_query", "started_utc"}:
        raise ProjectionError("ODL input manifest has unknown or missing fields")
    if (inputs["schema"] != "epyc.odl_bench.model_gated_inputs/v1"
            or inputs["image_bytes_sent_to_query"] is not True
            or not isinstance(inputs["started_utc"], str) or not inputs["started_utc"]):
        raise ProjectionError("ODL run lacks same-byte input parsing/transmission metadata")
    try:
        started = datetime.fromisoformat(inputs["started_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError("ODL run start time is not ISO-8601") from exc
    if started.tzinfo is None:
        raise ProjectionError("ODL run start time must include a timezone")
    gt = inputs["ground_truth"]
    if (not isinstance(gt, dict) or set(gt) != {"path", "bytes", "sha256", "parsed_from_hashed_bytes"}
            or gt["parsed_from_hashed_bytes"] is not True or type(gt["bytes"]) is not int
            or gt["bytes"] < 1 or not isinstance(gt["sha256"], str)
            or not _SHA256.fullmatch(gt["sha256"])):
        raise ProjectionError("ODL GT source bytes are not bound to the parsed dataset")
    images = inputs["images"]
    if not isinstance(images, list):
        raise ProjectionError("ODL image input inventory must be a list")
    for image in images:
        if not isinstance(image, dict) or image.get("status") not in {"read", "missing"}:
            raise ProjectionError("ODL image input row has an unknown status")
        expected = ({"gt_image", "path", "status", "bytes", "sha256"}
                    if image["status"] == "read" else {"gt_image", "path", "status"})
        if set(image) != expected:
            raise ProjectionError("ODL image input row has unknown or missing fields")
        if image["status"] == "read" and (type(image["bytes"]) is not int or image["bytes"] < 1
                or not isinstance(image["sha256"], str) or not _SHA256.fullmatch(image["sha256"])):
            raise ProjectionError("ODL image bytes read by inference are not hash-bound")
    measurement = payload["measurement"]
    if (not isinstance(measurement, dict) or set(measurement) != {"metric", "value", "unit",
            "direction", "reps", "reps_basis", "claim"} or measurement["metric"] != "latency_ms_median"
            or measurement["unit"] != "ms/page" or measurement["direction"] != "lower_better"
            or isinstance(measurement["value"], bool) or not isinstance(measurement["value"], (int, float))
            or not math.isfinite(measurement["value"]) or measurement["value"] <= 0
            or type(measurement["reps"]) is not int or measurement["reps"] < 1
            or not isinstance(measurement["reps_basis"], str) or not measurement["reps_basis"]
            or not isinstance(measurement["claim"], str) or not measurement["claim"]):
        raise ProjectionError("ODL primary run-level measurement is incomplete or non-finite")
    locator = payload["locator"]
    if not isinstance(locator, dict) or set(locator) != {"run_dir", "row_set", "input_manifest",
                                                         "inference_window"}:
        raise ProjectionError("ODL run locators have unknown or missing fields")
    run_dir = Path(locator["run_dir"]).absolute()
    if run_dir != record_path.parent.absolute() or locator["row_set"] != str(run_dir / "model_gated_row_set.json"):
        raise ProjectionError("ODL run locator does not bind the record to its native row set")
    if not all(isinstance(locator[name], str) and locator[name]
               for name in ("input_manifest", "inference_window")):
        raise ProjectionError("ODL run input/window locator is missing")
    window_path = Path(locator["inference_window"])
    window = json.loads(_regular_bytes(window_path))
    if (not isinstance(window, dict) or window.get("schema") != "epyc.autokernel.inference_call_window.v1"
            or window.get("released") is not True or not window.get("lock_path")
            or window.get("degraded")):
        raise ProjectionError("ODL model run has no completed shared inference-call window")
    outputs = payload["outputs"]
    if not isinstance(outputs, dict) or set(outputs) != {"predictions", "responses", "row_set"}:
        raise ProjectionError("ODL output manifest has unknown or missing fields")
    if not isinstance(outputs["predictions"], list) or not isinstance(outputs["responses"], list):
        raise ProjectionError("ODL output file inventories must be lists")
    for item in outputs["predictions"] + outputs["responses"] + [outputs["row_set"]]:
        _bound_output(run_dir, item)
    input_path = Path(locator["input_manifest"]).absolute()
    if input_path != run_dir / "responses" / "unlimited_ocr" / "producer_input_manifest.json":
        raise ProjectionError("ODL input locator does not name the producer's captured manifest")
    if not any(Path(row["path"]).absolute() == input_path for row in outputs["responses"]):
        raise ProjectionError("ODL source input manifest is missing from the retained response hashes")
    if not any(Path(row["path"]).absolute() == Path(locator["inference_window"]).absolute()
               for row in outputs["responses"]):
        raise ProjectionError("ODL inference-call window is missing from retained response hashes")
    if json.loads(_regular_bytes(input_path)) != inputs:
        raise ProjectionError("ODL payload input metadata differs from the producer-written input manifest")
    row_set = json.loads(_regular_bytes(run_dir / "model_gated_row_set.json"))
    if not isinstance(row_set, dict) or not isinstance(row_set.get("metric_rows"), list):
        raise ProjectionError("ODL row set has no native metric rows")
    expected_metrics = [{key: row.get(key) for key in
                         ("metric_family", "metric_name", "value", "n", "detail")}
                        for row in row_set["metric_rows"] if isinstance(row, dict)]
    if len(expected_metrics) != len(row_set["metric_rows"]) or payload["run_metrics"] != expected_metrics:
        raise ProjectionError("ODL run metrics differ from the native row-set file")
    native_speed = [row for row in row_set["metric_rows"] if isinstance(row, dict)
                    and row.get("engine") == "unlimited_ocr"
                    and row.get("metric_family") == "speed"
                    and row.get("metric_name") == "latency_ms_median"]
    if len(native_speed) != 1 or native_speed[0].get("value") != measurement["value"]:
        raise ProjectionError("ODL projected latency differs from the native row-set metric")
    attempts = [row for row in row_set.get("run_manifests", []) if isinstance(row, dict)
                and row.get("engine") == "unlimited_ocr"]
    if len(attempts) != 1 or not isinstance(attempts[0].get("artifacts"), list):
        raise ProjectionError("ODL row set does not identify one native model-gated run")
    timed = [row for row in attempts[0]["artifacts"] if isinstance(row, dict)
             and type(row.get("latency_ms")) in (int, float) and row["latency_ms"] > 0]
    if len(timed) != measurement["reps"]:
        raise ProjectionError("ODL reps differ from the native positive-latency page count")
    return payload


def native_rows(path: str | Path) -> tuple[dict, ...]:
    record_path = Path(path)
    if not os.path.lexists(record_path):
        return ()
    try:
        data = _regular_bytes(record_path)
        envelope = json.loads(data)
        if not isinstance(envelope, dict) or set(envelope) != {"payload_sha256", "payload"}:
            raise ProjectionError("ODL record envelope has unknown or missing fields")
        digest = hashlib.sha256(_canonical(envelope["payload"])).hexdigest()
        if envelope["payload_sha256"] != digest:
            raise ProjectionError("ODL native payload digest does not match its write-time envelope")
        payload = _validate_payload(envelope["payload"], record_path.absolute())
        return ({"envelope": envelope, "record_path": str(record_path.absolute()),
                 "record_sha256": hashlib.sha256(data).hexdigest(), "payload": payload},)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f"ODL run record refused: {exc}") from exc


@register("odl-unlimited-ocr-run", source_class="measurement")
def project_unlimited_ocr_run(native: dict) -> ClaimTuple:
    try:
        reopened = native_rows(native["record_path"])
        if len(reopened) != 1 or reopened[0] != native:
            raise ProjectionError("ODL native record or output bytes changed after reopening")
        payload = native["payload"]
        metric = payload["measurement"]
        return ClaimTuple(
            measurement_id="odl-unlimited-ocr:" + payload["record_id"],
            metric=metric["metric"], value=metric["value"],
            date=payload["inputs"]["started_utc"], category=payload["category"],
            metric_direction=metric["direction"], protocol_id=payload["protocol_id"],
            reps=metric["reps"], reps_basis=metric["reps_basis"], unit=metric["unit"],
            claim=metric["claim"], attestation_path=native["record_path"],
            attestation_sha256=native["record_sha256"], attestation_present=True,
            attestation_verified=True, source_kind=ADAPTER_ID, source_class="measurement",
            extra={"record_id": payload["record_id"], "source": payload["source"],
                   "producer": payload["producer"], "inputs": payload["inputs"],
                   "run_metrics": payload["run_metrics"], "outputs": payload["outputs"]})
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f"ODL run projection refused: {exc}") from exc
