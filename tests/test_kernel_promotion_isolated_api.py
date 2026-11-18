"""Fixture checks for the promotion candidate's forced API smoke."""

import base64
import hashlib
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
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jD3sAAAAASUVORK5CYII="
)


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
    assert "image_base64" not in isolated.request_payload("worker_vision", URL, 30)


def test_prepared_png_is_read_only_by_canonical_path_and_digest(tmp_path):
    path = tmp_path / "prepared.png"
    path.write_bytes(PNG)
    pin = {"path": str(path), "sha256": hashlib.sha256(PNG).hexdigest()}
    assert isolated.read_image(pin) == PNG
    alias = tmp_path / "alias.png"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="canonical prepared PNG"):
        isolated.read_image(pin | {"path": str(alias)})
    path.write_bytes(PNG + b"mutation")
    with pytest.raises(ValueError, match="SHA-256 changed"):
        isolated.read_image(pin)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        isolated.read_image(pin)


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


@pytest.mark.parametrize("mode", ["text", "image", "missing-image", "changed-image", "foreign-vision"])
def test_real_chat_route_uses_only_selected_mock_backend(tmp_path, mode):
    # The publisher Python has no FastAPI dependencies. The child runs in the
    # orchestrator environment with an in-memory llama transport and zero sockets.
    fixture = r"""
import base64
import importlib.util
import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

source, output, orchestrator = map(Path, sys.argv[1:4])
mode, encoded_png = sys.argv[4:]
spec = importlib.util.spec_from_file_location("isolated_api", source)
isolated = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isolated)
isolated.private_environment(output)
sys.path.insert(0, str(orchestrator))

import httpx
import httpx._client
from httpcore._trace import Trace
from src.api.routes import chat_vision
from src.services import document_client

def no_connections(event, args):
    if event == "socket.connect":
        raise AssertionError(f"memory-only fixture attempted a socket connection: {args[1]!r}")

sys.addaudithook(no_connections)
url = "http://127.0.0.1:18600"
assert {8000, 8080, 8083, 19111} <= isolated.forbidden_ports(["http://localhost:19111"])

def fake_server(request):
    assert (request.url.scheme, request.url.host, request.url.port) == ("http", "127.0.0.1", 18600)
    logger = logging.getLogger("httpcore.http11")
    with Trace("send_request_headers", logger, request):
        pass
    with Trace("send_request_body", logger, request):
        raw = request.read()
    with Trace("receive_response_headers", logger, request):
        return fake_response(request, raw)

def fake_response(request, raw):
    if request.method == "GET":
        assert request.url.path in {"/props", "/slots", "/metrics", "/health"}
        return httpx.Response(404)
    assert request.url.path in isolated.GENERATION_PATHS
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

async def fake_vision(request):
    assert mode == "image", "only pinned image requests can reach the transport"
    assert request.method == "POST"
    assert str(request.url) == f"{url}/v1/chat/completions"
    logger = logging.getLogger("httpcore.http11")
    async with Trace("send_request_headers", logger, request):
        pass
    async with Trace("send_request_body", logger, request):
        raw = await request.aread()
    async with Trace("receive_response_headers", logger, request):
        data = json.loads(raw)
        content = data["messages"][0]["content"]
        assert content[0]["image_url"]["url"] == f"data:image/png;base64,{encoded_png}"
        assert isolated.VISION_PROMPT in content[1]["text"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "red square"}}]})

def mock_async_transport(**kwargs):
    return httpx.MockTransport(fake_vision)

post = httpx.AsyncClient.post

async def exercise_refusals(client, destination, **kwargs):
    if destination == f"{url}/v1/chat/completions":
        if mode == "missing-image":
            kwargs["json"]["messages"][0]["content"].pop(0)
        elif mode == "changed-image":
            kwargs["json"]["messages"][0]["content"][0]["image_url"]["url"] = "data:image/png;base64,aW52YWxpZA=="
        elif mode == "foreign-vision":
            destination = "http://127.0.0.1:8086/v1/chat/completions"
    return await post(client, destination, **kwargs)

def production_service(*args, **kwargs):
    raise AssertionError("real production vision resolver or OCR client was invoked")

fence = isolated.SocketFence()
result = {"outbound": [], "witness_events": []}

def witness(event, request_id):
    result["witness_events"].append([event, request_id])

role, image = ("frontdoor", None) if mode == "text" else ("worker_vision", base64.b64decode(encoded_png))
with (
    patch.object(httpx, "HTTPTransport", mock_transport),
    patch.object(httpx._client, "HTTPTransport", mock_transport),
    patch.object(httpx._client, "AsyncHTTPTransport", mock_async_transport),
    patch.object(httpx.AsyncClient, "post", exercise_refusals),
    patch.object(chat_vision, "_vl_url_for_role", production_service),
    patch.object(document_client, "get_document_client", production_service),
):
    try:
        isolated.run_isolated_chat(role, url, 18600, 10, output, fence, result, witness, image=image)
    except ValueError:
        assert mode not in {"text", "image"}
        assert not fence.denied
    else:
        assert mode in {"text", "image"}
(output / "test-result.json").write_text(json.dumps(result))
"""
    orchestrator = isolated.planner.ORCHESTRATOR
    completed = subprocess.run(
        [str(orchestrator / ".venv/bin/python"), "-I", "-B", "-c", fixture,
         str(SOURCE), str(tmp_path), str(orchestrator), mode, base64.b64encode(PNG).decode("ascii")],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    request = json.loads((tmp_path / "request.json").read_bytes())
    response = json.loads((tmp_path / "response.body").read_bytes())
    observed = json.loads((tmp_path / "test-result.json").read_bytes())
    role = "frontdoor" if mode == "text" else "worker_vision"
    assert request["server_urls"] == {role: URL}
    if mode != "text":
        assert base64.b64decode(request["image_base64"]) == PNG
    if mode not in {"text", "image"}:
        assert any(not row["allowed"] and row["method"] == "POST" for row in observed["outbound"])
        assert not any(row.get("status_code") == 200 and row["method"] == "POST" for row in observed["outbound"])
        upstream = tmp_path / "upstream-request.json"
        if mode == "foreign-vision":
            assert not upstream.exists()
            assert any(row["url"] == "http://127.0.0.1:8086/v1/chat/completions" and not row["allowed"]
                       for row in observed["outbound"])
        else:
            with pytest.raises(ValueError):
                isolated.verify_outbound_image(upstream.read_bytes(), hashlib.sha256(PNG).hexdigest())
        return
    assert response["routed_to"] == role and response["answer"] == ("ok" if mode == "text" else "red square")
    assert observed["server_urls_source"] == "request"
    assert any(row["status_code"] == 200 and row["method"] == "POST" for row in observed["outbound"])
    if mode == "image":
        raw = (tmp_path / "upstream-request.json").read_bytes()
        proof = isolated.verify_outbound_image(raw, hashlib.sha256(PNG).hexdigest())
        call = next(row for row in observed["outbound"] if row["method"] == "POST")
        assert all(call[key] == value for key, value in proof.items())
    for index, row in enumerate(observed["outbound"], 1):
        events = [event for event, request_id in observed["witness_events"] if request_id == index]
        assert events == (["connect", "dispatch", "sent", "headers"]
                          if row["method"] == "POST" else ["connect", "dispatch"])
