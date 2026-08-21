from __future__ import annotations

import io
import logging
import threading
import time

import numpy as np
from PIL import Image

from app.core.pdf_digital import extract_fields_heuristic
from app.domains.invoice import InvoiceDraft

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_engine = None


def available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return True
    except Exception:
        return False


def _engine_get():
    global _engine
    if _engine is not None:
        return _engine
    with _lock:
        if _engine is not None:
            return _engine
        from rapidocr_onnxruntime import RapidOCR

        t0 = time.perf_counter()
        _engine = RapidOCR()
        logger.info("rapidocr loaded in %.2fs", time.perf_counter() - t0)
        return _engine


def warmup() -> None:
    if not available():
        return
    try:
        _engine_get()
    except Exception as exc:
        logger.warning("rapidocr warmup: %s", exc)


def _to_array(png: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    return np.asarray(img)


def extract(png: bytes) -> InvoiceDraft:
    try:
        eng = _engine_get()
        arr = _to_array(png)
        t0 = time.perf_counter()
        result, _elapse = eng(arr)
        logger.info("rapidocr infer %.2fs lines=%s", time.perf_counter() - t0, 0 if not result else len(result))
        lines: list[str] = []
        if result:
            for row in result:
                if len(row) >= 2:
                    lines.append(str(row[1]))
        md = "\n".join(lines)
        draft = extract_fields_heuristic(md, "ocr") or InvoiceDraft(
            report="RapidOCR. Tabla vacía o incompleta."
        )
        draft.report = "RapidOCR local. Queda para revisión humana."
        if not draft.supplier and lines:
            draft.supplier = lines[0][:80]
        return draft
    except Exception as exc:
        logger.warning("rapidocr: %s", exc)
        return InvoiceDraft(report=f"RapidOCR falló: {exc}")
