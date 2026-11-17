#!/usr/bin/python3
"""Grant-only native MUL_MAT capture. --dry-run checks inputs without running native code."""
import argparse
from datetime import datetime
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

ROW = "ni-gpu-pool-matmul-20261117-v1"
COMMIT = "c463f601bd39d0e313b744c214b8c22f9455bcd3"
OP = "MUL_MAT"
SEED = 20261026
EXPECTED = 201
TYPES = ("f32", "f16", "q4_0", "q8_0", "q4_K", "q6_K")
PARAMS = (r"^type_a=(f32|f16|q4_0|q8_0|q4_K|q6_K),type_b=f32,m=16,n=([1-9]|16),k=256,"
          r"bs=\[(1,1|3,1|3,2|2,3)\],nr=\[[12],[12]\],per=\[(0,1,2,3|0,2,1,3|0,1,3,2|0,3,2,1)\],k_v=0,o=1$")
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
CPUS = set(range(184, 192))
REGIONS = "mi210_0,184-191"
BIN = HERE / "candidate/bin/test-backend-ops"
DSOS = {HERE / "candidate/bin" / f"libggml{name}.so.0" for name in ("", "-hip", "-base", "-cpu")}
HIP = HERE / "candidate/bin/libggml-hip.so.0"
SHIM = HERE / "candidate/nprocs_shim.so"
SNAPSHOT = HERE / "candidate/test-backend-ops.cpp"
LINKAGE = HERE / "verify_ggml_linkage.sh"
ARGV = [str(BIN), "test", "-b", "ROCm0", "-o", OP, "-p", PARAMS, "-j", "1", "--suite-seed", str(SEED)]
ENV = {
    "BLIS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "SHIM_NPROCS": "2", "LD_PRELOAD": str(SHIM),
    "LD_LIBRARY_PATH": f"{BIN.parent}:/opt/rocm/lib", "HIP_VISIBLE_DEVICES": "0",
    "ROCR_VISIBLE_DEVICES": "0", "HSA_OVERRIDE_CPU_AFFINITY_DEBUG": "0",
    "GGML_CUDA_DISABLE_GRAPHS": "1", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
}
PINNED = {BIN, *DSOS, SHIM, SNAPSHOT, LINKAGE, Path(capture.__file__),
          HERE / "scripts/vidya/claim_tuple.py", HERE / "scripts/vidya/canonical.py", Path(__file__).resolve()}


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
    start, end = (datetime.fromisoformat(record[key]).timestamp() for key in ("start", "end"))
    require(record["regions"] == REGIONS and start <= time.time() < end, "invalid exact GPU grant")
    require(os.sched_getaffinity(0) == CPUS, "driver did not inherit exact grant CPU affinity")
    return stop, min(float(os.environ["FILLER_DEADLINE"]), end - 90), path, record


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


def sample(pid, expected_maps):
    proc = Path(f"/proc/{pid}")
    masks = {}
    for task in (proc / "task").glob("*/status"):
        try:
            line = re.search(r"^Cpus_allowed_list:\s*(.+)$", task.read_text(), re.M)
        except (FileNotFoundError, ProcessLookupError):
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
        if proc.exists() and (proc / "stat").read_text().split(") ", 1)[1][0] != "Z":
            raise
        return None
    return {"time": time.time(), "pid": pid, "task_masks": masks, "kfd": kfd.exists(),
            "vram_bytes": vram, "maps": found_maps}


def qualified(run, expected_maps):
    samples = run["residency_samples"]
    require(all(run["started_epoch"] <= item["time"] <= run["ended_epoch"] and item["pid"] == run["pid"]
                and all(mask_set(mask) <= CPUS for mask in item["task_masks"].values())
                and all(path in expected_maps and expected_maps[path] == proof for path, proof in item["maps"].items())
                and all(type(n) is int and 0 <= n for n in item["vram_bytes"].values())
                for item in samples), "sample window, affinity, map or VRAM custody fails")
    return {item["time"] for item in samples if item["kfd"] is True and item["task_masks"]
            and 0 < sum(item["vram_bytes"].values()) <= 60 * 2**30 and item["maps"] == expected_maps}


def output_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def execute(out, grant_info, pins, linkage, *, smoke):
    stop, deadline, grant_path, grant_record = grant_info
    guard(stop, deadline)
    out.mkdir()
    expected_maps = {str(path): file_identity(path) for path in sorted({BIN, *DSOS, SHIM})}
    candidate = identity(pins)
    request = capture.begin("matmul", ROW, candidate, [OP], producer=__file__)
    output_json(out / "request.json", request)
    (out / "linkage.log").write_text(linkage)
    log = out / (OP + ".log")
    start = time.time()
    samples = []
    with log.open("x") as stream:
        stream.write("ARGV " + json.dumps(ARGV) + "\n")
        stream.flush()
        child = subprocess.Popen(ARGV, stdout=stream, stderr=subprocess.STDOUT,
                                 env={**ENV, "FILLER_ID": ROW, "FILLER_STOPFILE": str(stop)})
        try:
            with Path(os.environ["FILLER_PIDFILE"]).open("a") as pidfile:
                pidfile.write(f"{child.pid}\n")
            while child.poll() is None:
                guard(stop, deadline)
                current = sample(child.pid, expected_maps)
                if current is not None:
                    require(sum(current["vram_bytes"].values()) <= 60 * 2**30, "own PID VRAM guard exceeded")
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
    lines = [line for line in clean_log.splitlines() if line.startswith("  MUL_MAT(")]
    run = {"op": OP, "argv": ARGV, "seed": SEED, "generated_expected": EXPECTED,
           "status": "native_exit_recorded", "pid": child.pid, "rc": rc,
           "started_epoch": start, "ended_epoch": end, "log": str(log), "log_sha256": sha(log),
           "observed": len(lines), "passed": sum(line.endswith("OK") for line in lines),
           "unsupported": sum("not supported" in line for line in lines),
           "failed": [line for line in lines if not line.endswith("OK") and "not supported" not in line],
           "residency_samples": samples}
    record = {
        **candidate, "schema": capture.NATIVE, "row_id": ROW, "model_free": True, "seed": SEED,
        "invocation_token": request["invocation_token"], "runs": [run],
        "scope": "Selected seeded MUL_MAT cases against the artifact's candidate-local native CPU reference",
        "proposition": "Native correctness uses the existing binary NMSE tolerance of 5e-4",
        "claim_limits": [capture.LIMIT], "environment": ENV, "expected_maps": expected_maps,
        "grant": {"path": str(grant_path), "record": grant_record, "smoke": smoke},
        "preflight": {"linkage_log_sha256": sha(out / "linkage.log"), "shim_threads": 2,
                      "graphs_disabled": True}, "owned_pid_reaped": True,
    }
    receipt = out / "belief.json"
    capture.write_capture(receipt, request, record)
    return check_capture(out, pins, smoke=smoke)


def check_capture(out, pins, *, smoke):
    receipt = out / "belief.json"
    record = json.loads(receipt.read_text())
    claim, = capture.project(record)
    native = record["native"]
    run, = native["runs"]
    require(native["grant"]["smoke"] is smoke and native["row_id"] == ROW, "wrong capture purpose")
    require(claim.extra["candidate_identity"] == identity(pins) and pinned_inputs() == pins,
            "candidate, source or shim bytes changed")
    require(native["expected_maps"] == {str(path): file_identity(path) for path in sorted({BIN, *DSOS, SHIM})},
            "mapped artifact files changed")
    require(run["argv"] == ARGV and run["log"] == str(out / (OP + ".log")) and native["environment"] == ENV,
            "native invocation differs from the prepared selection")
    require(native["owned_pid_reaped"] is True and run["rc"] == 0 and run["observed"] == EXPECTED
            and run["passed"] == EXPECTED and not run["failed"] and run["unsupported"] == 0,
            "expected native pass partition absent")
    grant_record = native["grant"]["record"]
    grant_start, grant_end = (datetime.fromisoformat(grant_record[key]).timestamp() for key in ("start", "end"))
    require(grant_record["regions"] == REGIONS and grant_start <= run["started_epoch"] < run["ended_epoch"] <= grant_end,
            "native process window exceeds exact GPU grant")
    require(native["preflight"]["linkage_log_sha256"] == sha(out / "linkage.log"), "linkage log changed")
    log = re.sub(r"\x1b\[[0-9;]*m", "", Path(run["log"]).read_text())
    require(re.search(r"Backend [0-9]+/[0-9]+: ROCm0\n  Device description:", log), "native ROCm0 backend line absent")
    require(all(any(line.startswith("  MUL_MAT(type_a=" + dtype + ",") and line.endswith("OK")
                    for line in log.splitlines()) for dtype in TYPES), "a selected type had no positive pass")
    residency = qualified(run, native["expected_maps"])
    require(len(residency) >= 2, "fewer than two in-window own-PID HIP/KFD/VRAM samples")
    return {"row_id": ROW, "capture": str(receipt), "sha256": sha(receipt), "observed": run["observed"],
            "passed": run["passed"], "unsupported": run["unsupported"], "failed": len(run["failed"]),
            "resident_samples": len(residency), "projected": 1, "refused": 0}


def interrupt(_signum, _frame):
    raise InterruptedError("row received stop signal")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "run", "complete", "smoke"])
    parser.add_argument("--dry-run", action="store_true", help="verify inputs only")
    args = parser.parse_args(argv)
    if args.action == "smoke":
        if "FILLER_DRYRUN_DIR" not in os.environ or "FILLER_SMOKE_T0" not in os.environ:
            return 1
        path = Path(os.environ["FILLER_DRYRUN_DIR"]) / f"matmul-{os.environ['FILLER_SMOKE_T0']}/SMOKE.json"
        return 0 if path.is_file() and json.loads(path.read_text())["projected"] == 1 else 1
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
        root = Path(os.environ["FILLER_DRYRUN_DIR"]) / f"matmul-{os.environ['FILLER_SMOKE_T0']}"
        root.mkdir()
        result = execute(root / "native", grant_info, pins, linkage, smoke=True)
        output_json(root / "SMOKE.json", result)
    else:
        result = execute(HERE / "native", grant_info, pins, linkage, smoke=False)
        output_json(HERE / "native/RESULT.json", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
