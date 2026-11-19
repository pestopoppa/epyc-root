"""Versioned recovery instrument; never a replacement for a quality cell.

Install capture BEFORE constructing the REPL so its namespace binds the wrapped
native method. The caller supplies the source-written log path after archive
installation, and persists these receipts beside the existing wire receipts.
"""

import copy
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

VERSION = "epyc.cf3c.native-recovery-probe.v1"
COHORT_SHA = "14c79e10bade5909a5406b86ea72d91e44b66f830859044639b0c9c622cb5cc3"
PROBE_SEED = 195981119


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def compile_probe(cohort):
    """Use the fixed archive, with an explicit instruction, outside all 24 cells."""
    # Validate content, not merely the self-reported digest.
    payload = {k: v for k, v in cohort.items() if k != "cohort_sha256"}
    actual = sha(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if actual != COHORT_SHA or cohort.get("cohort_sha256") != COHORT_SHA:
        raise ValueError("fixed quality cohort changed")
    case = next(c for c in cohort["cases"] if c["id"] == "binding_deep_v1")
    return {
        "schema": VERSION,
        "id": "native_recovery_control_v1",
        "arm": "A1-k12",
        "seed": PROBE_SEED,
        "initial_history": copy.deepcopy(case["initial_history"]),
        "prompt": (
            "This is a recovery instrument control, separate from task grading. "
            "Before answering, execute print(peek(99999, file_path=<the registered "
            "Scripted archive full log path>, offset=0)) using the exact path "
            "supplied in context. Read the returned log, then finish with RECOVERY_DONE. "
            "Do not infer the archived text from the compressed history."
        ),
        "quality_cohort_sha256": COHORT_SHA,
        "grade_cohort": False,
    }


@contextmanager
def capture_peeks(repl_class, archive):
    """Observe native peek returns without injecting reads or changing tool output.

    Only a read of the exact source-written log containing the masked fourth
    observation is a witness. A wrong file, an error, or a partial prefix cannot
    establish recovery. This context is private to the trial subprocess.
    """
    original = repl_class._peek
    evidence = {"schema": VERSION, "log_path": None, "events": []}
    marker = archive[3]["output"]

    def observed(repl, n=500, file_path=None, offset=0):
        result = original(repl, n=n, file_path=file_path, offset=offset)
        target = evidence["log_path"]
        matched = bool(target and file_path is not None
                       and Path(file_path).resolve() == Path(target).resolve())
        evidence["events"].append({
            "source_log": matched,
            "source_log_sha256": hashlib.sha256(Path(target).read_bytes()).hexdigest()
                                 if matched else None,
            "returned_sha256": sha(result),
            "recovered_observation": matched and marker in result,
        })
        return result

    with patch.object(repl_class, "_peek", observed):
        yield evidence


def qualify(probe, trial, capture, *, server_exited, error):
    """Require custody/recovery/cost/teardown; deliberately never read task grade.

    ``trial`` is the native runner OUTCOME; its wire validation must have run.
    ``capture`` must come from capture_peeks, never from the model's answer.
    """
    native = trial.get("native_result") or {}
    receipts = native.get("policy_receipts", [])
    archive = native.get("initial_history_receipt") or {}
    archive_sha = sha(json.dumps(probe["initial_history"], sort_keys=True,
                                separators=(",", ":")))
    checks = {
        "probe_version": probe.get("schema") == capture.get("schema") == VERSION,
        "separate_control": probe.get("grade_cohort") is False
                            and probe.get("quality_cohort_sha256") == COHORT_SHA
                            and trial.get("case") == probe["id"]
                            and trial.get("arm") == probe["arm"] == "A1-k12"
                            and trial.get("seed") == probe["seed"] == PROBE_SEED,
        "active_first_generation": bool(receipts and receipts[0].get("active") is True
                                         and receipts[0].get("selected_history_sha256")),
        "source_archive": archive.get("observations") == 10
                          and archive.get("archive_sha256") == archive_sha
                          and bool(archive.get("verbatim_sha256")),
        "native_recovery": native.get("tool_calls", {}).get("retrieval", 0) > 0
                           and any(e.get("source_log") is True
                                   and e.get("recovered_observation") is True
                                   and e.get("source_log_sha256") == archive.get("verbatim_sha256")
                                   for e in capture.get("events", [])),
        "observed": trial.get("status") in {"graded", "grade_unavailable", "NA"}
                    and native.get("wire_requests", 0) > 0,
        "complete_cost": trial.get("usage_complete", {}).get("total_tokens") is True,
        "teardown": trial.get("child_exited") is True and server_exited is True,
        "no_error": error is None,
    }
    return {"schema": VERSION, "checks": checks, "qualified": all(checks.values()),
            "quality_cells_observed": 0, "adoption_claim": False}
