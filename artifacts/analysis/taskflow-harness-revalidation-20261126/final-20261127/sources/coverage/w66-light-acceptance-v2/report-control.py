"""Exercise the existing comparison reporter with disposable staged evidence."""
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import review


def main():
    root = review.HERE
    mode = "gpu-OFF-off-common-light"
    seal, original_run = review.verify(mode)
    original_plan = review.load(original_run / "plan.json")
    with TemporaryDirectory(prefix="w66-report-scope-control-", dir=root) as scratch:
        private = Path(scratch)
        (private / "cases").symlink_to(review.CASE_ROOT, target_is_directory=True)
        run = private / "runs" / review.CASE / "guidance-1"
        run.mkdir(parents=True)
        shutil.copytree(original_run / "lane", run / "lane")
        review.write(run / "plan.json", original_plan)
        review.write(run / "execution.json", {"control_only": True, "rc": 0, "wall_s": 0.0})
        (run / "events.jsonl").write_text(json.dumps({"type": "thread.started", "thread_id": "fixture-only"}) + "\n")
        _, measure = review.modules(private, seal["evidence"])
        clean = measure.report(run)
        assert clean["path_scope_pass"] and clean["changed_by_strong_turn"] == []
        assert clean["final_changes"] == [review.SOURCE]
        evidence = run / "lane" / review.ARTIFACTS["patch"]
        evidence.chmod(0o644)
        evidence.write_bytes(evidence.read_bytes() + b"\n")
        tampered = measure.report(run)
        assert not tampered["path_scope_pass"]
        assert tampered["out_of_scope_changes"] == [review.ARTIFACTS["patch"]]
        assert tampered["changed_by_strong_turn"] == [review.ARTIFACTS["patch"]]
    review.write(root / "REPORT-CONTROL.json", {
        "unchanged_evidence_is_expected_input": clean["path_scope_pass"],
        "candidate_still_only_source_output": clean["final_changes"],
        "modified_evidence_is_rejected": not tampered["path_scope_pass"],
        "modified_evidence_path": tampered["out_of_scope_changes"][0],
        "input_source_comparison_seal_sha256": review.sha(review.review_root(mode) / "SEAL.json"),
        "model_calls": 0, "control_execution_is_not_paid_measurement": True,
    })


if __name__ == "__main__":
    main()
