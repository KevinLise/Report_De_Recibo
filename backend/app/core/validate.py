"""Reglas de plata. Sin IA."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.domains.invoice import InvoiceDraft, LineItemDraft

IVA = 0.19
EPS = 0.01

_NIT_PRIMES = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def nit_digits(raw: str) -> tuple[str, str] | None:
    s = re.sub(r"[^\d]", "", raw or "")
    if len(s) < 6:
        return None
    return s[:-1], s[-1]


def nit_dv(body: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * _NIT_PRIMES[i]
    r = total % 11
    return str(r if r < 2 else 11 - r)


def nit_ok(raw: str) -> bool:
    parsed = nit_digits(raw)
    if not parsed:
        return False
    body, dv = parsed
    return nit_dv(body) == dv


def _parse_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def money(n: float | None) -> float:
    return 0.0 if n is None else float(n)


def run(
    draft: InvoiceDraft,
    *,
    existing: list[tuple[str, str, float]] | None = None,
) -> list[dict]:
    """existing = [(nit, number, total), ...] para unique."""
    sub = money(draft.subtotal)
    tax = money(draft.tax)
    disc = money(draft.discount)
    total = money(draft.total)
    items_sum = sum(money(i.net) for i in draft.items)
    taxable = sub - disc
    tax_expect = round(taxable * IVA, 2)
    total_expect = round(sub + tax - disc, 2)

    out: list[dict] = []

    ok_items = abs(items_sum - sub) <= max(EPS, 1) if draft.items else True
    out.append(
        {
            "id": "sum-items",
            "ok": ok_items,
            "formula": "sum(items.net) == subtotal",
            "message": "ítems = subtotal"
            if ok_items
            else f"No cuadra: ítems {items_sum} ≠ subtotal {sub}",
        }
    )

    ok_tax = abs(tax - tax_expect) <= max(EPS, 1) if sub else tax == 0
    out.append(
        {
            "id": "tax-rate",
            "ok": ok_tax,
            "formula": "taxable * 0.19 ~= tax",
            "message": "iva 19 %" if ok_tax else f"No cuadra: 19 % es {tax_expect}, no {tax}",
        }
    )

    ok_total = abs(total - total_expect) <= max(EPS, 1) if total or sub else True
    out.append(
        {
            "id": "total",
            "ok": ok_total,
            "formula": "subtotal + tax - discount == total",
            "message": "total cierra"
            if ok_total
            else f"No cuadra: {sub} + {tax} − {disc} = {total_expect}, no {total}",
        }
    )

    issued = _parse_date(draft.date)
    due = _parse_date(draft.due_date) if draft.due_date else issued
    dates_ok = True
    date_msg = "fechas"
    if draft.date and issued is None:
        dates_ok, date_msg = False, "fecha no se lee"
    elif due and issued and due < issued:
        dates_ok, date_msg = False, "vence < fecha"
    out.append({"id": "dates", "ok": dates_ok, "formula": "due >= issued", "message": date_msg})

    has_nit = bool((draft.nit or "").strip())
    if not has_nit:
        out.append({"id": "nit", "ok": False, "formula": "NIT DIAN modulo 11", "message": "Falta NIT"})
    else:
        ok_nit = nit_ok(draft.nit)
        out.append(
            {
                "id": "nit",
                "ok": ok_nit,
                "formula": "NIT DIAN modulo 11",
                "message": "NIT" if ok_nit else "NIT no cuadra",
            }
        )

    negs = [k for k, v in (("subtotal", sub), ("tax", tax), ("total", total)) if v < 0]
    if disc < 0:
        negs.append("discount")
    ok_neg = not negs
    out.append(
        {
            "id": "negatives",
            "ok": ok_neg,
            "formula": "montos >= 0",
            "message": "signos" if ok_neg else f"negativos: {', '.join(negs)}",
        }
    )

    dup = False
    if existing and draft.nit and draft.number:
        key = (re.sub(r"[^\d]", "", draft.nit), draft.number.strip(), round(total, 2))
        for nit, num, tot in existing:
            if (re.sub(r"[^\d]", "", nit), num, round(tot, 2)) == key:
                dup = True
                break
    out.append(
        {
            "id": "unique",
            "ok": not dup,
            "formula": "unique(nit, number, total)",
            "message": "única" if not dup else "ya está en cola (mismo NIT + número + total)",
        }
    )
    return out


def draft_from_fields(fields: dict[str, str], items: list[LineItemDraft] | None = None) -> InvoiceDraft:
    def fnum(key: str) -> float | None:
        raw = (fields.get(key) or "").replace(".", "").replace(",", ".")
        raw = re.sub(r"[^\d.\-]", "", raw)
        if raw in ("", "-", "."):
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    return InvoiceDraft(
        supplier=fields.get("supplier", ""),
        nit=fields.get("nit", ""),
        number=fields.get("number", ""),
        date=fields.get("date", ""),
        due_date=fields.get("due_date", ""),
        subtotal=fnum("subtotal"),
        tax=fnum("tax"),
        discount=fnum("discount") or 0,
        total=fnum("total"),
        items=items or [],
    )
