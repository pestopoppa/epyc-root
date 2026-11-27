"""Dispatch hash-approved legacy jobs and saved CPU continuations to the owned CPU replacement."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import fcntl
import importlib.util
import json
from pathlib import Path
import signal
import sys
import threading
import time

import serve

legacy = serve.legacy
HERE = serve.HERE
V4 = legacy.V4
CONTINUE_TEXT = (
    "Resume the same task from your existing private workspace and session. "
    "The controller interrupted the previous turn for a CPU serving-placement repair. "
    "Continue the original pinned brief and its existing scopes and checks. "
    "No additional task guidance is available.\n"
)
LEGACY_CPU = ("cpu-TU-GR-1-off-recommended", "cpu-MM-5-off-recommended")


def quality_module():
    path = V4 / "launch.py"
    known = legacy.read(V4 / "QUALITY-MANIFEST.json")["sha256"]["quality-v4/launch.py"]
    legacy.same_file(path, known)
    sys.path[:0] = [str(V4), str(legacy.ENGINE)]
    module = importlib.util.spec_from_file_location("frozen_quality_v4", path)
    quality = importlib.util.module_from_spec(module)
    module.loader.exec_module(quality)
    grid, _ = quality.check_inputs(legacy.V4_SHA)
    return quality, [row for row in grid["rows"] if row["backend"] == "cpu"]


def prior_for(row):
    return serve.PREVIOUS / "units" / row["id"]


def prior_snapshot(row):
    from opencode_derived.__main__ import state_digest
    prior = prior_for(row)
    result = legacy.read(prior / "RESULT.json")
    if (result["manifest_sha256"] != legacy.V4_SHA or result["id"] != row["id"] or not result.get("terminal_at")
            or not result.get("session") or result["status"] != "no_candidate"):
        raise ValueError("previous attempt must be the exported, terminal, unedited CPU original")
    return {"initial_row": row["id"], "mode": "resume", "prior": str(prior),
            "prior_result_sha256": legacy.digest(prior / "RESULT.json"),
            "prior_session_sha256": legacy.digest(prior / "OPEN-CODE-SESSION.json"),
            "prior_state_sha256": state_digest(prior / "sandbox/work", prior / "sandbox/session", prior / "refs"),
            "session_id": result["session"], "previous_generated_observed": result["generation_observed"],
            "previous_model_wall_s": result["model_wall_s"]}


def draft(out):
    legacy.verify(serve.SEAL)
    _, cpu_rows = quality_module()
    if out.exists() or not out.is_relative_to(HERE):
        raise ValueError("draft must use a new private file inside the replacement workspace")
    specs = [prior_snapshot(row) for row in cpu_rows]
    document = {"approved_by": None, "server_ready_sha256": None,
                "legacy_seal_sha256": serve.SEAL, "quality_manifest_sha256": legacy.V4_SHA,
                "legacy_rows": list(LEGACY_CPU), "quality_resume_rows": specs,
                "continuation_text": CONTINUE_TEXT}
    legacy.write(out, document)
    print(legacy.digest(out), flush=True)


def plan(approval, cpu_rows, *, verify_prior=True):
    if (approval["legacy_seal_sha256"] != serve.SEAL or approval["quality_manifest_sha256"] != legacy.V4_SHA
            or approval["continuation_text"] != CONTINUE_TEXT):
        raise ValueError("approval changes pinned comparison or bound continuation")
    known, _ = legacy.sealed_rows()
    selections = approval["legacy_rows"]
    resumes = approval["quality_resume_rows"]
    if (not selections and not resumes) or len(set(selections)) != len(selections) or set(selections) - set(LEGACY_CPU):
        raise ValueError("invalid approved legacy CPU rows")
    selected = {spec["initial_row"]: spec for spec in resumes}
    original = {row["id"]: row for row in cpu_rows}
    if len(selected) != len(resumes) or set(selected) - original.keys():
        raise ValueError("invalid approved saved CPU continuation rows")
    queues = {slot: [] for slot in range(4)}
    for key in selections:
        row = known[key]
        queues[row["slot"]].append(("legacy", row, None))
    for name, spec in selected.items():
        row = original[name]
        if verify_prior and spec != prior_snapshot(row):
            raise ValueError(f"previous workspace, session or result changed: {name}")
        continuation = dict(row, id=row["id"] + "-numa-resume-1")
        queues[row["slot"]].append(("resume", continuation, spec))
    return {slot: queue for slot, queue in queues.items() if queue}


def check_ready(epoch, approval):
    ready_file = epoch / "READY.json"
    legacy.same_file(ready_file, approval["server_ready_sha256"])
    ready = legacy.read(ready_file)
    live_path = epoch / "out-cpu/live.json"
    if Path(ready["live_receipt"]).resolve() != live_path or ready["server_executable_sha256"] != serve.CPU_SHA:
        raise ValueError("CPU replacement receipt lies outside the approved epoch")
    if not ready["cpu_only"] or "--no-mmap" not in ready["argv"] or ready["owned_grant"] != legacy.read(epoch / "GRANT.json"):
        raise ValueError("receipt does not match the owned CPU placement replacement")
    legacy.same_file(epoch / "NUMA-AFTER.json", ready["residency_sha256"])
    serve.grant_live()
    serving = {"port": ready["port"], "serving_receipt": str(live_path),
               "serving_receipt_sha256": ready["live_receipt_sha256"],
               "server_executable_sha256": serve.CPU_SHA, "model_path": ready["model"]}
    from opencode_derived.__main__ import serving_proof
    if serving_proof(dict(serving, slot=0, backend="cpu", context=131072)) != ready["pid"]:
        raise ValueError("live process differs from the approved CPU placement receipt")
    return serving, ready["pid"]


def close_requested(epoch, batch, pid):
    if (epoch / "STOP").exists() or (batch / "STOP").exists() or (epoch / "CLEANUP.json").exists():
        return "owner stop"
    try:
        serve.grant_live()
        state = serve.identity(pid)
        if state["state"] == "Z":
            return "replacement server exited"
        expected = legacy.read(epoch / "READY.json")
        if (Path(f"/proc/{pid}/exe").resolve() != Path(expected["argv"][0])
                or "--no-mmap" not in (Path(f"/proc/{pid}/cmdline").read_text().split("\0"))):
            return "replacement server identity changed"
    except (OSError, RuntimeError, ValueError) as error:
        return repr(error)
    return None


def run_batch(epoch, batch_name, approval_file, approved_sha):
    legacy.same_file(approval_file, approved_sha)
    approval = legacy.read(approval_file)
    if approval["approved_by"] != "main" or (epoch / "STOP").exists():
        raise ValueError("main must approve the exact replacement job plan")
    legacy.verify(serve.SEAL)
    quality, cpu_rows = quality_module()
    queues = plan(approval, cpu_rows)
    serving, pid = check_ready(epoch, approval)
    if (Path(batch_name).name != batch_name or batch_name in {"", ".", ".."}
            or not epoch.is_relative_to(HERE / "runs")):
        raise ValueError("use a private batch name and replacement epoch")
    batch = epoch / "jobs" / batch_name
    batch.mkdir(parents=True, mode=0o700)
    (batch / "units").mkdir()
    legacy.write(batch / "APPROVAL.json", approval)
    legacy.write(batch / "DISPATCH.json", {"approval_sha256": approved_sha, "serving": serving, "server_pid": pid,
                                           "started_at": time.time(), "approved_slots": list(queues)})
    notice = batch / "CONTINUE.md"
    notice.write_text(CONTINUE_TEXT)
    notice.chmod(0o444)
    finished = threading.Event()

    def cancel(*_):
        legacy.STOP.set()
        quality.pilot.stop.set()

    def watch():
        while not finished.wait(.5):
            issue = close_requested(epoch, batch, pid)
            if issue:
                legacy.write(batch / "STOP-REASON.json", {"reason": issue, "at": time.time()})
                cancel()
                return

    def run_slot(queue):
        receipts = []
        for arm, row, ancestry in queue:
            issue = close_requested(epoch, batch, pid)
            if issue or legacy.STOP.is_set():
                break
            if arm == "legacy":
                receipt = legacy.execute(batch, row, serving, quality.pilot)
            else:
                original_id = ancestry["initial_row"]
                if prior_snapshot(dict(row, id=original_id)) != ancestry:
                    raise RuntimeError("previous private state changed before resumption")
                continuation = dict(ancestry, feedback=str(notice), feedback_sha256=legacy.digest(notice))
                receipt = quality.run_row(batch, serving["port"], dict(row, resume=continuation), legacy.V4_SHA)
                metrics = {"classification": "same-session continuation after an interrupted placement-confounded attempt",
                           "previous": ancestry, "continuation_placement_ready_sha256": approval["server_ready_sha256"],
                           "continuation_observed_generated": receipt.get("generation_observed"),
                           "continuation_wall_s": receipt.get("model_wall_s"),
                           "same_session": receipt.get("session") == ancestry["session_id"]}
                if metrics["continuation_observed_generated"] is not None:
                    metrics["cumulative_observed_generated"] = (ancestry["previous_generated_observed"]
                                                                + metrics["continuation_observed_generated"])
                if metrics["continuation_wall_s"] is not None:
                    metrics["cumulative_model_wall_s"] = (ancestry["previous_model_wall_s"]
                                                          + metrics["continuation_wall_s"])
                legacy.write(batch / "units" / row["id"] / "CONTINUATION.json", metrics)
            receipts.append(receipt)
        return receipts

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, cancel)
    with ExitStack() as stack:
        lock_root = epoch / "slot-locks"
        lock_root.mkdir(exist_ok=True)
        for slot in sorted(queues):
            lock = stack.enter_context((lock_root / f"{slot}.lock").open("a"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            with ThreadPoolExecutor(max_workers=len(queues)) as pool:
                records = [f.result() for f in [pool.submit(run_slot, queue) for queue in queues.values()]]
            observed = [r for slot in records for r in slot]
            started = {r["id"] for r in observed}
            pending = [row["id"] for queue in queues.values() for _, row, _ in queue if row["id"] not in started]
            legacy.write(batch / "RESULTS.json", {"terminal": observed, "unattempted": pending,
                                                 "serving_pid": pid, "approval_sha256": approved_sha})
        finally:
            finished.set()
            watcher.join(timeout=2)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    child = cli.add_subparsers(dest="command", required=True)
    p = child.add_parser("draft")
    p.add_argument("out", type=Path)
    p = child.add_parser("verify")
    p.add_argument("draft", type=Path)
    p = child.add_parser("launch")
    p.add_argument("--epoch", type=Path, required=True)
    p.add_argument("--batch", required=True)
    p.add_argument("--approval", type=Path, required=True)
    p.add_argument("--approval-sha256", required=True)
    p.add_argument("--seal-sha256", required=True)
    p = child.add_parser("grade")
    p.add_argument("--attempt", type=Path, required=True)
    p.add_argument("--receipt-sha256", required=True)
    p.add_argument("--reviewed-python-test", action="store_true")
    args = cli.parse_args()
    if args.command == "draft":
        draft(args.out.resolve())
    elif args.command == "verify":
        legacy.verify(serve.SEAL)
        _, rows = quality_module()
        queues = plan(legacy.read(args.draft), rows)
        print(json.dumps({slot: [row["id"] for _, row, _ in queue] for slot, queue in queues.items()}))
    elif args.command == "grade":
        legacy.verify(serve.SEAL)
        attempt = args.attempt.resolve()
        if not attempt.is_relative_to(HERE / "runs"):
            raise ValueError("grading attempt outside CPU replacement scope")
        print(json.dumps(legacy.grade(attempt, args.receipt_sha256, args.reviewed_python_test)))
    else:
        seal = HERE / "DISPATCH-SEAL.json"
        legacy.same_file(seal, args.seal_sha256)
        for name, expected in legacy.read(seal)["sha256"].items():
            legacy.same_file(HERE / name, expected)
        run_batch(args.epoch.resolve(), args.batch, args.approval.resolve(), args.approval_sha256)


if __name__ == "__main__":
    main()
