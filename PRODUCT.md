# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated by brief: Vite 6 + React 19 + TypeScript + react-router hash + CSS tokens (no Tailwind, no Next, no shadcn). Proxy `/api` → FastAPI `:4005`. Puerto UI `:5173`.

## Users

Operador local (una persona) que revisa facturas y comprobantes que ya pasaron por extracción y reglas. Está frente a una cola, no frente a un dashboard. El trabajo es mirar el papel, corregir un campo y aprobar o rechazar.

## Product Purpose

CUADREIQ extrae, valida y deja revisar facturas. La plata la cuadra Python (`validate.py`), no el modelo. Gemini solo propone JSON cuando el PDF digital no cierra. Éxito = un documento cuadra o queda marcado, con tokens de esa petición a la vista, sin mandar a Gemini de nuevo lo que ya se vio.

## Positioning

Instrumento de revisión: cola + papel flotante + inspector. El campo de puntos es el aire, no un adorno de landing. No es FeedbackIQ (un POST /analyze con charts). No es invoice SaaS.

## Operating Context

- Inbox local o drop de PDF/foto sobre el campo.
- PDF digital → PyMuPDF, 0 tokens. Scan/foto → Gemini 1 página @768px. Fallback RapidOCR.
- Chat local (Ollama qwen3.5:0.8b + RAG del manual). Mail vía backend → n8n, no desde el browser.
- Un operador. SQLite. Sin login.

## Capabilities and Constraints

- Una pantalla: `/` y `/doc/:id`. Cero login, settings, analytics.
- API solo `/api` (health, engine, documents, jobs, queue, usage, chat, chat/email).
- Si `/api/health` falla: mocks. Nunca Gemini ni Ollama ni n8n desde el browser.
- Frontend no inventa campos del schema. Extra del backend se lista; faltante = vacío + signal.
- Aprobar no recalcula. Confirma lo que se ve.
- Idioma UI: es. Copy corto del brief (“12 en cola”, “No cuadra”, “Falta NIT”).

## Brand Commitments

- Nombre de trabajo: CUADREIQ. El look no se renombra.
- Autoridad visual: `briefs/estilo-campo-de-puntos.txt`. Ese archivo manda sobre defaults de Impeccable.
- Tokens, tipo, layout y piezas de la sección 3–9 de ese brief. IBM Plex Sans/Mono está anclado ahí (instrumento, no costume tech).
- Prohibido: navbar+sidebar+KPI, particles.js, Inter/Geist/serif cream, bento, KPI cards.
- Pin de sesión (2026-08-20): paneles de cola/inspector en **vidrio** (Stitch atmospheric-glass: blur, borde 1px, radio ~20). Fondo = video aurora + campo de puntos. El botón **asistente** abre una vista composer (`#/asistente`) con wordmark CUADREIQ. El papel sigue opaco.

## Evidence on Hand

- `briefs/estilo-campo-de-puntos.txt` — estructura y look.
- `briefs/backend-cuadreiq.txt` — contrato API cerrado.
- `briefs/knowledge-asistente.txt` — manual del chat.
- Backend aún no existe en este repo. Demos = mocks sintéticos, etiquetados como tal.
- No hay clientes, precios ni benchmarks reales que citar.

## Product Principles

1. El papel es el objeto; la UI no es un marco.
2. Quietud por defecto; onda solo en evento real.
3. Un label = un trabajo. Datos en mono, UI en sentence case.
4. Mocks para diseñar; el contrato `/api` no se inventa.
5. Revisión humana confirma. El modelo no pisa totales.

## Accessibility & Inclusion

Contraste de lectura sobre void. `prefers-reduced-motion`: puntos estáticos, cero ondas. Focus visible. Idioma `es`.
