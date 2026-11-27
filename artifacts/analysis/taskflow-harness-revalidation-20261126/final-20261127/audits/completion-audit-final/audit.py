#!/usr/bin/env python3
"""Bind final canary verdicts and accounting without executing candidates."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT_LANE = ROOT.with_name("ws58-a3b-finish-20261126")
COVERAGE = ROOT / "coverage"
REGISTRY = ROOT / "quality-assessments/registry"
EXPORT = COVERAGE / "final-export"
PAID = COVERAGE / "paid-call-accounting/snapshot-final-40"
SERVING = COVERAGE / "persistent-serving/runs/final-01"
FINAL = ROOT / "performance/multi-epoch-v3/snapshot-persistent-final-01/REPORT.json"

CPU_W66 = "cpu-DS41-W-66-off-recommended-numa-resume-1-boundary"
TU_ON = "gpu-TU-GR-1-on-coding-paid-2"
MM_OFF = "gpu-MM-5-off-common-on-sampling-v4-objective-2"
MM_EXTRA = "gpu-MM-5-off-common-on-sampling-v4-mechanical-3"


def read(path):
    return json.loads(path.read_bytes())


def bind(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is not None:
        assert digest == expected, (path, expected, digest)
    return {"path": str(path), "sha256": digest}


def ref(value):
    return bind(Path(value["path"]), value["sha256"])


def registry(id, decision, attempt):
    path = REGISTRY / f"{id}.json"
    value = read(path)
    assert value["decision"] == decision, path
    assert value["candidate_patch_sha256"] == attempt["patch_sha256"], path
    if id != MM_EXTRA:
        assert attempt["acceptance"]["state"] == decision, id
        ref(attempt["acceptance"]["evidence"])
    return {
        "owner": bind(path),
        "patch_sha256": value["candidate_patch_sha256"],
        "source_review": bind(Path(value["source_review"]), value["source_review_sha256"]),
        "snapshot_raw_status": attempt["status"],
        "snapshot_owner_state": attempt["acceptance"]["state"],
        "final_owner_state": decision,
    }


def served():
    ready = read(SERVING / "READY.json")
    pre = read(SERVING / "PRE-CLOSE.json")
    cleanup = read(SERVING / "CLEANUP.json")
    assert set(pre["native_slots"]) == {"cpu", "gpu"}
    slots = 0
    for rows in pre["native_slots"].values():
        assert [row["id"] for row in rows] == [0, 1, 2, 3]
        assert all(row["n_ctx"] == 131072 and not row["is_processing"] for row in rows)
        slots += len(rows)
    assert set(pre["slot_locks"]) == {f"{route}-{index}" for route in ("cpu", "gpu") for index in range(4)}
    assert cleanup["kfd_pids"] == []
    assert set(cleanup["servers"]) == {"cpu", "gpu"}
    for row in cleanup["servers"].values():
        assert row["dead_verified"] and row["rc"] == 0
    process = ROOT / "completion-audit-final/PROCESS-OBSERVATION.txt"
    ids = {int(line.split()[0]) for line in process.read_text().splitlines()[1:]}
    assert ids == {ready["holder"]["ppid"]} == {89061}
    return {
        "ready": bind(SERVING / "READY.json"),
        "pre_close": bind(SERVING / "PRE-CLOSE.json"),
        "cleanup": bind(SERVING / "CLEANUP.json"),
        "idle_slots": slots,
        "exclusive_slot_locks": len(pre["slot_locks"]),
        "owned_servers": cleanup["servers"],
        "kfd_pids_after_close": cleanup["kfd_pids"],
        "preserved_codex_app_server_pid": ready["holder"]["ppid"],
        "process_observation": bind(process),
    }


def performance(final):
    summary_path = EXPORT / "files-v2/SUMMARY.json"
    summary = read(summary_path)
    assert Path(summary["source"]) == FINAL
    performance_binding = bind(FINAL, summary["source_sha256"])
    assert len(final["epochs"]) == summary["epochs"] == 18
    assert len(final["attempts"]) == summary["tasks"] == 62
    assert final["rollup"]["forwarded_receipts"] == summary["requests"] == 1061
    assert final["accepted_count"] == summary["accepted_artifact_variants"] == 9
    assert not final["read_warnings"]
    assert final["unreceipted_archives"] == 0
    files = {}
    validation_path = EXPORT / "CSV-FORMAT-VALIDATION.json"
    for validation in read(validation_path):
        name = validation["file"]
        raw = EXPORT / "files" / name
        delivery = EXPORT / "files-v2" / name
        with raw.open(newline="") as first, delivery.open(newline="") as second:
            rows = list(csv.DictReader(second))
            assert rows == list(csv.DictReader(first))
        if name == "REQUESTS.csv":
            ids = {row["receipt_sha256"] for row in rows}
            assert all(len(value) == 64 for value in ids)
            assert len(ids) == len(rows) == 1061
        else:
            assert name == "TASKS.csv"
            assert len({(row["epoch"], row["id"]) for row in rows}) == len(rows) == 62
        files[name] = {"rows": len(rows), **bind(delivery, validation["sha256"])}
    return {
        "authoritative_snapshot": performance_binding,
        "summary": bind(summary_path),
        "csv_transformation_receipt": bind(validation_path),
        "csv_files": files,
        "epochs": summary["epochs"],
        "attempts": summary["tasks"],
        "unique_forwarded_receipts": summary["requests"],
        "accepted_artifact_variants": summary["accepted_artifact_variants"],
        "unreceipted_archives": final["unreceipted_archives"],
        "read_warning_count": len(final["read_warnings"]),
        "snapshot_owner_state_counts": dict(Counter(row["acceptance"]["state"] for row in final["attempts"])),
        "native_reasoning_count": final["rollup"]["tokens"]["reasoning_output"],
    }


def paid_accounting():
    path = PAID / "ACCOUNTING.json"
    value = read(path)
    seal_path = PAID / "FINAL-SEAL.json"
    seal = read(seal_path)
    addendum_path = PAID / "OWNER-QUALITY-ADDENDUM.json"
    addendum = read(addendum_path)
    assert addendum["billed_vectors_unchanged"] and not addendum["model_api_calls"]
    assert seal["unique_terminal_executions"] == addendum["billed_execution_count_unchanged"] == 40
    assert seal["implementation_calls"] == 8 and seal["assistance_review_calls"] == 32
    assert len({item["call_id"] for item in value["calls"]}) == len(value["calls"]) == 40
    assert Counter(item["role"] for item in value["calls"]) == {
        "main-only-implementation": 8, "final-acceptance": 22, "guidance": 5, "initial-diagnosis": 5,
    }
    bind(path, addendum["immutable_accounting_sha256"])
    ref(addendum["owner_registry_row"])
    main = COVERAGE / "main-only-accounting/ACCOUNTING.json"
    main_value = read(main)
    return {
        "ledger": bind(path),
        "ledger_seal": bind(seal_path),
        "ledger_cpu_quality_addendum": bind(addendum_path),
        "call_roles": dict(Counter(item["role"] for item in value["calls"])),
        "global_vector": value["global_unique_observed_execution_vectors"],
        "detailed_main_only": bind(main),
        "detailed_main_totals": main_value["totals"],
    }


def outcomes(attempts):
    cases = {id: registry(id, decision, attempts[id]) for id, decision in (
        (CPU_W66, "accepted"), (TU_ON, "rejected"), (MM_OFF, "accepted"), (MM_EXTRA, "rejected"),
    )}
    cpu = read(REGISTRY / f"{CPU_W66}.json")
    assert cpu["known_chain_generation"] == 5663 and cpu["unknown_generation_receipts"] == 1
    cases[CPU_W66]["known_generation"] = cpu["known_chain_generation"]
    cases[CPU_W66]["unknown_generation_receipts"] = cpu["unknown_generation_receipts"]
    cases[CPU_W66]["cost_qualification"] = bind(Path(cpu["cost_addendum"]), cpu["cost_addendum_sha256"])

    raw = COVERAGE / "persistent-callback-admission-v2/runs/tu-on-paid-01/units" / TU_ON / "RESULT.json"
    tu_raw = read(raw)
    assert tu_raw["current_local_tokens"] == 2787 and tu_raw["known_combined_local_tokens"] == 25576
    tu_grade = COVERAGE / "gpu-tu-on-paid-final-review/grade-v4/RESULT.json"
    tu_grade_value = read(tu_grade)
    assert tu_grade_value["candidate_patch_sha256"] == cases[TU_ON]["patch_sha256"]
    assert tu_grade_value["rc"] == 1 and "skipped" in tu_grade_value["first_diagnostic"][0]
    cases[TU_ON]["raw_terminal"] = bind(raw)
    cases[TU_ON]["qualified_grade"] = bind(tu_grade)
    cases[TU_ON]["current_local_tokens"] = tu_raw["current_local_tokens"]
    cases[TU_ON]["known_combined_local_tokens"] = tu_raw["known_combined_local_tokens"]
    for id, advisory in ((TU_ON, "REJECT"), (MM_OFF, "ACCEPT")):
        review = read(Path(cases[id]["source_review"]["path"]))
        assert review["semantic_review_advisory"] == advisory
        cases[id]["paid_review"] = {key: review[key] for key in ("execution", "usage", "semantic_review_advisory")}

    mm_addendum = EXPORT / "OWNER-QUALITY-FINAL-ADDENDUM.json"
    mm = read(mm_addendum)
    assert mm["id"] == MM_EXTRA and mm["accepted_artifact_variant_count_unchanged"] == 9
    assert mm["candidate_patch_sha256"] != cases[MM_OFF]["patch_sha256"]
    assert mm["candidate_patch_sha256"] == cases[MM_EXTRA]["patch_sha256"]
    assert mm["raw_snapshot_acceptance"] == cases[MM_EXTRA]["snapshot_owner_state"]
    bind(Path(mm["owner_receipt"]), mm["owner_receipt_sha256"])
    mm_grade = read(Path(cases[MM_EXTRA]["source_review"]["path"]))
    assert mm_grade["rc"] == 1
    assert mm_grade["checks"]["brief_environment_control"]["status"] == "pass"
    assert mm_grade["checks"]["unchanged_original_and_v2_feasible"]["status"] == "pass"
    assert mm_grade["checks"]["additional_infeasible_cap_robustness"]["status"] == "fail"
    cases[MM_EXTRA]["post_snapshot_owner_addendum"] = bind(mm_addendum)
    cases[MM_EXTRA]["qualified_scope_checks"] = mm_grade["checks"]
    return cases


def main():
    previous = ROOT / "completion-audit/AUDIT.json"
    earlier = read(previous)
    baseline = {}
    assert len(earlier["requirements"]) == 12
    for key, value in earlier["requirements"].items():
        baseline[key] = [ref(item) for item in value["evidence"]]
    final = read(FINAL)
    attempts = {item["id"]: item for item in final["attempts"]}

    checker = COVERAGE / "canonical-checker-validation/RECEIPT.json"
    qualified = read(checker)
    assert qualified["exit_code"] == qualified["git_diff_check"]["exit_code"] == 0
    assert qualified["tests_passed"] == 47
    tested = [bind(GIT_LANE / rel, sha) for rel, sha in qualified["sha256_of_tested_files"].items()]
    assert len(tested) == 4
    print(json.dumps({
        "schema": "a3b.closed-completion-audit.v1",
        "new_tests_measurements_models_or_api_calls": 0,
        "earlier_requirements": bind(previous),
        "requirement_evidence_rechecked": baseline,
        "canonical_checkers": {"receipt": bind(checker), "tests_passed": 47, "tested_bytes": tested},
        "serving": served(),
        "native_performance": performance(final),
        "final_owner_outcomes": outcomes(attempts),
        "paid_accounting": paid_accounting(),
        "feedback_audit": bind(ROOT / "feedback-final-audit/REPORT.json"),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
