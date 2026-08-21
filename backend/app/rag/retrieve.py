from __future__ import annotations

import math
import re

from app.config import get_settings
from app.core import store
from app.rag.embed import embed, unpack

_WORD = re.compile(r"[a-záéíóúñü0-9]{3,}", re.I)
_GREET = re.compile(
    r"^\s*(hola|hey|hi|hello|buenas|buenos\s+d[ií]as|buenas\s+tardes|"
    r"buenas\s+noches|qu[eé]\s+tal|saludos)[\s!?.¡¿]*$",
    re.I,
)


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1
    nb = math.sqrt(sum(y * y for y in b)) or 1
    return dot / (na * nb)


def _tokens(text: str) -> set[str]:
    return {w.group(0).lower() for w in _WORD.finditer(text)}


def _kw_score(query: str, text: str) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    t = _tokens(text)
    hit = len(q & t)
    return hit / math.sqrt(len(t) or 1)


def is_greeting(message: str) -> bool:
    return bool(_GREET.match(message or ""))


_HINTS = {
    "ingesta": ("entra", "subir", "arrastr", "inbox", "pdf", "foto", "archivo", "ocr", "pymupdf", "scan"),
    "correo": ("correo", "email", "mail", "n8n"),
    "aprobar": ("aprob", "rechaz", "atajo"),
    "inspector": ("inspector", "campo", "nit", "iva", "formula", "cuadra"),
    "cola": ("cola", "queue", "needs_review"),
    "tokens": ("token", "gemini", "gasto"),
    "identidad": ("quien", "sos", "asistente"),
    "limites": ("no hace", "no extra", "limite"),
}


def _label_boost(query: str, text: str) -> float:
    q = query.lower()
    head = text[:80].lower()
    boost = 0.0
    for label, words in _HINTS.items():
        if f"[{label}]" in head and any(w in q for w in words):
            boost += 0.8
    return boost


def retrieve(query: str) -> list[str]:
    s = get_settings()
    rows = store.rag_rows()
    if not rows:
        return []
    if is_greeting(query):
        ident = [r["text"] for r in rows if "[identidad]" in r["text"] or "[producto]" in r["text"]]
        if ident:
            return ident[: s.RAG_TOP_K]

    scored: list[tuple[float, str]] = []
    has_vec = any(r["embedding"] for r in rows)
    qv = embed([query], timeout=2.5)[0] if has_vec else None
    for r in rows:
        text = r["text"]
        kw = _kw_score(query, text)
        vec_score = 0.0
        if qv:
            vec = unpack(r["embedding"])
            if vec:
                vec_score = _cos(qv, vec)
        label_boost = _label_boost(query, text)
        scored.append((vec_score * 0.5 + kw * 0.3 + label_boost, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = [t for score, t in scored if score > 0][: s.RAG_TOP_K]
    if out:
        return out
    return [r["text"] for r in rows[: s.RAG_TOP_K]]
