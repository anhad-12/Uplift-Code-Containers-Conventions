from pydantic import BaseModel, Field


class PaymentIn(BaseModel):
    user_id: int
    amount: float
    card: str = Field(..., pattern=r"^\d{16}$")
