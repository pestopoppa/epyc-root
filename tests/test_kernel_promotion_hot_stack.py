"""Fixture checks for the static isolated hot-stack planner."""

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "scripts/benchmark/kernel_promotion_hot_stack.py"
MODULE = importlib.util.spec_from_file_location("kernel_promotion_hot_stack", SOURCE)
hot_stack = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(hot_stack)


def make_stage(root, backend="cpu"):
    candidate = {"source_commit": "1" * 40, "source_tree": "2" * 40, "branch": "experimental/test"}
    bindir = root / "bin"
    bindir.mkdir(parents=True)
    binary = bindir / "llama-server"
    binary.write_bytes(b"server")
    binary.chmod(0o700)
    for library in hot_stack.LIBRARIES + (("libggml-hip.so",) if backend == "hip" else ()):
        real_library = bindir / (library + ".1")
        real_library.write_text(library)
        (bindir / library).symlink_to(real_library.name)
    identity = root / "BUILD-IDENTITY.json"
    identity.write_text(json.dumps({
        "schema": "epyc.build-identity.v1",
        "source_sha": candidate["source_commit"], "source_tree": candidate["source_tree"],
        "branch": candidate["branch"], "kind": {"cpu": "cpu", "hip": "gpu"}[backend],
    }))
    inventory = root / "SHA256SUMS"
    inventory.write_text("".join(f"{hot_stack.digest(path)}  bin/{path.name}\n" for path in sorted(bindir.iterdir())))
    return candidate, {
        "root": str(root), "inventory": inventory.name, "identity_sha256": hot_stack.digest(identity),
        "inventory_sha256": hot_stack.digest(inventory),
    }


@pytest.mark.parametrize("backend", ["cpu", "hip"])
def test_stage_accepts_pinned_inventory_and_local_aliases(tmp_path, backend):
    stage = tmp_path / "image"
    candidate, image = make_stage(stage, backend)
    result = hot_stack.verify_stage(image, candidate, backend, [])
    assert result["binary"] == str(stage / "bin/llama-server")
    assert result["library_dir"] == str(stage / "bin")


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        ("bytes", "changed cpu stage member"),
        ("metadata", "invalid or changed pin"),
        ("unlisted", "unlisted files"),
        ("symlink", "escapes candidate"),
        ("production-root", "overlaps a production"),
        ("production-binary", "hardlinked to the production"),
        ("source", "build identity differs"),
    ],
)
def test_stage_refuses_bad_custody(tmp_path, mutation, failure):
    stage = tmp_path / "stage"
    candidate, image = make_stage(stage)
    production = []
    if mutation == "bytes":
        (stage / "bin/libggml.so.1").write_text("changed")
    elif mutation == "metadata":
        (stage / "BUILD-IDENTITY.json").write_text("{}")
    elif mutation == "unlisted":
        (stage / "bin/extra.so").write_text("unexpected")
    elif mutation == "symlink":
        outside = tmp_path / "libggml.so"
        outside.write_text("libggml.so")
        link = stage / "bin/libggml.so"
        link.unlink()
        link.symlink_to(outside)
    elif mutation == "production-root":
        production.append(stage)
    elif mutation == "production-binary":
        production.append(tmp_path / "production")
        production[0].mkdir()
        (production[0] / "llama-server").hardlink_to(stage / "bin/llama-server")
    else:
        candidate["source_commit"] = "3" * 40

    with pytest.raises(ValueError, match=failure):
        hot_stack.verify_stage(image, candidate, "cpu", production)


def test_stage_refuses_alias_root(tmp_path):
    stage = tmp_path / "stage"
    candidate, image = make_stage(stage)
    link = tmp_path / "link"
    link.symlink_to(stage)
    image["root"] = str(link)
    with pytest.raises(ValueError, match="canonical directory"):
        hot_stack.verify_stage(image, candidate, "cpu", [])


COMMAND = [
    "/production/llama-server", "-m", "/models/model.gguf", "--host", "127.0.0.1",
    "--port", "8070", "--device", "none", "--slot-save-path", "/production/slots", "-np", "16",
]


def isolate(command=COMMAND):
    return hot_stack.isolate_argv(command, 8070, 19520, {"binary": "/candidate/llama-server"}, Path("/isolated/slots"))


def test_isolation_rewrites_only_binary_port_and_slot_path():
    assert isolate() == [
        "/candidate/llama-server", "-m", "/models/model.gguf", "--host", "127.0.0.1",
        "--port", "19520", "--device", "none", "--slot-save-path", "/isolated/slots", "-np", "16",
    ]
    assert COMMAND[0] == "/production/llama-server"


@pytest.mark.parametrize(
    ("change", "failure"),
    [
        (lambda argv: ["/production/whisper-server", *argv[1:]], "llama-server command"),
        (lambda argv: [*argv, "--port=8070"], "expected one --port"),
        (lambda argv: [*argv, "--hf-repo", "test/repo"], "external model source"),
        (lambda argv: [*argv, "--log-file", "/production/log"], "unsupported server path"),
        (lambda argv: [*argv[:4], "0.0.0.0", *argv[5:]], "loopback endpoint"),
    ],
)
def test_isolation_rejects_ambiguous_or_external_launches(change, failure):
    with pytest.raises(ValueError, match=failure):
        isolate(change(COMMAND))


@pytest.mark.parametrize(
    ("ports", "tests", "failure"),
    [
        ({"8070": 19520}, {"8070": "chat"}, "port map"),
        ({"8070": 19520, "8090": 19520}, {"8070": "chat", "8090": "embedding"}, "duplicate isolated port"),
        ({"8070": 19520, "8090": 8089}, {"8070": "chat", "8090": "embedding"}, "non-production ports"),
        ({"8070": 19520, "8090": True}, {"8070": "chat", "8090": "embedding"}, "non-production ports"),
        ({"8070": 19520, "8090": 19521}, {"8070": "chat", "8090": "chat"}, "must use embedding"),
    ],
)
def test_endpoint_map_refuses_missing_ambiguous_or_production_ports(ports, tests, failure):
    with pytest.raises(ValueError, match=failure):
        hot_stack.validate_endpoints(
            {"ports": ports, "endpoint_tests": tests},
            [{"port": 8070}, {"port": 8090, "embedding": True}],
            {8070, 8089, 8090},
        )


def test_endpoint_preserves_logical_binding_and_claims_physical_sibling(tmp_path):
    def build_command(role, port, *, prepare_runtime_dirs, **kwargs):
        assert not prepare_runtime_dirs
        assert (role, port) == ("critic", 8070)
        return [*COMMAND[:8], "ROCm0", *COMMAND[9:]]

    def build_env(role, base):
        return base | {"LD_LIBRARY_PATH": "/production/cpu", "OMP_NUM_THREADS": "8"}

    def apply_affinity(env, prefix):
        assert prefix == ["numactl", "--membind=3", "--", "taskset", "-c", "184-191"]
        env["HSA_OVERRIDE_CPU_AFFINITY_DEBUG"] = "0"

    launch = SimpleNamespace(build_server_command=build_command, build_launch_env=build_env, apply_pinned_launch_env=apply_affinity)
    numa = SimpleNamespace(
        _numa_prefix=lambda role, index: ["numactl", "--membind=3", "--", "taskset", "-c", "184-191"],
        _parse_cpus=lambda cpus: set(range(184, 192)) if cpus == "184-191" else set(range(88, 96)),
    )
    manifest = SimpleNamespace(_HOST_LOGICAL_CPUS=192, _smt_fold=lambda cpus: {cpu % 96 for cpu in cpus})
    endpoint = hot_stack.build_endpoint(
        {"ports": {"8070": 19520}, "endpoint_tests": {"8070": "chat"}}, tmp_path,
        {"port": 8070, "roles": ["critic"]}, manifest, launch, numa,
        SimpleNamespace(get_role=lambda role: role),
        {"hip": {"binary": "/hip/llama-server", "library_dir": "/hip"}},
    )
    assert endpoint["logical_cpus"] == list(range(184, 192))
    assert endpoint["physical_cpus"] == list(range(88, 96))
    assert endpoint["env"]["LD_LIBRARY_PATH"] == "/hip:/usr/lib/llvm-20/lib"
    assert endpoint["env"]["HSA_OVERRIDE_CPU_AFFINITY_DEBUG"] == "0"
    assert endpoint["argv"][6] == "/hip/llama-server"
    assert endpoint["endpoint"] == "http://127.0.0.1:19520"
    assert endpoint["state_dir"] == str(tmp_path / "state/19520")
    assert endpoint["log"] == str(tmp_path / "logs/19520.log")
    hot_stack.validate_claim({"physical_cpus": "88-95", "gpu_devices": ["ROCm0"], "ram_gib": 100}, [endpoint], numa, 96)
    with pytest.raises(ValueError, match="physical CPU IDs"):
        hot_stack.validate_claim({"physical_cpus": "184-191", "gpu_devices": ["ROCm0"], "ram_gib": 100}, [endpoint], numa, 96)
    with pytest.raises(ValueError, match="GPU claim differs"):
        hot_stack.validate_claim({"physical_cpus": "88-95", "gpu_devices": [], "ram_gib": 100}, [endpoint], numa, 96)


def test_plan_artifact_is_exclusive(tmp_path):
    output = tmp_path / "plan.json"
    hot_stack.write_new(output, {"status": "prepared_only"})
    with pytest.raises(FileExistsError):
        hot_stack.write_new(output, {"status": "changed"})
    assert hot_stack.read_json(output) == {"status": "prepared_only"}


def test_cli_cannot_execute_a_plan():
    with pytest.raises(SystemExit) as refused:
        hot_stack.main(["--spec", "sample", "--output-dir", "sample-output", "--apply"])
    assert refused.value.code == 2


def test_cli_preserves_rowflow_provenance_without_ambient_loader(tmp_path, monkeypatch):
    def prepare(spec, output):
        assert spec == {"fixture": True}
        assert os.environ["FILLER_ID"] == "fixture-row"
        assert "LD_LIBRARY_PATH" not in os.environ
        assert "LD_PRELOAD" not in os.environ
        assert os.environ["ARTIFACT_FINGERPRINT_LEDGER"] == str(output / "artifact-ledger.json")
        return {"status": "prepared_only"}

    monkeypatch.setattr(hot_stack, "SCRATCH", tmp_path)
    monkeypatch.setattr(hot_stack, "prepare_plan", prepare)
    monkeypatch.setenv("FILLER_ID", "fixture-row")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/production/cpu")
    monkeypatch.setenv("LD_PRELOAD", "/ambient/library.so")
    spec = tmp_path / "spec.json"
    spec.write_text('{"fixture": true}')
    output = tmp_path / "run"
    assert hot_stack.main(["--spec", str(spec), "--output-dir", str(output)]) == 0
    assert hot_stack.read_json(output / "plan.json") == {"status": "prepared_only"}
    assert os.environ["LD_LIBRARY_PATH"] == "/production/cpu"
    assert os.environ["LD_PRELOAD"] == "/ambient/library.so"


def test_stack_inputs_refuse_changed_config(tmp_path, monkeypatch):
    def fake_git(root, *argv):
        assert root == tmp_path
        return "1" * 40 if argv == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(hot_stack, "ORCHESTRATOR", tmp_path)
    monkeypatch.setattr(hot_stack, "git", fake_git)
    config = {}
    for filename in hot_stack.CONFIG_FILES:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
        config[filename] = hot_stack.digest(path)
    spec = {"orchestrator_commit": "1" * 40, "config_sha256": config}
    assert hot_stack.check_stack_inputs(spec) == tmp_path
    (tmp_path / hot_stack.CONFIG_FILES[0]).write_text("changed")
    with pytest.raises(ValueError, match="invalid or changed pin"):
        hot_stack.check_stack_inputs(spec)


def test_spec_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text('{"schema": "one", "schema": "two"}')
    with pytest.raises(ValueError, match="duplicate JSON"):
        hot_stack.read_json(path)
