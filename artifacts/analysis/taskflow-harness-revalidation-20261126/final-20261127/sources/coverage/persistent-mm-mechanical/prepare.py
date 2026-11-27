"""Stage the one verifier-only MM exception after an independently graded cap-two result."""
from pathlib import Path
import tempfile

import callback

COVERAGE = callback.HERE.parent
INPUTS = COVERAGE.parent
REVIEW = INPUTS / "source-review-gpu-mm-objective-2"
CASE = INPUTS / "mm5-oracle-v4"
CASE_SHA = "0dd66ef730a0715235abbae6e78ac71f99bff80aa35fac7c24b09d19cda48368"
BASE = "gpu-MM-5-off-common-on-sampling"
PARENT = COVERAGE / "persistent-callback/runs/mm-v4-01/units" / (BASE + "-v4-objective-2")
OBSERVED = "cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (28, 28) exceed the cap"


def build():
    ctx = callback.sources()
    bridge, _, legacy, gpu, _, _ = ctx
    row = gpu.sealed_rows()[0][BASE]
    paths = {}
    manifest = CASE / "SOURCE-CONTROL.sha256"
    paths[str(manifest)] = legacy.same_file(manifest, CASE_SHA)
    for line in manifest.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        source = CASE / name
        paths[str(source)] = legacy.same_file(source, expected)
    directory = REVIEW / "grades-v4" / PARENT.name
    assessment = legacy.read(directory / "RESULT.json")
    review = REVIEW / "REVIEW.json"
    paths[str(review)] = legacy.same_file(review, assessment["source_review_sha256"])
    wrapped = legacy.read(PARENT / "CALLBACK-RESULT.json")
    worker = PARENT / "worker"
    prior = legacy.read(worker / "receipt.json")
    receipt_sha = legacy.digest(worker / "receipt.json")
    patch = worker / "candidate/candidate.patch"
    patch_sha = legacy.same_file(patch, prior["patch_sha256"])
    checks = assessment["checks"]
    if (assessment["rc"] != 1 or assessment["id"] != PARENT.name or not assessment["raw_results_preserved"]
            or assessment["candidate_patch_sha256"] != patch_sha
            or assessment["oracle_sha256"] != paths[str(CASE / "oracle.py")]
            or assessment["check_module_sha256"] != paths[str(CASE / "vision_contract_v4.py")]
            or checks["additional_infeasible_cap_robustness"]["detail"] != OBSERVED
            or checks["additional_infeasible_cap_robustness"]["status"] != "fail"
            or checks["brief_environment_control"]["status"] != "pass"
            or checks["unchanged_original_and_v2_feasible"]["status"] != "pass"
            or wrapped["source_guidance"]["ordinal"] != 2 or not wrapped["terminal_at"]
            or not wrapped["same_session"] or wrapped["worker_receipt_sha256"] != receipt_sha):
        raise RuntimeError("MM cap-two receipt differs from the qualified sole cap-one failure")
    for name, expected in legacy.read(review)["rows"][PARENT.name]["input_sha256"].items():
        paths[name] = legacy.same_file(Path(name), expected)
    for item in assessment["prior_grades_preserved"].values():
        paths[item["path"]] = legacy.same_file(Path(item["path"]), item["sha256"])
    for stream in ("stdout", "stderr"):
        path = directory / f"{stream}.log"
        paths[str(path)] = legacy.same_file(path, assessment[f"{stream}_sha256"])
    for path in (directory / "RESULT.json", PARENT / "RESULT.json", PARENT / "CALLBACK-RESULT.json",
                 PARENT / "JOB.json", worker / "receipt.json", worker / "session.json", patch):
        paths[str(path)] = legacy.digest(path)
    note = ("Continue in the same saved workspace and session. A supplemental independent verifier reported:\n\n"
            + OBSERVED + "\n\nAddress only that observation, keeping the original scope and previous working behaviors.\n")
    from opencode_derived import __main__ as driver
    from opencode_derived.sandbox import Assets, Sandbox
    state_paths = [str(worker / "sandbox/work"), str(worker / "sandbox/session")]
    state = driver.state_digest(*map(Path, state_paths))
    if state != prior["workspace_session_sha256"]:
        raise RuntimeError("canonical cap-two predecessor bytes changed")
    feedback = {"text": note, "prior_attempt": str(worker), "prior_receipt_sha256": receipt_sha,
                "prior_session_sha256": paths[str(worker / "session.json")], "prior_workspace_session_sha256": state}
    earlier = list(wrapped["previous_attempts"])
    earlier.append({"path": str(PARENT), "generated": prior.get("generated_observed"),
                    "worker_wall_s": prior["ended_at"] - prior["started_at"]})
    job = {"id": BASE + "-v4-mechanical-3", "kind": "canonical", "row": row, "sha256": paths,
           "owner_deadline_s": 300, "feedback": feedback, "state_paths": state_paths, "state_sha256": state,
           "prior_session": prior["session"], "previous_attempts": earlier,
           "source_guidance": {"paid_model_calls": 0, "ordinal": 3, "class": "extra post-review verifier-only",
                               "original_cap_two_robustness_reject_preserved": True,
                               "additional_infeasible_cap_robustness_only": True,
                               "claim_minimum_guidance": False}}
    plan = {"lease": bridge.lease.snapshot(legacy), "jobs": [job], "model_calls_during_preparation": 0,
            "after": "W66 light-v2 OFF terminal, GPU2 lock released, native slot idle"}
    route = callback.check_item(ctx, plan, job)
    with tempfile.TemporaryDirectory(dir=callback.HERE) as temp:
        out = Path(temp)
        prompt = out / "diagnostic.txt"
        prompt.write_text(note)
        envelope = dict(feedback, feedback=str(prompt), feedback_sha256=legacy.digest(prompt))
        source = out / "JOB.json"
        legacy.write(source, gpu.build_job(out, row, route, envelope))
        native, _, case, _ = driver.load_job(source, legacy.digest(source))
        assets = native["assets"]
        box = Sandbox(out / "sandbox", native["port"], "84-87", assets=Assets(
            Path(assets["opencode"]), Path(assets["python_packages"]), Path(assets["socket_root"]),
            image=assets["image"], executable_sha256=assets["opencode_sha256"]), ctx=native["context"],
            cap=native["request_cap"], transport_wall_s=native["wall_s"], public_web=native["public_web"])
        if driver.restore_session(native, case, box) != prior["session"]:
            raise RuntimeError("offline canonical restore differed from cap-two predecessor")
    path = callback.HERE / "MM-MECHANICAL-3-PLAN.json"
    legacy.write(path, plan)
    legacy.write(callback.HERE / "CONTROL.json", {"passed": True, "native_calls": 0,
        "canonical_same_session_config_offline": True, "case_scope_and_actual_v4_receipts_bound": True,
        "model_facing_provider_wall_s": row["wall_s"], "external_deadline_s": 300,
        "native_route_verified": True, "plan_sha256": legacy.digest(path),
        "existing_watchdog_proof": "e310f09960fae6b6bf8801c520395f49c0494a91fcfa8f267dabbef4aa746a0f"})
    print(legacy.digest(path))


if __name__ == "__main__":
    build()
