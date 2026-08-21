from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_email(document_id: str, to: str, filename: str, path: str) -> dict:
    s = get_settings()
    payload = {
        "to": to,
        "subject": f"CUADREIQ · {filename}",
        "filename": filename,
        "path": path,
        "document_id": document_id,
    }
    if not s.N8N_WEBHOOK_URL:
        if s.N8N_DRY_RUN:
            logger.info("n8n dry-run email %s → %s", document_id, to)
            return {"ok": True, "dry_run": True}
        raise RuntimeError("n8n no está configurado")
    headers = {}
    if s.N8N_WEBHOOK_SECRET:
        headers[s.N8N_WEBHOOK_HEADER_NAME] = s.N8N_WEBHOOK_SECRET
    r = httpx.post(s.N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=s.N8N_TIMEOUT_SEC)
    if r.status_code >= 400:
        raise RuntimeError(f"n8n {r.status_code}")
    return {"ok": True}
