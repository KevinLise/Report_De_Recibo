from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
_stop = threading.Event()


def start() -> None:
    t = threading.Thread(target=_loop, name="cq-inbox", daemon=True)
    t.start()


def stop() -> None:
    _stop.set()


def _loop() -> None:
    inbox = get_settings().inbox_path
    seen: set[str] = set()
    while not _stop.is_set():
        try:
            for p in inbox.iterdir():
                if not p.is_file() or p.name.startswith("."):
                    continue
                key = str(p.resolve())
                if key in seen:
                    continue
                seen.add(key)
                _ingest(p)
        except Exception as exc:
            logger.warning("inbox: %s", exc)
        _stop.wait(5)


def _ingest(path: Path) -> None:
    from app.core import pipeline

    mime = "application/pdf" if path.suffix.lower() == ".pdf" else "image/jpeg"
    if path.suffix.lower() in {".png", ".webp"}:
        mime = f"image/{path.suffix.lower().lstrip('.')}"
    try:
        data = path.read_bytes()
        pipeline.ingest(path.name, mime, data)
        logger.info("inbox ok %s", path.name)
    except Exception as exc:
        logger.warning("inbox %s: %s", path.name, exc)
