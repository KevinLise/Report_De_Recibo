from __future__ import annotations

from app.config import get_settings


def probe() -> dict:
    s = get_settings()
    pymu = True
    try:
        import pymupdf4llm  # noqa: F401
    except Exception:
        pymu = False
    from app.core.ocr import available as ocr_ok

    gemini_ok = False
    if s.GEMINI_ENABLED and s.GEMINI_API_KEY:
        try:
            import google.genai  # noqa: F401

            gemini_ok = True
        except Exception:
            gemini_ok = False

    ollama = {"ok": False, "chat": s.OLLAMA_CHAT_MODEL, "embed": s.OLLAMA_EMBED_MODEL}
    try:
        import httpx

        r = httpx.get(s.OLLAMA_HOST + "/api/tags", timeout=1.5)
        ollama["ok"] = r.status_code == 200
    except Exception:
        pass

    chat_ok = ollama["ok"] or gemini_ok
    primary = "ollama" if ollama["ok"] else ("gemini" if gemini_ok else None)
    return {
        "pymupdf4llm": pymu,
        "rapidocr": ocr_ok(),
        "gemini": {
            "configured": bool(s.GEMINI_API_KEY) and s.GEMINI_ENABLED,
            "ok": gemini_ok,
            "model": s.GEMINI_MODEL,
        },
        "ollama": ollama,
        "chat": {
            "ok": chat_ok,
            "primary": primary,
        },
        "inbox": str(s.inbox_path),
        "db": str(s.db_path),
    }
