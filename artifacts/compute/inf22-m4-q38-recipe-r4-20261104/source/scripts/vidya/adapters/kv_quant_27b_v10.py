"""Read producer-authored v10 MI210 KV-quant sweep measurements.

One invalid row voids its entire sidecar. The adapter projects the native capture;
the shared measurement ladder alone assigns its grade.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import functools
import math
import os
import re
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters._argv_scope import flag, scope_from_argv  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

_HEX64 = re.compile(r"[0-9a-f]{64}")

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


def _finite_stat_median(value: Any) -> float | None:
    """Normalize a finite scalar or stats median without rewriting native evidence."""
    median = value.get("median") if isinstance(value, dict) else value
    if isinstance(median, bool) or not isinstance(median, (int, float)):
        return None
    try:
        normalized = float(median)
    except OverflowError:
        return None
    return normalized if math.isfinite(normalized) else None


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
    prefill_median = _finite_stat_median(arm.get("prefill_tokens_measured"))
    if arm.get("prefill_depth_target_tokens") not in {2048, 32768} or prefill_median is None:
        raise ProjectionError("KV-quant prefill depth evidence missing")
    k_median = _finite_stat_median(extra.get("kv_buffer_k_mib"))
    v_median = _finite_stat_median(extra.get("kv_buffer_v_mib"))
    if k_median is None or v_median is None:
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
    extra = row["extra"]
    scope = {"context_tokens": extra["arm"]["context"],
             "kernel": extra["kernel"], "run_id": row["run_id"]}
    # The reviewed producer stores these declarations, but old/minimal rows may
    # omit them. Never infer model quant, backend, or expected keys from a pin.
    for native_key, key in (("model", "model_file"), ("recipe", "device")):
        declaration = extra.get(native_key)
        if declaration is not None:
            if not isinstance(declaration, dict):
                raise ProjectionError(f"KV-quant {native_key} declaration must be a mapping")
            value_key = "path" if native_key == "model" else "device"
            if value_key in declaration:
                scope[key] = declaration[value_key]
    if "run_expected_keys" in row:
        scope["run_expected_keys"] = row["run_expected_keys"]
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"],
        value=row["value"], date=row["date"], category=row["category"],
        claim=(f"{row['claim']} K buffer {_finite_stat_median(row['extra']['kv_buffer_k_mib'])} MiB; "
               f"V buffer {_finite_stat_median(row['extra']['kv_buffer_v_mib'])} MiB; "
               "mixed K/V structurally absent; prefill depth is part of the key."),
        metric_direction=row["metric_direction"],
        protocol_id=row["protocol_id"], reps=row["reps"],
        reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["scored_sha256"],
        attestation_locator=(f"{row['extra']['locator']}|{row['scored_path']}"
                             f"#sha256={row['scored_sha256']}"),
        attestation_present=present, attestation_verified=True if verified else None,
        source_kind=SOURCE_KIND, applicability=scope,
        extra={"schema": row["schema"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "row_sha256": row["row_sha256"],
               "sidecar_path": native.get("sidecar_path", ""),
               "scored_path": row["scored_path"], **row["extra"]},
    )


# ---------------------------------------------------------------------------------------------
# Retrofit reader (belief redesign §5.1, Phase 2): the 2026-09-22 sweep predates the capture hook,
# so its run directories hold `identities.json` + `runs/<cell>_rep<N>/result.json` and no
# `belief_measurements.jsonl`. Layout: <sweep>/run-20260922{,b,c}/run-<ts>/ .
#
# STRICT: only `status: ok` cells project. A cell is refused (ProjectionError, whole unit) unless
#  * `identities.json` says `valid`/`reason ok`, the binary digest matches `expected_binary_sha256`, the
#    source head equals the expected head, and the harness snapshot digest equals the file on disk and
#    the pinned producer;
#  * the binary, every inspected ggml library and the harness snapshot are RE-HASHED when present on
#    disk and must equal the recorded digests (absent => recorded as unverified, never as verified);
#    the 29 GB model is size-checked (full re-hash with VIDYA_REHASH_MODEL=1);
#  * `server_argv.json` names the identity's binary and model, `-fa on`, equal K/V types that match the
#    cell name;
#  * decode/prompt t/s, token and ms totals re-derive from the per-request rows; every request
#    finished, passed the semantic and sanity validators; residency proves full offload and the
#    requested K/V types.
# Runs a and b (every cell `status: error`) are declined: an errored cell has no measurement.
# `protocol_id` is EMPTY (retrofit => Judged/Located); N=1 (one fresh server per cell, three requests
# aggregated into one rate). PROJECTION ONLY: `claim_tuple.grade()` decides.
# ---------------------------------------------------------------------------------------------

RETROFIT_KIND = "kv-quant-27b-v10-retrofit"
RETROFIT_SCHEMA = "epyc.kv_quant_27b_v10_retrofit.v1"
RETROFIT_METRICS = (("gpu_decode_tps", "decode_tps", "decode_ms", "completion_tokens"),
                    ("gpu_prefill_tps", "prompt_tps", "prompt_ms", "prompt_tokens"))
_RETRO_CELLS = {"A_f16_kv": "f16", "B_q8_0_kv": "q8_0", "C_q4_0_kv": "q4_0"}
_RETRO_DEPTHS = ("d2k", "d32k")
_CELL_DIR = re.compile(r"^(?P<cell>[A-Z]_[a-z0-9_]+_kv)_(?P<depth>d\d+k)_rep(?P<rep>\d+)$")
_RUN_TS = re.compile(r"run-(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")


def _jload(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"KV-quant retrofit file unreadable: {path.name}: {exc}") from exc


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _num(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProjectionError("KV-quant retrofit numeric field malformed")
    return float(value)


@functools.lru_cache(maxsize=16)
def _run_identity(run_dir: str) -> dict:
    """Verify one run's identities (re-hashing what is on disk) and return what the projection needs."""
    run = Path(run_dir)
    ident = _jload(run / "identities.json")
    if ident.get("valid") is not True or ident.get("reason") != "ok" or ident.get("harness_valid") is not True:
        raise ProjectionError("KV-quant retrofit identities.json is not valid/ok")
    binary = ident.get("binary") or {}
    expected = binary.get("expected_binary_sha256")
    if not _HEX64.fullmatch(str(expected or "")) or binary.get("binary_sha256") != expected \
            or binary.get("binary_sha256_matches") is not True:
        raise ProjectionError("KV-quant retrofit binary digest does not match its expected digest")
    source = ident.get("source") or {}
    if source.get("head_matches") is not True or source.get("branch_matches") is not True \
            or source.get("clean") is not True or source.get("head") != source.get("expected_head"):
        raise ProjectionError("KV-quant retrofit source tree identity is not the clean expected head")
    harness = ident.get("harness") or {}
    if harness.get("sha256") != PRODUCER_SHA256 \
            or (ident.get("harness_snapshot") or {}).get("sha256") != PRODUCER_SHA256:
        raise ProjectionError("KV-quant retrofit harness digest is not the reviewed producer digest")
    snapshot = run / "harness_source.py"
    if not snapshot.is_file() or _sha256(snapshot) != PRODUCER_SHA256:
        raise ProjectionError("KV-quant retrofit harness_source.py does not re-hash to the pinned digest")
    verified: list[str] = ["harness_source.py"]
    unverified: list[str] = []
    path = Path(str(binary.get("binary") or ""))
    artifact = binary.get("artifact") or {}
    if path.is_file():
        if _sha256(path) != expected:
            raise ProjectionError("KV-quant retrofit binary on disk re-hashes to a different digest")
        verified.append("binary")
    else:
        unverified.append("binary")
    libs = (binary.get("linkage_receipt") or {}).get("inspected_libraries")
    if not isinstance(libs, list) or not libs:
        raise ProjectionError("KV-quant retrofit linkage receipt lists no ggml libraries")
    for lib in libs:
        lib_path = Path(str(lib.get("path") or ""))
        digest = str(lib.get("sha256") or "")
        if not _HEX64.fullmatch(digest):
            raise ProjectionError("KV-quant retrofit library digest malformed")
        if lib_path.is_file():
            if _sha256(lib_path) != digest:
                raise ProjectionError(f"KV-quant retrofit library {lib_path.name} re-hashes differently")
        else:
            unverified.append(lib_path.name)
    if libs and all(Path(str(lib.get("path") or "")).is_file() for lib in libs):
        verified.append("ggml_libraries")
    model = ident.get("target_model") or {}
    model_sha = str(model.get("sha256") or "")
    if not _HEX64.fullmatch(model_sha) or not isinstance(model.get("bytes"), int):
        raise ProjectionError("KV-quant retrofit target model identity malformed")
    model_path = Path(str(model.get("path") or ""))
    if model_path.is_file():
        if model_path.stat().st_size != model["bytes"]:
            raise ProjectionError("KV-quant retrofit model size differs from the recorded identity")
        if os.environ.get("VIDYA_REHASH_MODEL") == "1":
            if _sha256(model_path) != model_sha:
                raise ProjectionError("KV-quant retrofit model re-hashes to a different digest")
            verified.append("model")
        else:
            verified.append("model_size")
    else:
        unverified.append("model")
    plan = _jload(run / "plan.json")
    if (plan.get("target_model") or {}).get("sha256") != model_sha:
        raise ProjectionError("KV-quant retrofit plan.json and identities.json name different models")
    return {"binary_path": str(path), "binary_sha256": expected, "model_path": str(model_path),
            "model_sha256": model_sha, "head": source["head"], "verified": verified,
            "unverified": sorted(set(unverified)), "ident_sha256": _sha256(run / "identities.json")}


def _retro_date(run: Path) -> str:
    match = _RUN_TS.search(run.name)
    if match is None:
        raise ProjectionError("KV-quant retrofit run directory name carries no UTC timestamp")
    y, mo, d, h, mi, s = match.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}Z"


def _retro_cell(run: Path, cell_dir: Path, ident: dict) -> dict:
    result_path = cell_dir / "result.json"
    match = _CELL_DIR.fullmatch(cell_dir.name)
    if match is None or match["cell"] not in _RETRO_CELLS or match["depth"] not in _RETRO_DEPTHS:
        raise ProjectionError(f"KV-quant retrofit cell directory {cell_dir.name!r} is not a declared cell")
    res = _jload(result_path)
    if res.get("cell") != match["cell"] or res.get("depth") != match["depth"] \
            or res.get("rep") != int(match["rep"]):
        raise ProjectionError("KV-quant retrofit result.json cell/depth/rep disagree with its directory")
    ktype = _RETRO_CELLS[match["cell"]]
    argv = _jload(cell_dir / "server_argv.json")
    if not isinstance(argv, list) or not all(isinstance(t, str) for t in argv):
        raise ProjectionError("KV-quant retrofit server_argv.json malformed")
    if argv[:1] != [ident["binary_path"]] or flag(argv, "-m") != ident["model_path"] \
            or flag(argv, "-fa") != "on" or flag(argv, "-ngl") != "all" \
            or not (flag(argv, "-dev") or "").startswith("ROCm"):
        raise ProjectionError("KV-quant retrofit argv does not name the identity's binary/model, -fa on, full GPU")
    if flag(argv, "--cache-type-k") != ktype or flag(argv, "--cache-type-v") != ktype:
        raise ProjectionError("KV-quant retrofit argv KV types differ from the cell")
    records = res.get("records")
    if not isinstance(records, list) or not records:
        raise ProjectionError("KV-quant retrofit cell has no request records")
    for rec in records:
        if rec.get("finish_reason") != "stop" or rec.get("depth") != match["depth"] \
                or (rec.get("semantic_validation") or {}).get("passed") is not True \
                or (rec.get("response_sanity") or {}).get("passed") is not True:
            raise ProjectionError("KV-quant retrofit request did not finish and validate")
    rez = res.get("residency") or {}
    if rez.get("passed") is not True or rez.get("full_target_offload") is not True \
            or rez.get("kv_types_and_positive_buffers") is not True \
            or rez.get("requested_kv") != {"k": ktype, "v": ktype}:
        raise ProjectionError("KV-quant retrofit residency proof absent or contradicts the cell")
    if res.get("post_cleanup_clean") is not True:
        raise ProjectionError("KV-quant retrofit cell post-cleanup was not clean")
    values: dict[str, float] = {}
    for metric, rate_key, ms_key, tok_key in RETROFIT_METRICS:
        tokens = sum(_num(r[tok_key]) for r in records)
        millis = sum(_num(r[ms_key]) for r in records)
        if millis <= 0 or not _close(tokens, _num(res[tok_key])) or not _close(millis, _num(res[ms_key])):
            raise ProjectionError(f"KV-quant retrofit {tok_key}/{ms_key} totals do not re-derive")
        rate = tokens / millis * 1000.0
        if not _close(rate, _num(res[rate_key])):
            raise ProjectionError(f"KV-quant retrofit {rate_key} does not re-derive from the request rows")
        values[metric] = rate
    return {"cell": match["cell"], "depth": match["depth"], "rep": int(match["rep"]), "kv_type": ktype,
            "values": values, "argv": argv, "result": res, "result_path": result_path,
            "result_sha256": _sha256(result_path),
            "prompt_tokens_per_request": [int(r["prompt_tokens"]) for r in records]}


def retrofit_rows(run_dir: str | Path) -> list[dict]:
    """One native row per (ok cell x metric) of a run directory; ``[]`` for a foreign or all-error run."""
    run = Path(run_dir)
    if run.is_file():
        run = run.parent
    if not (run / "identities.json").is_file() or not (run / "runs").is_dir():
        return []
    cells = sorted(p for p in (run / "runs").iterdir() if p.is_dir() and (p / "result.json").is_file())
    ok = [p for p in cells if _jload(p / "result.json").get("status") == "ok"]
    if not ok:
        return []   # errored cells carry no measurement; runs a and b land here
    ident = _run_identity(str(run.resolve()))
    rows: list[dict] = []
    for cell_dir in ok:
        cell = _retro_cell(run, cell_dir, ident)
        for metric, *_ in RETROFIT_METRICS:
            rows.append({"schema": RETROFIT_SCHEMA, "run_dir": str(run), "cell_dir": str(cell_dir),
                         "metric": metric})
    return rows


def _anchor(run: Path, cell: dict, metric: str) -> float | None:
    """The f16 same-depth value of this run, when that cell is ok (a derived reference, not a new rule)."""
    if cell["kv_type"] == "f16":
        return None
    sibling = run / "runs" / f"A_f16_kv_{cell['depth']}_rep{cell['rep']}"
    if not (sibling / "result.json").is_file():
        return None
    ref = _jload(sibling / "result.json")
    if ref.get("status") != "ok":
        return None
    ident = _run_identity(str(run.resolve()))
    return _retro_cell(run, sibling, ident)["values"][metric]


@register(RETROFIT_KIND)
def project_retrofit(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native.get("schema") != RETROFIT_SCHEMA:
        raise ProjectionError("KV-quant retrofit native row missing")
    run, cell_dir, metric = Path(native["run_dir"]), Path(native["cell_dir"]), native["metric"]
    if metric not in {m[0] for m in RETROFIT_METRICS}:
        raise ProjectionError("KV-quant retrofit metric unknown")
    ident = _run_identity(str(run.resolve()))
    cell = _retro_cell(run, cell_dir, ident)
    value = cell["values"][metric]
    anchor = _anchor(run, cell, metric)
    argv = cell["argv"]
    scope = scope_from_argv(argv, binary=ident["binary_path"], binary_sha256=ident["binary_sha256"],
                            family="kv_profile", varied=["cache_type_k", "cache_type_v"])
    if not scope:
        raise ProjectionError("KV-quant retrofit argv yields no scope")
    scope["backend"] = "gpu"          # -dev ROCm0 -ngl all, proven by residency.full_target_offload
    scope["model_sha256"] = ident["model_sha256"]
    scope["run_id"] = run.name
    # Prefill depth is part of the claim's key (cautions (e)); the loop reader renders neither field yet, the
    # claim text and measurement id carry it too.
    scope["shape"] = f"prefill_depth={cell['depth']}"
    scope["config_key"] = f"kv={cell['kv_type']}/{cell['kv_type']};fa=on;depth={cell['depth']}"
    obs: dict[str, Any] = {"retrofit": True}
    if anchor is not None and anchor > 0:
        obs["anchor_value"] = anchor
        obs["effect_rel"] = value / anchor - 1.0
    kind = "decode" if metric == "gpu_decode_tps" else "prefill"
    per_req = cell["prompt_tokens_per_request"]
    claim = (f"MI210 Qwen3.8-27B-Q8_0 at production-consolidated-v10 ({scope.get('build_sha', '')}): "
             f"{kind} {value:.2f} t/s with K/V cache {cell['kv_type']}/{cell['kv_type']}, -fa on, "
             f"depth {cell['depth']} (prompt {min(per_req)}-{max(per_req)} tokens/request); N=1 fresh "
             f"server, {len(per_req)} requests aggregated; K {cell['result']['kv_k_mib']} MiB, "
             f"V {cell['result']['kv_v_mib']} MiB; bench instrument, bursty, not a serving rate; "
             "retrofit of the pre-hook run")
    rel = cell_dir.relative_to(run.parent.parent) if run.parent.parent in cell_dir.parents else cell_dir
    locator = f"kvq-retrofit:{run.name}:{cell['cell']}:{cell['depth']}:{metric}|{rel}/result.json"
    return ClaimTuple(
        measurement_id=f"kvq-retrofit:v1:{run.name}:{cell['cell']}:{cell['depth']}:rep{cell['rep']}:{metric}",
        metric=metric, value=value, unit="tokens/s", date=_retro_date(run),
        category="BASELINE" if cell["kv_type"] == "f16" else "CANDIDATE", claim=claim,
        metric_direction="higher_better", protocol_id="", reps=1,
        reps_basis="scored:1 fresh-server replicate (N=1; the cell's requests are one aggregate rate)",
        attestation_sha256=cell["result_sha256"], attestation_locator=locator,
        attestation_present=True, attestation_verified=True, source_kind=RETROFIT_KIND,
        applicability=scope, observation=obs,
        extra={"schema": RETROFIT_SCHEMA, "run_dir": str(run), "cell": cell["cell"], "depth": cell["depth"],
               "rep": cell["rep"], "kv_type": cell["kv_type"], "kv_buffer_k_mib": cell["result"]["kv_k_mib"],
               "kv_buffer_v_mib": cell["result"]["kv_v_mib"], "prompt_tokens_per_request": per_req,
               "flash_attention": "on", "source_head": ident["head"], "identities_sha256": ident["ident_sha256"],
               "rehashed": ident["verified"], "not_rehashed": ident["unverified"],
               "instrument_class": "bench", "duty_cycle": "bursty", "retrofit": True})
