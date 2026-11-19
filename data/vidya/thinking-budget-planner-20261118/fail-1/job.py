"""Allocator-only replay of retained thinking-budget chat diagnostics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
ROW = "vb-tb-semantics-native-planner-20261118"
SOURCE = "thinking_budget_semantics_context"
RULE = {"native_rows": 6, "native_report_count": 2, "visible_count": 6, "history_count": 6,
        "refusal_control_count": 4, "exclusion_count": 3, "refusal_count": 0, "producer_protocol_passed": 1}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    require(path.is_file() and path.resolve() == path, f"invalid pinned file {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_inputs(expected):
    manifest = HERE / "pins.json"
    require(digest(manifest) == expected, "input manifest changed")
    pins = json.loads(manifest.read_bytes())
    for name, identity in {**pins["code"], **pins["native_results"]}.items():
        require(digest(HERE / name) == identity, f"input changed: {name}")
    return pins


def four_cpus():
    granted = set()
    for field in os.environ["FILLER_CPUS"].split(","):
        require(re.fullmatch(r"\d{1,4}(?:-\d{1,4})?", field), "invalid FILLER_CPUS")
        first, _, last = field.partition("-")
        granted.update(range(int(first), int(last or first) + 1))
    physical = {}
    for cpu in sorted(granted & os.sched_getaffinity(0)):
        physical.setdefault(cpu % 96, cpu)
    selected = sorted(physical.values())[:4]
    require(len(selected) == 4, "expected four granted physical cores")
    os.sched_setaffinity(0, selected)
    require(os.sched_getaffinity(0) == set(selected), "affinity changed")
    return selected


def write(path, result):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        pending = Path(stream.name)
        try:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(pending, path)
        finally:
            pending.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "complete"))
    parser.add_argument("pins_sha256")
    args = parser.parse_args()
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    mode = "publisher-smoke" if smoke else "official"
    smoke_path = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if smoke and not smoke_path:
        return 1
    output = Path(smoke_path) if smoke else HERE / "official/RESULT.json"
    identity = {"id": ROW, "mode": mode, "pins_sha256": args.pins_sha256}

    if args.mode == "complete":
        try:
            result = json.loads(output.read_bytes())
            return int(result["status"] != "passed" or any(
                result.get(key) != value for key, value in {**identity, **RULE}.items()))
        except (OSError, ValueError, KeyError, TypeError):
            return 1

    workspace = Path(tempfile.mkdtemp(prefix=mode + "-", dir=HERE))
    report = dict(identity, status="UNKNOWN", native_rows=0, refusal_count=1)
    try:
        require(os.environ.get("FILLER_ID") == ROW, "allocator row identity required")
        stop = Path(os.environ["FILLER_STOPFILE"])
        deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + 200)

        def remaining():
            seconds = deadline - time.time()
            require(seconds > 0 and not stop.exists(), "allocator STOP or deadline")
            return seconds

        def interrupted(_signal, _frame):
            raise ValueError("allocator interrupted replay")

        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
            signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, remaining())
        report["cpus"] = four_cpus()
        pins = check_inputs(args.pins_sha256)
        producer = HERE / "reader/scripts/experiments/thinking-budget-semantics"
        control_log = workspace / "producer-protocol.log"
        with control_log.open("w") as log:
            subprocess.run(
                [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", str(producer),
                 "-p", "test_protocol.py", "-v"],
                cwd=workspace, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=remaining(),
            )
        sys.path.insert(0, str(HERE / "reader/scripts/vidya/canary"))
        canary = __import__(SOURCE)
        observations = canary.replay(tuple(map(Path, pins["native_results"])), HERE / "research", workspace)
        observations.update(producer_protocol_passed=1, producer_protocol_log_sha256=digest(control_log))
        check_inputs(args.pins_sha256)
        remaining()
        require(all(observations.get(k) == v for k, v in RULE.items()), "canary decision rule refused")
        report.update(observations, status="passed",
                      source_revision=pins["source_revision"],
                      native_result_sha256=pins["native_results"], artifact_directory=workspace.name)
        write(output, report)
        return 0
    except Exception as exc:
        report.update(status="UNKNOWN", refusal=f"{type(exc).__name__}: {exc}")
        (workspace / "error.log").write_text(traceback.format_exc())
        write(workspace / "RESULT.partial.json", report)
        print(report["refusal"], file=sys.stderr)
        return 75
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    sys.exit(main())
