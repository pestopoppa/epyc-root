"""Seal one W66 Light OFF deterministic correction from existing control evidence."""
import copy
import json
from pathlib import Path
import subprocess

import callback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIGHT = HERE.parent / "w66-light-brief-v2"
CASE = LIGHT / "cases/DS41-W-66"
ORIGIN = HERE.parent / "persistent-w66-light-12/runs/light-01"
UNIT = "gpu-DS41-W-66-off-common-light-v2"
NEW_ID = UNIT + "-identity-1"
PRIOR = ORIGIN / "units" / UNIT
CONTROL = ROOT / "w66-receipt-identity-control"
TOTAL = 120000
ELAPSED = 600


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    inputs = {}

    def bind(path, expected=None):
        digest = callback.digest(path)
        if expected is not None and digest != expected:
            raise ValueError(f"pinned input differs: {path}")
        inputs[str(path)] = digest
        return load(path) if path.suffix == ".json" else path

    prior_runner = HERE.parent / "persistent-callback-admission-v2"
    old = bind(prior_runner / "RUNNER-SEAL.json", "652ea6d728c0c9ee274d74dca77ba2f7e2c52acfde3225df4fe0b566e4aa753f")
    bind(prior_runner / "callback.py", old["sha256"]["callback.py"])
    bind(CONTROL / "SOURCE-CONTROL.sha256", "85075d9e8199128edec575e55eae65fb0bf0b3fa0b9141e44ed87000fe39ee6c")
    subprocess.run(["sha256sum", "-c", "--quiet", "SOURCE-CONTROL.sha256"],
                   cwd=CONTROL, check=True, timeout=15)
    witness = bind(CONTROL / "REPORT-full.json", "ce0aec2adbc5a83d7ee45c2573ffb814c4cd8de7461b8fbce7fe278c9b6b316e")
    owner = bind(ROOT / "w66-light-off-adjudication/ADJUDICATION.json",
                 "29be3790097881f6fccc9b276705ad71cdfdba4997e4974a6e0e06caf3b2dcee")
    assert owner["owner_decision"] == "reject_semantic_light_assertion_preservation"
    cases = {(row["id"], row["mode"]): row for row in witness["rows"]}
    for label in ("gpu-off-light", "gpu-on-light", "main-light"):
        control, mutant = (cases[label, mode] for mode in ("original", "mutated"))
        assert control["rc"] == 0 and control["candidate_source"] == mutant["candidate_source"]
        if label == "gpu-off-light":
            assert mutant["rc"] == 0 and mutant["serial_receives_replacement"]
        else:
            assert mutant["rc"] == 1 and mutant["failure_locations"] and not mutant["serial_receives_replacement"]
        event = bind(Path(mutant["evidence"]["path"]), mutant["evidence"]["sha256"])
        assert event["routing"]["phase_verified_before_change"] and event["routing"]["same_content"]
    manifest = bind(LIGHT / "PACKAGE-SEAL.json",
                    "65e235b135ecc4a82aa56fdedb60679dba6f10e62be05b10b0bee0d6ce774ea1")
    for name in ("case.json", "oracle.py", "prompt.md"):
        bind(CASE / name, manifest["sha256"][f"cases/DS41-W-66/{name}"])
    assert (HERE / "packet-view/packets/DS41-W-66").resolve() == CASE
    assert "preserving existing private-lock isolation and assertions" in (CASE / "prompt.md").read_text()
    approval = bind(ORIGIN / "APPROVAL.json")
    assert approval["approved_by"] == "main"
    original_plan = bind(ORIGIN / "PLAN.json", approval["plan_sha256"])
    row = dict(next(item["row"] for item in original_plan["jobs"] if item["id"] == UNIT))
    raw = bind(PRIOR / "RESULT.json", owner["raw_oracle"]["result"]["sha256"])
    assert raw["id"] == UNIT and raw["status"] == "oracle_pass" and raw["oracle"]["rc"] == 0
    assert raw["session"] and raw["fresh_session"] and raw["thinking"] is False
    assert raw["slot"] == row["slot"] == 2 and raw["sampling"] == row["sampling"]
    assert raw["backend"] == row["backend"] == "gpu"
    assert raw["request_cap"] == row["request_cap"] == 32768 and raw["wall_s"] == row["wall_s"] == 1800
    assert raw["generation_charged"] == raw["generation_observed"] == 14111
    assert raw["generation_unknown_requests"] == 0
    ledger_path = PRIOR / "wire/requests.jsonl"
    bind(ledger_path)
    requests = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    assert len(requests) == len({entry["seq"] for entry in requests}) == 70
    assert sum(entry["predicted_n"] for entry in requests) == raw["generation_charged"]
    prior_patch = PRIOR / "independent/candidate.patch"
    bind(prior_patch, raw["patch_sha256"])
    assert raw["patch_sha256"] == owner["candidate"]["patch"]["sha256"]
    session_path = PRIOR / "OPEN-CODE-SESSION.json"
    prior_session = bind(session_path)
    assert prior_session["info"]["id"] == raw["session"]
    assert len([message for message in prior_session["messages"] if message["type"] == "user"]) == 1
    feedback = HERE / "FEEDBACK.md"
    bind(feedback)
    text = feedback.read_text()
    assert all(term in text for term in ("different valid receipt", "both tests passed", "serial child used the replacement"))
    assert not any(term in text for term in ("ArtifactStore", "selection_reference", "ACCEPT", "REJECT", "main-light"))

    bridge, _, legacy, _, quality, _ = callback.sources()
    from opencode_derived.__main__ import state_digest
    paths = (PRIOR / "sandbox/work", PRIOR / "sandbox/session", PRIOR / "refs")
    checkpoint = state_digest(*paths)
    row.update(id=NEW_ID, fresh_session=False, generated_ceiling=TOTAL - raw["generation_charged"],
               guidance_received="one deterministic observed assertion sensitivity failure",
               resume={"prior": str(PRIOR), "prior_result_sha256": inputs[str(PRIOR / "RESULT.json")],
                       "prior_session_sha256": inputs[str(session_path)], "prior_state_sha256": checkpoint,
                       "feedback": str(feedback), "feedback_sha256": inputs[str(feedback)],
                       "ordinal": 1, "main_model_feedback_calls": 0})
    item = {
        "kind": "quality-resume", "id": NEW_ID, "row": row, "sha256": inputs,
        "supervision_wall_s": ELAPSED, "cumulative_generated_ceiling": TOTAL,
        "state_paths": [str(path) for path in paths], "state_sha256": checkpoint,
        "prior_session": raw["session"],
        "previous_attempts": [{"path": str(PRIOR), "generated": raw["generation_charged"],
                               "model_wall_s": raw["model_wall_s"], "status": raw["status"]}],
        "source_guidance": {"paid_model_calls": 0, "ordinal": 1,
                            "class": "deterministic receipt substitution observation only",
                            "original_two_test_pass_and_owner_adjudication_preserved": True},
    }
    lease = bridge.lease.snapshot(legacy)
    assert lease == original_plan["lease"]
    callback.verify_condition([item])
    for key, value in (("slot", 1), ("thinking", True), ("wall_s", 600), ("generated_ceiling", TOTAL)):
        negative = copy.deepcopy(item)
        negative["row"][key] = value
        try:
            callback.verify_condition([negative])
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"wrong {key} passed callback scope check")
    comparison = load(quality.HERE / "packets/DS41-W-66/case.json")
    light = load(CASE / "case.json")
    assert light["baseline_files"] == comparison["baseline_files"]
    assert light["oracle_sha256"] == comparison["oracle_sha256"]
    plan = {"lease": lease, "jobs": [item], "model_calls_during_preparation": 0}
    plan_path = HERE / "PLAN.json"
    write(plan_path, plan)
    write(HERE / "CONTROL.json", {
        "qualified": True, "original_scope_and_observer_preserved": True,
        "actual_candidate_specific_observation": True, "main_expert_critique_supplied": False,
        "model_calls": 0, "original_result_preserved": True, "begin_from_same_checkpoint": checkpoint,
        "same_gpu_slot": 2, "same_session_id": raw["session"], "sdk_wall_s": 1800,
        "external_condition_budget_s": ELAPSED, "external_budget_includes_slot_admission_and_signal_grace": True,
        "previous_generated_charged": raw["generation_charged"],
        "worker_generation_remaining": row["generated_ceiling"], "executable_proof_fault_cases_rejected": 4,
    })
    names = ("callback.py", "prepare.py", "PLAN.json", "CONTROL.json", "FEEDBACK.md")
    seal_path = HERE / "RUNNER-SEAL.json"
    write(seal_path, {"sha256": {name: callback.digest(HERE / name) for name in names}})
    write(HERE / "APPROVAL-TEMPLATE.json", {
        "approved_by": None, "runner_seal_sha256": callback.digest(seal_path),
        "plan": str(plan_path), "plan_sha256": callback.digest(plan_path),
        "scope": "one evidence-only same-session continuation; template authorizes no model call",
    })
    callback.verify(legacy, callback.digest(seal_path))
    print(json.dumps({"seal_sha256": callback.digest(seal_path), "plan_sha256": callback.digest(plan_path),
                      "slot": row["slot"], "max_additional_generated": row["generated_ceiling"]}))


if __name__ == "__main__":
    main()
