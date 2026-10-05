"""The KV-quant width table must match ggml's real block layout.

Regression guard for a defect found 2026-09-22. `_KV_TYPE_F16_RATIO` scored a
quantised KV element by its NOMINAL bit-width, ignoring the scale(s) stored in
every ggml block. q8_0 is 34 bytes per 32 elements, not 32, so "half of f16"
understated it by 5.88%; q4_0 by 11.11%; q4_1 by 10%.

The shape of the error is what gave it away: q5_0 and q5_1 already carried their
true ratios while q8_0/q4_0/q4_1 carried nominal ones. A deliberate
simplification would have been uniformly nominal.

Consequence: the capacity gate UNDERSTATED KV for the three most-used types and
could pass a lineup that does not fit -- exactly the failure its own docstring
says must never happen. Measured: Qwen3.8-27B at n_ctx 262144 with q8_0/q8_0 was
scored 32.50 GiB against a true 34.53 GiB, a 2.03 GiB shortfall on a 64 GiB card.

Asserting the ratios against a hand-copied list would just re-copy the mistake,
so these derive the expected values from the block layouts ggml itself
static_asserts in ggml/src/ggml-common.h.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "server"))

QK = 32
HALF = 2  # sizeof(ggml_half)
U32 = 4

# block_bytes per ggml-common.h's own static_asserts
GGML_BLOCK_BYTES = {
    "q4_0": HALF + QK // 2,            # static_assert: half + QK4_0/2
    "q4_1": 2 * HALF + QK // 2,        # static_assert: 2*half + QK4_1/2
    "q5_0": HALF + U32 + QK // 2,      # static_assert: half + u32 + QK5_0/2
    "q5_1": 2 * HALF + U32 + QK // 2,  # static_assert: 2*half + u32 + QK5_1/2
    "q8_0": HALF + QK,                 # static_assert: half + QK8_0
}


@pytest.fixture(scope="module")
def sm():
    return importlib.import_module("stack_manifest")


@pytest.mark.parametrize("kv_type,block_bytes", sorted(GGML_BLOCK_BYTES.items()))
def test_quantised_ratio_matches_ggml_block_layout(sm, kv_type, block_bytes):
    expected = (block_bytes / QK) / 2.0
    actual = sm._KV_TYPE_F16_RATIO[kv_type]
    assert actual == pytest.approx(expected, abs=1e-12), (
        f"{kv_type}: table says {actual}, ggml block layout gives {expected} "
        f"({block_bytes} B per {QK} elements). A quantised KV block stores its "
        f"scale(s) alongside the quants; the nominal bit-width is not the width."
    )


def test_unquantised_widths(sm):
    assert sm._KV_TYPE_F16_RATIO["f16"] == 1.0
    assert sm._KV_TYPE_F16_RATIO["bf16"] == 1.0
    assert sm._KV_TYPE_F16_RATIO["f32"] == 2.0


def test_no_quantised_type_is_scored_below_its_true_width(sm):
    """The direction that matters: understating passes an infeasible lineup."""
    for kv_type, block_bytes in GGML_BLOCK_BYTES.items():
        true_ratio = (block_bytes / QK) / 2.0
        assert sm._KV_TYPE_F16_RATIO[kv_type] >= true_ratio - 1e-12, (
            f"{kv_type} is scored below its true width -- the gate would pass a "
            f"lineup that does not fit in VRAM."
        )


def test_ratios_are_ordered_by_block_size(sm):
    """A coherence check the old half-corrected table would still have passed,
    kept because it is cheap and catches a transposed pair."""
    by_size = sorted(GGML_BLOCK_BYTES, key=lambda t: GGML_BLOCK_BYTES[t])
    ratios = [sm._KV_TYPE_F16_RATIO[t] for t in by_size]
    assert ratios == sorted(ratios), f"ratios not monotonic in block size: {list(zip(by_size, ratios))}"
