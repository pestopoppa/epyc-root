"""Offline checks for the production-first prospective quality request inputs."""

from collections import Counter
import base64
from datetime import UTC, datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/benchmark"))
import kernel_promotion_quality_prepare as prepare


INPUTS = prepare.ROOT / "data/vidya/quality-pack-live-20261118/request_inputs.json"
INPUTS_SHA = "e9b8d9d40b88851de2299b8fba372c8e0f5920abd47315747251a87313855914"


def test_materializes_original_requests_and_the_repaired_banks():
    pack = prepare.materialize(INPUTS, INPUTS_SHA)
    source = prepare.parity._parse(INPUTS.read_bytes())
    assert set(row["id"] for row in pack["shapes"]) == prepare.live.PROFILES.keys()
    assert all("generation_path_sha256" not in row for row in pack["shapes"])
    items = pack["items"]
    assert Counter(row["shape"] for row in items) == {
        profile: 8 if profile == "dspark-dflash" else 4 for profile in prepare.live.PROFILES
    }
    for profile, record in source["profiles"].items():
        expected = {item["id"]: item["request_body"] for item in prepare.read_source(record["source"])["items"]}
        assert {row["id"]: row["request_body"] for row in items if row["shape"] == profile} == expected
    repaired = next(row for row in items if row["id"] == "ingest-document-reconciliation-signed-record")
    assert repaired["validator"]["expected"] == {"annex": "SOUTH", "governing_record": "E59"}
    assert {row["fixture"] for row in items if row["fixture"]} == {"loader-reshape", "recurrent-state"}
    assert {row["request_body"][prepare.parity.CAP_KEY] for row in items if row["dflash_pair"]} == {0, 7}
    assert len(pack["models"]) == 8
    assert len(pack["shape_model_paths"]["architect-general-hip"]) == 3


def test_rejects_changed_request_or_source_pin(tmp_path):
    inputs = prepare.parity._parse(INPUTS.read_bytes())
    path = tmp_path / "inputs.json"
    entry = inputs["profiles"]["frontdoor-cpu-moe-mtp"]
    entry["request_sha256"]["json"] = "0" * 64
    path.write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match="changed input pin"):
        prepare.materialize(path, INPUTS_SHA)
    with pytest.raises(ValueError, match="canonical bytes differ"):
        prepare.materialize(path, prepare.planner.digest(path))

    entry["source"]["sha256"] = "0" * 64
    path.write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match="changed original plan bytes"):
        prepare.materialize(path, prepare.planner.digest(path))


def test_builds_all_seven_original_recipes_with_dedicated_loopback_ports(tmp_path, monkeypatch):
    recipes = prepare.recipe_inputs(INPUTS_SHA)
    inputs = prepare.parity._parse(INPUTS.read_bytes())["profiles"]
    assert set(recipes) == set(inputs)
    ports = {profile: 19100 + index for index, profile in enumerate(recipes)}
    resources = {"physical_cpus": "0-95", "gpu_devices": ["ROCm0"], "ram_gib": 112}
    spec = {"schema": prepare.planner.QUALITY_SPEC_SCHEMA, "request_inputs_sha256": INPUTS_SHA,
            "ports": ports, "resources": resources}
    role_ports = {recipe["mapping"]["role"]: recipe["mapping"]["canonical_port"] for recipe in recipes.values()}
    manifest = SimpleNamespace(PORT_MAP=role_ports, _HOST_LOGICAL_CPUS=192,
                               _smt_fold=lambda cpus: {cpu % 96 for cpu in cpus})
    images = {backend: {"binary": f"/{backend}/llama-server", "library_dir": f"/{backend}"}
              for backend in ("cpu", "hip")}
    checked_models = []
    checked_templates = []
    monkeypatch.setattr(prepare.live.evidence, "verify_models", checked_models.append)
    monkeypatch.setattr(prepare.live.runner, "canonical_file", lambda path: path)
    monkeypatch.setattr(prepare.planner, "check_pin", lambda path, sha: checked_templates.append((str(path), sha)))

    endpoints = prepare.prepare_quality_endpoints(spec, tmp_path, images, set(role_ports.values()), manifest)
    plan = {"spec": spec, "endpoints": endpoints, "images": images}
    shapes = {shape["id"]: shape for shape in prepare.materialize(INPUTS, INPUTS_SHA)["shapes"]}
    assert len({endpoint["port"] for endpoint in endpoints}) == 7
    for profile, entry in recipes.items():
        record = inputs[profile]
        recipe = prepare.read_source(record["source"])["recipes"][record["recipe"]]
        assert entry["args"] == recipe["args"]
        endpoint = prepare.live.endpoint_for(plan, entry["mapping"], shapes[profile])
        assert endpoint["port"] == ports[profile]
        assert endpoint["argv"][13:] == recipe["args"]
        assert endpoint["argv"][11:13] == ["--threads", str(len(entry["logical_cpus"]))]
    assert len(checked_models) == 7
    assert len(checked_models[list(recipes).index("architect-general-hip")]) == 3
    assert len(checked_templates) == 6
    vision = next(endpoint for endpoint in endpoints if endpoint["quality_profile"] == "worker-vision-hip-mmproj")
    assert vision["env"]["MTMD_BACKEND_DEVICE"] == "ROCm0"

    with pytest.raises(ValueError, match="at least 112 GiB"):
        prepare.prepare_quality_endpoints(spec | {"resources": resources | {"ram_gib": 111}}, tmp_path,
                                          images, set(role_ports.values()), manifest)
    frontdoor = "frontdoor-cpu-moe-mtp"
    with pytest.raises(ValueError, match="non-production ports"):
        prepare.prepare_quality_endpoints(spec | {"ports": ports | {frontdoor: 8070}}, tmp_path,
                                          images, set(role_ports.values()), manifest)


def test_quality_plan_dispatch_regenerates_and_refuses_changed_archive(tmp_path, monkeypatch):
    planner = prepare.planner
    monkeypatch.setattr(sys, "path", sys.path.copy())
    server = ModuleType("scripts.server")
    server.orchestrator_stack = server.stack_prewarm = SimpleNamespace()
    server.stack_numa = SimpleNamespace(NUMA_CONFIG={})
    server.stack_manifest = SimpleNamespace(
        PORT_MAP={role: port for port, role, _ in prepare.RECIPE_LAYOUT.values()},
        AUX_SERVICES={}, HOT_SERVERS=[], WARM_SERVERS=[], _HOST_LOGICAL_CPUS=192,
        _smt_fold=lambda cpus: {cpu % 96 for cpu in cpus},
    )
    scheduling = ModuleType("src.scheduling")
    matrix_status = Enum("MatrixStatus", {"OK": "ok", "STALE": "stale"})
    matrix = SimpleNamespace(topology_hash="topology", measured_at=datetime.now(UTC).isoformat())
    scheduling.contention = SimpleNamespace(
        load_contention_matrix=lambda path: matrix,
        topology_fingerprint_for_matrix=lambda numa, matrix: "topology",
        matrix_status=lambda *args, **kwargs: matrix_status.OK,
        MatrixStatus=matrix_status,
        MATRIX_STALENESS_DAYS=30,
    )
    for name, module in (("scripts", ModuleType("scripts")), ("scripts.server", server),
                         ("src", ModuleType("src")), ("src.scheduling", scheduling)):
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(planner, "check_stack_inputs", lambda spec: tmp_path)
    monkeypatch.setattr(planner, "production_runtime_dirs", lambda: [])
    monkeypatch.setattr(planner, "verify_stage", lambda image, candidate, backend, dirs: image)
    monkeypatch.setattr(planner, "digest", lambda path: "c" * 64)
    monkeypatch.setattr(planner, "check_pin", lambda path, sha: None)
    monkeypatch.setattr(prepare.live.runner, "canonical_file", lambda path: path)
    monkeypatch.setattr(prepare.live.evidence, "verify_models", lambda pins: None)
    images = {backend: {"root": f"/{backend}", "binary": f"/{backend}/llama-server", "library_dir": f"/{backend}"}
              for backend in ("cpu", "hip")}
    spec = {
        "schema": planner.QUALITY_SPEC_SCHEMA, "request_inputs_sha256": INPUTS_SHA, "config_sha256": {},
        "orchestrator_commit": "d" * 40, "candidate": {"source_commit": "a" * 40,
                                                     "source_tree": "b" * 40, "branch": "fixture", **images},
        "ports": {profile: 19200 + index for index, profile in enumerate(prepare.RECIPE_LAYOUT)},
        "resources": {"physical_cpus": "0-95", "gpu_devices": ["ROCm0"], "ram_gib": 112},
    }
    plan = planner.prepare_plan(spec, tmp_path)
    assert len(plan["endpoints"]) == 7
    assert prepare.live.runner.regenerate(plan, tmp_path, tmp_path / "ledger.json") == plan
    fresh_time = matrix.measured_at
    matrix.measured_at = (datetime.now(UTC) - timedelta(days=31)).isoformat()
    stale = planner.prepare_plan(spec, tmp_path)
    assert stale["contention_matrix_status"] == "stale"
    with pytest.raises(ValueError, match="matrix must be fresh"):
        prepare.live.runner.regenerate(stale, tmp_path, tmp_path / "ledger.json")
    ordinary = {key: value for key, value in spec.items() if key != "request_inputs_sha256"}
    ordinary.update(schema=planner.SPEC_SCHEMA, numa_mode="full", warm_roles=[], endpoint_tests={})
    monkeypatch.setattr(planner, "prepare_serving_endpoints", lambda *args: (stale["endpoints"], {}))
    assert planner.prepare_plan(ordinary, tmp_path)["contention_matrix_status"] == "stale"
    matrix.measured_at = fresh_time

    record = prepare.parity._parse(INPUTS.read_bytes())["profiles"]["architect-critic-cpu-mtp"]
    archive = prepare.ROOT / record["source"]["path"]
    wrapper = prepare.parity._parse(archive.read_bytes())
    source = prepare.read_source(record["source"])
    source["recipes"][record["recipe"]]["args"][-1] = "5"
    modified = prepare.parity.pack_bytes(source)
    wrapper.update(bytes_b64=base64.b64encode(modified).decode("ascii"), sha256=prepare.live.sha(modified))
    local = tmp_path / record["source"]["path"]
    local.parent.mkdir(parents=True)
    local.write_bytes(prepare.parity.pack_bytes(wrapper))
    monkeypatch.setattr(prepare, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="changed original plan bytes"):
        prepare.live.runner.regenerate(plan, tmp_path, tmp_path / "ledger.json")


def test_stale_plan_refuses_to_emit_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(prepare.planner, "SCRATCH", tmp_path)
    directory = tmp_path / "production"
    directory.mkdir(mode=0o700)
    plan = directory / "plan.json"
    plan.write_text(json.dumps({"schema": prepare.planner.PLAN_SCHEMA, "status": "prepared_only",
                                "contention_matrix_status": "stale"}))
    pinned = [str(plan), prepare.planner.digest(plan)]
    output = tmp_path / "config.json"
    rc = prepare.main(["config", "--inputs", str(INPUTS), "--inputs-sha256", INPUTS_SHA,
                       "--production-plan", *pinned, "--candidate-plan", *pinned,
                       "--mappings", *pinned, "--orchestrator", str(tmp_path),
                       "--source-repository", str(tmp_path), "--production-attestation", str(tmp_path / "freeze.json"),
                       "--capture-commit", "0" * 40, "--observation-dir", str(tmp_path / "observation"),
                       "--startup-timeout-s", "240", "--request-timeout-s", "360", "--out", str(output)])
    assert rc == 2
    assert "fresh matrix" in capsys.readouterr().err
    assert not output.exists()


def test_assembly_pins_durable_source_and_both_arm_mappings(tmp_path, monkeypatch):
    live = prepare.live
    monkeypatch.setattr(prepare.planner, "SCRATCH", tmp_path)
    orchestrator = tmp_path / "orchestrator"
    orchestrator.mkdir()
    monkeypatch.setattr(prepare.planner, "ORCHESTRATOR", orchestrator)
    repository = tmp_path / "durable-root"
    script = repository / "scripts/benchmark" / Path(live.__file__).name
    script.parent.mkdir(parents=True)
    script.write_bytes(Path(live.__file__).read_bytes())
    for command in (["init", "-q"], ["add", "scripts"],
                    ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "-c", "commit.gpgsign=false", "commit", "-qm", "Capture source"]):
        subprocess.run(["git", "-C", str(repository), *command], check=True, capture_output=True)
    commit = prepare.planner.git(repository, "rev-parse", "HEAD")
    attestation = tmp_path / "v10-freeze.json"
    attestation.write_text("{}")

    inputs = prepare.materialize(INPUTS, INPUTS_SHA)
    archive_models = inputs["shape_model_paths"]
    general_shards = archive_models["architect-general-hip"]
    shard_paths = {general_shards[0]: [Path(path) for path in general_shards]}
    registry = ModuleType("src.registry")
    registry.artifact_integrity = SimpleNamespace(
        __file__=str(orchestrator / "src/registry/artifact_integrity.py"),
        shard_paths=lambda path: shard_paths.get(path, [Path(path)]),
    )
    monkeypatch.setitem(sys.modules, "src", ModuleType("src"))
    monkeypatch.setitem(sys.modules, "src.registry", registry)
    monkeypatch.setattr(live.evidence, "verify_models", lambda models: None)
    monkeypatch.setattr(live.runner, "verify_models", lambda endpoint: None)
    regenerated = []
    monkeypatch.setattr(live.runner, "regenerate", lambda plan, directory, ledger: regenerated.append(directory))
    freezes = []
    monkeypatch.setattr(live, "verify_production", lambda plan, path: freezes.append(path))
    monkeypatch.setattr(live, "tool_files", lambda: {"comparator": Path(prepare.parity.__file__)})
    monkeypatch.setattr(live, "shape_digests", lambda plan, endpoint, shape, integrity, models: {
        "model_sha256": "1" * 64, "recipe_sha256": "2" * 64, "endpoint_semantics_sha256": "3" * 64,
        "generation_path_sha256": "4" * 64, "prompt_template_sha256": inputs["template_sha256"][shape["id"]],
    })

    mappings, ports, plans = {}, {}, {}
    for arm, digit in (("production", "a"), ("candidate", "b")):
        directory = tmp_path / arm
        directory.mkdir(mode=0o700)
        images = {backend: {"binary": str(directory / backend / "llama-server"), "binary_sha256": digit * 64}
                  for backend in ("cpu", "hip")}
        endpoints = []
        for index, shape in enumerate(inputs["shapes"]):
            profile = shape["id"]
            role, backend, spec = live.PROFILES[profile]
            role, backend = role or "dflash", backend or "cpu"
            canonical, isolated = 8000 + index, 19000 + index
            ports[str(canonical)] = isolated
            mappings[profile] = {"canonical_port": canonical, "numa_instance": 0, "role": role,
                                 "path": shape["endpoint"]}
            models = archive_models[profile]
            argv = ["fixture"] * 6 + [images[backend]["binary"], "--port", str(isolated), "--host", "127.0.0.1",
                                      "--spec-type", spec or "none"]
            if profile == "dspark-dflash":
                argv.extend(["-np", "1", "--spec-draft-n-max", str(shape["validated_cap"]), "-md", models[1]])
            if profile == "worker-vision-hip-mmproj":
                argv.extend(["--mmproj", models[1]])
            launch_models = models[:1] if models[0] in shard_paths else models
            endpoints.append({"canonical_port": canonical, "port": isolated, "roles": [role], "numa_instance": 0,
                              "test": "chat", "backend": backend, "endpoint": f"http://127.0.0.1:{isolated}",
                              "argv": argv, "models": [{"path": path} for path in launch_models]})
        plan = directory / "plan.json"
        plan.write_text(json.dumps({"schema": prepare.planner.PLAN_SCHEMA, "status": "prepared_only",
                                    "contention_matrix_status": "ok", "endpoints": endpoints, "images": images,
                                    "spec": {"ports": ports, "resources": {"physical_cpus": "0-95"},
                                             "candidate": {"source_commit": digit * 40, "source_tree": digit * 40}}}))
        plans[arm] = [str(plan), prepare.planner.digest(plan)]
    mapping_file = tmp_path / "mappings.json"
    mapping_file.write_text(json.dumps(mappings))
    output = tmp_path / "config.json"
    assert prepare.main(["config", "--inputs", str(INPUTS), "--inputs-sha256", INPUTS_SHA,
                         "--production-plan", *plans["production"], "--candidate-plan", *plans["candidate"],
                         "--mappings", str(mapping_file), prepare.planner.digest(mapping_file),
                         "--orchestrator", str(orchestrator), "--source-repository", str(repository),
                         "--production-attestation", str(attestation), "--capture-commit", commit,
                         "--observation-dir", str(tmp_path / "observation"), "--startup-timeout-s", "240",
                         "--request-timeout-s", "360", "--out", str(output)]) == 0
    config = prepare.parity._parse(output.read_bytes())
    assert config["source_repository"] == str(repository)
    assert config["production_attestation"] == str(attestation) and freezes == [attestation]
    assert config["capture_source"]["commit"] == commit
    assert config["mappings"] == mappings
    assert regenerated == [tmp_path / "production", tmp_path / "candidate"]
    for arm, scope in config["arms"].items():
        assert [scope["plan"], scope["plan_sha256"]] == plans[arm]
        assert set(scope["runtime"]) == set(mappings)
