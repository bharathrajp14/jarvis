# tools/video_tools.py — JARVIS MK37 Video Generation Tools Plugin
"""
Registers AI video generation tools in the JARVIS tool registry.
"""
from __future__ import annotations

import json
import os
from .registry import register_tool


@register_tool(
    name="generate_video",
    description="Generate an AI video from a text description. Providers: veo (Google Veo), kling (Kling AI). Returns file path of the generated video.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Detailed description of the video to generate"},
            "provider": {"type": "string", "description": "Provider: 'auto', 'veo', 'kling' (default: auto)"},
            "duration": {"type": "integer", "description": "Duration in seconds (default: 5)"},
            "resolution": {"type": "string", "description": "Resolution: '720p' or '1080p' (default: 1080p)"},
            "aspect_ratio": {"type": "string", "description": "Aspect ratio: '16:9', '9:16', '1:1' (default: 16:9)"},
            "image_path": {"type": "string", "description": "Optional reference image for image-to-video generation"},
        },
        "required": ["prompt"],
    }
)
def tool_generate_video(args: dict) -> str:
    from actions.video_generator import generate_video
    result = generate_video(
        prompt=args["prompt"],
        provider=args.get("provider", "auto"),
        duration=args.get("duration", 5),
        resolution=args.get("resolution", "1080p"),
        aspect_ratio=args.get("aspect_ratio", "16:9"),
        image_path=args.get("image_path"),
    )
    return json.dumps(result, indent=2)


@register_tool(
    name="list_generated_videos",
    description="List all previously generated AI videos.",
    parameters={}
)
def tool_list_generated_videos(args: dict) -> str:
    from actions.video_generator import list_generated_videos
    videos = list_generated_videos()
    if not videos:
        return "No generated videos found."
    return json.dumps(videos, indent=2)
