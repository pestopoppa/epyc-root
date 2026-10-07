"""Hosted CPU controls invoke actual source-built C++ programs, never a copied RNG."""
from pathlib import Path
import os
import re
import subprocess
import struct


def _run_actual_initializer(label: str):
    root = Path(os.environ["RVP_NATIVE_OUTPUT_ROOT"]) / label
    root.mkdir(exist_ok=False)
    binary = Path(os.environ["RVP_INITIALIZER_BINARY"])
    command = [str(binary), str(root)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=120, check=False)
    (root / "command.log").write_bytes(result.stdout)
    assert result.returncode == 0, result.stdout.decode(errors="replace")
    files = sorted(root.glob("seed-*-replay-*.bin"))
    assert len(files) == 32
    expected = {f"seed-{seed}-replay-{replay}.bin" for seed in range(16) for replay in range(2)}
    assert {file.name for file in files} == expected
    for file in files:
        assert len(file.read_bytes()) == 8
        assert sorted(struct.unpack("=2i", file.read_bytes())) == [0, 1]
    return root


def test_actual_rollback_integer_initializer_replays_same_seed():
    root = _run_actual_initializer("same-seed")
    for seed in range(16):
        assert (root / f"seed-{seed}-replay-0.bin").read_bytes() == (root / f"seed-{seed}-replay-1.bin").read_bytes()


def test_actual_rollback_integer_initializer_varies_across_seeds():
    root = _run_actual_initializer("seed-variation")
    actual_bytes = {(root / f"seed-{seed}-replay-0.bin").read_bytes() for seed in range(16)}
    assert len(actual_bytes) > 1


def test_actual_backend_rollback_graph_matches_reference_twice():
    root = Path(os.environ["RVP_NATIVE_OUTPUT_ROOT"]) / "backend-reference"
    root.mkdir(exist_ok=False)
    command = [os.environ["RVP_BACKEND_BINARY"], "test", "-b", "CPU", "-o", "SSM_SCAN_ROLLBACK",
               "--suite-seed", "42", "--repeat-suite", "2", "-j", "1"]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=300, check=False)
    (root / "command.log").write_bytes(result.stdout)
    output = result.stdout.decode(errors="replace")
    assert result.returncode == 0, output
    assert "SSM_SCAN_ROLLBACK" in output
    assert len(re.findall(r"(?m)^\s*1/1 tests passed\s*$", output)) == 2, output
    assert re.search(r"(?m)^\s*1/1 backends passed\s*$", output), output
    assert "NOT_SUPPORTED" not in output and "FAIL" not in output
