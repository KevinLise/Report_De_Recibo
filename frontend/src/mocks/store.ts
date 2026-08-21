import type {
  ChatResponse,
  DayUsage,
  Document,
  Engine,
  Field,
  Job,
  QueueItem,
  Stage,
  Status,
} from "../api/types";
import { FIELD_LABELS, type FieldKey } from "../api/types";
import { fieldNum } from "../lib/format";
import { MOCK_DOCUMENTS, MOCK_ENGINE, MOCK_KNOWLEDGE } from "./documents";
import seedQueue from "./queue.json";

const LIVE: Status[] = ["queued", "running", "needs_review", "error"];

let queue: QueueItem[] = (seedQueue as QueueItem[]).map((q) => ({ ...q }));
const docs: Record<string, Document> = structuredClone(MOCK_DOCUMENTS);
const jobs = new Map<string, Job>();
let jobTickers = 0;

function liveQueue(): QueueItem[] {
  return queue.filter((q) => LIVE.includes(q.status));
}

function getField(doc: Document, key: string): Field | undefined {
  return doc.fields.find((f) => f.key === key);
}

function revalidate(doc: Document): Document {
  const sub = fieldNum(getField(doc, "subtotal")?.value ?? "") ?? 0;
  const tax = fieldNum(getField(doc, "tax")?.value ?? "") ?? 0;
  const disc = fieldNum(getField(doc, "discount")?.value ?? "") ?? 0;
  const total = fieldNum(getField(doc, "total")?.value ?? "") ?? 0;
  const items = doc.items.reduce((s, i) => s + i.net, 0);
  const taxExpect = Math.round(sub * 0.19);
  const totalExpect = sub + tax - disc;

  doc.validations = [
    {
      id: "sum-items",
      ok: Math.abs(items - sub) <= 1,
      formula: "sum(items.net) == subtotal",
      message:
        Math.abs(items - sub) <= 1
          ? "ítems = subtotal"
          : `No cuadra: ítems ${items} ≠ subtotal ${sub}`,
    },
    {
      id: "tax-rate",
      ok: Math.abs(tax - taxExpect) <= 1,
      formula: "taxable * 0.19 ~= tax",
      message:
        Math.abs(tax - taxExpect) <= 1
          ? "iva 19 %"
          : `No cuadra: 19 % es ${taxExpect}, no ${tax}`,
    },
    {
      id: "total",
      ok: Math.abs(total - totalExpect) <= 1,
      formula: "subtotal + tax - discount == total",
      message:
        Math.abs(total - totalExpect) <= 1
          ? "total cierra"
          : `No cuadra: ${sub} + ${tax} − ${disc} = ${totalExpect}, no ${total}`,
    },
  ];
  return doc;
}

export const mockStore = {
  engine(): Engine {
    return structuredClone(MOCK_ENGINE);
  },

  queue(status?: string): QueueItem[] {
    const rows = liveQueue();
    if (!status) return structuredClone(rows);
    return structuredClone(rows.filter((q) => q.status === status));
  },

  document(id: string): Document | null {
    const d = docs[id];
    return d ? structuredClone(d) : null;
  },

  patch(id: string, fields: Record<string, string>): Document | null {
    const d = docs[id];
    if (!d) return null;
    for (const [key, value] of Object.entries(fields)) {
      const existing = d.fields.find((f) => f.key === key);
      if (existing) {
        existing.value = value;
        existing.edited = true;
      } else {
        d.fields.push({
          key,
          label: FIELD_LABELS[key as FieldKey] ?? key,
          value,
          confidence: 1,
          edited: true,
        });
      }
    }
    revalidate(d);
    const q = queue.find((i) => i.id === id);
    if (q) {
      q.supplier = getField(d, "supplier")?.value ?? q.supplier;
      q.number = getField(d, "number")?.value ?? q.number;
      q.total = fieldNum(getField(d, "total")?.value ?? "");
    }
    return structuredClone(d);
  },

  setStatus(id: string, status: Status): Document | null {
    const d = docs[id];
    if (!d) return null;
    d.status = status;
    const q = queue.find((i) => i.id === id);
    if (q) q.status = status;
    return structuredClone(d);
  },

  job(id: string): Job | null {
    const j = jobs.get(id);
    return j ? { ...j } : null;
  },

  usage(): DayUsage {
    let tokens_in = 0;
    let tokens_out = 0;
    let calls = 0;
    const last: DayUsage["last"] = [];
    for (const d of Object.values(docs)) {
      if (d.usage.tokens_total > 0) {
        calls += 1;
        tokens_in += d.usage.tokens_in;
        tokens_out += d.usage.tokens_out;
        last.push({
          document_id: d.id,
          tokens_in: d.usage.tokens_in,
          tokens_out: d.usage.tokens_out,
        });
      }
    }
    return { today: { calls, tokens_in, tokens_out }, last };
  },

  upload(files: File[]): { status: 200 | 202; document?: Document; job?: Job } {
    const file = files[0];
    if (!file) throw new Error("sin archivo");
    const id = `doc-${Date.now().toString(36)}`;
    const isImage = file.type.startsWith("image/");
    const item: QueueItem = {
      id,
      filename: file.name,
      supplier: file.name.replace(/\.[^.]+$/, ""),
      number: "",
      total: null,
      status: isImage ? "running" : "needs_review",
      confidence: isImage ? 0 : 0.7,
      created_at: new Date().toISOString(),
    };
    queue = [item, ...queue];

    if (!isImage) {
      const doc: Document = {
        id,
        filename: file.name,
        mime: file.type || "application/pdf",
        file_url: URL.createObjectURL(file),
        status: "needs_review",
        stage: "human",
        source: "pymupdf",
        confidence: 0.7,
        report: "Mock local. El archivo quedó en cola para revisar. Backend no está arriba.",
        fields: [
          { key: "supplier", label: "proveedor", value: item.supplier, confidence: 0.5, edited: false },
          { key: "nit", label: "NIT", value: "", confidence: 0.2, edited: false },
          { key: "number", label: "número", value: "", confidence: 0.2, edited: false },
          { key: "date", label: "fecha", value: "", confidence: 0.2, edited: false },
          { key: "due_date", label: "vence", value: "", confidence: 0.2, edited: false },
          { key: "subtotal", label: "subtotal", value: "", confidence: 0.2, edited: false },
          { key: "tax", label: "iva", value: "", confidence: 0.2, edited: false },
          { key: "discount", label: "descuento", value: "0", confidence: 0.4, edited: false },
          { key: "total", label: "total", value: "", confidence: 0.2, edited: false },
        ],
        items: [],
        validations: [],
        usage: {
          tokens_est: 0,
          tokens_in: 0,
          tokens_out: 0,
          tokens_total: 0,
          model: "",
          cache_hit: false,
        },
      };
      docs[id] = doc;
      return { status: 200, document: structuredClone(doc) };
    }

    const job: Job = { id: `job-${id}`, status: "running", document_id: id, stage: "extract" };
    jobs.set(job.id, job);
    startTicker(job.id, id, file);
    return { status: 202, job: { ...job } };
  },

  chat(message: string, documentId?: string): ChatResponse {
    const text = message.trim();
    if (/^\s*(hola|hey|hi|buenas|qué tal|que tal|buenos días|buenos dias)\s*[!?.¡¿]*$/i.test(text)) {
      return {
        text: "Hola. Soy el asistente de Cuadre IQ. Te ayudo con la cola de facturas, el inspector, los totales y a mandar el PDF original por correo. ¿Qué necesitas?",
        provider: "local",
      };
    }
    const email = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0];
    const wantsMail = /correo|manda|envía|envia|email|mail/i.test(text);

    if (email && documentId) {
      return {
        text: `Listo. El backend mandaría ${documentId} a ${email} por n8n. En mock no sale el mail.`,
        action: "email",
        document_id: documentId,
        to: email,
        tokens_local: 24,
      };
    }
    if (wantsMail) {
      if (!documentId) {
        return { text: "Abrí una factura primero. Después te pido el correo.", tokens_local: 18 };
      }
      return {
        text: "¿A qué correo? Solo documentos en revisión o aprobados. Se adjunta el original, no un PDF nuevo.",
        tokens_local: 22,
      };
    }

    const q = text.toLowerCase();
    const hit =
      MOCK_KNOWLEDGE.find((line) =>
        line.toLowerCase().split(/\W+/).some((w) => w.length > 3 && q.includes(w)),
      ) ?? MOCK_KNOWLEDGE[0];
    return { text: hit ?? "No está en el manual.", tokens_local: 16 };
  },

  email(documentId: string, to: string): { ok: true } {
    const d = docs[documentId];
    if (!d) throw new Error("documento no está");
    if (d.status !== "needs_review" && d.status !== "approved") {
      throw new Error("solo needs_review o approved");
    }
    void to;
    return { ok: true };
  },
};

function startTicker(jobId: string, docId: string, file: File) {
  const stages: Stage[] = ["extract", "rules", "gemini", "human"];
  let i = 0;
  jobTickers += 1;
  const timer = window.setInterval(() => {
    i += 1;
    const job = jobs.get(jobId);
    if (!job) {
      window.clearInterval(timer);
      return;
    }
    if (i < stages.length) {
      job.stage = stages[i];
      const q = queue.find((x) => x.id === docId);
      if (q) q.status = "running";
      return;
    }
    window.clearInterval(timer);
    const doc: Document = {
      id: docId,
      filename: file.name,
      mime: file.type || "image/jpeg",
      file_url: URL.createObjectURL(file),
      status: "needs_review",
      stage: "human",
      source: "gemini",
      confidence: 0.55,
      report: "Esto es mock. El backend no está. Gemini no corrió.",
      fields: [
        { key: "supplier", label: "proveedor", value: file.name.replace(/\.[^.]+$/, ""), confidence: 0.4, edited: false },
        { key: "nit", label: "NIT", value: "", confidence: 0.2, edited: false },
        { key: "number", label: "número", value: "", confidence: 0.2, edited: false },
        { key: "date", label: "fecha", value: "", confidence: 0.2, edited: false },
        { key: "due_date", label: "vence", value: "", confidence: 0.2, edited: false },
        { key: "subtotal", label: "subtotal", value: "", confidence: 0.2, edited: false },
        { key: "tax", label: "iva", value: "", confidence: 0.2, edited: false },
        { key: "discount", label: "descuento", value: "0", confidence: 0.3, edited: false },
        { key: "total", label: "total", value: "", confidence: 0.2, edited: false },
      ],
      items: [],
      validations: [],
      usage: {
        tokens_est: 258,
        tokens_in: 310,
        tokens_out: 80,
        tokens_total: 390,
        model: "gemini-3.5-flash-lite",
        cache_hit: false,
      },
    };
    docs[docId] = doc;
    const q = queue.find((x) => x.id === docId);
    if (q) {
      q.status = "needs_review";
      q.confidence = 0.55;
    }
    job.status = "done";
    job.stage = "human";
    job.document_id = docId;
  }, 1500);
  void jobTickers;
}
