#!/usr/bin/python3
"""Capture one reference executable's original output and own-PID custody."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from capture import P, _write_new, artifact, cpu_mask

LIMIT = 32 << 20


def interrupted(number, _frame):
    raise InterruptedError(f"received signal {number}")


def run(mode, args):
    signal.signal(signal.SIGTERM, interrupted)
    pins = json.loads((P / "PINS.json").read_bytes())["artifacts"]
    executable = pins[mode]
    libraries = {v["path"]: v for k, v in pins.items() if k.startswith("instrument-lib:")}
    threads = os.environ["FILLER_THREADS"]
    expected = cpu_mask(os.environ["FILLER_CPUS"])
    if (artifact(executable["path"]) != executable or len(expected) != int(threads)
            or os.sched_getaffinity(0) != expected or args[args.index("-t") + 1] != threads):
        raise ValueError("native executable, affinity or thread argument differs from the pin")
    unit = os.environ["EXP01_LAUNCH_UNIT"]
    dest = Path(os.environ["OUT"]) / "launches"
    dest.mkdir(exist_ok=True)
    stdout_path, stderr_path = (dest / f"{unit}.{ext}" for ext in ("stdout", "stderr"))
    deadline = min(float(os.environ[key]) for key in ("FILLER_DEADLINE", "EXP01_CONTROL_END"))
    stop = Path(os.environ["FILLER_STOPFILE"])
    operator_stop = Path(os.environ["EXP01_OPERATOR_STOP"])
    argv = [executable["path"], *args]
    record = dict(schema="epyc.exp01.launch.v1", unit=unit, argv=argv, executable=executable,
                  started_at=time.time(), started_monotonic_s=time.monotonic(), samples=[],
                  mapped_artifacts={}, disposition="failed", rc=1)
    proc = None
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            if stop.exists() or operator_stop.exists() or time.time() >= deadline:
                raise InterruptedError("STOP or launch deadline before invocation")
            proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
            record["pid"] = proc.pid
            while proc.poll() is None:
                if stop.exists() or operator_stop.exists() or time.time() >= deadline:
                    raise InterruptedError("STOP or launch deadline during owned invocation")
                if max(stdout_path.stat().st_size, stderr_path.stat().st_size) > LIMIT:
                    raise ValueError("native output exceeded the capture bound")
                try:
                    mapped = set()
                    for line in Path(f"/proc/{proc.pid}/maps").read_text().splitlines():
                        fields = line.split(maxsplit=5)
                        if len(fields) == 6 and fields[5].startswith("/") and ".so" in fields[5]:
                            mapped.add(fields[5])
                    mask = os.sched_getaffinity(proc.pid)
                except (FileNotFoundError, ProcessLookupError):
                    continue
                if mask != expected:
                    raise ValueError("owned child affinity differs from the allocated mask")
                record["samples"].append(dict(own_pid=proc.pid, monotonic_s=time.monotonic(),
                                               affinity=sorted(mask), mapped=sorted(mapped)))
                time.sleep(0.05)
        record["rc"] = proc.returncode
        if proc.returncode != 0:
            raise ValueError(f"reference program exit {proc.returncode}")
        witnessed = sum(libraries.keys() <= set(sample["mapped"]) for sample in record["samples"])
        if witnessed < 2:
            raise ValueError("fewer than two in-window mapped instrument witnesses")
        record["mapped_artifacts"] = {path: artifact(path) for path in libraries}
        if record["mapped_artifacts"] != libraries:
            raise ValueError("mapped instrument identities differ from pinned libraries")
        record["disposition"] = "complete"
    except (OSError, ValueError, InterruptedError) as exc:
        record["failure"] = str(exc)
        record["rc"] = record["rc"] or 1
        stop.touch()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        record.update(ended_at=time.time(), ended_monotonic_s=time.monotonic())
        if proc is not None:
            record["native_rc"] = proc.returncode
        for name, path, stream in (("stdout", stdout_path, sys.stdout), ("stderr", stderr_path, sys.stderr)):
            if path.exists():
                record[name] = artifact(path)
                with path.open("rb") as source:
                    stream.buffer.write(source.read(LIMIT))
                    stream.buffer.flush()
        _write_new(dest / (unit + ".json"), record)
    return record["rc"]


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1], sys.argv[2:]))
