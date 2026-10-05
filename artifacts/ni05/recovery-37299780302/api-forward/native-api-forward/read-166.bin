"""ESC-8 Fix 2-addendum: cmd_start facts refresh must use the merged fleet state.

A subset/``--only`` start (or a start that leaves already-healthy llama-servers
untouched) keeps those llama rows solely in the persisted state file. Passing
only the in-memory (newly-started) rows to the runtime-facts refresh yields
``selected_servers: []`` even though the fleet is up (the 09:14 defect). The fix
merges the persisted rows under the in-memory rows before refreshing; the
manifest writer's pid-liveness filter drops any stale merged-in rows.
"""

from __future__ import annotations

from pathlib import Path

from scripts.server.runtime_facts_manifest import build_runtime_facts_manifest
from scripts.server.stack_commands import _merge_persisted_state_for_facts
from scripts.server.stack_state import ProcessInfo


def _pi(role: str, pid: int, port: int) -> ProcessInfo:
    return ProcessInfo(
        role=role,
        pid=pid,
        port=port,
        started_at="2026-07-22T09:14:00Z",
        model_path=f"/models/{role}.gguf",
        log_file=f"/logs/{role}.log",
    )


def test_merge_keeps_persisted_only_rows_and_in_memory_wins() -> None:
    persisted = {
        "worker_general": _pi("worker_general", 111, 8082),
        "frontdoor": _pi("frontdoor", 112, 8080),
    }
    in_memory = {
        # collision: freshly (re)started worker_general row must win
        "worker_general": _pi("worker_general", 999, 8082),
        "orchestrator": _pi("orchestrator", 222, 8000),
    }

    merged = _merge_persisted_state_for_facts(persisted, in_memory)

    assert set(merged) == {"worker_general", "frontdoor", "orchestrator"}
    assert merged["worker_general"].pid == 999  # in-memory wins
    assert merged["frontdoor"].pid == 112  # persisted-only row preserved


def _selected_ports(state, *, pid_alive) -> set[int]:
    manifest = build_runtime_facts_manifest(
        state=state,
        launch_contracts={},
        stack_priors_path=Path("/nonexistent/stack_priors.yaml"),
        stack_numa_mode="quarter",
        tmp_dir=Path("/nonexistent/tmp"),
        source="test",
        pid_alive=pid_alive,
    )
    servers = manifest["runtime_stack"]["selected_servers"]
    return {s["port"] for s in servers}


def test_partial_in_memory_state_alone_emits_no_llama_servers() -> None:
    """The defect: passing only the newly-started (non-llama) rows → empty fleet."""
    in_memory = {"orchestrator": _pi("orchestrator", 222, 8000)}
    assert _selected_ports(in_memory, pid_alive=lambda _p: True) == set()


def test_merged_state_recovers_the_live_llama_fleet() -> None:
    """The fix: merging the persisted llama rows recovers the realized fleet."""
    persisted = {
        "worker_general": _pi("worker_general", 111, 8082),
        "frontdoor": _pi("frontdoor", 112, 8080),
    }
    in_memory = {"orchestrator": _pi("orchestrator", 222, 8000)}

    merged = _merge_persisted_state_for_facts(persisted, in_memory)
    ports = _selected_ports(merged, pid_alive=lambda _p: True)

    assert 8082 in ports  # worker_general (quarter) recovered
    assert 8080 in ports  # frontdoor (quarter) recovered
    assert 8000 not in ports  # orchestrator is not a llama serving role


def test_stale_merged_row_is_liveness_filtered() -> None:
    """A merged-in persisted row whose pid is dead is dropped by the writer."""
    persisted = {
        "worker_general": _pi("worker_general", 111, 8082),  # dead below
        "frontdoor": _pi("frontdoor", 112, 8080),
    }
    in_memory = {"orchestrator": _pi("orchestrator", 222, 8000)}

    merged = _merge_persisted_state_for_facts(persisted, in_memory)
    ports = _selected_ports(merged, pid_alive=lambda p: p != 111)

    assert 8082 not in ports  # stale worker_general dropped
    assert 8080 in ports  # live frontdoor retained
