"""Prove each additive MM-5 check distinguishes its targeted regression."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "coverage/legacy-comparison"
CASE = LEGACY / "cases/MM-5"
MAIN = LEGACY / "runs/MM-5/direct-1"
SOURCE = Path("src/vision/analyzers/vl_describe.py")
CHECKS = ("unchanged_original_and_v2_feasible", "brief_environment_control",
          "additional_infeasible_cap_robustness")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def run(name, lane, expected, witness=None, *, oracle=HERE / "oracle.py"):
    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                          timeout=185, capture_output=True)
    output = HERE / "controls" / name
    output.mkdir(parents=True)
    (output / "stdout.log").write_bytes(proc.stdout)
    (output / "stderr.log").write_bytes(proc.stderr)
    result = json.loads(proc.stdout)
    checks = result["checks"]
    assert tuple(checks[key]["status"] for key in CHECKS) == expected, result
    assert proc.returncode == int("fail" in expected), proc.returncode
    if witness:
        assert witness in json.dumps(checks), result
    return {"id": name, "rc": proc.returncode, "checks": checks, "oracle_sha256": digest(oracle),
            "source_sha256": digest(lane / SOURCE),
            "stdout_sha256": digest(output / "stdout.log"), "stderr_sha256": digest(output / "stderr.log")}


def replace_one(source, before, after):
    if source.count(before) != 1:
        raise RuntimeError("pinned control location changed")
    return source.replace(before, after)


def main():
    sys.path.insert(0, str(LEGACY))
    from prepare import candidate_state, file_map

    case = load(CASE / "case.json")
    direct = load(MAIN / "measurement.json")
    assert direct["path_scope_pass"] and digest(MAIN / "delta.patch") == direct["patch_sha256"]
    baseline = CASE / "baseline"
    positive = MAIN / "lane"
    raw = file_map(positive)
    before = case["baseline_files"]
    source_files, _runtime = candidate_state(before, raw)
    changed = sorted(key for key in before.keys() | source_files.keys() if before.get(key) != source_files.get(key))
    assert changed == direct["final_changes"]
    assert file_map(baseline) == before
    source = (positive / SOURCE).read_text()
    controls = [
        run("main-direct", positive, ("pass", "pass", "pass")),
        run("baseline", baseline, ("fail", "fail", "fail"), "cannot import name 'encode_image_for_vl'"),
    ]
    with TemporaryDirectory(prefix="private-mm5-controls-", dir=HERE) as scratch:
        lane = Path(scratch) / "lane"
        shutil.copytree(positive, lane, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))
        env_read = 'os.environ.get("ORCHESTRATOR_VL_MAX_PIXELS")'
        backend_marker = '_VALID_VL_BACKENDS = {"auto", "server", "cli"}'
        startup = replace_one(source, f"env_max_pixels = {env_read}",
                              "env_max_pixels = _STARTUP_MAX_PIXELS")
        startup = replace_one(startup, backend_marker,
                              f"{backend_marker}\n_STARTUP_MAX_PIXELS = {env_read}")
        (lane / SOURCE).write_text(startup)
        controls.append(run("environment-read-at-startup", lane, ("pass", "pass", "pass")))
        controls.append(run("environment-read-at-startup-old-v3", lane, ("pass", "fail", "pass"),
                            "ORCHESTRATOR_VL_MAX_PIXELS=784: sent dimensions (896, 896)",
                            oracle=HERE.parent / "mm5-oracle-v3/oracle.py"))
        (lane / SOURCE).write_text(replace_one(
            source, f"env_max_pixels = {env_read}", "env_max_pixels = None",
        ))
        controls.append(run("environment-control-removed", lane, ("pass", "fail", "pass"),
                            "ORCHESTRATOR_VL_MAX_PIXELS=784: sent dimensions (896, 896)"))
        (lane / SOURCE).write_text(replace_one(
            source, '    if max_pixels is not None and max_pixels < 28 * 28:\n',
            '    if max_pixels == 1:\n        while True:\n            pass\n'
            '    if max_pixels is not None and max_pixels < 28 * 28:\n',
        ))
        controls.append(run("infeasible-cap-stalled", lane, ("pass", "pass", "fail"),
                            "cap=1: encoder did not return within 8 seconds"))
    assert file_map(positive) == raw and file_map(baseline) == before
    record = {
        "schema": "mm5.capped-encoding.v4.controls",
        "model_calls": 0, "main_patch_sha256": direct["patch_sha256"],
        "preserved_v2_seal_sha256": digest(HERE.parent / "mm5-oracle-v2/SOURCE-CONTROL.sha256"),
        "checks": controls,
    }
    (HERE / "CONTROL.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": len(controls), "model_calls": 0}))


if __name__ == "__main__":
    main()
