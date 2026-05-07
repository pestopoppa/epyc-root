"""Hermes plugin: local self-hosted image_generate via ERNIE-Image-Turbo.

Registered tool name: image_generate (overrides the FAL cloud
implementation that ships with hermes-agent's model_tools.py).

The handler delegates to src.services.image_generator.ImageGenerator from
the epyc-orchestrator repo, which submits a ComfyUI workflow on
127.0.0.1:8188 and returns a saved file path + base64 bytes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# epyc-orchestrator repo on the Python path so we can import its services.
_ORCH_ROOT = Path("/mnt/raid0/llm/epyc-orchestrator")
if str(_ORCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_ORCH_ROOT))


_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "image_generate",
        "description": (
            "Generate an image from a text prompt using ERNIE-Image-Turbo "
            "(self-hosted, single-stream DiT, 8-step distilled). Bilingual "
            "EN+ZH, strong on dense in-image text rendering (posters, "
            "infographics, comics). Saves the result under "
            "/mnt/raid0/llm/output/images/YYYY-MM-DD/ and returns the path "
            "plus base64 bytes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Image description.",
                },
                "width": {
                    "type": "integer",
                    "description": "Width in pixels (default 1024).",
                    "default": 1024,
                },
                "height": {
                    "type": "integer",
                    "description": "Height in pixels (default 1024).",
                    "default": 1024,
                },
                "seed": {
                    "type": ["integer", "null"],
                    "description": "Optional fixed seed for reproducibility; null = random.",
                    "default": None,
                },
                "steps": {
                    "type": "integer",
                    "description": "Sampling steps (default 8 — model is distilled for 8-step).",
                    "default": 8,
                },
                "enhance_prompt": {
                    "type": ["string", "boolean"],
                    "description": (
                        "Prompt enhancer policy: 'auto' (default — on for prompts "
                        "<50 words, off otherwise), true (always on), false (always off)."
                    ),
                    "default": "auto",
                },
            },
            "required": ["prompt"],
        },
    },
}


async def _handle_image_generate(args, **_kw):
    """Async handler invoked by the Hermes tool dispatcher."""
    from src.models.image import ImageGenerateRequest
    from src.services.image_generator import ImageGenerator

    prompt = args.get("prompt")
    if not prompt:
        return json.dumps({"error": "prompt is required"})

    enhance = args.get("enhance_prompt", "auto")
    if isinstance(enhance, str):
        if enhance.lower() == "true":
            enhance = True
        elif enhance.lower() == "false":
            enhance = False
        else:
            enhance = "auto"

    req = ImageGenerateRequest(
        prompt=prompt,
        width=int(args.get("width", 1024)),
        height=int(args.get("height", 1024)),
        seed=args.get("seed"),
        steps=int(args.get("steps", 8)),
        enhance=enhance,
    )

    gen = ImageGenerator()
    try:
        result = await gen.generate(req)
    finally:
        await gen.client.close()

    payload = result.to_dict()
    # Trim base64 from agent context: 1024² PNG is ~1.5 MB which becomes
    # ~2 MB base64 — too large to cycle through the LLM. Return the path;
    # callers that need bytes can read from disk.
    payload.pop("image_bytes_b64", None)
    return json.dumps(payload, default=str)


def register(ctx):
    """Plugin entry point — called by hermes_cli/plugins.py at startup."""
    ctx.register_tool(
        name="image_generate",
        toolset="image_gen",
        schema=_TOOL_SCHEMA,
        handler=_handle_image_generate,
        is_async=True,
        description=(
            "Generate an image from a text prompt via local ERNIE-Image-Turbo "
            "(replaces the disabled FAL cloud adapter)."
        ),
        emoji="🎨",
    )
    logger.info("local-image-generate plugin: image_generate now points at local ComfyUI")
