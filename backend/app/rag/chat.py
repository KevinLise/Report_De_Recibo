from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import get_settings
from app.core import store
from app.core.report_service import send_email
from app.core.tokenizer import from_usage
from app.rag.retrieve import is_greeting, retrieve

logger = logging.getLogger(__name__)

SYSTEM = """Sos el asistente de Cuadre IQ. Español, frases cortas, sin emojis.
La plata la cuadra Python, no vos. No extraés facturas. No cambies montos.
Respondé con el MANUAL y el DOCUMENTO. Si no está ahí, decí que no sabés.
"""

GREETING = (
    "Hola. Soy el asistente de Cuadre IQ. Te ayudo con la cola de facturas, "
    "el inspector, los totales y a mandar el PDF original por correo. ¿Qué necesitas?"
)

_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_HOW = re.compile(r"^\s*(c[oó]mo|qu[eé]\s+es|explic|para\s+qu[eé]|y\s+eso)", re.I)
_SEND = re.compile(
    r"(manda|mánda|env[ií]a|adjunt).{0,48}(correo|e-?mail|\bmail\b|pdf|factura)|"
    r"(correo|e-?mail|\bmail\b).{0,48}(manda|mánda|env[ií]a|adjunt)",
    re.I,
)
_JSON_BLOCK = re.compile(r"\{[^{}]*\"action\"\s*:\s*\"email\"[^{}]*\}", re.I)
_MARKER = re.compile(
    r"\[\[EMAIL\s+to=\"([^\"]+)\"(?:\s+document_id=\"([^\"]+)\")?\s*\]\]",
    re.I,
)


def _doc_blob(doc_id: str | None) -> str:
    if not doc_id:
        return ""
    d = store.get_document(doc_id)
    if not d:
        return ""
    fields = ", ".join(f"{f['key']}={f['value']}" for f in d["fields"] if f.get("value"))
    vals = "; ".join(
        f"{v['id']}={'ok' if v['ok'] else 'falla'}: {v['message']}" for v in d.get("validations") or []
    )
    items = "; ".join(
        f"{it.get('description')} x{it.get('qty')} net={it.get('net')}" for it in (d.get("items") or [])[:8]
    )
    return (
        f"id={d['id']} archivo={d['filename']} estado={d['status']} fuente={d['source']} "
        f"confianza={d.get('confidence')}. Campos: {fields}. Ítems: {items}. "
        f"Validaciones: {vals}. Reporte: {d.get('report') or '—'}"
    )


def _user_blob(message: str, chunks: list[str], doc: str) -> str:
    manual = "\n\n".join(chunks) if chunks else "(vacío: reindexa el RAG)"
    doc_line = doc or "(ninguno abierto)"
    return f"MANUAL:\n{manual}\n\nDOCUMENTO:\n{doc_line}\n\nUSUARIO:\n{message}"


def _gemini_chat(system: str, user: str, history: list[dict]) -> tuple[str, dict]:
    s = get_settings()
    if not (s.GEMINI_ENABLED and s.GEMINI_API_KEY):
        raise RuntimeError("gemini off")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=s.GEMINI_API_KEY)
    contents: list = []
    for turn in history[-8:]:
        role = "user" if turn.get("role") == "user" else "model"
        text = str(turn.get("text") or "").strip()
        if not text:
            continue
        contents.append(types.Content(role=role, parts=[types.Part(text=text[:2000])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user)]))
    resp = client.models.generate_content(
        model=s.GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.4,
            max_output_tokens=700,
        ),
    )
    text = _resp_text(resp)
    if not text:
        raise RuntimeError("gemini empty")
    return text, from_usage(resp)


def _resp_text(resp) -> str:
    text = (getattr(resp, "text", None) or "").strip()
    if text:
        return text
    for cand in getattr(resp, "candidates", None) or []:
        parts = getattr(getattr(cand, "content", None), "parts", None) or []
        joined = "".join(getattr(p, "text", "") or "" for p in parts).strip()
        if joined:
            return joined
    return ""


_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_LABEL = re.compile(r"^\[(?:identidad|producto|ingesta|cola|inspector|aprobar|tokens|correo|limites|atajos|manual)\]\s*", re.I | re.M)


def _clean_model_text(text: str) -> str:
    text = _THINK.sub("", text or "")
    text = _LABEL.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _ollama_chat(system: str, user: str, history: list[dict]) -> tuple[str, int]:
    s = get_settings()
    messages = [{"role": "system", "content": system}]
    for turn in history[-8:]:
        role = turn.get("role")
        text = str(turn.get("text") or "").strip()
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text[:1200]})
    messages.append({"role": "user", "content": user})
    r = httpx.post(
        s.OLLAMA_HOST + "/api/chat",
        json={
            "model": s.OLLAMA_CHAT_MODEL,
            "stream": False,
            "think": False,
            "messages": messages,
            "options": {"temperature": 0.2, "num_predict": 220},
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    raw = data.get("message") or {}
    text = raw.get("content") or data.get("response") or ""
    text = _clean_model_text(text)
    if not text:
        raise RuntimeError("ollama empty")
    tokens = int((data.get("eval_count") or 0) + (data.get("prompt_eval_count") or 0))
    return text, tokens


def _complete(message: str, chunks: list[str], doc: str, history: list[dict]) -> dict:
    grounded = _clean_model_text("\n\n".join(chunks[:2])) if chunks else ""
    # qwen3.5:0.8b inventa. Manual = RAG verbatim. El modelo solo habla del documento abierto.
    if grounded and not doc:
        return {
            "text": grounded,
            "provider": "ollama",
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_local": None,
        }

    user = _user_blob(message, chunks[:2], doc)
    try:
        text, tokens_local = _ollama_chat(SYSTEM, user, history)
        return {
            "text": text,
            "provider": "ollama",
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_local": tokens_local,
        }
    except Exception as exc:
        logger.warning("ollama chat: %s", exc)

    s = get_settings()
    if s.GEMINI_ENABLED and s.GEMINI_API_KEY:
        try:
            text, usage = _gemini_chat(SYSTEM, user, history)
            return {
                "text": text,
                "provider": "gemini",
                "tokens_in": usage.get("tokens_in") or 0,
                "tokens_out": usage.get("tokens_out") or 0,
                "tokens_local": None,
            }
        except Exception as exc:
            logger.warning("gemini chat: %s", exc)

    if grounded:
        text = grounded
    elif doc:
        text = "Soy el asistente de Cuadre IQ.\n\n" + doc
    else:
        text = (
            "Soy el asistente de Cuadre IQ. Preguntá por la cola, el inspector o el correo."
        )
    return {
        "text": text,
        "provider": "local",
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_local": None,
    }


def _wants_mail(message: str) -> bool:
    m = message or ""
    if _HOW.search(m):
        return False
    if _EMAIL.search(m) and re.search(r"correo|e-?mail|\bmail\b|manda|mánda|env[ií]a", m, re.I):
        return True
    return bool(_SEND.search(m))


def _parse_email_payload(text: str, document_id: str | None, fallback_to: str | None) -> dict:
    to = fallback_to
    doc_id = document_id
    marker = _MARKER.search(text or "")
    if marker:
        to = marker.group(1) or to
        doc_id = marker.group(2) or doc_id
    block = _JSON_BLOCK.search(text or "")
    if block:
        try:
            payload = json.loads(block.group(0))
            if payload.get("action") == "email":
                to = payload.get("to") or to
                doc_id = payload.get("document_id") or doc_id
        except json.JSONDecodeError:
            pass
    return {"to": to, "document_id": doc_id}


def _strip_machine(text: str) -> str:
    text = _MARKER.sub("", text or "")
    text = _JSON_BLOCK.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _try_send(document_id: str | None, to: str | None) -> dict:
    if not to:
        return {"ok": False, "reason": "need_to"}
    if not document_id:
        return {"ok": False, "reason": "need_doc"}
    d = store.get_document(document_id)
    if not d:
        return {"ok": False, "reason": "missing"}
    if d["status"] not in ("approved", "needs_review"):
        return {"ok": False, "reason": "status"}
    try:
        result = send_email(d["id"], to, d["filename"], d["path"])
        return {"ok": True, "result": result, "filename": d["filename"]}
    except Exception as exc:
        logger.warning("email: %s", exc)
        return {"ok": False, "reason": "n8n", "error": str(exc)}


def ask(message: str, document_id: str | None, history: list[dict] | None = None) -> dict:
    message = (message or "").strip()
    history = history or []
    if is_greeting(message):
        return {"text": GREETING, "provider": "local", "sent": False, "tokens_local": None}
    chunks = retrieve(message)
    doc = _doc_blob(document_id)
    email_in_msg = _EMAIL.search(message)
    to_hint = email_in_msg.group(0) if email_in_msg else None
    wants = _wants_mail(message)

    if wants and to_hint and document_id:
        sent = _try_send(document_id, to_hint)
        if sent.get("ok"):
            dry = bool((sent.get("result") or {}).get("dry_run"))
            if dry:
                text = (
                    f"Listo. n8n no tiene webhook todavía: el envío de {sent['filename']} "
                    f"a {to_hint} quedó en dry-run. El original ya está en disco."
                )
            else:
                text = f"Listo. Mandé el original de {sent['filename']} a {to_hint}."
            return {
                "text": text,
                "action": "email",
                "document_id": document_id,
                "to": to_hint,
                "sent": True,
                "provider": "local",
            }
        if sent.get("reason") == "status":
            return {
                "text": "Solo mando documentos en revisión o aprobados.",
                "provider": "local",
            }
        if sent.get("reason") == "n8n":
            return {
                "text": f"Quise mandar el original a {to_hint} pero n8n falló: {sent.get('error')}.",
                "provider": "local",
            }
        if sent.get("reason") == "missing":
            return {
                "text": "Ese documento no está. Abrí una factura primero.",
                "provider": "local",
            }

    if wants and not document_id:
        return {
            "text": "Abrí una factura primero. Después te pido el correo.",
            "action": "email",
            "provider": "local",
            "sent": False,
        }
    if wants and not to_hint:
        return {
            "text": "¿A qué correo? Solo documentos en revisión o aprobados. Se adjunta el original.",
            "action": "email",
            "document_id": document_id,
            "provider": "local",
            "sent": False,
        }

    raw = _complete(message, chunks, doc, history)
    text = raw["text"]
    parsed = _parse_email_payload(text, document_id, to_hint)
    text = _strip_machine(text) or text
    sent = False
    action = None
    to = parsed.get("to")
    doc_id = parsed.get("document_id") or document_id

    if wants or parsed.get("to"):
        if not doc_id:
            text = "Abrí una factura primero. Después te pido el correo."
            action = "email"
        elif not to:
            text = "¿A qué correo? Solo documentos en revisión o aprobados. Se adjunta el original."
            action = "email"
        else:
            result = _try_send(doc_id, to)
            if result.get("ok"):
                sent = True
                action = "email"
                dry = bool((result.get("result") or {}).get("dry_run"))
                name = result.get("filename") or doc_id
                if dry:
                    text = (
                        f"Listo. n8n no tiene webhook todavía: el envío de {name} "
                        f"a {to} quedó en dry-run. El original ya está en disco."
                    )
                else:
                    text = f"Listo. Mandé el original de {name} a {to}."
            elif result.get("reason") == "status":
                text = "Solo mando documentos en revisión o aprobados."
            elif result.get("reason") == "n8n":
                text = f"Quise mandar el original a {to} pero n8n falló: {result.get('error')}."

    if is_greeting(message) and "cuadre" not in text.lower():
        text = GREETING

    tin = int(raw.get("tokens_in") or 0)
    tout = int(raw.get("tokens_out") or 0)
    local = raw.get("tokens_local")
    if tin or tout:
        store.add_usage(document_id, "chat", tin, tout)
    elif local:
        store.add_usage(document_id, "chat", 0, int(local))

    out: dict = {
        "text": text,
        "provider": raw.get("provider"),
        "tokens_local": local,
        "sent": sent,
    }
    if tin or tout:
        out["tokens_in"] = tin
        out["tokens_out"] = tout
    if action:
        out["action"] = action
        out["document_id"] = doc_id
        if to:
            out["to"] = to
    return out


def reindex() -> int:
    from app.rag.chunker import chunk_corpus
    from app.rag.embed import embed, pack

    parts = chunk_corpus()
    vecs = embed(parts, timeout=60) if parts else []
    store.replace_rag([(p, pack(v) if v else None) for p, v in zip(parts, vecs, strict=False)])
    return len(parts)
