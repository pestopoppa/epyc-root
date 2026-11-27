"""Prepare only the paid second PAW correction from the clean neutral predecessor."""
import json
from pathlib import Path
import tempfile

import callback
import prepare_paw

COVERAGE = callback.HERE.parent
REVIEW = COVERAGE / "paw-clean-review"
STAGE = REVIEW / "reviews/PAW-5/gpu-OFF-off-recommended/initial-diagnosis"
CLEAN = callback.HERE / "runs/paw-clean-01/units/gpu-PAW-5-off-recommended-clean-guidance-1"
CLEAN_PLAN_SHA = "4d001d4fc816fff31f9896d1f75cde25253ff144e724a58108f0b53d2a1d08f9"


def cost(legacy, unit, inputs):
    raw = unit / "RESULT.json"
    wire = unit / "wire/requests.jsonl"
    result = legacy.read(raw)
    rows = [json.loads(line) for line in wire.read_text().splitlines()]
    known = [(row.get("usage") or {}).get("completion_tokens") for row in rows]
    observed = sum(n for n in known if isinstance(n, int))
    for ref in (raw, wire):
        inputs[str(ref)] = legacy.digest(ref)
    return {"path": str(unit), "generated": result.get("generation_observed"),
        "model_wall_s": result.get("model_wall_s"), "wire_observed_generated": observed,
        "wire_records": len(rows), "wire_records_missing_completion_usage": sum(n is None for n in known),
        "wire_failed_records": sum(row["http_status"] != 200 or bool(row["transport_error"] or row["server_error"])
                                   for row in rows),
        "wire_matches_raw_generated": observed == result.get("generation_observed"),
        "wire_sha256": inputs[str(wire)]}


def build():
    ctx = callback.sources()
    bridge, _, legacy, _, quality, _ = ctx
    clean_plan = callback.HERE / "PAW-CLEAN-PLAN.json"
    legacy.same_file(clean_plan, CLEAN_PLAN_SHA)
    initial_spec = legacy.read(clean_plan)["jobs"][0]
    row = dict(initial_spec["row"])
    inputs = dict(initial_spec["sha256"])
    inputs[str(clean_plan)] = CLEAN_PLAN_SHA
    for path, expected in inputs.items():
        legacy.same_file(Path(path), expected)
    initial = Path(row["resume"]["prior"])
    raw, wrapped = (legacy.read(CLEAN / name) for name in ("RESULT.json", "CALLBACK-RESULT.json"))
    structural = legacy.read(CLEAN / "CLEAN-V5-REVIEW-RECEIPT.json")
    if (raw["id"] != CLEAN.name or not raw["terminal_at"] or raw["session"] != initial_spec["prior_session"]
            or row["slot"] != 0 or row["thinking"] is not False or wrapped["independent_v5_rc"] != 0
            or not wrapped["terminal_at"] or not wrapped["cleanup"]["removed_verified"]
            or structural["source_callback_result_sha256"] != legacy.digest(CLEAN / "CALLBACK-RESULT.json")
            or structural["candidate_patch_sha256"] != raw["patch_sha256"]
            or structural["checker_sha256"] != inputs[str(prepare_paw.V5 / "oracle.py")]):
        raise RuntimeError("source is not the exact clean neutral checkpoint")
    patch = CLEAN / "independent/candidate.patch"
    legacy.same_file(patch, raw["patch_sha256"])
    paid = STAGE / "runs/PAW-5/guidance-1"
    plan, measurement = (legacy.read(paid / name) for name in ("plan.json", "measurement.json"))
    if (plan["source_native_result_sha256"] != legacy.digest(CLEAN / "RESULT.json")
            or plan["candidate_input_patch_sha256"] != raw["patch_sha256"]
            or plan["native_ordinal"] != 1 or plan["allowed_next_native_correction"] != 2
            or plan["native_correction_ceiling"] != 2 or measurement["jsonl"]["completed_turn_count"] != 1
            or measurement["jsonl"]["errors"] or not measurement["path_scope_pass"]
            or measurement["changed_by_strong_turn"]):
        raise RuntimeError("paid review is not the exact scoped terminal observation")
    exported = paid / "FEEDBACK.txt"
    events = (json.loads(line) for line in (paid / "events.jsonl").read_text().splitlines())
    messages = [event["item"]["text"] for event in events
                if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message"]
    if not messages or not messages[-1].startswith("REJECT") or exported.read_text().strip() != messages[-1].strip():
        raise RuntimeError("approved feedback is not the measured review's exact terminal text")
    evidence = [exported, paid / "plan.json", paid / "measurement.json", paid / "events.jsonl",
                paid / "assistance-accounting.json", STAGE / "SEAL.json", REVIEW / "SEAL.json",
                CLEAN / "CALLBACK-RESULT.json", CLEAN / "CLEAN-V5-REVIEW-RECEIPT.json",
                CLEAN / "OPEN-CODE-SESSION.json", patch]
    for path in evidence:
        inputs[str(path)] = legacy.digest(path)
    earlier = [cost(legacy, unit, inputs) for unit in (initial, CLEAN)]
    state_paths = [str(CLEAN / "sandbox/work"), str(CLEAN / "sandbox/session"), str(CLEAN / "refs")]
    from opencode_derived.__main__ import state_digest
    identity = state_digest(*map(Path, state_paths))
    row.update(id="gpu-PAW-5-off-recommended-clean-paid-2",
               protocol_class="initial0 + clean neutral1 + reviewed paid2",
               resume={"prior": str(CLEAN), "prior_result_sha256": inputs[str(CLEAN / "RESULT.json")],
                       "prior_session_sha256": inputs[str(CLEAN / "OPEN-CODE-SESSION.json")],
                       "prior_state_sha256": identity, "feedback": str(exported),
                       "feedback_sha256": inputs[str(exported)], "ordinal": 2, "main_model_feedback_calls": 1})
    guidance = {"paid_model_calls": 1, "main_model_feedback_calls": 1, "ordinal": 2,
                "class": "paid source review of clean neutral predecessor",
                "model": measurement["requested_model"], "effort": measurement["requested_effort"],
                "usage": measurement["jsonl"]["usage"], "measured_wall_s": measurement["execution"]["wall_s"],
                "excluded_false_feedback_branch": True}
    job = {"id": row["id"], "kind": "quality-resume", "row": row, "sha256": inputs,
           "state_paths": state_paths, "state_sha256": identity, "prior_session": raw["session"],
           "grade_v5": str(prepare_paw.V5 / "oracle.py"), "source_guidance": guidance, "previous_attempts": earlier}
    packet = {"lease": bridge.lease.snapshot(legacy), "jobs": [job], "model_calls_during_preparation": 0,
              "after": "TU-ON-V2 terminal and shared GPU slot 0 released"}
    route = callback.check_item(ctx, packet, job)
    with tempfile.TemporaryDirectory(dir=callback.HERE) as temp:
        out = Path(temp)
        refs = out / "refs"
        box = quality.Sandbox(out / "sandbox", route["port"], "84-87", assets=quality.ASSETS,
                              cap=row["request_cap"], ctx=131072, transport_wall_s=row["wall_s"],
                              refs=refs, public_web=True)
        _, restored = quality.stage_resume(quality.HERE / "packets/PAW-5", out, box, refs, row)
        if restored != raw["session"] or legacy.digest(box.config_path) != raw["config_sha256"]:
            raise RuntimeError("offline continuation changed saved session/profile")
    path = callback.HERE / "PAW-CLEAN-PAID-2-PLAN.json"
    legacy.write(path, packet)
    legacy.write(callback.HERE / "PAW-CLEAN-PAID-2-CONTROL.json", {
        "passed": True, "native_calls": 0, "actual_review_feedback_matched": True,
        "clean_history_and_exact_profile_restored_offline": True,
        "legacy_false_feedback_branch_excluded": True, "raw_and_wire_previous_costs": earlier,
        "plan_sha256": legacy.digest(path), "preparer_sha256": legacy.digest(Path(__file__))})
    print(legacy.digest(path))


if __name__ == "__main__":
    build()
