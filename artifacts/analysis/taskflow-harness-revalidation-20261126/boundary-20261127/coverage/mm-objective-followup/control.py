"""Verify the live owned routes and both saved OpenCode states without model calls."""
from pathlib import Path
import tempfile

import follow


def main():
    recovery, components = follow.sources()
    cpu = components[1]
    gpu = components[2]
    legacy = cpu.legacy
    from opencode_derived import __main__ as driver
    from opencode_derived.sandbox import Assets, Sandbox
    plan_path = follow.HERE / "MM-OBJECTIVE-PLAN.json"
    plan = legacy.read(plan_path)
    assert plan == follow.stage(recovery, components, follow.CURRENT_MM)
    assert {(r["row"]["backend"], r["row"]["slot"]) for r in plan["cohort"]} == {("cpu", 1), ("gpu", 2)}
    sessions = {}
    with tempfile.TemporaryDirectory(dir=follow.HERE) as folder:
        root = Path(folder)
        for entry in plan["cohort"]:
            row = entry["row"]
            attempt = root / row["backend"]
            attempt.mkdir()
            passage = attempt / "diagnostic.md"
            passage.write_text(entry["diagnostic"] + "\n")
            assert "/case" not in entry["diagnostic"] and "/tmp" not in entry["diagnostic"]
            assert "Traceback" not in entry["diagnostic"] and entry["source_guidance_tokens"] == 0
            assert legacy.read(Path(entry["original_rc0_receipt"]))["rc"] == 0
            assert legacy.read(Path(entry["grade_receipt"]))["rc"] == 1
            envelope = dict(entry, feedback=str(passage), feedback_sha256=legacy.digest(passage))
            job_path = attempt / "JOB.json"
            legacy.write(job_path, gpu.build_job(root, row, plan["lease"]["providers"][row["backend"]], envelope))
            job, _, case, brief = driver.load_job(job_path, legacy.digest(job_path))
            assert brief == passage.read_text()
            spec = job["assets"]
            assets = Assets(Path(spec["opencode"]), Path(spec["python_packages"]), Path(spec["socket_root"]),
                            image=spec["image"], executable_sha256=spec["opencode_sha256"])
            box = Sandbox(attempt / "sandbox", job["port"], "84-87", assets=assets, ctx=job["context"],
                          cap=job["request_cap"], transport_wall_s=job["wall_s"], public_web=job["public_web"])
            session = driver.restore_session(job, case, box)
            assert session == entry["prior_session"]
            sessions[row["backend"]] = session
    legacy.write(follow.HERE / "CONTROL.json", {
        "passed": True, "native_model_calls": 0, "exact_actual_checker_receipts": 2,
        "live_owner_and_idle_slots_verified": True, "session_ids_restored_offline": sessions,
        "same_provider_config_and_slot": True, "no_source_snippets_in_feedback": True,
        "plan_sha256": legacy.digest(plan_path)})
    print(legacy.digest(follow.HERE / "CONTROL.json"))


if __name__ == "__main__":
    main()
