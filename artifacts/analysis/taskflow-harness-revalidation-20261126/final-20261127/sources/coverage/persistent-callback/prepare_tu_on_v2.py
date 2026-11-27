"""Bind only the qualified TU V2 mount diagnostic to the original thinking session."""
from pathlib import Path
import tempfile

import callback

ROOT = callback.HERE.parent.parent
NAME = "gpu-TU-GR-1-on-coding"
CHECK = ROOT / "tu-oracle-v2"
CHECK_SHA = "75745276e36e01cc279da123094036228ba187dc707f82ce0769b6b50345bca8"


def main():
    ctx = callback.sources()
    bridge, _, legacy, gpu, _, _ = ctx
    row = gpu.sealed_rows()[0][NAME]
    prior = callback.HERE.parent / "legacy-boundary-v3/runs/boundary-01/units" / NAME
    worker = prior / "worker"
    raw = legacy.read(prior / "RESULT.json")
    source = legacy.read(worker / "receipt.json")
    if not raw["terminal_at"] or raw["worker_receipt_sha256"] != legacy.digest(worker / "receipt.json"):
        raise RuntimeError("original TU thinking checkpoint is not terminal")
    paths = (prior / "RESULT.json", worker / "receipt.json", worker / "session.json",
             worker / "candidate/candidate.patch")
    proof = {str(path): legacy.digest(path) for path in paths}
    sha_path = CHECK / "SOURCE-CONTROL.sha256"
    proof[str(sha_path)] = legacy.same_file(sha_path, CHECK_SHA)
    for line in sha_path.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        path = CHECK / name
        proof[str(path)] = legacy.same_file(path, expected)
    directory = CHECK / "owner-assessments" / NAME
    report = directory / "RESULT.json"
    test = legacy.read(report)
    if (test["rc"] != 1 or test["id"] != NAME or test["candidate_patch_sha256"] != source["patch_sha256"]
            or test["candidate_patch_sha256"] != proof[str(paths[-1])] or not test["raw_results_preserved"]
            or test["oracle_sha256"] != proof[str(CHECK / "oracle.py")]
            or test["checker_sha256"] != proof[str(CHECK / "tu_grader_isolation.py")]):
        raise RuntimeError("the qualified owner receipt does not bind this candidate")
    review = ROOT / "source-review-legacy-boundary-tu-on/REVIEW.json"
    proof[str(review)] = legacy.same_file(review, test["source_review_sha256"])
    for name, expected in legacy.read(review)["rows"][NAME]["input_sha256"].items():
        proof[name] = legacy.same_file(Path(name), expected)
    proof[test["v1_raw_score"]["path"]] = legacy.same_file(Path(test["v1_raw_score"]["path"]),
                                                          test["v1_raw_score"]["sha256"])
    proof[str(report)] = legacy.digest(report)
    for stream in ("stdout", "stderr"):
        path = directory / f"{stream}.log"
        proof[str(path)] = legacy.same_file(path, test[f"{stream}_sha256"])
    diagnosis = test["diagnostic"]
    line = (directory / "stdout.log").read_text().splitlines()[0]
    expected = "simulated namespace mount-permission-refusal: expected rc=1 and control passed / isolated failure, got rc=0"
    if (diagnosis != [line] or not line.startswith(expected) or "'test_isolated_launch_denies': ('skipped'" not in line
            or "mount: simulated tmpfs setup: Operation not permitted" not in line):
        raise RuntimeError("TU V2 diagnostic does not identify the recorded mount behavior")
    message = ("Continue the same task from your saved workspace/session.\n\n"
               "The independent verifier observed: " + expected + ". The control passed, but "
               "the isolated test was skipped on the mount error 'Operation not permitted'.\n\n"
               "Address that observed behavior within the original scope and run the task-local check.\n")
    from opencode_derived import __main__ as driver
    from opencode_derived.sandbox import Assets, Sandbox
    state_paths = [str(worker / "sandbox/work"), str(worker / "sandbox/session")]
    state = driver.state_digest(*map(Path, state_paths))
    if state != source["workspace_session_sha256"]:
        raise RuntimeError("original saved TU thinking state changed")
    feedback = {"prior_attempt": str(worker), "prior_receipt_sha256": proof[str(paths[1])],
                "prior_session_sha256": proof[str(paths[2])], "prior_workspace_session_sha256": state}
    job = {"id": NAME + "-v2-objective-1", "kind": "canonical", "row": row, "sha256": proof,
           "feedback": {**feedback, "text": message}, "state_paths": state_paths, "state_sha256": state,
           "prior_session": source["session"], "source_guidance": {"paid_model_calls": 0, "ordinal": 1,
               "class": "TU V2 mount observation only", "empty-map failure was never submitted": True},
           "previous_attempts": [{"path": str(prior), "generated": source.get("generated_observed"),
                                  "worker_wall_s": source["ended_at"] - source["started_at"]}]}
    plan = {"lease": bridge.lease.snapshot(legacy), "jobs": [job],
            "model_calls_during_preparation": 0, "after": "PAW clean terminal on the shared GPU0 lock"}
    route = callback.check_item(ctx, plan, job)
    slot_idle = bridge.slot_idle(route["port"], 0)
    with tempfile.TemporaryDirectory(dir=callback.HERE) as tmp:
        work = Path(tmp)
        guide = work / "feedback"
        guide.write_text(message)
        env = dict(feedback, feedback=str(guide), feedback_sha256=legacy.digest(guide))
        params = gpu.build_job(work, row, route, env)
        source_path = work / "JOB.json"
        legacy.write(source_path, params)
        native, _, case, _ = driver.load_job(source_path, legacy.digest(source_path))
        assets = native["assets"]
        box = Sandbox(work / "sandbox", native["port"], "84-87", assets=Assets(
            Path(assets["opencode"]), Path(assets["python_packages"]), Path(assets["socket_root"]),
            image=assets["image"], executable_sha256=assets["opencode_sha256"]), ctx=native["context"],
            cap=native["request_cap"], transport_wall_s=native["wall_s"], public_web=native["public_web"])
        assert driver.restore_session(native, case, box) == source["session"]
    target = callback.HERE / "TU-ON-V2-PLAN.json"
    legacy.write(target, plan)
    legacy.write(callback.HERE / "TU-ON-V2-CONTROL.json", {"passed": True, "native_calls": 0,
        "offline_canonical_session_profile_restored": True, "gpu0_idle_at_control": slot_idle,
        "plan_sha256": legacy.digest(target), "preparer_sha256": legacy.digest(Path(__file__))})
    print(legacy.digest(target))


if __name__ == "__main__":
    main()
