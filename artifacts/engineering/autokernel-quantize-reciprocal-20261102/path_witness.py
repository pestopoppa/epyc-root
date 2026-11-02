#!/usr/bin/env python3
"""Diagnostic dispatch coverage only; never a benchmark/performance receipt.

Consumes native rocprofv3 CSV. Source/build/PID attribution must be supplied by
the capture owner separately; the ROCm 6.2 CSV has no PID column.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

TARGET = re.compile(r"^(?:void\s+)?quantize_q8_1\s*\(")
ONE_D = re.compile(r"^(?:void\s+)?quantize_q8_1_1d\s*\(")
REQUIRED = {"Kind", "Kernel_Name", "Start_Timestamp", "End_Timestamp",
            "Grid_Size_Y", "Grid_Size_Z"}


def inspect_trace(path, start_ns, end_ns):
    if not 0 <= start_ns < end_ns:
        raise ValueError("window must be increasing nonnegative trace-clock ns")
    raw = Path(path).read_bytes()
    reader = csv.DictReader(raw.decode().splitlines())
    if not REQUIRED.issubset(reader.fieldnames or ()):
        raise ValueError("missing native dispatch CSV columns")
    targets, one_d = [], 0
    for row in reader:
        if row["Kind"] != "KERNEL_DISPATCH":
            continue
        name = row["Kernel_Name"]
        if not (TARGET.match(name) or ONE_D.match(name)):
            continue
        start, end = int(row["Start_Timestamp"]), int(row["End_Timestamp"])
        if start >= end:
            raise ValueError("invalid quantize dispatch interval")
        # Full containment avoids counting warmup/edge dispatches.
        if not (start_ns <= start and end <= end_ns):
            continue
        if ONE_D.match(name):
            one_d += 1
            continue
        gy, gz = int(row["Grid_Size_Y"]), int(row["Grid_Size_Z"])
        # Wrapper maps grid.y=ne1, grid.z=ne2*ne3. Dimensions are positive.
        if gy < 1 or gz < 1 or gy * gz <= 1:
            raise ValueError("target symbol contradicts multidimensional launch grid")
        targets.append({"name": name, "start_ns": start, "end_ns": end,
                        "grid_y": gy, "grid_z": gz})
    return {"schema": "autokernel.quantize-path-witness.v1",
            "evidence_class": "diagnostic_dispatch_coverage_only",
            "performance_evidence_eligible": False,
            "source_build_pid_attribution": "requires_separate_capture_manifest",
            "trace_sha256": hashlib.sha256(raw).hexdigest(),
            "window_trace_clock_ns": [start_ns, end_ns],
            "target_dispatch_count": len(targets), "one_d_dispatch_count": one_d,
            "dispatch_coverage": "observed" if targets else "not_observed",
            "target_dispatches": targets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--start-ns", type=int, required=True)
    parser.add_argument("--end-ns", type=int, required=True)
    args = parser.parse_args()
    try:
        result = inspect_trace(args.trace, args.start_ns, args.end_ns)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"invalid witness: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["target_dispatch_count"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
