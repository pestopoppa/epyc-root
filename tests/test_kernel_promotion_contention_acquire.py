"""Software fixtures for the isolated CPU contention acquisition."""

import hashlib
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


@pytest.mark.parametrize("options, error", [
    (["--acquire", "--api-role", "worker_general"], "invalid choice"),
    (["--validate-inputs", "--api-role", "frontdoor"], "--api-role requires --acquire"),
    (["--acquire", "--api-role", "worker_vision", "--api-image", "/prepared.png"], "paired SHA-256"),
    (["--acquire", "--api-role", "frontdoor", "--api-image", "/prepared.png", "--api-image-sha256", "a" * 64],
     "--api-image requires the worker_vision role"),
])
def test_api_cli_rejects_unscoped_role_and_non_acquire_mode(tmp_path, capsys, options, error):
    with pytest.raises(SystemExit) as exc:
        acquire.main(["--packet", str(tmp_path), *options])
    assert exc.value.code == 2
    assert error in capsys.readouterr().err


@pytest.fixture
def native_api(tmp_path, monkeypatch):
    row_id = "fixture-native-api"
    (tmp_path / "row.spec.json").write_text(json.dumps({"id": row_id}))
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text("unchanged scoped topology fixture\n")
    frontdoor = endpoint(19560, 8180, "frontdoor", 2, range(48, 96))
    vision = endpoint(19561, 8086, "worker_vision", 0, range(48))
    projector = tmp_path / "mmproj.gguf"
    projector.write_bytes(b"small projector fixture")
    vision.update(argv=["llama-server", "--mmproj", str(projector)],
                  models=[{"path": str(projector), "stat": acquire.runner.evidence.stat_identity(projector.stat())}])
    plan = {"endpoints": [vision, frontdoor], "images": {"cpu": {}},
            "spec": {"resources": {"gpu_devices": []},
                     "config_sha256": {matrix.name: acquire.planner.digest(matrix)}},
            "contention_matrix_status": "stale", "topology_hash": "fixture"}
    for item in plan["endpoints"]:
        item["endpoint"] = f'http://127.0.0.1:{item["port"]}'
    plan["endpoint_manifest"] = {
        "schema": acquire.runner.isolated_api.MANIFEST_SCHEMA,
        "endpoints": [{"role": item["roles"][0], "kind": item["test"], "base_url": item["endpoint"]}
                      for item in plan["endpoints"]],
    }
    for item in plan["endpoints"]:
        log = tmp_path / f'{item["port"]}.log'
        log.touch()
        item["log"] = str(log)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    plan_sha = acquire.planner.digest(plan_path)
    events = []
    fixture = SimpleNamespace(plan=plan, events=events, api_fails=False, cleanup_fails=False, projector=projector)

    class Runtime:
        def __init__(self, selected, path, output, admission, startup_timeout, request_timeout, *, plan_sha256):
            self.output = output
            self.plan_sha256 = plan_sha256
            self.servers = []

        def preflight(self):
            pass

        def verify_model_inputs(self):
            pass

        def start(self, item):
            server = SimpleNamespace(port=item["port"], endpoint=item)
            self.servers.append(server)
            return server

        def ready(self, server):
            return {}

        def check(self):
            pass

        def isolated_api_smoke(self, role, port, *, image=None):
            events.append((role, port) if image is None else (role, port, image))
            plan_bytes = (self.output / "plan.json").read_bytes()
            assert plan_bytes == plan_path.read_bytes()
            assert hashlib.sha256(plan_bytes).hexdigest() == self.plan_sha256
            output = self.output / "isolated-api" / "consumer"
            output.mkdir(parents=True)
            (output / "response.body").write_text('{"response":"raw"}')
            if fixture.api_fails:
                raise ValueError("api fixture refusal")

        def cleanup(self):
            events.append("cleanup")
            return {"servers": {}, "spawn_unproved": fixture.cleanup_fails}

    def phase(runtime, directory, servers):
        events.append(directory.name)
        return {server.endpoint["roles"][0]: 1.0 for server in servers}

    monkeypatch.setenv("FILLER_ID", row_id)
    for key in ("FILLER_SMOKE", "FILLER_DRYRUN", "FILLER_DIRECT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(acquire, "load_prepared", lambda _: (plan_path, plan_sha, plan_path.read_bytes(), plan))
    monkeypatch.setattr(acquire, "verify_prepared_inputs", lambda _: None)
    monkeypatch.setattr(acquire, "check_workloads", lambda *_: None)
    monkeypatch.setattr(acquire, "capture_phase", phase)
    monkeypatch.setattr(acquire.planner, "ORCHESTRATOR", tmp_path)
    monkeypatch.setattr(acquire.planner, "check_stack_inputs", lambda _: None)
    monkeypatch.setattr(acquire.runner, "MATRIX_CONFIG", matrix.name)
    monkeypatch.setattr(acquire.runner, "LINKAGE", matrix)
    monkeypatch.setattr(acquire.runner, "SIGNALS", ())
    monkeypatch.setattr(acquire.runner, "Runtime", Runtime)
    monkeypatch.setattr(acquire.runner, "Admission", lambda _: SimpleNamespace(witness=lambda: {}))
    monkeypatch.setattr(acquire.runner.evidence, "host_snapshot", dict)
    return fixture


@pytest.mark.parametrize("role, port, fails", [(None, None, False), ("frontdoor", 19560, True),
                                                ("worker_vision", 19561, False)])
def test_native_api_runs_after_all_legs_with_raw_custody_and_cleanup(tmp_path, native_api, role, port, fails):
    native_api.api_fails = fails
    args = ["--packet", str(tmp_path), "--acquire"]
    if role is not None:
        args.extend(["--api-role", role])
    assert acquire.main(args) == (2 if fails else 0)
    result = json.loads((tmp_path / "out" / "RESULT.json").read_text())
    assert result["status"] == ("failed" if fails else "captured")
    assert result["cleanup_proved"] is True
    phases = ["solo-frontdoor", "solo-worker_vision", "parallel"]
    if role is None:
        assert "isolated_api" not in result
        assert "observation/plan.json" not in result["files"]
    else:
        phases.append((role, port))
        assert result["isolated_api"] == {"role": role, "requested_port": port,
                                         "status": "failed" if fails else "pass"}
        capture = Path(result["capture_dir"]) / "observation/isolated-api/consumer/response.body"
        assert capture.read_text() == '{"response":"raw"}'
        assert result["files"]["observation/isolated-api/consumer/response.body"] == acquire.planner.digest(capture)
        assert "observation/plan.json" in result["files"]
    assert native_api.events == phases + ["cleanup"]


def test_native_api_rejects_role_at_wrong_isolated_port(tmp_path, native_api):
    frontdoor = next(item for item in native_api.plan["endpoints"] if item["roles"] == ["frontdoor"])
    frontdoor["port"] = 19521
    assert acquire.main(["--packet", str(tmp_path), "--acquire", "--api-role", "frontdoor"]) == 2
    result = json.loads((tmp_path / "out" / "RESULT.json").read_text())
    assert result["isolated_api"] == {"role": "frontdoor", "requested_port": 19560, "status": "not_run"}
    assert "isolated API role port changed" in result["failure"]
    assert result["cleanup_proved"] is True
    assert native_api.events == []


def test_successful_api_response_cannot_override_unproved_server_cleanup(tmp_path, native_api):
    native_api.cleanup_fails = True
    assert acquire.main(["--packet", str(tmp_path), "--acquire", "--api-role", "frontdoor"]) == 2
    result = json.loads((tmp_path / "out/RESULT.json").read_text())
    assert result["status"] == "failed"
    assert result["isolated_api"]["status"] == "pass"
    assert result["cleanup_proved"] is False
    assert "observation/isolated-api/consumer/response.body" in result["files"]
    assert native_api.events[-2:] == [("frontdoor", 19560), "cleanup"]


@pytest.mark.parametrize("mutation", [None, "image", "mmproj"])
def test_native_image_options_bind_prepared_inputs_before_any_leg(tmp_path, native_api, mutation):
    image = tmp_path / "red-square.png"
    image.write_bytes(acquire.runner.isolated_api.PNG_SIGNATURE + b"fixture")
    pin = {"path": str(image), "sha256": acquire.planner.digest(image)}
    if mutation == "image":
        image.write_bytes(image.read_bytes() + b"changed")
    if mutation == "mmproj":
        native_api.projector.write_bytes(b"changed")
    args = ["--packet", str(tmp_path), "--acquire", "--api-role", "worker_vision",
            "--api-image", pin["path"], "--api-image-sha256", pin["sha256"]]
    assert acquire.main(args) == (0 if mutation is None else 2)
    result = acquire.planner.read_json(tmp_path / "out" / "RESULT.json")
    if mutation is None:
        assert result["isolated_api"]["image"] == pin
        assert result["isolated_api"]["mmproj"]["path"] == str(native_api.projector)
        assert native_api.events[-2:] == [("worker_vision", 19561, pin), "cleanup"]
    else:
        assert result["status"] == "failed" and "changed" in result["failure"]
        assert native_api.events == []
