from __future__ import annotations

from app.domains.invoice import InvoiceDraft, MONEY_KEYS, SCHEMA_KEYS


def score(draft: InvoiceDraft, validations: list[dict], field_conf: dict[str, float] | None = None) -> float:
    filled = 0
    for k in SCHEMA_KEYS:
        v = getattr(draft, k, None)
        if v not in (None, ""):
            filled += 1
    fill = filled / len(SCHEMA_KEYS)
    oks = [1.0 if v.get("ok") else 0.0 for v in validations] or [0]
    rules = sum(oks) / len(oks)
    confs = list((field_conf or {}).values())
    avg = sum(confs) / len(confs) if confs else fill
    return round(0.35 * fill + 0.45 * rules + 0.20 * avg, 3)


def field_map(draft: InvoiceDraft, base: float = 0.85) -> list[dict]:
    from app.domains.invoice import FIELD_LABELS

    out = []
    for k, label in FIELD_LABELS.items():
        val = getattr(draft, k, None)
        if val is None:
            s = ""
        elif k in MONEY_KEYS:
            s = str(int(val) if float(val).is_integer() else val)
        else:
            s = str(val)
        c = base if s else 0.2
        out.append({"key": k, "label": label, "value": s, "confidence": c, "edited": False})
    return out
