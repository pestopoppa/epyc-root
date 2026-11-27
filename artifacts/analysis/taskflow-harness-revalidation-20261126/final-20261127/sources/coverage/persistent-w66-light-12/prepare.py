"""Stage the accurate W66 light-v2 packet with equal-sampler thinking controls."""
from pathlib import Path
import tempfile

import callback

ROOT = callback.HERE.parent / "w66-light-brief-v2"
PACK_SHA = "65e235b135ecc4a82aa56fdedb60679dba6f10e62be05b10b0bee0d6ce774ea1"
SOURCE_RUNNER_SHA = "e203f1389e8753223da7ff9623ce67fad0f627716dd735c39117cce8344c5803"


def main():
    ctx = callback.sources()
    bridge, _, legacy, _, quality, _ = ctx
    legacy.same_file(callback.HERE.parent / "persistent-callback/RUNNER-SEAL.json", SOURCE_RUNNER_SHA)
    manifest = ROOT / "PACKAGE-SEAL.json"
    inputs = {str(manifest): legacy.same_file(manifest, PACK_SHA)}
    for name, expected in legacy.read(manifest)["sha256"].items():
        path = ROOT / name
        inputs[str(path)] = legacy.same_file(path, expected)
    case_dir = ROOT / "cases/DS41-W-66"
    case = legacy.read(case_dir / "case.json")
    from opencode_derived.case_snapshot import stage, validate_baseline
    validate_baseline(case_dir, case)
    detailed = legacy.read(quality.HERE / "packets/DS41-W-66/case.json")
    packet_view = callback.HERE / "packet-view/packets/DS41-W-66"
    if (case["baseline_files"] != detailed["baseline_files"] or case["oracle_sha256"] != detailed["oracle_sha256"]
            or case["task_packet_sha256"] == detailed["task_packet_sha256"] or packet_view.resolve() != case_dir):
        raise RuntimeError("light comparison changes baseline/oracle or uses the detailed brief")
    planned_slots = {True: 1, False: 2}
    sealed_rows = legacy.read(ROOT / "NATIVE-ROWS.json")
    rows = [{**row, "slot": planned_slots[row["thinking"]]} for row in sealed_rows]
    if len(rows) != 2 or {row["thinking"] for row in rows} != {True, False}:
        raise RuntimeError("light comparison must contain the two matched modes")
    for row in rows:
        if (Path(row["case_dir"]).resolve() != case_dir or Path(row["prompt"]).resolve() != case_dir / "prompt.md"
                or row["backend"] != "gpu" or row["fresh_session"] is not True or row.get("resume")
                or row["sampling"] != rows[0]["sampling"] or row["wall_s"] != 1800 or row["request_cap"] != 32768):
            raise RuntimeError("light control differs from the sealed equal-sampler test")
    plan = {"lease": bridge.lease.snapshot(legacy), "jobs": [
        {"kind": "quality-fresh", "id": row["id"], "row": row, "sha256": inputs,
         "source_guidance": {"paid_model_calls": 0, "class": "accurate light brief only"}}
        for row in rows], "model_calls_during_preparation": 0,
            "approved_slot_adjustment_from_tentative_packet": {"thinking_on": 1, "thinking_off": 2}}
    observed = {}
    for item in plan["jobs"]:
        row = item["row"]
        route = callback.check_item(ctx, plan, item)
        observed[str(row["slot"])] = bridge.slot_idle(route["port"], row["slot"])
    with tempfile.TemporaryDirectory(dir=callback.HERE) as folder:
        path = Path(folder)
        work = path / "work"
        work.mkdir()
        staged = stage(case_dir, work, path / "refs")
        assert staged["task_packet_sha256"] == case["task_packet_sha256"]
    target = callback.HERE / "W66-LIGHT-V2-PLAN.json"
    legacy.write(target, plan)
    legacy.write(callback.HERE / "CONTROL.json", {"passed": True, "native_model_calls": 0,
        "sealed_accurate_brief_and_same_baseline_oracle": True, "baseline_files": len(case["baseline_files"]),
        "persistent_route_proved": True, "idle_slot_sample": observed,
        "plan_sha256": legacy.digest(target), "source_packet_sha256": PACK_SHA})
    print(legacy.digest(target))


if __name__ == "__main__":
    main()
