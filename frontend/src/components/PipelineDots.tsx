import type { Source, Stage } from "../api/types";

const STEPS: { id: Stage; label: string }[] = [
  { id: "extract", label: "extract" },
  { id: "gemini", label: "ocr" },
  { id: "rules", label: "reglas" },
  { id: "human", label: "humano" },
];

const ORDER: Stage[] = ["extract", "gemini", "rules", "human"];

export function PipelineDots({ stage, source }: { stage: Stage; source?: Source }) {
  const here = ORDER.indexOf(stage);
  const sourceNote =
    source === "pymupdf" ? "PyMuPDF" : source === "rapidocr" ? "RapidOCR" : source === "gemini" ? "Gemini" : "";

  return (
    <p className="pipe">
      {STEPS.map((s, i) => (
        <span key={s.id} className={i === here ? "is-now" : i < here ? "is-done" : ""}>
          {s.label}
          {i < STEPS.length - 1 ? " · " : ""}
        </span>
      ))}
      {sourceNote ? <span className="pipe__src">{sourceNote}</span> : null}
    </p>
  );
}
