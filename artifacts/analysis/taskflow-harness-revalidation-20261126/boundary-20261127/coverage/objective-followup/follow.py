"""Run objective legacy verifier feedback inside the already-owned combined serving epoch."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import fcntl
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
RECOVERY = HERE.parent / "slot3-recovery"
RECOVERY_SHA = "b4e9a10f04507dbdeb2c11e86a5150feb415a70bd9098661dcd377e1b41cb372"
EPOCH = HERE.parent / "legacy-boundary-v3/runs/boundary-01"
CPU02 = HERE.parent / "cpu-numa-repair/runs/cpu-02/jobs/measured-01/units"
REVIEW = HERE.parent.parent / "source-review-legacy-boundary"
CPU_NATIVE = (3553728, 161585436)
CURRENT_TU = ("cpu-TU-GR-1-off-recommended", "gpu-TU-GR-1-off-common-on-sampling")
MM_ID = "gpu-MM-5-on-coding"


def sources():
    path = RECOVERY / "recover.py"
    ref = RECOVERY / "RUNNER-SEAL.json"
    from hashlib import sha256
    if sha256(ref.read_bytes()).hexdigest() != RECOVERY_SHA:
        raise RuntimeError("slot3 custody source manifest changed")
    if sha256(path.read_bytes()).hexdigest() != json.loads(ref.read_text())["sha256"]["recover.py"]:
        raise RuntimeError("slot3 custody source changed")
    spec = importlib.util.spec_from_file_location("verified_slot3_custody", path)
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    return recovery, recovery.load_sources()


def prior_path(name):
    if name.startswith("cpu-"):
        return CPU02 / name
    if name == MM_ID:
        return RECOVERY / "runs/fix-01/units" / name
    return EPOCH / "units" / name


def slot_idle(port, slot):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=4)) as connection:
        connection.request("GET", "/slots")
        reply = connection.getresponse()
        if reply.status != 200:
            raise RuntimeError(f"owned slot check returned HTTP {reply.status}")
        slots = json.loads(reply.read())
    return not next(item for item in slots if item["id"] == slot)["is_processing"]


def expected_slot_done(legacy, row):
    desired = (row["backend"], row["slot"])
    original = legacy.read(EPOCH / "PLAN.json")
    approved = legacy.read(EPOCH / "APPROVAL.json")
    entries = original["cpu_rows"] + original["legacy_gpu_rows"]
    if approved["gpu_supplements"]:
        entries += original["gpu_supplements"]
    for item in entries:
        planned = item["row"]
        if (planned["backend"], planned["slot"]) != desired:
            continue
        terminal = EPOCH / "units" / planned["id"] / "RESULT.json"
        if row["id"] == MM_ID and planned["id"] == MM_ID:
            terminal = prior_path(MM_ID) / "RESULT.json"
            if not (RECOVERY / "runs/fix-01/RESULTS.json").exists():
                raise RuntimeError("the original slot3 callback has not ended")
        if not terminal.exists() or not legacy.read(terminal).get("terminal_at"):
            raise RuntimeError(f"the combined owner can still write slot {desired}: {planned['id']}")


def grant(recovery, engine, legacy, mechanical, spec, backend):
    recovery.verify_guard(engine, mechanical, spec)
    if backend == "cpu":
        active = mechanical.proc_identity(CPU_NATIVE[0])
        if active != spec["cpu"] or active["start_ticks"] != CPU_NATIVE[1] or active["ppid"] != spec["controller"]["pid"]:
            raise RuntimeError("owned balanced CPU serving process changed")
    provider = legacy.read(EPOCH / "SERVING.json")[backend]
    if provider != spec["providers"][backend]:
        raise RuntimeError("active route changed")
    return provider


def objective_diagnostic(case, stdout):
    # Copy observed behavior from the sealed diagnostic and omit stdout snippets
    # that contain candidate code, local paths, or evaluator implementation.
    if case != "TU-GR-1":
        raise ValueError("no qualified deterministic extractor for this case")
    lead = re.match(r"^simulated namespace [a-z -]+: expected rc=\d+ and control [a-z]+ / isolated [a-z]+, got rc=\d+",
                    stdout)
    if lead is None:
        raise ValueError("sealed failure does not map to a qualified objective diagnostic")
    pieces = [lead[0] + "."]
    if "Expected listdir_ok=False" in stdout and "'listdir_ok': True" in stdout:
        pieces.append("The validator expected listdir_ok=False and observed listdir_ok=True.")
    if "SyntaxError: invalid syntax" in stdout:
        pieces.append("The isolated launcher emitted SyntaxError: invalid syntax.")
    elif "Launcher exited with code 1" in stdout:
        pieces.append("The isolated launcher exited with code 1.")
    if "test_isolated_launch_denies" in stdout:
        pieces.append("The failed test was test_isolated_launch_denies.")
    return " ".join(pieces)


def stage(recovery, components, names):
    engine, cpu, gpu, quality, mechanical = components
    legacy = cpu.legacy
    shared = legacy.read(RECOVERY / "CURRENT-PLAN.json")
    spec = {name: shared[name] for name in ("holder", "controller", "server", "grant")}
    spec["cpu"] = mechanical.proc_identity(CPU_NATIVE[0])
    spec["providers"] = legacy.read(EPOCH / "SERVING.json")
    rows, _ = gpu.sealed_rows()
    records = []
    for name in names:
        if name not in rows:
            raise ValueError("unknown sealed legacy attempt")
        row = rows[name]
        prior = prior_path(name)
        worker = prior / "worker"
        result = legacy.read(prior / "RESULT.json")
        receipt = legacy.read(worker / "receipt.json")
        case = legacy.read(legacy.PACKAGE / "cases" / row["case"] / "case.json")
        expected_slot_done(legacy, row)
        provider = grant(recovery, engine, legacy, mechanical, spec, row["backend"])
        if not slot_idle(provider["port"], row["slot"]):
            raise RuntimeError(f"owned route not idle: {row['backend']}/{row['slot']}")
        from opencode_derived.__main__ import state_digest, serving_proof
        serving_proof(dict(provider, slot=row["slot"], context=131072, backend=row["backend"]))
        prior_receipt = legacy.digest(worker / "receipt.json")
        if (result["status"] != "awaiting_source_review" or not result.get("terminal_at")
                or result["worker_receipt_sha256"] != prior_receipt
                or receipt["case"] != row["case"] or receipt["session_profile"]["slot"] != row["slot"]):
            raise RuntimeError("grade does not follow the exact scoped legacy candidate")
        patch = worker / "candidate/candidate.patch"
        patch_sha = legacy.same_file(patch, receipt["patch_sha256"])
        if (prior / "independent/oracle-result.json").exists():
            grade = prior / "independent/oracle-result.json"
            original_grade = legacy.read(grade)
            if original_grade["checked_candidate_files"] != receipt["changed_files"]:
                raise RuntimeError("grade did not check this exact candidate")
            stdout, stderr = grade.parent / "oracle.stdout.log", grade.parent / "oracle.stderr.log"
        else:
            root = REVIEW / "grades" / name
            grade = root / "RESULT.json"
            original_grade = legacy.read(grade)
            if original_grade["id"] != name or original_grade["candidate_patch_sha256"] != patch_sha:
                raise RuntimeError("grade patch digest does not match this exact candidate")
            stdout, stderr = root / "stdout.log", root / "stderr.log"
        if original_grade["rc"] != 1 or original_grade["oracle_sha256"] != case["oracle_sha256"]:
            raise ValueError("only a real rc1 from the original sealed checker is eligible")
        legacy.same_file(stdout, original_grade["stdout_sha256"])
        legacy.same_file(stderr, original_grade["stderr_sha256"])
        message = objective_diagnostic(row["case"], stdout.read_text(errors="replace"))
        state = state_digest(worker / "sandbox/work", worker / "sandbox/session")
        if not receipt["session"] or state != receipt["workspace_session_sha256"]:
            raise RuntimeError("stored same-session state differs from its worker receipt")
        records.append({"id": name, "row": row, "grade_receipt": str(grade),
            "grade_receipt_sha256": legacy.digest(grade), "prior_owner_result_sha256": legacy.digest(prior / "RESULT.json"),
            "diagnostic": message, "prior_attempt": str(worker), "prior_receipt_sha256": prior_receipt,
            "prior_session_sha256": legacy.digest(worker / "session.json"),
            "prior_workspace_session_sha256": state, "prior_patch_sha256": patch_sha,
            "ordinal": 1, "source_guidance_tokens": 0, "max_protocol_rounds": 2,
            "prior_cost": {"generation": receipt.get("generated_observed"),
                           "elapsed_s": receipt["ended_at"] - receipt["started_at"]},
            "prior_session": receipt["session"]})
    coordinates = [(item["row"]["backend"], item["row"]["slot"]) for item in records]
    if len(coordinates) != len(set(coordinates)):
        raise ValueError("one deterministic callback per distinct physical slot")
    return {"schema": "legacy-objective-followup.v1", "cohort": records, "lease": spec,
            "native_calls_during_preparation": 0, "original_results_unchanged": True}


def verify(legacy, expected):
    ref = HERE / "RUNNER-SEAL.json"
    legacy.same_file(ref, expected)
    for name, digest in legacy.read(ref)["sha256"].items():
        legacy.same_file(HERE / name, digest)


def isolated_worker(attempt, job_sha, provenance, provenance_sha):
    recovery, components = sources()
    engine, cpu, _, _, mechanical = components
    legacy = cpu.legacy
    legacy.same_file(provenance, provenance_sha)
    spec = legacy.read(provenance)
    verify(legacy, spec["runner_seal_sha256"])
    if mechanical.proc_identity(os.getppid()) != spec["supervisor"]:
        raise RuntimeError("deterministic continuation worker supervisor changed")
    grant(recovery, engine, legacy, mechanical, spec["lease"], spec["backend"])
    from opencode_derived import __main__ as driver
    original = driver.Sandbox

    class RegisteredSandbox(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            legacy.write(self.root.parent / "MECHANICAL-CONTAINER-INTENT.json", {"name": self.name})

    driver.Sandbox = RegisteredSandbox
    return driver.main([str(attempt / "JOB.json"), "--approved-sha256", job_sha, "--out", str(attempt / "worker")])


def launch(args, recovery, components):
    engine, cpu, gpu, _, mechanical = components
    legacy = cpu.legacy
    verify(legacy, args.seal)
    legacy.same_file(args.approval, args.approval_sha256)
    approval = legacy.read(args.approval)
    if approval["approved_by"] != "main" or approval["runner_seal_sha256"] != args.seal:
        raise ValueError("main must approve the exact sealed objective followup")
    plan_path = Path(approval["plan"])
    legacy.same_file(plan_path, approval["plan_sha256"])
    prepared = legacy.read(plan_path)
    if stage(recovery, components, [entry["id"] for entry in prepared["cohort"]]) != prepared:
        raise RuntimeError("current source, grade, checkpoint or owned route differs from approval")
    out = args.out.resolve()
    if out == HERE / "runs" or not out.is_relative_to(HERE / "runs"):
        raise ValueError("use a new private followup directory")
    out.mkdir(parents=True, mode=0o700)
    legacy.write(out / "APPROVAL.json", approval)
    legacy.write(out / "PLAN.json", prepared)
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: stopped.set())

    def one(item):
        row = item["row"]
        backend, slot = row["backend"], row["slot"]
        lock_path = RECOVERY / "slot3.lock" if backend == "gpu" and slot == 3 else HERE / f"{backend}-{slot}.lock"
        with lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return in_slot(item, row, backend, slot)

    def in_slot(item, row, backend, slot):
        attempt = out / "units" / (item["id"] + "-objective-1")
        attempt.mkdir(parents=True)
        provider = grant(recovery, engine, legacy, mechanical, prepared["lease"], backend)
        if not slot_idle(provider["port"], slot):
            raise RuntimeError("reserved response slot is busy")
        launch_guard = HERE / "started" / item["id"]
        feedback = attempt / "VERIFIER-FEEDBACK.md"
        feedback.write_text("Continue the same task and scope from the saved workspace and session.\n\n"
                            "The independent verifier reported:\n\n" + item["diagnostic"] + "\n\n"
                            "Address that observed failure. Preserve the original requirements and rerun the task-local check.\n")
        feedback.chmod(0o444)
        envelope = dict(item, feedback=str(feedback), feedback_sha256=legacy.digest(feedback))
        job_path = attempt / "JOB.json"
        legacy.write(job_path, gpu.build_job(out, row, provider, envelope))
        spec = {"runner_seal_sha256": args.seal, "supervisor": mechanical.proc_identity(os.getpid()),
                "lease": prepared["lease"], "backend": backend}
        provenance = attempt / "EXECUTION.json"
        legacy.write(provenance, spec)

        def lost():
            if stopped.is_set() or (out / "STOP").exists():
                return "owner_cancel"
            try:
                grant(recovery, engine, legacy, mechanical, prepared["lease"], backend)
            except (OSError, RuntimeError):
                return "combined_owner_grant_lost"
            return None

        argv = [sys.executable, "-B", "-u", str(Path(__file__)), "worker", str(attempt),
                legacy.digest(job_path), str(provenance), legacy.digest(provenance)]
        if lost():
            raise RuntimeError("owner grant stopped before verifier followup submission")
        launch_guard.parent.mkdir(exist_ok=True)
        with launch_guard.open("x") as marker:
            marker.write(str(attempt) + "\n")
        try:
            supervised = mechanical.run_timed(argv, attempt / "worker.log", lost, seconds=row["wall_s"])
        finally:
            cleanup = mechanical.cleanup_container(attempt / "worker/MECHANICAL-CONTAINER-INTENT.json")
        status = {"id": item["id"], "case": row["case"], "backend": backend, "slot": slot,
                  "worker": supervised, "cleanup": cleanup, "prior_cost": item["prior_cost"],
                  "verifier_feedback_sha256": legacy.digest(feedback),
                  "verifier_feedback_utf8_bytes": feedback.stat().st_size, "paid_source_guidance_tokens": 0,
                  "round": 1, "second_round_requires_separate_paid_guidance_approval": True,
                  "status": "interrupted" if supervised["reason"] else "no_receipt", "terminal_at": time.time()}
        receipt = attempt / "worker/receipt.json"
        if receipt.exists():
            result = legacy.read(receipt)
            elapsed = result["ended_at"] - result["started_at"]
            generated = result.get("generated_observed")
            status.update(worker_status=result["status"], same_session=result.get("session") == item["prior_session"],
                          worker_receipt_sha256=legacy.digest(receipt), objective_cost={"generation": generated, "elapsed_s": elapsed},
                          cumulative_observed_generation=(item["prior_cost"]["generation"] + generated
                              if generated is not None and item["prior_cost"]["generation"] is not None else None),
                          cumulative_elapsed_s=item["prior_cost"]["elapsed_s"] + elapsed)
            status["status"] = result["status"] if not supervised["reason"] else "interrupted"
            if result.get("patch_sha256"):
                lane = gpu.grade_lane(attempt, row["case"])
                status.update(status="awaiting_source_review", lane=str(lane))
        legacy.write(attempt / "RESULT.json", status)
        return status

    with ThreadPoolExecutor(max_workers=len(prepared["cohort"])) as pool:
        submitted = {pool.submit(one, item): item["id"] for item in prepared["cohort"]}
        results = []
        for task, name in submitted.items():
            try:
                results.append(task.result())
            except Exception as error:
                results.append({"id": name, "status": "callback_error", "error": repr(error)})
    legacy.write(out / "RESULTS.json", {"terminal": results, "raw_prior_evidence_preserved": True})


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    draft = sub.add_parser("draft")
    draft.add_argument("--out", type=Path, required=True)
    draft.add_argument("ids", nargs="+")
    start = sub.add_parser("launch")
    start.add_argument("--seal", required=True)
    start.add_argument("--approval", type=Path, required=True)
    start.add_argument("--approval-sha256", required=True)
    start.add_argument("--out", type=Path, required=True)
    work = sub.add_parser("worker")
    work.add_argument("attempt", type=Path)
    work.add_argument("job_sha")
    work.add_argument("provenance", type=Path)
    work.add_argument("provenance_sha")
    check = sub.add_parser("grade")
    check.add_argument("--seal", required=True)
    check.add_argument("--attempt", required=True, type=Path)
    check.add_argument("--receipt-sha256", required=True)
    check.add_argument("--reviewed-python-test", action="store_true")
    args = cli.parse_args()
    if args.command == "worker":
        return isolated_worker(args.attempt.resolve(), args.job_sha, args.provenance.resolve(), args.provenance_sha)
    recovery, components = sources()
    if args.command == "grade":
        legacy = components[1].legacy
        verify(legacy, args.seal)
        attempt = args.attempt.resolve()
        if not attempt.is_relative_to(HERE / "runs"):
            raise ValueError("grade only a private objective followup attempt")
        print(json.dumps(legacy.grade(attempt, args.receipt_sha256, args.reviewed_python_test)))
        return 0
    if args.command == "draft":
        path = args.out.resolve()
        if path.exists() or not path.is_relative_to(HERE):
            raise ValueError("stage into a new private artifact")
        document = stage(recovery, components, args.ids)
        legacy = components[1].legacy
        legacy.write(path, document)
        print(legacy.digest(path))
        return 0
    launch(args, recovery, components)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
