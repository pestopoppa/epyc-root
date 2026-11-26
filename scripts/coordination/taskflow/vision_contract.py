"""Independent, zero-inference acceptance for the MM-5 image encoding helpers."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch


ORCH_PYTHON = Path("/workspace/repos/epyc-orchestrator/.venv/bin/python")
_SUCCESS = "MM-5 vision contract passed"
_TIMEOUT_S = 120


def check(lane: Path, *, python: Path = ORCH_PYTHON) -> tuple[bool, str]:
    """Run verifier-owned cases in the app interpreter. Runtime startup errors raise."""
    lane = lane.resolve()
    try:
        result = subprocess.run(
            [str(python), "-I", "-B", str(Path(__file__).resolve()), str(lane)],
            cwd=lane,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=_TIMEOUT_S,
        )
    except OSError as exc:
        raise RuntimeError(f"MM-5 contract could not start: {exc}") from exc
    except subprocess.TimeoutExpired:
        return False, f"MM-5 candidate checks timed out after {_TIMEOUT_S} seconds"
    if result.returncode == 0 and result.stdout.splitlines()[-1:] == [_SUCCESS]:
        return True, _SUCCESS
    details = (result.stderr.strip() or result.stdout.strip()).splitlines()
    diagnostic = details[-1][:350] if details else "no result"
    return False, f"MM-5 contract exited {result.returncode}: {diagnostic}"


def _check_encodings(lane: Path) -> None:
    from PIL import Image

    os.environ.pop("ORCHESTRATOR_VL_MAX_PIXELS", None)
    sys.path.insert(0, str(lane))
    from src.vision.analyzers.vl_describe import encode_image_for_vl, vision_token_estimate

    with TemporaryDirectory(prefix="taskflow-mm5-") as tmpdir:
        for label, size, cap in (
            ("large", (4000, 3000), 1_000_000),
            ("wide", (4000, 100), 784),
            ("tall", (100, 4000), 784),
        ):
            path = Path(tmpdir) / f"{label}.png"
            with Image.new("RGB", size, color=(71, 133, 211)) as original:
                original.save(path)

            encoded, mime, dimensions = encode_image_for_vl(path, None)
            assert base64.b64decode(encoded, validate=True) == path.read_bytes(), f"{label}: raw bytes changed"
            assert mime == "image/png", f"{label}: raw PNG MIME was {mime!r}"
            assert dimensions == size, f"{label}: raw dimensions {dimensions!r}, expected {size}"

            encoded, mime, dimensions = encode_image_for_vl(path, cap)
            assert mime == "image/png", f"{label}: resized PNG MIME was {mime!r}"
            with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as decoded:
                assert decoded.format == "PNG", f"{label}: resized payload is {decoded.format!r}"
                decoded.load()
                assert decoded.size == dimensions, (
                    f"{label}: encoded dimensions {decoded.size}, reported {dimensions!r}"
                )
                width, height = decoded.size
            assert width % 28 == height % 28 == 0, f"{label}: dimensions {dimensions} are off the 28-pixel grid"
            assert width * height <= cap, f"{label}: dimensions {dimensions} exceed the {cap}-pixel cap"

        assert vision_token_estimate(896, 896) == 1024, "896×896 must estimate 1024 vision tokens"
        path = Path(tmpdir) / "recorded.png"
        with Image.new("RGB", (896, 896)) as image:
            image.save(path)
        _check_server_path(path)


def _check_server_path(path: Path) -> None:
    from PIL import Image

    from src.backends import serving_calls
    from src.vision.analyzers.vl_describe import VLDescribeAnalyzer

    for cap, size, estimate in ((None, (896, 896), 1024), (784, (28, 28), 1)):
        label = f"server max_pixels={cap}"
        kwargs = {} if cap is None else {"max_pixels": cap}
        analyzer = VLDescribeAnalyzer(backend="server", **kwargs)
        response = BytesIO(b'{"choices": [{"message": {"content": "fixture description"}}]}')
        response.status = 200
        with (
            patch("urllib.request.urlopen", return_value=response) as server,
            patch.object(serving_calls, "record_http_call", autospec=True) as recorder,
        ):
            result = analyzer._analyze_with_server(path, perf_counter())

        assert result.success, f"{label}: synthetic response was not accepted"
        assert server.call_count == 1, f"{label}: expected one server request"
        payload = json.loads(server.call_args.args[0].data)
        image_url = next(
            part["image_url"]["url"]
            for part in payload["messages"][0]["content"]
            if part.get("type") == "image_url"
        )
        sent = base64.b64decode(image_url.split(",", 1)[1], validate=True)
        if cap is None:
            assert sent == path.read_bytes(), f"{label}: server request changed default bytes"
        with Image.open(BytesIO(sent)) as decoded:
            assert decoded.size == size, f"{label}: server sent dimensions {decoded.size}, expected {size}"

        assert recorder.call_count == 1, f"{label}: expected one serving-call record"
        notes = recorder.call_args.kwargs.get("notes") or {}
        assert notes.get("vision_token_estimate") == estimate, (
            f"{label}: serving-call estimate {notes.get('vision_token_estimate')!r}, expected {estimate}"
        )


if __name__ == "__main__":
    _check_encodings(Path(sys.argv[1]))
    print(_SUCCESS)
