"""Extend MM-5 with request-level environment control and a bounded robustness probe."""
import base64
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

ENV_NAME = "ORCHESTRATOR_VL_MAX_PIXELS"
PATCH_SIZE = 28
CHILD_TIMEOUT_S = 8


def check_environment(lane):
    """Observe the actual request bytes with the constructor keyword omitted."""
    from PIL import Image

    sys.path.insert(0, str(lane))
    from src.backends import serving_calls
    from src.vision.analyzers.vl_describe import VLDescribeAnalyzer

    source_size = (896, 896)
    with TemporaryDirectory(prefix="mm5-env-") as scratch:
        path = Path(scratch) / "env-fixture.png"
        with Image.new("RGB", source_size, color=(71, 133, 211)) as image:
            image.save(path)
        for configured, expected in ((None, source_size), (PATCH_SIZE ** 2, (PATCH_SIZE, PATCH_SIZE))):
            label = f"{ENV_NAME}={'unset' if configured is None else configured}"
            response = BytesIO(b'{"choices":[{"message":{"content":"fixture description"}}]}')
            response.status = 200
            with patch.dict(os.environ):
                os.environ.pop(ENV_NAME, None)
                if configured is not None:
                    os.environ[ENV_NAME] = str(configured)
                analyzer = VLDescribeAnalyzer(backend="server")
                with (
                    patch("urllib.request.urlopen", return_value=response) as server,
                    patch.object(serving_calls, "record_http_call", autospec=True),
                ):
                    result = analyzer._analyze_with_server(path, perf_counter())
            assert result.success, f"{label}: synthetic server response was not accepted"
            assert server.call_count == 1, f"{label}: expected one synthetic server request"
            request = json.loads(server.call_args.args[0].data)
            url = next(part["image_url"]["url"] for part in request["messages"][0]["content"]
                       if part.get("type") == "image_url")
            payload = base64.b64decode(url.split(",", 1)[1], validate=True)
            if configured is None:
                assert payload == path.read_bytes(), f"{label}: default changed the original image bytes"
            with Image.open(BytesIO(payload)) as image:
                image.load()
                assert image.size == expected, f"{label}: sent dimensions {image.size}, expected {expected}"


def cap_child(lane, path):
    """Probe the real candidate in a subprocess with its own wall deadline."""
    from PIL import Image

    sys.path.insert(0, str(lane))
    from src.vision.analyzers.vl_describe import encode_image_for_vl

    try:
        encoded, _, dimensions = encode_image_for_vl(path, 1)
    except Exception as exc:
        message = str(exc).strip()
        assert re.search(r"\b(?:pixel\w*|cap|patch\w*|budget|dimensions?|size|784)\b", message, re.IGNORECASE), (
            f"cap=1: encoder raised {type(exc).__name__} without a clear cap diagnostic: {message!r}")
        print(f"cap=1: returned promptly with {type(exc).__name__}: {message}")
        return
    from vision_contract_v2 import check_resized_geometry

    with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as decoded:
        decoded.load()
        assert decoded.size == tuple(dimensions), "cap=1: encoded and returned dimensions differ"
        check_resized_geometry((200, 150), 1, decoded.size)


def check_no_hang(lane):
    from PIL import Image

    with TemporaryDirectory(prefix="mm5-cap-") as scratch:
        path = Path(scratch) / "tiny-cap-fixture.png"
        with Image.new("RGB", (200, 150), color=(71, 133, 211)) as image:
            image.save(path)
        command = [sys.executable, "-B", __file__, "--cap-child", str(lane), str(path)]
        try:
            child = subprocess.run(command, check=False, capture_output=True, text=True,
                                   timeout=CHILD_TIMEOUT_S)
        except subprocess.TimeoutExpired as exc:
            raise AssertionError(f"cap=1: encoder did not return within {CHILD_TIMEOUT_S} seconds") from exc
        if child.returncode:
            lines = child.stderr.strip().splitlines()
            detail = lines[-1] if lines else f"child rc {child.returncode}"
            raise AssertionError(f"cap=1: {detail}")
        return child.stdout.strip()


def check_earlier_contract(lane):
    sys.path.insert(0, "/oracles")
    from vision_contract import _check_encodings
    from vision_contract_v2 import additional_checks

    _check_encodings(lane)
    additional_checks(lane)


def result_for(check, lane):
    try:
        detail = check(lane)
    except Exception as exc:
        return {"status": "fail", "failure_type": type(exc).__name__, "detail": str(exc)}
    return {"status": "pass", "detail": detail}


def main():
    lane = Path(sys.argv[1])
    results = {
        "unchanged_original_and_v2_feasible": result_for(check_earlier_contract, lane),
        "brief_environment_control": result_for(check_environment, lane),
        "additional_infeasible_cap_robustness": result_for(check_no_hang, lane),
    }
    print(json.dumps({"schema": "mm5.capped-encoding.v3", "checks": results}, sort_keys=True))
    raise SystemExit(any(item["status"] != "pass" for item in results.values()))


if __name__ == "__main__":
    if sys.argv[1] == "--cap-child":
        cap_child(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
