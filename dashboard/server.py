#!/usr/bin/env python3
"""EPYC project dashboard hub — handoff progress board.

A tiny, dependency-free web server (stdlib ``http.server`` only) owned by the
governance repo. It surfaces project-wide progress that is *artifact/file-backed*
(handoffs today; more views later). Anything that needs the orchestrator's live
in-process state or SSE inference taps stays on the orchestrator dashboard
(:8000) — this hub links to it. See ``dashboard/README.md`` for that boundary.

Routes
------
GET /                        the kanban page (static HTML, re-read per request)
GET /health                 ``{"status":"ok"}`` for the stack health probe
GET /api/handoff_board       compact cards for all four columns (live scan, TTL-cached)
GET /api/handoff_detail?id=  full card + scrubbed markdown body (lazy modal load)
GET /api/handoff_timeline    the git-derived timeline artifact (+ freshness)
GET /api/health              board=live + timeline staleness class

Run: ``python3 -m dashboard.server --port 8100``  (or ``python3 dashboard/server.py``)
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Make ``from dashboard import ...`` work whether launched as ``-m dashboard.server``
# (cwd on path) or as a bare script ``python3 dashboard/server.py``.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dashboard import freshness, handoff_parser

# ``resolve()`` follows the /workspace -> /mnt/raid0/llm/epyc-root symlink, so the
# hub always reads its own repo regardless of which path launched it.
REPO = Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO / "handoffs"
TIMELINE_PATH = REPO / "data" / "handoff_timeline.json"
STATIC_HTML = Path(__file__).resolve().parent / "static" / "handoffs.html"

# Timeline freshness thresholds (handoffs move on a human/commit cadence).
_TIMELINE_WARN_S = 6 * 3600
_TIMELINE_STALE_S = 2 * 86400

_BOARD_TTL_S = 30.0
_NO_STORE = {"Cache-Control": "no-store", "Content-Type": "application/json"}

# --------------------------------------------------------------------------- #
# Payload builders (importable / unit-testable independent of the HTTP layer)
# --------------------------------------------------------------------------- #
_board_lock = threading.Lock()
_board_cache: dict | None = None
_board_cache_ts = 0.0


def board_payload(*, force: bool = False) -> dict:
    """Live directory scan of the four state dirs, cached for ``_BOARD_TTL_S``."""
    global _board_cache, _board_cache_ts
    with _board_lock:
        now = time.time()
        if force or _board_cache is None or (now - _board_cache_ts) > _BOARD_TTL_S:
            _board_cache = handoff_parser.build_board(HANDOFF_DIR)
            _board_cache_ts = now
        payload = dict(_board_cache)
    payload["_freshness"] = {"staleness_class": "fresh", "source": "live-scan"}
    return payload


def _validate_id(handoff_id: str) -> Path | None:
    """Resolve a ``state/stem`` id to a file path, or ``None`` if unsafe/missing.

    Guards against path traversal: the resolved path must stay inside
    ``HANDOFF_DIR`` and the leading segment must be a real state directory.
    """
    if (not handoff_id or ".." in handoff_id or handoff_id.startswith("/")
            or "\x00" in handoff_id or any(ord(c) < 32 for c in handoff_id)):
        return None
    parts = handoff_id.split("/")
    if len(parts) != 2 or parts[0] not in handoff_parser.STATES:
        return None
    state, stem = parts
    if not stem or "/" in stem or "\\" in stem:
        return None
    try:
        candidate = (HANDOFF_DIR / state / f"{stem}.md").resolve()
        candidate.relative_to(HANDOFF_DIR.resolve())
    except (ValueError, OSError):
        return None
    return candidate if candidate.is_file() else None


def detail_payload(handoff_id: str) -> tuple[int, dict]:
    """Return ``(http_status, payload)`` for one handoff's detail view."""
    path = _validate_id(handoff_id or "")
    if path is None:
        return 404, {"error": "handoff not found", "id": handoff_id}
    state = handoff_id.split("/")[0]
    card = handoff_parser.parse_file(state, path, detail=True)
    return 200, card


def timeline_payload() -> dict:
    """Read the git-derived timeline artifact, tolerating absence/corruption."""
    fresh = freshness.classify(TIMELINE_PATH, _TIMELINE_WARN_S, _TIMELINE_STALE_S)
    try:
        data = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"series": [], "tasks_weekly": [], "handoffs_weekly": [],
                "generated_at": None, "error": "timeline artifact not generated yet"}
    except (OSError, json.JSONDecodeError) as exc:
        data = {"series": [], "tasks_weekly": [], "handoffs_weekly": [],
                "generated_at": None, "error": f"timeline artifact unreadable: {exc}"}
    if not isinstance(data, dict):  # valid JSON but not an object (hand-edited/clobbered)
        data = {"series": [], "tasks_weekly": [], "handoffs_weekly": [],
                "generated_at": None, "error": "timeline artifact malformed (not an object)"}
    data["_freshness"] = fresh
    return data


def health_payload() -> dict:
    """Fold the board (live) + timeline (artifact) into one status line."""
    tl = freshness.classify(TIMELINE_PATH, _TIMELINE_WARN_S, _TIMELINE_STALE_S)
    # ``missing`` is not degraded (fresh checkout / first run); ``stale`` is.
    degraded = tl["staleness_class"] == "stale"
    return {
        "status": "degraded" if degraded else "ok",
        "board": {"staleness_class": "fresh", "source": "live-scan"},
        "timeline": tl,
        "now": time.time(),
    }


# --------------------------------------------------------------------------- #
# HTTP layer
# --------------------------------------------------------------------------- #
class _Handler(BaseHTTPRequestHandler):
    server_version = "EPYCHandoffHub/1.0"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for key, value in _NO_STORE.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_html(self) -> None:
        try:
            body = STATIC_HTML.read_bytes()
            status = 200
        except OSError:
            body = b"<h1>handoff dashboard</h1><p>static page missing</p>"
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        try:
            if route == "/":
                self._send_html()
            elif route == "/health":
                self._send_json({"status": "ok"})
            elif route == "/api/handoff_board":
                self._send_json(board_payload())
            elif route == "/api/handoff_detail":
                qs = parse_qs(parsed.query)
                handoff_id = (qs.get("id") or [""])[0]
                status, payload = detail_payload(handoff_id)
                self._send_json(payload, status=status)
            elif route == "/api/handoff_timeline":
                self._send_json(timeline_payload())
            elif route == "/api/health":
                self._send_json(health_payload())
            else:
                self._send_json({"error": "not found", "path": route}, status=404)
        except BrokenPipeError:
            pass  # client hung up mid-response; nothing to do
        except Exception as exc:  # never let one bad request kill the thread
            try:
                self._send_json({"error": "internal", "detail": str(exc)}, status=500)
            except OSError:
                pass

    do_HEAD = do_GET  # allow HEAD probes to reuse the same dispatch

    def log_message(self, fmt: str, *args) -> None:  # quieter default logging
        return


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def main() -> None:
    ap = argparse.ArgumentParser(description="EPYC handoff dashboard hub")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8100)
    args = ap.parse_args()
    httpd = build_server(args.host, args.port)
    print(f"[handoff-hub] serving http://{args.host}:{args.port}/  (repo: {REPO})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
