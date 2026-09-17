"""Strict, advisory reader for producer-authored AutoKernel codegen observations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_codegen_summary/v1"
SOURCE_SCHEMA = "epyc.autokernel.codegen_summary.v1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_OID = re.compile(r"[0-9a-f]{40}\Z")
_MIX = ("scalar", "vector", "matrix", "memory", "other")
_CPU_ELF = re.compile(r"bin/libggml-cpu\.so(?:\.[0-9]+)*\Z")
_CPU_SYMBOLS = (
    "ggml_compute_forward_gated_delta_net", "ggml_vec_dot_q4_K_q8_K",
    "ggml_vec_dot_q5_K_q8_K", "ggml_vec_dot_q6_K_q8_K",
)


def _digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"codegen summary is not canonical JSON: {exc}") from exc
    return hashlib.sha256(raw).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ProjectionError(f"{label} must be a SHA-256 digest")
    return value


def _oid(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _OID.fullmatch(value):
        raise ProjectionError(f"{label} must be a full Git OID")
    return value


def _mix(value: Any, label: str) -> dict | None:
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != set(_MIX)
            or any(type(count) is not int or count < 0 for count in value.values())):
        raise ProjectionError(f"{label} has invalid instruction counts")
    return value


def diagnostic_reason(document: dict) -> str | None:
    if "belief_claim_tuple" not in document:
        return "pre-hook codegen sidecar has no producer-authored ClaimTuple"
    return None


def native_rows(document: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "", attestation_present: bool = False) -> list[dict]:
    """Re-derive all local bindings before accepting the producer's tuple."""
    if document.get("schema") != SOURCE_SCHEMA:
        raise ProjectionError("unsupported codegen summary schema")
    if "belief_claim_tuple" not in document:
        return []
    if not isinstance(document.get("belief_claim_tuple"), dict):
        raise ProjectionError("belief_claim_tuple must be an object")
    head = _oid(document.get("champion_head"), "champion_head")
    tree = _oid(document.get("source_tree_oid"), "source_tree_oid")
    attempt = document.get("attempt_identity")
    if not isinstance(attempt, str) or not attempt.strip():
        raise ProjectionError("attempt_identity is required")
    backend = document.get("backend")
    if backend not in {"llama_cpu", "llama_gpu"}:
        raise ProjectionError("codegen backend is unsupported")
    frame = document.get("build_frame")
    if not isinstance(frame, dict) or frame.get("backend") != backend:
        raise ProjectionError("build frame backend mismatch")
    if (not isinstance(frame.get("recipe"), dict)
            or not isinstance(frame.get("build_dir"), str)
            or not frame["build_dir"]):
        raise ProjectionError("build frame recipe or directory is invalid")
    toolchain = document.get("toolchain")
    if not isinstance(toolchain, dict) or frame.get("toolchain") != toolchain:
        raise ProjectionError("build frame toolchain mismatch")
    frame_sha = _sha(document.get("build_frame_sha256"), "build_frame_sha256")
    if _digest(frame) != frame_sha:
        raise ProjectionError("build frame digest mismatch")
    artifact_ref = f"codegen/{head}.{backend}.{frame_sha}.json"
    if document.get("artifact_ref") != artifact_ref:
        raise ProjectionError("codegen artifact identity mismatch")
    if receipt_locator:
        path = Path(receipt_locator.removeprefix("autokernel:"))
        if path.name != PurePosixPath(artifact_ref).name or path.parent.name != "codegen":
            raise ProjectionError("codegen receipt locator mismatch")
    if receipt_sha256:
        _sha(receipt_sha256, "receipt_sha256")
    objects = document.get("objects")
    if not isinstance(objects, list) or len(objects) > 8:
        raise ProjectionError("codegen object list exceeds bound or is invalid")
    object_hashes: list[str] = []
    object_refs: list[dict] = []
    totals = dict.fromkeys(_MIX, 0)
    seen_paths: set[str] = set()
    disassembled_symbols: list[str] = []
    cpu_symbol_summary = backend == "llama_cpu" and "cpu_objdump_stat" in toolchain
    if backend == "llama_cpu":
        stat = toolchain.get("cpu_objdump_stat")
        if stat is not None and (not isinstance(stat, dict)
                or not isinstance(stat.get("path"), str) or not stat["path"]
                or any(type(stat.get(key)) is not int or stat[key] < 0 for key in
                       ("device", "inode", "bytes", "mtime_ns"))):
            raise ProjectionError("CPU disassembler identity is invalid")
        if len(objects) > 1 or (objects and not cpu_symbol_summary):
            raise ProjectionError("CPU codegen requires one bounded library and tool identity")
    for index, row in enumerate(objects):
        if not isinstance(row, dict):
            raise ProjectionError("codegen object row is invalid")
        relative = row.get("relative_path")
        if (not isinstance(relative, str) or not relative
                or PurePosixPath(relative).is_absolute()
                or ".." in PurePosixPath(relative).parts
                or relative in seen_paths or not (
                    bool(_CPU_ELF.fullmatch(relative)) if backend == "llama_cpu"
                    else relative.endswith((".hsaco", ".co")))):
            raise ProjectionError("codegen object path is invalid or repeated")
        seen_paths.add(relative)
        if not isinstance(row.get("disassembly_status"), str):
            raise ProjectionError("codegen object disassembly status is missing")
        if "sha256" in row:
            object_hashes.append(_sha(row["sha256"], f"objects[{index}].sha256"))
            size = row.get("bytes")
            if type(size) is not int or size < 0 or size > 8 * 1024 * 1024:
                raise ProjectionError("codegen object byte count is invalid")
            object_refs.append({"relative_path": relative, "sha256": row["sha256"]})
        elif "bytes" in row or "instruction_mix" in row:
            raise ProjectionError("unhashed code object claims bytes or instructions")
        mix = _mix(row.get("instruction_mix"), f"objects[{index}].instruction_mix")
        if backend == "llama_cpu":
            symbols = row.get("symbols")
            if not isinstance(symbols, list) or len(symbols) > len(_CPU_SYMBOLS):
                raise ProjectionError("CPU symbol list is invalid")
            symbol_totals = dict.fromkeys(_MIX, 0)
            for symbol in symbols:
                if not isinstance(symbol, dict) or set(symbol) != {"name", "instruction_mix"}:
                    raise ProjectionError("CPU symbol row is invalid")
                name = symbol["name"]
                if (name not in _CPU_SYMBOLS or name in disassembled_symbols or
                        (disassembled_symbols and
                         _CPU_SYMBOLS.index(name) <= _CPU_SYMBOLS.index(disassembled_symbols[-1]))):
                    raise ProjectionError("CPU symbol is not allowlisted or is out of order")
                symbol_mix = _mix(symbol["instruction_mix"], "CPU symbol instruction_mix")
                if symbol_mix is None or not any(symbol_mix.values()):
                    raise ProjectionError("CPU symbol lacks parsed instructions")
                disassembled_symbols.append(name)
                for key in _MIX:
                    symbol_totals[key] += symbol_mix[key]
            if mix != (symbol_totals if symbols else None):
                raise ProjectionError("CPU library mix does not match selected symbols")
        elif "symbols" in row:
            raise ProjectionError("GPU code object cannot claim CPU symbols")
        if mix is not None:
            if row["disassembly_status"] != "ok":
                raise ProjectionError("instruction mix lacks successful disassembly")
            for key in _MIX:
                totals[key] += mix[key]
    if frame.get("object_sha256s") != object_hashes:
        raise ProjectionError("build frame object hashes mismatch")
    mix = _mix(document.get("instruction_mix"), "instruction_mix")
    if mix != (totals if any(totals.values()) else None):
        raise ProjectionError("instruction mix does not re-derive")
    status = document.get("status")
    if status != ("partial" if mix is not None else "unavailable"):
        raise ProjectionError("codegen status does not match native evidence")
    if cpu_symbol_summary and status == "partial" and toolchain["cpu_objdump_stat"] is None:
        raise ProjectionError("CPU disassembly lacks identified objdump")
    if (document.get("authority") != "diagnostic_only"
            or document.get("ptx_sass_cubin") != "unavailable: non-CUDA backend"
            or any(document.get(key) is not None for key in
                   ("register_spills", "occupancy", "vectorization"))):
        raise ProjectionError("codegen summary claims unavailable evidence")
    core_sha = _sha(document.get("summary_core_sha256"), "summary_core_sha256")
    core = {key: value for key, value in document.items()
            if key not in {"summary_core_sha256", "belief_claim_tuple"}}
    if _digest(core) != core_sha:
        raise ProjectionError("codegen summary core digest mismatch")
    tuple_row = document["belief_claim_tuple"]
    date = tuple_row.get("date")
    try:
        parsed = datetime.fromisoformat(date)
        if parsed.tzinfo is None:
            raise ValueError("date lacks timezone")
    except (TypeError, ValueError) as exc:
        raise ProjectionError("codegen observation date is invalid") from exc
    available = int(status == "partial")
    expected = {
        "measurement_id": f"ak-codegen:{attempt}:{frame_sha}",
        "metric": "codegen_disassembly_availability", "value": available,
        "unit": "availability indicator", "metric_direction": "higher_better",
        "category": "CANDIDATE",
        "claim": ("Bounded native code-object disassembly was available for this retained build"
                  if available else
                  "Bounded native code-object disassembly was unavailable for this retained build"),
        "date": date, "protocol_id": "", "reps": 1,
        "reps_basis": "one retained build; not benchmark repetitions",
        "attestation_locator": artifact_ref, "attestation_sha256": "",
        "attestation_verified": None, "source_class": "measurement",
        "extra": {
            "authority": "diagnostic_only", "not_throughput_or_correctness": True,
            "not_occupancy_evidence": True, "attempt_identity": attempt,
            "retained_source_commit": head, "retained_source_tree_oid": tree,
            "backend": backend, "toolchain": toolchain,
            "build_frame_sha256": frame_sha, "summary_core_sha256": core_sha,
            "code_objects": object_refs, "instruction_mix": mix,
            "unavailable_fields": ["register_spills", "occupancy", "vectorization"],
            "ptx_sass_cubin": document["ptx_sass_cubin"],
        },
    }
    if cpu_symbol_summary:
        expected["extra"]["disassembled_symbols"] = disassembled_symbols
    if tuple_row != expected:
        raise ProjectionError("producer ClaimTuple does not bind codegen summary")
    return [{"document": document, "tuple": tuple_row, "receipt_locator": receipt_locator,
             "receipt_sha256": receipt_sha256}]


@register("autokernel-codegen-summary-measurement")
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("document"), dict):
        raise ProjectionError("codegen native row lacks original sidecar")
    checked = native_rows(native["document"],
                          receipt_locator=native.get("receipt_locator", ""),
                          receipt_sha256=native.get("receipt_sha256", ""))
    if not checked or native.get("tuple") != checked[0]["tuple"]:
        raise ProjectionError("codegen native row differs from original sidecar")
    return ClaimTuple(**native["tuple"])
