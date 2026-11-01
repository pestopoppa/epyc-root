"""The retired kernel API is not a dashboard data dependency."""
from __future__ import annotations
from dashboard import kernel_contract as legacy, kernel_identity as identity

from contextlib import contextmanager
import http.client
import json
import threading
import time
from unittest import mock

from dashboard import panels, server


@contextmanager
def _http_server():
    httpd = server.build_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        httpd.server_close()


def _get(port: int, path: str) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        payload = json.loads(response.read())
        return response.status, payload
    finally:
        connection.close()


def test_retired_routes_404_and_loop_routes_still_serve():
    observation = panels.Observation(
        artifact_present=True,
        timestamp=time.time(),
        source="generated_at",
        populated=True,
    )
    with (mock.patch.object(server.loop_status, "snapshot",
                            return_value=({"schema": server.loop_status.STATUS_SCHEMA},
                                          observation)),
          mock.patch.object(server, "_read_operator_gate_bundle",
                            return_value={"freshness": {"state": "relevant"}})):
        with _http_server() as port:
            for path in ("/api/kernel", "/api/kernel/live", "/api/kernel/health"):
                status, payload = _get(port, path)
                assert status == 404
                assert payload["error"] == "not found"
            status, payload = _get(port, "/api/loop")
            assert status == 200
            assert payload["schema"] == server.loop_status.STATUS_SCHEMA
            with mock.patch.dict(server.PANEL_HEALTH_ROUTES, {
                    "/api/loop/health": lambda: (200, {"probe": "loop"})}):
                status, payload = _get(port, "/api/loop/health")
            assert status == 200
            assert payload["probe"] == "loop"


def test_retired_producers_do_not_enter_registry_or_global_health():
    assert "kernel" not in panels.PANELS
    assert "kernel_live" not in panels.PANELS

    with (mock.patch.object(legacy, "_read_kernel_contract",
                            side_effect=AssertionError("retired contract read")) as terminal,
          mock.patch.object(legacy, "_read_kernel_progression",
                            side_effect=AssertionError("retired progression read")) as progression):
        envelopes = server.panel_envelopes()
        assert set(envelopes) == set(panels.PANELS)
        with mock.patch.object(server, "panel_envelopes", return_value=envelopes):
            health = server.health_payload()

    assert not ({"kernel", "kernel_live"} & set(health["panels"]))
    assert "kernel" not in health
    assert all(entry.get("panel") not in {"kernel", "kernel_live"}
               for entry in health["attention"])
    terminal.assert_not_called()
    assert not hasattr(server, "_discovery_live_read")
    assert not hasattr(server, "legacy_discovery_live_data")
    progression.assert_not_called()


def test_loop_health_remains_a_distinct_registered_probe():
    source = panels.source("autokernel_loop")
    assert server.API_ROUTES["/api/loop"] is server.loop_payload
    assert server.PANEL_HEALTH_ROUTES["/api/loop/health"] is server.loop_data_health
    assert source.route == "/api/loop"
    assert source.health_route == "/api/loop/health"
    assert "kernel" not in panels.PANELS
    assert "kernel_live" not in panels.PANELS
