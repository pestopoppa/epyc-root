"""CH-17 frontdoor CPU comparison dispatched only by the Rowflow engine."""

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
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server_np_sweep import http_json

HERE = Path(__file__).resolve().parent
ROW = "ch17-c13-frontdoor-cpu-20261118-r4"
PORT = 19578
IMAGE = Path("/mnt/raid0/llm/kernels/builds/cpu-20261117-bda43aa17-c13")
BIN = IMAGE / "bin/llama-server"
ORDER = (("none", "mtp"), ("mtp", "none"), ("none", "mtp"))
RESULT = HERE / "RESULT.json"
SMOKE = HERE / "smoke/RESULT.json"


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
    model = Path(pins["model"]["path"])
    require({field: getattr(model.stat(), f"st_{field}") for field in pins["model"]["stat"]}
            == pins["model"]["stat"], "prepared model stat drift")
    return pins


def window():
    require(not Path(os.environ["FILLER_STOPFILE"]).exists(), "keeper STOP")
    require(time.time() < int(os.environ["FILLER_DEADLINE"]), "keeper deadline")


def cpu_options(smoke):
    def expand(cpulist):
        result = set()
        for item in cpulist.split(","):
            first, _, last = item.partition("-")
            result.update(range(int(first), int(last or first) + 1))
        return result

    allowed = os.sched_getaffinity(0)
    require(allowed and allowed == expand(os.environ["FILLER_CPUS"]), "affinity differs from grant")
    cores = {}
    for cpu in sorted(allowed):
        siblings = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
        cores.setdefault(min(expand(siblings.read_text().strip())), cpu)
    expected = 4 if smoke else 24
    require(int(os.environ["FILLER_THREADS"]) == len(cores) == expected, "wrong grant shape")
    require(smoke or len({core // 24 for core in cores}) == 1, "native comparison needs one CPU quarter")
    os.sched_setaffinity(0, set(cores.values()))
    return expected


def server_env(threads):
    hidden = {"ROCR_VISIBLE_DEVICES": "", "HIP_VISIBLE_DEVICES": "-1", "GPU_DEVICE_ORDINAL": "-1",
              "CUDA_VISIBLE_DEVICES": "-1", "GGML_VK_VISIBLE_DEVICES": "-1", "HSA_ENABLE_SDMA": "0"}
    require(os.environ["FILLER_GPU_FENCE"] == "1" and os.environ["FILLER_NEEDGPU"] == "0" and
            all(os.environ.get(key) == value for key, value in hidden.items()), "CPU GPU fence missing")
    preloads = re.split(r"[:\s]+", os.environ.get("LD_PRELOAD", "").strip())
    fence = [path for path in preloads if Path(path).is_absolute() and
             re.fullmatch(r"gpu_fence-[0-9a-f]{12}\.so", Path(path).name)]
    require(len(fence) == 1, "GPU fence shim missing")
    return {**hidden, "FILLER_GPU_FENCE": "1", "FILLER_ID": ROW,
            "FILLER_STOPFILE": os.environ["FILLER_STOPFILE"], "LD_PRELOAD": fence[0],
            "LD_LIBRARY_PATH": str(BIN.parent), "PATH": "/usr/bin:/bin", "LC_ALL": "C",
            "OMP_NUM_THREADS": str(threads), "OMP_DYNAMIC": "FALSE"}


def wait_owned_listener(proc):
    process = Path(f"/proc/{proc.pid}")
    address = f"0100007F:{PORT:04X}"
    until = time.monotonic() + 180
    while time.monotonic() < until:
        window()
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
        time.sleep(1)
    raise TimeoutError(f"private listener ownership/health missing for pid {proc.pid}")


def proc_start(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def live_custody(pid, expected_start, expected_mapped, allowed):
    proc = Path(f"/proc/{pid}")
    begin = time.monotonic_ns()
    require(proc_start(pid) == expected_start, "server process identity changed")
    mapped = set()
    for line in (proc / "maps").read_text().splitlines():
        columns = line.split(maxsplit=5)
        if len(columns) != 6:
            continue
        name = Path(columns[5]).name
        if name == BIN.name or name.startswith(("libllama", "libggml", "libmtmd")):
            mapped.add(str(Path(columns[5]).resolve()))
    require(mapped == expected_mapped, f"server mapped different project objects: {mapped ^ expected_mapped}")
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
            "start_ticks": expected_start, "mapped": sorted(mapped), "affinity_by_tid": affinities}


def request_owned(payload, pid, expected_start, expected_mapped, smoke):
    allowed = os.sched_getaffinity(0)
    start = time.monotonic_ns()
    samples = []
    with ThreadPoolExecutor(max_workers=1) as executor:
        reply = executor.submit(http_json, "POST", f"http://127.0.0.1:{PORT}/completion", payload, 150)
        while not reply.done():
            window()
            sample = live_custody(pid, expected_start, expected_mapped, allowed)
            if not reply.done():
                samples.append(sample)
            time.sleep(0.1 if smoke else 0.5)
        status, response = reply.result()
    end = time.monotonic_ns()
    require(len(samples) >= (1 if smoke else 2), "missing overlapping request custody")
    return status, response, {"start_mono_ns": start, "end_mono_ns": end, "live_samples": samples}


def run_arm(root, number, arm, threads, env, pins, smoke):
    window()
    model = pins["model"]["path"]
    require({field: getattr(Path(model).stat(), f"st_{field}") for field in pins["model"]["stat"]}
            == pins["model"]["stat"], "prepared model changed before launch")
    name = f"pair{number}-{arm}"
    args = [str(BIN), "-m", model, "--host", "127.0.0.1", "--port", str(PORT),
            "--device", "none", "-ngl", "0", "-t", str(threads), "-tb", str(threads),
            "-c", "4096" if smoke else "32768", "-np", "1", "-b", "512" if smoke else "2048",
            "-ub", "512" if smoke else "2048", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0",
            "--no-mmap", "--no-warmup", "--cache-ram", "0", "--jinja", "--reasoning", "off",
            "--chat-template-file", pins["template"], "--spec-type", "draft-mtp" if arm == "mtp" else "none"]
    if arm == "mtp":
        args += ["--spec-draft-n-max", "4"]
    events = {"arm": arm, "argv": args, "started_at": timestamp(), "requests": []}
    try:
        with (root / f"{name}.server.log").open("wb") as log:
            proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                events["pid"] = proc.pid
                with open(os.environ["FILLER_PIDFILE"], "a") as pidfile:
                    pidfile.write(f"{proc.pid}\n")
                events["owned_listener_inode"] = wait_owned_listener(proc)
                events["server_start_ticks"] = proc_start(proc.pid)
                expected_mapped = {str(Path(path).resolve()) for path in pins["files"]
                                   if Path(path).parent == BIN.parent}
                prompts = pins["prompts"][:1] if smoke else pins["prompts"]
                cap = 12 if smoke else 128
                for prompt in prompts:
                    window()
                    payload = {"prompt": prompt["prompt"], "temperature": 0, "seed": 7, "n_predict": cap,
                               "ignore_eos": True, "cache_prompt": False, "return_tokens": True,
                               "stream": False}
                    status, response, custody = request_owned(payload, proc.pid, events["server_start_ticks"],
                                                                expected_mapped, smoke)
                    events["requests"].append({"prompt_id": prompt["id"], "response": response,
                                                "custody": custody})
                    write(root / f"{name}.json", events)
                    timings = response.get("timings", {})
                    count = timings.get("predicted_n")
                    ms = timings.get("predicted_ms")
                    drafted = timings.get("draft_n", 0)
                    require(status == 200 and count == cap and type(ms) in (int, float)
                            and math.isfinite(ms) and ms > 0, f"{name}: incomplete decode")
                    require(isinstance(response.get("tokens"), list) and len(response["tokens"]) == count,
                            f"{name}: missing token identities")
                    require(type(drafted) is int and ((arm == "mtp" and drafted > 0) or
                            (arm == "none" and drafted == 0)), f"{name}: invalid draft activation")
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
    finally:
        events["ended_at"] = timestamp()
        write(root / f"{name}.json", events)
    return events


def compare(arms):
    comparisons = []
    for base, mtp in zip(arms["none"]["requests"], arms["mtp"]["requests"], strict=True):
        require(base["prompt_id"] == mtp["prompt_id"], "request pairing mismatch")
        a, b = base["response"], mtp["response"]
        tps = {name: r["timings"]["predicted_n"] * 1000 / r["timings"]["predicted_ms"]
               for name, r in (("none", a), ("mtp", b))}
        comparisons.append({"prompt_id": base["prompt_id"], "decode_tps": tps,
                            "mtp_to_none_ratio": tps["mtp"] / tps["none"],
                            "greedy_token_identity": a["tokens"] == b["tokens"],
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
        raise SystemExit(0 if RESULT.is_file() else 1)
    if sys.argv[1:] == ["--smoke-predicate"]:
        identity = smoke_identity()
        result = Path(identity["harness_result_path"])
        record = json.loads(result.read_text())
        require(record["verdict"] == "SMOKE_PASS" and record["smoke_attempt"] == identity and
                result.stat().st_mtime >= identity["attempt_epoch"], "missing current live two-arm smoke")
        return
    require(not sys.argv[1:] and os.environ.get("FILLER_ID") == ROW, "requires Rowflow allocation")
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    require(smoke == (os.environ.get("FILLER_DRYRUN") == "1"), "requires native grant or publisher smoke")
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    window()
    out = HERE / ("smoke" if smoke else "out")
    out.mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="run-", dir=out))
    pins = check_inputs()
    threads = cpu_options(smoke)
    env = server_env(threads)
    linkage = subprocess.check_output(["/bin/bash", str(HERE / "verify_ggml_linkage.sh"), str(BIN),
                                        str(BIN.parent)], env=env, text=True)
    (root / "linkage.txt").write_text(linkage)
    receipt = {"id": ROW, "candidate": pins["candidate"], "model": pins["model"], "scope": pins["scope"],
               "input_sha256": hashlib.sha256((HERE / "inputs.json").read_bytes()).hexdigest(),
               "grant": (Path(os.environ["FILLER_GRANTS_DIR"]) / f"{ROW}.grant").read_text().strip(),
               "affinity": sorted(os.sched_getaffinity(0)), "environment": env, "raw_directory": str(root),
               "started_at": timestamp(), "pairs": []}
    if smoke:
        receipt["smoke_attempt"] = smoke_identity()
    for number, order in enumerate(ORDER[:1] if smoke else ORDER, start=1):
        arms = {arm: run_arm(root, number, arm, threads, env, pins, smoke) for arm in order}
        receipt["pairs"].append({"order": order, "comparisons": compare(arms)})
        write(root / "pairs.json", receipt)
        print(f"pair {number} complete", flush=True)
    receipt.update(ended_at=timestamp(), complete=True, status="complete",
                   verdict="SMOKE_PASS" if smoke else "COMPARISON_COMPLETE",
                   pair_median_ratios=[median(item["mtp_to_none_ratio"] for item in pair["comparisons"])
                                       for pair in receipt["pairs"]])
    if smoke:
        write(SMOKE, receipt)
        write(Path(receipt["smoke_attempt"]["harness_result_path"]), receipt)
    else:
        write(RESULT, receipt)


if __name__ == "__main__":
    main()
