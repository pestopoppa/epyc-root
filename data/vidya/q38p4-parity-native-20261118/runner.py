import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

import producer as p
from settings import ROOT, ROW, HF, BIN, IMAGE, PORTS, FULL_CPUS, llama_args, vllm_args

DOCKER = "/usr/bin/docker"


def stopped(*_):
    raise InterruptedError("row stopped")


def check_assets():
    for name, pin in json.loads((ROOT / "asset-pins.json").read_bytes()).items():
        st = Path(name).stat()
        p.require((st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino, st.st_dev)
                  == (pin["size"], pin["mtime_ns"], pin["ctime_ns"], pin["inode"], pin["device"]),
                  f"asset changed after pregrant pin: {name}")


def command(*argv, **kwargs):
    return subprocess.run(argv, check=True, timeout=12, **kwargs)


def until_ready(port, pid, seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        p.birth(pid)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"owned server did not become ready on port {port}")


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    return process.returncode


def arm_capture(arm, pid, capture, container=None):
    args = [sys.executable, "-B", str(ROOT / "producer.py"), "arm", str(capture),
            arm, str(PORTS[arm]), str(pid)]
    if container is not None:
        args.extend(("--container", container))
    process = subprocess.Popen(args)
    try:
        rc = process.wait(timeout=140)
        p.require(rc == 0, f"{arm} exchange exited {rc}")
    finally:
        stop_process(process)


def run_llama(capture, scratch, cpus, smoke):
    env = {k: v for k, v in os.environ.items() if k not in (
        "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES", "LD_PRELOAD")}
    env.update(FILLER_ID=os.environ.get("FILLER_ID", ROW), LD_LIBRARY_PATH=str(BIN) + ":/opt/rocm/lib", OMP_NUM_THREADS=str(len(cpus)))
    with (scratch / "llama-server.log").open("xb") as log:
        process = subprocess.Popen(["/usr/bin/taskset", "-c", ",".join(map(str, cpus)), *llama_args(smoke)],
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            until_ready(PORTS["llama"], process.pid, 65 if smoke else 100)
            arm_capture("llama", process.pid, capture)
        finally:
            rc = stop_process(process)
            p.artifact(scratch / "llama-stop.json", {"pid": process.pid, "exit_status": rc})
            if (capture / "llama/exchange.json").exists():
                p.require(p.capture_cleanup(capture, "llama") == 0, "llama cleanup verification refused")


def inspect_container(ref):
    inspect = subprocess.run([DOCKER, "inspect", "--type", "container", ref], timeout=10,
                             capture_output=True)
    if inspect.returncode != 0 and b"No such" in inspect.stderr:
        return None
    inspect.check_returncode()
    container, = json.loads(inspect.stdout)
    return container


def owned_container(name, owner, expected_id=None):
    container = inspect_container(name)
    if container is None:
        return None
    labels = container["Config"]["Labels"] or {}
    p.require(container["Name"] == "/" + name and labels.get("org.epyc.q38p4.owner") == owner
              and p.SHA.fullmatch(container["Id"])
              and (expected_id is None or container["Id"] == expected_id),
              "container name, ownership token or ID differs")
    return container


def run_vllm(capture, scratch, cpus):
    owner = f"{ROW}-{os.getpid()}-{time.time_ns()}"
    name = owner
    config = [
        DOCKER, "create", "--pull", "never", "--name", name, "--label", f"org.epyc.q38p4.owner={owner}",
        "--network", "host", "--device", "/dev/kfd", "--device", "/dev/dri", "--group-add", "992",
        "-u", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp", "-e", "HF_HUB_OFFLINE=1",
        "-e", f"FILLER_ID={os.environ.get('FILLER_ID', ROW)}",
        "--ipc", "host", "--security-opt", "seccomp=unconfined", "--cpuset-cpus", ",".join(map(str, cpus)),
        "-v", f"{HF}:/model:ro", "--entrypoint", "python3", IMAGE, *vllm_args()[1:],
    ]
    container = None
    logger = None
    with (scratch / "vllm-server.log").open("xb") as log:
        try:
            created = command(*config, stdout=subprocess.PIPE, text=True).stdout.strip()
            p.require(p.SHA.fullmatch(created), "Docker did not return the full owned container ID")
            container = created
            p.require(owned_container(name, owner, container) is not None, "created vLLM container missing")
            p.artifact(scratch / "vllm-owned.json", {"id": container, "ownership": owner, "argv": config})
            command(DOCKER, "start", container, stdout=log, stderr=subprocess.STDOUT)
            logger = subprocess.Popen([DOCKER, "logs", "-f", container], stdout=log, stderr=subprocess.STDOUT)
            state = owned_container(name, owner, container)
            p.require(state is not None and state["State"]["Running"], "owned vLLM container stopped")
            pid = state["State"]["Pid"]
            p.require(type(pid) is int and pid > 0, "owned vLLM container has no running init")
            until_ready(PORTS["vllm"], pid, 185)
            arm_capture("vllm", pid, capture, container)
        finally:
            try:
                state = owned_container(name, owner, container)
                stop_rc = None
                if state is not None:
                    container = state["Id"]
                    if state["State"]["Running"]:
                        termination = subprocess.run([DOCKER, "stop", "--time", "10", container],
                                                     timeout=16, stdout=log, stderr=subprocess.STDOUT)
                        stop_rc = termination.returncode
                    command(DOCKER, "rm", "--force", container, stdout=log, stderr=subprocess.STDOUT)
                absent = owned_container(name, owner, container) is None
                p.artifact(scratch / "vllm-stop.json", {"container": container, "stop_rc": stop_rc, "absent": absent})
                p.require(absent, "owned vLLM container still exists")
                if (capture / "vllm/exchange.json").exists():
                    p.require(p.capture_cleanup(capture, "vllm") == 0, "vLLM cleanup verification refused")
            finally:
                if logger is not None:
                    stop_process(logger)


def main():
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    dryrun = os.environ.get("FILLER_DRYRUN") == "1"
    p.require(smoke == dryrun, "entry requires production mode or the publisher's isolated smoke")
    mode = "smoke" if smoke else "native"
    if smoke:
        dry_dir = Path(os.environ["FILLER_DRYRUN_DIR"])
        result = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
        scratch = ROOT / "smoke" / result.parent.name
        grant = dry_dir / "grants" / f"{ROW}.grant"
    else:
        grant = Path(os.environ.get("FILLER_GRANTS_DIR", "/mnt/raid0/llm/tmp/compute-flags/grants")) / f"{ROW}.grant"
        scratch = ROOT / "official"
        result = scratch / "RESULT.json"
    try:
        scratch.mkdir(parents=True)
        check_assets()
        cpu_set = set(os.sched_getaffinity(0))
        permit = cpu_set & FULL_CPUS
        p.require(len(permit) >= (4 if smoke else 8), "row CPU affinity lacks its reserved threads")
        cpus = sorted(permit)[:4] if smoke else sorted(permit)
        plan = scratch / "plan.json"
        shutil.copyfile(ROOT / f"{mode}-plan.json", plan)
        capture = scratch / "capture"
        p.init(capture, plan, grant, ROOT / "receipts" / mode)
    except Exception as exc:
        report = {"mode": mode, "state": "unstarted", "status": "UNKNOWN", "accepted": False,
                  "native_unit_count": 0, "finished_ns": time.time_ns(),
                  "error": f"{type(exc).__name__}: {exc}"[:4000]}
        output = result if not result.exists() else ROOT / f"unstarted-{os.getpid()}-{time.time_ns()}.json"
        p.artifact(output, report)
        print(json.dumps(report))
        return 2
    terminal = "failed"
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stopped)
    try:
        run_llama(capture, scratch, cpus, smoke)
        if not smoke:
            run_vllm(capture, scratch, cpus)
        terminal = "finished"
    except Exception as exc:
        terminal = "stopped" if isinstance(exc, InterruptedError) else "failed"
        p.artifact(capture / "failure.json", {"type": type(exc).__name__, "error": str(exc)[:4000]})
    finally:
        disposition = p.close(capture, terminal)
    actual = disposition["status"]
    accepted = actual in ({"smoke-pass"} if smoke else {"match", "divergence"})
    report = {"unit_id": "llama-hip-smoke" if smoke else "q38p4-greedy-comparison",
              "mode": mode, "status": actual, "finished_ns": time.time_ns(),
              "accepted": accepted, "capture": str(capture / p.SEAL_NAME), "cpus": cpus,
              "native_unit_count": 0 if smoke else int(accepted), "disposition": disposition}
    if smoke:
        p.artifact(scratch / "RESULT.json", report)
    p.artifact(result, report)
    print(json.dumps(report))
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
