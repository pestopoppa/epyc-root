"""Accept a fresh scoped publisher smoke with the sealed original CLI output."""
import base64
import hashlib
import json
import os
from pathlib import Path


def ready():
    path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
    started = int(os.environ["FILLER_SMOKE_T0"])
    result = json.loads(path.read_bytes())
    seal = Path(result["native_path"])
    root = Path(__file__).resolve().parent / "out/smoke"
    if not seal.is_relative_to(root) or not seal.is_file() or seal.is_symlink():
        return False
    data = seal.read_bytes()
    envelope = json.loads(data)
    record = envelope["payload"]
    body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    linkage, cli = record["records"]
    output = base64.b64decode(cli["raw_output_b64"], validate=True)
    return (record["mode"] == result["mode"] == "publisher-smoke"
            and record["status"] == result["status"] == "COMPLETE"
            and result["measurement"] is False and record["started_at"] >= started
            and result["native_sha256"] == hashlib.sha256(data).hexdigest()
            and envelope["sha256"] == hashlib.sha256(body).hexdigest()
            and [linkage["name"], cli["name"]] == ["verify-ggml-linkage", "cli-model-selection-eof"]
            and linkage["rc"] == 0 and cli["rc"] == 1 and cli["process"]["runtime_maps"]
            and linkage["cleanup"] is True and cli["cleanup"] is True
            and b"Select model by number" in output
            and ["GET", "/v1/models"] in record["mock"]["requests"]
            and all(method == "GET" for method, _ in record["mock"]["requests"])
            and record["mock"]["cleanup"] is True and record["unstarted"] == [])


if __name__ == "__main__":
    try:
        raise SystemExit(0 if ready() else 1)
    except (KeyError, OSError, TypeError, ValueError):
        raise SystemExit(1)
