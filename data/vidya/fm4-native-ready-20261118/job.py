"""Replay a fixed census of native Codex dispatch receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import tempfile
import time


ROOT = Path(__file__).resolve().parent
ROW = "vb-fm4-codex-native-20261118"
SCHEMA = "fm4.codex_dispatch.census.v1"
OFFICIAL = ROOT / "official" / "RESULT.json"
PAIR_IDS = ("scratch_cleanup", "exp01_acceptance")
CAP_S = 300


class Refusal(Exception):
    pass


def sealed_bytes(path, expected):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise Refusal("input_not_regular")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise Refusal("input_digest_drift")
    return raw


def publish_json(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        scratch = Path(stream.name)
        try:
            stream.write((json.dumps(content, indent=2, sort_keys=True) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
            os.link(scratch, path)
        finally:
            scratch.unlink()


def capture(collector, pair):
    files = {}
    for role, pin in pair["inputs"].items():
        path = ROOT / pin["file"]
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != pin["bytes"]:
            raise Refusal("rollout_type_or_size_drift")
        files[role] = path
    receipt = collector(files["parent"], files["child"])
    for role, pin in pair["inputs"].items():
        observed = receipt["inputs"][role]
        if observed["sha256"] != pin["sha256"] or observed["path"] != str(files[role]):
            raise Refusal("rollout_digest_or_path_drift")
    if receipt["disposition"] != "terminal_child":
        raise Refusal(receipt["disposition"])
    if (receipt["identity"] != pair["identity"]
            or receipt["binding_kind"] != pair["binding_kind"]
            or receipt["lineage"]["child_agent_path"] != pair["child_agent_path"]
            or receipt["task_outcome"] is not None):
        raise Refusal("dispatch_identity_drift")
    for input_receipt in receipt["inputs"].values():
        del input_receipt["path"]
    return {"pair_id": pair["pair_id"], **receipt}


def check_stop(stop, cutoff):
    if stop.exists():
        raise Refusal("stop_requested")
    if time.time() >= cutoff:
        raise Refusal("deadline")


def deadline_expired(_signal, _frame):
    raise Refusal("deadline")


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("run", "complete"))
    parser.add_argument("--pins-sha256", required=True)
    parser.add_argument("--threads", required=True, type=int, choices=(4,))
    args = parser.parse_args()
    dryrun = os.environ.get("FILLER_DRYRUN") == "1"
    dry_result = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if dryrun and dry_result is None:
        return 1
    output = Path(dry_result) if dryrun else OFFICIAL
    pair_ids = PAIR_IDS[:1] if dryrun else PAIR_IDS
    if args.action == "complete":
        if not output.is_file():
            return 1
        result = json.loads(output.read_bytes())
        return int(not (
            result.get("id") == ROW and result.get("schema") == SCHEMA
            and result.get("input_pins_sha256") == args.pins_sha256
            and result.get("mode") == ("publisher_smoke" if dryrun else "official")
            and result.get("pair_ids") == list(pair_ids)
            and result.get("terminal_receipt_count") == len(pair_ids)
            and result.get("refusal_count") == 0
        ))

    if os.environ.get("FILLER_ID") != ROW or "FILLER_STOPFILE" not in os.environ:
        print("FM-4 census refused: missing row execution environment")
        return 1
    stop = Path(os.environ["FILLER_STOPFILE"])
    cutoff = min(time.time() + CAP_S, int(os.environ["FILLER_DEADLINE"]))
    result = {
        "schema": SCHEMA, "id": ROW, "mode": "publisher_smoke" if dryrun else "official",
        "input_pins_sha256": args.pins_sha256, "pair_ids": list(pair_ids),
        "receipts": [], "task_outcome": None,
    }
    refused_pair = None
    try:
        check_stop(stop, cutoff)
        signal.signal(signal.SIGALRM, deadline_expired)
        signal.setitimer(signal.ITIMER_REAL, cutoff - time.time())
        cpus = sorted(os.sched_getaffinity(0))[:args.threads]
        if len(cpus) != args.threads:
            raise Refusal("insufficient_cpu_affinity")
        os.sched_setaffinity(0, cpus)
        result["cpus"] = sorted(os.sched_getaffinity(0))
        plan = json.loads(sealed_bytes(ROOT / "input-pins.json", args.pins_sha256))
        if tuple(pair["pair_id"] for pair in plan["pairs"]) != PAIR_IDS:
            raise Refusal("census_membership_drift")
        result["collector_sha256"] = plan["collector_sha256"]
        code = sealed_bytes(ROOT / "codex_dispatch.py", plan["collector_sha256"])
        producer = {}
        exec(compile(code, "codex_dispatch.py", "exec"), producer)
        for pair in plan["pairs"][:len(pair_ids)]:
            refused_pair = pair["pair_id"]
            check_stop(stop, cutoff)
            receipt = capture(producer["collect"], pair)
            check_stop(stop, cutoff)
            result["receipts"].append(receipt)
        result.update(terminal_receipt_count=len(result["receipts"]), refusal_count=0)
        check_stop(stop, cutoff)
        publish_json(output, result)
    except (OSError, ValueError, Refusal) as exc:
        # Collector errors can contain private rollout data. Persist only a safe disposition.
        reason = str(exc) if isinstance(exc, Refusal) else "input_or_output_refused"
        result.update(terminal_receipt_count=len(result["receipts"]), refusal_count=1,
                      disposition="unknown", refusal=reason, refused_pair=refused_pair)
        publish_json(output.with_suffix(".partial.json"), result)
        print(f"FM-4 census refused: {reason}")
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(f"FM-4 census retained {len(result['receipts'])} native terminal dispatch receipt(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
