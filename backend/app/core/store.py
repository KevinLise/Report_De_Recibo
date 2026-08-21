from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.domains.invoice import FIELD_LABELS, SCHEMA_KEYS

_local = threading.local()


def _conn() -> sqlite3.Connection:
    c = getattr(_local, "conn", None)
    if c is None:
        path = get_settings().db_path
        c = sqlite3.connect(str(path), check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        _local.conn = c
        init(c)
    return c


def init(c: sqlite3.Connection | None = None) -> None:
    db = c or _conn()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            mime TEXT NOT NULL DEFAULT 'application/pdf',
            path TEXT NOT NULL,
            sha256 TEXT UNIQUE,
            status TEXT NOT NULL,
            stage TEXT NOT NULL,
            source TEXT NOT NULL,
            report TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0,
            tokens_est INTEGER NOT NULL DEFAULT 0,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            tokens_total INTEGER NOT NULL DEFAULT 0,
            gemini_model TEXT NOT NULL DEFAULT '',
            cache_hit INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS fields (
            document_id TEXT NOT NULL,
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0,
            edited INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (document_id, key),
            FOREIGN KEY (document_id) REFERENCES documents(id)
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL,
            description TEXT NOT NULL,
            qty REAL NOT NULL DEFAULT 1,
            unit TEXT,
            net REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        );
        CREATE TABLE IF NOT EXISTS validations (
            document_id TEXT NOT NULL,
            val_id TEXT NOT NULL,
            ok INTEGER NOT NULL,
            formula TEXT NOT NULL,
            message TEXT NOT NULL,
            PRIMARY KEY (document_id, val_id),
            FOREIGN KEY (document_id) REFERENCES documents(id)
        );
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            embedding BLOB
        );
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT,
            kind TEXT NOT NULL,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            at TEXT NOT NULL
        );
        """
    )
    db.commit()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_by_hash(sha256: str) -> dict | None:
    row = _conn().execute("SELECT id FROM documents WHERE sha256=?", (sha256,)).fetchone()
    return get_document(row["id"]) if row else None


def get_document(doc_id: str) -> dict | None:
    db = _conn()
    row = db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return None
    fields = [
        dict(r)
        for r in db.execute(
            "SELECT key, label, value, confidence, edited FROM fields WHERE document_id=?",
            (doc_id,),
        )
    ]
    for f in fields:
        f["edited"] = bool(f["edited"])
    by_key = {f["key"]: f for f in fields}
    ordered = []
    for k in SCHEMA_KEYS:
        ordered.append(
            by_key.get(
                k,
                {
                    "key": k,
                    "label": FIELD_LABELS[k],
                    "value": "",
                    "confidence": 0,
                    "edited": False,
                },
            )
        )
    extras = [f for f in fields if f["key"] not in SCHEMA_KEYS]
    items = [
        {
            "description": r["description"],
            "qty": r["qty"],
            "unit": r["unit"],
            "net": r["net"],
        }
        for r in db.execute(
            "SELECT description, qty, unit, net FROM items WHERE document_id=? ORDER BY id",
            (doc_id,),
        )
    ]
    validations = [
        {
            "id": r["val_id"],
            "ok": bool(r["ok"]),
            "formula": r["formula"],
            "message": r["message"],
        }
        for r in db.execute(
            "SELECT val_id, ok, formula, message FROM validations WHERE document_id=?",
            (doc_id,),
        )
    ]
    d = dict(row)
    return {
        "id": d["id"],
        "filename": d["filename"],
        "mime": d["mime"],
        "file_url": f"/api/documents/{d['id']}/file",
        "status": d["status"],
        "stage": d["stage"],
        "source": d["source"],
        "report": d["report"],
        "confidence": d["confidence"],
        "fields": ordered + extras,
        "items": items,
        "validations": validations,
        "usage": {
            "tokens_est": d["tokens_est"],
            "tokens_in": d["tokens_in"],
            "tokens_out": d["tokens_out"],
            "tokens_total": d["tokens_total"],
            "model": d["gemini_model"],
            "cache_hit": bool(d["cache_hit"]),
        },
        "path": d["path"],
        "sha256": d["sha256"],
        "created_at": d["created_at"],
    }


def create_running(
    doc_id: str,
    filename: str,
    mime: str,
    path: str,
    sha256: str,
) -> dict:
    from app.domains.invoice import FIELD_LABELS, SCHEMA_KEYS

    fields = [
        {
            "key": k,
            "label": FIELD_LABELS[k],
            "value": "",
            "confidence": 0,
            "edited": False,
        }
        for k in SCHEMA_KEYS
    ]
    return save_document(
        {
            "id": doc_id,
            "filename": filename,
            "mime": mime,
            "path": path,
            "sha256": sha256,
            "status": "running",
            "stage": "extract",
            "source": "rapidocr",
            "report": "Leyendo la imagen…",
            "confidence": 0,
            "fields": fields,
            "items": [],
            "validations": [],
            "usage": {
                "tokens_est": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0,
                "model": "",
                "cache_hit": False,
            },
        }
    )


def save_document(doc: dict) -> dict:
    db = _conn()
    db.execute(
        """
        INSERT INTO documents (
            id, filename, mime, path, sha256, status, stage, source, report,
            confidence, tokens_est, tokens_in, tokens_out, tokens_total,
            gemini_model, cache_hit, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status, stage=excluded.stage, source=excluded.source,
            report=excluded.report, confidence=excluded.confidence,
            tokens_est=excluded.tokens_est, tokens_in=excluded.tokens_in,
            tokens_out=excluded.tokens_out, tokens_total=excluded.tokens_total,
            gemini_model=excluded.gemini_model, cache_hit=excluded.cache_hit
        """,
        (
            doc["id"],
            doc["filename"],
            doc["mime"],
            doc["path"],
            doc.get("sha256"),
            doc["status"],
            doc["stage"],
            doc["source"],
            doc.get("report", ""),
            doc.get("confidence", 0),
            doc.get("usage", {}).get("tokens_est", 0),
            doc.get("usage", {}).get("tokens_in", 0),
            doc.get("usage", {}).get("tokens_out", 0),
            doc.get("usage", {}).get("tokens_total", 0),
            doc.get("usage", {}).get("model", ""),
            1 if doc.get("usage", {}).get("cache_hit") else 0,
            doc.get("created_at") or now(),
        ),
    )
    db.execute("DELETE FROM fields WHERE document_id=?", (doc["id"],))
    db.execute("DELETE FROM items WHERE document_id=?", (doc["id"],))
    db.execute("DELETE FROM validations WHERE document_id=?", (doc["id"],))
    for f in doc.get("fields", []):
        db.execute(
            "INSERT INTO fields(document_id,key,label,value,confidence,edited) VALUES(?,?,?,?,?,?)",
            (
                doc["id"],
                f["key"],
                f.get("label") or FIELD_LABELS.get(f["key"], f["key"]),
                f.get("value") or "",
                f.get("confidence") or 0,
                1 if f.get("edited") else 0,
            ),
        )
    for it in doc.get("items", []):
        db.execute(
            "INSERT INTO items(document_id,description,qty,unit,net) VALUES(?,?,?,?,?)",
            (doc["id"], it.get("description", ""), it.get("qty", 1), it.get("unit"), it.get("net", 0)),
        )
    for v in doc.get("validations", []):
        db.execute(
            "INSERT INTO validations(document_id,val_id,ok,formula,message) VALUES(?,?,?,?,?)",
            (doc["id"], v["id"], 1 if v.get("ok") else 0, v.get("formula", ""), v.get("message", "")),
        )
    db.commit()
    return get_document(doc["id"])  # type: ignore[return-value]


def list_queue(status: str | None = None) -> list[dict]:
    db = _conn()
    live = ("queued", "running", "needs_review", "error")
    if status:
        rows = db.execute(
            "SELECT * FROM documents WHERE status=? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        q = ",".join("?" * len(live))
        rows = db.execute(
            f"SELECT * FROM documents WHERE status IN ({q}) ORDER BY created_at DESC", live
        ).fetchall()
    out = []
    for r in rows:
        fields = {
            x["key"]: x["value"]
            for x in db.execute("SELECT key,value FROM fields WHERE document_id=?", (r["id"],))
        }
        total_raw = fields.get("total") or ""
        try:
            total = float(str(total_raw).replace(",", ".")) if total_raw else None
        except ValueError:
            total = None
        out.append(
            {
                "id": r["id"],
                "filename": r["filename"],
                "supplier": fields.get("supplier") or r["filename"],
                "number": fields.get("number") or "",
                "total": total,
                "status": r["status"],
                "confidence": r["confidence"],
                "created_at": r["created_at"],
            }
        )
    return out


def set_status(doc_id: str, status: str) -> dict | None:
    db = _conn()
    db.execute("UPDATE documents SET status=? WHERE id=?", (status, doc_id))
    db.commit()
    return get_document(doc_id)


def file_path(doc_id: str) -> Path | None:
    row = _conn().execute("SELECT path FROM documents WHERE id=?", (doc_id,)).fetchone()
    return Path(row["path"]) if row else None


def existing_keys(exclude_id: str | None = None) -> list[tuple[str, str, float]]:
    db = _conn()
    rows = db.execute("SELECT id FROM documents").fetchall()
    out = []
    for r in rows:
        if exclude_id and r["id"] == exclude_id:
            continue
        d = get_document(r["id"])
        if not d:
            continue
        by = {f["key"]: f["value"] for f in d["fields"]}
        try:
            tot = float(str(by.get("total") or "0").replace(",", "."))
        except ValueError:
            tot = 0
        out.append((by.get("nit") or "", by.get("number") or "", tot))
    return out


def add_usage(document_id: str | None, kind: str, tokens_in: int, tokens_out: int) -> None:
    _conn().execute(
        "INSERT INTO usage_events(document_id,kind,tokens_in,tokens_out,at) VALUES(?,?,?,?,?)",
        (document_id, kind, tokens_in, tokens_out, now()),
    )
    _conn().commit()


def usage_today() -> dict:
    db = _conn()
    day = datetime.now(timezone.utc).date().isoformat()
    rows = db.execute(
        "SELECT document_id, tokens_in, tokens_out, at FROM usage_events WHERE kind='gemini' AND at LIKE ?",
        (day + "%",),
    ).fetchall()
    calls = len(rows)
    tin = sum(r["tokens_in"] for r in rows)
    tout = sum(r["tokens_out"] for r in rows)
    last = [
        {"document_id": r["document_id"], "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"]}
        for r in rows[-8:]
    ]
    return {"today": {"calls": calls, "tokens_in": tin, "tokens_out": tout}, "last": last}


def replace_rag(chunks: list[tuple[str, bytes | None]]) -> None:
    db = _conn()
    db.execute("DELETE FROM rag_chunks")
    for text, blob in chunks:
        db.execute("INSERT INTO rag_chunks(text, embedding) VALUES(?,?)", (text, blob))
    db.commit()


def rag_rows() -> list[sqlite3.Row]:
    return list(_conn().execute("SELECT id, text, embedding FROM rag_chunks"))
