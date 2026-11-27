"""Bind paid TU and deterministic MM owner receipts to persistent canonical workers."""
import argparse
import json
from pathlib import Path
import tempfile

import callback

COVERAGE = callback.HERE.parent
ROOT = COVERAGE.parent
TU = "cpu-TU-GR-1-off-recommended"
MM_OFF = "cpu-MM-5-off-recommended"
MM_ON = "gpu-MM-5-on-coding"
G4 = ROOT / "mm5-oracle-v4"
V4_SHA = "0dd66ef730a0715235abbae6e78ac71f99bff80aa35fac7c24b09d19cda48368"
TUR = COVERAGE / "legacy-assisted-review/reviews/TU-GR-1/cpu-OFF-off-recommended/initial-diagnosis"
MMR = ROOT / "source-review-cpu-objective-followup"


def actual_usage(measurement):
    trace = measurement["jsonl"]
    if (trace["completed_turn_count"] != 1 or trace["errors"] or not measurement["path_scope_pass"]
            or measurement["changed_by_strong_turn"] or measurement["final_changes"] == []):
        raise RuntimeError("paid source guidance altered the candidate or lacks an exact terminal record")
    return trace["usage"]


def paid_tu(legacy, prior, proof, patch_sha):
    plan_dir = TUR / "runs/TU-GR-1/guidance-1"
    supplied = plan_dir / "FEEDBACK.txt"
    summary = plan_dir / "measurement.json"
    evidence = plan_dir / "events.jsonl"
    plan_path = plan_dir / "plan.json"
    measure = legacy.read(summary)
    usage = actual_usage(measure)
    plan = legacy.read(plan_path)
    projected = COVERAGE / "legacy-assisted-review/projections" / prior.name
    projection = legacy.read(projected / "PROJECTION.json")
    if (projection["source_owner_result"] != str(prior / "RESULT.json")
            or projection["projected_result_sha256"] != plan["source_native_result_sha256"]
            or projection["projected_patch_sha256"] != patch_sha
            or plan["candidate_input_patch_sha256"] != patch_sha or plan["allowed_next_native_correction"] != 2
            or plan["native_correction_ceiling"] != 2 or plan["native_ordinal"] != 1):
        raise RuntimeError("paid guidance refers to a different objective checkpoint or round")
    for name, expected in projection["source_hashes"].items():
        proof[name] = legacy.same_file(Path(name), expected)
    final = [item["item"]["text"] for item in (json.loads(row) for row in evidence.read_text().splitlines())
             if item.get("type") == "item.completed" and item.get("item", {}).get("type") == "agent_message"]
    if not final or supplied.read_text().strip() != final[-1].strip() or not final[-1].startswith("REJECT"):
        raise RuntimeError("selected paid feedback differs from the exact terminal advisory")
    for file in (supplied, summary, evidence, plan_path, TUR / "MAIN-APPROVAL.json",
                 projected / "PROJECTION.json", projected / "RESULT.json"):
        proof[str(file)] = legacy.digest(file)
    return {"feedback": str(supplied), "feedback_sha256": proof[str(supplied)]}, {
        "paid_model_calls": 1, "ordinal": 2, "class": "measured paid source review corrective guidance",
        "usage": usage, "model": measure["requested_model"], "effort": measure["requested_effort"],
        "measured_wall_s": measure["execution"]["wall_s"]}


def objective_mm(legacy, prior, proof, patch_sha, name, ordinal):
    control = G4 / "SOURCE-CONTROL.sha256"
    proof[str(control)] = legacy.same_file(control, V4_SHA)
    for line in control.read_text().splitlines():
        expected, filename = line.split(maxsplit=1)
        path = G4 / filename
        proof[str(path)] = legacy.same_file(path, expected)
    grade = MMR / "grades-v4" / name
    receipt = legacy.read(grade / "RESULT.json")
    if (receipt["rc"] != 1 or receipt["id"] != name or receipt["candidate_patch_sha256"] != patch_sha
            or receipt["oracle_sha256"] != proof[str(G4 / "oracle.py")]
            or receipt["check_module_sha256"] != proof[str(G4 / "vision_contract_v4.py")]
            or not receipt["raw_results_preserved"]):
        raise RuntimeError("MM v4 owner assessment differs from this candidate")
    for role in ("stdout", "stderr"):
        path = grade / f"{role}.log"
        proof[str(path)] = legacy.same_file(path, receipt[f"{role}_sha256"])
    path = MMR / "REVIEW.json"
    proof[str(path)] = legacy.same_file(path, receipt["source_review_sha256"])
    record = legacy.read(path)["rows"][name]
    if record["candidate_patch_sha256"] != patch_sha:
        raise RuntimeError("MM tested source was a different candidate")
    for path, expected in record["input_sha256"].items():
        proof[path] = legacy.same_file(Path(path), expected)
    for ref in receipt["prior_grades_preserved"].values():
        proof[ref["path"]] = legacy.same_file(Path(ref["path"]), ref["sha256"])
    proof[str(grade / "RESULT.json")] = legacy.digest(grade / "RESULT.json")
    details = [check["detail"] for check in receipt["checks"].values() if check["status"] == "fail"]
    permitted = {"cap=1: encoder did not return within 8 seconds",
                 "cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (28, 28) exceed the cap",
                 "ORCHESTRATOR_VL_MAX_PIXELS=784: sent dimensions (896, 896), expected (28, 28)"}
    if not details or any(obs not in permitted for obs in details):
        raise RuntimeError("v4 negative observation is outside the approved exact diagnostics")
    message = ("Continue the task in the same saved workspace and session. The independent versioned verifier observed:\n\n"
               + "\n".join("- " + obs for obs in details)
               + "\n\nAddress those observed behaviors and retain the original requirements, scope, and focused task tests.\n")
    return {"text": message}, {"paid_model_calls": 0, "ordinal": ordinal, "class": "verifier observations only",
                               "original_grades_preserved": True, "checker_version": "MM v4"}


def native_cost(legacy, path):
    receipt = legacy.read(path / "worker/receipt.json")
    return {"path": str(path), "generated": receipt.get("generated_observed"),
            "worker_wall_s": receipt["ended_at"] - receipt["started_at"]}


def item(ctx, name):
    _, _, legacy, gpu, _, _ = ctx
    rows, _ = gpu.sealed_rows()
    row = rows[name]
    if name == TU:
        initial = COVERAGE / "cpu-numa-repair/runs/cpu-02/jobs/measured-01/units" / name
        prior = COVERAGE / "objective-followup/runs/tu-01/units" / (name + "-objective-1")
    elif name == MM_OFF:
        initial = COVERAGE / "cpu-numa-repair/runs/cpu-02/jobs/measured-01/units" / name
        prior = COVERAGE / "mm-objective-followup/runs/mm-01/units" / (name + "-objective-1")
    elif name == MM_ON:
        initial = prior = COVERAGE / "slot3-recovery/runs/fix-01/units" / name
    else:
        raise ValueError("unqualified callback name")
    worker = prior / "worker"
    report = legacy.read(prior / "RESULT.json")
    receipt = legacy.read(worker / "receipt.json")
    digest = legacy.digest(worker / "receipt.json")
    if (not report["terminal_at"] or report["status"] != "awaiting_source_review"
            or report["worker_receipt_sha256"] != digest or receipt["status"] != "review"):
        raise RuntimeError("same-session continuation requires an exact reviewed, scoped candidate")
    patch = worker / "candidate/candidate.patch"
    patch_sha = legacy.same_file(patch, receipt["patch_sha256"])
    files = {str(path): legacy.digest(path) for path in (patch, worker / "receipt.json", worker / "session.json",
                                                         prior / "RESULT.json", prior / "JOB.json")}
    ordinal = 1 if name == MM_ON else 2
    feedback, accounting = paid_tu(legacy, prior, files, patch_sha) if name == TU else objective_mm(
        legacy, prior, files, patch_sha, prior.name, ordinal)
    state_paths = [str(worker / "sandbox/work"), str(worker / "sandbox/session")]
    from opencode_derived.__main__ import state_digest
    state = state_digest(*map(Path, state_paths))
    if state != receipt["workspace_session_sha256"]:
        raise RuntimeError("canonical OpenCode saved state changed")
    feedback.update(prior_attempt=str(worker), prior_receipt_sha256=digest,
                    prior_session_sha256=files[str(worker / "session.json")], prior_workspace_session_sha256=state)
    label = name + ("-paid-2" if name == TU else f"-v4-objective-{ordinal}")
    return {"id": label, "kind": "canonical", "row": row, "sha256": files, "feedback": feedback,
            "state_paths": state_paths, "state_sha256": state, "prior_session": receipt["session"],
            "source_guidance": accounting, "previous_attempts": [
                native_cost(legacy, path) for path in dict.fromkeys((initial, prior))]}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.parse_args()
    ctx = callback.sources()
    bridge, _, legacy, gpu, _, _ = ctx
    names = (TU, MM_OFF)
    from opencode_derived import __main__ as driver
    from opencode_derived.sandbox import Assets, Sandbox
    plan = {"lease": bridge.lease.snapshot(legacy), "jobs": [item(ctx, name) for name in names],
            "model_calls_during_preparation": 0}
    restored = {}
    with tempfile.TemporaryDirectory(dir=callback.HERE) as scratch:
        folder = Path(scratch)
        for record in plan["jobs"]:
            row = record["row"]
            route = callback.check_item(ctx, plan, record)
            if not bridge.slot_idle(route["port"], row["slot"]):
                raise RuntimeError(f"persistent {row['backend']}/{row['slot']} is busy")
            out = folder / str(row["slot"])
            out.mkdir()
            envelope = record["feedback"]
            if "text" in envelope:
                message = out / "feedback.txt"
                message.write_text(envelope["text"])
                envelope = dict(envelope, feedback=str(message), feedback_sha256=legacy.digest(message))
            prepared = gpu.build_job(folder, row, route, envelope)
            job_path = out / "JOB.json"
            legacy.write(job_path, prepared)
            job, _, case, _ = driver.load_job(job_path, legacy.digest(job_path))
            spec = job["assets"]
            box = Sandbox(out / "sandbox", job["port"], "84-87", assets=Assets(
                Path(spec["opencode"]), Path(spec["python_packages"]), Path(spec["socket_root"]),
                image=spec["image"], executable_sha256=spec["opencode_sha256"]), ctx=job["context"],
                cap=job["request_cap"], transport_wall_s=job["wall_s"], public_web=job["public_web"])
            session = driver.restore_session(job, case, box)
            if session != record["prior_session"]:
                raise RuntimeError("offline canonical resume yielded different session")
            restored[record["id"]] = session
    label = "CPU-TU-MM"
    target = callback.HERE / (label + "-PLAN.json")
    legacy.write(target, plan)
    legacy.write(callback.HERE / (label + "-CONTROL.json"), {"passed": True, "native_calls": 0,
        "offline_restored_sessions": restored, "new_active_grant_and_idle_slots": True,
        "plan_sha256": legacy.digest(target), "preparer_sha256": legacy.digest(Path(__file__))})
    print(legacy.digest(target))


if __name__ == "__main__":
    main()
