#!/usr/bin/python3
"""Run two model-free Q38 planner controls on four granted CPUs."""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROW = "vb-mi210-q38-planner-control-20261118"
CAP = 300
CASES = ("baseline", "candidate")
RULE = {"control_count": 2, "baseline_visible": 0, "excluded_count": 4,
        "refusal_control_count": 3, "native_q38_acceptance_count": 0, "refusal_count": 0}


def digest(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"invalid pinned file {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(pin):
    manifest = HERE / "source-pins.json"
    if digest(manifest) != pin:
        raise ValueError("source manifest drift")
    pins = json.loads(manifest.read_bytes())
    for name, identity in pins["files"].items():
        if digest(HERE / name) != identity:
            raise ValueError(f"source drift: {name}")
    for ref in ("HEAD", "refs/remotes/origin/main"):
        observed = subprocess.check_output(
            ["git", "-C", str(HERE / "reader"), "rev-parse", "--verify", ref], text=True).strip()
        if observed != pins["reader_commit"]:
            raise ValueError(f"reader ref drift: {ref}")
    return pins


def restrict_cpus():
    cpus = set()
    for block in os.environ["FILLER_CPUS"].split(","):
        if not re.fullmatch(r"[0-9]{1,4}(?:-[0-9]{1,4})?", block):
            raise ValueError("invalid grant CPU list")
        start, _, end = block.partition("-")
        if int(end or start) < int(start):
            raise ValueError("inverted grant CPU list")
        cpus.update(range(int(start), int(end or start) + 1))
    selected = sorted(cpus & os.sched_getaffinity(0))[:4]
    if len(selected) != 4:
        raise ValueError("fewer than four actual granted CPUs")
    os.sched_setaffinity(0, selected)
    if os.sched_getaffinity(0) != set(selected):
        raise ValueError("grant affinity drift")
    return selected


def publish(path, report):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temporary, path)
        finally:
            temporary.unlink()


def verify_controls(run_dir):
    if run_dir.parent != HERE or run_dir.resolve(strict=True) != run_dir or not run_dir.is_dir():
        raise ValueError("invalid result workspace")
    reports = {}
    for case in CASES:
        receipt = run_dir / case / "receipt.json"
        result = json.loads(receipt.read_bytes())
        if (result["status"], result["authority"], result["baseline"], result["rows"], result["frames"],
                result["refused"], result["actor_backend_called"]) != (
                    "passed", "software-control-only", case == "baseline", 20, 60, 0, False):
            raise ValueError(f"failed structural control: {case}")
        if result["reader_checkout"]["root"] != str(HERE / "reader"):
            raise ValueError("unexpected control reader")
        reports[case] = (result, digest(receipt))
    base, candidate = (reports[case][0] for case in CASES)
    if (base["visible_count"] != 0 or candidate["visible_count"] <= 0
            or base["model_scope"] != candidate["model_scope"]
            or set(candidate["excluded"]) != {"cpu", "different-weight", "missing-digest", "invalid-digest"}
            or set(candidate["refusal_controls"]) != {"partial", "smoke", "tampered"}
            or base["reliance"]["accepted"]):
        raise ValueError("scope or refusal control failed")
    return dict(RULE, candidate_visible=candidate["visible_count"],
                control_receipts_sha256={case: reports[case][1] for case in CASES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "complete"))
    parser.add_argument("--pins-sha256", required=True)
    args = parser.parse_args()
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    mode = "publisher-smoke" if smoke else "official"
    path = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if smoke and not path:
        return 1
    output = Path(path) if smoke else HERE / "official/RESULT.json"
    expected = {"id": ROW, "authority": "software-control-only", "mode": mode,
                "source_pins_sha256": args.pins_sha256}
    errors = (OSError, ValueError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError)
    if args.action == "complete":
        try:
            report = json.loads(output.read_bytes())
            run_dir = Path(report["run_dir"])
            if not run_dir.name.startswith(mode + "-"):
                return 1
            return int(report["status"] != "passed"
                       or any(report.get(k) != v for k, v in expected.items())
                       or any(report.get(k) != v for k, v in verify_controls(run_dir).items()))
        except errors:
            return 1

    report = dict(expected, status="unknown", control_count=0, refusal_count=1)
    run_dir = None
    try:
        if os.environ["FILLER_ID"] != ROW:
            raise ValueError("allocator row identity mismatch")
        stop = Path(os.environ["FILLER_STOPFILE"])
        grant_deadline = os.environ["FILLER_DEADLINE"]
        if not re.fullmatch(r"[0-9]{1,12}", grant_deadline):
            raise ValueError("invalid allocation deadline")
        cap = time.monotonic() + CAP

        def remaining():
            if stop.exists():
                raise ValueError("STOP requested")
            seconds = min(int(grant_deadline) - time.time(), cap - time.monotonic())
            if seconds <= 0:
                raise ValueError("deadline reached")
            return seconds

        def interrupted(_signal, _frame):
            raise ValueError("interrupted or deadline reached")

        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
            signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, remaining())
        report["cpus"] = restrict_cpus()
        pins = verify_sources(args.pins_sha256)
        report["source_commit"] = pins["reader_commit"]
        report["research_baseline_commit"] = pins["research_baseline_commit"]
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        env.update(PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4")
        run_dir = Path(tempfile.mkdtemp(prefix=mode + "-", dir=HERE))
        report["run_dir"] = str(run_dir)
        for case in CASES:
            cmd = [sys.executable, "-I", "-B", str(HERE / "reader/scripts/vidya/canary/mi210_q38_context.py"),
                   "--reader", str(HERE / "reader"), "--research", str(HERE / f"research-{case if case == 'candidate' else 'base'}"),
                   "--scratch", str(run_dir / case), "--synthetic", case]
            with (run_dir / f"{case}.log").open("w") as log:
                subprocess.run(cmd, env=env, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT,
                               timeout=remaining(), check=True)
        report.update(verify_controls(run_dir))
        verify_sources(args.pins_sha256)
        remaining()
        report["status"] = "passed"
        publish(output, report)
        signal.setitimer(signal.ITIMER_REAL, 0)
        return 0
    except errors as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        report.update(status="unknown", control_count=0, refusal_count=1,
                      refusal=f"{type(exc).__name__}: {exc}")
        partial_dir = run_dir if run_dir is not None else Path(tempfile.mkdtemp(prefix=mode + "-", dir=HERE))
        publish(partial_dir / "RESULT.partial.json", report)
        print(report["refusal"], file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
