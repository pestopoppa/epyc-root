"""Project pinned W66 receipt rows into the serving phase report schema."""

import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

from src.backends.serving_calls import SCHEMA, record_digest
from src.backends.serving_phases import phase_breakdown

SOURCE = "06b010e1361768b7d1d65b83cb4428df28a0d1c3"
CSV = "artifacts/analysis/taskflow-harness-revalidation-20261126/final-20261127/performance/export/REQUESTS.csv"
CSV_SHA = "29febeab9a22a6b582840f067e34963a24cd0c7b2fa4ee7182ee54ea74c77125"
LIGHT = "persistent-w66-light-12/light-01"
SELECT = {
    (LIGHT, "gpu-DS41-W-66-off-common-light-v2", "56"): "slow_prefill",
    (LIGHT, "gpu-DS41-W-66-on-common-light-v2", "28"): "slow_decode",
    ("cache-safe-01", "gpu-DS41-W-66-off-recommended", "117"): "missing_counters",
    ("cache-safe-01", "gpu-DS41-W-66-off-recommended", "108"): "heldout",
}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def record(row, batch):
    wire_path = Path(row["wire_receipt_path"])
    receipts = [json.loads(line) for line in wire_path.read_bytes().splitlines() if line.strip()]
    receipt, = [r for r in receipts if str(r.get("seq")) == row["seq"] and r.get("body_ref") == row["body_ref"]]
    assert hashlib.sha256(canonical(receipt)).hexdigest() == row["receipt_sha256"]
    assert {k: float(row[k]) for k in ("prompt_ms", "predicted_ms", "cache_n", "predicted_n", "prompt_n") if row[k]} == {
        k: receipt[k] for k in ("prompt_ms", "predicted_ms", "cache_n", "predicted_n", "prompt_n") if row[k]
    }
    win = json.loads(row["forwarded_request_window"])
    timings = {k: receipt.get(k) for k in ("prompt_n", "cache_n", "predicted_n", "prompt_ms", "predicted_ms", "draft_n")}
    timings["draft_n_accepted"] = receipt.get("draft_accepted")
    timings["id_slot"] = receipt["slot"]
    trial_id = f"{row['epoch']}/{row['id']}"
    identity = f"{trial_id}/{row['seq']}"
    stream_id = row["receipt_sha256"]
    completed = row["generation_complete"] == "True"
    phase = phase_breakdown(
        {k: v for k, v in timings.items() if k != "id_slot" and v is not None},
        trial_id=trial_id, batch_id=batch, request_id=identity, stream_id=stream_id,
        streamed=row["stream_requested"] == "True", wall_ms=float(row["wall_s"]) * 1000,
        delivered_first_ms=float(row["delivered_ttft_s"]) * 1000 if row["delivered_ttft_s"] else None,
    )
    phase["wall_scope"] = "forward_to_receipt"
    phase["first_delta_scope"] = ("worker_client_arrival" if phase["delivered_first_ms"] is not None else None)
    phase["source_receipt"] = {
        "origin": "verified_historical_wire_receipt_projection", "source_commit": SOURCE,
        "source_csv": CSV, "source_csv_sha256": CSV_SHA, "capture_id": row["epoch"],
        "server_id": row["backend"], "receipt_sha256": row["receipt_sha256"],
        "seq": int(row["seq"]), "unit": row["id"],
        "native_phase_windows": "right_aligned_inferences_excluded",
        "request_window_scope": "forward_to_receipt",
    }
    out = {"schema": SCHEMA, "record_id": stream_id, "ts_start": win["start_epoch_s"],
           "ts_end": win["receipt_epoch_s"], "timings": timings,
           "outcome": "ok" if completed else "failed", "phase_breakdown": phase}
    out["record_sha256"] = record_digest(out)
    return out


def main(root):
    content = subprocess.check_output(["git", "-C", root, "show", f"{SOURCE}:{CSV}"])
    assert hashlib.sha256(content).hexdigest() == CSV_SHA
    identities = set()
    for row in csv.DictReader(io.StringIO(content.decode())):
        key = (row["epoch"], row["id"], row["seq"])
        if key in SELECT:
            assert key not in identities
            identities.add(key)
            print(canonical(record(row, SELECT[key])).decode())
    assert identities == SELECT.keys()
    # A real historical receipt with its versioned phase block omitted presents
    # the pre-change serving schema. The batch label selects this control.
    prefill = record(next(row for row in csv.DictReader(io.StringIO(content.decode())) if
                          (row["epoch"], row["id"], row["seq"]) == (LIGHT, "gpu-DS41-W-66-off-common-light-v2", "56")),
                     "legacy_control")
    phase = prefill.pop("phase_breakdown")
    prefill["record_id"] = hashlib.sha256(b"legacy-control:" + prefill["record_id"].encode()).hexdigest()
    prefill["caller"] = {"batch_id": phase["batch_id"], "request_id": phase["request_id"],
                         "trial_id": phase["trial_id"]}
    prefill["legacy_control_source"] = phase["source_receipt"]
    prefill["timings_source"] = "server"
    prefill["wall_ms"] = phase["client_wall_ms"]
    prefill["record_sha256"] = record_digest(prefill)
    print(canonical(prefill).decode())


if __name__ == "__main__":
    main(sys.argv[1])
