#!/usr/bin/env python3
"""Verify provenance and consumed verifier feedback from saved receipts."""
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT.with_name("ws58-a3b-frozen-revalidation-20261126")
ORIGINAL = FROZEN / "quality-runs/cache-safe-01/units"
COVERAGE = ROOT / "coverage"


def read(path):
    return json.loads(path.read_bytes())


def record(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError(f"hash mismatch at {path}: {digest} != {expected}")
    return {"path": str(path), "sha256": digest}


def verify_ref(ref):
    return record(Path(ref["path"]), ref["sha256"])


def session_path(unit):
    for relative in ("OPEN-CODE-SESSION.json", "worker/session.json"):
        path = unit / relative
        if path.is_file():
            return path
    raise ValueError(f"missing session export at {unit}")


def user_content(request):
    for message in request["messages"]:
        if message["role"] != "user":
            continue
        content = message["content"]
        if isinstance(content, str):
            yield content
        else:
            for part in content:
                if part.get("type") == "text":
                    yield part["text"]


def consumed(unit, prompt="PROMPT.md", absent=None):
    result = unit / "RESULT.json"
    session = session_path(unit)
    prompt = unit / prompt
    exact = prompt.read_text().strip()
    users = [m for m in read(session)["messages"] if m["type"] == "user"]
    matching = [m for m in users if m["text"].strip() == exact]
    assert len(matching) == 1, unit
    if absent is not None:
        assert all(not absent.search(m["text"]) for m in users), unit

    wire = session.parent / "wire"
    ledger = wire / "requests.jsonl"
    with ledger.open() as stream:
        for line in stream:
            row = json.loads(line)
            if not row.get("forwarded_at") or not row.get("body_ref"):
                continue
            archive = wire / row["body_ref"]
            with gzip.open(archive, "rt") as stream_body:
                messages = list(user_content(json.load(stream_body)))
            if any(exact == m.strip() for m in messages):
                if absent is not None:
                    assert all(not absent.search(m) for m in messages), archive
                return {
                    "unit": unit.name,
                    "result": record(result),
                    "prompt": record(prompt),
                    "session": record(session),
                    "saved_user_message_id": matching[0]["id"],
                    "saved_user_message_time": matching[0]["time"],
                    "wire_ledger": record(ledger),
                    "forwarded_request": record(archive),
                    "wire_sequence": row["seq"],
                    "forwarded_at": row["forwarded_at"],
                }
    raise ValueError(f"saved prompt absent from forwarded wire at {unit}")


def result_counter(unit):
    path = unit / "RESULT.json"
    row = read(path)
    return {
        "source": record(path),
        "raw_status": row["status"],
        "raw_observed_generated_tokens": row["generation_observed"],
        "raw_unknown_generation_requests": row["generation_unknown_requests"],
        "model_wall_s": row["model_wall_s"],
    }


def paid(path):
    row = read(path)
    return {
        "source": record(path),
        "cli_wall_s": row["execution"]["wall_s"],
        "usage": row["usage"],
        "advisory": row["semantic_review_advisory"],
    }


def unit(suffix):
    return COVERAGE / suffix


def original_consumption():
    earlier = COVERAGE / "feedback-confound-audit/CONSUMED-FEEDBACK.json"
    findings = {}
    for row in read(earlier)["rows"]:
        name = row["unit"]
        evidence = consumed(ORIGINAL / name)
        assert evidence["result"]["sha256"] == row["result_sha256"]
        assert evidence["prompt"]["sha256"] == row["prompt_sha256"]
        assert evidence["session"]["sha256"] == row["session_export_sha256"]
        assert evidence["saved_user_message_id"] == row["saved_user_message_id"]
        assert evidence["saved_user_message_time"] == row["saved_user_message_time"]
        evidence["prior_audit_classification"] = row["classification"]
        evidence["feedback"] = record(Path(row["feedback_path"]), row["feedback_sha256"])
        findings[name] = evidence
    assert len(findings) == 4
    return earlier, findings


def paw(findings):
    historical = ORIGINAL / "gpu-PAW-5-off-recommended-guidance-1"
    false_text = "candidate has no pinned source"
    absent = re.compile(re.escape(false_text), re.IGNORECASE)
    assert absent.search((historical / "PROMPT.md").read_text())

    clean1 = unit("persistent-callback/runs/paw-clean-01/units/gpu-PAW-5-off-recommended-clean-guidance-1")
    clean2 = unit("persistent-callback-admission-v2/runs/paw-clean-paid-01/units/gpu-PAW-5-off-recommended-clean-paid-2")
    neutral = consumed(clean1, absent=absent)
    followup = consumed(clean2, absent=absent)
    prior = ROOT / "coverage/paw-clean-replay/PRIOR-STATE.json"
    state = read(prior)
    original = Path(state["source_unit"])
    first_resume = read(clean1 / "RESULT.json")["resume"]
    second_resume = read(clean2 / "RESULT.json")["resume"]
    assert original == ORIGINAL / "gpu-PAW-5-off-recommended"
    assert state["source_result_sha256"] == first_resume["prior_result_sha256"]
    assert state["session_export_sha256"] == first_resume["prior_session_sha256"]
    assert first_resume["main_model_feedback_calls"] == 0
    assert first_resume["substantive_guidance_rounds"] == 0
    assert first_resume["feedback_sha256"] == neutral["prompt"]["sha256"]
    assert Path(second_resume["prior"]) == clean1
    assert second_resume["prior_result_sha256"] == neutral["result"]["sha256"]
    assert second_resume["prior_session_sha256"] == neutral["session"]["sha256"]
    assert second_resume["feedback_sha256"] == followup["prompt"]["sha256"]
    assert second_resume["main_model_feedback_calls"] == 1

    history = ROOT / "coverage/paw-clean-review-v3/HISTORY-INPUTS.json"
    bindings = [record(Path(p), sha) for p, sha in read(history)["expected_sha256"].items()]
    registry = ROOT / "quality-assessments/registry/gpu-PAW-5-off-recommended-clean-paid-2.json"
    owner = read(registry)
    assert owner["decision"] == "rejected"
    assert owner["candidate_patch_sha256"] == read(clean2 / "RESULT.json")["patch_sha256"]
    record(Path(owner["source_review"]), owner["source_review_sha256"])

    comparison = ROOT / "quality-assessments/registry/gpu-PAW-5-off-recommended-guidance-2.json"
    old2 = ORIGINAL / "gpu-PAW-5-off-recommended-guidance-2"
    old_followup = consumed(old2)
    old_resume = read(old2 / "RESULT.json")["resume"]
    old_diagnosis = Path(old_resume["main_review_measurement"])
    old_final = read(comparison)
    old_final_path = Path(old_final["source_review"])
    return {
        "historical_feedback": findings[historical.name],
        "historical_paid_2": old_followup,
        "historical_paid_diagnosis_measurement": record(old_diagnosis, old_resume["main_review_measurement_sha256"]),
        "historical_paid_diagnosis_cli_wall_s": read(old_diagnosis)["execution"]["wall_s"],
        "historical_paid_final_review": paid(old_final_path),
        "historical_paid_final_review_binding": record(old_final_path, old_final["source_review_sha256"]),
        "historical_conditional_owner_record": record(comparison),
        "original_checkpoint": record(original / "RESULT.json", state["source_result_sha256"]),
        "original_session": record(session_path(original), state["session_export_sha256"]),
        "prior_state_manifest": record(prior),
        "clean_neutral": neutral,
        "clean_paid_2": followup,
        "clean_history_inputs": record(history),
        "clean_input_bindings": bindings,
        "clean_owner_disposition": record(registry),
        "clean_owner_decision": owner["decision"],
        "initial_raw_counter": result_counter(original),
        "conditional_history_followup_raw_counters": [
            result_counter(historical), result_counter(old2)
        ],
        "clean_followup_raw_counters": [result_counter(clean1), result_counter(clean2)],
        "clean_paid_calls": [paid(Path(read(history)["paid_accounting"])), paid(Path(owner["source_review"]))],
    }


def tu():
    predecessor = COVERAGE / "persistent-tu-on"
    withdrawal = predecessor / "WITHDRAWAL.json"
    record_value = read(withdrawal)
    assert record_value["status"] == "withdrawn_before_launch"
    assert record_value["model_calls"] == 0
    assert not (predecessor / "runs").exists()
    old_plan = predecessor / "TU-ON-PLAN.json"
    assert "empty outcome map" in read(old_plan)["cohort"][0]["diagnostic"]

    resumed = unit("persistent-callback-admission-v2/runs/tu-on-retry-01/units/gpu-TU-GR-1-on-coding-v2-objective-1")
    feedback = (resumed / "FEEDBACK.txt").read_text()
    assert "simulated namespace mount-permission-refusal" in feedback
    witness = consumed(resumed, "FEEDBACK.txt", re.compile("empty outcome map", re.IGNORECASE))
    origin = read(resumed / "RESULT.json")["source_guidance"]
    assert origin["empty-map failure was never submitted"]
    migration = ROOT / "tu-oracle-v2/acceptance-migration.json"
    migration_data = read(migration)
    return {
        "obsolete_plan": record(old_plan),
        "withdrawal": record(withdrawal),
        "corrected_consumed_feedback": witness,
        "migration": record(migration),
        "old_grade": verify_ref(migration_data["raw_tu_on"]["result"]),
        "corrected_grade_stdout": verify_ref(migration_data["diagnostic_tu_on_v2"]["stdout"]),
        "later_false_pass_controls": record(ROOT / "tu-oracle-v4-qualification-v2/CONTROL.json"),
    }


def mm():
    migration = ROOT / "mm5-oracle-v4/acceptance-migration.json"
    value = read(migration)
    assert value["v3_comparison_assessments"] == 0
    assert value["startup_read_control"]["v3"]["status"] == "fail"
    assert value["startup_read_control"]["v4"]["status"] == "pass"
    controls = []
    for route in (
        "persistent-callback/runs/mm-v4-01/units/gpu-MM-5-on-coding-v4-objective-1",
        "persistent-callback/runs/mm-v4-01/units/gpu-MM-5-off-common-on-sampling-v4-objective-2",
        "persistent-callback/runs/cpu-tu-mm-01/units/cpu-MM-5-off-recommended-v4-objective-2",
    ):
        saved = unit(route)
        assert read(saved / "RESULT.json")["source_guidance"]["checker_version"] == "MM v4"
        controls.append(consumed(saved, "FEEDBACK.txt"))
    return {
        "v4_migration": record(migration),
        "v3_migration": verify_ref(value["v3_migration"]),
        "fresh_process_v4_control": verify_ref(value["v4_control_receipt"]),
        "v4_consumed_feedback": controls,
        "extra_robustness": consumed(unit(
            "persistent-mm-mechanical/runs/mechanical-01/units/gpu-MM-5-off-common-on-sampling-v4-mechanical-3"
        ), "FEEDBACK.txt"),
    }


def nariq():
    reassessment = ROOT / "nariq-v2-terminal-assessment-01/REPORT.json"
    value = read(reassessment)
    assert value["counts"] == {"changed_structural_verdict": 1, "no_candidate": 7, "regraded": 8, "terminal": 15}
    changed = next(row for row in value["rows"] if row.get("changed_structural_verdict"))
    assert changed["v1_raw_rc"] == 1 and changed["v2_replay"]["rc"] == 0
    assert not changed["guidance"] and changed["id"].startswith("cpu-")
    result = Path(changed["raw_result"]["path"])
    assert "No additional task guidance" in (result.parent / "PROMPT.md").read_text()
    absent = re.compile(r"Harness coverage['\"]\s*,\s*['\"]test_runtime\.hip", re.IGNORECASE)
    gpu = [
        consumed(Path(row["raw_result"]["path"]).parent, absent=absent)
        for row in value["rows"]
        if row["guidance"]
    ]
    assert len(gpu) == 4
    owner = unit("assisted-review/reviews/NARIQ-LIBTRELLIS-MAP-1/cpu-OFF-off-recommended/final-acceptance/runs/NARIQ-LIBTRELLIS-MAP-1/guidance-1/assistance-accounting.json")
    assert read(owner)["native_ordinal"] == 0
    assert read(owner)["allowed_next_native_correction"] is None
    assert read(owner)["semantic_review_advisory"] == "REJECT"
    return {
        "assessment": record(reassessment),
        "cpu_raw_grade": verify_ref(changed["raw_result"]),
        "cpu_resource_resume": consumed(result.parent, absent=absent),
        "observed_gpu_feedback": gpu,
        "cpu_independent_source_reject": paid(owner),
        "terminal_counts": value["counts"],
    }


def pfx(findings):
    migration = ROOT / "pfxc-oracle-v4/feedback-migration.json"
    value = read(migration)
    assert not value["guidance_unit_existed_at_migration"]
    result = {}
    for mode, expected in (("on-coding", "found 44"), ("off-recommended", "11896")):
        name = f"gpu-PFXC-A3-{mode}-guidance-1"
        prompt = (ORIGINAL / name / "PROMPT.md").read_text()
        assert expected in prompt, name
        evidence = findings[name]
        result[mode] = evidence
    return {"migration": record(migration), "consumed": result}


def main():
    earlier, findings = original_consumption()
    snapshot = {
        "schema": "a3b.feedback-lineage-audit.v1",
        "scope": "retained affected native feedback histories and protocol receipts",
        "model_calls": 0,
        "candidate_or_grader_executions": 0,
        "prior_consumption_audit": record(earlier),
        "paw": paw(findings),
        "paw_on_genuine_seam": findings["gpu-PAW-5-on-coding-guidance-1"],
        "pfx": pfx(findings),
        "tu": tu(),
        "mm": mm(),
        "nariq": nariq(),
        "comparison_cost_context": record(ROOT / "completion-audit/REPORT-v2.md"),
    }
    print(json.dumps(snapshot, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
