"""CH-17 architect_general CPU comparison dispatched only by Rowflow."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
from statistics import median
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import urllib.error
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server_np_sweep import http_json
import workloads

HERE = Path(__file__).resolve().parent
ROW = "ch17-c13-architect-general-cpu-20261118"
PORT = 19580
IMAGE = Path("/mnt/raid0/llm/kernels/builds/cpu-20261117-bda43aa17-c13")
BIN = IMAGE / "bin/llama-server"
ORDER = (("none", "mtp"), ("mtp", "none"), ("none", "mtp"))
RESULT = HERE / "RESULT.json"
SMOKE = HERE / "smoke/RESULT.json"
LIVE_GRANTS = Path("/mnt/raid0/llm/tmp/compute-flags/grants")
STAT_FIELDS = ("dev", "ino", "size", "mtime_ns", "ctime_ns")
STARTUP_SECONDS = 780
REQUEST_SECONDS = 150

def stat_fields(path):
    stat = Path(path).stat()
    return [getattr(stat, f"st_{field}") for field in STAT_FIELDS]


def prove_models(pins):
    for pin in pins:
        require(stat_fields(pin["path"]) == pin["stat"], f"prepared weight identity drift: {pin['path']}")


def smoke_identity():
    return {"attempt_epoch": int(os.environ["FILLER_SMOKE_T0"]),
            "harness_result_path": os.environ["FILLER_DRYRUN_RESULT_PATH"],
            "dryrun_dir": os.environ["FILLER_DRYRUN_DIR"]}


def require(ok, detail):
    if not ok:
        raise RuntimeError(detail)


def write(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def check_inputs():
    pins = json.loads((HERE / "inputs.json").read_text())
    for path, expected in pins["files"].items():
        with open(path, "rb") as stream:
            require(hashlib.file_digest(stream, "sha256").hexdigest() == expected, f"pin drift: {path}")
    prove_models([*pins["models"], pins["smoke_model"]])
    return pins


def read_grant(smoke):
    directory = Path(os.environ["FILLER_DRYRUN_DIR"]) / "grants" if smoke else LIVE_GRANTS
    path = directory / f"{ROW}.grant"
    raw = path.read_text().strip()
    receipt = dict(item.split("=", 1) for item in raw.split())
    start, end = (datetime.fromisoformat(receipt[key].replace("Z", "+00:00")).timestamp()
                  for key in ("start", "end"))
    require(start <= time.time() < end == int(os.environ["FILLER_END"]), "wrong live grant interval")
    require(os.environ["FILLER_PORTS"] == str(PORT), "wrong engine port")
    require(expand(receipt.get("cpus", receipt["regions"])) == expand(os.environ["FILLER_CPUS"]),
            "grant CPU list disagrees with the engine")
    if smoke:
        require(receipt.get("id") == ROW and receipt.get("kind") == "rowflow-dryrun",
                "publisher smoke grant missing")
    else:
        require(set(receipt["holds"].split(",")) == {"q0", "q1", "q2", "q3"},
                "whole-physical-host claim missing")
    return path, raw


def window(grant):
    require(not Path(os.environ["FILLER_STOPFILE"]).exists(), "keeper STOP")
    require(time.time() < int(os.environ["FILLER_DEADLINE"]), "keeper deadline")
    path, expected = grant
    require(path.read_text().strip() == expected, "live grant changed")


def expand(cpulist):
    result = set()
    for item in cpulist.split(","):
        first, _, last = item.partition("-")
        result.update(range(int(first), int(last or first) + 1))
    return result


def cpu_options(smoke, pins):

    allowed = os.sched_getaffinity(0)
    require(allowed and allowed == expand(os.environ["FILLER_CPUS"]), "affinity differs from grant")
    cores = {}
    for cpu in sorted(allowed):
        siblings = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
        cores.setdefault(min(expand(siblings.read_text().strip())), cpu)
    expected = 4 if smoke else pins["scope"]["threads"]
    require(int(os.environ["FILLER_THREADS"]) == len(cores) == len(allowed) == expected, "wrong grant shape")
    require(smoke or allowed == set(pins["physical_cpus"]), "grant does not match the native CPU recipe")
    return expected


def server_env(threads, pins, smoke):
    hidden = {"ROCR_VISIBLE_DEVICES": "", "HIP_VISIBLE_DEVICES": "-1", "GPU_DEVICE_ORDINAL": "-1",
              "CUDA_VISIBLE_DEVICES": "-1", "GGML_VK_VISIBLE_DEVICES": "-1", "HSA_ENABLE_SDMA": "0"}
    require(os.environ["FILLER_GPU_FENCE"] == "1" and os.environ["FILLER_NEEDGPU"] == "0" and
            all(os.environ.get(key) == value for key, value in hidden.items()), "CPU GPU fence missing")
    preloads = re.split(r"[:\s]+", os.environ.get("LD_PRELOAD", "").strip())
    fence = [path for path in preloads if Path(path).is_absolute() and
             re.fullmatch(r"gpu_fence-[0-9a-f]{12}\.so", Path(path).name)]
    require(len(fence) == 1, "GPU fence shim missing")
    placement = {"LD_LIBRARY_PATH": str(BIN.parent), "PATH": "/usr/bin:/bin", "LC_ALL": "C",
                 "OMP_NUM_THREADS": str(threads), "OMP_DYNAMIC": "FALSE"} if smoke else pins["env"]
    return {**placement, **hidden, "FILLER_GPU_FENCE": "1", "FILLER_ID": ROW,
            "FILLER_STOPFILE": os.environ["FILLER_STOPFILE"], "LD_PRELOAD": fence[0]}


def wait_owned_listener(proc, grant, smoke):
    process = Path(f"/proc/{proc.pid}")
    address = f"0100007F:{PORT:04X}"
    until = time.monotonic() + (45 if smoke else STARTUP_SECONDS)
    while time.monotonic() < until:
        window(grant)
        require(proc.poll() is None, f"owned server exited before health, rc={proc.returncode}")
        listeners = {row.split()[9] for row in (process / "net/tcp").read_text().splitlines()[1:]
                     if row.split()[1] == address and row.split()[3] == "0A"}
        if listeners:
            for fd in (process / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except FileNotFoundError:
                    continue
                if target.startswith("socket:[") and target[8:-1] in listeners:
                    try:
                        status, _ = http_json("GET", f"http://127.0.0.1:{PORT}/health", None, 3)
                    except OSError:
                        continue
                    if status == 200:
                        return target[8:-1]
        time.sleep(0.1 if smoke else 1)
    raise TimeoutError(f"private listener ownership/health missing for pid {proc.pid}")


def proc_start(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def live_custody(pid, expected_start, inode, expected_mapped, allowed):
    proc = Path(f"/proc/{pid}")
    begin = time.monotonic_ns()
    require(proc_start(pid) == expected_start, "server process identity changed")
    require(os.path.samefile(proc / "exe", BIN), "owned executable inode differs from the image")
    mapped = {}
    for line in (proc / "maps").read_text().splitlines():
        columns = line.split(maxsplit=5)
        if len(columns) != 6:
            continue
        name = Path(columns[5]).name
        if name == BIN.name or name.startswith(("libllama", "libggml", "libmtmd")):
            target = str(Path(columns[5]).resolve())
            dev = os.makedev(*(int(value, 16) for value in columns[3].split(":")))
            mapped[target] = [dev, int(columns[4])]
    require(mapped == expected_mapped, "mapped image object path/inode drift")
    address = f"0100007F:{PORT:04X}"
    require(any(row.split()[1] == address and row.split()[3] == "0A" and row.split()[9] == inode
                for row in (proc / "net/tcp").read_text().splitlines()[1:]), "owned listener changed")
    for fd in (proc / "fd").iterdir():
        try:
            if os.readlink(fd) == f"socket:[{inode}]":
                break
        except FileNotFoundError:
            continue
    else:
        raise RuntimeError("listener is no longer owned by the captured process")
    affinities = {}
    for thread in (proc / "task").iterdir():
        try:
            cpus = os.sched_getaffinity(int(thread.name))
        except ProcessLookupError:
            continue
        require(cpus and cpus <= allowed, f"server TID {thread.name} escaped the CPU claim")
        affinities[thread.name] = sorted(cpus)
    require(str(pid) in affinities and proc_start(pid) == expected_start, "owned thread identity missing")
    return {"start_mono_ns": begin, "end_mono_ns": time.monotonic_ns(), "pid": pid,
            "start_ticks": expected_start, "listener_inode": inode, "mapped_device_inode": mapped,
            "affinity_by_tid": affinities}


def request_owned(payload, pid, expected_start, inode, expected_mapped, smoke, grant):
    allowed = os.sched_getaffinity(0)
    samples, observations, bounds = [], [], {}
    started = Event()
    owned = {pid: int(expected_start), os.getpid(): int(proc_start(os.getpid()))}

    def submit_request():
        bounds["start"] = time.monotonic_ns()
        started.set()
        try:
            return http_json("POST", f"http://127.0.0.1:{PORT}/completion", payload,
                             30 if smoke else REQUEST_SECONDS)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                return exc.code, json.loads(body)
            except (ValueError, UnicodeError):
                return exc.code, {"body": body.decode(errors="replace")}
        finally:
            bounds["end"] = time.monotonic_ns()

    with ThreadPoolExecutor(max_workers=1) as executor:
        reply = executor.submit(submit_request)
        require(started.wait(5), "request worker did not start")
        while not reply.done():
            window(grant)
            sample = live_custody(pid, expected_start, inode, expected_mapped, allowed)
            if not smoke and (not observations or sample["start_mono_ns"] - observations[-1][0] >= 300_000_000):
                observation = workloads.snapshot(owned)
                if not reply.done():
                    observations.append(observation)
            if not reply.done():
                samples.append(sample)
            time.sleep(0.05 if smoke else 0.1)
        status, response = reply.result()
    samples = [sample for sample in samples if bounds["start"] <= sample["start_mono_ns"]
               <= sample["end_mono_ns"] <= bounds["end"]]
    observations = [item for item in observations if bounds["start"] <= item[0] <= bounds["end"]]
    activity = [workloads.compare(before, after) for before, after in zip(observations, observations[1:])]
    return status, response, {"start_mono_ns": bounds["start"], "end_mono_ns": bounds["end"],
                              "live_samples": samples, "foreign_workload_samples": activity}

def run_arm(root, number, arm, threads, env, pins, smoke, grant):
    window(grant)
    name = f"pair{number}-{arm}"
    use_draft = arm != "none"
    if smoke:
        model = pins["smoke_model"]["path"]
        prove_models([pins["smoke_model"]])
        args = [str(BIN), "-m", model, "--host", "127.0.0.1", "--port", str(PORT),
                "--device", "none", "-ngl", "0", "-t", str(threads), "-tb", str(threads),
                "-c", "1024", "-np", "1", "-b", "128", "-ub", "128",
                "--no-warmup", "--cache-ram", "0", "--jinja", "--reasoning", "off",
                "--spec-type", "draft-simple" if use_draft else "none"]
        if use_draft:
            args += ["-md", model, "--device-draft", "none", "-ngld", "0",
                     "--spec-draft-n-max", "4", "--spec-draft-p-min", "0"]
    else:
        prove_models(pins["models"])
        slots = root / f"{name}.slots"
        slots.mkdir()
        args = [*pins["numa"], *(str(slots) if item == "{private_slots}" else item
                                 for item in pins["argv"][arm])]
        check_workloads(root / f"{name}.preload.json")
    events = {"arm": arm, "argv": args, "started_at": timestamp(), "requests": []}
    try:
        with (root / f"{name}.server.log").open("wb") as log:
            proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                events["pid"] = proc.pid
                with open(os.environ["FILLER_PIDFILE"], "a") as pidfile:
                    pidfile.write(f"{proc.pid}\n")
                inode = wait_owned_listener(proc, grant, smoke)
                events["owned_listener_inode"] = inode
                events["server_start_ticks"] = proc_start(proc.pid)
                expected_mapped = {str(Path(path).resolve()): stat_fields(path)[:2]
                                   for path in pins["files"] if Path(path).parent == BIN.parent}
                actual_env = (Path(f"/proc/{proc.pid}") / "environ").read_bytes().split(b"\0")
                require(all(f"{key}={value}".encode() in actual_env for key, value in env.items()),
                        "server environment differs from the selected recipe")
                prompts = [{"id": "smoke-repeat-list", "prompt": "Continue the sequence: 1, 2, 3,"}] if smoke else pins["prompts"]
                cap = 32 if smoke else 128
                for prompt in prompts:
                    window(grant)
                    payload = {"prompt": prompt["prompt"], "temperature": 0, "seed": 7, "n_predict": cap,
                               "ignore_eos": True, "cache_prompt": False, "return_tokens": True,
                               "stream": False}
                    status, response, custody = request_owned(payload, proc.pid, events["server_start_ticks"],
                                                                inode, expected_mapped, smoke, grant)
                    events["requests"].append({"prompt_id": prompt["id"], "request": payload, "http_status": status,
                                                "response": response, "custody": custody})
                    write(root / f"{name}.json", events)
                    require(len(custody["live_samples"]) >= (1 if smoke else 2),
                            "missing overlapping all-TID request custody")
                    if not smoke:
                        activity = custody["foreign_workload_samples"]
                        require(activity and not any(item["refused"] for item in activity),
                                "foreign workload, unknown contention or missing overlapping workload custody")
                    timings = response.get("timings", {})
                    count = timings.get("predicted_n")
                    ms = timings.get("predicted_ms")
                    drafted = timings.get("draft_n", 0)
                    require(status == 200 and count == cap and type(ms) in (int, float)
                            and math.isfinite(ms) and ms > 0, f"{name}: incomplete decode")
                    tokens = response.get("tokens")
                    require(isinstance(tokens, list) and len(tokens) == count and all(type(token) is int for token in tokens),
                            f"{name}: missing token identities")
                    accepted = timings.get("draft_n_accepted", 0 if arm == "none" else None)
                    require(type(drafted) is int and type(accepted) is int and 0 <= accepted <= drafted and
                            (drafted > 0 if use_draft else drafted == 0), f"{name}: invalid draft activation")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=15)
                require(subprocess.run(["/usr/bin/ps", "-p", str(proc.pid)],
                                       stdout=subprocess.DEVNULL).returncode != 0, "owned PID still present")
                events["cleanup_verified"] = True
    except BaseException as exc:
        events["failure"] = {"type": type(exc).__name__, "reason": str(exc)}
        raise
    finally:
        events["ended_at"] = timestamp()
        write(root / f"{name}.json", events)
    return events


def check_workloads(path):
    _, _, known, unknown = workloads.snapshot({os.getpid(): int(proc_start(os.getpid()))})
    write(path, {"captured_at": timestamp(), "foreign_known": known, "unreadable_pids": unknown})
    require(not known and not unknown, f"whole-host workload custody refused: {path}")


def compare(arms, draft_arm):
    comparisons = []
    for base, mtp in zip(arms["none"]["requests"], arms[draft_arm]["requests"], strict=True):
        require(base["prompt_id"] == mtp["prompt_id"], "request pairing mismatch")
        a, b = base["response"], mtp["response"]
        tps = {name: r["timings"]["predicted_n"] * 1000 / r["timings"]["predicted_ms"]
               for name, r in (("none", a), (draft_arm, b))}
        comparisons.append({"prompt_id": base["prompt_id"], "decode_tps": tps,
                            "draft_to_none_ratio": tps[draft_arm] / tps["none"],
                            "greedy_token_identity": a["tokens"] == b["tokens"],
                            "first_token_difference_index": next(
                                (index for index, (left, right) in enumerate(zip(a["tokens"], b["tokens"], strict=True))
                                 if left != right), None),
                            "draft_n": b["timings"]["draft_n"],
                            "draft_n_accepted": b["timings"].get("draft_n_accepted")})
    return comparisons


def interrupted(_signum, _frame):
    raise SystemExit(75)


def main():
    if sys.argv[1:] == ["--precondition"]:
        require(BIN.is_file() and (HERE / "inputs.json").is_file(), "prepared image or input absent")
        return
    if sys.argv[1:] == ["--complete"]:
        if not RESULT.is_file():
            raise SystemExit(1)
        record = json.loads(RESULT.read_bytes())
        complete = (record["id"] == ROW and record["verdict"] == "COMPARISON_COMPLETE"
                    and len(record["pairs"]) == 3 and record["scope"]["threads"] == 96)
        raise SystemExit(0 if complete else 1)
    if sys.argv[1:] == ["--smoke-predicate"]:
        identity = smoke_identity()
        result = Path(identity["harness_result_path"])
        record = json.loads(result.read_text())
        require(record["id"] == ROW and record["verdict"] == "SMOKE_PASS"
                and record["scope"]["draft_type"] == "draft-simple"
                and record["scope"]["threads"] == 4 and record["native_mtp_exercised"] is False
                and record["smoke_attempt"] == identity and result.stat().st_mtime >= identity["attempt_epoch"],
                "missing current live two-arm plumbing smoke")
        return
    require(not sys.argv[1:] and os.environ.get("FILLER_ID") == ROW, "requires Rowflow allocation")
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    require(smoke == (os.environ.get("FILLER_DRYRUN") == "1") and os.environ.get("FILLER_DIRECT") != "1",
            "requires native grant or publisher smoke")
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    receipt = {"id": ROW, "started_at": timestamp(), "pairs": [], "native_mtp_exercised": False}
    try:
        grant = read_grant(smoke)
        window(grant)
        out = HERE / ("smoke" if smoke else "out")
        out.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="run-", dir=out))
        receipt["raw_directory"] = str(root)
        pins = check_inputs()
        threads = cpu_options(smoke, pins)
        env = server_env(threads, pins, smoke)
        linkage = subprocess.check_output(["/bin/bash", str(HERE / "verify_ggml_linkage.sh"), str(BIN),
                                            str(BIN.parent)], env=env, text=True)
        (root / "linkage.txt").write_text(linkage)
        receipt.update({"id": ROW, "candidate": pins["candidate"],
                   "models": [pins["smoke_model"]] if smoke else pins["models"],
                   "scope": {"threads": 4, "draft_type": "draft-simple", "role": "plumbing smoke"}
                   if smoke else pins["scope"],
                   "input_sha256": hashlib.sha256((HERE / "inputs.json").read_bytes()).hexdigest(),
                   "grant": grant[1], "grant_path": str(grant[0]),
                   "affinity": sorted(os.sched_getaffinity(0)), "environment": env, "raw_directory": str(root),
                   "started_at": timestamp(), "pairs": []})
        if smoke:
            receipt["smoke_attempt"] = smoke_identity()
        draft_arm = "draft-simple" if smoke else "mtp"
        orderings = (("none", draft_arm),) if smoke else ORDER
        for number, order in enumerate(orderings, start=1):
            arms = {}
            for arm in order:
                arms[arm] = run_arm(root, number, arm, threads, env, pins, smoke, grant)
                if not smoke and arm == "mtp":
                    receipt["native_mtp_exercised"] = True
            receipt["pairs"].append({"order": order, "comparisons": compare(arms, draft_arm)})
            write(root / "pairs.json", receipt)
            print(f"pair {number} complete", flush=True)
        window(grant)
        if not smoke:
            check_workloads(root / "post-cleanup.json")
        receipt.update(ended_at=timestamp(), complete=True, status="complete",
                       verdict="SMOKE_PASS" if smoke else "COMPARISON_COMPLETE",
                       pair_median_ratios=[median(item["draft_to_none_ratio"] for item in pair["comparisons"])
                                           for pair in receipt["pairs"]])
        if smoke:
            comparison, = receipt["pairs"][0]["comparisons"]
            require(comparison["draft_n_accepted"] > 0, "smoke draft produced no accepted tokens")
            write(SMOKE, receipt)
            write(Path(receipt["smoke_attempt"]["harness_result_path"]), receipt)
        else:
            write(RESULT, receipt)
    except (Exception, SystemExit) as exc:
        if not smoke:
            receipt.update(ended_at=timestamp(), complete=False, status="failed", verdict="COMPARISON_FAILED",
                           failure={"type": type(exc).__name__, "reason": str(exc)})
            write(RESULT, receipt)
        raise


if __name__ == "__main__":
    main()
