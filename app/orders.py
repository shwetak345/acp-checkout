from typing import Literal, Optional
import httpx

class Order:
    def __init__(self, id: str, checkout_session_id: str, total: int, currency: str,
                 status: Literal["created","paid","fulfillment_in_progress","shipped"] = "paid"):
        self.id = id
        self.checkout_session_id = checkout_session_id
        self.total = total
        self.currency = currency
        self.status = status

_ORDERS: dict[str, Order] = {}

def create_order(o: Order) -> Order:
    _ORDERS[o.id] = o
    return o

def get_order(order_id: str) -> Optional[Order]:
    return _ORDERS.get(order_id)

async def emit_order_event(webhook_url: Optional[str], event: dict):
    if not webhook_url:
        print("[webhook simulation]", event)
        return
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(webhook_url, json=event)
