"""Invariant: the config fingerprint is CANONICAL (order-independent) and excludes ONLY truly
ephemeral metadata (free-text narrative), so genuine reproductions of the same intervention
cluster into one robust-median Pareto representative instead of fragmenting. Locks both the
live-archive fingerprint (autopilot._config_fingerprint) and the dashboard reconstruction's
mirror (dashboard._config_fingerprint_from_row). See the 2026-06-04 MAD policy correction.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from autopilot import _config_fingerprint, _EPHEMERAL_ACTION_KEYS  # type: ignore[import-not-found]
from src.api.routes.dashboard import _config_fingerprint_from_row


def test_fingerprint_is_canonical_order_independent():
    """Key order must not change the fingerprint (sort_keys)."""
    assert _config_fingerprint({"type": "seed_batch", "n_questions": 10}) == \
        _config_fingerprint({"n_questions": 10, "type": "seed_batch"})


def test_fingerprint_excludes_ephemeral_narrative():
    """Free-text narrative that describes but does not determine the config must NOT change
    the fingerprint — otherwise per-trial descriptions fragment genuine reproductions."""
    base = {"type": "seed_batch", "n_questions": 10}
    narrated = {**base, "description": "relax WS-3 web-search deny", "hypothesis": "h",
                "reasoning": "r", "expected_mechanism": "m"}
    assert _config_fingerprint(base) == _config_fingerprint(narrated)


def test_fingerprint_distinguishes_config_determining_fields():
    """Anything that changes behaviour (type, params, flags, n_questions, …) MUST change it —
    the exclusion list stays tight so distinct interventions never collide."""
    base = {"type": "seed_batch", "n_questions": 10}
    assert _config_fingerprint(base) != _config_fingerprint({"type": "train_routing_models"})
    assert _config_fingerprint(base) != _config_fingerprint({**base, "n_questions": 20})
    assert _config_fingerprint(base) != _config_fingerprint({**base, "flags": {"skillbank": True}})


def test_ephemeral_key_set_is_narrative_only():
    """Guard against accidental over-stripping: the ephemeral set must contain only narrative
    keys, never config-determining ones."""
    forbidden = {"type", "params", "flags", "surface", "n_questions", "min_memories", "tier"}
    assert _EPHEMERAL_ACTION_KEYS.isdisjoint(forbidden)


def test_dashboard_fingerprint_mirrors_canonical_and_ephemeral_rules():
    """The dashboard reconstruction's fingerprint must follow the same rules, so the panel
    clusters reproductions exactly like the live archive."""
    row_a = {"config_snapshot": {"type": "seed_batch", "n_questions": 10}}
    row_b = {"config_snapshot": {"n_questions": 10, "type": "seed_batch",
                                 "description": "narrated differently"}}
    row_c = {"config_snapshot": {"type": "train_routing_models"}}
    assert _config_fingerprint_from_row(row_a) == _config_fingerprint_from_row(row_b)
    assert _config_fingerprint_from_row(row_a) != _config_fingerprint_from_row(row_c)
