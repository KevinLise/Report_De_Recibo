from pathlib import Path

from app.config import get_settings
from app.core import store
from app.core.pipeline import ingest


ROOT = Path(__file__).resolve().parents[2]


def _db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_ENABLED", "false")
    get_settings.cache_clear()
    store._local.conn = None
    store.init()


def test_digital_pdf_zero_tokens(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    data = (ROOT / "samples" / "norte.pdf").read_bytes()
    d = ingest("norte.pdf", "application/pdf", data)
    assert d["source"] == "pymupdf"
    assert d["usage"]["tokens_in"] == 0
    assert d["usage"]["tokens_out"] == 0
    by = {f["key"]: f["value"] for f in d["fields"]}
    assert by.get("total")
    store._local.conn = None
    get_settings.cache_clear()


def test_png_uses_rapidocr_not_gemini(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (420, 220), "white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    d = ingest("blank.png", "image/png", buf.getvalue())
    assert d["source"] == "rapidocr"
    assert d["usage"]["tokens_in"] == 0
    assert d["status"] == "needs_review"
    store._local.conn = None
    get_settings.cache_clear()
