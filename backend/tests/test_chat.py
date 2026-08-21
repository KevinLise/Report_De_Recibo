from app.config import get_settings
from app.core import store
from app.rag import chat as rag_chat
from app.rag.chunker import chunk, chunk_corpus, load_corpus
from app.rag.retrieve import is_greeting, retrieve


def test_greeting_detect():
    assert is_greeting("hola")
    assert is_greeting("Hola!")
    assert is_greeting("buenos días")
    assert not is_greeting("hola, manda la factura a a@b.com")
    assert not is_greeting("cómo entra un pdf")


def test_corpus_and_chunks():
    docs = load_corpus()
    names = {n for n, _ in docs}
    assert "01_identidad" in names
    assert "08_correo" in names
    parts = chunk_corpus(docs)
    assert len(parts) >= 8
    assert any("[identidad]" in p and "asistente de Cuadre IQ" in p for p in parts)
    assert any("[correo]" in p and "n8n" in p for p in parts)
    bits = chunk("uno\n\ndos\n\n" + ("x" * 40), size=30, overlap=4)
    assert len(bits) >= 2


def test_reindex_keyword_retrieve(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    store._local.conn = None
    store.init()
    monkeypatch.setattr(
        "app.rag.embed.embed",
        lambda texts, timeout=None: [None] * len(texts),
    )
    monkeypatch.setattr(
        "app.rag.retrieve.embed",
        lambda texts, timeout=None: [None] * len(texts),
    )
    n = rag_chat.reindex()
    assert n >= 8
    hits = retrieve("hola")
    assert hits
    assert any("asistente" in h.lower() for h in hits)
    mail = retrieve("cómo mando el pdf por correo")
    assert any("n8n" in h.lower() or "correo" in h.lower() for h in mail)
    store._local.conn = None
    get_settings.cache_clear()


def test_manual_question_uses_rag_not_hallucination(monkeypatch):
    monkeypatch.setattr(
        rag_chat,
        "retrieve",
        lambda _q: ["[ingesta]\nArrastra el PDF. Límite: 40 MB. RapidOCR local."],
    )
    monkeypatch.setattr(rag_chat, "_ollama_chat", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no llm")))
    out = rag_chat.ask("cómo entra un pdf", None)
    assert "40 MB" in out["text"]
    assert "RapidOCR" in out["text"]
    assert "no hay límite" not in out["text"].lower()


def test_hola_is_local_identity(monkeypatch):
    monkeypatch.setattr(rag_chat, "_ollama_chat", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no llm")))
    monkeypatch.setattr(rag_chat, "_gemini_chat", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no gemini")))
    out = rag_chat.ask("hola", None, [])
    assert out["provider"] == "local"
    assert "asistente de Cuadre IQ" in out["text"]


def test_hola_falls_back_to_local(monkeypatch):
    monkeypatch.setattr(rag_chat, "retrieve", lambda _q: [])
    monkeypatch.setattr(rag_chat, "_gemini_chat", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("gemini down")))
    monkeypatch.setattr(rag_chat, "_ollama_chat", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("ollama down")))
    monkeypatch.setattr(rag_chat.store, "add_usage", lambda *a, **k: None)
    out = rag_chat.ask("hola", None)
    assert out["provider"] == "local"
    assert "asistente de Cuadre IQ" in out["text"]


def test_email_sends_without_llm(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    store._local.conn = None
    store.init()
    store.save_document(
        {
            "id": "doc-1",
            "filename": "fv.pdf",
            "mime": "application/pdf",
            "path": str(tmp_path / "fv.pdf"),
            "sha256": "x",
            "status": "needs_review",
            "stage": "human",
            "source": "pymupdf",
            "report": "ok",
            "confidence": 0.9,
            "fields": [],
            "items": [],
            "validations": [],
            "usage": {},
        }
    )
    sent = {}

    def fake_send(document_id, to, filename, path):
        sent.update(document_id=document_id, to=to, filename=filename, path=path)
        return {"ok": True, "dry_run": True}

    monkeypatch.setattr(rag_chat, "send_email", fake_send)
    monkeypatch.setattr(rag_chat, "_complete", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no llm")))
    out = rag_chat.ask("manda esta factura a ana@acme.co", "doc-1")
    assert out["sent"] is True
    assert out["to"] == "ana@acme.co"
    assert sent["to"] == "ana@acme.co"
    assert "dry-run" in out["text"]
    store._local.conn = None
    get_settings.cache_clear()


def test_email_needs_document(monkeypatch):
    monkeypatch.setattr(rag_chat, "retrieve", lambda _q: ["[correo]\nn8n"])
    monkeypatch.setattr(rag_chat, "_complete", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no llm")))
    monkeypatch.setattr(rag_chat.store, "add_usage", lambda *a, **k: None)
    out = rag_chat.ask("manda esta factura por correo", None)
    assert "factura" in out["text"].lower()
    assert not out.get("sent")
    assert not rag_chat._wants_mail("cómo mando el pdf por correo")


def test_email_asks_for_address(monkeypatch):
    monkeypatch.setattr(rag_chat, "retrieve", lambda _q: ["[correo]\nn8n adjunta el original"])
    monkeypatch.setattr(
        rag_chat,
        "_complete",
        lambda *_a, **_k: {
            "text": "¿A qué correo?",
            "provider": "gemini",
            "tokens_in": 1,
            "tokens_out": 1,
            "tokens_local": None,
        },
    )
    monkeypatch.setattr(rag_chat.store, "add_usage", lambda *a, **k: None)
    out = rag_chat.ask("manda esta factura por correo", "doc-1")
    assert "correo" in out["text"].lower()
    assert not out.get("sent")
