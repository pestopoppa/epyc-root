"""Run the FM-4 coordinator entrypoint against the retained Codex dispatch census."""
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
ROW = "vb-fm4-coordinator-context-20261118"
SCHEMA = "fm4.codex_dispatch.coordinator_context_row.v1"
PIN_SCHEMA = "fm4.codex_dispatch.coordinator_context_inputs.v1"
ENTRY = "scripts/vidya/coordinator_fm4_context.py"
PAIRS = ["scratch_cleanup", "exp01_acceptance"]
CAP_S = 300
THREADS = 4


class Refusal(Exception):
    pass


def sealed_bytes(path, expected):
    if not path.resolve(strict=True).is_relative_to(SOURCE) or not stat.S_ISREG(path.lstat().st_mode):
        raise Refusal("input_not_regular")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected:
        raise Refusal("input_digest_drift")
    return body


def publish(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="w") as stream:
        staging = Path(stream.name)
        try:
            json.dump(content, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(staging, path)
        finally:
            staging.unlink()


def stopped(signum, _frame):
    raise Refusal("deadline" if signum == signal.SIGALRM else "stop_requested")


def qualifies(report, expected, count):
    cpus = report.get("cpus")
    return (
        all(report.get(key) == value for key, value in expected.items())
        and report.get("status") == "passed"
        and type(report.get("selected_count")) is int and report["selected_count"] == count
        and all(type(report.get(key)) is int and report[key] == 0 for key in (
            "refusal_count", "reliance_count", "task_gate_claims",
        ))
        and "task_outcome" in report and report["task_outcome"] is None
        and isinstance(cpus, list) and len(cpus) == THREADS
        and all(type(cpu) is int and cpu >= 0 for cpu in cpus) and len(set(cpus)) == THREADS
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "complete"))
    parser.add_argument("--pins-sha256", required=True)
    args = parser.parse_args()
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    mode = "publisher_smoke" if smoke else "official"
    dry_path = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if smoke and not dry_path:
        return 1
    output = Path(dry_path) if smoke else ROOT / "official/RESULT.json"
    pairs = PAIRS[:1] if smoke else PAIRS
    expected = {"schema": SCHEMA, "id": ROW, "mode": mode, "source_pins_sha256": args.pins_sha256}
    if args.action == "complete":
        try:
            report = json.loads(output.read_bytes())
            return int(not isinstance(report, dict) or not qualifies(report, expected, len(pairs)))
        except (OSError, ValueError):
            return 1

    report = dict(expected, status="unknown", selected_count=0, refusal_count=1,
                  reliance_count=None, task_gate_claims=None, task_outcome=None)
    try:
        if os.environ.get("FILLER_ID") != ROW or not os.environ.get("FILLER_STOPFILE"):
            raise Refusal("missing_grant")
        stop = Path(os.environ["FILLER_STOPFILE"])
        cutoff = min(time.time() + CAP_S, int(os.environ["FILLER_DEADLINE"]))

        def remaining():
            seconds = cutoff - time.time()
            if stop.exists():
                raise Refusal("stop_requested")
            if seconds <= 0:
                raise Refusal("deadline")
            return seconds

        signal.signal(signal.SIGTERM, stopped)
        signal.signal(signal.SIGALRM, stopped)
        signal.setitimer(signal.ITIMER_REAL, remaining())
        cpus = sorted(os.sched_getaffinity(0))[:THREADS]
        if len(cpus) != THREADS:
            raise Refusal("insufficient_cpu_affinity")
        os.sched_setaffinity(0, cpus)
        report["cpus"] = sorted(os.sched_getaffinity(0))

        plan = json.loads(sealed_bytes(SOURCE / "source-pins.json", args.pins_sha256))
        if plan["schema"] != PIN_SCHEMA or plan["pair_ids"] != PAIRS:
            raise Refusal("source_pin_schema_or_membership_drift")
        def verify_source():
            for name, digest in plan["files"].items():
                remaining()
                sealed_bytes(SOURCE / name, digest)

        verify_source()
        role = (SOURCE / "agents/coordinator-agent.md").read_text()
        if f"python3 -B /mnt/raid0/llm/views/epyc-root-main/{ENTRY}" not in role:
            raise Refusal("coordinator_role_entry_mismatch")

        sys.path.insert(0, str(SOURCE / "scripts/experiments/fm4"))
        import native_canary

        run_dir = Path(tempfile.mkdtemp(prefix=f"{mode}-", dir=ROOT))
        result = native_canary.run_codex_dispatch(
            SOURCE / plan["descriptors"][mode], run_dir / "planner", coordinator_review=True,
        )
        if (
            [item["receipt"]["pair_id"] for item in result["selected"]] != pairs
            or result["consumer"] != "coordination.fm4"
            or result["entrypoint"] != ENTRY
            or result["entrypoint_sha256"] != plan["files"][ENTRY]
            or result["excluded_consumer"] != "autokernel.planner"
            or result["census"]["sha256"] != plan["files"][plan["census"]]
            or result["task_outcome"] is not None
        ):
            raise Refusal("unexpected_coordinator_context")
        verify_source()
        report.update(status="passed", source_base_commit=plan["base_commit"], selected_count=len(pairs),
                      refusal_count=0, reliance_count=result["reliance_count"],
                      task_gate_claims=result["task_gate_claim_count"], canary=result)
        if not qualifies(report, expected, len(pairs)):
            raise Refusal("coordinator_acceptance_metric_disagrees")
        remaining()
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish(output, report)
    except (OSError, RuntimeError, ValueError, KeyError, Refusal) as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        # Refuse with a bounded reason. Lower-level errors can name private inputs.
        reason = str(exc) if isinstance(exc, Refusal) else "replay_or_coordinator_refused"
        report.update(status="unknown", refusal_count=1, refusal=reason)
        publish(output.with_suffix(".partial.json"), report)
        print(f"FM-4 coordinator canary refused: {reason}")
        return 1
    print(f"FM-4 coordinator context selected {report['selected_count']} terminal-dispatch observation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
