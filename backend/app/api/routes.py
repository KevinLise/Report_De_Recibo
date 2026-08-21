from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api.schemas import ChatBody, EmailBody, PatchBody
from app.core import engine, jobs, pipeline, store
from app.core.report_service import send_email
from app.rag import chat as rag_chat

router = APIRouter()


def _err(msg: str, code: int = 400) -> HTTPException:
    return HTTPException(status_code=code, detail=str(msg))


def _sniff_mime(name: str, mime: str, data: bytes) -> str:
    if mime.startswith("image/") or mime == "application/pdf":
        return mime
    n = name.lower()
    if n.endswith(".pdf"):
        return "application/pdf"
    if n.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if n.endswith(".png"):
        return "image/png"
    if n.endswith(".webp"):
        return "image/webp"
    if n.endswith((".tif", ".tiff")):
        return "image/tiff"
    if n.endswith((".heic", ".heif")):
        return "image/heic"
    if data[:4] == b"%PDF":
        return "application/pdf"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return mime


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/engine")
def get_engine():
    return engine.probe()


@router.post("/documents")
def post_documents(files: list[UploadFile] = File(...)):
    if not files:
        raise _err("sin archivo")
    s = get_settings()
    last_doc = None
    last_job = None
    async_needed = False
    for uf in files:
        data = uf.file.read()
        if len(data) > s.max_upload_bytes:
            raise _err("archivo > 40 MB")
        name = uf.filename or "file"
        mime = _sniff_mime(name, uf.content_type or "application/octet-stream", data)
        is_img = mime.startswith("image/") or name.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff")
        )
        if is_img:
            hit = store.get_by_hash(pipeline.sha256_bytes(data))
            if hit and hit["status"] not in ("queued", "running"):
                if hit["status"] in ("approved", "rejected"):
                    store.set_status(hit["id"], "needs_review")
                    hit = store.get_document(hit["id"]) or hit
                last_doc = hit
            else:
                async_needed = True
                last_job = jobs.submit(name, mime, data)
        else:
            try:
                last_doc = pipeline.ingest(name, mime, data)
            except Exception as exc:
                raise _err(str(exc), 500) from exc
    if async_needed and last_job:
        j = jobs.get_job(last_job) or {"id": last_job, "status": "queued"}
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=202, content=j)
    if last_doc:
        return last_doc
    raise _err("upload vacío")


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    j = jobs.get_job(job_id)
    if not j:
        raise _err("job no está", 404)
    return {
        "id": j["id"],
        "status": j["status"],
        "document_id": j.get("document_id"),
        "stage": j.get("stage"),
        "error": j.get("error"),
    }


@router.get("/queue")
def get_queue(status: str | None = None):
    return store.list_queue(status)


@router.get("/documents/{doc_id}")
def get_document(doc_id: str):
    d = store.get_document(doc_id)
    if not d:
        raise _err("documento no está", 404)
    d = dict(d)
    d.pop("path", None)
    d.pop("sha256", None)
    return d


@router.patch("/documents/{doc_id}")
def patch_document(doc_id: str, body: PatchBody):
    try:
        d = pipeline.patch_fields(doc_id, body.fields)
    except KeyError:
        raise _err("documento no está", 404) from None
    d = dict(d)
    d.pop("path", None)
    d.pop("sha256", None)
    return d


@router.post("/documents/{doc_id}/approve")
def approve(doc_id: str):
    d = store.set_status(doc_id, "approved")
    if not d:
        raise _err("documento no está", 404)
    d = dict(d)
    d.pop("path", None)
    d.pop("sha256", None)
    return d


@router.post("/documents/{doc_id}/reject")
def reject(doc_id: str):
    d = store.set_status(doc_id, "rejected")
    if not d:
        raise _err("documento no está", 404)
    d = dict(d)
    d.pop("path", None)
    d.pop("sha256", None)
    return d


@router.get("/documents/{doc_id}/file")
def get_file(doc_id: str):
    path = store.file_path(doc_id)
    if not path or not path.exists():
        raise _err("archivo no está", 404)
    d = store.get_document(doc_id)
    return FileResponse(path, media_type=(d or {}).get("mime") or "application/octet-stream", filename=(d or {}).get("filename"))


@router.get("/usage")
def usage():
    return store.usage_today()


@router.post("/chat")
def chat(body: ChatBody):
    history = [t.model_dump() for t in body.history]
    return rag_chat.ask(body.message, body.document_id, history)


@router.post("/chat/email")
def chat_email(body: EmailBody):
    d = store.get_document(body.document_id)
    if not d:
        raise _err("documento no está", 404)
    if d["status"] not in ("approved", "needs_review"):
        raise _err("solo needs_review o approved")
    try:
        return send_email(d["id"], body.to, d["filename"], d["path"])
    except Exception as exc:
        raise _err(str(exc), 502) from exc


@router.post("/rag/reindex")
def reindex():
    n = rag_chat.reindex()
    return {"chunks": n}
