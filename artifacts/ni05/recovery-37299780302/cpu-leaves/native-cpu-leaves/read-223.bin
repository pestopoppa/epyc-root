"""Tests for the dashboard-scoped CORS middleware (RTG-47 Phase 1a).

Covers `src/api/dashboard_cors.py`:
    * preflight is answered directly (204) for hub origins on dashboard paths
    * allowed origin is echoed on GET/POST responses, including SSE (header must
      land on http.response.start, without buffering the stream)
    * every non-hub origin, absent origin, and non-dashboard path is passed
      through with no response mutation at all
    * Access-Control-Allow-Credentials is never emitted

The middleware is exercised directly over a recording ASGI app (fast, and lets us
assert the app is *not* invoked for a preflight); a final class asserts the wiring
into `create_app()` — registered, and outermost.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dashboard_cors import DashboardCORSMiddleware

HUB_ORIGIN = "http://epyc-hub.example:8100"
HUB_ORIGIN_HTTPS = "https://epyc-hub.example:8100"
HUB_ORIGIN_LOCALHOST = "http://localhost:8100"

DASHBOARD_API_PATH = "/dashboard/api/snapshot"
DASHBOARD_SSE_PATH = "/dashboard/events/stream"

CORS_HEADER = "access-control-allow-origin"
CREDENTIALS_HEADER = "access-control-allow-credentials"


class RecordingApp:
    """Minimal ASGI app recording the requests it received.

    `/dashboard/events/*` is answered as a multi-chunk SSE stream so the tests can
    prove the CORS headers arrive on `http.response.start` without the body being
    buffered.
    """

    def __init__(self, extra_headers: list[tuple[bytes, bytes]] | None = None):
        self.calls: list[tuple[str, str]] = []
        self._extra_headers = extra_headers or []

    async def __call__(self, scope, receive, send) -> None:
        self.calls.append((scope.get("method", ""), scope.get("path", "")))

        if scope.get("path", "").startswith("/dashboard/events/"):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/event-stream"), *self._extra_headers],
                }
            )
            for i in range(3):
                await send(
                    {
                        "type": "http.response.body",
                        "body": f"data: {i}\n\n".encode(),
                        "more_body": i < 2,
                    }
                )
            return

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json"), *self._extra_headers],
            }
        )
        await send({"type": "http.response.body", "body": b'{"ok":true}'})


def _client(app: RecordingApp) -> AsyncClient:
    """AsyncClient talking to `app` through the middleware under test."""
    wrapped = DashboardCORSMiddleware(app)
    return AsyncClient(transport=ASGITransport(app=wrapped), base_url="http://orchestrator.test")


class TestPreflight:
    """OPTIONS preflight from the hub is answered by the middleware itself."""

    @pytest.mark.asyncio
    async def test_preflight_returns_204_with_cors_headers(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.options(
                "/dashboard/api/autopilot_control",
                headers={
                    "Origin": HUB_ORIGIN,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

        assert resp.status_code == 204
        assert resp.headers[CORS_HEADER] == HUB_ORIGIN
        assert resp.headers["access-control-allow-methods"] == "GET, POST, OPTIONS"
        assert resp.headers["access-control-allow-headers"] == "content-type"
        assert resp.headers["access-control-max-age"] == "3600"
        assert resp.headers["vary"] == "Origin"
        assert CREDENTIALS_HEADER not in resp.headers
        # The app must never see the preflight.
        assert app.calls == []

    @pytest.mark.asyncio
    async def test_preflight_allows_https_hub_origin(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.options(
                DASHBOARD_SSE_PATH,
                headers={"Origin": HUB_ORIGIN_HTTPS, "Access-Control-Request-Method": "GET"},
            )

        assert resp.status_code == 204
        assert resp.headers[CORS_HEADER] == HUB_ORIGIN_HTTPS
        assert app.calls == []

    @pytest.mark.asyncio
    async def test_preflight_from_other_origin_is_forwarded_untouched(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.options(
                DASHBOARD_API_PATH,
                headers={
                    "Origin": "http://localhost:8200",
                    "Access-Control-Request-Method": "GET",
                },
            )

        assert CORS_HEADER not in resp.headers
        assert app.calls == [("OPTIONS", DASHBOARD_API_PATH)]


class TestAllowedOriginEcho:
    """Simple (non-preflight) requests from the hub get the origin echoed back."""

    @pytest.mark.asyncio
    async def test_get_dashboard_api_echoes_origin(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.get(DASHBOARD_API_PATH, headers={"Origin": HUB_ORIGIN})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert resp.headers[CORS_HEADER] == HUB_ORIGIN
        assert "Origin" in resp.headers["vary"]
        assert CREDENTIALS_HEADER not in resp.headers

    @pytest.mark.asyncio
    async def test_post_control_path_echoes_origin(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.post(
                "/dashboard/api/autopilot_control",
                json={"action": "pause"},
                headers={"Origin": HUB_ORIGIN_LOCALHOST},
            )

        assert resp.headers[CORS_HEADER] == HUB_ORIGIN_LOCALHOST
        assert CREDENTIALS_HEADER not in resp.headers
        assert app.calls == [("POST", "/dashboard/api/autopilot_control")]

    @pytest.mark.asyncio
    async def test_sse_headers_land_on_response_start_without_buffering(self):
        app = RecordingApp()
        wrapped = DashboardCORSMiddleware(app)
        async with AsyncClient(
            transport=ASGITransport(app=wrapped), base_url="http://orchestrator.test"
        ) as client:
            async with client.stream(
                "GET", DASHBOARD_SSE_PATH, headers={"Origin": HUB_ORIGIN}
            ) as resp:
                # Headers are available before a single body byte is consumed.
                assert resp.headers[CORS_HEADER] == HUB_ORIGIN
                assert "Origin" in resp.headers["vary"]
                assert resp.headers["content-type"] == "text/event-stream"
                assert CREDENTIALS_HEADER not in resp.headers
                chunks = [chunk async for chunk in resp.aiter_bytes()]

        assert b"".join(chunks) == b"data: 0\n\ndata: 1\n\ndata: 2\n\n"

    @pytest.mark.asyncio
    async def test_parameterised_dashboard_paths_are_covered(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.get("/dashboard/api/task/abc-123", headers={"Origin": HUB_ORIGIN})

        assert resp.headers[CORS_HEADER] == HUB_ORIGIN

    @pytest.mark.asyncio
    async def test_inner_allow_credentials_is_stripped(self):
        """Starlette's global CORSMiddleware stamps allow-credentials on ANY response
        carrying an Origin header, even for origins it disallows. Inert on its own —
        but paired with our Allow-Origin it would turn this into a credentialed grant.
        """
        app = RecordingApp(extra_headers=[(b"access-control-allow-credentials", b"true")])
        async with _client(app) as client:
            resp = await client.get(DASHBOARD_API_PATH, headers={"Origin": HUB_ORIGIN})

        assert resp.headers[CORS_HEADER] == HUB_ORIGIN
        assert CREDENTIALS_HEADER not in resp.headers

    @pytest.mark.asyncio
    async def test_no_duplicate_allow_origin_when_inner_app_already_set_one(self):
        """A second Access-Control-Allow-Origin would make browsers reject the response."""
        app = RecordingApp(extra_headers=[(b"access-control-allow-origin", HUB_ORIGIN.encode())])
        async with _client(app) as client:
            resp = await client.get(DASHBOARD_API_PATH, headers={"Origin": HUB_ORIGIN})

        assert resp.headers.get_list(CORS_HEADER) == [HUB_ORIGIN]


class TestPassthrough:
    """Anything outside the hub-origin × dashboard-path box is untouched."""

    @pytest.mark.asyncio
    async def test_no_origin_header_is_untouched(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.get(DASHBOARD_API_PATH)

        assert resp.status_code == 200
        assert resp.content == b'{"ok":true}'
        assert CORS_HEADER not in resp.headers
        assert "vary" not in resp.headers
        assert CREDENTIALS_HEADER not in resp.headers

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "origin",
        [
            "http://localhost:8200",  # right host, wrong port
            "http://epyc-hub.example",  # hub host, no port
            "https://evil.example",
            "http://evil.example:81000",  # port is a superstring of 8100
            "http://evil.example:8100.attacker.test",
            "null",
        ],
    )
    async def test_non_matching_origins_get_no_cors_headers(self, origin: str):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.get(DASHBOARD_SSE_PATH, headers={"Origin": origin})

        assert CORS_HEADER not in resp.headers
        assert CREDENTIALS_HEADER not in resp.headers
        assert app.calls == [("GET", DASHBOARD_SSE_PATH)]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/v1/chat/completions",
            "/v1/models",
            "/sessions",
            "/dashboard",  # the legacy same-origin HTML page itself
            "/dashboard/api",  # prefix requires the trailing slash
        ],
    )
    async def test_non_dashboard_paths_get_no_cors_headers(self, path: str):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.get(path, headers={"Origin": HUB_ORIGIN})

        assert CORS_HEADER not in resp.headers
        assert CREDENTIALS_HEADER not in resp.headers
        assert "vary" not in resp.headers
        assert app.calls == [("GET", path)]

    @pytest.mark.asyncio
    async def test_preflight_on_non_dashboard_path_is_not_answered_here(self):
        app = RecordingApp()
        async with _client(app) as client:
            resp = await client.options(
                "/v1/chat/completions",
                headers={"Origin": HUB_ORIGIN, "Access-Control-Request-Method": "POST"},
            )

        assert resp.status_code == 200  # forwarded to the app, not answered with 204
        assert CORS_HEADER not in resp.headers
        assert app.calls == [("OPTIONS", "/v1/chat/completions")]

    @pytest.mark.asyncio
    async def test_non_http_scope_is_passed_through(self):
        """Websocket/lifespan scopes must not be inspected for CORS."""
        seen: list[str] = []

        async def app(scope, receive, send):
            seen.append(scope["type"])

        await DashboardCORSMiddleware(app)({"type": "lifespan"}, None, None)
        await DashboardCORSMiddleware(app)(
            {"type": "websocket", "path": DASHBOARD_SSE_PATH}, None, None
        )
        assert seen == ["lifespan", "websocket"]


class TestAppWiring:
    """The middleware is actually installed on the real app, and installed outermost."""

    def test_registered_and_outermost(self):
        from src.api import create_app

        app = create_app()
        classes = [mw.cls for mw in app.user_middleware]
        assert DashboardCORSMiddleware in classes, "DashboardCORSMiddleware is not wired in"
        # add_middleware inserts at index 0, so index 0 == last added == outermost.
        # It must sit outside the global CORSMiddleware, which would otherwise answer
        # the hub's preflight with 400 "Disallowed CORS origin".
        assert classes[0] is DashboardCORSMiddleware

    @pytest.mark.asyncio
    async def test_real_app_answers_hub_preflight(self):
        from src.api import create_app

        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://orchestrator.test") as client:
            resp = await client.options(
                DASHBOARD_API_PATH,
                headers={"Origin": HUB_ORIGIN, "Access-Control-Request-Method": "GET"},
            )

        assert resp.status_code == 204
        assert resp.headers[CORS_HEADER] == HUB_ORIGIN
        assert CREDENTIALS_HEADER not in resp.headers

    @pytest.mark.asyncio
    async def test_real_app_echoes_origin_on_dashboard_api(self):
        from src.api import create_app

        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://orchestrator.test") as client:
            resp = await client.get("/dashboard/api/version", headers={"Origin": HUB_ORIGIN})

        assert resp.headers[CORS_HEADER] == HUB_ORIGIN
        assert "Origin" in resp.headers["vary"]
        assert CREDENTIALS_HEADER not in resp.headers

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/health", "/v1/chat/completions"])
    async def test_real_app_leaves_non_dashboard_paths_uncorsed(self, path: str):
        """The hub origin buys nothing outside the dashboard data plane.

        Note the global CORSMiddleware still stamps a bare allow-credentials on any
        Origin-carrying request (pre-existing Starlette behavior, untouched here). It
        is inert precisely because no Allow-Origin accompanies it — which is what this
        asserts.
        """
        from src.api import create_app

        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://orchestrator.test") as client:
            resp = await client.get(path, headers={"Origin": HUB_ORIGIN})

        assert CORS_HEADER not in resp.headers
