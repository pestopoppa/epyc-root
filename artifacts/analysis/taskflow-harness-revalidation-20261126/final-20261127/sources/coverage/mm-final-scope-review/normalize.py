"""Bind three exact MM objective-only candidates and stage independent final reviews."""
import json
from pathlib import Path
import shutil

import review

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
COVERAGE = HERE.parent
NATIVE = COVERAGE / "persistent-callback"
MM = ROOT / "mm5-oracle-v4"
CASE = COVERAGE / "legacy-comparison/cases/MM-5/case.json"
ROWS = {
    "gpu-MM-5-on-coding-v4-objective-1": (
        "mm-v4-01", "source-review-gpu-mm-on-tu-paid/grades-v4",
        "369955ac3ce54965c17ba702dc494146e8f5fb242171ee5e668edef7feffe63f", 1),
    "gpu-MM-5-off-common-on-sampling-v4-objective-2": (
        "mm-v4-01", "source-review-gpu-mm-objective-2/grades-v4",
        "66414931b053ad1d9bfac19070a312b27e1ad1dca4e96e210444341dea8fb0f6", 2),
    "cpu-MM-5-off-recommended-v4-objective-2": (
        "cpu-tu-mm-01", "source-review-cpu-paid-terminal/grades",
        "5e929eb362a3123ca2e00c41bf5599d96bee86639e1a7507615d68be63a7d0d9", 2),
}
PLANS = {
    "mm-v4-01": "1c71921fa4d653a6996a4ae2a62dba1851c1b954980ed0840ee95f46d27353f4",
    "cpu-tu-mm-01": "9dbe1061abdb87ca63f9943355ff94c647198eedd5a9c9ad817ce1680f0ac7f8",
}
ORACLE_MANIFEST = "0dd66ef730a0715235abbae6e78ac71f99bff80aa35fac7c24b09d19cda48368"
ORACLE_SHA = "0f3ab2bb06b1b6e209795e9aa103ed2a7b134322daaa04e37fa60a70d8aa3c2a"
CHECKER_SHA = "b74f64cccb3ac7543f6283ad92a25067fe8e4e47ded63b310b2580992f75c091"
CASE_SHA = "08d950e7bfe1447adbd9f0fe124f1bfcf0b34cf5b6199e6c80b7049474f4a655"
STATUS = {"brief_environment_control": "pass", "unchanged_original_and_v2_feasible": "pass",
          "additional_infeasible_cap_robustness": "fail"}


def stage(unit_id, spec):
    epoch_name, grade_dir, grade_hash, ordinal = spec
    sources = {}

    def bind(path, expected=None):
        checksum = review.sha(path)
        if expected is not None and checksum != expected:
            raise RuntimeError(f"candidate input differs: {path}")
        sources[str(path)] = checksum
        return checksum

    bind(CASE, CASE_SHA)
    bind(MM / "SOURCE-CONTROL.sha256", ORACLE_MANIFEST)
    for line in (MM / "SOURCE-CONTROL.sha256").read_text().splitlines():
        checksum, name = line.split(maxsplit=1)
        bind(MM / name, checksum)
    case = review.load(CASE)
    epoch = NATIVE / "runs" / epoch_name
    bind(epoch / "PLAN.json", PLANS[epoch_name])
    bind(epoch / "APPROVAL.json")
    plan = review.load(epoch / "PLAN.json")
    [entry] = [job for job in plan["jobs"] if job["id"] == unit_id]
    row = entry["row"]
    unit = epoch / "units" / unit_id
    owner_path = unit / "CALLBACK-RESULT.json"
    owner = review.load(owner_path)
    if (owner["status"] != "awaiting_source_review" or not owner["terminal_at"]
            or not owner["cleanup"]["removed_verified"] or not owner["same_session"]
            or owner["source_guidance"] != entry["source_guidance"]
            or entry["source_guidance"]["paid_model_calls"] != 0 or not row["case"] == "MM-5"):
        raise RuntimeError("scope or measured correction class differs")
    bind(owner_path)
    for name, checksum in entry["sha256"].items():
        bind(Path(name), checksum)
    history = [Path(part["path"]) for part in entry["previous_attempts"]] + [unit]
    if len(history) != ordinal + 1:
        raise RuntimeError("incomplete prior objective-feedback lineage")
    transcript = []
    previous = None
    for idx, lane in enumerate(history):
        worker = lane / "worker"
        path = worker / "receipt.json"
        bind(path)
        receipt = review.load(path)
        job_path = lane / "JOB.json"
        bind(job_path, receipt["job_sha256"])
        job = review.load(job_path)
        if (receipt["case"] != case["id"] or receipt["session"] != entry["prior_session"]
                or receipt["task_packet_sha256"] != case["task_packet_sha256"]
                or receipt["repo_base_sha"] != case["repo_base_sha"]
                or receipt["status"] != "review" or receipt["unsafe_paths"] or receipt["outside_scope"]):
            raise RuntimeError("saved attempt changed case, session or scope")
        if previous is not None:
            prior_path, prior = previous
            resume = receipt["resume"]
            if (receipt["resume"] != job["resume"] or Path(resume["prior_run"]) != prior_path.parent
                    or resume["receipt_sha256"] != sources[str(prior_path)]
                    or resume["workspace_session_sha256"] != prior["workspace_session_sha256"]):
                raise RuntimeError("saved continuation does not bind exact previous attempt")
            bind(prior_path.parent / "session.json", resume["session_sha256"])
            prompt_path = Path(job["prompt"])
            bind(prompt_path, receipt["prompt_sha256"])
            if not prompt_path.is_relative_to(lane) or job["prompt_sha256"] != receipt["prompt_sha256"]:
                raise RuntimeError("objective prompt differs from the actual native job")
            transcript.append({"path": str(prompt_path), "sha256": receipt["prompt_sha256"],
                               "native_ordinal": idx, "help_kind": "deterministic verifier observations only"})
        previous = path, receipt
    bind(unit / "worker/receipt.json", owner["worker_receipt_sha256"])
    patch = unit / "worker/candidate/candidate.patch"
    bind(patch, receipt["patch_sha256"])
    bind(unit / "worker/session.json")
    if not set(receipt["changed_files"]) <= set(case["editable_paths"]):
        raise RuntimeError("terminal candidate exceeds original approved paths")
    grade_path = ROOT / grade_dir / unit_id / "RESULT.json"
    bind(grade_path, grade_hash)
    grade = review.load(grade_path)
    if (grade["id"] != unit_id or grade["rc"] != 1
            or grade["candidate_patch_sha256"] != receipt["patch_sha256"]
            or grade["oracle_sha256"] != ORACLE_SHA
            or (grade.get("check_module_sha256") != CHECKER_SHA
                and grade.get("oracle_manifest_sha256") != ORACLE_MANIFEST)
            or {name: check["status"] for name, check in grade["checks"].items()} != STATUS):
        raise RuntimeError("grades do not bind exact original scope checks and separate cap behavior")
    for stream in ("stdout", "stderr"):
        bind(grade_path.parent / (stream + ".log"), grade[stream + "_sha256"])
    structural = {
        "rc": grade["rc"], "candidate_patch_sha256": receipt["patch_sha256"],
        "oracle_sha256": grade["oracle_sha256"], "acceptance_version": "MM V4",
        "native_suite_components": grade["checks"],
        "scope": "observed contained V4 test outcomes; reviewer interprets original brief",
    }
    candidate = {
        "id": unit_id, "case": case["id"], "backend": row["backend"], "slot": row["slot"],
        "thinking": row["thinking"], "profile": row["profile"], "sampling": row["sampling"],
        "status": owner["status"], "terminal_at": owner["terminal_at"], "session": receipt["session"],
        "changed_files": receipt["changed_files"], "patch_sha256": receipt["patch_sha256"],
        "outside_scope": receipt["outside_scope"], "unsafe_paths": receipt["unsafe_paths"],
        "generation_observed": receipt["generated_observed"],
        "model_wall_s": receipt["ended_at"] - receipt["started_at"], "native_ordinal": ordinal,
        "actual_prior_feedback": transcript, "projection_sources": sources, "oracle": structural,
        "prior_measured_paid_guidance": {"paid_model_calls": 0, "help": "actual deterministic feedback only"},
    }
    output = HERE / "projections" / unit_id
    (output / "independent").mkdir(parents=True)
    shutil.copy2(patch, output / "independent/candidate.patch")
    review.write(output / "RESULT.json", candidate)
    review.write(output / "STRUCTURAL-RECEIPT.json", structural)
    prepared = review.stage(output / "RESULT.json", "final-acceptance", ordinal,
                            output / "STRUCTURAL-RECEIPT.json")
    return {**prepared, "id": unit_id, "historical_paid_guidance_calls": 0,
            "historical_verifier_messages": len(transcript)}


if __name__ == "__main__":
    review.source_lock()
    print(json.dumps([stage(unit_id, spec) for unit_id, spec in ROWS.items()], indent=2))
