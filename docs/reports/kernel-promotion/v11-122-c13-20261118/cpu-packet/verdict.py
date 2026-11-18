"""Validate two llama-bench records per arm and evaluate completed pairs."""

import math
from statistics import median

ARMS = ("nollg", "llg")
ORDER = (ARMS, ARMS[::-1], ARMS)
METRICS = ("pp512", "tg128")
RULE = (
    "AB, BA, AB, with A=nollg and B=llg. FAIL on two pairs with >2% loss "
    "for the same arm and metric, relative to the other arm. After all three pairs, "
    "PASS when both absolute median paired deltas are <1% and within their respective "
    "noise bands (median larger within-pair repeat CV, floor 0.5%). Otherwise "
    "INCONCLUSIVE at three pairs or RUNNING at an earlier checkpoint."
)


def validate(records, prompt, generation, repeats, threads, model):
    expected = {(prompt, 0): f"pp{prompt}", (0, generation): f"tg{generation}"}
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError("expected exactly two benchmark records")
    metrics = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("benchmark record must be an object")
        prompt_tokens, generation_tokens = record.get("n_prompt"), record.get("n_gen")
        if type(prompt_tokens) is not int or type(generation_tokens) is not int:
            raise ValueError("invalid prompt/generation counts")
        metric = expected.get((prompt_tokens, generation_tokens))
        if metric is None or metric in metrics:
            raise ValueError("unexpected or duplicate benchmark metric")
        identity = (record.get("model_filename"), record.get("n_threads"), record.get("devices"),
                    record.get("n_gpu_layers"), record.get("backends"), record.get("gpu_info"),
                    record.get("flash_attn"), record.get("n_depth"))
        if identity != (model, threads, "none", 0, "CPU", "", 1, 0):
            raise ValueError(f"{metric}: benchmark settings differ from CPU recipe: {identity!r}")
        mean = record.get("avg_ts")
        deviation = record.get("stddev_ts")
        samples = record.get("samples_ts")
        if not valid_number(mean, positive=True) or not valid_number(deviation):
            raise ValueError(f"{metric}: invalid throughput or repeat standard deviation")
        if not isinstance(samples, list) or len(samples) != repeats or not all(
            valid_number(sample, positive=True) for sample in samples
        ):
            raise ValueError(f"{metric}: expected {repeats} finite positive repeat samples")
        metrics[metric] = (mean, deviation)
    return metrics


def valid_number(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (
        value > 0 if positive else value >= 0
    )


def checkpoint(pairs):
    if not 1 <= len(pairs) <= len(ORDER):
        raise ValueError("checkpoint requires one to three complete adjacent pairs")
    paired = []
    for pair, order in zip(pairs, ORDER):
        measurements = {}
        for metric in METRICS:
            a, a_sd = pair["nollg"][metric]
            b, b_sd = pair["llg"][metric]
            values = {
                "nollg_ts": a, "llg_ts": b, "nollg_stddev_ts": a_sd, "llg_stddev_ts": b_sd,
                "delta_pct": 100 * (b / a - 1),
                "nollg_loss_pct": 100 * (1 - a / b),
                "llg_loss_pct": 100 * (1 - b / a),
                "within_cv_pct": 100 * max(a_sd / a, b_sd / b),
            }
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError(f"{metric}: nonfinite paired statistic")
            # Multiplicative comparison keeps an exact 98-to-100 pair on the boundary.
            values["nollg_drop_gt2"] = a < 0.98 * b
            values["llg_drop_gt2"] = b < 0.98 * a
            measurements[metric] = values
        paired.append({"order": order, "metrics": measurements})

    summary = {}
    for metric in METRICS:
        values = [pair["metrics"][metric] for pair in paired]
        summary[metric] = {
            "median_delta_pct": median(x["delta_pct"] for x in values),
            "noise_band_pct": max(0.5, median(x["within_cv_pct"] for x in values)),
            "drops_gt2": {arm: sum(x[f"{arm}_drop_gt2"] for x in values) for arm in ARMS},
        }
    failed = any(count >= 2 for item in summary.values() for count in item["drops_gt2"].values())
    full = len(pairs) == len(ORDER)
    passed = full and all(
        abs(item["median_delta_pct"]) < 1 and abs(item["median_delta_pct"]) <= item["noise_band_pct"]
        for item in summary.values()
    )
    verdict = "FAIL" if failed else "PASS" if passed else "INCONCLUSIVE" if full else "RUNNING"
    return {"pairs": paired, "n_pairs": len(pairs), "summary": summary, "verdict": verdict,
            "final": failed or full, "rule": RULE}


def smoke_fixtures():
    def pair(a, b, sd=0.1):
        return {
            "nollg": {metric: (a, sd) for metric in METRICS},
            "llg": {metric: (b, sd) for metric in METRICS},
        }

    for pairs, expected in (
        ([pair(100, 100)] * 2, "RUNNING"),
        ([pair(100, 100)] * 3, "PASS"),
        ([pair(100, 97)] * 2, "FAIL"),
        ([pair(97, 100)] * 2, "FAIL"),
        ([pair(98, 100)] * 2, "RUNNING"),
        ([pair(100, 98)] * 2, "RUNNING"),
        ([pair(100, 102.02)] * 2, "RUNNING"),
        ([pair(100, 97), pair(97, 100), pair(100, 100)], "PASS"),
        ([pair(100, 100.75)] * 3, "INCONCLUSIVE"),
        ([pair(100, 100.75, 0.9)] * 3, "PASS"),
        ([pair(100, 101, 2)] * 3, "INCONCLUSIVE"),
    ):
        actual = checkpoint(pairs)["verdict"]
        if actual != expected:
            raise ValueError(f"verdict fixture expected {expected}, got {actual}: {pairs}")

    base = {"model_filename": "fixture", "n_threads": 4, "devices": "none", "n_gpu_layers": 0,
            "backends": "CPU", "gpu_info": "", "flash_attn": 1, "n_depth": 0, "avg_ts": 100.0,
            "stddev_ts": 0.0, "samples_ts": [100.0]}
    pp = {**base, "n_prompt": 8, "n_gen": 0}
    tg = {**base, "n_prompt": 0, "n_gen": 2}
    validate([pp, tg], 8, 2, 1, 4, "fixture")
    for records in (
        [pp], [pp, pp], [pp, {}], [pp, {**tg, "avg_ts": float("inf")}],
        [pp, {**tg, "stddev_ts": float("nan")}], [pp, {**tg, "avg_ts": 0}],
        [pp, {**tg, "stddev_ts": -1}], [pp, {**tg, "samples_ts": [float("nan")]}],
    ):
        try:
            validate(records, 8, 2, 1, 4, "fixture")
        except ValueError:
            continue
        raise ValueError(f"invalid fixture was accepted: {records}")
