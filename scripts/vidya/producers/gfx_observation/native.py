#!/usr/bin/python3
"""Capture one fixed real Qwen GFX observation under allocator ownership."""
from argparse import ArgumentParser
from contextlib import ExitStack
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from observation import *  # noqa: F403

FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
KFD = Path("/sys/class/kfd/kfd/proc")
CLIENT = build_opener(ProxyHandler({}))
ENV = {"GGML_IQK": "1", "LD_LIBRARY_PATH": f"{IMAGE}:/opt/rocm/lib:/usr/lib/llvm-20/lib",
       "OMP_NUM_THREADS": "4", "HIP_VISIBLE_DEVICES": "0", "ROCR_VISIBLE_DEVICES": "0"}
CAP = 300


def write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        scratch = Path(file.name)
        try:
            file.write(canonical(data) + b"\n")
            file.flush()
            os.fsync(file.fileno())
            os.link(scratch, path)
        finally:
            scratch.unlink()


def birth(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    return (int(fields[1]), int(fields[19]))


def lock_owner():
    pid = os.getppid()
    while pid > 1:
        parent, born = birth(pid)
        proc = Path(f"/proc/{pid}")
        for d in (proc / "fd").iterdir():
            try:
                if d.readlink() != GPU_LOCK:
                    continue
                locks = (proc / "fdinfo" / d.name).read_text()
            except FileNotFoundError:
                continue
            line = next((line for line in locks.splitlines()
                         if re.match(r"^lock:\s+\d+: FLOCK\s+ADVISORY\s+WRITE\s", line)), None)
            if line:
                a, b = d.stat(), GPU_LOCK.stat()
                require((a.st_dev, a.st_ino) == (b.st_dev, b.st_ino), "GPU lock inode drift")
                return {"pid": pid, "birth": born, "fd": d.name, "path": str(GPU_LOCK),
                        "device": b.st_dev, "inode": b.st_ino, "raw": line}
        pid = parent
    raise ValueError("no exclusive allocator MI210 flock found in original ancestry")


def artifacts(work):
    return {str(path.relative_to(work)): digest(path)
            for path in sorted(work.rglob("*")) if path.is_file()}


def retain_sources(work):
    manifest = HERE / "source-manifest.json"
    closure = json.loads(manifest.read_bytes())
    require(set(closure["files"]) == set(SOURCE_FILES), "incorrect source closure")
    (work / "source").mkdir()
    for name, expected in closure["files"].items():
        dest = work / "source" / name
        shutil.copyfile(HERE / name, dest)
        require(digest(dest) == expected, f"source bytes changed: {name}")
    dest = work / manifest.name
    shutil.copyfile(manifest, dest)
    return {"locator": manifest.name, "sha256": digest(dest)}


def current_weights():
    return subprocess.check_output(
        ["/usr/bin/stat", "--printf=%n %d %i %s %y %z\n", str(MODEL), str(DRAFTER)])


def verify():
    readers = json.loads((HERE / "reader-manifest.json").read_bytes())
    for name, expected in readers.items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "unsafe reader source path")
        require(digest(HERE / "reader" / name) == expected, "planning reader source drift")
    sums = (HERE / "weights.sha256").read_text()
    require(sums == f"{MODEL_SHA}  {MODEL}\n{DRAFTER_SHA}  {DRAFTER}\n", "weight digest mismatch")
    before = (HERE / "weights.stat.before").read_bytes()
    require(before == (HERE / "weights.stat.after").read_bytes() == current_weights(),
            "prehashed weight stat drift")
    require(SERVER.is_file() and HIP.is_file() and LIBRARY.resolve(strict=True) == LIBRARY_REAL,
            "missing pinned server, HIP DSO or ROCm library")
    require(digest(SERVER) == SERVER_SHA and digest(HIP) == HIP_SHA
            and digest(LIBRARY) == LIBRARY_SHA, "pinned server, HIP or ROCm bytes differ")


def own_listener(pid):
    proc = Path(f"/proc/{pid}")
    sockets = set()
    for d in (proc / "fd").iterdir():
        try:
            link = str(d.readlink())
        except FileNotFoundError:
            continue
        if link.startswith("socket:["):
            sockets.add(link[8:-1])
    port = f"0100007F:{PORT:04X}"
    return next((cols[9] for line in (proc / "net/tcp").read_text().splitlines()[1:]
                 if (cols := line.split())[1] == port and cols[3] == "0A" and cols[9] in sockets), "")


def witness(pid):
    proc = Path(f"/proc/{pid}")
    kfd = KFD / str(pid)
    rows = [fields for line in (proc / "maps").read_text().splitlines()
            if (fields := line.split(maxsplit=5))[-1].endswith(HIP.name)]
    require(rows and all(row[5] == str(HIP) and int(row[4]) == HIP.stat().st_ino
                         and tuple(map(lambda word: int(word, 16), row[3].split(":")))
                         == (os.major(HIP.stat().st_dev), os.minor(HIP.stat().st_dev))
                         for row in rows), "server does not map the pinned HIP DSO")
    vram = {f.name: int(f.read_text()) for f in kfd.glob("vram*")}
    listener = own_listener(pid)
    require(listener and (proc / "exe").resolve(strict=True) == SERVER
            and list((proc / "cmdline").read_bytes().rstrip(b"\0").decode().split("\0")) == argv()
            and kfd.is_dir() and sum(vram.values()) > 0,
            "own listener, launch identity, KFD or VRAM witness missing")
    return {"pid": pid, "birth": birth(pid)[1], "bound_loopback_inode": listener,
            "exe": str(SERVER), "argv": argv(), "kfd_vram_bytes": vram,
            "hip_mapping": {str(HIP): HIP_SHA}, "at_ns": time.monotonic_ns()}


def wait_for_kfd_release(pid, remaining):
    # The driver can retain the sysfs entry briefly after wait() reaps the child.
    kfd = KFD / str(pid)
    until = time.monotonic() + 3
    while kfd.exists():
        delay = min(remaining(), until - time.monotonic())
        if delay <= 0:
            return False
        time.sleep(min(0.05, delay))
    return True


def http(parts, remaining, data=None):
    url = f"http://127.0.0.1:{PORT}/{parts}"
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with CLIENT.open(req, timeout=min(remaining(), 20 if data else 2)) as response:
        require(response.status == 200, f"HTTP {response.status}")
        body = response.read(1_048_577)
        require(len(body) <= 1_048_576, "response exceeds fixed native capture bound")
        return body


def run(out):
    work = HERE / ("native-" + uuid4().hex)
    work.mkdir()
    smoke_path = os.environ.get("FILLER_DRYRUN_DIR")
    mode = "publisher-smoke" if smoke_path else "official"
    report = {"schema": SCHEMA, "row_id": ROW, "run_id": work.name, "mode": mode,
              "research_commit": RESEARCH, "build_commit": BUILD, "target": TARGET,
              "model_sha256": MODEL_SHA, "drafter_sha256": DRAFTER_SHA, "started_at": now(),
              "status": "UNKNOWN", "observed_window": None, METRIC: None,
              "full_claim_coverage": None, "per_process_attribution": None,
              "binary_busy_time": None}
    process = None
    try:
        require(os.environ["FILLER_ID"] == ROW and os.environ.get("FILLER_NEEDGPU") == "1"
                and os.environ.get("FILLER_GPU_FENCE") == "0", "no authorized GPU allocation")
        stop = Path(os.environ["FILLER_STOPFILE"])
        deadline = int(os.environ["FILLER_DEADLINE"])
        cap = time.monotonic() + CAP

        def remaining():
            require(not stop.exists(), "STOP")
            left = min(cap - time.monotonic(), deadline - time.time())
            require(left > 0, "deadline reached")
            return left

        def interrupted(signum, _frame):
            raise ValueError(f"interrupted by signal {signum}")

        for sig in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, remaining())
        allowed = os.sched_getaffinity(0)
        cpus = sorted(allowed & set(range(184, 192)))[:4]
        require(len(cpus) == 4, "four granted MI210 host CPUs required")
        os.sched_setaffinity(0, cpus)
        report["cpus"] = cpus
        grant_dir = Path(smoke_path) / "grants" if smoke_path else FLAGS / "grants"
        grant = grant_dir / (ROW + ".grant")
        grant_text = grant.read_text()
        require(re.search(r"(?:^|[\s,])mi210_0(?:[\s,]|$)", grant_text.replace("regions=", "", 1))
                and "gpu-quiet" in grant_text,
                "grant omits MI210 or GPU quiet")
        require((grant_dir.parent.name == ROW) if smoke_path else grant_dir == FLAGS / "grants",
                "unexpected allocator grant directory")
        report["grant"] = {"path": str(grant), "raw": grant_text, "deadline_epoch": deadline}
        report["lock_begin"] = lock_owner()
        report["source_manifest"] = retain_sources(work)
        verify()
        gpu_counter.LIBRARY = LIBRARY  # host ROCm 6.2 ABI at its pinned installed path
        with (work / "ggml-linkage.log").open("wb") as logfile:
            subprocess.run(["/bin/bash", str(HERE / "verify_ggml_linkage.sh"), str(SERVER), str(IMAGE)],
                           env={**os.environ, **ENV}, stdout=logfile, stderr=subprocess.STDOUT,
                           check=True, timeout=min(remaining(), 10))
        with ExitStack() as stack, (work / "server.log").open("wb") as log:
            collector = gpu_counter.attach(stack, "mi210_0",
                                           lambda trace: write(work / "gfx-counter.json", trace))
            start_trace = collector.snapshot()
            require(not start_trace["errors"], f"collector refused: {start_trace['errors']}")
            (work / "request.json").write_bytes(canonical(REQUEST))
            process = subprocess.Popen(argv(), env={**os.environ, **ENV}, stdout=log,
                                       stderr=subprocess.STDOUT)
            try:
                with Path(os.environ["FILLER_PIDFILE"]).open("a") as pidfile:
                    print(process.pid, file=pidfile)
                while True:
                    require(process.poll() is None, "server exited before health")
                    if own_listener(process.pid):
                        try:
                            http("health", remaining)
                            break
                        except (HTTPError, URLError, TimeoutError):
                            pass
                    remaining()
                    time.sleep(0.15)
                report["server_before"] = witness(process.pid)
                collector.sample("request:start")
                report["request_started_ns"] = time.monotonic_ns()
                response = http("completion", remaining, (work / "request.json").read_bytes())
                report["request_ended_ns"] = time.monotonic_ns()
                (work / "response.json").write_bytes(response)
                collector.sample("request:end")
                report["server_after"] = witness(process.pid)
                remaining()
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
                expected_listener = report.get("server_before", {}).get("bound_loopback_inode")
                tcp = Path("/proc/net/tcp").read_text().splitlines()[1:]
                listener_gone = bool(expected_listener) and all(
                    cols[3] != "0A" or cols[9] != expected_listener for line in tcp if (cols := line.split()))
                cleanup = report["server_cleanup"] = {
                    "returncode": process.returncode,
                    "verified_gone": not Path(f"/proc/{process.pid}").exists(),
                    "verified_kfd_gone": False,
                    "verified_listener_released": listener_gone,
                }
                if cleanup["verified_gone"] and listener_gone:
                    cleanup["verified_kfd_gone"] = wait_for_kfd_release(process.pid, remaining)
        report["lock_end"] = lock_owner()
        require(report["lock_begin"] == report["lock_end"] and grant_text == grant.read_text(),
                "GPU ownership or calendar grant changed")
        require(current_weights() == (HERE / "weights.stat.before").read_bytes(),
                "weight stat drift during request")
        remaining()
        from reader import validate_workload
        trace = json.loads((work / "gfx-counter.json").read_bytes())
        report["files"] = artifacts(work)
        report["ended_at"] = now()
        reduced = counter_window(trace, report["request_started_ns"], report["request_ended_ns"])
        report.update({"observed_window": reduced["observed_window"], METRIC: reduced[METRIC]})
        report["belief_measurements"] = [
            native_measurement(report, report["files"]["gfx-counter.json"], reduced)]
        validate_workload(work, report)
        report["status"] = "observed"
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError) as exc:
        report.update({"failure": f"{type(exc).__name__}: {exc}", "observed_window": None,
                       METRIC: None, "belief_measurements": []})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        report["files"] = artifacts(work)
        report.setdefault("ended_at", now())
        report["self_sha256"] = seal(report)
        write(work / "observation.json", report)
        write(out, {"id": ROW, "row_id": ROW, "run_id": work.name, "status": report["status"],
                    "mode": mode, "workload_requests": int(report["status"] == "observed"),
                    "observation": str(work / "observation.json"),
                    "sha256": digest(work / "observation.json")})
    if report["status"] == "observed" and mode == "official":
        try:
            signal.setitimer(signal.ITIMER_REAL, remaining())
            from reader import canary
            result = canary(work / "observation.json", HERE / (work.name + "-canary"))
            summary = json.loads(out.read_bytes())
            summary["planning_context"] = result
            temp = out.with_suffix(".updated")
            write(temp, summary)
            os.replace(temp, out)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            summary = json.loads(out.read_bytes())
            summary.update(status="UNKNOWN", planning_failure=f"{type(exc).__name__}: {exc}")
            temp = out.with_suffix(".updated")
            write(temp, summary)
            os.replace(temp, out)
            return 1
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    return 0 if report["status"] == "observed" else 1


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "complete", "verify"))
    action = parser.parse_args().action
    if action == "verify":
        verify()
        return 0
    smoke_out = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    out = Path(smoke_out) if smoke_out else HERE / "official-RESULT.json"
    if action == "run":
        return run(out)
    try:
        summary = json.loads(out.read_bytes())
        capture = Path(summary["observation"])
        require(capture.parent.parent == HERE and digest(capture) == summary["sha256"],
                "unbound native result")
        from reader import load
        load(capture, allow_smoke=bool(smoke_out))
        require(summary["status"] == "observed", "incomplete native/planning result")
        if not smoke_out:
            context = summary["planning_context"]
            require(context["eligible"] == 1 and context["refused"] == 0
                    and context["visible"] == {"exact_ak27b": True, "cpu": False,
                        "other_weights": False, "same_name_other_digest": False},
                    "official planner context incomplete")
        return 0
    except (KeyError, TypeError, ValueError, OSError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
