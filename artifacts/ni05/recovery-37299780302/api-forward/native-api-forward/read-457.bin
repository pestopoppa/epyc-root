"""`serving_shape.kv_kib_per_token_f16` must count KV LAYERS, not all layers.

Found 2026-09-22. The capacity gate's documented formula said
`block_count * head_count_kv * (key+value) * 2 / 1024`, which is right only when
every layer is globally attentive. Qwen3.6/3.8 declare
`full_attention_interval = 4`, so only every 4th layer keeps a KV cache and the
rest are filtered out of it. Six fleet rows inherited the 4x over-count.

It matters in the refusing direction: over-counting KV makes the gate reject
lineups that fit. A 262144-context role was scored infeasible on a card with
16 GiB to spare, which nearly bought a KV-quantisation quality tradeoff that was
never needed.

The expected values below are MEASURED from the server's own KV buffer report on
the v10 GPU build at n_ctx 65536, not re-derived from the same formula under test:
Qwen3.8-27B reported `size = 2176.00 MiB ( 65536 cells, 16 layers ...)` with
K (q8_0) 1088.00 MiB and V (q8_0) 1088.00 MiB -> 34.0 KiB/token at q8_0 and
64.0 KiB/token at f16.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "server"))


@pytest.fixture(scope="module")
def sm():
    return importlib.import_module("stack_manifest")


def test_qwen38_27b_matches_the_server_reported_kv(sm) -> None:
    """block_count 65, full_attention_interval 4 -> 16 KV layers, 64.0 KiB/token."""
    assert sm.kv_layers(65, 4) == 16
    assert sm.kv_kib_per_token_f16(65, 4, 256, 256, 4) == pytest.approx(64.0)
    # ... and the q8_0 figure the server actually printed, via the width table.
    half = 64.0 / 2.0
    ratio = sm._KV_TYPE_F16_RATIO["q8_0"]
    assert half * (ratio + ratio) == pytest.approx(34.0)


def test_the_block_count_form_is_the_bug_not_the_contract(sm) -> None:
    """Guard against someone 'restoring' the old formula."""
    naive = 65 * 4 * (256 + 256) * 2 / 1024
    assert naive == pytest.approx(260.0)
    assert sm.kv_kib_per_token_f16(65, 4, 256, 256, 4) < naive
    assert naive / sm.kv_kib_per_token_f16(65, 4, 256, 256, 4) == pytest.approx(4.0625)


@pytest.mark.parametrize(
    "name,block_count,kv_heads,interval,expected",
    [
        ("Qwen3.8-27B", 65, 4, 4, 64.0),
        ("Qwen3.6-27B-MTP", 65, 4, 4, 64.0),
        ("Qwen3.6-27B", 64, 4, 4, 64.0),
        ("Qwen3.6-35B-A3B-MTP", 41, 2, 4, 20.0),
        ("Qwen3.6-35B-A3B", 40, 2, 4, 20.0),
    ],
)
def test_fleet_models_with_filtered_layers(sm, name, block_count, kv_heads, interval, expected) -> None:
    assert sm.kv_kib_per_token_f16(block_count, kv_heads, 256, 256, interval) == pytest.approx(expected), name


@pytest.mark.parametrize(
    "name,block_count,kv_heads,klen,expected",
    [
        ("Qwen3-Next-80B", 48, 2, 256, 96.0),
        ("gemma-4-e4b", 42, 2, 512, 168.0),
    ],
)
def test_models_without_the_key_are_unchanged(sm, name, block_count, kv_heads, klen, expected) -> None:
    """No full_attention_interval -> every layer keeps KV, and the old formula was right."""
    assert sm.kv_kib_per_token_f16(block_count, kv_heads, klen, klen, None) == pytest.approx(expected), name
    assert sm.kv_layers(block_count, None) == block_count


def test_interval_of_one_or_zero_is_every_layer(sm) -> None:
    assert sm.kv_layers(65, 1) == 65
    assert sm.kv_layers(65, 0) == 65
