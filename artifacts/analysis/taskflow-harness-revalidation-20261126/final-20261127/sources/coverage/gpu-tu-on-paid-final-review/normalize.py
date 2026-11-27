"""Stage the actual terminal GPU TU ON paid2 for a fresh, independent final review."""
import json
from pathlib import Path
import shutil

import grade_saved as checked
import review


def main():
    review.source_lock()
    candidate, _, _, _ = checked.check()
    if checked.read(checked.CANDIDATE) != candidate:
        raise RuntimeError("exact candidate source review differs")
    grade = checked.read(checked.GRADE)
    if (grade["id"] != checked.ID or grade["rc"] not in (0, 1)
            or grade["candidate_patch_sha256"] != candidate["candidate_patch_sha256"]
            or grade["candidate_json_sha256"] != checked.digest(checked.CANDIDATE)
            or grade["oracle_sha256"] != candidate["verifier_sha256"]
            or grade["checker_sha256"] != candidate["v4_checker_sha256"]
            or grade["v4_qualification_sha256"] != candidate["v4_qualification_sha256"]):
        raise RuntimeError("actual owner V4 grade does not bind the paid2 candidate")
    sources = dict(candidate["input_sha256"])

    def bind(path, expected=None):
        found = checked.digest(path)
        if expected is not None and found != expected:
            raise RuntimeError(f"review source changed: {path}")
        sources[str(path)] = found
        return found

    bind(checked.CANDIDATE, grade["candidate_json_sha256"])
    bind(checked.GRADE)
    bind(Path(grade["source_safety"]), grade["source_safety_sha256"])
    for stream in ("stdout", "stderr"):
        bind(checked.GRADE.parent / (stream + ".log"), grade[stream + "_sha256"])
    row, = checked.read(checked.NATIVE / "PLAN.json")["jobs"]
    prior_worker = Path(row["feedback"]["prior_attempt"])
    prior = checked.read(prior_worker / "receipt.json")
    terminal = checked.read(checked.UNIT / "CALLBACK-RESULT.json")
    receipt = checked.read(checked.WORKER / "receipt.json")
    if terminal["source_guidance"] != row["source_guidance"] or row["source_guidance"]["paid_model_calls"] != 1:
        raise RuntimeError("paid guidance accounting does not match the actual terminal row")
    prompts = [
        (prior_worker.parent / "FEEDBACK.txt", prior["prompt_sha256"],
         "deterministic objective verifier with zero paid semantic guidance"),
        (Path(row["feedback"]["feedback"]), receipt["prompt_sha256"],
         "one measured paid source guidance"),
    ]
    replays = [{"path": str(path), "sha256": bind(path, expected), "native_ordinal": ordinal,
                "help_kind": kind} for ordinal, (path, expected, kind) in enumerate(prompts, 1)]
    structural = {"rc": grade["rc"], "candidate_patch_sha256": candidate["candidate_patch_sha256"],
                  "oracle_sha256": grade["oracle_sha256"], "acceptance_version": "TU V4",
                  "qualification_sha256": grade["v4_qualification_sha256"],
                  "outcome": grade["first_diagnostic"],
                  "scope": "actual contained checker result for the reviewed bytes"}
    job = row["row"]
    projected = {
        "id": checked.ID, "case": "TU-GR-1", "backend": "gpu", "slot": job["slot"],
        "profile": job["profile"], "thinking": job["thinking"], "sampling": job["sampling"],
        "status": terminal["status"], "terminal_at": terminal["terminal_at"], "session": receipt["session"],
        "changed_files": receipt["changed_files"], "outside_scope": receipt["outside_scope"],
        "unsafe_paths": receipt["unsafe_paths"], "patch_sha256": candidate["candidate_patch_sha256"],
        "generation_observed": receipt["generated_observed"],
        "model_wall_s": receipt["ended_at"] - receipt["started_at"],
        "oracle": structural, "actual_prior_feedback": replays, "projection_sources": sources,
        "native_ordinal": 2, "prior_measured_paid_guidance": row["source_guidance"],
    }
    output = checked.HERE / "projections" / checked.ID
    (output / "independent").mkdir(parents=True)
    shutil.copy2(candidate["patch"], output / "independent/candidate.patch")
    review.write(output / "RESULT.json", projected)
    review.write(output / "STRUCTURAL-RECEIPT.json", structural)
    staged = review.stage(output / "RESULT.json", "final-acceptance", 2, output / "STRUCTURAL-RECEIPT.json")
    reviewed = review.verify(Path(staged["root"]))
    if reviewed["prior_measured_paid_guidance"] != row["source_guidance"]:
        raise RuntimeError("review plan lost actual prior measured policy")
    print(json.dumps({**staged, "native_v4_rc": grade["rc"], "model_calls": 0}))


if __name__ == "__main__":
    main()
