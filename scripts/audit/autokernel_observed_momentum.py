#!/usr/bin/env python3
"""Read-only, epoch-local AutoKernel serving momentum diagnostic.

This is not PACEvolve's known-optimum backtracker, an AK-D32 replacement, or
evidence of a counterfactual keep. It describes only completed native A/B
candidate rates under one exact metric/surface/recipe/request/anchor epoch.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

SCHEMA = "epyc.autokernel.observed_momentum.v1"
STATUSES = ("measured_null", "kept", "keep_candidate")
MAX_ATTEMPTS = 500
MAX_PAYLOAD_BYTES = 128 * 1024 * 1024
BETA = 0.85
EPS_REL = 0.001


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and value > 0


def project(db: Path, *, max_attempts: int = MAX_ATTEMPTS,
            max_payload_bytes: int = MAX_PAYLOAD_BYTES) -> dict[str, Any]:
    if not 1 <= max_attempts <= MAX_ATTEMPTS or not 1 <= max_payload_bytes <= MAX_PAYLOAD_BYTES:
        raise ValueError("requested bounds exceed the instrument limits")
    if not db.is_file():
        raise ValueError("native experiments.db is absent")
    connection = sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(experiments)")}
        required = {"attempt_id", "recorded_at", "epoch_sha256", "status", "payload"}
        if not required <= columns:
            raise ValueError("experiments table lacks native identity/time/epoch/status/payload")
        rows = connection.execute(
            "SELECT attempt_id,recorded_at,epoch_sha256,status,length(payload),payload "
            "FROM experiments WHERE status IN (?,?,?) ORDER BY rowid LIMIT ?",
            (*STATUSES, max_attempts + 1),
        )
        grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
        excluded: dict[str, int] = defaultdict(int)
        seen = 0
        for attempt_id, recorded_at, epoch, status, size, raw in rows:
            seen += 1
            if seen > max_attempts:
                raise ValueError("attempt bound reached; refusing a silently partial timeline")
            if size is None or size > max_payload_bytes:
                excluded["oversize_payload"] += 1
                continue
            try:
                comparison = json.loads(raw).get("comparison")
            except (ValueError, TypeError):
                excluded["malformed_payload"] += 1
                continue
            if not isinstance(comparison, dict) or comparison.get("schema") != "epyc.autokernel.serving_ab.v1":
                excluded["not_serving_ab"] += 1
                continue
            # The native producer in loop/serving.py defines aggregate_tok_s as
            # throughput and effect=candidate/anchor-1: higher is better.
            if comparison.get("metric") != "aggregate_tok_s":
                excluded["unsupported_metric_direction"] += 1
                continue
            anchor, candidate = comparison.get("anchor_tok_s"), comparison.get("candidate_tok_s")
            if not _positive(anchor) or not _positive(candidate) or not _positive(comparison.get("pairs")):
                excluded["invalid_native_rate_or_pairs"] += 1
                continue
            surface = comparison.get("surface")
            recipe = comparison.get("recipe_hash")
            request = comparison.get("request_digest")
            if not all(isinstance(item, str) and item for item in
                       (attempt_id, recorded_at, epoch, surface, recipe, request)):
                excluded["missing_comparability_identity"] += 1
                continue
            key = (epoch, "aggregate_tok_s", surface, recipe, request)
            grouped[key].append({"attempt_id": attempt_id, "recorded_at": recorded_at,
                                 "status": status, "anchor_tok_s": anchor,
                                 "candidate_tok_s": candidate, "pairs": comparison["pairs"]})
    finally:
        connection.close()

    epochs = []
    for (epoch, metric, surface, recipe, request), observations in sorted(grouped.items()):
        observations.sort(key=lambda row: (row["recorded_at"], row["attempt_id"]))
        best = 0.0
        momentum = 0.0
        points = []
        for ordinal, row in enumerate(observations):
            candidate = row["candidate_tok_s"]
            relative_progress = None if ordinal == 0 else max(0.0, candidate / best - 1.0)
            if relative_progress is not None:
                momentum = BETA * momentum + (1 - BETA) * relative_progress
            best = max(best, candidate)
            points.append({**row, "best_observed_tok_s": best,
                           "relative_best_progress": relative_progress,
                           "relative_progress_ewma": None if ordinal == 0 else momentum,
                           "below_eps_observed": None if ordinal == 0 else momentum < EPS_REL})
        epochs.append({"epoch_sha256": epoch, "metric": metric,
                       "metric_direction": "higher_better",
                       "metric_direction_basis": "loop/serving.py: aggregate_tok_s; effect=candidate/anchor-1",
                       "surface": surface, "recipe_hash": recipe,
                       "request_digest": request, "points": points})
    return {"schema": SCHEMA, "authority": "observe_only_not_a_plateau_stop",
            "source_db": str(db), "selected_attempts": seen,
            "excluded": dict(sorted(excluded.items())),
            "beta": BETA, "epsilon_relative": EPS_REL,
            "epoch_local_only": True, "cross_epoch_absolute_gain": None,
            "cost_credit_vs_ak_d32": None,
            "ancestor_revert_vs_cold_restart": None, "epochs": epochs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = project(args.db)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.resolve() == args.db.resolve():
            parser.error("output must not overwrite the native database")
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
