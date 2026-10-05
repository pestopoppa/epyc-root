"""D2: autopilot state_store.save_state emits strict JSON (non-finite -> null).

A saved state file with bare ``NaN`` / ``Infinity`` tokens is invalid JSON and
breaks strict readers (jq, load_state). save_state must sanitize non-finite
floats to null and round-trip cleanly. Fixtures use tmp_path only.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.autopilot.state_store import load_state, save_state


def _fail_on_bare_constant(token: str):  # pragma: no cover - only hit on failure
    raise AssertionError(f"bare non-finite JSON constant present: {token!r}")


def test_save_state_sanitizes_nonfinite_and_round_trips(tmp_path: Path) -> None:
    state = {
        "scalar_nan": float("nan"),
        "nested": {"inf": float("inf"), "neg_inf": float("-inf")},
        "list": [1.0, float("nan"), 2.5],
        "finite": 0.25,
        "text": "ok",
        "count": 3,
    }
    path = tmp_path / "autopilot_state.json"

    save_state(path, state)

    raw = path.read_text(encoding="utf-8")
    assert "NaN" not in raw
    assert "Infinity" not in raw
    # Strict parse: parse_constant fires only on bare NaN/Infinity/-Infinity.
    json.loads(raw, parse_constant=_fail_on_bare_constant)

    # load_state returns the parsed dict (no corrupt-state exit for valid JSON).
    loaded = load_state(path, lambda: {})
    assert loaded["scalar_nan"] is None
    assert loaded["nested"]["inf"] is None
    assert loaded["nested"]["neg_inf"] is None
    assert loaded["list"] == [1.0, None, 2.5]
    assert loaded["finite"] == 0.25
    assert loaded["text"] == "ok"
    assert loaded["count"] == 3
