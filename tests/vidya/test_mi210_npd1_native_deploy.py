"""Synthetic controls for the NPD1 launcher. Never start inference."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

import pytest

from scripts.vidya.adapters.mi210_paired_raw import project
from scripts.vidya.claim_tuple import grade
from scripts.vidya.producers import mi210_native_run as native
from scripts.vidya.producers import mi210_npd1_native_deploy as deploy
from scripts.vidya.producers import mi210_paired_capture as raw
from test_mi210_native_patches import patched


def grant_text(smoke):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=35)
    placement = (
        f"regions=4-7 holds=c4,c5,c6,c7 id={deploy.ROW} kind=rowflow-dryrun"
        if smoke else "regions=0-95 holds=q0,q1,q2,q3,gpu-quiet lock=0-95,96-111"
    )
    return f"{placement} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n", int(end.timestamp()) - 90


def test_grant_width_and_gpu_quiet():
    measurement, _ = grant_text(False)
    assert deploy.validate_grant(measurement, False, deploy.CPU_POOL)[2] == set(range(112))
    with pytest.raises(ValueError, match="full quiet-host grant"):
        deploy.validate_grant(measurement.replace(",gpu-quiet", ""), False, deploy.CPU_POOL)
    with pytest.raises(ValueError, match="full quiet-host grant"):
        deploy.validate_grant(measurement, False, set(range(4)))
    smoke, _ = grant_text(True)
    with pytest.raises(ValueError, match="four-CPU"):
        deploy.validate_grant(smoke, True, {4, 5, 6, 8})


def stage_fixture(root):
    job = root / "job.py"
    job.write_text("# synthetic control")
    builds = {}
    for arm in ("cpu", "gpu_cpu"):
        image = root / arm
        image.mkdir()
        path = image / "libggml-cpu.so"
        path.write_text(f"{arm} fixture")
        builds[arm] = {
            "directory": str(image), "files": [deploy.prepare_identity(path)],
            "targets": {path.name: str(path), "llama-server": str(image / "llama-server")},
        }
        (image / "llama-server").touch()
    manifest = {"row": deploy.ROW, "inputs": {"job.py": deploy.digest(job)},
                "original_producer": {"fake": True}, "models": [], "builds": builds}
    deploy.write(root / "prepared.json", manifest)
    return manifest, deploy.digest(root / "prepared.json")


def sealed_fixture(root, manifest, smoke, *, wrong_linkage=False):
    mode = "smoke" if smoke else "measurement"
    parent = root / "captures" / f"{mode}-{wrong_linkage}"
    capture = parent / "belief-fixture"
    capture.mkdir(parents=True)
    grant_path = parent / "rowflow.grant"
    grant_doc, deadline = grant_text(smoke)
    grant_path.write_text(grant_doc)
    grant = native.identity(grant_path)
    cpus = list(range(4, 8)) if smoke else list(range(96))
    order = deploy.ORDER[:1] if smoke else deploy.ORDER
    raw.begin(capture, {
        "source": deploy.SOURCE, "mode": mode, "order": order,
        "native_producer": native.identity(root / "job.py"), "model": [], "builds": manifest["builds"],
        "original_native_producer": manifest["original_producer"], "deployment": native.identity(root / "prepared.json"),
        "grant": grant, "recipe": {"arm_categories": {"cpu": "BASELINE", "gpu_cpu": "CANDIDATE"}},
        "allocation": {"rowflow_id": deploy.ROW, "grant_sha256": grant["sha256"], "actual_cpus": cpus,
                       "grant_cpus": "4-7" if smoke else "0-95,96-111", "deadline_epoch": deadline,
                       "decode_threads": 4 if smoke else 48, "load_threads": 4 if smoke else 96},
    })
    for pair, arm in order:
        store = manifest["builds"][arm]["files"][0]["path"]
        paths = ["/wrong/libggml-cpu.so"] if wrong_linkage else [store]
        raw.record(capture, {
            "pair": pair, "arm": arm, "state": "complete", "grant": grant, "errors": None, "stop": None,
            "actual_placement": {"pid": 1, "before_request": cpus, "after_request": cpus},
            "requests": [{"start": 1, "end": 3, "timings": {"predicted_n": 8 if smoke else 512, "predicted_ms": 200}}],
            "residency_linkage": {"samples": [{"time": 2, "pid": 1, "affinity": cpus, "paths": paths}]},
            "release": {"pid": 1, "alive": False},
        })
    terminal = raw.finish(capture, "complete")
    result = {"mode": mode, "state": "complete", "capture": str(capture), "terminal_sha256": terminal["row_sha256"]}
    deploy.write(parent / "custody.json", result)
    deploy.write(root / ("SMOKE.json" if smoke else "RESULT.json"), result)
    return capture


def test_result_gate_refuses_smoke_as_measurement_wrong_mapped_store_and_changed_grant(tmp_path, monkeypatch):
    manifest, seal = stage_fixture(tmp_path)
    monkeypatch.setenv("FILLER_SMOKE_T0", str(int(time.time()) - 1))
    smoke = sealed_fixture(tmp_path, manifest, True)
    assert deploy.verified_result(tmp_path, seal, True) == smoke
    (tmp_path / "RESULT.json").write_bytes((tmp_path / "SMOKE.json").read_bytes())
    assert deploy.verified_result(tmp_path, seal, False) is None
    monkeypatch.setenv("FILLER_SMOKE_T0", str(int(time.time()) + 1))
    assert deploy.verified_result(tmp_path, seal, True) is None
    sealed_fixture(tmp_path, manifest, False, wrong_linkage=True)
    assert deploy.verified_result(tmp_path, seal, False) is None
    measurement = sealed_fixture(tmp_path, manifest, False)
    assert deploy.verified_result(tmp_path, seal, False) == measurement
    claims = project(measurement)
    assert len(claims) == 4
    assert all(grade(claim)[:2] == ("Judged", "Located") and claim.metric_direction == "lower_better" for claim in claims)
    with (measurement.parent / "rowflow.grant").open("a") as stream:
        stream.write("changed=1\n")
    assert deploy.verified_result(tmp_path, seal, False) is None


def test_early_refusal_has_custody_without_native_result(tmp_path, monkeypatch):
    monkeypatch.setenv("FILLER_DRYRUN", "1")
    monkeypatch.delenv("FILLER_ID", raising=False)
    assert deploy.runtime(tmp_path, "unused") == 1
    result = deploy.load(tmp_path / "SMOKE.json")
    attempt = Path(result["attempt"])
    assert deploy.load(attempt / "custody.json") == result
    assert result["state"] == "refused"
    assert "FILLER_ID" in result["error"]
    assert not (tmp_path / "RESULT.json").exists()


def test_deployed_job_stop_seals_without_launching(tmp_path):
    job = patched(tmp_path, "npd1")
    deploy.deploy_npd1(job)
    tree = ast.parse(job.read_text())
    body = tree.body[next(i for i, statement in enumerate(tree.body)
                          if ast.unparse(statement) == "OUT.mkdir(exist_ok=True)"):]
    env = {
        "__file__": str(job), "OUT": tmp_path / "capture", "NativeRun": native.NativeRun,
        "identity": native.identity, "grant": lambda: None, "build_identity": lambda _: {},
        "model_identities": lambda _: [], "MODEL": "/unused", "MTP": "/unused",
        "CPU": "/unused", "GPU": "/unused", "COMMON": [], "ENV": {}, "PROMPT": "fixture",
        "ORDER": deploy.ORDER, "SMOKE": False, "Path": Path, "stopped": lambda: True,
    }
    with pytest.raises(SystemExit) as exit_info:
        exec(compile(ast.Module(body=body, type_ignores=[]), str(job), "exec"), env)
    assert exit_info.value.code == 75
    capture, = env["OUT"].glob("belief-*")
    run = raw.read(capture)
    assert run["state"] == "stopped"
    assert not run["attempts"]
    assert run["terminal"]["stop"] == "STOP before launch"
