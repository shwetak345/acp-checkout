class PaymentDeclined(Exception):
    pass

async def authorize_charge(*, token: str, amount: int, currency: str) -> dict:
    # allow totals up to $500 (50000 cents)
    if amount > 50000:
        raise PaymentDeclined("authorization_failed")
    return {"auth_id": "auth_mock"}
