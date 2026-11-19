"""Offline control for a staged MI210 deployment.

Pass its stage directory and a fresh fixture directory as positional arguments.
This verifies prepared files and creates synthetic sealed captures in the
fixture directory. It starts no inference processes.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

stage = Path(sys.argv[1])
control = Path(sys.argv[2])
control.mkdir()
sys.path.insert(0, str(stage))
from scripts.vidya.producers import mi210_paired_capture as raw
from scripts.vidya.producers import mi210_native_run as native
import mi210_native_deploy as deploy
import gpuproof

manifest, identity = deploy.prepared(stage)
compile((stage / "job.py").read_text(), "job.py", "exec")
compile((stage / "gpuproof.py").read_text(), "gpuproof.py", "exec")
sampler = gpuproof.Sampler(sid=os.getpid())
assert sampler.mine(os.getpid()) and not sampler.mine(os.getppid())

shutil.copyfile(stage / "mi210_native_deploy.py", control / "mi210_native_deploy.py")
shutil.copytree(stage / "scripts", control / "scripts")
checks = dict.fromkeys(("in_request_own_residency_and_linkage", "requests", "no_draft", "no_error",
                       "own_vram", "no_foreign_kfd", "linkage", "released"), True)
order = [("p1", "C"), ("p1", "B"), ("p2", "B"), ("p2", "C")]
def sealed(mode, width):
    smoke = mode == "smoke"
    run_dir = control / "captures" / (mode + "-" + str(width))
    capture = run_dir / "belief-fake"
    capture.mkdir(parents=True)
    grant = run_dir / "rowflow.grant"
    grant.write_text("offline-fixture; never launched")
    grant_identity = native.identity(grant)
    cpus = list(range(184, 184 + width))
    raw.begin(capture, {"source": "Q38P-3a", "mode": mode, "model": [manifest["model"]],
                        "native_producer": native.identity(stage / "job.py"), "builds": manifest["builds"],
                        "recipe": {"arm_categories": {"C": "BASELINE", "B": "CANDIDATE"}},
                        "order": [list(x) for x in (order[:1] if smoke else order)], "grant": grant_identity,
                        "allocation": {"actual_cpus": cpus, "threads": width, "grant_sha256": grant_identity["sha256"]}})
    for pair, arm in order[:1] if smoke else order:
        raw.record(capture, {"state": "complete", "pair": pair, "arm": arm, "grant": grant_identity,
                             "checks": checks, "actual_placement": [{"allowed": cpus, "escapes": []}],
                             "residency_linkage": None, "errors": None, "stop": None, "release": None,
                             "requests": [{"timings": {"predicted_n": 8, "predicted_ms": 200,
                                                       "predicted_per_second": 40.0}}] * (1 if smoke else 5)})
    raw.finish(capture, "complete")
    deploy.record_result(control, capture, smoke)
    return grant

def isolated(command, expect):
    result = subprocess.run(["/usr/bin/python3", "-I", str(control / "mi210_native_deploy.py"), command],
                            env={**os.environ, "FILLER_SMOKE_T0":"0"}, text=True, capture_output=True)
    if result.returncode != expect:
        raise AssertionError((result.returncode, result.stdout, result.stderr))
    return result.stdout

isolated("complete", 1)
isolated("smoke", 1)
sealed("smoke", 4)
isolated("smoke", 0)
isolated("project", 1)
sealed("measurement", 4)
isolated("complete", 1)
grant = sealed("measurement", 8)
isolated("complete", 0)
observations = json.loads(isolated("project", 0))
assert len(observations) == 20
assert all(x["grade"] == ["Judged","Located"] and x["direction"] == "higher_better" for x in observations)
grant.write_text("changed")
isolated("complete", 1)
prepared = deploy.load(stage / "prepared.json")
real_fingerprint = deploy.fingerprint
deploy.fingerprint = lambda path: [0] if str(path) == prepared["model"]["path"] else real_fingerprint(path)
try:
    deploy.prepared(stage)
except ValueError as e:
    assert "prepared input changed" in str(e)
else:
    raise AssertionError("changed model metadata passed")
print("offline controls passed: prepared gate; transformed sources and PID scope; isolated clean/missing/stale resource/grant result; 20 shared-grade observations")

