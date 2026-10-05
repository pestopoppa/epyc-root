"""Tests for orchestrator stack state persistence."""

from __future__ import annotations

import json

from scripts.server.stack_state import ProcessInfo, load_state_file, save_state_file


def test_state_round_trips_process_info(tmp_path) -> None:
    state_file = tmp_path / "orchestrator_state.json"
    process = ProcessInfo(
        role="orchestrator",
        pid=123,
        port=8000,
        started_at="now",
        model_path="api",
        log_file="api.log",
    )

    save_state_file(state_file, {"api": process})

    assert load_state_file(state_file) == {"api": process}


def test_save_state_skips_transient_dict_records(tmp_path) -> None:
    state_file = tmp_path / "orchestrator_state.json"
    process = ProcessInfo(
        role="embedder",
        pid=456,
        port=8090,
        started_at="now",
        model_path="embed.gguf",
        log_file="embed.log",
    )

    save_state_file(state_file, {"server_8090": process, "preserved": {"roles": []}})

    assert sorted(json.loads(state_file.read_text())) == ["server_8090"]


def test_load_state_drops_invalid_records(tmp_path) -> None:
    state_file = tmp_path / "orchestrator_state.json"
    state_file.write_text(
        json.dumps(
            {
                "valid": {
                    "role": "embedder",
                    "pid": 456,
                    "port": 8090,
                    "started_at": "now",
                    "model_path": "embed.gguf",
                    "log_file": "embed.log",
                },
                "invalid": {"roles": []},
            }
        )
    )

    assert sorted(load_state_file(state_file)) == ["valid"]
