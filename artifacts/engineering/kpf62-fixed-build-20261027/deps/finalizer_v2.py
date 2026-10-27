#!/usr/bin/env python3
"""Finalize one prospective KPF-62 generated-tiny-model G1 capture.

This scratch bridge accepts only the producer's new per-position schema-v1 JSONL and a
run invocation record. It never reads legacy logs, invents native fields, or edits the
human-ratified measurement protocol. Execute only inside the approved capture window.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_WT = Path("/mnt/raid0/llm/worktrees/codex-ni-20261024-kpf62-root-publish")
ROOT_COMMIT = "8f4fea302798d9b938e2da655cee86ca3d14f09d"
ROOT_ADAPTER_SHA256 = "3c078ecc0a1b47d2c5de215413742aaea5f00558c1d7955df4d69808726e79ec"
ROOT_TEST_SHA256 = "c1f1ad39326f8a5f903a591d3d6106b08395204ec93f104d41000d7773edb682"
PRODUCER_WT = Path("/mnt/raid0/llm/worktrees/codex-ni-20261024-kpf62-g1capture-publish")
PRODUCER_COMMIT = "0a9fa2c29bc0929d7a2493a8416659ca892ae3d6"
OUTPUT_ROOT = Path("/mnt/raid0/llm/tmp/codex-ni-20261024-kpf62-adapter/finalized-v2")
INVOCATION_SCHEMA = "epyc.chunk_kv.g1_invocation.v1"
POSITION_SCHEMA = "epyc.chunk_kv.g1_position.v1"
EXPECTED_DELTAS = (1, 17, 300)
EXPECTED_SUFFIX = 6
COMPONENTS = ("k", "v", "logits")
COMPARISONS = ("inject_vs_seq_add", "inject_vs_in_place_ref")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class Refusal(ValueError):
    pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise Refusal(f"{label} must be a UTC timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refusal(f"{label} is not an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise Refusal(f"{label} must include a zero-offset UTC timezone")
    return parsed


def require_map(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Refusal(f"{label} must be an object")
    return value


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Refusal(f"{label} must be a non-empty string")
    return value


def require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise Refusal(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def verify_tree(path: Path, expected_commit: str, label: str) -> None:
    if not path.is_dir():
        raise Refusal(f"pinned {label} worktree is missing: {path}")
    head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    if head != expected_commit:
        raise Refusal(f"{label} pin mismatch: {head} != {expected_commit}")
    dirty = subprocess.run(["git", "-C", str(path), "status", "--porcelain"],
                           check=True, capture_output=True, text=True).stdout
    if dirty:
        raise Refusal(f"{label} worktree is dirty")


def verify_code_pins() -> None:
    verify_tree(ROOT_WT, ROOT_COMMIT, "ROOT adapter")
    verify_tree(PRODUCER_WT, PRODUCER_COMMIT, "G1 producer")
    files = (
        (ROOT_WT / "scripts/vidya/adapters/chunk_kv.py", ROOT_ADAPTER_SHA256, "adapter"),
        (ROOT_WT / "tests/vidya/test_ibench_kvchunk_carriers.py", ROOT_TEST_SHA256, "adapter test"),
    )
    for path, expected, label in files:
        if file_sha256(path) != expected:
            raise Refusal(f"{label} source hash mismatch")


def read_invocation(path: Path, raw_path: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"cannot read invocation JSON: {exc}") from exc
    record = require_map(record, "invocation")
    if record.get("schema") != INVOCATION_SCHEMA:
        raise Refusal(f"invocation schema must be {INVOCATION_SCHEMA!r}")
    if record.get("producer_commit") != PRODUCER_COMMIT:
        raise Refusal("invocation producer_commit does not match the approved producer pin")
    if record.get("root_adapter_commit") != ROOT_COMMIT:
        raise Refusal("invocation root_adapter_commit does not match the approved adapter pin")
    run_id = require_text(record.get("run_id"), "run_id")
    if not RUN_ID_RE.fullmatch(run_id):
        raise Refusal("run_id contains unsupported path characters")

    model = require_map(record.get("model"), "model")
    require_text(model.get("name"), "model.name")
    model_path = Path(require_text(model.get("path"), "model.path")).resolve(strict=True)
    if file_sha256(model_path) != require_sha(model.get("sha256"), "model.sha256"):
        raise Refusal("model file hash does not match invocation")
    binary = require_map(record.get("binary"), "binary")
    binary_path = Path(require_text(binary.get("path"), "binary.path")).resolve(strict=True)
    if file_sha256(binary_path) != require_sha(binary.get("sha256"), "binary.sha256"):
        raise Refusal("test binary hash does not match invocation")

    argv = record.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        raise Refusal("argv must retain the actual test-chunk-kv argument vector")
    if not Path(argv[0]).is_absolute() or Path(argv[0]).resolve(strict=True) != binary_path:
        raise Refusal("argv[0] does not identify the hashed test binary")
    def option_value(option: str) -> str:
        indexes = [i for i, item in enumerate(argv) if item == option]
        if len(indexes) != 1 or indexes[0] + 1 >= len(argv):
            raise Refusal(f"argv must contain exactly one {option} value pair")
        return argv[indexes[0] + 1]
    if Path(option_value("-m")).resolve(strict=True) != model_path:
        raise Refusal("argv model path does not identify the hashed model")
    if option_value("-ctk") != "f32" or option_value("-ctv") != "f32":
        raise Refusal("G1 capture must explicitly run with -ctk f32 -ctv f32")
    threads = option_value("-t")
    if not threads.isdecimal() or int(threads) < 1:
        raise Refusal("argv must record a positive -t thread count")
    capture = require_map(record.get("capture"), "capture")
    recorded_raw = Path(require_text(capture.get("path"), "capture.path")).resolve(strict=True)
    if recorded_raw != raw_path.resolve(strict=True):
        raise Refusal("CLI raw JSONL path does not match invocation capture.path")
    capture_arg = option_value("--g1-capture-jsonl")
    if not Path(capture_arg).is_absolute() or Path(capture_arg).resolve(strict=True) != recorded_raw:
        raise Refusal("argv capture path does not identify the bound raw JSONL")
    raw_hash = require_sha(capture.get("sha256"), "capture.sha256")
    if file_sha256(recorded_raw) != raw_hash:
        raise Refusal("raw capture hash does not match invocation")
    if capture.get("exit_code") != 0:
        raise Refusal("producer run did not exit successfully; raw capture preserved, no sidecar emitted")
    if capture.get("deltas") != list(EXPECTED_DELTAS):
        raise Refusal(f"capture.deltas must equal {list(EXPECTED_DELTAS)}")
    n_chunk = capture.get("n_chunk")
    n_suffix = capture.get("n_suffix")
    environment = require_map(capture.get("environment"), "capture.environment")
    chunk_env = environment.get("CKV_N_CHUNK")
    if chunk_env is None:
        resolved_n_chunk = 24
    elif isinstance(chunk_env, str) and chunk_env.isdecimal():
        resolved_n_chunk = min(512, max(24, int(chunk_env)))
    else:
        raise Refusal("capture.environment.CKV_N_CHUNK must be absent or a decimal string")
    if isinstance(n_chunk, bool) or not isinstance(n_chunk, int) or n_chunk != resolved_n_chunk:
        raise Refusal("capture.n_chunk does not match the producer's resolved CKV_N_CHUNK value")
    if environment.get("CKV_G1_REF_INFORMATIONAL") != "1":
        raise Refusal("capture must set CKV_G1_REF_INFORMATIONAL=1 so in-place drift remains informational")
    if environment.get("CKV_SKIP_K_GATE") not in (None, "", "0"):
        raise Refusal("capture must not set CKV_SKIP_K_GATE")
    if n_suffix != EXPECTED_SUFFIX:
        raise Refusal(f"capture.n_suffix must equal producer-defined {EXPECTED_SUFFIX}")

    grant = require_map(record.get("grant"), "grant")
    require_text(grant.get("grant_id"), "grant.grant_id")
    require_text(grant.get("regions"), "grant.regions")
    grant_start = parse_utc(grant.get("start_utc"), "grant.start_utc")
    grant_end = parse_utc(grant.get("end_utc"), "grant.end_utc")
    started = parse_utc(capture.get("started_at_utc"), "capture.started_at_utc")
    finished = parse_utc(capture.get("finished_at_utc"), "capture.finished_at_utc")
    if not grant_start < grant_end or not grant_start <= started <= finished <= grant_end:
        raise Refusal("capture timestamps are outside the recorded grant window")

    window = require_map(record.get("window"), "window")
    for key in ("window_id", "region_lock_claim"):
        require_text(window.get(key), f"window.{key}")
    window_start = parse_utc(window.get("start_utc"), "window.start_utc")
    window_end = parse_utc(window.get("end_utc"), "window.end_utc")
    if window_start != grant_start or window_end != grant_end:
        raise Refusal("window bounds must match the invocation's recorded grant bounds")
    require_text(record.get("role"), "role")
    finalized_at = parse_utc(record.get("finalized_at_utc"), "finalized_at_utc")
    if not grant_start <= started <= finished <= finalized_at <= grant_end:
        raise Refusal("run and finalization timestamps must remain inside the recorded grant window")
    return record


def read_rows(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Refusal(f"cannot read raw G1 JSONL: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise Refusal(f"raw G1 JSONL has a blank line at {line_number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Refusal(f"raw G1 JSONL line {line_number} is invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise Refusal(f"raw G1 JSONL line {line_number} is not an object")
        rows.append(row)
    if not rows:
        raise Refusal("raw G1 JSONL contains no per-position rows")
    return rows


def validate_capture_rows(rows: list[dict[str, Any]], *, n_chunk: int) -> dict[tuple[int, str, str], list[dict[str, Any]]]:
    expected: dict[tuple[int, str, str], set[int]] = {}
    for delta in EXPECTED_DELTAS:
        for component in COMPONENTS:
            positions = (range(delta, delta + n_chunk) if component in {"k", "v"}
                         else range(delta + n_chunk, delta + n_chunk + EXPECTED_SUFFIX))
            for comparison in COMPARISONS:
                expected[(delta, component, comparison)] = set(positions)
    grouped: dict[tuple[int, str, str], dict[int, dict[str, Any]]] = {
        key: {} for key in expected
    }
    for line_number, row in enumerate(rows, 1):
        delta = row.get("delta")
        component = row.get("component")
        comparison = row.get("comparison")
        if isinstance(delta, bool) or not isinstance(delta, int):
            raise Refusal(f"raw G1 line {line_number} has invalid delta")
        if component not in COMPONENTS or comparison not in COMPARISONS:
            raise Refusal(f"raw G1 line {line_number} has invalid component/comparison")
        key = (delta, component, comparison)
        if row.get("schema") != POSITION_SCHEMA or key not in grouped:
            raise Refusal(f"raw G1 line {line_number} has an unexpected schema/group")
        position = row.get("position")
        if isinstance(position, bool) or not isinstance(position, int) or position not in expected[key]:
            raise Refusal(f"raw G1 line {line_number} has an unexpected position")
        if position in grouped[key]:
            raise Refusal(f"raw G1 has duplicate position {position} in group {key}")
        for field in ("sum_sq_error", "reference_sq_norm"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise Refusal(f"raw G1 line {line_number} has invalid {field}")
        count = row.get("element_count")
        mismatch = row.get("mismatch_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise Refusal(f"raw G1 line {line_number} has invalid element_count")
        if isinstance(mismatch, bool) or not isinstance(mismatch, int) or not 0 <= mismatch <= count:
            raise Refusal(f"raw G1 line {line_number} has invalid mismatch_count")
        grouped[key][position] = row

    complete: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    for key, positions in expected.items():
        actual = set(grouped[key])
        if actual != positions:
            missing = sorted(positions - actual)
            extra = sorted(actual - positions)
            raise Refusal(f"incomplete native G1 group {key}: missing={missing[:8]} extra={extra[:8]}")
        ordered = [grouped[key][pos] for pos in sorted(positions)]
        counts = {row["element_count"] for row in ordered}
        if len(counts) != 1:
            raise Refusal(f"native G1 group {key} has inconsistent per-position element_count")
        complete[key] = ordered
    return complete


def build_measurements(record: dict[str, Any], groups: dict[tuple[int, str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    model = record["model"]
    binary = record["binary"]
    window = record["window"]
    capture = record["capture"]
    n_chunk = capture["n_chunk"]
    served_pin = {
        "role": record["role"],
        "model": f"{model['name']} sha256={model['sha256']}",
        "kernel_ref": f"source={PRODUCER_COMMIT};binary_sha256={binary['sha256']}",
    }
    adapter_window = {
        "window_id": window["window_id"],
        "region_lock_claim": window["region_lock_claim"],
        "start_utc": window["start_utc"],
        "end_utc": window["end_utc"],
    }
    measurements: list[dict[str, Any]] = []
    for delta in EXPECTED_DELTAS:
        for comparison in COMPARISONS:
            for component in COMPONENTS:
                payload = groups[(delta, component, comparison)]
                common = {
                    "source_program": "KPF-62",
                    "subject": f"generated tiny model {model['name']}; n_chunk={n_chunk}; n_suffix={EXPECTED_SUFFIX}",
                    "served_pin": served_pin,
                    "window": adapter_window,
                    "kind": "shift_exactness",
                    "component": component,
                    "comparison": comparison,
                    "delta": delta,
                    "position_rows": payload,
                    "detail": "Generated tiny-model kernel-correctness capture only; no production-quality, serving, performance, or cost claim.",
                }
                measure = {"k": "k_nmse", "v": "v_nmse", "logits": "logits_nmse"}[component]
                measurements.append({**common, "measure": measure})
                if comparison == "inject_vs_seq_add":
                    measurements.append({**common, "measure": "mismatch_fraction"})
    return measurements


def finalize(raw_path: Path, invocation_path: Path) -> Path:
    verify_code_pins()
    raw_path = raw_path.resolve(strict=True)
    invocation_path = invocation_path.resolve(strict=True)
    invocation_bytes = invocation_path.read_bytes()
    record = read_invocation(invocation_path, raw_path)
    rows = read_rows(raw_path)
    groups = validate_capture_rows(rows, n_chunk=record["capture"]["n_chunk"])
    measurements = build_measurements(record, groups)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    final_dir = OUTPUT_ROOT / record["run_id"]
    if final_dir.exists():
        raise Refusal(f"refusing to overwrite existing finalized artifact: {final_dir}")
    final_dir.mkdir()
    try:
        packaged_raw = final_dir / "g1-position.jsonl"
        shutil.copyfile(raw_path, packaged_raw)
        if file_sha256(packaged_raw) != record["capture"]["sha256"]:
            raise Refusal("packaged raw G1 bytes changed during copy")
        packaged_invocation = final_dir / "invocation.json"
        packaged_invocation.write_bytes(invocation_bytes)

        # Import only from the pinned, clean ROOT worktree; this is the existing carrier and grader path.
        sys.path.insert(0, str(ROOT_WT / "scripts/vidya"))
        import claim_tuple  # noqa: PLC0415
        from adapters import chunk_kv  # noqa: PLC0415
        from adapters._native_sidecar import file_sha256 as carrier_file_sha256  # noqa: PLC0415
        if carrier_file_sha256(packaged_raw) != record["capture"]["sha256"]:
            raise Refusal("existing carrier hash check disagrees with raw capture hash")
        sidecar_path = chunk_kv.write_belief_measurements(
            final_dir,
            run_id=record["run_id"],
            producer=f"test-chunk-kv@{PRODUCER_COMMIT}",
            results_path=packaged_raw,
            measurements=measurements,
            protocol_id="unknown",
            emitted_at=record["finalized_at_utc"],
        )
        native = chunk_kv.native_rows(sidecar_path)
        expected_row_count = 27
        if len(native) != expected_row_count:
            raise Refusal(f"existing carrier emitted {len(native)} rows, expected {expected_row_count}")
        grade_counts: dict[str, int] = {}
        for item in native:
            quality, truth, reasons = claim_tuple.grade(chunk_kv.project(item))
            if quality == "Refused":
                raise Refusal("existing shared grader refused a carrier row: " + "; ".join(reasons))
            grade_key = f"{quality}/{truth}"
            grade_counts[grade_key] = grade_counts.get(grade_key, 0) + 1
        manifest = {
            "schema": "epyc.chunk_kv.g1_finalized_artifact.v1",
            "run_id": record["run_id"],
            "scope": "generated tiny-model kernel correctness only",
            "producer_commit": PRODUCER_COMMIT,
            "root_adapter_commit": ROOT_COMMIT,
            "raw_sha256": record["capture"]["sha256"],
            "invocation_sha256": hashlib.sha256(invocation_bytes).hexdigest(),
            "sidecar_sha256": file_sha256(sidecar_path),
            "finalizer_sha256": file_sha256(Path(__file__).resolve()),
            "position_rows": len(rows),
            "carrier_rows": len(native),
            "protocol_id": "unknown",
            "existing_claim_tuple_grade_counts": grade_counts,
        }
        manifest_path = final_dir / "finalization.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        for path in (packaged_raw, packaged_invocation, sidecar_path, manifest_path):
            path.chmod(0o444)
        final_dir.chmod(0o555)
        return final_dir
    except Exception:
        # Preserve the producer's original raw file. Remove only this failed, unaccepted package.
        final_dir.chmod(0o755)
        shutil.rmtree(final_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path, help="new producer schema-v1 raw JSONL")
    parser.add_argument("--invocation", required=True, type=Path, help="actual invocation record JSON")
    args = parser.parse_args()
    try:
        out = finalize(args.raw, args.invocation)
    except (Refusal, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"refuse: {exc}", file=sys.stderr)
        return 2
    print(f"FINALIZED_ARTIFACT={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
