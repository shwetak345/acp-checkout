import os
from dotenv import load_dotenv
from typing import List
from .models import LineItem, TotalsRow, FulfillmentOption, Item
from .catalog import CATALOG
from uuid import uuid4

load_dotenv()

CURRENCY = "usd"
LINKS = [
    {"type": "terms_of_use", "url": "https://example.com/terms"},
    {"type": "privacy_policy", "url": "https://example.com/privacy"},
]
OPENAI_ORDER_WEBHOOK_URL = os.getenv("OPENAI_ORDER_WEBHOOK_URL")
PORT = int(os.getenv("PORT", "3000"))

def uuid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"

def price_for(sku: str) -> int:
    data = CATALOG.get(sku)
    if not data:
        raise KeyError("unknown_sku")
    return int(data["price"])  # cents

def default_fulfillment_options() -> List[FulfillmentOption]:
    return [
        FulfillmentOption(id="ship_econ", label="Economy (5–7 days)", amount=599, eta_days=7),
        FulfillmentOption(id="ship_exp",  label="Express (2–3 days)",  amount=1299, eta_days=3),
    ]

def calc_cart(items: list[Item], fulfillment: FulfillmentOption | None):
    line_items: list[LineItem] = []
    for it in items:
        base = price_for(it.id) * it.quantity
        tax = round(base * 0.085)
        total = base + tax
        line_items.append(
            LineItem(
                id=uuid("li"),
                item=it,
                base_amount=base,
                discount=0,
                subtotal=base,
                tax=tax,
                total=total,
            )
        )
    items_base_amount = sum(li.base_amount for li in line_items)
    tax = sum(li.tax for li in line_items)
    shipping = fulfillment.amount if fulfillment else 0
    total = items_base_amount + tax + shipping

    totals: list[TotalsRow] = [
        TotalsRow(type="items_base_amount", display_text="Item(s) total", amount=items_base_amount),
        TotalsRow(type="tax", display_text="Tax", amount=tax),
    ]
    if fulfillment:
        totals.append(TotalsRow(type="shipping", display_text="Shipping", amount=shipping))
    totals.append(TotalsRow(type="total", display_text="Total", amount=total))
    return line_items, totals, total
