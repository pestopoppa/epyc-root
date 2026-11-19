"""Bounded, isolated replay of the original Astropy scorer case."""
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
ROW = "vb-p5-astropy-planner-acceptance-20261118"
SCHEMA = "epyc.p5.astropy.task_planning_acceptance.v1"


def write_terminal(path, payload):
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as temp:
        try:
            json.dump(payload, temp, indent=2, sort_keys=True)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
            os.link(temp.name, path)
        finally:
            Path(temp.name).unlink()


def passed(receipt, mode, seal):
    return (receipt.get("schema") == SCHEMA and receipt.get("id") == ROW
            and receipt.get("mode") == mode and receipt.get("status") == "PASS"
            and receipt.get("source_manifest_sha256") == seal
            and len(receipt.get("actual_cpus", [])) == 4
            and receipt.get("rows") == 30 and receipt.get("frames") == 90 and receipt.get("refusals") == 0
            and receipt.get("tamper_refusals") == 1 and receipt.get("tamper_frames") == 0
            and receipt["cases"]["exact-task"]["eligible"] == 30
            and receipt["cases"]["exact-task"]["shown"] > 0
            and all(receipt["cases"][name]["eligible"] == receipt["cases"][name]["shown"] == 0
                    for name in ("wrong-task", "wrong-consumer", "model-target")))


def interrupted(_signum, _frame):
    raise ValueError("STOP or cutoff reached")


def main():
    action, seal = sys.argv[1:]
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    mode = "publisher_smoke" if smoke else "official"
    if smoke and not os.environ.get("FILLER_DRYRUN_RESULT_PATH"):
        return 1
    path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if smoke else ROOT / "official/RESULT.json"
    if action == "complete":
        try:
            return int(not passed(json.loads(path.read_bytes()), mode, seal))
        except (OSError, ValueError, KeyError, TypeError):
            return 1
    if action != "run" or os.environ.get("FILLER_ID") != ROW or os.environ.get("FILLER_NEEDGPU") != "0":
        return 1
    if smoke and Path(os.environ["FILLER_DRYRUN_DIR"]).resolve() not in path.resolve().parents:
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    stop = Path(os.environ["FILLER_STOPFILE"])
    cutoff = min(time.time() + 300, int(os.environ["FILLER_DEADLINE"]))

    def checkpoint():
        if stop.exists() or time.time() >= cutoff:
            raise ValueError("STOP or cutoff reached")

    attempt = Path(tempfile.mkdtemp(prefix=f"{mode}-", dir=ROOT))
    receipt = {"schema": SCHEMA, "id": ROW, "mode": mode, "status": "UNKNOWN",
               "source_manifest_sha256": seal, "attempt": str(attempt)}
    try:
        checkpoint()
        for signum in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, interrupted)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, cutoff - time.time()))
        cpus = sorted(os.sched_getaffinity(0))[:4]
        if len(cpus) != 4:
            raise ValueError("fewer than four effective CPUs")
        os.sched_setaffinity(0, cpus)
        receipt["actual_cpus"] = sorted(os.sched_getaffinity(0))
        manifest = (ROOT / "SOURCE.sha256").read_bytes()
        if hashlib.sha256(manifest).hexdigest() != seal:
            raise ValueError("source manifest pin changed")
        for line in manifest.decode().splitlines():
            checkpoint()
            digest, name = line.split("  ", 1)
            input_path = ROOT / name
            if (input_path.resolve(strict=True) != input_path or not input_path.is_relative_to(ROOT / "source")
                    or hashlib.sha256(input_path.read_bytes()).hexdigest() != digest):
                raise ValueError(f"sealed input changed: {name}")
        source = ROOT / "source"
        sys.path.insert(0, str(source / "scripts/vidya"))
        from canary.p5_astropy_task_context import run
        receipt.update(run(source / "data/vidya/p5-astropy-native-20261118", attempt / "canary",
                           checkpoint=checkpoint))
        checkpoint()
        if not passed(receipt, mode, seal):
            raise ValueError("planning control returned unexpected coverage")
        write_terminal(path, receipt)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        receipt.update(status="UNKNOWN", error=str(exc))
        write_terminal(attempt / "partial.json", receipt)
        print(f"Astropy planning control refused: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(f"Astropy planning acceptance PASS: {receipt['rows']} statuses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
