from __future__ import annotations

import logging
import math

from app.config import get_settings

logger = logging.getLogger(__name__)
TILE = 258


def estimate_image_tokens(w: int, h: int) -> int:
    if w <= 384 and h <= 384:
        return TILE
    tiles_x = math.ceil(w / 768)
    tiles_y = math.ceil(h / 768)
    return tiles_x * tiles_y * TILE


def count_gemini(prompt: str, image_bytes: bytes | None) -> int:
    settings = get_settings()
    if not settings.GEMINI_API_KEY or not settings.GEMINI_ENABLED:
        return 0
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        parts: list = [prompt]
        if image_bytes:
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))
        r = client.models.count_tokens(model=settings.GEMINI_MODEL, contents=parts)
        return int(getattr(r, "total_tokens", 0) or 0)
    except Exception as exc:
        logger.warning("count_tokens falló: %s", exc)
        return 0


def from_usage(resp) -> dict:
    meta = getattr(resp, "usage_metadata", None)
    tin = int(getattr(meta, "prompt_token_count", 0) or 0) if meta else 0
    tout = int(getattr(meta, "candidates_token_count", 0) or 0) if meta else 0
    return {"tokens_in": tin, "tokens_out": tout, "tokens_total": tin + tout}
