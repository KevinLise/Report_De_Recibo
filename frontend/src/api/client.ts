import type {
  ChatResponse,
  DayUsage,
  Document,
  Engine,
  Job,
  QueueItem,
  UploadResult,
} from "./types";
import { mockStore } from "../mocks/store";

const BASE = "/api";
const FETCH_TIMEOUT_MS = 120_000;
const POLL_INTERVAL_MS = 1500;
const POLL_MAX_MS = 30 * 60 * 1000;
const HEALTH_MS = 1500;
const PROBE_TTL_MS = 2000;

let mocked = true;
let probedAt = 0;

async function parseError(res: Response): Promise<string> {
  let detail = res.statusText;
  try {
    const j = (await res.json()) as { detail?: unknown; message?: string; error?: string };
    if (typeof j.detail === "string") detail = j.detail;
    else if (j.message) detail = j.message;
    else if (j.error) detail = j.error;
  } catch {
    /* ignore */
  }
  return detail;
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = FETCH_TIMEOUT_MS,
): Promise<Response> {
  const ctrl = new AbortController();
  const id = window.setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: ctrl.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("El servidor tardó demasiado.");
    }
    throw err;
  } finally {
    window.clearTimeout(id);
  }
}

export async function probeLive(force = false): Promise<boolean> {
  const now = Date.now();
  if (!force && probedAt && now - probedAt < PROBE_TTL_MS) return !mocked;
  try {
    const res = await fetchWithTimeout(`${BASE}/health`, {}, HEALTH_MS);
    mocked = !res.ok;
  } catch {
    mocked = true;
  }
  probedAt = now;
  return !mocked;
}

export function isMocked(): boolean {
  return mocked === true;
}

export async function getEngine(): Promise<Engine> {
  if (!(await probeLive())) return mockStore.engine();
  const res = await fetchWithTimeout(`${BASE}/engine`, {}, 8000);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Engine>;
}

export async function getQueue(status?: string): Promise<QueueItem[]> {
  if (!(await probeLive())) return mockStore.queue(status);
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await fetchWithTimeout(`${BASE}/queue${q}`, {}, 8000);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<QueueItem[]>;
}

export async function getDocument(id: string): Promise<Document> {
  if (!(await probeLive())) {
    const d = mockStore.document(id);
    if (!d) throw new Error("documento no está");
    return d;
  }
  const res = await fetchWithTimeout(`${BASE}/documents/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Document>;
}

export async function patchDocument(
  id: string,
  fields: Record<string, string>,
): Promise<Document> {
  if (!(await probeLive())) {
    const d = mockStore.patch(id, fields);
    if (!d) throw new Error("documento no está");
    return d;
  }
  const res = await fetchWithTimeout(`${BASE}/documents/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Document>;
}

export async function approveDocument(id: string): Promise<Document> {
  if (!(await probeLive())) {
    const d = mockStore.setStatus(id, "approved");
    if (!d) throw new Error("documento no está");
    return d;
  }
  const res = await fetchWithTimeout(`${BASE}/documents/${encodeURIComponent(id)}/approve`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Document>;
}

export async function rejectDocument(id: string): Promise<Document> {
  if (!(await probeLive())) {
    const d = mockStore.setStatus(id, "rejected");
    if (!d) throw new Error("documento no está");
    return d;
  }
  const res = await fetchWithTimeout(`${BASE}/documents/${encodeURIComponent(id)}/reject`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Document>;
}

export function fileUrl(doc: Document): string {
  if (doc.file_url.startsWith("blob:") || doc.file_url.startsWith("/mocks")) {
    return doc.file_url;
  }
  return `${BASE}/documents/${encodeURIComponent(doc.id)}/file`;
}

export async function getJob(id: string): Promise<Job> {
  if (!(await probeLive())) {
    const j = mockStore.job(id);
    if (!j) throw new Error("job no está");
    return j;
  }
  const res = await fetchWithTimeout(`${BASE}/jobs/${encodeURIComponent(id)}`, {}, 15_000);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Job>;
}

export async function pollJob(
  jobId: string,
  onTick?: (job: Job) => void,
): Promise<Job> {
  const start = Date.now();
  while (Date.now() - start < POLL_MAX_MS) {
    const job = await getJob(jobId);
    onTick?.(job);
    if (job.status === "done") return job;
    if (job.status === "error") throw new Error(job.error || "Error en el trabajo");
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  throw new Error("El trabajo superó 30 min.");
}

export async function uploadDocuments(files: File[]): Promise<UploadResult> {
  if (files.some((f) => f.size > 40 * 1024 * 1024)) {
    throw new Error("archivo > 40 MB");
  }
  if (!(await probeLive(true))) {
    throw new Error("API apagada (:4005). No subí el archivo. Gemini no corrió.");
  }
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  const res = await fetchWithTimeout(`${BASE}/documents`, { method: "POST", body: fd });
  if (res.status === 202) {
    const job = (await res.json()) as Job;
    return { kind: "job", job };
  }
  if (!res.ok) throw new Error(await parseError(res));
  const document = (await res.json()) as Document;
  return { kind: "ready", document };
}

export async function getUsage(): Promise<DayUsage> {
  if (!(await probeLive())) return mockStore.usage();
  const res = await fetchWithTimeout(`${BASE}/usage`, {}, 8000);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<DayUsage>;
}

export async function sendChat(
  message: string,
  documentId?: string,
  history: Array<{ role: "user" | "assistant"; text: string }> = [],
): Promise<ChatResponse> {
  if (!(await probeLive(true))) {
    throw new Error("API apagada (:4005). El asistente no corre en mock.");
  }
  const res = await fetchWithTimeout(
    `${BASE}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, document_id: documentId, history }),
    },
    90_000,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ChatResponse>;
}

export async function sendChatEmail(documentId: string, to: string): Promise<void> {
  if (!(await probeLive())) {
    mockStore.email(documentId, to);
    return;
  }
  const res = await fetchWithTimeout(`${BASE}/chat/email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, to }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}
