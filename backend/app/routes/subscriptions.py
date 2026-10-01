from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.services.subscription_plans import get_plan_for_user

router = APIRouter(
    prefix="/api/subscriptions",
    tags=["Subscriptions"]
)


@router.get("/plans")
def subscription_plans(current_user=Depends(get_current_user)):
    role = current_user["role"]

    if role not in ("client", "restaurant", "hotel"):
        raise HTTPException(
            status_code=403,
            detail="Type de compte non éligible à un abonnement"
        )

    return {
        "role": role,
        "plans": [
            get_plan_for_user(role, "monthly"),
            get_plan_for_user(role, "annual")
        ]
    }
