from __future__ import annotations

import logging
import struct

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack(blob: bytes | None) -> list[float] | None:
    if not blob:
        return None
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def embed(texts: list[str], timeout: float | None = None) -> list[list[float] | None]:
    s = get_settings()
    try:
        r = httpx.post(
            s.OLLAMA_HOST + "/api/embed",
            json={"model": s.OLLAMA_EMBED_MODEL, "input": texts},
            timeout=timeout if timeout is not None else 20,
        )
        r.raise_for_status()
        data = r.json()
        embs = data.get("embeddings") or data.get("embedding")
        if isinstance(embs, list) and embs and isinstance(embs[0], (int, float)):
            return [list(map(float, embs))]
        if isinstance(embs, list):
            return [list(map(float, e)) for e in embs]
    except Exception as exc:
        logger.warning("embed: %s", exc)
    return [None] * len(texts)
