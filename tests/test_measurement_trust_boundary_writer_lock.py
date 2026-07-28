"""Cross-process contention coverage for every live campaign writer surface."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]
P_BENCH = ROOT / "artifacts/operator/ratify_pbench4_fg4b_server_native_20260728.sh"
FINAL_C1 = ROOT / "artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.sh"
E8_ROOT = Path("/mnt/raid0/llm/worktrees/e8-clean-integration-20260728")
E8_WRAPPER = (
    E8_ROOT
    / "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
)
V5_APPLIER = (
    E8_ROOT
    / "scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
)


@dataclass(frozen=True)
class Surface:
    name: str
    command: list[str]
    environment: dict[str, str]
    hold_variable: str


def _surfaces(tmp_path: Path, trust_lock: Path) -> list[Surface]:
    pbench_root = tmp_path / "pbench-root"
    final_root = tmp_path / "final-root"
    evidence_root = tmp_path / "final-evidence"
    orch_root = tmp_path / "final-orchestrator"
    wrapper_root = tmp_path / "wrapper-root"
    wrapper_state = tmp_path / "wrapper-state.json"
    wrapper_private_lock = tmp_path / "wrapper-private.lock"
    wrapper_evidence = tmp_path / "wrapper-evidence.json"
    for path in (
        pbench_root,
        final_root,
        evidence_root,
        orch_root,
        wrapper_root,
    ):
        path.mkdir()
    wrapper_state.write_text("{}\n", encoding="utf-8")
    wrapper_evidence.write_text("{}\n", encoding="utf-8")

    return [
        Surface(
            "pbench4",
            ["/bin/bash", str(P_BENCH), "--validate-only"],
            {
                "P_BENCH_4_TEST_MODE": "1",
                "EPYC_ROOT": str(pbench_root),
                "P_BENCH_4_TRUST_LOCK": str(trust_lock),
            },
            "P_BENCH_4_TEST_HOLD_TRUST_LOCK_SECONDS",
        ),
        Surface(
            "final-c1",
            ["/bin/bash", str(FINAL_C1), "--validate-only"],
            {
                "E8_C1_AMENDMENT_TEST_MODE": "1",
                "EPYC_ROOT": str(final_root),
                "E8_C1_EVIDENCE": str(evidence_root),
                "EPYC_ORCHESTRATOR": str(orch_root),
                "E8_C1_TRUST_LOCK": str(trust_lock),
            },
            "E8_C1_TEST_HOLD_TRUST_LOCK_SECONDS",
        ),
        Surface(
            "e8-wrapper",
            [
                "/bin/bash",
                str(E8_WRAPPER),
                "--prevalidate",
                "--evidence",
                str(wrapper_evidence),
                "--expected-pre-state-sha256",
                "0" * 64,
                "--expected-candidate-state-sha256",
                "1" * 64,
            ],
            {
                "E8_V5_OPERATOR_ROOT": str(wrapper_root),
                "E8_V5_STATE": str(wrapper_state),
                "E8_V5_LOCK_PATH": str(wrapper_private_lock),
                "E8_V5_TRUST_LOCK": str(trust_lock),
                "E8_V5_TEST_MODE": "1",
            },
            "E8_V5_TEST_HOLD_TRUST_LOCK_SECONDS",
        ),
        Surface(
            "v5-applier",
            [
                "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python",
                str(V5_APPLIER),
                "--plan",
            ],
            {
                "E8_V5_TRUST_LOCK": str(trust_lock),
                "E8_V5_TEST_MODE": "1",
            },
            "E8_V5_TEST_HOLD_TRUST_LOCK_SECONDS",
        ),
    ]


def _lock_is_held(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("r+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return False


def _wait_for_holder(process: subprocess.Popen[str], trust_lock: Path) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if _lock_is_held(trust_lock):
            return
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(f"writer exited before holding lock: {stdout=} {stderr=}")
        time.sleep(0.01)
    pytest.fail("writer did not acquire the shared measurement lock")


def _kill_and_verify(process: subprocess.Popen[str], trust_lock: Path) -> None:
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGKILL)
    process.communicate(timeout=5)
    assert process.returncode == -signal.SIGKILL
    assert subprocess.run(
        ["ps", "-p", str(process.pid)],
        capture_output=True,
        check=False,
    ).returncode != 0
    assert not _lock_is_held(trust_lock)


def test_every_live_writer_blocks_every_other_writer_on_one_inode(
    tmp_path: Path,
) -> None:
    trust_lock = tmp_path / "measurement-trust-boundary.lock"
    surfaces = _surfaces(tmp_path, trust_lock)
    inode: tuple[int, int] | None = None

    for holder in surfaces:
        holder_env = {
            **os.environ,
            **holder.environment,
            holder.hold_variable: "30",
        }
        process = subprocess.Popen(
            holder.command,
            cwd="/",
            env=holder_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            _wait_for_holder(process, trust_lock)
            current_inode = (trust_lock.stat().st_dev, trust_lock.stat().st_ino)
            inode = inode or current_inode
            assert current_inode == inode

            for contender in surfaces:
                if contender.name == holder.name:
                    continue
                blocked = subprocess.run(
                    contender.command,
                    cwd="/",
                    env={**os.environ, **contender.environment},
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
                assert blocked.returncode != 0, (
                    f"{contender.name} entered while {holder.name} held the lock"
                )
                assert "measurement trust-boundary lock is already held" in blocked.stderr
                assert (trust_lock.stat().st_dev, trust_lock.stat().st_ino) == inode
        finally:
            _kill_and_verify(process, trust_lock)
