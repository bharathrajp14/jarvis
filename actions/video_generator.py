# actions/video_generator.py — JARVIS MK37 AI Video Generation
"""
AI video generation using multiple providers:
  - Google Veo (primary, via google.genai SDK)
  - Kling (via REST API, if KLING_API_KEY set)
"""
from __future__ import annotations

import base64
import json
import os
import time
import traceback
from datetime import datetime
from pathlib import Path


def _output_dir() -> Path:
    """Get or create the generated videos output directory."""
    d = Path(os.environ.get("JARVIS_VIDEO_DIR", "workspace/generated_videos"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_filename(prompt: str, ext: str = "mp4") -> str:
    """Generate a unique filename from the prompt."""
    slug = "".join(c if c.isalnum() or c == " " else "" for c in prompt[:40]).strip().replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}.{ext}"


def generate_video(
    prompt: str,
    provider: str = "auto",
    duration: int = 5,
    resolution: str = "1080p",
    aspect_ratio: str = "16:9",
    image_path: str = None,
) -> dict:
    """
    Generate a video from a text prompt.

    Args:
        prompt: Description of the video to generate.
        provider: 'veo', 'kling', or 'auto'.
        duration: Duration in seconds (5-10 for most providers).
        resolution: '720p', '1080p'.
        aspect_ratio: '16:9', '9:16', '1:1'.
        image_path: Optional reference image (for image-to-video).

    Returns:
        dict with 'path', 'provider', 'prompt', 'error'.
    """
    providers_to_try = []
    if provider == "auto":
        providers_to_try = ["veo", "kling"]
    else:
        providers_to_try = [provider.lower()]

    for prov in providers_to_try:
        try:
            if prov == "veo":
                result = _generate_veo(prompt, duration, aspect_ratio, image_path)
            elif prov == "kling":
                result = _generate_kling(prompt, duration, resolution, aspect_ratio)
            else:
                continue

            if result and result.get("path"):
                result["provider"] = prov
                result["prompt"] = prompt
                return result
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.warning(f"{ f"[VideoGen] {prov} failed: {e}" }" if isinstance(f"[VideoGen] {prov} failed: {e}", str) else f"[VideoGen] {prov} failed: {e}")
            else:
                import logging
                logging.getLogger(__name__).warning(f"{ f"[VideoGen] {prov} failed: {e}" }" if isinstance(f"[VideoGen] {prov} failed: {e}", str) else f"[VideoGen] {prov} failed: {e}")
            traceback.print_exc()
            continue

    return {"error": "All video generation providers failed.", "prompt": prompt, "path": None}


def _generate_veo(prompt: str, duration: int, aspect_ratio: str, image_path: str = None) -> dict:
    """Generate video using Google Veo via google.genai SDK."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    # Determine model based on features needed
    model = "veo-3.0-generate-preview"

    config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        number_of_videos=1,
    )

    # Generate video
    if image_path:
        # Image-to-video generation
        image = types.Image.from_file(image_path)
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image,
            config=config,
        )
    else:
        # Text-to-video generation
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=config,
        )

    # Poll for completion (video generation can take a while)
    max_wait = 300  # 5 minutes max
    start = time.time()
    while not operation.done:
        if time.time() - start > max_wait:
            return {"error": "Video generation timed out after 5 minutes."}
        time.sleep(10)
        operation = client.operations.get(operation)

    if not operation.response or not operation.response.generated_videos:
        return {"error": "Veo returned no video."}

    # Save the generated video
    video = operation.response.generated_videos[0]
    filename = _make_filename(prompt, "mp4")
    filepath = _output_dir() / filename

    video.video.save(str(filepath))

    return {"path": str(filepath)}


def _generate_kling(prompt: str, duration: int, resolution: str, aspect_ratio: str) -> dict:
    """Generate video using Kling AI REST API."""
    import requests

    api_key = os.environ.get("KLING_API_KEY", "")
    if not api_key:
        raise ValueError("KLING_API_KEY not set")

    url = "https://api.klingai.com/v1/videos/text-to-video"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "duration": str(min(duration, 10)),
        "aspect_ratio": aspect_ratio,
    }

    # Submit generation request
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        return {"error": "Kling API did not return a task ID."}

    # Poll for completion
    status_url = f"https://api.klingai.com/v1/videos/text-to-video/{task_id}"
    max_wait = 300
    start = time.time()

    while True:
        if time.time() - start > max_wait:
            return {"error": "Kling video generation timed out."}

        time.sleep(15)
        status_resp = requests.get(status_url, headers=headers, timeout=30)
        status_data = status_resp.json()
        task_status = status_data.get("data", {}).get("task_status", "")

        if task_status == "succeed":
            videos = status_data.get("data", {}).get("task_result", {}).get("videos", [])
            if videos:
                video_url = videos[0].get("url", "")
                if video_url:
                    # Download the video
                    video_resp = requests.get(video_url, timeout=120)
                    filename = _make_filename(prompt, "mp4")
                    filepath = _output_dir() / filename
                    filepath.write_bytes(video_resp.content)
                    return {"path": str(filepath)}
            return {"error": "Kling returned no video URL."}
        elif task_status == "failed":
            return {"error": "Kling video generation failed."}


def list_generated_videos() -> list[str]:
    """List all generated video files."""
    out = _output_dir()
    return [str(f) for f in out.glob("*.mp4")]
