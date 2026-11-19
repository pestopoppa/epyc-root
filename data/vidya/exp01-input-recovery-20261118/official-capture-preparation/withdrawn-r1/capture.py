"""Capture immutable EXP01 run identity and original native unit records."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

P = Path(__file__).resolve().parent
ARMS = ("Q4KM", "IQ4KT", "IQ2XXS", "IQ2KT")
ALLOCATION = ("FILLER_ID", "FILLER_CPUS", "FILLER_THREADS", "FILLER_DEADLINE")


def artifact(path, hash_bytes=True):
    path = Path(path).resolve(strict=True)

    def metadata():
        stat = path.stat()
        return dict(path=str(path), size=stat.st_size, dev=stat.st_dev, ino=stat.st_ino,
                    mtime_ns=stat.st_mtime_ns, ctime_ns=stat.st_ctime_ns)

    original = metadata()
    if hash_bytes:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if original != metadata():
            raise ValueError(f"artifact changed during hashing: {path}")
        original["sha256"] = digest
    return original


def checked():
    pins = json.loads((P / "PINS.json").read_bytes())
    for name, expected in pins["artifacts"].items():
        if artifact(expected["path"]) != expected:
            raise ValueError(f"artifact pin changed: {name}")
    if set(pins["models"]) != set(ARMS):
        raise ValueError("prepared model set differs")
    for arm, model in pins["models"].items():
        if (artifact(model["metadata"]["path"], False) != model["metadata"]
                or not re.fullmatch(r"[0-9a-f]{64}", model["sha256_pinned"])):
            raise ValueError(f"prepared model identity changed: {arm}")
    for tree, head in pins["trees"].items():
        actual = subprocess.check_output(["git", "-C", tree, "rev-parse", "HEAD"], text=True)
        dirty = subprocess.check_output(["git", "-C", tree, "status", "--porcelain",
                                         "--untracked-files=no"], text=True)
        if actual.strip() != head or dirty.strip():
            raise ValueError(f"source tree head or tracked state differs: {tree}")
    for name, digest in json.loads((P / "SOURCE.json").read_bytes()).items():
        if artifact(P / name)["sha256"] != digest:
            raise ValueError(f"producer source differs: {name}")
    return pins


def cpu_mask(value):
    result = set()
    for span in value.split(","):
        first, _, last = span.partition("-")
        start, end = int(first), int(last or first)
        if not 0 <= start <= end <= 4095:
            raise ValueError("invalid CPU interval")
        result.update(range(start, end + 1))
    return result


def _write_new(path, row):
    with path.open("x") as stream:
        json.dump(row, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _official_plan(pins, allocation):
    source = pins["artifacts"]
    if (os.environ.get("FILLER_DRYRUN") == "1"
            or artifact(os.environ["MODELSET"]) != source["modelset"]
            or artifact(os.environ["EXP01_JOB_SOURCE"]) != source["producer"]
            or os.environ["IK"] not in pins["trees"]):
        raise ValueError("official invocation differs from the sealed source or uses smoke")
    launches, pp, tg, cap = (int(os.environ[key]) for key in ("LAUNCHES", "PP", "TG", "CAP_S"))
    if not 2 <= launches <= 3 or (pp, tg) != (512, 128) or not 0 < cap <= 5400:
        raise ValueError("official invocation differs from the bounded EXP01 recipe")
    items = [json.loads(line) for line in Path(source["items"]["path"]).read_bytes().splitlines()]
    item_ids = [item["id"] for item in items]
    if len(item_ids) != 24 or len(set(item_ids)) != 24:
        raise ValueError("official EXP01 expects the pinned 24 distinct items")
    planned_end = float(os.environ["EXP01_CONTROL_END"])
    if not math.isfinite(planned_end) or planned_end > float(allocation["FILLER_DEADLINE"]):
        raise ValueError("launch deadline differs from the grant")
    return dict(speed_arms=list(ARMS), launches_per_arm=launches, pp=pp, tg=tg, cap_s=cap,
                paired_item_ids=item_ids, planned_looks=list(range(2, launches + 1)),
                look_source=artifact(P / "look.py")["sha256"], launch_deadline=planned_end,
                stop_file=os.environ["FILLER_STOPFILE"])


def begin(out, mode="capture-control"):
    pins = checked()
    out = Path(out).resolve()
    allocation = {key: os.environ[key] for key in ALLOCATION}
    mask = cpu_mask(allocation["FILLER_CPUS"])
    deadline = float(allocation["FILLER_DEADLINE"])
    if (mask != os.sched_getaffinity(0) or len(mask) != int(allocation["FILLER_THREADS"])
            or not math.isfinite(deadline) or deadline <= time.time()):
        raise ValueError("allocation must match live affinity, native threads and a future deadline")
    grant = Path(os.environ.get("FILLER_GRANTS_DIR", "/mnt/raid0/llm/tmp/compute-flags/grants"))
    row_id = allocation["FILLER_ID"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", row_id):
        raise ValueError("invalid captured grant identity")
    grant = grant / (row_id + ".grant")
    identity = artifact(grant)
    if identity["size"] > 65536:
        raise ValueError("unbounded grant")
    grant_raw = grant.read_text()
    fields = dict(field.split("=", 1) for field in grant_raw.split())
    if (hashlib.sha256(grant_raw.encode()).hexdigest() != identity["sha256"]
            or fields["id"] != row_id or fields["regions"] != allocation["FILLER_CPUS"]):
        raise ValueError("grant source differs from the allocated row")
    if mode == "official":
        planned = _official_plan(pins, allocation)
    elif mode == "capture-control" and len(mask) == 4:
        planned = dict(purpose="source-capture-diagnostic-only", speed_arms=list(ARMS),
                       launches_per_arm=1, paired_items=1, pp=512, tg=128,
                       item_selection="first original pinned item in file order",
                       no_pilot_decision=True)
    else:
        raise ValueError("unknown mode or source control without four allocated CPUs")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("a fresh EXP01 output directory is required")
    run = dict(schema="epyc.exp01.capture.v1", run_id=uuid.uuid4().hex, mode=mode,
               started_at=time.time(), pins=pins, source_sha256=artifact(P / "SOURCE.json")["sha256"],
               grant=dict(identity=identity, raw=grant_raw), allocation=allocation, planned=planned)
    _write_new(out / "RUN.json", run)
    return run


def emit(result, row):
    result = Path(result)
    run = json.loads((result.parent / "RUN.json").read_bytes())
    unit = row["unit"]
    if not re.fullmatch(r"[\w.-]+", unit):
        raise ValueError("invalid native unit identity")
    if row.get("kind") in ("speed", "quality"):
        if (row["cpus"] != run["allocation"]["FILLER_CPUS"]
                or row["threads"] != int(run["allocation"]["FILLER_THREADS"])):
            raise ValueError("native unit resource mismatch")
    row = dict(row)
    carrier = dict(schema="epyc.exp01.unit_capture.v1", run_id=run["run_id"], mode=run["mode"],
                   allocation=run["allocation"], written_at=time.time())
    if row.get("kind") in ("speed", "quality"):
        carrier["launch"] = artifact(result.parent / "launches" / (unit + ".json"))
    if row.get("kind") == "speed":
        carrier["raw"] = artifact(result.parent / (unit + ".json"))
    row["belief_capture"] = carrier
    with result.open("a") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return row


def terminal_official(out, code):
    out = Path(out)
    run = json.loads((out / "RUN.json").read_bytes())
    if run["mode"] != "official":
        raise ValueError("official terminal requires an official source envelope")
    result = out / "results.jsonl"
    rows = [json.loads(line) for line in result.read_bytes().splitlines()]
    if any(row["belief_capture"]["run_id"] != run["run_id"]
           or row["belief_capture"]["mode"] != run["mode"]
           or row["belief_capture"]["allocation"] != run["allocation"] for row in rows):
        raise ValueError("mixed native output")
    plan = run["planned"]
    ended = time.time()
    stop = Path(plan["stop_file"]).exists()
    summary = out / "SUMMARY.json"
    success = (code == 0 and rows and rows[0].get("ok") is True
               and all(row.get("rc", 0) == 0 for row in rows)
               and summary.is_file() and _complete_schedule(rows, plan)
               and not stop and ended <= plan["launch_deadline"])
    record = dict(run_id=run["run_id"], mode="official", rc=code, ended_at=ended,
                  state="complete-unprojected" if success else "partial-or-failed",
                  stop_file_observed=stop, deadline_reached=ended > plan["launch_deadline"],
                  raw=artifact(result), summary=artifact(summary) if summary.is_file() else None)
    _write_new(out / "TERMINAL.json", record)
    return 0 if success else 4


def _complete_schedule(rows, plan):
    expected = [(None, "validity")]
    looks = [row for row in rows if row.get("kind") == "look"]
    stopped = set()
    for launch in range(1, plan["launches_per_arm"] + 1):
        for first, second in zip(ARMS[::2], ARMS[1::2], strict=True):
            look = f"look-{first}-{second}"
            if look in stopped:
                continue
            expected.extend(("speed", f"speed-{arm}-{launch}") for arm in (first, second))
            if launch in plan["planned_looks"]:
                if not looks or looks[0]["unit"] != look:
                    return False
                expected.append(("look", look))
                if looks.pop(0).get("stop") in ("answer", "futility"):
                    stopped.add(look)
    expected.extend(("quality", f"q-{arm}-{item}")
                    for item in plan["paired_item_ids"] for arm in ARMS[:2])
    return [(row.get("kind"), row["unit"]) for row in rows] == expected


if __name__ == "__main__":
    command, *args = sys.argv[1:]
    if command == "check":
        checked()
    elif command == "begin-official":
        begin(args[0], mode="official")
    elif command == "emit":
        emit(args[0], json.loads(args[1]))
    elif command == "terminal-official":
        raise SystemExit(terminal_official(args[0], int(args[1])))
    else:
        raise SystemExit(f"unknown EXP01 capture action: {command}")
