#!/usr/bin/env python3
"""Run two pinned EvalPerf endpoint arms; reject partial output before comparison.

Requires a prepared EvalPlus checkout/environment and a manifest of the 118 task
IDs. This script neither installs dependencies nor starts/reloads serving stacks.
Invoke only inside an allocated row. No promotion or significance claim is made.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import urllib.request


def bounded_number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("metric must be numeric")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("metric out of range")
    return value


def summarize(native, task_ids, n_samples, min_correct, temperature):
    """Validate native rows, retaining unprofiled tasks as unknown efficiency."""
    if len(task_ids) != 118 or len(set(task_ids)) != 118:
        raise ValueError("expected exactly 118 unique pinned task IDs")
    if not 1 <= min_correct <= n_samples:
        raise ValueError("invalid sample bounds")
    if (native.get("n_samples"), native.get("min_correct"), native.get("temperature")) != (
        n_samples, min_correct, temperature
    ):
        raise ValueError("native sampling configuration drift")
    if native.get("max_profile") != min(2 * min_correct, n_samples):
        raise ValueError("native profile bound drift")
    tasks = native["eval"]
    if set(tasks) != set(task_ids):
        raise ValueError("missing or unexpected native tasks")
    solved = profiled = passed = 0
    efficiency = []
    for task in tasks.values():
        results = task["results"]
        if len(results) != n_samples or any(type(r.get("pass")) is not bool for r in results):
            raise ValueError("missing samples or invalid correctness flags")
        count = sum(r["pass"] for r in results)
        expected = 100 * count / n_samples
        if not math.isclose(bounded_number(task["pass@1"], 0, 100), expected):
            raise ValueError("correctness summary disagrees with samples")
        passed += count
        solved += count > 0
        good = []
        for result in results:
            if type(result.get("profiled")) is not bool:
                raise ValueError("invalid native profile flag")
            if not result["profiled"]:
                if any(result.get(key) is not None for key in
                       ("dps", "dps_norm", "_num_cpu_instructions")):
                    raise ValueError("unprofiled sample contains profile evidence")
                continue
            if not result["pass"]:
                raise ValueError("incorrect sample included in efficiency")
            bounded_number(result.get("_num_cpu_instructions"), 1, float("inf"))
            for key in ("dps", "dps_norm"):
                bounded_number(result.get(key), 0, 100)
            good.append(result)
        score = task.get("dps_norm")
        if score is None:
            if (task.get("dps") is not None or count >= min_correct or good
                    or task.get("n_profiled") is not None):
                raise ValueError("inconsistent missing efficiency")
            continue
        if count < min_correct:
            raise ValueError("efficiency scored below min_correct")
        bounded_number(score, 0, 100)
        bounded_number(task["dps"], 0, 100)
        if (type(task.get("n_profiled")) is not int
                or len(good) != task["n_profiled"]
                or len(good) != min(count, native["max_profile"])):
            raise ValueError("missing native profile evidence")
        for key in ("dps", "dps_norm"):
            if not math.isclose(task[key], statistics.mean(r[key] for r in good)):
                raise ValueError("efficiency summary disagrees with samples")
        profiled += 1
        efficiency.append(score)
    return {
        "tasks": len(tasks), "samples": len(tasks) * n_samples,
        "correct_samples": passed, "correctness_rate": passed / (len(tasks) * n_samples),
        "solved_tasks": solved, "profiled_tasks": profiled,
        "unknown_efficiency_tasks": len(tasks) - profiled,
        # Working convention in model-evaluation-queue, not a ratified protocol.
        # Native DPS is retained in the input; missing/failing tasks get no sentinel.
        "conditional_harmonic_dps_norm": (
            statistics.harmonic_mean(efficiency) if profiled >= 30 else None
        ),
        "claim_scope": "descriptive generated-code efficiency only",
    }


def run(config, output):
    source = Path(config["source"]).resolve()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    if git("rev-parse", "HEAD") != config["source_commit"] or git("status", "--porcelain"):
        raise ValueError("EvalPlus source must be clean at the pinned commit")
    manifest = Path(config["task_manifest"])
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != config["task_manifest_sha256"]:
        raise ValueError("task manifest drift")
    task_ids = json.loads(manifest.read_text())
    if len(task_ids) != 118 or len(set(task_ids)) != 118:
        raise ValueError("expected exactly 118 unique pinned task IDs")
    arms = config["arms"]
    if len(arms) != 2 or {a["role"] for a in arms} != {"coder", "architect"}:
        raise ValueError("requires one coder and one architect arm")
    n, minimum = config["n_samples"], config["min_correct"]
    if type(n) is not int or type(minimum) is not int or not 1 <= minimum <= n:
        raise ValueError("invalid explicit sample bounds")
    temperature = bounded_number(config["temperature"], 0, 2)
    if temperature == 0:
        raise ValueError("native sampling requires positive temperature")
    for key in ("max_new_tokens", "arm_timeout_s"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"invalid {key}")
    parallel = config["parallel"]
    if type(parallel) is not int or not 1 <= parallel <= len(os.sched_getaffinity(0)):
        raise ValueError("workers exceed inherited CPU allocation")
    # Read-only identity checks happen before either expensive generation arm.
    for arm in arms:
        request = urllib.request.Request(arm["base_url"].rstrip("/") + "/models")
        with urllib.request.urlopen(request, timeout=5) as response:
            models = json.load(response)["data"]
        if arm["model"] not in {m["id"] for m in models}:
            raise ValueError("endpoint model identity mismatch")
    output.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "PYTHONPATH": str(source), "TOKENIZERS_PARALLELISM": "false"}
    summaries = {}
    for arm in arms:
        role_dir = output / arm["role"]
        role_dir.mkdir()
        argv = [config["python"], "-m", "evalplus.evalperf", "--backend", "openai",
                "--base-url", arm["base_url"], "--model", arm["model"],
                "--root", str(role_dir), "--evalperf-type", "perf-instruct",
                "--n-samples", str(n), "--min-correct", str(minimum),
                "--max-profile", str(min(2 * minimum, n)), "--parallel", str(parallel),
                "--temperature", str(temperature), "--bs", "1",
                "--max-new-tokens", str(config["max_new_tokens"])]
        # GNU timeout owns the native process group and forwards termination to
        # its descendants, including correctness/profiling workers.
        argv = ["timeout", "--kill-after=5s", str(config["arm_timeout_s"]), *argv]
        (role_dir / "command.json").write_text(json.dumps(argv) + "\n")
        with (role_dir / "native.log").open("w") as log:
            subprocess.run(argv, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True)
        files = list(role_dir.rglob("*_evalperf_results.json"))
        if len(files) != 1:
            raise ValueError("expected exactly one full native result")
        summaries[arm["role"]] = summarize(json.loads(files[0].read_text()), task_ids,
                                              n, minimum, temperature)
        summaries[arm["role"]]["native_sha256"] = hashlib.sha256(files[0].read_bytes()).hexdigest()
        (output / "checkpoint.json").write_text(json.dumps(summaries, indent=2) + "\n")
    return {"status": "COMPLETE", "source_commit": config["source_commit"], "arms": summaries,
            "verdict": "descriptive only; no automatic instrument adoption or role change"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run(json.loads(args.config.read_text()), args.output.resolve())
    (args.output / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
