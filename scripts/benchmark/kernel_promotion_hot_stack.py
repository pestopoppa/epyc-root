#!/usr/bin/env python3
"""Prepare a read-only, isolated command plan for a sealed promotion candidate."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SPEC_SCHEMA = "epyc.kernel_promotion_hot_stack_spec.v1"
QUALITY_SPEC_SCHEMA = "epyc.kernel_promotion_quality_stack_spec.v1"
PLAN_SCHEMA = "epyc.kernel_promotion_hot_stack_plan.v1"
ORCHESTRATOR = Path("/mnt/raid0/llm/epyc-orchestrator")
SCRATCH = Path("/mnt/raid0/llm/tmp")
PRODUCTION = Path("/mnt/raid0/llm/kernels/production")
CONFIG_FILES = (
    "orchestration/launch_manifest.yaml",
    "orchestration/stack_topology.yaml",
    "orchestration/model_registry.yaml",
    "orchestration/derived/stack_priors.yaml",
    "orchestration/contention_matrix.yaml",
)
LAUNCHER_FILES = (
    "scripts/server/orchestrator_stack.py",
    "scripts/server/stack_manifest.py",
    "scripts/server/stack_numa.py",
    "scripts/server/stack_env.py",
    "scripts/server/stack_prewarm.py",
    "scripts/server/launch_affinity.py",
)
LLVM_LIBRARY_DIR = "/usr/lib/llvm-20/lib"
LIBRARIES = (
    "libggml-base.so", "libggml-cpu.so", "libggml.so", "libllama-common.so",
    "libllama-server-impl.so", "libllama.so", "libmtmd.so",
)
MODEL_FLAGS = ("-m", "-md", "--mmproj")
ROWFLOW_ENV = ("FILLER_ID", "FILLER_STOPFILE", "FILLER_DEADLINE", "FILLER_GPU_FENCE")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def validate_keys(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), f"invalid {label} keys")


def unique_keys(items):
    result = dict(items)
    require(len(result) == len(items), "duplicate JSON key")
    return result


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_keys)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_hash(value, length=64):
    return isinstance(value, str) and re.fullmatch(rf"[a-f0-9]{{{length}}}", value) is not None


def check_pin(path, expected):
    require(is_hash(expected) and path.is_file() and digest(path) == expected, f"invalid or changed pin: {path}")


def git(root, *args):
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        check=True, timeout=20, capture_output=True, text=True,
    ).stdout.strip()


def check_stack_inputs(spec):
    root = ORCHESTRATOR.resolve(strict=True)
    require(is_hash(spec["orchestrator_commit"], 40) and git(root, "rev-parse", "HEAD") == spec["orchestrator_commit"],
            "orchestrator HEAD differs from its pin")
    require(not git(root, "status", "--porcelain", "--untracked-files=all", "--", "scripts", "src")
            and not git(root, "status", "--porcelain", "--untracked-files=no", "--", "orchestration"),
            "orchestrator launcher/config worktree is dirty")
    validate_keys(spec["config_sha256"], CONFIG_FILES, "stack config pins")
    for relative, expected in spec["config_sha256"].items():
        path = root / relative
        require(path.resolve(strict=True) == path, f"stack input traverses a symlink: {path}")
        check_pin(path, expected)
    return root


def stage_file(root, entry):
    resolved = entry.resolve(strict=True)
    require(resolved.is_relative_to(root) and resolved.is_file(), f"stage file escapes candidate: {entry}")
    return resolved


def verify_stage(image, candidate, backend, production_dirs):
    validate_keys(image, {"root", "inventory", "inventory_sha256", "identity_sha256"}, f"{backend} image")
    root = Path(image["root"])
    require(root.is_absolute() and root.resolve(strict=True) == root, f"{backend} stage must be an absolute canonical directory")
    require(all(not root.is_relative_to(path) and not path.is_relative_to(root) for path in production_dirs),
            f"{backend} stage overlaps a production directory")
    require(isinstance(image["inventory"], str) and re.fullmatch(r"SHA256SUMS(?:[.][A-Za-z0-9_-]+)?", image["inventory"]),
            f"invalid {backend} inventory name")
    manifest = root / image["inventory"]
    build_identity = root / "BUILD-IDENTITY.json"
    for path, expected in ((manifest, image["inventory_sha256"]), (build_identity, image["identity_sha256"])):
        require(stage_file(root, path) == path, f"stage metadata must be a regular file: {path}")
        check_pin(path, expected)

    identity = read_json(build_identity)
    require(
        identity.get("schema") == "epyc.build-identity.v1"
        and identity.get("kind") == {"cpu": "cpu", "hip": "gpu"}[backend]
        and identity.get("source_sha") == candidate["source_commit"]
        and identity.get("source_tree") == candidate["source_tree"]
        and identity.get("branch") == candidate["branch"],
        f"{backend} build identity differs from the candidate pin",
    )

    listed = {}
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64}) [ *](bin/[A-Za-z0-9_.+-]+)", line)
        require(match and match[2] not in listed, f"invalid or duplicate {backend} inventory entry: {line}")
        listed[match[2]] = match[1]

    bindir = root / "bin"
    require(bindir.resolve(strict=True) == bindir and bindir.is_dir(), f"invalid {backend} runtime directory")
    entries = {str(path.relative_to(root)): path for path in bindir.iterdir()}
    require(set(entries) == set(listed), f"{backend} binary and library inventory is incomplete or has unlisted files")
    verified = {}
    for relative, path in entries.items():
        resolved = stage_file(bindir, path)
        require(str(resolved.relative_to(root)) in listed, f"unlisted {backend} symlink target: {path}")
        if resolved not in verified:
            verified[resolved] = digest(resolved)
        require(verified[resolved] == listed[relative], f"changed {backend} stage member: {path}")

    binary = bindir / "llama-server"
    require(binary in verified and not binary.is_symlink() and os.access(binary, os.X_OK), f"missing {backend} executable")
    for path in production_dirs:
        executable = path / "llama-server"
        require(not os.path.samefile(binary, executable), f"{backend} server is hardlinked to the production image")
    libraries = {path.name for path in entries.values()}
    require(set(LIBRARIES) <= libraries, f"incomplete {backend} shared libraries")
    require(("libggml-hip.so" in libraries) == (backend == "hip"), f"{backend} has the wrong HIP library set")
    return image | {"binary": str(binary), "binary_sha256": verified[binary], "library_dir": str(bindir)}


def production_runtime_dirs():
    dirs = []
    for name in ("cpu", "gpu"):
        location = PRODUCTION / name
        dirs.extend((location, location.resolve(strict=True)))
    return dirs


def value_index(argv, flag, *, required=True):
    occurrences = [index for index, item in enumerate(argv) if item == flag or item.startswith(f"{flag}=")]
    if not occurrences and not required:
        return None
    require(len(occurrences) == 1, f"expected one {flag} in generated command")
    index = occurrences[0]
    require(argv[index] == flag and index + 1 < len(argv) and not argv[index + 1].startswith("-"),
            f"expected a separate argument for {flag}")
    return index + 1


def isolate_argv(original, canonical_port, isolated_port, image, slot_dir):
    require(isinstance(original, list) and original and all(isinstance(token, str) for token in original),
            "invalid generated server command")
    argv = original.copy()
    binary = Path(argv[0])
    require(binary.is_absolute() and binary.name == "llama-server", "expected a generated llama-server command")
    port = value_index(argv, "--port")
    host = value_index(argv, "--host")
    slot = value_index(argv, "--slot-save-path", required=False)
    require(argv[port] == str(canonical_port) and argv[host] == "127.0.0.1",
            "generated listener differs from the declared loopback endpoint")
    unsupported = {
        "--rpc", "--models-dir", "--model-url", "-mu", "-hf", "--hf-repo", "--hf-repo-draft",
        "--hf-file", "--mmproj-url", "--path", "--ssl-key-file", "--ssl-cert-file", "--lookup-cache-dynamic",
        "--log-file", "--log-dir", "--logdir",
    }
    require(not any(token.split("=", 1)[0] in unsupported for token in argv),
            "generated command requests an external model source or unsupported server path")
    argv[0] = image["binary"]
    argv[port] = str(isolated_port)
    if slot is not None:
        argv[slot] = str(slot_dir)
    return argv


def validate_endpoints(spec, servers, production_ports):
    declared = {str(server["port"]) for server in servers}
    require(servers and len(declared) == len(servers), "empty or duplicate production endpoint set")
    validate_keys(spec["ports"], declared, "isolated port map")
    validate_keys(spec["endpoint_tests"], declared, "endpoint test selection")
    validate_isolated_ports(spec["ports"], production_ports)
    for server in servers:
        expected = "embedding" if server.get("embedding") else "chat"
        require(spec["endpoint_tests"][str(server["port"])] == expected,
                f"endpoint test on :{server['port']} must use {expected}")


def validate_isolated_ports(mapping, production_ports):
    ports = list(mapping.values())
    require(all(type(port) is int and 1024 <= port <= 65535 and port not in production_ports for port in ports),
            "isolated ports must be valid non-production ports")
    require(len(set(ports)) == len(ports), "duplicate isolated port")


def build_endpoint(spec, output, server, manifest, launch, numa, registry, images):
    port = server["port"]
    roles = server["roles"]
    role = roles[0]
    instance = server.get("numa_instance", 0)
    embedder = server.get("embedding", False)
    if embedder:
        placement = manifest.EMBEDDING_PLACEMENT[port]
        prefix = ["numactl", f"--membind={placement.numa_node}", "--", "taskset", "-c", placement.cpuset]
    else:
        prefix = numa._numa_prefix(role, instance)
    require(prefix[-3:-1] == ["taskset", "-c"], f"missing declared CPU binding on :{port}")
    cpus = numa._parse_cpus(prefix[-1])
    require(cpus and cpus <= set(range(manifest._HOST_LOGICAL_CPUS)), f"invalid declared CPU binding on :{port}")
    dedicated = embedder or any(server.get(key) for key in ("dev", "vision", "worker_pool", "eval_batch_frontdoor", "gpu_shadow_lane"))
    original = launch.build_server_command(
        None if dedicated else registry.get_role(role), port,
        dev_mode=server.get("dev", False), embedding_mode=embedder,
        worker_pool_mode=server.get("worker_pool", False), worker_type=server.get("worker_type"),
        vision_mode=server.get("vision", False), vision_type=server.get("vision_type"),
        eval_batch_frontdoor_mode=server.get("eval_batch_frontdoor", False),
        gpu_shadow_lane_mode=server.get("gpu_shadow_lane", False),
        numa_instance=instance, prepare_runtime_dirs=False,
    )
    device_index = value_index(original, "--device")
    device = original[device_index]
    require(device == "none" or re.fullmatch(r"ROCm[0-9]+", device), f"unsupported backend on :{port}: {device}")
    draft_device = value_index(original, "--device-draft", required=False)
    require(draft_device is None or original[draft_device] in {"none", device}, f"unexpected drafter device on :{port}")
    backend = "cpu" if device == "none" else "hip"
    isolated_port = spec["ports"][str(port)]
    state_dir = output / "state" / str(isolated_port)
    argv = isolate_argv(original, port, isolated_port, images[backend], state_dir / "slots")
    env_role = "worker" if server.get("worker_pool") else "frontdoor" if server.get("eval_batch_frontdoor") else role
    env = launch.build_launch_env(env_role, {"PATH": "/usr/bin:/bin", "LANG": "C"})
    # The canonical environment adds LLVM libomp before the role settings. Keep
    # that specific toolchain path while replacing any ggml search path.
    env["LD_LIBRARY_PATH"] = f"{images[backend]['library_dir']}:{LLVM_LIBRARY_DIR}"
    require(not ({"LD_PRELOAD", "LD_AUDIT"} & env.keys()), f"unexpected loader override on :{port}")
    launch.apply_pinned_launch_env(env, prefix)
    return {
        "canonical_port": port, "port": isolated_port, "roles": roles, "numa_instance": instance,
        "backend": backend, "device": device, "physical_cpus": sorted(manifest._smt_fold(cpus)),
        "logical_cpus": sorted(cpus), "argv": prefix + argv, "env": env,
        "endpoint": f"http://127.0.0.1:{isolated_port}",
        "test": spec["endpoint_tests"][str(port)],
        "state_dir": str(state_dir), "log": str(output / "logs" / f"{isolated_port}.log"),
    }


def validate_claim(resources, endpoints, numa, physical_cores):
    validate_keys(resources, {"physical_cpus", "gpu_devices", "ram_gib"}, "resource claim")
    cpus = resources["physical_cpus"]
    require(isinstance(cpus, str) and re.fullmatch(r"\d{1,3}(?:-\d{1,3})?(?:,\d{1,3}(?:-\d{1,3})?)*", cpus),
            "invalid physical CPU list")
    cpu_set = numa._parse_cpus(cpus)
    require(cpu_set and cpu_set <= set(range(physical_cores)), "resource claim must use physical CPU IDs")
    require(set().union(*(set(endpoint["physical_cpus"]) for endpoint in endpoints)) == cpu_set,
            "resource claim must cover exactly the endpoints' physical CPU union")
    devices = resources["gpu_devices"]
    require(isinstance(devices, list) and all(isinstance(device, str) for device in devices)
            and sorted(set(devices)) == sorted(devices), "invalid GPU claim")
    require({endpoint["device"] for endpoint in endpoints} - {"none"} == set(devices),
            "GPU claim differs from the endpoints' declared device set")
    require(type(resources["ram_gib"]) is int and resources["ram_gib"] > 0, "invalid RAM request")


def prepare_plan(spec, output):
    common = {"schema", "orchestrator_commit", "config_sha256", "candidate", "ports", "resources"}
    require(isinstance(spec, dict), "invalid hot stack spec")
    quality = spec.get("schema") == QUALITY_SPEC_SCHEMA
    require(quality or spec.get("schema") == SPEC_SCHEMA, "unknown hot stack spec schema")
    mode_keys = {"request_inputs_sha256"} if quality else {"numa_mode", "warm_roles", "endpoint_tests"}
    validate_keys(spec, common | mode_keys, "hot stack spec")
    root = check_stack_inputs(spec)
    candidate = spec["candidate"]
    validate_keys(candidate, {"source_commit", "source_tree", "branch", "cpu", "hip"}, "candidate")
    require(is_hash(candidate["source_commit"], 40) and is_hash(candidate["source_tree"], 40)
            and isinstance(candidate["branch"], str) and candidate["branch"], "invalid candidate source pin")
    production_dirs = production_runtime_dirs()
    images = {backend: verify_stage(candidate[backend], candidate, backend, production_dirs) for backend in ("cpu", "hip")}
    require(images["cpu"]["root"] != images["hip"]["root"], "CPU and HIP images must be separate")
    sys.path.insert(0, str(root))
    from scripts.server import orchestrator_stack as launch, stack_manifest as manifest, stack_numa as numa, stack_prewarm
    from src.scheduling import contention

    matrix_path = root / "orchestration/contention_matrix.yaml"
    matrix = contention.load_contention_matrix(matrix_path)
    topology_hash = contention.topology_fingerprint_for_matrix(numa.NUMA_CONFIG, matrix)
    require(matrix.topology_hash == topology_hash, "contention matrix topology differs from the live declarations")
    matrix_status = contention.matrix_status(matrix_path, current_topology_hash=topology_hash)
    require(matrix_status in {contention.MatrixStatus.OK, contention.MatrixStatus.STALE}, "invalid contention matrix")
    # Checkout refreshes the file mtime. Also check the measurement
    # timestamp recorded in the pinned matrix bytes.
    measured_at = datetime.fromisoformat(matrix.measured_at)
    require(measured_at.tzinfo is not None, "matrix measurement timestamp must include a timezone")
    age = datetime.now(UTC) - measured_at
    if not timedelta(0) <= age <= timedelta(days=contention.MATRIX_STALENESS_DAYS):
        matrix_status = contention.MatrixStatus.STALE
    production_ports = set(manifest.PORT_MAP.values()) | {service.port for service in manifest.AUX_SERVICES.values()}
    production_ports.update(server["port"] for server in manifest.HOT_SERVERS + manifest.WARM_SERVERS)
    if quality:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from kernel_promotion_quality_prepare import prepare_quality_endpoints

        endpoints = prepare_quality_endpoints(spec, output, images, production_ports, manifest)
        targets = {}
    else:
        endpoints, targets = prepare_serving_endpoints(spec, output, images, production_ports, launch, manifest,
                                                       numa, stack_prewarm)

    check_stack_inputs(spec)
    return {
        "schema": PLAN_SCHEMA, "status": "prepared_only", "spec": spec,
        "topology_hash": topology_hash, "contention_matrix_status": matrix_status.value,
        "planner_sha256": digest(Path(__file__).resolve()),
        "launcher_sha256": {relative: digest(root / relative) for relative in LAUNCHER_FILES},
        "launcher_sequence": "serial", "images": images, "endpoints": endpoints,
        "endpoint_manifest": {
            "schema": "epyc.kernel_promotion_isolated_endpoints.v1",
            "endpoints": [{"role": endpoint["roles"][0], "kind": endpoint["test"],
                           "base_url": endpoint["endpoint"]} for endpoint in endpoints],
        },
        "prewarm_targets": [{"path": str(target["path"]), "size_bytes": target["size_bytes"],
                             "canonical_ports": sorted(set(target["ports"])), "roles": sorted(target["roles"])}
                            for target in targets.values()],
    }


def prepare_serving_endpoints(spec, output, images, production_ports, launch, manifest, numa, stack_prewarm):
    require(spec["numa_mode"] in ("full", "quarter", "both"), "invalid NUMA mode")
    warm_roles = spec["warm_roles"]
    require(isinstance(warm_roles, list) and all(isinstance(role, str) for role in warm_roles)
            and sorted(set(warm_roles)) == sorted(warm_roles), "invalid warm role selection")
    warm = [server for server in manifest.WARM_SERVERS if set(server["roles"]) & set(warm_roles)]
    require(set(warm_roles) <= {role for server in warm for role in server["roles"]}, "unknown warm role")
    servers = manifest._filter_by_numa_mode(manifest.HOT_SERVERS + warm, spec["numa_mode"])
    validate_endpoints(spec, servers, production_ports)
    registry = launch.RegistryLoader()
    endpoints = [build_endpoint(spec, output, server, manifest, launch, numa, registry, images) for server in servers]
    validate_claim(spec["resources"], endpoints, numa, manifest._HOST_PHYSICAL_CORES)

    commands = {endpoint["canonical_port"]: endpoint["argv"] for endpoint in endpoints}
    targets = stack_prewarm.collect_targets(servers, lambda _, port, **kwargs: commands[port], registry)
    for endpoint, server in zip(endpoints, servers, strict=True):
        models = []
        for flag in MODEL_FLAGS:
            index = value_index(endpoint["argv"], flag, required=flag == "-m")
            if index is not None:
                path = Path(endpoint["argv"][index]).resolve(strict=True)
                stat = path.stat()
                require(path.is_file(), f"invalid model path: {path}")
                models.append({"path": str(path), "stat": [stat.st_dev, stat.st_ino, stat.st_size,
                                                           stat.st_mtime_ns, stat.st_ctime_ns]})
                if not server.get("gpu_shadow_lane"):
                    require(endpoint["canonical_port"] in targets.get((stat.st_dev, stat.st_ino), {}).get("ports", []),
                            f"missing prewarm target on :{endpoint['canonical_port']}: {path}")
        endpoint["models"] = models

    return endpoints, targets


def write_new(path, value):
    with tempfile.TemporaryDirectory(dir=path.parent) as temp:
        staging = Path(temp) / "plan.json"
        with staging.open("x") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(staging, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    invoking_env = os.environ.copy()
    try:
        output = args.output_dir.absolute()
        root = SCRATCH.resolve(strict=True)
        require(output.parent.resolve(strict=True) == output.parent and output.is_relative_to(root)
                and output != root and not output.exists() and not output.is_symlink(),
                "output must be a new directory under the canonical scratch root")
        spec = read_json(args.spec)
        output.mkdir(mode=0o700)
        # The command builder can consult an artifact ledger. Use an empty private
        # ledger here so planning cannot refresh the serving ledger or hash weights.
        os.environ.clear()
        os.environ.update({name: invoking_env[name] for name in ROWFLOW_ENV if name in invoking_env})
        os.environ.update(PATH="/usr/bin:/bin", LANG="C", ARTIFACT_FINGERPRINT_LEDGER=str(output / "artifact-ledger.json"))
        plan = prepare_plan(spec, output)
        write_new(output / "plan.json", plan)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError, subprocess.SubprocessError) as exc:
        print(f"hot stack plan refused: {exc}", file=sys.stderr)
        return 2
    finally:
        os.environ.clear()
        os.environ.update(invoking_env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
