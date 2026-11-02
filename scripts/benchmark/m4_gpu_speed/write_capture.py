"""Write-side binding for one M4 GPU native server process.

Enrollment is code-owned and the capture is validated before publication.
This is not a resource-admission or grant-authority mechanism.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vidya" / "adapters"))
from claim_tuple import ProjectionError
from m4_gpu_speed_v2 import Trust, validate_capture
import enrollment


def _dryrun(env):
    value = env.get('FILLER_DRYRUN', '0')
    if value not in ('0', '1'):
        raise ProjectionError('invalid dry-run selector')
    return value == '1'


def grant_directories(env):
    if _dryrun(env):
        if not enrollment.DRYRUN_GRANTS_DIR or not enrollment.DRYRUN_HOLD_DIR:
            raise ProjectionError('dry-run grant authority absent')
        return enrollment.DRYRUN_GRANTS_DIR, enrollment.DRYRUN_HOLD_DIR
    return enrollment.GRANTS_DIR, enrollment.HOLD_DIR


def enrolled():
    dryrun = _dryrun(os.environ)
    root = enrollment.DRYRUN_CAPTURE_ROOT if dryrun else enrollment.CAPTURE_ROOT
    plan = enrollment.DRYRUN_PLAN_PATH if dryrun else enrollment.PLAN_PATH
    digest = enrollment.DRYRUN_PLAN_SHA256 if dryrun else enrollment.PLAN_SHA256
    if not (enrollment.EXECUTION_ENABLED and root and plan and digest and enrollment.SOURCE_SEALS):
        raise ProjectionError("M4 GPU source and plan enrollment absent")
    seals = tuple((Path(p), h) for p, h in enrollment.SOURCE_SEALS)
    own = Path(__file__).resolve().parent
    required = {own / 'launcher.py', own / 'server_np_sweep.py', own / 'write_capture.py',
                own.parents[1] / 'vidya/adapters/m4_gpu_speed_v2.py',
                own.parent / 'm4_cpu_ownership/watch.py', own.parent / 'm4_cpu_ownership/owned.py',
                own.parent / 'm4_cpu_ownership/m4_cgroup_guard.py'}
    if not required.issubset({p for p, _ in seals}):
        raise ProjectionError('source enrollment does not cover actual entry and guardian')
    return Trust(Path(root), Path(plan), digest, seals, qualification_only=dryrun)


def grant_proof(cell, env):
    grant = cell.get("grant")
    if not isinstance(grant, dict) or set(grant) != {"id", "regions", "stopfile"}:
        raise ProjectionError("planned grant identity missing")
    grant_id = grant["id"]
    if not isinstance(grant_id, str) or not grant_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in grant_id):
        raise ProjectionError("unsafe grant identity")
    if env.get("FILLER_ID") != grant_id or env.get("FILLER_NEEDGPU") != "1":
        raise ProjectionError("actual grant identity differs from plan")
    grants_dir, hold_dir = grant_directories(env)
    grant_path = Path(grants_dir) / (grant_id + ".grant")
    try:
        raw = grant_path.read_bytes()
        fields = dict(field.split("=", 1) for field in raw.decode().split())
        if len(raw.decode().split()) != 3 or set(fields) != {"regions", "start", "end"} or fields["regions"] != grant["regions"]:
            raise ValueError("invalid grant fields")
        start = datetime.strptime(fields["start"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp()
        end = datetime.strptime(fields["end"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp()
        deadline = int(env["FILLER_DEADLINE"])
        if int(env["FILLER_END"]) != end or not start <= time.time() < deadline < end:
            raise ValueError("outside grant or deadline")
        stop = Path(env["FILLER_STOPFILE"])
        if not stop.is_absolute() or str(stop) != grant["stopfile"] or stop.exists() or list(Path(hold_dir).glob("HOLD_*")):
            raise ValueError("STOP, HOLD or invalid STOP path")
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        raise ProjectionError(f"actual grant refusal: {exc}") from exc
    return raw


def preflight(key, command, env, model, np, prompt):
    trust = enrolled()
    plan = trust.plan()
    try:
        cell = plan["cells"][key]
    except (KeyError, TypeError) as exc:
        raise ProjectionError("cell absent from enrolled plan") from exc
    # Reject inherited overrides, including those not represented in argv.
    if any(env.get(k) for k in ("LLAMA_ARG_PREFILL_ORDER", "LLAMA_ARG_PREFILL_CONTEND_CAP")):
        raise ProjectionError("hidden M4 environment override")
    if (cell.get("argv") != command or cell.get("model") != str(model) or cell.get("np") != np
            or not isinstance(cell.get("environment"), dict)
            or any(env.get(k) != v for k, v in cell["environment"].items())):
        raise ProjectionError("actual command, environment or model differs from plan")
    required = ("OMP_PROC_BIND", "OMP_PLACES", "OMP_WAIT_POLICY", "OMP_DYNAMIC", "KMP_BLOCKTIME", "LD_LIBRARY_PATH")
    if any(k not in cell["environment"] for k in required):
        raise ProjectionError("execution environment is not fully bound")
    sensitive = ("LD_", "GGML_", "LLAMA_", "HSA_", "HIP_", "ROCR_", "OMP_", "KMP_")
    for name, value in env.items():
        if name.startswith(sensitive) and value and cell['environment'].get(name) != value:
            raise ProjectionError(f"unbound runtime override: {name}")
    # Verify all inputs before launch, including model and runtime libraries.
    for entry in cell.get("files", {}).values():
        with Path(entry["path"]).open("rb") as fh:
            digest = hashlib.file_digest(fh, "sha256").hexdigest()
        if digest != entry["sha256"]:
            raise ProjectionError("preflight file seal mismatch")
    if not {"binary", "model", "prompt"}.issubset(cell.get("files", {})) or not cell.get("ggml"):
        raise ProjectionError("plan lacks required files or libraries")
    if (not command or command[0] != cell['files']['binary']['path']
            or cell['model'] != cell['files']['model']['path'] or str(prompt) != cell['files']['prompt']['path']):
        raise ProjectionError("command inputs differ from sealed files")
    if command.count('-m') != 1 or command.index('-m') + 1 >= len(command) or command[command.index('-m') + 1] != cell['model']:
        raise ProjectionError("command model differs from plan")
    if cell['arm'] == 'BASELINE':
        if any(token == flag or token.startswith(flag + '=') for token in command for flag in ('--prefill-order', '--prefill-contend-cap')):
            raise ProjectionError("baseline unexpectedly enables M4")
    elif cell['arm'] == 'CANDIDATE':
        for flag, value in (('--prefill-order', 'srpf'), ('--prefill-contend-cap', '512')):
            if (any(token.startswith(flag + '=') for token in command) or command.count(flag) != 1
                    or command.index(flag) + 1 >= len(command) or command[command.index(flag) + 1] != value):
                raise ProjectionError("candidate treatment differs from plan")
    else:
        raise ProjectionError("invalid arm")
    for path, digest in cell["ggml"].items():
        with Path(path).open("rb") as fh:
            actual = hashlib.file_digest(fh, "sha256").hexdigest()
        if actual != digest:
            raise ProjectionError("preflight ggml seal mismatch")
    grant_bytes = grant_proof(cell, env)
    return trust, cell, grant_bytes


def write(*, trust, cell, key, row, requests_path, output_path, process, mapped, cleanup, grant_bytes, env):
    if grant_proof(cell, env) != grant_bytes:
        raise ProjectionError("grant changed during execution")
    grant_path = output_path.with_name(output_path.stem + ".grant")
    with grant_path.open("xb") as grant_file:
        grant_file.write(grant_bytes)
        grant_file.flush()
        os.fsync(grant_file.fileno())
    raw = requests_path.read_bytes()
    doc = {name: cell[name] for name in ("role", "arm", "source_commit", "model", "recipe", "argv", "environment", "device", "np", "grant")}
    doc.update({"schema": "epyc.m4.gpu.capture.v2", "plan_cell": key, "plan_sha256": trust.plan_sha256,
                "mapped_ggml": mapped, "process": process, "cleanup": cleanup,
                "request_start_ns": row["request_batch_start_ns"], "request_end_ns": row["request_batch_end_ns"],
                "residency": row["gpu_residency_during"], "requests_path": str(requests_path),
                "requests_sha256": hashlib.sha256(raw).hexdigest(), "aggregate_decode_tps": row["aggregate_decode_tps"],
                "measurement_id": "m4_gpu_" + hashlib.sha256((key + str(requests_path)).encode()).hexdigest()[:24],
                "date": row["timestamp"][:10], "grant_receipt_path": str(grant_path),
                "grant_receipt_sha256": hashlib.sha256(grant_bytes).hexdigest()})
    # Unique attempt directories and exclusive creation preserve prior failures.
    with output_path.open("x", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True, allow_nan=False)
        fh.flush()
        os.fsync(fh.fileno())
    validate_capture(output_path, trust, require_guardian=False)
    return output_path
