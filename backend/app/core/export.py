"""Export mínimo: JSON del documento. Sin PDF 'arreglado'."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.core import store


def dump_json(doc_id: str) -> Path:
    doc = store.get_document(doc_id)
    if not doc:
        raise KeyError(doc_id)
    path = get_settings().data_path / f"{doc_id}.json"
    slim = {k: doc[k] for k in doc if k != "path"}
    path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
