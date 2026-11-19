#!/usr/bin/python3
"""Grant-only historical C5 elementwise comparison."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from uuid import uuid4

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "scripts" / "vidya"))
from adapters import gpu_pool_native as capture
from claim_tuple import grade

# Proposed row identifier, independent of invocation timestamps.
ROW = "ni-gpu-pool-elementwise-20261118-v6"
FAMILY = "elementwise"
COMMIT = "c72ec82f5417bb2937310326120f149b665e8400"
SEEDS = tuple(range(2026102600, 2026102632))
SMOKE_SEEDS = (2026102603,)
TARGET_PER_OP = {"NORM": 10, "SUM": 1, "SUM_ROWS": 6}
OPS = list(TARGET_PER_OP)
MAX_VRAM = 8 * 2**30
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
CPUS = set(range(184, 192))
REGIONS = "mi210_0,184-191"
BIN = HERE / "candidate/bin/test-backend-ops"
DSOS = {HERE / "candidate/bin" / f"libggml{name}.so.0" for name in ("", "-hip", "-base", "-cpu")}
HIP = HERE / "candidate/bin/libggml-hip.so.0"
SHIM = HERE / "candidate/nprocs_shim.so"
SNAPSHOT = HERE / "source/c5-test-backend-ops.cpp"
LINKAGE = HERE / "verify_ggml_linkage.sh"
CASE_PLAN = HERE / "case-plan.tsv"
CONTROL_PLAN = HERE / "control-plan.tsv"
CONTROLS = HERE / "test_run_elementwise.py"
HISTORICAL = HERE / "historical-reference.json"
ENV = {
    "BLIS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "SHIM_NPROCS": "2", "LD_PRELOAD": str(SHIM),
    "LD_LIBRARY_PATH": f"{BIN.parent}:/opt/rocm/lib", "HIP_VISIBLE_DEVICES": "0",
    "ROCR_VISIBLE_DEVICES": "0", "HSA_OVERRIDE_CPU_AFFINITY_DEBUG": "0",
    "GGML_CUDA_DISABLE_GRAPHS": "1", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
}
PINNED = {
    BIN, *DSOS, SHIM, SNAPSHOT, LINKAGE, CASE_PLAN, CONTROL_PLAN, CONTROLS, HISTORICAL,
    HERE / "prepare_historical_reference.py", HERE / "source/SHA256SUMS", HERE / "source/PROVENANCE.md",
    Path(capture.__file__), HERE / "scripts/vidya/claim_tuple.py", HERE / "scripts/vidya/canonical.py",
    Path(__file__).resolve(), HERE / "launch.sh", HERE / "spec.json",
}


def argv_for(seed, op, params):
    return [str(BIN), "test", "-b", "ROCm0", "-o", op, "-p", params, "-j", "1", "--suite-seed", str(seed)]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned_inputs():
    lines = (HERE / "PINNED.sha256").read_text().splitlines()
    pins = {HERE / name: digest for digest, name in (line.split("  ", 1) for line in lines)}
    require(set(pins) == PINNED and len(lines) == len(PINNED), "wrong prepared input set")
    for path, digest in pins.items():
        require(not path.is_symlink() and sha(path) == digest, f"pinned bytes changed: {path}")
    for dso in DSOS:
        require(dso.with_suffix("").resolve() == dso, f"wrong native loader alias: {dso}")
    return pins


def preflight():
    pins = pinned_inputs()
    read_case_plan()
    linkage = subprocess.run(
        ["/bin/bash", str(LINKAGE), str(BIN), str(BIN.parent)],
        env={**ENV, "LD_PRELOAD": ""}, check=True, capture_output=True, text=True,
    )
    require("PASS:" in linkage.stdout, "ggml linkage did not pass")
    knob = b"GGML_CUDA_DISABLE_GRAPHS"
    with HIP.open("rb") as stream:
        import mmap
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as content:
            require(content.find(knob) >= 0, "compiled graphs-off knob absent")
    probe = subprocess.run(
        ["/usr/bin/python3", "-BI", "-c",
         "import ctypes; fn=ctypes.CDLL('libstdc++.so.6')._ZNSt6thread20hardware_concurrencyEv;"
         "fn.restype=ctypes.c_uint; print(fn())"],
        env=ENV, check=True, capture_output=True, text=True,
    )
    require(probe.stdout.strip() == "2", "pinned shim did not cap hardware_concurrency")
    return pins, linkage.stdout + linkage.stderr


def read_case_plan():
    plan = {op: {} for op in OPS}
    for path, expected_role in ((CASE_PLAN, "UNSUPPORTED"), (CONTROL_PLAN, "PASS")):
        for line in path.read_text().splitlines():
            op, status, params = line.split("\t")
            require(op in plan and status == expected_role and params and params not in plan[op],
                    "unknown or duplicate planned case")
            plan[op][params] = status
    for op, targets in TARGET_PER_OP.items():
        require(Counter(plan[op].values()) == Counter({"UNSUPPORTED": targets, "PASS": 1}),
                f"planned {op} cases differ from the original support partition")
    history = json.loads(HISTORICAL.read_text())
    original_logs = history["original_log_sha256"]
    require(history["seeds"] == list(SEEDS) and history["target_cases_per_seed"] == TARGET_PER_OP
            and history["control_cases_per_seed"] == dict.fromkeys(OPS, 1)
            and history["target_plan_sha256"] == sha(CASE_PLAN)
            and history["control_plan_sha256"] == sha(CONTROL_PLAN)
            and set(original_logs) == {f"logs/{op}-{seed}.log" for seed in SEEDS for op in OPS}
            and all(re.fullmatch(r"[a-f0-9]{64}", digest) for digest in original_logs.values()),
            "historical reference differs from the selected workload")
    return plan


def selection(case_plan, pins, *, smoke):
    seeds = SMOKE_SEEDS if smoke else SEEDS
    selectors = {op: "^(?:" + "|".join(map(re.escape, case_plan[op])) + ")$" for op in OPS}
    return {
        "row_id": ROW, "smoke": smoke, "seeds": list(seeds),
        "inputs": {path.name: pins[path] for path in (CASE_PLAN, CONTROL_PLAN, HISTORICAL)},
        "target_cases_per_seed": TARGET_PER_OP, "control_cases_per_seed": dict.fromkeys(OPS, 1),
        "invocations": [
            {"seed": seed, "op": op, "argv": argv_for(seed, op, selectors[op]),
             "generated_expected": len(case_plan[op])}
            for seed in seeds for op in OPS
        ],
    }


def identity(pins):
    return {
        "source": {"commit": COMMIT, "removed_worktree_dirty_state": "UNKNOWN",
                   "snapshot": str(SNAPSHOT), "snapshot_sha256": pins[SNAPSHOT],
                   "build_manifest": str(HERE / "source/SHA256SUMS"),
                   "build_manifest_sha256": pins[HERE / "source/SHA256SUMS"],
                   "build_provenance": str(HERE / "source/PROVENANCE.md"),
                   "build_provenance_sha256": pins[HERE / "source/PROVENANCE.md"]},
        "artifacts": [{"path": str(path), "sha256": pins[path]} for path in sorted({BIN, *DSOS})],
        "shim": {"path": str(SHIM), "sha256": pins[SHIM], "SHIM_NPROCS": 2,
                 "original_source_digest_receipt": "51080dff80b0b8a72b7a41ce878f093eff0f13e739fee93d3490421c8d1041e6",
                 "later_recreated_source_matches_receipt": False},
    }


def grant():
    stop = Path(os.environ["FILLER_STOPFILE"])
    base = Path(os.environ["FILLER_DRYRUN_DIR"]) if os.environ.get("FILLER_DRYRUN") == "1" else FLAGS
    require(os.environ["FILLER_ID"] == ROW and os.environ["FILLER_CPUS"] == "184-191", "wrong filler identity")
    require(stop == (base / "stop" if base != FLAGS else HERE / "STOP"), "wrong STOP path")
    path = base / "grants" / (ROW + ".grant")
    record = dict(part.split("=", 1) for part in path.read_text().split() if "=" in part)
    start, end = (capture.timestamp(record[key]).timestamp() for key in ("start", "end"))
    require(record["regions"] == REGIONS and start <= time.time() < end, "invalid exact GPU grant")
    require(os.sched_getaffinity(0) == CPUS, "driver did not inherit exact grant CPU affinity")
    deadline = min(float(os.environ["FILLER_DEADLINE"]), end - 90)
    require(start < deadline <= end - 90, "invalid capture deadline")
    return stop, deadline, path, record


def guard(stop, deadline):
    require(not stop.exists() and not list(FLAGS.glob("HOLD_*")), "STOP or host HOLD")
    require(time.time() < deadline, "capture deadline reached")


def mask_set(mask):
    cpus = set()
    for item in mask.split(","):
        lo, _, hi = item.partition("-")
        cpus.update(range(int(lo), int(hi or lo) + 1))
    return cpus


def file_identity(path):
    stat = path.stat()
    return [os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino]


def process_birth(proc):
    fields = (proc / "stat").read_text().rsplit(") ", 1)[1].split()
    return None if fields[0] in {"X", "Z"} else int(fields[19])


def sample(pid, expected_maps):
    proc = Path(f"/proc/{pid}")
    try:
        birth = process_birth(proc)
    except (FileNotFoundError, ProcessLookupError):
        return None
    if birth is None:
        return None
    masks = {}
    complete = True
    for task in (proc / "task").glob("*/status"):
        try:
            line = re.search(r"^Cpus_allowed_list:\s*(.+)$", task.read_text(), re.M)
        except (FileNotFoundError, ProcessLookupError):
            complete = False
            continue
        require(line and mask_set(line[1]) <= CPUS, f"escaped task {task}")
        masks[task.parent.name] = line[1]
    kfd = Path(f"/sys/class/kfd/kfd/proc/{pid}")
    vram = {}
    found_maps = {}
    try:
        for counter in kfd.glob("vram*"):
            try:
                vram[counter.name] = int(counter.read_text())
            except FileNotFoundError:
                continue
        for line in (proc / "maps").read_text().splitlines():
            cols = line.split(maxsplit=5)
            if len(cols) != 6 or not any(name in cols[5] for name in ("/libggml", "/nprocs_shim.so", "/test-backend-ops")):
                continue
            path = str(Path(cols[5]).resolve(strict=True))
            mapped = [*(int(part, 16) for part in cols[3].split(":")), int(cols[4])]
            require(path in expected_maps and mapped == expected_maps[path], f"unbound runtime map: {line}")
            found_maps[path] = mapped
    except (FileNotFoundError, ProcessLookupError):
        try:
            still_live = process_birth(proc) == birth
        except (FileNotFoundError, ProcessLookupError):
            still_live = False
        if still_live:
            raise
        return None
    observed = time.time()
    kfd_present = kfd.exists()
    try:
        if process_birth(proc) != birth:
            return None
    except (FileNotFoundError, ProcessLookupError):
        return None
    return {"time": observed, "pid": pid, "birth_ticks": birth, "task_masks": masks, "kfd": kfd_present,
            "complete": complete,
            "vram_bytes": vram, "maps": found_maps}


def qualified(run, expected_maps):
    samples = run["residency_samples"]
    require(type(run["birth_ticks"]) is int and run["birth_ticks"] > 0,
            "missing native process birth identity")
    require(all(run["started_epoch"] <= item["time"] <= run["ended_epoch"] and item["pid"] == run["pid"]
                and item["birth_ticks"] == run["birth_ticks"]
                and all(set() < mask_set(mask) <= CPUS for mask in item["task_masks"].values())
                and all(path in expected_maps and expected_maps[path] == proof for path, proof in item["maps"].items())
                and all(type(n) is int and 0 <= n for n in item["vram_bytes"].values())
                for item in samples), "sample window, affinity, map or VRAM custody fails")
    return {item["time"] for item in samples if item["kfd"] is True and item["complete"] is True
            and str(run["pid"]) in item["task_masks"]
            and 0 < sum(item["vram_bytes"].values()) <= MAX_VRAM and item["maps"] == expected_maps}


def output_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def invocation_stem(invocation):
    return f"{invocation['op']}-{invocation['seed']}"


def run_native(out, invocation, stop, deadline, expected_maps):
    op, argv = invocation["op"], invocation["argv"]
    log = out / (invocation_stem(invocation) + ".log")
    guard(stop, deadline)
    start = time.time()
    samples = []
    with log.open("x") as stream:
        stream.write("ARGV " + json.dumps(argv) + "\n")
        stream.flush()
        child = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                                 env={**ENV, "FILLER_ID": ROW, "FILLER_STOPFILE": str(stop)})
        try:
            birth = process_birth(Path(f"/proc/{child.pid}"))
            with Path(os.environ["FILLER_PIDFILE"]).open("a") as pidfile:
                pidfile.write(f"{child.pid}\n")
            while child.poll() is None:
                guard(stop, deadline)
                current = sample(child.pid, expected_maps)
                if current is not None:
                    require(sum(current["vram_bytes"].values()) <= MAX_VRAM, "own PID VRAM guard exceeded")
                    samples.append(current)
                time.sleep(0.02)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            rc = child.wait()
            os.fsync(stream.fileno())
    end = time.time()
    require(not Path(f"/proc/{child.pid}").exists(), "owned native child still present")
    clean_log = re.sub(r"\x1b\[[0-9;]*m", "", log.read_text())
    lines = [line for line in clean_log.splitlines() if line.startswith(f"  {op}(")]
    return {**invocation, "status": "native_exit_recorded", "pid": child.pid, "birth_ticks": birth, "rc": rc,
           "started_epoch": start, "ended_epoch": end, "log": str(log), "log_sha256": sha(log),
           "observed": len(lines), "passed": sum(line.endswith("OK") for line in lines),
           "unsupported": sum("not supported" in line for line in lines),
           "failed": [line for line in lines if not line.endswith("OK") and "not supported" not in line],
           "residency_samples": samples}


def execute(out, grant_info, pins, linkage, *, smoke):
    stop, deadline, grant_path, grant_record = grant_info
    guard(stop, deadline)
    out.mkdir()
    expected_maps = {str(path): file_identity(path) for path in sorted({BIN, *DSOS, SHIM})}
    candidate = identity(pins)
    case_plan = read_case_plan()
    plan = selection(case_plan, pins, smoke=smoke)
    selection_path = out / "selection.json"
    output_json(selection_path, plan)
    selection_sha256 = sha(selection_path)
    request = capture.begin(FAMILY, ROW, candidate, OPS, producer=__file__)
    output_json(out / "request.json", request)
    (out / "linkage.log").write_text(linkage)
    runs = []
    for invocation in plan["invocations"]:
        stem = invocation_stem(invocation)
        run = run_native(out, invocation, stop, deadline, expected_maps)
        output_json(out / f"{stem}.terminal.json", run)
        summary = check_run(out, run, invocation, expected_maps, case_plan[invocation["op"]])
        output_json(out / f"{stem}.summary.json", summary)
        require(summary["control_pass"] and not summary["missing"], f"{stem}: incomplete custody or coverage")
        print(f"{stem}: native terminal and residency verified", flush=True)
        runs.append(run)
    guard(stop, deadline)
    require(pinned_inputs() == pins, "candidate, source or shim bytes changed")
    require(sha(selection_path) == selection_sha256, "prospective selection changed")
    target_count = sum(TARGET_PER_OP.values()) * len(plan["seeds"])
    control_count = len(runs)
    record = {
        **candidate, "schema": capture.NATIVE, "row_id": ROW, "model_free": True, "seeds": plan["seeds"],
        "selection_sha256": selection_sha256, "historical_reference_sha256": pins[HISTORICAL],
        "invocation_token": request["invocation_token"], "runs": runs,
        "scope": f"C5 candidate, {target_count} exact historical target/seed pairs and {control_count} separately tagged original residency controls",
        "proposition": f"Native case census for {target_count} selected targets. {control_count} separate residency controls exercise in-process allocation.",
        "claim_limits": [capture.LIMIT], "environment": ENV, "expected_maps": expected_maps,
        "grant": {"path": str(grant_path), "record": grant_record, "deadline_epoch": deadline, "smoke": smoke},
        "preflight": {"linkage_log_sha256": sha(out / "linkage.log"), "shim_threads": 2,
                      "graphs_disabled": True}, "owned_pid_reaped": True,
    }
    receipt = out / "belief.json"
    capture.write_capture(receipt, request, record)
    return check_capture(out, pins, smoke=smoke)


def check_run(out, run, invocation, expected_maps, case_plan):
    op = invocation["op"]
    require(all(run[key] == value for key, value in invocation.items())
            and run["log"] == str(out / (invocation_stem(invocation) + ".log"))
            and run["status"] == "native_exit_recorded", "native invocation differs from the prepared selection")
    capture.log_counts(run)
    log = re.sub(r"\x1b\[[0-9;]*m", "", Path(run["log"]).read_text())
    backend = re.findall(r"^Backend [0-9]+/[0-9]+: ROCm0\n  Device description: AMD Instinct MI210\n(.*?)^  Backend ROCm0: (OK|FAIL) *$", log, re.M | re.S)
    require(len(backend) == 1, "missing or ambiguous MI210 ROCm0 backend terminal identity")
    backend_status = backend[0][1]
    require(type(run["rc"]) is int and run["rc"] == (0 if backend_status == "OK" else 1),
            "ROCm0 terminal disagrees with native process exit")
    prefix = f"  {op}("
    lines = [line for line in backend[0][0].splitlines() if line.startswith(prefix)]
    require(lines == [line for line in log.splitlines() if line.startswith(prefix)], "case records outside MI210 backend")
    actual = {}
    for line in lines:
        match = re.fullmatch(r"(.*)\): (.*)", line[len(prefix):])
        require(match and match[1] in case_plan, f"native {op} case outside selection: {line}")
        require(match[1] not in actual, f"duplicate native {op} case")
        actual[match[1]] = match[2].strip()
    # A missing native case is a coverage gap, not an inferred unsupported result.
    targets = {key: value for key, value in actual.items() if case_plan[key] == "UNSUPPORTED"}
    controls = {key: value for key, value in actual.items() if case_plan[key] == "PASS"}
    missing = sorted(key for key, role in case_plan.items() if role == "UNSUPPORTED" and key not in actual)
    control_missing = sorted(key for key, role in case_plan.items() if role == "PASS" and key not in actual)
    control_pass = len(controls) == 1 and all(value == "OK" for value in controls.values())
    residency = qualified(run, expected_maps)
    require(len(residency) >= 2, f"fewer than two in-window own-PID HIP/KFD/VRAM samples for {op}")
    return {
        "seed": run["seed"], "op": op,
        "observed": run["observed"], "passed": run["passed"], "unsupported": run["unsupported"],
        "failed": len(run["failed"]), "resident_samples": len(residency),
        "target_outcomes": targets, "control_outcomes": controls, "missing": missing,
        "control_missing": control_missing, "control_pass": control_pass, "rc": run["rc"],
        "backend_status": backend_status,
    }


def json_grade(claim):
    return list(grade(claim))


def check_capture(out, pins, *, smoke):
    receipt = out / "belief.json"
    record = json.loads(receipt.read_text())
    claims = capture.project(record)
    native = record["native"]
    request = record["capture"]
    require(request == json.loads((out / "request.json").read_text())
            and request["family"] == FAMILY and request["selected_ops"] == OPS
            and request["producer"]["path"] == str(Path(__file__).resolve()),
            "capture request differs from the prospectively written request")
    runs = native["runs"]
    case_plan = read_case_plan()
    plan = selection(case_plan, pins, smoke=smoke)
    selection_path = out / "selection.json"
    require(json.loads(selection_path.read_text()) == plan and native["selection_sha256"] == sha(selection_path)
            and native["historical_reference_sha256"] == pins[HISTORICAL], "prospective selection changed")
    require([(run["seed"], run["op"]) for run in runs]
            == [(item["seed"], item["op"]) for item in plan["invocations"]], "exact ordered seed/operator coverage required")
    require(native["grant"]["smoke"] is smoke and native["row_id"] == ROW, "wrong capture purpose")
    require(all(claim.extra["candidate_identity"] == identity(pins) for claim in claims)
            and pinned_inputs() == pins, "candidate, source or shim bytes changed")
    expected_maps = {str(path): file_identity(path) for path in sorted({BIN, *DSOS, SHIM})}
    require(native["expected_maps"] == expected_maps, "mapped artifact files changed")
    require(native["seeds"] == plan["seeds"] and native["environment"] == ENV and native["owned_pid_reaped"] is True,
            "native seed, environment or reaping proof changed")
    require(native["preflight"] == {"linkage_log_sha256": sha(out / "linkage.log"),
                                    "shim_threads": 2, "graphs_disabled": True}, "preflight custody changed")
    native_grant = native["grant"]
    grant_record = native_grant["record"]
    grant_path = Path(native_grant["path"])
    grant_start, grant_end = (capture.timestamp(grant_record[key]).timestamp() for key in ("start", "end"))
    require(grant_record["regions"] == REGIONS and grant_path.name == ROW + ".grant"
            and grant_path.parent.name == "grants"
            and (smoke or grant_path == FLAGS / "grants" / (ROW + ".grant")), "wrong grant regions or path")
    deadline = native_grant["deadline_epoch"]
    require(grant_start < deadline <= grant_end - 90, "invalid native capture deadline")
    earliest = max(grant_start, capture.timestamp(request["started_utc"]).timestamp())
    latest = min(deadline, capture.timestamp(record["ended_utc"]).timestamp())
    summaries = {}
    for run, invocation in zip(runs, plan["invocations"], strict=True):
        stem = invocation_stem(invocation)
        require(run == json.loads((out / f"{stem}.terminal.json").read_text()), "terminal run record differs")
        require(earliest <= run["started_epoch"] < run["ended_epoch"] <= latest,
                "native process window overlaps another invocation or exceeds exact GPU grant")
        summary = check_run(out, run, invocation, expected_maps, case_plan[invocation["op"]])
        require(summary == json.loads((out / f"{stem}.summary.json").read_text()), "terminal summary differs")
        summaries[stem] = summary
        earliest = run["ended_epoch"]
    totals = {key: sum(summary[key] for summary in summaries.values())
              for key in ("observed", "passed", "unsupported", "failed", "resident_samples")}
    require(len(claims) == len(plan["invocations"]), "expected one projected tuple per native invocation")
    targets = [value for summary in summaries.values() for value in summary["target_outcomes"].values()]
    target_counts = {
        "passed": sum(value == "OK" for value in targets),
        "unsupported": sum("not supported" in value for value in targets),
        "failed": sum(value != "OK" and "not supported" not in value for value in targets),
        "missing": sum(len(summary["missing"]) for summary in summaries.values()),
    }
    control_count = {
        "passed": sum(summary["control_pass"] for summary in summaries.values()),
        "expected": len(plan["invocations"]),
    }
    target_expected = sum(TARGET_PER_OP.values()) * len(plan["seeds"])
    coverage_complete = (len(targets) == target_expected and target_counts["missing"] == 0
                         and control_count["passed"] == control_count["expected"]
                         and totals["observed"] == target_expected + control_count["expected"])
    return {
        "row_id": ROW, "capture": str(receipt), "sha256": sha(receipt), **totals,
        "smoke": smoke, "seeds": plan["seeds"], "coverage_complete": coverage_complete,
        "target_expected": target_expected, "target_counts": target_counts, "control_counts": control_count,
        "invocations": summaries, "projected": len(claims), "grades": [json_grade(claim) for claim in claims],
        "refused": 0,
    }


def interrupt(_signum, _frame):
    raise InterruptedError("row received stop signal")


def smoke_controls(root, stop, deadline):
    guard(stop, deadline)
    log = root / "controls.log"
    with log.open("x") as stream:
        subprocess.run([sys.executable, "-BI", str(CONTROLS), "-v"], stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=min(45, deadline - time.time()))
    guard(stop, deadline)
    receipt = {"status": "PASS", "test_sha256": sha(CONTROLS), "log_sha256": sha(log)}
    output_json(root / "controls.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "run", "complete", "smoke"])
    parser.add_argument("--dry-run", action="store_true", help="verify inputs only")
    args = parser.parse_args(argv)
    if args.action == "smoke" or (args.action == "complete" and os.environ.get("FILLER_DRYRUN") == "1"):
        if "FILLER_DRYRUN_DIR" not in os.environ or "FILLER_SMOKE_T0" not in os.environ:
            return 1
        root = Path(os.environ["FILLER_DRYRUN_DIR"]) / f"historical544-{os.environ['FILLER_SMOKE_T0']}"
        path = root / "SMOKE.json"
        if not path.is_file():
            return 1
        pins = pinned_inputs()
        controls = {"status": "PASS", "test_sha256": pins[CONTROLS],
                    "log_sha256": sha(root / "controls.log")}
        require(controls == json.loads((root / "controls.json").read_text()), "smoke control receipt changed")
        result = check_capture(root / "native", pins, smoke=True)
        return 0 if result["coverage_complete"] and json.loads(path.read_text()) == {"native": result, "controls": controls} else 1
    if args.action == "complete":
        root = HERE / "native"
        path = root / "RESULT.json"
        if not path.is_file():
            return 1
        expected = json.loads(path.read_text())
        receipt = Path(expected["capture"])
        require(receipt.name == "belief.json" and receipt.parent.parent == root
                and re.fullmatch(r"attempt-[a-f0-9]{32}", receipt.parent.name), "wrong official attempt path")
        result = check_capture(receipt.parent, pinned_inputs(), smoke=False)
        return 0 if result["coverage_complete"] and expected == result else 1
    if args.action == "verify" or args.dry_run:
        preflight()
        print("Pinned candidate bytes, linkage and shim verified without native execution")
        return 0
    grant_info = grant()
    pins, linkage = preflight()
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    if os.environ.get("FILLER_DRYRUN") == "1":
        root = Path(os.environ["FILLER_DRYRUN_DIR"]) / f"historical544-{os.environ['FILLER_SMOKE_T0']}"
        root.mkdir()
        controls = smoke_controls(root, grant_info[0], grant_info[1])
        result = execute(root / "native", grant_info, pins, linkage, smoke=True)
        output_json(root / "SMOKE.json", {"native": result, "controls": controls})
    else:
        root = HERE / "native"
        root.mkdir(exist_ok=True)
        attempt = root / f"attempt-{uuid4().hex}"
        result = execute(attempt, grant_info, pins, linkage, smoke=False)
        require(result["coverage_complete"], "official workload coverage incomplete")
        marker = attempt / "RESULT.json"
        output_json(marker, result)
        os.link(marker, root / marker.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
