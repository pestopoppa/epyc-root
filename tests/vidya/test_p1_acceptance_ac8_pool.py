"""P1 acceptance AC8: the sampled pool is exactly the mechanisms the experiments adapter projects.

Regression (2026-10-24): the pool admitted every `gate_refused` row by status, so a mechanism tried
only through harness/scope refusals (`oracle_unavailable`, `op_scope`) -- which the adapter never
projects (`scope_gate`) -- could be sampled and reported MISSING although nothing could carry it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import p1_acceptance as acc  # noqa: E402
import test_autokernel_experiments as fx  # noqa: E402
from adapters import autokernel_experiments as exp  # noqa: E402


def test_pool_matches_the_adapter_classification(tmp_path):
    store = fx.make_store(tmp_path)
    pool = acc._store_mechanisms(store)
    projected = {str(r["mechanism_id"]) for r in exp.native_rows(store)
                 if r.get("status") in acc.PROJECTED_STATUSES and r.get("mechanism_id")
                 and r.get("payload") is not None and exp.classify(r)[0] is not None}
    assert set(pool) == projected
    # the correctness refusals stay (by `refusal_gate` and by the gates list) ...
    assert "akm-q8-streamk" in pool and "akm-gl" in pool
    # ... the scope-gate refusal, the unparseable payload and the attempt-less row do not
    assert "akm-scope" not in pool and "akm-bad" not in pool and "akm-x" not in pool
    # BASELINE records are not mechanisms tried
    assert "anchor-guard" not in pool and "rt-arm" not in pool


def test_oracle_unavailable_only_mechanism_is_not_sampled(tmp_path):
    base = {"campaign_id": "ak-loop", "epoch_sha256": fx.EPOCH, "spawn_parent": fx.BUILD,
            "target_surface": "ggml/src/ggml-cpu/ops.cpp", "target_symbol": "fa"}
    fixture = list(fx.FIXTURE) + [
        ("oracle_unavail", "gate_refused",
         {**base, "mechanism_id": "akm-cpu-fa-sparse-mask-bitwalk",
          "refusal_reason": "the anchor's own repeated greedy completions differ"},
         {"refusal_gate": "oracle_unavailable", "reason": "instrument cannot judge a race"}),
    ]
    store = fx.make_store(tmp_path, fixture=fixture)
    assert "akm-cpu-fa-sparse-mask-bitwalk" not in acc._store_mechanisms(store)
