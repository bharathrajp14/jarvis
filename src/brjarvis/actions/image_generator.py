# actions/image_generator.py — JARVIS MK37 AI Image Generation
"""
AI image generation using multiple providers:
  - Gemini Imagen (primary, via google.genai SDK)
  - OpenAI DALL-E 3 (via openai SDK)
  - Stability AI (via REST API)
"""
from __future__ import annotations

import base64
import json
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger("JARVIS.ImageGen")


def _output_dir() -> Path:
    """Get or create the generated images output directory."""
    d = Path(os.environ.get("JARVIS_IMAGE_DIR", "workspace/generated_images"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_filename(prompt: str, ext: str = "png") -> str:
    """Generate a unique filename from the prompt."""
    slug = "".join(c if c.isalnum() or c == " " else "" for c in prompt[:40]).strip().replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{ts}.{ext}"


def generate_image(
    prompt: str,
    provider: str = "auto",
    size: str = "1024x1024",
    style: str = "vivid",
    negative_prompt: str = "",
    num_images: int = 1,
) -> dict:
    """
    Generate an image from a text prompt.

    Args:
        prompt: Description of the image to generate.
        provider: 'gemini', 'openai', 'stability', or 'auto' (try in order).
        size: Image dimensions (e.g., '1024x1024', '1792x1024').
        style: Style preset ('vivid', 'natural').
        negative_prompt: What to avoid in the image.
        num_images: Number of images to generate (1-4).

    Returns:
        dict with 'paths', 'provider', 'prompt', 'error' (if any).
    """
    providers_to_try = []
    if provider == "auto":
        providers_to_try = ["gemini", "openai", "stability"]
    else:
        providers_to_try = [provider.lower()]

    for prov in providers_to_try:
        try:
            if prov == "gemini":
                result = _generate_gemini(prompt, size, num_images)
            elif prov == "openai":
                result = _generate_openai(prompt, size, style, num_images)
            elif prov == "stability":
                result = _generate_stability(prompt, size, negative_prompt, num_images)
            else:
                continue

            if result and result.get("paths"):
                result["provider"] = prov
                result["prompt"] = prompt
                return result
        except Exception as e:
            logger.warning(f"[ImageGen] {prov} failed: {e}")
            traceback.print_exc()
            continue

    return {"error": "All image generation providers failed.", "prompt": prompt, "paths": []}


def _generate_gemini(prompt: str, size: str, num_images: int) -> dict:
    """Generate using Gemini Imagen via google.genai SDK."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    imagen_models = ["imagen-3.0-fast-generate-001", "imagen-3.0-generate-001", "imagen-3.0-generate-002"]
    last_err = None
    for model_name in imagen_models:
        try:
            response = client.models.generate_images(
                model=model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=min(num_images, 4),
                    aspect_ratio="1:1" if "1024x1024" in size else "16:9",
                ),
            )
            paths = []
            for i, image in enumerate(response.generated_images):
                filename = _make_filename(prompt, "png")
                if i > 0:
                    filename = filename.replace(".png", f"_{i}.png")
                filepath = _output_dir() / filename
                image.image.save(str(filepath))
                paths.append(str(filepath))
            return {"paths": paths}
        except Exception as e:
            last_err = e
            continue
    raise last_err or ValueError("Failed to generate image with Gemini Imagen models")


def _generate_openai(prompt: str, size: str, style: str, num_images: int) -> dict:
    """Generate using OpenAI DALL-E 3."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)
    img_model = os.environ.get("OPENAI_IMAGE_MODEL", "gemini-3-pro-image")
    try:
        response = client.images.generate(
            model=img_model,
            prompt=prompt,
            n=min(num_images, 1),
            response_format="b64_json",
        )
    except Exception as e:
        if "dall-e-3" not in img_model:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=min(num_images, 1),
                response_format="b64_json",
            )
        else:
            raise e

    paths = []
    for i, img_data in enumerate(response.data):
        filename = _make_filename(prompt, "png")
        if i > 0:
            filename = filename.replace(".png", f"_{i}.png")
        filepath = _output_dir() / filename
        img_bytes = base64.b64decode(img_data.b64_json)
        filepath.write_bytes(img_bytes)
        paths.append(str(filepath))

    return {"paths": paths}


def _generate_stability(prompt: str, size: str, negative_prompt: str, num_images: int) -> dict:
    """Generate using Stability AI REST API."""
    import requests

    api_key = os.environ.get("STABILITY_API_KEY", "")
    if not api_key:
        raise ValueError("STABILITY_API_KEY not set")

    # Parse size
    w, h = 1024, 1024
    if "x" in size:
        parts = size.split("x")
        w, h = int(parts[0]), int(parts[1])

    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    payload = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": "1:1" if w == h else "16:9",
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    paths = []
    if "image" in data:
        filename = _make_filename(prompt, "png")
        filepath = _output_dir() / filename
        img_bytes = base64.b64decode(data["image"])
        filepath.write_bytes(img_bytes)
        paths.append(str(filepath))

    return {"paths": paths}


def edit_image(
    image_path: str,
    prompt: str,
    mask_path: str = None,
    provider: str = "openai",
) -> dict:
    """
    Edit an existing image using AI.

    Args:
        image_path: Path to the source image.
        prompt: What to change in the image.
        mask_path: Optional mask image for inpainting.
        provider: 'openai' or 'stability'.

    Returns:
        dict with 'path', 'provider'.
    """
    try:
        if provider == "openai":
            return _edit_openai(image_path, prompt, mask_path)
        elif provider == "stability":
            return {"error": "Stability AI editing not yet implemented."}
        else:
            return {"error": f"Unknown provider: {provider}"}
    except Exception as e:
        return {"error": f"Image editing failed: {e}"}


def _edit_openai(image_path: str, prompt: str, mask_path: str = None) -> dict:
    """Edit image using OpenAI."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    kwargs = {
        "model": "dall-e-2",
        "image": open(image_path, "rb"),
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    if mask_path:
        kwargs["mask"] = open(mask_path, "rb")

    response = client.images.edit(**kwargs)
    filename = _make_filename(prompt, "png")
    filepath = _output_dir() / filename
    img_bytes = base64.b64decode(response.data[0].b64_json)
    filepath.write_bytes(img_bytes)

    return {"path": str(filepath), "provider": "openai"}
