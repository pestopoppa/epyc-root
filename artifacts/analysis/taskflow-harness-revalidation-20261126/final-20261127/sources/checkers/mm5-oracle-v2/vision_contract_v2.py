"""Preserve the original MM-5 contract and check its capped-image requirements."""
from __future__ import annotations

import base64
from fractions import Fraction
from io import BytesIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PATCH = 28


def check_resized_geometry(source, cap, encoded):
    """Require a consistent resize up to grid rounding or a required minimum side."""
    w, h = source
    width, height = encoded
    assert width > 0 and height > 0 and width % PATCH == height % PATCH == 0, (
        f"source {source}, cap {cap}: encoded dimensions {encoded} are off the positive {PATCH}-pixel grid")
    assert width * height <= cap, f"source {source}, cap {cap}: encoded dimensions {encoded} exceed the cap"
    # A minimum side can make the exact source ratio infeasible at this cap.
    # Keep portrait/landscape orientation whenever at least two tiles fit.
    if min(w, h) ** 2 * cap < PATCH ** 2 * w * h:
        if cap >= 2 * PATCH ** 2:
            assert (w - h) * (width - height) > 0, (
                f"source {source}, cap {cap}: encoded dimensions {encoded} lose source orientation")
        return
    # Floor rounding admits every output with one common scale in both
    # corresponding patch intervals. This allows legitimate variations.
    lower = max(Fraction(width, w), Fraction(height, h))
    upper = min(Fraction(width + PATCH, w), Fraction(height + PATCH, h))
    assert lower < upper, f"source {source}, cap {cap}: encoded dimensions {encoded} are inconsistent with aspect-preserving grid rounding"


def check_unchanged(path, cap, encoded, mime, dimensions):
    expected = path.read_bytes()
    actual = base64.b64decode(encoded, validate=True)
    assert actual == expected, f"under-cap image at cap {cap}: encoded bytes differ from the original"
    from PIL import Image

    with Image.open(BytesIO(expected)) as source:
        assert mime == "image/png", "unchanged PNG has incorrect MIME"
        assert dimensions == source.size, f"unchanged PNG dimensions {dimensions} differ from {source.size}"


def additional_checks(lane):
    from PIL import Image

    sys.path.insert(0, str(lane))
    from src.vision.analyzers.vl_describe import encode_image_for_vl

    with TemporaryDirectory(prefix="mm5-capped-") as scratch:
        path = Path(scratch) / "fixture.png"
        with Image.new("RGB", (200, 150), color=(71, 133, 211)) as image:
            image.save(path)
        for cap in (30_000, 1_000_000):
            check_unchanged(path, cap, *encode_image_for_vl(path, cap))
        for size, cap in (((100, 4000), 7840), ((4000, 100), 7840),
                          ((641, 913), 200_000), ((913, 641), 200_000)):
            with Image.new("RGB", size, color=(71, 133, 211)) as image:
                image.save(path)
            encoded, mime, dimensions = encode_image_for_vl(path, cap)
            assert mime == "image/png", f"source {size}, cap {cap}: resized image must be PNG"
            with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as decoded:
                assert decoded.format == "PNG", f"source {size}, cap {cap}: encoded payload is not PNG"
                decoded.load()
                assert decoded.size == dimensions, (
                    f"source {size}, cap {cap}: reported {dimensions}, decoded {decoded.size}")
            check_resized_geometry(size, cap, dimensions)


def main():
    sys.path.insert(0, "/oracles")
    from vision_contract import _check_encodings

    lane = Path(sys.argv[1])
    _check_encodings(lane)
    additional_checks(lane)
    print("MM-5 original vision contract and capped-image controls passed")


if __name__ == "__main__":
    main()
