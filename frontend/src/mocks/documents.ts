import type { Document } from "../api/types";

export const MOCK_DOCUMENTS: Record<string, Document> = {
  "doc-andina": {
    id: "doc-andina",
    filename: "FV-10482-andina.pdf",
    mime: "application/pdf",
    file_url: "/mocks/andina.svg",
    status: "needs_review",
    stage: "human",
    source: "gemini",
    confidence: 0.64,
    report:
      "Gemini leyó una página. El IVA no cierra con el 19 % sobre el gravable y el total está redondeado a ojo. Corregí iva o total; no inventes el gravable.",
    fields: [
      { key: "supplier", label: "proveedor", value: "Comercial Andina S.A.S.", confidence: 0.92, edited: false },
      { key: "nit", label: "NIT", value: "900.123.456-8", confidence: 0.58, edited: false },
      { key: "number", label: "número", value: "FV-10482", confidence: 0.88, edited: false },
      { key: "date", label: "fecha", value: "2026-08-12", confidence: 0.9, edited: false },
      { key: "due_date", label: "vence", value: "2026-09-11", confidence: 0.86, edited: false },
      { key: "subtotal", label: "subtotal", value: "4050000", confidence: 0.84, edited: false },
      { key: "tax", label: "iva", value: "770000", confidence: 0.61, edited: false },
      { key: "discount", label: "descuento", value: "0", confidence: 0.8, edited: false },
      { key: "total", label: "total", value: "4820000", confidence: 0.7, edited: false },
    ],
    items: [
      { description: "Resma carta 80 g", qty: 10, unit: "und", net: 1200000 },
      { description: "Toner 85A", qty: 4, unit: "und", net: 2400000 },
      { description: "Servicio de corte", qty: 1, unit: "serv", net: 450000 },
    ],
    validations: [
      { id: "sum-items", ok: true, formula: "sum(items.net) == subtotal", message: "ítems = subtotal" },
      {
        id: "tax-rate",
        ok: false,
        formula: "taxable * 0.19 ~= tax",
        message: "No cuadra: 19 % de 4.050.000 es 769.500, no 770.000",
      },
      {
        id: "total",
        ok: false,
        formula: "subtotal + tax - discount == total",
        message: "No cuadra: 4.050.000 + 770.000 = 4.820.000, pero el 19 % deja 4.819.500",
      },
    ],
    usage: {
      tokens_est: 774,
      tokens_in: 812,
      tokens_out: 146,
      tokens_total: 958,
      model: "gemini-3.5-flash-lite",
      cache_hit: false,
    },
  },
  "doc-norte": {
    id: "doc-norte",
    filename: "POS-2291-norte.pdf",
    mime: "application/pdf",
    file_url: "/mocks/norte.svg",
    status: "needs_review",
    stage: "human",
    source: "pymupdf",
    confidence: 0.91,
    report:
      "PDF digital. PyMuPDF sacó NIT, ítems y totales. Las reglas cierran. Queda en revisión porque AUTO_APPROVE_DIGITAL está apagado.",
    fields: [
      { key: "supplier", label: "proveedor", value: "Droguería El Norte", confidence: 0.97, edited: false },
      { key: "nit", label: "NIT", value: "800.456.123-7", confidence: 0.96, edited: false },
      { key: "number", label: "número", value: "POS-2291", confidence: 0.95, edited: false },
      { key: "date", label: "fecha", value: "2026-08-18", confidence: 0.95, edited: false },
      { key: "due_date", label: "vence", value: "2026-08-18", confidence: 0.94, edited: false },
      { key: "subtotal", label: "subtotal", value: "156639", confidence: 0.94, edited: false },
      { key: "tax", label: "iva", value: "29761", confidence: 0.93, edited: false },
      { key: "discount", label: "descuento", value: "0", confidence: 0.9, edited: false },
      { key: "total", label: "total", value: "186400", confidence: 0.95, edited: false },
    ],
    items: [
      { description: "Losartán 50 mg x 30", qty: 2, unit: "caja", net: 62400 },
      { description: "Acetaminofén 500 mg", qty: 3, unit: "caja", net: 18600 },
      { description: "Suero oral", qty: 4, unit: "und", net: 75639 },
    ],
    validations: [
      { id: "sum-items", ok: true, formula: "sum(items.net) == subtotal", message: "ítems = subtotal" },
      { id: "tax-rate", ok: true, formula: "taxable * 0.19 ~= tax", message: "iva 19 %" },
      { id: "total", ok: true, formula: "subtotal + tax - discount == total", message: "total cierra" },
    ],
    usage: {
      tokens_est: 0,
      tokens_in: 0,
      tokens_out: 0,
      tokens_total: 0,
      model: "",
      cache_hit: false,
    },
  },
};

export const MOCK_ENGINE = {
  pymupdf4llm: true,
  rapidocr: true,
  gemini: { configured: true, ok: true, model: "gemini-3.5-flash-lite" },
  ollama: { ok: true, chat: "qwen3.5:0.8b", embed: "nomic-embed-text" },
  chat: { ok: true, primary: "gemini" as const },
  inbox: "../inbox",
  db: "../data/app.db",
};

export const MOCK_KNOWLEDGE = [
  "Hola. Soy el asistente de Cuadre IQ. Te ayudo con la cola, el inspector y a mandar el PDF original por correo.",
  "Cuadre IQ extrae, valida y deja revisar facturas. La plata la cuadra Python, no la IA.",
  "Arrastra al campo o deja el PDF/foto en inbox. PDF con texto: PyMuPDF, 0 tokens. Foto o scan: Gemini ve una página chica. Si Gemini no responde: RapidOCR.",
  "Cola a la izquierda. Click = abrir. needs_review = hay que mirarlo.",
  "Campos: Enter o blur guarda. Amarillo = baja confianza. Rojo = no cuadra. No cambies un total a ojo si la fórmula está roja: corrige el ítem.",
  "Aprobar = R. Rechazar = Shift+R. Aprobar no recalcula.",
  "Tokens debajo del reporte: es Gemini en ESA factura. cache = no se cobró de nuevo. PDF digital muestra 0.",
  "Si pides mandar esta factura por correo, doy la dirección y el backend se la pasa a n8n con el PDF original. Solo needs_review o approved.",
  "No extraigo facturas. No cambio montos. No llamo a Gemini. No invento proveedores.",
];
