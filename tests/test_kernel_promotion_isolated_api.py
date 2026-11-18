"""Fixture checks for the promotion candidate's forced API smoke."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "scripts/benchmark/kernel_promotion_isolated_api.py"
MODULE = importlib.util.spec_from_file_location("kernel_promotion_isolated_api", SOURCE)
isolated = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(isolated)
URL = "http://127.0.0.1:18600"


def endpoint(role="frontdoor", kind="chat", url=URL):
    return {"role": role, "kind": kind, "base_url": url}


def manifest(*entries):
    return {"schema": isolated.MANIFEST_SCHEMA, "endpoints": list(entries)}


def test_selects_one_manifest_endpoint_and_creates_single_role_request():
    entries = manifest(endpoint(), endpoint(role="embedder", kind="embedding", url="http://127.0.0.1:18601"))
    assert isolated.select_endpoint(entries, "frontdoor", None, {8080}) == (URL, 18600)
    payload = isolated.request_payload("frontdoor", URL, 30)
    assert payload["server_urls"] == {"frontdoor": URL}
    assert payload["force_role"] == "frontdoor" and payload["force_mode"] == "direct"
    assert payload["real_mode"] and not payload["mock_mode"]
    assert not payload["allow_delegation"] and not payload["cache_prompt"]


def test_requires_explicit_port_for_multiple_role_instances():
    entries = manifest(endpoint(), endpoint(url="http://127.0.0.1:18601"))
    with pytest.raises(ValueError, match="choose one with --port"):
        isolated.select_endpoint(entries, "frontdoor", None, set())
    assert isolated.select_endpoint(entries, "frontdoor", 18601, set()) == ("http://127.0.0.1:18601", 18601)


@pytest.mark.parametrize("role, kind", [("", "chat"), ("coder_escalation", "chat"), ("frontdoor", "embedding")])
def test_refuses_absent_or_unservable_roles(role, kind):
    with pytest.raises(ValueError, match="forced role"):
        isolated.select_endpoint(manifest(endpoint(kind=kind)), role, None, set())


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:18601",
        "http://192.0.2.5:18601",
        "http://[::1]:18601",
        "http://127.0.0.1:18601/",
        "http://127.0.0.1:18601?x=y",
        "http://127.0.0.1:18601@192.0.2.5",
        "http://127.0.0.1:18601,http://127.0.0.1:8080",
        "full:http://127.0.0.1:18601",
    ],
)
def test_refuses_noncanonical_urls_anywhere_in_manifest(url):
    entries = manifest(endpoint(), endpoint(role="architect_general", url=url))
    with pytest.raises(ValueError, match="canonical IPv4 loopback"):
        isolated.select_endpoint(entries, "frontdoor", None, set())


def test_collects_pool_default_alias_and_service_ports():
    ports = isolated.configured_ports([
        "full:http://localhost:8070,http://localhost:8080",
        "http://[::1]:8083",
        "http://serving-alias.example:8000/v1/vision/analyze",
        "https://service.example",
    ])
    assert ports == {8070, 8080, 8083, 8000, 443}
    entries = manifest(endpoint(), endpoint(role="coder_escalation", url="http://127.0.0.1:8083"))
    with pytest.raises(ValueError, match="production or default port refused: 8083"):
        isolated.select_endpoint(entries, "frontdoor", None, ports)


def test_socket_fence_refuses_all_except_the_selected_ipv4_address():
    fence = isolated.SocketFence()
    with pytest.raises(PermissionError):
        fence.audit("socket.connect", (None, ("127.0.0.1", 18600)))
    fence.allowed = ("127.0.0.1", 18600)
    fence.audit("socket.connect", (None, ("127.0.0.1", 18600)))
    with pytest.raises(PermissionError):
        fence.audit("socket.connect", (None, ("127.0.0.1", 8080)))
    with pytest.raises(PermissionError):
        fence.audit("socket.connect", (None, ("192.0.2.5", 18600)))
    assert len(fence.denied) == 3


def test_primitives_cannot_merge_defaults_or_fall_back():
    backend = SimpleNamespace(config=SimpleNamespace(base_url=URL))
    primitives = SimpleNamespace(
        server_urls_source="request", server_urls={"frontdoor": URL}, model_server=None,
        _backends={"frontdoor": SimpleNamespace(backend=backend)},
    )
    assert isolated.verify_primitives(primitives, "frontdoor", URL) is backend
    primitives.server_urls["worker_general"] = "http://127.0.0.1:8080"
    with pytest.raises(ValueError, match="rewrote or merged"):
        isolated.verify_primitives(primitives, "frontdoor", URL)
    del primitives.server_urls["worker_general"]
    primitives.model_server = object()
    with pytest.raises(ValueError, match="legacy model fallback"):
        isolated.verify_primitives(primitives, "frontdoor", URL)


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({}, 503),
        ({"routed_to": "worker_general"}, 200),
        ({"role_history": ["frontdoor", "worker_general"]}, 200),
        ({"routing_strategy": "forced:nonserving_fenced"}, 200),
        ({"mock_mode": True}, 200),
        ({"real_mode": False}, 200),
        ({"answer": "[ERROR: unavailable]"}, 200),
        ({"error_detail": {"type": "fallback"}}, 200),
    ],
)
def test_refuses_fallback_mock_and_error_responses(changes, status):
    body = {
        "routed_to": "frontdoor", "role_history": ["frontdoor"], "routing_strategy": "forced",
        "real_mode": True, "mock_mode": False, "mode": "direct", "answer": "ok",
    }
    outbound = [{"method": "POST", "path": "/completion", "status_code": 200}]
    isolated.verify_response(body, 200, "frontdoor", outbound)
    with pytest.raises(ValueError):
        isolated.verify_response(body | changes, status, "frontdoor", outbound)
    with pytest.raises(ValueError, match="exactly one successful upstream generation"):
        isolated.verify_response(body, 200, "frontdoor", [])


def test_real_chat_route_uses_only_selected_mock_backend(tmp_path):
    # The publisher Python has no FastAPI dependencies. The child runs in the
    # orchestrator environment with an in-memory llama transport and zero sockets.
    fixture = r"""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

source, output, orchestrator = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("isolated_api", source)
isolated = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isolated)
isolated.private_environment(output)
sys.path.insert(0, str(orchestrator))

import httpx
import httpx._client

def no_connections(event, args):
    if event == "socket.connect":
        raise AssertionError(f"memory-only fixture attempted a socket connection: {args[1]!r}")

sys.addaudithook(no_connections)
url = "http://127.0.0.1:18600"
assert {8000, 8080, 8083, 19111} <= isolated.forbidden_ports(["http://localhost:19111"])

def fake_server(request):
    assert (request.url.scheme, request.url.host, request.url.port) == ("http", "127.0.0.1", 18600)
    if request.method == "GET":
        assert request.url.path in {"/props", "/slots", "/metrics", "/health"}
        return httpx.Response(404)
    assert request.url.path in isolated.GENERATION_PATHS
    raw = request.read()
    assert b"Return the single word ok." in raw
    streaming = json.loads(raw).get("stream", False)
    if request.url.path == "/completion":
        body = {"content": "ok", "stop": True, "stop_type": "stop",
                "tokens_evaluated": 8, "tokens_predicted": 1}
    else:
        content_key = "delta" if streaming else "message"
        body = {"choices": [{"index": 0, content_key: {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 1}}
    if streaming:
        return httpx.Response(200, content=f"data: {json.dumps(body)}\n\ndata: [DONE]\n\n")
    return httpx.Response(200, json=body)

def mock_transport(**kwargs):
    return httpx.MockTransport(fake_server)

fence = isolated.SocketFence()
result = {"outbound": []}
with patch.object(httpx, "HTTPTransport", mock_transport), patch.object(
    httpx._client, "HTTPTransport", mock_transport
):
    isolated.run_isolated_chat("frontdoor", url, 18600, 10, output, fence, result)
(output / "test-result.json").write_text(json.dumps(result))
"""
    orchestrator = isolated.planner.ORCHESTRATOR
    completed = subprocess.run(
        [str(orchestrator / ".venv/bin/python"), "-I", "-B", "-c", fixture,
         str(SOURCE), str(tmp_path), str(orchestrator)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    request = json.loads((tmp_path / "request.json").read_bytes())
    response = json.loads((tmp_path / "response.body").read_bytes())
    observed = json.loads((tmp_path / "test-result.json").read_bytes())
    assert request["server_urls"] == {"frontdoor": URL}
    assert response["routed_to"] == "frontdoor" and response["answer"] == "ok"
    assert observed["server_urls_source"] == "request"
    assert any(row["status_code"] == 200 and row["method"] == "POST" for row in observed["outbound"])
