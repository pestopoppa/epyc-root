"""Export existing, closed performance receipts; performs no measurements."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "performance/multi-epoch-v3/snapshot-persistent-final-01/REPORT.json"
OUT = Path(__file__).resolve().parent / "files-v2"


def write_csv(name, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (OUT / name).open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


report = json.loads(SOURCE.read_bytes())
assert not report["read_warnings"] and report["unreceipted_archives"] == 0
OUT.mkdir()
requests, tasks = [], []
for attempt in report["attempts"]:
    prefix = {key: attempt[key] for key in ("epoch", "id", "case", "backend")}
    for request in attempt["requests"]:
        requests.append({**prefix, **request})
    summary = attempt["summary"]
    tasks.append({**prefix, "raw_status": attempt["status"],
                  "acceptance": attempt["acceptance"]["state"],
                  **attempt["task_latency"], **summary,
                  "resource_observation": attempt["resources"],
                  "source_path": attempt["source_path"],
                  "candidate_patch_sha256": attempt["patch_sha256"],
                  "qualification_tags": attempt["qualification_tags"]})

assert len(requests) == report["rollup"]["forwarded_receipts"] == 1061
assert len({r["receipt_sha256"] for r in requests}) == len(requests)
assert len(tasks) == 62 and len(report["epochs"]) == 18
write_csv("REQUESTS.csv", requests)
write_csv("TASKS.csv", tasks)
record = {"source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          "requests": len(requests), "tasks": len(tasks), "epochs": len(report["epochs"]),
          "rollup": report["rollup"], "accepted_artifact_variants": report["accepted_count"],
          "interpretation": [
              "This exports existing closed receipts, not a new experiment or hardware benchmark.",
              "Blank CSV values are unknown, not zero. Native reasoning-only counts are unavailable.",
              "TTFT applies to streaming deltas; response completion is not first-token timing.",
              "Native phase union rates are estimates from right-aligned intervals.",
              "Resources are shared-host observations, not per-task attribution; repeated windows are references.",
              "Standalone source review of superseded intermediate artifacts is not pending dispatch work.",
              "Accepted artifact variants are not unique tasks or an estimated model success rate."]}
(OUT / "SUMMARY.json").write_text(json.dumps(record, indent=2) + "\n")
(OUT / "README.md").write_text(
    "# Closed canary performance export\n\n"
    "REQUESTS.csv contains one row per unique request receipt, including stream/slot, latency, queue, "
    "upstream and delivered streaming TTFT, native prefill/decode, cache and MTP fields, failure details, "
    "role observations and source hashes. TASKS.csv retains task windows, metrics and shared resource summaries. "
    "SUMMARY.json records the aggregate and its scope.\n\n"
    + "\n".join("- " + item for item in record["interpretation"]) + "\n\n"
    "Next: owning main publishes these exports with the task/paid-cost report.\n")
print(json.dumps({"requests": len(requests), "tasks": len(tasks), "epochs": len(report["epochs"]),
                  "unique_receipts": True, "output": str(OUT)}))
