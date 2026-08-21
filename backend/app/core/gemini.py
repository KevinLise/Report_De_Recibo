from __future__ import annotations

import logging

from app.config import get_settings
from app.domains.invoice import InvoiceDraft

logger = logging.getLogger(__name__)

PROMPT = """Extrae una factura o comprobante colombiano.
Devuelve solo el schema: supplier, nit, number, date (YYYY-MM-DD), due_date,
subtotal, tax, discount, total, items[{description,qty,unit,net}], report (1-2 frases).
Montos en número, sin símbolo. NIT con dígito. No inventes ítems.
No recalcules totales: copia lo que se lee."""


class GeminiUnavailable(Exception):
    pass


def configured() -> bool:
    s = get_settings()
    return bool(s.GEMINI_ENABLED and s.GEMINI_API_KEY)


def extract(png: bytes) -> tuple[InvoiceDraft, object]:
    s = get_settings()
    if not configured():
        raise GeminiUnavailable("Gemini no configurado")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=s.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=s.GEMINI_MODEL,
            contents=[
                PROMPT,
                types.Part.from_bytes(data=png, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=InvoiceDraft,
            ),
        )
        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, InvoiceDraft):
            draft = parsed
        else:
            draft = InvoiceDraft.model_validate_json(resp.text)
        if not draft.report:
            draft.report = "Gemini leyó una página."
        return draft, resp
    except GeminiUnavailable:
        raise
    except Exception as exc:
        logger.warning("gemini: %s", exc)
        raise GeminiUnavailable(str(exc)) from exc
