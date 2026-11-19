#!/usr/bin/python3
"""Run model-free Q38 runner-to-planner controls on four granted CPUs."""
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
ROW = "vb-q38-preflight-planner-20261118"
CAP = 300
RULE = {"control_count": 2, "baseline_visible": 0,
        "native_q38_acceptance_count": 0, "refusal_count": 0}


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
    for role in ("reader", "research"):
        observed = subprocess.check_output(
            ["git", "-C", str(HERE / role), "rev-parse", "--verify", "HEAD"], text=True).strip()
        if observed != pins[f"{role}_commit"]:
            raise ValueError(f"{role} source commit drift")
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
    summary = run_dir / "probe.json"
    report = json.loads(summary.read_bytes())
    bound = report["controls"]["preflight"]
    baseline = report["controls"]["path-only"]
    if (bound["visible"] <= 0 or bound["visible"] + bound["bounded"] != 20
            or baseline["visible"] != 0 or bound["actor_backend_called"] or baseline["actor_backend_called"]
            or (report["rows"], report["frames"], report["native_q38_acceptance_count"]) != (20, 60, 0)
            or bound["target"]["model_sha256"] != report["model_sha256"]
            or "model_sha256" in baseline["target"]):
        raise ValueError("runner scope or planning controls failed")
    receipts = {}
    for case, outcome in report["controls"].items():
        receipt = run_dir / f"actor-{case}.json"
        actor = json.loads(receipt.read_bytes())
        if (actor["receipt_id"] != outcome["actor_receipt_id"]
                or set(actor["reliance"]["accepted"]) != set(outcome["claims"])):
            raise ValueError(f"actor receipt mismatch: {case}")
        receipts[case] = digest(receipt)
    return dict(RULE, candidate_visible=bound["visible"], probe_sha256=digest(summary),
                actor_receipts_sha256=receipts, verified_model_sha256=report["model_sha256"])



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
        report["research_commit"] = pins["research_commit"]
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        env.update(PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4")
        run_dir = Path(tempfile.mkdtemp(prefix=mode + "-", dir=HERE))
        report["run_dir"] = str(run_dir)
        cmd = [sys.executable, "-I", "-B", str(HERE / "probe.py"), "exercise",
               "--reader", str(HERE / "reader"), "--research", str(HERE / "research"),
               "--fixture", str(HERE / "fixture"), "--output", str(run_dir)]
        with (run_dir / "probe.log").open("w") as log:
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
