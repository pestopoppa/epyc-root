#!/usr/bin/python3
"""Copy reviewed row inputs into a self-contained packet before publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

PACKET = Path(__file__).resolve().parent
SNAPSHOT = PACKET / "sources/root"
RUNNER = "scripts/benchmark/kernel_promotion_resident_runner.py"
TESTS = (
    "tests/test_kernel_promotion_resident_plan.py",
    "tests/test_kernel_promotion_resident_runner.py",
    "tests/test_kernel_promotion_fresh_replay.py",
    "tests/test_kernel_promotion_evidence.py",
    "tests/test_kernel_promotion_quality_parity.py",
)
DEPS = (
    RUNNER,
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/canonical.py",
    "scripts/vidya/cli.py",
    "scripts/vidya/checkpoint.py",
    "scripts/vidya/fold.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/ledger.py",
    "scripts/vidya/ledger_home.py",
    "scripts/vidya/ingest_sources.py",
    "scripts/vidya/adapters/_llama_bench_protocol.py",
    "scripts/vidya/adapters/kernel_promotion_lifecycle.py",
    "scripts/vidya/adapters/quality_pack_comparison.py",
    "scripts/benchmark/kernel_promotion_evidence.py",
    ".claude/skills/kernel-promotion/scripts/quality_parity.py",
    ".claude/skills/kernel-promotion/scripts/resident_plan.py",
    "scripts/benchmark/m4_cpu_ownership/owned.py",
    "scripts/benchmark/jetlong_cpu/affinity_guard.py",
    "tests/conftest.py",
    "pytest.ini",
    *TESTS,
)
PACKET_FILES = (
    "README.md", "cohorts.json", "plan.json", "prompt.txt", "recipe.json",
    "model.sha256", "model-stat-before.txt", "model-stat-after.txt", "pins.json",
    "job.py", "snapshot.py", "launch.sh", "row.spec.json", "native_check.py", "test_native_packet.py",
    "sources/k35-research.py", "sources/k35-m4-native.py",
    "sources/store-SHA256SUMS", "sources/store-PROVENANCE.md",
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_status(lane):
    """Record index/worktree changes and untracked reviewed paths relative to HEAD."""
    statuses = {}
    for name in DEPS:
        status = subprocess.check_output(
            ["git", "-C", str(lane), "status", "--porcelain=v1", "--untracked-files=all", "--", name],
            text=True,
        )
        statuses[name] = status[:2] if status else "clean"
    return statuses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane", type=Path)
    args = parser.parse_args()
    lane = args.lane.resolve(strict=True)
    if SNAPSHOT.exists() or (PACKET / "SOURCE.sha256").exists():
        parser.error("packet already sealed")
    for name in DEPS:
        if not (lane / name).is_file():
            parser.error(f"required source missing: {name}")
    commit = subprocess.check_output(
        ["git", "-C", str(lane), "rev-parse", "HEAD"], text=True
    ).strip()
    statuses = source_status(lane)
    with tempfile.TemporaryDirectory(dir=PACKET / "sources") as temp:
        staged = Path(temp) / "root"
        for name in DEPS:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lane / name, target)
            if digest(target) != digest(lane / name):
                raise RuntimeError(f"source changed during snapshot: {name}")
        if any(digest(staged / name) != digest(lane / name) for name in DEPS):
            raise RuntimeError("lane changed during snapshot")
        if source_status(lane) != statuses or subprocess.check_output(
            ["git", "-C", str(lane), "rev-parse", "HEAD"], text=True
        ).strip() != commit:
            raise RuntimeError("source status or base commit changed during snapshot")
        source_hashes = {name: digest(staged / name) for name in DEPS}
        staged.rename(SNAPSHOT)
    pins_path = PACKET / "pins.json"
    pins = json.loads(pins_path.read_text())
    pins.update(runner_sha256=digest(SNAPSHOT / RUNNER), source_base_commit=commit,
                source_identity="sha256 of each snapshotted file; base commit is context only",
                reviewed_source_status=statuses, reviewed_source_sha256=source_hashes,
                reviewed_sources_dirty=any(status != "clean" for status in statuses.values()))
    pins_path.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
    names = (*PACKET_FILES, *(f"sources/root/{name}" for name in DEPS))
    manifest = "".join(f"{digest(PACKET / name)}  {name}\n" for name in names)
    (PACKET / "SOURCE.sha256").write_text(manifest)
    print(PACKET / "SOURCE.sha256")


if __name__ == "__main__":
    main()
