"""Shared capture contract for one original R18-E GPU request."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

try:
    from . import gpu_counter
except ImportError:
    import gpu_counter

HERE = Path(__file__).resolve().parent
ROW = "vb-ak-r18-gfx-observation-20261118"
SCHEMA = "epyc.autokernel.gfx_observation.v1"
RESEARCH = "26d89b6ea20f21675d9cc4bc07a8db11ec42199e"
BUILD = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
IMAGE = Path("/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin")
SERVER = IMAGE / "llama-server"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf")
DRAFTER = MODEL.with_name("Qwen3.8-27B-DFlash2-Q8_0.gguf")
MODEL_SHA = "a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348"
DRAFTER_SHA = "7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751"
SERVER_SHA = "2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b"
HIP_SHA = "f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079"
HIP = IMAGE / "libggml-hip.so.0.16.0"
LIBRARY = Path("/opt/rocm/lib/librocm_smi64.so.7")
LIBRARY_REAL = Path("/opt/rocm/lib/librocm_smi64.so.7.3.60200")
COLLECTOR_SHA = "1f34fb48243a26f8e51d0f9c9c361f295a406d5b31532ce29e6270e68d760b07"
LINKAGE_SHA = "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33"
READER_REVISION = "4c799f872115ec712362fdc6e104b7d4731c3b80"
SOURCE_FILES = ("reader-manifest.json", "gpu_counter.py", "native.py", "observation.py", "reader.py",
                "verify_ggml_linkage.sh", "weights.sha256", "weights.stat.before", "weights.stat.after")
LIBRARY_SHA = "26d634f892e301aabb109105729037b64d63bcbe91a5ad6ea9a0ef774428eeb7"
GPU_LOCK = Path("/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock")
PORT = 19831
METRIC = "approx_gfx_activity_weighted_seconds"
COMPLETENESS = "valid_gfx_request_boundary_samples"
PHASES = ["claim_start", "request:start", "request:end", "claim_end"]
REQUEST = {"prompt": "Count from one to forty, writing each integer followed by a comma: 1,",
           "n_predict": 32, "temperature": 0, "seed": 42, "cache_prompt": False,
           "ignore_eos": True, "stream": False}
LIMIT = ("Device-wide GFX activity-weighted seconds over the two recorded request boundary "
         "reads. Per-process attribution, full-claim utilization and binary busy time are UNKNOWN. "
         "Counter resets between reads cannot be excluded.")
TARGET = {"model_file": MODEL.name, "quant": "Q8_0", "backend": "gpu", "device": "gfx90a", "model_sha256": MODEL_SHA}


def now():
    return datetime.now(timezone.utc).isoformat()


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def seal(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def argv():
    return [str(SERVER), "-m", str(MODEL), "-md", str(DRAFTER), "--spec-type", "draft-dflash",
            "--spec-draft-n-max", "7", "--host", "127.0.0.1", "--port", str(PORT),
            "-np", "1", "-c", "4096", "-t", "4", "-b", "512", "-ub", "512",
            "--flash-attn", "on", "-ctk", "q8_0", "-ctv", "q8_0", "-ngl", "all",
            "-ngld", "99", "--device", "ROCm0", "--device-draft", "ROCm0"]


def counter_window(trace, start, end):
    require(trace["schema"] == gpu_counter.SCHEMA and trace["claim_device_id"] == "mi210_0",
            "unexpected collector schema or device")
    require(trace["closed"] is True and trace["full_claim_coverage"] is None,
            "partial or unrecognized collector lifecycle")
    samples, errors = trace["samples"], trace["errors"]
    require(not errors and [sample["phase"] for sample in samples] == PHASES,
            f"collector errors or missing/contradictory phases: {errors}")
    reduction = gpu_counter.reduce_trace(samples, errors)
    require(reduction["unavailable_reason"] is None, reduction["unavailable_reason"])
    require(all(trace[key] == val for key, val in reduction.items()), "trace reduction mismatch")
    require(trace["claim_acquired_observed_ns"] <= samples[0]["host_before_ns"]
            <= samples[1]["host_before_ns"] <= samples[1]["host_after_ns"]
            <= start < end <= samples[2]["host_before_ns"]
            <= samples[2]["host_after_ns"] <= samples[3]["host_before_ns"]
            <= samples[3]["host_after_ns"] <= trace["claim_release_observed_ns"],
            "counter, claim and request windows fail to nest")
    identity = trace["identity"]
    require(identity["bdf"] == "0000:43:00.0" and identity["library"] == str(LIBRARY_REAL)
            and identity["library_sha256"] == LIBRARY_SHA
            and identity["counter_type"] == "RSMI_COARSE_GRAIN_GFX_ACTIVITY"
            and type(identity["index"]) is int and identity["index"] >= 0
            and len(identity["library_file_identity"]) == 4
            and all(type(val) is int and val > 0 for val in identity["library_file_identity"])
            and all(type(identity["version"][key]) is int and identity["version"][key] >= 0
                    for key in ("major", "minor", "patch")), "counter library or device identity mismatch")
    request = gpu_counter.reduce_trace(samples[1:3], errors)
    require(request["unavailable_reason"] is None
            and request[METRIC] >= 0, "fixed request has no eligible GFX observation")
    return request


def native_measurement(record, raw_trace, reduction):
    """Replay the declaration authored by the writer before the capture seal."""
    return {"measurement_id": "akgfx:" + record["run_id"].removeprefix("native-"),
            "metric": COMPLETENESS, "value": 2, "unit": "samples",
            "metric_direction": "higher_better", "category": "CANDIDATE",
            "reps": 1, "reps_basis": "scored", "protocol_id": "",
            "date": record["ended_at"][:10], "applicability": record["target"],
            "attestation_locator": "gfx-counter.json",
            "attestation_sha256": raw_trace,
            "producer_manifest_sha256": record["source_manifest"]["sha256"],
            "observed_window": reduction["observed_window"], METRIC: reduction[METRIC],
            "limitations": LIMIT}
