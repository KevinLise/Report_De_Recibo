import { useCallback, useEffect, useState } from "react";
import { getDocument, patchDocument } from "../api/client";
import type { Document } from "../api/types";
import { pulseField } from "../field/bus";
import { MOCK_DOCUMENTS } from "../mocks/documents";

function seedDoc(id: string | undefined): Document | null {
  if (!id) return null;
  const d = MOCK_DOCUMENTS[id];
  return d ? structuredClone(d) : null;
}

export function useDocument(id: string | undefined) {
  const [doc, setDoc] = useState<Document | null>(() => seedDoc(id));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (docId: string) => {
    setLoading(true);
    setError(null);
    try {
      const d = await getDocument(docId);
      setDoc(d);
      if (d.validations.some((v) => !v.ok) || d.status === "needs_review") {
        pulseField(d.validations.some((v) => !v.ok) ? "validation" : "needs_review");
      }
    } catch (e) {
      setDoc(null);
      setError(e instanceof Error ? e.message : "documento no está");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!id) {
      setDoc(null);
      setError(null);
      setLoading(false);
      return;
    }
    setDoc((prev) => (prev?.id === id ? prev : seedDoc(id)));
    void load(id);
  }, [id, load]);

  useEffect(() => {
    if (!doc || (doc.status !== "running" && doc.status !== "queued")) return;
    const t = window.setInterval(() => void load(doc.id), 1200);
    return () => window.clearInterval(t);
  }, [doc, load]);

  const saveField = useCallback(async (key: string, value: string) => {
    if (!doc) return;
    const next = await patchDocument(doc.id, { [key]: value });
    setDoc(next);
    if (next.validations.some((v) => !v.ok)) pulseField("validation");
  }, [doc]);

  return { doc, setDoc, loading, error, saveField, reload: load };
}
