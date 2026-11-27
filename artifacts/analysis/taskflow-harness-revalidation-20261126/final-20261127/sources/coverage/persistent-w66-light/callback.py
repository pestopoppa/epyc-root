"""Dispatch exact jobs through the already-held persistent C22 owner."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
from hashlib import file_digest
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
SUPPORT = HERE.parent / "persistent-tu-on"
SOURCE = "0f61d02d42ae9fef8c4545901ac847ec2d70e8c70e3e94211efc27e7e20b852d"


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def sources():
    manifest = SUPPORT / "RUNNER-SEAL.json"
    if digest(manifest) != SOURCE:
        raise RuntimeError("persistent custody source manifest changed")
    for name in ("follow.py", "lease.py"):
        if digest(SUPPORT / name) != json.loads(manifest.read_text())["sha256"][name]:
            raise RuntimeError("persistent custody source changed")
    sys.path.insert(0, str(SUPPORT))
    try:
        spec = importlib.util.spec_from_file_location("persistent_jobs_source", SUPPORT / "follow.py")
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
    finally:
        sys.path.remove(str(SUPPORT))
    recovery, components = bridge.sources()
    engine, cpu, gpu, quality, mechanical = components
    return bridge, engine, cpu.legacy, gpu, quality, mechanical


def verify(legacy, seal):
    path = HERE / "RUNNER-SEAL.json"
    legacy.same_file(path, seal)
    for name, expected in legacy.read(path)["sha256"].items():
        legacy.same_file(HERE / name, expected)


def live(ctx, plan, row):
    bridge, engine, legacy, _, _, mechanical = ctx
    return bridge.lease.prove(engine, legacy, mechanical, plan["lease"], row["backend"])


def check_item(ctx, plan, item):
    bridge, _, legacy, _, _, _ = ctx
    row = item["row"]
    for name, expected in item["sha256"].items():
        legacy.same_file(Path(name), expected)
    route = live(ctx, plan, row)
    from opencode_derived.__main__ import serving_proof, state_digest
    if serving_proof(dict(route, slot=row["slot"], context=131072, backend=row["backend"])) != plan["lease"]["native"][row["backend"]]["pid"]:
        raise RuntimeError("candidate job could escape the approved serving route")
    if item.get("state_paths"):
        state = state_digest(*map(Path, item["state_paths"]))
        if state != item["state_sha256"]:
            raise RuntimeError("saved OpenCode checkpoint state changed")
    return route


def child(mode, epoch, attempt, spec_path, expected):
    ctx = sources()
    bridge, _, legacy, gpu, quality, mechanical = ctx
    legacy.same_file(spec_path, expected)
    spec = legacy.read(spec_path)
    verify(legacy, spec["seal"])
    if mechanical.proc_identity(os.getppid()) != spec["supervisor"]:
        raise RuntimeError("per-job supervisor changed")
    bridge.lease.verify_receipts(legacy, spec["plan"]["lease"])
    row = spec["job"]["row"]
    route = check_item(ctx, spec["plan"], spec["job"])
    from opencode_derived import __main__ as driver

    def registered(base, path):
        class PrivateSandbox(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.root.name == "sandbox":
                    legacy.write(path / "MECHANICAL-CONTAINER-INTENT.json", {"name": self.name})
        return PrivateSandbox

    if mode == "quality-fresh":
        packet = HERE / "packet-view/packets/DS41-W-66"
        expected = HERE.parent / "w66-light-brief-v2/cases/DS41-W-66"
        if (packet.resolve() != expected or Path(row["case_dir"]).resolve() != expected or row.get("resume")
                or row.get("fresh_session") is not True):
            raise RuntimeError("light-v2 worker cannot use the detailed brief or saved history")
        quality.HERE = HERE / "packet-view"
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda *_: quality.pilot.stop.set())
        quality.Sandbox = registered(quality.Sandbox, attempt)
        quality.run_row(epoch, route["port"], row, gpu.V4_SHA)
        return 0
    if mode != "canonical":
        raise ValueError("unsupported persistent callback kind")
    driver.Sandbox = registered(driver.Sandbox, attempt / "worker")
    return driver.main([str(attempt / "JOB.json"), "--approved-sha256", spec["canonical_job_sha256"],
                        "--out", str(attempt / "worker")])


def launch(ctx, args):
    bridge, _, legacy, gpu, _, mechanical = ctx
    verify(legacy, args.seal)
    legacy.same_file(args.approval, args.approval_sha256)
    approval = legacy.read(args.approval)
    if approval["approved_by"] != "main" or approval["runner_seal_sha256"] != args.seal:
        raise ValueError("main must approve this exact receipt")
    plan_path = Path(approval["plan"])
    legacy.same_file(plan_path, approval["plan_sha256"])
    plan = legacy.read(plan_path)
    bridge.lease.verify_receipts(legacy, plan["lease"])
    if not plan["jobs"]:
        raise ValueError("approved job set is empty")
    queues = {}
    for item in plan["jobs"]:
        row = item["row"]
        key = (row["backend"], row["slot"])
        queues.setdefault(key, []).append(item)
    epoch = args.out.resolve()
    if epoch == HERE / "runs" or not epoch.is_relative_to(HERE / "runs"):
        raise ValueError("use a new private callback directory")
    epoch.mkdir(parents=True, mode=0o700)
    (epoch / "units").mkdir()
    legacy.write(epoch / "PLAN.json", plan)
    legacy.write(epoch / "APPROVAL.json", approval)
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: stopped.set())

    def run_one(item):
        row = item["row"]
        mode = item["kind"]
        provider = check_item(ctx, plan, item)
        if not bridge.slot_idle(provider["port"], row["slot"]):
            raise RuntimeError("the owned slot is still busy")
        attempt = epoch / "units" / item["id"]
        if mode == "quality-fresh" and row["id"] != item["id"]:
            raise ValueError("quality callback output id differs from row")
        if mode == "canonical":
            attempt.mkdir()
            feedback = item.get("feedback")
            if feedback and "text" in feedback:
                message = attempt / "FEEDBACK.txt"
                message.write_text(feedback["text"])
                feedback = {**feedback, "feedback": str(message), "feedback_sha256": legacy.digest(message)}
            job = gpu.build_job(epoch, row, provider, feedback) if item.get("case_spec") is None else {
                **item["case_spec"], **provider, "slot": row["slot"]}
            legacy.write(attempt / "JOB.json", job)
        spec = {"seal": args.seal, "plan": plan, "job": item,
                "supervisor": mechanical.proc_identity(os.getpid())}
        if mode == "canonical":
            spec["canonical_job_sha256"] = legacy.digest(attempt / "JOB.json")
        root = epoch / (item["id"] + ".execution.json")
        legacy.write(root, spec)

        def cancelled():
            if stopped.is_set() or (epoch / "STOP").exists():
                return "operator_stop"
            try:
                live(ctx, plan, row)
            except (OSError, RuntimeError):
                return "persistent_owner_grant_lost"
            return None

        if cancelled():
            raise InterruptedError("owned slot stopped before submission")
        starts = bridge.lease.LOCKS / "starts"
        starts.mkdir(exist_ok=True)
        with (starts / item["id"]).open("x") as marker:
            marker.write(str(attempt) + "\n")
        argv = [sys.executable, "-B", "-u", str(Path(__file__)), "child", mode,
                str(epoch), str(attempt), str(root), legacy.digest(root)]
        registration = attempt / ("worker/MECHANICAL-CONTAINER-INTENT.json" if mode == "canonical"
                                  else "MECHANICAL-CONTAINER-INTENT.json")
        try:
            supervision = mechanical.run_timed(argv, epoch / (item["id"] + ".worker.log"),
                                               cancelled, seconds=row["wall_s"])
        finally:
            cleanup = mechanical.cleanup_container(registration)
        attempt.mkdir(exist_ok=True)
        candidate = attempt / ("worker/receipt.json" if mode == "canonical" else "RESULT.json")
        raw = legacy.read(candidate) if candidate.exists() else {}
        wrap = {"id": item["id"], "case": row["case"], "backend": row["backend"], "slot": row["slot"],
                "supervision": supervision, "cleanup": cleanup, "previous_attempts": item.get("previous_attempts", []),
                "native_status": raw.get("status"), "raw_receipt": str(candidate),
                "terminal_at": time.time(), "source_guidance": item.get("source_guidance"),
                "current_local_tokens": raw.get("generation_observed", raw.get("generated_observed"))}
        parts = [part["generated"] for part in wrap["previous_attempts"]] + [wrap["current_local_tokens"]]
        wrap["known_combined_local_tokens"] = sum(n for n in parts if n is not None)
        wrap["parts_with_unobserved_tokens"] = parts.count(None)
        if mode == "canonical" and raw.get("patch_sha256"):
            lane = gpu.grade_lane(attempt, row["case"])
            wrap.update(status="awaiting_source_review", lane=str(lane), worker_receipt_sha256=legacy.digest(candidate))
        elif mode == "quality-resume" and item.get("grade_v5") and (attempt / "independent/work").is_dir():
            oracle = Path(item["grade_v5"])
            grade = subprocess.run([sys.executable, "-IB", str(oracle), str(attempt / "independent/work")],
                                   check=False, capture_output=True, timeout=30)
            (attempt / "V5.stdout.log").write_bytes(grade.stdout)
            (attempt / "V5.stderr.log").write_bytes(grade.stderr)
            wrap.update(status="awaiting_source_review", independent_v5_rc=grade.returncode,
                        independent_v5_stdout_sha256=legacy.digest(attempt / "V5.stdout.log"),
                        independent_v5_stderr_sha256=legacy.digest(attempt / "V5.stderr.log"))
        else:
            wrap["status"] = "interrupted" if supervision["reason"] else raw.get("status", "worker_absent")
        if item.get("prior_session"):
            wrap["same_session"] = raw.get("session") == item["prior_session"]
        legacy.write(attempt / "CALLBACK-RESULT.json", wrap)
        if mode == "canonical":
            legacy.write(attempt / "RESULT.json", wrap)
        return wrap

    def schedule(key, items):
        backend, slot = key
        bridge.lease.LOCKS.mkdir(exist_ok=True)
        with (bridge.lease.LOCKS / f"{backend}-{slot}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return [run_one(item) for item in items]

    result = []
    with ThreadPoolExecutor(max_workers=len(queues)) as pool:
        submitted = {pool.submit(schedule, k, q): k for k, q in queues.items()}
        for task, coords in submitted.items():
            try:
                result.extend(task.result())
            except Exception as error:
                result.append({"backend": coords[0], "slot": coords[1], "status": "callback_error",
                               "error": repr(error)})
    legacy.write(epoch / "RESULTS.json", {"terminal": result, "original_results_preserved": True})


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    part = cli.add_subparsers(dest="cmd", required=True)
    launch_ = part.add_parser("launch")
    launch_.add_argument("--seal", required=True)
    launch_.add_argument("--approval", required=True, type=Path)
    launch_.add_argument("--approval-sha256", required=True)
    launch_.add_argument("--out", required=True, type=Path)
    worker = part.add_parser("child")
    worker.add_argument("mode")
    worker.add_argument("epoch", type=Path)
    worker.add_argument("attempt", type=Path)
    worker.add_argument("spec", type=Path)
    worker.add_argument("sha256")
    args = cli.parse_args()
    if args.cmd == "child":
        return child(args.mode, args.epoch, args.attempt, args.spec, args.sha256)
    launch(sources(), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
