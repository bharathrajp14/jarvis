# tools/image_tools.py — JARVIS MK37 Image Generation Tools Plugin
"""
Registers AI image generation and editing tools in the JARVIS tool registry.
"""
from __future__ import annotations

import json
from .registry import register_tool


@register_tool(
    name="generate_image",
    description="Generate an AI image from a text description. Providers: gemini (Imagen), openai (DALL-E 3), stability (Stable Diffusion). Returns file paths of generated images.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Detailed description of the image to generate"},
            "provider": {"type": "string", "description": "Provider: 'auto', 'gemini', 'openai', 'stability' (default: auto)"},
            "size": {"type": "string", "description": "Image size: '1024x1024', '1792x1024', '1024x1792' (default: 1024x1024)"},
            "style": {"type": "string", "description": "Style: 'vivid' or 'natural' (default: vivid)"},
            "negative_prompt": {"type": "string", "description": "What to avoid in the image"},
            "num_images": {"type": "integer", "description": "Number of images (1-4, default: 1)"},
        },
        "required": ["prompt"],
    }
)
def tool_generate_image(args: dict) -> str:
    from actions.image_generator import generate_image
    result = generate_image(
        prompt=args["prompt"],
        provider=args.get("provider", "auto"),
        size=args.get("size", "1024x1024"),
        style=args.get("style", "vivid"),
        negative_prompt=args.get("negative_prompt", ""),
        num_images=args.get("num_images", 1),
    )
    return json.dumps(result, indent=2)


@register_tool(
    name="edit_image",
    description="Edit an existing image using AI. Supports inpainting with optional mask.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Path to the source image to edit"},
            "prompt": {"type": "string", "description": "What to change in the image"},
            "mask_path": {"type": "string", "description": "Optional path to mask image for inpainting"},
            "provider": {"type": "string", "description": "Provider: 'openai' (default)"},
        },
        "required": ["image_path", "prompt"],
    }
)
def tool_edit_image(args: dict) -> str:
    from actions.image_generator import edit_image
    result = edit_image(
        image_path=args["image_path"],
        prompt=args["prompt"],
        mask_path=args.get("mask_path"),
        provider=args.get("provider", "openai"),
    )
    return json.dumps(result, indent=2)
