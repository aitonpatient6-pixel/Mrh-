from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.subscription_plans import get_plan_for_user
from app.services.payment_service import create_payment_request

router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"]
)


class PaymentRequest(BaseModel):
    period: str


@router.post("/create")
def create_payment(
    data: PaymentRequest,
    current_user=Depends(get_current_user)
):
    role = current_user["role"]

    if role not in ("client", "restaurant", "hotel"):
        raise HTTPException(
            status_code=403,
            detail="Type de compte non éligible au paiement"
        )

    if data.period not in ("monthly", "annual"):
        raise HTTPException(
            status_code=400,
            detail="Choisissez monthly ou annual"
        )

    plan = get_plan_for_user(role, data.period)

    payment = create_payment_request(
        user_id=current_user["id"],
        role=role,
        period=data.period,
        price_fcfa=plan["price_fcfa"]
    )

    return {
        "message": "Demande de paiement créée",
        "payment": payment
    }
