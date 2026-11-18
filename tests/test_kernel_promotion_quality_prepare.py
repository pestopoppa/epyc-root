"""Offline checks for the production-first prospective quality request inputs."""

from collections import Counter
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
