"""Prepare the sealed neutral PAW replay on its original GPU slot."""
from pathlib import Path
import tempfile

import callback

PACK = callback.HERE.parent / "paw-clean-replay"
V5 = callback.HERE.parent.parent / "paw-oracle-v5"
PACK_SHA = "6e69776455f3cfb3e58f245a9a92c41eb2b050382ebfdac9247d84fc66ed2ac0"
V5_SHA = "c3d2456c2f896b80ac2d480225a604c9833c758a9e7258cf4150ad6e741f81df"


def main():
    ctx = callback.sources()
    bridge, _, legacy, gpu, quality, _ = ctx
    proof = {}
    for root, filename, expected in ((PACK, "SEAL.json", PACK_SHA), (V5, "V5-SEAL.json", V5_SHA)):
        manifest = root / filename
        proof[str(manifest)] = legacy.same_file(manifest, expected)
        for name, digest in legacy.read(manifest)["files"].items():
            path = root / name
            proof[str(path)] = legacy.same_file(path, digest)
    prior_state = legacy.read(PACK / "PRIOR-STATE.json")
    row = legacy.read(PACK / "ROW.json")
    resume = row["resume"]
    previous = Path(prior_state["source_unit"])
    if (str(previous) != resume["prior"] or previous.name != "gpu-PAW-5-off-recommended"
            or resume["ordinal"] != 1 or row["slot"] != 0 or row["thinking"] is not False):
        raise RuntimeError("neutral replay includes wrong history or profile")
    for name, data in prior_state["files"].items():
        path = previous / name
        if path.stat().st_size != data["bytes"]:
            raise RuntimeError("clean predecessor bytes changed")
        legacy.same_file(path, data["sha256"])
    for path, expected in ((previous / "RESULT.json", resume["prior_result_sha256"]),
                           (previous / "OPEN-CODE-SESSION.json", resume["prior_session_sha256"])):
        proof[str(path)] = legacy.same_file(path, expected)
    source = legacy.read(previous / "RESULT.json")
    if source["session"] != prior_state["session"] or source["config_sha256"] != prior_state["config_sha256"]:
        raise RuntimeError("clean predecessor config or session differs")
    bench = quality.read(quality.HERE / "GRID.json")
    initial = next(x for x in bench["rows"] if x["id"] == previous.name)
    for key in ("case", "backend", "thinking", "profile", "sampling", "slot", "request_cap", "generated_ceiling", "wall_s"):
        if row[key] != initial[key]:
            raise RuntimeError(f"clean replay changes {key}")
    from opencode_derived.__main__ import state_digest
    state = [str(previous / "sandbox/work"), str(previous / "sandbox/session"), str(previous / "refs")]
    job = {"id": row["id"], "kind": "quality-resume", "row": row, "sha256": proof,
           "state_paths": state, "state_sha256": state_digest(*map(Path, state)),
           "prior_session": source["session"], "grade_v5": str(V5 / "oracle.py"),
           "source_guidance": {"paid_model_calls": 0, "class": "neutral self-check", "ordinal": 1},
           "previous_attempts": [{"path": str(previous), "generated": source.get("generation_observed"),
                                  "model_wall_s": source.get("model_wall_s")}]}
    plan = {"lease": bridge.lease.snapshot(legacy), "jobs": [job], "model_calls_during_preparation": 0}
    serving = callback.check_item(ctx, plan, job)
    if not bridge.slot_idle(serving["port"], 0):
        raise RuntimeError("GPU0 is busy")
    with tempfile.TemporaryDirectory(dir=callback.HERE) as folder:
        out = Path(folder)
        refs = out / "refs"
        box = quality.Sandbox(out / "sandbox", serving["port"], "84-87", assets=quality.ASSETS,
                              cap=row["request_cap"], ctx=131072, transport_wall_s=row["wall_s"],
                              refs=refs, public_web=True)
        _, restored = quality.stage_resume(quality.HERE / "packets/PAW-5", out, box, refs, row)
        if restored != source["session"] or legacy.digest(box.config_path) != source["config_sha256"]:
            raise RuntimeError("offline resume failed original source/session/config proof")
    target = callback.HERE / "PAW-CLEAN-PLAN.json"
    legacy.write(target, plan)
    legacy.write(callback.HERE / "PAW-CONTROL.json", {"passed": True, "native_model_calls": 0,
        "sole_original_checkpoint": str(previous), "new_live_idle_slot": 0,
        "offline_exact_restored_session": source["session"], "plan_sha256": legacy.digest(target)})
    print(legacy.digest(target))


if __name__ == "__main__":
    main()
