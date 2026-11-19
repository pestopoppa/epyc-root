#!/usr/bin/python3
"""Grant-only seven-operator elementwise capture. verify runs no native backend test."""
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "scripts" / "vidya"))
from adapters import gpu_pool_native as capture

# Proposed row identifier, independent of invocation timestamps.
ROW = "ni-gpu-pool-elementwise-20261117-v1"
FAMILY = "elementwise"
COMMIT = "c463f601bd39d0e313b744c214b8c22f9455bcd3"
SEED = 2026102603
BROADCAST = r"^type=f32,ne=\[10,5,4,3\],nr=\[[12],[12],[12],[12]\],nf=1,perm1=[01],src_overlap=0$"
CASES = (
    ("ADD", BROADCAST, 16, 0),
    ("MUL", BROADCAST, 16, 0),
    ("SCALE", r"^type=f32,ne=\[(10|100),10,10,10\],", 4, 0),
    ("NORM", r"^type=f32,ne=\[(64|1025),5,4,3\],", 30, 10),
    ("RMS_NORM", r"^type=f32,ne=\[(64|1025),5,4,3\],", 21, 0),
    ("SUM", r"^type=f32,ne=\[(10,5,4,3|11,5,6,3|33,(1|256|1024),1,1)\]", 8, 1),
    ("SUM_ROWS", r"^type=f32,ne=\[(10,5,4,3|11,5,6,3|16,5,6,3|33,(1|256|1024),1,1)\]", 10, 6),
)
OPS = [op for op, *_ in CASES]
MAX_VRAM = 8 * 2**30
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
CPUS = set(range(184, 192))
REGIONS = "mi210_0,184-191"
BIN = HERE / "candidate/bin/test-backend-ops"
DSOS = {HERE / "candidate/bin" / f"libggml{name}.so.0" for name in ("", "-hip", "-base", "-cpu")}
HIP = HERE / "candidate/bin/libggml-hip.so.0"
SHIM = HERE / "candidate/nprocs_shim.so"
SNAPSHOT = HERE / "candidate/test-backend-ops.cpp"
LINKAGE = HERE / "verify_ggml_linkage.sh"
CASE_PLAN = HERE / "case-plan.tsv"
CONTROLS = HERE / "test_run_elementwise.py"
ENV = {
    "BLIS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "SHIM_NPROCS": "2", "LD_PRELOAD": str(SHIM),
    "LD_LIBRARY_PATH": f"{BIN.parent}:/opt/rocm/lib", "HIP_VISIBLE_DEVICES": "0",
    "ROCR_VISIBLE_DEVICES": "0", "HSA_OVERRIDE_CPU_AFFINITY_DEBUG": "0",
    "GGML_CUDA_DISABLE_GRAPHS": "1", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
}
PINNED = {BIN, *DSOS, SHIM, SNAPSHOT, LINKAGE, CASE_PLAN, CONTROLS, Path(capture.__file__),
          HERE / "source/run-v3.py", HERE / "source/ACTUAL-ARTIFACT-PINS.sha256",
          HERE / "scripts/vidya/claim_tuple.py", HERE / "scripts/vidya/canonical.py", Path(__file__).resolve()}


def argv_for(op, params):
    return [str(BIN), "test", "-b", "ROCm0", "-o", op, "-p", params, "-j", "1", "--suite-seed", str(SEED)]


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
    for line in CASE_PLAN.read_text().splitlines():
        op, status, params = line.split("\t")
        require(op in plan and params not in plan[op], "unknown or duplicate planned case")
        plan[op][params] = status
    for op, selector, generated, unsupported in CASES:
        counts = Counter(plan[op].values())
        require(counts == Counter({"PASS": generated - unsupported, "UNSUPPORTED": unsupported})
                and all(re.search(selector, params) for params in plan[op]),
                f"planned {op} cases differ from the original selector or support partition")
    return plan


def identity(pins):
    return {
        "source": {"commit": COMMIT, "removed_worktree_dirty_state": "UNKNOWN",
                   "snapshot": str(SNAPSHOT), "snapshot_sha256": pins[SNAPSHOT]},
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


def run_native(out, op, params, expected, stop, deadline, expected_maps):
    log = out / (op + ".log")
    argv = argv_for(op, params)
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
    end = time.time()
    require(not Path(f"/proc/{child.pid}").exists(), "owned native child still present")
    clean_log = re.sub(r"\x1b\[[0-9;]*m", "", log.read_text())
    lines = [line for line in clean_log.splitlines() if line.startswith(f"  {op}(")]
    return {"op": op, "argv": argv, "seed": SEED, "generated_expected": expected,
           "status": "native_exit_recorded", "pid": child.pid, "birth_ticks": birth, "rc": rc,
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
    request = capture.begin(FAMILY, ROW, candidate, OPS, producer=__file__)
    output_json(out / "request.json", request)
    (out / "linkage.log").write_text(linkage)
    runs = []
    for op, params, expected, unsupported in CASES:
        run = run_native(out, op, params, expected, stop, deadline, expected_maps)
        output_json(out / f"{op}.terminal.json", run)
        check_run(out, run, op, params, expected, unsupported, expected_maps, case_plan[op])
        runs.append(run)
    guard(stop, deadline)
    require(pinned_inputs() == pins, "candidate, source or shim bytes changed")
    record = {
        **candidate, "schema": capture.NATIVE, "row_id": ROW, "model_free": True, "seed": SEED,
        "invocation_token": request["invocation_token"], "runs": runs,
        "scope": "Seven exact elementwise operator selections at seed 2026102603 on the pinned candidate",
        "proposition": "The 88 supported cases agree with the candidate-local CPU reference under native tolerances. "
                       "The 17 unsupported cases remain explicit and were not compared.",
        "claim_limits": [capture.LIMIT], "environment": ENV, "expected_maps": expected_maps,
        "grant": {"path": str(grant_path), "record": grant_record, "deadline_epoch": deadline, "smoke": smoke},
        "preflight": {"linkage_log_sha256": sha(out / "linkage.log"), "shim_threads": 2,
                      "graphs_disabled": True}, "owned_pid_reaped": True,
    }
    receipt = out / "belief.json"
    capture.write_capture(receipt, request, record)
    return check_capture(out, pins, smoke=smoke)


def check_run(out, run, op, params, expected, unsupported, expected_maps, case_plan):
    require(run["op"] == op and run["argv"] == argv_for(op, params)
            and run["log"] == str(out / (op + ".log")), "native invocation differs from the prepared selection")
    require(run["seed"] == SEED and run["generated_expected"] == expected
            and run["status"] == "native_exit_recorded", "native seed, denominator or status changed")
    capture.log_counts(run)
    supported = expected - unsupported
    require(run["rc"] == 0 and run["observed"] == expected and run["passed"] == supported
            and not run["failed"] and run["unsupported"] == unsupported, "expected native pass/unsupported partition absent")
    log = re.sub(r"\x1b\[[0-9;]*m", "", Path(run["log"]).read_text())
    backend = re.findall(
        r"^Backend [0-9]+/[0-9]+: ROCm0\n  Device description: AMD Instinct MI210\n"
        r"(.*?)^  Backend ROCm0: OK$", log, re.M | re.S)
    require(len(backend) == 1 and f"  {supported}/{supported} tests passed" in backend[0].splitlines(),
            "native MI210 backend or supported comparison summary absent")
    prefix = f"  {op}("
    lines = [line for line in backend[0].splitlines() if line.startswith(prefix)]
    actual = {}
    for line in lines:
        match = re.fullmatch(r"(.*)\): (OK|not supported \[ROCm0\]) *", line[len(prefix):])
        require(match and re.search(params, match[1]), f"native {op} case outside the original selection")
        require(match[1] not in actual, f"duplicate native {op} case")
        actual[match[1]] = "PASS" if match[2] == "OK" else "UNSUPPORTED"
    require(actual == case_plan and len(lines) == expected, f"native {op} case identity or support disposition changed")
    residency = qualified(run, expected_maps)
    require(len(residency) >= 2, f"fewer than two in-window own-PID HIP/KFD/VRAM samples for {op}")
    return {
        "observed": run["observed"], "passed": run["passed"], "unsupported": run["unsupported"],
        "failed": len(run["failed"]), "resident_samples": len(residency),
    }


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
    require([run["op"] for run in runs] == OPS, "exact ordered operator coverage required")
    require(native["grant"]["smoke"] is smoke and native["row_id"] == ROW, "wrong capture purpose")
    require(all(claim.extra["candidate_identity"] == identity(pins) for claim in claims)
            and pinned_inputs() == pins, "candidate, source or shim bytes changed")
    expected_maps = {str(path): file_identity(path) for path in sorted({BIN, *DSOS, SHIM})}
    require(native["expected_maps"] == expected_maps, "mapped artifact files changed")
    require(native["seed"] == SEED and native["environment"] == ENV and native["owned_pid_reaped"] is True,
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
    case_plan = read_case_plan()
    for run, (op, params, expected, unsupported) in zip(runs, CASES, strict=True):
        require(run == json.loads((out / f"{op}.terminal.json").read_text()), "terminal run record differs")
        require(earliest <= run["started_epoch"] < run["ended_epoch"] <= latest,
                "native process window overlaps another invocation or exceeds exact GPU grant")
        summaries[op] = check_run(out, run, op, params, expected, unsupported, expected_maps, case_plan[op])
        earliest = run["ended_epoch"]
    totals = {key: sum(summary[key] for summary in summaries.values())
              for key in ("observed", "passed", "unsupported", "failed", "resident_samples")}
    return {"row_id": ROW, "capture": str(receipt), "sha256": sha(receipt), **totals,
            "operators": summaries, "projected": len(claims), "refused": 0}


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
    if args.action == "smoke":
        if "FILLER_DRYRUN_DIR" not in os.environ or "FILLER_SMOKE_T0" not in os.environ:
            return 1
        root = Path(os.environ["FILLER_DRYRUN_DIR"]) / f"elementwise-{os.environ['FILLER_SMOKE_T0']}"
        path = root / "SMOKE.json"
        if not path.is_file():
            return 1
        pins = pinned_inputs()
        controls = {"status": "PASS", "test_sha256": pins[CONTROLS],
                    "log_sha256": sha(root / "controls.log")}
        require(controls == json.loads((root / "controls.json").read_text()), "smoke control receipt changed")
        result = check_capture(root / "native", pins, smoke=True)
        return 0 if json.loads(path.read_text()) == {"native": result, "controls": controls} else 1
    if args.action == "complete":
        path = HERE / "native/RESULT.json"
        return 0 if path.is_file() and json.loads(path.read_text()) == check_capture(
            path.parent, pinned_inputs(), smoke=False
        ) else 1
    if args.action == "verify" or args.dry_run:
        preflight()
        print("Pinned candidate bytes, linkage and shim verified without native execution")
        return 0
    grant_info = grant()
    pins, linkage = preflight()
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    if os.environ.get("FILLER_DRYRUN") == "1":
        root = Path(os.environ["FILLER_DRYRUN_DIR"]) / f"elementwise-{os.environ['FILLER_SMOKE_T0']}"
        root.mkdir()
        controls = smoke_controls(root, grant_info[0], grant_info[1])
        result = execute(root / "native", grant_info, pins, linkage, smoke=True)
        output_json(root / "SMOKE.json", {"native": result, "controls": controls})
    else:
        result = execute(HERE / "native", grant_info, pins, linkage, smoke=False)
        output_json(HERE / "native/RESULT.json", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
