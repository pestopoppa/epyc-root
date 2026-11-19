"""Check filed native FM-4 dispatches through the isolated Vidya reader."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
ROW = "vb-fm4-codex-projection-20261118"
SCHEMA = "fm4.codex_dispatch.projection_row.v1"
CAP_S = 300


class Refusal(Exception):
    pass


def sealed_bytes(path, expected):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise Refusal("input_not_regular")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected:
        raise Refusal("input_digest_drift")
    return body


def publish(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        staging = Path(stream.name)
        try:
            stream.write((json.dumps(content, indent=2, sort_keys=True) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
            os.link(staging, path)
        finally:
            staging.unlink()


def check_time(stop, cutoff):
    if stop.exists():
        raise Refusal("stop_requested")
    if time.time() >= cutoff:
        raise Refusal("deadline")


def expired(_signal, _frame):
    raise Refusal("deadline")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "complete"))
    parser.add_argument("--pins-sha256", required=True)
    parser.add_argument("--threads", type=int, choices=(4,), required=True)
    args = parser.parse_args()
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    mode = "publisher_smoke" if smoke else "official"
    dry_result = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if smoke and not dry_result:
        return 1
    output = Path(dry_result) if smoke else ROOT / "official" / "RESULT.json"
    expected_count = 1 if smoke else 2
    if args.action == "complete":
        if not output.is_file():
            return 1
        report = json.loads(output.read_bytes())
        return int(not (
            report.get("schema") == SCHEMA and report.get("id") == ROW and report.get("mode") == mode
            and report.get("source_pins_sha256") == args.pins_sha256
            and report.get("selected_dispatch_count") == expected_count
            and report.get("refusal_count") == report.get("task_gate_claim_count") == 0
            and report.get("task_outcome", "missing") is None
        ))

    if os.environ.get("FILLER_ID") != ROW or not os.environ.get("FILLER_STOPFILE"):
        print("FM-4 projection refused: missing row execution environment")
        return 1
    stop = Path(os.environ["FILLER_STOPFILE"])
    cutoff = min(time.time() + CAP_S, int(os.environ["FILLER_DEADLINE"]))
    report = {"schema": SCHEMA, "id": ROW, "mode": mode, "source_pins_sha256": args.pins_sha256,
              "selected_dispatch_count": 0, "task_outcome": None, "task_gate_claim_count": None}
    try:
        check_time(stop, cutoff)
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, cutoff - time.time())
        cpus = sorted(os.sched_getaffinity(0))[:args.threads]
        if len(cpus) != args.threads:
            raise Refusal("insufficient_cpu_affinity")
        os.sched_setaffinity(0, cpus)
        report["cpus"] = sorted(os.sched_getaffinity(0))
        plan = json.loads(sealed_bytes(ROOT / "source-pins.json", args.pins_sha256))
        if (plan.get("schema") != "fm4.codex_dispatch.projection_inputs.v1"
                or plan.get("pair_ids") != ["scratch_cleanup", "exp01_acceptance"]):
            raise Refusal("source_pin_schema_or_membership_drift")
        report["source_base_commit"] = plan["base_commit"]
        for name, digest in plan["files"].items():
            check_time(stop, cutoff)
            sealed_bytes(SOURCE / name, digest)

        sys.path.insert(0, str(SOURCE / "scripts" / "experiments" / "fm4"))
        import native_canary

        pairs = plan["pair_ids"][:expected_count]
        run_dir = Path(tempfile.mkdtemp(prefix=f"{mode}-", dir=ROOT))
        descriptor = run_dir / "dispatch-replay.json"
        publish(descriptor, {
            "schema": native_canary.adapter.DISPATCH_BUNDLE_SCHEMA,
            "result": str(SOURCE / plan["census"]),
            "result_sha256": plan["files"][plan["census"]],
            "snapshot_dir": str(ROOT.parent / "private"),
            "pair_ids": pairs,
        })
        descriptor.chmod(0o400)
        check_time(stop, cutoff)
        result = native_canary.run_codex_dispatch(descriptor, run_dir / "planner")
        if ([item["receipt"]["pair_id"] for item in result["selected"]] != pairs
                or result["task_outcome"] is not None or result["task_gate_claim_count"] != 0):
            raise Refusal("native_planner_result_disagrees")
        report.update(canary=result, selected_dispatch_count=len(result["selected"]),
                      task_gate_claim_count=result["task_gate_claim_count"], refusal_count=0)
        check_time(stop, cutoff)
        publish(output, report)
    except (OSError, RuntimeError, ValueError, Refusal) as exc:
        # A failure from a lower layer may contain private paths or transcript content.
        reason = str(exc) if isinstance(exc, Refusal) else "projection_or_planning_refused"
        report.update(disposition="unknown", refusal=reason, refusal_count=1)
        publish(output.with_suffix(".partial.json"), report)
        print(f"FM-4 projection refused: {reason}")
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(f"FM-4 projection selected {report['selected_dispatch_count']} native dispatch receipt(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
