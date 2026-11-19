"""Ledger projection of sealed KVU-16a producer records."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from adapters import kvu16a_native as native_capture
from claim_tuple import ProjectionError, to_frames

ADAPTER_ID = "vidya.adapters.kvu16a_projection/v2"
AUTHORITY = native_capture.AUTHORITY


def project(native):
    # Keep the original validator byte-identical: the launch plan pins its file digest.
    claim = native_capture.project(native)
    row = native["row"]
    try:
        body = Path(row["results_path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != row["results_sha256"]:
            raise ValueError("result changed after native validation")
        result = json.loads(body)
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"invalid sealed KVU-16a result: {exc}") from exc

    startup_unknown = result.get("startup_unknown_samples")
    startup_detail = (f" (unknown sample count: {startup_unknown})"
                      if type(startup_unknown) is int and startup_unknown >= 0 else "")
    limits = (f"Healthy samples in one load-only process. Startup coverage UNKNOWN{startup_detail}. "
              "Sampled maximum minus observed target KV; not a lifetime peak or bound.")
    return replace(claim, observation={"outcome_reason": limits})


def emit(sidecar, *, as_of, limit=None):
    return [frame for native in native_capture.native_rows(sidecar)[:limit]
            for frame in to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)]
