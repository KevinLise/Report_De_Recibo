import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { uploadDocuments } from "../api/client";
import type { Job } from "../api/types";
import { Actions } from "../components/Actions";
import { ChatDock } from "../components/ChatDock";
import { Inspector } from "../components/Inspector";
import { Paper } from "../components/Paper";
import { Queue } from "../components/Queue";
import { pulseField } from "../field/bus";
import { useDocument } from "../hooks/useDocument";
import { useEngine } from "../hooks/useEngine";
import { useJob } from "../hooks/useJob";
import { useQueue } from "../hooks/useQueue";
import { approveDocument, rejectDocument } from "../api/client";

export function Review() {
  const { id: routeId } = useParams();
  const queryId =
    typeof window !== "undefined"
      ? (new URLSearchParams(window.location.search).get("doc") ?? undefined)
      : undefined;
  const id = routeId ?? queryId;
  const navigate = useNavigate();
  const { items, refresh } = useQueue();
  const { mocked } = useEngine();
  const selected = items.find((i) => i.id === id);
  const { doc, setDoc, loading, saveField } = useDocument(id);
  const [jobId, setJobId] = useState<string | null>(null);
  const [flash, setFlash] = useState(false);
  const [dropOver, setDropOver] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const onJobDone = useCallback(
    (job: Job) => {
      setJobId(null);
      void refresh();
      if (job.document_id) navigate(`/doc/${job.document_id}`);
    },
    [navigate, refresh],
  );
  const { job } = useJob(jobId, onJobDone);

  const empty = items.length === 0 && !id;

  const nextId = useMemo(() => {
    const rest = items.filter((i) => i.id !== id && i.status === "needs_review");
    return rest[0]?.id;
  }, [items, id]);

  const select = (next: string) => {
    setSheetOpen(false);
    navigate(`/doc/${next}`);
  };

  const decide = useCallback(
    async (kind: "approve" | "reject") => {
      if (!doc || busy) return;
      setBusy(true);
      try {
        if (kind === "approve") {
          setFlash(true);
          const next = await approveDocument(doc.id);
          setDoc(next);
          window.setTimeout(() => {
            setFlash(false);
            void refresh();
            if (nextId) navigate(`/doc/${nextId}`);
            else navigate("/");
          }, 400);
        } else {
          await rejectDocument(doc.id);
          void refresh();
          if (nextId) navigate(`/doc/${nextId}`);
          else navigate("/");
        }
      } catch (e) {
        setNote(e instanceof Error ? e.message : "No cuadra");
      } finally {
        setBusy(false);
      }
    },
    [busy, doc, navigate, nextId, refresh, setDoc],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "R" || e.key === "r") {
        if (!doc) return;
        e.preventDefault();
        void decide(e.shiftKey ? "reject" : "approve");
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [decide, doc]);

  async function onFiles(files: File[], point?: { x: number; y: number }) {
    if (!files.length) return;
    pulseField("upload", point);
    setNote(null);
    try {
      const res = await uploadDocuments(files);
      if (res.kind === "ready") {
        await refresh();
        navigate(`/doc/${res.document.id}`);
      } else {
        setJobId(res.job.id);
        await refresh();
        const docId = res.job.document_id;
        if (docId) navigate(`/doc/${docId}`);
      }
    } catch (e) {
      setNote(e instanceof Error ? e.message : "No cuadra");
    }
  }

  const stage =
    job?.stage ??
    (selected?.status === "running" || selected?.status === "queued" ? "extract" : doc?.stage);

  return (
    <div
      className="review"
      onDragEnter={(e) => {
        e.preventDefault();
        setDropOver(true);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDropOver(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget.contains(e.relatedTarget as Node)) return;
        setDropOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDropOver(false);
        const list = Array.from(e.dataTransfer.files);
        void onFiles(list, { x: e.clientX, y: e.clientY });
      }}
    >
      <Queue
        items={items}
        activeId={id}
        onSelect={select}
        sheet={false}
        note={mocked ? "API apagada · :4005" : undefined}
      />

      <main className="review__main">
        {empty ? (
          <div className="empty">
            <p>Nada en cola.</p>
            <p>
              {mocked
                ? "Backend apagado (:4005). Sin él no hay cola real."
                : "Abrí un PDF o una foto de la factura."}
            </p>
            <button type="button" className="empty__open" onClick={() => fileRef.current?.click()}>
              abrir PDF o foto
            </button>
          </div>
        ) : (
          <Paper
            doc={doc}
            loading={!doc && (loading || selected?.status === "running" || !!job)}
            stage={stage}
            flash={flash}
          />
        )}
      </main>

      {doc ? (
        <Inspector doc={doc} flash={flash} onSave={saveField} />
      ) : selected?.status === "running" || selected?.status === "queued" ? (
        <section className="inspector">
          <p className="pipe">
            extract · reglas · <span className="is-now">{stage ?? "extract"}</span> · humano
          </p>
          <p className="engine-line">{selected.status === "queued" ? "en cola" : "en pipeline"}</p>
          {note ? <p className="engine-line is-fault">{note}</p> : null}
        </section>
      ) : (
        <section className="inspector inspector--idle" aria-hidden={!note} />
      )}

      <Actions
        disabled={!doc || busy}
        onApprove={() => void decide("approve")}
        onReject={() => void decide("reject")}
        onOpen={empty ? undefined : () => fileRef.current?.click()}
      />

      <Queue
        items={items}
        activeId={id}
        onSelect={select}
        sheet
        open={sheetOpen}
        onToggle={() => setSheetOpen((v) => !v)}
      />

      <ChatDock documentId={doc?.id} />

      <input
        ref={fileRef}
        className="file-hidden"
        type="file"
        accept="application/pdf,image/jpeg,image/png,image/webp,image/jpg,image/heic,image/heif,.pdf,.jpg,.jpeg,.png,.webp,.heic,.heif,.bmp,.tif"
        multiple
        onChange={(e) => {
          const list = Array.from(e.target.files ?? []);
          e.target.value = "";
          void onFiles(list);
        }}
      />

      {dropOver ? (
        <div className="drop" aria-hidden="true">
          soltar
        </div>
      ) : null}
    </div>
  );
}
