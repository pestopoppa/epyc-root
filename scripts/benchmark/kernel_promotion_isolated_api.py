#!/usr/bin/env python3
"""Exercise the orchestrator's forced /chat route against one planned endpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import time
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
TRACE_EVENTS = {
    "http11.send_request_headers.started": "dispatch",
    "http11.send_request_body.complete": "sent",
    "http11.receive_response_headers.complete": "headers",
}
require = planner.require


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


def request_payload(role, url, timeout):
    return {
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


def run_isolated_chat(role, url, port, timeout, output, fence, result, witness=None):
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
    payload = request_payload(role, url, timeout)
    require(ChatRequest.model_validate(payload).force_role == role, "API changed the forced role")
    app = FastAPI()
    app.add_api_route("/chat", chat_module.chat, methods=["POST"])
    state = AppState(admission=AdmissionController({url: 1}), q_scorer_enabled=False, _memrl_initialized=True)
    app.dependency_overrides[dep_app_state] = lambda: state
    init_primitives = chat_module._init_primitives
    send = httpx.Client.send
    backends = []
    outbound = result["outbound"]

    def checked_primitives(request, request_state):
        require(request_state is state and request.real_mode and request.force_role == role
                and request.server_urls == {role: url}, "request reached primitives without its isolated mapping")
        primitives = init_primitives(request, request_state)
        backends.append(verify_primitives(primitives, role, url))
        result["server_urls_source"] = primitives.server_urls_source
        return primitives

    def checked_send(client, request, **kwargs):
        if client is api_client:
            return send(client, request, **kwargs)
        target = request.url
        row = {"method": request.method, "path": target.path, "url": str(target)}
        outbound.append(row)
        metadata = request.method == "GET" and target.path in {"/props", "/slots", "/metrics", "/health"}
        bound_client = len(backends) == 1 and client is backends[0].client
        allowed = ((bound_client or metadata)
                   and (target.scheme, target.host, target.port) == ("http", "127.0.0.1", port))
        row["allowed"] = allowed
        require(allowed, f"isolated API refused HTTP destination {target}")
        if witness is not None:
            request_id = len(outbound)
            generation = request.method == "POST" and target.path in GENERATION_PATHS
            witness("connect", request_id)

            def trace(name, _info):
                event = TRACE_EVENTS.get(name)
                if event == "dispatch" or (event is not None and generation):
                    witness(event, request_id)

            request.extensions["trace"] = trace
        kwargs["follow_redirects"] = False
        response = send(client, request, **kwargs)
        row["status_code"] = response.status_code
        return response

    try:
        with TestClient(app, raise_server_exceptions=False) as api_client:
            request = api_client.build_request("POST", "/chat", json=payload)
            (output / "request.json").write_bytes(request.content)
            with patch.object(chat_module, "_init_primitives", checked_primitives), patch.object(
                httpx.Client, "send", checked_send
            ):
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
    args = parser.parse_args(argv)
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
        if args.witness_fd is None:
            run_isolated_chat(args.role, url, port, args.timeout, output, fence, result)
        else:
            with socket.socket(fileno=args.witness_fd) as channel:
                channel.settimeout(args.timeout)

                def witness(event, request_id):
                    channel.send(json.dumps([event, request_id, time.monotonic_ns()]).encode())
                    if event in {"connect", "dispatch"}:
                        require(channel.recv(16) == b"allow", "hot-stack runner refused upstream dispatch")

                run_isolated_chat(args.role, url, port, args.timeout, output, fence, result, witness)
        result["status"] = "passed"
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        print(result["error"], file=sys.stderr)
    planner.write_new(output / "result.json", result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
