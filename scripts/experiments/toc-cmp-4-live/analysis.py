"""Analyze one model's TOC-CMP-4 option (a) records.

Input is a JSON object with a "runs" array or a .jsonl file. Each row has point_id, stratum
(early/middle/late), arm, zero-based repeat, and boolean valid. Valid rows
have baps in [0, 1], boolean or null correct, and nonnegative wall_s.
Null correct means the external grader did not supply a score. A row with
point_id, stratum, valid=false, and void_point=true or status="void_point"
excludes all runs at that point. Other invalid rows retain their arm and
repeat and fail completeness.
Include only the preregistered arms from one model. Preserve repeat indices
because the runner uses the same sampling seed across arms at each index.

Use calculate_baps() to normalize action-level data before making a valid
row. No post-boundary actions means BAPS is undefined.
"""

import argparse
import json
import math
import random
import statistics
from collections import Counter
from itertools import combinations
from pathlib import Path

ARMS = ("summary_only", "pointer_only", "prune_pointer")
STRATA = ("early", "middle", "late")
CONTRASTS = tuple(combinations(ARMS, 2))
CONTRAST_INDICES = tuple(combinations(range(len(ARMS)), 2))
ALPHA = 0.05
MDE = 0.10
BOOTSTRAP_DRAWS = 10_000
DEFAULT_SEED = 20261109


def calculate_baps(post_boundary_actions):
    """Return BAPS and deliberate rereads among the first five ordered actions.

    Action flags blocked, error and deliberate_reread are boolean. A reread
    still occupies a slot in the first-five window and denominator.
    """
    window = post_boundary_actions[:5]
    if not window:
        return {"baps": None, "deliberate_rereads": 0}

    blocked = 0
    rereads = 0
    for action in window:
        if any(type(action.get(flag)) is not bool
               for flag in ("blocked", "error", "deliberate_reread")):
            raise ValueError("action flags blocked, error and deliberate_reread must be boolean")
        if action["deliberate_reread"]:
            rereads += 1
        elif action["blocked"] or action["error"]:
            blocked += 1
    return {"baps": blocked / len(window), "deliberate_rereads": rereads}


def pass3(correct, repeats):
    """Estimate the probability of three correct attempts, or return UNKNOWN."""
    if repeats < 3:
        return "UNKNOWN"
    return math.comb(correct, 3) / math.comb(repeats, 3)


def _finite(row, field, upper=None):
    value = row.get(field)
    if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
            or (upper is not None and value > upper)):
        raise ValueError(f"{row['point_id']}: invalid {field}")
    return value


def _paired_points(runs, mode):
    strata = {}
    voided = set()
    for row in runs:
        if not isinstance(row, dict):
            raise ValueError("each runs entry must be an object")  # noqa: TRY004
        point_id = row.get("point_id")
        stratum = row.get("stratum")
        if not isinstance(point_id, str) or not point_id or stratum not in STRATA:
            raise ValueError("each row needs a point_id and a registered stratum")
        if strata.setdefault(point_id, stratum) != stratum:
            raise ValueError(f"{point_id}: inconsistent boundary stratum")
        if type(row.get("valid")) is not bool or type(row.get("void_point", False)) is not bool:
            raise ValueError(f"{point_id}: validity flags must be boolean")
        if row.get("void_point") or row.get("status") == "void_point":
            if row["valid"]:
                raise ValueError(f"{point_id}: a void marker cannot be valid")
            voided.add(point_id)

    groups = {point_id: {arm: {} for arm in ARMS} for point_id in sorted(strata)
              if point_id not in voided}
    for row in runs:
        point_id = row["point_id"]
        if point_id in voided:
            continue
        arm = row.get("arm")
        repeat = row.get("repeat")
        if arm not in ARMS or type(repeat) is not int or repeat < 0:
            raise ValueError(f"{point_id}: invalid arm or repeat")
        if not row["valid"]:
            raise ValueError(f"{point_id}: invalid run ({arm}, repeat {repeat})")
        if repeat in groups[point_id][arm]:
            raise ValueError(f"{point_id}: duplicate run ({arm}, repeat {repeat})")
        baps = _finite(row, "baps", upper=1)
        wall_s = _finite(row, "wall_s")
        if "correct" not in row or (row["correct"] is not None and type(row["correct"]) is not bool):
            raise ValueError(f"{point_id}: correct must be boolean or null")
        groups[point_id][arm][repeat] = (baps, row["correct"], wall_s)

    points = {stratum: [] for stratum in STRATA}
    repeat_counts = set()
    for point_id, arms in groups.items():
        repeats = tuple(sorted(arms[ARMS[0]]))
        if not repeats or any(tuple(sorted(arms[arm])) != repeats for arm in ARMS):
            raise ValueError(f"{point_id}: mismatched repeat IDs across arms")
        if repeats != tuple(range(len(repeats))):
            raise ValueError(f"{point_id}: missing zero-based repeat IDs")
        repeat_counts.add(len(repeats))
        points[strata[point_id]].append(tuple(
            tuple(arms[arm][repeat] for repeat in repeats) for arm in ARMS
        ))

    if mode == "pilot":
        if len(groups) != 8 or repeat_counts != {4}:
            raise ValueError("pilot requires 8 complete paired points with 4 repeats per arm")
    elif (any(len(group) < 10 for group in points.values()) or len(repeat_counts) != 1
          or not repeat_counts <= set(range(8, 13))):
        raise ValueError("confirmatory requires at least 10 complete paired points per stratum "
                         "and a common 8–12 repeats per arm")
    return points, Counter(strata[point_id] for point_id in voided)


def _point_metrics(point, indices, complete_scores):
    metrics = []
    for arm, complete in zip(point, complete_scores):
        repeats = len(indices)
        baps = sum(arm[i][0] for i in indices) / repeats
        if complete:
            correct = sum(arm[i][1] for i in indices)
            metrics.append((baps, correct / repeats, pass3(correct, repeats)))
        else:
            metrics.append((baps,))
    return tuple(metrics)


def _summarize(point_metrics):
    arms = tuple(zip(*point_metrics))
    arm_means = [
        tuple(statistics.fmean(values) for values in zip(*arm)) for arm in arms
    ]
    differences = [
        statistics.fmean(a[0] - b[0] for a, b in zip(arms[left], arms[right]))
        for left, right in CONTRAST_INDICES
    ]
    return arm_means, differences


def _percentile(ordered, probability):
    rank = probability * (len(ordered) - 1)
    lower = int(rank)
    weight = rank - lower
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def _interval(ordered, alpha=ALPHA):
    return [_percentile(ordered, alpha / 2), _percentile(ordered, 1 - alpha / 2)]


def _excludes_zero(interval):
    return interval[0] > 0 or interval[1] < 0


def _holm_p_values(samples):
    """Apply Holm's correction to two-sided empirical bootstrap tail areas."""
    count = len(samples)
    tail_areas = [
        min(1.0, 2 * (1 + min(sum(value <= 0 for value in sample),
                              sum(value >= 0 for value in sample))) / (len(sample) + 1))
        for sample in samples
    ]
    ranked = sorted(range(count), key=tail_areas.__getitem__)
    adjusted = [0.0] * count
    previous = 0.0
    for rank, index in enumerate(ranked):
        previous = min(1.0, max(previous, (count - rank) * tail_areas[index]))
        adjusted[index] = previous
    return adjusted


def _bootstrap(points, complete_scores, seed, draws):
    rng = random.Random(seed)
    arm_samples = [[[], [], []] for _ in ARMS]
    contrast_samples = [[] for _ in CONTRASTS]
    for _ in range(draws):
        resampled = []
        for group in points.values():
            for _ in group:
                point = rng.choice(group)
                repeats = len(point[0])
                indices = [rng.randrange(repeats) for _ in range(repeats)]
                resampled.append(_point_metrics(point, indices, complete_scores))
        arm_means, differences = _summarize(resampled)
        for metrics, samples in zip(arm_means, arm_samples):
            for value, sample in zip(metrics, samples):
                sample.append(value)
        for difference, sample in zip(differences, contrast_samples):
            sample.append(difference)
    return arm_samples, [sorted(sample) for sample in contrast_samples]


def analyze(runs, mode, *, seed=DEFAULT_SEED, draws=BOOTSTRAP_DRAWS):
    if mode not in ("pilot", "confirmatory"):
        raise ValueError("mode must be pilot or confirmatory")
    if not isinstance(runs, list):
        raise ValueError("runs must be an array")  # noqa: TRY004
    points, voids = _paired_points(runs, mode)
    all_points = [point for group in points.values() for point in group]
    repeats = len(all_points[0][0])
    total_per_arm = len(all_points) * repeats
    scored = [sum(row[1] is not None for point in all_points for row in point[arm])
              for arm in range(len(ARMS))]
    complete_scores = [mode == "confirmatory" and count == total_per_arm for count in scored]
    observed = [_point_metrics(point, range(repeats), complete_scores) for point in all_points]
    report = {
        "mode": mode,
        "baps_direction": "lower_is_better",
        "points": len(all_points),
        "repeats_per_arm": repeats,
        "strata": {
            stratum: {
                "included": len(group),
                "voided": voids[stratum],
                "void_rate": voids[stratum] / (len(group) + voids[stratum])
                if group or voids[stratum] else None,
            }
            for stratum, group in points.items()
        },
        "base_baps": statistics.mean(point[0][0] for point in observed),
    }
    if mode == "pilot":
        durations = [row[2] for point in all_points for arm in point for row in arm]
        report["run_wall_s"] = {
            "count": len(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
        }
        report["paired_difference_sd"] = {
            f"{a} - {b}": statistics.stdev(point[left][0] - point[right][0] for point in observed)
            for (a, b), (left, right) in zip(CONTRASTS, CONTRAST_INDICES)
        }
        if any(not group for group in points.values()):
            report["sd_scope"] = (
                "The pilot SD covers sampled strata only and cannot assess the MDE across all strata."
            )
        return report

    if type(draws) is not int or draws < 2:
        raise ValueError("bootstrap needs at least two draws")
    arm_means, differences = _summarize(observed)
    arm_samples, contrast_samples = _bootstrap(points, complete_scores, seed, draws)
    adjusted = _holm_p_values(contrast_samples)
    report["bootstrap"] = {"seed": seed, "draws": draws}
    report["minimum_detectable_effect"] = MDE
    report["arms"] = {}
    for arm, metrics, samples, count in zip(ARMS, arm_means, arm_samples, scored):
        arm_report = {
            name: {"mean": value, "interval_95": _interval(sorted(sample))}
            for name, value, sample in zip(("baps", "accuracy", "pass3"), metrics, samples)
        }
        for metric in ("accuracy", "pass3"):
            arm_report.setdefault(metric, {"mean": "UNKNOWN", "interval_95": None})
            arm_report[metric].update(scored_repeats=count, total_repeats=total_per_arm)
        report["arms"][arm] = arm_report
    floor = all(metrics[0] == 0 for metrics in arm_means)
    report["floor_effect"] = floor
    report["contrasts"] = {}
    for index, ((left, right), mean, sample) in enumerate(
        zip(CONTRASTS, differences, contrast_samples)
    ):
        # Bonferroni gives conservative simultaneous intervals. Require one
        # to exclude zero as well as passing the Holm zero-null test.
        interval = _interval(sample, ALPHA / len(CONTRASTS))
        rejected = adjusted[index] <= ALPHA and _excludes_zero(interval)
        decision = "no_effect_established"
        if floor:
            decision = "floor_effect"
        elif rejected:
            meets_mde = abs(mean) >= MDE or math.isclose(abs(mean), MDE, rel_tol=1e-12)
            decision = "effect" if meets_mde else "below_mde"
        report["contrasts"][f"{left} - {right}"] = {
            "mean_difference": mean,
            "interval_95": _interval(sample),
            "bonferroni_interval_95_familywise": interval,
            "holm_adjusted_bootstrap_p": adjusted[index],
            "decision": decision,
        }
    return report


def _load_runs(path):
    with path.open() as source:
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in source if line.strip()]
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError("input must be an object with a runs array")  # noqa: TRY004
    return payload.get("runs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("pilot", "confirmatory"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    try:
        result = analyze(_load_runs(args.input), args.mode, seed=args.seed)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
