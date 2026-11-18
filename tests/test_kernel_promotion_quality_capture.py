"""Socket-free controls for quality capture, native comparison and request custody."""

import base64
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
from threading import Event
from types import SimpleNamespace

import pytest

from test_kernel_promotion_quality_parity import source


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/benchmark"))
import kernel_promotion_quality_capture as live


def state():
    return {"cleanup_proved": True, "signal": None, "runtime": None}


@pytest.fixture
def attempt(source, tmp_path):
    rows = deepcopy(source["items"])
    raw = {item["id"]: item.pop("production") for item in rows}
    for item in rows:
        item["request_sha256"] = raw[item["id"]]["request_sha256"]
        if item["shape"] == "worker-vision-hip-mmproj":
            item["request_body"]["messages"][0]["content"] = [
                {"type": "text", "text": item["request_body"]["messages"][0]["content"]},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,UE5H"}},
            ]
            pin = live.parity._json_hash(item["request_body"])
            item["request_sha256"] = raw[item["id"]]["request_sha256"] = pin
    shapes = live.parity._shapes(source["shapes"])
    items = live.request_manifest(rows, shapes)
    config = {
        "capture_source": source["capture_source"],
        "shapes": source["shapes"],
        "mappings": {shape: {"canonical_port": 8070, "numa_instance": 0, "role": "fixture",
                             "path": row["endpoint"]} for shape, row in shapes.items()},
        "arms": {name: {"runtime": source["runtime"]} for name in live.ARM_NAMES},
    }
    return config, shapes, items, raw, tmp_path


def replace_response(capture, change):
    decoded = json.loads(base64.b64decode(capture["response_b64"]))
    change(decoded)
    encoded = json.dumps(decoded).encode()
    capture.update(response_b64=base64.b64encode(encoded).decode(), response_sha256=live.sha(encoded))


@pytest.mark.parametrize(("failure", "reason", "sealed"), [
    ("semantic", "semantic validation", True),
    ("tokens", "lacks exposed token IDs", True),
    ("cleanup", "cleanup must be proved", False),
])
def test_production_refusals_prevent_dispatch(attempt, monkeypatch, failure, reason, sealed):
    config, shapes, items, raw, output = attempt
    capture = raw["frontdoor-cpu-moe-mtp-0"]
    if failure == "semantic":
        replace_response(capture, lambda reply: reply.update(content="bad"))
    if failure == "tokens":
        replace_response(capture, lambda reply: reply.pop("tokens"))
    called = []

    def capture_arm(arm, prepared, config, shapes, items, output, run_state):
        called.append(arm)
        if failure == "cleanup":
            run_state["cleanup_proved"] = False
        return raw

    monkeypatch.setattr(live, "capture_arm", capture_arm)
    result = live.execute(config, "a" * 64, dict.fromkeys(live.ARM_NAMES), shapes, items, output, state())
    assert called == ["production"]
    assert result["status"] == "incomplete"
    assert reason in result["failure"]
    assert not result["candidate_arm_started"]
    assert not (output / "production-pack.sha256").exists()
    assert (output / "COMPLETE").exists() is sealed


@pytest.mark.parametrize(("omit_token_ids", "expected"), [(False, "pass"), (True, "incomplete")])
def test_candidate_uses_already_published_pack_and_existing_comparator(attempt, monkeypatch, omit_token_ids, expected):
    config, shapes, items, raw, output = attempt
    called = []

    def capture_arm(arm, *_):
        called.append(arm)
        if arm == "production":
            assert not (output / "production-pack.sha256").exists()
            return raw
        bank_pin = (output / "production-pack.sha256").read_text().strip()
        assert live.planner.digest(output / "production-pack.json") == bank_pin
        assert (output / "request-manifest.json").is_file()
        candidate = deepcopy(raw)
        for item in candidate.values():
            if "server_instance" in item:
                item["server_instance"] = "candidate:234:567"
        if omit_token_ids:
            replace_response(candidate["frontdoor-cpu-moe-mtp-0"], lambda reply: reply.pop("tokens"))
        return candidate

    monkeypatch.setattr(live, "capture_arm", capture_arm)
    result = live.execute(config, "a" * 64, dict.fromkeys(live.ARM_NAMES), shapes, items, output, state())
    assert called == list(live.ARM_NAMES)
    assert result["status"] == expected
    assert not result["quality_transfer_authorized"] and not result["promotion_authorized"]
    comparison = json.loads((output / "comparison.json").read_bytes())
    assert comparison["report"]["status"] == expected
    assert comparison["report"]["production_runtime"] == config["arms"]["production"]["runtime"]
    manifest = json.loads((output / "MANIFEST.json").read_bytes())
    assert manifest["files"]["comparison.json"] == result["comparison_sha256"]
    assert (output / "COMPLETE").read_text().strip() == live.planner.digest(output / "MANIFEST.json")


def test_manifest_refuses_mutated_and_external_media_requests(attempt):
    _, shapes, items, _, _ = attempt
    item = items["worker-vision-hip-mmproj-0"]
    item["request_body"]["messages"][0]["content"][1]["image_url"]["url"] = "https://example.org/photo.png"
    with pytest.raises(ValueError, match="changed request pin"):
        live.request_manifest(list(items.values()), shapes)
    item["request_sha256"] = live.parity._json_hash(item["request_body"])
    with pytest.raises(ValueError, match="must be embedded"):
        live.request_manifest(list(items.values()), shapes)


def test_dflash_capture_records_observed_echo_and_owned_instance(attempt):
    _, shapes, items, raw, _ = attempt
    item_id = "dspark-dflash-0-6"
    shape = shapes["dspark-dflash"]
    server = SimpleNamespace(port=19520, pid=123, birth=456, endpoint={"argv": ["llama-server", "-np", "1"]})
    decoded = base64.b64decode(raw[item_id]["response_b64"])
    capture = live.capture_record(items[item_id], shape, server, decoded, "row", "production")
    assert capture["effective_n_max"] == 6
    assert capture["parallel_slots"] == 1
    assert capture["server_instance"] == "row:production:19520:123:456"

    replace_response(raw[item_id], lambda reply: reply["generation_settings"].update({"speculative.n_max": 2}))
    with pytest.raises(ValueError, match="does not echo"):
        live.capture_record(items[item_id], shape, server, base64.b64decode(raw[item_id]["response_b64"]),
                            "row", "production")


@pytest.mark.parametrize("headers_first", [False, True])
def test_capture_requires_complete_in_window_sample_and_retains_http_bytes(attempt, headers_first):
    _, _, items, _, output = attempt
    item = items["frontdoor-cpu-moe-mtp-0"]
    sample = Event()
    server = SimpleNamespace(endpoint={"endpoint": "http://127.0.0.1:19520"})
    raw = b'{ "content": "original" }\n'

    class FakeRuntime:
        request_timeout = 10
        timeout = staticmethod(lambda seconds: seconds)
        check = staticmethod(lambda: None)
        verify_identity = staticmethod(lambda _: None)

        def sample(self, target):
            assert target is server
            sample.set()
            return {"threads": {"42": {"cpus": [1], "numa_policy": "bind:0"}},
                    "backend": {"kfd_client": False}}

        def request_http(self, target, method, path, body, timeout, sent, headers, **kwargs):
            assert (target, method, path) == (server, "POST", "/completion")
            assert live.sha(body) == item["request_sha256"]
            assert timeout == 10 and kwargs["wait_for_generation"]
            # Make the scan deterministic without sleeps or a real socket.
            if headers_first:
                headers()
                sent()
            else:
                sent()
                assert sample.wait(2)
                while not scan_published.is_set():
                    # The clock wrapper sets this event on the sample end.
                    if scan_published.wait(2):
                        break
                    raise TimeoutError("sample did not finish")
                headers()
            return 200, raw

    scan_published = Event()
    clock = live.time.monotonic

    def scan_clock():
        stamp = clock()
        if sample.is_set():
            scan_published.set()
        return stamp

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(live, "time", SimpleNamespace(monotonic=scan_clock))
        if headers_first:
            with pytest.raises(ValueError, match="no complete affinity"):
                live.capture_request(FakeRuntime(), server, "/completion", item, output / "item")
        else:
            assert live.capture_request(FakeRuntime(), server, "/completion", item, output / "item") == raw
    assert (output / "item" / "response.raw.json").read_bytes() == raw
    http = json.loads((output / "item" / "http.json").read_bytes())
    assert http["response_sha256"] == live.sha(raw)
    witnesses = json.loads((output / "item" / "during-request.json").read_bytes())
    assert len(witnesses["samples"]) == (0 if headers_first else 1)


@pytest.mark.parametrize(("wait_for_generation", "cancel"), [(False, False), (True, False), (True, True)])
def test_request_http_generation_opt_in_preserves_default_and_closes_connection(
        monkeypatch, wait_for_generation, cancel):
    class FakeSocket:
        def __init__(self, timeout):
            self.timeout = timeout
            self.cancelled = False

        def settimeout(self, timeout):
            self.timeout = timeout

        def shutdown(self, direction):
            assert direction == socket.SHUT_RDWR
            self.cancelled = True

    class Response:
        status = 200
        length = 0

        def isclosed(self):
            return False

        def read1(self, _count):
            return b""

        def close(self):
            pass

    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("127.0.0.1", 19520, 5)
            self.sock = FakeSocket(timeout)
            self.closed = False
            connections.append(self)

        def connect(self):
            pass

        def request(self, *_args, **_kwargs):
            assert self.sock.timeout == 5

        def getresponse(self):
            assert (self.sock.timeout > 5) is wait_for_generation
            if self.sock.cancelled:
                raise ConnectionResetError("cancelled")
            return Response()

        def close(self):
            self.closed = True

    connections = []
    monkeypatch.setattr(live.runner.http.client, "HTTPConnection", Connection)
    runtime = SimpleNamespace(verify_identity=lambda _: None)
    socket_hook = (lambda sock: sock.shutdown(socket.SHUT_RDWR)) if cancel else None
    kwargs = {"wait_for_generation": wait_for_generation, "connected_socket": socket_hook}
    if cancel:
        with pytest.raises(ConnectionResetError, match="cancelled"):
            live.runner.Runtime.request_http(runtime, SimpleNamespace(port=19520), "POST", "/completion", b"{}", 20, **kwargs)
    else:
        assert live.runner.Runtime.request_http(
            runtime, SimpleNamespace(port=19520), "POST", "/completion", b"{}", 20, **kwargs
        ) == (200, b"")
    assert connections[0].closed
