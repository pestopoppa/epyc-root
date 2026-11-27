"""Stage exact GPU TU ON paid correction 2 after a measured diagnosis. No model calls."""
import argparse
from hashlib import file_digest
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent
SOURCE = COVERAGE / "persistent-callback-admission-v2"
SOURCE_SEAL = "652ea6d728c0c9ee274d74dca77ba2f7e2c52acfde3225df4fe0b566e4aa753f"
RETRY = SOURCE / "runs/tu-on-retry-01"
PRIOR_ID = "gpu-TU-GR-1-on-coding-v2-objective-1"
UNIT = RETRY / "units" / PRIOR_ID
WORKER = UNIT / "worker"
NEXT_ID = "gpu-TU-GR-1-on-coding-paid-2"
PAW = SOURCE / "runs/paw-clean-paid-01/units/gpu-PAW-5-off-recommended-clean-paid-2"
GRADING = COVERAGE.parent / "source-review-gpu-tu-on-retry/grades" / PRIOR_ID
DIAGNOSIS = COVERAGE / "gpu-tu-on-paid-diagnosis/reviews/TU-GR-1/gpu-ON-on-coding/initial-diagnosis"
DIAGNOSIS_RUN = DIAGNOSIS / "runs/TU-GR-1/guidance-1"
REVIEW_SEAL = "f7f8773e5bb4bff1483b7a41c3f1132843b255f0b8c26324af57724db4d1e41a"
REVIEW_PLAN = "a44f0a615189ef3a52f0cf9dde722b5dd5812680cb958bc426abbd464f154e45"
PATCH = "0d35e2f372c19d81486d9eca64ebb2391e76c09d899446525004f35e37fe04a3"
KNOWN = {
    SOURCE / "RUNNER-SEAL.json": SOURCE_SEAL,
    RETRY / "PLAN.json": "68d74d1d187b3603c225c20f14ecae229c561b9d51f60cda9131412a213ae471",
    RETRY / "APPROVAL.json": "92fe3726014f815cb75a2fc4a9ed43f7063caa77bce06801e09f530aaccf0883",
    DIAGNOSIS / "SEAL.json": REVIEW_SEAL,
    DIAGNOSIS_RUN / "plan.json": REVIEW_PLAN,
    GRADING / "RESULT.json": "66c8a77eab20e798737cb887ee8f112263b178bfb569ebf196be5479ef1e5ac5",
    HERE / "PLAN.json": "3b3557eaa7388a3b94ce737ab28f6835b4954eae0741a47feeeb2a3a4a330d3c",
    HERE / "APPROVAL-TEMPLATE.json": "5a2c3dfbbf128024b647c15f819062a4958483f37ec3f77cbdff1738545c7b78",
    COVERAGE.parent / "tu-oracle-v4-qualification-v2/CONTROL.json":
        "e1f66b12bc1c5c5690486446ee23bdf5baf0b49144b9c487b679b6e176215ee8",
}


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def binding():
    source = {}

    def bind(path, expected=None):
        found = digest(path)
        if expected is not None and found != expected:
            raise ValueError(f"sealed TU ON source changed: {path}")
        source[str(path)] = found
        return found

    for path, expected in KNOWN.items():
        bind(path, expected)
    for name, expected in load(SOURCE / "RUNNER-SEAL.json")["sha256"].items():
        bind(SOURCE / name, expected)
    return source, bind


def stage_checkpoint(source, bind):
    plan = load(RETRY / "PLAN.json")
    entry, = plan["jobs"]
    row = entry["row"]
    owner = load(UNIT / "CALLBACK-RESULT.json")
    receipt = load(WORKER / "receipt.json")
    grade = load(GRADING / "RESULT.json")
    paw = load(PAW / "CALLBACK-RESULT.json")
    if (entry["id"] != PRIOR_ID or row["id"] != "gpu-TU-GR-1-on-coding"
            or row["case"] != "TU-GR-1" or row["backend"] != "gpu" or row["slot"] != 0
            or row["thinking"] is not True or row["profile"] != "on-coding"
            or row["wall_s"] != 1800 or row["request_cap"] != 32768
            or entry["source_guidance"]["paid_model_calls"] != 0):
        raise ValueError("prior measured native row changed")
    if (receipt["status"] != "review" or owner["status"] != "awaiting_source_review"
            or not owner["same_session"] or not owner["cleanup"]["removed_verified"]
            or owner["supervision"]["returncode"] != 0
            or receipt["outside_scope"] or receipt["unsafe_paths"]
            or receipt["patch_sha256"] != PATCH or receipt["generated_observed"] != 9118
            or grade["rc"] != 1 or grade["candidate_patch_sha256"] != PATCH
            or "wrong-access-errno" not in grade["diagnostic"][0]):
        raise ValueError("objective1 does not have exact candidate scope and actual V3 failure")
    if (paw["backend"] != "gpu" or paw["slot"] != 0 or not paw["terminal_at"]
            or not paw["cleanup"]["removed_verified"] or paw["supervision"]["returncode"] is None):
        raise ValueError("PAW GPU0 predecessor has not proved terminal cleanup")
    for path in (UNIT / "CALLBACK-RESULT.json", RETRY / "RESULTS.json",
                 PAW / "CALLBACK-RESULT.json", WORKER / "session.json"):
        bind(path)
    bind(WORKER / "receipt.json", owner["worker_receipt_sha256"])
    bind(WORKER / "candidate/candidate.patch", PATCH)
    bind(UNIT / "JOB.json", receipt["job_sha256"])
    bind(UNIT / "FEEDBACK.txt", receipt["prompt_sha256"])
    if (UNIT / "FEEDBACK.txt").read_text() != entry["feedback"]["text"]:
        raise ValueError("the original mount-only objective feedback changed")
    for name, expected in entry["sha256"].items():
        bind(Path(name), expected)
    for stream in ("stdout", "stderr"):
        bind(GRADING / (stream + ".log"), grade[stream + "_sha256"])
    for name, expected in load(DIAGNOSIS / "SEAL.json")["source_native_files"].items():
        bind(Path(name), expected)
    history = entry["previous_attempts"] + [{"path": str(UNIT), "generated": receipt["generated_observed"],
                                           "worker_wall_s": owner["supervision"]["elapsed_s"]}]
    return plan, row, receipt, history


def stage_diagnosis(source, bind, feedback):
    approval_path, events = DIAGNOSIS / "MAIN-APPROVAL.json", DIAGNOSIS_RUN / "events.jsonl"
    measurement, accounting = DIAGNOSIS_RUN / "measurement.json", DIAGNOSIS_RUN / "assistance-accounting.json"
    if any(not path.is_file() for path in (approval_path, events, measurement, accounting, feedback)):
        raise RuntimeError("waiting for owner-approved exact feedback and complete measured paid diagnosis")
    for path in (approval_path, events, measurement, accounting, feedback):
        bind(path)
    approval, measure, report = map(load, (approval_path, measurement, accounting))
    if (approval["approved_by"] != "main" or approval["native_harness_qualified"] is not True
            or approval["review_seal_sha256"] != REVIEW_SEAL
            or approval["plans"][str(DIAGNOSIS_RUN / "plan.json")] != REVIEW_PLAN
            or report["review_kind"] != "initial-diagnosis" or report["native_ordinal"] != 1
            or report["allowed_next_native_correction"] != 2 or report["semantic_review_advisory"] != "REJECT"
            or report["review_seal_sha256"] != REVIEW_SEAL or not report["candidate_unmodified_by_review"]
            or not report["path_scope_pass"] or report["model"] != "gpt-6.1-sol" or report["effort"] != "low"
            or report["events_sha256"] != source[str(events)]
            or report["measurement_sha256"] != source[str(measurement)]
            or report["execution"] != measure["execution"] or measure["execution"]["rc"] != 0):
        raise ValueError("paid diagnosis approval, receipt, or candidate custody differs")
    stream = [json.loads(line) for line in events.read_text().splitlines()]
    started = [event for event in stream if event.get("type") == "thread.started"]
    complete = [event["usage"] for event in stream if event.get("type") == "turn.completed"]
    last = [event["item"]["text"] for event in stream if event.get("type") == "item.completed"
            and event.get("item", {}).get("type") == "agent_message"][-1].strip()
    text = feedback.read_text().strip()
    body = re.sub(r"^REJECT\b[.:\s]*", "", last).strip()
    if (len(started) != 1 or len(complete) != 1 or not re.match(r"^REJECT\b", last)
            or text not in (last, body)):
        raise ValueError("feedback is not the actual paid verdict or its verbatim body")
    usage = report["usage"]
    names = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
    if (any(usage.get(name) != complete[0].get(name) for name in names)
            or usage["uncached_input_tokens"] != usage["input_tokens"] - usage["cached_input_tokens"]):
        raise ValueError("paid source guidance costs do not match the CLI's actual usage")
    return {"paid_model_calls": 1, "ordinal": 2, "class": "measured paid source review corrective guidance",
            "usage": usage, "model": report["model"], "effort": report["effort"],
            "measured_wall_s": measure["execution"]["wall_s"]}


def closed_debits(history, session, source, bind):
    debits = []
    for part in history:
        path = Path(part["path"]) / "worker/receipt.json"
        if str(path) not in source:
            raise ValueError("history does not reference a sealed native receipt")
        bind(path, source[str(path)])
        prior = load(path)
        observed = prior["generated_observed"]
        charged = prior["charged_toward_ceiling"]
        if (prior["status"] != "review" or prior["session"] != session
                or prior["reserved_at_terminal"] != 0 or prior["generation_unknown"] != 0
                or type(observed) is not int or type(charged) is not int
                or observed != part["generated"] or not 0 <= observed <= charged <= 120000):
            raise ValueError("unclosed or unresolved generated output ledger")
        debits.append({**part, "charged": charged, "generation_unknown": prior["generation_unknown"],
                       "receipt_sha256": source[str(path)], "reserved_at_terminal": 0})
    remaining = 120000 - sum(part["charged"] for part in debits)
    if len(debits) != 2 or remaining != 97211:
        raise ValueError("actual TU ON chain does not have the expected verified remaining budget")
    return debits, remaining


def verify_native(checkpoint, row, receipt, feedback):
    spec = importlib.util.spec_from_file_location("approved_tu_on_paid_callback", SOURCE / "callback.py")
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    ctx = native.sources()
    bridge, _, legacy, gpu, _, _ = ctx
    bridge.lease.verify_receipts(legacy, checkpoint["lease"])
    route = native.live(ctx, checkpoint, row)
    from opencode_derived.__main__ import SESSION_PROFILE, serving_proof, state_digest

    paths = [WORKER / "sandbox/work", WORKER / "sandbox/session"]
    if state_digest(*paths) != receipt["workspace_session_sha256"]:
        raise ValueError("saved objective1 workspace/session changed")
    job = gpu.build_job(SOURCE, row, route, feedback)
    if {key: job[key] for key in SESSION_PROFILE} != receipt["session_profile"]:
        raise ValueError("continuation would change the original provider profile")
    if serving_proof(job) != checkpoint["lease"]["native"]["gpu"]["pid"]:
        raise ValueError("continuation would use a different serving owner")
    return [str(path) for path in paths]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--feedback", type=Path)
    cli.add_argument("--check-prior-only", action="store_true")
    args = cli.parse_args()
    source, bind = binding()
    checkpoint, row, receipt, history = stage_checkpoint(source, bind)
    if args.check_prior_only:
        print(json.dumps({"candidate": PATCH, "objective_generated": 9118,
                          "same_session": receipt["session"], "slot": 0, "model_calls": 0}))
        return
    if not args.feedback:
        cli.error("supply exact owner-audited paid feedback")
    feedback_path = args.feedback.resolve(strict=True)
    cost = stage_diagnosis(source, bind, feedback_path)
    feedback = {
        "feedback": str(feedback_path), "feedback_sha256": source[str(feedback_path)],
        "prior_attempt": str(WORKER), "prior_receipt_sha256": source[str(WORKER / "receipt.json")],
        "prior_session_sha256": source[str(WORKER / "session.json")],
        "prior_workspace_session_sha256": receipt["workspace_session_sha256"],
    }
    history, remaining = closed_debits(history, receipt["session"], source, bind)
    row = {**row, "generated_ceiling": remaining}
    paths = verify_native(checkpoint, row, receipt, feedback)
    job = {"id": NEXT_ID, "kind": "canonical", "row": row, "feedback": feedback,
           "state_paths": paths, "state_sha256": receipt["workspace_session_sha256"],
           "prior_session": receipt["session"], "previous_attempts": history,
            "source_guidance": cost, "sha256": source,
           "generated_chain_budget": {"ceiling": 120000, "previous_charged": 120000 - remaining,
                                      "remaining_before_admission": remaining}}
    plan = HERE / "PLAN-v2.json"
    with plan.open("x") as stream:
        json.dump({"lease": checkpoint["lease"], "jobs": [job]}, stream, indent=2)
        stream.write("\n")
    template = {"approved_by": None, "runner_seal_sha256": SOURCE_SEAL,
                "plan": str(plan), "plan_sha256": digest(plan)}
    with (HERE / "APPROVAL-TEMPLATE-v2.json").open("x") as stream:
        json.dump(template, stream, indent=2)
        stream.write("\n")
    print(json.dumps({ "plan_sha256": digest(plan), "prior_paid_usage": cost,
                      "generated_chain_budget": job["generated_chain_budget"],
                      "out": str(SOURCE / "runs/tu-on-paid-01"), "model_calls": 0}))


if __name__ == "__main__":
    main()
