"""Unit tests for src.api.rate_limit."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest

from src.api.rate_limit import RateLimitMiddleware, _is_loopback_peer


class TestRateLimitMiddlewareConfig:
    """Validate cleanup-related tunables are wired correctly."""

    def test_cleanup_threshold_uses_constructor_overrides(self) -> None:
        middleware = RateLimitMiddleware(
            app=Mock(),
            cleanup_interval_seconds=1.25,
            stale_bucket_ttl_seconds=2.5,
        )
        assert middleware._cleanup_interval == 1.25
        assert middleware._stale_bucket_ttl_seconds == 2.5

    def test_cleanup_prunes_stale_buckets_using_ttl(self) -> None:
        middleware = RateLimitMiddleware(
            app=Mock(),
            cleanup_interval_seconds=0.0,
            stale_bucket_ttl_seconds=0.0,
        )
        bucket = middleware._buckets["127.0.0.1"]
        bucket.last_refill = time.monotonic() - 10.0

        middleware._maybe_cleanup()

        assert "127.0.0.1" not in middleware._buckets


class TestLoopbackPeerDetection:
    """`_is_loopback_peer` decides whether to bypass the limiter."""

    @pytest.mark.parametrize(
        "host,expected",
        [
            ("127.0.0.1", True),
            ("127.5.5.5", True),
            ("::1", True),
            ("10.0.0.1", False),
            ("192.168.1.1", False),
            ("8.8.8.8", False),
            ("", False),
        ],
    )
    def test_loopback_classification(self, host: str, expected: bool) -> None:
        scope = {"client": (host, 12345)} if host else {"client": ("", 0)}
        assert _is_loopback_peer(scope) is expected

    def test_missing_client_is_not_loopback(self) -> None:
        assert _is_loopback_peer({}) is False
        assert _is_loopback_peer({"client": None}) is False

    def test_xforwarded_for_does_not_grant_bypass(self) -> None:
        """Spoofing X-Forwarded-For: 127.0.0.1 from a remote peer must NOT bypass."""
        scope = {
            "client": ("8.8.8.8", 54321),
            "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        }
        assert _is_loopback_peer(scope) is False


class TestLoopbackBypassInMiddleware:
    """End-to-end: loopback peers skip the limiter; remote peers don't."""

    @staticmethod
    def _make_scope(client_ip: str, path: str = "/dashboard/api/version") -> dict:
        return {
            "type": "http",
            "path": path,
            "headers": [],
            "client": (client_ip, 12345),
        }

    def test_loopback_peer_never_429s_even_after_burst(self) -> None:
        app = AsyncMock(return_value=None)
        mw = RateLimitMiddleware(app=app, rpm=1, burst=1, trust_proxy=False)
        scope = self._make_scope("127.0.0.1")
        receive, send = AsyncMock(), AsyncMock()

        async def _hammer() -> None:
            for _ in range(50):
                await mw(scope, receive, send)

        asyncio.run(_hammer())
        assert app.await_count == 50
        # No 429 ever sent — middleware called send only via the inner app
        # (which is mocked and sends nothing).
        send.assert_not_called()

    def test_remote_peer_still_rate_limited(self) -> None:
        app = AsyncMock(return_value=None)
        mw = RateLimitMiddleware(app=app, rpm=1, burst=1, trust_proxy=False)
        scope = self._make_scope("8.8.8.8")
        receive, send = AsyncMock(), AsyncMock()

        async def _hammer() -> None:
            for _ in range(10):
                await mw(scope, receive, send)

        asyncio.run(_hammer())
        # First 2 (capacity = rpm + burst = 2) reach the app; rest are 429'd.
        assert app.await_count == 2
        # Each 429 sends two messages (start + body) -> 8 remaining × 2 = 16.
        assert send.await_count == 16

    def test_xforwarded_for_127_from_remote_peer_does_not_bypass(self) -> None:
        """Defense-in-depth: header spoof can't grant bypass."""
        app = AsyncMock(return_value=None)
        mw = RateLimitMiddleware(app=app, rpm=1, burst=1, trust_proxy=True)
        scope = {
            "type": "http",
            "path": "/dashboard/api/version",
            "headers": [(b"x-forwarded-for", b"127.0.0.1")],
            "client": ("8.8.8.8", 12345),
        }
        receive, send = AsyncMock(), AsyncMock()

        async def _hammer() -> None:
            for _ in range(10):
                await mw(scope, receive, send)

        asyncio.run(_hammer())
        # Bypass denied -> remote peer still gets rate-limited after capacity.
        assert app.await_count == 2
