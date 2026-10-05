#!/usr/bin/env python3
"""EV-CONF-2 offline comparison of confidence sources (AUROC / ECE) on an eval sidecar.

Input is one or more ``question_results*.jsonl`` sidecars written by
``eval_tower._EvalQuestionJsonlWriter``. The tool needs zero inference. For
every scored row it computes each candidate confidence source and reports, per
source:

* ``n``: the number of rows where the source is defined
* ``auroc`` (``stat_tests.roc_auc``, tie-averaged) with a seeded percentile
  bootstrap CI
* ``ece`` (the closed-top-bin, 10-bin definition that ``stat_tests`` uses and
  eval_tower's EV-11b era stamps), optionally prevalence-reweighted
* ``paired_delta_auroc`` against the ``legacy_confidence`` baseline, computed on
  rows common to both sources with a paired bootstrap CI

Sources:

* ``legacy_confidence``: the aggregate geomean stored on every real-confidence
  row, present in old sidecars. It reproduces the E7c ECE exactly. Its AUROC is
  shifted by the 6-d.p. rounding of the stored value, which creates ties (E7c
  worker_general: 0.437 from the sidecar vs 0.401 from the in-memory aggregate).
* ``neg_length`` (AUROC only; not a probability): ``-tokens_generated``. This is
  the length-confounding probe. If it discriminates as well as the geomean
  does, the geomean is mostly a length proxy.
* token-trace sources (``token_confidence.CANDIDATE_SOURCES``): present only on
  rows written after EV-CONF-2 capture landed (``token_logprobs`` key). Old
  sidecars decode to "absent" and are reported with ``n=0``, never as errors.

Output is an observation-grade JSON report, with a short text table on stderr.
It applies no gate or verdict. The EV-CONF-2 success gate (scoping (c)) and any
P-CAL amendment are read by a human from these numbers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (REPO_ROOT, REPO_ROOT / "scripts" / "autopilot", REPO_ROOT / "scripts" / "benchmark"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import token_confidence  # noqa: E402
from src.llm_primitives.stat_tests import expected_calibration_error, roc_auc  # noqa: E402

REPORT_SCHEMA = "epyc.confidence_source_compare.v1"
REAL_CONFIDENCE_SOURCES = {"completion_probabilities_geomean"}
BASELINE = "legacy_confidence"
PROBABILITY_SOURCES = {BASELINE, *token_confidence.CANDIDATE_SOURCES}


def load_rows(paths: Sequence[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return scored rows (deduplicated by (file, ordinal), last write wins) plus load stats."""
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    stats: dict[str, Any] = {"files": [], "excluded_unscored": 0, "malformed": 0}
    for path in paths:
        data = path.read_bytes()
        stats["files"].append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest()})
        for line in data.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                stats["malformed"] += 1
                continue
            if row.get("row_type") != "question_result" or not isinstance(row.get("result"), dict):
                continue
            rows[(str(path), int(row.get("ordinal", -1)))] = row
    scored: list[dict[str, Any]] = []
    for row in rows.values():
        res = row["result"]
        disposition = res.get("disposition")
        if res.get("error") or (disposition not in (None, "", "scored")):
            stats["excluded_unscored"] += 1
            continue
        scored.append(row)
    stats["scored_rows"] = len(scored)
    return scored, stats


def source_values(row: dict[str, Any]) -> dict[str, float | None]:
    res = row["result"]
    out: dict[str, float | None] = {}
    conf = res.get("confidence")
    out[BASELINE] = (
        float(conf)
        if conf is not None and res.get("confidence_source") in REAL_CONFIDENCE_SOURCES
        else None
    )
    tokens = res.get("tokens_generated")
    out["neg_length"] = -float(tokens) if isinstance(tokens, (int, float)) and tokens > 0 else None
    try:
        trace = token_confidence.decode_token_trace(row.get("token_logprobs"))
    except ValueError:
        trace = None
    for name, fn in token_confidence.CANDIDATE_SOURCES.items():
        out[name] = fn(trace) if trace is not None else None
    return out


def weighted_ece(
    probs: Sequence[float], labels: Sequence[float], weights: Sequence[float], n_bins: int = 10
) -> float | None:
    """Closed-top-bin ECE with sample weights. Uniform weights equal ``stat_tests`` exactly."""
    total_w = sum(weights)
    if not probs or total_w <= 0:
        return None
    acc = 0.0
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        idx = [
            k
            for k, p in enumerate(probs)
            if (lo <= p < hi) or (i == n_bins - 1 and lo <= p <= hi)
        ]
        w = sum(weights[k] for k in idx)
        if w <= 0:
            continue
        conf = sum(weights[k] * probs[k] for k in idx) / w
        accb = sum(weights[k] * labels[k] for k in idx) / w
        acc += (w / total_w) * abs(accb - conf)
    return acc


def _bootstrap(
    n: int, stat: Callable[[list[int]], float | None], reps: int, seed: int
) -> tuple[float, float] | None:
    if reps <= 0 or n == 0:
        return None
    rng = random.Random(seed)
    vals: list[float] = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        v = stat(idx)
        if v is not None and math.isfinite(v):
            vals.append(v)
    if len(vals) < max(10, reps // 2):
        return None
    vals.sort()
    lo = vals[int(0.025 * (len(vals) - 1))]
    hi = vals[int(math.ceil(0.975 * (len(vals) - 1)))]
    return (round(lo, 4), round(hi, 4))


def compare(
    rows: Sequence[dict[str, Any]],
    *,
    reweight_prevalence: float | None = None,
    bootstrap: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    labels_all = [1.0 if r["result"].get("correct") else 0.0 for r in rows]
    values = [source_values(r) for r in rows]
    names = [BASELINE, "neg_length", *token_confidence.CANDIDATE_SOURCES]
    p_hat = sum(labels_all) / len(labels_all) if labels_all else 0.0

    def weights_for(labels: Sequence[float]) -> list[float]:
        if reweight_prevalence is None:
            return [1.0] * len(labels)
        p = sum(labels) / len(labels) if labels else 0.0
        if p <= 0.0 or p >= 1.0:
            return [1.0] * len(labels)
        wp, wn = reweight_prevalence / p, (1.0 - reweight_prevalence) / (1.0 - p)
        return [wp if y >= 0.5 else wn for y in labels]

    per_source: dict[str, Any] = {}
    for si, name in enumerate(names):
        idx = [i for i, v in enumerate(values) if v[name] is not None]
        xs = [float(values[i][name]) for i in idx]  # type: ignore[arg-type]
        ys = [labels_all[i] for i in idx]
        entry: dict[str, Any] = {"n": len(idx)}
        if not idx:
            per_source[name] = entry
            continue
        entry["accuracy"] = round(sum(ys) / len(ys), 4)
        auc = roc_auc(xs, ys)
        entry["auroc"] = round(auc, 4) if auc is not None else None
        entry["auroc_ci95"] = _bootstrap(
            len(xs),
            lambda b, xs=xs, ys=ys: roc_auc([xs[k] for k in b], [ys[k] for k in b]),
            bootstrap,
            seed + si,
        )
        if name in PROBABILITY_SOURCES:
            ece = expected_calibration_error(xs, ys, n_bins=10)
            entry["ece"] = round(ece, 4) if ece is not None else None
            entry["mean_confidence"] = round(sum(xs) / len(xs), 4)
            if reweight_prevalence is not None:
                w = weights_for(ys)
                we = weighted_ece(xs, ys, w)
                entry["ece_reweighted"] = round(we, 4) if we is not None else None
        else:
            entry["ece"] = None
            entry["ece_note"] = "not a probability; AUROC only"
        if name != BASELINE:
            common = [i for i in idx if values[i][BASELINE] is not None]
            if common:
                a = [float(values[i][name]) for i in common]  # type: ignore[arg-type]
                b = [float(values[i][BASELINE]) for i in common]  # type: ignore[arg-type]
                y = [labels_all[i] for i in common]
                auc_a, auc_b = roc_auc(a, y), roc_auc(b, y)
                if auc_a is not None and auc_b is not None:

                    def _delta(bi: list[int], a=a, b=b, y=y) -> float | None:
                        ya = [y[k] for k in bi]
                        ra = roc_auc([a[k] for k in bi], ya)
                        rb = roc_auc([b[k] for k in bi], ya)
                        return None if ra is None or rb is None else ra - rb

                    entry["paired_vs_baseline"] = {
                        "n_common": len(common),
                        "delta_auroc": round(auc_a - auc_b, 4),
                        "delta_auroc_ci95": _bootstrap(len(common), _delta, bootstrap, seed + 1000 + si),
                    }
        per_source[name] = entry

    fracs: list[float] = []
    for r in rows:
        try:
            tr = token_confidence.decode_token_trace(r.get("token_logprobs"))
        except ValueError:
            tr = None
        if tr is not None:
            fracs.append(tr.placeholder_fraction)
    fracs.sort()
    token_trace = {
        "rows_with_trace": len(fracs),
        "rows_legacy_no_trace": len(rows) - len(fracs),
        # Speculative-decoding placeholders (prob=1.0, no top-k). A high fraction
        # means full_geomean/legacy_confidence are dominated by fake certainty.
        "placeholder_fraction_median": round(fracs[len(fracs) // 2], 4) if fracs else None,
        "placeholder_fraction_max": round(fracs[-1], 4) if fracs else None,
        "rows_with_any_placeholder": sum(1 for f in fracs if f > 0),
    }
    return {
        "schema": REPORT_SCHEMA,
        "token_trace": token_trace,
        "claim_grade": "observation",
        "n_scored": len(rows),
        "accuracy": round(p_hat, 4),
        "ece_binning": "closed_top_bin_stat_tests",
        "reweight_prevalence": reweight_prevalence,
        "bootstrap": {"reps": bootstrap, "seed": seed, "method": "percentile"},
        "metric_direction": {"auroc": "higher_better", "ece": "lower_better"},
        "baseline_source": BASELINE,
        "sources": per_source,
    }


def _table(report: dict[str, Any]) -> str:
    tt = report.get("token_trace") or {}
    lines = [
        f"n_scored={report['n_scored']} accuracy={report['accuracy']} "
        f"trace_rows={tt.get('rows_with_trace')} "
        f"placeholder_frac_median={tt.get('placeholder_fraction_median')}"
    ]
    lines.append(f"{'source':26} {'n':>6} {'AUROC':>7} {'CI95':>17} {'ECE':>7} {'dAUROC':>8}")
    for name, e in report["sources"].items():
        ci = e.get("auroc_ci95")
        d = (e.get("paired_vs_baseline") or {}).get("delta_auroc")
        lines.append(
            f"{name:26} {e['n']:>6} {str(e.get('auroc', '-')):>7} "
            f"{(f'[{ci[0]},{ci[1]}]' if ci else '-'):>17} {str(e.get('ece', '-')):>7} {str(d if d is not None else '-'):>8}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("sidecars", nargs="+", type=Path, help="question_results*.jsonl file(s)")
    ap.add_argument("--out", type=Path, help="write the JSON report here (default: stdout)")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--reweight-prevalence",
        type=float,
        default=None,
        help="also report ECE reweighted to this positive-class prevalence "
        "(for a correctness-stratified probe; e.g. E7c worker_general 0.7886)",
    )
    args = ap.parse_args(argv)
    rows, stats = load_rows(args.sidecars)
    if not rows:
        print("no scored rows", file=sys.stderr)
        return 2
    report = compare(
        rows,
        reweight_prevalence=args.reweight_prevalence,
        bootstrap=args.bootstrap,
        seed=args.seed,
    )
    report["inputs"] = stats
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n")
    else:
        print(text)
    print(_table(report), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
