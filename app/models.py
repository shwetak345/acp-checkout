from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

class RestockPreference(BaseModel):
    enabled: bool
    # guardrails; allow 1–365 days, default later if omitted
    remind_in_days: Optional[int] = Field(default=None, ge=1, le=365)

class Item(BaseModel):
    id: str
    quantity: int = Field(gt=0)
    restock_preference: Optional[RestockPreference] = None

class Address(BaseModel):
    name: Optional[str] = None
    line_one: Optional[str] = None
    line_two: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

class CreateSessionReq(BaseModel):
    buyer: Optional[Any] = None
    items: List[Item]
    fulfillment_address: Optional[Address] = None

class UpdateSessionReq(BaseModel):
    buyer: Optional[Any] = None
    items: Optional[List[Item]] = None
    fulfillment_address: Optional[Address] = None
    fulfillment_option_id: Optional[str] = None
    discount_code: Optional[str] = None

class CompleteReqPaymentData(BaseModel):
    token: str
    provider: Literal["stripe","custom"]
    billing_address: Optional[Address] = None

class CompleteReq(BaseModel):
    buyer: Optional[Any] = None
    payment_data: CompleteReqPaymentData

class LineItem(BaseModel):
    id: str
    item: Item
    base_amount: int
    discount: int
    subtotal: int
    tax: int
    total: int

class TotalsRow(BaseModel):
    type: Literal["items_base_amount","subtotal","tax","shipping","discount","total"]
    display_text: str
    amount: int

class FulfillmentOption(BaseModel):
    id: str
    label: str
    amount: int
    eta_days: int

class Message(BaseModel):
    type: Literal["info","error"]
    code: Optional[str] = None
    path: Optional[str] = None
    content_type: Literal["plain"] = "plain"
    content: str

class Link(BaseModel):
    type: Literal["terms_of_use","privacy_policy"]
    url: str

class PaymentProvider(BaseModel):
    provider: Literal["stripe","custom"] = "stripe"
    supported_payment_methods: List[str] = ["card"]

class ACPCheckoutSession(BaseModel):
    id: str
    payment_provider: PaymentProvider
    status: Literal["not_ready_for_payment","ready_for_payment","completed","canceled","in_progress"]
    currency: str
    line_items: List[LineItem]
    fulfillment_address: Optional[Address] = None
    fulfillment_options: List[FulfillmentOption]
    fulfillment_option_id: Optional[str] = None
    totals: List[TotalsRow]
    messages: List[Message]
    links: List[Link]
    order_id: Optional[str] = None

class Feedback(BaseModel):
    session_id: str
    rating: int  # 1 to 5
    comment: str | None = None


