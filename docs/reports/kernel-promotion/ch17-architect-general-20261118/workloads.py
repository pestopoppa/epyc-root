"""Host claim workload custody for the 96-physical-CPU comparison.

The llama and autopilot markers follow collect_process_blockers in the K35
acquisition runner. Add OCR detection and per-process CPU accounting because a
whole-physical-host timing grant also competes with foreign SMT workloads.
"""
from pathlib import Path
import os
import re
import time

PROC = Path("/proc")
LLAMA = {"llama-server", "llama-cli", "llama-bench", "llama-mtmd-cli"}
AUTOPILOT = {"autopilot.py", "start_fable_authority_daemon.py", "autopilot_supervisor.py"}
OCR = re.compile(r"(^|[_.-])(ocr|paddleocr|tesseract|surya|easyocr)([_.-]|$)", re.I)
MAX_PROCESS_CORES = 0.25
MAX_AGGREGATE_CORES = 1.0
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")


def snapshot(owned):
    point = time.monotonic_ns()
    observed, known, unknown = {}, [], []
    for entry in PROC.iterdir():
        if not entry.name.isdecimal():
            continue
        pid = int(entry.name)
        try:
            stat = (entry / "stat").read_text(errors="replace")
            fields = stat.rsplit(")", 1)[1].split()
            start = int(fields[19])
            if owned.get(pid) == start or fields[0] in ("Z", "X"):
                continue
            command = stat.split("(", 1)[1].rsplit(")", 1)[0]
            observed[pid] = (start, int(fields[11]) + int(fields[12]), command)
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            unknown.append(pid)
            continue
        entrypoints = {command, *(Path(os.fsdecode(item)).name for item in argv[:3])}
        if entrypoints & (LLAMA | AUTOPILOT) or any(OCR.search(name) for name in entrypoints):
            known.append({"pid": pid, "start_ticks": start, "command": command})
    return point, observed, known, unknown


def compare(before, after):
    before_ns, old, _, _ = before
    after_ns, new, _, _ = after
    elapsed = (after_ns - before_ns) / 1e9
    active = []
    for pid, (birth, ticks, command) in new.items():
        previous = old.get(pid)
        if previous and previous[0] == birth:
            delta = ticks - previous[1]
        elif birth / CLOCK_TICKS >= before_ns / 1e9:
            delta = ticks
        else:
            continue
        if delta > 0:
            active.append({"pid": pid, "start_ticks": birth, "command": command,
                           "cpu_cores_observed": delta / CLOCK_TICKS / elapsed})
    total = sum(item["cpu_cores_observed"] for item in active)
    return {
        "start_mono_ns": before_ns, "end_mono_ns": after_ns, "known": before[2] + after[2],
        "unreadable_pids": sorted(set(before[3] + after[3])),
        "foreign_aggregate_cores": total, "foreign_cpu": active,
        "max_process_cores": MAX_PROCESS_CORES, "max_aggregate_cores": MAX_AGGREGATE_CORES,
        "refused": bool(before[2] or after[2] or before[3] or after[3]
                        or total >= MAX_AGGREGATE_CORES
                        or any(item["cpu_cores_observed"] >= MAX_PROCESS_CORES for item in active)),
    }
