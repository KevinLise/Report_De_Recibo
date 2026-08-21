from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Callable
from pathlib import Path

from app.config import get_settings
from app.core import confidence, gemini, ocr, store, tokenizer
from app.core.gemini import GeminiUnavailable
from app.core.pdf_digital import (
    extract_fields_heuristic,
    markdown_from_pdf,
    render_page_png,
    useful_text,
)
from app.core.validate import run as validate_run
from app.domains.invoice import InvoiceDraft, LineItemDraft

logger = logging.getLogger(__name__)
StageCb = Callable[[str], None] | None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _items(draft: InvoiceDraft) -> list[dict]:
    return [
        {"description": i.description, "qty": i.qty, "unit": i.unit, "net": i.net}
        for i in draft.items
    ]


def _pack(
    *,
    doc_id: str,
    filename: str,
    mime: str,
    path: str,
    sha: str,
    draft: InvoiceDraft,
    source: str,
    usage: dict,
    status: str,
    stage: str,
    field_conf: dict[str, float] | None = None,
) -> dict:
    vals = validate_run(draft, existing=store.existing_keys(exclude_id=doc_id))
    fields = confidence.field_map(draft, base=0.9 if source == "pymupdf" else 0.7)
    if field_conf:
        for f in fields:
            if f["key"] in field_conf:
                f["confidence"] = field_conf[f["key"]]
    conf = confidence.score(draft, vals, {f["key"]: f["confidence"] for f in fields})
    settings = get_settings()
    if source == "pymupdf" and all(v["ok"] for v in vals) and settings.AUTO_APPROVE_DIGITAL:
        status = "approved"
    return {
        "id": doc_id,
        "filename": filename,
        "mime": mime,
        "path": path,
        "sha256": sha,
        "status": status,
        "stage": stage,
        "source": source,
        "report": draft.report,
        "confidence": conf,
        "fields": fields,
        "items": _items(draft),
        "validations": vals,
        "usage": usage,
        "created_at": store.now(),
    }


def ingest(
    filename: str,
    mime: str,
    data: bytes,
    *,
    on_stage: StageCb = None,
    force_id: str | None = None,
) -> dict:
    settings = get_settings()
    sha = sha256_bytes(data)
    hit = store.get_by_hash(sha)
    if hit and hit["id"] != (force_id or "") and hit["status"] not in ("queued", "running"):
        if hit["status"] in ("approved", "rejected"):
            store.set_status(hit["id"], "needs_review")
            hit = store.get_document(hit["id"]) or hit
        hit["usage"] = {**(hit.get("usage") or {}), "cache_hit": True}
        return hit

    doc_id = force_id or uuid.uuid4().hex[:12]
    dest = settings.originals_path / doc_id
    suffix = Path(filename).suffix or (".png" if mime.startswith("image/") else ".pdf")
    dest = dest.with_suffix(suffix.lower() if suffix else ".png")
    if not dest.exists():
        dest.write_bytes(data)

    on_stage = on_stage or (lambda _s: None)
    on_stage("extract")

    draft: InvoiceDraft | None = None
    source = "pymupdf"
    usage = {
        "tokens_est": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
        "model": "",
        "cache_hit": False,
    }
    is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf")

    if is_pdf:
        md = markdown_from_pdf(data)
        if useful_text(md):
            draft = extract_fields_heuristic(md, filename)
            if draft and (draft.nit or draft.total is not None):
                on_stage("rules")
                packed = _pack(
                    doc_id=doc_id,
                    filename=filename,
                    mime=mime or "application/pdf",
                    path=str(dest),
                    sha=sha,
                    draft=draft,
                    source="pymupdf",
                    usage=usage,
                    status="needs_review",
                    stage="human",
                )
                return store.save_document(packed)

    png, w, h = render_page_png(
        data,
        mime if mime else ("image/jpeg" if not is_pdf else "application/pdf"),
        settings.GEMINI_LONG_EDGE_PX,
    )
    usage["tokens_est"] = tokenizer.estimate_image_tokens(w, h)
    use_gemini = bool(settings.GEMINI_ENABLED and settings.GEMINI_API_KEY and gemini.configured())
    if use_gemini:
        on_stage("gemini")
        try:
            usage["tokens_in"] = tokenizer.count_gemini(gemini.PROMPT, png)
            draft, resp = gemini.extract(png)
            used = tokenizer.from_usage(resp)
            usage.update(used)
            usage["model"] = settings.GEMINI_MODEL
            source = "gemini"
            store.add_usage(doc_id, "gemini", usage["tokens_in"], usage["tokens_out"])
        except GeminiUnavailable as exc:
            logger.info("gemini skip, rapidocr: %s", exc)
            use_gemini = False
    if not use_gemini or draft is None:
        on_stage("gemini")
        draft = ocr.extract(png)
        source = "rapidocr"
        usage = {
            "tokens_est": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "model": "",
            "cache_hit": False,
        }

    on_stage("rules")
    assert draft is not None
    packed = _pack(
        doc_id=doc_id,
        filename=filename,
        mime=mime or ("application/pdf" if is_pdf else "image/jpeg"),
        path=str(dest),
        sha=sha,
        draft=draft,
        source=source,
        usage=usage,
        status="needs_review",
        stage="human",
    )
    return store.save_document(packed)


def patch_fields(doc_id: str, fields: dict[str, str]) -> dict:
    doc = store.get_document(doc_id)
    if not doc:
        raise KeyError(doc_id)
    by = {f["key"]: f for f in doc["fields"]}
    from app.domains.invoice import FIELD_LABELS

    for k, v in fields.items():
        if k in by:
            by[k]["value"] = v
            by[k]["edited"] = True
        else:
            doc["fields"].append(
                {
                    "key": k,
                    "label": FIELD_LABELS.get(k, k),
                    "value": v,
                    "confidence": 1,
                    "edited": True,
                }
            )
    items = [
        LineItemDraft(description=i["description"], qty=i["qty"], unit=i.get("unit"), net=i["net"])
        for i in doc["items"]
    ]
    from app.core.validate import draft_from_fields

    draft = draft_from_fields({f["key"]: f["value"] for f in doc["fields"]}, items)
    doc["validations"] = validate_run(draft, existing=store.existing_keys(exclude_id=doc_id))
    doc["fields"] = list(by.values()) if False else doc["fields"]
    # keep schema order via save/get
    return store.save_document(
        {
            **doc,
            "fields": doc["fields"],
            "validations": doc["validations"],
            "usage": doc["usage"],
            "path": doc["path"],
            "sha256": doc.get("sha256"),
        }
    )
