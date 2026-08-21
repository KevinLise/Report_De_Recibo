from __future__ import annotations

import io
import logging
import re
from pathlib import Path

from app.domains.invoice import InvoiceDraft, LineItemDraft

logger = logging.getLogger(__name__)

NIT_RE = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d)\b")
NUM_RE = re.compile(r"\b((?:FV|FAC|FE|POS|INV)[- ]?\d{3,})\b", re.I)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
LABEL_AMT = re.compile(
    r"(subtotal|iva|impuesto|descuento|total|neto)\s*[:\.]?\s*\$?\s*([\d]{1,3}(?:[.\s]\d{3})+(?:,\d{2})?|\d+[.,]\d{2}|\d{3,})",
    re.I,
)


def _fnum(raw: str) -> float | None:
    s = raw.strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def markdown_from_pdf(data: bytes) -> str:
    try:
        import pymupdf as fitz
        import pymupdf4llm

        doc = fitz.open(stream=data, filetype="pdf")
        return pymupdf4llm.to_markdown(doc) or ""
    except Exception:
        try:
            import pymupdf as fitz

            doc = fitz.open(stream=data, filetype="pdf")
            return "\n".join(p.get_text() for p in doc)
        except Exception as exc:
            logger.warning("pdf text falló: %s", exc)
            return ""


def useful_text(md: str) -> bool:
    if len(md.strip()) < 80:
        return False
    return bool(NIT_RE.search(md) or re.search(r"total", md, re.I))


def extract_fields_heuristic(md: str, filename: str = "") -> InvoiceDraft | None:
    if not md.strip():
        return None
    nit = NIT_RE.search(md)
    num = NUM_RE.search(md)
    dates = DATE_RE.findall(md)
    labeled: dict[str, float] = {}
    for lab, raw in LABEL_AMT.findall(md):
        n = _fnum(raw)
        if n is None:
            continue
        key = lab.lower()
        if key in ("iva", "impuesto"):
            labeled["tax"] = n
        elif key == "neto":
            labeled.setdefault("subtotal", n)
        else:
            labeled[key] = n
    sub = labeled.get("subtotal")
    tax = labeled.get("tax")
    disc = labeled.get("descuento", 0)
    total = labeled.get("total")
    heading = next((ln.strip("# ").strip() for ln in md.splitlines() if ln.strip()), filename)

    items: list[LineItemDraft] = []
    for ln in md.splitlines():
        if re.search(r"subtotal|total|iva|nit|impuesto|descuento", ln, re.I):
            continue
        nums = re.findall(r"\d+", ln)
        if nums and all(n.startswith("20") and len(n) == 4 for n in nums):
            continue
        m = re.search(r"([\d.,]{3,})\s*$", ln)
        desc = re.sub(r"[\d.,\$]+", " ", ln).strip()
        if m and desc and len(desc) > 3:
            n = _fnum(m.group(1))
            if not n or n <= 100 or n >= 1e9:
                continue
            if 1900 <= n <= 2100:
                continue
            if total is not None and n > total:
                continue
            items.append(LineItemDraft(description=desc[:80], qty=1, net=n))

    if not (nit or total or sub):
        return None
    return InvoiceDraft(
        supplier=heading[:80],
        nit=nit.group(1) if nit else "",
        number=num.group(1) if num else "",
        date=dates[0] if dates else "",
        due_date=dates[1] if len(dates) > 1 else (dates[0] if dates else ""),
        subtotal=sub,
        tax=tax,
        discount=disc or 0,
        total=total,
        items=items[:20],
        report="PDF digital. PyMuPDF sacó campos. Las reglas juzgan la plata.",
    )


def render_page_png(data: bytes, mime: str, long_edge: int = 768) -> tuple[bytes, int, int]:
    from PIL import Image, ImageOps

    if mime.startswith("image/") or not mime:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img) or img
        img = img.convert("RGB")
    else:
        import fitz

        doc = fitz.open(stream=data, filetype="pdf")
        page = doc[0]
        rect = page.rect
        zoom = long_edge / max(rect.width, rect.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    w, h = img.size
    scale = long_edge / max(w, h)
    if scale < 1:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img.size[0], img.size[1]
