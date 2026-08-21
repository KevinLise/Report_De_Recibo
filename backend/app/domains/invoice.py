from pydantic import BaseModel, Field


FIELD_LABELS = {
    "supplier": "proveedor",
    "nit": "NIT",
    "number": "número",
    "date": "fecha",
    "due_date": "vence",
    "subtotal": "subtotal",
    "tax": "iva",
    "discount": "descuento",
    "total": "total",
}

SCHEMA_KEYS = list(FIELD_LABELS.keys())
MONEY_KEYS = {"subtotal", "tax", "discount", "total"}


class LineItemDraft(BaseModel):
    description: str = ""
    qty: float = 1
    unit: str | None = None
    net: float = 0


class InvoiceDraft(BaseModel):
    supplier: str = ""
    nit: str = ""
    number: str = ""
    date: str = ""
    due_date: str = ""
    subtotal: float | None = None
    tax: float | None = None
    discount: float | None = 0
    total: float | None = None
    items: list[LineItemDraft] = Field(default_factory=list)
    report: str = ""
