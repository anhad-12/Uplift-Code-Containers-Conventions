from fastapi import APIRouter

from shop.payments import charge, repo
from shop.payments.schemas import PaymentIn

router = APIRouter(prefix="/payments")


@router.post("")
def post_payment(payload: PaymentIn):
    payment = repo.save_payment(charge.charge(payload.user_id, payload.amount))
    return {"user_id": payment.user_id, "amount": payment.amount}
