"""Recover the one unstarted GPU slot-3 queue while the same owner holds its lease."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
BOUNDARY = HERE.parent / "legacy-boundary-v3"
EPOCH = BOUNDARY / "runs/boundary-01"
BOUNDARY_SHA = "185ba0467a41eefd63a9ada0d3856abb565ce7d5a7a6f0af68ef4d0362a288cb"
OLD_MECHANICAL = EPOCH / "units/gpu-PFXC-A3-on-coding-post-review-mechanical-3"
MM_ID = "gpu-MM-5-on-coding"
EXPECTED = {"holder": (3507046, 161578912), "controller": (3507253, 161578918),
            "server": (3553296, 161585422)}


def load_sources():
    sys.path.insert(0, str(BOUNDARY))
    try:
        spec = importlib.util.spec_from_file_location("sealed_boundary_slot3", BOUNDARY / "run.py")
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
    finally:
        sys.path.remove(str(BOUNDARY))
    cpu, gpu, quality, _ = engine.inputs()
    engine.verify(BOUNDARY_SHA, cpu.legacy)
    return engine, cpu, gpu, quality, engine.mechanical


def verify_guard(engine, mechanical, spec):
    for label, (pid, ticks) in EXPECTED.items():
        recorded = spec[label]
        current = mechanical.proc_identity(pid)
        if current != recorded or recorded["pid"] != pid or recorded["start_ticks"] != ticks:
            raise RuntimeError(f"live owned {label} changed")
    mechanical.verify_lease(spec, EXPECTED["controller"][0])
    actual = engine.region(True, owner_pid=EXPECTED["holder"][0])
    if actual != spec["grant"]:
        raise RuntimeError("actual exclusive whole-host grant changed")
    if (EPOCH / "STOP").exists() or (EPOCH / "CLEANUP.json").exists():
        raise RuntimeError("original combined owner is closing")


def plan(engine, cpu, gpu, quality, mechanical, *, probe_idle):
    legacy = cpu.legacy
    paths = [EPOCH / name for name in ("GRANT.json", "APPROVAL.json", "PLAN.json", "SERVING.json",
                                      "mechanical-control/EXECUTION.json", "mechanical-control/worker.log")]
    paths.append(OLD_MECHANICAL / "MECHANICAL-ERROR.json")
    proof = {str(path): legacy.digest(path) for path in paths}
    old = legacy.read(paths[4])
    spec = {**{name: old[name] for name in EXPECTED}, "grant": legacy.read(paths[0]),
            "serving": legacy.read(paths[3])["gpu"]}
    if (old["serving"] != spec["serving"] or old["runner_seal_sha256"] != BOUNDARY_SHA
            or spec["serving"]["port"] != 42559):
        raise RuntimeError("current route differs from the failed slot's owned route")
    approve = legacy.read(paths[1])
    if (approve["approved_by"] != "main" or approve["runner_seal_sha256"] != BOUNDARY_SHA
            or approve["mechanical_package_seal_sha256"] != mechanical.SEAL):
        raise RuntimeError("original owner did not approve the slot-3 rows")
    failure = legacy.read(paths[-1])
    if (failure["status"] != "mechanical_harness_error" or failure["can_reuse_slot"] is not False
            or "has no attribute 'region'" not in failure["error"]):
        raise RuntimeError("original slot has no matching harness failure")
    if (paths[5].stat().st_size != 0 or (EPOCH / "units" / MM_ID).exists()
            or {p.name for p in OLD_MECHANICAL.iterdir()} != {"MECHANICAL-ERROR.json"}):
        raise RuntimeError("slot3 no longer has two unstarted attempts")
    verify_guard(engine, mechanical, spec)
    sys.path[:0] = [str(cpu.legacy.ENGINE)]
    from opencode_derived.__main__ import serving_proof
    if serving_proof(dict(spec["serving"], slot=3, context=131072, backend="gpu")) != EXPECTED["server"][0]:
        raise RuntimeError("active executable/route does not match the sealed C22 serving receipt")
    if probe_idle and not mechanical.idle_slot(spec["serving"]["port"]):
        raise RuntimeError("GPU slot3 is processing another request")
    mechanical_case = mechanical.verify_inputs(cpu, quality)
    rows, _ = gpu.sealed_rows()
    mm = rows[MM_ID]
    if mm["backend"] != "gpu" or mm["slot"] != 3 or mm["thinking"] is not True:
        raise RuntimeError("sealed mandatory MM thinking row changed route")
    return {"schema": "owner-slot3-recovery.v1", **spec, "bound_source_receipts": proof,
            "mechanical": mechanical_case, "legacy_mm_on": mm, "original_attempts_started": False,
            "mechanical_deadline_s": 300, "mm_deadline_s": 1800,
            "write_scope": "private recovery evidence only", "context": 131072}


def verify_seal(legacy, expected):
    manifest = HERE / "RUNNER-SEAL.json"
    legacy.same_file(manifest, expected)
    for name, digest in legacy.read(manifest)["sha256"].items():
        legacy.same_file(HERE / name, digest)


def run_child(mode, epoch, spec_path, checksum):
    engine, cpu, gpu, quality, mechanical = load_sources()
    legacy = cpu.legacy
    legacy.same_file(spec_path, checksum)
    execution = legacy.read(spec_path)
    verify_seal(legacy, execution["seal"])
    approved = execution["plan"]
    if mechanical.proc_identity(os.getppid()) != execution["supervisor"]:
        raise RuntimeError("the callback child has no matching active supervisor")
    verify_guard(engine, mechanical, approved)
    from opencode_derived import __main__ as driver
    if driver.serving_proof(dict(approved["serving"], slot=3, context=131072, backend="gpu")) != EXPECTED["server"][0]:
        raise RuntimeError("the callback child cannot use any other route")

    def custody(base, destination):
        class RegisteredSandbox(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.root.name == "sandbox":
                    legacy.write(destination / "MECHANICAL-CONTAINER-INTENT.json", {"name": self.name})
        return RegisteredSandbox

    if mode == "mechanical":
        row = mechanical.verify_inputs(cpu, quality)
        if row != approved["mechanical"]:
            raise RuntimeError("approved mechanical row changed")
        destination = epoch / "units" / row["id"]
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda *_: quality.pilot.stop.set())
        quality.Sandbox = custody(quality.Sandbox, destination)
        quality.run_row(epoch, approved["serving"]["port"], row, gpu.V4_SHA)
        return 0
    attempt = epoch / "units" / MM_ID
    job_path = attempt / "JOB.json"
    driver.Sandbox = custody(driver.Sandbox, attempt / "worker")
    return driver.main([str(job_path), "--approved-sha256", execution["mm_job_sha256"],
                        "--out", str(attempt / "worker")])


def launch(args, engine, cpu, gpu, quality, mechanical):
    legacy = cpu.legacy
    verify_seal(legacy, args.seal)
    legacy.same_file(args.approval, args.approval_sha256)
    approval = legacy.read(args.approval)
    if approval["approved_by"] != "main" or approval["runner_seal_sha256"] != args.seal:
        raise ValueError("main approval must bind this exact recovery launcher")
    plan_path = Path(approval["plan"])
    legacy.same_file(plan_path, approval["plan_sha256"])
    approved = legacy.read(plan_path)
    if plan(engine, cpu, gpu, quality, mechanical, probe_idle=True) != approved:
        raise RuntimeError("scope or active lease differs from the approved recovery")
    epoch = args.out.resolve()
    if epoch == HERE / "runs" or not epoch.is_relative_to(HERE / "runs"):
        raise ValueError("use a new private recovery path")
    with (HERE / "slot3.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        epoch.mkdir(parents=True, mode=0o700)
        (epoch / "units").mkdir()
        legacy.write(epoch / "APPROVAL.json", approval)
        legacy.write(epoch / "PLAN.json", approved)
        stopped = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda *_: stopped.set())

        def expired():
            if stopped.is_set() or (epoch / "STOP").exists():
                return "recovery_operator_stop"
            try:
                verify_guard(engine, mechanical, approved)
            except (OSError, RuntimeError) as error:
                legacy.write(epoch / "LEASE-LOST.json", {"error": repr(error), "at": time.time()})
                return "original_owner_grant_expired"
            return None

        attempt = epoch / "units" / MM_ID
        attempt.mkdir()
        mm_job = gpu.build_job(epoch, approved["legacy_mm_on"], approved["serving"])
        legacy.write(attempt / "JOB.json", mm_job)
        spec = {"seal": args.seal, "plan": approved,
                "mm_job_sha256": legacy.digest(attempt / "JOB.json"),
                "supervisor": mechanical.proc_identity(os.getpid())}
        execution_path = epoch / "EXECUTION.json"
        legacy.write(execution_path, spec)

        def run_one(mode, dest, seconds):
            if expired():
                return None
            argv = [sys.executable, "-B", "-u", str(Path(__file__)), "child", mode,
                    str(epoch), str(execution_path), legacy.digest(execution_path)]
            try:
                record = mechanical.run_timed(argv, epoch / f"{mode}-worker.log", expired, seconds=seconds)
            finally:
                dest.mkdir(exist_ok=True)
                cleanup = mechanical.cleanup_container(dest / "MECHANICAL-CONTAINER-INTENT.json")
            record.update(cleanup)
            record["slot_reusable"] = not expired() and mechanical.release_slot(approved["serving"]["port"])
            legacy.write(dest / "RECOVERY-SUPERVISION.json", record)
            return record

        row = approved["mechanical"]
        row_dir = epoch / "units" / row["id"]
        first = run_one("mechanical", row_dir, approved["mechanical_deadline_s"])
        if first is None:
            legacy.write(epoch / "RESULTS.json", {"status": "lease_lost_before_submission", "unattempted": [row["id"], MM_ID]})
            return
        raw = legacy.read(row_dir / "RESULT.json") if (row_dir / "RESULT.json").exists() else {}
        try:
            assessment = mechanical.assess(legacy, quality, row_dir, row, raw, first)
        except Exception as error:
            assessment = {"semantic_review": "pending", "assessor_error": repr(error), "native_cap2_status": "REJECT"}
            legacy.write(row_dir / "MECHANICAL-ASSESSMENT.json", assessment)
        summary = {"mechanical": first, "mechanical_assessment": assessment}
        if first["slot_reusable"]:
            mm = run_one("mm", attempt / "worker", approved["mm_deadline_s"])
            summary["mm"] = mm
            receipt = attempt / "worker/receipt.json"
            if receipt.exists():
                verdict = legacy.read(receipt)
                result = {"id": MM_ID, "case": "MM-5", "status": verdict["status"],
                          "worker_receipt_sha256": legacy.digest(receipt), "terminal_at": time.time()}
                if verdict.get("patch_sha256"):
                    lane = gpu.grade_lane(attempt, "MM-5")
                    result.update(status="awaiting_source_review", lane=str(lane))
                legacy.write(attempt / "RESULT.json", result)
                summary["mm_result"] = result
        summary["unattempted"] = [] if summary.get("mm") is not None else [MM_ID]
        legacy.write(epoch / "RESULTS.json", summary)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    child = cli.add_subparsers(dest="command", required=True)
    p = child.add_parser("plan")
    p.add_argument("--out", type=Path)
    x = child.add_parser("launch")
    x.add_argument("--seal", required=True)
    x.add_argument("--approval", type=Path, required=True)
    x.add_argument("--approval-sha256", required=True)
    x.add_argument("--out", type=Path, required=True)
    w = child.add_parser("child")
    w.add_argument("mode", choices=("mechanical", "mm"))
    w.add_argument("epoch", type=Path)
    w.add_argument("spec", type=Path)
    w.add_argument("sha256")
    args = cli.parse_args()
    if args.command == "child":
        return run_child(args.mode, args.epoch.resolve(), args.spec.resolve(), args.sha256)
    engine, cpu, gpu, quality, mechanical = load_sources()
    if args.command == "plan":
        doc = plan(engine, cpu, gpu, quality, mechanical, probe_idle=True)
        if args.out:
            path = args.out.resolve()
            if path.exists() or not path.is_relative_to(HERE):
                raise ValueError("use a new private plan path")
            cpu.legacy.write(path, doc)
            print(json.dumps({"plan": str(path), "sha256": cpu.legacy.digest(path), "model_calls": 0}))
        return 0
    launch(args, engine, cpu, gpu, quality, mechanical)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
