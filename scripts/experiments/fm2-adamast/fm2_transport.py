"""Loopback-only OpenAI SDK options and a byte-exact HTTP journal for FM-2."""

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, value):
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, sort_keys=True)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)


def local_client_options(base_url, timeout):
    url = urlsplit(base_url)
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port
            or url.username or url.password or url.path != "/v1"
            or url.query or url.fragment):
        raise ValueError("FM-2 requires an explicit loopback /v1 endpoint")
    directory = Path(os.environ["ADAMAST_CAPTURE_DIR"])
    request_log = directory / "request.json"
    response_log = directory / "response.json"

    def request_hook(request):
        if request_log.exists():
            raise RuntimeError("FM-2 allows a single request per trace")
        dump(request_log, {
            "sent_at": now(), "method": request.method, "url": str(request.url),
            "body_b64": base64.b64encode(request.read()).decode(),
        })

    def response_hook(response):
        dump(response_log, {
            "received_at": now(), "status": response.status_code,
            "body_b64": base64.b64encode(response.read()).decode(),
        })

    return {
        "base_url": base_url, "max_retries": 0,
        "http_client": httpx.Client(
            trust_env=False, follow_redirects=False, timeout=timeout,
            event_hooks={"request": [request_hook], "response": [response_hook]},
        ),
    }
