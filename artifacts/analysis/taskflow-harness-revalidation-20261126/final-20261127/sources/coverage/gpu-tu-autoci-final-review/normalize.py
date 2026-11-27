"""Project the finite, actual GPU TU Auto-CI lineage for independent review."""
from pathlib import Path
import json
import shutil

import review

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent
ROOT = COVERAGE.parent
CI = COVERAGE / "persistent-tu-off-auto-ci"
EPOCH = CI / "runs/auto-01"
UNIT = "gpu-TU-GR-1-off-common-on-sampling-auto-ci-2"
ORACLE = ROOT / "tu-oracle-v3"
PATCH = "64e5c64624fded791a5235670204af173ad9c4d1f681e82ffc3a6420ca152014"
V3_MANIFEST = "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b"
BOUND = {
    EPOCH / "PLAN.json": "85bc19dd6bc4d8254b5b04c14b90a237195d9c1fcc4dab3d2d90bae4c28779e9",
    EPOCH / "APPROVAL.json": "5b134c73e0720f11154a670ea49f05e094a4ddfd2e32cfff96e9e1a36eff7c4f",
    EPOCH / "RESULTS.json": "d5320957647bd0156646548d846dda74122e1d33ae8efd4991fecba76f33bb64",
    EPOCH / "units" / UNIT / "grade-v3/RESULT.json":
        "a77104561efa744df8b42ac74805776e9e57082f9008945fcca8190644fe9d57",
    CI / "RUNNER-SEAL.json": "8fd3519c1517ce56c73ba1c7ff53a43cb180cd5d8c58eec17d94ba02427a1ccd",
    ORACLE / "SOURCE-CONTROL.sha256": V3_MANIFEST,
}


def main():
    review.source_lock()
    sources = {}

    def bind(path, expected=None):
        checksum = review.sha(path)
        if expected is not None and checksum != expected:
            raise ValueError(f"exact source differs: {path}")
        sources[str(path)] = checksum
        return checksum

    for path, digest in BOUND.items():
        bind(path, digest)
    for name, digest in review.load(CI / "RUNNER-SEAL.json")["sha256"].items():
        bind(CI / name, digest)
    for line in (ORACLE / "SOURCE-CONTROL.sha256").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        bind(ORACLE / name, digest)
    plan = review.load(EPOCH / "PLAN.json")
    terminal = review.load(EPOCH / "RESULTS.json")
    if (terminal["status"] != "checker_pass_pending_source_review" or
            terminal["original_verdict"] != "cap2_rejected_preserved" or
            terminal["new_paid_guidance_calls"] != 0 or len(terminal["turns"]) != 2):
        raise ValueError("unexpected terminal supplemental CI state")
    for name, digest in plan["sha256"].items():
        bind(Path(name), digest)
    lineage = terminal["token_lineage"]
    if ([part["generated"] for part in lineage] != [6470, 12765, 9660, 7777, 5108] or
            terminal["accounted_charged"] != 41780):
        raise ValueError("actual native token lineage differs")
    checkpoints = []
    for part in lineage:
        worker = Path(part["path"])
        receipt_path = worker / "receipt.json"
        bind(receipt_path, part["receipt_sha256"])
        receipt = review.load(receipt_path)
        job_path = worker.parent / "JOB.json"
        bind(job_path, receipt["job_sha256"])
        if (receipt["session"] != plan["session"] or receipt["status"] != "review"
                or receipt["generated_observed"] != part["generated"]
                or receipt["charged_toward_ceiling"] != part["charged"]
                or receipt["generation_unknown"] != part["generation_unknown"]
                or receipt["reserved_at_terminal"] != 0 or receipt["outside_scope"] or receipt["unsafe_paths"]):
            raise ValueError("open or inconsistent native checkpoint")
        if checkpoints:
            previous, prior_receipt = checkpoints[-1]
            resume = receipt["resume"]
            if (Path(resume["prior_run"]) != previous or
                    resume["receipt_sha256"] != sources[str(previous / "receipt.json")] or
                    resume["workspace_session_sha256"] != prior_receipt["workspace_session_sha256"]):
                raise ValueError("checkpoint continuation does not bind exact predecessor")
            bind(previous / "session.json", resume["session_sha256"])
        checkpoints.append((worker, receipt))
    unit = EPOCH / "units" / UNIT
    worker, receipt = checkpoints[-1]
    if worker.parent != unit or receipt["patch_sha256"] != PATCH:
        raise ValueError("final worker or patch identity differs")
    patch = worker / "candidate/candidate.patch"
    bind(patch, PATCH)
    bind(worker / "session.json")
    for idx, turn in enumerate(terminal["turns"], 1):
        turn_path = checkpoints[idx + 2][0].parent / "CALLBACK-RESULT.json"
        bind(turn_path)
        if (review.load(turn_path) != turn or not turn["cleanup"]["removed_verified"]
                or not turn["same_session"]):
            raise ValueError("supplemental CI terminal/cleanup record differs")
        grade_path = Path(turn["grade_result"])
        bind(grade_path)
        grade = review.load(grade_path)
        if (grade != turn["grade"] or grade["rc"] != (1 if idx == 1 else 0)
                or grade["checker_manifest_sha256"] != V3_MANIFEST or not grade["cleanup_verified"]):
            raise ValueError("contained V3 terminal not qualified")
        for stream in ("stdout", "stderr"):
            bind(grade_path.parent / (stream + ".log"), grade[stream + "_sha256"])

    help_records = []
    for ordinal, (path, prior) in enumerate(checkpoints[1:], 1):
        job = review.load(path.parent / "JOB.json")
        feedback = Path(job["prompt"])
        bind(feedback, prior["prompt_sha256"])
        if job["prompt_sha256"] != prior["prompt_sha256"]:
            raise ValueError("prior prompt does not match worker and job")
        help_records.append({"path": str(feedback), "sha256": prior["prompt_sha256"],
                             "native_ordinal": ordinal, "help_kind": (
                                 "deterministic objective verifier" if ordinal == 1 else
                                 "actual measured paid semantic guidance" if ordinal == 2 else
                                 "supplemental automatic contained CI diagnostic, zero paid guidance")})
    paid = terminal["prior_paid_guidance"]
    paid_prompt = Path(help_records[1]["path"])
    record = review.load(paid_prompt.parent / "measurement.json")
    events = [json.loads(line) for line in (paid_prompt.parent / "events.jsonl").read_text().splitlines()]
    completed = [e["usage"] for e in events if e.get("type") == "turn.completed"]
    if (paid != plan["prior_paid_guidance"] or paid["paid_model_calls"] != 1
            or paid["usage"]["output_tokens"] != 1128
            or record["execution"]["wall_s"] != paid["measured_wall_s"] or len(completed) != 1
            or any(completed[0].get(key) != paid["usage"][key] for key in
                   ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"))):
        raise ValueError("historic paid cost does not match measured turn")
    row = plan["row"]
    if row["case"] != "TU-GR-1" or row["backend"] != "gpu" or row["thinking"] or row["profile"] != "off-common-on-sampling":
        raise ValueError("review candidate is not the actual GPU TU OFF arm")
    structural = {
        "rc": 0, "candidate_patch_sha256": PATCH, "oracle_sha256": sources[str(ORACLE / "oracle.py")],
        "oracle_manifest_sha256": V3_MANIFEST, "acceptance_version": "TU V3",
        "scope": "contained deterministic checker receipt only",
    }
    projected = {
        "id": UNIT, "case": row["case"], "backend": row["backend"], "slot": row["slot"],
        "thinking": row["thinking"], "profile": row["profile"], "sampling": row["sampling"],
        "status": terminal["status"], "worker_status": receipt["status"],
        "terminal_at": terminal["terminal_at"], "session": receipt["session"],
        "changed_files": receipt["changed_files"], "patch_sha256": PATCH,
        "outside_scope": receipt["outside_scope"], "unsafe_paths": receipt["unsafe_paths"],
        "generation_observed": receipt["generated_observed"],
        "model_wall_s": receipt["ended_at"] - receipt["started_at"],
        "native_ordinal": 2, "auto_ci_turns": 2, "original_verdict": terminal["original_verdict"],
        "native_lineage": [{"attempt": i, "generated": part["generated"], "charged": part["charged"]}
                           for i, part in enumerate(lineage)],
        "projection_sources": sources, "actual_prior_feedback": help_records,
        "prior_measured_paid_guidance": paid, "oracle": structural,
    }
    output = HERE / "projections" / UNIT
    (output / "independent").mkdir(parents=True)
    shutil.copy2(patch, output / "independent/candidate.patch")
    review.write(output / "RESULT.json", projected)
    review.write(output / "STRUCTURAL-RECEIPT.json", structural)
    print(json.dumps({"result": str(output / "RESULT.json"), "patch": PATCH, "model_calls": 0}))


if __name__ == "__main__":
    main()
