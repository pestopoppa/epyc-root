#!/usr/bin/env python3
"""Capture a prospective quality comparison on isolated, admitted hot-stack listeners."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_promotion_contention_acquire as workload_guard

runner = workload_guard.runner
planner = runner.planner
evidence = runner.evidence
require = runner.require

# The evidence module adds the kernel-promotion skill scripts to the import path.
import quality_parity as parity

SCHEMA = "epyc.kernel_quality_live_capture.v1"
ARM_NAMES = ("production", "candidate")
PRODUCTION_SOURCE = Path("/mnt/raid0/llm/llama.cpp")
FREEZE_SHA256 = "4a0e6c832bb34cb587de38574e3e163be6b14f6ff598c2e3044a1815e99526d8"
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
PROFILES = {
    "frontdoor-cpu-moe-mtp": ("frontdoor", "cpu", "draft-mtp"),
    "worker-general-cpu-moe-mtp": ("worker_general", "cpu", "draft-mtp"),
    "architect-critic-cpu-mtp": ("architect_critic", "cpu", "draft-mtp"),
    "ingest-long-context-recurrent-no-spec": ("ingest_long_context", None, "none"),
    "architect-general-hip": ("architect_general", "hip", None),
    "worker-vision-hip-mmproj": ("worker_vision", "hip", None),
    "dspark-dflash": (None, None, "draft-dflash"),
}
TIMEOUT_LIMITS = {"startup_timeout_s": 3600, "request_timeout_s": 1800}


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def write_bytes(path, payload):
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def pinned_bytes(filename, pin):
    path = runner.canonical_file(Path(filename))
    raw = path.read_bytes()
    require(planner.is_hash(pin) and sha(raw) == pin, f"changed input pin: {path}")
    return path, raw


def tool_files():
    return {
        "planner": Path(planner.__file__),
        "preparer": Path(__file__).resolve().with_name("kernel_promotion_quality_prepare.py"),
        "runner": Path(runner.__file__),
        "evidence": Path(evidence.__file__),
        "linkage": runner.LINKAGE,
        "workload_guard": Path(workload_guard.__file__),
        "k35": Path(workload_guard.k35.__file__),
        "comparator": Path(parity.__file__),
    }


def verify_source(config):
    source = config["capture_source"]
    path = Path(__file__).resolve()
    repository = Path(config["source_repository"])
    require(repository.is_absolute() and repository.resolve(strict=True) == repository
            and repository.is_dir(), "capture source repository must be a canonical directory")
    require(planner.git(repository, "rev-parse", f"{source['commit']}^{{tree}}") == source["tree"],
            "capture source commit and Git tree differ")
    original = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repository), "show",
         f"{source['commit']}:scripts/benchmark/{path.name}"],
        capture_output=True, check=True, timeout=20,
    ).stdout
    require(sha(original) == source["source_sha256"] == planner.digest(path),
            "capture source differs from its committed pin")
    files = tool_files()
    planner.validate_keys(config["tool_sha256"], files, "capture tool pins")
    for name, filename in files.items():
        planner.check_pin(filename, config["tool_sha256"][name])
    require(config["tool_sha256"]["comparator"] == parity.VALIDATOR_SOURCE_SHA256,
            "loaded comparator differs from its source pin")


def load_plan(arm, scratch):
    planner.validate_keys(arm, {"plan", "plan_sha256", "runtime"}, "arm")
    path, raw = pinned_bytes(arm["plan"], arm["plan_sha256"])
    require(path.name == "plan.json" and path.parent.is_relative_to(scratch) and path.parent != scratch
            and (path.parent.stat().st_mode & 0o077) == 0, "expected a private prepared plan under host scratch")
    plan = parity._parse(raw)
    require(plan["schema"] == planner.PLAN_SCHEMA and plan["status"] == "prepared_only"
            and plan["contention_matrix_status"] == "ok", "expected a prepared hot-stack plan with a fresh matrix")
    return path, raw, plan


def verify_production(plan, attestation_path):
    _, raw = pinned_bytes(attestation_path, FREEZE_SHA256)
    attestation = parity._parse(raw)
    source = plan["spec"]["candidate"]
    baseline = attestation["production_head"]
    branch = attestation["production_branch"]
    require(source["source_commit"] == baseline and source["branch"] == branch
            and planner.git(PRODUCTION_SOURCE, "rev-parse", "HEAD") == baseline
            and planner.git(PRODUCTION_SOURCE, "branch", "--show-current") == branch
            and planner.git(PRODUCTION_SOURCE, "rev-parse", f"{baseline}^{{tree}}") == source["source_tree"],
            "production plan differs from the ratified frozen source")
    require(not planner.git(PRODUCTION_SOURCE, "status", "--porcelain", "--untracked-files=no"),
            "frozen production source has tracked changes")
    for backend, location in (("cpu", "cpu"), ("hip", "gpu")):
        image = plan["images"][backend]
        frozen = (planner.PRODUCTION / location).resolve(strict=True)
        pin = runner.image_pin(image, backend)
        require(pin["binary_sha256"] == attestation["production_binary_sha256"][backend],
                f"{backend} stage differs from the ratified production binary")
        planner.check_pin(frozen / "llama-server", pin["binary_sha256"])
        for name, digest in pin["libraries"].items():
            planner.check_pin(runner.canonical_file(frozen / name), digest)
    return raw


def endpoint_for(plan, mapping, shape):
    planner.validate_keys(mapping, {"canonical_port", "role", "numa_instance", "path"}, "shape mapping")
    require(type(mapping["canonical_port"]) is int and type(mapping["numa_instance"]) is int
            and isinstance(mapping["role"], str) and mapping["path"] == shape["endpoint"],
            f"{shape['id']}: invalid endpoint mapping")
    spec = plan["spec"]
    quality = spec.get("schema") == planner.QUALITY_SPEC_SCHEMA
    profile = shape["profile"]
    matches = [endpoint for endpoint in plan["endpoints"]
               if endpoint["canonical_port"] == mapping["canonical_port"]
               and (not quality or endpoint["quality_profile"] == profile)]
    require(len(matches) == 1, f"{shape['id']}: missing or ambiguous endpoint port")
    endpoint = matches[0]
    port = endpoint["port"]
    argv = endpoint["argv"]
    role, backend, speculation = PROFILES[profile]
    spec_index = planner.value_index(argv, "--spec-type", required=False)
    spec_type = argv[spec_index] if spec_index is not None else "none"
    require(mapping["role"] in endpoint["roles"] and (role is None or role == mapping["role"])
            and endpoint["numa_instance"] == mapping["numa_instance"]
            and endpoint["test"] == "chat" and (backend is None or endpoint["backend"] == backend)
            and endpoint["endpoint"] == f"http://127.0.0.1:{port}"
            and spec["ports"][profile if quality else str(mapping["canonical_port"])] == port
            and argv[planner.value_index(argv, "--port")] == str(port)
            and argv[planner.value_index(argv, "--host")] == "127.0.0.1"
            and (speculation is None or spec_type == speculation),
            f"{shape['id']}: prepared endpoint differs from the prescribed serving profile or instance")
    if shape["profile"] == "worker-vision-hip-mmproj":
        require(mapping["path"] == "/v1/chat/completions"
                and planner.value_index(argv, "--mmproj", required=False) is not None,
                f"{shape['id']}: vision shape requires the image chat endpoint and a projector")
    if shape["profile"] == "dspark-dflash":
        require(argv[planner.value_index(argv, "-np")] == "1"
                and argv[planner.value_index(argv, "--spec-draft-n-max")] == str(shape["validated_cap"])
                and planner.value_index(argv, "-md", required=False) is not None,
                f"{shape['id']}: DFlash requires a drafter, pinned cap and -np 1")
    return endpoint


def verify_runtime(identity, plan, endpoint):
    stage = plan["spec"]["candidate"]
    image = plan["images"][endpoint["backend"]]
    expected = {"kernel_commit": stage["source_commit"], "kernel_tree": stage["source_tree"],
                "binary_sha256": image["binary_sha256"]}
    require(identity == expected and endpoint["argv"][6] == image["binary"],
            "declared runtime or launch executable differs from the prepared image")


def endpoint_semantics(path):
    return {"method": "POST", "path": path, "request_encoding": "canonical-json",
            "response_encoding": "raw-json", "stream": False}


def recipe_record(plan, endpoint):
    argv = endpoint["argv"].copy()
    argv[6] = "<isolated-executable>"
    argv[planner.value_index(argv, "--port")] = "<isolated-port>"
    slot = planner.value_index(argv, "--slot-save-path", required=False)
    if slot is not None:
        argv[slot] = "<isolated-slots>"
    env = endpoint["env"].copy()
    lib = plan["images"][endpoint["backend"]]["library_dir"]
    require(env["LD_LIBRARY_PATH"] == f"{lib}:{planner.LLVM_LIBRARY_DIR}", "isolated loader path changed")
    env["LD_LIBRARY_PATH"] = f"<isolated-library-dir>:{planner.LLVM_LIBRARY_DIR}"
    return {"argv": argv, "env": env, **{key: endpoint[key] for key in
            ("canonical_port", "roles", "numa_instance", "backend", "device", "physical_cpus", "logical_cpus")}}


def shape_digests(plan, endpoint, shape, artifact_integrity, models):
    # The pinned model ledger includes every split shard, drafter and projector.
    # Compare the precomputed file identities here without hashing tensor data.
    model_records = []
    for model in endpoint["models"]:
        for shard in artifact_integrity.shard_paths(model["path"]):
            path = runner.canonical_file(Path(shard))
            pin = models[str(path)]
            evidence.verify_models({str(path): pin})
            if str(path) == model["path"]:
                require(pin["stat"] == model["stat"], f"prepared model pin differs: {path}")
            model_records.append({"path": str(path), "sha256": pin["sha256"]})

    argv = endpoint["argv"]
    if shape["endpoint"] == "/completion":
        template = b"raw-native-prompt.v1"
    else:
        template, _ = artifact_integrity.effective_template_bytes(argv)
        require(isinstance(template, bytes) and template, f"{shape['id']}: no pin-ready chat template")
    recipe = parity._json_hash(recipe_record(plan, endpoint))
    semantics = parity._json_hash(endpoint_semantics(shape["endpoint"]))
    model = parity._json_hash(model_records)
    template_sha = sha(template)
    return {"model_sha256": model, "recipe_sha256": recipe, "prompt_template_sha256": template_sha,
            "endpoint_semantics_sha256": semantics,
            "generation_path_sha256": parity._json_hash([recipe, semantics, model, template_sha])}


def verify_shape(plan, endpoint, shape, artifact_integrity, models):
    for key, digest in shape_digests(plan, endpoint, shape, artifact_integrity, models).items():
        require(shape[key] == digest, f"{shape['id']}: {key} differs from its prepared endpoint")


def check_chat_media(body):
    has_image = False
    for message in body["messages"]:
        content = message["content"]
        if not isinstance(content, list):
            continue
        for part in content:
            require(isinstance(part, dict) and part.get("type") in ("text", "image_url"),
                    "quality chat supports text and inline image parts")
            if part["type"] == "image_url":
                url = part.get("image_url")
                url = url.get("url") if isinstance(url, dict) else None
                header, _, data = url.partition(",") if isinstance(url, str) else ("", "", "")
                require(header in ("data:image/png;base64", "data:image/jpeg;base64") and data,
                        "quality image must be embedded as a PNG or JPEG data URL")
                base64.b64decode(data, validate=True)
                has_image = True
    return has_image


def request_manifest(items, shapes):
    rows = parity._named_rows(items, "request")
    require(all(SAFE_ID.fullmatch(item_id) for item_id in rows), "unsafe request ID")
    seen = set()
    pairs = {}
    images = set()
    for item_id, item in rows.items():
        planner.validate_keys(item, (parity.ITEM_FIELDS - {"production"}) | {"request_sha256"}, item_id)
        shape = shapes[item["shape"]]
        path, body = shape["endpoint"], item["request_body"]
        parity._request(body, path)
        pin = parity._json_hash(body)
        require(pin == item["request_sha256"] and (path, pin) not in seen,
                f"{item_id}: changed request pin or duplicate canonical request")
        seen.add((path, pin))
        require(item["prompt_shape"] in parity.PROMPTS and item["output_format"] in parity.FORMATS
                and item["fixture"] in parity.FIXTURES | {None} and item["expected_finish"] in parity.FINISHES,
                f"{item_id}: unsupported coverage tag")
        parity._semantic_matches(item["validator"], "")
        require(item["output_format"] != "json" or item["validator"]["id"] == "json-object-subset.v1",
                f"{item_id}: JSON coverage requires the JSON object validator")
        if path == "/v1/chat/completions" and check_chat_media(body):
            images.add(item["shape"])
        cap, pair = body.get(parity.CAP_KEY), item["dflash_pair"]
        if shape["profile"] == "dspark-dflash":
            require(type(cap) is int and cap in (0, shape["validated_cap"])
                    and isinstance(pair, str) and bool(pair.strip()), f"{item_id}: invalid DFlash pair or cap")
            # Prospective pairing checks compare the declared endpoint; capture will bind the actual PID.
            pairs.setdefault(pair, []).append(parity._pair_row(item, {"server_instance": item["shape"]}, cap))
        else:
            require(parity.CAP_KEY not in body and pair is None, f"{item_id}: unexpected DFlash metadata")
    for shape_id, shape in shapes.items():
        require(shape["profile"] != "worker-vision-hip-mmproj" or shape_id in images,
                f"{shape_id}: vision coverage requires an inline image request")
    parity._coverage(items, shapes, pairs)
    return rows


def load_config(path, pin, output):
    _, raw = pinned_bytes(path, pin)
    config = parity._parse(raw)
    planner.validate_keys(config, {"schema", "capture_source", "source_repository", "tool_sha256",
                                   "production_attestation", "arms", "shapes", "mappings", "models",
                                   "items", *TIMEOUT_LIMITS}, "live capture config")
    require(config["schema"] == SCHEMA, "unsupported live quality capture config schema")
    for name, maximum in TIMEOUT_LIMITS.items():
        require(type(config[name]) is int and 1 <= config[name] <= maximum, f"invalid {name}")
    parity._capture_source(config["capture_source"])
    shapes = parity._shapes(config["shapes"])
    planner.validate_keys(config["arms"], ARM_NAMES, "arm inventory")
    planner.validate_keys(config["mappings"], shapes, "shape mappings")
    rows = request_manifest(config["items"], shapes)
    scratch = planner.SCRATCH.resolve(strict=True)
    require(output.is_absolute() and output != scratch and output.is_relative_to(scratch)
            and output.parent.resolve(strict=True) == output.parent, "output must be new under canonical host scratch")
    plans = {arm: load_plan(config["arms"][arm], scratch) for arm in ARM_NAMES}
    directories = [path.parent for path, _, _ in plans.values()]
    require(directories[0] != directories[1]
            and not any(output.is_relative_to(directory) or directory.is_relative_to(output) for directory in directories),
            "both arms and observation require distinct private directories")
    for arm, (_, _, plan) in plans.items():
        declared = config["arms"][arm]["runtime"]
        parity._runtime(declared, shapes)
        for shape_id, shape in shapes.items():
            verify_runtime(declared[shape_id], plan, endpoint_for(plan, config["mappings"][shape_id], shape))
    left, right = [plan["spec"] for _, _, plan in plans.values()]
    require(left["ports"] == right["ports"] and left["resources"] == right["resources"],
            "the arms must match the port and resource assignment of one Rowflow grant")
    if any(spec.get("schema") == planner.QUALITY_SPEC_SCHEMA for spec in (left, right)):
        require(left.get("schema") == right.get("schema") == planner.QUALITY_SPEC_SCHEMA
                and left["request_inputs_sha256"] == right["request_inputs_sha256"],
                "both arms must share the same isolated recipe input pin")
    require(left["candidate"]["source_commit"] != right["candidate"]["source_commit"],
            "production and candidate source commits must differ")
    verify_source(config)
    return config, raw, plans, shapes, rows


def capture_request(runtime, server, path, item, directory):
    body = parity.canonical_json(item["request_body"])
    pin = item["request_sha256"]
    require(sha(body) == pin, f"{item['id']}: request body changed before dispatch")
    directory.mkdir(mode=0o700)
    write_bytes(directory / "request.json", body)
    started = time.monotonic()
    timeout = runtime.timeout(runtime.request_timeout)
    sent = threading.Event()
    done = threading.Event()
    cancelled = threading.Event()
    outcome = {}

    def connected(sock):
        outcome["socket"] = sock
        require(not cancelled.is_set(), "quality request cancelled before dispatch")

    def upload_finished():
        outcome["sent"] = time.monotonic()
        sent.set()

    def headers_arrived():
        outcome["headers"] = time.monotonic()

    def dispatch():
        try:
            outcome["response"] = runtime.request_http(
                server, "POST", path, body, timeout, upload_finished, headers_arrived,
                wait_for_generation=True, connected_socket=connected,
            )
            runtime.verify_identity(server)
        except Exception as exc:
            outcome["failure"] = exc
        finally:
            outcome["finished"] = time.monotonic()
            done.set()

    thread = threading.Thread(target=dispatch)
    thread.start()
    scans = []
    try:
        while not done.is_set():
            runtime.check()
            require(time.monotonic() < started + timeout, "quality request exceeded its deadline")
            if sent.is_set() and "headers" not in outcome and not scans:
                before = time.monotonic()
                witness = runtime.sample(server)
                after = time.monotonic()
                scans.append({"start": before, "end": after, "witness": witness})
            done.wait(0.05)
    finally:
        if not done.is_set():
            cancelled.set()
            sock = outcome.get("socket")
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass  # The request thread can close it before shutdown.
        thread.join()
        window = {name: outcome[name] for name in ("sent", "headers") if name in outcome}
        during = workload_guard.complete_scans({"request": window}, scans)
        relative_window = {name + "_s": stamp - started for name, stamp in window.items()}
        relative_scans = [scan | {"start": scan["start"] - started, "end": scan["end"] - started}
                          for scan in during]
        planner.write_new(directory / "during-request.json",
                          relative_window | {"finished_s": outcome["finished"] - started, "samples": relative_scans})
        http = {"endpoint": server.endpoint["endpoint"] + path, "request_sha256": pin}
        if "response" in outcome:
            status, raw = outcome["response"]
            write_bytes(directory / "response.raw.json", raw)
            http.update(status=status, response_sha256=sha(raw))
        if "failure" in outcome:
            http["transport_failure"] = str(outcome["failure"])
        planner.write_new(directory / "http.json", http)
    if "failure" in outcome:
        raise outcome["failure"]
    require(during, "no complete affinity, NUMA and backend witness inside the quality generation window")
    require(status == 200, f"quality endpoint returned HTTP {status}")
    runtime.check()
    return raw


def capture_record(item, shape, server, raw, row_id, arm):
    capture = {"request_sha256": item["request_sha256"], "response_b64": base64.b64encode(raw).decode("ascii"),
               "response_sha256": sha(raw)}
    if shape["profile"] == "dspark-dflash":
        path = shape["endpoint"]
        body = item["request_body"]
        _, limit = parity._request(body, path)
        # The native validator first checks the effective echo against the sent cap.
        parity._response(raw, path, body[parity.CAP_KEY], limit)
        result = parity._parse(raw)
        details = result if path == "/completion" else result["__verbose"]
        argv = server.endpoint["argv"]
        capture.update(server_instance=f"{row_id}:{arm}:{server.port}:{server.pid}:{server.birth}",
                       parallel_slots=int(argv[planner.value_index(argv, "-np")]),
                       effective_n_max=details["generation_settings"][parity.CAP_KEY])
    return capture


def run_endpoint(runtime, group, config, artifact_integrity, arm, state):
    endpoint = runtime.plan["endpoints"][0]
    output = runtime.output
    captures = {}
    try:
        require(state["signal"] is None, f"capture interrupted by signal {state['signal']}")
        state["runtime"] = runtime
        runtime.preflight()
        runtime.verify_model_inputs()
        workload_guard.check_workloads(runtime, output / "preload-workloads.json")
        for shape, _ in group:
            verify_shape(runtime.plan, endpoint, shape, artifact_integrity, config["models"])
        server = runtime.start(endpoint)
        startup = runtime.ready(server)
        proc = runner.PROC / str(server.pid)
        cmdline = (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        require(cmdline == [os.fsencode(arg) for arg in endpoint["argv"][6:]],
                "running process command line differs from the admitted recipe")
        runtime.verify_identity(server)
        require(startup["image"]["binary"]["sha256"] == runtime.plan["images"][endpoint["backend"]]["binary_sha256"],
                "witnessed binary differs from the prepared runtime image")
        planner.write_new(output / "startup.json", startup | {"process_argv": endpoint["argv"][6:]})
        for shape, items in group:
            verify_shape(runtime.plan, endpoint, shape, artifact_integrity, config["models"])
            for item in items:
                raw = capture_request(runtime, server, shape["endpoint"], item, output / item["id"])
                captures[item["id"]] = capture_record(item, shape, server, raw, runtime.admission.row_id, arm)
            verify_shape(runtime.plan, endpoint, shape, artifact_integrity, config["models"])
        workload_guard.check_workloads(runtime, output / "end-workloads.json")
        runtime.check()
    finally:
        try:
            cleanup = runtime.cleanup()
            expected = {str(server.pid) for server in runtime.servers}
            proved = runner.cleanup_proved(cleanup) and cleanup["servers"].keys() == expected
        except Exception as exc:
            cleanup = {"servers": {}, "spawn_unproved": True, "failure": f"{type(exc).__name__}: {exc}"}
            proved = False
        state["cleanup_proved"] = state["cleanup_proved"] and proved
        state["runtime"] = None
        planner.write_new(output / "cleanup.json", cleanup | {"cleanup_proved": proved})
        require(proved, "captured-PID cleanup was not proved")
    return captures


def capture_arm(arm, prepared, config, shapes, items, output, state):
    source, raw, plan = prepared
    directory = output / arm
    directory.mkdir(mode=0o700)
    write_bytes(directory / "prepared-plan.json", raw)
    require(state["signal"] is None, f"capture interrupted by signal {state['signal']}")
    admission = runner.Admission(plan)
    planner.write_new(directory / "admission.json", admission.witness())
    planner.write_new(directory / "host.json", evidence.host_snapshot())
    plan = runner.regenerate(plan, source.parent, directory / "artifact-ledger.json")
    from src.registry import artifact_integrity

    require(Path(artifact_integrity.__file__).resolve().is_relative_to(planner.ORCHESTRATOR.resolve(strict=True)),
            "artifact integrity did not load from the pinned orchestrator")
    if arm == "production":
        freeze = verify_production(plan, config["production_attestation"])
        write_bytes(directory / "production-freeze.json", freeze)

    groups = {}
    for shape_id, shape in sorted(shapes.items()):
        selected = endpoint_for(plan, config["mappings"][shape_id], shape)
        verify_shape(plan, selected, shape, artifact_integrity, config["models"])
        shape_items = [item for _, item in sorted(items.items()) if item["shape"] == shape_id]
        groups.setdefault(selected["port"], []).append((shape, shape_items))

    captures = {}
    for port, shape_items in sorted(groups.items()):
        endpoint_dir = directory / str(port)
        endpoint_dir.mkdir(mode=0o700)
        rebased = runner.rebase_plan_storage(plan, source.parent, endpoint_dir)
        endpoint = next(endpoint for endpoint in rebased["endpoints"] if endpoint["port"] == port)
        selected = rebased | {"endpoints": [endpoint], "images": {endpoint["backend"]: plan["images"][endpoint["backend"]]}}
        runtime = runner.Runtime(selected, endpoint_dir / "plan.json", endpoint_dir, admission,
                                 config["startup_timeout_s"], config["request_timeout_s"],
                                 plan_sha256=config["arms"][arm]["plan_sha256"])
        planner.write_new(endpoint_dir / "effective-endpoint.json", endpoint)
        captures.update(run_endpoint(runtime, shape_items, config, artifact_integrity, arm, state))
    admission.check()
    return captures


def seal(output, result):
    files = evidence.inventory(output)
    manifest = output / "MANIFEST.json"
    planner.write_new(manifest, {"schema": SCHEMA, "status": "observation_only",
                                 "capture_status": result["status"], "files": files})
    require(evidence.inventory(output) == files, "capture files changed during sealing")
    write_bytes(output / "COMPLETE", (planner.digest(manifest) + "\n").encode("ascii"))
    fd = os.open(output, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def execute(config, config_sha256, plans, shapes, items, output, state):
    result = {"schema": SCHEMA, "authority": "observation_only", "status": "incomplete",
              "quality_transfer_authorized": False, "promotion_authorized": False,
              "candidate_arm_started": False, "config_sha256": config_sha256}
    planner.write_new(output / "request-manifest.json", {
        "config_sha256": config_sha256,
        "rows": [{"id": item_id, "shape": item["shape"], "mapping": config["mappings"][item["shape"]],
                  "request_sha256": item["request_sha256"]} for item_id, item in sorted(items.items())],
    })
    shared = {"capture_source": config["capture_source"], "shapes": config["shapes"]}
    try:
        production = capture_arm("production", plans["production"], config, shapes, items, output, state)
        source = shared | {
            "schema": parity.SOURCE_SCHEMA, "runtime": config["arms"]["production"]["runtime"],
            "items": [{key: value for key, value in item.items() if key != "request_sha256"}
                      | {"production": production[item_id]} for item_id, item in sorted(items.items())],
        }
        write_bytes(output / "production-source.json", parity.pack_bytes(source))
        pack = parity.build_pack(source)
        missing_tokens = [item["id"] for item in pack["items"] if item["output_token_ids"] is None]
        missing_counts = [item["id"] for item in pack["items"] if item["completion_count"] is None]
        result.update(missing_production_token_ids=missing_tokens, missing_production_completion_counts=missing_counts)
        require(not missing_tokens and not missing_counts, "production pack lacks exposed token IDs or counts")
        require(state["cleanup_proved"], "production cleanup must be proved before pinning the bank")
        pack_path = output / "production-pack.json"
        pack_raw = parity.pack_bytes(pack)
        pack_pin = sha(pack_raw)
        write_bytes(pack_path, pack_raw)
        write_bytes(output / "production-pack.sha256", (pack_pin + "\n").encode("ascii"))
        planner.check_pin(pack_path, pack_pin)
        result["production_pack_sha256"] = pack_pin
        result["candidate_arm_started"] = True
        candidate = capture_arm("candidate", plans["candidate"], config, shapes, items, output, state)
        candidate_source = shared | {
            "schema": parity.CANDIDATE_SCHEMA, "runtime": config["arms"]["candidate"]["runtime"],
            "pack_sha256": pack_pin, "items": [{"id": key, "capture": value} for key, value in sorted(candidate.items())],
        }
        candidate_raw = parity.pack_bytes(candidate_source)
        write_bytes(output / "candidate-source.json", candidate_raw)
        require(state["cleanup_proved"] and state["signal"] is None, "candidate custody ended before comparison")
        _, pack_raw = pinned_bytes(pack_path, pack_pin)
        report = parity.capture_comparison(pack_raw, pack_pin, candidate_raw, output / "comparison.json")
        result.update(status=report["status"], comparison_sha256=planner.digest(output / "comparison.json"))
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}: {exc}"
    result["cleanup_proved"] = state["cleanup_proved"]
    planner.write_new(output / "result.json", result)
    if state["cleanup_proved"]:
        seal(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    state = {"cleanup_proved": True, "signal": None, "runtime": None}

    def interrupt(signum, _frame):
        state["signal"] = signum
        if state["runtime"] is not None:
            state["runtime"].interrupted = signum

    try:
        config, raw, plans, shapes, items = load_config(args.config, args.config_sha256, args.out)
        args.out.mkdir(mode=0o700)
        write_bytes(args.out / "config.json", raw)
        previous = {sig: signal.signal(sig, interrupt) for sig in runner.SIGNALS}
        try:
            result = execute(config, args.config_sha256, plans, shapes, items, args.out, state)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        print(parity.canonical_json(result).decode("utf-8"))
        return {"pass": 0, "fail": 1}.get(result["status"], 2)
    except (OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"live quality capture refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
