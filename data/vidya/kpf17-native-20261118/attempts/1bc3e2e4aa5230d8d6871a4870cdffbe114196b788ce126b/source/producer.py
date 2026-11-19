"""Prospective private KPF-17 map-revalidation fixture and read-only evidence checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import signal
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "kpf17.alt17-custody-race.v1"
CAPTURE = "epyc.kpf17.map_revalidation_capture.v1"
ROW = "vb-kpf17-map-revalidation-20261118"
SOURCE_PINS = {
    "custody.py": "ab6d10e509d7483963a39b0da2caccab4ac8b85ee33a9e0b117107601d8d8702",
    "binding.json": "5b56f806a39f24a2f68dafe147b5b56295a2975fea3914bca2a388e571b16b82",
    "input_seal.json": "a4e6c0dc65e5e58d800e7cf52cd1285385ce027cbefb3fdbddaabf947ec14c99",
}
FILES = ("libggml.so", "libggml-base.so", "libggml-cpu.so", "libllama.so", "libllama-common.so")
LIMIT = "Private fixture only. Scope ends at the second validate_maps call following the overwrite."
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
MUTATED = b"private mutated fixture\0" * 128


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(record):
    return sha(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def write(path, record):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".kpf17-")
    try:
        with os.fdopen(fd, "w") as file:
            file.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.link(temp, path)
    finally:
        os.unlink(temp)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def original(name):
    return (b"private approved fixture " + name.encode() + b"\0") * 128


def source_identity(directory):
    actual = {name: sha((directory / name).read_bytes()) for name in SOURCE_PINS}
    need(actual == SOURCE_PINS, "source or original input seal changed")
    seal = json.loads((directory / "input_seal.json").read_text())
    binding = json.loads((directory / "binding.json").read_text())
    need(seal["custody_source_sha256"] == binding["runner_files"]["custody.py"] == actual["custody.py"]
         and seal["source_binding_sha256"] == actual["binding.json"], "inconsistent retained source seals")
    return actual


def cpus(text):
    result = set()
    for segment in text.split(","):
        lo, dash, hi = segment.partition("-")
        result.update(range(int(lo), int(hi if dash else lo) + 1))
    return result


def grant_fields(raw):
    return dict(part.split("=", 1) for part in raw.split() if "=" in part)


def grant_bounds(record):
    return tuple(datetime.fromisoformat(record[key].replace("Z", "+00:00")).timestamp()
                 for key in ("start", "end"))


def ended_utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def guard(context, stop):
    if stop.exists() or time.time() >= context["deadline_epoch"]:
        raise InterruptedError("STOP or deadline")


def no_external_exec(event, _args):
    if event in {"subprocess.Popen", "os.exec", "os.posix_spawn", "os.system"}:
        raise RuntimeError("private map fixture cannot execute an external program")


def acquire(context, threads):
    smoke = context["result_kind"] == "smoke"
    need(os.environ.get("FILLER_ID") == ROW, "foreign row")
    grant_dir = Path(os.environ["FILLER_DRYRUN_DIR"]) / "grants" if smoke else FLAGS / "grants"
    grant_path = grant_dir / (ROW + ".grant")
    raw = grant_path.read_bytes()
    grant = grant_fields(raw.decode())
    allowed = cpus(os.environ["FILLER_CPUS"])
    need(allowed == os.sched_getaffinity(0) == cpus(grant.get("cpus", grant["regions"]))
         and len(allowed) >= threads, "grant affinity mismatch")
    need((grant.get("kind") == "rowflow-dryrun" and grant.get("id") == ROW) if smoke
         else grant.get("kind") != "rowflow-dryrun", "wrong grant purpose")
    # Full sub-quarter grants can include the SMT siblings. Consume the four lowest grant CPUs.
    selected = sorted(allowed)[:threads]
    os.sched_setaffinity(0, selected)
    need(sorted(os.sched_getaffinity(0)) == selected, "fixture affinity mismatch")
    start, end = grant_bounds(grant)
    deadline = min(int(os.environ["FILLER_DEADLINE"]), context["started_epoch"] + 300)
    need(start <= time.time() < deadline < end, "no active grant window")
    context.update(grant_path=str(grant_path), grant_text=raw.decode(), grant_sha256=sha(raw),
                   granted_cpus=sorted(allowed), fixture_cpus=selected, deadline_epoch=deadline)


def load_validator(directory):
    source_identity(directory)
    path = directory / "custody.py"
    raw = path.read_bytes()
    need(sha(raw) == SOURCE_PINS[path.name], "retained validator changed at execution")
    namespace = {"__file__": str(path), "__name__": "kpf17_retained_validator"}
    exec(compile(raw, str(path), "exec"), namespace)
    return namespace["validate_maps"]


def map_line(path, index, stat):
    addr = 0x100000 + index * 0x1000
    return (f"{addr:x}-{addr+0x1000:x} r-xp 00000000 "
            f"{os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x} {stat.st_ino} {path}")


def file_sample(path, index):
    stat = path.stat()
    return {"map": map_line(path, index, stat), "sha256": sha(path.read_bytes())}


def exercise(directory, validate, check, observed):
    """Original validator and private input bytes, synchronized before the second call."""
    with tempfile.TemporaryDirectory(prefix="private-fixture-", dir=directory) as fixture:
        observed["fixture"] = fixture
        paths = [Path(fixture) / name for name in FILES]
        for path in paths:
            path.write_bytes(original(path.name))
        before = [file_sample(path, i) for i, path in enumerate(paths)]
        observed["before"] = before
        maps = [sample["map"] for sample in before]
        expected = {str(path): sample["sha256"] for path, sample in zip(paths, before, strict=True)}
        observed["baseline"] = validate(maps, expected)
        moments = observed["barrier"] = {"baseline_accepted": time.monotonic_ns()}
        need(observed["baseline"] == expected, "incomplete baseline")

        entered, mutated = threading.Event(), threading.Event()

        def recheck():
            moments["worker_ready"] = time.monotonic_ns()
            entered.set()
            if not mutated.wait(5) or "overwrite_end" not in moments:
                observed["revalidation"] = {"outcome": "MISSING", "reason": "overwrite barrier incomplete"}
                return
            moments["second_call"] = time.monotonic_ns()
            try:
                validate(maps, expected)
            except Exception as error:
                observed["revalidation"] = {"outcome": "REFUSED", "type": type(error).__name__, "reason": str(error)}
            else:
                observed["revalidation"] = {"outcome": "ACCEPTED"}
            moments["second_return"] = time.monotonic_ns()

        worker = threading.Thread(target=recheck, daemon=True)
        worker.start()
        try:
            need(entered.wait(5), "revalidation barrier timeout")
            check()
            moments["overwrite_start"] = time.monotonic_ns()
            paths[0].write_bytes(MUTATED)
            observed["after"] = [file_sample(path, i) for i, path in enumerate(paths)]
            moments["overwrite_end"] = time.monotonic_ns()
        finally:
            mutated.set()
            worker.join(6)
            need(not worker.is_alive(), "fixture worker did not terminate")
        check()


def validate_observation(observed, directory):
    fixture = Path(observed["fixture"])
    need(fixture.parent == directory and fixture.name.startswith("private-fixture-")
         and observed["cleanup"] is True, "missing private fixture cleanup")
    before, after = observed["before"], observed["after"]
    need(len(before) == len(after) == len(FILES), "incomplete map witnesses")
    for index, (name, initial, final) in enumerate(zip(FILES, before, after, strict=True)):
        need(initial["map"] == final["map"]
             and initial["map"].endswith(" " + str(fixture / name))
             and re.fullmatch(r"[0-9a-f]+-[0-9a-f]+ r-xp 00000000 [0-9a-f]+:[0-9a-f]+ [1-9][0-9]*",
                              initial["map"].rsplit(" ", 1)[0])
             and initial["sha256"] == sha(original(name))
             and final["sha256"] == sha(MUTATED if index == 0 else original(name)), "fixture witness changed")
    expected = {str(fixture / name): sha(original(name)) for name in FILES}
    need(observed["baseline"] == expected, "incomplete baseline witness")
    barrier = observed["barrier"]
    order = [barrier[key] for key in ("baseline_accepted", "worker_ready", "overwrite_start",
                                      "overwrite_end", "second_call", "second_return")]
    need(all(type(value) is int for value in order) and all(a < b for a, b in zip(order, order[1:])),
         "invalid barrier sequence")
    need(observed["revalidation"] == {"outcome": "REFUSED", "type": "ValueError",
                                     "reason": "unattested mapped library: " + str(fixture / FILES[0])},
         "expected second-call refusal absent")


def read_attempt(directory, kind, grant_dir):
    """Recheck original prospective bytes without running the evidence's source."""
    native_bytes = (directory / "native.json").read_bytes()
    context_bytes = (directory / "attempt.json").read_bytes()
    native, context = json.loads(native_bytes), json.loads(context_bytes)
    native_sha, context_sha = sha(native_bytes), sha(context_bytes)
    need(context["schema"] == CAPTURE and native["schema"] == SCHEMA
         and native["capture_schema"] == CAPTURE and native["status"] == "PASS" and native["error"] is None
         and native["result_kind"] == context["result_kind"] == kind and native["row_id"] == context["row_id"] == ROW
         and native["attempt_nonce"] == context["nonce"] == directory.name
         and re.fullmatch(r"[0-9a-f]{48}", context["nonce"])
         and native["attempt_context_sha256"] == context_sha, "unbound, invalid or wrong-purpose attempt")
    need(source_identity(directory / "source") == context["source_pins"]
         and sha((directory / "source/producer.py").read_bytes()) == context["producer_sha256"],
         "prospective producer or inputs changed")
    raw = context["grant_text"]
    grant = grant_fields(raw)
    start, end = grant_bounds(grant)
    need(context["grant_path"] == str(grant_dir / (ROW + ".grant"))
         and sha(raw.encode()) == context["grant_sha256"]
         and sorted(cpus(grant.get("cpus", grant["regions"]))) == context["granted_cpus"]
         and context["fixture_cpus"] == context["granted_cpus"][:4]
         and len(context["fixture_cpus"]) == 4
         and context["deadline_epoch"] <= context["started_epoch"] + 300
         and start <= context["started_epoch"] <= native["ended_epoch"] < context["deadline_epoch"] < end,
         "invalid prospective grant window or affinity")
    need((grant.get("kind") == "rowflow-dryrun" and grant.get("id") == ROW) if kind == "smoke"
         else grant.get("kind") != "rowflow-dryrun", "wrong recorded grant purpose")
    attempt_path = Path(context["attempt_path"])
    need(attempt_path.is_absolute() and attempt_path.name == context["nonce"], "foreign attempt directory")
    validate_observation(native["observation"], attempt_path)
    return native, native_sha, context_sha


def check_sidecar(row, sidecar):
    native, native_sha, context_sha = read_attempt(sidecar.parent.resolve(), "full", FLAGS / "grants")
    need(row == sidecar_record(native, native_sha, context_sha), "sidecar does not bind original records")
    return native


def sidecar_record(native, native_sha, context_sha):
    record = {"schema": CAPTURE, "native_schema": SCHEMA, "row_id": native["row_id"],
              "nonce": native["attempt_nonce"], "native_sha256": native_sha, "context_sha256": context_sha}
    return {**record, "record_sha256": digest(record)}


def run(root, threads):
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    group = root / "out" / ("smoke" if smoke else "attempts")
    nonce = secrets.token_hex(24)
    directory = group / nonce
    directory.mkdir(parents=True)
    source = directory / "source"
    source.mkdir()
    ctx = {"schema": CAPTURE, "row_id": ROW, "nonce": nonce, "started_epoch": time.time(),
           "result_kind": "smoke" if smoke else "full", "attempt_path": str(directory)}
    attempt = directory / "attempt.json"
    observation = {}
    status, error = "INVALID", None
    try:
        for name in SOURCE_PINS:
            (source / name).write_bytes((root / "source" / name).read_bytes())
        producer = Path(__file__).read_bytes()
        (source / "producer.py").write_bytes(producer)
        ctx.update(source_pins=source_identity(source), producer_sha256=sha(producer))
        acquire(ctx, threads)
        write(attempt, ctx)
        check = lambda: guard(ctx, Path(os.environ["FILLER_STOPFILE"]))
        check()
        try:
            exercise(directory, load_validator(source), check, observation)
        finally:
            observation["cleanup"] = "fixture" in observation and not Path(observation["fixture"]).exists()
        validate_observation(observation, directory)
        check()
        status = "PASS"
    except (OSError, RuntimeError, ValueError, KeyError) as failure:
        error = f"{type(failure).__name__}: {failure}"
    if not attempt.exists():
        write(attempt, ctx)
    native = {"schema": SCHEMA, "capture_schema": CAPTURE, "row_id": ROW, "attempt_nonce": nonce,
              "attempt_context_sha256": sha(attempt.read_bytes()), "result_kind": ctx["result_kind"],
              "status": status, "error": error, "ended_epoch": time.time(), "observation": observation}
    native_path = directory / "native.json"
    write(native_path, native)
    if status != "PASS":
        print(json.dumps({"status": status, "error": error, "attempt": str(directory)}), flush=True)
        return 2
    sidecar = directory / "belief_measurements.jsonl"
    if smoke:
        read_attempt(directory, "smoke", Path(os.environ["FILLER_DRYRUN_DIR"]) / "grants")
    else:
        row = sidecar_record(native, sha(native_path.read_bytes()), native["attempt_context_sha256"])
        write(sidecar, row)
        check_sidecar(row, sidecar)
    result = {"status": "PASS", "rc": 0, "case_count": 1, "result_kind": ctx["result_kind"],
              "row_id": ROW, "nonce": nonce, "native_sha256": sha(native_path.read_bytes()),
              "sidecar": str(sidecar) if not smoke else None}
    result_path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if smoke else root / "out/RESULT.json"
    write(result_path, result)
    print(json.dumps(result), flush=True)
    return 0


def complete(root):
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    if smoke and not os.environ.get("FILLER_DRYRUN_RESULT_PATH"):
        return 1  # publisher preflight has no active smoke attempt
    result = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if smoke else root / "out/RESULT.json"
    if not result.is_file():
        return 1
    receipt = json.loads(result.read_text())
    nonce = receipt["nonce"]
    need(re.fullmatch(r"[0-9a-f]{48}", nonce), "invalid attempt nonce")
    directory = root / "out" / ("smoke" if smoke else "attempts") / nonce
    sidecar = directory / "belief_measurements.jsonl"
    if smoke:
        need(not sidecar.exists(), "smoke cannot carry a belief sidecar")
        _, native_sha, _ = read_attempt(directory, "smoke", Path(os.environ["FILLER_DRYRUN_DIR"]) / "grants")
    else:
        row = json.loads(sidecar.read_text())
        check_sidecar(row, sidecar)
        native_sha = row["native_sha256"]
    expected = {"status": "PASS", "rc": 0, "case_count": 1, "result_kind": "smoke" if smoke else "full",
                "row_id": ROW, "nonce": nonce, "native_sha256": native_sha,
                "sidecar": None if smoke else str(sidecar)}
    return 0 if receipt == expected else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "verify", "complete"))
    parser.add_argument("--threads", type=int, choices=(4,), default=4)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.action == "verify":
        source_identity(root / "source")
        return 0
    if args.action == "complete":
        return complete(root)

    def stopped(_number, _frame):
        raise InterruptedError("scheduler signal")

    signal.signal(signal.SIGTERM, stopped)
    signal.signal(signal.SIGINT, stopped)
    sys.addaudithook(no_external_exec)
    return run(root, args.threads)


if __name__ == "__main__":
    raise SystemExit(main())
