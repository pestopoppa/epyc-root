#!/usr/bin/env python3
"""Exercise the orchestrator's forced /chat route against one planned endpoint."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import stat
import sys
import time
from contextlib import ExitStack
from contextvars import ContextVar
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_promotion_hot_stack as planner


MANIFEST_SCHEMA = "epyc.kernel_promotion_isolated_endpoints.v1"
RESULT_SCHEMA = "epyc.kernel_promotion_isolated_api_observation.v1"
ROLE_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}")
LOOPBACK_URL = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{3,4})")
GENERATION_PATHS = {"/completion", "/v1/chat/completions"}
VISION_ROLE = "worker_vision"
VISION_PATH = "/v1/chat/completions"
VISION_PROMPT = "What color and shape is centered in the image? Answer with the color and shape only."
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 1024 * 1024
TRACE_EVENTS = {
    "http11.send_request_headers.started": "dispatch",
    "http11.send_request_body.complete": "sent",
    "http11.receive_response_headers.complete": "headers",
}
require = planner.require


def add_image_options(parser, prefix=""):
    parser.add_argument(f"--{prefix}image", type=Path, help="canonical path to a prepared vision-smoke PNG")
    parser.add_argument(f"--{prefix}image-sha256", help="prepared SHA-256 of the PNG")


def image_options(parser, role, path, checksum, prefix=""):
    if path is None and checksum is None:
        return None
    if path is None or not planner.is_hash(checksum):
        parser.error(f"--{prefix}image and --{prefix}image-sha256 require a path and a paired SHA-256")
    if role != VISION_ROLE:
        parser.error(f"--{prefix}image requires the {VISION_ROLE} role")
    return {"path": str(path), "sha256": checksum}


def read_image(pin):
    path = Path(pin["path"])
    require(path.is_absolute() and path.resolve(strict=True) == path,
            f"expected a canonical prepared PNG path: {path}")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and len(PNG_SIGNATURE) < before.st_size <= MAX_IMAGE_BYTES,
                "prepared image must be a regular PNG of at most 1 MiB")
        raw = stream.read(MAX_IMAGE_BYTES + 1)
        require(len(raw) == before.st_size and _input_stat(before) == _input_stat(os.fstat(stream.fileno()))
                == _input_stat(path.stat()),
                f"prepared image changed while reading: {path}")
    require(raw.startswith(PNG_SIGNATURE) and hashlib.sha256(raw).hexdigest() == pin["sha256"],
            f"prepared PNG or SHA-256 changed: {path}")
    return raw


def _input_stat(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def verify_mmproj(endpoint):
    argv = endpoint["argv"]
    index = planner.value_index(argv, "--mmproj")
    source = Path(argv[index])
    path = source.resolve(strict=True)
    pins = [model for model in endpoint["models"] if model["path"] == str(path)]
    info = path.stat()
    require(source.is_absolute() and stat.S_ISREG(info.st_mode) and info.st_size > 0 and len(pins) == 1
            and pins[0]["stat"] == _input_stat(info),
            f"prepared --mmproj input is missing or changed: {source}")
    return pins[0]


def verify_vision_projector(plan, url):
    matches = [endpoint for endpoint in plan["endpoints"]
               if endpoint["endpoint"] == url and endpoint["test"] == "chat"
               and endpoint["roles"][0] == VISION_ROLE]
    require(len(matches) == 1, "expected one prepared worker_vision chat endpoint with --mmproj")
    return verify_mmproj(matches[0])


def verify_outbound_image(raw, expected_sha256):
    body = json.loads(raw, object_pairs_hook=planner.unique_keys)
    messages = body.get("messages") if isinstance(body, dict) else None
    require(isinstance(messages, list), "vision upstream request is missing its messages")
    parts = [part for message in messages if isinstance(message, dict)
             and isinstance(message.get("content"), list)
             for part in message["content"] if isinstance(part, dict) and part.get("type") == "image_url"]
    require(len(parts) == 1 and len(messages) == 1 and messages[0].get("role") == "user",
            "vision upstream request must carry exactly one user image")
    image = parts[0].get("image_url")
    data_url = image.get("url") if isinstance(image, dict) else None
    prefix = "data:image/png;base64,"
    require(isinstance(data_url, str) and data_url.startswith(prefix),
            "vision upstream image must be an inline PNG")
    decoded = base64.b64decode(data_url.removeprefix(prefix), validate=True)
    require(hashlib.sha256(decoded).hexdigest() == expected_sha256,
            "vision upstream image differs from the prepared SHA-256")
    return {"image_sha256": expected_sha256, "request_sha256": hashlib.sha256(raw).hexdigest()}


def configured_ports(urls):
    """Extract default, pool, alias, and service ports regardless of hostname."""
    ports = set()
    for value in urls:
        for url in value.split(","):
            parsed = urlsplit(url.strip().removeprefix("full:"))
            require(parsed.scheme in {"http", "https"} and parsed.hostname,
                    f"invalid configured backend URL: {url!r}")
            ports.add(parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80))
    return ports


def forbidden_ports(inherited_defaults):
    from scripts.server import stack_manifest
    from src.config import get_config
    from src.config.models import _LEGACY_SERVER_URL_FALLBACKS

    ports = set(stack_manifest.PORT_MAP.values())
    ports.update(service.port for service in stack_manifest.AUX_SERVICES.values())
    ports.update(server["port"] for server in stack_manifest.HOT_SERVERS + stack_manifest.WARM_SERVERS)
    config = get_config()
    ports.update(configured_ports([
        *asdict(config.server_urls).values(), config.server.default_url,
        *_LEGACY_SERVER_URL_FALLBACKS.values(), *inherited_defaults,
    ]))
    return ports


def select_endpoint(manifest, role, port, blocked_ports):
    planner.validate_keys(manifest, {"schema", "endpoints"}, "endpoint manifest")
    require(manifest["schema"] == MANIFEST_SCHEMA, "unknown endpoint manifest schema")
    endpoints = manifest["endpoints"]
    require(isinstance(endpoints, list) and endpoints, "empty or invalid endpoint list")
    require(isinstance(role, str) and ROLE_PATTERN.fullmatch(role), "a valid forced role is required")
    selected = []
    seen = set()
    for entry in endpoints:
        planner.validate_keys(entry, {"role", "kind", "base_url"}, "endpoint")
        name, kind, url = (entry[key] for key in ("role", "kind", "base_url"))
        require(isinstance(name, str) and ROLE_PATTERN.fullmatch(name), "invalid manifest role")
        require(kind in ("chat", "embedding"), "invalid endpoint kind")
        match = LOOPBACK_URL.fullmatch(url) if isinstance(url, str) else None
        require(match is not None, f"expected a canonical IPv4 loopback HTTP base URL: {url!r}")
        candidate_port = int(match[1])
        require(1024 <= candidate_port <= 65535, f"isolated port outside permitted range: {candidate_port}")
        require(candidate_port not in blocked_ports, f"production or default port refused: {candidate_port}")
        require(candidate_port not in seen, f"duplicate manifest port: {candidate_port}")
        seen.add(candidate_port)
        if kind == "chat" and name == role and (port is None or candidate_port == port):
            selected.append((url, candidate_port))
    require(selected, f"no chat endpoint for forced role {role!r} and selected port")
    require(len(selected) == 1, f"multiple chat endpoints for {role!r}; choose one with --port")
    return selected[0]


class SocketFence:
    """Default-deny Python socket connects throughout the dedicated CLI process."""

    def __init__(self):
        self.allowed = None
        self.denied = []

    def audit(self, event, args):
        if event == "socket.connect":
            address = args[1]
            if self.allowed is None or address != self.allowed:
                self.denied.append(repr(address))
                raise PermissionError(f"isolated API refused socket destination {address!r}")


def private_environment(output):
    inherited_defaults = [
        value for key, value in os.environ.items()
        if (key.upper().startswith("ORCHESTRATOR_SERVER_URLS_")
            or key.upper() == "ORCHESTRATOR_SERVER_DEFAULT_URL") and value
    ]
    for key in list(os.environ):
        if key.upper().startswith("ORCHESTRATOR_") or key.lower().endswith("_proxy"):
            del os.environ[key]
    os.environ.update({
        "ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS": "1",
        "ORCHESTRATOR_RUNTIME_FLAGS_PATH": str(output / "runtime-flags.json"),
        "ORCHESTRATOR_TMP_DIR": str(output),
        "ORCHESTRATOR_PATHS_TMP_DIR": str(output),
        "ORCHESTRATOR_PATHS_LOG_DIR": str(output),
        "ORCHESTRATOR_GPU_WINDOW_FILE": "off",
        "ORCHESTRATOR_SERVING_CALLS_LOG": "off",
        "ORCHESTRATOR_SERVING_CALLS_PRIVATE_LOG": "off",
        "ORCHESTRATOR_DISPATCH_LOG": "off",
    })
    os.chdir(output)
    return inherited_defaults


def request_payload(role, url, timeout, image=None):
    payload = {
        "prompt": "Return the single word ok.",
        "force_role": role,
        "force_mode": "direct",
        "allow_delegation": False,
        "real_mode": True,
        "mock_mode": False,
        "cache_prompt": False,
        "max_turns": 1,
        "max_tokens": 8,
        "timeout_s": timeout,
        "quiescent_after": True,
        "x_request_source": "smoke",
        "server_urls": {role: url},
    }
    if image is not None:
        require(role == VISION_ROLE, f"image requests require {VISION_ROLE}")
        payload.update(prompt=VISION_PROMPT, image_base64=base64.b64encode(image).decode("ascii"))
    return payload


def verify_primitives(primitives, role, url):
    require(primitives.server_urls_source == "request", "primitive URLs are not request-sourced")
    require(primitives.server_urls == {role: url}, "primitives rewrote or merged the isolated mapping")
    require(primitives.model_server is None, "legacy model fallback is enabled")
    require(set(primitives._backends) == {role}, "primitives did not construct exactly the selected role")
    backend = primitives._backends[role].backend
    require(backend.config.base_url == url, "constructed backend differs from isolated endpoint")
    return backend


def verify_response(body, status, role, outbound):
    require(status == 200 and isinstance(body, dict), f"isolated /chat failed with HTTP {status}")
    require(body.get("routed_to") == role and body.get("role_history") == [role]
            and body.get("routing_strategy") == "forced", "API did not serve exactly the forced role")
    require(body.get("mode") == "direct" and body.get("real_mode") is True
            and body.get("mock_mode") is False, "API did not run real direct chat")
    answer = body.get("answer")
    require(isinstance(answer, str) and answer.strip() and not answer.lstrip().startswith("[ERROR")
            and not any(body.get(key) for key in ("error", "error_code", "error_detail")),
            "API returned no successful answer")
    generations = [call for call in outbound if call["method"] == "POST" and call["path"] in GENERATION_PATHS]
    require(len(generations) == 1 and generations[0].get("status_code") == 200,
            "expected exactly one successful upstream generation")


def run_isolated_chat(role, url, port, timeout, output, fence, result, witness=None, *, image=None):
    import httpx
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.api.admission import AdmissionController
    from src.api.dependencies import dep_app_state
    from src.api.models.requests import ChatRequest
    from src.api.routes import chat as chat_module
    from src.api.state import AppState
    from src.features import Features, set_features
    from src.roles import Role

    require(Role.from_string(role) is not None, f"role is unknown to the orchestrator: {role!r}")
    set_features(Features(tools=False, repl=False, semantic_classifiers=False, generation_monitor=False))
    payload = request_payload(role, url, timeout, image)
    validated = ChatRequest.model_validate(payload)
    require(validated.force_role == role, "API changed the forced role")
    if image is not None:
        require(validated.image_base64 == payload["image_base64"], "API changed the prepared image")
    app = FastAPI()
    app.add_api_route("/chat", chat_module.chat, methods=["POST"])
    state = AppState(admission=AdmissionController({url: 1}), q_scorer_enabled=False, _memrl_initialized=True)
    app.dependency_overrides[dep_app_state] = lambda: state
    init_primitives = chat_module._init_primitives
    send = httpx.Client.send
    async_send = httpx.AsyncClient.send
    backends = []
    outbound = result["outbound"]
    vision_primitives = ContextVar("isolated_vision_primitives", default=None)

    def check_request(request, request_state):
        require(request_state is state and request.real_mode and request.force_role == role
                and request.server_urls == {role: url}, "request reached primitives without its isolated mapping")
        if image is not None:
            require(request.image_base64 == payload["image_base64"] and request.image_path is None
                    and not request.files and request.force_mode == "direct" and request.prompt == VISION_PROMPT,
                    "isolated vision request changed its image, mode, or prompt")

    def checked_primitives(request, request_state):
        check_request(request, request_state)
        primitives = init_primitives(request, request_state)
        backends.append(verify_primitives(primitives, role, url))
        result["server_urls_source"] = primitives.server_urls_source
        return primitives

    def trace_upstream(generation):
        request_id = len(outbound)
        witness("connect", request_id)

        def trace(name, _info):
            event = TRACE_EVENTS.get(name)
            if event == "dispatch" or (event is not None and generation):
                witness(event, request_id)

        return trace

    def checked_send(client, request, **kwargs):
        if client is api_client:
            return send(client, request, **kwargs)
        target = request.url
        row = {"method": request.method, "path": target.path, "url": str(target)}
        outbound.append(row)
        metadata = request.method == "GET" and target.path in {"/props", "/slots", "/metrics", "/health"}
        bound_client = image is None and len(backends) == 1 and client is backends[0].client
        allowed = ((bound_client or metadata)
                   and (target.scheme, target.host, target.port) == ("http", "127.0.0.1", port))
        row["allowed"] = allowed
        require(allowed, f"isolated API refused HTTP destination {target}")
        if witness is not None:
            generation = request.method == "POST" and target.path in GENERATION_PATHS
            request.extensions["trace"] = trace_upstream(generation)
        kwargs["follow_redirects"] = False
        response = send(client, request, **kwargs)
        row["status_code"] = response.status_code
        return response

    async def checked_async_send(client, request, **kwargs):
        target = request.url
        row = {"method": request.method, "path": target.path, "url": str(target), "allowed": False}
        outbound.append(row)
        require(vision_primitives.get() is not None and request.method == "POST"
                and str(target) == f"{url}{VISION_PATH}", f"isolated vision refused HTTP destination {target}")
        raw = request.content
        with (output / "upstream-request.json").open("xb") as stream:
            stream.write(raw)
        row.update(verify_outbound_image(raw, hashlib.sha256(image).hexdigest()))
        row["allowed"] = True
        if witness is not None:
            trace = trace_upstream(True)

            async def async_trace(name, info):
                trace(name, info)

            request.extensions["trace"] = async_trace
        kwargs["follow_redirects"] = False
        response = await async_send(client, request, **kwargs)
        row["status_code"] = response.status_code
        return response

    def isolate_vision(stack):
        from src.api.routes import chat_vision
        from src.services import document_client

        handle_vision = chat_vision._handle_vision_request

        async def skip_document_preprocessing(request, _routing, primitives, request_state, _start):
            check_request(request, request_state)
            verify_primitives(primitives, role, url)

        async def checked_vision(request, primitives, request_state, task_id, force_server=None):
            check_request(request, request_state)
            require(force_server == role == VISION_ROLE, "multimodal handler changed the forced role")
            require(not chat_vision._needs_structured_analysis(request.prompt),
                    "isolated vision prompt selects the structured analysis service")
            token = vision_primitives.set(primitives)
            try:
                return await handle_vision(request, primitives, request_state, task_id, force_server)
            finally:
                vision_primitives.reset(token)

        def checked_vision_url(requested_role):
            primitives = vision_primitives.get()
            require(primitives is not None and requested_role == role, "unbound vision role refused")
            verify_primitives(primitives, role, url)
            return primitives.server_urls[role]

        def refuse_ocr():
            raise RuntimeError("OCR is disabled for the isolated vision request")

        stack.enter_context(patch.object(chat_module, "_execute_vision", skip_document_preprocessing))
        stack.enter_context(patch.object(chat_vision, "_handle_vision_request", checked_vision))
        stack.enter_context(patch.object(chat_vision, "_vl_url_for_role", checked_vision_url))
        stack.enter_context(patch.object(document_client, "get_document_client", refuse_ocr))
        stack.enter_context(patch.object(httpx.AsyncClient, "send", checked_async_send))
        result["vision_scope"] = "direct_multimodal_without_document_preprocessing_or_ocr"

    try:
        with TestClient(app, raise_server_exceptions=False) as api_client:
            request = api_client.build_request("POST", "/chat", json=payload)
            (output / "request.json").write_bytes(request.content)
            with ExitStack() as stack:
                stack.enter_context(patch.object(chat_module, "_init_primitives", checked_primitives))
                stack.enter_context(patch.object(httpx.Client, "send", checked_send))
                if image is not None:
                    isolate_vision(stack)
                fence.allowed = ("127.0.0.1", port)
                response = api_client.send(request)
                fence.allowed = None
            (output / "response.body").write_bytes(response.content)
            result["http_status"] = response.status_code
            require(not fence.denied and all(call["allowed"] for call in outbound),
                    "API attempted a connection outside its isolated backend")
            require(len(backends) == 1, "route did not construct exactly one request-scoped backend")
            verify_response(response.json(), response.status_code, role, outbound)
    finally:
        fence.allowed = None
        for backend in backends:
            backend.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--port", type=int, help="disambiguate repeated rows for the forced role")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--witness-fd", type=int, help=argparse.SUPPRESS)
    add_image_options(parser)
    args = parser.parse_args(argv)
    image_pin = image_options(parser, args.role, args.image, args.image_sha256)
    if image_pin is not None and args.witness_fd is None:
        parser.error("--image requires the live runner's dispatch witness")
    try:
        require(1 <= args.timeout <= 3600, "invalid request timeout")
        plan_raw = args.plan.read_bytes()
        require(hashlib.sha256(plan_raw).hexdigest() == args.plan_sha256, "prepared plan digest mismatch")
        plan = json.loads(plan_raw, object_pairs_hook=planner.unique_keys)
        require(isinstance(plan, dict) and plan.get("schema") == planner.PLAN_SCHEMA
                and plan.get("status") == "prepared_only", "expected the prepared hot-stack plan")
        orchestrator = planner.check_stack_inputs(plan["spec"])
        output = args.output_dir
        require(output.is_absolute() and output.resolve() == output and output.is_relative_to(planner.SCRATCH)
                and output != planner.SCRATCH, "expected a canonical output directory under scratch")
        output.mkdir(mode=0o700)
    except (OSError, TypeError, KeyError, ValueError) as exc:
        parser.error(str(exc))

    fence = SocketFence()
    sys.addaudithook(fence.audit)
    result = {
        "schema": RESULT_SCHEMA,
        "authority": "observation_only",
        "plan_sha256": args.plan_sha256,
        "role": args.role,
        "outbound": [],
        "denied_sockets": fence.denied,
    }
    try:
        inherited_defaults = private_environment(output)
        sys.path.insert(0, str(orchestrator))
        url, port = select_endpoint(plan["endpoint_manifest"], args.role, args.port, forbidden_ports(inherited_defaults))
        result["base_url"] = url
        image = None
        if image_pin is not None:
            image = read_image(image_pin)
            result.update(image=image_pin, mmproj=verify_vision_projector(plan, url))
        if args.witness_fd is None:
            run_isolated_chat(args.role, url, port, args.timeout, output, fence, result)
        else:
            with socket.socket(fileno=args.witness_fd) as channel:
                channel.settimeout(args.timeout)

                def witness(event, request_id):
                    channel.send(json.dumps([event, request_id, time.monotonic_ns()]).encode())
                    if event in {"connect", "dispatch"}:
                        require(channel.recv(16) == b"allow", "hot-stack runner refused upstream dispatch")

                run_isolated_chat(args.role, url, port, args.timeout, output, fence, result, witness,
                                  image=image)
        if image_pin is not None:
            read_image(image_pin)
            require(verify_vision_projector(plan, url) == result["mmproj"],
                    "prepared --mmproj input changed during the isolated API request")
        result["status"] = "passed"
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        print(result["error"], file=sys.stderr)
    planner.write_new(output / "result.json", result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
