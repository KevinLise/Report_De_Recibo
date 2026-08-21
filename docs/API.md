# CUADREIQ API

Base: `http://127.0.0.1:4005/api`

Errores: `{ "detail": "string" }`

| método | ruta | nota |
|---|---|---|
| GET | /health | `{ok:true}` |
| GET | /engine | pymupdf4llm, rapidocr, gemini, ollama, inbox, db |
| POST | /documents | multipart `files`. 200 documento o 202 job |
| GET | /jobs/{id} | queued\|running\|done\|error |
| GET | /queue | `?status=` |
| GET | /documents/{id} | fields, items, validations, usage |
| PATCH | /documents/{id} | `{fields:{nit:"..."}}` |
| POST | /documents/{id}/approve | |
| POST | /documents/{id}/reject | |
| GET | /documents/{id}/file | original |
| GET | /usage | today + last |
| POST | /chat | `{message, document_id?, history?:[{role,text}]}`. Gemini primero, Ollama si falla. `{text, provider, action?, to?, sent?}` |
| POST | /chat/email | `{document_id, to}` |
| POST | /rag/reindex | |

Puerto 4005. CORS `localhost:5173`.
