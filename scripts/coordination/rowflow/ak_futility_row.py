"""AK-EVAL-FUT row helper: the shared AutoKernel futility look, self-contained for a sealed row dir.

mk_ak_row.py (polar profile) copies this file VERBATIM into every default-scaffolded row and pins it by sha256
(SOURCE.sha256 + a start-time check in job.py), so a row never imports the research repo at run time.

The math is a line-for-line copy of epyc-inference-research
scripts/kernel_rnd/autokernel/loop/futility.py (sha256 UPSTREAM_SHA256 below; parity pinned by
scripts/coordination/tests/test_ak_futility_row.py):

    after each COMPLETE pair k >= MIN_PAIRS:  bound = fmean(100*ln(c/a)) + z * sigma / sqrt(k)
    futile iff bound < bar_pct

sigma comes from stored A/A pairs (stdev of their log-ratios, >= 3 pairs) or from a single-pair p95 floor / 1.96.
z: 2.5 serving lane (Z_SERVING), 3.5 GPU bench lane (Z_BENCH). Futility-only: there is no early KEEP.
Direction: the look assumes higher is better; a lower-is-better metric (latency) is inverted (1/x) first.
A futile stop is FUTILITY_CANDIDATE_BELOW_BAR with polar FAIL and the look record in RESULT.json.
"""
from __future__ import annotations

import math
import statistics

UPSTREAM = "epyc-inference-research:scripts/kernel_rnd/autokernel/loop/futility.py"
UPSTREAM_SHA256 = "422a4546601c117088eb136867b6c358e1e8498f7c474cc43a65604a34b8970e"
STOPPING = "fixed_pairs+futility_only.v1"
SCHEMA = "epyc.autokernel.futility_look.v1"
Z_SERVING = 2.5
Z_BENCH = 3.5
MIN_PAIRS = 2
P95_Z = 1.96
VERDICT = "FUTILITY_CANDIDATE_BELOW_BAR"


def log_ratios_pct(anchor, candidate) -> list[float]:
    """Per complete pair: 100 * ln(candidate / anchor)."""
    return [100.0 * math.log(c / a) for a, c in zip(anchor, candidate) if a > 0 and c > 0]


def sigma_from_aa_samples(anchor, candidate) -> float | None:
    ratios = log_ratios_pct(anchor or (), candidate or ())
    return statistics.stdev(ratios) if len(ratios) >= 3 else None


def sigma_from_single_pair_floor(floor1_pct) -> float | None:
    return None if not floor1_pct or floor1_pct <= 0 else floor1_pct / P95_Z


def look(ratios, *, sigma_pair_pct: float, bar_pct: float, z: float, min_pairs: int = MIN_PAIRS) -> dict:
    """One interim look over the complete pairs so far. Pure."""
    k = len(ratios)
    if k < min_pairs:
        return {"decision": "continue", "k": k, "bound_pct": None}
    bound = statistics.fmean(ratios) + z * sigma_pair_pct / math.sqrt(k)
    return {"decision": "futile" if bound < bar_pct else "continue", "k": k, "bound_pct": round(bound, 4)}


def sigma_from_source(source: str, read=None) -> tuple[float, str]:
    """`aa:<path>` (JSON {"anchor": [...], "candidate": [...]} of stored A/A pairs) or `floor1:<pct>`.
    Returns (sigma, source tag); raises ValueError when it cannot produce a sigma."""
    kind, _, val = (source or "").partition(":")
    if kind == "floor1":
        s = sigma_from_single_pair_floor(float(val))
    elif kind == "aa":
        import json
        rec = json.loads(read(val) if read else open(val).read())
        s = sigma_from_aa_samples(rec.get("anchor"), rec.get("candidate"))
    else:
        raise ValueError(f"sigma source {source!r} is not aa:<path> or floor1:<pct>")
    if not s or s <= 0:
        raise ValueError(f"sigma source {source!r} gives no sigma (aa needs >= 3 pairs, floor1 > 0)")
    return s, kind


class Look:
    """The row's pre-registered rule. Call with the complete anchor/candidate samples after every pair."""

    def __init__(self, sigma_pair_pct, bar_pct, z, min_pairs=MIN_PAIRS, sigma_source="aa_calibration",
                 direction="higher"):
        if not (sigma_pair_pct > 0 and z > 0 and min_pairs >= 2 and bar_pct is not None):
            raise ValueError("futility rule needs sigma>0, z>0, min_pairs>=2 and a bar")
        if direction not in ("higher", "lower"):
            raise ValueError("direction must be higher or lower")
        self.sigma, self.bar, self.z, self.min_pairs, self.source = sigma_pair_pct, bar_pct, z, min_pairs, sigma_source
        self.direction = direction

    def plan(self) -> dict:
        return {"schema": SCHEMA, "stopping": STOPPING, "stop_on_answer": False, "z": self.z,
                "min_pairs": self.min_pairs, "bar_pct": self.bar, "sigma_pair_pct": round(self.sigma, 6),
                "sigma_source": self.source, "direction": self.direction, "upstream_sha256": UPSTREAM_SHA256}

    def __call__(self, anchor, candidate) -> dict:
        if self.direction == "lower":   # the look assumes higher is better: invert lower-is-better samples first
            anchor = [1.0 / x if x > 0 else x for x in anchor]
            candidate = [1.0 / x if x > 0 else x for x in candidate]
        r = look(log_ratios_pct(anchor, candidate), sigma_pair_pct=self.sigma, bar_pct=self.bar, z=self.z,
                 min_pairs=self.min_pairs)
        r.update(sigma_pair_pct=round(self.sigma, 6), z=self.z, bar_pct=self.bar, direction=self.direction)
        return r

    def result(self, rec: dict) -> dict:
        """RESULT.json fields for a futile stop: a polar FAIL, never a keep."""
        return {"complete": True, "verdict": VERDICT, "polar": "FAIL", "stop_reason": "futility",
                "futility": {**self.plan(), "stopped_at": rec}}
