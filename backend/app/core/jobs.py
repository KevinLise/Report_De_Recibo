from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core import store
from app.core.pipeline import sha256_bytes

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_pool: ThreadPoolExecutor | None = None


def _ensure() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        n = max(1, get_settings().MAX_HEAVY_WORKERS)
        _pool = ThreadPoolExecutor(max_workers=n, thread_name_prefix="cq-job")
    return _pool


def get_job(job_id: str) -> dict | None:
    with _lock:
        j = _jobs.get(job_id)
        return dict(j) if j else None


def _set(job_id: str, **kw) -> None:
    with _lock:
        _jobs.setdefault(job_id, {"id": job_id, "status": "queued", "created_at": time.time()})
        _jobs[job_id].update(kw)


def submit(filename: str, mime: str, data: bytes) -> str:
    s = get_settings()
    job_id = uuid.uuid4().hex[:12]
    doc_id = uuid.uuid4().hex[:12]
    sha = sha256_bytes(data)
    suffix = Path(filename).suffix or (".png" if mime.startswith("image/") else ".bin")
    dest = (s.originals_path / doc_id).with_suffix(suffix.lower() if suffix else ".png")
    dest.write_bytes(data)
    store.create_running(doc_id, filename, mime, str(dest), sha)
    _set(
        job_id,
        status="running",
        stage="extract",
        filename=filename,
        document_id=doc_id,
    )
    _ensure().submit(_run, job_id, doc_id, filename, mime, data)
    return job_id


def _run(job_id: str, doc_id: str, filename: str, mime: str, data: bytes) -> None:
    from app.core.pipeline import ingest

    try:
        _set(job_id, status="running", stage="extract", document_id=doc_id)
        doc = ingest(
            filename,
            mime,
            data,
            on_stage=lambda st: _set(job_id, stage=st, status="running", document_id=doc_id),
            force_id=doc_id,
        )
        _set(job_id, status="done", stage=doc.get("stage", "human"), document_id=doc["id"])
    except Exception as exc:
        logger.exception("job %s", job_id)
        store.set_status(doc_id, "error")
        _set(job_id, status="error", error=str(exc)[:400], document_id=doc_id)
