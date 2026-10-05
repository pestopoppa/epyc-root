"""Unit tests for seeding telemetry helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "seeding_telemetry.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_batch_duration_history_persists_across_module_loads(tmp_path: Path, monkeypatch):
    history_path = tmp_path / "seed_batch_history.jsonl"
    monkeypatch.setenv("SEEDING_BATCH_TELEMETRY_PATH", str(history_path))
    monkeypatch.setenv("SEEDING_BATCH_TELEMETRY_PERSIST", "1")

    writer = _load_module("seeding_telemetry_test_writer")
    writer.reset(clear_persisted=True)
    writer.record_batch_duration(4, 400.0)

    reader = _load_module("seeding_telemetry_test_reader")

    assert history_path.exists()
    assert reader.median_seconds_per_question() == 100.0
    assert reader.batch_summary()["n_recent"] == 1
