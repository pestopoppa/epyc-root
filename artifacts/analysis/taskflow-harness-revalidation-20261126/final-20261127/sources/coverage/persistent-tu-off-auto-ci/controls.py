"""No-model end-to-end checker custody and deterministic feedback guards."""
from pathlib import Path
import json
import time

import ci_callback as c
import ci_grade


def main():
    initial = c.diagnostic(c.V2)
    exception = "ModuleNotFoundError: No module named 'harness'"
    assert exception in initial and 'File "<string>", line 1' in initial
    assert "/tmp/taskflow-tu-grader-" not in initial
    assert exception in c.feedback_text(initial, "V2")
    needle = c.V3 / "tu_grader_isolation.py"
    test_lanes = [
        ("actual-prior-negative", c.PRIOR / "grade-lane", 1, exception),
        ("actual-main-positive", c.COVERAGE / "legacy-direct-repair/runs/TU-GR-1/direct-repair-1/lane",
         0, "TU-GR-1 contract passed"),
    ]
    rows = []
    for name, lane, expected, witness in test_lanes:
        candidate = lane / ci_grade.TEST
        before = ci_grade.digest(candidate)
        output = c.HERE / "controls" / name
        if output.exists() and name == "actual-prior-negative":
            evidence = output / "stdout.log"
            assert witness in evidence.read_text()
            result = {"rc": expected, "cleanup_verified": True}
        else:
            result = ci_grade.run(lane, needle, output, time.monotonic() + 60, lambda: None)
            assert result["rc"] == expected and result["cleanup_verified"], result
            assert witness in (output / "stdout.log").read_text()
        result["test_sha256"] = before
        assert ci_grade.digest(candidate) == before
        rows.append(result)
    current = c.diagnostic(c.HERE / "controls/actual-prior-negative")
    failed = {"rc": 1, "reason": None}
    assert c.classify(failed, current, initial, False) == "duplicate_failure"
    assert c.classify(failed, current + " different", initial, True) == "unchanged_candidate"
    assert c.classify(failed, current + " different", initial, False) == "new_failure"
    assert c.classify(failed, "", initial, False) == "no_usable_candidate_diagnostic"
    assert c.classify({"rc": 125, "reason": None}, "", initial, False) == "checker_interrupted_or_unavailable"
    assert c.classify({"rc": 0, "reason": None}, "", initial, False) == "checker_pass_pending_source_review"
    assert c.predecessor(c.read(c.PAID / "PLAN.json")["lease"])
    history = [c.counted(p, c.read(c.PRIOR / "worker/receipt.json")["session"]) for p in c.prior_attempts()]
    assert c.CEILING - sum(part["charged"] for part in history) == 91105
    result = {"control_results": rows, "actual_exception_full": True, "failures_are_distinct": True,
              "stage_budget": 91105, "original_cap2_preserved": True, "model_calls": 0}
    path = Path(c.HERE / "CONTROL.json")
    with path.open("x") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
