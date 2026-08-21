from app.core.validate import nit_dv, nit_ok, run
from app.domains.invoice import InvoiceDraft, LineItemDraft


def test_nit_andina():
    assert nit_dv("900123456") == "8"
    assert nit_ok("900.123.456-8")
    assert not nit_ok("900.123.456-1")


def test_cierra():
    d = InvoiceDraft(
        supplier="Norte",
        nit="800.456.123-7",
        number="POS-1",
        date="2026-08-18",
        due_date="2026-08-18",
        subtotal=156639,
        tax=29761,
        discount=0,
        total=186400,
        items=[
            LineItemDraft(description="a", qty=2, net=62400),
            LineItemDraft(description="b", qty=3, net=18600),
            LineItemDraft(description="c", qty=4, net=75639),
        ],
    )
    vals = {v["id"]: v["ok"] for v in run(d)}
    assert vals["sum-items"]
    assert vals["tax-rate"]
    assert vals["total"]
    assert vals["nit"]
    assert vals["dates"]


def test_no_cuadra():
    d = InvoiceDraft(
        supplier="Andina",
        nit="900.123.456-8",
        number="FV-1",
        date="2026-08-12",
        due_date="2026-09-11",
        subtotal=4050000,
        tax=770000,
        discount=0,
        total=4820000,
        items=[
            LineItemDraft(description="a", qty=1, net=1200000),
            LineItemDraft(description="b", qty=1, net=2400000),
            LineItemDraft(description="c", qty=1, net=450000),
        ],
    )
    vals = {v["id"]: v for v in run(d)}
    assert vals["sum-items"]["ok"]
    assert not vals["tax-rate"]["ok"]
