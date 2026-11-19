"""Native loopback HTTP callback and exclusive durable episode journal.

The row must establish endpoint ownership before constructing this transport.
No server is launched here, and these helpers make no model-quality claim.
"""
import base64
from copy import deepcopy
import http.client
import ipaddress
import json
import math
import os
import socket
import threading
import time
from urllib.parse import urlsplit


class CaptureError(RuntimeError):
    """A lost receipt is a fatal run error, never a model transport failure."""


class DurableJournal:
    """One exclusive JSONL per episode; every receipt reaches fsync before return."""

    def __init__(self, path, envelope):
        if not isinstance(envelope, dict) or not envelope:
            raise ValueError("nonempty prospective custody envelope required")
        self.envelope = deepcopy(envelope)
        self.sequence = 0
        self.file = open(path, "x", encoding="utf-8")
        try:
            self({"event": "episode_start"})
            # Persist the newly created directory entry as well as the file.
            directory = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            self.file.close()
            raise

    def __call__(self, record):
        try:
            line = json.dumps({"sequence": self.sequence, "custody": self.envelope,
                               "record": record}, allow_nan=False, separators=(",", ":"))
            self.file.write(line + "\n")
            self.file.flush()
            os.fsync(self.file.fileno())
        except OSError as error:
            raise CaptureError("durable episode capture failed") from error
        self.sequence += 1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.file.close()


class NativeCompletion:
    """Unmodified JSON replies, bounded bytes and absolute HTTP wall deadline.

    Only a literal loopback address is accepted; no proxies, DNS or redirects.
    A watchdog shuts down only this request's captured socket, including during
    response headers or a trickling body. Native bytes are journaled before JSON
    parsing, including partial bytes on failure. Calls are sequential.
    """

    def __init__(self, base_url, capture, *, max_bytes=8 * 1024 * 1024):
        url = urlsplit(base_url)
        try:
            loopback = ipaddress.ip_address(url.hostname).is_loopback
            port = url.port
        except (ValueError, TypeError):
            raise ValueError("literal loopback HTTP endpoint required") from None
        if (url.scheme != "http" or not loopback or url.username is not None
                or url.password is not None or url.query or url.fragment
                or url.path.rstrip("/") != "/v1" or port is None):
            raise ValueError("explicit loopback http://address:port/v1 required")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("positive response byte bound required")
        self.host, self.port = url.hostname, port
        self.capture, self.max_bytes = capture, max_bytes

    def __call__(self, request, timeout_s):
        if (isinstance(timeout_s, bool) or not isinstance(timeout_s, (float, int))
                or not math.isfinite(timeout_s) or timeout_s <= 0):
            raise ValueError("finite positive HTTP deadline required")
        deadline = time.monotonic() + timeout_s
        payload = json.dumps(request, allow_nan=False).encode("utf-8")
        connection = http.client.HTTPConnection(self.host, self.port, timeout=timeout_s)
        expired = threading.Event()
        timer = None
        body = bytearray()
        receipt = {"event": "native_http", "status": None, "complete": False}
        try:
            connection.connect()
            owned_socket = connection.sock

            def abort():
                expired.set()
                try:
                    owned_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("HTTP deadline")
            timer = threading.Timer(remaining, abort)
            timer.daemon = True
            timer.start()
            connection.request("POST", "/v1/chat/completions", payload,
                               {"Content-Type": "application/json", "Accept": "application/json"})
            response = connection.getresponse()
            receipt["status"] = response.status
            receipt["headers"] = response.getheaders()
            while True:
                chunk = response.read1(min(65536, self.max_bytes + 1 - len(body)))
                body.extend(chunk)
                if expired.is_set() or time.monotonic() >= deadline:
                    raise TimeoutError("HTTP deadline")
                if not chunk:
                    break
                if len(body) > self.max_bytes:
                    raise OSError("native response exceeds byte bound")
            # read1 can return EOF without detecting a truncated Content-Length.
            if response.length not in (None, 0):
                raise OSError("truncated native response")
            receipt["complete"] = True
            if response.status != 200:
                raise OSError(f"native HTTP status {response.status}")
        except (OSError, http.client.HTTPException) as error:
            receipt["error"] = {"type": type(error).__name__, "message": str(error)}
            if expired.is_set():
                raise TimeoutError("HTTP deadline") from error
            raise OSError(str(error)) from error
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            connection.close()
            receipt["body_base64"] = base64.b64encode(body).decode("ascii")
            try:
                self.capture(receipt)
            except OSError as error:
                raise CaptureError("native HTTP receipt lost") from error
        try:
            return json.loads(body)
        except (ValueError, UnicodeError) as error:
            raise OSError("invalid native JSON; bytes retained") from error
