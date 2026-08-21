import { useEffect, useRef, useState } from "react";
import { getDocument as getPdf, GlobalWorkerOptions } from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { fileUrl } from "../api/client";
import type { Document, Stage } from "../api/types";

GlobalWorkerOptions.workerSrc = workerSrc;

const STAGE_COPY: Record<Stage, string> = {
  extract: "leyendo",
  rules: "reglas",
  gemini: "ocr",
  human: "humano",
};

type Props = {
  doc: Document | null;
  loading: boolean;
  stage?: Stage;
  flash?: boolean;
};

export function Paper({ doc, loading, stage, flash }: Props) {
  if (loading || (doc && (doc.status === "running" || doc.status === "queued") && !doc.file_url)) {
    return (
      <div className="paper">
        <p className="paper__stage">{STAGE_COPY[stage ?? doc?.stage ?? "extract"]}</p>
      </div>
    );
  }

  if (!doc) {
    return <div className="paper" />;
  }

  const url = fileUrl(doc);
  const name = (doc.filename || "").toLowerCase();
  const isImg =
    doc.mime.startsWith("image/") ||
    /\.(png|jpe?g|webp|gif|bmp|heic|heif|tiff?)$/.test(name);
  const isPdf = !isImg && (doc.mime.includes("pdf") || name.endsWith(".pdf")) && !url.endsWith(".svg");

  return (
    <div className={`paper${flash ? " is-flash" : ""}`}>
      <div className="paper__sheet">
        {isPdf ? (
          <PdfPage url={url} />
        ) : (
          <img src={url} alt={doc.filename} className="paper__img" />
        )}
      </div>
    </div>
  );
}

function PdfPage({ url }: { url: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fail, setFail] = useState(false);

  useEffect(() => {
    let cancel = false;
    const canvas = canvasRef.current;
    if (!canvas) return;
    (async () => {
      try {
        const pdf = await getPdf(url).promise;
        const page = await pdf.getPage(1);
        if (cancel) return;
        const box = canvas.parentElement?.getBoundingClientRect();
        const width = box?.width ?? 480;
        const viewport0 = page.getViewport({ scale: 1 });
        const scale = width / viewport0.width;
        const viewport = page.getViewport({ scale });
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        await page.render({ canvasContext: ctx, viewport }).promise;
      } catch {
        if (!cancel) setFail(true);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [url]);

  if (fail) return <p className="paper__stage">no se pudo leer el pdf</p>;
  return <canvas ref={canvasRef} className="paper__pdf" />;
}
