#!/usr/bin/python3
"""Validate the selected historical descriptions against the original raw logs."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SEEDS = range(2026102600, 2026102632)
OPS = {"NORM": (30, 10), "SUM": (8, 1), "SUM_ROWS": (10, 6)}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def case_plan(name, role):
    by_op = {op: set() for op in OPS}
    for line in (HERE / name).read_text().splitlines():
        op, status, description = line.split("\t")
        require(op in by_op and status == role and description not in by_op[op],
                f"invalid {name} row: {line!r}")
        by_op[op].add(description)
    return by_op


def manifest(path):
    return dict((name.removeprefix("./"), digest)
                for digest, name in (line.split("  ", 1) for line in path.read_text().splitlines()))


def derive(archive, revision):
    targets = case_plan("case-plan.tsv", "UNSUPPORTED")
    controls = case_plan("control-plan.tsv", "PASS")
    archive_manifest = archive / "SHA256SUMS"
    native_manifest = archive / "NATIVE-EVIDENCE.sha256"
    copied_pins = manifest(archive_manifest)
    native_pins = manifest(native_manifest)
    inputs = {}
    historical_row = "ni-gpu-sampler-elementwise-20261026-v3"
    for seed in SEEDS:
        for op, (observed_count, target_count) in OPS.items():
            path = archive / "logs" / f"{op}-{seed}.log"
            key = str(path.relative_to(archive))
            digest = sha(path)
            require(copied_pins[key] == native_pins[path.name] == digest, f"original raw log pin mismatch: {key}")
            text = re.sub(r"\x1b\[[0-9;]*m", "", path.read_text())
            first, *_ = text.splitlines()
            require(first.startswith("ARGV "), f"original argv missing: {key}")
            argv = json.loads(first[5:])
            require(argv[1:6] == ["test", "-b", "ROCm0", "-o", op]
                    and argv[-2:] == ["--suite-seed", str(seed)], f"original argv mismatch: {key}")
            backend = re.findall(
                r"^Backend [0-9]+/[0-9]+: ROCm0\n  Device description: AMD Instinct MI210\n(.*?)"
                r"^  Backend ROCm0: OK *$", text, re.M | re.S,
            )
            require(len(backend) == 1, f"original ROCm0 terminal missing: {key}")
            pattern = rf"^  {op}\((.*)\): (.*)$"
            native = re.findall(pattern, backend[0], re.M)
            require(native == re.findall(pattern, text, re.M) and len(native) == len(dict(native)) == observed_count,
                    f"original descriptions are ambiguous: {key}")
            unsupported = {name for name, status in native if status.strip() == "not supported [ROCm0]"}
            passed = {name for name, status in native if status.strip() == "OK"}
            require(len(unsupported) == target_count and len(unsupported) + len(passed) == observed_count
                    and unsupported == targets[op] and len(controls[op]) == 1 and controls[op] <= passed,
                    f"original target or control partition differs: {key}")
            inputs[key] = digest
    return {
        "archive_path": str(archive), "archive_git_revision": revision, "archive_row_id": historical_row,
        "historical_candidate_commit": "c463f601bd39d0e313b744c214b8c22f9455bcd3",
        "archive_manifest_sha256": sha(archive_manifest), "native_manifest_sha256": sha(native_manifest),
        "original_log_sha256": inputs, "seeds": list(SEEDS),
        "target_cases_per_seed": {op: target_count for op, (_, target_count) in OPS.items()},
        "control_cases_per_seed": {op: 1 for op in OPS},
        "target_plan_sha256": sha(HERE / "case-plan.tsv"), "control_plan_sha256": sha(HERE / "control-plan.tsv"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("revision")
    args = parser.parse_args()
    print(json.dumps(derive(args.archive, args.revision), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
