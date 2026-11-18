"""Software fixtures for the isolated CPU contention acquisition."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "scripts/benchmark/kernel_promotion_contention_acquire.py"
SPEC = importlib.util.spec_from_file_location("kernel_promotion_contention_acquire", SOURCE)
acquire = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquire)


def endpoint(port, canonical, role, index, cores):
    return {"port": port, "canonical_port": canonical, "roles": [role], "backend": "cpu",
            "device": "none", "physical_cpus": list(cores), "numa_instance": index, "test": "chat"}


def test_cpu_scope_preserves_full_source_plan():
    frontdoor = endpoint(19560, 8180, "frontdoor", 2, range(48, 96))
    vision = endpoint(19561, 8086, "worker_vision", 0, range(48))
    plan = {"endpoints": [vision, {"canonical_port": 8083}, frontdoor],
            "images": {"cpu": {"binary": "cpu"}, "hip": {"binary": "hip"}},
            "spec": {"ports": {"8180": 19560, "8086": 19561, "8083": 19524},
                     "resources": {"physical_cpus": "0-95", "gpu_devices": ["ROCm0"], "ram_gib": 224}},
            "contention_matrix_status": "stale"}
    scope = acquire.scoped_plan(plan)
    assert scope["endpoints"] == [frontdoor, vision]
    assert scope["spec"]["ports"] == {"8180": 19560, "8086": 19561}
    assert scope["spec"]["resources"] == {"physical_cpus": "0-95", "gpu_devices": [], "ram_gib": 224}
    assert scope["images"] == {"cpu": {"binary": "cpu"}}
    assert scope["contention_matrix_status"] == "stale"
    assert len(plan["spec"]["ports"]) == 3
    assert plan["spec"]["resources"]["gpu_devices"] == ["ROCm0"]
    vision["physical_cpus"].append(88)
    with pytest.raises(ValueError, match="geometry"):
        acquire.scoped_plan(plan)


def test_ratio_and_incomplete_legs():
    assert acquire.ratio(5, 7, 8, 10)["ratio"] == pytest.approx(1.2)
    for bad in (0.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            acquire.ratio(5, 7, bad, 10)
    complete = json.dumps({"timings": {"predicted_n": 100, "predicted_ms": 5600}}).encode()
    assert acquire.leg_timing(200, complete) == pytest.approx(5.6)
    with pytest.raises(ValueError, match="HTTP 503"):
        acquire.leg_timing(503, complete)
    with pytest.raises(ValueError, match="complete fixed-token"):
        acquire.leg_timing(200, complete.replace(b"100", b"99"))


def test_scan_must_fit_common_request_interval():
    states = {1: {"sent": 1, "headers": 4}, 2: {"sent": 2, "headers": 5}}
    before = {"start": 1.5, "end": 3}
    inside = {"start": 2.5, "end": 3.5}
    after = {"start": 3.5, "end": 4.5}
    assert acquire.complete_scans(states, [before, inside, after]) == [inside]
    del states[2]["headers"]
    assert acquire.complete_scans(states, [inside]) == []


def test_foreign_workload_refused_and_retained(tmp_path, monkeypatch):
    blocker = {"pid": 9, "reason": "llama workload"}
    monkeypatch.setattr(acquire.k35, "collect_process_blockers", lambda: [blocker])
    path = tmp_path / "workloads.json"
    with pytest.raises(ValueError, match="workload"):
        acquire.check_workloads(SimpleNamespace(servers=[]), path)
    assert json.loads(path.read_text())["foreign"] == [blocker]


def test_owned_workload_exemption_requires_unchanged_birth(tmp_path, monkeypatch):
    blocker = {"pid": 9, "reason": "llama workload"}
    monkeypatch.setattr(acquire.k35, "collect_process_blockers", lambda: [blocker])
    runtime = SimpleNamespace(servers=[SimpleNamespace(pid=9, birth=17)], verify_identity=lambda _: None)
    monkeypatch.setattr(acquire.runner.owned, "birth", lambda _: 17)
    acquire.check_workloads(runtime, tmp_path / "owned.json")
    monkeypatch.setattr(acquire.runner.owned, "birth", lambda _: 18)
    path = tmp_path / "changed.json"
    with pytest.raises(ValueError, match="identity"):
        acquire.check_workloads(runtime, path)
    evidence = json.loads(path.read_text())
    assert evidence["foreign"] == [blocker]
    assert evidence["identity_errors"] == {"9": "captured PID birth changed"}


@pytest.mark.parametrize("raises", [False, True])
def test_unproved_cleanup_cannot_retain_captured_status(tmp_path, raises):
    def cleanup():
        if raises:
            raise OSError("cleanup exception")
        return {"servers": {}, "spawn_unproved": True}

    result = {"status": "captured"}
    acquire.finish_cleanup(SimpleNamespace(cleanup=cleanup), tmp_path, result)
    assert result["status"] == "failed"
    assert result["cleanup_proved"] is False
    assert json.loads((tmp_path / "cleanup.json").read_text())["spawn_unproved"] is True


@pytest.mark.parametrize("mode", [None, "FILLER_SMOKE", "FILLER_DRYRUN", "FILLER_DIRECT"])
def test_native_cli_without_live_grant_refuses_before_writes(tmp_path, monkeypatch, mode):
    row_id = "contention-fixture"
    (tmp_path / "row.spec.json").write_text(json.dumps({"id": row_id}))
    for key in ("FILLER_ID", "FILLER_SMOKE", "FILLER_DRYRUN", "FILLER_DIRECT"):
        monkeypatch.delenv(key, raising=False)
    if mode:
        monkeypatch.setenv("FILLER_ID", row_id)
        monkeypatch.setenv(mode, "1")
    with pytest.raises(ValueError, match="real grant"):
        acquire.main(["--packet", str(tmp_path), "--acquire"])
    assert not (tmp_path / "out").exists()
