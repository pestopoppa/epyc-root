"""Project exact GPU TU ON objective1 and contained V3 failure for paid diagnosis."""
from pathlib import Path
import json
import shutil

import review

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent
ROOT = COVERAGE.parent
NATIVE = COVERAGE / "persistent-callback-admission-v2"
EPOCH = NATIVE / "runs/tu-on-retry-01"
UNIT = "gpu-TU-GR-1-on-coding-v2-objective-1"
GRADED = ROOT / "source-review-gpu-tu-on-retry"
GRADE = GRADED / "grades" / UNIT / "RESULT.json"
UNIT_PATH = EPOCH / "units" / UNIT
PATCH = "0d35e2f372c19d81486d9eca64ebb2391e76c09d899446525004f35e37fe04a3"
V3 = "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b"
BOUND = {
    EPOCH / "PLAN.json": "68d74d1d187b3603c225c20f14ecae229c561b9d51f60cda9131412a213ae471",
    EPOCH / "APPROVAL.json": "92fe3726014f815cb75a2fc4a9ed43f7063caa77bce06801e09f530aaccf0883",
    NATIVE / "RUNNER-SEAL.json": "652ea6d728c0c9ee274d74dca77ba2f7e2c52acfde3225df4fe0b566e4aa753f",
    GRADE: "66c8a77eab20e798737cb887ee8f112263b178bfb569ebf196be5479ef1e5ac5",
    GRADED / "REVIEW.json": "5026eaa5693beea1fe82035325f2cc0fba7520f517e49b184d15a5e38e775c07",
    ROOT / "tu-oracle-v3/SOURCE-CONTROL.sha256": V3,
}


def main():
    review.source_lock()
    sources = {}

    def bind(path, expected=None):
        content = review.sha(path)
        if expected is not None and content != expected:
            raise ValueError(f"bound source changed: {path}")
        sources[str(path)] = content

    for path, expected in BOUND.items():
        bind(path, expected)
    source = review.load(GRADED / "REVIEW.json")["rows"]["TU-GR-1"]
    grade = review.load(GRADE)
    if (grade["rc"] != 1 or grade["candidate_patch_sha256"] != PATCH
            or grade["oracle_manifest_sha256"] != V3 or
            "wrong-access-errno" not in grade["diagnostic"][0]):
        raise ValueError("candidate lacks the expected actual V3 failure")
    for kind in ("stdout", "stderr"):
        bind(GRADE.parent / (kind + ".log"), grade[kind + "_sha256"])
    plan = review.load(EPOCH / "PLAN.json")
    entry, = plan["jobs"]
    row = entry["row"]
    if (entry["id"] != UNIT or row["case"] != "TU-GR-1" or row["backend"] != "gpu"
            or row["profile"] != "on-coding" or row["thinking"] is not True
            or entry["source_guidance"]["paid_model_calls"] != 0):
        raise ValueError("expected exact objective1 arm with no paid guidance")
    for name, expected in entry["sha256"].items():
        bind(Path(name), expected)

    unit = UNIT_PATH
    worker = unit / "worker"
    bind(unit / "CALLBACK-RESULT.json", source["sha256"]["callback"])
    bind(worker / "receipt.json", source["sha256"]["worker"])
    receipt = review.load(worker / "receipt.json")
    terminal = review.load(unit / "CALLBACK-RESULT.json")
    patch = worker / "candidate/candidate.patch"
    bind(patch, PATCH)
    bind(unit / "JOB.json", receipt["job_sha256"])
    bind(worker / "session.json")
    job = review.load(unit / "JOB.json")
    resume = job["resume"]
    previous = Path(resume["prior_run"])
    bind(previous / "receipt.json", resume["receipt_sha256"])
    bind(previous / "session.json", resume["session_sha256"])
    previous_record = review.load(previous / "receipt.json")
    if (receipt["status"] != "review" or terminal["status"] != "awaiting_source_review"
            or not terminal["cleanup"]["removed_verified"] or not terminal["same_session"]
            or receipt["session"] != previous_record["session"]
            or receipt["resume"] != resume or receipt["patch_sha256"] != PATCH
            or receipt["changed_files"] != source["changed_files"]
            or receipt["outside_scope"] or receipt["unsafe_paths"] or receipt["generated_observed"] != 9118):
        raise ValueError("unexpected actual candidate/custody")
    feedback = unit / "FEEDBACK.txt"
    bind(feedback, receipt["prompt_sha256"])
    if (str(feedback) != job["prompt"] or job["prompt_sha256"] != receipt["prompt_sha256"]
            or feedback.read_text() != entry["feedback"]["text"]):
        raise ValueError("objective feedback differs from authorized exact text")
    structural = {"rc": grade["rc"], "candidate_patch_sha256": PATCH,
                  "oracle_sha256": grade["oracle_sha256"], "oracle_manifest_sha256": V3,
                  "acceptance_version": "TU V3", "observed_failure": grade["diagnostic"],
                  "scope": "actual contained checker outcome for this candidate"}
    result = {"id": UNIT, "case": row["case"], "backend": "gpu", "slot": row["slot"], "thinking": True,
              "profile": row["profile"], "sampling": row["sampling"], "status": terminal["status"],
              "terminal_at": terminal["terminal_at"], "session": receipt["session"],
              "changed_files": receipt["changed_files"], "patch_sha256": PATCH, "outside_scope": [],
              "unsafe_paths": [], "generation_observed": receipt["generated_observed"],
              "model_wall_s": receipt["ended_at"] - receipt["started_at"], "native_ordinal": 1,
              "projection_sources": sources, "oracle": structural,
              "actual_prior_feedback": [{"native_ordinal": 1, "sha256": receipt["prompt_sha256"],
                                         "path": str(feedback), "help_kind": "deterministic objective verifier"}]}
    output = HERE / "projections" / UNIT
    (output / "independent").mkdir(parents=True)
    shutil.copy2(patch, output / "independent/candidate.patch")
    review.write(output / "RESULT.json", result)
    review.write(output / "STRUCTURAL-RECEIPT.json", structural)
    print(json.dumps({"result": str(output / "RESULT.json"), "model_calls": 0}))


if __name__ == "__main__":
    main()
