"""Meter the unchanged OpenCode tool wire against one owned inference slot."""
from contextlib import closing, contextmanager
import gzip
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import time


REASONING_MODE = {"preserve_reasoning": True, "preserve_thinking": True}
PATH = "/v1/chat/completions"
MODEL_ID = "q35-a3b"
TITLE_MODEL_ID = "q35-a3b-title"
TITLE_OUTPUT_CAP = 64
TITLE_SAMPLING = {"temperature": 0.0, "top_k": 1, "top_p": 1.0, "min_p": 0.0,
                  "presence_penalty": 0.0, "repeat_penalty": 1.0}
OUT_KEYS = ("n_predict", "max_tokens", "max_completion_tokens", "maxOutputTokens")
SAMPLING_KEYS = {"seed", "temperature", "top_p", "top_k", "min_p", "repeat_penalty", "presence_penalty", "frequency_penalty"}


class Limits:
    """Reserve output bounds across simultaneous primary, side and subagent requests."""
    def __init__(self, *, wall_s, output_cap, cumulative_output):
        if wall_s <= 0 or output_cap <= 0 or cumulative_output < output_cap:
            raise ValueError("invalid approved wall or token bounds")
        self.started = time.monotonic()
        self.deadline = self.started + wall_s
        self.wall_s = wall_s
        self.output_cap = output_cap
        self.ceiling = cumulative_output
        self.charged = self.observed = self.unknown = self.pending = self.seq = 0
        self.lock = threading.Lock()

    def seconds_left(self):
        return max(0, self.deadline - time.monotonic())

    def reserve(self, requested):
        with self.lock:
            remaining = self.ceiling - self.charged - self.pending
            cap = min(requested, self.output_cap, remaining)
            if self.seconds_left() <= 0 or cap < 1:
                raise RuntimeError("approved request wall or cumulative generated-token bound exhausted")
            self.pending += cap
            self.seq += 1
            return self.seq, cap

    def finish(self, cap, generated):
        with self.lock:
            self.pending -= cap
            if generated is None:
                self.unknown += 1
                self.charged += cap
            else:
                self.observed += generated
                self.charged += generated


class EventMeter:
    def __init__(self):
        self.timings = {}
        self.usage = {}
        self.error = None
        self.outcome = None
        self.first_token = self.delivered = None
        self.reasoning_chars = self.tool_calls = 0

    def read(self, value, elapsed):
        if value.get("timings"):
            self.timings = value["timings"]
        if value.get("usage"):
            self.usage = value["usage"]
        if value.get("error"):
            self.error = value["error"]
        for choice in value.get("choices", []):
            delta = choice.get("delta") or choice.get("message") or {}
            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
            self.reasoning_chars += len(reasoning)
            calls = delta.get("tool_calls") or []
            self.tool_calls += sum(bool(c.get("function", {}).get("name")) for c in calls)
            if elapsed is not None and self.first_token is None and (reasoning or delta.get("content") or calls):
                self.first_token = elapsed
            self.outcome = choice.get("finish_reason") or self.outcome


def close_channels(channels):
    for channel in channels:
        try:
            channel.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *_):
        pass

    def send_error(self, code, message=None, explain=None):
        if code in (400, 404, 429):
            limits = self.server.limits
            with limits.lock:
                record = {"task": self.server.task, "label": self.server.label, "backend": self.server.backend,
                          "slot": self.server.slot, "http_status": code, "reason": message, "at": time.time(),
                          "wall_remaining_s": limits.seconds_left(), "generated_ceiling": limits.ceiling,
                          "charged": limits.charged, "reserved": limits.pending}
            with self.server.write_lock:
                with (self.server.output / "adapter-rejections.jsonl").open("a") as saved:
                    saved.write(json.dumps(record) + "\n")
        super().send_error(code, message, explain)

    def prepare(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length < 32 * 1024 * 1024:
            raise ValueError("missing body or body exceeds 32 MiB")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
            raise ValueError("expected a chat-completion request")
        requested_model = payload.get("model")
        if requested_model not in (MODEL_ID, TITLE_MODEL_ID):
            raise ValueError("request used an unconfigured local model")
        is_title = requested_model == TITLE_MODEL_ID
        if is_title and payload.get("tools"):
            raise ValueError("the OpenCode title route cannot carry worker tools")
        requested = [int(payload[field]) for field in OUT_KEYS
                     if payload.get(field) is not None]
        original_max = min(requested) if requested else None
        if any(payload.get(field) not in (None, 1) for field in ("n_cmpl", "n", "n_parallel")):
            raise ValueError("each case request gets one completion in one owned slot")
        # Keep prompts, requested tools, args and stock side-call behavior intact.
        kwargs = dict(payload.get("chat_template_kwargs") or {})
        # Only the explicit stock title model suppresses reasoning.
        thinking = self.server.thinking and not is_title
        kwargs.update(enable_thinking=thinking)
        for key in REASONING_MODE:
            kwargs.pop(key, None)
        if thinking and self.server.preserve_resume:
            kwargs.update(REASONING_MODE)
        payload.update(id_slot=self.server.slot, chat_template_kwargs=kwargs, timings_per_token=True)
        payload.update(self.server.sampling)
        payload["model"] = MODEL_ID
        if is_title:
            payload.update(TITLE_SAMPLING)
        if payload.get("stream"):
            value = dict(payload.get("stream_options") or {})
            value["include_usage"] = True
            payload["stream_options"] = value
        requested = original_max if original_max is not None else self.server.limits.output_cap
        seq, cap = self.server.limits.reserve(min(requested, TITLE_OUTPUT_CAP) if is_title else requested)
        for key in OUT_KEYS:
            payload.pop(key, None)
        for key in ("n_cmpl", "n", "n_parallel"):
            payload.pop(key, None)
        payload["max_completion_tokens"] = cap
        return seq, cap, original_max, payload, requested_model, is_title

    def do_POST(self):
        if self.path != PATH:
            self.send_error(404)
            return
        try:
            seq, cap, original_max, payload, requested_model, is_title = self.prepare()
        except (TypeError, ValueError) as error:
            self.send_error(400, str(error))
            return
        except RuntimeError as error:
            self.send_error(429, str(error))
            return
        started = time.time()
        tzero = time.monotonic()
        meter = EventMeter()
        headers_sent = False
        status = error = first_body = watchdog = channels = None
        body_ref = f"{self.server.label}-{seq:04d}.json.gz"
        body = json.dumps(payload, ensure_ascii=False).encode()
        try:
            with gzip.open(self.server.output / body_ref, "wb") as archive:
                archive.write(body)
            with closing(http.client.HTTPConnection("127.0.0.1", self.server.upstream, timeout=self.server.limits.seconds_left())) as conn:
                conn.connect()
                channels = (conn.sock, self.connection)
                with self.server.connection_lock:
                    self.server.connections.add(channels)
                    if self.server.closed:
                        close_channels(channels)
                watchdog = threading.Timer(self.server.limits.seconds_left(), close_channels, args=(channels,))
                watchdog.daemon = True
                watchdog.start()
                conn.request("POST", PATH, body, {"Content-Type": "application/json"})
                response = conn.getresponse()
                status = response.status
                mime = response.getheader("Content-Type", "application/json")
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.end_headers()
                headers_sent = True
                buffered = b""
                streaming = "text/event-stream" in mime
                while data := response.read1(65536):
                    elapsed = time.monotonic() - tzero
                    if first_body is None:
                        first_body = elapsed
                    buffered += data
                    if streaming:
                        *lines, buffered = buffered.split(b"\n")
                        for line in lines:
                            if line.startswith(b"data: {"):
                                meter.read(json.loads(line[6:]), elapsed)
                    self.wfile.write(data)
                    self.wfile.flush()
                    if meter.first_token is not None and meter.delivered is None:
                        meter.delivered = time.monotonic() - tzero
                if not streaming and buffered:
                    try:
                        meter.read(json.loads(buffered), None)
                    except ValueError:
                        pass
        except (OSError, http.client.HTTPException, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            if not headers_sent:
                try:
                    self.send_error(502, "model transport failed")
                except OSError:
                    pass
        finally:
            if watchdog:
                watchdog.cancel()
            if channels:
                with self.server.connection_lock:
                    self.server.connections.discard(channels)
            if self.server.limits.seconds_left() <= 0 and meter.outcome is None:
                error = error or "approved wall deadline reached"
            timing, usage = meter.timings, meter.usage
            # Native predicted_n includes reasoning where C22 emits no separate count.
            generated = timing.get("predicted_n", usage.get("completion_tokens"))
            if generated is None and status is not None and 400 <= status < 500:
                generated = 0
            completed = error is None and (meter.outcome is not None or usage.get("completion_tokens") is not None
                                           or (status is not None and 400 <= status < 500))
            self.server.limits.finish(cap, generated if completed else None)
            total = lambda value: round(value, 4) if value is not None else None
            template = payload["chat_template_kwargs"]
            digest = {"tools": len(payload.get("tools") or []), "thinking": template["enable_thinking"],
                      "preserve_thinking": template.get("preserve_thinking", False), "cap_agent": cap,
                      "sdk_model": requested_model, "role": "title" if is_title else None,
                      "upstream_requested_cap": original_max}
            row = {"task": self.server.task, "label": self.server.label, "seq": seq,
                   "slot": self.server.slot, "backend": self.server.backend, "t0": started,
                   "wall_s": total(time.monotonic() - tzero), "http_status": status,
                   "first_body_s": total(first_body), "ttft_s": total(meter.first_token),
                   "delivered_ttft_s": total(meter.delivered), "server_error": meter.error,
                   "transport_error": error, "generation_complete": completed, "finish_reason": meter.outcome, "body_ref": body_ref,
                   "usage": usage or None, "prompt_n": timing.get("prompt_n"), "cache_n": timing.get("cache_n"),
                   "prompt_tok_s": timing.get("prompt_per_second"), "prompt_ms": timing.get("prompt_ms"),
                   "predicted_n": generated, "decode_tok_s": timing.get("predicted_per_second"),
                   "predicted_ms": timing.get("predicted_ms"), "draft_n": timing.get("draft_n"),
                   "draft_accepted": timing.get("draft_n_accepted"), "digest": digest,
                   "reasoning_characters": meter.reasoning_chars, "tool_calls": meter.tool_calls}
            with self.server.write_lock:
                self.server.rows.append(row)
                with (self.server.output / "requests.jsonl").open("a") as out:
                    out.write(json.dumps(row) + "\n")


class Proxy(ThreadingHTTPServer):
    daemon_threads = True


@contextmanager
def proxy(upstream, output, *, limits, backend, slot, task, label, thinking, preserve_resume=False, sampling=None):
    if backend == "cpu" and thinking or preserve_resume and not thinking:
        raise ValueError("invalid task mode or resume state")
    if set(sampling or {}) - SAMPLING_KEYS:
        raise ValueError("unsupported sampling keys in approved profile")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with Proxy(("127.0.0.1", 0), Handler) as server:
        server.upstream, server.output, server.limits = upstream, output, limits
        server.backend, server.slot, server.task, server.label = backend, slot, task, label
        server.thinking, server.preserve_resume = thinking, preserve_resume
        server.sampling = dict(sampling or {})
        server.rows, server.write_lock = [], threading.Lock()
        server.connections, server.connection_lock, server.closed = set(), threading.Lock(), False
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield server
        finally:
            with server.connection_lock:
                server.closed = True
                for channels in server.connections:
                    close_channels(channels)
            server.shutdown()
