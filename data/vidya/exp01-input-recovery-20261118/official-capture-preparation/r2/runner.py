#!/usr/bin/python3
"""Run and check separate official and four-CPU publisher EXP01 captures."""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from capture import ARMS, P, _complete_schedule, _write_new, artifact, checked, cpu_mask
from prepare import COMMIT, IK, load, require

ROW = "vidya-exp01-proxy-official-native-20261118-r2"
OFFICIAL = P / "official"
SMOKE = P / "smoke"
REPORT = OFFICIAL / "RESULT.json"
SMOKE_REPORT = SMOKE / "RESULT.json"


def ensure_record(path, pin):
    require(artifact(path) == pin, f"raw custody mismatch: {path.name}")


def fixture(pins):
    pin = pins["smoke_fixture"]["metadata"]
    ensure_fixture = artifact(pin["path"], False)
    require(ensure_fixture == pin, "small-model fixture changed")
    return pin["path"]


def allocation(count):
    cpus = os.environ["FILLER_CPUS"]
    mask = cpu_mask(cpus)
    require(os.environ["FILLER_ID"] == ROW and len(mask) == count and os.sched_getaffinity(0) == mask
            and int(os.environ["FILLER_THREADS"]) == count, "job affinity, row or native threads differ")
    return cpus, mask


def speed(stdout, model, threads):
    cells = load(stdout)
    require(len(cells) == 2 and [(c["n_prompt"], c["n_gen"]) for c in cells] == [(512, 0), (0, 128)],
            "native bench did not provide the requested pp512/tg128 cells")
    for c in cells:
        require(c["model_filename"] == model and c["n_threads"] == threads
                and re.fullmatch(r"[0-9a-f]{7,40}", c["build_commit"]) and COMMIT.startswith(c["build_commit"])
                and all(not c.get(key) for key in ("cuda", "vulkan", "kompute", "metal", "sycl", "gpu_blas"))
                and c["n_gpu_layers"] == 999 and len(c["samples_ns"]) == len(c["samples_ts"]) == 1,
                "native bench recipe, model, sample count or CPU build differs")
        ns = c["samples_ns"][0]
        require(type(ns) is int and ns > 0 and ns == c["avg_ns"], "invalid native sample duration")
        rate = (c["n_prompt"] + c["n_gen"]) * 1e9 / ns
        require(c["avg_ts"] == float(f"{rate:.6f}") and c["samples_ts"][0] == float(f"{rate:.6g}"),
                "native throughput did not rederive")
    return cells


def launch(path, unit, mode, args, pins, mask):
    out = path / "launches" / unit
    native = load(Path(f"{out}.json"))
    tool = pins["artifacts"][mode]
    libs = {p["path"]: p for name, p in pins["artifacts"].items() if name.startswith("instrument-lib:")}
    require(native["schema"] == "epyc.exp01.launch.v1" and native["unit"] == unit
            and native["disposition"] == "complete" and native["native_rc"] == native["rc"] == 0
            and native["executable"] == tool and native["argv"] == [tool["path"], *args]
            and native["mapped_artifacts"] == libs, f"native launch pin mismatch: {unit}")
    start, end = native["started_monotonic_s"], native["ended_monotonic_s"]
    witnesses = native["samples"]
    require(all(start <= s["monotonic_s"] <= end and s["own_pid"] == native["pid"]
                and set(s["affinity"]) == mask for s in witnesses)
            and sum(libs.keys() <= set(s["mapped"]) for s in witnesses) >= 2, f"inside-launch witness mismatch: {unit}")
    for stream in ("stdout", "stderr"):
        ensure_record(Path(f"{out}.{stream}"), native[stream])
    return native, Path(f"{out}.stdout")


def bench_args(model, threads):
    return ["-m", model, "-p", "512", "-n", "128", "-r", "1", "-t", str(threads), "-o", "json"]


def quality_args(model, threads, prompt):
    return ["-m", model, "-p", prompt, "-n", "256", "--temp", "0", "--seed", "42",
            "-t", str(threads), "--no-display-prompt"]


def verify_official(out, pins):
    out = out.resolve(strict=True)
    require(out.parent == OFFICIAL and not out.is_symlink(), "unexpected official attempt")
    run, terminal = (load(out / name) for name in ("RUN.json", "TERMINAL.json"))
    alloc = run["allocation"]
    plan = run["planned"]
    mask = cpu_mask(alloc["FILLER_CPUS"])
    require(run["schema"] == "epyc.exp01.capture.v1" and terminal["mode"] == run["mode"] == "official"
            and terminal["state"] == "complete-unprojected" and terminal["rc"] == 0
            and terminal["run_id"] == run["run_id"] and not terminal["stop_file_observed"]
            and not terminal["deadline_reached"] and run["pins"] == pins
            and run["source_sha256"] == artifact(P / "SOURCE.json")["sha256"]
            and alloc["FILLER_ID"] == ROW and len(mask) == int(alloc["FILLER_THREADS"]) == 24
            and plan["launches_per_arm"] == 3 and plan["cap_s"] == 5400
            and (plan["pp"], plan["tg"]) == (512, 128) and plan["planned_looks"] == [2, 3]
            and math.isfinite(plan["launch_deadline"]) and plan["launch_deadline"] <= float(alloc["FILLER_DEADLINE"])
            and run["started_at"] <= terminal["ended_at"] <= plan["launch_deadline"],
            "official terminal, allocation or immutable launch plan differs")
    source = Path(pins["artifacts"]["items"]["path"])
    items = {item["id"]: item for item in map(json.loads, source.read_bytes().splitlines())}
    require(list(items) == plan["paired_item_ids"] and len(items) == 24,
            "official pinned item order differs")
    result = out / "results.jsonl"
    ensure_record(result, terminal["raw"])
    ensure_record(out / "SUMMARY.json", terminal["summary"])
    rows = list(map(json.loads, result.read_bytes().splitlines()))
    require(_complete_schedule(rows, plan) and rows[0]["ok"] is True, "official schedule is incomplete")
    previous = 0.0
    for row in rows:
        carrier = row["belief_capture"]
        require(carrier["schema"] == "epyc.exp01.unit_capture.v1" and carrier["mode"] == "official"
                and carrier["run_id"] == run["run_id"] and carrier["allocation"] == alloc,
                "official unit identity differs")
        kind = row.get("kind")
        if kind not in ("speed", "quality"):
            continue
        arm, unit = row["arm"], row["unit"]
        model = pins["models"][arm]["metadata"]["path"]
        require(row["cpus"] == alloc["FILLER_CPUS"] and row["threads"] == 24 and row["rc"] == 0,
                f"official native resources or exit differ: {unit}")
        ensure_record(out / "launches" / (unit + ".json"), carrier["launch"])
        if kind == "speed":
            ensure_record(out / (unit + ".json"), carrier["raw"])
            native, stdout = launch(out, unit, "bench", bench_args(model, 24), pins, mask)
            require(stdout.read_bytes() == (out / (unit + ".json")).read_bytes(), "original bench bytes differ")
            pp, tg = speed(stdout, model, 24)
            require(row["pp"] == pp["avg_ts"] and row["tg"] == tg["avg_ts"] and row["pp_n"] == 512
                    and row["tg_n"] == 128 and row["build_commit"] == tg["build_commit"] and row["gguf"] == model,
                    f"official speed unit does not match native bench: {unit}")
        else:
            item = items[row["item"]]
            item_hash = hashlib.sha256((item["prompt"] + item["expect_regex"]).encode()).hexdigest()[:16]
            require(row["item_native"] == item and row["item_hash"] == item_hash,
                    f"official item bytes do not match the fixed set: {unit}")
            native, stdout = launch(out, unit, "cli", quality_args(model, 24, item["prompt"]), pins, mask)
            answer = stdout.read_text()
            require(row["output"] == answer and row["correct"] == bool(re.search(item["expect_regex"], answer)),
                    f"official item outcome does not rederive: {unit}")
        require(run["started_at"] <= native["started_at"] <= native["ended_at"] <= terminal["ended_at"]
                and previous <= native["started_monotonic_s"], f"official launch order or interval differs: {unit}")
        previous = native["ended_monotonic_s"]
    return dict(unit_id=ROW, mode="official", state=terminal["state"], native_units=len(rows),
                attempt=str(out), terminal=artifact(out / "TERMINAL.json"))


def new_attempt(base):
    base.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=base, prefix="attempt-"))


def run_smoke(pins):
    cpus, mask = allocation(4)
    require(cpu_mask(os.environ["WS58_REGIONS"]) == mask, "publisher smoke affinity differs from keeper")
    model = fixture(pins)
    out = new_attempt(SMOKE)
    started = time.time()
    env = os.environ.copy()
    env.update(EXP01_CAPTURE_DIR=str(P), OUT=str(out), EXP01_CONTROL_END=env["FILLER_DEADLINE"],
               EXP01_OPERATOR_STOP=env["FILLER_STOPFILE"], FILLER_STOPFILE=str(out / "STOP"),
               LD_LIBRARY_PATH=f"{IK}/build/ggml/src:{IK}/build/src")
    item = json.loads(Path(pins["artifacts"]["items"]["path"]).read_text().splitlines()[0])
    tasks = [("bench", bench_args(model, 4)), ("cli", quality_args(model, 4, item["prompt"]))]
    for mode, args in tasks:
        env["EXP01_LAUNCH_UNIT"] = "smoke-" + mode
        subprocess.run([str(P / (mode + ".sh")), *args], env=env, check=True, stdout=subprocess.DEVNULL)
    report = dict(unit_id=ROW, mode="publisher-smoke", state="complete", native_units=2,
                  started_at=started, ended_at=time.time(), cpus=cpus, threads=4, attempt=str(out),
                  fixture=pins["smoke_fixture"], source=artifact(P / "SOURCE.json"),
                  item_id=item["id"], item_source=pins["artifacts"]["items"], launch_records={})
    for mode, args in tasks:
        unit = "smoke-" + mode
        _, stdout = launch(out, unit, mode, args, pins, mask)
        if mode == "bench":
            speed(stdout, model, 4)
        else:
            require(bool(stdout.read_text().strip()), "native CLI smoke returned no output")
        report["launch_records"][mode] = artifact(out / "launches" / (unit + ".json"))
    _write_new(out / "RESULT.json", report)
    pending = out / "PUBLISH-RESULT.json"
    _write_new(pending, report)
    pending.replace(SMOKE_REPORT)


def run_official(pins):
    allocation(24)
    out = new_attempt(OFFICIAL)
    # The producer requires an empty attempt, including absence of the run-local STOP.
    env = os.environ.copy()
    env.update(EXP01_CAPTURE_DIR=str(P), OUT=str(out), IK=str(IK), PP="512", TG="128",
               EXP01_OPERATOR_STOP=env["FILLER_STOPFILE"], FILLER_STOPFILE=str(out / "STOP"))
    result = subprocess.run(["/bin/bash", str(P / "pilot_r3_job.sh")], env=env)
    if result.returncode:
        _write_new(out / "FAILURE.json", dict(rc=result.returncode, state="partial-or-failed", attempt=str(out)))
        return result.returncode
    try:
        report = verify_official(out, pins)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _write_new(out / "FAILURE.json", dict(rc=4, state="partial-or-failed", attempt=str(out), reason=str(exc)))
        raise
    _write_new(REPORT, report)
    return 0


def main(action):
    if action == "smoke-complete":
        if "FILLER_SMOKE_T0" not in os.environ or not SMOKE_REPORT.is_file():
            return 1
        smoke = load(SMOKE_REPORT)
        return 0 if (smoke["unit_id"] == ROW and smoke["mode"] == "publisher-smoke"
                     and smoke["state"] == "complete" and smoke["native_units"] == 2 and smoke["threads"] == 4
                     and smoke["started_at"] >= float(os.environ["FILLER_SMOKE_T0"])
                     and cpu_mask(smoke["cpus"]) == cpu_mask(os.environ["WS58_REGIONS"])
                     and all(artifact(p["path"]) == p for p in smoke["launch_records"].values())
                     and artifact(P / "SOURCE.json") == smoke["source"]) else 1
    if action == "complete" and not REPORT.is_file():
        return 1
    pins = checked()
    fixture(pins)
    if action == "check":
        return 0
    if action == "complete":
        report = load(REPORT)
        return 0 if verify_official(Path(report["attempt"]), pins) == report else 1
    if action != "run":
        raise ValueError(f"unknown action: {action}")
    if os.environ.get("FILLER_SMOKE") == "1" and os.environ.get("FILLER_DRYRUN") == "1":
        run_smoke(pins)
        return 0
    if os.environ.get("FILLER_DRYRUN") == "1":
        raise ValueError("official capture requires an actual 24-CPU grant")
    return run_official(pins)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1]))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(1)
