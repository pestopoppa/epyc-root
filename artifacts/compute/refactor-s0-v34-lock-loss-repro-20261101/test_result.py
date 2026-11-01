"""Verify the captured S0 v33 lock-loss reproducer receipt."""
import json
from pathlib import Path


def test_v33_false_lock_loss_has_live_owner_fd_evidence():
    root = Path(__file__).resolve().parent
    result = json.loads((root / "run-20261101T0915Z/RESULT.json").read_text())
    assert result["scope"] == "ACTUAL_UNCHANGED_V33_PREDICATE_PRIVATE_FLOCK_CHURN"
    assert result["iterations"] > 0
    failures = result["failures_with_still_held_real_fd_rows"]
    loss = [entry for entry in failures if entry["old_refusal"] == "lock lost"]
    assert loss, "legacy predicate did not reproduce RuntimeError: lock lost"
    for entry in loss:
        assert set(entry["actual_owner_fd_locks_after_refusal"]) == {"GLOBAL", "build"}
        for lock in entry["actual_owner_fd_locks_after_refusal"].values():
            assert "FLOCK ADVISORY WRITE" in lock["kernel_row"]
    assert result["churn_rc"] == 0 and result["churn_drained"]
    assert set(result["target_owner_held_after"]) == {"GLOBAL", "build"}
    assert (root / "run-20261101T0915Z/launcher.log").read_text().count("regions ['q3']") == 1


if __name__ == "__main__":
    test_v33_false_lock_loss_has_live_owner_fd_evidence()
    print("PASS: v33 false lock-loss reproduced; v34 owner-FD evidence retained")
