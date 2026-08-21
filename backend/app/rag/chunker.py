from __future__ import annotations

import re
from pathlib import Path

from app.config import get_settings

_SPLIT = re.compile(r"\n{2,}")


def knowledge_dir() -> Path:
    return Path(__file__).resolve().parent / "knowledge"


def load_corpus() -> list[tuple[str, str]]:
    folder = knowledge_dir()
    files = sorted(folder.glob("*.txt")) if folder.is_dir() else []
    out: list[tuple[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8").strip()
        if text:
            out.append((path.stem, text))
    if not out:
        legacy = Path(__file__).resolve().parent / "knowledge.txt"
        if legacy.exists():
            out.append(("manual", legacy.read_text(encoding="utf-8")))
    return out


def chunk(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    s = get_settings()
    size = size if size is not None else s.RAG_CHUNK
    overlap = overlap if overlap is not None else s.RAG_OVERLAP
    text = text.strip()
    if not text:
        return []
    paras = [p.strip() for p in _SPLIT.split(text) if p.strip()]
    if not paras:
        paras = [text]
    out: list[str] = []
    buf = ""
    for para in paras:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= size:
            buf = candidate
            continue
        if buf:
            out.append(buf)
        if len(para) <= size:
            buf = para
            continue
        out.extend(_window(para, size, overlap))
        buf = ""
    if buf:
        out.append(buf)
    return out


def chunk_corpus(docs: list[tuple[str, str]] | None = None) -> list[str]:
    docs = docs if docs is not None else load_corpus()
    parts: list[str] = []
    for name, body in docs:
        label = name.split("_", 1)[-1]
        for piece in chunk(body):
            parts.append(f"[{label}]\n{piece}")
    return parts


def _window(text: str, size: int, overlap: int) -> list[str]:
    out: list[str] = []
    i = 0
    step = max(1, size - overlap)
    while i < len(text):
        out.append(text[i : i + size].strip())
        i += step
    return [p for p in out if p]
