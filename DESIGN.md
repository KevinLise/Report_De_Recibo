---
name: CUADREIQ
description: Instrumento de revisión. La factura es el objeto; el campo es el aire.
colors:
  void: "#0B0C10"
  void-2: "#12141A"
  ink: "#D8D6D0"
  ink-dim: "#8B8A84"
  rule: "#2A2C33"
  phosphor: "#C9D0C4"
  signal: "#C4A574"
  fault: "#C45C4A"
  pass: "#7A8F72"
  paper: "#E7E2D6"
  paper-ink: "#1C1B18"
typography:
  ui:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  data:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  total:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "18px"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "normal"
rounded:
  none: "0"
  hair: "2px"
spacing:
  field: "8px"
  group: "18px"
  section: "22px"
components:
  act:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dim}"
    rounded: "{rounded.none}"
    padding: "6px 2px 4px"
  act-hover-pass:
    backgroundColor: "transparent"
    textColor: "{colors.pass}"
  act-hover-fault:
    backgroundColor: "transparent"
    textColor: "{colors.fault}"
  input-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 0 2px"
  queue-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dim}"
    rounded: "{rounded.none}"
    padding: "11px 6px"
  queue-item-active:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
---

# Design System: CUADREIQ

Canónica: `briefs/estilo-campo-de-puntos.txt`. Este archivo describe lo **construido**, no un look paralelo.

## Overview

**Creative North Star: "La factura es el objeto. El campo es el aire."**

CUADREIQ es un instrumento de revisión, no un dashboard. El operador mira un papel que flota sobre un campo de puntos casi invisibles. La UI no enmarca: cola a la izquierda, inspector a la derecha, acciones abajo. Quietud por defecto. Una onda en el campo solo cuando pasa algo real (archivo, etapa, validación, revisión).

Rechazos confirmados por el brief y por el código: navbar + sidebar + KPI, video de fondo, particles.js, Inter/Geist/serif cream, glow, glass, bento, radius 16, cards.

**Key Characteristics:**
- Void casi negro; el único objeto claro es el papel `#E7E2D6`.
- IBM Plex Sans para UI, IBM Plex Mono para datos. Peso 400; total 500. Nunca 700.
- Separación por espacio y una línea `--rule`, no por cajas.
- Sentence case. Copy corto en español.

## Colors

Paleta Restrained: neutros de void/ink + semántica puntual (signal, fault, pass).

### Primary
- **Phosphor** (`#C9D0C4`): foco visible y etapa hecha. No es CTA de marketing.

### Neutral
- **Void** (`#0B0C10`): fondo de la página y del canvas.
- **Void-2** (`#12141A`): velo 94% sobre cola e inspector, para que los puntos no peleen con el texto.
- **Ink** (`#D8D6D0`): texto activo y puntos (al 6–12%).
- **Ink-dim** (`#8B8A84`): resto de la cola, labels, usage.
- **Rule** (`#2A2C33`): rayas de campo, borde del dock.
- **Paper** (`#E7E2D6`) / **Paper-ink** (`#1C1B18`): el documento.

### Named Rules
**The Signal Is the Value Rule.** Baja confianza pinta el número en `#C4A574`. Fallo de fórmula pinta el número en `#C45C4A`. Cero badges, cero pills.

**The Paper Object Rule.** El PDF/foto es un rectángulo de papel. Sin card, sin sombra suave, sin radius 16.

## Typography

**Display Font:** no hay display. El total es Plex Mono 18/500.
**Body Font:** IBM Plex Sans 13–15 / 400.
**Label/Mono Font:** IBM Plex Mono 12, `tabular-nums`.

**Character:** misma familia Sans+Mono, instrumento, no costume tech.

### Hierarchy
- **Brand/orientación** (13, ink-dim): “CUADREIQ”, “4 en cola”.
- **Body** (14–15, ink): reporte, chat, acciones.
- **Label** (13, ink-dim): claves del inspector.
- **Data** (12–13, Mono): NIT, fechas, montos, usage `812 in · 146 out`.
- **Total** (18, Mono 500): el número que se confirma.

### Named Rules
**The Sentence Case Rule.** Nada de eyebrow ALL CAPS de landing. Un label = un trabajo.

## Layout

Desktop: grid `180 / 1fr / 312`, alto `100dvh`. Cola film, papel centrado A4 (`aspect-ratio 1 / 1.414`), inspector con velo, fila de acciones.

`< 960px`: papel `46vh` arriba, inspector debajo (alto auto), chat en flujo, acciones, cola en sheet inferior. Sin hamburger.

 Ritmo: 8px dentro de un campo, 18–22px entre grupos. Más aire arriba de un bloque que debajo.

## Elevation & Depth

Tres capas: video aurora (fondo), campo de puntos, vidrio flotante. Cola e inspector no son losas opacas: `backdrop-filter: blur(28px)`, `background: rgba(255,255,255,0.07)`, borde `1px rgba(255,255,255,0.16)`, radio 20px, sombra `0 8px 32px` + shine interior. El papel sigue opaco `#E7E2D6`. Composer del asistente: blur 36px, radio 24px (Stitch).

### Named Rules
**The Event Wave Rule.** Ondas 0.5–1 px, 1.4–2.6 s, `cubic-bezier(0.16, 1, 0.3, 1)`, máximo 1–2. `prefers-reduced-motion`: puntos estáticos, video parado (poster).
**The Glass Lens Rule.** Cola, inspector y composer dejan ver el campo. El papel no.

## Shapes

Radio 0, o 2px. Marca de `needs_review`: cuadrado 4×4 `--signal`, no pastilla. Inputs: línea inferior, fondo transparente.

## Components

### Buttons
- **Shape:** sin relleno. Línea inferior `--rule`.
- **Primary (aprobar):** hover `--pass`.
- **Reject:** hover `--fault`.
- **Focus:** `outline 1px phosphor`, offset 3.

### Inputs / Fields
- Grid `92px | 1fr`. Label dim, valor ink/mono.
- Focus: la línea pasa a phosphor.
- Signal / fault: el valor cambia de color, no el chrome.

### Navigation
No hay nav. La cola es un film: activo ink 500, resto ink-dim.

### Signature: Campo de puntos
Canvas 2D fijo, `pointer-events: none`. Puntos 1.0–1.6 px, densidad baja, distribución irregular. No particles.js. No grid CSS.

### Signature: Papel
Hoja `#E7E2D6`. `pdfjs` o `<img>`. Carga = hoja vacía + etapa en mono 12.

### Signature: ChatDock
Esquina, void-2, sin burbuja iOS. Cerrado: chip “asistente”. Abierto: log ink/ink-dim + input línea. Si Ollama no está: “asistente apagado”.

## Do's and Don'ts

### Do:
- **Do** dejar que el papel sea el único objeto claro.
- **Do** escribir copy como el brief: “12 en cola”, “No cuadra”, “Falta NIT”.
- **Do** caer a `mocks/` si `/api/health` no responde.

### Don't:
- **Don't** meter navbar, sidebar, KPI cards, charts ni “dashboard para después”.
- **Don't** usar Inter, Geist, Space Grotesk, Instrument Serif, glow, glass, ni video de fondo.
- **Don't** llamar a Gemini, Ollama o n8n desde el browser.
