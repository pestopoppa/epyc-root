"""Exercise the actual import order and live lease validator without model calls."""
from copy import deepcopy
import importlib
from pathlib import Path
import subprocess

import recover


def main():
    engine, cpu, gpu, quality, mechanical = recover.load_sources()
    # The original entry is __main__ and inputs() prepends legacy paths.
    # A bare import after that stack resolves the older module exactly as
    # in the original AttributeError. The recovery has its explicit module.
    ambiguous = importlib.import_module("run")
    assert not hasattr(ambiguous, "region")
    assert Path(ambiguous.__file__).resolve() == cpu.legacy.HERE / "run.py"
    assert Path(engine.__file__).resolve() == recover.BOUNDARY / "run.py" and callable(engine.region)
    source = recover.HERE / "CURRENT-PLAN.json"
    approved = cpu.legacy.read(source)
    assert recover.plan(engine, cpu, gpu, quality, mechanical, probe_idle=True) == approved
    assert approved["mechanical"]["slot"] == approved["legacy_mm_on"]["slot"] == 3
    assert approved["mechanical_deadline_s"] == 300 and approved["mm_deadline_s"] == 1800
    for label in ("holder", "controller", "server"):
        bad = deepcopy(approved)
        bad[label]["start_ticks"] += 1
        try:
            recover.verify_guard(engine, mechanical, bad)
        except RuntimeError as error:
            assert f"{label} changed" in str(error)
        else:
            raise AssertionError("stale birth admitted")
    bad = deepcopy(approved)
    bad["grant"]["regions"].remove("q3")
    try:
        recover.verify_guard(engine, mechanical, bad)
    except RuntimeError as error:
        assert "grant changed" in str(error)
    else:
        raise AssertionError("wrong held grant admitted")

    # Use the actual canonical job loader for the later MM row. Verification
    # reads the case and prompt but cannot submit an inference request.
    import tempfile
    with tempfile.TemporaryDirectory(dir=recover.HERE) as folder:
        out = Path(folder)
        job = out / "MM.json"
        cpu.legacy.write(job, gpu.build_job(out, approved["legacy_mm_on"], approved["serving"]))
        proof = subprocess.run(gpu.child_argv(job), env=gpu.worker_env(), text=True,
                               capture_output=True, check=True, timeout=15)
        assert cpu.legacy.json.loads(proof.stdout)["verified_case"] == "MM-5"
    cpu.legacy.write(recover.HERE / "CONTROL.json", {
        "passed": True, "native_calls": 0, "raw_import_reproduced": str(ambiguous.__file__),
        "fixed_explicit_import": str(engine.__file__), "live_lease_and_slot3_idle": True,
        "rejected_stale_holder_controller_gpu_births": True, "rejected_incorrect_region_grant": True,
        "mm_verify_only_passed": True, "plan_sha256": cpu.legacy.digest(source)})
    print(cpu.legacy.digest(recover.HERE / "CONTROL.json"))


if __name__ == "__main__":
    main()
