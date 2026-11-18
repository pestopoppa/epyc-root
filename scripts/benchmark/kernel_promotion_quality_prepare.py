#!/usr/bin/env python3
"""Materialize pinned prospective requests and assemble an offline live-capture configuration."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_promotion_quality_capture as live

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "epyc.kernel_quality_request_inputs.v1"
PROSPECTIVE_SCHEMA = "epyc.kernel_quality_prospective_requests.v1"
REQUEST_INPUTS = ROOT / "data/vidya/quality-pack-live-20261118/request_inputs.json"
RECIPE_LAYOUT = {
    "architect-critic-cpu-mtp": (8083, "architect_critic", 3),
    "architect-general-hip": (8074, "architect_general", 3),
    "dspark-dflash": (8083, "dflash", 3),
    "frontdoor-cpu-moe-mtp": (8070, "frontdoor", 2),
    "ingest-long-context-recurrent-no-spec": (8083, "ingest_long_context", 3),
    "worker-general-cpu-moe-mtp": (8070, "worker_general", 3),
    "worker-vision-hip-mmproj": (8086, "worker_vision", 3),
}
AFFINITY_WITNESSES = {
    "architect-critic-cpu-mtp": (
        "quality-pack-architect-bank-20261118/full-admitted-r2/native/production/server.json",
        "2b5ccd2ac796febc38e65d8cf9de949e932b287522df6c133608a775588075b4",
    ),
    "dspark-dflash": (
        "quality-pack-dflash-bank-20261118/full-admitted/native/production/server.json.original-bytes.json",
        "0eaa94eaa4bda256486ec680fd4066d0aef6872c0ec67e9547c330766e077bb6",
    ),
    "frontdoor-cpu-moe-mtp": (
        "quality-pack-native-20261118/full-capture/native/production/server.json.original-bytes.json",
        "640351410c0691f87fe5a9d5ba31aa095caee6719c93c995a622354a5ea2bdcf",
    ),
    "ingest-long-context-recurrent-no-spec": (
        "quality-pack-ingest-bank-20261118/full-admitted/native/production/server.json",
        "2f1e49c7ca606ab2c2da477685ea816a13f30a92b5ac84911c8240952dc75c64",
    ),
    "worker-general-cpu-moe-mtp": (
        "quality-pack-worker-general-20261118/full-capture/native/production/server.json.original-bytes.json",
        "5ae27637d66c905dc30c581d94d90a434cdfae9699c6f84e5f82c251b0aa5fe0",
    ),
}
# The original architect-general HIP row reserved 112 GiB. The recipes run serially.
MIN_RECIPE_RAM_GIB = 112
planner = live.planner
parity = live.parity
require = live.require


def read_source(record):
    planner.validate_keys(record, {"path", "sha256"}, "source archive")
    path = (ROOT / record["path"]).resolve(strict=True)
    require(path.is_relative_to(ROOT / "data/vidya"), "source archive escaped data/vidya")
    wrapper = parity._parse(path.read_bytes())
    require(wrapper.get("schema") in (None, "epyc.original_bytes.v1", "epyc.vidya.original_bytes.v1"),
            f"unexpected archival schema: {path}")
    raw = base64.b64decode(wrapper["bytes_b64"], validate=True)
    require(live.sha(raw) == wrapper["sha256"] == record["sha256"], f"changed original plan bytes: {path}")
    return parity._parse(raw)


def materialize_profile(profile, record, scorer_sha, *, source=None):
    if source is None:
        source = read_source(record["source"])
    require(source.get("profile", profile) == profile, f"{profile}: wrong source profile")
    recipe = source["recipes"][record["recipe"]]
    shape = {"id": profile, "profile": profile, "endpoint": recipe["endpoint"]}
    if profile == "dspark-dflash":
        shape["validated_cap"] = source["validated_cap"]
    overrides = record.get("vision_policies", {})
    rows = []
    for item in source["items"]:
        body = item["request_body"]
        require(body.get("return_tokens") is True and (shape["endpoint"] == "/completion" or body.get("verbose") is True),
                f"{item['id']}: request must expose token IDs")
        policy = overrides[item["id"]] if overrides else item
        row = {key: policy[key] for key in ("output_format", "fixture", "expected_finish", "dflash_pair", "validator")}
        row.update(id=item["id"], shape=profile, prompt_shape=item["prompt_shape"], request_body=body,
                   request_sha256=parity._json_hash(body))
        rows.append(row)
    require({row["id"]: row["request_sha256"] for row in rows} == record["request_sha256"],
            f"{profile}: request inventory or canonical bytes differ from the pin")
    models = [source[name] for name in record["model_fields"]]
    pins = [pin for entry in models for pin in (entry if isinstance(entry, list) else [entry])]
    template = (live.sha(b"raw-native-prompt.v1") if shape["endpoint"] == "/completion"
                else source[record["template_field"]]["sha256"])
    controls = [{"id": row["id"], "body": {key: value for key, value in row["request_body"].items()
                                          if key not in ("prompt", "messages", "model")}} for row in rows]
    scoring = [{key: row[key] for key in ("id", "validator", "expected_finish")} for row in rows]
    shape.update(sampling_sha256=parity._json_hash(controls),
                 scorer_sha256=parity._json_hash({"comparator": scorer_sha, "items": scoring}),
                 question_pool_sha256=parity._json_hash(rows))
    return shape, rows, pins, template


def read_request_inputs(path, pin):
    _, raw = live.pinned_bytes(path, pin)
    inputs = parity._parse(raw)
    planner.validate_keys(inputs, {"schema", "question", "scorer_source_sha256", "profiles"}, "request inputs")
    require(inputs["schema"] == SCHEMA, "unsupported request input schema")
    scorer_sha = inputs["scorer_source_sha256"]
    require(scorer_sha == parity.VALIDATOR_SOURCE_SHA256, "loaded comparator differs from the prospective scorer")
    planner.validate_keys(inputs["profiles"], live.PROFILES, "request profile inventory")
    return inputs


def materialize(path, pin):
    inputs = read_request_inputs(path, pin)
    scorer_sha = inputs["scorer_source_sha256"]
    shapes, items, models, shape_models, templates = {}, [], {}, {}, {}
    for profile, record in sorted(inputs["profiles"].items()):
        shape, rows, pins, template = materialize_profile(profile, record, scorer_sha)
        shapes[profile] = shape
        shape_models[profile] = [entry["path"] for entry in pins]
        templates[profile] = template
        items.extend(rows)
        for entry in pins:
            path = entry["path"]
            identity = {key: entry[key] for key in ("sha256", "stat")}
            require(models.setdefault(path, identity) == identity, f"conflicting original model pin: {path}")
    live.request_manifest(items, shapes)
    return {"schema": PROSPECTIVE_SCHEMA, "question": inputs["question"], "input_sha256": pin,
            "scorer_source_sha256": scorer_sha, "shapes": list(shapes.values()), "items": items,
            "models": models, "shape_model_paths": shape_models, "template_sha256": templates}


def recipe_inputs(pin):
    inputs = read_request_inputs(REQUEST_INPUTS, pin)
    recipes = {}
    for profile, (port, role, node) in RECIPE_LAYOUT.items():
        record = inputs["profiles"][profile]
        source = read_source(record["source"])
        recipe = source["recipes"][record["recipe"]]
        args = recipe["args"]
        device = args[planner.value_index(args, "--device")]
        require(device in ("none", "ROCm0"), f"{profile}: unsupported device")
        affinity_source = record["source"]
        if device == "none":
            relative, sha = AFFINITY_WITNESSES[profile]
            affinity_source = {"path": f"data/vidya/{relative}", "sha256": sha}
            if relative.endswith(".original-bytes.json"):
                witness = read_source(affinity_source)
            else:
                _, raw = live.pinned_bytes(ROOT / affinity_source["path"], sha)
                witness = parity._parse(raw)
            logical_cpus = witness["cpus"]
            argv = witness["argv"]
            require(argv[planner.value_index(argv, "--threads")] == str(len(logical_cpus))
                    and argv[7:] == args, f"{profile}: original launch witness differs from the recipe")
        else:
            logical_cpus = recipe["cpu_affinity"]
        require(isinstance(logical_cpus, list) and all(type(cpu) is int and cpu >= 0 for cpu in logical_cpus)
                and len(set(logical_cpus)) == len(logical_cpus) == (24 if device == "none" else 8),
                f"{profile}: invalid original affinity")
        cpuset = ",".join(map(str, logical_cpus))
        template = None
        if recipe["endpoint"] == "/v1/chat/completions":
            path = args[planner.value_index(args, "--chat-template-file")]
            template = {"path": path, "sha256": source[record["template_field"]]["sha256"]}
        _, _, models, _ = materialize_profile(profile, record, inputs["scorer_source_sha256"], source=source)
        recipes[profile] = {
            "mapping": {"canonical_port": port, "role": role, "numa_instance": 0, "path": recipe["endpoint"]},
            "source": record["source"], "affinity_source": affinity_source,
            "args": args, "device": device, "template": template,
            "logical_cpus": logical_cpus,
            "prefix": ["numactl", f"--membind={node}", "--", "taskset", "-c", cpuset],
            "models": [{key: model[key] for key in ("path", "sha256", "stat")} for model in models],
        }
    return recipes


def prepare_quality_endpoints(spec, directory, images, production_ports, manifest):
    recipes = recipe_inputs(spec["request_inputs_sha256"])
    ports = spec["ports"]
    resources = spec["resources"]
    planner.validate_keys(ports, recipes, "quality profile ports")
    planner.validate_isolated_ports(ports, production_ports)
    planner.validate_keys(resources, {"physical_cpus", "gpu_devices", "ram_gib"}, "resource claim")
    require(resources["physical_cpus"] == "0-95" and resources["gpu_devices"] == ["ROCm0"]
            and type(resources["ram_gib"]) is int and resources["ram_gib"] >= MIN_RECIPE_RAM_GIB,
            f"quality capture requires full-host CPU, MI210 and at least {MIN_RECIPE_RAM_GIB} GiB of RAM")
    endpoints = []
    for profile, recipe in recipes.items():
        mapping = recipe["mapping"]
        anchor = mapping["canonical_port"]
        anchor_role = "architect_critic" if mapping["role"] == "dflash" else mapping["role"]
        require(manifest.PORT_MAP[anchor_role] == anchor, f"{profile}: changed production role anchor")
        logical = recipe["logical_cpus"]
        require(set(logical) <= set(range(manifest._HOST_LOGICAL_CPUS)), f"{profile}: invalid CPU binding")
        port = ports[profile]
        device = recipe["device"]
        backend = "cpu" if device == "none" else "hip"
        image = images[backend]
        original = [image["binary"], "--host", "127.0.0.1", "--port", str(anchor),
                    "--threads", str(len(logical)), *recipe["args"]]
        state_dir = directory / "state" / str(port)
        argv = planner.isolate_argv(original, anchor, port, image, state_dir / "slots")
        # Check every original model pin, including cold split shards, without reading tensor data.
        pins = {model["path"]: {key: model[key] for key in ("sha256", "stat")} for model in recipe["models"]}
        live.evidence.verify_models(pins)
        models = []
        for flag in planner.MODEL_FLAGS:
            index = planner.value_index(argv, flag, required=flag == "-m")
            if index is not None:
                path = argv[index]
                require(path in pins, f"{profile}: unpinned {flag} file")
                models.append({"path": path, "stat": pins[path]["stat"]})
        if template := recipe["template"]:
            path = live.runner.canonical_file(Path(template["path"]))
            planner.check_pin(path, template["sha256"])
        visibility = {"ROCR_VISIBLE_DEVICES": "0", "HIP_VISIBLE_DEVICES": "0", "CUDA_VISIBLE_DEVICES": "0"}
        if backend == "cpu":
            visibility = {"ROCR_VISIBLE_DEVICES": "-1", "HIP_VISIBLE_DEVICES": "-1", "CUDA_VISIBLE_DEVICES": ""}
        env = {"PATH": "/usr/bin:/bin", "LANG": "C", "GGML_IQK": "1", "OMP_NUM_THREADS": "1",
               "LD_LIBRARY_PATH": f"{image['library_dir']}:{planner.LLVM_LIBRARY_DIR}"} | visibility
        if profile == "worker-vision-hip-mmproj":
            env["MTMD_BACKEND_DEVICE"] = device
        endpoints.append({
            "quality_profile": profile, "canonical_port": anchor, "port": port, "roles": [mapping["role"]],
            "numa_instance": mapping["numa_instance"], "backend": backend, "device": device,
            "physical_cpus": sorted(manifest._smt_fold(set(logical))), "logical_cpus": logical,
            "argv": recipe["prefix"] + argv, "env": env, "endpoint": f"http://127.0.0.1:{port}",
            "test": "chat", "state_dir": str(state_dir), "log": str(directory / "logs" / f"{port}.log"),
            "models": models,
        })
    return endpoints


def assemble_config(pack, args):
    scratch = planner.SCRATCH.resolve(strict=True)
    plans = {arm: live.load_plan({"plan": value[0], "plan_sha256": value[1], "runtime": {}}, scratch)
             for arm, value in (("production", args.production_plan), ("candidate", args.candidate_plan))}
    specs = [plan["spec"] for _, _, plan in plans.values()]
    if any(spec.get("schema") == planner.QUALITY_SPEC_SCHEMA for spec in specs):
        require(all(spec.get("request_inputs_sha256") == pack["input_sha256"] for spec in specs),
                "both quality plans must use the prospective request inputs")
    repository = args.source_repository
    require(repository.is_absolute() and repository.resolve(strict=True) == repository and repository.is_dir()
            and planner.git(repository, "rev-parse", "--show-toplevel") == str(repository),
            "capture source repository must be the canonical Git root")
    planner.ORCHESTRATOR = args.orchestrator
    _, mapping_raw = live.pinned_bytes(*args.mappings)
    mappings = parity._parse(mapping_raw)
    planner.validate_keys(mappings, live.PROFILES, "shape mappings")
    attestation = live.runner.canonical_file(args.production_attestation)
    live.verify_production(plans["production"][2], attestation)
    live.evidence.verify_models(pack["models"])

    with tempfile.TemporaryDirectory(dir=args.out.parent) as temp:
        for arm, (path, _, plan) in plans.items():
            live.runner.regenerate(plan, path.parent, Path(temp) / f"{arm}-artifact-ledger.json")

    from src.registry import artifact_integrity

    require(Path(artifact_integrity.__file__).resolve().is_relative_to(args.orchestrator),
            "artifact integrity did not load from the pinned orchestrator")
    shapes = {shape["id"]: shape.copy() for shape in pack["shapes"]}
    arms = {}
    for arm, (path, raw, plan) in plans.items():
        stage = plan["spec"]["candidate"]
        runtime = {}
        for profile, shape in shapes.items():
            endpoint = live.endpoint_for(plan, mappings[profile], shape)
            live.runner.verify_models(endpoint)
            paths = [str(Path(shard)) for model in endpoint["models"]
                     for shard in artifact_integrity.shard_paths(model["path"])]
            require(paths == pack["shape_model_paths"][profile], f"{profile}: model or shard selection changed")
            digests = live.shape_digests(plan, endpoint, shape, artifact_integrity, pack["models"])
            require(digests["prompt_template_sha256"] == pack["template_sha256"][profile],
                    f"{profile}: effective template differs from prospective template")
            if arm == "production":
                shape.update(digests)
            else:
                require(all(shape[key] == value for key, value in digests.items()),
                        f"{profile}: candidate serving identity differs from production")
            image = plan["images"][endpoint["backend"]]
            runtime[profile] = {"kernel_commit": stage["source_commit"], "kernel_tree": stage["source_tree"],
                                "binary_sha256": image["binary_sha256"]}
        arms[arm] = {"plan": str(path), "plan_sha256": live.sha(raw), "runtime": runtime}

    capture_path = Path(live.__file__).resolve()
    require(planner.is_hash(args.capture_commit, 40), "capture commit must be a full Git commit hash")
    capture_source = {"commit": args.capture_commit,
                      "tree": planner.git(repository, "rev-parse", f"{args.capture_commit}^{{tree}}"),
                      "source_sha256": planner.digest(capture_path)}
    return {"schema": live.SCHEMA, "source_repository": str(repository), "capture_source": capture_source,
            "tool_sha256": {name: planner.digest(path) for name, path in live.tool_files().items()},
            "production_attestation": str(attestation), "arms": arms, "shapes": list(shapes.values()),
            "mappings": mappings, "models": pack["models"], "items": pack["items"],
            "startup_timeout_s": args.startup_timeout_s, "request_timeout_s": args.request_timeout_s}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    requests = commands.add_parser("requests", help="verify and materialize the prospective request inputs")
    recipes = commands.add_parser("recipes", help="materialize the source-bound isolated quality recipes")
    recipes.add_argument("--inputs-sha256", required=True)
    recipes.add_argument("--out", type=Path, required=True)
    config = commands.add_parser("config", help="assemble a capture config from two fresh prepared plans")
    for command in (requests, config):
        command.add_argument("--inputs", type=Path, required=True)
        command.add_argument("--inputs-sha256", required=True)
        command.add_argument("--out", type=Path, required=True)
    for flag in ("production-plan", "candidate-plan", "mappings"):
        config.add_argument(f"--{flag}", nargs=2, metavar=("FILE", "SHA256"), required=True)
    config.add_argument("--orchestrator", type=Path, required=True)
    config.add_argument("--source-repository", type=Path, required=True)
    config.add_argument("--production-attestation", type=Path, required=True)
    config.add_argument("--capture-commit", required=True)
    config.add_argument("--observation-dir", type=Path, required=True)
    config.add_argument("--startup-timeout-s", type=int, required=True)
    config.add_argument("--request-timeout-s", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        scratch = planner.SCRATCH.resolve(strict=True)
        require(args.out.is_absolute() and args.out.is_relative_to(scratch)
                and args.out.parent.resolve(strict=True) == args.out.parent and not args.out.exists()
                and not args.out.is_symlink(), "output must be new under canonical host scratch")
        if args.command == "recipes":
            raw = parity.pack_bytes(recipe_inputs(args.inputs_sha256))
        else:
            pack = materialize(args.inputs, args.inputs_sha256)
            raw = parity.pack_bytes(pack)
        if args.command == "config":
            require(args.orchestrator.is_absolute() and args.orchestrator.resolve(strict=True) == args.orchestrator,
                    "orchestrator checkout must use its canonical path")
            require(not args.observation_dir.exists() and not args.observation_dir.is_symlink(),
                    "observation directory already exists")
            raw = parity.pack_bytes(assemble_config(pack, args))
            with tempfile.TemporaryDirectory(dir=args.out.parent) as temp:
                staged = Path(temp) / args.out.name
                live.write_bytes(staged, raw)
                live.load_config(staged, live.sha(raw), args.observation_dir)
        live.write_bytes(args.out, raw)
        print(live.sha(raw))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError, ImportError, RuntimeError,
            subprocess.SubprocessError) as exc:
        print(f"quality input preparation refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
