"""Replay frozen W66 source in the original private grading scaffold."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BINDER = ROOT / "w66-light-v2-independent-grade/grade_saved.py"
NATIVE = ROOT / "source-review-w66-light-native/REVIEW.json"
SOURCE = "scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py"
GPU = ROOT / "coverage/persistent-w66-light-12/runs/light-01/units"


def ref(path, expected=None):
    with path.open("rb") as stream:
        found = hashlib.file_digest(stream, "sha256").hexdigest()
    if expected is not None and found != expected:
        raise RuntimeError(f"pinned input changed: {path}")
    return {"path": str(path), "sha256": found}


def load(path):
    return json.loads(path.read_bytes())


def binder():
    ref(BINDER, "1618043389a926e08573ddf5ee7bbca8d932f5b5c6cca7c27f140028d2ac202e")
    spec = importlib.util.spec_from_file_location("light_grade_binder", BINDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(name, mode, source, expected_source, case, app_ref, app_sha, oracle, baseline_dir):
    candidate = ref(source, expected_source)
    out = HERE / "runs" / name / mode
    out.mkdir(parents=True)
    with TemporaryDirectory(prefix="private-w66-identity-", dir=out) as tmp:
        scratch = Path(tmp)
        app = scratch / "app"
        app.mkdir()
        prepare = sys.modules["prepare"]
        app_path = "src/runtime/cpu_region_lock.py"
        prepare.stage_archive("epyc-orchestrator", app_ref, app_path, app)
        ref(app / app_path, app_sha)
        root = scratch / "root"
        (root / "scripts/vidya/adapters").mkdir(parents=True)
        lane = scratch / "candidate"
        shutil.copytree(baseline_dir, lane)
        shutil.copy2(source, lane / SOURCE)
        mode_bits = (lane / SOURCE).stat().st_mode
        expected_map = case["baseline_files"] | {SOURCE: {
            "sha256": candidate["sha256"], "bytes": source.stat().st_size, "executable": bool(mode_bits & 0o111),
        }}
        assert prepare.file_map(lane) == expected_map
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_ADDOPTS="", OPENBLAS_NUM_THREADS="1",
                   OMP_NUM_THREADS="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", TMPDIR=tmp)
        for key in ("EPYC_ROOT", "EPYC_ROOT_REPO", "EPYC_ORCHESTRATOR_REPO", "PYTHONPATH"):
            env.pop(key, None)
        env |= {"EPYC_ROOT_REPO": str(root), "EPYC_ORCHESTRATOR_REPO": str(app)}
        evidence = out / "OBSERVATION.json"
        cmd = ["/usr/bin/python3", "-B", str(HERE / "observer.py"), str(oracle),
               str(scratch / "pytest"), mode, str(evidence)]
        result = subprocess.run(cmd, cwd=lane, env=env, capture_output=True, timeout=90)
        assert prepare.file_map(lane) == expected_map
    (out / "stdout.log").write_bytes(result.stdout)
    (out / "stderr.log").write_bytes(result.stderr)
    ref(source, candidate["sha256"])
    assert evidence.is_file(), (name, mode, result.returncode)
    observed = load(evidence)
    assert observed["rc"] == result.returncode and observed["oracle_claim_observations"] == 2
    assert observed["routing"]["phase_verified_before_change"] and observed["routing"]["original_read_proof_verified"]
    assert observed["journal_completion_observations"] > 0
    if mode == "mutated":
        assert observed["routing"]["same_content"]
        original, replacement = observed["routing"]["original"], observed["routing"]["replacement"]
        assert original["locator"] != replacement["locator"] and original["sha256"] != replacement["sha256"]
    verdict = {
        "id": name, "mode": mode, "candidate_source": candidate, "rc": result.returncode,
        "evidence": ref(evidence), "stdout": ref(out / "stdout.log"), "stderr": ref(out / "stderr.log"),
        "serial_receives_replacement": observed["serial_receives_replacement"],
        "pytest_result": result.stdout.decode().splitlines()[-1:],
        "failure_locations": [line for line in result.stdout.decode().splitlines() if "AssertionError" in line],
    }
    print(json.dumps(verdict), flush=True)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("gpu-off-light", "gpu-on-light", "main-light"))
    parser.add_argument("--extra-only", action="store_true")
    options = parser.parse_args()
    helper = binder()
    main_review, case, _, main_lane = helper.bind()
    assert main_review == load(BINDER.parent / "REVIEW.json")
    ref(NATIVE, "a3a287683ab947b79154e6ff77404b02083854a21afa4ede85d388abf2f2d8de")
    native = load(NATIVE)["rows"]
    baseline = helper.CASE / "baseline"
    oracle = helper.CASE / "oracle.py"
    ref(oracle, case["oracle_sha256"])

    inputs = {"main-light": (main_lane / SOURCE, main_review["candidate"]["sha256"])}
    for mode in ("off", "on"):
        name = f"gpu-DS41-W-66-{mode}-common-light-v2"
        reviewed = native[name]
        for path, expected in reviewed["input_sha256"].items():
            ref(Path(path), expected)
        candidate = GPU / name / "independent/work" / SOURCE
        inputs[f"gpu-{mode}-light"] = (candidate, reviewed["input_sha256"][str(candidate)])
    if options.extra_only:
        extra = HERE / "EXTRA-INPUTS.json"
        saved = load(extra)
        for value in saved.values():
            for artifact in (value["result"], value["patch"]):
                ref(Path(artifact["path"]), artifact["sha256"])
        inputs = {key: (Path(value["path"]), value["sha256"]) for key, value in saved.items()}
    elif options.only:
        inputs = {options.only: inputs[options.only]}

    app = main_review["app_scaffold"]
    jobs = [(name, mode, candidate, digest) for name, (candidate, digest) in sorted(inputs.items())
            for mode in ("original", "mutated")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda job: run(*job, case, app["rev"], app["sha256"], oracle, baseline), jobs))
    name = options.only or ("extra" if options.extra_only else "full")
    path = HERE / f"REPORT-{name}.json"
    report = {
        "schema": "taskflow.w66.receipt-identity-control.v1", "rows": results,
        "oracle": ref(oracle), "semantic_variation": "same recipe and body values, distinct locator and valid digest",
        "source_candidates_unchanged": True, "model_calls": 0,
    }
    with path.open("x") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
