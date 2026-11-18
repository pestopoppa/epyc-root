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


def materialize_profile(profile, record, scorer_sha):
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


def materialize(path, pin):
    _, raw = live.pinned_bytes(path, pin)
    inputs = parity._parse(raw)
    planner.validate_keys(inputs, {"schema", "question", "scorer_source_sha256", "profiles"}, "request inputs")
    require(inputs["schema"] == SCHEMA, "unsupported request input schema")
    scorer_sha = inputs["scorer_source_sha256"]
    require(scorer_sha == parity.VALIDATOR_SOURCE_SHA256, "loaded comparator differs from the prospective scorer")
    planner.validate_keys(inputs["profiles"], live.PROFILES, "request profile inventory")
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


def assemble_config(pack, args):
    scratch = planner.SCRATCH.resolve(strict=True)
    plans = {arm: live.load_plan({"plan": value[0], "plan_sha256": value[1], "runtime": {}}, scratch)
             for arm, value in (("production", args.production_plan), ("candidate", args.candidate_plan))}
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
