from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
from .models import (
    CreateSessionReq, UpdateSessionReq, CompleteReq,
    ACPCheckoutSession, FulfillmentOption, Message, Link
)
from .utils import (
    default_fulfillment_options, calc_cart, LINKS, CURRENCY, uuid,
    OPENAI_ORDER_WEBHOOK_URL
)
from .payments import authorize_charge, PaymentDeclined
from .orders import create_order, emit_order_event, Order

app = FastAPI(title="ACP Checkout (Python)", version="0.1.0")

sessions: Dict[str, ACPCheckoutSession] = {}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/checkout_sessions", response_model=ACPCheckoutSession, status_code=201)
def create_session(payload: CreateSessionReq):
    session_id = uuid("cs")
    fopts = default_fulfillment_options()
    selected = fopts[0]
    line_items, totals, _ = calc_cart(payload.items, selected)

    ready = payload.fulfillment_address is not None
    messages: list[Message] = []
    if not ready:
        messages.append(Message(
            type="info",
            content="Add a shipping address to calculate final taxes & enable payment."
        ))

    s = ACPCheckoutSession(
        id=session_id,
        payment_provider={"provider": "stripe", "supported_payment_methods": ["card"]},
        status="ready_for_payment" if ready else "in_progress",
        currency=CURRENCY,
        line_items=line_items,
        fulfillment_address=payload.fulfillment_address,
        fulfillment_options=fopts,
        fulfillment_option_id=selected.id,
        totals=totals,
        messages=messages,
        links=[Link(**l) for l in LINKS],
    )
    sessions[session_id] = s
    return s

@app.post("/checkout_sessions/{session_id}", response_model=ACPCheckoutSession)
def update_session(session_id: str, payload: UpdateSessionReq):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "not_found")

    if s.status in ["canceled", "completed"]:
        raise HTTPException(409, f"Cannot update a session with status '{s.status}'")

    items = payload.items or [li.item for li in s.line_items]
    fopts = s.fulfillment_options or default_fulfillment_options()
    selected_id = payload.fulfillment_option_id or s.fulfillment_option_id or fopts[0].id
    selected = next((o for o in fopts if o.id == selected_id), fopts[0])

    line_items, totals, _ = calc_cart(items, selected)

    s.line_items = line_items
    s.fulfillment_address = payload.fulfillment_address or s.fulfillment_address
    s.fulfillment_options = fopts
    s.fulfillment_option_id = selected.id
    s.totals = totals
    s.status = "ready_for_payment" if s.fulfillment_address else "in_progress"
    s.messages = []
    sessions[session_id] = s
    return s

@app.post("/checkout_sessions/{session_id}/complete", response_model=ACPCheckoutSession)
async def complete_session(session_id: str, payload: CompleteReq):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "not_found")

    if s.status in ["completed", "canceled"]:
        raise HTTPException(409, f"Cannot complete a session with status '{s.status}'")

    total_row = next((t for t in s.totals if t.type == "total"), None)
    if not total_row:
        raise HTTPException(400, "invalid_state")

    try:
        await authorize_charge(
            token=payload.payment_data.token,
            amount=total_row.amount,
            currency=s.currency,
        )
    except PaymentDeclined:
        s.messages = [{
            "type": "error",
            "code": "payment_declined",
            "content_type": "plain",
            "content": "Payment declined."
        }]
        return JSONResponse(status_code=402, content=s.model_dump())

    s.status = "completed"
    order_id = uuid("ord")
    s.order_id = order_id

    order = create_order(Order(
        id=order_id,
        checkout_session_id=s.id,
        total=total_row.amount,
        currency=s.currency,
        status="paid"
    ))

    await emit_order_event(OPENAI_ORDER_WEBHOOK_URL, {
        "type": "order.created",
        "data": {
            "id": order.id,
            "checkout_session_id": order.checkout_session_id,
            "total": order.total,
            "currency": order.currency,
            "status": order.status,
        }
    })

    sessions[session_id] = s
    return s

@app.post("/checkout_sessions/{session_id}/cancel", response_model=ACPCheckoutSession)
def cancel_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "not_found")
    # Prevent canceling completed sessions
    if s.status == "completed":
        raise HTTPException(409, "Cannot cancel a completed session")

    # Prevent double cancel
    if s.status == "canceled":
        raise HTTPException(409, "Session already canceled")
    
    s.status = "canceled"
    return s

@app.get("/checkout_sessions/{session_id}", response_model=ACPCheckoutSession)
def get_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "not_found")
    return s
