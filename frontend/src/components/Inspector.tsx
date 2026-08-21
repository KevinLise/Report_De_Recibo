import { useEffect, useState } from "react";
import type { Document, Field } from "../api/types";
import { DATA_KEYS, FIELD_LABELS, MONEY_KEYS, SCHEMA_KEYS, type FieldKey } from "../api/types";
import { money, fieldNum } from "../lib/format";
import { PipelineDots } from "./PipelineDots";
import { Report } from "./Report";
import { UsageLine } from "./UsageLine";

const LOW = 0.72;

type Props = {
  doc: Document;
  flash?: boolean;
  onSave: (key: string, value: string) => Promise<void>;
};

export function Inspector({ doc, flash, onSave }: Props) {
  const byKey = new Map(doc.fields.map((f) => [f.key, f]));
  const extras = doc.fields.filter((f) => !(SCHEMA_KEYS as string[]).includes(f.key));
  const faults = new Set(doc.validations.filter((v) => !v.ok).flatMap(faultKeys));

  return (
    <section className="inspector">
      <PipelineDots stage={doc.stage} source={doc.source} />
      <div className="inspector__fields">
        {SCHEMA_KEYS.map((key) => {
          const field = byKey.get(key) ?? emptyField(key);
          const fault = faults.has(key);
          return (
            <FieldRow
              key={key}
              field={field}
              fault={fault}
              flash={flash && key === "total"}
              total={key === "total"}
              onSave={onSave}
            />
          );
        })}
        {extras.map((field) => (
          <FieldRow key={field.key} field={field} fault={false} onSave={onSave} />
        ))}
      </div>

      {doc.items.length > 0 ? (
        <ul className="inspector__items">
          {doc.items.map((it, i) => (
            <li key={`${it.description}-${i}`}>
              <span>
                {it.qty}× {it.description}
              </span>
              <span>{money(it.net)}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {doc.validations.length > 0 ? (
        <ul className="inspector__vals">
          {doc.validations.map((v) => (
            <li key={v.id} className={v.ok ? "is-ok" : "is-fault"}>
              <span>{v.message}</span>
              {!v.ok ? <code>{v.formula}</code> : null}
            </li>
          ))}
        </ul>
      ) : null}

      <Report text={doc.report} />
      <UsageLine usage={doc.usage} />
    </section>
  );
}

function FieldRow({
  field,
  fault,
  flash,
  total,
  onSave,
}: {
  field: Field;
  fault: boolean;
  flash?: boolean;
  total?: boolean;
  onSave: (key: string, value: string) => Promise<void>;
}) {
  const [value, setValue] = useState(displayValue(field));
  useEffect(() => {
    setValue(displayValue(field));
  }, [field]);

  const low = field.confidence < LOW;
  const empty = field.value.trim() === "";
  const tone = fault || empty ? "is-fault" : low ? "is-signal" : "";
  const data = DATA_KEYS.has(field.key);

  async function commit() {
    const raw = MONEY_KEYS.has(field.key)
      ? String(fieldNum(value.replace(/\./g, "").replace(",", ".")) ?? value)
      : value;
    if (raw === field.value) return;
    await onSave(field.key, raw);
  }

  return (
    <label className={`i-row${flash ? " is-flash" : ""}${total ? " is-total" : ""}`}>
      <span>{field.label}</span>
      <input
        className={`${data ? "is-data" : ""} ${tone}`.trim()}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={() => void commit()}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            (e.target as HTMLInputElement).blur();
          }
        }}
        spellCheck={false}
      />
    </label>
  );
}

function emptyField(key: FieldKey): Field {
  return {
    key,
    label: FIELD_LABELS[key],
    value: "",
    confidence: 0,
    edited: false,
  };
}

function displayValue(field: Field): string {
  if (!MONEY_KEYS.has(field.key) || field.value === "") return field.value;
  const n = fieldNum(field.value);
  return n === null ? field.value : money(n);
}

function faultKeys(v: { id: string; formula: string }): string[] {
  if (v.id === "tax-rate") return ["tax"];
  if (v.id === "total") return ["total"];
  if (v.id === "sum-items") return ["subtotal"];
  if (v.formula.includes("taxable") || v.formula.includes("0.19")) return ["tax"];
  if (v.formula.includes("== total")) return ["total"];
  if (v.formula.includes("items")) return ["subtotal"];
  return [];
}
