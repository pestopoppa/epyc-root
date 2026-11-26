"""Access OpenCode's stock API on the current case's loopback only."""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8103"
AUTH = base64.b64encode((os.environ["OPENCODE_SERVER_USERNAME"] + ":" + os.environ["OPENCODE_SERVER_PASSWORD"]).encode())


def query(path, method="GET", body=None):
    request = urllib.request.Request(BASE + path, data=body, method=method,
        headers={"Content-Type": "application/json", "Authorization": "Basic " + AUTH.decode()})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        body = error.read(16384).decode("utf-8", "replace")
        print(json.dumps({"status": error.code, "method": method, "path": path, "body": body}), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    path, method = sys.argv[1:3]
    if method == "POLL":
        value = {"data": {
            "forms": query("/api/form?location%5Bdirectory%5D=%2Fcase")["data"],
            "active": query("/api/session/active")["data"],
        }}
    else:
        body = sys.argv[3].encode() if len(sys.argv) == 4 else None
        value = query(path, method, body)
    if value is not None:
        print(json.dumps(value))
