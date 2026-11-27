"""Owner-bound, two-turn TU OFF recovery from actual contained CI failure."""
import argparse
from contextlib import contextmanager
import fcntl
from hashlib import file_digest
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time

import ci_grade

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent
ROOT = COVERAGE.parent
SOURCE = COVERAGE / "persistent-callback"
SOURCE_SEAL = "e203f1389e8753223da7ff9623ce67fad0f627716dd735c39117cce8344c5803"
ARM = "gpu-TU-GR-1-off-common-on-sampling"
PAID = SOURCE / "runs/tu-off-paid-01"
PRIOR = PAID / "units" / (ARM + "-paid-2")
V2 = ROOT / "source-review-gpu-mm-on-tu-paid/grades-tu-v2" / PRIOR.name
V3 = ROOT / "tu-oracle-v3"
V3_SEAL = "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b"
V3_CHECKER = "01a09351635c64b5b6f7c7486a4baee391095e7f18041a6380cf479aac313bda"
W66 = COVERAGE / "persistent-w66-light-12/runs/light-01"
W66_ID = "gpu-DS41-W-66-on-common-light-v2"
W66_PLAN = "77674acc57934b69f84fa6ee49dab7ed5df020b0077733d5e510cf90125a55a1"
W66_APPROVAL = "244ccc9bfe42382b7f6cc035a6d625f24c4af38a6b3131f0b8db089eae2fb6c0"
CEILING = 120000
DURATION = 900
PER_TURN = 450
STOP = threading.Event()


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def require(path, checksum):
    if digest(path) != checksum:
        raise RuntimeError(f"sealed input changed: {path}")


def read(path):
    return json.loads(path.read_bytes())


def sources():
    seal = SOURCE / "RUNNER-SEAL.json"
    require(seal, SOURCE_SEAL)
    require(SOURCE / "callback.py", read(seal)["sha256"]["callback.py"])
    spec = importlib.util.spec_from_file_location("approved_tu_ci_custody", SOURCE / "callback.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.sources()


def verify_seal(checksum):
    seal = HERE / "RUNNER-SEAL.json"
    require(seal, checksum)
    for name, expected in read(seal)["sha256"].items():
        require(HERE / name, expected)
    require(V3 / "SOURCE-CONTROL.sha256", V3_SEAL)
    for line in (V3 / "SOURCE-CONTROL.sha256").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        require(V3 / name, expected)
    require(V3 / "tu_grader_isolation.py", V3_CHECKER)


def diagnostic(path):
    """Keep the actual V2/V3 assertion and candidate traceback, with volatile paths removed."""
    content = "\n".join((path / (stem + ".log")).read_text(errors="replace")
                        for stem in ("stdout", "stderr"))
    content = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", content)
    lines = content.splitlines()
    head = next((line for line in lines if line.strip()), "")
    tail = re.search(r"(?m)^(FAILED |ERROR ).*(?:test_grader_isolation\.py|test_isolated_launch_denies).*$", content)
    exception = tail.group() if tail else ""
    if tail and "Traceback (most recent call last)" in exception:
        for line in content[tail.end():].splitlines():
            if line.startswith(("  File ", "    ", "During handling ", "Traceback ")) or re.match(
                    r"^[A-Za-z_.]+(?:Error|Exception|Warning):", line):
                exception += "\n" + line
            elif line.strip():
                break
    detail = "\n".join(line for line in (head, exception) if line)
    detail = re.sub(r"/tmp/taskflow-tu-grader-[a-zA-Z0-9_-]+", "<verifier scratch>", detail)
    detail = re.sub(r"/(?:mnt|home|root|workspace)/[^\s\"'<>]+", "<host path>", detail)
    detail = "".join(c for c in detail if c.isprintable() or c in "\n\t")
    return detail[:7200].strip()


def feedback_text(detail, checker):
    return ("The contained TU acceptance checker reported the result below for the saved candidate. "
            "Use this failure evidence to debug the existing candidate and continue the original task. "
            "Keep the original scope and test contract. The verifier will rerun after this turn.\n\n"
            f"Evidence from the trusted TU {checker} checker\n\n"
            + "\n".join("> " + line for line in detail.splitlines()) + "\n")


def classify(grade, detail, prior_detail, same_candidate):
    if grade["reason"] or grade["rc"] not in (0, 1):
        return "checker_interrupted_or_unavailable"
    if grade["rc"] == 0:
        return "checker_pass_pending_source_review"
    if not detail or not detail.startswith(("simulated namespace ", "direct ", "namespace ")):
        return "no_usable_candidate_diagnostic"
    if same_candidate:
        return "unchanged_candidate"
    if detail == prior_detail:
        return "duplicate_failure"
    return "new_failure"


def checkpoint(worker):
    from opencode_derived.__main__ import state_digest

    receipt_path = worker / "receipt.json"
    receipt = read(receipt_path)
    state = state_digest(worker / "sandbox/work", worker / "sandbox/session")
    if (receipt["workspace_session_sha256"] != state or not receipt["session"]
            or receipt["status"] != "review"):
        raise RuntimeError("previous candidate has no intact terminal session to resume")
    return {"prior_attempt": str(worker), "prior_receipt_sha256": digest(receipt_path),
            "prior_session_sha256": digest(worker / "session.json"),
            "prior_workspace_session_sha256": state}


def counted(worker, session):
    receipt = read(worker / "receipt.json")
    charged, observed = receipt["charged_toward_ceiling"], receipt["generated_observed"]
    if (receipt["session"] != session or receipt["reserved_at_terminal"] != 0
            or type(observed) is not int or type(charged) is not int
            or not 0 <= observed <= charged <= CEILING):
        raise RuntimeError("session or cumulative-token accounting is unresolved")
    return {"path": str(worker), "receipt_sha256": digest(worker / "receipt.json"),
            "generated": observed, "charged": charged,
            "generation_unknown": receipt["generation_unknown"]}


def prior_attempts():
    return [
        COVERAGE / "legacy-boundary-v3/runs/boundary-01/units" / ARM / "worker",
        COVERAGE / "objective-followup/runs/tu-01/units" / (ARM + "-objective-1") / "worker",
        PRIOR / "worker",
    ]


def stage(ctx):
    bridge, _, _, _, _, _ = ctx
    require(PAID / "PLAN.json", "54efa40ccb5176f68cfe2cece2d942ac0359aa765846259fc13f4cf36a4d2f51")
    require(V2 / "RESULT.json", "d3d3e72c122d2589d2d0aef972aec1c0e196c90a84cdd854ca70ab8f00ab89f1")
    original = read(PAID / "PLAN.json")["jobs"][0]
    grade = read(V2 / "RESULT.json")
    path = PRIOR / "worker"
    receipt = read(path / "receipt.json")
    patch = path / "candidate/candidate.patch"
    require(patch, grade["candidate_patch_sha256"])
    if grade["rc"] != 1 or grade["candidate_patch_sha256"] != receipt["patch_sha256"]:
        raise RuntimeError("prior V2 failure does not bind the saved candidate")
    for stream in ("stdout", "stderr"):
        require(V2 / (stream + ".log"), grade[stream + "_sha256"])
    detail = diagnostic(V2)
    if "ModuleNotFoundError: No module named 'harness'" not in detail:
        raise RuntimeError("approved candidate exception is absent")
    row = original["row"]
    if (row["id"] != ARM or row["case"] != "TU-GR-1" or row["backend"] != "gpu" or row["slot"] != 1
            or row["thinking"] or row["wall_s"] != 1800 or row["request_cap"] != 32768):
        raise RuntimeError("unexpected original TU OFF route/profile")
    history = [counted(p, receipt["session"]) for p in prior_attempts()]
    hashes = dict(original["sha256"])
    for part in history:
        hashes[part["path"] + "/receipt.json"] = part["receipt_sha256"]
    for item in (patch, path / "session.json", PRIOR / "CALLBACK-RESULT.json", PAID / "PLAN.json",
                 V2 / "RESULT.json", V2 / "stdout.log", V2 / "stderr.log",
                 W66 / "PLAN.json", W66 / "APPROVAL.json"):
        hashes[str(item)] = digest(item)
    lease = bridge.lease.snapshot(ctx[2])
    if lease != read(PAID / "PLAN.json")["lease"]:
        raise RuntimeError("paid2 and the current persistent lease differ")
    return {"row": row, "lease": lease, "sha256": hashes, "history": history,
            "session": receipt["session"], "checkpoint": checkpoint(path),
            "prior_paid_guidance": original["source_guidance"], "new_paid_guidance_calls": 0,
            "first_feedback": feedback_text(detail, "V2"), "first_diagnostic": detail,
            "original_verdict": "cap2_rejected_preserved", "repeat_grade": "V3",
            "budget": {"turns": 2, "branch_wall_s": DURATION, "each_active_s": PER_TURN,
                       "cumulative_generated_ceiling": CEILING}}


def predecessor(lease):
    require(W66 / "PLAN.json", W66_PLAN)
    require(W66 / "APPROVAL.json", W66_APPROVAL)
    plan = read(W66 / "PLAN.json")
    jobs = [job for job in plan["jobs"] if job["id"] == W66_ID]
    if plan["lease"] != lease or len(jobs) != 1 or (jobs[0]["row"]["backend"], jobs[0]["row"]["slot"]) != ("gpu", 1):
        raise RuntimeError("wrong W66 predecessor or native owner")
    path = W66 / "units" / W66_ID / "CALLBACK-RESULT.json"
    if not path.exists():
        return None
    result = read(path)
    if (result["id"] != W66_ID or result["backend"] != "gpu" or result["slot"] != 1
            or not result["terminal_at"] or not result["cleanup"]["removed_verified"]
            or result["supervision"]["returncode"] is None):
        raise RuntimeError("W66 predecessor lacks a valid terminal and cleanup receipt")
    return {"receipt": str(path), "sha256": digest(path), "status": result["status"]}


@contextmanager
def own_slot(ctx, plan, output, cancelled):
    bridge = ctx[0]
    lock = bridge.lease.LOCKS / "gpu-1.lock"
    while (reason := cancelled()) is None:
        previous = predecessor(plan["lease"])
        if previous:
            with lock.open("a") as lease:
                try:
                    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    provider = plan["lease"]["providers"]["gpu"]
                    if bridge.slot_idle(provider["port"], 1):
                        ctx[2].write(output / "READY.json", previous)
                        yield
                        return
        time.sleep(1)
    raise InterruptedError(reason)


def child(seal, spec_path, spec_sha):
    verify_seal(seal)
    require(spec_path, spec_sha)
    spec = read(spec_path)
    callback, ctx = sources()
    bridge, _, legacy, _, _, mechanical = ctx
    if mechanical.proc_identity(os.getppid()) != spec["supervisor"]:
        raise RuntimeError("worker lost its exact owner-bound supervisor")
    bridge.lease.verify_receipts(legacy, spec["lease"])
    callback.live(ctx, spec, {"backend": "gpu"})
    from opencode_derived import __main__ as driver

    attempt = spec_path.parent
    path = attempt / "worker"
    original = driver.Sandbox

    class RegisteredSandbox(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            legacy.write(path / "MECHANICAL-CONTAINER-INTENT.json", {"name": self.name})

    driver.Sandbox = RegisteredSandbox
    return driver.main([str(attempt / "JOB.json"), "--approved-sha256", spec["job_sha256"],
                        "--out", str(path)])


def grade_candidate(ctx, attempt, deadline, cancelled):
    _, _, _, gpu, _, _ = ctx
    from opencode_derived.case_snapshot import file_map

    lane = gpu.grade_lane(attempt, "TU-GR-1")
    before = file_map(lane)
    if before[1]:
        raise RuntimeError("unsafe independent candidate lane")
    output = attempt / "grade-v3"
    result = ci_grade.run(lane, V3 / "tu_grader_isolation.py", output, deadline, cancelled)
    if file_map(lane) != before:
        raise RuntimeError("contained checker changed independent candidate bytes")
    for stream in ("stdout", "stderr"):
        result[stream + "_sha256"] = digest(output / (stream + ".log"))
    result.update(checker_sha256=V3_CHECKER, checker_manifest_sha256=V3_SEAL, model_calls=0)
    ctx[2].write(output / "RESULT.json", result)
    return result, diagnostic(output)


def issue_turn(callback, ctx, plan, seal, output, ordinal, history, previous, detail, deadline, cancelled):
    bridge, _, legacy, gpu, _, mechanical = ctx
    remaining = CEILING - sum(previous["charged"] for previous in history)
    # Each child sizes its transport ledger from the remaining whole-chain budget.
    # Session matching excludes this cumulative ceiling, retaining SDK wall and per-call cap.
    if remaining <= 0 or deadline - time.monotonic() < 75 or cancelled():
        return {"status": "branch_budget_or_owner_exhausted"}, None, None
    source_grade = "V2" if ordinal == 1 else "V3"
    row = plan["row"]
    route = callback.live(ctx, plan, row)
    if not bridge.slot_idle(route["port"], row["slot"]):
        raise RuntimeError("owned TU slot still processing before the next turn")
    name = f"{ARM}-auto-ci-{ordinal}"
    attempt = output / "units" / name
    attempt.mkdir()
    prompt = attempt / "FEEDBACK.txt"
    prompt.write_text(feedback_text(detail, source_grade))
    if ordinal == 1 and prompt.read_text() != plan["first_feedback"]:
        raise RuntimeError("initial diagnostic differs from the approved CI prompt")
    previous_worker = previous / "worker"
    saved = checkpoint(previous_worker)
    if ordinal == 1 and saved != plan["checkpoint"]:
        raise RuntimeError("paid2 checkpoint changed since approval")
    feedback = dict(saved, feedback=str(prompt), feedback_sha256=digest(prompt))
    job = gpu.build_job(output, {**row, "generated_ceiling": remaining}, route, feedback)
    job_path = attempt / "JOB.json"
    legacy.write(job_path, job)
    spec = attempt / "EXECUTION.json"
    legacy.write(spec, {"lease": plan["lease"], "supervisor": mechanical.proc_identity(os.getpid()),
                        "job_sha256": digest(job_path)})
    argv = [sys.executable, "-B", "-u", str(Path(__file__)), "child", seal, str(spec), digest(spec)]
    intent = attempt / "worker/MECHANICAL-CONTAINER-INTENT.json"
    starts = bridge.lease.LOCKS / "starts"
    starts.mkdir(exist_ok=True)
    with (starts / name).open("x") as marker:
        marker.write(str(attempt) + "\n")
    active_seconds = min(PER_TURN - 15, deadline - time.monotonic() - 65)
    if active_seconds <= 0 or cancelled():
        return {"status": "branch_budget_or_owner_exhausted"}, None, None
    try:
        supervision = mechanical.run_timed(argv, attempt / "worker.log", cancelled,
                                           seconds=active_seconds, grace=15)
    finally:
        cleanup = mechanical.cleanup_container(intent)
    receipt_path = attempt / "worker/receipt.json"
    result = {"id": name, "case": "TU-GR-1", "backend": "gpu", "slot": 1,
              "raw_receipt": str(receipt_path), "supervision": supervision, "cleanup": cleanup,
              "previous_attempts": list(history), "feedback_sha256": digest(prompt),
              "source_guidance": {"paid_model_calls": 0, "class": "automatic contained CI exception",
                                  "ordinal": ordinal},
              "remaining_generated_at_start": remaining, "terminal_at": time.time()}
    followup_detail = None
    try:
        if not receipt_path.is_file():
            result.update(status="worker_receipt_unavailable", token_accounting_unresolved=True)
            return result, None, None
        receipt = read(receipt_path)
        debit = counted(receipt_path.parent, plan["session"])
        if debit["charged"] > remaining:
            raise RuntimeError("transport exceeded remaining authorized generated tokens")
        history.append(debit)
        result.update(native_status=receipt["status"], same_session=True,
                      current_local_tokens=debit["generated"], current_charged=debit["charged"],
                      known_combined_local_tokens=sum(part["generated"] for part in history),
                      cumulative_charged=sum(part["charged"] for part in history))
        if receipt["status"] not in ("review", "interrupted") or not receipt.get("patch_sha256"):
            result["status"] = "no_scope_verified_candidate"
            return result, None, None
        if cancelled() or deadline - time.monotonic() < 30:
            result["status"] = "candidate_preserved_checker_deadline_or_grant_loss"
            return result, None, None
        verdict, followup_detail = grade_candidate(ctx, attempt, deadline, cancelled)
        prior_receipt = read(previous_worker / "receipt.json")
        status = classify(verdict, followup_detail, detail,
                          prior_receipt["patch_sha256"] == receipt["patch_sha256"])
        if status == "new_failure" and (supervision["reason"] or receipt["status"] != "review"):
            status = "interrupted_candidate_preserved"
        result.update(status=status, grade=verdict, lane=str(attempt / "grade-lane"),
                      grade_result=str(attempt / "grade-v3/RESULT.json"))
        return result, attempt, followup_detail
    except (ValueError, RuntimeError, TimeoutError, OSError, KeyError) as error:
        result.update(status="candidate_or_grader_custody_failed", error=repr(error))
        return result, None, None
    finally:
        legacy.write(attempt / "CALLBACK-RESULT.json", result)


def launch(args):
    verify_seal(args.seal)
    require(args.approval, args.approval_sha256)
    approval = read(args.approval)
    if approval["approved_by"] != "main" or approval["runner_seal_sha256"] != args.seal:
        raise ValueError("main must approve the exact auto-CI plan and source")
    path = Path(approval["plan"])
    require(path, approval["plan_sha256"])
    plan = read(path)
    callback, ctx = sources()
    bridge, _, legacy, _, _, _ = ctx
    bridge.lease.verify_receipts(legacy, plan["lease"])
    for path, checksum in plan["sha256"].items():
        require(Path(path), checksum)
    # Rederive the fixed policy and historic input from the actual saved receipts.
    if plan != stage(ctx):
        raise ValueError("owner-staged CI plan does not match the exact fixed branch")
    output = args.out.resolve()
    runs = HERE / "runs"
    if output.parent != runs:
        raise ValueError("use a new private auto-CI run under runs/")
    output.mkdir(parents=True, mode=0o700)
    (output / "units").mkdir()
    legacy.write(output / "PLAN.json", plan)
    legacy.write(output / "APPROVAL.json", approval)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: STOP.set())

    def cancelled():
        if STOP.is_set() or (output / "STOP").exists():
            return "operator_stop"
        try:
            callback.live(ctx, plan, plan["row"])
        except (RuntimeError, OSError):
            return "persistent_owner_grant_lost"
        return None

    history = list(plan["history"])
    detail, previous = plan["first_diagnostic"], PRIOR
    outcome = {"turns": [], "original_verdict": plan["original_verdict"],
               "prior_paid_guidance": plan["prior_paid_guidance"], "new_paid_guidance_calls": 0,
               "semantic_review_required": True}
    try:
        with own_slot(ctx, plan, output, cancelled):
            deadline = time.monotonic() + DURATION
            for ordinal in (1, 2):
                result, previous, detail = issue_turn(callback, ctx, plan, args.seal, output, ordinal,
                                                       history, previous, detail, deadline, cancelled)
                outcome["turns"].append(result)
                outcome["status"] = result["status"]
                if result["status"] != "new_failure":
                    break
            if outcome["status"] == "new_failure":
                outcome["status"] = "two_ci_turn_budget_exhausted"
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        outcome.update(status="auto_ci_harness_or_owner_stop", error=repr(error))
    finally:
        outcome.update(token_lineage=history, accounted_charged=sum(p["charged"] for p in history),
                       terminal_at=time.time())
        legacy.write(output / "RESULTS.json", outcome)
        print(json.dumps({"status": outcome["status"], "turns": len(outcome["turns"])}))
    return 0 if outcome["status"] == "checker_pass_pending_source_review" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="mode", required=True)
    prepare = subs.add_parser("prepare")
    prepare.add_argument("--seal", required=True)
    prepare.add_argument("--out", required=True, type=Path)
    start = subs.add_parser("launch")
    start.add_argument("--seal", required=True)
    start.add_argument("--approval", required=True, type=Path)
    start.add_argument("--approval-sha256", required=True)
    start.add_argument("--out", required=True, type=Path)
    work = subs.add_parser("child")
    work.add_argument("seal")
    work.add_argument("spec", type=Path)
    work.add_argument("sha256")
    args = parser.parse_args()
    if args.mode == "launch":
        return launch(args)
    if args.mode == "child":
        return child(args.seal, args.spec, args.sha256)
    verify_seal(args.seal)
    _, ctx = sources()
    plan = stage(ctx)
    with args.out.open("x") as fd:
        json.dump(plan, fd, indent=2)
        fd.write("\n")
    print(json.dumps({"sha256": digest(args.out), "previous_charged": sum(p["charged"] for p in plan["history"]),
                      "new_main_calls": 0, "model_calls": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
