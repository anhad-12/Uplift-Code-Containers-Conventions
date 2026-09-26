from pydantic import BaseModel, Field


class PaymentIn(BaseModel):
    user_id: int
    amount: float
    card: str = Field(..., regex=r"^\d{16}$")
