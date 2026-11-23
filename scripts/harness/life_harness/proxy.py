"""Loopback proxies for the hardwired Life-Harness model endpoints (LH4a).

Two listeners, one class:

* improver: the shipped proposer call goes to ``MR_HOST + /protocol/openai/v1/chat/completions``
  with ``"model": "deepseek-v4-flash"``. This proxy accepts ``/protocol/openai/v1/*`` and forwards
  to a local llama-server ``<upstream>/v1/*``, rewriting ``model`` to the served alias. The
  response is passed through UNCHANGED (usage is never fabricated); conformance problems
  (no ``tool_calls`` when tools were requested, non-integer usage) are logged, not hidden.
* solver: the frozen manifest hardwires ``http://127.0.0.1:8400/v1/chat/completions`` with model
  ``qwen3-4b``. This proxy listens there (port is a parameter, 8400 is the frozen value) and
  forwards ``/v1/*`` to the real solver server with the model rewritten.

Every request appends one metadata line to ``log_path`` (no bodies, no secrets). A
``/lh-proxy/health`` route returns this proxy's identity so a launcher can prove it is talking to
its own server and not whatever else holds the port.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

IMPROVER_PREFIX = "/protocol/openai/v1"
SOLVER_PREFIX = "/v1"
HEALTH_PATH = "/lh-proxy/health"
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def check_response(payload: dict[str, Any], *, tools_requested: bool) -> dict[str, Any]:
    """Conformance facts for one improver response (shape only; no model judgement)."""
    usage = payload.get("usage") if isinstance(payload, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    ints = all(type(usage.get(k)) is int and usage.get(k) >= 0 for k in ("prompt_tokens", "completion_tokens"))
    choices = payload.get("choices") if isinstance(payload, dict) else None
    msg = (choices[0].get("message") or {}) if choices else {}
    calls = msg.get("tool_calls") or []
    return {"has_choice": bool(choices), "usage_integer": ints, "tool_calls": len(calls),
            "tool_calls_ok": bool(calls) if tools_requested else True,
            "finish_reason": (choices[0].get("finish_reason") if choices else None),
            "ok": bool(choices) and ints and (bool(calls) or not tools_requested)}


class LoopbackProxy:
    def __init__(self, *, mode: str, upstream_base: str, model_alias: str, port: int,
                 host: str = "127.0.0.1", log_path: Path | None = None, timeout: float = 3600.0,
                 name: str | None = None):
        if mode not in ("improver", "solver"):
            raise ValueError("mode must be improver or solver")
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("loopback only: refusing to listen on a non-loopback host")
        self.mode, self.model_alias, self.timeout = mode, model_alias, timeout
        self.prefix = IMPROVER_PREFIX if mode == "improver" else SOLVER_PREFIX
        self.upstream_base = upstream_base.rstrip("/")  # e.g. http://127.0.0.1:8080/v1
        self.log_path = Path(log_path) if log_path else None
        self.name = name or f"lh-{mode}-proxy"
        self._log_lock = threading.Lock()
        self.stats = {"requests": 0, "ok": 0, "upstream_errors": 0, "nonconformant": 0}
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == HEALTH_PATH:
                    self._send(200, json.dumps({"proxy": proxy.name, "mode": proxy.mode,
                        "upstream": proxy.upstream_base, "model_alias": proxy.model_alias,
                        "prefix": proxy.prefix, "stats": proxy.stats}).encode())
                elif self.path.startswith(proxy.prefix + "/models"):
                    proxy._forward(self, b"", "GET", self.path[len(proxy.prefix):])
                else:
                    self._send(404, b'{"error":"not found"}')

            def do_POST(self):
                if not self.path.startswith(proxy.prefix + "/"):
                    self._send(404, json.dumps({"error": "path must start with " + proxy.prefix + "/"}).encode())
                    return
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                proxy._forward(self, body, "POST", self.path[len(proxy.prefix):])

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread: threading.Thread | None = None

    # -- request path -------------------------------------------------
    def _log(self, entry: dict[str, Any]) -> None:
        if not self.log_path:
            return
        with self._log_lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")

    def _forward(self, handler: BaseHTTPRequestHandler, body: bytes, method: str, rest: str) -> None:
        started = time.time()
        self.stats["requests"] += 1
        model_in, tools_requested, stream = None, False, False
        if body:
            try:
                payload = json.loads(body)
            except ValueError:
                handler._send(400, b'{"error":"request body is not JSON"}')
                return
            model_in = payload.get("model")
            tools_requested = bool(payload.get("tools"))
            stream = bool(payload.get("stream"))
            payload["model"] = self.model_alias
            body = json.dumps(payload, ensure_ascii=False).encode()
        request = urllib.request.Request(self.upstream_base + rest, data=body or None, method=method,
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"})
        entry = {"t": started, "proxy": self.name, "path": rest, "model_in": model_in,
                 "model_out": self.model_alias, "stream": stream, "tools_requested": tools_requested}
        try:
            with _NO_PROXY.open(request, timeout=self.timeout) as resp:
                code, ctype = resp.status, resp.headers.get("Content-Type", "application/json")
                if stream:
                    handler.send_response(code)
                    handler.send_header("Content-Type", ctype)
                    handler.send_header("Connection", "close")
                    handler.end_headers()
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        handler.wfile.write(chunk)
                        handler.wfile.flush()
                    entry.update(status=code, conformance="not_checked_stream")
                else:
                    data = resp.read()
                    entry["status"] = code
                    if self.mode == "improver" and rest.endswith("/chat/completions"):
                        try:
                            facts = check_response(json.loads(data), tools_requested=tools_requested)
                        except ValueError:
                            facts = {"ok": False, "error": "non-JSON response"}
                        entry["conformance"] = facts
                        if not facts.get("ok"):
                            self.stats["nonconformant"] += 1
                    # Log BEFORE replying so a caller that returns on the reply sees its own line.
                    entry["seconds"] = round(time.time() - started, 3)
                    self._log(entry)
                    entry = None
                    handler._send(code, data, ctype)
            self.stats["ok"] += 1
        except urllib.error.HTTPError as exc:
            data = exc.read()
            entry.update(status=exc.code, upstream_error=True)
            self.stats["upstream_errors"] += 1
            handler._send(exc.code, data, exc.headers.get("Content-Type", "application/json"))
        except Exception as exc:  # connection refused, timeout, broken pipe
            entry.update(status=502, upstream_error=True, error=type(exc).__name__)
            self.stats["upstream_errors"] += 1
            try:
                handler._send(502, json.dumps({"error": "upstream unreachable: " + type(exc).__name__}).encode())
            except OSError:
                pass
        finally:
            if entry is not None:
                entry["seconds"] = round(time.time() - started, 3)
                self._log(entry)

    # -- lifecycle -----------------------------------------------------
    def start(self) -> "LoopbackProxy":
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"
