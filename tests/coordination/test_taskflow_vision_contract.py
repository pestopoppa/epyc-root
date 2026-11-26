"""Regressions for the verifier-owned MM-5 candidate checks."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import vision_contract  # noqa: E402


_CANDIDATE = """
import base64
import json
import urllib.request
from io import BytesIO
from types import SimpleNamespace
from PIL import Image
from src.backends import serving_calls


def encode_image_for_vl(path, max_pixels):
    with Image.open(path) as original:
        w, h = original.size
        if max_pixels is None:
            size = (0, 0) if variant == "zero raw dimensions" else (w, h)
            raw = b"wrong bytes" if variant == "reencoded default" else path.read_bytes()
            return base64.b64encode(raw).decode("ascii"), "image/png", size

        scale = (max_pixels / (w * h)) ** 0.5
        width = max(28, int(w * scale) // 28 * 28)
        height = max(28, int(h * scale) // 28 * 28)
        if width >= height and variant != "cap overflow":
            width = min(width, max_pixels // height // 28 * 28)
        if width < height and variant != "tall overflow":
            height = min(height, max_pixels // width // 28 * 28)
        with BytesIO() as output:
            original.resize((width, height)).save(output, format="PNG")
            size = (w, h) if variant == "original resize dimensions" else (width, height)
            return base64.b64encode(output.getvalue()).decode("ascii"), "image/png", size


def vision_token_estimate(w, h):
    return 1 if variant == "bad estimate" else (w // 28) * (h // 28)


class VLDescribeAnalyzer:
    def __init__(self, *, backend, max_pixels=None):
        self.max_pixels = max_pixels

    def _analyze_with_server(self, path, start):
        cap = None if variant == "wire bypass" else self.max_pixels
        encoded, mime, (w, h) = encode_image_for_vl(path, cap)
        payload = {
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
            ]}],
        }
        request = urllib.request.Request("http://127.0.0.1", data=json.dumps(payload).encode())
        with urllib.request.urlopen(request) as response:
            response.read()
        try:
            estimate = vision_token_estimate(w, h)
            if variant == "unsupported recorder keyword":
                serving_calls.record_http_call(vision_token_count=estimate)
            else:
                notes = {} if variant == "missing recorder estimate" else {"vision_token_estimate": estimate}
                serving_calls.record_http_call(notes=notes)
        except TypeError:
            pass
        return SimpleNamespace(success=True)
"""


@pytest.mark.skipif(not vision_contract.ORCH_PYTHON.exists(), reason="orchestrator venv unavailable")
@pytest.mark.parametrize(
    ("variant", "failure"),
    [
        ("correct", ""),
        ("reencoded default", "large: raw bytes changed"),
        ("zero raw dimensions", "large: raw dimensions (0, 0)"),
        ("original resize dimensions", "large: encoded dimensions"),
        ("cap overflow", "wide: dimensions (168, 28) exceed the 784-pixel cap"),
        ("tall overflow", "tall: dimensions (28, 168) exceed the 784-pixel cap"),
        ("bad estimate", "896×896 must estimate 1024 vision tokens"),
        ("wire bypass", "server max_pixels=784: server sent dimensions (896, 896)"),
        ("unsupported recorder keyword", "server max_pixels=None: expected one serving-call record"),
        ("missing recorder estimate", "server max_pixels=None: serving-call estimate None, expected 1024"),
    ],
)
def test_mm5_candidate_contract(tmp_path, variant, failure):
    module = tmp_path / "src" / "vision" / "analyzers" / "vl_describe.py"
    module.parent.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").touch()
    module.write_text(f"variant = {variant!r}\n" + _CANDIDATE)
    recorder = tmp_path / "src" / "backends" / "serving_calls.py"
    recorder.parent.mkdir()
    recorder.write_text("def record_http_call(*, notes=None): pass\n")

    ok, diagnostic = vision_contract.check(tmp_path)
    assert ok is (not failure), diagnostic
    assert failure in diagnostic


def test_mm5_contract_missing_interpreter(tmp_path):
    with pytest.raises(RuntimeError, match="MM-5 contract could not start"):
        vision_contract.check(tmp_path, python=tmp_path / "missing-python")



def test_mm5_candidate_timeout_rejects(monkeypatch, tmp_path):
    interpreter = tmp_path / "stuck-candidate"
    interpreter.write_text("#!/bin/sh\nexec sleep 5\n")
    interpreter.chmod(0o700)
    monkeypatch.setattr(vision_contract, "_TIMEOUT_S", 0.05)

    ok, diagnostic = vision_contract.check(tmp_path, python=interpreter)

    assert not ok
    assert diagnostic == "MM-5 candidate checks timed out after 0.05 seconds"
