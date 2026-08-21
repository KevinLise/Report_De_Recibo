export type Status =
  | "queued"
  | "running"
  | "needs_review"
  | "approved"
  | "rejected"
  | "error";

export type Stage = "extract" | "rules" | "gemini" | "human";

export type Source = "pymupdf" | "rapidocr" | "gemini";

export type FieldKey =
  | "supplier"
  | "nit"
  | "number"
  | "date"
  | "due_date"
  | "subtotal"
  | "tax"
  | "discount"
  | "total";

export const SCHEMA_KEYS: FieldKey[] = [
  "supplier",
  "nit",
  "number",
  "date",
  "due_date",
  "subtotal",
  "tax",
  "discount",
  "total",
];

export const FIELD_LABELS: Record<FieldKey, string> = {
  supplier: "proveedor",
  nit: "NIT",
  number: "número",
  date: "fecha",
  due_date: "vence",
  subtotal: "subtotal",
  tax: "iva",
  discount: "descuento",
  total: "total",
};

export const MONEY_KEYS = new Set<string>([
  "subtotal",
  "tax",
  "discount",
  "total",
]);

export const DATA_KEYS = new Set<string>([
  "nit",
  "number",
  "date",
  "due_date",
  "subtotal",
  "tax",
  "discount",
  "total",
]);

export type QueueItem = {
  id: string;
  filename: string;
  supplier: string;
  number: string;
  total: number | null;
  status: Status;
  confidence: number;
  created_at: string;
};

export type Field = {
  key: string;
  label: string;
  value: string;
  confidence: number;
  edited: boolean;
};

export type LineItem = {
  description: string;
  qty: number;
  unit?: string;
  net: number;
};

export type Validation = {
  id: string;
  ok: boolean;
  formula: string;
  message: string;
};

export type Usage = {
  tokens_est: number;
  tokens_in: number;
  tokens_out: number;
  tokens_total: number;
  model: string;
  cache_hit: boolean;
};

export type Document = {
  id: string;
  filename: string;
  mime: string;
  file_url: string;
  status: Status;
  stage: Stage;
  fields: Field[];
  items: LineItem[];
  validations: Validation[];
  report: string;
  confidence: number;
  source: Source;
  usage: Usage;
};

export type Job = {
  id: string;
  status: "queued" | "running" | "done" | "error";
  document_id?: string;
  stage?: Stage;
  error?: string;
};

export type Engine = {
  pymupdf4llm: boolean;
  rapidocr: boolean;
  gemini: { configured: boolean; ok: boolean; model: string };
  ollama: { ok: boolean; chat: string; embed: string };
  chat?: { ok: boolean; primary: "gemini" | "ollama" | null };
  inbox: string;
  db: string;
};

export type DayUsage = {
  today: { calls: number; tokens_in: number; tokens_out: number };
  last: Array<{ document_id: string; tokens_in: number; tokens_out: number }>;
};

export type ChatResponse = {
  text: string;
  action?: "email";
  document_id?: string;
  to?: string;
  sent?: boolean;
  provider?: "gemini" | "ollama" | "local";
  tokens_local?: number;
  tokens_in?: number;
  tokens_out?: number;
};

export type UploadResult =
  | { kind: "ready"; document: Document }
  | { kind: "job"; job: Job };
