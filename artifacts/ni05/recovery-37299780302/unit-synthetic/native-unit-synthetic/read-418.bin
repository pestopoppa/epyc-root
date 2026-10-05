import base64
from pathlib import Path

import pytest
from PIL import Image

from src.models.image import ImageGenerateRequest
from src.services.image_generator import ImageGenerator


def test_auto_enhance_prefers_text_surfaces() -> None:
    request = ImageGenerateRequest(prompt="Create an infographic about kernel v6 speedups.")

    assert request.enhance_auto_reason() == "text_surface"
    assert request.resolve_enhance() is True


def test_auto_enhance_suppresses_compositional_prompts() -> None:
    request = ImageGenerateRequest(prompt="A red cube to the left of a blue sphere on a table.")

    assert request.enhance_auto_reason() == "compositional_scene"
    assert request.resolve_enhance() is False


def test_auto_enhance_keeps_short_prompt_fallback() -> None:
    request = ImageGenerateRequest(prompt="A watercolor city street at sunrise.")

    assert request.enhance_auto_reason() == "short_prompt"
    assert request.resolve_enhance() is True


def test_auto_enhance_disables_already_rich_prompt() -> None:
    prompt = " ".join(f"detail{i}" for i in range(60))
    request = ImageGenerateRequest(prompt=prompt)

    assert request.enhance_auto_reason() == "rich_prompt"
    assert request.resolve_enhance() is False


class FakeSDClient:
    async def txt2img(self, **kwargs):
        self.kwargs = kwargs
        return {
            "images": [base64.b64encode(b"fake image bytes").decode("ascii")],
            "info": "ok",
        }


@pytest.mark.asyncio
async def test_generator_records_unwired_enhancer_policy(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("src.services.image_generator.output_dir_for_today", lambda: tmp_path)
    client = FakeSDClient()
    generator = ImageGenerator(client=client)

    result = await generator.generate(
        ImageGenerateRequest(
            prompt="A red cube to the left of a blue sphere.",
            seed=123,
            reference_images=("/mnt/raid0/llm/output/images/ref.png",),
        )
    )

    assert result.success
    assert result.enhancer_used is False
    assert result.metadata["enhance_policy"] == "auto"
    assert result.metadata["enhance_resolved"] is False
    assert result.metadata["enhance_auto_reason"] == "compositional_scene"
    assert result.metadata["enhancer_available"] is False
    assert result.metadata["backend"] == "qwen_image_2_1"
    assert client.kwargs["prompt"] == "A red cube to the left of a blue sphere."
    assert client.kwargs["reference_images"] == ("/mnt/raid0/llm/output/images/ref.png",)


def test_qwen_service_request_validation() -> None:
    from src.services.qwen_image_server import validate_request

    request = validate_request({"prompt": "A quiet mountain lake."})
    assert request["steps"] == 40
    assert request["width"] == request["height"] == 1024
    assert request["cfg_scale"] == 1.0

    with pytest.raises(ValueError, match="multiples of 16"):
        validate_request({"prompt": "x", "width": 513, "height": 512})
    with pytest.raises(ValueError, match="pixel limit"):
        validate_request({"prompt": "x", "width": 3072, "height": 2048})
    with pytest.raises(ValueError, match="at most 10"):
        validate_request({"prompt": "x", "reference_images": ["ref.png"] * 11})


def test_qwen_service_rejects_reference_paths_outside_allowed_roots(tmp_path: Path) -> None:
    from src.services.qwen_image_server import load_reference_images

    untrusted_path = tmp_path / "not-allowed.png"
    untrusted_path.write_bytes(b"placeholder")
    with pytest.raises(ValueError, match="allowed image-input root"):
        load_reference_images([str(untrusted_path)])


def test_qwen_service_maps_request_and_returns_legacy_response(monkeypatch) -> None:
    from src.services.qwen_image_server import generate_images

    class FakeGenerator:
        def __init__(self, device):
            assert device == "cpu"

        def manual_seed(self, seed):
            self.seed = seed
            return self

    class FakeTorch:
        Generator = FakeGenerator

    class FakePipeline:
        def __call__(self, **kwargs):
            self.kwargs = kwargs
            return type("Result", (), {"images": [Image.new("RGB", (8, 8), "white")]})()

    pipeline = FakePipeline()
    monkeypatch.setattr(
        "src.services.qwen_image_server.load_reference_images",
        lambda paths: ["fake-reference"] if paths else [],
    )
    response = generate_images(
        {
            "prompt": "A quiet mountain lake.",
            "width": 512,
            "height": 512,
            "seed": 17,
            "reference_images": ["/mnt/raid0/llm/output/images/reference.jpg"],
        },
        pipeline,
        FakeTorch,
    )

    assert pipeline.kwargs["num_inference_steps"] == 40
    assert pipeline.kwargs["width"] == pipeline.kwargs["height"] == 512
    assert pipeline.kwargs["generator"].seed == 17
    assert pipeline.kwargs["image"] == ["fake-reference"]
    assert "images" in response and "info" in response and "parameters" in response
    assert response["parameters"]["seed"] == 17
    assert '"reference_count":1' in response["info"]
